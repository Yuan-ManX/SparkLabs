"""
SparkLabs Agent - Delegation Framework

A flat delegation system where a parent agent spawns isolated child
agents with restricted toolsets and clean contexts. Children execute
sub-tasks independently and return only summarized results to the parent.

Architecture:
  DelegationFramework
    |-- ChildAgent (isolated worker with restricted tool access)
    |-- DelegationTask (sub-task dispatched to a child)
    |-- DelegationResult (summarized output from child execution)
    |-- DelegationPool (managed collection of children with scheduling)

Delegation Strategies:
  - ROUND_ROBIN: cycle through available children evenly
  - FIRST_AVAILABLE: assign to the first idle child found
  - CAPABILITY_MATCH: match task to child by capability set
  - LOAD_BALANCED: assign to child with least active tasks
  - PRIORITY_QUEUE: critical tasks preempt lower-priority work

Isolation Levels:
  - FULL: no shared context, only result returned to parent
  - TOOL_RESTRICTED: child has limited tool access only
  - CONTEXT_SHARED: child can read parent context
  - READ_ONLY: child can read but not modify parent state

Usage:
    df = DelegationFramework()
    child = df.register_child("code_auditor", ChildRole.SPECIALIST,
                              capabilities=["code_review", "linting"],
                              allowed_tools=["read_file", "search"],
                              blocked_tools=["write_file", "delete_file"],
                              isolation=IsolationLevel.TOOL_RESTRICTED)
    pool = df.create_pool("audit_pool", [child.id],
                          strategy=DelegationStrategy.FIRST_AVAILABLE,
                          max_concurrent=3)
    task = df.delegate_task(pool.id, parent_session_id,
                            "Audit all TypeScript files for security issues",
                            {"priority": "high"})
    result = df.get_child_result(task.id)
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

_time_module = time


class ChildRole(Enum):
    WORKER = "worker"
    SPECIALIST = "specialist"
    ORCHESTRATOR = "orchestrator"
    OBSERVER = "observer"


class ChildStatus(Enum):
    IDLE = "idle"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class DelegationStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    FIRST_AVAILABLE = "first_available"
    CAPABILITY_MATCH = "capability_match"
    LOAD_BALANCED = "load_balanced"
    PRIORITY_QUEUE = "priority_queue"


class IsolationLevel(Enum):
    FULL = "full"
    TOOL_RESTRICTED = "tool_restricted"
    CONTEXT_SHARED = "context_shared"
    READ_ONLY = "read_only"


_STRATEGY_RANK = {
    DelegationStrategy.ROUND_ROBIN: 0,
    DelegationStrategy.FIRST_AVAILABLE: 1,
    DelegationStrategy.CAPABILITY_MATCH: 2,
    DelegationStrategy.LOAD_BALANCED: 3,
    DelegationStrategy.PRIORITY_QUEUE: 4,
}

_ISOLATION_SEVERITY = {
    IsolationLevel.FULL: 3,
    IsolationLevel.TOOL_RESTRICTED: 2,
    IsolationLevel.CONTEXT_SHARED: 1,
    IsolationLevel.READ_ONLY: 0,
}


@dataclass
class ChildAgent:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    role: ChildRole = ChildRole.WORKER
    capabilities: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    blocked_tools: List[str] = field(default_factory=list)
    isolation: IsolationLevel = IsolationLevel.FULL
    max_iterations: int = 20
    timeout_seconds: float = 300.0
    status: ChildStatus = ChildStatus.IDLE
    stats: Dict[str, Any] = field(default_factory=lambda: {
        "tasks_completed": 0,
        "tasks_failed": 0,
        "total_duration_ms": 0.0,
        "peak_active_tasks": 0,
        "last_active_at": None,
    })
    created_at: float = field(default_factory=_time_module.time)

    @property
    def is_available(self) -> bool:
        return self.status == ChildStatus.IDLE

    @property
    def success_rate(self) -> float:
        total = self.stats["tasks_completed"] + self.stats["tasks_failed"]
        if total == 0:
            return 1.0
        return self.stats["tasks_completed"] / total

    @property
    def avg_duration_ms(self) -> float:
        completed = self.stats["tasks_completed"]
        if completed == 0:
            return 0.0
        return self.stats["total_duration_ms"] / completed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "capabilities": self.capabilities,
            "allowed_tools": self.allowed_tools,
            "blocked_tools": self.blocked_tools,
            "isolation": self.isolation.value,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "status": self.status.value,
            "stats": self.stats,
            "success_rate": round(self.success_rate, 3),
            "avg_duration_ms": round(self.avg_duration_ms, 1),
            "is_available": self.is_available,
            "created_at": self.created_at,
        }

    def record_completion(self, duration_ms: float) -> None:
        self.stats["tasks_completed"] += 1
        self.stats["total_duration_ms"] += duration_ms
        self.stats["last_active_at"] = _time_module.time()

    def record_failure(self) -> None:
        self.stats["tasks_failed"] += 1
        self.stats["last_active_at"] = _time_module.time()


@dataclass
class DelegationTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    parent_session_id: str = ""
    description: str = ""
    assigned_child_id: Optional[str] = None
    status: ChildStatus = ChildStatus.IDLE
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result_summary: str = ""
    error: Optional[str] = None
    turn_count: int = 0
    max_turns: int = 30
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

    @property
    def is_active(self) -> bool:
        return self.status in (ChildStatus.DISPATCHED, ChildStatus.RUNNING)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_session_id": self.parent_session_id,
            "description": self.description[:200],
            "assigned_child_id": self.assigned_child_id,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": round(self.duration_seconds, 3),
            "result_summary": self.result_summary[:200],
            "error": self.error[:200] if self.error else None,
            "turn_count": self.turn_count,
            "max_turns": self.max_turns,
            "priority": self.priority,
            "metadata": self.metadata,
        }

    def mark_dispatched(self, child_id: str) -> None:
        self.assigned_child_id = child_id
        self.status = ChildStatus.DISPATCHED
        self.start_time = _time_module.time()

    def mark_running(self) -> None:
        self.status = ChildStatus.RUNNING
        self.turn_count += 1

    def mark_completed(self, summary: str) -> None:
        self.status = ChildStatus.COMPLETED
        self.end_time = _time_module.time()
        self.result_summary = summary

    def mark_failed(self, error_msg: str) -> None:
        self.status = ChildStatus.FAILED
        self.end_time = _time_module.time()
        self.error = error_msg

    def mark_timeout(self) -> None:
        self.status = ChildStatus.TIMEOUT
        self.end_time = _time_module.time()
        self.error = "Task exceeded maximum execution duration"

    def mark_cancelled(self) -> None:
        self.status = ChildStatus.CANCELLED
        self.end_time = _time_module.time()
        self.error = "Task was cancelled by parent"


@dataclass
class DelegationResult:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    task_id: str = ""
    child_id: str = ""
    success: bool = False
    summary: str = ""
    artifacts: Dict[str, Any] = field(default_factory=dict)
    error_details: Optional[str] = None
    duration_ms: float = 0.0
    token_usage: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "child_id": self.child_id,
            "success": self.success,
            "summary": self.summary[:500],
            "artifacts": self.artifacts,
            "error_details": self.error_details[:300] if self.error_details else None,
            "duration_ms": round(self.duration_ms, 2),
            "token_usage": self.token_usage,
            "created_at": self.created_at,
        }


@dataclass
class DelegationPool:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    children: Dict[str, ChildAgent] = field(default_factory=dict)
    strategy: DelegationStrategy = DelegationStrategy.ROUND_ROBIN
    max_concurrent: int = 5
    active_tasks: Dict[str, DelegationTask] = field(default_factory=dict)
    queue: deque = field(default_factory=deque)
    stats: Dict[str, Any] = field(default_factory=lambda: {
        "total_delegated": 0,
        "total_completed": 0,
        "total_failed": 0,
        "total_timeouts": 0,
        "total_cancelled": 0,
    })
    created_at: float = field(default_factory=_time_module.time)
    paused: bool = False

    @property
    def idle_child_count(self) -> int:
        return sum(1 for c in self.children.values() if c.is_available)

    @property
    def total_child_count(self) -> int:
        return len(self.children)

    @property
    def queue_depth(self) -> int:
        return len(self.queue)

    @property
    def load_factor(self) -> float:
        if self.total_child_count == 0:
            return 0.0
        return len(self.active_tasks) / (self.total_child_count * self.max_concurrent)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "children": {cid: c.to_dict() for cid, c in self.children.items()},
            "strategy": self.strategy.value,
            "max_concurrent": self.max_concurrent,
            "active_tasks": len(self.active_tasks),
            "queue_depth": self.queue_depth,
            "idle_children": self.idle_child_count,
            "total_children": self.total_child_count,
            "load_factor": round(self.load_factor, 3),
            "stats": self.stats,
            "paused": self.paused,
            "created_at": self.created_at,
        }

    def _select_child(self, task: DelegationTask) -> Optional[str]:
        available = [
            cid for cid, c in self.children.items()
            if c.is_available and cid not in self.active_tasks
        ]
        if not available:
            return None

        if self.strategy == DelegationStrategy.FIRST_AVAILABLE:
            return available[0]

        elif self.strategy == DelegationStrategy.ROUND_ROBIN:
            sorted_children = sorted(available, key=lambda cid: (
                self.children[cid].stats["last_active_at"] or 0
            ))
            return sorted_children[0] if sorted_children else None

        elif self.strategy == DelegationStrategy.CAPABILITY_MATCH:
            best_id = None
            best_score = -1
            task_words = set(task.description.lower().split())
            for cid in available:
                child = self.children[cid]
                cap_words = set(" ".join(child.capabilities).lower().split())
                if not cap_words:
                    continue
                overlap = len(task_words & cap_words)
                if overlap > best_score:
                    best_score = overlap
                    best_id = cid
            return best_id or (available[0] if available else None)

        elif self.strategy == DelegationStrategy.LOAD_BALANCED:
            return min(
                available,
                key=lambda cid: self.children[cid].stats["tasks_completed"] + self.children[cid].stats["tasks_failed"],
            )

        elif self.strategy == DelegationStrategy.PRIORITY_QUEUE:
            available_sorted = sorted(
                available,
                key=lambda cid: (
                    self.children[cid].success_rate,
                    self.children[cid].stats["tasks_completed"],
                ),
                reverse=True,
            )
            return available_sorted[0] if available_sorted else None

        return None


class DelegationFramework:
    """
    Flat delegation system managing isolated child agents with restricted
    toolsets and clean execution contexts. Parent agents spawn children
    that execute independently and return summarized results.
    """

    _instance: Optional["DelegationFramework"] = None

    MAX_CHILDREN_PER_POOL = 50
    MAX_POOLS = 100
    MAX_TASKS_PER_POOL = 200
    MAX_RESULT_CACHE = 500

    def __init__(self):
        self._children: Dict[str, ChildAgent] = {}
        self._pools: Dict[str, DelegationPool] = {}
        self._tasks: Dict[str, DelegationTask] = {}
        self._results: Dict[str, DelegationResult] = {}
        self._lock = threading.RLock()
        self._global_stats = {
            "total_children_registered": 0,
            "total_pools_created": 0,
            "total_tasks_delegated": 0,
            "total_tasks_completed": 0,
            "total_tasks_failed": 0,
            "total_tasks_timeout": 0,
            "total_tasks_cancelled": 0,
        }

    @classmethod
    def get_instance(cls) -> "DelegationFramework":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_child(
        self,
        name: str,
        role: str = "worker",
        capabilities: Optional[List[str]] = None,
        allowed_tools: Optional[List[str]] = None,
        blocked_tools: Optional[List[str]] = None,
        isolation: str = "full",
        max_iterations: int = 20,
        timeout_seconds: float = 300.0,
    ) -> ChildAgent:
        role_enum = ChildRole(role) if role in [r.value for r in ChildRole] else ChildRole.WORKER
        isolation_enum = IsolationLevel(isolation) if isolation in [i.value for i in IsolationLevel] else IsolationLevel.FULL

        child = ChildAgent(
            name=name,
            role=role_enum,
            capabilities=capabilities or [],
            allowed_tools=allowed_tools or [],
            blocked_tools=blocked_tools or [],
            isolation=isolation_enum,
            max_iterations=max_iterations,
            timeout_seconds=timeout_seconds,
        )

        with self._lock:
            self._children[child.id] = child
            self._global_stats["total_children_registered"] += 1

        return child

    def create_pool(
        self,
        name: str,
        child_ids: List[str],
        strategy: str = "round_robin",
        max_concurrent: int = 5,
    ) -> Optional[DelegationPool]:
        strategy_enum = DelegationStrategy(strategy) if strategy in [s.value for s in DelegationStrategy] else DelegationStrategy.ROUND_ROBIN

        with self._lock:
            if len(self._pools) >= self.MAX_POOLS:
                return None

            pool_children: Dict[str, ChildAgent] = {}
            for cid in child_ids:
                child = self._children.get(cid)
                if child is None:
                    continue
                if len(pool_children) >= self.MAX_CHILDREN_PER_POOL:
                    break
                pool_children[cid] = child

            if not pool_children:
                return None

            pool = DelegationPool(
                name=name,
                children=pool_children,
                strategy=strategy_enum,
                max_concurrent=max(1, min(max_concurrent, len(pool_children))),
            )

            self._pools[pool.id] = pool
            self._global_stats["total_pools_created"] += 1

        return pool

    def delegate_task(
        self,
        pool_id: str,
        parent_session_id: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        priority: int = 0,
    ) -> Optional[DelegationTask]:
        with self._lock:
            pool = self._pools.get(pool_id)
            if pool is None:
                return None

            if pool.paused:
                return None

            if len(pool.active_tasks) >= self.MAX_TASKS_PER_POOL:
                return None

            task = DelegationTask(
                parent_session_id=parent_session_id,
                description=description,
                metadata=metadata or {},
                priority=priority,
            )

            active_count = len(pool.active_tasks)
            if active_count < pool.max_concurrent:
                selected = pool._select_child(task)
                if selected:
                    child = pool.children[selected]
                    child.status = ChildStatus.DISPATCHED
                    task.mark_dispatched(selected)
                    pool.active_tasks[task.id] = task
                    pool.stats["total_delegated"] += 1
                else:
                    pool.queue.append(task.id)
                    task.status = ChildStatus.IDLE
            else:
                pool.queue.append(task.id)
                task.status = ChildStatus.IDLE

            self._tasks[task.id] = task
            self._global_stats["total_tasks_delegated"] += 1

        return task

    def get_child_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            result = self._results.get(task_id)
            if result:
                return result.to_dict()

            task = self._tasks.get(task_id)
            if task is None:
                return None

            if task.status == ChildStatus.COMPLETED:
                auto_result = DelegationResult(
                    task_id=task.id,
                    child_id=task.assigned_child_id or "",
                    success=True,
                    summary=task.result_summary,
                    duration_ms=task.duration_seconds * 1000,
                    token_usage=len(task.result_summary) // 4,
                )
                return auto_result.to_dict()

            if task.status in (ChildStatus.FAILED, ChildStatus.TIMEOUT, ChildStatus.CANCELLED):
                auto_result = DelegationResult(
                    task_id=task.id,
                    child_id=task.assigned_child_id or "",
                    success=False,
                    error_details=task.error or "Task did not complete successfully",
                    duration_ms=task.duration_seconds * 1000,
                )
                return auto_result.to_dict()

            return None

    def cancel_delegation(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False

            if task.status in (ChildStatus.COMPLETED, ChildStatus.FAILED,
                               ChildStatus.TIMEOUT, ChildStatus.CANCELLED):
                return False

            task.mark_cancelled()
            self._global_stats["total_tasks_cancelled"] += 1

            if task.assigned_child_id:
                pool = self._find_pool_for_task(task_id)
                if pool:
                    if task.id in pool.active_tasks:
                        del pool.active_tasks[task.id]
                        pool.stats["total_cancelled"] += 1

                    child = pool.children.get(task.assigned_child_id)
                    if child and child.status in (ChildStatus.DISPATCHED, ChildStatus.RUNNING):
                        child.status = ChildStatus.IDLE

                    self._drain_pool_queue(pool)

            return True

    def _find_pool_for_task(self, task_id: str) -> Optional[DelegationPool]:
        for pool in self._pools.values():
            if task_id in pool.active_tasks:
                return pool
            if task_id in pool.queue:
                return pool
        return None

    def get_pool_status(self, pool_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            pool = self._pools.get(pool_id)
            if pool is None:
                return None
            return pool.to_dict()

    def pause_pool(self, pool_id: str) -> bool:
        with self._lock:
            pool = self._pools.get(pool_id)
            if pool is None:
                return False
            pool.paused = True
            return True

    def resume_pool(self, pool_id: str) -> bool:
        with self._lock:
            pool = self._pools.get(pool_id)
            if pool is None:
                return False
            pool.paused = False
            self._drain_pool_queue(pool)
            return True

    def reassign_task(self, task_id: str, new_child_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False

            if task.status not in (ChildStatus.DISPATCHED, ChildStatus.RUNNING):
                return False

            pool = self._find_pool_for_task(task_id)
            if pool is None:
                return False

            new_child = pool.children.get(new_child_id)
            if new_child is None:
                return False

            if not new_child.is_available:
                return False

            old_child_id = task.assigned_child_id
            if old_child_id and old_child_id in pool.children:
                old_child = pool.children[old_child_id]
                old_child.status = ChildStatus.IDLE

            task.assigned_child_id = new_child_id
            new_child.status = ChildStatus.DISPATCHED
            task.start_time = _time_module.time()
            return True

    def get_framework_stats(self) -> Dict[str, Any]:
        with self._lock:
            pool_stats = []
            for pool in self._pools.values():
                pool_stats.append({
                    "pool_id": pool.id,
                    "pool_name": pool.name,
                    "idle_children": pool.idle_child_count,
                    "total_children": pool.total_child_count,
                    "active_tasks": len(pool.active_tasks),
                    "queue_depth": pool.queue_depth,
                    "paused": pool.paused,
                    "strategy": pool.strategy.value,
                    "stats": pool.stats,
                })

            return {
                "global": self._global_stats,
                "active_children": sum(1 for c in self._children.values() if not c.is_available),
                "total_children": len(self._children),
                "total_pools": len(self._pools),
                "cached_results": len(self._results),
                "pools": pool_stats,
            }

    def update_child_capabilities(
        self,
        child_id: str,
        capabilities: List[str],
    ) -> bool:
        with self._lock:
            child = self._children.get(child_id)
            if child is None:
                return False
            child.capabilities = capabilities
            return True

    def set_isolation_level(self, child_id: str, level: str) -> bool:
        with self._lock:
            child = self._children.get(child_id)
            if child is None:
                return False
            isolation = IsolationLevel(level) if level in [i.value for i in IsolationLevel] else IsolationLevel.FULL
            child.isolation = isolation
            return True

    def complete_task(
        self,
        task_id: str,
        summary: str = "",
        artifacts: Optional[Dict[str, Any]] = None,
        token_usage: int = 0,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None

            if task.status not in (ChildStatus.DISPATCHED, ChildStatus.RUNNING):
                return None

            task.mark_completed(summary)

            pool = self._find_pool_for_task(task_id)
            if pool and task.assigned_child_id:
                child = pool.children.get(task.assigned_child_id)
                if child:
                    duration_ms = task.duration_seconds * 1000
                    child.record_completion(duration_ms)

                if task.id in pool.active_tasks:
                    del pool.active_tasks[task.id]

                pool.stats["total_completed"] += 1

            self._global_stats["total_tasks_completed"] += 1

            result = DelegationResult(
                task_id=task.id,
                child_id=task.assigned_child_id or "",
                success=True,
                summary=summary,
                artifacts=artifacts or {},
                duration_ms=task.duration_seconds * 1000,
                token_usage=token_usage,
            )
            self._store_result(result)

            if pool:
                self._drain_pool_queue(pool)

            return result.to_dict()

    def fail_task(
        self,
        task_id: str,
        error: str = "",
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None

            if task.status not in (ChildStatus.DISPATCHED, ChildStatus.RUNNING):
                return None

            task.mark_failed(error)

            pool = self._find_pool_for_task(task_id)
            if pool and task.assigned_child_id:
                child = pool.children.get(task.assigned_child_id)
                if child:
                    child.record_failure()

                if task.id in pool.active_tasks:
                    del pool.active_tasks[task.id]

                pool.stats["total_failed"] += 1

            self._global_stats["total_tasks_failed"] += 1

            result = DelegationResult(
                task_id=task.id,
                child_id=task.assigned_child_id or "",
                success=False,
                error_details=error,
                duration_ms=task.duration_seconds * 1000,
            )
            self._store_result(result)

            if pool:
                self._drain_pool_queue(pool)

            return result.to_dict()

    def timeout_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None

            if task.status not in (ChildStatus.DISPATCHED, ChildStatus.RUNNING):
                return None

            task.mark_timeout()

            pool = self._find_pool_for_task(task_id)
            if pool and task.assigned_child_id:
                child = pool.children.get(task.assigned_child_id)
                if child:
                    child.record_failure()

                if task.id in pool.active_tasks:
                    del pool.active_tasks[task.id]

                pool.stats["total_timeouts"] += 1

            self._global_stats["total_tasks_timeout"] += 1

            result = DelegationResult(
                task_id=task.id,
                child_id=task.assigned_child_id or "",
                success=False,
                error_details="Task exceeded maximum execution duration",
                duration_ms=task.duration_seconds * 1000,
            )
            self._store_result(result)

            if pool:
                self._drain_pool_queue(pool)

            return result.to_dict()

    def start_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False

            if task.status != ChildStatus.DISPATCHED:
                return False

            task.mark_running()

            pool = self._find_pool_for_task(task_id)
            if pool and task.assigned_child_id:
                child = pool.children.get(task.assigned_child_id)
                if child:
                    child.status = ChildStatus.RUNNING

            return True

    def _store_result(self, result: DelegationResult) -> None:
        if len(self._results) >= self.MAX_RESULT_CACHE:
            oldest_key = min(self._results.keys(), key=lambda k: self._results[k].created_at)
            del self._results[oldest_key]
        self._results[result.task_id] = result

    def _drain_pool_queue(self, pool: DelegationPool) -> None:
        while pool.queue and len(pool.active_tasks) < pool.max_concurrent:
            next_task_id = pool.queue.popleft()
            task = self._tasks.get(next_task_id)
            if task is None:
                continue

            if task.status not in (ChildStatus.IDLE, ChildStatus.DISPATCHED):
                continue

            selected = pool._select_child(task)
            if selected is None:
                pool.queue.appendleft(next_task_id)
                break

            child = pool.children[selected]
            child.status = ChildStatus.DISPATCHED
            task.mark_dispatched(selected)
            pool.active_tasks[task.id] = task
            pool.stats["total_delegated"] += 1

    def get_child(self, child_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            child = self._children.get(child_id)
            if child:
                return child.to_dict()
            return None

    def list_children(
        self,
        role: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            children = list(self._children.values())
            if role:
                children = [c for c in children if c.role.value == role]
            if status:
                children = [c for c in children if c.status.value == status]
            return [c.to_dict() for c in children]

    def list_pools(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [p.to_dict() for p in self._pools.values()]

    def list_tasks(
        self,
        pool_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            tasks = list(self._tasks.values())
            if pool_id:
                pool = self._pools.get(pool_id)
                if pool:
                    pool_task_ids = set(pool.active_tasks.keys()) | set(pool.queue)
                    tasks = [t for t in tasks if t.id in pool_task_ids]
                else:
                    return []
            if status:
                tasks = [t for t in tasks if t.status.value == status]
            return [t.to_dict() for t in tasks]

    def remove_child(self, child_id: str) -> bool:
        with self._lock:
            child = self._children.get(child_id)
            if child is None:
                return False

            for pool in list(self._pools.values()):
                if child_id in pool.children:
                    orphaned_tasks = [
                        tid for tid, t in pool.active_tasks.items()
                        if t.assigned_child_id == child_id
                    ]
                    for tid in orphaned_tasks:
                        task = self._tasks.get(tid)
                        if task:
                            task.mark_cancelled()
                            self._global_stats["total_tasks_cancelled"] += 1
                        del pool.active_tasks[tid]
                        pool.stats["total_cancelled"] += 1

                    del pool.children[child_id]
                    if not pool.children:
                        del self._pools[pool.id]

            del self._children[child_id]
            return True

    def remove_pool(self, pool_id: str) -> bool:
        with self._lock:
            pool = self._pools.get(pool_id)
            if pool is None:
                return False

            for tid in list(pool.active_tasks.keys()):
                task = self._tasks.get(tid)
                if task:
                    task.mark_cancelled()
                    self._global_stats["total_tasks_cancelled"] += 1
                pool.stats["total_cancelled"] += 1

            for tid in list(pool.queue):
                task = self._tasks.get(tid)
                if task:
                    task.mark_cancelled()
                    self._global_stats["total_tasks_cancelled"] += 1

            pool.active_tasks.clear()
            pool.queue.clear()
            del self._pools[pool_id]
            return True

    def check_timeouts(self) -> List[str]:
        timed_out: List[str] = []
        now = _time_module.time()

        with self._lock:
            for pool in self._pools.values():
                for tid, task in list(pool.active_tasks.items()):
                    if task.status not in (ChildStatus.DISPATCHED, ChildStatus.RUNNING):
                        continue
                    if task.assigned_child_id and task.assigned_child_id in pool.children:
                        child = pool.children[task.assigned_child_id]
                        if task.start_time and (now - task.start_time) > child.timeout_seconds:
                            self.timeout_task(tid)
                            timed_out.append(tid)

        return timed_out

    def cancel_all_pool_tasks(self, pool_id: str) -> int:
        count = 0
        with self._lock:
            pool = self._pools.get(pool_id)
            if pool is None:
                return 0

            for tid in list(pool.active_tasks.keys()):
                self.cancel_delegation(tid)
                count += 1

            for tid in list(pool.queue):
                task = self._tasks.get(tid)
                if task:
                    task.mark_cancelled()
                    self._global_stats["total_tasks_cancelled"] += 1
                    count += 1
                pool.queue.remove(tid)

        return count

    def reset_framework(self) -> None:
        with self._lock:
            for pool in list(self._pools.values()):
                for tid in list(pool.active_tasks.keys()):
                    task = self._tasks.get(tid)
                    if task:
                        task.mark_cancelled()
                pool.active_tasks.clear()
                pool.queue.clear()

            self._children.clear()
            self._pools.clear()
            self._tasks.clear()
            self._results.clear()
            self._global_stats = {
                "total_children_registered": 0,
                "total_pools_created": 0,
                "total_tasks_delegated": 0,
                "total_tasks_completed": 0,
                "total_tasks_failed": 0,
                "total_tasks_timeout": 0,
                "total_tasks_cancelled": 0,
            }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_children": len(self._children),
            "active_tasks": sum(1 for t in self._tasks.values() if t.is_active),
            "completed_tasks": self._global_stats["total_tasks_completed"],
            "pool_count": len(self._pools),
        }


def get_delegation_framework() -> DelegationFramework:
    return DelegationFramework.get_instance()