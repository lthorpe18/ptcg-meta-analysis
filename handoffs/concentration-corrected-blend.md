# Concentration-corrected IRL + Online blend handoff

Date: 15 September 2026
Repository: `lthorpe18/ptcg-meta-analysis`
Base research state: `historical-online-chunked` at `67310cbab568a2632cec96cedfce1b8118d25d3c`
Working branch: `research/concentration-corrected-blend`

## Explicit owner question

After the Online-spread diagnostic showed that Online play is structurally more diffuse than IRL, test whether correcting that dilution before IRL/Online blending can beat the previous historical field-share forecasts.

## Verified baseline

The unchanged historical grid reproduces the prior result on the same 34 settled tournaments / 25 independent cohorts:
- best full-sample raw IRL+Online grid: **84.01%** cohort-weighted Field Accuracy;
- expanding walk-forward raw tuned blend after 10 prior cohorts: **83.93%** across 15 later cohorts.

This matches the existing historical weighting research, so the comparison is apples-to-apples.

## Primary correction

Predeclared primary group: previous-IRL **top 10**.

For each target:
1. identify the previous IRL top-10 archetypes using only pre-target information;
2. preserve the relative Online shares among those top-10 decks and separately among the rest of the Online field;
3. shrink the top-10 group's total Online share toward its previous-IRL total by correction strengths 0%, 25%, 50%, 75%, 100%;
4. blend the corrected Online distribution with previous IRL using the same historical IRL-weight grid;
5. renormalise and score with the existing named-archetype Field Accuracy metric.

Strength 0% is exactly the raw Online baseline. No target outcome is used to construct its own correction.

## Verified results

### Full sample — descriptive/in-sample

- best raw grid: **84.01%**;
- best corrected grid: **84.34%**;
- difference: **+0.33pp**;
- best corrected fit used **75% concentration correction**.

Holding the old 80% start / -1pp/day / 55% floor weighting rule fixed isolates the correction:
- 0% correction: 84.01%;
- 25%: 84.17%;
- 50%: 84.26%;
- 75%: **84.28%**;
- 100%: 84.19%.

The peak at 50–75%, followed by deterioration at 100%, is consistent with the prior diagnostic: Online direction contains useful information, but its raw magnitude is too diffuse to read literally.

### Expanding walk-forward — primary validation

After at least 10 prior cohorts, each later cohort selected parameters from prior cohorts only:
- raw tuned blend: **83.93%**;
- concentration-corrected tuned blend: **84.31%**;
- improvement: **+0.386pp**;
- corrected model improved **11/15** tested cohorts and worsened 4/15.

This is the first tested field-share modification in this workstream to beat the previous tuned raw blend by a non-trivial amount in the existing expanding walk-forward replay.

### Frozen recent-era split

Parameters fitted only on cohorts before **2025-08-28**, then scored on the later 11 cohorts:
- raw blend: **84.11%**;
- corrected blend: **84.68%**;
- improvement: **+0.573pp**;
- training selected **75% correction**.

### Top-N sensitivity

At the old fixed 80/-1pp/55 rule, full-sample sensitivity was:
- top-5 correction: small/no benefit; best 25% = 84.07%;
- top-10 correction: best 75% = 84.28%;
- top-20 correction: best 75% = 84.41%.

Top-20 was not the predeclared primary correction and has not been promoted from this post-hoc in-sample sensitivity. Do not claim it is better without separate chronological validation.

## Interpretation

**Verified:** correcting the structural Online concentration/tail effect improves historical Field Accuracy under both expanding walk-forward replay and a frozen recent-era split, relative to the same raw IRL+Online framework.

**Inferred:** Online evidence is useful primarily for relative deck movement, while the raw Online concentration level systematically overstates how much share migrates into the long tail. A partial concentration correction preserves movement information while restoring some IRL-like field concentration.

**Unknown:** true future-event gain. The correction family itself was motivated by a full-archive diagnostic, so these chronological replays are stronger than in-sample fitting but are not equivalent to a genuinely unseen tournament after model conception.

## Reproducibility

- Script: `scripts/analyse_concentration_corrected_blend.py`
- Generated summary: `data/processed/concentration-corrected-blend/summary.json`
- Report: `results/concentration-corrected-blend/README.md`
- Workflow: `.github/workflows/run-concentration-corrected-blend.yml`
- Successful run: `34999219467`
- Generated output commit: `a6e29bd`

## Exact next action

Owner decision required. The evidence supports retaining **partial top-10 concentration correction** as a serious candidate for the final field-share model. Do not change the production `ptcg-tools` formula automatically. A sensible next research step is either:

1. freeze the top-10 correction rule and test it jointly with the already-demonstrated IRL performance signal / future Online-mediation model, or
2. perform one bounded robustness check of the concentration correction (for example, fixed 75% top-10 correction without re-tuning the IRL weight grid) before combining signals.

Do not chase the post-hoc top-20 in-sample winner without a separately declared validation experiment.
