# IRL performance → next IRL field — Phase 2

## Research question

After accounting for how popular an archetype already was, does overperformance at one IRL major predict increased Day-1 representation at the next adjacent same-format IRL cohort?

## Evidence and validation

- **36** eligible adjacent same-format cohort pairs across **10** formats, preserving the prior IRL-regression cohort/capture rules.
- Fixed chronology: first **25** pairs train, final **11** pairs test.
- Expanding walk-forward: each target after the first **15** pairs is fitted only on earlier pairs.
- No Online evidence and no target-tournament performance features are used.

## Primary specification (declared before this target analysis)

Day-2 representation lift relative to Day-1 share, +0.5 smoothed, log2 transformed, bounded to [-2,+2], and activated only for archetypes with >=1% prior cohort share. Smaller archetypes remain in the field at their persistence shares rather than being dropped.

The forecasting adjustment is a single composition-preserving tilt around the previous IRL field. Positive beta means prior overperformance increases forecast share; negative beta means reversal. Shares are clipped at zero if needed and renormalised.

## Descriptive performance coefficient, controlling previous share

Within-pair regression coefficient on prior share: **-0.114**. Coefficient on bounded Day-2 performance: **0.593 percentage points of next-share movement per +1 log2-lift unit**, with format-cluster bootstrap 95% CI **[0.386, 0.774]**. This is descriptive; chronological forecasting below is the decision test.

## Forecast validation

| Model / sensitivity | Full-sample fit | Fixed holdout | vs persistence | Walk-forward | vs persistence | Pairs in holdout / WF |
|---|---:|---:|---:|---:|---:|---:|
| **Day-2 lift, bounded [-2,+2], prior share >=1%** | 84.29% | 85.25% | 0.116pp | 85.08% | 0.296pp | 11 / 21 |
| Day-2 lift, bounded [-2,+2], prior share >=0.5% | 84.30% | 85.21% | 0.073pp | 85.09% | 0.298pp | 11 / 21 |
| Day-2 lift, bounded [-2,+2], prior share >=2% | 84.27% | 85.29% | 0.150pp | 85.06% | 0.275pp | 11 / 21 |
| Day-2 lift, unbounded, prior share >=1% | 84.26% | 85.27% | 0.133pp | 85.06% | 0.271pp | 11 / 21 |
| Event-centred Day-1 points rate, prior share >=1% | 84.21% | 85.16% | 0.025pp | 84.94% | 0.149pp | 11 / 21 |
| Top-32 lift, bounded [-2,+2], prior share >=1% | 84.55% | 85.31% | 0.174pp | 85.18% | 0.389pp | 11 / 21 |
| Tournament-winner visibility indicator | 84.10% | 85.34% | 0.200pp | 85.05% | 0.264pp | 11 / 21 |

## Primary chronological result

Primary fixed holdout: performance-adjusted **85.25%** vs matched persistence **85.14%** = **0.116pp** across **11** independent target cohorts.
Primary expanding walk-forward: performance-adjusted **85.08%** vs persistence **84.79%** = **0.296pp** across **21** targets.

The full-sample fitted beta is **0.1730**; fixed-training beta is **0.1849**; mean walk-forward fitted beta is **0.1795**. A stable positive sign would be consistent with adoption after overperformance; sign instability is evidence against a robust effect.

## Recent-year descriptive sensitivity

Using only targets from 2025-06-12 onward, the primary model fits **84.92%** vs persistence **84.54%** (0.380pp) across **18** pairs. This is an in-sample era sensitivity, not a new holdout claim.

## Interpretation boundary

**Verified:** the table above records both fitted and chronological performance against matched persistence. The primary specification was fixed from Phase 1 before this script inspected next-IRL outcomes.

**Inferred:** whether IRL overperformance is a useful behavioural adoption signal depends on the sign, size and chronological stability shown above, not on the in-sample coefficient alone.

**Limitation:** 36 independent adjacent cohort pairs remain a small forecasting sample. Archetype rows within a cohort are compositional and correlated; the descriptive coefficient therefore uses within-pair demeaning and a format-cluster bootstrap, while the forecasting decision is made at cohort level.

## Next experiment gate

Only if Phase 2 shows a credible chronological performance effect should the exact performance transform be elaborated. Regardless of sign, the next programme question can separately quantify Online movement and then test mediation: prior IRL performance -> subsequent Online adoption -> next IRL share. The combined model must compare persistence, persistence+performance, persistence+Online, and persistence+Online+performance on matched chronological targets.
