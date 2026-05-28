"""Unit tests for the manifest writer."""

from __future__ import annotations

from pathlib import Path

from indexer import manifest


def test_manifest_round_trip(tmp_path: Path) -> None:
    m = manifest.IndexManifest(
        chunk_count=10,
        token_count=1234,
        source_zims=[{"name": "wikipedia.zim", "sha256": "deadbeef"}],
    )
    out = tmp_path / "manifest.yaml"
    manifest.write_manifest(out, m)
    text = out.read_text()
    assert "layout_version: 1" in text
    assert "embedding_model: BAAI/bge-small-en-v1.5" in text
    assert "chunk_count: 10" in text
    assert "wikipedia.zim" in text
    assert "deadbeef" in text


def test_layout_version_pinned() -> None:
    # If you bump this, rpi-pod-retrieve must learn to handle the new layout.
    assert manifest.INDEX_LAYOUT_VERSION == 1
