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

import fcntl
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

# Cross-process dongle mutex. The RTL-SDR has ONE USB endpoint shared by
# three *independent OS processes*: this in-process Tuner (FM/GPS), the
# SAME pipeline (rpi-hub-listen-same.service), and dump1090-mutability. A
# threading.Lock only arbitrates callers inside this process, so every
# consumer must instead hold this advisory flock — see same_pipeline.sh
# and the dump1090 drop-in. The lock file is provisioned 0666 by
# tmpfiles.d so each unit's (dynamic) user can open it.
RTLSDR_LOCK_PATH = os.environ.get("rpi_hub_RTLSDR_LOCK", "/run/rpi-hub/rtlsdr.lock")
DETECT_SCRIPT = os.environ.get("rpi_hub_DETECT_RTLSDR", "/opt/rpi-hub/scripts/detect_rtlsdr.sh")

# Cache passive detection briefly so the Listen UI polling /state does not
# re-probe USB on every request.
_DETECT_CACHE: tuple[float, bool] | None = None
_DETECT_TTL_S = 5.0


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
    """Passive USB-ID detection that does NOT open/claim the dongle.

    The old implementation shelled ``rtl_test -t``, which *opens* the
    radio — so polling ``/state`` while SAME/broadcast/GPS held the
    dongle both reported a false "no device" and disrupted the live
    stream. We instead reuse ``scripts/detect_rtlsdr.sh``, which only
    matches USB vendor:product IDs (lsusb), and cache the result for a
    few seconds so the polling Listen UI never re-probes per request.
    """

    global _DETECT_CACHE
    now = time.monotonic()
    if _DETECT_CACHE is not None and (now - _DETECT_CACHE[0]) < _DETECT_TTL_S:
        return _DETECT_CACHE[1]
    present = False
    try:
        rc = subprocess.run(
            [DETECT_SCRIPT], capture_output=True, timeout=2.0
        ).returncode
        present = rc == 0
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired, OSError):
        present = False
    _DETECT_CACHE = (now, present)
    return present


class Tuner:
    """Process-wide arbiter. Hold the lock for the whole transition."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[bytes] | None = None
        self._lock_fd: int | None = None  # held flock fd while a child owns the dongle
        self._state = TunerState(mode="idle", frequency_hz=0, label="idle", started_ts=0.0)

    @property
    def state(self) -> TunerState:
        return self._state

    def stop(self) -> None:
        with self._lock:
            self._kill_locked()

    def _acquire_dongle_locked(self) -> None:
        """Take the cross-process RTL-SDR flock; raise TunerBusy if held.

        Degrades gracefully when the lock file cannot be created (e.g. a
        dev box with no /run/rpi-hub) — there we fall back to the
        in-process lock only, which is correct off-device.
        """

        try:
            fd = os.open(RTLSDR_LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o666)
        except OSError:
            self._lock_fd = None
            return
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(fd)
            raise TunerBusy(
                "RTL-SDR is held by another process (SAME pipeline or dump1090); "
                "stop it before tuning"
            ) from exc
        self._lock_fd = fd

    def _release_dongle_locked(self) -> None:
        if self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(self._lock_fd)
            except OSError:
                pass
            self._lock_fd = None

    def _signal_group(self, sig: int) -> None:
        """Signal the child's whole process group (it is a session leader).

        Falls back to signalling the bare child if the group lookup
        fails (e.g. the child already exited).
        """

        proc = self._proc
        if proc is None:
            return
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.send_signal(sig)
            except OSError:
                pass

    def _kill_locked(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._signal_group(signal.SIGTERM)
                self._proc.wait(timeout=2.0)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    self._signal_group(signal.SIGKILL)
                    self._proc.wait(timeout=2.0)
                except (OSError, subprocess.TimeoutExpired):
                    pass
        self._proc = None
        self._release_dongle_locked()
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
            self._acquire_dongle_locked()  # raises TunerBusy if another process holds it
            try:
                self._proc = subprocess.Popen(
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,
                    env=env,
                    start_new_session=True,
                )
            except (FileNotFoundError, OSError) as exc:
                self._release_dongle_locked()
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
            self._acquire_dongle_locked()  # raises TunerBusy if another process holds it
            try:
                self._proc = subprocess.Popen(
                    argv,
                    stdout=subprocess.DEVNULL,  # WebSocket bridge will replace this
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except (FileNotFoundError, OSError) as exc:
                self._release_dongle_locked()
                raise TunerUnavailable(str(exc)) from exc
            self._state = TunerState(
                mode=mode,
                frequency_hz=frequency_hz,
                label=label,
                started_ts=time.time(),
            )
            return self._state
