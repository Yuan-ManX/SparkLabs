"""
SparkLabs Backend - Cognitive Kernel & Game Brain API Routes

REST API endpoints for the unified cognitive kernel, kernel-engine
integrator, and AI-native game brain. These endpoints expose the new
cognitive substrate so the web frontend and external clients can drive
real-time cognition, inspect state, and dispatch directorial directives.

Endpoints:
  GET  /cognitive-kernel/status        - Kernel status and memory stats
  POST /cognitive-kernel/perceive      - Inject a perception into the kernel
  POST /cognitive-kernel/goal          - Submit a goal for decomposition
  POST /cognitive-kernel/cycle         - Advance the kernel one cognitive cycle
  GET  /cognitive-kernel/recall        - Recall memories by query
  POST /cognitive-kernel/reset         - Reset the kernel state

  GET  /cognitive-integrator/status    - Integrator status and tick history
  POST /cognitive-integrator/tick      - Advance the integrator by one tick
  POST /cognitive-integrator/action    - Submit an engine command
  POST /cognitive-integrator/event     - Emit an engine event
  GET  /cognitive-integrator/history   - Recent integrator tick results
  POST /cognitive-integrator/reset     - Reset the integrator tick state

  GET  /game-brain/status              - Brain status (player, pacing, difficulty)
  POST /game-brain/tick                - Advance the brain by one cognitive tick
  POST /game-brain/directive           - Manually issue a directorial directive
  GET  /game-brain/directives          - List pending and dispatched directives
  POST /game-brain/reset               - Reset the brain state
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================


class PerceiveRequest(BaseModel):
    source: str = Field(default="user", description="Perception source")
    channel: str = Field(default="text", description="Perception channel")
    payload: Dict[str, Any] = Field(default_factory=dict)
    salience: float = Field(default=0.5, ge=0.0, le=1.0)


class GoalRequest(BaseModel):
    goal: str
    sub_tasks: List[Dict[str, Any]] = Field(default_factory=list)


class RecallRequest(BaseModel):
    query: str = ""
    limit: int = Field(default=8, ge=1, le=100)


class EngineActionRequest(BaseModel):
    kind: str = "custom"
    target: str = ""
    args: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    issued_by: str = "api"


class EngineEventRequest(BaseModel):
    kind: str = "tick"
    source: str = "api"
    payload: Dict[str, Any] = Field(default_factory=dict)
    tick: int = 0


class DirectiveRequest(BaseModel):
    kind: str = "custom"
    intent: str = ""
    args: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    confidence: float = 0.5
    expected_effect: str = ""


# =============================================================================
# Cognitive Kernel Endpoints
# =============================================================================


@router.get("/cognitive-kernel/status")
async def kernel_status():
    """Get the unified cognitive kernel status."""
    try:
        from sparkai.agent.agent_unified_kernel import AgentKernel
        kernel = AgentKernel.get_instance()
        if not kernel._initialized:
            kernel.initialize()
        return JSONResponse({"status": "success", "data": kernel.status()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-kernel/perceive")
async def kernel_perceive(req: PerceiveRequest):
    """Inject a perception into the kernel."""
    try:
        from sparkai.agent.agent_unified_kernel import AgentKernel
        kernel = AgentKernel.get_instance()
        if not kernel._initialized:
            kernel.initialize()
        perception = kernel.perceive(
            source=req.source,
            channel=req.channel,
            payload=req.payload,
            salience=req.salience,
        )
        return JSONResponse({
            "status": "success",
            "data": {
                "perception_id": perception.perception_id,
                "source": perception.source,
                "channel": perception.channel,
                "salience": perception.salience,
            },
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-kernel/goal")
async def kernel_goal(req: GoalRequest):
    """Submit a goal for HTN decomposition and planning."""
    try:
        from sparkai.agent.agent_unified_kernel import AgentKernel
        kernel = AgentKernel.get_instance()
        if not kernel._initialized:
            kernel.initialize()
        tasks = kernel.submit_goal(req.goal, req.sub_tasks)
        return JSONResponse({
            "status": "success",
            "data": {
                "goal": req.goal,
                "task_count": len(tasks),
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "name": t.name,
                        "status": t.status.value,
                        "tool": t.tool,
                    }
                    for t in tasks
                ],
            },
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-kernel/cycle")
async def kernel_cycle():
    """Advance the kernel by one cognitive cycle."""
    try:
        from sparkai.agent.agent_unified_kernel import AgentKernel
        kernel = AgentKernel.get_instance()
        if not kernel._initialized:
            kernel.initialize()
        result = kernel.cycle()
        return JSONResponse({
            "status": "success",
            "data": {
                "phase": result.phase.value,
                "perceptions_processed": result.perceptions_processed,
                "memories_written": result.memories_written,
                "reasoning_traces": result.reasoning_traces,
                "tasks_planned": result.tasks_planned,
                "tasks_executed": result.tasks_executed,
                "reflections": result.reflections,
                "skills_learned": result.skills_learned,
                "duration_s": result.duration_s,
            },
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/cognitive-kernel/recall")
async def kernel_recall(query: str = "", limit: int = 8):
    """Recall memories by query."""
    try:
        from sparkai.agent.agent_unified_kernel import AgentKernel
        kernel = AgentKernel.get_instance()
        if not kernel._initialized:
            kernel.initialize()
        memories = kernel.recall(query, limit)
        return JSONResponse({
            "status": "success",
            "data": {
                "query": query,
                "count": len(memories),
                "memories": [
                    {
                        "memory_id": m.memory_id,
                        "layer": m.layer.value,
                        "namespace": m.namespace,
                        "content": m.content if isinstance(m.content, (str, int, float)) else str(m.content)[:200],
                        "salience": m.salience,
                        "tags": list(m.tags),
                        "created_at": m.created_at,
                    }
                    for m in memories
                ],
            },
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-kernel/reset")
async def kernel_reset():
    """Reset the kernel state (preserves registered tools and skills)."""
    try:
        from sparkai.agent.agent_unified_kernel import AgentKernel
        kernel = AgentKernel.get_instance()
        kernel.reset()
        return JSONResponse({"status": "success", "data": {"reset": True}})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


# =============================================================================
# Cognitive Integrator Endpoints
# =============================================================================


@router.get("/cognitive-integrator/status")
async def integrator_status():
    """Get the kernel-engine integrator status."""
    try:
        from sparkai.engine.engine_kernel_integration import KernelEngineIntegrator
        integrator = KernelEngineIntegrator.get_instance()
        if not integrator._initialized:
            integrator.initialize()
        return JSONResponse({"status": "success", "data": integrator.status()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-integrator/tick")
async def integrator_tick():
    """Advance the integrator by one tick."""
    try:
        from sparkai.engine.engine_kernel_integration import KernelEngineIntegrator
        integrator = KernelEngineIntegrator.get_instance()
        if not integrator._initialized:
            integrator.initialize()
        result = integrator.tick()
        return JSONResponse({
            "status": "success",
            "data": {
                "tick": result.tick,
                "phase": result.phase.value,
                "events_collected": result.events_collected,
                "perceptions_encoded": result.perceptions_encoded,
                "kernel_cycle_ran": result.kernel_cycle_ran,
                "commands_dispatched": result.commands_dispatched,
                "snapshot_written": result.snapshot_written,
                "feedback_records": result.feedback_records,
                "duration_s": result.duration_s,
            },
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-integrator/action")
async def integrator_action(req: EngineActionRequest):
    """Submit an engine command through the integrator."""
    try:
        from sparkai.engine.engine_kernel_integration import (
            KernelEngineIntegrator, EngineCommand, EngineCommandKind,
        )
        integrator = KernelEngineIntegrator.get_instance()
        if not integrator._initialized:
            integrator.initialize()
        # Map string kind to enum (fallback to CUSTOM)
        try:
            kind_enum = EngineCommandKind(req.kind)
        except ValueError:
            kind_enum = EngineCommandKind.CUSTOM
        command = integrator.submit_action(
            kind=kind_enum,
            target=req.target,
            args=req.args,
            priority=req.priority,
            issued_by=req.issued_by,
        )
        return JSONResponse({
            "status": "success",
            "data": {
                "command_id": command.command_id,
                "kind": command.kind.value,
                "target": command.target,
                "priority": command.priority,
                "issued_by": command.issued_by,
                "pending": integrator.action_pipeline.pending_count(),
            },
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-integrator/event")
async def integrator_event(req: EngineEventRequest):
    """Emit an engine event into the integrator."""
    try:
        from sparkai.engine.engine_kernel_integration import (
            KernelEngineIntegrator, EngineEvent, EngineEventType,
        )
        integrator = KernelEngineIntegrator.get_instance()
        if not integrator._initialized:
            integrator.initialize()
        try:
            kind_enum = EngineEventType(req.kind)
        except ValueError:
            kind_enum = EngineEventType.CUSTOM
        event = EngineEvent(
            kind=kind_enum,
            source=req.source,
            payload=req.payload,
            tick=req.tick,
        )
        integrator.emit_event(event)
        return JSONResponse({
            "status": "success",
            "data": {
                "event_id": event.event_id,
                "kind": event.kind.value,
                "source": event.source,
                "tick": event.tick,
            },
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/cognitive-integrator/history")
async def integrator_history(limit: int = 16):
    """Return recent integrator tick results."""
    try:
        from sparkai.engine.engine_kernel_integration import KernelEngineIntegrator
        integrator = KernelEngineIntegrator.get_instance()
        return JSONResponse({
            "status": "success",
            "data": {
                "history": integrator.history(limit),
                "count": len(integrator.history(limit)),
            },
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-integrator/reset")
async def integrator_reset():
    """Reset the integrator tick state."""
    try:
        from sparkai.engine.engine_kernel_integration import KernelEngineIntegrator
        integrator = KernelEngineIntegrator.get_instance()
        integrator.reset()
        return JSONResponse({"status": "success", "data": {"reset": True}})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


# =============================================================================
# Game Brain Endpoints
# =============================================================================


@router.get("/game-brain/status")
async def brain_status():
    """Get the AI-native game brain status."""
    try:
        from sparkai.agent.agent_game_brain import GameBrain
        brain = GameBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        return JSONResponse({"status": "success", "data": brain.status()})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/game-brain/tick")
async def brain_tick():
    """Advance the game brain by one cognitive tick."""
    try:
        from sparkai.agent.agent_game_brain import GameBrain
        brain = GameBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        result = brain.tick()
        return JSONResponse({
            "status": "success",
            "data": {
                "tick": result.tick,
                "phase": result.phase.value,
                "player_modeled": result.player_modeled,
                "pacing_updated": result.pacing_updated,
                "directives_issued": result.directives_issued,
                "emergence_detected": result.emergence_detected,
                "duration_s": result.duration_s,
                "notes": result.notes,
            },
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/game-brain/directive")
async def brain_directive(req: DirectiveRequest):
    """Manually issue a directorial directive through the brain."""
    try:
        from sparkai.agent.agent_game_brain import GameBrain, Directive, DirectiveKind
        brain = GameBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        try:
            kind_enum = DirectiveKind(req.kind)
        except ValueError:
            kind_enum = DirectiveKind.CUSTOM
        directive = Directive(
            kind=kind_enum,
            intent=req.intent,
            args=req.args,
            priority=req.priority,
            confidence=req.confidence,
            expected_effect=req.expected_effect,
        )
        # Bypass coherence guard for manual directives
        brain._directive_queue.append(directive)
        if brain._integrator is not None:
            brain._forward_to_integrator()
        return JSONResponse({
            "status": "success",
            "data": {
                "directive_id": directive.directive_id,
                "kind": directive.kind.value,
                "intent": directive.intent,
                "priority": directive.priority,
                "confidence": directive.confidence,
            },
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/game-brain/directives")
async def brain_directives():
    """List pending and recently dispatched brain directives."""
    try:
        from sparkai.agent.agent_game_brain import GameBrain
        brain = GameBrain.get_instance()
        if not brain._initialized:
            brain.initialize()
        pending = brain.pending_directives()
        dispatched = brain.dispatched_directives(limit=16)
        return JSONResponse({
            "status": "success",
            "data": {
                "pending": [
                    {
                        "directive_id": d.directive_id,
                        "kind": d.kind.value,
                        "intent": d.intent,
                        "priority": d.priority,
                        "confidence": d.confidence,
                        "issued_at": d.issued_at,
                    }
                    for d in pending
                ],
                "dispatched": [
                    {
                        "directive_id": d.directive_id,
                        "kind": d.kind.value,
                        "intent": d.intent,
                        "priority": d.priority,
                        "confidence": d.confidence,
                        "issued_at": d.issued_at,
                    }
                    for d in dispatched
                ],
            },
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/game-brain/reset")
async def brain_reset():
    """Reset the game brain state."""
    try:
        from sparkai.agent.agent_game_brain import GameBrain
        brain = GameBrain.get_instance()
        brain.reset()
        return JSONResponse({"status": "success", "data": {"reset": True}})
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )
