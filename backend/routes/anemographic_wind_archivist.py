"""
SparkLabs Backend - Anemographic Wind Archivist Routes

REST endpoints for the Anemographic Wind Archivist agent.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()  # NO prefix here - prefix added in app.py


# =============================================================================
# Request Models
# =============================================================================

class RegisterWindRequest(BaseModel):
    entity_id: str
    wind_label: str
    note: Optional[str] = None


class SimulateRequest(BaseModel):
    cycles: int = 5


class ArchiveGustsRequest(BaseModel):
    wind_id: Optional[str] = None
    limit: int = 50


# =============================================================================
# Routes
# =============================================================================

@router.post("/anemographic-wind-archivist/register")
async def anemographic_wind_archivist_register(req: RegisterWindRequest):
    from sparkai.agent.agent_anemographic_wind_archivist import (
        AnemographicWindArchivist,
    )
    archivist = AnemographicWindArchivist.get_instance()
    result = archivist.register_wind(
        entity_id=req.entity_id,
        wind_label=req.wind_label,
        note=req.note or "",
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/anemographic-wind-archivist/status")
async def anemographic_wind_archivist_get_status():
    from sparkai.agent.agent_anemographic_wind_archivist import (
        AnemographicWindArchivist,
    )
    archivist = AnemographicWindArchivist.get_instance()
    return {"status": "ok", "data": archivist.get_status()}


@router.get("/anemographic-wind-archivist/list")
async def anemographic_wind_archivist_list(limit: int = 10):
    from sparkai.agent.agent_anemographic_wind_archivist import (
        AnemographicWindArchivist,
    )
    archivist = AnemographicWindArchivist.get_instance()
    return {"status": "ok", "data": archivist.get_winds(limit=limit)}


@router.get("/anemographic-wind-archivist/get-by-id/{wind_id}")
async def anemographic_wind_archivist_get_by_id(wind_id: str):
    from sparkai.agent.agent_anemographic_wind_archivist import (
        AnemographicWindArchivist,
    )
    archivist = AnemographicWindArchivist.get_instance()
    result = archivist.get_wind(wind_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/anemographic-wind-archivist/cycle")
async def anemographic_wind_archivist_cycle():
    from sparkai.agent.agent_anemographic_wind_archivist import (
        AnemographicWindArchivist,
    )
    archivist = AnemographicWindArchivist.get_instance()
    return {"status": "ok", "data": archivist.cycle()}


@router.get("/anemographic-wind-archivist/events")
async def anemographic_wind_archivist_get_events(limit: int = 20):
    from sparkai.agent.agent_anemographic_wind_archivist import (
        AnemographicWindArchivist,
    )
    archivist = AnemographicWindArchivist.get_instance()
    return {"status": "ok", "data": archivist.get_events_log(limit=limit)}


@router.post("/anemographic-wind-archivist/simulate")
async def anemographic_wind_archivist_simulate(req: Optional[SimulateRequest] = None):
    from sparkai.agent.agent_anemographic_wind_archivist import (
        AnemographicWindArchivist,
    )
    archivist = AnemographicWindArchivist.get_instance()
    cycles = req.cycles if req is not None else 5
    return {"status": "ok", "data": archivist.simulate(cycles=cycles)}


@router.post("/anemographic-wind-archivist/reset")
async def anemographic_wind_archivist_reset():
    from sparkai.agent.agent_anemographic_wind_archivist import (
        AnemographicWindArchivist,
    )
    archivist = AnemographicWindArchivist.get_instance()
    return {"status": "ok", "data": archivist.reset()}


# Domain-specific action endpoint: compile an archive manifest of gust records
@router.post("/anemographic-wind-archivist/archive")
async def anemographic_wind_archivist_archive(req: Optional[ArchiveGustsRequest] = None):
    from sparkai.agent.agent_anemographic_wind_archivist import (
        AnemographicWindArchivist,
    )
    archivist = AnemographicWindArchivist.get_instance()
    wind_id = req.wind_id if req is not None else None
    limit = req.limit if req is not None else 50
    result = archivist.archive_gusts(wind_id=wind_id, limit=limit)
    return {"status": "ok", "data": result}
