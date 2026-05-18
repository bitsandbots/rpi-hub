"""Unit tests for the alert ring."""

from __future__ import annotations

import time

from listen.signal_listen import alerts, same


def _fake_alert(duration_minutes: int = 30) -> same.SameAlert:
    return same.SameAlert(
        originator="WXR",
        event_code="TOR",
        event_label="Tornado Warning",
        fips_codes=["053009"],
        duration_minutes=duration_minutes,
        issued_jjj_hhmm="3171800",
        station="KEAX/NWS",
        raw="ZCZC-…",
    )


def test_push_and_recent() -> None:
    ring = alerts.AlertRing()
    a = ring.push(_fake_alert())
    recent = ring.recent()
    assert len(recent) == 1
    assert recent[0] is a


def test_expired_alerts_filtered_from_recent() -> None:
    ring = alerts.AlertRing()
    ring.push(_fake_alert(duration_minutes=0))  # already expired
    # received_ts == now → expires_ts == now; pass a future "now".
    future = time.time() + 1
    assert ring.recent(now=future) == []


def test_ring_caps_capacity() -> None:
    ring = alerts.AlertRing(capacity=3)
    for _ in range(5):
        ring.push(_fake_alert())
    assert len(ring.all()) == 3
