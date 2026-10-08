# ADR 0004 — Rule-based, explainable pest/disease risk

## Status
Accepted.

## Context
Pest and disease pressure depends on weather: many foliar diseases need a
temperature window, high humidity and a stretch of leaf wetness to establish. We
want a risk signal that a grower can understand and challenge, not an opaque score
— and one that stays deterministic like the rest of the engine.

## Decision
Each crop carries one key disease with a weather band: a temperature range, a
minimum humidity and a minimum leaf-wetness duration. The engine checks the three
conditions independently, counts how many hold (0–3), and maps the count to a
label: `MODERATE` at `AA_RISK_MODERATE_AT` (default 2), `HIGH` at
`AA_RISK_HIGH_AT` (default 3), otherwise `LOW`. Every condition is reported with
the exact comparison behind it (for example `95% >= 90%`), and the thresholds are
inclusive.

## Consequences
- The risk level is fully explainable: a grower sees which conditions fired and
  why, and can override with local judgement.
- It is deterministic and testable, including on the inclusive boundaries.
- It is intentionally simple: a univariate, three-condition rule, not a validated
  epidemiological model. It does not account for inoculum presence, cultivar
  resistance, spray history or a multi-day wetness pattern; a real product would
  use a validated disease model. The thresholds being operator dials makes the
  simplification explicit rather than hidden.
