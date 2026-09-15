#!/usr/bin/env python3
"""Test whether correcting structural Online spread improves next-IRL field forecasts.

Primary correction: take the previous IRL top 10 as a group. Preserve Online relative
shares within that group and within the remainder, but shrink the group's total Online
share part-way back toward its previous-IRL total. Then blend that corrected Online
snapshot with previous IRL using the same historical IRL-weight grid.

All target membership and named-archetype normalisation come from the frozen baseline
research. Forecast scoring is cohort-weighted Field Accuracy. No production formula is
changed by this script.
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFILE = ROOT / "data" / "processed" / "model-results" / "baselines.json"
OUTDIR = ROOT / "data" / "processed" / "concentration-corrected-blend"
RESDIR = ROOT / "results" / "concentration-corrected-blend"

STARTS = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
FLOORS = [0.30, 0.40, 0.45, 0.50, 0.55, 0.60]
DECAYS = [0.005, 0.010, 0.015, 0.020]
STRENGTHS = [0.0, 0.25, 0.50, 0.75, 1.0]
PRIMARY_TOP_N = 10
SENSITIVITY_TOP_NS = [5, 20]
MIN_TRAIN_COHORTS = 10
RECENT_START = date(2025, 8, 28)
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
    out = {k: (0.0 if -EPS < v < 0.0 else v) for k, v in raw.items()}
    if min(out.values(), default=0.0) < -1e-7:
        raise RuntimeError("Could not reconstruct Online component cleanly from 50/50 prediction")
    out = {k: max(0.0, v) for k, v in out.items()}
    total = sum(out.values())
    return {k: v / total for k, v in out.items()} if total else {}


def weight(days, start, floor, decay):
    return max(floor, min(start, start - decay * days))


def top_keys(dist, n):
    return [k for k, _ in sorted(dist.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]


def concentration_correct(irl, online, n, strength):
    """Shrink prior-IRL top-N Online group share toward its previous IRL group share.

    strength=0 leaves Online unchanged. strength=1 makes the previous-IRL top-N group's
    corrected Online total equal its previous-IRL total. Relative Online shares within
    top-N and within the rest are preserved.
    """
    if strength <= 0:
        return dict(online)
    group = set(top_keys(irl, n))
    prior_group = sum(irl.get(k, 0.0) for k in group)
    online_group = sum(online.get(k, 0.0) for k in group)
    target_group = online_group + strength * (prior_group - online_group)
    target_group = max(0.0, min(1.0, target_group))
    online_tail = 1.0 - online_group
    target_tail = 1.0 - target_group
    if online_group <= EPS or online_tail <= EPS:
        return dict(online)
    top_scale = target_group / online_group
    tail_scale = target_tail / online_tail
    out = {k: v * (top_scale if k in group else tail_scale) for k, v in online.items()}
    total = sum(out.values())
    return {k: v / total for k, v in out.items()} if total else {}


def load_rows():
    data = json.loads(INFILE.read_text(encoding="utf-8"))
    rows = []
    for t in data.get("targets", []):
        if not t.get("target_eligible_ge_95") or t.get("window_class") != "settled":
            continue
        models = t.get("models", {})
        irl_m = models.get("irl_only", {})
        half_m = models.get("fifty_fifty", {})
        current_m = models.get("current_v2_1", {})
        if not (irl_m.get("available") and half_m.get("available") and current_m.get("available")):
            continue
        irl = pred_map(irl_m)
        online = reconstruct_online(irl, pred_map(half_m))
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
    return rows


def cohort_mean(scored):
    by = defaultdict(list)
    for r in scored:
        by[r["cohort_id"]].append(r["score"])
    return mean(mean(v) for v in by.values())


def evaluate(rows, start, floor, decay, strength=0.0, top_n=PRIMARY_TOP_N):
    scored = []
    for r in rows:
        online = concentration_correct(r["irl"], r["online"], top_n, strength)
        w = weight(r["days_since_major"], start, floor, decay)
        score = accuracy(blend(r["irl"], online, w), r["actual"])
        scored.append({"cohort_id": r["cohort_id"], "score": score})
    return {
        "start": start,
        "floor": floor,
        "decay_per_day": decay,
        "strength": strength,
        "top_n": top_n,
        "event_count": len(rows),
        "cohort_count": len(set(r["cohort_id"] for r in rows)),
        "mean_event_accuracy": mean(r["score"] for r in scored),
        "mean_cohort_accuracy": cohort_mean(scored),
    }


def parameter_grid(rows, allow_correction):
    ranked = []
    strengths = STRENGTHS if allow_correction else [0.0]
    for s in STARTS:
        for f in FLOORS:
            if f > s:
                continue
            for d in DECAYS:
                for c in strengths:
                    ranked.append(evaluate(rows, s, f, d, c, PRIMARY_TOP_N))
    ranked.sort(key=lambda x: (x["mean_cohort_accuracy"], x["mean_event_accuracy"], -x["strength"]), reverse=True)
    return ranked


def ordered_cohorts(rows):
    dates = {}
    for r in rows:
        dates[r["cohort_id"]] = min(dates.get(r["cohort_id"], r["date"]), r["date"])
    return sorted(dates, key=lambda c: (dates[c], c)), dates


def wf_compare(rows):
    cohorts, dates = ordered_cohorts(rows)
    out = []
    for i, cohort in enumerate(cohorts):
        if i < MIN_TRAIN_COHORTS:
            continue
        train_ids = set(cohorts[:i])
        train = [r for r in rows if r["cohort_id"] in train_ids]
        test = [r for r in rows if r["cohort_id"] == cohort]
        raw = parameter_grid(train, False)[0]
        corrected = parameter_grid(train, True)[0]
        raw_test = evaluate(test, raw["start"], raw["floor"], raw["decay_per_day"], 0.0)
        corr_test = evaluate(test, corrected["start"], corrected["floor"], corrected["decay_per_day"], corrected["strength"])
        out.append({
            "cohort_id": cohort,
            "date": dates[cohort],
            "raw_accuracy": raw_test["mean_cohort_accuracy"],
            "corrected_accuracy": corr_test["mean_cohort_accuracy"],
            "delta_pp": corr_test["mean_cohort_accuracy"] - raw_test["mean_cohort_accuracy"],
            "raw_selected": {k: raw[k] for k in ("start", "floor", "decay_per_day")},
            "corrected_selected": {k: corrected[k] for k in ("start", "floor", "decay_per_day", "strength")},
        })
    return {
        "tested_cohorts": len(out),
        "raw_mean_accuracy": mean(r["raw_accuracy"] for r in out),
        "corrected_mean_accuracy": mean(r["corrected_accuracy"] for r in out),
        "delta_pp": mean(r["delta_pp"] for r in out),
        "cohorts_improved": sum(1 for r in out if r["delta_pp"] > 1e-9),
        "cohorts_worse": sum(1 for r in out if r["delta_pp"] < -1e-9),
        "cohorts_tied": sum(1 for r in out if abs(r["delta_pp"]) <= 1e-9),
        "rows": out,
    }


def frozen_recent_test(rows):
    train = [r for r in rows if date.fromisoformat(r["date"]) < RECENT_START]
    test = [r for r in rows if date.fromisoformat(r["date"]) >= RECENT_START]
    if not train or not test:
        return None
    raw = parameter_grid(train, False)[0]
    corrected = parameter_grid(train, True)[0]
    raw_test = evaluate(test, raw["start"], raw["floor"], raw["decay_per_day"], 0.0)
    corr_test = evaluate(test, corrected["start"], corrected["floor"], corrected["decay_per_day"], corrected["strength"])
    return {
        "cutoff": RECENT_START.isoformat(),
        "train_cohorts": len(set(r["cohort_id"] for r in train)),
        "test_cohorts": len(set(r["cohort_id"] for r in test)),
        "raw_selected": raw,
        "corrected_selected": corrected,
        "raw_test_accuracy": raw_test["mean_cohort_accuracy"],
        "corrected_test_accuracy": corr_test["mean_cohort_accuracy"],
        "delta_pp": corr_test["mean_cohort_accuracy"] - raw_test["mean_cohort_accuracy"],
    }


def main():
    rows = load_rows()
    cohorts, _ = ordered_cohorts(rows)

    raw_grid = parameter_grid(rows, False)
    corr_grid = parameter_grid(rows, True)
    best_raw = raw_grid[0]
    best_corr = corr_grid[0]

    # Isolate correction at the historical full-sample grid winner.
    fixed_rule = (0.80, 0.55, 0.010)
    fixed_strengths = [evaluate(rows, *fixed_rule, c, PRIMARY_TOP_N) for c in STRENGTHS]
    sensitivity = {
        str(n): [evaluate(rows, *fixed_rule, c, n) for c in STRENGTHS]
        for n in SENSITIVITY_TOP_NS
    }

    wf = wf_compare(rows)
    recent = frozen_recent_test(rows)

    out = {
        "question": "Does correcting structural Online concentration/tail dilution improve next-IRL field prediction?",
        "sample": {
            "event_count": len(rows),
            "cohort_count": len(cohorts),
            "selection": ">=95% IRL capture, settled, complete previous-IRL and post-major Online components",
        },
        "method": {
            "primary_top_n": PRIMARY_TOP_N,
            "strengths": STRENGTHS,
            "description": "Preserve Online within-group relative shares, but shrink the previous-IRL top-10 group's total Online share toward its previous-IRL total before IRL/Online blending.",
            "weight_grid": {"starts": STARTS, "floors": FLOORS, "decays_per_day": DECAYS},
        },
        "full_sample": {
            "best_raw": best_raw,
            "best_corrected": best_corr,
            "delta_pp": best_corr["mean_cohort_accuracy"] - best_raw["mean_cohort_accuracy"],
            "fixed_historical_80_55_1pp_strength_sweep": fixed_strengths,
            "top_n_sensitivity": sensitivity,
            "warning": "Best raw and corrected rows are in-sample fits on the same 25 cohorts.",
        },
        "expanding_walk_forward": wf,
        "frozen_recent_test": recent,
        "interpretation_boundary": "The correction family was motivated by the full historical spread diagnostic, so even chronological replay is not a wholly untouched model-discovery test. Future-event validation remains required before adoption.",
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    RESDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "summary.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    fs = out["full_sample"]
    lines = [
        "# Concentration-corrected IRL + Online forecast",
        "",
        "## Question",
        "",
        "Can we improve next-IRL field forecasts by correcting the structural Online long-tail effect before blending Online evidence with the previous IRL field?",
        "",
        "## Primary correction",
        "",
        "Take the **previous IRL top 10** as a group. Keep the Online relative movement inside that group and inside the rest of the field, but move the group's total Online share part-way back toward its previous-IRL total. Strength 0% is the raw Online baseline; 100% fully restores the prior top-10 total before blending.",
        "",
        f"Sample: **{len(rows)} tournaments / {len(cohorts)} independent settled cohorts**.",
        "",
        "## Full-sample fit — descriptive only",
        "",
        f"Best raw IRL+Online grid: **{best_raw['mean_cohort_accuracy']:.2f}%** ({best_raw['start']*100:.0f}% start, -{best_raw['decay_per_day']*100:.1f}pp/day, {best_raw['floor']*100:.0f}% floor).",
        f"Best concentration-corrected grid: **{best_corr['mean_cohort_accuracy']:.2f}%** with **{best_corr['strength']*100:.0f}% correction**.",
        f"In-sample difference: **{fs['delta_pp']:+.2f}pp**.",
        "",
        "### Same historical 80% / -1pp/day / 55% rule, correction only",
        "",
        "| Correction strength | Accuracy |",
        "|---:|---:|",
    ]
    for r in fixed_strengths:
        lines.append(f"| {r['strength']*100:.0f}% | {r['mean_cohort_accuracy']:.2f}% |")

    lines += [
        "",
        "## Expanding walk-forward — primary validation",
        "",
        f"After at least {MIN_TRAIN_COHORTS} prior cohorts, each later cohort chose parameters using earlier cohorts only.",
        f"Raw tuned blend: **{wf['raw_mean_accuracy']:.2f}%**.",
        f"Concentration-corrected tuned blend: **{wf['corrected_mean_accuracy']:.2f}%**.",
        f"Difference: **{wf['delta_pp']:+.2f}pp**; corrected improved {wf['cohorts_improved']}/{wf['tested_cohorts']} cohorts, worsened {wf['cohorts_worse']}/{wf['tested_cohorts']}.",
        "",
    ]
    if recent:
        lines += [
            "## Frozen recent-era split",
            "",
            f"Fit parameters only before **{RECENT_START.isoformat()}**, then score the later {recent['test_cohorts']} cohorts.",
            f"Raw: **{recent['raw_test_accuracy']:.2f}%**; corrected: **{recent['corrected_test_accuracy']:.2f}%**; difference **{recent['delta_pp']:+.2f}pp**.",
            f"Training selected correction strength: **{recent['corrected_selected']['strength']*100:.0f}%**.",
            "",
        ]
    lines += [
        "## Interpretation boundary",
        "",
        "- **Verified:** all scores use the frozen historical windows and the same named-archetype Field Accuracy metric as previous research.",
        "- **Verified:** walk-forward target cohorts do not tune their own parameters.",
        "- **Caution:** the correction idea itself was discovered from the full archive, so this is stronger than an in-sample comparison but not equivalent to a genuinely unseen future tournament.",
        "- No production PTCG Tools formula is changed by this experiment.",
        "",
    ]
    (RESDIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "cohorts": len(cohorts),
        "best_raw": best_raw["mean_cohort_accuracy"],
        "best_corrected": best_corr["mean_cohort_accuracy"],
        "walk_forward_raw": wf["raw_mean_accuracy"],
        "walk_forward_corrected": wf["corrected_mean_accuracy"],
        "walk_forward_delta": wf["delta_pp"],
        "recent_delta": recent["delta_pp"] if recent else None,
    }, indent=2))


if __name__ == "__main__":
    main()
