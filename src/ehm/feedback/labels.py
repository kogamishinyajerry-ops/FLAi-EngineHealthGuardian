"""Adjudication vocabulary + event model.

The outcome categories come directly from the strategy report's gold-label
factory: every alert should finally resolve to one of
「真实故障 / 条件异常 / 操作因素 / 传感器问题 / 无故障发现 NFF / 无法判断」.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AdjudicationOutcome(StrEnum):
    """Engineer verdict on an Evidence item — the gold label."""

    TRUE_FAULT = "true_fault"  # a real fault was confirmed
    CONDITIONAL_ANOMALY = "conditional_anomaly"  # anomalous condition, not (yet) a fault
    OPERATIONAL = "operational"  # explained by operation / environment, not the engine
    SENSOR_ISSUE = "sensor_issue"  # data / sensor problem, not the engine
    NFF = "nff"  # no fault found
    INCONCLUSIVE = "inconclusive"  # cannot determine from available evidence


#: Outcomes that count as "the alert was real / actionable" for the precision proxy.
REAL_OUTCOMES: frozenset[AdjudicationOutcome] = frozenset(
    {AdjudicationOutcome.TRUE_FAULT, AdjudicationOutcome.CONDITIONAL_ANOMALY}
)

#: Outcome excluded from the precision denominator (neither right nor wrong).
EXCLUDED_FROM_PRECISION: frozenset[AdjudicationOutcome] = frozenset(
    {AdjudicationOutcome.INCONCLUSIVE}
)


class Adjudication(BaseModel):
    """An append-only human verdict on one Evidence item (event-sourced; see ADR-0004)."""

    id: UUID = Field(default_factory=uuid4)
    evidence_id: UUID
    outcome: AdjudicationOutcome
    human_response: str = Field(description="Engineer's note / decision (free text)")
    actual_finding: str | None = Field(
        default=None, description="Ground truth if known (e.g. shop-visit / borescope result)"
    )
    adjudicated_by: str
    adjudicated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    supersedes: UUID | None = Field(
        default=None, description="id of a prior adjudication this one replaces (provenance)"
    )
