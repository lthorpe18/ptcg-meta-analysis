# Concentration-corrected IRL + Online forecast

## Question

Can we improve next-IRL field forecasts by correcting the structural Online long-tail effect before blending Online evidence with the previous IRL field?

## Primary correction

Take the **previous IRL top 10** as a group. Keep the Online relative movement inside that group and inside the rest of the field, but move the group's total Online share part-way back toward its previous-IRL total. Strength 0% is the raw Online baseline; 100% fully restores the prior top-10 total before blending.

Sample: **34 tournaments / 25 independent settled cohorts**.

## Full-sample fit — descriptive only

Best raw IRL+Online grid: **84.01%** (80% start, -1.0pp/day, 55% floor).
Best concentration-corrected grid: **84.34%** with **75% correction**.
In-sample difference: **+0.33pp**.

### Same historical 80% / -1pp/day / 55% rule, correction only

| Correction strength | Accuracy |
|---:|---:|
| 0% | 84.01% |
| 25% | 84.17% |
| 50% | 84.26% |
| 75% | 84.28% |
| 100% | 84.19% |

## Expanding walk-forward — primary validation

After at least 10 prior cohorts, each later cohort chose parameters using earlier cohorts only.
Raw tuned blend: **83.93%**.
Concentration-corrected tuned blend: **84.31%**.
Difference: **+0.39pp**; corrected improved 11/15 cohorts, worsened 4/15.

## Frozen recent-era split

Fit parameters only before **2025-08-28**, then score the later 11 cohorts.
Raw: **84.11%**; corrected: **84.68%**; difference **+0.57pp**.
Training selected correction strength: **75%**.

## Interpretation boundary

- **Verified:** all scores use the frozen historical windows and the same named-archetype Field Accuracy metric as previous research.
- **Verified:** walk-forward target cohorts do not tune their own parameters.
- **Caution:** the correction idea itself was discovered from the full archive, so this is stronger than an in-sample comparison but not equivalent to a genuinely unseen future tournament.
- No production PTCG Tools formula is changed by this experiment.

