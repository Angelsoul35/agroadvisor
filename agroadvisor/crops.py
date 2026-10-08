"""Crop data model: growth stages, crop coefficients, NPK targets, disease rules.

These are the *types* the agronomy engine reasons over. The concrete, illustrative
reference values live in :mod:`agroadvisor.knowledge`. Keeping the shapes here and
the numbers there mirrors how a real product separates its schema from its
(regionally calibrated) agronomic data.

Units are stated on every field and kept consistent across the engine:

- crop coefficient ``Kc`` is dimensionless (FAO-56 single crop coefficient);
- nutrient targets and soil-test levels are kilograms per hectare (``kg/ha``);
- temperatures are degrees Celsius, humidity is a percentage, leaf wetness is hours.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GrowthStage(StrEnum):
    """Four coarse growth stages shared by every crop in the knowledge base.

    They follow the FAO-56 crop-development arc: a low-demand establishment phase,
    rising demand through canopy build-up, a peak around flowering, then a decline
    towards maturity.
    """

    INITIAL = "initial"
    VEGETATIVE = "vegetative"
    FLOWERING = "flowering"
    MATURITY = "maturity"


@dataclass(frozen=True)
class StageProfile:
    """Per-stage agronomic targets for one crop.

    ``kc`` scales reference evapotranspiration into crop water demand. The three
    nutrient targets are the amount of plant-available N, P and K (kg/ha) the stage
    is assumed to want in the root zone; the engine subtracts the soil test from
    them to get a top-up need.
    """

    kc: float
    n_target_kg_ha: float
    p_target_kg_ha: float
    k_target_kg_ha: float


@dataclass(frozen=True)
class DiseaseRisk:
    """A single key disease per crop with the weather band that favours it.

    The engine checks three independent conditions — temperature inside
    ``[temp_min_c, temp_max_c]``, humidity at or above ``humidity_pct_min``, and
    leaf wetness at or above ``leaf_wetness_hours_min`` — and counts how many hold.
    """

    name: str
    temp_min_c: float
    temp_max_c: float
    humidity_pct_min: float
    leaf_wetness_hours_min: float


@dataclass(frozen=True)
class Crop:
    """A crop: its stages' profiles and its key disease rule."""

    key: str
    name: str
    scientific_name: str
    stages: dict[GrowthStage, StageProfile]
    disease: DiseaseRisk

    def stage(self, stage: GrowthStage) -> StageProfile:
        try:
            return self.stages[stage]
        except KeyError as exc:  # pragma: no cover - guarded by the service layer
            raise KeyError(f"{self.name} has no profile for stage {stage!r}") from exc
