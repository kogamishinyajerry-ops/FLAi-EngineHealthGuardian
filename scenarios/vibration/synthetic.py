"""Synthetic data generator for the vibration vertical slice.

Same 3-branch fleet shape as the EGT slice (healthy / degrading / low-data) so the
two scenarios are directly comparable, but the signal is vibration (ips) and the
baseline keys on rotor speed. Seeded for reproducibility.

- ``ESN_VIB_HEALTHY``  (config LEAP1C-VIB-A) — vibration ~ baseline + noise -> NOMINAL
- ``ESN_VIB_DEGRADE``  (config LEAP1C-VIB-A) — rising vibration ~0.08 ips/flight -> ADVISORY
- ``ESN_VIB_LOWDATA``  (config LEAP1C-VIB-B) — few flights, solo cohort -> ABSTAIN
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from ehm.core.schemas import EngineSnapshot, FlightPhase
from scenarios.vibration.features import baseline

NUM_FLIGHTS = 25
LOWDATA_FLIGHTS = 4
DEGRADE_RATE = 0.08  # ips added to residual per flight


def generate(seed: int = 42) -> list[EngineSnapshot]:
    """Return a reproducible synthetic fleet of cruise-phase vibration snapshots."""
    rnd = random.Random(seed)
    snapshots: list[EngineSnapshot] = []
    start = datetime(2026, 8, 1, tzinfo=UTC)

    for flight in range(NUM_FLIGHTS):
        ts = start + timedelta(hours=flight * 6)
        n1 = rnd.uniform(87.0, 90.0)
        n2 = rnd.uniform(93.0, 95.0)
        base = baseline(FlightPhase.CRUISE, n1, n2)
        snapshots.append(
            _snap(
                "ESN_VIB_HEALTHY",
                "LEAP1C-VIB-A",
                flight,
                ts,
                n1,
                n2,
                base + rnd.uniform(-0.08, 0.08),
                rnd,
            )
        )
        snapshots.append(
            _snap(
                "ESN_VIB_DEGRADE",
                "LEAP1C-VIB-A",
                flight,
                ts,
                n1,
                n2,
                base + DEGRADE_RATE * flight + rnd.uniform(-0.08, 0.08),
                rnd,
            )
        )

    for flight in range(LOWDATA_FLIGHTS):
        ts = start + timedelta(hours=flight * 6)
        n1 = rnd.uniform(87.0, 90.0)
        n2 = rnd.uniform(93.0, 95.0)
        base = baseline(FlightPhase.CRUISE, n1, n2)
        snapshots.append(
            _snap(
                "ESN_VIB_LOWDATA",
                "LEAP1C-VIB-B",
                flight,
                ts,
                n1,
                n2,
                base + rnd.uniform(-0.08, 0.08),
                rnd,
            )
        )

    return snapshots


def _snap(
    esn: str,
    config: str,
    flight: int,
    ts: datetime,
    n1: float,
    n2: float,
    vibration: float,
    rnd: random.Random,
) -> EngineSnapshot:
    return EngineSnapshot(
        esn=esn,
        flight_id=f"V{flight:04d}",
        phase=FlightPhase.CRUISE,
        timestamp=ts,
        oat_c=rnd.uniform(-15.0, 30.0),
        n1_pct=n1,
        n2_pct=n2,
        egt_c=rnd.uniform(500.0, 650.0),
        fuel_flow_kg_h=rnd.uniform(2400.0, 2700.0),
        vibration_ips=vibration,
        config_tag=config,
    )
