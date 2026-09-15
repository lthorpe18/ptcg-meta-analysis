# Flat splits and Online-recency analysis

Evidence window: **2025-08-28 to 2026-08-28**; **16 tournaments / 11 independent cohorts**.

## Baselines

| Model | Cohort accuracy |
|---|---:|
| 100% Online | 78.39% |
| 100% IRL | 82.20% |
| Flat 50/50 | 84.11% |

## 1. Flat split sweep (equal/current Online aggregation)

Best flat split: **60% IRL / 40% Online = 84.40%**.

| IRL / Online | Accuracy |
|---|---:|
| 60% / 40% | 84.40% |
| 65% / 35% | 84.40% |
| 55% / 45% | 84.31% |
| 70% / 30% | 84.30% |
| 75% / 25% | 84.14% |
| 50% / 50% | 84.11% |
| 80% / 20% | 83.91% |
| 45% / 55% | 83.84% |
| 85% / 15% | 83.58% |
| 40% / 60% | 83.46% |
| 90% / 10% | 83.20% |
| 35% / 65% | 83.01% |
| 95% / 5% | 82.73% |
| 30% / 70% | 82.52% |
| 100% / 0% | 82.20% |
| 25% / 75% | 81.99% |
| 20% / 80% | 81.38% |
| 15% / 85% | 80.72% |
| 10% / 90% | 79.99% |
| 5% / 95% | 79.21% |
| 0% / 100% | 78.39% |

## 2. Online recency at fixed 50/50 IRL/Online

Best recency method at 50/50: **Exponential, 7-day half-life = 84.14%**.

| Online treatment | Accuracy |
|---|---:|
| Exponential, 7-day half-life | 84.14% |
| Exponential, 14-day half-life | 84.13% |
| Exponential, 21-day half-life | 84.13% |
| Exponential, 3-day half-life | 84.12% |
| Exponential, 28-day half-life | 84.12% |
| Last 28 days only | 84.12% |
| Equal/current | 84.11% |
| Last 21 days only | 84.09% |
| Linear recency | 83.86% |

## 3. Best flat split after allowing Online recency

Best: **65% IRL / 35% Online with Exponential, 3-day half-life = 84.45%**.

## 4. Combined Online recency + dynamic IRL grid

Best in-sample combination: **95% IRL start, -3pp/day, 20% floor + Exponential, 3-day half-life = 84.88%**.

## 5. Fixed chronological holdout

Tune on first 6 cohorts; score on final 5 untouched cohorts.

| Selection family | Training-selected model | Holdout accuracy |
|---|---|---:|
| Flat split, equal Online | 55% IRL / 45% Online | 83.73% |
| Recency at 50/50 | Exponential, 7-day half-life | 83.44% |
| Flat split + recency | 55% IRL + Exponential, 7-day half-life | 83.77% |
| Dynamic IRL + recency | 80% start / -2pp/day / 25% floor + Exponential, 3-day half-life | **84.34%** |
| Flat 50/50 baseline | Equal/current Online | 83.40% |
| 100% IRL baseline | — | 83.08% |
| 100% Online baseline | Equal/current Online | 77.06% |

**Interpretation boundary:** full-period winners are in-sample. The chronological holdout is more informative, but has only five independent test cohorts.
