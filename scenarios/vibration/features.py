"""Vibration residual feature — scenario-local feature engineering.

``residual = observed vibration − baseline(phase, N1, N2)``

Vibration scales with rotor speed, so the baseline keys on N1/N2 (and phase) —
distinct from the EGT baseline (which keys on thrust/OAT). This is the scenario's
own contribution: the *library* is parameter-agnostic; each scenario brings the
physics it needs.

v0 uses a crude linear baseline as a PLACEHOLDER (real bearing/vibration models
and OEM limits are deferred). Stable here is the interface.
"""

from __future__ import annotations

from ehm.core.schemas import EngineSnapshot, FlightPhase

# Placeholder healthy vibration baselines (ips). Coefficients ILLUSTRATIVE, not OEM.
_BASE: dict[FlightPhase, float] = {
    FlightPhase.TAKEOFF: 1.0,
    FlightPhase.CLIMB: 0.8,
    FlightPhase.CRUISE: 0.6,
    FlightPhase.DESCENT: 0.5,
    FlightPhase.APPROACH: 0.7,
    FlightPhase.GROUND: 0.3,
}
_N1_COEF = 0.020  # ips per %N1 above the 80% reference
_N2_COEF = 0.015  # ips per %N2 above the 90% reference


def baseline(phase: FlightPhase, n1_pct: float | None, n2_pct: float | None) -> float:
    """Healthy vibration for the given rotor-speed / phase condition (placeholder)."""
    n1 = n1_pct if n1_pct is not None else 85.0
    n2 = n2_pct if n2_pct is not None else 93.0
    return _BASE[phase] + _N1_COEF * (n1 - 80.0) + _N2_COEF * (n2 - 90.0)


def residual(snapshot: EngineSnapshot) -> float | None:
    """Vibration residual vs the healthy baseline; ``None`` when vibration missing."""
    if snapshot.vibration_ips is None:
        return None
    return snapshot.vibration_ips - baseline(snapshot.phase, snapshot.n1_pct, snapshot.n2_pct)
