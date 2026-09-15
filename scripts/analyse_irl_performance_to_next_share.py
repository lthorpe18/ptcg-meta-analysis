#!/usr/bin/env python3
"""Phase 2: does prior-IRL performance predict next same-format IRL share change?

Uses only the already-audited IRL performance evidence and the existing IRL cohort
structure. No Online evidence enters this experiment.

Primary forecast comparison:
  persistence: next = previous IRL field
  persistence + performance: previous field tilted by prior Day-2 relative lift

The performance tilt is composition-preserving before clipping:
  a_i = x_i * (s_i - sum_j x_j s_j)
  pred_i = x_i + beta * a_i
where x is previous IRL share and s is the prior performance signal.

Validation is chronological: fixed early-train/later-holdout and expanding
walk-forward. Multi-event weekends remain cohorts and each pair contributes equal
weight when fitting beta.
"""
from __future__ import annotations

import csv
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import score_baseline_models as scorer

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ROOT / "data/processed/prediction-windows/windows.json"
IRL_TAGS = ROOT / "data/processed/format-tags/irl-events.json"
PERF_CSV = ROOT / "data/processed/irl-performance/performance-signals.csv"
OUT = ROOT / "data/processed/irl-performance/phase2-summary.json"
PAIR_CSV = ROOT / "data/processed/irl-performance/phase2-pairs.csv"
REPORT = ROOT / "results/irl-performance/PHASE2.md"

MIN_CAPTURE = 0.95
MIN_WALKFORWARD_TRAIN = 15
BOOTSTRAPS = 3000
RNG_SEED = 20260915


def mean(xs):
    xs = list(xs)
    return statistics.fmean(xs) if xs else None


def percentile(xs, p):
    vals = sorted(v for v in xs if v is not None and math.isfinite(v))
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


def fmt(x, n=2):
    return "n/a" if x is None else f"{x:.{n}f}"


def normalise(values):
    clean = {k: max(0.0, float(v)) for k, v in values.items() if float(v) > 0}
    total = sum(clean.values())
    return {k: v / total for k, v in clean.items()} if total else {}


def field_accuracy(pred, actual):
    keys = set(pred) | set(actual)
    l1 = sum(abs(pred.get(k, 0.0) - actual.get(k, 0.0)) for k in keys)
    return 100.0 * max(0.0, 1.0 - 0.5 * l1)


def load_perf_rows():
    rows = []
    with PERF_CSV.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            def num(name):
                v = r.get(name)
                return None if v in (None, "") else float(v)
            rows.append({
                "event_id": str(r["event_id"]),
                "slug": r["slug"],
                "day1_entries": int(float(r["day1_entries"])),
                "day2_entries": num("day2_entries"),
                "day2_expected": num("day2_expected"),
                "day2_raw": num("day2_log2_lift_smoothed_05"),
                "day2_bounded": num("day2_log2_lift_bounded_2"),
                "points": num("points_rate_centered_pp"),
                "top32": num("top32"),
                "day1_share_pct": num("day1_share_pct"),
                "winner": num("winner"),
            })
    return rows


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
            raise RuntimeError(f"cohort {c['cohort_id']} spans formats: {formats}")
        counts = Counter()
        for event_id in ids:
            counts.update(irl_counts.get(event_id, Counter()))
        cohorts.append({
            "cohort_id": c["cohort_id"],
            "start_date": c["start_date"],
            "end_date": c["end_date"],
            "event_ids": ids,
            "format": next(iter(formats)),
            "eligible": all(float(m.get("field_count_ratio") or 0) >= MIN_CAPTURE for m in metas),
            "distribution": scorer.normalise(counts),
            "players": sum(int(m.get("players") or 0) for m in metas),
        })
    cohorts.sort(key=lambda x: (x["start_date"], x["cohort_id"]))
    return cohorts, names


