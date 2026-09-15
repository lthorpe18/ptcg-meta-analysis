# IRL-to-IRL regression handoff

Date: 2026-09-15

## Owner question

> Run a full regression analysis JUST comparing IRL tournament to IRL tournament of the same format.

Research question used:

**How predictive is one IRL major weekend of the next same-format IRL major weekend, and does that relationship decay with elapsed time?**

## Research boundary

- Repository: `lthorpe18/ptcg-meta-analysis` only.
- Research base: `historical-online-chunked` at `67310cbab568a2632cec96cedfce1b8118d25d3c` (PR #5 remains open/unmerged).
- Branch: `research/irl-to-irl-regression`.
- Online evidence: **none**.
- Existing IRL archive, format tags and prediction-window cohorts are reused without changing ingestion, taxonomy or cohort membership.
- Pair = adjacent existing IRL cohorts within identical `display_format`; no skipping an intervening cohort.
- Both sides of a retained pair require every event in that cohort to have >=95% captured Day-1 field coverage.
- Events inside a multi-event weekend/cohort are field-entry weighted.

## Implemented analysis

Primary script: `scripts/analyse_irl_to_irl_regression.py`.

Generated outputs:
- `data/processed/irl-regression/summary.json`
- `data/processed/irl-regression/pairs.csv`
- `results/irl-regression/README.md`

Sensitivity script: `scripts/analyse_irl_regression_sensitivity.py`.

Sensitivity outputs:
- `data/processed/irl-regression/sensitivity.json`
- `results/irl-regression/SENSITIVITY.md`

Workflow: `.github/workflows/run-irl-to-irl-regression.yml`.
Successful run: `34974082965`.
Generated-output commit after that run: `cb8a354fd863e87cd8e4881b14249c1483388429`.

## Verified evidence/sample

- 55 existing IRL overlap cohorts in the archive.
- 36 eligible adjacent same-format cohort pairs across 10 formats.
- Pair target dates span 2024-10-19 through 2026-06-12; source evidence begins 2024-10-11.
- Median post-weekend gap = 6 days; range 5-47 days.
- 25/36 pairs are <=7 days apart, 8 are 8-14 days, and only 3 exceed 14 days.

## Verified findings

### 1. The previous IRL weekend is already a strong predictor

Persistence baseline (`next field = previous same-format IRL cohort`) across all 36 pairs:
- mean Field Accuracy **83.89%**
- median **84.57%**

This is a direct IRL-to-IRL stability result, not an IRL/Online blend result.

### 2. Full-history time-decay signal is negative but not statistically decisive

Pair-level persistence accuracy vs days after the prior weekend:
- overall slope **-0.169 accuracy points/day** (~-1.18pp per 7 days), R² 0.111
- 95% format-cluster bootstrap CI **[-0.378, +0.063] pp/day**
- within-format slope **-0.200 pp/day** (~-1.40pp per 7 days)
- 95% format-cluster bootstrap CI **[-0.446, +0.045] pp/day**

Both central estimates are negative, but both CIs cross zero. Do **not** claim a proven full-history decay rate.

Observed mean persistence accuracy by gap bucket:
- 0-7 days: **84.53%** (25 pairs)
- 8-14 days: **83.58%** (8 pairs)
- 22-35 days: **81.37%** (2 pairs)
- 36+ days: **75.32%** (1 pair)

The long-gap tail is sparse and influential.

### 3. Archetype shares show strong persistence and mild mean reversion

Pair-fixed-effect archetype-share regression:
- prior-share slope at median 6-day gap: **0.954**
- 95% format-cluster bootstrap CI **[0.932, 0.989]**
- share×gap interaction: **-0.0020/day**
- interaction CI **[-0.0110, +0.0020]**

The <1 median-gap slope is consistent with regression toward the broader field / prior format mean rather than exact 1:1 persistence. The negative gap interaction is directionally consistent with staleness, but its CI crosses zero.

Implied descriptive share-retention slopes from this regression:
- 7 days: 0.952
- 14 days: 0.938
- 21 days: 0.924
- 28 days: 0.911
- 35 days: 0.897

These are descriptive regression slopes, **not IRL-vs-Online weights**.

### 4. Composition-preserving shrinkage fits suggest ~85% retention in-sample, but do not beat persistence reliably

Full-sample composition-preserving fit uses the earlier same-format IRL mean as an anchor:

`target = format_mean + lambda * (previous_IRL - format_mean)`

In-sample:
- constant lambda = **0.849**
- gap-aware lambda at median 6-day gap = **0.859**
- fitted gap interaction = **-0.00375/day**

Interpretation: in-sample, the previous weekend carries roughly 85% of the deviation from the earlier same-format IRL mean. This is not an Online blend formula.

Fixed chronological holdout (first 25 pairs fit, final 11 pairs test):
- persistence **85.14%**
- constant shrinkage **85.23%** (+0.09pp)
- gap-aware shrinkage **85.23%** (+0.09pp)
- gap + format-age shrinkage **85.19%** (+0.05pp)

Expanding walk-forward after >=15 earlier pairs (21 later targets):
- persistence **84.79%**
- constant shrinkage **84.77%** (-0.02pp)
- gap-aware shrinkage **84.75%** (-0.04pp)
- gap + format-age shrinkage **84.72%** (-0.07pp)

**Verified conclusion:** regression/shrinkage has not demonstrated an out-of-sample improvement over simply using the latest same-format IRL field.

### 5. Two-weekend trend does not show useful positive momentum

The fitted full-sample coefficient on `(previous IRL - IRL two weekends ago)` is **-0.113**, i.e. slight **reversal/mean reversion**, not positive momentum.

On the same subsets:
- fixed holdout trend model: **86.48%** on 7 eligible targets vs persistence **86.38%** on those same 7 (+0.10pp)
- expanding walk-forward trend model: **86.85%** on 14 targets vs persistence **86.66%** on those same 14 (+0.19pp)

These gains are too small and the sample too restricted to claim predictive improvement.

### 6. Recent-year sensitivity is stronger and is the most interesting new signal

Latest 365 days (2025-06-12 to 2026-06-12): 18 pairs across 6 formats.
- overall gap slope **-0.310 pp/day** (~-2.17pp per 7 days)
- format-cluster bootstrap CI **[-0.641, -0.236]**
- within-format slope **-0.369 pp/day** (~-2.58pp per 7 days)
- CI **[-0.866, -0.311]**

Restricting the same recent-year sample to gaps <=14 days (16 pairs across 6 formats; within-format slope uses 4 formats):
- overall slope **-0.503 pp/day**
- cluster CI **[-1.489, -0.117]**
- within-format slope **-0.675 pp/day**
- CI **[-1.378, -0.301]**

This means the recent-year negative gap relationship is not solely produced by the 27/47-day gaps.

**Interpretation:** this is evidence that IRL fields may have become more time-sensitive in the recent era, consistent with the owner's hypothesis of a more active/competitive modern meta. However, it is only 18 pairs / 6 formats, and the <=14-day within-format sensitivity effectively draws slope information from only 4 formats. Treat as a supported recent-era hypothesis requiring further validation, not a calibrated production decay law.

## Supported / unsupported claims

### Verified / supported
- Adjacent same-format IRL fields are highly similar (~83.9% mean persistence Field Accuracy).
- Archetype shares show strong <1 retention, consistent with modest mean reversion.
- Full-history gap slopes are negative in both overall and within-format regressions.
- The full-history uncertainty intervals include zero.
- Recent-year gap slopes are materially more negative and their format-cluster bootstrap intervals in this analysis stay below zero.
- Simple regression shrinkage and gap-aware regression do not produce a demonstrated chronological improvement over persistence.
- The prior-two-weekend trend coefficient is negative, not positive.

### Inferred
- Modern IRL metagames may stale faster between major weekends than older archived eras.
- This may help explain why dynamic IRL/Online weighting was useful in the separate recent-year blend experiments.
- A practical blend may benefit from treating recent IRL as very strong immediately after a major but allowing newer evidence to displace it as the gap grows.

### Not supported / Unknown
- A precise universal IRL decay rate.
- That the latest-year slope will persist into future formats.
- That the IRL-to-IRL regression coefficient can be substituted directly for an IRL-vs-Online blend weight.
- That regression/shrinkage should replace latest-IRL persistence in the forecasting model.
- Causal explanation for the stronger recent-era gap relationship.

## Exact next action

None authorised. If the owner wants to extend this question, the highest-value next test would be a **recent-era rolling/leave-format-out validation** of the gap effect (e.g. fit the decay relationship on earlier recent formats and test on the next unseen format), because the current recent-year slope is the strongest new finding but is based on only six formats.

Do not merge without explicit owner authorisation.
