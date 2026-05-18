"""Ed25519 identity for this node.

The keypair is generated once on first boot (signal-mesh.service's
ExecStartPre) and pinned at ``/var/lib/signal/keys/`` with mode 0600.
The public-key fingerprint is what an operator scans to mark a peer as
trusted — short, base32, six groups of four chars.

Cryptography uses ``cryptography`` (a dep we'd add to install.sh's
apt-install line) when available; we degrade to a stub that produces
deterministic fake signatures so the rest of the service is testable
on dev machines without the library.
"""

from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

KEY_DIR = Path("/var/lib/signal/keys")
PRIV_PATH = KEY_DIR / "ed25519.priv"
PUB_PATH = KEY_DIR / "ed25519.pub"


@dataclass(frozen=True)
class Identity:
    public_key: bytes
    fingerprint: str  # base32, grouped, no padding


def _fingerprint(pub: bytes) -> str:
    """Short base32 fingerprint of a 32-byte public key.

    We take the first 15 bytes of SHA-256(pubkey) → 24 base32 chars →
    six groups of four for readability. That's 120 bits of entropy,
    plenty to resist accidental collisions on a small mesh.
    """

    h = hashlib.sha256(pub).digest()[:15]
    b32 = base64.b32encode(h).decode("ascii").rstrip("=")
    return "-".join(b32[i : i + 4] for i in range(0, len(b32), 4))


def load_or_create() -> Identity:
    """Return the local identity, generating it on first run.

    Idempotent: if the keys already exist on disk we just read them.
    The cryptography dep is optional; without it we generate a fake
    "key" (32 random bytes) so the service can boot on dev. Production
    deployments install python3-cryptography via apt.
    """

    KEY_DIR.mkdir(parents=True, exist_ok=True)
    try:
        priv_bytes = PRIV_PATH.read_bytes()
        pub_bytes = PUB_PATH.read_bytes()
        return Identity(public_key=pub_bytes, fingerprint=_fingerprint(pub_bytes))
    except FileNotFoundError:
        pass

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # type: ignore[import-not-found]
            Ed25519PrivateKey,
        )
        from cryptography.hazmat.primitives import serialization  # type: ignore[import-not-found]

        priv = Ed25519PrivateKey.generate()
        priv_bytes = priv.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_bytes = priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    except ImportError:
        # Stub path. Two 32-byte random buffers — the API surface above
        # still works for tests, but signatures are not real Ed25519.
        priv_bytes = os.urandom(32)
        pub_bytes = hashlib.sha256(priv_bytes).digest()

    PRIV_PATH.write_bytes(priv_bytes)
    PRIV_PATH.chmod(0o600)
    PUB_PATH.write_bytes(pub_bytes)
    PUB_PATH.chmod(0o644)
    return Identity(public_key=pub_bytes, fingerprint=_fingerprint(pub_bytes))
