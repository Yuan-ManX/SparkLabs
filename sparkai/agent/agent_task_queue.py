"""
SparkLabs Agent - Task Queue

Prioritized task scheduling and execution queue for AI-native
game development operations. Manages task lifecycle from submission
through execution, with dependency resolution, retry logic, and
concurrency control for multi-agent coordination.

Architecture:
  AgentTaskQueue
    |-- TaskScheduler (priority-based ordering with deadlines)
    |-- TaskWorker (concurrent executor with resource limits)
    |-- TaskDependencyGraph (DAG constraint resolution)
    |-- TaskMonitor (progress tracking and heartbeat checks)
    |-- TaskResultCache (idempotent result storage)

Task Categories:
  - GAME_GENERATION: full game creation workflows
  - CODE_SYNTHESIS: script and logic generation
  - ASSET_PROCESSING: sprite, audio, tilemap operations
  - VALIDATION: quality gate and correctness checks
  - MAINTENANCE: cleanup, optimization, refactoring
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, Future


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskState(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    RETRYING = "retrying"


class TaskCategory(Enum):
    GAME_GENERATION = "game_generation"
    CODE_SYNTHESIS = "code_synthesis"
    ASSET_PROCESSING = "asset_processing"
    VALIDATION = "validation"
    MAINTENANCE = "maintenance"
    CUSTOM = "custom"


@dataclass
class TaskDependency:
    task_id: str
    required_state: TaskState = TaskState.COMPLETED


@dataclass
class TaskResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    retries_used: int = 0


@dataclass
class QueueTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    category: TaskCategory = TaskCategory.CUSTOM
    priority: TaskPriority = TaskPriority.NORMAL
    state: TaskState = TaskState.PENDING
    payload: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[TaskDependency] = field(default_factory=list)
    deadline: Optional[float] = None
    max_retries: int = 3
    retry_count: int = 0
    retry_delay: float = 1.0
    timeout: float = 300.0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[TaskResult] = None
    assigned_worker: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "priority": self.priority.name,
            "state": self.state.value,
            "dependencies": [d.task_id for d in self.dependencies],
            "deadline": self.deadline,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "tags": self.tags,
        }

    def is_blocked(self, completed_ids: Set[str]) -> bool:
        for dep in self.dependencies:
            if dep.task_id not in completed_ids:
                return True
        return False


class AgentTaskQueue:
    """
    Prioritized task queue with dependency resolution, concurrency
    control, and retry logic for AI-native game development workflows.

    Usage:
        queue = AgentTaskQueue(max_workers=4)
        task_id = queue.submit(
            name="generate_sprite",
            category=TaskCategory.ASSET_PROCESSING,
            handler=lambda payload: generate(**(payload or {})),
            payload={"width": 64, "height": 64},
        )
        result = queue.wait_for(task_id)
    """

    _instance: Optional["AgentTaskQueue"] = None

    MAX_QUEUE_SIZE = 1000
    MAX_RESULT_CACHE = 500

    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers
        self._tasks: Dict[str, QueueTask] = {}
        self._pending: Dict[TaskPriority, deque] = {
            TaskPriority.CRITICAL: deque(),
            TaskPriority.HIGH: deque(),
            TaskPriority.NORMAL: deque(),
            TaskPriority.LOW: deque(),
            TaskPriority.BACKGROUND: deque(),
        }
        self._completed_ids: Set[str] = set()
        self._handlers: Dict[str, Callable] = {}
        self._executor: Optional[ThreadPoolExecutor] = None
        self._futures: Dict[str, Future] = {}
        self._lock = threading.RLock()
        self._running = False
        self._result_cache: Dict[str, TaskResult] = {}
        self._stats = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }

    @classmethod
    def get_instance(cls, max_workers: int = 4) -> "AgentTaskQueue":
        if cls._instance is None:
            cls._instance = cls(max_workers=max_workers)
        return cls._instance

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
            self._running = True

    def stop(self) -> None:
        with self._lock:
            self._running = False
            if self._executor:
                self._executor.shutdown(wait=False)
                self._executor = None

    def submit(
        self,
        name: str,
        handler: Callable[[Dict[str, Any]], Any],
        payload: Optional[Dict[str, Any]] = None,
        category: TaskCategory = TaskCategory.CUSTOM,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: Optional[List[str]] = None,
        deadline: Optional[float] = None,
        max_retries: int = 3,
        timeout: float = 300.0,
        tags: Optional[List[str]] = None,
    ) -> str:
        with self._lock:
            if len(self._tasks) >= self.MAX_QUEUE_SIZE:
                raise RuntimeError(f"Task queue full ({self.MAX_QUEUE_SIZE} max)")

            task = QueueTask(
                name=name,
                category=category,
                priority=priority,
                payload=payload or {},
                dependencies=[TaskDependency(task_id=did) for did in (dependencies or [])],
                deadline=deadline,
                max_retries=max_retries,
                timeout=timeout,
                tags=tags or [],
            )
            task.state = TaskState.QUEUED
            self._tasks[task.id] = task
            self._handlers[task.id] = handler
            self._pending[priority].append(task.id)
            self._stats["submitted"] += 1

            self._try_dispatch()
            return task.id

    def submit_and_wait(
        self,
        name: str,
        handler: Callable[[Dict[str, Any]], Any],
        payload: Optional[Dict[str, Any]] = None,
        category: TaskCategory = TaskCategory.CUSTOM,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: float = 300.0,
    ) -> TaskResult:
        task_id = self.submit(
            name=name,
            handler=handler,
            payload=payload,
            category=category,
            priority=priority,
            timeout=timeout,
        )
        return self.wait_for(task_id, timeout=timeout)

    def wait_for(self, task_id: str, timeout: float = 300.0, poll_interval: float = 0.05) -> TaskResult:
        start = time.time()
        while time.time() - start < timeout:
            with self._lock:
                task = self._tasks.get(task_id)
                if task and task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
                    if task.result:
                        return task.result
                    return TaskResult(success=False, error="No result available")
            time.sleep(poll_interval)
        return TaskResult(success=False, error=f"Timeout waiting for task {task_id}")

    def get_task(self, task_id: str) -> Optional[QueueTask]:
        return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
                return False
            future = self._futures.get(task_id)
            if future and not future.done():
                future.cancel()
            task.state = TaskState.CANCELLED
            task.completed_at = time.time()
            self._stats["cancelled"] += 1

            for priority_deque in self._pending.values():
                if task_id in priority_deque:
                    priority_deque.remove(task_id)
                    break
            return True

    def list_tasks(
        self,
        state: Optional[TaskState] = None,
        category: Optional[TaskCategory] = None,
        tag: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            tasks = list(self._tasks.values())
            if state:
                tasks = [t for t in tasks if t.state == state]
            if category:
                tasks = [t for t in tasks if t.category == category]
            if tag:
                tasks = [t for t in tasks if tag in t.tags]
            return [t.to_dict() for t in tasks]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            pending_count = sum(len(d) for d in self._pending.values())
            return {
                **self._stats,
                "pending_count": pending_count,
                "total_tasks": len(self._tasks),
                "running_tasks": sum(
                    1 for t in self._tasks.values() if t.state == TaskState.RUNNING
                ),
                "max_workers": self._max_workers,
                "running": self._running,
            }

    def _try_dispatch(self) -> None:
        if not self._running or self._executor is None:
            return

        active = sum(1 for f in self._futures.values() if not f.done())
        available = self._max_workers - active
        if available <= 0:
            return

        dispatched = 0
        for priority in [
            TaskPriority.CRITICAL,
            TaskPriority.HIGH,
            TaskPriority.NORMAL,
            TaskPriority.LOW,
            TaskPriority.BACKGROUND,
        ]:
            if dispatched >= available:
                break
            task_ids = list(self._pending[priority])
            for tid in task_ids:
                if dispatched >= available:
                    break
                task = self._tasks.get(tid)
                if not task or task.state != TaskState.QUEUED:
                    self._pending[priority].remove(tid)
                    continue
                if task.is_blocked(self._completed_ids):
                    task.state = TaskState.BLOCKED
                    continue

                self._pending[priority].remove(tid)
                task.state = TaskState.RUNNING
                task.started_at = time.time()
                task.assigned_worker = f"worker-{dispatched}"

                future = self._executor.submit(self._execute_task, task)
                self._futures[task.id] = future
                dispatched += 1

    def _execute_task(self, task: QueueTask) -> None:
        handler = self._handlers.get(task.id)
        if not handler:
            self._complete_task(task, TaskResult(success=False, error="No handler registered"))
            return

        attempt = 0
        last_error = None

        while attempt <= task.max_retries:
            attempt_start = time.time()
            try:
                result_data = handler(task.payload)
                duration = (time.time() - attempt_start) * 1000
                self._complete_task(
                    task,
                    TaskResult(
                        success=True,
                        data=result_data,
                        duration_ms=duration,
                        retries_used=attempt,
                    ),
                )
                return
            except Exception as e:
                last_error = str(e)
                attempt += 1
                task.retry_count = attempt

                if attempt <= task.max_retries:
                    with self._lock:
                        task.state = TaskState.RETRYING
                    time.sleep(task.retry_delay * attempt)

        duration = (time.time() - (task.started_at or task.created_at)) * 1000
        self._complete_task(
            task,
            TaskResult(
                success=False,
                error=last_error,
                duration_ms=duration,
                retries_used=attempt - 1,
            ),
        )

    def _complete_task(self, task: QueueTask, result: TaskResult) -> None:
        with self._lock:
            task.state = TaskState.COMPLETED if result.success else TaskState.FAILED
            task.completed_at = time.time()
            task.result = result

            if result.success:
                self._completed_ids.add(task.id)
                self._stats["completed"] += 1
            else:
                self._stats["failed"] += 1

            if len(self._result_cache) >= self.MAX_RESULT_CACHE:
                oldest = min(self._result_cache, key=lambda k: self._tasks.get(k, QueueTask()).created_at) if self._result_cache else None
                if oldest:
                    del self._result_cache[oldest]
            if result.success:
                self._result_cache[task.id] = result

            if task.id in self._futures:
                del self._futures[task.id]

            self._try_dispatch()


def get_agent_task_queue(max_workers: int = 4) -> AgentTaskQueue:
    return AgentTaskQueue.get_instance(max_workers=max_workers)