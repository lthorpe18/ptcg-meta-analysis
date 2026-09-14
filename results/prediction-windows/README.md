# Baseline historical prediction windows

Generated from the tagged Online and IRL archives. These files define **what evidence is available** for each historical IRL target; they do not yet select or score a blend formula.

## Headline

- Targets/windows: **71**
- IRL overlap cohorts: **55**
- Multi-event contemporaneous cohorts: **14**
- Settled-format windows: **56**
- Transition/opening-format windows: **15**
- Primary targets (IRL capture >=95%): **68**
- Sensitivity targets (IRL capture >=98%): **66**
- Online primary-evidence classification threshold: **90%**
- Leakage audit errors: **0**

## Window rules

1. IRL events whose date ranges overlap are placed in one cohort. No event in the target cohort can be prior evidence for another event in that cohort.
2. The prediction cutoff is 00:00 UTC on the cohort's first start date because the IRL archive has dates, not exact start timestamps.
3. Clean Online evidence must be the **same legal format**, start before the cutoff, and have at least **90% deck classification**. Same-format events below 90% remain recorded as excluded evidence for sensitivity work.
4. Prior IRL evidence must have finished before the target cohort starts. Same-format and previous-format evidence are stored separately.
5. A window is `transition` when no earlier completed IRL major exists in the target format; otherwise it is `settled`.
6. Online tournament **start time is an availability proxy**. Exact completion/decklist-publication timestamps are not present in the historical archive, so this assumption is explicit and can be challenged later.

## Files

- `data/processed/prediction-windows/windows.json` — full auditable window membership
- `data/processed/prediction-windows/events.csv` — one-row-per-target review table
- `data/processed/prediction-windows/summary.json` — headline audit counts
