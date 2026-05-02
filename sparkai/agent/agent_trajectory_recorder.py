"""
Trajectory Recorder - Records agent sessions into replayable action timelines.

Architecture:
    TrajectoryRecorder/
    |-- TrajectoryEvent (single action record dataclass)
    |-- TrajectorySession (complete session timeline dataclass)
    |-- TrajectoryRecorder (global recording orchestration)

Captures the full sequence of agent actions, tool calls, and LLM exchanges
during AI-native game development sessions. Stores structured event timelines
for debugging, replay, analysis, and training data generation.
"""

from __future__ import annotations

import uuid
import time
import json
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class EventType(Enum):
    SESSION_START = auto()
    SESSION_END = auto()
    USER_MESSAGE = auto()
    LLM_REQUEST = auto()
    LLM_RESPONSE = auto()
    TOOL_CALL = auto()
    TOOL_RESULT = auto()
    ENGINE_ACTION = auto()
    EDITOR_CHANGE = auto()
    AGENT_THOUGHT = auto()
    ERROR = auto()
    STATE_SNAPSHOT = auto()


@dataclass
class TrajectoryEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.USER_MESSAGE
    timestamp: float = 0.0
    session_id: str = ""
    agent_id: str = ""
    step_index: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    parent_event_id: Optional[str] = None
    duration_ms: float = 0.0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "type": self.event_type.name,
            "timestamp": self.timestamp,
            "step": self.step_index,
            "duration_ms": round(self.duration_ms, 2),
            "data_summary": self._summarize_data(),
            "tags": self.tags,
        }

    def _summarize_data(self) -> Dict[str, Any]:
        summary = {}
        for k, v in self.data.items():
            if isinstance(v, str):
                summary[k] = v[:80] if len(v) > 80 else v
            elif isinstance(v, (int, float, bool)):
                summary[k] = v
            elif isinstance(v, dict):
                summary[k] = f"dict({len(v)}keys)"
            elif isinstance(v, list):
                summary[k] = f"list({len(v)}items)"
            else:
                summary[k] = str(type(v).__name__)
        return summary


@dataclass
class TrajectorySession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    started_at: float = 0.0
    ended_at: Optional[float] = None
    events: List[TrajectoryEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    step_count: int = 0
    total_tool_calls: int = 0
    total_llm_calls: int = 0
    total_errors: int = 0
    status: str = "recording"

    def get_duration(self) -> float:
        end = self.ended_at or time.time()
        return end - self.started_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "duration_seconds": round(self.get_duration(), 1),
            "event_count": len(self.events),
            "step_count": self.step_count,
            "tool_calls": self.total_tool_calls,
            "llm_calls": self.total_llm_calls,
            "errors": self.total_errors,
            "status": self.status,
            "metadata": self.metadata,
        }


