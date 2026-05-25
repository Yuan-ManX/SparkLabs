"""
SparkLabs Agent - Concurrency Manager

Manages multiple concurrent agent tasks with rate limiting, prioritization,
and queue management. Orchestrates task execution across agent subsystems
with configurable concurrency strategies and throughput monitoring.

Architecture:
  AgentConcurrencyManager
    |-- TaskScheduler (priority-based task dispatch with deadlines)
    |-- RateLimiter (multi-strategy rate limiting for API/resource calls)
    |-- QueueManager (task queue lifecycle and concurrency control)
    |-- StatsCollector (throughput, latency, and queue depth metrics)
    |-- ConcurrencyPolicy (parallel, sequential, pipeline, round-robin)

Concurrency Strategies:
  - PARALLEL: execute tasks concurrently (GPU-style parallelism)
  - SEQUENTIAL: ordered execution with dependency chains
  - PIPELINE: stage-based processing with intermediate queues
  - ROUND_ROBIN: fair distribution across agent queues
  - PRIORITY_QUEUE: critical tasks preempt lower-priority work
"""

from __future__ import annotations

import heapq
import json
import queue as queue_module
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class ConcurrencyStrategy(Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    PIPELINE = "pipeline"
    ROUND_ROBIN = "round_robin"
    PRIORITY_QUEUE = "priority_queue"


class RateLimitType(Enum):
    TOKENS_PER_MINUTE = "tokens_per_minute"
    REQUESTS_PER_SECOND = "requests_per_second"
    CONCURRENT_LIMIT = "concurrent_limit"
    CUSTOM = "custom"


@dataclass
class ConcurrencyTask:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    task_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.QUEUED
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    attempts: int = 0
    max_retries: int = 3
    timeout_seconds: float = 60.0
    result: Any = None
    error_log: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "attempts": self.attempts,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "result": self.result,
            "error_log": self.error_log,
        }


@dataclass
class RateLimit:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    limit_type: RateLimitType = RateLimitType.REQUESTS_PER_SECOND
    max_value: float = 0.0
    current_value: float = 0.0
    reset_interval: float = 1.0
    last_reset: float = field(default_factory=time.time)
    enabled: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "limit_type": self.limit_type.value,
            "max_value": self.max_value,
            "current_value": self.current_value,
            "reset_interval": self.reset_interval,
            "last_reset": self.last_reset,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


@dataclass
class TaskQueue:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    tasks: Dict[str, ConcurrencyTask] = field(default_factory=dict)
    strategy: ConcurrencyStrategy = ConcurrencyStrategy.PARALLEL
    max_concurrent: int = 10
    active_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "task_count": len(self.tasks),
            "strategy": self.strategy.value,
            "max_concurrent": self.max_concurrent,
            "active_count": self.active_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "created_at": self.created_at,
        }


@dataclass
class ConcurrencyStats:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    total_tasks: int = 0
    active_tasks: int = 0
    queued_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    average_latency_ms: float = 0.0
    throughput_per_sec: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "total_tasks": self.total_tasks,
            "active_tasks": self.active_tasks,
            "queued_tasks": self.queued_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "average_latency_ms": self.average_latency_ms,
            "throughput_per_sec": self.throughput_per_sec,
            "created_at": self.created_at,
        }


