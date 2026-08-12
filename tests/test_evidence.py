from ehm.core.evidence import Confidence, Evidence, EvidenceStatus, Provenance
from ehm.safety_brain.policy import gate


def _evidence(conf: Confidence, recommendation: str | None = None) -> Evidence:
    return Evidence(
        subject="ehm:ESN:X",
        observation="o",
        confidence=conf,
        provenance=Provenance(),
        recommendation=recommendation,
    )


def test_overall_is_weakest_link():
    conf = Confidence(data=0.9, model=0.2, knowledge=0.9, applicability=0.9)
    assert conf.overall() == 0.2


def test_overall_ignores_unassessed_dimensions():
    conf = Confidence(data=0.9, model=None, knowledge=0.8, applicability=None)
    assert conf.overall() == 0.8


def test_overall_is_none_when_nothing_assessed():
    assert Confidence().overall() is None


def test_gate_abstains_below_threshold():
    ev = _evidence(
        Confidence(data=0.3, model=0.3, knowledge=0.3, applicability=0.3),
        recommendation="do something",
    )
    out = gate(ev, abstain_gate=0.6)
    assert out.status is EvidenceStatus.ABSTAIN
    assert out.recommendation is None
    assert out.abstain_reason
    assert out.is_abstain


def test_gate_advisory_when_recommendation_and_confident():
    ev = _evidence(
        Confidence(data=0.9, model=0.9, knowledge=0.9, applicability=0.9),
        recommendation="inspect",
    )
    out = gate(ev)
    assert out.status is EvidenceStatus.ADVISORY
    assert out.recommendation == "inspect"


def test_gate_nominal_when_no_recommendation_and_confident():
    ev = _evidence(Confidence(data=0.9, model=0.9, knowledge=0.9, applicability=0.9))
    out = gate(ev)
    assert out.status is EvidenceStatus.NOMINAL


def test_gate_boundary_does_not_abstain():
    # overall exactly 0.6 is NOT below the strict-less gate
    ev = _evidence(
        Confidence(data=0.6, model=0.6, knowledge=0.6, applicability=0.6),
        recommendation="inspect",
    )
    assert gate(ev).status is EvidenceStatus.ADVISORY
