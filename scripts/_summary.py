"""Write a run-summary sidecar JSON consumed by the dashboard's pipeline view.

The dashboard is a read-only consumer; it does not recompute pipeline stage
counts itself — it reads them from this sidecar (written next to the audit log).
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol


class _SliceResult(Protocol):
    snapshots_in: int
    snapshots_clean: int
    evidence: list[object]


def write_summary(audit_path: str, scenario: str, result: _SliceResult) -> None:
    """Write <audit_path>.summary.json with stage counts + status breakdown."""
    counts = Counter(ev.status.value for ev in result.evidence)  # type: ignore[attr-defined]
    payload = {
        "scenario": scenario,
        "snapshots_in": result.snapshots_in,
        "snapshots_clean": result.snapshots_clean,
        "evidence_out": len(result.evidence),
        "advisory": counts.get("advisory", 0),
        "abstain": counts.get("abstain", 0),
        "nominal": counts.get("nominal", 0),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    summary_path = Path(audit_path).with_suffix(".summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
