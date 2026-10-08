"""The deterministic engine, with every expected number recomputed by hand here.

These tests are the project's honesty anchor: they do not trust the engine, they
independently recompute what the arithmetic must produce and assert the engine
agrees.
"""

from __future__ import annotations

import pytest

from agroadvisor.crops import GrowthStage
from agroadvisor.engine import SoilTest, Weather, recommend
from agroadvisor.knowledge import KnowledgeBase

KB = KnowledgeBase()


def test_irrigation_is_demand_net_of_effective_rainfall(dry_maize_soil, dry_maize_weather):
    maize = KB.get("maize")
    rec = recommend(maize, GrowthStage.VEGETATIVE, dry_maize_soil, dry_maize_weather)

    # Hand computation: Kc=0.70, ET0=6.5 -> ETc=4.55; rain 2.0 * 0.8 = 1.6 effective;
    # net = max(0, 4.55 - 1.6) = 2.95 mm/day = 2.95 L/m^2.
    irr = rec.irrigation
    assert irr.kc == 0.70
    assert irr.crop_etc_mm == pytest.approx(4.55)
    assert irr.effective_rainfall_mm == pytest.approx(1.6)
    assert irr.net_irrigation_mm == pytest.approx(2.95)
    assert irr.litres_per_m2 == pytest.approx(2.95)


def test_irrigation_zero_when_rainfall_covers_demand():
    tomato = KB.get("tomato")
    soil = SoilTest(n_kg_ha=130, p_kg_ha=70, k_kg_ha=180)
    weather = Weather(
        et0_mm=4.0, rainfall_mm=12.0, temperature_c=22.0, humidity_pct=60.0, leaf_wetness_hours=3.0
    )
    rec = recommend(tomato, GrowthStage.FLOWERING, soil, weather)

    # Kc=1.15, ET0=4.0 -> ETc=4.6; rain 12 * 0.8 = 9.6 effective; net = max(0, 4.6-9.6) = 0.
    irr = rec.irrigation
    assert irr.crop_etc_mm == pytest.approx(4.6)
    assert irr.effective_rainfall_mm == pytest.approx(9.6)
    assert irr.net_irrigation_mm == 0.0
    assert irr.litres_per_m2 == 0.0


def test_effective_fraction_is_configurable():
    maize = KB.get("maize")
    soil = SoilTest(n_kg_ha=0, p_kg_ha=0, k_kg_ha=0)
    weather = Weather(
        et0_mm=5.0, rainfall_mm=5.0, temperature_c=20.0, humidity_pct=50.0, leaf_wetness_hours=0.0
    )
    # Kc(vegetative)=0.70 -> ETc=3.5. With fraction 1.0, effective rain = 5.0, net = 0.
    rec = recommend(maize, GrowthStage.VEGETATIVE, soil, weather, effective_fraction=1.0)
    assert rec.irrigation.effective_rainfall_mm == pytest.approx(5.0)
    assert rec.irrigation.net_irrigation_mm == 0.0


def test_fertiliser_deficit_is_target_minus_soil(dry_maize_soil, dry_maize_weather):
    maize = KB.get("maize")
    rec = recommend(maize, GrowthStage.VEGETATIVE, dry_maize_soil, dry_maize_weather)

    # Vegetative maize targets N=120, P=40, K=60; soil 50/15/30.
    # deficits: N=70, P=25, K=30.
    by_nutrient = {d.nutrient: d for d in rec.fertilisation.deficits}
    assert by_nutrient["N"].deficit_kg_ha == pytest.approx(70.0)
    assert by_nutrient["P"].deficit_kg_ha == pytest.approx(25.0)
    assert by_nutrient["K"].deficit_kg_ha == pytest.approx(30.0)


def test_fertiliser_deficit_never_negative_when_soil_exceeds_target(dry_maize_weather):
    maize = KB.get("maize")
    rich_soil = SoilTest(n_kg_ha=500, p_kg_ha=500, k_kg_ha=500)
    rec = recommend(maize, GrowthStage.VEGETATIVE, rich_soil, dry_maize_weather)
    for d in rec.fertilisation.deficits:
        assert d.deficit_kg_ha == 0.0


