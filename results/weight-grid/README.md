# IRL weighting test

Complete-case settled sample: 34 tournaments across 25 independent cohorts.
Observed gap since previous major: 5–47 days (median 6.0).

## Higher start only (keep today's 2pp/day decay and 30% floor)

| Theoretical day-0 IRL start | Cohort-weighted accuracy | Event-weighted accuracy |
|---:|---:|---:|
| 70% | 83.30% | 83.27% |
| 75% | 83.57% | 83.50% |
| 80% | 83.76% | 83.65% |
| 85% | 83.86% | 83.74% |
| 90% | 83.89% | 83.74% |
| 95% | 83.82% | 83.66% |

## Best historical grid result

Start 80% IRL, decay 1.0pp/day, floor 55% IRL.
Cohort-weighted accuracy: 84.01%.

## Expanding walk-forward check

Tested 15 later cohorts after at least 10 prior cohorts were available.
Tuned rule: 83.93%
50/50: 83.84%
IRL-only: 82.20%
Current decay rule: 84.13%

Grid tuning is exploratory; the walk-forward result is the more important guard against overfitting.
