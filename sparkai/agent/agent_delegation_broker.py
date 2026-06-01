"""
DelegationBroker - Subagent delegation and parallel task management system.

Subagent spawning capabilities, this module
provides a centralized broker for registering specialized subagents,
delegating tasks using configurable strategies, executing tasks in
parallel via threading, and orchestrating multi-agent pipeline workflows.

Architecture:
    DelegationBroker (singleton)
      |-- SubagentDefinition (agent capability registry entry)
      |-- DelegationTask (task lifecycle tracking)
      |-- DelegationStrategy (task-to-agent assignment logic)
      |-- ParallelExecutor (threading-based concurrent execution)
      |-- WorkflowPipeline (planner -> executor -> reviewer)

Delegation Strategies:
    - ROUND_ROBIN: cycles through available agents evenly
    - PRIORITY_BASED: assigns to highest-priority available agent
    - CAPABILITY_MATCH: scores agents by capability overlap
    - LOAD_BALANCED: assigns to least-loaded capable agent
    - FIRST_AVAILABLE: assigns to first agent with matching capability

Usage:
    broker = get_delegation_broker()
    agent = broker.register_agent(
        name="Gameplay Coder",
        role=AgentRole.CODER,
        capabilities=["code_gen", "world_build"],
    )
    task = broker.assign_task(
        agent_id=agent.id,
        task_description="Implement player controller",
        strategy=DelegationStrategy.CAPABILITY_MATCH,
    )
    results = broker.execute_parallel([task1, task2, task3])
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

_time_module = time


class AgentRole(Enum):
    """Specialized roles that subagents can fulfill within the delegation system."""

    PLANNER = "planner"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
    RESEARCHER = "researcher"
    CODER = "coder"
    TESTER = "tester"
    COORDINATOR = "coordinator"


class TaskStatus(Enum):
    """Lifecycle states for a delegated task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class DelegationStrategy(Enum):
    """Strategies for assigning tasks to subagents."""

    ROUND_ROBIN = "round_robin"
    PRIORITY_BASED = "priority_based"
    CAPABILITY_MATCH = "capability_match"
    LOAD_BALANCED = "load_balanced"
    FIRST_AVAILABLE = "first_available"


@dataclass
class SubagentDefinition:
    """A registered subagent with role, capabilities, and runtime metadata.

    Each subagent represents a specialized worker that can accept delegated
    tasks. The broker manages their lifecycle, workload, and availability.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    role: AgentRole = AgentRole.EXECUTOR
    capabilities: List[str] = field(default_factory=list)
    model: str = "default"
    timeout_seconds: float = 120.0
    max_retries: int = 3
    priority: int = 50
    status: str = "idle"
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "capabilities": self.capabilities,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass
class DelegationTask:
    """A task delegated to a subagent with full lifecycle tracking.

    Tracks the assignment, execution attempts, result collection, and
    any errors that occur during processing. Supports retry logic and
    parent session correlation for complex workflows.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    task_description: str = ""
    context_json: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result_json: Dict[str, Any] = field(default_factory=dict)
    attempts: int = 0
    parent_session_id: Optional[str] = None
    assigned_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "task_description": self.task_description,
            "context_json": self.context_json,
            "status": self.status.value,
            "result_json": self.result_json,
            "attempts": self.attempts,
            "parent_session_id": self.parent_session_id,
            "assigned_at": self.assigned_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
        }


