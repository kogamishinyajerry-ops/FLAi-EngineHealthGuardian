"""EGT-margin end-to-end vertical slice.

Proves the whole architecture with synthetic data on one scenario::

    ingest -> DQ -> EGT residual feature -> peer normalization -> trend rule
            -> uncertainty -> advisory policy gate -> Evidence -> agent -> audit log

Run via ``make demo`` (scripts/run_egt_demo.py). The slice is deliberately a
linear, readable function — it exists to validate that the four brains compose
behind the Evidence spine, not to be production logic.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ehm.agent.graph import run_agent
from ehm.core.evidence import Evidence, EvidenceStatus, Provenance, Signal
from ehm.core.schemas import EngineSnapshot
from ehm.data_brain.features.egt import residual
from ehm.data_brain.features.peer import PeerGroup
from ehm.data_brain.ingestion.synthetic import SyntheticAdapter
from ehm.data_brain.phm.anomaly import residual_trend
from ehm.data_brain.quality import checks as dq
from ehm.knowledge_brain.rules import RULES_VERSION, EgtFailureMode
from ehm.safety_brain import audit, policy, uncertainty


@dataclass
class SliceResult:
    """Outcome of running the slice."""

    evidence: list[Evidence]
    messages: list[str]
    audit_path: str
    snapshots_in: int = 0
    snapshots_clean: int = 0


def run(snapshots: list[EngineSnapshot], audit_path: str) -> SliceResult:
    """Execute the EGT-margin slice over a batch of snapshots."""
    log = audit.AuditLog(audit_path)
    log.clear()

    # 1. ingest (synthetic adapter) + 2. DQ gate
    adapter = SyntheticAdapter(snapshots)
    clean: list[EngineSnapshot] = [snap for snap in adapter.iter_snapshots() if dq.assess(snap).ok]

    # Per-ESN average data completeness (from RAW, incl. any DQ-rejected) -> Data Confidence
    completeness_by_esn: dict[str, list[float]] = defaultdict(list)
    for snap in snapshots:
        completeness_by_esn[snap.esn].append(dq.assess(snap).completeness)
    avg_completeness = {e: sum(v) / len(v) for e, v in completeness_by_esn.items()}

    # 3. peer baseline over the clean population
    peers = PeerGroup(residual_fn=residual)
    peers.add_population(clean)

    # 4. per-ESN residual series (time-ordered) -> trend rule
    series: dict[str, list[float]] = defaultdict(list)
    flights_by_esn: dict[str, list[str]] = defaultdict(list)
    latest_by_esn: dict[str, EngineSnapshot] = {}
    for snap in sorted(clean, key=lambda s: s.timestamp):
        value = residual(snap)
        if value is not None:
            series[snap.esn].append(value)
            flights_by_esn[snap.esn].append(snap.flight_id)
            latest_by_esn[snap.esn] = snap

    evidence: list[Evidence] = []
    for esn, residuals in series.items():
        latest = latest_by_esn[esn]
        rule = residual_trend(residuals)
        peer_z = peers.zscore(latest)
        model_score = min(1.0, rule.score / 3.0) if rule.triggered else None
        confidence = uncertainty.from_signals(
            data_completeness=avg_completeness.get(esn, 0.0),
            peer_size=peers.size(latest),
            rule_applies=True,
            model_score=model_score,
        )
        hypothesis = (
            EgtFailureMode.COMPRESSOR_EFFICIENCY_DEGRADATION.value if rule.triggered else None
        )

        ev = Evidence(
            subject=f"ehm:ESN:{esn}",
            timestamp=latest.timestamp,
            signal=Signal(
                label="egt_residual",
                unit="°C",
                points=residuals,
                baseline=0.0,
                flight_ids=flights_by_esn.get(esn, []),
            ),
            observation=(
                f"EGT residual trailing slope {rule.score:.2f} °C/flight ({rule.detail}); "
                f"peer z={peer_z if peer_z is not None else 'n/a'}; peer_size={peers.size(latest)}."
            ),
            hypothesis=hypothesis,
            confidence=confidence,
            provenance=Provenance(
                raw_refs=[f"synthetic:{esn}"],
                feature_refs=["egt_residual", "peer_zscore", "trend_slope"],
                rule_version=RULES_VERSION,
                ontology_entities=[EgtFailureMode.COMPRESSOR_EFFICIENCY_DEGRADATION.uri()],
                manual_citations=["FIM 72-00-00"],
            ),
            recommendation=(
                "Monitor EGT margin; plan borescope if the upward trend persists."
                if rule.triggered
                else None
            ),
        )
        ev = policy.gate(ev)
        evidence.append(ev)
        log.log(ev)

    messages = run_agent(evidence)
    return SliceResult(
        evidence=evidence,
        messages=messages,
        audit_path=audit_path,
        snapshots_in=len(snapshots),
        snapshots_clean=len(clean),
    )


def summarize(result: SliceResult) -> dict[str, int]:
    """Count Evidence by status — handy for demo output and tests."""
    counts: dict[str, int] = defaultdict(int)
    for ev in result.evidence:
        counts[ev.status.value] += 1
    return dict(counts)


__all__ = ["SliceResult", "run", "summarize", "EvidenceStatus"]
