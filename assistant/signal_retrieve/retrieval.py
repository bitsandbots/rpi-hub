"""Hybrid BM25 + vector retrieval with reciprocal-rank fusion.

The full production path is::

    query → BM25 top-N (sqlite FTS5)         ─┐
          → embed(query) → HNSW top-N        ─┼─→ RRF fusion → diversity filter → top-k
                                              ┘

We split the implementation so each piece is testable in isolation:

* :func:`bm25_search` returns ranked chunk ids from the FTS5 index.
* :func:`vector_search` returns ranked chunk ids from the HNSW graph.
* :func:`reciprocal_rank_fusion` merges any number of ranked id lists.
* :func:`diversity_filter` caps per-article chunks so a single dominant
  article can't monopolise the answer.

In the runtime, ``HybridRetriever`` wires them together. In tests, the
caller stitches the steps directly so neither FTS5 nor HNSW need to be
installed.
"""

from __future__ import annotations

import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass

# RRF constant — Cormack et al. 2009 use k=60. We mirror that.
RRF_K = 60

# Hybrid retrieval pulls a wider candidate pool than the final k so RRF has
# room to surface a chunk that one of the two lanes ranked highly.
DEFAULT_CANDIDATES = 32

# Confidence floor below which the retriever should report "no answer".
# Calibrated against the Phase 6.1 acceptance set on first build; revisit
# whenever the eval harness moves.
CONFIDENCE_FLOOR = 0.05


@dataclass(frozen=True)
class RankedResult:
    chunk_id: int
    score: float


def bm25_search(conn: sqlite3.Connection, query: str, limit: int) -> list[int]:
    """Top-`limit` chunk ids from sqlite FTS5.

    Uses the ``chunks_fts`` virtual table the indexer creates. Returns ids
    in descending relevance order. Empty queries short-circuit so the FTS5
    grammar never sees a stray operator-only string.
    """

    q = query.strip()
    if not q:
        return []
    rows = conn.execute(
        "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? "
        "ORDER BY bm25(chunks_fts) LIMIT ?",
        (q, limit),
    ).fetchall()
    return [int(r[0]) for r in rows]


def vector_search(
    embed_query: list[float],
    hnsw: object | None,
    id_map: list[int],
    limit: int,
) -> list[int]:
    """Top-`limit` chunk ids from the HNSW vector index.

    ``hnsw`` is the runtime-loaded ``hnswlib.Index`` handle. We type it
    loosely so the module imports cleanly on machines that do not have the
    library installed (CI, dev) — callers pass ``None`` there and we
    return an empty list.
    """

    if hnsw is None or not embed_query:
        return []
    # Lazy attribute lookup so hnswlib is not a hard import.
    knn = getattr(hnsw, "knn_query", None)
    if knn is None:
        return []
    labels, _distances = knn([embed_query], k=limit)
    # hnswlib returns numpy arrays; cast through python to keep the type
    # surface stable for tests using plain lists.
    return [int(id_map[int(label)]) for label in labels[0] if int(label) < len(id_map)]


def reciprocal_rank_fusion(
    ranked_lists: list[list[int]], k: int = RRF_K
) -> list[RankedResult]:
    """Merge multiple ranked lists by RRF.

    Score per chunk = sum over lanes of 1 / (k + rank_in_lane). A chunk
    that appears at rank 1 in two lanes beats a chunk that appears at rank
    1 in one lane and rank 50 in the other — exactly the behaviour we want
    when fusing lexical and semantic results.
    """

    scores: dict[int, float] = defaultdict(float)
    for ranked in ranked_lists:
        for rank, chunk_id in enumerate(ranked, start=1):
            scores[chunk_id] += 1.0 / (k + rank)
    return sorted(
        (RankedResult(chunk_id=cid, score=s) for cid, s in scores.items()),
        key=lambda r: r.score,
        reverse=True,
    )


def diversity_filter(
    ranked: list[RankedResult],
    chunk_articles: dict[int, str],
    per_article: int = 3,
) -> list[RankedResult]:
    """Cap each article at `per_article` chunks while preserving order.

    Stops a single Wikipedia article from filling every slot when its
    intro chunk also happens to be the single highest BM25 hit. The
    indexer guarantees ``chunk_articles`` covers every id we'll see here.
    """

    seen: dict[str, int] = defaultdict(int)
    out: list[RankedResult] = []
    for r in ranked:
        article = chunk_articles.get(r.chunk_id, "")
        if seen[article] >= per_article:
            continue
        seen[article] += 1
        out.append(r)
    return out


def confidence(ranked: list[RankedResult]) -> float:
    """Confidence score in [0, 1]. Used to gate the "no good answer" UX.

    The top RRF score is unbounded above but in practice tops out around
    0.06 (two perfect-rank-1 lanes → 2 * 1/61 ≈ 0.0328 minimum-meaningful
    threshold). We map onto [0, 1] with a soft cap; the exact curve is
    less important than the *threshold* the eval harness pins.
    """

    if not ranked:
        return 0.0
    top = ranked[0].score
    # Smooth squash; saturates around top≈0.15.
    return 1.0 - math.exp(-top * 20.0)
