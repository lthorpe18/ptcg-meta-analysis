from __future__ import annotations

import csv
import json
import math
import random
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
EVENTS_PATH = ROOT / "data" / "processed" / "model-results" / "events.csv"
OUT_DIR = ROOT / "results" / "accuracy-over-time"

# Verified by results/irl-audit/README.md: these are the three targets below
# the >=95% IRL field-capture threshold used for primary scoring.
PRIMARY_EXCLUDED_TARGET_IDS = {"0004", "0008", "0051"}

PERMUTATIONS = 20_000
SEED = 20260915

SERIES = [
    ("online_all_primary", "Online-only — all primary windows", "online_only_accuracy_pct", None),
    ("online_settled_primary", "Online-only — settled primary windows", "online_only_accuracy_pct", "settled"),
    ("online_transition_primary", "Online-only — transition primary windows", "online_only_accuracy_pct", "transition"),
    ("irl_settled_primary", "IRL-only — settled primary windows", "irl_only_accuracy_pct", "settled"),
    ("fifty_fifty_complete_case", "50/50 — complete-case settled windows", "fifty_fifty_accuracy_pct", "settled"),
    ("current_v2_1_complete_case", "Current v2.1 — complete-case settled windows", "current_v2_1_accuracy_pct", "settled"),
]


def parse_float(value: str) -> float | None:
    return None if value == "" else float(value)


def load_rows() -> list[dict]:
    rows = []
    with EVENTS_PATH.open(newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            if raw["target_id"] in PRIMARY_EXCLUDED_TARGET_IDS:
                continue
            row = dict(raw)
            row["date"] = date.fromisoformat(raw["target_start_date"])
            for field in (
                "online_only_accuracy_pct",
                "irl_only_accuracy_pct",
                "fifty_fifty_accuracy_pct",
                "current_v2_1_accuracy_pct",
            ):
                row[field] = parse_float(raw[field])
            rows.append(row)
    return rows


def cohort_means(rows: list[dict], metric: str, window_class: str | None) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if window_class and row["window_class"] != window_class:
            continue
        if row[metric] is None:
            continue
        groups[row["cohort_id"]].append(row)

    out = []
    for cohort_id, members in groups.items():
        out.append(
            {
                "cohort_id": cohort_id,
                "date": min(m["date"] for m in members),
                "accuracy": mean(m[metric] for m in members),
                "event_count": len(members),
            }
        )
    return sorted(out, key=lambda x: (x["date"], x["cohort_id"]))


def slope_pp_per_year(points: list[dict], accuracies: list[float] | None = None) -> float:
    xs = [(p["date"] - points[0]["date"]).days / 365.25 for p in points]
    ys = accuracies if accuracies is not None else [p["accuracy"] for p in points]
    xbar = mean(xs)
    ybar = mean(ys)
    denom = sum((x - xbar) ** 2 for x in xs)
    return sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / denom


def pearson_r(points: list[dict]) -> float:
    xs = [(p["date"] - points[0]["date"]).days / 365.25 for p in points]
    ys = [p["accuracy"] for p in points]
    xbar = mean(xs)
    ybar = mean(ys)
    sxx = sum((x - xbar) ** 2 for x in xs)
    syy = sum((y - ybar) ** 2 for y in ys)
    sxy = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sxx * syy)


def permutation_p(points: list[dict], observed: float, rng: random.Random) -> float:
    ys = [p["accuracy"] for p in points]
    extreme = 0
    for _ in range(PERMUTATIONS):
        shuffled = ys[:]
        rng.shuffle(shuffled)
        trial = slope_pp_per_year(points, shuffled)
        if abs(trial) >= abs(observed):
            extreme += 1
    return (extreme + 1) / (PERMUTATIONS + 1)


def half_split(points: list[dict]) -> dict:
    cut = len(points) // 2
    early = points[:cut]
    late = points[cut:]
    early_mean = mean(p["accuracy"] for p in early)
    late_mean = mean(p["accuracy"] for p in late)
    return {
        "early_cohorts": len(early),
        "late_cohorts": len(late),
        "early_mean_accuracy_pct": early_mean,
        "late_mean_accuracy_pct": late_mean,
        "late_minus_early_pp": late_mean - early_mean,
        "note": "Descriptive only; the half split is not the primary inferential test.",
    }


