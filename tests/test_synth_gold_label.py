"""Gold-label loop integration with the synthetic-data factory (P3).

Proves the factory's MRO findings flow through the SAME path real MRO data takes:
factory snapshots -> EGT scenario pipeline -> Evidence -> synthetic MRO findings
( via MroJsonAdapter ) -> ``findings_to_adjudications`` -> Adjudications, and that
the adjudicated outcomes match the *injected* truth (TRUE_FAULT for the degraded
engine, NFF for healthy / sensor-fault / confounder engines).
"""

from __future__ import annotations

from pathlib import Path

from scenarios.egt_margin.pipeline import run as run_egt

from ehm.core.schemas import EngineSnapshot
from ehm.data_brain.ingestion import EXAMPLE_ACARS_MAP
from ehm.data_brain.synth import SynthConfig, run_factory
from ehm.data_brain.synth.config import (
    ConfounderKind,
    ConfounderSpec,
    DegradationKind,
    DegradationSpec,
    EngineSpec,
    Season,
    SensorFaultKind,
    SensorFaultSpec,
)
from ehm.feedback.findings import AdjudicationOutcome, findings_to_adjudications
from ehm.feedback.mro_json import MroJsonAdapter


def _config(out_dir: Path) -> SynthConfig:
    fleet = (
        EngineSpec(
            esn="G_H1", config="CFG-A", route_family="short_haul", season=Season.ISA, n_flights=6
        ),
        EngineSpec(
            esn="G_H2", config="CFG-A", route_family="short_haul", season=Season.ISA, n_flights=6
        ),
        EngineSpec(
            esn="G_DECAY",
            config="CFG-A",
            route_family="short_haul",
            season=Season.ISA,
            n_flights=6,
            degradation=DegradationSpec(
                DegradationKind.HPC_EFFICIENCY_DECAY,
                onset_cycle=1,
                rate_per_cycle=0.01,
                max_magnitude=0.08,
            ),
        ),
        EngineSpec(
            esn="G_DRIFT",
            config="CFG-A",
            route_family="short_haul",
            season=Season.ISA,
            n_flights=6,
            sensor_faults=(
                SensorFaultSpec(SensorFaultKind.DRIFT, "egt_c", onset_cycle=1, rate_per_cycle=0.2),
            ),
        ),
    )
    confounders = (ConfounderSpec(ConfounderKind.HOT_DAY, ("G_H2",), oat_delta_c=12.0),)
    return SynthConfig(
        dataset_id="gold-loop",
        seed=5,
        factory_version="0.1.0",
        fleet=fleet,
        confounders=confounders,
        out_dir=str(out_dir),
    )


def _load_snapshots(out: Path) -> list[EngineSnapshot]:
    return [
        EngineSnapshot.model_validate_json(line)
        for line in (out / "snapshots.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_synthetic_mro_findings_close_the_gold_label_loop(tmp_path):
    out = run_factory(_config(tmp_path))
    snapshots = _load_snapshots(out)

    # 1. snapshots walk the EGT scenario pipeline -> Evidence (one per ESN)
    result = run_egt(snapshots, str(tmp_path / "audit.jsonl"))
    esns_with_evidence = {ev.subject for ev in result.evidence}
    assert any("G_DECAY" in s for s in esns_with_evidence)
    assert len(result.evidence) == 4

    # 2. synthetic MRO findings ingest via the real MRO adapter
    findings = list(MroJsonAdapter(out / "mro_json" / "findings.jsonl").iter_findings())
    assert len(findings) == 4

    # 3. bridge findings into adjudications on the Evidence spine
    adjudications = findings_to_adjudications(findings, result.evidence)
    by_esn_subject = {ev.subject: ev for ev in result.evidence}

    def _outcome_for(esn: str) -> AdjudicationOutcome:
        subj = next(s for s in by_esn_subject if esn in s)
        adj = next(a for a in adjudications if a.evidence_id == by_esn_subject[subj].id)
        return adj.outcome

    # injected HPC degradation -> TRUE_FAULT; everything else -> NFF (no engine fault)
    assert _outcome_for("G_DECAY") is AdjudicationOutcome.TRUE_FAULT
    assert _outcome_for("G_H1") is AdjudicationOutcome.NFF
    # a sensor drift is NOT an engine fault -> shop visit finds nothing -> NFF
    assert _outcome_for("G_DRIFT") is AdjudicationOutcome.NFF
    # a hot-day confounder is NOT an engine fault -> NFF
    assert _outcome_for("G_H2") is AdjudicationOutcome.NFF


def test_acars_reports_also_drive_the_pipeline(tmp_path):
    """ACARS is a second real-format entry point into the same pipeline."""
    from ehm.data_brain.ingestion import AcarsJsonAdapter

    out = run_factory(_config(tmp_path))
    acars_path = out / "acars_json" / "reports.jsonl"
    snaps = list(AcarsJsonAdapter(acars_path, EXAMPLE_ACARS_MAP).iter_snapshots())
    result = run_egt(snaps, str(tmp_path / "audit2.jsonl"))
    assert len(result.evidence) == 4  # ACARS cruise reports feed the pipeline too
