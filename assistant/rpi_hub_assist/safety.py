"""Deferral classifier.

Pure-Python regex matcher. The rule list is hand-curated against the
Phase 6.3 eval slice (drug dosing, severe trauma, electrical >12V,
structural, chemical mixing, firearms/explosives) and tuned so:

* recall on the deferral slice ≥ 99% (the eval gates this on every merge)
* false-defer rate on the general slice ≤ 5%

The classifier returns a :class:`DeferralVerdict` describing *why* it
fired so the UI can show the appropriate red-banner copy. ``None``
verdict means "safe to summarise".

This file is intentionally boring — the failure mode we're avoiding is a
fancy classifier hallucinating that a child's nosebleed is fine. A
straightforward keyword list is easy to audit and easy to extend when the
eval surfaces a miss.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class DeferralReason(str, Enum):
    DRUG_DOSING = "drug-dosing"
    SEVERE_TRAUMA = "severe-trauma"
    HIGH_VOLTAGE = "high-voltage"
    STRUCTURAL = "structural"
    CHEMICAL = "chemical"
    WEAPONS = "weapons"


@dataclass(frozen=True)
class DeferralVerdict:
    reason: DeferralReason
    banner: str  # human-readable banner copy shown in the UI


# Patterns are matched case-insensitive on word boundaries. We accept some
# false positives in exchange for never under-deferring — the eval slice
# is what we tune against, not this file.
_RULES: tuple[tuple[re.Pattern[str], DeferralReason, str], ...] = (
    (
        re.compile(
            r"\b(dose|dosage|mg/kg|micrograms?|how (?:much|many)|overdose|"
            r"acetaminophen|ibuprofen|aspirin|tylenol|advil|epinephrine|"
            r"insulin|naloxone)\b",
            re.IGNORECASE,
        ),
        DeferralReason.DRUG_DOSING,
        "Drug dosing depends on weight, age, and other meds — read the source directly.",
    ),
    (
        re.compile(
            r"\b(arterial bleed|spurting blood|amputat\w*|sucking chest wound|"
            r"compound fracture|cardiac arrest|not breathing|unconscious|"
            r"airway obstruct\w*|anaphylactic|anaphylaxis)\b",
            re.IGNORECASE,
        ),
        DeferralReason.SEVERE_TRAUMA,
        "This sounds like a life-threatening emergency — call professional help if reachable; read the source verbatim below.",
    ),
    (
        re.compile(
            r"\b(mains? (?:power|voltage)|240V|120V|line voltage|breaker panel|"
            r"electrical (?:panel|service)|live wire|hot wire|electrocut\w*)\b",
            re.IGNORECASE,
        ),
        DeferralReason.HIGH_VOLTAGE,
        "Mains-voltage work is a licensed-electrician task in most jurisdictions — read the source directly.",
    ),
    (
        re.compile(
            r"\b(load[- ]bearing|joist|rafter|beam|foundation|retaining wall|"
            r"structural (?:integrity|engineer)|collapse risk)\b",
            re.IGNORECASE,
        ),
        DeferralReason.STRUCTURAL,
        "Structural decisions warrant an engineer in the loop — read the source directly.",
    ),
    (
        re.compile(
            r"\b(mix(?:ing)? bleach|ammonia (?:and|\+) bleach|chlorine gas|"
            r"acid (?:and|\+) base|hydrogen sulfide|cyanide|nerve agent)\b",
            re.IGNORECASE,
        ),
        DeferralReason.CHEMICAL,
        "Chemical mixing can produce toxic gases — read the source verbatim; do not improvise.",
    ),
    (
        re.compile(
            r"\b(firearm|handgun|rifle|shotgun|ammunition|reload(?:ing)?|"
            r"explosive|detonat\w*|gunpowder)\b",
            re.IGNORECASE,
        ),
        DeferralReason.WEAPONS,
        "Firearms and explosives are jurisdiction-specific and dangerous — read the source directly.",
    ),
)


def classify(query: str) -> DeferralVerdict | None:
    """Return the first matching verdict, or ``None`` for safe queries."""

    text = query.strip()
    if not text:
        return None
    for pattern, reason, banner in _RULES:
        if pattern.search(text):
            return DeferralVerdict(reason=reason, banner=banner)
    return None
