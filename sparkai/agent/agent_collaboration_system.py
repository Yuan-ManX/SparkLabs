"""
SparkLabs Agent - Multi-Agent Collaboration System

Coordinates multiple specialized AI agents working together simultaneously
on different aspects of game creation. Manages shared workspaces, task
delegation protocols, message passing, conflict resolution, and session
lifecycle across collaborative game development workflows.

Architecture:
    CollaborationSystem (singleton)
      |-- CollaborationAgent (specialized worker with role and skills)
      |-- CollaborationMessage (inter-agent communication)
      |-- SharedTask (decomposed work unit with dependencies)
      |-- CollaborationSession (shared workspace with agents, tasks, messages)

Collaboration Modes:
    - SEQUENTIAL: agents work one after another in a defined order
    - PARALLEL: agents work simultaneously on independent sub-tasks
    - ITERATIVE: agents alternate rounds of work and feedback
    - CONSENSUS: agents vote on proposals before proceeding
    - LEADER_FOLLOWER: lead agent assigns work to follower agents

Agent Roles:
    - GAME_DESIGNER: overall game vision, mechanics, and rules
    - LEVEL_DESIGNER: spatial layout, encounters, and pacing
    - NARRATIVE_DESIGNER: story arcs, character development, dialogue
    - SYSTEM_DESIGNER: core systems, economy, progression models
    - UI_DESIGNER: user interface layout, HUD, menu flows
    - AUDIO_DESIGNER: sound effects, music, ambient audio
    - BALANCE_DESIGNER: tuning, difficulty curves, fairness analysis
    - QA_TESTER: testing, bug reporting, quality validation

Usage:
    cs = get_collaboration_system()
    session = cs.create_session("RPG Boss Fight", CollaborationMode.PARALLEL)
    agent = cs.register_agent(session.session_id, "designer_1",
                              "Alice", AgentRole.GAME_DESIGNER,
                              ["combat_design", "boss_mechanics"])
    task = cs.assign_task(session.session_id, "Design Boss AI",
                          "Create behavior tree for the dragon boss",
                          ["designer_1", "designer_2"])
    msg = cs.send_message(session.session_id, "designer_1", "designer_2",
                          MessageType.QUESTION, "What phase transitions?")
    report = cs.generate_collaboration_report(session.session_id)
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

_time_module = time


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------


class AgentRole(Enum):
    """Specialized roles agents can fulfill in game creation collaboration."""

    GAME_DESIGNER = "game_designer"
    LEVEL_DESIGNER = "level_designer"
    NARRATIVE_DESIGNER = "narrative_designer"
    SYSTEM_DESIGNER = "system_designer"
    UI_DESIGNER = "ui_designer"
    AUDIO_DESIGNER = "audio_designer"
    BALANCE_DESIGNER = "balance_designer"
    QA_TESTER = "qa_tester"


class CollaborationMode(Enum):
    """Execution modes determining how agents coordinate their work."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ITERATIVE = "iterative"
    CONSENSUS = "consensus"
    LEADER_FOLLOWER = "leader_follower"


class MessageType(Enum):
    """Types of inter-agent messages for structured communication."""

    PROPOSAL = "proposal"
    FEEDBACK = "feedback"
    APPROVAL = "approval"
    REJECTION = "rejection"
    TASK_ASSIGNMENT = "task_assignment"
    STATUS_UPDATE = "status_update"
    QUESTION = "question"
    ANSWER = "answer"


class AgentStatus(Enum):
    """Runtime status of a collaboration agent."""

    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class TaskStatus(Enum):
    """Lifecycle states for a shared task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class CollaborationAgent:
    """A specialized AI agent participating in a collaboration session.

    Each agent has a unique ID, designated role, skill set, and tracks
    its current task assignment alongside a history of completed work.
    """

    agent_id: str = ""
    name: str = ""
    role: AgentRole = AgentRole.GAME_DESIGNER
    status: AgentStatus = AgentStatus.IDLE
    skills: List[str] = field(default_factory=list)
    current_task: Optional[str] = None
    task_history: Deque[str] = field(default_factory=lambda: deque(maxlen=100))
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value,
            "status": self.status.value,
            "skills": self.skills,
            "current_task": self.current_task,
            "task_history": list(self.task_history),
            "tasks_completed": len(self.task_history),
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def record_task_completion(self, task_id: str) -> None:
        """Add a task ID to the agent's completion history."""
        self.task_history.append(task_id)


