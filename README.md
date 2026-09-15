# PTCG Meta Analysis

> **Start here:** [CURRENT_STATE.md](CURRENT_STATE.md) distinguishes the default branch from the active/deployed research branch. Read the [research handoff](handoffs/historical-field-prediction.md) before continuing.
>
> **SUPERSEDED as current status — retained for historical reference.** The initial data-audit-only description and prospective analysis sequence below describe the bootstrap stage. Historical ingestion, baselines, weighting experiments, walk-forward analysis and a research website now exist on open [PR #5](https://github.com/lthorpe18/ptcg-meta-analysis/pull/5), branch `historical-online-chunked`, audited at `67310cbab568a2632cec96cedfce1b8118d25d3c`. Main has not merged that work.
>
> The repository remains independent of the production PTCG Tools application. See the [documentation/evidence inventory](docs/FORENSIC_AUDIT_2026-09-14.md) for provenance and unresolved questions.

## Original bootstrap documentation

Standalone research workspace for testing Pokémon TCG metagame prediction methods independently of the production **PTCG Tools** application.

## Research objective

Reconstruct what information was available immediately before historical IRL majors, build candidate field predictions from prior IRL + Online evidence, and score those predictions against the actual Day 1 field.

The first phase is deliberately **data audit only**. No live PTCG Tools formula is changed from this repository.

## Phase 1 — Online historical data

The collector uses the public Limitless Tournament API and creates an auditable tournament-level source snapshot.

Initial eligibility rules:

- Game: Pokémon TCG (`PTCG`)
- Format: Standard
- Online event
- Platform: Pokémon TCG Live / PTCGL
- At least 50 players by default
- Decklists/standings available
- Exclude events with custom banned cards or special rules
- Preserve the source deck classification used at collection time

These rules are intentionally conservative and auditable. Later analysis can test thresholds such as event size, classification coverage, recency, organiser effects, etc.

## Repository layout

```text
data/
  raw/
    online/       # Limitless source snapshots and audit index
  processed/      # later cleaned analysis tables
scripts/
  fetch_online.py # historical Online collector
notebooks/
  01_data_audit.ipynb
  02_baselines.ipynb
  03_weight_fitting.ipynb
results/
.github/workflows/
  fetch-online.yml
```

## Run locally

Python 3.11+ is sufficient; the collector uses only the standard library.

```bash
python scripts/fetch_online.py \
  --start-date 2024-09-01 \
  --end-date 2026-09-13 \
  --min-players 50
```

The script writes:

- `data/raw/online/tournament-index.json` — all in-range PTCG Standard index rows
- `data/raw/online/index.json` — eligibility audit and rejection reasons
- `data/raw/online/<tournament-id>/details.json`
- `data/raw/online/<tournament-id>/standings.json`
- `data/raw/online/<tournament-id>/tournament.json`
- `data/raw/online/manifest.json`

`standings.json` is intentionally compact. It preserves research-relevant source fields such as deck classification, country, record, placing and drop metadata, but removes full card-list payloads and player handles. This keeps the historical archive practical while freezing the deck classification evidence used by the model.

## Run in GitHub Actions

Use **Actions → Fetch historical Online data → Run workflow** and set dates/minimum players.

The workflow commits collected JSON back to the repository when data changes.

## Analysis sequence

1. Audit historical Online availability and classification coverage.
2. Add/reconstruct historical IRL Day 1 fields.
3. Build clean major-by-major backtest windows.
4. Score simple baselines: IRL-only, Online-only, 50/50.
5. Reproduce current Blended v2.1 as a benchmark.
6. Test IRL weight/decay.
7. Test Online recency/window/half-life.
8. Use chronological walk-forward validation.
9. Examine format-transition rules separately.
10. Only after evidence is convincing, specify a candidate production formula for PTCG Tools.

## Data policy

This repository is a research dataset, not an app cache. Source classifications are snapshotted at collection time. Derived tables must be reproducible from those snapshots and scripts. Avoid retrospectively changing deck identities merely to improve model scores.
