"""Declarative configuration for the synthetic-data factory.

Everything reproducibility needs lives here: fleet, missions, degradation,
sensor model, confounders, output. A ``SynthConfig`` is frozen; its
``config_hash`` pins the dataset, so a run is fully reproducible from
``(config, factory_version, seed)``. See ``docs/synthetic-data-plan.md``.

Honesty (per ADR-0010/0013 and CODEBUDDY §5): labels are *what we injected*,
never model-hallucinated; every record is tagged ``source=synthetic`` and must
never be mixed with real data.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum


class DegradationKind(StrEnum):
    """Engine-fault injection modes (each maps to physics knobs in ``engine``)."""

    NONE = "none"
    HPC_EFFICIENCY_DECAY = "hpc_efficiency_decay"  # gas-path: T3 up + EGT up + fuel up
    TURBINE_DISTRESS = "turbine_distress"  # gas-path: EGT up strongly (more fuel)
    BEARING_WEAR = "bearing_wear"  # vibration: unbalance up
    OIL_LEAK = "oil_leak"  # oil: consumption up


class SensorFaultKind(StrEnum):
    """Sensor-channel faults — distinct from engine faults (mislabel driver)."""

    DRIFT = "drift"  # cumulative drift vs cycle
    STUCK = "stuck"  # frozen at a value
    BIAS = "bias"  # constant offset from onset


class ConfounderKind(StrEnum):
    """Operating-condition confounders — real physics, NOT faults (truth=no_fault)."""

    HOT_DAY = "hot_day"  # raised OAT -> EGT up (looks like degradation)
    COLD_DAY = "cold_day"  # lowered OAT -> oil/temp signature
    HIGH_ALT_AIRPORT = "high_alt_airport"  # raised field elevation -> takeoff EGT up


class Season(StrEnum):
    """Season drives the surface-OAT distribution the mission sampler draws from."""

    SUMMER = "summer"
    WINTER = "winter"
    ISA = "isa"


class TruthLabel(StrEnum):
    """Authoritative per-flight ground truth (what was injected)."""

    TRUE_FAULT = "true_fault"
    SENSOR_FAULT = "sensor_fault"
    NO_FAULT = "no_fault"


@dataclass(frozen=True)
class DegradationSpec:
    """A linearly-growing engine-fault injection.

    Magnitude grows as ``min(rate_per_cycle * (cycle - onset_cycle), max_magnitude)``
    for cycles at/after ``onset_cycle``; zero before.
    """

    kind: DegradationKind = DegradationKind.NONE
    onset_cycle: int = 0
    rate_per_cycle: float = 0.0
    max_magnitude: float = 1.0


@dataclass(frozen=True)
class SensorFaultSpec:
    """A sensor-channel fault on one canonical parameter.

    ``param`` is a canonical ``EngineSnapshot`` attribute (e.g. ``"egt_c"``).
    DRIFT uses ``rate_per_cycle``; BIAS uses ``rate_per_cycle`` as the offset;
    STUCK uses ``stuck_value``.
    """

    kind: SensorFaultKind
    param: str
    onset_cycle: int = 0
    rate_per_cycle: float = 0.0
    stuck_value: float | None = None


@dataclass(frozen=True)
class ConfounderSpec:
    """An operating-condition confounder applied before physics (no fault injected)."""

    kind: ConfounderKind
    applies_to_esns: tuple[str, ...] = ()  # empty = all engines
    oat_delta_c: float = 0.0
    field_elevation_ft: float = 0.0


@dataclass(frozen=True)
class EngineSpec:
    """One engine in the synthetic fleet."""

    esn: str
    config: str
    route_family: str  # "short_haul" | "long_haul"
    season: Season = Season.ISA
    n_flights: int = 50
    degradation: DegradationSpec = DegradationSpec(DegradationKind.NONE)
    sensor_faults: tuple[SensorFaultSpec, ...] = ()


@dataclass(frozen=True)
class SensorModelSpec:
    """Sensor-channel reality model (noise, autocorrelation, dropout)."""

    egt_noise_sd: float = 2.0
    egt_ar1: float = 0.3
    n1_noise_sd: float = 0.15
    n2_noise_sd: float = 0.15
    fuel_noise_sd: float = 18.0
    vibration_noise_sd: float = 0.04
    oil_temp_noise_sd: float = 1.2
    oil_press_noise_sd: float = 4.0
    dropout_p: float = 0.002
    # (phase -> Hz); cruise is sampled sparsely, non-cruise densely (real QAR).
    sample_rate_hz: tuple[tuple[str, float], ...] = (
        ("ground", 0.2),
        ("takeoff", 1.0),
        ("climb", 0.5),
        ("cruise", 0.25),
        ("descent", 0.5),
        ("approach", 1.0),
    )


@dataclass(frozen=True)
class SynthConfig:
    """Top-level factory configuration. Frozen + JSON-hashable for reproducibility."""

    dataset_id: str
    seed: int
    factory_version: str
    fleet: tuple[EngineSpec, ...]
    sensor_model: SensorModelSpec = field(default_factory=SensorModelSpec)
    confounders: tuple[ConfounderSpec, ...] = ()
    out_dir: str = "data/synth"

    def config_hash(self) -> str:
        """Stable short hash of the full config (sorted JSON) for manifest provenance."""
        blob = json.dumps(self.to_jsonable(), sort_keys=True, default=str).encode()
        return hashlib.sha256(blob).hexdigest()[:16]

    def to_jsonable(self) -> dict[str, object]:
        """Return a JSON-serialisable view (StrEnum -> str via ``default=str``)."""
        return asdict(self)


__all__ = [
    "ConfounderKind",
    "ConfounderSpec",
    "DegradationKind",
    "DegradationSpec",
    "EngineSpec",
    "Season",
    "SensorFaultKind",
    "SensorFaultSpec",
    "SensorModelSpec",
    "SynthConfig",
    "TruthLabel",
]
