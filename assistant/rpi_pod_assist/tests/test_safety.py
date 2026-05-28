"""Unit tests for the deferral classifier.

Recall/false-defer numbers in the docstring are tracked by the Phase 6.2
eval harness, not here. These tests pin the *behaviour* — that each rule
fires on a representative query and that obviously safe queries pass.
"""

from __future__ import annotations

import pytest

from assistant.rpi_pod_assist import safety


@pytest.mark.parametrize(
    ("query", "reason"),
    [
        ("How much ibuprofen can I give a child?", safety.DeferralReason.DRUG_DOSING),
        ("What is the acetaminophen dosage for adults?", safety.DeferralReason.DRUG_DOSING),
        ("compound fracture of the femur", safety.DeferralReason.SEVERE_TRAUMA),
        ("she's not breathing, what do I do", safety.DeferralReason.SEVERE_TRAUMA),
        ("how to wire a 240V outlet", safety.DeferralReason.HIGH_VOLTAGE),
        ("can I remove a load-bearing wall", safety.DeferralReason.STRUCTURAL),
        ("what happens if I mix bleach and ammonia", safety.DeferralReason.CHEMICAL),
        ("how does gunpowder work", safety.DeferralReason.WEAPONS),
    ],
)
def test_classifier_fires(query: str, reason: safety.DeferralReason) -> None:
    v = safety.classify(query)
    assert v is not None
    assert v.reason is reason
    assert v.banner  # non-empty


@pytest.mark.parametrize(
    "query",
    [
        "how do I purify water in the field",
        "what's the boiling point of water at altitude",
        "knot for securing a tarp",
        "how to start a fire with a ferro rod",
        "wikipedia article on the krebs cycle",
    ],
)
def test_classifier_safe_queries_pass(query: str) -> None:
    assert safety.classify(query) is None


def test_classifier_empty_passes() -> None:
    assert safety.classify("") is None
    assert safety.classify("   ") is None
