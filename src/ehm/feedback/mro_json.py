"""MRO-JSON adapter — decode work-order / shop findings into ``MroFinding`` records.

JSONL on disk (one finding per line), mirroring the audit / labels / ACARS
convention. Field names are conventional (``esn`` / ``date`` / ``type`` / ``text``
/ ``disposition`` / ``component``); a real deployment with divergent column names
would add a field map (the natural analog of ``ParameterMap`` — deferred here).

This is a *label-side* source: it yields findings, not ``EngineSnapshot``, so it
intentionally does NOT implement ``IngestionAdapter``.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from ehm.core.timeutil import parse_time
from ehm.feedback.findings import Disposition, FindingType, MroFinding


class MroJsonAdapter:
    """Ingest an MRO findings JSONL file."""

    name = "mro_json"

    def __init__(self, path: str | Path, *, source: str = "mro") -> None:
        self.path = Path(path)
        self._source = source

    def iter_findings(self) -> Iterator[MroFinding]:
        """Yield one MroFinding per non-blank JSON line, in file order."""
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                yield self._line_to_finding(json.loads(line))

    def _line_to_finding(self, obj: dict[str, object]) -> MroFinding:
        disposition_raw = obj.get("disposition")
        return MroFinding(
            esn=str(obj["esn"]),
            finding_date=parse_time(obj["date"]),
            finding_type=FindingType(str(obj["type"])),
            finding_text=str(obj.get("text", "")),
            component=_opt_str(obj.get("component")),
            disposition=Disposition(str(disposition_raw)) if disposition_raw is not None else None,
            source=self._source,
        )


def _opt_str(value: object | None) -> str | None:
    return str(value) if value is not None else None


__all__ = ["MroJsonAdapter"]
