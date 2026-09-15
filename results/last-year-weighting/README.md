# Last-year IRL/Online weighting experiment

Evidence window: **2025-08-28 to 2026-08-28**.
Complete-case settled sample: **16 tournaments across 11 independent cohorts**.

## Question

Which interpretable IRL/Online decay rule is most accurate on the latest 365 days of archived play?

## In-sample recent-period fit

Best grid rule: **85% IRL start, 2.0pp/day decay, 30% IRL floor**.
Cohort-weighted accuracy: **84.77%**.

| Comparator | Cohort accuracy |
|---|---:|
| Online-only | 76.37% |
| IRL-only | 82.20% |
| 50/50 | 84.11% |
| Current v2.1 (70%, -2pp/day, 30% floor) | 84.46% |
| Full-history grid winner (80%, -1pp/day, 55% floor) | 84.58% |
| **Recent in-sample winner** | **84.77%** |

This recent winner is **in-sample** and is not by itself evidence that the rule will predict future events better.

## Fixed chronological holdout

Tune on first 6 recent cohorts; test untouched on final 5 cohorts.
Training selected: **70% start, 1.5pp/day, 30% floor**.
Holdout selected-rule accuracy: **83.99%**.
Holdout current v2.1: **83.77%**.
Holdout 50/50: **83.40%**.
Holdout IRL-only: **83.08%**.
Holdout full-history grid winner: **84.36%**.

Only five independent holdout cohorts are available, so this validation is directional rather than decisive.

## Recent expanding walk-forward (supplementary)

After at least 5 recent cohorts, tested 6 later cohorts.
Retuned rule: **84.46%**; current v2.1: **84.46%**; 50/50: **84.10%**; IRL-only: **83.04%**.

## Interpretation boundary

This experiment tests weighting within the existing frozen evidence windows. It does not test the causal hypothesis that increased player numbers or competitiveness caused the recent Online-to-IRL relationship to strengthen, and it does not authorise a production formula change.
