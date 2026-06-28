"""Unit tests for the citation-validation post-processor."""

from __future__ import annotations

from assistant.rpi_hub_assist import postprocess


def test_strips_uncited_sentences() -> None:
    text = (
        "Irrigate the wound with clean water [1]. "
        "Dressings are critical. "
        "Apply a sterile dressing [2]."
    )
    result = postprocess.process(text, valid_numbers={1, 2})
    # "Dressings are critical." is uncited; expect it removed.
    assert "Dressings are critical" not in result.text
    assert "[1]" in result.text and "[2]" in result.text
    assert result.cited_chunk_numbers == [1, 2]
    assert not result.rejected


def test_rejects_when_coverage_too_low() -> None:
    # 1 cited out of 4 = 25% coverage; floor is 60%.
    text = (
        "Sentence one. Sentence two. Sentence three. Cited only here [1]."
    )
    result = postprocess.process(text, valid_numbers={1})
    assert result.rejected
    assert result.text == ""


def test_invalid_citation_treated_as_uncited() -> None:
    # [7] points outside the valid set — should be discarded entirely.
    text = "Hallucinated source claim [7]."
    result = postprocess.process(text, valid_numbers={1, 2, 3})
    assert result.rejected


def test_strips_urls() -> None:
    text = "See more at https://example.com/foo [1]."
    result = postprocess.process(text, valid_numbers={1})
    assert "https://example.com" not in result.text
    assert "[link removed]" in result.text


def test_empty_input() -> None:
    result = postprocess.process("", valid_numbers={1})
    assert result.rejected
    assert result.text == ""
