#!/usr/bin/env python3
"""Build the research site as a concise decision-first experience.

The site is intentionally small: one answer page, one evidence page and one method
page. Detailed analysis remains auditable, but is no longer the default experience.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "data" / "processed" / "model-results" / "baselines.json"
WEIGHTS = ROOT / "data" / "processed" / "weight-grid" / "weight-grid.json"
TOP20 = ROOT / "data" / "processed" / "top20-sensitivity" / "top20-sensitivity.json"
OUT = ROOT / "dashboard"

CSS = r"""
:root{--bg:#07111d;--panel:#0d1b2a;--panel2:#102238;--line:#243b55;--text:#f3f6fa;--muted:#9fb0c3;--accent:#69b7ff;--good:#7bd8a6;--warn:#f0c46a;--max:1120px}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:linear-gradient(180deg,#07111d,#081522 55%,#07111d);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.5}
a{color:inherit}header{position:sticky;top:0;z-index:20;background:rgba(7,17,29,.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
.nav{max-width:var(--max);margin:auto;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;gap:20px}.brand{font-weight:800;letter-spacing:-.02em}.navlinks{display:flex;gap:8px}.navlinks a{padding:8px 12px;border-radius:999px;text-decoration:none;color:var(--muted);font-size:14px}.navlinks a.active,.navlinks a:hover{background:var(--panel2);color:var(--text)}
main{max-width:var(--max);margin:auto;padding:54px 24px 80px}.hero{max-width:840px;margin-bottom:54px}.eyebrow{text-transform:uppercase;letter-spacing:.13em;font-size:12px;color:var(--accent);font-weight:800}.hero h1{font-size:clamp(38px,6vw,70px);line-height:1.03;letter-spacing:-.045em;margin:12px 0 18px}.hero p{font-size:21px;color:var(--muted);max-width:760px;margin:0}.lede{font-size:18px;color:var(--muted)}
.section{margin:56px 0}.section h2{font-size:30px;letter-spacing:-.03em;margin:0 0 10px}.section-intro{max-width:760px;color:var(--muted);margin:0 0 24px}.grid{display:grid;gap:18px}.grid.two{grid-template-columns:repeat(2,minmax(0,1fr))}.grid.three{grid-template-columns:repeat(3,minmax(0,1fr))}.card{background:linear-gradient(180deg,var(--panel),#0a1725);border:1px solid var(--line);border-radius:18px;padding:24px}.card h3{margin:0 0 8px;font-size:19px}.card p{margin:0;color:var(--muted)}.big{font-size:44px;line-height:1;font-weight:850;letter-spacing:-.04em;margin:12px 0 8px}.accent{color:var(--accent)}.good{color:var(--good)}.small{font-size:13px;color:var(--muted)}
.answer{border:1px solid #315c7f;background:linear-gradient(135deg,#102944,#0c1d31);padding:28px;border-radius:20px}.answer strong{font-size:25px;display:block;margin-bottom:8px}.answer p{margin:0;color:#c4d4e6;font-size:17px}.subanswer{margin-top:14px;padding-top:14px;border-top:1px solid #31506d;color:#b9c9da}
.score{display:grid;grid-template-columns:160px 1fr 72px;align-items:center;gap:14px;margin:18px 0}.score-label{font-weight:700}.track{height:13px;background:#15273a;border-radius:999px;overflow:hidden}.fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#397fb9,#69b7ff)}.fill.best{background:linear-gradient(90deg,#3d9568,#7bd8a6)}.score-value{text-align:right;font-variant-numeric:tabular-nums;font-weight:800}
.calculator{background:linear-gradient(135deg,#0e2135,#0b1828);border:1px solid #2e5271;border-radius:20px;padding:26px}.slider-row{display:flex;align-items:end;justify-content:space-between;gap:18px;margin-bottom:16px}.slider-row label{font-weight:750}.day-value{font-size:30px;font-weight:850}.weights{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:20px}.weightbox{background:#081522;border:1px solid var(--line);border-radius:16px;padding:18px}.weightbox .number{font-size:36px;font-weight:850;letter-spacing:-.04em}.weightbox span{color:var(--muted)}input[type=range]{width:100%;accent-color:#69b7ff}
.notice{border-left:3px solid var(--warn);padding:4px 0 4px 16px;color:#d8c99f}.pill{display:inline-flex;align-items:center;padding:5px 9px;border-radius:999px;background:#14263a;color:#bcd0e4;font-size:12px;font-weight:700;margin-right:7px}.divider{height:1px;background:var(--line);margin:34px 0}
details{border:1px solid var(--line);border-radius:16px;background:var(--panel);padding:0 18px;margin:16px 0}summary{cursor:pointer;font-weight:750;padding:17px 0}details .inside{padding:0 0 20px}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:14px}table{border-collapse:collapse;width:100%;min-width:720px;font-size:14px}th,td{padding:11px 13px;border-bottom:1px solid var(--line);text-align:left}th{background:#13263b;color:#dbe7f2;position:sticky;top:0}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}tbody tr:last-child td{border-bottom:0}.method{display:grid;grid-template-columns:210px 1fr;gap:24px;padding:23px 0;border-bottom:1px solid var(--line)}.method h3{margin:0}.method p{margin:0;color:var(--muted)}code.formula{display:block;background:#06101b;border:1px solid var(--line);padding:16px;border-radius:12px;font-size:16px;overflow:auto;color:#dceaf6}
footer{max-width:var(--max);margin:auto;padding:24px;color:#71869a;border-top:1px solid var(--line);font-size:13px}
@media(max-width:760px){.nav{align-items:flex-start}.navlinks{gap:2px}.navlinks a{padding:7px 9px}.grid.two,.grid.three,.weights{grid-template-columns:1fr}.score{grid-template-columns:1fr 64px}.score .track{grid-column:1/-1;grid-row:2}.hero p{font-size:18px}.method{grid-template-columns:1fr;gap:8px}main{padding-top:36px}}
"""


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def nav(active: str) -> str:
    links = [("answer","index.html","Answer"),("evidence","evidence.html","Evidence"),("method","method.html","Method")]
    bits = "".join(f'<a class="{"active" if k==active else ""}" href="{href}">{label}</a>' for k,href,label in links)
    return f'<header><div class="nav"><div class="brand">PTCG Meta Research</div><nav class="navlinks">{bits}</nav></div></header>'


def page(title: str, active: str, body: str, script: str = "") -> str:
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} · PTCG Meta Research</title><style>{CSS}</style></head><body>{nav(active)}<main>{body}</main><footer>Historical walk-forward research for PTCG Tools. Decision first; audit trail available when needed.</footer>{script}</body></html>'''


def pct(x):
    return f"{x:.1f}%"


def main():
    baselines = load(BASELINES)
    weights = load(WEIGHTS)
    top20 = load(TOP20)
    t = top20["summary"]
    best = weights["best_in_sample_grid"][0]
    wf = weights["walk_forward"]
    online = t["full_online_only"]["cohort_weighted_accuracy"]
    irl = t["full_irl_only"]["cohort_weighted_accuracy"]
    blend = t["full_best_blend"]["cohort_weighted_accuracy"]
    events = top20["event_count"]
    cohorts = top20["cohort_count"]
    min_days = weights["days_since_major"]["min"]
    max_days = weights["days_since_major"]["max"]
    start = best["start"]
    floor = best["floor"]
    decay = best["decay_per_day"]

    body = f'''
<section class="hero"><div class="eyebrow">Current conclusion</div><h1>Use the latest in-person major as the anchor. Use Online to adjust it.</h1><p>For a settled format, the latest major is by far the strongest signal. Online results add useful information, but the evidence does not support letting them quickly take over.</p></section>
<section class="answer"><strong>What should we do today?</strong><p>For a settled format, start from the latest same-format major and blend in Online results since that major. The strongest historical fit keeps the in-person result as the majority signal throughout the normal gap between majors.</p><div class="subanswer"><b>Brand-new format:</b> use current-format Online results until the first same-format in-person major has happened.</div></section>
<section class="section"><h2>How much better is that?</h2><p class="section-intro">Same settled-format sample for every method: {events} tournaments across {cohorts} independent major weekends. Weekends are weighted once.</p>
<div class="card"><div class="score"><div class="score-label">Online only</div><div class="track"><div class="fill" style="width:{online}%"></div></div><div class="score-value">{pct(online)}</div></div><div class="score"><div class="score-label">Latest major only</div><div class="track"><div class="fill" style="width:{irl}%"></div></div><div class="score-value">{pct(irl)}</div></div><div class="score"><div class="score-label">Best historical blend</div><div class="track"><div class="fill best" style="width:{blend}%"></div></div><div class="score-value good">{pct(blend)}</div></div></div>
<p class="small">Field accuracy measures how close the predicted archetype shares were to the actual Day-1 shares. Higher is better.</p></section>
<section class="section"><h2>What weight would that imply?</h2><p class="section-intro">Use this as a research aid, not yet as a final production rule. It shows the best historical fit we have found so far.</p>
<div class="calculator"><div class="slider-row"><label for="days">Days since the latest same-format major</label><div class="day-value"><span id="daysOut">11</span> days</div></div><input id="days" type="range" min="{min_days}" max="{max_days}" value="11" step="1"><div class="weights"><div class="weightbox"><div class="number good" id="irlOut">69%</div><span>latest in-person major</span></div><div class="weightbox"><div class="number accent" id="onlineOut">31%</div><span>Online results since that major</span></div></div><p class="small" style="margin-bottom:0">Best historical fit: {start*100:.0f}% theoretical starting in-person weight, falling {decay*100:.0f} percentage point per day, with a {floor*100:.0f}% floor. Observed major gaps in this sample: {min_days}–{max_days} days.</p></div></section>
<section class="section"><h2>What are we ultimately trying to predict?</h2><div class="grid two"><div class="card"><h3>Any decks you care about</h3><p>The eventual tool should let you choose any set of archetypes — 5, 12, 20, whatever — and return an expected Day-1 share for each one.</p></div><div class="card"><h3>No renormalising your selection</h3><p>If the decks you choose are predicted to make up 63% of the field, they stay at 63%. The rest of the field remains the rest of the field.</p></div></div></section>
<section class="section"><h2>How certain are we?</h2><div class="notice">The direction is clearer than the exact formula. In the expanding walk-forward check, the newly tuned rule scored {wf['tuned_rule_mean_accuracy']:.2f}% while the current decay rule scored {wf['current_decay_mean_accuracy']:.2f}%. So the evidence supports “in-person first, Online adjustment” more strongly than it supports one exact decay curve.</div></section>'''

    script = f'''<script>(()=>{{const s=document.getElementById('days'),d=document.getElementById('daysOut'),i=document.getElementById('irlOut'),o=document.getElementById('onlineOut');const start={start},floor={floor},decay={decay};function draw(){{const days=Number(s.value);const w=Math.max(floor,Math.min(start,start-decay*days));d.textContent=days;i.textContent=Math.round(w*100)+'%';o.textContent=Math.round((1-w)*100)+'%';}}s.addEventListener('input',draw);draw();}})();</script>'''

    rows = "".join(f'<tr><td>{html.escape(r["target_name"])}</td><td class="num">{r["days_since_major"]}</td><td class="num">{r["full_online_only"]:.1f}%</td><td class="num">{r["full_irl_only"]:.1f}%</td><td class="num">{r["full_best_blend"]:.1f}%</td></tr>' for r in top20["rows"])
    evidence = f'''
<section class="hero"><div class="eyebrow">Evidence</div><h1>The latest major does most of the work. Online improves it a little.</h1><p>The important result is the gap between Online-only and in-person-based methods. The precise best blend is a smaller, less certain optimisation problem.</p></section>
<section class="section"><h2>Settled-format comparison</h2><div class="grid three"><div class="card"><h3>Online only</h3><div class="big">{pct(online)}</div><p>Useful movement signal, but a poor replacement for the latest major.</p></div><div class="card"><h3>Latest major only</h3><div class="big">{pct(irl)}</div><p>Most of the predictive power is already here.</p></div><div class="card"><h3>Best historical blend</h3><div class="big good">{pct(blend)}</div><p>Latest major plus Online movement since that major.</p></div></div><p class="small">Complete-case settled sample: {events} tournaments / {cohorts} independent weekends.</p></section>
<section class="section"><h2>What survives the robustness checks?</h2><div class="grid two"><div class="card"><h3>Long-tail deck noise is not driving the result</h3><p>When the actual top 20 decks are kept individually and the long tail is grouped into Other as a diagnostic, the ordering is unchanged: blend &gt; latest major &gt; Online only.</p></div><div class="card"><h3>The exact curve is not settled</h3><p>The in-sample best blend reaches {blend:.2f}%, but walk-forward tuning did not beat the existing production decay rule. Treat the formula parameters as exploratory.</p></div></div></section>
<section class="section"><h2>Event-by-event audit</h2><p class="section-intro">This is intentionally hidden by default. It is here to challenge the conclusion, not to dominate the page.</p><details><summary>Show the {events} settled tournaments used in the like-for-like comparison</summary><div class="inside"><div class="table-wrap"><table><thead><tr><th>Tournament</th><th class="num">Days since major</th><th class="num">Online only</th><th class="num">Latest major</th><th class="num">Best blend</th></tr></thead><tbody>{rows}</tbody></table></div></div></details></section>'''

    summary = baselines["summary"]
    method = f'''
<section class="hero"><div class="eyebrow">Method</div><h1>Predict the Day-1 share of each archetype as closely as possible.</h1><p>The analysis is built around the same thing the eventual tool needs to do: estimate deck shares before an event, using only evidence that would have been available at the time.</p></section>
<section class="section"><div class="method"><h3>What is scored?</h3><p>Each method produces a full predicted field distribution. We compare every archetype's predicted share with its actual Day-1 share.</p></div><div class="method"><h3>Headline score</h3><div><code class="formula">Field Accuracy = 100% − ½ × Σ | predicted share − actual share |</code><p style="margin-top:10px">The ½ is needed because moving field share from one deck to another creates an equal over-prediction and under-prediction.</p></div></div><div class="method"><h3>Why this matches the tool</h3><p>You may ultimately ask the product for any set of decks. Their predicted percentages do not change depending on how many you chose, and they are not renormalised to total 100%.</p></div><div class="method"><h3>No future information</h3><p>Every historical prediction is frozen before the target major. Overlapping majors are treated as one contemporaneous cohort so they cannot predict one another.</p></div><div class="method"><h3>Settled format</h3><p>A same-format in-person major already exists. This is where we compare Online-only, latest-major-only and blended predictions.</p></div><div class="method"><h3>New / transition format</h3><p>No completed same-format in-person major exists yet, so the clean baseline is current-format Online evidence only.</p></div><div class="method"><h3>Data quality</h3><p>{summary['primary_target_count']} primary historical targets meet the in-person field-capture threshold; {summary['primary_settled_count']} are settled and {summary['primary_transition_count']} are transition targets. The strict like-for-like settled comparison currently has {summary['complete_case_settled_event_count']} events across {summary['complete_case_settled_cohort_count']} independent cohorts.</p></div></section>'''

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page("Answer", "answer", body, script), encoding="utf-8")
    (OUT / "evidence.html").write_text(page("Evidence", "evidence", evidence), encoding="utf-8")
    (OUT / "method.html").write_text(page("Method", "method", method), encoding="utf-8")
    (OUT / "models.html").write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=evidence.html"><title>Moved</title><a href="evidence.html">Continue to evidence</a>', encoding="utf-8")
    print(f"Built concise research site in {OUT}")


if __name__ == "__main__":
    main()
