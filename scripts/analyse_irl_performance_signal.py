#!/usr/bin/env python3
"""Phase 1 audit: construct and assess IRL performance signals relative to Day-1 share.

No next-tournament outcome is used here. This experiment only asks which performance
measures are available, interpretable, and numerically stable enough to carry into a
later chronological forecasting experiment.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

RAW = Path("data/raw/irl-performance/labs")
DAY1 = Path("data/raw/irl/labs/events")
OUT = Path("data/processed/irl-performance")
REPORT = Path("results/irl-performance/README.md")


def q(values, p):
    vals = sorted(v for v in values if v is not None and math.isfinite(v))
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * p
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    f = pos - lo
    return vals[lo] * (1 - f) + vals[hi] * f


def fmt(x, digits=2):
    if x is None:
        return "n/a"
    return f"{x:.{digits}f}"


def share_bin(share_pct):
    if share_pct < 0.5:
        return "<0.5%"
    if share_pct < 1.0:
        return "0.5-1%"
    if share_pct < 2.0:
        return "1-2%"
    if share_pct < 5.0:
        return "2-5%"
    return ">=5%"


def smoothed_log2_ratio(observed, expected, pseudo=0.5):
    return math.log2((observed + pseudo) / (expected + pseudo))


def pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None and math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 3:
        return None
    ax = mean(x for x, _ in pairs)
    ay = mean(y for _, y in pairs)
    num = sum((x - ax) * (y - ay) for x, y in pairs)
    denx = math.sqrt(sum((x - ax) ** 2 for x, _ in pairs))
    deny = math.sqrt(sum((y - ay) ** 2 for _, y in pairs))
    if denx == 0 or deny == 0:
        return None
    return num / (denx * deny)


def event_centered_points(archetypes):
    total_mp = 0.0
    total_max = 0.0
    for row in archetypes.values():
        d1 = row.get("day1_live") or {}
        w, l, t = d1.get("wins"), d1.get("losses"), d1.get("ties")
        if None in (w, l, t):
            continue
        games = w + l + t
        if games:
            total_mp += 3 * w + t
            total_max += 3 * games
    return 100 * total_mp / total_max if total_max else None


def main():
    manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("failures"):
        raise RuntimeError("Collector manifest contains failures; do not analyse partial evidence")

    rows = []
    event_checks = []
    for event_path in sorted((RAW / "events").glob("*.json")):
        event = json.loads(event_path.read_text(encoding="utf-8"))
        archived = json.loads((DAY1 / f"{event['id']}.json").read_text(encoding="utf-8"))
        day1_total = archived["deck_entries_sum"]
        day2_total = event["day2_total_live"]
        event_points_mean = event_centered_points(event["archetypes"])
        top32_complete = event["top32_rows_with_deck"] >= 32
        exact_entry_match = event["day1_total_live"] == day1_total
        event_checks.append({
            "event_id": event["id"],
            "name": event["name"],
            "exact_entry_match": exact_entry_match,
            "archived_entries": day1_total,
            "live_entries": event["day1_total_live"],
            "entry_difference": event["day1_total_live"] - day1_total,
            "day2_total": day2_total,
            "top32_rows_with_deck": event["top32_rows_with_deck"],
            "top32_complete": top32_complete,
            "archived_only_slugs": len(event["archived_only_slugs"]),
            "live_only_slugs": len(event["live_only_slugs"]),
        })

        for slug, a in event["archetypes"].items():
            if slug == "other":
                continue
            d1_arch_n = a.get("day1_entries_archived") or 0
            if d1_arch_n <= 0:
                continue
            p = d1_arch_n / day1_total
            d1_live = a.get("day1_live")
            exact_live_join = d1_live is not None
            d2 = a.get("day2_live")
            d2_n = (d2 or {}).get("entries", 0) if exact_live_join else None
            expected_d2 = day2_total * p if day2_total and exact_live_join else None
            day2_lift = (d2_n / expected_d2) if expected_d2 and expected_d2 > 0 else None
            day2_log = smoothed_log2_ratio(d2_n, expected_d2) if expected_d2 is not None else None
            top8 = a.get("top8") if top32_complete else None
            top16 = a.get("top16") if top32_complete else None
            top32 = a.get("top32") if top32_complete else None
            expected8 = 8 * p
            expected16 = 16 * p
            expected32 = 32 * p
            points_rate = d1_live.get("points_rate_pct") if d1_live else None
            points_centered = (points_rate - event_points_mean) if points_rate is not None and event_points_mean is not None else None
            w = d1_live.get("wins") if d1_live else None
            l = d1_live.get("losses") if d1_live else None
            t = d1_live.get("ties") if d1_live else None
            calc_rate = None
            if None not in (w, l, t) and (w + l + t) > 0:
                calc_rate = 100 * (3 * w + t) / (3 * (w + l + t))
            source_rate_delta = (points_rate - calc_rate) if points_rate is not None and calc_rate is not None else None

            rows.append({
                "event_id": event["id"],
                "event_name": event["name"],
                "event_start_date": event.get("start_date"),
                "slug": slug,
                "name": a.get("name"),
                "day1_entries": d1_arch_n,
                "day1_total": day1_total,
                "day1_share": p,
                "day1_share_pct": 100 * p,
                "share_bin": share_bin(100 * p),
                "exact_live_join": exact_live_join,
                "day1_points_rate_pct": points_rate,
                "event_points_rate_pct": event_points_mean,
                "points_rate_centered_pp": points_centered,
                "source_rate_formula_delta_pp": source_rate_delta,
                "day2_entries": d2_n,
                "day2_total": day2_total if exact_live_join else None,
                "day2_expected": expected_d2,
                "day2_lift": day2_lift,
                "day2_log2_lift_smoothed_05": day2_log,
                "day2_log2_lift_bounded_2": max(-2, min(2, day2_log)) if day2_log is not None else None,
                "top8": top8,
                "top16": top16,
                "top32": top32,
                "top8_lift": (top8 / expected8) if top8 is not None and expected8 > 0 else None,
                "top16_lift": (top16 / expected16) if top16 is not None and expected16 > 0 else None,
                "top32_lift": (top32 / expected32) if top32 is not None and expected32 > 0 else None,
                "top32_log2_lift_smoothed_05": smoothed_log2_ratio(top32, expected32) if top32 is not None else None,
                "winner": a.get("winner") if top32_complete else None,
            })

    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with (OUT / "performance-signals.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # Source reliability and coverage.
    n_events = len(event_checks)
    exact_match_events = sum(x["exact_entry_match"] for x in event_checks)
    top32_events = sum(x["top32_complete"] for x in event_checks)
    no_slug_mismatch_events = sum(x["archived_only_slugs"] == 0 and x["live_only_slugs"] == 0 for x in event_checks)
    max_entry_delta = max(abs(x["entry_difference"]) for x in event_checks) if event_checks else None
    joined_rows = [r for r in rows if r["exact_live_join"]]
    rate_deltas = [abs(r["source_rate_formula_delta_pp"]) for r in joined_rows if r["source_rate_formula_delta_pp"] is not None]

    bins = {}
    ordered_bins = ["<0.5%", "0.5-1%", "1-2%", "2-5%", ">=5%"]
    for b in ordered_bins:
        rr = [r for r in joined_rows if r["share_bin"] == b]
        d2_logs = [r["day2_log2_lift_smoothed_05"] for r in rr if r["day2_log2_lift_smoothed_05"] is not None]
        top32_logs = [r["top32_log2_lift_smoothed_05"] for r in rr if r["top32_log2_lift_smoothed_05"] is not None]
        bins[b] = {
            "rows": len(rr),
            "events": len({r["event_id"] for r in rr}),
            "day2_zero_rate": (sum((r["day2_entries"] or 0) == 0 for r in rr) / len(rr)) if rr else None,
            "top32_zero_rate": (sum((r["top32"] or 0) == 0 for r in rr if r["top32"] is not None) / sum(r["top32"] is not None for r in rr)) if any(r["top32"] is not None for r in rr) else None,
            "day2_abs_log2_median": median(abs(x) for x in d2_logs) if d2_logs else None,
            "day2_abs_log2_p90": q([abs(x) for x in d2_logs], 0.9),
            "day2_abs_log2_max": max([abs(x) for x in d2_logs], default=None),
            "top32_abs_log2_median": median(abs(x) for x in top32_logs) if top32_logs else None,
            "top32_abs_log2_p90": q([abs(x) for x in top32_logs], 0.9),
        }

    thresholds = {}
    for threshold in (0, 0.5, 1.0, 2.0):
        rr = [r for r in joined_rows if r["day1_share_pct"] >= threshold]
        thresholds[str(threshold)] = {
            "rows": len(rr),
            "events": len({r["event_id"] for r in rr}),
            "day2_signal_available": sum(r["day2_log2_lift_smoothed_05"] is not None for r in rr),
            "points_signal_available": sum(r["points_rate_centered_pp"] is not None for r in rr),
            "top32_signal_available": sum(r["top32_log2_lift_smoothed_05"] is not None for r in rr),
        }

    eligible_corr = [r for r in joined_rows if r["day1_share_pct"] >= 1.0]
    correlation = {
        "share_threshold_pct": 1.0,
        "rows": len(eligible_corr),
        "day2_vs_points": pearson(
            [r["day2_log2_lift_smoothed_05"] for r in eligible_corr],
            [r["points_rate_centered_pp"] for r in eligible_corr],
        ),
        "day2_vs_top32": pearson(
            [r["day2_log2_lift_smoothed_05"] for r in eligible_corr],
            [r["top32_log2_lift_smoothed_05"] for r in eligible_corr],
        ),
        "points_vs_top32": pearson(
            [r["points_rate_centered_pp"] for r in eligible_corr],
            [r["top32_log2_lift_smoothed_05"] for r in eligible_corr],
        ),
    }

    summary = {
        "question": "Which prior-IRL popularity-adjusted performance measures are reliably available and stable enough to test as next-IRL predictors?",
        "phase": 1,
        "events": n_events,
        "archetype_event_rows": len(rows),
        "joined_archetype_event_rows": len(joined_rows),
        "source_reliability": {
            "day1_entry_exact_match_events": exact_match_events,
            "day1_entry_exact_match_rate": exact_match_events / n_events if n_events else None,
            "max_absolute_day1_entry_delta": max_entry_delta,
            "top32_complete_events": top32_events,
            "top32_complete_rate": top32_events / n_events if n_events else None,
            "no_exact_slug_mismatch_events": no_slug_mismatch_events,
            "no_exact_slug_mismatch_rate": no_slug_mismatch_events / n_events if n_events else None,
            "source_points_rate_formula_max_abs_delta_pp": max(rate_deltas, default=None),
            "source_points_rate_formula_median_abs_delta_pp": median(rate_deltas) if rate_deltas else None,
        },
        "share_bin_stability": bins,
        "minimum_share_threshold_coverage": thresholds,
        "signal_correlations_at_1pct_plus": correlation,
        "candidate_signals": {
            "primary": {
                "name": "day2_log2_lift_smoothed_05",
                "definition": "log2((observed Day-2 archetype entrants + 0.5) / (expected Day-2 entrants from Day-1 share + 0.5))",
                "raw_interpretation": "0 = represented on Day 2 as expected from Day-1 share; +1 ~= twice expected; -1 ~= half expected after 0.5 smoothing",
                "forecast_variant": "bounded to [-2,+2] before modelling; minimum-share sensitivity retained rather than silently dropping small decks",
            },
            "secondary": [
                {
                    "name": "points_rate_centered_pp",
                    "definition": "source Day-1 displayed points-rate minus event-wide match-side weighted points-rate",
                    "reason": "uses all Day-1 match evidence and is not mechanically driven by deck popularity",
                },
                {
                    "name": "top32_log2_lift_smoothed_05",
                    "definition": "log2((Top-32 count + 0.5)/(32 * Day-1 share + 0.5))",
                    "reason": "high-finish performance; noisier than Day-2 conversion but closer to visible placements",
                },
                {
                    "name": "winner",
                    "definition": "1 if archetype won the tournament, otherwise 0",
                    "reason": "separate visibility/hype signal; never used as the main performance measure",
                },
            ],
        },
        "notes": [
            "This phase does not inspect next-IRL outcomes and therefore cannot establish predictive value.",
            "The 0.5 correction is a transparent finite-count stabilizer; threshold and transform sensitivity must be tested in Phase 2.",
            "Top-8/16/32 are relative-to-Day-1 representation, never raw counts as the primary signal.",
            "All field-share denominators come from the previously archived Day-1 event data.",
        ],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with (OUT / "event-audit.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(event_checks[0].keys()))
        writer.writeheader()
        writer.writerows(event_checks)

    lines = [
        "# IRL performance signal — Phase 1 evidence audit",
        "",
        "## Research question",
        "",
        "Which prior-IRL popularity-adjusted performance measures are reliably available and numerically stable enough to test as predictors of the next same-format IRL field? This phase deliberately does **not** use the next tournament outcome.",
        "",
        "## Evidence and source coverage",
        "",
        f"- Events audited: **{n_events}**.",
        f"- Archetype-event rows from the archived Day-1 slug universe: **{len(rows)}**; exact live-source joins: **{len(joined_rows)}**.",
        f"- Day-1 live entry totals exactly match the archived totals for **{exact_match_events}/{n_events}** events; maximum absolute difference: **{max_entry_delta}** entries.",
        f"- Complete deck identity for ranks 1-32 was recovered for **{top32_events}/{n_events}** events.",
        f"- Events with no exact-slug mismatch between archived and current Day-1 source: **{no_slug_mismatch_events}/{n_events}**.",
        f"- The source's displayed Day-1 `Win %` is reproducible from records as match-points earned / maximum match points: median absolute formula difference **{fmt(median(rate_deltas) if rate_deltas else None, 3)}pp**, max **{fmt(max(rate_deltas, default=None), 3)}pp**. It is labelled `points_rate` here to avoid overstating it as literal win percentage.",
        "",
        "## Candidate performance measures",
        "",
        "**Primary candidate for Phase 2:** Day-2 representation lift relative to Day-1 share, transformed as `log2((observed + 0.5)/(expected + 0.5))`. Zero means the archetype reached Day 2 at its expected rate; approximately +1/-1 means ~2x/~0.5x expected once counts are large enough. A bounded [-2,+2] version is also emitted for modelling.",
        "",
        "Secondary candidates are event-centred Day-1 points rate, Top-32 representation lift using the same 0.5 correction, and a separate tournament-winner indicator as a possible visibility/hype effect. Raw Top-8 counts are not used as the primary signal.",
        "",
        "## Small-archetype stability",
        "",
        "| Day-1 share | Rows | Day-2 zero | Top-32 zero | Median |log2 Day-2 lift| | P90 |log2 Day-2 lift| |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for b in ordered_bins:
        x = bins[b]
        lines.append(
            f"| {b} | {x['rows']} | {fmt(100*x['day2_zero_rate'] if x['day2_zero_rate'] is not None else None,1)}% | "
            f"{fmt(100*x['top32_zero_rate'] if x['top32_zero_rate'] is not None else None,1)}% | "
            f"{fmt(x['day2_abs_log2_median'],2)} | {fmt(x['day2_abs_log2_p90'],2)} |"
        )
    lines += [
        "",
        "This table is diagnostic rather than a filtering rule. Very small archetypes are expected to produce more zero/high-ratio outcomes; Phase 2 must therefore compare minimum-share thresholds and the bounded/smoothed transform chronologically rather than silently excluding them.",
        "",
        "## Signal agreement (Day-1 share >=1%)",
        "",
        f"Across **{correlation['rows']}** archetype-event rows at >=1% Day-1 share, Pearson correlations are: Day-2 lift vs centred points rate **{fmt(correlation['day2_vs_points'],3)}**; Day-2 lift vs Top-32 lift **{fmt(correlation['day2_vs_top32'],3)}**; centred points rate vs Top-32 lift **{fmt(correlation['points_vs_top32'],3)}**.",
        "",
        "These correlations test whether the candidate measures broadly describe the same tournament performance, not whether any predicts future adoption.",
        "",
        "## Phase-1 conclusion",
        "",
        "**Verified:** the source supports Day-1 representation, Day-1 aggregate records/points rate, Day-2 representation, high-finish representation and tournament winner at archetype level. The exact coverage diagnostics above determine which can be used consistently.",
        "",
        "**Inferred:** Day-2 relative representation is the most direct primary behavioural signal because it asks whether an archetype survived into Day 2 more or less often than its Day-1 popularity would imply, while using materially more observations than Top 8/Top 16. Day-1 points rate is the strongest complementary continuous signal; Top-32 and winner are useful visibility sensitivities.",
        "",
        "**Limitation:** all performance pages are fetched retrospectively from current public Labs pages. Exact-slug mismatch diagnostics are retained because source taxonomy may have changed after the historical event. This phase does not claim the performance labels were frozen on the event date.",
        "",
        "## Next bounded experiment",
        "",
        "Phase 2 should join these prior-event signals to the existing adjacent same-format IRL cohort pairs, field-entry weight simultaneous majors into cohorts, and test whether performance predicts `next IRL share - previous IRL share` after controlling for previous share. Compare persistence vs persistence+performance with fixed chronological holdout and expanding walk-forward; include 0.5%/1%/2% share and bounded-transform sensitivities.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
