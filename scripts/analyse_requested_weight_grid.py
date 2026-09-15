#!/usr/bin/env python3
"""Exhaustive owner-requested IRL/Online weighting grid on the latest 365 days.

Tests every combination of:
- initial IRL weight: 100% to 80% in 5pp steps;
- IRL weight loss: 1 to 5 percentage points per day;
- IRL floor: 50% to 10% in 5pp steps.

Online weight is always the remainder. Uses exactly the same frozen recent-year
sample and cohort-weighted Field Accuracy semantics as analyse_last_year_weighting.py.
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import analyse_last_year_weighting as base

ROOT = Path(__file__).resolve().parents[1]
INFILE = ROOT / "data" / "processed" / "model-results" / "baselines.json"
OUTDIR = ROOT / "data" / "processed" / "last-year-weighting" / "requested-grid"
RESDIR = ROOT / "results" / "last-year-weighting"

STARTS = [1.00, 0.95, 0.90, 0.85, 0.80]
DECAYS = [0.01, 0.02, 0.03, 0.04, 0.05]
FLOORS = [0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20, 0.15, 0.10]


def mean(xs):
    xs = list(xs)
    return statistics.fmean(xs) if xs else None


def cohort_metric(rows, score_key):
    by = defaultdict(list)
    for r in rows:
        by[r["cohort_id"]].append(r[score_key])
    return mean(mean(v) for v in by.values())


def baseline_metric(rows, key):
    return {"event": mean(r[key] for r in rows), "cohort": cohort_metric(rows, key)}


def load_recent_rows():
    data = json.loads(INFILE.read_text(encoding="utf-8"))
    eligible_dates = [
        date.fromisoformat(t["target_start_date"])
        for t in data.get("targets", [])
        if t.get("target_eligible_ge_95")
    ]
    end_date = max(eligible_dates)
    start_date = end_date - timedelta(days=365)

    rows = []
    for t in data.get("targets", []):
        if not t.get("target_eligible_ge_95") or t.get("window_class") != "settled":
            continue
        d = date.fromisoformat(t["target_start_date"])
        if not (start_date <= d <= end_date):
            continue
        models = t.get("models", {})
        irl_m = models.get("irl_only", {})
        half_m = models.get("fifty_fifty", {})
        current_m = models.get("current_v2_1", {})
        online_m = models.get("online_only", {})
        if not all(m.get("available") for m in [irl_m, half_m, current_m, online_m]):
            continue
        irl = base.pred_map(irl_m)
        fifty = base.pred_map(half_m)
        online = base.reconstruct_online(irl, fifty)
        actual = base.actual_map(irl_m)
        rows.append({
            "target_id": str(t["target_id"]),
            "target_name": t["target_name"],
            "date": t["target_start_date"],
            "cohort_id": t["cohort_id"],
            "days_since_major": int(t["days_since_major"]),
            "irl": irl,
            "online": online,
            "actual": actual,
            "online_only": float(online_m["field_accuracy_pct"]),
            "irl_only": float(irl_m["field_accuracy_pct"]),
            "fifty": float(half_m["field_accuracy_pct"]),
        })
    if not rows:
        raise RuntimeError("No recent complete-case settled targets found")
    return rows, start_date, end_date


def best_for(rows, field):
    vals = sorted({r[field] for r in rows}, reverse=True)
    out = []
    for val in vals:
        subset = [r for r in rows if r[field] == val]
        best = max(subset, key=lambda r: (r["mean_cohort_accuracy"], r["mean_event_accuracy"]))
        out.append({
            field: val,
            "best_cohort_accuracy": best["mean_cohort_accuracy"],
            "best_start": best["start"],
            "best_decay_per_day": best["decay_per_day"],
            "best_floor": best["floor"],
        })
    return out


def main():
    rows, start_date, end_date = load_recent_rows()
    cohort_count = len({r["cohort_id"] for r in rows})

    baselines = {
        "fifty_fifty": baseline_metric(rows, "fifty"),
        "irl_only": baseline_metric(rows, "irl_only"),
        "online_only": baseline_metric(rows, "online_only"),
    }

    grid = []
    for start in STARTS:
        for decay in DECAYS:
            for floor in FLOORS:
                result = base.evaluate(rows, start, floor, decay)
                result["delta_vs_50_50_pp"] = result["mean_cohort_accuracy"] - baselines["fifty_fifty"]["cohort"]
                result["delta_vs_irl_only_pp"] = result["mean_cohort_accuracy"] - baselines["irl_only"]["cohort"]
                result["delta_vs_online_only_pp"] = result["mean_cohort_accuracy"] - baselines["online_only"]["cohort"]
                grid.append(result)

    grid.sort(key=lambda r: (r["mean_cohort_accuracy"], r["mean_event_accuracy"]), reverse=True)
    for i, r in enumerate(grid, start=1):
        r["rank"] = i

    counts = {
        "total_rules": len(grid),
        "beat_50_50": sum(r["delta_vs_50_50_pp"] > 0 for r in grid),
        "beat_irl_only": sum(r["delta_vs_irl_only_pp"] > 0 for r in grid),
        "beat_online_only": sum(r["delta_vs_online_only_pp"] > 0 for r in grid),
        "beat_all_three": sum(
            r["delta_vs_50_50_pp"] > 0 and r["delta_vs_irl_only_pp"] > 0 and r["delta_vs_online_only_pp"] > 0
            for r in grid
        ),
    }

    out = {
        "research_question": "Across all owner-requested IRL start/decay/floor combinations, which rules best predict the latest year of settled IRL fields?",
        "evidence_window": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "sample": {"event_count": len(rows), "cohort_count": cohort_count},
        "metric": "Cohort-weighted Field Accuracy; named archetypes only, matching frozen baseline scoring",
        "grid_definition": {
            "starts": STARTS,
            "decays_per_day": DECAYS,
            "floors": FLOORS,
            "combination_count": len(grid),
            "online_weight": "1 - IRL weight",
            "weight_formula": "max(floor, initial_IRL_weight - decay_per_day * days_since_previous_major)",
        },
        "baselines": baselines,
        "counts": counts,
        "best_rule": grid[0],
        "top_25_rules": grid[:25],
        "bottom_10_rules": grid[-10:],
        "best_by_initial": best_for(grid, "start"),
        "best_by_decay": best_for(grid, "decay_per_day"),
        "best_by_floor": best_for(grid, "floor"),
        "all_rules": grid,
        "interpretation_boundary": "All 225 rules are fitted and scored on the same recent 11 cohorts. Ranking is descriptive/in-sample, not out-of-sample validation.",
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    RESDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    with (OUTDIR / "all_rules.csv").open("w", newline="", encoding="utf-8") as f:
        fields = [
            "rank", "start", "decay_per_day", "floor", "mean_cohort_accuracy", "mean_event_accuracy",
            "delta_vs_50_50_pp", "delta_vs_irl_only_pp", "delta_vs_online_only_pp",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in grid:
            w.writerow({k: r[k] for k in fields})

    best = grid[0]
    lines = [
        "# Exhaustive requested IRL-weight grid",
        "",
        f"Evidence window: **{start_date.isoformat()} to {end_date.isoformat()}**.",
        f"Sample: **{len(rows)} tournaments / {cohort_count} independent cohorts**.",
        f"Tested **{len(grid)} combinations**.",
        "",
        "IRL weight = max(floor, initial IRL weight − daily percentage-point loss × days since previous major). Online is the remainder.",
        "",
        "## Baselines",
        "",
        "| Baseline | Cohort-weighted accuracy |",
        "|---|---:|",
        f"| Flat 50/50 | {baselines['fifty_fifty']['cohort']:.2f}% |",
        f"| 100% IRL | {baselines['irl_only']['cohort']:.2f}% |",
        f"| 100% Online | {baselines['online_only']['cohort']:.2f}% |",
        "",
        "## Best rule",
        "",
        f"**{best['start']*100:.0f}% initial IRL, lose {best['decay_per_day']*100:.0f}pp/day, floor {best['floor']*100:.0f}% IRL** = **{best['mean_cohort_accuracy']:.2f}%**.",
        f"Vs 50/50: **{best['delta_vs_50_50_pp']:+.2f}pp**; vs 100% IRL: **{best['delta_vs_irl_only_pp']:+.2f}pp**; vs 100% Online: **{best['delta_vs_online_only_pp']:+.2f}pp**.",
        "",
        "## How many rules beat each baseline?",
        "",
        f"- 50/50: **{counts['beat_50_50']} / {len(grid)}**",
        f"- 100% IRL: **{counts['beat_irl_only']} / {len(grid)}**",
        f"- 100% Online: **{counts['beat_online_only']} / {len(grid)}**",
        f"- all three: **{counts['beat_all_three']} / {len(grid)}**",
        "",
        "## Top 15 rules",
        "",
        "| Rank | Initial IRL | Loss/day | Floor | Accuracy | vs 50/50 | vs IRL | vs Online |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in grid[:15]:
        lines.append(
            f"| {r['rank']} | {r['start']*100:.0f}% | {r['decay_per_day']*100:.0f}pp | {r['floor']*100:.0f}% | "
            f"{r['mean_cohort_accuracy']:.2f}% | {r['delta_vs_50_50_pp']:+.2f} | {r['delta_vs_irl_only_pp']:+.2f} | {r['delta_vs_online_only_pp']:+.2f} |"
        )

    lines += [
        "",
        "## Best result available at each initial weight",
        "",
        "| Initial IRL | Best accuracy | Best loss/day | Best floor |",
        "|---:|---:|---:|---:|",
    ]
    for r in out["best_by_initial"]:
        lines.append(f"| {r['start']*100:.0f}% | {r['best_cohort_accuracy']:.2f}% | {r['best_decay_per_day']*100:.0f}pp | {r['best_floor']*100:.0f}% |")

    lines += [
        "",
        "## Best result available at each daily loss",
        "",
        "| Loss/day | Best accuracy | Best initial | Best floor |",
        "|---:|---:|---:|---:|",
    ]
    for r in out["best_by_decay"]:
        lines.append(f"| {r['decay_per_day']*100:.0f}pp | {r['best_cohort_accuracy']:.2f}% | {r['best_start']*100:.0f}% | {r['best_floor']*100:.0f}% |")

    lines += [
        "",
        "## Best result available at each floor",
        "",
        "| Floor | Best accuracy | Best initial | Best loss/day |",
        "|---:|---:|---:|---:|",
    ]
    for r in out["best_by_floor"]:
        lines.append(f"| {r['floor']*100:.0f}% | {r['best_cohort_accuracy']:.2f}% | {r['best_start']*100:.0f}% | {r['best_decay_per_day']*100:.0f}pp |")

    lines += [
        "",
        "Full 225-rule ranking is stored in `data/processed/last-year-weighting/requested-grid/all_rules.csv` and `summary.json`.",
        "",
        "**Interpretation boundary:** this is an exhaustive in-sample ranking over the same 11 recent cohorts, not proof that the winning rule will outperform on future tournaments.",
    ]
    (RESDIR / "requested-grid.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "best_rule": best,
        "baselines": baselines,
        "counts": counts,
        "top_15": grid[:15],
    }, indent=2))


if __name__ == "__main__":
    main()
