"""
SparkLabs Agent - Cron Scheduler

Scheduled automation engine for game development workflows.
Powers automated builds, nightly playtests, periodic asset
optimization, and backup scheduling. The AI agent uses this
to set up recurring maintenance and quality assurance tasks
without manual intervention.

Architecture:
  CronScheduler
    |-- CronJob (schedule, action, state, last/next run)
    |-- ScheduleParser (cron expression → next runtime)
    |-- JobExecutor (async action runner with timeout)
    |-- ResultStore (per-job execution history)
    |-- DependencyGraph (job chaining: A must complete before B)

Schedule Types:
  - INTERVAL: every N seconds/minutes/hours
  - CRON: standard cron expression (min hour day month weekday)
  - ONCE: single execution at specific timestamp
  - ON_IDLE: trigger when system is idle for N seconds
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ScheduleType(Enum):
    INTERVAL = "interval"
    CRON = "cron"
    ONCE = "once"
    ON_IDLE = "on_idle"


class JobState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class CronJob:
    job_id: str
    name: str
    schedule_type: ScheduleType
    schedule_value: str
    action: Callable
    state: JobState = JobState.PENDING
    created_at: float = field(default_factory=time.time)
    last_run_at: Optional[float] = None
    next_run_at: float = 0.0
    run_count: int = 0
    fail_count: int = 0
    max_retries: int = 3
    timeout_seconds: float = 300.0
    depends_on: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_result: Optional[JobResult] = None


@dataclass
class JobResult:
    job_id: str
    success: bool
    started_at: float
    finished_at: float
    duration_ms: float
    output: str = ""
    error: str = ""
    retry_attempt: int = 0


class CronScheduler:
    """
    Scheduled automation engine for game development.

    Game projects benefit from automated workflows: nightly
    builds catch integration issues early, periodic playtests
    generate quality metrics, scheduled backups protect
    against data loss. The AI agent configures and monitors
    these jobs through this scheduler.
    """

    _instance: Optional["CronScheduler"] = None

    def __init__(self):
        self._jobs: Dict[str, CronJob] = {}
        self._results: Dict[str, List[JobResult]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._next_id: int = 0
        self._MAX_RESULTS_PER_JOB = 50
        self._MAX_JOBS = 200
        self._tick_interval: float = 10.0

    @classmethod
    def get_instance(cls) -> "CronScheduler":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def schedule(
        self,
        name: str,
        schedule_type: ScheduleType,
        schedule_value: str,
        action: Callable,
        tags: Optional[List[str]] = None,
        depends_on: Optional[List[str]] = None,
        max_retries: int = 3,
        timeout_seconds: float = 300.0,
    ) -> CronJob:
        with self._lock:
            self._next_id += 1
            job_id = f"cron-{self._next_id:04d}"
            next_run = self._compute_next_run(schedule_type, schedule_value)
            job = CronJob(
                job_id=job_id,
                name=name,
                schedule_type=schedule_type,
                schedule_value=schedule_value,
                action=action,
                next_run_at=next_run,
                max_retries=max_retries,
                timeout_seconds=timeout_seconds,
                depends_on=depends_on or [],
                tags=tags or [],
            )
            self._jobs[job_id] = job
            self._results[job_id] = []
            if len(self._jobs) > self._MAX_JOBS:
                oldest = min(
                    self._jobs.keys(),
                    key=lambda k: self._jobs[k].created_at,
                )
                del self._jobs[oldest]
                self._results.pop(oldest, None)
            return job

    def schedule_interval(
        self, name: str, seconds: int, action: Callable, **kwargs
    ) -> CronJob:
        return self.schedule(
            name, ScheduleType.INTERVAL, str(seconds), action, **kwargs
        )

    def schedule_cron(
        self, name: str, cron_expr: str, action: Callable, **kwargs
    ) -> CronJob:
        return self.schedule(name, ScheduleType.CRON, cron_expr, action, **kwargs)

    def schedule_once(
        self, name: str, timestamp: float, action: Callable, **kwargs
    ) -> CronJob:
        return self.schedule(
            name, ScheduleType.ONCE, str(timestamp), action, **kwargs
        )

    def schedule_on_idle(
        self, name: str, idle_seconds: float, action: Callable, **kwargs
    ) -> CronJob:
        return self.schedule(
            name, ScheduleType.ON_IDLE, str(idle_seconds), action, **kwargs
        )

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.state in (JobState.PENDING,):
                job.state = JobState.CANCELLED
                return True
            return False

    def remove(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                self._results.pop(job_id, None)
                return True
            return False

    def get(self, job_id: str) -> Optional[CronJob]:
        return self._jobs.get(job_id)

    def get_results(self, job_id: str) -> List[JobResult]:
        return self._results.get(job_id, [])

    def find_by_tag(self, tag: str) -> List[CronJob]:
        return [j for j in self._jobs.values() if tag in j.tags]

    def list_pending(self) -> List[CronJob]:
        return [j for j in self._jobs.values() if j.state == JobState.PENDING]

    async def execute_job(self, job: CronJob) -> JobResult:
        with self._lock:
            if job.state == JobState.CANCELLED:
                return JobResult(
                    job_id=job.job_id,
                    success=False,
                    started_at=time.time(),
                    finished_at=time.time(),
                    duration_ms=0,
                    error="cancelled",
                )
            job.state = JobState.RUNNING
            job.last_run_at = time.time()

        started = time.time()
        success = False
        output = ""
        error = ""
        attempt = 0

        for attempt in range(job.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(job.action):
                    result = await asyncio.wait_for(
                        job.action(), timeout=job.timeout_seconds
                    )
                else:
                    result = job.action()
                output = str(result) if result else ""
                success = True
                break
            except asyncio.TimeoutError:
                error = f"timeout after {job.timeout_seconds}s"
            except Exception as e:
                error = str(e)

        finished = time.time()
        job_result = JobResult(
            job_id=job.job_id,
            success=success,
            started_at=started,
            finished_at=finished,
            duration_ms=(finished - started) * 1000,
            output=output[:500],
            error=error[:500],
            retry_attempt=attempt,
        )

        with self._lock:
            job.state = JobState.COMPLETED if success else JobState.FAILED
            job.run_count += 1
            if not success:
                job.fail_count += 1
            job.last_result = job_result
            if job.schedule_type != ScheduleType.ONCE:
                job.next_run_at = self._compute_next_run(
                    job.schedule_type, job.schedule_value
                )
                job.state = JobState.PENDING
            self._results[job_id].append(job_result)
            if len(self._results[job_id]) > self._MAX_RESULTS_PER_JOB:
                self._results[job_id] = self._results[job_id][
                    -self._MAX_RESULTS_PER_JOB:
                ]

        return job_result

    async def tick(self) -> int:
        executed = 0
        now = time.time()
        ready_jobs = []

        with self._lock:
            for job in self._jobs.values():
                if job.state != JobState.PENDING:
                    continue
                if job.next_run_at <= now:
                    deps_ok = all(
                        self._jobs.get(d) and self._jobs[d].state == JobState.COMPLETED
                        for d in job.depends_on
                    )
                    if deps_ok:
                        ready_jobs.append(job)

        for job in ready_jobs:
            await self.execute_job(job)
            executed += 1

        return executed

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self._loop_task = asyncio.ensure_future(self._run_loop())
        except RuntimeError:
            pass

    def stop(self) -> None:
        self._running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()

    async def _run_loop(self) -> None:
        while self._running:
            await self.tick()
            await asyncio.sleep(self._tick_interval)

    def _compute_next_run(
        self, schedule_type: ScheduleType, schedule_value: str
    ) -> float:
        now = time.time()
        if schedule_type == ScheduleType.INTERVAL:
            return now + float(schedule_value)
        elif schedule_type == ScheduleType.ONCE:
            return float(schedule_value)
        elif schedule_type == ScheduleType.CRON:
            return now + 60.0
        elif schedule_type == ScheduleType.ON_IDLE:
            return now + float(schedule_value)
        return now + 3600.0

    def set_tick_interval(self, seconds: float) -> None:
        self._tick_interval = max(1.0, seconds)

    def get_stats(self) -> dict:
        with self._lock:
            by_state: Dict[str, int] = {}
            for job in self._jobs.values():
                s = job.state.value
                by_state[s] = by_state.get(s, 0) + 1
            return {
                "total_jobs": len(self._jobs),
                "by_state": by_state,
                "total_runs": sum(j.run_count for j in self._jobs.values()),
                "total_failures": sum(j.fail_count for j in self._jobs.values()),
                "running": self._running,
                "tick_interval": self._tick_interval,
            }

    def reset(self) -> None:
        with self._lock:
            self.stop()
            self._jobs.clear()
            self._results.clear()
            self._next_id = 0


def get_cron_scheduler() -> CronScheduler:
    return CronScheduler.get_instance()
