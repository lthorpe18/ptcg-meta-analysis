#!/usr/bin/env python3
"""Add v2.1-vs-50/50 weighting analysis to the generated model page."""

from __future__ import annotations

import collections
import html
import json
import re
import statistics
from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / "dashboard" / "models.html"


def mean(values):
    values = list(values)
    return statistics.mean(values) if values else None


def pct(value):
    return "—" if value is None else f"{value:.1f}%"


def signed(value):
    if value is None:
        return "—"
    return f"{value:+.2f} pp"


def number(value, digits=1):
    return "—" if value is None else f"{value:.{digits}f}"


def esc(value):
    return html.escape(str(value), quote=True)


def main() -> None:
    source = PAGE.read_text(encoding="utf-8")
    match = re.search(r"const DATA=(.*?);const state=", source, re.S)
    if not match:
        raise RuntimeError("Could not find embedded model data")
    data = json.loads(match.group(1))

    rows = []
    for target in data["targets"]:
        v21 = target["models"].get("current_v2_1", {})
        half = target["models"].get("fifty_fifty", {})
        if not (
            target.get("target_eligible_ge_95")
            and target.get("window_class") == "settled"
            and v21.get("available")
            and half.get("available")
        ):
            continue
        irl_weight = float(v21["weights"]["irl"])
        rows.append(
            {
                "date": target["target_start_date"],
                "name": target["target_name"],
                "cohort": target["cohort_id"],
                "days": target.get("days_since_major"),
                "irl_weight": irl_weight,
                "online_weight": float(v21["weights"]["online"]),
                "v21": float(v21["field_accuracy_pct"]),
                "half": float(half["field_accuracy_pct"]),
                "delta": float(v21["field_accuracy_pct"]) - float(half["field_accuracy_pct"]),
            }
        )

    if not rows:
        raise RuntimeError("No complete-case settled rows found")

    def group(label, predicate):
        selected = [row for row in rows if predicate(row["irl_weight"])]
        by_cohort = collections.defaultdict(list)
        for row in selected:
            by_cohort[row["cohort"]].append(row["delta"])
        cohort_deltas = [mean(values) for values in by_cohort.values()]
        return {
            "label": label,
            "events": len(selected),
            "cohorts": len(by_cohort),
            "days": mean(row["days"] for row in selected if row["days"] is not None),
            "irl_weight": mean(row["irl_weight"] for row in selected),
            "v21": mean(row["v21"] for row in selected),
            "half": mean(row["half"] for row in selected),
            "delta": mean(row["delta"] for row in selected),
            "cohort_delta": mean(cohort_deltas),
            "wins": sum(row["delta"] > 1e-9 for row in selected),
            "losses": sum(row["delta"] < -1e-9 for row in selected),
            "ties": sum(abs(row["delta"]) <= 1e-9 for row in selected),
        }

    groups = [
        group("More IRL than 50/50", lambda w: w > 0.500001),
        group("Exactly 50/50", lambda w: abs(w - 0.5) <= 0.000001),
        group("More Online than 50/50", lambda w: w < 0.499999),
    ]

    exact = collections.defaultdict(list)
    for row in rows:
        exact[round(row["irl_weight"] * 100)].append(row)

    irl_heavy = groups[0]
    online_heavy = groups[2]
    interpretation = (
        f"Across the current complete-case sample, v2.1 is IRL-heavy on "
        f"<b>{irl_heavy['events']} events / {irl_heavy['cohorts']} weekends</b> and beats 50/50 by "
        f"<b>{signed(irl_heavy['delta'])}</b> per event ({signed(irl_heavy['cohort_delta'])} weekend-weighted). "
        f"When v2.1 is Online-heavy, it covers <b>{online_heavy['events']} events / {online_heavy['cohorts']} weekends</b> "
        f"and trails 50/50 by <b>{signed(online_heavy['delta'])}</b> per event "
        f"({signed(online_heavy['cohort_delta'])} weekend-weighted). This is descriptive rather than fitted evidence: "
        f"the historical sample currently supports leaning toward IRL when it is recent, but does not support the present "
        f"strength of the decay toward Online as IRL evidence gets older."
    )

    group_rows = "".join(
        "<tr>"
        f"<td><b>{esc(g['label'])}</b></td>"
        f"<td class='num'>{g['events']}</td>"
        f"<td class='num'>{g['cohorts']}</td>"
        f"<td class='num'>{pct(None if g['irl_weight'] is None else g['irl_weight'] * 100)}</td>"
        f"<td class='num'>{number(g['days'])}</td>"
        f"<td class='num'>{pct(g['v21'])}</td>"
        f"<td class='num'>{pct(g['half'])}</td>"
        f"<td class='num'>{signed(g['delta'])}</td>"
        f"<td class='num'>{signed(g['cohort_delta'])}</td>"
        f"<td class='num'>{g['wins']}–{g['losses']}–{g['ties']}</td>"
        "</tr>"
        for g in groups
    )

    exact_rows = "".join(
        "<tr>"
        f"<td><b>{weight}% IRL / {100-weight}% Online</b></td>"
        f"<td class='num'>{len(items)}</td>"
        f"<td class='num'>{number(mean(row['days'] for row in items if row['days'] is not None))}</td>"
        f"<td class='num'>{pct(mean(row['v21'] for row in items))}</td>"
        f"<td class='num'>{pct(mean(row['half'] for row in items))}</td>"
        f"<td class='num'>{signed(mean(row['delta'] for row in items))}</td>"
        "</tr>"
        for weight, items in sorted(exact.items(), reverse=True)
    )

    event_rows = "".join(
        "<tr>"
        f"<td>{esc(row['date'])}</td>"
        f"<td>{esc(row['name'])}</td>"
        f"<td class='num'>{esc(row['days'] if row['days'] is not None else '—')}</td>"
        f"<td class='num'>{row['irl_weight']*100:.0f}% / {row['online_weight']*100:.0f}%</td>"
        f"<td class='num'>{row['v21']:.1f}%</td>"
        f"<td class='num'>{row['half']:.1f}%</td>"
        f"<td class='num'>{row['delta']:+.2f} pp</td>"
        "</tr>"
        for row in sorted(
            rows,
            key=lambda x: (
                x["days"] if x["days"] is not None else 9999,
                x["date"],
                x["name"],
            ),
        )
    )

    page_section = f"""
<div class="card span12">
  <div class="section-title">Does v2.1's weighting move help?</div>
  <div class="callout" style="margin-bottom:12px">{interpretation}</div>
  <div class="table-wrap"><table>
    <thead><tr><th>v2.1 direction vs 50/50</th><th>Events</th><th>Weekends</th><th>Mean IRL weight</th><th>Mean days since IRL</th><th>v2.1 accuracy</th><th>50/50 accuracy</th><th>v2.1 advantage</th><th>Weekend-weighted advantage</th><th>W-L-T</th></tr></thead>
    <tbody>{group_rows}</tbody>
  </table></div>
  <div class="section-title" style="margin-top:18px">By actual v2.1 weighting used</div>
  <div class="table-wrap"><table>
    <thead><tr><th>v2.1 mix</th><th>Events</th><th>Mean days since IRL</th><th>v2.1 accuracy</th><th>50/50 accuracy</th><th>v2.1 advantage</th></tr></thead>
    <tbody>{exact_rows}</tbody>
  </table></div>
  <div class="section-title" style="margin-top:18px">Every complete-case tournament</div>
  <div class="muted tiny" style="margin-bottom:8px">Positive delta means v2.1 beat 50/50. This makes the changing IRL/Online mix explicit for every scored target.</div>
  <div class="table-wrap" style="max-height:520px"><table>
    <thead><tr><th>Date</th><th>Tournament</th><th>Days since prior IRL</th><th>v2.1 IRL / Online</th><th>v2.1</th><th>50/50</th><th>Delta</th></tr></thead>
    <tbody>{event_rows}</tbody>
  </table></div>
</div>
""".strip()

    function = "function weightAnalysis(){return " + json.dumps(page_section) + ";}\n"
    marker = "function transition(){"
    if marker not in source:
        raise RuntimeError("Could not find transition() insertion point")
    source = source.replace(marker, function + marker, 1)

    render_marker = "${pairCard('current_v2_1_vs_irl_only','Current v2.1 vs IRL-only')}${transition()}"
    if render_marker not in source:
        raise RuntimeError("Could not find render insertion point")
    source = source.replace(
        render_marker,
        "${pairCard('current_v2_1_vs_irl_only','Current v2.1 vs IRL-only')}${weightAnalysis()}${transition()}",
        1,
    )

    PAGE.write_text(source, encoding="utf-8")
    print(
        json.dumps(
            {
                "page": str(PAGE),
                "complete_case_events": len(rows),
                "irl_heavy_events": irl_heavy["events"],
                "irl_heavy_delta_pp": round(irl_heavy["delta"], 4),
                "online_heavy_events": online_heavy["events"],
                "online_heavy_delta_pp": round(online_heavy["delta"], 4),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
