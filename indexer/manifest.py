"""Manifest writer for built indexes.

The manifest pins:

* indexer version (so rpi-pod-retrieve can refuse mismatched layouts)
* embedding model + dimension
* HNSW parameters (ef_construction, M)
* chunk count and total token count
* source ZIMs (name + sha256)

It's a small YAML file rather than JSON because the rest of the project
already uses YAML for ``content/manifest.yaml`` and there's no upside to
mixing formats.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

# Layout version. Bump whenever rpi-pod-retrieve's expectations of the
# index directory change — older runtimes will refuse to serve a newer
# index rather than mis-interpret it.
INDEX_LAYOUT_VERSION = 1


@dataclass
class IndexManifest:
    layout_version: int = INDEX_LAYOUT_VERSION
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    hnsw_ef_construction: int = 200
    hnsw_M: int = 16
    chunk_count: int = 0
    token_count: int = 0
    source_zims: list[dict[str, str]] = field(default_factory=list)

    def to_yaml(self) -> str:
        """Hand-rolled YAML writer — no PyYAML dep needed at build time.

        We only emit primitives, lists, and shallow dicts so this is safe.
        """

        d = asdict(self)
        lines: list[str] = []
        for k, v in d.items():
            if isinstance(v, list):
                lines.append(f"{k}:")
                for item in v:
                    lines.append("  -")
                    for ik, iv in item.items():
                        lines.append(f"    {ik}: {iv!s}")
            else:
                lines.append(f"{k}: {v!s}")
        return "\n".join(lines) + "\n"


def write_manifest(path: Path, manifest: IndexManifest) -> None:
    path.write_text(manifest.to_yaml())
