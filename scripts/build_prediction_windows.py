#!/usr/bin/env python3
"""Build auditable historical prediction windows for each IRL major.

The output deliberately contains evidence membership and timing only. It does not
fit or score any blend model. Raw source snapshots remain unchanged.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "processed" / "prediction-windows"
RESULTS_DIR = ROOT / "results" / "prediction-windows"
ONLINE_THRESHOLD = 0.90


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def online_quality() -> dict[str, dict]:
    quality: dict[str, dict] = {}
    for standings_path in ROOT.glob("data/raw/online/backfill/chunks/*/*/standings.json"):
        event_id = standings_path.parent.name
        rows = load_json(standings_path, []) or []
        classified = 0
        for row in rows:
            deck = row.get("deck") if isinstance(row, dict) else None
            if isinstance(deck, dict) and (deck.get("id") or deck.get("name")):
                classified += 1
        total = len(rows)
        quality[event_id] = {
            "stored_entries": total,
            "classified_entries": classified,
            "classification_share": classified / total if total else 0.0,
        }
    return quality


def build_cohorts(irl: list[dict]) -> tuple[list[dict], dict[str, str]]:
    """Cluster overlapping IRL events so contemporaneous majors cannot leak."""
    rows = sorted(irl, key=lambda r: (r["start_date"], r["end_date"], str(r["id"])))
    cohorts: list[dict] = []
    current: dict | None = None

    for row in rows:
        start = parse_date(row["start_date"])
        end = parse_date(row["end_date"])
        if current is None or start > current["end_obj"]:
            current = {
                "start_obj": start,
                "end_obj": end,
                "event_ids": [str(row["id"])],
            }
            cohorts.append(current)
        else:
            current["event_ids"].append(str(row["id"]))
            if end > current["end_obj"]:
                current["end_obj"] = end

    event_to_cohort: dict[str, str] = {}
    serialised: list[dict] = []
    for idx, cohort in enumerate(cohorts, start=1):
        cohort_id = f"C{idx:03d}"
        item = {
            "cohort_id": cohort_id,
            "start_date": cohort["start_obj"].isoformat(),
            "end_date": cohort["end_obj"].isoformat(),
            "event_ids": cohort["event_ids"],
            "event_count": len(cohort["event_ids"]),
        }
        serialised.append(item)
        for event_id in cohort["event_ids"]:
            event_to_cohort[event_id] = cohort_id

    return serialised, event_to_cohort


def main() -> None:
    online = load_json(ROOT / "data/processed/format-tags/online-events.json", []) or []
    irl = load_json(ROOT / "data/processed/format-tags/irl-events.json", []) or []
    if not online or not irl:
        raise SystemExit("Tagged Online/IRL event files are required first.")

    quality = online_quality()
    missing_quality = sorted(str(e["id"]) for e in online if str(e["id"]) not in quality)
    if missing_quality:
        raise SystemExit(f"Missing standings quality for {len(missing_quality)} Online events")

    cohorts, event_to_cohort = build_cohorts(irl)
    cohort_by_id = {c["cohort_id"]: c for c in cohorts}
    irl_by_id = {str(e["id"]): e for e in irl}
    online_by_id = {str(e["id"]): e for e in online}

    windows: list[dict] = []
    opening_flag_mismatches: list[str] = []

    for target in sorted(irl, key=lambda r: (r["start_date"], str(r["id"]))):
        target_id = str(target["id"])
        cohort = cohort_by_id[event_to_cohort[target_id]]
        cohort_start = parse_date(cohort["start_date"])
        cutoff = datetime.combine(cohort_start, datetime.min.time(), tzinfo=timezone.utc)
        target_format = target["display_format"]

        compatible_online_all = [
            e for e in online
            if e["display_format"] == target_format and parse_dt(e["start_at"]) < cutoff
        ]
        compatible_online_primary = [
            e for e in compatible_online_all
            if quality[str(e["id"])]["classification_share"] >= ONLINE_THRESHOLD
        ]
        compatible_online_excluded = [
            e for e in compatible_online_all
            if quality[str(e["id"])]["classification_share"] < ONLINE_THRESHOLD
        ]

        prior_all = [
            e for e in irl
            if parse_date(e["end_date"]) < cohort_start
        ]
        prior_same_format = [e for e in prior_all if e["display_format"] == target_format]
        prior_other_format = [e for e in prior_all if e["display_format"] != target_format]
        prior_same_format.sort(key=lambda e: (e["end_date"], e["start_date"], str(e["id"])), reverse=True)
        prior_other_format.sort(key=lambda e: (e["end_date"], e["start_date"], str(e["id"])), reverse=True)
        prior_all.sort(key=lambda e: (e["end_date"], e["start_date"], str(e["id"])), reverse=True)

        is_transition = len(prior_same_format) == 0
        if bool(target.get("format_opening_cohort")) != is_transition:
            opening_flag_mismatches.append(target_id)

        latest_prior = prior_all[0] if prior_all else None
        latest_compatible = prior_same_format[0] if prior_same_format else None

        online_entries = sum(quality[str(e["id"])]["stored_entries"] for e in compatible_online_primary)
        online_classified = sum(quality[str(e["id"])]["classified_entries"] for e in compatible_online_primary)

        window = {
            "target_id": target_id,
            "target_name": target["name"],
            "target_start_date": target["start_date"],
            "target_end_date": target["end_date"],
            "target_format": target_format,
            "target_event_type": target["event_type"],
            "target_players": target["players"],
            "target_field_capture": target.get("field_count_ratio"),
            "target_eligible_ge_95": bool(target.get("target_eligible_ge_95")),
            "target_eligible_ge_98": bool(target.get("target_eligible_ge_98")),
            "cohort_id": cohort["cohort_id"],
            "cohort_start_date": cohort["start_date"],
            "cohort_end_date": cohort["end_date"],
            "cohort_event_ids": cohort["event_ids"],
            "cohort_event_count": cohort["event_count"],
            "cutoff_at": cutoff.isoformat().replace("+00:00", "Z"),
            "window_class": "transition" if is_transition else "settled",
            "transition_reason": (
                "archive_start" if is_transition and not prior_all
                else "format_change" if is_transition
                else None
            ),
            "online_primary_classification_threshold": ONLINE_THRESHOLD,
            "online_compatible_all_ids": [str(e["id"]) for e in compatible_online_all],
            "online_primary_ids": [str(e["id"]) for e in compatible_online_primary],
            "online_excluded_low_classification_ids": [str(e["id"]) for e in compatible_online_excluded],
            "online_compatible_all_count": len(compatible_online_all),
            "online_primary_count": len(compatible_online_primary),
            "online_excluded_low_classification_count": len(compatible_online_excluded),
            "online_primary_stored_entries": online_entries,
            "online_primary_classified_entries": online_classified,
            "online_primary_classification_share": online_classified / online_entries if online_entries else None,
            "prior_irl_all_ids": [str(e["id"]) for e in prior_all],
            "prior_irl_same_format_ids": [str(e["id"]) for e in prior_same_format],
            "prior_irl_same_format_ge_95_ids": [
                str(e["id"]) for e in prior_same_format if e.get("target_eligible_ge_95")
            ],
            "prior_irl_other_format_ids": [str(e["id"]) for e in prior_other_format],
            "prior_irl_same_format_count": len(prior_same_format),
            "prior_irl_same_format_ge_95_count": sum(bool(e.get("target_eligible_ge_95")) for e in prior_same_format),
            "latest_prior_irl_id": str(latest_prior["id"]) if latest_prior else None,
            "latest_compatible_irl_id": str(latest_compatible["id"]) if latest_compatible else None,
            "availability_proxy": "Online tournament start timestamp is used as the evidence-availability boundary because exact decklist publication/completion timestamps are not archived.",
        }
        windows.append(window)

    # Hard leakage checks.
    leakage_errors: list[str] = []
    for window in windows:
        cutoff = parse_dt(window["cutoff_at"])
        cohort_ids = set(window["cohort_event_ids"])
        for event_id in window["online_primary_ids"]:
            if parse_dt(online_by_id[event_id]["start_at"]) >= cutoff:
                leakage_errors.append(f"{window['target_id']}: Online {event_id} at/after cutoff")
        for event_id in window["prior_irl_all_ids"]:
            if event_id in cohort_ids or parse_date(irl_by_id[event_id]["end_date"]) >= parse_date(window["cohort_start_date"]):
                leakage_errors.append(f"{window['target_id']}: IRL {event_id} overlaps target cohort")
    if leakage_errors:
        raise SystemExit("Leakage audit failed:\n" + "\n".join(leakage_errors[:20]))

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_count": len(windows),
        "cohort_count": len(cohorts),
        "multi_event_cohort_count": sum(c["event_count"] > 1 for c in cohorts),
        "transition_window_count": sum(w["window_class"] == "transition" for w in windows),
        "settled_window_count": sum(w["window_class"] == "settled" for w in windows),
        "primary_target_count_ge_95": sum(w["target_eligible_ge_95"] for w in windows),
        "sensitivity_target_count_ge_98": sum(w["target_eligible_ge_98"] for w in windows),
        "online_primary_classification_threshold": ONLINE_THRESHOLD,
        "opening_flag_mismatch_ids": opening_flag_mismatches,
        "leakage_error_count": 0,
        "availability_proxy": "Online tournament start timestamp; exact completion/decklist-publication time is unavailable in the archive.",
    }

    pack = {
        "schema_version": 1,
        "summary": summary,
        "cohorts": cohorts,
        "windows": windows,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "windows.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with (OUT_DIR / "events.csv").open("w", encoding="utf-8", newline="") as f:
        cols = [
            "target_id", "target_name", "target_start_date", "target_event_type", "target_format",
            "window_class", "cohort_id", "cohort_event_count", "cutoff_at",
            "online_primary_count", "online_primary_stored_entries",
            "online_excluded_low_classification_count", "prior_irl_same_format_count",
            "prior_irl_same_format_ge_95_count", "target_field_capture",
            "target_eligible_ge_95", "target_eligible_ge_98",
        ]
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for window in windows:
            writer.writerow({k: window.get(k) for k in cols})

    readme = f"""# Baseline historical prediction windows

