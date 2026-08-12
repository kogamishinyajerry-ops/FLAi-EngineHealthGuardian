from scenarios.egt_margin.pipeline import run
from scenarios.egt_margin.synthetic import generate

from ehm.core.evidence import EvidenceStatus


def test_slice_produces_three_distinct_outcomes(tmp_path):
    snapshots = generate(seed=42)
    audit = tmp_path / "audit.jsonl"

    result = run(snapshots, str(audit))

    statuses = {ev.status for ev in result.evidence}
    assert EvidenceStatus.ADVISORY in statuses
    assert EvidenceStatus.ABSTAIN in statuses
    assert len(result.evidence) == 3

    # audit log persisted exactly one line per evidence
    assert audit.exists()
    assert sum(1 for _ in audit.open()) == 3

    # provenance populated on every evidence
    assert all(ev.provenance.feature_refs for ev in result.evidence)
    assert all(ev.provenance.rule_version for ev in result.evidence)


def test_degrade_engine_is_the_advisory(tmp_path):
    result = run(generate(seed=42), str(tmp_path / "audit.jsonl"))
    advisory = [ev for ev in result.evidence if ev.status is EvidenceStatus.ADVISORY]
    assert len(advisory) == 1
    assert "ESN_DEGRADE_02" in advisory[0].subject


def test_lowdata_engine_abstains(tmp_path):
    result = run(generate(seed=42), str(tmp_path / "audit.jsonl"))
    abstain = [ev for ev in result.evidence if ev.status is EvidenceStatus.ABSTAIN]
    assert len(abstain) == 1
    assert "ESN_LOWDATA_03" in abstain[0].subject


def test_slice_is_reproducible(tmp_path):
    a = run(generate(seed=7), str(tmp_path / "a.jsonl"))
    b = run(generate(seed=7), str(tmp_path / "b.jsonl"))
    assert [ev.observation for ev in a.evidence] == [ev.observation for ev in b.evidence]


def test_agent_emits_one_message_per_evidence(tmp_path):
    result = run(generate(seed=42), str(tmp_path / "audit.jsonl"))
    assert len(result.messages) == 3
    assert all(message.startswith("[") for message in result.messages)
