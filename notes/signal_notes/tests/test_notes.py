"""End-to-end tests for the notes board over an in-memory SQLite db."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from notes.signal_notes import main, storage, validation


@pytest.fixture
def app_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db = tmp_path / "notes.sqlite"
    monkeypatch.setattr(storage, "DEFAULT_DB", db)
    # Force re-open on a fresh handle for each test.
    monkeypatch.setattr(main, "_CONN", None)
    token_file = tmp_path / "token"
    token_file.write_text("super-secret-owner\n")
    monkeypatch.setattr(main, "OWNER_TOKEN_PATH", token_file)
    return TestClient(main.app)


def test_clean_text_caps_length() -> None:
    s = "a" * 1000
    out = validation.clean_text(s)
    assert out is not None and len(out) == validation.TEXT_MAX


def test_clean_text_strips_control_chars() -> None:
    assert validation.clean_text("hello\x00world") == "helloworld"
    assert validation.clean_text("   ") is None


def test_post_then_list(app_client: TestClient) -> None:
    r = app_client.post("/notes", json={"text": "water at the church"})
    assert r.status_code == 201
    body = r.json()
    assert body["text"] == "water at the church"

    r2 = app_client.get("/notes")
    assert r2.status_code == 200
    notes = r2.json()["notes"]
    assert len(notes) == 1
    assert notes[0]["text"] == "water at the church"


def test_rate_limit_short_window(app_client: TestClient) -> None:
    r1 = app_client.post("/notes", json={"text": "first"})
    assert r1.status_code == 201
    # Same client IP — second post within 60s must 429.
    r2 = app_client.post("/notes", json={"text": "second"})
    assert r2.status_code == 429
    assert r2.headers.get("Retry-After") == "60"


def test_delete_requires_owner_token(app_client: TestClient) -> None:
    r = app_client.post("/notes", json={"text": "ephemeral"})
    note_id = r.json()["id"]

    # No header → 401.
    r2 = app_client.delete(f"/notes/{note_id}")
    assert r2.status_code == 401

    # Wrong header → 401.
    r3 = app_client.delete(f"/notes/{note_id}", headers={"X-Owner-Token": "nope"})
    assert r3.status_code == 401

    # Correct → 204.
    r4 = app_client.delete(f"/notes/{note_id}", headers={"X-Owner-Token": "super-secret-owner"})
    assert r4.status_code == 204


def test_wipe_owner_only(app_client: TestClient) -> None:
    app_client.post("/notes", json={"text": "n1"})
    # Manually bump the IP via header so rate-limit doesn't block us.
    app_client.post("/notes", json={"text": "n2"}, headers={"X-Real-IP": "10.0.0.2"})
    r = app_client.post("/notes/wipe", headers={"X-Owner-Token": "super-secret-owner"})
    assert r.status_code == 200
    assert r.json()["wiped"] >= 2
    r2 = app_client.get("/notes")
    assert r2.json()["notes"] == []


def test_empty_text_rejected(app_client: TestClient) -> None:
    r = app_client.post("/notes", json={"text": "    "})
    assert r.status_code == 400


def test_name_displayed_separately(app_client: TestClient) -> None:
    r = app_client.post("/notes", json={"text": "meet at 6", "name": "Maya"})
    note = r.json()
    assert note["name"] == "Maya"
    assert note["text"] == "meet at 6"


def test_health(app_client: TestClient) -> None:
    r = app_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert "note_count" in body
