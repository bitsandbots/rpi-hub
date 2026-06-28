"""Phase 13 tests — GPS sweeper lifecycle, arbitration, and API surface.

Fast paths use an injected argv builder (a tiny ``python -c`` child that
prints a canned report). One end-to-end test runs the real vendored
``gps_sdr`` simulator restricted to two PRNs to keep it quick.
"""

from __future__ import annotations

import json
import sys
import time

import pytest
from fastapi.testclient import TestClient

from listen.rpi_hub_listen import dongle, gps, main

CANNED_REPORT = {
    "ts": 0.0,
    "scan": 1,
    "mode": "SIMULATE",
    "bias_tee": False,
    "sample_rate": 2_048_000.0,
    "integration_ms": 1,
    "threshold": 15.0,
    "elapsed_s": 0.1,
    "acquired_count": 1,
    "results": [
        {
            "prn": 7,
            "acquired": True,
            "doppler_hz": 1200.0,
            "code_phase": 512,
            "metric": 19.0,
            "cn0_proxy_db": 12.8,
        }
    ],
}


def _canned_argv(**_kw: object) -> list[str]:
    code = (
        "import json,sys;"
        "print('preamble noise that must be tolerated');"
        f"print(json.dumps({CANNED_REPORT!r}))"
    )
    return [sys.executable, "-c", code]


def _slow_argv(**_kw: object) -> list[str]:
    return [sys.executable, "-c", "import time; time.sleep(30)"]


def _failing_argv(**_kw: object) -> list[str]:
    return [sys.executable, "-c", "import sys; sys.stderr.write('boom'); sys.exit(3)"]


def _wait_done(sweeper: gps.GPSSweeper, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while sweeper.running():
        if time.monotonic() > deadline:
            pytest.fail("sweep did not complete in time")
        time.sleep(0.05)


# ── sweeper unit tests ────────────────────────────────────────────────


def test_sweep_happy_path_releases_arbiter() -> None:
    tuner = dongle.Tuner()
    sw = gps.GPSSweeper(tuner, argv_builder=_canned_argv)
    sw.start()
    _wait_done(sw)
    last = sw.last()
    assert last is not None and last["ok"] is True
    assert last["report"]["acquired_count"] == 1
    assert last["report"]["results"][0]["prn"] == 7
    assert tuner.state.mode == "idle"


def test_sweep_holds_gps_mode_while_running_and_rejects_second() -> None:
    tuner = dongle.Tuner()
    sw = gps.GPSSweeper(tuner, argv_builder=_slow_argv)
    sw.start(timeout_s=30)
    try:
        assert tuner.state.mode == "gps"
        with pytest.raises(dongle.TunerBusy):
            sw.start()
        # rtl_fm modes are also locked out while a sweep holds the dongle.
        with pytest.raises(dongle.TunerBusy):
            tuner.start_gps([sys.executable, "-c", "pass"])
    finally:
        tuner.stop()  # cancels the child (SIGTERM)
        _wait_done(sw)
    last = sw.last()
    assert last is not None and last["ok"] is False
    assert last["error"] == "cancelled"
    assert tuner.state.mode == "idle"


def test_sweep_child_failure_is_recorded_with_stderr_tail() -> None:
    tuner = dongle.Tuner()
    sw = gps.GPSSweeper(tuner, argv_builder=_failing_argv)
    sw.start()
    _wait_done(sw)
    last = sw.last()
    assert last is not None and last["ok"] is False
    assert "exit 3" in last["error"] and "boom" in last["error"]
    assert tuner.state.mode == "idle"


def test_sweep_timeout_kills_child_and_releases() -> None:
    tuner = dongle.Tuner()
    sw = gps.GPSSweeper(tuner, argv_builder=_slow_argv)
    sw.start(timeout_s=0.5)
    _wait_done(sw)
    last = sw.last()
    assert last is not None and last["ok"] is False
    assert "timeout" in last["error"]
    assert tuner.state.mode == "idle"


def test_parse_report_tolerates_noise_and_picks_last_valid() -> None:
    blob = (
        b"garbage\n"
        b'{"not": "a report"}\n'
        + json.dumps({"results": [], "acquired_count": 0}).encode()
        + b"\ntrailing junk\n"
    )
    doc = gps._parse_report(blob)
    assert doc is not None and doc["acquired_count"] == 0
    assert gps._parse_report(b"nothing here") is None


def test_real_simulator_end_to_end() -> None:
    """Runs the vendored gps_sdr against its own simulator (2 PRNs)."""
    pytest.importorskip("numpy")
    tuner = dongle.Tuner()
    sw = gps.GPSSweeper(tuner)  # default argv builder → python -m gps_sdr
    sw.start(prns=[1, 5], integration_ms=1, simulate=True, timeout_s=60)
    _wait_done(sw, timeout=60)
    last = sw.last()
    assert last is not None, "no record"
    assert last["ok"] is True, f"sweep failed: {last['error']}"
    prns = {r["prn"] for r in last["report"]["results"]}
    assert prns == {1, 5}
    # Both injected PRNs (1 and 5) must clear the demonstration threshold
    # of 15 — amplitudes are tuned so the whole synthetic constellation
    # acquires, not just the strongest sat (regression for the under-
    # reporting sim gap).
    by_prn = {r["prn"]: r for r in last["report"]["results"]}
    assert by_prn[1]["acquired"] is True
    assert by_prn[5]["acquired"] is True


def test_real_simulator_full_scenario_all_acquire() -> None:
    """A full default-scenario sweep must report ALL four injected
    satellites as acquired with no false positives — the sim demonstrates
    the whole synthetic constellation, not just one sat."""
    pytest.importorskip("numpy")
    tuner = dongle.Tuner()
    sw = gps.GPSSweeper(tuner)
    injected = {1, 5, 14, 22}
    sw.start(prns=sorted(injected), integration_ms=1, simulate=True, timeout_s=60)
    _wait_done(sw, timeout=60)
    last = sw.last()
    assert last is not None and last["ok"] is True
    acquired = {r["prn"] for r in last["report"]["results"] if r["acquired"]}
    assert injected.issubset(acquired), f"under-reported: {injected - acquired}"


# ── API tests ─────────────────────────────────────────────────────────


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main.dongle, "dongle_present", lambda: True)
    monkeypatch.setattr(main._GPS, "_argv_builder", _canned_argv)
    main._TUNER.stop()
    return TestClient(main.app)


