"""Unit tests for the signal-status app.

These run on any dev machine — they never assume Pi hardware. Probes that
touch the OS are monkeypatched to fixed values, and the FastAPI TestClient
exercises the route end-to-end via Starlette's ASGI shim.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from signal_status import main, system


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


def test_uptime_reads_proc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "uptime"
    fake.write_text("12345.67 9876.54\n")
    monkeypatch.setattr(system, "PROC_UPTIME", fake)
    assert system.uptime_seconds() == pytest.approx(12345.67)


def test_uptime_missing_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(system, "PROC_UPTIME", tmp_path / "nope")
    assert system.uptime_seconds() is None


def test_storage_falls_back_to_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(system, "KIWIX_DIR", tmp_path / "missing")
    info = system.storage()
    # Whichever filesystem / is on must exist and have non-None totals.
    assert info.kiwix_bytes_total is not None
    assert info.kiwix_bytes_free is not None


def test_dhcp_clients_counts_lease_lines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    leases = tmp_path / "leases"
    leases.write_text(
        "1700000000 aa:bb:cc:dd:ee:ff 192.168.4.10 phone1 *\n"
        "1700000050 11:22:33:44:55:66 192.168.4.11 laptop *\n"
        "\n"  # blank lines shouldn't count
    )
    monkeypatch.setattr(system, "DNSMASQ_LEASES", leases)
    monkeypatch.setattr(system, "DNSMASQ_LEASES_ALT", tmp_path / "alt-nope")
    assert system.dhcp_clients() == 2


def test_dhcp_clients_missing_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(system, "DNSMASQ_LEASES", tmp_path / "nope")
    monkeypatch.setattr(system, "DNSMASQ_LEASES_ALT", tmp_path / "alt-nope")
    assert system.dhcp_clients() is None


def test_voltage_parses_throttled(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kw: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["vcgencmd"], returncode=0, stdout="throttled=0x50005\n", stderr=""
        )

    monkeypatch.setattr(system.subprocess, "run", fake_run)
    v = system.voltage()
    # 0x50005 has bit 0 set → undervoltage active now.
    assert v.throttled == "0x50005"
    assert v.undervoltage is True


def test_voltage_nominal(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kw: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["vcgencmd"], returncode=0, stdout="throttled=0x0\n", stderr=""
        )

    monkeypatch.setattr(system.subprocess, "run", fake_run)
    v = system.voltage()
    assert v.throttled == "0x0"
    assert v.undervoltage is False


def test_voltage_no_vcgencmd(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kw: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("vcgencmd")

    monkeypatch.setattr(system.subprocess, "run", fake_run)
    v = system.voltage()
    assert v.throttled is None
    assert v.undervoltage is None


def test_voltage_malformed_word(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kw: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["vcgencmd"], returncode=0, stdout="throttled=garbage\n", stderr=""
        )

    monkeypatch.setattr(system.subprocess, "run", fake_run)
    v = system.voltage()
    assert v.throttled == "garbage"
    assert v.undervoltage is None


def test_build_version_reads_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vf = tmp_path / "version"
    vf.write_text("v0.5.0-phase5\n")
    monkeypatch.setattr(system, "VERSION_FILE", vf)
    assert system.build_version() == "v0.5.0-phase5"


def test_build_version_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(system, "VERSION_FILE", tmp_path / "nope")
    assert system.build_version() == "dev"


def test_status_endpoint_shape(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Pin every probe so the response schema is fully populated and
    # independent of the host running pytest.
    monkeypatch.setattr(system, "uptime_seconds", lambda: 123.45)
    monkeypatch.setattr(system, "load_avg", lambda: (0.1, 0.2, 0.3))
    monkeypatch.setattr(
        system,
        "storage",
        lambda: system.StorageInfo(kiwix_bytes_free=10, kiwix_bytes_total=100),
    )
    monkeypatch.setattr(
        system,
        "voltage",
        lambda: system.VoltageInfo(throttled="0x0", undervoltage=False),
    )
    monkeypatch.setattr(system, "dhcp_clients", lambda: 2)
    monkeypatch.setattr(system, "time_source", lambda: "none")
    monkeypatch.setattr(system, "build_version", lambda: "v0.5.0-phase5")

    r = client.get("/status")
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "uptime_seconds": 123.45,
        "load_avg": [0.1, 0.2, 0.3],
        "storage": {"kiwix_bytes_free": 10, "kiwix_bytes_total": 100},
        "voltage": {"throttled": "0x0", "undervoltage": False},
        "dhcp_clients": 2,
        "time_source": "none",
        "build_version": "v0.5.0-phase5",
    }


def test_status_endpoint_handles_all_unknowns(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # If every probe fails the response should still be a 200 with nulls.
    monkeypatch.setattr(system, "uptime_seconds", lambda: None)
    monkeypatch.setattr(system, "load_avg", lambda: None)
    monkeypatch.setattr(
        system,
        "storage",
        lambda: system.StorageInfo(kiwix_bytes_free=None, kiwix_bytes_total=None),
    )
    monkeypatch.setattr(
        system,
        "voltage",
        lambda: system.VoltageInfo(throttled=None, undervoltage=None),
    )
    monkeypatch.setattr(system, "dhcp_clients", lambda: None)

    r = client.get("/status")
    assert r.status_code == 200
    body = r.json()
    assert body["uptime_seconds"] is None
    assert body["load_avg"] is None
    assert body["storage"]["kiwix_bytes_free"] is None
    assert body["voltage"]["undervoltage"] is None
    assert body["dhcp_clients"] is None
