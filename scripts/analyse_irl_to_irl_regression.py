#!/usr/bin/env python3
"""IRL-to-IRL same-format regression analysis.

Research question
-----------------
How predictive is one IRL major weekend of the next IRL major weekend in the
same legal format, and does that predictive relationship weaken with elapsed
time?

This analysis intentionally uses IRL evidence only. It does not use Online
results and does not alter the frozen archive, format tags, cohort membership,
or archetype identities.

Primary design
--------------
* Cohort = the existing overlapping-date IRL cohort from prediction-windows.
* A pair is two adjacent IRL cohorts within the same display_format.
* A pair is eligible only when every event in both adjacent cohorts has >=95%
  captured Day-1 field coverage. We do not skip over an ineligible intervening
  cohort and pretend the later cohort directly followed an earlier one.
* Events within a cohort are field-entry weighted, matching the historical IRL
  baseline aggregation.
* Persistence baseline: previous cohort distribution predicts the target.
* Pair-level decay: regress persistence Field Accuracy on days after the prior
  weekend, both overall and within-format (format fixed-effect / de-meaned).
* Archetype retention: pair-fixed-effect regression of target share on previous
  share with a share×gap interaction.
* Composition-preserving forecast regressions:
    y = m + lambda * (x - m)
  where x is the previous cohort and m is the equal-cohort mean of earlier
  eligible IRL cohorts in the same format. lambda is fitted either constant or
  as a linear function of time gap. This keeps component changes summing to 0
  before clipping/renormalisation.
* Momentum sensitivity (when two prior adjacent eligible cohorts exist):
    y = x + k * (x - x2)
* Validation: fixed chronological 70/30 holdout plus expanding walk-forward
  after 15 training pairs. All parameters for a target are fitted only on
  earlier target pairs.

Interpretation warning
----------------------
The regression coefficients describe IRL-to-IRL persistence. They are NOT the
same parameter as the IRL-vs-Online mixture weight used elsewhere in the
research. A decaying IRL-to-IRL relationship may support the qualitative idea
of stale IRL evidence, but it does not directly estimate an Online blend rule.
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
OUTDIR = ROOT / "data" / "processed" / "irl-regression"
RESDIR = ROOT / "results" / "irl-regression"

MIN_CAPTURE = 0.95
MIN_WALKFORWARD_TRAIN = 15
BOOTSTRAPS = 3000
RNG_SEED = 20260915


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


def average_distributions(distributions):
    ds = [d for d in distributions if d]
    if not ds:
        return {}
    keys = set().union(*(set(d) for d in ds))
    out = {k: mean(d.get(k, 0.0) for d in ds) for k in keys}
    return normalise_map(out)


def add_scaled(base, components):
    """Return normalised base + sum(coef * vector), clipping negatives."""
    keys = set(base)
    for _, vec in components:
        keys |= set(vec)
    out = {k: base.get(k, 0.0) for k in keys}
    for coef, vec in components:
        for k in keys:
            out[k] = out.get(k, 0.0) + coef * vec.get(k, 0.0)
    return normalise_map(out)


def diff_map(a, b):
    keys = set(a) | set(b)
    return {k: a.get(k, 0.0) - b.get(k, 0.0) for k in keys}


def solve_linear(a, b):
    """Small dense linear solver with partial pivoting; returns None if singular."""
    n = len(b)
    m = [list(map(float, a[i])) + [float(b[i])] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            return None
        if pivot != col:
            m[col], m[pivot] = m[pivot], m[col]
        div = m[col][col]
        for j in range(col, n + 1):
            m[col][j] /= div
        for r in range(n):
            if r == col:
                continue
            factor = m[r][col]
            if factor == 0:
                continue
            for j in range(col, n + 1):
                m[r][j] -= factor * m[col][j]
    return [m[i][n] for i in range(n)]


def fit_least_squares(rows, feature_fn, response_fn, weight_fn=None):
    if not rows:
        return None
    sample_features = feature_fn(rows[0])
    p = len(sample_features)
    xtx = [[0.0] * p for _ in range(p)]
    xty = [0.0] * p
    n = 0
    sse = 0.0
    obs = []
    for row in rows:
        x = [float(v) for v in feature_fn(row)]
        y = float(response_fn(row))
        w = float(weight_fn(row) if weight_fn else 1.0)
        if not math.isfinite(y) or any(not math.isfinite(v) for v in x) or w <= 0:
            continue
        n += 1
        obs.append((x, y, w))
        for i in range(p):
            xty[i] += w * x[i] * y
            for j in range(p):
                xtx[i][j] += w * x[i] * x[j]
    if n < p:
        return None
    coef = solve_linear(xtx, xty)
    if coef is None:
        return None
    ys = []
    preds = []
    for x, y, w in obs:
        pred = sum(c * v for c, v in zip(coef, x))
        sse += w * (y - pred) ** 2
        ys.append(y)
        preds.append(pred)
    ybar = mean(ys)
    sst = sum((y - ybar) ** 2 for y in ys) if ybar is not None else 0.0
    r2 = 1.0 - sse / sst if sst > 0 else None
    return {"coef": coef, "n": n, "sse": sse, "r2": r2}


def simple_regression(xs, ys):
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    xm, ym = mean(xs), mean(ys)
    den = sum((x - xm) ** 2 for x in xs)
    if den <= 1e-12:
        return None
    slope = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / den
    intercept = ym - slope * xm
    pred = [intercept + slope * x for x in xs]
    sse = sum((y - p) ** 2 for y, p in zip(ys, pred))
    sst = sum((y - ym) ** 2 for y in ys)
    r2 = 1 - sse / sst if sst > 0 else None
    return {"intercept": intercept, "slope": slope, "r2": r2, "n": len(xs)}


def pearson(xs, ys):
    if len(xs) < 2:
        return None
    xm, ym = mean(xs), mean(ys)
    num = sum((x - xm) * (y - ym) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - xm) ** 2 for x in xs))
    dy = math.sqrt(sum((y - ym) ** 2 for y in ys))
    return num / (dx * dy) if dx > 0 and dy > 0 else None


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            out[order[k]] = rank
        i = j
    return out


def end_of_iso_week(d):
    return d + timedelta(days=6 - d.weekday())


def build_cohorts():
    pack = json.loads(WINDOWS.read_text(encoding="utf-8"))
    tags = {str(e["id"]): e for e in json.loads(IRL_TAGS.read_text(encoding="utf-8"))}
    irl_counts, names = scorer.irl_decks()

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
            "event_count": len(ids),
            "event_names": [m["name"] for m in metas],
            "format": next(iter(formats)),
            "format_start_date": metas[0]["format_start_date"],
            "days_into_format": mean(float(m.get("days_into_format") or 0) for m in metas),
            "players": sum(int(m.get("players") or 0) for m in metas),
            "capture_min": min(float(m.get("field_count_ratio") or 0.0) for m in metas),
            "eligible": eligible,
            "distribution": distribution,
        })
    cohorts.sort(key=lambda c: (c["start_date"], c["cohort_id"]))
    return cohorts, names


def build_pairs(cohorts):
    by_format = defaultdict(list)
    for c in cohorts:
        by_format[c["format"]].append(c)
    pairs = []
    for fmt, seq in by_format.items():
        seq.sort(key=lambda c: (c["start_date"], c["cohort_id"]))
        eligible_history = []
        for idx, cohort in enumerate(seq):
            if cohort["eligible"]:
                eligible_history.append(cohort)
            if idx == 0:
                continue
            prev = seq[idx - 1]
            target = cohort
            # Strict adjacency: no skipping over low-capture cohorts.
            if not (prev["eligible"] and target["eligible"]):
                continue
            prior_eligible = [c for c in seq[:idx] if c["eligible"]]
            prior_mean = average_distributions([c["distribution"] for c in prior_eligible])
            prev2 = seq[idx - 2] if idx >= 2 else None
            momentum_ok = bool(prev2 and prev2["eligible"])
            gap_calendar = (date.fromisoformat(target["start_date"]) - date.fromisoformat(prev["end_date"])).days
            gap_after_week = (
                date.fromisoformat(target["start_date"])
                - end_of_iso_week(date.fromisoformat(prev["end_date"]))
            ).days
            gap_after_week = max(0, gap_after_week)
            persistence = field_accuracy(prev["distribution"], target["distribution"])
            pair = {
                "pair_id": f"{prev['cohort_id']}->{target['cohort_id']}",
                "format": fmt,
                "source_cohort": prev["cohort_id"],
                "target_cohort": target["cohort_id"],
                "source_start_date": prev["start_date"],
                "source_end_date": prev["end_date"],
                "target_start_date": target["start_date"],
                "target_end_date": target["end_date"],
                "source_names": prev["event_names"],
                "target_names": target["event_names"],
                "source_players": prev["players"],
                "target_players": target["players"],
                "source_capture_min": prev["capture_min"],
                "target_capture_min": target["capture_min"],
                "gap_calendar_days": gap_calendar,
                "gap_days": gap_after_week,
                "target_days_into_format": target["days_into_format"],
                "source": prev["distribution"],
                "target": target["distribution"],
                "prior_mean": prior_mean,
                "prev2": prev2["distribution"] if momentum_ok else {},
                "momentum_available": momentum_ok,
                "persistence_accuracy": persistence,
                "prior_eligible_cohort_count": len(prior_eligible),
            }
            pairs.append(pair)
    pairs.sort(key=lambda p: (p["target_start_date"], p["target_cohort"]))
    return pairs


def gap_bins(pairs):
    bins = [
        ("0-7", 0, 7),
        ("8-14", 8, 14),
        ("15-21", 15, 21),
        ("22-35", 22, 35),
        ("36+", 36, 10**9),
    ]
    out = []
    for label, lo, hi in bins:
        rows = [p for p in pairs if lo <= p["gap_days"] <= hi]
        if rows:
            out.append({
                "label": label,
                "pair_count": len(rows),
                "mean_gap_days": mean(p["gap_days"] for p in rows),
                "mean_persistence_accuracy": mean(p["persistence_accuracy"] for p in rows),
                "median_persistence_accuracy": median(p["persistence_accuracy"] for p in rows),
            })
    return out


def within_format_slope(pairs):
    grouped = defaultdict(list)
    for p in pairs:
        grouped[p["format"]].append(p)
    xs, ys = [], []
    for rows in grouped.values():
        if len(rows) < 2:
            continue
        gx = mean(r["gap_days"] for r in rows)
        gy = mean(r["persistence_accuracy"] for r in rows)
        for r in rows:
            xs.append(r["gap_days"] - gx)
            ys.append(r["persistence_accuracy"] - gy)
    if not xs:
        return None
    den = sum(x * x for x in xs)
    slope = sum(x * y for x, y in zip(xs, ys)) / den if den else None
    return {"slope": slope, "n": len(xs), "format_count": sum(len(v) >= 2 for v in grouped.values())}


def cluster_bootstrap_slope(pairs, within=False):
    rng = random.Random(RNG_SEED + (1 if within else 0))
    grouped = defaultdict(list)
    for p in pairs:
        grouped[p["format"]].append(p)
    formats = sorted(grouped)
    estimates = []
    for _ in range(BOOTSTRAPS):
        sampled = []
        for _j in range(len(formats)):
            fmt = rng.choice(formats)
            sampled.extend(grouped[fmt])
        if within:
            fit = within_format_slope(sampled)
            est = fit["slope"] if fit else None
        else:
            fit = simple_regression(
                [p["gap_days"] for p in sampled],
                [p["persistence_accuracy"] for p in sampled],
            )
            est = fit["slope"] if fit else None
        if est is not None and math.isfinite(est):
            estimates.append(est)
    return {
        "bootstrap_count": len(estimates),
        "ci95": [percentile(estimates, 0.025), percentile(estimates, 0.975)],
        "median": percentile(estimates, 0.5),
    }


def archetype_retention_rows(pairs, gap_center):
    rows = []
    for p in pairs:
        keys = set(p["source"]) | set(p["target"])
        if not keys:
            continue
        xmean = mean(p["source"].get(k, 0.0) for k in keys)
        ymean = mean(p["target"].get(k, 0.0) for k in keys)
        for k in keys:
            xdm = p["source"].get(k, 0.0) - xmean
            ydm = p["target"].get(k, 0.0) - ymean
            rows.append({
                "format": p["format"],
                "pair_id": p["pair_id"],
                "key": k,
                "x_dm": xdm,
                "y_dm": ydm,
                "gap_centered": p["gap_days"] - gap_center,
            })
    return rows


def fit_retention(rows):
    return fit_least_squares(
        rows,
        lambda r: [r["x_dm"], r["x_dm"] * r["gap_centered"]],
        lambda r: r["y_dm"],
    )


def bootstrap_retention(rows):
    rng = random.Random(RNG_SEED + 2)
    by_format = defaultdict(list)
    for r in rows:
        by_format[r["format"]].append(r)
    formats = sorted(by_format)
    coefs = []
    for _ in range(BOOTSTRAPS):
        sample = []
        for _j in range(len(formats)):
            fmt = rng.choice(formats)
            sample.extend(by_format[fmt])
        fit = fit_retention(sample)
        if fit:
            coefs.append(fit["coef"])
    return {
        "bootstrap_count": len(coefs),
        "beta_ci95": [percentile([c[0] for c in coefs], 0.025), percentile([c[0] for c in coefs], 0.975)],
        "gap_interaction_ci95": [percentile([c[1] for c in coefs], 0.025), percentile([c[1] for c in coefs], 0.975)],
    }


def composition_training_rows(pairs, gap_center, age_center, include_momentum=False):
    rows = []
    for p in pairs:
        m = p["prior_mean"]
        x = p["source"]
        y = p["target"]
        keys = set(m) | set(x) | set(y)
        x2 = p.get("prev2") or {}
        for k in keys:
            d = x.get(k, 0.0) - m.get(k, 0.0)
            row = {
                "pair_id": p["pair_id"],
                "format": p["format"],
                "response": y.get(k, 0.0) - m.get(k, 0.0),
                "d": d,
                "dgap": d * (p["gap_days"] - gap_center),
                "dage": d * (p["target_days_into_format"] - age_center),
                "trend": x.get(k, 0.0) - x2.get(k, 0.0) if p.get("momentum_available") else 0.0,
                "momentum_available": p.get("momentum_available", False),
            }
            if include_momentum and not row["momentum_available"]:
                continue
            rows.append(row)
    return rows


def fit_composition_model(pairs, model):
    if not pairs:
        return None
    gap_center = median(p["gap_days"] for p in pairs)
    age_center = median(p["target_days_into_format"] for p in pairs)
    rows = composition_training_rows(pairs, gap_center, age_center, include_momentum=(model in {"momentum", "combined"}))
    if model == "shrink_constant":
        fit = fit_least_squares(rows, lambda r: [r["d"]], lambda r: r["response"])
    elif model == "shrink_gap":
        fit = fit_least_squares(rows, lambda r: [r["d"], r["dgap"]], lambda r: r["response"])
    elif model == "shrink_gap_age":
        fit = fit_least_squares(rows, lambda r: [r["d"], r["dgap"], r["dage"]], lambda r: r["response"])
    elif model == "momentum":
        # Target - previous = k * trend; fit directly with previous as base.
        momentum_rows = []
        for p in pairs:
            if not p.get("momentum_available"):
                continue
            keys = set(p["source"]) | set(p["target"]) | set(p["prev2"])
            for k in keys:
                momentum_rows.append({
                    "trend": p["source"].get(k, 0.0) - p["prev2"].get(k, 0.0),
                    "response": p["target"].get(k, 0.0) - p["source"].get(k, 0.0),
                })
        fit = fit_least_squares(momentum_rows, lambda r: [r["trend"]], lambda r: r["response"])
    elif model == "combined":
        fit = fit_least_squares(rows, lambda r: [r["d"], r["trend"]], lambda r: r["response"])
    else:
        raise ValueError(model)
    if not fit:
        return None
    fit = dict(fit)
    fit["model"] = model
    fit["gap_center"] = gap_center
    fit["age_center"] = age_center
    return fit


def predict_composition(pair, fit):
    model = fit["model"]
    c = fit["coef"]
    if model == "shrink_constant":
        d = diff_map(pair["source"], pair["prior_mean"])
        return add_scaled(pair["prior_mean"], [(c[0], d)])
    if model == "shrink_gap":
        d = diff_map(pair["source"], pair["prior_mean"])
        lam = c[0] + c[1] * (pair["gap_days"] - fit["gap_center"])
        return add_scaled(pair["prior_mean"], [(lam, d)])
    if model == "shrink_gap_age":
        d = diff_map(pair["source"], pair["prior_mean"])
        lam = (
            c[0]
            + c[1] * (pair["gap_days"] - fit["gap_center"])
            + c[2] * (pair["target_days_into_format"] - fit["age_center"])
        )
        return add_scaled(pair["prior_mean"], [(lam, d)])
    if model == "momentum":
        if not pair.get("momentum_available"):
            return {}
        trend = diff_map(pair["source"], pair["prev2"])
        return add_scaled(pair["source"], [(c[0], trend)])
    if model == "combined":
        if not pair.get("momentum_available"):
            return {}
        d = diff_map(pair["source"], pair["prior_mean"])
        trend = diff_map(pair["source"], pair["prev2"])
        return add_scaled(pair["prior_mean"], [(c[0], d), (c[1], trend)])
    raise ValueError(model)


def evaluate_model(pairs, fit):
    rows = []
    for p in pairs:
        pred = predict_composition(p, fit)
        if not pred:
            continue
        rows.append({
            "pair_id": p["pair_id"],
            "target_date": p["target_start_date"],
            "accuracy": field_accuracy(pred, p["target"]),
        })
    return {
        "pair_count": len(rows),
        "mean_accuracy": mean(r["accuracy"] for r in rows),
        "median_accuracy": median(r["accuracy"] for r in rows),
        "rows": rows,
    }


def persistence_eval(pairs, require_momentum=False):
    rows = [p for p in pairs if (not require_momentum or p.get("momentum_available"))]
    return {
        "pair_count": len(rows),
        "mean_accuracy": mean(p["persistence_accuracy"] for p in rows),
        "median_accuracy": median(p["persistence_accuracy"] for p in rows),
    }


def format_mean_eval(pairs):
    vals = []
    for p in pairs:
        acc = field_accuracy(p["prior_mean"], p["target"])
        if acc is not None:
            vals.append(acc)
    return {"pair_count": len(vals), "mean_accuracy": mean(vals), "median_accuracy": median(vals)}


def walkforward(pairs):
    models = ["shrink_constant", "shrink_gap", "shrink_gap_age"]
    rows = []
    for i in range(MIN_WALKFORWARD_TRAIN, len(pairs)):
        train = pairs[:i]
        target = pairs[i]
        record = {
            "pair_id": target["pair_id"],
            "target_date": target["target_start_date"],
            "format": target["format"],
            "gap_days": target["gap_days"],
            "persistence": target["persistence_accuracy"],
            "format_mean": field_accuracy(target["prior_mean"], target["target"]),
        }
        for model in models:
            fit = fit_composition_model(train, model)
            pred = predict_composition(target, fit) if fit else {}
            record[model] = field_accuracy(pred, target["target"]) if pred else None
        # Momentum and combined are scored only where target has two clean priors.
        if target.get("momentum_available"):
            for model in ["momentum", "combined"]:
                fit = fit_composition_model(train, model)
                pred = predict_composition(target, fit) if fit else {}
                record[model] = field_accuracy(pred, target["target"]) if pred else None
        else:
            record["momentum"] = None
            record["combined"] = None
        rows.append(record)

    def summarise(key, subset=None):
        selected = [r for r in rows if r.get(key) is not None and (subset(r) if subset else True)]
        return {
            "pair_count": len(selected),
            "mean_accuracy": mean(r[key] for r in selected),
            "median_accuracy": median(r[key] for r in selected),
        }

    momentum_subset = lambda r: r.get("momentum") is not None
    return {
        "min_training_pairs": MIN_WALKFORWARD_TRAIN,
        "rows": rows,
        "persistence": summarise("persistence"),
        "format_mean": summarise("format_mean"),
        "shrink_constant": summarise("shrink_constant"),
        "shrink_gap": summarise("shrink_gap"),
        "shrink_gap_age": summarise("shrink_gap_age"),
        "momentum": summarise("momentum"),
        "combined": summarise("combined"),
        "persistence_on_momentum_subset": summarise("persistence", momentum_subset),
    }


def fixed_holdout(pairs):
    split = max(MIN_WALKFORWARD_TRAIN, int(math.floor(len(pairs) * 0.70)))
    split = min(split, len(pairs) - 1)
    train, test = pairs[:split], pairs[split:]
    out = {
        "train_pair_count": len(train),
        "test_pair_count": len(test),
        "train_end_target_date": train[-1]["target_start_date"] if train else None,
        "test_start_target_date": test[0]["target_start_date"] if test else None,
        "persistence": persistence_eval(test),
        "format_mean": format_mean_eval(test),
        "models": {},
    }
    for model in ["shrink_constant", "shrink_gap", "shrink_gap_age", "momentum", "combined"]:
        fit = fit_composition_model(train, model)
        ev = evaluate_model(test, fit) if fit else None
        out["models"][model] = {"fit": fit, "test": ev}
    momentum_test = [p for p in test if p.get("momentum_available")]
    out["persistence_on_momentum_subset"] = persistence_eval(momentum_test)
    return out


def main():
    cohorts, names = build_cohorts()
    pairs = build_pairs(cohorts)
    if len(pairs) <= MIN_WALKFORWARD_TRAIN:
        raise RuntimeError(f"Only {len(pairs)} eligible adjacent same-format pairs")

    gaps = [p["gap_days"] for p in pairs]
    accuracies = [p["persistence_accuracy"] for p in pairs]
    overall_gap_fit = simple_regression(gaps, accuracies)
    within_fit = within_format_slope(pairs)
    overall_boot = cluster_bootstrap_slope(pairs, within=False)
    within_boot = cluster_bootstrap_slope(pairs, within=True)

    gap_center = median(gaps)
    retention_rows = archetype_retention_rows(pairs, gap_center)
    retention_fit = fit_retention(retention_rows)
    retention_boot = bootstrap_retention(retention_rows)
    retention_points = {}
    if retention_fit:
        beta, interaction = retention_fit["coef"]
        for g in [0, 7, 14, 21, 28, 35]:
            retention_points[str(g)] = beta + interaction * (g - gap_center)

    all_fits = {}
    all_eval = {}
    for model in ["shrink_constant", "shrink_gap", "shrink_gap_age", "momentum", "combined"]:
        fit = fit_composition_model(pairs, model)
        all_fits[model] = fit
        all_eval[model] = evaluate_model(pairs, fit) if fit else None

    holdout = fixed_holdout(pairs)
    wf = walkforward(pairs)

    summary = {
        "research_question": "How predictive is one IRL major weekend of the next same-format IRL major weekend, and does that relationship decay with elapsed time?",
        "evidence": {
            "cohort_definition": "Existing prediction-window overlapping-date IRL cohorts",
            "pair_definition": "Adjacent cohorts within identical display_format; no skipping intervening cohorts",
            "minimum_capture_each_event": MIN_CAPTURE,
            "online_evidence_used": False,
            "event_within_cohort_weighting": "field-entry weighted",
            "cohort_count_total": len(cohorts),
            "eligible_pair_count": len(pairs),
            "format_count_in_pairs": len({p["format"] for p in pairs}),
            "date_range": [pairs[0]["source_start_date"], pairs[-1]["target_start_date"]],
        },
        "persistence_baseline": {
            "mean_accuracy": mean(accuracies),
            "median_accuracy": median(accuracies),
            "min_accuracy": min(accuracies),
            "max_accuracy": max(accuracies),
        },
        "gap_summary": {
            "median_gap_days": median(gaps),
            "mean_gap_days": mean(gaps),
            "min_gap_days": min(gaps),
            "max_gap_days": max(gaps),
            "bins": gap_bins(pairs),
            "overall_regression": overall_gap_fit,
            "overall_cluster_bootstrap": overall_boot,
            "within_format_regression": within_fit,
            "within_format_cluster_bootstrap": within_boot,
            "pearson_gap_vs_accuracy": pearson(gaps, accuracies),
            "spearman_gap_vs_accuracy": pearson(ranks(gaps), ranks(accuracies)),
        },
        "archetype_retention": {
            "model": "pair-fixed-effect target_share ~ prior_share + prior_share*gap; gap centered at median",
            "gap_center_days": gap_center,
            "observation_count": len(retention_rows),
            "fit": retention_fit,
            "cluster_bootstrap": retention_boot,
            "implied_prior_share_slope_by_gap": retention_points,
            "warning": "Descriptive compositional sensitivity; rows within a pair are not independent. Pair fixed effects and format-cluster bootstrap mitigate but do not eliminate compositional dependence.",
        },
        "composition_preserving_models_full_sample": {
            "warning": "In-sample fits only; use holdout/walk-forward for predictive conclusions.",
            "fits": all_fits,
            "evaluation": all_eval,
            "persistence": persistence_eval(pairs),
            "format_mean": format_mean_eval(pairs),
            "persistence_on_momentum_subset": persistence_eval([p for p in pairs if p.get("momentum_available")]),
        },
        "fixed_chronological_holdout": holdout,
        "expanding_walkforward": wf,
        "interpretation_boundary": "IRL-to-IRL regression measures persistence of IRL fields. Its coefficients are not IRL-vs-Online blend weights. Full-sample fits are in-sample; chronological holdout/walk-forward are the stronger prediction checks.",
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    RESDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    with (OUTDIR / "pairs.csv").open("w", newline="", encoding="utf-8") as f:
        fields = [
            "pair_id", "format", "source_cohort", "target_cohort", "source_start_date", "source_end_date",
            "target_start_date", "target_end_date", "gap_calendar_days", "gap_days", "target_days_into_format",
            "source_players", "target_players", "source_capture_min", "target_capture_min",
            "prior_eligible_cohort_count", "momentum_available", "persistence_accuracy",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for p in pairs:
            w.writerow({k: p[k] for k in fields})

    h = holdout
    wf_s = wf
    lines = [
        "# IRL-to-IRL same-format regression",
        "",
        f"Evidence: **{len(pairs)} adjacent same-format cohort pairs across {len({p['format'] for p in pairs})} formats**; every event on both sides of a retained pair has >=95% captured Day-1 field coverage.",
        "Online evidence is **not used**.",
        "",
        "## 1. Persistence baseline",
        "",
        f"Using the previous same-format IRL cohort unchanged predicts the next cohort at **{mean(accuracies):.2f}% mean Field Accuracy** (median {median(accuracies):.2f}%).",
        "",
        "## 2. Does IRL-to-IRL similarity decay with time?",
        "",
        f"Median gap after the prior IRL weekend: **{median(gaps):.1f} days** (range {min(gaps)}-{max(gaps)}).",
        f"Overall regression: **{overall_gap_fit['slope']:+.3f} accuracy points/day** ({overall_gap_fit['slope']*7:+.2f}pp per 7 days), R²={overall_gap_fit['r2']:.3f}.",
        f"95% format-cluster bootstrap CI for the overall slope: **[{overall_boot['ci95'][0]:+.3f}, {overall_boot['ci95'][1]:+.3f}] pp/day**.",
        f"Within-format (format fixed-effect) slope: **{within_fit['slope']:+.3f} pp/day** ({within_fit['slope']*7:+.2f}pp per 7 days).",
        f"95% format-cluster bootstrap CI: **[{within_boot['ci95'][0]:+.3f}, {within_boot['ci95'][1]:+.3f}] pp/day**.",
        "",
        "| Gap after prior weekend | Pairs | Mean persistence accuracy |",
        "|---|---:|---:|",
    ]
    for b in gap_bins(pairs):
        lines.append(f"| {b['label']} days | {b['pair_count']} | {b['mean_persistence_accuracy']:.2f}% |")

    lines += [
        "",
        "## 3. Archetype-share retention",
        "",
    ]
    if retention_fit:
        beta, interaction = retention_fit["coef"]
        lines += [
            f"Pair-fixed-effect regression gives a prior-share slope of **{beta:.3f}** at the median {gap_center:.1f}-day gap, with gap interaction **{interaction:+.4f} per day**.",
            f"Bootstrap 95% CI for median-gap slope: **[{retention_boot['beta_ci95'][0]:.3f}, {retention_boot['beta_ci95'][1]:.3f}]**; gap interaction CI **[{retention_boot['gap_interaction_ci95'][0]:+.4f}, {retention_boot['gap_interaction_ci95'][1]:+.4f}]**.",
            "",
            "| Gap | Implied target-vs-prior share slope |",
            "|---:|---:|",
        ]
        for g, val in retention_points.items():
            lines.append(f"| {g} days | {val:.3f} |")

    def model_holdout_row(label, key):
        entry = h["models"][key]
        test = entry.get("test") if entry else None
        return f"| {label} | {test['pair_count'] if test else 0} | {test['mean_accuracy']:.2f}% |" if test and test.get("mean_accuracy") is not None else f"| {label} | 0 | n/a |"

    lines += [
        "",
        "## 4. Fixed chronological holdout",
        "",
        f"Fit on first **{h['train_pair_count']} pairs**; evaluate on final **{h['test_pair_count']} pairs** ({h['test_start_target_date']} onward).",
        "",
        "| Model | Test pairs | Mean Field Accuracy |",
        "|---|---:|---:|",
        f"| Persistence: last IRL = next IRL | {h['persistence']['pair_count']} | **{h['persistence']['mean_accuracy']:.2f}%** |",
        f"| Earlier same-format IRL mean | {h['format_mean']['pair_count']} | {h['format_mean']['mean_accuracy']:.2f}% |",
        model_holdout_row("Regression shrinkage to format mean", "shrink_constant"),
        model_holdout_row("Gap-aware regression shrinkage", "shrink_gap"),
        model_holdout_row("Gap + format-age regression", "shrink_gap_age"),
        model_holdout_row("Two-weekend momentum", "momentum"),
        model_holdout_row("Shrinkage + momentum", "combined"),
        "",
        "Momentum models have fewer test pairs because they require two clean adjacent prior cohorts; compare them with the persistence-on-momentum-subset result in summary.json, not the full persistence row.",
        "",
        "## 5. Expanding walk-forward",
        "",
        f"After at least {MIN_WALKFORWARD_TRAIN} earlier training pairs, refit using only past pairs before each target.",
        "",
        "| Model | Pairs | Mean Field Accuracy |",
        "|---|---:|---:|",
    ]
    for key, label in [
        ("persistence", "Persistence"),
        ("format_mean", "Earlier format mean"),
        ("shrink_constant", "Regression shrinkage"),
        ("shrink_gap", "Gap-aware shrinkage"),
        ("shrink_gap_age", "Gap + format-age shrinkage"),
        ("momentum", "Two-weekend momentum"),
        ("combined", "Shrinkage + momentum"),
    ]:
        row = wf_s[key]
        if row.get("mean_accuracy") is not None:
            lines.append(f"| {label} | {row['pair_count']} | {row['mean_accuracy']:.2f}% |")

    lines += [
        "",
        "## Interpretation boundary",
        "",
        "Full-sample coefficients and model rankings are in-sample. The fixed chronological holdout and expanding walk-forward are the stronger checks.",
        "IRL-to-IRL retention/decay is **not** an IRL-vs-Online blend weight. A negative time interaction can support the idea that old IRL evidence becomes stale, but it does not directly tell us how much Online weight to assign.",
    ]
    (RESDIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "pairs": len(pairs),
        "formats": len({p['format'] for p in pairs}),
        "persistence_mean": mean(accuracies),
        "gap_slope_per_day": overall_gap_fit["slope"],
        "within_format_gap_slope_per_day": within_fit["slope"],
        "holdout": {
            "persistence": h["persistence"]["mean_accuracy"],
            "shrink_constant": h["models"]["shrink_constant"]["test"]["mean_accuracy"],
            "shrink_gap": h["models"]["shrink_gap"]["test"]["mean_accuracy"],
            "shrink_gap_age": h["models"]["shrink_gap_age"]["test"]["mean_accuracy"],
        },
        "walkforward": {k: wf_s[k]["mean_accuracy"] for k in ["persistence", "shrink_constant", "shrink_gap", "shrink_gap_age"]},
    }, indent=2))


if __name__ == "__main__":
    main()
