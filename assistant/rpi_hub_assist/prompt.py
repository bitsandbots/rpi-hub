"""Prompt scaffold for the Qwen2.5 1.5B Instruct chat template.

We hand-format the conversation rather than using a template engine —
the scaffold is small enough to keep visible at the top of the file, and
keeping it explicit makes the "summarise only retrieved passages" rule
auditable. The model is allowed to do exactly two things:

1. Write a one-paragraph (≤ 80 word) summary of the passages.
2. Cite every claim with an inline ``[n]`` referencing the passage list.

Anything else is stripped by :mod:`postprocess`.
"""

from __future__ import annotations

from dataclasses import dataclass

# Hard cap. Qwen2.5 1.5B has 32k context but we never need that much, and
# llama.cpp will reject prompts that don't fit. 6 chunks × ~600 chars +
# scaffold ≈ 4–5k chars; well under any plausible context limit.
MAX_PASSAGES = 6

SYSTEM = (
    "You are rpi-hub, an offline-library assistant. You write short, neutral "
    "summaries of retrieved passages. You never add facts that are not in "
    "the passages. Every claim ends with a bracketed citation like [1] or "
    "[2]. If the passages do not answer the question, you say so in one "
    "sentence and stop. You never invent URLs, dates, or numbers."
)


# Qwen2.5 chat-template control tokens. User input and retrieved passage
# text are untrusted; if either contained these literally it could close
# the user turn and inject a forged system/assistant turn (prompt
# injection), defeating the "summarise only the passages" rules. We strip
# them from all interpolated text — the scaffold below is the only place
# these tokens may appear.
_CONTROL_TOKENS = ("<|im_start|>", "<|im_end|>")


def _scrub(s: str) -> str:
    for tok in _CONTROL_TOKENS:
        s = s.replace(tok, "")
    return s


@dataclass(frozen=True)
class PromptPassage:
    """Subset of a retrieved chunk used to build the prompt."""

    number: int  # 1-based; this is what the model emits in [n]
    article: str
    section: str
    text: str


def build_prompt(question: str, passages: list[PromptPassage]) -> str:
    """Build the chat-formatted prompt sent to llama.cpp.

    The format matches Qwen2.5's chat template: ``<|im_start|>role`` /
    ``<|im_end|>`` markers. llama.cpp's HTTP server accepts this verbatim
    via the raw ``prompt`` parameter (we deliberately bypass its
    /chat/completions wrapper so we can pin the exact bytes). All
    interpolated text is scrubbed of control tokens first to close the
    prompt-injection surface.
    """

    if len(passages) > MAX_PASSAGES:
        passages = passages[:MAX_PASSAGES]

    body_lines = ["Passages from the library:"]
    for p in passages:
        body_lines.append(f"[{p.number}] {_scrub(p.article)} — {_scrub(p.section)}")
        body_lines.append(_scrub(p.text.strip()))
        body_lines.append("")  # blank between passages

    body_lines.append(f"Question: {_scrub(question.strip())}")
    body_lines.append(
        "Answer in one paragraph of at most 80 words. End every sentence "
        "with the bracketed number of the passage it draws from. If the "
        'passages do not contain the answer, reply: "The library '
        "doesn't have that.\""
    )
    user = "\n".join(body_lines)

    return (
        f"<|im_start|>system\n{SYSTEM}<|im_end|>\n"
        f"<|im_start|>user\n{user}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )
