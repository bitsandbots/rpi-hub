"""Pure-Python QR encoder for the mesh-fingerprint trust workflow.

Scope is deliberately narrow:

* **Versions 1-3** (21×21 / 25×25 / 29×29 matrices)
* **Byte mode** encoding (covers any ASCII payload)
* **ECC level M** (≈15% recovery — enough headroom against glare or
  camera tilt without bloating the matrix)
* **Single block per version** at this ECC level (so no interleaving
  complexity)
* All **8 mask patterns** evaluated; the lowest-penalty mask wins

The 29-char fingerprint we produce in ``identity._fingerprint`` fits
comfortably in version 3 (44 data codewords, ≈42 byte effective
capacity after the mode and length overhead). We auto-pick the
smallest version that fits, so callers can pass shorter strings and
get a smaller matrix.

Why a hand-rolled encoder: the project's offline-first invariant means
no extra apt/pip deps for a printable widget. ISO/IEC 18004:2015 is
small enough to implement directly for our narrow slice of the spec.
"""

from __future__ import annotations

from collections.abc import Callable

# ECC level M, one block per version:
#   version → (data codewords, ECC codewords)
_BLOCK_INFO: dict[int, tuple[int, int]] = {
    1: (16, 10),
    2: (28, 16),
    3: (44, 26),
}

# Alignment pattern centres (versions 2-3 have one each at (n-7, n-7)).
_ALIGN_CENTRES: dict[int, list[int]] = {
    1: [],
    2: [18],
    3: [22],
}

# QR specification constants for function patterns
_FINDER_PATTERN_SIZE = 7  # 7×7 pattern (indexed 0-6)
_FINDER_INNER_START = 2  # Inner white ring starts at distance 2 from edge
_FINDER_INNER_END = 4  # Inner dark center ends at distance 4 from edge
_TIMING_COLUMN = 6  # Vertical timing column position
_MIN_RUN_LENGTH = 5  # Minimum run length for penalty rule (ISO 18004 Rule 1)


# ---------------------------------------------------------------------------
# GF(256) arithmetic for Reed-Solomon ECC
# ---------------------------------------------------------------------------


