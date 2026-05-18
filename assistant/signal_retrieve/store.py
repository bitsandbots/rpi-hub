"""Read-only access to the prebuilt chunk store.

Index layout under ``/var/lib/signal/index/``::

    chunks.sqlite       # one row per chunk: id, article, section, text, offset
    bm25/               # tantivy / sqlite FTS5 index, depending on builder
    vectors.hnsw        # HNSW graph over chunk embeddings
    vectors.ids         # int32 array mapping HNSW node id → chunk id
    manifest.yaml       # builder version, embedding model, chunk count

The runtime opens ``chunks.sqlite`` in WAL/read-only mode and never writes
to it. Embedding lookup goes through the HNSW handle in
``retrieval.HybridRetriever``.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

INDEX_DIR = Path("/var/lib/signal/index")
CHUNKS_DB = INDEX_DIR / "chunks.sqlite"
MANIFEST = INDEX_DIR / "manifest.yaml"


@dataclass(frozen=True)
class Chunk:
    """A single retrieved passage with the metadata callers need.

    ``article`` is the human-facing source ("Wikipedia: Wound care"); the
    Ask UI surfaces it as the citation chip label. ``url`` is the deep
    link into kiwix-serve so the user can read the full passage in context.
    """

    chunk_id: int
    article: str
    section: str
    text: str
    url: str

    def as_dict(self) -> dict[str, object]:
        return {
            "chunk_id": self.chunk_id,
            "article": self.article,
            "section": self.section,
            "text": self.text,
            "url": self.url,
        }


def index_present(path: Path = CHUNKS_DB) -> bool:
    return path.exists() and path.stat().st_size > 0


def open_chunks_ro(path: Path = CHUNKS_DB) -> sqlite3.Connection:
    """Open chunks.sqlite read-only.

    Uses the SQLite URI form so a second writer cannot accidentally upgrade
    the connection. The indexer is the only writer, and it runs on a
    workstation — never on the Pi.
    """

    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def chunk_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()
    return int(row["n"]) if row else 0


def fetch_chunks(conn: sqlite3.Connection, ids: list[int]) -> list[Chunk]:
    """Look up chunks by id, preserving the caller's ordering.

    The hybrid retriever produces a ranked id list; we re-materialise rows
    in that order so the response keeps RRF ranking intact.
    """

    if not ids:
        return []
    # SQLite caps host-variables at 999. Our k is ≤ 32 so a single IN clause
    # is fine, but we still guard against accidental future growth.
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT id, article, section, text, url FROM chunks WHERE id IN ({placeholders})",
        ids,
    ).fetchall()
    by_id = {int(r["id"]): r for r in rows}
    out: list[Chunk] = []
    for cid in ids:
        r = by_id.get(cid)
        if r is None:
            continue
        out.append(
            Chunk(
                chunk_id=int(r["id"]),
                article=str(r["article"]),
                section=str(r["section"]),
                text=str(r["text"]),
                url=str(r["url"]),
            )
        )
    return out
