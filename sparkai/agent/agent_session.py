"""
SparkAI Agent - Agent Session

Deep session management system that provides persistent, resumable
conversations with full context threading, checkpoint/restore, and
multi-turn dialogue tracking. The AgentSession system enables agents
to maintain coherent long-running interactions with state preservation.

Architecture:
  AgentSessionManager
    |-- SessionStore (persistent session storage)
    |-- ConversationThread (multi-turn dialogue tracking)
    |-- ContextWindow (rolling context with priority scoring)
    |-- CheckpointManager (session state snapshots for resume)
    |-- SessionAnalytics (usage patterns and session metrics)

Session Lifecycle:
  Create -> Active -> Idle -> Suspended -> Resumed -> Closed

Features:
  - Conversation threading with parent/child relationships
  - Context window management with token budgeting
  - Checkpoint/restore for session persistence
  - Session branching for exploring alternative paths
  - Automatic session expiration and cleanup
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SessionState(Enum):
    CREATED = "created"
    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    EXPIRED = "expired"
    ERROR = "error"


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    OBSERVATION = "observation"


class CheckpointType(Enum):
    MANUAL = "manual"
    AUTO = "auto"
    PRE_ACTION = "pre_action"
    POST_ACTION = "post_action"
    MILESTONE = "milestone"


@dataclass
class ConversationMessage:
    """A single message in a conversation thread."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole = MessageRole.USER
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    timestamp: float = field(default_factory=time.time)
    parent_id: Optional[str] = None
    thread_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content[:500],
            "metadata": self.metadata,
            "token_count": self.token_count,
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
            "thread_id": self.thread_id,
        }


@dataclass
class ConversationThread:
    """A conversation thread within a session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    messages: List[ConversationMessage] = field(default_factory=list)
    parent_thread_id: Optional[str] = None
    child_thread_ids: List[str] = field(default_factory=list)
    summary: str = ""
    total_tokens: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "message_count": len(self.messages),
            "parent_thread_id": self.parent_thread_id,
            "child_thread_ids": self.child_thread_ids,
            "summary": self.summary,
            "total_tokens": self.total_tokens,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None, token_count: int = 0) -> ConversationMessage:
        parent_id = self.messages[-1].id if self.messages else None
        msg = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {},
            token_count=token_count,
            parent_id=parent_id,
            thread_id=self.id,
        )
        self.messages.append(msg)
        self.total_tokens += token_count
        self.updated_at = time.time()
        return msg

    def get_context_window(self, max_tokens: int = 4000) -> List[ConversationMessage]:
        if not self.messages:
            return []
        selected: List[ConversationMessage] = []
        total = 0
        for msg in reversed(self.messages):
            if total + msg.token_count > max_tokens:
                break
            selected.insert(0, msg)
            total += msg.token_count
        return selected


@dataclass
class SessionCheckpoint:
    """A snapshot of session state for restore."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    checkpoint_type: CheckpointType = CheckpointType.MANUAL
    name: str = ""
    description: str = ""
    state: SessionState = SessionState.ACTIVE
    thread_count: int = 0
    message_count: int = 0
    total_tokens: int = 0
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    agent_state: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "checkpoint_type": self.checkpoint_type.value,
            "name": self.name,
            "description": self.description,
            "state": self.state.value,
            "thread_count": self.thread_count,
            "message_count": self.message_count,
            "total_tokens": self.total_tokens,
            "created_at": self.created_at,
        }


