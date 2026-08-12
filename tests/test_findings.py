from datetime import UTC, datetime
from pathlib import Path

from scenarios.egt_margin.pipeline import run
from scenarios.egt_margin.synthetic import generate

from ehm.core.evidence import EvidenceStatus
from ehm.feedback import (
    AdjudicationOutcome,
    Disposition,
    FindingType,
    LabelStore,
    MroFinding,
    MroJsonAdapter,
    build_gold_labels,
    compute,
    derive_outcome,
    evidence_esn,
    findings_to_adjudications,
)

FIX = Path(__file__).parent / "fixtures"


def _finding(
    finding_type: FindingType,
    *,
    disposition: Disposition | None = None,
    esn: str = "ESN_X",
    text: str = "t",
) -> MroFinding:
    return MroFinding(
        esn=esn,
        finding_date=datetime(2026, 8, 5, tzinfo=UTC),
        finding_type=finding_type,
        finding_text=text,
        disposition=disposition,
    )


# --- derive_outcome --------------------------------------------------------


def test_derive_outcome_removal_and_repair_are_true_fault():
    assert derive_outcome(_finding(FindingType.REMOVAL)) is AdjudicationOutcome.TRUE_FAULT
    assert derive_outcome(_finding(FindingType.REPAIR)) is AdjudicationOutcome.TRUE_FAULT


def test_derive_outcome_nff_and_rtv():
    assert derive_outcome(_finding(FindingType.NFF)) is AdjudicationOutcome.NFF
    assert derive_outcome(_finding(FindingType.RTV)) is AdjudicationOutcome.NFF


def test_derive_outcome_borescope_depends_on_disposition():
    faulty = _finding(FindingType.BORESCOPE, disposition=Disposition.REPAIR)
    clean = _finding(FindingType.BORESCOPE, disposition=Disposition.RTV)
    unknown = _finding(FindingType.BORESCOPE)
    assert derive_outcome(faulty) is AdjudicationOutcome.TRUE_FAULT
    assert derive_outcome(clean) is AdjudicationOutcome.NFF
    assert derive_outcome(unknown) is AdjudicationOutcome.CONDITIONAL_ANOMALY


def test_derive_outcome_test_and_shop_visit_inconclusive():
    assert derive_outcome(_finding(FindingType.TEST)) is AdjudicationOutcome.INCONCLUSIVE
    assert derive_outcome(_finding(FindingType.SHOP_VISIT)) is AdjudicationOutcome.INCONCLUSIVE


# --- evidence_esn ----------------------------------------------------------


def test_evidence_esn_parses_subject_convention():
    assert evidence_esn("ehm:ESN:ESN_DEGRADE_02") == "ESN_DEGRADE_02"
    assert evidence_esn("something:else") is None


# --- adapter ---------------------------------------------------------------


def test_mro_json_adapter_reads_fixture():
    findings = list(MroJsonAdapter(FIX / "mro_sample.jsonl").iter_findings())
    assert len(findings) == 3
    assert findings[0].esn == "ESN_DEGRADE_02"
    assert findings[0].finding_type is FindingType.REMOVAL
    assert findings[0].disposition is Disposition.REPAIR
    assert findings[0].component == "HPC"
    assert findings[0].finding_date.tzinfo is not None


# --- bridge to adjudications ----------------------------------------------


def test_findings_attach_actual_finding_and_match_by_esn(tmp_path):
    evidence = run(generate(seed=42), str(tmp_path / "audit.jsonl")).evidence
    findings = list(MroJsonAdapter(FIX / "mro_sample.jsonl").iter_findings())
    adjudications = findings_to_adjudications(findings, evidence)

    assert len(adjudications) == 3  # one per finding, each matches its ESN's evidence
    by_esn = {evidence_esn(ev.subject): ev for ev in evidence}
    degrade_target = by_esn["ESN_DEGRADE_02"]
    degrade_adj = next(a for a in adjudications if a.evidence_id == degrade_target.id)
    assert degrade_adj.outcome is AdjudicationOutcome.TRUE_FAULT
    assert "blade tip rub" in degrade_adj.actual_finding
    assert degrade_adj.adjudicated_by.startswith("mro:")


def test_orphan_finding_is_skipped():
    # finding for an ESN with no Evidence -> skipped (nothing to adjudicate)
    findings = [_finding(FindingType.REMOVAL, esn="ESN_NONEXISTENT")]
    assert findings_to_adjudications(findings, evidence=[]) == []


# --- end-to-end: MRO ground truth flows through the loop ------------------


def test_mro_findings_drive_metrics_end_to_end(tmp_path):
    evidence = run(generate(seed=42), str(tmp_path / "audit.jsonl")).evidence
    findings = list(MroJsonAdapter(FIX / "mro_sample.jsonl").iter_findings())
    store = LabelStore(tmp_path / "labels.jsonl")
    for adjudication in findings_to_adjudications(findings, evidence):
        store.record(adjudication)

    gold = build_gold_labels(evidence, store)
    metrics = compute(gold)

    # actual_finding populated on every evidence (each ESN had a finding)
    assert all(row.adjudication is not None for row in gold)
    assert metrics.coverage == 1.0
    # the one ADVISORY (degrade) was shop-confirmed -> precision proxy 100%
    assert metrics.advisory_total == 1
    assert metrics.advisory_evaluable == 1
    assert metrics.advisory_precision_proxy == 1.0
    assert metrics.confusion[("advisory", "true_fault")] == 1
    assert metrics.confusion[("nominal", "nff")] == 1
    assert metrics.confusion[("abstain", "nff")] == 1


def test_prefer_non_nominal_evidence_when_multiple_prior():
    """If an ESN has a NOMINAL then an ADVISORY evidence, a finding targets the ADVISORY."""
    from ehm.core.evidence import Confidence, Evidence, Provenance

    base = datetime(2026, 8, 1, tzinfo=UTC)
    nominal = Evidence(
        subject="ehm:ESN:E1",
        observation="early nominal",
        confidence=Confidence(data=0.9, knowledge=0.9, applicability=0.9),
        provenance=Provenance(),
        status=EvidenceStatus.NOMINAL,
        timestamp=base,
    )
    advisory = Evidence(
        subject="ehm:ESN:E1",
        observation="later advisory",
        confidence=Confidence(data=0.9, knowledge=0.9, applicability=0.9),
        provenance=Provenance(),
        status=EvidenceStatus.ADVISORY,
        timestamp=datetime(2026, 8, 3, tzinfo=UTC),
    )
    finding = _finding(FindingType.REMOVAL, esn="E1")
    finding = finding.model_copy(update={"finding_date": datetime(2026, 8, 5, tzinfo=UTC)})
    adjudications = findings_to_adjudications([finding], [nominal, advisory])
    assert len(adjudications) == 1
    assert adjudications[0].evidence_id == advisory.id  # the open alert, not the nominal
