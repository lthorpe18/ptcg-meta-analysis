#!/usr/bin/env python3
"""Analyse whether Online meta evidence is structurally more diffuse than prior IRL fields.

The analysis uses the same frozen historical windows and named-archetype normalisation
as the baseline field-prediction research. It asks:
1) how often prior-IRL top decks have lower share in post-major Online evidence;
2) whether Online top-N concentration is systematically lower than IRL;
3) how much of that apparent Online tail survives into the next observed IRL cohort.

No forecast rule is changed by this analysis.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOWS_PATH = ROOT / "data" / "processed" / "prediction-windows" / "windows.json"
ONLINE_TAGS_PATH = ROOT / "data" / "processed" / "format-tags" / "online-events.json"
IRL_TAGS_PATH = ROOT / "data" / "processed" / "format-tags" / "irl-events.json"
CURRENT_PATH = ROOT / "data" / "processed" / "current-archetype-prediction.json"

OUT_DIR = ROOT / "data" / "processed" / "online-spread-tail"
RESULTS_DIR = ROOT / "results" / "online-spread-tail"

TOP_NS = (1, 3, 5, 10, 20)
RECENT_START = date(2025, 8, 28)
RECENT_END = date(2026, 8, 28)


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(value: str) -> date:
    return date.fromisoformat(str(value)[:10])


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def end_of_iso_week(value: date) -> date:
    return value + timedelta(days=6 - value.weekday())


def clean_key(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    return text if text else "name:" + fallback.strip().lower()


def ignored(name: object, key: object = None) -> bool:
    n = str(name or "").strip().lower()
    k = str(key or "").strip().lower()
    return n in {"", "other", "unknown", "unclassified"} or k in {"other", "unknown", "unclassified"}


def online_decks() -> tuple[dict[str, Counter], dict[str, str]]:
    counts: dict[str, Counter] = {}
    names: dict[str, str] = {}
    for path in ROOT.glob("data/raw/online/backfill/chunks/*/*/standings.json"):
        event_id = path.parent.name
        event_counts: Counter = Counter()
        for row in load_json(path, []) or []:
            deck = row.get("deck") if isinstance(row, dict) else None
            if not isinstance(deck, dict):
                continue
            name = str(deck.get("name") or deck.get("id") or "").strip()
            key = clean_key(deck.get("id"), name)
            if ignored(name, key):
                continue
            event_counts[key] += 1
            names.setdefault(key, name or key)
        counts[event_id] = event_counts
    return counts, names


def irl_decks() -> tuple[dict[str, Counter], dict[str, str]]:
    counts: dict[str, Counter] = {}
    names: dict[str, str] = {}
    for path in sorted((ROOT / "data/raw/irl/labs/events").glob("*.json")):
        raw = load_json(path, {}) or {}
        event_id = str(raw.get("id") or path.stem)
        event_counts: Counter = Counter()
        for deck in raw.get("decks") or []:
            name = str(deck.get("name") or deck.get("slug") or "").strip()
            key = clean_key(deck.get("slug"), name)
            if ignored(name, key):
                continue
            event_counts[key] += int(deck.get("entries") or 0)
            names.setdefault(key, name or key)
        counts[event_id] = event_counts
    return counts, names


def aggregate(ids: list[str], source: dict[str, Counter]) -> Counter:
    out: Counter = Counter()
    for event_id in ids:
        out.update(source.get(str(event_id), Counter()))
    return out


def normalise(counts: Counter) -> dict[str, float]:
    total = sum(max(0.0, float(v)) for v in counts.values())
    if not total:
        return {}
    return {k: max(0.0, float(v)) / total for k, v in counts.items() if v > 0}


def top_keys(dist: dict[str, float], n: int) -> list[str]:
    return [k for k, _ in sorted(dist.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]


def own_top_share(dist: dict[str, float], n: int) -> float:
    return sum(dist.get(k, 0.0) for k in top_keys(dist, n))


def share_on_keys(dist: dict[str, float], keys: list[str]) -> float:
    return sum(dist.get(k, 0.0) for k in keys)


def mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    denom = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    if denom == 0:
        return None
    return sum(x * y for x, y in zip(dx, dy)) / denom


def latest_prior_ids(window: dict, cohorts: list[dict]) -> tuple[dict | None, list[str]]:
    prior_same = set(str(i) for i in window.get("prior_irl_same_format_ids") or [])
    candidates = []
    for cohort in cohorts:
        same_ids = [str(i) for i in cohort.get("event_ids") or [] if str(i) in prior_same]
        if same_ids:
            candidates.append((cohort["end_date"], cohort["cohort_id"], cohort, same_ids))
    if not candidates:
        return None, []
    _, _, cohort, same_ids = max(candidates, key=lambda item: (item[0], item[1]))
    return cohort, same_ids


def historical_rows() -> tuple[list[dict], dict[str, str]]:
    pack = load_json(WINDOWS_PATH, {}) or {}
    windows = pack.get("windows") or []
    cohorts = pack.get("cohorts") or []
    online_meta = {str(e["id"]): e for e in (load_json(ONLINE_TAGS_PATH, []) or [])}
    irl_meta = {str(e["id"]): e for e in (load_json(IRL_TAGS_PATH, []) or [])}
    online_counts, online_names = online_decks()
    irl_counts, irl_names = irl_decks()
    names = {**online_names, **irl_names}

    eligible = [
        w for w in windows
        if w.get("window_class") == "settled" and bool(w.get("target_eligible_ge_95"))
    ]
    by_cohort: dict[str, list[dict]] = defaultdict(list)
    for w in eligible:
        by_cohort[str(w["cohort_id"])].append(w)

    rows: list[dict] = []
    for cohort_id, group in sorted(by_cohort.items()):
        w = sorted(group, key=lambda x: str(x["target_id"]))[0]
        prior_cohort, prior_ids = latest_prior_ids(w, cohorts)
        if not prior_ids:
            continue

        online_all_ids = [str(i) for i in w.get("online_primary_ids") or []]
        latest_end = max(parse_date(irl_meta[i]["end_date"]) for i in prior_ids)
        major_final_day = end_of_iso_week(latest_end)
        online_since_ids = [
            event_id for event_id in online_all_ids
            if event_id in online_meta and parse_dt(online_meta[event_id]["start_at"]).date() > major_final_day
        ]
        if not online_since_ids:
            continue

        prior = normalise(aggregate(prior_ids, irl_counts))
        online = normalise(aggregate(online_since_ids, online_counts))
        target_ids = [str(x["target_id"]) for x in group]
        actual = normalise(aggregate(target_ids, irl_counts))
        if not prior or not online or not actual:
            continue

        top_metrics = {}
        deck_rows = {}
        for n in TOP_NS:
            keys = top_keys(prior, n)
            obs = []
            for key in keys:
                p = prior.get(key, 0.0)
                o = online.get(key, 0.0)
                a = actual.get(key, 0.0)
                obs.append({
                    "key": key,
                    "name": names.get(key, key),
                    "prior_irl_pct": p * 100.0,
                    "online_since_pct": o * 100.0,
                    "next_irl_pct": a * 100.0,
                    "online_delta_pp": (o - p) * 100.0,
                    "next_irl_delta_pp": (a - p) * 100.0,
                    "online_lower_than_prior": o < p,
                    "next_irl_lower_than_prior": a < p,
                })
            deck_rows[str(n)] = obs
            negative = sum(1 for x in obs if x["online_lower_than_prior"])
            top_metrics[str(n)] = {
                "prior_irl_own_top_share_pct": own_top_share(prior, n) * 100.0,
                "online_own_top_share_pct": own_top_share(online, n) * 100.0,
                "next_irl_own_top_share_pct": own_top_share(actual, n) * 100.0,
                "prior_top_keys_online_share_pct": share_on_keys(online, keys) * 100.0,
                "prior_top_keys_next_irl_share_pct": share_on_keys(actual, keys) * 100.0,
                "online_tail_vs_prior_top_pct": (1.0 - share_on_keys(online, keys)) * 100.0,
                "next_irl_tail_vs_prior_top_pct": (1.0 - share_on_keys(actual, keys)) * 100.0,
                "top_decks_lower_online_count": negative,
                "top_decks_lower_online_fraction": negative / len(obs) if obs else None,
            }

        prior_keys = set(prior)
        online_new_keys = set(online) - prior_keys
        actual_new_keys = set(actual) - prior_keys

        rows.append({
            "cohort_id": cohort_id,
            "target_start_date": min(str(x["target_start_date"]) for x in group),
            "target_names": [str(x["target_name"]) for x in sorted(group, key=lambda x: str(x["target_id"]))],
            "target_ids": target_ids,
            "target_format": str(w["target_format"]),
            "prior_cohort_id": prior_cohort["cohort_id"] if prior_cohort else None,
            "prior_ids": prior_ids,
            "days_since_major": max(0, (parse_date(w["cohort_start_date"]) - major_final_day).days),
            "online_event_count": len(online_since_ids),
            "prior_named_archetype_count": len(prior),
            "online_named_archetype_count": len(online),
            "next_irl_named_archetype_count": len(actual),
            "online_new_vs_prior_share_pct": sum(online[k] for k in online_new_keys) * 100.0,
            "next_irl_new_vs_prior_share_pct": sum(actual[k] for k in actual_new_keys) * 100.0,
            "online_new_vs_prior_archetype_count": len(online_new_keys),
            "next_irl_new_vs_prior_archetype_count": len(actual_new_keys),
            "top_metrics": top_metrics,
            "deck_rows": deck_rows,
        })

    return rows, names


def summarise(rows: list[dict]) -> dict:
    result = {
        "cohort_count": len(rows),
        "date_min": min((r["target_start_date"] for r in rows), default=None),
        "date_max": max((r["target_start_date"] for r in rows), default=None),
        "top_n": {},
        "tail": {},
    }

    for n in TOP_NS:
        key = str(n)
        own_prior = [r["top_metrics"][key]["prior_irl_own_top_share_pct"] for r in rows]
        own_online = [r["top_metrics"][key]["online_own_top_share_pct"] for r in rows]
        own_actual = [r["top_metrics"][key]["next_irl_own_top_share_pct"] for r in rows]
        same_online = [r["top_metrics"][key]["prior_top_keys_online_share_pct"] for r in rows]
        same_actual = [r["top_metrics"][key]["prior_top_keys_next_irl_share_pct"] for r in rows]

        observations = [obs for r in rows for obs in r["deck_rows"][key]]
        online_drop_obs = [obs for obs in observations if obs["online_lower_than_prior"]]
        online_deltas = [obs["online_delta_pp"] for obs in observations]
        actual_deltas = [obs["next_irl_delta_pp"] for obs in observations]
        drop_actual_deltas = [obs["next_irl_delta_pp"] for obs in online_drop_obs]

        lower_online_count = sum(1 for obs in observations if obs["online_lower_than_prior"])
        lower_actual_count = sum(1 for obs in observations if obs["next_irl_lower_than_prior"])
        drop_and_actual_down = sum(
            1 for obs in online_drop_obs if obs["next_irl_lower_than_prior"]
        )
        majority_cohorts = sum(
            1 for r in rows
            if r["top_metrics"][key]["top_decks_lower_online_count"] > len(r["deck_rows"][key]) / 2
        )
        all_cohorts = sum(
            1 for r in rows
            if r["top_metrics"][key]["top_decks_lower_online_count"] == len(r["deck_rows"][key])
        )
        online_less_concentrated = sum(
            1 for p, o in zip(own_prior, own_online) if o < p
        )

        result["top_n"][key] = {
            "deck_observation_count": len(observations),
            "top_decks_lower_online_count": lower_online_count,
            "top_decks_lower_online_pct": 100.0 * lower_online_count / len(observations) if observations else None,
            "top_decks_lower_next_irl_pct": 100.0 * lower_actual_count / len(observations) if observations else None,
            "cohorts_majority_top_decks_lower_online_count": majority_cohorts,
            "cohorts_majority_top_decks_lower_online_pct": 100.0 * majority_cohorts / len(rows) if rows else None,
            "cohorts_all_top_decks_lower_online_count": all_cohorts,
            "cohorts_all_top_decks_lower_online_pct": 100.0 * all_cohorts / len(rows) if rows else None,
            "online_own_top_n_less_concentrated_than_prior_count": online_less_concentrated,
            "online_own_top_n_less_concentrated_than_prior_pct": 100.0 * online_less_concentrated / len(rows) if rows else None,
            "mean_prior_irl_own_top_n_share_pct": mean(own_prior),
            "mean_online_own_top_n_share_pct": mean(own_online),
            "mean_next_irl_own_top_n_share_pct": mean(own_actual),
            "mean_prior_top_keys_online_share_pct": mean(same_online),
            "mean_prior_top_keys_next_irl_share_pct": mean(same_actual),
            "mean_online_delta_pp_for_prior_top_decks": mean(online_deltas),
            "median_online_delta_pp_for_prior_top_decks": median(online_deltas),
            "mean_next_irl_delta_pp_for_prior_top_decks": mean(actual_deltas),
            "median_next_irl_delta_pp_for_prior_top_decks": median(actual_deltas),
            "online_delta_vs_next_irl_delta_pearson_r": pearson(online_deltas, actual_deltas),
            "among_online_drops_next_irl_also_down_pct": (
                100.0 * drop_and_actual_down / len(online_drop_obs) if online_drop_obs else None
            ),
            "among_online_drops_mean_next_irl_delta_pp": mean(drop_actual_deltas),
        }

    result["tail"] = {
        "mean_online_new_vs_prior_share_pct": mean([r["online_new_vs_prior_share_pct"] for r in rows]),
        "median_online_new_vs_prior_share_pct": median([r["online_new_vs_prior_share_pct"] for r in rows]),
        "mean_next_irl_new_vs_prior_share_pct": mean([r["next_irl_new_vs_prior_share_pct"] for r in rows]),
        "median_next_irl_new_vs_prior_share_pct": median([r["next_irl_new_vs_prior_share_pct"] for r in rows]),
        "mean_online_named_archetype_count": mean([float(r["online_named_archetype_count"]) for r in rows]),
        "mean_prior_irl_named_archetype_count": mean([float(r["prior_named_archetype_count"]) for r in rows]),
        "mean_next_irl_named_archetype_count": mean([float(r["next_irl_named_archetype_count"]) for r in rows]),
    }
    return result


def current_snapshot() -> dict | None:
    current = load_json(CURRENT_PATH, None)
    if not current:
        return None
    archetypes = current.get("archetypes") or []
    if not archetypes:
        return None
    sorted_irl = sorted(archetypes, key=lambda x: (-float(x.get("irl_pct") or 0.0), str(x.get("key") or "")))
    out = {
        "forecast_date": current.get("forecast_date"),
        "format": current.get("format"),
        "latest_irl": current.get("latest_irl"),
        "online_event_count": current.get("online_event_count"),
        "weights": current.get("weights"),
        "top_n": {},
    }
    for n in TOP_NS:
        rows = sorted_irl[:n]
        drops = [x for x in rows if float(x.get("online_pct") or 0.0) < float(x.get("irl_pct") or 0.0)]
        out["top_n"][str(n)] = {
            "prior_irl_top_share_pct": sum(float(x.get("irl_pct") or 0.0) for x in rows),
            "same_keys_online_share_pct": sum(float(x.get("online_pct") or 0.0) for x in rows),
            "lower_online_count": len(drops),
            "lower_online_pct": 100.0 * len(drops) / len(rows) if rows else None,
            "rows": [
                {
                    "key": x.get("key"),
                    "name": x.get("name"),
                    "irl_pct": float(x.get("irl_pct") or 0.0),
                    "online_pct": float(x.get("online_pct") or 0.0),
                    "delta_pp": float(x.get("online_pct") or 0.0) - float(x.get("irl_pct") or 0.0),
                }
                for x in rows
            ],
        }
    return out


def fmt(x, digits=1):
    return "—" if x is None else f"{x:.{digits}f}"


def build_report(summary: dict, recent: dict, current: dict | None) -> str:
    lines = [
        "# Online spread / long-tail diagnostic",
        "",
        "## Question",
        "",
        "When we compare the previous IRL major with qualifying Online play before the next IRL cohort, "
        "how often do the previous IRL top decks lose share simply because Online is more diffuse, and "
        "how much of that wider Online tail survives into the next IRL field?",
        "",
        "This is a descriptive diagnostic only. It does **not** change the forecast formula.",
        "",
        "## Sample",
        "",
        f"- Full historical settled primary sample: **{summary['cohort_count']} independent cohorts** "
        f"({summary['date_min']} to {summary['date_max']}).",
        f"- Recent-era sensitivity: **{recent['cohort_count']} cohorts** "
        f"({recent['date_min']} to {recent['date_max']}).",
        "- Named archetypes only; source Other/Unknown/unclassified is excluded and each source distribution is renormalised to 100%, matching the existing forecast research.",
        "- 'Top N' is defined from the **previous IRL field**, so no future information is used.",
        "",
        "## Headline concentration result",
        "",
        "| Previous-IRL top group | IRL top-N share | Online own top-N share | Same IRL top-N decks Online | Next IRL own top-N share | Prior top-N decks lower Online | Cohorts where Online top-N is less concentrated |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for n in (3, 5, 10, 20):
        s = summary["top_n"][str(n)]
        lines.append(
            f"| Top {n} | {fmt(s['mean_prior_irl_own_top_n_share_pct'])}% | "
            f"{fmt(s['mean_online_own_top_n_share_pct'])}% | "
            f"{fmt(s['mean_prior_top_keys_online_share_pct'])}% | "
            f"{fmt(s['mean_next_irl_own_top_n_share_pct'])}% | "
            f"{fmt(s['top_decks_lower_online_pct'])}% | "
            f"{fmt(s['online_own_top_n_less_concentrated_than_prior_pct'])}% |"
        )

    lines += [
        "",
        "## Do apparent Online drops carry into the next IRL field?",
        "",
        "| Previous-IRL top group | Mean Online delta per top deck | Mean next-IRL delta per top deck | If deck drops Online, next IRL also down | Correlation Online delta vs next IRL delta |",
        "|---|---:|---:|---:|---:|",
    ]
    for n in (3, 5, 10, 20):
        s = summary["top_n"][str(n)]
        lines.append(
            f"| Top {n} | {fmt(s['mean_online_delta_pp_for_prior_top_decks'], 2)}pp | "
            f"{fmt(s['mean_next_irl_delta_pp_for_prior_top_decks'], 2)}pp | "
            f"{fmt(s['among_online_drops_next_irl_also_down_pct'])}% | "
            f"{fmt(s['online_delta_vs_next_irl_delta_pearson_r'], 2)} |"
        )

    lines += [
        "",
        "## New / tail archetypes",
        "",
        f"- Mean share Online from named archetypes absent from the previous IRL field: **{fmt(summary['tail']['mean_online_new_vs_prior_share_pct'])}%**.",
        f"- Mean share at the next IRL cohort from named archetypes absent from the previous IRL field: **{fmt(summary['tail']['mean_next_irl_new_vs_prior_share_pct'])}%**.",
        f"- Mean named archetype count: previous IRL **{fmt(summary['tail']['mean_prior_irl_named_archetype_count'], 1)}**, "
        f"Online **{fmt(summary['tail']['mean_online_named_archetype_count'], 1)}**, "
        f"next IRL **{fmt(summary['tail']['mean_next_irl_named_archetype_count'], 1)}**.",
        "",
        "## Recent-era sensitivity",
        "",
        "| Previous-IRL top group | Prior top decks lower Online | Online own top-N less concentrated | Mean Online delta | Mean next-IRL delta |",
        "|---|---:|---:|---:|---:|",
    ]
    for n in (3, 5, 10, 20):
        s = recent["top_n"][str(n)]
        lines.append(
            f"| Top {n} | {fmt(s['top_decks_lower_online_pct'])}% | "
            f"{fmt(s['online_own_top_n_less_concentrated_than_prior_pct'])}% | "
            f"{fmt(s['mean_online_delta_pp_for_prior_top_decks'], 2)}pp | "
            f"{fmt(s['mean_next_irl_delta_pp_for_prior_top_decks'], 2)}pp |"
        )

    if current:
        c10 = current["top_n"]["10"]
        lines += [
            "",
            "## Current Worlds → Online illustration",
            "",
            f"For the existing {current.get('forecast_date')} snapshot, the previous IRL top 10 held "
            f"**{fmt(c10['prior_irl_top_share_pct'])}%** of the Worlds field but only "
            f"**{fmt(c10['same_keys_online_share_pct'])}%** of subsequent Online play; "
            f"**{c10['lower_online_count']}/10** were lower Online.",
            "",
            "| Archetype | Worlds IRL | Online since | Delta |",
            "|---|---:|---:|---:|",
        ]
        for row in c10["rows"]:
            lines.append(
                f"| {row['name']} | {fmt(row['irl_pct'])}% | {fmt(row['online_pct'])}% | {fmt(row['delta_pp'], 1)}pp |"
            )

    lines += [
        "",
        "## Interpretation boundary",
        "",
        "- **Verified:** values above are direct calculations from the frozen historical archive and existing window rules.",
        "- **Inferred:** if Online concentration is repeatedly lower while the next IRL field re-concentrates, raw per-deck Online-vs-IRL deltas partly reflect platform-level spread rather than pure deck-specific decline.",
        "- **Unknown:** whether explicitly correcting for concentration/tail structure improves chronological field-forecast accuracy. That requires a separate forecasting experiment.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    rows, _ = historical_rows()
    recent_rows = [
        r for r in rows
        if RECENT_START <= parse_date(r["target_start_date"]) <= RECENT_END
    ]
    summary = summarise(rows)
    recent = summarise(recent_rows)
    current = current_snapshot()

    pack = {
        "schema_version": 1,
        "question": "How much of the apparent decline in previous-IRL top-deck share Online is structural Online spread/long-tail behaviour?",
        "sample": {
            "full": {
                "cohort_count": summary["cohort_count"],
                "date_min": summary["date_min"],
                "date_max": summary["date_max"],
            },
            "recent": {
                "start": RECENT_START.isoformat(),
                "end": RECENT_END.isoformat(),
                "cohort_count": recent["cohort_count"],
            },
        },
        "full": summary,
        "recent": recent,
        "current_snapshot": current,
        "cohorts": rows,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "summary.json").write_text(json.dumps(pack, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    (RESULTS_DIR / "README.md").write_text(build_report(summary, recent, current) + "\n", encoding="utf-8")
    print(json.dumps({
        "cohorts": summary["cohort_count"],
        "recent_cohorts": recent["cohort_count"],
        "top10_lower_online_pct": summary["top_n"]["10"]["top_decks_lower_online_pct"],
        "top10_online_less_concentrated_pct": summary["top_n"]["10"]["online_own_top_n_less_concentrated_than_prior_pct"],
    }, indent=2))


if __name__ == "__main__":
    main()
