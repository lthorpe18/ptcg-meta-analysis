#!/usr/bin/env python3
"""Describe per-tournament Field Accuracy distribution for the concentration-corrected forecast."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from analyse_concentration_corrected_blend import load_rows, concentration_correct, weight, blend, accuracy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "concentration-corrected-blend" / "score-distribution.json"
RES = ROOT / "results" / "concentration-corrected-blend" / "SCORE_DISTRIBUTION.md"

# Hold the previously selected historical rule fixed so every event is scored comparably.
START, FLOOR, DECAY, STRENGTH, TOP_N = 0.80, 0.55, 0.010, 0.75, 10


def quantile(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    pos = (len(xs) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    frac = pos - lo
    return xs[lo] * (1-frac) + xs[hi] * frac


def score_row(r):
    online = concentration_correct(r["irl"], r["online"], TOP_N, STRENGTH)
    w = weight(r["days_since_major"], START, FLOOR, DECAY)
    return accuracy(blend(r["irl"], online, w), r["actual"])


def main():
    rows = load_rows()
    scored = [{"target_id":r["target_id"], "target_name":r["target_name"], "date":r["date"], "cohort_id":r["cohort_id"], "score":score_row(r)} for r in rows]
    scores = [r["score"] for r in scored]
    bins = [(0,75),(75,80),(80,85),(85,90),(90,101)]
    hist = []
    for lo, hi in bins:
        members=[x for x in scores if lo <= x < hi]
        hist.append({"range":f"{lo}-{hi if hi<101 else 100}","count":len(members),"pct":100*len(members)/len(scores)})
    summary={
        "model":"fixed 80% start / -1pp per day / 55% floor + 75% top-10 concentration correction",
        "event_count":len(scored),
        "cohort_count":len(set(r["cohort_id"] for r in scored)),
        "mean_event_accuracy":statistics.fmean(scores),
        "median":statistics.median(scores),
        "min":min(scores),
        "q1":quantile(scores,.25),
        "q3":quantile(scores,.75),
        "max":max(scores),
        "stddev":statistics.pstdev(scores),
        "histogram":hist,
        "events":sorted(scored,key=lambda x:(x["score"],x["date"],x["target_name"]))
    }
    OUT.parent.mkdir(parents=True,exist_ok=True); RES.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    lines=["# Forecast score distribution","",f"Fixed corrected rule across {len(scored)} settled tournaments.","",f"Mean event score: **{summary['mean_event_accuracy']:.2f}%**; median **{summary['median']:.2f}%**; Q1–Q3 **{summary['q1']:.2f}–{summary['q3']:.2f}%**; range **{summary['min']:.2f}–{summary['max']:.2f}%**.","","| Score band | Tournaments | Share |","|---|---:|---:|"]
    for h in hist: lines.append(f"| {h['range']}% | {h['count']} | {h['pct']:.1f}% |")
    lines += ["","## Events (lowest to highest)","","| Date | Tournament | Score |","|---|---|---:|"]
    for r in summary["events"]: lines.append(f"| {r['date']} | {r['target_name']} | {r['score']:.2f}% |")
    RES.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!='events'},indent=2))

if __name__ == "__main__": main()
