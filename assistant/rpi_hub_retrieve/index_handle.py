"""Process-wide HNSW handle, lazy-loaded once at startup.

The retrieval app imports ``HNSW`` and ``ID_MAP`` directly. The vector
lane requires ``hnswlib``; the blueprint sells "hybrid BM25 + HNSW + RRF"
so on a production Pi this MUST load. If it does not, ``VECTOR_STATUS``
records exactly why and ``/health`` surfaces ``vector_ready=False`` so
the degradation to BM25-only is *observable* rather than silent.

The embedding dimension is read from the index manifest (the source of
truth the indexer stamped), not guessed — a dim mismatch would otherwise
load garbage into a cosine graph. An ``rpi_hub_EMBED_DIM`` env var still
overrides for tests.

Loading is performed at module import — uvicorn imports the app module
once per worker, and rpi-hub-retrieve runs a single worker (the model is
the bottleneck, not request concurrency). Re-load by restarting the
service.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path
from typing import cast

from . import store

VECTORS_HNSW = Path("/var/lib/rpi-hub/index/vectors.hnsw")
VECTORS_IDS = Path("/var/lib/rpi-hub/index/vectors.ids")


def _resolve_embed_dim() -> int:
    override = os.environ.get("rpi_hub_EMBED_DIM")
    if override:
        return int(override)
    man = store.read_manifest()
    try:
        return int(man.get("embedding_dim", "384"))
    except ValueError:
        return 384


EMBED_DIM = _resolve_embed_dim()  # from manifest (bge-small-en → 384)

HNSW: object | None = None
ID_MAP: list[int] = []
# Human-readable reason the vector lane is or isn't live, surfaced at
# /health. "ready" only when the HNSW graph actually loaded.
VECTOR_STATUS: str = "not loaded"


def vector_ready() -> bool:
    return HNSW is not None


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
    global VECTOR_STATUS  # noqa: PLW0603 — update module status during init
    if not path.exists():
        VECTOR_STATUS = "no vectors.hnsw (index has no vector lane)"
        return None
    if not ids:
        VECTOR_STATUS = "empty vectors.ids"
        return None
    ok, reason = store.manifest_layout_ok()
    if not ok:
        VECTOR_STATUS = f"refused: {reason}"
        return None
    try:
        import hnswlib  # noqa: PLC0415
    except ImportError:
        # This is the production-critical case: the blueprint promises a
        # vector lane but the host lacks the ANN library. Make it loud.
        VECTOR_STATUS = "hnswlib not installed — vector lane DISABLED (install python3-hnswlib)"
        return None
    try:
        index = hnswlib.Index(space="cosine", dim=EMBED_DIM)
        index.load_index(str(path), max_elements=len(ids))
        index.set_ef(64)
    except (RuntimeError, OSError, ValueError) as exc:
        VECTOR_STATUS = f"hnsw load failed: {exc}"
        return None
    VECTOR_STATUS = f"ready ({len(ids)} vectors, dim={EMBED_DIM})"
    return cast(object, index)


# Eager load. Failure here is non-fatal — vector lane disables itself but
# records VECTOR_STATUS so the degradation is observable at /health.
try:
    ID_MAP = _load_id_map(VECTORS_IDS)
    HNSW = _load_hnsw(VECTORS_HNSW, ID_MAP)
except Exception as exc:  # noqa: BLE001 — best-effort startup probe
    ID_MAP = []
    HNSW = None
    VECTOR_STATUS = f"load error: {exc}"