def test_pest_risk_high_when_all_three_conditions_met():
    maize = KB.get("maize")  # blight band: 18-27 C, humidity >= 85, wetness >= 6 h
    soil = SoilTest(n_kg_ha=0, p_kg_ha=0, k_kg_ha=0)
    weather = Weather(
        et0_mm=3.0, rainfall_mm=0.0, temperature_c=22.0, humidity_pct=90.0, leaf_wetness_hours=8.0
    )
    rec = recommend(maize, GrowthStage.VEGETATIVE, soil, weather)
    assert rec.pest_risk.conditions_met == 3
    assert rec.pest_risk.level == "HIGH"


def test_pest_risk_moderate_when_two_conditions_met():
    maize = KB.get("maize")
    soil = SoilTest(n_kg_ha=0, p_kg_ha=0, k_kg_ha=0)
    # temp in range (yes), humidity high (yes), wetness too short (no) -> 2/3.
    weather = Weather(
        et0_mm=3.0, rainfall_mm=0.0, temperature_c=22.0, humidity_pct=90.0, leaf_wetness_hours=2.0
    )
    rec = recommend(maize, GrowthStage.VEGETATIVE, soil, weather)
    assert rec.pest_risk.conditions_met == 2
    assert rec.pest_risk.level == "MODERATE"


def test_pest_risk_low_when_weather_is_unfavourable(dry_maize_soil, dry_maize_weather):
    maize = KB.get("maize")
    # The dry-spell weather: 30 C (out of range), 50% humidity (<85), 2 h wetness (<6).
    rec = recommend(maize, GrowthStage.VEGETATIVE, dry_maize_soil, dry_maize_weather)
    assert rec.pest_risk.conditions_met == 0
    assert rec.pest_risk.level == "LOW"


def test_pest_risk_thresholds_are_inclusive():
    maize = KB.get("maize")
    soil = SoilTest(n_kg_ha=0, p_kg_ha=0, k_kg_ha=0)
    # Exactly on every boundary: temp 27 (<=27), humidity 85 (>=85), wetness 6 (>=6).
    weather = Weather(
        et0_mm=3.0, rainfall_mm=0.0, temperature_c=27.0, humidity_pct=85.0, leaf_wetness_hours=6.0
    )
    rec = recommend(maize, GrowthStage.VEGETATIVE, soil, weather)
    assert rec.pest_risk.conditions_met == 3
    assert rec.pest_risk.level == "HIGH"


def test_recommendation_carries_crop_and_stage_identity():
    wheat = KB.get("wheat")
    soil = SoilTest(n_kg_ha=10, p_kg_ha=10, k_kg_ha=10)
    weather = Weather(
        et0_mm=5.0, rainfall_mm=0.0, temperature_c=20.0, humidity_pct=70.0, leaf_wetness_hours=4.0
    )
    rec = recommend(wheat, GrowthStage.FLOWERING, soil, weather)
    assert rec.crop == "Wheat"
    assert rec.crop_scientific == "Triticum aestivum"
    assert rec.stage == "flowering"
    assert rec.pest_risk.disease == "Fusarium head blight"


def test_unknown_crop_is_rejected():
    with pytest.raises(KeyError):
        KB.get("banana")


def test_crop_stage_rejects_a_missing_stage_with_a_helpful_error():
    # Crop.stage() is a public method: when a crop does not define a requested
    # stage it must raise a clear KeyError naming the crop and the stage, not a
    # bare dict lookup error. Build a crop with only one stage and ask for another.
    from agroadvisor.crops import Crop, DiseaseRisk, StageProfile

    partial = Crop(
        key="test",
        name="Testcrop",
        scientific_name="Testus cropus",
        stages={GrowthStage.INITIAL: StageProfile(0.4, 10.0, 5.0, 8.0)},
        disease=DiseaseRisk("none", 0.0, 100.0, 0.0, 0.0),
    )
    assert partial.stage(GrowthStage.INITIAL).kc == 0.4
    with pytest.raises(KeyError, match="no profile for stage"):
        partial.stage(GrowthStage.FLOWERING)
