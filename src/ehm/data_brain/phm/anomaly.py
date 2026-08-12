"""Rule-based anomaly detection for the EGT slice (deterministic, no ML yet).

Real anomaly detection (robust statistics, isolation forest, autoencoder, a
physics-residual learner) is P0 work layered in after the scaffold. The contract
here is ``RuleResult``; richer detectors can return the same shape.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleResult:
    """Outcome of a deterministic rule on one engine's residual series."""

    triggered: bool
    score: float
    detail: str


def residual_trend(
    residuals: list[float], *, window: int = 5, slope_threshold: float = 2.0
) -> RuleResult:
    """Flag when the trailing-window slope of residuals exceeds a threshold.

    Generic over the residual source (EGT margin, vibration, oil, ...). The rule
    was originally named ``egt_residual_trend``; renaming reflects that the logic
    is parameter-agnostic — see ADR-0007. ``residuals`` are ordered oldest→newest
    per ESN/phase; the slope is a simple least-squares estimate over the trailing
    window (deliberately conservative, explainable — no black-box model).
    """
    if len(residuals) < window:
        return RuleResult(False, 0.0, f"insufficient samples ({len(residuals)}<{window})")
    series = residuals[-window:]
    n = len(series)
    xs = list(range(n))
    x_bar = sum(xs) / n
    y_bar = sum(series) / n
    num = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, series, strict=True))
    den = sum((x - x_bar) ** 2 for x in xs)
    slope = num / den if den else 0.0
    triggered = slope >= slope_threshold
    return RuleResult(
        # Unit-agnostic: the caller knows the residual's unit (°C/flight, ips/flight, ...)
        # and renders it in the observation text. Hard-coding a unit here was an EGT leak.
        triggered,
        slope,
        f"trailing-slope={slope:.3f} over window={window}",
    )
