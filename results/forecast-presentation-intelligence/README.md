# Forecast presentation intelligence

This is a **presentation/evaluation analysis**, not another forecast optimisation. It uses the PR #15 chronological combined forecasts unchanged.

## Empirical uncertainty by displayed forecast share

| Forecast share | MAE | Historical P80 abs error | Historical P90 abs error |
|---|---:|---:|---:|
| 10%+ | 2.39pp | 3.17pp | 4.98pp |
| 5-10% | 1.38pp | 2.11pp | 2.80pp |
| 2-5% | 1.17pp | 1.81pp | 2.36pp |
| 1-2% | 0.63pp | 0.85pp | 1.15pp |

These ranges are descriptive historical errors, not guaranteed confidence intervals.

## Which evidence deserves an explanation?

Among decks forecast or observed at >=1%, the median absolute Online-vs-last-IRL movement is **1.17pp** (P80 **2.66pp**).
The performance term is smaller: median absolute adjustment **0.15pp**, P80 **0.44pp**.
Only **38.7%** of relevant deck observations receive a performance adjustment of at least 0.25pp, so performance should be shown as a callout only when material rather than as a permanent headline column.

When a material performance adjustment and Online movement point the same way, historical MAE is **1.01pp**; when they disagree it is **1.54pp**. This is diagnostic, not a new confidence formula.

## Can we trust the mover direction?

For decks moved at least **0.5pp** from last IRL, the forecast gets the direction of the eventual move right **81.9%** of the time and beats simply repeating last IRL on **74.6%** of those observations.
For decks moved at least **1.0pp** from last IRL, the forecast gets the direction of the eventual move right **90.8%** of the time and beats simply repeating last IRL on **81.2%** of those observations.

## Presentation conclusion

Recommended research output hierarchy: **Forecast %** first; **Last IRL -> Online since** as the visible evidence trail; a compact mover label; **performance only when its adjustment is material**; and an empirical uncertainty cue driven primarily by forecast-share band, with prior archetype volatility available as a secondary confidence modifier where enough history exists.

Do not turn the P80/P90 ranges into formal confidence intervals without a separate calibration study.
