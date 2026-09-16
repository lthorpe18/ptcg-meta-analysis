# Forecast accuracy for the decks users care about

Diagnostic only. Uses PR #15 combined forecasts exactly as produced in the primary expanding chronological replay; **no model tuning**.

Sample: **18 events / 13 independent cohorts**.

## Error by predicted field share

| Predicted share | MAE | Bias | Within ±1pp | Within ±2pp | P80 abs error | P90 abs error |
|---|---:|---:|---:|---:|---:|---:|
| 10%+ | 2.39pp | +0.21pp | 25% | 52% | 3.17pp | 4.98pp |
| 5-10% | 1.38pp | -0.05pp | 50% | 72% | 2.11pp | 2.80pp |
| 2-5% | 1.17pp | +0.09pp | 55% | 84% | 1.81pp | 2.36pp |
| 1-2% | 0.63pp | -0.26pp | 88% | 96% | 0.85pp | 1.15pp |
| <1% | 0.11pp | -0.00pp | 99% | 100% | 0.15pp | 0.26pp |

Bias = predicted minus actual. Percentile errors are descriptive, not formal confidence intervals.

## Do we identify the decks at the top?

Predicted top 5 contains **87.7%** of the actual top-5 identities on average and captures **48.7%** of the actual field.
Predicted top 10 contains **88.6%** of the actual top-10 identities and captures **69.1%** of the actual field.
For comparison, the actual top 10 itself accounts for **71.8%** of the field on average.

## Threshold reliability

| Forecast threshold | Precision | Recall | Avg predicted decks | Avg actual decks | Avg missed |
|---|---:|---:|---:|---:|---:|
| ≥1% | 90% | 90% | 19.3 | 19.3 | 2.0 |
| ≥2% | 90% | 87% | 12.2 | 12.7 | 1.7 |
| ≥5% | 85% | 86% | 6.5 | 6.4 | 1.0 |

Precision: of decks forecast above the threshold, how many actually finish above it. Recall: of decks that actually finish above it, how many the forecast put above it.

## Practical use

The predicted-share bands can support empirical uncertainty language in the research output. Do not present P80/P90 as guaranteed statistical confidence intervals; they are historical error ranges from the replay sample.
