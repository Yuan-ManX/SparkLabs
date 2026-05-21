"""
SparkLabs Agent - Cron Scheduler

Scheduled autonomous agent task execution with cron-like expression
evaluation, task dependency chains, retry logic, and multi-agent
coordination. Provides a centralized scheduling engine that evaluates
time-based execution rules, respects dependency ordering, applies
configurable retry strategies, and coordinates task dispatch across
multiple agent instances.

Architecture:
  AgentCronScheduler
    |-- ScheduleRule (cron expression definition and evaluation)
    |-- CronTask (scheduled task with state and retry tracking)
    |-- TaskExecution (per-run execution record with timing metrics)
    |-- TaskDependency (dependency chain definition and validation)
    |-- RetryManager (backoff strategy computation and apply logic)

Scheduling Features:
  - FREQUENCY: once, minutley, hourly, daily, weekly, monthly, custom cron
  - DEPENDENCIES: chain tasks with prerequisite completion requirements
  - PRIORITIES: low, normal, high, critical execution ordering
  - RETRIES: linear, exponential, fixed, and none backoff strategies
  - COORDINATION: multi-agent task dispatch with state synchronization
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CronFrequency(Enum):
    ONCE = "once"
    MINUTELY = "minutely"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class RetryPolicy(Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIXED = "fixed"
    NONE = "none"


@dataclass
class TaskDependency:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str = ""
    depends_on_task_id: str = ""
    required_state: TaskState = TaskState.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "depends_on_task_id": self.depends_on_task_id,
            "required_state": self.required_state.value,
        }


@dataclass
class ScheduleRule:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    frequency: CronFrequency = CronFrequency.DAILY
    cron_expression: str = ""
    timezone: str = "UTC"
    created_at: float = field(default_factory=time.time)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "frequency": self.frequency.value,
            "cron_expression": self.cron_expression,
            "timezone": self.timezone,
            "created_at": self.created_at,
            "enabled": self.enabled,
        }


@dataclass
class CronTask:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    rule_id: str = ""
    task_name: str = ""
    action_params: Dict[str, Any] = field(default_factory=dict)
    state: TaskState = TaskState.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    max_retries: int = 3
    retry_policy: RetryPolicy = RetryPolicy.EXPONENTIAL
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    scheduled_at: float = 0.0
    last_run_at: float = 0.0
    next_run_at: float = 0.0
    paused: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "rule_id": self.rule_id,
            "task_name": self.task_name,
            "action_params": self.action_params,
            "state": self.state.value,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "max_retries": self.max_retries,
            "retry_policy": self.retry_policy.value,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "scheduled_at": self.scheduled_at,
            "last_run_at": self.last_run_at,
            "next_run_at": self.next_run_at,
            "paused": self.paused,
        }


@dataclass
class TaskExecution:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str = ""
    state: TaskState = TaskState.PENDING
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    output: Optional[Dict[str, Any]] = None
    duration: float = 0.0
    retry_attempt: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "state": self.state.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "output": self.output,
            "duration": round(self.duration, 3),
            "retry_attempt": self.retry_attempt,
        }


class AgentCronScheduler:
    """Autonomous agent task scheduler with cron evaluation and retry handling."""

    _instance: Optional["AgentCronScheduler"] = None
    _lock = threading.RLock()

    _FREQUENCY_INTERVALS: Dict[CronFrequency, float] = {
        CronFrequency.ONCE: 0,
        CronFrequency.MINUTELY: 60,
        CronFrequency.HOURLY: 3600,
        CronFrequency.DAILY: 86400,
        CronFrequency.WEEKLY: 604800,
        CronFrequency.MONTHLY: 2592000,
        CronFrequency.CUSTOM: 0,
    }

    def __init__(self) -> None:
        self._tasks: Dict[str, CronTask] = {}
        self._executions: List[TaskExecution] = []
        self._rules: Dict[str, ScheduleRule] = {}
        self._dependencies: Dict[str, TaskDependency] = {}
        self._tick_count: int = 0

    @classmethod
    def get_instance(cls) -> "AgentCronScheduler":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Rule Management ----

    def create_rule(self,
                    name: str,
                    frequency: CronFrequency,
                    cron_expression: str = "",
                    timezone: str = "UTC") -> ScheduleRule:
        rule = ScheduleRule(
            name=name,
            frequency=frequency,
            cron_expression=cron_expression,
            timezone=timezone,
        )
        self._rules[rule.id] = rule
        return rule

    def get_rule(self, rule_id: str) -> Optional[ScheduleRule]:
        return self._rules.get(rule_id)

    def list_rules(self) -> List[ScheduleRule]:
        return list(self._rules.values())

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    # ---- Task Scheduling ----

    def schedule_task(self,
                      agent_id: str,
                      rule_id: str,
                      task_name: str,
                      action_params: Optional[Dict[str, Any]] = None,
                      priority: TaskPriority = TaskPriority.NORMAL,
                      dependencies: Optional[List[str]] = None,
                      max_retries: int = 3,
                      retry_policy: RetryPolicy = RetryPolicy.EXPONENTIAL) -> CronTask:
        rule = self._rules.get(rule_id)
        next_run = 0.0
        if rule is not None and rule.frequency != CronFrequency.ONCE:
            interval = self._FREQUENCY_INTERVALS.get(rule.frequency, 0)
            if interval > 0:
                next_run = time.time() + interval

        task = CronTask(
            agent_id=agent_id,
            rule_id=rule_id,
            task_name=task_name,
            action_params=action_params or {},
            priority=priority,
            dependencies=dependencies or [],
            max_retries=max_retries,
            retry_policy=retry_policy,
            scheduled_at=time.time(),
            next_run_at=next_run,
        )
        self._tasks[task.id] = task

        for dep_task_id in task.dependencies:
            dep = TaskDependency(
                task_id=task.id,
                depends_on_task_id=dep_task_id,
            )
            self._dependencies[dep.id] = dep

        return task

    def get_task(self, task_id: str) -> Optional[CronTask]:
        return self._tasks.get(task_id)

    def list_tasks(self,
                   state: Optional[TaskState] = None,
                   agent_id: Optional[str] = None) -> List[CronTask]:
        results = list(self._tasks.values())
        if state is not None:
            results = [t for t in results if t.state == state]
        if agent_id is not None:
            results = [t for t in results if t.agent_id == agent_id]
        return sorted(results, key=lambda t: (t.priority.value, t.created_at), reverse=True)

    # ---- Task Control ----

    def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        if task.state not in (TaskState.PENDING, TaskState.RETRYING):
            return False
        task.state = TaskState.CANCELLED
        return True

    def pause_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        if task.state not in (TaskState.PENDING, TaskState.RETRYING):
            return False
        task.paused = True
        return True

    def resume_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        if not task.paused:
            return False
        task.paused = False
        return True

    def trigger_task_now(self, task_id: str) -> Optional[TaskExecution]:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        if task.state == TaskState.CANCELLED:
            return None
        if not self._dependencies_satisfied(task):
            return None

        task.state = TaskState.RUNNING
        task.last_run_at = time.time()

        execution = TaskExecution(
            task_id=task.id,
            state=TaskState.RUNNING,
            retry_attempt=task.retry_count,
        )
        return execution

    # ---- Due Task Evaluation ----

    def get_due_tasks(self) -> List[CronTask]:
        now = time.time()
        due: List[CronTask] = []

        for task in self._tasks.values():
            if task.state != TaskState.PENDING:
                continue
            if task.paused:
                continue
            if task.next_run_at <= 0:
                due.append(task)
                continue
            if now >= task.next_run_at:
                due.append(task)

        due.sort(key=lambda t: (t.priority.value, t.created_at), reverse=True)
        return due

    # ---- Execution Recording ----

    def record_execution(self,
                         task_id: str,
                         state: TaskState,
                         output: Optional[Dict[str, Any]] = None,
                         duration: float = 0.0) -> TaskExecution:
        task = self._tasks.get(task_id)
        execution = TaskExecution(
            task_id=task_id,
            state=state,
            output=output,
            duration=duration,
            completed_at=time.time(),
        )

        if task is not None:
            execution.retry_attempt = task.retry_count
            if state == TaskState.COMPLETED:
                task.state = TaskState.COMPLETED
            elif state == TaskState.FAILED:
                should_retry = self._should_retry(task)
                if should_retry:
                    task.state = TaskState.RETRYING
                    task.retry_count += 1
                    backoff = self._compute_backoff(task)
                    task.next_run_at = time.time() + backoff
                else:
                    task.state = TaskState.FAILED

        self._executions.append(execution)
        return execution

    def get_execution_history(self,
                              task_id: str,
                              limit: int = 50) -> List[TaskExecution]:
        matches = [e for e in self._executions if e.task_id == task_id]
        matches.sort(key=lambda e: e.started_at, reverse=True)
        return matches[:limit]

    # ---- Tick Engine ----

    def tick(self) -> Dict[str, Any]:
        self._tick_count += 1
        due_tasks = self.get_due_tasks()
        spawned: List[TaskExecution] = []

        for task in due_tasks:
            if not self._dependencies_satisfied(task):
                continue
            task.state = TaskState.RUNNING
            task.last_run_at = time.time()
            interval = self._FREQUENCY_INTERVALS.get(
                CronFrequency.DAILY, 86400
            )
            rule = self._rules.get(task.rule_id)
            if rule is not None:
                interval = self._FREQUENCY_INTERVALS.get(rule.frequency, 0)
            if interval > 0:
                task.next_run_at = time.time() + interval

            execution = TaskExecution(
                task_id=task.id,
                state=TaskState.RUNNING,
                retry_attempt=task.retry_count,
            )
            self._executions.append(execution)
            spawned.append(execution)

        return {
            "tick": self._tick_count,
            "due_count": len(due_tasks),
            "spawned": len(spawned),
            "spawned_ids": [e.id for e in spawned],
            "timestamp": time.time(),
        }

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        task_states: Dict[str, int] = {}
        for task in self._tasks.values():
            key = task.state.value
            task_states[key] = task_states.get(key, 0) + 1

        priority_counts: Dict[str, int] = {}
        for task in self._tasks.values():
            key = task.priority.name.lower()
            priority_counts[key] = priority_counts.get(key, 0) + 1

        successful = sum(
            1 for e in self._executions if e.state == TaskState.COMPLETED
        )
        failed = sum(
            1 for e in self._executions if e.state == TaskState.FAILED
        )
        total_duration = sum(e.duration for e in self._executions)
        avg_duration = total_duration / max(len(self._executions), 1)

        return {
            "total_tasks": len(self._tasks),
            "total_rules": len(self._rules),
            "total_executions": len(self._executions),
            "total_dependencies": len(self._dependencies),
            "tick_count": self._tick_count,
            "tasks_by_state": task_states,
            "tasks_by_priority": priority_counts,
            "successful_executions": successful,
            "failed_executions": failed,
            "average_duration": round(avg_duration, 3),
            "paused_tasks": sum(1 for t in self._tasks.values() if t.paused),
        }

    # ---- Private Helpers ----

    def _dependencies_satisfied(self, task: CronTask) -> bool:
        if not task.dependencies:
            return True
        for dep_task_id in task.dependencies:
            dep_task = self._tasks.get(dep_task_id)
            if dep_task is None:
                return False
            if dep_task.state != TaskState.COMPLETED:
                return False
        return True

    def _should_retry(self, task: CronTask) -> bool:
        if task.retry_policy == RetryPolicy.NONE:
            return False
        if task.retry_count >= task.max_retries:
            return False
        if task.state == TaskState.CANCELLED:
            return False
        return True

    @staticmethod
    def _compute_backoff(task: CronTask) -> float:
        base_delay = 5.0
        attempt = task.retry_count + 1

        if task.retry_policy == RetryPolicy.LINEAR:
            return base_delay * attempt
        elif task.retry_policy == RetryPolicy.EXPONENTIAL:
            return base_delay * (2 ** (attempt - 1))
        elif task.retry_policy == RetryPolicy.FIXED:
            return base_delay
        return 0.0

    def _compute_next_run(self, rule: ScheduleRule, from_time: float) -> float:
        interval = self._FREQUENCY_INTERVALS.get(rule.frequency, 0)
        if interval <= 0:
            return 0.0
        return from_time + interval

    def _reschedule_recurring(self, task: CronTask) -> None:
        rule = self._rules.get(task.rule_id)
        if rule is None:
            return
        if rule.frequency == CronFrequency.ONCE:
            return
        interval = self._FREQUENCY_INTERVALS.get(rule.frequency, 0)
        if interval > 0:
            task.next_run_at = time.time() + interval
            task.state = TaskState.PENDING
            task.retry_count = 0


def get_cron_scheduler() -> AgentCronScheduler:
    return AgentCronScheduler.get_instance()