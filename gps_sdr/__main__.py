"""gps_sdr – GPS L1 C/A acquisition via RTL-SDR.

Usage
─────
Hardware mode (RTL-SDR Blog v3/v4 with active antenna):
    python -m gps_sdr

Simulation mode (no hardware required):
    python -m gps_sdr --simulate

Full options:
    python -m gps_sdr --help
"""

from __future__ import annotations

import argparse
import functools
import json
import logging
import sys
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from .constants import DEFAULT_ACQ_THRESHOLD

if TYPE_CHECKING:
    from .acquisition import AcquisitionResult

# ── logging ───────────────────────────────────────────────────────────────────


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)-8s %(name)s: %(message)s",
    )


# ── argument parser ───────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m gps_sdr",
        description="GPS L1 C/A acquisition using an RTL-SDR receiver.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    hw = p.add_argument_group("Hardware")
    hw.add_argument("--device", type=int, default=0, metavar="N", help="RTL-SDR device index")
    hw.add_argument(
        "--no-bias-tee",
        action="store_true",
        help="Do NOT enable bias tee (passive antenna or external LNA)",
    )
    hw.add_argument(
        "--ppm",
        type=int,
        default=0,
        metavar="PPM",
        help="RTL-SDR frequency correction in parts-per-million",
    )
    hw.add_argument(
        "--gain", type=float, default=49.6, metavar="DB", help="RTL-SDR gain in dB (49.6 = max)"
    )
    hw.add_argument(
        "--sample-rate",
        type=float,
        default=2.048,
        metavar="MSPS",
        help="Sample rate in Msps (2.048 recommended for GPS L1)",
    )

    acq = p.add_argument_group("Acquisition")
    acq.add_argument(
        "--prns",
        type=int,
        nargs="+",
        metavar="N",
        help="Specific PRN numbers to search (default: all 1–32)",
    )
    acq.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_ACQ_THRESHOLD,
        metavar="RATIO",
        help="Peak-to-noise-floor detection threshold "
        "(default %(default)s; see constants.py for the "
        "false-alarm derivation — do not lower without care)",
    )
    acq.add_argument(
        "--doppler-range",
        type=float,
        default=10_000,
        metavar="HZ",
        help="Doppler search half-range in Hz",
    )
    acq.add_argument(
        "--doppler-step", type=float, default=500, metavar="HZ", help="Doppler bin step in Hz"
    )
    acq.add_argument(
        "--integration-ms",
        type=int,
        default=1,
        metavar="MS",
        help="Non-coherent integration (number of 1 ms blocks to sum)",
    )

    run = p.add_argument_group("Run control")
    run.add_argument(
        "--simulate", action="store_true", help="Use synthetic signal (no hardware needed)"
    )
    run.add_argument("--once", action="store_true", help="Run a single acquisition pass then exit")
    run.add_argument(
        "--json",
        action="store_true",
        help="Machine output: suppress tables/preamble, emit one JSON "
        "document per sweep on stdout (JSONL in loop mode)",
    )
    run.add_argument(
        "--interval",
        type=float,
        default=5.0,
        metavar="SEC",
        help="Seconds between acquisition sweeps",
    )
    run.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    return p


# ── Rich display ──────────────────────────────────────────────────────────────


def _check_rich() -> bool:
    try:
        import rich  # noqa: F401, PLC0415

        return True
    except ImportError:
        return False


def _signal_bar(metric: float, width: int = 18) -> str:
    """ASCII signal strength bar for *metric* (clamp at 20)."""
    filled = int(min(metric / 20.0, 1.0) * width)
    return "█" * filled + "░" * (width - filled)


