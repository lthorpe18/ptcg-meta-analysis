# Combined corrected Online + previous-major performance

## Primary expanding replay
Matched sample: **30 events / 23 cohorts**; **13** later cohorts tested after 10 prior cohorts.
Field Accuracy: **84.39% -> 84.97%** (+0.577pp).
Improved **9/13** cohorts; worsened **4/13**.

## Decks that matter (predicted OR actual >=1%)
MAE: **1.10pp -> 1.09pp** (-0.005pp; lower is better).
Within 1pp of actual: **64.5% -> 63.3%**.
Actual top-10 MAE: **1.64pp -> 1.57pp**.

## Robustness
Replay after 15 prior cohorts: **84.83% -> 85.44%** (+0.609pp).
Frozen recent split: **84.48% -> 84.98%** (+0.495pp).

The >=1% and top-10 views are evaluation metrics only and were not used to fit beta.
