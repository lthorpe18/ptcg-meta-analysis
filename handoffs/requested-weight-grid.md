# Exhaustive requested IRL-weight grid handoff

Date: 15 September 2026
Repository: `lthorpe18/ptcg-meta-analysis`
Base research state: `historical-online-chunked` at `67310cbab568a2632cec96cedfce1b8118d25d3c`
Working branch / PR: `research/last-year-weighting` / PR #8

## Explicit owner question

Run all combinations of these IRL-weight variables over the same latest-year analysis window, with Online always the remainder:
- initial IRL weight: 100%, 95%, 90%, 85%, 80%;
- daily IRL loss: 1, 2, 3, 4, 5 percentage points per day;
- IRL floor: 50%, 45%, 40%, 35%, 30%, 25%, 20%, 15%, 10%.

Compare the resulting rules with flat 50/50, 100% IRL and 100% Online.

## Evidence and metric

**Verified:** same frozen recent-year sample as the parent experiment: 2025-08-28 through 2026-08-28; 16 settled-format tournaments across 11 independent cohorts; >=95% IRL field capture and complete blend components.

**Verified:** primary metric is cohort-weighted Field Accuracy using the existing named-archetype scoring policy. Same-weekend tournaments are averaged before the primary comparison.

**Verified:** 5 initial weights x 5 decay rates x 9 floors = 225 combinations. Weight rule: `max(floor, initial_IRL_weight - daily_loss * days_since_previous_major)`. Online receives the remainder.

## Generated result

Baselines:
- flat 50/50: 84.11%
- 100% IRL: 82.20%
- 100% Online: 76.37%

**Verified in-sample winner:** 95% initial IRL / 3pp per day loss / 20% IRL floor = 84.78% cohort-weighted accuracy.

Winner margins:
- +0.66pp vs flat 50/50;
- +2.57pp vs 100% IRL;
- +8.40pp vs 100% Online.

Rule counts:
- 186 / 225 beat flat 50/50;
- 225 / 225 beat 100% IRL;
- 225 / 225 beat 100% Online;
- 186 / 225 beat all three baselines.

The top of the grid is very shallow: ranks 1-15 span about 84.75%-84.78%. Nearby winners include 95/3pp/15, 95/3pp/25, 85/2pp/30, and 90/3pp/20. This supports a broad pattern more strongly than one exact triplet.

Best available result by initial weight:
- 100% start: 84.74% at 4pp/day, 20% floor;
- 95% start: 84.78% at 3pp/day, 20% floor;
- 90% start: 84.77% at 3pp/day, 20% floor;
- 85% start: 84.77% at 2pp/day, 30% floor;
- 80% start: 84.75% at 2pp/day, 25% floor.

Best available result by daily loss:
- 1pp/day: 84.60%;
- 2pp/day: 84.77%;
- 3pp/day: 84.78%;
- 4pp/day: 84.74%;
- 5pp/day: 84.69%.

Best available result by floor rises from 84.69% at 50% to ~84.77-84.78% around 15-30%, then is 84.76% at 10%. This suggests the recent sample generally prefers allowing Online evidence to become the majority after enough time, rather than holding IRL at >=50%.

## Interpretation boundary

**Verified:** these are exhaustive in-sample comparisons across the same 11 recent cohorts. They do not establish an out-of-sample winning formula.

**Inferred:** the stable high-performing region is roughly high initial IRL weight (85-95%), relatively fast decay (2-3pp/day), and a low/moderate IRL floor (15-35%).

Do not infer that 95/3/20 is meaningfully superior to nearby rules: the numerical differences are only hundredths of an accuracy point.

Do not use this result as automatic authority to change PTCG Tools.

## Reproducibility

- Analysis: `scripts/analyse_requested_weight_grid.py`
- Full 225-rule CSV: `data/processed/last-year-weighting/requested-grid/all_rules.csv`
- Generated JSON: `data/processed/last-year-weighting/requested-grid/summary.json`
- Human-readable result: `results/last-year-weighting/requested-grid.md`
- Workflow: `.github/workflows/run-last-year-weighting.yml`
- Successful run: `34958292924`

## Exact next action

None authorised. This is a one-off exploratory extension of PR #8. PR #8 remains open and unmerged. If no further work is wanted on this question, it can be closed without merging while preserving the audit trail.
