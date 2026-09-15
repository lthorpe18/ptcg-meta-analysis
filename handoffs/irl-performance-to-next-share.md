# IRL performance → next IRL share — Phase 2 handoff

Date: 2026-09-15
Repository: `lthorpe18/ptcg-meta-analysis`
Research base: `historical-online-chunked` at `67310cbab568a2632cec96cedfce1b8118d25d3c`
Working branch / PR: `research/irl-performance-signal` / PR #10
Successful workflows: Phase 1 `34977235684`; Phase 2 `34980170095`; recent sensitivity `34980345823`.

## Research question

> After accounting for how popular an archetype already was, does overperformance at one IRL major predict increased representation at the next adjacent same-format IRL major cohort?

This phase uses IRL evidence only. It does not use subsequent Online play and therefore does not yet test mediation by Online adoption.

## Evidence and model

- 36 eligible adjacent same-format IRL cohort pairs across 10 formats.
- Same >=95% Day-1 field-capture rule and strict adjacency as the IRL-to-IRL regression work; no skipping intervening cohorts.
- Simultaneous majors remain one field-entry-weighted cohort.
- Primary performance signal: bounded [-2,+2] smoothed log2 Day-2 representation lift relative to Day-1 popularity.
- Previous IRL field remains the forecast anchor. Performance only tilts that composition; negative shares are clipped and the result renormalised to 100%.
- Pair-fixed-effect descriptive regression controls for previous share.
- Validation: fixed chronological 70/30 holdout and expanding walk-forward after 15 earlier pairs.

## Verified association

Pair-fixed-effect regression of next-field share change on previous share plus prior performance gives:

- performance coefficient: **+0.250 percentage points of next-field share per +1 unit of bounded log2 Day-2 lift**;
- format-cluster bootstrap 95% interval: **[+0.183, +0.316]pp**.

This establishes a positive historical association after controlling for prior popularity. It is not on its own a forecasting result.

## Verified forecasting results

Primary bounded Day-2 signal, no minimum-share exclusion:

- full-sample fitted: persistence **83.89%** vs performance-adjusted **84.35%** = **+0.462pp**;
- fixed chronological holdout: **85.14% → 85.27% = +0.135pp** on 11 test pairs;
- expanding walk-forward: **84.79% → 85.12% = +0.334pp** on 21 chronological targets.

All tested performance variants were positive versus persistence in both chronological comparisons. Walk-forward improvements ranged from **+0.173pp** for event-centred Day-1 points rate to **+0.334pp** for the primary bounded Day-2 signal; Top-32 lift was essentially tied with the primary at **+0.332pp**.

Minimum-share sensitivities did not improve on simply bounding the Day-2 signal: 0.5%, 1% and 2% thresholds produced walk-forward gains of +0.296pp, +0.299pp and +0.300pp respectively. The bounded all-share version therefore remains the simplest primary specification at this stage.

## Recent-era sensitivity

Latest 365 days ending at the final eligible target date: 18 adjacent pairs across 6 formats (2025-06-12 to 2026-06-12).

For each recent target, the coefficient was fitted using all eligible historical pairs strictly earlier than that target:

- persistence **84.54%**;
- performance-adjusted **84.96%**;
- improvement **+0.423pp** across all 18 recent targets.

All tested variants remained positive in this recent chronological sensitivity; the primary bounded Day-2 signal was +0.423pp and Top-32 lift +0.430pp.

## Interpretation

**Verified:** prior IRL performance contains incremental historical information about next-major field movement beyond simply knowing previous IRL share. The effect is modest but positive in the fixed holdout, expanding walk-forward and recent-target sensitivity.

**Inferred:** players appear to respond to deck performance at majors: decks that survive into Day 2 more often than their Day-1 popularity predicts tend, on average, to gain some representation at the next same-format major. The magnitude is small enough that previous IRL share should remain the dominant anchor.

**Not yet established:** that performance adds information beyond subsequent Online adoption. The hypothesised causal pathway may be `IRL overperformance → Online adoption → next IRL adoption`, in which case Online movement could absorb much or most of the apparent performance effect.

## Limitations

- Only 36 independent adjacent cohort pairs across 10 formats; recent sensitivity is 18 pairs / 6 formats.
- Performance evidence was reconstructed retrospectively from current public Labs pages.
- Forecast improvements are fractions of a percentage point; they should not be described as a large accuracy breakthrough.
- This model cannot predict genuinely new archetypes absent from the previous IRL field; that is one reason Online evidence remains important.
- This phase contains no matchup evidence and says nothing directly about which deck a player should choose for a specific predicted field.

## Exact next bounded experiment

Test the mediation / incremental-information question using the clean three-stage structure:

`previous IRL field → subsequent Online field → next IRL field`

For each adjacent same-format pair construct:

- previous IRL share;
- post-major, pre-target Online share using only evidence available before the target;
- Online movement = Online share − previous IRL share;
- next IRL movement = next IRL share − previous IRL share;
- previous-IRL bounded Day-2 performance signal.

Compare chronologically:

1. previous IRL only;
2. previous IRL + performance;
3. previous IRL + Online movement;
4. previous IRL + Online movement + performance.

The critical result is whether model 4 improves on model 3. If performance largely disappears after Online movement is included, Online play is probably already carrying the market response to major performance. If performance remains useful, it is an independent forecasting feature, potentially most valuable soon after a major before much Online evidence accumulates.

Do not merge without explicit owner authorisation. No result here changes `lthorpe18/ptcg-tools` automatically.
