"""Oil-scenario pipeline — consumption-rate leak detection.

Reuses generic primitives (``residual_trend``, ``uncertainty``, ``policy.gate``,
``Evidence``, ``run_agent``, ``AuditLog``) but brings its own feature engineering
(oil consumption rate from tank-level deltas) and a fleet-rate peer, because the
per-snapshot ``PeerGroup`` does not fit a rate signal. See ADR-0011.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from ehm.agent.graph import run_agent
from ehm.core.evidence import Evidence, Provenance, Signal
from ehm.core.schemas import EngineSnapshot
from ehm.data_brain.ingestion.synthetic import SyntheticAdapter
from ehm.data_brain.phm.anomaly import residual_trend
from ehm.data_brain.quality import checks as dq
from ehm.knowledge_brain.ontology import FAILURE_MODE
from ehm.safety_brain import audit, policy, uncertainty
from scenarios.oil.features import consumption_series, mean_rate

#: Consumption-rate slope (L/flight²) above which a leak is suspected.
_OIL_SLOPE_THRESHOLD = 0.03


class OilFailureMode(StrEnum):
    """Failure modes exercised by the oil slice."""

    OIL_LEAK = "OilLeak"
    BEARING_WEAR = "BearingWear"

    def uri(self) -> str:
        return f"{FAILURE_MODE}{self.value}"


RULES_VERSION = "rules:oil:v0"


@dataclass
class SliceResult:
    """Outcome of running the slice."""

    evidence: list[Evidence]
    messages: list[str]
    audit_path: str
    snapshots_in: int = 0
    snapshots_clean: int = 0


def run(snapshots: list[EngineSnapshot], audit_path: str) -> SliceResult:
    """Execute the oil slice over a batch of snapshots."""
    log = audit.AuditLog(audit_path)
    log.clear()

    clean = [s for s in SyntheticAdapter(snapshots).iter_snapshots() if dq.assess(s).ok]

    completeness_by_esn: dict[str, list[float]] = defaultdict(list)
    for snap in snapshots:
        completeness_by_esn[snap.esn].append(dq.assess(snap).completeness)
    avg_completeness = {e: sum(v) / len(v) for e, v in completeness_by_esn.items()}

    by_esn: dict[str, list[EngineSnapshot]] = defaultdict(list)
    for snap in sorted(clean, key=lambda s: s.timestamp):
        by_esn[snap.esn].append(snap)

    # peer size = snapshots sharing the config (consistent w/ EGT/vibration semantics)
    config_count: dict[str, int] = defaultdict(int)
    for snap in clean:
        config_count[snap.config_tag] += 1
    # fleet mean consumption rate (for the observation / signal baseline)
    rates = {esn: (mean_rate(consumption_series(snaps)) or 0.0) for esn, snaps in by_esn.items()}
    fleet_mean = sum(rates.values()) / len(rates) if rates else 0.0

    evidence: list[Evidence] = []
    for esn, snaps in by_esn.items():
        series = consumption_series(snaps)
        rule = residual_trend(series, slope_threshold=_OIL_SLOPE_THRESHOLD)
        latest = snaps[-1]
        peer_size = config_count[latest.config_tag]
        my_rate = rates[esn]
        confidence = uncertainty.from_signals(
            data_completeness=avg_completeness.get(esn, 0.0),
            peer_size=peer_size,
            rule_applies=True,
            model_score=None,
        )
        hypothesis = OilFailureMode.OIL_LEAK.value if rule.triggered else None

        ev = Evidence(
            subject=f"ehm:ESN:{esn}",
            timestamp=latest.timestamp,
            signal=Signal(
                label="oil_consumption",
                unit="L/flight",
                points=series,
                baseline=fleet_mean,
            ),
            observation=(
                f"Oil consumption trailing slope {rule.score:.3f} L/flight² ({rule.detail}); "
                f"mean rate {my_rate:.3f} L/flight vs fleet {fleet_mean:.3f}; "
                f"peer_size={peer_size}."
            ),
            hypothesis=hypothesis,
            confidence=confidence,
            provenance=Provenance(
                raw_refs=[f"synthetic:{esn}"],
                feature_refs=["oil_consumption_rate", "fleet_mean_rate", "trend_slope"],
                rule_version=RULES_VERSION,
                ontology_entities=[OilFailureMode.OIL_LEAK.uri()],
                manual_citations=["FIM 79-21-00 (engine oil system)"],
            ),
            recommendation=(
                "Inspect oil system for leak / scavenge issue; monitor consumption trend."
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
