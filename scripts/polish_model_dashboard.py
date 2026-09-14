#!/usr/bin/env python3
"""Turn the model-comparison page into a prediction-first research dashboard.

The detailed benchmark tables stay available for audit, but the default page answers
one question first: what should we use to predict the next major tournament?
"""

from __future__ import annotations

import collections
import json
import re
import statistics
from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / "dashboard" / "models.html"


def mean(values):
    values = list(values)
    return statistics.fmean(values) if values else None


def signed(value):
    if value is None:
        return "—"
    return f"{value:+.2f} pp"


def main() -> None:
    source = PAGE.read_text(encoding="utf-8")

    data_match = re.search(r"const DATA=(.*?);const state=", source, re.S)
    if not data_match:
        raise RuntimeError("Could not find embedded model data")
    data = json.loads(data_match.group(1))

    # Descriptive comparison only: use the already-frozen complete historical windows.
    rows = []
    for target in data["targets"]:
        decay = target["models"].get("current_v2_1", {})
        half = target["models"].get("fifty_fifty", {})
        if not (
            target.get("target_eligible_ge_95")
            and target.get("window_class") == "settled"
            and decay.get("available")
            and half.get("available")
        ):
            continue
        irl_weight = float(decay["weights"]["irl"])
        rows.append(
            {
                "cohort": target["cohort_id"],
                "irl_weight": irl_weight,
                "delta": float(decay["field_accuracy_pct"]) - float(half["field_accuracy_pct"]),
            }
        )

    def grouped(predicate):
        selected = [row for row in rows if predicate(row["irl_weight"])]
        by_cohort = collections.defaultdict(list)
        for row in selected:
            by_cohort[row["cohort"]].append(row["delta"])
        return {
            "events": len(selected),
            "cohorts": len(by_cohort),
            "event_delta": mean(row["delta"] for row in selected),
            "cohort_delta": mean(mean(values) for values in by_cohort.values()),
        }

    irl_heavy = grouped(lambda w: w > 0.500001)
    online_heavy = grouped(lambda w: w < 0.499999)
    transition = data["summary"]["models"]["online_only"]["transition_primary"]

    guide_html = f"""
<div class="card span12 prediction-guide">
  <div class="eyebrow">Working answer</div>
  <div class="guide-title">How should we predict the next tournament?</div>
  <div class="guide-subtitle">The research should optimise this decision, not defend one historic formula.</div>
  <div class="guide-grid">
    <div class="guide-step">
      <div class="step-kicker">New / transition format</div>
      <div class="step-answer">Start with current-format Online data</div>
      <div class="step-note">No same-format IRL major exists yet. Current clean baseline: {transition['mean_field_accuracy_pct']:.1f}% historical field accuracy across {transition['event_count']} targets. Next research question: does carrying any previous-format IRL forward improve this?</div>
    </div>
    <div class="guide-step good-step">
      <div class="step-kicker">Settled format + recent IRL major</div>
      <div class="step-answer">Use Online + latest IRL, leaning toward the IRL result</div>
      <div class="step-note">In the current sample, when the decay blend leaned IRL, it beat a neutral 50/50 blend by <b>{signed(irl_heavy['event_delta'])}</b> per tournament ({signed(irl_heavy['cohort_delta'])} weekend-weighted).</div>
    </div>
    <div class="guide-step warn-step">
      <div class="step-kicker">Settled format + older IRL major</div>
      <div class="step-answer">Do not automatically keep shifting toward Online</div>
      <div class="step-note">When the current decay rule became Online-heavy, it was <b>{signed(online_heavy['event_delta'])}</b> versus 50/50 ({signed(online_heavy['cohort_delta'])} weekend-weighted). That suggests the present Online shift is too aggressive.</div>
    </div>
  </div>
  <div class="guide-footer">This is a working rule from the historical evidence so far, not the final fitted predictor. The next analysis should find the best walk-forward rule and validate it by major weekend.</div>
</div>
""".strip()

    guide_function = "function nextTournamentGuide(){return " + json.dumps(guide_html) + ";}\n"
    insert_at = "function metric(k,v,n='')"
    if insert_at not in source:
        raise RuntimeError("Could not find metric() insertion point")
    source = source.replace(insert_at, guide_function + insert_at, 1)

    # Replace the dense default render with a prediction-first page. Detailed tables remain,
    # but are collapsed until the user explicitly asks for the audit evidence.
    new_render = r'''function render(){const s=DATA.summary;$('#root').innerHTML=header()+`<div class="grid">${nextTournamentGuide()}${metric('Historical targets',fmt(s.primary_target_count),'High-quality Day-1 fields')}${metric('Settled targets',fmt(s.primary_settled_count),'Same-format IRL available')}${metric('Transition targets',fmt(s.primary_transition_count),'No same-format IRL yet')}${metric('Independent weekends',fmt(s.complete_case_settled_cohort_count),'Complete-case settled comparison')}<details class="card span12 audit-panel"><summary>Show model benchmark details</summary><div class="grid nested-grid">${summaryTable()}${pairCard('current_v2_1_vs_fifty_fifty','IRL-decay blend vs 50/50')}${pairCard('current_v2_1_vs_irl_only','IRL-decay blend vs IRL-only')}${weightAnalysis()}${coverage()}</div></details><details class="card span12 audit-panel" ${state.selected?'open':''}><summary>Show tournament-by-tournament evidence</summary><div class="grid nested-grid">${eventTable()}${detail()}</div></details><details class="card span12 audit-panel"><summary>Methodology & audit notes</summary><div class="grid nested-grid">${transition()}${rules()}</div></details></div>`;bind()}'''
    source, count = re.subn(r"function render\(\)\{.*?\}\nfunction bind\(\)", new_render + "\nfunction bind()", source, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Could not replace render()")

    # Use descriptive language, not an internal version number, in the UI.
    source = source.replace("Current v2.1", "IRL-decay blend")
    source = source.replace("v2.1", "decay blend")
    source = source.replace("Baseline Model Comparison", "Next Tournament Meta Prediction")
    source = source.replace(">Model comparison<", ">Prediction research<")
    source = source.replace(
        "Compare simple historical predictions against actual Day-1 fields, both tournament-by-tournament and with each contemporaneous major weekend weighted once.",
        "Use historical major results to learn the most reliable way to predict the next tournament's Day-1 metagame.",
    )

    # Stronger table structure: visible column boundaries, alternating column/row shade,
    # clearer headers, and more breathing room. This applies to every table on the page.
    css = r'''
/* Prediction-first layout */
.prediction-guide{padding:20px}.guide-title{font-size:24px;font-weight:800;margin:3px 0 4px}.guide-subtitle{color:var(--muted);margin-bottom:16px}.guide-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.guide-step{background:#0b1828;border:1px solid #2b425d;border-radius:12px;padding:15px}.good-step{border-color:#315f50}.warn-step{border-color:#725a31}.step-kicker{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:750}.step-answer{font-size:18px;font-weight:800;margin:5px 0 8px}.step-note{color:#c7d5e5}.guide-footer{margin-top:13px;color:var(--muted);font-size:12px}.audit-panel{padding:0;overflow:hidden}.audit-panel>summary{cursor:pointer;list-style:none;padding:15px 17px;font-size:15px;font-weight:750;background:#102038;border-bottom:1px solid transparent}.audit-panel[open]>summary{border-bottom-color:#314a66}.audit-panel>summary::-webkit-details-marker{display:none}.audit-panel>summary:after{content:'Show';float:right;color:var(--muted);font-size:12px;font-weight:600}.audit-panel[open]>summary:after{content:'Hide'}.nested-grid{padding:14px}.nested-grid>.card{box-shadow:none}

/* Tables: make columns visually distinct */
.table-wrap{background:#0a1625;border:1px solid #34506e;border-radius:11px;overflow:auto}table{border-collapse:separate;border-spacing:0}th,td{padding:11px 14px;border-bottom:1px solid #263d57;border-right:1px solid #304b68}th:last-child,td:last-child{border-right:0}thead th{background:#172c47;color:#f2f6fb;border-bottom:2px solid #466889;font-weight:750}tbody tr:nth-child(even) td{background:rgba(91,137,181,.055)}tbody td:nth-child(even){box-shadow:inset 0 0 0 9999px rgba(110,158,201,.025)}tbody tr:hover td{background:#132942}td.num{text-align:right;font-variant-numeric:tabular-nums;font-feature-settings:'tnum'}
@media(max-width:900px){.guide-grid{grid-template-columns:1fr}}
'''
    if "</style>" not in source:
        raise RuntimeError("Could not find style block")
    source = source.replace("</style>", css + "\n</style>", 1)

    PAGE.write_text(source, encoding="utf-8")
    print(json.dumps({
        "page": str(PAGE),
        "irl_heavy": irl_heavy,
        "online_heavy": online_heavy,
        "transition_accuracy": transition.get("mean_field_accuracy_pct"),
    }, indent=2))


if __name__ == "__main__":
    main()
