# IRL-to-IRL regression — leverage sensitivity

The main sample has only three pairs with gaps above 14 days. These checks test whether the negative time-gap slope survives removing sparse long-gap leverage.

| Sensitivity | Pairs | Gap range | Overall slope/day | Within-format slope/day |
|---|---:|---:|---:|---:|
| Full eligible sample | 36 | 5-47 | -0.169 | -0.200 |
| Exclude single longest-gap pair | 35 | 5-34 | -0.105 | -0.110 |
| Gaps <=14 days | 33 | 5-13 | -0.156 | -0.242 |
| Latest 365 days | 18 | 5-47 | -0.310 | -0.369 |
| Latest 365 days, gaps <=14 | 16 | 5-13 | -0.503 | -0.675 |

## Bootstrap details

- **Exclude single longest-gap pair**: overall 95% format-cluster CI [-0.443, +0.089] pp/day; within-format CI [-0.529, +0.065] pp/day.
- **Gaps <=14 days**: overall 95% format-cluster CI [-0.613, +0.139] pp/day; within-format CI [-0.787, +0.076] pp/day.
- **Latest 365 days**: overall 95% format-cluster CI [-0.641, -0.236] pp/day; within-format CI [-0.866, -0.311] pp/day.
- **Latest 365 days, gaps <=14**: overall 95% format-cluster CI [-1.489, -0.117] pp/day; within-format CI [-1.378, -0.301] pp/day.

A slope that changes materially after excluding the longest gaps should be treated as leverage-sensitive rather than a stable decay law.