def _render_table_rich(
    results: list[AcquisitionResult],
    scan_no: int,
    elapsed: float,
    mode: str,
    bias_tee_ok: bool,
) -> None:
    from rich import box  # noqa: PLC0415
    from rich.console import Console  # noqa: PLC0415
    from rich.panel import Panel  # noqa: PLC0415
    from rich.table import Table  # noqa: PLC0415

    console = Console()

    acquired = [r for r in results if r.acquired]
    acq_color = "green" if acquired else "yellow"
    mode_color = "green" if mode == "HARDWARE" else "magenta"
    tee_color = "green" if bias_tee_ok else "red"
    tee_text = "ON ✓" if bias_tee_ok else "OFF ✗"
    header_lines = [
        f"[bold cyan]GPS L1 Acquisition[/bold cyan]  [dim]1575.42 MHz[/dim]  "
        f"[yellow]Scan #{scan_no}[/yellow]  [dim](+{elapsed:.1f} s)[/dim]",
        f"Mode: [{mode_color}]{mode}[/]  "
        f"Bias tee: [{tee_color}]{tee_text}[/]  "
        f"Satellites acquired: [{acq_color}]{len(acquired)} / {len(results)}[/]",
    ]

    tbl = Table(box=box.ROUNDED, show_lines=False, highlight=True, expand=False)
    tbl.add_column("PRN", style="cyan", width=5, justify="right")
    tbl.add_column("Status", width=11, justify="center")
    tbl.add_column("Doppler", width=12, justify="right")
    tbl.add_column("Phase", width=8, justify="right")
    tbl.add_column("Metric", width=9, justify="right")
    tbl.add_column("Signal", width=22)

    for r in results:
        if r.acquired:
            row = (
                str(r.prn),
                "[bold green]LOCKED[/bold green]",
                f"[green]{r.doppler_hz:+.0f} Hz[/green]",
                f"[green]{r.code_phase}[/green]",
                f"[green]{r.metric:5.1f}[/green]",
                f"[green]{_signal_bar(r.metric)}[/green]",
            )
        else:
            row = (
                f"[dim]{r.prn}[/dim]",
                "[dim]searching[/dim]",
                f"[dim]{r.doppler_hz:+.0f} Hz[/dim]",
                f"[dim]{r.code_phase}[/dim]",
                f"[dim]{r.metric:5.1f}[/dim]",
                f"[dim]{_signal_bar(r.metric)}[/dim]",
            )
        tbl.add_row(*row)

    console.print()
    console.print(Panel("\n".join(header_lines), border_style="bright_blue"))
    console.print(tbl)

    if acquired:
        console.print(
            "\n[bold]Acquired satellites:[/bold]  "
            + "  ".join(
                f"[green]PRN {r.prn}[/green] "
                f"[dim](Δf={r.doppler_hz:+.0f} Hz, "
                f"phase={r.code_phase})[/dim]"
                for r in acquired
            )
        )


def _render_table_plain(
    results: list[AcquisitionResult],
    scan_no: int,
    elapsed: float,
    mode: str,
    bias_tee_ok: bool,
) -> None:
    acquired = [r for r in results if r.acquired]
    print(f"\n{'─'*70}")
    print(f"GPS L1 Acquisition │ Scan #{scan_no} (+{elapsed:.1f}s) │ Mode: {mode}")
    acq_count = len(acquired)
    total_count = len(results)
    tee_state = "ON" if bias_tee_ok else "OFF"
    print(f"Bias tee: {tee_state}  │  Acquired: {acq_count}/{total_count}")
    print(f"{'─'*70}")
    print(f"{'PRN':>4}  {'Status':^10}  {'Doppler':>10}  {'Phase':>6}  {'Metric':>7}  Signal")
    print(f"{'─'*70}")
    for r in results:
        status = "LOCKED" if r.acquired else "searching"
        bar = _signal_bar(r.metric, width=14)
        print(
            f"{r.prn:>4}  {status:^10}  {r.doppler_hz:>+9.0f}Hz  {r.code_phase:>6}  "
            f"{r.metric:>7.2f}  {bar}"
        )
    print(f"{'─'*70}")


# ── JSON output (machine consumers: rpi-hub-listen GPS sweeper) ──────────────


