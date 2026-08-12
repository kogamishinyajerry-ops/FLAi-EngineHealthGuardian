"""Vibration pipeline — thin wrapper over the shared residual-trend runner.

Same orchestration as EGT (``scenarios._runner``); differs only in config: the
vibration residual (vs rotor-speed baseline), a much smaller slope threshold
(ips vs °C), and model confidence left unassessed (the rule is a binary trigger).
See ADR-0007/0013.
"""

from __future__ import annotations

from enum import StrEnum

from ehm.core.schemas import EngineSnapshot
from ehm.knowledge_brain.ontology import FAILURE_MODE
from scenarios._runner import ResidualTrendConfig, SliceResult, run_residual_trend_scenario
from scenarios.vibration.features import residual

#: Vibration trends are small-magnitude (ips); far smaller slope threshold than EGT.
_VIB_SLOPE_THRESHOLD = 0.05

#: Domain key params for DQ completeness (vibration, not the EGT-oriented default).
_KEY_PARAMS = ("oat_c", "n1_pct", "n2_pct", "vibration_ips", "fuel_flow_kg_h")

_RULES_VERSION = "rules:vibration:v0"


class VibrationFailureMode(StrEnum):
    """Failure modes exercised by the vibration slice."""

    BEARING_DEGRADATION = "BearingDegradation"
    ROTOR_IMBALANCE = "RotorImbalance"

    def uri(self) -> str:
        """Ontology URI (reuses the generic ``FAILURE_MODE`` namespace)."""
        return f"{FAILURE_MODE}{self.value}"


_CONFIG = ResidualTrendConfig(
    residual_fn=residual,
    signal_label="vibration_residual",
    signal_unit="ips",
    slope_threshold=_VIB_SLOPE_THRESHOLD,
    rule_version=_RULES_VERSION,
    hypothesis=VibrationFailureMode.BEARING_DEGRADATION.value,
    ontology_uri=VibrationFailureMode.BEARING_DEGRADATION.uri(),
    manual_citations=["FIM 79-00-00 (engine vibration analysis)"],
    recommendation=(
        "Inspect engine vibration; borescope bearings / rotor balance if trend persists."
    ),
    key_params=_KEY_PARAMS,
    # The trend rule is a binary trigger, not a calibrated probability -> model
    # confidence is left unassessed (None). See ADR-0007.
    model_score_fn=None,
)


def run(snapshots: list[EngineSnapshot], audit_path: str) -> SliceResult:
    """Execute the vibration slice over a batch of snapshots."""
    return run_residual_trend_scenario(snapshots, audit_path, _CONFIG)


__all__ = ["SliceResult", "VibrationFailureMode", "run"]
