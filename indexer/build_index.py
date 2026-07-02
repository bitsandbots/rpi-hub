#!/usr/bin/env python3
"""Build the assistant index from a directory of ZIM files.

This is a workstation tool. Usage::

    python -m indexer.build_index \\
        --zim-dir /var/lib/kiwix \\
        --out ./payload/var/lib/rpi-hub/index

It produces the on-disk layout rpi-hub-retrieve consumes. The build is
deterministic given the same ZIM inputs and embedding model, so two
runs on different machines should produce byte-identical
``chunks.sqlite`` (vectors are bit-identical up to the BLAS
implementation; the HNSW graph itself depends on the chosen ef/M but
not on host RNG since hnswlib seeds from the chunk id sequence).

This script intentionally avoids hard-importing optional deps
(libzim, hnswlib) at module level — that way the unit tests for the
pure helpers don't pull them in.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import struct
import sys
from collections.abc import Iterator
from pathlib import Path

from . import chunk as chunker
from . import embed as embedder
from . import manifest as manifest_mod
from .htmlstrip import html_to_text


def _open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            article TEXT NOT NULL,
            section TEXT NOT NULL,
            text TEXT NOT NULL,
            url TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            text, content='chunks', content_rowid='id', tokenize='porter unicode61'
        );
        CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
        END;
        """
    )
    return conn


def _iter_articles(zim_dir: Path) -> Iterator[tuple[str, str, str]]:
    """Yield ``(article_name, body_text, url)`` tuples from every ZIM.

    Imports libzim lazily so the rest of the indexer is importable on a
    workstation that hasn't installed it yet.
    """

    try:
        from libzim.reader import (  # noqa: PLC0415 # optional heavy dep — see module docstring
            Archive,
        )
    except ImportError:
        print(
            "[indexer] libzim not installed; install with `pip install libzim` to read ZIMs",
            file=sys.stderr,
        )
        return

    for zim_path in sorted(zim_dir.glob("*.zim")):
        archive = Archive(zim_path)
        for i in range(archive.entry_count):
            entry = archive._get_entry_by_id(i)  # noqa: SLF001
            if entry.is_redirect:
                continue
            item = entry.get_item()
            mime = item.mimetype or ""
            if mime != "text/html":
                continue
            try:
                raw_html = bytes(item.content).decode("utf-8", errors="ignore")
            except Exception:  # noqa: BLE001
                continue
            body = html_to_text(raw_html)
            if not body:
                continue
            yield (entry.title or entry.path, body, f"/library/{zim_path.stem}/A/{entry.path}")


def build(zim_dir: Path, out_dir: Path) -> manifest_mod.IndexManifest:
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "chunks.sqlite"
    conn = _open_db(db_path)

    encode = embedder.load_encoder()

    manifest = manifest_mod.IndexManifest()

    pending_ids: list[int] = []
    pending_text: list[str] = []
    embeddings: list[list[float]] = []
    chunk_id = 0
    token_count = 0

    def flush() -> None:
        nonlocal pending_ids, pending_text
        if not pending_text:
            return
        vecs = encode(pending_text)
        embeddings.extend(vecs)
        pending_ids = []
        pending_text = []

    for article, body, url in _iter_articles(zim_dir):
        for c in chunker.chunk_article(article, body, url):
            chunk_id += 1
            conn.execute(
                "INSERT INTO chunks (id, article, section, text, url) VALUES (?, ?, ?, ?, ?)",
                (chunk_id, c.article, c.section, c.text, c.url),
            )
            pending_ids.append(chunk_id)
            pending_text.append(c.text)
            token_count += len(c.text.split())
            if len(pending_text) >= embedder.EMBED_BATCH:
                flush()
        # Commit per-article so a long build is restart-friendly.
        conn.commit()

    flush()
    conn.commit()

    # Write HNSW + id map.
    try:
        import hnswlib  # noqa: PLC0415

        if embeddings:
            index = hnswlib.Index(space="cosine", dim=embedder.EMBED_DIM)
            index.init_index(
                max_elements=len(embeddings),
                ef_construction=manifest.hnsw_ef_construction,
                M=manifest.hnsw_M,
            )
            labels = list(range(len(embeddings)))
            index.add_items(embeddings, labels)
            index.save_index(str(out_dir / "vectors.hnsw"))

            # id_map: HNSW label → chunk id. Chunk ids are 1-based and we
            # add embeddings in order, so label i corresponds to chunk i+1.
            with (out_dir / "vectors.ids").open("wb") as f:
                f.write(struct.pack(f"<{len(embeddings)}i", *range(1, len(embeddings) + 1)))
    except ImportError:
        print("[indexer] hnswlib not installed; skipping vector index", file=sys.stderr)

    manifest.chunk_count = chunk_id
    manifest.token_count = token_count
    manifest_mod.write_manifest(out_dir / "manifest.yaml", manifest)

    conn.close()
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zim-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--allow-stub-embeddings",
        action="store_true",
        help="build with zero-vector embeddings when sentence-transformers is "
        "absent (plumbing smoke-test only; the vector lane will be useless)",
    )
    args = ap.parse_args()
    if args.allow_stub_embeddings:
        os.environ["rpi_hub_ALLOW_STUB_EMBEDDINGS"] = "1"

    manifest = build(args.zim_dir, args.out)
    print(f"[indexer] wrote {manifest.chunk_count} chunks ({manifest.token_count} tokens)")
    print(f"[indexer] output: {args.out}")
    print("[indexer] rsync to Pi:")
    print(f"  rsync -avh --delete {args.out}/ pi@hub.local:/var/lib/rpi-hub/index/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
