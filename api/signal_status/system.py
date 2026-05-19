"""Host probes for the status endpoint.

Each probe returns a typed value (or `None`) and never raises. The endpoint
composes them once per request — total wall time stays well under the 200ms
budget on a Pi Zero 2 W because the slowest single call (vcgencmd) is
~30ms and runs at most once per request.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
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
ADSB_JSON = Path("/run/dump1090-mutability/aircraft.json")
# Stale-ness ceiling for the ADS-B probe. dump1090-mutability writes
# aircraft.json once per second by default; 30s of staleness reliably
# means the process is wedged or stopped.
ADSB_STALE_SECONDS = 30.0

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


# -- per-service readiness probes (Phases 6–9) ---------------------------
#
# These are local-loopback HTTP probes with a tight budget. Every probe
# returns one of three strings, never None:
#
#   "ready"        — the service responded
#   "not-running"  — connection refused / timeout (unit inactive or absent)
#   "unknown"      — anything else; surfaced for diagnostics
#
# The endpoint composes all probes in parallel-ish fashion (they share
# the request budget). On a fresh Pi where most optional services are
# inactive, each probe falls through to "not-running" in ~5ms.

PROBE_TIMEOUT_S = 0.4


def _probe_local_http(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=PROBE_TIMEOUT_S) as resp:
            return "ready" if 200 <= resp.status < 500 else "unknown"
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError):
        return "not-running"


def _probe_json_field(url: str, field: str) -> str | None:
    """Hit a JSON endpoint and return a single string field, or None."""

    try:
        with urllib.request.urlopen(url, timeout=PROBE_TIMEOUT_S) as resp:
            body = json.loads(resp.read())
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(body, dict):
        return None
    v = body.get(field)
    return str(v) if v is not None else None


@dataclass(frozen=True)
class ServicesInfo:
    retrieve: str  # Phase 6
    assist: str    # Phase 6
    listen: str    # Phase 8
    notes: str     # Phase 9A
    mesh: str      # Phase 7
    adsb: str      # Phase 8.4
    adsb_aircraft: int | None  # surfaced from aircraft.json on a ready probe
    mesh_fingerprint: str | None  # surfaced for owner-to-owner trust


def _probe_adsb() -> tuple[str, int | None]:
    """File-based probe for dump1090-mutability.

    The ADS-B decoder has no HTTP surface in our config (HTTP=no in
    /etc/default/dump1090-mutability). What it *does* have is a JSON
    file refreshed once per second at ``/run/dump1090-mutability/aircraft.json``,
    and that file's mtime is the cleanest readiness signal: anything
    older than ~30s means the decoder is wedged or stopped, regardless
    of whether the unit thinks it's active.

    Semantics:

    * Freshness comes from ``aircraft.json`` mtime — must be within
      ``ADSB_STALE_SECONDS``.
    * Aircraft count is ``len(body["aircraft"])`` from the JSON payload.
    * Falls back to ``("not-running", None)`` if the file is missing
      or older than the staleness ceiling.
    """

    try:
        st = ADSB_JSON.stat()
    except OSError:
        return ("not-running", None)
    age = max(0.0, _now() - st.st_mtime)
    if age > ADSB_STALE_SECONDS:
        return ("not-running", None)
    try:
        body = json.loads(ADSB_JSON.read_bytes())
    except (OSError, json.JSONDecodeError):
        return ("unknown", None)
    if not isinstance(body, dict):
        return ("unknown", None)
    aircraft = body.get("aircraft")
    count = len(aircraft) if isinstance(aircraft, list) else None
    return ("ready", count)


def _now() -> float:
    """Wallclock seconds, factored for test monkeypatching."""

    import time

    return time.time()


def services() -> ServicesInfo:
    adsb_state, adsb_count = _probe_adsb()
    return ServicesInfo(
        retrieve=_probe_local_http("http://127.0.0.1:8100/health"),
        assist=_probe_local_http("http://127.0.0.1:8200/health"),
        listen=_probe_local_http("http://127.0.0.1:8300/health"),
        notes=_probe_local_http("http://127.0.0.1:8400/health"),
        mesh=_probe_local_http("http://127.0.0.1:8500/health"),
        adsb=adsb_state,
        adsb_aircraft=adsb_count,
        mesh_fingerprint=_probe_json_field("http://127.0.0.1:8500/identity", "fingerprint"),
    )
