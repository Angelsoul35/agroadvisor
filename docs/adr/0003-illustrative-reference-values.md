# ADR 0003 — Keep agronomy data illustrative, in one labelled module

## Status
Accepted.

## Context
Real agronomic constants — crop coefficients, nutrient budgets, disease-favouring
weather bands — are regional, cultivar-specific and seasonal, and getting them
right is an agronomist's job backed by field data. This project is a portfolio
piece demonstrating an architecture, not a calibrated agronomic model, and must
not pretend otherwise.

## Decision
The reference values live in a single module, `knowledge.py`, whose docstring
states clearly that the numbers are illustrative teaching values — `Kc` figures
rounded from published FAO-56 ranges, and plausible order-of-magnitude NPK targets
and disease bands — not calibrated for any real region. The engine's arithmetic
(`engine.py`) is kept entirely separate from this data.

## Consequences
- The engine's logic can be read, trusted and tested on its own, independent of
  whether the constants are right for a given field.
- The data can be replaced with locally calibrated, agronomist-reviewed values
  without touching the arithmetic — the intended path to a real product.
- The claim the project makes is verifiable: the *method* is sound and tested; the
  *numbers* are illustrative, and the README's scope note says so explicitly.
