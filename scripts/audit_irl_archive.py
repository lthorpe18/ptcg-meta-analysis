#!/usr/bin/env python3
"""Audit historical IRL major Day-1 fields collected from Limitless Labs."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

ROOT = Path("data/raw/irl/labs")
OUT = Path("results/irl-audit")
EXPECTED_TYPES = {
    "Regional Championship",
    "Special Event",
    "International Championship",
    "World Championship",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def pct(values, p):
    if not values:
        return None
    v = sorted(values)
    if len(v) == 1:
        return v[0]
    k = (len(v) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return v[lo]
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def mean(values):
    return sum(values) / len(values) if values else None


def fmt_pct(x):
    return "—" if x is None else f"{100*x:.2f}%"


def concentration(event):
    decks = [d for d in event.get("decks", []) if str(d.get("name", "")).lower() != "other"]
    total = event.get("deck_entries_sum") or sum(int(d.get("entries") or 0) for d in event.get("decks", []))
    if not total:
        return {"named_variants": len(decks), "variants_ge_1pct": 0, "top5_share": None, "top10_share": None, "hhi": None}
    shares = sorted((int(d.get("entries") or 0) / total for d in decks), reverse=True)
    return {
        "named_variants": len(decks),
        "variants_ge_1pct": sum(s >= 0.01 for s in shares),
        "top5_share": sum(shares[:5]),
        "top10_share": sum(shares[:10]),
        "hhi": sum(s*s for s in shares),
    }


def summarize(rows):
    ratios = [r["field_count_ratio"] for r in rows]
    classified = [r["classified_share"] for r in rows]
    players = [r["players"] for r in rows]
    return {
        "events": len(rows),
        "players": sum(players),
        "median_players": median(players) if players else None,
        "field_count_ratio_mean": mean(ratios),
        "field_count_ratio_median": median(ratios) if ratios else None,
        "field_count_ratio_min": min(ratios) if ratios else None,
        "classified_share_mean": mean(classified),
        "classified_share_median": median(classified) if classified else None,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = load(ROOT / "manifest.json")
    index = load(ROOT / "index.json")
    event_files = sorted((ROOT / "events").glob("*.json"))
    events = [load(p) for p in event_files]

    ids = [e.get("id") for e in events]
    duplicate_ids = [k for k, v in Counter(ids).items() if v > 1]
    rows = []
    anomalies = Counter()

    for e in events:
        players = int(e.get("players") or 0)
        total = int(e.get("deck_entries_sum") or 0)
        other = int(e.get("other_entries") or 0)
        classified = int(e.get("classified_entries") or 0)
        ratio = (total / players) if players else 0
        classified_share = (classified / players) if players else 0
        c = concentration(e)
        row = {
            "id": e.get("id"),
            "name": e.get("name"),
            "start_date": e.get("start_date"),
            "end_date": e.get("end_date"),
            "event_type": e.get("event_type"),
            "division": e.get("division"),
            "players": players,
            "deck_entries_sum": total,
            "other_entries": other,
            "classified_entries": classified,
            "field_count_ratio": ratio,
            "classified_share": classified_share,
            **c,
        }
        rows.append(row)

        if e.get("division") != "Masters": anomalies["non_masters"] += 1
        if e.get("event_type") not in EXPECTED_TYPES: anomalies["unexpected_event_type"] += 1
        if e.get("variant_grouping") is not False: anomalies["variant_grouping_not_false"] += 1
        if e.get("view") != "day1": anomalies["not_day1_view"] += 1
        if total > players: anomalies["deck_entries_exceed_players"] += 1
        if classified + other != total: anomalies["classified_plus_other_mismatch"] += 1
        if not e.get("complete"): anomalies["event_not_complete"] += 1

    ratios = [r["field_count_ratio"] for r in rows]
    classified_shares = [r["classified_share"] for r in rows]

    thresholds = {}
    for t in (0.90, 0.95, 0.98, 0.99, 0.995, 1.0):
        thresholds[f"ge_{t:.3f}"] = sum(r >= t for r in ratios)

    by_type = {}
    for typ in sorted(EXPECTED_TYPES):
        group = [r for r in rows if r["event_type"] == typ]
        by_type[typ] = summarize(group)
        if group:
            by_type[typ]["median_named_variants"] = median(r["named_variants"] for r in group)
            by_type[typ]["median_variants_ge_1pct"] = median(r["variants_ge_1pct"] for r in group)
            by_type[typ]["median_top5_share"] = median(r["top5_share"] for r in group)
            by_type[typ]["median_top10_share"] = median(r["top10_share"] for r in group)
            by_type[typ]["median_hhi"] = median(r["hhi"] for r in group)

    # Same-start-date groups are the strongest simple proxy for correlated same-weekend majors.
    by_date = defaultdict(list)
    for r in rows:
        by_date[r["start_date"]].append(r)
    same_date_groups = [
        {
            "start_date": d,
            "events": [{"id": r["id"], "name": r["name"], "event_type": r["event_type"]} for r in grp],
        }
        for d, grp in sorted(by_date.items()) if len(grp) > 1
    ]

    dated = sorted(rows, key=lambda r: r["start_date"])
    gaps = []
    for a, b in zip(dated, dated[1:]):
        da = datetime.fromisoformat(a["start_date"])
        db = datetime.fromisoformat(b["start_date"])
        gaps.append(((db-da).days, a, b))
    max_gap = max(gaps, key=lambda x: x[0]) if gaps else None

    low = sorted(rows, key=lambda r: r["field_count_ratio"])[:15]
    worlds = [r for r in rows if r["event_type"] == "World Championship"]
    non_worlds = [r for r in rows if r["event_type"] != "World Championship"]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest_complete": bool(manifest.get("complete")),
        "source_failures": manifest.get("failures", []),
        "events": len(rows),
        "unique_event_ids": len(set(ids)),
        "duplicate_event_ids": duplicate_ids,
        "period": {
            "start": min((r["start_date"] for r in rows), default=None),
            "end": max((r["end_date"] for r in rows), default=None),
        },
        "total_players_reported": sum(r["players"] for r in rows),
        "total_deck_entries": sum(r["deck_entries_sum"] for r in rows),
        "total_other_entries": sum(r["other_entries"] for r in rows),
        "field_count_ratio": {
            "mean": mean(ratios),
            "min": min(ratios),
            "p10": pct(ratios, .10),
            "p25": pct(ratios, .25),
            "median": median(ratios),
            "p75": pct(ratios, .75),
            "p90": pct(ratios, .90),
            "max": max(ratios),
            "threshold_counts": thresholds,
        },
        "classified_share": {
            "mean": mean(classified_shares),
            "min": min(classified_shares),
            "p10": pct(classified_shares, .10),
            "median": median(classified_shares),
            "max": max(classified_shares),
        },
        "by_event_type": by_type,
        "worlds_descriptive": {
            "note": "Only two Worlds are present, so this is descriptive rather than inferential.",
            "worlds": worlds,
            "worlds_summary": summarize(worlds),
            "non_worlds_summary": summarize(non_worlds),
            "worlds_median_top5_share": median(r["top5_share"] for r in worlds) if worlds else None,
            "non_worlds_median_top5_share": median(r["top5_share"] for r in non_worlds) if non_worlds else None,
            "worlds_median_variants_ge_1pct": median(r["variants_ge_1pct"] for r in worlds) if worlds else None,
            "non_worlds_median_variants_ge_1pct": median(r["variants_ge_1pct"] for r in non_worlds) if non_worlds else None,
        },
        "same_start_date_groups": same_date_groups,
        "timeline": {
            "largest_start_date_gap_days": max_gap[0] if max_gap else None,
            "before": {"date": max_gap[1]["start_date"], "name": max_gap[1]["name"]} if max_gap else None,
            "after": {"date": max_gap[2]["start_date"], "name": max_gap[2]["name"]} if max_gap else None,
        },
        "anomalies": dict(anomalies),
        "lowest_field_completeness": low,
        "source_index_rows": len(index),
        "caveat": "Completeness is verified against the Limitless Labs index captured by the collector, not yet against an independent official Pokemon event calendar.",
    }

    (OUT / "audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md = [
        "# Historical IRL archive audit",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Headline",
        "",
        f"- Period: **{report['period']['start']} to {report['period']['end']}**",
        f"- IRL majors: **{len(rows)}**; unique IDs: **{len(set(ids))}**; source failures: **{len(report['source_failures'])}**",
        f"- Reported Masters players: **{report['total_players_reported']:,}**",
        f"- Day-1 deck-field entries captured: **{report['total_deck_entries']:,} ({100*report['total_deck_entries']/report['total_players_reported']:.2f}% overall)**",
        f"- `Other` entries retained: **{report['total_other_entries']:,}**",
        "",
        "## Field completeness by event",
        "",
        f"- Median: **{fmt_pct(report['field_count_ratio']['median'])}**",
        f"- 10th percentile: **{fmt_pct(report['field_count_ratio']['p10'])}**",
        f"- Minimum: **{fmt_pct(report['field_count_ratio']['min'])}**",
        f"- Events >=99% complete: **{thresholds['ge_0.990']}/{len(rows)}**",
        f"- Events >=98% complete: **{thresholds['ge_0.980']}/{len(rows)}**",
        f"- Events >=95% complete: **{thresholds['ge_0.950']}/{len(rows)}**",
        "",
        "## Integrity",
        "",
        f"- Duplicate IDs: **{len(duplicate_ids)}**",
        f"- Non-Masters events: **{anomalies['non_masters']}**",
        f"- Non-Day-1 views: **{anomalies['not_day1_view']}**",
        f"- Variant grouping unexpectedly enabled: **{anomalies['variant_grouping_not_false']}**",
        f"- Field rows exceeding reported players: **{anomalies['deck_entries_exceed_players']}**",
        "",
        "## By event type",
        "",
        "| Type | Events | Players | Median field completeness | Min | Median top-5 share | Median variants >=1% |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for typ, s in by_type.items():
        md.append(f"| {typ} | {s['events']} | {s['players']:,} | {fmt_pct(s['field_count_ratio_median'])} | {fmt_pct(s['field_count_ratio_min'])} | {fmt_pct(s.get('median_top5_share'))} | {s.get('median_variants_ge_1pct')} |")

    md += [
        "",
        "## Worlds — descriptive only",
        "",
        "There are only **2 Worlds**, so do not infer a stable Worlds-specific rule from this sample yet.",
        f"- Worlds median top-5 share: **{fmt_pct(report['worlds_descriptive']['worlds_median_top5_share'])}** vs **{fmt_pct(report['worlds_descriptive']['non_worlds_median_top5_share'])}** for non-Worlds.",
        f"- Worlds median number of variants >=1%: **{report['worlds_descriptive']['worlds_median_variants_ge_1pct']}** vs **{report['worlds_descriptive']['non_worlds_median_variants_ge_1pct']}** for non-Worlds.",
        "",
        "## Lowest field completeness",
        "",
        "| Date | Event | Type | Players | Captured | Completeness |",
        "|---|---|---|---:|---:|---:|",
    ]
    for r in low[:10]:
        md.append(f"| {r['start_date']} | {r['name']} | {r['event_type']} | {r['players']} | {r['deck_entries_sum']} | {fmt_pct(r['field_count_ratio'])} |")

    md += [
        "",
        "## Interpretation",
        "",
        "For prediction-target scoring, field completeness matters more than the share assigned to a named archetype, because `Other` is still a legitimate field bucket. A sensible first candidate is to require >=95% captured field, then test >=98% as a sensitivity check rather than choosing a threshold to improve model scores.",
        "",
        "Same-date majors are retained but must be treated as one correlated prediction cohort during walk-forward evaluation.",
        "",
        report['caveat'],
    ]
    (OUT / "README.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({
        "events": len(rows),
        "players": report["total_players_reported"],
        "deck_entries": report["total_deck_entries"],
        "median_completeness": report["field_count_ratio"]["median"],
        "events_ge_99": thresholds["ge_0.990"],
        "events_ge_98": thresholds["ge_0.980"],
        "events_ge_95": thresholds["ge_0.950"],
        "same_date_groups": len(same_date_groups),
        "anomalies": dict(anomalies),
    }, indent=2))


if __name__ == "__main__":
    main()
