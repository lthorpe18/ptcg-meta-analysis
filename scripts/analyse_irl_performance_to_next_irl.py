#!/usr/bin/env python3
"""Phase 2: test whether previous-IRL performance predicts next-IRL field movement.

Research question
-----------------
After controlling for an archetype's previous same-format IRL Day-1 share, does
relative performance at that major predict its change in representation at the
next adjacent same-format IRL cohort?

Boundary
--------
* IRL evidence only. No Online evidence is used.
* Existing prediction-window cohort membership and >=95% capture rule are reused.
* Simultaneous majors remain one cohort and never predict one another.
* Target-tournament performance is never used as a feature.
* Primary performance specification is predeclared from Phase 1:
    bounded Day-2 log2 representation lift, prior cohort share >=1%.
* Forecasts start from persistence and apply one fitted composition-preserving
  scalar performance tilt. Negative shares are clipped and distributions are
  renormalised to 100%.
* Validation is fixed chronological 70/30 plus expanding walk-forward after 15
  earlier eligible pairs. Secondary signals/small-share thresholds are sensitivity
  analyses, not post-hoc replacements for the primary specification.
"""
from __future__ import annotations

import csv
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import score_baseline_models as scorer

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ROOT / "data" / "processed" / "prediction-windows" / "windows.json"
IRL_TAGS = ROOT / "data" / "processed" / "format-tags" / "irl-events.json"
PERF_DIR = ROOT / "data" / "raw" / "irl-performance" / "labs" / "events"
OUTDIR = ROOT / "data" / "processed" / "irl-performance-to-next-irl"
RESDIR = ROOT / "results" / "irl-performance-to-next-irl"

MIN_CAPTURE = 0.95
MIN_WALKFORWARD_TRAIN = 15
BOOTSTRAPS = 3000
RNG_SEED = 20260915

SCENARIOS = [
    {
        "id": "day2_bounded_share1",
        "label": "Day-2 lift, bounded [-2,+2], prior share >=1%",
        "kind": "day2",
        "threshold_pct": 1.0,
        "bound": 2.0,
        "primary": True,
    },
    {
        "id": "day2_bounded_share0_5",
        "label": "Day-2 lift, bounded [-2,+2], prior share >=0.5%",
        "kind": "day2",
        "threshold_pct": 0.5,
        "bound": 2.0,
        "primary": False,
    },
    {
        "id": "day2_bounded_share2",
        "label": "Day-2 lift, bounded [-2,+2], prior share >=2%",
        "kind": "day2",
        "threshold_pct": 2.0,
        "bound": 2.0,
        "primary": False,
    },
    {
        "id": "day2_unbounded_share1",
        "label": "Day-2 lift, unbounded, prior share >=1%",
        "kind": "day2",
        "threshold_pct": 1.0,
        "bound": None,
        "primary": False,
    },
    {
        "id": "points_share1",
        "label": "Event-centred Day-1 points rate, prior share >=1%",
        "kind": "points",
        "threshold_pct": 1.0,
        "bound": None,
        "primary": False,
    },
    {
        "id": "top32_bounded_share1",
        "label": "Top-32 lift, bounded [-2,+2], prior share >=1%",
        "kind": "top32",
        "threshold_pct": 1.0,
        "bound": 2.0,
        "primary": False,
    },
    {
        "id": "winner_all",
        "label": "Tournament-winner visibility indicator",
        "kind": "winner",
        "threshold_pct": 0.0,
        "bound": None,
        "primary": False,
    },
]


def mean(values):
    vals = list(values)
    return statistics.fmean(vals) if vals else None


def median(values):
    vals = list(values)
    return statistics.median(vals) if vals else None


def percentile(values, p):
    vals = sorted(v for v in values if v is not None and math.isfinite(v))
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * p
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    frac = pos - lo
    return vals[lo] * (1 - frac) + vals[hi] * frac


def normalise_map(values):
    cleaned = {k: max(0.0, float(v)) for k, v in values.items() if float(v) > 0}
    total = sum(cleaned.values())
    return {k: v / total for k, v in cleaned.items()} if total else {}


def field_accuracy(pred, actual):
    if not pred or not actual:
        return None
    keys = set(pred) | set(actual)
    l1 = sum(abs(pred.get(k, 0.0) - actual.get(k, 0.0)) for k in keys)
    return 100.0 * max(0.0, 1.0 - 0.5 * l1)


