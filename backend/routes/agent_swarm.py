"""
SparkLabs Backend - Agent Swarm Intelligence Routes

API endpoints for swarm-based multi-agent coordination including
agent registration, consensus protocols, task distribution,
shared knowledge management, and emergent behavior detection.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# In-memory storage for swarm agents
_agents: Dict[str, Dict[str, Any]] = {}
_knowledge_entries: Dict[str, Dict[str, Any]] = {}
_consensus_history: List[Dict[str, Any]] = []
_task_assignments: List[Dict[str, Any]] = []


class RegisterAgentRequest(BaseModel):
    moniker: str
    capabilities: List[str]
    disposition: Dict[str, Any]


class ConsensusRequest(BaseModel):
    proposal: str
    protocol: str = "PLAIN_MAJORITY"
    context: Dict[str, Any] = {}


class TaskDistributeRequest(BaseModel):
    task_description: str
    required_capabilities: List[str]
    priority: float = 0.5


class KnowledgeContributeRequest(BaseModel):
    agent_id: str
    knowledge_type: str
    content: Dict[str, Any]
    confidence: float = 0.8


@router.post("/swarm-intel/register")
async def register_swarm_agent(request: RegisterAgentRequest):
    try:
        agent_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        agent = {
            "id": agent_id,
            "moniker": request.moniker,
            "capabilities": request.capabilities,
            "disposition": request.disposition,
            "status": "active",
            "energy": 1.0,
            "contributions": 0,
            "created_at": timestamp,
            "last_active": timestamp,
        }

        _agents[agent_id] = agent

        return {
            "status": "success",
            "data": {
                "agent_id": agent_id,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/swarm-intel/agents")
async def list_swarm_agents():
    try:
        agents_list = list(_agents.values())

        return {
            "status": "success",
            "data": {
                "agents": agents_list,
                "total_count": len(agents_list),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/swarm-intel/consensus")
async def run_consensus(request: ConsensusRequest):
    try:
        timestamp = datetime.utcnow().isoformat()

        votes: Dict[str, str] = {}
        for agent_id, agent in _agents.items():
            disposition = agent.get("disposition", {})
            agree_bias = disposition.get("agreeableness", 0.5)
            if agree_bias > 0.5:
                votes[agent_id] = "approve"
            elif agree_bias < 0.3:
                votes[agent_id] = "reject"
            else:
                votes[agent_id] = "abstain"

        approve_count = sum(1 for v in votes.values() if v == "approve")
        reject_count = sum(1 for v in votes.values() if v == "reject")
        total_votes = len(votes)
        confidence = approve_count / total_votes if total_votes > 0 else 0.5

        if request.protocol == "PLAIN_MAJORITY":
            decision = "approved" if approve_count > reject_count else "rejected"
        elif request.protocol == "SUPER_MAJORITY":
            decision = "approved" if approve_count > total_votes * 0.67 else "rejected"
        else:
            decision = "approved" if approve_count > reject_count else "rejected"

        consensus_record = {
            "id": str(uuid.uuid4()),
            "proposal": request.proposal,
            "protocol": request.protocol,
            "decision": decision,
            "confidence": confidence,
            "votes": votes,
            "timestamp": timestamp,
        }
        _consensus_history.append(consensus_record)

        return {
            "status": "success",
            "data": {
                "decision": decision,
                "confidence": round(confidence, 4),
                "votes": votes,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/swarm-intel/task-distribute")
async def distribute_task(request: TaskDistributeRequest):
    try:
        timestamp = datetime.utcnow().isoformat()
        assignments: List[Dict[str, Any]] = []

        available_agents = [
            agent for agent in _agents.values()
            if any(cap in agent.get("capabilities", []) for cap in request.required_capabilities)
        ]

        if not available_agents:
            available_agents = list(_agents.values())

        for i, agent in enumerate(available_agents[: len(request.required_capabilities) or 3]):
            assignment = {
                "id": str(uuid.uuid4()),
                "agent_id": agent.get("id"),
                "agent_moniker": agent.get("moniker"),
                "sub_task": f"{request.task_description} - part {i + 1}",
                "priority": request.priority,
                "assigned_at": timestamp,
                "status": "assigned",
            }
            assignments.append(assignment)
            _task_assignments.append(assignment)

        return {
            "status": "success",
            "data": {
                "assignments": assignments,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/swarm-intel/knowledge")
async def contribute_knowledge(request: KnowledgeContributeRequest):
    try:
        entry_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        agent = _agents.get(request.agent_id, {})
        agent_moniker = agent.get("moniker", "unknown")

        entry = {
            "id": entry_id,
            "agent_id": request.agent_id,
            "agent_moniker": agent_moniker,
            "knowledge_type": request.knowledge_type,
            "content": request.content,
            "confidence": request.confidence,
            "created_at": timestamp,
            "access_count": 0,
        }

        _knowledge_entries[entry_id] = entry

        if request.agent_id in _agents:
            _agents[request.agent_id]["contributions"] += 1
            _agents[request.agent_id]["last_active"] = timestamp

        return {
            "status": "success",
            "data": {
                "entry_id": entry_id,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/swarm-intel/knowledge")
async def query_knowledge(
    query: str = Query(default=""),
    tags: Optional[List[str]] = Query(default=None),
    limit: int = Query(default=10),
):
    try:
        results = []
        query_lower = query.lower()

        for entry in _knowledge_entries.values():
            content_str = str(entry.get("content", "")).lower()
            if query_lower and query_lower not in content_str:
                continue
            if tags:
                entry_tags = entry.get("content", {}).get("tags", [])
                if not any(tag in entry_tags for tag in tags):
                    continue
            entry["access_count"] += 1
            results.append(entry)

        results = sorted(results, key=lambda e: e.get("confidence", 0), reverse=True)
        results = results[:limit]

        return {
            "status": "success",
            "data": {
                "entries": results,
                "total_results": len(results),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/swarm-intel/emergence")
async def get_emergence():
    try:
        patterns: List[Dict[str, Any]] = []
        innovations: List[Dict[str, Any]] = []

        if len(_consensus_history) >= 3:
            patterns.append({
                "id": str(uuid.uuid4()),
                "name": "Consensus Convergence",
                "description": "Multiple consensus rounds show converging decision patterns",
                "confidence": 0.72,
                "observed_agents": len(_agents),
                "timestamp": datetime.utcnow().isoformat(),
            })

        if len(_task_assignments) >= 2:
            patterns.append({
                "id": str(uuid.uuid4()),
                "name": "Task Specialization",
                "description": "Agents are developing specialized task preferences",
                "confidence": 0.65,
                "observed_agents": len(set(a.get("agent_id") for a in _task_assignments)),
                "timestamp": datetime.utcnow().isoformat(),
            })

        if len(_knowledge_entries) >= 5:
            innovations.append({
                "id": str(uuid.uuid4()),
                "name": "Knowledge Synthesis",
                "description": "New knowledge patterns emerging from shared pool",
                "confidence": 0.58,
                "contributing_agents": len(set(
                    e.get("agent_id") for e in _knowledge_entries.values()
                )),
                "timestamp": datetime.utcnow().isoformat(),
            })

        return {
            "status": "success",
            "data": {
                "patterns": patterns,
                "innovations": innovations,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )