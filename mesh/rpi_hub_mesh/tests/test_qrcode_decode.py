"""Real-decoder round trip for the vendored QR encoder.

GAP §5 callout: the existing test_qrcode.py asserts structural
invariants (finder patterns, timing rows, mask format word) but never
hands the output to a real decoder. The risk is a QR that "looks
right" on paper but no phone camera can read.

The decoder + rasteriser dependencies are deliberately not in
pyproject — they would pull system libraries (zbar, cairo) that we
don't want on the Pi image. We import them defensively and skip
cleanly when any are missing.

Strategy:
  1. Build a matrix directly via ``qrcode.encode`` and rasterise it
     ourselves into a numpy/Pillow image (no external rasteriser
     needed). This is the *preferred* path because it sidesteps the
     SVG-to-PNG step entirely.
  2. Fall back to ``cairosvg`` → PNG bytes → Pillow if the direct
     bitmap path isn't enough.

Decoder candidates, in priority order: ``pyzbar`` (libzbar binding).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from mesh.rpi_hub_mesh import qrcode


def _import_optional() -> tuple[object, Callable[..., Any]]:
    """Resolve (PIL.Image, pyzbar.decode) or skip with a clear message."""

    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError:
        pytest.skip("Pillow unavailable; install pillow to run QR decode round-trip")

    try:
        from pyzbar.pyzbar import decode  # noqa: PLC0415
    except ImportError:
        pytest.skip("pyzbar unavailable; install pyzbar + libzbar0 to run QR decode round-trip")

    return Image, decode


def _matrix_to_image(matrix: list[list[int]], scale: int = 8, quiet: int = 4) -> object:
    """Rasterise a QR matrix to a Pillow image directly, no SVG step.

    A dark module is 0 (black), a light module is 255 (white). The
    quiet zone around the matrix is mandatory for decoder lock-on.
    """

    from PIL import Image  # noqa: PLC0415

    n = len(matrix)
    side = (n + 2 * quiet) * scale
    img = Image.new("L", (side, side), 255)
    pixels = img.load()
    for r in range(n):
        for c in range(n):
            if matrix[r][c] == 1:
                x0 = (c + quiet) * scale
                y0 = (r + quiet) * scale
                for dx in range(scale):
                    for dy in range(scale):
                        pixels[x0 + dx, y0 + dy] = 0
    return img


def test_qr_decodes_back_to_fingerprint() -> None:
    """Encode → rasterise → decode → assert text equality.

    Uses the fingerprint shape we actually emit, so this guards the
    real-world case (a 29-char identity string) not just toy input.
    """

    _Image, decode = _import_optional()

    fingerprint = "ABCD-EFGH-IJKL-MNOP-QRST-UVWX"
    matrix = qrcode.encode(fingerprint)
    img = _matrix_to_image(matrix, scale=8, quiet=4)

    results = decode(img)
    assert results, "no QR found in the rasterised matrix"
    decoded = results[0].data.decode("utf-8")
    assert decoded == fingerprint


def test_qr_decodes_short_string() -> None:
    """Smaller payload lands in version 1 — verify the decoder still
    locks on at the lower module count."""

    _Image, decode = _import_optional()

    payload = "hi"
    matrix = qrcode.encode(payload)
    img = _matrix_to_image(matrix, scale=10, quiet=4)

    results = decode(img)
    assert results, "no QR found for short payload"
    assert results[0].data.decode("utf-8") == payload
