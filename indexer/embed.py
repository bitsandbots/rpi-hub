"""Embedding helper used by build_index.

We keep this thin so the heavyweight imports (sentence-transformers,
torch) happen lazily at call time and the rest of the indexer package
imports cleanly on a machine that doesn't have them yet.

Production: ``BAAI/bge-small-en-v1.5`` via sentence-transformers. The
model is small enough to fit on a workstation laptop; we don't try to
run it on the Pi.
"""

from __future__ import annotations

import os
from typing import Callable

EMBED_MODEL = os.environ.get("rpi_hub_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
EMBED_DIM = int(os.environ.get("rpi_hub_EMBED_DIM", "384"))
EMBED_BATCH = int(os.environ.get("rpi_hub_EMBED_BATCH", "32"))


def load_encoder() -> Callable[[list[str]], list[list[float]]]:
    """Return a function that batches strings → embedding vectors.

    Tries sentence-transformers; if absent, returns a zero-vector stub so
    the rest of the pipeline can be smoke-tested without the model. The
    indexer CLI surfaces a loud warning in that case — the stub is fine
    for plumbing tests, not for shipping an actual index.
    """

    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
    except ImportError:
        def zero_encode(texts: list[str]) -> list[list[float]]:
            return [[0.0] * EMBED_DIM for _ in texts]

        return zero_encode

    model = SentenceTransformer(EMBED_MODEL)

    def encode(texts: list[str]) -> list[list[float]]:
        # normalize_embeddings keeps the HNSW cosine space well-conditioned.
        vecs = model.encode(
            texts,
            batch_size=EMBED_BATCH,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [list(map(float, v)) for v in vecs]

    return encode
