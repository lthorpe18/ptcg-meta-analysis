# Archetype responsiveness and volatility

This extends the residual-bias diagnostic by asking whether archetypes respond differently to the **corrected Online movement signal**, rather than merely carrying a persistent additive bias.

## Chronological forecasting comparison

Across 15 expanding-replay cohorts:

- frozen concentration-corrected baseline: **84.62%**;
- one global residual-response coefficient fitted from earlier cohorts: **84.91%** (+0.296pp);
- partially pooled exact-archetype response coefficients (k=5): **84.61%** (-0.003pp vs baseline; -0.299pp vs global).

Archetype-specific response beats the global response in **8/15** cohorts and beats the frozen baseline in **8/15**.

Partial-pooling sensitivity: k=2: -0.539pp vs global; k=5: -0.299pp vs global; k=10: -0.099pp vs global; k=20: -0.001pp vs global.

## Does archetype volatility persist?

Using only earlier residual history (minimum 3 observations), prior archetype residual SD vs next absolute residual: **r=0.236** across **407** observations.

Deck-observations below the median prior volatility subsequently miss by **0.68pp** on average; above-median prior volatility miss by **1.28pp** (+0.60pp).

## Interpretation boundary

A global-response improvement would mean the base forecast is systematically under/over-reacting to Online movement. Only an additional gain from the partially pooled model is evidence that **archetype-specific responsiveness** helps prediction.

A positive chronological volatility relationship can support archetype-specific uncertainty/confidence even if archetype-specific point-estimate adjustments do not help.
