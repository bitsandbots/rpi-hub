"""rpi-hub-retrieve — FastAPI app on 127.0.0.1:8100.

Mounted by nginx under ``/api/retrieve``. The app composes
:mod:`store`, :mod:`retrieval`, and :mod:`embed_client` into a single
``GET /retrieve`` endpoint plus a readiness probe.

Failure modes the endpoint absorbs cleanly (always 200, never 500):

* Index directory missing or empty — ``ready=False`` in the body, empty
  results, ``confidence=0``.
* FTS5 syntax error from a stray ``"`` or ``-`` in the query — falls back
  to vector-only.
* Embedding service unreachable — falls back to BM25-only.

The Ask UI treats any of these as "search the library directly".
"""

from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, Query
from pydantic import BaseModel

from . import __version__, retrieval, store
from .embed_client import embed_query as _embed_query

app = FastAPI(
    title="rpi-hub-retrieve",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


class ChunkOut(BaseModel):
    chunk_id: int
    article: str
    section: str
    text: str
    url: str
    score: float


class RetrieveResponse(BaseModel):
    ready: bool
    query: str
    confidence: float
    results: list[ChunkOut]


class HealthResponse(BaseModel):
    ready: bool
    chunk_count: int
    version: str


def _hybrid_search(
    conn: object, query: str, k: int
) -> list[retrieval.RankedResult]:
    """Run the BM25 + vector lanes and fuse.

    Each lane is allowed to fail independently — if vector search returns
    nothing because the embedding service is down, BM25 still produces
    answers. This is intentional: the assistant degrades gracefully on a
    Pi that has been running for weeks.
    """

    # Cast back to sqlite3.Connection at the call boundary; we accept
    # ``object`` here so the function is trivial to monkeypatch in tests.
    import sqlite3 as _sql  # local to keep top-level imports tidy  # noqa: PLC0415

    assert isinstance(conn, _sql.Connection)

    candidates = max(k * 4, retrieval.DEFAULT_CANDIDATES)

    bm25_ids: list[int] = []
    try:
        bm25_ids = retrieval.bm25_search(conn, query, candidates)
    except _sql.OperationalError:
        # Bad FTS5 grammar (user typed a bare hyphen). Vector lane only.
        bm25_ids = []

    vec_ids: list[int] = []
    try:
        qvec = _embed_query(query)
    except Exception:  # noqa: BLE001 — embedding service is best-effort
        qvec = []
    if qvec:
        # hnsw + id_map are lazy-loaded once per process at startup; we
        # pull them via attribute lookup on the module so tests can stub.
        from . import index_handle

        vec_ids = retrieval.vector_search(
            qvec,
            index_handle.HNSW,
            index_handle.ID_MAP,
            candidates,
        )

    fused = retrieval.reciprocal_rank_fusion([bm25_ids, vec_ids])

    # Pull article names for the diversity filter in one query.
    if fused:
        all_ids = [r.chunk_id for r in fused]
        rows = conn.execute(
            "SELECT id, article FROM chunks WHERE id IN ({seq})".format(
                seq=",".join("?" for _ in all_ids)
            ),
            all_ids,
        ).fetchall()
        article_map = {int(r["id"]): str(r["article"]) for r in rows}
        fused = retrieval.diversity_filter(fused, article_map)

    return fused[:k]


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    if not store.index_present():
        return HealthResponse(ready=False, chunk_count=0, version=__version__)
    with store.open_chunks_ro() as conn:
        return HealthResponse(
            ready=True,
            chunk_count=store.chunk_count(conn),
            version=__version__,
        )


@app.get("/retrieve", response_model=RetrieveResponse)
def retrieve(
    q: Annotated[str, Query(min_length=1, max_length=500)],
    k: Annotated[int, Query(ge=1, le=32)] = 8,
) -> RetrieveResponse:
    if not store.index_present():
        return RetrieveResponse(ready=False, query=q, confidence=0.0, results=[])

    with store.open_chunks_ro() as conn:
        ranked = _hybrid_search(conn, q, k)
        conf = retrieval.confidence(ranked)
        chunks = store.fetch_chunks(conn, [r.chunk_id for r in ranked])
        scores = {r.chunk_id: r.score for r in ranked}

    results = [
        ChunkOut(
            chunk_id=c.chunk_id,
            article=c.article,
            section=c.section,
            text=c.text,
            url=c.url,
            score=scores.get(c.chunk_id, 0.0),
        )
        for c in chunks
    ]
    return RetrieveResponse(ready=True, query=q, confidence=conf, results=results)
