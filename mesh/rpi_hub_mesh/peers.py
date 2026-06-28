"""Peer table — who else is on the mesh.

Stored in-memory for now (the mesh runs on a single host process; peers
re-introduce themselves on every presence-beacon round, so persistence
across restarts is nice-to-have, not required).

Trust state:

* ``unverified`` — discovered, message signature OK, but the owner has
  not marked the peer as trusted. Banner shown on every interaction.
* ``trusted`` — owner scanned the peer's QR fingerprint, called
  ``mark_trusted``, and now sync flows freely.
* ``blocked`` — owner explicitly blocked; messages still verified for
  metrics but never surfaced to the UI.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class TrustState(str, Enum):
    UNVERIFIED = "unverified"
    TRUSTED = "trusted"
    BLOCKED = "blocked"


@dataclass
class Peer:
    fingerprint: str
    display_name: str = ""  # operator-chosen on trust
    trust: TrustState = TrustState.UNVERIFIED
    last_seen_ts: float = field(default_factory=time.time)
    last_rssi: int | None = None  # LoRa RSSI; None for Wi-Fi peers
    last_seq: int = 0  # monotonic per-peer sequence; for replay protection
    radio: str = "lora"  # "lora" | "wifi"
    pubkey: bytes | None = None  # TOFU-pinned Ed25519 public key (None for Wi-Fi/BAT peers)
    seq_seen: bool = False  # True once a real sequence number has been recorded


class PeerTable:
    """In-memory peer table. Thread-safe via the GIL for our small N."""

    def __init__(self) -> None:
        self._by_fp: dict[str, Peer] = {}

    def upsert(self, fingerprint: str, **fields: object) -> Peer:
        peer = self._by_fp.get(fingerprint)
        if peer is None:
            peer = Peer(fingerprint=fingerprint)
            self._by_fp[fingerprint] = peer
        for k, v in fields.items():
            if hasattr(peer, k):
                setattr(peer, k, v)
        peer.last_seen_ts = time.time()
        return peer

    def get(self, fingerprint: str) -> Peer | None:
        return self._by_fp.get(fingerprint)

    def mark_trusted(self, fingerprint: str, display_name: str) -> Peer | None:
        peer = self._by_fp.get(fingerprint)
        if peer is None:
            return None
        peer.trust = TrustState.TRUSTED
        peer.display_name = display_name
        return peer

    def mark_blocked(self, fingerprint: str) -> Peer | None:
        peer = self._by_fp.get(fingerprint)
        if peer is None:
            return None
        peer.trust = TrustState.BLOCKED
        return peer

    def all(self) -> list[Peer]:
        return list(self._by_fp.values())

    def pin_key(self, fingerprint: str, pubkey: bytes) -> bool:
        """Trust-on-first-use key pinning.

        On the first authenticated frame from a fingerprint we record
        its public key. On every later frame the presented key must
        match the pinned one, otherwise we reject — this catches a key
        rotation / impersonation attempt even in the (cryptographically
        improbable) event of a fingerprint prefix collision. Returns
        ``True`` when the key is accepted (newly pinned or matching),
        ``False`` on a mismatch.
        """

        peer = self._by_fp.get(fingerprint)
        if peer is None:
            peer = Peer(fingerprint=fingerprint, pubkey=pubkey)
            self._by_fp[fingerprint] = peer
            return True
        if peer.pubkey is None:
            peer.pubkey = pubkey
            return True
        return peer.pubkey == pubkey

    def accept_sequence(self, fingerprint: str, seq: int) -> bool:
        """Replay-protection check.

        Mesh messages carry a monotonically increasing per-node sequence
        number. If the inbound seq is not strictly greater than the last
        recorded one, we drop the message (likely a replay or stale
        rebroadcast). The first sequence seen from a peer IS recorded, so
        that very first frame cannot be replayed afterwards.
        """

        peer = self._by_fp.get(fingerprint)
        if peer is None:
            peer = Peer(fingerprint=fingerprint, last_seq=seq, seq_seen=True)
            self._by_fp[fingerprint] = peer
            return True
        if peer.seq_seen and seq <= peer.last_seq:
            return False
        peer.last_seq = seq
        peer.seq_seen = True
        return True
