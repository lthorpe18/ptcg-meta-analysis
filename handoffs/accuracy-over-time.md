# Accuracy-over-time research handoff

Date: 15 September 2026  
Repository: `lthorpe18/ptcg-meta-analysis`  
Branch: `research/accuracy-over-time`  
Base research commit: `67310cbab568a2632cec96cedfce1b8118d25d3c` (`historical-online-chunked` / PR #5)

## Current question

**Verified owner decision:** investigate whether historical field-share prediction accuracy changes over chronological time.

## Experiment definition

- **Evidence window:** primary targets from 13 September 2024 through 28 August 2026.
- **Eligibility:** existing >=95% IRL field-capture threshold; target IDs `0004`, `0008`, `0051` excluded consistently with the existing scorer/audit.
- **Unit:** correlated tournament cohort, using mean Field Accuracy within each cohort so multi-major weekends are not overweighted.
- **Metric:** existing Field Accuracy = `100% - 0.5 * sum(abs(predicted share - actual share))`.
- **Comparison:** Online-only over all primary windows and separately settled/transition windows; IRL-only settled; 50/50 and current v2.1 complete-case settled samples.
- **Validation:** no model retuning. Primary trend is a linear slope in accuracy percentage points per calendar year. Significance is checked by a deterministic two-sided 20,000-shuffle permutation test.

## Generated outputs

- `scripts/analyse_accuracy_over_time.py`
- `results/accuracy-over-time/summary.json`
- `results/accuracy-over-time/cohort-accuracy.csv`
- `results/accuracy-over-time/README.md`

## Results

**Verified generated diagnostic:**

- Online-only, all primary windows: **+1.98 pp/year**, 53 cohorts, permutation p = **0.093**.
- Online-only, settled primary windows: **+3.84 pp/year**, 40 cohorts, permutation p = **0.002**.
- Online-only, transition primary windows: **-2.28 pp/year**, 13 cohorts, permutation p = **0.396**.
- IRL-only, settled primary windows: **+0.94 pp/year**, 40 cohorts, permutation p = **0.505**.
- 50/50 complete-case settled: **+0.75 pp/year**, 25 cohorts, permutation p = **0.609**.
- Current v2.1 complete-case settled: **+1.06 pp/year**, 25 cohorts, permutation p = **0.502**.

The descriptive chronological half split for settled Online-only is **69.42% early vs 74.55% late**. This split is descriptive only; the slope/permutation test is the primary diagnostic.

## Interpretation and limitations

**Supported:** settled-format Online-only prediction accuracy increased over this historical sample strongly enough to justify investigation of the cause.

**Not supported:** a general improvement across all prediction methods. Current v2.1, 50/50 and IRL-only do not show a clear monotonic trend. This analysis does not establish that Online evidence itself became intrinsically more predictive.

**Confounders / unknowns:** calendar time is entangled with format/rotation era, tournament ecosystem, event mix, field concentration and retrospective data conditions. Transition windows behave differently and include only 13 cohorts.

No production-app change follows from this result. PR #5 remains unmerged. No ingestion was rerun.

## Exact next action

Owner decision required before the next experiment. The natural follow-up is to test whether the settled Online-only trend remains after accounting for **format/rotation era and target-field concentration**. Do not start that follow-up or merge this work without explicit owner instruction.
