"""Client for rpi-hub-retrieve (the sibling service on 8100).

Goes through localhost rather than calling the retrieval code directly so
the two services have a clean boundary — rpi-hub-retrieve can be
restarted independently and rpi-hub-assist falls back to the no-answer
path while it's down.
"""

from __future__ import annotations

import http.client
import json
import os
import urllib.error
import urllib.parse
import urllib.request

def _require_loopback(url: str) -> str:
    """Refuse a non-loopback upstream — the device must never initiate
    outbound IP connections. Override with
    ``rpi_hub_ALLOW_NONLOOPBACK_UPSTREAM=1`` for diagnostics.
    """

    if os.environ.get("rpi_hub_ALLOW_NONLOOPBACK_UPSTREAM") == "1":
        return url
    host = urllib.parse.urlsplit(url).hostname or ""
    if host not in ("127.0.0.1", "::1", "localhost"):
        raise RuntimeError(
            f"refusing non-loopback upstream {url!r}: this device must not "
            "initiate outbound connections (set "
            "rpi_hub_ALLOW_NONLOOPBACK_UPSTREAM=1 to override)"
        )
    return url


RETRIEVE_ENDPOINT = _require_loopback(
    os.environ.get("rpi_hub_RETRIEVE_ENDPOINT", "http://127.0.0.1:8100/retrieve")
)
RETRIEVE_TIMEOUT_S = float(os.environ.get("rpi_hub_RETRIEVE_TIMEOUT_S", "5.0"))


class RetrieveUnavailable(RuntimeError):
    pass


def fetch(query: str, k: int = 6) -> dict[str, object]:
    """Return the parsed /retrieve response or raise RetrieveUnavailable.

    No fancy retry — rpi-hub-assist sits behind a 10s end-to-end budget
    and a single retry would burn most of it.
    """

    qs = urllib.parse.urlencode({"q": query, "k": k})
    url = f"{RETRIEVE_ENDPOINT}?{qs}"
    try:
        with urllib.request.urlopen(url, timeout=RETRIEVE_TIMEOUT_S) as resp:
            body = json.loads(resp.read())
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,  # ConnectionReset/Refused raised during read()
        http.client.HTTPException,  # RemoteDisconnected / IncompleteRead
        json.JSONDecodeError,
    ) as exc:
        raise RetrieveUnavailable(str(exc)) from exc
    if not isinstance(body, dict):
        raise RetrieveUnavailable(f"unexpected retrieve payload: {body!r}")
    return body
