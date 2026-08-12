"""Canonical Data Model v0 — the single normalized shape all brains speak in.

Units are QUDT-aware in field names/comments. v0 does NOT bind the full QUDT
ontology (deferred); the field-name + doc convention is enough to avoid the
°C/K, psi/kPa, lb/h/kg/h semantic errors the report calls out.

Every record carries enough context (esn, flight_id, phase, timestamp, oat,
thrust proxy, config_tag) to be normalized downstream without re-reading raw.
``config_tag`` enables time-aware configuration: a conclusion must be answerable
for "at this flight, what config / SB status / decode version applied?".
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FlightPhase(StrEnum):
    """Coarse flight phase. Real QAR needs phase detection from alt/speed (deferred)."""

    GROUND = "ground"
    TAKEOFF = "takeoff"
    CLIMB = "climb"
    CRUISE = "cruise"
    DESCENT = "descent"
    APPROACH = "approach"


class EngineSnapshot(BaseModel):
    """One normalized engine observation at a point in a flight phase.

    Temperatures in °C, rotational speeds in % (referenced), fuel flow in kg/h,
    vibration in ips, unless the field name says otherwise. ``None`` means the
    parameter was absent or marked invalid at the source — downstream DQ must
    account for it; it is never silently coerced.
    """

    model_config = ConfigDict(extra="ignore")

    esn: str = Field(description="Engine Serial Number — primary identity")
    flight_id: str
    phase: FlightPhase
    timestamp: datetime
    oat_c: float | None = Field(default=None, description="Outside Air Temperature, °C")
    n1_pct: float | None = Field(default=None, description="Low-pressure rotor speed, %")
    n2_pct: float | None = Field(default=None, description="High-pressure rotor speed, %")
    egt_c: float | None = Field(default=None, description="Exhaust Gas Temperature, °C")
    fuel_flow_kg_h: float | None = Field(default=None, description="Fuel flow, kg/h")
    thrust_ref_pct: float | None = Field(default=None, description="Thrust reference setting, %")
    vibration_ips: float | None = Field(default=None, description="Engine vibration, ips")
    oil_temp_c: float | None = Field(default=None, description="Oil temperature, °C")
    oil_pressure_kpa: float | None = Field(default=None, description="Oil pressure, kPa")
    oil_level_l: float | None = Field(
        default=None, description="Oil tank level, L (for consumption rate)"
    )
    config_tag: str = Field(
        default="default",
        description="Configuration id valid at this timestamp (time-aware config)",
    )