class AgentConcurrencyManager:
    """Manages concurrent agent task execution with rate limiting and prioritization."""

    _instance: Optional["AgentConcurrencyManager"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "AgentConcurrencyManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._queues: Dict[str, TaskQueue] = {}
        self._rate_limits: Dict[str, RateLimit] = {}
        self._task_registry: Dict[str, ConcurrencyTask] = {}
        self._priority_heap: List[Tuple[int, float, str]] = []
        self._heap_lock = threading.Lock()
        self._total_tasks_enqueued: int = 0
        self._total_tasks_completed: int = 0
        self._total_tasks_failed: int = 0
        self._latency_samples: List[float] = []
        self._throughput_window: List[float] = []
        self._paused_queues: set[str] = set()
        self._initialized: bool = True

    @classmethod
    def get_instance(cls) -> "AgentConcurrencyManager":
        return cls()

    # ---- Queue Management ----

    def create_queue(self,
                     name: str,
                     strategy: str = "parallel",
                     max_concurrent: int = 10) -> TaskQueue:
        try:
            st = ConcurrencyStrategy(strategy.lower())
        except ValueError:
            st = ConcurrencyStrategy.PARALLEL

        tq = TaskQueue(
            name=name,
            strategy=st,
            max_concurrent=max_concurrent,
        )
        self._queues[tq.id] = tq
        return tq

    def get_queue(self, queue_id: str) -> Optional[TaskQueue]:
        return self._queues.get(queue_id)

    def list_queues(self) -> List[TaskQueue]:
        return list(self._queues.values())

    def pause_queue(self, queue_id: str) -> bool:
        if queue_id not in self._queues:
            return False
        self._paused_queues.add(queue_id)
        return True

    def resume_queue(self, queue_id: str) -> bool:
        if queue_id not in self._queues:
            return False
        self._paused_queues.discard(queue_id)
        return True

    def is_paused(self, queue_id: str) -> bool:
        return queue_id in self._paused_queues

    def drain_queue(self, queue_id: str) -> int:
        tq = self._queues.get(queue_id)
        if tq is None:
            return 0

        processed = 0
        for task in list(tq.tasks.values()):
            if task.status == TaskStatus.QUEUED:
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                task.attempts += 1
                task.completed_at = time.time()
                task.status = TaskStatus.COMPLETED
                task.result = {"drained": True, "timestamp": task.completed_at}
                tq.completed_count += 1
                processed += 1
                if task.id in self._task_registry:
                    self._task_registry[task.id].status = TaskStatus.COMPLETED

        tq.active_count = 0
        self._total_tasks_completed += processed
        return processed

    # ---- Task Management ----

    def enqueue_task(self,
                     queue_id: str,
                     agent_id: str,
                     task_type: str,
                     payload: Optional[Dict[str, Any]] = None,
                     priority: str = "normal",
                     timeout_seconds: float = 60.0) -> Optional[ConcurrencyTask]:
        tq = self._queues.get(queue_id)
        if tq is None:
            return None

        try:
            p = TaskPriority(priority.lower())
        except ValueError:
            p = TaskPriority.NORMAL

        task = ConcurrencyTask(
            agent_id=agent_id,
            task_type=task_type,
            payload=payload or {},
            priority=p,
            timeout_seconds=timeout_seconds,
        )

        tq.tasks[task.id] = task
        self._task_registry[task.id] = task
        self._total_tasks_enqueued += 1

        with self._heap_lock:
            heapq.heappush(
                self._priority_heap,
                (p.value, task.created_at, task.id),
            )

        return task

    def dequeue_next(self, queue_id: str) -> Optional[ConcurrencyTask]:
        tq = self._queues.get(queue_id)
        if tq is None:
            return None

        if self.is_paused(queue_id):
            return None

        queued_tasks = [
            t for t in tq.tasks.values()
            if t.status == TaskStatus.QUEUED
        ]
        if not queued_tasks:
            return None

        # Currently active count acts as a simple concurrency cap for
        # non-PARALLEL strategies; PARALLEL bypasses the cap check.
        if tq.strategy != ConcurrencyStrategy.PARALLEL:
            if tq.active_count >= tq.max_concurrent:
                return None

        queued_tasks.sort(key=lambda t: (t.priority.value, t.created_at))

        if tq.strategy == ConcurrencyStrategy.ROUND_ROBIN:
            candidate = queued_tasks[0]
        elif tq.strategy == ConcurrencyStrategy.PRIORITY_QUEUE:
            candidate = min(queued_tasks, key=lambda t: (t.priority.value, t.created_at))
        else:
            candidate = queued_tasks[0]

        return candidate

    def execute_task(self, task_id: str) -> Optional[ConcurrencyTask]:
        task = self._task_registry.get(task_id)
        if task is None:
            return None

        if task.status not in (TaskStatus.QUEUED,):
            return task

        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        task.attempts += 1

        for tq in self._queues.values():
            if task.id in tq.tasks:
                tq.active_count += 1
                break

        return task

    def complete_task(self,
                      task_id: str,
                      result: Any = None) -> Optional[ConcurrencyTask]:
        task = self._task_registry.get(task_id)
        if task is None:
            return None

        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.result = result

        self._total_tasks_completed += 1

        if task.started_at is not None:
            latency = (task.completed_at - task.started_at) * 1000
            self._latency_samples.append(latency)
            if len(self._latency_samples) > 1000:
                self._latency_samples.pop(0)

        now = time.time()
        self._throughput_window.append(now)
        self._throughput_window = [
            t for t in self._throughput_window if now - t <= 60.0
        ]

        for tq in self._queues.values():
            if task.id in tq.tasks:
                tq.active_count = max(0, tq.active_count - 1)
                tq.completed_count += 1
                break

        return task

    def fail_task(self,
                  task_id: str,
                  error: str = "") -> Optional[ConcurrencyTask]:
        task = self._task_registry.get(task_id)
        if task is None:
            return None

        task.status = TaskStatus.FAILED
        task.error_log.append(error)
        task.completed_at = time.time()

        self._total_tasks_failed += 1

        for tq in self._queues.values():
            if task.id in tq.tasks:
                tq.active_count = max(0, tq.active_count - 1)
                tq.failed_count += 1
                break

        return task

    def cancel_task(self, task_id: str) -> bool:
        task = self._task_registry.get(task_id)
        if task is None:
            return False

        if task.status == TaskStatus.QUEUED:
            task.status = TaskStatus.CANCELLED
            return True

        return False

    def get_task(self, task_id: str) -> Optional[ConcurrencyTask]:
        return self._task_registry.get(task_id)

    def list_tasks(self,
                   status: Optional[str] = None,
                   queue_id: Optional[str] = None) -> List[ConcurrencyTask]:
        tasks = list(self._task_registry.values())
        if status is not None:
            try:
                s = TaskStatus(status.lower())
                tasks = [t for t in tasks if t.status == s]
            except ValueError:
                pass
        if queue_id is not None:
            tq = self._queues.get(queue_id)
            if tq is not None:
                tasks = [t for t in tasks if t.id in tq.tasks]
        return tasks

    # ---- Rate Limiting ----

    def set_rate_limit(self,
                       limit_type: str,
                       max_value: float,
                       reset_interval: float = 1.0) -> RateLimit:
        try:
            lt = RateLimitType(limit_type.lower())
        except ValueError:
            lt = RateLimitType.CUSTOM

        rl = RateLimit(
            limit_type=lt,
            max_value=max_value,
            reset_interval=reset_interval,
        )
        self._rate_limits[rl.id] = rl
        return rl

    def check_rate_limit(self, limit_id: str) -> bool:
        rl = self._rate_limits.get(limit_id)
        if rl is None:
            return True
        if not rl.enabled:
            return True

        now = time.time()
        if now - rl.last_reset >= rl.reset_interval:
            rl.current_value = 0
            rl.last_reset = now

        if rl.current_value < rl.max_value:
            rl.current_value += 1
            return True

        return False

    def update_rate_limit(self,
                          limit_id: str,
                          max_value: float,
                          reset_interval: float) -> bool:
        rl = self._rate_limits.get(limit_id)
        if rl is None:
            return False
        rl.max_value = max_value
        rl.reset_interval = reset_interval
        return True

    def disable_rate_limit(self, limit_id: str) -> bool:
        rl = self._rate_limits.get(limit_id)
        if rl is None:
            return False
        rl.enabled = False
        return True

    def enable_rate_limit(self, limit_id: str) -> bool:
        rl = self._rate_limits.get(limit_id)
        if rl is None:
            return False
        rl.enabled = True
        return True

    def get_rate_limit(self, limit_id: str) -> Optional[RateLimit]:
        return self._rate_limits.get(limit_id)

    def list_rate_limits(self) -> List[RateLimit]:
        return list(self._rate_limits.values())

    def get_active_limits(self) -> List[RateLimit]:
        return [rl for rl in self._rate_limits.values() if rl.enabled]

    # ---- Task Lifecycle Extensions ----

    def retry_task(self, task_id: str) -> Optional[ConcurrencyTask]:
        task = self._task_registry.get(task_id)
        if task is None:
            return None
        if task.status not in (TaskStatus.FAILED, TaskStatus.TIMED_OUT):
            return None
        if task.attempts >= task.max_retries:
            return None

        task.status = TaskStatus.QUEUED
        task.started_at = None
        task.completed_at = None

        with self._heap_lock:
            heapq.heappush(
                self._priority_heap,
                (task.priority.value, time.time(), task.id),
            )

        return task

    def reprioritize_task(self, task_id: str, new_priority: str) -> bool:
        task = self._task_registry.get(task_id)
        if task is None:
            return False
        if task.status not in (TaskStatus.QUEUED,):
            return False

        try:
            p = TaskPriority(new_priority.lower())
        except ValueError:
            return False

        task.priority = p
        with self._heap_lock:
            heapq.heappush(
                self._priority_heap,
                (p.value, task.created_at, task.id),
            )

        return True

    def remove_queue(self, queue_id: str) -> bool:
        tq = self._queues.get(queue_id)
        if tq is None:
            return False
        if tq.active_count > 0:
            return False

        for task in tq.tasks.values():
            if task.status in (TaskStatus.RUNNING,):
                return False
            self._task_registry.pop(task.id, None)

        self._paused_queues.discard(queue_id)
        del self._queues[queue_id]
        return True

    def get_priority_queue_size(self) -> int:
        with self._heap_lock:
            return len(self._priority_heap)

    def get_tasks_by_priority(self, priority: str) -> List[ConcurrencyTask]:
        try:
            p = TaskPriority(priority.lower())
        except ValueError:
            return []
        return [
            t for t in self._task_registry.values()
            if t.priority == p and t.status == TaskStatus.QUEUED
        ]

    def timeout_task(self, task_id: str) -> Optional[ConcurrencyTask]:
        task = self._task_registry.get(task_id)
        if task is None:
            return None
        if task.status != TaskStatus.RUNNING:
            return None

        task.status = TaskStatus.TIMED_OUT
        task.completed_at = time.time()

        for tq in self._queues.values():
            if task.id in tq.tasks:
                tq.active_count = max(0, tq.active_count - 1)
                tq.failed_count += 1
                break

        self._total_tasks_failed += 1
        return task

    # ---- Internal Methods ----

    def _compact_task_registry(self) -> int:
        terminal_statuses = {
            TaskStatus.COMPLETED, TaskStatus.FAILED,
            TaskStatus.CANCELLED, TaskStatus.TIMED_OUT,
        }
        removed = 0
        stale_ids = [
            tid for tid, task in self._task_registry.items()
            if task.status in terminal_statuses
            and task.completed_at is not None
            and time.time() - task.completed_at > 3600
        ]
        for tid in stale_ids:
            del self._task_registry[tid]
            removed += 1
        return removed

    def _calculate_latency_percentile(self, percentile: float) -> float:
        if not self._latency_samples:
            return 0.0
        sorted_samples = sorted(self._latency_samples)
        index = int(len(sorted_samples) * percentile / 100.0)
        index = min(index, len(sorted_samples) - 1)
        return sorted_samples[index]

    # ---- Stats ----

    def get_queue_stats(self, queue_id: str) -> Optional[ConcurrencyStats]:
        tq = self._queues.get(queue_id)
        if tq is None:
            return None

        queued = sum(
            1 for t in tq.tasks.values()
            if t.status == TaskStatus.QUEUED
        )
        running = sum(
            1 for t in tq.tasks.values()
            if t.status == TaskStatus.RUNNING
        )

        avg_latency = (
            sum(self._latency_samples) / len(self._latency_samples)
            if self._latency_samples
            else 0.0
        )

        now = time.time()
        recent_window = [ts for ts in self._throughput_window if now - ts <= 60.0]
        throughput = len(recent_window) / max(now - (recent_window[0] if recent_window else now), 1.0)

        return ConcurrencyStats(
            total_tasks=len(tq.tasks),
            active_tasks=running,
            queued_tasks=queued,
            completed_tasks=tq.completed_count,
            failed_tasks=tq.failed_count,
            average_latency_ms=avg_latency,
            throughput_per_sec=throughput,
        )

    def get_stats(self) -> Dict[str, Any]:
        total_queued = sum(
            len(tq.tasks) for tq in self._queues.values()
        )
        total_active = sum(
            tq.active_count for tq in self._queues.values()
        )
        avg_latency = (
            sum(self._latency_samples) / len(self._latency_samples)
            if self._latency_samples
            else 0.0
        )

        now = time.time()
        recent_window = [ts for ts in self._throughput_window if now - ts <= 60.0]
        throughput = len(recent_window) / max(now - (recent_window[0] if recent_window else now), 1.0)

        return {
            "total_queues": len(self._queues),
            "total_tasks_enqueued": self._total_tasks_enqueued,
            "total_tasks_completed": self._total_tasks_completed,
            "total_tasks_failed": self._total_tasks_failed,
            "tasks_in_registry": len(self._task_registry),
            "total_queued_tasks": total_queued,
            "active_tasks": total_active,
            "paused_queues": len(self._paused_queues),
            "rate_limits_configured": len(self._rate_limits),
            "average_latency_ms": avg_latency,
            "throughput_per_sec": throughput,
        }


def get_concurrency_manager() -> AgentConcurrencyManager:
    return AgentConcurrencyManager.get_instance()