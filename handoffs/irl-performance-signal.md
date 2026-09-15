# IRL performance signal — Phase 1 handoff

Date: 2026-09-15
Repository: `lthorpe18/ptcg-meta-analysis`
Research base: `historical-online-chunked` at `67310cbab568a2632cec96cedfce1b8118d25d3c`
Working branch: `research/irl-performance-signal`
Successful workflow: `34977235684`

## Research boundary

This work is a research-only extension of the historical archive. It does not modify `lthorpe18/ptcg-tools`, does not select a production forecasting formula, and does not merge any open research PR.

Phase 1 asks only:

> Which prior-IRL popularity-adjusted performance measures are reliably available and numerically stable enough to test as predictors of the next same-format IRL field?

It deliberately does **not** inspect next-tournament outcomes, so no result in this phase establishes predictive value.

## Verified base state

- `main` remains the documentation/foundation baseline; the substantial historical archive remains on `historical-online-chunked` / PR #5.
- PR #8 (`research/last-year-weighting`) contains the recent-year IRL/Online weighting analyses.
- PR #9 (`research/irl-to-irl-regression`) contains the adjacent same-format IRL persistence/decay analysis.
- This branch starts directly from PR #5 at `67310cb` so Phase 1 does not inherit either sibling experiment's model code or conclusions.
- Existing IRL ingestion stored Day-1 field shares only; it did not contain a performance predictor.

## Evidence collection

New collector: `scripts/collect_irl_performance.py`.

For the same 71 audited Masters majors already in `data/raw/irl/labs/index.json`, the collector retrieves public Limitless Labs aggregate evidence from:

- exact-variant Day-1 metagame view;
- exact-variant Day-2 metagame view;
- final standings.

The existing archived Day-1 slug universe remains authoritative. Live rows are joined only by exact slug; any current-source mismatch is recorded rather than silently remapped. Standings are reduced to rank/deck evidence and player identity is not retained.

Raw aggregate output: `data/raw/irl-performance/labs/`.

## Phase-1 signal construction

Analysis: `scripts/analyse_irl_performance_signal.py`.

Generated outputs:

- `data/processed/irl-performance/performance-signals.csv`
- `data/processed/irl-performance/event-audit.csv`
- `data/processed/irl-performance/summary.json`
- `results/irl-performance/README.md`

### Primary candidate

Day-2 representation relative to Day-1 popularity:

`expected Day-2 count = total Day-2 field × Day-1 archetype share`

`Day-2 performance = log2((observed + 0.5) / (expected + 0.5))`

Interpretation once counts are reasonably large: 0 is expected representation; +1 is about twice expected; -1 is about half expected. A bounded `[-2,+2]` version is emitted for later forecasting sensitivity.

### Secondary candidates

- Day-1 aggregate points rate, event-centred in percentage points. The source labels this `Win %`, but it exactly reproduces match points earned divided by maximum possible match points, so this research calls it `points_rate` rather than literal match win rate.
- Top-32 representation lift relative to Day-1 share, using the same +0.5 smoothing before log2 transform.
- Tournament winner indicator as a separate possible visibility/hype signal. It is not the main performance measure.

Raw Top-8 count is not used as a primary signal.

## Verified source reliability

Across all 71 events:

- 4,643 archived archetype-event rows and 4,643 exact current-source joins.
- Day-1 live entry totals match the archived Day-1 totals for **71/71** events; maximum difference **0** entries.
- Exact named-archetype slug sets match for **71/71** events.
- Day-1 points-rate evidence is available on all 4,643 rows.
- Day-2 performance evidence is available on all 4,643 rows.
- Complete rank/deck identity through Top 32 is available for **69/71** events. Special Event Lima (`0004`) has 31/32 identified rows; Special Event Auckland (`0051`) has 30/32. Top-32 signals are therefore absent rather than imputed for those incomplete events.
- Recomputing the displayed Day-1 points rate from W-L-T records has median absolute error **0.003 percentage points** and maximum **0.005pp**, consistent with display rounding.

## Verified small-archetype stability findings

The raw ratio problem is substantial and share-dependent:

| Day-1 share | Rows | Zero Day-2 rate | Zero Top-32 rate | Median absolute smoothed log2 Day-2 lift | P90 |
|---|---:|---:|---:|---:|---:|
| <0.5% | 2,851 | 84.0% | 98.2% | 0.47 | 1.29 |
| 0.5-1% | 446 | 38.1% | 87.8% | 0.80 | 2.34 |
| 1-2% | 404 | 15.8% | 73.2% | 0.65 | 1.89 |
| 2-5% | 500 | 5.0% | 42.9% | 0.49 | 1.37 |
| >=5% | 442 | 0.7% | 12.5% | 0.34 | 0.85 |

This is diagnostic, not a justification to discard small archetypes. Phase 2 must compare minimum Day-1 share thresholds (planned 0.5%, 1%, 2%) and bounded vs unbounded smoothed transforms.

## Verified signal agreement

At Day-1 share >=1% (1,346 archetype-event rows):

- Day-2 lift vs event-centred Day-1 points rate: **r = 0.756**.
- Day-2 lift vs Top-32 lift: **r = 0.528**.
- Event-centred points rate vs Top-32 lift: **r = 0.480**.

These are contemporaneous performance correlations only. They do not show future adoption.

## Inferred interpretation

Day-2 relative representation is the best primary signal to take forward because it directly asks whether an archetype advances beyond Day 1 more or less frequently than its starting popularity implies, while using materially more observations than Top-8/16/32 finishes.

Day-1 event-centred points rate is the strongest complementary continuous measure because it uses all Day-1 match evidence and is not mechanically increased by archetype popularity. Top-32 lift and the winner indicator are better treated as high-visibility sensitivities than as primary performance measures.

The 0.756 correlation between Day-2 lift and points rate means they capture substantially overlapping tournament performance. They should therefore first be tested separately before any combined performance model is considered.

## Limitations / Unknown

- Performance pages were collected retrospectively from the current public Labs source. The exact Day-1 archived totals/slugs still match perfectly, which is reassuring, but this does not independently prove every historical performance label was frozen on the event date.
- Day-2 qualification structures can differ by event size/rules; relative representation mitigates popularity but does not automatically make every tournament structurally identical.
- Small archetypes remain statistically noisy even after +0.5 smoothing.
- Top-32 evidence is incomplete for two events and is intentionally not imputed.
- No causal or predictive conclusion is authorised from Phase 1.

## Exact next bounded experiment — Phase 2

Join prior-event performance to the existing eligible adjacent same-format IRL cohort pairs and test:

> After controlling for previous IRL Day-1 share, does previous-tournament relative performance predict `next IRL share - previous IRL share`?

Requirements:

1. Preserve the existing same-format adjacent-cohort construction and >=95% IRL capture rule from the IRL-to-IRL research.
2. Aggregate simultaneous majors into the same existing IRL cohort before they become predictor evidence; do not let same-weekend events predict each other.
3. Start with one performance term at a time: Day-2 lift primary, then centred points rate, Top-32 lift and winner as sensitivities.
4. Compare persistence against composition-preserving persistence + performance. Forecast shares must remain non-negative and renormalise to 100%.
5. Test 0.5% / 1% / 2% prior-share thresholds and bounded vs unbounded Day-2 transforms explicitly.
6. Use fixed chronological early-train/later-holdout and expanding walk-forward validation where sample size permits.
7. Report Field Accuracy, change versus persistence, independent cohort count and recent-year sensitivity.
8. Do not add Online evidence yet. Online mediation belongs to the later experiment only after the IRL-performance-only question is resolved.

Do not merge without explicit owner authorisation.
