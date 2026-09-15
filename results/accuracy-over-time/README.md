# Prediction accuracy over time

Generated from `data/processed/model-results/events.csv`.

## Question

Does field-share prediction accuracy change systematically over chronological time?

## Evidence and method

- Historical target window: **2024-09-13 to 2026-08-28**.
- Primary targets use the existing **>=95% IRL field-capture** threshold; targets 0004, 0008 and 0051 are excluded consistently with the existing scorer.
- Unit of analysis: **tournament cohort mean**, so correlated same-weekend majors do not receive extra weight.
- Metric: existing **Field Accuracy**.
- Primary trend statistic: linear change in Field Accuracy percentage points per calendar year.
- Two-sided permutation test: **20,000** shuffled cohort accuracies, deterministic seed `20260915`.
- No model is retuned here. This is a diagnostic of existing prediction outputs.

## Results

| Series | Cohorts | Slope (pp/year) | Permutation p | Early half | Late half |
|---|---:|---:|---:|---:|---:|
| Online-only, all primary windows | 53 | 1.98 | 0.093 | 70.48% | 73.89% |
| Online-only, settled primary windows | 40 | 3.84 | 0.002 | 69.42% | 74.55% |
| Online-only, transition primary windows | 13 | -2.28 | 0.396 | 74.03% | 71.98% |
| IRL-only, settled primary windows | 40 | 0.94 | 0.505 | 82.44% | 83.78% |
| 50/50, complete-case settled | 25 | 0.75 | 0.609 | 81.84% | 84.37% |
| Current v2.1, complete-case settled | 25 | 1.06 | 0.502 | 81.65% | 84.83% |

## Interpretation

**Verified from this diagnostic:** the clearest chronological signal is in **Online-only accuracy on settled formats**. Its cohort-level accuracy rises by about **3.84 percentage points per year**, with a small permutation p-value (0.002). The descriptive half split is 69.42% versus 74.55%.

The same clear monotonic trend is **not** present in the current blended benchmark: current v2.1 changes by about **1.06 pp/year** with permutation p=0.502. IRL-only and 50/50 likewise do not show a clear linear trend.

**Important limitation:** this does not establish that Online evidence itself became intrinsically more predictive. Calendar time is confounded with format/rotation, tournament ecosystem, event mix, field concentration and retrospective data conditions. Transition windows also behave differently from settled windows. The result supports a follow-up question about *why settled Online-only accuracy improved*, not a model change.

## What this supports

- There is evidence worth investigating that **settled-format Online-only field prediction became more accurate over this historical period**.
- There is not yet evidence of a general across-the-board improvement in the blended/IRL prediction methods.
- No production-model change is supported by this analysis alone.

## Next analytical question

Test whether the settled Online-only trend remains after accounting for plausible confounders, starting with **format/rotation era and target-field concentration**. That follow-up requires an explicit owner decision before implementation.
