"""Dashboard HTML renderer — builds a self-contained page from Evidence + metrics.

Pure string composition (no template engine, no external assets) so the output is
one offline-openable file. All dynamic text is HTML-escaped. The renderer is a
read-only consumer of ``ehm.core`` + ``ehm.feedback`` — it never becomes a source
of truth (ADR-0008).
"""

from __future__ import annotations

import html
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime

from ehm.core.evidence import EvidenceStatus
from ehm.dashboard.style import CSS
from ehm.feedback.gold import GoldLabel
from ehm.feedback.metrics import Metrics

_SEVERITY = {"advisory": 0, "abstain": 1, "nominal": 2}
_OUTCOMES = (
    "true_fault",
    "conditional_anomaly",
    "operational",
    "sensor_issue",
    "nff",
    "inconclusive",
    "unadjudicated",
)
_STATUSES = ("advisory", "abstain", "nominal")
_SUBJECT_PREFIX = "ehm:ESN:"


@dataclass(frozen=True)
class ScenarioData:
    """One scenario's worth of rendered data."""

    name: str
    key: str
    gold: list[GoldLabel]
    metrics: Metrics


def _esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def _bar_color(value: float | None) -> str:
    if value is None:
        return "#cbd5e1"
    if value >= 0.7:
        return "#10b981"
    if value >= 0.4:
        return "#f59e0b"
    return "#ef4444"


def _esn(subject: str) -> str:
    return subject[len(_SUBJECT_PREFIX) :] if subject.startswith(_SUBJECT_PREFIX) else subject


def _status_badge(status: EvidenceStatus) -> str:
    return f'<span class="status {status.value}">{status.value}</span>'


def _confidence_bars(g: GoldLabel) -> str:
    conf = g.evidence.confidence
    rows = []
    for label in ("data", "model", "knowledge", "applicability"):
        value = getattr(conf, label)
        pct = (value * 100) if value is not None else 0.0
        shown = f"{value:.2f}" if value is not None else "n/a"
        rows.append(
            f'<div class="row"><span class="cl">{label}</span>'
            f'<div class="bar"><i style="width:{pct:.0f}%;background:{_bar_color(value)}"></i></div>'
            f'<span class="cv">{shown}</span></div>'
        )
    return f'<div class="conf">{"".join(rows)}</div>'


def _pill(items: list[str], empty_note: str = "—") -> str:
    """Render a list of strings as one (or an empty-muted) pill."""
    if not items:
        return f'<span class="pill empty">{_esc(empty_note)}</span>'
    joined = ", ".join(items)
    return f'<span class="pill">{_esc(joined)}</span>'


def _short_uri(uri: str) -> str:
    return uri.rsplit("#", 1)[-1] if "#" in uri else uri.rsplit("/", 1)[-1]


def _provenance_chain(g: GoldLabel) -> str:
    p = g.evidence.provenance
    rule = p.rule_version or p.model_version or "—"
    steps = [
        ("raw", _pill(p.raw_refs, "raw")),
        ("feat", _pill(p.feature_refs, "feature")),
        ("rule", f'<span class="pill">{_esc(rule)}</span>'),
        ("ont", _pill([_short_uri(u) for u in p.ontology_entities], "ontology")),
        ("ref", _pill(p.manual_citations, "FIM")),
    ]
    chain = []
    for i, (_label, pill) in enumerate(steps):
        chain.append(pill)
        if i < len(steps) - 1:
            chain.append('<span class="arrow">→</span>')
    return f'<details class="chain"><summary>证据链溯源(provenance)</summary><div class="chain-pills">{"".join(chain)}</div></details>'


def _adjudication_tag(g: GoldLabel) -> str:
    if g.adjudication is None:
        return ""
    outcome = g.adjudication.outcome.value
    tag = f'<span class="tag {outcome}">{outcome}</span>'
    finding = g.adjudication.actual_finding
    finding_html = f'<div class="finding">{_esc(finding)}</div>' if finding else ""
    src = g.adjudication.adjudicated_by
    return f'<div style="margin-top:11px">{tag}<span class="finding" style="display:inline">via {_esc(src)}</span>{finding_html}</div>'


def _engine_card(g: GoldLabel) -> str:
    ev = g.evidence
    status = ev.status
    hyp = f'<span class="hyp">· {_esc(ev.hypothesis)}</span>' if ev.hypothesis else ""
    head = (
        f'<div class="head">{_status_badge(status)}'
        f'<span class="esn">{_esc(_esn(ev.subject))}</span>{hyp}</div>'
    )
    metric_line = f'<div class="metric-line">{_esc(ev.observation)}</div>'

    if status is EvidenceStatus.ABSTAIN:
        body_text = (
            f'<div class="reco abstain"><span class="lbl">拒答(ABSTAIN):</span>'
            f"{_esc(ev.abstain_reason or '置信不足,转人工')}</div>"
        )
    elif ev.recommendation:
        body_text = f'<div class="reco"><span class="lbl">建议(advisory-only):</span>{_esc(ev.recommendation)}</div>'
    else:
        body_text = '<div class="reco"><span class="lbl">状态:</span>正常,无需动作</div>'

    body_text += _adjudication_tag(g)
    body_text += _provenance_chain(g)

    body = f'<div class="card-body"><div>{body_text}</div><div>{_confidence_bars(g)}</div></div>'
    return f'<div class="card {status.value}" data-status="{status.value}">{head}{metric_line}{body}</div>'


def _metric_tiles(gold: list[GoldLabel], metrics: Metrics) -> str:
    counts = Counter(g.evidence.status.value for g in gold)
    precision = (
        f"{metrics.advisory_precision_proxy:.0%}"
        if metrics.advisory_precision_proxy is not None
        else "—"
    )
    tiles = [
        ("发动机", str(len(gold)), "受监控"),
        ("ADVISORY", str(counts.get("advisory", 0)), "建议关注", "acc"),
        ("ABSTAIN", str(counts.get("abstain", 0)), "拒答转人工", "warn"),
        ("覆盖率", f"{metrics.coverage:.0%}", f"{metrics.adjudicated}/{metrics.total} 已判定"),
        ("precision", precision, "advisory 命中真故障"),
    ]
    out = []
    for tile in tiles:
        label, value, sub = tile[0], tile[1], tile[2]
        cls = tile[3] if len(tile) > 3 else ""
        out.append(
            f'<div class="tile {cls}"><div class="v">{value}</div><div class="l">{label} · {sub}</div></div>'
        )
    return f'<div class="tiles">{"".join(out)}</div>'


def _filters() -> str:
    chips = [
        ("全部", "all", True),
        ("告警", "advisory", False),
        ("拒答", "abstain", False),
        ("正常", "nominal", False),
    ]
    out = [
        f'<button class="chip {"active" if act else ""}" data-filter="{f}">{label}</button>'
        for label, f, act in chips
    ]
    return f'<div class="filters">{"".join(out)}</div>'


