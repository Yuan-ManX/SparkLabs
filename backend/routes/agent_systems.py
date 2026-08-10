"""
SparkLabs Backend - Agent Systems API Routes

Exposes the agent's internal systems: memory, context management,
trajectory timeline, and perception-decision pipeline.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class ThinkRequest(BaseModel):
    prompt: str
    agent_name: str = "SparkAgent"


class ActRequest(BaseModel):
    action: str
    params: dict = {}
    agent_name: str = "SparkAgent"


class ReflectRequest(BaseModel):
    query: str
    agent_name: str = "SparkAgent"


# Global agent registry for API access
_agents: dict = {}


def _get_or_create_agent(name: str = "SparkAgent"):
    if name not in _agents:
        from sparkai.agent.base import SparkAgent, AgentRole, AgentCapability
        from sparkai.agent.llm import LLMProvider, LLMConfig
        from sparkai.agent.toolkit import create_engine_toolset
        from sparkai.agent.engine_bridge import get_engine_bridge_handlers

        agent = SparkAgent(
            name=name,
            role=AgentRole.SPECIALIST,
            capabilities=[
                AgentCapability.REASONING,
                AgentCapability.WORLD_BUILDING,
                AgentCapability.CODE_GENERATION,
            ],
        )
        # LLM will be initialized lazily on first use
        config = LLMConfig(provider="simulation", model="spark-sim-v1")
        llm = LLMProvider(config)
        agent.set_llm_provider(llm)

        engine_toolset = create_engine_toolset()
        agent.tools.load_toolset(engine_toolset.tools())

        # Initialize perception pipeline with engine bridge
        class BridgeWrapper:
            def get_engine_bridge_handlers(self):
                return get_engine_bridge_handlers()

        agent.init_perception_pipeline(BridgeWrapper())
        _agents[name] = agent
    return _agents[name]


@router.get("/systems/status")
async def agent_systems_status():
    """Get status of all agent internal systems."""
    try:
        agent = _get_or_create_agent()
        return JSONResponse({"status": "success", "data": agent.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/systems/think")
async def agent_think(req: ThinkRequest):
    """Run the agent's think phase with context management."""
    try:
        agent = _get_or_create_agent(req.agent_name)
        response = await agent.think(req.prompt)
        return JSONResponse({
            "status": "success",
            "data": {
                "response": response,
                "context_stats": agent.context_manager.get_statistics(),
            }
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/systems/act")
async def agent_act(req: ActRequest):
    """Run the agent's act phase with trajectory recording."""
    try:
        agent = _get_or_create_agent(req.agent_name)
        result = await agent.act(req.action, req.params)
        return JSONResponse({
            "status": "success",
            "data": {
                "result": result,
                "trajectory_stats": agent.trajectory.get_statistics(),
            }
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/systems/reflect")
async def agent_reflect(req: ReflectRequest):
    """Generate a reflection from memories and store in the reflection DAG."""
    try:
        agent = _get_or_create_agent(req.agent_name)
        reflection = await agent.reflect_on_memories(req.query)
        return JSONResponse({
            "status": "success",
            "data": {"reflection": reflection}
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/systems/perceive-and-decide")
async def agent_perceive_and_decide():
    """Run the perception-menu-decision pipeline."""
    try:
        agent = _get_or_create_agent()
        decision = await agent.perceive_and_decide()
        if decision:
            return JSONResponse({
                "status": "success",
                "data": {
                    "action_id": decision.action_id,
                    "action_label": decision.action_label,
                    "target_id": decision.target_id,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning,
                }
            })
        return JSONResponse({
            "status": "success",
            "data": None,
            "message": "Perception pipeline not initialized"
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/trajectory")
async def agent_trajectory(limit: int = 50):
    """Get the agent's action trajectory timeline."""
    try:
        agent = _get_or_create_agent()
        return JSONResponse({
            "status": "success",
            "data": agent.trajectory.get_timeline(limit=limit)
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/trajectory/stats")
async def agent_trajectory_stats():
    """Get trajectory statistics."""
    try:
        agent = _get_or_create_agent()
        return JSONResponse({
            "status": "success",
            "data": agent.trajectory.get_statistics()
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/trajectory/export")
async def agent_trajectory_export():
    """Export trajectory as training data format."""
    try:
        agent = _get_or_create_agent()
        return JSONResponse({
            "status": "success",
            "data": agent.trajectory.export_trajectory()
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/memory")
async def agent_memory(memory_type: Optional[str] = None):
    """Get agent memories, optionally filtered by type."""
    try:
        agent = _get_or_create_agent()
        from sparkai.agent.memory import MemoryType
        mt = None
        if memory_type:
            mt = MemoryType(memory_type)
        memories = agent.memory.get_all(mt)
        return JSONResponse({
            "status": "success",
            "data": {
                "memories": memories,
                "total": len(memories),
                "emotional_state": agent.memory.get_emotional_summary(),
            }
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/context/stats")
async def agent_context_stats():
    """Get context manager statistics."""
    try:
        agent = _get_or_create_agent()
        return JSONResponse({
            "status": "success",
            "data": agent.context_manager.get_statistics()
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/systems/context/compress")
async def agent_context_compress():
    """Manually trigger context compression."""
    try:
        agent = _get_or_create_agent()
        saved = agent.context_manager.compress()
        return JSONResponse({
            "status": "success",
            "data": {"tokens_saved": saved}
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


class BuildGameRequest(BaseModel):
    concept: str
    agent_name: str = "SparkAgent"


@router.post("/systems/build-game")
async def agent_build_game(req: BuildGameRequest):
    """
    Build a runnable game world from a natural-language concept.

    Uses the shared agent's environment (memory, trajectory, engine
    toolset) plus the Game Build Director to construct a scene, entities,
    and GameLogicIR rules, then confirms behavior via verification.
    Returns the built world summary for the web editor.
    """
    try:
        agent = _get_or_create_agent(req.agent_name)
        from sparkai.agent.agent_game_builder import get_game_build_director
        director = get_game_build_director()
        result = director.build(req.concept).to_dict()

        # Record the build on the agent's trajectory + memory for auditability
        await agent.observe(
            f"Built game for concept: {req.concept}",
            importance=0.8,
        )
        agent.emit("game_build_complete", {
            "concept": req.concept,
            "scene_id": result.get("scene_id"),
            "status": result.get("status"),
        })

        return JSONResponse({
            "status": "success",
            "data": result,
            "agent_name": req.agent_name,
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


class RefineRequest(BaseModel):
    failure: str
    adjustment: str
    outcome: str = "pending"
    agent_name: str = "SparkAgent"


class RestoreStateRequest(BaseModel):
    state: dict
    agent_name: str = "SparkAgent"


@router.get("/systems/refinements")
async def agent_refinements(limit: int = 20, agent_name: str = "SparkAgent"):
    """Return the agent's experiential refinement history."""
    try:
        agent = _get_or_create_agent(agent_name)
        return JSONResponse({
            "status": "success",
            "data": {
                "refinements": agent.get_refinements(limit=limit),
                "total": len(agent.get_refinements()),
            }
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/systems/refinements")
async def agent_record_refinement(req: RefineRequest):
    """Persist a durable refinement lesson from a failure."""
    try:
        agent = _get_or_create_agent(req.agent_name)
        agent.record_refinement(req.failure, req.adjustment, req.outcome)
        return JSONResponse({
            "status": "success",
            "data": {"total": len(agent.get_refinements())},
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.delete("/systems/refinements")
async def agent_clear_refinements(agent_name: str = "SparkAgent"):
    """Clear the agent's experiential refinement history."""
    try:
        agent = _get_or_create_agent(agent_name)
        removed = agent.clear_refinements()
        return JSONResponse({"status": "success", "data": {"removed": removed}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/state")
async def agent_state(agent_name: str = "SparkAgent"):
    """Serialize the agent's identity and learned state for continuity."""
    try:
        agent = _get_or_create_agent(agent_name)
        return JSONResponse({"status": "success", "data": agent.to_state()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/systems/state/restore")
async def agent_restore_state(req: RestoreStateRequest):
    """Restore the agent from a previously serialized state snapshot."""
    try:
        agent = _get_or_create_agent(req.agent_name)
        ok = agent.restore_state(req.state)
        if not ok:
            return JSONResponse({"status": "error", "message": "Invalid state snapshot"}, status_code=400)
        return JSONResponse({
            "status": "success",
            "data": {"restored": True, "refinements": len(agent.get_refinements())},
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


class LearnRequest(BaseModel):
    goal: str = "autonomous"
    limit: int = 40
    agent_name: str = "SparkAgent"


class ExecuteSkillRequest(BaseModel):
    skill_id: str
    context: dict = {}
    agent_name: str = "SparkAgent"


@router.get("/systems/learning/skills")
async def agent_accumulated_skills(limit: int = 20, agent_name: str = "SparkAgent"):
    """Return the agent's accumulated skills derived from trajectory."""
    try:
        agent = _get_or_create_agent(agent_name)
        return JSONResponse({
            "status": "success",
            "data": {
                "skills": agent.get_accumulated_skills(limit=limit),
                "total": len(agent.get_accumulated_skills(limit=500)),
            }
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/systems/learning/learn")
async def agent_learn(req: LearnRequest):
    """Derive reusable skills from the agent's recent trajectory."""
    try:
        agent = _get_or_create_agent(req.agent_name)
        learned = agent.learn_from_trajectory(limit=req.limit, goal=req.goal)
        return JSONResponse({
            "status": "success",
            "data": {
                "learned": learned,
                "total_skills": len(agent.get_accumulated_skills(limit=500)),
            }
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/systems/learning/skills/execute")
async def agent_execute_skill(req: ExecuteSkillRequest):
    """Execute an accumulated skill and report the outcome."""
    try:
        agent = _get_or_create_agent(req.agent_name)
        result = agent.execute_accumulated_skill(req.skill_id, req.context)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
