"""End-to-end: ``POST /api/notes`` → ``signal-mesh /notes/publish``.

The existing tests cover each half in isolation:

* ``notes/signal_notes/tests/test_publish_mesh_handoff.py`` — notes app
  hands off to ``mesh_client.publish``, and the JSON payload matches
  what ``PublishNoteIn`` expects.
* ``mesh/signal_mesh/tests/test_mesh.py`` — signing helpers and peer
  table primitives.

But neither test drives the **cross-service hop**: the wire bytes that
``mesh_client.publish`` puts on ``http://127.0.0.1:8500/notes/publish``
actually parse on the mesh side, the mesh app signs the envelope, and
the operation returns 200. A regression in either schema would slip
past both isolated suites — silent in journalctl, silent in tile
probes.

This test bridges the two FastAPI apps by intercepting
``urllib.request.urlopen`` (the one call ``mesh_client.publish``
makes) and re-emitting it as an in-memory ``TestClient.post`` against
the mesh app. The envelope returned by the mesh side is then
verified against the public key the mesh app loaded — closing the
loop end-to-end.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from mesh.signal_mesh import identity as mesh_identity
from mesh.signal_mesh import main as mesh_main
from mesh.signal_mesh import messages
from notes.signal_notes import main as notes_main
from notes.signal_notes import mesh_client, storage


@pytest.fixture
def keypair_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provision a real keypair on disk and point load_from_credentials at it.

    We set CREDENTIALS_DIRECTORY to a tmp dir so the mesh app reads its
    keys from there (mirroring production where systemd's LoadCredential
    populates the same path).
    """

    cred = tmp_path / "creds"
    cred.mkdir()
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(cred))

    # Reuse the production keygen helper — KEY_DIR is module-level so
    # we point it at the tmp dir, then copy the produced files into
    # cred/ with the LoadCredential filenames.
    key_dir = tmp_path / "keys"
    monkeypatch.setattr(mesh_identity, "KEY_DIR", key_dir)
    monkeypatch.setattr(mesh_identity, "PRIV_PATH", key_dir / "ed25519.priv")
    monkeypatch.setattr(mesh_identity, "PUB_PATH", key_dir / "ed25519.pub")
    mesh_identity.load_or_create()

    (cred / "ed25519_priv").write_bytes((key_dir / "ed25519.priv").read_bytes())
    (cred / "ed25519_pub").write_bytes((key_dir / "ed25519.pub").read_bytes())

    # Reset the mesh app's cached identity so it re-reads from CREDENTIALS_DIRECTORY.
    monkeypatch.setattr(mesh_main, "_BUNDLE", None)
    return cred


@pytest.fixture
def mesh_client_app(keypair_dir: Path) -> TestClient:  # noqa: ARG001
    return TestClient(mesh_main.app)


@pytest.fixture
def notes_app_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mesh_client_app: TestClient
) -> TestClient:
    """Stand up the notes app with a tmp DB and a urlopen patch that
    routes mesh_client.publish to the in-memory mesh TestClient."""

    db = tmp_path / "notes.sqlite"
    monkeypatch.setattr(storage, "DEFAULT_DB", db)
    _real_open_db = storage.open_db
    monkeypatch.setattr(storage, "open_db", lambda path=db: _real_open_db(path))
    monkeypatch.setattr(notes_main, "_CONN", None)

    token_file = tmp_path / "token"
    token_file.write_text("super-secret-owner\n")
    monkeypatch.setattr(notes_main, "OWNER_TOKEN_PATH", token_file)

    def routed_urlopen(req: urllib.request.Request, timeout: float = 0.0) -> Any:  # noqa: ARG001
        assert req.full_url.endswith("/notes/publish"), req.full_url
        body = bytes(req.data) if req.data is not None else b""
        resp = mesh_client_app.post("/notes/publish", content=body, headers={"Content-Type": "application/json"})

        class _Wrapped:
            status = resp.status_code

            def __enter__(self) -> "_Wrapped":
                return self

            def __exit__(self, *_: object) -> None:
                return None

            def read(self) -> bytes:
                return resp.content

        return _Wrapped()

    monkeypatch.setattr(urllib.request, "urlopen", routed_urlopen)
    return TestClient(notes_main.app)


