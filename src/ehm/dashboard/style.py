"""Dashboard CSS — embedded inline so the HTML is fully self-contained / offline.

A clean light theme with a dark slate top bar, status color-coding, card layout.
Kept as a Python string constant (no template engine, no external assets).
"""

CSS = """
:root{
  --nominal:#10b981; --advisory:#f59e0b; --abstain:#64748b;
  --bg:#f1f5f9; --card:#ffffff; --ink:#0f172a; --muted:#64748b; --line:#e2e8f0;
  --ok:#10b981; --warn:#f59e0b; --bad:#ef4444;
}
*{box-sizing:border-box;}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue","PingFang SC","Microsoft YaHei",Arial,sans-serif;background:var(--bg);color:var(--ink);}
header.topbar{background:linear-gradient(135deg,#0f172a,#1e293b);color:#fff;padding:16px 28px;position:sticky;top:0;z-index:10;box-shadow:0 2px 14px rgba(0,0,0,.18);display:flex;align-items:center;gap:18px;flex-wrap:wrap;}
.brand{font-size:19px;font-weight:800;display:flex;align-items:center;gap:10px;letter-spacing:.01em;}
.brand .shield{font-size:22px;}
.tabs{display:flex;gap:6px;}
.tab{background:rgba(255,255,255,.08);border:none;color:#cbd5e1;padding:7px 15px;border-radius:9px;cursor:pointer;font-size:13px;font-weight:600;transition:.15s;}
.tab:hover{background:rgba(255,255,255,.16);}
.tab.active{background:#fff;color:#0f172a;}
.spacer{flex:1;}
.badge{background:rgba(16,185,129,.18);color:#6ee7b7;padding:5px 12px;border-radius:999px;font-size:12px;font-weight:700;}
.gen{color:#94a3b8;font-size:12px;}
main{max-width:1200px;margin:0 auto;padding:24px 28px 60px;}
.tiles{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:6px;}
.tile{background:var(--card);border-radius:14px;padding:15px 17px;box-shadow:0 1px 3px rgba(15,23,42,.07);}
.tile .v{font-size:27px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums;}
.tile .l{color:var(--muted);font-size:11px;margin-top:6px;text-transform:uppercase;letter-spacing:.05em;}
.tile.acc .v{color:var(--advisory);}
.tile.warn .v{color:var(--abstain);}
.filters{display:flex;gap:8px;margin:18px 0 12px;}
.chip{background:#fff;border:1px solid var(--line);color:var(--muted);padding:6px 13px;border-radius:999px;cursor:pointer;font-size:12px;font-weight:600;transition:.15s;}
.chip:hover{border-color:#94a3b8;}
.chip.active{background:#0f172a;color:#fff;border-color:#0f172a;}
.section-title{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin:20px 0 10px;}
.cards{display:flex;flex-direction:column;gap:11px;}
.card{background:var(--card);border-radius:14px;padding:15px 18px;box-shadow:0 1px 3px rgba(15,23,42,.07);border-left:4px solid var(--abstain);}
.card.advisory{border-left-color:var(--advisory);}
.card.nominal{border-left-color:var(--nominal);}
.card.head{display:flex;align-items:center;gap:11px;flex-wrap:wrap;}
.status{font-size:10.5px;font-weight:800;padding:3px 9px;border-radius:999px;text-transform:uppercase;letter-spacing:.06em;}
.status.advisory{background:#fef3c7;color:#92400e;}
.status.nominal{background:#d1fae5;color:#065f46;}
.status.abstain{background:#e2e8f0;color:#334155;}
.esn{font-weight:700;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:14px;}
.hyp{color:var(--muted);font-size:12px;}
.metric-line{color:#475569;font-size:13px;margin-top:9px;font-family:ui-monospace,monospace;}
.card-body{display:grid;grid-template-columns:1fr 240px;gap:18px;margin-top:6px;align-items:start;}
.conf{display:flex;flex-direction:column;gap:6px;}
.conf .row{display:flex;align-items:center;gap:8px;}
.conf .cl{width:78px;font-size:11px;color:var(--muted);text-transform:capitalize;}
.conf .bar{flex:1;height:8px;background:var(--line);border-radius:999px;overflow:hidden;}
.conf .bar > i{display:block;height:100%;border-radius:999px;}
.conf .cv{width:38px;font-size:11px;text-align:right;font-variant-numeric:tabular-nums;color:var(--muted);}
.reco{margin-top:11px;padding:10px 13px;background:#f8fafc;border-radius:10px;font-size:13px;line-height:1.5;}
.reco.abstain{background:#f1f5f9;color:#475569;}
.reco .lbl{font-weight:700;margin-right:6px;}
.tag{display:inline-block;font-size:11px;font-weight:800;padding:3px 9px;border-radius:7px;margin-right:6px;vertical-align:middle;}
.tag.true_fault,.tag.conditional_anomaly{background:#fee2e2;color:#991b1b;}
.tag.nff,.tag.operational{background:#dbeafe;color:#1e40af;}
.tag.sensor_issue{background:#fef3c7;color:#92400e;}
.tag.inconclusive{background:#e2e8f0;color:#334155;}
.finding{color:#475569;font-size:12.5px;margin-top:6px;}
details.chain{margin-top:10px;border-top:1px dashed var(--line);padding-top:8px;}
summary{cursor:pointer;font-size:12px;color:var(--muted);font-weight:700;outline:none;}
.chain-pills{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:9px;}
.pill{background:#eef2ff;color:#3730a3;padding:3px 9px;border-radius:999px;font-size:11px;font-family:ui-monospace,monospace;}
.pill.empty{background:#f1f5f9;color:#94a3b8;}
.arrow{color:#94a3b8;font-size:12px;}
.grid2{display:grid;grid-template-columns:1.1fr 1fr;gap:20px;margin-top:26px;align-items:start;}
.panel{background:var(--card);border-radius:14px;padding:16px 18px;box-shadow:0 1px 3px rgba(15,23,42,.07);}
.panel h3{margin:0 0 12px;font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);}
.matrix{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums;}
.matrix th,.matrix td{border:1px solid var(--line);padding:6px 5px;text-align:center;}
.matrix th{background:#f8fafc;color:var(--muted);font-weight:700;font-size:10.5px;}
.matrix td.cell{font-weight:800;}
.matrix td.zero{color:#cbd5e1;font-weight:400;}
.matrix tr.rowhead td{background:#f8fafc;font-weight:700;text-align:left;padding-left:9px;}
.flow-pills{display:flex;flex-wrap:wrap;align-items:center;gap:5px;}
.empty-note{color:var(--muted);font-size:13px;}
footer{color:var(--muted);font-size:11.5px;margin-top:34px;text-align:center;line-height:1.6;}
.hidden{display:none !important;}
@media (max-width:900px){.tiles{grid-template-columns:repeat(2,1fr);} .grid2{grid-template-columns:1fr;} .card-body{grid-template-columns:1fr;}}
"""
