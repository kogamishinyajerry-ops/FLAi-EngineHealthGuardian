"""Ground-truth manifest — the honest label layer for synthetic data.

Every flight gets one ``FlightTruth`` record recording *what was injected*
(degradation kind/magnitude, active sensor faults, active confounders) and the
derived ``truth_label``. This is the authoritative label — never model output.
The manifest is written alongside the data, tagged ``source=synthetic``, and must
never be mixed with real-data labels (CODEBUDDY §5).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from ehm.data_brain.synth.config import TruthLabel

_EPS = 1e-9


@dataclass(frozen=True)
class FlightTruth:
    """One flight's ground-truth record (what the factory injected)."""

    esn: str
    flight_id: str
    cycle: int
    timestamp: str  # ISO-8601 UTC
    n_samples: int
    phase_counts: dict[str, int]
    degradation_kind: str
    degradation_magnitude: float
    degradation_active: bool
    sensor_faults_active: list[str]
    confounders_active: list[str]
    truth_label: str
    source: str = "synthetic"


def classify(degradation_active: bool, sensor_faults: Sequence[str]) -> TruthLabel:
    """Derive the truth label: engine fault > sensor fault > no fault.

    If both an engine fault and a sensor fault are active, the engine fault wins
    (the sensor fault is secondary noise on a genuinely faulty engine).
    """
    if degradation_active:
        return TruthLabel.TRUE_FAULT
    if sensor_faults:
        return TruthLabel.SENSOR_FAULT
    return TruthLabel.NO_FAULT


def write_manifest(records: list[FlightTruth], path: Path) -> None:
    """Write the manifest as JSONL (one record per line), in order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for rec in records:
            handle.write(json.dumps(asdict(rec), sort_keys=True) + "\n")


def magnitude_nonzero(magnitude: float) -> bool:
    """Whether a degradation magnitude counts as active for labelling."""
    return magnitude > _EPS


__all__ = ["FlightTruth", "classify", "magnitude_nonzero", "write_manifest"]
