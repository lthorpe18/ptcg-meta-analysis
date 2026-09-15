# IRL-to-IRL same-format regression

Evidence: **36 adjacent same-format cohort pairs across 10 formats**; every event on both sides of a retained pair has >=95% captured Day-1 field coverage.
Online evidence is **not used**.

## 1. Persistence baseline

Using the previous same-format IRL cohort unchanged predicts the next cohort at **83.89% mean Field Accuracy** (median 84.57%).

## 2. Does IRL-to-IRL similarity decay with time?

Median gap after the prior IRL weekend: **6.0 days** (range 5-47).
Overall regression: **-0.169 accuracy points/day** (-1.18pp per 7 days), R²=0.111.
95% format-cluster bootstrap CI for the overall slope: **[-0.378, +0.063] pp/day**.
Within-format (format fixed-effect) slope: **-0.200 pp/day** (-1.40pp per 7 days).
95% format-cluster bootstrap CI: **[-0.446, +0.045] pp/day**.

| Gap after prior weekend | Pairs | Mean persistence accuracy |
|---|---:|---:|
| 0-7 days | 25 | 84.53% |
| 8-14 days | 8 | 83.58% |
| 22-35 days | 2 | 81.37% |
| 36+ days | 1 | 75.32% |

## 3. Archetype-share retention

Pair-fixed-effect regression gives a prior-share slope of **0.954** at the median 6.0-day gap, with gap interaction **-0.0020 per day**.
Bootstrap 95% CI for median-gap slope: **[0.932, 0.989]**; gap interaction CI **[-0.0110, +0.0020]**.

| Gap | Implied target-vs-prior share slope |
|---:|---:|
| 0 days | 0.965 |
| 7 days | 0.952 |
| 14 days | 0.938 |
| 21 days | 0.924 |
| 28 days | 0.911 |
| 35 days | 0.897 |

## 4. Fixed chronological holdout

Fit on first **25 pairs**; evaluate on final **11 pairs** (2026-02-13 onward).

| Model | Test pairs | Mean Field Accuracy |
|---|---:|---:|
| Persistence: last IRL = next IRL | 11 | **85.14%** |
| Earlier same-format IRL mean | 11 | 83.63% |
| Regression shrinkage to format mean | 11 | 85.23% |
| Gap-aware regression shrinkage | 11 | 85.23% |
| Gap + format-age regression | 11 | 85.19% |
| Two-weekend momentum | 7 | 86.48% |
| Shrinkage + momentum | 7 | 86.46% |

Momentum models have fewer test pairs because they require two clean adjacent prior cohorts; compare them with the persistence-on-momentum-subset result in summary.json, not the full persistence row.

## 5. Expanding walk-forward

After at least 15 earlier training pairs, refit using only past pairs before each target.

| Model | Pairs | Mean Field Accuracy |
|---|---:|---:|
| Persistence | 21 | 84.79% |
| Earlier format mean | 21 | 82.05% |
| Regression shrinkage | 21 | 84.77% |
| Gap-aware shrinkage | 21 | 84.75% |
| Gap + format-age shrinkage | 21 | 84.72% |
| Two-weekend momentum | 14 | 86.85% |
| Shrinkage + momentum | 14 | 86.76% |

## Interpretation boundary

Full-sample coefficients and model rankings are in-sample. The fixed chronological holdout and expanding walk-forward are the stronger checks.
IRL-to-IRL retention/decay is **not** an IRL-vs-Online blend weight. A negative time interaction can support the idea that old IRL evidence becomes stale, but it does not directly tell us how much Online weight to assign.
