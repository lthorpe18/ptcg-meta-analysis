# Historical field prediction and research website

Audit: 14 September 2026; documentation state re-verified 15 September 2026. Repository: `lthorpe18/ptcg-meta-analysis`. Substantial research workstream: historical evidence → model comparison → current field-share illustration.

## Recovery instructions and scope

Read [CURRENT_STATE](../CURRENT_STATE.md), then inspect [PR #5](https://github.com/lthorpe18/ptcg-meta-analysis/pull/5) / `historical-online-chunked` at `67310cbab568a2632cec96cedfce1b8118d25d3c`. The main **research implementation** baseline before documentation consolidation is `74cde68ad5f8d4663e36c269e81e8692140f1c18`; documentation PR #6 adds recovery/state documentation only and does not bring #5's analysis/data onto main. All source/result links below are pinned to the audited research commit because these files mostly do **not** exist in main's research implementation.

**Verified 15 September state:** main's pre-documentation implementation remains `74cde68`; research PR #5 remains open at `67310cb`; the branches remain diverged by 2 main-only and 161 research-only commits. PR #6 was reviewed only to consolidate documentation. Its merge does **not** authorise merging #5 or starting new analysis.

**Verified original objective:** reconstruct information available before historical IRL majors, compare candidate field predictions with actual Day-1 shares, investigate interpretable weights and chronological validation. No production app formula is changed here. **Verified implemented scope** is substantially beyond the still-open “backfill” PR description.

## Datasets and ingestion

| Layer | Verified assembled evidence | Source / method |
|---|---|---|
| Online | 25 completed chunks; 2024-09-01–2026-09-13; 6,327 discovered Standard rows; 2,605 candidate snapshots; 1,444 usable events; 186,224 entries, 179,872 classified | [fetch_online.py](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/scripts/fetch_online.py), [chunk runner](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/scripts/backfill_online_chunked.py), public `play.limitlesstcg.com/api`; PTCG Standard, PTCGL, Online, >=50 players, available standings/deck evidence, no custom bans/special rules |
| IRL | 71 Masters majors, 2024-09-13–2026-08-30; 50 Regionals, 13 Specials, 6 Internationals, 2 Worlds; 112,228 captured entries / 112,609 reported | [fetch_irl_labs.py](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/scripts/fetch_irl_labs.py), public Limitless Labs pages; Masters, Day 1, variant grouping off |
| Formats | 1,444 Online and 71 IRL events tagged; zero unmatched | [historical calendar](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/data/reference/legality-calendar.json), [tagger](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/scripts/tag_historical_formats.py); separate Online timestamps / IRL dates, documented rotation/release sources and derived legality assumptions |

The 13 recorded labels are BRS–SFA/SCR/SSP/PRE, SVI–JTG/DRI/BLK-WHT/MEG/PFL/ASC, TEF–POR/CRI/PBL (the actual combined-set label is `SVI-BLK/WHT`). See [exact format counts](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/data/processed/format-tags/README.md).

Online compact standings retain classification, country, record, placing/drop evidence; omit full decklists and player handles. Raw snapshot classifications must not be edited to improve scores. The archive is a research dataset, not an app cache. Source “raw” IRL JSON contains parsed field evidence rather than a full original HTML archive.

Audits: [Online](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/results/online-audit/README.md), [IRL](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/results/irl-audit/README.md). Online: 96.59% total classification, 26 usable events below 90%, one reported-player/standings mismatch, zero duplicate IDs. IRL: 99.66% overall capture; 68 targets >=95%, 66 >=98%; three targets below 95%; zero duplicates/source failures. Completeness is against captured Labs index, not an independent official event census.

## Archetypes, shares and performance boundaries

**Verified code policy:** Online `deck.id` and IRL `slug` are exact keys, with lowercase-name fallback; variants are not collapsed. There is no recovered curated cross-source equivalence map. **Unknown:** whether every historical ID/slug pair represents the same exact archetype and whether source reclassification occurred before collection.

[Scorer](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/scripts/score_baseline_models.py) aggregates player/deck-entry counts, removes source Other/Unknown/unclassified, then normalises each named distribution to 100%. This denominator is not all reported participants. Source omitted mass remains in audit data.

Field Accuracy = `100 × (1 − 0.5 × Σ|p−a|)` for fractional shares over the union of named keys. MAE uses that union; per-target largest misses and prediction rows are retained. The top-20 sensitivity collapses remaining **named** mass into Other; it does not restore the source unknown mass already removed.

**Verified:** descriptive field concentration and prediction performance are analysed. No pairwise matchup/H2H modelling pipeline or win-rate-based predictor was found in the inspected scripts/results. Stored Online records and IRL performance fields are not evidence that such an analysis was performed. PTCG Tools' matchup features do not fill this gap.

## Historical windows and models

[Windows](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/results/prediction-windows/README.md): 71 targets / 55 overlapping-date cohorts (14 multi-event cohorts), 56 settled and 15 transition windows. Cutoff is 00:00 UTC at cohort start. Prior IRL must finish before the cohort; same-cohort events cannot predict one another. Online must start before cutoff, match legal format and reach 90% classification.

**Assumption:** Online start time proxies completion/publication; zero recorded leakage errors only proves the implemented membership rules, not real-world availability. Retrospective classification snapshots cannot establish what taxonomy was publicly known on the historical date.

[Baselines](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/results/model-results/README.md):
- Online-only: all qualifying same-format Online evidence before cutoff.
- IRL-only: latest completed same-format overlap cohort, weighted by field entries.
- 50/50 and `current_v2_1`: latest IRL cohort plus Online after that cohort's final ISO-week Sunday.
- `current_v2_1` settled benchmark: IRL max 70%, decay 2 percentage points/day, floor 30%; remainder Online.
- Transition targets: clean Online-only; no prior-format IRL carry-forward. This is a research benchmark, not a verified full reproduction of every production transition branch.

Primary targets = 68 (53 settled, 15 transition). Like-for-like four-model comparison = 34 settled events across 25 cohorts. Cohort-mean accuracy: Online 72.78%, IRL 82.63%, 50/50 83.16%, current decay 83.30%. Equal cohorts prevent multi-major weekends from receiving extra weight. Model input windows differ intentionally; equal targets do not mean identical Online windows.

[Weight grid](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/results/weight-grid/README.md): starts 70–95%, floors 30–60%, decay 0.5–2pp/day. Best full-sample rule = 80% start, 1pp/day, 55% floor, 84.01%. Expanding walk-forward selects only on prior cohorts after ten training cohorts; 15 later cohorts: tuned 83.93%, 50/50 83.84%, IRL 82.20%, current decay 84.13%. **Verified results; inferred conclusion:** do not promote the grid winner as demonstrated predictive improvement.

[Top-20 sensitivity](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/results/top20-sensitivity/README.md): fixed prior grid winner, not retuned; 34 events / 25 cohorts. Online 74.50%, IRL 85.99%, blend 86.48%. Actual-field top-20 selection is an evaluation lens, not knowledge available before the event.

## Latest work: current shares and website

**Verified:** `e7662cc` builds [current forecast](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/scripts/build_current_archetype_prediction.py); `1f3c827` adds archetype page; `c077385` makes comparison table; `59c47fc` makes it mobile-first; `ec73038` adjusts smoke test; `aa3e063` triggers deploy; `67310cb` refreshes generated output.

[Current snapshot](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/data/processed/current-archetype-prediction.json): forecast 2026-09-14, Online through 2026-09-13, TEF–PBL, latest IRL event 0071 “World Championship San Francisco” (28–30 August), 42 Online events, 65% IRL / 35% Online. Uses the best **in-sample** rule; explicitly exploratory. Selection of displayed archetypes does not renormalise their shares.

Current forecast chooses the latest single IRL event by end/start/id, takes its format and dates forecast as last Online evidence + one day. It does not select a named upcoming event or aggregate a latest multi-event cohort, and does not resolve a future legal format. **Inferred debt:** these differences matter before generalising this illustration to an ongoing forecasting service.

[Website](https://lthorpe18.github.io/ptcg-meta-analysis/): research summary, evidence, method, legacy model comparison and archetype share table. Current generators are [build_research_site.py](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/scripts/build_research_site.py) then [add_archetype_page.py](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/scripts/add_archetype_page.py). This replaced the old explorer presentation; generated pages are not authoritative modelling logic.

## Validation and operating hazards

**Verified:** [run 34871503993](https://github.com/lthorpe18/ptcg-meta-analysis/actions/runs/34871503993), trigger `aa3e063`, passed windows, baseline scoring, weighting, top-20 sensitivity, forecast, site generation, text smoke tests, output commit and Pages deployment. The job committed `67310cb` before uploading. This is build/analysis execution evidence, not independent statistical validation or owner visual acceptance.

No conventional unit-test suite was found; `test_irl_weight_grid.py` and `test_top20_sensitivity.py` are analysis programs. The three notebooks have only Markdown scaffold cells and no executed outputs. Latest failed table builds were followed by successful smoke-test corrections/deployments.

Hazards to review before a later code change:
- Two Pages workflows and different concurrency groups can deploy; legacy full-backfill workflow still calls `build_dashboard.py` and can overwrite the newer index if run.
- Main-only overnight backfill workflow is date-guarded to 13–14 September; research branch retires its own old PR trigger in `37b65a1`. Main and branch must be reconciled deliberately.
- Generated README/results should not be hand-edited to invent conclusions; their generators overwrite them.
- Calendar is bounded to this historical period. Do not treat it as the app's maintained current calendar.
- No independent confidence intervals, taxonomy audit or full publication-time reconstruction was recovered.

## Exact next step / unresolved decisions

**Verified current instruction:** complete documentation consolidation PR #6 only. Do not merge research PR #5 and do not start a new analytical experiment in this session.

**Exact next research action after #6:** none is authorised. On the next research session, recover or obtain the owner's explicit next analytical question before modifying models, data collection or presentation. Review of #5's accumulated scope and deployment path may be needed operationally, but it is not itself an authorised research experiment or merge decision.

**Unknown:** exact next user-requested analytical question after the table; acceptance of the exploratory current formula; next named forecast tournament; whether the next experiment should be recency, transition rules, taxonomy/availability sensitivity or something else; and whether/how #5 should eventually merge. The scaffold supports later Online recency/half-life and chronological validation, but does not establish that these are the final agreed next task.

This handoff is reconstructed from code, commits and generated outputs (**Verified**); risk interpretation is **Inferred**. No missing intent has been filled from the main product roadmap.
