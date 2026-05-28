"""SAME (Specific Area Message Encoding) decoder helpers.

SAME headers are the EAS messages NOAA broadcasts over the WX
frequencies. Format::

    ZCZC-ORG-EEE-PSSCCC-PSSCCC+TTTT-JJJHHMM-LLLLLLLL-

We don't decode the audio ourselves — multimon-ng does that, and it
emits a single header line per alert. This module parses that line into
a typed record the service can pin to the landing page.

FIPS codes are six-digit numeric county identifiers. The optional
``fips_filter`` lets the operator restrict pinned alerts to their
county; everything else is logged but not promoted. That keeps the
landing-page red banner from going stale on alerts hundreds of miles
away.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# SAME header grammar: ZCZC-ORG-EEE-PSSCCC[-PSSCCC...]+TTTT-JJJHHMM-LLLLLLLL-
# FIPS codes are dash-separated; the *last* FIPS is followed directly by
# '+', not '-+'. So the FIPS blob is `\d{6}(?:-\d{6})*`, not
# `(\d{6}-)+`.
_HEADER = re.compile(
    r"ZCZC-([A-Z]{3})-([A-Z]{3})-(\d{6}(?:-\d{6})*)\+(\d{4})-(\d{7})-([A-Z0-9 /]{1,8})-?"
)

# Common EAS event codes → human label. Not exhaustive (NOAA publishes
# ~80 codes); the long tail falls through to the raw code.
EVENT_LABELS: dict[str, str] = {
    "RWT": "Required Weekly Test",
    "RMT": "Required Monthly Test",
    "TOA": "Tornado Watch",
    "TOR": "Tornado Warning",
    "SVR": "Severe Thunderstorm Warning",
    "SVA": "Severe Thunderstorm Watch",
    "FFW": "Flash Flood Warning",
    "FLW": "Flood Warning",
    "EQW": "Earthquake Warning",
    "TSW": "Tsunami Warning",
    "BZW": "Blizzard Warning",
    "WSW": "Winter Storm Warning",
    "WFW": "Red Flag / Wildfire Warning",
    "EVI": "Evacuation Immediate",
    "CDW": "Civil Danger Warning",
    "LAE": "Local Area Emergency",
    "HMW": "Hazardous Materials Warning",
}


@dataclass(frozen=True)
class SameAlert:
    originator: str
    event_code: str
    event_label: str
    fips_codes: list[str]
    duration_minutes: int
    issued_jjj_hhmm: str  # day-of-year + UTC hh:mm
    station: str
    raw: str

    def affects_fips(self, fips: str) -> bool:
        if not fips:
            return True  # no filter configured → all alerts affect us
        # SAME prefixes one leading digit (subcounty: 0 = entire county,
        # 1–9 = portion). Match against the trailing 5-digit county id so
        # a "0" full-county alert still hits a "5XXXXX" partial-county
        # filter and vice versa.
        target = fips[-5:] if len(fips) >= 5 else fips
        return any((c[-5:] if len(c) >= 5 else c) == target for c in self.fips_codes)


def parse(line: str) -> SameAlert | None:
    """Parse a single multimon-ng output line.

    multimon-ng prefixes its decoder output with "EAS: " — we accept both
    forms (raw and prefixed) so callers don't need to strip.
    """

    text = line.strip()
    if text.startswith("EAS:"):
        text = text[4:].strip()
    m = _HEADER.match(text)
    if m is None:
        return None
    org, event, fips_blob, duration_s, jjj_hhmm, station = m.groups()
    fips_codes = [c for c in fips_blob.split("-") if c]
    try:
        duration = int(duration_s)
    except ValueError:
        duration = 0
    minutes = (duration // 100) * 60 + (duration % 100)
    return SameAlert(
        originator=org,
        event_code=event,
        event_label=EVENT_LABELS.get(event, event),
        fips_codes=fips_codes,
        duration_minutes=minutes,
        issued_jjj_hhmm=jjj_hhmm,
        station=station.strip(),
        raw=text,
    )
