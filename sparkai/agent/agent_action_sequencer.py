"""
SparkLabs Agent - Action Sequencer

Orders and sequences game development operations into optimal
execution pipelines. Determines the correct ordering of file
creation, component attachment, asset importing, and code
generation steps to produce valid, runnable game projects.

Architecture:
  ActionSequencer
    |-- DependencyGraph (which operations depend on others)
    |-- ExecutionPipeline (ordered list of operations to run)
    |-- ConflictDetector (find ordering conflicts before execution)
    |-- ParallelOpportunityFinder (identify safe parallel steps)
    |-- RollbackPlan (undo sequence if any step fails)

Operation Types (game dev specific ordering constraints):
  - PROJECT_INIT must come before everything
  - ASSET_IMPORT before SPRITE_REFERENCE
  - COMPONENT_CREATE before COMPONENT_ATTACH
  - CODE_GEN before CODE_COMPILE
  - SCENE_CREATE before ENTITY_SPAWN
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class OpType(Enum):
    PROJECT_INIT = ("project_init", 100)
    ASSET_IMPORT = ("asset_import", 90)
    CODE_GEN = ("code_gen", 80)
    COMPONENT_CREATE = ("component_create", 70)
    COMPONENT_ATTACH = ("component_attach", 60)
    SCENE_CREATE = ("scene_create", 50)
    ENTITY_SPAWN = ("entity_spawn", 40)
    PROPERTY_SET = ("property_set", 30)
    CODE_COMPILE = ("code_compile", 20)
    DEPLOY = ("deploy", 10)


class OpStatus(Enum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


@dataclass
class Operation:
    op_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    op_type: OpType = OpType.PROPERTY_SET
    description: str = ""
    target: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    status: OpStatus = OpStatus.PENDING
    priority: int = 0
    estimated_duration_ms: float = 100.0

    def is_ready(self, completed_ids: Set[str]) -> bool:
        return all(dep in completed_ids for dep in self.depends_on)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "op_id": self.op_id,
            "op_type": self.op_type.value[0],
            "description": self.description,
            "target": self.target,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "priority": self.priority,
        }


@dataclass
class ExecutionPipeline:
    pipeline_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    operations: List[Operation] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_count: int = 0
    failed_count: int = 0

    @property
    def progress(self) -> float:
        total = len(self.operations)
        if total == 0:
            return 1.0
        succeeded = sum(
            1 for op in self.operations if op.status == OpStatus.SUCCEEDED
        )
        return succeeded / total

    @property
    def execution_order(self) -> List[str]:
        in_degree: Dict[str, int] = defaultdict(int)
        adj: Dict[str, List[str]] = defaultdict(list)
        op_map: Dict[str, Operation] = {op.op_id: op for op in self.operations}

        for op in self.operations:
            if op.op_id not in in_degree:
                in_degree[op.op_id] = 0
            for dep in op.depends_on:
                adj[dep].append(op.op_id)
                in_degree[op.op_id] += 1

        queue = deque([oid for oid, deg in in_degree.items() if deg == 0])
        order: List[str] = []
        while queue:
            oid = queue.popleft()
            order.append(oid)
            for neighbor in adj[oid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        return order

    def get_next_operations(self) -> List[Operation]:
        completed: Set[str] = {
            op.op_id
            for op in self.operations
            if op.status == OpStatus.SUCCEEDED
        }
        ready = [
            op
            for op in self.operations
            if op.status == OpStatus.PENDING and op.is_ready(completed)
        ]
        ready.sort(key=lambda o: (-o.priority, o.op_type.value[1]))
        return ready

    def can_parallelize(self) -> List[List[Operation]]:
        completed: Set[str] = {
            op.op_id
            for op in self.operations
            if op.status == OpStatus.SUCCEEDED
        }
        ready = [
            op
            for op in self.operations
            if op.status == OpStatus.PENDING and op.is_ready(completed)
        ]
        groups: Dict[str, List[Operation]] = defaultdict(list)
        for op in ready:
            groups[op.op_type.value[0]].append(op)
        return [g for g in groups.values() if len(g) > 1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "name": self.name,
            "operation_count": len(self.operations),
            "progress": round(self.progress, 3),
            "completed": self.completed_count,
            "failed": self.failed_count,
            "execution_order": self.execution_order,
            "ready_operations": [op.to_dict() for op in self.get_next_operations()],
            "parallel_groups": len(self.can_parallelize()),
        }

    def to_full_dict(self) -> Dict[str, Any]:
        return {
            **self.to_dict(),
            "operations": [op.to_dict() for op in self.operations],
        }


class ActionSequencer:
    """Orders game development operations into optimal execution pipelines."""

    _instance: Optional["ActionSequencer"] = None
    _lock = threading.Lock()

    MAX_PIPELINES = 100
    MAX_OPERATIONS_PER_PIPELINE = 200

    def __init__(self):
        self._pipelines: Dict[str, ExecutionPipeline] = {}
        self._ordering_rules: Dict[str, List[str]] = {
            OpType.PROJECT_INIT.value[0]: [],
            OpType.ASSET_IMPORT.value[0]: [OpType.PROJECT_INIT.value[0]],
            OpType.CODE_GEN.value[0]: [OpType.PROJECT_INIT.value[0]],
            OpType.COMPONENT_CREATE.value[0]: [OpType.PROJECT_INIT.value[0]],
            OpType.COMPONENT_ATTACH.value[0]: [OpType.COMPONENT_CREATE.value[0]],
            OpType.SCENE_CREATE.value[0]: [OpType.PROJECT_INIT.value[0]],
            OpType.ENTITY_SPAWN.value[0]: [
                OpType.SCENE_CREATE.value[0],
                OpType.COMPONENT_CREATE.value[0],
            ],
            OpType.PROPERTY_SET.value[0]: [OpType.ENTITY_SPAWN.value[0]],
            OpType.CODE_COMPILE.value[0]: [OpType.CODE_GEN.value[0]],
            OpType.DEPLOY.value[0]: [OpType.CODE_COMPILE.value[0]],
        }

    @classmethod
    def get_instance(cls) -> "ActionSequencer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def create_pipeline(self, name: str = "") -> ExecutionPipeline:
        pipeline = ExecutionPipeline(name=name)
        self._pipelines[pipeline.pipeline_id] = pipeline
        return pipeline

    def add_operation(
        self,
        pipeline_id: str,
        op_type: OpType,
        description: str = "",
        target: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[str]] = None,
        priority: int = 0,
    ) -> Optional[Operation]:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline or len(pipeline.operations) >= self.MAX_OPERATIONS_PER_PIPELINE:
            return None

        op = Operation(
            op_type=op_type,
            description=description,
            target=target,
            parameters=parameters or {},
            depends_on=depends_on or [],
            priority=priority,
        )
        pipeline.operations.append(op)
        return op

    def auto_sequence(
        self,
        pipeline_id: str,
        operations: List[Tuple[str, str, str, Dict[str, Any]]],
    ) -> List[Operation]:
        """Auto-sequence operations by applying ordering rules.
        Each tuple: (op_type_str, description, target, parameters)"""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return []

        created: List[Tuple[Operation, int]] = []
        op_index: Dict[str, int] = {}

        for i, (op_type_str, desc, target, params) in enumerate(operations):
            try:
                ot = OpType(op_type_str)
            except ValueError:
                ot = OpType.PROPERTY_SET

            op = self.add_operation(
                pipeline_id, ot, desc, target, params, priority=i
            )
            if op:
                created.append((op, i))
                op_index[ot.value[0]] = i

        for op, idx in created:
            required_deps = self._ordering_rules.get(op.op_type.value[0], [])
            for dep_type_name in required_deps:
                for other_op, other_idx in created:
                    if (
                        other_op.op_type.value[0] == dep_type_name
                        and other_op.op_id not in op.depends_on
                    ):
                        op.depends_on.append(other_op.op_id)

        return [op for op, _ in created]

    def get_pipeline(self, pipeline_id: str) -> Optional[ExecutionPipeline]:
        return self._pipelines.get(pipeline_id)

    def update_operation_status(
        self,
        pipeline_id: str,
        op_id: str,
        status: OpStatus,
    ) -> Optional[Operation]:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return None
        for op in pipeline.operations:
            if op.op_id == op_id:
                op.status = status
                if status == OpStatus.SUCCEEDED:
                    pipeline.completed_count += 1
                elif status == OpStatus.FAILED:
                    pipeline.failed_count += 1
                return op
        return None

    def list_pipelines(self) -> List[ExecutionPipeline]:
        return list(self._pipelines.values())

    def detect_conflicts(self, pipeline_id: str) -> List[Tuple[str, str, str]]:
        """Detect circular dependencies and ordering conflicts."""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return []

        conflicts: List[Tuple[str, str, str]] = []
        for op in pipeline.operations:
            for dep_id in op.depends_on:
                dep_op = next(
                    (o for o in pipeline.operations if o.op_id == dep_id), None
                )
                if dep_op and op.op_id in dep_op.depends_on:
                    conflicts.append((
                        op.op_id,
                        dep_id,
                        "circular_dependency",
                    ))

        order = pipeline.execution_order
        if len(order) != len(pipeline.operations):
            for op in pipeline.operations:
                if op.op_id not in order:
                    conflicts.append((
                        op.op_id,
                        "",
                        "unreachable_in_order",
                    ))

        return conflicts

    def get_stats(self) -> Dict[str, Any]:
        total_ops = sum(len(p.operations) for p in self._pipelines.values())
        succeeded = sum(
            sum(1 for op in p.operations if op.status == OpStatus.SUCCEEDED)
            for p in self._pipelines.values()
        )
        return {
            "pipelines": len(self._pipelines),
            "total_operations": total_ops,
            "succeeded_operations": succeeded,
            "ordering_rules": len(self._ordering_rules),
            "operation_types": len(OpType),
            "overall_progress": round(
                succeeded / max(1, total_ops), 3
            ),
        }

    def delete_pipeline(self, pipeline_id: str) -> bool:
        if pipeline_id in self._pipelines:
            del self._pipelines[pipeline_id]
            return True
        return False


def get_action_sequencer() -> ActionSequencer:
    return ActionSequencer.get_instance()