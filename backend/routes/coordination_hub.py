"""
SparkLabs Backend - Agent Coordination Hub Routes

REST API endpoints for the AgentCoordinationHub that unifies all AI agent
modules (BridgeOrchestrator, AgentEngineFusionLoop, CreativeAutonomyDirector)
into a single coherent intelligence.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/coordination-hub", tags=["coordination-hub"])


class CycleRequest(BaseModel):
    """Request to run coordination cycle(s)."""
    count: int = 1


def _hub():
    """Get the coordination hub singleton."""
    from sparkai.agent.agent_coordination_hub import AgentCoordinationHub
    return AgentCoordinationHub.get_instance()


@router.get("/status")
async def get_status():
    """Get the coordination hub status."""
    return {"status": "ok", "data": _hub().get_status()}


@router.get("/insights")
async def get_insights(limit: int = 20):
    """Get recent coordination insights."""
    return {"status": "ok", "data": _hub().get_insights(limit)}


@router.get("/context")
async def get_context():
    """Get the current coordination context."""
    return {"status": "ok", "data": _hub().get_context()}


@router.post("/cycle")
async def run_cycle():
    """Run a single coordination cycle."""
    result = _hub().run_coordination_cycle()
    return {"status": "ok", "data": result}


@router.post("/simulate")
async def simulate_cycles(req: CycleRequest):
    """Run multiple coordination cycles for testing."""
    count = max(1, min(req.count, 50))
    results = _hub().simulate_cycles(count)
    return {"status": "ok", "data": {"cycles": results, "count": len(results)}}


@router.post("/reset")
async def reset():
    """Reset the coordination hub state."""
    _hub().reset()
    return {"status": "ok", "data": {"message": "Coordination hub reset"}}
