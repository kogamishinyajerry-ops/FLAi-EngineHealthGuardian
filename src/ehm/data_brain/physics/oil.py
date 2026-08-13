"""Oil-system model — consumption mass balance + temperature/pressure proxy.

Companion to ``cycle.py`` (ADR-0010/0013). Placeholder coefficients, NOT OEM.
The functional form is physical: oil temperature tracks engine heat (EGT), oil
pressure tracks the scavenger/pump speed (N2), and tank level integrates
consumption over flight hours. A leak adds consumption; bearing distress raises
oil temperature and destabilises pressure. Absolute magnitudes are illustrative;
the rate residual used for monitoring is calibration-invariant.
"""

from __future__ import annotations

from dataclasses import dataclass

# Placeholder coefficients (illustrative).
_BASE_BURN_L_PER_H = 0.04  # healthy steady consumption
_OIL_TEMP_GAIN = 0.18  # °C oil-temp rise per °C of EGT above the reference
_OIL_TEMP_REF_EGT_C = 600.0
_OIL_TEMP_FLOOR_C = 80.0
_OIL_PRESS_BASE_KPA = 280.0  # at idle N2
_OIL_PRESS_GAIN = 1.8  # kPa per %N2


@dataclass(frozen=True)
class OilState:
    """Per-engine oil-system health (the digital-twin knob for the oil domain).

    ``leak_rate_l_per_h`` adds consumption (a leak); ``oil_temp_penalty_c`` models
    bearing distress / coolant inefficiency raising oil temp; ``press_jitter``
    destabilises pressure.
    """

    leak_rate_l_per_h: float = 0.0
    oil_temp_penalty_c: float = 0.0
    press_jitter: float = 0.0


def oil_temperature(egt_c: float, state: OilState) -> float:
    """Oil temperature (°C) from exhaust heat and oil-system health."""
    base = _OIL_TEMP_FLOOR_C + _OIL_TEMP_GAIN * max(0.0, egt_c - _OIL_TEMP_REF_EGT_C)
    return base + state.oil_temp_penalty_c


def oil_pressure(n2_pct: float, state: OilState) -> float:
    """Oil pressure (kPa) from pump (N2) speed and oil-system health."""
    return _OIL_PRESS_BASE_KPA + _OIL_PRESS_GAIN * max(0.0, n2_pct) + state.press_jitter


def consumption_rate_l_per_h(state: OilState) -> float:
    """Total oil consumption (L/h): healthy burn plus any leak."""
    return _BASE_BURN_L_PER_H + state.leak_rate_l_per_h


__all__ = [
    "OilState",
    "consumption_rate_l_per_h",
    "oil_pressure",
    "oil_temperature",
]
