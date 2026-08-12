"""Gold-label join — pair each Evidence with its effective adjudication.

This is the canonical "labeled Evidence" dataset: the system's view (Evidence +
its NOMINAL/ADVISORY/ABSTAIN status) alongside the human truth (Adjudication).
Everything downstream — training/eval sets, precision proxies, the report's
gold-label factory — is derived from this view, not from the raw logs.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ehm.core.evidence import Evidence
from ehm.feedback.labels import Adjudication
from ehm.feedback.store import LabelStore


@dataclass(frozen=True)
class GoldLabel:
    """One Evidence joined with its effective adjudication (None if un-adjudicated)."""

    evidence: Evidence
    adjudication: Adjudication | None

    @property
    def is_adjudicated(self) -> bool:
        """True when this Evidence has an effective adjudication."""
        return self.adjudication is not None


def build_gold_labels(evidence: Iterable[Evidence], labels: LabelStore) -> list[GoldLabel]:
    """Join an Evidence stream with the latest adjudication per Evidence id."""
    by_evidence = labels.by_evidence()
    rows: list[GoldLabel] = []
    for ev in evidence:
        events = by_evidence.get(ev.id, [])
        if not events:
            rows.append(GoldLabel(evidence=ev, adjudication=None))
            continue
        latest = max(events, key=lambda a: (a.adjudicated_at, a.id))
        rows.append(GoldLabel(evidence=ev, adjudication=latest))
    return rows
