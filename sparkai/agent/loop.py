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
        max_consecutive_errors: int = 3,
    ):
        self.agent = agent
        self.max_iterations = max_iterations
        self.stop_condition = stop_condition
        self.on_iteration = on_iteration
        self.max_consecutive_errors = max_consecutive_errors
        self.state = LoopState.IDLE
        self._chain: Optional[ReasoningChain] = None
        self._cancelled = False
        self._paused = False

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
            consecutive_errors = 0

            for i in range(self.max_iterations):
                if self._cancelled:
                    self.state = LoopState.CANCELLED
                    break

                while self._paused:
                    self.state = LoopState.PAUSED
                    await asyncio.sleep(0.5)
                    if self._cancelled:
                        self.state = LoopState.CANCELLED
                        return self._chain or ReasoningChain(goal=goal)

                self.state = LoopState.RUNNING

                iteration = LoopIteration(iteration=i + 1)

                # Phase 1: Think
                thought = await self._think(current_input, i + 1)
                iteration.thought = thought

                # Error recovery: if thinking failed, try to recover
                if thought.metadata.get("error"):
                    consecutive_errors += 1
                    if consecutive_errors >= self.max_consecutive_errors:
                        self._chain.final_result = f"Loop terminated: {consecutive_errors} consecutive errors"
                        break
                    current_input = f"Previous thinking failed. Retry with simpler approach. Original goal: {goal}"
                    self._chain.add_iteration(iteration)
                    continue
                else:
                    consecutive_errors = 0

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
            self.save_chain()
            return self._chain

        except Exception as e:
            self.state = LoopState.FAILED
            if self._chain:
                self._chain.end_time = time.time()
                self._chain.final_result = f"Loop failed: {str(e)}"
            self.save_chain()
            return self._chain or ReasoningChain(goal=goal, final_result=str(e))

    def cancel(self) -> None:
        self._cancelled = True

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False
        self.state = LoopState.RUNNING

    def is_paused(self) -> bool:
        return self._paused

    def save_chain(self, filepath: str = "") -> bool:
        if not self._chain:
            return False
        try:
            import json
            from pathlib import Path
            path = Path(filepath or f".sparkai/chains/{self._chain.goal[:50].replace(' ', '_')}.json")
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(self._chain.to_dict(), f, indent=2, default=str)
            return True
        except Exception:
            return False

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
                return ThoughtStep(
                    content=f"Thinking error: {str(e)}",
                    metadata={"error": True, "retry_eligible": True},
                )
        return ThoughtStep(content=f"[No agent] Input: {input_text[:500]}")

    def _decide_action(self, thought: str) -> ActionStep:
        thought_lower = thought.lower()

        tool_keywords = {
            "create_world": ["create world", "new world", "make world", "build world", "generate world"],
            "create_entity": ["create entity", "add entity", "new entity", "spawn", "create object"],
            "add_component": ["add component", "attach component", "component"],
            "create_scene": ["create scene", "new scene", "build scene"],
            "generate_asset": ["generate asset", "create asset", "make asset", "asset"],
            "generate_code": ["write code", "generate code", "implement", "code gen", "program"],
            "generate_narrative": ["write story", "generate narrative", "create story", "narrative", "dialogue"],
            "configure_npc": ["configure npc", "setup npc", "create npc", "npc behavior"],
            "create_quest": ["create quest", "add quest", "quest design"],
            "diagnose_error": ["diagnose", "debug", "fix error", "troubleshoot", "resolve error"],
            "scaffold_project": ["scaffold", "create project", "new project", "initialize project"],
            "evaluate_game": ["evaluate", "assess", "quality check", "review game"],
            "run_playtest": ["playtest", "test game", "run test", "play test"],
        }

        best_match = None
        best_score = 0
        for tool_name, keywords in tool_keywords.items():
            for kw in keywords:
                if kw in thought_lower:
                    score = len(kw)
                    if score > best_score:
                        best_score = score
                        best_match = tool_name

        if best_match:
            return ActionStep(tool_name=best_match, parameters={"prompt": thought})

        if any(kw in thought_lower for kw in ["done", "complete", "finished", "task complete", "goal achieved"]):
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
                    content=str(result)[:2000] if result else "Action completed with no output",
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
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    stage_result = await self._execute_stage(stage, context)
                    context.update(stage_result.get("context_update", {}))
                    self._results.append({
                        "stage": stage["name"],
                        "status": "completed",
                        "duration": time.time() - stage_start,
                        "result": stage_result,
                        "attempt": attempt + 1,
                    })
                    break
                except Exception as e:
                    if attempt < max_retries:
                        await asyncio.sleep(1.0 * (2 ** attempt))
                        continue
                    self._results.append({
                        "stage": stage["name"],
                        "status": "failed",
                        "duration": time.time() - stage_start,
                        "error": str(e),
                        "attempts": attempt + 1,
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

        prompt = context.get("prompt", "")
        genre = context.get("genre", "unspecified")
        systems = context.get("systems", [])

        stage_outputs = {
            "analyze": f"Analyzed prompt: genre={genre}, systems={systems or ['core']}, prompt_summary='{prompt[:100]}'",
            "design": f"Game design generated from prompt: '{prompt[:80]}' (no agent connected for detailed design)",
            "scaffold": f"Project structure prepared for {genre} game (awaiting agent for code generation)",
            "implement": f"Implementation pending - no agent connected to generate code for {genre} game",
            "integrate": f"Integration pending - no agent connected to wire systems for {genre} game",
            "validate": f"Validation pending - no agent connected to verify {genre} game build",
        }

        return {
            "output": stage_outputs.get(stage_name, f"Stage {stage_name} pending (no agent)"),
            "context_update": {f"stage_{stage_name}": stage_outputs.get(stage_name, ""), "agent_connected": False},
        }
