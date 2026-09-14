#!/usr/bin/env python3
"""Audit the completed historical Online archive using only stored snapshots."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

UNKNOWN_DECK_NAMES = {"", "unknown", "unclassified", "other", "none", "null"}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_dt(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def percentile(values, p):
    if not values:
        return None
    vals = sorted(values)
    if len(vals) == 1:
        return vals[0]
    k = (len(vals) - 1) * p
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return vals[lo]
    return vals[lo] + (vals[hi] - vals[lo]) * (k - lo)


def round_or_none(value, digits=4):
    return None if value is None else round(value, digits)


def deck_is_classified(deck):
    if not isinstance(deck, dict):
        return False
    deck_id = str(deck.get("id") or "").strip().lower()
    deck_name = str(deck.get("name") or "").strip().lower()
    return bool(deck_id or deck_name) and deck_id not in UNKNOWN_DECK_NAMES and deck_name not in UNKNOWN_DECK_NAMES


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/raw/online/backfill/chunks")
    ap.add_argument("--out-dir", default="results/online-audit")
    args = ap.parse_args()

    root = Path(args.root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    chunk_rows = []
    event_rows = []
    seen_event_ids = Counter()
    deck_counts = Counter()
    country_counts = Counter()
    organizer_counts = Counter()
    platform_counts = Counter()
    anomaly_counts = Counter()

    discovered_total = 0
    manifest_eligible_total = 0
    manifest_ineligible_total = 0
    manifests_complete = True

    for chunk_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        manifest_path = chunk_dir / "manifest.json"
        if not manifest_path.exists():
            anomaly_counts["chunk_missing_manifest"] += 1
            continue
        manifest = load_json(manifest_path)
        manifests_complete = manifests_complete and bool(manifest.get("complete"))
        discovered_total += int(manifest.get("discovered_index_rows") or 0)
        manifest_eligible_total += int(manifest.get("eligible_first_pass") or 0)
        manifest_ineligible_total += int(manifest.get("ineligible_or_failed") or 0)

        chunk_start = manifest.get("start_date")
        chunk_end = manifest.get("end_date")
        start_dt = parse_dt(chunk_start + "T00:00:00+00:00") if chunk_start else None
        end_dt = parse_dt(chunk_end + "T23:59:59.999999+00:00") if chunk_end else None

        candidates = 0
        usable = 0
        entries = 0
        classified = 0

        for event_dir in sorted(p for p in chunk_dir.iterdir() if p.is_dir()):
            tournament_path = event_dir / "tournament.json"
            if not tournament_path.exists():
                continue
            candidates += 1
            tournament = load_json(tournament_path)
            event_id = str(tournament.get("id") or event_dir.name)
            seen_event_ids[event_id] += 1
            standings_path = event_dir / "standings.json"
            details_path = event_dir / "details.json"
            event_date = parse_dt(tournament.get("date"))
            players_reported = tournament.get("players")

            row = {
                "chunk": chunk_dir.name,
                "event_id": event_id,
                "date": tournament.get("date"),
                "name": tournament.get("name"),
                "reported_players": players_reported,
                "has_details": details_path.exists(),
                "has_standings": standings_path.exists(),
                "standings_players": None,
                "classified_players": None,
                "classification_coverage": None,
                "platform": None,
                "organizer": None,
            }

            if event_date and start_dt and end_dt and not (start_dt <= event_date <= end_dt):
                anomaly_counts["event_outside_chunk_date"] += 1

            if tournament.get("game") != "PTCG":
                anomaly_counts["non_ptcg_tournament"] += 1
            if tournament.get("format") != "STANDARD":
                anomaly_counts["non_standard_tournament"] += 1

            details = None
            if details_path.exists():
                details = load_json(details_path)
                row["platform"] = details.get("platform")
                platform_counts[str(details.get("platform"))] += 1
                organizer = details.get("organizer") or {}
                row["organizer"] = organizer.get("name") if isinstance(organizer, dict) else None
                if row["organizer"]:
                    organizer_counts[row["organizer"]] += 1
                if details.get("platform") != "PTCGL":
                    anomaly_counts["usable_non_ptcgl_details"] += int(standings_path.exists())
                if details.get("isOnline") is not True:
                    anomaly_counts["usable_not_online_details"] += int(standings_path.exists())
                if details.get("decklists") is not True:
                    anomaly_counts["usable_without_decklists_flag"] += int(standings_path.exists())
                if details.get("format") != "STANDARD":
                    anomaly_counts["usable_non_standard_details"] += int(standings_path.exists())

            if standings_path.exists():
                usable += 1
                standings = load_json(standings_path)
                n = len(standings)
                c = 0
                for player in standings:
                    deck = player.get("deck")
                    if deck_is_classified(deck):
                        c += 1
                        deck_counts[(deck.get("id") or deck.get("name") or "unknown")] += 1
                    country = player.get("country")
                    if country:
                        country_counts[country] += 1
                entries += n
                classified += c
                row["standings_players"] = n
                row["classified_players"] = c
                row["classification_coverage"] = (c / n) if n else None
                if isinstance(players_reported, int) and n != players_reported:
                    anomaly_counts["reported_vs_standings_player_mismatch"] += 1
                if not details_path.exists():
                    anomaly_counts["usable_missing_details"] += 1
            event_rows.append(row)

        chunk_rows.append({
            "chunk": chunk_dir.name,
            "start_date": chunk_start,
            "end_date": chunk_end,
            "complete": bool(manifest.get("complete")),
            "discovered_standard_rows": int(manifest.get("discovered_index_rows") or 0),
            "candidate_event_dirs": candidates,
            "usable_events": usable,
            "manifest_eligible_first_pass": int(manifest.get("eligible_first_pass") or 0),
            "entries": entries,
            "classified_entries": classified,
            "classification_coverage": classified / entries if entries else None,
        })

    usable_rows = [r for r in event_rows if r["has_standings"]]
    candidate_rows = event_rows
    total_entries = sum(r["standings_players"] or 0 for r in usable_rows)
    total_classified = sum(r["classified_players"] or 0 for r in usable_rows)
    coverages = [r["classification_coverage"] for r in usable_rows if r["classification_coverage"] is not None]
    sizes = [r["standings_players"] for r in usable_rows if isinstance(r["standings_players"], int)]

    dated = sorted((parse_dt(r["date"]), r) for r in usable_rows if parse_dt(r["date"]))
    max_gap_days = None
    max_gap_pair = None
    if len(dated) >= 2:
        gaps = [((dated[i][0] - dated[i-1][0]).total_seconds() / 86400, dated[i-1][1], dated[i][1]) for i in range(1, len(dated))]
        gap, before, after = max(gaps, key=lambda x: x[0])
        max_gap_days = gap
        max_gap_pair = {"before": {"date": before["date"], "name": before["name"]}, "after": {"date": after["date"], "name": after["name"]}}

    duplicate_ids = {k: v for k, v in seen_event_ids.items() if v > 1}
    anomaly_counts["duplicate_event_ids"] = len(duplicate_ids)

    mismatch_rows = []
    for r in usable_rows:
        if isinstance(r["reported_players"], int) and isinstance(r["standings_players"], int) and r["reported_players"] != r["standings_players"]:
            mismatch_rows.append({**r, "difference": r["standings_players"] - r["reported_players"]})
    mismatch_rows.sort(key=lambda r: abs(r["difference"]), reverse=True)

    low_coverage_rows = sorted(
        [r for r in usable_rows if r["classification_coverage"] is not None],
        key=lambda r: r["classification_coverage"]
    )[:20]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": {
            "start": min((c["start_date"] for c in chunk_rows if c["start_date"]), default=None),
            "end": max((c["end_date"] for c in chunk_rows if c["end_date"]), default=None),
        },
        "chunks": {
            "count": len(chunk_rows),
            "all_complete": manifests_complete and all(c["complete"] for c in chunk_rows),
        },
        "tournaments": {
            "standard_rows_discovered": discovered_total,
            "candidate_50plus_event_dirs": len(candidate_rows),
            "usable_online_ptcgl_events": len(usable_rows),
            "manifest_eligible_first_pass_total": manifest_eligible_total,
            "manifest_ineligible_or_failed_total": manifest_ineligible_total,
            "usable_share_of_candidates": len(usable_rows) / len(candidate_rows) if candidate_rows else None,
        },
        "players": {
            "stored_standings_entries": total_entries,
            "classified_entries": total_classified,
            "unclassified_entries": total_entries - total_classified,
            "overall_classification_coverage": total_classified / total_entries if total_entries else None,
        },
        "event_size": {
            "min": min(sizes) if sizes else None,
            "p25": percentile(sizes, .25),
            "median": median(sizes) if sizes else None,
            "p75": percentile(sizes, .75),
            "p90": percentile(sizes, .90),
            "max": max(sizes) if sizes else None,
        },
        "classification_coverage_by_event": {
            "min": min(coverages) if coverages else None,
            "p10": percentile(coverages, .10),
            "p25": percentile(coverages, .25),
            "median": median(coverages) if coverages else None,
            "p75": percentile(coverages, .75),
            "p90": percentile(coverages, .90),
            "max": max(coverages) if coverages else None,
            "events_ge_90pct": sum(c >= .90 for c in coverages),
            "events_ge_95pct": sum(c >= .95 for c in coverages),
            "events_ge_98pct": sum(c >= .98 for c in coverages),
            "events_100pct": sum(c == 1 for c in coverages),
            "events_lt_90pct": sum(c < .90 for c in coverages),
        },
        "timeline": {
            "max_gap_days_between_usable_events": max_gap_days,
            "max_gap_pair": max_gap_pair,
        },
        "anomalies": dict(anomaly_counts),
        "duplicate_event_ids": duplicate_ids,
        "largest_reported_vs_standings_mismatches": mismatch_rows[:20],
        "lowest_classification_coverage_events": low_coverage_rows,
        "top_deck_ids_all_periods_sanity_only": deck_counts.most_common(20),
        "top_organizers_by_usable_events": organizer_counts.most_common(20),
        "platforms_in_stored_details": platform_counts.most_common(),
        "countries_in_standings_top20": country_counts.most_common(20),
        "monthly": chunk_rows,
    }

    json_path = out_dir / "audit.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")

    csv_path = out_dir / "events.csv"
    fields = list(event_rows[0].keys()) if event_rows else []
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(event_rows)

    md = []
    md.append("# Historical Online archive audit")
    md.append("")
    md.append(f"Generated: {report['generated_at']}")
    md.append("")
    md.append("## Headline")
    md.append("")
    md.append(f"- Period: **{report['period']['start']} to {report['period']['end']}**")
    md.append(f"- Monthly chunks: **{report['chunks']['count']}**, all complete: **{report['chunks']['all_complete']}**")
    md.append(f"- Standard tournament index rows discovered: **{discovered_total:,}**")
    md.append(f"- 50+ player candidate tournament snapshots: **{len(candidate_rows):,}**")
    md.append(f"- Usable Online PTCGL tournaments with standings: **{len(usable_rows):,}**")
    md.append(f"- Stored player entries: **{total_entries:,}**")
    md.append(f"- Classified player entries: **{total_classified:,} / {total_entries:,} ({(100*total_classified/total_entries if total_entries else 0):.2f}%)**")
    md.append("")
    md.append("## Classification coverage")
    md.append("")
    cov = report["classification_coverage_by_event"]
    if coverages:
        md.append(f"- Median event coverage: **{100*cov['median']:.2f}%**")
        md.append(f"- 10th percentile: **{100*cov['p10']:.2f}%**")
        md.append(f"- Minimum: **{100*cov['min']:.2f}%**")
        md.append(f"- Events >=95%: **{cov['events_ge_95pct']}/{len(coverages)}**")
        md.append(f"- Events <90%: **{cov['events_lt_90pct']}/{len(coverages)}**")
    md.append("")
    md.append("## Event size")
    md.append("")
    es = report["event_size"]
    md.append(f"- Median stored field: **{es['median']}**")
    md.append(f"- 90th percentile: **{round_or_none(es['p90'], 1)}**")
    md.append(f"- Range: **{es['min']} to {es['max']}**")
    md.append("")
    md.append("## Timeline / integrity")
    md.append("")
    md.append(f"- Largest gap between usable event dates: **{round_or_none(max_gap_days, 1)} days**")
    md.append(f"- Duplicate tournament IDs: **{len(duplicate_ids)}**")
    md.append(f"- Reported-player vs standings-count mismatches: **{len(mismatch_rows)}**")
    md.append("")
    md.append("## Lowest-coverage events")
    md.append("")
    md.append("| Date | Event | Players | Classified | Coverage |")
    md.append("|---|---|---:|---:|---:|")
    for r in low_coverage_rows[:10]:
        covp = 100 * r["classification_coverage"] if r["classification_coverage"] is not None else 0
        md.append(f"| {str(r['date'])[:10]} | {str(r['name']).replace('|','/')} | {r['standings_players']} | {r['classified_players']} | {covp:.1f}% |")
    md.append("")
    md.append("## Monthly coverage")
    md.append("")
    md.append("| Chunk | Usable events | Entries | Classification |")
    md.append("|---|---:|---:|---:|")
    for c in chunk_rows:
        covp = 100 * c["classification_coverage"] if c["classification_coverage"] is not None else 0
        md.append(f"| {c['chunk']} | {c['usable_events']} | {c['entries']} | {covp:.2f}% |")
    md.append("")
    md.append("## Audit interpretation")
    md.append("")
    md.append("This audit describes the stored Online evidence only. It does **not** yet decide a classification-coverage cutoff for model fitting; that threshold should be chosen after reviewing the empirical coverage distribution and the effect of excluding low-coverage events.")
    md.append("")

    md_path = out_dir / "README.md"
    md_path.write_text("\n".join(md), encoding="utf-8")

    print(json.dumps({
        "chunks": len(chunk_rows),
        "discovered": discovered_total,
        "candidates": len(candidate_rows),
        "usable_events": len(usable_rows),
        "entries": total_entries,
        "classified": total_classified,
        "coverage": round_or_none(total_classified / total_entries if total_entries else None, 6),
        "median_event_coverage": round_or_none(median(coverages) if coverages else None, 6),
        "events_ge_95pct": sum(c >= .95 for c in coverages),
        "events_lt_90pct": sum(c < .90 for c in coverages),
        "max_gap_days": round_or_none(max_gap_days, 2),
        "duplicates": len(duplicate_ids),
        "player_count_mismatches": len(mismatch_rows),
    }, indent=2))


if __name__ == "__main__":
    main()