def aggregate_performance(cohort, perf_rows):
    by_event_slug = {(r["event_id"], r["slug"]): r for r in perf_rows}
    keys = set(cohort["distribution"])
    out = {}
    for slug in keys:
        rows = [by_event_slug[(eid, slug)] for eid in cohort["event_ids"] if (eid, slug) in by_event_slug]
        if not rows:
            continue
        obs2 = sum(r["day2_entries"] or 0.0 for r in rows if r["day2_expected"] is not None)
        exp2 = sum(r["day2_expected"] or 0.0 for r in rows if r["day2_expected"] is not None)
        d2 = math.log2((obs2 + 0.5) / (exp2 + 0.5)) if exp2 >= 0 else None
        d2b = max(-2.0, min(2.0, d2)) if d2 is not None else None
        point_rows = [(r["points"], r["day1_entries"]) for r in rows if r["points"] is not None and r["day1_entries"] > 0]
        points = (sum(v * w for v, w in point_rows) / sum(w for _, w in point_rows)) if point_rows else None
        top_rows = [r for r in rows if r["top32"] is not None and r["day1_share_pct"] is not None]
        # Only use Top-32 if every source event contributed complete evidence for this archetype.
        top32 = None
        if len(top_rows) == len(rows):
            obs32 = sum(r["top32"] for r in top_rows)
            exp32 = sum(32.0 * r["day1_share_pct"] / 100.0 for r in top_rows)
            top32 = math.log2((obs32 + 0.5) / (exp32 + 0.5))
        out[slug] = {
            "day2_raw": d2,
            "day2_bounded": d2b,
            "points": points,
            "top32": top32,
            "winner": 1.0 if any((r["winner"] or 0) > 0 for r in rows) else 0.0,
        }
    return out


def build_pairs(cohorts, perf_rows):
    perf_by_cohort = {c["cohort_id"]: aggregate_performance(c, perf_rows) for c in cohorts}
    by_format = defaultdict(list)
    for c in cohorts:
        by_format[c["format"]].append(c)
    pairs = []
    for fmt, seq in by_format.items():
        seq.sort(key=lambda c: (c["start_date"], c["cohort_id"]))
        for i in range(1, len(seq)):
            prev, target = seq[i - 1], seq[i]
            if not (prev["eligible"] and target["eligible"]):
                continue
            pairs.append({
                "pair_id": f"{prev['cohort_id']}->{target['cohort_id']}",
                "format": fmt,
                "source_cohort": prev["cohort_id"],
                "target_cohort": target["cohort_id"],
                "source_date": prev["start_date"],
                "target_date": target["start_date"],
                "source": prev["distribution"],
                "target": target["distribution"],
                "performance": perf_by_cohort.get(prev["cohort_id"], {}),
                "persistence_accuracy": field_accuracy(prev["distribution"], target["distribution"]),
            })
    pairs.sort(key=lambda p: (p["target_date"], p["pair_id"]))
    return pairs


VARIANTS = {
    "day2_bounded_all": ("day2_bounded", 0.0),
    "day2_bounded_0_5": ("day2_bounded", 0.005),
    "day2_bounded_1": ("day2_bounded", 0.01),
    "day2_bounded_2": ("day2_bounded", 0.02),
    "day2_raw_1": ("day2_raw", 0.01),
    "points_1": ("points", 0.01),
    "top32_1": ("top32", 0.01),
    "winner_1": ("winner", 0.01),
}
PRIMARY = "day2_bounded_all"


def signal_map(pair, variant):
    field, threshold = VARIANTS[variant]
    out = {}
    for k, share in pair["source"].items():
        if share < threshold:
            out[k] = 0.0
        else:
            v = pair["performance"].get(k, {}).get(field)
            out[k] = 0.0 if v is None or not math.isfinite(v) else float(v)
    return out


def tilt_map(pair, variant):
    x = pair["source"]
    s = signal_map(pair, variant)
    sbar = sum(x.get(k, 0.0) * s.get(k, 0.0) for k in x)
    return {k: x[k] * (s.get(k, 0.0) - sbar) for k in x}


def fit_beta(pairs, variant):
    num = 0.0
    den = 0.0
    for p in pairs:
        tilt = tilt_map(p, variant)
        keys = set(p["source"]) | set(p["target"])
        if not keys:
            continue
        w = 1.0 / len(keys)  # equal pair influence despite different archetype counts
        for k in keys:
            a = tilt.get(k, 0.0)
            y = p["target"].get(k, 0.0) - p["source"].get(k, 0.0)
            num += w * a * y
            den += w * a * a
    return num / den if den > 1e-15 else 0.0


def predict(pair, variant, beta):
    tilt = tilt_map(pair, variant)
    raw = {k: pair["source"].get(k, 0.0) + beta * tilt.get(k, 0.0) for k in pair["source"]}
    return normalise(raw)


def evaluate(test_pairs, variant, beta):
    perf = []
    persistence = []
    for p in test_pairs:
        persistence.append(p["persistence_accuracy"])
        perf.append(field_accuracy(predict(p, variant, beta), p["target"]))
    return {
        "pair_count": len(test_pairs),
        "beta": beta,
        "persistence_accuracy": mean(persistence),
        "performance_accuracy": mean(perf),
        "improvement_pp": mean(perf) - mean(persistence) if perf else None,
    }