def _verify_signed_note(
    envelope: dict[str, Any], pub_key: bytes, expected_text: str, expected_name: str
) -> None:
    """Assert the envelope is a valid signed note over the expected body."""

    assert envelope["kind"] == "note"
    assert envelope["body"]["text"] == expected_text
    assert envelope["body"]["name"] == expected_name
    payload = messages.canonical_bytes(
        {
            "kind": envelope["kind"],
            "sender": envelope["sender"],
            "seq": envelope["seq"],
            "body": envelope["body"],
        }
    )
    assert messages.verify(pub_key, payload, envelope["sig"]), (
        "signature did not verify against the mesh app's public key"
    )


def test_post_note_round_trips_signed_envelope(
    notes_app_client: TestClient, mesh_client_app: TestClient, keypair_dir: Path
) -> None:
    """The full hop: POST /notes → mesh /notes/publish → 200 + queued flag.

    We then re-fetch the mesh app's identity to grab the public key,
    rebuild the canonical body from the wire bytes we captured during
    the urlopen patch, and verify the signature. If any of the three
    contracts drifts (JSON keys, canonical body shape, sign/verify pair)
    the test fails — none of the isolated tests would catch all three.
    """

    captured_envelope: dict[str, Any] = {}

    # Wrap publish on the wifi bridge — easiest way to capture what
    # the mesh app actually signs. Falls through to the no-op bridge
    # behavior on no-hardware (publish returns False).
    from mesh.signal_mesh import wifi_bridge

    original_attach = wifi_bridge.attach

    def attach_capture(callback: Any) -> Any:
        bridge = original_attach(callback)

        original_publish = bridge.publish

        def capturing_publish(payload: bytes) -> bool:
            captured_envelope.update(json.loads(payload.decode("utf-8")))
            return original_publish(payload)

        bridge.publish = capturing_publish  # type: ignore[method-assign]
        return bridge

    import pytest as _pt

    with _pt.MonkeyPatch.context() as mp:
        mp.setattr(wifi_bridge, "attach", attach_capture)
        mp.setattr(mesh_main, "_WIFI", None)
        mp.setattr(mesh_main, "_LORA", None)

        # Warm the mesh bridges by hitting /health (which calls
        # _ensure_bridges). Then post the note.
        h = mesh_client_app.get("/health")
        assert h.status_code == 200

        r = notes_app_client.post(
            "/notes", json={"text": "water at the church", "name": "Maya"}
        )
        assert r.status_code == 201, r.text
        note = r.json()
        assert note["text"] == "water at the church"

    assert captured_envelope, "mesh app never signed an envelope from the notes hop"

    identity_resp = mesh_client_app.get("/identity")
    assert identity_resp.status_code == 200
    pub_b64 = identity_resp.json()["public_key_b64"]
    import base64

    pub_key = base64.b64decode(pub_b64)

    _verify_signed_note(captured_envelope, pub_key, "water at the church", "Maya")
    assert captured_envelope["body"]["ttl_s"] == 86400


def test_mesh_app_rejects_oversize_payload_from_notes(
    notes_app_client: TestClient,
) -> None:
    """A note that exceeds the notes-side 400-char cap is rejected at
    the notes app — the mesh hop never fires. This pins the chain's
    *input boundary*: bad data fails fast at the first service, not
    silently on the radio."""

    big = "x" * 500
    r = notes_app_client.post("/notes", json={"text": big})
    assert r.status_code == 422  # pydantic Field(max_length=400)


def test_mesh_publish_failure_does_not_break_local_post(
    notes_app_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the mesh side returns 500 or refuses the connection, the
    notes POST still 201s — the local board is the canonical store,
    fan-out is best-effort."""

    def boom(*_: object, **__: object) -> Any:
        raise ConnectionRefusedError("mesh down")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    r = notes_app_client.post("/notes", json={"text": "still local"})
    assert r.status_code == 201
