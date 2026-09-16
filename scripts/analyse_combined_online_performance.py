#!/usr/bin/env python3
"""Incremental test: frozen PR13 corrected IRL+Online forecast + PR11 performance.
Primary validation is expanding chronological replay. Secondary deck-level evaluation uses
the existing project convention: predicted OR actual share >=1%."""
from __future__ import annotations
import json, statistics
from collections import defaultdict
from datetime import date
from pathlib import Path
import analyse_irl_performance_to_next_irl as perf

ROOT=Path(__file__).resolve().parents[1]
INFILE=ROOT/'data/processed/model-results/baselines.json'
OUTDIR=ROOT/'data/processed/combined-online-performance'
RESDIR=ROOT/'results/combined-online-performance'
START,FLOOR,DECAY=0.80,0.55,0.010
CORRECTION,TOP_N,THRESH=0.75,10,0.01
RECENT_START=date(2025,8,28)
EPS=1e-10

def mean(x):
    x=list(x); return statistics.fmean(x) if x else None

def pmap(m): return {str(r['key']):float(r['predicted_pct'])/100 for r in m.get('prediction',[])}
def amap(m): return {str(r['key']):float(r['actual_pct'])/100 for r in m.get('prediction',[])}
def norm(d):
    d={k:max(0.,float(v)) for k,v in d.items()}; s=sum(d.values())
    return {k:v/s for k,v in d.items()} if s else {}
def topkeys(d,n): return [k for k,_ in sorted(d.items(),key=lambda x:(-x[1],x[0]))[:n]]
def acc(p,a):
    ks=set(p)|set(a); return 100*(1-.5*sum(abs(p.get(k,0)-a.get(k,0)) for k in ks))

def reconstruct_online(irl,half):
    raw={k:2*half.get(k,0)-irl.get(k,0) for k in set(irl)|set(half)}
    if min(raw.values(),default=0)<-1e-7: raise RuntimeError('Online reconstruction failed')
    return norm({k:0 if -EPS<v<0 else v for k,v in raw.items()})

def correct(irl,on):
    g=set(topkeys(irl,TOP_N)); pi=sum(irl.get(k,0) for k in g); po=sum(on.get(k,0) for k in g)
    tgt=po+CORRECTION*(pi-po); tail=1-po
    if po<=EPS or tail<=EPS:return dict(on)
    return norm({k:v*((tgt/po) if k in g else ((1-tgt)/tail)) for k,v in on.items()})

def baseline(irl,on,days):
    w=max(FLOOR,min(START,START-DECAY*days)); co=correct(irl,on)
    return norm({k:w*irl.get(k,0)+(1-w)*co.get(k,0) for k in set(irl)|set(co)})

def load_rows():
    d=json.loads(INFILE.read_text()) ; out=[]
    for t in d.get('targets',[]):
        if not t.get('target_eligible_ge_95') or t.get('window_class')!='settled':continue
        ms=t.get('models',{}); im=ms.get('irl_only',{}); hm=ms.get('fifty_fifty',{}); cm=ms.get('current_v2_1',{})
        if not(im.get('available') and hm.get('available') and cm.get('available')):continue
        irl=pmap(im); on=reconstruct_online(irl,pmap(hm)); days=int(t['days_since_major'])
        out.append({'target_id':str(t['target_id']),'date':t['target_start_date'],'cohort_id':t['cohort_id'],
                    'baseline':baseline(irl,on,days),'actual':amap(im)})
    return out

def feature_map():
    pairs=perf.build_pairs(perf.build_cohorts()); events=perf.load_performance_events()
    scenario=next(s for s in perf.SCENARIOS if s.get('primary')); out={}
    for p in pairs:
        f=perf.composition_feature(p,scenario,events)
        if f is not None: out[p['target_cohort']]=f['z']
    return out

def matched():
    fm=feature_map(); out=[]
    for r in load_rows():
        if r['cohort_id'] in fm: out.append({**r,'z':fm[r['cohort_id']]})
    if not out: raise RuntimeError('No matched rows')
    return out

