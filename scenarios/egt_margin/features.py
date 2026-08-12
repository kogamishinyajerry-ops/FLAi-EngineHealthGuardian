"""EGT residual feature — backed by the gas-path physics model.

``residual = observed EGT − physics_baseline(phase, thrust, oat)``

The baseline now comes from ``ehm.data_brain.physics`` (a simplified turbofan
cycle) instead of the earlier linear placeholder — same ``baseline()`` /
``residual()`` interface, so the pipeline and synthetic generator are unchanged.
See ADR-0010 for the honest scope (functional form is real cycle physics;
coefficients are generic, not OEM; the residual is calibration-invariant).
"""

from __future__ import annotations

from ehm.core.schemas import EngineSnapshot, FlightPhase
from ehm.data_brain.physics import default_design, egt_healthy, operating_point_from

_DESIGN = default_design()


def baseline(phase: FlightPhase, thrust_pct: float | None, oat_c: float | None) -> float:
    """Healthy EGT (°C) for the operating condition, from the gas-path model."""
    op = operating_point_from(oat_c, phase, thrust_pct)
    return egt_healthy(_DESIGN, op) - 273.15  # K -> °C


def residual(snapshot: EngineSnapshot) -> float | None:
    """EGT residual vs the healthy baseline; ``None`` when EGT is missing."""
    if snapshot.egt_c is None:
        return None
    return snapshot.egt_c - baseline(snapshot.phase, snapshot.thrust_ref_pct, snapshot.oat_c)
