"""Policy — the advisory-only hard gate.

No EHM output in v0 may change dispatch, MEL, maintenance program, or
airworthiness. This is the single chokepoint enforcing "engineer co-pilot, not
auto release officer": if overall confidence is below the abstain gate, the
recommendation is stripped and the Evidence becomes an explicit ABSTAIN.
"""

from __future__ import annotations

from ehm.core.evidence import Evidence, EvidenceStatus

#: Overall confidence below this => ABSTAIN (defer to human).
ABSTAIN_GATE: float = 0.6
ABSTAIN_MSG = "Confidence below advisory gate; defer to manual check per the applicable FIM task."


def gate(evidence: Evidence, *, abstain_gate: float = ABSTAIN_GATE) -> Evidence:
    """Apply the advisory-only policy and return the safe Evidence.

    - below gate               -> ABSTAIN (recommendation stripped)
    - has recommendation, confident -> ADVISORY
    - otherwise                -> NOMINAL
    """
    overall = evidence.confidence.overall()
    if overall is not None and overall < abstain_gate:
        return evidence.model_copy(
            update={
                "status": EvidenceStatus.ABSTAIN,
                "recommendation": None,
                "abstain_reason": ABSTAIN_MSG,
            }
        )
    if evidence.recommendation is not None:
        return evidence.model_copy(update={"status": EvidenceStatus.ADVISORY})
    return evidence.model_copy(update={"status": EvidenceStatus.NOMINAL})