def cohort_order(rows):
    ds={}
    for r in rows: ds[r['cohort_id']]=min(ds.get(r['cohort_id'],r['date']),r['date'])
    return sorted(ds,key=lambda c:(ds[c],c))

def fit_beta(rows):
    by=defaultdict(list)
    for r in rows:by[r['cohort_id']].append(r)
    num=den=0.
    for rs in by.values():
        cn=cd=0.
        for r in rs:
            ks=set(r['baseline'])|set(r['actual'])|set(r['z']); n=max(1,len(ks))
            cn+=sum(r['z'].get(k,0)*(r['actual'].get(k,0)-r['baseline'].get(k,0)) for k in ks)/n
            cd+=sum(r['z'].get(k,0)**2 for k in ks)/n
        num+=cn/len(rs); den+=cd/len(rs)
    return num/den if den>1e-16 else 0.

def apply(r,b):
    return norm({k:r['baseline'].get(k,0)+b*r['z'].get(k,0) for k in set(r['baseline'])|set(r['z'])})

def metrics(p,a):
    ks=set(p)|set(a); rel=[k for k in ks if p.get(k,0)>=THRESH or a.get(k,0)>=THRESH]
    ae=[100*abs(p.get(k,0)-a.get(k,0)) for k in rel]; t10=topkeys(a,10)
    return {'rel_mae':mean(ae),'rel_within1':sum(x<=1 for x in ae)/len(ae) if ae else None,
            'top10_mae':mean(100*abs(p.get(k,0)-a.get(k,0)) for k in t10)}

def eval_rows(rows,b):
    ev=[]
    for r in rows:
        c=apply(r,b); bm=metrics(r['baseline'],r['actual']); cm=metrics(c,r['actual'])
        ev.append({'cohort_id':r['cohort_id'],'date':r['date'],'ba':acc(r['baseline'],r['actual']),'ca':acc(c,r['actual']),
                   'br':bm['rel_mae'],'cr':cm['rel_mae'],'bw':bm['rel_within1'],'cw':cm['rel_within1'],
                   'bt':bm['top10_mae'],'ct':cm['top10_mae']})
    by=defaultdict(list)
    for e in ev:by[e['cohort_id']].append(e)
    out=[]
    for cid,rs in by.items():
        out.append({'cohort_id':cid,'date':min(x['date'] for x in rs),**{k:mean(x[k] for x in rs) for k in ['ba','ca','br','cr','bw','cw','bt','ct']}})
    return out

def summary(rs):
    return {'tested_cohorts':len(rs),'baseline_accuracy':mean(x['ba'] for x in rs),'combined_accuracy':mean(x['ca'] for x in rs),
            'accuracy_delta_pp':mean(x['ca']-x['ba'] for x in rs),'cohorts_improved':sum(x['ca']>x['ba']+1e-9 for x in rs),
            'cohorts_worse':sum(x['ca']<x['ba']-1e-9 for x in rs),'baseline_relevant_mae_pp':mean(x['br'] for x in rs),
            'combined_relevant_mae_pp':mean(x['cr'] for x in rs),'relevant_mae_delta_pp':mean(x['cr']-x['br'] for x in rs),
            'baseline_relevant_within_1pp':mean(x['bw'] for x in rs),'combined_relevant_within_1pp':mean(x['cw'] for x in rs),
            'baseline_actual_top10_mae_pp':mean(x['bt'] for x in rs),'combined_actual_top10_mae_pp':mean(x['ct'] for x in rs),'rows':rs}

def walk(rows,mintrain):
    cs=cohort_order(rows); rr=[]
    for i,c in enumerate(cs):
        if i<mintrain:continue
        train=[r for r in rows if r['cohort_id'] in set(cs[:i])]; test=[r for r in rows if r['cohort_id']==c]
        b=fit_beta(train); e=eval_rows(test,b)[0]; e['beta']=b; rr.append(e)
    s=summary(rr); s['min_prior_cohorts']=mintrain; s['mean_beta']=mean(x['beta'] for x in rr); return s

