"""
SparkLabs Unified Task Execution Engine

Single execution backend for all coordination systems (Studio, Swarm, Orchestrator).
Connects task assignment to actual agent execution with context passing,
result capture, and skill integration.
"""

from __future__ import annotations

import uuid
import time
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set


class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ExecutionStrategy(Enum):
    DIRECT = "direct"
    AUTONOMOUS = "autonomous"
    PIPELINE = "pipeline"
    REFLECTIVE = "reflective"


@dataclass
class TaskContext:
    overall_goal: str = ""
    prior_results: List[Dict[str, Any]] = field(default_factory=list)
    game_context: Optional[Dict[str, Any]] = None
    skill_hints: List[str] = field(default_factory=list)
    parent_task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskExecution:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_name: str = ""
    task_description: str = ""
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    strategy: ExecutionStrategy = ExecutionStrategy.DIRECT
    context: TaskContext = field(default_factory=TaskContext)
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    confidence: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 1
    timeout_seconds: float = 300.0


@dataclass
class ExecutionBatch:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    executions: List[TaskExecution] = field(default_factory=list)
    max_concurrent: int = 3
    fail_fast: bool = False


class TaskExecutionEngine:
    """
    Unified task execution engine for SparkLabs.

    Provides a single execution backend that connects task assignment
    from Studio, Swarm, and Orchestrator to actual agent execution.
    Supports multiple execution strategies, context passing, and retry logic.
    """

    def __init__(self):
        self._executions: Dict[str, TaskExecution] = {}
        self._batches: Dict[str, ExecutionBatch] = {}
        self._agent_registry: Dict[str, Any] = {}
        self._pre_execution_hooks: List[Callable] = []
        self._post_execution_hooks: List[Callable] = []
        self._max_history = 500
        self._execution_history: List[Dict[str, Any]] = []

    def register_agent(self, agent_id: str, agent: Any) -> None:
        self._agent_registry[agent_id] = agent

    def unregister_agent(self, agent_id: str) -> None:
        self._agent_registry.pop(agent_id, None)

    def add_pre_execution_hook(self, hook: Callable) -> None:
        self._pre_execution_hooks.append(hook)

    def add_post_execution_hook(self, hook: Callable) -> None:
        self._post_execution_hooks.append(hook)

    def submit_execution(
        self,
        task_name: str,
        task_description: str,
        agent_id: Optional[str] = None,
        strategy: ExecutionStrategy = ExecutionStrategy.DIRECT,
        context: Optional[TaskContext] = None,
        max_retries: int = 1,
        timeout_seconds: float = 300.0,
    ) -> TaskExecution:
        execution = TaskExecution(
            task_name=task_name,
            task_description=task_description,
            agent_id=agent_id,
            strategy=strategy,
            context=context or TaskContext(),
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )

        if not execution.agent_id:
            execution.agent_id = self._find_best_agent(task_description)

        self._executions[execution.id] = execution
        return execution

    async def execute(self, execution_id: str) -> TaskExecution:
        execution = self._executions.get(execution_id)
        if not execution:
            return TaskExecution(status=ExecutionStatus.FAILED, error="Execution not found")

        for hook in self._pre_execution_hooks:
            try:
                hook(execution)
            except Exception:
                pass

        execution.status = ExecutionStatus.RUNNING
        execution.started_at = time.time()

        agent = self._agent_registry.get(execution.agent_id) if execution.agent_id else None

        if not agent:
            execution.status = ExecutionStatus.FAILED
            execution.error = f"No agent found for id: {execution.agent_id}"
            execution.completed_at = time.time()
            self._record_history(execution)
            return execution

        prompt = self._build_prompt(execution)

        for attempt in range(execution.max_retries + 1):
            try:
                if execution.strategy == ExecutionStrategy.AUTONOMOUS:
                    result = await asyncio.wait_for(
                        self._execute_autonomous(agent, prompt, execution),
                        timeout=execution.timeout_seconds,
                    )
                elif execution.strategy == ExecutionStrategy.REFLECTIVE:
                    result = await asyncio.wait_for(
                        self._execute_reflective(agent, prompt, execution),
                        timeout=execution.timeout_seconds,
                    )
                elif execution.strategy == ExecutionStrategy.PIPELINE:
                    result = await asyncio.wait_for(
                        self._execute_pipeline(agent, prompt, execution),
                        timeout=execution.timeout_seconds,
                    )
                else:
                    result = await asyncio.wait_for(
                        self._execute_direct(agent, prompt, execution),
                        timeout=execution.timeout_seconds,
                    )

                execution.result = result
                execution.status = ExecutionStatus.COMPLETED
                execution.confidence = self._extract_confidence(result)
                break

            except asyncio.TimeoutError:
                execution.retry_count = attempt
                if attempt >= execution.max_retries:
                    execution.status = ExecutionStatus.TIMEOUT
                    execution.error = f"Execution timed out after {execution.timeout_seconds}s"
                else:
                    continue

            except Exception as e:
                execution.retry_count = attempt
                if attempt >= execution.max_retries:
                    execution.status = ExecutionStatus.FAILED
                    execution.error = str(e)
                else:
                    continue

        execution.completed_at = time.time()

        for hook in self._post_execution_hooks:
            try:
                hook(execution)
            except Exception:
                pass

        self._record_history(execution)
        return execution

    async def execute_batch(self, batch: ExecutionBatch) -> List[TaskExecution]:
        semaphore = asyncio.Semaphore(batch.max_concurrent)
        results = []

        async def _run(ex: TaskExecution) -> TaskExecution:
            async with semaphore:
                result = await self.execute(ex.id)
                if batch.fail_fast and result.status == ExecutionStatus.FAILED:
                    for remaining in batch.executions:
                        if remaining.status == ExecutionStatus.PENDING:
                            remaining.status = ExecutionStatus.CANCELLED
                return result

        for ex in batch.executions:
            self._executions[ex.id] = ex

        tasks = [_run(ex) for ex in batch.executions if ex.status == ExecutionStatus.PENDING]
        if tasks:
            results = await asyncio.gather(*tasks)
        return list(results)

    async def _execute_direct(self, agent: Any, prompt: str, execution: TaskExecution) -> Any:
        if hasattr(agent, 'think'):
            return await agent.think(prompt)
        return {"output": "Agent has no think method", "agent": str(type(agent))}

    async def _execute_autonomous(self, agent: Any, prompt: str, execution: TaskExecution) -> Any:
        if hasattr(agent, 'run_autonomous'):
            return await agent.run_autonomous(
                goal=prompt,
                reflection_interval=execution.context.metadata.get("reflection_interval", 3),
                max_replans=execution.context.metadata.get("max_replans", 2),
            )
        return await self._execute_direct(agent, prompt, execution)

    async def _execute_reflective(self, agent: Any, prompt: str, execution: TaskExecution) -> Any:
        if hasattr(agent, 'think') and hasattr(agent, 'reflect'):
            think_result = await agent.think(prompt)
            if hasattr(agent, 'act'):
                act_result = await agent.act("execute", {"prompt": prompt, "thought": think_result})
            else:
                act_result = think_result
            reflection = await agent.reflect(
                goal=prompt,
                steps_completed=1,
                total_steps=1,
                results=[{"result": str(act_result)[:200], "confidence": 0.7}],
                errors=[],
            )
            return {
                "thought": think_result,
                "action": act_result,
                "reflection": reflection,
                "verdict": reflection.get("verdict", "on_track") if isinstance(reflection, dict) else "unknown",
            }
        return await self._execute_direct(agent, prompt, execution)

    async def _execute_pipeline(self, agent: Any, prompt: str, execution: TaskExecution) -> Any:
        if hasattr(agent, 'think'):
            stages = ["analyze", "design", "implement", "validate"]
            results = {}
            for stage in stages:
                stage_prompt = f"Pipeline stage '{stage}': {prompt}\nPrevious results: {results}"
                stage_result = await agent.think(stage_prompt)
                results[stage] = str(stage_result)[:500]
            return {"pipeline_results": results, "stages_completed": len(stages)}
        return await self._execute_direct(agent, prompt, execution)

    def _build_prompt(self, execution: TaskExecution) -> str:
        parts = [execution.task_description]

        ctx = execution.context
        if ctx.overall_goal:
            parts.append(f"\nOverall Goal: {ctx.overall_goal}")

        if ctx.prior_results:
            parts.append("\nPrior Step Results:")
            for pr in ctx.prior_results[-5:]:
                agent_name = pr.get("agent", "unknown")
                result_str = str(pr.get("result", ""))[:200]
                parts.append(f"  - [{agent_name}]: {result_str}")

        if ctx.game_context:
            parts.append(f"\nGame Context: {str(ctx.game_context)[:300]}")

        if ctx.skill_hints:
            parts.append(f"\nRelevant Skills: {', '.join(ctx.skill_hints)}")

        return "\n".join(parts)

    def _extract_confidence(self, result: Any) -> float:
        if isinstance(result, dict):
            return float(result.get("confidence", 0.7))
        return 0.7

    def _find_best_agent(self, task_description: str) -> Optional[str]:
        best_id = None
        best_score = -1
        desc_lower = task_description.lower()

        for agent_id, agent in self._agent_registry.items():
            score = 0
            if hasattr(agent, 'state'):
                try:
                    from sparkai.agent.base import AgentState
                    if agent.state == AgentState.IDLE:
                        score += 10
                except Exception:
                    pass

            if hasattr(agent, 'role'):
                role = str(getattr(agent, 'role', '')).lower()
                if 'director' in role:
                    score += 5
                elif 'lead' in role:
                    score += 3
                elif 'specialist' in role:
                    score += 2

            if hasattr(agent, 'capabilities'):
                caps = getattr(agent, 'capabilities', set())
                if hasattr(caps, '__iter__'):
                    for cap in caps:
                        cap_str = str(cap).lower()
                        if cap_str in desc_lower:
                            score += 2

            if score > best_score:
                best_score = score
                best_id = agent_id

        return best_id

    def _record_history(self, execution: TaskExecution) -> None:
        self._execution_history.append({
            "id": execution.id,
            "task_name": execution.task_name,
            "agent_id": execution.agent_id,
            "status": execution.status.value,
            "confidence": execution.confidence,
            "error": execution.error,
            "retry_count": execution.retry_count,
            "duration": (execution.completed_at or time.time()) - (execution.started_at or time.time()),
        })
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        ex = self._executions.get(execution_id)
        if not ex:
            return None
        return {
            "id": ex.id,
            "task_name": ex.task_name,
            "task_description": ex.task_description[:200],
            "agent_id": ex.agent_id,
            "strategy": ex.strategy.value,
            "status": ex.status.value,
            "result": str(ex.result)[:500] if ex.result else None,
            "error": ex.error,
            "confidence": ex.confidence,
            "retry_count": ex.retry_count,
            "started_at": ex.started_at,
            "completed_at": ex.completed_at,
        }

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._execution_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._execution_history)
        completed = sum(1 for h in self._execution_history if h["status"] == "completed")
        failed = sum(1 for h in self._execution_history if h["status"] == "failed")
        avg_confidence = 0.0
        if completed > 0:
            avg_confidence = sum(h["confidence"] for h in self._execution_history if h["status"] == "completed") / completed
        return {
            "total_executions": total,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / total if total > 0 else 0.0,
            "avg_confidence": round(avg_confidence, 3),
            "registered_agents": len(self._agent_registry),
            "active_executions": sum(1 for ex in self._executions.values() if ex.status == ExecutionStatus.RUNNING),
        }
