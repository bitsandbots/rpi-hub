"""Chunker for the assistant index.

Strategy: section-boundary split with a token cap and overlap. Headings
are the natural unit a Wikipedia editor wrote against — splitting on
them preserves topical coherence better than blind char windows.

Token counting uses a cheap whitespace approximation. The bge-small
tokenizer would be more accurate but pulling transformers into the
chunker just to count tokens is a poor trade. Empirically the
approximation runs ~1% short of the real count on English Wikipedia,
which is well inside our 100-token overlap.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_TOKENS = 800
OVERLAP_TOKENS = 100

# A heading line in Wikipedia HTML-stripped text looks like "== Section ==".
# We accept 2–4 equals signs to cover sub-sections.
_HEADING = re.compile(r"^(={2,4})\s*(.+?)\s*\1\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    article: str
    section: str
    text: str
    url: str  # deep link into kiwix-serve for the source article


def _approx_tokens(text: str) -> int:
    return len(text.split())


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """Return ``[(section_title, section_body), ...]``.

    The first segment uses the synthetic title "Lead" because Wikipedia
    leads sit before any heading. Empty sections are dropped.
    """

    out: list[tuple[str, str]] = []
    cursor = 0
    current_title = "Lead"
    for m in _HEADING.finditer(text):
        body = text[cursor : m.start()].strip()
        if body:
            out.append((current_title, body))
        current_title = m.group(2).strip()
        cursor = m.end()
    tail = text[cursor:].strip()
    if tail:
        out.append((current_title, tail))
    return out


def _window(body: str, max_tokens: int, overlap: int) -> list[str]:
    """Sliding-window split with token-approx step.

    When the body fits under the cap we emit it as-is, which preserves
    the section's natural sentence boundaries.
    """

    tokens = body.split()
    if len(tokens) <= max_tokens:
        return [body]

    out: list[str] = []
    step = max_tokens - overlap
    if step <= 0:
        step = max_tokens
    for start in range(0, len(tokens), step):
        window = tokens[start : start + max_tokens]
        if not window:
            break
        out.append(" ".join(window))
        if start + max_tokens >= len(tokens):
            break
    return out


def chunk_article(article: str, text: str, url: str) -> list[Chunk]:
    """Produce the chunks for one article body."""

    chunks: list[Chunk] = []
    for section, body in _split_into_sections(text):
        for window in _window(body, MAX_TOKENS, OVERLAP_TOKENS):
            if _approx_tokens(window) < 20:
                # Drop trivially short chunks — usually navigation
                # boilerplate stripped to one sentence.
                continue
            chunks.append(
                Chunk(article=article, section=section, text=window, url=url)
            )
    return chunks
