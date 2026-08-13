"""The synthetic-data factory — config-driven, physics-driven, reproducible.

Pipeline::

    SynthConfig (seed)
      -> per engine: resolve confounders -> per flight (cycle):
           evolve degradation -> sample OAT -> build full-flight profile
             -> physics truth per sample -> sensor reality -> QAR rows
           -> cruise snapshot (for scenario pipelines) + oil-level mass balance
      -> emit QAR-CSV (one file/flight) + snapshots.jsonl + manifest.jsonl
      -> write config.json + config_hash + README (provenance + honesty note)

Output is consumed by the existing adapters (``QarCsvAdapter`` / ``SyntheticAdapter``)
over the same path real data will take, so the factory doubles as end-to-end
architecture verification. Labels come only from ``manifest.jsonl`` (what we
injected), tagged ``source=synthetic``.

Scope (per docs/synthetic-data-plan.md, P2): QAR-CSV + manifest + snapshots.
ACARS-JSONL / MRO-JSONL / C-MAPSS method-validation are deferred (P4/P5).
"""

from __future__ import annotations

import csv
import json
import random
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ehm.core.schemas import EngineSnapshot, FlightPhase
from ehm.data_brain.physics import default_design
from ehm.data_brain.synth.config import (
    ConfounderKind,
    ConfounderSpec,
    DegradationKind,
    DegradationSpec,
    EngineSpec,
    Season,
    SensorFaultKind,
    SensorFaultSpec,
    SynthConfig,
    TruthLabel,
)
from ehm.data_brain.synth.confounders import ResolvedConfounders, resolve_for_esn
from ehm.data_brain.synth.engine import (
    DegradationState,
    evolve,
    magnitude,
    oil_burn_litres,
    true_reading,
)
from ehm.data_brain.synth.manifest import FlightTruth, classify, write_manifest
from ehm.data_brain.synth.mission import build_profile, sample_surface_oat
from ehm.data_brain.synth.sensor import SampleReading, SensorLayer

_FACTORY_VERSION = "0.1.0"
_BASE_TS = datetime(2026, 8, 1, tzinfo=UTC)
_FLIGHT_SPACING = timedelta(hours=6)
_TANK_START_L = 12.0

# QAR columns match ingestion.EXAMPLE_QAR_MAP (EGT in °F, FF in lb/h on disk).
_QAR_COLUMNS: tuple[tuple[str, str], ...] = (
    ("time", "time"),
    ("ALT_FT", "alt_ft"),
    ("SPD_KT", "airspeed_kt"),
    ("SAT_C", "oat_c"),
    ("N1", "n1_pct"),
    ("N2", "n2_pct"),
    ("EGT_F", "egt_c"),  # converted °C -> °F on emit
    ("FF_LBH", "fuel_flow_kg_h"),  # converted kg/h -> lb/h on emit
    ("VIB", "vibration_ips"),
    ("THR", "thrust_pct"),
)


def _deg_c_to_f(c: float) -> float:
    return c * 9.0 / 5.0 + 32.0


def _kg_h_to_lb_h(kg: float) -> float:
    return kg / 0.45359237


def default_config(dataset_id: str = "synth-fleet-v1", seed: int = 42) -> SynthConfig:
    """A demo fleet exercising peers, fault, sensor-fault, confounder, low-data."""
    fleet = (
        EngineSpec(esn="ESN_HEALTHY_A", config="LEAP1C-A", route_family="short_haul"),
        EngineSpec(esn="ESN_HEALTHY_B", config="LEAP1C-A", route_family="short_haul"),
        EngineSpec(
            esn="ESN_HPC_DECAY",
            config="LEAP1C-A",
            route_family="short_haul",
            degradation=DegradationSpec(
                DegradationKind.HPC_EFFICIENCY_DECAY,
                onset_cycle=5,
                rate_per_cycle=0.0015,
                max_magnitude=0.08,
            ),
        ),
        EngineSpec(
            esn="ESN_EGT_DRIFT",
            config="LEAP1C-A",
            route_family="short_haul",
            sensor_faults=(
                SensorFaultSpec(
                    SensorFaultKind.DRIFT, param="egt_c", onset_cycle=5, rate_per_cycle=0.08
                ),
            ),
        ),
        EngineSpec(
            esn="ESN_HOTDAY", config="LEAP1C-A", route_family="short_haul", season=Season.SUMMER
        ),
        EngineSpec(
            esn="ESN_LOWDATA_B", config="LEAP1C-B", route_family="short_haul", n_flights=4
        ),
    )
    confounders = (
        ConfounderSpec(
            ConfounderKind.HOT_DAY, applies_to_esns=("ESN_HOTDAY",), oat_delta_c=12.0
        ),
    )
    return SynthConfig(
        dataset_id=dataset_id,
        seed=seed,
        factory_version=_FACTORY_VERSION,
        fleet=fleet,
        confounders=confounders,
    )


