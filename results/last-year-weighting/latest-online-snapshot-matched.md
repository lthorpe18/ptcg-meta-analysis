# Latest Online snapshot — matched-subset sensitivity

Incomplete size-threshold scenarios are compared against broad post-major Online evidence on exactly the same targets.

## Matched full-period comparison

| Snapshot | Events/cohorts | Flat delta vs broad | Dynamic delta vs broad | Snapshot dynamic accuracy | Broad dynamic accuracy |
|---|---:|---:|---:|---:|---:|
| Latest 5 Online >= 200 players | 4/3 | +0.05pp | +0.28pp | 83.72% | 83.44% |
| Latest 5 Online >= 100 players | 14/9 | -0.02pp | -0.08pp | 84.63% | 84.71% |
| Latest 4 Online >= 100 players | 15/10 | -0.15pp | -0.12pp | 84.87% | 85.00% |
| Latest 5 Online >= 150 players | 9/6 | -0.21pp | -0.13pp | 83.94% | 84.07% |
| Latest 5 Online >= 50 players | 16/11 | -0.21pp | -0.15pp | 84.62% | 84.78% |
| Latest 3 Online >= 100 players | 15/10 | -0.32pp | -0.25pp | 84.74% | 85.00% |
| Latest 4 Online >= 50 players | 16/11 | -0.37pp | -0.36pp | 84.42% | 84.78% |
| Latest 4 Online >= 150 players | 11/7 | -0.45pp | -0.41pp | 83.91% | 84.32% |
| Latest 3 Online >= 150 players | 11/7 | -0.51pp | -0.43pp | 83.89% | 84.32% |
| Latest 3 Online >= 50 players | 16/11 | -0.61pp | -0.48pp | 84.29% | 84.78% |
| Latest 4 Online >= 200 players | 7/5 | -0.72pp | -0.54pp | 83.70% | 84.25% |
| Latest 2 Online >= 50 players | 16/11 | -0.59pp | -0.56pp | 84.21% | 84.78% |
| Latest 2 Online >= 100 players | 16/11 | -0.67pp | -0.59pp | 84.19% | 84.78% |
| Latest 3 Online >= 200 players | 9/6 | -0.73pp | -0.60pp | 83.47% | 84.07% |
| Latest 2 Online >= 150 players | 14/9 | -0.67pp | -0.63pp | 84.31% | 84.94% |
| Latest 2 Online >= 200 players | 9/6 | -0.75pp | -0.74pp | 83.34% | 84.07% |
| Latest 1 Online >= 200 players | 12/8 | -1.10pp | -1.08pp | 83.39% | 84.47% |
| Latest 1 Online >= 150 players | 15/10 | -1.12pp | -1.08pp | 83.91% | 85.00% |
| Latest 1 Online >= 50 players | 16/11 | -1.24pp | -1.17pp | 83.60% | 84.78% |
| Latest 1 Online >= 100 players | 16/11 | -1.33pp | -1.25pp | 83.53% | 84.78% |

## Chronological sensitivities with complete final-five coverage

| Snapshot | Training cohorts | Flat holdout delta | Dynamic holdout delta | Snapshot dynamic holdout | Broad dynamic holdout |
|---|---:|---:|---:|---:|---:|
| Latest 5 Online >= 50 players | 6 | +0.15pp | +0.03pp | 84.33% | 84.30% |
| Latest 4 Online >= 50 players | 6 | -0.08pp | -0.02pp | 84.28% | 84.30% |
| Latest 2 Online >= 50 players | 6 | +0.12pp | -0.13pp | 84.16% | 84.30% |
| Latest 2 Online >= 100 players | 6 | -0.50pp | -0.31pp | 83.98% | 84.30% |
| Latest 3 Online >= 50 players | 6 | -0.28pp | -0.38pp | 83.91% | 84.30% |
| Latest 1 Online >= 50 players | 6 | -0.38pp | -0.54pp | 83.76% | 84.30% |
| Latest 1 Online >= 100 players | 6 | -0.56pp | -0.70pp | 83.59% | 84.30% |

**Interpretation boundary:** matched full-period results remain in-sample. Holdout rows are stronger evidence but some thresholds have fewer training cohorts; do not promote a sparse threshold from a tiny subset.
