"""MRO findings from injected truth — the label-side bridge to the gold-label loop.

A finding's truth is *what was injected*: an engine whose degradation ever became
active becomes a shop-visit ``removal``/``repair`` (-> ``TRUE_FAULT``); every other
engine (healthy, sensor-fault, confounder) becomes a clean ``borescope`` rtv
(-> ``NFF``). This is the honest, realistic mapping — a sensor drift or a hot day
that triggered an alert yields *no engine fault* at the shop visit, i.e. NFF, which
is exactly the discrimination the gold-label loop must learn.

Emits the JSONL shape ``MroJsonAdapter`` ingests (esn/date/type/text/disposition/
component), so synthetic findings flow through the same path as real MRO data and
into ``findings_to_adjudications`` (ADR-0004/0006). All tagged ``source=synthetic``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ehm.data_brain.synth.config import DegradationKind

# Degradation kind -> (component, finding text). None = no engine fault.
_KIND_FINDING: dict[DegradationKind, tuple[str, str]] = {
    DegradationKind.HPC_EFFICIENCY_DECAY: (
        "HPC",
        "HPC efficiency degradation confirmed at shop visit",
    ),
    DegradationKind.TURBINE_DISTRESS: (
        "HPT",
        "HPT thermal distress confirmed at shop visit",
    ),
    DegradationKind.BEARING_WEAR: (
        "BEARING",
        "Bearing distress / rotor unbalance confirmed at shop visit",
    ),
    DegradationKind.OIL_LEAK: (
        "OIL_SYSTEM",
        "Oil leak / consumption exceedance confirmed at shop visit",
    ),
}
_SHOP_VISIT_LAG = timedelta(days=3)


@dataclass(frozen=True)
class EngineRunSummary:
    """Per-engine roll-up over its full run, used to synthesise one MRO finding."""

    esn: str
    config: str
    degradation_kind: DegradationKind
    ever_active: bool
    max_magnitude: float
    last_flight_ts: datetime
    last_cycle: int


def finding_dict(summary: EngineRunSummary) -> dict[str, object]:
    """Build one MRO finding (JSONL shape) whose truth reflects what was injected."""
    shop_date = summary.last_flight_ts + _SHOP_VISIT_LAG
    date_iso = shop_date.isoformat().replace("+00:00", "Z")
    if summary.ever_active and summary.degradation_kind in _KIND_FINDING:
        component, text = _KIND_FINDING[summary.degradation_kind]
        return {
            "esn": summary.esn,
            "date": date_iso,
            "type": "removal",
            "text": text,
            "disposition": "repair",
            "component": component,
            "source": "synthetic",
        }
    # healthy / sensor-fault / confounder: no engine fault found at the shop visit
    return {
        "esn": summary.esn,
        "date": date_iso,
        "type": "borescope",
        "text": "Routine borescope inspection; no engine anomaly",
        "disposition": "rtv",
        "component": "HPT",
        "source": "synthetic",
    }


__all__ = ["EngineRunSummary", "finding_dict"]
