"""Post-process raw model output before showing it to the user.

Two jobs:

1. **Strip uncited claims** — any sentence without a trailing ``[n]``
   citation is removed. Bare model assertions are exactly the failure
   mode the assistant rules prohibit.
2. **Validate citation coverage** — if fewer than 60% of the surviving
   sentences carry a citation, we discard the answer entirely and the
   endpoint falls back to "no good answer".
3. **Strip model-invented URLs** — the system prompt forbids them but
   small models still sometimes emit one. Killing them at the boundary is
   cheap insurance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Sentence splitter: terminator punctuation followed by whitespace + capital.
# Conservative on purpose — we'd rather merge two sentences than split a
# sentence on "e.g." and lose the citation.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'\(])")
_CITATION = re.compile(r"\[(\d+)\]")
_URL = re.compile(r"https?://\S+")

# Coverage threshold: ≥60% of surviving sentences must carry at least one
# citation, OR the answer must be a single sentence that is a citation.
MIN_COVERAGE = 0.6


@dataclass(frozen=True)
class ProcessedAnswer:
    text: str
    cited_chunk_numbers: list[int]  # the [n] values the model actually used
    rejected: bool  # True iff coverage was below MIN_COVERAGE
    reason: str  # diagnostic; never shown to the user


def _split_sentences(text: str) -> list[str]:
    out = [s.strip() for s in _SENTENCE_END.split(text.strip()) if s.strip()]
    return out


def _strip_urls(sentence: str) -> str:
    return _URL.sub("[link removed]", sentence)


def process(text: str, valid_numbers: set[int]) -> ProcessedAnswer:
    """Clean a raw model completion.

    ``valid_numbers`` is the set of passage indices (1-based) the prompt
    actually sent the model. A citation like ``[7]`` when only 6 passages
    were sent is a hallucinated reference; we treat that sentence as
    uncited.
    """

    sentences = _split_sentences(text)
    if not sentences:
        return ProcessedAnswer(text="", cited_chunk_numbers=[], rejected=True, reason="empty")

    kept: list[str] = []
    cited: set[int] = set()
    for s in sentences:
        nums = {int(m) for m in _CITATION.findall(s)}
        valid = nums & valid_numbers
        if not valid:
            continue
        cited |= valid
        kept.append(_strip_urls(s))

    coverage = len(kept) / len(sentences) if sentences else 0.0
    if coverage < MIN_COVERAGE or not kept:
        return ProcessedAnswer(
            text="",
            cited_chunk_numbers=sorted(cited),
            rejected=True,
            reason=f"coverage={coverage:.2f} kept={len(kept)} total={len(sentences)}",
        )

    return ProcessedAnswer(
        text=" ".join(kept),
        cited_chunk_numbers=sorted(cited),
        rejected=False,
        reason="ok",
    )
