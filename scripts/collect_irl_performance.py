#!/usr/bin/env python3
"""Collect popularity-adjusted IRL performance evidence from public Limitless Labs.

This deliberately leaves the existing Day-1 field archive untouched. It reuses the
71 audited Masters events in data/raw/irl/labs/index.json and stores only aggregate
archetype performance evidence: Day-1/Day-2 deck rows and top-finish counts. Player
names/handles are not retained.
"""

from __future__ import annotations

import html as html_lib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://labs.limitlesstcg.com"
UA = "ptcg-meta-analysis IRL performance research; public Limitless Labs pages"
INDEX = Path("data/raw/irl/labs/index.json")
DAY1_DIR = Path("data/raw/irl/labs/events")
OUT = Path("data/raw/irl-performance/labs")


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


def cells_from_row(body: str) -> list[str]:
    return [clean(m.group(1)) for m in re.finditer(r"<td[^>]*>([\s\S]*?)</td>", body, re.I)]


def percentages(cells: list[str]) -> list[float]:
    out = []
    for cell in cells:
        for m in re.finditer(r"(-?\d+(?:\.\d+)?)%", cell):
            out.append(float(m.group(1)))
    return out


def first_int(cells: list[str]) -> int | None:
    for cell in cells:
        raw = re.sub(r"[, ]", "", cell)
        if raw.isdigit():
            return int(raw)
    return None


def parse_record(cells: list[str]) -> tuple[int, int, int] | None:
    text = " | ".join(cells)
    m = re.search(r"\b(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\b", text)
    if not m:
        return None
    return tuple(int(x) for x in m.groups())


def parse_deck_rows(page: str, event_id: str) -> dict[str, dict]:
    """Parse exact-variant deck rows from a day-filtered event metagame page."""
    out: dict[str, dict] = {}
    for tr in re.finditer(r"<tr[^>]*>([\s\S]*?)</tr>", page, re.I):
        body = tr.group(1)
        link = re.search(
            rf'href=["\']/{re.escape(event_id)}/decks/([^"\'?/]+)["\'][^>]*>([\s\S]*?)</a>',
            body,
            re.I,
        )
        if not link:
            continue
        cells = cells_from_row(body)
        entries = first_int(cells)
        if entries is None:
            continue
        pcts = percentages(cells)
        record = parse_record(cells)
        wins = losses = ties = None
        if record:
            wins, losses, ties = record
        out[link.group(1)] = {
            "name": clean(link.group(2)),
            "slug": link.group(1),
            "entries": entries,
            "share_pct": pcts[0] if pcts else None,
            "points_rate_pct": pcts[-1] if len(pcts) >= 2 else None,
            "wins": wins,
            "losses": losses,
            "ties": ties,
        }
    return out


def parse_standings(page: str, event_id: str) -> list[dict]:
    """Return rank/deck only; never persist player identity."""
    rows = []
    for tr in re.finditer(r"<tr[^>]*>([\s\S]*?)</tr>", page, re.I):
        body = tr.group(1)
        cells = cells_from_row(body)
        if not cells:
            continue
        rank = None
        for cell in cells[:2]:
            m = re.match(r"^#?\s*(\d+)\b", cell)
            if m:
                rank = int(m.group(1))
                break
        if rank is None:
            continue
        deck_link = re.search(
            rf'href=["\']/{re.escape(event_id)}/decks/([^"\'?/]+)(?:/[^"\']*)?["\']',
            body,
            re.I,
        )
        if not deck_link:
            continue
        record = parse_record(cells)
        points = None
        # Points normally precede the W-L-T record and are the last small integer cell.
        for cell in cells:
            raw = re.sub(r"[, ]", "", cell)
            if raw.isdigit():
                value = int(raw)
                if value != rank:
                    points = value
        rows.append({
            "rank": rank,
            "slug": deck_link.group(1),
            "points": points,
            "record": list(record) if record else None,
        })
    # Keep one row per rank if markup contains duplicate links.
    by_rank = {}
    for row in rows:
        by_rank.setdefault(row["rank"], row)
    return [by_rank[k] for k in sorted(by_rank)]