@dataclass
class CollaborationMessage:
    """A structured message between two agents within a session.

    Messages carry typed content with optional context and can reference
    related messages to form conversation threads and decision chains.
    """

    message_id: str = ""
    sender_id: str = ""
    receiver_id: str = ""
    message_type: MessageType = MessageType.STATUS_UPDATE
    content: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)
    references: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type.value,
            "content": self.content[:500],
            "context": self.context,
            "timestamp": self.timestamp,
            "references": self.references,
            "reference_count": len(self.references),
        }


@dataclass
class SharedTask:
    """A unit of work shared across one or more agents in a session.

    Tasks track assigned agents, priority, dependencies on other tasks,
    and produced artifacts. They flow through a lifecycle from pending
    through in-progress to completion or rejection.
    """

    task_id: str = ""
    title: str = ""
    description: str = ""
    assigned_agents: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description[:300],
            "assigned_agents": self.assigned_agents,
            "assignee_count": len(self.assigned_agents),
            "status": self.status.value,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "dependency_count": len(self.dependencies),
            "artifacts": self.artifacts,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "duration_seconds": (
                round(self.completed_at - self.created_at, 2)
                if self.completed_at else None
            ),
        }

    @property
    def is_blocked(self) -> bool:
        return self.status == TaskStatus.BLOCKED

    @property
    def is_active(self) -> bool:
        return self.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.UNDER_REVIEW)


@dataclass
class CollaborationSession:
    """A shared workspace binding agents, tasks, and messages together.

    Each session operates in a specific collaboration mode, maintains
    the roster of participating agents, the shared task board, and the
    full message history for inter-agent communication.
    """

    session_id: str = ""
    name: str = ""
    mode: CollaborationMode = CollaborationMode.PARALLEL
    agents: Dict[str, CollaborationAgent] = field(default_factory=dict)
    tasks: Dict[str, SharedTask] = field(default_factory=dict)
    messages: List[CollaborationMessage] = field(default_factory=list)
    workspace: Dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=_time_module.time)
    ended_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "mode": self.mode.value,
            "agent_count": len(self.agents),
            "agents": {aid: a.to_dict() for aid, a in self.agents.items()},
            "task_count": len(self.tasks),
            "tasks": {tid: t.to_dict() for tid, t in self.tasks.items()},
            "message_count": len(self.messages),
            "workspace_keys": list(self.workspace.keys()),
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": (
                round((self.ended_at or _time_module.time()) - self.started_at, 2)
            ),
            "metadata": self.metadata,
            "active_tasks": sum(
                1 for t in self.tasks.values()
                if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.UNDER_REVIEW)
            ),
            "completed_tasks": sum(
                1 for t in self.tasks.values()
                if t.status == TaskStatus.COMPLETED
            ),
            "blocked_tasks": sum(
                1 for t in self.tasks.values()
                if t.status == TaskStatus.BLOCKED
            ),
        }

    def get_agent_messages(self, agent_id: str) -> List[CollaborationMessage]:
        """Filter messages where the given agent is sender or receiver."""
        return [
            m for m in self.messages
            if m.sender_id == agent_id or m.receiver_id == agent_id
        ]

    def get_agent_tasks(self, agent_id: str) -> List[SharedTask]:
        """Get all tasks assigned to the given agent."""
        return [
            t for t in self.tasks.values()
            if agent_id in t.assigned_agents
        ]


# ------------------------------------------------------------------
# CollaborationSystem
# ------------------------------------------------------------------