@dataclass
class AgentSessionV2:
    """A persistent agent session with conversation threading."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    agent_name: str = ""
    name: str = ""
    state: SessionState = SessionState.CREATED
    threads: Dict[str, ConversationThread] = field(default_factory=dict)
    active_thread_id: Optional[str] = None
    checkpoints: List[SessionCheckpoint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    max_context_tokens: int = 8000
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)
    closed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "name": self.name,
            "state": self.state.value,
            "thread_count": len(self.threads),
            "active_thread_id": self.active_thread_id,
            "checkpoint_count": len(self.checkpoints),
            "total_messages": sum(len(t.messages) for t in self.threads.values()),
            "total_tokens": sum(t.total_tokens for t in self.threads.values()),
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_active_at": self.last_active_at,
            "closed_at": self.closed_at,
        }

    def get_active_thread(self) -> Optional[ConversationThread]:
        if self.active_thread_id and self.active_thread_id in self.threads:
            return self.threads[self.active_thread_id]
        return None

    def create_thread(self, name: str = "", parent_thread_id: Optional[str] = None) -> ConversationThread:
        thread = ConversationThread(name=name or f"Thread-{len(self.threads) + 1}", parent_thread_id=parent_thread_id)
        if parent_thread_id and parent_thread_id in self.threads:
            self.threads[parent_thread_id].child_thread_ids.append(thread.id)
        self.threads[thread.id] = thread
        if not self.active_thread_id:
            self.active_thread_id = thread.id
        self.updated_at = time.time()
        return thread

    def switch_thread(self, thread_id: str) -> bool:
        if thread_id in self.threads:
            self.active_thread_id = thread_id
            self.updated_at = time.time()
            return True
        return False

    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None, token_count: int = 0) -> Optional[ConversationMessage]:
        thread = self.get_active_thread()
        if not thread:
            thread = self.create_thread("Main")
        msg = thread.add_message(role, content, metadata, token_count)
        self.last_active_at = time.time()
        self.updated_at = time.time()
        return msg

    def get_context(self, max_tokens: Optional[int] = None) -> List[ConversationMessage]:
        thread = self.get_active_thread()
        if not thread:
            return []
        return thread.get_context_window(max_tokens or self.max_context_tokens)

    def create_checkpoint(self, name: str = "", description: str = "", checkpoint_type: CheckpointType = CheckpointType.MANUAL) -> SessionCheckpoint:
        checkpoint = SessionCheckpoint(
            session_id=self.id,
            checkpoint_type=checkpoint_type,
            name=name or f"Checkpoint-{len(self.checkpoints) + 1}",
            description=description,
            state=self.state,
            thread_count=len(self.threads),
            message_count=sum(len(t.messages) for t in self.threads.values()),
            total_tokens=sum(t.total_tokens for t in self.threads.values()),
            context_snapshot={tid: {"message_count": len(t.messages), "total_tokens": t.total_tokens} for tid, t in self.threads.items()},
        )
        self.checkpoints.append(checkpoint)
        self.updated_at = time.time()
        return checkpoint

    def activate(self) -> None:
        self.state = SessionState.ACTIVE
        self.last_active_at = time.time()
        self.updated_at = time.time()

    def suspend(self) -> None:
        self.state = SessionState.SUSPENDED
        self.updated_at = time.time()

    def close(self) -> None:
        self.state = SessionState.CLOSED
        self.closed_at = time.time()
        self.updated_at = time.time()


class AgentSessionManager:
    """
    Deep session management system for the SparkLabs AI-Native Game Engine.

    Provides persistent, resumable conversations with full context threading,
    checkpoint/restore, and multi-turn dialogue tracking.

    Usage:
        manager = AgentSessionManager()
        session = manager.create_session(agent_id="agent-1", agent_name="GameDesigner")
        session.add_message(MessageRole.USER, "Design a platformer")
        checkpoint = session.create_checkpoint("pre-design")
        session.add_message(MessageRole.ASSISTANT, "Here is the design...")
    """

    def __init__(self, max_sessions: int = 100, session_ttl: float = 3600.0, auto_checkpoint_interval: float = 300.0):
        self._sessions: Dict[str, AgentSessionV2] = {}
        self._max_sessions = max_sessions
        self._session_ttl = session_ttl
        self._auto_checkpoint_interval = auto_checkpoint_interval
        self._total_created: int = 0
        self._total_messages: int = 0
        self._total_checkpoints: int = 0

    def create_session(self, agent_id: str = "", agent_name: str = "", name: str = "", metadata: Optional[Dict[str, Any]] = None) -> AgentSessionV2:
        if len(self._sessions) >= self._max_sessions:
            self._evict_oldest()
        session = AgentSessionV2(
            agent_id=agent_id,
            agent_name=agent_name,
            name=name or f"Session-{self._total_created + 1}",
            metadata=metadata or {},
        )
        session.create_thread("Main")
        session.activate()
        self._sessions[session.id] = session
        self._total_created += 1
        return session

    def get_session(self, session_id: str) -> Optional[AgentSessionV2]:
        return self._sessions.get(session_id)

    def list_sessions(self, state: Optional[SessionState] = None) -> List[AgentSessionV2]:
        sessions = list(self._sessions.values())
        if state:
            sessions = [s for s in sessions if s.state == state]
        return sorted(sessions, key=lambda s: s.last_active_at, reverse=True)

    def close_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session:
            session.close()
            return True
        return False

    def resume_session(self, session_id: str) -> Optional[AgentSessionV2]:
        session = self._sessions.get(session_id)
        if session and session.state in (SessionState.SUSPENDED, SessionState.IDLE):
            session.activate()
            return session
        return None

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def send_message(self, session_id: str, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None, token_count: int = 0) -> Optional[ConversationMessage]:
        session = self._sessions.get(session_id)
        if not session or session.state not in (SessionState.ACTIVE, SessionState.CREATED):
            return None
        msg = session.add_message(role, content, metadata, token_count)
        self._total_messages += 1
        if session.last_active_at - session.created_at > self._auto_checkpoint_interval:
            if not session.checkpoints or (time.time() - session.checkpoints[-1].created_at > self._auto_checkpoint_interval):
                session.create_checkpoint("auto", "Automatic checkpoint", CheckpointType.AUTO)
                self._total_checkpoints += 1
        return msg

    def get_context(self, session_id: str, max_tokens: Optional[int] = None) -> List[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        return [m.to_dict() for m in session.get_context(max_tokens)]

    def create_checkpoint(self, session_id: str, name: str = "", description: str = "") -> Optional[SessionCheckpoint]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        checkpoint = session.create_checkpoint(name, description)
        self._total_checkpoints += 1
        return checkpoint

    def get_checkpoints(self, session_id: str) -> List[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        return [c.to_dict() for c in session.checkpoints]

    def create_thread(self, session_id: str, name: str = "", parent_thread_id: Optional[str] = None) -> Optional[str]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        thread = session.create_thread(name, parent_thread_id)
        return thread.id

    def switch_thread(self, session_id: str, thread_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        return session.switch_thread(thread_id)

    def get_threads(self, session_id: str) -> List[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        return [t.to_dict() for t in session.threads.values()]

    def cleanup_expired(self) -> int:
        now = time.time()
        expired = []
        for sid, session in self._sessions.items():
            if session.state == SessionState.CLOSED:
                expired.append(sid)
            elif session.state not in (SessionState.ACTIVE, SessionState.CREATED):
                if now - session.last_active_at > self._session_ttl:
                    session.state = SessionState.EXPIRED
                    expired.append(sid)
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    def _evict_oldest(self) -> None:
        if not self._sessions:
            return
        oldest_id = min(self._sessions, key=lambda sid: self._sessions[sid].last_active_at)
        del self._sessions[oldest_id]

    def get_stats(self) -> Dict[str, Any]:
        by_state: Dict[str, int] = {}
        for s in self._sessions.values():
            by_state[s.state.value] = by_state.get(s.state.value, 0) + 1
        return {
            "total_sessions": len(self._sessions),
            "total_created": self._total_created,
            "total_messages": self._total_messages,
            "total_checkpoints": self._total_checkpoints,
            "by_state": by_state,
            "avg_messages_per_session": self._total_messages / max(len(self._sessions), 1),
        }


_global_session_manager: Optional[AgentSessionManager] = None


def get_agent_session_manager() -> AgentSessionManager:
    """Get the global AgentSessionManager singleton."""
    global _global_session_manager
    if _global_session_manager is None:
        _global_session_manager = AgentSessionManager()
    return _global_session_manager


def reset_agent_session_manager() -> None:
    """Reset the global AgentSessionManager singleton."""
    global _global_session_manager
    _global_session_manager = None
