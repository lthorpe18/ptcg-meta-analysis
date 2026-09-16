#!/usr/bin/env python3
"""Diagnostic for a user-facing next-IRL forecast intelligence layer.

Uses the PR15 combined model exactly as produced in its primary expanding replay.
No forecast parameter is tuned here. We ask:
1) how should empirical uncertainty be communicated by forecast-share band?
2) when do Online movement and prior-major performance give a useful explanation?
3) how reliable is forecast movement direction relative to the last IRL anchor?
"""
from __future__ import annotations
import json, statistics
from collections import defaultdict
from pathlib import Path
import analyse_combined_online_performance as combo

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed/forecast-presentation-intelligence/summary.json'
RES=ROOT/'results/forecast-presentation-intelligence/README.md'
BANDS=[('10%+',10,1e9),('5-10%',5,10),('2-5%',2,5),('1-2%',1,2)]
MAT_PERF=0.25   # pp: only call performance out when it visibly changes the displayed share
MOVE_THRESHOLDS=[0.5,1.0]

def mean(xs):
    xs=list(xs); return statistics.fmean(xs) if xs else None

def quantile(xs,q):
    xs=sorted(xs)
    if not xs:return None
    p=(len(xs)-1)*q; lo=int(p); hi=min(lo+1,len(xs)-1); f=p-lo
    return xs[lo]*(1-f)+xs[hi]*f

def band(v):
    for name,lo,hi in BANDS:
        if lo<=v<hi:return name
    return '<1%'

def raw_components():
    data=json.loads(combo.INFILE.read_text())
    out={}
    for t in data.get('targets',[]):
        if not t.get('target_eligible_ge_95') or t.get('window_class')!='settled':continue
        ms=t.get('models',{}); im=ms.get('irl_only',{}); hm=ms.get('fifty_fifty',{}); cm=ms.get('current_v2_1',{})
        if not(im.get('available') and hm.get('available') and cm.get('available')):continue
        irl=combo.pmap(im); online=combo.reconstruct_online(irl,combo.pmap(hm)); days=int(t['days_since_major'])
        out[str(t['target_id'])]={'irl':irl,'online':online,'corrected_online':combo.correct(irl,online),'days':days}
    return out

def replay_decks():
    rows=combo.matched(); cs=combo.cohort_order(rows); raw=raw_components(); obs=[]
    for i,cid in enumerate(cs):
        if i<10:continue
        train=[r for r in rows if r['cohort_id'] in set(cs[:i])]
        beta=combo.fit_beta(train)
        for r in [x for x in rows if x['cohort_id']==cid]:
            pred=combo.apply(r,beta); rc=raw[r['target_id']]
            keys=set(pred)|set(r['actual'])|set(rc['irl'])|set(rc['online'])|set(r['baseline'])|set(r['z'])
            for k in keys:
                p=100*pred.get(k,0); a=100*r['actual'].get(k,0); irl=100*rc['irl'].get(k,0); on=100*rc['online'].get(k,0)
                base=100*r['baseline'].get(k,0); perf_delta=p-base; online_delta=on-irl
                obs.append({'cohort_id':cid,'target_id':r['target_id'],'date':r['date'],'key':k,'pred':p,'actual':a,'irl':irl,'online':on,
                            'online_delta':online_delta,'perf_delta':perf_delta,'forecast_delta':p-irl,'actual_delta':a-irl,
                            'abs_error':abs(p-a),'band':band(p)})
    return obs

def weighted_group(obs,field):
    by=defaultdict(list)
    for o in obs:by[o['cohort_id']].append(o)
    vals=[]
    for rs in by.values():
        x=[r[field] for r in rs]
        if x:vals.append(mean(x))
    return mean(vals)

def uncertainty(obs):
    out=[]
    for name,_,_ in BANDS:
        rs=[o for o in obs if o['band']==name]
        by=defaultdict(list)
        for r in rs:by[r['cohort_id']].append(r)
        out.append({'band':name,'observations':len(rs),'cohorts':len(by),'mae_pp':weighted_group(rs,'abs_error'),
                    'p50_abs_error_pp':quantile([r['abs_error'] for r in rs],.5),'p80_abs_error_pp':quantile([r['abs_error'] for r in rs],.8),
                    'p90_abs_error_pp':quantile([r['abs_error'] for r in rs],.9)})
    return out

def explanation(obs):
    rel=[o for o in obs if o['pred']>=1 or o['actual']>=1]
    material=[o for o in rel if abs(o['perf_delta'])>=MAT_PERF]
    agree=[]; disagree=[]
    for o in material:
        if abs(o['online_delta'])<0.01:continue
        (agree if o['online_delta']*o['perf_delta']>0 else disagree).append(o)
    def s(rs):
        return {'observations':len(rs),'cohorts':len(set(x['cohort_id'] for x in rs)),'mae_pp':weighted_group(rs,'abs_error'),
                'movement_direction_correct':weighted_group([{**x,'ok':1.0 if x['forecast_delta']*x['actual_delta']>0 else 0.0} for x in rs if abs(x['forecast_delta'])>=.5 and abs(x['actual_delta'])>0.01],'ok')}
    return {'relevant_observations':len(rel),'material_performance_threshold_pp':MAT_PERF,
            'material_performance_share':len(material)/len(rel) if rel else None,
            'material_performance_abs_delta_median_pp':quantile([abs(x['perf_delta']) for x in material],.5),
            'signal_agreement':s(agree),'signal_disagreement':s(disagree),
            'performance_adjustment_abs_p50_pp':quantile([abs(x['perf_delta']) for x in rel],.5),
            'performance_adjustment_abs_p80_pp':quantile([abs(x['perf_delta']) for x in rel],.8),
            'online_movement_abs_p50_pp':quantile([abs(x['online_delta']) for x in rel],.5),
            'online_movement_abs_p80_pp':quantile([abs(x['online_delta']) for x in rel],.8)}

