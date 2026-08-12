"""Parameter mapping + deterministic unit conversion for real-format adapters.

This is the seed of the report's "canonical parameter dictionary": a source's
column/message names are mapped to canonical ``EngineSnapshot`` attributes, with
the source unit declared so values are converted deterministically (never by an
LLM). Adding a new airline/source is a config change (a new ``ParameterMap``),
not code.

Decoding itself uses the stdlib (``csv`` / ``json``) row-by-row; Polars is
reserved for bulk feature/analytics paths, not line-oriented model construction.
See ADR-0005.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ehm.core.timeutil import parse_time


@dataclass(frozen=True)
class ParamSpec:
    """How one source field maps to one canonical attribute.

    ``from_unit`` declares the unit the source uses; ``None`` means the value is
    already in the canonical unit and is passed through unchanged.
    """

    canonical_attr: str
    from_unit: str | None = None


def _identity(value: float) -> float:
    return value


#: source unit -> (canonical unit, conversion fn). Extend here to support more.
_UNIT_TABLE: dict[str, tuple[str, Callable[[float], float]]] = {
    "degC": ("degC", _identity),
    "K": ("degC", lambda v: v - 273.15),
    "degF": ("degC", lambda v: (v - 32.0) * 5.0 / 9.0),
    "kPa": ("kPa", _identity),
    "psi": ("kPa", lambda v: v * 6.894757),
    "hPa": ("kPa", lambda v: v / 10.0),
    "bar": ("kPa", lambda v: v * 100.0),
    "kg_h": ("kg_h", _identity),
    "lb_h": ("kg_h", lambda v: v * 0.45359237),
    "%": ("%", _identity),
    "ips": ("ips", _identity),
    "ft": ("ft", _identity),
    "kt": ("kt", _identity),
}

#: canonical attribute -> its canonical unit (used by ``ParameterMap.validate``).
_CANONICAL_UNIT: dict[str, str] = {
    "oat_c": "degC",
    "egt_c": "degC",
    "n1_pct": "%",
    "n2_pct": "%",
    "fuel_flow_kg_h": "kg_h",
    "thrust_ref_pct": "%",
    "vibration_ips": "ips",
}


def convert(value: float, from_unit: str | None) -> float:
    """Convert ``value`` from ``from_unit`` to its canonical unit.

    Raises ``ValueError`` on an unknown source unit — fail loud rather than
    silently producing wrong-unit data (the °C/K, psi/kPa, lb/h/kg/h class of
    error the report calls out).
    """
    if from_unit is None:
        return value
    if from_unit not in _UNIT_TABLE:
        raise ValueError(f"unknown source unit: {from_unit!r}")
    _canonical, fn = _UNIT_TABLE[from_unit]
    return fn(value)


def to_float(value: object | None) -> float | None:
    """Coerce a raw cell/message value to float; empty/missing -> None."""
    if value is None:
        return None
    if isinstance(value, bool):  # noqa: FBT001 - guard before int check
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip()
    if text == "":
        return None
    return float(text)


@dataclass(frozen=True)
class ParameterMap:
    """A source-to-canonical mapping for one data feed.

    ``time_col`` is mandatory. Altitude/airspeed cols feed phase detection
    (``phase.PhaseTracker``); ``phase_col`` overrides detection when the source
    already carries a phase. Inline metadata cols (``esn_col`` etc.) are used by
    message-style sources (e.g. ACARS) where identity lives in each message.
    """

    params: dict[str, ParamSpec]
    time_col: str
    time_format: str = "iso"
    altitude_col: str | None = None
    airspeed_col: str | None = None
    phase_col: str | None = None
    esn_col: str | None = None
    flight_id_col: str | None = None
    config_col: str | None = None

    def validate(self) -> None:
        """Fail loud if a ``from_unit`` does not convert to its attribute's canonical unit."""
        for src, spec in self.params.items():
            if spec.from_unit is None or spec.canonical_attr not in _CANONICAL_UNIT:
                continue
            expected = _CANONICAL_UNIT[spec.canonical_attr]
            actual = _UNIT_TABLE.get(spec.from_unit, (spec.from_unit, _identity))[0]
            if actual != expected:
                raise ValueError(
                    f"column {src!r}: unit {spec.from_unit!r} converts to {actual!r}, "
                    f"but attribute {spec.canonical_attr!r} expects {expected!r}"
                )


# --- Example maps matching the committed fixtures (self-documenting the format) ---
EXAMPLE_QAR_MAP: ParameterMap = ParameterMap(
    params={
        "SAT_C": ParamSpec("oat_c", "degC"),
        "N1": ParamSpec("n1_pct", "%"),
        "N2": ParamSpec("n2_pct", "%"),
        "EGT_F": ParamSpec("egt_c", "degF"),
        "FF_LBH": ParamSpec("fuel_flow_kg_h", "lb_h"),
        "VIB": ParamSpec("vibration_ips", "ips"),
        "THR": ParamSpec("thrust_ref_pct", "%"),
    },
    time_col="time",
    altitude_col="ALT_FT",
    airspeed_col="SPD_KT",
)

EXAMPLE_ACARS_MAP: ParameterMap = ParameterMap(
    params={
        "OAT": ParamSpec("oat_c", "degC"),
        "N1": ParamSpec("n1_pct", "%"),
        "N2": ParamSpec("n2_pct", "%"),
        "EGT": ParamSpec("egt_c", "degC"),
        "FF": ParamSpec("fuel_flow_kg_h", "kg_h"),
    },
    time_col="ts",
    esn_col="esn",
    flight_id_col="flight",
    phase_col="phase",
)


__all__ = [
    "ParamSpec",
    "ParameterMap",
    "EXAMPLE_ACARS_MAP",
    "EXAMPLE_QAR_MAP",
    "convert",
    "parse_time",
    "to_float",
]
