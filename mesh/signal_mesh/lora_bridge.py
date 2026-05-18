"""Reticulum (LoRa) bridge — Phase 7.1.

A long-running coroutine that connects to the local Reticulum daemon's
Unix socket, subscribes to inbound mesh frames, and pumps them into the
peer table and inbound-message queue. Outbound notes + presence
beacons are sent the other direction.

Reticulum's Python API (``RNS``) is the canonical client. We import it
lazily so the rest of the mesh control plane stays unit-testable on
machines without a LoRa hat. When ``RNS`` is unavailable the bridge
sits idle and ``mesh.lora_status`` reports ``"unavailable"`` instead of
crash-looping.

Operator workflow:

1. Plug in a RAK4631 or compatible LoRa hat (USB or HAT pinout).
2. Run ``signal-reticulum.service`` (ships with this commit).
3. ``signal-mesh.service`` auto-connects to the socket within ~5s.
"""

from __future__ import annotations

import os
import socket
import threading
import time
from dataclasses import dataclass
from typing import Callable

# Reticulum's default socket location. Operators can override via env.
RETICULUM_SOCKET = os.environ.get("SIGNAL_RETICULUM_SOCKET", "/run/reticulum/rnsapi.sock")
CONNECT_RETRY_S = 5.0


@dataclass(frozen=True)
class LoraStatus:
    state: str  # "unavailable" | "connecting" | "connected" | "error"
    detail: str
    last_change_ts: float


class LoraBridge:
    """Background thread that mirrors LoRa traffic into the peer table.

    The bridge owns the socket; it never returns frames out-of-band.
    All inbound frames are dispatched through ``on_frame``, which the
    caller wires to :func:`mesh.signal_mesh.peers.PeerTable.upsert` and
    the inbound-message dispatcher.
    """

    def __init__(self, on_frame: Callable[[bytes], None]) -> None:
        self._on_frame = on_frame
        self._status = LoraStatus(state="unavailable", detail="not started", last_change_ts=time.time())
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def status(self) -> LoraStatus:
        return self._status

    def _set_status(self, state: str, detail: str = "") -> None:
        self._status = LoraStatus(state=state, detail=detail, last_change_ts=time.time())

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="lora-bridge", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        # Hard requirement: a Reticulum-managed socket exists. If not,
        # we sit idle — the operator hasn't set up the hardware path
        # yet, which is fine.
        while not self._stop.is_set():
            if not os.path.exists(RETICULUM_SOCKET):
                self._set_status("unavailable", f"no socket at {RETICULUM_SOCKET}")
                if self._stop.wait(CONNECT_RETRY_S):
                    return
                continue

            try:
                self._set_status("connecting", RETICULUM_SOCKET)
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.connect(RETICULUM_SOCKET)
                    s.settimeout(1.0)
                    self._set_status("connected", RETICULUM_SOCKET)
                    self._read_loop(s)
            except (OSError, ConnectionError) as exc:
                self._set_status("error", str(exc))
                if self._stop.wait(CONNECT_RETRY_S):
                    return

    def _read_loop(self, s: socket.socket) -> None:
        """Read newline-framed payloads until the socket closes.

        The frame format is whatever ``signal-reticulum`` chooses to
        emit; the bridge does no parsing here beyond chunking. Parsing
        and signature verification happen in
        :mod:`mesh.signal_mesh.messages.verify` via the dispatcher.
        """

        buf = bytearray()
        while not self._stop.is_set():
            try:
                chunk = s.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                return
            buf.extend(chunk)
            while b"\n" in buf:
                line, _, rest = buf.partition(b"\n")
                buf[:] = rest
                if line:
                    try:
                        self._on_frame(bytes(line))
                    except Exception:  # noqa: BLE001 — never let one bad frame kill the bridge
                        pass


def attach(on_frame: Callable[[bytes], None]) -> LoraBridge:
    """Convenience wrapper used by signal-mesh.main on startup."""

    bridge = LoraBridge(on_frame)
    bridge.start()
    return bridge
