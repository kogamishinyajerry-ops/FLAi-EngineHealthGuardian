"""Time parsing — shared by ingestion and feedback.

Lives in ``core`` so subsystems don't grow lateral dependencies just to parse a
timestamp. Naive values are assumed UTC (QAR / ops-log convention); this also
satisfies the data-quality gate that requires tz-aware timestamps.
"""

from __future__ import annotations

from datetime import UTC, datetime


def parse_time(raw: object, fmt: str = "iso") -> datetime:
    """Parse a timestamp.

    ``fmt == "iso"`` uses ``datetime.fromisoformat`` (handles a trailing ``Z`` in
    3.11+); otherwise ``fmt`` is a ``strptime`` pattern. Naive results are pinned
    to UTC.
    """
    text = str(raw).strip()
    if fmt in ("iso", ""):
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    else:
        dt = datetime.strptime(text, fmt)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt
