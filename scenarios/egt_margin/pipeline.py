"""EGT-margin pipeline — thin wrapper over the shared residual-trend runner.

The orchestration lives in ``scenarios._runner``; this module just supplies the
EGT-specific config (residual fn from the physics baseline, failure mode, FIM,
threshold) so the EGT scenario is ~declarative. See ADR-0013.
"""

from __future__ import annotations

from ehm.core.schemas import EngineSnapshot
from ehm.knowledge_brain.rules import RULES_VERSION, EgtFailureMode
from scenarios._runner import (
    ResidualTrendConfig,
    SliceResult,
    run_residual_trend_scenario,
    summarize,
)
from scenarios.egt_margin.features import residual

_CONFIG = ResidualTrendConfig(
    residual_fn=residual,
    signal_label="egt_residual",
    signal_unit="°C",
    slope_threshold=2.0,
    rule_version=RULES_VERSION,
    hypothesis=EgtFailureMode.COMPRESSOR_EFFICIENCY_DEGRADATION.value,
    ontology_uri=EgtFailureMode.COMPRESSOR_EFFICIENCY_DEGRADATION.uri(),
    manual_citations=["FIM 72-00-00"],
    recommendation="Monitor EGT margin; plan borescope if the upward trend persists.",
    key_params=("oat_c", "n1_pct", "n2_pct", "egt_c", "fuel_flow_kg_h"),
    model_score_fn=lambda slope: min(1.0, slope / 3.0),
)


def run(snapshots: list[EngineSnapshot], audit_path: str) -> SliceResult:
    """Execute the EGT-margin slice over a batch of snapshots."""
    return run_residual_trend_scenario(snapshots, audit_path, _CONFIG)


__all__ = ["SliceResult", "run", "summarize"]