def solve_2x2(a11, a12, a22, b1, b2):
    det = a11 * a22 - a12 * a12
    if abs(det) < 1e-14:
        return None
    return ((b1 * a22 - b2 * a12) / det, (b2 * a11 - b1 * a12) / det)


def build_cohorts():
    pack = json.loads(WINDOWS.read_text(encoding="utf-8"))
    tags = {str(e["id"]): e for e in json.loads(IRL_TAGS.read_text(encoding="utf-8"))}
    irl_counts, _ = scorer.irl_decks()

    cohorts = []
    for c in pack.get("cohorts", []):
        ids = [str(i) for i in c.get("event_ids", [])]
        metas = [tags[i] for i in ids if i in tags]
        if len(metas) != len(ids) or not metas:
            continue
        formats = {m["display_format"] for m in metas}
        if len(formats) != 1:
            raise RuntimeError(f"Cohort {c['cohort_id']} spans multiple formats: {formats}")
        counts = Counter()
        for event_id in ids:
            counts.update(irl_counts.get(event_id, Counter()))
        distribution = scorer.normalise(counts)
        eligible = all(float(m.get("field_count_ratio") or 0.0) >= MIN_CAPTURE for m in metas)
        cohorts.append({
            "cohort_id": c["cohort_id"],
            "start_date": c["start_date"],
            "end_date": c["end_date"],
            "event_ids": ids,
            "event_names": [m["name"] for m in metas],
            "format": next(iter(formats)),
            "capture_min": min(float(m.get("field_count_ratio") or 0.0) for m in metas),
            "eligible": eligible,
            "distribution": distribution,
        })
    cohorts.sort(key=lambda c: (c["start_date"], c["cohort_id"]))
    return cohorts


def build_pairs(cohorts):
    by_format = defaultdict(list)
    for c in cohorts:
        by_format[c["format"]].append(c)
    pairs = []
    for fmt, seq in by_format.items():
        seq.sort(key=lambda c: (c["start_date"], c["cohort_id"]))
        for idx in range(1, len(seq)):
            prev = seq[idx - 1]
            target = seq[idx]
            # Exact same strict adjacency/capture boundary as the IRL regression work.
            if not (prev["eligible"] and target["eligible"]):
                continue
            pairs.append({
                "pair_id": f"{prev['cohort_id']}->{target['cohort_id']}",
                "format": fmt,
                "source_cohort": prev["cohort_id"],
                "target_cohort": target["cohort_id"],
                "source_event_ids": prev["event_ids"],
                "target_event_ids": target["event_ids"],
                "source_names": prev["event_names"],
                "target_names": target["event_names"],
                "source_start_date": prev["start_date"],
                "source_end_date": prev["end_date"],
                "target_start_date": target["start_date"],
                "target_end_date": target["end_date"],
                "source": prev["distribution"],
                "target": target["distribution"],
                "persistence_accuracy": field_accuracy(prev["distribution"], target["distribution"]),
            })
    pairs.sort(key=lambda p: (p["target_start_date"], p["target_cohort"]))
    return pairs


def load_performance_events():
    return {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(PERF_DIR.glob("*.json"))
    }


def raw_share(event, slug):
    a = event.get("archetypes", {}).get(slug)
    if not a or not event.get("day1_total_live"):
        return 0.0
    return float(a.get("day1_entries_archived") or 0) / float(event["day1_total_live"])


