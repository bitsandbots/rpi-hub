"""Static + dynamic guards for ``scripts/readonly_root.sh``.

GAP §3c callout: the script has no harness, so a regression in the
overlay setup goes unnoticed until an operator boots a hub with the
overlay enabled and discovers nothing comes back. We can't safely
exercise ``enable`` / ``disable`` in CI (both touch ``/etc/fstab`` and
the initramfs), but we can:

1. **Static** — parse the script and pin the invariants a regression
   would break: the three subcommands, the require_root guard on
   destructive paths, the fstab begin/end marker pair (and that
   remove uses the same markers so disable is reversible), and the
   initramfs hook generation.

2. **Dynamic** — shell ``readonly_root.sh status`` (read-only) with a
   stubbed ``findmnt`` on PATH. We can't override the hard-coded
   ``MARKER`` / ``OVERLAY_BASE`` paths from outside, but we *can*
   confirm: the script runs to completion, exits 0, and prints the
   three label lines that the runbook in ``docs/OVERVIEW.md §7.1``
   tells operators to look for.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "readonly_root.sh"


# --------------------------------------------------------------------------- #
# Static
# --------------------------------------------------------------------------- #


def test_script_has_required_header() -> None:
    """check_config_header.py only walks config/ but the same convention
    applies — the rpi-hub repo's `set -euo pipefail` shell scripts all
    carry Purpose: / Unit: / Phase: lines."""

    text = SCRIPT.read_text()
    for needle in ("Purpose:", "Unit:", "Phase:"):
        assert needle in text, f"{needle} missing from readonly_root.sh header"


def test_script_defines_three_subcommands() -> None:
    text = SCRIPT.read_text()
    # Each subcommand is a shell function.
    assert "\nenable()" in text
    assert "\ndisable()" in text
    assert "\nstatus()" in text
    # And the case dispatch wires them.
    assert 'case "${1:-status}"' in text
    for verb in ("enable)", "disable)", "status)"):
        assert verb in text, f"case branch for {verb} missing"


def test_destructive_paths_require_root() -> None:
    """enable and disable touch the initramfs + fstab; they must guard
    on EUID before doing anything. status is intentionally allowed for
    non-root operators reading the runbook."""

    text = SCRIPT.read_text()
    # Both functions should call require_root as their first action.
    for func in ("enable()", "disable()"):
        start = text.index(func)
        body = text[start : start + 200]
        assert "require_root" in body, f"{func} does not call require_root early"


def test_fstab_marker_pair_is_symmetric() -> None:
    """write_fstab_block and remove_fstab_block must use the same
    begin/end markers — otherwise disable would leave the block in
    /etc/fstab forever."""

    text = SCRIPT.read_text()
    begin = "# >>> rpi-hub Phase 1.1 (readonly root) >>>"
    end = "# <<< rpi-hub Phase 1.1 (readonly root) <<<"
    # Both markers must appear in the writer (set-up) and the sed
    # script that strips the block.
    assert text.count(begin) >= 2, "fstab begin marker not in both write and remove"
    assert text.count(end) >= 2, "fstab end marker not in both write and remove"


def test_initramfs_hook_generated_and_removed() -> None:
    """enable writes the overlay init-bottom hook; disable removes it.
    Without the cleanup, disable would leave the kernel mounting an
    overlay over the freshly-disabled root."""

    text = SCRIPT.read_text()
    hook_path = "/usr/share/initramfs-tools/scripts/init-bottom/rpi-hub-overlay"
    assert hook_path in text
    # rm -f on the hook must appear in disable() — guard against a
    # refactor that drops the cleanup.
    disable_start = text.index("disable()")
    disable_end = text.index("status()", disable_start)
    disable_body = text[disable_start:disable_end]
    assert f"rm -f {hook_path}" in disable_body


def test_overlay_carves_keys_and_kiwix_per_design() -> None:
    """The header comment promises keys, kiwix, etc. are *not* on the
    overlay. If a refactor drops that contract from either the comment
    or the actual implementation we want to know — operators trust the
    runbook."""

    text = SCRIPT.read_text()
    # Header lists the carve-out reasons.
    assert "kiwix" in text.lower()
    assert "keypair" in text.lower() or "keys" in text.lower()


def test_persistent_state_paths_are_bound() -> None:
    """Regression for the bug where overlay-root regenerated the mesh
    identity every boot: the state dirs that must survive boots have to be
    declared in PERSIST_PATHS and bound in the initramfs hook, not left on
    the volatile tmpfs upper."""

    text = SCRIPT.read_text()
    assert "PERSIST_PATHS=(" in text, "PERSIST_PATHS list missing"
    for required in ("/etc/rpi-hub", "/var/lib/rpi-hub", "/var/lib/dnsmasq"):
        assert required in text, f"{required} not declared persistent"
    # The hook must actually bind them and the upper must be volatile tmpfs.
    assert "bind_persist" in text
    assert "mount --bind" in text
    assert "tmpfs" in text and "upper" in text


# --------------------------------------------------------------------------- #
# Dynamic — exercise `status` with stubbed findmnt/du.
# --------------------------------------------------------------------------- #


def _make_stub(bin_dir: Path, name: str, stdout: str, rc: int = 0) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake = bin_dir / name
    fake.write_text(f"#!/usr/bin/env bash\nprintf '%s' {stdout!r}\nexit {rc}\n")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return fake


@pytest.fixture
def stubbed_status_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """PATH-prefix a tmp bin with stub findmnt + du."""

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # Default stub findmnt: says rootfs is "ext4 rw" — i.e., overlay marker
    # absent. The script's current_mode() looks for the literal string
    # 'overlay' in `findmnt -n -o FSTYPE /`, so emitting 'ext4' is the
    # cleanest unambiguous "not overlay" answer.
    _make_stub(bin_dir, "findmnt", "ext4\n", rc=0)
    _make_stub(bin_dir, "du", "0\t.\n", rc=0)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return bin_dir


def test_status_runs_and_emits_three_label_lines(stubbed_status_env: Path) -> None:  # noqa: ARG001
    if shutil.which("bash") is None:
        pytest.skip("bash not on PATH")
    r = subprocess.run(
        ["bash", str(SCRIPT), "status"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    out = r.stdout
    # The runbook in docs/OVERVIEW.md §7.1 cites these three lines.
    assert "overlay marker" in out
    assert "current root" in out
    assert "upper" in out


def test_status_is_default_when_no_arg(stubbed_status_env: Path) -> None:  # noqa: ARG001
    """`bash readonly_root.sh` with no args runs status, not usage."""

    if shutil.which("bash") is None:
        pytest.skip("bash not on PATH")
    r = subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert "overlay marker" in r.stdout


def test_unknown_subcommand_errors_with_usage_line(
    stubbed_status_env: Path,
) -> None:  # noqa: ARG001
    if shutil.which("bash") is None:
        pytest.skip("bash not on PATH")
    r = subprocess.run(
        ["bash", str(SCRIPT), "wat"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode != 0
    assert "usage" in r.stderr.lower()
