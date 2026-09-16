# Forecast presentation intelligence — handoff

Date: 2026-09-16
Repository: `lthorpe18/ptcg-meta-analysis`
Branch: `research/forecast-presentation-intelligence`
Parent: PR #16 / `research/forecast-user-relevance`
Workflow run: `35084204747`

## Research question

> How should the validated next-IRL forecast be presented so users see the estimate, Last IRL anchor, Online movement, useful performance explanation and realistic uncertainty?

This is presentation/evaluation research only. It does not tune the PR #15 combined forecast.

## Sample

Uses the exact PR #15 primary expanding chronological replay:
- 18 events;
- 13 independent cohorts;
- 1,820 deck-event rows.

## Verified — empirical uncertainty

By displayed forecast share:

| Forecast share | MAE | P80 abs error | P90 abs error |
|---|---:|---:|---:|
| 10%+ | 2.39pp | 3.17pp | 4.98pp |
| 5–10% | 1.38pp | 2.11pp | 2.80pp |
| 2–5% | 1.17pp | 1.81pp | 2.36pp |
| 1–2% | 0.63pp | 0.85pp | 1.15pp |

These are empirical historical replay errors, not formal confidence intervals.

PR #14 independently established that prior archetype residual volatility adds modest uncertainty information (r=.236; low-volatility next error .68pp vs high-volatility 1.28pp). That result is referenced, not recomputed here because PR #14 is a sibling branch.

## Verified — evidence/explanation hierarchy

For decks forecast or observed >=1%:
- median absolute raw Online-vs-Last-IRL movement = **1.17pp**; P80 **2.66pp**;
- median absolute performance adjustment = **0.15pp**; P80 **0.44pp**;
- only **38.7%** of relevant deck observations get a performance adjustment >=0.25pp.

Therefore Online movement is a first-class visible signal; performance is usually a smaller modifier and should be called out only when material rather than occupying a permanent headline column.

Among material-performance observations:
- Online + performance same direction: 72 observations / 13 cohorts, MAE **1.01pp**; movement direction correct **88.8%** where a >=.5pp forecast move was made;
- Online + performance disagree: 75 observations / 13 cohorts, MAE **1.54pp**; movement direction correct **58.4%**.

This supports using signal agreement/disagreement as explanatory confidence context, but it has not been calibrated into a formal confidence score.

## Verified — mover reliability

For relevant decks moved >=0.5pp from Last IRL by the forecast:
- 148 observations / 13 cohorts;
- eventual movement direction correct **81.9%**;
- forecast beats simply repeating Last IRL **74.6%**.

For moves >=1.0pp:
- 53 observations / 13 cohorts;
- direction correct **90.8%**;
- forecast beats Last IRL **81.2%**.

Thus a visible mover label has genuine historical meaning. Large forecast moves are much more reliable directionally than exact percentage estimates are numerically.

## Recommended research-output hierarchy

1. **Forecast %** — primary answer, sorted by expected field share.
2. **Last IRL -> Online since** — visible evidence trail, with Online delta/mover direction.
3. **Mover label** — emphasize >=0.5pp; >=1pp is historically especially directionally reliable.
4. **Performance callout only when material** — e.g. adjustment >=0.25pp; avoid a permanent performance column for every deck.
5. **Empirical uncertainty cue** — primarily forecast-share-band historical error; optionally modified by prior archetype volatility when enough history exists.
6. **Signal conflict warning** — when Online and material performance point opposite ways, avoid overstating confidence.

## Interpretation

**Verified:** the forecast's direction of meaningful deck movement is substantially more reliable than its exact share estimate. This supports presenting movement as first-class intelligence rather than only a hidden model input.

**Verified:** Online movement is generally much larger than the performance adjustment. Performance is useful but usually secondary.

**Inferred:** a concise user-facing row should look conceptually like `Forecast | Last IRL -> Online | mover | uncertainty`, with a short performance note only where material. This better matches what the historical evidence can support than displaying many precise-looking percentages or model internals.

**Unknown:** whether P80/P90 historical ranges are calibrated as future probabilistic intervals. They must not be labelled 80%/90% confidence intervals without a separate calibration experiment.

## Exact next action

Owner decision. Do not merge automatically and do not change the production PTCG Tools app.

If this output approach is accepted, the next bounded research task should be to generate the **current next-event intelligence table** using these presentation rules, not another model-parameter search.
