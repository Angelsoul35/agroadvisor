"""The crop knowledge base: a small set of documented, *illustrative* reference values.

IMPORTANT — these numbers are illustrative teaching values, **not** calibrated for
any real region, cultivar, soil or season. The crop coefficients are rounded from
published FAO-56 ranges; the NPK stage targets and the disease weather bands are
plausible order-of-magnitude figures chosen so the engine's arithmetic is easy to
follow and verify. A real advisory product must replace this file with locally
calibrated data reviewed by an agronomist (see the scope note in the README).

What the knowledge base does *not* do is make any recommendation. It only supplies
the per-crop, per-stage constants; the deterministic maths lives in
:mod:`agroadvisor.engine`.
"""

from __future__ import annotations

from .crops import Crop, DiseaseRisk, GrowthStage, StageProfile

GS = GrowthStage

# ---------------------------------------------------------------------------
# Reference crops. Kc values are rounded from FAO-56 Irrigation & Drainage
# Paper 56 ranges; NPK stage targets (kg/ha) and disease bands are illustrative.
# ---------------------------------------------------------------------------

# StageProfile positional order is (kc, N target, P target, K target); targets in kg/ha.
_CROPS: dict[str, Crop] = {
    "maize": Crop(
        key="maize",
        name="Maize",
        scientific_name="Zea mays",
        stages={
            GS.INITIAL: StageProfile(0.30, 40, 20, 20),
            GS.VEGETATIVE: StageProfile(0.70, 120, 40, 60),
            GS.FLOWERING: StageProfile(1.20, 180, 60, 90),
            GS.MATURITY: StageProfile(0.60, 60, 30, 40),
        },
        disease=DiseaseRisk(
            name="Northern corn leaf blight",
            temp_min_c=18.0,
            temp_max_c=27.0,
            humidity_pct_min=85.0,
            leaf_wetness_hours_min=6.0,
        ),
    ),
    "tomato": Crop(
        key="tomato",
        name="Tomato",
        scientific_name="Solanum lycopersicum",
        stages={
            GS.INITIAL: StageProfile(0.60, 30, 40, 40),
            GS.VEGETATIVE: StageProfile(0.75, 80, 50, 80),
            GS.FLOWERING: StageProfile(1.15, 120, 60, 160),
            GS.MATURITY: StageProfile(0.80, 90, 40, 140),
        },
        disease=DiseaseRisk(
            name="Late blight (Phytophthora infestans)",
            temp_min_c=10.0,
            temp_max_c=24.0,
            humidity_pct_min=90.0,
            leaf_wetness_hours_min=8.0,
        ),
    ),
    "wheat": Crop(
        key="wheat",
        name="Wheat",
        scientific_name="Triticum aestivum",
        stages={
            GS.INITIAL: StageProfile(0.30, 30, 20, 20),
            GS.VEGETATIVE: StageProfile(0.70, 100, 40, 40),
            GS.FLOWERING: StageProfile(1.15, 150, 60, 60),
            GS.MATURITY: StageProfile(0.40, 40, 20, 20),
        },
        disease=DiseaseRisk(
            name="Fusarium head blight",
            temp_min_c=15.0,
            temp_max_c=25.0,
            humidity_pct_min=80.0,
            leaf_wetness_hours_min=6.0,
        ),
    ),
}


class KnowledgeBase:
    """Read-only access to the reference crops keyed by a short name."""

    def __init__(self, crops: dict[str, Crop] | None = None) -> None:
        self._crops = crops if crops is not None else dict(_CROPS)

    def crops(self) -> list[str]:
        """The available crop keys, sorted (``maize``, ``tomato``, ``wheat``)."""
        return sorted(self._crops)

    def get(self, key: str) -> Crop:
        """Look up a crop by key, case-insensitively."""
        normalised = key.strip().lower()
        if normalised not in self._crops:
            known = ", ".join(self.crops())
            raise KeyError(f"unknown crop {key!r} (known: {known})")
        return self._crops[normalised]

    def stages(self) -> list[GrowthStage]:
        """The growth stages the engine understands, in developmental order."""
        return list(GrowthStage)
