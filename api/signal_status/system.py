"""Host probes for the status endpoint.

Each probe returns a typed value (or `None`) and never raises. The endpoint
composes them once per request — total wall time stays well under the 200ms
budget on a Pi Zero 2 W because the slowest single call (vcgencmd) is
~30ms and runs at most once per request.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Paths are constants so tests can monkeypatch them.
PROC_UPTIME = Path("/proc/uptime")
DNSMASQ_LEASES = Path("/var/lib/misc/dnsmasq.leases")
DNSMASQ_LEASES_ALT = Path("/var/lib/dnsmasq/dnsmasq.leases")
KIWIX_DIR = Path("/var/lib/kiwix")
VERSION_FILE = Path("/etc/signal/version")
RTC_DEV = Path("/dev/rtc")
RTC_DEV_0 = Path("/dev/rtc0")

VCGENCMD_TIMEOUT_S = 1.0


@dataclass(frozen=True)
class StorageInfo:
    kiwix_bytes_free: int | None
    kiwix_bytes_total: int | None


@dataclass(frozen=True)
class VoltageInfo:
    # Raw "throttled=0x..." word (without the prefix) for diagnostics.
    throttled: str | None
    # True iff bit 0 is set — undervoltage is happening right now.
    undervoltage: bool | None


def uptime_seconds() -> float | None:
    try:
        first = PROC_UPTIME.read_text().split()[0]
        return float(first)
    except (OSError, ValueError, IndexError):
        return None


def load_avg() -> tuple[float, float, float] | None:
    try:
        a, b, c = os.getloadavg()
        return (a, b, c)
    except OSError:
        return None


def storage(path: Path = KIWIX_DIR) -> StorageInfo:
    # If the kiwix dir doesn't exist yet (Phase 3 hasn't run), fall back to
    # the root filesystem — gives the user *something* meaningful rather
    # than a hole in the page.
    target = path if path.exists() else Path("/")
    try:
        u = shutil.disk_usage(target)
        return StorageInfo(kiwix_bytes_free=u.free, kiwix_bytes_total=u.total)
    except OSError:
        return StorageInfo(kiwix_bytes_free=None, kiwix_bytes_total=None)


def dhcp_clients() -> int | None:
    # dnsmasq writes one lease per line. An empty/non-existent file means
    # zero clients, not unknown — distinguish by file presence.
    for candidate in (DNSMASQ_LEASES, DNSMASQ_LEASES_ALT):
        if candidate.exists():
            try:
                text = candidate.read_text()
                return sum(1 for line in text.splitlines() if line.strip())
            except OSError:
                return None
    return None


def voltage() -> VoltageInfo:
    # vcgencmd is a Pi-only binary. On a dev machine the FileNotFoundError
    # path returns "unknown" cleanly.
    try:
        result = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True,
            text=True,
            timeout=VCGENCMD_TIMEOUT_S,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return VoltageInfo(throttled=None, undervoltage=None)

    if result.returncode != 0:
        return VoltageInfo(throttled=None, undervoltage=None)

    # Expected format: "throttled=0x0\n"
    raw = result.stdout.strip()
    prefix = "throttled="
    if not raw.startswith(prefix):
        return VoltageInfo(throttled=raw or None, undervoltage=None)

    word = raw[len(prefix):]
    try:
        bits = int(word, 16)
    except ValueError:
        return VoltageInfo(throttled=word, undervoltage=None)

    # Bit 0 is "undervoltage detected" (active right now).
    return VoltageInfo(throttled=word, undervoltage=bool(bits & 0x1))


def time_source() -> str:
    # Cheap heuristic. Phase 7's GPS-via-LoRa pathway will overwrite this
    # with "gps" via a sidecar file once it lands.
    if RTC_DEV.exists() or RTC_DEV_0.exists():
        return "rtc"
    return "none"


def build_version() -> str:
    try:
        v = VERSION_FILE.read_text().strip()
        return v or "dev"
    except OSError:
        return "dev"
