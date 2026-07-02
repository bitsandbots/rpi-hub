"""Unit tests for the radio bridges (LoRa + Wi-Fi).

We verify the *plumbing* — status state machine, frame dispatch,
parsing of ``batctl`` output — without touching real radios.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from mesh.rpi_hub_mesh import lora_bridge, wifi_bridge


def test_lora_bridge_reports_unavailable_when_socket_missing(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lora_bridge, "RETICULUM_SOCKET", str(tmp_path / "no-such.sock"))
    monkeypatch.setattr(lora_bridge, "CONNECT_RETRY_S", 0.05)
    seen: list[bytes] = []
    bridge = lora_bridge.LoraBridge(on_frame=seen.append)
    bridge.start()
    time.sleep(0.15)
    bridge.stop()
    assert bridge.status.state == "unavailable"
    assert seen == []


def test_wifi_bridge_reports_unavailable_when_batctl_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wifi_bridge, "BATCTL", "/nonexistent/batctl")
    monkeypatch.setattr(wifi_bridge, "POLL_INTERVAL_S", 0.05)
    seen: list[tuple[str, int, str]] = []
    bridge = wifi_bridge.WifiBridge(on_peer=lambda mac, tq, nh: seen.append((mac, tq, nh)))
    bridge.start()
    time.sleep(0.15)
    bridge.stop()
    assert bridge.status.state == "unavailable"
    assert seen == []


def test_wifi_bridge_parses_originator_line(monkeypatch: pytest.MonkeyPatch) -> None:
    # Inject a fake batctl that emits a canned originator list. The
    # bridge should call on_peer with the parsed fields.
    fake_output = (
        "aa:bb:cc:dd:ee:01    1.234s  (200) aa:bb:cc:dd:ee:02  [wlan1]\n"
        "aa:bb:cc:dd:ee:03    5.678s  (180) aa:bb:cc:dd:ee:04  [wlan1]\n"
    )

    class FakeResult:
        returncode = 0
        stdout = fake_output
        stderr = ""

    monkeypatch.setattr(wifi_bridge, "BATCTL", "/bin/true")  # exists check
    monkeypatch.setattr(wifi_bridge.os.path, "exists", lambda p: True)  # type: ignore[attr-defined]
    monkeypatch.setattr(
        wifi_bridge.subprocess,  # type: ignore[attr-defined]
        "run",
        lambda *a, **kw: FakeResult(),
    )
    monkeypatch.setattr(wifi_bridge, "POLL_INTERVAL_S", 0.05)

    seen: list[tuple[str, int, str]] = []
    bridge = wifi_bridge.WifiBridge(on_peer=lambda mac, tq, nh: seen.append((mac, tq, nh)))
    bridge.start()
    time.sleep(0.15)
    bridge.stop()

    assert ("aa:bb:cc:dd:ee:01", 200, "aa:bb:cc:dd:ee:02") in seen
    assert ("aa:bb:cc:dd:ee:03", 180, "aa:bb:cc:dd:ee:04") in seen
