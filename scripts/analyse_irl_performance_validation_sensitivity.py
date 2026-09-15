#!/usr/bin/env python3
"""Leverage/consistency sensitivity for Phase-2 primary chronological validation."""
from __future__ import annotations

import csv
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "irl-performance-to-next-irl" / "primary-validation.csv"
OUT = ROOT / "data" / "processed" / "irl-performance-to-next-irl" / "validation-sensitivity.json"
REPORT = ROOT / "results" / "irl-performance-to-next-irl" / "VALIDATION_SENSITIVITY.md"
RNG_SEED = 20260915
BOOTSTRAPS = 5000


def mean(xs):
    return statistics.fmean(xs) if xs else None


def median(xs):
    return statistics.median(xs) if xs else None


def percentile(xs, p):
    vals = sorted(xs)
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(vals) - 1)
    f = pos - lo
    return vals[lo] * (1 - f) + vals[hi] * f


def cluster_bootstrap(rows):
    by_format = defaultdict(list)
    for r in rows:
        by_format[r["format"]].append(r)
    formats = sorted(by_format)
    rng = random.Random(RNG_SEED)
    vals = []
    for _ in range(BOOTSTRAPS):
        chosen = [rng.choice(formats) for _ in formats]
        sample = []
        for fmt in chosen:
            sample.extend(by_format[fmt])
        vals.append(mean(r["improvement_pp"] for r in sample))
    return {
        "format_count": len(formats),
        "iterations": BOOTSTRAPS,
        "median_mean_improvement_pp": median(vals),
        "ci95_mean_improvement_pp": [percentile(vals, 0.025), percentile(vals, 0.975)],
    }


def summarise(rows):
    improvements = [r["improvement_pp"] for r in rows]
    best = max(rows, key=lambda r: r["improvement_pp"])
    worst = min(rows, key=lambda r: r["improvement_pp"])
    loo = []
    for i in range(len(rows)):
        other = rows[:i] + rows[i + 1:]
        loo.append(mean(r["improvement_pp"] for r in other))
    by_format = {}
    for fmt in sorted({r["format"] for r in rows}):
        rr = [r for r in rows if r["format"] == fmt]
        by_format[fmt] = {
            "pair_count": len(rr),
            "mean_improvement_pp": mean(r["improvement_pp"] for r in rr),
            "median_improvement_pp": median(r["improvement_pp"] for r in rr),
            "wins": sum(r["improvement_pp"] > 0 for r in rr),
            "losses": sum(r["improvement_pp"] < 0 for r in rr),
        }
    return {
        "pair_count": len(rows),
        "mean_improvement_pp": mean(improvements),
        "median_improvement_pp": median(improvements),
        "wins": sum(x > 0 for x in improvements),
        "losses": sum(x < 0 for x in improvements),
        "best_target": best,
        "worst_target": worst,
        "mean_without_best_target_pp": mean(r["improvement_pp"] for r in rows if r is not best),
        "mean_without_worst_target_pp": mean(r["improvement_pp"] for r in rows if r is not worst),
        "leave_one_target_out_mean_range_pp": [min(loo), max(loo)],
        "by_format": by_format,
        "format_cluster_bootstrap": cluster_bootstrap(rows),
    }


def fmt(x, digits=3):
    return "n/a" if x is None else f"{x:.{digits}f}"


def main():
    with INPUT.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ["accuracy", "persistence_accuracy", "improvement_pp"]:
            r[k] = float(r[k])

    out = {}
    for validation in ["fixed_holdout", "walk_forward"]:
        rr = [r for r in rows if r["validation"] == validation]
        out[validation] = summarise(rr)
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Phase 2 primary validation — leverage and consistency sensitivity",
        "",
        "This sensitivity does not refit or choose a model. It examines the already-declared primary Day-2 performance forecast to determine whether its average chronological gain is broadly distributed or driven by a small number of targets.",
        "",
    ]
    for key, title in [("fixed_holdout", "Fixed chronological holdout"), ("walk_forward", "Expanding walk-forward")]:
        s = out[key]
        ci = s["format_cluster_bootstrap"]["ci95_mean_improvement_pp"]
        lines += [
            f"## {title}",
            "",
            f"- Mean improvement: **{fmt(s['mean_improvement_pp'])}pp**; median target improvement: **{fmt(s['median_improvement_pp'])}pp**.",
            f"- Positive targets: **{s['wins']}/{s['pair_count']}**; negative targets: **{s['losses']}/{s['pair_count']}**.",
            f"- Best target: **{s['best_target']['pair_id']}** ({fmt(s['best_target']['improvement_pp'])}pp); worst: **{s['worst_target']['pair_id']}** ({fmt(s['worst_target']['improvement_pp'])}pp).",
            f"- Mean after removing the best target: **{fmt(s['mean_without_best_target_pp'])}pp**; after removing the worst: **{fmt(s['mean_without_worst_target_pp'])}pp**.",
            f"- Leave-one-target-out mean range: **[{fmt(s['leave_one_target_out_mean_range_pp'][0])}, {fmt(s['leave_one_target_out_mean_range_pp'][1])}]pp**.",
            f"- Format-cluster bootstrap 95% interval for mean improvement: **[{fmt(ci[0])}, {fmt(ci[1])}]pp** across **{s['format_cluster_bootstrap']['format_count']}** observed formats.",
            "",
            "Per-format mean improvements:",
            "",
            "| Format | Targets | Mean improvement | Wins / losses |",
            "|---|---:|---:|---:|",
        ]
        for fmt_name, x in s["by_format"].items():
            lines.append(f"| {fmt_name} | {x['pair_count']} | {fmt(x['mean_improvement_pp'])}pp | {x['wins']} / {x['losses']} |")
        lines.append("")

    fixed = out["fixed_holdout"]
    walk = out["walk_forward"]
    lines += [
        "## Interpretation",
        "",
        "**Verified:** the fixed-holdout mean is sensitive to its strongest target if `mean_without_best_target_pp` changes sign. The expanding walk-forward result is more convincing only if its gain remains positive without the best target and is not confined to one format.",
        "",
        "**Limitation:** the format-cluster intervals are based on only a handful of formats in each validation window; crossing zero should be treated as unresolved uncertainty rather than proof of no effect.",
        "",
        "This sensitivity is diagnostic. It does not promote a sensitivity model over the predeclared primary specification.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
