# Last-year weighting experiment handoff

Date: 15 September 2026
Repository: `lthorpe18/ptcg-meta-analysis`
Base research state: `historical-online-chunked` at `67310cbab568a2632cec96cedfce1b8118d25d3c`
Branch: `research/last-year-weighting`

## Explicit research question

**Verified owner question:** what interpretable IRL/Online weighting formula would have been most accurate over the most recent year of archived play?

This follows the separate accuracy-over-time experiment (PR #7), which found a positive chronological trend specifically in settled-format Online-only prediction accuracy. The owner's hypothesis that greater participation and competitiveness may cause this is **Inferred / untested**, not assumed by this experiment.

## Evidence window and sample

- Window: **2025-08-28 through 2026-08-28**, the final 365 days ending at the latest archived >=95%-complete IRL target.
- Scored blend sample: **16 settled-format tournaments across 11 independent cohorts**.
- Eligibility: existing >=95% IRL capture threshold; settled-format; Online-only, IRL-only, 50/50 and current-v2.1 components all available.
- No ingestion, event eligibility, archetype identity, prediction windows or historical source snapshots were changed.
- Same-event-weekend tournaments are averaged to cohort level before the primary accuracy comparison.

## Comparison and metric

The experiment reuses the existing interpretable grid from `scripts/test_irl_weight_grid.py`:
- IRL starting weight: 70%, 75%, 80%, 85%, 90%, 95%.
- IRL floor: 30%, 40%, 45%, 50%, 55%, 60%.
- Decay: 0.5, 1.0, 1.5, 2.0 percentage points of IRL weight per day.

Primary metric is cohort-weighted **Field Accuracy** using the frozen named-archetype scoring policy: `100 × (1 − 0.5 × Σ|prediction − actual|)`.

Comparators: Online-only, IRL-only, 50/50, current v2.1 (70% start / 2pp-day / 30% floor), and the prior full-history grid winner (80% / 1pp-day / 55% floor).

## Generated results

### Recent-period in-sample fit

**Verified generated result:** best recent-year grid rule = **85% IRL start, 2.0pp/day decay, 30% IRL floor**, cohort-weighted accuracy **84.77%**.

Recent-period comparator accuracy:
- Online-only: 76.37%
- IRL-only: 82.20%
- 50/50: 84.11%
- current v2.1: 84.46%
- prior full-history grid winner 80/55/1pp: 84.58%
- recent in-sample winner 85/30/2pp: 84.77%

The top of the grid is shallow rather than decisive: several nearby faster-decay rules score within roughly 0.1 percentage points of the winner.

### Fixed chronological holdout

To avoid treating an in-sample winner as demonstrated improvement, the first six recent cohorts were used for tuning and the final five were untouched holdout cohorts.

Training selected **70% start / 1.5pp-day / 30% floor**.

Holdout cohort accuracy:
- selected recent-training rule: **83.99%**
- current v2.1: **83.77%**
- 50/50: 83.40%
- IRL-only: 83.08%
- prior full-history 80/55/1pp winner: **84.36%**

Only five independent holdout cohorts are available, so this is directional rather than decisive.

### Recent expanding walk-forward

Supplementary recent-only expanding walk-forward starts after five recent training cohorts and tests six later cohorts. The dynamically retuned grid and current v2.1 both score **84.46%**; 50/50 scores 84.10%, IRL-only 83.04%.

## What the evidence supports

**Verified:** recent-year in-sample fit favours a pattern of putting more weight on the latest IRL major immediately after it, then shifting relatively quickly toward Online evidence.

**Inferred:** this pattern is qualitatively compatible with the owner's hypothesis that a larger/more competitive Online ecosystem may make Online evidence become useful more quickly, but this experiment does not test participation or competitiveness as explanatory variables.

**Verified:** the recent in-sample winner improves only ~0.31 percentage points over current v2.1 on the same recent cohorts, and model selection is not stable across validation slices.

**Verified:** the previous full-history 80/55/1pp rule remains competitive and is best among the fixed comparators on the five-cohort recent holdout.

## What the evidence does not support

- Do not call 85/30/2pp a demonstrated out-of-sample winner.
- Do not infer that player growth or competitive intensity caused the change.
- Do not change the production PTCG Tools formula from this result.
- Do not infer transition-format behaviour; the blend experiment is settled-format only.

## Reproducibility

- Analysis: `scripts/analyse_last_year_weighting.py`
- Generated JSON: `data/processed/last-year-weighting/summary.json`
- Human-readable result: `results/last-year-weighting/README.md`
- Scoped workflow: `.github/workflows/run-last-year-weighting.yml`
- Workflow run: `34952131759` (successful)

## Exact next action / decision

**Owner decision required.** The strongest next analytical question would be whether the apparent recent preference for faster IRL-to-Online decay is stable when the recent period is expanded/rolled through time (for example, repeated trailing-12-month fits) and whether it is associated with measurable Online evidence volume/field concentration rather than calendar time alone.

No further experiment is authorised by this handoff. Do not merge without explicit owner authorisation.
