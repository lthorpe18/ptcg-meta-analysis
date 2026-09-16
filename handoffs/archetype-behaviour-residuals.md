# Archetype behaviour residuals — handoff

Date: 16 September 2026
Repository: `lthorpe18/ptcg-meta-analysis`
Base: `research/concentration-corrected-blend` / PR #13
Working branch: `research/archetype-behaviour-residuals`
PR: #14

## Owner question

After establishing the concentration-corrected IRL+Online forecast, investigate whether different deck archetypes behave differently enough that archetype identity should alter the next-IRL field-share forecast.

## Frozen baseline

The experiment freezes the PR #13 fixed rule rather than re-fitting it here:
- 80% starting IRL weight;
- -1 percentage point IRL weight per day;
- 55% IRL floor;
- 75% concentration correction on the previous-IRL top 10;
- same 34 settled tournaments / 25 independent cohorts;
- existing exact archetype keys only; no taxonomy remapping.

Full-sample cohort-weighted accuracy of that frozen rule is **84.28%**. On the later 15 cohorts used for expanding chronological checks, the same fixed rule scores **84.62%**.

## Experiment A — persistent archetype residual bias

Residual = actual next-IRL share minus frozen forecast share. Positive means underprediction.

Active criterion is forecast share >=0.5%, which is known before the target result.

### Verified

- 677 active archetype-cohort observations / 104 exact keys.
- In-sample archetype identity R² = 0.127, but this is descriptive and not predictive evidence.
- For 484 observations where the exact key had at least two earlier observations, correlation between its prior mean residual and next residual = **r=0.016**.
- Same-sign rate = **48.6%**, effectively chance.
- Predicting next residual from prior archetype mean gives MAE **1.07pp**, worse than **0.94pp** from assuming zero archetype-specific residual.
- Fixed partially-pooled bias adjustment, using only earlier cohorts and shrinkage n/(n+5): **84.62% -> 83.24% (-1.38pp)** across 15 later cohorts.
- It worsened **15/15** cohorts.
- Every shrinkage sensitivity was negative: k=2 -2.10pp; k=5 -1.38pp; k=10 -0.90pp; k=20 -0.50pp.

### Interpretation

**Verified:** exact-key additive forecast bias does not persist chronologically in this sample. Individual archetypes can look systematically over/under-predicted in-sample, but carrying that bias forward is harmful.

Do not add per-archetype additive corrections to the point forecast from this evidence.

## Experiment B — archetype-specific response to Online movement

To distinguish a general under/over-reaction to Online evidence from deck-specific behaviour, use corrected Online share minus previous IRL share as the movement feature. For every target, coefficients are fitted only from earlier cohorts.

Compare:
1. frozen concentration-corrected baseline;
2. one global residual-response coefficient for all archetypes;
3. exact-key response coefficients partially pooled toward the global coefficient.

### Verified

Across 15 expanding-replay cohorts:
- baseline: **84.62%**;
- global response: **84.91% (+0.296pp)**;
- archetype-specific partially pooled response, k=5: **84.61% (-0.003pp vs baseline; -0.299pp vs global)**.

Archetype-specific response beat global in 8/15 cohorts but lost on mean accuracy. Shrinkage sensitivity versus global:
- k=2: -0.539pp;
- k=5: -0.299pp;
- k=10: -0.099pp;
- k=20: -0.001pp.

As archetype-specific coefficients are shrunk harder toward the global coefficient, performance converges to the global model. There is no demonstrated gain from retaining the deck-specific coefficient.

### Important modelling interpretation

The global response adjustment is not a new archetype effect. Algebraically, adding a common multiple of `(corrected Online - previous IRL)` to an IRL/Online blend is approximately equivalent to shifting more blend weight from IRL toward corrected Online (apart from the >=0.5% active threshold, clipping and renormalisation). Therefore the +0.296pp global result should be treated as additional evidence about global IRL/Online weighting, not as a new independent signal.

**Verified:** this experiment does not support archetype-specific Online-response coefficients for point prediction.

## Experiment C — archetype volatility / forecast confidence

Rather than changing the point estimate, test whether some exact keys are consistently harder to predict.

Using only earlier residual history and requiring at least three prior observations:
- 407 eligible later observations;
- prior residual SD vs next absolute residual: **r=0.236**;
- below-median prior-volatility archetype observations miss by **0.68pp** on average;
- above-median prior-volatility observations miss by **1.28pp** on average;
- difference = **+0.60pp**.

### Interpretation

**Verified:** historical archetype volatility has modest chronological information about the size of the next forecast error.

**Inferred:** archetype-specific behaviour is more promising as a **confidence / uncertainty layer** than as a point-estimate correction. A forecast could eventually distinguish stable/high-confidence shares from volatile/low-confidence shares without moving the central estimate merely because a deck historically missed in one direction.

**Unknown:** whether a calibrated archetype-specific interval materially improves decision usefulness or maintains correct future coverage. That requires a separate uncertainty-calibration experiment.

## Individual archetype rows

Repeated exact keys show different descriptive biases and volatilities, but those individual estimates are not promoted because additive bias failed chronological validation and exact-key behaviour can change with format/list composition. The CSV is diagnostic only.

## Reproducibility

- `scripts/analyse_archetype_behaviour_residuals.py`
- `scripts/analyse_archetype_responsiveness.py`
- `data/processed/archetype-behaviour-residuals/summary.json`
- `data/processed/archetype-behaviour-residuals/archetype-summary.csv`
- `data/processed/archetype-behaviour-residuals/responsiveness.json`
- `results/archetype-behaviour-residuals/README.md`
- `results/archetype-behaviour-residuals/RESPONSIVENESS.md`

## Exact next action

Owner decision. For point-estimate accuracy, do **not** add archetype-specific bias or Online-response parameters from this experiment. The next accuracy-focused experiment should return to pooled signals, most naturally testing the concentration-corrected Online model jointly with the already-demonstrated previous-major performance signal on matched chronological targets.

If user-facing uncertainty is the priority instead, the next bounded experiment is to calibrate archetype-specific prediction ranges from prior residual volatility and test interval coverage chronologically.

Do not merge without explicit owner authorisation.
