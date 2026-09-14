# Research website — recovery entry

> **SUPERSEDED — the old “Backtest Explorer, before model fitting” description is retained in [history](https://github.com/lthorpe18/ptcg-meta-analysis/blob/67310cbab568a2632cec96cedfce1b8118d25d3c/dashboard/README.md).** Current project state is maintained in [CURRENT_STATE.md](../CURRENT_STATE.md).

At the 14 September 2026 audit, website implementation and generated HTML are on **`historical-online-chunked`**, open [PR #5](https://github.com/lthorpe18/ptcg-meta-analysis/pull/5), head `67310cbab568a2632cec96cedfce1b8118d25d3c`. This documentation on main does not imply its code/data have merged.

[Deployed research website](https://lthorpe18.github.io/ptcg-meta-analysis/) explains historical field-share evidence, model performance, method and an exploratory current archetype-share comparison. It is not the PTCG Tools product Meta interface.

**Verified current generation path:** `build_prediction_windows.py` → `score_baseline_models.py` → `test_irl_weight_grid.py` → `test_top20_sensitivity.py` → `build_current_archetype_prediction.py` → `build_research_site.py` → `add_archetype_page.py`. These are research-branch scripts, not files guaranteed to exist on main.

The current workflow builds, runs text smoke checks, commits generated outputs and deploys the dashboard. See [successful build/deploy 34871503993](https://github.com/lthorpe18/ptcg-meta-analysis/actions/runs/34871503993). Earlier explorer/polish generators and a second Pages workflow remain; review them before a future pipeline change rather than rerunning the original backfill.

Read the [active handoff](../handoffs/historical-field-prediction.md) for dataset boundaries, named-archetype scoring, current forecast date/weights and the walk-forward limitation. Generated pages should not be hand-edited to change model conclusions.
