"""rpi-pod-assist — FastAPI app on 127.0.0.1:8200.

Mounted by nginx under ``/api/ask``. Single endpoint:

* ``POST /ask`` ``{"q": "..."}`` →
  ``{"mode": "answer|defer|noanswer", "answer": "...", "citations": [...]}``

The three branches reflect the three rules:

* ``mode=defer`` — safety classifier hit. ``answer`` is verbatim from the
  top-ranked retrieved passage; the UI paints a red banner using the
  ``banner`` field.
* ``mode=answer`` — retrieval confidence high enough, model produced a
  citation-validated answer.
* ``mode=noanswer`` — retrieval below threshold, model unreachable, or
  post-processing rejected the output. UI links to the library.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI
from pydantic import BaseModel, Field

from . import __version__, llama_client, postprocess, prompt, retrieve_client, safety

app = FastAPI(
    title="rpi-pod-assist",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Confidence floor for letting the model speak. Retrieval below this floor
# is treated as "no good answer" — the user is sent to manual search.
ANSWER_CONFIDENCE_FLOOR = 0.20


class AskRequest(BaseModel):
    q: Annotated[str, Field(min_length=1, max_length=500)]


class Citation(BaseModel):
    number: int
    article: str
    section: str
    url: str


class AskResponse(BaseModel):
    mode: str  # "answer" | "defer" | "noanswer"
    answer: str
    citations: list[Citation]
    banner: str | None = None
    confidence: float


def _empty_noanswer(confidence: float = 0.0) -> AskResponse:
    return AskResponse(
        mode="noanswer",
        answer=(
            "I can't answer that reliably from the library. "
            "Open the library and search the article you need directly."
        ),
        citations=[],
        confidence=confidence,
    )


def _defer(query: str, verdict: safety.DeferralVerdict) -> AskResponse:
    """Build the verbatim-passage response for a deferred query.

    We *still* call retrieval — the user gets the most relevant passage
    verbatim, with no model rewriting. If retrieval is also down we serve
    the banner alone; that's better than silence on a dangerous query.
    """

    try:
        body = retrieve_client.fetch(query, k=1)
    except retrieve_client.RetrieveUnavailable:
        return AskResponse(
            mode="defer",
            answer="",
            citations=[],
            banner=verdict.banner,
            confidence=0.0,
        )

    results = body.get("results") or []
    if not isinstance(results, list) or not results:
        return AskResponse(
            mode="defer",
            answer="",
            citations=[],
            banner=verdict.banner,
            confidence=0.0,
        )

    top = results[0]
    return AskResponse(
        mode="defer",
        answer=str(top.get("text", "")),
        citations=[
            Citation(
                number=1,
                article=str(top.get("article", "")),
                section=str(top.get("section", "")),
                url=str(top.get("url", "")),
            )
        ],
        banner=verdict.banner,
        confidence=float(body.get("confidence", 0.0)),
    )


@app.get("/health")
def health() -> dict[str, object]:
    return {"version": __version__, "ready": True}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    # 1) Safety. The classifier is the first gate by design — if a query
    #    asks about pediatric ibuprofen dosing, we never want a model
    #    summary, regardless of how confident retrieval is.
    verdict = safety.classify(req.q)
    if verdict is not None:
        return _defer(req.q, verdict)

    # 2) Retrieve.
    try:
        body = retrieve_client.fetch(req.q, k=prompt.MAX_PASSAGES)
    except retrieve_client.RetrieveUnavailable:
        return _empty_noanswer()

    conf = float(body.get("confidence", 0.0))
    raw_results = body.get("results")
    results = raw_results if isinstance(raw_results, list) else []
    if conf < ANSWER_CONFIDENCE_FLOOR or not results:
        return _empty_noanswer(conf)

    passages = [
        prompt.PromptPassage(
            number=i + 1,
            article=str(r.get("article", "")),
            section=str(r.get("section", "")),
            text=str(r.get("text", "")),
        )
        for i, r in enumerate(results[: prompt.MAX_PASSAGES])
    ]

    # 3) Model.
    try:
        raw = llama_client.complete(prompt.build_prompt(req.q, passages))
    except llama_client.LlamaUnavailable:
        return _empty_noanswer(conf)

    valid_nums = {p.number for p in passages}
    processed = postprocess.process(raw, valid_nums)
    if processed.rejected:
        return _empty_noanswer(conf)

    cited = set(processed.cited_chunk_numbers)
    citations = [
        Citation(
            number=p.number,
            article=p.article,
            section=p.section,
            url=str(results[p.number - 1].get("url", "")),
        )
        for p in passages
        if p.number in cited
    ]
    return AskResponse(
        mode="answer",
        answer=processed.text,
        citations=citations,
        confidence=conf,
    )
