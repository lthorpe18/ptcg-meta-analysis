# PTCG Meta Analysis — current state

Audit: 14 September 2026; documentation state re-verified and consolidated on main 15 September 2026. **Read this before assuming main contains the analysis.**

## Purpose and boundary

**Verified:** `lthorpe18/ptcg-meta-analysis` is standalone historical Pokémon TCG field-share/prediction research. It reconstructs pre-major Online/IRL evidence and compares predictions with actual Masters Day-1 fields. Its website explains research and candidate forecasts. It is not the production Meta feature in [ptcg-tools](https://github.com/lthorpe18/ptcg-tools); no research result automatically changes that application's formula or roadmap.

## Two distinct baselines

| State | Verified reference | Meaning |
|---|---|---|
| Main research implementation baseline | [74cde68ad5f8d4663e36c269e81e8692140f1c18](https://github.com/lthorpe18/ptcg-meta-analysis/commit/74cde68ad5f8d4663e36c269e81e8692140f1c18) | Collector/chunk-runner foundation and compact 10–13 September smoke data. Documentation consolidation does not merge the completed research. |
| Current main documentation state | [PR #6 merge `047d288`](https://github.com/lthorpe18/ptcg-meta-analysis/commit/047d288a420bff3efe75457a0c77bf8bcb0f4892) | Documentation-only consolidation merged 15 September 2026. No code, workflows, models, datasets or generated analysis outputs were included. |
| Active research | `historical-online-chunked` at [67310cbab568a2632cec96cedfce1b8118d25d3c](https://github.com/lthorpe18/ptcg-meta-analysis/commit/67310cbab568a2632cec96cedfce1b8118d25d3c) | Historical archive, audits, format tags, windows, models, experiments and website |
| Open research PR | [#5](https://github.com/lthorpe18/ptcg-meta-analysis/pull/5) | Still titled “Backfill historical Online data in resumable monthly chunks”; title/body understate its actual scope. It remains open and unmerged at `67310cb`. After #6 merged, GitHub reports it non-mergeable against current main; resolving that is a separate future task and is not authorised here. |
| Deployed research site | [Website](https://lthorpe18.github.io/ptcg-meta-analysis/), [successful run 34871503993](https://github.com/lthorpe18/ptcg-meta-analysis/actions/runs/34871503993) | Workflow checked out the research branch, generated/committed `67310cb`, then deployed dashboard; not a deployment of main |

The 15 September pre-merge re-check confirmed the implementation relationship recorded by the audit: pre-documentation main `74cde68` was 2 commits ahead of the research branch at their divergence, while `historical-online-chunked` was 161 commits ahead of main. PR #6 changed documentation only and therefore did not alter that analytical split.

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

**Verified operational state:** documentation PR #6 merged to main at `047d288` on 15 September after confirming its five changed files were Markdown documentation only. Research PR #5 was not merged and no new analysis was started.

**Exact next research action:** none is authorised. A future research session must first recover or obtain the owner's next explicit analytical question before changing models, collecting more data, resolving #5 for merge, or extending the website.

**Unknown:** precise next analytical question after the mobile table, owner acceptance of the fitted rule, named upcoming target tournament, and intended merge timing/strategy for #5. Online recency/half-life and transition investigations remain supported research possibilities, not an authorised next experiment or app roadmap.

## Risks and authority

**Verified limitations:** Online start times proxy availability; classification snapshots were collected retrospectively; exact source IDs/slugs are joined without a proven cross-source taxonomy; named-only scoring excludes source Other/Unknown; single-event current forecast differs from historical cohort aggregation; stale legacy generators/workflows remain.

Operational authority: this file → [handoff](handoffs/historical-field-prediction.md) → pinned scripts/results. [Audit inventory](docs/FORENSIC_AUDIT_2026-09-14.md) records dispositions and branch/PR history. Update these documents after each substantial analytical or merge decision.

**Verified** = direct code/history/results/context evidence; **Inferred** = supported interpretation; **Unknown** = not reliably recoverable. Never fill an unknown from the PTCG Tools roadmap.
