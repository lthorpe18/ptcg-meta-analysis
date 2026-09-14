#!/usr/bin/env python3
"""Test alternative IRL/Online weighting curves on frozen historical targets.

This deliberately keeps the underlying evidence fixed. For each settled target that
has IRL-only and 50/50 predictions, reconstruct the Online-since-last-major component
and rescore alternative IRL weighting curves. Results are reported both event-weighted
and cohort/weekend-weighted. A simple expanding walk-forward test chooses parameters
using only earlier cohorts, then scores the next cohort.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFILE = ROOT / "data" / "processed" / "model-results" / "baselines.json"
OUTDIR = ROOT / "data" / "processed" / "weight-grid"
RESDIR = ROOT / "results" / "weight-grid"

STARTS = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
FLOORS = [0.30, 0.40, 0.45, 0.50, 0.55, 0.60]
DECAYS = [0.005, 0.010, 0.015, 0.020]  # IRL weight lost per day
MIN_TRAIN_COHORTS = 10
EPS = 1e-10


def mean(xs):
    xs = list(xs)
    return statistics.fmean(xs) if xs else None


def pred_map(model):
    return {str(r["key"]): float(r["predicted_pct"]) / 100.0 for r in model.get("prediction", [])}


def actual_map(model):
    return {str(r["key"]): float(r["actual_pct"]) / 100.0 for r in model.get("prediction", [])}


def blend(a, b, w):
    keys = set(a) | set(b)
    out = {k: w * a.get(k, 0.0) + (1.0 - w) * b.get(k, 0.0) for k in keys}
    total = sum(out.values())
    return {k: v / total for k, v in out.items()} if total else {}


def accuracy(pred, actual):
    keys = set(pred) | set(actual)
    return 100.0 * (1.0 - 0.5 * sum(abs(pred.get(k, 0.0) - actual.get(k, 0.0)) for k in keys))


def reconstruct_online(irl, fifty):
    keys = set(irl) | set(fifty)
    raw = {k: 2.0 * fifty.get(k, 0.0) - irl.get(k, 0.0) for k in keys}
    # Only numerical noise should ever be negative because 50/50 is generated directly
    # from these same two components.
    out = {k: (0.0 if -EPS < v < 0.0 else v) for k, v in raw.items()}
    if min(out.values(), default=0.0) < -1e-7:
        raise RuntimeError("Could not reconstruct Online component cleanly from 50/50 prediction")
    out = {k: max(0.0, v) for k, v in out.items()}
    total = sum(out.values())
    return {k: v / total for k, v in out.items()} if total else {}


def weight(days, start, floor, decay):
    return max(floor, min(start, start - decay * days))


def cohort_mean(rows, score_key):
    by = defaultdict(list)
    for r in rows:
        by[r["cohort_id"]].append(r[score_key])
    return mean(mean(v) for v in by.values())


def evaluate(rows, start, floor, decay):
    scored = []
    for r in rows:
        w = weight(r["days_since_major"], start, floor, decay)
        acc = accuracy(blend(r["irl"], r["online"], w), r["actual"])
        scored.append({**r, "score": acc, "weight": w})
    by = defaultdict(list)
    for r in scored:
        by[r["cohort_id"]].append(r["score"])
    cohort_scores = [mean(v) for v in by.values()]
    return {
        "start": start,
        "floor": floor,
        "decay_per_day": decay,
        "event_count": len(scored),
        "cohort_count": len(by),
        "mean_event_accuracy": mean(r["score"] for r in scored),
        "mean_cohort_accuracy": mean(cohort_scores),
        "median_cohort_accuracy": statistics.median(cohort_scores) if cohort_scores else None,
    }


def baseline_metric(rows, key):
    return {
        "event": mean(r[key] for r in rows),
        "cohort": cohort_mean(rows, key),
    }


def main():
    data = json.loads(INFILE.read_text(encoding="utf-8"))
    rows = []
    for t in data.get("targets", []):
        if not t.get("target_eligible_ge_95") or t.get("window_class") != "settled":
            continue
        irl_m = t.get("models", {}).get("irl_only", {})
        half_m = t.get("models", {}).get("fifty_fifty", {})
        current_m = t.get("models", {}).get("current_v2_1", {})
        if not (irl_m.get("available") and half_m.get("available") and current_m.get("available")):
            continue
        irl = pred_map(irl_m)
        fifty = pred_map(half_m)
        online = reconstruct_online(irl, fifty)
        actual = actual_map(irl_m)
        rows.append({
            "target_id": str(t["target_id"]),
            "target_name": t["target_name"],
            "date": t["target_start_date"],
            "cohort_id": t["cohort_id"],
            "days_since_major": int(t["days_since_major"]),
            "irl": irl,
            "online": online,
            "actual": actual,
            "irl_only": float(irl_m["field_accuracy_pct"]),
            "fifty": float(half_m["field_accuracy_pct"]),
            "current": float(current_m["field_accuracy_pct"]),
        })

    if not rows:
        raise RuntimeError("No complete-case settled targets found")

    # Direct question: if decay/floor remain as today (2 pp/day, 30% floor),
    # does a higher theoretical starting weight help?
    start_sweep = [evaluate(rows, s, 0.30, 0.020) for s in STARTS]

    grid = []
    for s in STARTS:
        for f in FLOORS:
            if f > s:
                continue
            for d in DECAYS:
                grid.append(evaluate(rows, s, f, d))
    grid.sort(key=lambda x: (x["mean_cohort_accuracy"], x["mean_event_accuracy"]), reverse=True)

    # Walk-forward: on each later cohort, choose the grid rule that would have been best
    # on PRIOR cohorts only. This prevents the current target from tuning its own weights.
    cohort_dates = {}
    for r in rows:
        cohort_dates[r["cohort_id"]] = min(cohort_dates.get(r["cohort_id"], r["date"]), r["date"])
    ordered_cohorts = sorted(cohort_dates, key=lambda c: (cohort_dates[c], c))
    wf_rows = []
    for i, cohort in enumerate(ordered_cohorts):
        if i < MIN_TRAIN_COHORTS:
            continue
        train_ids = set(ordered_cohorts[:i])
        train = [r for r in rows if r["cohort_id"] in train_ids]
        test = [r for r in rows if r["cohort_id"] == cohort]
        ranked = []
        for g in grid:
            ranked.append(evaluate(train, g["start"], g["floor"], g["decay_per_day"]))
        ranked.sort(key=lambda x: (x["mean_cohort_accuracy"], x["mean_event_accuracy"]), reverse=True)
        best = ranked[0]
        test_eval = evaluate(test, best["start"], best["floor"], best["decay_per_day"])
        wf_rows.append({
            "cohort_id": cohort,
            "date": cohort_dates[cohort],
            "start": best["start"],
            "floor": best["floor"],
            "decay_per_day": best["decay_per_day"],
            "accuracy": test_eval["mean_cohort_accuracy"],
            "fifty": mean(r["fifty"] for r in test),
            "irl_only": mean(r["irl_only"] for r in test),
            "current": mean(r["current"] for r in test),
        })

    out = {
        "event_count": len(rows),
        "cohort_count": len(set(r["cohort_id"] for r in rows)),
        "days_since_major": {
            "min": min(r["days_since_major"] for r in rows),
            "median": statistics.median(r["days_since_major"] for r in rows),
            "max": max(r["days_since_major"] for r in rows),
        },
        "baselines": {
            "irl_only": baseline_metric(rows, "irl_only"),
            "fifty_fifty": baseline_metric(rows, "fifty"),
            "current_decay": baseline_metric(rows, "current"),
        },
        "start_sweep_keep_current_decay_and_floor": start_sweep,
        "best_in_sample_grid": grid[:20],
        "walk_forward": {
            "min_training_cohorts": MIN_TRAIN_COHORTS,
            "tested_cohorts": len(wf_rows),
            "tuned_rule_mean_accuracy": mean(r["accuracy"] for r in wf_rows),
            "fifty_fifty_mean_accuracy": mean(r["fifty"] for r in wf_rows),
            "irl_only_mean_accuracy": mean(r["irl_only"] for r in wf_rows),
            "current_decay_mean_accuracy": mean(r["current"] for r in wf_rows),
            "rows": wf_rows,
        },
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    RESDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "weight-grid.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    lines = [
        "# IRL weighting test",
        "",
        f"Complete-case settled sample: {out['event_count']} tournaments across {out['cohort_count']} independent cohorts.",
        f"Observed gap since previous major: {out['days_since_major']['min']}–{out['days_since_major']['max']} days (median {out['days_since_major']['median']}).",
        "",
        "## Higher start only (keep today's 2pp/day decay and 30% floor)",
        "",
        "| Theoretical day-0 IRL start | Cohort-weighted accuracy | Event-weighted accuracy |",
        "|---:|---:|---:|",
    ]
    for r in start_sweep:
        lines.append(f"| {r['start']*100:.0f}% | {r['mean_cohort_accuracy']:.2f}% | {r['mean_event_accuracy']:.2f}% |")
    best = grid[0]
    lines += [
        "",
        "## Best historical grid result",
        "",
        f"Start {best['start']*100:.0f}% IRL, decay {best['decay_per_day']*100:.1f}pp/day, floor {best['floor']*100:.0f}% IRL.",
        f"Cohort-weighted accuracy: {best['mean_cohort_accuracy']:.2f}%.",
        "",
        "## Expanding walk-forward check",
        "",
        f"Tested {out['walk_forward']['tested_cohorts']} later cohorts after at least {MIN_TRAIN_COHORTS} prior cohorts were available.",
        f"Tuned rule: {out['walk_forward']['tuned_rule_mean_accuracy']:.2f}%",
        f"50/50: {out['walk_forward']['fifty_fifty_mean_accuracy']:.2f}%",
        f"IRL-only: {out['walk_forward']['irl_only_mean_accuracy']:.2f}%",
        f"Current decay rule: {out['walk_forward']['current_decay_mean_accuracy']:.2f}%",
        "",
        "Grid tuning is exploratory; the walk-forward result is the more important guard against overfitting.",
    ]
    (RESDIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
