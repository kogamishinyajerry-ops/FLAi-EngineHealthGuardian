"""Feedback — the gold-label loop.

Closes the report's most valuable early asset: every Evidence eventually gets an
engineer adjudication, and those labels become the training/eval ground truth that
feeds back into the PHM/rules layer.

Design (see ADR-0004): Evidence in the audit log is **immutable**. Human input is
recorded as append-only ``Adjudication`` events keyed by ``Evidence.id`` (event
sourcing), so the audit trail is never rewritten and full history is retained.
The "labeled Evidence" view is produced by joining audit + labels (``gold.py``),
and ``metrics.py`` turns that into feedback statistics for the model layer.

Depends only on ``ehm.core`` — a peer to the brains, not a reverse dependency.
"""

from ehm.feedback.findings import (
    Disposition,
    FindingType,
    MroFinding,
    derive_outcome,
    evidence_esn,
    findings_to_adjudications,
)
from ehm.feedback.gold import GoldLabel, build_gold_labels
from ehm.feedback.labels import Adjudication, AdjudicationOutcome
from ehm.feedback.metrics import Metrics, compute
from ehm.feedback.mro_json import MroJsonAdapter
from ehm.feedback.store import LabelStore

__all__ = [
    "Adjudication",
    "AdjudicationOutcome",
    "Disposition",
    "FindingType",
    "GoldLabel",
    "LabelStore",
    "Metrics",
    "MroFinding",
    "MroJsonAdapter",
    "build_gold_labels",
    "compute",
    "derive_outcome",
    "evidence_esn",
    "findings_to_adjudications",
]
