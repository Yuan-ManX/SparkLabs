"""
SparkLabs Backend - Semantic World Indexer & Predictive State Prefetcher Routes

REST API endpoints for:
  - AgentSemanticWorldIndexer: semantic world graph indexing and querying
  - EnginePredictiveStatePrefetcher: AI-driven predictive resource prefetching

Routes use /semantic-indexer/ and /predictive-prefetcher/ prefixes.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class SimulateRequest(BaseModel):
    cycles: int = 10


class RegisterEntityRequest(BaseModel):
    entity_id: str
    name: str
    category: str
    position: Optional[List[float]] = None
    tags: Optional[List[str]] = None
    properties: Optional[Dict[str, Any]] = None
    semantic_roles: Optional[List[str]] = None


class AddRelationRequest(BaseModel):
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    metadata: Optional[Dict[str, Any]] = None


class SemanticQueryRequest(BaseModel):
    intent: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    near_entity: Optional[str] = None
    near_radius: Optional[float] = None
    has_role: Optional[str] = None
    limit: int = 20


class QueryRelationsRequest(BaseModel):
    entity_id: str
    direction: str = "both"
    relation_type: Optional[str] = None
    limit: int = 20


class FindPathRequest(BaseModel):
    source_id: str
    target_id: str
    max_depth: int = 4


class ObserveRequest(BaseModel):
    position: List[float]
    velocity: List[float]
    activity: str
    facing: float = 0.0
    health_pct: float = 1.0
    target_entity: Optional[str] = None


# =============================================================================
# Semantic World Indexer Routes
# =============================================================================

@router.get("/semantic-indexer/status")
async def semantic_status():
    from sparkai.agent.agent_semantic_world_indexer import AgentSemanticWorldIndexer
    indexer = AgentSemanticWorldIndexer.get_instance()
    return {"status": "ok", "data": indexer.get_status()}


@router.post("/semantic-indexer/entities")
async def semantic_register_entity(req: RegisterEntityRequest):
    from sparkai.agent.agent_semantic_world_indexer import AgentSemanticWorldIndexer
    indexer = AgentSemanticWorldIndexer.get_instance()
    pos = tuple(req.position) if req.position else None
    result = indexer.register_entity(
        entity_id=req.entity_id,
        name=req.name,
        category=req.category,
        position=pos,
        tags=req.tags,
        properties=req.properties,
        semantic_roles=req.semantic_roles,
    )
    return {"status": "ok", "data": result}


@router.delete("/semantic-indexer/entities/{entity_id}")
async def semantic_remove_entity(entity_id: str):
    from sparkai.agent.agent_semantic_world_indexer import AgentSemanticWorldIndexer
    indexer = AgentSemanticWorldIndexer.get_instance()
    removed = indexer.remove_entity(entity_id)
    return {"status": "ok" if removed else "error", "removed": removed}


@router.post("/semantic-indexer/relations")
async def semantic_add_relation(req: AddRelationRequest):
    from sparkai.agent.agent_semantic_world_indexer import AgentSemanticWorldIndexer
    indexer = AgentSemanticWorldIndexer.get_instance()
    result = indexer.add_relation(
        req.source_id, req.target_id, req.relation,
        req.weight, req.metadata,
    )
    return {"status": "ok" if "error" not in result else "error", "data": result}


@router.post("/semantic-indexer/query")
async def semantic_query(req: SemanticQueryRequest):
    from sparkai.agent.agent_semantic_world_indexer import AgentSemanticWorldIndexer
    indexer = AgentSemanticWorldIndexer.get_instance()
    result = indexer.query(
        intent=req.intent,
        category=req.category,
        tags=req.tags,
        near_entity=req.near_entity,
        near_radius=req.near_radius,
        has_role=req.has_role,
        limit=req.limit,
    )
    return {"status": "ok", "data": result}


@router.post("/semantic-indexer/relations/query")
async def semantic_query_relations(req: QueryRelationsRequest):
    from sparkai.agent.agent_semantic_world_indexer import AgentSemanticWorldIndexer
    indexer = AgentSemanticWorldIndexer.get_instance()
    result = indexer.query_relations(
        req.entity_id, req.direction, req.relation_type, req.limit,
    )
    return {"status": "ok" if "error" not in result else "error", "data": result}


@router.post("/semantic-indexer/path")
async def semantic_find_path(req: FindPathRequest):
    from sparkai.agent.agent_semantic_world_indexer import AgentSemanticWorldIndexer
    indexer = AgentSemanticWorldIndexer.get_instance()
    result = indexer.find_path(req.source_id, req.target_id, req.max_depth)
    return {"status": "ok" if "error" not in result else "error", "data": result}


@router.get("/semantic-indexer/entities")
async def semantic_get_entities(
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
):
    from sparkai.agent.agent_semantic_world_indexer import AgentSemanticWorldIndexer
    indexer = AgentSemanticWorldIndexer.get_instance()
    return {"status": "ok", "data": indexer.get_entities(limit, category)}


@router.get("/semantic-indexer/relations")
async def semantic_get_relations(limit: int = Query(20, ge=1, le=100)):
    from sparkai.agent.agent_semantic_world_indexer import AgentSemanticWorldIndexer
    indexer = AgentSemanticWorldIndexer.get_instance()
    return {"status": "ok", "data": indexer.get_relations(limit)}


@router.get("/semantic-indexer/queries")
async def semantic_get_queries(limit: int = Query(20, ge=1, le=100)):
    from sparkai.agent.agent_semantic_world_indexer import AgentSemanticWorldIndexer
    indexer = AgentSemanticWorldIndexer.get_instance()
    return {"status": "ok", "data": indexer.get_queries(limit)}


@router.post("/semantic-indexer/cycle")
async def semantic_cycle():
    from sparkai.agent.agent_semantic_world_indexer import AgentSemanticWorldIndexer
    indexer = AgentSemanticWorldIndexer.get_instance()
    return {"status": "ok", "data": indexer.run_cycle()}


@router.post("/semantic-indexer/simulate")
async def semantic_simulate(req: SimulateRequest):
    from sparkai.agent.agent_semantic_world_indexer import AgentSemanticWorldIndexer
    indexer = AgentSemanticWorldIndexer.get_instance()
    return {"status": "ok", "data": indexer.simulate(req.cycles)}


@router.post("/semantic-indexer/reset")
async def semantic_reset():
    from sparkai.agent.agent_semantic_world_indexer import AgentSemanticWorldIndexer
    indexer = AgentSemanticWorldIndexer.get_instance()
    return {"status": "ok", "data": indexer.reset()}


# =============================================================================
# Predictive State Prefetcher Routes
# =============================================================================

@router.get("/predictive-prefetcher/status")
async def prefetch_status():
    from sparkai.engine.engine_predictive_state_prefetcher import EnginePredictiveStatePrefetcher
    pf = EnginePredictiveStatePrefetcher.get_instance()
    return {"status": "ok", "data": pf.get_status()}


@router.post("/predictive-prefetcher/observe")
async def prefetch_observe(req: ObserveRequest):
    from sparkai.engine.engine_predictive_state_prefetcher import EnginePredictiveStatePrefetcher
    pf = EnginePredictiveStatePrefetcher.get_instance()
    result = pf.observe(
        position=tuple(req.position),
        velocity=tuple(req.velocity),
        activity=req.activity,
        facing=req.facing,
        health_pct=req.health_pct,
        target_entity=req.target_entity,
    )
    return {"status": "ok", "data": result}


@router.post("/predictive-prefetcher/predict")
async def prefetch_predict():
    from sparkai.engine.engine_predictive_state_prefetcher import EnginePredictiveStatePrefetcher
    pf = EnginePredictiveStatePrefetcher.get_instance()
    return {"status": "ok", "data": pf.predict()}


@router.post("/predictive-prefetcher/prefetch")
async def prefetch_execute():
    from sparkai.engine.engine_predictive_state_prefetcher import EnginePredictiveStatePrefetcher
    pf = EnginePredictiveStatePrefetcher.get_instance()
    return {"status": "ok", "data": pf.prefetch()}


@router.post("/predictive-prefetcher/verify")
async def prefetch_verify():
    from sparkai.engine.engine_predictive_state_prefetcher import EnginePredictiveStatePrefetcher
    pf = EnginePredictiveStatePrefetcher.get_instance()
    return {"status": "ok", "data": pf.verify()}


@router.post("/predictive-prefetcher/cycle")
async def prefetch_cycle():
    from sparkai.engine.engine_predictive_state_prefetcher import EnginePredictiveStatePrefetcher
    pf = EnginePredictiveStatePrefetcher.get_instance()
    return {"status": "ok", "data": pf.run_cycle()}


@router.post("/predictive-prefetcher/simulate")
async def prefetch_simulate(req: SimulateRequest):
    from sparkai.engine.engine_predictive_state_prefetcher import EnginePredictiveStatePrefetcher
    pf = EnginePredictiveStatePrefetcher.get_instance()
    return {"status": "ok", "data": pf.simulate(req.cycles)}


@router.get("/predictive-prefetcher/predictions")
async def prefetch_predictions(limit: int = Query(20, ge=1, le=100)):
    from sparkai.engine.engine_predictive_state_prefetcher import EnginePredictiveStatePrefetcher
    pf = EnginePredictiveStatePrefetcher.get_instance()
    return {"status": "ok", "data": pf.get_predictions(limit)}


@router.get("/predictive-prefetcher/prefetches")
async def prefetch_requests(limit: int = Query(20, ge=1, le=100)):
    from sparkai.engine.engine_predictive_state_prefetcher import EnginePredictiveStatePrefetcher
    pf = EnginePredictiveStatePrefetcher.get_instance()
    return {"status": "ok", "data": pf.get_prefetches(limit)}


@router.get("/predictive-prefetcher/trajectory")
async def prefetch_trajectory(limit: int = Query(30, ge=1, le=60)):
    from sparkai.engine.engine_predictive_state_prefetcher import EnginePredictiveStatePrefetcher
    pf = EnginePredictiveStatePrefetcher.get_instance()
    return {"status": "ok", "data": pf.get_player_trajectory(limit)}


@router.delete("/predictive-prefetcher/prefetches/{request_id}")
async def prefetch_cancel(request_id: str):
    from sparkai.engine.engine_predictive_state_prefetcher import EnginePredictiveStatePrefetcher
    pf = EnginePredictiveStatePrefetcher.get_instance()
    cancelled = pf.cancel_prefetch(request_id)
    return {"status": "ok" if cancelled else "error", "cancelled": cancelled}


@router.post("/predictive-prefetcher/reset")
async def prefetch_reset():
    from sparkai.engine.engine_predictive_state_prefetcher import EnginePredictiveStatePrefetcher
    pf = EnginePredictiveStatePrefetcher.get_instance()
    return {"status": "ok", "data": pf.reset()}