def _confusion_matrix(metrics: Metrics) -> str:
    confusion = metrics.confusion
    max_cell = max((v for v in confusion.values()), default=0) or 1
    head = "".join(f"<th>{o}</th>" for o in _OUTCOMES)
    rows = []
    for status in _STATUSES:
        cells = []
        for outcome in _OUTCOMES:
            value = confusion.get((status, outcome), 0)
            if value == 0:
                cells.append('<td class="zero">·</td>')
            else:
                alpha = 0.16 + 0.6 * (value / max_cell)
                cells.append(
                    f'<td class="cell" style="background:rgba(59,130,246,{alpha:.2f})">{value}</td>'
                )
        rows.append(f'<tr class="rowhead"><td>{status}</td>{"".join(cells)}</tr>')
    return (
        f'<table class="matrix"><thead><tr><th>系统状态 ＼ 人工真相</th>{head}</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _flow_diagram() -> str:
    steps = [
        "ingest",
        "DQ",
        "feature",
        "peer",
        "rule",
        "uncertainty",
        "policy.gate",
        "Evidence",
        "agent",
        "audit",
    ]
    pills = []
    for i, step in enumerate(steps):
        pills.append(f'<span class="pill">{step}</span>')
        if i < len(steps) - 1:
            pills.append('<span class="arrow">→</span>')
    pills.append('<span class="arrow" style="margin:0 6px">↺</span>')
    pills.append(
        '<span class="pill" style="background:#dcfce7;color:#166534">gold-label 闭环</span>'
    )
    return f'<div class="flow-pills">{"".join(pills)}</div>'


def _scenario_section(sc: ScenarioData) -> str:
    if not sc.gold:
        return (
            f'<section class="scenario hidden" data-name="{sc.key}">'
            f'<p class="empty-note">该场景暂无 Evidence(先跑 <code>make demo</code> / <code>make demo-vib</code>)。</p></section>'
        )
    ordered = sorted(sc.gold, key=lambda g: _SEVERITY.get(g.evidence.status.value, 9))
    cards = "".join(_engine_card(g) for g in ordered)
    return (
        f'<section class="scenario hidden" data-name="{sc.key}">'
        f"{_metric_tiles(sc.gold, sc.metrics)}"
        f'<div class="section-title">机队状态</div>{_filters()}<div class="cards">{cards}</div>'
        f'<div class="grid2">'
        f'<div class="panel"><h3>混淆矩阵(系统状态 × 人工真相)</h3>{_confusion_matrix(sc.metrics)}</div>'
        f'<div class="panel"><h3>架构数据流</h3>{_flow_diagram()}'
        f'<p class="finding" style="margin-top:12px">每条 Evidence 沿这条链产出,'
        f"判定/MRO 真相回流形成 gold-label 闭环,反哺 precision。</p></div>"
        f"</div></section>"
    )


_JS = """
document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>{
  const name=t.dataset.target;
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x===t));
  document.querySelectorAll('.scenario').forEach(s=>s.classList.toggle('hidden',s.dataset.name!==name));
  try{localStorage.setItem('ehm-tab',name);}catch(e){}
}));
document.querySelectorAll('.chip').forEach(c=>c.addEventListener('click',()=>{
  const sec=c.closest('.scenario');const f=c.dataset.filter;
  sec.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x===c));
  sec.querySelectorAll('.card').forEach(card=>card.classList.toggle('hidden',!(f==='all'||card.dataset.status===f)));
}));
(function(){try{const s=localStorage.getItem('ehm-tab');if(s){const t=document.querySelector('.tab[data-target="'+s+'"]');if(t){t.click();return;}}}catch(e){}const first=document.querySelector('.tab');if(first)first.click();})();
"""


def render_dashboard(scenarios: list[ScenarioData]) -> str:
    """Render the full self-contained HTML for one or more scenarios."""
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    tabs = "".join(
        f'<button class="tab{" active" if i == 0 else ""}" data-target="{sc.key}">{_esc(sc.name)}</button>'
        for i, sc in enumerate(scenarios)
    )
    sections = "".join(_scenario_section(sc) for sc in scenarios)
    return (
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>EHM 看板 · Engine Health Guardian</title>"
        f"<style>{CSS}</style></head><body>"
        "<header class='topbar'>"
        "<div class='brand'><span class='shield'>🛡</span> Engine Health Guardian</div>"
        f"<div class='tabs'>{tabs}</div>"
        "<div class='spacer'></div>"
        "<div class='badge'>advisory-only</div>"
        f"<div class='gen'>生成于 {generated}</div>"
        "</header>"
        f"<main>{sections}"
        "<footer>所有结论均为 advisory-only,不改变放行/MEL/维修方案。"
        "数据为合成/示例,用于架构与闭环演示。</footer>"
        "</main>"
        f"<script>{_JS}</script>"
        "</body></html>"
    )


__all__ = ["ScenarioData", "render_dashboard"]
