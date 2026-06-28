"""Guard that owner-token comparisons use secrets.compare_digest.

A plain ``==`` / ``!=`` comparison short-circuits on the first differing
byte, leaking length and prefix information through response timing.
Both ``notes/rpi_hub_notes/main.py`` and ``mesh/rpi_hub_mesh/main.py``
must use ``secrets.compare_digest`` for the owner-token check.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

OWNER_TOKEN_FILES = [
    REPO_ROOT / "notes" / "rpi_hub_notes" / "main.py",
    REPO_ROOT / "mesh" / "rpi_hub_mesh" / "main.py",
]


@pytest.mark.parametrize("src_file", OWNER_TOKEN_FILES, ids=lambda p: p.parent.name)
def test_uses_compare_digest(src_file: Path) -> None:
    text = src_file.read_text()
    assert "secrets.compare_digest" in text, (
        f"{src_file.relative_to(REPO_ROOT)}: owner-token comparison must use "
        "secrets.compare_digest() to avoid timing side-channels"
    )


@pytest.mark.parametrize("src_file", OWNER_TOKEN_FILES, ids=lambda p: p.parent.name)
def test_no_plain_token_equality(src_file: Path) -> None:
    """Neither file should compare the owner token with == or !=."""
    text = src_file.read_text()
    # Narrow the check to the _require_owner function so we don't flag
    # unrelated comparisons elsewhere in the file.
    if "_require_owner" not in text:
        pytest.skip(f"no _require_owner in {src_file.name}")
    fn_start = text.index("def _require_owner")
    # Grab up to 30 lines of the function body — plenty to capture the comparison.
    fn_body = "\n".join(text[fn_start:].splitlines()[:30])
    assert "token_header !=" not in fn_body and "token_header ==" not in fn_body, (
        f"{src_file.relative_to(REPO_ROOT)}: _require_owner must not use plain == / != "
        "for token comparison; use secrets.compare_digest() instead"
    )
