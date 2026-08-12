"""Dashboard renderer v2 — mission console (3 views, progressive disclosure).

Read-only consumer of ``ehm.core`` + ``ehm.feedback`` (+ scenario summaries).
Anomalies surface and glow; nominal engines collapse; engine detail opens in a
drawer on demand. Pure string composition, fully offline (ADR-0008/0009).
"""

from __future__ import annotations

import html
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ehm.core.evidence import EvidenceStatus
from ehm.dashboard.charts import radar, sparkline
from ehm.dashboard.style import CSS
from ehm.feedback.gold import GoldLabel
from ehm.feedback.metrics import Metrics

_SEVERITY = {"advisory": 0, "abstain": 1, "nominal": 2}
_SPARK_COLOR = {"advisory": "#fbbf24", "abstain": "#fb7185", "nominal": "#22d3ee"}
_SUBJECT_PREFIX = "ehm:ESN:"
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


@dataclass(frozen=True)
class ScenarioData:
    """One scenario's rendered data: gold labels, metrics, and a run summary."""

    name: str
    key: str
    gold: list[GoldLabel]
    metrics: Metrics
    summary: dict[str, object] = field(default_factory=dict)


def _esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def _esn(subject: str) -> str:
    return subject[len(_SUBJECT_PREFIX) :] if subject.startswith(_SUBJECT_PREFIX) else subject


def _spark(g: GoldLabel, *, color: str | None = None, width: int = 150, height: int = 42) -> str:
    sig = g.evidence.signal
    col = color or _SPARK_COLOR.get(g.evidence.status.value, "#22d3ee")
    if sig is None:
        return sparkline([], color=col, width=width, height=height)
    return sparkline(
        sig.points,
        threshold=sig.threshold,
        baseline=sig.baseline,
        color=col,
        width=width,
        height=height,
    )


def _mro_tag(g: GoldLabel) -> str:
    if g.adjudication is None:
        return ""
    outcome = g.adjudication.outcome.value
    return f'<span class="mro {outcome}">✚ MRO:{_esc(outcome)}</span>'


def _engine_card(g: GoldLabel, drawer_id: str) -> str:
    ev = g.evidence
    status = ev.status.value
    hyp = f'<span class="hyp">· {_esc(ev.hypothesis)}</span>' if ev.hypothesis else ""
    reco_text = (
        ev.recommendation or ev.abstain_reason or ("正常,无需动作" if status == "nominal" else "—")
    )
    lbl = "拒答" if status == "abstain" else ("建议" if status == "advisory" else "状态")
    return (
        f'<div class="card {status}" data-drawer="{drawer_id}">'
        f'<div class="card-top">'
        f'<span class="badge {status}">{status}</span>'
        f'<span class="esn mono">{_esc(_esn(ev.subject))}</span>{hyp}'
        f'<span class="spark">{_spark(g)}</span>'
        f"{_mro_tag(g)}"
        f"</div>"
        f'<div class="card-mid">'
        f'<div class="reco"><span class="lbl">{lbl}:</span> {_esc(reco_text)}</div>'
        f'<div class="card-radar">{radar(ev.confidence, size=82)}<span class="cl">置信</span></div>'
        f"</div></div>"
    )


