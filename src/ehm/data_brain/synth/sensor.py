"""Sensor reality layer — noise, dropout, and sensor faults.

Turns pre-sensor ``TrueReading`` into the noisy, sometimes-missing values a real
QAR/ACARS feed delivers. Noise is AR(1) (real sensors are time-correlated, not
white); dropout produces ``None`` (exercising the DQ completeness path); and
sensor faults (drift/stuck/bias) are injected on specific channels. Critically,
a sensor fault is labelled ``sensor_fault`` — distinct from an engine fault —
because confusing the two is the main source of false alerts.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from ehm.core.schemas import FlightPhase
from ehm.data_brain.synth.config import SensorFaultKind, SensorFaultSpec, SensorModelSpec
from ehm.data_brain.synth.engine import TrueReading
from ehm.data_brain.synth.mission import ProfileSample

# Canonical params that may carry a sensor fault.
_FAULTABLE_PARAMS: frozenset[str] = frozenset(
    {
        "egt_c",
        "n1_pct",
        "n2_pct",
        "fuel_flow_kg_h",
        "vibration_ips",
        "oil_temp_c",
        "oil_pressure_kpa",
    }
)


@dataclass(frozen=True)
class SampleReading:
    """One sensed sample (context clean; sensed channels may be None on dropout)."""

    t_offset_s: float
    phase: FlightPhase
    alt_ft: float
    airspeed_kt: float
    oat_c: float
    thrust_pct: float
    mach: float
    egt_c: float | None
    n1_pct: float | None
    n2_pct: float | None
    fuel_flow_kg_h: float | None
    vibration_ips: float | None
    oil_temp_c: float | None
    oil_pressure_kpa: float | None


class _Channel:
    """AR(1) noise + independent dropout for one sensed parameter."""

    def __init__(self, sd: float, ar1: float, dropout_p: float, rng: random.Random) -> None:
        self._sd = sd
        self._phi = ar1
        self._dropout_p = dropout_p
        self._rng = rng
        self._prev = 0.0

    def sample(self, value: float) -> float | None:
        """Return the sensed value (with AR(1) noise) or None on dropout."""
        if self._rng.random() < self._dropout_p:
            return None
        eps_sd = self._sd * (1.0 - self._phi**2) ** 0.5
        self._prev = self._phi * self._prev + eps_sd * self._rng.gauss(0.0, 1.0)
        return value + self._prev


class SensorLayer:
    """Stateful per-flight sensor model (channels keep AR(1) state across samples)."""

    def __init__(
        self,
        model: SensorModelSpec,
        faults: tuple[SensorFaultSpec, ...],
        cycle: int,
        rng: random.Random,
    ) -> None:
        self._model = model
        self._cycle = cycle
        self._faults = {f.param: f for f in faults}
        self._rng = rng
        self._egt = _Channel(model.egt_noise_sd, model.egt_ar1, model.dropout_p, rng)
        self._n1 = _Channel(model.n1_noise_sd, 0.3, model.dropout_p, rng)
        self._n2 = _Channel(model.n2_noise_sd, 0.3, model.dropout_p, rng)
        self._fuel = _Channel(model.fuel_noise_sd, 0.3, model.dropout_p, rng)
        self._vib = _Channel(model.vibration_noise_sd, 0.3, model.dropout_p, rng)
        self._oil_t = _Channel(model.oil_temp_noise_sd, 0.3, model.dropout_p, rng)
        self._oil_p = _Channel(model.oil_press_noise_sd, 0.3, model.dropout_p, rng)

    def _fault_value(self, param: str, value: float) -> float:
        """Apply the active sensor fault (if any) for ``param`` to ``value``."""
        fault = self._faults.get(param)
        if fault is None or self._cycle < fault.onset_cycle:
            return value
        match fault.kind:
            case SensorFaultKind.STUCK:
                return fault.stuck_value if fault.stuck_value is not None else value
            case SensorFaultKind.DRIFT:
                return value + fault.rate_per_cycle * (self._cycle - fault.onset_cycle)
            case SensorFaultKind.BIAS:
                return value + fault.rate_per_cycle
        return value

    def apply(self, reading: TrueReading, sample: ProfileSample) -> SampleReading:
        """Produce the sensed sample from truth + sample context."""
        egt = self._egt.sample(self._fault_value("egt_c", reading.egt_c))
        n1 = self._n1.sample(self._fault_value("n1_pct", reading.n1_pct))
        n2 = self._n2.sample(self._fault_value("n2_pct", reading.n2_pct))
        fuel = self._fuel.sample(self._fault_value("fuel_flow_kg_h", reading.fuel_flow_kg_h))
        vib = self._vib.sample(self._fault_value("vibration_ips", reading.vibration_ips))
        oil_t = self._oil_t.sample(self._fault_value("oil_temp_c", reading.oil_temp_c))
        oil_p = self._oil_p.sample(self._fault_value("oil_pressure_kpa", reading.oil_pressure_kpa))
        return SampleReading(
            t_offset_s=sample.t_offset_s,
            phase=sample.phase,
            alt_ft=sample.alt_ft,
            airspeed_kt=sample.airspeed_kt,
            oat_c=sample.oat_c,
            thrust_pct=sample.thrust_pct,
            mach=sample.mach,
            egt_c=egt,
            n1_pct=n1,
            n2_pct=n2,
            fuel_flow_kg_h=fuel,
            vibration_ips=vib,
            oil_temp_c=oil_t,
            oil_pressure_kpa=oil_p,
        )

    def active_faults(self) -> list[str]:
        """Params with a sensor fault currently in effect (for the manifest)."""
        return sorted(p for p, f in self._faults.items() if self._cycle >= f.onset_cycle)


__all__ = ["SampleReading", "SensorLayer", "_FAULTABLE_PARAMS"]
