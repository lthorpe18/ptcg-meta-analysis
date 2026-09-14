#!/usr/bin/env python3
"""Tag historical Online and IRL tournaments with the legal Standard format.

Raw source snapshots are never modified. Derived tags are written under
``data/processed/format-tags`` using ``data/reference/legality-calendar.json``.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALENDAR_PATH = ROOT / "data/reference/legality-calendar.json"
ONLINE_ROOT = ROOT / "data/raw/online/backfill/chunks"
IRL_ROOT = ROOT / "data/raw/irl/labs/events"
OUT_DIR = ROOT / "data/processed/format-tags"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


def online_period(periods, event_dt: datetime):
    for period in periods:
        start = parse_dt(period["start_at"])
        end = parse_dt(period["end_at_exclusive"])
        if start <= event_dt < end:
            return period, start
    return None, None


def irl_period(periods, event_date):
    for period in periods:
        start = parse_date(period["start_date"])
        end = parse_date(period["end_date_exclusive"])
        if start <= event_date < end:
            return period, start
    return None, None


def tag_online(periods):
    rows = []
    seen = set()
    for tournament_path in sorted(ONLINE_ROOT.glob("*/*/tournament.json")):
        event_dir = tournament_path.parent
        # Match the audited usable archive: only events with collected standings.
        if not (event_dir / "standings.json").exists():
            continue
        event = load_json(tournament_path)
        event_id = str(event.get("id") or event_dir.name)
        if event_id in seen:
            raise RuntimeError(f"Duplicate Online event ID: {event_id}")
        seen.add(event_id)
        event_dt = parse_dt(event["date"])
        period, period_start = online_period(periods, event_dt)
        if period is None:
            raise RuntimeError(f"No Online format period for {event_id} at {event['date']}")
        rows.append({
            "id": event_id,
            "name": event.get("name"),
            "environment": "online",
            "start_at": event_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "players": event.get("players"),
            "display_format": period["display_format"],
            "regulation_marks": period["regulation_marks"],
            "latest_expansion": period["latest_expansion"],
            "format_start_at": period["start_at"],
            "hours_into_format": round((event_dt - period_start).total_seconds() / 3600, 3),
        })
    rows.sort(key=lambda r: (r["start_at"], r["id"]))
    return rows


def tag_irl(periods):
    rows = []
    seen = set()
    for event_path in sorted(IRL_ROOT.glob("*.json")):
        event = load_json(event_path)
        event_id = str(event.get("id") or event_path.stem)
        if event_id in seen:
            raise RuntimeError(f"Duplicate IRL event ID: {event_id}")
        seen.add(event_id)
        event_date = parse_date(event["start_date"])
        period, period_start = irl_period(periods, event_date)
        if period is None:
            raise RuntimeError(f"No IRL format period for {event_id} at {event['start_date']}")
        rows.append({
            "id": event_id,
            "name": event.get("name"),
            "environment": "irl",
            "event_type": event.get("event_type"),
            "start_date": event["start_date"],
            "end_date": event.get("end_date"),
            "players": event.get("players"),
            "field_count_ratio": event.get("field_count_ratio"),
            "target_eligible_ge_95": (event.get("field_count_ratio") or 0) >= 0.95,
            "target_eligible_ge_98": (event.get("field_count_ratio") or 0) >= 0.98,
            "display_format": period["display_format"],
            "regulation_marks": period["regulation_marks"],
            "latest_expansion": period["latest_expansion"],
            "format_start_date": period["start_date"],
            "days_into_format": (event_date - period_start).days,
        })

    rows.sort(key=lambda r: (r["start_date"], r["id"]))

    # First IRL weekend/cohort in each format, not merely one arbitrary event.
    first_date_by_format = {}
    date_counts = Counter(r["start_date"] for r in rows)
    for row in rows:
        first_date_by_format.setdefault(row["display_format"], row["start_date"])
    for row in rows:
        row["format_opening_cohort"] = row["start_date"] == first_date_by_format[row["display_format"]]
        row["same_start_date_event_count"] = date_counts[row["start_date"]]
        row["same_start_date_cohort"] = date_counts[row["start_date"]] > 1
    return rows


def write_csv(path: Path, rows):
    if not rows:
        return
    keys = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def count_formats(rows):
    return dict(sorted(Counter(r["display_format"] for r in rows).items()))


def main():
    calendar = load_json(CALENDAR_PATH)
    online = tag_online(calendar["format_periods"]["online"])
    irl = tag_irl(calendar["format_periods"]["irl"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "online-events.json").write_text(json.dumps(online, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "irl-events.json").write_text(json.dumps(irl, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(OUT_DIR / "online-events.csv", online)
    write_csv(OUT_DIR / "irl-events.csv", irl)

    opening = [r for r in irl if r["format_opening_cohort"]]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "calendar_schema_version": calendar.get("schema_version"),
        "online_events_tagged": len(online),
        "irl_events_tagged": len(irl),
        "irl_primary_targets_ge_95": sum(r["target_eligible_ge_95"] for r in irl),
        "irl_sensitivity_targets_ge_98": sum(r["target_eligible_ge_98"] for r in irl),
        "online_by_format": count_formats(online),
        "irl_by_format": count_formats(irl),
        "irl_format_opening_cohorts": [
            {
                "start_date": r["start_date"],
                "display_format": r["display_format"],
                "id": r["id"],
                "name": r["name"],
            }
            for r in opening
        ],
        "notes": [
            "Online tags use the exact Limitless tournament start timestamp against PTCGL legality boundaries.",
            "IRL tags use the major start date against official IRL legality boundaries.",
            "Raw source snapshots are unchanged; these are reproducible derived tags.",
            "Same-start-date IRL majors are flagged as correlated cohorts for chronological backtesting.",
            "format_opening_cohort marks every major on the earliest major start date observed in that format.",
        ],
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    readme = [
        "# Historical tournament format tags",
        "",
        f"- Online usable events tagged: **{len(online):,}**",
        f"- IRL majors tagged: **{len(irl):,}**",
        f"- IRL primary targets (>=95% field capture): **{sum(r['target_eligible_ge_95'] for r in irl):,}**",
        f"- IRL sensitivity targets (>=98% field capture): **{sum(r['target_eligible_ge_98'] for r in irl):,}**",
        "- Unmatched events: **0** (the script fails instead of silently leaving an event untagged)",
        "",
        "## Online events by format",
        "",
    ]
    for fmt, count in count_formats(online).items():
        readme.append(f"- {fmt}: {count}")
    readme.extend(["", "## IRL majors by format", ""])
    for fmt, count in count_formats(irl).items():
        readme.append(f"- {fmt}: {count}")
    readme.extend([
        "",
        "## Backtest flags",
        "",
        "IRL rows retain field-completeness eligibility, same-date cohort flags, the legal format start date, and the number of days into that format. These fields are intended to separate settled-format from transition-major analysis without altering the raw data.",
        "",
    ])
    (OUT_DIR / "README.md").write_text("\n".join(readme), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
