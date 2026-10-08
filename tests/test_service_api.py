from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agroadvisor import main
from agroadvisor.engine import SoilTest, Weather
from agroadvisor.llm.fake import FailingLLM
from agroadvisor.service import AdvisorService


@pytest.fixture(autouse=True)
def offline_service():
    # Force the offline template path so no test ever touches the network.
    main._service = AdvisorService(llm=FailingLLM())
    yield
    main._service = None


client = TestClient(main.app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_crops_lists_reference_data():
    body = client.get("/crops").json()
    assert body["crops"] == ["maize", "tomato", "wheat"]
    assert "vegetative" in body["stages"]


def test_advise_returns_structured_recommendation_and_advisory():
    r = client.post(
        "/advise",
        json={
            "crop": "maize",
            "stage": "vegetative",
            "soil": {"n_kg_ha": 50, "p_kg_ha": 15, "k_kg_ha": 30},
            "weather": {
                "et0_mm": 6.5,
                "rainfall_mm": 2.0,
                "temperature_c": 30.0,
                "humidity_pct": 50.0,
                "leaf_wetness_hours": 2.0,
            },
        },
    )
    assert r.status_code == 200
    body = r.json()
    # The structured, computed substance is present and correct (2.95 mm, see engine tests).
    assert body["recommendation"]["irrigation"]["net_irrigation_mm"] == 2.95
    assert body["advisory_source"] == "template"
    assert "2.95" in body["advisory"]


def test_advise_rejects_unknown_crop():
    r = client.post(
        "/advise",
        json={
            "crop": "banana",
            "stage": "vegetative",
            "soil": {"n_kg_ha": 1, "p_kg_ha": 1, "k_kg_ha": 1},
            "weather": {
                "et0_mm": 5.0,
                "rainfall_mm": 0.0,
                "temperature_c": 20.0,
                "humidity_pct": 50.0,
                "leaf_wetness_hours": 0.0,
            },
        },
    )
    assert r.status_code == 422


def test_service_advise_matches_engine_directly():
    service = AdvisorService(llm=FailingLLM())
    soil = SoilTest(n_kg_ha=50, p_kg_ha=15, k_kg_ha=30)
    weather = Weather(
        et0_mm=6.5, rainfall_mm=2.0, temperature_c=30.0, humidity_pct=50.0, leaf_wetness_hours=2.0
    )
    out = service.advise("maize", "vegetative", soil, weather)
    assert out["recommendation"]["stage"] == "vegetative"
    assert out["advisory_source"] == "template"
