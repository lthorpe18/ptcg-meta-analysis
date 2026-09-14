# PTCG Meta Analysis — current state

Audit: 14 September 2026. **Read this before assuming main contains the analysis.**

## Purpose and boundary

**Verified:** `lthorpe18/ptcg-meta-analysis` is standalone historical Pokémon TCG field-share/prediction research. It reconstructs pre-major Online/IRL evidence and compares predictions with actual Masters Day-1 fields. Its website explains research and candidate forecasts. It is not the production Meta feature in [ptcg-tools](https://github.com/lthorpe18/ptcg-tools); no research result automatically changes that application's formula or roadmap.

## Two distinct baselines

| State | Verified reference | Meaning |
|---|---|---|
| Default branch | `main` at [74cde68ad5f8d4663e36c269e81e8692140f1c18](https://github.com/lthorpe18/ptcg-meta-analysis/commit/74cde68ad5f8d4663e36c269e81e8692140f1c18) | Collector/chunk-runner foundation and compact 10–13 September smoke data; not the completed research |
| Active research | `historical-online-chunked` at [67310cbab568a2632cec96cedfce1b8118d25d3c](https://github.com/lthorpe18/ptcg-meta-analysis/commit/67310cbab568a2632cec96cedfce1b8118d25d3c) | Historical archive, audits, format tags, windows, models, experiments and website |
| Open implementation PR | [#5](https://github.com/lthorpe18/ptcg-meta-analysis/pull/5) | Still titled “Backfill historical Online data in resumable monthly chunks”; title/body understate its actual scope |
| Deployed research site | [Website](https://lthorpe18.github.io/ptcg-meta-analysis/), [successful run 34871503993](https://github.com/lthorpe18/ptcg-meta-analysis/actions/runs/34871503993) | Workflow checked out the research branch, generated/committed `67310cb`, then deployed dashboard; not a deployment of main |

At audit, main has 2 commits absent from the research branch; the research branch has 161 absent from main. Neither default-branch HEAD nor the PR's old description describes the deployed research. This documentation branch adds no analysis/data to main.

## Work demonstrably completed on the research branch

**Verified from scripts, committed outputs and CI:**

- 25 monthly Online chunks, 2024-09-01 through 2026-09-13; 6,327 discovered Standard events, 1,444 usable tournaments, 186,224 stored player entries; 96.59% classified.
- 71 IRL Masters majors, 2024-09-13 through 2026-08-30; 112,228 captured Day-1 entries / 112,609 reported players.
- 13 historical formats; 71 prediction windows, 55 overlap cohorts, zero recorded window-membership leakage errors.
- Four baseline models; fair settled comparison = 34 tournaments / 25 cohorts. IRL weighting grid, expanding walk-forward and top-20 sensitivity executed.
- Research site and mobile archetype-share comparison. Forecast dated 2026-09-14: TEF–PBL, Worlds anchor, 42 subsequent Online events, 65% IRL / 35% Online using an exploratory 80%-start / 1pp-per-day / 55%-floor rule.
- Best full-sample grid accuracy 84.01%; walk-forward tuned result 83.93% versus existing decay benchmark 84.13%. **This does not establish an out-of-sample improvement.**

See [research handoff](handoffs/historical-field-prediction.md) for sources, scoring semantics, limitations and exact files. Notebook filenames are scaffolds, not executed analyses.

## Current active work and exact next action

**Verified latest activity:** building the current archetype forecast, then converting deck shares to a mobile comparison table; last authored correction `ec73038`, deploy trigger `aa3e063`, generated output `67310cb`. Backfill itself is complete.

**Next recommended action:** inspect #5 at the recorded head, review the current forecast/table and the evidence/limitations in the handoff, and establish the next research question with the owner before changing models or collecting more data. Decide separately whether/how the broad #5 should become main and which workflow should own site generation. Do not rerun the completed backfill as the assumed next task.

**Unknown:** precise next analytical question after the mobile table, owner acceptance of the fitted rule, named upcoming target tournament, and intended merge timing. Online recency/half-life and transition investigations remain supported research possibilities, not an authorised next experiment or app roadmap.

## Risks and authority

**Verified limitations:** Online start times proxy availability; classification snapshots were collected retrospectively; exact source IDs/slugs are joined without a proven cross-source taxonomy; named-only scoring excludes source Other/Unknown; single-event current forecast differs from historical cohort aggregation; stale legacy generators/workflows remain.

Operational authority: this file → [handoff](handoffs/historical-field-prediction.md) → pinned scripts/results. [Audit inventory](docs/FORENSIC_AUDIT_2026-09-14.md) records dispositions and branch/PR history. Update these documents after each substantial analytical or merge decision.

**Verified** = direct code/history/results/context evidence; **Inferred** = supported interpretation; **Unknown** = not reliably recoverable. Never fill an unknown from the PTCG Tools roadmap.
