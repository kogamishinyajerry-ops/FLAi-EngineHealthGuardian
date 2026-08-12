"""Synthetic data for the oil scenario — leak detection via consumption rate.

Three engines (same 3-branch shape for comparability):

- ``ESN_OIL_HEALTHY`` (config OIL-A) — steady low consumption ~0.10 L/flight -> NOMINAL
- ``ESN_OIL_LEAK``    (config OIL-A) — consumption rising ~0.06 L/flight/flight -> ADVISORY
- ``ESN_OIL_LOWDATA`` (config OIL-B) — few flights, solo cohort -> ABSTAIN

Tank level is driven by cumulative consumption; the pipeline derives the rate back.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from ehm.core.schemas import EngineSnapshot, FlightPhase

NUM_FLIGHTS = 25
LOWDATA_FLIGHTS = 4
BASE_CONSUMPTION = 0.10  # L/flight (healthy steady burn)
LEAK_RATE = 0.06  # L/flight added per flight (leak growth)
TANK_START_L = 12.0


def generate(seed: int = 42) -> list[EngineSnapshot]:
    rnd = random.Random(seed)
    snapshots: list[EngineSnapshot] = []
    start = datetime(2026, 8, 1, tzinfo=UTC)

    def add(esn: str, config: str, n: int, leak: bool) -> None:
        level = TANK_START_L
        for f in range(n):
            burn = BASE_CONSUMPTION + (LEAK_RATE * f if leak else 0.0) + rnd.uniform(-0.01, 0.01)
            level -= burn
            snapshots.append(_snap(esn, config, f, start + timedelta(hours=f * 6), level, rnd))

    add("ESN_OIL_HEALTHY", "OIL-A", NUM_FLIGHTS, leak=False)
    add("ESN_OIL_LEAK", "OIL-A", NUM_FLIGHTS, leak=True)
    add("ESN_OIL_LOWDATA", "OIL-B", LOWDATA_FLIGHTS, leak=False)
    return snapshots


def _snap(
    esn: str, config: str, flight: int, ts: datetime, level: float, rnd: random.Random
) -> EngineSnapshot:
    return EngineSnapshot(
        esn=esn,
        flight_id=f"O{flight:04d}",
        phase=FlightPhase.CRUISE,
        timestamp=ts,
        oat_c=rnd.uniform(-15.0, 30.0),
        n1_pct=rnd.uniform(87.0, 90.0),
        n2_pct=rnd.uniform(93.0, 95.0),
        egt_c=rnd.uniform(500.0, 650.0),
        fuel_flow_kg_h=rnd.uniform(2400.0, 2700.0),
        oil_temp_c=rnd.uniform(90.0, 120.0),
        oil_pressure_kpa=rnd.uniform(380.0, 450.0),
        oil_level_l=round(level, 3),
        config_tag=config,
    )
