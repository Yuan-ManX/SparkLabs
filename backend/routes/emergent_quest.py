"""
SparkLabs Backend - Emergent Quest Composer Routes

REST endpoints for the Engine Emergent Quest Composer.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterRegionRequest(BaseModel):
    region_id: str


class SenseShiftRequest(BaseModel):
    region_id: str
    shift_id: str
    kind: str = "threat"                    # shortage/surplus/debt/grievance/opportunity/threat
    magnitude: float = 0.5                  # 0.0-1.0
    note: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/emergent-quest/regions")
async def quest_register_region(req: RegisterRegionRequest):
    from sparkai.engine.engine_emergent_quest_composer import (
        EngineEmergentQuestComposer,
    )
    composer = EngineEmergentQuestComposer.get_instance()
    result = composer.register_region(region_id=req.region_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/emergent-quest/shifts")
async def quest_sense_shift(req: SenseShiftRequest):
    from sparkai.engine.engine_emergent_quest_composer import (
        EngineEmergentQuestComposer, ShiftKind,
    )
    composer = EngineEmergentQuestComposer.get_instance()
    try:
        kind = ShiftKind(req.kind)
    except ValueError:
        return {"status": "error", "detail": f"Invalid kind: {req.kind}"}
    result = composer.sense_shift(
        region_id=req.region_id,
        shift_id=req.shift_id,
        kind=kind,
        magnitude=req.magnitude,
        note=req.note,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/emergent-quest/regions/{region_id}")
async def quest_get_region_state(region_id: str):
    from sparkai.engine.engine_emergent_quest_composer import (
        EngineEmergentQuestComposer,
    )
    composer = EngineEmergentQuestComposer.get_instance()
    result = composer.get_region_state(region_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/emergent-quest/regions/{region_id}/quests")
async def quest_get_quests(region_id: str, limit: int = 20):
    from sparkai.engine.engine_emergent_quest_composer import (
        EngineEmergentQuestComposer,
    )
    composer = EngineEmergentQuestComposer.get_instance()
    result = composer.get_quests(region_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/emergent-quest/regions/{region_id}/quests/{quest_id}")
async def quest_get_quest(region_id: str, quest_id: str):
    from sparkai.engine.engine_emergent_quest_composer import (
        EngineEmergentQuestComposer,
    )
    composer = EngineEmergentQuestComposer.get_instance()
    result = composer.get_quest(region_id, quest_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/emergent-quest/regions/{region_id}/pressures")
async def quest_get_pressures(region_id: str, limit: int = 30):
    from sparkai.engine.engine_emergent_quest_composer import (
        EngineEmergentQuestComposer,
    )
    composer = EngineEmergentQuestComposer.get_instance()
    result = composer.get_pressures(region_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/emergent-quest/events")
async def quest_get_events(limit: int = 50):
    from sparkai.engine.engine_emergent_quest_composer import (
        EngineEmergentQuestComposer,
    )
    composer = EngineEmergentQuestComposer.get_instance()
    return {"status": "ok", "data": composer.get_events_log(limit=limit)}


@router.get("/emergent-quest/status")
async def quest_get_status():
    from sparkai.engine.engine_emergent_quest_composer import (
        EngineEmergentQuestComposer,
    )
    composer = EngineEmergentQuestComposer.get_instance()
    return {"status": "ok", "data": composer.get_status()}


@router.post("/emergent-quest/cycle")
async def quest_cycle():
    from sparkai.engine.engine_emergent_quest_composer import (
        EngineEmergentQuestComposer,
    )
    composer = EngineEmergentQuestComposer.get_instance()
    return {"status": "ok", "data": composer.cycle()}


@router.post("/emergent-quest/simulate")
async def quest_simulate(req: SimulateRequest):
    from sparkai.engine.engine_emergent_quest_composer import (
        EngineEmergentQuestComposer,
    )
    composer = EngineEmergentQuestComposer.get_instance()
    return {"status": "ok", "data": composer.simulate(cycles=req.cycles)}


@router.post("/emergent-quest/reset")
async def quest_reset():
    from sparkai.engine.engine_emergent_quest_composer import (
        EngineEmergentQuestComposer,
    )
    composer = EngineEmergentQuestComposer.get_instance()
    return {"status": "ok", "data": composer.reset()}