def _flight_id(esn: str, cycle: int) -> str:
    return f"{esn}-F{cycle:04d}"


def _flight_ts(cycle: int) -> datetime:
    return _BASE_TS + cycle * _FLIGHT_SPACING


def _iso(ts: datetime, offset_s: float) -> str:
    return (ts + timedelta(seconds=offset_s)).isoformat().replace("+00:00", "Z")


def _emit_qar_csv(path: Path, flight_ts: datetime, readings: list[SampleReading]) -> None:
    """Write one flight's QAR CSV (units inverted vs the ingestion ParameterMap)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([col for col, _ in _QAR_COLUMNS])
        for r in readings:
            egt = _deg_c_to_f(r.egt_c) if r.egt_c is not None else None
            fuel = _kg_h_to_lb_h(r.fuel_flow_kg_h) if r.fuel_flow_kg_h is not None else None
            values: list[str] = [_iso(flight_ts, r.t_offset_s)]
            cells: dict[str, float | None] = {
                "alt_ft": r.alt_ft,
                "airspeed_kt": r.airspeed_kt,
                "oat_c": r.oat_c,
                "n1_pct": r.n1_pct,
                "n2_pct": r.n2_pct,
                "egt_c": egt,
                "fuel_flow_kg_h": fuel,
                "vibration_ips": r.vibration_ips,
                "thrust_pct": r.thrust_pct,
            }
            for _, attr in _QAR_COLUMNS[1:]:
                val = cells[attr]
                values.append("" if val is None else f"{val:.4g}")
            writer.writerow(values)


def _cruise_snapshot(
    esn: str, config: str, flight_id: str, flight_ts: datetime,
    readings: list[SampleReading], oil_level_l: float,
) -> EngineSnapshot | None:
    """Pick the median cruise sample and freeze it as a canonical cruise snapshot."""
    cruise_idx = [i for i, r in enumerate(readings) if r.phase is FlightPhase.CRUISE]
    if not cruise_idx:
        return None
    mid = cruise_idx[len(cruise_idx) // 2]
    r = readings[mid]
    fields: dict[str, object] = {
        "esn": esn,
        "flight_id": flight_id,
        "phase": FlightPhase.CRUISE,
        "timestamp": flight_ts + timedelta(seconds=r.t_offset_s),
        "oat_c": r.oat_c,
        "thrust_ref_pct": r.thrust_pct,
        "n1_pct": r.n1_pct,
        "n2_pct": r.n2_pct,
        "egt_c": r.egt_c,
        "fuel_flow_kg_h": r.fuel_flow_kg_h,
        "vibration_ips": r.vibration_ips,
        "oil_temp_c": r.oil_temp_c,
        "oil_pressure_kpa": r.oil_pressure_kpa,
        "oil_level_l": round(oil_level_l, 3),
        "config_tag": config,
    }
    return EngineSnapshot.model_validate(fields)


def _phase_counts(readings: list[SampleReading]) -> dict[str, int]:
    return {phase: n for phase, n in sorted(Counter(r.phase.value for r in readings).items())}


def run_factory(config: SynthConfig) -> Path:
    """Generate the dataset on disk; return its root directory."""
    out = Path(config.out_dir) / config.dataset_id
    qar_dir = out / "qar_csv"
    design = default_design()
    master_rng = random.Random(config.seed)
    manifest: list[FlightTruth] = []
    snapshots: list[EngineSnapshot] = []

    for engine in config.fleet:
        eng_rng = random.Random(master_rng.randrange(2**32))
        resolved = resolve_for_esn(engine.esn, config.confounders)
        oil_level = _TANK_START_L
        for cycle in range(engine.n_flights):
            state = evolve(engine.degradation, cycle)
            mag = magnitude(engine.degradation, cycle)
            surface_oat = sample_surface_oat(engine.season, eng_rng) + resolved.oat_delta_c
            profile = build_profile(
                engine.route_family, surface_oat, config.sensor_model.sample_rate_hz
            )
            sensor = SensorLayer(config.sensor_model, engine.sensor_faults, cycle, eng_rng)
            readings = [sensor.apply(true_reading(design, s, state), s) for s in profile]
            oil_level = max(0.0, oil_level - oil_burn_litres(profile, state))

            fid = _flight_id(engine.esn, cycle)
            fts = _flight_ts(cycle)
            _emit_qar_csv(qar_dir / f"{engine.esn}_{fid}.csv", fts, readings)

            snap = _cruise_snapshot(
                engine.esn, engine.config, fid, fts, readings, oil_level
            )
            if snap is not None:
                snapshots.append(snap)

            truth = classify(state.active, sensor.active_faults())
            manifest.append(
                _make_truth(engine, fid, cycle, fts, readings, mag, state, sensor, resolved, truth)
            )

    _write_artifacts(out, config, manifest, snapshots)
    return out


def _make_truth(
    engine: EngineSpec, fid: str, cycle: int, fts: datetime,
    readings: list[SampleReading], mag: float, state: DegradationState,
    sensor: SensorLayer, resolved: ResolvedConfounders, truth: TruthLabel,
) -> FlightTruth:
    return FlightTruth(
        esn=engine.esn,
        flight_id=fid,
        cycle=cycle,
        timestamp=_iso(fts, 0.0),
        n_samples=len(readings),
        phase_counts=_phase_counts(readings),
        degradation_kind=engine.degradation.kind.value,
        degradation_magnitude=round(mag, 6),
        degradation_active=state.active,
        sensor_faults_active=sensor.active_faults(),
        confounders_active=list(resolved.active),
        truth_label=truth.value,
    )


def _write_snapshots(snapshots: list[EngineSnapshot], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "snapshots.jsonl").open("w", encoding="utf-8") as handle:
        for snap in snapshots:
            handle.write(snap.model_dump_json() + "\n")


def _write_artifacts(
    out: Path, config: SynthConfig, manifest: list[FlightTruth], snapshots: list[EngineSnapshot]
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    write_manifest(manifest, out / "manifest.jsonl")
    _write_snapshots(snapshots, out)
    (out / "config.json").write_text(
        json.dumps(config.to_jsonable(), indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    (out / "config_hash.txt").write_text(config.config_hash() + "\n", encoding="utf-8")
    _write_readme(out, config, manifest)


def _write_readme(out: Path, config: SynthConfig, manifest: list[FlightTruth]) -> None:
    counts = Counter(r.truth_label for r in manifest)
    body = [
        f"Synthetic dataset: {config.dataset_id}",
        f"factory_version : {config.factory_version}",
        f"seed            : {config.seed}",
        f"config_hash     : {config.config_hash()}",
        "",
        "source          : SYNTHETIC (physics-driven). NOT real flight data, NOT LEAP-1C",
        "                  OEM truth. Coefficients are generic placeholders; the residual",
        "                  used for monitoring is calibration-invariant (ADR-0010/0013).",
        "labels          : manifest.jsonl only (what was injected). Never mix with real labels.",
        "",
        "truth breakdown : "
        + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())),
        "",
        "Reproduce        : run the factory with config.json + this seed + factory_version.",
    ]
    (out / "README.txt").write_text("\n".join(body) + "\n", encoding="utf-8")


__all__ = ["default_config", "run_factory"]
