"""Unit tests for ``scripts/adsb_shield.py``.

The script is a one-shot triggered by ``signal-adsb-shield.timer`` —
read raw ``aircraft.json``, round per-aircraft ``lat``/``lon`` to the
precision in ``/etc/signal/adsb-precision``, write atomically. The
timer + service carry ``ConditionPathExists=`` so the systemd side of
the opt-in is shipped at the unit-file layer; here we just pin the
rounding contract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import adsb_shield  # noqa: E402


@pytest.fixture(autouse=True)
def _redirect_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the module's filesystem constants at tmp paths.

    The production paths are under /run and /etc — neither is safe to
    touch in a unit test. Returning the tmp dir lets each test seed
    files into the expected locations.
    """

    src = tmp_path / "aircraft.json"
    shielded = tmp_path / "aircraft.shielded.json"
    precision = tmp_path / "adsb-precision"
    monkeypatch.setattr(adsb_shield, "SOURCE", src)
    monkeypatch.setattr(adsb_shield, "SHIELDED", shielded)
    monkeypatch.setattr(adsb_shield, "PRECISION_FILE", precision)
    return tmp_path


def test_default_precision_is_one_decimal(tmp_path: Path) -> None:
    # No precision file → DEFAULT_PRECISION applies (~11 km).
    assert adsb_shield.read_precision(tmp_path / "missing") == 1


def test_blank_precision_falls_back_to_default(tmp_path: Path) -> None:
    p = tmp_path / "adsb-precision"
    p.write_text("\n")
    assert adsb_shield.read_precision(p) == 1


def test_invalid_precision_falls_back_to_default(tmp_path: Path) -> None:
    p = tmp_path / "adsb-precision"
    p.write_text("garbage")
    assert adsb_shield.read_precision(p) == 1


def test_precision_clamped_to_max(tmp_path: Path) -> None:
    p = tmp_path / "adsb-precision"
    p.write_text("99")
    assert adsb_shield.read_precision(p) == adsb_shield.MAX_PRECISION


def test_negative_precision_clamped_to_zero(tmp_path: Path) -> None:
    p = tmp_path / "adsb-precision"
    p.write_text("-3")
    assert adsb_shield.read_precision(p) == 0


def test_rounds_lat_lon_to_precision() -> None:
    body = {"aircraft": [{"hex": "a1b2c3", "lat": 47.6062123, "lon": -122.3320456}]}
    out = adsb_shield.round_positions(body, 1)
    assert out["aircraft"][0]["lat"] == 47.6
    assert out["aircraft"][0]["lon"] == -122.3


def test_aircraft_without_position_unchanged() -> None:
    body = {"aircraft": [{"hex": "abc", "alt_baro": 35000}]}
    out = adsb_shield.round_positions(body, 1)
    assert "lat" not in out["aircraft"][0]
    assert "lon" not in out["aircraft"][0]


def test_other_fields_preserved() -> None:
    body = {
        "now": 1700000000.5,
        "messages": 12345,
        "aircraft": [{"hex": "abc", "lat": 1.234, "lon": 5.678, "alt_baro": 10000}],
    }
    out = adsb_shield.round_positions(body, 0)
    assert out["now"] == 1700000000.5
    assert out["messages"] == 12345
    assert out["aircraft"][0]["alt_baro"] == 10000


def test_main_writes_shielded_when_source_present(_redirect_paths: Path) -> None:
    body = {"aircraft": [{"hex": "abc", "lat": 47.6062, "lon": -122.3320}]}
    adsb_shield.SOURCE.write_text(json.dumps(body))
    adsb_shield.PRECISION_FILE.write_text("2")

    rc = adsb_shield.main()
    assert rc == 0

    written = json.loads(adsb_shield.SHIELDED.read_text())
    assert written["aircraft"][0]["lat"] == 47.61
    assert written["aircraft"][0]["lon"] == -122.33


def test_main_noop_when_source_missing(_redirect_paths: Path) -> None:
    adsb_shield.PRECISION_FILE.write_text("1")
    rc = adsb_shield.main()
    assert rc == 0
    assert not adsb_shield.SHIELDED.exists()


def test_main_noop_on_garbage_source(_redirect_paths: Path) -> None:
    adsb_shield.SOURCE.write_text("{not json")
    adsb_shield.PRECISION_FILE.write_text("1")
    rc = adsb_shield.main()
    assert rc == 0
    assert not adsb_shield.SHIELDED.exists()


def test_write_is_atomic_via_rename(_redirect_paths: Path) -> None:
    """No partial-write window: the tmp file is renamed into place."""

    body = {"aircraft": [{"hex": "abc", "lat": 1.0, "lon": 2.0}]}
    adsb_shield.SOURCE.write_text(json.dumps(body))
    adsb_shield.PRECISION_FILE.write_text("0")
    adsb_shield.main()
    # The .tmp file is gone after os.replace; only the final file remains.
    assert adsb_shield.SHIELDED.exists()
    assert not adsb_shield.SHIELDED.with_suffix(".json.tmp").exists()
