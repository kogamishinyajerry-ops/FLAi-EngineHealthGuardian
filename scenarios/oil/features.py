"""Oil feature engineering — consumption rate from tank-level deltas (scenario-local).

Unlike EGT/vibration (a residual vs a physics baseline per snapshot), oil
**consumption** is a *rate* derived from consecutive tank-level readings
(``level[i-1] - level[i]``). That breaks the per-snapshot ``PeerGroup`` pattern, so
this scenario compares an engine's mean rate against the fleet instead. Rising
consumption rate => potential leak / scavenge issue.
"""

from __future__ import annotations

from collections.abc import Iterable

from ehm.core.schemas import EngineSnapshot


def consumption_series(snapshots: Iterable[EngineSnapshot]) -> list[float]:
    """Per-flight oil consumption (L) from time-ordered tank levels.

    Caller must pass snapshots already sorted by timestamp. Returns one value
    per consecutive level pair (so len == n_levels - 1). Positive = consumed.
    """
    levels = [s.oil_level_l for s in snapshots if s.oil_level_l is not None]
    return [levels[i - 1] - levels[i] for i in range(1, len(levels))]


def mean_rate(series: list[float]) -> float | None:
    """Mean consumption rate (L/flight); None when not computable."""
    if not series:
        return None
    return sum(series) / len(series)