def _gf_tables() -> tuple[list[int], list[int]]:
    """Log / antilog tables under primitive polynomial 0x11d."""

    exp = [0] * 512
    log = [0] * 256
    x = 1
    for i in range(255):
        exp[i] = x
        log[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        exp[i] = exp[i - 255]
    return exp, log


_EXP, _LOG = _gf_tables()


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _rs_generator(degree: int) -> list[int]:
    poly = [1]
    for i in range(degree):
        new = [0] * (len(poly) + 1)
        for j, c in enumerate(poly):
            new[j] ^= c
            new[j + 1] ^= _gf_mul(c, _EXP[i])
        poly = new
    return poly


def _rs_ecc(data: list[int], ecc_count: int) -> list[int]:
    gen = _rs_generator(ecc_count)
    rem = data + [0] * ecc_count
    for i in range(len(data)):
        coef = rem[i]
        if coef == 0:
            continue
        for j, g in enumerate(gen):
            rem[i + j] ^= _gf_mul(g, coef)
    return rem[len(data) :]


# ---------------------------------------------------------------------------
# Data encoding
# ---------------------------------------------------------------------------


def _pick_version(byte_len: int) -> int:
    """Smallest supported version that fits ``byte_len`` bytes."""

    overhead_bits = 4 + 8 + 4  # mode + 8-bit length + terminator
    needed = overhead_bits + 8 * byte_len
    for v, (data_words, _ecc) in _BLOCK_INFO.items():
        if data_words * 8 >= needed:
            return v
    raise ValueError(f"input too long for v1-3 ECC M (got {byte_len} bytes)")


def _encode_data_bits(data: bytes, version: int) -> list[int]:
    data_words, _ = _BLOCK_INFO[version]
    bits: list[int] = []
    # Byte mode = 0100
    bits.extend([0, 1, 0, 0])
    # 8-bit character count
    for b in range(7, -1, -1):
        bits.append((len(data) >> b) & 1)
    for byte in data:
        for b in range(7, -1, -1):
            bits.append((byte >> b) & 1)
    # Up to 4 zero terminator bits, capped at remaining capacity
    remaining = data_words * 8 - len(bits)
    bits.extend([0] * max(0, min(4, remaining)))
    # Pad to byte boundary, then fill with the spec pad bytes
    while len(bits) % 8 != 0:
        bits.append(0)
    codewords: list[int] = []
    for i in range(0, len(bits), 8):
        b = 0
        for j in range(8):
            b = (b << 1) | bits[i + j]
        codewords.append(b)
    while len(codewords) < data_words:
        codewords.append(0xEC)
        if len(codewords) < data_words:
            codewords.append(0x11)
    return codewords


def _data_plus_ecc_bits(data: bytes, version: int) -> list[int]:
    data_words, ecc_words = _BLOCK_INFO[version]
    codewords = _encode_data_bits(data, version)
    ecc = _rs_ecc(codewords, ecc_words)
    out: list[int] = []
    for byte in codewords + ecc:
        for b in range(7, -1, -1):
            out.append((byte >> b) & 1)
    return out


# ---------------------------------------------------------------------------
# Matrix placement
# ---------------------------------------------------------------------------


def _matrix_size(version: int) -> int:
    return 21 + 4 * (version - 1)


def _place_function_patterns(
    matrix: list[list[int]], reserved: list[list[bool]], version: int
) -> None:
    n = _matrix_size(version)

    def finder(top: int, left: int) -> None:
        for i in range(-1, 8):
            for j in range(-1, 8):
                r, c = top + i, left + j
                if not (0 <= r < n and 0 <= c < n):
                    continue
                reserved[r][c] = True
                if 0 <= i < _FINDER_PATTERN_SIZE and 0 <= j < _FINDER_PATTERN_SIZE:
                    on_ring = i in (0, _FINDER_PATTERN_SIZE - 1) or j in (
                        0,
                        _FINDER_PATTERN_SIZE - 1,
                    )
                    inner = (
                        _FINDER_INNER_START <= i <= _FINDER_INNER_END
                        and _FINDER_INNER_START <= j <= _FINDER_INNER_END
                    )
                    matrix[r][c] = 1 if (on_ring or inner) else 0
                else:
                    matrix[r][c] = 0

    finder(0, 0)
    finder(0, n - 7)
    finder(n - 7, 0)

    # Timing patterns
    for k in range(8, n - 8):
        matrix[6][k] = 1 - (k & 1)
        matrix[k][6] = 1 - (k & 1)
        reserved[6][k] = True
        reserved[k][6] = True

    # Dark module
    matrix[4 * version + 9][8] = 1
    reserved[4 * version + 9][8] = True

    # Format-info reservation (top-left strip + top-right strip + bottom-left strip)
    for k in range(9):
        reserved[8][k] = True
        reserved[k][8] = True
    for k in range(n - 8, n):
        reserved[8][k] = True
    for k in range(n - 7, n):
        reserved[k][8] = True

    # Alignment patterns (v2-3 only)
    for cy in _ALIGN_CENTRES[version]:
        for cx in _ALIGN_CENTRES[version]:
            for i in range(-2, 3):
                for j in range(-2, 3):
                    r, c = cy + i, cx + j
                    reserved[r][c] = True
                    on_ring = i in (-2, 2) or j in (-2, 2)
                    centre = i == 0 and j == 0
                    matrix[r][c] = 1 if (on_ring or centre) else 0


def _place_data_bits(
    matrix: list[list[int]],
    reserved: list[list[bool]],
    bits: list[int],
    version: int,
) -> None:
    n = _matrix_size(version)
    bit_idx = 0
    col = n - 1
    going_up = True
    while col > 0:
        if col == _TIMING_COLUMN:  # Skip vertical timing column
            col -= 1
        rows = range(n - 1, -1, -1) if going_up else range(n)
        for r in rows:
            for dc in (0, 1):
                c = col - dc
                if reserved[r][c]:
                    continue
                if bit_idx < len(bits):
                    matrix[r][c] = bits[bit_idx]
                else:
                    matrix[r][c] = 0  # Remainder bits (v1-3 have 0 remainder bits, but be safe)
                bit_idx += 1
        col -= 2
        going_up = not going_up


# ---------------------------------------------------------------------------
# Masking
# ---------------------------------------------------------------------------

_MASKS: list[Callable[[int, int], bool]] = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]


def _apply_mask(
    matrix: list[list[int]], reserved: list[list[bool]], mask_idx: int
) -> list[list[int]]:
    out = [row[:] for row in matrix]
    f = _MASKS[mask_idx]
    for r, row in enumerate(out):
        for c in range(len(row)):
            if not reserved[r][c] and f(r, c):
                row[c] ^= 1
    return out


