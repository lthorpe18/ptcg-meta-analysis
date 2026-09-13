#!/usr/bin/env python3
"""Collect historical Standard PTCGL tournaments from Limitless for research.

The collector deliberately separates discovery from eligibility:
- all in-range PTCG Standard index rows are preserved in one source file;
- events below the player threshold are audited without extra API calls;
- for threshold-passing events, details are fetched first;
- standings are fetched only for Online PTCGL events with usable decklists
  and no custom bans/special rules.

This keeps the raw archive reproducible without filling the repository with
large standings payloads for obviously ineligible events.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

BASE_URL = "https://play.limitlesstcg.com/api"
DEFAULT_START = "2024-09-01"
DEFAULT_MIN_PLAYERS = 50
USER_AGENT = "ptcg-meta-analysis/0.2 (+historical metagame research)"


@dataclass
class FetchConfig:
    start_date: date
    end_date: date
    min_players: int
    out_dir: Path
    page_size: int
    pause: float
    max_pages: int


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date {value!r}; expected YYYY-MM-DD"
        ) from exc


def request_json(
    path: str,
    params: dict[str, Any] | None = None,
    *,
    retries: int = 4,
    pause: float = 0.5,
) -> Any:
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 or 500 <= exc.code < 600:
                wait = pause * (2**attempt)
                print(f"HTTP {exc.code}; retrying in {wait:.1f}s: {url}",
                      file=sys.stderr)
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise
            wait = pause * (2**attempt)
            print(f"{exc!r}; retrying in {wait:.1f}s: {url}",
                  file=sys.stderr)
            time.sleep(wait)

    raise RuntimeError(f"Failed to fetch {url}")


def tournament_date(item: dict[str, Any]) -> date | None:
    raw = item.get("date")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(str(raw)[:10])
        except ValueError:
            return None


def player_count(item: dict[str, Any]) -> int:
    try:
        return int(item.get("players") or 0)
    except (TypeError, ValueError):
        return 0


def normalise_platform(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def platform_is_ptcgl(details: dict[str, Any]) -> bool:
    platform = normalise_platform(details.get("platform"))
    return platform in {"ptcgl", "pokemontcglive"} or (
        "pokemon" in platform and "tcg" in platform and "live" in platform
    )


def detail_rejection_reasons(details: dict[str, Any]) -> list[str]:
    reasons: list[str] = []

    if details.get("isOnline") is not True:
        reasons.append("not_online")

    if not platform_is_ptcgl(details):
        reasons.append("not_ptcgl_platform")

    if bool(details.get("bannedCards")) or bool(details.get("specialRules")):
        reasons.append("custom_bans_or_special_rules")

    if details.get("decklists") is False:
        reasons.append("decklists_disabled")

    return reasons


def classification_stats(standings: Any) -> dict[str, Any]:
    if not isinstance(standings, list):
        return {
            "standing_rows": 0,
            "classified_rows": 0,
            "classification_coverage": None,
        }

    total = len(standings)
    classified = sum(
        1
        for row in standings
        if isinstance(row, dict)
        and isinstance(row.get("deck"), dict)
        and (row["deck"].get("name") or row["deck"].get("id"))
    )
    return {
        "standing_rows": total,
        "classified_rows": classified,
        "classification_coverage": (classified / total) if total else None,
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def discover_index(config: FetchConfig) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    for page in range(1, config.max_pages + 1):
        print(f"Index page {page}...")
        payload = request_json(
            "/tournaments",
            {
                "game": "PTCG",
                "format": "STANDARD",
                "limit": config.page_size,
                "page": page,
            },
            pause=config.pause,
        )

        if not isinstance(payload, list) or not payload:
            break

        dates = [
            tournament_date(row)
            for row in payload
            if isinstance(row, dict)
        ]
        dates = [d for d in dates if d is not None]

        for item in payload:
            if not isinstance(item, dict):
                continue
            d = tournament_date(item)
            if d is not None and config.start_date <= d <= config.end_date:
                found.append(item)

        if dates and min(dates) < config.start_date:
            break
        time.sleep(config.pause)
    else:
        print(
            f"WARNING: reached max-pages={config.max_pages}; "
            "older in-range tournaments may remain.",
            file=sys.stderr,
        )

    deduped: dict[str, dict[str, Any]] = {}
    for item in found:
        tid = str(item.get("id") or "")
        if tid and tid not in deduped:
            deduped[tid] = item
    return list(deduped.values())


def base_audit_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""),
        "name": item.get("name"),
        "date": item.get("date"),
        "players": item.get("players"),
        "game": item.get("game"),
        "format": item.get("format"),
    }


def audit_event(
    item: dict[str, Any],
    config: FetchConfig,
    counters: dict[str, int],
) -> dict[str, Any]:
    row = base_audit_row(item)
    players = player_count(item)

    if players < config.min_players:
        row.update({
            "eligible_first_pass": False,
            "rejection_reasons": [f"players_below_{config.min_players}"],
            "details_fetched": False,
            "standings_fetched": False,
            "classification_coverage": None,
            "classified_rows": 0,
            "standing_rows": 0,
        })
        return row

    tid = row["id"]
    event_dir = config.out_dir / tid
    event_dir.mkdir(parents=True, exist_ok=True)
    write_json(event_dir / "tournament.json", item)

    details_path = event_dir / "details.json"
    details = load_json(details_path)
    if details is None:
        details = request_json(f"/tournaments/{tid}/details", pause=config.pause)
        write_json(details_path, details)
        counters["details_fetched"] += 1
        time.sleep(config.pause)

    if not isinstance(details, dict):
        row.update({
            "eligible_first_pass": False,
            "rejection_reasons": ["invalid_details_payload"],
            "details_fetched": True,
            "standings_fetched": False,
            "classification_coverage": None,
            "classified_rows": 0,
            "standing_rows": 0,
        })
        return row

    row.update({
        "platform": details.get("platform"),
        "isOnline": details.get("isOnline"),
        "decklists": details.get("decklists"),
        "has_banned_cards": bool(details.get("bannedCards")),
        "has_special_rules": bool(details.get("specialRules")),
        "details_fetched": True,
    })

    reasons = detail_rejection_reasons(details)
    if reasons:
        row.update({
            "eligible_first_pass": False,
            "rejection_reasons": reasons,
            "standings_fetched": False,
            "classification_coverage": None,
            "classified_rows": 0,
            "standing_rows": 0,
        })
        return row

    standings_path = event_dir / "standings.json"
    standings = load_json(standings_path)
    if standings is None:
        standings = request_json(f"/tournaments/{tid}/standings", pause=config.pause)
        write_json(standings_path, standings)
        counters["standings_fetched"] += 1
        time.sleep(config.pause)

    stats = classification_stats(standings)
    reasons = [] if isinstance(standings, list) and standings else ["no_standings"]

    row.update({
        **stats,
        "standings_fetched": True,
        "eligible_first_pass": not reasons,
        "rejection_reasons": reasons,
    })
    return row


def main() -> int:
    today = datetime.now(timezone.utc).date()

    parser = argparse.ArgumentParser(
        description="Fetch historical Standard PTCGL tournament data from Limitless."
    )
    parser.add_argument("--start-date", type=parse_date,
                        default=parse_date(DEFAULT_START))
    parser.add_argument("--end-date", type=parse_date, default=today)
    parser.add_argument("--min-players", type=int, default=DEFAULT_MIN_PLAYERS)
    parser.add_argument("--out-dir", type=Path, default=Path("data/raw/online"))
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--pause", type=float, default=0.35)
    parser.add_argument("--max-pages", type=int, default=100)
    args = parser.parse_args()

    if args.start_date > args.end_date:
        parser.error("--start-date must not be after --end-date")
    if args.min_players < 1:
        parser.error("--min-players must be >= 1")

    config = FetchConfig(
        start_date=args.start_date,
        end_date=args.end_date,
        min_players=args.min_players,
        out_dir=args.out_dir,
        page_size=args.page_size,
        pause=args.pause,
        max_pages=args.max_pages,
    )
    config.out_dir.mkdir(parents=True, exist_ok=True)

    items = discover_index(config)
    write_json(config.out_dir / "tournament-index.json", items)
    print(f"Discovered {len(items)} in-range PTCG Standard tournament rows.")

    counters = {"details_fetched": 0, "standings_fetched": 0}
    audit_rows: list[dict[str, Any]] = []

    for i, item in enumerate(
        sorted(items, key=lambda x: str(x.get("date") or "")),
        start=1,
    ):
        print(f"[{i}/{len(items)}] {item.get('id')} — {item.get('name')}")
        try:
            audit_rows.append(audit_event(item, config, counters))
        except Exception as exc:
            print(f"ERROR: {item.get('id')}: {exc!r}", file=sys.stderr)
            row = base_audit_row(item)
            row.update({
                "eligible_first_pass": False,
                "rejection_reasons": ["fetch_error"],
                "fetch_error": repr(exc),
            })
            audit_rows.append(row)

    eligible = [row for row in audit_rows if row.get("eligible_first_pass")]
    write_json(config.out_dir / "index.json", audit_rows)
    write_json(
        config.out_dir / "manifest.json",
        {
            "collector_version": "0.2",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": BASE_URL,
            "start_date": config.start_date.isoformat(),
            "end_date": config.end_date.isoformat(),
            "min_players": config.min_players,
            "discovered_index_rows": len(items),
            "details_fetched_this_run": counters["details_fetched"],
            "standings_fetched_this_run": counters["standings_fetched"],
            "eligible_first_pass": len(eligible),
            "ineligible_or_failed": len(audit_rows) - len(eligible),
            "note": (
                "First-pass eligibility is not final research inclusion. "
                "Classification coverage, historical legality and archetype "
                "taxonomy are audited later."
            ),
        },
    )

    print(
        f"Done: {len(eligible)} first-pass eligible of {len(audit_rows)} audited; "
        f"{counters['details_fetched']} details and "
        f"{counters['standings_fetched']} standings fetched."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
