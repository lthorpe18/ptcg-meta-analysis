#!/usr/bin/env python3
"""Sensitivity check: score settled-format methods on actual top 20 decks + Other.

Uses the same 34 complete-case settled targets as the blend-weight test. The top 20
archetypes are chosen from each target's *actual* Day-1 field; every remaining
archetype is aggregated into one Other bucket. This preserves 100% of field mass and
avoids artificially inflating accuracy by dropping the long tail.

The blended method is the current best in-sample rule from the existing full-field
grid search: 80% theoretical day-0 IRL start, 1 percentage point/day decay, 55% floor.
It is NOT re-tuned on the top-20 score.
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFILE = ROOT / "data" / "processed" / "model-results" / "baselines.json"
OUTDIR = ROOT / "data" / "processed" / "top20-sensitivity"
RESDIR = ROOT / "results" / "top20-sensitivity"

BEST_START = 0.80
BEST_FLOOR = 0.55
BEST_DECAY = 0.010
TOP_N = 20
EPS = 1e-10


def mean(xs):
    xs = list(xs)
    return statistics.fmean(xs) if xs else None


def pred_map(model):
    return {str(r["key"]): float(r["predicted_pct"]) / 100.0 for r in model.get("prediction", [])}


def actual_map(model):
    return {str(r["key"]): float(r["actual_pct"]) / 100.0 for r in model.get("prediction", [])}


def normalise(dist):
    total = sum(max(0.0, float(v)) for v in dist.values())
    return {k: max(0.0, float(v)) / total for k, v in dist.items()} if total else {}


def reconstruct_online_since_major(irl, fifty):
    keys = set(irl) | set(fifty)
    raw = {k: 2.0 * fifty.get(k, 0.0) - irl.get(k, 0.0) for k in keys}
    out = {k: (0.0 if -EPS < v < 0.0 else v) for k, v in raw.items()}
    if min(out.values(), default=0.0) < -1e-7:
        raise RuntimeError("Could not reconstruct Online-since-major component cleanly")
    return normalise({k: max(0.0, v) for k, v in out.items()})


def blend(irl, online, irl_weight):
    keys = set(irl) | set(online)
    return normalise({
        k: irl_weight * irl.get(k, 0.0) + (1.0 - irl_weight) * online.get(k, 0.0)
        for k in keys
    })


def weight(days):
    return max(BEST_FLOOR, min(BEST_START, BEST_START - BEST_DECAY * days))


def accuracy(pred, actual):
    keys = set(pred) | set(actual)
    return 100.0 * (1.0 - 0.5 * sum(abs(pred.get(k, 0.0) - actual.get(k, 0.0)) for k in keys))


def top_n_plus_other(dist, top_keys):
    top_keys = list(top_keys)
    kept = {k: dist.get(k, 0.0) for k in top_keys}
    kept["__OTHER__"] = max(0.0, 1.0 - sum(kept.values()))
    return normalise(kept)


def cohort_mean(rows, key):
    by = defaultdict(list)
    for row in rows:
        by[row["cohort_id"]].append(row[key])
    return mean(mean(values) for values in by.values())


def main():
    data = json.loads(INFILE.read_text(encoding="utf-8"))
    rows = []

    for target in data.get("targets", []):
        if not target.get("target_eligible_ge_95") or target.get("window_class") != "settled":
            continue
        models = target.get("models", {})
        online_m = models.get("online_only", {})
        irl_m = models.get("irl_only", {})
        fifty_m = models.get("fifty_fifty", {})
        current_m = models.get("current_v2_1", {})
        if not all(m.get("available") for m in (online_m, irl_m, fifty_m, current_m)):
            continue

        actual = actual_map(irl_m)
        online_all = pred_map(online_m)
        irl = pred_map(irl_m)
        fifty = pred_map(fifty_m)
        online_since = reconstruct_online_since_major(irl, fifty)
        w = weight(int(target["days_since_major"]))
        best_blend = blend(irl, online_since, w)

        top_keys = [k for k, _ in sorted(actual.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]]
        actual_top = top_n_plus_other(actual, top_keys)

        rows.append({
            "target_id": str(target["target_id"]),
            "target_name": target["target_name"],
            "cohort_id": target["cohort_id"],
            "days_since_major": int(target["days_since_major"]),
            "best_blend_irl_weight": w,
            "full_online_only": accuracy(online_all, actual),
            "full_irl_only": accuracy(irl, actual),
            "full_best_blend": accuracy(best_blend, actual),
            "top20_online_only": accuracy(top_n_plus_other(online_all, top_keys), actual_top),
            "top20_irl_only": accuracy(top_n_plus_other(irl, top_keys), actual_top),
            "top20_best_blend": accuracy(top_n_plus_other(best_blend, top_keys), actual_top),
        })

    if not rows:
        raise RuntimeError("No complete-case settled targets found")

    score_keys = [
        "full_online_only", "full_irl_only", "full_best_blend",
        "top20_online_only", "top20_irl_only", "top20_best_blend",
    ]
    summary = {
        key: {
            "event_weighted_accuracy": mean(r[key] for r in rows),
            "cohort_weighted_accuracy": cohort_mean(rows, key),
        }
        for key in score_keys
    }

    out = {
        "event_count": len(rows),
        "cohort_count": len(set(r["cohort_id"] for r in rows)),
        "top_n": TOP_N,
        "top20_definition": "Top 20 archetypes in each target's actual Day-1 field; all remaining field mass aggregated into Other; no renormalisation after dropping decks because no decks are dropped.",
        "best_blend_rule": {
            "start_irl": BEST_START,
            "decay_per_day": BEST_DECAY,
            "floor_irl": BEST_FLOOR,
            "note": "Chosen from the existing full-field in-sample grid; not re-tuned for the top-20 sensitivity test."
        },
        "summary": summary,
        "rows": rows,
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    RESDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "top20-sensitivity.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    lines = [
        "# Top-20 + Other sensitivity test",
        "",
        f"Settled complete-case sample: {out['event_count']} tournaments across {out['cohort_count']} independent major-weekend cohorts.",
        "",
        "Top-20 scoring keeps the 20 largest archetypes in each tournament's actual Day-1 field and combines every other archetype into one Other bucket. No field mass is discarded.",
        "",
        "The best blended rule is fixed from the prior full-field grid (80% start, 1pp/day decay, 55% floor); it is not re-tuned on this sensitivity test.",
        "",
        "| Method | Full field | Top 20 + Other |",
        "|---|---:|---:|",
        f"| Online only | {summary['full_online_only']['cohort_weighted_accuracy']:.2f}% | {summary['top20_online_only']['cohort_weighted_accuracy']:.2f}% |",
        f"| Latest IRL only | {summary['full_irl_only']['cohort_weighted_accuracy']:.2f}% | {summary['top20_irl_only']['cohort_weighted_accuracy']:.2f}% |",
        f"| Best blend | {summary['full_best_blend']['cohort_weighted_accuracy']:.2f}% | {summary['top20_best_blend']['cohort_weighted_accuracy']:.2f}% |",
        "",
        "Headline values are cohort/weekend-weighted so weekends with multiple contemporaneous majors do not receive extra weight.",
    ]
    (RESDIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
