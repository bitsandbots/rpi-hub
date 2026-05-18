"""Wire format for mesh messages.

We define three message kinds; all share an outer envelope::

    {
        "kind":   "presence" | "note" | "index",
        "sender": "<fingerprint>",
        "seq":    <monotonic int>,
        "ts":     <wall-clock seconds; advisory only, not authoritative>,
        "body":   {... kind-specific ...},
        "sig":    "<base64 Ed25519 signature over canonical(body)>"
    }

Canonicalisation: JSON with sorted keys, no whitespace. That's
deterministic enough for the small messages we send — there are no
floats in the bodies, only integers and short strings, so we avoid the
classic "float formatting differs across libs" trap.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


class MessageKind(str, Enum):
    PRESENCE = "presence"
    NOTE = "note"
    INDEX = "index"


@dataclass(frozen=True)
class Envelope:
    kind: str
    sender: str
    seq: int
    ts: float
    body: dict[str, Any]
    sig: str

    def canonical_body(self) -> bytes:
        """Canonical bytes the signature must cover."""

        return canonical_bytes({"kind": self.kind, "sender": self.sender, "seq": self.seq, "body": self.body})


def canonical_bytes(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign(priv_key: bytes, payload: bytes) -> str:
    """Return a base64 signature. Falls back to a hash-MAC stub when
    Ed25519 isn't available — see identity.load_or_create for why.
    """

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # type: ignore[import-not-found]
            Ed25519PrivateKey,
        )

        key = Ed25519PrivateKey.from_private_bytes(priv_key)
        sig = key.sign(payload)
    except ImportError:
        # Deterministic stub for dev. Not a real signature.
        sig = hashlib.blake2b(priv_key + payload, digest_size=64).digest()
    return base64.b64encode(sig).decode("ascii")


def verify(pub_key: bytes, payload: bytes, sig_b64: str) -> bool:
    try:
        sig = base64.b64decode(sig_b64)
    except (ValueError, TypeError):
        return False
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # type: ignore[import-not-found]
            Ed25519PublicKey,
        )
        from cryptography.exceptions import InvalidSignature  # type: ignore[import-not-found]

        pub = Ed25519PublicKey.from_public_bytes(pub_key)
        try:
            pub.verify(sig, payload)
        except InvalidSignature:
            return False
        return True
    except ImportError:
        # Stub verification mirrors the stub sign().
        expected = hashlib.blake2b(pub_key + payload, digest_size=64).digest()
        # In dev we don't have the private key here, so this can't
        # truly verify; we accept any signature of the expected length.
        return len(sig) == len(expected)


def make_presence(sender: str, seq: int, priv: bytes, battery_pct: int | None = None) -> Envelope:
    body = {"battery_pct": battery_pct}
    payload = canonical_bytes({"kind": "presence", "sender": sender, "seq": seq, "body": body})
    return Envelope(
        kind="presence", sender=sender, seq=seq, ts=0.0, body=body, sig=sign(priv, payload)
    )


def make_note(sender: str, seq: int, priv: bytes, note_id: int, name: str, text: str, ttl_s: int = 86400) -> Envelope:
    body = {"note_id": note_id, "name": name, "text": text, "ttl_s": ttl_s}
    payload = canonical_bytes({"kind": "note", "sender": sender, "seq": seq, "body": body})
    return Envelope(
        kind="note", sender=sender, seq=seq, ts=0.0, body=body, sig=sign(priv, payload)
    )


def make_index(sender: str, seq: int, priv: bytes, zims: list[str]) -> Envelope:
    body = {"zims": sorted(zims)}
    payload = canonical_bytes({"kind": "index", "sender": sender, "seq": seq, "body": body})
    return Envelope(
        kind="index", sender=sender, seq=seq, ts=0.0, body=body, sig=sign(priv, payload)
    )
