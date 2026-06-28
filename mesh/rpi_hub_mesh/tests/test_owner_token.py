"""Owner-token reader tests for rpi-hub-mesh.

The per-domain split (`/etc/rpi-hub/mesh-owner-token` for peer
trust/block, `/etc/rpi-hub/notes-owner-token` for notes moderation) ships
with a legacy fallback so pre-v1.3 single-token deployments keep
working. These tests pin the fallback contract:

* mesh file present + non-empty → use it
* mesh file absent → fall back to legacy notes-owner-token
* mesh file present but empty → fall back to legacy
* both absent → return None (the endpoint will 503)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mesh.rpi_hub_mesh import main


def _set_paths(monkeypatch: pytest.MonkeyPatch, mesh: Path, legacy: Path) -> None:
    monkeypatch.setattr(main, "OWNER_TOKEN_PATH", mesh)
    monkeypatch.setattr(main, "LEGACY_OWNER_TOKEN_PATH", legacy)


def test_mesh_token_preferred_over_legacy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mesh_file = tmp_path / "mesh-owner-token"
    legacy_file = tmp_path / "notes-owner-token"
    mesh_file.write_text("mesh-token\n")
    legacy_file.write_text("legacy-token\n")
    _set_paths(monkeypatch, mesh_file, legacy_file)

    assert main._read_owner_token() == "mesh-token"


def test_fallback_to_legacy_when_mesh_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mesh_file = tmp_path / "mesh-owner-token"  # not created
    legacy_file = tmp_path / "notes-owner-token"
    legacy_file.write_text("legacy-token\n")
    _set_paths(monkeypatch, mesh_file, legacy_file)

    assert main._read_owner_token() == "legacy-token"


def test_fallback_when_mesh_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mesh_file = tmp_path / "mesh-owner-token"
    legacy_file = tmp_path / "notes-owner-token"
    mesh_file.write_text("")
    legacy_file.write_text("legacy-token\n")
    _set_paths(monkeypatch, mesh_file, legacy_file)

    assert main._read_owner_token() == "legacy-token"


def test_none_when_both_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mesh_file = tmp_path / "mesh-owner-token"
    legacy_file = tmp_path / "notes-owner-token"
    _set_paths(monkeypatch, mesh_file, legacy_file)

    assert main._read_owner_token() is None
