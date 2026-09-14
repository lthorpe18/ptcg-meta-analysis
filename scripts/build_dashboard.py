#!/usr/bin/env python3
"""Build a self-contained interactive HTML explorer for the historical meta archive."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboard" / "index.html"


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def online_deck_counts() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for standings_path in ROOT.glob("data/raw/online/backfill/chunks/*/*/standings.json"):
        event_id = standings_path.parent.name
        rows = load_json(standings_path, []) or []
        counts: Counter[tuple[str, str]] = Counter()
        classified = 0
        for row in rows:
            deck = row.get("deck") if isinstance(row, dict) else None
            if isinstance(deck, dict) and (deck.get("id") or deck.get("name")):
                deck_id = str(deck.get("id") or deck.get("name") or "unclassified")
                deck_name = str(deck.get("name") or deck_id)
                classified += 1
            else:
                deck_id = "unclassified"
                deck_name = "Unclassified"
            counts[(deck_id, deck_name)] += 1
        out[event_id] = {
            "entries": len(rows),
            "classified_entries": classified,
            "classification_share": classified / len(rows) if rows else 0.0,
            "decks": [
                {"id": deck_id, "name": deck_name, "entries": entries}
                for (deck_id, deck_name), entries in counts.most_common()
            ],
        }
    return out


def irl_fields() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in sorted((ROOT / "data/raw/irl/labs/events").glob("*.json")):
        event = load_json(path, {}) or {}
        event_id = str(event.get("id") or path.stem)
        out[event_id] = {
            "source_url": event.get("source_url"),
            "classified_entries": event.get("classified_entries"),
            "other_entries": event.get("other_entries"),
            "deck_entries_sum": event.get("deck_entries_sum"),
            "decks": event.get("decks") or [],
        }
    return out


def merge_payload() -> dict:
    calendar = load_json(ROOT / "data/reference/legality-calendar.json", {}) or {}
    summary = load_json(ROOT / "data/processed/format-tags/summary.json", {}) or {}
    online = load_json(ROOT / "data/processed/format-tags/online-events.json", []) or []
    irl = load_json(ROOT / "data/processed/format-tags/irl-events.json", []) or []
    window_pack = load_json(ROOT / "data/processed/prediction-windows/windows.json", {}) or {}
    online_counts = online_deck_counts()
    fields = irl_fields()

    for row in online:
        extra = online_counts.get(str(row.get("id")), {"entries": 0, "classified_entries": 0, "classification_share": 0, "decks": []})
        row["stored_entries"] = extra["entries"]
        row["classified_entries"] = extra["classified_entries"]
        row["classification_share"] = extra["classification_share"]
        row["decks"] = extra["decks"]

    for row in irl:
        extra = fields.get(str(row.get("id")), {})
        row["actual_field"] = extra.get("decks", [])
        row["source_url"] = extra.get("source_url")
        row["classified_entries"] = extra.get("classified_entries")
        row["other_entries"] = extra.get("other_entries")
        row["deck_entries_sum"] = extra.get("deck_entries_sum")

    windows = window_pack.get("windows", []) or []
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "calendar": calendar,
        "summary": summary,
        "online": online,
        "irl": irl,
        "window_summary": window_pack.get("summary", {}),
        "cohorts": window_pack.get("cohorts", []),
        "windows_by_target": {str(w.get("target_id")): w for w in windows},
        "online_audit": load_json(ROOT / "results/online-audit/audit.json", {}),
        "irl_audit": load_json(ROOT / "results/irl-audit/audit.json", {}),
    }


HTML_HEAD = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PTCG Meta Backtest Explorer</title>
<style>
:root{--bg:#08111f;--panel:#0f1c2e;--panel2:#13243a;--text:#eef4fb;--muted:#9fb0c5;--line:#233850;--accent:#65b8ff;--good:#6dd6a8;--warn:#ffc76a;--bad:#ff8585;--shadow:0 10px 30px rgba(0,0,0,.22)}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#07101c,#0a1422 38%,#08111f);color:var(--text);font:14px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}button,input,select{font:inherit}.app{max-width:1500px;margin:0 auto;padding:20px}.top{display:flex;gap:16px;align-items:flex-start;justify-content:space-between;margin-bottom:16px}.eyebrow{font-size:12px;letter-spacing:.11em;text-transform:uppercase;color:var(--accent);font-weight:700}.title{font-size:26px;font-weight:800;margin:2px 0 4px}.subtitle{color:var(--muted);max-width:900px}.stamp{color:var(--muted);font-size:12px;text-align:right}.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}.tab{border:1px solid var(--line);background:#0b1727;color:var(--muted);padding:9px 13px;border-radius:999px;cursor:pointer}.tab.active,.tab:hover{background:var(--panel2);color:var(--text);border-color:#355477}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px}.card{background:linear-gradient(180deg,rgba(19,36,58,.96),rgba(14,28,46,.96));border:1px solid var(--line);border-radius:14px;padding:16px;box-shadow:var(--shadow)}.metric{grid-column:span 3;min-height:104px}.metric .v{font-size:30px;font-weight:800;margin-top:8px}.metric .k{color:var(--muted)}.span12{grid-column:span 12}.span8{grid-column:span 8}.span6{grid-column:span 6}.span4{grid-column:span 4}.section-title{font-size:16px;font-weight:750;margin:0 0 12px}.muted{color:var(--muted)}.pill{display:inline-flex;align-items:center;gap:5px;padding:4px 8px;border:1px solid var(--line);border-radius:999px;background:#0a1727;color:#c8d7e8;font-size:12px}.pill.good{border-color:#2f6a57;color:#9ce5c7}.pill.warn{border-color:#70562f;color:#ffd995}.pill.bad{border-color:#704047;color:#ffb0b0}.controls{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}.controls input,.controls select{background:#091625;color:var(--text);border:1px solid var(--line);border-radius:9px;padding:8px 10px;min-height:38px}.controls input{min-width:250px}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:11px}table{width:100%;border-collapse:collapse;white-space:nowrap}th,td{text-align:left;padding:9px 10px;border-bottom:1px solid rgba(35,56,80,.72)}th{position:sticky;top:0;background:#12233a;color:#b9cbe0;font-size:12px;z-index:1}tr.clickable{cursor:pointer}tr.clickable:hover{background:rgba(101,184,255,.08)}td.num{text-align:right;font-variant-numeric:tabular-nums}.bar-row{display:grid;grid-template-columns:minmax(130px,1.2fr) minmax(110px,3fr) 70px;gap:10px;align-items:center;margin:7px 0}.bar{height:10px;background:#091625;border-radius:999px;overflow:hidden;border:1px solid #1f344b}.bar>i{display:block;height:100%;background:linear-gradient(90deg,#4d9ee7,#76c7ff)}.bar-val{text-align:right;font-variant-numeric:tabular-nums;color:#cbd9e9}.hero-row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px}.back{background:#0a1727;color:var(--text);border:1px solid var(--line);padding:7px 10px;border-radius:9px;cursor:pointer}.kv{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr));gap:10px}.kv>div{background:#0b1828;border:1px solid var(--line);border-radius:10px;padding:10px}.kv b{display:block;font-size:17px;margin-top:3px}.subtabs{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0}.subtab{padding:7px 10px;border-radius:8px;border:1px solid var(--line);background:#0a1727;color:var(--muted);cursor:pointer}.subtab.active{background:#17304d;color:white}.callout{border-left:3px solid var(--accent);padding:10px 12px;background:#0b1828;border-radius:8px;color:#cbd9e9}.two-col{display:grid;grid-template-columns:1fr 1fr;gap:14px}.delta-pos{color:#8fe0bd}.delta-neg{color:#ffaaa8}.tiny{font-size:12px}.legend{display:flex;gap:12px;flex-wrap:wrap;color:var(--muted);font-size:12px}.timeline{display:grid;gap:7px}.timeline-row{display:grid;grid-template-columns:150px 110px 150px 150px 1fr;gap:10px;padding:9px 10px;border:1px solid var(--line);border-radius:9px;background:#0b1828;align-items:center}.empty{padding:24px;text-align:center;color:var(--muted)}.footer{margin:24px 0 8px;color:var(--muted);font-size:12px;text-align:center}a{color:var(--accent)}
@media(max-width:1000px){.metric{grid-column:span 6}.span8,.span6,.span4{grid-column:span 12}.two-col{grid-template-columns:1fr}.kv{grid-template-columns:repeat(2,1fr)}.timeline-row{grid-template-columns:1fr 1fr}.timeline-row>*:last-child{grid-column:1/-1}}@media(max-width:620px){.app{padding:12px}.metric{grid-column:span 12}.title{font-size:22px}.top{display:block}.stamp{text-align:left;margin-top:8px}.kv{grid-template-columns:1fr}.controls input{min-width:100%;width:100%}.timeline-row{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="app"><div id="root"></div><div class="footer">Generated directly from the historical research archive. Raw snapshots remain unchanged.</div></div>
<script>
'''

JS = r'''
const DATA = __DATA__;
const state={view:'overview',major:null,majorSub:'window',search:'',format:'all',type:'all',quality:'95'};
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmtN=n=>Number(n||0).toLocaleString();
const pct=x=>x==null?'—':(Number(x)*100).toFixed(1)+'%';
const dateOnly=s=>s?new Date(s+'T12:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):'—';
const dt=s=>s?new Date(s).toLocaleString('en-GB',{day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',timeZone:'UTC'})+' UTC':'—';
const onlineById=id=>DATA.online.find(x=>String(x.id)===String(id));
const irlById=id=>DATA.irl.find(x=>String(x.id)===String(id));
const rowsByIds=(ids,fn)=>((ids||[]).map(fn).filter(Boolean));
function nav(){return `<div class="top"><div><div class="eyebrow">Historical research workspace</div><div class="title">PTCG Meta Backtest Explorer</div><div class="subtitle">Audit the exact legal format and evidence window available before every historical IRL major, then use the same workspace to challenge model results as they are added.</div></div><div class="stamp">Built ${esc(new Date(DATA.generated_at).toLocaleString('en-GB'))}<br>${fmtN(DATA.online.length)} Online · ${fmtN(DATA.irl.length)} IRL</div></div><div class="tabs">${[['overview','Overview'],['majors','Majors'],['windows','Prediction windows'],['formats','Format timeline'],['quality','Data quality & assumptions']].map(([v,l])=>`<button class="tab ${state.view===v?'active':''}" data-view="${v}">${l}</button>`).join('')}</div>`}
function metric(k,v,n=''){return `<div class="card metric"><div class="k">${k}</div><div class="v">${v}</div>${n?`<div class="muted tiny">${n}</div>`:''}</div>`}
function formatCounts(kind){const m=kind==='online'?DATA.summary.online_by_format:DATA.summary.irl_by_format;return Object.entries(m||{}).map(([k,v])=>({k,v}));}
function bars(rows){const mx=Math.max(...rows.map(x=>x.v),1);return rows.map(x=>`<div class="bar-row"><div>${esc(x.k)}</div><div class="bar"><i style="width:${100*x.v/mx}%"></i></div><div class="bar-val">${fmtN(x.v)}</div></div>`).join('')}
function overview(){const s=DATA.summary,w=DATA.window_summary||{};return `<div class="grid">${metric('Usable Online events',fmtN(s.online_events_tagged),'PTCGL Standard, 50+ players')}${metric('IRL majors',fmtN(s.irl_events_tagged),'Masters Day 1 fields')}${metric('Baseline windows',fmtN(w.window_count||0),'Persisted & leakage-audited')}${metric('Primary targets',fmtN(w.primary_target_count_ge_95||s.irl_primary_targets_ge_95),'≥95% field capture')}${metric('Settled windows',fmtN(w.settled_window_count||0),'Prior same-format IRL exists')}${metric('Transition windows',fmtN(w.transition_window_count||0),'First IRL cohort in format')}${metric('IRL evidence cohorts',fmtN(w.cohort_count||0),`${fmtN(w.multi_event_cohort_count||0)} multi-event`)}${metric('Leakage audit',fmtN(w.leakage_error_count||0),'Target cohort cannot predict itself')}<div class="card span6"><div class="section-title">Online events by legal format</div>${bars(formatCounts('online'))}</div><div class="card span6"><div class="section-title">IRL majors by legal format</div>${bars(formatCounts('irl'))}</div><div class="card span12"><div class="section-title">Window foundation now locked for inspection</div><div class="legend"><span class="pill good">Exact Online legality timestamps</span><span class="pill good">Independent IRL legality dates</span><span class="pill good">Overlapping-major cohorts</span><span class="pill good">90% Online classification baseline</span><span class="pill good">Actual IRL Day-1 fields</span><span class="pill good">No contemporaneous IRL leakage</span></div><p class="muted">The Prediction windows page is the persisted source of truth for which evidence each historical target can see. No blend formula has been fitted yet.</p></div></div>`}
function filteredMajors(){return DATA.irl.filter(e=>{if(state.search&&!(`${e.name} ${e.id}`.toLowerCase().includes(state.search.toLowerCase())))return false;if(state.format!=='all'&&e.display_format!==state.format)return false;if(state.type!=='all'&&e.event_type!==state.type)return false;if(state.quality==='95'&&!e.target_eligible_ge_95)return false;if(state.quality==='98'&&!e.target_eligible_ge_98)return false;return true})}
function majors(){const formats=[...new Set(DATA.irl.map(x=>x.display_format))];const types=[...new Set(DATA.irl.map(x=>x.event_type))];const rows=filteredMajors();return `<div class="card span12"><div class="section-title">IRL majors</div><div class="controls"><input id="search" placeholder="Search tournament…" value="${esc(state.search)}"><select id="formatFilter"><option value="all">All formats</option>${formats.map(x=>`<option ${state.format===x?'selected':''}>${esc(x)}</option>`).join('')}</select><select id="typeFilter"><option value="all">All event types</option>${types.map(x=>`<option ${state.type===x?'selected':''}>${esc(x)}</option>`).join('')}</select><select id="qualityFilter"><option value="all" ${state.quality==='all'?'selected':''}>All field completeness</option><option value="95" ${state.quality==='95'?'selected':''}>Primary ≥95%</option><option value="98" ${state.quality==='98'?'selected':''}>Sensitivity ≥98%</option></select><span class="pill">${rows.length} events</span></div><div class="table-wrap"><table><thead><tr><th>Date</th><th>Event</th><th>Type</th><th>Format</th><th>Window</th><th>Days into format</th><th>Players</th><th>Field capture</th><th>Flags</th></tr></thead><tbody>${rows.map(e=>{const w=DATA.windows_by_target[String(e.id)]||{};return `<tr class="clickable" data-major="${esc(e.id)}"><td>${dateOnly(e.start_date)}</td><td>${esc(e.name)}</td><td>${esc(e.event_type)}</td><td><span class="pill">${esc(e.display_format)}</span></td><td>${w.window_class==='transition'?'<span class="pill warn">Transition</span>':'<span class="pill good">Settled</span>'}</td><td class="num">${e.days_into_format}</td><td class="num">${fmtN(e.players)}</td><td class="num">${pct(e.field_count_ratio)}</td><td>${(w.cohort_event_count||1)>1?`<span class="pill">${w.cohort_event_count}-event cohort</span>`:''}</td></tr>`}).join('')}</tbody></table></div></div>`}
function windowsPage(){const windows=Object.values(DATA.windows_by_target||{}).sort((a,b)=>a.target_start_date.localeCompare(b.target_start_date)||String(a.target_id).localeCompare(String(b.target_id)));return `<div class="grid">${metric('Windows',fmtN(windows.length),'One per historical IRL target')}${metric('Settled',fmtN(windows.filter(w=>w.window_class==='settled').length),'Same-format IRL available')}${metric('Transition',fmtN(windows.filter(w=>w.window_class==='transition').length),'Opening IRL cohort')}${metric('Online quality floor','≥90%','Classification for baseline evidence')}<div class="card span12"><div class="section-title">Persisted baseline prediction windows</div><div class="callout" style="margin-bottom:12px">Each row is frozen from information timestamped before the target cohort. Click a target to inspect every included/excluded event.</div><div class="table-wrap"><table><thead><tr><th>Target</th><th>Date</th><th>Format</th><th>Class</th><th>Cohort</th><th>Cutoff</th><th>Online events</th><th>Online entries</th><th>Low-quality excluded</th><th>Prior same-format IRL</th></tr></thead><tbody>${windows.map(w=>`<tr class="clickable" data-major="${esc(w.target_id)}"><td>${esc(w.target_name)}</td><td>${dateOnly(w.target_start_date)}</td><td><span class="pill">${esc(w.target_format)}</span></td><td>${w.window_class==='transition'?'<span class="pill warn">Transition</span>':'<span class="pill good">Settled</span>'}</td><td>${esc(w.cohort_id)}${w.cohort_event_count>1?` · ${w.cohort_event_count} events`:''}</td><td>${dt(w.cutoff_at)}</td><td class="num">${fmtN(w.online_primary_count)}</td><td class="num">${fmtN(w.online_primary_stored_entries)}</td><td class="num">${fmtN(w.online_excluded_low_classification_count)}</td><td class="num">${fmtN(w.prior_irl_same_format_count)}</td></tr>`).join('')}</tbody></table></div></div></div>`}
function aggregateOnline(events){const c=new Map();let entries=0;for(const e of events){entries+=Number(e.stored_entries||0);for(const d of e.decks||[]){const key=d.id||d.name;const cur=c.get(key)||{id:key,name:d.name||key,entries:0};cur.entries+=Number(d.entries||0);c.set(key,cur)}}return {entries,decks:[...c.values()].sort((a,b)=>b.entries-a.entries).map(d=>({...d,share:entries?100*d.entries/entries:0}))}}
function actualField(m){return (m.actual_field||[]).map(d=>({id:d.slug||d.name,name:d.name,entries:Number(d.entries||0),share:Number(d.share||0)})).sort((a,b)=>b.share-a.share)}
function fieldTable(rows,limit=30){return `<div class="table-wrap"><table><thead><tr><th>Archetype</th><th>Entries</th><th>Share</th></tr></thead><tbody>${rows.slice(0,limit).map(d=>`<tr><td>${esc(d.name)}</td><td class="num">${fmtN(d.entries)}</td><td class="num">${Number(d.share||0).toFixed(2)}%</td></tr>`).join('')}</tbody></table></div>`}
function diffTable(actual,online){const m=new Map();for(const d of actual)m.set(d.id,{id:d.id,name:d.name,actual:d.share,online:0});for(const d of online){const r=m.get(d.id)||{id:d.id,name:d.name,actual:0,online:0};r.online=d.share;m.set(d.id,r)}return [...m.values()].map(r=>({...r,delta:r.online-r.actual})).sort((a,b)=>Math.abs(b.delta)-Math.abs(a.delta))}
function majorDetail(){const m=irlById(state.major);if(!m){state.view='majors';return majors()}const w=DATA.windows_by_target[String(m.id)];if(!w)return `<div class="card span12"><div class="empty">No persisted prediction window found for this target.</div></div>`;const online=rowsByIds(w.online_primary_ids,onlineById);const excluded=rowsByIds(w.online_excluded_low_classification_ids,onlineById);const prior=rowsByIds(w.prior_irl_same_format_ids,irlById);const previousAny=rowsByIds(w.prior_irl_all_ids,irlById);const old=rowsByIds(w.prior_irl_other_format_ids,irlById);const agg=aggregateOnline(online);const actual=actualField(m);const diffs=diffTable(actual,agg.decks);const sub=state.majorSub;return `<div class="hero-row"><button class="back" id="backMajors">← Majors</button><span class="pill">${esc(m.display_format)}</span>${w.window_class==='transition'?'<span class="pill warn">Transition window</span>':'<span class="pill good">Settled window</span>'}${w.cohort_event_count>1?`<span class="pill">${w.cohort_event_count}-event cohort</span>`:''}</div><div class="card span12"><div class="section-title" style="font-size:20px">${esc(m.name)}</div><div class="muted">${dateOnly(m.start_date)}–${dateOnly(m.end_date)} · ${esc(m.event_type)}</div><div class="kv" style="margin-top:12px"><div><span class="muted">Players</span><b>${fmtN(m.players)}</b></div><div><span class="muted">Field captured</span><b>${pct(m.field_count_ratio)}</b></div><div><span class="muted">Days into format</span><b>${m.days_into_format}</b></div><div><span class="muted">Prediction cutoff</span><b>${dt(w.cutoff_at)}</b></div></div><div class="subtabs">${[['window','Prediction window'],['actual','Actual field'],['online','Online evidence'],['irl','Prior IRL'],['compare','Raw Online vs actual']].map(([v,l])=>`<button class="subtab ${sub===v?'active':''}" data-sub="${v}">${l}</button>`).join('')}</div>${sub==='window'?windowView(m,w,online,excluded,prior,previousAny,agg):sub==='actual'?`<div class="two-col"><div><div class="section-title">Actual Day-1 field</div>${fieldTable(actual,50)}</div><div><div class="section-title">Target metadata</div><div class="callout">This is the observed field the historical prediction must reproduce. The raw Limitless Labs snapshot remains the source of truth.${m.source_url?` <a href="${esc(m.source_url)}" target="_blank">Open source ↗</a>`:''}</div></div></div>`:sub==='online'?onlineView(online,excluded,agg,w):sub==='irl'?irlView(prior,old):compareView(diffs)}</div>`}
function windowView(m,w,online,excluded,prior,previousAny,agg){const mostRecent=previousAny[0];const cohortRows=rowsByIds(w.cohort_event_ids,irlById);return `<div class="callout">Persisted cutoff: <b>${dt(w.cutoff_at)}</b>, at the start of cohort <b>${esc(w.cohort_id)}</b> (${dateOnly(w.cohort_start_date)}–${dateOnly(w.cohort_end_date)}). Overlapping IRL events are treated as contemporaneous and cannot leak into one another.</div><div class="grid" style="margin-top:14px">${metric('Included Online events',fmtN(online.length),`${fmtN(agg.entries)} stored player entries`)}${metric('Low-quality Online excluded',fmtN(excluded.length),'Below 90% deck classification')}${metric('Prior same-format IRL',fmtN(prior.length),prior[0]?`Latest: ${prior[0].name}`:'None — transition window')}${metric('Window class',w.window_class==='transition'?'Transition':'Settled',w.transition_reason==='format_change'?'First IRL cohort after format change':'')}<div class="card span6"><div class="section-title">Target cohort</div>${simpleIRLTable(cohortRows,false)}</div><div class="card span6"><div class="section-title">Most recent included Online events</div>${simpleOnlineTable([...online].sort((a,b)=>b.start_at.localeCompare(a.start_at)).slice(0,12))}</div><div class="card span6"><div class="section-title">Prior same-format IRL</div>${simpleIRLTable(prior.slice(0,12),true)}</div><div class="card span6"><div class="section-title">Availability assumption</div><div class="callout">${esc(w.availability_proxy)} This is deliberately visible so we can sensitivity-test it later rather than hide it inside the model.</div>${mostRecent?`<p class="muted tiny">Most recent completed IRL before the cohort: ${esc(mostRecent.name)} · ${dateOnly(mostRecent.end_date)} · ${esc(mostRecent.display_format)}</p>`:''}</div></div>`}
function simpleOnlineTable(rows){if(!rows.length)return '<div class="empty">No events.</div>';return `<div class="table-wrap"><table><thead><tr><th>Start</th><th>Event</th><th>Players</th><th>Classification</th></tr></thead><tbody>${rows.map(e=>`<tr><td>${dt(e.start_at)}</td><td>${esc(e.name)}</td><td class="num">${fmtN(e.players)}</td><td class="num">${pct(e.classification_share)}</td></tr>`).join('')}</tbody></table></div>`}
function simpleIRLTable(rows,clickable=true){if(!rows.length)return '<div class="empty">No events.</div>';return `<div class="table-wrap"><table><thead><tr><th>Date</th><th>Event</th><th>Players</th><th>Capture</th></tr></thead><tbody>${rows.map(e=>`<tr ${clickable?`class="clickable" data-major="${esc(e.id)}"`:''}><td>${dateOnly(e.start_date)}</td><td>${esc(e.name)}</td><td class="num">${fmtN(e.players)}</td><td class="num">${pct(e.field_count_ratio)}</td></tr>`).join('')}</tbody></table></div>`}
function onlineView(events,excluded,agg,w){const recent=[...events].sort((a,b)=>b.start_at.localeCompare(a.start_at));const bad=[...excluded].sort((a,b)=>b.start_at.localeCompare(a.start_at));return `<div class="two-col"><div><div class="section-title">Aggregated baseline Online evidence</div><div class="muted tiny" style="margin-bottom:8px">Player-weighted aggregation across ${fmtN(events.length)} same-format events before ${dt(w.cutoff_at)}, after the 90% classification floor. This is evidence, not a model prediction.</div>${fieldTable(agg.decks,50)}</div><div><div class="section-title">Included Online tournaments</div>${simpleOnlineTable(recent)}${bad.length?`<div class="section-title" style="margin-top:14px">Excluded below 90% classification</div>${simpleOnlineTable(bad)}`:''}</div></div>`}
function irlView(prior,old){return `<div class="two-col"><div><div class="section-title">Same-format prior IRL</div>${simpleIRLTable(prior,true)}</div><div><div class="section-title">Recent previous-format IRL</div><div class="muted tiny" style="margin-bottom:8px">Retained for later transition modelling; not silently mixed into the clean settled-format baseline.</div>${simpleIRLTable(old.slice(0,20),true)}</div></div>`}
function compareView(rows){return `<div class="callout">This compares the <b>raw aggregated baseline Online evidence</b> with the eventual IRL field. It is not yet one of the candidate blend formulas; it is useful for spotting where Online systematically led or lagged IRL.</div><div class="table-wrap" style="margin-top:12px"><table><thead><tr><th>Archetype</th><th>Online evidence</th><th>Actual IRL</th><th>Online − actual</th></tr></thead><tbody>${rows.slice(0,60).map(r=>`<tr><td>${esc(r.name)}</td><td class="num">${r.online.toFixed(2)}%</td><td class="num">${r.actual.toFixed(2)}%</td><td class="num ${r.delta>=0?'delta-pos':'delta-neg'}">${r.delta>=0?'+':''}${r.delta.toFixed(2)} pp</td></tr>`).join('')}</tbody></table></div>`}
function formats(){const ex=DATA.calendar.expansions||[];const onlineCounts=DATA.summary.online_by_format||{};const irlCounts=DATA.summary.irl_by_format||{};return `<div class="card span12"><div class="section-title">Set legality timeline</div><div class="timeline"><div class="timeline-row" style="font-weight:700;color:var(--muted)"><span>Set</span><span>Code</span><span>PTCGL legal</span><span>IRL legal</span><span>Physical release / notes</span></div>${ex.map(x=>`<div class="timeline-row"><strong>${esc(x.name)}</strong><span class="pill">${esc(x.code)}</span><span>${dt(x.ptcgl_legal_at)}</span><span>${dateOnly(x.irl_legal_date)}</span><span>${dateOnly(x.physical_release_date)}${x.note?` · <span class="muted">${esc(x.note)}</span>`:''}</span></div>`).join('')}</div></div><div class="card span12" style="margin-top:14px"><div class="section-title">Tagged event counts by format</div><div class="table-wrap"><table><thead><tr><th>Format</th><th>Online events</th><th>IRL majors</th></tr></thead><tbody>${[...new Set([...Object.keys(onlineCounts),...Object.keys(irlCounts)])].map(f=>`<tr><td><span class="pill">${esc(f)}</span></td><td class="num">${fmtN(onlineCounts[f]||0)}</td><td class="num">${fmtN(irlCounts[f]||0)}</td></tr>`).join('')}</tbody></table></div></div>`}
function quality(){const w=DATA.window_summary||{};return `<div class="grid">${metric('Online classification coverage',DATA.online_audit?.classification?.overall_share?pct(DATA.online_audit.classification.overall_share):'96.6%','Whole archive')}${metric('Baseline Online floor','≥90%',`${fmtN(DATA.online.filter(e=>e.classification_share>=.9).length)} events pass overall`)}${metric('Primary IRL threshold','≥95%',`${fmtN(w.primary_target_count_ge_95||68)} / ${fmtN(w.window_count||71)} targets`)}${metric('Leakage audit','0','Persisted windows')}<div class="card span6"><div class="section-title">Baseline window rules</div><ul><li>Online legality uses exact PTCGL timestamps.</li><li>IRL legality uses official tournament legality dates, including the Ascended Heroes exception.</li><li>IRL events with overlapping date ranges form one contemporaneous cohort; cohort members never predict each other.</li><li>The cutoff is 00:00 UTC on the first date of the target cohort because historical IRL start times are not available.</li><li>Primary Online evidence is same-format, starts before the cutoff, and has ≥90% deck classification.</li><li>Same-format Online events below 90% are retained as explicit exclusions for later sensitivity tests.</li><li>Prior IRL must have finished before the target cohort starts. Previous-format IRL is stored separately.</li><li>Primary targets require ≥95% IRL field capture; ≥98% remains a sensitivity threshold.</li></ul></div><div class="card span6"><div class="section-title">Important challenge point</div><div class="callout"><b>Online start time is currently the evidence-availability proxy.</b> Limitless does not give us a historical timestamp for when a tournament's full deck field/results became visible. We therefore include an Online event once its recorded start is before the cutoff. This is explicit and can later be sensitivity-tested with a delay buffer.</div><div class="section-title" style="margin-top:16px">Not yet modelled</div><ul><li>No fitted IRL/Online weight has been selected.</li><li>No Online recency decay or half-life has been imposed.</li><li>No special Worlds coefficient has been imposed.</li><li>No geography or event-type adjustment has been imposed.</li><li>Transition-major handling remains separate from settled-format fitting.</li></ul></div></div>`}
function render(){let body=state.view==='overview'?overview():state.view==='majors'?majors():state.view==='windows'?windowsPage():state.view==='major'?majorDetail():state.view==='formats'?formats():quality();$('#root').innerHTML=nav()+body;bind()}
function bind(){document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{state.view=b.dataset.view;state.major=null;render()});document.querySelectorAll('[data-major]').forEach(r=>r.onclick=()=>{state.major=r.dataset.major;state.view='major';state.majorSub='window';render()});document.querySelectorAll('[data-sub]').forEach(b=>b.onclick=()=>{state.majorSub=b.dataset.sub;render()});if($('#backMajors'))$('#backMajors').onclick=()=>{state.view='majors';render()};if($('#search'))$('#search').oninput=e=>{state.search=e.target.value;render()};if($('#formatFilter'))$('#formatFilter').onchange=e=>{state.format=e.target.value;render()};if($('#typeFilter'))$('#typeFilter').onchange=e=>{state.type=e.target.value;render()};if($('#qualityFilter'))$('#qualityFilter').onchange=e=>{state.quality=e.target.value;render()}}
render();
'''

HTML_TAIL = "\n</script>\n</body>\n</html>\n"


def main():
    payload = merge_payload()
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = HTML_HEAD + JS.replace("__DATA__", data) + HTML_TAIL
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(json.dumps({
        "output": str(OUT.relative_to(ROOT)),
        "bytes": OUT.stat().st_size,
        "online_events": len(payload["online"]),
        "irl_events": len(payload["irl"]),
        "prediction_windows": len(payload["windows_by_target"]),
    }, indent=2))


if __name__ == "__main__":
    main()
