"""
SparkLabs Engine Job System

A parallel job/task scheduling engine for the AI-native game engine.
Distributes engine operations across multiple worker threads with
priority-based scheduling, dependency resolution, and work stealing.

Architecture:
  JobSystemEngine (Singleton)
    |-- Job              — unit of work with priority, dependencies, retries
    |-- JobQueue         — prioritized queue with concurrency limits
    |-- JobResult        — execution outcome with timing and diagnostics
    |-- WorkerThread     — dedicated thread that executes jobs
    |-- JobGraph         — directed acyclic graph for dependency ordering

Scheduling Pipeline:
  1. Submission  — jobs are validated and enqueued with priority
  2. Scheduling  — workers dequeue based on active scheduling policy
  3. Execution   — job's data callback is invoked on the worker thread
  4. Completion  — result is recorded, dependents are unblocked
  5. Retry       — failed jobs are re-queued up to max_retries
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class JobStatus(Enum):
    """Lifecycle states of a job within the scheduling system."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobType(Enum):
    """Category of engine operation that a job performs."""
    PHYSICS_STEP = "physics_step"
    AI_INFERENCE = "ai_inference"
    RENDER_PASS = "render_pass"
    ASSET_LOAD = "asset_load"
    AUDIO_PROCESS = "audio_process"
    PARTICLE_UPDATE = "particle_update"
    PATHFINDING = "pathfinding"
    SERIALIZATION = "serialization"
    NETWORK_SYNC = "network_sync"
    CUSTOM = "custom"


class WorkerStatus(Enum):
    """Operational state of a worker thread."""
    IDLE = "idle"
    WORKING = "working"
    STOPPED = "stopped"
    ERROR = "error"


class SchedulingPolicy(Enum):
    """Strategy used to select the next job from the queue."""
    FIFO = "fifo"
    PRIORITY_FIRST = "priority_first"
    WORK_STEALING = "work_stealing"
    DEPENDENCY_AWARE = "dependency_aware"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Job:
    """A unit of work scheduled for execution on a worker thread."""

    job_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    job_type: JobType = JobType.CUSTOM
    priority: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: JobStatus = JobStatus.PENDING
    assigned_thread: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    progress: float = 0.0
    result: Any = None
    error: str = ""
    retry_count: int = 0
    max_retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Internal fields not serialized
    _completion_event: Any = field(
        default_factory=threading.Event, repr=False
    )
    _result_lock: Any = field(
        default_factory=threading.Lock, repr=False
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "name": self.name,
            "job_type": self.job_type.value,
            "priority": self.priority,
            "data": self.data,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "assigned_thread": self.assigned_thread,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "metadata": self.metadata,
        }

    def mark_running(self, thread_id: str) -> None:
        self.status = JobStatus.RUNNING
        self.assigned_thread = thread_id
        self.start_time = time.time()
        self.progress = 0.0
        self._completion_event.clear()

    def mark_completed(self, result: Any) -> None:
        self.status = JobStatus.COMPLETED
        self.end_time = time.time()
        self.progress = 1.0
        self.result = result
        self.error = ""
        self._completion_event.set()

    def mark_failed(self, error: str) -> None:
        self.status = JobStatus.FAILED
        self.end_time = time.time()
        self.error = error
        self._completion_event.set()

    def mark_cancelled(self) -> None:
        self.status = JobStatus.CANCELLED
        self.end_time = time.time()
        self._completion_event.set()

    @property
    def execution_time(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time is not None else time.time()
        return end - self.start_time

    @property
    def is_ready(self) -> bool:
        return self.status in (JobStatus.PENDING, JobStatus.QUEUED)

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        )