class DelegationBroker:
    """Singleton broker for subagent delegation and parallel task management.

    Provides the central registry for subagents and tasks, implements
    multiple delegation strategies for intelligent task routing, supports
    parallel execution via threading, and orchestrates multi-agent pipeline
    workflows where output from one agent feeds as input to the next.

    Thread-safe via RLock. Single instance enforced with double-check
    locking in __new__. Use get_delegation_broker() or
    DelegationBroker.get_instance() to obtain the singleton instance.
    """

    _instance: Optional[DelegationBroker] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> DelegationBroker:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._agents: Dict[str, SubagentDefinition] = {}
                    instance._tasks: Dict[str, DelegationTask] = {}
                    instance._workload: Dict[str, int] = {}
                    instance._round_robin_index: int = 0
                    instance._pipeline_results: List[Dict[str, Any]] = []
                    instance._total_registered: int = 0
                    instance._total_assigned: int = 0
                    instance._total_completed: int = 0
                    instance._total_failed: int = 0
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> DelegationBroker:
        return cls()

    # ------------------------------------------------------------------
    # Agent registration and management
    # ------------------------------------------------------------------

    def register_agent(
        self,
        name: str,
        role: AgentRole = AgentRole.EXECUTOR,
        capabilities: Optional[List[str]] = None,
        model: str = "default",
        timeout_seconds: float = 120.0,
        max_retries: int = 3,
        priority: int = 50,
    ) -> SubagentDefinition:
        """Create and register a new subagent with role and capabilities.

        Args:
            name: Human-readable name for the subagent.
            role: The specialized role this agent fulfills.
            capabilities: List of capability strings (e.g. code_gen, world_build).
            model: Model identifier used for LLM calls.
            timeout_seconds: Maximum execution time per task.
            max_retries: Maximum retry attempts for failed tasks.
            priority: Priority score for PRIORITY_BASED strategy (higher = preferred).

        Returns:
            The newly created SubagentDefinition.
        """
        with self._lock:
            agent = SubagentDefinition(
                name=name,
                role=role,
                capabilities=capabilities or [],
                model=model,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                priority=priority,
            )
            self._agents[agent.id] = agent
            self._workload[agent.id] = 0
            self._total_registered += 1
            return agent

    def unregister_agent(self, agent_id: str) -> bool:
        """Remove an agent from the registry.

        Args:
            agent_id: The ID of the agent to remove.

        Returns:
            True if the agent was found and removed, False otherwise.
        """
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                self._workload.pop(agent_id, None)
                return True
            return False

    def list_agents(
        self,
        role: Optional[AgentRole] = None,
        capability: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List registered agents, optionally filtered by role or capability.

        Args:
            role: Filter agents by this role.
            capability: Filter agents that have this capability.

        Returns:
            A list of agent dictionaries.
        """
        with self._lock:
            agents = list(self._agents.values())
            if role:
                agents = [a for a in agents if a.role == role]
            if capability:
                agents = [a for a in agents if capability in a.capabilities]
            return [a.to_dict() for a in agents]

    # ------------------------------------------------------------------
    # Task delegation
    # ------------------------------------------------------------------

    def assign_task(
        self,
        agent_id: str = "",
        task_description: str = "",
        context_json: Optional[Dict[str, Any]] = None,
        strategy: DelegationStrategy = DelegationStrategy.CAPABILITY_MATCH,
        parent_session_id: Optional[str] = None,
    ) -> Optional[DelegationTask]:
        """Delegate a task to the best matching agent using the given strategy.

        If agent_id is provided, the task is directly assigned to that agent.
        Otherwise, the broker selects an agent based on the strategy.

        Args:
            agent_id: Target agent ID. If empty, auto-selects using strategy.
            task_description: Description of the work to perform.
            context_json: Additional context data for the task.
            strategy: The delegation strategy for agent selection.
            parent_session_id: Optional parent session for correlation.

        Returns:
            The created DelegationTask, or None if no suitable agent found.
        """
        with self._lock:
            selected_id = agent_id
            if not selected_id:
                selected_id = self._select_agent_by_strategy(
                    strategy, task_description, context_json or {}
                )
            if not selected_id or selected_id not in self._agents:
                return None

            task = DelegationTask(
                agent_id=selected_id,
                task_description=task_description,
                context_json=context_json or {},
                status=TaskStatus.PENDING,
                parent_session_id=parent_session_id,
                assigned_at=_time_module.time(),
            )
            self._tasks[task.id] = task
            self._workload[selected_id] = self._workload.get(selected_id, 0) + 1
            self._total_assigned += 1
            return task

    def _select_agent_by_strategy(
        self,
        strategy: DelegationStrategy,
        task_description: str,
        context_json: Dict[str, Any],
    ) -> Optional[str]:
        """Select the best agent for a task based on the delegation strategy.

        Args:
            strategy: The strategy to use for selection.
            task_description: Task description for capability matching.
            context_json: Additional context for capability inference.

        Returns:
            The selected agent ID, or None if no agent is available.
        """
        available = [a for a in self._agents.values() if a.status == "idle"]
        if not available:
            return None

        required_caps: Set[str] = set(context_json.get("required_capabilities", []))

        if strategy == DelegationStrategy.ROUND_ROBIN:
            avail_sorted = sorted(available, key=lambda a: a.id)
            idx = self._round_robin_index % len(avail_sorted)
            self._round_robin_index += 1
            return avail_sorted[idx].id

        elif strategy == DelegationStrategy.PRIORITY_BASED:
            avail_sorted = sorted(available, key=lambda a: a.priority, reverse=True)
            return avail_sorted[0].id

        elif strategy == DelegationStrategy.CAPABILITY_MATCH:
            if not required_caps:
                task_words = set(task_description.lower().split())
                scored: List[Tuple[str, float]] = []
                for agent in available:
                    agent_cap_words = set(" ".join(agent.capabilities).lower().split())
                    overlap = len(task_words & agent_cap_words) / max(len(task_words), 1)
                    agent_score = overlap * 10.0 + agent.priority * 0.01
                    scored.append((agent.id, agent_score))
                scored.sort(key=lambda x: x[1], reverse=True)
                return scored[0][0] if scored else None
            else:
                scored = []
                for agent in available:
                    agent_caps = set(agent.capabilities)
                    match_count = len(required_caps & agent_caps)
                    if match_count > 0:
                        scored.append((agent.id, match_count + agent.priority * 0.01))
                scored.sort(key=lambda x: x[1], reverse=True)
                return scored[0][0] if scored else None

        elif strategy == DelegationStrategy.LOAD_BALANCED:
            candidates = [(a.id, self._workload.get(a.id, 0)) for a in available]
            candidates.sort(key=lambda x: x[1])
            return candidates[0][0] if candidates else None

        elif strategy == DelegationStrategy.FIRST_AVAILABLE:
            return available[0].id

        return None

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a task by its ID.

        Args:
            task_id: The task ID to look up.

        Returns:
            The task dictionary, or None if not found.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                return task.to_dict()
            return None

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered by status or agent.

        Args:
            status: Filter by task status.
            agent_id: Filter by assigned agent ID.
            limit: Maximum number of tasks to return.

        Returns:
            A list of task dictionaries.
        """
        with self._lock:
            tasks = list(self._tasks.values())
            if status:
                tasks = [t for t in tasks if t.status == status]
            if agent_id:
                tasks = [t for t in tasks if t.agent_id == agent_id]
            tasks.sort(key=lambda t: t.assigned_at or 0, reverse=True)
            return [t.to_dict() for t in tasks[:limit]]

    # ------------------------------------------------------------------
    # Parallel execution
    # ------------------------------------------------------------------

    def execute_parallel(
        self,
        tasks: List[DelegationTask],
        timeout_seconds: float = 120.0,
    ) -> List[Dict[str, Any]]:
        """Run multiple tasks concurrently using threading.Thread.

        Each task is dispatched to a separate thread. The broker waits
        for all threads to complete or until the timeout is reached,
        then collects and returns the results.

        Args:
            tasks: The list of tasks to execute in parallel.
            timeout_seconds: Maximum time to wait for all tasks.

        Returns:
            A list of result dictionaries, one per task.
        """
        results: List[Dict[str, Any]] = []
        results_lock = threading.Lock()
        threads: List[threading.Thread] = []

        def _execute_single(task: DelegationTask) -> None:
            with self._lock:
                task.status = TaskStatus.IN_PROGRESS
                task.attempts += 1

            try:
                agent = None
                with self._lock:
                    agent = self._agents.get(task.agent_id)

                execution_fn = self._build_execution_fn(agent)
                outcome = execution_fn(task)

                with self._lock:
                    task.status = TaskStatus.SUCCESS
                    task.result_json = outcome
                    task.completed_at = _time_module.time()
                    self._total_completed += 1

                with results_lock:
                    results.append(task.to_dict())

            except Exception as exc:
                with self._lock:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(exc)
                    task.completed_at = _time_module.time()
                    self._total_failed += 1

                with results_lock:
                    results.append(task.to_dict())

        for t in tasks:
            thread = threading.Thread(target=_execute_single, args=(t,), daemon=True)
            threads.append(thread)
            thread.start()

        deadline = _time_module.time() + timeout_seconds
        for thread in threads:
            remaining = max(0.0, deadline - _time_module.time())
            thread.join(timeout=remaining)

        for task in tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                with self._lock:
                    task.status = TaskStatus.TIMED_OUT
                    task.error_message = f"Task timed out after {timeout_seconds}s"
                    task.completed_at = _time_module.time()

        return results

    def _build_execution_fn(
        self, agent: Optional[SubagentDefinition]
    ) -> Callable[[DelegationTask], Dict[str, Any]]:
        """Build a simulated execution function for a given agent.

        In production, this would dispatch to an LLM or command executor.
        Here it simulates the execution with a brief delay and returns
        a structured result reflecting the agent's capabilities.

        Args:
            agent: The agent definition to build the function for.

        Returns:
            A callable that takes a DelegationTask and returns a result dict.
        """
        def _execute(task: DelegationTask) -> Dict[str, Any]:
            _time_module.sleep(0.05)
            agent_name = agent.name if agent else "unknown"
            return {
                "task_id": task.id,
                "agent_name": agent_name,
                "agent_role": agent.role.value if agent else "unknown",
                "output": f"[{agent_name} completed: {task.task_description[:100]}]",
                "confidence": 0.85,
                "execution_time_ms": 50.0,
            }
        return _execute

    # ------------------------------------------------------------------
    # Task cancellation
    # ------------------------------------------------------------------

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or in-progress task.

        Args:
            task_id: The ID of the task to cancel.

        Returns:
            True if the task was found and cancelled, False otherwise.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if task.status not in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                return False
            task.status = TaskStatus.CANCELLED
            task.completed_at = _time_module.time()
            if task.agent_id in self._workload:
                self._workload[task.agent_id] = max(
                    0, self._workload[task.agent_id] - 1
                )
            return True

    # ------------------------------------------------------------------
    # Agent workload
    # ------------------------------------------------------------------

    def get_agent_load(self, agent_id: str) -> Dict[str, Any]:
        """Check the current workload of a specific agent.

        Args:
            agent_id: The agent ID to query.

        Returns:
            A dictionary with load information, or an error if not found.
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return {"error": f"Agent {agent_id} not found", "load": 0}
            pending = sum(
                1 for t in self._tasks.values()
                if t.agent_id == agent_id and t.status in (
                    TaskStatus.PENDING, TaskStatus.IN_PROGRESS
                )
            )
            return {
                "agent_id": agent_id,
                "agent_name": agent.name,
                "role": agent.role.value,
                "current_load": self._workload.get(agent_id, 0),
                "pending_tasks": pending,
                "status": agent.status,
                "max_retries": agent.max_retries,
                "timeout_seconds": agent.timeout_seconds,
            }

    # ------------------------------------------------------------------
    # Result aggregation
    # ------------------------------------------------------------------

    def aggregate_results(
        self,
        task_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Merge results from multiple parallel tasks into a unified summary.

        If task_ids is provided, only those tasks are aggregated. Otherwise,
        all completed tasks are included.

        Args:
            task_ids: Optional list of specific task IDs to aggregate.

        Returns:
            A dictionary with aggregated summary and individual results.
        """
        with self._lock:
            if task_ids:
                tasks = [
                    self._tasks[tid] for tid in task_ids if tid in self._tasks
                ]
            else:
                tasks = [
                    t for t in self._tasks.values()
                    if t.status == TaskStatus.SUCCESS
                ]

            if not tasks:
                return {"total": 0, "results": [], "summary": "No completed tasks to aggregate"}

            successes = [t for t in tasks if t.status == TaskStatus.SUCCESS]
            failures = [t for t in tasks if t.status == TaskStatus.FAILED]
            timed_out = [t for t in tasks if t.status == TaskStatus.TIMED_OUT]

            combined_output: List[str] = []
            for t in successes:
                output_text = t.result_json.get("output", "")
                if output_text:
                    combined_output.append(output_text)

            avg_confidence = 0.0
            confidences = [
                t.result_json.get("confidence", 0.0)
                for t in successes
                if "confidence" in t.result_json
            ]
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)

            return {
                "total": len(tasks),
                "success_count": len(successes),
                "failure_count": len(failures),
                "timed_out_count": len(timed_out),
                "average_confidence": round(avg_confidence, 3),
                "combined_output": "\n---\n".join(combined_output),
                "results": [t.to_dict() for t in tasks],
                "summary": (
                    f"Aggregated {len(tasks)} tasks: "
                    f"{len(successes)} succeeded, "
                    f"{len(failures)} failed, "
                    f"{len(timed_out)} timed out"
                ),
            }

    # ------------------------------------------------------------------
    # Pipeline workflow orchestration
    # ------------------------------------------------------------------

    def coordinate_workflow(
        self,
        workflow_name: str,
        task_description: str,
        context_json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Orchestrate a multi-agent workflow with pipeline stages.

        The pipeline flows through three sequential stages:
          1. PLANNER   - decomposes the task and creates a plan
          2. EXECUTOR  - executes the plan and produces output
          3. REVIEWER  - reviews the output and provides feedback

        Output from each stage is fed as input context to the next stage,
        creating a cohesive pipeline where each agent builds on prior work.

        Args:
            workflow_name: A name for this workflow instance.
            task_description: The high-level task to complete.
            context_json: Optional initial context for the planner.

        Returns:
            A dictionary with the full pipeline results and trace.
        """
        ctx = context_json or {}

        # Stage 1: Planner
        planner = self._find_agent_by_role(AgentRole.PLANNER)
        planner_task = self.assign_task(
            task_description=f"Plan: {task_description}",
            context_json={**ctx, "stage": "planning", "workflow": workflow_name},
            strategy=DelegationStrategy.FIRST_AVAILABLE,
            parent_session_id=workflow_name,
        ) if planner else None

        plan_output: Dict[str, Any] = {"plan": "No planner available", "steps": []}
        if planner_task and planner:
            with self._lock:
                planner_task.status = TaskStatus.IN_PROGRESS
            execution_fn = self._build_execution_fn(planner)
            try:
                plan_output = execution_fn(planner_task)
                plan_output["plan"] = f"Decomposed '{task_description}' into sub-steps"
                plan_output["steps"] = [
                    f"Analyze requirements for: {task_description[:60]}",
                    f"Design solution approach",
                    f"Prepare implementation strategy",
                ]
                with self._lock:
                    planner_task.status = TaskStatus.SUCCESS
                    planner_task.result_json = plan_output
                    planner_task.completed_at = _time_module.time()
            except Exception as exc:
                with self._lock:
                    planner_task.status = TaskStatus.FAILED
                    planner_task.error_message = str(exc)

        # Stage 2: Executor
        executor = self._find_agent_by_role(AgentRole.EXECUTOR)
        executor_ctx = {**ctx, "plan": plan_output, "stage": "execution", "workflow": workflow_name}
        executor_task = self.assign_task(
            task_description=f"Execute: {task_description}",
            context_json=executor_ctx,
            strategy=DelegationStrategy.FIRST_AVAILABLE,
            parent_session_id=workflow_name,
        ) if executor else None

        exec_output: Dict[str, Any] = {"result": "No executor available"}
        if executor_task and executor:
            with self._lock:
                executor_task.status = TaskStatus.IN_PROGRESS
            execution_fn = self._build_execution_fn(executor)
            try:
                exec_output = execution_fn(executor_task)
                exec_output["result"] = f"Executed plan for '{task_description[:80]}'"
                exec_output["artifacts"] = [f"Implementation of: {task_description[:60]}"]
                with self._lock:
                    executor_task.status = TaskStatus.SUCCESS
                    executor_task.result_json = exec_output
                    executor_task.completed_at = _time_module.time()
            except Exception as exc:
                with self._lock:
                    executor_task.status = TaskStatus.FAILED
                    executor_task.error_message = str(exc)

        # Stage 3: Reviewer
        reviewer = self._find_agent_by_role(AgentRole.REVIEWER)
        reviewer_ctx = {
            **ctx,
            "plan": plan_output,
            "execution_result": exec_output,
            "stage": "review",
            "workflow": workflow_name,
        }
        reviewer_task = self.assign_task(
            task_description=f"Review: {task_description}",
            context_json=reviewer_ctx,
            strategy=DelegationStrategy.FIRST_AVAILABLE,
            parent_session_id=workflow_name,
        ) if reviewer else None

        review_output: Dict[str, Any] = {"feedback": "No reviewer available", "approved": False}
        if reviewer_task and reviewer:
            with self._lock:
                reviewer_task.status = TaskStatus.IN_PROGRESS
            execution_fn = self._build_execution_fn(reviewer)
            try:
                review_output = execution_fn(reviewer_task)
                review_output["feedback"] = f"Reviewed output for '{task_description[:80]}'"
                review_output["approved"] = True
                review_output["suggestions"] = ["Consider edge cases", "Add error handling"]
                with self._lock:
                    reviewer_task.status = TaskStatus.SUCCESS
                    reviewer_task.result_json = review_output
                    reviewer_task.completed_at = _time_module.time()
            except Exception as exc:
                with self._lock:
                    reviewer_task.status = TaskStatus.FAILED
                    reviewer_task.error_message = str(exc)

        pipeline_trace = {
            "workflow_name": workflow_name,
            "task_description": task_description,
            "pipeline": ["planner", "executor", "reviewer"],
            "planner": plan_output,
            "executor": exec_output,
            "reviewer": review_output,
            "approved": review_output.get("approved", False),
            "completed_at": _time_module.time(),
        }
        with self._lock:
            self._pipeline_results.append(pipeline_trace)

        return pipeline_trace

    def _find_agent_by_role(self, role: AgentRole) -> Optional[SubagentDefinition]:
        """Find an idle agent with the specified role.

        Args:
            role: The AgentRole to search for.

        Returns:
            The first matching agent, or None.
        """
        with self._lock:
            for agent in self._agents.values():
                if agent.role == role and agent.status == "idle":
                    return agent
            return None

    # ------------------------------------------------------------------
    # Broker statistics
    # ------------------------------------------------------------------

    def get_broker_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the delegation broker.

        Returns aggregate counts for agents, tasks, workloads, and
        pipeline executions across the broker's entire lifetime.

        Returns:
            A dictionary with broker-wide statistics.
        """
        with self._lock:
            role_counts: Dict[str, int] = {}
            cap_counts: Dict[str, int] = {}
            for agent in self._agents.values():
                role_counts[agent.role.value] = role_counts.get(agent.role.value, 0) + 1
                for cap in agent.capabilities:
                    cap_counts[cap] = cap_counts.get(cap, 0) + 1

            status_counts: Dict[str, int] = {}
            for task in self._tasks.values():
                status_counts[task.status.value] = status_counts.get(task.status.value, 0) + 1

            total_load = sum(self._workload.values())
            avg_load = total_load / max(len(self._workload), 1)

            pipeline_count = len(self._pipeline_results)
            pipeline_approved = sum(
                1 for p in self._pipeline_results if p.get("approved", False)
            )

            return {
                "total_agents": len(self._agents),
                "total_registered": self._total_registered,
                "total_tasks_assigned": self._total_assigned,
                "total_tasks_completed": self._total_completed,
                "total_tasks_failed": self._total_failed,
                "agents_by_role": role_counts,
                "capability_distribution": cap_counts,
                "tasks_by_status": status_counts,
                "total_workload": total_load,
                "average_workload_per_agent": round(avg_load, 2),
                "pipelines_executed": pipeline_count,
                "pipelines_approved": pipeline_approved,
                "pipeline_approval_rate": (
                    pipeline_approved / max(pipeline_count, 1)
                ),
                "round_robin_index": self._round_robin_index,
            }

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive DelegationBroker subsystem statistics."""
        return {
            "total_agents": len(self._agents),
            "total_tasks": len(self._tasks),
            "tasks_by_status": {
                ts.value: sum(1 for t in self._tasks.values() if t.status == ts)
                for ts in TaskStatus
            },
            "agents_by_role": {
                ar.value: sum(1 for a in self._agents.values() if a.role == ar)
                for ar in AgentRole
            },
            "pipelines_executed": len(self._pipeline_results),
            "round_robin_index": self._round_robin_index,
        }


# ------------------------------------------------------------------
# Module-level accessor
# ------------------------------------------------------------------


def get_delegation_broker() -> DelegationBroker:
    """Return the singleton DelegationBroker instance."""
    return DelegationBroker.get_instance()