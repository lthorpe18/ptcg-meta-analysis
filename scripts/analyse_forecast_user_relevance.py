#!/usr/bin/env python3
"""Diagnostic only: how accurate are chronological forecasts for decks users care about?

Uses the PR15 combined model exactly as implemented there. Reconstructs its primary expanding
walk-forward predictions (10 prior matched cohorts before a target), then evaluates:
- error by *predicted* share band (available before the event; no future leakage in grouping),
- top-5/top-10 identity and captured actual field mass,
- threshold precision/recall for >=1%, >=2%, >=5%,
- descriptive empirical absolute-error percentiles for practical uncertainty language.

No model parameters are selected or changed by this analysis.
"""
from __future__ import annotations
import json, statistics
from collections import defaultdict
from pathlib import Path
import analyse_combined_online_performance as comb

ROOT=Path(__file__).resolve().parents[1]
OUTDIR=ROOT/'data/processed/forecast-user-relevance'
RESDIR=ROOT/'results/forecast-user-relevance'
MIN_TRAIN=10
BANDS=[('10%+',10.0,None),('5-10%',5.0,10.0),('2-5%',2.0,5.0),('1-2%',1.0,2.0),('<1%',0.0,1.0)]
THRESHOLDS=[1.0,2.0,5.0]

def mean(xs):
    xs=list(xs); return statistics.fmean(xs) if xs else None

def percentile(xs,p):
    xs=sorted(xs)
    if not xs:return None
    if len(xs)==1:return xs[0]
    pos=(len(xs)-1)*p; lo=int(pos); hi=min(lo+1,len(xs)-1); f=pos-lo
    return xs[lo]*(1-f)+xs[hi]*f

def band_for(pred_pct):
    for name,lo,hi in BANDS:
        if pred_pct>=lo and (hi is None or pred_pct<hi):return name
    raise AssertionError(pred_pct)

def topkeys(d,n): return [k for k,_ in sorted(d.items(),key=lambda x:(-x[1],x[0]))[:n]]

def oos_predictions():
    rows=comb.matched(); cohorts=comb.cohort_order(rows); out=[]
    for i,cid in enumerate(cohorts):
        if i<MIN_TRAIN:continue
        prior=set(cohorts[:i]); beta=comb.fit_beta([r for r in rows if r['cohort_id'] in prior])
        for r in rows:
            if r['cohort_id']!=cid:continue
            pred=comb.apply(r,beta)
            out.append({'cohort_id':cid,'target_id':r['target_id'],'date':r['date'],'beta':beta,'pred':pred,'actual':r['actual']})
    return out

def deck_rows(events):
    out=[]
    for e in events:
        for k in set(e['pred'])|set(e['actual']):
            p=100*e['pred'].get(k,0); a=100*e['actual'].get(k,0)
            out.append({'cohort_id':e['cohort_id'],'target_id':e['target_id'],'key':k,'predicted_pct':p,'actual_pct':a,
                        'error_pp':p-a,'abs_error_pp':abs(p-a),'band':band_for(p)})
    return out

def band_metrics(rows):
    result=[]
    for name,_,_ in BANDS:
        rr=[r for r in rows if r['band']==name]
        if not rr:continue
        by=defaultdict(list)
        for r in rr:by[r['cohort_id']].append(r)
        # Primary averages give each independent cohort equal weight.
        cohort=[]
        for cid,cr in by.items():
            cohort.append({'mae':mean(x['abs_error_pp'] for x in cr),'bias':mean(x['error_pp'] for x in cr),
                           'within1':mean(x['abs_error_pp']<=1 for x in cr),'within2':mean(x['abs_error_pp']<=2 for x in cr)})
        abses=[r['abs_error_pp'] for r in rr]
        result.append({'band':name,'observations':len(rr),'cohorts_with_band':len(by),
                       'mean_predicted_pct':mean(r['predicted_pct'] for r in rr),'mean_actual_pct':mean(r['actual_pct'] for r in rr),
                       'cohort_weighted_mae_pp':mean(x['mae'] for x in cohort),'cohort_weighted_bias_pp':mean(x['bias'] for x in cohort),
                       'cohort_weighted_within_1pp':mean(x['within1'] for x in cohort),'cohort_weighted_within_2pp':mean(x['within2'] for x in cohort),
                       'pooled_abs_error_p50_pp':percentile(abses,.5),'pooled_abs_error_p80_pp':percentile(abses,.8),
                       'pooled_abs_error_p90_pp':percentile(abses,.9)})
    return result

def topn_metrics(events,n):
    rows=[]
    for e in events:
        pk=topkeys(e['pred'],n); ak=set(topkeys(e['actual'],n)); ps=set(pk)
        captured=sum(100*e['actual'].get(k,0) for k in pk)
        predmass=sum(100*e['pred'].get(k,0) for k in pk)
        actual_own=sum(100*e['actual'].get(k,0) for k in ak)
        rows.append({'cohort_id':e['cohort_id'],'overlap':len(ps&ak)/n,'captured':captured,'predmass':predmass,
                     'same_keys_mass_error':predmass-captured,'actual_own_mass':actual_own})
    by=defaultdict(list)
    for r in rows:by[r['cohort_id']].append(r)
    cs=[]
    for cr in by.values():
        cs.append({k:mean(x[k] for x in cr) for k in ['overlap','captured','predmass','same_keys_mass_error','actual_own_mass']})
    return {'n':n,'events':len(rows),'cohorts':len(cs),'mean_identity_overlap':mean(x['overlap'] for x in cs),
            'mean_actual_field_share_captured_pct':mean(x['captured'] for x in cs),'mean_predicted_topn_mass_pct':mean(x['predmass'] for x in cs),
            'mean_actual_own_topn_mass_pct':mean(x['actual_own_mass'] for x in cs),
            'mean_same_keys_mass_bias_pp':mean(x['same_keys_mass_error'] for x in cs)}

