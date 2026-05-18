"""Process-wide HNSW handle, lazy-loaded once at startup.

The retrieval app imports ``HNSW`` and ``ID_MAP`` directly. On a host
without hnswlib installed (CI, dev box) both stay ``None`` / ``[]`` and
the vector lane silently degrades.

Loading is performed at module import — uvicorn imports the app module
once per worker, and signal-retrieve runs a single worker (the model is
the bottleneck, not request concurrency). Re-load by restarting the
service.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path

VECTORS_HNSW = Path("/var/lib/signal/index/vectors.hnsw")
VECTORS_IDS = Path("/var/lib/signal/index/vectors.ids")
EMBED_DIM = int(os.environ.get("SIGNAL_EMBED_DIM", "384"))  # bge-small-en

HNSW: object | None = None
ID_MAP: list[int] = []


def _load_id_map(path: Path) -> list[int]:
    if not path.exists():
        return []
    raw = path.read_bytes()
    # int32 little-endian per the indexer's writer.
    n, rem = divmod(len(raw), 4)
    if rem != 0:
        return []
    return list(struct.unpack(f"<{n}i", raw))


def _load_hnsw(path: Path, ids: list[int]) -> object | None:
    if not path.exists() or not ids:
        return None
    try:
        import hnswlib  # type: ignore[import-untyped]
    except ImportError:
        return None
    index = hnswlib.Index(space="cosine", dim=EMBED_DIM)
    index.load_index(str(path), max_elements=len(ids))
    index.set_ef(64)
    return index


# Eager load. Failure here is non-fatal — vector lane disables itself.
try:
    ID_MAP = _load_id_map(VECTORS_IDS)
    HNSW = _load_hnsw(VECTORS_HNSW, ID_MAP)
except Exception:  # noqa: BLE001 — best-effort startup probe
    ID_MAP = []
    HNSW = None
