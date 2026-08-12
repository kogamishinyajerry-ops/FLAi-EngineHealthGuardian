"""Dashboard CSS v2 — dark 'mission console' theme.

Inline (no external assets) so the HTML stays self-contained / offline. Designed
for glanceability and progressive disclosure: anomalies glow, normals recede.
"""

CSS = """
:root{
  --bg:#060a14; --panel:#0c1322; --panel2:#111a2e; --ink:#e2e8f0; --muted:#7d8aa3; --faint:#475569;
  --line:#1e293b; --nominal:#34d399; --advisory:#fbbf24; --abstain:#fb7185; --cyan:#22d3ee;
}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",Arial,sans-serif;
  background-image:radial-gradient(1200px 600px at 80% -10%,rgba(34,211,238,.06),transparent),radial-gradient(900px 500px at -10% 110%,rgba(99,102,241,.07),transparent);}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;}

/* ---------- HUD header ---------- */
header.hud{position:sticky;top:0;z-index:20;background:linear-gradient(180deg,rgba(8,12,22,.96),rgba(8,12,22,.82));
  backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:14px 26px;display:flex;align-items:center;gap:20px;flex-wrap:wrap;}
.brand{font-weight:800;font-size:17px;letter-spacing:.02em;display:flex;align-items:center;gap:9px;}
.brand .mark{color:var(--cyan);filter:drop-shadow(0 0 6px rgba(34,211,238,.6));}
.brand .sub{color:var(--muted);font-weight:600;font-size:11px;letter-spacing:.14em;}
.nav{display:flex;gap:4px;background:rgba(255,255,255,.03);padding:4px;border-radius:12px;border:1px solid var(--line);}
.navbtn{background:transparent;border:none;color:var(--muted);padding:7px 15px;border-radius:9px;cursor:pointer;font-size:13px;font-weight:700;transition:.15s;}
.navbtn:hover{color:var(--ink);}
.navbtn.active{background:rgba(34,211,238,.14);color:var(--cyan);box-shadow:inset 0 0 0 1px rgba(34,211,238,.3);}
.spacer{flex:1;}
.meta{color:var(--muted);font-size:12px;display:flex;gap:14px;align-items:center;}
.pillflag{background:rgba(52,211,153,.12);color:var(--nominal);border:1px solid rgba(52,211,153,.3);padding:4px 11px;border-radius:999px;font-size:11px;font-weight:700;}

main{max-width:1240px;margin:0 auto;padding:24px 26px 70px;}
.view{display:none;animation:fade .25s ease;}
.view.active{display:block;}
@keyframes fade{from{opacity:0;transform:translateY(4px);}to{opacity:1;transform:none;}}

/* ---------- hero / fleet health ---------- */
.hero{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:22px;}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px 20px;}
.stat .big{font-size:30px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums;}
.stat .cap{color:var(--muted);font-size:12px;margin-top:7px;letter-spacing:.04em;}
.healthbar{height:12px;border-radius:999px;background:#0a1120;overflow:hidden;margin-top:12px;border:1px solid var(--line);}
.healthbar > i{display:block;height:100%;background:linear-gradient(90deg,var(--nominal),#22d3ee);box-shadow:0 0 12px rgba(52,211,153,.5);}
.kpis{display:flex;gap:22px;flex-wrap:wrap;align-items:center;}
.kpi{display:flex;flex-direction:column;}
.kpi .v{font-size:22px;font-weight:800;font-variant-numeric:tabular-nums;}
.kpi .l{color:var(--muted);font-size:11px;letter-spacing:.05em;}
.kpi.adv .v{color:var(--advisory);} .kpi.abt .v{color:var(--abstain);}

.section-label{display:flex;align-items:center;gap:9px;color:var(--muted);font-size:11px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;margin:22px 0 12px;}
.section-label .dot{width:7px;height:7px;border-radius:50%;background:var(--cyan);}

/* ---------- engine cards (anomaly-first) ---------- */
.cards{display:flex;flex-direction:column;gap:12px;}
.card{position:relative;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:15px 17px;cursor:pointer;transition:.15s;overflow:hidden;}
.card:hover{border-color:#334155;transform:translateY(-1px);}
.card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;}
.card.advisory::before{background:var(--advisory);box-shadow:0 0 16px var(--advisory);}
.card.abstain::before{background:var(--abstain);box-shadow:0 0 16px var(--abstain);}
.card.nominal::before{background:var(--nominal);}
.card.advisory{animation:pulseAmber 2.4s ease-in-out infinite;}
@keyframes pulseAmber{0%,100%{box-shadow:0 0 0 0 rgba(251,191,36,0);}50%{box-shadow:0 0 22px rgba(251,191,36,.16);}}
.card-top{display:flex;align-items:center;gap:11px;flex-wrap:wrap;}
.badge{font-size:10px;font-weight:800;padding:3px 9px;border-radius:6px;letter-spacing:.08em;text-transform:uppercase;}
.badge.advisory{background:rgba(251,191,36,.14);color:var(--advisory);}
.badge.abstain{background:rgba(251,113,133,.14);color:var(--abstain);}
.badge.nominal{background:rgba(52,211,153,.14);color:var(--nominal);}
.esn{font-weight:700;font-size:14px;}
.hyp{color:var(--muted);font-size:12px;}
.spark{flex:1;min-width:140px;height:42px;}
.mro{font-size:11px;font-weight:800;padding:3px 8px;border-radius:6px;}
.mro.true_fault,.mro.conditional_anomaly{background:rgba(251,113,133,.14);color:var(--abstain);}
.mro.nff,.mro.operational{background:rgba(96,165,250,.14);color:#93c5fd;}
.card-mid{display:flex;gap:16px;margin-top:10px;align-items:flex-start;}
.card-mid .reco{flex:1;font-size:13px;color:#cbd5e1;line-height:1.5;}
.card-mid .reco .lbl{color:var(--muted);font-weight:700;}
.card-radar{flex:0 0 auto;display:flex;flex-direction:column;align-items:center;gap:3px;}
.card-radar .cl{color:var(--faint);font-size:9px;letter-spacing:.08em;}

/* collapsed normals */
.collapsed{margin-top:14px;}
.collapsed > summary{cursor:pointer;color:var(--faint);font-size:13px;list-style:none;display:flex;align-items:center;gap:8px;}
.collapsed > summary::-webkit-details-marker{display:none;}
.collapsed > summary::before{content:"▸";color:var(--faint);}
.collapsed[open] > summary::before{content:"▾";}
.dots{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap;}
.ndot{display:flex;align-items:center;gap:7px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:7px 11px;font-size:12px;color:var(--muted);cursor:pointer;}
.ndot .led{width:8px;height:8px;border-radius:50%;background:var(--nominal);box-shadow:0 0 8px var(--nominal);}

/* ---------- drawer (engine detail) ---------- */
.overlay{position:fixed;inset:0;background:rgba(2,6,16,.7);backdrop-filter:blur(3px);z-index:30;display:none;}
.overlay.show{display:block;}
.drawer{position:fixed;top:0;right:0;bottom:0;width:min(560px,92vw);background:var(--panel);border-left:1px solid var(--line);z-index:31;transform:translateX(100%);transition:transform .25s ease;overflow-y:auto;padding:22px 24px;}
.drawer.show{transform:none;}
.drawer .x{position:absolute;top:16px;right:18px;background:none;border:none;color:var(--muted);font-size:22px;cursor:pointer;}
.drawer h2{margin:0 0 4px;font-size:18px;}
.drawer .d-sub{color:var(--muted);font-size:13px;margin-bottom:16px;}
.drawer .blk{margin-top:18px;}
.drawer .blk h4{margin:0 0 8px;color:var(--muted);font-size:11px;letter-spacing:.1em;text-transform:uppercase;}
.bigchart{width:100%;height:120px;}
.dgrid{display:flex;gap:18px;align-items:center;}
.chainpills{display:flex;flex-wrap:wrap;gap:6px;align-items:center;}
.chip{background:#0a1120;border:1px solid var(--line);color:#cbd5e1;padding:4px 9px;border-radius:7px;font-size:11px;}
.chip .k{color:var(--faint);margin-right:4px;}
.arrow{color:var(--faint);}

/* ---------- pipeline (flow view) ---------- */
.pipeline{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:22px;}
.flow-row{display:flex;align-items:stretch;gap:0;flex-wrap:wrap;position:relative;}
.stage{flex:1;min-width:120px;background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:12px 12px;margin:0 4px;position:relative;text-align:center;}
.stage .nm{font-size:12px;font-weight:700;color:#cbd5e1;}
.stage .ct{font-size:20px;font-weight:800;color:var(--cyan);font-variant-numeric:tabular-nums;margin-top:4px;}
.stage .ds{font-size:10px;color:var(--faint);margin-top:3px;}
.stage::after{content:"→";position:absolute;right:-12px;top:50%;transform:translateY(-50%);color:var(--faint);z-index:2;}
.stage:last-child::after{content:"";}
.loopnote{text-align:center;color:var(--muted);font-size:12px;margin-top:18px;}
.replay{margin-top:16px;background:rgba(34,211,238,.1);border:1px solid rgba(34,211,238,.35);color:var(--cyan);padding:8px 16px;border-radius:9px;cursor:pointer;font-weight:700;font-size:13px;}
.replay:hover{background:rgba(34,211,238,.18);}
/* travelling packet */
.packet{width:10px;height:10px;border-radius:50%;background:var(--cyan);box-shadow:0 0 12px var(--cyan);position:absolute;top:50%;left:0;transform:translateY(-50%);opacity:0;}
.flow-row.run .packet{animation:flow 3.2s linear;opacity:1;}
@keyframes flow{0%{left:0;opacity:0;}8%{opacity:1;}92%{opacity:1;}100%{left:100%;opacity:0;}}

/* ---------- model view ---------- */
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px;}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;}
.tile .v{font-size:26px;font-weight:800;font-variant-numeric:tabular-nums;}
.tile .l{color:var(--muted);font-size:11px;margin-top:5px;letter-spacing:.04em;}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;}
.panel h3{margin:0 0 12px;font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);}
.matrix{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums;}
.matrix th,.matrix td{border:1px solid var(--line);padding:7px 6px;text-align:center;}
.matrix th{color:var(--muted);font-weight:700;font-size:10.5px;}
.matrix td.cell{font-weight:800;}
.matrix td.zero{color:var(--faint);}
.matrix tr.rowhead td{font-weight:700;text-align:left;padding-left:9px;}
.grid2{display:grid;grid-template-columns:1.1fr 1fr;gap:18px;}

/* svg styling */
.spark-line{stroke-width:2;stroke-linejoin:round;stroke-linecap:round;}
.spark-area{opacity:.9;}
.thr{stroke:var(--advisory);stroke-width:1;stroke-dasharray:3 3;opacity:.8;}
.base{stroke:var(--faint);stroke-width:1;stroke-dasharray:2 4;}
.rgrid,.raxis{fill:none;stroke:var(--line);stroke-width:1;}
.rpoly{fill:rgba(34,211,238,.18);stroke:var(--cyan);stroke-width:1.6;}
.rlabel{fill:var(--faint);font-size:9px;}

footer{color:var(--faint);font-size:11.5px;margin-top:36px;text-align:center;line-height:1.7;border-top:1px solid var(--line);padding-top:18px;}
.empty-note{color:var(--muted);font-size:13px;}
@media (max-width:880px){.hero{grid-template-columns:1fr;}.tiles{grid-template-columns:repeat(2,1fr);}.grid2{grid-template-columns:1fr;}.drawer{width:100vw;}}
"""
