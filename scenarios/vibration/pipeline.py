"""Vibration vertical-slice pipeline.

Structurally mirrors the EGT pipeline but reuses only **generic** library
primitives — no library code is EGT-specific here. This is the proof point for
ADR-0007: a second scenario composed entirely from the generic platform + its own
feature engineering.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from ehm.agent.graph import run_agent
from ehm.core.evidence import Evidence, Provenance, Signal
from ehm.core.schemas import EngineSnapshot
from ehm.data_brain.features.peer import PeerGroup
from ehm.data_brain.ingestion.synthetic import SyntheticAdapter
from ehm.data_brain.phm.anomaly import residual_trend
from ehm.data_brain.quality import checks as dq
from ehm.knowledge_brain.ontology import FAILURE_MODE
from ehm.safety_brain import audit, policy, uncertainty
from scenarios.vibration.features import residual

#: Vibration trends are small-magnitude (ips); use a much smaller slope threshold
#: than the EGT slice's 2.0 °C/flight default.
_VIB_SLOPE_THRESHOLD = 0.05

#: Domain key params for DQ completeness (vibration, not the EGT-oriented default).
_KEY_PARAMS = ("oat_c", "n1_pct", "n2_pct", "vibration_ips", "fuel_flow_kg_h")


class VibrationFailureMode(StrEnum):
    """Failure modes exercised by the vibration slice."""

    BEARING_DEGRADATION = "BearingDegradation"
    ROTOR_IMBALANCE = "RotorImbalance"

    def uri(self) -> str:
        """Ontology URI (reuses the generic ``FAILURE_MODE`` namespace)."""
        return f"{FAILURE_MODE}{self.value}"


RULES_VERSION = "rules:vibration:v0"


@dataclass
class SliceResult:
    """Outcome of running the slice."""

    evidence: list[Evidence]
    messages: list[str]
    audit_path: str
    snapshots_in: int = 0
    snapshots_clean: int = 0


def run(snapshots: list[EngineSnapshot], audit_path: str) -> SliceResult:
    """Execute the vibration slice over a batch of snapshots."""
    log = audit.AuditLog(audit_path)
    log.clear()

    clean: list[EngineSnapshot] = [
        snap
        for snap in SyntheticAdapter(snapshots).iter_snapshots()
        if dq.assess(snap, key_params=_KEY_PARAMS).ok
    ]

    completeness_by_esn: dict[str, list[float]] = defaultdict(list)
    for snap in snapshots:
        completeness_by_esn[snap.esn].append(dq.assess(snap, key_params=_KEY_PARAMS).completeness)
    avg_completeness = {e: sum(v) / len(v) for e, v in completeness_by_esn.items()}

    peers = PeerGroup(residual_fn=residual)
    peers.add_population(clean)

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
        rule = residual_trend(residuals, slope_threshold=_VIB_SLOPE_THRESHOLD)
        peer_z = peers.zscore(latest)
        # The trend rule is a binary trigger, not a calibrated probability -> model
        # confidence is left unassessed (None). See ADR-0007.
        confidence = uncertainty.from_signals(
            data_completeness=avg_completeness.get(esn, 0.0),
            peer_size=peers.size(latest),
            rule_applies=True,
            model_score=None,
        )
        hypothesis = VibrationFailureMode.BEARING_DEGRADATION.value if rule.triggered else None

        ev = Evidence(
            subject=f"ehm:ESN:{esn}",
            timestamp=latest.timestamp,
            signal=Signal(
                label="vibration_residual",
                unit="ips",
                points=residuals,
                baseline=0.0,
                flight_ids=flights_by_esn.get(esn, []),
            ),
            observation=(
                f"Vibration residual trailing slope {rule.score:.3f} ips/flight ({rule.detail}); "
                f"peer z={peer_z if peer_z is not None else 'n/a'}; peer_size={peers.size(latest)}."
            ),
            hypothesis=hypothesis,
            confidence=confidence,
            provenance=Provenance(
                raw_refs=[f"synthetic:{esn}"],
                feature_refs=["vibration_residual", "peer_zscore", "trend_slope"],
                rule_version=RULES_VERSION,
                ontology_entities=[VibrationFailureMode.BEARING_DEGRADATION.uri()],
                manual_citations=["FIM 79-00-00 (engine vibration analysis)"],
            ),
            recommendation=(
                "Inspect engine vibration; borescope bearings / rotor balance if trend persists."
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
