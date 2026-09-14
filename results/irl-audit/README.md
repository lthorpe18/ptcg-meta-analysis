# Historical IRL archive audit

Generated: 2026-09-14T08:22:02.955095+00:00

## Headline

- Period: **2024-09-13 to 2026-08-30**
- IRL majors: **71**; unique IDs: **71**; source failures: **0**
- Reported Masters players: **112,609**
- Day-1 deck-field entries captured: **112,228 (99.66% overall)**
- `Other` entries retained: **1,020**

## Field completeness by event

- Median: **99.76%**
- 10th percentile: **98.66%**
- Minimum: **88.16%**
- Events >=99% complete: **63/71**
- Events >=98% complete: **66/71**
- Events >=95% complete: **68/71**

## Integrity

- Duplicate IDs: **0**
- Non-Masters events: **0**
- Non-Day-1 views: **0**
- Variant grouping unexpectedly enabled: **0**
- Field rows exceeding reported players: **0**

## By event type

| Type | Events | Players | Median field completeness | Min | Median top-5 share | Median variants >=1% |
|---|---:|---:|---:|---:|---:|---:|
| International Championship | 6 | 18,862 | 99.79% | 99.72% | 52.24% | 17.0 |
| Regional Championship | 50 | 83,184 | 99.77% | 99.17% | 48.61% | 19.0 |
| Special Event | 13 | 9,045 | 98.60% | 88.16% | 52.40% | 19 |
| World Championship | 2 | 1,518 | 99.79% | 99.58% | 62.75% | 14.5 |

## Worlds — descriptive only

There are only **2 Worlds**, so do not infer a stable Worlds-specific rule from this sample yet.
- Worlds median top-5 share: **62.75%** vs **49.23%** for non-Worlds.
- Worlds median number of variants >=1%: **14.5** vs **19** for non-Worlds.

## Lowest field completeness

| Date | Event | Type | Players | Captured | Completeness |
|---|---|---|---:|---:|---:|
| 2024-10-05 | Special Event Lima | Special Event | 304 | 268 | 88.16% |
| 2026-01-24 | Special Event Auckland | Special Event | 80 | 71 | 88.75% |
| 2024-11-09 | Special Event Buenos Aires | Special Event | 275 | 250 | 90.91% |
| 2026-03-07 | Special Event San Juan | Special Event | 356 | 345 | 96.91% |
| 2026-05-23 | Special Event Lima | Special Event | 499 | 485 | 97.19% |
| 2025-11-15 | Special Event Buenos Aires | Special Event | 350 | 345 | 98.57% |
| 2024-12-07 | Special Event Bogotá | Special Event | 215 | 212 | 98.60% |
| 2025-02-15 | Special Event San Juan | Special Event | 299 | 295 | 98.66% |
| 2026-04-04 | Regional Championship Querétaro | Regional Championship | 1446 | 1434 | 99.17% |
| 2025-04-19 | Regional Championship Monterrey | Regional Championship | 1327 | 1317 | 99.25% |

## Interpretation

For prediction-target scoring, field completeness matters more than the share assigned to a named archetype, because `Other` is still a legitimate field bucket. A sensible first candidate is to require >=95% captured field, then test >=98% as a sensitivity check rather than choosing a threshold to improve model scores.

Same-date majors are retained but must be treated as one correlated prediction cohort during walk-forward evaluation.

Completeness is verified against the Limitless Labs index captured by the collector, not yet against an independent official Pokemon event calendar.
