"""Static + dynamic guards for ``phase8_adsb()`` in ``install.sh``.

GAP §5 callout: ``phase8_adsb`` decides whether to enable
``dump1090-mutability`` based on USB dongle detection. There was no
automated test, so a regression silently disables ADS-B on every
install.

Two layers of defence:

1. **Static** — parse ``install.sh`` + ``scripts/detect_rtlsdr.sh`` and
   assert the dongle VID:PIDs we ship for. This catches accidental
   deletions of the dongle list or the gate call.
2. **Dynamic** — shell ``scripts/detect_rtlsdr.sh`` with a fake
   ``lsusb`` on ``PATH``, once printing a known RTL-SDR id (exit 0,
   stdout ``present``) and once printing nothing (exit 1, stdout
   ``absent``). This exercises the matcher itself without needing a
   real dongle on a CI runner.

We never invoke ``apt-get`` or ``systemctl`` — those are guarded inside
``phase8_adsb`` only after detection succeeds, and we don't shell the
whole install script.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SH = REPO_ROOT / "install.sh"
DETECT_SH = REPO_ROOT / "scripts" / "detect_rtlsdr.sh"

# A representative subset of the VID:PIDs librtlsdr claims. The full
# list lives in detect_rtlsdr.sh; we sanity-check that the two most
# common ones are still present.
KNOWN_RTLSDR_IDS = ("0bda:2832", "0bda:2838")


# --------------------------------------------------------------------------- #
# Static: install.sh and detect_rtlsdr.sh look the way we expect.
# --------------------------------------------------------------------------- #


def test_install_sh_defines_phase8_adsb() -> None:
    text = INSTALL_SH.read_text()
    assert "phase8_adsb()" in text, "phase8_adsb function missing from install.sh"
    # phase8 must actually invoke phase8_adsb — otherwise the ADS-B
    # gate is dead code.
    assert "    phase8_adsb" in text or "\nphase8_adsb" in text


def test_install_sh_gates_on_detect_script() -> None:
    """install.sh's phase8_adsb must defer the VID:PID match to
    detect_rtlsdr.sh — otherwise install.sh and the script can drift."""

    text = INSTALL_SH.read_text()
    assert "scripts/detect_rtlsdr.sh" in text


def test_shield_extracted_into_own_function() -> None:
    """adsb_shield install must live in phase8_adsb_shield(), not phase8_adsb().

    phase8_adsb() early-returns when dump1090-mutability is absent; the
    shield is decoder-independent and must not be gated on that package.
    """
    text = INSTALL_SH.read_text()
    assert "phase8_adsb_shield()" in text, "phase8_adsb_shield function missing from install.sh"
    # adsb_shield.py install must appear inside the shield function, not inside
    # phase8_adsb. We verify by checking the text between the two function headers.
    adsb_fn_start = text.index("phase8_adsb()")
    shield_fn_start = text.index("phase8_adsb_shield()")
    adsb_fn_body = text[adsb_fn_start:shield_fn_start]
    assert "adsb_shield.py" not in adsb_fn_body, (
        "adsb_shield.py install must be in phase8_adsb_shield(), not phase8_adsb()"
    )


def test_phase8_calls_shield_unconditionally() -> None:
    """phase8() must call phase8_adsb_shield unconditionally (not nested inside phase8_adsb)."""
    text = INSTALL_SH.read_text()
    # Locate the phase8() function body (between its opening line and the next top-level function).
    phase8_start = text.index("\nphase8() {")
    # Find the next top-level function after phase8_adsb_shield
    after = text.find("\nphase8_adsb()", phase8_start)
    phase8_body = text[phase8_start:after]
    assert "phase8_adsb_shield" in phase8_body, (
        "phase8() must call phase8_adsb_shield unconditionally"
    )


def test_detect_rtlsdr_lists_known_dongles() -> None:
    """A regression that drops the canonical Realtek IDs would silently
    leave every device looking ADS-B-capable as if it had no dongle."""

    text = DETECT_SH.read_text()
    for vid_pid in KNOWN_RTLSDR_IDS:
        assert vid_pid in text, f"{vid_pid} missing from detect_rtlsdr.sh"


# --------------------------------------------------------------------------- #
# Dynamic: stub lsusb and exercise detect_rtlsdr.sh end-to-end.
# --------------------------------------------------------------------------- #


def _make_fake_lsusb(bin_dir: Path, output: str) -> Path:
    """Drop a fake ``lsusb`` into a tmp dir and make it executable."""

    bin_dir.mkdir(parents=True, exist_ok=True)
    fake = bin_dir / "lsusb"
    fake.write_text(f"#!/usr/bin/env bash\nprintf '%s\\n' {output!r}\n")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return fake


@pytest.fixture
def stubbed_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Prepend a writable bin dir to PATH so we control ``lsusb``.

    We keep the rest of PATH intact (the detect script also needs
    ``grep``, ``command``).
    """

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return bin_dir


def _run_detect() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(DETECT_SH)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_detect_returns_present_when_known_id_on_bus(stubbed_path: Path) -> None:
    if shutil.which("bash") is None:
        pytest.skip("bash not on PATH; can't exercise detect_rtlsdr.sh")
    _make_fake_lsusb(
        stubbed_path,
        # A real lsusb line for a Realtek RTL2832U dongle.
        "Bus 001 Device 005: ID 0bda:2838 Realtek Semiconductor Corp. RTL2838 DVB-T",
    )
    result = _run_detect()
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "present"


def test_detect_returns_absent_when_no_known_id(stubbed_path: Path) -> None:
    if shutil.which("bash") is None:
        pytest.skip("bash not on PATH; can't exercise detect_rtlsdr.sh")
    _make_fake_lsusb(
        stubbed_path,
        # Some other USB device — the detector must say absent.
        "Bus 001 Device 002: ID 1d6b:0002 Linux Foundation 2.0 root hub",
    )
    result = _run_detect()
    assert result.returncode == 1
    assert result.stdout.strip() == "absent"


def test_detect_returns_absent_when_lsusb_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No ``lsusb`` on PATH (e.g. minimal image) must degrade to
    "absent" rather than crashing the install."""

    if shutil.which("bash") is None:
        pytest.skip("bash not on PATH; can't exercise detect_rtlsdr.sh")
    # PATH containing nothing but a tmp dir → no lsusb, no usbutils.
    empty_bin = tmp_path / "emptybin"
    empty_bin.mkdir()
    # Keep /bin so bash + grep are reachable.
    monkeypatch.setenv("PATH", f"{empty_bin}{os.pathsep}/usr/bin{os.pathsep}/bin")
    result = _run_detect()
    assert result.returncode == 1
    assert result.stdout.strip() == "absent"
