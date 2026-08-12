"""Peer-group normalization — compare one engine against the same-config fleet.

Keys on ``(phase, config_tag)``: a comparison is only meaningful between engines
of the same configuration (report: ``validForConfiguration``). A peer group that
is too small drives down Knowledge/Applicability confidence (see ``safety_brain``),
which is one route to ABSTAIN.

Generic over the residual source: the caller supplies the ``residual_fn`` (EGT
margin, vibration, oil, ...). Previously this class imported the EGT residual
directly; making it a parameter is what lets a new scenario reuse it without
touching the library (see ADR-0007).
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Callable, Iterable

from ehm.core.schemas import EngineSnapshot, FlightPhase

_Key = tuple[FlightPhase, str]


class PeerGroup:
    """Collects residuals over a population to form per-key baselines."""

    def __init__(self, residual_fn: Callable[[EngineSnapshot], float | None]) -> None:
        self._residual_fn = residual_fn
        self._by_key: dict[_Key, list[float]] = defaultdict(list)

    @staticmethod
    def _key(snapshot: EngineSnapshot) -> _Key:
        return (snapshot.phase, snapshot.config_tag)

    def add_population(self, snapshots: Iterable[EngineSnapshot]) -> None:
        """Fold a population of snapshots into the per-key residual store."""
        for snap in snapshots:
            value = self._residual_fn(snap)
            if value is not None:
                self._by_key[self._key(snap)].append(value)

    def zscore(self, snapshot: EngineSnapshot) -> float | None:
        """Standardized residual vs peers; ``None`` when not computable."""
        value = self._residual_fn(snapshot)
        if value is None:
            return None
        population = self._by_key.get(self._key(snapshot), [])
        if len(population) < 2:
            return None
        mean = statistics.fmean(population)
        stdev = statistics.pstdev(population)
        if stdev == 0:
            return 0.0
        return (value - mean) / stdev

    def size(self, snapshot: EngineSnapshot) -> int:
        """Number of peer residuals available for this snapshot's key."""
        return len(self._by_key.get(self._key(snapshot), []))
