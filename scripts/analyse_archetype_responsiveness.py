#!/usr/bin/env python3
"""Stage 2: distinguish global Online responsiveness from archetype-specific behaviour.

Uses the frozen PR #13 forecast and only prior cohorts for every chronological fit.
Compares: baseline; one global residual response to corrected Online movement; and exact-key
partially-pooled response slopes. Also tests whether an archetype's prior residual volatility
predicts the size of its next forecast error.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import analyse_archetype_behaviour_residuals as base

ROOT=Path(__file__).resolve().parents[1]
OUTDIR=ROOT/"data"/"processed"/"archetype-behaviour-residuals"
RESDIR=ROOT/"results"/"archetype-behaviour-residuals"
K=5.0
BETA_MIN=-1.0
BETA_MAX=1.0
EPS=1e-12


def mean(xs):
    xs=list(xs); return statistics.fmean(xs) if xs else None


def pearson(xs,ys):
    xs=list(xs); ys=list(ys)
    if len(xs)<3 or len(xs)!=len(ys): return None
    mx,my=mean(xs),mean(ys)
    num=sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    den=math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
    return num/den if den>EPS else None


def clamp(x): return max(BETA_MIN,min(BETA_MAX,x))


def feature_rows(events):
    grouped=defaultdict(list)
    for e in events: grouped[e["cohort_id"]].append(e)
    out=[]
    for cohort,es in grouped.items():
        corrected=[base.concentration_correct(e["irl"],e["online"]) for e in es]
        keys=set()
        for e,c in zip(es,corrected): keys |= set(e["pred"])|set(e["actual"])|set(e["irl"])|set(c)
        for key in keys:
            p=mean(e["pred"].get(key,0.0) for e in es)
            a=mean(e["actual"].get(key,0.0) for e in es)
            irl=mean(e["irl"].get(key,0.0) for e in es)
            con=mean(c.get(key,0.0) for c in corrected)
            name=next((e["names"].get(key) for e in es if e["names"].get(key)),key)
            out.append({"cohort_id":cohort,"key":key,"name":name,"pred":p,"actual":a,
                        "residual":a-p,"x":con-irl,"active":p>=base.ACTIVE_THRESHOLD})
    return out


def fit_no_intercept(rows):
    rows=[r for r in rows if r["active"]]
    den=sum(r["x"]**2 for r in rows)
    return clamp(sum(r["x"]*r["residual"] for r in rows)/den) if den>EPS else 0.0


def fit_key_betas(rows,global_beta,k=K):
    by=defaultdict(list)
    for r in rows:
        if r["active"]: by[r["key"]].append(r)
    out={}
    for key,rs in by.items():
        den=sum(r["x"]**2 for r in rs)
        own=sum(r["x"]*r["residual"] for r in rs)/den if den>EPS else global_beta
        n=len(rs)
        out[key]=clamp((n/(n+k))*own+(k/(n+k))*global_beta)
    return out


def adjust_event(e,beta_or_map):
    corrected=base.concentration_correct(e["irl"],e["online"])
    out={}
    for key,val in e["pred"].items():
        if val < base.ACTIVE_THRESHOLD:
            out[key]=val; continue
        x=corrected.get(key,0.0)-e["irl"].get(key,0.0)
        b=beta_or_map.get(key,beta_or_map.get("__global__",0.0)) if isinstance(beta_or_map,dict) else beta_or_map
        out[key]=max(0.0,val+b*x)
    total=sum(out.values())
    return {k:v/total for k,v in out.items()} if total else dict(e["pred"])


def chronological_compare(events,rows,cohorts,dates,k=K):
    ev_by=defaultdict(list); row_by=defaultdict(list)
    for e in events: ev_by[e["cohort_id"]].append(e)
    for r in rows: row_by[r["cohort_id"]].append(r)
    prior_rows=[]; tested=[]
    for i,cohort in enumerate(cohorts):
        if i>=base.MIN_WF_PRIOR_COHORTS:
            gb=fit_no_intercept(prior_rows)
            kb=fit_key_betas(prior_rows,gb,k)
            kb["__global__"]=gb
            bs=[]; gs=[]; ks=[]
            for e in ev_by[cohort]:
                bs.append(e["score"])
                gs.append(base.accuracy(adjust_event(e,gb),e["actual"]))
                ks.append(base.accuracy(adjust_event(e,kb),e["actual"]))
            tested.append({"cohort_id":cohort,"date":dates[cohort],"global_beta":gb,
                           "baseline":mean(bs),"global_response":mean(gs),"archetype_response":mean(ks),
                           "global_delta_pp":mean(gs)-mean(bs),"archetype_delta_pp":mean(ks)-mean(bs),
                           "archetype_vs_global_pp":mean(ks)-mean(gs)})
        prior_rows.extend(row_by[cohort])
    return {"shrink_k":k,"tested_cohorts":len(tested),
            "baseline_mean_accuracy":mean(r["baseline"] for r in tested),
            "global_response_mean_accuracy":mean(r["global_response"] for r in tested),
            "archetype_response_mean_accuracy":mean(r["archetype_response"] for r in tested),
            "global_delta_pp":mean(r["global_delta_pp"] for r in tested),
            "archetype_delta_pp":mean(r["archetype_delta_pp"] for r in tested),
            "archetype_vs_global_pp":mean(r["archetype_vs_global_pp"] for r in tested),
            "archetype_beats_global":sum(r["archetype_vs_global_pp"]>EPS for r in tested),
            "archetype_beats_baseline":sum(r["archetype_delta_pp"]>EPS for r in tested),
            "rows":tested}


def volatility_signal(rows,cohorts):
    by=defaultdict(list)
    for r in rows:
        if r["active"]: by[r["cohort_id"]].append(r)
    hist=defaultdict(list); pairs=[]
    for cohort in cohorts:
        for r in by[cohort]:
            h=hist[r["key"]]
            if len(h)>=3:
                prior_sd=statistics.stdev(h)
                pairs.append((100*prior_sd,100*abs(r["residual"]),r["key"],r["name"]))
        for r in by[cohort]: hist[r["key"]].append(r["residual"])
    xs=[p[0] for p in pairs]; ys=[p[1] for p in pairs]
    med=statistics.median(xs) if xs else None
    low=[y for x,y,*_ in pairs if x<=med] if med is not None else []
    high=[y for x,y,*_ in pairs if x>med] if med is not None else []
    return {"eligible_observations":len(pairs),"pearson_prior_sd_vs_next_abs_residual":pearson(xs,ys),
            "median_prior_sd_pp":med,"next_abs_error_low_volatility_pp":mean(low),
            "next_abs_error_high_volatility_pp":mean(high),
            "high_minus_low_pp":mean(high)-mean(low) if high and low else None}


def main():
    events=base.load_events(); cohorts,dates=base.cohort_order(events); rows=feature_rows(events)
    primary=chronological_compare(events,rows,cohorts,dates,K)
    sensitivity={str(k):chronological_compare(events,rows,cohorts,dates,k) for k in (2.0,5.0,10.0,20.0)}
    vol=volatility_signal(rows,cohorts)
    out={"question":"Do archetypes differ predictably in response to corrected Online movement or forecast volatility?",
         "feature":"corrected Online share minus previous IRL share; residual is actual minus frozen PR13 forecast",
         "primary_walk_forward":primary,"partial_pooling_sensitivity":sensitivity,"volatility_signal":vol,
         "boundary":"All coefficients for a target are fitted only from earlier cohorts. Exact repository archetype keys only. This remains retrospective model discovery, not future prospective validation."}
    OUTDIR.mkdir(parents=True,exist_ok=True); RESDIR.mkdir(parents=True,exist_ok=True)
    (OUTDIR/"responsiveness.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    lines=["# Archetype responsiveness and volatility","",
           "This extends the residual-bias diagnostic by asking whether archetypes respond differently to the **corrected Online movement signal**, rather than merely carrying a persistent additive bias.","",
           "## Chronological forecasting comparison","",
           f"Across {primary['tested_cohorts']} expanding-replay cohorts:","",
           f"- frozen concentration-corrected baseline: **{primary['baseline_mean_accuracy']:.2f}%**;",
           f"- one global residual-response coefficient fitted from earlier cohorts: **{primary['global_response_mean_accuracy']:.2f}%** ({primary['global_delta_pp']:+.3f}pp);",
           f"- partially pooled exact-archetype response coefficients (k={K:g}): **{primary['archetype_response_mean_accuracy']:.2f}%** ({primary['archetype_delta_pp']:+.3f}pp vs baseline; {primary['archetype_vs_global_pp']:+.3f}pp vs global).","",
           f"Archetype-specific response beats the global response in **{primary['archetype_beats_global']}/{primary['tested_cohorts']}** cohorts and beats the frozen baseline in **{primary['archetype_beats_baseline']}/{primary['tested_cohorts']}**.","",
           "Partial-pooling sensitivity: " + "; ".join(f"k={float(k):g}: {v['archetype_vs_global_pp']:+.3f}pp vs global" for k,v in sensitivity.items()) + ".","",
           "## Does archetype volatility persist?","",
           f"Using only earlier residual history (minimum 3 observations), prior archetype residual SD vs next absolute residual: **r={vol['pearson_prior_sd_vs_next_abs_residual']:.3f}** across **{vol['eligible_observations']}** observations.","",
           f"Deck-observations below the median prior volatility subsequently miss by **{vol['next_abs_error_low_volatility_pp']:.2f}pp** on average; above-median prior volatility miss by **{vol['next_abs_error_high_volatility_pp']:.2f}pp** ({vol['high_minus_low_pp']:+.2f}pp).","",
           "## Interpretation boundary","",
           "A global-response improvement would mean the base forecast is systematically under/over-reacting to Online movement. Only an additional gain from the partially pooled model is evidence that **archetype-specific responsiveness** helps prediction.","",
           "A positive chronological volatility relationship can support archetype-specific uncertainty/confidence even if archetype-specific point-estimate adjustments do not help.",""]
    (RESDIR/"RESPONSIVENESS.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"baseline":primary['baseline_mean_accuracy'],"global":primary['global_response_mean_accuracy'],
                      "archetype":primary['archetype_response_mean_accuracy'],"arch_vs_global":primary['archetype_vs_global_pp'],
                      "volatility_r":vol['pearson_prior_sd_vs_next_abs_residual']},indent=2))

if __name__=="__main__": main()
