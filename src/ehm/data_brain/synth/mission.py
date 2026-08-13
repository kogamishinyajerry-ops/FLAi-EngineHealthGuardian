"""Flight-mission profile generator (ground -> takeoff -> ... -> ground).

Replaces the single cruise snapshot of ``scenarios/*/synthetic.py`` with a full
flight profile. Cruise altitude/duration come from the route family; OAT follows
the ISA lapse rate from a seasonal surface temperature plus confounder offsets.
Profiles are built so ingestion's ``PhaseTracker`` reconstructs the phase from
altitude/airspeed — a round-trip the factory tests assert. Altitude/airspeed are
kept noise-free so phase boundaries stay stable; noise lives on engine params.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

from ehm.core.schemas import FlightPhase
from ehm.data_brain.synth.config import Season

# Route family -> (cruise altitude ft, cruise duration min).
_ROUTE_PARAMS: dict[str, tuple[float, float]] = {
    "short_haul": (36000.0, 40.0),
    "long_haul": (39000.0, 180.0),
}

# Season -> surface OAT (mean °C, sd °C).
_SEASON_OAT: dict[Season, tuple[float, float]] = {
    Season.SUMMER: (28.0, 5.0),
    Season.WINTER: (2.0, 8.0),
    Season.ISA: (15.0, 5.0),
}

_TROPOPAUSE_OAT_C = -56.5
_LAPSE_C_PER_1000M = 6.5
_FT_TO_M = 0.3048
# Speed of sound in knots ≈ 38.97 * sqrt(T_K).
_SOS_KT_COEF = 38.97


@dataclass(frozen=True)
class ProfileSample:
    """One time-sample of a flight's operating condition (pre-sensor truth)."""

    t_offset_s: float
    phase: FlightPhase
    alt_ft: float
    airspeed_kt: float
    mach: float
    thrust_pct: float
    oat_c: float


@dataclass(frozen=True)
class _Segment:
    """A phase leg interpolated linearly between its start/end conditions."""

    phase: FlightPhase
    duration_s: float
    alt_start: float
    alt_end: float
    spd_start: float
    spd_end: float
    thrust_start: float
    thrust_end: float


def _segments(cruise_alt_ft: float, cruise_min: float) -> tuple[_Segment, ...]:
    """Build the phase legs; durations make each PhaseTracker band populated."""
    cruise_s = cruise_min * 60.0
    return (
        _Segment(FlightPhase.GROUND, 120.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        _Segment(FlightPhase.TAKEOFF, 45.0, 0.0, 1500.0, 0.0, 250.0, 100.0, 95.0),
        _Segment(
            FlightPhase.CLIMB, 720.0, 1500.0, cruise_alt_ft, 250.0, 300.0, 95.0, 82.0
        ),
        _Segment(
            FlightPhase.CRUISE, cruise_s, cruise_alt_ft, cruise_alt_ft, 470.0, 470.0, 82.0, 82.0
        ),
        _Segment(FlightPhase.DESCENT, 900.0, cruise_alt_ft, 3000.0, 300.0, 200.0, 80.0, 40.0),
        _Segment(FlightPhase.APPROACH, 360.0, 3000.0, 0.0, 200.0, 140.0, 35.0, 15.0),
        _Segment(FlightPhase.GROUND, 60.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    )


def _oat_at_alt(surface_oat_c: float, alt_ft: float) -> float:
    """ISA lapse-rate OAT (°C) at altitude, floored at the tropopause."""
    alt_km = alt_ft * _FT_TO_M / 1000.0
    return max(surface_oat_c - _LAPSE_C_PER_1000M * alt_km, _TROPOPAUSE_OAT_C)


def _mach_from(airspeed_kt: float, oat_c: float) -> float:
    """Mach from true airspeed and OAT (speed of sound in knots)."""
    sos = _SOS_KT_COEF * (oat_c + 273.15) ** 0.5
    return airspeed_kt / sos if sos > 0 else 0.0


def _rate_for(phase: FlightPhase, rates: Sequence[tuple[str, float]]) -> float:
    """Look up the sample rate (Hz) for a phase; default 0.5 Hz."""
    label = phase.value
    for key, hz in rates:
        if key == label:
            return hz
    return 0.5


def build_profile(
    route_family: str,
    surface_oat_c: float,
    sample_rates: Sequence[tuple[str, float]],
) -> list[ProfileSample]:
    """Build the full-flight sample list for one flight.

    ``surface_oat_c`` already includes any confounder offset. Each phase leg is
    sampled at its own rate; alt/airspeed are noise-free so the PhaseTracker
    round-trip is stable.
    """
    cruise_alt_ft, cruise_min = _ROUTE_PARAMS.get(route_family, _ROUTE_PARAMS["short_haul"])
    samples: list[ProfileSample] = []
    t = 0.0
    for seg in _segments(cruise_alt_ft, cruise_min):
        hz = _rate_for(seg.phase, sample_rates)
        n = max(2, int(round(seg.duration_s * hz)))
        for i in range(n):
            frac = i / n
            alt = seg.alt_start + (seg.alt_end - seg.alt_start) * frac
            spd = seg.spd_start + (seg.spd_end - seg.spd_start) * frac
            thr = seg.thrust_start + (seg.thrust_end - seg.thrust_start) * frac
            oat = _oat_at_alt(surface_oat_c, alt)
            samples.append(
                ProfileSample(
                    t_offset_s=t,
                    phase=seg.phase,
                    alt_ft=alt,
                    airspeed_kt=spd,
                    mach=_mach_from(spd, oat),
                    thrust_pct=thr,
                    oat_c=oat,
                )
            )
            t += seg.duration_s / n
    return samples


def sample_surface_oat(season: Season, rng: random.Random) -> float:
    """Draw a surface OAT (°C) for a flight from the seasonal distribution."""
    mean, sd = _SEASON_OAT.get(season, _SEASON_OAT[Season.ISA])
    return rng.gauss(mean, sd)


__all__ = ["ProfileSample", "build_profile", "sample_surface_oat"]
