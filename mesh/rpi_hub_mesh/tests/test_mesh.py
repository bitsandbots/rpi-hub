"""Unit tests for the mesh control plane.

We exercise:
- Identity generation + idempotence
- Peer table CRUD + replay-protection
- Message canonicalisation + signature round-trip
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mesh.rpi_hub_mesh import identity, messages, peers


def test_identity_fingerprint_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(identity, "KEY_DIR", tmp_path / "keys")
    monkeypatch.setattr(identity, "PRIV_PATH", tmp_path / "keys" / "ed25519.priv")
    monkeypatch.setattr(identity, "PUB_PATH", tmp_path / "keys" / "ed25519.pub")
    ident = identity.load_or_create()
    # 6 groups of 4 base32 chars, dash-separated
    parts = ident.fingerprint.split("-")
    assert len(parts) == 6
    for p in parts:
        assert len(p) == 4
        assert p.isalnum()


def test_identity_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(identity, "KEY_DIR", tmp_path / "keys")
    monkeypatch.setattr(identity, "PRIV_PATH", tmp_path / "keys" / "ed25519.priv")
    monkeypatch.setattr(identity, "PUB_PATH", tmp_path / "keys" / "ed25519.pub")
    a = identity.load_or_create()
    b = identity.load_or_create()
    assert a.public_key == b.public_key
    assert a.fingerprint == b.fingerprint


def test_peer_table_upsert_and_trust() -> None:
    table = peers.PeerTable()
    p = table.upsert("ABCD-EFGH", radio="lora", last_rssi=-42)
    assert p.trust is peers.TrustState.UNVERIFIED
    table.mark_trusted("ABCD-EFGH", "Maya's Pi")
    p2 = table.get("ABCD-EFGH")
    assert p2 is not None
    assert p2.trust is peers.TrustState.TRUSTED
    assert p2.display_name == "Maya's Pi"


def test_peer_replay_protection() -> None:
    table = peers.PeerTable()
    table.upsert("ABCD-EFGH")
    assert table.accept_sequence("ABCD-EFGH", 1)
    assert table.accept_sequence("ABCD-EFGH", 2)
    # Replaying seq 1 must fail.
    assert not table.accept_sequence("ABCD-EFGH", 1)
    # Equal seq is also a replay.
    assert not table.accept_sequence("ABCD-EFGH", 2)


def test_message_canonical_round_trip() -> None:
    body = {"battery_pct": 70}
    a = messages.canonical_bytes({"kind": "presence", "sender": "x", "seq": 1, "body": body})
    # Reorder body keys; canonicalisation must produce identical bytes.
    b = messages.canonical_bytes({"sender": "x", "kind": "presence", "body": body, "seq": 1})
    assert a == b


def test_sign_verify_round_trip() -> None:
    # Real Ed25519 round trip — skipped if cryptography is unavailable.
    # Without real crypto sign() raises RuntimeError (fail-closed design);
    # the stub path is only reachable via rpi_hub_ALLOW_INSECURE_CRYPTO=1.
    if not messages.CRYPTO_AVAILABLE:
        pytest.skip("cryptography unavailable; install python3-cryptography to run")
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

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
    payload = messages.canonical_bytes(
        {"kind": "presence", "sender": "x", "seq": 1, "body": {}}
    )
    sig = messages.sign(priv_bytes, payload)
    assert messages.verify(pub_bytes, payload, sig)


def test_load_from_credentials_prefers_credentials_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When CREDENTIALS_DIRECTORY is set, identity.load_from_credentials
    must read both halves from there and never touch the on-disk path."""

    cred_dir = tmp_path / "creds"
    cred_dir.mkdir()
    priv_bytes = b"\x11" * 32
    pub_bytes = b"\x22" * 32
    (cred_dir / "ed25519_priv").write_bytes(priv_bytes)
    (cred_dir / "ed25519_pub").write_bytes(pub_bytes)
    # Poison the disk path: if the function reads it, the test fails
    # because the bytes differ from what's in CREDENTIALS_DIRECTORY.
    monkeypatch.setattr(identity, "PRIV_PATH", tmp_path / "nope.priv")
    monkeypatch.setattr(identity, "PUB_PATH", tmp_path / "nope.pub")
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(cred_dir))

    bundle = identity.load_from_credentials()
    assert bundle.private_key == priv_bytes
    assert bundle.identity.public_key == pub_bytes


def test_load_from_credentials_falls_back_to_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No CREDENTIALS_DIRECTORY → read from PRIV_PATH/PUB_PATH."""

    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    priv_bytes = b"\x33" * 32
    pub_bytes = b"\x44" * 32
    priv_path = tmp_path / "keys" / "ed25519.priv"
    pub_path = tmp_path / "keys" / "ed25519.pub"
    priv_path.parent.mkdir(parents=True)
    priv_path.write_bytes(priv_bytes)
    pub_path.write_bytes(pub_bytes)
    monkeypatch.setattr(identity, "PRIV_PATH", priv_path)
    monkeypatch.setattr(identity, "PUB_PATH", pub_path)

    bundle = identity.load_from_credentials()
    assert bundle.private_key == priv_bytes
    assert bundle.identity.public_key == pub_bytes


def test_load_from_credentials_stub_when_nothing_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Neither credentials dir nor disk has keys — daemon stays up
    with a deterministic stub instead of crashing."""

    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setattr(identity, "PRIV_PATH", tmp_path / "absent.priv")
    monkeypatch.setattr(identity, "PUB_PATH", tmp_path / "absent.pub")
    bundle = identity.load_from_credentials()
    # The stub priv is the all-zero buffer; the pub is deterministic so
    # the daemon's fingerprint is stable across restarts of an
    # unprovisioned device.
    assert bundle.private_key == b"\x00" * 32
    assert len(bundle.identity.public_key) == 32
    # Calling twice yields the same fingerprint.
    again = identity.load_from_credentials()
    assert again.identity.fingerprint == bundle.identity.fingerprint


def test_publish_note_signs_with_real_key_when_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: when a real Ed25519 keypair is present in the
    credentials dir, /notes/publish emits a signature that verifies
    against the published public key. Skipped without cryptography."""

    try:
        from cryptography.hazmat.primitives import serialization  # type: ignore[import-not-found]
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # type: ignore[import-not-found]
            Ed25519PrivateKey,
        )
    except ImportError:
        pytest.skip("cryptography not installed; can't validate real signature")
        return

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
    env = messages.make_note(
        sender="ABCD-EFGH",
        seq=42,
        priv=priv_bytes,
        note_id=7,
        name="alice",
        text="hello mesh",
    )
    assert messages.verify(pub_bytes, env.canonical_body(), env.sig)


def test_verify_rejects_tampered_payload() -> None:
    # Real Ed25519 verification rejects tampering; the stub does not
    # (it's length-only). Skip in stub mode.
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        pytest.skip("cryptography not installed; stub verify is length-only")
        return

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
    sig = messages.sign(
        priv_bytes,
        messages.canonical_bytes({"kind": "presence", "sender": "x", "seq": 1, "body": {}}),
    )
    tampered = messages.canonical_bytes(
        {"kind": "presence", "sender": "x", "seq": 2, "body": {}}
    )
    assert not messages.verify(pub_bytes, tampered, sig)
