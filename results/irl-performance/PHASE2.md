# IRL performance → next IRL share — Phase 2

## Research question

After accounting for how popular an archetype already was, does overperformance at one IRL major predict increased representation at the next adjacent same-format IRL major cohort?

## Evidence and design

- Eligible adjacent same-format cohort pairs: **36** across **10** formats.
- Same >=95% Day-1 capture rule and no-skipping adjacency used by the prior IRL-to-IRL analysis.
- Simultaneous majors stay aggregated as cohorts.
- Primary performance signal: bounded [-2,+2] smoothed log2 Day-2 representation lift; no minimum-share exclusion.
- Forecast is composition-preserving before clipping: previous field plus a fitted performance tilt proportional to previous share.
- Fixed chronological 70/30 holdout and expanding walk-forward after 15 earlier pairs.

## Controlled association

Pair-fixed-effect regression of next-share change on previous share + prior performance gives a performance coefficient of **0.250 percentage points of next-field share per +1 unit of bounded log2 Day-2 lift**.
Format-cluster bootstrap 95% interval: **[0.183, 0.316] pp**.

This is an association estimate, not by itself proof of future predictive improvement.

## Primary forecast comparison

- Full-sample in-sample: persistence **83.89%** vs performance-adjusted **84.35%** (0.462pp).
- Fixed holdout: persistence **85.14%** vs performance-adjusted **85.27%** (0.135pp), 11 test pairs.
- Expanding walk-forward: persistence **84.79%** vs performance-adjusted **85.12%** (0.334pp), 21 chronological targets.

## Sensitivity variants

| Variant | Holdout Δ vs persistence | Walk-forward Δ |
|---|---:|---:|
| day2_bounded_all | 0.135pp | 0.334pp |
| day2_bounded_0_5 | 0.069pp | 0.296pp |
| day2_bounded_1 | 0.113pp | 0.299pp |
| day2_bounded_2 | 0.152pp | 0.300pp |
| day2_raw_1 | 0.130pp | 0.271pp |
| points_1 | 0.042pp | 0.173pp |
| top32_1 | 0.208pp | 0.332pp |
| winner_1 | 0.198pp | 0.257pp |

## Interpretation boundary

**Verified:** values above are reproducible outputs from the frozen adjacent-cohort sample and chronological splits.

**Inferred:** only if the chronological comparisons remain positive and reasonably stable should prior IRL performance advance as an independent forecasting feature.

**Not tested here:** whether subsequent Online movement mediates the performance effect. That is the next programme stage after deciding whether the standalone performance signal is worth carrying forward.
