"""Unit tests for the vendored QR encoder.

We do not have an external QR decoder on the test path, so the tests
focus on **structural invariants** every valid QR matrix must satisfy:

* The selected version matches the input length (auto-sizing).
* The three finder patterns are in place at the corners.
* The dark module sits at (4·V + 9, 8).
* Each version's alignment-pattern centre is dark.
* The timing rows on row/col 6 alternate.
* The SVG output is well-formed text we can hand to nginx.

If a decoder is ever added to the toolchain (e.g. zbar-py for a
contributor's dev box), it would slot in alongside these as an
end-to-end round trip.
"""

from __future__ import annotations

import re

from mesh.rpi_hub_mesh import qrcode


def _check_finders(matrix: list[list[int]]) -> None:
    n = len(matrix)
    for top, left in [(0, 0), (0, n - 7), (n - 7, 0)]:
        # Outer ring should be all dark.
        for k in range(7):
            assert matrix[top + 0][left + k] == 1
            assert matrix[top + 6][left + k] == 1
            assert matrix[top + k][left + 0] == 1
            assert matrix[top + k][left + 6] == 1
        # 3×3 dark core.
        for i in range(2, 5):
            for j in range(2, 5):
                assert matrix[top + i][left + j] == 1
        # White separator between ring and core (one ring of zeros).
        for k in range(1, 6):
            assert matrix[top + 1][left + k] == 0
            assert matrix[top + 5][left + k] == 0
            assert matrix[top + k][left + 1] == 0
            assert matrix[top + k][left + 5] == 0


def test_short_input_lands_in_version_1() -> None:
    matrix = qrcode.encode("hi")
    assert len(matrix) == 21
    _check_finders(matrix)


def test_fingerprint_length_lands_in_version_3() -> None:
    fp = "ABCD-EFGH-IJKL-MNOP-QRST-UVWX"
    matrix = qrcode.encode(fp)
    assert len(matrix) == 29  # version 3
    _check_finders(matrix)
    # Dark module
    assert matrix[4 * 3 + 9][8] == 1
    # Alignment centre at (22, 22)
    assert matrix[22][22] == 1


def test_timing_patterns_alternate() -> None:
    matrix = qrcode.encode("test data")
    n = len(matrix)
    for k in range(8, n - 8):
        assert matrix[6][k] == 1 - (k & 1)
        assert matrix[k][6] == 1 - (k & 1)


def test_oversize_input_raises() -> None:
    # v3 ECC M caps around 42 effective bytes.
    import pytest

    with pytest.raises(ValueError):
        qrcode.encode("x" * 200)


def test_svg_is_well_formed() -> None:
    svg = qrcode.to_svg("ABCD-EFGH-IJKL-MNOP-QRST-UVWX")
    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    # Must declare an XML namespace so nginx serves it as a real SVG.
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    # White background rect (for QR contrast).
    assert 'fill="#ffffff"' in svg
    # Dark modules are rendered via at least one rect under the black group.
    assert '<g fill="#000000">' in svg
    assert "<rect" in svg
    # No raw script tags or external refs — defends against an
    # accidental XSS surface if we ever serve this through the portal.
    assert "<script" not in svg
    assert "xlink:href" not in svg


def test_svg_module_size_is_configurable() -> None:
    small = qrcode.to_svg("hello", module_px=4, quiet=2)
    big = qrcode.to_svg("hello", module_px=12, quiet=2)
    # The bigger module size produces a larger viewBox dimension.
    small_size = int(re.search(r'viewBox="0 0 (\d+)', small).group(1))  # type: ignore[union-attr]
    big_size = int(re.search(r'viewBox="0 0 (\d+)', big).group(1))  # type: ignore[union-attr]
    assert big_size == small_size * 3


def test_encoded_matrix_is_deterministic() -> None:
    a = qrcode.encode("ABCD-EFGH-IJKL-MNOP-QRST-UVWX")
    b = qrcode.encode("ABCD-EFGH-IJKL-MNOP-QRST-UVWX")
    assert a == b
