"""Synthetic adapter — serves pre-generated ``EngineSnapshot`` objects.

Used by the EGT-margin demo and by tests so the whole pipeline runs offline with
no real data. The generator itself lives in ``scenarios.egt_margin.synthetic``;
this adapter just wraps an iterable in the ``IngestionAdapter`` protocol.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from ehm.core.schemas import EngineSnapshot
from ehm.data_brain.ingestion.base import IngestionAdapter


class SyntheticAdapter:
    """In-memory adapter over an iterable of snapshots."""

    name = "synthetic"

    def __init__(self, snapshots: Iterable[EngineSnapshot]) -> None:
        self._snapshots = list(snapshots)

    def iter_snapshots(self) -> Iterator[EngineSnapshot]:
        """Yield the wrapped snapshots in their original order."""
        yield from self._snapshots


__all__ = ["SyntheticAdapter", "IngestionAdapter"]
