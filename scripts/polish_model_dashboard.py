#!/usr/bin/env python3
"""Turn the model page into a senior-stakeholder prediction summary.

The default view answers one question in plain English: how should we predict the
next tournament meta? Detailed model evidence remains available, but it is
secondary and collapsed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / "dashboard" / "models.html"


def main() -> None:
    source = PAGE.read_text(encoding="utf-8")

    data_match = re.search(r"const DATA=(.*?);const state=", source, re.S)
    if not data_match:
        raise RuntimeError("Could not find embedded model data")
    data = json.loads(data_match.group(1))
    target_count = data["summary"]["primary_target_count"]

    executive_html = f"""
<div class="card span12 exec-card">
  <div class="exec-kicker">Current answer</div>
  <div class="exec-answer">Use the latest in-person major as the anchor, then use Online results to adjust it.</div>
  <div class="exec-sub">For a brand-new format, start with Online results until the first in-person major has happened.</div>
</div>

<div class="card span12 journey-card">
  <div class="section-title">How the prediction should work</div>
  <div class="journey">
    <div class="journey-step">
      <div class="journey-number">1</div>
      <div>
        <div class="journey-title">New format</div>
        <div class="journey-copy">Use current-format Online results. There is no relevant in-person result yet.</div>
      </div>
    </div>
    <div class="journey-arrow">→</div>
    <div class="journey-step">
      <div class="journey-number">2</div>
      <div>
        <div class="journey-title">First major happens</div>
        <div class="journey-copy">That result becomes the strongest real-world signal for the next event.</div>
      </div>
    </div>
    <div class="journey-arrow">→</div>
    <div class="journey-step">
      <div class="journey-number">3</div>
      <div>
        <div class="journey-title">Between majors</div>
        <div class="journey-copy">Keep the latest major as the anchor and use Online play to capture movement in the field.</div>
      </div>
    </div>
  </div>
</div>

<div class="card span6 finding-card">
  <div class="finding-label">What the history is telling us</div>
  <div class="finding-title">Recent in-person results matter.</div>
  <div class="finding-copy">When a same-format major has just happened, predictions improve when that result carries more influence than a neutral blend.</div>
</div>

<div class="card span6 finding-card">
  <div class="finding-label">What not to do</div>
  <div class="finding-title">Do not automatically let Online data take over.</div>
  <div class="finding-copy">The evidence so far says the existing rule shifts away from the latest major too quickly as it gets older.</div>
</div>

<div class="card span12 next-card">
  <div class="section-title">What we still need to determine</div>
  <div class="next-question">How quickly should the influence of the latest major fade?</div>
  <div class="next-copy">That is now the main modelling question. We should answer it by replaying history one major weekend at a time and choosing the rule that predicts unseen tournaments best.</div>
  <div class="evidence-note">Based on {target_count} high-quality historical tournament fields.</div>
