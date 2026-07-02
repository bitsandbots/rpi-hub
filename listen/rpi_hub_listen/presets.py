"""Preset frequency loader.

Phase 9B writes ``/var/lib/rpi-hub/listen/noaa-presets.yaml`` when a
regional content pack is applied. The service reads it lazily so the
list stays in sync with the active pack.

Format (matches the pack schema)::

    preset_frequencies_mhz:
      - 162.400
      - 162.475

Falls back to the canonical 7 NOAA WX frequencies when no pack-supplied
presets exist — the device is still useful out of the box.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

NOAA_PRESETS_FILE = Path("/var/lib/rpi-hub/listen/noaa-presets.yaml")

# Canonical WX frequencies (MHz). Used when no pack has been applied.
NOAA_DEFAULTS_MHZ: tuple[float, ...] = (
    162.400,
    162.425,
    162.450,
    162.475,
    162.500,
    162.525,
    162.550,
)


@dataclass(frozen=True)
class Preset:
    label: str
    frequency_hz: int


def _to_hz(mhz: float) -> int:
    return int(round(mhz * 1_000_000))


def load_noaa() -> list[Preset]:
    if not NOAA_PRESETS_FILE.exists():
        return [
            Preset(label=f"NOAA {mhz:.3f} MHz", frequency_hz=_to_hz(mhz))
            for mhz in NOAA_DEFAULTS_MHZ
        ]
    # Hand-parse the trivial subset of YAML we emit. PyYAML is not
    # guaranteed to be installed on minimal Bookworm images, and bringing
    # in a dep for two-line files is overkill.
    presets: list[Preset] = []
    for line in NOAA_PRESETS_FILE.read_text().splitlines():
        s = line.strip()
        if not s.startswith("-"):
            continue
        token = s.lstrip("- ").strip()
        try:
            mhz = float(token)
        except ValueError:
            continue
        presets.append(Preset(label=f"NOAA {mhz:.3f} MHz", frequency_hz=_to_hz(mhz)))
    if not presets:
        return [
            Preset(label=f"NOAA {mhz:.3f} MHz", frequency_hz=_to_hz(mhz))
            for mhz in NOAA_DEFAULTS_MHZ
        ]
    return presets


# FM broadcast — every 200 kHz from 88.1 to 107.9 is the US allocation
# grid. We don't ship a per-region presets file in v0.8; the UI lets the
# user free-tune. This list is for the Broadcast tile dropdown.
FM_BAND = [
    Preset(label=f"FM {mhz:.1f}", frequency_hz=_to_hz(mhz))
    for mhz in (88.1, 91.5, 93.7, 96.3, 99.5, 101.1, 103.5, 105.7, 107.9)
]

# Ham band markers a non-licensed user might still find useful for
# context (calling frequencies, simplex coordination). Receive-only.
HAM_PRESETS = [
    Preset(label="146.520 — 2m simplex", frequency_hz=_to_hz(146.520)),
    Preset(label="446.000 — 70cm simplex", frequency_hz=_to_hz(446.000)),
    Preset(label="144.200 — 2m SSB calling", frequency_hz=_to_hz(144.200)),
]
