# Flat split and Online recency experiment handoff

Date: 15 September 2026
Repository: `lthorpe18/ptcg-meta-analysis`
Base research state: `historical-online-chunked` at `67310cbab568a2632cec96cedfce1b8118d25d3c`
Working branch / PR: `research/last-year-weighting` / PR #8

## Explicit owner questions

1. Test flat IRL/Online splits beyond 50/50.
2. Test whether Online evidence should be weighted more heavily toward the target tournament date.
3. Present the conclusions together with the prior dynamic IRL-weight work.

## Evidence and scoring

**Verified:** same frozen recent-year sample as PR #8: 2025-08-28 through 2026-08-28; 16 settled-format tournaments across 11 independent cohorts; >=95% IRL field capture and complete latest-IRL/post-major-Online components.

**Verified:** primary metric is cohort-weighted Field Accuracy under the existing named-archetype scoring policy. Same-weekend tournaments are averaged before the primary comparison.

No ingestion, archetype identity, format assignment, target eligibility or prediction-window membership was changed.

## Flat split experiment

Tested constant IRL weights from 0% through 100% in 5pp increments. Online is the remainder and uses the existing post-major Online aggregation.

**Verified in-sample result:** best flat split = **60% IRL / 40% Online**, 84.40% cohort accuracy. 65/35 is effectively tied at 84.40%; 55/45 = 84.31%; flat 50/50 = 84.11%.

**Verified fixed chronological holdout:** tuning on the first six cohorts selected **55% IRL / 45% Online**. On the final five untouched cohorts it scored **83.73%**, versus **83.40%** for flat 50/50.

Interpretation: the recent sample contains a modest but repeatable preference for a small IRL majority rather than exactly 50/50.

## Online recency experiment

Recency factors multiply each Online event's deck/player-entry counts; larger tournaments therefore remain larger contributors. Methods tested:
- equal/current weighting;
- last 7/14/21/28 days only;
- linear weighting across the available post-major evidence span;
- exponential weighting with 3/7/14/21/28-day half-lives.

The 7-day window lacked evidence for 5/16 targets and the 14-day window lacked evidence for 1/16, so they were not eligible for full-sample model selection. All exponential methods, equal/current, linear, 21-day window and 28-day window covered all 16 targets.

At fixed 50/50 IRL/Online:
- equal/current = 84.11%;
- best recency = **7-day exponential half-life, 84.14%**;
- 14-day = 84.13%; 21-day = 84.13%; 3-day = 84.12%; 28-day = 84.12%;
- linear = 83.86%.

**Verified:** recency weighting alone adds only about **0.03pp** in-sample at fixed 50/50.

**Verified holdout:** training selected 7-day exponential half-life; holdout = **83.44%**, versus **83.40%** for equal/current flat 50/50. The holdout improvement is only ~0.04pp.

Interpretation: there is no strong evidence that Online recency weighting by itself materially improves prediction accuracy on this sample.

## Flat split plus recency

**Verified in-sample result:** best flat+recency model = **65% IRL / 35% Online with a 3-day exponential Online half-life**, 84.45%.

**Verified holdout:** training selected **55% IRL plus 7-day Online half-life**, scoring **83.77%** on the final five cohorts. This is +0.04pp over the selected flat split without recency (83.73%).

Again, most of the improvement comes from the IRL/Online split, not the recency weighting.

## Dynamic IRL decay plus Online recency

Combined every full-coverage Online recency method with the owner-requested 225-rule IRL start/decay/floor grid (2,025 complete candidates).

**Verified in-sample winner:** **95% IRL start / -3pp per day / 20% floor + 3-day exponential Online half-life = 84.88%**.

This is only ~0.10pp above the same dynamic IRL rule family with equal/current Online evidence (best previous result 84.78%).

**Verified fixed chronological holdout:** training on the first six cohorts selected **80% start / -2pp per day / 25% floor + 3-day exponential Online half-life**. On the final five untouched cohorts it scored **84.34%**.

Relevant holdout comparisons:
- dynamic IRL grid without recency, selected from the same first six cohorts in the prior experiment: **84.30%**;
- dynamic IRL + recency: **84.34%**;
- selected flat split + recency: 83.77%;
- selected flat split, equal Online: 83.73%;
- flat 50/50: 83.40%;
- 100% IRL: 83.08%.

Thus Online recency contributes roughly **+0.04pp** on the chronological holdout once the IRL decay rule is already present.

## Important Online-only terminology

The flat-split model's 0% IRL / 100% Online endpoint means **100% of the post-major Online component used by the blend**, which scores 78.39% across the full recent sample.

This is distinct from the earlier research model named `online_only`, which uses **all qualifying same-format Online evidence before the target cutoff** and scored 76.37% on the same recent-year comparison. Do not conflate these two baselines.

## Overall conclusion

**Verified:** the useful signal is primarily the IRL/Online balance and its evolution after a major, not sophisticated weighting inside the Online sample.

**Verified:** recent data favours:
- a modest IRL majority for a simple static model (~55-65% IRL);
- for a dynamic model, a high initial IRL share that falls fairly quickly toward Online evidence;
- allowing Online eventually to become the majority.

**Inferred:** recency-weighting Online events may offer a very small incremental benefit, especially short exponential half-lives, but the observed gain is only a few hundredths of an accuracy point and is not strong enough to justify additional model complexity on current evidence.

Do not claim an out-of-sample winning production formula. The holdout has only five independent cohorts.

## Reproducibility

- Analysis: `scripts/analyse_flat_and_online_recency.py`
- Generated JSON: `data/processed/last-year-weighting/flat-and-recency/summary.json`
- Human-readable report: `results/last-year-weighting/flat-and-online-recency.md`
- Workflow: `.github/workflows/run-last-year-weighting.yml`
- Successful run: `34959860165`

## Exact next action

None authorised. PR #8 remains open and unmerged. If no further work is wanted on this one-off question, close PR #8 without merging and retain it as an auditable exploratory result. If further validation is wanted, the highest-value next step would be rolling/expanding chronological validation rather than adding more recency parameters.
