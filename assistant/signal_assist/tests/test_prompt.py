"""Unit tests for the prompt scaffold."""

from __future__ import annotations

from assistant.signal_assist import prompt


def _pass(n: int, text: str = "passage text") -> prompt.PromptPassage:
    return prompt.PromptPassage(number=n, article=f"Article {n}", section="intro", text=text)


def test_prompt_contains_question_and_passages() -> None:
    out = prompt.build_prompt(
        "how do I purify water",
        [_pass(1, "Boil water for one minute."), _pass(2, "Filter sediment first.")],
    )
    assert "how do I purify water" in out
    assert "[1]" in out and "[2]" in out
    assert "Boil water for one minute." in out
    assert "Filter sediment first." in out
    # Chat-template markers must be present so llama.cpp tokenises correctly.
    assert "<|im_start|>system" in out
    assert "<|im_start|>assistant" in out


def test_prompt_caps_passages() -> None:
    passages = [_pass(i + 1) for i in range(prompt.MAX_PASSAGES + 3)]
    out = prompt.build_prompt("q", passages)
    # Last allowed passage appears, the one after does not.
    assert f"[{prompt.MAX_PASSAGES}]" in out
    assert f"[{prompt.MAX_PASSAGES + 1}]" not in out
