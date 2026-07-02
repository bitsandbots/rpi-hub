"""End-to-end: ``POST /api/notes`` triggers a signed publish to mesh.

GAP §5 callout: ``test_publish_note_signs_with_real_key_when_available``
covers the signing helper in isolation, but never drives the
cross-service hop. A regression in :mod:`rpi_hub_notes.mesh_client`
would leave notes failing to fan out to mesh without a journalctl
entry — silent, unobservable, untested.

This test:

* Stands up the notes FastAPI app with a tmp SQLite db (reusing the
  fixture pattern from test_notes.py).
* Monkeypatches :func:`rpi_hub_notes.mesh_client.publish` to capture
   what would have hit ``rpi-hub-mesh /notes/publish``.
 * Asserts the payload shape matches what rpi-hub-mesh's PublishNoteIn
  pydantic model expects, AND that the user-supplied text round-trips.

We deliberately don't spin up a real mesh app — that's what
``test_publish_note_signs_with_real_key_when_available`` does. Here
we exercise the *handoff*: notes-app → mesh_client → outbound URL.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from notes.rpi_hub_notes import main, mesh_client, storage


@pytest.fixture
def app_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Mirror the fixture in test_notes.py: tmp db + tmp owner token.

    We also wrap ``storage.open_db`` so the default-arg path (captured
    at function-definition time as ``DEFAULT_DB``) is overridden with
    a tmp_path location. Patching the module-level ``DEFAULT_DB`` alone
    doesn't rebind the default argument.
    """

    db = tmp_path / "notes.sqlite"
    monkeypatch.setattr(storage, "DEFAULT_DB", db)
    _real_open_db = storage.open_db
    monkeypatch.setattr(storage, "open_db", lambda path=db: _real_open_db(path))
    monkeypatch.setattr(main, "_CONN", None)
    token_file = tmp_path / "token"
    token_file.write_text("super-secret-owner\n")
    monkeypatch.setattr(main, "OWNER_TOKEN_PATH", token_file)
    return TestClient(main.app)


@pytest.fixture
def capture_publish(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    """Replace mesh_client.publish with a recorder.

    The notes app imports ``mesh_client`` once at module load and
    calls ``mesh_client.publish(...)``; patching the function on the
    module is therefore sufficient — we don't need to rebind the
    attribute on ``main`` too.
    """

    calls: list[dict[str, object]] = []

    def fake_publish(note_id: int, name: str, text: str, ttl_s: int = 86400) -> bool:
        calls.append({"note_id": note_id, "name": name, "text": text, "ttl_s": ttl_s})
        return True

    monkeypatch.setattr(mesh_client, "publish", fake_publish)
    return calls


def test_post_note_handoff_to_mesh(
    app_client: TestClient, capture_publish: list[dict[str, object]]
) -> None:
    r = app_client.post("/notes", json={"text": "water at the church", "name": "Maya"})
    assert r.status_code == 201
    note = r.json()

    assert len(capture_publish) == 1
    call = capture_publish[0]
    # Same fields the signed-payload integration test on the mesh side
    # asserts (PublishNoteIn in mesh/rpi_hub_mesh/main.py).
    assert call["note_id"] == note["id"]
    assert call["name"] == "Maya"
    assert call["text"] == "water at the church"
    # Default TTL — 24h. The mesh service caps it at 7 days; the notes
    # app currently sends the default and never lets the user override.
    assert call["ttl_s"] == 86400


def test_post_note_handoff_fires_after_validation(
    app_client: TestClient, capture_publish: list[dict[str, object]]
) -> None:
    """Empty notes must 400 *and* skip the mesh hop — otherwise we'd
    fan out junk over the radio for every typo."""

    r = app_client.post("/notes", json={"text": "    "})
    assert r.status_code == 400
    assert capture_publish == []


def test_post_note_handoff_continues_when_mesh_returns_false(
    app_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A False return from the mesh client (e.g. rpi-hub-mesh down)
    must not break the local POST — the notes board is the canonical
    store; the mesh is best-effort."""

    def fail(*_: object, **__: object) -> bool:
        return False

    monkeypatch.setattr(mesh_client, "publish", fail)
    r = app_client.post("/notes", json={"text": "first"})
    assert r.status_code == 201


def test_mesh_client_payload_shape_via_real_urlopen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sanity-check the wire format mesh_client.publish actually emits.

    We intercept ``urllib.request.urlopen`` and capture the Request
    bytes — that's the JSON rpi-hub-mesh's pydantic model parses.
    This complements the test above (which intercepts at the
    function boundary) by validating the JSON shape too.
    """

    captured: dict[str, object] = {}

    class _FakeResp:
        status = 200

        def __enter__(self) -> _FakeResp:
            return self

        def __exit__(self, *_: object) -> None:
            return None

    def fake_urlopen(req: object, timeout: float = 0.0) -> _FakeResp:  # noqa: ARG001
        captured["url"] = req.full_url  # type: ignore[attr-defined]
        captured["body"] = req.data  # type: ignore[attr-defined]
        captured["content_type"] = req.headers.get("Content-type")  # type: ignore[attr-defined]
        return _FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    ok = mesh_client.publish(7, "alice", "hello mesh", ttl_s=3600)
    assert ok is True
    assert captured["url"] == mesh_client.MESH_PUBLISH_URL
    assert captured["content_type"] == "application/json"
    assert isinstance(captured["body"], bytes | bytearray)
    payload = json.loads(bytes(captured["body"]).decode("utf-8"))
    assert payload == {
        "note_id": 7,
        "name": "alice",
        "text": "hello mesh",
        "ttl_s": 3600,
    }