@dataclass
class JobQueue:
    """A prioritized queue that holds jobs awaiting execution."""

    queue_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = "default"
    max_concurrent: int = 4
    jobs: List[Job] = field(default_factory=list)
    priority_levels: Dict[int, float] = field(default_factory=dict)
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queue_id": self.queue_id,
            "name": self.name,
            "max_concurrent": self.max_concurrent,
            "job_count": len(self.jobs),
            "priority_levels": self.priority_levels,
            "status": self.status,
        }

    def enqueue(self, job: Job) -> None:
        job.status = JobStatus.QUEUED
        self.jobs.append(job)

    def dequeue(self, policy: SchedulingPolicy = SchedulingPolicy.PRIORITY_FIRST) -> Optional[Job]:
        if not self.jobs:
            return None
        if policy == SchedulingPolicy.FIFO:
            return self.jobs.pop(0)
        elif policy == SchedulingPolicy.PRIORITY_FIRST:
            best_idx = 0
            best_priority = -999999
            for i, j in enumerate(self.jobs):
                if j.priority > best_priority:
                    best_priority = j.priority
                    best_idx = i
            return self.jobs.pop(best_idx)
        else:
            return self.jobs.pop(0)

    def remove_job(self, job_id: str) -> Optional[Job]:
        for i, job in enumerate(self.jobs):
            if job.job_id == job_id:
                return self.jobs.pop(i)
        return None


@dataclass
class JobResult:
    """The outcome of executing a single job."""

    job_id: str = ""
    success: bool = False
    result: Any = None
    error: str = ""
    execution_time: float = 0.0
    thread_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "thread_id": self.thread_id,
        }


@dataclass
class WorkerThread:
    """Metadata and state for a single worker thread in the pool."""

    thread_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    status: WorkerStatus = WorkerStatus.IDLE
    current_job_id: Optional[str] = None
    jobs_completed: int = 0
    total_execution_time: float = 0.0
    cpu_usage: float = 0.0

    # Internal fields
    _thread_handle: Any = field(default=None, repr=False)
    _pause_event: Any = field(
        default_factory=threading.Event, repr=False
    )
    _stop_event: Any = field(
        default_factory=threading.Event, repr=False
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "name": self.name,
            "status": self.status.value,
            "current_job_id": self.current_job_id,
            "jobs_completed": self.jobs_completed,
            "total_execution_time": self.total_execution_time,
            "cpu_usage": self.cpu_usage,
        }


@dataclass
class JobGraph:
    """Directed acyclic graph representing job dependencies."""

    nodes: List[str] = field(default_factory=list)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    exit_points: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "entry_points": self.entry_points,
            "exit_points": self.exit_points,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }

    def get_topological_order(self) -> List[str]:
        """Compute a topological ordering of the graph nodes."""
        in_degree: Dict[str, int] = {node: 0 for node in self.nodes}
        adjacency: Dict[str, List[str]] = {node: [] for node in self.nodes}

        for from_id, to_id in self.edges:
            if from_id in adjacency and to_id in in_degree:
                adjacency[from_id].append(to_id)
                in_degree[to_id] += 1

        queue: deque = deque()
        for node in self.nodes:
            if in_degree.get(node, 0) == 0:
                queue.append(node)

        order: List[str] = []
        while queue:
            current = queue.popleft()
            order.append(current)
            for neighbor in adjacency.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self.nodes):
            return []
        return order


# ---------------------------------------------------------------------------
# Job System Engine
# ---------------------------------------------------------------------------

