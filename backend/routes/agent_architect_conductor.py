"""
SparkLabs Backend - Cognitive Architect & AI-Native Conductor API Routes

REST API endpoints for the unified cognitive architect and the AI-native
engine conductor. The architect orchestrates multi-modal reasoning, tool
evolution, and knowledge synthesis. The conductor unifies physics, render,
and scene adjustments driven by the cognitive kernel and game brain.

Endpoints:
  # Cognitive Architect
  GET  /architect/status              - Architect status and subsystem stats
  POST /architect/reason              - Run a reasoning request
  POST /architect/forge-tool          - Forge a new tool on demand
  POST /architect/synthesize          - Synthesize knowledge from episodes
  GET  /architect/knowledge           - Query the knowledge base
  POST /architect/collaborate         - Propose a collaboration task
  POST /architect/cycle               - Run one architect cycle
  GET  /architect/tools               - List deployed and active tools
  POST /architect/reset               - Reset the architect state

  # AI-Native Conductor
  GET  /conductor/status              - Conductor status and subsystem stats
  POST /conductor/cycle               - Run one conductor cycle
  POST /conductor/physics             - Submit a manual physics adjustment
  POST /conductor/render              - Submit a manual render adjustment
  POST /conductor/scene               - Submit a manual scene adjustment
  POST /conductor/reset               - Reset the conductor state
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class ReasonRequest(BaseModel):
    task: str
    context: Dict[str, Any] = {}
    preferred_modes: List[str] = []
    strategy: str = "adaptive_switch"
    max_steps: int = 6
    confidence_threshold: float = 0.6


class ForgeToolRequest(BaseModel):
    missing_capability: str
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    test_cases: List[Dict[str, Any]] = []


class SynthesizeRequest(BaseModel):
    episodes: List[Dict[str, Any]] = []


class KnowledgeQuery(BaseModel):
    query: str = ""
    domain: Optional[str] = None
    limit: int = 5


class CollaborateRequest(BaseModel):
    objective: str
    subtasks: List[Dict[str, Any]] = []


class PhysicsAdjustmentRequest(BaseModel):
    kind: str
    target: str = ""
    args: Dict[str, Any] = {}
    rationale: str = ""


class RenderAdjustmentRequest(BaseModel):
    kind: str
    target: str = ""
    args: Dict[str, Any] = {}
    rationale: str = ""


class SceneAdjustmentRequest(BaseModel):
    kind: str
    target: str = ""
    args: Dict[str, Any] = {}
    rationale: str = ""


# ---------------------------------------------------------------------------
# Cognitive Architect Endpoints
# ---------------------------------------------------------------------------

@router.get("/architect/status")
async def architect_status():
    """Get the cognitive architect status."""
    try:
        from sparkai.agent.agent_cognitive_architect import get_architect
        architect = get_architect()
        if not architect._initialized:
            architect.initialize()
        return JSONResponse({"status": "success", "data": architect.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/architect/reason")
async def architect_reason(req: ReasonRequest):
    """Run a multi-modal reasoning request."""
    try:
        from sparkai.agent.agent_cognitive_architect import (
            get_architect, ReasoningRequest, ReasoningStrategy,
        )
        architect = get_architect()
        if not architect._initialized:
            architect.initialize()
        try:
            strategy = ReasoningStrategy(req.strategy)
        except ValueError:
            strategy = ReasoningStrategy.ADAPTIVE_SWITCH
        request = ReasoningRequest(
            task=req.task,
            context=req.context,
            preferred_modes=req.preferred_modes,
            strategy=strategy,
            max_steps=req.max_steps,
            confidence_threshold=req.confidence_threshold,
        )
        result = architect.run_reasoning(request)
        return JSONResponse({"status": "success", "data": {
            "result_id": result.result_id,
            "request_id": result.request_id,
            "conclusion": result.conclusion,
            "confidence": result.confidence,
            "modes_used": result.modes_used,
            "steps": result.steps,
            "duration_s": result.duration_s,
            "success": result.success,
        }})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/architect/forge-tool")
async def architect_forge_tool(req: ForgeToolRequest):
    """Forge and deploy a new tool on demand."""
    try:
        from sparkai.agent.agent_cognitive_architect import get_architect
        architect = get_architect()
        if not architect._initialized:
            architect.initialize()
        deployed, msg = architect.forge_tool_on_demand(
            req.missing_capability,
            req.input_schema,
            req.output_schema,
            req.test_cases,
        )
        return JSONResponse({"status": "success", "data": {
            "deployed": deployed,
            "message": msg,
            "capability": req.missing_capability,
        }})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/architect/synthesize")
async def architect_synthesize(req: SynthesizeRequest):
    """Synthesize knowledge from episodic entries."""
    try:
        from sparkai.agent.agent_cognitive_architect import get_architect
        architect = get_architect()
        if not architect._initialized:
            architect.initialize()
        facts = architect.synthesize_knowledge(req.episodes)
        return JSONResponse({"status": "success", "data": {
            "synthesized_count": len(facts),
            "facts": [
                {
                    "fact_id": f.fact_id,
                    "domain": f.domain,
                    "statement": f.statement[:200],
                    "confidence": f.confidence,
                    "salience": f.salience,
                    "tags": f.tags,
                }
                for f in facts
            ],
        }})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/architect/knowledge")
async def architect_knowledge(query: str = "", domain: Optional[str] = None, limit: int = 5):
    """Query the knowledge base."""
    try:
        from sparkai.agent.agent_cognitive_architect import get_architect
        architect = get_architect()
        if not architect._initialized:
            architect.initialize()
        facts = architect.query_knowledge(query, domain, limit)
        return JSONResponse({"status": "success", "data": {
            "query": query,
            "domain": domain,
            "facts": [
                {
                    "fact_id": f.fact_id,
                    "domain": f.domain,
                    "statement": f.statement[:200],
                    "confidence": f.confidence,
                    "salience": f.salience,
                    "tags": f.tags,
                }
                for f in facts
            ],
        }})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/architect/collaborate")
async def architect_collaborate(req: CollaborateRequest):
    """Propose a multi-agent collaboration task."""
    try:
        from sparkai.agent.agent_cognitive_architect import get_architect
        architect = get_architect()
        if not architect._initialized:
            architect.initialize()
        task = architect.propose_collaboration(req.objective, req.subtasks)
        return JSONResponse({"status": "success", "data": {
            "task_id": task.task_id,
            "objective": task.objective,
            "subtask_count": len(task.decomposed_subtasks),
            "status": task.status,
        }})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/architect/cycle")
async def architect_cycle():
    """Run one architect cycle."""
    try:
        from sparkai.agent.agent_cognitive_architect import get_architect
        architect = get_architect()
        if not architect._initialized:
            architect.initialize()
        decision = architect.cycle()
        return JSONResponse({"status": "success", "data": {
            "cycle_id": decision.cycle_id,
            "phase": decision.phase.value,
            "tools_forged": decision.tools_forged,
            "knowledge_synthesized": decision.knowledge_synthesized,
            "collaboration_tasks": decision.collaboration_tasks,
            "directives": decision.directives,
            "duration_s": decision.duration_s,
            "notes": decision.notes,
            "reasoning_conclusion": decision.reasoning_result.conclusion if decision.reasoning_result else None,
            "reasoning_confidence": decision.reasoning_result.confidence if decision.reasoning_result else 0,
        }})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/architect/tools")
async def architect_tools():
    """List deployed and active tools."""
    try:
        from sparkai.agent.agent_cognitive_architect import get_architect
        architect = get_architect()
        if not architect._initialized:
            architect.initialize()
        return JSONResponse({"status": "success", "data": {
            "deployed": architect.list_deployed_tools(),
            "active": architect.list_active_specs(),
        }})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/architect/reset")
async def architect_reset():
    """Reset the architect state."""
    try:
        from sparkai.agent.agent_cognitive_architect import get_architect
        architect = get_architect()
        architect.reset()
        return JSONResponse({"status": "success", "data": {"reset": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# AI-Native Conductor Endpoints
# ---------------------------------------------------------------------------

@router.get("/conductor/status")
async def conductor_status():
    """Get the AI-native conductor status."""
    try:
        from sparkai.engine.engine_ai_native_conductor import get_conductor
        conductor = get_conductor()
        if not conductor._initialized:
            conductor.initialize()
        return JSONResponse({"status": "success", "data": conductor.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/conductor/cycle")
async def conductor_cycle():
    """Run one conductor cycle."""
    try:
        from sparkai.engine.engine_ai_native_conductor import get_conductor
        conductor = get_conductor()
        if not conductor._initialized:
            conductor.initialize()
        decision = conductor.cycle()
        return JSONResponse({"status": "success", "data": {
            "cycle_id": decision.cycle_id,
            "phase": decision.phase.value,
            "physics_adjustments": [
                {
                    "kind": a.kind.value, "target": a.target,
                    "args": a.args, "rationale": a.rationale,
                    "applied": a.applied,
                }
                for a in decision.physics_adjustments
            ],
            "render_adjustments": [
                {
                    "kind": a.kind.value, "target": a.target,
                    "args": a.args, "rationale": a.rationale,
                    "applied": a.applied,
                }
                for a in decision.render_adjustments
            ],
            "scene_adjustments": [
                {
                    "kind": a.kind.value, "target": a.target,
                    "args": a.args, "rationale": a.rationale,
                    "applied": a.applied,
                }
                for a in decision.scene_adjustments
            ],
            "duration_s": decision.duration_s,
            "notes": decision.notes,
        }})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/conductor/physics")
async def conductor_physics(req: PhysicsAdjustmentRequest):
    """Submit a manual physics adjustment."""
    try:
        from sparkai.engine.engine_ai_native_conductor import get_conductor
        conductor = get_conductor()
        if not conductor._initialized:
            conductor.initialize()
        adj = conductor.submit_physics_adjustment(
            req.kind, req.target, req.args, req.rationale,
        )
        return JSONResponse({"status": "success", "data": {
            "adjustment_id": adj.adjustment_id,
            "kind": adj.kind.value,
            "target": adj.target,
            "applied": adj.applied,
        }})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/conductor/render")
async def conductor_render(req: RenderAdjustmentRequest):
    """Submit a manual render adjustment."""
    try:
        from sparkai.engine.engine_ai_native_conductor import get_conductor
        conductor = get_conductor()
        if not conductor._initialized:
            conductor.initialize()
        adj = conductor.submit_render_adjustment(
            req.kind, req.target, req.args, req.rationale,
        )
        return JSONResponse({"status": "success", "data": {
            "adjustment_id": adj.adjustment_id,
            "kind": adj.kind.value,
            "target": adj.target,
            "applied": adj.applied,
        }})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/conductor/scene")
async def conductor_scene(req: SceneAdjustmentRequest):
    """Submit a manual scene adjustment."""
    try:
        from sparkai.engine.engine_ai_native_conductor import get_conductor
        conductor = get_conductor()
        if not conductor._initialized:
            conductor.initialize()
        adj = conductor.submit_scene_adjustment(
            req.kind, req.target, req.args, req.rationale,
        )
        return JSONResponse({"status": "success", "data": {
            "adjustment_id": adj.adjustment_id,
            "kind": adj.kind.value,
            "target": adj.target,
            "applied": adj.applied,
        }})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/conductor/reset")
async def conductor_reset():
    """Reset the conductor state."""
    try:
        from sparkai.engine.engine_ai_native_conductor import get_conductor
        conductor = get_conductor()
        conductor.reset()
        return JSONResponse({"status": "success", "data": {"reset": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
