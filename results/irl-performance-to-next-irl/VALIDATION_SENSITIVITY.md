# Phase 2 primary validation — leverage and consistency sensitivity

This sensitivity does not refit or choose a model. It examines the already-declared primary Day-2 performance forecast to determine whether its average chronological gain is broadly distributed or driven by a small number of targets.

## Fixed chronological holdout

- Mean improvement: **0.116pp**; median target improvement: **0.033pp**.
- Positive targets: **6/11**; negative targets: **5/11**.
- Best target: **C053->C054** (2.672pp); worst: **C043->C044** (-1.266pp).
- Mean after removing the best target: **-0.139pp**; after removing the worst: **0.254pp**.
- Leave-one-target-out mean range: **[-0.139, 0.254]pp**.
- Format-cluster bootstrap 95% interval for mean improvement: **[-0.266, 1.161]pp** across **4** observed formats.

Per-format mean improvements:

| Format | Targets | Mean improvement | Wins / losses |
|---|---:|---:|---:|
| SVI-ASC | 4 | -0.364pp | 2 / 2 |
| SVI-PFL | 2 | -0.025pp | 1 / 1 |
| TEF-CRI | 1 | 2.672pp | 1 / 0 |
| TEF-POR | 4 | 0.028pp | 2 / 2 |

## Expanding walk-forward

- Mean improvement: **0.296pp**; median target improvement: **0.386pp**.
- Positive targets: **15/21**; negative targets: **6/21**.
- Best target: **C053->C054** (2.378pp); worst: **C043->C044** (-1.270pp).
- Mean after removing the best target: **0.192pp**; after removing the worst: **0.374pp**.
- Leave-one-target-out mean range: **[0.192, 0.374]pp**.
- Format-cluster bootstrap 95% interval for mean improvement: **[-0.028, 0.757]pp** across **7** observed formats.

Per-format mean improvements:

| Format | Targets | Mean improvement | Wins / losses |
|---|---:|---:|---:|
| SVI-ASC | 4 | -0.311pp | 2 / 2 |
| SVI-BLK/WHT | 2 | 0.556pp | 2 / 0 |
| SVI-JTG | 3 | -0.004pp | 2 / 1 |
| SVI-MEG | 4 | 0.776pp | 4 / 0 |
| SVI-PFL | 3 | 0.176pp | 2 / 1 |
| TEF-CRI | 1 | 2.378pp | 1 / 0 |
| TEF-POR | 4 | 0.088pp | 2 / 2 |

## Interpretation

**Verified:** the fixed-holdout mean is sensitive to its strongest target if `mean_without_best_target_pp` changes sign. The expanding walk-forward result is more convincing only if its gain remains positive without the best target and is not confined to one format.

**Limitation:** the format-cluster intervals are based on only a handful of formats in each validation window; crossing zero should be treated as unresolved uncertainty rather than proof of no effect.

This sensitivity is diagnostic. It does not promote a sensitivity model over the predeclared primary specification.