def fixed_holdout(pairs, variant):
    split = int(math.floor(len(pairs) * 0.70))
    train, test = pairs[:split], pairs[split:]
    beta = fit_beta(train, variant)
    out = evaluate(test, variant, beta)
    out.update({"train_pairs": len(train), "test_pairs": len(test), "split_target_date": test[0]["target_date"] if test else None})
    return out


def walk_forward(pairs, variant):
    scores = []
    persistence = []
    betas = []
    for i in range(MIN_WALKFORWARD_TRAIN, len(pairs)):
        train = pairs[:i]
        target = pairs[i]
        beta = fit_beta(train, variant)
        betas.append(beta)
        scores.append(field_accuracy(predict(target, variant, beta), target["target"]))
        persistence.append(target["persistence_accuracy"])
    return {
        "test_pairs": len(scores),
        "minimum_training_pairs": MIN_WALKFORWARD_TRAIN,
        "mean_beta": mean(betas),
        "last_beta": betas[-1] if betas else None,
        "persistence_accuracy": mean(persistence),
        "performance_accuracy": mean(scores),
        "improvement_pp": mean(scores) - mean(persistence) if scores else None,
    }


def controlled_regression(pairs, variant=PRIMARY):
    # Pair-fixed-effect regression: change ~ previous share + performance signal.
    # Demeaning each variable within pair removes the pair intercept. Each pair has equal total weight.
    xtx = [[0.0, 0.0], [0.0, 0.0]]
    xty = [0.0, 0.0]
    n = 0
    for p in pairs:
        keys = sorted(set(p["source"]) | set(p["target"]))
        if not keys:
            continue
        s = signal_map(p, variant)
        vals = []
        for k in keys:
            vals.append((p["source"].get(k, 0.0), s.get(k, 0.0), p["target"].get(k, 0.0) - p["source"].get(k, 0.0)))
        mx = mean(v[0] for v in vals)
        ms = mean(v[1] for v in vals)
        my = mean(v[2] for v in vals)
        w = 1.0 / len(vals)
        for x, sig, y in vals:
            f = [x - mx, sig - ms]
            yy = y - my
            n += 1
            for i in range(2):
                xty[i] += w * f[i] * yy
                for j in range(2):
                    xtx[i][j] += w * f[i] * f[j]
    det = xtx[0][0] * xtx[1][1] - xtx[0][1] * xtx[1][0]
    if abs(det) < 1e-15:
        return None
    b_share = (xty[0] * xtx[1][1] - xty[1] * xtx[0][1]) / det
    b_perf = (xtx[0][0] * xty[1] - xtx[1][0] * xty[0]) / det
    return {"rows": n, "prior_share_coef": b_share, "performance_coef": b_perf, "performance_coef_pp_per_unit": 100 * b_perf}


def bootstrap_performance_coef(pairs):
    rng = random.Random(RNG_SEED)
    by_fmt = defaultdict(list)
    for p in pairs:
        by_fmt[p["format"]].append(p)
    fmts = sorted(by_fmt)
    vals = []
    for _ in range(BOOTSTRAPS):
        sampled = [rng.choice(fmts) for _ in fmts]
        boot = []
        for fmt in sampled:
            boot.extend(by_fmt[fmt])
        r = controlled_regression(boot)
        if r and math.isfinite(r["performance_coef_pp_per_unit"]):
            vals.append(r["performance_coef_pp_per_unit"])
    return {
        "cluster": "format",
        "replicates": len(vals),
        "low_95": percentile(vals, 0.025),
        "high_95": percentile(vals, 0.975),
    }


