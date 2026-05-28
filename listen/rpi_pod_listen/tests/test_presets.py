"""Unit tests for preset loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from listen.rpi_pod_listen import presets


def test_noaa_defaults_when_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(presets, "NOAA_PRESETS_FILE", tmp_path / "missing.yaml")
    out = presets.load_noaa()
    assert len(out) == len(presets.NOAA_DEFAULTS_MHZ)
    assert all("NOAA" in p.label for p in out)


def test_noaa_parses_pack_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    f = tmp_path / "noaa.yaml"
    f.write_text("preset_frequencies_mhz:\n  - 162.400\n  - 162.475\n")
    monkeypatch.setattr(presets, "NOAA_PRESETS_FILE", f)
    out = presets.load_noaa()
    assert [p.frequency_hz for p in out] == [162_400_000, 162_475_000]


def test_noaa_empty_file_falls_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    f = tmp_path / "empty.yaml"
    f.write_text("preset_frequencies_mhz:\n")
    monkeypatch.setattr(presets, "NOAA_PRESETS_FILE", f)
    out = presets.load_noaa()
    assert len(out) == len(presets.NOAA_DEFAULTS_MHZ)