def aggregate_signal_values(pair, scenario, perf_events):
    """Return signal by source archetype. None means the whole scenario is unavailable."""
    kind = scenario["kind"]
    source = pair["source"]
    events = [perf_events[eid] for eid in pair["source_event_ids"]]

    if kind == "top32" and any(int(e.get("top32_rows_with_deck") or 0) < 32 for e in events):
        return None

    # Cohort-wide named-deck points baseline for the points-rate signal.
    pooled_w = pooled_l = pooled_t = 0
    if kind == "points":
        for event in events:
            for slug, a in event.get("archetypes", {}).items():
                if slug == "other":
                    continue
                d1 = a.get("day1_live") or {}
                w, l, t = d1.get("wins"), d1.get("losses"), d1.get("ties")
                if None in (w, l, t):
                    continue
                pooled_w += int(w)
                pooled_l += int(l)
                pooled_t += int(t)
        pooled_games = pooled_w + pooled_l + pooled_t
        pooled_rate = (100.0 * (3 * pooled_w + pooled_t) / (3 * pooled_games)) if pooled_games else None
    else:
        pooled_rate = None

    values = {}
    for slug in source:
        if kind == "day2":
            observed = 0.0
            expected = 0.0
            for event in events:
                a = event.get("archetypes", {}).get(slug)
                share = raw_share(event, slug)
                expected += float(event.get("day2_total_live") or 0) * share
                if a and a.get("day2_live"):
                    observed += float(a["day2_live"].get("entries") or 0)
            value = math.log2((observed + 0.5) / (expected + 0.5))
        elif kind == "points":
            w = l = t = 0
            seen = False
            for event in events:
                a = event.get("archetypes", {}).get(slug)
                d1 = (a or {}).get("day1_live") or {}
                if None in (d1.get("wins"), d1.get("losses"), d1.get("ties")):
                    continue
                seen = True
                w += int(d1["wins"])
                l += int(d1["losses"])
                t += int(d1["ties"])
            games = w + l + t
            if not seen or not games or pooled_rate is None:
                continue
            rate = 100.0 * (3 * w + t) / (3 * games)
            value = rate - pooled_rate
        elif kind == "top32":
            observed = 0.0
            expected = 0.0
            for event in events:
                a = event.get("archetypes", {}).get(slug)
                observed += float((a or {}).get("top32") or 0)
                expected += 32.0 * raw_share(event, slug)
            value = math.log2((observed + 0.5) / (expected + 0.5))
        elif kind == "winner":
            value = 1.0 if any(
                int((event.get("archetypes", {}).get(slug) or {}).get("winner") or 0) == 1
                for event in events
            ) else 0.0
        else:
            raise ValueError(kind)

        if scenario.get("bound") is not None:
            b = float(scenario["bound"])
            value = max(-b, min(b, value))
        values[slug] = value
    return values


def composition_feature(pair, scenario, perf_events):
    """z_i = x_i * (performance_i - active-share-weighted mean performance).

    Only archetypes meeting the predeclared prior-share threshold are active.
    Inactive archetypes receive z=0, so small decks are retained at persistence
    rather than silently removed. Active z values sum to zero, preserving total
    mass before clipping/renormalisation.
    """
    values = aggregate_signal_values(pair, scenario, perf_events)
    if values is None:
        return None
    source = pair["source"]
    threshold = float(scenario["threshold_pct"]) / 100.0
    active = [
        slug for slug, x in source.items()
        if x >= threshold and slug in values and math.isfinite(values[slug])
    ]
    if not active:
        return None
    active_mass = sum(source[s] for s in active)
    if active_mass <= 0:
        return None
    mu = sum(source[s] * values[s] for s in active) / active_mass
    z = {slug: 0.0 for slug in source}
    for slug in active:
        z[slug] = source[slug] * (values[slug] - mu)
    # Floating-point invariant: active tilt should be composition preserving.
    if abs(sum(z.values())) > 1e-10:
        raise RuntimeError(f"Non-zero composition feature sum for {pair['pair_id']}: {sum(z.values())}")
    return {"z": z, "values": values, "active": active, "active_mean": mu}


def fit_beta(pairs, features):
    """Equal-pair weighted least-squares coefficient for target movement on z."""
    num = 0.0
    den = 0.0
    used = 0
    for pair in pairs:
        feat = features.get(pair["pair_id"])
        if feat is None:
            continue
        keys = set(pair["source"]) | set(pair["target"])
        if not keys:
            continue
        pair_num = pair_den = 0.0
        for slug in keys:
            z = feat["z"].get(slug, 0.0)
            movement = pair["target"].get(slug, 0.0) - pair["source"].get(slug, 0.0)
            pair_num += z * movement
            pair_den += z * z
        # Each independent cohort pair contributes equally regardless of taxonomy width.
        scale = 1.0 / len(keys)
        num += scale * pair_num
        den += scale * pair_den
        used += 1
    if used == 0 or den <= 1e-16:
        return None
    return num / den


