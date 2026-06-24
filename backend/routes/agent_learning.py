"""
SparkLabs Backend - Agent Learning & Team Routes

API endpoints for self-improving learning loop, team factory orchestration,
and world simulation.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# ── Request Models ──

class StartSessionRequest(BaseModel):
    task_description: str


class ObserveRequest(BaseModel):
    session_id: str
    observation_type: str
    data: Dict[str, Any] = {}


class RecordActionRequest(BaseModel):
    session_id: str
    action: str
    params: Dict[str, Any] = {}
    result: Any = None


class EvaluateRequest(BaseModel):
    session_id: str
    success: bool
    metrics: Optional[Dict[str, Any]] = None


class ConsolidateRequest(BaseModel):
    session_id: str


class PromoteSkillRequest(BaseModel):
    skill_id: str


class CreateTeamRequest(BaseModel):
    domain: str
    team_type: str = "code_generation"
    custom_agents: Optional[List[Dict[str, Any]]] = None


class DispatchTaskRequest(BaseModel):
    blueprint_id: str
    task_description: str
    context: Optional[Dict[str, Any]] = None


class CompleteTaskRequest(BaseModel):
    task_id: str
    result: Dict[str, Any]
    success: bool = True


class CreateWorldRequest(BaseModel):
    name: str
    description: str = ""
    size_x: int = 100
    size_y: int = 100
    agent_count: int = 10
    max_ticks: int = 10000
    tick_rate: float = 1.0


class AddAgentRequest(BaseModel):
    name: str
    personality: Dict[str, float] = {}


class AddObjectRequest(BaseModel):
    name: str
    object_type: str
    x: float = 0.0
    y: float = 0.0
    properties: Optional[Dict[str, Any]] = None


class BroadcastEventRequest(BaseModel):
    event_type: str
    description: str
    target_agents: Optional[List[str]] = None


class EditAgentRequest(BaseModel):
    agent_id: str
    updates: Dict[str, Any]


# ── Learning Loop Endpoints ──

@router.post("/learning/initialize")
async def initialize_learning_loop():
    """Initialize the self-improving learning loop engine."""
    try:
        from sparkai.agent.agent_learning_loop import LearningLoopEngine

        engine = LearningLoopEngine.get_instance()
        engine.initialize()
        return {
            "status": "success",
            "data": {
                "initialized": True,
                "memory": engine.get_memory_statistics(),
                "skills": engine.get_skill_statistics(),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/learning/session/start")
async def start_learning_session(request: StartSessionRequest):
    """Start a new learning session."""
    try:
        from sparkai.agent.agent_learning_loop import LearningLoopEngine

        engine = LearningLoopEngine.get_instance()
        if not engine._initialized:
            engine.initialize()

        session = engine.start_session(request.task_description)
        return {
            "status": "success",
            "data": session.to_dict(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/learning/session/observe")
async def observe_session(request: ObserveRequest):
    """Record an observation in a learning session."""
    try:
        from sparkai.agent.agent_learning_loop import LearningLoopEngine

        engine = LearningLoopEngine.get_instance()
        engine.observe(request.session_id, request.observation_type, request.data)
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/learning/session/action")
async def record_action(request: RecordActionRequest):
    """Record an action taken in a learning session."""
    try:
        from sparkai.agent.agent_learning_loop import LearningLoopEngine

        engine = LearningLoopEngine.get_instance()
        engine.record_action(
            request.session_id, request.action, request.params, request.result
        )
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/learning/session/evaluate")
async def evaluate_session(request: EvaluateRequest):
    """Evaluate a learning session and generate lessons."""
    try:
        from sparkai.agent.agent_learning_loop import LearningLoopEngine

        engine = LearningLoopEngine.get_instance()
        lessons = engine.evaluate(
            request.session_id, request.success, request.metrics
        )
        return {
            "status": "success",
            "data": {
                "lessons": lessons,
                "count": len(lessons),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/learning/session/consolidate")
async def consolidate_session(request: ConsolidateRequest):
    """Consolidate learnings and potentially generate a skill."""
    try:
        from sparkai.agent.agent_learning_loop import LearningLoopEngine

        engine = LearningLoopEngine.get_instance()
        skill = engine.consolidate(request.session_id)
        return {
            "status": "success",
            "data": {
                "skill_generated": skill.to_dict() if skill else None,
                "has_skill": skill is not None,
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/learning/sessions")
async def get_learning_sessions():
    """Get all active learning sessions."""
    try:
        from sparkai.agent.agent_learning_loop import LearningLoopEngine

        engine = LearningLoopEngine.get_instance()
        return {
            "status": "success",
            "data": {
                "active": engine.get_active_sessions(),
                "history": engine.get_session_history(limit=20),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/learning/skills")
async def get_skills():
    """Get all active skills."""
    try:
        from sparkai.agent.agent_learning_loop import LearningLoopEngine

        engine = LearningLoopEngine.get_instance()
        return {
            "status": "success",
            "data": {
                "skills": engine.get_skills(),
                "statistics": engine.get_skill_statistics(),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/learning/skills/promote")
async def promote_skill(request: PromoteSkillRequest):
    """Promote a draft skill to active."""
    try:
        from sparkai.agent.agent_learning_loop import LearningLoopEngine

        engine = LearningLoopEngine.get_instance()
        success = engine.promote_skill(request.skill_id)
        return {
            "status": "success" if success else "error",
            "data": {"promoted": success},
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/learning/skills/deprecate")
async def deprecate_skill(request: PromoteSkillRequest):
    """Deprecate an active skill."""
    try:
        from sparkai.agent.agent_learning_loop import LearningLoopEngine

        engine = LearningLoopEngine.get_instance()
        success = engine.deprecate_skill(request.skill_id)
        return {
            "status": "success" if success else "error",
            "data": {"deprecated": success},
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/learning/memory")
async def get_memory_stats():
    """Get memory system statistics."""
    try:
        from sparkai.agent.agent_learning_loop import LearningLoopEngine

        engine = LearningLoopEngine.get_instance()
        return {
            "status": "success",
            "data": engine.get_memory_statistics(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/learning/memory/search")
async def search_memory(keyword: str, limit: int = 20):
    """Search across all memory tiers."""
    try:
        from sparkai.agent.agent_learning_loop import LearningLoopEngine

        engine = LearningLoopEngine.get_instance()
        results = engine.search_memory(keyword, limit)
        return {
            "status": "success",
            "data": {
                "results": results,
                "count": len(results),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ── Team Factory Endpoints ──

@router.post("/team/initialize")
async def initialize_team_factory():
    """Initialize the team factory engine."""
    try:
        from sparkai.agent.agent_team_factory import TeamFactory

        factory = TeamFactory.get_instance()
        factory.initialize()
        return {
            "status": "success",
            "data": {
                "initialized": True,
                "team_types": factory.list_team_types(),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/team/create")
async def create_team(request: CreateTeamRequest):
    """Create a new team blueprint."""
    try:
        from sparkai.agent.agent_team_factory import TeamFactory

        factory = TeamFactory.get_instance()
        if not factory._initialized:
            factory.initialize()

        blueprint = factory.create_team(
            request.domain, request.team_type, request.custom_agents
        )
        return {
            "status": "success",
            "data": blueprint.to_dict(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/team/dispatch")
async def dispatch_task(request: DispatchTaskRequest):
    """Dispatch a task to a team."""
    try:
        from sparkai.agent.agent_team_factory import TeamFactory

        factory = TeamFactory.get_instance()
        task = factory.dispatch_task(
            request.blueprint_id, request.task_description, request.context
        )
        return {
            "status": "success",
            "data": task.to_dict(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/team/complete")
async def complete_task(request: CompleteTaskRequest):
    """Complete a team task."""
    try:
        from sparkai.agent.agent_team_factory import TeamFactory

        factory = TeamFactory.get_instance()
        task = factory.complete_task(
            request.task_id, request.result, request.success
        )
        return {
            "status": "success",
            "data": task.to_dict() if task else None,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/team/blueprints")
async def list_blueprints():
    """List all team blueprints."""
    try:
        from sparkai.agent.agent_team_factory import TeamFactory

        factory = TeamFactory.get_instance()
        return {
            "status": "success",
            "data": {
                "blueprints": factory.list_blueprints(),
                "count": len(factory.list_blueprints()),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/team/blueprints/{blueprint_id}")
async def get_blueprint(blueprint_id: str):
    """Get a specific team blueprint."""
    try:
        from sparkai.agent.agent_team_factory import TeamFactory

        factory = TeamFactory.get_instance()
        blueprint = factory.get_team_blueprint(blueprint_id)
        if not blueprint:
            raise HTTPException(status_code=404, detail="Blueprint not found")
        return {
            "status": "success",
            "data": blueprint.to_dict(),
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/team/types")
async def list_team_types():
    """List available team types."""
    try:
        from sparkai.agent.agent_team_factory import TeamFactory

        factory = TeamFactory.get_instance()
        return {
            "status": "success",
            "data": factory.list_team_types(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/team/tasks")
async def get_team_tasks():
    """Get active and completed team tasks."""
    try:
        from sparkai.agent.agent_team_factory import TeamFactory

        factory = TeamFactory.get_instance()
        return {
            "status": "success",
            "data": {
                "active": factory.get_active_tasks(),
                "completed": factory.get_completed_tasks(limit=20),
                "statistics": factory.get_statistics(),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ── World Simulator Endpoints ──

@router.post("/world/initialize")
async def initialize_world(request: CreateWorldRequest):
    """Create and initialize a new simulated world."""
    try:
        from sparkai.agent.agent_world_simulator import (
            WorldSimulator, WorldConfig,
        )

        config = WorldConfig(
            name=request.name,
            description=request.description,
            size=(request.size_x, request.size_y),
            agent_count=request.agent_count,
            max_ticks=request.max_ticks,
            tick_rate=request.tick_rate,
        )

        simulator = WorldSimulator.get_instance()
        simulator.initialize(config)
        return {
            "status": "success",
            "data": simulator.get_world_state(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/world/tick")
async def tick_world():
    """Advance the simulation by one tick."""
    try:
        from sparkai.agent.agent_world_simulator import WorldSimulator

        simulator = WorldSimulator.get_instance()
        events = simulator.tick()
        return {
            "status": "success",
            "data": {
                "events": [e.to_dict() for e in events],
                "event_count": len(events),
                "world_state": simulator.get_world_state(),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/world/tick-multiple")
async def tick_multiple(ticks: int = 10):
    """Advance the simulation by multiple ticks."""
    try:
        from sparkai.agent.agent_world_simulator import WorldSimulator

        simulator = WorldSimulator.get_instance()
        total_events = []
        for _ in range(min(ticks, 100)):
            events = simulator.tick()
            total_events.extend(events)
        return {
            "status": "success",
            "data": {
                "events": [e.to_dict() for e in total_events[-50:]],
                "total_events": len(total_events),
                "world_state": simulator.get_world_state(),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/world/pause")
async def pause_world():
    """Pause the simulation."""
    try:
        from sparkai.agent.agent_world_simulator import WorldSimulator

        simulator = WorldSimulator.get_instance()
        simulator.pause()
        return {
            "status": "success",
            "data": simulator.get_world_state(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/world/resume")
async def resume_world():
    """Resume the simulation."""
    try:
        from sparkai.agent.agent_world_simulator import WorldSimulator

        simulator = WorldSimulator.get_instance()
        simulator.resume()
        return {
            "status": "success",
            "data": simulator.get_world_state(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/world/stop")
async def stop_world():
    """Stop the simulation."""
    try:
        from sparkai.agent.agent_world_simulator import WorldSimulator

        simulator = WorldSimulator.get_instance()
        simulator.stop()
        return {
            "status": "success",
            "data": simulator.get_world_state(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/world/agent")
async def add_agent(request: AddAgentRequest):
    """Add an agent to the world."""
    try:
        from sparkai.agent.agent_world_simulator import WorldSimulator

        simulator = WorldSimulator.get_instance()
        agent = simulator.add_agent(request.name, request.personality)
        return {
            "status": "success",
            "data": agent.to_dict(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/world/object")
async def add_object(request: AddObjectRequest):
    """Add an object to the world."""
    try:
        from sparkai.agent.agent_world_simulator import (
            WorldSimulator, Position,
        )

        simulator = WorldSimulator.get_instance()
        obj = simulator.add_object(
            request.name, request.object_type,
            Position(request.x, request.y),
            request.properties,
        )
        return {
            "status": "success",
            "data": obj.to_dict(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/world/broadcast")
async def broadcast_event(request: BroadcastEventRequest):
    """Broadcast an event (God Mode)."""
    try:
        from sparkai.agent.agent_world_simulator import WorldSimulator

        simulator = WorldSimulator.get_instance()
        event = simulator.broadcast_event(
            request.event_type, request.description, request.target_agents
        )
        return {
            "status": "success",
            "data": event.to_dict(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/world/agent/edit")
async def edit_agent(request: EditAgentRequest):
    """Edit an agent's state (God Mode)."""
    try:
        from sparkai.agent.agent_world_simulator import WorldSimulator

        simulator = WorldSimulator.get_instance()
        agent = simulator.edit_agent(request.agent_id, request.updates)
        if agent:
            return {
                "status": "success",
                "data": agent.to_dict(),
            }
        return JSONResponse(status_code=404, content={"status": "error", "message": "Agent not found"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/world/state")
async def get_world_state():
    """Get current world state."""
    try:
        from sparkai.agent.agent_world_simulator import WorldSimulator

        simulator = WorldSimulator.get_instance()
        return {
            "status": "success",
            "data": simulator.get_world_state(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/world/agents")
async def get_agents():
    """Get all agents in the world."""
    try:
        from sparkai.agent.agent_world_simulator import WorldSimulator

        simulator = WorldSimulator.get_instance()
        return {
            "status": "success",
            "data": {
                "agents": simulator.get_all_agents(),
                "count": len(simulator.get_all_agents()),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/world/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get a specific agent."""
    try:
        from sparkai.agent.agent_world_simulator import WorldSimulator

        simulator = WorldSimulator.get_instance()
        agent = simulator.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {
            "status": "success",
            "data": agent,
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/world/objects")
async def get_objects():
    """Get all objects in the world."""
    try:
        from sparkai.agent.agent_world_simulator import WorldSimulator

        simulator = WorldSimulator.get_instance()
        return {
            "status": "success",
            "data": {
                "objects": simulator.get_all_objects(),
                "count": len(simulator.get_all_objects()),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/world/events")
async def get_events(limit: int = 50):
    """Get recent world events."""
    try:
        from sparkai.agent.agent_world_simulator import WorldSimulator

        simulator = WorldSimulator.get_instance()
        return {
            "status": "success",
            "data": {
                "events": simulator.get_events(limit),
                "count": min(len(simulator.get_events(limit)), limit),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})