"""BATMAN-adv (Wi-Fi mesh) bridge — Phase 7.3.

BATMAN-adv exposes peer presence via ``batctl`` and lets us push small
key/value payloads through ``alfred``. We don't try to be Reticulum
here — different radio, different bandwidth budget, different sync
semantics.

What this bridge does:

* periodically shells ``batctl o -nH`` to list originators (peers) and
  upserts them into the peer table tagged ``radio="wifi"``.
* exposes ``publish(payload: bytes)`` which writes to ``alfred -s 65``
  (data type 65 is reserved for rpi-hub by convention; bump if your
  deployment shares the link with other batman users).

Like the LoRa bridge, this degrades silently when the binaries or
adapter aren't present.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable

BATCTL = shutil.which("batctl") or "/usr/sbin/batctl"
ALFRED = shutil.which("alfred") or "/usr/sbin/alfred"
ALFRED_DATA_TYPE = int(os.environ.get("rpi_hub_ALFRED_DATA_TYPE", "65"))
POLL_INTERVAL_S = 30.0

# `batctl o -nH` line shape (approximate):
#   <originator MAC>    <last-seen>s  (<TQ>) <next-hop MAC>  [<iface>]
_ORIG_LINE = re.compile(
    r"^([0-9a-f:]{17})\s+([0-9.]+)s\s+\((\d+)\)\s+([0-9a-f:]{17})", re.IGNORECASE
)


@dataclass(frozen=True)
class WifiStatus:
    state: str  # "unavailable" | "running" | "error"
    detail: str
    last_change_ts: float


class WifiBridge:
    """Poll BATMAN-adv originators and surface them as mesh peers."""

    def __init__(self, on_peer: Callable[[str, int, str], None]) -> None:
        # on_peer receives (mac, tq, last_hop)
        self._on_peer = on_peer
        self._stop = threading.Event()
        self._status = WifiStatus(state="unavailable", detail="not started", last_change_ts=time.time())
        self._thread: threading.Thread | None = None

    @property
    def status(self) -> WifiStatus:
        return self._status

    def _set_status(self, state: str, detail: str = "") -> None:
        self._status = WifiStatus(state=state, detail=detail, last_change_ts=time.time())

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="wifi-bridge", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def publish(self, payload: bytes) -> bool:
        """Hand a payload to alfred for type-65 distribution.

        Returns True on success. False = alfred not installed or refused.
        """

        if not os.path.exists(ALFRED):
            return False
        try:
            subprocess.run(
                [ALFRED, "-s", str(ALFRED_DATA_TYPE)],
                input=payload,
                capture_output=True,
                timeout=2.0,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False
        return True

    def _run(self) -> None:
        while not self._stop.is_set():
            if not os.path.exists(BATCTL):
                self._set_status("unavailable", f"{BATCTL} not installed")
                if self._stop.wait(POLL_INTERVAL_S):
                    return
                continue
            try:
                result = subprocess.run(
                    [BATCTL, "o", "-nH"],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                    check=False,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
                self._set_status("error", str(exc))
                if self._stop.wait(POLL_INTERVAL_S):
                    return
                continue

            if result.returncode != 0:
                self._set_status("error", f"batctl rc={result.returncode}")
            else:
                self._set_status("running", "")
                for line in result.stdout.splitlines():
                    m = _ORIG_LINE.match(line.strip())
                    if not m:
                        continue
                    mac, _last_seen, tq_str, next_hop = m.groups()
                    try:
                        tq = int(tq_str)
                    except ValueError:
                        continue
                    try:
                        self._on_peer(mac, tq, next_hop)
                    except Exception:  # noqa: BLE001
                        pass

            if self._stop.wait(POLL_INTERVAL_S):
                return


def attach(on_peer: Callable[[str, int, str], None]) -> WifiBridge:
    bridge = WifiBridge(on_peer)
    bridge.start()
    return bridge
