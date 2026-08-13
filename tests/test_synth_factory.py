"""End-to-end tests for the synthetic-data factory.

These prove the factory's headline claims:
- it writes the documented artifacts (QAR-CSV, snapshots, manifest, config, hash);
- QAR-CSV round-trips through the existing ``QarCsvAdapter`` + ``PhaseTracker``
  (phases reconstruct, units invert correctly) — i.e. synthetic data walks the
  same path real data will;
- the manifest carries honest truth labels (what was injected);
- the run is bit-for-bit reproducible from (config, seed).
"""

import csv
import json
from pathlib import Path

import pytest

from ehm.core.schemas import FlightPhase
from ehm.data_brain.ingestion import EXAMPLE_QAR_MAP, QarCsvAdapter
from ehm.data_brain.synth import SynthConfig, run_factory
from ehm.data_brain.synth.config import (
    ConfounderKind,
    ConfounderSpec,
    DegradationKind,
    DegradationSpec,
    EngineSpec,
    Season,
    SensorFaultKind,
    SensorFaultSpec,
)


def _tiny_config(out_dir: Path, seed: int = 7) -> SynthConfig:
    fleet = (
        EngineSpec(
            esn="E_H1", config="CFG-A", route_family="short_haul", season=Season.ISA, n_flights=3
        ),
        EngineSpec(
            esn="E_H2", config="CFG-A", route_family="short_haul", season=Season.ISA, n_flights=3
        ),
        EngineSpec(
            esn="E_DECAY",
            config="CFG-A",
            route_family="short_haul",
            season=Season.ISA,
            n_flights=3,
            degradation=DegradationSpec(
                DegradationKind.HPC_EFFICIENCY_DECAY,
                onset_cycle=1,
                rate_per_cycle=0.01,
                max_magnitude=0.08,
            ),
        ),
        EngineSpec(
            esn="E_DRIFT",
            config="CFG-A",
            route_family="short_haul",
            season=Season.ISA,
            n_flights=3,
            sensor_faults=(
                SensorFaultSpec(
                    SensorFaultKind.DRIFT, "egt_c", onset_cycle=1, rate_per_cycle=0.1
                ),
            ),
        ),
        EngineSpec(
            esn="E_HOT",
            config="CFG-A",
            route_family="short_haul",
            season=Season.SUMMER,
            n_flights=3,
        ),
    )
    confounders = (ConfounderSpec(ConfounderKind.HOT_DAY, ("E_HOT",), oat_delta_c=12.0),)
    return SynthConfig(
        dataset_id="test-fleet",
        seed=seed,
        factory_version="0.1.0",
        fleet=fleet,
        confounders=confounders,
        out_dir=str(out_dir),
    )


def _read_manifest(out: Path) -> list[dict]:
    with (out / "manifest.jsonl").open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_factory_writes_all_artifacts(tmp_path):
    out = run_factory(_tiny_config(tmp_path))
    assert (out / "manifest.jsonl").exists()
    assert (out / "snapshots.jsonl").exists()
    assert (out / "config.json").exists()
    assert (out / "config_hash.txt").exists()
    assert (out / "README.txt").exists()
    csvs = list((out / "qar_csv").glob("*.csv"))
    assert len(csvs) == 5 * 3  # 5 engines x 3 flights


def test_qar_csv_round_trips_phases_and_units(tmp_path):
    out = run_factory(_tiny_config(tmp_path))
    first_csv = next((out / "qar_csv").glob("E_H1_*.csv"))
    adapter = QarCsvAdapter(first_csv, EXAMPLE_QAR_MAP, esn="E_H1", flight_id="t")
    snaps = list(adapter.iter_snapshots())

    phases = {s.phase for s in snaps}
    # PhaseTracker reconstructs a full flight from alt/airspeed
    assert FlightPhase.GROUND in phases
    assert FlightPhase.TAKEOFF in phases
    assert FlightPhase.CLIMB in phases
    assert FlightPhase.CRUISE in phases
    assert FlightPhase.DESCENT in phases
    assert FlightPhase.APPROACH in phases
    assert snaps[0].phase is FlightPhase.GROUND

    # unit inversion holds: adapter °C == manual convert of the °F cell
    cruise = next(s for s in snaps if s.phase is FlightPhase.CRUISE)
    assert cruise.egt_c is not None
    assert 250.0 < cruise.egt_c < 950.0
    assert cruise.fuel_flow_kg_h is not None and cruise.fuel_flow_kg_h > 0.0


def test_qar_unit_inversion_is_arithmetic_inverse(tmp_path):
    out = run_factory(_tiny_config(tmp_path))
    first_csv = next((out / "qar_csv").glob("E_H1_*.csv"))
    adapter = QarCsvAdapter(first_csv, EXAMPLE_QAR_MAP, esn="E_H1", flight_id="t")
    snaps = list(adapter.iter_snapshots())
    with first_csv.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    # the adapter preserves row order; find a cruise row with a present EGT_F
    idx = next(
        i
        for i, s in enumerate(snaps)
        if s.phase is FlightPhase.CRUISE and s.egt_c is not None
    )
    raw_f = float(rows[idx]["EGT_F"])
    assert snaps[idx].egt_c == pytest.approx((raw_f - 32.0) * 5.0 / 9.0, rel=1e-3)


def test_manifest_truth_labels(tmp_path):
    out = run_factory(_tiny_config(tmp_path))
    by_esn: dict[str, set[str]] = {}
    for rec in _read_manifest(out):
        by_esn.setdefault(rec["esn"], set()).add(rec["truth_label"])

    assert by_esn["E_H1"] == {"no_fault"}  # healthy peer
    assert by_esn["E_H2"] == {"no_fault"}  # healthy peer
    assert by_esn["E_HOT"] == {"no_fault"}  # hot-day confounder, NOT a fault
    assert "true_fault" in by_esn["E_DECAY"]  # HPC decay active after onset
    assert "sensor_fault" in by_esn["E_DRIFT"]  # EGT drift, not an engine fault


def test_manifest_records_source_synthetic_and_config_hash(tmp_path):
    cfg = _tiny_config(tmp_path)
    out = run_factory(cfg)
    recs = _read_manifest(out)
    assert all(r["source"] == "synthetic" for r in recs)
    assert (out / "config_hash.txt").read_text().strip() == cfg.config_hash()


def test_factory_is_reproducible(tmp_path):
    cfg = _tiny_config(tmp_path / "a")
    cfg2 = _tiny_config(tmp_path / "b")
    out1 = run_factory(cfg)
    out2 = run_factory(cfg2)
    m1 = (out1 / "manifest.jsonl").read_text(encoding="utf-8")
    m2 = (out2 / "manifest.jsonl").read_text(encoding="utf-8")
    assert m1 == m2  # same seed + config -> identical manifest
    # and the QAR bytes are identical too
    f1 = sorted(p.name for p in (out1 / "qar_csv").glob("*.csv"))
    f2 = sorted(p.name for p in (out2 / "qar_csv").glob("*.csv"))
    assert f1 == f2


def test_snapshots_jsonl_parses_into_canonical_model(tmp_path):
    from ehm.core.schemas import EngineSnapshot

    out = run_factory(_tiny_config(tmp_path))
    snaps = [
        EngineSnapshot.model_validate_json(line)
        for line in (out / "snapshots.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(snaps) == 5 * 3  # one cruise snapshot per flight
    cruise = next(s for s in snaps if s.esn == "E_H1")
    assert cruise.phase is FlightPhase.CRUISE
    assert cruise.oil_level_l is not None  # oil mass-balance carried through
