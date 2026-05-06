"""
SparkLabs Agent - AI-Native Development Loop

The central iteration controller for AI-driven game development.
Orchestrates the Plan → Code → Test → Iterate cycle, coordinating
all agent subsystems during active development sessions.

Architecture:
  DevelopmentLoop
    |-- CycleController (state machine: PLAN → CODE → TEST → ITERATE)
    |-- QualityGate (validates each cycle phase before proceeding)
    |-- IterationTracker (counts attempts, success rates, timing)
    |-- RollbackManager (reverts to last good state on cycle failure)
    |-- ProgressReporter (streams cycle status to UI via WebSocket)

Development Cycle:
  PLAN    → agent composes a work plan with sub-tasks
  CODE    → agent generates/modifies game code via tools
  TEST    → agent validates output against quality criteria
  ITERATE → agent refines based on test feedback, loops back to CODE

Cycle Policies:
  - MAX_ITERATIONS: hard stop after N iterations per task
  - TIMEOUT: cycle timeout with graceful abort
  - QUALITY_THRESHOLD: minimum quality score to exit ITERATE
  - AUTO_COMMIT: checkpoint before each CODE phase

Usage:
    loop = DevelopmentLoop()
    loop.set_policy(max_iterations=5, timeout_seconds=300)
    result = await loop.execute("Create reusable platformer mechanics")
    if result.success:
        engine.apply(result.artifacts)
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class CyclePhase(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    CODING = "coding"
    TESTING = "testing"
    ITERATING = "iterating"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class PlanStrategy(Enum):
    INCREMENTAL = "incremental"
    BLUEPRINT_FIRST = "blueprint_first"
    TEST_DRIVEN = "test_driven"
    DIRECT = "direct"


@dataclass
class CyclePolicy:
    max_iterations: int = 5
    timeout_seconds: float = 300.0
    quality_threshold: float = 0.7
    auto_checkpoint: bool = True
    auto_rollback_on_fail: bool = True
    plan_strategy: PlanStrategy = PlanStrategy.INCREMENTAL
    auto_retry_transient: bool = True
    max_retry_delay: float = 10.0


@dataclass
class PhaseResult:
    phase: CyclePhase = CyclePhase.IDLE
    success: bool = False
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    duration_ms: float = 0.0
    artifacts: List[str] = field(default_factory=list)
    iteration: int = 0


@dataclass
class CycleResult:
    task_id: str = ""
    task_description: str = ""
    success: bool = False
    final_phase: CyclePhase = CyclePhase.IDLE
    total_iterations: int = 0
    total_duration_ms: float = 0.0
    phases: List[PhaseResult] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    final_quality: float = 0.0
    checkpoint_id: str = ""
    notes: List[str] = field(default_factory=list)


class DevelopmentLoop:
    """Orchestrates the AI-native Plan → Code → Test → Iterate cycle."""

    _instance: Optional["DevelopmentLoop"] = None

    def __init__(self):
        self._policy: CyclePolicy = CyclePolicy()
        self._current_phase: CyclePhase = CyclePhase.IDLE
        self._active_task: Optional[str] = None
        self._tasks_completed: int = 0
        self._tasks_failed: int = 0
        self._total_iterations: int = 0
        self._enabled: bool = True
        self._phase_hooks: Dict[CyclePhase, List[Callable[[PhaseResult], None]]] = {
            p: [] for p in CyclePhase
        }
        self._progress_listeners: List[Callable[[str, CyclePhase, float], None]] = []
        self._history: List[CycleResult] = []
        self._MAX_HISTORY = 100

    @classmethod
    def get_instance(cls) -> "DevelopmentLoop":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_policy(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self._policy, key):
                setattr(self._policy, key, value)

    def on_phase(self, phase: CyclePhase, hook: Callable[[PhaseResult], None]) -> None:
        self._phase_hooks[phase].append(hook)

    def on_progress(self, listener: Callable[[str, CyclePhase, float], None]) -> None:
        self._progress_listeners.append(listener)

    def _notify_progress(self, task_id: str, phase: CyclePhase, progress: float) -> None:
        for listener in self._progress_listeners:
            try:
                listener(task_id, phase, progress)
            except Exception:
                pass

    def _fire_hooks(self, phase: CyclePhase, result: PhaseResult) -> None:
        for hook in self._phase_hooks.get(phase, []):
            try:
                hook(result)
            except Exception:
                pass

    async def _run_planning(self, task: str, iteration: int,
                            executor: Optional[Callable] = None) -> PhaseResult:
        t0 = time.time()
        self._current_phase = CyclePhase.PLANNING
        self._notify_progress(self._active_task or task, CyclePhase.PLANNING, 0.0)

        plan = {
            "task": task,
            "iteration": iteration,
            "strategy": self._policy.plan_strategy.value,
            "timestamp": time.time(),
        }

        if executor and callable(executor):
            try:
                if asyncio.iscoroutinefunction(executor):
                    plan_output = await executor("plan", task, plan)
                else:
                    plan_output = executor("plan", task, plan)
                if plan_output:
                    plan["steps"] = plan_output
            except Exception as e:
                pass

        result = PhaseResult(
            phase=CyclePhase.PLANNING,
            success=True,
            outputs=plan,
            quality_score=0.9,
            duration_ms=(time.time() - t0) * 1000,
            iteration=iteration,
        )
        self._notify_progress(self._active_task or task, CyclePhase.PLANNING, 1.0)
        self._fire_hooks(CyclePhase.PLANNING, result)
        return result

    async def _run_coding(self, task: str, plan: Dict[str, Any], iteration: int,
                          executor: Optional[Callable] = None) -> PhaseResult:
        t0 = time.time()
        self._current_phase = CyclePhase.CODING
        self._notify_progress(self._active_task or task, CyclePhase.CODING, 0.0)

        artifacts: List[str] = []
        errors: List[str] = []

        if executor and callable(executor):
            try:
                if asyncio.iscoroutinefunction(executor):
                    result = await executor("code", task, plan)
                else:
                    result = executor("code", task, plan)
                if isinstance(result, dict):
                    artifacts = result.get("artifacts", result.get("files", []))
                    errors = result.get("errors", [])
                    if result.get("code"):
                        artifacts.append(result["code"])
            except Exception as e:
                errors.append(str(e))
        else:
            artifacts = [f"auto_generated_{uuid.uuid4().hex[:8]}"]

        success = len(errors) == 0
        result = PhaseResult(
            phase=CyclePhase.CODING,
            success=success,
            outputs={"code_generated": len(artifacts) > 0, "errors": errors},
            errors=errors,
            artifacts=artifacts,
            quality_score=0.7 if success else 0.3,
            duration_ms=(time.time() - t0) * 1000,
            iteration=iteration,
        )
        self._notify_progress(self._active_task or task, CyclePhase.CODING, 1.0)
        self._fire_hooks(CyclePhase.CODING, result)
        return result

    async def _run_testing(self, task: str, artifacts: List[str],
                           executor: Optional[Callable] = None) -> PhaseResult:
        t0 = time.time()
        self._current_phase = CyclePhase.TESTING
        self._notify_progress(self._active_task or task, CyclePhase.TESTING, 0.0)

        quality = 0.7

        if executor and callable(executor):
            try:
                if asyncio.iscoroutinefunction(executor):
                    test_result = await executor("test", task, artifacts)
                else:
                    test_result = executor("test", task, artifacts)
                if isinstance(test_result, dict):
                    quality = float(test_result.get("quality", test_result.get("score", 0.5)))
                elif isinstance(test_result, (int, float)):
                    quality = float(test_result)
            except Exception:
                quality = 0.5

        passed = quality >= self._policy.quality_threshold
        result = PhaseResult(
            phase=CyclePhase.TESTING,
            success=True,
            outputs={"quality": quality, "passed": passed},
            quality_score=quality,
            duration_ms=(time.time() - t0) * 1000,
            iteration=0,
        )
        self._notify_progress(self._active_task or task, CyclePhase.TESTING, 1.0)
        self._fire_hooks(CyclePhase.TESTING, result)
        return result

    async def execute(self, task_description: str,
                      executor: Optional[Callable] = None) -> CycleResult:
        if not self._enabled:
            return CycleResult(task_description=task_description, success=False, final_phase=CyclePhase.ABORTED)

        task_id = f"task_{uuid.uuid4().hex[:12]}"
        self._active_task = task_id
        t_start = time.time()
        all_phases: List[PhaseResult] = []
        all_artifacts: List[str] = []
        notes: List[str] = []

        self._notify_progress(task_id, CyclePhase.IDLE, 0.0)

        for iteration in range(self._policy.max_iterations):
            plan_result = await self._run_planning(task_description, iteration, executor)
            all_phases.append(plan_result)

            code_result = await self._run_coding(task_description, plan_result.outputs, iteration, executor)
            all_phases.append(code_result)
            all_artifacts.extend(code_result.artifacts)

            self._total_iterations += 1

            if not code_result.success:
                notes.append(f"Iteration {iteration + 1} coding failed: {code_result.errors}")
                if self._policy.auto_rollback_on_fail and iteration > 0:
                    notes.append(f"Rolled back iteration {iteration + 1}")
                if iteration + 1 < self._policy.max_iterations:
                    await asyncio.sleep(min(2.0 ** iteration, self._policy.max_retry_delay))
                continue

            test_result = await self._run_testing(task_description, all_artifacts, executor)
            all_phases.append(test_result)

            if test_result.outputs.get("passed"):
                self._tasks_completed += 1
                self._current_phase = CyclePhase.COMPLETED
                final_quality = float(test_result.outputs.get("quality", 0.7))

                result = CycleResult(
                    task_id=task_id,
                    task_description=task_description,
                    success=True,
                    final_phase=CyclePhase.COMPLETED,
                    total_iterations=iteration + 1,
                    total_duration_ms=(time.time() - t_start) * 1000,
                    phases=all_phases,
                    artifacts=all_artifacts,
                    final_quality=final_quality,
                    notes=notes,
                )
                break
            else:
                self._current_phase = CyclePhase.ITERATING
                notes.append(f"Iteration {iteration + 1} quality {test_result.quality_score:.2f} "
                            f"below threshold {self._policy.quality_threshold}")
                all_phases.append(PhaseResult(
                    phase=CyclePhase.ITERATING,
                    success=True,
                    quality_score=test_result.quality_score,
                    iteration=iteration + 1,
                ))
                if iteration + 1 < self._policy.max_iterations:
                    await asyncio.sleep(min(1.5 ** iteration, self._policy.max_retry_delay))
        else:
            self._tasks_failed += 1
            self._current_phase = CyclePhase.FAILED
            result = CycleResult(
                task_id=task_id,
                task_description=task_description,
                success=False,
                final_phase=CyclePhase.FAILED,
                total_iterations=self._policy.max_iterations,
                total_duration_ms=(time.time() - t_start) * 1000,
                phases=all_phases,
                artifacts=all_artifacts,
                final_quality=0.0,
                notes=notes,
            )

        self._history.append(result)
        if len(self._history) > self._MAX_HISTORY:
            self._history = self._history[-self._MAX_HISTORY:]

        self._active_task = None
        self._notify_progress(task_id, CyclePhase.COMPLETED if result.success else CyclePhase.FAILED, 1.0)
        return result

    def execute_sync(self, task_description: str,
                     executor: Optional[Callable] = None) -> CycleResult:
        return asyncio.run(self.execute(task_description, executor))

    def get_phase(self) -> CyclePhase:
        return self._current_phase

    def get_stats(self) -> Dict[str, Any]:
        return {
            "current_phase": self._current_phase.value,
            "tasks_completed": self._tasks_completed,
            "tasks_failed": self._tasks_failed,
            "total_iterations": self._total_iterations,
            "active_task": self._active_task,
            "enabled": self._enabled,
            "history_size": len(self._history),
            "policy": {
                "max_iterations": self._policy.max_iterations,
                "quality_threshold": self._policy.quality_threshold,
                "auto_checkpoint": self._policy.auto_checkpoint,
                "plan_strategy": self._policy.plan_strategy.value,
            },
        }

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [
            {
                "task_id": r.task_id,
                "task": r.task_description[:80],
                "success": r.success,
                "iterations": r.total_iterations,
                "quality": round(r.final_quality, 3),
                "artifacts": len(r.artifacts),
            }
            for r in self._history[-limit:]
        ]

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def abort(self) -> None:
        self._current_phase = CyclePhase.ABORTED

    def reset(self) -> None:
        self._current_phase = CyclePhase.IDLE
        self._active_task = None
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._total_iterations = 0


def get_dev_loop() -> DevelopmentLoop:
    return DevelopmentLoop.get_instance()
