"""End-to-end test for the /retrieve endpoint over an in-memory sqlite db.

We bypass FTS5 / HNSW by monkeypatching the two lane functions. The point
of this test is the *plumbing* — that retrieval.py, store.py, and
main.py compose into a sane HTTP response — not the search quality
itself, which is gated by the eval harness in Phase 6.2.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from assistant.rpi_pod_retrieve import main, retrieval, store


@pytest.fixture
def index_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db = tmp_path / "chunks.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE chunks ("
        "id INTEGER PRIMARY KEY, article TEXT, section TEXT, "
        "text TEXT, url TEXT)"
    )
    conn.executemany(
        "INSERT INTO chunks VALUES (?, ?, ?, ?, ?)",
        [
            (1, "Wound care", "Cleaning", "Irrigate the wound with clean water.", "/library/A#1"),
            (2, "Wound care", "Dressing", "Apply a sterile dressing.", "/library/A#2"),
            (3, "Burn care", "Cooling", "Cool the burn under running water.", "/library/B#1"),
        ],
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(store, "CHUNKS_DB", db)
    return db


def test_health_reports_chunk_count(index_db: Path) -> None:
    client = TestClient(main.app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert body["chunk_count"] == 3


def test_health_empty_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(store, "CHUNKS_DB", tmp_path / "missing.sqlite")
    client = TestClient(main.app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ready"] is False


def test_retrieve_returns_ranked_chunks(
    index_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Pin both lanes so the test doesn't depend on FTS5 or hnswlib being
    # installed. BM25 lane returns [1, 2]; vector lane returns [3, 1].
    monkeypatch.setattr(retrieval, "bm25_search", lambda conn, q, n: [1, 2])
    monkeypatch.setattr(
        main, "_embed_query", lambda q: [0.1] * 384  # type: ignore[attr-defined]
    )
    monkeypatch.setattr(retrieval, "vector_search", lambda *args, **kw: [3, 1])

    client = TestClient(main.app)
    r = client.get("/retrieve?q=wound&k=3")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert {res["chunk_id"] for res in body["results"]} == {1, 2, 3}
    # chunk 1 appears in both lanes — should rank above the others.
    assert body["results"][0]["chunk_id"] == 1
    assert body["confidence"] > 0.0


def test_retrieve_bm25_only_when_embed_fails(
    index_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(retrieval, "bm25_search", lambda conn, q, n: [1])

    def boom(_q: str) -> list[float]:
        raise RuntimeError("embedding service down")

    monkeypatch.setattr(main, "_embed_query", boom)  # type: ignore[attr-defined]

    client = TestClient(main.app)
    r = client.get("/retrieve?q=wound")
    assert r.status_code == 200
    body = r.json()
    assert [res["chunk_id"] for res in body["results"]] == [1]


def test_retrieve_no_index_returns_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store, "CHUNKS_DB", tmp_path / "nope.sqlite")
    client = TestClient(main.app)
    r = client.get("/retrieve?q=anything")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is False
    assert body["results"] == []
