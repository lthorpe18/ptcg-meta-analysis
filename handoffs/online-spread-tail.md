# Online spread / long-tail diagnostic handoff

Date: 15 September 2026
Repository: `lthorpe18/ptcg-meta-analysis`
Base research state: `historical-online-chunked` at `67310cbab568a2632cec96cedfce1b8118d25d3c`
Working branch: `research/online-spread-tail`

## Explicit owner question

Investigate whether the large number of small named decks in Online play structurally depresses the apparent percentage share of the top decks versus the previous IRL major, and quantify how often that happens historically.

## Scope and method

- Same frozen historical prediction windows and named-archetype normalisation as the existing field-prediction research.
- Settled targets with >=95% IRL field capture and usable post-major Online evidence.
- Independent cohort is the unit of analysis; simultaneous targets are not double-counted.
- Full sample: 25 cohorts, 2024-10-19 through 2026-06-12.
- Recent-era sensitivity: 11 cohorts, 2025-09-13 through 2026-06-12.
- `Top N` is defined from the previous IRL field only; no future information is used.
- Source Other/Unknown/unclassified remains excluded and each named distribution is renormalised to 100%, matching the existing forecast research.

## Verified results

### Structural concentration difference

Across the 25 full-history cohorts:
- previous IRL top 10 mean share: **71.3%**;
- Online own top 10 mean share: **59.5%**;
- next IRL own top 10 mean share: **71.0%**;
- Online top-10 concentration was lower than previous IRL in **25/25 cohorts (100%)**.

For the previous-IRL top decks themselves:
- top 1 lower Online: **24/25 = 96.0%**;
- top 3 deck-observations lower Online: **67/75 = 89.3%**;
- top 5: **110/125 = 88.0%**;
- top 10: **191/250 = 76.4%**;
- top 20: **314/500 = 62.8%**.

Every cohort had a majority of its previous IRL top 10 decks lower Online.

### Apparent Online decline is much larger than next-IRL decline

For previous-IRL top 10 decks:
- mean Online delta vs previous IRL: **-1.72pp per deck**;
- mean next-IRL delta vs previous IRL: **-0.28pp per deck**;
- among top-10 observations that fell Online, **68.1%** also fell at the next IRL, so Online direction contains real information, but the magnitude is much more negative Online;
- Online-delta vs next-IRL-delta Pearson correlation: **r = 0.58**.

### Long-tail / new archetypes

- Mean Online share from named archetypes absent from the previous IRL field: **6.5%**.
- Mean next-IRL share from named archetypes absent from the previous IRL field: **1.5%**.
- Mean named archetype count: previous IRL **72.2**, Online **83.6**, next IRL **72.3**.

This shows that much of the extra Online tail does not survive at the same magnitude into the next IRL field.

### Recent-era sensitivity

The pattern persists in the 11 recent cohorts:
- previous IRL top 10 decks lower Online: **80.0%**;
- Online own top-10 concentration lower than previous IRL: **11/11 = 100%**;
- mean Online delta for prior top-10 decks: **-1.65pp**;
- mean next-IRL delta: **-0.26pp**.

### Current Worlds illustration

Existing 2026-09-14 snapshot:
- Worlds previous-IRL top 10 share: **82.6%**;
- those same decks' subsequent Online share: **54.4%**;
- **7/10** are lower Online.

This is more extreme than average because Worlds was unusually concentrated, but it follows the same historical structural pattern.

## Interpretation boundary

**Verified:** Online is systematically more diffuse than IRL in the historical settled sample, and raw previous-IRL-to-Online deltas therefore contain a strong concentration/tail component. The next IRL field typically re-concentrates toward the prior IRL level.

**Verified:** Online movement still contains real deck-specific information: decks that fall Online are more likely than not to fall at the next IRL, and Online/next-IRL deltas have moderate positive correlation.

**Inferred:** raw Online percentages should probably not be read literally as direct IRL-share targets, especially for major established decks after a concentrated event. A useful presentation should distinguish deck-specific movement from platform-level spread.

**Unknown:** whether an explicit concentration/tail correction improves chronological Field Accuracy. No correction is adopted by this diagnostic.

## Reproducibility

- Script: `scripts/analyse_online_spread_tail.py`
- Generated JSON: `data/processed/online-spread-tail/summary.json`
- Report: `results/online-spread-tail/README.md`
- Successful workflow run: `34992093296`

## Exact next action

Owner decision required. If desired, the next bounded experiment is to test a simple concentration-aware forecast correction chronologically against the existing IRL+Online blend. Candidate corrections should remain simple and interpretable (for example, shrink Online deck-level deltas toward an expected IRL concentration/tail structure) and must be compared against the unchanged current baseline before adoption.