def forecast(pair, feature, beta):
    raw = {
        slug: pair["source"].get(slug, 0.0) + beta * feature["z"].get(slug, 0.0)
        for slug in pair["source"]
    }
    return normalise_map(raw)


def score_pairs(pairs, features, beta):
    rows = []
    for pair in pairs:
        feat = features.get(pair["pair_id"])
        if feat is None:
            continue
        pred = forecast(pair, feat, beta)
        rows.append({
            "pair_id": pair["pair_id"],
            "format": pair["format"],
            "target_start_date": pair["target_start_date"],
            "accuracy": field_accuracy(pred, pair["target"]),
            "persistence_accuracy": pair["persistence_accuracy"],
        })
    return rows


def summarise_scores(rows):
    if not rows:
        return None
    model = mean(r["accuracy"] for r in rows)
    persistence = mean(r["persistence_accuracy"] for r in rows)
    return {
        "pair_count": len(rows),
        "format_count": len({r["format"] for r in rows}),
        "mean_accuracy": model,
        "mean_persistence_accuracy": persistence,
        "improvement_pp": model - persistence,
    }


def evaluate_scenario(all_pairs, scenario, perf_events):
    features = {
        p["pair_id"]: composition_feature(p, scenario, perf_events)
        for p in all_pairs
    }
    available = [p for p in all_pairs if features[p["pair_id"]] is not None]
    full_beta = fit_beta(available, features)
    full_scores = score_pairs(available, features, full_beta) if full_beta is not None else []

    split = int(math.floor(0.70 * len(all_pairs)))
    train_base = all_pairs[:split]
    holdout_base = all_pairs[split:]
    fixed_beta = fit_beta(train_base, features)
    fixed_rows = score_pairs(holdout_base, features, fixed_beta) if fixed_beta is not None else []

    walk_rows = []
    walk_betas = []
    for idx, target in enumerate(all_pairs):
        if idx < MIN_WALKFORWARD_TRAIN or features[target["pair_id"]] is None:
            continue
        beta = fit_beta(all_pairs[:idx], features)
        if beta is None:
            continue
        scored = score_pairs([target], features, beta)
        if scored:
            walk_rows.extend(scored)
            walk_betas.append(beta)

    latest_target = max(date.fromisoformat(p["target_start_date"]) for p in all_pairs)
    recent_cut = latest_target - timedelta(days=365)
    recent = [p for p in all_pairs if date.fromisoformat(p["target_start_date"]) >= recent_cut]
    recent_beta = fit_beta(recent, features)
    recent_rows = score_pairs(recent, features, recent_beta) if recent_beta is not None else []

    return {
        "scenario": scenario,
        "available_pair_count": len(available),
        "full_sample": {
            "beta": full_beta,
            **(summarise_scores(full_scores) or {}),
        },
        "fixed_holdout": {
            "global_train_pair_count": len(train_base),
            "global_holdout_pair_count": len(holdout_base),
            "training_available_pair_count": sum(features[p["pair_id"]] is not None for p in train_base),
            "beta": fixed_beta,
            **(summarise_scores(fixed_rows) or {}),
        },
        "walk_forward": {
            "minimum_prior_pair_count": MIN_WALKFORWARD_TRAIN,
            "mean_fitted_beta": mean(walk_betas),
            "median_fitted_beta": median(walk_betas),
            **(summarise_scores(walk_rows) or {}),
        },
        "recent_year_descriptive": {
            "cutoff": recent_cut.isoformat(),
            "beta": recent_beta,
            **(summarise_scores(recent_rows) or {}),
        },
        "features": features,
        "fixed_rows": fixed_rows,
        "walk_rows": walk_rows,
    }


