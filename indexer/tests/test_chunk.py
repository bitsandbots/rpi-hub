"""Unit tests for the chunker — runs without any optional deps."""

from __future__ import annotations

from indexer import chunk


def test_lead_section_emitted_when_no_headings() -> None:
    body = " ".join(["word"] * 30)
    out = chunk.chunk_article("Article", body, "/library/A")
    assert len(out) == 1
    assert out[0].section == "Lead"
    assert out[0].article == "Article"


def test_section_boundaries_split() -> None:
    body = (
        "Lead paragraph " + ("a " * 30) + "\n"
        "== Section One ==\n" + ("b " * 30) + "\n"
        "== Section Two ==\n" + ("c " * 30)
    )
    out = chunk.chunk_article("Article", body, "/library/A")
    sections = [c.section for c in out]
    assert "Lead" in sections
    assert "Section One" in sections
    assert "Section Two" in sections


def test_long_section_windowed() -> None:
    # 2000 tokens; cap is 800 with 100 overlap → 3 windows.
    body = " ".join(["w"] * 2000)
    out = chunk.chunk_article("Article", body, "/library/A")
    assert len(out) >= 2
    # Token approximation: each window <= MAX_TOKENS.
    for c in out:
        assert len(c.text.split()) <= chunk.MAX_TOKENS


def test_tiny_sections_dropped() -> None:
    body = "short lead\n" "== Empty ==\n" "short\n" "== Real ==\n" + (" ".join(["w"] * 30))
    out = chunk.chunk_article("Article", body, "/library/A")
    sections = [c.section for c in out]
    # "Empty" body and the "short" lead both fall under the 20-token floor.
    assert "Empty" not in sections
    assert "Real" in sections
