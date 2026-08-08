"""
SparkLabs Backend - Engine Checkpoint & Predictive Simulation API

REST API for the world-checkpointing and sandbox predictive-simulation
service. Enables the web editor and AI agents to snapshot world state,
step the engine forward in a sandbox, inspect predicted outcomes, and
roll back or commit.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, Optional

router = APIRouter()


def _get_engine():
    from sparkai.engine.engine import SparkEngine
    return SparkEngine.get_instance()


class CheckpointRequest(BaseModel):
    reason: str = "checkpoint"


class RestoreRequest(BaseModel):
    checkpoint_id: str


class SimulateRequest(BaseModel):
    frames: int = 60
    delta_time: float = 1.0 / 60.0
    commit: bool = False


@router.post("/checkpoints")
async def create_checkpoint(req: CheckpointRequest):
    """Capture a snapshot of the current world state."""
    try:
        engine = _get_engine()
        cp = engine.create_checkpoint(reason=req.reason)
        return JSONResponse({"status": "success", "data": cp})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/checkpoints")
async def list_checkpoints():
    """List all captured world checkpoints."""
    try:
        engine = _get_engine()
        return JSONResponse({
            "status": "success",
            "data": {"checkpoints": engine.list_checkpoints()},
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/checkpoints/restore")
async def restore_checkpoint(req: RestoreRequest):
    """Restore the world to a captured checkpoint (rollback)."""
    try:
        engine = _get_engine()
        ok = engine.restore_checkpoint(req.checkpoint_id)
        return JSONResponse({
            "status": "success" if ok else "error",
            "data": {"restored": ok, "checkpoint_id": req.checkpoint_id},
        }, status_code=200 if ok else 404)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.delete("/checkpoints/{checkpoint_id}")
async def discard_checkpoint(checkpoint_id: str):
    """Discard a captured checkpoint without restoring it."""
    try:
        engine = _get_engine()
        ok = engine.discard_checkpoint(checkpoint_id)
        return JSONResponse({
            "status": "success" if ok else "error",
            "data": {"discarded": ok},
        }, status_code=200 if ok else 404)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/simulate")
async def simulate_frames(req: SimulateRequest):
    """
    Predict world consequences by stepping the engine forward in a sandbox.

    `commit=false` (default) rolls the world back after measurement
    (predictive what-if). `commit=true` keeps the simulated outcome.
    """
    try:
        engine = _get_engine()
        result = engine.simulate_frames(
            frames=req.frames,
            delta_time=req.delta_time,
            commit=req.commit,
        )
        return JSONResponse({
            "status": "success",
            "data": result,
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/checkpoints/status")
async def checkpoint_status():
    """Return checkpoint service statistics."""
    try:
        engine = _get_engine()
        return JSONResponse({
            "status": "success",
            "data": engine.checkpoints.get_statistics(),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
