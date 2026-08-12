from datetime import UTC, datetime

from ehm.core.schemas import EngineSnapshot, FlightPhase


def test_snapshot_builds_and_ignores_extra_fields():
    snap = EngineSnapshot.model_validate(
        {
            "esn": "E1",
            "flight_id": "F1",
            "phase": "cruise",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "egt_c": 640.0,
            "config_tag": "LEAP1C-A",
            "not_a_real_field": 999,
        }
    )
    assert snap.phase is FlightPhase.CRUISE
    assert snap.egt_c == 640.0
    assert snap.config_tag == "LEAP1C-A"
    assert not hasattr(snap, "not_a_real_field")


def test_optional_params_default_to_none():
    snap = EngineSnapshot(
        esn="E1",
        flight_id="F1",
        phase=FlightPhase.GROUND,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert snap.egt_c is None
    assert snap.n1_pct is None
    assert snap.config_tag == "default"


def test_flight_phase_enum_values():
    assert FlightPhase.CRUISE.value == "cruise"
    assert len(list(FlightPhase)) == 6
