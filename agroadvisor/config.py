"""Runtime configuration, loaded from environment variables with the ``AA_`` prefix."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AA_", env_file=".env", extra="ignore")

    # Fraction of recent rainfall that actually reaches the root zone (the rest is
    # lost to runoff and deep percolation). An illustrative flat coefficient; a real
    # product would use a method such as USDA-SCS that depends on rainfall depth.
    effective_rainfall_fraction: float = 0.8

    # Pest/disease risk is a count of favourable conditions met (0..3). These two
    # dials map that count to a LOW / MODERATE / HIGH label.
    risk_moderate_at: int = 2
    risk_high_at: int = 3

    # LLM provider cascade, tried in order. Each reads its own key from the env;
    # when all fail (for instance, no key is set), the advisor falls back to a
    # deterministic template that renders the very same computed numbers.
    llm_spec: str = "anthropic,openai,gemini,deepseek,ollama"
    llm_max_tokens: int = 400


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
