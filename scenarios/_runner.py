"""Shared scenario runner — the common residual-trend orchestration.

EGT and vibration pipelines were ~60 lines of near-identical orchestration
(ingest→DQ→peer→per-ESN residual series→trend→uncertainty→policy→Evidence→audit).
This captures that pattern once, parameterised by a ``ResidualTrendConfig``. The
oil scenario is rate-based (different shape) and stays bespoke.

Lives in ``scenarios/`` (not the library): this is scenario *orchestration*, not a
library primitive — the library stays primitives-only (ADR-0007/0011).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from ehm.agent.graph import run_agent
from ehm.core.evidence import Evidence, Provenance, Signal
from ehm.core.schemas import EngineSnapshot
from ehm.data_brain.features.peer import PeerGroup
from ehm.data_brain.ingestion.synthetic import SyntheticAdapter
from ehm.data_brain.phm.anomaly import residual_trend
from ehm.data_brain.quality import checks as dq
from ehm.safety_brain import audit, policy, uncertainty


@dataclass(frozen=True)
class SliceResult:
    """Outcome of running a slice."""

    evidence: list[Evidence]
    messages: list[str]
    audit_path: str
    snapshots_in: int = 0
    snapshots_clean: int = 0


@dataclass(frozen=True)
class ResidualTrendConfig:
    """Everything a residual-trend scenario customises; the runner does the rest."""

    residual_fn: Callable[[EngineSnapshot], float | None]
    signal_label: str
    signal_unit: str  # per-flight unit of the slope, e.g. "°C" or "ips"
    slope_threshold: float
    rule_version: str
    hypothesis: str  # failure-mode value set when triggered
    ontology_uri: str  # failure-mode ontology URI
    manual_citations: list[str]
    recommendation: str
    key_params: tuple[str, ...]
    model_score_fn: Callable[[float], float] | None = None  # None -> model confidence unassessed


def summarize(result: SliceResult) -> dict[str, int]:
    """Count Evidence by status — used by demo CLIs."""
    counts: dict[str, int] = defaultdict(int)
    for ev in result.evidence:
        counts[ev.status.value] += 1
    return dict(counts)


def run_residual_trend_scenario(
    snapshots: list[EngineSnapshot], audit_path: str, config: ResidualTrendConfig
) -> SliceResult:
    """Run the shared ingest→…→audit residual-trend flow for one scenario."""
    log = audit.AuditLog(audit_path)
    log.clear()

    clean = [
        s
        for s in SyntheticAdapter(snapshots).iter_snapshots()
        if dq.assess(s, key_params=config.key_params).ok
    ]

    completeness_by_esn: dict[str, list[float]] = defaultdict(list)
    for snap in snapshots:
        completeness_by_esn[snap.esn].append(
            dq.assess(snap, key_params=config.key_params).completeness
        )
    avg_completeness = {e: sum(v) / len(v) for e, v in completeness_by_esn.items()}

    peers = PeerGroup(residual_fn=config.residual_fn)
    peers.add_population(clean)

    series: dict[str, list[float]] = defaultdict(list)
    flights_by_esn: dict[str, list[str]] = defaultdict(list)
    latest_by_esn: dict[str, EngineSnapshot] = {}
    for snap in sorted(clean, key=lambda s: s.timestamp):
        value = config.residual_fn(snap)
        if value is not None:
            series[snap.esn].append(value)
            flights_by_esn[snap.esn].append(snap.flight_id)
            latest_by_esn[snap.esn] = snap

    evidence: list[Evidence] = []
    for esn, residuals in series.items():
        latest = latest_by_esn[esn]
        rule = residual_trend(residuals, slope_threshold=config.slope_threshold)
        peer_z = peers.zscore(latest)
        model_score = (
            config.model_score_fn(rule.score)
            if (rule.triggered and config.model_score_fn)
            else None
        )
        confidence = uncertainty.from_signals(
            data_completeness=avg_completeness.get(esn, 0.0),
            peer_size=peers.size(latest),
            rule_applies=True,
            model_score=model_score,
        )
        hypothesis = config.hypothesis if rule.triggered else None
        ev = Evidence(
            subject=f"ehm:ESN:{esn}",
            timestamp=latest.timestamp,
            signal=Signal(
                label=config.signal_label,
                unit=config.signal_unit,
                points=residuals,
                baseline=0.0,
                flight_ids=flights_by_esn.get(esn, []),
            ),
            observation=(
                f"{config.signal_label} trailing slope {rule.score:.2f} "
                f"{config.signal_unit}/flight ({rule.detail}); "
                f"peer z={peer_z if peer_z is not None else 'n/a'}; peer_size={peers.size(latest)}."
            ),
            hypothesis=hypothesis,
            confidence=confidence,
            provenance=Provenance(
                raw_refs=[f"synthetic:{esn}"],
                feature_refs=[config.signal_label, "peer_zscore", "trend_slope"],
                rule_version=config.rule_version,
                ontology_entities=[config.ontology_uri],
                manual_citations=config.manual_citations,
            ),
            recommendation=config.recommendation if rule.triggered else None,
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


__all__ = ["ResidualTrendConfig", "SliceResult", "run_residual_trend_scenario", "summarize"]
