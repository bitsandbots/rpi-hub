"""Unit tests for the pure retrieval algorithms.

These tests exercise RRF and diversity-filter logic in isolation — no
sqlite, no hnswlib, no embedding server. The endpoint integration test
lives in :mod:`test_app` so a CI box without those deps still runs them.
"""

from __future__ import annotations

from assistant.signal_retrieve import retrieval


def test_rrf_merges_two_lanes() -> None:
    # Lane A: chunks 1, 2, 3. Lane B: chunks 3, 2, 1.
    # Chunk 3 is rank-3 in A and rank-1 in B; chunk 2 is rank-2 in both.
    # With k=60: 1/(60+2) + 1/(60+2) ≈ 0.0322 for chunk 2
    #             1/(60+3) + 1/(60+1) ≈ 0.0322 for chunk 3
    # Chunk 2 wins by tie-break on order — verify the merge is total.
    ranked = retrieval.reciprocal_rank_fusion([[1, 2, 3], [3, 2, 1]])
    ids = [r.chunk_id for r in ranked]
    assert set(ids) == {1, 2, 3}


def test_rrf_empty_lists_returns_empty() -> None:
    assert retrieval.reciprocal_rank_fusion([[], []]) == []


def test_rrf_single_lane_preserves_order() -> None:
    ranked = retrieval.reciprocal_rank_fusion([[10, 20, 30]])
    assert [r.chunk_id for r in ranked] == [10, 20, 30]


def test_diversity_filter_caps_per_article() -> None:
    # Five chunks all from the same article — only the first 3 survive.
    inputs = [retrieval.RankedResult(chunk_id=i, score=1.0 - i * 0.01) for i in range(5)]
    articles = {i: "Wound care" for i in range(5)}
    out = retrieval.diversity_filter(inputs, articles, per_article=3)
    assert [r.chunk_id for r in out] == [0, 1, 2]


def test_diversity_filter_interleaves() -> None:
    inputs = [
        retrieval.RankedResult(chunk_id=1, score=0.9),
        retrieval.RankedResult(chunk_id=2, score=0.8),
        retrieval.RankedResult(chunk_id=3, score=0.7),
        retrieval.RankedResult(chunk_id=4, score=0.6),
    ]
    articles = {1: "A", 2: "A", 3: "A", 4: "B"}
    # per_article=2 lets 1 and 2 from A through; 3 is filtered; 4 from B
    # passes regardless.
    out = retrieval.diversity_filter(inputs, articles, per_article=2)
    assert [r.chunk_id for r in out] == [1, 2, 4]


def test_confidence_monotonic() -> None:
    low = [retrieval.RankedResult(chunk_id=1, score=0.01)]
    high = [retrieval.RankedResult(chunk_id=1, score=0.10)]
    assert retrieval.confidence(low) < retrieval.confidence(high)
    assert retrieval.confidence([]) == 0.0
