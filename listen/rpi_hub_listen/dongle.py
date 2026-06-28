"""Single-listener arbitration for the RTL-SDR dongle.

The RTL-SDR exposes a single USB endpoint; two ``rtl_fm`` processes
fighting over it produce silence. The arbiter is the only thing in this
codebase allowed to spawn rtl_fm / dump1090 / multimon-ng. It keeps a
single child process in a known state and rejects mode changes with a
clean 409 to the caller.

The arbiter is sync — RTL-SDR mode transitions are slow (the dongle
takes ~200ms to settle on a new frequency) but rare, so a single
process-wide lock is fine.
"""

from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass

# Where rtl_fm lives. apt's "rtl-sdr" package installs it at /usr/bin/rtl_fm.
RTL_FM = "/usr/bin/rtl_fm"
DUMP1090 = "/usr/bin/dump1090"
MULTIMON = "/usr/bin/multimon-ng"


@dataclass(frozen=True)
class TunerState:
    mode: str  # "idle" | "weather" | "broadcast" | "bands"
    frequency_hz: int  # 0 in idle
    label: str  # human-readable, surfaced to the UI
    started_ts: float


class TunerBusy(RuntimeError):
    """Another mode is active; caller must STOP first."""


class TunerUnavailable(RuntimeError):
    """No dongle detected, or rtl_fm not installed."""


def _binary_present(path: str) -> bool:
    return shutil.which(path) is not None or os.path.exists(path)


def dongle_present() -> bool:
    """Cheap detection: does an rtl_test report any device?

    rtl_test exits non-zero if the kernel has no USB device matching the
    Realtek vendor IDs the driver claims. We treat any non-zero as
    "no dongle"; the UI just shows a "no hardware" banner.
    """

    if not _binary_present("rtl_test"):
        return False
    try:
        out = subprocess.run(
            ["rtl_test", "-t"], capture_output=True, text=True, timeout=2.0
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    blob = (out.stdout + out.stderr).lower()
    return "found 1 device" in blob or "found " in blob and "device" in blob


class Tuner:
    """Process-wide arbiter. Hold the lock for the whole transition."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[bytes] | None = None
        self._state = TunerState(mode="idle", frequency_hz=0, label="idle", started_ts=0.0)

    @property
    def state(self) -> TunerState:
        return self._state

    def stop(self) -> None:
        with self._lock:
            self._kill_locked()

    def _kill_locked(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.send_signal(signal.SIGTERM)
                self._proc.wait(timeout=2.0)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    self._proc.kill()
                except OSError:
                    pass
        self._proc = None
        self._state = TunerState(mode="idle", frequency_hz=0, label="idle", started_ts=0.0)

    def start_weather(self, frequency_hz: int, label: str) -> TunerState:
        """rtl_fm tuned to a NOAA WX frequency, FM narrow, 12 kHz output.

        The multimon-ng EAS decoder is wired downstream by the SAME
        decoder module — :mod:`same`. Here we just spin rtl_fm with
        stdout piped to a named FIFO (created by the service unit).
        """

        return self._start(
            mode="weather",
            frequency_hz=frequency_hz,
            label=label,
            argv=[
                RTL_FM,
                "-M", "fm",
                "-f", str(frequency_hz),
                "-s", "22050",
                "-r", "22050",
                "-g", "40",
                "-l", "0",
                "-",  # stdout
            ],
        )

    def start_broadcast(self, frequency_hz: int, label: str) -> TunerState:
        """FM broadcast band — wider deemphasis, higher sample rate."""

        return self._start(
            mode="broadcast",
            frequency_hz=frequency_hz,
            label=label,
            argv=[
                RTL_FM,
                "-M", "wbfm",
                "-f", str(frequency_hz),
                "-s", "200000",
                "-r", "44100",
                "-g", "30",
                "-",
            ],
        )

    def start_bands(self, frequency_hz: int, label: str, mode: str = "fm") -> TunerState:
        """Ham band tuner. Defaults to FM narrow; SSB requires post-detect SDR
        software we don't ship in v0.8.
        """

        return self._start(
            mode="bands",
            frequency_hz=frequency_hz,
            label=label,
            argv=[
                RTL_FM,
                "-M", mode,
                "-f", str(frequency_hz),
                "-s", "22050",
                "-r", "22050",
                "-g", "40",
                "-",
            ],
        )

    def start_gps(
        self,
        argv: list[str],
        label: str = "GPS sky survey",
        env: dict[str, str] | None = None,
    ) -> tuple[TunerState, "subprocess.Popen[bytes]"]:
        """Phase 13: spawn a finite ``gps_sdr`` sweep under the arbiter.

        Unlike the rtl_fm modes this child is *expected to exit on its
        own* (``--once``), and its stdout carries the JSON report the
        :mod:`gps` sweeper parses — so stdout is PIPE, not DEVNULL. The
        caller (GPSSweeper) owns reaping via ``communicate()`` and MUST
        call :meth:`finish` afterwards to release the dongle.

        gps_sdr opens the dongle through pyrtlsdr rather than spawning
        rtl_fm, so the rtl_fm binary check does not apply here; failure
        to open the device surfaces in the child's exit code / stderr.
        """
        with self._lock:
            if self._state.mode != "idle":
                raise TunerBusy(
                    f"current mode={self._state.mode!s}; stop before re-tuning"
                )
            try:
                self._proc = subprocess.Popen(
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,
                    env=env,
                )
            except (FileNotFoundError, OSError) as exc:
                raise TunerUnavailable(str(exc)) from exc
            self._state = TunerState(
                mode="gps",
                frequency_hz=1_575_420_000,  # GPS L1
                label=label,
                started_ts=time.time(),
            )
            return self._state, self._proc

    def finish(self, mode: str) -> None:
        """Release the arbiter if *mode* is still current.

        Idempotent. If the child already exited this just clears state;
        if it is somehow still alive (timeout path) it is killed by the
        same code path :meth:`stop` uses.
        """
        with self._lock:
            if self._state.mode == mode:
                self._kill_locked()

    def _start(
        self, mode: str, frequency_hz: int, label: str, argv: list[str]
    ) -> TunerState:
        if not _binary_present(RTL_FM):
            raise TunerUnavailable("rtl_fm not installed")
        with self._lock:
            if self._state.mode != "idle":
                raise TunerBusy(
                    f"current mode={self._state.mode!s}; stop before re-tuning"
                )
            # Sanity-quote the argv in logs — never shell out via `bash -c`.
            _ = " ".join(shlex.quote(a) for a in argv)
            try:
                self._proc = subprocess.Popen(
                    argv,
                    stdout=subprocess.DEVNULL,  # WebSocket bridge will replace this
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                )
            except (FileNotFoundError, OSError) as exc:
                raise TunerUnavailable(str(exc)) from exc
            self._state = TunerState(
                mode=mode,
                frequency_hz=frequency_hz,
                label=label,
                started_ts=time.time(),
            )
            return self._state
