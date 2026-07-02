"""In-memory ring buffer of recent SAME alerts.

The service holds the last N alerts so the landing page can pin a red
banner when one fires recently. Older alerts age out automatically; the
landing page polls /api/listen/alerts and decides whether to render
based on the alert's age + expiry.

Persistence is intentional non-goal: a rebooted hub forgets prior
alerts, just like the notes board. Active alerts within their stated
duration repopulate from the next SAME burst.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

from . import same

RING_CAPACITY = 32


@dataclass
class StoredAlert:
    alert: same.SameAlert
    received_ts: float = field(default_factory=time.time)

    @property
    def expires_ts(self) -> float:
        return self.received_ts + self.alert.duration_minutes * 60

    def is_active(self, now: float | None = None) -> bool:
        ts = now if now is not None else time.time()
        return ts <= self.expires_ts


class AlertRing:
    def __init__(self, capacity: int = RING_CAPACITY) -> None:
        self._dq: deque[StoredAlert] = deque(maxlen=capacity)

    def push(self, alert: same.SameAlert) -> StoredAlert:
        stored = StoredAlert(alert=alert)
        self._dq.append(stored)
        return stored

    def recent(self, now: float | None = None) -> list[StoredAlert]:
        ts = now if now is not None else time.time()
        return [a for a in reversed(self._dq) if a.is_active(ts)]

    def all(self) -> list[StoredAlert]:
        return list(reversed(self._dq))
