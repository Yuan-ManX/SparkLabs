"""
SparkLabs Backend - Playtest Simulator Routes

REST API endpoints for the AgentPlaytestSimulator that runs virtual
playtests on generated games with multiple player archetypes.

Routes use the /playtest-sim/ prefix to avoid conflicts with the legacy
playtest engine routes in agent.py that use /playtest/.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class PlaytestRequest(BaseModel):
    """Request to run a playtest."""
    game_id: str = "test_game"


def _sim():
    """Get the playtest simulator singleton."""
    from sparkai.agent.agent_playtest_simulator import AgentPlaytestSimulator
    return AgentPlaytestSimulator.get_instance()


@router.get("/playtest-sim/status")
async def get_status():
    """Get the simulator status."""
    return {"status": "ok", "data": _sim().get_status()}


@router.post("/playtest-sim/run")
async def run_playtest(req: PlaytestRequest):
    """Run a complete playtest with all archetypes."""
    report = _sim().run_playtest(req.game_id)
    return {"status": "ok", "data": _sim()._report_to_dict(report)}


@router.get("/playtest-sim/latest")
async def get_latest():
    """Get the most recent playtest report."""
    report = _sim().get_latest_report()
    if report is None:
        return {"status": "ok", "data": None}
    return {"status": "ok", "data": report}


@router.get("/playtest-sim/history")
async def get_history(limit: int = 10):
    """Get recent playtest reports."""
    return {"status": "ok", "data": _sim().get_history(limit)}


@router.post("/playtest-sim/reset")
async def reset():
    """Reset the simulator state."""
    _sim().reset()
    return {"status": "ok", "data": {"message": "Playtest simulator reset"}}
