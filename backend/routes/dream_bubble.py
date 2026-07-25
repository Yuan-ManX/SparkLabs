"""
SparkLabs Backend - Memory Dream Consolidator & Reality Bubble Projector Routes

REST API endpoints for:
  - AgentMemoryDreamConsolidator: episodic-to-semantic memory consolidation
  - EngineRealityBubbleProjector: probabilistic reality bubble management

Routes use /dream-consolidator/ and /reality-bubble/ prefixes.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models - Dream Consolidator
# =============================================================================

class SimulateDreamRequest(BaseModel):
    cycles: int = 5


class RecordEpisodeRequest(BaseModel):
    scene: str
    actors: List[str]
    action: str
    outcome: str
    valence: str = "neutral"
    salience: str = "ordinary"
    emotional_weight: float = 0.3
    tags: Optional[List[str]] = None


class QueryKnowledgeRequest(BaseModel):
    knowledge_type: Optional[str] = None
    min_confidence: float = 0.0
    tag: Optional[str] = None
    limit: int = 20


class QueryByActorRequest(BaseModel):
    actor: str
    limit: int = 20


class QueryBySceneRequest(BaseModel):
    scene: str
    limit: int = 20


# =============================================================================
# Request Models - Reality Bubble Projector
# =============================================================================

class SimulateBubbleRequest(BaseModel):
    cycles: int = 10
    move_player: bool = True


class RegisterBubbleEntityRequest(BaseModel):
    entity_id: str
    name: str
    category: str
    position: List[float]
    importance: float = 0.5
    initial_state: str = "idle"
    tags: Optional[List[str]] = None


class UpdatePlayerRequest(BaseModel):
    position: List[float]
    velocity: Optional[List[float]] = None


class UpdateBubbleConfigRequest(BaseModel):
    core_radius: Optional[float] = None
    shadow_radius: Optional[float] = None
    max_probable_positions: Optional[int] = None
    collapse_cooldown_s: Optional[float] = None
    dissolve_cooldown_s: Optional[float] = None
    propagation_step_s: Optional[float] = None
    importance_bias: Optional[float] = None


class ForceCollapseRequest(BaseModel):
    reason: str = "manual"


# =============================================================================
# Dream Consolidator Routes
# =============================================================================

@router.get("/dream-consolidator/status")
async def dream_status():
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    return {"status": "ok", "data": dreamer.get_status()}


@router.post("/dream-consolidator/episodes")
async def dream_record_episode(req: RecordEpisodeRequest):
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    result = dreamer.record_episode(
        scene=req.scene,
        actors=req.actors,
        action=req.action,
        outcome=req.outcome,
        valence=req.valence,
        salience=req.salience,
        emotional_weight=req.emotional_weight,
        tags=req.tags,
    )
    return {"status": "ok", "data": result}


@router.post("/dream-consolidator/cycle")
async def dream_run_cycle():
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    return {"status": "ok", "data": dreamer.run_cycle()}


@router.post("/dream-consolidator/simulate")
async def dream_simulate(req: SimulateDreamRequest):
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    return {"status": "ok", "data": dreamer.simulate(cycles=req.cycles)}


@router.get("/dream-consolidator/episodic")
async def dream_list_episodic(limit: int = Query(20, ge=1, le=200)):
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    return {"status": "ok", "data": dreamer.list_episodic(limit=limit)}


@router.get("/dream-consolidator/semantic")
async def dream_list_semantic(limit: int = Query(20, ge=1, le=200)):
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    return {"status": "ok", "data": dreamer.list_semantic(limit=limit)}


@router.get("/dream-consolidator/links")
async def dream_list_links(limit: int = Query(20, ge=1, le=200)):
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    return {"status": "ok", "data": dreamer.list_links(limit=limit)}


@router.get("/dream-consolidator/dreams")
async def dream_list_dreams(limit: int = Query(20, ge=1, le=200)):
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    return {"status": "ok", "data": dreamer.list_dreams(limit=limit)}


@router.post("/dream-consolidator/knowledge/query")
async def dream_query_knowledge(req: QueryKnowledgeRequest):
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    result = dreamer.query_knowledge(
        knowledge_type=req.knowledge_type,
        min_confidence=req.min_confidence,
        tag=req.tag,
        limit=req.limit,
    )
    return {"status": "ok", "data": result}


@router.get("/dream-consolidator/knowledge/{knowledge_id}")
async def dream_get_knowledge(knowledge_id: str):
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    result = dreamer.get_knowledge(knowledge_id)
    if result is None:
        return {"status": "error", "message": "Knowledge not found"}
    return {"status": "ok", "data": result}


@router.post("/dream-consolidator/knowledge/{knowledge_id}/reinforce")
async def dream_reinforce_knowledge(knowledge_id: str):
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    return {"status": "ok", "data": dreamer.reinforce_knowledge(knowledge_id)}


@router.post("/dream-consolidator/knowledge/{knowledge_id}/contradict")
async def dream_contradict_knowledge(knowledge_id: str):
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    return {"status": "ok", "data": dreamer.contradict_knowledge(knowledge_id)}


@router.post("/dream-consolidator/query/scene")
async def dream_query_by_scene(req: QueryBySceneRequest):
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    return {"status": "ok", "data": dreamer.query_by_scene(req.scene, req.limit)}


@router.post("/dream-consolidator/query/actor")
async def dream_query_by_actor(req: QueryByActorRequest):
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    return {"status": "ok", "data": dreamer.query_by_actor(req.actor, req.limit)}


@router.post("/dream-consolidator/reset")
async def dream_reset():
    from sparkai.agent.agent_memory_dream_consolidator import AgentMemoryDreamConsolidator
    dreamer = AgentMemoryDreamConsolidator.get_instance()
    return {"status": "ok", "data": dreamer.reset()}


# =============================================================================
# Reality Bubble Projector Routes
# =============================================================================

@router.get("/reality-bubble/status")
async def bubble_status():
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    return {"status": "ok", "data": projector.get_status()}


@router.post("/reality-bubble/entities")
async def bubble_register_entity(req: RegisterBubbleEntityRequest):
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    result = projector.register_entity(
        entity_id=req.entity_id,
        name=req.name,
        category=req.category,
        position=tuple(req.position),
        importance=req.importance,
        initial_state=req.initial_state,
        tags=req.tags,
    )
    return {"status": "ok", "data": result}


@router.delete("/reality-bubble/entities/{entity_id}")
async def bubble_remove_entity(entity_id: str):
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    return {"status": "ok", "data": projector.remove_entity(entity_id)}


@router.post("/reality-bubble/player")
async def bubble_update_player(req: UpdatePlayerRequest):
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    velocity = tuple(req.velocity) if req.velocity else None
    result = projector.update_player(
        position=tuple(req.position),
        velocity=velocity,
    )
    return {"status": "ok", "data": result}


@router.post("/reality-bubble/config")
async def bubble_update_config(req: UpdateBubbleConfigRequest):
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    # Only pass non-None fields
    updates = {k: v for k, v in req.dict().items() if v is not None}
    return {"status": "ok", "data": projector.update_config(**updates)}


@router.post("/reality-bubble/cycle")
async def bubble_run_cycle():
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    return {"status": "ok", "data": projector.run_cycle()}


@router.post("/reality-bubble/simulate")
async def bubble_simulate(req: SimulateBubbleRequest):
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    return {"status": "ok", "data": projector.simulate(cycles=req.cycles, move_player=req.move_player)}


@router.get("/reality-bubble/entities")
async def bubble_list_entities(
    zone: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
):
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    return {"status": "ok", "data": projector.list_entities(zone=zone, limit=limit)}


@router.get("/reality-bubble/entities/{entity_id}")
async def bubble_get_entity(entity_id: str):
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    result = projector.get_entity(entity_id)
    if result is None:
        return {"status": "error", "message": "Entity not found"}
    return {"status": "ok", "data": result}


@router.post("/reality-bubble/entities/{entity_id}/collapse")
async def bubble_force_collapse(entity_id: str, req: ForceCollapseRequest):
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    return {"status": "ok", "data": projector.force_collapse(entity_id, req.reason)}


@router.get("/reality-bubble/observable")
async def bubble_query_observable(radius: Optional[float] = Query(None)):
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    return {"status": "ok", "data": projector.query_observable(radius=radius)}


@router.get("/reality-bubble/superposition")
async def bubble_query_superposition(limit: int = Query(20, ge=1, le=200)):
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    return {"status": "ok", "data": projector.query_superposition(limit=limit)}


@router.get("/reality-bubble/snapshots")
async def bubble_list_snapshots(limit: int = Query(20, ge=1, le=200)):
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    return {"status": "ok", "data": projector.list_snapshots(limit=limit)}


@router.get("/reality-bubble/events")
async def bubble_list_events(limit: int = Query(20, ge=1, le=200)):
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    return {"status": "ok", "data": projector.list_events(limit=limit)}


@router.post("/reality-bubble/reset")
async def bubble_reset():
    from sparkai.engine.engine_reality_bubble_projector import EngineRealityBubbleProjector
    projector = EngineRealityBubbleProjector.get_instance()
    return {"status": "ok", "data": projector.reset()}
