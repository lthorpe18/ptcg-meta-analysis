#!/usr/bin/env python3
"""Resumable historical Online backfill using a cached discovery index.

This wrapper deliberately keeps the existing validated collector unchanged.
It performs either:
- one discovery pass for the whole requested history; or
- one bounded chunk using the cached discovery index.

Each successful chunk writes a manifest with complete=true. GitHub Actions can
therefore commit each chunk independently and safely resume after cancellation.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fetch_online import (
    BASE_URL,
    FetchConfig,
    audit_event,
    base_audit_row,
    discover_index,
    load_json,
    parse_date,
    tournament_date,
    write_json,
)


def filter_items(items: list[dict[str, Any]], start: date, end: date) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        d = tournament_date(item)
        if d is not None and start <= d <= end:
            filtered.append(item)
    return filtered


def discovery(args: argparse.Namespace) -> int:
    out_dir = args.root / "discovery"
    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "tournament-index.json"
    manifest_path = out_dir / "manifest.json"

    existing_manifest = load_json(manifest_path)
    if (
        index_path.exists()
        and isinstance(existing_manifest, dict)
        and existing_manifest.get("complete") is True
        and existing_manifest.get("start_date") == args.start_date.isoformat()
        and existing_manifest.get("end_date") == args.end_date.isoformat()
    ):
        print("Discovery already complete; reusing cached tournament index.")
        return 0

    config = FetchConfig(
        start_date=args.start_date,
        end_date=args.end_date,
        min_players=args.min_players,
        out_dir=out_dir,
        page_size=args.page_size,
        pause=args.pause,
        max_pages=args.max_pages,
    )
    items = discover_index(config)
    write_json(index_path, items)
    write_json(
        manifest_path,
        {
            "complete": True,
            "kind": "discovery",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": BASE_URL,
            "start_date": args.start_date.isoformat(),
            "end_date": args.end_date.isoformat(),
            "discovered_index_rows": len(items),
            "page_size": args.page_size,
            "max_pages": args.max_pages,
        },
    )
    print(f"Discovery complete: {len(items)} in-range Standard tournament rows.")
    return 0


def chunk(args: argparse.Namespace) -> int:
    source_index = args.root / "discovery" / "tournament-index.json"
    all_items = load_json(source_index)
    if not isinstance(all_items, list):
        raise RuntimeError(f"Missing or invalid discovery index: {source_index}")

    chunk_name = f"{args.chunk_start.isoformat()}_{args.chunk_end.isoformat()}"
    out_dir = args.root / "chunks" / chunk_name
    manifest_path = out_dir / "manifest.json"
    existing_manifest = load_json(manifest_path)
    if (
        isinstance(existing_manifest, dict)
        and existing_manifest.get("complete") is True
        and existing_manifest.get("start_date") == args.chunk_start.isoformat()
        and existing_manifest.get("end_date") == args.chunk_end.isoformat()
    ):
        print(f"Chunk {chunk_name} already complete; skipping.")
        return 0

    items = filter_items(all_items, args.chunk_start, args.chunk_end)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "tournament-index.json", items)

    config = FetchConfig(
        start_date=args.chunk_start,
        end_date=args.chunk_end,
        min_players=args.min_players,
        out_dir=out_dir,
        page_size=args.page_size,
        pause=args.pause,
        max_pages=args.max_pages,
    )

    counters = {"details_fetched": 0, "standings_fetched": 0, "standings_compacted": 0}
    audit_rows: list[dict[str, Any]] = []

    for i, item in enumerate(sorted(items, key=lambda x: str(x.get("date") or "")), start=1):
        print(f"[{i}/{len(items)}] {item.get('id')} — {item.get('name')}", flush=True)
        try:
            audit_rows.append(audit_event(item, config, counters))
        except Exception as exc:
            print(f"ERROR: {item.get('id')}: {exc!r}", flush=True)
            row = base_audit_row(item)
            row.update({
                "eligible_first_pass": False,
                "rejection_reasons": ["fetch_error"],
                "fetch_error": repr(exc),
            })
            audit_rows.append(row)

    eligible = [row for row in audit_rows if row.get("eligible_first_pass")]
    write_json(out_dir / "index.json", audit_rows)
    write_json(
        manifest_path,
        {
            "complete": True,
            "kind": "chunk",
            "collector_version": "0.3",
            "standings_storage": "compact_without_decklists_or_player_handles",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": BASE_URL,
            "start_date": args.chunk_start.isoformat(),
            "end_date": args.chunk_end.isoformat(),
            "min_players": args.min_players,
            "discovered_index_rows": len(items),
            "details_fetched_this_run": counters["details_fetched"],
            "standings_fetched_this_run": counters["standings_fetched"],
            "standings_compacted_this_run": counters["standings_compacted"],
            "eligible_first_pass": len(eligible),
            "ineligible_or_failed": len(audit_rows) - len(eligible),
        },
    )
    print(
        f"Chunk complete: {chunk_name}; {len(eligible)} eligible of {len(audit_rows)} audited.",
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Resumable chunked Online historical backfill")
    parser.add_argument("--mode", choices=["discover", "chunk"], required=True)
    parser.add_argument("--root", type=Path, default=Path("data/raw/online/backfill"))
    parser.add_argument("--start-date", type=parse_date, default=parse_date("2024-09-01"))
    parser.add_argument("--end-date", type=parse_date, default=datetime.now(timezone.utc).date())
    parser.add_argument("--chunk-start", type=parse_date)
    parser.add_argument("--chunk-end", type=parse_date)
    parser.add_argument("--min-players", type=int, default=50)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--pause", type=float, default=0.35)
    parser.add_argument("--max-pages", type=int, default=100)
    args = parser.parse_args()

    if args.mode == "discover":
        if args.start_date > args.end_date:
            parser.error("--start-date must not be after --end-date")
        return discovery(args)

    if args.chunk_start is None or args.chunk_end is None:
        parser.error("chunk mode requires --chunk-start and --chunk-end")
    if args.chunk_start > args.chunk_end:
        parser.error("--chunk-start must not be after --chunk-end")
    return chunk(args)


if __name__ == "__main__":
    raise SystemExit(main())
