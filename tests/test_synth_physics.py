"""Directional physics tests for the vibration + oil sub-models.

Mirrors the style of test_physics.py: assertions are on functional form
(direction), not absolute magnitudes — coefficients are generic placeholders.
"""

from ehm.core.schemas import FlightPhase
from ehm.data_brain.physics import (
    OilState,
    VibrationState,
    consumption_rate_l_per_h,
    default_design,
    oil_pressure,
    oil_temperature,
    vibration_at,
    vibration_healthy,
)
from ehm.data_brain.synth.config import DegradationKind, DegradationSpec
from ehm.data_brain.synth.engine import DegradationState, evolve, magnitude, true_reading
from ehm.data_brain.synth.mission import build_profile

# --- vibration --------------------------------------------------------------


def test_vibration_rises_with_rotor_speed():
    idle = vibration_healthy(n1_pct=60.0, n2_pct=72.0)
    cruise = vibration_healthy(n1_pct=90.0, n2_pct=93.0)
    assert cruise > idle  # faster spools -> more unbalance force


def test_vibration_rises_with_unbalance():
    healthy = vibration_at(90.0, 93.0, VibrationState(unbalance_factor=1.0))
    worn = vibration_at(90.0, 93.0, VibrationState(unbalance_factor=1.5))
    assert worn > healthy  # bearing wear / blade loss raises vibration


# --- oil --------------------------------------------------------------------


def test_oil_temp_rises_with_egt():
    cool = oil_temperature(500.0, OilState())
    hot = oil_temperature(700.0, OilState())
    assert hot > cool  # hotter engine -> hotter oil


def test_oil_temp_penalty_adds():
    base = oil_temperature(600.0, OilState())
    distressed = oil_temperature(600.0, OilState(oil_temp_penalty_c=15.0))
    assert distressed > base + 14.0


def test_oil_pressure_rises_with_n2():
    idle = oil_pressure(72.0, OilState())
    cruise = oil_pressure(93.0, OilState())
    assert cruise > idle  # pump speed drives pressure


def test_leak_raises_consumption():
    healthy = consumption_rate_l_per_h(OilState())
    leaking = consumption_rate_l_per_h(OilState(leak_rate_l_per_h=0.2))
    assert leaking > healthy


# --- degradation evolution --------------------------------------------------


def test_magnitude_zero_before_onset_and_grows():
    spec = DegradationSpec(DegradationKind.HPC_EFFICIENCY_DECAY, onset_cycle=5, rate_per_cycle=0.01)
    assert magnitude(spec, 0) == 0.0
    assert magnitude(spec, 4) == 0.0
    assert magnitude(spec, 10) > magnitude(spec, 7)
    # capped
    capped = DegradationSpec(
        DegradationKind.HPC_EFFICIENCY_DECAY, onset_cycle=0, rate_per_cycle=1.0, max_magnitude=0.05
    )
    assert magnitude(capped, 100) == 0.05


def test_hpc_decay_state_marks_active_and_raises_egt():
    design = default_design()
    # degradation must be evaluated at sustained power (cruise), where the cycle
    # model is valid — not at ground idle (out of domain, EGT floored).
    profile = build_profile("short_haul", 15.0, (("cruise", 0.25),))
    sample = next(s for s in profile if s.phase is FlightPhase.CRUISE)
    healthy = true_reading(design, sample, DegradationState())
    deg_state = evolve(
        DegradationSpec(DegradationKind.HPC_EFFICIENCY_DECAY, onset_cycle=0, rate_per_cycle=0.01),
        cycle=8,
    )
    assert deg_state.active
    degraded = true_reading(design, sample, deg_state)
    assert degraded.egt_c > healthy.egt_c  # HPC decay -> hotter EGT
    assert degraded.fuel_flow_kg_h > healthy.fuel_flow_kg_h  # and more fuel


def test_bearing_wear_raises_vibration_only():
    design = default_design()
    # pick a cruise sample for a non-trivial rotor speed
    profile = [
        s
        for s in build_profile("short_haul", 15.0, (("cruise", 0.25),))
        if s.phase is FlightPhase.CRUISE
    ]
    sample = profile[len(profile) // 2]
    healthy = true_reading(design, sample, DegradationState())
    worn = evolve(
        DegradationSpec(DegradationKind.BEARING_WEAR, onset_cycle=0, rate_per_cycle=0.1), cycle=1
    )
    degraded = true_reading(design, sample, worn)
    assert degraded.vibration_ips > healthy.vibration_ips
    # gas-path EGT is essentially unaffected by a pure bearing-wear fault
    assert abs(degraded.egt_c - healthy.egt_c) < 1e-6


def test_profile_is_full_flight_with_all_phases():
    profile = build_profile("short_haul", 15.0, (("cruise", 0.25),))
    phases = {s.phase for s in profile}
    assert phases == {
        FlightPhase.GROUND,
        FlightPhase.TAKEOFF,
        FlightPhase.CLIMB,
        FlightPhase.CRUISE,
        FlightPhase.DESCENT,
        FlightPhase.APPROACH,
    }


def test_full_profile_egt_stays_in_dq_band():
    """Every phase (incl. ground idle) yields a DQ-plausible EGT (>= -60 °C)."""
    design = default_design()
    profile = build_profile("short_haul", 15.0, (("cruise", 0.25),))
    egts = [true_reading(design, s, DegradationState()).egt_c for s in profile]
    assert all(-60.0 <= e <= 1200.0 for e in egts)
    assert all(e >= 0.0 for e in egts)  # idle floor keeps exhaust above ambient
