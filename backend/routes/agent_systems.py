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


@router.get("/systems/debriefs")
async def agent_run_reports(limit: int = 10, agent_name: str = "SparkAgent"):
    """Return mission debriefs (after-action reports) for completed runs."""
    try:
        agent = _get_or_create_agent(agent_name)
        return JSONResponse({
            "status": "success",
            "data": {
                "reports": agent.get_run_reports(limit=limit),
                "total": len(agent.get_run_reports(limit=100)),
            }
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/debriefs/latest")
async def agent_latest_run_report(agent_name: str = "SparkAgent"):
    """Return the most recent mission debrief."""
    try:
        agent = _get_or_create_agent(agent_name)
        return JSONResponse({
            "status": "success",
            "data": agent._last_run_report,
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


class EmotionRequest(BaseModel):
    stimulus: dict = {}
    intensity: str = "moderate"
    agent_name: str = "SparkAgent"


class SetEmotionRequest(BaseModel):
    emotion_type: str
    value: float = 0.5
    agent_name: str = "SparkAgent"


@router.get("/systems/emotion")
async def agent_emotional_state(agent_name: str = "SparkAgent"):
    """Return the agent's current emotional state and mood."""
    try:
        agent = _get_or_create_agent(agent_name)
        return JSONResponse({"status": "success", "data": agent.get_emotional_state()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/systems/emotion/stimulus")
async def agent_emotional_stimulus(req: EmotionRequest):
    """Feed an emotional stimulus into the agent's emotional state."""
    try:
        agent = _get_or_create_agent(req.agent_name)
        state = agent.apply_emotional_stimulus(req.stimulus, req.intensity)
        return JSONResponse({"status": "success", "data": state})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/systems/emotion/set")
async def agent_set_emotion(req: SetEmotionRequest):
    """Directly set an emotion level on the agent."""
    try:
        agent = _get_or_create_agent(req.agent_name)
        state = agent.set_emotion(req.emotion_type, req.value)
        return JSONResponse({"status": "success", "data": state})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


class CounterfactualRequest(BaseModel):
    candidates: list = []
    goal: str = ""
    frames: int = 60
    agent_name: str = "SparkAgent"


@router.post("/systems/counterfactual")
async def agent_counterfactual_reason(req: CounterfactualRequest):
    """Evaluate candidate actions by sandbox simulation and rank them."""
    try:
        agent = _get_or_create_agent(req.agent_name)
        decision = agent.reason_counterfactually(
            candidates=req.candidates,
            goal=req.goal,
            frames=req.frames,
        )
        return JSONResponse({"status": "success", "data": decision})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/counterfactual")
async def agent_counterfactual_history(limit: int = 10, agent_name: str = "SparkAgent"):
    """Return recent counterfactual decision logs."""
    try:
        agent = _get_or_create_agent(agent_name)
        return JSONResponse({
            "status": "success",
            "data": {
                "decisions": agent.get_counterfactual_decisions(limit=limit),
                "total": len(agent.get_counterfactual_decisions(limit=500)),
            }
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


class PolicyCommitRequest(BaseModel):
    action_type: str = "create_entity"
    params: dict = {}
    goal: str = ""
    description: str = ""
    agent_name: str = "SparkAgent"


class AutonomyRequest(BaseModel):
    raw_confidence: float = 0.5
    high_threshold: float = 0.8
    review_threshold: float = 0.5
    description: str = ""
    agent_name: str = "SparkAgent"


class ReasonAndCommitRequest(BaseModel):
    candidates: list = []
    goal: str = ""
    frames: int = 60
    agent_name: str = "SparkAgent"


@router.post("/systems/policy/commit")
async def agent_policy_commit(req: PolicyCommitRequest):
    """Apply an action to the LIVE game world and record the outcome."""
    try:
        agent = _get_or_create_agent(req.agent_name)
        record = agent.commit_policy_action(
            action_type=req.action_type,
            params=req.params,
            goal=req.goal,
            description=req.description,
        )
        return JSONResponse({"status": "success", "data": record})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/systems/policy/reason-and-commit")
async def agent_policy_reason_and_commit(req: ReasonAndCommitRequest):
    """Reason counterfactually, then commit the recommended candidate to the live world."""
    try:
        agent = _get_or_create_agent(req.agent_name)
        result = agent.reason_and_commit(
            candidates=req.candidates,
            goal=req.goal,
            frames=req.frames,
        )
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/policy/commits")
async def agent_policy_commits(limit: int = 10, agent_name: str = "SparkAgent"):
    """Return the recent policy commit history."""
    try:
        agent = _get_or_create_agent(agent_name)
        return JSONResponse({
            "status": "success",
            "data": {
                "commits": agent.get_policy_commits(limit=limit),
                "total": len(agent.get_policy_commits(limit=500)),
            }
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/calibration")
async def agent_calibration(agent_name: str = "SparkAgent"):
    """Return the agent's prediction-calibration reliability profile."""
    try:
        agent = _get_or_create_agent(agent_name)
        agent.ingest_commits_for_calibration()
        return JSONResponse({
            "status": "success",
            "data": agent.get_calibration(),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/systems/calibration/assess-autonomy")
async def agent_assess_autonomy(req: AutonomyRequest):
    """Gate an intended action by the agent's calibrated confidence."""
    try:
        agent = _get_or_create_agent(req.agent_name)
        result = agent.assess_autonomy(
            raw_confidence=req.raw_confidence,
            high_threshold=req.high_threshold,
            review_threshold=req.review_threshold,
            description=req.description,
        )
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# === Proactive Autonomous Initiative ===

class PursueGoalRequest(BaseModel):
    max_iterations: int = 6
    agent_name: str = "SparkAgent"


@router.get("/systems/goals")
async def agent_discover_goals(max_goals: int = 6, agent_name: str = "SparkAgent"):
    """Observe the live world and return ranked candidate goals."""
    try:
        agent = _get_or_create_agent(agent_name)
        goals = agent.discover_goals(max_goals=max_goals)
        return JSONResponse({
            "status": "success",
            "data": {"goals": goals, "total": len(goals)},
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/goals/history")
async def agent_goals_history(limit: int = 20, agent_name: str = "SparkAgent"):
    """Return the recent goal-discovery history."""
    try:
        agent = _get_or_create_agent(agent_name)
        discoverer = agent._get_goal_discoverer()
        return JSONResponse({
            "status": "success",
            "data": {
                "history": discoverer.get_history(limit=limit),
                "statistics": discoverer.get_statistics(),
            },
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/systems/goals/{goal_id}/pursue")
async def agent_pursue_goal(goal_id: str, req: PursueGoalRequest):
    """Pursue a discovered goal through the autonomy-gated autonomous loop."""
    try:
        agent = _get_or_create_agent(req.agent_name)
        result = agent.pursue_discovered_goal(
            goal_id=goal_id,
            max_iterations=req.max_iterations,
        )
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/forecast")
async def agent_forecast_world(
    horizon_frames: int = 60,
    delta_time: float = 0.01667,
    agent_name: str = "SparkAgent",
):
    """Project the live world forward and return a forecast summary."""
    try:
        agent = _get_or_create_agent(agent_name)
        forecast = agent.forecast_world(
            horizon_frames=horizon_frames,
            delta_time=delta_time,
        )
        return JSONResponse({"status": "success", "data": forecast})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/forecast/history")
async def agent_forecast_history(limit: int = 10, agent_name: str = "SparkAgent"):
    """Return recent world-forecast history and statistics."""
    try:
        agent = _get_or_create_agent(agent_name)
        forecaster = agent._get_world_forecaster()
        return JSONResponse({
            "status": "success",
            "data": {
                "history": forecaster.get_history(limit=limit),
                "statistics": forecaster.get_statistics(),
            },
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# === World Stewardship Cycle ===

@router.post("/systems/stewardship/run")
async def agent_run_stewardship(agent_name: str = "SparkAgent"):
    """Execute one full world stewardship cycle and return the audit report."""
    try:
        agent = _get_or_create_agent(agent_name)
        report = agent.run_stewardship_cycle()
        return JSONResponse({"status": "success", "data": report})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/stewardship/history")
async def agent_stewardship_history(limit: int = 10, agent_name: str = "SparkAgent"):
    """Return recent stewardship cycle reports and statistics."""
    try:
        agent = _get_or_create_agent(agent_name)
        steward = agent._get_world_steward()
        return JSONResponse({
            "status": "success",
            "data": {
                "history": steward.get_history(limit=limit),
                "statistics": steward.get_statistics(),
            },
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/stewardship/candidates")
async def agent_stewardship_candidates(agent_name: str = "SparkAgent"):
    """Preview the dynamic candidates the steward would synthesize now."""
    try:
        agent = _get_or_create_agent(agent_name)
        result = agent.preview_stewardship_candidates()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ==================================================================
# Dream Cycle — offline experience consolidation
# ==================================================================

@router.post("/systems/dream/run")
async def agent_dream_run(agent_name: str = "SparkAgent"):
    """Execute one dream cycle and return the dream report."""
    try:
        agent = _get_or_create_agent(agent_name)
        report = agent.run_dream_cycle()
        return JSONResponse({"status": "success", "data": report})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/dream/history")
async def agent_dream_history(limit: int = 10, agent_name: str = "SparkAgent"):
    """Return recent dream reports."""
    try:
        agent = _get_or_create_agent(agent_name)
        history = agent.get_dream_history(limit=limit)
        return JSONResponse({"status": "success", "data": {"history": history, "total": len(history)}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/dream/statistics")
async def agent_dream_statistics(agent_name: str = "SparkAgent"):
    """Return aggregate dream statistics."""
    try:
        agent = _get_or_create_agent(agent_name)
        stats = agent.get_dream_statistics()
        return JSONResponse({"status": "success", "data": stats})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ==================================================================
# Causal Atlas — cause-effect reasoning
# ==================================================================

class CausalRecordRequest(BaseModel):
    cause_label: str
    effect_label: str
    cause_type: str = "action"
    effect_type: str = "state_change"
    entity_id: str = ""
    scene_id: str = ""
    confidence: float = 0.6
    context: str = ""


@router.post("/systems/causal/record")
async def agent_causal_record(req: CausalRecordRequest, agent_name: str = "SparkAgent"):
    """Record a cause-effect relationship in the causal atlas."""
    try:
        agent = _get_or_create_agent(agent_name)
        result = agent.record_causal(
            cause_label=req.cause_label,
            effect_label=req.effect_label,
            cause_type=req.cause_type,
            effect_type=req.effect_type,
            entity_id=req.entity_id,
            scene_id=req.scene_id,
            confidence=req.confidence,
            context=req.context,
        )
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/causal/explain")
async def agent_causal_explain(event_label: str, max_depth: int = 5, agent_name: str = "SparkAgent"):
    """Trace backward from an event to find its root causes."""
    try:
        agent = _get_or_create_agent(agent_name)
        chain = agent.explain_causal(event_label, max_depth=max_depth)
        return JSONResponse({"status": "success", "data": chain})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/causal/predict")
async def agent_causal_predict(action_label: str, max_depth: int = 5, agent_name: str = "SparkAgent"):
    """Trace forward from an action to predict its likely effects."""
    try:
        agent = _get_or_create_agent(agent_name)
        chain = agent.predict_causal(action_label, max_depth=max_depth)
        return JSONResponse({"status": "success", "data": chain})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/causal/path")
async def agent_causal_path(from_label: str, to_label: str, agent_name: str = "SparkAgent"):
    """Find a causal chain connecting two events."""
    try:
        agent = _get_or_create_agent(agent_name)
        chain = agent.find_causal_path(from_label, to_label)
        return JSONResponse({"status": "success", "data": chain})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/causal/statistics")
async def agent_causal_statistics(agent_name: str = "SparkAgent"):
    """Return causal atlas statistics."""
    try:
        agent = _get_or_create_agent(agent_name)
        stats = agent.get_causal_statistics()
        return JSONResponse({"status": "success", "data": stats})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/systems/causal/events")
async def agent_causal_events(limit: int = 50, agent_name: str = "SparkAgent"):
    """Return recent causal events."""
    try:
        agent = _get_or_create_agent(agent_name)
        events = agent.get_causal_events(limit=limit)
        return JSONResponse({"status": "success", "data": {"events": events, "total": len(events)}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


