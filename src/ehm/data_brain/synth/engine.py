"""Physics engine — turns a mission sample + health state into pre-sensor truth.

This is the heart of the "physics-driven" factory. Unlike ``scenarios/*/synthetic``
(which add a linear slope to the residual), here degradation flows *through* the
gas-path/vibration/oil models via explicit physics knobs, and N1/N2/fuel are
derived from the operating point so they stay thermodynamically consistent
(real engines' N1/EGT/FF are strongly coupled; iid-random values lose that).

Honesty (ADR-0010/0013): coefficients are generic placeholders, NOT LEAP-1C OEM.
The point is correct functional dependence / fault signature, not absolute value;
the monitoring residual is calibration-invariant.
"""

from __future__ import annotations

from dataclasses import dataclass

from ehm.data_brain.physics import (
    Degradation,
    EngineDesign,
    GasPathPoint,
    OilState,
    OperatingPoint,
    VibrationState,
    consumption_rate_l_per_h,
    gas_path,
    oil_pressure,
    oil_temperature,
    vibration_at,
)
from ehm.data_brain.synth.config import DegradationKind, DegradationSpec
from ehm.data_brain.synth.mission import ProfileSample

# Standard day temperature (K); must match physics.cycle for fuel scaling.
_STANDARD_DAY_K = 288.15

# Placeholder coefficients for rotor-speed / fuel proxies (illustrative).
_N1_IDLE = 58.0
_N1_THRUST_GAIN = 37.0
_N1_MACH_GAIN = 4.0
_N2_IDLE = 72.0
_N2_THRUST_GAIN = 26.0
_FUEL_BASE = 600.0
_FUEL_THRUST_GAIN = 2600.0
# The steady-state cycle (cycle.gas_path) is valid at sustained power; at ground
# idle it over-extracts turbine work and can under-predict EGT below ambient. Floor
# to a plausible running-engine exhaust so non-cruise samples stay physically sane
# and DQ-clean. Cruise EGT sits well above this floor, so monitoring is unaffected.
_IDLE_EGT_RISE_C = 250.0


@dataclass(frozen=True)
class DegradationState:
    """Per-cycle engine health across all three physics domains.

    Each field feeds the matching sub-model: gas-path (``eta_comp_factor``,
    ``thrust_penalty``), vibration (``unbalance_factor``), oil (leak/temp/jitter).
    """

    eta_comp_factor: float = 1.0
    thrust_penalty: float = 0.0
    unbalance_factor: float = 1.0
    leak_rate_l_per_h: float = 0.0
    oil_temp_penalty_c: float = 0.0
    press_jitter: float = 0.0

    @property
    def active(self) -> bool:
        """True when any fault knob has moved off its healthy value."""
        return (
            self.thrust_penalty > 0.0
            or self.eta_comp_factor < 1.0
            or self.unbalance_factor > 1.0
            or self.leak_rate_l_per_h > 0.0
            or self.oil_temp_penalty_c > 0.0
            or self.press_jitter > 0.0
        )


@dataclass(frozen=True)
class TrueReading:
    """Pre-sensor physical truth for one sample (canonical units)."""

    egt_c: float
    n1_pct: float
    n2_pct: float
    fuel_flow_kg_h: float
    vibration_ips: float
    oil_temp_c: float
    oil_pressure_kpa: float
    gas_path: GasPathPoint


def magnitude(spec: DegradationSpec, cycle: int) -> float:
    """Raw injection magnitude at the given cycle (0 before onset; capped at max)."""
    if spec.kind is DegradationKind.NONE or cycle < spec.onset_cycle:
        return 0.0
    return min(spec.rate_per_cycle * (cycle - spec.onset_cycle), spec.max_magnitude)


