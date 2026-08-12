from scenarios.oil.pipeline import run
from scenarios.oil.synthetic import generate

from ehm.core.evidence import EvidenceStatus


def test_slice_produces_three_distinct_outcomes(tmp_path):
    result = run(generate(seed=42), str(tmp_path / "audit.jsonl"))
    statuses = {ev.status for ev in result.evidence}
    assert EvidenceStatus.ADVISORY in statuses
    assert EvidenceStatus.ABSTAIN in statuses
    assert len(result.evidence) == 3


def test_leak_engine_is_the_advisory(tmp_path):
    result = run(generate(seed=42), str(tmp_path / "audit.jsonl"))
    advisory = [ev for ev in result.evidence if ev.status is EvidenceStatus.ADVISORY]
    assert len(advisory) == 1
    assert "ESN_OIL_LEAK" in advisory[0].subject
    assert advisory[0].hypothesis == "OilLeak"


def test_lowdata_engine_abstains(tmp_path):
    result = run(generate(seed=42), str(tmp_path / "audit.jsonl"))
    abstain = [ev for ev in result.evidence if ev.status is EvidenceStatus.ABSTAIN]
    assert len(abstain) == 1
    assert "ESN_OIL_LOWDATA" in abstain[0].subject


def test_consumption_signal_persisted(tmp_path):
    """The oil Evidence carries the consumption-rate series (for the dashboard waveform)."""
    result = run(generate(seed=42), str(tmp_path / "audit.jsonl"))
    leak = next(ev for ev in result.evidence if "ESN_OIL_LEAK" in ev.subject)
    assert leak.signal is not None
    assert leak.signal.label == "oil_consumption"
    assert len(leak.signal.points) >= 5  # one per consecutive flight pair


def test_reproducible(tmp_path):
    a = run(generate(seed=7), str(tmp_path / "a.jsonl"))
    b = run(generate(seed=7), str(tmp_path / "b.jsonl"))
    assert [ev.observation for ev in a.evidence] == [ev.observation for ev in b.evidence]


def test_audit_and_summary_counts(tmp_path):
    audit = tmp_path / "audit.jsonl"
    result = run(generate(seed=42), str(audit))
    assert audit.exists()
    assert sum(1 for _ in audit.open()) == 3
    assert result.snapshots_in == 54  # 25 + 25 + 4
    assert result.snapshots_clean == 54
