#!/usr/bin/env python3
"""Score simple historical meta baselines against frozen prediction windows.

Headline scoring is on named archetypes only: source `Other`/`Unknown` and
unclassified Online entries remain in the archive/audits but are excluded from
model distributions, matching the production blend's normalisation policy.
Exact archetype IDs/slugs are preserved as the comparison key.
"""

from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOWS_PATH = ROOT / "data" / "processed" / "prediction-windows" / "windows.json"
ONLINE_TAGS_PATH = ROOT / "data" / "processed" / "format-tags" / "online-events.json"
IRL_TAGS_PATH = ROOT / "data" / "processed" / "format-tags" / "irl-events.json"
OUT_DIR = ROOT / "data" / "processed" / "model-results"
RESULTS_DIR = ROOT / "results" / "model-results"

IRL_MAX = 0.70
IRL_MIN = 0.30
IRL_DECAY_PER_DAY = 0.02

MODELS = {
    "online_only": {
        "label": "Online-only",
        "description": "All qualifying same-format Online evidence before the frozen target cutoff.",
    },
    "irl_only": {
        "label": "IRL-only",
        "description": "Latest completed same-format IRL major cohort only; settled targets only.",
    },
    "fifty_fifty": {
        "label": "50/50",
        "description": "Latest same-format IRL cohort plus qualifying Online evidence since that cohort, fixed 50/50 weights; settled targets only.",
    },
    "current_v2_1": {
        "label": "Current v2.1",
        "description": "Production settled-format weighting: IRL starts at 70%, decays 2 percentage points/day to a 30% floor; Online is qualifying evidence since the latest IRL cohort.",
    },
}


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
    total = sum(max(0, float(v)) for v in counts.values())
    return {k: max(0, float(v)) / total for k, v in counts.items() if v > 0} if total else {}


def blend(left: dict[str, float], right: dict[str, float], left_weight: float) -> dict[str, float]:
    if not left or not right:
        return {}
    right_weight = 1.0 - left_weight
    keys = set(left) | set(right)
    out = {k: left.get(k, 0.0) * left_weight + right.get(k, 0.0) * right_weight for k in keys}
    total = sum(out.values())
    return {k: v / total for k, v in out.items()} if total else {}


def score(pred: dict[str, float], actual: dict[str, float], names: dict[str, str]) -> dict | None:
    if not pred or not actual:
        return None
    keys = sorted(set(pred) | set(actual))
    deltas = [(k, pred.get(k, 0.0) - actual.get(k, 0.0)) for k in keys]
    l1 = sum(abs(delta) for _, delta in deltas)
    field_accuracy = max(0.0, 1.0 - 0.5 * l1)
    misses = sorted(deltas, key=lambda item: abs(item[1]), reverse=True)
    return {
        "field_accuracy": field_accuracy,
        "field_accuracy_pct": field_accuracy * 100.0,
        "mae_pp": (l1 / len(keys) * 100.0) if keys else None,
        "archetype_count": len(keys),
        "biggest_miss": ({
            "key": misses[0][0],
            "name": names.get(misses[0][0], misses[0][0]),
            "predicted_pct": pred.get(misses[0][0], 0.0) * 100.0,
            "actual_pct": actual.get(misses[0][0], 0.0) * 100.0,
            "delta_pp": misses[0][1] * 100.0,
        } if misses else None),
        "top_misses": [
            {
                "key": key,
                "name": names.get(key, key),
                "predicted_pct": pred.get(key, 0.0) * 100.0,
                "actual_pct": actual.get(key, 0.0) * 100.0,
                "delta_pp": delta * 100.0,
            }
            for key, delta in misses[:5]
        ],
    }


def prediction_rows(pred: dict[str, float], actual: dict[str, float], names: dict[str, str]) -> list[dict]:
    rows = []
    for key in sorted(set(pred) | set(actual), key=lambda k: max(pred.get(k, 0), actual.get(k, 0)), reverse=True):
        p = pred.get(key, 0.0) * 100.0
        a = actual.get(key, 0.0) * 100.0
        rows.append({"key": key, "name": names.get(key, key), "predicted_pct": p, "actual_pct": a, "delta_pp": p - a})
    return rows


