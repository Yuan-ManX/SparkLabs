"""
SparkLabs Backend - Story Director & Live Tuner Routes

REST API for the AgentStoryDirector (narrative intelligence) and
EngineLiveTuner (continuous parameter optimization).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class CreateArcRequest(BaseModel):
    title: str
    theme: str
    description: str = ""
    acts: int = 3
    priority: float = 0.5
    characters: Optional[List[str]] = None


class DeployPlotRequest(BaseModel):
    plot_type: str
    arc_id: Optional[str] = None
    characters: Optional[List[str]] = None


class UpdatePlayerRequest(BaseModel):
    engagement: float
    location: str = ""


class AddCharacterRequest(BaseModel):
    name: str
    role: str
    disposition: float = 0.0
    trust: float = 0.5
    goals: Optional[List[str]] = None


class SimulateRequest(BaseModel):
    count: int = 5
    cycles: int = 5


class SetParameterRequest(BaseModel):
    value: float


class ReportMetricRequest(BaseModel):
    metric_name: str
    value: float
    context: str = ""


# ---------------------------------------------------------------------------
# Story Director Endpoints
# ---------------------------------------------------------------------------

def _director():
    from sparkai.agent.agent_story_director import AgentStoryDirector
    return AgentStoryDirector.get_instance()


@router.get("/story-director/status")
async def get_director_status():
    return {"status": "ok", "data": _director().get_status()}


@router.get("/story-director/characters")
async def get_characters():
    return {"status": "ok", "data": _director().get_characters()}


@router.post("/story-director/characters")
async def add_character(req: AddCharacterRequest):
    from sparkai.agent.agent_story_director import CharacterRole
    try:
        role = CharacterRole(req.role)
    except ValueError:
        return {"status": "error", "error": f"Invalid role: {req.role}"}
    result = _director().add_character(req.name, role, req.disposition, req.trust, req.goals)
    return {"status": "ok", "data": result}


@router.get("/story-director/relationships")
async def get_relationships():
    return {"status": "ok", "data": _director().get_relationships()}


@router.get("/story-director/arcs")
async def get_arcs():
    return {"status": "ok", "data": _director().get_arcs()}


@router.post("/story-director/arcs")
async def create_arc(req: CreateArcRequest):
    result = _director().create_arc(req.title, req.theme, req.description,
                                    req.acts, req.priority, req.characters)
    return {"status": "ok", "data": result}


@router.post("/story-director/arcs/{arc_id}/start")
async def start_arc(arc_id: str):
    success = _director().start_arc(arc_id)
    return {"status": "ok" if success else "error", "data": {"started": success}}


@router.post("/story-director/arcs/{arc_id}/complete")
async def complete_arc(arc_id: str):
    success = _director().complete_arc(arc_id)
    return {"status": "ok" if success else "error", "data": {"completed": success}}


@router.get("/story-director/plots")
async def get_plots(limit: int = 20):
    return {"status": "ok", "data": _director().get_plot_points(limit)}


@router.post("/story-director/plots/deploy")
async def deploy_plot(req: DeployPlotRequest):
    result = _director().deploy_plot_point(req.plot_type, req.arc_id, req.characters)
    return {"status": "ok", "data": result}


@router.get("/story-director/tension")
async def get_tension():
    return {"status": "ok", "data": _director().get_tension()}


@router.post("/story-director/player")
async def update_player(req: UpdatePlayerRequest):
    _director().update_player_state(req.engagement, req.location)
    return {"status": "ok"}


@router.get("/story-director/memory")
async def get_memory(limit: int = 20):
    return {"status": "ok", "data": _director().get_memory(limit)}


@router.post("/story-director/cycle")
async def run_cycle():
    return {"status": "ok", "data": _director().run_cycle()}


@router.post("/story-director/simulate")
async def simulate(req: SimulateRequest):
    result = _director().simulate(req.cycles)
    return {"status": "ok", "data": result}


@router.post("/story-director/reset")
async def reset_director():
    _director().reset()
    return {"status": "ok", "data": {"message": "Story director reset"}}


# ---------------------------------------------------------------------------
# Live Tuner Endpoints
# ---------------------------------------------------------------------------

def _tuner():
    from sparkai.engine.engine_live_tuner import EngineLiveTuner
    return EngineLiveTuner.get_instance()


@router.get("/live-tuner/status")
async def get_tuner_status():
    return {"status": "ok", "data": _tuner().get_status()}


@router.get("/live-tuner/parameters")
async def get_parameters(domain: Optional[str] = None):
    return {"status": "ok", "data": _tuner().get_parameters(domain)}


@router.get("/live-tuner/parameters/{param_id}")
async def get_parameter(param_id: str):
    p = _tuner().get_parameter(param_id)
    if p is None:
        return {"status": "error", "error": f"Parameter {param_id} not found"}
    return {"status": "ok", "data": p}


@router.put("/live-tuner/parameters/{param_id}")
async def set_parameter(param_id: str, req: SetParameterRequest):
    success = _tuner().set_parameter_value(param_id, req.value)
    return {"status": "ok" if success else "error", "data": {"set": success}}


@router.post("/live-tuner/parameters/{param_id}/reset")
async def reset_parameter(param_id: str):
    success = _tuner().reset_parameter(param_id)
    return {"status": "ok" if success else "error", "data": {"reset": success}}


@router.post("/live-tuner/reset-all")
async def reset_all_parameters():
    count = _tuner().reset_all_parameters()
    return {"status": "ok", "data": {"reset_count": count}}


@router.post("/live-tuner/metrics")
async def report_metric(req: ReportMetricRequest):
    success = _tuner().report_metric_by_name(req.metric_name, req.value, req.context)
    return {"status": "ok" if success else "error", "data": {"reported": success}}


@router.get("/live-tuner/metrics")
async def get_metrics():
    return {"status": "ok", "data": _tuner().get_metrics()}


@router.get("/live-tuner/adjustments")
async def get_adjustments(limit: int = 20):
    return {"status": "ok", "data": _tuner().get_adjustments(limit)}


@router.post("/live-tuner/cycle")
async def run_tuner_cycle():
    return {"status": "ok", "data": _tuner().run_cycle()}


@router.post("/live-tuner/simulate")
async def simulate_tuner(req: SimulateRequest):
    result = _tuner().simulate_metrics(req.count)
    return {"status": "ok", "data": result}


@router.post("/live-tuner/reset")
async def reset_tuner():
    _tuner().reset()
    return {"status": "ok", "data": {"message": "Live tuner reset"}}
