#!/usr/bin/env python3
"""Test flat IRL/Online splits and recency-weighted Online evidence on the latest year.

Uses the same frozen recent-year complete-case settled sample as the parent weighting
experiments. No ingestion, archetype identity, event eligibility or window membership
is changed.

Questions:
1. Do flat IRL/Online splits other than 50/50 improve accuracy?
2. Does giving more weight to Online events closer to the target tournament improve
   accuracy?
3. Does Online recency weighting add value when combined with the owner-requested
   dynamic IRL start/decay/floor grid?

Primary metric is cohort-weighted Field Accuracy. Model selection is reported both
in-sample and with the same fixed chronological guard: tune on the first six recent
cohorts, score on the final five untouched cohorts.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import analyse_last_year_weighting as base
import score_baseline_models as scorer

ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "data" / "processed" / "model-results" / "baselines.json"
ONLINE_TAGS = ROOT / "data" / "processed" / "format-tags" / "online-events.json"
OUTDIR = ROOT / "data" / "processed" / "last-year-weighting" / "flat-and-recency"
RESDIR = ROOT / "results" / "last-year-weighting"

FLAT_IRL_WEIGHTS = [i / 100.0 for i in range(0, 101, 5)]
STARTS = [1.00, 0.95, 0.90, 0.85, 0.80]
DECAYS = [0.01, 0.02, 0.03, 0.04, 0.05]
FLOORS = [0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20, 0.15, 0.10]
HOLDOUT_TRAIN_COHORTS = 6

ONLINE_METHODS = [
    {"key": "equal", "label": "Equal/current", "kind": "equal"},
    {"key": "window_7", "label": "Last 7 days only", "kind": "window", "days": 7},
    {"key": "window_14", "label": "Last 14 days only", "kind": "window", "days": 14},
    {"key": "window_21", "label": "Last 21 days only", "kind": "window", "days": 21},
    {"key": "window_28", "label": "Last 28 days only", "kind": "window", "days": 28},
    {"key": "linear", "label": "Linear recency", "kind": "linear"},
    {"key": "exp_3", "label": "Exponential, 3-day half-life", "kind": "exp", "half_life": 3},
    {"key": "exp_7", "label": "Exponential, 7-day half-life", "kind": "exp", "half_life": 7},
    {"key": "exp_14", "label": "Exponential, 14-day half-life", "kind": "exp", "half_life": 14},
    {"key": "exp_21", "label": "Exponential, 21-day half-life", "kind": "exp", "half_life": 21},
    {"key": "exp_28", "label": "Exponential, 28-day half-life", "kind": "exp", "half_life": 28},
]
METHOD_BY_KEY = {m["key"]: m for m in ONLINE_METHODS}


def mean(xs):
    xs = list(xs)
    return statistics.fmean(xs) if xs else None


def cohort_mean(scored):
    by = defaultdict(list)
    for r in scored:
        by[r["cohort_id"]].append(r["accuracy"])
    return mean(mean(v) for v in by.values())


def target_cutoff(d: str) -> datetime:
    return datetime.combine(date.fromisoformat(d), time.min, tzinfo=timezone.utc)


def event_age_days(target_date: str, start_at: str) -> float:
    age = (target_cutoff(target_date) - scorer.parse_dt(start_at)).total_seconds() / 86400.0
    return max(0.0, age)


def event_factor(method: dict, age: float, min_age: float, max_age: float) -> float:
    kind = method["kind"]
    if kind == "equal":
        return 1.0
    if kind == "window":
        return 1.0 if age <= float(method["days"]) else 0.0
    if kind == "exp":
        return 0.5 ** (age / float(method["half_life"]))
    if kind == "linear":
        # Within the available post-major Online evidence, map the newest event to
        # weight 1 and the oldest to weight 0. If all events have the same age,
        # retain them all equally.
        span = max_age - min_age
        if span <= 1e-12:
            return 1.0
        return max(0.0, min(1.0, (max_age - age) / span))
    raise ValueError(f"Unknown method: {method}")


def weighted_online(event_ids, target_date, online_counts, online_meta, method):
    available = [str(i) for i in event_ids if str(i) in online_meta and str(i) in online_counts]
    if not available:
        return {}, 0
    ages = {event_id: event_age_days(target_date, online_meta[event_id]["start_at"]) for event_id in available}
    min_age = min(ages.values())
    max_age = max(ages.values())
    counts = Counter()
    used = 0
    for event_id in available:
        factor = event_factor(method, ages[event_id], min_age, max_age)
        if factor <= 0:
            continue
        used += 1
        for key, value in online_counts[event_id].items():
            counts[key] += float(value) * factor
    return scorer.normalise(counts), used


def load_rows():
    data = json.loads(BASELINES.read_text(encoding="utf-8"))
    online_meta = {str(e["id"]): e for e in json.loads(ONLINE_TAGS.read_text(encoding="utf-8"))}
    online_counts, _ = scorer.online_decks()

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
        online_m = models.get("online_only", {})
        if not all(m.get("available") for m in [irl_m, half_m, online_m]):
            continue

        irl = base.pred_map(irl_m)
        actual = base.actual_map(irl_m)
        baseline_online = base.reconstruct_online(irl, base.pred_map(half_m))
        online_ids = [str(i) for i in half_m.get("online_event_ids", [])]
        methods = {}
        used_counts = {}
        for method in ONLINE_METHODS:
            pred, used = weighted_online(online_ids, t["target_start_date"], online_counts, online_meta, method)
            methods[method["key"]] = pred
            used_counts[method["key"]] = used

        # Sanity check: equal weighting of raw deck entries must reproduce the frozen
        # Online-since-major component reconstructed from the baseline 50/50 model.
        equal = methods["equal"]
        keys = set(equal) | set(baseline_online)
        l1 = sum(abs(equal.get(k, 0.0) - baseline_online.get(k, 0.0)) for k in keys)
        if l1 > 1e-7:
            raise RuntimeError(f"Equal Online reconstruction mismatch for target {t['target_id']}: L1={l1}")

        rows.append({
            "target_id": str(t["target_id"]),
            "target_name": t["target_name"],
            "date": t["target_start_date"],
            "cohort_id": t["cohort_id"],
            "days_since_major": int(t["days_since_major"]),
            "irl": irl,
            "actual": actual,
            "online_methods": methods,
            "online_event_counts_used": used_counts,
        })

    if not rows:
        raise RuntimeError("No recent complete-case settled targets found")
    return rows, start_date, end_date


def evaluate(rows, method_key, irl_weight_fn):
    scored = []
    for r in rows:
        online = r["online_methods"].get(method_key) or {}
        if not online:
            continue
        w = max(0.0, min(1.0, float(irl_weight_fn(r))))
        pred = base.blend(r["irl"], online, w)
        acc = base.accuracy(pred, r["actual"])
        scored.append({
            "target_id": r["target_id"],
            "target_name": r["target_name"],
            "date": r["date"],
            "cohort_id": r["cohort_id"],
            "days_since_major": r["days_since_major"],
            "accuracy": acc,
            "irl_weight": w,
        })
    return {
        "event_count": len(scored),
        "cohort_count": len({r["cohort_id"] for r in scored}),
        "mean_event_accuracy": mean(r["accuracy"] for r in scored),
        "mean_cohort_accuracy": cohort_mean(scored),
        "rows": scored,
    }


def eval_flat(rows, method_key, irl_weight):
    out = evaluate(rows, method_key, lambda r: irl_weight)
    out.update({"online_method": method_key, "irl_weight": irl_weight})
    return out


def eval_dynamic(rows, method_key, start, floor, decay):
    out = evaluate(rows, method_key, lambda r: base.weight(r["days_since_major"], start, floor, decay))
    out.update({
        "online_method": method_key,
        "start": start,
        "floor": floor,
        "decay_per_day": decay,
    })
    return out


def rank_flat(rows, method_key="equal"):
    ranked = [eval_flat(rows, method_key, w) for w in FLAT_IRL_WEIGHTS]
    ranked.sort(key=lambda x: (x["mean_cohort_accuracy"] if x["mean_cohort_accuracy"] is not None else -1,
                               x["mean_event_accuracy"] if x["mean_event_accuracy"] is not None else -1), reverse=True)
    return ranked


def complete_method_keys(rows):
    return [
        m["key"] for m in ONLINE_METHODS
        if all(bool(r["online_methods"].get(m["key"])) for r in rows)
    ]


def rank_recency_at_50(rows, method_keys):
    ranked = [eval_flat(rows, key, 0.50) for key in method_keys]
    ranked.sort(key=lambda x: (x["mean_cohort_accuracy"], x["mean_event_accuracy"]), reverse=True)
    return ranked


def best_flat_by_method(rows, method_keys):
    out = []
    for key in method_keys:
        best = rank_flat(rows, key)[0]
        out.append(best)
    out.sort(key=lambda x: (x["mean_cohort_accuracy"], x["mean_event_accuracy"]), reverse=True)
    return out


def rank_combined(rows, method_keys):
    ranked = []
    for method_key in method_keys:
        for start in STARTS:
            for decay in DECAYS:
                for floor in FLOORS:
                    ranked.append(eval_dynamic(rows, method_key, start, floor, decay))
    ranked.sort(key=lambda x: (x["mean_cohort_accuracy"], x["mean_event_accuracy"]), reverse=True)
    return ranked


def slim(result):
    keep = [
        "online_method", "irl_weight", "start", "floor", "decay_per_day",
        "event_count", "cohort_count", "mean_event_accuracy", "mean_cohort_accuracy",
    ]
    return {k: result[k] for k in keep if k in result}


def main():
    rows, start_date, end_date = load_rows()
    cohort_dates = {}
    for r in rows:
        cohort_dates[r["cohort_id"]] = min(cohort_dates.get(r["cohort_id"], r["date"]), r["date"])
    ordered_cohorts = sorted(cohort_dates, key=lambda c: (cohort_dates[c], c))
    if len(ordered_cohorts) <= HOLDOUT_TRAIN_COHORTS:
        raise RuntimeError("Not enough recent cohorts for chronological holdout")

    complete_methods = complete_method_keys(rows)
    method_coverage = []
    for method in ONLINE_METHODS:
        key = method["key"]
        method_coverage.append({
            "key": key,
            "label": method["label"],
            "event_count": sum(bool(r["online_methods"].get(key)) for r in rows),
            "cohort_count": len({r["cohort_id"] for r in rows if r["online_methods"].get(key)}),
            "complete": key in complete_methods,
            "mean_online_events_used": mean(r["online_event_counts_used"].get(key, 0) for r in rows),
        })

    flat_equal = rank_flat(rows, "equal")
    recency_50 = rank_recency_at_50(rows, complete_methods)
    flat_by_method = best_flat_by_method(rows, complete_methods)
    combined = rank_combined(rows, complete_methods)

    baseline_online = eval_flat(rows, "equal", 0.0)
    baseline_irl = eval_flat(rows, "equal", 1.0)
    baseline_50 = eval_flat(rows, "equal", 0.5)

    train_ids = set(ordered_cohorts[:HOLDOUT_TRAIN_COHORTS])
    test_ids = set(ordered_cohorts[HOLDOUT_TRAIN_COHORTS:])
    train = [r for r in rows if r["cohort_id"] in train_ids]
    test = [r for r in rows if r["cohort_id"] in test_ids]

    train_complete_methods = [key for key in complete_methods if all(bool(r["online_methods"].get(key)) for r in train + test)]

    selected_flat = rank_flat(train, "equal")[0]
    holdout_flat = eval_flat(test, "equal", selected_flat["irl_weight"])

    selected_recency_50 = rank_recency_at_50(train, train_complete_methods)[0]
    holdout_recency_50 = eval_flat(test, selected_recency_50["online_method"], 0.50)

    selected_flat_recency = best_flat_by_method(train, train_complete_methods)[0]
    holdout_flat_recency = eval_flat(test, selected_flat_recency["online_method"], selected_flat_recency["irl_weight"])

    selected_combined = rank_combined(train, train_complete_methods)[0]
    holdout_combined = eval_dynamic(
        test,
        selected_combined["online_method"],
        selected_combined["start"],
        selected_combined["floor"],
        selected_combined["decay_per_day"],
    )

    holdout_baselines = {
        "online_only": slim(eval_flat(test, "equal", 0.0)),
        "irl_only": slim(eval_flat(test, "equal", 1.0)),
        "flat_50_50": slim(eval_flat(test, "equal", 0.5)),
    }

    out = {
        "research_questions": [
            "Do flat IRL/Online splits other than 50/50 improve recent-year prediction accuracy?",
            "Does recency-weighting Online evidence toward the target tournament improve accuracy?",
            "Does recency weighting still help when combined with the owner-requested IRL decay grid?",
        ],
        "evidence_window": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "sample": {
            "event_count": len(rows),
            "cohort_count": len(ordered_cohorts),
            "cohorts": [{"cohort_id": c, "date": cohort_dates[c]} for c in ordered_cohorts],
            "selection": ">=95% IRL capture, settled-format, complete latest-IRL and post-major Online components",
        },
        "metric": "Cohort-weighted Field Accuracy; named archetypes only, frozen historical windows",
        "online_recency_semantics": {
            "event_size": "Deck/player-entry counts remain the base weight; each event's entries are multiplied by its recency factor.",
            "equal": "Current aggregation: every Online deck entry since the latest major has factor 1.",
            "windows": "Only Online events within N days of the target cutoff receive weight; other post-major events receive zero.",
            "linear": "Within each target's post-major evidence span, newest Online event factor=1 and oldest factor=0, with linear interpolation.",
            "exponential": "Event factor halves every specified half-life days before the target cutoff.",
        },
        "method_coverage": method_coverage,
        "baselines": {
            "online_only": slim(baseline_online),
            "irl_only": slim(baseline_irl),
            "flat_50_50": slim(baseline_50),
        },
        "flat_splits_equal_online": {
            "weights_tested": FLAT_IRL_WEIGHTS,
            "best": slim(flat_equal[0]),
            "ranking": [slim(r) for r in flat_equal],
        },
        "recency_at_flat_50_50": {
            "best": slim(recency_50[0]),
            "ranking": [slim(r) for r in recency_50],
        },
        "best_flat_split_by_online_method": {
            "best": slim(flat_by_method[0]),
            "ranking": [slim(r) for r in flat_by_method],
        },
        "combined_recency_plus_dynamic_irl": {
            "candidate_count": len(combined),
            "grid": {
                "starts": STARTS,
                "decays_per_day": DECAYS,
                "floors": FLOORS,
                "online_methods": complete_methods,
            },
            "best": slim(combined[0]),
            "top_25": [slim(r) for r in combined[:25]],
        },
        "fixed_chronological_holdout": {
            "train_cohorts": ordered_cohorts[:HOLDOUT_TRAIN_COHORTS],
            "test_cohorts": ordered_cohorts[HOLDOUT_TRAIN_COHORTS:],
            "flat_equal_online": {
                "selected_on_training": slim(selected_flat),
                "holdout": slim(holdout_flat),
            },
            "recency_at_50_50": {
                "selected_on_training": slim(selected_recency_50),
                "holdout": slim(holdout_recency_50),
            },
            "flat_plus_recency": {
                "selected_on_training": slim(selected_flat_recency),
                "holdout": slim(holdout_flat_recency),
            },
            "combined_recency_plus_dynamic_irl": {
                "selected_on_training": slim(selected_combined),
                "holdout": slim(holdout_combined),
            },
            "baselines": holdout_baselines,
            "warning": "Only five independent holdout cohorts; directional validation, not decisive model selection.",
        },
        "interpretation_boundary": "Full-period winners are in-sample. The five-cohort chronological holdout is the stronger check, but remains small. No production formula change is authorised.",
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    RESDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    # Compact human-readable report.
    method_label = lambda key: METHOD_BY_KEY[key]["label"]
    fbest = out["flat_splits_equal_online"]["best"]
    rbest = out["recency_at_flat_50_50"]["best"]
    frbest = out["best_flat_split_by_online_method"]["best"]
    cbest = out["combined_recency_plus_dynamic_irl"]["best"]
    h = out["fixed_chronological_holdout"]

    lines = [
        "# Flat splits and Online-recency analysis",
        "",
        f"Evidence window: **{start_date.isoformat()} to {end_date.isoformat()}**; **{len(rows)} tournaments / {len(ordered_cohorts)} independent cohorts**.",
        "",
        "## Baselines",
        "",
        "| Model | Cohort accuracy |",
        "|---|---:|",
        f"| 100% Online | {baseline_online['mean_cohort_accuracy']:.2f}% |",
        f"| 100% IRL | {baseline_irl['mean_cohort_accuracy']:.2f}% |",
        f"| Flat 50/50 | {baseline_50['mean_cohort_accuracy']:.2f}% |",
        "",
        "## 1. Flat split sweep (equal/current Online aggregation)",
        "",
        f"Best flat split: **{fbest['irl_weight']*100:.0f}% IRL / {(1-fbest['irl_weight'])*100:.0f}% Online = {fbest['mean_cohort_accuracy']:.2f}%**.",
        "",
        "| IRL / Online | Accuracy |",
        "|---|---:|",
    ]
    for r in out["flat_splits_equal_online"]["ranking"]:
        lines.append(f"| {r['irl_weight']*100:.0f}% / {(1-r['irl_weight'])*100:.0f}% | {r['mean_cohort_accuracy']:.2f}% |")

    lines += [
        "",
        "## 2. Online recency at fixed 50/50 IRL/Online",
        "",
        f"Best recency method at 50/50: **{method_label(rbest['online_method'])} = {rbest['mean_cohort_accuracy']:.2f}%**.",
        "",
        "| Online treatment | Accuracy |",
        "|---|---:|",
    ]
    for r in out["recency_at_flat_50_50"]["ranking"]:
        lines.append(f"| {method_label(r['online_method'])} | {r['mean_cohort_accuracy']:.2f}% |")

    lines += [
        "",
        "## 3. Best flat split after allowing Online recency",
        "",
        f"Best: **{frbest['irl_weight']*100:.0f}% IRL / {(1-frbest['irl_weight'])*100:.0f}% Online with {method_label(frbest['online_method'])} = {frbest['mean_cohort_accuracy']:.2f}%**.",
        "",
        "## 4. Combined Online recency + dynamic IRL grid",
        "",
        f"Best in-sample combination: **{cbest['start']*100:.0f}% IRL start, -{cbest['decay_per_day']*100:.0f}pp/day, {cbest['floor']*100:.0f}% floor + {method_label(cbest['online_method'])} = {cbest['mean_cohort_accuracy']:.2f}%**.",
        "",
        "## 5. Fixed chronological holdout",
        "",
        f"Tune on first {HOLDOUT_TRAIN_COHORTS} cohorts; score on final {len(ordered_cohorts)-HOLDOUT_TRAIN_COHORTS} untouched cohorts.",
        "",
        "| Selection family | Training-selected model | Holdout accuracy |",
        "|---|---|---:|",
        f"| Flat split, equal Online | {h['flat_equal_online']['selected_on_training']['irl_weight']*100:.0f}% IRL / {(1-h['flat_equal_online']['selected_on_training']['irl_weight'])*100:.0f}% Online | {h['flat_equal_online']['holdout']['mean_cohort_accuracy']:.2f}% |",
        f"| Recency at 50/50 | {method_label(h['recency_at_50_50']['selected_on_training']['online_method'])} | {h['recency_at_50_50']['holdout']['mean_cohort_accuracy']:.2f}% |",
        f"| Flat split + recency | {h['flat_plus_recency']['selected_on_training']['irl_weight']*100:.0f}% IRL + {method_label(h['flat_plus_recency']['selected_on_training']['online_method'])} | {h['flat_plus_recency']['holdout']['mean_cohort_accuracy']:.2f}% |",
        f"| Dynamic IRL + recency | {h['combined_recency_plus_dynamic_irl']['selected_on_training']['start']*100:.0f}% start / -{h['combined_recency_plus_dynamic_irl']['selected_on_training']['decay_per_day']*100:.0f}pp/day / {h['combined_recency_plus_dynamic_irl']['selected_on_training']['floor']*100:.0f}% floor + {method_label(h['combined_recency_plus_dynamic_irl']['selected_on_training']['online_method'])} | **{h['combined_recency_plus_dynamic_irl']['holdout']['mean_cohort_accuracy']:.2f}%** |",
        f"| Flat 50/50 baseline | Equal/current Online | {h['baselines']['flat_50_50']['mean_cohort_accuracy']:.2f}% |",
        f"| 100% IRL baseline | — | {h['baselines']['irl_only']['mean_cohort_accuracy']:.2f}% |",
        f"| 100% Online baseline | Equal/current Online | {h['baselines']['online_only']['mean_cohort_accuracy']:.2f}% |",
        "",
        "**Interpretation boundary:** full-period winners are in-sample. The chronological holdout is more informative, but has only five independent test cohorts.",
    ]
    (RESDIR / "flat-and-online-recency.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "flat_best": fbest,
        "recency_50_best": rbest,
        "flat_recency_best": frbest,
        "combined_best": cbest,
        "holdout": h,
        "method_coverage": method_coverage,
    }, indent=2))


if __name__ == "__main__":
    main()
