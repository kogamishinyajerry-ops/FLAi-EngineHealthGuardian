"""Simplified rotor-dynamics vibration model (vibration baseline + degradation).

Companion to ``cycle.py`` (ADR-0010/0013). A real engine's casing vibration is
dominated by rotor unbalance at 1× the fan (N1) and HPC (N2) shaft speeds. This
model captures only that functional form — vibration rises with rotor speed and
with unbalance — with generic placeholder coefficients (NOT LEAP-1C OEM data).
Absolute amplitude is illustrative; the monitoring RESIDUAL is calibration-invariant
(a constant offset cancels), so functional correctness is what matters.

Tests assert directional physics, not absolute magnitudes.
"""

from __future__ import annotations

from dataclasses import dataclass

# Placeholder sensitivities (ips per squared speed ratio); illustrative only.
_N1_GAIN = 0.55  # fan-unbalance contribution at 100% N1
_N2_GAIN = 0.35  # HPC-unbalance contribution at 100% N2
_BASELINE_IPS = 0.10  # floor (flow / bearing background)


@dataclass(frozen=True)
class VibrationState:
    """Per-engine vibration health (the digital-twin knob for the vibration domain).

    ``unbalance_factor`` > 1 models bearing wear or fan-blade loss raising the
    unbalance force (vibration scales with it).
    """

    unbalance_factor: float = 1.0


def vibration_healthy(n1_pct: float, n2_pct: float) -> float:
    """Healthy casing vibration (ips) at the given referenced rotor speeds."""
    n1 = max(0.0, n1_pct) / 100.0
    n2 = max(0.0, n2_pct) / 100.0
    return _BASELINE_IPS + _N1_GAIN * n1 * n1 + _N2_GAIN * n2 * n2


def vibration_at(n1_pct: float, n2_pct: float, state: VibrationState) -> float:
    """Vibration (ips) under a vibration health state."""
    return vibration_healthy(n1_pct, n2_pct) * state.unbalance_factor


__all__ = ["VibrationState", "vibration_at", "vibration_healthy"]
