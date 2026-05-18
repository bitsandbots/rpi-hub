"""Unit tests for the mesh control plane.

We exercise:
- Identity generation + idempotence
- Peer table CRUD + replay-protection
- Message canonicalisation + signature round-trip (stub mode)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mesh.signal_mesh import identity, messages, peers


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
    # Real Ed25519 round trip when cryptography is installed; the stub
    # path verifies any same-length signature against the public key.
    try:
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
    except ImportError:
        priv_bytes = b"\x00" * 32
        pub_bytes = b"\x01" * 32

    payload = messages.canonical_bytes(
        {"kind": "presence", "sender": "x", "seq": 1, "body": {}}
    )
    sig = messages.sign(priv_bytes, payload)
    assert messages.verify(pub_bytes, payload, sig)


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
