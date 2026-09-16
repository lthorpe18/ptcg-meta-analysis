# Forecast user-relevance diagnostic — handoff

Date: 2026-09-16
Repository: `lthorpe18/ptcg-meta-analysis`
Branch: `research/forecast-user-relevance`
Parent: PR #15 / `research/combined-online-performance`
Workflow run: `35083247712`

## Research question

> How accurate is the current combined chronological field forecast for the individual decks users actually care about, rather than only in aggregate Field Accuracy?

This is a diagnostic/evaluation analysis only. It does not tune or change the model.

## Model and validation sample

Uses PR #15 combined model exactly as produced in its primary expanding chronological replay:
- frozen concentration-corrected IRL+Online baseline;
- previous-major Day-2 performance term;
- beta learned only from earlier cohorts;
- target tested only after at least 10 prior matched cohorts.

Evaluation sample:
- 18 target events;
- 13 independent chronological cohorts;
- 1,820 archetype-event rows.

Predicted-share bands are defined from the **forecast**, not the eventual result, so the band is known before the tournament.

## Verified — error by predicted share

Cohort-weighted results:

| Predicted share | MAE | Bias | Within ±1pp | Within ±2pp | P80 abs error | P90 abs error |
|---|---:|---:|---:|---:|---:|---:|
| 10%+ | 2.39pp | +0.21pp | 25% | 52% | 3.17pp | 4.98pp |
| 5–10% | 1.38pp | -0.05pp | 50% | 72% | 2.11pp | 2.80pp |
| 2–5% | 1.17pp | +0.09pp | 55% | 84% | 1.81pp | 2.36pp |
| 1–2% | 0.63pp | -0.26pp | 88% | 96% | 0.85pp | 1.15pp |
| <1% | 0.11pp | ~0pp | 99% | ~100% | 0.15pp | 0.26pp |

Bias = predicted minus actual. P80/P90 are descriptive empirical historical error percentiles, not formal confidence intervals.

The largest decks are hardest to estimate precisely in absolute percentage points. A forecast around 12–15% should not be read as precise to ±1pp; historically the 80th-percentile absolute error for 10%+ forecasts is ~3.2pp and the 90th is ~5.0pp.

## Verified — top-deck identification

Predicted top 5:
- contains **87.7%** of actual top-5 identities on average (~4.4/5);
- captures **48.7%** of actual field share;
- actual top 5 itself accounts for **49.9%** on average;
- predicted top-5 total mass is 48.7%, essentially unbiased as a group.

Predicted top 10:
- contains **88.6%** of actual top-10 identities (~8.9/10);
- captures **69.1%** of actual field share;
- actual top 10 itself accounts for **71.8%**;
- predicted top-10 mass averages 71.0%, but the same predicted keys actually total 69.1%, a +1.89pp group-mass bias.

## Verified — threshold reliability

For the practical question “which decks are at least X% of the field?”:

| Threshold | Precision | Recall | Avg predicted | Avg actual | Avg missed |
|---|---:|---:|---:|---:|---:|
| >=1% | 90% | 90% | 19.3 | 19.3 | 2.0 |
| >=2% | 90% | 87% | 12.2 | 12.7 | 1.7 |
| >=5% | 85% | 86% | 6.5 | 6.4 | 1.0 |

At >=1%, the forecast typically identifies about 17–18 of the ~19 decks that actually clear 1%, while also including about two that do not. At >=5%, it typically misses about one meaningful deck and includes about one that finishes below 5%.

## Interpretation

**Verified:** the model is substantially better at identifying *which decks matter* than at pinning the exact share of the biggest decks. Top-5/top-10 identity overlap is ~88%, and >=1% threshold precision/recall is ~90%.

**Verified:** exact share estimates for large archetypes carry material uncertainty. For 10%+ predictions, MAE is 2.39pp and only 25% land within ±1pp.

**Inferred:** user-facing forecast output should emphasize ranked field structure, movers and empirical uncertainty rather than presenting each percentage as equally precise. A large-deck forecast such as 15% should visually communicate a wider plausible range than a 1.5% forecast.

**Inferred:** the aggregate ~85% Field Accuracy is not misleading, but it answers a different question: overall distributional overlap. For practical preparation, top-N identity/coverage and share-band error are more interpretable companion metrics.

**Unknown:** whether these empirical error ranges remain calibrated on genuinely future tournaments. The diagnostic uses chronological replay but the underlying model family was developed on overlapping history.

## Exact next action

Owner decision. Do not merge automatically.

If adopted as the research-output approach, the next bounded task should be presentation design: show forecast share plus empirically derived uncertainty by predicted-share band, and summarize expected top-5/top-10 coverage. Do not tune the forecast against these diagnostics unless a separate model-improvement experiment is explicitly authorised.
