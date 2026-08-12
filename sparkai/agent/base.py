"""
SparkAI Agent - Core Agent Foundation"""

from __future__ import annotations

import asyncio
import logging
import uuid
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

from sparkai.agent.memory import AgentMemory, MemoryType, NodeType
from sparkai.agent.toolkit import ToolRegistry, Tool, Toolset, ToolsetRegistry, get_tools_for_role
from sparkai.agent.llm import LLMProvider, LLMConfig
from sparkai.agent.skills.base import Skill, SkillRegistry
from sparkai.agent.agent_error_classifier import ErrorClassifier, get_error_classifier
from sparkai.agent.agent_tool_pruner import ToolOutputPruner, get_tool_output_pruner
from sparkai.agent.agent_file_state import FileStateEngine, get_file_state_engine
from sparkai.agent.context_manager import ContextManager, ContextBudget
from sparkai.agent.trajectory import TrajectoryRecorder, PermissionTier, get_trajectory_recorder
from sparkai.agent.perception import (
    PerceptionDecisionPipeline, PerceptionBuilder, ActionMenuBuilder,
    Perception, ActionMenuItem, Decision,
)


class AgentCapability(Enum):
    REASONING = "reasoning"
    CODE_GENERATION = "code_generation"
    NARRATIVE_GENERATION = "narrative_generation"
    ASSET_GENERATION = "asset_generation"
    WORLD_BUILDING = "world_building"
    GAMEPLAY_DESIGN = "gameplay_design"
    NPC_CONTROL = "npc_control"
    SCENE_MANAGEMENT = "scene_management"
    WORKFLOW_ORCHESTRATION = "workflow_orchestration"
    QUALITY_REVIEW = "quality_review"
    AUDIO_GENERATION = "audio_generation"
    VIDEO_GENERATION = "video_generation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class AgentState(Enum):
    IDLE = "idle"
    OBSERVING = "observing"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    VERIFYING = "verifying"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETED = "completed"


class AgentRole(Enum):
    DIRECTOR = "director"
    LEAD = "lead"
    SPECIALIST = "specialist"
    WORKER = "worker"


@dataclass
class AgentMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "agent"
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    assigned_to: str = ""
    status: str = "pending"
    priority: int = 0
    verification_criteria: str = ""
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    status_quo: str = ""
    target_end_state: str = ""
    end_state_checklist: List[str] = field(default_factory=list)
    work_plan: List[Dict[str, Any]] = field(default_factory=list)
    verification_gates: List[str] = field(default_factory=list)
    phase: str = "planning"
    status: str = "pending"
    iteration: int = 0
    max_iterations: int = 50
    created_at: float = field(default_factory=time.time)
    result: Optional[Any] = None


