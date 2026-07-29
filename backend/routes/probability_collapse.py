"""
SparkLabs Backend - Probability Collapse Theater Routes

REST API endpoints for EngineProbabilityCollapseTheater: game events as
quantum-like probability amplitudes with SUPERPOSE/INTERFERE/OBSERVE/COLLAPSE/DECOHERE cycle.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class CreateWaveRequest(BaseModel):
    wave_id: str
    label: str
    domain: str = "general"


class AddBranchRequest(BaseModel):
    branch_id: str
    label: str
    amplitude_real: float
    amplitude_imag: float = 0.0
    description: str = ""
    properties: Optional[Dict[str, Any]] = None


class EntangleRequest(BaseModel):
    wave_a: str
    wave_b: str
    link_type: str = "mirror"
    correlation: float = 1.0


class ObserveRequest(BaseModel):
    observer: str
    observer_type: str = "player"


class SimulateRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Wave Routes
# =============================================================================

@router.get("/probability-collapse/status")
async def probability_collapse_status():
    from sparkai.engine.engine_probability_collapse_theater import EngineProbabilityCollapseTheater
    theater = EngineProbabilityCollapseTheater.get_instance()
    return {"status": "ok", "data": theater.get_status()}


@router.post("/probability-collapse/waves")
async def probability_collapse_create_wave(req: CreateWaveRequest):
    from sparkai.engine.engine_probability_collapse_theater import EngineProbabilityCollapseTheater
    theater = EngineProbabilityCollapseTheater.get_instance()
    result = theater.create_wave(
        wave_id=req.wave_id,
        label=req.label,
        domain=req.domain,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/probability-collapse/waves")
async def probability_collapse_list_waves():
    from sparkai.engine.engine_probability_collapse_theater import EngineProbabilityCollapseTheater
    theater = EngineProbabilityCollapseTheater.get_instance()
    return {"status": "ok", "data": theater.list_waves()}


@router.get("/probability-collapse/waves/{wave_id}")
async def probability_collapse_get_wave(wave_id: str):
    from sparkai.engine.engine_probability_collapse_theater import EngineProbabilityCollapseTheater
    theater = EngineProbabilityCollapseTheater.get_instance()
    result = theater.get_wave(wave_id)
    if result is None:
        return {"status": "error", "detail": f"Wave not found: {wave_id}"}
    return {"status": "ok", "data": result}


@router.delete("/probability-collapse/waves/{wave_id}")
async def probability_collapse_remove_wave(wave_id: str):
    from sparkai.engine.engine_probability_collapse_theater import EngineProbabilityCollapseTheater
    theater = EngineProbabilityCollapseTheater.get_instance()
    result = theater.remove_wave(wave_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Branch Routes
# =============================================================================

@router.post("/probability-collapse/waves/{wave_id}/branches")
async def probability_collapse_add_branch(wave_id: str, req: AddBranchRequest):
    from sparkai.engine.engine_probability_collapse_theater import EngineProbabilityCollapseTheater
    theater = EngineProbabilityCollapseTheater.get_instance()
    result = theater.add_branch(
        wave_id=wave_id,
        branch_id=req.branch_id,
        label=req.label,
        amplitude=complex(req.amplitude_real, req.amplitude_imag),
        description=req.description,
        properties=req.properties,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Entanglement Routes
# =============================================================================

@router.post("/probability-collapse/entanglements")
async def probability_collapse_entangle(req: EntangleRequest):
    from sparkai.engine.engine_probability_collapse_theater import EngineProbabilityCollapseTheater
    theater = EngineProbabilityCollapseTheater.get_instance()
    result = theater.entangle(
        wave_a=req.wave_a,
        wave_b=req.wave_b,
        link_type=req.link_type,
        correlation=req.correlation,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/probability-collapse/entanglements")
async def probability_collapse_list_entanglements():
    from sparkai.engine.engine_probability_collapse_theater import EngineProbabilityCollapseTheater
    theater = EngineProbabilityCollapseTheater.get_instance()
    return {"status": "ok", "data": theater.list_entanglements()}


# =============================================================================
# Observation Routes
# =============================================================================

@router.post("/probability-collapse/waves/{wave_id}/observe")
async def probability_collapse_observe(wave_id: str, req: ObserveRequest):
    from sparkai.engine.engine_probability_collapse_theater import (
        EngineProbabilityCollapseTheater, ObservationType,
    )
    theater = EngineProbabilityCollapseTheater.get_instance()
    try:
        ot = ObservationType(req.observer_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid observer_type: {req.observer_type}"}
    result = theater.observe(
        wave_id=wave_id,
        observer=req.observer,
        observer_type=ot,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Query Routes
# =============================================================================

@router.get("/probability-collapse/results")
async def probability_collapse_get_results(limit: int = Query(20, ge=1, le=100)):
    from sparkai.engine.engine_probability_collapse_theater import EngineProbabilityCollapseTheater
    theater = EngineProbabilityCollapseTheater.get_instance()
    return {"status": "ok", "data": theater.get_results(limit)}


@router.get("/probability-collapse/events")
async def probability_collapse_events(limit: int = Query(50, ge=1, le=200)):
    from sparkai.engine.engine_probability_collapse_theater import EngineProbabilityCollapseTheater
    theater = EngineProbabilityCollapseTheater.get_instance()
    return {"status": "ok", "data": theater.get_events_log(limit)}


# =============================================================================
# Cycle Routes
# =============================================================================

@router.post("/probability-collapse/cycle")
async def probability_collapse_cycle():
    from sparkai.engine.engine_probability_collapse_theater import EngineProbabilityCollapseTheater
    theater = EngineProbabilityCollapseTheater.get_instance()
    return {"status": "ok", "data": theater.cycle()}


@router.post("/probability-collapse/simulate")
async def probability_collapse_simulate(req: SimulateRequest):
    from sparkai.engine.engine_probability_collapse_theater import EngineProbabilityCollapseTheater
    theater = EngineProbabilityCollapseTheater.get_instance()
    result = theater.simulate(req.cycles)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/probability-collapse/reset")
async def probability_collapse_reset():
    from sparkai.engine.engine_probability_collapse_theater import EngineProbabilityCollapseTheater
    theater = EngineProbabilityCollapseTheater.get_instance()
    return {"status": "ok", "data": theater.reset()}
