"""
SparkLabs Agent - Cross-Module Orchestrator

Orchestration system that coordinates all SparkLabs agent subsystems
across module boundaries. Manages pipeline execution, module contracts,
circuit breaking, and health monitoring for distributed agent workflows.

Architecture:
  AgentCrossModuleOrchestrator
    |-- ModulePipeline (ordered sequence of module executions)
    |-- ModuleContract (data contracts and validation between modules)
    |-- OrchestrationTask (tracked execution of a pipeline)
    |-- CircuitBreaker (failure isolation for module-to-module calls)
    |-- ModuleHealthReport (real-time module status and metrics)

Module States:
  - IDLE: Module registered but not executing tasks
  - RUNNING: Module actively processing tasks
  - DEGRADED: Module operating with reduced capacity
  - ERROR: Module encountered an unrecoverable failure
  - RECOVERING: Module transitioning back from ERROR to RUNNING
  - OFFLINE: Module unregistered or unavailable

Pipeline Statuses:
  - PENDING: Pipeline defined but not yet started
  - IN_PROGRESS: Pipeline actively executing through module sequence
  - PAUSED: Pipeline execution suspended
  - COMPLETED: Pipeline finished all modules successfully
  - FAILED: Pipeline terminated due to error
  - PARTIALLY_COMPLETED: Some modules finished, others failed or skipped
  - CANCELLED: Pipeline explicitly cancelled by user

Circuit Breaker States:
  - CLOSED: Normal operation — cross-module calls pass through
  - OPEN: Failure threshold exceeded — calls are rejected
  - HALF_OPEN: Probing state — limited calls test recovery

Usage:
    orchestrator = get_cross_module_orchestrator()
    module_id = orchestrator.register_module(
        "GameDesignAgent", "designer",
        ["level_design", "mechanic_balancing"],
        ["AssetGenerator", "PhysicsEngine"],
    )
    pipeline = orchestrator.create_pipeline(
        "Level Generation",
        ["GameDesignAgent", "AssetGenerator", "PhysicsEngine"],
        entry_condition={"mode": "procedural"},
        exit_condition={"quality_score": 0.8},
    )
    task = orchestrator.execute_pipeline(pipeline.pipeline_id, {"theme": "dungeon"})
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

_time_module = time


class ModuleStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    DEGRADED = "degraded"
    ERROR = "error"
    RECOVERING = "recovering"
    OFFLINE = "offline"


class PipelineStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    CANCELLED = "cancelled"


class BreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class TaskPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


@dataclass
class ModulePipeline:
    pipeline_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    module_sequence: List[str] = field(default_factory=list)
    data_flow_graph: Dict[str, List[str]] = field(default_factory=dict)
    entry_condition: Dict[str, Any] = field(default_factory=dict)
    exit_condition: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 300.0
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    execution_count: int = 0
    success_count: int = 0
    avg_duration: float = 0.0
    last_execution: float = 0.0
    created_at: float = field(default_factory=lambda: _time_module.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "name": self.name,
            "module_sequence": self.module_sequence,
            "data_flow_graph": self.data_flow_graph,
            "entry_condition": self.entry_condition,
            "exit_condition": self.exit_condition,
            "timeout": self.timeout,
            "retry_policy": self.retry_policy,
            "is_active": self.is_active,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "avg_duration": self.avg_duration,
            "last_execution": self.last_execution,
            "created_at": self.created_at,
        }


@dataclass
class ModuleContract:
    contract_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_module: str = ""
    target_module: str = ""
    data_schema: Dict[str, Any] = field(default_factory=dict)
    validation_rules: List[Dict[str, Any]] = field(default_factory=list)
    fallback_behavior: Dict[str, Any] = field(default_factory=dict)
    rate_limit: float = 0.0
    circuit_breaker_threshold: int = 5
    created_at: float = field(default_factory=lambda: _time_module.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "source_module": self.source_module,
            "target_module": self.target_module,
            "data_schema": self.data_schema,
            "validation_rules": self.validation_rules,
            "fallback_behavior": self.fallback_behavior,
            "rate_limit": self.rate_limit,
            "circuit_breaker_threshold": self.circuit_breaker_threshold,
            "created_at": self.created_at,
        }


@dataclass
class OrchestrationTask:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    pipeline_id: str = ""
    input_context: Dict[str, Any] = field(default_factory=dict)
    output_context: Dict[str, Any] = field(default_factory=dict)
    status: PipelineStatus = PipelineStatus.PENDING
    progress: float = 0.0
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_modules: List[str] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_log: List[str] = field(default_factory=list)
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "pipeline_id": self.pipeline_id,
            "input_context": self.input_context,
            "output_context": self.output_context,
            "status": self.status.value,
            "progress": self.progress,
            "priority": self.priority.value,
            "assigned_modules": self.assigned_modules,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "error_log": self.error_log,
            "retry_count": self.retry_count,
        }


@dataclass
class CircuitBreaker:
    breaker_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    contract_id: str = ""
    failure_threshold: int = 5
    failure_count: int = 0
    recovery_time: float = 30.0
    state: BreakerState = BreakerState.CLOSED
    last_failure: float = 0.0
    last_success: float = 0.0
    consecutive_successes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "breaker_id": self.breaker_id,
            "contract_id": self.contract_id,
            "failure_threshold": self.failure_threshold,
            "failure_count": self.failure_count,
            "recovery_time": self.recovery_time,
            "state": self.state.value,
            "last_failure": self.last_failure,
            "last_success": self.last_success,
            "consecutive_successes": self.consecutive_successes,
        }


@dataclass
class ModuleHealthReport:
    module_name: str = ""
    status: ModuleStatus = ModuleStatus.IDLE
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_tasks: int = 0
    error_rate: float = 0.0
    avg_response_time: float = 0.0
    last_heartbeat: float = field(default_factory=lambda: _time_module.time())
    dependencies_status: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_name": self.module_name,
            "status": self.status.value,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "active_tasks": self.active_tasks,
            "error_rate": self.error_rate,
            "avg_response_time": self.avg_response_time,
            "last_heartbeat": self.last_heartbeat,
            "dependencies_status": self.dependencies_status,
            "warnings": self.warnings,
        }


@dataclass
class _ModuleRegistration:
    module_name: str = ""
    module_type: str = ""
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 10
    health_check_endpoint: str = ""
    status: ModuleStatus = ModuleStatus.IDLE
    registered_at: float = field(default_factory=lambda: _time_module.time())
    active_task_ids: Set[str] = field(default_factory=set)
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    total_execution_time: float = 0.0
    failure_window: Deque[float] = field(default_factory=deque)


def _generate_uid_stub() -> str:
    return uuid.uuid4().hex


class AgentCrossModuleOrchestrator:
    """
    Cross-module orchestration system for coordinating agent subsystems.

    Manages module registration, pipeline definition and execution,
    inter-module contracts with circuit breaking, and real-time health
    monitoring across all SparkLabs agent subsystems.

    Usage:
        orchestrator = AgentCrossModuleOrchestrator.get_instance()
        orchestrator.register_module("MyAgent", "worker", ["task_a"], [])
        pipeline = orchestrator.create_pipeline("My Pipeline", ["MyAgent"], {}, {})
    """

    _instance: Optional["AgentCrossModuleOrchestrator"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "AgentCrossModuleOrchestrator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentCrossModuleOrchestrator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        _time_module.sleep(0.001)
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._modules: Dict[str, _ModuleRegistration] = {}
        self._pipelines: Dict[str, ModulePipeline] = {}
        self._contracts: Dict[str, ModuleContract] = {}
        self._tasks: Dict[str, OrchestrationTask] = {}
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._pipeline_history: Dict[str, List[OrchestrationTask]] = {}
        self._cross_module_calls: List[Dict[str, Any]] = []
        self._interaction_records: List[Dict[str, Any]] = []
        self._total_circuit_trips: int = 0
        self._total_completed_tasks: int = 0
        self._total_failed_tasks: int = 0
        self._total_executions: int = 0
        self._total_execution_time: float = 0.0
        self._initialized = True

    # --------------- Module Registration ---------------

    def register_module(
        self,
        module_name: str,
        module_type: str,
        capabilities: List[str],
        dependencies: List[str],
        max_concurrent_tasks: int = 10,
        health_check_endpoint: str = "",
    ) -> str:
        mid = _generate_uid_stub()
        registration = _ModuleRegistration(
            module_name=module_name,
            module_type=module_type,
            capabilities=list(capabilities),
            dependencies=list(dependencies),
            max_concurrent_tasks=max_concurrent_tasks,
            health_check_endpoint=health_check_endpoint,
        )
        self._modules[mid] = registration
        return mid

    def unregister_module(self, module_name: str) -> bool:
        target_id: Optional[str] = None
        for mid, reg in self._modules.items():
            if reg.module_name == module_name:
                target_id = mid
                break
        if target_id is None:
            return False
        self._modules.pop(target_id, None)
        self._remove_module_from_pipelines(module_name)
        return True

    def _remove_module_from_pipelines(self, module_name: str) -> None:
        for pipeline in self._pipelines.values():
            if module_name in pipeline.module_sequence:
                pipeline.module_sequence = [
                    m for m in pipeline.module_sequence if m != module_name
                ]
            if module_name in pipeline.data_flow_graph:
                del pipeline.data_flow_graph[module_name]
            for src, targets in list(pipeline.data_flow_graph.items()):
                pipeline.data_flow_graph[src] = [
                    t for t in targets if t != module_name
                ]

    # --------------- Pipeline Management ---------------

    def create_pipeline(
        self,
        name: str,
        module_sequence: List[str],
        entry_condition: Optional[Dict[str, Any]] = None,
        exit_condition: Optional[Dict[str, Any]] = None,
        timeout: float = 300.0,
        retry_policy: Optional[Dict[str, Any]] = None,
    ) -> ModulePipeline:
        pipeline = ModulePipeline(
            name=name,
            module_sequence=list(module_sequence),
            entry_condition=entry_condition or {},
            exit_condition=exit_condition or {},
            timeout=timeout,
            retry_policy=retry_policy or {},
        )
        self._pipelines[pipeline.pipeline_id] = pipeline
        self._pipeline_history.setdefault(pipeline.pipeline_id, [])
        return pipeline

    # --------------- Contract Management ---------------

    def create_contract(
        self,
        source_module: str,
        target_module: str,
        data_schema: Optional[Dict[str, Any]] = None,
        validation_rules: Optional[List[Dict[str, Any]]] = None,
        fallback_behavior: Optional[Dict[str, Any]] = None,
        rate_limit: float = 0.0,
        circuit_breaker_threshold: int = 5,
    ) -> ModuleContract:
        contract = ModuleContract(
            source_module=source_module,
            target_module=target_module,
            data_schema=data_schema or {},
            validation_rules=validation_rules or [],
            fallback_behavior=fallback_behavior or {},
            rate_limit=rate_limit,
            circuit_breaker_threshold=circuit_breaker_threshold,
        )
        self._contracts[contract.contract_id] = contract
        breaker = CircuitBreaker(
            contract_id=contract.contract_id,
            failure_threshold=circuit_breaker_threshold,
        )
        self._breakers[contract.contract_id] = breaker
        return contract

    # --------------- Pipeline Execution ---------------

    def execute_pipeline(
        self,
        pipeline_id: str,
        input_context: Optional[Dict[str, Any]] = None,
        priority: str = "medium",
    ) -> OrchestrationTask:
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            raise ValueError(f"Pipeline not found: {pipeline_id}")

        task = OrchestrationTask(
            name=pipeline.name,
            description=f"Execution of pipeline: {pipeline.name}",
            pipeline_id=pipeline_id,
            input_context=input_context or {},
            priority=TaskPriority(priority),
            assigned_modules=list(pipeline.module_sequence),
            status=PipelineStatus.IN_PROGRESS,
            progress=0.0,
            start_time=_time_module.time(),
        )
        self._tasks[task.task_id] = task

        step_count = len(pipeline.module_sequence)
        for idx, module_name in enumerate(pipeline.module_sequence):
            task.progress = (idx + 1) / max(step_count, 1)
            module_reg = self._find_module_by_name(module_name)
            if module_reg is None:
                task.error_log.append(
                    f"Module '{module_name}' not found in pipeline execution"
                )
                task.status = PipelineStatus.FAILED
                task.end_time = _time_module.time()
                self._total_failed_tasks += 1
                break

            contract_id = self._find_contract_for_modules(
                pipeline.module_sequence[max(0, idx - 1)] if idx > 0 else "",
                module_name,
            )
            if contract_id and not self._allow_call(contract_id):
                task.error_log.append(
                    f"Circuit breaker open for contract {contract_id} "
                    f"({pipeline.module_sequence[max(0, idx - 1)] if idx > 0 else 'entry'} -> {module_name})"
                )
                task.status = PipelineStatus.FAILED
                task.end_time = _time_module.time()
                self._total_failed_tasks += 1
                break

            _time_module.sleep(0.005)

            module_reg.status = ModuleStatus.RUNNING
            module_reg.active_task_ids.add(task.task_id)

            simulated = self._simulate_module_execution(module_name, task.input_context)
            task.output_context[module_name] = simulated

            module_reg.status = ModuleStatus.IDLE
            module_reg.total_tasks_completed += 1
            module_reg.total_execution_time += simulated.get("duration", 0.01)

            self._record_interaction(
                source=(pipeline.module_sequence[max(0, idx - 1)] if idx > 0 else "entry"),
                target=module_name,
                pipeline_id=pipeline_id,
                task_id=task.task_id,
            )

        if task.status != PipelineStatus.FAILED:
            task.status = PipelineStatus.COMPLETED
            task.progress = 1.0
            task.end_time = _time_module.time()
            pipeline.execution_count += 1
            pipeline.success_count += 1
            if task.start_time is not None and task.end_time is not None:
                duration = task.end_time - task.start_time
                prev_total = pipeline.avg_duration * (pipeline.execution_count - 1)
                pipeline.avg_duration = (prev_total + duration) / max(pipeline.execution_count, 1)
                self._total_execution_time += duration
            pipeline.last_execution = _time_module.time()
            self._total_completed_tasks += 1

        self._total_executions += 1
        self._pipeline_history[pipeline_id].append(task)
        return task

    # --------------- Pipeline Control ---------------

    def pause_pipeline(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None or task.status != PipelineStatus.IN_PROGRESS:
            return False
        task.status = PipelineStatus.PAUSED
        return True

    def resume_pipeline(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None or task.status != PipelineStatus.PAUSED:
            return False
        task.status = PipelineStatus.IN_PROGRESS
        return True

    def cancel_pipeline(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        if task.status in (PipelineStatus.COMPLETED, PipelineStatus.CANCELLED):
            return False
        task.status = PipelineStatus.CANCELLED
        task.end_time = _time_module.time()
        return True

    def retry_pipeline(self, task_id: str) -> OrchestrationTask:
        task = self._tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        if task.status not in (PipelineStatus.FAILED, PipelineStatus.PARTIALLY_COMPLETED):
            raise ValueError(
                f"Task {task_id} has status {task.status.value}, "
                f"expected FAILED or PARTIALLY_COMPLETED"
            )

        return self.execute_pipeline(
            pipeline_id=task.pipeline_id,
            input_context=task.input_context,
            priority=task.priority.value,
        )

    # --------------- Task Status and Results ---------------

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        task = self._tasks.get(task_id)
        if task is None:
            return {"error": "Task not found", "task_id": task_id}
        return task.to_dict()

    def get_pipeline_results(self, task_id: str) -> Dict[str, Any]:
        task = self._tasks.get(task_id)
        if task is None:
            return {"error": "Task not found", "task_id": task_id}
        pipeline = self._pipelines.get(task.pipeline_id)
        return {
            "task_id": task.task_id,
            "pipeline_name": pipeline.name if pipeline else "unknown",
            "status": task.status.value,
            "input_context": task.input_context,
            "output_context": task.output_context,
            "progress": task.progress,
            "duration": (
                (task.end_time - task.start_time)
                if task.end_time and task.start_time
                else None
            ),
            "error_log": task.error_log,
            "retry_count": task.retry_count,
        }

    # --------------- Health Monitoring ---------------

    def check_module_health(self, module_name: str) -> ModuleHealthReport:
        reg = self._find_module_by_name(module_name)
        if reg is None:
            return ModuleHealthReport(
                module_name=module_name,
                status=ModuleStatus.OFFLINE,
                warnings=[f"Module '{module_name}' is not registered"],
            )

        cpus = 0.5 + hash(module_name + "cpu") % 50 / 100.0
        mem = 30.0 + hash(module_name + "mem") % 40
        active = len(reg.active_task_ids)
        total_ops = max(reg.total_tasks_completed + reg.total_tasks_failed, 1)
        err_rate = reg.total_tasks_failed / total_ops
        avg_resp = (
            reg.total_execution_time / max(reg.total_tasks_completed, 1)
            if reg.total_tasks_completed > 0
            else 0.005
        )

        dep_status: Dict[str, str] = {}
        warnings: List[str] = []
        for dep in reg.dependencies:
            dep_reg = self._find_module_by_name(dep)
            if dep_reg is None:
                dep_status[dep] = "unknown"
                warnings.append(f"Dependency '{dep}' is not registered")
            else:
                dep_status[dep] = dep_reg.status.value
                if dep_reg.status == ModuleStatus.OFFLINE:
                    warnings.append(f"Dependency '{dep}' is OFFLINE")
                elif dep_reg.status == ModuleStatus.ERROR:
                    warnings.append(f"Dependency '{dep}' is in ERROR state")

        if reg.status == ModuleStatus.ERROR:
            warnings.append(f"Module '{module_name}' is in ERROR state")

        return ModuleHealthReport(
            module_name=module_name,
            status=reg.status,
            cpu_usage=cpus,
            memory_usage=mem,
            active_tasks=active,
            error_rate=err_rate,
            avg_response_time=avg_resp,
            last_heartbeat=_time_module.time(),
            dependencies_status=dep_status,
            warnings=warnings,
        )

    def check_all_health(self) -> List[ModuleHealthReport]:
        reports: List[ModuleHealthReport] = []
        for reg in self._modules.values():
            reports.append(self.check_module_health(reg.module_name))
        return reports

    # --------------- Circuit Breaker ---------------

    def get_circuit_breaker_state(self, contract_id: str) -> CircuitBreaker:
        breaker = self._breakers.get(contract_id)
        if breaker is None:
            breaker = CircuitBreaker(contract_id=contract_id)
            self._breakers[contract_id] = breaker
        return breaker

    def _allow_call(self, contract_id: str) -> bool:
        breaker = self._breakers.get(contract_id)
        if breaker is None:
            return True
        if breaker.state == BreakerState.CLOSED:
            return True
        if breaker.state == BreakerState.OPEN:
            elapsed = _time_module.time() - breaker.last_failure
            if elapsed >= breaker.recovery_time:
                breaker.state = BreakerState.HALF_OPEN
                breaker.consecutive_successes = 0
                return True
            return False
        return True

    def _record_call_success(self, contract_id: str) -> None:
        breaker = self._breakers.get(contract_id)
        if breaker is None:
            return
        breaker.last_success = _time_module.time()
        breaker.consecutive_successes += 1
        if breaker.state == BreakerState.HALF_OPEN and breaker.consecutive_successes >= 3:
            breaker.state = BreakerState.CLOSED
            breaker.failure_count = 0

    def _record_call_failure(self, contract_id: str) -> None:
        breaker = self._breakers.get(contract_id)
        if breaker is None:
            return
        breaker.failure_count += 1
        breaker.last_failure = _time_module.time()
        if breaker.failure_count >= breaker.failure_threshold:
            breaker.state = BreakerState.OPEN
            self._total_circuit_trips += 1

    # --------------- Cascading Failure Resolution ---------------

    def resolve_cascading_failure(self, source_module: str) -> Dict[str, Any]:
        affected: List[str] = []
        recovery_actions: List[str] = []

        for reg in self._modules.values():
            if source_module in reg.dependencies:
                affected.append(reg.module_name)

        for pipeline in self._pipelines.values():
            if source_module in pipeline.module_sequence:
                idx = pipeline.module_sequence.index(source_module)
                for downstream in pipeline.module_sequence[idx + 1:]:
                    if downstream not in affected:
                        affected.append(downstream)

        if affected:
            recovery_actions.append(
                f"Pause all pipelines containing '{source_module}' and its "
                f"{len(affected)} downstream modules"
            )
            recovery_actions.append(
                f"Check circuit breakers for contracts involving '{source_module}'"
            )
            recovery_actions.append(
                f"Restart '{source_module}' and verify health before resuming pipelines"
            )
            recovery_actions.append(
                f"Replay queued tasks that were blocked by '{source_module}' failure"
            )
        else:
            recovery_actions.append(
                f"No downstream modules depend on '{source_module}'"
            )

        estimated_recovery = max(10.0, len(affected) * 5.0)

        return {
            "source_module": source_module,
            "affected_modules": affected,
            "affected_count": len(affected),
            "recovery_actions": recovery_actions,
            "estimated_recovery_time": estimated_recovery,
        }

    # --------------- Pipeline Optimization ---------------

    def optimize_pipeline_sequence(self, pipeline_id: str) -> Dict[str, Any]:
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            return {"error": "Pipeline not found"}

        original = list(pipeline.module_sequence)

        scored: List[Tuple[str, float]] = []
        for module_name in pipeline.module_sequence:
            reg = self._find_module_by_name(module_name)
            score = 1.0
            if reg:
                total_calls = max(reg.total_tasks_completed + reg.total_tasks_failed, 1)
                error_rate = reg.total_tasks_failed / total_calls
                avg_time = (
                    reg.total_execution_time / max(reg.total_tasks_completed, 1)
                    if reg.total_tasks_completed > 0
                    else 0.01
                )
                score = (1.0 - error_rate) / max(avg_time, 0.001)
            scored.append((module_name, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        dependency_order: List[str] = []
        remaining = set(pipeline.module_sequence)
        dep_graph: Dict[str, Set[str]] = {
            m: set(reg.dependencies) & remaining
            for m, reg in ((m, self._find_module_by_name(m)) for m in pipeline.module_sequence)
            if reg
        }

        while remaining:
            ready = [m for m in remaining if not (dep_graph.get(m, set()) & remaining)]
            if not ready:
                dependency_order.extend(sorted(remaining))
                break
            for m in ready:
                remaining.discard(m)
                dependency_order.append(m)

        improved = False
        if dependency_order != original:
            improved = True

        orig_efficiency = self._estimate_sequence_efficiency(original)
        opt_efficiency = self._estimate_sequence_efficiency(dependency_order)
        improvement_pct = (
            ((opt_efficiency - orig_efficiency) / max(orig_efficiency, 0.001)) * 100
            if improved
            else 0.0
        )

        return {
            "pipeline_id": pipeline_id,
            "original_sequence": original,
            "optimized_sequence": dependency_order,
            "was_improved": improved,
            "original_efficiency": round(orig_efficiency, 4),
            "optimized_efficiency": round(opt_efficiency, 4),
            "estimated_improvement": round(improvement_pct, 2),
        }

    def _estimate_sequence_efficiency(self, sequence: List[str]) -> float:
        total = 0.0
        for module_name in sequence:
            reg = self._find_module_by_name(module_name)
            if reg and reg.total_tasks_completed > 0:
                avg_time = reg.total_execution_time / reg.total_tasks_completed
                total += 1.0 / max(avg_time, 0.001)
            else:
                total += 1.0
        return total / max(len(sequence), 1)

    # --------------- Dependency Graph ---------------

    def get_dependency_graph(self) -> Dict[str, Any]:
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        for mid, reg in self._modules.items():
            nodes.append({
                "id": mid,
                "name": reg.module_name,
                "type": reg.module_type,
                "status": reg.status.value,
                "capabilities": reg.capabilities,
            })

        for mid, reg in self._modules.items():
            for dep_name in reg.dependencies:
                dep_reg = self._find_module_by_name(dep_name)
                if dep_reg:
                    dep_id = ""
                    for dmid, dmreg in self._modules.items():
                        if dmreg.module_name == dep_name:
                            dep_id = dmid
                            break
                    if dep_id:
                        edges.append({
                            "source": mid,
                            "target": dep_id,
                            "source_name": reg.module_name,
                            "target_name": dep_name,
                        })

        return {
            "nodes": nodes,
            "edges": edges,
        }

    # --------------- Orchestration Statistics ---------------

    def get_orchestration_stats(self) -> Dict[str, Any]:
        active_pipeline_count = sum(
            1 for t in self._tasks.values()
            if t.status == PipelineStatus.IN_PROGRESS
        )
        avg_exec_time = (
            self._total_execution_time / max(self._total_completed_tasks, 1)
            if self._total_completed_tasks > 0
            else 0.0
        )

        return {
            "registered_modules": len(self._modules),
            "active_pipelines": active_pipeline_count,
            "completed_tasks": self._total_completed_tasks,
            "failed_tasks": self._total_failed_tasks,
            "total_executions": self._total_executions,
            "avg_execution_time": round(avg_exec_time, 4),
            "circuit_breaker_trips": self._total_circuit_trips,
            "cross_module_calls": len(self._cross_module_calls),
            "defined_pipelines": len(self._pipelines),
            "defined_contracts": len(self._contracts),
            "active_breakers": sum(
                1 for b in self._breakers.values() if b.state != BreakerState.CLOSED
            ),
        }

    # --------------- Module Interactions ---------------

    def get_module_interactions(
        self, module_name: str, time_window: float = 3600.0
    ) -> List[Dict[str, Any]]:
        now = _time_module.time()
        cutoff = now - time_window

        interactions: List[Dict[str, Any]] = []
        for record in self._interaction_records:
            if record.get("timestamp", 0) < cutoff:
                continue
            if record.get("source") == module_name or record.get("target") == module_name:
                interactions.append({
                    "source": record.get("source", ""),
                    "target": record.get("target", ""),
                    "pipeline_id": record.get("pipeline_id", ""),
                    "task_id": record.get("task_id", ""),
                    "timestamp": record.get("timestamp", 0),
                    "direction": (
                        "outbound" if record.get("source") == module_name else "inbound"
                    ),
                })

        return interactions

    def _record_interaction(
        self, source: str, target: str, pipeline_id: str, task_id: str
    ) -> None:
        record = {
            "source": source,
            "target": target,
            "pipeline_id": pipeline_id,
            "task_id": task_id,
            "timestamp": _time_module.time(),
        }
        self._interaction_records.append(record)
        self._cross_module_calls.append(record)

    # --------------- Pipeline Improvement Suggestions ---------------

    def suggest_pipeline_improvements(self) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []

        for pipeline in self._pipelines.values():
            if pipeline.execution_count >= 5 and pipeline.avg_duration > pipeline.timeout * 0.8:
                suggestions.append({
                    "pipeline_id": pipeline.pipeline_id,
                    "pipeline_name": pipeline.name,
                    "type": "timeout_approaching",
                    "description": (
                        f"Pipeline '{pipeline.name}' avg duration "
                        f"({pipeline.avg_duration:.2f}s) is near timeout "
                        f"({pipeline.timeout:.2f}s). Consider increasing timeout."
                    ),
                    "recommended_action": "increase_timeout",
                    "current_value": pipeline.timeout,
                    "suggested_value": pipeline.avg_duration * 1.5,
                })

            if pipeline.execution_count >= 10 and (
                pipeline.execution_count > 0
                and pipeline.success_count / pipeline.execution_count < 0.7
            ):
                suggestions.append({
                    "pipeline_id": pipeline.pipeline_id,
                    "pipeline_name": pipeline.name,
                    "type": "low_success_rate",
                    "description": (
                        f"Pipeline '{pipeline.name}' has low success rate "
                        f"({pipeline.success_count}/{pipeline.execution_count}). "
                        f"Check module health and circuit breakers."
                    ),
                    "recommended_action": "investigate_modules",
                    "current_value": (
                        pipeline.success_count / pipeline.execution_count
                        if pipeline.execution_count > 0
                        else 0
                    ),
                })

            for module_name in pipeline.module_sequence:
                reg = self._find_module_by_name(module_name)
                if reg and reg.total_tasks_completed + reg.total_tasks_failed >= 20:
                    total_ops = max(reg.total_tasks_completed + reg.total_tasks_failed, 1)
                    err_rate = reg.total_tasks_failed / total_ops
                    if err_rate > 0.3:
                        suggestions.append({
                            "pipeline_id": pipeline.pipeline_id,
                            "pipeline_name": pipeline.name,
                            "type": "high_module_error_rate",
                            "description": (
                                f"Module '{module_name}' in pipeline '{pipeline.name}' "
                                f"has high error rate ({err_rate:.2f}). Consider adding "
                                f"a fallback module or adjusting retry policy."
                            ),
                            "recommended_action": "add_fallback_or_retry",
                            "module_name": module_name,
                            "error_rate": round(err_rate, 4),
                        })

        return suggestions

    # --------------- Reset ---------------

    def reset(self) -> None:
        self._modules.clear()
        self._pipelines.clear()
        self._contracts.clear()
        self._tasks.clear()
        self._breakers.clear()
        self._pipeline_history.clear()
        self._cross_module_calls.clear()
        self._interaction_records.clear()
        self._total_circuit_trips = 0
        self._total_completed_tasks = 0
        self._total_failed_tasks = 0
        self._total_executions = 0
        self._total_execution_time = 0.0

    # --------------- Internal Helpers ---------------

    def _find_module_by_name(self, module_name: str) -> Optional[_ModuleRegistration]:
        for reg in self._modules.values():
            if reg.module_name == module_name:
                return reg
        return None

    def _find_contract_for_modules(
        self, source_module: str, target_module: str
    ) -> Optional[str]:
        for contract in self._contracts.values():
            if contract.source_module == source_module and contract.target_module == target_module:
                return contract.contract_id
        return None

    def _simulate_module_execution(
        self, module_name: str, input_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        base_hash = hash(module_name + str(input_context))
        duration = 0.01 + (abs(base_hash) % 100) / 1000.0
        return {
            "module": module_name,
            "success": True,
            "output": f"Processed by {module_name}",
            "duration": duration,
            "metadata": {
                "confidence": 0.7 + (abs(base_hash) % 30) / 100.0,
                "tokens_consumed": abs(base_hash) % 500,
            },
        }


def get_cross_module_orchestrator() -> AgentCrossModuleOrchestrator:
    return AgentCrossModuleOrchestrator.get_instance()