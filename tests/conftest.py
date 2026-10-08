from __future__ import annotations

import pytest

from agroadvisor.engine import SoilTest, Weather
from agroadvisor.knowledge import KnowledgeBase


@pytest.fixture
def knowledge() -> KnowledgeBase:
    return KnowledgeBase()


@pytest.fixture
def dry_maize_soil() -> SoilTest:
    return SoilTest(n_kg_ha=50, p_kg_ha=15, k_kg_ha=30)


@pytest.fixture
def dry_maize_weather() -> Weather:
    # A hot, dry spell: high ET0, little rain, no disease weather.
    return Weather(
        et0_mm=6.5,
        rainfall_mm=2.0,
        temperature_c=30.0,
        humidity_pct=50.0,
        leaf_wetness_hours=2.0,
    )