def recent(rows):
    tr=[r for r in rows if date.fromisoformat(r['date'])<RECENT_START]; te=[r for r in rows if date.fromisoformat(r['date'])>=RECENT_START]
    b=fit_beta(tr); s=summary(eval_rows(te,b)); s['beta']=b; s['train_cohorts']=len(set(r['cohort_id'] for r in tr)); s['cutoff']=RECENT_START.isoformat(); return s

def main():
    rows=matched(); cs=cohort_order(rows); wf=walk(rows,10); wf15=walk(rows,15); rec=recent(rows); ba=fit_beta(rows); full=summary(eval_rows(rows,ba)); full['beta']=ba
    out={'question':'Does PR11 previous-major performance add value after frozen PR13 concentration-corrected IRL+Online?',
         'sample':{'events':len(rows),'cohorts':len(cs)},
         'frozen_baseline':{'irl_start':START,'irl_floor':FLOOR,'irl_decay_per_day':DECAY,'top_n':TOP_N,'concentration_correction':CORRECTION},
         'performance':'PR11 primary bounded Day2 log2 lift, previous IRL share >=1%; beta fitted to residual after baseline',
         'relevant_decks':'predicted OR actual share >=1%; evaluation only','full_sample_descriptive':full,
         'expanding_walk_forward_primary':wf,'expanding_walk_forward_min15_sensitivity':wf15,'frozen_recent_test':rec,
         'boundary':'Component signals were discovered on overlapping history; chronological replay is not a genuinely untouched future event.'}
    OUTDIR.mkdir(parents=True,exist_ok=True); RESDIR.mkdir(parents=True,exist_ok=True)
    (OUTDIR/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
    lines=['# Combined corrected Online + previous-major performance','','## Primary expanding replay',
           f"Matched sample: **{len(rows)} events / {len(cs)} cohorts**; **{wf['tested_cohorts']}** later cohorts tested after 10 prior cohorts.",
           f"Field Accuracy: **{wf['baseline_accuracy']:.2f}% -> {wf['combined_accuracy']:.2f}%** ({wf['accuracy_delta_pp']:+.3f}pp).",
           f"Improved **{wf['cohorts_improved']}/{wf['tested_cohorts']}** cohorts; worsened **{wf['cohorts_worse']}/{wf['tested_cohorts']}**.",'',
           '## Decks that matter (predicted OR actual >=1%)',
           f"MAE: **{wf['baseline_relevant_mae_pp']:.2f}pp -> {wf['combined_relevant_mae_pp']:.2f}pp** ({wf['relevant_mae_delta_pp']:+.3f}pp; lower is better).",
           f"Within 1pp of actual: **{100*wf['baseline_relevant_within_1pp']:.1f}% -> {100*wf['combined_relevant_within_1pp']:.1f}%**.",
           f"Actual top-10 MAE: **{wf['baseline_actual_top10_mae_pp']:.2f}pp -> {wf['combined_actual_top10_mae_pp']:.2f}pp**.",'','## Robustness',
           f"Replay after 15 prior cohorts: **{wf15['baseline_accuracy']:.2f}% -> {wf15['combined_accuracy']:.2f}%** ({wf15['accuracy_delta_pp']:+.3f}pp).",
           f"Frozen recent split: **{rec['baseline_accuracy']:.2f}% -> {rec['combined_accuracy']:.2f}%** ({rec['accuracy_delta_pp']:+.3f}pp).",'',
           'The >=1% and top-10 views are evaluation metrics only and were not used to fit beta.']
    (RESDIR/'README.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'cohorts':len(cs),'wf':wf['tested_cohorts'],'baseline':wf['baseline_accuracy'],'combined':wf['combined_accuracy'],'delta':wf['accuracy_delta_pp'],
                      'rel_mae_before':wf['baseline_relevant_mae_pp'],'rel_mae_after':wf['combined_relevant_mae_pp'],'top10_before':wf['baseline_actual_top10_mae_pp'],'top10_after':wf['combined_actual_top10_mae_pp']},indent=2))
if __name__=='__main__':main()