class SparkAgent:
    """
    Core Agent for the SparkLabs AI-Native Game Engine.

    Implements the four-phase autonomous loop:
        Observe -> Think -> Act -> Verify

    Each agent has:
    - A unique identity (name, role, capabilities)
    - A hierarchical memory system
    - A tool registry with composable toolsets
    - An LLM provider for reasoning
    - A state machine for lifecycle management
    - Event-driven communication
    - Contract-based verification
    """

    def __init__(
        self,
        name: str,
        role: AgentRole = AgentRole.SPECIALIST,
        capabilities: Optional[List[AgentCapability]] = None,
        agent_id: Optional[str] = None,
        max_iterations: int = 50,
    ):
        self.id = agent_id or str(uuid.uuid4())
        self.name = name
        self.role = role
        self.capabilities = capabilities or [AgentCapability.REASONING]
        self.state = AgentState.IDLE
        self.max_iterations = max_iterations

        self._memory = AgentMemory()
        self._tools = ToolRegistry()
        self._llm: Optional[LLMProvider] = None
        self._message_history: List[AgentMessage] = []
        self._current_task: Optional[AgentTask] = None
        self._current_plan: Optional[ExecutionPlan] = None
        self._task_history: List[AgentTask] = []
        self._plan_history: List[ExecutionPlan] = []
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._context: Dict[str, Any] = {}
        self._iteration_count: int = 0
        self._consecutive_failures: int = 0
        self._max_consecutive_failures: int = 5
        self._skills: Dict[str, Skill] = {}
        self._loaded_toolsets: List[str] = []

        # Game context injected into prompts (populated via set_game_context)
        self._game_context: Optional[Any] = None

        # Experiential refinement log: durable lessons from failures that
        # shape future reasoning. Kept bounded to avoid context bloat.
        self._refinements: List[Dict[str, Any]] = []
        self._max_refinements: int = 24

        # Progressive learning: reusable skills derived from successful
        # trajectory patterns. Backed by the shared SkillAccumulatorEngine
        # and injected into future prompts so the agent compounds competence.
        self._skill_accumulator = None

        # Mission debrief: structured after-action reports produced when an
        # autonomous run completes. Bounded list plus the latest report.
        self._run_reports: List[Dict[str, Any]] = []
        self._max_run_reports: int = 20
        self._last_run_report: Optional[Dict[str, Any]] = None

        # Emotional intelligence: the agent carries a personality and a live
        # emotional state (borrowing the shared EmotionEngine) that colors its
        # reasoning and decisions, bridging AI agency with game-character life.
        self._emotion_engine = None
        self._emotion_entity_id = f"agent:{self.id}"

        self._load_role_toolsets()
        self._load_role_skills()

        # Context management (orthogonal compress vs. select)
        self._context_mgr = ContextManager(ContextBudget(max_tokens=8000))

        # Trajectory recording (audit spine for all actions)
        self._trajectory = get_trajectory_recorder()

        # Perception-decision pipeline (game world interaction)
        self._perception_pipeline: Optional[PerceptionDecisionPipeline] = None

        # Counterfactual decision reasoning: evaluates candidate actions
        # by sandbox simulation before committing, fusing AI planning with
        # the engine's predictive dynamics.
        self._counterfactual_reasoner = None

        # Policy committing: after reasoning, applies the strongest candidate
        # to the LIVE world and records the observable outcome, closing the
        # observe -> simulate -> commit -> verify -> learn loop.
        self._policy_committer = None

        # Prediction calibration: turns the policy committer's prediction-vs-
        # actual history into a reliability profile and a calibrated confidence,
        # so the agent can self-correct how much it trusts its own simulations.
        self._prediction_calibrator = None

    @property
    def memory(self) -> AgentMemory:
        return self._memory

    @property
    def tools(self) -> ToolRegistry:
        return self._tools

    @property
    def context_manager(self) -> ContextManager:
        return self._context_mgr

    @property
    def trajectory(self) -> TrajectoryRecorder:
        return self._trajectory

    @property
    def perception_pipeline(self) -> Optional[PerceptionDecisionPipeline]:
        return self._perception_pipeline

    def init_perception_pipeline(self, engine_bridge: Any = None) -> None:
        """Initialize the perception-menu-decision pipeline with an engine bridge."""
        builder = PerceptionBuilder(engine_bridge)
        menu_builder = ActionMenuBuilder()
        self._perception_pipeline = PerceptionDecisionPipeline(builder, menu_builder)

    def set_llm_provider(self, provider: LLMProvider) -> None:
        self._llm = provider

    def add_capability(self, capability: AgentCapability) -> None:
        if capability not in self.capabilities:
            self.capabilities.append(capability)

    def has_capability(self, capability: AgentCapability) -> bool:
        return capability in self.capabilities

    def register_tool(self, tool: Tool) -> None:
        self._tools.register(tool)

    def on(self, event: str, handler: Callable) -> None:
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event: str, handler: Callable) -> None:
        if event in self._event_handlers:
            self._event_handlers[event] = [
                h for h in self._event_handlers[event] if h != handler
            ]

    def emit(self, event: str, data: Any = None) -> None:
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    handler(data)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Event handler for '{event}' failed: {e}")

    # === Four-Phase Autonomous Loop ===

    async def observe(self, observation: str, importance: float = 0.5) -> None:
        """
        Phase 1: Observe the environment and record observations.
        Agents perceive the game world state and user inputs.
        """
        self.state = AgentState.OBSERVING
        self.emit("observe_start", {"observation": observation})

        self._memory.remember(
            content=observation,
            memory_type=MemoryType.SHORT_TERM,
            importance=importance,
        )

        self._memory.remember(
            content=f"[Observation] {observation}",
            memory_type=MemoryType.EPISODIC,
            importance=importance * 0.8,
        )

        self.state = AgentState.IDLE
        self.emit("observe_complete", {"observation": observation})

    async def think(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Phase 2: Reason about the current state and decide on action.
        Uses LLM with memory-augmented context and context selection
        for efficient per-turn retrieval.
        """
        self.state = AgentState.THINKING
        self.emit("thinking_start", {"prompt": prompt})

        try:
            memory_context = self._build_memory_context(prompt)
            full_prompt = self._assemble_prompt(prompt, memory_context, context)

            # Add to context manager
            self._context_mgr.add_message("user", prompt)

            # Select relevant context for this turn
            selected = self._context_mgr.select_context(prompt)

            self._memory.remember(
                content=f"User: {prompt}",
                memory_type=MemoryType.SHORT_TERM,
                importance=0.5,
            )
            self._memory.tick()

            if self._llm:
                try:
                    response = await asyncio.wait_for(
                        self._llm.generate(full_prompt),
                        timeout=60.0,
                    )
                except asyncio.TimeoutError:
                    response = self._fallback_think(prompt)
                    self.emit("thinking_timeout", {"prompt": prompt[:100]})
            else:
                response = self._fallback_think(prompt)

            self._context_mgr.add_message("agent", response)

            self._memory.remember(
                content=f"Agent({self.name}): {response}",
                memory_type=MemoryType.SHORT_TERM,
                importance=0.6,
            )

            self._message_history.append(
                AgentMessage(role="agent", content=response)
            )

            self._consecutive_failures = 0
            self.state = AgentState.IDLE
            self.emit("thinking_complete", {"response": response})
            return response

        except Exception as e:
            self._consecutive_failures += 1
            self.state = AgentState.ERROR
            classifier = get_error_classifier()
            classified = classifier.classify(e, context_messages=len(self._message_history))
            self.emit("thinking_error", {"error": str(e), "category": classified.category.value, "hints": classified.hints.to_dict()})
            if classified.hints.should_compress:
                self._context_mgr.compress()
                self.emit("context_overflow_detected", {"tokens": self._context_mgr.token_usage})
            return f"Error during thinking: {str(e)}"

    async def act(self, action: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Phase 3: Execute an action using registered tools.
        Actions modify the game world state. All actions are recorded
        in the trajectory timeline with before/after state and validation.
        """
        self.state = AgentState.EXECUTING
        self.emit("action_start", {"action": action, "params": params})

        # Determine permission tier
        read_only_actions = {"query_entities", "list_scenes", "get_world_state", "get_console_logs"}
        tier = PermissionTier.TIER_0_READONLY if action in read_only_actions else PermissionTier.TIER_1_UNDOABLE

        # Begin trajectory recording
        traj_entry = self._trajectory.begin_action(
            agent_id=self.id,
            agent_name=self.name,
            action=action,
            params=params or {},
            permission_tier=tier,
        )

        try:
            tool = self._tools.get(action)
            if tool:
                try:
                    result = await asyncio.wait_for(
                        tool.execute(params or {}),
                        timeout=120.0,
                    )
                except asyncio.TimeoutError:
                    self._consecutive_failures += 1
                    self.state = AgentState.ERROR
                    self._trajectory.fail_action(traj_entry.id, "Timeout")
                    self.emit("action_timeout", {"action": action})
                    return f"Timeout executing action: {action}"

                # Complete trajectory entry with result
                affected = []
                if isinstance(result, dict):
                    eid = result.get("entity_id") or result.get("world_id") or result.get("scene_id")
                    if eid:
                        affected.append(eid)
                self._trajectory.complete_action(
                    traj_entry.id, result, affected_entities=affected
                )

                self._memory.remember(
                    content=f"Executed tool '{action}' with result: {str(result)[:200]}",
                    memory_type=MemoryType.EPISODIC,
                    importance=0.7,
                )
                pruner = get_tool_output_pruner()
                pruned_result, prune_info = pruner.prune(action, result)
                if prune_info.was_pruned:
                    self.emit("tool_output_pruned", {"tool": action, "original_size": prune_info.original_size, "pruned_size": prune_info.pruned_size})
                    result = pruned_result
                file_state = get_file_state_engine()
                if action in ("read_file", "list_directory", "search_code", "web_fetch"):
                    path = (params or {}).get("path", (params or {}).get("file_path", (params or {}).get("directory", "")))
                    if path:
                        file_state.register_read(self.id, str(path))
                elif action in ("write_file", "create_file", "delete_file", "update_file"):
                    path = (params or {}).get("path", (params or {}).get("file_path", ""))
                    if path:
                        content = (params or {}).get("content", "")
                        file_state.register_write(self.id, str(path), str(content))
                self._consecutive_failures = 0
                self.state = AgentState.IDLE
                self.emit("action_complete", {"action": action, "result": result})
                return result
            else:
                self._trajectory.fail_action(traj_entry.id, f"Tool '{action}' not found")
                self.state = AgentState.IDLE
                return f"Tool '{action}' not found"

        except Exception as e:
            self._consecutive_failures += 1
            self.state = AgentState.ERROR
            self._trajectory.fail_action(traj_entry.id, str(e))
            classifier = get_error_classifier()
            classified = classifier.classify(e)
            self.emit("action_error", {"action": action, "error": str(e), "category": classified.category.value})
            return f"Error executing action: {str(e)}"

    async def verify(self, criteria: str, evidence: Optional[str] = None) -> Dict[str, Any]:
        """
        Phase 4: Verify that the action achieved the intended result.
        Contract-based verification with confidence scoring.
        """
        self.state = AgentState.VERIFYING
        self.emit("verify_start", {"criteria": criteria})

        try:
            verification_prompt = (
                f"Verify the following criteria:\n"
                f"Criteria: {criteria}\n"
            )
            if evidence:
                verification_prompt += f"Evidence: {evidence}\n"
            verification_prompt += (
                f"\nRespond with JSON: {{\"verified\": true/false, "
                f"\"confidence\": 0.0-1.0, \"notes\": \"explanation\"}}"
            )

            if self._llm:
                response = await self._llm.generate(verification_prompt)
                result = self._parse_json_response(response, {
                    "verified": "verified" in response.lower() or "pass" in response.lower(),
                    "confidence": 0.5,
                    "notes": response[:200],
                })
            else:
                result = {
                    "verified": True,
                    "confidence": 0.5,
                    "notes": "LLM not configured, defaulting to verified",
                }

            confidence = result.get("confidence", 0.5)
            if confidence >= 0.8:
                result["confidence_level"] = "high"
            elif confidence >= 0.5:
                result["confidence_level"] = "medium"
            elif result.get("verified"):
                result["confidence_level"] = "low"
            else:
                result["confidence_level"] = "failed"

            self._memory.remember(
                content=f"Verification: criteria='{criteria[:50]}', verified={result.get('verified')}, confidence={confidence:.2f}",
                memory_type=MemoryType.EPISODIC,
                importance=0.8 if result.get("verified") else 0.9,
            )

            self.state = AgentState.IDLE
            self.emit("verify_complete", result)
            return result

        except Exception as e:
            self.state = AgentState.ERROR
            self.emit("verify_error", {"error": str(e)})
            return {"verified": False, "confidence": 0.0, "confidence_level": "failed", "notes": str(e)}

    async def reflect(
        self,
        goal: str,
        steps_completed: int,
        total_steps: int,
        results: List[Dict[str, Any]],
        errors: List[str],
    ) -> Dict[str, Any]:
        """
        Phase 5: Reflect on execution progress and decide whether to
        continue, adjust, or replan.

        This phase enables self-correction by evaluating whether the
        current plan is on track and triggering replanning when needed.
        """
        self.state = AgentState.REFLECTING
        self.emit("reflect_start", {"goal": goal, "progress": f"{steps_completed}/{total_steps}"})

        try:
            avg_confidence = 0.0
            confidence_values = [r.get("confidence", 0.5) for r in results if isinstance(r, dict)]
            if confidence_values:
                avg_confidence = sum(confidence_values) / len(confidence_values)

            reflection_prompt = (
                f"Reflect on the following execution progress:\n"
                f"Goal: {goal}\n"
                f"Steps completed: {steps_completed}/{total_steps}\n"
                f"Average confidence: {avg_confidence:.2f}\n"
                f"Errors encountered: {len(errors)}\n"
            )
            if errors:
                reflection_prompt += f"Error details: {'; '.join(errors[:5])}\n"
            reflection_prompt += (
                f"\nRespond with JSON: {{\"verdict\": \"on_track|needs_adjustment|needs_replan|critical_failure\", "
                f"\"confidence\": 0.0-1.0, \"observations\": [\"...\"], "
                f"\"adjustments\": [\"...\"], \"replan_reason\": \"...\"}}"
            )

            if self._llm:
                response = await self._llm.generate(reflection_prompt)
                result = self._parse_json_response(response, {
                    "verdict": "on_track" if avg_confidence >= 0.7 else "needs_adjustment",
                    "confidence": avg_confidence,
                    "observations": [f"Completed {steps_completed}/{total_steps} steps"],
                    "adjustments": [],
                    "replan_reason": None,
                })
            else:
                if avg_confidence >= 0.7:
                    verdict = "on_track"
                elif avg_confidence >= 0.4:
                    verdict = "needs_adjustment"
                else:
                    verdict = "needs_replan"
                result = {
                    "verdict": verdict,
                    "confidence": avg_confidence,
                    "observations": [f"Completed {steps_completed}/{total_steps} steps with avg confidence {avg_confidence:.2f}"],
                    "adjustments": [] if avg_confidence >= 0.7 else ["Review recent steps for quality"],
                    "replan_reason": f"Low confidence ({avg_confidence:.2f})" if verdict == "needs_replan" else None,
                }

            self._memory.remember(
                content=f"Reflection: verdict={result.get('verdict')}, confidence={result.get('confidence', 0):.2f}",
                memory_type=MemoryType.EPISODIC,
                importance=0.9,
            )

            self.state = AgentState.IDLE
            self.emit("reflect_complete", result)
            return result

        except Exception as e:
            self.state = AgentState.ERROR
            self.emit("reflect_error", {"error": str(e)})
            return {"verdict": "needs_adjustment", "confidence": 0.0, "observations": [str(e)], "adjustments": [], "replan_reason": None}

    # === Autonomous Loop ===

    async def run_autonomous(
        self,
        goal: str,
        max_iterations: Optional[int] = None,
        reflection_interval: int = 3,
        max_replans: int = 2,
        verify_each_step: bool = False,
        self_refine: bool = False,
    ) -> Any:
        """
        Run the full autonomous loop: Plan -> Execute -> Reflect -> Verify.

        The agent creates an execution plan, iterates through work steps,
        reflects at regular intervals, and verifies each step against criteria.
        Reflection can trigger replanning when confidence is low.

        With verify_each_step=True each step is checked against its own
        criteria and the recorded confidence reflects that check. With
        self_refine=True failed steps capture a durable refinement lesson
        (failure -> adjustment) that informs later reasoning.
        """
        plan = ExecutionPlan(goal=goal, max_iterations=max_iterations or self.max_iterations)
        self._current_plan = plan
        self._iteration_count = 0
        replan_count = 0
        step_refine_count = 0

        self.emit("autonomous_start", {"goal": goal})

        try:
            plan.phase = "planning"
            self.state = AgentState.PLANNING

            plan_response = await self.think(
                f"Create an execution plan for: {goal}\n"
                f"Include: status quo, target end state, checklist, "
                f"work steps, and verification gates."
            )
            plan.target_end_state = plan_response[:500]
            plan.end_state_checklist = self._extract_checklist(plan_response)
            plan.work_plan = self._extract_steps(plan_response)
            plan.verification_gates = self._extract_verification(plan_response)

            plan.phase = "execution"
            self.state = AgentState.EXECUTING

            results = []
            errors = []
            for i, step in enumerate(plan.work_plan):
                if self._iteration_count >= plan.max_iterations:
                    break
                if self._consecutive_failures >= self._max_consecutive_failures:
                    break

                self._iteration_count += 1
                step_description = step.get("description", str(step))

                await self.observe(
                    f"Step {self._iteration_count}: {step_description}",
                    importance=0.4,
                )

                step_result = await self.think(step_description)

                action_name = step.get("action")
                if action_name:
                    action_result = await self.act(action_name, step.get("params", {}))
                    step_result = action_result

                step_entry = {
                    "step": self._iteration_count,
                    "description": step_description,
                    "result": str(step_result)[:200] if step_result else None,
                }

                if isinstance(step_result, dict) and step_result.get("error"):
                    errors.append(str(step_result.get("error"))[:100])
                    step_entry["confidence"] = 0.2
                elif isinstance(step_result, dict) and step_result.get("confidence"):
                    step_entry["confidence"] = step_result["confidence"]
                else:
                    step_entry["confidence"] = 0.6

                # Emotional feedback: a successful step lifts confidence-
                # related affect; a failure adds frustration/stress. The mood
                # then mildly colors the recorded confidence.
                try:
                    if step_entry["confidence"] >= 0.5:
                        self.apply_emotional_stimulus({"joy": 0.12, "trust": 0.08}, "weak")
                    else:
                        self.apply_emotional_stimulus({"frustration": 0.12, "fear": 0.08}, "moderate")
                    step_entry["confidence"] = self._emotionally_adjust_confidence(step_entry["confidence"])
                    step_entry["mood"] = self.get_emotional_state().get("mood", "neutral")
                except Exception:
                    pass

                # Optional per-step contract verification.
                if verify_each_step:
                    criteria = step.get("verification_criteria") or (
                        f"Step '{step_description}' completed with a valid result."
                    )
                    check = await self.verify(criteria, evidence=str(step_result)[:300])
                    step_entry["verified"] = check.get("verified", False)
                    step_entry["verification_notes"] = str(check.get("notes", ""))[:120]
                    step_entry["confidence"] = min(step_entry["confidence"],
                                                   float(check.get("confidence", 0.5)))

                # Self-refinement: capture a durable lesson on failure.
                if self_refine and step_entry["confidence"] < 0.5:
                    step_refine_count += 1
                    self.record_refinement(
                        failure=f"Step {self._iteration_count}: {step_description}",
                        adjustment=(
                            f"Lower expected confidence for '{step_description}'; "
                            "validate inputs, narrow scope, or re-attempt with revised plan."
                        ),
                        outcome=f"confidence={step_entry['confidence']:.2f}",
                    )
                    step_entry["refined"] = True

                results.append(step_entry)

                if (i + 1) % reflection_interval == 0 and i + 1 < len(plan.work_plan):
                    reflection = await self.reflect(
                        goal=goal,
                        steps_completed=i + 1,
                        total_steps=len(plan.work_plan),
                        results=results,
                        errors=errors,
                    )
                    verdict = reflection.get("verdict", "on_track")
                    if verdict == "needs_replan" and replan_count < max_replans:
                        replan_count += 1
                        self._memory.remember(
                            content=f"Replanning (attempt {replan_count}): {reflection.get('replan_reason', 'low confidence')}",
                            memory_type=MemoryType.EPISODIC,
                            importance=0.9,
                        )
                        new_plan_response = await self.think(
                            f"The current plan for '{goal}' needs adjustment.\n"
                            f"Reflection: {reflection.get('observations', [])}\n"
                            f"Adjustments needed: {reflection.get('adjustments', [])}\n"
                            f"Create a revised execution plan."
                        )
                        new_steps = self._extract_steps(new_plan_response)
                        if new_steps:
                            plan.work_plan = plan.work_plan[:i + 1] + new_steps
                        errors = []
                    elif verdict == "critical_failure":
                        break

            plan.phase = "verifying"
            self.state = AgentState.VERIFYING

            for gate in plan.verification_gates:
                await self.verify(gate)

            plan.status = "completed"
            plan.result = results
            self._plan_history.append(plan)
            self.state = AgentState.COMPLETED

            # Progressive learning: convert successful trajectory patterns
            # into reusable skills that feed future reasoning.
            if self_refine:
                try:
                    self.learn_from_trajectory(goal=goal)
                except Exception as e:
                    logger.debug("Skill learning skipped: %s", e)

            # Mission debrief: produce and store the after-action report.
            try:
                report = self.finish_run_report(goal)
            except Exception as e:
                logger.debug("Debrief skipped: %s", e)
                report = None

            self.emit("autonomous_complete", {"goal": goal, "iterations": self._iteration_count, "replans": replan_count, "step_refinements": step_refine_count})
            if report is not None:
                return {"result": results, "report": report}
            return results

        except Exception as e:
            plan.status = "failed"
            self.state = AgentState.ERROR
            self.emit("autonomous_error", {"error": str(e)})
            return {"error": str(e)}

    # === Decision Making ===

    async def decide(self, options: List[str], context: Optional[str] = None) -> str:
        prompt = f"Choose the best option from the following:\n"
        for i, option in enumerate(options, 1):
            prompt += f"{i}. {option}\n"
        if context:
            prompt += f"\nContext: {context}\n"
        prompt += "\nRespond with only the number of your choice."

        response = await self.think(prompt)
        try:
            choice_idx = int(response.strip()) - 1
            if 0 <= choice_idx < len(options):
                return options[choice_idx]
        except (ValueError, IndexError):
            pass
        return options[0] if options else ""

    async def perceive_and_decide(self) -> Optional[Decision]:
        """
        Run the perception-menu-decision pipeline.

        Builds a filtered perception of the game world, constructs
        an enumerated action menu, queries the LLM for a choice,
        and resolves the response via fuzzy ID matching.
        """
        if not self._perception_pipeline:
            return None

        # Stage 1: Perceive the game world
        perception = await self._perception_pipeline.perceive(self.id, self.name)

        # Stage 2: Build action menu from tools and perception
        tool_names = [t.name for t in self._tools.list_tools()]
        menu = self._perception_pipeline.build_menu(perception, tool_names)

        if not menu:
            return None

        # Stage 3: Ask LLM to choose
        prompt = f"{perception.to_prompt()}\n\n{self._perception_pipeline._menu_builder.to_prompt(menu)}"
        response = await self.think(prompt)

        # Resolve the response to a concrete decision
        decision = self._perception_pipeline.resolve_decision(response, menu, perception)

        # Execute the chosen action if it maps to a tool
        if decision.action_id and self._tools.get(decision.action_id):
            params = dict(decision.params)
            if decision.target_id:
                params["entity_id"] = decision.target_id
            await self.act(decision.action_id, params)

        return decision

    async def reflect_on_memories(self, query: str) -> Optional[str]:
        """
        Generate a reflection from recent memories and store it
        in the reflection DAG with provenance pointers.
        """
        relevant = self._memory.recall(query=query, max_results=10)
        if not relevant:
            return None

        # Build reflection prompt from retrieved memories
        memory_texts = [m["content"][:200] for m in relevant]
        reflection_prompt = (
            f"Reflect on the following memories and generate an insight:\n"
            + "\n".join(f"- {t}" for t in memory_texts)
            + "\n\nProvide a concise insight or pattern you observe."
        )

        response = await self.think(reflection_prompt)

        # Store as reflection node with provenance pointers
        source_ids = [m["id"] for m in relevant]
        self._memory.add_reflection(
            content=response[:500],
            source_ids=source_ids,
            importance=0.8,
        )

        return response

    # === Task Management ===

    def assign_task(self, task: AgentTask) -> None:
        self._current_task = task
        task.status = "in_progress"
        task.assigned_to = self.id
        self.emit("task_assigned", {"task": task})

    async def complete_task(self, result: Any = None) -> None:
        if self._current_task:
            self._current_task.status = "completed"
            self._current_task.result = result
            self._current_task.completed_at = time.time()
            self._task_history.append(self._current_task)
            self.emit("task_completed", {"task": self._current_task})
            self._current_task = None

    # === Status ===

    def get_status(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "state": self.state.value,
            "capabilities": [c.value for c in self.capabilities],
            "current_task": self._current_task.id if self._current_task else None,
            "task_count": len(self._task_history),
            "plan_count": len(self._plan_history),
            "memory_size": self._memory.size(),
            "memory_emotional_state": self._memory.get_emotional_summary(),
            "iteration_count": self._iteration_count,
            "consecutive_failures": self._consecutive_failures,
            "skills": list(self._skills.keys()),
            "toolsets": self._loaded_toolsets,
            "tool_count": len(self._tools.list_tools()),
            "refinements": len(self._refinements),
            "accumulated_skills": len(self.get_accumulated_skills(limit=200)),
            "run_reports": len(self._run_reports),
            "emotional_state": self._safe_emotional_state(),
            "counterfactual_decisions": len(self.get_counterfactual_decisions(limit=200)),
            "policy_commits": len(self.get_policy_commits(limit=200)),
            "calibration": self._get_prediction_calibrator().get_statistics(),
            "context_stats": self._context_mgr.get_statistics(),
            "trajectory_stats": self._trajectory.get_statistics(),
            "perception_enabled": self._perception_pipeline is not None,
        }

    # === Internal Methods ===

    def _build_memory_context(self, prompt: str) -> str:
        relevant = self._memory.recall(query=prompt, max_results=5)
        if not relevant:
            return ""
        context_parts = ["Relevant memories:"]
        for mem in relevant:
            context_parts.append(f"- {mem['content']}")
        return "\n".join(context_parts)

    def _assemble_prompt(
        self,
        prompt: str,
        memory_context: str,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        parts = [
            f"You are {self.name}, a {self.role.value} agent in the SparkLabs AI-Native Game Engine.",
            f"Your role: {self.role.value}",
        ]
        if self.capabilities:
            caps = ", ".join(c.value for c in self.capabilities)
            parts.append(f"Your capabilities: {caps}")
        if memory_context:
            parts.append(memory_context)

        refinement_ctx = self._refinement_context()
        if refinement_ctx:
            parts.append(refinement_ctx)

        skill_ctx = self._skill_context()
        if skill_ctx:
            parts.append(skill_ctx)

        emotion_ctx = self._emotion_context()
        if emotion_ctx:
            parts.append(emotion_ctx)

        counterfactual_ctx = self._counterfactual_context()
        if counterfactual_ctx:
            parts.append(counterfactual_ctx)

        game_ctx = self._get_game_context_summary()
        if game_ctx:
            parts.append(f"Game Context:\n{game_ctx}")

        if extra_context:
            if isinstance(extra_context, dict):
                ctx_parts = []
                if "overall_goal" in extra_context:
                    ctx_parts.append(f"Goal: {extra_context['overall_goal']}")
                if "prior_results" in extra_context and extra_context["prior_results"]:
                    ctx_parts.append("Prior results:")
                    for pr in extra_context["prior_results"][-3:]:
                        agent_name = pr.get("agent", "unknown")
                        result_str = str(pr.get("result", ""))[:150]
                        ctx_parts.append(f"  [{agent_name}]: {result_str}")
                if "skill_hints" in extra_context and extra_context["skill_hints"]:
                    ctx_parts.append(f"Relevant skills: {', '.join(extra_context['skill_hints'])}")
                if ctx_parts:
                    parts.append("Additional context:\n" + "\n".join(ctx_parts))
                else:
                    parts.append(f"Additional context: {extra_context}")
            else:
                parts.append(f"Additional context: {extra_context}")

        if self._current_task:
            parts.append(f"Current task: {self._current_task.title} - {self._current_task.description}")
        parts.append(f"\nPrompt: {prompt}")
        return "\n".join(parts)

    def _get_game_context_summary(self) -> str:
        """Build a concise summary of the current game context for prompt injection."""
        if not hasattr(self, '_game_context') or self._game_context is None:
            return ""

        ctx = self._game_context
        summary_parts = []

        if hasattr(ctx, 'get_project_info'):
            info = ctx.get_project_info()
            if info:
                summary_parts.append(f"Project: {info.get('name', 'Untitled')}")

        if hasattr(ctx, 'list_entities'):
            try:
                entities = ctx.list_entities()
                if entities:
                    summary_parts.append(f"Entities: {len(entities)} objects in scene")
            except Exception as e:
                logger.debug("Failed to list entities for context summary: %s", e)

        if hasattr(ctx, 'list_scenes'):
            try:
                scenes = ctx.list_scenes()
                if scenes:
                    active = ctx.get_active_scene() if hasattr(ctx, 'get_active_scene') else None
                    summary_parts.append(f"Scenes: {len(scenes)} (active: {active.name if active else 'none'})")
            except Exception as e:
                logger.debug("Failed to list scenes for context summary: %s", e)

        if hasattr(ctx, 'list_assets'):
            try:
                assets = ctx.list_assets()
                if assets:
                    summary_parts.append(f"Assets: {len(assets)} loaded")
            except Exception as e:
                logger.debug("Failed to list assets for context summary: %s", e)

        if hasattr(ctx, 'get_pipeline_state'):
            try:
                pipeline = ctx.get_pipeline_state()
                if pipeline and hasattr(pipeline, 'current_phase'):
                    summary_parts.append(f"Pipeline: {pipeline.current_phase}")
            except Exception as e:
                logger.debug("Failed to get pipeline state for context summary: %s", e)

        return "\n".join(summary_parts) if summary_parts else ""

    def set_game_context(self, context: Any) -> None:
        """Set the game context for automatic prompt injection."""
        self._game_context = context

    # === Experiential Refinement ===

    def record_refinement(self, failure: str, adjustment: str, outcome: str = "pending") -> None:
        """
        Persist a durable lesson from a failure.

        Each refinement captures the triggering failure, the corrective
        adjustment taken, and the eventual outcome. Lessons are bounded
        (oldest are evicted first) and injected into future prompts so
        the agent becomes measurably wiser over repeated attempts.
        """
        entry = {
            "failure": failure[:200],
            "adjustment": adjustment[:200],
            "outcome": outcome[:200],
            "timestamp": time.time(),
        }
        self._refinements.append(entry)
        if len(self._refinements) > self._max_refinements:
            self._refinements = self._refinements[-self._max_refinements:]
        self._memory.remember(
            content=f"Refinement: {failure[:80]} -> {adjustment[:80]} (outcome={outcome[:40]})",
            memory_type=MemoryType.SEMANTIC,
            importance=0.85,
        )
        self.emit("refinement_recorded", entry)

    def _refinement_context(self, limit: int = 6) -> str:
        """Render recent refinements for prompt injection."""
        if not self._refinements:
            return ""
        recent = self._refinements[-limit:]
        lines = []
        for r in recent:
            lines.append(f"- Failure: {r['failure']}")
            lines.append(f"  Adjustment: {r['adjustment']}")
        return "Learned lessons from prior attempts:\n" + "\n".join(lines)

    def get_refinements(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the refinement history (for status/diagnostics)."""
        return list(self._refinements[-limit:])

    def clear_refinements(self) -> int:
        """Clear the refinement history; returns the number removed."""
        count = len(self._refinements)
        self._refinements.clear()
        return count

    # === Progressive Learning (Skill Accumulation) ===

    def _get_skill_accumulator(self):
        """Lazily resolve the shared skill accumulator engine."""
        if self._skill_accumulator is None:
            from sparkai.agent.agent_skill_accumulator import get_skill_accumulator_engine
            self._skill_accumulator = get_skill_accumulator_engine()
        return self._skill_accumulator

    def learn_from_trajectory(
        self,
        limit: int = 40,
        goal: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Derive reusable skills from recent successful trajectory patterns.

        Scans the recorded action timeline, groups successful executions by
        action, and accumulates a persistent skill for each repeated pattern.
        This turns past competence into future capability, forming the agent's
        progressive learning loop.
        """
        engine = self._get_skill_accumulator()
        entries = self._trajectory.get_timeline(limit=limit)
        learned: List[Dict[str, Any]] = []

        # Group successful actions by name.
        patterns: Dict[str, List[Dict[str, Any]]] = {}
        for e in entries:
            if not isinstance(e, dict):
                continue
            action = e.get("action")
            status = e.get("status")
            if not action or status not in ("success", "validated"):
                continue
            patterns.setdefault(action, []).append(e)

        for action, items in patterns.items():
            if len(items) < 1:
                continue
            # Reuse an existing skill if one already matches this action.
            existing = engine.discover_skills(limit=100)
            existing_ids = {s.name for s in existing}
            skill_name = f"Execute {action.replace('_', ' ').title()}"
            if skill_name in existing_ids:
                continue

            sample = items[0]
            avg_duration = (
                sum(float(i.get("duration_s", 0.0)) for i in items) / len(items)
            )
            skill = engine.accumulate_skill(
                domain="ai_behavior",
                name=skill_name,
                description=(
                    f"Repeatedly successful pattern from trajectory: "
                    f"'{action}' (goal: {goal or 'autonomous'})."
                ),
                steps=[
                    {
                        "description": f"Execute the {action} action",
                        "action_type": action,
                        "parameters": sample.get("params", {}),
                        "expected_output": str(sample.get("result", ""))[:120],
                        "timeout_ms": max(avg_duration * 1000, 30000.0),
                    }
                ],
                tags=[action, "trajectory", "learned"],
                postconditions=["Action completed without error"],
            )
            learned.append({
                "skill_id": skill.skill_id,
                "name": skill.name,
                "action": action,
                "occurrences": len(items),
            })
            self._memory.remember(
                content=f"Accumulated skill '{skill.name}' from {len(items)} trajectory executions",
                memory_type=MemoryType.SEMANTIC,
                importance=0.8,
            )

        if learned:
            self.emit("skills_learned", {"count": len(learned), "skills": learned})
        return learned

    def get_accumulated_skills(
        self,
        domain: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Return the agent's accumulated skills for diagnostics."""
        engine = self._get_skill_accumulator()
        skills = engine.discover_skills(domain=domain, limit=limit)
        return [
            {
                "skill_id": s.skill_id,
                "name": s.name,
                "domain": s.domain.value,
                "description": s.description,
                "maturity": s.maturity.value,
                "version": s.version,
                "usage_count": s.usage_count,
                "success_count": s.success_count,
                "tags": s.tags,
                "steps": [
                    {"order": st.order, "description": st.description, "action_type": st.action_type}
                    for st in s.steps
                ],
            }
            for s in skills
        ]

    def execute_accumulated_skill(
        self,
        skill_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute an accumulated skill and record the outcome."""
        engine = self._get_skill_accumulator()
        execution = engine.execute_skill(skill_id, context or {})
        skill = engine.get_skill(skill_id)
        return {
            "execution_id": execution.execution_id,
            "skill_id": skill_id,
            "skill_name": skill.name if skill else skill_id,
            "outcome": execution.outcome.value,
            "duration_ms": execution.duration_ms,
            "output": execution.output,
            "error": execution.error_details,
        }

    def _skill_context(self, limit: int = 4) -> str:
        """Render the top accumulated skills for prompt injection."""
        try:
            skills = self.get_accumulated_skills(limit=limit)
        except Exception:
            return ""
        if not skills:
            return ""
        lines = ["Reusable skills from prior successes:"]
        for s in skills:
            lines.append(f"- {s['name']} (maturity={s['maturity']}, uses={s['usage_count']})")
        return "\n".join(lines)

    # === Mission Debrief (After-Action Report) ===

    def synthesize_run_report(self, goal: str) -> Dict[str, Any]:
        """
        Compose a structured after-action report for a completed mission.

        The debrief consolidates the goal, plan phase/status, per-step
        outcomes, verification gates, refinements captured, skills learned,
        and trajectory statistics into one reviewable record. This gives the
        editor a single source of truth for auditing an autonomous run.
        """
        plan = self._current_plan
        steps = list(plan.work_plan) if plan else []
        step_results = list(plan.result) if (plan and plan.result) else []

        verified_steps = sum(1 for s in step_results if s.get("verified"))
        refined_steps = sum(1 for s in step_results if s.get("refined"))
        failed_steps = sum(1 for s in step_results if s.get("confidence", 1.0) < 0.5)

        report = {
            "goal": goal,
            "plan_id": plan.id if plan else None,
            "plan_status": plan.status if plan else "none",
            "plan_phase": plan.phase if plan else "none",
            "target_end_state": (plan.target_end_state if plan else "")[:300],
            "step_count": len(steps),
            "iterations": self._iteration_count,
            "verified_steps": verified_steps,
            "refined_steps": refined_steps,
            "failed_steps": failed_steps,
            "steps": [
                {
                    "step": s.get("step"),
                    "description": s.get("description", ""),
                    "confidence": round(float(s.get("confidence", 0.0)), 2),
                    "verified": s.get("verified", False),
                    "refined": s.get("refined", False),
                }
                for s in step_results
            ],
            "verification_gates": list(plan.verification_gates) if plan else [],
            "refinements": list(self._refinements[-5:]),
            "skills_learned": [
                s["name"] for s in self.get_accumulated_skills(limit=10)
            ],
            "trajectory_stats": self._trajectory.get_statistics(),
        }
        return report

    def finish_run_report(self, goal: str) -> Dict[str, Any]:
        """Record the debrief for the just-completed run and store it."""
        report = self.synthesize_run_report(goal)
        self._last_run_report = report
        self._run_reports.append(report)
        if len(self._run_reports) > self._max_run_reports:
            self._run_reports = self._run_reports[-self._max_run_reports:]
        self.emit("run_report_ready", {"goal": goal, "step_count": report["step_count"]})
        return report

    def get_run_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return the stored mission debriefs (most recent first)."""
        return list(reversed(self._run_reports[-limit:]))

    # === Emotional Intelligence ===

    def _get_emotion_engine(self):
        """Lazily resolve the shared emotion/affect engine and seed the agent's
        personality profile on first use."""
        if self._emotion_engine is None:
            from sparkai.agent.agent_emotion_affect import (
                EmotionEngine, PersonalityTrait,
            )
            engine = EmotionEngine.get_instance()
            engine.set_personality(
                self._emotion_entity_id,
                traits={
                    PersonalityTrait.OPENNESS.value: 0.7,
                    PersonalityTrait.CONSCIENTIOUSNESS.value: 0.8,
                    PersonalityTrait.EXTRAVERSION.value: 0.6,
                    PersonalityTrait.AGREEABLENESS.value: 0.6,
                    PersonalityTrait.NEUROTICISM.value: 0.3,
                },
                baseline_mood=0.2,
            )
            self._emotion_engine = engine
        return self._emotion_engine

    def apply_emotional_stimulus(
        self,
        stimulus: Dict[str, float],
        intensity: str = "moderate",
    ) -> Dict[str, Any]:
        """Feed an emotional stimulus (e.g. step outcome) into the agent's
        emotional state. Returns the updated emotional summary."""
        from sparkai.agent.agent_emotion_affect import AffectIntensity
        engine = self._get_emotion_engine()
        engine.apply_stimulus(
            self._emotion_entity_id,
            stimulus,
            intensity=AffectIntensity(intensity),
        )
        return self.get_emotional_state()

    def set_emotion(self, emotion_type: str, value: float) -> Dict[str, Any]:
        """Directly set an emotion level on the agent."""
        from sparkai.agent.agent_emotion_affect import EmotionType
        engine = self._get_emotion_engine()
        engine.set_emotion(self._emotion_entity_id, EmotionType(emotion_type), value)
        return self.get_emotional_state()

    def get_emotional_state(self) -> Dict[str, Any]:
        """Return the agent's current mood and emotion levels in one view."""
        engine = self._get_emotion_engine()
        vector = engine.get_emotional_state(self._emotion_entity_id)
        mood = engine.get_current_mood(self._emotion_entity_id)
        if not vector:
            return {
                "entity_id": self._emotion_entity_id,
                "mood": mood.get("mood_state", "neutral"),
                "mood_value": mood.get("mood", 0.0),
                "emotions": {},
                "dominant_emotion": "",
            }
        return {
            "entity_id": self._emotion_entity_id,
            "mood": mood.get("mood_state", "neutral"),
            "mood_value": mood.get("mood", 0.0),
            "emotions": vector.get("emotion_values", {}),
            "dominant_emotion": vector.get("dominant_emotion", ""),
        }

    def _safe_emotional_state(self) -> Dict[str, Any]:
        """Return a compact emotional snapshot safe for status serialization."""
        try:
            state = self.get_emotional_state()
        except Exception:
            return {"mood": "neutral", "emotions": {}}
        return {
            "mood": state.get("mood", "neutral"),
            "emotions": state.get("emotions", {}),
        }

    def _emotion_context(self) -> str:
        """Render the agent's mood/personality for prompt injection."""
        try:
            state = self.get_emotional_state()
        except Exception:
            return ""
        mood = state.get("mood", "neutral")
        emotions = state.get("emotions", {})
        top = sorted(emotions.items(), key=lambda kv: kv[1], reverse=True)[:3]
        top_str = ", ".join(f"{k}={v:.2f}" for k, v in top) if top else "neutral"
        return f"Current mood: {mood} (dominant emotions: {top_str})"

    def _emotionally_adjust_confidence(self, base_confidence: float) -> float:
        """Blend a mood-derived factor into a step's confidence so emotional
        state mildly colors the agent's self-assessment."""
        try:
            state = self.get_emotional_state()
        except Exception:
            return base_confidence
        mood = state.get("mood", "neutral")
        boost = {
            "ecstatic": 0.08, "happy": 0.05, "calm": 0.03,
            "neutral": 0.0, "sad": -0.05, "anxious": -0.06,
            "angry": -0.04, "depressed": -0.08,
        }.get(mood, 0.0)
        return max(0.0, min(1.0, base_confidence + boost))

    # === Counterfactual Decision Reasoning ===

    def _get_counterfactual_reasoner(self):
        """Lazily resolve the shared counterfactual decision reasoner."""
        if self._counterfactual_reasoner is None:
            from sparkai.agent.agent_counterfactual_reasoner import (
                get_counterfactual_reasoner,
            )
            self._counterfactual_reasoner = get_counterfactual_reasoner()
        return self._counterfactual_reasoner

    def reason_counterfactually(
        self,
        candidates: List[Dict[str, Any]],
        goal: str = "",
        frames: int = 60,
        delta_time: float = 1.0 / 60.0,
    ) -> Dict[str, Any]:
        """
        Evaluate a set of candidate actions by sandbox simulation.

        Each candidate is applied to a rolled-back copy of the live world,
        stepped forward for `frames` frames, measured, and restored. The
        agent then ranks the candidates and surfaces the recommended path
        so it can commit only to the strongest course of action. The live
        world is never permanently altered by this reasoning pass.
        """
        reasoner = self._get_counterfactual_reasoner()
        from sparkai.engine.engine import SparkEngine
        engine = SparkEngine.get_instance()
        decision = reasoner.reason(
            engine, candidates=candidates, goal=goal,
            frames=frames, delta_time=delta_time,
        )

        # Persist the reasoning as an episodic memory for later recall.
        self._memory.remember(
            content=(
                f"Counterfactual decision for '{goal or 'unspecified'}': "
                f"{decision.reasoning}"
            ),
            memory_type=MemoryType.EPISODIC,
            importance=0.7,
        )
        self.emit("counterfactual_decision", {
            "goal": goal,
            "recommended_id": decision.recommended_id,
            "recommended_score": decision.recommended_score,
        })
        return decision.to_dict()

    def get_counterfactual_decisions(
        self, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Return recent counterfactual decision logs for diagnostics."""
        reasoner = self._get_counterfactual_reasoner()
        return reasoner.list_decisions(limit=limit)

    def _counterfactual_context(self, limit: int = 3) -> str:
        """Render recent counterfactual insights for prompt injection."""
        try:
            reasoner = self._get_counterfactual_reasoner()
            decisions = reasoner.list_decisions(limit=limit)
        except Exception:
            return ""
        if not decisions:
            return ""
        lines = ["Prior counterfactual decisions:"]
        for d in decisions:
            lines.append(
                f"- '{d.get('goal', 'unspecified')}' -> "
                f"{d.get('recommended_id', 'none')} (score="
                f"{d.get('recommended_score', 0.0):.2f})"
            )
        return "\n".join(lines)

    # === Policy Commit (Close the Loop) ===

    def _get_policy_committer(self):
        """Lazily resolve the shared policy committer singleton."""
        if self._policy_committer is None:
            from sparkai.agent.agent_policy_committer import get_policy_committer
            self._policy_committer = get_policy_committer()
        return self._policy_committer

    def commit_policy_action(
        self,
        action_type: str,
        params: Optional[Dict[str, Any]] = None,
        goal: str = "",
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Apply a single action to the LIVE game world and record the outcome.

        This is the execution half of the AI-native loop: the agent commits
        a concrete scene-editing operation (create/destroy/set-property/
        add-component) and captures the observable world delta. The result
        is fed back into memory and affect so the agent can calibrate.
        """
        from sparkai.engine.engine import SparkEngine
        engine = SparkEngine.get_instance()

        committer = self._get_policy_committer()
        record = committer.commit(
            engine, action_type, params, goal=goal, description=description,
            source="policy",
        )

        self._remember_commit(record)
        self._react_to_commit(record)
        self._record_calibration(record)
        return record.to_dict()

    def reason_and_commit(
        self,
        candidates: List[Dict[str, Any]],
        goal: str = "",
        frames: int = 60,
    ) -> Dict[str, Any]:
        """
        Reason counterfactually, then commit the recommended candidate to
        the live world.

        Combines the sandbox evaluation with live execution so the agent
        both predicts the strongest course of action and carries it out,
        recording the prediction-vs-actual fidelity for self-correction.
        """
        decision = self.reason_counterfactually(
            candidates=candidates, goal=goal, frames=frames,
        )

        from sparkai.engine.engine import SparkEngine
        engine = SparkEngine.get_instance()
        committer = self._get_policy_committer()

        record = committer.commit_recommended(engine, decision["id"], goal=goal)
        if record is None:
            return {
                "decision": decision,
                "commit": None,
                "message": "No recommended candidate to commit.",
            }

        self._remember_commit(record)
        self._react_to_commit(record)
        self._record_calibration(record)
        return {"decision": decision, "commit": record.to_dict()}

    def commit_latest_decision(self, goal: str = "") -> Optional[Dict[str, Any]]:
        """Commit the recommended candidate of the most recent decision."""
        from sparkai.engine.engine import SparkEngine
        engine = SparkEngine.get_instance()
        committer = self._get_policy_committer()
        record = committer.commit_latest_decision(engine, goal=goal)
        if record is None:
            return None
        self._remember_commit(record)
        self._react_to_commit(record)
        self._record_calibration(record)
        return record.to_dict()

    def get_policy_commits(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the recent policy commit history for diagnostics."""
        return self._get_policy_committer().get_commits(limit=limit)

    # === Prediction Calibration (Self-Model of Prediction Fidelity) ===

    def _get_prediction_calibrator(self):
        """Lazily resolve the shared prediction calibrator singleton."""
        if self._prediction_calibrator is None:
            from sparkai.agent.agent_prediction_calibrator import (
                get_prediction_calibrator,
            )
            self._prediction_calibrator = get_prediction_calibrator()
        return self._prediction_calibrator

    def _record_calibration(self, record) -> None:
        """
        Feed a committed action into the prediction calibrator.

        Only commits that carried a sandbox prediction produce a sample;
        the rest are safely ignored. This is where the agent learns how
        faithfully its simulations forecast reality.
        """
        try:
            self._get_prediction_calibrator().record_commit(record.to_dict())
        except Exception as exc:
            logger.debug("Calibration record skipped: %s", exc)

    def get_calibration(self) -> Dict[str, Any]:
        """Return the agent's prediction-calibration reliability profile."""
        calibrator = self._get_prediction_calibrator()
        profile = calibrator.get_profile()
        return {
            "profile": profile.to_dict(),
            "statistics": calibrator.get_statistics(),
            "samples": calibrator.get_samples(limit=20),
        }

    def calibrate_confidence(self, raw_confidence: float) -> float:
        """
        Scale a raw confidence by the agent's measured prediction reliability.

        Lets downstream decision-making discount confidence that has
        historically over-predicted outcomes, and trust confidence that has
        been faithful.
        """
        return self._get_prediction_calibrator().calibrate(raw_confidence)

    def ingest_commits_for_calibration(self) -> int:
        """
        Re-sync the calibrator from the full policy-commit history.

        Useful after a restore or on first load so the reliability profile
        reflects all recorded commits, not just those observed live.
        """
        commits = self._get_policy_committer().get_commits(limit=500)
        return self._get_prediction_calibrator().record_many(commits)

    def _remember_commit(self, record) -> None:
        """Persist a committed action as episodic memory and a trajectory echo."""
        try:
            self._memory.remember(
                content=(
                    f"Committed '{record.description or record.action_type}' "
                    f"(goal={record.goal or 'unspecified'}): "
                    f"added={record.added_entities} removed={record.removed_entities} "
                    f"score_delta={record.score_delta:+.2f} actual={record.actual_score:.2f}"
                ),
                memory_type=MemoryType.EPISODIC,
                importance=0.75,
            )
        except Exception as exc:
            logger.debug("Commit memory record skipped: %s", exc)

    def _react_to_commit(self, record) -> None:
        """Apply affective feedback and emit an event for a committed action."""
        try:
            changed = (
                record.added_entities or record.removed_entities
                or abs(record.score_delta) > 0.001
            )
            if changed and record.actual_score >= 0.5:
                self.apply_emotional_stimulus(
                    {"joy": 0.12, "trust": 0.10, "pride": 0.08}, "weak"
                )
            elif changed:
                self.apply_emotional_stimulus(
                    {"surprise": 0.10, "curiosity": 0.08}, "weak"
                )
            else:
                self.apply_emotional_stimulus(
                    {"frustration": 0.06, "confusion": 0.05}, "weak"
                )
        except Exception as exc:
            logger.debug("Commit affect skipped: %s", exc)

        self.emit("policy_committed", {
            "goal": record.goal,
            "description": record.description,
            "action_type": record.action_type,
            "actual_score": record.actual_score,
            "prediction_delta": record.prediction_delta,
        })

    # === State Persistence ===

    def to_state(self) -> Dict[str, Any]:
        """Serialize agent identity, capabilities, and learned state.

        Enables session continuity: a restored agent resumes with the same
        identity, toolset loading, and experiential refinements it had built.
        """
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "capabilities": [c.value for c in self.capabilities],
            "max_iterations": self.max_iterations,
            "loaded_toolsets": list(self._loaded_toolsets),
            "skills": list(self._skills.keys()),
            "refinements": list(self._refinements),
            "message_history": [
                {"role": m.role, "content": m.content[:500], "metadata": m.metadata}
                for m in self._message_history[-40:]
            ],
        }

    def restore_state(self, state: Dict[str, Any]) -> bool:
        """Restore agent identity and learned state from a serialized snapshot."""
        if not isinstance(state, dict) or "id" not in state:
            return False
        self.id = state.get("id", self.id)
        self.name = state.get("name", self.name)
        try:
            role = AgentRole(state.get("role", self.role.value))
        except ValueError:
            role = self.role
        self.role = role
        self.max_iterations = int(state.get("max_iterations", self.max_iterations))
        for cap in state.get("capabilities", []):
            try:
                self.add_capability(AgentCapability(cap))
            except ValueError:
                pass
        for ts in state.get("loaded_toolsets", []):
            self.load_toolset_by_name(ts)
        self._refinements = [r for r in state.get("refinements", []) if isinstance(r, dict)]
        self._refinements = self._refinements[-self._max_refinements:]
        for msg in state.get("message_history", []):
            self._message_history.append(AgentMessage(
                role=msg.get("role", "agent"),
                content=msg.get("content", ""),
                metadata=msg.get("metadata", {}),
            ))
        self.emit("state_restored", {"id": self.id, "refinements": len(self._refinements)})
        return True

    def _fallback_think(self, prompt: str) -> str:
        return f"[{self.name}] Processed: {prompt[:100]}... (LLM not configured)"

    def _parse_json_response(self, response: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON from LLM response with robust fallback handling."""
        import json
        import re

        cleaned = response.strip()
        fence_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
        fence_match = re.search(fence_pattern, cleaned, re.DOTALL)
        if fence_match:
            cleaned = fence_match.group(1).strip()

        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            pass

        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start_idx = cleaned.find(start_char)
            if start_idx >= 0:
                depth = 0
                end_idx = start_idx
                for idx in range(start_idx, len(cleaned)):
                    if cleaned[idx] == start_char:
                        depth += 1
                    elif cleaned[idx] == end_char:
                        depth -= 1
                    if depth == 0:
                        end_idx = idx + 1
                        break
                if end_idx > start_idx:
                    try:
                        parsed = json.loads(cleaned[start_idx:end_idx])
                        if isinstance(parsed, dict):
                            return parsed
                        elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                            return parsed[0]
                    except (json.JSONDecodeError, ValueError):
                        pass

        return fallback

    def _extract_checklist(self, text: str) -> List[str]:
        items = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith(("- [", "* [", "1.", "2.", "3.", "- ", "* ")):
                clean = line.lstrip("-*0123456789. []x")
                if clean:
                    items.append(clean)
        return items[:10] if items else ["Goal achieved"]

    def _extract_steps(self, text: str) -> List[Dict[str, Any]]:
        steps = []
        for line in text.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-") or line.startswith("*")):
                clean = line.lstrip("0123456789.-*) ")
                if clean and len(clean) > 5:
                    steps.append({"description": clean})
        return steps[:20] if steps else [{"description": text[:200]}]

    def _extract_verification(self, text: str) -> List[str]:
        gates = []
        keywords = ["verify", "check", "ensure", "confirm", "validate"]
        for line in text.split("\n"):
            line_lower = line.lower().strip()
            if any(kw in line_lower for kw in keywords):
                clean = line.strip().lstrip("-*0123456789.) ")
                if clean:
                    gates.append(clean)
        return gates[:5] if gates else ["Task completed successfully"]

    # === Skill Management ===

    def load_skill(self, skill: Skill) -> None:
        self._skills[skill.name] = skill
        self.emit("skill_loaded", {"skill": skill.name})

    def unload_skill(self, name: str) -> bool:
        if name in self._skills:
            del self._skills[name]
            self.emit("skill_unloaded", {"skill": name})
            return True
        return False

    def get_skill(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def list_skills(self) -> List[str]:
        return list(self._skills.keys())

    def _load_role_skills(self) -> None:
        all_skills = SkillRegistry.list_skills()
        for skill in all_skills:
            if self._is_skill_relevant(skill):
                self._skills[skill.name] = skill

    def _is_skill_relevant(self, skill: Skill) -> bool:
        if skill.category == "game_creation":
            return self.role in (AgentRole.DIRECTOR, AgentRole.LEAD)
        if skill.category == "debugging":
            return True
        return self.role in (AgentRole.DIRECTOR, AgentRole.LEAD, AgentRole.SPECIALIST)

    # === Toolset Management ===

    def load_toolset_by_name(self, name: str) -> bool:
        toolset = ToolsetRegistry.get(name)
        if toolset:
            self._tools.load_toolset(toolset.tools())
            if name not in self._loaded_toolsets:
                self._loaded_toolsets.append(name)
            self.emit("toolset_loaded", {"toolset": name})
            return True
        return False

    def unload_toolset_by_name(self, name: str) -> bool:
        toolset = ToolsetRegistry.get(name)
        if toolset:
            self._tools.unload_toolset(toolset.tool_names())
            if name in self._loaded_toolsets:
                self._loaded_toolsets.remove(name)
            self.emit("toolset_unloaded", {"toolset": name})
            return True
        return False

    def list_toolsets(self) -> List[str]:
        return list(self._loaded_toolsets)

    def _load_role_toolsets(self) -> None:
        role_tools = get_tools_for_role(self.role.value)
        self._tools.load_toolset(role_tools)
        role_toolsets = ToolsetRegistry.list_toolsets()
        for ts in role_toolsets:
            ts_tools = ts.tools()
            if any(t.name in [rt.name for rt in role_tools] for t in ts_tools):
                if ts.name not in self._loaded_toolsets:
                    self._loaded_toolsets.append(ts.name)
