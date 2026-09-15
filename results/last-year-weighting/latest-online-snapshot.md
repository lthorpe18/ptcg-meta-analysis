# Latest large-Online snapshot analysis

Evidence window: **2025-08-28 to 2026-08-28**; **16 tournaments / 11 independent cohorts**.

Question: can a small snapshot of the latest large Online tournaments beat aggregating all qualifying Online evidence since the previous IRL major?

## Scenario coverage

| Online snapshot | Events | Cohorts | Full coverage? | Mean selected-event size | Mean age to target |
|---|---:|---:|---|---:|---:|
| Latest 1 Online >= 50 players | 16 | 11 | Yes | 127 | 4.8d |
| Latest 2 Online >= 50 players | 16 | 11 | Yes | 133 | 4.8d |
| Latest 3 Online >= 50 players | 16 | 11 | Yes | 132 | 4.9d |
| Latest 4 Online >= 50 players | 16 | 11 | Yes | 123 | 5.1d |
| Latest 5 Online >= 50 players | 16 | 11 | Yes | 132 | 5.3d |
| Latest 1 Online >= 100 players | 16 | 11 | Yes | 140 | 4.8d |
| Latest 2 Online >= 100 players | 16 | 11 | Yes | 162 | 5.0d |
| Latest 3 Online >= 100 players | 15 | 10 | No | 171 | 5.4d |
| Latest 4 Online >= 100 players | 15 | 10 | No | 164 | 5.7d |
| Latest 5 Online >= 100 players | 14 | 9 | No | 168 | 5.9d |
| Latest 1 Online >= 150 players | 15 | 10 | No | 177 | 5.4d |
| Latest 2 Online >= 150 players | 14 | 9 | No | 189 | 5.7d |
| Latest 3 Online >= 150 players | 11 | 7 | No | 196 | 6.3d |
| Latest 4 Online >= 150 players | 11 | 7 | No | 198 | 6.7d |
| Latest 5 Online >= 150 players | 9 | 6 | No | 203 | 7.1d |
| Latest 1 Online >= 200 players | 12 | 8 | No | 235 | 7.2d |
| Latest 2 Online >= 200 players | 9 | 6 | No | 250 | 8.0d |
| Latest 3 Online >= 200 players | 9 | 6 | No | 247 | 8.5d |
| Latest 4 Online >= 200 players | 7 | 5 | No | 250 | 8.9d |
| Latest 5 Online >= 200 players | 4 | 3 | No | 248 | 9.4d |

## Broad post-major Online comparators

| Model | Accuracy |
|---|---:|
| All post-major Online, flat 50/50 | 84.11% |
| All post-major Online, best flat (60% IRL) | 84.40% |
| All post-major Online, best dynamic (95% start / -3pp/day / 20% floor) | 84.78% |

## Best snapshot results in-sample

At fixed 50/50: **Latest 5 Online >= 50 players = 83.52%**.
With flat IRL split tuned: **Latest 5 Online >= 50 players, 70% IRL / 30% Online = 84.19%**.
With dynamic IRL rule tuned: **Latest 5 Online >= 50 players, 100% start / -3pp/day / 40% floor = 84.62%**.

### Top full-coverage snapshots with their own best flat split

| Snapshot | Best IRL split | Accuracy |
|---|---:|---:|
| Latest 5 Online >= 50 players | 70% | 84.19% |
| Latest 4 Online >= 50 players | 70% | 84.03% |
| Latest 2 Online >= 50 players | 75% | 83.81% |
| Latest 3 Online >= 50 players | 75% | 83.79% |
| Latest 2 Online >= 100 players | 75% | 83.73% |
| Latest 1 Online >= 50 players | 85% | 83.17% |
| Latest 1 Online >= 100 players | 80% | 83.07% |

## Fixed chronological holdout

Tune on first 6 cohorts; score the frozen selection on final 5 untouched cohorts.

| Family | Training selection | Holdout accuracy |
|---|---|---:|
| Snapshot at fixed 50/50 | Latest 5 Online >= 50 players | 82.81% |
| Snapshot + flat split | Latest 5 Online >= 50 players, 65% IRL | 83.88% |
| Snapshot + dynamic IRL | Latest 5 Online >= 50 players, 85%/-2pp/40% | 84.33% |
| Broad Online + flat split | all post-major, 55% IRL | 83.73% |
| Broad Online + dynamic IRL | all post-major, 80%/-2pp/25% | 84.30% |

**Interpretation boundary:** full-period winners are in-sample. The five-cohort chronological holdout is more informative but still small; incomplete high-threshold scenarios are not promoted over full-coverage alternatives.
