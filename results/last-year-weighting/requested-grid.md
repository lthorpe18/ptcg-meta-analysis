# Exhaustive requested IRL-weight grid

Evidence window: **2025-08-28 to 2026-08-28**.
Sample: **16 tournaments / 11 independent cohorts**.
Tested **225 combinations**.

IRL weight = max(floor, initial IRL weight − daily percentage-point loss × days since previous major). Online is the remainder.

## Baselines

| Baseline | Cohort-weighted accuracy |
|---|---:|
| Flat 50/50 | 84.11% |
| 100% IRL | 82.20% |
| 100% Online | 76.37% |

## Best in-sample rule

**95% initial IRL, lose 3pp/day, floor 20% IRL** = **84.78%**.
Vs 50/50: **+0.66pp**; vs 100% IRL: **+2.57pp**; vs 100% Online: **+8.40pp**.

## How many rules beat each baseline?

- 50/50: **186 / 225**
- 100% IRL: **225 / 225**
- 100% Online: **225 / 225**
- all three: **186 / 225**

## Top 15 in-sample rules

| Rank | Initial IRL | Loss/day | Floor | Accuracy | vs 50/50 | vs IRL | vs Online |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 95% | 3pp | 20% | 84.78% | +0.66 | +2.57 | +8.40 |
| 2 | 95% | 3pp | 15% | 84.78% | +0.66 | +2.57 | +8.40 |
| 3 | 95% | 3pp | 25% | 84.77% | +0.66 | +2.57 | +8.40 |
| 4 | 85% | 2pp | 30% | 84.77% | +0.66 | +2.56 | +8.40 |
| 5 | 90% | 3pp | 20% | 84.77% | +0.66 | +2.56 | +8.40 |
| 6 | 90% | 3pp | 15% | 84.77% | +0.66 | +2.56 | +8.40 |
| 7 | 95% | 3pp | 30% | 84.76% | +0.65 | +2.56 | +8.39 |
| 8 | 90% | 3pp | 25% | 84.76% | +0.65 | +2.56 | +8.39 |
| 9 | 95% | 3pp | 10% | 84.76% | +0.65 | +2.56 | +8.39 |
| 10 | 85% | 2pp | 35% | 84.76% | +0.65 | +2.56 | +8.39 |
| 11 | 85% | 2pp | 25% | 84.76% | +0.65 | +2.55 | +8.39 |
| 12 | 90% | 3pp | 30% | 84.76% | +0.64 | +2.55 | +8.38 |
| 13 | 95% | 3pp | 35% | 84.75% | +0.64 | +2.55 | +8.38 |
| 14 | 85% | 2pp | 20% | 84.75% | +0.64 | +2.55 | +8.38 |
| 15 | 80% | 2pp | 25% | 84.75% | +0.63 | +2.54 | +8.37 |

## Fixed chronological holdout

Tune on first 6 recent cohorts; score the selected rule on the final 5 untouched cohorts.
Training selected **80% start / 2pp-day / 25% floor**.

| Holdout model | Cohort accuracy |
|---|---:|
| Training-selected requested-grid rule | **84.30%** |
| Flat 50/50 | 83.40% |
| 100% IRL | 83.08% |
| 100% Online | 75.14% |

Only five independent holdout cohorts are available, so this is directional rather than decisive.

## Best result available at each initial weight

| Initial IRL | Best accuracy | Best loss/day | Best floor |
|---:|---:|---:|---:|
| 100% | 84.74% | 4pp | 20% |
| 95% | 84.78% | 3pp | 20% |
| 90% | 84.77% | 3pp | 20% |
| 85% | 84.77% | 2pp | 30% |
| 80% | 84.75% | 2pp | 25% |

## Best result available at each daily loss

| Loss/day | Best accuracy | Best initial | Best floor |
|---:|---:|---:|---:|
| 5pp | 84.69% | 100% | 50% |
| 4pp | 84.74% | 100% | 20% |
| 3pp | 84.78% | 95% | 20% |
| 2pp | 84.77% | 85% | 30% |
| 1pp | 84.60% | 80% | 50% |

## Best result available at each floor

| Floor | Best accuracy | Best initial | Best loss/day |
|---:|---:|---:|---:|
| 50% | 84.69% | 85% | 2pp |
| 45% | 84.72% | 85% | 2pp |
| 40% | 84.74% | 85% | 2pp |
| 35% | 84.76% | 85% | 2pp |
| 30% | 84.77% | 85% | 2pp |
| 25% | 84.77% | 95% | 3pp |
| 20% | 84.78% | 95% | 3pp |
| 15% | 84.78% | 95% | 3pp |
| 10% | 84.76% | 95% | 3pp |

Full 225-rule ranking is stored in `data/processed/last-year-weighting/requested-grid/all_rules.csv` and `summary.json`.

**Interpretation boundary:** the full-period ranking is in-sample. The chronological holdout is the stronger validation check, but only five independent test cohorts are available.
