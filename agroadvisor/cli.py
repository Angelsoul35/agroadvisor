"""AgroAdvisor command-line demo and entry point.

``python -m agroadvisor.cli demo`` runs three field scenarios. For each it prints
the figures the deterministic engine computed, then the advisory prose. With no
API key set (the default) the advisory comes from the offline template, so the
demo is fully reproducible and shows that the template uses only the engine's
numbers.
"""

from __future__ import annotations

import argparse

from .crops import GrowthStage
from .engine import Recommendation, SoilTest, Weather
from .service import AdvisorService

# Each scenario: a label, crop key, growth stage, soil test and weather.
SCENARIOS = [
    (
        "Dry-spell maize at the vegetative stage",
        "maize",
        GrowthStage.VEGETATIVE,
        SoilTest(n_kg_ha=50, p_kg_ha=15, k_kg_ha=30),
        Weather(
            et0_mm=6.5,
            rainfall_mm=2.0,
            temperature_c=30.0,
            humidity_pct=50.0,
            leaf_wetness_hours=2.0,
        ),
    ),
    (
        "Well-watered tomato at flowering (recent rain covers demand)",
        "tomato",
        GrowthStage.FLOWERING,
        SoilTest(n_kg_ha=130, p_kg_ha=70, k_kg_ha=180),
        Weather(
            et0_mm=4.0,
            rainfall_mm=12.0,
            temperature_c=22.0,
            humidity_pct=60.0,
            leaf_wetness_hours=3.0,
        ),
    ),
    (
        "High-humidity tomato at flowering (late-blight weather)",
        "tomato",
        GrowthStage.FLOWERING,
        SoilTest(n_kg_ha=90, p_kg_ha=50, k_kg_ha=120),
        Weather(
            et0_mm=3.5,
            rainfall_mm=1.0,
            temperature_c=18.0,
            humidity_pct=95.0,
            leaf_wetness_hours=12.0,
        ),
    ),
]


def _print_recommendation(rec: Recommendation) -> None:
    irr = rec.irrigation
    print(f"   crop:  {rec.crop} ({rec.crop_scientific}), stage {rec.stage}")
    print("   irrigation:")
    print(f"     Kc={irr.kc:g}  ET0={irr.et0_mm:g} mm  ETc=Kc*ET0={irr.crop_etc_mm:g} mm")
    print(
        f"     effective rainfall={irr.effective_rainfall_mm:g} mm "
        f"({irr.rainfall_mm:g} mm x {irr.effective_fraction:g})"
    )
    print(
        f"     net irrigation={irr.net_irrigation_mm:g} mm/day "
        f"= {irr.litres_per_m2:g} L/m^2   [{irr.rule}]"
    )
    print("   fertilisation (kg/ha):")
    for d in rec.fertilisation.deficits:
        print(
            f"     {d.nutrient}: target {d.target_kg_ha:g} - soil {d.soil_kg_ha:g} "
            f"-> deficit {d.deficit_kg_ha:g}"
        )
    risk = rec.pest_risk
    print(f"   pest/disease: {risk.disease}")
    for c in risk.conditions:
        mark = "x" if c.met else " "
        print(f"     [{mark}] {c.name}: {c.detail}")
    print(f"     risk level: {risk.level}  [{risk.rule}]")


def demo() -> None:
    print("AgroAdvisor demo\n" + "=" * 64)
    print(
        "\nThe numbers below are computed by the deterministic agronomy engine.\n"
        "The advisory is phrased by the LLM cascade when an API key is set, and\n"
        "by the offline template otherwise (as here) - same numbers either way."
    )
    service = AdvisorService()
    print(f"\nadvisor model: {service.llm.model}")

    for i, (label, crop, stage, soil, weather) in enumerate(SCENARIOS, start=1):
        print("\n" + "-" * 64)
        print(f"{i}) {label}")
        rec = service.recommend(crop, stage.value, soil, weather)
        _print_recommendation(rec)
        advisory = service.advisor.advise(rec)
        print(f"\n   advisory [{advisory.source}]:")
        print(f"   {advisory.text}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agroadvisor", description="AgroAdvisor CLI")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("demo", help="run three built-in field scenarios")
    args = parser.parse_args(argv)
    if args.command == "demo":
        demo()
        return 0
    parser.print_usage()
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
