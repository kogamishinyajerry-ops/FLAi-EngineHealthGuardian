"""EGT residual feature — the core signal of the first vertical slice.

``residual = observed EGT − physics_baseline(phase, thrust, oat)``

A positive residual means the engine is running hotter than the healthy baseline
for the same operating condition — a candidate degradation signal.

v0 uses a crude linear baseline as a **PLACEHOLDER** for the real thermodynamic
gas-path performance model. The real model is P0 work but deferred past the
scaffold (it needs OEM-derived coefficients and validation). What is stable here
is the **interface** (``baseline()`` / ``residual()``); a real model can drop in
behind the same signatures.
"""

from __future__ import annotations

from ehm.core.schemas import EngineSnapshot, FlightPhase

# Placeholder healthy EGT baselines (°C). Coefficients are ILLUSTRATIVE, NOT OEM values.
# baseline = _BASE[phase] + _THRUST_COEF * thrust + _OAT_COEF * oat
_BASE: dict[FlightPhase, float] = {
    FlightPhase.TAKEOFF: 850.0,
    FlightPhase.CLIMB: 720.0,
    FlightPhase.CRUISE: 640.0,
    FlightPhase.DESCENT: 480.0,
    FlightPhase.APPROACH: 600.0,
    FlightPhase.GROUND: 420.0,
}
_THRUST_COEF = 1.2  # °C per % thrust
_OAT_COEF = -1.5  # °C per °C OAT (illustrative; sign/size not OEM-derived)


def baseline(phase: FlightPhase, thrust_pct: float | None, oat_c: float | None) -> float:
    """Healthy EGT for the given operating condition (placeholder physics model)."""
    thrust = thrust_pct if thrust_pct is not None else 80.0
    oat = oat_c if oat_c is not None else 15.0
    return _BASE[phase] + _THRUST_COEF * thrust + _OAT_COEF * oat


def residual(snapshot: EngineSnapshot) -> float | None:
    """EGT residual vs the healthy baseline; ``None`` when EGT is missing."""
    if snapshot.egt_c is None:
        return None
    return snapshot.egt_c - baseline(snapshot.phase, snapshot.thrust_ref_pct, snapshot.oat_c)
