# PTCG Meta Analysis

Standalone research workspace for testing Pokémon TCG metagame prediction methods independently of the production **PTCG Tools** application.

## Research objective

Reconstruct what information was available immediately before historical IRL majors, build candidate field predictions from prior IRL + Online evidence, and score those predictions against the actual Day 1 field.

The first phase is deliberately **data audit only**. No live PTCG Tools formula is changed from this repository.

## Phase 1 — Online historical data

The collector uses the public Limitless Tournament API and preserves raw tournament-level evidence.

Initial eligibility rules:

- Game: Pokémon TCG (`PTCG`)
- Format: Standard
- Online event
- Platform: Pokémon TCG Live / PTCGL
- At least 50 players by default
- Decklists/standings available
- Exclude events with custom banned cards or special rules
- Preserve raw source payloads rather than collapsing them into the current PTCG Tools formula

These rules are intentionally conservative and auditable. Later analysis can test thresholds such as event size, classification coverage, recency, organiser effects, etc.

## Repository layout

```text
data/
  raw/
    online/       # one folder per Limitless tournament
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

- `data/raw/online/index.json` — discovered eligible/ineligible events and audit reasons
- `data/raw/online/<tournament-id>/details.json`
- `data/raw/online/<tournament-id>/standings.json`
- `data/raw/online/<tournament-id>/tournament.json`
- `data/raw/online/manifest.json`

Raw responses are kept so later cleaning/model changes remain reproducible.

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

This repository is a research dataset, not an app cache. Raw source data should be immutable where practical. Derived tables must be reproducible from raw data and scripts. Avoid retrospectively changing deck identities merely to improve model scores.
