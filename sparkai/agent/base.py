"""
SparkAI Agent - Core Agent Foundation

The SparkAgent implements a four-phase autonomous loop:
  Observe -> Think -> Act -> Verify

This design enables AI-native game development where agents
can autonomously create, modify, and reason about game worlds.

Agent Roles:
  - Director: Strategic planning, delegates to Leads
  - Lead: Domain coordination, delegates to Specialists
  - Specialist: Focused execution on a single domain
  - Worker: Task-level execution with restricted permissions
"""

from __future__ import annotations

import asyncio
import uuid
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

from sparkai.agent.memory import AgentMemory, MemoryType
from sparkai.agent.toolkit import ToolRegistry, Tool, Toolset, ToolsetRegistry, get_tools_for_role
from sparkai.agent.llm import LLMProvider, LLMConfig
from sparkai.agent.skills.base import Skill, SkillRegistry
from sparkai.agent.agent_error_classifier import ErrorClassifier, get_error_classifier
from sparkai.agent.agent_tool_pruner import ToolOutputPruner, get_tool_output_pruner
from sparkai.agent.agent_file_state import FileStateEngine, get_file_state_engine


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

        self._load_role_toolsets()
        self._load_role_skills()

    @property
    def memory(self) -> AgentMemory:
        return self._memory

    @property
    def tools(self) -> ToolRegistry:
        return self._tools

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
        Uses LLM with memory-augmented context for decision-making.
        """
        self.state = AgentState.THINKING
        self.emit("thinking_start", {"prompt": prompt})

        try:
            memory_context = self._build_memory_context(prompt)
            full_prompt = self._assemble_prompt(prompt, memory_context, context)

            self._memory.remember(
                content=f"User: {prompt}",
                memory_type=MemoryType.SHORT_TERM,
                importance=0.5,
            )

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
                self.emit("context_overflow_detected", {"tokens": len(self._message_history)})
            return f"Error during thinking: {str(e)}"

    async def act(self, action: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Phase 3: Execute an action using registered tools.
        Actions modify the game world state.
        """
        self.state = AgentState.EXECUTING
        self.emit("action_start", {"action": action, "params": params})

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
                    self.emit("action_timeout", {"action": action})
                    return f"Timeout executing action: {action}"
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
                        file_state.register_read(self.agent_id, str(path))
                elif action in ("write_file", "create_file", "delete_file", "update_file"):
                    path = (params or {}).get("path", (params or {}).get("file_path", ""))
                    if path:
                        content = (params or {}).get("content", "")
                        file_state.register_write(self.agent_id, str(path), str(content))
                self._consecutive_failures = 0
                self.state = AgentState.IDLE
                self.emit("action_complete", {"action": action, "result": result})
                return result
            else:
                self.state = AgentState.IDLE
                return f"Tool '{action}' not found"

        except Exception as e:
            self._consecutive_failures += 1
            self.state = AgentState.ERROR
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
    ) -> Any:
        """
        Run the full autonomous loop: Plan -> Execute -> Reflect -> Verify.

        The agent creates an execution plan, iterates through work steps,
        reflects at regular intervals, and verifies each step against criteria.
        Reflection can trigger replanning when confidence is low.
        """
        plan = ExecutionPlan(goal=goal, max_iterations=max_iterations or self.max_iterations)
        self._current_plan = plan
        self._iteration_count = 0
        replan_count = 0

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

            self.emit("autonomous_complete", {"goal": goal, "iterations": self._iteration_count, "replans": replan_count})
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
            "iteration_count": self._iteration_count,
            "consecutive_failures": self._consecutive_failures,
            "skills": list(self._skills.keys()),
            "toolsets": self._loaded_toolsets,
            "tool_count": len(self._tools.list_tools()),
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
            except Exception:
                pass

        if hasattr(ctx, 'list_scenes'):
            try:
                scenes = ctx.list_scenes()
                if scenes:
                    active = ctx.get_active_scene() if hasattr(ctx, 'get_active_scene') else None
                    summary_parts.append(f"Scenes: {len(scenes)} (active: {active.name if active else 'none'})")
            except Exception:
                pass

        if hasattr(ctx, 'list_assets'):
            try:
                assets = ctx.list_assets()
                if assets:
                    summary_parts.append(f"Assets: {len(assets)} loaded")
            except Exception:
                pass

        if hasattr(ctx, 'get_pipeline_state'):
            try:
                pipeline = ctx.get_pipeline_state()
                if pipeline and hasattr(pipeline, 'current_phase'):
                    summary_parts.append(f"Pipeline: {pipeline.current_phase}")
            except Exception:
                pass

        return "\n".join(summary_parts) if summary_parts else ""

    def set_game_context(self, context: Any) -> None:
        """Set the game context for automatic prompt injection."""
        self._game_context = context

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
