"""
SparkLabs Backend - Temporal Director & Music Conductor Routes"""

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


class TimeScaleRequest(BaseModel):
    scale: str


class PacingPhaseRequest(BaseModel):
    phase: str


class ScheduleEventRequest(BaseModel):
    event_type: str
    target_module: str
    method: str
    delay_s: float = 5.0
    params: Dict[str, Any] = {}
    priority: int = 0
    label: str = ""


class MusicContextRequest(BaseModel):
    scene_intensity: Optional[float] = None
    narrative_tension: Optional[float] = None
    emotional_context: Optional[str] = None
    pacing_phase: Optional[str] = None
    is_combat: Optional[bool] = None
    is_dialogue: Optional[bool] = None
    is_exploration: Optional[bool] = None
    is_boss_fight: Optional[bool] = None
    is_cutscene: Optional[bool] = None
    player_health: Optional[float] = None
    time_of_day: Optional[str] = None


# =============================================================================
# Temporal Director Routes
# =============================================================================

@router.get("/temporal-director/status")
async def temporal_status():
    from sparkai.agent.agent_temporal_director import AgentTemporalDirector
    director = AgentTemporalDirector.get_instance()
    return {"status": "ok", "data": director.get_status()}


@router.post("/temporal-director/time-scale")
async def temporal_set_time_scale(req: TimeScaleRequest):
    from sparkai.agent.agent_temporal_director import AgentTemporalDirector
    director = AgentTemporalDirector.get_instance()
    result = director.set_time_scale(req.scale)
    return {"status": "ok" if "error" not in result else "error", "data": result}


@router.post("/temporal-director/pacing")
async def temporal_force_pacing(req: PacingPhaseRequest):
    from sparkai.agent.agent_temporal_director import AgentTemporalDirector
    director = AgentTemporalDirector.get_instance()
    result = director.force_pacing_phase(req.phase)
    return {"status": "ok" if "error" not in result else "error", "data": result}


@router.get("/temporal-director/events")
async def temporal_events(limit: int = Query(20, ge=1, le=100), include_fired: bool = Query(True)):
    from sparkai.agent.agent_temporal_director import AgentTemporalDirector
    director = AgentTemporalDirector.get_instance()
    return {"status": "ok", "data": director.get_events(limit, include_fired)}


@router.post("/temporal-director/events")
async def temporal_schedule_event(req: ScheduleEventRequest):
    from sparkai.agent.agent_temporal_director import AgentTemporalDirector
    director = AgentTemporalDirector.get_instance()
    result = director.schedule_event(
        req.event_type, req.target_module, req.method,
        req.delay_s, req.params, req.priority, req.label,
    )
    return {"status": "ok" if "error" not in result else "error", "data": result}


@router.delete("/temporal-director/events/{event_id}")
async def temporal_cancel_event(event_id: str):
    from sparkai.agent.agent_temporal_director import AgentTemporalDirector
    director = AgentTemporalDirector.get_instance()
    cancelled = director.cancel_event(event_id)
    return {"status": "ok" if cancelled else "error", "cancelled": cancelled}


@router.get("/temporal-director/history")
async def temporal_history(limit: int = Query(20, ge=1, le=200)):
    from sparkai.agent.agent_temporal_director import AgentTemporalDirector
    director = AgentTemporalDirector.get_instance()
    return {"status": "ok", "data": director.get_event_history(limit)}


@router.get("/temporal-director/effects")
async def temporal_effects(limit: int = Query(20, ge=1, le=50)):
    from sparkai.agent.agent_temporal_director import AgentTemporalDirector
    director = AgentTemporalDirector.get_instance()
    return {"status": "ok", "data": director.get_temporal_effects(limit)}


@router.post("/temporal-director/cycle")
async def temporal_cycle():
    from sparkai.agent.agent_temporal_director import AgentTemporalDirector
    director = AgentTemporalDirector.get_instance()
    return {"status": "ok", "data": director.run_cycle()}


@router.post("/temporal-director/simulate")
async def temporal_simulate(req: SimulateRequest):
    from sparkai.agent.agent_temporal_director import AgentTemporalDirector
    director = AgentTemporalDirector.get_instance()
    return {"status": "ok", "data": director.simulate(req.cycles)}


@router.post("/temporal-director/reset")
async def temporal_reset():
    from sparkai.agent.agent_temporal_director import AgentTemporalDirector
    director = AgentTemporalDirector.get_instance()
    return {"status": "ok", "data": director.reset()}


# =============================================================================
# Music Conductor Routes
# =============================================================================

@router.get("/music-conductor/status")
async def music_status():
    from sparkai.agent.agent_music_conductor import AgentMusicConductor
    conductor = AgentMusicConductor.get_instance()
    return {"status": "ok", "data": conductor.get_status()}


@router.post("/music-conductor/context")
async def music_update_context(req: MusicContextRequest):
    from sparkai.agent.agent_music_conductor import AgentMusicConductor
    conductor = AgentMusicConductor.get_instance()
    result = conductor.update_context(
        scene_intensity=req.scene_intensity,
        narrative_tension=req.narrative_tension,
        emotional_context=req.emotional_context,
        pacing_phase=req.pacing_phase,
        is_combat=req.is_combat,
        is_dialogue=req.is_dialogue,
        is_exploration=req.is_exploration,
        is_boss_fight=req.is_boss_fight,
        is_cutscene=req.is_cutscene,
        player_health=req.player_health,
        time_of_day=req.time_of_day,
    )
    return {"status": "ok", "data": result}


@router.get("/music-conductor/directives")
async def music_directives(limit: int = Query(20, ge=1, le=100)):
    from sparkai.agent.agent_music_conductor import AgentMusicConductor
    conductor = AgentMusicConductor.get_instance()
    return {"status": "ok", "data": conductor.get_directives(limit)}


@router.get("/music-conductor/current")
async def music_current():
    from sparkai.agent.agent_music_conductor import AgentMusicConductor
    conductor = AgentMusicConductor.get_instance()
    return {"status": "ok", "data": conductor.get_current_directive()}


@router.get("/music-conductor/layers")
async def music_layers():
    from sparkai.agent.agent_music_conductor import AgentMusicConductor
    conductor = AgentMusicConductor.get_instance()
    return {"status": "ok", "data": conductor.get_layer_states()}


@router.get("/music-conductor/distribution")
async def music_distribution():
    from sparkai.agent.agent_music_conductor import AgentMusicConductor
    conductor = AgentMusicConductor.get_instance()
    return {"status": "ok", "data": conductor.get_distribution()}


@router.post("/music-conductor/cycle")
async def music_cycle():
    from sparkai.agent.agent_music_conductor import AgentMusicConductor
    conductor = AgentMusicConductor.get_instance()
    return {"status": "ok", "data": conductor.run_cycle()}


@router.post("/music-conductor/simulate")
async def music_simulate(req: SimulateRequest):
    from sparkai.agent.agent_music_conductor import AgentMusicConductor
    conductor = AgentMusicConductor.get_instance()
    return {"status": "ok", "data": conductor.simulate(req.cycles)}


@router.post("/music-conductor/reset")
async def music_reset():
    from sparkai.agent.agent_music_conductor import AgentMusicConductor
    conductor = AgentMusicConductor.get_instance()
    return {"status": "ok", "data": conductor.reset()}
