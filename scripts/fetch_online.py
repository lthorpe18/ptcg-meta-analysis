#!/usr/bin/env python3
"""Fetch historical Pokémon TCG Standard Online tournaments from Limitless.

Purpose:
- Build an auditable raw research dataset.
- Preserve tournament index, details and standings responses.
- Apply only objective first-pass eligibility rules.
- Record rejection reasons instead of silently discarding events.

Public API base:
    https://play.limitlesstcg.com/api

No API key is required for the tournament endpoints used here.
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
USER_AGENT = "ptcg-meta-analysis/0.1 (+historical metagame research)"


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


def request_json(path: str, params: dict[str, Any] | None = None,
                 retries: int = 4, pause: float = 0.5) -> Any:
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    headers = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 or 500 <= exc.code < 600:
                wait = pause * (2 ** attempt)
                print(f"HTTP {exc.code} for {url}; retrying in {wait:.1f}s",
                      file=sys.stderr)
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise
            wait = pause * (2 ** attempt)
            print(f"{exc!r} for {url}; retrying in {wait:.1f}s",
                  file=sys.stderr)
            time.sleep(wait)

    raise RuntimeError(f"Failed to fetch {url}")


def tournament_date(item: dict[str, Any]) -> date | None:
    raw = item.get("date")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt.date()
    except ValueError:
        try:
            return date.fromisoformat(str(raw)[:10])
        except ValueError:
            return None


def normalise_platform(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def platform_is_ptcgl(details: dict[str, Any]) -> bool:
    platform = normalise_platform(details.get("platform"))
    return platform in {
        "ptcgl",
        "pokemontcglive",
        "pokemontcgonlineclientlive",
    } or ("pokemon" in platform and "tcg" in platform and "live" in platform)


def has_custom_rules(details: dict[str, Any]) -> bool:
    banned = details.get("bannedCards")
    special = details.get("specialRules")
    return bool(banned) or bool(special)


def first_pass_reasons(index_item: dict[str, Any],
                       details: dict[str, Any],
                       standings: Any,
                       min_players: int) -> list[str]:
    reasons: list[str] = []

    if str(index_item.get("game", "")).upper() != "PTCG":
        reasons.append("not_ptcg")

    if str(index_item.get("format", "")).upper() != "STANDARD":
        reasons.append("not_standard")

    try:
        players = int(index_item.get("players") or 0)
    except (TypeError, ValueError):
        players = 0
    if players < min_players:
        reasons.append(f"players_below_{min_players}")

    if details.get("isOnline") is not True:
        reasons.append("not_online")

    if not platform_is_ptcgl(details):
        reasons.append("not_ptcgl_platform")

    if has_custom_rules(details):
        reasons.append("custom_bans_or_special_rules")

    if details.get("decklists") is False:
        reasons.append("decklists_disabled")

    if not isinstance(standings, list) or not standings:
        reasons.append("no_standings")

    return reasons


def classification_stats(standings: Any) -> dict[str, Any]:
    if not isinstance(standings, list):
        return {
            "standing_rows": 0,
            "classified_rows": 0,
            "classification_coverage": None,
        }

    total = len(standings)
    classified = 0
    for row in standings:
        deck = row.get("deck") if isinstance(row, dict) else None
        if isinstance(deck, dict) and (deck.get("name") or deck.get("id")):
            classified += 1

    coverage = classified / total if total else None
    return {
        "standing_rows": total,
        "classified_rows": classified,
        "classification_coverage": coverage,
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_existing_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def discover_index(config: FetchConfig) -> list[dict[str, Any]]:
    """Walk newest-to-oldest Standard PTCG tournament pages."""
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

        page_dates = [tournament_date(x) for x in payload if isinstance(x, dict)]
        page_dates = [d for d in page_dates if d is not None]

        for item in payload:
            if not isinstance(item, dict):
                continue
            d = tournament_date(item)
            if d is None:
                continue
            if config.start_date <= d <= config.end_date:
                found.append(item)

        if page_dates and min(page_dates) < config.start_date:
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


def fetch_one(item: dict[str, Any], config: FetchConfig) -> dict[str, Any]:
    tid = str(item["id"])
    event_dir = config.out_dir / tid
    event_dir.mkdir(parents=True, exist_ok=True)

    write_json(event_dir / "tournament.json", item)

    details_path = event_dir / "details.json"
    standings_path = event_dir / "standings.json"

    details = load_existing_json(details_path, None)
    if details is None:
        details = request_json(f"/tournaments/{tid}/details", pause=config.pause)
        write_json(details_path, details)
        time.sleep(config.pause)

    standings = load_existing_json(standings_path, None)
    if standings is None:
        standings = request_json(f"/tournaments/{tid}/standings", pause=config.pause)
        write_json(standings_path, standings)
        time.sleep(config.pause)

    reasons = first_pass_reasons(item, details, standings, config.min_players)
    stats = classification_stats(standings)

    return {
        "id": tid,
        "name": item.get("name"),
        "date": item.get("date"),
        "players": item.get("players"),
        "game": item.get("game"),
        "format": item.get("format"),
        "platform": details.get("platform") if isinstance(details, dict) else None,
        "isOnline": details.get("isOnline") if isinstance(details, dict) else None,
        "decklists": details.get("decklists") if isinstance(details, dict) else None,
        "has_banned_cards": bool(details.get("bannedCards")) if isinstance(details, dict) else None,
        "has_special_rules": bool(details.get("specialRules")) if isinstance(details, dict) else None,
        **stats,
        "eligible_first_pass": not reasons,
        "rejection_reasons": reasons,
    }


def main() -> int:
    today = datetime.now(timezone.utc).date()

    parser = argparse.ArgumentParser(
        description="Fetch historical Standard PTCGL tournament data from Limitless."
    )
    parser.add_argument("--start-date", type=parse_date,
                        default=parse_date(DEFAULT_START))
    parser.add_argument("--end-date", type=parse_date, default=today)
    parser.add_argument("--min-players", type=int, default=DEFAULT_MIN_PLAYERS)
    parser.add_argument("--out-dir", type=Path,
                        default=Path("data/raw/online"))
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--pause", type=float, default=0.35,
                        help="Polite delay between API calls in seconds.")
    parser.add_argument("--max-pages", type=int, default=100,
                        help="Safety cap for tournament-index pagination.")
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
    print(f"Discovered {len(items)} in-range PTCG Standard tournament index rows.")

    audit_rows: list[dict[str, Any]] = []
    for i, item in enumerate(
        sorted(items, key=lambda x: str(x.get("date") or "")), start=1
    ):
        tid = item.get("id")
        print(f"[{i}/{len(items)}] {tid} — {item.get('name')}")
        try:
            audit_rows.append(fetch_one(item, config))
        except Exception as exc:
            print(f"ERROR fetching {tid}: {exc!r}", file=sys.stderr)
            audit_rows.append({
                "id": str(tid or ""),
                "name": item.get("name"),
                "date": item.get("date"),
                "players": item.get("players"),
                "game": item.get("game"),
                "format": item.get("format"),
                "eligible_first_pass": False,
                "rejection_reasons": ["fetch_error"],
                "fetch_error": repr(exc),
            })

    eligible = [row for row in audit_rows if row.get("eligible_first_pass")]

    write_json(config.out_dir / "index.json", audit_rows)
    write_json(
        config.out_dir / "manifest.json",
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": BASE_URL,
            "start_date": config.start_date.isoformat(),
            "end_date": config.end_date.isoformat(),
            "min_players": config.min_players,
            "discovered_index_rows": len(items),
            "eligible_first_pass": len(eligible),
            "ineligible_or_failed": len(audit_rows) - len(eligible),
            "note": (
                "First-pass eligibility is not final research inclusion. "
                "Classification coverage, historical format legality and "
                "archetype taxonomy are audited later."
            ),
        },
    )

    print(
        f"Done: {len(eligible)} first-pass eligible of {len(audit_rows)} audited."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
