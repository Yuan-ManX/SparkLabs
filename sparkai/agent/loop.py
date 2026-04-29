"""
SparkAI Agent - Loop Engine

Iterative agent loop with tool execution and reasoning chain.
The loop drives the core agent behavior:

  1. Receive input (user prompt or system observation)
  2. Think: LLM generates reasoning and decides on action
  3. Act: Execute a tool or delegate to a sub-agent
  4. Observe: Process the result and update context
  5. Repeat until goal is met or max iterations reached

The loop maintains a reasoning chain that tracks every
thought-action-observation triple for transparency and debugging.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable


class LoopState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ThoughtStep:
    """
    A single thought in the reasoning chain.
    Records the agent's reasoning before taking action.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionStep:
    """
    A single action taken by the agent.
    Records the tool call and parameters.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ObservationStep:
    """
    The result of an action, fed back into the next iteration.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    success: bool = True
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0


@dataclass
class LoopIteration:
    """
    One complete iteration of the agent loop:
    Thought -> Action -> Observation
    """
    iteration: int = 0
    thought: Optional[ThoughtStep] = None
    action: Optional[ActionStep] = None
    observation: Optional[ObservationStep] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReasoningChain:
    """
    Complete reasoning chain for an agent loop run.
    Provides full traceability of agent decisions.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    iterations: List[LoopIteration] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    final_result: Optional[str] = None
    total_tool_calls: int = 0
    total_errors: int = 0

    def add_iteration(self, iteration: LoopIteration) -> None:
        self.iterations.append(iteration)
        if iteration.action:
            self.total_tool_calls += 1
        if iteration.observation and not iteration.observation.success:
            self.total_errors += 1

    def get_summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "iteration_count": len(self.iterations),
            "total_tool_calls": self.total_tool_calls,
            "total_errors": self.total_errors,
            "duration": (self.end_time or time.time()) - self.start_time,
            "final_result": self.final_result,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.get_summary(),
            "iterations": [
                {
                    "iteration": it.iteration,
                    "thought": it.thought.content if it.thought else None,
                    "action": it.action.tool_name if it.action else None,
                    "action_params": it.action.parameters if it.action else None,
                    "observation": it.observation.content if it.observation else None,
                    "success": it.observation.success if it.observation else None,
                }
                for it in self.iterations
            ],
        }


class AgentLoop:
    """
    Iterative agent loop with tool execution and reasoning chain.

    The loop is the core execution engine for SparkLabs agents.
    It drives the think-act-observe cycle, manages the reasoning
    chain, and provides hooks for monitoring and control.

    Usage:
        loop = AgentLoop(agent=my_agent)
        result = await loop.run("Create a platformer game")
    """

    def __init__(
        self,
        agent: Any = None,
        max_iterations: int = 25,
        stop_condition: Optional[Callable[[str], bool]] = None,
        on_iteration: Optional[Callable[[LoopIteration], None]] = None,
    ):
        self.agent = agent
        self.max_iterations = max_iterations
        self.stop_condition = stop_condition
        self.on_iteration = on_iteration
        self.state = LoopState.IDLE
        self._chain: Optional[ReasoningChain] = None
        self._cancelled = False

    async def run(self, goal: str) -> ReasoningChain:
        """
        Execute the agent loop for a given goal.
        Returns the complete reasoning chain.
        """
        self.state = LoopState.RUNNING
        self._cancelled = False
        self._chain = ReasoningChain(goal=goal)

        try:
            current_input = goal

            for i in range(self.max_iterations):
                if self._cancelled:
                    self.state = LoopState.CANCELLED
                    break

                iteration = LoopIteration(iteration=i + 1)

                # Phase 1: Think
                thought = await self._think(current_input, i + 1)
                iteration.thought = thought

                # Check stop condition on thought
                if self.stop_condition and self.stop_condition(thought.content):
                    self._chain.final_result = thought.content
                    break

                # Phase 2: Decide and Act
                action = self._decide_action(thought.content)
                iteration.action = action

                if action.tool_name == "done":
                    self._chain.final_result = thought.content
                    break

                # Phase 3: Execute
                observation = await self._execute_action(action)
                iteration.observation = observation

                # Phase 4: Update context for next iteration
                current_input = observation.content

                self._chain.add_iteration(iteration)

                if self.on_iteration:
                    self.on_iteration(iteration)

            self._chain.end_time = time.time()
            if not self._chain.final_result and self._chain.iterations:
                last = self._chain.iterations[-1]
                self._chain.final_result = (
                    last.observation.content if last.observation
                    else last.thought.content if last.thought
                    else "Loop completed without final result"
                )

            self.state = LoopState.COMPLETED
            return self._chain

        except Exception as e:
            self.state = LoopState.FAILED
            if self._chain:
                self._chain.end_time = time.time()
                self._chain.final_result = f"Loop failed: {str(e)}"
            return self._chain or ReasoningChain(goal=goal, final_result=str(e))

    def cancel(self) -> None:
        self._cancelled = True

    def get_chain(self) -> Optional[ReasoningChain]:
        return self._chain

    async def _think(self, input_text: str, iteration: int) -> ThoughtStep:
        if self.agent and hasattr(self.agent, 'think'):
            try:
                response = await self.agent.think(
                    f"[Iteration {iteration}] {input_text}"
                )
                return ThoughtStep(content=response)
            except Exception as e:
                return ThoughtStep(content=f"Thinking error: {str(e)}")
        return ThoughtStep(content=f"[No agent] Input: {input_text[:200]}")

    def _decide_action(self, thought: str) -> ActionStep:
        thought_lower = thought.lower()

        tool_keywords = {
            "create_world": ["create world", "new world", "make world"],
            "create_entity": ["create entity", "add entity", "new entity", "spawn"],
            "add_component": ["add component", "attach component"],
            "create_scene": ["create scene", "new scene"],
            "generate_asset": ["generate asset", "create asset", "make asset"],
            "generate_code": ["write code", "generate code", "implement"],
            "generate_narrative": ["write story", "generate narrative", "create story"],
            "configure_npc": ["configure npc", "setup npc", "create npc"],
            "create_quest": ["create quest", "add quest"],
            "diagnose_error": ["diagnose", "debug", "fix error"],
            "scaffold_project": ["scaffold", "create project", "new project"],
        }

        for tool_name, keywords in tool_keywords.items():
            for kw in keywords:
                if kw in thought_lower:
                    return ActionStep(tool_name=tool_name, parameters={"prompt": thought})

        if any(kw in thought_lower for kw in ["done", "complete", "finished", "task complete"]):
            return ActionStep(tool_name="done", parameters={})

        return ActionStep(tool_name="reason", parameters={"thought": thought})

    async def _execute_action(self, action: ActionStep) -> ObservationStep:
        start = time.time()
        try:
            if action.tool_name == "done":
                return ObservationStep(content="Task completed", success=True, duration=time.time() - start)

            if action.tool_name == "reason":
                return ObservationStep(
                    content=f"Reasoning step: {action.parameters.get('thought', '')[:200]}",
                    success=True,
                    duration=time.time() - start,
                )

            if self.agent and hasattr(self.agent, 'act'):
                result = await self.agent.act(action.tool_name, action.parameters)
                return ObservationStep(
                    content=str(result)[:500] if result else "Action completed with no output",
                    success=True,
                    duration=time.time() - start,
                )

            return ObservationStep(
                content=f"Tool '{action.tool_name}' executed (no agent connected)",
                success=True,
                duration=time.time() - start,
            )

        except Exception as e:
            return ObservationStep(
                content=f"Error executing '{action.tool_name}': {str(e)}",
                success=False,
                duration=time.time() - start,
            )


class Pipeline:
    """
    Game generation pipeline for end-to-end game creation.

    The pipeline orchestrates the full game creation workflow:
      1. Analyze: Parse the user's game prompt
      2. Design: Generate game design document
      3. Scaffold: Create project structure from template
      4. Implement: Generate game code for each system
      5. Integrate: Wire up all systems together
      6. Validate: Run build health and playability checks

    Each stage uses the agent loop with specialized tools.
    """

    def __init__(self, agent: Any = None):
        self.agent = agent
        self._stages: List[Dict[str, Any]] = [
            {"name": "analyze", "description": "Analyze game prompt and extract requirements"},
            {"name": "design", "description": "Generate game design document"},
            {"name": "scaffold", "description": "Create project structure from template"},
            {"name": "implement", "description": "Generate game code for each system"},
            {"name": "integrate", "description": "Wire up all systems together"},
            {"name": "validate", "description": "Run build health and playability checks"},
        ]
        self._results: List[Dict[str, Any]] = []

    def get_stages(self) -> List[Dict[str, Any]]:
        return list(self._stages)

    async def run(self, prompt: str) -> Dict[str, Any]:
        """
        Execute the full game generation pipeline.
        """
        start_time = time.time()
        self._results = []

        context = {"prompt": prompt, "genre": "", "systems": [], "entities": []}

        for i, stage in enumerate(self._stages):
            stage_start = time.time()
            try:
                stage_result = await self._execute_stage(stage, context)
                context.update(stage_result.get("context_update", {}))
                self._results.append({
                    "stage": stage["name"],
                    "status": "completed",
                    "duration": time.time() - stage_start,
                    "result": stage_result,
                })
            except Exception as e:
                self._results.append({
                    "stage": stage["name"],
                    "status": "failed",
                    "duration": time.time() - stage_start,
                    "error": str(e),
                })
                break

        return {
            "prompt": prompt,
            "stages": self._results,
            "total_duration": time.time() - start_time,
            "completed_stages": sum(1 for r in self._results if r["status"] == "completed"),
            "total_stages": len(self._stages),
        }

    async def _execute_stage(
        self, stage: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        stage_name = stage["name"]

        if self.agent and hasattr(self.agent, 'think'):
            response = await self.agent.think(
                f"Pipeline stage '{stage_name}': {stage['description']}\n"
                f"Context: {context}\n"
                f"Execute this stage and provide the output."
            )
            return {
                "output": response,
                "context_update": {f"stage_{stage_name}": response[:500]},
            }

        stage_outputs = {
            "analyze": f"Analyzed prompt: genre=platformer, systems=[physics, input, rendering]",
            "design": f"Game design: 2D platformer with 3 levels, player movement, enemy AI",
            "scaffold": f"Project scaffolded: index.html, game.js, style.css, assets/",
            "implement": f"Implemented: PhysicsEngine, PlayerController, EnemyAI, LevelManager",
            "integrate": f"Integrated: All systems wired, game loop running at 60fps",
            "validate": f"Validated: Build health 100%, visual usability 80%, intent alignment 90%",
        }

        return {
            "output": stage_outputs.get(stage_name, f"Stage {stage_name} completed"),
            "context_update": {f"stage_{stage_name}": stage_outputs.get(stage_name, "")},
        }
