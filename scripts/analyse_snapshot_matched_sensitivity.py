#!/usr/bin/env python3
"""Matched-subset sensitivity for incomplete latest-N large-Online snapshots.

This supplements analyse_latest_online_snapshot.py. Each snapshot definition is
compared with the broad all-post-major Online model on exactly the targets where the
snapshot has its full requested N events. This prevents sparse high-player thresholds
from receiving an unfair comparison against a different sample.
"""
from __future__ import annotations

import json
from pathlib import Path

import analyse_latest_online_snapshot as snap

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "data" / "processed" / "last-year-weighting" / "latest-online-snapshot"
RESDIR = ROOT / "results" / "last-year-weighting"


def slim(result):
    return snap.slim(result)


def best_dynamic(rows, key):
    return snap.rank_dynamic(rows, [key])[0]


def main():
    rows, start_date, end_date, _online_meta = snap.load_rows()
    cohort_dates = {}
    for r in rows:
        cohort_dates[r["cohort_id"]] = min(cohort_dates.get(r["cohort_id"], r["date"]), r["date"])
    ordered_cohorts = sorted(cohort_dates, key=lambda c: (cohort_dates[c], c))
    train_ids = set(ordered_cohorts[: snap.HOLDOUT_TRAIN_COHORTS])
    test_ids = set(ordered_cohorts[snap.HOLDOUT_TRAIN_COHORTS :])
    train_all = [r for r in rows if r["cohort_id"] in train_ids]
    test_all = [r for r in rows if r["cohort_id"] in test_ids]

    labels = {
        snap.scenario_key(n, p): snap.scenario_label(n, p)
        for p in snap.MIN_PLAYERS for n in snap.NS
    }

    sensitivities = []
    holdout_sensitivities = []
    for p in snap.MIN_PLAYERS:
        for n in snap.NS:
            key = snap.scenario_key(n, p)
            subset = [r for r in rows if r["snapshots"].get(key)]
            if not subset:
                continue
            cohort_count = len({r["cohort_id"] for r in subset})
            missing = [r["target_name"] for r in rows if not r["snapshots"].get(key)]

            snapshot_50 = snap.eval_flat(subset, key, 0.50)
            broad_50 = snap.eval_flat(subset, "all_post_major", 0.50)
            snapshot_flat = snap.rank_flat(subset, key)[0]
            broad_flat = snap.rank_flat(subset, "all_post_major")[0]
            snapshot_dynamic = best_dynamic(subset, key)
            broad_dynamic = best_dynamic(subset, "all_post_major")

            sensitivities.append({
                "snapshot": key,
                "label": labels[key],
                "event_count": len(subset),
                "cohort_count": cohort_count,
                "missing_targets": missing,
                "fixed_50": {
                    "snapshot_accuracy": snapshot_50["mean_cohort_accuracy"],
                    "broad_accuracy": broad_50["mean_cohort_accuracy"],
                    "delta_snapshot_minus_broad_pp": snapshot_50["mean_cohort_accuracy"] - broad_50["mean_cohort_accuracy"],
                },
                "best_flat": {
                    "snapshot": slim(snapshot_flat),
                    "broad": slim(broad_flat),
                    "delta_snapshot_minus_broad_pp": snapshot_flat["mean_cohort_accuracy"] - broad_flat["mean_cohort_accuracy"],
                },
                "best_dynamic": {
                    "snapshot": slim(snapshot_dynamic),
                    "broad": slim(broad_dynamic),
                    "delta_snapshot_minus_broad_pp": snapshot_dynamic["mean_cohort_accuracy"] - broad_dynamic["mean_cohort_accuracy"],
                },
            })

            # Secondary chronological sensitivity only when the snapshot is available
            # for every final holdout target. Tune both snapshot and broad comparator
            # on the same subset of training targets where the snapshot is available.
            if all(bool(r["snapshots"].get(key)) for r in test_all):
                train_subset = [r for r in train_all if r["snapshots"].get(key)]
                train_cohorts = len({r["cohort_id"] for r in train_subset})
                if train_cohorts >= 4:
                    selected_snapshot_flat = snap.rank_flat(train_subset, key)[0]
                    selected_broad_flat = snap.rank_flat(train_subset, "all_post_major")[0]
                    holdout_snapshot_flat = snap.eval_flat(test_all, key, selected_snapshot_flat["irl_weight"])
                    holdout_broad_flat = snap.eval_flat(test_all, "all_post_major", selected_broad_flat["irl_weight"])

                    selected_snapshot_dynamic = best_dynamic(train_subset, key)
                    selected_broad_dynamic = best_dynamic(train_subset, "all_post_major")
                    holdout_snapshot_dynamic = snap.eval_dynamic(
                        test_all, key,
                        selected_snapshot_dynamic["start"],
                        selected_snapshot_dynamic["floor"],
                        selected_snapshot_dynamic["decay_per_day"],
                    )
                    holdout_broad_dynamic = snap.eval_dynamic(
                        test_all, "all_post_major",
                        selected_broad_dynamic["start"],
                        selected_broad_dynamic["floor"],
                        selected_broad_dynamic["decay_per_day"],
                    )
                    holdout_sensitivities.append({
                        "snapshot": key,
                        "label": labels[key],
                        "training_event_count": len(train_subset),
                        "training_cohort_count": train_cohorts,
                        "flat": {
                            "selected_snapshot": slim(selected_snapshot_flat),
                            "selected_broad": slim(selected_broad_flat),
                            "snapshot_holdout": slim(holdout_snapshot_flat),
                            "broad_holdout": slim(holdout_broad_flat),
                            "delta_snapshot_minus_broad_pp": holdout_snapshot_flat["mean_cohort_accuracy"] - holdout_broad_flat["mean_cohort_accuracy"],
                        },
                        "dynamic": {
                            "selected_snapshot": slim(selected_snapshot_dynamic),
                            "selected_broad": slim(selected_broad_dynamic),
                            "snapshot_holdout": slim(holdout_snapshot_dynamic),
                            "broad_holdout": slim(holdout_broad_dynamic),
                            "delta_snapshot_minus_broad_pp": holdout_snapshot_dynamic["mean_cohort_accuracy"] - holdout_broad_dynamic["mean_cohort_accuracy"],
                        },
                    })

    sensitivities.sort(
        key=lambda r: (r["best_dynamic"]["delta_snapshot_minus_broad_pp"], r["cohort_count"]),
        reverse=True,
    )
    holdout_sensitivities.sort(
        key=lambda r: r["dynamic"]["delta_snapshot_minus_broad_pp"],
        reverse=True,
    )

    out = {
        "evidence_window": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "purpose": "Matched-subset comparison of latest-N size-threshold Online snapshots versus broad post-major Online evidence.",
        "matched_full_period": sensitivities,
        "chronological_holdout_when_full_test_coverage": holdout_sensitivities,
        "interpretation_boundary": "Matched full-period comparisons are in-sample. Holdout sensitivities only include scenarios available for every final holdout target and may use fewer than six training cohorts when a threshold is unavailable historically.",
    }
    OUTDIR.mkdir(parents=True, exist_ok=True)
    RESDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "matched-sensitivity.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    lines = [
        "# Latest Online snapshot — matched-subset sensitivity",
        "",
        "Incomplete size-threshold scenarios are compared against broad post-major Online evidence on exactly the same targets.",
        "",
        "## Matched full-period comparison",
        "",
        "| Snapshot | Events/cohorts | Flat delta vs broad | Dynamic delta vs broad | Snapshot dynamic accuracy | Broad dynamic accuracy |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in sensitivities:
        lines.append(
            f"| {r['label']} | {r['event_count']}/{r['cohort_count']} | "
            f"{r['best_flat']['delta_snapshot_minus_broad_pp']:+.2f}pp | "
            f"{r['best_dynamic']['delta_snapshot_minus_broad_pp']:+.2f}pp | "
            f"{r['best_dynamic']['snapshot']['mean_cohort_accuracy']:.2f}% | "
            f"{r['best_dynamic']['broad']['mean_cohort_accuracy']:.2f}% |"
        )

    lines += [
        "",
        "## Chronological sensitivities with complete final-five coverage",
        "",
        "| Snapshot | Training cohorts | Flat holdout delta | Dynamic holdout delta | Snapshot dynamic holdout | Broad dynamic holdout |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in holdout_sensitivities:
        lines.append(
            f"| {r['label']} | {r['training_cohort_count']} | "
            f"{r['flat']['delta_snapshot_minus_broad_pp']:+.2f}pp | "
            f"{r['dynamic']['delta_snapshot_minus_broad_pp']:+.2f}pp | "
            f"{r['dynamic']['snapshot_holdout']['mean_cohort_accuracy']:.2f}% | "
            f"{r['dynamic']['broad_holdout']['mean_cohort_accuracy']:.2f}% |"
        )

    lines += [
        "",
        "**Interpretation boundary:** matched full-period results remain in-sample. Holdout rows are stronger evidence but some thresholds have fewer training cohorts; do not promote a sparse threshold from a tiny subset.",
    ]
    (RESDIR / "latest-online-snapshot-matched.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "top_matched_dynamic": sensitivities[:10],
        "holdout_sensitivities": holdout_sensitivities,
    }, indent=2))


if __name__ == "__main__":
    main()
