"""Data quality checks — completeness, unit/range sanity.

v0 does gross plausibility checks. Real thresholds come from OEM engineering
limits and are deferred. The two completeness notions matter:

* per-snapshot ``completeness`` — fraction of key params present; drives whether a
  snapshot is usable at all (DQ gate in the pipeline).
* per-ESN average completeness — feeds Data Confidence (see ``safety_brain``); an
  engine sampled sparsely yields low Data Confidence and tends to ABSTAIN.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ehm.core.schemas import EngineSnapshot

# Parameters considered "key" for an EGT-oriented judgment.
_KEY_PARAMS: tuple[str, ...] = ("oat_c", "n1_pct", "n2_pct", "egt_c", "fuel_flow_kg_h")


@dataclass(frozen=True)
class DqReport:
    """Result of assessing one snapshot."""

    snapshot: EngineSnapshot
    completeness: float
    issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when the snapshot passed all configured gates."""
        return not self.issues


def assess(snapshot: EngineSnapshot, *, min_completeness: float = 0.6) -> DqReport:
    """Assess a snapshot; returns a report (never raises on bad data — record it)."""
    issues: list[str] = []
    present = sum(1 for p in _KEY_PARAMS if getattr(snapshot, p) is not None)
    completeness = present / len(_KEY_PARAMS)

    if completeness < min_completeness:
        issues.append(f"completeness {completeness:.2f} < {min_completeness:.2f}")
    # Gross range sanity (NOT OEM limits; those are deferred).
    if snapshot.egt_c is not None and not (-60.0 <= snapshot.egt_c <= 1200.0):
        issues.append(f"egt_c out of plausible range: {snapshot.egt_c}")
    if snapshot.oat_c is not None and not (-60.0 <= snapshot.oat_c <= 70.0):
        issues.append(f"oat_c out of plausible range: {snapshot.oat_c}")
    if snapshot.timestamp.tzinfo is None:
        issues.append("timestamp lacks tzinfo; time alignment unreliable")

    return DqReport(snapshot=snapshot, completeness=completeness, issues=issues)
