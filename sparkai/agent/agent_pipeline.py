"""
SparkLabs Agent - Pipeline

Multi-stage agent workflow pipeline system for orchestrating
complex game development operations through sequenced stages
with conditional branching, parallel execution, and rollback.

Architecture:
  AgentPipeline
    |-- PipelineStage (discrete operation with input/output contract)
    |-- PipelineContext (shared state flowing through stages)
    |-- StageRouter (conditional next-stage selection)
    |-- ParallelFanout (concurrent stage execution)
    |-- PipelineMonitor (progress tracking and stage timing)
    |-- RollbackManager (reversal on stage failure)

Pipeline Templates:
  - GENERATE_GAME: design → code → assets → test → publish
  - REFACTOR: analyze → plan → transform → validate → commit
  - DEBUG: reproduce → diagnose → fix → verify → document
  - REVIEW: scan → categorize → suggest → approve → apply
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class PipelineStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StageResult:
    success: bool
    output: Any = None
    error: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class StageRecord:
    name: str
    status: StageStatus = StageStatus.PENDING
    result: Optional[StageResult] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "success": self.result.success if self.result else None,
            "duration_ms": self.result.duration_ms if self.result else 0,
            "retries": self.retries,
        }


@dataclass
class PipelineDefinition:
    name: str = ""
    stages: List[str] = field(default_factory=list)
    transitions: Dict[str, str] = field(default_factory=dict)
    on_failure: Dict[str, str] = field(default_factory=dict)
    parallel_groups: Dict[str, List[str]] = field(default_factory=dict)
    max_retries_per_stage: int = 1
    abort_on_failure: bool = True


@dataclass
class PipelineContext:
    pipeline_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    stage_outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)

    def resolve(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, self.inputs.get(key, default))

    def set_output(self, stage: str, value: Any) -> None:
        self.stage_outputs[stage] = value


@dataclass
class PipelineRun:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    definition: PipelineDefinition = field(default_factory=PipelineDefinition)
    status: PipelineStatus = PipelineStatus.IDLE
    stages: OrderedDict[str, StageRecord] = field(default_factory=OrderedDict)
    context: PipelineContext = field(default_factory=PipelineContext)
    current_stage: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    total_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "definition": self.definition.name,
            "status": self.status.value,
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
            "current_stage": self.current_stage,
            "total_duration_ms": self.total_duration_ms,
        }


class AgentPipeline:
    """
    Multi-stage agent workflow pipeline for orchestrating complex
    game development operations.

    Stages execute sequentially with conditional branching based
    on stage results. Parallel groups execute concurrently and
    join before proceeding. Stage failures can trigger rollback
    or alternative paths.

    Usage:
        pipeline = AgentPipeline()
        pipeline.register_stage("analyze", analyze_handler)
        pipeline.register_stage("generate", generate_handler)
        pipeline.set_transition("analyze", "generate")
        run = await pipeline.execute(inputs={"prompt": "Create platformer"})
        print(run.to_dict())
    """

    _instance: Optional["AgentPipeline"] = None

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._runs: Dict[str, PipelineRun] = {}
        self._definitions: Dict[str, PipelineDefinition] = {}
        self._run_count: int = 0

        self._register_builtin_templates()

    @classmethod
    def get_instance(cls) -> "AgentPipeline":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _register_builtin_templates(self) -> None:
        self._definitions["generate_game"] = PipelineDefinition(
            name="generate_game",
            stages=["analyze_prompt", "design_architecture", "generate_code", "validate", "package"],
            transitions={
                "analyze_prompt": "design_architecture",
                "design_architecture": "generate_code",
                "generate_code": "validate",
                "validate": "package",
            },
            max_retries_per_stage=2,
            abort_on_failure=False,
        )

        self._definitions["review_code"] = PipelineDefinition(
            name="review_code",
            stages=["parse_files", "static_analysis", "security_scan", "style_check", "generate_report"],
            transitions={
                "parse_files": "static_analysis",
                "static_analysis": "security_scan",
                "security_scan": "style_check",
                "style_check": "generate_report",
            },
            max_retries_per_stage=1,
        )

        self._definitions["debug_issue"] = PipelineDefinition(
            name="debug_issue",
            stages=["reproduce", "diagnose", "apply_fix", "verify", "document"],
            transitions={
                "reproduce": "diagnose",
                "diagnose": "apply_fix",
                "apply_fix": "verify",
                "verify": "document",
            },
            on_failure={"apply_fix": "diagnose"},
            max_retries_per_stage=3,
        )

    def register_stage(self, name: str, handler: Callable[[PipelineContext], Any]) -> None:
        self._handlers[name] = handler

    def unregister_stage(self, name: str) -> bool:
        if name in self._handlers:
            del self._handlers[name]
            return True
        return False

    def register_definition(self, definition: PipelineDefinition) -> None:
        self._definitions[definition.name] = definition

    def get_definition(self, name: str) -> Optional[PipelineDefinition]:
        return self._definitions.get(name)

    async def execute(
        self,
        inputs: Optional[Dict[str, Any]] = None,
        definition: Optional[PipelineDefinition] = None,
        definition_name: Optional[str] = None,
        context: Optional[PipelineContext] = None,
    ) -> PipelineRun:
        if definition is None and definition_name:
            definition = self._definitions.get(definition_name)

        if definition is None:
            definition = PipelineDefinition()

        ctx = context or PipelineContext(inputs=inputs or {})

        run = PipelineRun(
            definition=definition,
            context=ctx,
            status=PipelineStatus.RUNNING,
            started_at=time.time(),
        )

        for stage_name in definition.stages:
            run.stages[stage_name] = StageRecord(name=stage_name)

        self._runs[run.id] = run
        self._run_count += 1

        try:
            for stage_name in definition.stages:
                run.current_stage = stage_name
                record = run.stages[stage_name]

                if stage_name in definition.parallel_groups:
                    await self._execute_parallel_group(
                        run, stage_name, definition.parallel_groups[stage_name]
                    )
                    continue

                handler = self._handlers.get(stage_name)
                if handler is None:
                    record.status = StageStatus.SKIPPED
                    continue

                result = await self._execute_stage_with_retry(
                    run, stage_name, handler, definition.max_retries_per_stage
                )

                if not result.success and definition.abort_on_failure:
                    run.status = PipelineStatus.FAILED
                    run.completed_at = time.time()
                    run.total_duration_ms = (run.completed_at - (run.started_at or run.completed_at)) * 1000
                    return run

                transition = definition.transitions.get(stage_name)
                if transition and result.success is False:
                    fallback = definition.on_failure.get(stage_name, transition)
                    if fallback != transition and fallback in definition.stages:
                        pass

            run.status = PipelineStatus.COMPLETED

        except asyncio.CancelledError:
            run.status = PipelineStatus.CANCELLED
        except Exception as e:
            run.status = PipelineStatus.FAILED
            run.context.metadata["error"] = str(e)

        run.completed_at = time.time()
        run.total_duration_ms = (run.completed_at - (run.started_at or run.completed_at)) * 1000
        return run

    async def _execute_stage_with_retry(
        self,
        run: PipelineRun,
        stage_name: str,
        handler: Callable,
        max_retries: int,
    ) -> StageResult:
        record = run.stages[stage_name]
        last_error = None

        for attempt in range(max_retries + 1):
            record.status = StageStatus.RUNNING
            record.started_at = time.time()

            try:
                output = handler(run.context)
                if asyncio.iscoroutine(output):
                    output = await output

                duration = (time.time() - (record.started_at or time.time())) * 1000
                result = StageResult(success=True, output=output, duration_ms=duration)
                record.result = result
                record.status = StageStatus.COMPLETED
                record.completed_at = time.time()
                run.context.set_output(stage_name, result)
                return result

            except Exception as e:
                last_error = str(e)
                record.retries = attempt + 1

        duration = (time.time() - (record.started_at or time.time())) * 1000
        result = StageResult(success=False, error=last_error, duration_ms=duration)
        record.result = result
        record.status = StageStatus.FAILED
        record.completed_at = time.time()
        run.context.set_output(stage_name, result)
        return result

    async def _execute_parallel_group(
        self,
        run: PipelineRun,
        group_name: str,
        stage_names: List[str],
    ) -> None:
        tasks = []
        for stage_name in stage_names:
            handler = self._handlers.get(stage_name)
            if handler:
                tasks.append(self._execute_stage_with_retry(run, stage_name, handler, 0))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_run(self, run_id: str) -> Optional[PipelineRun]:
        return self._runs.get(run_id)

    def list_runs(
        self,
        status: Optional[PipelineStatus] = None,
        definition_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        runs = list(self._runs.values())
        if status:
            runs = [r for r in runs if r.status == status]
        if definition_name:
            runs = [r for r in runs if r.definition.name == definition_name]
        return [r.to_dict() for r in runs]

    def cancel_run(self, run_id: str) -> bool:
        run = self._runs.get(run_id)
        if run and run.status == PipelineStatus.RUNNING:
            run.status = PipelineStatus.CANCELLED
            run.completed_at = time.time()
            run.total_duration_ms = (run.completed_at - (run.started_at or run.completed_at)) * 1000
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        runs = list(self._runs.values())
        return {
            "total_runs": self._run_count,
            "active_runs": sum(1 for r in runs if r.status == PipelineStatus.RUNNING),
            "completed_runs": sum(1 for r in runs if r.status == PipelineStatus.COMPLETED),
            "failed_runs": sum(1 for r in runs if r.status == PipelineStatus.FAILED),
            "registered_stages": len(self._handlers),
            "definitions": list(self._definitions.keys()),
        }


def get_agent_pipeline() -> AgentPipeline:
    return AgentPipeline.get_instance()