def threshold_metrics(rows,t):
    by=defaultdict(list)
    for r in rows:by[(r['cohort_id'],r['target_id'])].append(r)
    ev=[]
    for rr in by.values():
        pred={r['key'] for r in rr if r['predicted_pct']>=t}; actual={r['key'] for r in rr if r['actual_pct']>=t}
        tp=len(pred&actual)
        ev.append({'cohort_id':rr[0]['cohort_id'],'precision':tp/len(pred) if pred else 1.,'recall':tp/len(actual) if actual else 1.,
                   'pred_count':len(pred),'actual_count':len(actual),'false_pos':len(pred-actual),'missed':len(actual-pred)})
    byc=defaultdict(list)
    for x in ev:byc[x['cohort_id']].append(x)
    cs=[]
    for rr in byc.values():cs.append({k:mean(x[k] for x in rr) for k in ['precision','recall','pred_count','actual_count','false_pos','missed']})
    return {'threshold_pct':t,'cohorts':len(cs),'mean_precision':mean(x['precision'] for x in cs),'mean_recall':mean(x['recall'] for x in cs),
            'mean_predicted_count':mean(x['pred_count'] for x in cs),'mean_actual_count':mean(x['actual_count'] for x in cs),
            'mean_false_positives':mean(x['false_pos'] for x in cs),'mean_missed':mean(x['missed'] for x in cs)}

def main():
    events=oos_predictions(); rows=deck_rows(events); cohorts=len(set(e['cohort_id'] for e in events))
    bands=band_metrics(rows); top5=topn_metrics(events,5); top10=topn_metrics(events,10); thresholds=[threshold_metrics(rows,t) for t in THRESHOLDS]
    out={'question':'How accurate is the current combined chronological forecast for the individual decks users actually care about?',
         'model':'PR15 combined forecast; expanding chronological replay with >=10 prior matched cohorts; no retuning in this diagnostic.',
         'sample':{'events':len(events),'independent_cohorts':cohorts,'deck_event_rows':len(rows)},
         'predicted_share_bands':bands,'top_n':{'top5':top5,'top10':top10},'threshold_detection':thresholds,
         'interpretation_boundary':'Bands use predicted share, so grouping is available before the event. Pooled p50/p80/p90 errors are descriptive across correlated deck-event observations; cohort-weighted MAE/coverage are the primary summaries. This analysis does not select model parameters.'}
    OUTDIR.mkdir(parents=True,exist_ok=True); RESDIR.mkdir(parents=True,exist_ok=True)
    (OUTDIR/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
    lines=['# Forecast accuracy for the decks users care about','',
           'Diagnostic only. Uses PR #15 combined forecasts exactly as produced in the primary expanding chronological replay; **no model tuning**.','',
           f"Sample: **{len(events)} events / {cohorts} independent cohorts**.",'','## Error by predicted field share','',
           '| Predicted share | MAE | Bias | Within ±1pp | Within ±2pp | P80 abs error | P90 abs error |','|---|---:|---:|---:|---:|---:|---:|']
    for b in bands:
        lines.append(f"| {b['band']} | {b['cohort_weighted_mae_pp']:.2f}pp | {b['cohort_weighted_bias_pp']:+.2f}pp | {100*b['cohort_weighted_within_1pp']:.0f}% | {100*b['cohort_weighted_within_2pp']:.0f}% | {b['pooled_abs_error_p80_pp']:.2f}pp | {b['pooled_abs_error_p90_pp']:.2f}pp |")
    lines += ['','Bias = predicted minus actual. Percentile errors are descriptive, not formal confidence intervals.','','## Do we identify the decks at the top?','',
              f"Predicted top 5 contains **{100*top5['mean_identity_overlap']:.1f}%** of the actual top-5 identities on average and captures **{top5['mean_actual_field_share_captured_pct']:.1f}%** of the actual field.",
              f"Predicted top 10 contains **{100*top10['mean_identity_overlap']:.1f}%** of the actual top-10 identities and captures **{top10['mean_actual_field_share_captured_pct']:.1f}%** of the actual field.",
              f"For comparison, the actual top 10 itself accounts for **{top10['mean_actual_own_topn_mass_pct']:.1f}%** of the field on average.",'','## Threshold reliability','',
              '| Forecast threshold | Precision | Recall | Avg predicted decks | Avg actual decks | Avg missed |','|---|---:|---:|---:|---:|---:|']
    for t in thresholds:
        lines.append(f"| ≥{t['threshold_pct']:.0f}% | {100*t['mean_precision']:.0f}% | {100*t['mean_recall']:.0f}% | {t['mean_predicted_count']:.1f} | {t['mean_actual_count']:.1f} | {t['mean_missed']:.1f} |")
    lines += ['','Precision: of decks forecast above the threshold, how many actually finish above it. Recall: of decks that actually finish above it, how many the forecast put above it.','','## Practical use','',
              'The predicted-share bands can support empirical uncertainty language in the research output. Do not present P80/P90 as guaranteed statistical confidence intervals; they are historical error ranges from the replay sample.']
    (RESDIR/'README.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'events':len(events),'cohorts':cohorts,'bands':bands,'top5':top5,'top10':top10,'thresholds':thresholds},indent=2))
if __name__=='__main__':main()
