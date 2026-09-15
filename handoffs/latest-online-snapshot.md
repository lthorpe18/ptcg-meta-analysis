# Latest Online snapshot experiment handoff

Date: 15 September 2026
Repository: `lthorpe18/ptcg-meta-analysis`
Base research state: `historical-online-chunked` at `67310cbab568a2632cec96cedfce1b8118d25d3c`
Working branch / PR: `research/last-year-weighting` / PR #8

## Explicit owner question

Test whether the latest IRL weekend should be blended against only the latest few large Online tournaments rather than all qualifying post-major Online evidence.

## Scenarios

**Verified:** tested latest N = 1, 2, 3, 4, 5 Online tournaments, with minimum field-size thresholds 50, 100, 150 and 200 players. Tournaments were selected chronologically from the existing same-format post-major evidence before each target cutoff. Selected tournaments were aggregated by deck/player entries, not event-equal.

For full-coverage scenarios, tested:
- fixed 50/50;
- flat IRL weights 0-100% in 5pp steps;
- the existing 225-rule dynamic IRL grid (80-100% starts, 1-5pp/day decay, 10-50% floors).

Primary metric remains cohort-weighted Field Accuracy on the frozen 2025-08-28 to 2026-08-28 recent-year sample: 16 tournaments / 11 independent cohorts, settled only, >=95% IRL capture.

## Coverage finding

**Verified:** size thresholds quickly reduce historical coverage.
- Latest 1-5 at >=50 players: complete 16/16 events, 11/11 cohorts.
- Latest 1-2 at >=100: complete; latest 3 >=100: 15/16 events, 10/11 cohorts; latest 5 >=100: 14/16, 9 cohorts.
- Latest 3 >=150: 11/16 events, 7 cohorts.
- Latest 3 >=200: 9/16 events, 6 cohorts.

Therefore incomplete threshold scenarios were also compared with the broad post-major model on exactly the same target subset; sparse scenarios were not promoted as headline winners.

## Full-coverage results

Broad post-major Online comparators:
- flat 50/50: 84.11%
- best flat: 60% IRL / 40% Online = 84.40%
- best dynamic: 95% start / -3pp/day / 20% floor = 84.78%

Best latest-N snapshot results:
- fixed 50/50: latest 5 >=50 = 83.52%
- best flat: latest 5 >=50, 70% IRL / 30% Online = 84.19%
- best dynamic: latest 5 >=50, 100% start / -3pp/day / 40% floor = 84.62%

**Verified:** on the complete recent-year sample, every full-coverage latest-N snapshot underperformed the broad post-major Online aggregation after comparable tuning.

## Chronological holdout

Tune on first six cohorts; score frozen choices on final five cohorts.

- latest-5 >=50 snapshot + flat split: 65% IRL -> 83.88%
- broad post-major + flat split: 55% IRL -> 83.73%
- latest-5 >=50 snapshot + dynamic IRL: 85% start / -2pp/day / 40% floor -> 84.33%
- broad post-major + dynamic IRL: 80% start / -2pp/day / 25% floor -> 84.30%

**Verified:** latest-5 gives only +0.03pp over broad Online in the dynamic holdout. With only five independent test cohorts, this is effectively a tie rather than evidence that the snapshot is superior.

## Matched sensitivity for 'large' scenarios

Compared each incomplete size-threshold scenario against broad Online on exactly the same available targets.

Key results:
- latest 3 >=100: dynamic 84.74% vs broad 85.00% on 15 events / 10 cohorts = -0.25pp.
- latest 5 >=100: dynamic 84.63% vs broad 84.71% on 14 events / 9 cohorts = -0.08pp.
- latest 3 >=150: dynamic 83.89% vs broad 84.32% on 11 events / 7 cohorts = -0.43pp.
- latest 3 >=200: dynamic 83.47% vs broad 84.07% on 9 events / 6 cohorts = -0.60pp.
- the apparent latest-5 >=200 improvement (+0.28pp) is based on only 4 events / 3 cohorts and is too sparse to treat as useful evidence.

**Verified:** the literal 'last ~3 large Online tournaments' hypothesis is not supported by this recent-year archive. Raising the size threshold generally reduces coverage and does not improve matched accuracy.

## Interpretation

**Verified:** Online evidence benefits from having more than only the latest 1-3 events. The best snapshot family is the least restrictive tested one: latest 5 qualifying >=50-player events.

**Inferred:** the broad post-major aggregation likely gains useful stability from additional tournaments; aggressively narrowing to a few large events adds sampling noise that outweighs any extra freshness signal.

**Verified:** latest-5 >=50 is a plausible simplification because its chronological dynamic result (84.33%) is effectively tied with broad evidence (84.30%), but it is not demonstrated to be more accurate. The full-period comparison favours broad evidence (84.78% vs 84.62%).

This reinforces the prior finding that the material modelling lever is the overall IRL/Online weight and its decay after the latest major. Fine-grained choices about Online recency/windowing have so far changed holdout accuracy only by hundredths of a percentage point.

## Reproducibility

- Main analysis: `scripts/analyse_latest_online_snapshot.py`
- Matched sensitivity: `scripts/analyse_snapshot_matched_sensitivity.py`
- Main JSON: `data/processed/last-year-weighting/latest-online-snapshot/summary.json`
- Matched JSON: `data/processed/last-year-weighting/latest-online-snapshot/matched-sensitivity.json`
- Reports: `results/last-year-weighting/latest-online-snapshot.md` and `results/last-year-weighting/latest-online-snapshot-matched.md`
- Successful workflows: `34966864047` and `34967031612`

## Exact next action

None authorised. This remains one-off exploratory work on PR #8. If no further analysis is wanted, PR #8 can be closed without merging while preserving the audit trail. Do not change the production PTCG Tools formula from this result without a separate explicit adoption decision.
