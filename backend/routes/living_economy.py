"""
SparkLabs Backend - Living Economy Director Routes

REST endpoints for the Engine Living Economy Director.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterGoodRequest(BaseModel):
    good_id: str
    kind: str = "staple"                    # staple/luxury/material/tool/curiosity
    initial_supply: float = 0.3             # 0.0-1.0
    initial_demand: float = 0.3             # 0.0-1.0


class RegisterProducerRequest(BaseModel):
    producer_id: str
    archetype: str = "grower"               # grower/artisan/miner/smith/scavenger
    output_good_id: str
    input_good_ids: Optional[List[str]] = None
    productivity: float = 0.5               # 0.0-1.0


class RegisterParticipantRequest(BaseModel):
    participant_id: str
    role: str = "broker"                    # buyer/seller/broker
    liquidity: float = 0.5                  # 0.0-1.0


class SetNeedRequest(BaseModel):
    participant_id: str
    good_id: str
    level: float                            # 0.0-1.0


class SetSurplusRequest(BaseModel):
    participant_id: str
    good_id: str
    level: float                            # 0.0-1.0


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/living-economy/goods")
async def economy_register_good(req: RegisterGoodRequest):
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector, GoodKind,
    )
    director = EngineLivingEconomyDirector.get_instance()
    try:
        kind = GoodKind(req.kind)
    except ValueError:
        return {"status": "error", "detail": f"Invalid kind: {req.kind}"}
    result = director.register_good(
        good_id=req.good_id,
        kind=kind,
        initial_supply=req.initial_supply,
        initial_demand=req.initial_demand,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/living-economy/producers")
async def economy_register_producer(req: RegisterProducerRequest):
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector, ProducerArchetype,
    )
    director = EngineLivingEconomyDirector.get_instance()
    try:
        archetype = ProducerArchetype(req.archetype)
    except ValueError:
        return {"status": "error", "detail": f"Invalid archetype: {req.archetype}"}
    result = director.register_producer(
        producer_id=req.producer_id,
        archetype=archetype,
        output_good_id=req.output_good_id,
        input_good_ids=req.input_good_ids,
        productivity=req.productivity,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/living-economy/participants")
async def economy_register_participant(req: RegisterParticipantRequest):
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector, ExchangeRole,
    )
    director = EngineLivingEconomyDirector.get_instance()
    try:
        role = ExchangeRole(req.role)
    except ValueError:
        return {"status": "error", "detail": f"Invalid role: {req.role}"}
    result = director.register_participant(
        participant_id=req.participant_id,
        role=role,
        liquidity=req.liquidity,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/living-economy/needs")
async def economy_set_need(req: SetNeedRequest):
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector,
    )
    director = EngineLivingEconomyDirector.get_instance()
    result = director.set_participant_need(
        participant_id=req.participant_id,
        good_id=req.good_id,
        level=req.level,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/living-economy/surpluses")
async def economy_set_surplus(req: SetSurplusRequest):
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector,
    )
    director = EngineLivingEconomyDirector.get_instance()
    result = director.set_participant_surplus(
        participant_id=req.participant_id,
        good_id=req.good_id,
        level=req.level,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/living-economy/goods")
async def economy_get_goods(limit: int = 30):
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector,
    )
    director = EngineLivingEconomyDirector.get_instance()
    return {"status": "ok", "data": director.get_goods(limit=limit)}


@router.get("/living-economy/goods/{good_id}")
async def economy_get_good(good_id: str):
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector,
    )
    director = EngineLivingEconomyDirector.get_instance()
    result = director.get_good(good_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/living-economy/producers/{producer_id}")
async def economy_get_producer(producer_id: str):
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector,
    )
    director = EngineLivingEconomyDirector.get_instance()
    result = director.get_producer(producer_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/living-economy/participants/{participant_id}")
async def economy_get_participant(participant_id: str):
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector,
    )
    director = EngineLivingEconomyDirector.get_instance()
    result = director.get_participant(participant_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/living-economy/exchanges")
async def economy_get_exchanges(limit: int = 30):
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector,
    )
    director = EngineLivingEconomyDirector.get_instance()
    return {"status": "ok", "data": director.get_exchanges(limit=limit)}


@router.get("/living-economy/events")
async def economy_get_events(limit: int = 50):
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector,
    )
    director = EngineLivingEconomyDirector.get_instance()
    return {"status": "ok", "data": director.get_events_log(limit=limit)}


@router.get("/living-economy/status")
async def economy_get_status():
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector,
    )
    director = EngineLivingEconomyDirector.get_instance()
    return {"status": "ok", "data": director.get_status()}


@router.post("/living-economy/cycle")
async def economy_cycle():
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector,
    )
    director = EngineLivingEconomyDirector.get_instance()
    return {"status": "ok", "data": director.cycle()}


@router.post("/living-economy/simulate")
async def economy_simulate(req: SimulateRequest):
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector,
    )
    director = EngineLivingEconomyDirector.get_instance()
    return {"status": "ok", "data": director.simulate(cycles=req.cycles)}


@router.post("/living-economy/reset")
async def economy_reset():
    from sparkai.engine.engine_living_economy_director import (
        EngineLivingEconomyDirector,
    )
    director = EngineLivingEconomyDirector.get_instance()
    return {"status": "ok", "data": director.reset()}
