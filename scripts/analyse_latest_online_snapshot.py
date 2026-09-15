#!/usr/bin/env python3
"""Test latest-N large Online tournament snapshots against the latest IRL cohort.

Uses the same frozen recent-year complete-case settled sample as the parent weighting
experiments. No ingestion, archetype identity, format assignment, target eligibility,
or prediction-window membership is changed.

Online snapshot scenarios:
- latest N = 1,2,3,4,5 post-major same-format Online tournaments;
- minimum event size = 50,100,150,200 players;
- selected Online tournaments are aggregated by deck/player entries (not event-equal).

For each full-coverage Online definition we test:
- fixed 50/50;
- all flat IRL shares 0-100% in 5pp steps;
- the existing 225-rule dynamic IRL start/decay/floor grid.

Primary metric: cohort-weighted Field Accuracy. Model selection is reported in-sample
and with the same chronological guard used by the parent experiments: train on the
first six recent cohorts, score on the final five untouched cohorts.
"""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import analyse_last_year_weighting as base
import score_baseline_models as scorer

ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "data" / "processed" / "model-results" / "baselines.json"
ONLINE_TAGS = ROOT / "data" / "processed" / "format-tags" / "online-events.json"
OUTDIR = ROOT / "data" / "processed" / "last-year-weighting" / "latest-online-snapshot"
RESDIR = ROOT / "results" / "last-year-weighting"

NS = [1, 2, 3, 4, 5]
MIN_PLAYERS = [50, 100, 150, 200]
FLAT_IRL_WEIGHTS = [i / 100.0 for i in range(0, 101, 5)]
STARTS = [1.00, 0.95, 0.90, 0.85, 0.80]
DECAYS = [0.01, 0.02, 0.03, 0.04, 0.05]
FLOORS = [0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20, 0.15, 0.10]
HOLDOUT_TRAIN_COHORTS = 6


def mean(xs):
    xs = list(xs)
    return statistics.fmean(xs) if xs else None


def cohort_mean(scored):
    by = defaultdict(list)
    for r in scored:
        by[r["cohort_id"]].append(r["accuracy"])
    return mean(mean(v) for v in by.values())


def scenario_key(n, min_players):
    return f"latest_{n}_min_{min_players}"


def scenario_label(n, min_players):
    return f"Latest {n} Online >= {min_players} players"


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
        post_major_ids = [str(i) for i in half_m.get("online_event_ids", [])]

        # Verify all evidence being considered is known to the frozen target model.
        candidate_ids = [
            i for i in post_major_ids
            if i in online_meta and i in online_counts
        ]
        candidate_ids.sort(key=lambda i: scorer.parse_dt(online_meta[i]["start_at"]), reverse=True)

        snapshots = {}
        selected_ids = {}
        for min_players in MIN_PLAYERS:
            eligible = [
                i for i in candidate_ids
                if int(online_meta[i].get("players") or 0) >= min_players
            ]
            for n in NS:
                key = scenario_key(n, min_players)
                chosen = eligible[:n]
                # Require the full requested N; otherwise this scenario is unavailable
                # for this target and cannot silently collapse to a different N.
                if len(chosen) < n:
                    snapshots[key] = {}
                    selected_ids[key] = chosen
                    continue
                counts = Counter()
                for event_id in chosen:
                    counts.update(online_counts[event_id])
                snapshots[key] = scorer.normalise(counts)
                selected_ids[key] = chosen

        # Broad post-major comparator used by the existing 50/50/dynamic blend.
        broad_counts = Counter()
        for event_id in candidate_ids:
            broad_counts.update(online_counts[event_id])
        snapshots["all_post_major"] = scorer.normalise(broad_counts)
        selected_ids["all_post_major"] = candidate_ids

        rows.append({
            "target_id": str(t["target_id"]),
            "target_name": t["target_name"],
            "date": t["target_start_date"],
            "cohort_id": t["cohort_id"],
            "days_since_major": int(t["days_since_major"]),
            "irl": irl,
            "actual": actual,
            "snapshots": snapshots,
            "selected_ids": selected_ids,
        })

    if not rows:
        raise RuntimeError("No recent complete-case settled targets found")
    return rows, start_date, end_date, online_meta