def _drawer(g: GoldLabel, drawer_id: str) -> str:
    ev = g.evidence
    status = ev.status.value
    sig = ev.signal
    big = _spark(g, width=480, height=120) if sig else sparkline([], width=480, height=120)
    reco_text = ev.recommendation or ev.abstain_reason or "正常,无需动作"
    lbl = (
        "拒答"
        if status == "abstain"
        else ("建议(advisory-only)" if status == "advisory" else "状态")
    )
    finding = ""
    if g.adjudication and g.adjudication.actual_finding:
        finding = f'<div class="blk"><h4>MRO 真相</h4><div class="reco">{_esc(g.adjudication.actual_finding)}</div></div>'
    p = ev.provenance
    chain_steps = [
        ("raw", ", ".join(p.raw_refs) or "—"),
        ("feature", ", ".join(p.feature_refs) or "—"),
        ("rule", p.rule_version or p.model_version or "—"),
        (
            "ontology",
            ", ".join((u.rsplit("#", 1)[-1] if "#" in u else u) for u in p.ontology_entities)
            or "—",
        ),
        ("FIM", ", ".join(p.manual_citations) or "—"),
    ]
    pills = []
    for i, (k, val) in enumerate(chain_steps):
        pills.append(f'<span class="chip"><span class="k">{k}</span>{_esc(val)}</span>')
        if i < len(chain_steps) - 1:
            pills.append('<span class="arrow">→</span>')
    obs = ev.observation
    label_txt = _esc(sig.label) if sig else "signal"
    return (
        f'<div class="drawer" id="{drawer_id}"><button class="x" aria-label="close">×</button>'
        f'<h2 class="mono">{_esc(_esn(ev.subject))}</h2>'
        f'<div class="d-sub"><span class="badge {status}">{status}</span> '
        f"{_esc(ev.hypothesis) if ev.hypothesis else ''}</div>"
        f'<div class="blk"><h4>{label_txt} 趋势</h4><div class="bigchart">{big}</div></div>'
        f'<div class="blk"><h4>观测</h4><div class="reco mono" style="font-size:12px">{_esc(obs)}</div></div>'
        f'<div class="blk dgrid"><div style="flex:0 0 auto">{radar(ev.confidence, size=110)}</div>'
        f'<div class="reco" style="flex:1"><span class="lbl">{lbl}:</span> {_esc(reco_text)}</div></div>'
        f"{finding}"
        f'<div class="blk"><h4>证据链溯源</h4><div class="chainpills">{"".join(pills)}</div></div>'
        f"</div>"
    )


def _fleet_view(sc: ScenarioData) -> str:
    if not sc.gold:
        return '<div class="view active" data-view="fleet"><p class="empty-note">该场景暂无 Evidence。</p></div>'
    counts = Counter(g.evidence.status.value for g in sc.gold)
    total = len(sc.gold)
    healthy = counts.get("nominal", 0)
    health_pct = (healthy / total * 100) if total else 0.0
    ordered = sorted(sc.gold, key=lambda g: _SEVERITY.get(g.evidence.status.value, 9))
    cards = []
    drawers = []
    for i, g in enumerate(ordered):
        did = f"dr-{sc.key}-{i}"
        if g.evidence.status is not EvidenceStatus.NOMINAL:
            cards.append(_engine_card(g, did))
        drawers.append(_drawer(g, did))
    normal_dots = "".join(
        f'<span class="ndot" data-drawer="dr-{sc.key}-{i}"><span class="led"></span>{_esc(_esn(g.evidence.subject))}</span>'
        for i, g in enumerate(ordered)
        if g.evidence.status is not EvidenceStatus.NOMINAL
    )
    collapsed = (
        f'<details class="collapsed"><summary>正常 · {healthy} 台(点击查看)</summary><div class="dots">{normal_dots}</div></details>'
        if healthy
        else ""
    )
    precision = sc.metrics.advisory_precision_proxy
    prec_s = f"{precision:.0%}" if precision is not None else "—"
    hero = (
        f'<div class="hero">'
        f'<div class="stat"><div class="big">{health_pct:.0f}%</div><div class="cap">机队健康(正常占比)</div>'
        f'<div class="healthbar"><i style="width:{health_pct:.0f}%"></i></div></div>'
        f'<div class="stat"><div class="kpis">'
        f'<div class="kpi adv"><span class="v">{counts.get("advisory", 0)}</span><span class="l">告警 ADVISORY</span></div>'
        f'<div class="kpi abt"><span class="v">{counts.get("abstain", 0)}</span><span class="l">拒答 ABSTAIN</span></div>'
        f'<div class="kpi"><span class="v">{sc.metrics.coverage:.0%}</span><span class="l">判定覆盖</span></div>'
        f'<div class="kpi"><span class="v">{prec_s}</span><span class="l">advisory precision</span></div>'
        f"</div></div></div>"
    )
    anomaly_html = "".join(cards) if cards else "<p class='empty-note'>全部正常,无需关注。</p>"
    return (
        f'<div class="view active" data-view="fleet">{hero}'
        f'<div class="section-label"><span class="dot"></span>需要关注(异常优先)</div>'
        f'<div class="cards">{anomaly_html}</div>'
        f"{collapsed}"
        f'<div id="drawers-{sc.key}" style="display:none">{"".join(drawers)}</div></div>'
    )