def model_summary(rows: list[dict], model_key: str, subset=None) -> dict:
    selected = []
    for row in rows:
        if subset and not subset(row):
            continue
        result = row["models"].get(model_key)
        if result and result.get("available") and row.get("target_eligible_ge_95"):
            selected.append((row, result))
    accuracies = [r["field_accuracy_pct"] for _, r in selected]
    maes = [r["mae_pp"] for _, r in selected if r.get("mae_pp") is not None]
    cohort_values: dict[str, list[float]] = defaultdict(list)
    for row, result in selected:
        cohort_values[row["cohort_id"]].append(result["field_accuracy_pct"])
    cohort_means = [statistics.fmean(values) for values in cohort_values.values()]
    return {
        "event_count": len(selected),
        "cohort_count": len(cohort_values),
        "mean_field_accuracy_pct": statistics.fmean(accuracies) if accuracies else None,
        "median_field_accuracy_pct": statistics.median(accuracies) if accuracies else None,
        "cohort_mean_field_accuracy_pct": statistics.fmean(cohort_means) if cohort_means else None,
        "mean_mae_pp": statistics.fmean(maes) if maes else None,
    }


def main() -> None:
    pack = load_json(WINDOWS_PATH, {}) or {}
    windows = pack.get("windows") or []
    cohorts = pack.get("cohorts") or []
    online_meta = {str(e["id"]): e for e in (load_json(ONLINE_TAGS_PATH, []) or [])}
    irl_meta = {str(e["id"]): e for e in (load_json(IRL_TAGS_PATH, []) or [])}
    online_counts, online_names = online_decks()
    irl_counts, irl_names = irl_decks()
    names = {**online_names, **irl_names}
    rows: list[dict] = []

    for w in windows:
        target_id = str(w["target_id"])
        actual = normalise(irl_counts.get(target_id, Counter()))
        target_meta = irl_meta[target_id]
        online_all_ids = [str(i) for i in w.get("online_primary_ids") or []]
        online_all = normalise(aggregate(online_all_ids, online_counts))

        latest_cohort = None
        latest_irl_ids: list[str] = []
        prior_same = set(str(i) for i in w.get("prior_irl_same_format_ids") or [])
        candidates = []
        for cohort in cohorts:
            same_ids = [str(i) for i in cohort.get("event_ids") or [] if str(i) in prior_same]
            if same_ids:
                candidates.append((cohort["end_date"], cohort, same_ids))
        if candidates:
            _, latest_cohort, latest_irl_ids = max(candidates, key=lambda item: (item[0], item[1]["cohort_id"]))

        latest_irl = normalise(aggregate(latest_irl_ids, irl_counts)) if latest_irl_ids else {}
        major_final_day = None
        online_since_ids: list[str] = []
        days_since_major = None
        if latest_irl_ids:
            latest_end = max(parse_date(irl_meta[i]["end_date"]) for i in latest_irl_ids)
            major_final_day = end_of_iso_week(latest_end)
            online_since_ids = [
                event_id for event_id in online_all_ids
                if event_id in online_meta and parse_dt(online_meta[event_id]["start_at"]).date() > major_final_day
            ]
            days_since_major = max(0, (parse_date(w["cohort_start_date"]) - major_final_day).days)
        online_since = normalise(aggregate(online_since_ids, online_counts)) if online_since_ids else {}

        model_results: dict[str, dict] = {}

        def store(model_key: str, pred: dict[str, float], *, available: bool, reason: str | None, weights=None, online_ids=None, irl_ids=None):
            base = {
                "available": available,
                "reason": reason,
                "weights": weights,
                "online_event_ids": list(online_ids or []),
                "irl_event_ids": list(irl_ids or []),
            }
            if available:
                scored = score(pred, actual, names)
                if not scored:
                    base.update({"available": False, "reason": "No scoreable named-archetype distribution."})
                else:
                    base.update(scored)
                    base["prediction"] = prediction_rows(pred, actual, names)
            model_results[model_key] = base

        store(
            "online_only", online_all,
            available=bool(online_all), reason=None if online_all else "No qualifying Online evidence before cutoff.",
            weights={"irl": 0.0, "online": 1.0}, online_ids=online_all_ids,
        )

        if w["window_class"] == "settled" and latest_irl:
            store("irl_only", latest_irl, available=True, reason=None, weights={"irl": 1.0, "online": 0.0}, irl_ids=latest_irl_ids)
            if online_since:
                store("fifty_fifty", blend(latest_irl, online_since, 0.50), available=True, reason=None,
                      weights={"irl": 0.50, "online": 0.50}, online_ids=online_since_ids, irl_ids=latest_irl_ids)
                irl_weight = max(IRL_MIN, min(IRL_MAX, IRL_MAX - IRL_DECAY_PER_DAY * (days_since_major or 0)))
                store("current_v2_1", blend(latest_irl, online_since, irl_weight), available=True, reason=None,
                      weights={"irl": irl_weight, "online": 1.0 - irl_weight}, online_ids=online_since_ids, irl_ids=latest_irl_ids)
            else:
                reason = "No qualifying same-format Online event after the latest IRL cohort and before target cutoff."
                store("fifty_fifty", {}, available=False, reason=reason, weights={"irl": 0.50, "online": 0.50}, irl_ids=latest_irl_ids)
                store("current_v2_1", {}, available=False, reason=reason, irl_ids=latest_irl_ids)
        else:
            reason = "Transition windows use the clean Online-only baseline; no same-format completed IRL major exists yet."
            store("irl_only", {}, available=False, reason=reason)
            store("fifty_fifty", {}, available=False, reason=reason)
            store("current_v2_1", {}, available=False, reason=reason)

        rows.append({
            "target_id": target_id,
            "target_name": w["target_name"],
            "target_start_date": w["target_start_date"],
            "target_end_date": w["target_end_date"],
            "target_event_type": w["target_event_type"],
            "target_format": w["target_format"],
            "target_players": w["target_players"],
            "target_field_capture": w["target_field_capture"],
            "target_eligible_ge_95": bool(w["target_eligible_ge_95"]),
            "target_eligible_ge_98": bool(w["target_eligible_ge_98"]),
            "window_class": w["window_class"],
            "cohort_id": w["cohort_id"],
            "cohort_event_count": w["cohort_event_count"],
            "days_into_format": target_meta.get("days_into_format"),
            "latest_prior_cohort_id": latest_cohort["cohort_id"] if latest_cohort else None,
            "latest_prior_irl_ids": latest_irl_ids,
            "latest_prior_major_final_day": major_final_day.isoformat() if major_final_day else None,
            "days_since_major": days_since_major,
            "online_all_event_count": len(online_all_ids),
            "online_since_major_event_count": len(online_since_ids),
            "models": model_results,
        })

    settled_primary = [r for r in rows if r["target_eligible_ge_95"] and r["window_class"] == "settled"]
    model_keys = list(MODELS)
    complete = [r for r in settled_primary if all(r["models"][m].get("available") for m in model_keys)]
    complete_ids = {r["target_id"] for r in complete}

    event_wins = {m: 0.0 for m in model_keys}
    for row in complete:
        best = max(row["models"][m]["field_accuracy_pct"] for m in model_keys)
        winners = [m for m in model_keys if abs(row["models"][m]["field_accuracy_pct"] - best) < 1e-9]
        for m in winners:
            event_wins[m] += 1.0 / len(winners)

    cohort_scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in complete:
        for m in model_keys:
            cohort_scores[row["cohort_id"]][m].append(row["models"][m]["field_accuracy_pct"])
    cohort_wins = {m: 0.0 for m in model_keys}
    for by_model in cohort_scores.values():
        means = {m: statistics.fmean(by_model[m]) for m in model_keys}
        best = max(means.values())
        winners = [m for m, value in means.items() if abs(value - best) < 1e-9]
        for m in winners:
            cohort_wins[m] += 1.0 / len(winners)

    def pairwise(a: str, b: str) -> dict:
        deltas = [r["models"][a]["field_accuracy_pct"] - r["models"][b]["field_accuracy_pct"] for r in complete]
        return {
            "event_count": len(deltas),
            "first_model": a,
            "second_model": b,
            "first_wins": sum(d > 1e-9 for d in deltas),
            "second_wins": sum(d < -1e-9 for d in deltas),
            "ties": sum(abs(d) <= 1e-9 for d in deltas),
            "mean_first_minus_second_pp": statistics.fmean(deltas) if deltas else None,
        }

    summaries = {}
    for model_key in model_keys:
        summaries[model_key] = {
            "model": MODELS[model_key],
            "overall_primary": model_summary(rows, model_key),
            "settled_primary": model_summary(rows, model_key, lambda r: r["window_class"] == "settled"),
            "transition_primary": model_summary(rows, model_key, lambda r: r["window_class"] == "transition"),
            "worlds_primary": model_summary(rows, model_key, lambda r: "World" in str(r["target_event_type"])),
            "complete_case_settled": model_summary(rows, model_key, lambda r: r["target_id"] in complete_ids),
            "event_wins_complete_case": event_wins[model_key],
            "cohort_wins_complete_case": cohort_wins[model_key],
        }

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scoring_policy": {
            "metric": "Field Accuracy = 100% - 0.5 * sum(abs(predicted share - actual share))",
            "distribution_scope": "Named archetypes only; Other/Unknown/unclassified are retained in source data but excluded then distributions are renormalised.",
            "identity_key": "Exact Online deck id / IRL Labs slug; variants are not collapsed.",
            "primary_target_threshold": ">=95% IRL field capture",
            "transition_policy": "Online-only clean baseline. Prior-format IRL is not carried forward.",
            "settled_irl_scope": "Latest completed same-format IRL overlap cohort.",
            "settled_online_only_scope": "All qualifying same-format Online events before cutoff.",
            "settled_blend_online_scope": "Qualifying same-format Online events after the latest IRL cohort and before cutoff.",
            "current_v2_1_weights": "IRL max 70%, min 30%, decay 2 percentage points/day; Online receives the remainder.",
        },
        "target_count": len(rows),
        "primary_target_count": sum(r["target_eligible_ge_95"] for r in rows),
        "primary_settled_count": sum(r["target_eligible_ge_95"] and r["window_class"] == "settled" for r in rows),
        "primary_transition_count": sum(r["target_eligible_ge_95"] and r["window_class"] == "transition" for r in rows),
        "complete_case_settled_event_count": len(complete),
        "complete_case_settled_cohort_count": len(cohort_scores),
        "models": summaries,
        "pairwise": {
            "current_v2_1_vs_fifty_fifty": pairwise("current_v2_1", "fifty_fifty"),
            "current_v2_1_vs_irl_only": pairwise("current_v2_1", "irl_only"),
            "fifty_fifty_vs_irl_only": pairwise("fifty_fifty", "irl_only"),
            "current_v2_1_vs_online_only": pairwise("current_v2_1", "online_only"),
        },
        "pairwise_v2_1_vs_50_50": {
            "event_count": len(complete),
            "v2_1_wins": pairwise("current_v2_1", "fifty_fifty")["first_wins"],
            "fifty_fifty_wins": pairwise("current_v2_1", "fifty_fifty")["second_wins"],
            "ties": pairwise("current_v2_1", "fifty_fifty")["ties"],
            "mean_v2_1_minus_50_50_pp": pairwise("current_v2_1", "fifty_fifty")["mean_first_minus_second_pp"],
        },
    }

    pack_out = {"schema_version": 1, "summary": summary, "targets": rows}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "baselines.json").write_text(json.dumps(pack_out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with (OUT_DIR / "events.csv").open("w", encoding="utf-8", newline="") as f:
        cols = ["target_id", "target_name", "target_start_date", "target_event_type", "target_format", "window_class", "cohort_id"]
        for model_key in model_keys:
            cols.extend([f"{model_key}_available", f"{model_key}_accuracy_pct", f"{model_key}_mae_pp"])
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for row in rows:
            record = {k: row.get(k) for k in cols if k in row}
            for model_key in model_keys:
                result = row["models"][model_key]
                record[f"{model_key}_available"] = bool(result.get("available"))
                record[f"{model_key}_accuracy_pct"] = result.get("field_accuracy_pct")
                record[f"{model_key}_mae_pp"] = result.get("mae_pp")
            writer.writerow(record)

    readme = f"""# Baseline model scoring\n\nPrimary comparison uses targets with >=95% IRL field capture. Transition targets use the clean Online-only baseline; IRL-only, 50/50 and current v2.1 are compared on settled-format targets.\n\n- Primary targets: **{summary['primary_target_count']}**\n- Primary settled targets: **{summary['primary_settled_count']}**\n- Primary transition targets: **{summary['primary_transition_count']}**\n- Complete-case settled targets for like-for-like model comparison: **{summary['complete_case_settled_event_count']}** across **{summary['complete_case_settled_cohort_count']}** cohorts\n\nHeadline Field Accuracy is `100% - 0.5 * sum(abs(predicted - actual))`. Named archetypes are normalised to 100%; source Other/Unknown/unclassified mass remains auditable but is not treated as an archetype.\n"""
    (RESULTS_DIR / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