class TrajectoryRecorder:
    _instance: Optional["TrajectoryRecorder"] = None
    _MAX_EVENTS_PER_SESSION = 10000
    _MAX_SESSIONS = 50

    def __init__(self):
        self._sessions: Dict[str, TrajectorySession] = {}
        self._active_session_id: Optional[str] = None
        self._total_events_recorded: int = 0
        self._total_sessions_created: int = 0
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "TrajectoryRecorder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_session(self, agent_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> TrajectorySession:
        session = TrajectorySession(
            agent_id=agent_id,
            started_at=time.time(),
            metadata=metadata or {},
        )
        with self._lock:
            self._sessions[session.session_id] = session
            self._active_session_id = session.session_id
            self._total_sessions_created += 1
            self._trim_sessions()

        self.record_event(EventType.SESSION_START, data=metadata or {})
        return session

    def end_session(self, session_id: Optional[str] = None) -> Optional[TrajectorySession]:
        sid = session_id or self._active_session_id
        if not sid or sid not in self._sessions:
            return None
        session = self._sessions[sid]
        session.ended_at = time.time()
        session.status = "completed"
        self.record_event(EventType.SESSION_END, data={"duration": session.get_duration()})
        if session_id or self._active_session_id == sid:
            self._active_session_id = None
        return session

    def record_event(self, event_type: EventType, data: Optional[Dict[str, Any]] = None,
                     tags: Optional[List[str]] = None,
                     parent_event_id: Optional[str] = None,
                     duration_ms: float = 0.0) -> Optional[TrajectoryEvent]:
        session = self._get_active_session()
        if not session:
            return None

        if len(session.events) >= self._MAX_EVENTS_PER_SESSION:
            return None

        event = TrajectoryEvent(
            event_type=event_type,
            timestamp=time.time(),
            session_id=session.session_id,
            agent_id=session.agent_id,
            step_index=session.step_count,
            data=data or {},
            parent_event_id=parent_event_id,
            duration_ms=duration_ms,
            tags=tags or [],
        )

        with self._lock:
            session.events.append(event)
            session.step_count += 1
            self._total_events_recorded += 1

            if event_type == EventType.TOOL_CALL:
                session.total_tool_calls += 1
            elif event_type == EventType.LLM_REQUEST:
                session.total_llm_calls += 1
            elif event_type == EventType.ERROR:
                session.total_errors += 1

        return event

    def record_llm_exchange(self, prompt: str, response: str, model: str = "",
                            duration_ms: float = 0.0, tokens_used: int = 0) -> Tuple[TrajectoryEvent, TrajectoryEvent]:
        req = self.record_event(
            EventType.LLM_REQUEST,
            data={"prompt": prompt, "model": model, "tokens": tokens_used},
            tags=["llm", model],
        )
        resp = self.record_event(
            EventType.LLM_RESPONSE,
            data={"response": response, "model": model},
            parent_event_id=req.event_id if req else None,
            duration_ms=duration_ms,
            tags=["llm", model],
        )
        return req, resp

    def record_tool_execution(self, tool_name: str, params: Dict[str, Any],
                              result: Any, duration_ms: float = 0.0,
                              success: bool = True) -> Tuple[TrajectoryEvent, TrajectoryEvent]:
        call = self.record_event(
            EventType.TOOL_CALL,
            data={"tool": tool_name, "params": params},
            tags=["tool", tool_name],
        )
        result_data = {"tool": tool_name, "result": str(result)[:500], "success": success}
        res = self.record_event(
            EventType.TOOL_RESULT,
            data=result_data,
            parent_event_id=call.event_id if call else None,
            duration_ms=duration_ms,
            tags=["tool", tool_name, "success" if success else "failure"],
        )
        return call, res

    def get_session(self, session_id: str) -> Optional[TrajectorySession]:
        return self._sessions.get(session_id)

    def get_active_session(self) -> Optional[TrajectorySession]:
        if not self._active_session_id:
            return None
        return self._sessions.get(self._active_session_id)

    def list_sessions(self) -> List[TrajectorySession]:
        return list(self._sessions.values())

    def get_session_events(self, session_id: str, event_type: Optional[EventType] = None,
                           limit: int = 100) -> List[TrajectoryEvent]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        events = session.events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def export_session(self, session_id: str) -> Optional[str]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        return json.dumps({
            "session": session.to_dict(),
            "events": [e.to_dict() for e in session.events],
        }, indent=2, default=str)

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                if self._active_session_id == session_id:
                    self._active_session_id = None
                del self._sessions[session_id]
                return True
        return False

    def _get_active_session(self) -> Optional[TrajectorySession]:
        if not self._active_session_id:
            return None
        return self._sessions.get(self._active_session_id)

    def _trim_sessions(self) -> None:
        if len(self._sessions) > self._MAX_SESSIONS:
            keys = sorted(self._sessions.keys(), key=lambda k: self._sessions[k].started_at)
            for key in keys[:len(keys) - self._MAX_SESSIONS]:
                del self._sessions[key]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            active_session = self._get_active_session()
        return {
            "total_sessions": self._total_sessions_created,
            "active_sessions": len(self._sessions),
            "active_recording": self._active_session_id is not None and active_session is not None,
            "total_events": self._total_events_recorded,
            "max_sessions": self._MAX_SESSIONS,
            "sessions": [s.to_dict() for s in self._sessions.values()],
        }


def get_trajectory_recorder() -> TrajectoryRecorder:
    return TrajectoryRecorder.get_instance()
