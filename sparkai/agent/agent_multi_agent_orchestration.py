"""
SparkLabs Agent - Multi-Agent Orchestration Engine

Coordinates specialized agent teams with role-based task assignment,
consensus-driven decision making, and parallel execution management.
Enables complex multi-agent workflows for AI-native game creation.

Architecture:
  MultiAgentOrchestrator
    |-- AgentTask (unit of work with role requirements)
    |-- OrchestrationSession (task collection with agent roster)
    |-- TaskDispatcher (role-matching assignment logic)
    |-- ConsensusEngine (agreement detection and resolution)
    |-- ProgressTracker (session state and milestone tracking)
    |-- DependencyResolver (task ordering and deadlock prevention)

Orchestration Roles:
  - COORDINATOR: manages workflow, assigns tasks
  - ANALYZER: inspects problems, identifies patterns
  - GENERATOR: produces creative output, code, assets
  - REVIEWER: validates quality, catches issues
  - TESTER: verifies behavior, runs checks
  - DEBUGGER: diagnoses and fixes problems
  - OPTIMIZER: improves performance, reduces waste
  - TRANSLATOR: converts between formats, bridges systems
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class OrchestrationRole(Enum):
    COORDINATOR = "coordinator"
    ANALYZER = "analyzer"
    GENERATOR = "generator"
    REVIEWER = "reviewer"
    TESTER = "tester"
    DEBUGGER = "debugger"
    OPTIMIZER = "optimizer"
    TRANSLATOR = "translator"


class TaskStatus(Enum):
    QUEUED = "queued"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    DELEGATED = "delegated"


class ConsensusMethod(Enum):
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_VOTE = "weighted_vote"
    RANKED_CHOICE = "ranked_choice"
    DELPHI_METHOD = "delphi_method"
    ADAPTIVE = "adaptive"


@dataclass
class AgentTask:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""
    role_required: OrchestrationRole = OrchestrationRole.GENERATOR
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.QUEUED
    assigned_agent: str = ""
    result: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "role_required": self.role_required.value,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "assigned_agent": self.assigned_agent,
            "result": self.result,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "retry_count": self.retry_count,
        }


@dataclass
class OrchestrationSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    goal_description: str = ""
    tasks: List[AgentTask] = field(default_factory=list)
    agents: Dict[str, OrchestrationRole] = field(default_factory=dict)
    consensus_method: ConsensusMethod = ConsensusMethod.MAJORITY_VOTE
    total_agents: int = 0
    active_task_count: int = 0
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal_description": self.goal_description,
            "task_count": len(self.tasks),
            "agent_count": len(self.agents),
            "total_agents": self.total_agents,
            "active_task_count": self.active_task_count,
            "consensus_method": self.consensus_method.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "tasks": [t.to_dict() for t in self.tasks],
            "agent_roles": {
                agent_id: role.value for agent_id, role in self.agents.items()
            },
        }


class MultiAgentOrchestrator:
    """
    Multi-agent orchestration engine for AI-native game creation.

    Coordinates specialized agent teams with role-based task assignment
    and consensus-driven decision making across complex workflows.
    """

    _instance: Optional[MultiAgentOrchestrator] = None

    @classmethod
    def get_instance(cls) -> MultiAgentOrchestrator:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._sessions: Dict[str, OrchestrationSession] = {}
        self._session_count: int = 0
        self._task_count: int = 0
        self._completed_task_count: int = 0
        self._failed_task_count: int = 0
        self._agent_pool: Dict[str, OrchestrationRole] = {}
        self._consensus_history: List[Dict[str, Any]] = []

    def create_session(
        self,
        goal: str,
        consensus_method: str = "majority_vote",
    ) -> OrchestrationSession:
        session = OrchestrationSession(
            goal_description=goal,
            consensus_method=ConsensusMethod(consensus_method),
        )
        self._sessions[session.id] = session
        self._session_count += 1
        return session

    def add_task(
        self,
        session_id: str,
        description: str,
        role: str,
        priority: int = 1,
        dependencies: Optional[List[str]] = None,
    ) -> str:
        session = self._sessions.get(session_id)
        if not session:
            return ""

        task = AgentTask(
            description=description,
            role_required=OrchestrationRole(role),
            priority=priority,
            dependencies=dependencies or [],
        )
        session.tasks.append(task)
        self._task_count += 1
        return task.id

    def assign_tasks(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        assignments: Dict[str, List[str]] = defaultdict(list)
        unassigned: List[str] = []

        for task in session.tasks:
            if task.status not in (TaskStatus.QUEUED, TaskStatus.FAILED):
                continue

            dep_unmet = False
            for dep_id in task.dependencies:
                dep_task = self._find_task_in_session(session, dep_id)
                if dep_task and dep_task.status != TaskStatus.COMPLETED:
                    dep_unmet = True
                    break

            if dep_unmet:
                unassigned.append(task.id)
                continue

            best_agent = self._find_agent_for_task(session, task)
            if best_agent:
                task.assigned_agent = best_agent
                task.status = TaskStatus.ASSIGNED
                assignments[best_agent].append(task.id)
            else:
                unassigned.append(task.id)

        return {
            "assigned": dict(assignments),
            "unassigned": unassigned,
            "total_assigned": sum(len(v) for v in assignments.values()),
            "total_unassigned": len(unassigned),
        }

    def execute_session(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        results: Dict[str, Any] = {
            "session_id": session_id,
            "goal": session.goal_description,
            "tasks_executed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "rounds": 0,
        }

        max_rounds = 10
        for round_idx in range(max_rounds):
            results["rounds"] = round_idx + 1

            assignments = self.assign_tasks(session_id)
            if assignments["total_assigned"] == 0 and assignments["total_unassigned"] == 0:
                break

            for task in session.tasks:
                if task.status == TaskStatus.ASSIGNED:
                    task.status = TaskStatus.IN_PROGRESS
                    task.started_at = time.time()
                    results["tasks_executed"] += 1

                    simulated_result = self._simulate_task_result(task)
                    task.result = simulated_result
                    task.completed_at = time.time()

                    if simulated_result.get("success", True):
                        task.status = TaskStatus.COMPLETED
                        results["tasks_completed"] += 1
                        self._completed_task_count += 1
                    else:
                        task.retry_count += 1
                        if task.retry_count < task.max_retries:
                            task.status = TaskStatus.QUEUED
                        else:
                            task.status = TaskStatus.FAILED
                            results["tasks_failed"] += 1
                            self._failed_task_count += 1

        session.completed_at = time.time()
        return results

    def collect_results(self, session_id: str) -> List[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if not session:
            return []

        return [
            {
                "task_id": task.id,
                "description": task.description,
                "role": task.role_required.value,
                "status": task.status.value,
                "result": task.result,
                "assigned_agent": task.assigned_agent,
                "duration": (
                    (task.completed_at - task.started_at)
                    if task.completed_at and task.started_at
                    else 0
                ),
            }
            for task in session.tasks
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
        ]

    def reach_consensus(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        opinions: Dict[str, Dict[str, Any]] = {}
        for task in session.tasks:
            if task.status == TaskStatus.COMPLETED:
                opinions[task.id] = {
                    "agent": task.assigned_agent,
                    "confidence": task.result.get("confidence", 0.7),
                    "verdict": task.result.get("verdict", "accept"),
                }

        if not opinions:
            return {"consensus": "no_data", "confidence": 0.0}

        accept_count = sum(
            1 for o in opinions.values() if o["verdict"] == "accept"
        )
        total = len(opinions)

        method = session.consensus_method
        if method == ConsensusMethod.MAJORITY_VOTE:
            passed = accept_count > total / 2
            confidence = accept_count / total
        elif method == ConsensusMethod.WEIGHTED_VOTE:
            weighted_accept = sum(
                o["confidence"] for o in opinions.values() if o["verdict"] == "accept"
            )
            weighted_total = sum(o["confidence"] for o in opinions.values())
            passed = weighted_accept > weighted_total / 2 if weighted_total > 0 else False
            confidence = weighted_accept / weighted_total if weighted_total > 0 else 0.0
        elif method == ConsensusMethod.RANKED_CHOICE:
            passed = accept_count >= total * 0.6
            confidence = accept_count / total
        elif method == ConsensusMethod.DELPHI_METHOD:
            confidences = [o["confidence"] for o in opinions.values()]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0
            passed = avg_conf >= 0.7
            confidence = avg_conf
        elif method == ConsensusMethod.ADAPTIVE:
            if total <= 3:
                passed = accept_count == total
                confidence = accept_count / total
            else:
                passed = accept_count > total / 2
                confidence = accept_count / total
        else:
            passed = accept_count > total / 2
            confidence = accept_count / total

        result = {
            "session_id": session_id,
            "consensus_method": method.value,
            "opinion_count": total,
            "accept_count": accept_count,
            "consensus_reached": passed,
            "confidence": round(confidence, 3),
            "opinions": opinions,
        }

        self._consensus_history.append(result)
        return result

    def get_session_progress(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        status_counts: Dict[str, int] = {}
        for task in session.tasks:
            status_counts[task.status.value] = status_counts.get(task.status.value, 0) + 1

        completed = status_counts.get("completed", 0)
        total = len(session.tasks)

        return {
            "session_id": session_id,
            "goal": session.goal_description,
            "total_tasks": total,
            "completed_tasks": completed,
            "failed_tasks": status_counts.get("failed", 0),
            "in_progress_tasks": status_counts.get("in_progress", 0),
            "queued_tasks": status_counts.get("queued", 0),
            "progress_percent": round((completed / total * 100) if total > 0 else 0, 1),
            "status_breakdown": status_counts,
            "elapsed_seconds": (
                time.time() - session.started_at if session.started_at else 0
            ),
        }

    def register_agent(
        self,
        agent_id: str,
        role: str,
    ) -> bool:
        self._agent_pool[agent_id] = OrchestrationRole(role)

        for session in self._sessions.values():
            if agent_id not in session.agents:
                session.agents[agent_id] = OrchestrationRole(role)
                session.total_agents = len(session.agents)

        return True

    def unregister_agent(self, agent_id: str) -> bool:
        if agent_id in self._agent_pool:
            del self._agent_pool[agent_id]
            return True
        return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if session:
            return session.to_dict()
        return None

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._sessions.values()]

    def _find_task_in_session(
        self, session: OrchestrationSession, task_id: str
    ) -> Optional[AgentTask]:
        for task in session.tasks:
            if task.id == task_id:
                return task
        return None

    def _find_agent_for_task(
        self, session: OrchestrationSession, task: AgentTask
    ) -> str:
        candidates = [
            (aid, role)
            for aid, role in session.agents.items()
            if role == task.role_required or role == OrchestrationRole.COORDINATOR
        ]

        if not candidates:
            for aid in session.agents:
                candidates.append((aid, session.agents[aid]))

        if not candidates:
            return ""

        best_agent = ""
        best_score = -1.0

        for agent_id, role in candidates:
            score = 0.0
            if role == task.role_required:
                score += 10.0
            elif role == OrchestrationRole.COORDINATOR:
                score += 3.0

            current_load = sum(
                1 for t in session.tasks
                if t.assigned_agent == agent_id and t.status == TaskStatus.IN_PROGRESS
            )
            score -= current_load * 2.0

            completed_by_agent = sum(
                1 for t in session.tasks
                if t.assigned_agent == agent_id and t.status == TaskStatus.COMPLETED
            )
            score += completed_by_agent * 0.5

            if score > best_score:
                best_score = score
                best_agent = agent_id

        return best_agent

    def _simulate_task_result(self, task: AgentTask) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "task_id": task.id,
            "output": f"Completed: {task.description[:50]}",
            "confidence": 0.7 + (task.priority * 0.05),
            "verdict": "accept",
            "success": True,
        }

        if task.retry_count > 0:
            result["retried"] = True
            result["confidence"] = max(0.3, result["confidence"] - 0.1 * task.retry_count)

        return result

    def get_stats(self) -> Dict[str, Any]:
        role_counts: Dict[str, int] = {}
        for role in self._agent_pool.values():
            role_counts[role.value] = role_counts.get(role.value, 0) + 1

        status_global: Dict[str, int] = {}
        for session in self._sessions.values():
            for task in session.tasks:
                status_global[task.status.value] = status_global.get(task.status.value, 0) + 1

        return {
            "total_sessions": self._session_count,
            "total_tasks": self._task_count,
            "completed_tasks": self._completed_task_count,
            "failed_tasks": self._failed_task_count,
            "success_rate": (
                self._completed_task_count / self._task_count
                if self._task_count > 0 else 0.0
            ),
            "agent_pool_size": len(self._agent_pool),
            "by_role": role_counts,
            "by_task_status": status_global,
            "available_roles": [r.value for r in OrchestrationRole],
            "available_methods": [m.value for m in ConsensusMethod],
            "consensus_rounds": len(self._consensus_history),
            "active_sessions": sum(
                1 for s in self._sessions.values() if s.completed_at is None
            ),
        }


def get_multi_agent_orchestrator() -> MultiAgentOrchestrator:
    return MultiAgentOrchestrator.get_instance()