Generated from the tagged Online and IRL archives. These files define **what evidence is available** for each historical IRL target; they do not yet select or score a blend formula.

## Headline

- Targets/windows: **{summary['window_count']}**
- IRL overlap cohorts: **{summary['cohort_count']}**
- Multi-event contemporaneous cohorts: **{summary['multi_event_cohort_count']}**
- Settled-format windows: **{summary['settled_window_count']}**
- Transition/opening-format windows: **{summary['transition_window_count']}**
- Primary targets (IRL capture >=95%): **{summary['primary_target_count_ge_95']}**
- Sensitivity targets (IRL capture >=98%): **{summary['sensitivity_target_count_ge_98']}**
- Online primary-evidence classification threshold: **{ONLINE_THRESHOLD:.0%}**
- Leakage audit errors: **0**

## Window rules

1. IRL events whose date ranges overlap are placed in one cohort. No event in the target cohort can be prior evidence for another event in that cohort.
2. The prediction cutoff is 00:00 UTC on the cohort's first start date because the IRL archive has dates, not exact start timestamps.
3. Clean Online evidence must be the **same legal format**, start before the cutoff, and have at least **90% deck classification**. Same-format events below 90% remain recorded as excluded evidence for sensitivity work.
4. Prior IRL evidence must have finished before the target cohort starts. Same-format and previous-format evidence are stored separately.
5. A window is `transition` when no earlier completed IRL major exists in the target format; otherwise it is `settled`.
6. Online tournament **start time is an availability proxy**. Exact completion/decklist-publication timestamps are not present in the historical archive, so this assumption is explicit and can be challenged later.

## Files

- `data/processed/prediction-windows/windows.json` — full auditable window membership
- `data/processed/prediction-windows/events.csv` — one-row-per-target review table
- `data/processed/prediction-windows/summary.json` — headline audit counts
"""
    (RESULTS_DIR / "README.md").write_text(readme, encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
