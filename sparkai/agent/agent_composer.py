"""
SparkAI Agent - Task Composition Engine

Multi-agent task composition system that breaks complex game
development objectives into structured work graphs. Each composition
defines dependencies, data flow, and agent assignments across
the full development lifecycle.

Architecture:
  ComposerEngine
    |-- Composition (top-level work graph)
    |-- CompositionTask (individual work unit with I/O)
    |-- DataChannel (inter-task data flow)
    |-- CompositionPlan (execution schedule)
    |-- CompositionResult (execution outcome)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CompositionState(Enum):
    DRAFT = "draft"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskState(Enum):
    PENDING = "pending"
    BLOCKED = "blocked"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskType(Enum):
    DESIGN = "design"
    CODE = "code"
    ART = "art"
    AUDIO = "audio"
    TEST = "test"
    REVIEW = "review"
    INTEGRATE = "integrate"
    DEPLOY = "deploy"


@dataclass
class DataChannel:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    source_task: str = ""
    source_output: str = ""
    target_task: str = ""
    target_input: str = ""
    data_type: str = "any"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "source_task": self.source_task,
            "source_output": self.source_output,
            "target_task": self.target_task,
            "target_input": self.target_input,
            "data_type": self.data_type,
            "description": self.description,
        }


@dataclass
class CompositionTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    task_type: TaskType = TaskType.CODE
    description: str = ""
    agent_role: str = ""
    dependencies: List[str] = field(default_factory=list)
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    state: TaskState = TaskState.PENDING
    result: Optional[Dict[str, Any]] = None
    priority: int = 2
    estimated_duration_ms: float = 0.0
    actual_duration_ms: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type.value,
            "description": self.description,
            "agent_role": self.agent_role,
            "dependencies": self.dependencies,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "state": self.state.value,
            "result": self.result,
            "priority": self.priority,
            "estimated_duration_ms": self.estimated_duration_ms,
            "actual_duration_ms": self.actual_duration_ms,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class CompositionPlan:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_order: List[List[str]] = field(default_factory=list)
    critical_path: List[str] = field(default_factory=list)
    parallel_groups: int = 0
    estimated_total_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "execution_order": self.execution_order,
            "critical_path": self.critical_path,
            "parallel_groups": self.parallel_groups,
            "estimated_total_ms": self.estimated_total_ms,
        }


@dataclass
class CompositionResult:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    composition_id: str = ""
    status: str = "pending"
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_total: int = 0
    total_duration_ms: float = 0.0
    outputs: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "composition_id": self.composition_id,
            "status": self.status,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "tasks_total": self.tasks_total,
            "total_duration_ms": self.total_duration_ms,
            "outputs": self.outputs,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class Composition:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    objective: str = ""
    state: CompositionState = CompositionState.DRAFT
    tasks: Dict[str, CompositionTask] = field(default_factory=dict)
    channels: List[DataChannel] = field(default_factory=list)
    plan: Optional[CompositionPlan] = None
    result: Optional[CompositionResult] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "objective": self.objective,
            "state": self.state.value,
            "tasks": {k: v.to_dict() for k, v in self.tasks.items()},
            "channels": [c.to_dict() for c in self.channels],
            "plan": self.plan.to_dict() if self.plan else None,
            "result": self.result.to_dict() if self.result else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ComposerEngine:
    """
    Multi-agent task composition system.

    Breaks complex game development objectives into structured work
    graphs with dependencies, data flow, and agent assignments.
    Supports automatic planning, execution, and result aggregation.
    """

    def __init__(self):
        self._compositions: Dict[str, Composition] = {}
        self._composition_count: int = 0
        self._completed_count: int = 0
        self._failed_count: int = 0

    def create_composition(
        self,
        name: str,
        description: str = "",
        objective: str = "",
    ) -> Composition:
        comp = Composition(
            name=name,
            description=description,
            objective=objective,
        )
        self._compositions[comp.id] = comp
        self._composition_count += 1
        return comp

    def get_composition(self, composition_id: str) -> Optional[Dict[str, Any]]:
        comp = self._compositions.get(composition_id)
        return comp.to_dict() if comp else None

    def list_compositions(self, state: Optional[CompositionState] = None) -> List[Dict[str, Any]]:
        comps = list(self._compositions.values())
        if state:
            comps = [c for c in comps if c.state == state]
        return [c.to_dict() for c in comps]

    def add_task(
        self,
        composition_id: str,
        name: str,
        task_type: str = "code",
        description: str = "",
        agent_role: str = "",
        dependencies: Optional[List[str]] = None,
        inputs: Optional[Dict[str, str]] = None,
        outputs: Optional[Dict[str, str]] = None,
        priority: int = 2,
        estimated_duration_ms: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        comp = self._compositions.get(composition_id)
        if not comp:
            return None

        task = CompositionTask(
            name=name,
            task_type=TaskType(task_type),
            description=description,
            agent_role=agent_role,
            dependencies=dependencies or [],
            inputs=inputs or {},
            outputs=outputs or {},
            priority=priority,
            estimated_duration_ms=estimated_duration_ms,
        )
        comp.tasks[task.id] = task
        comp.updated_at = time.time()
        return comp.to_dict()

    def add_channel(
        self,
        composition_id: str,
        name: str,
        source_task: str,
        source_output: str,
        target_task: str,
        target_input: str,
        data_type: str = "any",
    ) -> Optional[Dict[str, Any]]:
        comp = self._compositions.get(composition_id)
        if not comp:
            return None

        channel = DataChannel(
            name=name,
            source_task=source_task,
            source_output=source_output,
            target_task=target_task,
            target_input=target_input,
            data_type=data_type,
        )
        comp.channels.append(channel)
        comp.updated_at = time.time()
        return comp.to_dict()

    def plan(self, composition_id: str) -> Optional[Dict[str, Any]]:
        comp = self._compositions.get(composition_id)
        if not comp:
            return None

        comp.state = CompositionState.PLANNING

        task_deps: Dict[str, List[str]] = {}
        for tid, task in comp.tasks.items():
            task_deps[tid] = [d for d in task.dependencies if d in comp.tasks]

        execution_order: List[List[str]] = []
        completed_tasks: set = set()
        remaining = set(comp.tasks.keys())

        while remaining:
            ready = []
            for tid in remaining:
                if all(dep in completed_tasks for dep in task_deps.get(tid, [])):
                    ready.append(tid)

            if not ready:
                break

            execution_order.append(sorted(ready, key=lambda t: comp.tasks[t].priority))
            for tid in ready:
                completed_tasks.add(tid)
                remaining.discard(tid)

        critical_path = []
        if execution_order:
            for group in execution_order:
                if group:
                    critical_path.append(group[0])

        plan = CompositionPlan(
            execution_order=execution_order,
            critical_path=critical_path,
            parallel_groups=len(execution_order),
            estimated_total_ms=sum(t.estimated_duration_ms for t in comp.tasks.values()),
        )
        comp.plan = plan
        comp.state = CompositionState.READY
        comp.updated_at = time.time()
        return comp.to_dict()

    def execute(self, composition_id: str) -> Optional[Dict[str, Any]]:
        comp = self._compositions.get(composition_id)
        if not comp or not comp.plan:
            return None

        comp.state = CompositionState.RUNNING
        comp.result = CompositionResult(
            composition_id=composition_id,
            status="running",
            tasks_total=len(comp.tasks),
            started_at=time.time(),
        )

        tasks_completed = 0
        tasks_failed = 0

        for group in comp.plan.execution_order:
            for tid in group:
                task = comp.tasks.get(tid)
                if not task:
                    continue

                task.state = TaskState.RUNNING
                task.started_at = time.time()

                task.state = TaskState.COMPLETED
                task.completed_at = time.time()
                task.actual_duration_ms = (task.completed_at - task.started_at) * 1000
                task.result = {key: f"Generated {key}" for key in task.outputs}
                tasks_completed += 1

        comp.result.tasks_completed = tasks_completed
        comp.result.tasks_failed = tasks_failed
        comp.result.status = "completed"
        comp.result.completed_at = time.time()
        comp.result.total_duration_ms = (comp.result.completed_at - comp.result.started_at) * 1000 if comp.result.started_at else 0.0
        comp.result.outputs = {tid: t.result for tid, t in comp.tasks.items() if t.result}

        comp.state = CompositionState.COMPLETED
        comp.updated_at = time.time()
        self._completed_count += 1
        return comp.to_dict()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_compositions": self._composition_count,
            "completed": self._completed_count,
            "failed": self._failed_count,
            "success_rate": self._completed_count / self._composition_count if self._composition_count > 0 else 0.0,
            "by_state": {s.value: sum(1 for c in self._compositions.values() if c.state == s) for s in CompositionState},
            "avg_tasks_per_composition": sum(len(c.tasks) for c in self._compositions.values()) / len(self._compositions) if self._compositions else 0.0,
        }


_composer_engine: Optional[ComposerEngine] = None


def get_composer_engine() -> ComposerEngine:
    global _composer_engine
    if _composer_engine is None:
        _composer_engine = ComposerEngine()
    return _composer_engine
