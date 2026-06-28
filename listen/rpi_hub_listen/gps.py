"""Phase 13 — GPS L1 sky survey via the vendored ``gps_sdr`` package.

What this is
────────────
A finite, on-demand acquisition sweep: which GPS satellites are visible
right now, at what Doppler offset, at what signal strength. It is a
**diagnostic and educational** capability:

  * validates the active GPS antenna + bias-tee chain end-to-end,
  * gives an offline node a "sky state" readout with zero infrastructure,
  * demonstrates the receive path for SDR teaching sessions.

What this is NOT
────────────────
It does **not** produce a position fix or a time fix. Acquisition stops
before tracking loops and navigation-message decoding (see gps_sdr
README). For offline stratum-1 time the right tool is a u-blox module
with PPS into chrony — a hardware decision, not a software gap to paper
over here.

Arbitration
───────────
The RTL-SDR is a single-consumer device. A sweep acquires the same
:class:`~.dongle.Tuner` arbiter the rtl_fm modes use (mode ``"gps"``),
so Listen's existing busy/stop semantics apply unchanged: a sweep
rejects with 409 while audio is tuned, and ``POST /stop`` (or tuning
another mode, which always stops first) cancels an in-flight sweep.

The child process is ``python3 -m gps_sdr --once --json``; its single
stdout JSON line is the report. The sweeper keeps only the most recent
report — history is a UI concern we have no requirement for yet.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

from . import dongle

log = logging.getLogger(__name__)

# Repo root (/opt/rpi-hub in production) — parent that makes both
# ``listen`` and the vendored ``gps_sdr`` packages importable.
_REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_TIMEOUT_S = 180.0
# Hard bounds mirrored by the API model; kept here so direct callers
# (tests, future cron-style sweeps) get the same envelope.
INTEGRATION_MS_MIN, INTEGRATION_MS_MAX = 1, 10


def default_argv(
    *, prns: list[int] | None, integration_ms: int, simulate: bool
) -> list[str]:
    """Build the gps_sdr child argv. Split out for test injection."""
    argv = [
        sys.executable,
        "-m",
        "gps_sdr",
        "--once",
        "--json",
        "--integration-ms",
        str(integration_ms),
    ]
    if simulate:
        argv += ["--simulate", "--threshold", "15"]  # see gps_sdr README note
    if prns:
        argv += ["--prns", *[str(p) for p in prns]]
    return argv


def _parse_report(stdout: bytes) -> dict[str, Any] | None:
    """Last stdout line that parses as a sweep report wins.

    gps_sdr keeps stdout clean in --json mode, but tolerating stray
    lines costs nothing and protects against future preamble leaks.
    """
    for raw in reversed(stdout.decode("utf-8", errors="replace").splitlines()):
        raw = raw.strip()
        if not raw.startswith("{"):
            continue
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(doc, dict) and "results" in doc:
            return doc
    return None


class GPSSweeper:
    """Owns the sweep lifecycle: one background thread, one last result."""

    def __init__(
        self,
        tuner: dongle.Tuner,
        argv_builder: Callable[..., list[str]] = default_argv,
    ) -> None:
        self._tuner = tuner
        self._argv_builder = argv_builder
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._last: dict[str, Any] | None = None

    # ── public surface ────────────────────────────────────────────────

    def running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def last(self) -> dict[str, Any] | None:
        with self._lock:
            return dict(self._last) if self._last is not None else None

    def start(
        self,
        *,
        prns: list[int] | None = None,
        integration_ms: int = 2,
        simulate: bool = False,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        """Kick off a sweep.

        Raises :class:`dongle.TunerBusy` if any mode (including a prior
        sweep) holds the dongle, :class:`dongle.TunerUnavailable` if the
        child cannot be spawned. Returns immediately; poll ``running()``
        / ``last()``.
        """
        integration_ms = max(
            INTEGRATION_MS_MIN, min(INTEGRATION_MS_MAX, integration_ms)
        )
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise dongle.TunerBusy("sweep already in progress")
            argv = self._argv_builder(
                prns=prns, integration_ms=integration_ms, simulate=simulate
            )
            # PYTHONPATH must reach the repo root so `-m gps_sdr` resolves
            # under DynamicUser with no site install.
            env = dict(os.environ)
            env["PYTHONPATH"] = str(_REPO_ROOT) + (
                os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
            )
            _state, proc = self._tuner.start_gps(argv, env=env)
            t = threading.Thread(
                target=self._reap,
                args=(proc, timeout_s, time.time()),
                name="gps-sweep-reaper",
                daemon=True,
            )
            self._thread = t
            t.start()

    # ── internals ─────────────────────────────────────────────────────

    def _reap(
        self, proc: subprocess.Popen[bytes], timeout_s: float, started: float
    ) -> None:
        record: dict[str, Any] = {
            "requested_ts": started,
            "completed_ts": None,
            "ok": False,
            "error": None,
            "report": None,
        }
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
            if proc.returncode != 0:
                tail = stderr.decode("utf-8", errors="replace").strip()[-400:]
                # SIGTERM from Tuner.stop()/tune() → operator cancel, not fault.
                if proc.returncode < 0:
                    record["error"] = "cancelled"
                else:
                    record["error"] = f"exit {proc.returncode}: {tail or 'no stderr'}"
            else:
                report = _parse_report(stdout)
                if report is None:
                    record["error"] = "no JSON report on stdout"
                else:
                    record["ok"] = True
                    record["report"] = report
        except subprocess.TimeoutExpired:
            record["error"] = f"timeout after {timeout_s:.0f}s"
            # finish() below kills the still-running child.
        except Exception as exc:  # pragma: no cover — defensive
            log.exception("gps sweep reaper failed")
            record["error"] = f"internal: {exc}"
        finally:
            record["completed_ts"] = time.time()
            self._tuner.finish("gps")
            with self._lock:
                self._last = record
