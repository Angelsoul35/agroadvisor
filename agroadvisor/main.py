"""AgroAdvisor HTTP API."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .engine import SoilTest, Weather
from .service import AdvisorService

app = FastAPI(
    title="AgroAdvisor",
    version="1.0.0",
    summary="Deterministic agronomy engine with an LLM phrasing layer.",
)

_service: AdvisorService | None = None


def get_service() -> AdvisorService:
    global _service
    if _service is None:
        _service = AdvisorService()
    return _service


class SoilModel(BaseModel):
    n_kg_ha: float = Field(ge=0)
    p_kg_ha: float = Field(ge=0)
    k_kg_ha: float = Field(ge=0)


class WeatherModel(BaseModel):
    et0_mm: float = Field(ge=0)
    rainfall_mm: float = Field(ge=0)
    temperature_c: float
    humidity_pct: float = Field(ge=0, le=100)
    leaf_wetness_hours: float = Field(ge=0, le=24)


class AdviseRequest(BaseModel):
    crop: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    soil: SoilModel
    weather: WeatherModel


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/crops", tags=["reference"])
def crops() -> dict:
    kb = get_service().knowledge
    return {"crops": kb.crops(), "stages": [s.value for s in kb.stages()]}


@app.post("/advise", tags=["advisory"])
def advise(request: AdviseRequest) -> dict:
    soil = SoilTest(**request.soil.model_dump())
    weather = Weather(**request.weather.model_dump())
    try:
        return get_service().advise(request.crop, request.stage, soil, weather)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
