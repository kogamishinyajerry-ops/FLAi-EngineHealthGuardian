from datetime import UTC, datetime

from scenarios.egt_margin.features import baseline, residual

from ehm.core.schemas import EngineSnapshot, FlightPhase
from ehm.data_brain.physics import (
    Degradation,
    OperatingPoint,
    default_design,
    egt_degraded,
    egt_healthy,
    gas_path,
)

_DESIGN = default_design()


def _op(
    oat_c: float = -40.0, mach: float = 0.8, alt: float = 11000.0, thrust: float = 0.85
) -> OperatingPoint:
    return OperatingPoint(oat_k=oat_c + 273.15, mach=mach, altitude_m=alt, thrust_frac=thrust)


# --- cycle ordering (textbook station behavior) ---


def test_compression_heats_the_air():
    gp = gas_path(_DESIGN, _op())
    assert gp.t3 > gp.t2  # compressor raises temperature


def test_turbine_cools_the_gas():
    gp = gas_path(_DESIGN, _op())
    assert gp.t5 < gp.t4  # expansion lowers temperature -> EGT below TIT


def test_compressor_pressure_rises_with_opr():
    gp = gas_path(_DESIGN, _op())
    assert gp.p3 > gp.p2


# --- directional dependence (the monitoring-relevant functional form) ---


def test_egt_rises_with_oat():
    cold = egt_healthy(_DESIGN, _op(oat_c=-30.0))
    hot = egt_healthy(_DESIGN, _op(oat_c=30.0))
    assert hot > cold  # hotter day -> hotter EGT


def test_egt_rises_with_thrust():
    idle = egt_healthy(_DESIGN, _op(thrust=0.6))
    toga = egt_healthy(_DESIGN, _op(thrust=1.0))
    assert toga > idle  # more thrust -> hotter EGT


def test_egt_in_plausible_band():
    # absolute value is illustrative, but should be a sane order of magnitude (K)
    egt_k = egt_healthy(_DESIGN, _op())
    assert 400.0 < egt_k < 1200.0


# --- degradation signature (EGT margin loss) ---


def test_degradation_raises_egt_at_fixed_thrust():
    healthy = egt_healthy(_DESIGN, _op())
    degraded = egt_degraded(_DESIGN, _op(), Degradation(thrust_penalty=0.10))
    assert degraded > healthy  # degraded engine runs hotter at the same thrust


def test_lower_compressor_efficiency_raises_t3():
    healthy = gas_path(_DESIGN, _op())
    worn = gas_path(_DESIGN, _op(), Degradation(eta_comp_factor=0.95))
    assert worn.t3 > healthy.t3  # worse compression -> hotter compressor delivery


# --- residual is calibration-invariant (monitoring value) ---


def test_baseline_returns_celsius():
    b = baseline(FlightPhase.CRUISE, 85.0, -40.0)
    assert isinstance(b, float)
    assert -100.0 < b < 1000.0  # °C sanity band


def test_residual_cancels_baseline():
    """An engine exactly at the baseline has ~zero residual regardless of conditions."""
    snap = EngineSnapshot(
        esn="E1",
        flight_id="F1",
        phase=FlightPhase.CRUISE,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        oat_c=-40.0,
        n1_pct=88.0,
        n2_pct=94.0,
        egt_c=baseline(FlightPhase.CRUISE, 85.0, -40.0),  # exactly healthy
        thrust_ref_pct=85.0,
    )
    assert abs(residual(snap)) < 1e-6


def test_residual_none_when_egt_missing():
    snap = EngineSnapshot(
        esn="E1",
        flight_id="F1",
        phase=FlightPhase.CRUISE,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        egt_c=None,
    )
    assert residual(snap) is None
