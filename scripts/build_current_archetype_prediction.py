#!/usr/bin/env python3
"""Build the current settled-format archetype share forecast used by the research site.

The current forecast mirrors the historical settled-format model: the latest same-format
in-person major is the anchor, qualifying Online events after that major provide the
movement signal, and the two named-archetype distributions are blended without
renormalising any later user selection.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ONLINE_TAGS = ROOT / "data" / "processed" / "format-tags" / "online-events.json"
IRL_TAGS = ROOT / "data" / "processed" / "format-tags" / "irl-events.json"
IRL_EVENTS = ROOT / "data" / "raw" / "irl" / "labs" / "events"
OUT = ROOT / "data" / "processed" / "current-archetype-prediction.json"

ONLINE_CLASSIFICATION_MIN = 0.90
IRL_START = 0.80
IRL_FLOOR = 0.55
IRL_DECAY_PER_DAY = 0.01


def load(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(value: str) -> date:
    return date.fromisoformat(str(value)[:10])


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def end_of_iso_week(value: date) -> date:
    return value + timedelta(days=6 - value.weekday())


def clean_key(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    return text if text else "name:" + fallback.strip().lower()


def ignored(name: object, key: object = None) -> bool:
    n = str(name or "").strip().lower()
    k = str(key or "").strip().lower()
    return n in {"", "other", "unknown", "unclassified"} or k in {"other", "unknown", "unclassified"}


def normalise(counts: Counter) -> dict[str, float]:
    total = sum(max(0.0, float(v)) for v in counts.values())
    return {k: max(0.0, float(v)) / total for k, v in counts.items() if v > 0} if total else {}


def blend(irl: dict[str, float], online: dict[str, float], irl_weight: float) -> dict[str, float]:
    if not irl or not online:
        return irl or online
    keys = set(irl) | set(online)
    out = {
        k: irl_weight * irl.get(k, 0.0) + (1.0 - irl_weight) * online.get(k, 0.0)
        for k in keys
    }
    total = sum(out.values())
    return {k: v / total for k, v in out.items()} if total else {}


def latest_irl_distribution(irl_id: str) -> tuple[dict[str, float], dict[str, str], dict]:
    raw = load(IRL_EVENTS / f"{irl_id}.json", {}) or {}
    counts: Counter = Counter()
    names: dict[str, str] = {}
    for deck in raw.get("decks") or []:
        name = str(deck.get("name") or deck.get("slug") or "").strip()
        key = clean_key(deck.get("slug"), name)
        if ignored(name, key):
            continue
        counts[key] += int(deck.get("entries") or 0)
        names.setdefault(key, name or key)
    return normalise(counts), names, raw


def online_archive() -> tuple[dict[str, Counter], dict[str, str], dict[str, float]]:
    counts: dict[str, Counter] = {}
    names: dict[str, str] = {}
    coverage: dict[str, float] = {}
    for path in ROOT.glob("data/raw/online/backfill/chunks/*/*/standings.json"):
        event_id = path.parent.name
        rows = load(path, []) or []
        event_counts: Counter = Counter()
        classified = 0
        for row in rows:
            deck = row.get("deck") if isinstance(row, dict) else None
            if not isinstance(deck, dict):
                continue
            name = str(deck.get("name") or deck.get("id") or "").strip()
            key = clean_key(deck.get("id"), name)
            if not ignored(name, key):
                event_counts[key] += 1
                names.setdefault(key, name or key)
            if name or str(deck.get("id") or "").strip():
                classified += 1
        counts[event_id] = event_counts
        coverage[event_id] = classified / len(rows) if rows else 0.0
    return counts, names, coverage


def main() -> None:
    irl_tags = load(IRL_TAGS, []) or []
    online_tags = load(ONLINE_TAGS, []) or []
    if not irl_tags:
        raise RuntimeError("No IRL format tags found")

    latest = max(
        irl_tags,
        key=lambda r: (parse_date(r["end_date"]), parse_date(r["start_date"]), str(r["id"])),
    )
    irl_id = str(latest["id"])
    current_format = str(latest["display_format"])
    latest_irl, irl_names, irl_raw = latest_irl_distribution(irl_id)
    if not latest_irl:
        raise RuntimeError(f"Latest IRL event {irl_id} has no named-archetype distribution")

    major_end = parse_date(latest["end_date"])
    major_final_day = end_of_iso_week(major_end)
    online_counts, online_names, online_coverage = online_archive()

    qualifying = []
    for event in online_tags:
        event_id = str(event.get("id"))
        if str(event.get("display_format")) != current_format:
            continue
        if event_id not in online_counts:
            continue
        if online_coverage.get(event_id, 0.0) < ONLINE_CLASSIFICATION_MIN:
            continue
        event_date = parse_dt(event["start_at"]).date()
        if event_date <= major_final_day:
            continue
        qualifying.append((event_date, event_id, event))

    if not qualifying:
        raise RuntimeError("No qualifying same-format Online evidence after the latest IRL major")

    evidence_through = max(d for d, _, _ in qualifying)
    online_ids = [event_id for d, event_id, _ in qualifying if d <= evidence_through]
    online_total: Counter = Counter()
    for event_id in online_ids:
        online_total.update(online_counts[event_id])
    online = normalise(online_total)
    if not online:
        raise RuntimeError("Qualifying Online evidence has no named-archetype distribution")

    # The archive currently closes at the end of the prior day. Use the following day
    # as the forecast date so the displayed weight describes the next event-day forecast.
    forecast_date = evidence_through + timedelta(days=1)
    days_since_major = max(0, (forecast_date - major_final_day).days)
    irl_weight = max(IRL_FLOOR, min(IRL_START, IRL_START - IRL_DECAY_PER_DAY * days_since_major))
    predicted = blend(latest_irl, online, irl_weight)

    names = {**online_names, **irl_names}
    archetypes = []
    for key in sorted(set(latest_irl) | set(online) | set(predicted), key=lambda k: predicted.get(k, 0.0), reverse=True):
        archetypes.append({
            "key": key,
            "name": names.get(key, key),
            "irl_pct": latest_irl.get(key, 0.0) * 100.0,
            "online_pct": online.get(key, 0.0) * 100.0,
            "blended_pct": predicted.get(key, 0.0) * 100.0,
        })

    payload = {
        "schema_version": 1,
        "forecast_date": forecast_date.isoformat(),
        "online_evidence_through": evidence_through.isoformat(),
        "format": current_format,
        "latest_irl": {
            "id": irl_id,
            "name": irl_raw.get("name") or latest.get("name") or irl_id,
            "start_date": latest["start_date"],
            "end_date": latest["end_date"],
            "players": irl_raw.get("players") or latest.get("players"),
        },
        "days_since_major": days_since_major,
        "weights": {
            "irl": irl_weight,
            "online": 1.0 - irl_weight,
            "rule": {
                "start_irl": IRL_START,
                "decay_per_day": IRL_DECAY_PER_DAY,
                "floor_irl": IRL_FLOOR,
            },
        },
        "online_event_count": len(online_ids),
        "online_classification_min": ONLINE_CLASSIFICATION_MIN,
        "archetypes": archetypes,
        "notes": [
            "IRL and Online are named-archetype distributions normalised using the same semantics as the historical scoring model.",
            "Online uses qualifying same-format events after the latest in-person major, not all Online events in the format.",
            "The blend uses the current best in-sample historical weighting rule and remains exploratory.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "format": current_format,
        "latest_irl": payload["latest_irl"]["name"],
        "forecast_date": payload["forecast_date"],
        "online_evidence_through": payload["online_evidence_through"],
        "online_event_count": payload["online_event_count"],
        "weights": payload["weights"],
        "archetype_count": len(archetypes),
    }, indent=2))


if __name__ == "__main__":
    main()
