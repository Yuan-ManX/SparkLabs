"""
SparkAI Agent - Game Runtime Orchestrator

Manages the full lifecycle of game instances: creation, launching,
runtime control, pausing, resuming, stopping, and cleanup.
Supports multiple concurrent game sessions with WebSocket broadcast.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class GameState(Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class GameSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    prompt: str = ""
    html: str = ""
    html_length: int = 0
    state: GameState = GameState.CREATED
    run_id: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    paused_at: float = 0.0
    stopped_at: float = 0.0
    duration_s: float = 0.0
    fps: int = 60
    tick_count: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "prompt": self.prompt,
            "state": self.state.value,
            "run_id": self.run_id,
            "html_length": self.html_length,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "paused_at": self.paused_at,
            "stopped_at": self.stopped_at,
            "duration_s": self.duration_s,
            "fps": self.fps,
            "tick_count": self.tick_count,
            "error": self.error,
            "metadata": self.metadata,
        }


class GameRuntime:
    """
    Manages game instance lifecycle with thread-safe session tracking.

    Sessions can be created from prompts (via the game creation
    orchestrator) or from pre-built HTML. Each session supports
    start/pause/resume/stop operations and reports runtime metrics.
    """

    _instance: Optional["GameRuntime"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._sessions: Dict[str, GameSession] = {}
        self._session_lock = threading.RLock()
        self._listeners: Dict[str, List[Callable]] = {}
        self._tick_tasks: Dict[str, asyncio.Task] = {}
        self._max_sessions: int = 32

    @classmethod
    def get_instance(cls) -> "GameRuntime":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def create_session(
        self,
        prompt: str = "",
        html: str = "",
        run_id: str = "",
        fps: int = 60,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GameSession:
        """Create a new game session from a prompt or pre-built HTML."""
        with self._session_lock:
            if len(self._sessions) >= self._max_sessions:
                oldest = min(
                    self._sessions.values(), key=lambda s: s.created_at
                )
                self._cleanup_session(oldest.session_id)

            session = GameSession(
                prompt=prompt,
                html=html,
                html_length=len(html),
                run_id=run_id,
                fps=fps,
                metadata=metadata or {},
            )
            self._sessions[session.session_id] = session
            self._emit_event("session_created", session)
            logger.info(
                "Created game session %s (prompt=%s)",
                session.session_id,
                prompt[:50],
            )
            return session

    def create_from_prompt(
        self,
        prompt: str,
        genre_hint: Optional[str] = None,
    ) -> GameSession:
        """Create a game session by running the full AI-native creation pipeline."""
        try:
            from sparkai.engine.engine_game_creation_orchestrator import (
                get_orchestrator,
            )
            orch = get_orchestrator()
            if not orch._initialized:
                orch.initialize()

            result = orch.create_game(prompt, genre_hint=genre_hint)
            session = self.create_session(
                prompt=prompt,
                html=result.html,
                run_id=result.run_id,
                metadata={
                    "architect_conclusion": result.architect_conclusion,
                    "architect_confidence": result.architect_confidence,
                    "creation_duration_s": result.duration_s,
                    "phases": [p.phase.value for p in result.phases],
                },
            )
            if result.status.value == "success":
                self.start_session(session.session_id)
            else:
                session.state = GameState.ERROR
                session.error = result.error
            return session
        except Exception as exc:
            logger.exception("Failed to create game from prompt")
            return self.create_session(
                prompt=prompt,
                metadata={"error": str(exc)},
            )

    def start_session(self, session_id: str) -> Optional[GameSession]:
        """Start a game session, beginning its runtime tick loop."""
        with self._session_lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            if session.state == GameState.RUNNING:
                return session

            session.state = GameState.RUNNING
            session.started_at = time.time()
            session.error = None
            self._emit_event("session_started", session)
            logger.info("Started game session %s", session_id)
            return session

    def pause_session(self, session_id: str) -> Optional[GameSession]:
        """Pause a running game session."""
        with self._session_lock:
            session = self._sessions.get(session_id)
            if not session or session.state != GameState.RUNNING:
                return session
            session.state = GameState.PAUSED
            session.paused_at = time.time()
            self._emit_event("session_paused", session)
            return session

    def resume_session(self, session_id: str) -> Optional[GameSession]:
        """Resume a paused game session."""
        with self._session_lock:
            session = self._sessions.get(session_id)
            if not session or session.state != GameState.PAUSED:
                return session
            session.state = GameState.RUNNING
            self._emit_event("session_resumed", session)
            return session

    def stop_session(self, session_id: str) -> Optional[GameSession]:
        """Stop a running or paused game session."""
        with self._session_lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            if session.state == GameState.STOPPED:
                return session

            if session.started_at:
                session.duration_s += time.time() - session.started_at
            session.state = GameState.STOPPED
            session.stopped_at = time.time()
            self._emit_event("session_stopped", session)
            logger.info("Stopped game session %s", session_id)
            return session

    def destroy_session(self, session_id: str) -> bool:
        """Permanently remove a game session."""
        with self._session_lock:
            if session_id in self._sessions:
                self._cleanup_session(session_id)
                return True
            return False

    def _cleanup_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._tick_tasks.pop(session_id, None)
        self._emit_event("session_destroyed", None, extra={"session_id": session_id})

    def get_session(self, session_id: str) -> Optional[GameSession]:
        with self._session_lock:
            return self._sessions.get(session_id)

    def list_sessions(self, state: Optional[GameState] = None) -> List[Dict[str, Any]]:
        with self._session_lock:
            sessions = list(self._sessions.values())
        if state:
            sessions = [s for s in sessions if s.state == state]
        return [s.to_dict() for s in sessions]

    def get_session_html(self, session_id: str) -> Optional[str]:
        with self._session_lock:
            session = self._sessions.get(session_id)
        if session and session.html:
            return session.html
        return None

    def get_status(self) -> Dict[str, Any]:
        with self._session_lock:
            sessions = list(self._sessions.values())
        return {
            "total_sessions": len(sessions),
            "running": sum(1 for s in sessions if s.state == GameState.RUNNING),
            "paused": sum(1 for s in sessions if s.state == GameState.PAUSED),
            "stopped": sum(1 for s in sessions if s.state == GameState.STOPPED),
            "created": sum(1 for s in sessions if s.state == GameState.CREATED),
            "error": sum(1 for s in sessions if s.state == GameState.ERROR),
            "max_sessions": self._max_sessions,
        }

    def subscribe(
        self, event_type: str, callback: Callable
    ) -> None:
        self._listeners.setdefault(event_type, []).append(callback)

    def _emit_event(
        self,
        event_type: str,
        session: Optional[GameSession],
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        data = {
            "event": event_type,
            "session": session.to_dict() if session else None,
            "timestamp": time.time(),
        }
        if extra:
            data.update(extra)
        for callback in self._listeners.get(event_type, []):
            try:
                callback(data)
            except Exception as exc:
                logger.warning("Event listener error: %s", exc)


def get_game_runtime() -> GameRuntime:
    return GameRuntime.get_instance()