def primary_regression_rows(all_pairs, features, threshold_pct=1.0):
    """Within-pair demeaned rows for Δshare ~ prior share + performance.

    This is interpretation only. Forecasting uses the composition-preserving model above.
    Each pair receives equal total weight in the regression.
    """
    out = []
    threshold = threshold_pct / 100.0
    for pair in all_pairs:
        feat = features.get(pair["pair_id"])
        if feat is None:
            continue
        rows = []
        for slug in feat["active"]:
            x = pair["source"].get(slug, 0.0)
            if x < threshold:
                continue
            rows.append({
                "prior_share_pp": 100.0 * x,
                "performance": feat["values"][slug],
                "movement_pp": 100.0 * (pair["target"].get(slug, 0.0) - x),
            })
        if len(rows) < 3:
            continue
        mx = mean(r["prior_share_pp"] for r in rows)
        mp = mean(r["performance"] for r in rows)
        my = mean(r["movement_pp"] for r in rows)
        w = 1.0 / len(rows)
        for r in rows:
            out.append({
                "pair_id": pair["pair_id"],
                "format": pair["format"],
                "target_start_date": pair["target_start_date"],
                "x": r["prior_share_pp"] - mx,
                "p": r["performance"] - mp,
                "y": r["movement_pp"] - my,
                "weight": w,
            })
    return out


def fit_interpretive_regression(rows):
    a11 = a12 = a22 = b1 = b2 = 0.0
    for r in rows:
        w = r["weight"]
        x, p, y = r["x"], r["p"], r["y"]
        a11 += w * x * x
        a12 += w * x * p
        a22 += w * p * p
        b1 += w * x * y
        b2 += w * p * y
    coef = solve_2x2(a11, a12, a22, b1, b2)
    if coef is None:
        return None
    prior_coef, performance_coef = coef
    sse = sst = 0.0
    # Pair-demeaned y has mean ~0, so zero is the natural comparator.
    for r in rows:
        pred = prior_coef * r["x"] + performance_coef * r["p"]
        sse += r["weight"] * (r["y"] - pred) ** 2
        sst += r["weight"] * r["y"] ** 2
    return {
        "prior_share_coef": prior_coef,
        "performance_coef": performance_coef,
        "r2_within_pair": 1.0 - sse / sst if sst > 0 else None,
        "row_count": len(rows),
        "pair_count": len({r["pair_id"] for r in rows}),
        "format_count": len({r["format"] for r in rows}),
    }


def cluster_bootstrap_performance_coef(rows, iterations=BOOTSTRAPS):
    by_format = defaultdict(list)
    for r in rows:
        by_format[r["format"]].append(r)
    formats = sorted(by_format)
    if len(formats) < 2:
        return None
    rng = random.Random(RNG_SEED)
    coefs = []
    for _ in range(iterations):
        sampled = [rng.choice(formats) for _ in formats]
        boot = []
        for fmt in sampled:
            boot.extend(by_format[fmt])
        fit = fit_interpretive_regression(boot)
        if fit is not None and math.isfinite(fit["performance_coef"]):
            coefs.append(fit["performance_coef"])
    return {
        "iterations_requested": iterations,
        "iterations_successful": len(coefs),
        "ci95": [percentile(coefs, 0.025), percentile(coefs, 0.975)] if coefs else [None, None],
        "median": median(coefs),
    }


def strip_features(result):
    return {k: v for k, v in result.items() if k not in {"features", "fixed_rows", "walk_rows"}}


def fmt(x, digits=2):
    return "n/a" if x is None else f"{x:.{digits}f}"