def evaluate(rows, snapshot_key, weight_fn):
    scored = []
    for r in rows:
        online = r["snapshots"].get(snapshot_key) or {}
        if not online:
            continue
        w = max(0.0, min(1.0, float(weight_fn(r))))
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


def eval_flat(rows, snapshot_key, irl_weight):
    out = evaluate(rows, snapshot_key, lambda r: irl_weight)
    out.update({"snapshot": snapshot_key, "irl_weight": irl_weight})
    return out


def eval_dynamic(rows, snapshot_key, start, floor, decay):
    out = evaluate(rows, snapshot_key, lambda r: base.weight(r["days_since_major"], start, floor, decay))
    out.update({
        "snapshot": snapshot_key,
        "start": start,
        "floor": floor,
        "decay_per_day": decay,
    })
    return out


def rank_flat(rows, snapshot_key):
    ranked = [eval_flat(rows, snapshot_key, w) for w in FLAT_IRL_WEIGHTS]
    ranked.sort(key=lambda x: (
        x["mean_cohort_accuracy"] if x["mean_cohort_accuracy"] is not None else -1,
        x["mean_event_accuracy"] if x["mean_event_accuracy"] is not None else -1,
    ), reverse=True)
    return ranked


def rank_dynamic(rows, snapshot_keys):
    ranked = []
    for snapshot_key in snapshot_keys:
        for start in STARTS:
            for decay in DECAYS:
                for floor in FLOORS:
                    ranked.append(eval_dynamic(rows, snapshot_key, start, floor, decay))
    ranked.sort(key=lambda x: (
        x["mean_cohort_accuracy"] if x["mean_cohort_accuracy"] is not None else -1,
        x["mean_event_accuracy"] if x["mean_event_accuracy"] is not None else -1,
    ), reverse=True)
    return ranked


def slim(result):
    keys = [
        "snapshot", "irl_weight", "start", "floor", "decay_per_day",
        "event_count", "cohort_count", "mean_event_accuracy", "mean_cohort_accuracy",
    ]
    return {k: result[k] for k in keys if k in result}