def movement(obs):
    rel=[o for o in obs if o['pred']>=1 or o['actual']>=1]
    out=[]
    for th in MOVE_THRESHOLDS:
        movers=[o for o in rel if abs(o['forecast_delta'])>=th]
        correct=[{**o,'ok':1.0 if o['forecast_delta']*o['actual_delta']>0 else 0.0} for o in movers]
        # Was movement estimate closer than simply repeating last IRL?
        better=[{**o,'better':1.0 if abs(o['pred']-o['actual'])<abs(o['irl']-o['actual']) else 0.0} for o in movers]
        out.append({'forecast_move_threshold_pp':th,'observations':len(movers),'cohorts':len(set(o['cohort_id'] for o in movers)),
                    'direction_correct':weighted_group(correct,'ok'),'forecast_beats_last_irl':weighted_group(better,'better'),
                    'mean_abs_forecast_move_pp':weighted_group([{**o,'x':abs(o['forecast_delta'])} for o in movers],'x'),
                    'mean_abs_actual_move_pp':weighted_group([{**o,'x':abs(o['actual_delta'])} for o in movers],'x')})
    return out

def main():
    obs=replay_decks(); u=uncertainty(obs); e=explanation(obs); m=movement(obs)
    out={'question':'How should the validated next-IRL forecast be presented so users see the estimate, anchor, movement evidence, performance explanation and realistic uncertainty?',
         'model':'PR15 combined model primary expanding chronological replay; no retuning.',
         'sample':{'events':len(set(o['target_id'] for o in obs)),'cohorts':len(set(o['cohort_id'] for o in obs)),'deck_event_rows':len(obs)},
         'uncertainty_by_predicted_share':u,'explanation_diagnostic':e,'movement_diagnostic':m,
         'prior_archetype_volatility_evidence':'PR14 independently found prior residual SD predicts next absolute error (r=0.236; low-volatility 0.68pp vs high-volatility 1.28pp). Not recomputed here because PR14 is a sibling research branch.',
         'boundary':'Empirical P80/P90 values are historical replay error ranges, not formal probabilistic confidence intervals. Signal explanation diagnostics are descriptive and do not tune the forecast.'}
    OUT.parent.mkdir(parents=True,exist_ok=True); RES.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    lines=['# Forecast presentation intelligence','','This is a **presentation/evaluation analysis**, not another forecast optimisation. It uses the PR #15 chronological combined forecasts unchanged.','',
           '## Empirical uncertainty by displayed forecast share','',
           '| Forecast share | MAE | Historical P80 abs error | Historical P90 abs error |','|---|---:|---:|---:|']
    for x in u: lines.append(f"| {x['band']} | {x['mae_pp']:.2f}pp | {x['p80_abs_error_pp']:.2f}pp | {x['p90_abs_error_pp']:.2f}pp |")
    lines += ['','These ranges are descriptive historical errors, not guaranteed confidence intervals.','',
              '## Which evidence deserves an explanation?','',
              f"Among decks forecast or observed at >=1%, the median absolute Online-vs-last-IRL movement is **{e['online_movement_abs_p50_pp']:.2f}pp** (P80 **{e['online_movement_abs_p80_pp']:.2f}pp**).",
              f"The performance term is smaller: median absolute adjustment **{e['performance_adjustment_abs_p50_pp']:.2f}pp**, P80 **{e['performance_adjustment_abs_p80_pp']:.2f}pp**.",
              f"Only **{100*e['material_performance_share']:.1f}%** of relevant deck observations receive a performance adjustment of at least {MAT_PERF:.2f}pp, so performance should be shown as a callout only when material rather than as a permanent headline column.",'',
              'When a material performance adjustment and Online movement point the same way, historical MAE is '
              f"**{e['signal_agreement']['mae_pp']:.2f}pp**; when they disagree it is **{e['signal_disagreement']['mae_pp']:.2f}pp**. This is diagnostic, not a new confidence formula.",'',
              '## Can we trust the mover direction?','']
    for x in m:
        lines.append(f"For decks moved at least **{x['forecast_move_threshold_pp']:.1f}pp** from last IRL, the forecast gets the direction of the eventual move right **{100*x['direction_correct']:.1f}%** of the time and beats simply repeating last IRL on **{100*x['forecast_beats_last_irl']:.1f}%** of those observations.")
    lines += ['','## Presentation conclusion','',
              'Recommended research output hierarchy: **Forecast %** first; **Last IRL -> Online since** as the visible evidence trail; a compact mover label; **performance only when its adjustment is material**; and an empirical uncertainty cue driven primarily by forecast-share band, with prior archetype volatility available as a secondary confidence modifier where enough history exists.','',
              'Do not turn the P80/P90 ranges into formal confidence intervals without a separate calibration study.']
    RES.write_text('\n'.join(lines)+'\n')
    print(json.dumps({'sample':out['sample'],'uncertainty':u,'explanation':e,'movement':m},indent=2))
if __name__=='__main__':main()
