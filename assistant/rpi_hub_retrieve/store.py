"""Read-only access to the prebuilt chunk store.

Index layout under ``/var/lib/rpi-hub/index/``::

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

INDEX_DIR = Path("/var/lib/rpi-hub/index")
CHUNKS_DB = INDEX_DIR / "chunks.sqlite"
MANIFEST = INDEX_DIR / "manifest.yaml"

# Layout version this runtime understands. Must match
# indexer.manifest.INDEX_LAYOUT_VERSION; an index built under a newer
# layout is refused rather than mis-read. Kept as a literal here so the
# runtime has no build-time (indexer) import dependency.
SUPPORTED_LAYOUT_VERSION = 1


def read_manifest(path: Path | None = None) -> dict[str, str]:
    """Parse the index manifest's top-level scalar keys.

    The manifest is a tiny hand-rolled YAML emitted by
    ``indexer.manifest`` — flat ``key: value`` lines plus a nested
    ``source_zims`` list we don't need at runtime. We parse only the
    scalar keys (layout_version, embedding_dim, …) without a YAML dep.
    Returns an empty dict when the manifest is absent or unreadable.
    """

    if path is None:
        path = MANIFEST
    out: dict[str, str] = {}
    try:
        text = path.read_text()
    except OSError:
        return out
    for line in text.splitlines():
        # Skip list items / nested keys (leading whitespace) and blanks.
        if not line or line[0].isspace() or line.lstrip().startswith("-"):
            continue
        key, sep, value = line.partition(":")
        if sep and value.strip():
            out[key.strip()] = value.strip()
    return out


def manifest_layout_ok(path: Path | None = None) -> tuple[bool, str]:
    """Return (ok, reason). ``ok`` is False on a layout-version mismatch.

    A missing manifest is treated as OK-but-unknown (legacy indexes
    predate the manifest) so we don't hard-fail an otherwise-valid index;
    a present-but-newer layout is refused.
    """

    man = read_manifest(path)
    if not man:
        return True, "no manifest (legacy index)"
    raw = man.get("layout_version", "")
    try:
        version = int(raw)
    except ValueError:
        return False, f"unparseable layout_version={raw!r}"
    if version > SUPPORTED_LAYOUT_VERSION:
        return False, f"index layout v{version} newer than supported v{SUPPORTED_LAYOUT_VERSION}"
    return True, f"layout v{version}"


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


def index_present(path: Path | None = None) -> bool:
    if path is None:
        path = CHUNKS_DB
    return path.exists() and path.stat().st_size > 0


def open_chunks_ro(path: Path | None = None) -> sqlite3.Connection:
    """Open chunks.sqlite read-only.

    Uses the SQLite URI form so a second writer cannot accidentally upgrade
    the connection. The indexer is the only writer, and it runs on a
    workstation — never on the Pi.
    """

    if path is None:
        path = CHUNKS_DB
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
