#!/usr/bin/env python3
"""Leverage/time-window sensitivities for IRL-to-IRL gap regression."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import analyse_irl_to_irl_regression as base

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "data" / "processed" / "irl-regression"
RESDIR = ROOT / "results" / "irl-regression"


def fit_subset(label, rows, bootstrap=False):
    xs = [p["gap_days"] for p in rows]
    ys = [p["persistence_accuracy"] for p in rows]
    overall = base.simple_regression(xs, ys) if len(rows) >= 2 else None
    within = base.within_format_slope(rows) if len(rows) >= 2 else None
    return {
        "label": label,
        "pair_count": len(rows),
        "format_count": len({p["format"] for p in rows}),
        "gap_min": min(xs) if xs else None,
        "gap_max": max(xs) if xs else None,
        "mean_accuracy": base.mean(ys),
        "overall": overall,
        "within_format": within,
        "overall_cluster_bootstrap": base.cluster_bootstrap_slope(rows, False) if bootstrap and len(rows) >= 3 else None,
        "within_format_cluster_bootstrap": base.cluster_bootstrap_slope(rows, True) if bootstrap and len(rows) >= 3 else None,
    }


def main():
    cohorts, _ = base.build_cohorts()
    pairs = base.build_pairs(cohorts)
    latest = max(date.fromisoformat(p["target_start_date"]) for p in pairs)
    recent_start = latest - timedelta(days=365)
    max_gap = max(p["gap_days"] for p in pairs)

    subsets = [
        fit_subset("Full eligible sample", pairs, False),
        fit_subset("Exclude single longest-gap pair", [p for p in pairs if p["gap_days"] < max_gap], True),
        fit_subset("Gaps <=14 days", [p for p in pairs if p["gap_days"] <= 14], True),
        fit_subset("Latest 365 days", [p for p in pairs if date.fromisoformat(p["target_start_date"]) >= recent_start], True),
        fit_subset("Latest 365 days, gaps <=14", [p for p in pairs if date.fromisoformat(p["target_start_date"]) >= recent_start and p["gap_days"] <= 14], True),
    ]
    out = {
        "purpose": "Test whether the negative IRL-to-IRL gap slope is robust to sparse long-gap leverage and to the recent-year era.",
        "latest_target_date": latest.isoformat(),
        "recent_365_start": recent_start.isoformat(),
        "subsets": subsets,
        "interpretation_boundary": "Sensitivity analyses are descriptive. Small subsets and few independent formats make slope estimates imprecise.",
    }
    OUTDIR.mkdir(parents=True, exist_ok=True)
    RESDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "sensitivity.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    lines = [
        "# IRL-to-IRL regression — leverage sensitivity",
        "",
        "The main sample has only three pairs with gaps above 14 days. These checks test whether the negative time-gap slope survives removing sparse long-gap leverage.",
        "",
        "| Sensitivity | Pairs | Gap range | Overall slope/day | Within-format slope/day |",
        "|---|---:|---:|---:|---:|",
    ]
    for s in subsets:
        o = s["overall"]["slope"] if s["overall"] else None
        w = s["within_format"]["slope"] if s["within_format"] else None
        lines.append(
            f"| {s['label']} | {s['pair_count']} | {s['gap_min']}-{s['gap_max']} | "
            f"{o:+.3f} | {w:+.3f} |"
        )
    lines += ["", "## Bootstrap details", ""]
    for s in subsets:
        if s.get("overall_cluster_bootstrap"):
            ci = s["overall_cluster_bootstrap"]["ci95"]
            wci = s["within_format_cluster_bootstrap"]["ci95"] if s.get("within_format_cluster_bootstrap") else [None, None]
            lines.append(
                f"- **{s['label']}**: overall 95% format-cluster CI [{ci[0]:+.3f}, {ci[1]:+.3f}] pp/day; "
                f"within-format CI [{wci[0]:+.3f}, {wci[1]:+.3f}] pp/day."
            )
    lines += [
        "",
        "A slope that changes materially after excluding the longest gaps should be treated as leverage-sensitive rather than a stable decay law.",
    ]
    (RESDIR / "SENSITIVITY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
