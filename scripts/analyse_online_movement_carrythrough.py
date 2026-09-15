#!/usr/bin/env python3
"""Phase 3: previous IRL -> subsequent Online movement -> next IRL movement.

The primary model estimates one interpretable carry-through parameter alpha:
    next = previous_IRL + alpha * (subsequent_Online - previous_IRL)
         = (1-alpha) * previous_IRL + alpha * subsequent_Online

Thus alpha=0 is persistence and alpha=1 is Online-only.  The fitted raw alpha is
reported; forecasting clips alpha to [0,1] so every prediction is a valid
composition without needing archetype-level clipping.

Time and Online-evidence-volume are tested separately as one-interaction
sensitivities, not as a multi-parameter search grid.
"""
from __future__ import annotations

import json
import math
import random
import statistics
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import score_baseline_models as scorer

ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "data" / "processed" / "model-results" / "baselines.json"
WINDOWS = ROOT / "data" / "processed" / "prediction-windows" / "windows.json"
IRL_TAGS = ROOT / "data" / "processed" / "format-tags" / "irl-events.json"
OUTDIR = ROOT / "data" / "processed" / "online-movement-carrythrough"
RESDIR = ROOT / "results" / "online-movement-carrythrough"

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
    f = pos - lo
    return vals[lo] * (1 - f) + vals[hi] * f


def field_accuracy(pred, actual):
    keys = set(pred) | set(actual)
    l1 = sum(abs(pred.get(k, 0.0) - actual.get(k, 0.0)) for k in keys)
    return 100.0 * max(0.0, 1.0 - 0.5 * l1)


def blend(previous, online, alpha):
    alpha = max(0.0, min(1.0, float(alpha)))
    keys = set(previous) | set(online)
    out = {k: (1.0 - alpha) * previous.get(k, 0.0) + alpha * online.get(k, 0.0) for k in keys}
    total = sum(out.values())
    return {k: v / total for k, v in out.items()} if total else {}


