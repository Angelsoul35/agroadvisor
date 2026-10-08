"""The advisor: LLM phrasing on the happy path, deterministic template otherwise.

The key honesty test here is ``test_template_invents_no_numbers``: every numeric
token the offline template prints must be one the engine actually computed.
"""

from __future__ import annotations

import re

from agroadvisor.advisor import Advisor
from agroadvisor.crops import GrowthStage
from agroadvisor.engine import Recommendation, SoilTest, Weather, recommend
from agroadvisor.knowledge import KnowledgeBase
from agroadvisor.llm.fake import FailingLLM, FakeLLM

KB = KnowledgeBase()


def _dry_maize() -> Recommendation:
    return recommend(
        KB.get("maize"),
        GrowthStage.VEGETATIVE,
        SoilTest(n_kg_ha=50, p_kg_ha=15, k_kg_ha=30),
        Weather(
            et0_mm=6.5,
            rainfall_mm=2.0,
            temperature_c=30.0,
            humidity_pct=50.0,
            leaf_wetness_hours=2.0,
        ),
    )


def _allowed_numbers(rec: Recommendation) -> set[str]:
    """Every number the engine produced, in the ``:g`` string form the template uses."""
    irr = rec.irrigation
    allowed = {
        f"{v:g}"
        for v in (
            irr.kc,
            irr.et0_mm,
            irr.crop_etc_mm,
            irr.rainfall_mm,
            irr.effective_fraction,
            irr.effective_rainfall_mm,
            irr.net_irrigation_mm,
            irr.litres_per_m2,
        )
    }
    for d in rec.fertilisation.deficits:
        allowed.update({f"{d.target_kg_ha:g}", f"{d.soil_kg_ha:g}", f"{d.deficit_kg_ha:g}"})
    allowed.add(f"{rec.pest_risk.conditions_met:g}")
    allowed.add("3")  # the fixed denominator: three conditions are checked
    return allowed


def test_llm_path_uses_model_text():
    advisor = Advisor(llm=FakeLLM("Water the maize and watch for blight."))
    advisory = advisor.advise(_dry_maize())
    assert advisory.source == "llm"
    assert advisory.text == "Water the maize and watch for blight."


def test_failing_llm_falls_back_to_template():
    advisory = Advisor(llm=FailingLLM()).advise(_dry_maize())
    assert advisory.source == "template"
    # The computed net irrigation (2.95 mm) must be present in the prose.
    assert "2.95" in advisory.text


def test_empty_llm_text_falls_back_to_template():
    advisory = Advisor(llm=FakeLLM("   ")).advise(_dry_maize())
    assert advisory.source == "template"


def test_no_llm_uses_template():
    advisory = Advisor(llm=None).advise(_dry_maize())
    assert advisory.source == "template"


def test_template_invents_no_numbers():
    rec = _dry_maize()
    advisory = Advisor(llm=FailingLLM()).advise(rec)
    allowed = _allowed_numbers(rec)
    # Word-boundary anchored so a digit inside a label (the "0" in "ET0") is not
    # mistaken for a number.
    found = re.findall(r"\b\d+(?:\.\d+)?\b", advisory.text)
    assert found, "template should contain numbers"
    unexpected = [n for n in found if n not in allowed]
    assert not unexpected, f"template printed numbers the engine never computed: {unexpected}"


def test_template_says_no_irrigation_when_demand_is_covered():
    rec = recommend(
        KB.get("tomato"),
        GrowthStage.FLOWERING,
        SoilTest(n_kg_ha=130, p_kg_ha=70, k_kg_ha=180),
        Weather(
            et0_mm=4.0,
            rainfall_mm=12.0,
            temperature_c=22.0,
            humidity_pct=60.0,
            leaf_wetness_hours=3.0,
        ),
    )
    advisory = Advisor(llm=FailingLLM()).advise(rec)
    assert rec.irrigation.net_irrigation_mm == 0.0
    assert "none needed" in advisory.text.lower()
    # It must also report that fertiliser is already met (soil exceeds the targets).
    assert "apply nothing" in advisory.text.lower()


def test_template_reports_high_blight_risk():
    rec = recommend(
        KB.get("tomato"),
        GrowthStage.FLOWERING,
        SoilTest(n_kg_ha=90, p_kg_ha=50, k_kg_ha=120),
        Weather(
            et0_mm=3.5,
            rainfall_mm=1.0,
            temperature_c=18.0,
            humidity_pct=95.0,
            leaf_wetness_hours=12.0,
        ),
    )
    advisory = Advisor(llm=FailingLLM()).advise(rec)
    assert rec.pest_risk.level == "HIGH"
    assert "HIGH" in advisory.text
    assert "Late blight" in advisory.text
