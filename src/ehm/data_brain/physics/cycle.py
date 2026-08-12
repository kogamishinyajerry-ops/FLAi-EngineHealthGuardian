"""Simplified two-spool turbofan gas-path cycle (EGT baseline + degradation).

Enhanced from the single-spool sketch: two-spool compression split
(fan -> LPC booster -> HPC), bypass ratio (BPR) driving fan work, and turbine
cooling-air bleed. Cycle stations (per unit core flow, all total temps)::

    OAT,mach,alt -> T2/P2            (ram-heated inlet)
    fan (FPR)   -> T13               (bypass + core; fan work ~ BPR)
    LPC (LPC_PR)-> T25               (LP spool, booster)
    HPC (HPC_PR)-> T3/P3             (HP spool; HPC_PR = OPR/(FPR*LPC_PR))
    combustor   -> T4                (TIT, thrust + day-temp driven)
    cooling mix -> T4_mix            (cooling air at T3 lowers effective inlet)
    HPT         -> T45               (drives HPC)
    LPT         -> T5  (EGT)         (drives fan + LPC)

Honesty (ADR-0010/0013): coefficients are generic public turbofan-class values,
NOT LEAP-1C OEM data. Absolute EGT is illustrative; the monitoring RESIDUAL is
calibration-invariant. Tests assert directional physics only.
"""

from __future__ import annotations

from dataclasses import dataclass

from ehm.core.schemas import FlightPhase

# --- gas constants (SI) ---
GAMMA_AIR = 1.4
GAMMA_GAS = 1.33
CP_AIR = GAMMA_AIR * 287.0 / (GAMMA_AIR - 1.0)  # ~1004.5 J/kg/K
CP_GAS = 1148.0
_STANDARD_DAY_K = 288.15


@dataclass(frozen=True)
class EngineDesign:
    """Generic two-spool high-bypass turbofan (ILLUSTRATIVE, not OEM)."""

    opr: float = 42.0  # overall (core) pressure ratio, incl fan+lpc+hpc
    fpr: float = 1.4  # fan pressure ratio
    lpc_pr: float = 2.5  # LPC/booster pressure ratio
    bpr: float = 9.0  # bypass ratio
    cooling_bleed: float = 0.12  # fraction of HPC-exit air used for turbine cooling
    tit_design: float = 1750.0  # turbine inlet temp at full thrust, standard day (K)
    eta_fan: float = 0.86
    eta_lpc: float = 0.90
    eta_comp_poly: float = 0.905  # HPC polytropic efficiency
    eta_turb: float = 0.90
    eta_mech: float = 0.99
    p_loss_combustor: float = 0.03


def default_design() -> EngineDesign:
    """The default generic turbofan design used by the EGT scenario."""
    return EngineDesign()


# Approximate (mach, altitude_m) per flight phase.
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

    oat_k: float
    mach: float
    altitude_m: float
    thrust_frac: float  # 0..1


@dataclass(frozen=True)
class GasPathPoint:
    """Cycle station temperatures/pressures (K, Pa)."""

    t2: float
    t13: float
    t25: float
    t3: float
    p3: float
    t4: float
    t45: float
    t5: float  # EGT


@dataclass(frozen=True)
class Degradation:
    """How a degraded engine deviates from healthy (the digital-twin knob)."""

    thrust_penalty: float = 0.0  # raises T4 (fuel) for the same thrust -> EGT up
    eta_comp_factor: float = 1.0  # <1 lowers HPC efficiency -> T3 up


def _isa_pressure(altitude_m: float) -> float:
    """ISA static pressure (Pa) for the troposphere (h < 11 km)."""
    h = max(0.0, min(altitude_m, 11000.0))
    return float(101325.0 * (1.0 - 2.25577e-5 * h) ** 5.2559)


def _compress(t_in: float, pr: float, eta_poly: float) -> float:
    """Polytropic compression outlet temperature (K)."""
    return float(t_in * pr ** ((GAMMA_AIR - 1.0) / (GAMMA_AIR * eta_poly)))


def gas_path(
    design: EngineDesign, op: OperatingPoint, degradation: Degradation | None = None
) -> GasPathPoint:
    """Compute cycle station values for the given design + operating point."""
    deg = degradation or Degradation()
    g = GAMMA_AIR

    # 1. inlet — ram-heated total conditions
    ram = (g - 1.0) / 2.0 * op.mach**2
    t2 = op.oat_k * (1.0 + ram)
    p2 = _isa_pressure(op.altitude_m) * (1.0 + ram) ** (g / (g - 1.0))

    # 2. compression train (fan -> LPC -> HPC), per unit core flow
    t13 = _compress(t2, design.fpr, design.eta_fan)
    t25 = _compress(t2, design.lpc_pr, design.eta_lpc)
    hpc_pr = design.opr / (design.fpr * design.lpc_pr)
    eta_hpc = design.eta_comp_poly * deg.eta_comp_factor
    t3 = _compress(t25, hpc_pr, eta_hpc)
    p3 = p2 * design.opr * (1.0 - design.p_loss_combustor)

    # specific works (J per kg of core flow)
    fan_work = design.bpr * CP_AIR * (t13 - t2)  # bypass gets BPR x the work
    lpc_work = CP_AIR * (t25 - t2)
    hpc_work = CP_AIR * (t3 - t25)

    # 3. combustor — T4 from thrust demand, scaled by day temperature + degradation
    thrust_factor = 0.55 + 0.45 * op.thrust_frac
    t4 = design.tit_design * thrust_factor * (1.0 + deg.thrust_penalty) * (t2 / _STANDARD_DAY_K)

    # cooling-air mix: cooling air bled at T3 mixes into the hot gas -> lowers inlet
    eps = design.cooling_bleed
    t4_mix = (1.0 - eps) * t4 + eps * t3

    # 4. turbines — power balance (turbine work = compressor/fan work it drives)
    # HPT drives HPC; LPT drives fan + LPC. (η_mech lumps mechanical losses.)
    t45 = t4_mix - hpc_work / (design.eta_mech * CP_GAS)
    t5 = t45 - (fan_work + lpc_work) / (design.eta_mech * CP_GAS)

    return GasPathPoint(t2=t2, t13=t13, t25=t25, t3=t3, p3=p3, t4=t4, t45=t45, t5=t5)


def egt_healthy(design: EngineDesign, op: OperatingPoint) -> float:
    """Healthy EGT (K) at the operating point — the monitoring baseline."""
    return gas_path(design, op).t5


def egt_degraded(design: EngineDesign, op: OperatingPoint, degradation: Degradation) -> float:
    """EGT (K) under a degradation state — the EGT-margin-loss signature."""
    return gas_path(design, op, degradation).t5


def operating_point_from(
    oat_c: float | None, phase: FlightPhase, thrust_pct: float | None
) -> OperatingPoint:
    """Build an OperatingPoint from the canonical snapshot fields."""
    mach, alt = phase_environment(phase)
    oat_k = (oat_c if oat_c is not None else 15.0) + 273.15
    thrust_frac = (thrust_pct / 100.0) if thrust_pct is not None else 0.8
    return OperatingPoint(
        oat_k=oat_k, mach=mach, altitude_m=alt, thrust_frac=max(0.0, min(1.0, thrust_frac))
    )


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
