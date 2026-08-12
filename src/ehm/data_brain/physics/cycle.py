"""Simplified turbofan gas-path cycle (EGT baseline + degradation).

Cycle stations (textbook, per unit core flow)::

    OAT, mach, alt  ->  T2/P2  (ram-heated total inlet)
    OPR, polytropic  ->  T3/P3  (compressor delivery)
    thrust demand    ->  T4     (turbine inlet temp, scaled by thrust + day temp)
    turbine expand   ->  T5     (EGT, via isentropic-with-efficiency over P5/P4)

Key honesty points (ADR-0010):
- Coefficients are generic public turbofan-class values, NOT LEAP-1C OEM data.
- Absolute EGT is illustrative; **the residual (observed - baseline) is
  calibration-invariant** — a constant offset cancels — so monitoring correctness
  depends on functional form, not absolute calibration.
- Degradation raises T4 (more fuel for the same thrust) -> EGT rises; this is the
  classic "EGT margin loss" signature.
"""

from __future__ import annotations

from dataclasses import dataclass

from ehm.core.schemas import FlightPhase

# --- gas constants (SI) ---
GAMMA_AIR = 1.4
GAMMA_GAS = 1.33  # hot section
CP_AIR = GAMMA_AIR * 287.0 / (GAMMA_AIR - 1.0)  # ~1004.5 J/kg/K
_STANDARD_DAY_K = 288.15  # ISA sea-level temperature

# --- generic high-bypass turbofan design (ILLUSTRATIVE, not OEM) ---


@dataclass(frozen=True)
class EngineDesign:
    """Generic turbofan design coefficients (placeholder for an OEM cycle deck)."""

    opr: float = 42.0  # overall pressure ratio
    fpr: float = 1.4  # fan pressure ratio
    tit_design: float = 1750.0  # turbine inlet temp at full thrust, standard day (K)
    eta_comp_poly: float = 0.905  # compressor polytropic efficiency
    eta_turb: float = 0.90  # turbine efficiency
    p_loss_combustor: float = 0.03  # combustor fractional pressure loss


def default_design() -> EngineDesign:
    """The default generic turbofan design used by the EGT scenario."""
    return EngineDesign()


# Approximate (mach, altitude_m) per flight phase for the operating-point model.
_PHASE_ENV: dict[FlightPhase, tuple[float, float]] = {
    FlightPhase.GROUND: (0.0, 0.0),
    FlightPhase.TAKEOFF: (0.2, 0.0),
    FlightPhase.CLIMB: (0.5, 4500.0),
    FlightPhase.CRUISE: (0.80, 11000.0),
    FlightPhase.DESCENT: (0.6, 4500.0),
    FlightPhase.APPROACH: (0.3, 600.0),
}


def phase_environment(phase: FlightPhase) -> tuple[float, float]:
    """Return (mach, altitude_m) approximated for a flight phase."""
    return _PHASE_ENV.get(phase, _PHASE_ENV[FlightPhase.CRUISE])


@dataclass(frozen=True)
class OperatingPoint:
    """The engine's operating condition for one cycle evaluation."""

    oat_k: float  # ambient static temperature (K)
    mach: float
    altitude_m: float
    thrust_frac: float  # 0..1, fraction of reference thrust


@dataclass(frozen=True)
class GasPathPoint:
    """Cycle station temperatures/pressures (all SI: K, Pa)."""

    t2: float
    p2: float
    t3: float
    p3: float
    t4: float
    t5: float  # EGT (K)


@dataclass(frozen=True)
class Degradation:
    """How a degraded engine deviates from healthy (the digital-twin knob).

    ``thrust_penalty`` raises the T4 (fuel) needed to hit a given thrust -> EGT up
    (the EGT-margin-loss signature). ``eta_comp_factor`` (<1) lowers compressor
    efficiency -> T3 up. Both are placeholders for real damage-state models.
    """

    thrust_penalty: float = 0.0  # e.g. 0.05 = +5% T4 for same thrust
    eta_comp_factor: float = 1.0  # e.g. 0.97 = 3% efficiency loss


def _isa_pressure(altitude_m: float) -> float:
    """ISA static pressure (Pa) for the troposphere (h < 11 km)."""
    h = max(0.0, min(altitude_m, 11000.0))
    return float(101325.0 * (1.0 - 2.25577e-5 * h) ** 5.2559)


def gas_path(
    design: EngineDesign, op: OperatingPoint, degradation: Degradation | None = None
) -> GasPathPoint:
    """Compute cycle station values for the given design + operating point."""
    deg = degradation or Degradation()
    g = GAMMA_AIR
    gg = GAMMA_GAS

    # 1. intake — ram-heated total conditions
    ram = (g - 1.0) / 2.0 * op.mach**2
    t2 = op.oat_k * (1.0 + ram)
    p0 = _isa_pressure(op.altitude_m)
    p2 = p0 * (1.0 + ram) ** (g / (g - 1.0))

    # 2. compressor — polytropic compression (efficiency loss -> hotter T3)
    eta_c = design.eta_comp_poly * deg.eta_comp_factor
    t3 = t2 * design.opr ** ((g - 1.0) / (g * eta_c))
    p3 = p2 * design.opr * (1.0 - design.p_loss_combustor)

    # 3. combustor — T4 from thrust demand, scaled by day temperature + degradation
    thrust_factor = 0.55 + 0.45 * op.thrust_frac
    t4 = design.tit_design * thrust_factor * (1.0 + deg.thrust_penalty) * (t2 / _STANDARD_DAY_K)

    # 4. turbine — expansion to (near) ambient via isentropic-with-efficiency
    pr_turb = p0 / p3  # exhaust back to ambient over turbine inlet
    t5 = t4 * (1.0 - design.eta_turb * (1.0 - pr_turb ** ((gg - 1.0) / gg)))

    return GasPathPoint(t2=t2, p2=p2, t3=t3, p3=p3, t4=t4, t5=t5)


def egt_healthy(design: EngineDesign, op: OperatingPoint) -> float:
    """Healthy EGT (K) at the operating point — the monitoring baseline."""
    return gas_path(design, op).t5


def egt_degraded(design: EngineDesign, op: OperatingPoint, degradation: Degradation) -> float:
    """EGT (K) under a degradation state — shows the EGT-margin-loss signature."""
    return gas_path(design, op, degradation).t5


def operating_point_from(
    oat_c: float | None, phase: FlightPhase, thrust_pct: float | None
) -> OperatingPoint:
    """Build an OperatingPoint from the canonical snapshot fields."""
    mach, alt = phase_environment(phase)
    oat_k = (oat_c if oat_c is not None else 15.0) + 273.15
    thrust_frac = (thrust_pct / 100.0) if thrust_pct is not None else 0.8
    thrust_frac = max(0.0, min(1.0, thrust_frac))
    return OperatingPoint(oat_k=oat_k, mach=mach, altitude_m=alt, thrust_frac=thrust_frac)


__all__ = [
    "CP_AIR",
    "Degradation",
    "EngineDesign",
    "GasPathPoint",
    "OperatingPoint",
    "default_design",
    "egt_degraded",
    "egt_healthy",
    "gas_path",
    "operating_point_from",
    "phase_environment",
]