def main():
    rows, start_date, end_date, online_meta = load_rows()
    cohort_dates = {}
    for r in rows:
        cohort_dates[r["cohort_id"]] = min(cohort_dates.get(r["cohort_id"], r["date"]), r["date"])
    ordered_cohorts = sorted(cohort_dates, key=lambda c: (cohort_dates[c], c))
    if len(ordered_cohorts) <= HOLDOUT_TRAIN_COHORTS:
        raise RuntimeError("Not enough recent cohorts for chronological holdout")

    scenario_keys = [scenario_key(n, p) for p in MIN_PLAYERS for n in NS]
    labels = {scenario_key(n, p): scenario_label(n, p) for p in MIN_PLAYERS for n in NS}
    labels["all_post_major"] = "All qualifying post-major Online events"

    coverage = []
    for key in scenario_keys:
        available = [r for r in rows if r["snapshots"].get(key)]
        selected_counts = [len(r["selected_ids"].get(key, [])) for r in rows]
        selected_players = []
        selected_ages = []
        for r in rows:
            for event_id in r["selected_ids"].get(key, []):
                meta = online_meta[event_id]
                selected_players.append(int(meta.get("players") or 0))
                target = date.fromisoformat(r["date"])
                event_day = scorer.parse_dt(meta["start_at"]).date()
                selected_ages.append((target - event_day).days)
        coverage.append({
            "snapshot": key,
            "label": labels[key],
            "event_count": len(available),
            "cohort_count": len({r["cohort_id"] for r in available}),
            "complete": len(available) == len(rows),
            "mean_selected_tournaments": mean(selected_counts),
            "mean_selected_event_players": mean(selected_players),
            "mean_selected_event_age_days": mean(selected_ages),
        })

    complete_snapshot_keys = [c["snapshot"] for c in coverage if c["complete"]]
    if not complete_snapshot_keys:
        raise RuntimeError("No latest-N scenarios have full sample coverage")

    # Broad evidence comparators.
    broad_50 = eval_flat(rows, "all_post_major", 0.50)
    broad_best_flat = rank_flat(rows, "all_post_major")[0]
    broad_dynamic = rank_dynamic(rows, ["all_post_major"])[0]

    # Snapshot results at fixed 50/50 and with each snapshot's best flat split.
    fixed_50 = [slim(eval_flat(rows, key, 0.50)) for key in complete_snapshot_keys]
    fixed_50.sort(key=lambda x: (x["mean_cohort_accuracy"], x["mean_event_accuracy"]), reverse=True)

    best_flat_each = [slim(rank_flat(rows, key)[0]) for key in complete_snapshot_keys]
    best_flat_each.sort(key=lambda x: (x["mean_cohort_accuracy"], x["mean_event_accuracy"]), reverse=True)

    # Joint dynamic search across all full-coverage snapshot definitions.
    dynamic_ranked = rank_dynamic(rows, complete_snapshot_keys)

    # Chronological guard: all selection decisions use first six cohorts only.
    train_ids = set(ordered_cohorts[:HOLDOUT_TRAIN_COHORTS])
    test_ids = set(ordered_cohorts[HOLDOUT_TRAIN_COHORTS:])
    train = [r for r in rows if r["cohort_id"] in train_ids]
    test = [r for r in rows if r["cohort_id"] in test_ids]

    # Only methods available on every train+test target can be selected.
    holdout_complete_keys = [
        key for key in complete_snapshot_keys
        if all(bool(r["snapshots"].get(key)) for r in train + test)
    ]

    train_fixed_50 = [eval_flat(train, key, 0.50) for key in holdout_complete_keys]
    train_fixed_50.sort(key=lambda x: (x["mean_cohort_accuracy"], x["mean_event_accuracy"]), reverse=True)
    selected_fixed_50 = train_fixed_50[0]
    holdout_fixed_50 = eval_flat(test, selected_fixed_50["snapshot"], 0.50)

    train_flat_candidates = []
    for key in holdout_complete_keys:
        train_flat_candidates.extend(rank_flat(train, key))
    train_flat_candidates.sort(key=lambda x: (x["mean_cohort_accuracy"], x["mean_event_accuracy"]), reverse=True)
    selected_flat = train_flat_candidates[0]
    holdout_flat = eval_flat(test, selected_flat["snapshot"], selected_flat["irl_weight"])

    selected_dynamic = rank_dynamic(train, holdout_complete_keys)[0]
    holdout_dynamic = eval_dynamic(
        test,
        selected_dynamic["snapshot"],
        selected_dynamic["start"],
        selected_dynamic["floor"],
        selected_dynamic["decay_per_day"],
    )

    # Broad comparators on identical holdout.
    holdout_broad_50 = eval_flat(test, "all_post_major", 0.50)
    selected_broad_flat = rank_flat(train, "all_post_major")[0]
    holdout_broad_flat = eval_flat(test, "all_post_major", selected_broad_flat["irl_weight"])
    selected_broad_dynamic = rank_dynamic(train, ["all_post_major"])[0]
    holdout_broad_dynamic = eval_dynamic(
        test,
        "all_post_major",
        selected_broad_dynamic["start"],
        selected_broad_dynamic["floor"],
        selected_broad_dynamic["decay_per_day"],
    )

    out = {
        "research_question": "Can a latest-N snapshot of large Online tournaments predict recent settled IRL fields better than aggregating all qualifying post-major Online evidence?",
        "evidence_window": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "sample": {
            "event_count": len(rows),
            "cohort_count": len(ordered_cohorts),
            "cohorts": [{"cohort_id": c, "date": cohort_dates[c]} for c in ordered_cohorts],
            "selection": ">=95% IRL capture, settled-format, complete latest-IRL and post-major Online components",
        },
        "metric": "Cohort-weighted Field Accuracy; named archetypes only, frozen historical windows",
        "scenario_definition": {
            "latest_n": NS,
            "minimum_players": MIN_PLAYERS,
            "selection": "Latest N qualifying post-major same-format Online tournaments before target cutoff",
            "within_snapshot_weighting": "Deck/player-entry weighted across selected tournaments",
            "flat_weights": FLAT_IRL_WEIGHTS,
            "dynamic_grid": {"starts": STARTS, "decays_per_day": DECAYS, "floors": FLOORS},
        },
        "coverage": coverage,
        "complete_snapshot_keys": complete_snapshot_keys,
        "labels": labels,
        "broad_post_major_comparators": {
            "flat_50_50": slim(broad_50),
            "best_flat_in_sample": slim(broad_best_flat),
            "best_dynamic_in_sample": slim(broad_dynamic),
        },
        "snapshot_fixed_50_50": {
            "best": fixed_50[0],
            "ranking": fixed_50,
        },
        "snapshot_best_flat": {
            "best": best_flat_each[0],
            "ranking": best_flat_each,
        },
        "snapshot_dynamic": {
            "candidate_count": len(dynamic_ranked),
            "best": slim(dynamic_ranked[0]),
            "top_25": [slim(r) for r in dynamic_ranked[:25]],
        },
        "fixed_chronological_holdout": {
            "train_cohorts": ordered_cohorts[:HOLDOUT_TRAIN_COHORTS],
            "test_cohorts": ordered_cohorts[HOLDOUT_TRAIN_COHORTS:],
            "snapshot_fixed_50_50": {
                "selected_on_training": slim(selected_fixed_50),
                "holdout": slim(holdout_fixed_50),
            },
            "snapshot_flat": {
                "selected_on_training": slim(selected_flat),
                "holdout": slim(holdout_flat),
            },
            "snapshot_dynamic": {
                "selected_on_training": slim(selected_dynamic),
                "holdout": slim(holdout_dynamic),
            },
            "broad_post_major": {
                "flat_50_50": slim(holdout_broad_50),
                "selected_flat_on_training": slim(selected_broad_flat),
                "selected_flat_holdout": slim(holdout_broad_flat),
                "selected_dynamic_on_training": slim(selected_broad_dynamic),
                "selected_dynamic_holdout": slim(holdout_broad_dynamic),
            },
            "warning": "Only five independent holdout cohorts; directional validation, not decisive model selection.",
        },
        "interpretation_boundary": "Full-period rankings are in-sample. Scenarios without full 16-event/11-cohort coverage are reported but excluded from headline like-for-like model selection. The five-cohort chronological holdout is the stronger validation check but remains small.",
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    RESDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    def label_of(result):
        return labels.get(result.get("snapshot"), result.get("snapshot", ""))

    lines = [
        "# Latest large-Online snapshot analysis",
        "",
        f"Evidence window: **{start_date.isoformat()} to {end_date.isoformat()}**; **{len(rows)} tournaments / {len(ordered_cohorts)} independent cohorts**.",
        "",
        "Question: can a small snapshot of the latest large Online tournaments beat aggregating all qualifying Online evidence since the previous IRL major?",
        "",
        "## Scenario coverage",
        "",
        "| Online snapshot | Events | Cohorts | Full coverage? | Mean selected-event size | Mean age to target |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for c in coverage:
        lines.append(
            f"| {c['label']} | {c['event_count']} | {c['cohort_count']} | {'Yes' if c['complete'] else 'No'} | "
            f"{c['mean_selected_event_players']:.0f} | {c['mean_selected_event_age_days']:.1f}d |"
        )

    lines += [
        "",
        "## Broad post-major Online comparators",
        "",
        "| Model | Accuracy |",
        "|---|---:|",
        f"| All post-major Online, flat 50/50 | {broad_50['mean_cohort_accuracy']:.2f}% |",
        f"| All post-major Online, best flat ({broad_best_flat['irl_weight']*100:.0f}% IRL) | {broad_best_flat['mean_cohort_accuracy']:.2f}% |",
        f"| All post-major Online, best dynamic ({broad_dynamic['start']*100:.0f}% start / -{broad_dynamic['decay_per_day']*100:.0f}pp/day / {broad_dynamic['floor']*100:.0f}% floor) | {broad_dynamic['mean_cohort_accuracy']:.2f}% |",
        "",
        "## Best snapshot results in-sample",
        "",
        f"At fixed 50/50: **{label_of(fixed_50[0])} = {fixed_50[0]['mean_cohort_accuracy']:.2f}%**.",
        f"With flat IRL split tuned: **{label_of(best_flat_each[0])}, {best_flat_each[0]['irl_weight']*100:.0f}% IRL / {(1-best_flat_each[0]['irl_weight'])*100:.0f}% Online = {best_flat_each[0]['mean_cohort_accuracy']:.2f}%**.",
        f"With dynamic IRL rule tuned: **{label_of(dynamic_ranked[0])}, {dynamic_ranked[0]['start']*100:.0f}% start / -{dynamic_ranked[0]['decay_per_day']*100:.0f}pp/day / {dynamic_ranked[0]['floor']*100:.0f}% floor = {dynamic_ranked[0]['mean_cohort_accuracy']:.2f}%**.",
        "",
        "### Top full-coverage snapshots with their own best flat split",
        "",
        "| Snapshot | Best IRL split | Accuracy |",
        "|---|---:|---:|",
    ]
    for r in best_flat_each[:10]:
        lines.append(f"| {label_of(r)} | {r['irl_weight']*100:.0f}% | {r['mean_cohort_accuracy']:.2f}% |")

    h = out["fixed_chronological_holdout"]
    sf = h["snapshot_fixed_50_50"]
    sflat = h["snapshot_flat"]
    sdyn = h["snapshot_dynamic"]
    broad = h["broad_post_major"]
    lines += [
        "",
        "## Fixed chronological holdout",
        "",
        "Tune on first 6 cohorts; score the frozen selection on final 5 untouched cohorts.",
        "",
        "| Family | Training selection | Holdout accuracy |",
        "|---|---|---:|",
        f"| Snapshot at fixed 50/50 | {label_of(sf['selected_on_training'])} | {sf['holdout']['mean_cohort_accuracy']:.2f}% |",
        f"| Snapshot + flat split | {label_of(sflat['selected_on_training'])}, {sflat['selected_on_training']['irl_weight']*100:.0f}% IRL | {sflat['holdout']['mean_cohort_accuracy']:.2f}% |",
        f"| Snapshot + dynamic IRL | {label_of(sdyn['selected_on_training'])}, {sdyn['selected_on_training']['start']*100:.0f}%/-{sdyn['selected_on_training']['decay_per_day']*100:.0f}pp/{sdyn['selected_on_training']['floor']*100:.0f}% | {sdyn['holdout']['mean_cohort_accuracy']:.2f}% |",
        f"| Broad Online + flat split | all post-major, {broad['selected_flat_on_training']['irl_weight']*100:.0f}% IRL | {broad['selected_flat_holdout']['mean_cohort_accuracy']:.2f}% |",
        f"| Broad Online + dynamic IRL | all post-major, {broad['selected_dynamic_on_training']['start']*100:.0f}%/-{broad['selected_dynamic_on_training']['decay_per_day']*100:.0f}pp/{broad['selected_dynamic_on_training']['floor']*100:.0f}% | {broad['selected_dynamic_holdout']['mean_cohort_accuracy']:.2f}% |",
        "",
        "**Interpretation boundary:** full-period winners are in-sample. The five-cohort chronological holdout is more informative but still small; incomplete high-threshold scenarios are not promoted over full-coverage alternatives.",
    ]
    (RESDIR / "latest-online-snapshot.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "complete_snapshot_keys": complete_snapshot_keys,
        "best_fixed_50": slim(fixed_50[0]),
        "best_flat": slim(best_flat_each[0]),
        "best_dynamic": slim(dynamic_ranked[0]),
        "holdout": out["fixed_chronological_holdout"],
    }, indent=2))


if __name__ == "__main__":
    main()