</div>
""".strip()

    exec_function = "function executiveSummary(){return " + json.dumps(executive_html) + ";}\n"
    insert_at = "function metric(k,v,n='')"
    if insert_at not in source:
        raise RuntimeError("Could not find insertion point")
    source = source.replace(insert_at, exec_function + insert_at, 1)

    # Senior-stakeholder default: answer first, evidence second, technical detail last.
    new_render = r'''function render(){$('#root').innerHTML=header()+`<div class="grid">${executiveSummary()}<details class="card span12 evidence-panel"><summary>See the supporting analysis</summary><div class="evidence-intro">This contains the model comparisons and tournament-level results behind the summary above.</div><div class="grid nested-grid">${summaryTable()}${pairCard('current_v2_1_vs_fifty_fifty','IRL-decay blend vs 50/50')}${pairCard('current_v2_1_vs_irl_only','IRL-decay blend vs in-person only')}${weightAnalysis()}${coverage()}${eventTable()}${detail()}</div></details><details class="card span12 evidence-panel"><summary>Methodology and audit trail</summary><div class="grid nested-grid">${transition()}${rules()}</div></details></div>`;bind()}'''
    source, count = re.subn(r"function render\(\)\{.*?\}\nfunction bind\(\)", new_render + "\nfunction bind()", source, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Could not replace render()")

    # Plain-English labels.
    replacements = {
        "Historical research workspace": "Historical evidence",
        "Baseline Model Comparison": "Predicting the Next Tournament Meta",
        "Next Tournament Meta Prediction": "Predicting the Next Tournament Meta",
        "Compare simple historical predictions against actual Day-1 fields, both tournament-by-tournament and with each contemporaneous major weekend weighted once.": "What does history tell us about the best way to forecast the field at the next major?",
        "Use historical major results to learn the most reliable way to predict the next tournament's Day-1 metagame.": "What does history tell us about the best way to forecast the field at the next major?",
        ">Model comparison<": ">Prediction research<",
        "Current v2.1": "IRL-decay blend",
        "v2.1": "decay blend",
        "IRL-only": "In-person only",
        "Online-only": "Online only",
        "IRL": "in-person",
    }
    for old, new in replacements.items():
        source = source.replace(old, new)

    css = r'''
/* Executive summary layout */
.app{max-width:1240px}.top{align-items:center}.eyebrow{font-size:11px}.title{font-size:28px}.subtitle{max-width:760px;font-size:15px}.stamp{display:none}.tabs{margin:14px 0 18px}.tab{padding:8px 12px}
.exec-card{padding:28px 30px;background:linear-gradient(135deg,#132944,#102238);border-color:#315474}.exec-kicker{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#7fc3ff;font-weight:800}.exec-answer{font-size:30px;line-height:1.18;font-weight:850;max-width:980px;margin:7px 0 9px}.exec-sub{font-size:17px;color:#c3d2e2;max-width:900px}
.journey-card{padding:22px 24px}.journey{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;gap:14px;align-items:center}.journey-step{display:flex;gap:12px;align-items:flex-start;padding:14px;background:#0a1828;border:1px solid #2a435e;border-radius:12px;min-height:128px}.journey-number{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:#173a5c;color:#a8d7ff;font-weight:800;flex:0 0 auto}.journey-title{font-size:17px;font-weight:800;margin-bottom:5px}.journey-copy{color:#b8c8da;line-height:1.5}.journey-arrow{font-size:24px;color:#6f8ba7}
.finding-card{padding:22px 24px}.finding-label{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:#8fb5d9;font-weight:800}.finding-title{font-size:21px;font-weight:800;margin:5px 0 8px}.finding-copy{font-size:15px;color:#c3d1df;line-height:1.55}.next-card{padding:22px 24px}.next-question{font-size:22px;font-weight:800;margin:4px 0 7px}.next-copy{font-size:15px;color:#c3d1df;max-width:940px}.evidence-note{margin-top:12px;font-size:12px;color:#8fa4ba}
.evidence-panel{padding:0;overflow:hidden}.evidence-panel>summary{cursor:pointer;list-style:none;padding:16px 18px;font-size:15px;font-weight:750;background:#102038}.evidence-panel>summary::-webkit-details-marker{display:none}.evidence-panel>summary:after{content:'Open';float:right;color:#8fb5d9;font-size:12px}.evidence-panel[open]>summary:after{content:'Close'}.evidence-intro{padding:14px 18px 0;color:#9fb0c5}.nested-grid{padding:14px}.nested-grid>.card{box-shadow:none}
/* Detailed tables: readable when deliberately opened */
.table-wrap{background:#091522;border:1px solid #3a5876;border-radius:10px;overflow:auto}table{border-collapse:separate;border-spacing:0}th,td{padding:12px 14px;border-bottom:1px solid #29415a;border-right:1px solid #365470}th:last-child,td:last-child{border-right:0}thead th{background:#19314e;color:#f3f7fb;border-bottom:2px solid #52769a;font-weight:800}tbody tr:nth-child(even) td{background:#0c1c2d}tbody tr:hover td{background:#132a42}td.num{text-align:right;font-variant-numeric:tabular-nums}
@media(max-width:900px){.journey{grid-template-columns:1fr}.journey-arrow{transform:rotate(90deg);text-align:center}.span6{grid-column:span 12}.exec-answer{font-size:24px}.exec-card{padding:22px}}
'''
    if "</style>" not in source:
        raise RuntimeError("Could not find style block")
    source = source.replace("</style>", css + "\n</style>", 1)

    PAGE.write_text(source, encoding="utf-8")
    print(json.dumps({"page": str(PAGE), "historical_targets": target_count}, indent=2))


if __name__ == "__main__":
    main()
