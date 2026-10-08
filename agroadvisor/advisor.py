"""Turn a computed :class:`Recommendation` into readable prose.

This is the only place a language model is allowed near the advice, and even here
it does **not** decide anything: the numbers and the risk level are already fixed
by :mod:`agroadvisor.engine`. The advisor's job is purely presentational — phrase
the computed figures in plain language.

- **Primary path (LLM).** The prompt carries every computed number and the system
  prompt forbids inventing, changing or omitting any of them. If the cascade
  succeeds, the prose is the model's, grounded strictly in the figures it was given.
- **Offline fallback (template).** With no API key (or any provider failure) the
  cascade raises and the advisor renders a deterministic template over the exact
  same numbers. The substance is identical; only the wording is plainer.

The result records its ``source`` (``"llm"`` or ``"template"``) so a caller always
knows which path produced the text. Neither path can introduce a value that the
engine did not compute.
"""

from __future__ import annotations

from dataclasses import dataclass

from .engine import Recommendation
from .llm.base import LLMClient, LLMError

_SYSTEM = (
    "You are an agronomy assistant that phrases pre-computed recommendations for a "
    "grower. You will be given exact numbers from a deterministic agronomy engine: "
    "irrigation depth, nutrient deficits and a pest/disease risk level. Rewrite them "
    "as clear, practical advice in 3 to 5 short sentences. Use ONLY the numbers and "
    "the risk level provided. Do not invent, change, round differently, add or omit "
    "any figure, and do not introduce agronomic claims that are not in the input. If "
    "a value is zero (for example no irrigation needed, or a nutrient already met), "
    "say so plainly."
)


@dataclass
class Advisory:
    text: str
    source: str  # "llm" or "template"


def _facts(rec: Recommendation) -> str:
    """The computed figures, laid out for the LLM prompt (one fact per line)."""
    irr = rec.irrigation
    lines = [
        f"Crop: {rec.crop} ({rec.crop_scientific}), growth stage: {rec.stage}.",
        f"Crop coefficient Kc = {irr.kc:g}; reference ET0 = {irr.et0_mm:g} mm/day.",
        f"Crop water demand ETc = {irr.crop_etc_mm:g} mm/day.",
        (
            f"Effective rainfall = {irr.effective_rainfall_mm:g} mm/day "
            f"(of {irr.rainfall_mm:g} mm at {irr.effective_fraction:g} effectiveness)."
        ),
        (
            f"Net irrigation need = {irr.net_irrigation_mm:g} mm/day "
            f"= {irr.litres_per_m2:g} litres per square metre."
        ),
    ]
    for d in rec.fertilisation.deficits:
        lines.append(
            f"{d.nutrient}: target {d.target_kg_ha:g} kg/ha, soil {d.soil_kg_ha:g} kg/ha, "
            f"deficit {d.deficit_kg_ha:g} kg/ha."
        )
    risk = rec.pest_risk
    lines.append(
        f"Pest/disease: {risk.disease}, risk level {risk.level} "
        f"({risk.conditions_met}/3 favourable conditions met)."
    )
    return "\n".join(lines)


def _prompt(rec: Recommendation) -> str:
    return f"Computed figures:\n{_facts(rec)}\n\nWrite the advice:"


def _template(rec: Recommendation) -> str:
    """Deterministic prose over the exact computed numbers. Invents nothing."""
    irr = rec.irrigation
    out: list[str] = []
    out.append(
        f"{rec.crop} at the {rec.stage} stage (Kc {irr.kc:g}, ET0 {irr.et0_mm:g} mm/day)."
    )

    if irr.net_irrigation_mm > 0:
        out.append(
            f"Irrigation: apply {irr.net_irrigation_mm:g} mm/day "
            f"({irr.litres_per_m2:g} litres per square metre). Crop demand is "
            f"{irr.crop_etc_mm:g} mm/day and effective rainfall covers "
            f"{irr.effective_rainfall_mm:g} mm/day."
        )
    else:
        out.append(
            f"Irrigation: none needed. Effective rainfall ({irr.effective_rainfall_mm:g} "
            f"mm/day) already meets the {irr.crop_etc_mm:g} mm/day crop demand."
        )

    needed = [d for d in rec.fertilisation.deficits if d.deficit_kg_ha > 0]
    met = [d for d in rec.fertilisation.deficits if d.deficit_kg_ha <= 0]
    if needed:
        parts = ", ".join(f"{d.nutrient} {d.deficit_kg_ha:g} kg/ha" for d in needed)
        out.append(f"Fertilisation: top up {parts}.")
    else:
        out.append("Fertilisation: soil levels meet the stage targets; apply nothing.")
    if met and needed:
        out.append(
            "Already met: " + ", ".join(f"{d.nutrient}" for d in met) + "."
        )

    risk = rec.pest_risk
    out.append(
        f"Pest/disease risk for {risk.disease}: {risk.level} "
        f"({risk.conditions_met}/3 favourable conditions met)."
    )
    return " ".join(out)


class Advisor:
    def __init__(self, llm: LLMClient | None = None, max_tokens: int = 400) -> None:
        self.llm = llm
        self.max_tokens = max_tokens

    def advise(self, rec: Recommendation) -> Advisory:
        if self.llm is not None:
            try:
                result = self.llm.complete(
                    _SYSTEM, _prompt(rec), max_tokens=self.max_tokens
                )
                text = result.text.strip()
                if text:
                    return Advisory(text=text, source="llm")
            except LLMError:
                pass
        return Advisory(text=_template(rec), source="template")
