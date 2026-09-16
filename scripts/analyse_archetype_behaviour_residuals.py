#!/usr/bin/env python3
"""Test whether archetype identity predicts errors in the fixed concentration-corrected forecast.

This is deliberately stacked on the concentration-corrected blend experiment. It freezes
that model at 80% starting IRL weight, -1pp/day, 55% floor and 75% top-10 concentration
correction. No target outcome is used to construct its own baseline forecast.

The primary question is diagnostic: after that forecast, do the same exact archetype keys
show repeatable residual bias or materially different residual volatility? A secondary,
predeclared forecasting check applies a simple partially-pooled historical residual bias
using only earlier cohorts. It is intentionally much simpler than a per-archetype model.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFILE = ROOT / "data" / "processed" / "model-results" / "baselines.json"
OUTDIR = ROOT / "data" / "processed" / "archetype-behaviour-residuals"
RESDIR = ROOT / "results" / "archetype-behaviour-residuals"

START = 0.80
FLOOR = 0.55
DECAY = 0.010
CORRECTION = 0.75
TOP_N = 10
ACTIVE_THRESHOLD = 0.005  # baseline forecast share; pre-target only
MIN_PRIOR_OBS = 2
MIN_ARCHETYPE_COHORTS = 5
MIN_WF_PRIOR_COHORTS = 10
SHRINK_K = 5.0  # prior mean residual multiplied by n/(n+k)
SENSITIVITY_K = [2.0, 5.0, 10.0, 20.0]
EPS = 1e-12


def mean(xs):
    xs = list(xs)
    return statistics.fmean(xs) if xs else None


def sd(xs):
    xs = list(xs)
    return statistics.stdev(xs) if len(xs) >= 2 else None


def quantile(xs, q):
    vals = sorted(xs)
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * q
    lo = int(math.floor(pos)); hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)


def pearson(xs, ys):
    xs, ys = list(xs), list(ys)
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    den = math.sqrt(sum((x-mx)**2 for x in xs) * sum((y-my)**2 for y in ys))
    return num/den if den > EPS else None


def pred_map(model):
    return {str(r["key"]): float(r["predicted_pct"]) / 100.0 for r in model.get("prediction", [])}


def actual_map(model):
    return {str(r["key"]): float(r["actual_pct"]) / 100.0 for r in model.get("prediction", [])}


def name_map(model):
    return {str(r["key"]): str(r.get("name") or r["key"]) for r in model.get("prediction", [])}


def blend(a, b, w):
    keys = set(a) | set(b)
    out = {k: w*a.get(k,0.0) + (1.0-w)*b.get(k,0.0) for k in keys}
    total = sum(out.values())
    return {k:v/total for k,v in out.items()} if total else {}


def accuracy(pred, actual):
    keys = set(pred) | set(actual)
    return 100.0 * (1.0 - 0.5*sum(abs(pred.get(k,0.0)-actual.get(k,0.0)) for k in keys))


def reconstruct_online(irl, fifty):
    keys = set(irl) | set(fifty)
    raw = {k: 2.0*fifty.get(k,0.0)-irl.get(k,0.0) for k in keys}
    if min(raw.values(), default=0.0) < -1e-7:
        raise RuntimeError("Could not reconstruct Online component")
    out = {k:max(0.0,v) for k,v in raw.items()}
    total = sum(out.values())
    return {k:v/total for k,v in out.items()} if total else {}


def top_keys(dist, n):
    return [k for k,_ in sorted(dist.items(), key=lambda kv:(-kv[1],kv[0]))[:n]]


def concentration_correct(irl, online):
    group = set(top_keys(irl, TOP_N))
    prior_group = sum(irl.get(k,0.0) for k in group)
    online_group = sum(online.get(k,0.0) for k in group)
    target_group = online_group + CORRECTION*(prior_group-online_group)
    online_tail = 1.0-online_group
    if online_group <= EPS or online_tail <= EPS:
        return dict(online)
    top_scale = target_group/online_group
    tail_scale = (1.0-target_group)/online_tail
    out = {k:v*(top_scale if k in group else tail_scale) for k,v in online.items()}
    total = sum(out.values())
    return {k:v/total for k,v in out.items()}


def irl_weight(days):
    return max(FLOOR, min(START, START-DECAY*days))


def load_events():
    data = json.loads(INFILE.read_text(encoding="utf-8"))
    rows=[]
    for t in data.get("targets",[]):
        if not t.get("target_eligible_ge_95") or t.get("window_class") != "settled":
            continue
        models=t.get("models",{})
        irl_m=models.get("irl_only",{}); half_m=models.get("fifty_fifty",{}); cur=models.get("current_v2_1",{})
        if not (irl_m.get("available") and half_m.get("available") and cur.get("available")):
            continue
        irl=pred_map(irl_m); online=reconstruct_online(irl,pred_map(half_m)); actual=actual_map(irl_m)
        corrected=concentration_correct(irl,online)
        pred=blend(irl,corrected,irl_weight(int(t["days_since_major"])))
        names=name_map(irl_m)
        for m in (half_m,cur):
            names.update(name_map(m))
        rows.append({
            "target_id":str(t["target_id"]), "target_name":t["target_name"], "date":t["target_start_date"],
            "cohort_id":t["cohort_id"], "format":t.get("target_format"), "days":int(t["days_since_major"]),
            "irl":irl,"online":online,"pred":pred,"actual":actual,"names":names,
            "score":accuracy(pred,actual),
        })
    return rows


def cohort_order(events):
    dates={}
    for e in events:
        dates[e["cohort_id"]]=min(dates.get(e["cohort_id"],e["date"]),e["date"])
    return sorted(dates,key=lambda c:(dates[c],c)),dates


def cohort_archetype_rows(events):
    grouped=defaultdict(list)
    for e in events:
        grouped[e["cohort_id"]].append(e)
    out=[]
    for cohort,es in grouped.items():
        keys=set()
        for e in es:
            keys |= set(e["pred"]) | set(e["actual"]) | set(e["irl"]) | set(e["online"])
        for k in keys:
            p=mean(e["pred"].get(k,0.0) for e in es)
            a=mean(e["actual"].get(k,0.0) for e in es)
            irl=mean(e["irl"].get(k,0.0) for e in es)
            online=mean(e["online"].get(k,0.0) for e in es)
            name=next((e["names"].get(k) for e in es if e["names"].get(k)),k)
            out.append({"cohort_id":cohort,"date":min(e["date"] for e in es),"key":k,"name":name,
                        "pred":p,"actual":a,"residual":a-p,"irl":irl,"online":online,
                        "online_delta":online-irl,"active":p>=ACTIVE_THRESHOLD})
    return out


def archetype_summary(rows):
    by=defaultdict(list)
    for r in rows:
        if r["active"]:
            by[r["key"]].append(r)
    result=[]
    for k,rs in by.items():
        if len(rs)<MIN_ARCHETYPE_COHORTS:
            continue
        residuals=[100*r["residual"] for r in rs]
        xs=[100*r["online_delta"] for r in rs]
        mx=mean(xs); my=mean(residuals)
        den=sum((x-mx)**2 for x in xs)
        slope=sum((x-mx)*(y-my) for x,y in zip(xs,residuals))/den if den>EPS else None
        result.append({
            "key":k,"name":rs[-1]["name"],"cohorts":len(rs),
            "mean_residual_pp":mean(residuals),"residual_sd_pp":sd(residuals),
            "mean_abs_residual_pp":mean(abs(x) for x in residuals),
            "online_delta_residual_slope":slope,
            "mean_forecast_share_pct":100*mean(r["pred"] for r in rs),
        })
    return sorted(result,key=lambda x:(-x["cohorts"],x["key"]))


def identity_in_sample(rows):
    active=[r for r in rows if r["active"]]
    if not active:
        return {}
    overall=mean(r["residual"] for r in active)
    by=defaultdict(list)
    for r in active: by[r["key"]].append(r["residual"])
    means={k:mean(v) for k,v in by.items()}
    sst=sum((r["residual"]-overall)**2 for r in active)
    sse=sum((r["residual"]-means[r["key"]])**2 for r in active)
    return {"active_observations":len(active),"archetypes":len(by),"identity_r2_in_sample":1-sse/sst if sst>EPS else None,
            "overall_mean_residual_pp":100*overall}


def chronological_residual_signal(rows, cohorts):
    by_cohort=defaultdict(list)
    for r in rows:
        if r["active"]: by_cohort[r["cohort_id"]].append(r)
    history=defaultdict(list)
    pairs=[]
    for cohort in cohorts:
        for r in by_cohort.get(cohort,[]):
            h=history[r["key"]]
            if len(h)>=MIN_PRIOR_OBS:
                prior=mean(h)
                pairs.append((100*prior,100*r["residual"],r["key"],r["name"],len(h),cohort))
        for r in by_cohort.get(cohort,[]):
            history[r["key"]].append(r["residual"])
    xs=[p[0] for p in pairs]; ys=[p[1] for p in pairs]
    same=sum(1 for x,y,*_ in pairs if (x>0 and y>0) or (x<0 and y<0))
    nonzero=sum(1 for x,y,*_ in pairs if abs(x)>EPS and abs(y)>EPS)
    return {"eligible_observations":len(pairs),"pearson_prior_mean_vs_next_residual":pearson(xs,ys),
            "same_sign_share":same/nonzero if nonzero else None,
            "prior_mean_mae_pp":mean(abs(y-x) for x,y,*_ in pairs) if pairs else None,
            "zero_baseline_mae_pp":mean(abs(y) for y in ys) if ys else None}


def apply_bias(pred, history, k):
    adjusted={}
    for key,val in pred.items():
        h=history.get(key,[])
        bias=(len(h)/(len(h)+k))*mean(h) if h else 0.0
        adjusted[key]=max(0.0,val+bias)
    total=sum(adjusted.values())
    return {key:val/total for key,val in adjusted.items()} if total else dict(pred)


def walk_forward_bias(events, cohorts, dates, k):
    events_by=defaultdict(list)
    for e in events: events_by[e["cohort_id"]].append(e)
    history=defaultdict(list)
    tested=[]
    for i,cohort in enumerate(cohorts):
        es=events_by[cohort]
        if i>=MIN_WF_PRIOR_COHORTS:
            base_scores=[]; adj_scores=[]
            for e in es:
                adj=apply_bias(e["pred"],history,k)
                base_scores.append(e["score"]); adj_scores.append(accuracy(adj,e["actual"]))
            tested.append({"cohort_id":cohort,"date":dates[cohort],"base_accuracy":mean(base_scores),
                           "adjusted_accuracy":mean(adj_scores),"delta_pp":mean(adj_scores)-mean(base_scores)})
        # Update history once per cohort, averaging simultaneous-event residuals first.
        keys=set()
        for e in es: keys |= set(e["pred"]) | set(e["actual"])
        for key in keys:
            p=mean(e["pred"].get(key,0.0) for e in es); a=mean(e["actual"].get(key,0.0) for e in es)
            if p>=ACTIVE_THRESHOLD:
                history[key].append(a-p)
    return {"shrink_k":k,"tested_cohorts":len(tested),"base_mean_accuracy":mean(r["base_accuracy"] for r in tested),
            "adjusted_mean_accuracy":mean(r["adjusted_accuracy"] for r in tested),
            "delta_pp":mean(r["delta_pp"] for r in tested),
            "improved":sum(r["delta_pp"]>EPS for r in tested),"worse":sum(r["delta_pp"]<-EPS for r in tested),
            "rows":tested}


def threshold_sensitivity(rows, cohorts):
    out={}
    for threshold in (0.0025,0.005,0.01,0.02):
        subset=[dict(r,active=r["pred"]>=threshold) for r in rows]
        out[str(threshold)] = chronological_residual_signal(subset,cohorts)
    return out


def main():
    events=load_events()
    cohorts,dates=cohort_order(events)
    rows=cohort_archetype_rows(events)
    arch=archetype_summary(rows)
    ident=identity_in_sample(rows)
    chrono=chronological_residual_signal(rows,cohorts)
    wf=walk_forward_bias(events,cohorts,dates,SHRINK_K)
    wf_sens={str(k):walk_forward_bias(events,cohorts,dates,k) for k in SENSITIVITY_K}

    # Descriptive dispersion among repeated archetypes.
    sds=[r["residual_sd_pp"] for r in arch if r["residual_sd_pp"] is not None]
    biases=[r["mean_residual_pp"] for r in arch]
    slopes=[r["online_delta_residual_slope"] for r in arch if r["online_delta_residual_slope"] is not None]
    descriptive={
        "repeated_archetypes":len(arch),
        "residual_bias_abs_median_pp":quantile([abs(x) for x in biases],0.5),
        "residual_bias_abs_q75_pp":quantile([abs(x) for x in biases],0.75),
        "residual_sd_median_pp":quantile(sds,0.5),"residual_sd_q25_pp":quantile(sds,0.25),"residual_sd_q75_pp":quantile(sds,0.75),
        "online_responsiveness_slope_q25":quantile(slopes,0.25),"online_responsiveness_slope_median":quantile(slopes,0.5),"online_responsiveness_slope_q75":quantile(slopes,0.75),
    }

    # Most systematic / volatile repeated exact keys; descriptive only.
    most_biased=sorted(arch,key=lambda r:abs(r["mean_residual_pp"]),reverse=True)[:15]
    most_volatile=sorted(arch,key=lambda r:r["residual_sd_pp"] or 0,reverse=True)[:15]

    out={
        "question":"Does exact archetype identity predict systematic errors in the fixed concentration-corrected next-IRL forecast?",
        "baseline":{"start_irl_weight":START,"floor_irl_weight":FLOOR,"decay_per_day":DECAY,"top_n":TOP_N,"concentration_correction":CORRECTION,
                    "event_count":len(events),"cohort_count":len(cohorts),"mean_event_accuracy":mean(e["score"] for e in events),
                    "mean_cohort_accuracy":mean(mean(e["score"] for e in events if e["cohort_id"]==c) for c in cohorts)},
        "residual_definition":"actual next-IRL share minus fixed corrected forecast share; positive means underprediction",
        "active_definition":f"baseline forecast share >= {ACTIVE_THRESHOLD*100:.2f}% (pre-target criterion)",
        "identity_in_sample":ident,
        "chronological_residual_signal":chrono,
        "descriptive_repeated_archetypes":descriptive,
        "primary_partial_pooling_walk_forward":wf,
        "shrinkage_sensitivity":wf_sens,
        "forecast_share_threshold_sensitivity":threshold_sensitivity(rows,cohorts),
        "most_biased_repeated_archetypes":most_biased,
        "most_volatile_repeated_archetypes":most_volatile,
        "limitations":[
            "Identity is the repository's existing exact archetype key; no new taxonomy or cross-key mapping is introduced.",
            "Archetype behaviour can change when lists, sets and formats change; repeated key does not prove a stable causal deck trait.",
            "The 34-event/25-cohort complete-case sample is small for deck-specific modelling, so descriptive individual-deck estimates are not promoted as standalone forecast parameters.",
            "The partial-pooling adjustment uses only earlier residuals, but its family was motivated after inspecting the historical archive; future prospective validation remains required."
        ]
    }
    OUTDIR.mkdir(parents=True,exist_ok=True); RESDIR.mkdir(parents=True,exist_ok=True)
    (OUTDIR/"summary.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    with (OUTDIR/"archetype-summary.csv").open("w",newline="",encoding="utf-8") as f:
        fields=list(arch[0].keys()) if arch else ["key","name","cohorts"]
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(arch)

    def pct(x): return "—" if x is None else f"{100*x:.1f}%"
    lines=[
        "# Archetype behaviour residual analysis","",
        "## Question","",
        "After freezing the concentration-corrected IRL+Online forecast, does the same archetype tend to be systematically over/under-predicted, and is that stable enough to improve later forecasts?","",
        "## Frozen baseline","",
        f"Fixed PR #13 rule: 80% IRL start, -1pp/day, 55% floor, 75% previous-IRL top-10 concentration correction. Sample: **{len(events)} tournaments / {len(cohorts)} cohorts**. Cohort-weighted accuracy **{out['baseline']['mean_cohort_accuracy']:.2f}%**.","",
        "Residual = actual next-IRL share minus forecast share. Positive residual means the model underpredicted the archetype.","",
        "## Does archetype identity repeat?","",
        f"Active deck-cohort observations: **{ident.get('active_observations',0)}** across **{ident.get('archetypes',0)}** exact keys. In-sample identity R²: **{ident.get('identity_r2_in_sample',0):.3f}** (descriptive only).","",
        f"Using only earlier observations for an archetype (minimum {MIN_PRIOR_OBS}), prior mean residual vs its next residual: **r={chrono['pearson_prior_mean_vs_next_residual']:.3f}** across **{chrono['eligible_observations']}** observations; same-sign rate **{pct(chrono['same_sign_share'])}**.","",
        f"Predicting the next residual as the archetype's prior mean gives MAE **{chrono['prior_mean_mae_pp']:.2f}pp** versus **{chrono['zero_baseline_mae_pp']:.2f}pp** for assuming no archetype-specific residual.","",
        "## Partially pooled forecasting check","",
        f"Primary fixed shrinkage k={SHRINK_K:g}: historical mean residual for each exact key is shrunk by n/(n+k), then added to the next forecast and the whole field is renormalised. Only earlier cohorts contribute.","",
        f"Expanding replay after {MIN_WF_PRIOR_COHORTS} prior cohorts: **{wf['base_mean_accuracy']:.2f}% baseline -> {wf['adjusted_mean_accuracy']:.2f}% adjusted ({wf['delta_pp']:+.3f}pp)**; improved **{wf['improved']}/{wf['tested_cohorts']}** cohorts, worse **{wf['worse']}/{wf['tested_cohorts']}**.","",
        "Shrinkage sensitivity: " + "; ".join(f"k={k:g}: {v['delta_pp']:+.3f}pp" for k,v in [(float(k),v) for k,v in wf_sens.items()]) + ".","",
        "## Behaviour dispersion among repeated archetypes","",
        f"Repeated exact keys with >= {MIN_ARCHETYPE_COHORTS} active cohorts: **{descriptive['repeated_archetypes']}**. Median absolute systematic bias **{descriptive['residual_bias_abs_median_pp']:.2f}pp**; median residual volatility **{descriptive['residual_sd_median_pp']:.2f}pp** (IQR {descriptive['residual_sd_q25_pp']:.2f}–{descriptive['residual_sd_q75_pp']:.2f}).","",
        "The descriptive per-archetype Online-delta/residual slope distribution is reported in JSON/CSV to diagnose differing responsiveness, but is not used as a forecast parameter in this bounded experiment.","",
        "## Most systematic repeated residuals (descriptive)","",
        "| Archetype | Cohorts | Mean residual | Residual SD | Mean forecast share |","|---|---:|---:|---:|---:|",
    ]
    for r in most_biased[:10]:
        lines.append(f"| {r['name']} | {r['cohorts']} | {r['mean_residual_pp']:+.2f}pp | {r['residual_sd_pp']:.2f}pp | {r['mean_forecast_share_pct']:.2f}% |")
    lines += ["","## Interpretation boundary","",
              "**Verified** results above describe exact-key historical repetition and the chronological partial-pooling replay.","",
              "**Inferred** deck identity is useful only if the chronological residual relationship and/or adjusted Field Accuracy is meaningfully positive; individual deck rows remain descriptive because the sample per deck is small.","",
              "**Unknown** whether any apparent deck-specific behaviour is a persistent archetype trait versus a temporary format/list/player-base effect, and whether it will improve a genuinely future event.",""]
    (RESDIR/"README.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"events":len(events),"cohorts":len(cohorts),"baseline":out['baseline']['mean_cohort_accuracy'],
                      "identity_r":chrono['pearson_prior_mean_vs_next_residual'],"wf_delta":wf['delta_pp'],
                      "wf_adjusted":wf['adjusted_mean_accuracy'],"repeated_archetypes":len(arch)},indent=2))

if __name__ == "__main__":
    main()
