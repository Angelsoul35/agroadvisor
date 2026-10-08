# ADR 0002 — Offline-first, with a provider-agnostic LLM cascade

## Status
Accepted.

## Context
The phrasing layer should be able to use a strong hosted model when one is
available, but the advisory must never *depend* on a network call or a specific
vendor. A demo that breaks without an API key, or that is locked to one provider,
is neither robust nor portable.

## Decision
The advisor depends on an `LLMClient` interface, not a vendor SDK. `build_llm`
constructs a `CascadeLLM` over a configurable list of providers (Anthropic,
OpenAI, Gemini, DeepSeek, a local Ollama model). Each is tried in order; any
failure — missing key, rate limit, network error, bad response — raises
`LLMError` and the cascade falls through to the next. When every provider fails,
which includes the default no-key case, the advisor renders the deterministic
template. The template produces the same substantive numbers as the LLM path.

## Consequences
- The system runs fully offline out of the box, with no configuration.
- Switching or reordering providers is a config change (`AA_LLM_SPEC`), not a code
  change; adding one is a single adapter behind the same interface.
- Because failure is a normal, expected path, tests exercise the fallback with a
  `FailingLLM` double and never touch the network.
