"""Build the static EHM dashboard HTML.

Reads scenario audit logs + the label store, computes gold + metrics in-process
(reusing the library — the dashboard is a read-only consumer), writes a
self-contained HTML file, then opens it in the browser.

  uv run python -m scripts.build_dashboard
  make dashboard    # regenerates demo data, then builds + opens
"""

from __future__ import annotations

import argparse
import json
import webbrowser
from pathlib import Path

from ehm.dashboard import ScenarioData, render_dashboard
from ehm.feedback import LabelStore, build_gold_labels, compute
from ehm.safety_brain.audit import AuditLog

# (display name, scenario key, audit path)
DEFAULT_SCENARIOS: tuple[tuple[str, str, str], ...] = (
    ("EGT 裕度", "egt", "data/audit/egt_demo.jsonl"),
    ("振动", "vibration", "data/audit/vibration_demo.jsonl"),
)
DEFAULT_LABELS = "data/labels/adjudications.jsonl"
DEFAULT_OUT = "data/dashboard/index.html"


def _load_summary(audit_path: str) -> dict:
    """Read the <audit>.summary.json sidecar written by the demo scripts."""
    summary_path = Path(audit_path).with_suffix(".summary.json")
    if not summary_path.exists():
        return {}
    return json.loads(summary_path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build_dashboard")
    parser.add_argument("--labels", default=DEFAULT_LABELS, help="label store JSONL")
    parser.add_argument("--out", default=DEFAULT_OUT, help="output HTML path")
    parser.add_argument("--no-open", action="store_true", help="do not open the browser")
    args = parser.parse_args(argv)

    store = LabelStore(args.labels)
    scenarios: list[ScenarioData] = []
    for name, key, audit in DEFAULT_SCENARIOS:
        if not Path(audit).exists():
            print(f"  跳过 {name}:{audit} 不存在(先 make demo / make demo-vib)")
            continue
        evidence = list(AuditLog(audit).iter_logged())
        gold = build_gold_labels(evidence, store)
        summary = _load_summary(audit)
        scenarios.append(
            ScenarioData(name=name, key=key, gold=gold, metrics=compute(gold), summary=summary)
        )

    if not scenarios:
        print("没有可渲染的场景数据。请先运行:make demo && make demo-vib")
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_dashboard(scenarios), encoding="utf-8")
    print(f"看板已生成 -> {out}  (场景: {', '.join(s.name for s in scenarios)})")
    if not args.no_open:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
