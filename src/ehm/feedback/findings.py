"""MRO findings — the authoritative ``actual_finding`` source for the gold-label loop.

An MRO finding (shop visit / borescope / removal / NFF / repair disposition) is
*physical ground truth*, not an engine observation, so it lives in the label-side
(``feedback``), not in ``data_brain.ingestion``. Each finding is bridged into the
existing loop as an ``Adjudication`` carrying ``actual_finding`` (ADR-0004 event
sourcing), so the LabelStore / GoldLabel / metrics machinery is reused — no new
store or join.

Finding -> outcome mapping is a documented heuristic (driven by structured
``finding_type`` / ``disposition``, not text-mining). Orphan findings (no prior
Evidence on that ESN) are skipped: there is nothing to adjudicate.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ehm.core.evidence import Evidence, EvidenceStatus
from ehm.feedback.labels import Adjudication, AdjudicationOutcome

#: Subject URI prefix the pipeline emits (``ehm:ESN:<esn>``); load-bearing for matching.
_ESN_SUBJECT_PREFIX = "ehm:ESN:"
#: Sortable fallback so ``datetime | None`` timestamps type-check (never hit at runtime).
_EPOCH = datetime.min.replace(tzinfo=UTC)


class FindingType(StrEnum):
    """Kinds of MRO finding records ingested from work-order / shop data."""

    REMOVAL = "removal"
    BORESCOPE = "borescope"
    NFF = "nff"
    REPAIR = "repair"
    RTV = "rtv"  # return to service, no fault
    TEST = "test"
    SHOP_VISIT = "shop_visit"


class Disposition(StrEnum):
    """Work-order disposition of the affected item."""

    REPAIR = "repair"
    REPLACE = "replace"
    RTV = "rtv"
    SCRAP = "scrap"


#: Dispositions that confirm a real fault was found.
_FAULTY_DISPOSITIONS: frozenset[Disposition] = frozenset(
    {Disposition.REPAIR, Disposition.REPLACE, Disposition.SCRAP}
)


class MroFinding(BaseModel):
    """One ground-truth finding about an engine from MRO / shop data."""

    id: UUID = Field(default_factory=uuid4)
    esn: str
    finding_date: datetime
    finding_type: FindingType
    finding_text: str
    disposition: Disposition | None = None
    component: str | None = None
    source: str = "mro"


def derive_outcome(finding: MroFinding) -> AdjudicationOutcome:
    """Map a finding to a gold-label outcome (structured, documented heuristic).

    - REMOVAL / REPAIR -> TRUE_FAULT (a part was pulled/fixed)
    - NFF / RTV        -> NFF
    - BORESCOPE        -> fault only if disposition confirms it, else NFF/conditional
    - TEST / SHOP_VISIT-> INCONCLUSIVE (no clean signal either way)
    """
    match finding.finding_type:
        case FindingType.REMOVAL | FindingType.REPAIR:
            return AdjudicationOutcome.TRUE_FAULT
        case FindingType.NFF | FindingType.RTV:
            return AdjudicationOutcome.NFF
        case FindingType.BORESCOPE:
            if finding.disposition in _FAULTY_DISPOSITIONS:
                return AdjudicationOutcome.TRUE_FAULT
            if finding.disposition is Disposition.RTV:
                return AdjudicationOutcome.NFF
            return AdjudicationOutcome.CONDITIONAL_ANOMALY
        case FindingType.TEST | FindingType.SHOP_VISIT:
            return AdjudicationOutcome.INCONCLUSIVE


def evidence_esn(subject: str) -> str | None:
    """Return the ESN encoded in an Evidence subject, or None if not in the convention."""
    if subject.startswith(_ESN_SUBJECT_PREFIX):
        return subject[len(_ESN_SUBJECT_PREFIX) :]
    return None


def _target_evidence(prior: list[Evidence]) -> Evidence | None:
    """Pick the Evidence a finding resolves: latest non-NOMINAL, else latest."""
    if not prior:
        return None
    non_nominal = [ev for ev in prior if ev.status is not EvidenceStatus.NOMINAL]
    return non_nominal[-1] if non_nominal else prior[-1]


def findings_to_adjudications(
    findings: list[MroFinding], evidence: list[Evidence]
) -> list[Adjudication]:
    """Bridge findings into the loop: one Adjudication per finding with a target Evidence.

    Each finding attaches to the latest Evidence on the same ESN at or before
    ``finding_date`` (preferring non-NOMINAL alerts — the "open" alert the shop
    visit presumably answered). Findings with no matching prior Evidence are
    orphaned and skipped (count returned separately via ``orphan_count`` if needed).
    """
    by_esn: dict[str, list[Evidence]] = defaultdict(list)
    for ev in evidence:
        esn = evidence_esn(ev.subject)
        # Only evidence carrying an event timestamp can be matched temporally.
        if esn is not None and ev.timestamp is not None:
            by_esn[esn].append(ev)
    for bucket in by_esn.values():
        bucket.sort(key=lambda ev: ev.timestamp or _EPOCH)

    adjudications: list[Adjudication] = []
    for finding in findings:
        bucket = by_esn.get(finding.esn, [])
        prior = [ev for ev in bucket if (ev.timestamp or _EPOCH) <= finding.finding_date]
        target = _target_evidence(prior)
        if target is None:
            continue
        adjudications.append(
            Adjudication(
                evidence_id=target.id,
                outcome=derive_outcome(finding),
                human_response=f"{finding.finding_type.value}:{finding.component or '-'}",
                actual_finding=finding.finding_text,
                adjudicated_by=f"mro:{finding.source}",
                adjudicated_at=finding.finding_date,
            )
        )
    return adjudications


__all__ = [
    "Disposition",
    "FindingType",
    "MroFinding",
    "derive_outcome",
    "evidence_esn",
    "findings_to_adjudications",
]