def test_api_gps_state_empty(client: TestClient) -> None:
    r = client.get("/gps")
    assert r.status_code == 200
    body = r.json()
    assert body["running"] is False
    assert body["dongle_present"] is True


def test_api_sweep_lifecycle(client: TestClient) -> None:
    r = client.post("/gps/sweep", json={})
    assert r.status_code == 202
    deadline = time.monotonic() + 10
    while True:
        body = client.get("/gps").json()
        if not body["running"] and body["last"] is not None:
            break
        assert time.monotonic() < deadline
        time.sleep(0.05)
    assert body["last"]["ok"] is True
    assert body["last"]["report"]["results"][0]["prn"] == 7


def test_api_sweep_rejected_while_audio_tuned(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Fake an active rtl_fm mode without spawning anything.
    monkeypatch.setattr(
        main._TUNER,
        "_state",
        dongle.TunerState(
            mode="weather", frequency_hz=162_400_000, label="NOAA", started_ts=1.0
        ),
    )
    r = client.post("/gps/sweep", json={})
    assert r.status_code == 409
    assert "weather" in r.json()["detail"]


def test_api_sweep_503_without_dongle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main.dongle, "dongle_present", lambda: False)
    monkeypatch.setattr(main, "GPS_SIMULATE", False)
    main._TUNER.stop()
    c = TestClient(main.app)
    r = c.post("/gps/sweep", json={})
    assert r.status_code == 503


def test_api_sweep_validates_prns(client: TestClient) -> None:
    assert client.post("/gps/sweep", json={"prns": [0]}).status_code == 422
    assert client.post("/gps/sweep", json={"prns": [33]}).status_code == 422
    assert client.post("/gps/sweep", json={"integration_ms": 99}).status_code == 422
