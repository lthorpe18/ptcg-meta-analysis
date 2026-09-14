#!/usr/bin/env python3
"""Build the baseline model-comparison page and link it from the explorer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data" / "processed" / "model-results" / "baselines.json"
OUT = ROOT / "dashboard" / "models.html"
INDEX = ROOT / "dashboard" / "index.html"


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PTCG Baseline Model Comparison</title>
<style>
:root{--bg:#08111f;--panel:#0f1c2e;--panel2:#13243a;--text:#eef4fb;--muted:#9fb0c5;--line:#233850;--accent:#65b8ff;--good:#6dd6a8;--warn:#ffc76a;--bad:#ff8585;--shadow:0 10px 30px rgba(0,0,0,.22)}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#07101c,#0a1422 38%,#08111f);color:var(--text);font:14px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.app{max-width:1500px;margin:0 auto;padding:20px}button,input,select{font:inherit}.top{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}.eyebrow{font-size:12px;letter-spacing:.11em;text-transform:uppercase;color:var(--accent);font-weight:700}.title{font-size:26px;font-weight:800;margin:2px 0 4px}.subtitle,.muted{color:var(--muted)}.stamp{font-size:12px;color:var(--muted);text-align:right}.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}.tab{display:inline-block;border:1px solid var(--line);background:#0b1727;color:var(--muted);padding:9px 13px;border-radius:999px;text-decoration:none}.tab.active,.tab:hover{background:var(--panel2);color:var(--text);border-color:#355477}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px}.card{background:linear-gradient(180deg,rgba(19,36,58,.96),rgba(14,28,46,.96));border:1px solid var(--line);border-radius:14px;padding:16px;box-shadow:var(--shadow)}.metric{grid-column:span 3;min-height:104px}.metric .k{color:var(--muted)}.metric .v{font-size:30px;font-weight:800;margin-top:8px}.span12{grid-column:span 12}.span8{grid-column:span 8}.span6{grid-column:span 6}.span4{grid-column:span 4}.section-title{font-size:16px;font-weight:750;margin:0 0 12px}.tiny{font-size:12px}.callout{border-left:3px solid var(--accent);padding:10px 12px;background:#0b1828;border-radius:8px;color:#cbd9e9}.controls{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}.controls input,.controls select{background:#091625;color:var(--text);border:1px solid var(--line);border-radius:9px;padding:8px 10px;min-height:38px}.controls input{min-width:280px}.pill{display:inline-flex;align-items:center;padding:4px 8px;border:1px solid var(--line);border-radius:999px;background:#0a1727;color:#c8d7e8;font-size:12px}.pill.good{border-color:#2f6a57;color:#9ce5c7}.pill.warn{border-color:#70562f;color:#ffd995}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:11px}table{width:100%;border-collapse:collapse;white-space:nowrap}th,td{text-align:left;padding:9px 10px;border-bottom:1px solid rgba(35,56,80,.72)}th{position:sticky;top:0;background:#12233a;color:#b9cbe0;font-size:12px;z-index:1}td.num{text-align:right;font-variant-numeric:tabular-nums}tr.clickable{cursor:pointer}tr.clickable:hover{background:rgba(101,184,255,.08)}.goodtxt{color:#8fe0bd}.badtxt{color:#ffaaa8}.detail{margin-top:14px}.kv{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr));gap:10px;margin:12px 0}.kv>div{background:#0b1828;border:1px solid var(--line);border-radius:10px;padding:10px}.kv b{display:block;font-size:17px;margin-top:3px}.model-card{margin-bottom:12px}.model-head{display:flex;justify-content:space-between;gap:12px;align-items:center}.footer{margin:24px 0 8px;color:var(--muted);font-size:12px;text-align:center}a{color:var(--accent)}
@media(max-width:1000px){.metric{grid-column:span 6}.span8,.span6,.span4{grid-column:span 12}.kv{grid-template-columns:repeat(2,1fr)}}@media(max-width:620px){.app{padding:12px}.metric{grid-column:span 12}.title{font-size:22px}.top{display:block}.stamp{text-align:left;margin-top:8px}.kv{grid-template-columns:1fr}.controls input{min-width:100%;width:100%}}
</style>
</head>
<body><div class="app"><div id="root"></div><div class="footer">Generated from frozen historical prediction windows. Raw source snapshots remain unchanged.</div></div>
<script>
const DATA=__DATA__;
const state={class:'settled',search:'',type:'all',selected:null,detailModel:'current_v2_1'};
const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const f1=x=>x==null?'—':Number(x).toFixed(1);const f2=x=>x==null?'—':Number(x).toFixed(2);const fmt=n=>Number(n||0).toLocaleString();
const dateOnly=s=>s?new Date(s+'T12:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):'—';
const modelOrder=['online_only','irl_only','fifty_fifty','current_v2_1'];
const labels=Object.fromEntries(modelOrder.map(k=>[k,DATA.summary.models[k].model.label]));
function metric(k,v,n=''){return `<div class="card metric"><div class="k">${k}</div><div class="v">${v}</div>${n?`<div class="muted tiny">${n}</div>`:''}</div>`}
function header(){return `<div class="top"><div><div class="eyebrow">Historical research workspace</div><div class="title">Baseline Model Comparison</div><div class="subtitle">Compare simple historical predictions against the actual Day-1 field, tournament by tournament and major-weekend cohort by major-weekend cohort.</div></div><div class="stamp">Built ${esc(new Date(DATA.summary.generated_at).toLocaleString('en-GB'))}<br>${fmt(DATA.summary.primary_target_count)} primary targets</div></div><div class="tabs"><a class="tab" href="index.html">Explorer</a><a class="tab active" href="models.html">Model comparison</a></div>`}
function summaryTable(){const rows=modelOrder.map(k=>{const s=DATA.summary.models[k],m=s.settled_primary;return `<tr><td><b>${esc(s.model.label)}</b><div class="muted tiny">${esc(s.model.description)}</div></td><td class="num">${f1(m.mean_field_accuracy_pct)}%</td><td class="num">${f1(m.cohort_mean_field_accuracy_pct)}%</td><td class="num">${f1(m.median_field_accuracy_pct)}%</td><td class="num">${f2(m.mean_mae_pp)}</td><td class="num">${fmt(m.event_count)}</td><td class="num">${fmt(m.cohort_count)}</td><td class="num">${f1(s.event_wins_complete_case)}</td><td class="num">${f1(s.cohort_wins_complete_case)}</td></tr>`}).join('');return `<div class="card span12"><div class="section-title">Settled-format model comparison</div><div class="muted tiny" style="margin-bottom:10px">Primary ≥95% targets. Event accuracy weights every tournament equally; cohort accuracy first averages tournaments within a contemporaneous major weekend, then weights each weekend equally.</div><div class="table-wrap"><table><thead><tr><th>Model</th><th>Mean event accuracy</th><th>Mean cohort accuracy</th><th>Median event</th><th>Mean MAE (pp)</th><th>Events</th><th>Cohorts</th><th>Event wins*</th><th>Cohort wins*</th></tr></thead><tbody>${rows}</tbody></table></div><div class="muted tiny" style="margin-top:8px">* Wins use the complete-case settled comparison set; ties split a win.</div></div>`}
function filtered(){return DATA.targets.filter(r=>{if(!r.target_eligible_ge_95)return false;if(state.class!=='all'&&r.window_class!==state.class)return false;if(state.type!=='all'&&r.target_event_type!==state.type)return false;if(state.search&&!(`${r.target_name} ${r.target_format}`.toLowerCase().includes(state.search.toLowerCase())))return false;return true})}
function scoreCell(r,k){const m=r.models[k];return m&&m.available?`${f1(m.field_accuracy_pct)}%`:'—'}
function eventTable(){const types=[...new Set(DATA.targets.map(r=>r.target_event_type))].sort();const rows=filtered();return `<div class="card span12"><div class="section-title">Tournament-by-tournament results</div><div class="controls"><input id="search" placeholder="Search tournament or format…" value="${esc(state.search)}"><select id="class"><option value="settled" ${state.class==='settled'?'selected':''}>Settled</option><option value="transition" ${state.class==='transition'?'selected':''}>Transition</option><option value="all" ${state.class==='all'?'selected':''}>All</option></select><select id="type"><option value="all">All event types</option>${types.map(t=>`<option ${state.type===t?'selected':''}>${esc(t)}</option>`).join('')}</select><span class="pill">${rows.length} targets</span></div><div class="table-wrap"><table><thead><tr><th>Date</th><th>Target</th><th>Format</th><th>Class</th><th>Cohort</th>${modelOrder.map(k=>`<th>${esc(labels[k])}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr class="clickable" data-target="${esc(r.target_id)}"><td>${dateOnly(r.target_start_date)}</td><td>${esc(r.target_name)}</td><td><span class="pill">${esc(r.target_format)}</span></td><td>${r.window_class==='transition'?'<span class="pill warn">Transition</span>':'<span class="pill good">Settled</span>'}</td><td>${esc(r.cohort_id)}${r.cohort_event_count>1?` · ${r.cohort_event_count} events`:''}</td>${modelOrder.map(k=>`<td class="num">${scoreCell(r,k)}</td>`).join('')}</tr>`).join('')}</tbody></table></div></div>`}
function pairwise(){const p=DATA.summary.pairwise_v2_1_vs_50_50;const d=p.mean_v2_1_minus_50_50_pp;return `<div class="card span6"><div class="section-title">Current v2.1 vs 50/50</div><div class="kv"><div><span class="muted">v2.1 wins</span><b>${fmt(p.v2_1_wins)}</b></div><div><span class="muted">50/50 wins</span><b>${fmt(p.fifty_fifty_wins)}</b></div><div><span class="muted">Ties</span><b>${fmt(p.ties)}</b></div><div><span class="muted">Mean v2.1 advantage</span><b class="${d>=0?'goodtxt':'badtxt'}">${d>=0?'+':''}${f2(d)} pp</b></div></div><div class="muted tiny">${fmt(p.event_count)} complete-case settled targets.</div></div>`}
function transition(){const t=DATA.summary.models.online_only.transition_primary;return `<div class="card span6"><div class="section-title">Transition baseline</div><div class="callout">Transition windows deliberately use <b>Online only</b>. Previous-format IRL is not carried forward in this clean baseline.</div><div class="kv"><div><span class="muted">Targets</span><b>${fmt(t.event_count)}</b></div><div><span class="muted">Mean accuracy</span><b>${f1(t.mean_field_accuracy_pct)}%</b></div><div><span class="muted">Cohort mean</span><b>${f1(t.cohort_mean_field_accuracy_pct)}%</b></div><div><span class="muted">Median</span><b>${f1(t.median_field_accuracy_pct)}%</b></div></div></div>`}
function detail(){if(!state.selected)return '';const r=DATA.targets.find(x=>String(x.target_id)===String(state.selected));if(!r)return '';const opts=modelOrder.map(k=>`<option value="${k}" ${state.detailModel===k?'selected':''}>${esc(labels[k])}</option>`).join('');const chosen=r.models[state.detailModel];const cards=modelOrder.map(k=>{const m=r.models[k];if(!m.available)return `<div class="card model-card"><div class="model-head"><b>${esc(labels[k])}</b><span class="muted">Unavailable</span></div><div class="muted tiny">${esc(m.reason||'')}</div></div>`;const w=m.weights||{};return `<div class="card model-card"><div class="model-head"><b>${esc(labels[k])}</b><b>${f1(m.field_accuracy_pct)}%</b></div><div class="muted tiny">IRL ${f1((w.irl||0)*100)}% · Online ${f1((w.online||0)*100)}% · ${fmt(m.irl_event_ids.length)} IRL events · ${fmt(m.online_event_ids.length)} Online events</div><div class="tiny" style="margin-top:6px">Biggest miss: ${esc(m.biggest_miss?.name||'—')} · ${m.biggest_miss?`${m.biggest_miss.delta_pp>=0?'+':''}${f2(m.biggest_miss.delta_pp)} pp`:'—'}</div></div>`}).join('');let table='';if(chosen&&chosen.available){table=`<div class="controls"><select id="detailModel">${opts}</select></div><div class="table-wrap"><table><thead><tr><th>Archetype</th><th>Predicted</th><th>Actual</th><th>Delta</th></tr></thead><tbody>${chosen.prediction.map(x=>`<tr><td>${esc(x.name)}</td><td class="num">${f2(x.predicted_pct)}%</td><td class="num">${f2(x.actual_pct)}%</td><td class="num ${x.delta_pp>=0?'goodtxt':'badtxt'}">${x.delta_pp>=0?'+':''}${f2(x.delta_pp)} pp</td></tr>`).join('')}</tbody></table></div>`}else{table=`<div class="controls"><select id="detailModel">${opts}</select></div><div class="callout">${esc(chosen?.reason||'This model is unavailable for this target.')}</div>`}return `<div class="card span12 detail"><div class="model-head"><div><div class="section-title" style="margin-bottom:3px">${esc(r.target_name)}</div><div class="muted">${dateOnly(r.target_start_date)} · ${esc(r.target_format)} · ${esc(r.cohort_id)}</div></div><button id="close" style="background:#0a1727;color:var(--text);border:1px solid var(--line);border-radius:9px;padding:7px 10px;cursor:pointer">Close</button></div><div class="kv"><div><span class="muted">Window</span><b>${esc(r.window_class)}</b></div><div><span class="muted">Days into format</span><b>${r.days_into_format??'—'}</b></div><div><span class="muted">Days since prior major</span><b>${r.days_since_major??'—'}</b></div><div><span class="muted">Online since prior major</span><b>${fmt(r.online_since_major_event_count)}</b></div></div><div class="grid">${cards}</div><div class="section-title" style="margin-top:16px">Prediction vs actual</div>${table}</div>`}
function rules(){const p=DATA.summary.scoring_policy;return `<div class="card span12"><div class="section-title">Baseline rules used for this page</div><div class="callout"><b>${esc(p.metric)}</b></div><ul><li>${esc(p.distribution_scope)}</li><li>${esc(p.identity_key)}</li><li>Transition: ${esc(p.transition_policy)}</li><li>IRL baseline: ${esc(p.settled_irl_scope)}</li><li>Online-only baseline: ${esc(p.settled_online_only_scope)}</li><li>Blended Online scope: ${esc(p.settled_blend_online_scope)}</li><li>v2.1: ${esc(p.current_v2_1_weights)}</li></ul></div>`}
function render(){const s=DATA.summary;$('#root').innerHTML=header()+`<div class="grid">${metric('Primary targets',fmt(s.primary_target_count),'≥95% field capture')}${metric('Settled targets',fmt(s.primary_settled_count),'Model comparison pool')}${metric('Transition targets',fmt(s.primary_transition_count),'Online-only baseline')}${metric('Complete-case cohorts',fmt(s.complete_case_settled_cohort_count),'For fair model wins')}${summaryTable()}${pairwise()}${transition()}${eventTable()}${detail()}${rules()}</div>`;bind()}
function bind(){document.querySelectorAll('[data-target]').forEach(r=>r.onclick=()=>{state.selected=r.dataset.target;state.detailModel='current_v2_1';render();setTimeout(()=>document.querySelector('.detail')?.scrollIntoView({behavior:'smooth',block:'start'}),0)});if($('#class'))$('#class').onchange=e=>{state.class=e.target.value;state.selected=null;render()};if($('#type'))$('#type').onchange=e=>{state.type=e.target.value;state.selected=null;render()};if($('#search'))$('#search').onchange=e=>{state.search=e.target.value;state.selected=null;render()};if($('#detailModel'))$('#detailModel').onchange=e=>{state.detailModel=e.target.value;render()};if($('#close'))$('#close').onclick=()=>{state.selected=null;render()}}
render();
</script></body></html>'''


def add_index_link() -> None:
    if not INDEX.exists():
        return
    text = INDEX.read_text(encoding="utf-8")
    marker = "render();"
    pos = text.rfind(marker)
    if pos < 0:
        return
    injection = r'''const _baselineBind=bind;
bind=function(){_baselineBind();const tabs=document.querySelector('.tabs');if(tabs&&!tabs.querySelector('.models-link')){const a=document.createElement('a');a.href='models.html';a.className='tab models-link';a.textContent='Model comparison';a.style.textDecoration='none';tabs.appendChild(a);}};
'''
    text = text[:pos] + injection + text[pos:]
    INDEX.write_text(text, encoding="utf-8")


def main() -> None:
    data = load_json(RESULTS, {}) or {}
    if not data.get("targets"):
        raise SystemExit("Baseline model results are required first.")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
    add_index_link()
    print(json.dumps({
        "output": str(OUT.relative_to(ROOT)),
        "bytes": OUT.stat().st_size,
        "targets": len(data.get("targets") or []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))


if __name__ == "__main__":
    main()
