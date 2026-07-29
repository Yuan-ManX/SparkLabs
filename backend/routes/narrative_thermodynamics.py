"""
SparkLabs Backend - Narrative Thermodynamics Routes

REST endpoints for the Engine Narrative Thermodynamics.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class AddStoryRequest(BaseModel):
    node_id: str
    label: str
    genre: str = "drama"              # comedy/drama/tragedy/mystery/horror/adventure/romance/epic
    energy: float = 0.3
    temperature: float = 0.3
    x: float = 0.5
    y: float = 0.5
    energy_profile: Optional[Dict[str, float]] = None


class LinkStoriesRequest(BaseModel):
    node_a: str
    node_b: str


class InjectEnergyRequest(BaseModel):
    energy_type: str                  # tension/emotion/mystery/action/revelation/bonding/dread/hope
    amount: float = 0.3


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/narrative-thermo/stories")
async def thermo_add_story(req: AddStoryRequest):
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics, NarrativeGenre,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    try:
        genre = NarrativeGenre(req.genre)
    except ValueError:
        return {"status": "error", "detail": f"Invalid genre: {req.genre}"}
    result = thermo.add_story(
        node_id=req.node_id,
        label=req.label,
        genre=genre,
        energy=req.energy,
        temperature=req.temperature,
        x=req.x,
        y=req.y,
        energy_profile=req.energy_profile,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/narrative-thermo/stories/{node_id}")
async def thermo_remove_story(node_id: str):
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    result = thermo.remove_story(node_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/narrative-thermo/stories/link")
async def thermo_link_stories(req: LinkStoriesRequest):
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    result = thermo.link_stories(req.node_a, req.node_b)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/narrative-thermo/stories/unlink")
async def thermo_unlink_stories(req: LinkStoriesRequest):
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    result = thermo.unlink_stories(req.node_a, req.node_b)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/narrative-thermo/stories/{node_id}/energy")
async def thermo_inject_energy(node_id: str, req: InjectEnergyRequest):
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    result = thermo.inject_energy(node_id, req.energy_type, req.amount)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/narrative-thermo/stories")
async def thermo_get_all_stories():
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    return {"status": "ok", "data": thermo.get_all_stories()}


@router.get("/narrative-thermo/stories/{node_id}")
async def thermo_get_story(node_id: str):
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    result = thermo.get_story(node_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/narrative-thermo/transitions")
async def thermo_get_transitions(limit: int = 20):
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    return {"status": "ok", "data": thermo.get_transitions(limit)}


@router.get("/narrative-thermo/currents")
async def thermo_get_currents(limit: int = 20):
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    return {"status": "ok", "data": thermo.get_currents(limit)}


@router.get("/narrative-thermo/entropy-events")
async def thermo_get_entropy_events(limit: int = 20):
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    return {"status": "ok", "data": thermo.get_entropy_events(limit)}


@router.post("/narrative-thermo/cycle")
async def thermo_cycle():
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    return {"status": "ok", "data": thermo.cycle()}


@router.post("/narrative-thermo/simulate")
async def thermo_simulate(req: SimulateRequest):
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    return {"status": "ok", "data": thermo.simulate(req.cycles)}


@router.get("/narrative-thermo/events")
async def thermo_get_events(limit: int = 50):
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    return {"status": "ok", "data": thermo.get_events_log(limit)}


@router.get("/narrative-thermo/status")
async def thermo_status():
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    return {"status": "ok", "data": thermo.get_status()}


@router.post("/narrative-thermo/reset")
async def thermo_reset():
    from sparkai.engine.engine_narrative_thermodynamics import (
        EngineNarrativeThermodynamics,
    )
    thermo = EngineNarrativeThermodynamics.get_instance()
    return {"status": "ok", "data": thermo.reset()}
