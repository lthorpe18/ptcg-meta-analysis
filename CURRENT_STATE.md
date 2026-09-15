# PTCG Meta Analysis — current state

Audit: 14 September 2026; documentation state re-verified 15 September 2026. **Read this before assuming main contains the analysis.**

## Purpose and boundary

**Verified:** `lthorpe18/ptcg-meta-analysis` is standalone historical Pokémon TCG field-share/prediction research. It reconstructs pre-major Online/IRL evidence and compares predictions with actual Masters Day-1 fields. Its website explains research and candidate forecasts. It is not the production Meta feature in [ptcg-tools](https://github.com/lthorpe18/ptcg-tools); no research result automatically changes that application's formula or roadmap.

## Two distinct baselines

| State | Verified reference | Meaning |
|---|---|---|
| Main research implementation baseline | [74cde68ad5f8d4663e36c269e81e8692140f1c18](https://github.com/lthorpe18/ptcg-meta-analysis/commit/74cde68ad5f8d4663e36c269e81e8692140f1c18) | Collector/chunk-runner foundation and compact 10–13 September smoke data. Documentation consolidation PR #6 adds only recovery/state documentation on top of this implementation baseline; it does not merge the completed research. |
| Active research | `historical-online-chunked` at [67310cbab568a2632cec96cedfce1b8118d25d3c](https://github.com/lthorpe18/ptcg-meta-analysis/commit/67310cbab568a2632cec96cedfce1b8118d25d3c) | Historical archive, audits, format tags, windows, models, experiments and website |
| Open research PR | [#5](https://github.com/lthorpe18/ptcg-meta-analysis/pull/5) | Still titled “Backfill historical Online data in resumable monthly chunks”; title/body understate its actual scope. It remains separate from documentation PR #6 and is not authorised for merge by the documentation review. |
| Documentation consolidation | [#6](https://github.com/lthorpe18/ptcg-meta-analysis/pull/6) | Recovery/state documentation only. Re-verified 15 September against current main and #5 research head before merge. |
| Deployed research site | [Website](https://lthorpe18.github.io/ptcg-meta-analysis/), [successful run 34871503993](https://github.com/lthorpe18/ptcg-meta-analysis/actions/runs/34871503993) | Workflow checked out the research branch, generated/committed `67310cb`, then deployed dashboard; not a deployment of main |

The 15 September re-check confirmed the implementation relationship recorded by the audit: pre-documentation main `74cde68` is 2 commits ahead of the research branch at their divergence, while `historical-online-chunked` is 161 commits ahead of main. Documentation PR #6 does not alter that analytical split.

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

**Verified latest research activity:** building the current archetype forecast, then converting deck shares to a mobile comparison table; last authored correction `ec73038`, deploy trigger `aa3e063`, generated output `67310cb`. Backfill itself is complete.

**Verified current operational action:** documentation consolidation only. PR #6 was re-checked on 15 September against current main and `historical-online-chunked`; its intended merge does not authorise merging research PR #5 or beginning a new experiment.

**Exact next research action after documentation consolidation:** none is authorised. Stop after the documentation merge. A future research session must first recover or obtain the owner's next explicit analytical question before changing models, collecting more data or extending the website.

**Unknown:** precise next analytical question after the mobile table, owner acceptance of the fitted rule, named upcoming target tournament, and intended merge timing for #5. Online recency/half-life and transition investigations remain supported research possibilities, not an authorised next experiment or app roadmap.

## Risks and authority

**Verified limitations:** Online start times proxy availability; classification snapshots were collected retrospectively; exact source IDs/slugs are joined without a proven cross-source taxonomy; named-only scoring excludes source Other/Unknown; single-event current forecast differs from historical cohort aggregation; stale legacy generators/workflows remain.

Operational authority: this file → [handoff](handoffs/historical-field-prediction.md) → pinned scripts/results. [Audit inventory](docs/FORENSIC_AUDIT_2026-09-14.md) records dispositions and branch/PR history. Update these documents after each substantial analytical or merge decision.

**Verified** = direct code/history/results/context evidence; **Inferred** = supported interpretation; **Unknown** = not reliably recoverable. Never fill an unknown from the PTCG Tools roadmap.
