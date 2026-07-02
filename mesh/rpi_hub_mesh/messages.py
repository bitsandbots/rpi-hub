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
import logging
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

_log = logging.getLogger(__name__)


def _insecure_crypto_allowed() -> bool:
    """True only when the caller has explicitly opted into the dev stub."""
    return os.environ.get("rpi_hub_ALLOW_INSECURE_CRYPTO") == "1"


try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey as _Chk,  # noqa: F401  # type: ignore[import-not-found]
    )

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    _log.warning(
        "cryptography library unavailable — mesh signatures use an insecure stub. "
        "Signatures cannot be verified. Install python3-cryptography before deploying."
    )


class MessageKind(StrEnum):
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
    pub: str = ""  # base64 sender public key; transport-only, NOT signed

    def canonical_body(self) -> bytes:
        """Canonical bytes the signature must cover.

        ``pub`` and ``ts`` are deliberately excluded — the signature
        covers identity-bound, replay-bound content only. The receiver
        re-derives the fingerprint from ``pub`` and checks it equals
        ``sender`` separately (see ``identity.fingerprint_of``), so an
        attacker cannot swap the key without breaking that binding.
        """

        return canonical_bytes(
            {
                "kind": self.kind,
                "sender": self.sender,
                "seq": self.seq,
                "body": self.body,
            }
        )


def canonical_bytes(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign(priv_key: bytes, payload: bytes) -> str:
    """Return a base64 signature. Falls back to a hash-MAC stub when
    Ed25519 isn't available — see identity.load_or_create for why.
    """

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: PLC0415
            Ed25519PrivateKey,
        )

        key = Ed25519PrivateKey.from_private_bytes(priv_key)
        sig = key.sign(payload)
    except ImportError:
        if not _insecure_crypto_allowed():
            raise RuntimeError(
                "cryptography unavailable; set rpi_hub_ALLOW_INSECURE_CRYPTO=1 for dev use"
            ) from None
        # Deterministic stub for dev. Not a real signature.
        sig = hashlib.blake2b(priv_key + payload, digest_size=64).digest()
    return base64.b64encode(sig).decode("ascii")


def verify(pub_key: bytes, payload: bytes, sig_b64: str) -> bool:
    try:
        sig = base64.b64decode(sig_b64)
    except (ValueError, TypeError):
        return False
    try:
        from cryptography.exceptions import (  # noqa: PLC0415
            InvalidSignature,
        )
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: PLC0415
            Ed25519PublicKey,
        )

        pub = Ed25519PublicKey.from_public_bytes(pub_key)
        try:
            pub.verify(sig, payload)
        except InvalidSignature:
            return False
        return True
    except ImportError:
        if not _insecure_crypto_allowed():
            # Fail closed: without real Ed25519 the trust model is broken.
            # Set rpi_hub_ALLOW_INSECURE_CRYPTO=1 to use the dev stub instead.
            # See P2 in docs/GAP_ANALYSIS.md §4 for the decision rationale.
            return False
        # Dev stub: accepts any signature of the expected length — cannot
        # truly verify without the private key. Opt-in only via env var above.
        expected = hashlib.blake2b(pub_key + payload, digest_size=64).digest()
        return len(sig) == len(expected)


def make_presence(
    sender: str, seq: int, priv: bytes, battery_pct: int | None = None, pub: str = ""
) -> Envelope:
    body = {"battery_pct": battery_pct}
    payload = canonical_bytes({"kind": "presence", "sender": sender, "seq": seq, "body": body})
    return Envelope(
        kind="presence", sender=sender, seq=seq, ts=0.0, body=body, sig=sign(priv, payload), pub=pub
    )


def make_note(
    sender: str,
    seq: int,
    priv: bytes,
    note_id: int,
    name: str,
    text: str,
    ttl_s: int = 86400,
    pub: str = "",
) -> Envelope:
    body = {"note_id": note_id, "name": name, "text": text, "ttl_s": ttl_s}
    payload = canonical_bytes({"kind": "note", "sender": sender, "seq": seq, "body": body})
    return Envelope(
        kind="note", sender=sender, seq=seq, ts=0.0, body=body, sig=sign(priv, payload), pub=pub
    )


def make_index(sender: str, seq: int, priv: bytes, zims: list[str], pub: str = "") -> Envelope:
    body = {"zims": sorted(zims)}
    payload = canonical_bytes({"kind": "index", "sender": sender, "seq": seq, "body": body})
    return Envelope(
        kind="index", sender=sender, seq=seq, ts=0.0, body=body, sig=sign(priv, payload), pub=pub
    )


def verify_envelope(  # noqa: PLR0911 (strict envelope validation requires multiple exit paths)
    env: dict[str, Any],
) -> Envelope | None:
    """Authenticate one decoded inbound envelope; return it or ``None``.

    Enforces the trust model the blueprint claims ("signed envelopes")
    and which was previously produced but never checked on receive:

    1. ``pub``/``sender``/``sig``/``body`` are present and well-typed.
    2. ``fingerprint_of(pub) == sender`` — the claimed identity is
       cryptographically bound to the presented key (120-bit fingerprint
       over SHA-256(pub)), so a peer cannot spoof another's fingerprint.
    3. The Ed25519 signature verifies over the canonical body. This
       fails closed when the ``cryptography`` library is absent (see
       :func:`verify`), so an unprovisioned dev box drops mesh frames
       rather than trusting them.

    Returns the parsed :class:`Envelope` on success so the caller can
    pin the key and run replay protection; ``None`` on any failure.
    """

    from . import identity  # noqa: PLC0415  (avoid import cycle at module load)

    if not isinstance(env, dict):
        return None
    kind = str(env.get("kind") or "")
    sender = str(env.get("sender") or "")
    sig = str(env.get("sig") or "")
    pub_b64 = str(env.get("pub") or "")
    body = env.get("body")
    if not (kind and sender and sig and pub_b64 and isinstance(body, dict)):
        return None
    try:
        seq = int(env.get("seq") or 0)
    except (TypeError, ValueError):
        return None
    try:
        pub = base64.b64decode(pub_b64, validate=True)
    except (ValueError, TypeError):
        return None
    if identity.fingerprint_of(pub) != sender:
        return None  # claimed fingerprint not bound to presented key
    payload = canonical_bytes({"kind": kind, "sender": sender, "seq": seq, "body": body})
    if not verify(pub, payload, sig):
        return None  # bad / unverifiable signature (fails closed)
    return Envelope(
        kind=kind,
        sender=sender,
        seq=seq,
        ts=float(env.get("ts") or 0.0),
        body=body,
        sig=sig,
        pub=pub_b64,
    )
