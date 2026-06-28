"""Thin client for the local embedding server.

The embedding server is llama.cpp's HTTP shim running the bge-small-en
weights. We isolate the network call so retrieval.py stays pure and
testable. On hosts where the server is unavailable, :func:`embed_query`
raises ``EmbedUnavailable`` — the retrieval app catches it and falls back
to BM25-only.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

EMBED_ENDPOINT = os.environ.get(
    "rpi_hub_EMBED_ENDPOINT", "http://127.0.0.1:8201/embedding"
)
EMBED_TIMEOUT_S = float(os.environ.get("rpi_hub_EMBED_TIMEOUT_S", "5.0"))


class EmbedUnavailable(RuntimeError):
    """Embedding lane is unreachable; retrieval should fall back to BM25."""


def embed_query(text: str) -> list[float]:
    if not text.strip():
        return []
    payload = json.dumps({"content": text}).encode("utf-8")
    req = urllib.request.Request(
        EMBED_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=EMBED_TIMEOUT_S) as resp:
            body = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise EmbedUnavailable(str(exc)) from exc

    # llama.cpp's /embedding response shape is {"embedding": [..floats..]}.
    vec = body.get("embedding") if isinstance(body, dict) else None
    if not isinstance(vec, list):
        raise EmbedUnavailable(f"unexpected embedding payload: {body!r}")
    return [float(x) for x in vec]
