"""Gold-label adjudication CLI.

Operates on the audit log (Evidence) and the label store (Adjudication events)::

    uv run python -m scripts.adjudicate list
    uv run python -m scripts.adjudicate apply <evidence_id> <outcome> [--finding ...] [--by ...]
    uv run python -m scripts.adjudicate report
    uv run python -m scripts.adjudicate seed-demo

``apply`` is the engineer's verdict. ``report`` is the feedback statistics that
close the loop back to the PHM/rules layer. ``seed-demo`` writes illustrative
verdicts on the EGT demo so the loop is observable end-to-end (NOT real labels).
"""

from __future__ import annotations

import argparse
from uuid import UUID

from ehm.core.evidence import Evidence
from ehm.feedback import Adjudication, AdjudicationOutcome, LabelStore, build_gold_labels, compute
from ehm.safety_brain.audit import AuditLog

DEFAULT_AUDIT = "data/audit/egt_demo.jsonl"
DEFAULT_LABELS = "data/labels/adjudications.jsonl"


def _load_evidence(audit_path: str) -> list[Evidence]:
    return list(AuditLog(audit_path).iter_logged())


def _cmd_list(args: argparse.Namespace) -> int:
    evidence = _load_evidence(args.audit)
    store = LabelStore(args.labels)
    done = store.adjudicated_ids()
    pending = [ev for ev in evidence if ev.id not in done]
    print(f"Un-adjudicated Evidence: {len(pending)} / {len(evidence)}")
    for ev in pending:
        print(f"  [{ev.status.value:<8}] {ev.id}  {ev.subject}")
        print(f"            {ev.observation[:96]}")
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    evidence = _load_evidence(args.audit)
    by_id = {ev.id: ev for ev in evidence}
    if args.evidence_id not in by_id:
        print(f"No Evidence with id {args.evidence_id} in {args.audit}")
        return 1
    store = LabelStore(args.labels)
    prior = store.latest(args.evidence_id)
    adjudication = Adjudication(
        evidence_id=args.evidence_id,
        outcome=args.outcome,
        human_response=args.note,
        actual_finding=args.finding,
        adjudicated_by=args.by,
        supersedes=prior.id if prior else None,
    )
    store.record(adjudication)
    verb = "supersedes" if prior else "first verdict"
    print(f"Recorded {adjudication.outcome.value} for {args.evidence_id} ({verb}).")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    evidence = _load_evidence(args.audit)
    store = LabelStore(args.labels)
    gold = build_gold_labels(evidence, store)
    print(compute(gold).render())
    return 0


def _cmd_seed_demo(args: argparse.Namespace) -> int:
    """Write illustrative verdicts on the EGT demo (NOT real labels)."""
    evidence = _load_evidence(args.audit)
    if not evidence:
        print(f"No Evidence in {args.audit} — run `make demo` first.")
        return 1
    store = LabelStore(args.labels)
    plan = {
        "advisory": (
            AdjudicationOutcome.TRUE_FAULT,
            "Confirmed gas-path degradation at borescope.",
        ),
        "abstain": (AdjudicationOutcome.INCONCLUSIVE, "Insufficient peer data to judge; deferred."),
        "nominal": (AdjudicationOutcome.NFF, "No fault found on inspection."),
    }
    for ev in evidence:
        outcome, note = plan.get(ev.status.value, (AdjudicationOutcome.INCONCLUSIVE, "—"))
        prior = store.latest(ev.id)
        store.record(
            Adjudication(
                evidence_id=ev.id,
                outcome=outcome,
                human_response=note,
                adjudicated_by="demo:seed",
                supersedes=prior.id if prior else None,
            )
        )
    print(f"Seeded {len(evidence)} illustrative adjudications -> {args.labels}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="adjudicate", description="Gold-label adjudication CLI")
    parser.add_argument(
        "--audit", default=DEFAULT_AUDIT, help=f"Evidence audit log (default: {DEFAULT_AUDIT})"
    )
    parser.add_argument(
        "--labels", default=DEFAULT_LABELS, help=f"Label store (default: {DEFAULT_LABELS})"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list un-adjudicated Evidence").set_defaults(func=_cmd_list)
    sub.add_parser("report", help="show feedback metrics").set_defaults(func=_cmd_report)
    sub.add_parser("seed-demo", help="write illustrative verdicts on the EGT demo").set_defaults(
        func=_cmd_seed_demo
    )

    apply_parser = sub.add_parser("apply", help="record an engineer verdict")
    apply_parser.add_argument("evidence_id", type=UUID)
    apply_parser.add_argument(
        "outcome", choices=[o.value for o in AdjudicationOutcome], help="adjudication outcome"
    )
    apply_parser.add_argument("--note", default="", help="engineer note (human_response)")
    apply_parser.add_argument(
        "--finding", default=None, help="ground-truth finding (actual_finding)"
    )
    apply_parser.add_argument("--by", default="engineer", help="adjudicator identity")
    apply_parser.set_defaults(func=_cmd_apply)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
