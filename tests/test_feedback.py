from datetime import UTC, datetime
from uuid import uuid4

from ehm.core.evidence import Confidence, Evidence, EvidenceStatus, Provenance
from ehm.feedback import Adjudication, AdjudicationOutcome, LabelStore, build_gold_labels, compute
from ehm.feedback.labels import EXCLUDED_FROM_PRECISION, REAL_OUTCOMES


def _evidence(status: EvidenceStatus) -> Evidence:
    return Evidence(
        subject=f"ehm:ESN:{status.value}",
        observation="o",
        confidence=Confidence(data=0.9, knowledge=0.9, applicability=0.9),
        provenance=Provenance(),
        status=status,
    )


def _adj(
    evidence_id,
    outcome: AdjudicationOutcome,
    *,
    when: datetime | None = None,
    by: str = "tester",
) -> Adjudication:
    return Adjudication(
        evidence_id=evidence_id,
        outcome=outcome,
        human_response="note",
        adjudicated_by=by,
        adjudicated_at=when or datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_real_and_excluded_sets():
    assert (
        frozenset({AdjudicationOutcome.TRUE_FAULT, AdjudicationOutcome.CONDITIONAL_ANOMALY})
        == REAL_OUTCOMES
    )
    assert frozenset({AdjudicationOutcome.INCONCLUSIVE}) == EXCLUDED_FROM_PRECISION


def test_store_latest_wins_by_timestamp(tmp_path):
    store = LabelStore(tmp_path / "labels.jsonl")
    eid = uuid4()
    store.record(_adj(eid, AdjudicationOutcome.NFF, when=datetime(2026, 1, 1, tzinfo=UTC)))
    store.record(
        _adj(
            eid,
            AdjudicationOutcome.TRUE_FAULT,
            when=datetime(2026, 1, 5, tzinfo=UTC),
        )
    )
    latest = store.latest(eid)
    assert latest is not None
    assert latest.outcome is AdjudicationOutcome.TRUE_FAULT  # shop-visit refined the field call
    assert len(store.for_evidence(eid)) == 2  # history retained (event-sourced)


def test_build_gold_labels_joins_adjudicated_and_unadjudicated(tmp_path):
    evidence = [_evidence(EvidenceStatus.NOMINAL), _evidence(EvidenceStatus.ADVISORY)]
    store = LabelStore(tmp_path / "labels.jsonl")
    store.record(_adj(evidence[0].id, AdjudicationOutcome.NFF))

    gold = build_gold_labels(evidence, store)
    assert gold[0].is_adjudicated
    assert not gold[1].is_adjudicated


def test_metrics_full_demo_seed(tmp_path):
    evidence = [
        _evidence(EvidenceStatus.NOMINAL),
        _evidence(EvidenceStatus.ADVISORY),
        _evidence(EvidenceStatus.ABSTAIN),
    ]
    store = LabelStore(tmp_path / "labels.jsonl")
    store.record(_adj(evidence[0].id, AdjudicationOutcome.NFF))
    store.record(_adj(evidence[1].id, AdjudicationOutcome.TRUE_FAULT))
    store.record(_adj(evidence[2].id, AdjudicationOutcome.INCONCLUSIVE))

    metrics = compute(build_gold_labels(evidence, store))

    assert metrics.total == 3
    assert metrics.adjudicated == 3
    assert metrics.coverage == 1.0
    assert metrics.advisory_total == 1
    assert metrics.advisory_evaluable == 1  # INCONCLUSIVE excluded
    assert metrics.advisory_precision_proxy == 1.0  # the one ADVISORY was a TRUE_FAULT
    assert metrics.confusion[("nominal", "nff")] == 1
    assert metrics.confusion[("advisory", "true_fault")] == 1
    assert metrics.confusion[("abstain", "inconclusive")] == 1


def test_metrics_empty_when_no_labels(tmp_path):
    evidence = [_evidence(EvidenceStatus.ADVISORY)]
    metrics = compute(build_gold_labels(evidence, LabelStore(tmp_path / "x.jsonl")))
    assert metrics.coverage == 0.0
    assert metrics.advisory_precision_proxy is None
    assert metrics.confusion[("advisory", "unadjudicated")] == 1


def test_precision_proxy_counts_nff_as_not_real(tmp_path):
    evidence = [
        _evidence(EvidenceStatus.ADVISORY),
        _evidence(EvidenceStatus.ADVISORY),
    ]
    store = LabelStore(tmp_path / "labels.jsonl")
    store.record(_adj(evidence[0].id, AdjudicationOutcome.TRUE_FAULT))
    store.record(_adj(evidence[1].id, AdjudicationOutcome.NFF))

    metrics = compute(build_gold_labels(evidence, store))
    assert metrics.advisory_evaluable == 2
    assert metrics.advisory_precision_proxy == 0.5


def test_adjudication_does_not_mutate_logged_evidence(tmp_path):
    """Event-sourced design: the audit Evidence stays immutable; verdicts live in Adjudication."""
    evidence = [_evidence(EvidenceStatus.ADVISORY)]
    store = LabelStore(tmp_path / "labels.jsonl")
    store.record(_adj(evidence[0].id, AdjudicationOutcome.TRUE_FAULT))

    assert evidence[0].human_response is None
    assert evidence[0].actual_finding is None
    # the human truth is reachable via the gold-label join, not by editing the Evidence
    gold = build_gold_labels(evidence, store)
    assert gold[0].adjudication is not None


def test_render_is_human_readable(tmp_path):
    evidence = [_evidence(EvidenceStatus.ADVISORY)]
    store = LabelStore(tmp_path / "labels.jsonl")
    store.record(_adj(evidence[0].id, AdjudicationOutcome.TRUE_FAULT))
    text = compute(build_gold_labels(evidence, store)).render()
    assert "coverage" in text
    assert "precision" in text
    assert "confusion" in text
