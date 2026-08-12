"""Feedback metrics — turn the gold-label view into statistics for the model layer.

These map directly to the report's validation KPIs:

- ``coverage``        — fraction of Evidence adjudicated (label factory throughput)
- ``precision_proxy`` — of ADVISORY alerts, the fraction that were "real"
                        (TRUE_FAULT / CONDITIONAL_ANOMALY); the report's
                        "actionable alert precision"
- ``confusion``       — system status (NOMINAL/ADVISORY/ABSTAIN) x human truth

INCONCLUSIVE verdicts are excluded from the precision denominator (neither right
nor wrong). Ratios are reported alongside raw counts so a 1/1 = 100% is never
mistaken for significance.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ehm.core.evidence import EvidenceStatus
from ehm.feedback.gold import GoldLabel
from ehm.feedback.labels import EXCLUDED_FROM_PRECISION, REAL_OUTCOMES

_UNADJUDICATED = "unadjudicated"


@dataclass(frozen=True)
class Metrics:
    """Aggregate feedback statistics over a gold-label set."""

    total: int
    adjudicated: int
    coverage: float
    advisory_total: int
    advisory_evaluable: int
    advisory_precision_proxy: float | None
    confusion: dict[tuple[str, str], int] = field(default_factory=dict)

    def render(self) -> str:
        """Human-readable summary for the CLI / workbench."""
        precision = (
            f"{self.advisory_precision_proxy:.0%}"
            if self.advisory_precision_proxy is not None
            else "n/a (no evaluable ADVISORY)"
        )
        lines = [
            f"coverage              : {self.adjudicated}/{self.total} = {self.coverage:.0%}",
            f"advisory total        : {self.advisory_total}",
            f"advisory evaluable    : {self.advisory_evaluable}  (adjudicated, excl. INCONCLUSIVE)",
            f"advisory precision    : {precision}  (real / evaluable)",
            "confusion (system status x human truth):",
        ]
        for (status, outcome), count in sorted(self.confusion.items()):
            lines.append(f"  {status:<10} x {outcome:<20} : {count}")
        return "\n".join(lines)


def compute(gold: list[GoldLabel]) -> Metrics:
    """Compute feedback metrics over a gold-label set."""
    total = len(gold)
    adjudicated = sum(1 for row in gold if row.is_adjudicated)
    coverage = adjudicated / total if total else 0.0

    confusion: Counter[tuple[str, str]] = Counter()
    advisory_total = 0
    advisory_real = 0
    advisory_evaluable = 0

    for row in gold:
        status = row.evidence.status
        status_key = status.value
        is_advisory = status is EvidenceStatus.ADVISORY
        if is_advisory:
            advisory_total += 1

        if row.adjudication is None:
            confusion[(status_key, _UNADJUDICATED)] += 1
            continue

        outcome = row.adjudication.outcome
        confusion[(status_key, outcome.value)] += 1
        if is_advisory and outcome not in EXCLUDED_FROM_PRECISION:
            advisory_evaluable += 1
            if outcome in REAL_OUTCOMES:
                advisory_real += 1

    precision: float | None = advisory_real / advisory_evaluable if advisory_evaluable else None
    return Metrics(
        total=total,
        adjudicated=adjudicated,
        coverage=coverage,
        advisory_total=advisory_total,
        advisory_evaluable=advisory_evaluable,
        advisory_precision_proxy=precision,
        confusion=dict(confusion),
    )
