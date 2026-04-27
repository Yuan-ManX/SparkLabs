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
from sparkai.agent.toolkit import ToolRegistry, Tool
from sparkai.agent.llm import LLMProvider, LLMConfig


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
                except Exception:
                    pass

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
                response = await self._llm.generate(full_prompt)
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
            self.emit("thinking_error", {"error": str(e)})
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
                result = await tool.execute(params or {})
                self._memory.remember(
                    content=f"Executed tool '{action}' with result: {str(result)[:200]}",
                    memory_type=MemoryType.EPISODIC,
                    importance=0.7,
                )
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
            self.emit("action_error", {"action": action, "error": str(e)})
            return f"Error executing action: {str(e)}"

    async def verify(self, criteria: str, evidence: Optional[str] = None) -> Dict[str, Any]:
        """
        Phase 4: Verify that the action achieved the intended result.
        Contract-based verification ensures deterministic outcomes.
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
                try:
                    import json
                    result = json.loads(response)
                except (json.JSONDecodeError, ValueError):
                    result = {
                        "verified": "verified" in response.lower() or "pass" in response.lower(),
                        "confidence": 0.5,
                        "notes": response[:200],
                    }
            else:
                result = {
                    "verified": True,
                    "confidence": 0.5,
                    "notes": "LLM not configured, defaulting to verified",
                }

            self._memory.remember(
                content=f"Verification: criteria='{criteria[:50]}', verified={result.get('verified')}",
                memory_type=MemoryType.EPISODIC,
                importance=0.8 if result.get("verified") else 0.9,
            )

            self.state = AgentState.IDLE
            self.emit("verify_complete", result)
            return result

        except Exception as e:
            self.state = AgentState.ERROR
            self.emit("verify_error", {"error": str(e)})
            return {"verified": False, "confidence": 0.0, "notes": str(e)}

    # === Autonomous Loop ===

    async def run_autonomous(
        self,
        goal: str,
        max_iterations: Optional[int] = None,
    ) -> Any:
        """
        Run the full autonomous loop: Plan -> Execute -> Verify.

        The agent creates an execution plan, iterates through
        work steps, and verifies each step against criteria.
        """
        plan = ExecutionPlan(goal=goal, max_iterations=max_iterations or self.max_iterations)
        self._current_plan = plan
        self._iteration_count = 0

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
            for step in plan.work_plan:
                if self._iteration_count >= plan.max_iterations:
                    break
                if self._consecutive_failures >= self._max_consecutive_failures:
                    break

                self._iteration_count += 1
                step_description = step.get("description", str(step))
                step_result = await self.think(step_description)

                action_name = step.get("action")
                if action_name:
                    action_result = await self.act(action_name, step.get("params", {}))
                    step_result = action_result

                results.append({
                    "step": self._iteration_count,
                    "description": step_description,
                    "result": str(step_result)[:200] if step_result else None,
                })

            plan.phase = "verifying"
            self.state = AgentState.VERIFYING

            for gate in plan.verification_gates:
                await self.verify(gate)

            plan.status = "completed"
            plan.result = results
            self._plan_history.append(plan)
            self.state = AgentState.COMPLETED

            self.emit("autonomous_complete", {"goal": goal, "iterations": self._iteration_count})
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
        if extra_context:
            parts.append(f"Additional context: {extra_context}")
        if self._current_task:
            parts.append(f"Current task: {self._current_task.title} - {self._current_task.description}")
        parts.append(f"\nPrompt: {prompt}")
        return "\n".join(parts)

    def _fallback_think(self, prompt: str) -> str:
        return f"[{self.name}] Processed: {prompt[:100]}... (LLM not configured)"

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
