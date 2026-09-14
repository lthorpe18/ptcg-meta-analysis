#!/usr/bin/env python3
"""Collect historical IRL Masters Day-1 field data from public Limitless Labs pages."""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import time
from datetime import date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://labs.limitlesstcg.com"
UA = "ptcg-meta-analysis historical research; public Limitless Labs pages"
MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}


def clean(value: str) -> str:
    value = re.sub(r"<[^>]*>", " ", value or "")
    value = html_lib.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def get(url: str, attempts: int = 4) -> str:
    last = None
    for attempt in range(attempts):
        try:
            req = Request(url, headers={"User-Agent": UA})
            with urlopen(req, timeout=45) as r:
                return r.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            last = exc
            if exc.code == 429 or exc.code >= 500:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise
        except URLError as exc:
            last = exc
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"Could not fetch {url}: {last}")


def parse_date_range(text: str):
    patterns = [
        re.compile(r"([A-Z][a-z]+)\s+(\d{1,2})\s*[–-]\s*([A-Z][a-z]+)\s+(\d{1,2}),\s*(20\d{2})"),
        re.compile(r"([A-Z][a-z]+)\s+(\d{1,2})\s*[–-]\s*(\d{1,2}),\s*(20\d{2})"),
        re.compile(r"([A-Z][a-z]+)\s+(\d{1,2}),\s*(20\d{2})"),
    ]
    m = patterns[0].search(text)
    if m:
        sm, sd, em, ed, y = m.groups()
        start = date(int(y), MONTHS[sm], int(sd))
        end_year = int(y)
        if MONTHS[em] < MONTHS[sm]:
            end_year += 1
        end = date(end_year, MONTHS[em], int(ed))
        return start, end
    m = patterns[1].search(text)
    if m:
        month, sd, ed, y = m.groups()
        start = date(int(y), MONTHS[month], int(sd))
        end = date(int(y), MONTHS[month], int(ed))
        return start, end
    m = patterns[2].search(text)
    if m:
        month, d, y = m.groups()
        only = date(int(y), MONTHS[month], int(d))
        return only, only
    return None, None


def event_type(name: str) -> str:
    n = name.lower()
    if "world championship" in n:
        return "World Championship"
    if "international championship" in n:
        return "International Championship"
    if "regional championship" in n:
        return "Regional Championship"
    if "special event" in n:
        return "Special Event"
    return "Other"


def discover_event_ids(home: str):
    ids = []
    seen = set()
    for match in re.finditer(r'href=["\']/([0-9]{4})/standings["\']', home, re.I):
        event_id = match.group(1)
        if event_id not in seen:
            ids.append(event_id)
            seen.add(event_id)
    return ids


def percentages(cells):
    out = []
    for cell in cells:
        for m in re.finditer(r"(-?\d+(?:\.\d+)?)%", str(cell)):
            out.append(float(m.group(1)))
    return out


def parse_deck_rows(page: str, event_id: str):
    rows = []
    for tr in re.finditer(r"<tr[^>]*>([\s\S]*?)</tr>", page, re.I):
        body = tr.group(1)
        link = re.search(
            rf'href=["\']/{re.escape(event_id)}/decks/([^"\'?]+)["\'][^>]*>([\s\S]*?)</a>',
            body,
            re.I,
        )
        if not link:
            continue
        cells = [clean(m.group(1)) for m in re.finditer(r"<td[^>]*>([\s\S]*?)</td>", body, re.I)]
        entries = 0
        if len(cells) > 1:
            raw = re.sub(r"[, ]", "", cells[1])
            if raw.isdigit():
                entries = int(raw)
        if not entries:
            for cell in cells:
                raw = re.sub(r"[% ,]", "", cell)
                if raw.isdigit() and int(raw) >= 1:
                    entries = int(raw)
                    break
        pcts = percentages(cells)
        share = pcts[0] if len(pcts) > 1 else (pcts[0] if pcts else None)
        rows.append({
            "name": clean(link.group(2)),
            "slug": link.group(1),
            "entries": entries,
            "share": share,
        })

    dedup = {}
    for row in rows:
        if row["name"] and row["entries"]:
            dedup[row["slug"]] = row
    return sorted(dedup.values(), key=lambda x: (-x["entries"], x["name"]))


