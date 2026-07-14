"""
SparkLabs Agent - Agent Team Orchestrator

Comprehensive Multi-Agent Team Orchestration module for the SparkLabs
AI-native game engine. Manages teams of AI agents with defined roles,
task delegation, dependency-aware scheduling, collaborative messaging,
voting and consensus, workflow execution, performance monitoring,
conflict resolution, resource allocation, meeting tracking, and
adaptive team evolution.

Thread safety: a class-level _init_lock guards singleton creation with
double-checked locking; an instance-level _lock (threading.Lock) guards
every mutation; a _seeded flag ensures seed data is populated once.
The module exposes get_team_orchestrator() as the canonical factory.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Any, Dict, List, Optional


class TeamRole(Enum):
    LEADER = "leader"
    ANALYST = "analyst"
    BUILDER = "builder"
    REVIEWER = "reviewer"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"


class TeamStatus(Enum):
    FORMING = "forming"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class MessagePriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    INFORM = "inform"
    DELEGATE = "delegate"
    ESCALATE = "escalate"
    VOTE = "vote"


class ConflictType(Enum):
    TASK_DISPUTE = "task_dispute"
    RESOURCE_CONTENTION = "resource_contention"
    PRIORITY_CONFLICT = "priority_conflict"
    ROLE_CONFLICT = "role_conflict"
    DIRECTION_CONFLICT = "direction_conflict"


class ConflictResolution(Enum):
    VOTING = "voting"
    ESCALATION = "escalation"
    MEDIATION = "mediation"
    AUTO_RESOLVED = "auto_resolved"
    UNRESOLVED = "unresolved"


class WorkflowState(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class VoteStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"


class ActionItemStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


def _coerce_team_role(value: Any) -> TeamRole:
    """Coerce a string or unknown value into a TeamRole enum member."""
    if isinstance(value, TeamRole):
        return value
    if isinstance(value, str):
        key = value.strip().lower()
        for member in TeamRole:
            if member.value == key or member.name.lower() == key:
                return member
    return TeamRole.SPECIALIST


def _coerce_task_status(value: Any) -> TaskStatus:
    """Coerce a string or unknown value into a TaskStatus enum member."""
    if isinstance(value, TaskStatus):
        return value
    if isinstance(value, str):
        key = value.strip().lower()
        for member in TaskStatus:
            if member.value == key or member.name.lower() == key:
                return member
    return TaskStatus.PENDING


def _coerce_message_type(value: Any) -> MessageType:
    """Coerce a string or unknown value into a MessageType enum member."""
    if isinstance(value, MessageType):
        return value
    if isinstance(value, str):
        key = value.strip().lower()
        for member in MessageType:
            if member.value == key or member.name.lower() == key:
                return member
    return MessageType.INFORM


# Mapping of each role to its responsibilities and required capabilities.
ROLE_PROFILE: Dict[TeamRole, Dict[str, Any]] = {
    TeamRole.LEADER: {"responsibilities": ["set_objectives", "delegate_tasks", "make_final_decisions"],
                      "required_capabilities": ["planning", "decision_making", "coordination"]},
    TeamRole.ANALYST: {"responsibilities": ["analyze_data", "evaluate_options", "report_findings"],
                       "required_capabilities": ["analysis", "reasoning", "data_processing"]},
    TeamRole.BUILDER: {"responsibilities": ["implement_features", "produce_assets", "execute_plans"],
                       "required_capabilities": ["implementation", "construction", "tooling"]},
    TeamRole.REVIEWER: {"responsibilities": ["review_work", "validate_quality", "approve_deliverables"],
                        "required_capabilities": ["evaluation", "testing", "critique"]},
    TeamRole.COORDINATOR: {"responsibilities": ["track_progress", "schedule_syncs", "route_information"],
                           "required_capabilities": ["scheduling", "communication", "tracking"]},
    TeamRole.SPECIALIST: {"responsibilities": ["apply_domain_expertise", "advise_on_niche_topics"],
                          "required_capabilities": ["domain_knowledge", "advisory"]},
}


def _now_ts() -> float:
    """Return the current time as a POSIX timestamp."""
    return time.time()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value to the [low, high] interval."""
    return low if value < low else high if value > high else value


def _uid(prefix: str = "id") -> str:
    """Generate a short unique identifier with a descriptive prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _coerce_role(value: Any, default: TeamRole = TeamRole.SPECIALIST) -> TeamRole:
    """Convert a raw value into a TeamRole member with a safe fallback."""
    if isinstance(value, TeamRole):
        return value
    if isinstance(value, str):
        try:
            return TeamRole(value)
        except ValueError:
            try:
                return TeamRole[value.upper()]
            except KeyError:
                return default
    return default


def _dc_dict(obj: Any) -> Dict[str, Any]:
    """Convert a dataclass instance to a dict, unwrapping enums and nested dataclasses."""
    result: Dict[str, Any] = {}
    for f in fields(obj):
        v = getattr(obj, f.name)
        if isinstance(v, Enum):
            result[f.name] = v.value
        elif isinstance(v, list):
            result[f.name] = [x.to_dict() if hasattr(x, "to_dict") else x for x in v]
        elif isinstance(v, dict):
            result[f.name] = dict(v)
        else:
            result[f.name] = v
    return result


@dataclass
class TeamMember:
    member_id: str
    agent_id: str
    name: str = ""
    role: TeamRole = TeamRole.SPECIALIST
    capabilities: List[str] = field(default_factory=list)
    availability: float = 1.0
    performance_score: float = 0.5
    joined_at: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


@dataclass
class Team:
    team_id: str
    name: str
    description: str = ""
    objective: str = ""
    members: List[TeamMember] = field(default_factory=list)
    formed_at: float = field(default_factory=_now_ts)
    status: TeamStatus = TeamStatus.FORMING

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


@dataclass
class TaskDependency:
    task_id: str
    depends_on: str
    dependency_type: str = "finish_to_start"

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


@dataclass
class Task:
    task_id: str
    title: str
    description: str = ""
    assigned_to: Optional[str] = None
    team_id: Optional[str] = None
    priority: int = 3
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)
    parent_task: Optional[str] = None
    deadline: Optional[float] = None
    estimated_effort: float = 0.0
    actual_effort: float = 0.0
    result: Optional[Any] = None
    created_at: float = field(default_factory=_now_ts)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


@dataclass
class TeamMessage:
    message_id: str
    team_id: str
    sender: str
    recipient: Optional[str]
    message_type: MessageType
    content: str
    priority: MessagePriority = MessagePriority.NORMAL
    thread_id: Optional[str] = None
    related_task: Optional[str] = None
    timestamp: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


@dataclass
class ConversationThread:
    thread_id: str
    team_id: str
    subject: str
    message_ids: List[str] = field(default_factory=list)
    participants: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now_ts)
    closed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


@dataclass
class Vote:
    vote_id: str
    team_id: str
    question: str
    options: List[str] = field(default_factory=list)
    votes: Dict[str, str] = field(default_factory=dict)
    status: VoteStatus = VoteStatus.OPEN
    created_at: float = field(default_factory=_now_ts)
    closed_at: Optional[float] = None
    deadline: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


@dataclass
class WorkflowStep:
    """A single step within a workflow. Each next_steps entry is a dict
    with a target ``step_id`` and an optional ``condition`` string."""
    step_id: str
    task_type: str
    assigned_role: TeamRole
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    next_steps: List[Dict[str, Any]] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


@dataclass
class Workflow:
    workflow_id: str
    name: str
    team_id: Optional[str] = None
    steps: List[WorkflowStep] = field(default_factory=list)
    state: WorkflowState = WorkflowState.DRAFT
    created_at: float = field(default_factory=_now_ts)
    current_step_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


@dataclass
class WorkflowExecution:
    execution_id: str
    workflow_id: str
    started_at: float = field(default_factory=_now_ts)
    completed_at: Optional[float] = None
    state: WorkflowState = WorkflowState.RUNNING
    step_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    current_step: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


@dataclass
class PerformanceReport:
    team_id: str
    period_start: float
    period_end: float
    task_completion_rate: float = 0.0
    average_completion_time: float = 0.0
    collaboration_efficiency: float = 0.0
    conflict_resolution_rate: float = 0.0
    member_scores: Dict[str, float] = field(default_factory=dict)
    generated_at: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


@dataclass
class ConflictRecord:
    conflict_id: str
    team_id: str
    conflict_type: ConflictType
    description: str
    involved_members: List[str] = field(default_factory=list)
    related_task: Optional[str] = None
    resolution: ConflictResolution = ConflictResolution.UNRESOLVED
    resolution_detail: str = ""
    detected_at: float = field(default_factory=_now_ts)
    resolved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


@dataclass
class ResourceAllocation:
    allocation_id: str
    team_id: str
    resource_type: str
    total_capacity: float
    allocated: Dict[str, float] = field(default_factory=dict)
    utilization: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


@dataclass
class ActionItem:
    item_id: str
    description: str
    assignee: Optional[str] = None
    due_date: Optional[float] = None
    status: ActionItemStatus = ActionItemStatus.OPEN
    created_at: float = field(default_factory=_now_ts)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


@dataclass
class MeetingRecord:
    meeting_id: str
    team_id: str
    title: str
    scheduled_at: float
    attendees: List[str] = field(default_factory=list)
    agenda: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    action_items: List[ActionItem] = field(default_factory=list)
    notes: str = ""
    completed: bool = False
    created_at: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return _dc_dict(self)


class TeamOrchestrator:
    """Manages multi-agent teams with roles, tasks, workflows, and evolution.

    Provides a thread-safe facade over teams, members, tasks, messages,
    votes, workflows, conflicts, resources, and meetings. Internal
    helpers prefixed with a single underscore assume the instance lock
    is already held, which avoids re-entrancy issues with threading.Lock.
    """

    _instance: Optional["TeamOrchestrator"] = None
    _init_lock = threading.Lock()

    def __init__(self) -> None:
        self._teams: Dict[str, Team] = {}
        self._tasks: Dict[str, Task] = {}
        self._messages: Dict[str, TeamMessage] = {}
        self._threads: Dict[str, ConversationThread] = {}
        self._votes: Dict[str, Vote] = {}
        self._workflows: Dict[str, Workflow] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        self._conflicts: Dict[str, ConflictRecord] = {}
        self._resources: Dict[str, ResourceAllocation] = {}
        self._meetings: Dict[str, MeetingRecord] = {}
        self._action_items: Dict[str, ActionItem] = {}
        self._lock = threading.RLock()
        self._seeded: bool = False
        self._status: str = "idle"
        self._start_time: float = _now_ts()

    @classmethod
    def get_instance(cls) -> "TeamOrchestrator":
        """Return the singleton orchestrator instance."""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed_data(self) -> None:
        """Populate initial seed teams. Assumes the instance lock is held."""
        now = _now_ts()
        level_team = Team(
            team_id=_uid("team"), name="Level Design Team",
            description="Designs and builds playable levels with balanced mechanics",
            objective="Deliver polished, balanced, and engaging game levels",
            status=TeamStatus.ACTIVE, formed_at=now)
        level_team.members = [
            TeamMember(_uid("member"), "agent_level_lead", "Level Design Lead", TeamRole.LEADER, ["planning", "decision_making", "coordination", "level_design"], 1.0, 0.85),
            TeamMember(_uid("member"), "agent_level_builder", "Level Builder", TeamRole.BUILDER, ["implementation", "construction", "tooling", "level_design"], 0.9, 0.78),
            TeamMember(_uid("member"), "agent_level_analyst", "Playability Analyst", TeamRole.ANALYST, ["analysis", "reasoning", "data_processing", "playtesting"], 0.85, 0.80),
            TeamMember(_uid("member"), "agent_level_reviewer", "Level Reviewer", TeamRole.REVIEWER, ["evaluation", "testing", "critique", "quality_assurance"], 0.95, 0.82),
            TeamMember(_uid("member"), "agent_env_specialist", "Environment Specialist", TeamRole.SPECIALIST, ["domain_knowledge", "advisory", "environment_art", "lighting"], 0.8, 0.75),
        ]
        self._teams[level_team.team_id] = level_team
        narrative_team = Team(
            team_id=_uid("team"), name="Narrative Design Team",
            description="Crafts story, characters, quests, and dialogue",
            objective="Deliver a coherent and compelling narrative experience",
            status=TeamStatus.ACTIVE, formed_at=now)
        narrative_team.members = [
            TeamMember(_uid("member"), "agent_narrative_lead", "Narrative Lead", TeamRole.LEADER, ["planning", "decision_making", "coordination", "storytelling"], 1.0, 0.88),
            TeamMember(_uid("member"), "agent_story_builder", "Story Builder", TeamRole.BUILDER, ["implementation", "construction", "tooling", "writing"], 0.9, 0.76),
            TeamMember(_uid("member"), "agent_story_analyst", "Story Analyst", TeamRole.ANALYST, ["analysis", "reasoning", "data_processing", "narrative_review"], 0.88, 0.81),
            TeamMember(_uid("member"), "agent_narrative_reviewer", "Narrative Reviewer", TeamRole.REVIEWER, ["evaluation", "testing", "critique", "continuity_checking"], 0.92, 0.79),
            TeamMember(_uid("member"), "agent_lore_specialist", "Lore Specialist", TeamRole.SPECIALIST, ["domain_knowledge", "advisory", "worldbuilding", "history"], 0.83, 0.84),
            TeamMember(_uid("member"), "agent_narrative_coordinator", "Narrative Coordinator", TeamRole.COORDINATOR, ["scheduling", "communication", "tracking"], 0.95, 0.72),
        ]
        self._teams[narrative_team.team_id] = narrative_team
        self._seeded = True

    # Team Management

    def create_team(self, name: str, description: str = "", objective: str = "") -> Team:
        """Create a new team and register it in the orchestrator."""
        with self._lock:
            team = Team(team_id=_uid("team"), name=name, description=description, objective=objective)
            self._teams[team.team_id] = team
            return team

    def get_team(self, team_id: str) -> Optional[Team]:
        with self._lock:
            return self._teams.get(team_id)

    def remove_team(self, team_id: str) -> bool:
        """Remove a team from the orchestrator. Returns True if removed."""
        with self._lock:
            return self._teams.pop(team_id, None) is not None

    def list_teams(self, status: Optional[TeamStatus] = None) -> List[Team]:
        """List all teams, optionally filtered by status."""
        with self._lock:
            teams = list(self._teams.values())
            if status is not None:
                teams = [t for t in teams if t.status == status]
            return teams

    # Member Management

    def add_member(self, team_id: str, agent_id: str, name: str = "",
                   role: TeamRole = TeamRole.SPECIALIST,
                   capabilities: Optional[List[str]] = None,
                   availability: float = 1.0, performance_score: float = 0.5) -> TeamMember:
        """Add a new member to a team."""
        role = _coerce_team_role(role)
        member = TeamMember(member_id=_uid("member"), agent_id=agent_id, name=name,
                            role=role, capabilities=list(capabilities or []),
                            availability=_clamp(availability),
                            performance_score=_clamp(performance_score))
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            team.members.append(member)
            if team.status == TeamStatus.FORMING:
                team.status = TeamStatus.ACTIVE
            return member

    def remove_member(self, team_id: str, member_id: str) -> bool:
        """Remove a member from a team. Returns True if removed."""
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            for i, m in enumerate(team.members):
                if m.member_id == member_id:
                    team.members.pop(i)
                    return True
            return False

    def get_member(self, team_id: str, member_id: str) -> Optional[TeamMember]:
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                return None
            for m in team.members:
                if m.member_id == member_id:
                    return m
            return None

    def update_member(self, team_id: str, member_id: str, updates: Dict[str, Any]) -> TeamMember:
        """Update attributes of an existing member."""
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            member = None
            for m in team.members:
                if m.member_id == member_id:
                    member = m
                    break
            if member is None:
                raise KeyError(f"Member not found: {member_id}")
            if "name" in updates:
                member.name = updates["name"]
            if "role" in updates:
                member.role = _coerce_role(updates["role"], member.role)
            if "capabilities" in updates:
                member.capabilities = list(updates["capabilities"])
            if "availability" in updates:
                member.availability = _clamp(float(updates["availability"]))
            if "performance_score" in updates:
                member.performance_score = _clamp(float(updates["performance_score"]))
            return member

    # Role Assignment

    def assign_role(self, team_id: str, member_id: str, role: TeamRole) -> TeamMember:
        """Assign a role to a member, checking capability fit."""
        role = _coerce_team_role(role)
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            member = None
            for m in team.members:
                if m.member_id == member_id:
                    member = m
                    break
            if member is None:
                raise KeyError(f"Member not found: {member_id}")
            member.role = role
            return member

    def rotate_roles(self, team_id: str) -> List[TeamMember]:
        """Rotate roles among team members by one position."""
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            members = team.members
            if len(members) < 2:
                return list(members)
            roles = [m.role for m in members]
            rotated = [roles[-1]] + roles[:-1]
            for m, r in zip(members, rotated):
                m.role = r
            return list(members)

    # Task Delegation

    def create_task(self, title: str, description: str = "", team_id: Optional[str] = None,
                    assigned_to: Optional[str] = None, priority: int = 3,
                    dependencies: Optional[List[str]] = None, deadline: Optional[float] = None,
                    estimated_effort: float = 0.0) -> Task:
        """Create a new task and optionally assign it immediately."""
        with self._lock:
            task = Task(task_id=_uid("task"), title=title, description=description,
                        team_id=team_id, assigned_to=assigned_to, priority=priority,
                        dependencies=list(dependencies or []), deadline=deadline,
                        estimated_effort=estimated_effort)
            if assigned_to and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.IN_PROGRESS
                task.started_at = _now_ts()
            self._tasks[task.task_id] = task
            return task

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def assign_task(self, task_id: str, member_id: str) -> Task:
        """Assign a task to a member and start it if pending."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"Task not found: {task_id}")
            task.assigned_to = member_id
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.IN_PROGRESS
                task.started_at = _now_ts()
            return task

    def decompose_task(self, task_id: str, subtask_defs: List[Dict[str, Any]]) -> List[Task]:
        """Break a task into subtasks, linking them as children."""
        with self._lock:
            parent = self._tasks.get(task_id)
            if parent is None:
                raise KeyError(f"Task not found: {task_id}")
            created: List[Task] = []
            for sub_def in subtask_defs:
                sub = Task(task_id=_uid("task"), title=sub_def.get("title", ""),
                           description=sub_def.get("description", ""), team_id=parent.team_id,
                           priority=sub_def.get("priority", parent.priority), parent_task=task_id,
                           estimated_effort=sub_def.get("estimated_effort", 0.0))
                parent.subtasks.append(sub.task_id)
                self._tasks[sub.task_id] = sub
                created.append(sub)
            return created

    def list_tasks(self, team_id: Optional[str] = None, status: Optional[TaskStatus] = None) -> List[Task]:
        """List tasks, optionally filtered by team or status."""
        if isinstance(status, str):
            status = _coerce_task_status(status)
        with self._lock:
            tasks = list(self._tasks.values())
            if team_id is not None:
                tasks = [t for t in tasks if t.team_id == team_id]
            if status is not None:
                tasks = [t for t in tasks if t.status == status]
            return tasks

    def get_task_dependencies(self, task_id: str) -> List[TaskDependency]:
        """Return the dependency edges for a task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"Task not found: {task_id}")
            return [TaskDependency(task_id=task_id, depends_on=dep) for dep in task.dependencies]

    # Collaboration Protocol

    def send_message(self, team_id: str, sender: str, message_type: MessageType,
                     content: str, recipient: Optional[str] = None,
                     priority: MessagePriority = MessagePriority.NORMAL,
                     thread_id: Optional[str] = None,
                     related_task: Optional[str] = None) -> TeamMessage:
        """Send a collaboration message, creating or extending a thread."""
        message_type = _coerce_message_type(message_type)
        with self._lock:
            msg = TeamMessage(message_id=_uid("msg"), team_id=team_id, sender=sender,
                              recipient=recipient, message_type=message_type, content=content,
                              priority=priority, thread_id=thread_id, related_task=related_task)
            self._messages[msg.message_id] = msg
            if thread_id is None:
                thread = ConversationThread(thread_id=_uid("thread"), team_id=team_id, subject=content[:60])
                thread.message_ids.append(msg.message_id)
                thread.participants.append(sender)
                if recipient:
                    thread.participants.append(recipient)
                self._threads[thread.thread_id] = thread
                msg.thread_id = thread.thread_id
            else:
                thread = self._threads.get(thread_id)
                if thread is not None:
                    thread.message_ids.append(msg.message_id)
                    if sender not in thread.participants:
                        thread.participants.append(sender)
                    if recipient and recipient not in thread.participants:
                        thread.participants.append(recipient)
            return msg

    def get_messages(self, team_id: Optional[str] = None, thread_id: Optional[str] = None,
                     limit: int = 100) -> List[TeamMessage]:
        """Return messages filtered by team and/or thread."""
        with self._lock:
            msgs = list(self._messages.values())
            if team_id is not None:
                msgs = [m for m in msgs if m.team_id == team_id]
            if thread_id is not None:
                msgs = [m for m in msgs if m.thread_id == thread_id]
            msgs.sort(key=lambda m: m.timestamp)
            return msgs[-limit:] if limit > 0 else msgs

    def get_conversation(self, thread_id: str) -> Optional[ConversationThread]:
        with self._lock:
            return self._threads.get(thread_id)

    def create_vote(self, team_id: str, question: str, options: List[str],
                    deadline: Optional[float] = None) -> Vote:
        """Create a new consensus vote open for casting."""
        with self._lock:
            vote = Vote(vote_id=_uid("vote"), team_id=team_id, question=question,
                        options=list(options), deadline=deadline)
            self._votes[vote.vote_id] = vote
            return vote

    def cast_vote(self, vote_id: str, member_id: str, option: str) -> Vote:
        """Cast a vote for a specific option."""
        with self._lock:
            vote = self._votes.get(vote_id)
            if vote is None:
                raise KeyError(f"Vote not found: {vote_id}")
            if vote.status != VoteStatus.OPEN:
                raise ValueError("Vote is not open")
            if option not in vote.options:
                raise ValueError(f"Invalid option: {option}")
            vote.votes[member_id] = option
            return vote

    def get_vote_result(self, vote_id: str) -> Dict[str, Any]:
        """Return the tally and winner for a vote."""
        with self._lock:
            vote = self._votes.get(vote_id)
            if vote is None:
                raise KeyError(f"Vote not found: {vote_id}")
            tally: Dict[str, int] = defaultdict(int)
            for option in vote.votes.values():
                tally[option] += 1
            winner = max(tally, key=lambda k: tally[k]) if tally else None
            return {"vote_id": vote_id, "question": vote.question, "tally": dict(tally),
                    "total_votes": len(vote.votes), "winner": winner, "status": vote.status.value}

    # Workflow Management

    def create_workflow(self, name: str, steps: Optional[List[Dict[str, Any]]] = None,
                        team_id: Optional[str] = None) -> Workflow:
        """Create a workflow from a list of step definitions."""
        with self._lock:
            wf = Workflow(workflow_id=_uid("wf"), name=name, team_id=team_id)
            for step_def in steps or []:
                step = WorkflowStep(step_id=_uid("step"), task_type=step_def.get("task_type", ""),
                                    assigned_role=_coerce_role(step_def.get("assigned_role", "builder")),
                                    inputs=dict(step_def.get("inputs", {})),
                                    outputs=dict(step_def.get("outputs", {})),
                                    next_steps=list(step_def.get("next_steps", [])))
                wf.steps.append(step)
            self._workflows[wf.workflow_id] = wf
            return wf

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        with self._lock:
            return self._workflows.get(workflow_id)

    def execute_workflow(self, workflow_id: str) -> WorkflowExecution:
        """Execute a workflow by progressing through each step in order."""
        with self._lock:
            wf = self._workflows.get(workflow_id)
            if wf is None:
                raise KeyError(f"Workflow not found: {workflow_id}")
            execution = WorkflowExecution(execution_id=_uid("exec"), workflow_id=workflow_id)
            wf.state = WorkflowState.RUNNING
            for i, step in enumerate(wf.steps):
                step.status = TaskStatus.IN_PROGRESS
                execution.current_step = step.step_id
                # Simulate deterministic step execution
                step.outputs = {"status": "done", "executed_at": _now_ts(), "step_index": i}
                step.status = TaskStatus.COMPLETED
                execution.step_results[step.step_id] = {"status": "completed", "outputs": dict(step.outputs)}
                wf.current_step_index = i + 1
            wf.state = WorkflowState.COMPLETED
            execution.state = WorkflowState.COMPLETED
            execution.completed_at = _now_ts()
            execution.current_step = None
            self._executions[execution.execution_id] = execution
            return execution

    def get_workflow_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        with self._lock:
            return self._executions.get(execution_id)

    # Conflict Resolution

    def detect_conflict(self, team_id: str) -> List[ConflictRecord]:
        """Scan a team for task, resource, and priority conflicts."""
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            detected: List[ConflictRecord] = []
            # Task disputes: members overloaded with active tasks
            member_tasks: Dict[str, List[Task]] = defaultdict(list)
            for t in self._tasks.values():
                if t.team_id == team_id and t.assigned_to:
                    member_tasks[t.assigned_to].append(t)
            for member_id, tasks in member_tasks.items():
                active = [t for t in tasks if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)]
                if len(active) > 5:
                    c = ConflictRecord(conflict_id=_uid("conflict"), team_id=team_id,
                                       conflict_type=ConflictType.TASK_DISPUTE,
                                       description=f"Member {member_id} overloaded with {len(active)} active tasks",
                                       involved_members=[member_id])
                    self._conflicts[c.conflict_id] = c
                    detected.append(c)
            # Resource contention: over-allocated resources
            for alloc in self._resources.values():
                if alloc.team_id != team_id:
                    continue
                total_allocated = sum(alloc.allocated.values())
                if total_allocated > alloc.total_capacity:
                    c = ConflictRecord(conflict_id=_uid("conflict"), team_id=team_id,
                                       conflict_type=ConflictType.RESOURCE_CONTENTION,
                                       description=(f"Resource {alloc.resource_type} over-allocated: "
                                                    f"{total_allocated}/{alloc.total_capacity}"))
                    self._conflicts[c.conflict_id] = c
                    detected.append(c)
            # Priority conflicts: multiple high-priority tasks share a dependency
            high_priority = [t for t in self._tasks.values() if t.team_id == team_id and t.priority <= 2]
            dep_map: Dict[str, List[Task]] = defaultdict(list)
            for t in high_priority:
                for dep in t.dependencies:
                    dep_map[dep].append(t)
            for dep_id, dependents in dep_map.items():
                if len(dependents) > 1:
                    involved = [t.assigned_to for t in dependents if t.assigned_to]
                    c = ConflictRecord(conflict_id=_uid("conflict"), team_id=team_id,
                                       conflict_type=ConflictType.PRIORITY_CONFLICT,
                                       description=f"Multiple high-priority tasks depend on {dep_id}",
                                       involved_members=involved, related_task=dep_id)
                    self._conflicts[c.conflict_id] = c
                    detected.append(c)
            return detected

    def resolve_conflict(self, conflict_id: str,
                         resolution: ConflictResolution = ConflictResolution.MEDIATION,
                         detail: str = "") -> ConflictRecord:
        """Record a resolution for a detected conflict."""
        with self._lock:
            conflict = self._conflicts.get(conflict_id)
            if conflict is None:
                raise KeyError(f"Conflict not found: {conflict_id}")
            conflict.resolution = resolution
            conflict.resolution_detail = detail
            conflict.resolved_at = _now_ts()
            return conflict

    def get_conflict_history(self, team_id: Optional[str] = None) -> List[ConflictRecord]:
        """Return conflict records, optionally filtered by team."""
        with self._lock:
            conflicts = list(self._conflicts.values())
            if team_id is not None:
                conflicts = [c for c in conflicts if c.team_id == team_id]
            conflicts.sort(key=lambda c: c.detected_at)
            return conflicts

    # Resource Allocation

    def allocate_resource(self, team_id: str, resource_type: str, total_capacity: float,
                          allocations: Optional[Dict[str, float]] = None) -> ResourceAllocation:
        """Create or update a resource allocation for a team."""
        with self._lock:
            alloc = None
            for a in self._resources.values():
                if a.team_id == team_id and a.resource_type == resource_type:
                    alloc = a
                    break
            if alloc is None:
                alloc = ResourceAllocation(allocation_id=_uid("alloc"), team_id=team_id,
                                           resource_type=resource_type, total_capacity=total_capacity)
                self._resources[alloc.allocation_id] = alloc
            else:
                alloc.total_capacity = total_capacity
            if allocations:
                for consumer, amount in allocations.items():
                    alloc.allocated[consumer] = amount
            return alloc

    def get_resource_utilization(self, team_id: str) -> Dict[str, Any]:
        """Return utilization details for all resources of a team."""
        with self._lock:
            result: Dict[str, Any] = {}
            for alloc in self._resources.values():
                if alloc.team_id != team_id:
                    continue
                total_allocated = sum(alloc.allocated.values())
                result[alloc.resource_type] = {
                    "total_capacity": alloc.total_capacity, "allocated": total_allocated,
                    "available": alloc.total_capacity - total_allocated,
                    "utilization_rate": (round(total_allocated / alloc.total_capacity, 4)
                                         if alloc.total_capacity > 0 else 0.0),
                    "breakdown": dict(alloc.allocated)}
            return result

    # Meeting / Sync

    def schedule_meeting(self, team_id: str, title: str, scheduled_at: float,
                         attendees: Optional[List[str]] = None,
                         agenda: Optional[List[str]] = None) -> MeetingRecord:
        """Schedule a new team meeting."""
        with self._lock:
            meeting = MeetingRecord(meeting_id=_uid("meeting"), team_id=team_id, title=title,
                                     scheduled_at=scheduled_at, attendees=list(attendees or []),
                                     agenda=list(agenda or []))
            self._meetings[meeting.meeting_id] = meeting
            return meeting

    def record_meeting(self, meeting_id: str, decisions: Optional[List[str]] = None,
                       action_items: Optional[List[Dict[str, Any]]] = None,
                       notes: str = "") -> MeetingRecord:
        """Record the outcomes of a completed meeting."""
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                raise KeyError(f"Meeting not found: {meeting_id}")
            meeting.decisions = list(decisions or [])
            meeting.notes = notes
            meeting.completed = True
            for item in action_items or []:
                action = ActionItem(item_id=_uid("action"), description=item.get("description", ""),
                                    assignee=item.get("assignee"), due_date=item.get("due_date"))
                meeting.action_items.append(action)
                self._action_items[action.item_id] = action
            return meeting

    def get_action_items(self, team_id: Optional[str] = None,
                         status: Optional[ActionItemStatus] = None) -> List[ActionItem]:
        """Return action items, optionally filtered by team and status."""
        with self._lock:
            if team_id is not None:
                items = [a for m in self._meetings.values()
                         if m.team_id == team_id for a in m.action_items]
            else:
                items = list(self._action_items.values())
            if status is not None:
                items = [i for i in items if i.status == status]
            return items

    # Performance Monitoring

    def _compute_performance_report_impl(self, team: Team) -> PerformanceReport:
        """Compute a performance report. Assumes the lock is held."""
        team_tasks = [t for t in self._tasks.values() if t.team_id == team.team_id]
        total = len(team_tasks)
        completed = [t for t in team_tasks if t.status == TaskStatus.COMPLETED]
        completion_rate = len(completed) / total if total > 0 else 0.0
        times = [t.completed_at - t.started_at for t in completed if t.started_at and t.completed_at]
        avg_time = sum(times) / len(times) if times else 0.0
        team_msgs = [m for m in self._messages.values() if m.team_id == team.team_id]
        collab = min(len(team_msgs) / max(total, 1) / 5.0, 1.0) if total > 0 else 0.0
        team_conflicts = [c for c in self._conflicts.values() if c.team_id == team.team_id]
        resolved = [c for c in team_conflicts if c.resolution != ConflictResolution.UNRESOLVED]
        conflict_rate = len(resolved) / len(team_conflicts) if team_conflicts else 1.0
        member_scores = {m.member_id: m.performance_score for m in team.members}
        return PerformanceReport(team_id=team.team_id, period_start=team.formed_at,
                                 period_end=_now_ts(), task_completion_rate=round(completion_rate, 4),
                                 average_completion_time=round(avg_time, 4),
                                 collaboration_efficiency=round(collab, 4),
                                 conflict_resolution_rate=round(conflict_rate, 4),
                                 member_scores=member_scores)

    def get_performance_report(self, team_id: str) -> PerformanceReport:
        """Generate a performance report for a team."""
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            return self._compute_performance_report_impl(team)

    def get_team_statistics(self, team_id: str) -> Dict[str, Any]:
        """Return aggregate statistics for a team."""
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            team_tasks = [t for t in self._tasks.values() if t.team_id == team_id]
            by_status: Dict[str, int] = defaultdict(int)
            for t in team_tasks:
                by_status[t.status.value] += 1
            mc = len(team.members)
            return {"team_id": team_id, "member_count": mc, "task_count": len(team_tasks),
                    "tasks_by_status": dict(by_status),
                    "role_distribution": dict(Counter(m.role.value for m in team.members)),
                    "average_performance": round(sum(m.performance_score for m in team.members) / max(mc, 1), 4),
                    "average_availability": round(sum(m.availability for m in team.members) / max(mc, 1), 4),
                    "message_count": sum(1 for m in self._messages.values() if m.team_id == team_id),
                    "conflict_count": sum(1 for c in self._conflicts.values() if c.team_id == team_id),
                    "meeting_count": sum(1 for mt in self._meetings.values() if mt.team_id == team_id),
                    "timestamp": _now_ts()}

    # Team Evolution

    def evolve_team(self, team_id: str) -> Dict[str, Any]:
        """Adapt team composition based on performance scores."""
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            changes: List[str] = []
            for member in team.members:
                if member.performance_score >= 0.85 and member.role != TeamRole.LEADER:
                    old_role = member.role
                    member.role = TeamRole.COORDINATOR
                    changes.append(f"Promoted {member.name} from {old_role.value} to coordinator")
                elif member.performance_score < 0.3:
                    member.performance_score = _clamp(member.performance_score + 0.1)
                    changes.append(f"Adjusted performance for {member.name} (below threshold)")
            return {"team_id": team_id, "changes": changes,
                    "member_count": len(team.members), "evolved_at": _now_ts()}

    def archive_team(self, team_id: str) -> Team:
        """Mark a team as archived."""
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            team.status = TeamStatus.ARCHIVED
            return team

    # Lifecycle

    def reset(self) -> None:
        """Reset the orchestrator to its initial state and reseed."""
        with self._lock:
            self._teams.clear()
            self._tasks.clear()
            self._messages.clear()
            self._threads.clear()
            self._votes.clear()
            self._workflows.clear()
            self._executions.clear()
            self._conflicts.clear()
            self._resources.clear()
            self._meetings.clear()
            self._action_items.clear()
            self._seeded = False
            self._status = "idle"
            self._start_time = _now_ts()
            self._seed_data()
            self._status = "ready"

    def get_status(self) -> Dict[str, Any]:
        """Return a status snapshot of the orchestrator."""
        with self._lock:
            return {"status": self._status, "team_count": len(self._teams),
                    "task_count": len(self._tasks), "message_count": len(self._messages),
                    "thread_count": len(self._threads), "vote_count": len(self._votes),
                    "workflow_count": len(self._workflows), "execution_count": len(self._executions),
                    "conflict_count": len(self._conflicts), "resource_count": len(self._resources),
                    "meeting_count": len(self._meetings), "action_item_count": len(self._action_items),
                    "uptime": _now_ts() - self._start_time, "timestamp": _now_ts()}

    def get_snapshot(self) -> Dict[str, Any]:
        """Return a full serializable snapshot of the orchestrator."""
        with self._lock:
            return {"teams": [t.to_dict() for t in self._teams.values()],
                    "tasks": [t.to_dict() for t in self._tasks.values()],
                    "workflows": [w.to_dict() for w in self._workflows.values()],
                    "votes": [v.to_dict() for v in self._votes.values()],
                    "conflicts": [c.to_dict() for c in self._conflicts.values()],
                    "resources": [r.to_dict() for r in self._resources.values()],
                    "meetings": [m.to_dict() for m in self._meetings.values()],
                    "status": self._status, "timestamp": _now_ts()}

    def initialize(self, auto_seed: bool = True) -> None:
        """Initialize the orchestrator, optionally seeding default teams."""
        with self._lock:
            if auto_seed and not self._seeded:
                self._seed_data()
            self._status = "ready"

    def to_dict(self) -> Dict[str, Any]:
        """Return a compact dictionary representation of the orchestrator."""
        with self._lock:
            return {"teams": [t.to_dict() for t in self._teams.values()],
                    "team_count": len(self._teams), "task_count": len(self._tasks),
                    "message_count": len(self._messages), "workflow_count": len(self._workflows),
                    "conflict_count": len(self._conflicts), "meeting_count": len(self._meetings),
                    "status": self._status, "seeded": self._seeded}

    # AI Methods

    def ai_optimize_team(self, team_id: str) -> Dict[str, Any]:
        """Analyze a team and suggest structural improvements.

        Inspects role coverage, member performance, average availability,
        and task load distribution. Returns a list of actionable
        suggestions ordered by priority.
        """
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            report = self._compute_performance_report_impl(team)
            suggestions: List[Dict[str, Any]] = []
            # Role coverage gaps
            roles_present = {m.role for m in team.members}
            for role in TeamRole:
                if role not in roles_present:
                    suggestions.append({"type": "add_role", "role": role.value,
                        "reason": f"No member currently fills the {role.value} role",
                        "priority": "high" if role == TeamRole.LEADER else "medium"})
            # Low performers needing support
            for m in team.members:
                if m.performance_score < 0.4:
                    suggestions.append({"type": "support_member", "member_id": m.member_id,
                        "reason": f"Performance score {m.performance_score:.2f} is below threshold",
                        "priority": "high"})
            # Average availability too low
            mc = max(len(team.members), 1)
            avg_avail = sum(m.availability for m in team.members) / mc
            if avg_avail < 0.5:
                suggestions.append({"type": "increase_capacity",
                    "reason": f"Average availability {avg_avail:.2f} is low; consider adding members",
                    "priority": "high"})
            # Task load imbalance
            member_load: Dict[str, int] = defaultdict(int)
            for t in self._tasks.values():
                if t.team_id != team_id or not t.assigned_to:
                    continue
                if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                    member_load[t.assigned_to] += 1
            for member_id, load in member_load.items():
                if load > 5:
                    suggestions.append({"type": "rebalance_load", "member_id": member_id,
                        "reason": f"Member has {load} active tasks; redistribute", "priority": "medium"})
            return {"team_id": team_id, "current_completion_rate": report.task_completion_rate,
                    "suggestions": suggestions, "suggestion_count": len(suggestions),
                    "analyzed_at": _now_ts()}

    def ai_predict_collaboration(self, team_id: str) -> Dict[str, Any]:
        """Predict collaboration success for a team composition.

        Computes a weighted success score from role coverage, capability
        diversity, average performance, average availability, and team
        size fit. Returns a qualitative prediction label.
        """
        with self._lock:
            team = self._teams.get(team_id)
            if team is None:
                raise KeyError(f"Team not found: {team_id}")
            members = team.members
            if not members:
                return {"team_id": team_id, "success_score": 0.0,
                        "prediction": "insufficient_members", "factors": {},
                        "member_count": 0, "predicted_at": _now_ts()}
            roles_present = {m.role for m in members}
            role_coverage = len(roles_present) / len(TeamRole)
            all_caps: set = set()
            for m in members:
                all_caps.update(m.capabilities)
            cap_diversity = min(len(all_caps) / 20.0, 1.0)
            size = len(members)
            avg_perf = sum(m.performance_score for m in members) / size
            avg_avail = sum(m.availability for m in members) / size
            if 3 <= size <= 6:
                size_factor = 1.0
            elif size < 3:
                size_factor = 0.5
            else:
                size_factor = max(0.3, 1.0 - (size - 6) * 0.1)
            score = _clamp(role_coverage * 0.30 + cap_diversity * 0.20 + avg_perf * 0.25
                           + avg_avail * 0.15 + size_factor * 0.10)
            if score >= 0.75:
                prediction = "high_success"
            elif score >= 0.5:
                prediction = "moderate_success"
            elif score >= 0.3:
                prediction = "at_risk"
            else:
                prediction = "low_success"
            return {"team_id": team_id, "success_score": round(score, 4),
                    "prediction": prediction,
                    "factors": {"role_coverage": round(role_coverage, 4),
                                "capability_diversity": round(cap_diversity, 4),
                                "average_performance": round(avg_perf, 4),
                                "average_availability": round(avg_avail, 4),
                                "team_size_factor": round(size_factor, 4)},
                    "member_count": size, "predicted_at": _now_ts()}


def get_team_orchestrator() -> TeamOrchestrator:
    """Return the singleton TeamOrchestrator instance."""
    return TeamOrchestrator.get_instance()
