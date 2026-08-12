"""Flight-phase detection from a time-ordered altitude/airspeed sequence.

QAR samples are raw time-series without a phase column. Real systems derive phase
from altitude + airspeed trend; this module provides a small **stateful** tracker
that consumes ``(altitude_ft, airspeed_kt)`` samples in order and emits the flight
phase via a state machine (ground -> takeoff -> climb -> cruise -> descent ->
approach -> ground).

Thresholds are heuristic placeholders (NOT OEM-derived); the report lists proper
phase detection as work to do, but a sequence-aware tracker is far more correct
than band-classifying a single sample (which cannot distinguish climb from
descent at the same altitude).
"""

from __future__ import annotations

from ehm.core.schemas import FlightPhase

#: Hysteresis (ft) so level-flight noise doesn't flip the climb/descent state.
_ALT_HYST = 50.0
_CRUISE_THRESHOLD_FT = 20000.0
_APPROACH_THRESHOLD_FT = 3000.0
_GROUND_ALT_FT = 100.0
_GROUND_SPD_KT = 40.0
_TAKEOFF_TRANSITION_FT = 1000.0


class PhaseTracker:
    """Sequence-aware flight-phase state machine."""

    def __init__(self) -> None:
        self._state: FlightPhase = FlightPhase.GROUND
        self._prev_alt: float | None = None

    def update(self, altitude_ft: float | None, airspeed_kt: float | None) -> FlightPhase:
        """Advance the state with one sample; returns the current phase."""
        if altitude_ft is None or airspeed_kt is None:
            return self._state
        falling = self._prev_alt is not None and altitude_ft < self._prev_alt - _ALT_HYST

        match self._state:
            case FlightPhase.GROUND:
                if altitude_ft > _GROUND_ALT_FT or airspeed_kt > _GROUND_SPD_KT:
                    self._state = FlightPhase.TAKEOFF
            case FlightPhase.TAKEOFF:
                if altitude_ft > _TAKEOFF_TRANSITION_FT:
                    self._state = FlightPhase.CLIMB
                elif altitude_ft <= _GROUND_ALT_FT and airspeed_kt <= _GROUND_SPD_KT:
                    self._state = FlightPhase.GROUND
            case FlightPhase.CLIMB:
                if falling:
                    self._state = FlightPhase.DESCENT
                elif altitude_ft >= _CRUISE_THRESHOLD_FT:
                    self._state = FlightPhase.CRUISE
            case FlightPhase.CRUISE:
                if falling:
                    self._state = FlightPhase.DESCENT
            case FlightPhase.DESCENT:
                if altitude_ft <= _APPROACH_THRESHOLD_FT:
                    self._state = FlightPhase.APPROACH
            case FlightPhase.APPROACH:
                if altitude_ft <= _GROUND_ALT_FT and airspeed_kt <= _GROUND_SPD_KT:
                    self._state = FlightPhase.GROUND

        self._prev_alt = altitude_ft
        return self._state
