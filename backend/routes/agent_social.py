"""
SparkLabs Backend - Social Cognition Routes

API endpoints for social cognition including
relationship management, reputation tracking,
and theory of mind simulation.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# In-memory storage for social data
_relationships: Dict[str, Dict[str, Any]] = {}
_reputations: Dict[str, Dict[str, Any]] = {}
_theory_of_mind_simulations: Dict[str, Dict[str, Any]] = {}


class RelationshipRequest(BaseModel):
    agent_id: str
    target_id: str
    relationship_type: str = "neutral"
    affinity: float = 0.0
    trust: float = 0.5
    familiarity: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class ReputationRequest(BaseModel):
    agent_id: str
    reputation_score: float = 0.5
    traits: Optional[Dict[str, float]] = None
    source: str = "observation"
    metadata: Optional[Dict[str, Any]] = None


class TheoryOfMindRequest(BaseModel):
    agent_id: str
    target_id: str
    context: Optional[Dict[str, Any]] = None


@router.post("/social/relationship")
async def manage_relationship(request: RelationshipRequest):
    try:
        rel_id = f"{request.agent_id}:{request.target_id}"
        timestamp = datetime.utcnow().isoformat()

        if rel_id in _relationships:
            rel = _relationships[rel_id]
            rel["relationship_type"] = request.relationship_type
            rel["affinity"] = request.affinity
            rel["trust"] = request.trust
            rel["familiarity"] = request.familiarity
            if request.metadata:
                rel["metadata"].update(request.metadata)
            rel["updated_at"] = timestamp
            action = "updated"
        else:
            rel = {
                "id": rel_id,
                "agent_id": request.agent_id,
                "target_id": request.target_id,
                "relationship_type": request.relationship_type,
                "affinity": request.affinity,
                "trust": request.trust,
                "familiarity": request.familiarity,
                "metadata": request.metadata or {},
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            _relationships[rel_id] = rel
            action = "created"

        return {
            "status": "success",
            "data": {
                "relationship": rel,
                "action": action,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/social/relationships/{agent_id}")
async def get_agent_relationships(agent_id: str):
    try:
        agent_rels = [
            rel
            for rel in _relationships.values()
            if rel.get("agent_id") == agent_id
        ]

        return {
            "status": "success",
            "data": {
                "agent_id": agent_id,
                "relationships": agent_rels,
                "total_count": len(agent_rels),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/social/reputation")
async def update_reputation(request: ReputationRequest):
    try:
        timestamp = datetime.utcnow().isoformat()

        if request.agent_id in _reputations:
            rep = _reputations[request.agent_id]
            rep["reputation_score"] = request.reputation_score
            if request.traits:
                rep["traits"].update(request.traits)
            rep["sources"].append(request.source)
            rep["updated_at"] = timestamp
            action = "updated"
        else:
            rep = {
                "agent_id": request.agent_id,
                "reputation_score": request.reputation_score,
                "traits": request.traits or {},
                "sources": [request.source],
                "metadata": request.metadata or {},
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            _reputations[request.agent_id] = rep
            action = "created"

        return {
            "status": "success",
            "data": {
                "reputation": rep,
                "action": action,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/social/reputation/{agent_id}")
async def get_reputation(agent_id: str):
    try:
        reputation = _reputations.get(agent_id)
        if reputation:
            return {"status": "success", "data": reputation}
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Reputation not found for agent"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/social/theory-of-mind")
async def run_theory_of_mind(request: TheoryOfMindRequest):
    try:
        sim_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        rel_id = f"{request.agent_id}:{request.target_id}"
        relationship = _relationships.get(rel_id, {})

        simulation = {
            "id": sim_id,
            "agent_id": request.agent_id,
            "target_id": request.target_id,
            "context": request.context or {},
            "estimated_beliefs": {
                "trust_level": relationship.get("trust", 0.5),
                "perceived_intent": "neutral",
                "emotional_state": "calm",
                "goal_alignment": 0.5,
            },
            "predicted_actions": [
                {"action": "approach", "probability": 0.6},
                {"action": "observe", "probability": 0.3},
                {"action": "avoid", "probability": 0.1},
            ],
            "confidence": 0.75,
            "created_at": timestamp,
        }

        _theory_of_mind_simulations[sim_id] = simulation

        return {"status": "success", "data": simulation}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )