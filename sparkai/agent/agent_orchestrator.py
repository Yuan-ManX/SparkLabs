"""
SparkAI Agent - Orchestrator Engine

A unified agent orchestration layer that coordinates all agents in the
SparkLabs AI-native game engine. Manages agent lifecycle, task routing,
inter-agent communication, and provides a single entry point for
complex multi-agent workflows.

Architecture:
  OrchestratorEngine
    |-- AgentDescriptor (agent capability registry)
    |-- OrchestratedTask (multi-agent task with routing)
    |-- AgentChannel (inter-agent message passing)
    |-- WorkflowPlan (multi-step agent workflow)
    |-- RoutingStrategy (task-to-agent assignment logic)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class AgentRole(Enum):
    DIRECTOR = "director"
    LEAD = "lead"
    SPECIALIST = "specialist"
    WORKER = "worker"
    OBSERVER = "observer"


class AgentCapability(Enum):
    CODE_GEN = "code_gen"
    WORLD_BUILD = "world_build"
    ASSET_GEN = "asset_gen"
    AUDIO_GEN = "audio_gen"
    NARRATIVE = "narrative"
    QA_TEST = "qa_test"
    DESIGN = "design"
    OPTIMIZATION = "optimization"
    REVIEW = "review"
    DEPLOY = "deploy"
    ANALYSIS = "analysis"
    DIALOGUE = "dialogue"
    VALIDATION = "validation"
    KNOWLEDGE = "knowledge"
    COORDINATION = "coordination"


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskStatus(Enum):
    QUEUED = "queued"
    ROUTED = "routed"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


class WorkflowState(Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ChannelType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    ESCALATION = "escalation"
    NOTIFICATION = "notification"


@dataclass
class AgentDescriptor:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    role: AgentRole = AgentRole.WORKER
    capabilities: Set[AgentCapability] = field(default_factory=set)
    max_concurrent_tasks: int = 3
    current_tasks: int = 0
    total_completed: int = 0
    total_failed: int = 0
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    specializations: List[str] = field(default_factory=list)
    blocked_tools: Set[str] = field(default_factory=set)
    allowed_tools: Optional[Set[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "capabilities": [c.value for c in self.capabilities],
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "current_tasks": self.current_tasks,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "avg_latency_ms": self.avg_latency_ms,
            "success_rate": self.success_rate,
            "specializations": self.specializations,
            "blocked_tools": list(self.blocked_tools),
            "available": self.current_tasks < self.max_concurrent_tasks,
            "registered_at": self.registered_at,
            "last_active": self.last_active,
        }


@dataclass
class AgentChannel:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    channel_type: ChannelType = ChannelType.REQUEST
    sender_id: str = ""
    receiver_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "channel_type": self.channel_type.value,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
        }


@dataclass
class OrchestratedTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    required_capabilities: Set[AgentCapability] = field(default_factory=set)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.QUEUED
    assigned_agent_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    sub_tasks: List[str] = field(default_factory=list)
    spawn_depth: int = 0
    max_spawn_depth: int = 3
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "required_capabilities": [c.value for c in self.required_capabilities],
            "priority": self.priority.value,
            "priority_name": self.priority.name,
            "status": self.status.value,
            "assigned_agent_id": self.assigned_agent_id,
            "parent_task_id": self.parent_task_id,
            "sub_tasks": self.sub_tasks,
            "error": self.error,
            "retries": self.retries,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class WorkflowStep:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    task_template: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    assigned_agent_id: Optional[str] = None
    task_id: Optional[str] = None
    status: TaskStatus = TaskStatus.QUEUED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "task_template": self.task_template,
            "depends_on": self.depends_on,
            "assigned_agent_id": self.assigned_agent_id,
            "task_id": self.task_id,
            "status": self.status.value,
        }


@dataclass
class WorkflowPlan:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    state: WorkflowState = WorkflowState.DRAFT
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "step_count": len(self.steps),
            "state": self.state.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class RoutingStrategy:
    """
    Assigns tasks to agents based on capability matching,
    load balancing, and success rate optimization.
    """

    def route(
        self,
        task: OrchestratedTask,
        agents: Dict[str, AgentDescriptor],
    ) -> Optional[str]:
        candidates: List[Tuple[str, float]] = []

        for agent_id, agent in agents.items():
            if agent.current_tasks >= agent.max_concurrent_tasks:
                continue

            if not task.required_capabilities.issubset(agent.capabilities):
                continue

            score = agent.success_rate * 10.0
            score += (1.0 - agent.current_tasks / max(agent.max_concurrent_tasks, 1)) * 5.0
            score -= agent.avg_latency_ms / 1000.0

            if agent.role == AgentRole.SPECIALIST:
                overlap = len(task.required_capabilities & agent.capabilities)
                score += overlap * 2.0

            candidates.append((agent_id, score))

        if not candidates:
            for agent_id, agent in agents.items():
                if agent.role == AgentRole.DIRECTOR:
                    return agent_id
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]


class OrchestratorEngine:
    """
    Central orchestration system for the SparkLabs AI-native game engine.

    Coordinates all agents, manages task routing, inter-agent communication,
    and provides a single entry point for complex multi-agent workflows.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, AgentDescriptor] = {}
        self._tasks: Dict[str, OrchestratedTask] = {}
        self._workflows: Dict[str, WorkflowPlan] = {}
        self._channels: List[AgentChannel] = []
        self._routing = RoutingStrategy()
        self._task_count: int = 0
        self._workflow_count: int = 0
        self._seed_agents()

    def _seed_agents(self) -> None:
        seed = [
            ("director_main", "Creative Director", AgentRole.DIRECTOR,
             {AgentCapability.COORDINATION, AgentCapability.DESIGN, AgentCapability.REVIEW}),
            ("director_tech", "Technical Director", AgentRole.DIRECTOR,
             {AgentCapability.COORDINATION, AgentCapability.CODE_GEN, AgentCapability.OPTIMIZATION}),
            ("lead_design", "Lead Designer", AgentRole.LEAD,
             {AgentCapability.DESIGN, AgentCapability.NARRATIVE, AgentCapability.DIALOGUE}),
            ("lead_code", "Lead Programmer", AgentRole.LEAD,
             {AgentCapability.CODE_GEN, AgentCapability.REVIEW, AgentCapability.VALIDATION}),
            ("lead_art", "Art Director", AgentRole.LEAD,
             {AgentCapability.ASSET_GEN, AgentCapability.DESIGN}),
            ("lead_qa", "QA Lead", AgentRole.LEAD,
             {AgentCapability.QA_TEST, AgentCapability.VALIDATION, AgentCapability.ANALYSIS}),
            ("spec_coder", "Gameplay Programmer", AgentRole.SPECIALIST,
             {AgentCapability.CODE_GEN, AgentCapability.WORLD_BUILD}),
            ("spec_world", "World Builder", AgentRole.SPECIALIST,
             {AgentCapability.WORLD_BUILD, AgentCapability.ASSET_GEN}),
            ("spec_audio", "Audio Designer", AgentRole.SPECIALIST,
             {AgentCapability.AUDIO_GEN}),
            ("spec_narrative", "Narrative Designer", AgentRole.SPECIALIST,
             {AgentCapability.NARRATIVE, AgentCapability.DIALOGUE}),
            ("spec_optimizer", "Performance Analyst", AgentRole.SPECIALIST,
             {AgentCapability.OPTIMIZATION, AgentCapability.ANALYSIS}),
            ("spec_knowledge", "Knowledge Curator", AgentRole.SPECIALIST,
             {AgentCapability.KNOWLEDGE, AgentCapability.ANALYSIS}),
        ]

        for aid, name, role, caps in seed:
            agent = AgentDescriptor(
                id=aid,
                name=name,
                role=role,
                capabilities=caps,
                max_concurrent_tasks=5 if role == AgentRole.WORKER else 3,
            )
            self._agents[aid] = agent

    def register_agent(
        self,
        name: str,
        role: str = "worker",
        capabilities: Optional[List[str]] = None,
        max_concurrent_tasks: int = 3,
        specializations: Optional[List[str]] = None,
    ) -> AgentDescriptor:
        caps = {AgentCapability(c) for c in (capabilities or [])}
        agent = AgentDescriptor(
            name=name,
            role=AgentRole(role),
            capabilities=caps,
            max_concurrent_tasks=max_concurrent_tasks,
            specializations=specializations or [],
        )
        self._agents[agent.id] = agent
        return agent

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        agent = self._agents.get(agent_id)
        if agent:
            return agent.to_dict()
        return None

    def list_agents(
        self,
        role: Optional[AgentRole] = None,
        capability: Optional[AgentCapability] = None,
    ) -> List[Dict[str, Any]]:
        agents = list(self._agents.values())
        if role:
            agents = [a for a in agents if a.role == role]
        if capability:
            agents = [a for a in agents if capability in a.capabilities]
        return [a.to_dict() for a in agents]

    def unregister_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def submit_task(
        self,
        name: str,
        description: str = "",
        required_capabilities: Optional[List[str]] = None,
        priority: str = "normal",
        input_data: Optional[Dict[str, Any]] = None,
        parent_task_id: Optional[str] = None,
    ) -> OrchestratedTask:
        caps = {AgentCapability(c) for c in (required_capabilities or [])}
        task = OrchestratedTask(
            name=name,
            description=description,
            required_capabilities=caps,
            priority=TaskPriority[priority.upper()],
            input_data=input_data or {},
            parent_task_id=parent_task_id,
        )
        self._tasks[task.id] = task
        self._task_count += 1

        agent_id = self._routing.route(task, self._agents)
        if agent_id:
            task.status = TaskStatus.ROUTED
            task.assigned_agent_id = agent_id
            self._agents[agent_id].current_tasks += 1
            self._agents[agent_id].last_active = time.time()
        else:
            task.status = TaskStatus.QUEUED

        return task

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
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
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if agent_id:
            tasks = [t for t in tasks if t.assigned_agent_id == agent_id]
        tasks.sort(key=lambda t: (t.priority.value, t.created_at))
        return [t.to_dict() for t in tasks[:limit]]

    def start_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        if not task:
            return None

        if task.status in (TaskStatus.QUEUED, TaskStatus.ROUTED, TaskStatus.ASSIGNED):
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            return task.to_dict()
        return None

    def complete_task(self, task_id: str, output_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        if not task:
            return None

        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.output_data = output_data or {}

        if task.assigned_agent_id and task.assigned_agent_id in self._agents:
            agent = self._agents[task.assigned_agent_id]
            agent.current_tasks = max(0, agent.current_tasks - 1)
            agent.total_completed += 1
            if task.started_at:
                latency = (task.completed_at - task.started_at) * 1000
                agent.avg_latency_ms = (agent.avg_latency_ms * (agent.total_completed - 1) + latency) / agent.total_completed
            agent.success_rate = agent.total_completed / max(agent.total_completed + agent.total_failed, 1)
            agent.last_active = time.time()

        return task.to_dict()

    def fail_task(self, task_id: str, error: str = "") -> Optional[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        if not task:
            return None

        task.retries += 1
        if task.retries < task.max_retries:
            task.status = TaskStatus.QUEUED
            task.assigned_agent_id = None
            agent_id = self._routing.route(task, self._agents)
            if agent_id:
                task.status = TaskStatus.ROUTED
                task.assigned_agent_id = agent_id
        else:
            task.status = TaskStatus.FAILED
            task.error = error
            task.completed_at = time.time()

            if task.assigned_agent_id and task.assigned_agent_id in self._agents:
                agent = self._agents[task.assigned_agent_id]
                agent.current_tasks = max(0, agent.current_tasks - 1)
                agent.total_failed += 1
                agent.success_rate = agent.total_completed / max(agent.total_completed + agent.total_failed, 1)

        return task.to_dict()

    def escalate_task(self, task_id: str, reason: str = "") -> Optional[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        if not task:
            return None

        task.status = TaskStatus.ESCALATED

        directors = [a for a in self._agents.values() if a.role == AgentRole.DIRECTOR]
        if directors:
            director = min(directors, key=lambda a: a.current_tasks)
            task.assigned_agent_id = director.id
            director.current_tasks += 1

        self._channels.append(AgentChannel(
            channel_type=ChannelType.ESCALATION,
            sender_id=task.assigned_agent_id or "system",
            receiver_id=task.assigned_agent_id or "",
            payload={"task_id": task_id, "reason": reason},
        ))

        return task.to_dict()

    def send_message(
        self,
        sender_id: str,
        receiver_id: str,
        payload: Dict[str, Any],
        channel_type: str = "request",
        correlation_id: str = "",
    ) -> AgentChannel:
        channel = AgentChannel(
            channel_type=ChannelType(channel_type),
            sender_id=sender_id,
            receiver_id=receiver_id,
            payload=payload,
            correlation_id=correlation_id,
        )
        self._channels.append(channel)
        return channel

    def get_messages(
        self,
        agent_id: Optional[str] = None,
        channel_type: Optional[ChannelType] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        messages = self._channels
        if agent_id:
            messages = [m for m in messages if m.sender_id == agent_id or m.receiver_id == agent_id]
        if channel_type:
            messages = [m for m in messages if m.channel_type == channel_type]
        return [m.to_dict() for m in messages[-limit:]]

    def create_workflow(
        self,
        name: str,
        description: str = "",
        steps: Optional[List[Dict[str, Any]]] = None,
    ) -> WorkflowPlan:
        workflow = WorkflowPlan(
            name=name,
            description=description,
        )

        if steps:
            name_to_id: Dict[str, str] = {}
            for step_data in steps:
                step = WorkflowStep(
                    name=step_data.get("name", ""),
                    task_template=step_data.get("task_template", {}),
                    depends_on=step_data.get("depends_on", []),
                )
                name_to_id[step.name] = step.id
                workflow.steps.append(step)

            for step in workflow.steps:
                resolved: List[str] = []
                for dep in step.depends_on:
                    if dep in name_to_id:
                        resolved.append(name_to_id[dep])
                    else:
                        resolved.append(dep)
                step.depends_on = resolved

        self._workflows[workflow.id] = workflow
        self._workflow_count += 1
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        workflow = self._workflows.get(workflow_id)
        if workflow:
            return workflow.to_dict()
        return None

    def list_workflows(self, state: Optional[WorkflowState] = None) -> List[Dict[str, Any]]:
        workflows = list(self._workflows.values())
        if state:
            workflows = [w for w in workflows if w.state == state]
        return [w.to_dict() for w in workflows]

    def execute_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        workflow.state = WorkflowState.RUNNING
        workflow.started_at = time.time()

        completed_step_ids: Set[str] = set()
        failed_step_ids: Set[str] = set()

        for step in workflow.steps:
            if any(dep in failed_step_ids for dep in step.depends_on):
                step.status = TaskStatus.FAILED
                failed_step_ids.add(step.id)
                continue

            if all(dep in completed_step_ids for dep in step.depends_on):
                template = step.task_template
                task = self.submit_task(
                    name=template.get("name", step.name),
                    description=template.get("description", ""),
                    required_capabilities=template.get("required_capabilities"),
                    priority=template.get("priority", "normal"),
                    input_data=template.get("input_data", {}),
                )
                step.task_id = task.id
                step.assigned_agent_id = task.assigned_agent_id

                self.start_task(task.id)

                agent = self._agents.get(task.assigned_agent_id) if task.assigned_agent_id else None
                if agent:
                    task_result = {
                        "task_id": task.id,
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "output": template.get("input_data", {}),
                        "confidence": 0.7,
                        "status": "completed",
                    }
                    self.complete_task(task.id, task_result)
                    step.status = TaskStatus.COMPLETED
                    completed_step_ids.add(step.id)
                else:
                    self.fail_task(task.id, "No agent available for task")
                    step.status = TaskStatus.FAILED
                    failed_step_ids.add(step.id)
            else:
                step.status = TaskStatus.FAILED
                failed_step_ids.add(step.id)

        if failed_step_ids:
            workflow.state = WorkflowState.FAILED
        else:
            workflow.state = WorkflowState.COMPLETED
        workflow.completed_at = time.time()
        return workflow.to_dict()

    def get_stats(self) -> Dict[str, Any]:
        role_counts: Dict[str, int] = {}
        cap_counts: Dict[str, int] = {}
        for agent in self._agents.values():
            role_counts[agent.role.value] = role_counts.get(agent.role.value, 0) + 1
            for cap in agent.capabilities:
                cap_counts[cap.value] = cap_counts.get(cap.value, 0) + 1

        status_counts: Dict[str, int] = {}
        for task in self._tasks.values():
            status_counts[task.status.value] = status_counts.get(task.status.value, 0) + 1

        return {
            "total_agents": len(self._agents),
            "total_tasks": self._task_count,
            "total_workflows": self._workflow_count,
            "total_messages": len(self._channels),
            "by_role": role_counts,
            "by_capability": cap_counts,
            "by_task_status": status_counts,
            "available_agents": sum(1 for a in self._agents.values() if a.current_tasks < a.max_concurrent_tasks),
        }


_global_orchestrator: Optional[OrchestratorEngine] = None


def get_orchestrator_engine() -> OrchestratorEngine:
    global _global_orchestrator
    if _global_orchestrator is None:
        _global_orchestrator = OrchestratorEngine()
    return _global_orchestrator
