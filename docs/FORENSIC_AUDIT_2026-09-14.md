# PTCG Meta Analysis forensic audit — 14 September 2026

## Identity and audited refs

**Verified:** connected-account repository list and original README independently identify `lthorpe18/ptcg-meta-analysis` as standalone historical prediction research. It explicitly distinguishes the production `ptcg-tools` app. Personal-context retrieval did not recover a more precise final analytical question; it supplied only excluded main-app recovery material.

Audited main: `74cde68ad5f8d4663e36c269e81e8692140f1c18`. Audited research branch: `historical-online-chunked`, `67310cbab568a2632cec96cedfce1b8118d25d3c`. All 5 PRs, 11 branches, full research-branch commit sequence, current scripts/results/calendar/notebooks/workflows and documentation were inspected. No source code, models, pipelines or data changed.

**Verified** = direct evidence; **Inferred** = supported interpretation; **Unknown** = unrecovered. The main/branch split is the central recovery risk, not a reason to assume work was unfinished because main lacks it.

## Implementation chronology

| Evidence | Verified event / consequence |
|---|---|
| `453dc14`–`9159e47` | Standalone collector, data layout and three notebook scaffolds established |
| [#1](https://github.com/lthorpe18/ptcg-meta-analysis/pull/1) | Initial smoke test closed unmerged; storage-heavy approach abandoned |
| [#2](https://github.com/lthorpe18/ptcg-meta-analysis/pull/2), merge `56c5826` | Optimised 10–13 Sep smoke archive merged; 49 discovered / 14 first-pass eligible |
| [#3](https://github.com/lthorpe18/ptcg-meta-analysis/pull/3), merge `3f56ce4` | Compact standings merged; remove full decklists/handles from current snapshots |
| [#4](https://github.com/lthorpe18/ptcg-meta-analysis/pull/4) | Monolithic full backfill cancelled and closed unmerged; explicitly superseded by chunked approach |
| `a21ad4a`, `62c7688` | Chunk runner/workflow on main |
| `dc0ca2c`, `74cde68` | Main-only overnight resumable workflow and guard |
| [#5](https://github.com/lthorpe18/ptcg-meta-analysis/pull/5), `6833061`–`ce444de` | Discovery checkpoint and all 25 monthly chunks accumulated on research branch |
| `59fe196`, `c533097`, `90bcdf9` | Online audit, IRL collector, IRL audit |
| `0a32190`, `ace1bf6` | Historical calendar and format tagging |
| `d2db6cd`–`59f59d4` | Original interactive explorer built/refined/deployed |
| `97e6b25`, `33991ba`, `baeb4fc`, `b985f04` | Prediction windows, scoring and fair complete-case summaries |
| `017d360`, `8e5ab74`, `750ddc5` | Weight explanation, alternative-curve sweep/walk-forward, top-20 sensitivity |
| `bbada0d`, `e7662cc`, `1f3c827` | Research website rebuilt; current share forecast/page added |
| `c077385`, `59c47fc`, `ec73038` | Table comparison and mobile refinements; smoke-test correction |
| `aa3e063` → `67310cb` | Successful generation/deployment of current research site |

#5's unchanged backfill title/body are demonstrably stale: scope now spans dataset, analysis and presentation. Existing PR description is **recommended for update during its implementation review**, not modified by this docs-only PR. No recovered comments on #5 supplied additional intent.

## Actual state, validation and next action

See [CURRENT_STATE](../CURRENT_STATE.md) and [full handoff](../handoffs/historical-field-prediction.md) for exact counts, formulas, source methods, limitations and next action.

**Verified:** completed archive/audits, 13 tagged formats, 71 prediction windows, four baselines, IRL grid, walk-forward, top-20 sensitivity and current share table exist on #5. Current pipeline success is [34871503993](https://github.com/lthorpe18/ptcg-meta-analysis/actions/runs/34871503993). Trigger SHA `aa3e063` is not the final generated commit: job logs record `67310cb` before deployment. Site URL is [ptcg-meta-analysis Pages](https://lthorpe18.github.io/ptcg-meta-analysis/). This documents deployment history, not fresh browser/device acceptance.

**Verified:** main contains the compact smoke archive and collection foundation only. Git comparison gives 2 main-only commits and 161 research-only commits. Research PR #5 is open. All substantial research is recoverable from its branch, not hypothetical planned work.

**Verified:** best in-sample weighting is 84.01%, but walk-forward tuned 83.93% trails current decay 84.13%. Current forecast is an exploratory presentation of in-sample-selected weights. Historical model scores do not validate replacing the product rule.

**Inferred next action:** review the latest table/current snapshot and #5 scope; settle the next analytical question and branch/deployment plan before more experiments. **Unknown:** owner's exact next research request, acceptance of the selected weights/table, future named target tournament, and whether to merge the broad implementation PR.

## Documentation inventory

Inventory includes both audited main and branch-only documents. “Generated evidence” remains an output with generator provenance, not an operational roadmap.

| Document | Audited location | Problem / disposition |
|---|---|---|
| `README.md` | Both refs; branch adds old explorer paragraph | Initial “data audit only” / analysis sequence reads as current despite completed work. Update main entry to CURRENT_STATE; preserve original scoped collection instructions as historical. Eventual #5 merge must retain the new entry. |
| `dashboard/README.md` | Research branch only at audit | Says self-contained explorer and “before model fitting”; stale after `bbada0d` and archetype page. Add current documentation on main with explicit branch links, mark old explorer description superseded. Resolve possible add/add at later #5 merge. |
| [format-tags README](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/data/processed/format-tags/README.md) | Research branch; generated | Retain as generated evidence: actual tags/counts/eligibility. No manual rewrite. |
| [Online audit README](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/results/online-audit/README.md) | Research branch; generated | Retain snapshot. “No threshold yet” is audit-stage context; later window builder selects 90%. CURRENT_STATE/handoff explain temporal scope. Updating its generator is a separate code change if desired. |
| [IRL audit README](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/results/irl-audit/README.md) | Research branch; generated | Retain source completeness / candidate >=95/98 thresholds; later pipeline implements primary >=95. |
| [prediction-windows README](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/results/prediction-windows/README.md) | Research branch; generated | Retain layer-specific evidence. “Do not yet select or score” describes this output, not the repository's latest phase. |
| [model-results README](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/results/model-results/README.md) | Research branch; generated | Retain current scoring/sample semantics; point readers here from handoff. |
| [weight-grid README](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/results/weight-grid/README.md) | Research branch; generated | Retain in-sample vs walk-forward contrast; it does not approve a production rule. |
| [top20-sensitivity README](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/results/top20-sensitivity/README.md) | Research branch; generated | Retain named-field sensitivity; source unknowns were already excluded upstream. |
| `notebooks/01_data_audit.ipynb` | Both | Markdown-only scaffold, no execution. Leave untouched for history; actual analysis lives in scripts/results. |
| `notebooks/02_baselines.ipynb` | Both | Markdown-only scaffold. Leave untouched; do not infer missing baseline work from empty notebook. |
| `notebooks/03_weight_fitting.ipynb` | Both | Markdown-only scaffold. Leave untouched; grid/walk-forward executed elsewhere. Later recency ideas remain possibilities. |
| New `CURRENT_STATE.md` | Docs branch based on main | Operational authority, explicit main/research/deployed split |
| New `handoffs/historical-field-prediction.md` | Docs branch based on main | One substantial active-work handoff; avoids needless separate handoffs for completed ingestion stages |
| This audit | Docs branch based on main | Evidence, dispositions, history and unknowns |

No existing architecture/roadmap/handoff Markdown other than the above was found. Root README and dashboard README duplicate obsolete initial-explorer positioning; both receive clear entry/status notices. No documents are deleted or moved. Existing explicit references to PTCG Tools are legitimate research-benchmark / independence statements, not evidence of a shared roadmap.

## Experimental, generated and potentially abandoned files

| Material | Evidence / disposition |
|---|---|
| `data/raw/online/backfill/`, `data/raw/irl/labs/` | Verified frozen research evidence; preserve. Avoid conflating smoke and full-archive trees. |
| `data/processed/`, `results/` outputs | Verified reproducible derived tables/reports; preserve. Generated timestamps are not evidence of fresh source collection. |
| `dashboard/*.html` | Verified generated site; preserve. Edit generators in later implementation work, not this consolidation. |
| `build_research_site.py`, `add_archetype_page.py` | Verified active site generators in current successful workflow |
| `build_dashboard.py` | Verified old explorer generator still called by legacy full-backfill workflow; unsafe to label dead code. It can overwrite newer index output. |
| `build_model_comparison.py`, `enhance_model_weight_analysis.py`, `polish_model_dashboard.py` | Inferred superseded presentation utilities from history/current build path; retain for review, no deletion |
| `dashboard/models.html` | Retained earlier generated model page still packaged by workflow; review its navigation/presentation relevance before cleanup |
| `.analysis-dashboard-trigger`, `dashboard/.pages-trigger` | Deployment trigger markers; do not treat as research conclusions |
| Main overnight workflow | Verified main-only, date-limited 13–14 September; reconcile with completed-backfill branch, not blindly cherry-pick |
| Branch full-backfill workflow | Verified legacy path remains; trigger retirement does not remove its implementation. Future manual runs can invoke old generators. |
| Dual Pages workflows | Verified distinct concurrency groups / source paths; inferred overwrite/race risk. Choose one owner during a future code review. |

## Known research limitations, not invented product debt

- **Verified assumptions:** historical availability uses Online start-time proxy; raw classifications collected retrospectively; exact-key taxonomy without curated crosswalk; named-only denominator; date-based cohort cutoffs; historical calendar exceptions/derived dates.
- **Verified unresolved methodological coverage:** narrow settled complete-case sample; only two Worlds; no recovered full tuning of Online recency/half-life; no independent statistical significance study; no production transition parity proof.
- **Verified current-forecast difference:** latest one IRL event rather than cohort, latest-IRL format rather than future-target resolver, forecast date derived from last Online evidence.
- **Unknown:** whether retrospective source taxonomy changed relative to event-time labels or all keyed variants match across sources.
- **Unknown:** final user intent after latest mobile table. Do not copy Personal Matchup Analysis, Practice Priorities, Collection or calendar-consumer tasks from the main app.

## Branch inventory

| Branch | Tip | Classification |
|---|---|---|
| `compact-smoke-sample` | `6aa1daafe964` | Verified merged #3 |
| `full-online-backfill` | `eace22c520d4` | Inferred abandoned/temporary backfill trigger; same eace22c tip, no active PR recovered |
| `full-online-backfill-2` | `eace22c520d4` | Inferred abandoned/temporary backfill trigger; same eace22c tip, no active PR recovered |
| `historical-online-chunked` | `67310cbab568` | Verified open #5; active research and site |
| `historical-online-data` | `05c8054e630f` | Verified closed unmerged #4 |
| `main` | `74cde68ad5f8` | Verified default; smoke-data foundation |
| `smoke-online-bootstrap` | `80fa086c9119` | Verified closed unmerged #1 |
| `smoke-online-v02` | `d6945c23403c` | Verified merged #2 |
| `tmp-full-trigger` | `eace22c520d4` | Inferred abandoned/temporary backfill trigger; same eace22c tip, no active PR recovered |
| `tmp-full-trigger-2` | `eace22c520d4` | Inferred abandoned/temporary backfill trigger; same eace22c tip, no active PR recovered |
| `tmp-full-trigger-3` | `eace22c520d4` | Inferred abandoned/temporary backfill trigger; same eace22c tip, no active PR recovered |

## Documentation-only integration notes

This PR targets main to make fresh-chat discovery reliable. It does not merge #5, alter its description, rerun workflows or publish a site. The new dashboard README is documentation only and links pinned branch outputs. A future #5 merge may conflict in README/dashboard README; retain CURRENT_STATE and these recovery links while integrating the analytical work. After that decision, update baseline and live-source references explicitly.
