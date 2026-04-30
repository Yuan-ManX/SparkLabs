"""
SparkAI Agent - Agent Swarm

Collective intelligence system where multiple agents collaborate
through swarm coordination, emergent consensus, and distributed
problem decomposition.

Architecture:
  AgentSwarm
    |-- SwarmNode (individual agent in the swarm)
    |-- SwarmTask (decomposed work unit)
    |-- ConsensusEngine (agreement detection)
    |-- SwarmMemory (shared knowledge pool)
    |-- DecompositionStrategy (task splitting logic)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class SwarmRole(Enum):
    COORDINATOR = "coordinator"
    WORKER = "worker"
    EVALUATOR = "evaluator"
    INTEGRATOR = "integrator"


class SwarmState(Enum):
    IDLE = "idle"
    DECOMPOSING = "decomposing"
    DISPATCHING = "dispatching"
    EXECUTING = "executing"
    CONSENSUS = "consensus"
    INTEGRATING = "integrating"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskState(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    MERGED = "merged"


class ConsensusType(Enum):
    MAJORITY = "majority"
    UNANIMOUS = "unanimous"
    WEIGHTED = "weighted"
    QUORUM = "quorum"


class DecompositionStrategy(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    ADAPTIVE = "adaptive"


@dataclass
class SwarmNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    name: str = ""
    role: SwarmRole = SwarmRole.WORKER
    capabilities: List[str] = field(default_factory=list)
    capacity: int = 5
    current_load: int = 0
    reputation: float = 1.0
    contributions: int = 0
    successful_contributions: int = 0
    state: str = "available"
    last_active: float = field(default_factory=time.time)

    @property
    def is_available(self) -> bool:
        return self.current_load < self.capacity

    @property
    def success_rate(self) -> float:
        if self.contributions == 0:
            return 1.0
        return self.successful_contributions / self.contributions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value,
            "capabilities": self.capabilities,
            "capacity": self.capacity,
            "current_load": self.current_load,
            "reputation": self.reputation,
            "contributions": self.contributions,
            "successful_contributions": self.successful_contributions,
            "success_rate": self.success_rate,
            "state": self.state,
            "is_available": self.is_available,
        }


@dataclass
class SwarmTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    title: str = ""
    description: str = ""
    required_capabilities: List[str] = field(default_factory=list)
    priority: int = 2
    state: TaskState = TaskState.PENDING
    assigned_to: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    sub_tasks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    votes: Dict[str, bool] = field(default_factory=dict)
    confidence: float = 0.0
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "title": self.title,
            "description": self.description,
            "required_capabilities": self.required_capabilities,
            "priority": self.priority,
            "state": self.state.value,
            "assigned_to": self.assigned_to,
            "result": self.result,
            "sub_tasks": self.sub_tasks,
            "dependencies": self.dependencies,
            "votes": self.votes,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ConsensusResult:
    proposal_id: str
    consensus_type: ConsensusType
    total_voters: int
    yes_votes: int
    no_votes: int
    passed: bool
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "consensus_type": self.consensus_type.value,
            "total_voters": self.total_voters,
            "yes_votes": self.yes_votes,
            "no_votes": self.no_votes,
            "passed": self.passed,
            "confidence": self.confidence,
            "details": self.details,
        }


@dataclass
class SwarmMemoryEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    key: str = ""
    value: Any = None
    contributor: str = ""
    confidence: float = 1.0
    access_count: int = 0
    created_at: float = field(default_factory=time.time)


class ConsensusEngine:
    """
    Detects agreement among swarm participants using configurable
    consensus strategies.
    """

    def __init__(self, consensus_type: ConsensusType = ConsensusType.MAJORITY, quorum_size: int = 3):
        self._consensus_type = consensus_type
        self._quorum_size = quorum_size
        self._proposals: Dict[str, Dict[str, bool]] = {}
        self._results: List[ConsensusResult] = []

    def create_proposal(self, proposal_id: str) -> None:
        self._proposals[proposal_id] = {}

    def cast_vote(self, proposal_id: str, voter_id: str, vote: bool) -> None:
        if proposal_id not in self._proposals:
            self._proposals[proposal_id] = {}
        self._proposals[proposal_id][voter_id] = vote

    def evaluate(self, proposal_id: str) -> ConsensusResult:
        votes = self._proposals.get(proposal_id, {})
        yes_votes = sum(1 for v in votes.values() if v)
        no_votes = sum(1 for v in votes.values() if not v)
        total = yes_votes + no_votes

        if total == 0:
            return ConsensusResult(
                proposal_id=proposal_id,
                consensus_type=self._consensus_type,
                total_voters=0,
                yes_votes=0,
                no_votes=0,
                passed=False,
                confidence=0.0,
            )

        if self._consensus_type == ConsensusType.MAJORITY:
            passed = yes_votes > total / 2
        elif self._consensus_type == ConsensusType.UNANIMOUS:
            passed = yes_votes == total and total > 0
        elif self._consensus_type == ConsensusType.WEIGHTED:
            passed = yes_votes / total >= 0.6
        elif self._consensus_type == ConsensusType.QUORUM:
            passed = total >= self._quorum_size and yes_votes > total / 2
        else:
            passed = yes_votes > total / 2

        confidence = yes_votes / total if total > 0 else 0.0

        result = ConsensusResult(
            proposal_id=proposal_id,
            consensus_type=self._consensus_type,
            total_voters=total,
            yes_votes=yes_votes,
            no_votes=no_votes,
            passed=passed,
            confidence=confidence,
        )
        self._results.append(result)
        return result

    def get_results(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._results[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._results)
        passed = sum(1 for r in self._results if r.passed)
        return {
            "consensus_type": self._consensus_type.value,
            "quorum_size": self._quorum_size,
            "total_proposals": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "avg_confidence": sum(r.confidence for r in self._results) / total if total > 0 else 0.0,
        }


class SwarmMemory:
    """
    Shared knowledge pool accessible to all swarm participants.
    Supports confidence-weighted retrieval and automatic decay.
    """

    def __init__(self, max_entries: int = 500):
        self._entries: Dict[str, SwarmMemoryEntry] = {}
        self._max_entries = max_entries
        self._access_log: List[Dict[str, Any]] = []

    def store(self, key: str, value: Any, contributor: str, confidence: float = 1.0) -> SwarmMemoryEntry:
        if key in self._entries:
            existing = self._entries[key]
            if confidence > existing.confidence:
                existing.value = value
                existing.contributor = contributor
                existing.confidence = confidence
            existing.access_count += 1
            return existing

        if len(self._entries) >= self._max_entries:
            oldest_key = min(self._entries, key=lambda k: self._entries[k].access_count)
            del self._entries[oldest_key]

        entry = SwarmMemoryEntry(
            key=key,
            value=value,
            contributor=contributor,
            confidence=confidence,
        )
        self._entries[key] = entry
        return entry

    def retrieve(self, key: str) -> Optional[SwarmMemoryEntry]:
        entry = self._entries.get(key)
        if entry:
            entry.access_count += 1
            self._access_log.append({"key": key, "accessor": "swarm", "timestamp": time.time()})
        return entry

    def search(self, query: str, limit: int = 10) -> List[SwarmMemoryEntry]:
        results = []
        query_lower = query.lower()
        for entry in self._entries.values():
            if query_lower in entry.key.lower() or (isinstance(entry.value, str) and query_lower in entry.value.lower()):
                results.append(entry)
        results.sort(key=lambda e: e.confidence * (1 + e.access_count * 0.1), reverse=True)
        return results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "max_entries": self._max_entries,
            "avg_confidence": sum(e.confidence for e in self._entries.values()) / len(self._entries) if self._entries else 0.0,
            "total_accesses": sum(e.access_count for e in self._entries.values()),
        }


class AgentSwarm:
    """
    Collective intelligence system for distributed problem-solving.

    Coordinates multiple agents as a swarm to decompose, execute,
    and integrate complex tasks through consensus-driven workflows.
    """

    def __init__(
        self,
        consensus_type: ConsensusType = ConsensusType.MAJORITY,
        decomposition_strategy: DecompositionStrategy = DecompositionStrategy.ADAPTIVE,
    ):
        self._nodes: Dict[str, SwarmNode] = {}
        self._tasks: Dict[str, SwarmTask] = {}
        self._consensus = ConsensusEngine(consensus_type)
        self._memory = SwarmMemory()
        self._decomposition_strategy = decomposition_strategy
        self._state = SwarmState.IDLE
        self._history: List[Dict[str, Any]] = []
        self._swarm_count: int = 0
        self._task_count: int = 0
        self._completed_count: int = 0
        self._failed_count: int = 0

    def register_node(
        self,
        agent_id: str,
        name: str = "",
        role: SwarmRole = SwarmRole.WORKER,
        capabilities: Optional[List[str]] = None,
        capacity: int = 5,
    ) -> SwarmNode:
        node = SwarmNode(
            agent_id=agent_id,
            name=name or agent_id,
            role=role,
            capabilities=capabilities or [],
            capacity=capacity,
        )
        self._nodes[node.id] = node
        self._swarm_count += 1
        return node

    def unregister_node(self, node_id: str) -> bool:
        if node_id in self._nodes:
            del self._nodes[node_id]
            return True
        return False

    def list_nodes(self, role: Optional[SwarmRole] = None) -> List[Dict[str, Any]]:
        nodes = list(self._nodes.values())
        if role:
            nodes = [n for n in nodes if n.role == role]
        return [n.to_dict() for n in nodes]

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        node = self._nodes.get(node_id)
        return node.to_dict() if node else None

    def decompose_task(
        self,
        title: str,
        description: str,
        required_capabilities: Optional[List[str]] = None,
        strategy: Optional[DecompositionStrategy] = None,
    ) -> List[SwarmTask]:
        strat = strategy or self._decomposition_strategy
        self._state = SwarmState.DECOMPOSING

        parent = SwarmTask(
            title=title,
            description=description,
            required_capabilities=required_capabilities or [],
        )
        self._tasks[parent.id] = parent
        self._task_count += 1

        sub_tasks = []
        if strat == DecompositionStrategy.SEQUENTIAL:
            phases = ["analysis", "design", "implementation", "verification"]
            for i, phase in enumerate(phases):
                task = SwarmTask(
                    parent_id=parent.id,
                    title=f"{phase.capitalize()} Phase",
                    description=f"Execute {phase} for: {title}",
                    required_capabilities=required_capabilities or [],
                    priority=2,
                    dependencies=[sub_tasks[i - 1].id] if i > 0 else [],
                )
                self._tasks[task.id] = task
                parent.sub_tasks.append(task.id)
                sub_tasks.append(task)
                self._task_count += 1

        elif strat == DecompositionStrategy.PARALLEL:
            aspects = ["core", "visual", "audio", "logic"]
            for aspect in aspects:
                task = SwarmTask(
                    parent_id=parent.id,
                    title=f"{aspect.capitalize()} Component",
                    description=f"Build {aspect} component for: {title}",
                    required_capabilities=[aspect],
                )
                self._tasks[task.id] = task
                parent.sub_tasks.append(task.id)
                sub_tasks.append(task)
                self._task_count += 1

        elif strat == DecompositionStrategy.HIERARCHICAL:
            levels = [
                ("architecture", ["structure", "patterns"]),
                ("implementation", ["core_logic", "systems", "content"]),
                ("polish", ["testing", "optimization"]),
            ]
            for level_name, parts in levels:
                for part in parts:
                    task = SwarmTask(
                        parent_id=parent.id,
                        title=f"{level_name}/{part}",
                        description=f"{level_name} - {part} for: {title}",
                        required_capabilities=[part],
                    )
                    self._tasks[task.id] = task
                    parent.sub_tasks.append(task.id)
                    sub_tasks.append(task)
                    self._task_count += 1

        elif strat == DecompositionStrategy.ADAPTIVE:
            complexity = len(required_capabilities or []) + len(description.split()) / 20
            if complexity < 3:
                for phase in ["plan", "execute", "verify"]:
                    task = SwarmTask(
                        parent_id=parent.id,
                        title=f"{phase.capitalize()}",
                        description=f"{phase} for: {title}",
                        required_capabilities=required_capabilities or [],
                    )
                    self._tasks[task.id] = task
                    parent.sub_tasks.append(task.id)
                    sub_tasks.append(task)
                    self._task_count += 1
            else:
                for phase in ["analyze", "design", "scaffold", "implement", "integrate", "verify"]:
                    task = SwarmTask(
                        parent_id=parent.id,
                        title=f"{phase.capitalize()} Phase",
                        description=f"{phase} for: {title}",
                        required_capabilities=required_capabilities or [],
                    )
                    self._tasks[task.id] = task
                    parent.sub_tasks.append(task.id)
                    sub_tasks.append(task)
                    self._task_count += 1

        self._state = SwarmState.DISPATCHING
        self._history.append({
            "event": "decompose",
            "parent_task": parent.id,
            "sub_task_count": len(sub_tasks),
            "strategy": strat.value,
            "timestamp": time.time(),
        })

        return [parent] + sub_tasks

    def dispatch_task(self, task_id: str) -> Optional[str]:
        task = self._tasks.get(task_id)
        if not task or task.state != TaskState.PENDING:
            return None

        for dep_id in task.dependencies:
            dep = self._tasks.get(dep_id)
            if dep and dep.state != TaskState.COMPLETED:
                return None

        best_node = self._find_best_node(task)
        if best_node:
            task.assigned_to = best_node.id
            task.state = TaskState.ASSIGNED
            best_node.current_load += 1
            best_node.state = "busy"
            self._state = SwarmState.EXECUTING
            return best_node.id
        return None

    async def execute_swarm_task(
        self,
        task_id: str,
        task_executor: Optional[Any] = None,
        strategy: str = "direct",
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a swarm task using the unified TaskExecutionEngine.

        Connects the swarm's task dispatch to actual agent execution
        with dependency-aware context passing.
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        for dep_id in task.dependencies:
            dep = self._tasks.get(dep_id)
            if dep and dep.state != TaskState.COMPLETED:
                return {"error": f"Dependency {dep_id} not completed"}

        best_node = self._find_best_node(task)
        if not best_node:
            return {"error": "No available node for task"}

        task.assigned_to = best_node.id
        task.state = TaskState.ASSIGNED
        best_node.current_load += 1
        best_node.state = "busy"
        self._state = SwarmState.EXECUTING

        if task_executor is not None:
            from sparkai.agent.agent_task_executor import ExecutionStrategy, TaskContext

            strategy_enum = ExecutionStrategy(strategy) if strategy in [s.value for s in ExecutionStrategy] else ExecutionStrategy.DIRECT

            prior_results = []
            for dep_id in task.dependencies:
                dep = self._tasks.get(dep_id)
                if dep and dep.result:
                    prior_results.append({
                        "agent": dep.assigned_to or "unknown",
                        "result": str(dep.result)[:200],
                    })

            context = TaskContext(
                overall_goal=task.description,
                prior_results=prior_results,
                parent_task_id=task.parent_id,
                metadata={"strategy": task.strategy.value if hasattr(task.strategy, 'value') else str(task.strategy)},
            )

            execution = task_executor.submit_execution(
                task_name=task.description[:100],
                task_description=task.description,
                agent_id=best_node.id,
                strategy=strategy_enum,
                context=context,
            )

            result = await task_executor.execute(execution.id)

            success = result.status.value == "completed"
            self.complete_task(task_id, {"output": result.result, "confidence": result.confidence}, success)

            if success:
                best_node.reputation = min(1.0, best_node.reputation + 0.05)
            else:
                best_node.reputation = max(0.0, best_node.reputation - 0.1)

            return {
                "task_id": task_id,
                "node_id": best_node.id,
                "status": "completed" if success else "failed",
                "result": result.result,
                "confidence": result.confidence,
            }
        else:
            self.complete_task(task_id, {"output": "Dispatched (no executor)"}, True)
            return {"task_id": task_id, "node_id": best_node.id, "status": "dispatched"}

    def complete_task(self, task_id: str, result: Optional[Dict[str, Any]] = None, success: bool = True) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.result = result or {}
        task.completed_at = time.time()
        task.duration_ms = (task.completed_at - task.created_at) * 1000

        if success:
            task.state = TaskState.COMPLETED
            self._completed_count += 1
            if task.assigned_to:
                node = self._nodes.get(task.assigned_to)
                if node:
                    node.current_load = max(0, node.current_load - 1)
                    node.contributions += 1
                    node.successful_contributions += 1
                    node.reputation = min(2.0, node.reputation + 0.05)
                    if node.current_load == 0:
                        node.state = "available"
        else:
            task.state = TaskState.FAILED
            self._failed_count += 1
            if task.assigned_to:
                node = self._nodes.get(task.assigned_to)
                if node:
                    node.current_load = max(0, node.current_load - 1)
                    node.contributions += 1
                    node.reputation = max(0.1, node.reputation - 0.1)
                    if node.current_load == 0:
                        node.state = "available"

        self._history.append({
            "event": "complete",
            "task_id": task_id,
            "success": success,
            "duration_ms": task.duration_ms,
            "timestamp": time.time(),
        })

        parent = self._tasks.get(task.parent_id) if task.parent_id else None
        if parent:
            all_done = all(
                self._tasks.get(st_id) and self._tasks[st_id].state in (TaskState.COMPLETED, TaskState.FAILED)
                for st_id in parent.sub_tasks
            )
            if all_done:
                parent.state = TaskState.COMPLETED
                parent.completed_at = time.time()
                parent.duration_ms = (parent.completed_at - parent.created_at) * 1000
                self._state = SwarmState.COMPLETED

        return True

    def propose_consensus(self, proposal_id: str, voters: List[str], proposal_content: Optional[str] = None) -> ConsensusResult:
        self._state = SwarmState.CONSENSUS
        self._consensus.create_proposal(proposal_id)
        for voter in voters:
            node = self._nodes.get(voter)
            if node:
                if proposal_content:
                    node_capabilities = [str(c).lower() for c in node.capabilities]
                    content_lower = proposal_content.lower()
                    relevance = sum(1 for cap in node_capabilities if cap in content_lower)
                    relevance_score = min(1.0, relevance / 3.0) if node_capabilities else 0.5
                    vote = (node.reputation * 0.6 + relevance_score * 0.4) >= 0.5
                else:
                    vote = node.reputation >= 0.5
                self._consensus.cast_vote(proposal_id, voter, vote)
        result = self._consensus.evaluate(proposal_id)
        self._history.append({
            "event": "consensus",
            "proposal_id": proposal_id,
            "passed": result.passed,
            "confidence": result.confidence,
            "timestamp": time.time(),
        })
        return result

    def store_knowledge(self, key: str, value: Any, contributor: str, confidence: float = 1.0) -> Dict[str, Any]:
        entry = self._memory.store(key, value, contributor, confidence)
        return {"id": entry.id, "key": entry.key, "confidence": entry.confidence}

    def retrieve_knowledge(self, key: str) -> Optional[Dict[str, Any]]:
        entry = self._memory.retrieve(key)
        if entry:
            return {"key": entry.key, "value": entry.value, "confidence": entry.confidence, "contributor": entry.contributor}
        return None

    def search_knowledge(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        entries = self._memory.search(query, limit)
        return [{"key": e.key, "value": e.value, "confidence": e.confidence} for e in entries]

    def _find_best_node(self, task: SwarmTask) -> Optional[SwarmNode]:
        candidates = [n for n in self._nodes.values() if n.is_available]
        if not candidates:
            return None

        scored = []
        for node in candidates:
            score = 0.0
            cap_match = len(set(task.required_capabilities) & set(node.capabilities))
            score += cap_match * 10.0
            score += node.reputation * 5.0
            score += node.success_rate * 3.0
            if node.role == SwarmRole.COORDINATOR:
                score += 2.0
            remaining = node.capacity - node.current_load
            score += remaining * 1.0
            scored.append((node, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0] if scored else None

    def get_topology(self) -> Dict[str, Any]:
        return {
            "node_count": len(self._nodes),
            "available_nodes": sum(1 for n in self._nodes.values() if n.is_available),
            "busy_nodes": sum(1 for n in self._nodes.values() if not n.is_available),
            "by_role": {r.value: sum(1 for n in self._nodes.values() if n.role == r) for r in SwarmRole},
            "task_count": len(self._tasks),
            "pending_tasks": sum(1 for t in self._tasks.values() if t.state == TaskState.PENDING),
            "running_tasks": sum(1 for t in self._tasks.values() if t.state in (TaskState.ASSIGNED, TaskState.RUNNING)),
            "completed_tasks": sum(1 for t in self._tasks.values() if t.state == TaskState.COMPLETED),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "total_nodes": len(self._nodes),
            "total_tasks": self._task_count,
            "completed_tasks": self._completed_count,
            "failed_tasks": self._failed_count,
            "success_rate": self._completed_count / self._task_count if self._task_count > 0 else 0.0,
            "consensus": self._consensus.get_stats(),
            "memory": self._memory.get_stats(),
            "decomposition_strategy": self._decomposition_strategy.value,
        }

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._history[-limit:]


_swarm: Optional[AgentSwarm] = None


def get_agent_swarm() -> AgentSwarm:
    global _swarm
    if _swarm is None:
        _swarm = AgentSwarm()
    return _swarm
