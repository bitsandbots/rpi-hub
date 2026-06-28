"""Thin client for the local llama.cpp HTTP server.

llama.cpp exposes ``/completion`` for raw prompts. We POST the chat-
formatted prompt produced by :mod:`prompt` and stream the response back
as a single block (the Ask UI does its own typewriter animation — we
don't need server-sent events here).

The client is deliberately tiny: stdlib only, no httpx / requests, so it
imports cleanly under the systemd unit's strict apt-only Python world.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

LLAMA_ENDPOINT = os.environ.get(
    "rpi_hub_LLAMA_ENDPOINT", "http://127.0.0.1:8202/completion"
)
LLAMA_TIMEOUT_S = float(os.environ.get("rpi_hub_LLAMA_TIMEOUT_S", "20.0"))

# Generation knobs. Tuned for Pi 5 + Qwen2.5 1.5B Instruct Q4_K_M:
# ~8 tok/s sustained → 80 tokens fits inside the 10s end-to-end budget.
DEFAULT_MAX_TOKENS = 200
DEFAULT_TEMPERATURE = 0.2  # low — we want extraction, not creativity
DEFAULT_TOP_P = 0.9
STOP_TOKENS = ["<|im_end|>", "<|im_start|>"]


class LlamaUnavailable(RuntimeError):
    """The llama.cpp server is not reachable. Endpoint returns no-answer."""


def complete(
    prompt: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
) -> str:
    """Run a single non-streaming completion against llama.cpp.

    Returns the raw text the model emitted (no chat scaffolding). Callers
    are responsible for trimming the assistant's stop token and any
    trailing whitespace.
    """

    payload = json.dumps(
        {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature,
            "top_p": DEFAULT_TOP_P,
            "stop": STOP_TOKENS,
            "cache_prompt": True,
            "stream": False,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        LLAMA_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=LLAMA_TIMEOUT_S) as resp:
            body = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LlamaUnavailable(str(exc)) from exc

    content = body.get("content") if isinstance(body, dict) else None
    if not isinstance(content, str):
        raise LlamaUnavailable(f"unexpected completion payload: {body!r}")
    return content.strip()
