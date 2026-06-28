"""Unit tests for the SAME parser."""

from __future__ import annotations

from listen.rpi_hub_listen import same


def test_parses_canonical_test() -> None:
    line = "ZCZC-WXR-RWT-053009-053011+0015-3171800-KEAX/NWS-"
    out = same.parse(line)
    assert out is not None
    assert out.event_code == "RWT"
    assert out.event_label == "Required Weekly Test"
    assert "053009" in out.fips_codes
    assert "053011" in out.fips_codes
    assert out.duration_minutes == 15
    assert out.station == "KEAX/NWS"


def test_multimon_prefix_accepted() -> None:
    line = "EAS: ZCZC-WXR-TOR-031055+0030-1801800-KOAX/NWS-"
    out = same.parse(line)
    assert out is not None
    assert out.event_code == "TOR"
    assert out.duration_minutes == 30


def test_unknown_event_falls_through() -> None:
    line = "ZCZC-CIV-XYZ-053009+0010-3171800-KEAX/NWS-"
    out = same.parse(line)
    assert out is not None
    assert out.event_label == "XYZ"  # fallthrough


def test_garbage_returns_none() -> None:
    assert same.parse("not a SAME header at all") is None
    assert same.parse("") is None


def test_fips_filter() -> None:
    line = "ZCZC-WXR-TOR-053009-053011+0030-3171800-KEAX/NWS-"
    out = same.parse(line)
    assert out is not None
    assert out.affects_fips("")             # empty filter → always true
    assert out.affects_fips("053009")       # exact match
    assert out.affects_fips("153009")       # different subcounty digit, same county
    assert not out.affects_fips("019003")   # different county
