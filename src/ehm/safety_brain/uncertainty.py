"""Uncertainty — turn pipeline signals into the 4-dimension Confidence.

The mapping below is a v0 heuristic, not a calibration. Real calibration
(conformal prediction, ensembles, Bayesian/quantile intervals — the report's
calibration-first stance) is layered in later; the 4-dimension shape is stable.
"""

from __future__ import annotations

from ehm.core.evidence import Confidence


def clamp(value: float) -> float:
    """Clamp a value into the [0.0, 1.0] confidence range."""
    return max(0.0, min(1.0, value))


def from_signals(
    *,
    data_completeness: float,
    peer_size: int,
    rule_applies: bool,
    model_score: float | None,
) -> Confidence:
    """Build a Confidence from raw pipeline signals.

    - ``data``: driven by how completely the engine was sampled.
    - ``knowledge``: rules are expert heuristics in v0 (not OEM-derived); penalized
      when the peer group is too small to trust the comparison.
    - ``applicability``: does the rule apply to this ESN/config? Penalized for tiny peers.
    - ``model``: a detector score, if a detector fired.
    """
    data_conf = clamp(data_completeness)
    knowledge_conf = 0.7
    applicability = 1.0 if rule_applies else 0.2
    if peer_size < 5:
        knowledge_conf *= 0.5
        applicability *= 0.7
    return Confidence(
        data=data_conf,
        model=model_score,
        knowledge=knowledge_conf,
        applicability=applicability,
    )
