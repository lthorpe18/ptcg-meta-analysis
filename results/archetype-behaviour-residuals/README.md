# Archetype behaviour residual analysis

## Question

After freezing the concentration-corrected IRL+Online forecast, does the same archetype tend to be systematically over/under-predicted, and is that stable enough to improve later forecasts?

## Frozen baseline

Fixed PR #13 rule: 80% IRL start, -1pp/day, 55% floor, 75% previous-IRL top-10 concentration correction. Sample: **34 tournaments / 25 cohorts**. Cohort-weighted accuracy **84.28%**.

Residual = actual next-IRL share minus forecast share. Positive residual means the model underpredicted the archetype.

## Does archetype identity repeat?

Active deck-cohort observations: **677** across **104** exact keys. In-sample identity R²: **0.127** (descriptive only).

Using only earlier observations for an archetype (minimum 2), prior mean residual vs its next residual: **r=0.016** across **484** observations; same-sign rate **48.6%**.

Predicting the next residual as the archetype's prior mean gives MAE **1.07pp** versus **0.94pp** for assuming no archetype-specific residual.

## Partially pooled forecasting check

Primary fixed shrinkage k=5: historical mean residual for each exact key is shrunk by n/(n+k), then added to the next forecast and the whole field is renormalised. Only earlier cohorts contribute.

Expanding replay after 10 prior cohorts: **84.62% baseline -> 83.24% adjusted (-1.380pp)**; improved **0/15** cohorts, worse **15/15**.

Shrinkage sensitivity: k=2: -2.099pp; k=5: -1.380pp; k=10: -0.898pp; k=20: -0.502pp.

## Behaviour dispersion among repeated archetypes

Repeated exact keys with >= 5 active cohorts: **53**. Median absolute systematic bias **0.21pp**; median residual volatility **1.04pp** (IQR 0.53–1.40).

The descriptive per-archetype Online-delta/residual slope distribution is reported in JSON/CSV to diagnose differing responsiveness, but is not used as a forecast parameter in this bounded experiment.

## Most systematic repeated residuals (descriptive)

| Archetype | Cohorts | Mean residual | Residual SD | Mean forecast share |
|---|---:|---:|---:|---:|
| Poison Terapagos | 6 | +1.90pp | 1.16pp | 3.04% |
| Gholdengo Lunatone | 6 | +1.42pp | 3.12pp | 11.31% |
| Miraidon | 9 | +1.14pp | 3.00pp | 5.37% |
| Klawf Terapagos | 6 | -1.11pp | 0.40pp | 1.11% |
| Gholdengo Joltik Box | 5 | +0.82pp | 2.10pp | 2.56% |
| Lugia Archeops | 9 | +0.73pp | 2.04pp | 6.80% |
| Dragapult | 17 | +0.71pp | 2.22pp | 6.19% |
| Charizard Pidgeot | 22 | -0.63pp | 1.50pp | 5.63% |
| Dragapult Dusknoir | 25 | -0.60pp | 2.02pp | 10.18% |
| Palkia Dusknoir | 7 | -0.60pp | 0.59pp | 3.26% |

## Interpretation boundary

**Verified** results above describe exact-key historical repetition and the chronological partial-pooling replay.

**Inferred** deck identity is useful only if the chronological residual relationship and/or adjusted Field Accuracy is meaningfully positive; individual deck rows remain descriptive because the sample per deck is small.

**Unknown** whether any apparent deck-specific behaviour is a persistent archetype trait versus a temporary format/list/player-base effect, and whether it will improve a genuinely future event.
