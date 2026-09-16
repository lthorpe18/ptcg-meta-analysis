# Combined corrected Online + previous-major performance — handoff

Date: 2026-09-16
Repository: `lthorpe18/ptcg-meta-analysis`
Working branch: `research/combined-online-performance`
Parent performance research: PR #11 / `research/irl-performance-to-next-irl`
Concentration-correction source: PR #13 / `research/concentration-corrected-blend`
Workflow run: `35082582338`

## Research question

> Does the already-demonstrated previous-major Day-2 performance signal add incremental next-IRL forecast value after the concentration-corrected IRL+Online model, or is most of its useful information already visible in Online movement?

Secondary evaluation question:

> Does headline Field Accuracy reflect accuracy on the decks a player actually cares about?

The existing project convention is used for that diagnostic: include archetypes with **predicted OR actual share >=1%**. Actual top-10 MAE is also reported. These metrics are evaluation-only and do not tune the model.

## Frozen model components

Corrected IRL+Online baseline is frozen rather than retuned:
- 80% starting IRL weight;
- -1pp/day;
- 55% IRL floor;
- 75% correction of the previous-IRL top-10 Online concentration gap.

Performance feature is the PR #11 primary specification:
- bounded Day-2 log2 relative-representation lift [-2,+2];
- active only for previous-IRL archetypes >=1%;
- composition-preserving feature;
- one scalar beta fitted to the residual left after the corrected IRL+Online baseline.

Primary validation is expanding chronological replay after 10 earlier matched cohorts, matching PR #13's replay start. A 15-prior-cohort replay is retained as sensitivity. No target outcome fits its own beta.

## Matched sample

- 30 target events;
- 23 independent cohorts with both complete corrected-Online inputs and previous-major performance evidence;
- primary expanding replay tests the later 13 cohorts.

## Verified — primary expanding replay

Field Accuracy:
- frozen corrected IRL+Online: **84.39%**;
- + previous-major performance: **84.97%**;
- incremental gain: **+0.577pp**;
- improved **9/13** cohorts, worsened 4/13.

Robustness:
- replay beginning only after 15 prior cohorts: **84.83% -> 85.44%**, **+0.609pp**;
- frozen recent-era split from 2025-08-28: **84.48% -> 84.98%**, **+0.495pp**.

Full-sample descriptive fit is 84.12% -> 84.60% (+0.477pp), with fitted beta 0.1696. This is descriptive, not validation.

## Verified — decks that matter

On the same primary expanding replay, for decks with predicted OR actual share >=1%:
- mean absolute share error: **1.10pp -> 1.09pp**; improvement only **0.005pp**;
- share of relevant decks within 1pp of actual: **64.5% -> 63.3%** (slightly worse);
- actual top-10 deck MAE: **1.64pp -> 1.57pp**, an improvement of about **0.06pp**.

This is an important distinction: the performance term materially improves total-distribution Field Accuracy, and helps the largest decks somewhat, but it does **not** materially improve the average >=1% archetype estimate.

## Interpretation

**Verified:** previous-major performance retains incremental information after concentration-corrected Online movement. The positive gain appears in the primary chronological replay, the later-start replay, and the frozen recent-era split.

**Verified:** the headline Field Accuracy gain overstates the practical improvement for a typical individually relevant archetype. The frozen baseline already misses >=1% decks by about 1.10 percentage points on average, and the performance term barely changes that.

**Inferred:** this research is reaching diminishing returns if the sole objective remains raising aggregate Field Accuracy. Further work should separate two goals: (1) central field-distribution accuracy and (2) useful per-archetype accuracy/uncertainty for the decks likely to matter to a player.

**Unknown:** future-event gain. Both component ideas were developed on overlapping historical data, so chronological replay is stronger than in-sample fitting but not equivalent to a genuinely untouched future tournament.

## Exact next action

Owner decision. Do not merge automatically.

If continuing research, prioritise diagnostic evaluation of the forecast users actually consume rather than another broad parameter search: error by archetype share band, top-N identity/share accuracy, and calibrated uncertainty for >=1% decks. Avoid adding further model complexity unless it improves those user-relevant metrics chronologically.
