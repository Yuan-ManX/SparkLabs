"""
SparkAI Agent - Session Manager

Persistent agent sessions with conversation history,
context management, and state persistence.

Sessions enable:
  - Multi-turn conversations with agents
  - Persistent context across interactions
  - Session state save/restore
  - Session health monitoring
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SessionState(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    ERROR = "error"


@dataclass
class SessionMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "user"
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentSession:
    """
    A persistent session between a user and an agent.
    Maintains conversation history and session context.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    agent_name: str = ""
    state: str = SessionState.ACTIVE.value
    messages: List[SessionMessage] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    message_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> SessionMessage:
        msg = SessionMessage(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(msg)
        self.message_count += 1
        self.last_active = time.time()
        return msg

    def get_recent_messages(self, count: int = 10) -> List[SessionMessage]:
        return self.messages[-count:]

    def get_context_string(self) -> str:
        parts = []
        for msg in self.messages[-20:]:
            prefix = "User" if msg.role == "user" else "Agent"
            parts.append(f"{prefix}: {msg.content[:200]}")
        return "\n".join(parts)

    def set_context(self, key: str, value: Any) -> None:
        self.context[key] = value
        self.last_active = time.time()

    def get_context(self, key: str, default: Any = None) -> Any:
        return self.context.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "state": self.state,
            "message_count": self.message_count,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "context_keys": list(self.context.keys()),
            "metadata": self.metadata,
        }


class SessionManager:
    """
    Manages agent sessions with creation, retrieval, and cleanup.
    Provides session health monitoring and automatic expiry.
    """

    def __init__(self, max_sessions: int = 100, session_ttl: float = 3600.0):
        self._sessions: Dict[str, AgentSession] = {}
        self._max_sessions = max_sessions
        self._session_ttl = session_ttl

    def create_session(
        self,
        agent_id: str,
        agent_name: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentSession:
        self._cleanup_expired()
        if len(self._sessions) >= self._max_sessions:
            oldest = min(self._sessions.values(), key=lambda s: s.last_active)
            del self._sessions[oldest.id]

        session = AgentSession(
            agent_id=agent_id,
            agent_name=agent_name,
            metadata=metadata or {},
        )
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session:
            session.state = SessionState.ENDED.value
            return True
        return False

    def list_sessions(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        sessions = list(self._sessions.values())
        if agent_id:
            sessions = [s for s in sessions if s.agent_id == agent_id]
        return [s.to_dict() for s in sessions]

    def get_active_sessions(self) -> List[AgentSession]:
        now = time.time()
        return [
            s for s in self._sessions.values()
            if s.state == SessionState.ACTIVE.value and (now - s.last_active) < self._session_ttl
        ]

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if (now - s.last_active) > self._session_ttl
        ]
        for sid in expired:
            self._sessions[sid].state = SessionState.ENDED.value
            del self._sessions[sid]

    def get_stats(self) -> Dict[str, Any]:
        active = sum(1 for s in self._sessions.values() if s.state == SessionState.ACTIVE.value)
        total_messages = sum(s.message_count for s in self._sessions.values())
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": active,
            "total_messages": total_messages,
            "max_sessions": self._max_sessions,
            "session_ttl": self._session_ttl,
        }