def main():
    perf_rows = load_perf_rows()
    cohorts, names = build_cohorts()
    pairs = build_pairs(cohorts, perf_rows)
    if len(pairs) < 20:
        raise RuntimeError(f"unexpectedly small eligible adjacent-pair sample: {len(pairs)}")

    variants = {}
    for v in VARIANTS:
        beta = fit_beta(pairs, v)
        variants[v] = {
            "full_in_sample": evaluate(pairs, v, beta),
            "fixed_holdout": fixed_holdout(pairs, v),
            "walk_forward": walk_forward(pairs, v),
        }

    regression = controlled_regression(pairs)
    regression["format_cluster_bootstrap_95"] = bootstrap_performance_coef(pairs)

    summary = {
        "question": "After accounting for previous IRL popularity, does prior-major archetype performance predict share change at the next adjacent same-format IRL cohort?",
        "phase": 2,
        "pair_count": len(pairs),
        "format_count": len({p["format"] for p in pairs}),
        "target_start_date_min": min(p["target_date"] for p in pairs),
        "target_start_date_max": max(p["target_date"] for p in pairs),
        "primary_variant": PRIMARY,
        "controlled_association": regression,
        "variants": variants,
        "interpretation_guardrails": [
            "Full-sample fitted results are descriptive/in-sample only.",
            "Chronological holdout and expanding walk-forward determine whether performance demonstrates predictive value.",
            "This phase contains no Online evidence and cannot answer mediation by Online adoption.",
            "Performance signals are retrospective public Labs aggregates; historical publication-time taxonomy is not reconstructed.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with PAIR_CSV.open("w", newline="", encoding="utf-8") as f:
        fields = ["pair_id", "format", "source_cohort", "target_cohort", "source_date", "target_date", "persistence_accuracy"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for p in pairs:
            w.writerow({k: p[k] for k in fields})

    primary = variants[PRIMARY]
    lines = [
        "# IRL performance → next IRL share — Phase 2",
        "",
        "## Research question",
        "",
        "After accounting for how popular an archetype already was, does overperformance at one IRL major predict increased representation at the next adjacent same-format IRL major cohort?",
        "",
        "## Evidence and design",
        "",
        f"- Eligible adjacent same-format cohort pairs: **{len(pairs)}** across **{len({p['format'] for p in pairs})}** formats.",
        "- Same >=95% Day-1 capture rule and no-skipping adjacency used by the prior IRL-to-IRL analysis.",
        "- Simultaneous majors stay aggregated as cohorts.",
        "- Primary performance signal: bounded [-2,+2] smoothed log2 Day-2 representation lift; no minimum-share exclusion.",
        "- Forecast is composition-preserving before clipping: previous field plus a fitted performance tilt proportional to previous share.",
        "- Fixed chronological 70/30 holdout and expanding walk-forward after 15 earlier pairs.",
        "",
        "## Controlled association",
        "",
        f"Pair-fixed-effect regression of next-share change on previous share + prior performance gives a performance coefficient of **{fmt(regression['performance_coef_pp_per_unit'],3)} percentage points of next-field share per +1 unit of bounded log2 Day-2 lift**.",
        f"Format-cluster bootstrap 95% interval: **[{fmt(regression['format_cluster_bootstrap_95']['low_95'],3)}, {fmt(regression['format_cluster_bootstrap_95']['high_95'],3)}] pp**.",
        "",
        "This is an association estimate, not by itself proof of future predictive improvement.",
        "",
        "## Primary forecast comparison",
        "",
        f"- Full-sample in-sample: persistence **{fmt(primary['full_in_sample']['persistence_accuracy'])}%** vs performance-adjusted **{fmt(primary['full_in_sample']['performance_accuracy'])}%** ({fmt(primary['full_in_sample']['improvement_pp'],3)}pp).",
        f"- Fixed holdout: persistence **{fmt(primary['fixed_holdout']['persistence_accuracy'])}%** vs performance-adjusted **{fmt(primary['fixed_holdout']['performance_accuracy'])}%** ({fmt(primary['fixed_holdout']['improvement_pp'],3)}pp), {primary['fixed_holdout']['test_pairs']} test pairs.",
        f"- Expanding walk-forward: persistence **{fmt(primary['walk_forward']['persistence_accuracy'])}%** vs performance-adjusted **{fmt(primary['walk_forward']['performance_accuracy'])}%** ({fmt(primary['walk_forward']['improvement_pp'],3)}pp), {primary['walk_forward']['test_pairs']} chronological targets.",
        "",
        "## Sensitivity variants",
        "",
        "| Variant | Holdout Δ vs persistence | Walk-forward Δ |",
        "|---|---:|---:|",
    ]
    for v in VARIANTS:
        lines.append(f"| {v} | {fmt(variants[v]['fixed_holdout']['improvement_pp'],3)}pp | {fmt(variants[v]['walk_forward']['improvement_pp'],3)}pp |")
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "**Verified:** values above are reproducible outputs from the frozen adjacent-cohort sample and chronological splits.",
        "",
        "**Inferred:** only if the chronological comparisons remain positive and reasonably stable should prior IRL performance advance as an independent forecasting feature.",
        "",
        "**Not tested here:** whether subsequent Online movement mediates the performance effect. That is the next programme stage after deciding whether the standalone performance signal is worth carrying forward.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
