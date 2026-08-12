"""`make demo-vib` entrypoint — runs the vibration vertical slice and prints results.

Invoke with ``uv run python -m scripts.run_vibration_demo`` from the repo root.
"""

from __future__ import annotations

from collections import defaultdict

from scenarios.vibration.pipeline import run
from scenarios.vibration.synthetic import generate

from scripts._summary import write_summary

AUDIT_PATH = "data/audit/vibration_demo.jsonl"


def main() -> None:
    snapshots = generate(seed=42)
    result = run(snapshots, AUDIT_PATH)
    write_summary(AUDIT_PATH, "振动", result)

    width = 70
    print("=" * width)
    print("Vibration vertical slice — synthetic demo")
    print("=" * width)
    for message in result.messages:
        print(message)
    print("-" * width)
    counts: dict[str, int] = defaultdict(int)
    for ev in result.evidence:
        counts[ev.status.value] += 1
    print(f"Evidence logged : {len(result.evidence)}  ->  {result.audit_path}")
    print(
        "Status breakdown:"
        f" NOMINAL={counts.get('nominal', 0)}"
        f" ADVISORY={counts.get('advisory', 0)}"
        f" ABSTAIN={counts.get('abstain', 0)}"
    )
    print("-" * width)
    print("Advisory-only; reuses the same Evidence spine / policy gate / feedback loop as EGT.")


if __name__ == "__main__":
    main()
