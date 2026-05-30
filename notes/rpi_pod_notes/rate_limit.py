"""Per-IP rate limiting for note posts.

Two windows, both enforced::

* 1 post per IP per 60 seconds (the soft "stop spamming" gate)
* 10 posts per IP per 3600 seconds (the hard "abuse" ceiling)

A note that's already been wiped still counts for the hour window — the
DB stores the timestamp until reboot or owner-wipe. That's intentional:
the spec is "10 posts/IP/hour", not "10 visible posts/IP/hour".
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from . import storage

WINDOW_SHORT_S = 60
WINDOW_LONG_S = 3600

LIMIT_SHORT = 1
LIMIT_LONG = 10


@dataclass(frozen=True)
class Verdict:
    ok: bool
    retry_after_s: int  # 0 when ok=True
    reason: str  # diagnostic; safe to show the user


def check(conn: object, ip: str) -> Verdict:
    """Run both windows; return a Verdict the endpoint can map to 429.

    We accept ``object`` for ``conn`` to make this unit-testable without a
    real sqlite handle. The actual call site passes the live Connection.
    """

    import sqlite3 as _sql  # noqa: PLC0415

    assert isinstance(conn, _sql.Connection)
    now = time.time()

    short_count = storage.count_by_ip_since(conn, ip, now - WINDOW_SHORT_S)
    if short_count >= LIMIT_SHORT:
        return Verdict(
            ok=False,
            retry_after_s=WINDOW_SHORT_S,
            reason="One note per minute. Try again shortly.",
        )

    long_count = storage.count_by_ip_since(conn, ip, now - WINDOW_LONG_S)
    if long_count >= LIMIT_LONG:
        return Verdict(
            ok=False,
            retry_after_s=WINDOW_LONG_S,
            reason="Hourly post limit reached. Try again later.",
        )

    return Verdict(ok=True, retry_after_s=0, reason="ok")
