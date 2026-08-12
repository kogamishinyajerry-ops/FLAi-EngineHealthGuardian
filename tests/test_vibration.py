from scenarios.vibration.pipeline import run
from scenarios.vibration.synthetic import generate

from ehm.core.evidence import EvidenceStatus


def test_slice_produces_three_distinct_outcomes(tmp_path):
    result = run(generate(seed=42), str(tmp_path / "audit.jsonl"))

    statuses = {ev.status for ev in result.evidence}
    assert EvidenceStatus.ADVISORY in statuses
    assert EvidenceStatus.ABSTAIN in statuses
    assert len(result.evidence) == 3


def test_degrade_engine_is_the_advisory(tmp_path):
    result = run(generate(seed=42), str(tmp_path / "audit.jsonl"))
    advisory = [ev for ev in result.evidence if ev.status is EvidenceStatus.ADVISORY]
    assert len(advisory) == 1
    assert "ESN_VIB_DEGRADE" in advisory[0].subject
    assert advisory[0].hypothesis == "BearingDegradation"


def test_lowdata_engine_abstains(tmp_path):
    result = run(generate(seed=42), str(tmp_path / "audit.jsonl"))
    abstain = [ev for ev in result.evidence if ev.status is EvidenceStatus.ABSTAIN]
    assert len(abstain) == 1
    assert "ESN_VIB_LOWDATA" in abstain[0].subject


def test_audit_log_written_one_line_per_evidence(tmp_path):
    audit = tmp_path / "audit.jsonl"
    run(generate(seed=42), str(audit))
    assert audit.exists()
    assert sum(1 for _ in audit.open()) == 3


def test_slice_is_reproducible(tmp_path):
    a = run(generate(seed=7), str(tmp_path / "a.jsonl"))
    b = run(generate(seed=7), str(tmp_path / "b.jsonl"))
    assert [ev.observation for ev in a.evidence] == [ev.observation for ev in b.evidence]


def test_vibration_evidence_compatible_with_feedback_loop(tmp_path):
    """Vibration Evidence flows through the same gold-label machinery as EGT."""
    from ehm.feedback import LabelStore, build_gold_labels, compute

    result = run(generate(seed=42), str(tmp_path / "audit.jsonl"))
    metrics = compute(build_gold_labels(result.evidence, LabelStore(tmp_path / "labels.jsonl")))
    assert metrics.total == 3
    assert metrics.coverage == 0.0  # nothing adjudicated yet
    assert metrics.advisory_total == 1


def test_agent_emits_one_message_per_evidence(tmp_path):
    result = run(generate(seed=42), str(tmp_path / "audit.jsonl"))
    assert len(result.messages) == 3
    assert all(message.startswith("[") for message in result.messages)
