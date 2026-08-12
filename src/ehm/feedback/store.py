"""LabelStore — append-only JSONL of Adjudication events.

Mirrors ``safety_brain.audit.AuditLog``: never mutates a logged Evidence, only
appends verdicts keyed by ``Evidence.id``. The "effective" verdict for an Evidence
is the latest Adjudication by ``adjudicated_at`` (ties broken by ``id``); the
``supersedes`` field is kept for provenance/history. A later shop-visit result can
therefore refine an earlier field call without erasing the original.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

from ehm.feedback.labels import Adjudication


class LabelStore:
    """Append-only JSONL store of Adjudication events."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(self, adjudication: Adjudication) -> None:
        """Append one Adjudication as a JSON line."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(adjudication.model_dump_json() + "\n")

    def all(self) -> Iterator[Adjudication]:
        """Replay all recorded adjudications in write order."""
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    yield Adjudication.model_validate_json(line)

    def for_evidence(self, evidence_id: UUID) -> list[Adjudication]:
        """All adjudication events for one Evidence, in write order."""
        return [a for a in self.all() if a.evidence_id == evidence_id]

    def latest(self, evidence_id: UUID) -> Adjudication | None:
        """Effective verdict: the most recent adjudication for this Evidence."""
        events = self.for_evidence(evidence_id)
        if not events:
            return None
        return max(events, key=lambda a: (a.adjudicated_at, a.id))

    def adjudicated_ids(self) -> set[UUID]:
        """Set of Evidence ids that have at least one adjudication."""
        return {a.evidence_id for a in self.all()}

    def clear(self) -> None:
        """Remove the store file (tests / re-runs only)."""
        if self.path.exists():
            self.path.unlink()

    def by_evidence(self) -> dict[UUID, list[Adjudication]]:
        """Group all events by Evidence id (convenience for batch joins)."""
        grouped: dict[UUID, list[Adjudication]] = defaultdict(list)
        for adjudication in self.all():
            grouped[adjudication.evidence_id].append(adjudication)
        return grouped
