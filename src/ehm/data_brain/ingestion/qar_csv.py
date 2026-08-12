"""QAR-CSV adapter — decode a flight-data CSV export into EngineSnapshots.

A QAR export is one engine's time-series for one flight: parameter-per-column,
one row per sampled time. Engine/flight identity is file-level metadata (the
operator knows which engine/flight a file belongs to), so it is passed to the
constructor; the per-row columns carry the parameters and (optionally) altitude /
airspeed for phase detection.

Decoding is deterministic stdlib ``csv`` row-by-row. Units are converted via the
``ParameterMap``; phase is derived by a fresh ``PhaseTracker`` per file.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

from ehm.core.schemas import EngineSnapshot, FlightPhase
from ehm.data_brain.ingestion.base import IngestionAdapter
from ehm.data_brain.ingestion.mapping import ParameterMap, convert, parse_time, to_float
from ehm.data_brain.ingestion.phase import PhaseTracker


class QarCsvAdapter:
    """Ingest a decoded QAR CSV export. Satisfies ``IngestionAdapter``."""

    name = "qar_csv"

    def __init__(
        self,
        path: str | Path,
        mapping: ParameterMap,
        *,
        esn: str,
        flight_id: str,
        config_tag: str = "default",
    ) -> None:
        self.path = Path(path)
        self.mapping = mapping
        self._esn = esn
        self._flight_id = flight_id
        self._config_tag = config_tag

    def iter_snapshots(self) -> Iterator[EngineSnapshot]:
        """Yield decoded snapshots in time order (rows are assumed already ordered)."""
        tracker = PhaseTracker()
        with self.path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                yield self._row_to_snapshot(row, tracker)

    def _row_to_snapshot(self, row: dict[str, str], tracker: PhaseTracker) -> EngineSnapshot:
        mapping = self.mapping
        timestamp = parse_time(row.get(mapping.time_col, ""), mapping.time_format)

        phase = self._phase(row, tracker)
        fields: dict[str, object] = {
            "esn": self._esn,
            "flight_id": self._flight_id,
            "config_tag": self._config_tag,
            "phase": phase,
            "timestamp": timestamp,
        }
        for src, spec in mapping.params.items():
            raw = to_float(row.get(src))
            if raw is not None:
                fields[spec.canonical_attr] = convert(raw, spec.from_unit)
        return EngineSnapshot.model_validate(fields)

    def _phase(self, row: dict[str, str], tracker: PhaseTracker) -> FlightPhase:
        mapping = self.mapping
        if mapping.phase_col and row.get(mapping.phase_col):
            return FlightPhase(row[mapping.phase_col].strip().lower())
        altitude = to_float(row.get(mapping.altitude_col)) if mapping.altitude_col else None
        airspeed = to_float(row.get(mapping.airspeed_col)) if mapping.airspeed_col else None
        return tracker.update(altitude, airspeed)


__all__ = ["QarCsvAdapter", "IngestionAdapter"]