class JobSystemEngine:
    """
    Parallel job scheduling engine for multi-threaded game engine operations.

    Manages a pool of worker threads that execute prioritized jobs with
    support for dependency graphs, work stealing, retry logic, and
    real-time progress tracking. Workers can be paused, resumed, and
    the scheduling policy can be changed at runtime.
    """

    _instance: Optional["JobSystemEngine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "JobSystemEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "JobSystemEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._jobs: Dict[str, Job] = {}
        self._job_results: Dict[str, JobResult] = {}
        self._workers: Dict[str, WorkerThread] = {}
        self._queues: Dict[str, JobQueue] = {}
        self._policy: SchedulingPolicy = SchedulingPolicy.PRIORITY_FIRST
        self._running: bool = False
        self._job_counter: int = 0
        self._total_submitted: int = 0
        self._total_completed: int = 0
        self._total_failed: int = 0
        self._total_cancelled: int = 0
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self._default_queue: JobQueue = JobQueue(name="default")
        self._queues[self._default_queue.queue_id] = self._default_queue

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, num_workers: int) -> None:
        """Start the worker thread pool with the specified number of threads."""
        with self._lock:
            if self._running:
                return
            self._running = True
            for i in range(num_workers):
                name = f"worker-{i}"
                worker = WorkerThread(name=name)
                worker._pause_event.set()
                worker._stop_event.clear()
                thread = threading.Thread(
                    target=self._worker_loop,
                    args=(worker.thread_id,),
                    name=name,
                    daemon=True,
                )
                worker._thread_handle = thread
                worker.status = WorkerStatus.IDLE
                self._workers[worker.thread_id] = worker
                thread.start()

    def stop(self) -> None:
        """Gracefully stop all worker threads and drain pending jobs."""
        with self._lock:
            self._running = False
            for worker in self._workers.values():
                worker._stop_event.set()
                worker._pause_event.set()
        for worker in self._workers.values():
            if worker._thread_handle and worker._thread_handle.is_alive():
                worker._thread_handle.join(timeout=5.0)
                worker.status = WorkerStatus.STOPPED

    # ------------------------------------------------------------------
    # Job Submission
    # ------------------------------------------------------------------

    def submit_job(
        self,
        name: str,
        job_type: JobType,
        data: Dict[str, Any],
        priority: int = 0,
        dependencies: Optional[List[str]] = None,
        max_retries: int = 0,
        queue_id: Optional[str] = None,
    ) -> Job:
        """Submit a single job to the scheduling system."""
        with self._lock:
            self._job_counter += 1
            self._total_submitted += 1

            job = Job(
                name=name,
                job_type=job_type,
                priority=priority,
                data=data,
                dependencies=dependencies or [],
                max_retries=max_retries,
                status=JobStatus.PENDING,
            )
            self._jobs[job.job_id] = job

            if job.dependencies:
                for dep_id in job.dependencies:
                    self._dependency_graph[dep_id].add(job.job_id)
                    self._reverse_dependencies[job.job_id].add(dep_id)

            target_queue = self._queues.get(queue_id) if queue_id else self._default_queue
            if queue_id and queue_id not in self._queues:
                target_queue = self._default_queue

            if not job.dependencies:
                target_queue.enqueue(job)
            else:
                all_deps_satisfied = True
                for dep_id in job.dependencies:
                    dep_job = self._jobs.get(dep_id)
                    if dep_job is None or dep_job.status != JobStatus.COMPLETED:
                        all_deps_satisfied = False
                        break
                if all_deps_satisfied:
                    target_queue.enqueue(job)

            return job

    def submit_job_batch(self, jobs: List[Dict[str, Any]]) -> List[Job]:
        """Submit multiple jobs in a single batch operation."""
        results: List[Job] = []
        for job_spec in jobs:
            job = self.submit_job(
                name=job_spec.get("name", "batch_job"),
                job_type=job_spec.get("job_type", JobType.CUSTOM),
                data=job_spec.get("data", {}),
                priority=job_spec.get("priority", 0),
                dependencies=job_spec.get("dependencies", None),
                max_retries=job_spec.get("max_retries", 0),
                queue_id=job_spec.get("queue_id", None),
            )
            results.append(job)
        return results

    # ------------------------------------------------------------------
    # Waiting
    # ------------------------------------------------------------------

    def wait_for_job(
        self, job_id: str, timeout: Optional[float] = None
    ) -> Optional[JobResult]:
        """Block until a specific job completes, fails, or is cancelled."""
        job = self._jobs.get(job_id)
        if job is None:
            return None
        if job._completion_event.wait(timeout=timeout):
            return self._job_results.get(job_id)
        return None

    def wait_for_all(
        self, timeout: Optional[float] = None
    ) -> List[JobResult]:
        """Block until all submitted jobs reach a terminal state."""
        results: List[JobResult] = []
        deadline = time.time() + timeout if timeout is not None else float("inf")
        while True:
            with self._lock:
                pending = [
                    j for j in self._jobs.values()
                    if not j.is_terminal
                ]
            if not pending:
                break
            if time.time() >= deadline:
                break
            time.sleep(0.01)
        with self._lock:
            for job_id, result in self._job_results.items():
                results.append(result)
        return results

    # ------------------------------------------------------------------
    # Job Control
    # ------------------------------------------------------------------

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or queued job. Running jobs cannot be cancelled."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                return False
            if job.status == JobStatus.RUNNING:
                return False

            job.mark_cancelled()
            self._total_cancelled += 1
            self._job_results[job_id] = JobResult(
                job_id=job_id,
                success=False,
                error="Cancelled",
                execution_time=job.execution_time,
            )

            for queue in self._queues.values():
                queue.remove_job(job_id)

            self._unblock_dependents(job_id)
            return True

    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get the current status of a job by its ID."""
        job = self._jobs.get(job_id)
        return job.status if job else None

    def get_job_result(self, job_id: str) -> Optional[JobResult]:
        """Get the result of a completed job."""
        return self._job_results.get(job_id)

    # ------------------------------------------------------------------
    # Job Graph
    # ------------------------------------------------------------------

    def build_job_graph(self, job_ids: List[str]) -> JobGraph:
        """Build a dependency graph for the given set of job IDs."""
        nodes = list(job_ids)
        edges: List[Tuple[str, str]] = []
        entry: List[str] = []
        exit_nodes: List[str] = []

        in_degree: Dict[str, int] = defaultdict(int)
        out_degree: Dict[str, int] = defaultdict(int)

        for jid in job_ids:
            job = self._jobs.get(jid)
            if job is None:
                continue
            for dep_id in job.dependencies:
                if dep_id in job_ids:
                    edges.append((dep_id, jid))
                    in_degree[jid] += 1
                    out_degree[dep_id] += 1

        for jid in nodes:
            if in_degree.get(jid, 0) == 0:
                entry.append(jid)
            if out_degree.get(jid, 0) == 0:
                exit_nodes.append(jid)

        return JobGraph(
            nodes=nodes,
            edges=edges,
            entry_points=entry,
            exit_points=exit_nodes,
        )

    def execute_graph(self, graph: JobGraph) -> List[JobResult]:
        """Execute all jobs in a graph respecting dependency order."""
        order = graph.get_topological_order()
        if not order:
            return []

        results: List[JobResult] = []
        for job_id in order:
            job = self._jobs.get(job_id)
            if job is None:
                continue
            if job.status == JobStatus.COMPLETED:
                result = self._job_results.get(job_id)
                if result:
                    results.append(result)
                continue
            if job.status == JobStatus.CANCELLED:
                continue

            if not job.dependencies:
                self._default_queue.enqueue(job)

            result = self.wait_for_job(job_id)
            if result:
                results.append(result)
        return results

    # ------------------------------------------------------------------
    # Worker Management
    # ------------------------------------------------------------------

    def get_worker_status(self) -> List[WorkerThread]:
        """Get the current status of all worker threads."""
        with self._lock:
            return list(self._workers.values())

    def pause_worker(self, thread_id: str) -> bool:
        """Pause a specific worker thread."""
        worker = self._workers.get(thread_id)
        if worker is None:
            return False
        worker._pause_event.clear()
        return True

    def resume_worker(self, thread_id: str) -> bool:
        """Resume a paused worker thread."""
        worker = self._workers.get(thread_id)
        if worker is None:
            return False
        worker._pause_event.set()
        return True

    # ------------------------------------------------------------------
    # Queue Management
    # ------------------------------------------------------------------

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics for all job queues."""
        with self._lock:
            queue_data = {}
            for qid, queue in self._queues.items():
                pending = sum(1 for j in queue.jobs if j.status == JobStatus.QUEUED)
                queue_data[qid] = {
                    "name": queue.name,
                    "max_concurrent": queue.max_concurrent,
                    "total_jobs": len(queue.jobs),
                    "pending_jobs": pending,
                    "status": queue.status,
                }
            return {
                "queue_count": len(self._queues),
                "queues": queue_data,
            }

    def set_scheduling_policy(self, policy: SchedulingPolicy) -> None:
        """Change the scheduling policy used by all workers."""
        with self._lock:
            self._policy = policy

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics."""
        with self._lock:
            job_type_counts: Dict[str, int] = {}
            job_status_counts: Dict[str, int] = {}
            for job in self._jobs.values():
                t = job.job_type.value
                job_type_counts[t] = job_type_counts.get(t, 0) + 1
                s = job.status.value
                job_status_counts[s] = job_status_counts.get(s, 0) + 1

            worker_status_counts: Dict[str, int] = {}
            for worker in self._workers.values():
                s = worker.status.value
                worker_status_counts[s] = worker_status_counts.get(s, 0) + 1

            total_jobs_completed = sum(
                w.jobs_completed for w in self._workers.values()
            )
            total_execution = sum(
                w.total_execution_time for w in self._workers.values()
            )

            return {
                "job_system_running": self._running,
                "total_workers": len(self._workers),
                "total_jobs": len(self._jobs),
                "total_submitted": self._total_submitted,
                "total_completed": self._total_completed,
                "total_failed": self._total_failed,
                "total_cancelled": self._total_cancelled,
                "total_jobs_completed": total_jobs_completed,
                "total_execution_time": total_execution,
                "scheduling_policy": self._policy.value,
                "job_type_distribution": job_type_counts,
                "job_status_distribution": job_status_counts,
                "worker_status_distribution": worker_status_counts,
                "queue_count": len(self._queues),
                "dependency_edges": sum(
                    len(deps) for deps in self._dependency_graph.values()
                ),
            }

    # ------------------------------------------------------------------
    # Internal: Worker Loop
    # ------------------------------------------------------------------

    def _worker_loop(self, thread_id: str) -> None:
        """Main loop executed by each worker thread."""
        worker = self._workers.get(thread_id)
        if worker is None:
            return

        while not worker._stop_event.is_set():
            worker._pause_event.wait()

            job = self._dequeue_job(thread_id)
            if job is None:
                worker.status = WorkerStatus.IDLE
                worker.current_job_id = None
                time.sleep(0.001)
                continue

            worker.status = WorkerStatus.WORKING
            worker.current_job_id = job.job_id
            job.mark_running(thread_id)

            loop_start = time.time()
            result = self._execute_job(job, worker)
            elapsed = time.time() - loop_start

            worker.total_execution_time += elapsed
            worker.jobs_completed += 1

            with self._lock:
                self._job_results[job.job_id] = result

                if result.success:
                    self._total_completed += 1
                else:
                    self._total_failed += 1

                self._unblock_dependents(job.job_id)

            worker.status = WorkerStatus.IDLE
            worker.current_job_id = None

    def _execute_job(self, job: Job, worker: WorkerThread) -> JobResult:
        """Execute a single job and return its result."""
        callback = job.data.get("callback")
        args = job.data.get("args", ())
        kwargs = job.data.get("kwargs", {})

        try:
            if callable(callback):
                result = callback(*args, **kwargs)
            else:
                result = None

            job.mark_completed(result)
            return JobResult(
                job_id=job.job_id,
                success=True,
                result=result,
                execution_time=job.execution_time,
                thread_id=worker.thread_id,
            )
        except Exception as exc:
            error_msg = str(exc)
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = JobStatus.RETRYING
                with self._lock:
                    self._default_queue.enqueue(job)
                return JobResult(
                    job_id=job.job_id,
                    success=False,
                    error=f"Retrying ({job.retry_count}/{job.max_retries}): {error_msg}",
                    execution_time=job.execution_time,
                    thread_id=worker.thread_id,
                )
            job.mark_failed(error_msg)
            return JobResult(
                job_id=job.job_id,
                success=False,
                error=error_msg,
                execution_time=job.execution_time,
                thread_id=worker.thread_id,
            )

    def _dequeue_job(self, thread_id: str) -> Optional[Job]:
        """Dequeue a job using the current scheduling policy."""
        with self._lock:
            if self._policy == SchedulingPolicy.WORK_STEALING:
                return self._dequeue_work_stealing(thread_id)
            elif self._policy == SchedulingPolicy.DEPENDENCY_AWARE:
                return self._dequeue_dependency_aware()
            else:
                return self._default_queue.dequeue(self._policy)

    def _dequeue_work_stealing(self, thread_id: str) -> Optional[Job]:
        """Steal a job from another worker's queue if local is empty."""
        job = self._default_queue.dequeue(SchedulingPolicy.PRIORITY_FIRST)
        if job is not None:
            return job

        for qid, queue in self._queues.items():
            if qid == self._default_queue.queue_id:
                continue
            if not queue.jobs:
                continue
            job = queue.dequeue(SchedulingPolicy.PRIORITY_FIRST)
            if job is not None:
                return job

        return None

    def _dequeue_dependency_aware(self) -> Optional[Job]:
        """Dequeue a job whose dependencies are all satisfied."""
        for i, job in enumerate(self._default_queue.jobs):
            ready = True
            for dep_id in job.dependencies:
                dep_job = self._jobs.get(dep_id)
                if dep_job is None or dep_job.status != JobStatus.COMPLETED:
                    ready = False
                    break
            if ready:
                best_idx = i
                best_priority = job.priority
                for j in range(i + 1, len(self._default_queue.jobs)):
                    candidate = self._default_queue.jobs[j]
                    if candidate.priority > best_priority:
                        all_ready = True
                        for dep_id in candidate.dependencies:
                            dep_job = self._jobs.get(dep_id)
                            if dep_job is None or dep_job.status != JobStatus.COMPLETED:
                                all_ready = False
                                break
                        if all_ready:
                            best_priority = candidate.priority
                            best_idx = j
                return self._default_queue.jobs.pop(best_idx)
        return None

    def _unblock_dependents(self, completed_job_id: str) -> None:
        """Release any jobs that were waiting on the completed job."""
        dependents = self._dependency_graph.get(completed_job_id, set())
        for dep_job_id in list(dependents):
            dep_job = self._jobs.get(dep_job_id)
            if dep_job is None:
                continue
            if dep_job.status in (JobStatus.CANCELLED, JobStatus.FAILED):
                self._dependency_graph[completed_job_id].discard(dep_job_id)
                continue

            all_ready = True
            for requirement in dep_job.dependencies:
                req_job = self._jobs.get(requirement)
                if req_job is None or req_job.status != JobStatus.COMPLETED:
                    all_ready = False
                    break

            if all_ready:
                self._default_queue.enqueue(dep_job)
                self._dependency_graph[completed_job_id].discard(dep_job_id)

    # ------------------------------------------------------------------
    # Job Query
    # ------------------------------------------------------------------

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by its ID."""
        return self._jobs.get(job_id)

    def get_all_jobs(self) -> List[Job]:
        """Get all jobs in the system."""
        with self._lock:
            return list(self._jobs.values())

    def get_jobs_by_type(self, job_type: JobType) -> List[Job]:
        """Get all jobs of a specific type."""
        with self._lock:
            return [j for j in self._jobs.values() if j.job_type == job_type]

    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """Get all jobs with a specific status."""
        with self._lock:
            return [j for j in self._jobs.values() if j.status == status]

    # ------------------------------------------------------------------
    # Queue Administration
    # ------------------------------------------------------------------

    def create_queue(self, name: str, max_concurrent: int = 4) -> JobQueue:
        """Create a new named job queue."""
        with self._lock:
            queue = JobQueue(name=name, max_concurrent=max_concurrent)
            self._queues[queue.queue_id] = queue
            return queue

    def remove_queue(self, queue_id: str) -> bool:
        """Remove a queue. The default queue cannot be removed."""
        if queue_id == self._default_queue.queue_id:
            return False
        with self._lock:
            if queue_id in self._queues:
                queue = self._queues[queue_id]
                for job in queue.jobs:
                    self._default_queue.enqueue(job)
                del self._queues[queue_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire job system state."""
        with self._lock:
            self._jobs.clear()
            self._job_results.clear()
            self._dependency_graph.clear()
            self._reverse_dependencies.clear()
            self._job_counter = 0
            self._total_submitted = 0
            self._total_completed = 0
            self._total_failed = 0
            self._total_cancelled = 0
            self._default_queue = JobQueue(name="default")
            self._queues.clear()
            self._queues[self._default_queue.queue_id] = self._default_queue


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_job_system() -> JobSystemEngine:
    """Get or create the singleton JobSystemEngine instance."""
    return JobSystemEngine.get_instance()