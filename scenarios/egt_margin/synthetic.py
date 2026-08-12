"""Synthetic data generator for the EGT-margin vertical slice.

Builds a small fleet designed to exercise all three Evidence branches:

- ``ESN_HEALTHY_01`` (config LEAP1C-A)  — healthy noise around baseline  -> NOMINAL
- ``ESN_DEGRADE_02`` (config LEAP1C-A)  — rising EGT residual ~2.5 °C/flight -> ADVISORY
- ``ESN_LOWDATA_03`` (config LEAP1C-B)  — only a few flights, solo cohort -> ABSTAIN

No real LEAP-1C values are used; magnitudes are illustrative. The generator is
seeded for reproducibility — every test and demo run must be bit-for-bit repeatable.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from ehm.core.schemas import EngineSnapshot, FlightPhase
from scenarios.egt_margin.features import baseline

NUM_FLIGHTS = 25
#: The low-data engine only has this many flights (small solo cohort -> ABSTAIN).
LOWDATA_FLIGHTS = 4
DEGRADE_RATE = 2.5  # °C added to residual per flight (above threshold of 2.0)


def generate(seed: int = 42) -> list[EngineSnapshot]:
    """Return a reproducible synthetic fleet of cruise-phase snapshots."""
    rnd = random.Random(seed)
    snapshots: list[EngineSnapshot] = []
    start = datetime(2026, 8, 1, tzinfo=UTC)

    for flight in range(NUM_FLIGHTS):
        ts = start + timedelta(hours=flight * 6)
        oat = rnd.uniform(-20.0, 35.0)
        thrust = rnd.uniform(80.0, 92.0)
        base = baseline(FlightPhase.CRUISE, thrust, oat)
        snapshots.append(
            _snap(
                "ESN_HEALTHY_01",
                "LEAP1C-A",
                flight,
                ts,
                oat,
                thrust,
                base + rnd.uniform(-6, 6),
                rnd,
            )
        )
        snapshots.append(
            _snap(
                "ESN_DEGRADE_02",
                "LEAP1C-A",
                flight,
                ts,
                oat,
                thrust,
                base + DEGRADE_RATE * flight + rnd.uniform(-6, 6),
                rnd,
            )
        )

    for flight in range(LOWDATA_FLIGHTS):
        ts = start + timedelta(hours=flight * 6)
        oat = rnd.uniform(-20.0, 35.0)
        thrust = rnd.uniform(80.0, 92.0)
        base = baseline(FlightPhase.CRUISE, thrust, oat)
        snapshots.append(
            _snap(
                "ESN_LOWDATA_03",
                "LEAP1C-B",
                flight,
                ts,
                oat,
                thrust,
                base + rnd.uniform(-6, 6),
                rnd,
            )
        )

    return snapshots


def _snap(
    esn: str,
    config: str,
    flight: int,
    ts: datetime,
    oat: float,
    thrust: float,
    egt: float,
    rnd: random.Random,
) -> EngineSnapshot:
    return EngineSnapshot(
        esn=esn,
        flight_id=f"F{flight:04d}",
        phase=FlightPhase.CRUISE,
        timestamp=ts,
        oat_c=oat,
        n1_pct=rnd.uniform(88.0, 95.0),
        n2_pct=rnd.uniform(93.0, 98.0),
        egt_c=egt,
        fuel_flow_kg_h=rnd.uniform(2400.0, 2700.0),
        thrust_ref_pct=thrust,
        config_tag=config,
    )
