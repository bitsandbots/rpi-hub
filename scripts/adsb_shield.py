#!/usr/bin/env python3
"""Opt-in ADS-B position-rounding for /adsb/aircraft.json.

dump1090-mutability writes per-aircraft lat/lon to
``/run/dump1090-mutability/aircraft.json`` once per second. Anyone on
the open SSID can poll that file via nginx's ``/adsb/`` alias. For
deployments where exposing precise tracks is PII-adjacent, the operator
opts in by writing a number of decimal places into
``/etc/signal/adsb-precision`` (0–4). When the file exists, the
``signal-adsb-shield.timer`` wakes this script once per second; the
script rounds every aircraft's ``lat``/``lon`` to that precision and
writes ``aircraft.shielded.json`` next to the source. nginx prefers the
shielded copy when present (see ``config/nginx/signal-portal.conf``).

Precision reference (mid-latitudes): 0 ≈ 110 km, 1 ≈ 11 km, 2 ≈ 1.1 km,
3 ≈ 110 m, 4 ≈ 11 m. Default precision when the file contains a blank
or non-integer line is 1 (≈ 11 km — coarse enough that an attacker
cannot resolve a single household).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

SOURCE = Path("/run/dump1090-mutability/aircraft.json")
SHIELDED = Path("/run/dump1090-mutability/aircraft.shielded.json")
PRECISION_FILE = Path("/etc/signal/adsb-precision")
DEFAULT_PRECISION = 1
MAX_PRECISION = 4


def read_precision(path: Path | None = None) -> int:
    # PRECISION_FILE is resolved at call time (not as a default arg) so
    # monkeypatch.setattr(adsb_shield, "PRECISION_FILE", ...) takes
    # effect in tests.
    target = path if path is not None else PRECISION_FILE
    try:
        raw = target.read_text(encoding="utf-8").strip()
    except OSError:
        return DEFAULT_PRECISION
    if not raw:
        return DEFAULT_PRECISION
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_PRECISION
    if n < 0:
        return 0
    if n > MAX_PRECISION:
        return MAX_PRECISION
    return n


def round_positions(body: dict[str, Any], precision: int) -> dict[str, Any]:
    aircraft = body.get("aircraft")
    if not isinstance(aircraft, list):
        return body
    for a in aircraft:
        if not isinstance(a, dict):
            continue
        for key in ("lat", "lon"):
            v = a.get(key)
            if isinstance(v, (int, float)):
                a[key] = round(float(v), precision)
    return body


def write_atomic(path: Path, payload: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(payload)
    os.replace(tmp, path)


def main() -> int:
    try:
        raw = SOURCE.read_bytes()
    except OSError:
        return 0  # dump1090 may not have written yet; nothing to shield
    try:
        body = json.loads(raw)
    except ValueError:
        return 0
    if not isinstance(body, dict):
        return 0
    precision = read_precision()
    shielded = round_positions(body, precision)
    write_atomic(SHIELDED, json.dumps(shielded, separators=(",", ":")).encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
