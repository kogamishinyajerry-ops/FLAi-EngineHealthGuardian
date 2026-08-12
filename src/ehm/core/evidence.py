"""Evidence object — the spine of the system.

Every alert, recommendation, and label is an ``Evidence`` object carrying full
provenance from raw data to human response, implementing the chain required for
auditable, certifiable EHM::

    raw → cleaned → feature → model/rule version → ontology entities
        → manual citation → confidence → recommendation → human response → finding

``ABSTAIN`` is a first-class outcome (see ADR-0003): when confidence or
applicability is below the gate, ``recommendation`` is ``None`` and the object
says "defer to manual check" rather than forcing an answer. This is safer than
a hallucinated probability.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ConfidenceKind(StrEnum):
    """Four independent confidence dimensions."""

    DATA = "data"  # is the underlying data complete & valid?
    MODEL = "model"  # model probability / interval calibration
    KNOWLEDGE = "knowledge"  # OEM doc vs expert heuristic vs statistical association
    APPLICABILITY = "applicability"  # does the rule/model apply to this ESN/config?


class Confidence(BaseModel):
    """Confidence along four independent dimensions; ``None`` means not assessed."""

    data: float | None = Field(default=None, ge=0.0, le=1.0)
    model: float | None = Field(default=None, ge=0.0, le=1.0)
    knowledge: float | None = Field(default=None, ge=0.0, le=1.0)
    applicability: float | None = Field(default=None, ge=0.0, le=1.0)

    def overall(self) -> float | None:
        """Weakest-link aggregate: a chain is only as strong as its weakest confidence."""
        values = [
            v for v in (self.data, self.model, self.knowledge, self.applicability) if v is not None
        ]
        if not values:
            return None
        return min(values)


class Provenance(BaseModel):
    """Where a conclusion came from — every link in the evidence chain."""

    raw_refs: list[str] = Field(default_factory=list)
    cleaned_refs: list[str] = Field(default_factory=list)
    feature_refs: list[str] = Field(default_factory=list)
    model_version: str | None = None
    rule_version: str | None = None
    ontology_entities: list[str] = Field(default_factory=list)
    manual_citations: list[str] = Field(
        default_factory=list
    )  # e.g. ["FIM 73-21-00", "AMM 72-31-00"]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    generated_by: str = "ehm:pipeline:v0"


class EvidenceStatus(StrEnum):
    """Lifecycle of an Evidence object (see ADR-0003)."""

    NOMINAL = "nominal"  # analyzed, nothing notable
    ADVISORY = "advisory"  # recommending an action (advisory-only)
    ABSTAIN = "abstain"  # insufficient confidence, defer to human


class Signal(BaseModel):
    """The time-series the Evidence is based on (e.g. the residual series).

    Persisted so dashboards can draw waveforms/trends — the evidence's whole
    basis is this series, so carrying it is honest (not UI-only state). Optional
    and backward-compatible.
    """

    label: str = Field(description="What the series is, e.g. 'egt_residual'")
    unit: str = Field(default="", description="Per-point unit, e.g. '°C' (residual)")
    points: list[float] = Field(default_factory=list, description="Values oldest -> newest")
    baseline: float | None = Field(default=None, description="Healthy reference (0 for a residual)")
    threshold: float | None = Field(default=None, description="Alert threshold for shading")
    flight_ids: list[str] = Field(default_factory=list, description="Optional x-axis labels")


class Evidence(BaseModel):
    """A single auditable unit of EHM output."""

    id: UUID = Field(default_factory=uuid4)
    subject: str = Field(description="Engine URI / ESN the evidence concerns")
    timestamp: datetime | None = Field(
        default=None,
        description="When the observed condition occurred (event time, NOT pipeline-run time)",
    )
    signal: Signal | None = Field(
        default=None, description="Time-series the evidence is based on (for viz)"
    )
    observation: str = Field(description="What was observed, in plain terms")
    hypothesis: str | None = Field(default=None, description="Candidate cause / failure mode")
    confidence: Confidence = Field(default_factory=Confidence)
    provenance: Provenance = Field(default_factory=Provenance)
    status: EvidenceStatus = EvidenceStatus.NOMINAL
    recommendation: str | None = Field(
        default=None,
        description="Recommended action; None with status=ABSTAIN means defer to manual check",
    )
    abstain_reason: str | None = Field(
        default=None, description="Why the system abstained, if it did"
    )
    human_response: str | None = Field(
        default=None, description="Engineer adjudication (filled later)"
    )
    actual_finding: str | None = Field(
        default=None, description="Ground truth from MRO/shop visit (filled later)"
    )

    @property
    def is_abstain(self) -> bool:
        """True when the system chose to defer rather than answer."""
        return self.status is EvidenceStatus.ABSTAIN