def main() -> None:
    rows = load_rows()
    rng = random.Random(SEED)
    summary = {
        "question": "Does prediction Field Accuracy change systematically over chronological time?",
        "evidence_window": {
            "start": min(r["date"] for r in rows).isoformat(),
            "end": max(r["date"] for r in rows).isoformat(),
            "primary_irl_capture_threshold": ">=95%",
            "excluded_target_ids": sorted(PRIMARY_EXCLUDED_TARGET_IDS),
        },
        "analysis_unit": "Mean Field Accuracy per correlated tournament cohort.",
        "metric": "Field Accuracy = 100% - 0.5 * sum(abs(predicted share - actual share)).",
        "trend_test": {
            "primary": "Linear slope in percentage points of Field Accuracy per calendar year.",
            "significance": f"Two-sided permutation test with {PERMUTATIONS:,} shuffles; seed {SEED}.",
            "reason": "Cohort aggregation prevents multi-major weekends receiving extra weight.",
        },
        "series": {},
    }

    cohort_rows = []
    for key, label, metric, window_class in SERIES:
        points = cohort_means(rows, metric, window_class)
        slope = slope_pp_per_year(points)
        entry = {
            "label": label,
            "event_count": sum(p["event_count"] for p in points),
            "cohort_count": len(points),
            "start": points[0]["date"].isoformat(),
            "end": points[-1]["date"].isoformat(),
            "mean_accuracy_pct": mean(p["accuracy"] for p in points),
            "slope_pp_per_year": slope,
            "pearson_r": pearson_r(points),
            "permutation_p_two_sided": permutation_p(points, slope, rng),
            "half_split": half_split(points),
        }
        summary["series"][key] = entry
        for point in points:
            cohort_rows.append(
                {
                    "series": key,
                    "cohort_id": point["cohort_id"],
                    "date": point["date"].isoformat(),
                    "event_count": point["event_count"],
                    "cohort_mean_accuracy_pct": point["accuracy"],
                }
            )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with (OUT_DIR / "cohort-accuracy.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["series", "cohort_id", "date", "event_count", "cohort_mean_accuracy_pct"],
        )
        writer.writeheader()
        writer.writerows(cohort_rows)

    current = summary["series"]["current_v2_1_complete_case"]
    online_settled = summary["series"]["online_settled_primary"]
    online_all = summary["series"]["online_all_primary"]
    irl = summary["series"]["irl_settled_primary"]
    fifty = summary["series"]["fifty_fifty_complete_case"]
    transition = summary["series"]["online_transition_primary"]

    readme = f"""# Prediction accuracy over time

Generated from `data/processed/model-results/events.csv`.

## Question

Does field-share prediction accuracy change systematically over chronological time?

## Evidence and method

- Historical target window: **{summary['evidence_window']['start']} to {summary['evidence_window']['end']}**.
- Primary targets use the existing **>=95% IRL field-capture** threshold; targets 0004, 0008 and 0051 are excluded consistently with the existing scorer.
- Unit of analysis: **tournament cohort mean**, so correlated same-weekend majors do not receive extra weight.
- Metric: existing **Field Accuracy**.
- Primary trend statistic: linear change in Field Accuracy percentage points per calendar year.
- Two-sided permutation test: **{PERMUTATIONS:,}** shuffled cohort accuracies, deterministic seed `{SEED}`.
- No model is retuned here. This is a diagnostic of existing prediction outputs.

## Results

| Series | Cohorts | Slope (pp/year) | Permutation p | Early half | Late half |
|---|---:|---:|---:|---:|---:|
| Online-only, all primary windows | {online_all['cohort_count']} | {online_all['slope_pp_per_year']:.2f} | {online_all['permutation_p_two_sided']:.3f} | {online_all['half_split']['early_mean_accuracy_pct']:.2f}% | {online_all['half_split']['late_mean_accuracy_pct']:.2f}% |
| Online-only, settled primary windows | {online_settled['cohort_count']} | {online_settled['slope_pp_per_year']:.2f} | {online_settled['permutation_p_two_sided']:.3f} | {online_settled['half_split']['early_mean_accuracy_pct']:.2f}% | {online_settled['half_split']['late_mean_accuracy_pct']:.2f}% |
| Online-only, transition primary windows | {transition['cohort_count']} | {transition['slope_pp_per_year']:.2f} | {transition['permutation_p_two_sided']:.3f} | {transition['half_split']['early_mean_accuracy_pct']:.2f}% | {transition['half_split']['late_mean_accuracy_pct']:.2f}% |
| IRL-only, settled primary windows | {irl['cohort_count']} | {irl['slope_pp_per_year']:.2f} | {irl['permutation_p_two_sided']:.3f} | {irl['half_split']['early_mean_accuracy_pct']:.2f}% | {irl['half_split']['late_mean_accuracy_pct']:.2f}% |
| 50/50, complete-case settled | {fifty['cohort_count']} | {fifty['slope_pp_per_year']:.2f} | {fifty['permutation_p_two_sided']:.3f} | {fifty['half_split']['early_mean_accuracy_pct']:.2f}% | {fifty['half_split']['late_mean_accuracy_pct']:.2f}% |
| Current v2.1, complete-case settled | {current['cohort_count']} | {current['slope_pp_per_year']:.2f} | {current['permutation_p_two_sided']:.3f} | {current['half_split']['early_mean_accuracy_pct']:.2f}% | {current['half_split']['late_mean_accuracy_pct']:.2f}% |

## Interpretation

**Verified from this diagnostic:** the clearest chronological signal is in **Online-only accuracy on settled formats**. Its cohort-level accuracy rises by about **{online_settled['slope_pp_per_year']:.2f} percentage points per year**, with a small permutation p-value ({online_settled['permutation_p_two_sided']:.3f}). The descriptive half split is {online_settled['half_split']['early_mean_accuracy_pct']:.2f}% versus {online_settled['half_split']['late_mean_accuracy_pct']:.2f}%.

The same clear monotonic trend is **not** present in the current blended benchmark: current v2.1 changes by about **{current['slope_pp_per_year']:.2f} pp/year** with permutation p={current['permutation_p_two_sided']:.3f}. IRL-only and 50/50 likewise do not show a clear linear trend.

**Important limitation:** this does not establish that Online evidence itself became intrinsically more predictive. Calendar time is confounded with format/rotation, tournament ecosystem, event mix, field concentration and retrospective data conditions. Transition windows also behave differently from settled windows. The result supports a follow-up question about *why settled Online-only accuracy improved*, not a model change.

## What this supports

- There is evidence worth investigating that **settled-format Online-only field prediction became more accurate over this historical period**.
- There is not yet evidence of a general across-the-board improvement in the blended/IRL prediction methods.
- No production-model change is supported by this analysis alone.

## Next analytical question

Test whether the settled Online-only trend remains after accounting for plausible confounders, starting with **format/rotation era and target-field concentration**. That follow-up requires an explicit owner decision before implementation.
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