def _render_json(
    results: list[AcquisitionResult],
    scan_no: int,
    elapsed: float,
    mode: str,
    bias_tee_ok: bool,
    *,
    sample_rate: float,
    integration_ms: int,
    threshold: float,
) -> None:
    """One JSON document per line on stdout.

    Contract (consumed by listen/rpi_hub_listen/gps.py — keep stable):
    top-level keys ts/scan/mode/bias_tee/sample_rate/integration_ms/
    threshold/elapsed_s/acquired_count/results[]. ``results`` carries every
    searched PRN so consumers can render noise-floor context, not just hits.
    """
    doc = {
        "ts": time.time(),
        "scan": scan_no,
        "mode": mode,
        "bias_tee": bool(bias_tee_ok),
        "sample_rate": sample_rate,
        "integration_ms": integration_ms,
        "threshold": threshold,
        "elapsed_s": round(elapsed, 3),
        "acquired_count": sum(1 for r in results if r.acquired),
        "results": [
            {
                "prn": r.prn,
                "acquired": bool(r.acquired),
                "doppler_hz": round(float(r.doppler_hz), 1),
                "code_phase": int(r.code_phase),
                "metric": round(float(r.metric), 3),
                "cn0_proxy_db": round(float(r.cn0_proxy_db), 1),
            }
            for r in results
        ],
    }
    print(json.dumps(doc, separators=(",", ":")), flush=True)


# ── main ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:  # noqa: PLR0912, PLR0915
    args = _build_parser().parse_args(argv)
    _setup_logging(args.verbose)

    from .acquisition import GPSAcquisition  # noqa: PLC0415

    use_rich = _check_rich()
    quiet = args.json
    render: Callable[[list[AcquisitionResult], int, float, str, bool], None]
    if args.json:
        render = functools.partial(
            _render_json,
            sample_rate=args.sample_rate * 1e6,
            integration_ms=args.integration_ms,
            threshold=args.threshold,
        )
    else:
        render = _render_table_rich if use_rich else _render_table_plain

    sample_rate = args.sample_rate * 1e6

    # ── build acquisition engine ──────────────────────────────────────────────
    if not quiet:
        print("Initialising GPS acquisition engine … ", end="", flush=True)
    acq = GPSAcquisition(
        sample_rate=sample_rate,
        doppler_range_hz=args.doppler_range,
        doppler_step_hz=args.doppler_step,
        integration_ms=args.integration_ms,
        threshold=args.threshold,
    )
    if not quiet:
        print("ready.")
        print(
            f"  {len(acq.doppler_bins)} Doppler bins  ×  32 PRNs  "
            f"×  {acq.integration_ms} ms integration"
        )
        print(f"  {acq.spc} samples/code at {sample_rate/1e6:.3f} Msps\n")

    bias_tee_active = not args.no_bias_tee  # assume it will be enabled
    samples_needed = acq.spc * args.integration_ms

    if args.simulate:
        # ── simulation mode ───────────────────────────────────────────────────
        from .simulate import DEFAULT_SCENARIO, GPSSimulator  # noqa: PLC0415

        sim = GPSSimulator(sample_rate=sample_rate)
        if not quiet:
            print("[SIMULATE] Using synthetic signal with the following satellites:")
            for s in DEFAULT_SCENARIO:
                print(
                    f"  PRN {s.prn:2d}  Δf={s.doppler_hz:+.0f} Hz  "
                    f"phase={s.code_phase}  amp={s.amplitude}"
                )
            print()
        bias_tee_active = False  # no hardware in simulate mode

        scan = 0
        t0 = time.monotonic()
        try:
            while True:
                scan += 1
                samples = sim.generate(duration_ms=args.integration_ms)
                results = acq.run(samples, prns=args.prns)
                render(results, scan, time.monotonic() - t0, "SIMULATE", bias_tee_active)
                if args.once:
                    break
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nInterrupted.")

    else:
        # ── hardware mode ─────────────────────────────────────────────────────
        from .hardware import GPSRadio  # noqa: PLC0415

        radio = GPSRadio(
            device_index=args.device,
            sample_rate=sample_rate,
            ppm_correction=args.ppm,
            bias_tee=not args.no_bias_tee,
            gain_db=args.gain,
        )

        try:
            radio.open()
            bias_tee_active = radio._bias_tee_active

            # Discard first buffer (RTL-SDR AGC settling)
            if not quiet:
                print("Discarding AGC settling buffer … ", end="", flush=True)
            radio.read_samples(radio.samples_for_ms(10))
            if not quiet:
                print("done.\n")

            scan = 0
            t0 = time.monotonic()
            try:
                while True:
                    scan += 1
                    samples = radio.read_samples(samples_needed + acq.spc)
                    results = acq.run(samples, prns=args.prns)
                    render(results, scan, time.monotonic() - t0, "HARDWARE", bias_tee_active)
                    if args.once:
                        break
                    time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\nInterrupted.")
        finally:
            radio.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
