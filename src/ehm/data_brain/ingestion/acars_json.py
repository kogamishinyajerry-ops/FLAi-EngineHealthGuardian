"""ACARS-JSON adapter — decode ACARS engine-report messages into EngineSnapshots.

ACARS messages are discrete real-time-style reports: each JSON object is one
already-aggregated observation carrying identity (esn/flight) and (often) the
flight phase inline. One message -> one snapshot. Identity defaults can be passed
to the constructor for feeds that omit them per-message.

JSONL (one JSON object per line) is the expected on-disk shape; mirroring the
audit log. Decoding is deterministic (stdlib ``json``), units via ``ParameterMap``.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from ehm.core.schemas import EngineSnapshot, FlightPhase
from ehm.data_brain.ingestion.base import IngestionAdapter
from ehm.data_brain.ingestion.mapping import ParameterMap, convert, parse_time, to_float


class AcarsJsonAdapter:
    """Ingest a JSONL file of ACARS engine reports. Satisfies ``IngestionAdapter``."""

    name = "acars_json"

    def __init__(
        self,
        path: str | Path,
        mapping: ParameterMap,
        *,
        esn: str = "UNKNOWN",
        flight_id: str = "UNKNOWN",
        config_tag: str = "default",
    ) -> None:
        self.path = Path(path)
        self.mapping = mapping
        self._default_esn = esn
        self._default_flight_id = flight_id
        self._default_config_tag = config_tag

    def iter_snapshots(self) -> Iterator[EngineSnapshot]:
        """Yield one snapshot per non-blank JSON line, in file order."""
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                yield self._msg_to_snapshot(json.loads(line))

    def _msg_to_snapshot(self, msg: dict[str, object]) -> EngineSnapshot:
        mapping = self.mapping
        timestamp = parse_time(msg.get(mapping.time_col, ""), mapping.time_format)

        phase = self._phase(msg)
        fields: dict[str, object] = {
            "esn": str(msg.get(mapping.esn_col, self._default_esn))
            if mapping.esn_col
            else self._default_esn,
            "flight_id": (
                str(msg.get(mapping.flight_id_col, self._default_flight_id))
                if mapping.flight_id_col
                else self._default_flight_id
            ),
            "config_tag": (
                str(msg.get(mapping.config_col, self._default_config_tag))
                if mapping.config_col
                else self._default_config_tag
            ),
            "phase": phase,
            "timestamp": timestamp,
        }
        for src, spec in mapping.params.items():
            raw = to_float(msg.get(src))
            if raw is not None:
                fields[spec.canonical_attr] = convert(raw, spec.from_unit)
        return EngineSnapshot.model_validate(fields)

    def _phase(self, msg: dict[str, object]) -> FlightPhase:
        if self.mapping.phase_col and msg.get(self.mapping.phase_col):
            return FlightPhase(str(msg[self.mapping.phase_col]).strip().lower())
        return FlightPhase.CRUISE  # ACARS reports often arrive phase-tagged; fallback otherwise


__all__ = ["AcarsJsonAdapter", "IngestionAdapter"]
