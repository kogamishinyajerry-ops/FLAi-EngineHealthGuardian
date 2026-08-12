"""IngestionAdapter protocol — the seam between real data sources and the platform.

Real adapters (ACARS real-time, QAR batch, MRO work orders) are deferred; only the
protocol and a synthetic adapter exist in v0. This seam is what lets engineering
proceed before COMAC data access (report assumption A1) is granted: every brain
depends on ``EngineSnapshot`` objects, not on any specific source.

Cardinal rule: **decoding is never done by an LLM**. Adapters own the deterministic
translation from their native format (ARINC frames, ACARS messages, QAR binary)
into the canonical model.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from ehm.core.schemas import EngineSnapshot


@runtime_checkable
class IngestionAdapter(Protocol):
    """Yields ``EngineSnapshot`` objects already decoded into the canonical model."""

    name: str

    def iter_snapshots(self) -> Iterator[EngineSnapshot]:
        """Iterate decoded snapshots in source order (real-time or batch)."""
        ...