def main():
    cohorts = build_cohorts()
    pairs = build_pairs(cohorts)
    perf_events = load_performance_events()
    if len(pairs) != 36:
        raise RuntimeError(f"Expected 36 eligible adjacent same-format pairs from prior IRL work; got {len(pairs)}")

    scenario_results = {}
    raw_results = {}
    for scenario in SCENARIOS:
        result = evaluate_scenario(pairs, scenario, perf_events)
        raw_results[scenario["id"]] = result
        scenario_results[scenario["id"]] = strip_features(result)

    primary = raw_results["day2_bounded_share1"]
    reg_rows = primary_regression_rows(pairs, primary["features"], threshold_pct=1.0)
    regression = fit_interpretive_regression(reg_rows)
    regression["format_cluster_bootstrap"] = cluster_bootstrap_performance_coef(reg_rows)

    latest_target = max(date.fromisoformat(p["target_start_date"]) for p in pairs)
    recent_cut = latest_target - timedelta(days=365)
    recent_rows = [r for r in reg_rows if date.fromisoformat(r["target_start_date"]) >= recent_cut]
    recent_regression = fit_interpretive_regression(recent_rows)
    if recent_regression:
        recent_regression["cutoff"] = recent_cut.isoformat()
        recent_regression["format_cluster_bootstrap"] = cluster_bootstrap_performance_coef(recent_rows)

    summary = {
        "phase": 2,
        "question": "After controlling for previous IRL share, does prior-major relative performance predict archetype share movement at the next adjacent same-format IRL cohort?",
        "sample": {
            "eligible_adjacent_same_format_pairs": len(pairs),
            "formats": len({p["format"] for p in pairs}),
            "target_start": min(p["target_start_date"] for p in pairs),
            "target_end": max(p["target_start_date"] for p in pairs),
            "fixed_split_train_pairs": int(math.floor(0.70 * len(pairs))),
            "fixed_split_holdout_pairs": len(pairs) - int(math.floor(0.70 * len(pairs))),
            "walk_forward_min_training_pairs": MIN_WALKFORWARD_TRAIN,
        },
        "primary_specification": {
            "scenario_id": "day2_bounded_share1",
            "performance": "log2((observed Day-2 + 0.5)/(expected Day-2 from Day-1 share + 0.5)), bounded [-2,+2]",
            "minimum_prior_share_pct": 1.0,
            "forecast": "persistence + beta * previous_share * (performance - active-share-weighted mean performance), then clip/renormalise",
            "selection_status": "predeclared from Phase-1 stability audit before next-IRL outcomes were analysed in this script",
        },
        "interpretive_regression_primary": regression,
        "interpretive_regression_recent_year": recent_regression,
        "scenarios": scenario_results,
        "notes": [
            "The interpretive regression uses within-pair demeaning and controls for previous share; its performance coefficient is descriptive, not itself the forecasting rule.",
            "Fixed holdout and walk-forward parameters are fitted only on earlier pairs.",
            "Every forecast remains a valid non-negative field-share distribution after clipping/renormalisation.",
            "Sensitivity scenarios are reported against persistence on their own matched available pair subsets.",
            "No Online evidence is used in Phase 2; Online mediation is deliberately deferred.",
        ],
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    RESDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Pair-level primary chronological results for auditability.
    with (OUTDIR / "primary-validation.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["validation", "pair_id", "format", "target_start_date", "accuracy", "persistence_accuracy", "improvement_pp"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for validation, rows in [("fixed_holdout", primary["fixed_rows"]), ("walk_forward", primary["walk_rows"])]:
            for r in rows:
                writer.writerow({
                    "validation": validation,
                    "pair_id": r["pair_id"],
                    "format": r["format"],
                    "target_start_date": r["target_start_date"],
                    "accuracy": r["accuracy"],
                    "persistence_accuracy": r["persistence_accuracy"],
                    "improvement_pp": r["accuracy"] - r["persistence_accuracy"],
                })

    p = scenario_results["day2_bounded_share1"]
    reg_ci = regression["format_cluster_bootstrap"]["ci95"]
    lines = [
        "# IRL performance → next IRL field — Phase 2",
        "",
        "## Research question",
        "",
        "After accounting for how popular an archetype already was, does overperformance at one IRL major predict increased Day-1 representation at the next adjacent same-format IRL cohort?",
        "",
        "## Evidence and validation",
        "",
        f"- **{len(pairs)}** eligible adjacent same-format cohort pairs across **{len({x['format'] for x in pairs})}** formats, preserving the prior IRL-regression cohort/capture rules.",
        f"- Fixed chronology: first **{summary['sample']['fixed_split_train_pairs']}** pairs train, final **{summary['sample']['fixed_split_holdout_pairs']}** pairs test.",
        f"- Expanding walk-forward: each target after the first **{MIN_WALKFORWARD_TRAIN}** pairs is fitted only on earlier pairs.",
        "- No Online evidence and no target-tournament performance features are used.",
        "",
        "## Primary specification (declared before this target analysis)",
        "",
        "Day-2 representation lift relative to Day-1 share, +0.5 smoothed, log2 transformed, bounded to [-2,+2], and activated only for archetypes with >=1% prior cohort share. Smaller archetypes remain in the field at their persistence shares rather than being dropped.",
        "",
        "The forecasting adjustment is a single composition-preserving tilt around the previous IRL field. Positive beta means prior overperformance increases forecast share; negative beta means reversal. Shares are clipped at zero if needed and renormalised.",
        "",
        "## Descriptive performance coefficient, controlling previous share",
        "",
        f"Within-pair regression coefficient on prior share: **{fmt(regression['prior_share_coef'], 3)}**. Coefficient on bounded Day-2 performance: **{fmt(regression['performance_coef'], 3)} percentage points of next-share movement per +1 log2-lift unit**, with format-cluster bootstrap 95% CI **[{fmt(reg_ci[0],3)}, {fmt(reg_ci[1],3)}]**. This is descriptive; chronological forecasting below is the decision test.",
        "",
        "## Forecast validation",
        "",
        "| Model / sensitivity | Full-sample fit | Fixed holdout | vs persistence | Walk-forward | vs persistence | Pairs in holdout / WF |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for scenario in SCENARIOS:
        r = scenario_results[scenario["id"]]
        fh = r["fixed_holdout"]
        wf = r["walk_forward"]
        lines.append(
            f"| {'**' if scenario['primary'] else ''}{scenario['label']}{'**' if scenario['primary'] else ''} | "
            f"{fmt(r['full_sample'].get('mean_accuracy'))}% | {fmt(fh.get('mean_accuracy'))}% | "
            f"{fmt(fh.get('improvement_pp'),3)}pp | {fmt(wf.get('mean_accuracy'))}% | "
            f"{fmt(wf.get('improvement_pp'),3)}pp | {fh.get('pair_count','n/a')} / {wf.get('pair_count','n/a')} |"
        )

    primary_fixed = p["fixed_holdout"]
    primary_wf = p["walk_forward"]
    recent = p["recent_year_descriptive"]
    lines += [
        "",
        "## Primary chronological result",
        "",
        f"Primary fixed holdout: performance-adjusted **{fmt(primary_fixed.get('mean_accuracy'))}%** vs matched persistence **{fmt(primary_fixed.get('mean_persistence_accuracy'))}%** = **{fmt(primary_fixed.get('improvement_pp'),3)}pp** across **{primary_fixed.get('pair_count')}** independent target cohorts.",
        f"Primary expanding walk-forward: performance-adjusted **{fmt(primary_wf.get('mean_accuracy'))}%** vs persistence **{fmt(primary_wf.get('mean_persistence_accuracy'))}%** = **{fmt(primary_wf.get('improvement_pp'),3)}pp** across **{primary_wf.get('pair_count')}** targets.",
        "",
        "The full-sample fitted beta is **" + fmt(p["full_sample"].get("beta"), 4) + "**; fixed-training beta is **" + fmt(primary_fixed.get("beta"), 4) + "**; mean walk-forward fitted beta is **" + fmt(primary_wf.get("mean_fitted_beta"), 4) + "**. A stable positive sign would be consistent with adoption after overperformance; sign instability is evidence against a robust effect.",
        "",
        "## Recent-year descriptive sensitivity",
        "",
        f"Using only targets from {recent.get('cutoff')} onward, the primary model fits **{fmt(recent.get('mean_accuracy'))}%** vs persistence **{fmt(recent.get('mean_persistence_accuracy'))}%** ({fmt(recent.get('improvement_pp'),3)}pp) across **{recent.get('pair_count')}** pairs. This is an in-sample era sensitivity, not a new holdout claim.",
        "",
        "## Interpretation boundary",
        "",
        "**Verified:** the table above records both fitted and chronological performance against matched persistence. The primary specification was fixed from Phase 1 before this script inspected next-IRL outcomes.",
        "",
        "**Inferred:** whether IRL overperformance is a useful behavioural adoption signal depends on the sign, size and chronological stability shown above, not on the in-sample coefficient alone.",
        "",
        "**Limitation:** 36 independent adjacent cohort pairs remain a small forecasting sample. Archetype rows within a cohort are compositional and correlated; the descriptive coefficient therefore uses within-pair demeaning and a format-cluster bootstrap, while the forecasting decision is made at cohort level.",
        "",
        "## Next experiment gate",
        "",
        "Only if Phase 2 shows a credible chronological performance effect should the exact performance transform be elaborated. Regardless of sign, the next programme question can separately quantify Online movement and then test mediation: prior IRL performance -> subsequent Online adoption -> next IRL share. The combined model must compare persistence, persistence+performance, persistence+Online, and persistence+Online+performance on matched chronological targets.",
    ]
    (RESDIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
