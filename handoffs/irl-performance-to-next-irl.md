# IRL performance → next IRL field — Phase 2 handoff

Date: 2026-09-15
Repository: `lthorpe18/ptcg-meta-analysis`
Parent research: `research/irl-performance-signal` / PR #10
Working branch: `research/irl-performance-to-next-irl`
Successful workflows: `34978138334`, `34978334610`

## Research question

> After controlling for previous IRL Day-1 share, does relative performance at the previous major predict archetype share movement at the next adjacent same-format IRL cohort?

Phase 2 uses IRL evidence only. It does not use Online evidence and does not modify the production PTCG Tools application.

## Evidence / sample

The experiment reuses the exact adjacent same-format cohort rules from the prior IRL-to-IRL work:

- 36 eligible adjacent cohort pairs across 10 formats;
- every event in both source and target cohorts >=95% captured Day-1 field coverage;
- simultaneous majors remain a single cohort and never predict one another;
- fixed chronological split = first 25 pairs train, final 11 test;
- expanding walk-forward = 21 later targets after at least 15 prior training pairs.

## Primary performance specification

Declared from the Phase-1 stability audit before this script inspected next-IRL outcomes:

- Day-2 relative representation: `log2((observed Day-2 + 0.5)/(expected Day-2 from Day-1 share + 0.5))`;
- bounded to `[-2,+2]`;
- active only for archetypes with >=1% previous cohort share;
- smaller archetypes remain at persistence rather than being removed.

Forecast model is deliberately one-parameter and composition preserving:

`forecast = previous IRL + beta × previous share × (performance - active-share-weighted mean performance)`

The performance adjustment sums to zero over active archetypes. Negative predictions, if any, are clipped and the distribution is renormalised to 100%.

## Verified descriptive relationship

Within-pair regression of next-share movement on previous share and performance:

- previous-share coefficient: **-0.114**;
- bounded Day-2 performance coefficient: **+0.593 percentage points of next-share movement per +1 log2-lift unit**;
- format-cluster bootstrap 95% CI for performance: **[+0.386, +0.774]**;
- 703 archetype rows, 36 pairs, 10 formats.

Recent-year sensitivity (18 pairs / 6 formats):

- performance coefficient **+0.478pp**;
- format-cluster bootstrap CI **[+0.234, +0.727]**.

**Verified:** after controlling for prior share in this descriptive regression, better prior-major performance is positively associated with increased representation at the next major. This is not sufficient by itself to claim forecasting improvement.

## Verified chronological forecasting

Primary specification:

- Full-sample fit: **84.29%** vs persistence **83.89%** = +0.403pp in-sample.
- Fixed 11-cohort holdout: **85.25%** vs **85.14%** = **+0.116pp**.
- Expanding walk-forward, 21 targets: **85.08%** vs **84.79%** = **+0.296pp**.
- Full-sample beta **0.1730**; fixed-training beta **0.1849**; mean walk-forward beta **0.1795**.
- Recent-year descriptive fit: **84.92%** vs **84.54%** = +0.380pp across 18 pairs.

Threshold/transform sensitivity is directionally similar rather than highly tuned:

- bounded Day-2 >=0.5%: walk-forward **+0.298pp**;
- bounded Day-2 >=2%: **+0.275pp**;
- unbounded Day-2 >=1%: **+0.271pp**;
- centred Day-1 points rate >=1%: **+0.149pp**;
- bounded Top-32 lift >=1%: **+0.389pp**;
- tournament-winner indicator: **+0.264pp**.

These secondary results are sensitivities, not model-selection evidence.

## Verified leverage / consistency sensitivity

Fixed holdout:

- 6/11 targets improve; median target improvement **+0.033pp**;
- best target +2.672pp, worst -1.266pp;
- removing the best target changes mean improvement from +0.116pp to **-0.139pp**;
- format-cluster bootstrap CI for mean improvement **[-0.266, +1.161]pp** across only 4 holdout formats.

Expanding walk-forward:

- 15/21 targets improve; median target improvement **+0.386pp**;
- best target +2.378pp, worst -1.270pp;
- removing the best target still leaves **+0.192pp** mean improvement;
- every leave-one-target-out mean remains positive: **[+0.192, +0.374]pp**;
- format-cluster bootstrap CI **[-0.028, +0.757]pp** across 7 formats.

Per-format walk-forward mean improvement is positive for SVI-BLK/WHT, SVI-MEG, SVI-PFL, TEF-CRI and TEF-POR; near zero for SVI-JTG; negative for SVI-ASC.

## Interpretation

**Verified:** previous-major overperformance contains information about next-major share movement after controlling for prior popularity. The positive descriptive relationship survives a recent-year sensitivity, and the predeclared one-parameter performance adjustment produces small positive mean gains in both chronological validations.

**Inferred:** this is stronger evidence than the earlier prior-two-IRL momentum signal. It is consistent with a behavioural adoption response to tournament performance.

**However:** the standalone forecasting improvement is modest. The fixed holdout is leverage-sensitive and both format-cluster validation intervals cross zero. The walk-forward result is more broadly distributed and survives removal of its best target, but remains only 21 targets / 7 formats.

Therefore **do not promote performance as a standalone replacement for persistence**. Retain it as a candidate incremental signal for the later Online-mediation and combined-model tests.

## Reproducibility

- `scripts/analyse_irl_performance_to_next_irl.py`
- `scripts/analyse_irl_performance_validation_sensitivity.py`
- `data/processed/irl-performance-to-next-irl/summary.json`
- `data/processed/irl-performance-to-next-irl/primary-validation.csv`
- `data/processed/irl-performance-to-next-irl/validation-sensitivity.json`
- `results/irl-performance-to-next-irl/README.md`
- `results/irl-performance-to-next-irl/VALIDATION_SENSITIVITY.md`

## Exact next bounded experiment — Phase 3

Quantify the clean three-stage relationship:

`previous IRL field -> subsequent Online field -> next IRL field`

For each adjacent same-format IRL pair, construct Online evidence strictly after the source cohort and before the target cutoff, then calculate:

- previous IRL share;
- subsequent Online share;
- Online movement = Online share - previous IRL share;
- next IRL movement = next IRL share - previous IRL share.

Estimate the carry-through of Online movement into the next IRL field, with elapsed-time, Online-evidence-volume and recent-era sensitivities. Keep this separate from prior-IRL performance initially. Use chronological fitting and composition-valid forecasts.

Only after Phase 3 is established should Phase 4 compare on matched targets:

1. previous IRL only;
2. previous IRL + performance;
3. previous IRL + Online movement;
4. previous IRL + Online movement + performance.

That comparison will answer whether Online movement mediates most of the performance effect.

Do not merge without explicit owner authorisation.