class CollaborationSystem:
    """Singleton multi-agent collaboration system for AI-native game creation.

    Orchestrates sessions where multiple specialized AI agents collaborate
    on game design, development, and testing. Agents communicate via typed
    messages, share tasks with dependency tracking, and operate under
    configurable collaboration modes (sequential, parallel, iterative,
    consensus, leader-follower).

    Thread-safe via RLock. All public methods acquire the lock before
    reading or modifying internal state. Use get_collaboration_system()
    to obtain the singleton instance.
    """

    _instance: Optional["CollaborationSystem"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_SESSIONS = 200
    MAX_AGENTS_PER_SESSION = 50
    MAX_TASKS_PER_SESSION = 500
    MAX_MESSAGES_PER_SESSION = 2000
    MAX_MESSAGE_REFERENCES = 20

    def __new__(cls) -> "CollaborationSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._sessions: Dict[str, CollaborationSession] = {}
                    instance._global_agent_registry: Dict[str, Dict[str, Any]] = {}
                    instance._total_sessions_created: int = 0
                    instance._total_agents_registered: int = 0
                    instance._total_tasks_assigned: int = 0
                    instance._total_messages_sent: int = 0
                    instance._conflict_resolution_log: Deque[Dict[str, Any]] = deque(maxlen=200)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "CollaborationSystem":
        return cls()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(
        self,
        name: str,
        mode: CollaborationMode = CollaborationMode.PARALLEL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CollaborationSession:
        """Create a new collaboration session with the given name and mode.

        Args:
            name: Human-readable session name.
            mode: Collaboration mode for agent coordination.
            metadata: Optional key-value metadata for the session.

        Returns:
            The newly created CollaborationSession.

        Raises:
            RuntimeError: If the maximum session count is exceeded.
        """
        with self._lock:
            if len(self._sessions) >= self.MAX_SESSIONS:
                raise RuntimeError(
                    f"Maximum session count ({self.MAX_SESSIONS}) exceeded"
                )

            session_id = uuid.uuid4().hex
            session = CollaborationSession(
                session_id=session_id,
                name=name,
                mode=mode,
                metadata=metadata or {},
            )
            self._sessions[session_id] = session
            self._total_sessions_created += 1
            return session

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all collaboration sessions with summary information.

        Returns:
            A list of session summary dictionaries.
        """
        with self._lock:
            return [
                {
                    "session_id": s.session_id,
                    "name": s.name,
                    "mode": s.mode.value,
                    "agent_count": len(s.agents),
                    "task_count": len(s.tasks),
                    "message_count": len(s.messages),
                    "started_at": s.started_at,
                    "ended_at": s.ended_at,
                    "active": s.ended_at is None,
                }
                for s in self._sessions.values()
            ]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a full session by ID.

        Args:
            session_id: The session identifier.

        Returns:
            The session dictionary, or None if not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                return session.to_dict()
            return None

    def end_session(self, session_id: str) -> bool:
        """Mark a session as ended.

        Args:
            session_id: The session to end.

        Returns:
            True if the session was found and ended, False otherwise.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            if session.ended_at is not None:
                return False
            session.ended_at = _time_module.time()
            return True

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register_agent(
        self,
        session_id: str,
        agent_id: str,
        name: str,
        role: AgentRole = AgentRole.GAME_DESIGNER,
        skills: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CollaborationAgent:
        """Register a new agent into a collaboration session.

        Args:
            session_id: Target session identifier.
            agent_id: Unique agent identifier within the session.
            name: Human-readable agent name.
            role: The specialized role for this agent.
            skills: List of skill strings describing agent capabilities.
            metadata: Optional key-value metadata.

        Returns:
            The newly created CollaborationAgent.

        Raises:
            ValueError: If the session is not found or agent already exists.
            RuntimeError: If the maximum agents per session is exceeded.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise ValueError(f"Session not found: {session_id}")

            if agent_id in session.agents:
                raise ValueError(
                    f"Agent '{agent_id}' already registered in session '{session_id}'"
                )

            if len(session.agents) >= self.MAX_AGENTS_PER_SESSION:
                raise RuntimeError(
                    f"Maximum agents per session ({self.MAX_AGENTS_PER_SESSION}) exceeded"
                )

            agent = CollaborationAgent(
                agent_id=agent_id,
                name=name,
                role=role,
                skills=skills or [],
                metadata=metadata or {},
            )
            session.agents[agent_id] = agent

            if agent_id not in self._global_agent_registry:
                self._global_agent_registry[agent_id] = {
                    "name": name,
                    "roles_held": [role.value],
                    "sessions_joined": 1,
                    "total_tasks_assigned": 0,
                    "first_seen": _time_module.time(),
                }
            else:
                entry = self._global_agent_registry[agent_id]
                if role.value not in entry["roles_held"]:
                    entry["roles_held"].append(role.value)
                entry["sessions_joined"] += 1

            self._total_agents_registered += 1
            return agent

    def get_agent(
        self, session_id: str, agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve an agent from a session.

        Args:
            session_id: Session identifier.
            agent_id: Agent identifier.

        Returns:
            The agent dictionary, or None if not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            agent = session.agents.get(agent_id)
            if agent:
                return agent.to_dict()
            return None

    def update_agent_status(
        self, session_id: str, agent_id: str, status: AgentStatus
    ) -> bool:
        """Update the runtime status of an agent in a session.

        Args:
            session_id: Session identifier.
            agent_id: Agent identifier.
            status: New status to set.

        Returns:
            True if the agent was found and updated, False otherwise.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            agent = session.agents.get(agent_id)
            if agent is None:
                return False
            agent.status = status
            return True

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def assign_task(
        self,
        session_id: str,
        task_title: str,
        description: str = "",
        agent_ids: Optional[List[str]] = None,
        priority: int = 0,
        dependencies: Optional[List[str]] = None,
    ) -> SharedTask:
        """Create and assign a shared task to one or more agents.

        Args:
            session_id: Target session identifier.
            task_title: Short title for the task.
            description: Detailed description of the work.
            agent_ids: List of agent IDs assigned to this task.
            priority: Numeric priority (higher = more urgent).
            dependencies: List of task IDs this task depends on.

        Returns:
            The newly created SharedTask.

        Raises:
            ValueError: If the session is not found or any agent is not registered.
            RuntimeError: If the maximum tasks per session is exceeded.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise ValueError(f"Session not found: {session_id}")

            if len(session.tasks) >= self.MAX_TASKS_PER_SESSION:
                raise RuntimeError(
                    f"Maximum tasks per session ({self.MAX_TASKS_PER_SESSION}) exceeded"
                )

            assigned = agent_ids or []
            for aid in assigned:
                if aid not in session.agents:
                    raise ValueError(
                        f"Agent '{aid}' is not registered in session '{session_id}'"
                    )

            task_id = uuid.uuid4().hex
            task = SharedTask(
                task_id=task_id,
                title=task_title,
                description=description,
                assigned_agents=list(assigned),
                priority=priority,
                dependencies=dependencies or [],
            )
            session.tasks[task_id] = task

            for aid in assigned:
                agent = session.agents[aid]
                agent.current_task = task_id
                agent.status = AgentStatus.WORKING
                if aid in self._global_agent_registry:
                    self._global_agent_registry[aid]["total_tasks_assigned"] += 1

            self._total_tasks_assigned += 1
            return task

    def get_agent_tasks(
        self, session_id: str, agent_id: str
    ) -> List[Dict[str, Any]]:
        """Get all tasks assigned to a specific agent.

        Args:
            session_id: Session identifier.
            agent_id: Agent identifier.

        Returns:
            A list of task dictionaries assigned to the agent.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            tasks = session.get_agent_tasks(agent_id)
            return [t.to_dict() for t in tasks]

    def update_task_status(
        self, session_id: str, task_id: str, status: TaskStatus
    ) -> Optional[Dict[str, Any]]:
        """Update the status of a shared task.

        When a task is completed, all assigned agents are freed (status
        set to IDLE and current_task cleared). Completion time is recorded.

        Args:
            session_id: Session identifier.
            task_id: Task identifier.
            status: New task status.

        Returns:
            The updated task dictionary, or None if not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            task = session.tasks.get(task_id)
            if task is None:
                return None

            task.status = status

            if status == TaskStatus.COMPLETED:
                task.completed_at = _time_module.time()
                for aid in task.assigned_agents:
                    agent = session.agents.get(aid)
                    if agent:
                        agent.record_task_completion(task_id)
                        agent.status = AgentStatus.IDLE
                        agent.current_task = None

            elif status == TaskStatus.BLOCKED:
                for aid in task.assigned_agents:
                    agent = session.agents.get(aid)
                    if agent:
                        agent.status = AgentStatus.BLOCKED

            elif status == TaskStatus.IN_PROGRESS:
                for aid in task.assigned_agents:
                    agent = session.agents.get(aid)
                    if agent:
                        agent.status = AgentStatus.WORKING
                        agent.current_task = task_id

            return task.to_dict()

    def get_task(
        self, session_id: str, task_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a task by ID.

        Args:
            session_id: Session identifier.
            task_id: Task identifier.

        Returns:
            The task dictionary, or None if not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            task = session.tasks.get(task_id)
            if task:
                return task.to_dict()
            return None

    def resolve_task_dependencies(self, session_id: str) -> List[str]:
        """Find and return task IDs that have all dependencies satisfied.

        Args:
            session_id: Session identifier.

        Returns:
            A list of task IDs whose dependencies are all completed.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []

            ready: List[str] = []
            for tid, task in session.tasks.items():
                if task.status != TaskStatus.PENDING:
                    continue
                if not task.dependencies:
                    ready.append(tid)
                    continue
                all_deps_met = True
                for dep_id in task.dependencies:
                    dep_task = session.tasks.get(dep_id)
                    if dep_task is None or dep_task.status != TaskStatus.COMPLETED:
                        all_deps_met = False
                        break
                if all_deps_met:
                    ready.append(tid)

            return ready

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    def send_message(
        self,
        session_id: str,
        sender_id: str,
        receiver_id: str,
        message_type: MessageType = MessageType.STATUS_UPDATE,
        content: str = "",
        context: Optional[Dict[str, Any]] = None,
        references: Optional[List[str]] = None,
    ) -> CollaborationMessage:
        """Send a typed message from one agent to another in a session.

        Args:
            session_id: Session identifier.
            sender_id: Sending agent ID.
            receiver_id: Receiving agent ID.
            message_type: Type of message being sent.
            content: Message body text.
            context: Optional context dictionary.
            references: Optional list of referenced message IDs.

        Returns:
            The created CollaborationMessage.

        Raises:
            ValueError: If session, sender, or receiver is not found.
            RuntimeError: If the maximum messages per session is exceeded.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise ValueError(f"Session not found: {session_id}")

            if sender_id not in session.agents:
                raise ValueError(
                    f"Sender agent '{sender_id}' not registered in session '{session_id}'"
                )

            if receiver_id not in session.agents:
                raise ValueError(
                    f"Receiver agent '{receiver_id}' not registered in session '{session_id}'"
                )

            if len(session.messages) >= self.MAX_MESSAGES_PER_SESSION:
                raise RuntimeError(
                    f"Maximum messages per session ({self.MAX_MESSAGES_PER_SESSION}) exceeded"
                )

            refs = (references or [])[:self.MAX_MESSAGE_REFERENCES]
            message = CollaborationMessage(
                message_id=uuid.uuid4().hex,
                sender_id=sender_id,
                receiver_id=receiver_id,
                message_type=message_type,
                content=content,
                context=context or {},
                timestamp=_time_module.time(),
                references=refs,
            )
            session.messages.append(message)
            self._total_messages_sent += 1
            return message

    def broadcast_message(
        self,
        session_id: str,
        sender_id: str,
        message_type: MessageType = MessageType.STATUS_UPDATE,
        content: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> List[CollaborationMessage]:
        """Broadcast a message from one agent to all other agents in the session.

        Args:
            session_id: Session identifier.
            sender_id: Sending agent ID.
            message_type: Type of message being sent.
            content: Message body text.
            context: Optional context dictionary.

        Returns:
            A list of created CollaborationMessages, one per receiver.

        Raises:
            ValueError: If session or sender is not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise ValueError(f"Session not found: {session_id}")

            if sender_id not in session.agents:
                raise ValueError(
                    f"Sender agent '{sender_id}' not registered in session '{session_id}'"
                )

            messages: List[CollaborationMessage] = []
            for agent_id in session.agents:
                if agent_id == sender_id:
                    continue
                try:
                    msg = self.send_message(
                        session_id=session_id,
                        sender_id=sender_id,
                        receiver_id=agent_id,
                        message_type=message_type,
                        content=content,
                        context=context,
                    )
                    messages.append(msg)
                except RuntimeError:
                    break

            return messages

    def get_session_messages(
        self,
        session_id: str,
        message_type: Optional[MessageType] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve messages from a session with optional filters.

        Args:
            session_id: Session identifier.
            message_type: Filter by message type.
            agent_id: Filter by sender or receiver.
            limit: Maximum messages to return.

        Returns:
            A list of message dictionaries.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []

            messages = session.messages
            if message_type:
                messages = [m for m in messages if m.message_type == message_type]
            if agent_id:
                messages = [
                    m for m in messages
                    if m.sender_id == agent_id or m.receiver_id == agent_id
                ]

            messages.sort(key=lambda m: m.timestamp, reverse=True)
            return [m.to_dict() for m in messages[:limit]]

    def get_message_thread(
        self, session_id: str, message_id: str
    ) -> List[Dict[str, Any]]:
        """Reconstruct a message thread by following reference chains.

        Starting from the given message, walks backward through all
        referenced message IDs to collect the full conversation thread.

        Args:
            session_id: Session identifier.
            message_id: The message to start from.

        Returns:
            A list of message dictionaries in chronological order.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []

            msg_index: Dict[str, CollaborationMessage] = {
                m.message_id: m for m in session.messages
            }

            thread_ids: Set[str] = set()
            to_visit: Deque[str] = deque([message_id])

            while to_visit:
                mid = to_visit.popleft()
                if mid in thread_ids:
                    continue
                thread_ids.add(mid)
                msg = msg_index.get(mid)
                if msg:
                    for ref_id in msg.references:
                        if ref_id not in thread_ids:
                            to_visit.append(ref_id)

            thread_msgs = [msg_index[mid] for mid in thread_ids if mid in msg_index]
            thread_msgs.sort(key=lambda m: m.timestamp)
            return [m.to_dict() for m in thread_msgs]

    # ------------------------------------------------------------------
    # Conflict resolution
    # ------------------------------------------------------------------

    def resolve_conflicts(self, session_id: str) -> List[Dict[str, Any]]:
        """Detect and resolve conflicts in a session by analyzing messages.

        Conflicts are identified by finding pairs of agents that exchanged
        REJECTION messages. Resolution is attempted by locating an APPROVAL
        or PROPOSAL message in the thread. If no resolution is found, a
        mediator (the first idle agent with a different role from both
        parties) is suggested.

        Args:
            session_id: Session identifier.

        Returns:
            A list of conflict resolution result dictionaries.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []

            rejections = [
                m for m in session.messages
                if m.message_type == MessageType.REJECTION
            ]

            conflict_pairs: Set[Tuple[str, str]] = set()
            for rej in rejections:
                pair = tuple(sorted([rej.sender_id, rej.receiver_id]))
                conflict_pairs.add(pair)

            resolutions: List[Dict[str, Any]] = []
            for agent_a, agent_b in conflict_pairs:
                resolution_found = False
                resolution_msg_id: Optional[str] = None

                for msg in session.messages:
                    if msg.message_type == MessageType.APPROVAL:
                        parties = {msg.sender_id, msg.receiver_id}
                        if agent_a in parties and agent_b in parties:
                            resolution_found = True
                            resolution_msg_id = msg.message_id
                            break

                if not resolution_found:
                    for msg in session.messages:
                        if msg.message_type == MessageType.PROPOSAL:
                            parties = {msg.sender_id, msg.receiver_id}
                            if agent_a in parties and agent_b in parties:
                                resolution_found = True
                                resolution_msg_id = msg.message_id
                                break

                agent_a_obj = session.agents.get(agent_a)
                agent_b_obj = session.agents.get(agent_b)
                agent_a_role = agent_a_obj.role.value if agent_a_obj else "unknown"
                agent_b_role = agent_b_obj.role.value if agent_b_obj else "unknown"

                mediator_id: Optional[str] = None
                for aid, ag in session.agents.items():
                    if aid in (agent_a, agent_b):
                        continue
                    if ag.status == AgentStatus.IDLE:
                        mediator_id = aid
                        break

                result = {
                    "agent_a": agent_a,
                    "agent_b": agent_b,
                    "agent_a_role": agent_a_role,
                    "agent_b_role": agent_b_role,
                    "resolved": resolution_found,
                    "resolution_message_id": resolution_msg_id,
                    "resolution_type": "auto" if resolution_found else "pending_mediation",
                    "suggested_mediator": mediator_id,
                    "conflict_messages": len([
                        m for m in session.messages
                        if {m.sender_id, m.receiver_id} == {agent_a, agent_b}
                        and m.message_type in (MessageType.REJECTION, MessageType.FEEDBACK)
                    ]),
                    "resolved_at": _time_module.time() if resolution_found else None,
                }
                resolutions.append(result)
                self._conflict_resolution_log.append(result)

            return resolutions

    # ------------------------------------------------------------------
    # Workspace management
    # ------------------------------------------------------------------

    def update_workspace(
        self,
        session_id: str,
        key: str,
        value: Any,
    ) -> bool:
        """Set a value in the shared session workspace.

        Args:
            session_id: Session identifier.
            key: Workspace key.
            value: Value to store (must be JSON-serializable).

        Returns:
            True if the workspace was updated, False if session not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.workspace[key] = value
            return True

    def get_workspace(
        self, session_id: str, key: Optional[str] = None
    ) -> Optional[Any]:
        """Retrieve a value from the shared session workspace.

        Args:
            session_id: Session identifier.
            key: Workspace key. If None, returns the entire workspace.

        Returns:
            The workspace value, or None if not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if key is None:
                return dict(session.workspace)
            return session.workspace.get(key)

    def delete_workspace_key(self, session_id: str, key: str) -> bool:
        """Remove a key from the shared session workspace.

        Args:
            session_id: Session identifier.
            key: Workspace key to remove.

        Returns:
            True if the key was removed, False otherwise.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            if key in session.workspace:
                del session.workspace[key]
                return True
            return False

    # ------------------------------------------------------------------
    # Reporting and stats
    # ------------------------------------------------------------------

    def generate_collaboration_report(self, session_id: str) -> Dict[str, Any]:
        """Generate a comprehensive collaboration report for a session.

        Includes session metadata, agent participation, task statistics,
        activity timeline, communication patterns, and conflict resolution
        summary.

        Args:
            session_id: Session identifier.

        Returns:
            A detailed report dictionary with collaboration metrics.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return {"error": f"Session not found: {session_id}", "session_id": session_id}

            # Task breakdown
            task_status_counts: Dict[str, int] = {}
            for t in session.tasks.values():
                key = t.status.value
                task_status_counts[key] = task_status_counts.get(key, 0) + 1

            tasks_with_deps = sum(1 for t in session.tasks.values() if t.dependencies)
            dependency_chains = self._find_longest_dependency_chain(session)

            # Agent participation
            agent_contributions: Dict[str, Dict[str, Any]] = {}
            for aid, agent in session.agents.items():
                agent_tasks = session.get_agent_tasks(aid)
                agent_msgs = session.get_agent_messages(aid)
                sent_count = sum(1 for m in agent_msgs if m.sender_id == aid)
                received_count = sum(1 for m in agent_msgs if m.receiver_id == aid)

                agent_contributions[aid] = {
                    "name": agent.name,
                    "role": agent.role.value,
                    "tasks_assigned": len(agent_tasks),
                    "tasks_completed": len(agent.task_history),
                    "messages_sent": sent_count,
                    "messages_received": received_count,
                    "status": agent.status.value,
                }

            # Message type distribution
            msg_type_counts: Dict[str, int] = {}
            for m in session.messages:
                key = m.message_type.value
                msg_type_counts[key] = msg_type_counts.get(key, 0) + 1

            # Activity timeline (messages per minute buckets)
            activity_timeline: Dict[str, int] = {}
            if session.messages:
                first_ts = session.messages[0].timestamp
                last_ts = session.messages[-1].timestamp
                bucket_size = max(60.0, (last_ts - first_ts) / 10.0)
                for m in session.messages:
                    bucket_key = str(int((m.timestamp - first_ts) / bucket_size))
                    activity_timeline[bucket_key] = activity_timeline.get(bucket_key, 0) + 1

            # Conflict analysis
            conflict_results = self.resolve_conflicts(session_id)
            conflicts_resolved = sum(1 for c in conflict_results if c["resolved"])
            conflicts_pending = len(conflict_results) - conflicts_resolved

            return {
                "session_id": session.session_id,
                "session_name": session.name,
                "mode": session.mode.value,
                "duration_seconds": (
                    round((session.ended_at or _time_module.time()) - session.started_at, 2)
                ),
                "is_active": session.ended_at is None,
                "agents": {
                    "total": len(session.agents),
                    "by_role": self._count_by_role(session),
                    "contributions": agent_contributions,
                },
                "tasks": {
                    "total": len(session.tasks),
                    "by_status": task_status_counts,
                    "completion_rate": (
                        round(
                            task_status_counts.get("completed", 0) / max(len(session.tasks), 1), 3
                        )
                    ),
                    "tasks_with_dependencies": tasks_with_deps,
                    "longest_dependency_chain": dependency_chains,
                },
                "messages": {
                    "total": len(session.messages),
                    "by_type": msg_type_counts,
                    "average_per_agent": (
                        round(len(session.messages) / max(len(session.agents), 1), 1)
                    ),
                },
                "activity_timeline": activity_timeline,
                "conflicts": {
                    "total": len(conflict_results),
                    "resolved": conflicts_resolved,
                    "pending": conflicts_pending,
                    "details": conflict_results,
                },
                "workspace_size": len(session.workspace),
                "workspace_keys": list(session.workspace.keys()),
                "generated_at": _time_module.time(),
            }

    def _count_by_role(self, session: CollaborationSession) -> Dict[str, int]:
        """Count agents in a session grouped by role."""
        counts: Dict[str, int] = {}
        for agent in session.agents.values():
            role_key = agent.role.value
            counts[role_key] = counts.get(role_key, 0) + 1
        return counts

    def _find_longest_dependency_chain(self, session: CollaborationSession) -> int:
        """Find the length of the longest dependency chain in a session's tasks.

        Uses topological traversal with memoization to compute the maximum
        chain length from any task through its dependency graph.
        """
        memo: Dict[str, int] = {}

        def _chain_length(task_id: str, visited: Set[str]) -> int:
            if task_id in memo:
                return memo[task_id]
            if task_id in visited:
                return 0
            visited.add(task_id)
            task = session.tasks.get(task_id)
            if task is None:
                memo[task_id] = 0
                return 0
            if not task.dependencies:
                memo[task_id] = 1
                return 1
            max_sub = 0
            for dep_id in task.dependencies:
                sub_len = _chain_length(dep_id, visited.copy())
                max_sub = max(max_sub, sub_len)
            result = max_sub + 1
            memo[task_id] = result
            return result

        max_chain = 0
        for tid in session.tasks:
            chain = _chain_length(tid, set())
            max_chain = max(max_chain, chain)

        return max_chain

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive statistics across all collaboration sessions.

        Returns aggregate counts for sessions, agents, tasks, messages,
        and conflict resolutions across the system's entire lifetime.
        """
        with self._lock:
            active_sessions = sum(1 for s in self._sessions.values() if s.ended_at is None)
            total_agents = sum(len(s.agents) for s in self._sessions.values())
            total_tasks = sum(len(s.tasks) for s in self._sessions.values())
            total_messages = sum(len(s.messages) for s in self._sessions.values())

            completed_tasks = sum(
                1 for s in self._sessions.values()
                for t in s.tasks.values()
                if t.status == TaskStatus.COMPLETED
            )

            mode_distribution: Dict[str, int] = {}
            role_distribution: Dict[str, int] = {}
            for s in self._sessions.values():
                mode_distribution[s.mode.value] = mode_distribution.get(s.mode.value, 0) + 1
                for a in s.agents.values():
                    role_distribution[a.role.value] = role_distribution.get(a.role.value, 0) + 1

            return {
                "total_sessions": len(self._sessions),
                "active_sessions": active_sessions,
                "completed_sessions": len(self._sessions) - active_sessions,
                "total_agents_registered": total_agents,
                "total_tasks_assigned": total_tasks,
                "completed_tasks": completed_tasks,
                "total_messages_sent": total_messages,
                "lifetime_sessions_created": self._total_sessions_created,
                "lifetime_agents_registered": self._total_agents_registered,
                "lifetime_tasks_assigned": self._total_tasks_assigned,
                "lifetime_messages_sent": self._total_messages_sent,
                "conflicts_logged": len(self._conflict_resolution_log),
                "sessions_by_mode": mode_distribution,
                "agents_by_role": role_distribution,
                "average_tasks_per_session": (
                    round(total_tasks / max(len(self._sessions), 1), 1)
                ),
                "average_agents_per_session": (
                    round(total_agents / max(len(self._sessions), 1), 1)
                ),
                "task_completion_rate": (
                    round(completed_tasks / max(total_tasks, 1), 3)
                ),
            }

    # ------------------------------------------------------------------
    # Session cleanup
    # ------------------------------------------------------------------

    def remove_session(self, session_id: str) -> bool:
        """Permanently remove a session and all its data.

        Args:
            session_id: Session identifier to remove.

        Returns:
            True if the session was found and removed, False otherwise.
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def cleanup_ended_sessions(self, max_age_seconds: float = 3600.0) -> int:
        """Remove sessions that ended more than max_age_seconds ago.

        Args:
            max_age_seconds: Maximum age in seconds for ended sessions.

        Returns:
            The number of sessions cleaned up.
        """
        with self._lock:
            now = _time_module.time()
            to_remove: List[str] = []
            for sid, session in self._sessions.items():
                if session.ended_at is not None and (now - session.ended_at) > max_age_seconds:
                    to_remove.append(sid)

            for sid in to_remove:
                del self._sessions[sid]

            return len(to_remove)

    def reset(self) -> None:
        """Reset all collaboration system state."""
        with self._lock:
            self._sessions.clear()
            self._global_agent_registry.clear()
            self._conflict_resolution_log.clear()
            self._total_sessions_created = 0
            self._total_agents_registered = 0
            self._total_tasks_assigned = 0
            self._total_messages_sent = 0


# ------------------------------------------------------------------
# Module-level singleton accessor
# ------------------------------------------------------------------

_collaboration_system = CollaborationSystem.get_instance()


def get_collaboration_system() -> CollaborationSystem:
    """Return the singleton CollaborationSystem instance."""
    return _collaboration_system