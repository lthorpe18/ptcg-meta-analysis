# Online spread / long-tail diagnostic

## Question

When we compare the previous IRL major with qualifying Online play before the next IRL cohort, how often do the previous IRL top decks lose share simply because Online is more diffuse, and how much of that wider Online tail survives into the next IRL field?

This is a descriptive diagnostic only. It does **not** change the forecast formula.

## Sample

- Full historical settled primary sample: **25 independent cohorts** (2024-10-19 to 2026-06-12).
- Recent-era sensitivity: **11 cohorts** (2025-09-13 to 2026-06-12).
- Named archetypes only; source Other/Unknown/unclassified is excluded and each source distribution is renormalised to 100%, matching the existing forecast research.
- 'Top N' is defined from the **previous IRL field**, so no future information is used.

## Headline concentration result

| Previous-IRL top group | IRL top-N share | Online own top-N share | Same IRL top-N decks Online | Next IRL own top-N share | Prior top-N decks lower Online | Cohorts where Online top-N is less concentrated |
|---|---:|---:|---:|---:|---:|---:|
| Top 3 | 35.3% | 27.7% | 24.6% | 34.8% | 89.3% | 96.0% |
| Top 5 | 49.3% | 39.8% | 35.1% | 49.1% | 88.0% | 96.0% |
| Top 10 | 71.3% | 59.5% | 54.1% | 71.0% | 76.4% | 100.0% |
| Top 20 | 88.9% | 80.2% | 73.5% | 88.8% | 62.8% | 100.0% |

## Do apparent Online drops carry into the next IRL field?

| Previous-IRL top group | Mean Online delta per top deck | Mean next-IRL delta per top deck | If deck drops Online, next IRL also down | Correlation Online delta vs next IRL delta |
|---|---:|---:|---:|---:|
| Top 3 | -3.55pp | -0.93pp | 71.6% | 0.57 |
| Top 5 | -2.84pp | -0.60pp | 68.2% | 0.60 |
| Top 10 | -1.72pp | -0.28pp | 68.1% | 0.58 |
| Top 20 | -0.77pp | -0.13pp | 72.6% | 0.56 |

## New / tail archetypes

- Mean share Online from named archetypes absent from the previous IRL field: **6.5%**.
- Mean share at the next IRL cohort from named archetypes absent from the previous IRL field: **1.5%**.
- Mean named archetype count: previous IRL **72.2**, Online **83.6**, next IRL **72.3**.

## Recent-era sensitivity

| Previous-IRL top group | Prior top decks lower Online | Online own top-N less concentrated | Mean Online delta | Mean next-IRL delta |
|---|---:|---:|---:|---:|
| Top 3 | 90.9% | 90.9% | -3.80pp | -1.05pp |
| Top 5 | 90.9% | 100.0% | -2.81pp | -0.44pp |
| Top 10 | 80.0% | 100.0% | -1.65pp | -0.26pp |
| Top 20 | 65.9% | 100.0% | -0.74pp | -0.16pp |

## Current Worlds → Online illustration

For the existing 2026-09-14 snapshot, the previous IRL top 10 held **82.6%** of the Worlds field but only **54.4%** of subsequent Online play; **7/10** were lower Online.

| Archetype | Worlds IRL | Online since | Delta |
|---|---:|---:|---:|
| Dragapult | 22.5% | 12.8% | -9.6pp |
| Dragapult Dusknoir | 10.5% | 5.8% | -4.6pp |
| Dragapult Blaziken | 9.8% | 3.6% | -6.3pp |
| Basic Box | 9.3% | 4.0% | -5.4pp |
| N's Zoroark | 7.6% | 6.8% | -0.8pp |
| Alakazam Dudunsparce | 6.8% | 7.9% | 1.0pp |
| Slowking | 5.9% | 5.2% | -0.7pp |
| Mega Excadrill | 4.0% | 4.0% | 0.0pp |
| Raging Bolt Ogerpon | 3.2% | 1.3% | -1.9pp |
| Festival Lead | 2.9% | 3.0% | 0.1pp |

## Interpretation boundary

- **Verified:** values above are direct calculations from the frozen historical archive and existing window rules.
- **Inferred:** if Online concentration is repeatedly lower while the next IRL field re-concentrates, raw per-deck Online-vs-IRL deltas partly reflect platform-level spread rather than pure deck-specific decline.
- **Unknown:** whether explicitly correcting for concentration/tail structure improves chronological field-forecast accuracy. That requires a separate forecasting experiment.

