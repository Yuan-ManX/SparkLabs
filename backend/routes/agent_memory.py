"""
SparkLabs Backend - Agent Memory Routes

API endpoints for agent memory systems including
working memory, episodic memory, semantic memory,
similarity retrieval, and memory consolidation.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# In-memory storage for agent memories
_memories: Dict[str, Dict[str, Any]] = {}
_memory_types: List[str] = ["working", "episodic", "semantic"]


class MemoryStoreRequest(BaseModel):
    memory_type: str = "working"
    agent_id: str = ""
    content: str = ""
    metadata: Optional[Dict[str, Any]] = None


class MemoryRetrieveRequest(BaseModel):
    agent_id: str = ""
    query: str = ""
    memory_type: Optional[str] = None
    top_k: int = 5
    threshold: float = 0.5


class MemoryConsolidateRequest(BaseModel):
    agent_id: str = ""
    source_type: str = "working"
    target_type: str = "episodic"


@router.post("/memory/store")
async def store_memory(request: MemoryStoreRequest):
    try:
        memory_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        memory_entry = {
            "id": memory_id,
            "agent_id": request.agent_id,
            "memory_type": request.memory_type,
            "content": request.content,
            "metadata": request.metadata or {},
            "created_at": timestamp,
            "access_count": 0,
            "last_accessed": timestamp,
        }

        _memories[memory_id] = memory_entry

        return {
            "status": "success",
            "data": {
                "memory_id": memory_id,
                "memory_type": request.memory_type,
                "stored_at": timestamp,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/memory/retrieve")
async def retrieve_memories(request: MemoryRetrieveRequest):
    try:
        results = []
        query_lower = request.query.lower()

        for mem in _memories.values():
            if request.agent_id and mem.get("agent_id") != request.agent_id:
                continue
            if request.memory_type and mem.get("memory_type") != request.memory_type:
                continue
            if query_lower and query_lower not in mem.get("content", "").lower():
                continue

            mem["access_count"] += 1
            mem["last_accessed"] = datetime.utcnow().isoformat()
            results.append(mem)

        results = sorted(results, key=lambda m: m.get("access_count", 0), reverse=True)
        results = results[: request.top_k]

        return {
            "status": "success",
            "data": {
                "memories": results,
                "total_count": len(_memories),
                "matched_count": len(results),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/memory/consolidate")
async def consolidate_memory(request: MemoryConsolidateRequest):
    try:
        consolidated_ids = []
        timestamp = datetime.utcnow().isoformat()

        source_memories = [
            m
            for m in _memories.values()
            if m.get("agent_id") == request.agent_id
            and m.get("memory_type") == request.source_type
        ]

        for mem in source_memories:
            new_id = str(uuid.uuid4())
            consolidated = {
                "id": new_id,
                "agent_id": request.agent_id,
                "memory_type": request.target_type,
                "content": mem.get("content", ""),
                "metadata": {
                    **mem.get("metadata", {}),
                    "consolidated_from": mem.get("id"),
                    "source_type": request.source_type,
                },
                "created_at": timestamp,
                "access_count": 0,
                "last_accessed": timestamp,
            }
            _memories[new_id] = consolidated
            consolidated_ids.append(new_id)

        return {
            "status": "success",
            "data": {
                "consolidated_count": len(consolidated_ids),
                "consolidated_ids": consolidated_ids,
                "source_type": request.source_type,
                "target_type": request.target_type,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/memory/stats")
async def get_memory_stats():
    try:
        stats = {
            "total_memories": len(_memories),
            "by_type": {},
            "by_agent": {},
        }

        for mem in _memories.values():
            mem_type = mem.get("memory_type", "unknown")
            agent_id = mem.get("agent_id", "unknown")
            stats["by_type"][mem_type] = stats["by_type"].get(mem_type, 0) + 1
            stats["by_agent"][agent_id] = stats["by_agent"].get(agent_id, 0) + 1

        return {"status": "success", "data": stats}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )