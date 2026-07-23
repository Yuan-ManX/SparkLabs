"""
SparkLabs Backend - Frame Architect & AI Workflow Routes

REST API endpoints for:
  - AgentFrameArchitect: real-time cinematographic frame composition
  - EngineAIWorkflow: declarative AI agent action chaining

Routes use /frame-architect/ and /ai-workflow/ prefixes.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class ContextUpdateRequest(BaseModel):
    """Request to update the frame architect's scene context."""
    player_pos: Optional[List[float]] = None
    player_velocity: Optional[float] = None
    player_health: Optional[float] = None
    player_health_trend: Optional[str] = None
    action_intensity: Optional[float] = None
    enemy_count: Optional[int] = None
    narrative_tension: Optional[float] = None
    emotional_context: Optional[str] = None
    environment_type: Optional[str] = None
    time_of_day: Optional[str] = None
    is_cutscene: Optional[bool] = None
    is_boss_fight: Optional[bool] = None
    is_dialogue: Optional[bool] = None


class SimulateRequest(BaseModel):
    """Request to run a simulation."""
    cycles: int = 10


class MetricReportRequest(BaseModel):
    """Request to report a single metric."""
    metric_name: str
    value: float


class MetricsBatchRequest(BaseModel):
    """Request to report multiple metrics."""
    metrics: Dict[str, float]


class AddRuleRequest(BaseModel):
    """Request to add a new workflow rule."""
    name: str
    description: str = ""
    conditions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    priority: int = 0
    cooldown_s: float = 5.0


class RuleStatusRequest(BaseModel):
    """Request to change a rule's status."""
    status: str


# =============================================================================
# Frame Architect Routes
# =============================================================================

@router.get("/frame-architect/status")
async def frame_architect_status():
    """Get the current status of the frame architect."""
    from sparkai.agent.agent_frame_architect import AgentFrameArchitect
    architect = AgentFrameArchitect.get_instance()
    return {"status": "ok", "data": architect.get_status()}


@router.post("/frame-architect/context")
async def frame_architect_update_context(req: ContextUpdateRequest):
    """Update the scene context for the frame architect."""
    from sparkai.agent.agent_frame_architect import AgentFrameArchitect
    architect = AgentFrameArchitect.get_instance()
    result = architect.update_context(
        player_pos=req.player_pos,
        player_velocity=req.player_velocity,
        player_health=req.player_health,
        player_health_trend=req.player_health_trend,
        action_intensity=req.action_intensity,
        enemy_count=req.enemy_count,
        narrative_tension=req.narrative_tension,
        emotional_context=req.emotional_context,
        environment_type=req.environment_type,
        time_of_day=req.time_of_day,
        is_cutscene=req.is_cutscene,
        is_boss_fight=req.is_boss_fight,
        is_dialogue=req.is_dialogue,
    )
    return {"status": "ok", "data": result}


@router.get("/frame-architect/directives")
async def frame_architect_directives(limit: int = Query(20, ge=1, le=100)):
    """Get recent frame directives."""
    from sparkai.agent.agent_frame_architect import AgentFrameArchitect
    architect = AgentFrameArchitect.get_instance()
    return {"status": "ok", "data": architect.get_directives(limit)}


@router.get("/frame-architect/current")
async def frame_architect_current():
    """Get the current active frame directive."""
    from sparkai.agent.agent_frame_architect import AgentFrameArchitect
    architect = AgentFrameArchitect.get_instance()
    return {"status": "ok", "data": architect.get_current_directive()}


@router.get("/frame-architect/distribution")
async def frame_architect_distribution():
    """Get the distribution of shot types and lighting moods used."""
    from sparkai.agent.agent_frame_architect import AgentFrameArchitect
    architect = AgentFrameArchitect.get_instance()
    return {"status": "ok", "data": architect.get_shot_distribution()}


@router.post("/frame-architect/cycle")
async def frame_architect_cycle():
    """Run a single frame architect cycle."""
    from sparkai.agent.agent_frame_architect import AgentFrameArchitect
    architect = AgentFrameArchitect.get_instance()
    return {"status": "ok", "data": architect.run_cycle()}


@router.post("/frame-architect/simulate")
async def frame_architect_simulate(req: SimulateRequest):
    """Run multiple cycles with simulated game state."""
    from sparkai.agent.agent_frame_architect import AgentFrameArchitect
    architect = AgentFrameArchitect.get_instance()
    return {"status": "ok", "data": architect.simulate(req.cycles)}


@router.post("/frame-architect/reset")
async def frame_architect_reset():
    """Reset the frame architect to initial state."""
    from sparkai.agent.agent_frame_architect import AgentFrameArchitect
    architect = AgentFrameArchitect.get_instance()
    return {"status": "ok", "data": architect.reset()}


# =============================================================================
# AI Workflow Routes
# =============================================================================

@router.get("/ai-workflow/status")
async def ai_workflow_status():
    """Get the current status of the workflow engine."""
    from sparkai.engine.engine_ai_workflow import EngineAIWorkflow
    workflow = EngineAIWorkflow.get_instance()
    return {"status": "ok", "data": workflow.get_status()}


@router.get("/ai-workflow/rules")
async def ai_workflow_rules(status_filter: Optional[str] = Query(None)):
    """Get all workflow rules."""
    from sparkai.engine.engine_ai_workflow import EngineAIWorkflow
    workflow = EngineAIWorkflow.get_instance()
    return {"status": "ok", "data": workflow.get_rules(status_filter)}


@router.post("/ai-workflow/rules")
async def ai_workflow_add_rule(req: AddRuleRequest):
    """Add a new workflow rule."""
    from sparkai.engine.engine_ai_workflow import EngineAIWorkflow
    workflow = EngineAIWorkflow.get_instance()
    rule = workflow.add_rule(
        name=req.name,
        description=req.description,
        conditions=req.conditions,
        actions=req.actions,
        priority=req.priority,
        cooldown_s=req.cooldown_s,
    )
    return {"status": "ok", "data": rule}


@router.get("/ai-workflow/rules/{rule_id}")
async def ai_workflow_get_rule(rule_id: str):
    """Get a single rule by ID."""
    from sparkai.engine.engine_ai_workflow import EngineAIWorkflow
    workflow = EngineAIWorkflow.get_instance()
    rule = workflow.get_rule(rule_id)
    if rule is None:
        return {"status": "error", "message": f"Rule '{rule_id}' not found"}
    return {"status": "ok", "data": rule}


@router.delete("/ai-workflow/rules/{rule_id}")
async def ai_workflow_remove_rule(rule_id: str):
    """Remove a workflow rule."""
    from sparkai.engine.engine_ai_workflow import EngineAIWorkflow
    workflow = EngineAIWorkflow.get_instance()
    removed = workflow.remove_rule(rule_id)
    return {"status": "ok" if removed else "error", "removed": removed}


@router.put("/ai-workflow/rules/{rule_id}/status")
async def ai_workflow_set_rule_status(rule_id: str, req: RuleStatusRequest):
    """Enable, pause, or disable a rule."""
    from sparkai.engine.engine_ai_workflow import EngineAIWorkflow
    workflow = EngineAIWorkflow.get_instance()
    result = workflow.set_rule_status(rule_id, req.status)
    return {"status": "ok", "data": result}


@router.get("/ai-workflow/metrics")
async def ai_workflow_metrics():
    """Get all current metric values."""
    from sparkai.engine.engine_ai_workflow import EngineAIWorkflow
    workflow = EngineAIWorkflow.get_instance()
    return {"status": "ok", "data": workflow.get_metrics()}


@router.post("/ai-workflow/metrics")
async def ai_workflow_report_metric(req: MetricReportRequest):
    """Report a single metric value."""
    from sparkai.engine.engine_ai_workflow import EngineAIWorkflow
    workflow = EngineAIWorkflow.get_instance()
    result = workflow.report_metric(req.metric_name, req.value)
    return {"status": "ok", "data": result}


@router.post("/ai-workflow/metrics/batch")
async def ai_workflow_report_metrics_batch(req: MetricsBatchRequest):
    """Report multiple metrics at once."""
    from sparkai.engine.engine_ai_workflow import EngineAIWorkflow
    workflow = EngineAIWorkflow.get_instance()
    result = workflow.report_metrics_batch(req.metrics)
    return {"status": "ok", "data": result}


@router.get("/ai-workflow/flags")
async def ai_workflow_flags():
    """Get all internal flags."""
    from sparkai.engine.engine_ai_workflow import EngineAIWorkflow
    workflow = EngineAIWorkflow.get_instance()
    return {"status": "ok", "data": workflow.get_flags()}


@router.get("/ai-workflow/log")
async def ai_workflow_log(limit: int = Query(20, ge=1, le=200)):
    """Get recent execution log entries."""
    from sparkai.engine.engine_ai_workflow import EngineAIWorkflow
    workflow = EngineAIWorkflow.get_instance()
    return {"status": "ok", "data": workflow.get_execution_log(limit)}


@router.post("/ai-workflow/cycle")
async def ai_workflow_cycle():
    """Run a single workflow evaluation cycle."""
    from sparkai.engine.engine_ai_workflow import EngineAIWorkflow
    workflow = EngineAIWorkflow.get_instance()
    return {"status": "ok", "data": workflow.run_cycle()}


@router.post("/ai-workflow/simulate")
async def ai_workflow_simulate(req: SimulateRequest):
    """Run multiple cycles with simulated metrics."""
    from sparkai.engine.engine_ai_workflow import EngineAIWorkflow
    workflow = EngineAIWorkflow.get_instance()
    return {"status": "ok", "data": workflow.simulate(req.cycles)}


@router.post("/ai-workflow/reset")
async def ai_workflow_reset():
    """Reset the workflow engine to initial state."""
    from sparkai.engine.engine_ai_workflow import EngineAIWorkflow
    workflow = EngineAIWorkflow.get_instance()
    return {"status": "ok", "data": workflow.reset()}
