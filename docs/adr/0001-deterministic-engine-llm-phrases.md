# ADR 0001 — The agronomy engine computes the substance; the LLM only phrases it

## Status
Accepted.

## Context
A grower acts on the numbers an advisory produces: millimetres of irrigation,
kilograms of fertiliser, a spray/no-spray decision. Those numbers must be correct
and reproducible. A large language model is fluent but can hallucinate, so it is
the wrong component to *compute* a figure someone will act on in a field.

## Decision
All substantive output — irrigation depth, N/P/K deficits, pest/disease risk
level — is computed by a deterministic engine (`engine.py`) using explicit
arithmetic with stated units. The engine returns a structured `Recommendation`
that carries both the numbers and the rule behind each. The language model is
confined to presentation: it receives the computed figures and rephrases them,
instructed to invent, change or omit nothing.

## Consequences
- The trustworthy part of the system is small, pure and testable; the tests
  recompute its arithmetic by hand rather than trusting it.
- The LLM output is a convenience layer. The structured recommendation is always
  returned alongside the prose, so the contract never depends on the model.
- Verifiability is built in: the offline template is tested to print only numbers
  the engine computed, and the docs state plainly that the model phrases, not decides.