def _penalty(matrix: list[list[int]]) -> int:  # noqa: PLR0912
    """ISO 18004 mask-penalty rules.

    Implements 4 distinct penalty rules (branches map 1:1 to QR spec sections).
    """

    n = len(matrix)
    p = 0

    # Rule 1: runs of ≥5 same-colour modules in a row/column.
    for r in range(n):
        run = 1
        for c in range(1, n):
            if matrix[r][c] == matrix[r][c - 1]:
                run += 1
            else:
                if run >= _MIN_RUN_LENGTH:
                    p += run - 2
                run = 1
        if run >= _MIN_RUN_LENGTH:
            p += run - 2
    for c in range(n):
        run = 1
        for r in range(1, n):
            if matrix[r][c] == matrix[r - 1][c]:
                run += 1
            else:
                if run >= _MIN_RUN_LENGTH:
                    p += run - 2
                run = 1
        if run >= _MIN_RUN_LENGTH:
            p += run - 2

    # Rule 2: 2×2 same-colour blocks.
    for r in range(n - 1):
        for c in range(n - 1):
            v = matrix[r][c]
            if matrix[r][c + 1] == v and matrix[r + 1][c] == v and matrix[r + 1][c + 1] == v:
                p += 3

    # Rule 3: finder-pattern-like 1011101 with adjacent quiet zone.
    pat = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    revpat = list(reversed(pat))
    for r in range(n):
        for c in range(n - 10):
            seg = [matrix[r][c + i] for i in range(11)]
            if seg in (pat, revpat):
                p += 40
    for c in range(n):
        for r in range(n - 10):
            seg = [matrix[r + i][c] for i in range(11)]
            if seg in (pat, revpat):
                p += 40

    # Rule 4: dark-module ratio.
    dark = sum(sum(row) for row in matrix)
    pct = dark * 100 // (n * n)
    p += abs(pct - 50) // 5 * 10
    return p


# ---------------------------------------------------------------------------
# Format-info word (BCH(15,5) over ECC level + mask + mask XOR pattern)
# ---------------------------------------------------------------------------


def _format_word(mask: int) -> int:
    """15-bit format info: 2-bit ECC indicator (M=00) + 3-bit mask + 10-bit BCH."""

    fmt = (0b00 << 3) | mask  # 5 data bits
    rem = fmt << 10
    g = 0b10100110111
    for i in range(4, -1, -1):
        if (rem >> (i + 10)) & 1:
            rem ^= g << i
    word = (fmt << 10) | (rem & 0x3FF)
    word ^= 0b101010000010010  # spec mask
    return word


def _place_format(matrix: list[list[int]], mask: int) -> None:
    n = len(matrix)
    word = _format_word(mask)
    bits = [(word >> i) & 1 for i in range(14, -1, -1)]  # MSB first

    # Top-left strip: row 8 cols 0..5, (8,7), (8,8), (7,8), rows 5..0 col 8
    a_coords = [
        (8, 0),
        (8, 1),
        (8, 2),
        (8, 3),
        (8, 4),
        (8, 5),
        (8, 7),
        (8, 8),
        (7, 8),
        (5, 8),
        (4, 8),
        (3, 8),
        (2, 8),
        (1, 8),
        (0, 8),
    ]
    # Bottom-left + top-right strips: rows n-1..n-7 col 8, then row 8 cols n-8..n-1
    b_coords = [
        (n - 1, 8),
        (n - 2, 8),
        (n - 3, 8),
        (n - 4, 8),
        (n - 5, 8),
        (n - 6, 8),
        (n - 7, 8),
        (8, n - 8),
        (8, n - 7),
        (8, n - 6),
        (8, n - 5),
        (8, n - 4),
        (8, n - 3),
        (8, n - 2),
        (8, n - 1),
    ]
    for i, (r, c) in enumerate(a_coords):
        matrix[r][c] = bits[i]
    for i, (r, c) in enumerate(b_coords):
        matrix[r][c] = bits[i]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def encode(text: str) -> list[list[int]]:
    """Return the QR matrix (1 = dark module) for ``text``."""

    data = text.encode("utf-8")
    version = _pick_version(len(data))
    n = _matrix_size(version)

    bits = _data_plus_ecc_bits(data, version)
    base_matrix = [[0] * n for _ in range(n)]
    reserved = [[False] * n for _ in range(n)]
    _place_function_patterns(base_matrix, reserved, version)
    _place_data_bits(base_matrix, reserved, bits, version)

    best: tuple[int, list[list[int]]] | None = None
    for mask in range(8):
        candidate = _apply_mask(base_matrix, reserved, mask)
        _place_format(candidate, mask)
        score = _penalty(candidate)
        if best is None or score < best[0]:
            best = (score, candidate)
    assert best is not None
    return best[1]


def to_svg(text: str, *, module_px: int = 8, quiet: int = 4) -> str:
    """Render the QR for ``text`` as a self-contained SVG document."""

    matrix = encode(text)
    n = len(matrix)
    size = (n + 2 * quiet) * module_px

    rects: list[str] = []
    for r, row in enumerate(matrix):
        c = 0
        while c < n:
            if row[c] == 1:
                start = c
                while c < n and row[c] == 1:
                    c += 1
                x = (start + quiet) * module_px
                y = (r + quiet) * module_px
                w = (c - start) * module_px
                rects.append(f'<rect x="{x}" y="{y}" width="{w}" height="{module_px}"/>')
            else:
                c += 1

    body = "".join(rects)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}" '
        f'shape-rendering="crispEdges" role="img" aria-label="QR code">'
        f'<rect width="{size}" height="{size}" fill="#ffffff"/>'
        f'<g fill="#000000">{body}</g>'
        f"</svg>"
    )
