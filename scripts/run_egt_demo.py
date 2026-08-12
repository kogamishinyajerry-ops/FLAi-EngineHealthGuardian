"""`make demo` entrypoint — runs the EGT-margin vertical slice and prints results.

Invoke with ``uv run python -m scripts.run_egt_demo`` from the repo root.
"""

from __future__ import annotations

from scenarios.egt_margin.pipeline import run, summarize
from scenarios.egt_margin.synthetic import generate

AUDIT_PATH = "data/audit/egt_demo.jsonl"


def main() -> None:
    snapshots = generate(seed=42)
    result = run(snapshots, AUDIT_PATH)

    width = 70
    print("=" * width)
    print("EGT-margin vertical slice — synthetic demo")
    print("=" * width)
    for message in result.messages:
        print(message)
    print("-" * width)
    counts = summarize(result)
    print(f"Evidence logged : {len(result.evidence)}  ->  {result.audit_path}")
    print(
        "Status breakdown:"
        f" NOMINAL={counts.get('nominal', 0)}"
        f" ADVISORY={counts.get('advisory', 0)}"
        f" ABSTAIN={counts.get('abstain', 0)}"
    )
    print("-" * width)
    print("Every Evidence above carries full provenance (raw->feature->rule->ontology->citation).")
    print(
        "All output is advisory-only; nothing here changes dispatch, MEL, or maintenance program."
    )


if __name__ == "__main__":
    main()
