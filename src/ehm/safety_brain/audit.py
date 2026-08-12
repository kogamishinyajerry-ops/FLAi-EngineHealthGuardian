"""Audit — append-only JSONL evidence log.

Every Evidence that leaves the pipeline is serialized here with its full
provenance. v0 is a local file; production needs WORM/immutable storage with a
formal PROV-O binding (deferred). The contract (``log`` / ``iter_logged``) is
stable so the backend can be swapped without touching callers.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from ehm.core.evidence import Evidence


class AuditLog:
    """Append-only JSONL log of Evidence objects."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def log(self, evidence: Evidence) -> None:
        """Append one Evidence as a JSON line."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(evidence.model_dump_json() + "\n")

    def iter_logged(self) -> Iterator[Evidence]:
        """Replay all logged Evidence in write order."""
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    yield Evidence.model_validate_json(line)

    def clear(self) -> None:
        """Remove the log file (tests / demo re-runs only)."""
        if self.path.exists():
            self.path.unlink()
