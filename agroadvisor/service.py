"""Application service: resolve the crop, run the engine, then phrase the result.

The service is the one object a caller (the API or the CLI) needs. It owns the
knowledge base and the LLM cascade, turns the request into the engine's typed
inputs, and returns a plain dictionary holding the full structured recommendation
plus the advisory prose and the source that produced it.
"""

from __future__ import annotations

from dataclasses import asdict

from .advisor import Advisor
from .config import Settings, get_settings
from .crops import GrowthStage
from .engine import Recommendation, SoilTest, Weather, recommend
from .knowledge import KnowledgeBase
from .llm.base import LLMClient
from .llm.factory import build_llm


class AdvisorService:
    def __init__(
        self,
        settings: Settings | None = None,
        llm: LLMClient | None = None,
        knowledge: KnowledgeBase | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm = llm if llm is not None else build_llm(self.settings.llm_spec)
        self.knowledge = knowledge or KnowledgeBase()
        self.advisor = Advisor(llm=self.llm, max_tokens=self.settings.llm_max_tokens)

    def recommend(self, crop: str, stage: str, soil: SoilTest, weather: Weather) -> Recommendation:
        """Resolve the crop and stage and run the deterministic engine."""
        crop_obj = self.knowledge.get(crop)
        stage_obj = GrowthStage(stage.strip().lower())
        return recommend(
            crop_obj,
            stage_obj,
            soil,
            weather,
            effective_fraction=self.settings.effective_rainfall_fraction,
            risk_moderate_at=self.settings.risk_moderate_at,
            risk_high_at=self.settings.risk_high_at,
        )

    def advise(self, crop: str, stage: str, soil: SoilTest, weather: Weather) -> dict:
        """Full pipeline: compute the recommendation, then phrase it.

        The returned ``recommendation`` is the authoritative, computed substance;
        ``advisory`` is only a rendering of it, and ``advisory_source`` says whether
        the LLM or the offline template produced that rendering.
        """
        rec = self.recommend(crop, stage, soil, weather)
        advisory = self.advisor.advise(rec)
        return {
            "recommendation": asdict(rec),
            "advisory": advisory.text,
            "advisory_source": advisory.source,
        }
