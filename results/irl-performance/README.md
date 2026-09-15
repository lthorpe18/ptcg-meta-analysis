# IRL performance signal — Phase 1 evidence audit

## Research question

Which prior-IRL popularity-adjusted performance measures are reliably available and numerically stable enough to test as predictors of the next same-format IRL field? This phase deliberately does **not** use the next tournament outcome.

## Evidence and source coverage

- Events audited: **71**.
- Archetype-event rows from the archived Day-1 slug universe: **4643**; exact live-source joins: **4643**.
- Day-1 live entry totals exactly match the archived totals for **71/71** events; maximum absolute difference: **0** entries.
- Complete deck identity for ranks 1-32 was recovered for **69/71** events.
- Events with no exact-slug mismatch between archived and current Day-1 source: **71/71**.
- The source's displayed Day-1 `Win %` is reproducible from records as match-points earned / maximum match points: median absolute formula difference **0.003pp**, max **0.005pp**. It is labelled `points_rate` here to avoid overstating it as literal win percentage.

## Candidate performance measures

**Primary candidate for Phase 2:** Day-2 representation lift relative to Day-1 share, transformed as `log2((observed + 0.5)/(expected + 0.5))`. Zero means the archetype reached Day 2 at its expected rate; approximately +1/-1 means ~2x/~0.5x expected once counts are large enough. A bounded [-2,+2] version is also emitted for modelling.

Secondary candidates are event-centred Day-1 points rate, Top-32 representation lift using the same 0.5 correction, and a separate tournament-winner indicator as a possible visibility/hype effect. Raw Top-8 counts are not used as the primary signal.

## Small-archetype stability

| Day-1 share | Rows | Day-2 zero | Top-32 zero | Median |log2 Day-2 lift| | P90 |log2 Day-2 lift| |
|---|---:|---:|---:|---:|---:|
| <0.5% | 2851 | 84.0% | 98.2% | 0.47 | 1.29 |
| 0.5-1% | 446 | 38.1% | 87.8% | 0.80 | 2.34 |
| 1-2% | 404 | 15.8% | 73.2% | 0.65 | 1.89 |
| 2-5% | 500 | 5.0% | 42.9% | 0.49 | 1.37 |
| >=5% | 442 | 0.7% | 12.5% | 0.34 | 0.85 |

This table is diagnostic rather than a filtering rule. Very small archetypes are expected to produce more zero/high-ratio outcomes; Phase 2 must therefore compare minimum-share thresholds and the bounded/smoothed transform chronologically rather than silently excluding them.

## Signal agreement (Day-1 share >=1%)

Across **1346** archetype-event rows at >=1% Day-1 share, Pearson correlations are: Day-2 lift vs centred points rate **0.756**; Day-2 lift vs Top-32 lift **0.528**; centred points rate vs Top-32 lift **0.480**.

These correlations test whether the candidate measures broadly describe the same tournament performance, not whether any predicts future adoption.

## Phase-1 conclusion

**Verified:** the source supports Day-1 representation, Day-1 aggregate records/points rate, Day-2 representation, high-finish representation and tournament winner at archetype level. The exact coverage diagnostics above determine which can be used consistently.

**Inferred:** Day-2 relative representation is the most direct primary behavioural signal because it asks whether an archetype survived into Day 2 more or less often than its Day-1 popularity would imply, while using materially more observations than Top 8/Top 16. Day-1 points rate is the strongest complementary continuous signal; Top-32 and winner are useful visibility sensitivities.

**Limitation:** all performance pages are fetched retrospectively from current public Labs pages. Exact-slug mismatch diagnostics are retained because source taxonomy may have changed after the historical event. This phase does not claim the performance labels were frozen on the event date.

## Next bounded experiment

Phase 2 should join these prior-event signals to the existing adjacent same-format IRL cohort pairs, field-entry weight simultaneous majors into cohorts, and test whether performance predicts `next IRL share - previous IRL share` after controlling for previous share. Compare persistence vs persistence+performance with fixed chronological holdout and expanding walk-forward; include 0.5%/1%/2% share and bounded-transform sensitivities.