def _pipeline_view(sc: ScenarioData) -> str:
    s = sc.summary or {}
    snaps_in = s.get("snapshots_in", 0)
    snaps_clean = s.get("snapshots_clean", snaps_in)
    ev = s.get("evidence_out", len(sc.gold))
    adj = sc.metrics.adjudicated
    stages = [
        ("ACARS/QAR", snaps_in, "航班快照接入"),
        ("译码 + 单位", snaps_in, "确定性译码"),
        ("DQ 质量门", snaps_clean, "通过校验"),
        ("特征 + peer", snaps_clean, "残差 / 同群归一"),
        ("规则 / 异常", ev, "趋势规则判定"),
        ("Evidence / audit", ev, "落审计日志"),
        ("gold-label", adj, "已判定(闭环)"),
    ]
    stage_html = "".join(
        f'<div class="stage"><div class="nm">{name}</div><div class="ct">{ct}</div><div class="ds">{ds}</div></div>'
        for name, ct, ds in stages
    )
    return (
        f'<div class="view" data-view="flow">'
        f'<div class="pipeline"><div class="flow-row">{stage_html}<span class="packet"></span></div>'
        f"<div class='loopnote'>一个航班的信号沿管线被消化为可审计的 Evidence;"
        f"工程师判定 / MRO 真相回流形成 gold-label 闭环,反哺 precision。</div>"
        f'<button class="replay">▶ 重放数据流</button></div></div>'
    )


