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
import sys
from typing import Callable

EMBED_MODEL = os.environ.get("rpi_hub_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
EMBED_DIM = int(os.environ.get("rpi_hub_EMBED_DIM", "384"))
EMBED_BATCH = int(os.environ.get("rpi_hub_EMBED_BATCH", "32"))

# A zero-vector index is silently useless — every cosine distance is
# identical, so the vector lane returns meaningless neighbours. We refuse
# to build one by default; the stub is only for plumbing smoke-tests and
# must be opted into explicitly. Read at call time so the CLI flag (which
# sets the env var) takes effect after module import.
def _stub_allowed() -> bool:
    return os.environ.get("rpi_hub_ALLOW_STUB_EMBEDDINGS") == "1"


class EmbeddingModelUnavailable(RuntimeError):
    """sentence-transformers is not installed and stub embeddings weren't allowed."""


def load_encoder() -> Callable[[list[str]], list[list[float]]]:
    """Return a function that batches strings → embedding vectors.

    Tries sentence-transformers. If absent we FAIL LOUD by default
    (raising :class:`EmbeddingModelUnavailable`) rather than quietly
    returning a zero-vector stub that would ship a degenerate index.
    Set ``rpi_hub_ALLOW_STUB_EMBEDDINGS=1`` (or pass
    ``--allow-stub-embeddings``) to opt into the stub for plumbing tests.
    """

    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
    except ImportError as exc:
        if not _stub_allowed():
            raise EmbeddingModelUnavailable(
                "sentence-transformers is not installed — refusing to build a "
                "zero-vector index. Install it, or set "
                "rpi_hub_ALLOW_STUB_EMBEDDINGS=1 / pass --allow-stub-embeddings "
                "for a plumbing-only smoke test."
            ) from exc
        print(
            "\n" + "=" * 70 + "\n"
            "[indexer] WARNING: sentence-transformers missing — building a\n"
            "[indexer] ZERO-VECTOR stub index. The vector lane will be useless.\n"
            "[indexer] DO NOT SHIP THIS INDEX.\n"
            + "=" * 70 + "\n",
            file=sys.stderr,
        )

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