def solve_linear(a, b):
    n = len(b)
    m = [list(map(float, a[i])) + [float(b[i])] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-14:
            return None
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
            raise RuntimeError(f"Cohort {c['cohort_id']} spans formats: {formats}")
        counts = Counter()
        for eid in ids:
            counts.update(irl_counts.get(eid, Counter()))
        distribution = scorer.normalise(counts)
        cohorts.append({
            "cohort_id": c["cohort_id"],
            "start_date": c["start_date"],
            "end_date": c["end_date"],
            "event_ids": ids,
            "format": next(iter(formats)),
            "eligible": all(float(m.get("field_count_ratio") or 0.0) >= MIN_CAPTURE for m in metas),
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
        for i in range(1, len(seq)):
            source, target = seq[i - 1], seq[i]
            if not (source["eligible"] and target["eligible"]):
                continue
            pairs.append({
                "pair_id": f"{source['cohort_id']}->{target['cohort_id']}",
                "format": fmt,
                "source_cohort": source["cohort_id"],
                "target_cohort": target["cohort_id"],
                "source_event_ids": source["event_ids"],
                "target_event_ids": target["event_ids"],
                "source_start_date": source["start_date"],
                "source_end_date": source["end_date"],
                "target_start_date": target["start_date"],
                "source": source["distribution"],
                "target": target["distribution"],
                "persistence_accuracy": field_accuracy(source["distribution"], target["distribution"]),
            })
    pairs.sort(key=lambda p: (p["target_start_date"], p["target_cohort"]))
    return pairs


def attach_online_evidence(pairs):
    baseline = json.loads(BASELINES.read_text(encoding="utf-8"))
    targets = baseline.get("targets", [])
    target_rows = defaultdict(list)
    for t in targets:
        target_rows[str(t.get("cohort_id"))].append(t)
    online_counts, _ = scorer.online_decks()

    diagnostics = []
    for pair in pairs:
        rows = target_rows.get(pair["target_cohort"], [])
        matching = [r for r in rows if str(r.get("latest_prior_cohort_id")) == pair["source_cohort"]]
        if not matching:
            pair["online"] = None
            pair["online_event_ids"] = []
            pair["online_event_count"] = 0
            pair["online_named_entries"] = 0
            pair["days_since_major"] = None
            diagnostics.append({"pair_id": pair["pair_id"], "status": "no_matching_baseline_target"})
            continue

        id_sets = []
        day_values = set()
        for row in matching:
            model = (row.get("models") or {}).get("fifty_fifty") or {}
            ids = tuple(sorted(str(x) for x in model.get("online_event_ids") or []))
            id_sets.append(ids)
            if row.get("days_since_major") is not None:
                day_values.add(int(row["days_since_major"]))
        unique_sets = {x for x in id_sets}
        if len(unique_sets) > 1:
            raise RuntimeError(f"Target cohort {pair['target_cohort']} has inconsistent Online evidence cutoffs: {unique_sets}")
        if len(day_values) > 1:
            raise RuntimeError(f"Target cohort {pair['target_cohort']} has inconsistent days_since_major: {day_values}")

        ids = list(id_sets[0]) if id_sets else []
        counts = scorer.aggregate(ids, online_counts)
        online = scorer.normalise(counts) if ids else {}
        pair["online"] = online or None
        pair["online_event_ids"] = ids
        pair["online_event_count"] = len(ids)
        pair["online_named_entries"] = int(sum(counts.values()))
        pair["days_since_major"] = next(iter(day_values)) if day_values else None
        diagnostics.append({
            "pair_id": pair["pair_id"],
            "status": "ok" if online else "no_online_since_major",
            "online_event_count": len(ids),
            "online_named_entries": int(sum(counts.values())),
            "days_since_major": pair["days_since_major"],
        })
    return diagnostics


def model_features(pair, kind):
    days = float(pair["days_since_major"] or 0.0)
    volume = max(1.0, float(pair["online_named_entries"] or 0.0))
    if kind == "constant":
        return [1.0]
    if kind == "time":
        return [1.0, days / 7.0]
    if kind == "volume":
        return [1.0, math.log10(volume / 1000.0)]
    raise ValueError(kind)


def fit_carrythrough(pairs, kind):
    """Fit d_i = alpha(pair) * online_movement_i with equal pair weight."""
    usable = [p for p in pairs if p.get("online")]
    if not usable:
        return None
    p_dim = len(model_features(usable[0], kind))
    xtx = [[0.0] * p_dim for _ in range(p_dim)]
    xty = [0.0] * p_dim
    used = 0
    for pair in usable:
        cov = model_features(pair, kind)
        keys = set(pair["source"]) | set(pair["online"]) | set(pair["target"])
        if not keys:
            continue
        scale = 1.0 / len(keys)
        for slug in keys:
            movement_online = pair["online"].get(slug, 0.0) - pair["source"].get(slug, 0.0)
            movement_target = pair["target"].get(slug, 0.0) - pair["source"].get(slug, 0.0)
            xs = [movement_online * c for c in cov]
            for i in range(p_dim):
                xty[i] += scale * xs[i] * movement_target
                for j in range(p_dim):
                    xtx[i][j] += scale * xs[i] * xs[j]
        used += 1
    coef = solve_linear(xtx, xty)
    return {"coef": coef, "pair_count": used} if coef is not None else None


def alpha_for(pair, fit, kind):
    raw = sum(c * x for c, x in zip(fit["coef"], model_features(pair, kind)))
    return raw, max(0.0, min(1.0, raw))


def existing_decay_alpha(pair):
    # Existing research benchmark: IRL 70%, decays 2pp/day to 30% floor.
    days = float(pair["days_since_major"] or 0.0)
    irl_weight = max(0.30, min(0.70, 0.70 - 0.02 * days))
    return 1.0 - irl_weight


def score_model(pairs, fit=None, kind="constant", fixed_alpha=None, existing_decay=False):
    rows = []
    for pair in pairs:
        if not pair.get("online"):
            continue
        if existing_decay:
            raw_alpha = alpha = existing_decay_alpha(pair)
        elif fixed_alpha is not None:
            raw_alpha = alpha = float(fixed_alpha)
        else:
            raw_alpha, alpha = alpha_for(pair, fit, kind)
        pred = blend(pair["source"], pair["online"], alpha)
        rows.append({
            "pair_id": pair["pair_id"],
            "format": pair["format"],
            "target_start_date": pair["target_start_date"],
            "days_since_major": pair["days_since_major"],
            "online_event_count": pair["online_event_count"],
            "online_named_entries": pair["online_named_entries"],
            "raw_alpha": raw_alpha,
            "forecast_alpha": alpha,
            "accuracy": field_accuracy(pred, pair["target"]),
            "persistence_accuracy": pair["persistence_accuracy"],
            "online_only_accuracy": field_accuracy(pair["online"], pair["target"]),
            "fifty_accuracy": field_accuracy(blend(pair["source"], pair["online"], 0.5), pair["target"]),
            "existing_decay_accuracy": field_accuracy(blend(pair["source"], pair["online"], existing_decay_alpha(pair)), pair["target"]),
        })
    return rows


def summarise_scores(rows):
    if not rows:
        return {}
    acc = mean(r["accuracy"] for r in rows)
    persistence = mean(r["persistence_accuracy"] for r in rows)
    existing = mean(r["existing_decay_accuracy"] for r in rows)
    return {
        "pair_count": len(rows),
        "format_count": len({r["format"] for r in rows}),
        "mean_accuracy": acc,
        "mean_persistence_accuracy": persistence,
        "improvement_vs_persistence_pp": acc - persistence,
        "mean_existing_decay_accuracy": existing,
        "improvement_vs_existing_decay_pp": acc - existing,
        "mean_online_only_accuracy": mean(r["online_only_accuracy"] for r in rows),
        "mean_fifty_accuracy": mean(r["fifty_accuracy"] for r in rows),
        "mean_forecast_alpha": mean(r["forecast_alpha"] for r in rows),
        "median_forecast_alpha": median(r["forecast_alpha"] for r in rows),
    }


def evaluate_chronologically(all_pairs, kind):
    split = int(math.floor(0.70 * len(all_pairs)))
    train = all_pairs[:split]
    holdout = all_pairs[split:]
    fixed_fit = fit_carrythrough(train, kind)
    fixed_rows = score_model(holdout, fixed_fit, kind) if fixed_fit else []

    walk_rows = []
    fitted = []
    for i, target in enumerate(all_pairs):
        if i < MIN_WALKFORWARD_TRAIN or not target.get("online"):
            continue
        fit = fit_carrythrough(all_pairs[:i], kind)
        if not fit:
            continue
        rows = score_model([target], fit, kind)
        if rows:
            rows[0]["fit_coef"] = fit["coef"]
            walk_rows.extend(rows)
            fitted.append(fit["coef"])

    full_fit = fit_carrythrough(all_pairs, kind)
    full_rows = score_model(all_pairs, full_fit, kind) if full_fit else []
    return {
        "kind": kind,
        "full_sample": {"fit": full_fit, **summarise_scores(full_rows)},
        "fixed_holdout": {
            "global_train_pairs": split,
            "global_holdout_pairs": len(all_pairs) - split,
            "fit": fixed_fit,
            **summarise_scores(fixed_rows),
        },
        "walk_forward": {
            "minimum_global_prior_pairs": MIN_WALKFORWARD_TRAIN,
            "fits": fitted,
            **summarise_scores(walk_rows),
        },
        "fixed_rows": fixed_rows,
        "walk_rows": walk_rows,
    }


def fit_interpretive_regression(pairs):
    """Within-pair Δnext ~ prior_share + Δonline, equal total weight per pair."""
    rows = []
    for pair in pairs:
        if not pair.get("online"):
            continue
        keys = sorted(set(pair["source"]) | set(pair["online"]) | set(pair["target"]))
        local = []
        for slug in keys:
            local.append({
                "x": 100.0 * pair["source"].get(slug, 0.0),
                "m": 100.0 * (pair["online"].get(slug, 0.0) - pair["source"].get(slug, 0.0)),
                "y": 100.0 * (pair["target"].get(slug, 0.0) - pair["source"].get(slug, 0.0)),
            })
        mx, mm, my = mean(r["x"] for r in local), mean(r["m"] for r in local), mean(r["y"] for r in local)
        w = 1.0 / len(local)
        for r in local:
            rows.append({
                "pair_id": pair["pair_id"], "format": pair["format"], "target_start_date": pair["target_start_date"],
                "x": r["x"] - mx, "m": r["m"] - mm, "y": r["y"] - my, "weight": w,
            })

    def fit(rs):
        a11 = a12 = a22 = b1 = b2 = 0.0
        for r in rs:
            w, x, m, y = r["weight"], r["x"], r["m"], r["y"]
            a11 += w * x * x
            a12 += w * x * m
            a22 += w * m * m
            b1 += w * x * y
            b2 += w * m * y
        coef = solve_linear([[a11, a12], [a12, a22]], [b1, b2])
        if coef is None:
            return None
        return {"prior_share_coef": coef[0], "online_movement_coef": coef[1]}

    base = fit(rows)
    base.update({"row_count": len(rows), "pair_count": len({r['pair_id'] for r in rows}), "format_count": len({r['format'] for r in rows})})

    by_format = defaultdict(list)
    for r in rows:
        by_format[r["format"]].append(r)
    formats = sorted(by_format)
    rng = random.Random(RNG_SEED)
    coefs = []
    for _ in range(BOOTSTRAPS):
        boot = []
        for _j in formats:
            boot.extend(by_format[rng.choice(formats)])
        f = fit(boot)
        if f:
            coefs.append(f["online_movement_coef"])
    base["format_cluster_bootstrap"] = {
        "iterations": len(coefs),
        "ci95": [percentile(coefs, 0.025), percentile(coefs, 0.975)],
        "median": median(coefs),
    }
    return base


def descriptive_group_fit(pairs, label_fn):
    groups = defaultdict(list)
    for p in pairs:
        if p.get("online"):
            groups[label_fn(p)].append(p)
    out = {}
    for label, rows in sorted(groups.items()):
        fit = fit_carrythrough(rows, "constant")
        scores = score_model(rows, fit, "constant") if fit else []
        out[str(label)] = {
            "pair_count": len(rows),
            "fit_raw_alpha": fit["coef"][0] if fit else None,
            **summarise_scores(scores),
        }
    return out


def strip_eval(x):
    return {k: v for k, v in x.items() if k not in {"fixed_rows", "walk_rows"}}


def fmt(x, digits=3):
    return "n/a" if x is None else f"{x:.{digits}f}"


def main():
    cohorts = build_cohorts()
    pairs = build_pairs(cohorts)
    if len(pairs) != 36:
        raise RuntimeError(f"Expected 36 strict adjacent same-format pairs, got {len(pairs)}")
    diagnostics = attach_online_evidence(pairs)
    complete = [p for p in pairs if p.get("online")]
    if not complete:
        raise RuntimeError("No adjacent pairs have subsequent Online evidence")

    eval_constant = evaluate_chronologically(pairs, "constant")
    eval_time = evaluate_chronologically(pairs, "time")
    eval_volume = evaluate_chronologically(pairs, "volume")

    regression = fit_interpretive_regression(pairs)
    latest = max(date.fromisoformat(p["target_start_date"]) for p in complete)
    recent_cut = latest - timedelta(days=365)
    recent_pairs = [p for p in complete if date.fromisoformat(p["target_start_date"]) >= recent_cut]
    older_pairs = [p for p in complete if date.fromisoformat(p["target_start_date"]) < recent_cut]

    gaps = descriptive_group_fit(
        complete,
        lambda p: "0-7d" if p["days_since_major"] <= 7 else ("8-14d" if p["days_since_major"] <= 14 else "15+d"),
    )
    volume_median = median(p["online_named_entries"] for p in complete)
    volumes = descriptive_group_fit(complete, lambda p: "low" if p["online_named_entries"] <= volume_median else "high")
    eras = {
        "older": descriptive_group_fit(older_pairs, lambda p: "older").get("older", {}),
        "recent_year": descriptive_group_fit(recent_pairs, lambda p: "recent_year").get("recent_year", {}),
    }

    # Matched simple comparator scores on every complete pair.
    existing_rows = score_model(complete, existing_decay=True)
    fifty_rows = score_model(complete, fixed_alpha=0.5)
    online_rows = score_model(complete, fixed_alpha=1.0)

    summary = {
        "phase": 3,
        "question": "How much of archetype movement from the previous IRL field into subsequent Online play carries through to the next adjacent same-format IRL field?",
        "sample": {
            "all_eligible_adjacent_pairs": len(pairs),
            "pairs_with_subsequent_online_evidence": len(complete),
            "pairs_without_subsequent_online_evidence": len(pairs) - len(complete),
            "formats_with_online_evidence": len({p["format"] for p in complete}),
            "target_start": min(p["target_start_date"] for p in complete),
            "target_end": max(p["target_start_date"] for p in complete),
            "median_online_event_count": median(p["online_event_count"] for p in complete),
            "median_online_named_entries": volume_median,
            "median_days_since_major": median(p["days_since_major"] for p in complete),
        },
        "primary_model": {
            "definition": "next = previous_IRL + alpha * (subsequent_Online - previous_IRL)",
            "interpretation": "alpha is the fraction of Online movement carried into the next IRL forecast; forecast alpha is clipped to [0,1]",
            "validation": "fixed global 25/11 chronological split plus expanding walk-forward after 15 global prior pairs",
        },
        "interpretive_regression": regression,
        "constant_carrythrough": strip_eval(eval_constant),
        "time_interaction": strip_eval(eval_time),
        "volume_interaction": strip_eval(eval_volume),
        "descriptive_gap_groups": gaps,
        "descriptive_volume_groups": volumes,
        "descriptive_era_groups": eras,
        "matched_complete_pair_comparators": {
            "persistence": mean(r["persistence_accuracy"] for r in existing_rows),
            "online_only": mean(r["online_only_accuracy"] for r in online_rows),
            "fifty_fifty": mean(r["fifty_accuracy"] for r in fifty_rows),
            "existing_decay": mean(r["existing_decay_accuracy"] for r in existing_rows),
        },
        "diagnostics": diagnostics,
        "notes": [
            "Online evidence comes from the frozen baseline's same-format events strictly after the previous major's ISO-week end and before the target cutoff.",
            "The constant carry-through model is primary; time and volume each add only one interaction coefficient.",
            "Grouped time/volume/era fits are descriptive and not model-selection evidence.",
            "No prior-IRL performance signal is used in Phase 3; mediation is deferred to Phase 4.",
        ],
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    RESDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Preserve primary chronological rows for later matched Phase-4 comparison.
    rows_out = []
    for validation, rows in [("fixed_holdout", eval_constant["fixed_rows"]), ("walk_forward", eval_constant["walk_rows"])]:
        for r in rows:
            rows_out.append({"validation": validation, **r})
    (OUTDIR / "primary-validation.json").write_text(json.dumps(rows_out, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    c = summary["constant_carrythrough"]
    t = summary["time_interaction"]
    v = summary["volume_interaction"]
    ci = regression["format_cluster_bootstrap"]["ci95"]
    lines = [
        "# Online movement carry-through — Phase 3",
        "",
        "## Research question",
        "",
        "How much of the archetype movement observed Online after one IRL major carries through into the Day-1 field at the next adjacent same-format IRL major?",
        "",
        "## Evidence",
        "",
        f"- Strict adjacent same-format IRL pairs: **{len(pairs)}**; pairs with post-major/pre-target Online evidence: **{len(complete)}** across **{len({p['format'] for p in complete})}** formats.",
        f"- Median evidence per complete pair: **{summary['sample']['median_online_event_count']:.0f} Online events / {summary['sample']['median_online_named_entries']:.0f} named entries**.",
        f"- Median elapsed time after the previous major weekend: **{summary['sample']['median_days_since_major']:.1f} days**.",
        "",
        "## Descriptive relationship, controlling previous share",
        "",
        f"Within-pair regression coefficient on previous share: **{fmt(regression['prior_share_coef'])}**; coefficient on Online movement: **{fmt(regression['online_movement_coef'])}**. The latter is directly interpretable as approximate carry-through after controlling prior popularity. Format-cluster bootstrap 95% CI: **[{fmt(ci[0])}, {fmt(ci[1])}]**.",
        "",
        "## Primary carry-through model",
        "",
        "`next = previous IRL + alpha × (subsequent Online - previous IRL)`",
        "",
        f"Full-sample fitted raw alpha: **{fmt(c['full_sample']['fit']['coef'][0])}**. Full-sample Field Accuracy **{fmt(c['full_sample']['mean_accuracy'],2)}%** vs persistence **{fmt(c['full_sample']['mean_persistence_accuracy'],2)}%** ({fmt(c['full_sample']['improvement_vs_persistence_pp'])}pp) and existing decay benchmark **{fmt(c['full_sample']['mean_existing_decay_accuracy'],2)}%** ({fmt(c['full_sample']['improvement_vs_existing_decay_pp'])}pp).",
        "",
        "## Chronological validation",
        "",
        "| Model | Fixed holdout | vs persistence | vs existing decay | Walk-forward | vs persistence | vs existing decay |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| **Constant carry-through** | {fmt(c['fixed_holdout'].get('mean_accuracy'),2)}% | {fmt(c['fixed_holdout'].get('improvement_vs_persistence_pp'))}pp | {fmt(c['fixed_holdout'].get('improvement_vs_existing_decay_pp'))}pp | {fmt(c['walk_forward'].get('mean_accuracy'),2)}% | {fmt(c['walk_forward'].get('improvement_vs_persistence_pp'))}pp | {fmt(c['walk_forward'].get('improvement_vs_existing_decay_pp'))}pp |",
        f"| Time interaction | {fmt(t['fixed_holdout'].get('mean_accuracy'),2)}% | {fmt(t['fixed_holdout'].get('improvement_vs_persistence_pp'))}pp | {fmt(t['fixed_holdout'].get('improvement_vs_existing_decay_pp'))}pp | {fmt(t['walk_forward'].get('mean_accuracy'),2)}% | {fmt(t['walk_forward'].get('improvement_vs_persistence_pp'))}pp | {fmt(t['walk_forward'].get('improvement_vs_existing_decay_pp'))}pp |",
        f"| Evidence-volume interaction | {fmt(v['fixed_holdout'].get('mean_accuracy'),2)}% | {fmt(v['fixed_holdout'].get('improvement_vs_persistence_pp'))}pp | {fmt(v['fixed_holdout'].get('improvement_vs_existing_decay_pp'))}pp | {fmt(v['walk_forward'].get('mean_accuracy'),2)}% | {fmt(v['walk_forward'].get('improvement_vs_persistence_pp'))}pp | {fmt(v['walk_forward'].get('improvement_vs_existing_decay_pp'))}pp |",
        "",
        f"Primary fixed-training raw alpha coefficients: **{c['fixed_holdout']['fit']['coef']}**. Primary walk-forward mean forecast alpha: **{fmt(c['walk_forward'].get('mean_forecast_alpha'))}** across **{c['walk_forward'].get('pair_count')}** targets.",
        "",
        "## Does carry-through change with time?",
        "",
        f"Full-sample time model coefficients `[alpha_at_0_days, change_per_week]`: **{t['full_sample']['fit']['coef']}**.",
        "",
        "Descriptive constant-alpha fits by elapsed time:",
        "",
        "| Gap | Pairs | Raw alpha | Accuracy |",
        "|---|---:|---:|---:|",
    ]
    for label, x in gaps.items():
        lines.append(f"| {label} | {x.get('pair_count')} | {fmt(x.get('fit_raw_alpha'))} | {fmt(x.get('mean_accuracy'),2)}% |")
    lines += [
        "",
        "## Does carry-through change with Online evidence volume?",
        "",
        f"Full-sample volume model coefficients `[alpha_at_1000_entries, change_per_log10_volume]`: **{v['full_sample']['fit']['coef']}**. Median split is **{volume_median:.0f} named Online entries**.",
        "",
        "| Evidence volume | Pairs | Raw alpha | Accuracy |",
        "|---|---:|---:|---:|",
    ]
    for label, x in volumes.items():
        lines.append(f"| {label} | {x.get('pair_count')} | {fmt(x.get('fit_raw_alpha'))} | {fmt(x.get('mean_accuracy'),2)}% |")
    lines += [
        "",
        "## Era sensitivity",
        "",
        f"Older complete pairs: **{eras['older'].get('pair_count','n/a')}**, fitted alpha **{fmt(eras['older'].get('fit_raw_alpha'))}**. Recent-year pairs from {recent_cut.isoformat()}: **{eras['recent_year'].get('pair_count','n/a')}**, fitted alpha **{fmt(eras['recent_year'].get('fit_raw_alpha'))}**.",
        "",
        "## Interpretation boundary",
        "",
        "**Verified:** the fitted Online-movement coefficient and chronological scores above quantify the historical carry-through relationship on frozen pre-target evidence.",
        "",
        "**Inferred:** a stable alpha between 0 and 1 supports the interpretation that the next IRL field partially follows post-major Online adoption rather than either ignoring Online movement or copying it wholesale. Time/volume interactions should only be retained if they improve chronological validation, not merely because their full-sample coefficient is non-zero.",
        "",
        "**Limitation:** this phase deliberately omits prior-IRL performance. It therefore does not distinguish Online movement caused by IRL performance from Online movement caused by other metagame forces.",
        "",
        "## Next experiment",
        "",
        "Phase 4 should put the predeclared Phase-2 performance signal and the Phase-3 Online movement signal into the same matched chronological forecasts: persistence; persistence+performance; persistence+Online; persistence+Online+performance. This is the mediation test.",
    ]
    (RESDIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
