from pathlib import Path

import pytest
from scenarios.egt_margin.pipeline import run

from ehm.core.schemas import FlightPhase
from ehm.data_brain.ingestion import (
    EXAMPLE_ACARS_MAP,
    EXAMPLE_QAR_MAP,
    AcarsJsonAdapter,
    IngestionAdapter,
    ParameterMap,
    ParamSpec,
    QarCsvAdapter,
)
from ehm.data_brain.ingestion.mapping import convert, parse_time
from ehm.data_brain.ingestion.phase import PhaseTracker

FIX = Path(__file__).parent / "fixtures"


# --- unit conversion -------------------------------------------------------


def test_convert_temperature_units():
    assert convert(273.15, "K") == pytest.approx(0.0)
    assert convert(212.0, "degF") == pytest.approx(100.0)
    assert convert(100.0, "degC") == 100.0


def test_convert_pressure_and_fuel():
    assert convert(1.0, "psi") == pytest.approx(6.894757)
    assert convert(1.0, "lb_h") == pytest.approx(0.45359237)


def test_convert_none_unit_passthrough():
    assert convert(123.0, None) == 123.0


def test_convert_unknown_unit_raises():
    with pytest.raises(ValueError, match="unknown source unit"):
        convert(1.0, "smoot")


def test_parameter_map_validate_rejects_unit_mismatch():
    bad = ParameterMap(params={"X": ParamSpec("egt_c", "psi")}, time_col="t")
    with pytest.raises(ValueError, match="converts to 'kPa'"):
        bad.validate()


def test_example_maps_validate_clean():
    EXAMPLE_QAR_MAP.validate()
    EXAMPLE_ACARS_MAP.validate()


def test_parse_time_attaches_utc_when_naive():
    assert parse_time("2026-08-01T10:00:00").tzinfo is not None
    assert parse_time("2026-08-01T10:00:00Z").utcoffset() is not None


# --- phase tracker ---------------------------------------------------------


def test_phase_tracker_full_flight_profile():
    tracker = PhaseTracker()
    # (alt_ft, airspeed_kt) mirroring the QAR fixture
    profile = [
        (0, 0),
        (0, 140),
        (5000, 250),
        (15000, 300),
        (36000, 480),
        (36000, 480),
        (36000, 478),
        (15000, 320),
        (2000, 180),
        (0, 0),
    ]
    phases = [tracker.update(alt, spd) for alt, spd in profile]
    assert phases[0] is FlightPhase.GROUND
    assert phases[1] is FlightPhase.TAKEOFF
    assert phases[2] is FlightPhase.CLIMB
    assert phases[4] is FlightPhase.CRUISE
    assert phases[7] is FlightPhase.DESCENT
    assert phases[8] is FlightPhase.APPROACH
    assert phases[9] is FlightPhase.GROUND


# --- QAR-CSV adapter -------------------------------------------------------


def _qar_adapter() -> QarCsvAdapter:
    return QarCsvAdapter(
        FIX / "qar_sample.csv", EXAMPLE_QAR_MAP, esn="ESN_QAR_01", flight_id="QAR-DEMO"
    )


def test_qar_csv_decodes_all_rows_and_phases():
    snaps = list(_qar_adapter().iter_snapshots())
    assert len(snaps) == 10
    phases = [s.phase for s in snaps]
    assert phases[0] is FlightPhase.GROUND
    assert phases[1] is FlightPhase.TAKEOFF
    assert phases[4] is FlightPhase.CRUISE
    assert phases[7] is FlightPhase.DESCENT
    assert phases[8] is FlightPhase.APPROACH


def test_qar_csv_converts_units():
    snaps = list(_qar_adapter().iter_snapshots())
    cruise = snaps[4]  # EGT_F=960, FF_LBH=3000
    assert cruise.egt_c == pytest.approx((960.0 - 32.0) * 5.0 / 9.0)
    assert cruise.fuel_flow_kg_h == pytest.approx(3000.0 * 0.45359237)


def test_qar_csv_timestamps_are_tz_aware():
    snaps = list(_qar_adapter().iter_snapshots())
    assert all(s.timestamp.tzinfo is not None for s in snaps)


def test_qar_csv_missing_value_becomes_none(tmp_path):
    csv = tmp_path / "mini.csv"
    csv.write_text(
        "time,EGT_F\n2026-08-01T10:00:00Z,\n2026-08-01T10:01:00Z,900\n", encoding="utf-8"
    )
    snaps = list(QarCsvAdapter(csv, EXAMPLE_QAR_MAP, esn="E", flight_id="F").iter_snapshots())
    assert snaps[0].egt_c is None
    assert snaps[1].egt_c is not None


# --- ACARS-JSON adapter ----------------------------------------------------


def _acars_adapter() -> AcarsJsonAdapter:
    return AcarsJsonAdapter(FIX / "acars_sample.jsonl", EXAMPLE_ACARS_MAP)


def test_acars_json_decodes_messages_with_inline_identity():
    snaps = list(_acars_adapter().iter_snapshots())
    assert len(snaps) == 3
    assert snaps[0].esn == "ESN_ACARS_01"
    assert snaps[0].flight_id == "CZ1234"
    assert snaps[0].phase is FlightPhase.CRUISE
    assert snaps[0].egt_c == 640.0  # canonical units, no conversion
    assert snaps[2].esn == "ESN_ACARS_02"
    assert snaps[2].phase is FlightPhase.CLIMB


# --- protocol + integration ------------------------------------------------


def test_adapters_satisfy_ingestion_protocol():
    assert isinstance(_qar_adapter(), IngestionAdapter)
    assert isinstance(_acars_adapter(), IngestionAdapter)


def test_qar_data_flows_through_full_pipeline(tmp_path):
    """Real-format ingestion plugs into the Evidence spine end-to-end."""
    snaps = list(_qar_adapter().iter_snapshots())
    result = run(snaps, str(tmp_path / "audit.jsonl"))
    assert len(result.evidence) == 1  # one ESN in the fixture