def evolve(spec: DegradationSpec, cycle: int) -> DegradationState:
    """Grow a ``DegradationState`` from a spec at the given cycle.

    Magnitude grows linearly after ``onset_cycle`` up to ``max_magnitude``, then
    is mapped per ``DegradationKind`` onto physics knobs (each kind produces a
    distinct, physically-signedatured deviation).
    """
    m = magnitude(spec, cycle)
    if m <= 0.0:
        return DegradationState()
    match spec.kind:
        case DegradationKind.HPC_EFFICIENCY_DECAY:
            # Compressor wear: T3 up (eta down) AND engine burns more fuel -> EGT up.
            return DegradationState(eta_comp_factor=1.0 - 0.5 * m, thrust_penalty=0.5 * m)
        case DegradationKind.TURBINE_DISTRESS:
            return DegradationState(thrust_penalty=m)
        case DegradationKind.BEARING_WEAR:
            return DegradationState(unbalance_factor=1.0 + 2.0 * m)
        case DegradationKind.OIL_LEAK:
            return DegradationState(leak_rate_l_per_h=0.4 * m)
        case DegradationKind.NONE:
            return DegradationState()


def _operating_point(sample: ProfileSample) -> OperatingPoint:
    return OperatingPoint(
        oat_k=sample.oat_c + 273.15,
        mach=sample.mach,
        altitude_m=sample.alt_ft * 0.3048,
        thrust_frac=max(0.0, min(1.0, sample.thrust_pct / 100.0)),
    )


def _n1(thrust_frac: float, mach: float) -> float:
    return _N1_IDLE + _N1_THRUST_GAIN * thrust_frac + _N1_MACH_GAIN * mach


def _n2(thrust_frac: float) -> float:
    return _N2_IDLE + _N2_THRUST_GAIN * thrust_frac


def _fuel_flow(thrust_frac: float, t2_k: float, thrust_penalty: float) -> float:
    base = _FUEL_BASE + _FUEL_THRUST_GAIN * thrust_frac * (t2_k / _STANDARD_DAY_K)
    return base * (1.0 + thrust_penalty)


def true_reading(
    design: EngineDesign, sample: ProfileSample, state: DegradationState
) -> TrueReading:
    """Compute pre-sensor truth for one sample under the given health state."""
    op = _operating_point(sample)
    gp = gas_path(
        design,
        op,
        Degradation(
            eta_comp_factor=state.eta_comp_factor,
            thrust_penalty=state.thrust_penalty,
        ),
    )
    egt_c = max(gp.t5 - 273.15, sample.oat_c + _IDLE_EGT_RISE_C)
    n1 = _n1(op.thrust_frac, op.mach)
    n2 = _n2(op.thrust_frac)
    ff = _fuel_flow(op.thrust_frac, gp.t2, state.thrust_penalty)
    vib = vibration_at(n1, n2, VibrationState(unbalance_factor=state.unbalance_factor))
    oil = OilState(
        leak_rate_l_per_h=state.leak_rate_l_per_h,
        oil_temp_penalty_c=state.oil_temp_penalty_c,
        press_jitter=state.press_jitter,
    )
    return TrueReading(
        egt_c=egt_c,
        n1_pct=n1,
        n2_pct=n2,
        fuel_flow_kg_h=ff,
        vibration_ips=vib,
        oil_temp_c=oil_temperature(egt_c, oil),
        oil_pressure_kpa=oil_pressure(n2, oil),
        gas_path=gp,
    )


def flight_hours(samples: list[ProfileSample]) -> float:
    """Total flight duration in hours (last sample offset)."""
    if not samples:
        return 0.0
    return samples[-1].t_offset_s / 3600.0


def oil_burn_litres(samples: list[ProfileSample], state: DegradationState) -> float:
    """Oil consumed over the flight (L) at the given leak state."""
    return consumption_rate_l_per_h(
        OilState(leak_rate_l_per_h=state.leak_rate_l_per_h)
    ) * flight_hours(samples)


__all__ = [
    "DegradationState",
    "TrueReading",
    "evolve",
    "flight_hours",
    "magnitude",
    "oil_burn_litres",
    "true_reading",
]