def _confusion(metrics: Metrics) -> str:
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
                alpha = 0.18 + 0.55 * (value / max_cell)
                cells.append(
                    f'<td class="cell" style="background:rgba(34,211,238,{alpha:.2f})">{value}</td>'
                )
        rows.append(f'<tr class="rowhead"><td>{status}</td>{"".join(cells)}</tr>')
    return (
        f'<table class="matrix"><thead><tr><th>系统 ＼ 真相</th>{head}</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _model_view(sc: ScenarioData) -> str:
    m = sc.metrics
    prec = f"{m.advisory_precision_proxy:.0%}" if m.advisory_precision_proxy is not None else "—"
    tiles = (
        f'<div class="tiles">'
        f'<div class="tile"><div class="v">{m.coverage:.0%}</div><div class="l">判定覆盖率 ({m.adjudicated}/{m.total})</div></div>'
        f'<div class="tile"><div class="v">{prec}</div><div class="l">advisory precision</div></div>'
        f'<div class="tile"><div class="v">{m.advisory_total}</div><div class="l">advisory 总数</div></div>'
        f'<div class="tile"><div class="v">{m.advisory_evaluable}</div><div class="l">可评估(除 INCONCLUSIVE)</div></div>'
        f"</div>"
    )
    return (
        f'<div class="view" data-view="model">{tiles}'
        f'<div class="grid2"><div class="panel"><h3>混淆矩阵(系统状态 × 人工真相)</h3>{_confusion(m)}</div>'
        f"<div class='panel'><h3>说明</h3><div class='reco' style='font-size:13px;line-height:1.6'>"
        f"precision = 真故障+条件异常 / 已判定 advisory(除 INCONCLUSIVE)。<br>"
        f"样本量小(合成数据)时比率无统计意义,仅供闭环演示。</div></div></div></div>"
    )


def _scenario_section(sc: ScenarioData, active: bool) -> str:
    views = [_fleet_view(sc), _pipeline_view(sc), _model_view(sc)]
    labels = [("fleet", "机队总览"), ("flow", "航线流水"), ("model", "模型表现")]
    viewbtns = "".join(
        f'<button class="viewbtn {"active" if i == 0 else ""}" data-view="{v}">{label}</button>'
        for i, (v, label) in enumerate(labels)
    )
    return (
        f'<section class="scenario {"active" if active else ""}" data-name="{sc.key}">'
        f'<div class="nav" style="margin-bottom:18px">{viewbtns}</div>'
        f"{''.join(views)}</section>"
    )


_JS = """
document.querySelectorAll('.sctab').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.sctab').forEach(x=>x.classList.toggle('active',x===t));
  document.querySelectorAll('.scenario').forEach(s=>s.classList.toggle('active',s.dataset.name===t.dataset.target));
});
document.querySelectorAll('.viewbtn').forEach(b=>b.onclick=()=>{
  const sc=b.closest('.scenario');
  sc.querySelectorAll('.viewbtn').forEach(x=>x.classList.toggle('active',x===b));
  const v=b.dataset.view;
  sc.querySelectorAll('.view').forEach(vw=>vw.classList.toggle('active',vw.dataset.view===v));
});
function openDrawer(id){document.querySelectorAll('.drawer').forEach(d=>d.classList.remove('show'));const el=document.getElementById(id);if(el){el.classList.add('show');document.getElementById('ovl').classList.add('show');}}
document.querySelectorAll('[data-drawer]').forEach(el=>el.onclick=()=>openDrawer(el.dataset.drawer));
function closeDrawer(){document.querySelectorAll('.drawer.show').forEach(d=>d.classList.remove('show'));document.getElementById('ovl').classList.remove('show');}
document.getElementById('ovl').onclick=closeDrawer;
document.querySelectorAll('.drawer .x').forEach(x=>x.onclick=closeDrawer);
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeDrawer();});
document.querySelectorAll('.replay').forEach(r=>r.onclick=()=>{
  const row=r.closest('.pipeline').querySelector('.flow-row');
  row.classList.remove('run');void row.offsetWidth;row.classList.add('run');
});
"""


def render_dashboard(scenarios: list[ScenarioData]) -> str:
    """Render the full self-contained mission-console HTML."""
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    alerts = sum(
        1 for sc in scenarios for g in sc.gold if g.evidence.status is EvidenceStatus.ADVISORY
    )
    engines = sum(len(sc.gold) for sc in scenarios)
    sctabs = "".join(
        f'<button class="sctab {"active" if i == 0 else ""}" data-target="{sc.key}">{_esc(sc.name)}</button>'
        for i, sc in enumerate(scenarios)
    )
    sections = "".join(_scenario_section(sc, active=(i == 0)) for i, sc in enumerate(scenarios))
    return (
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>EHM 看板 · Engine Health Guardian</title>"
        f"<style>{CSS}</style></head><body>"
        "<header class='hud'>"
        "<div class='brand'><span class='mark'>◤</span> EHM "
        "<span class='sub'>ENGINE HEALTH GUARDIAN</span></div>"
        f"<div class='nav'>{sctabs}</div>"
        "<div class='spacer'></div>"
        f"<div class='meta'><span class='pillflag'>advisory-only</span>"
        f"<span>{engines} engines · {alerts} alert</span><span>⟳ {generated}</span></div>"
        "</header>"
        f"<main>{sections}"
        "<div class='overlay' id='ovl'></div>"
        "<footer>所有结论均为 advisory-only,不改变放行 / MEL / 维修方案。"
        "数据为合成 / 示例,用于架构与闭环演示。</footer>"
        "</main>"
        f"<script>{_JS}</script>"
        "</body></html>"
    )


__all__ = ["ScenarioData", "render_dashboard"]
