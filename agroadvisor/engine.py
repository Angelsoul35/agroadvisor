"""The deterministic agronomy engine: the part that actually computes the advice.

Every substantive recommendation and every number in this project is produced
here, by plain, auditable arithmetic with explicit units — never by a language
model. The engine takes a crop, a growth stage, a soil test and recent weather,
and returns a :class:`Recommendation` that carries both the numbers and the rule
that produced each one, so a reader (or a test, or the advisor's prose) can trace
exactly how a figure was reached.

Three independent calculations:

1. **Irrigation.** Crop water demand is ``ETc = Kc * ET0`` (mm/day), where ``ET0``
   is reference evapotranspiration and ``Kc`` is the stage's crop coefficient.
   Effective rainfall is ``rainfall * effective_fraction`` (the rest runs off or
   drains past the roots). The net irrigation need is the shortfall that rainfall
   does not cover: ``net = max(0, ETc - effective_rainfall)`` mm/day. One millimetre
   over one square metre is one litre, so ``litres/m² == net mm``.

2. **Fertilisation.** For each of N, P and K, the top-up need is the stage target
   minus what the soil test already supplies: ``deficit = max(0, target - soil)``
   kg/ha. A nutrient the soil already meets gets a zero deficit (apply nothing).

3. **Pest / disease risk.** The crop's key disease has a weather band that favours
   it. The engine counts how many of three conditions hold — temperature in range,
   humidity high enough, leaf wetness long enough — and maps the count to a LOW /
   MODERATE / HIGH label. Each condition is reported with the comparison behind it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .crops import Crop, GrowthStage


@dataclass(frozen=True)
class SoilTest:
    """Plant-available nutrients measured in the field, kg/ha."""

    n_kg_ha: float
    p_kg_ha: float
    k_kg_ha: float


@dataclass(frozen=True)
class Weather:
    """Recent weather / reference conditions used by the engine.

    ``et0_mm`` and ``rainfall_mm`` are daily figures (mm/day); the risk inputs
    describe the current canopy micro-climate.
    """

    et0_mm: float
    rainfall_mm: float
    temperature_c: float
    humidity_pct: float
    leaf_wetness_hours: float


@dataclass(frozen=True)
class IrrigationAdvice:
    et0_mm: float
    kc: float
    crop_etc_mm: float
    rainfall_mm: float
    effective_fraction: float
    effective_rainfall_mm: float
    net_irrigation_mm: float
    litres_per_m2: float
    rule: str


@dataclass(frozen=True)
class NutrientDeficit:
    nutrient: str
    target_kg_ha: float
    soil_kg_ha: float
    deficit_kg_ha: float


@dataclass(frozen=True)
class FertilisationAdvice:
    deficits: list[NutrientDeficit]
    rule: str


@dataclass(frozen=True)
class RiskCondition:
    name: str
    met: bool
    detail: str


@dataclass(frozen=True)
class PestRiskAdvice:
    disease: str
    conditions: list[RiskCondition]
    conditions_met: int
    level: str
    rule: str


@dataclass(frozen=True)
class Recommendation:
    crop: str
    crop_scientific: str
    stage: str
    irrigation: IrrigationAdvice
    fertilisation: FertilisationAdvice
    pest_risk: PestRiskAdvice


def _round(value: float) -> float:
    """Round to two decimals; ``-0.0`` is normalised to ``0.0``."""
    result = round(value, 2)
    return result + 0.0


def _irrigation(kc: float, weather: Weather, effective_fraction: float) -> IrrigationAdvice:
    etc = kc * weather.et0_mm
    effective_rain = weather.rainfall_mm * effective_fraction
    net = max(0.0, etc - effective_rain)
    return IrrigationAdvice(
        et0_mm=_round(weather.et0_mm),
        kc=kc,
        crop_etc_mm=_round(etc),
        rainfall_mm=_round(weather.rainfall_mm),
        effective_fraction=effective_fraction,
        effective_rainfall_mm=_round(effective_rain),
        net_irrigation_mm=_round(net),
        litres_per_m2=_round(net),
        rule=(
            f"net = max(0, Kc*ET0 - rainfall*{effective_fraction:g}) = "
            f"max(0, {kc:g}*{weather.et0_mm:g} - {weather.rainfall_mm:g}*{effective_fraction:g})"
        ),
    )


def _deficit(nutrient: str, target: float, soil: float) -> NutrientDeficit:
    return NutrientDeficit(
        nutrient=nutrient,
        target_kg_ha=_round(target),
        soil_kg_ha=_round(soil),
        deficit_kg_ha=_round(max(0.0, target - soil)),
    )


def _pest_risk(crop: Crop, weather: Weather, *, moderate_at: int, high_at: int) -> PestRiskAdvice:
    d = crop.disease
    temp_ok = d.temp_min_c <= weather.temperature_c <= d.temp_max_c
    humidity_ok = weather.humidity_pct >= d.humidity_pct_min
    wetness_ok = weather.leaf_wetness_hours >= d.leaf_wetness_hours_min
    conditions = [
        RiskCondition(
            name="temperature in favourable range",
            met=temp_ok,
            detail=(
                f"{weather.temperature_c:g} C "
                f"{'within' if temp_ok else 'outside'} {d.temp_min_c:g}-{d.temp_max_c:g} C"
            ),
        ),
        RiskCondition(
            name="humidity high enough",
            met=humidity_ok,
            detail=(
                f"{weather.humidity_pct:g}% {'>=' if humidity_ok else '<'} {d.humidity_pct_min:g}%"
            ),
        ),
        RiskCondition(
            name="leaf wetness long enough",
            met=wetness_ok,
            detail=(
                f"{weather.leaf_wetness_hours:g} h "
                f"{'>=' if wetness_ok else '<'} {d.leaf_wetness_hours_min:g} h"
            ),
        ),
    ]
    met = sum(1 for c in conditions if c.met)
    if met >= high_at:
        level = "HIGH"
    elif met >= moderate_at:
        level = "MODERATE"
    else:
        level = "LOW"
    return PestRiskAdvice(
        disease=d.name,
        conditions=conditions,
        conditions_met=met,
        level=level,
        rule=(
            f"{met}/3 favourable conditions met -> {level} "
            f"(MODERATE at {moderate_at}, HIGH at {high_at})"
        ),
    )


def recommend(
    crop: Crop,
    stage: GrowthStage,
    soil: SoilTest,
    weather: Weather,
    *,
    effective_fraction: float = 0.8,
    risk_moderate_at: int = 2,
    risk_high_at: int = 3,
) -> Recommendation:
    """Compute the full agronomic recommendation for one field observation.

    All three sub-calculations are pure functions of the inputs: the same inputs
    always yield the same numbers. Nothing here reads the network or an API key.
    """
    profile = crop.stage(stage)
    irrigation = _irrigation(profile.kc, weather, effective_fraction)
    fertilisation = FertilisationAdvice(
        deficits=[
            _deficit("N", profile.n_target_kg_ha, soil.n_kg_ha),
            _deficit("P", profile.p_target_kg_ha, soil.p_kg_ha),
            _deficit("K", profile.k_target_kg_ha, soil.k_kg_ha),
        ],
        rule="deficit = max(0, stage target - soil test) per nutrient, kg/ha",
    )
    pest_risk = _pest_risk(crop, weather, moderate_at=risk_moderate_at, high_at=risk_high_at)
    return Recommendation(
        crop=crop.name,
        crop_scientific=crop.scientific_name,
        stage=stage.value,
        irrigation=irrigation,
        fertilisation=fertilisation,
        pest_risk=pest_risk,
    )
