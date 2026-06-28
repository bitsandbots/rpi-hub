"""Owner-token reader tests for rpi-hub-mesh.

The per-domain split (`/etc/rpi-hub/mesh-owner-token` for peer
trust/block, `/etc/rpi-hub/notes-owner-token` for notes moderation) keeps
the two trust domains independent. The legacy fallback to the *notes*
token collapses them, so it is now OFF by default and only re-enabled by
``rpi_hub_MESH_TOKEN_LEGACY_FALLBACK=1`` for pre-v1.3 single-token
deployments. These tests pin that contract:

* mesh file present + non-empty → use it (regardless of fallback flag)
* mesh absent/empty, fallback OFF → return None (endpoint 503s)
* mesh absent/empty, fallback ON → use legacy notes-owner-token
* both absent → return None
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mesh.rpi_hub_mesh import main


def _set_paths(
    monkeypatch: pytest.MonkeyPatch, mesh: Path, legacy: Path, *, fallback: bool = False
) -> None:
    monkeypatch.setattr(main, "OWNER_TOKEN_PATH", mesh)
    monkeypatch.setattr(main, "LEGACY_OWNER_TOKEN_PATH", legacy)
    monkeypatch.setattr(main, "_LEGACY_TOKEN_FALLBACK", fallback)


def test_mesh_token_preferred_over_legacy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mesh_file = tmp_path / "mesh-owner-token"
    legacy_file = tmp_path / "notes-owner-token"
    mesh_file.write_text("mesh-token\n")
    legacy_file.write_text("legacy-token\n")
    _set_paths(monkeypatch, mesh_file, legacy_file, fallback=True)

    assert main._read_owner_token() == "mesh-token"


def test_no_fallback_by_default_when_mesh_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Fallback OFF (default): a missing mesh token must NOT silently use
    # the notes token — the two trust domains stay separate.
    mesh_file = tmp_path / "mesh-owner-token"  # not created
    legacy_file = tmp_path / "notes-owner-token"
    legacy_file.write_text("legacy-token\n")
    _set_paths(monkeypatch, mesh_file, legacy_file, fallback=False)

    assert main._read_owner_token() is None


def test_fallback_to_legacy_when_opted_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mesh_file = tmp_path / "mesh-owner-token"  # not created
    legacy_file = tmp_path / "notes-owner-token"
    legacy_file.write_text("legacy-token\n")
    _set_paths(monkeypatch, mesh_file, legacy_file, fallback=True)

    assert main._read_owner_token() == "legacy-token"


def test_fallback_when_mesh_empty_and_opted_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mesh_file = tmp_path / "mesh-owner-token"
    legacy_file = tmp_path / "notes-owner-token"
    mesh_file.write_text("")
    legacy_file.write_text("legacy-token\n")
    _set_paths(monkeypatch, mesh_file, legacy_file, fallback=True)

    assert main._read_owner_token() == "legacy-token"


def test_none_when_both_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mesh_file = tmp_path / "mesh-owner-token"
    legacy_file = tmp_path / "notes-owner-token"
    _set_paths(monkeypatch, mesh_file, legacy_file, fallback=True)

    assert main._read_owner_token() is None