def counts_at_thresholds(standings: list[dict], thresholds=(8, 16, 32)) -> dict[str, dict[str, int]]:
    result = {f"top{n}": {} for n in thresholds}
    for row in standings:
        slug = row["slug"]
        for n in thresholds:
            if row["rank"] <= n:
                bucket = result[f"top{n}"]
                bucket[slug] = bucket.get(slug, 0) + 1
    return result


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    event_out = OUT / "events"
    event_out.mkdir(parents=True, exist_ok=True)
    failures = []
    coverage = []

    for i, meta in enumerate(index, start=1):
        event_id = meta["id"]
        archived = json.loads((DAY1_DIR / f"{event_id}.json").read_text(encoding="utf-8"))
        archived_by_slug = {d["slug"]: d for d in archived.get("decks", [])}
        print(f"[{i}/{len(index)}] {event_id} {meta['name']}", flush=True)
        try:
            day1_page = get(f"{BASE}/{event_id}/decks?day=1")
            time.sleep(0.12)
            day2_page = get(f"{BASE}/{event_id}/decks?day=2")
            time.sleep(0.12)
            standings_page = get(f"{BASE}/{event_id}/standings")
            time.sleep(0.12)

            day1 = parse_deck_rows(day1_page, event_id)
            day2 = parse_deck_rows(day2_page, event_id)
            standings = parse_standings(standings_page, event_id)
            finish_counts = counts_at_thresholds(standings)

            # Join to the already-audited Day-1 slug universe. Live-source rows that no
            # longer align exactly are retained in diagnostics rather than silently remapped.
            joined = {}
            for slug, old in archived_by_slug.items():
                d1 = day1.get(slug)
                d2 = day2.get(slug)
                joined[slug] = {
                    "name": old.get("name"),
                    "day1_entries_archived": old.get("entries"),
                    "day1_share_pct_archived": old.get("share"),
                    "day1_live": d1,
                    "day2_live": d2,
                    "top8": finish_counts["top8"].get(slug, 0),
                    "top16": finish_counts["top16"].get(slug, 0),
                    "top32": finish_counts["top32"].get(slug, 0),
                    "winner": 1 if finish_counts["top8"].get(slug, 0) and any(
                        r["rank"] == 1 and r["slug"] == slug for r in standings
                    ) else 0,
                }

            archived_named = {s for s in archived_by_slug if s != "other"}
            live_named = {s for s in day1 if s != "other"}
            top32_rows = [r for r in standings if r["rank"] <= 32]
            event = {
                "id": event_id,
                "name": meta["name"],
                "start_date": meta.get("start_date"),
                "end_date": meta.get("end_date"),
                "players": meta.get("players"),
                "source_urls": {
                    "day1": f"{BASE}/{event_id}/decks?day=1",
                    "day2": f"{BASE}/{event_id}/decks?day=2",
                    "standings": f"{BASE}/{event_id}/standings",
                },
                "day1_total_live": sum(r["entries"] for r in day1.values()),
                "day2_total_live": sum(r["entries"] for r in day2.values()),
                "standings_rows_with_deck": len(standings),
                "top32_rows_with_deck": len(top32_rows),
                "day1_exact_slug_overlap_count": len(archived_named & live_named),
                "day1_archived_named_slug_count": len(archived_named),
                "day1_live_named_slug_count": len(live_named),
                "archived_only_slugs": sorted(archived_named - live_named),
                "live_only_slugs": sorted(live_named - archived_named),
                "archetypes": joined,
            }
            write_json(event_out / f"{event_id}.json", event)
            coverage.append({
                "id": event_id,
                "day1_archived_entries": archived.get("deck_entries_sum"),
                "day1_live_entries": event["day1_total_live"],
                "day2_live_entries": event["day2_total_live"],
                "standings_rows_with_deck": len(standings),
                "top32_rows_with_deck": len(top32_rows),
                "archived_named_slugs": len(archived_named),
                "live_named_slugs": len(live_named),
                "slug_overlap": len(archived_named & live_named),
                "archived_only": len(archived_named - live_named),
                "live_only": len(live_named - archived_named),
            })
        except Exception as exc:
            failures.append({"id": event_id, "name": meta.get("name"), "error": str(exc)})
            print(f"  FAILED: {exc}", flush=True)

    manifest = {
        "collector_version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": BASE,
        "base_day1_archive": "data/raw/irl/labs",
        "events_requested": len(index),
        "events_collected": len(coverage),
        "failures": failures,
        "coverage": coverage,
        "notes": [
            "Masters events inherited from the audited Day-1 archive; no new event selection.",
            "Exact variant slugs are joined to the archived Day-1 slug universe; mismatches are diagnostics, not remapped.",
            "Day-1 points_rate_pct is the source site's displayed WR metric for the Day-1 filtered view.",
            "Day-2 counts are used to derive conversion/representation lift without relying on the site's combine-sensitive conversion view.",
            "Standings retain rank/deck only; player identity is discarded.",
        ],
    }
    write_json(OUT / "manifest.json", manifest)
    if failures:
        raise RuntimeError(f"Performance collection had {len(failures)} event failures; inspect manifest")


if __name__ == "__main__":
    main()