def parse_event(page: str, event_id: str):
    text = clean(page)
    title_match = re.search(r"<title>(.*?)</title>", page, re.I | re.S)
    name = clean(title_match.group(1) if title_match else "")
    name = re.sub(r"^Decks:\s*", "", name, flags=re.I)
    name = re.sub(r"\s*[–-]\s*Limitless Labs.*$", "", name, flags=re.I)

    start, end = parse_date_range(text)
    players_m = re.search(r"([\d,]+)\s+players?", text, re.I)
    players = int(players_m.group(1).replace(",", "")) if players_m else 0
    decks = parse_deck_rows(page, event_id)
    entries_sum = sum(d["entries"] for d in decks)
    other_entries = sum(d["entries"] for d in decks if d["name"].strip().lower() == "other")
    classified_entries = entries_sum - other_entries

    return {
        "id": event_id,
        "name": name or f"Labs {event_id}",
        "event_type": event_type(name),
        "division": "Masters",
        "start_date": start.isoformat() if start else None,
        "end_date": end.isoformat() if end else None,
        "players": players,
        "source": "Limitless Labs",
        "source_url": f"{BASE}/{event_id}/decks?day=1",
        "view": "day1",
        "variant_grouping": False,
        "decks": decks,
        "deck_entries_sum": entries_sum,
        "classified_entries": classified_entries,
        "other_entries": other_entries,
        "classified_share": (classified_entries / players) if players else None,
        "field_count_ratio": (entries_sum / players) if players else None,
        "complete": bool(players and decks),
    }


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-date", default="2024-09-01")
    ap.add_argument("--end-date", default="2026-09-13")
    ap.add_argument("--out-dir", default="data/raw/irl/labs")
    ap.add_argument("--sleep-ms", type=int, default=150)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    start_limit = date.fromisoformat(args.start_date)
    end_limit = date.fromisoformat(args.end_date)
    out = Path(args.out_dir)
    events_dir = out / "events"
    events_dir.mkdir(parents=True, exist_ok=True)

    home = get(BASE + "/")
    event_ids = discover_event_ids(home)
    if not event_ids:
        raise RuntimeError("Limitless Labs home page exposed no tournament IDs")

    failures = []
    collected = []
    skipped_outside_range = []
    for i, event_id in enumerate(event_ids, start=1):
        path = events_dir / f"{event_id}.json"
        event = None
        if path.exists() and not args.force:
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                if existing.get("complete"):
                    event = existing
            except Exception:
                event = None

        if event is None:
            url = f"{BASE}/{event_id}/decks?day=1"
            print(f"[{i}/{len(event_ids)}] {event_id}: fetching {url}", flush=True)
            try:
                page = get(url)
                event = parse_event(page, event_id)
            except Exception as exc:
                failures.append({"id": event_id, "error": str(exc)})
                print(f"  failed: {exc}", flush=True)
                continue
            if not event.get("start_date"):
                failures.append({"id": event_id, "error": "could not parse event date"})
                continue
            d = date.fromisoformat(event["start_date"])
            if d < start_limit or d > end_limit:
                skipped_outside_range.append(event_id)
                continue
            if not event.get("decks"):
                failures.append({"id": event_id, "error": "parsed zero deck rows"})
                continue
            write_json(path, event)
            time.sleep(max(0, args.sleep_ms) / 1000)
        else:
            print(f"[{i}/{len(event_ids)}] {event_id}: cached", flush=True)

        if event.get("start_date"):
            d = date.fromisoformat(event["start_date"])
            if start_limit <= d <= end_limit:
                collected.append(event)

    collected.sort(key=lambda x: (x.get("start_date") or "", x["id"]))
    types = {}
    for event in collected:
        types[event["event_type"]] = types.get(event["event_type"], 0) + 1

    count_ratios = [e["field_count_ratio"] for e in collected if e.get("field_count_ratio") is not None]
    class_shares = [e["classified_share"] for e in collected if e.get("classified_share") is not None]

    index = [
        {k: e.get(k) for k in [
            "id", "name", "event_type", "division", "start_date", "end_date",
            "players", "deck_entries_sum", "classified_entries", "other_entries",
            "classified_share", "field_count_ratio", "source_url"
        ]}
        for e in collected
    ]
    manifest = {
        "collector_version": "0.1",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "source": BASE,
        "requested_start_date": args.start_date,
        "requested_end_date": args.end_date,
        "home_event_ids_discovered": len(event_ids),
        "events_collected_in_range": len(collected),
        "events_by_type": types,
        "total_reported_players": sum(e.get("players") or 0 for e in collected),
        "total_deck_entries": sum(e.get("deck_entries_sum") or 0 for e in collected),
        "total_other_entries": sum(e.get("other_entries") or 0 for e in collected),
        "mean_field_count_ratio": (sum(count_ratios) / len(count_ratios)) if count_ratios else None,
        "min_field_count_ratio": min(count_ratios) if count_ratios else None,
        "max_field_count_ratio": max(count_ratios) if count_ratios else None,
        "mean_classified_share": (sum(class_shares) / len(class_shares)) if class_shares else None,
        "failures": failures,
        "skipped_outside_range": skipped_outside_range,
        "complete": len(failures) == 0 and len(collected) > 0,
        "notes": [
            "Masters division only.",
            "Exact variant grouping retained (variant grouping OFF).",
            "Day-1 metagame view requested from Limitless Labs.",
            "The source may not contain every historical major; missing source events must be audited separately.",
        ],
    }

    write_json(out / "index.json", index)
    write_json(out / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2), flush=True)

    if not collected:
        raise RuntimeError("No in-range IRL events were collected")


if __name__ == "__main__":
    main()
