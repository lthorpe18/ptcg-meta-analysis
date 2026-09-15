#!/usr/bin/env python3
"""Recent-era sensitivity for Phase 2 IRL performance forecasting.

The recent subset is descriptive, but chronological recent-target scores fit each
target only from all earlier historical pairs. No recent-only parameter tuning is
used for the headline sensitivity.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import analyse_irl_performance_to_next_share as phase2

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/irl-performance/phase2-recent-sensitivity.json"
REPORT = ROOT / "results/irl-performance/PHASE2_RECENT.md"


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def fmt(x, n=3):
    return "n/a" if x is None else f"{x:.{n}f}"


def chronological_recent(pairs, variant, cutoff):
    perf_scores = []
    persistence = []
    betas = []
    targets = []
    for i, target in enumerate(pairs):
        if date.fromisoformat(target["target_date"]) < cutoff or i < phase2.MIN_WALKFORWARD_TRAIN:
            continue
        train = pairs[:i]
        beta = phase2.fit_beta(train, variant)
        betas.append(beta)
        perf_scores.append(phase2.field_accuracy(phase2.predict(target, variant, beta), target["target"]))
        persistence.append(target["persistence_accuracy"])
        targets.append(target["target_date"])
    return {
        "test_pairs": len(targets),
        "first_target": min(targets) if targets else None,
        "last_target": max(targets) if targets else None,
        "mean_beta": mean(betas),
        "persistence_accuracy": mean(persistence),
        "performance_accuracy": mean(perf_scores),
        "improvement_pp": mean(perf_scores) - mean(persistence) if perf_scores else None,
    }


def main():
    perf_rows = phase2.load_perf_rows()
    cohorts, _ = phase2.build_cohorts()
    pairs = phase2.build_pairs(cohorts, perf_rows)
    end = max(date.fromisoformat(p["target_date"]) for p in pairs)
    cutoff = end - timedelta(days=365)
    recent = [p for p in pairs if date.fromisoformat(p["target_date"]) >= cutoff]

    variants = {}
    for v in phase2.VARIANTS:
        beta_recent = phase2.fit_beta(recent, v)
        variants[v] = {
            "recent_in_sample": phase2.evaluate(recent, v, beta_recent),
            "recent_targets_chronological": chronological_recent(pairs, v, cutoff),
        }

    primary = variants[phase2.PRIMARY]
    summary = {
        "definition": "latest 365 days ending at the final eligible target date",
        "cutoff": cutoff.isoformat(),
        "end": end.isoformat(),
        "recent_pair_count": len(recent),
        "recent_format_count": len({p["format"] for p in recent}),
        "primary_variant": phase2.PRIMARY,
        "variants": variants,
        "guardrail": "Recent in-sample fits are descriptive. The chronological recent-target comparison fits each target using all earlier historical pairs only.",
    }
    OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# IRL performance → next IRL share — recent-era sensitivity",
        "",
        f"Recent window: **{cutoff.isoformat()} to {end.isoformat()}**, containing **{len(recent)} adjacent pairs across {len({p['format'] for p in recent})} formats**.",
        "",
        "The headline recent comparison is chronological: for each recent target, the performance coefficient is fitted using all eligible pairs strictly earlier than that target.",
        "",
        "## Primary bounded Day-2 signal",
        "",
        f"- Recent descriptive in-sample: persistence **{fmt(primary['recent_in_sample']['persistence_accuracy'],2)}%** vs performance-adjusted **{fmt(primary['recent_in_sample']['performance_accuracy'],2)}%** ({fmt(primary['recent_in_sample']['improvement_pp'])}pp).",
        f"- Recent chronological targets: persistence **{fmt(primary['recent_targets_chronological']['persistence_accuracy'],2)}%** vs performance-adjusted **{fmt(primary['recent_targets_chronological']['performance_accuracy'],2)}%** ({fmt(primary['recent_targets_chronological']['improvement_pp'])}pp), **{primary['recent_targets_chronological']['test_pairs']} targets**.",
        "",
        "## Variant chronological sensitivity",
        "",
        "| Variant | Recent chronological Δ vs persistence |",
        "|---|---:|",
    ]
    for v in phase2.VARIANTS:
        lines.append(f"| {v} | {fmt(variants[v]['recent_targets_chronological']['improvement_pp'])}pp |")
    lines += [
        "",
        "**Interpretation:** this sensitivity asks whether the historical performance adjustment continues to help on recent targets. It does not establish that recent-era coefficients should be fitted separately or that older data should be discarded.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
