"""
SparkLabs Agent - Trajectory Recorder

Session trajectory recording and replay for the AI game engine agent.
Captures agent decisions, tool calls, game state snapshots, and user
interactions during game development sessions. Enables post-mortem
analysis, quality review, and continuous improvement of the agent's
game creation capabilities through recorded session data.

Architecture:
  TrajectoryRecorder
    |-- TrajectoryStep (timestamp, phase, action, context snapshot)
    |-- GameStateSnapshot (entity tree, scene graph at point in time)
    |-- DecisionTrace (prompt → thought → action → result chain)
    |-- TrajectoryStore (file-based JSONL storage with rotation)
    |-- ReplayEngine (time-walk through recorded trajectories)

Recording Phases:
  - OBSERVE: agent reads current game state
  - THINK: agent formulates plan and reasoning
  - ACT: agent executes tool calls or code generation
  - VERIFY: agent checks results, iterates if needed
  - INTERACT: user provides feedback or new instructions
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class TrajectoryPhase(Enum):
    OBSERVE = "observe"
    THINK = "think"
    ACT = "act"
    VERIFY = "verify"
    INTERACT = "interact"
    ERROR = "error"
    COMPLETE = "complete"


@dataclass
class TrajectoryStep:
    step_id: int
    phase: TrajectoryPhase
    timestamp: float = field(default_factory=time.time)
    action_name: str = ""
    action_input: Dict[str, Any] = field(default_factory=dict)
    action_output: str = ""
    thinking: str = ""
    game_state_snapshot: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    duration_ms: float = 0.0
    success: bool = True
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "phase": self.phase.value,
            "timestamp": self.timestamp,
            "action_name": self.action_name,
            "action_input": self.action_input,
            "action_output": self.action_output[:500],
            "thinking": self.thinking[:500],
            "token_count": self.token_count,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message[:200],
        }


@dataclass
class TrajectorySession:
    session_id: str
    project_name: str = ""
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    steps: List[TrajectoryStep] = field(default_factory=list)
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    success_rate: float = 0.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    _step_counter: int = 0

    def add_step(self, step: TrajectoryStep) -> None:
        self._step_counter += 1
        step.step_id = self._step_counter
        self.steps.append(step)
        self.total_tokens += step.token_count
        self.total_duration_ms += step.duration_ms
        if self.steps:
            successes = sum(1 for s in self.steps if s.success)
            self.success_rate = successes / len(self.steps)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "project_name": self.project_name,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "step_count": len(self.steps),
            "total_tokens": self.total_tokens,
            "total_duration_ms": self.total_duration_ms,
            "success_rate": self.success_rate,
            "tags": self.tags,
        }

    def to_full_dict(self) -> dict:
        return {
            **self.to_dict(),
            "steps": [s.to_dict() for s in self.steps],
        }


class TrajectoryRecorder:
    """
    Session trajectory recording and replay system.

    Captures the full decision chain of AI agents during game
    development sessions. Each step records what the agent
    observed, thought, did, and whether it worked. This data
    powers post-session reviews, quality analysis, and
    continuous improvement of the agent's game creation skills.
    """

    _instance: Optional["TrajectoryRecorder"] = None

    def __init__(self):
        self._active_session: Optional[TrajectorySession] = None
        self._sessions: Dict[str, TrajectorySession] = {}
        self._storage_dir: str = ""
        self._auto_save: bool = True
        self._lock = threading.Lock()
        self._MAX_SESSIONS = 100

    @classmethod
    def get_instance(cls) -> "TrajectoryRecorder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_session(
        self, session_id: str, project_name: str = "", tags: Optional[List[str]] = None
    ) -> TrajectorySession:
        with self._lock:
            session = TrajectorySession(
                session_id=session_id,
                project_name=project_name,
                tags=tags or [],
            )
            self._active_session = session
            self._sessions[session_id] = session
            if len(self._sessions) > self._MAX_SESSIONS:
                oldest = min(self._sessions.keys(), key=lambda k: self._sessions[k].started_at)
                del self._sessions[oldest]
            return session

    def record(
        self,
        phase: TrajectoryPhase,
        action_name: str = "",
        action_input: Optional[Dict[str, Any]] = None,
        action_output: str = "",
        thinking: str = "",
        token_count: int = 0,
        duration_ms: float = 0.0,
        success: bool = True,
        error_message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TrajectoryStep]:
        if not self._active_session:
            return None

        step = TrajectoryStep(
            step_id=0,
            phase=phase,
            action_name=action_name,
            action_input=action_input or {},
            action_output=action_output,
            thinking=thinking,
            token_count=token_count,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
        )

        with self._lock:
            self._active_session.add_step(step)

        if self._auto_save and self._storage_dir:
            self._save_current()

        return step

    def end_session(self) -> Optional[TrajectorySession]:
        if not self._active_session:
            return None
        with self._lock:
            self._active_session.ended_at = time.time()
            session = self._active_session
            self._active_session = None
            if self._storage_dir:
                self._save_session_to_file(session)
            return session

    def get_active(self) -> Optional[TrajectorySession]:
        return self._active_session

    def get_session(self, session_id: str) -> Optional[TrajectorySession]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[TrajectorySession]:
        return sorted(
            self._sessions.values(), key=lambda s: s.started_at, reverse=True
        )

    def find_by_tag(self, tag: str) -> List[TrajectorySession]:
        return [s for s in self._sessions.values() if tag in s.tags]

    def export_session(self, session_id: str, output_path: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        try:
            with open(output_path, "w") as f:
                json.dump(session.to_full_dict(), f, indent=2)
            return True
        except Exception:
            return False

    def import_session(self, input_path: str) -> Optional[TrajectorySession]:
        try:
            with open(input_path, "r") as f:
                data = json.load(f)
            session = TrajectorySession(
                session_id=data.get("session_id", ""),
                project_name=data.get("project_name", ""),
                started_at=data.get("started_at", 0),
                ended_at=data.get("ended_at"),
                tags=data.get("tags", []),
                metadata=data.get("metadata", {}),
            )
            session.total_tokens = data.get("total_tokens", 0)
            session.total_duration_ms = data.get("total_duration_ms", 0)
            session.success_rate = data.get("success_rate", 0)
            self._sessions[session.session_id] = session
            return session
        except Exception:
            return None

    def replay_summary(self, session_id: str) -> Optional[str]:
        session = self._sessions.get(session_id)
        if not session:
            return None

        lines = [
            f"Session: {session.session_id}",
            f"Project: {session.project_name}",
            f"Duration: {session.total_duration_ms / 1000:.1f}s",
            f"Steps: {len(session.steps)}",
            f"Tokens: {session.total_tokens}",
            f"Success Rate: {session.success_rate:.1%}",
            "",
            "Timeline:",
        ]
        for step in session.steps:
            icon = "✓" if step.success else "✗"
            lines.append(
                f"  [{step.phase.value}] {icon} {step.action_name} "
                f"({step.duration_ms:.0f}ms, {step.token_count} tokens)"
            )
        return "\n".join(lines)

    def set_storage_dir(self, directory: str) -> None:
        self._storage_dir = directory
        os.makedirs(directory, exist_ok=True)

    def _save_current(self) -> None:
        if self._active_session and self._storage_dir:
            self._save_session_to_file(self._active_session)

    def _save_session_to_file(self, session: TrajectorySession) -> None:
        path = os.path.join(self._storage_dir, f"{session.session_id}.jsonl")
        try:
            with open(path, "a") as f:
                for step in session.steps:
                    f.write(json.dumps(step.to_dict()) + "\n")
        except Exception:
            pass

    def get_stats(self) -> dict:
        with self._lock:
            total_steps = sum(len(s.steps) for s in self._sessions.values())
            total_tokens_all = sum(s.total_tokens for s in self._sessions.values())
            return {
                "total_sessions": len(self._sessions),
                "active_session": self._active_session is not None,
                "total_steps_recorded": total_steps,
                "total_tokens": total_tokens_all,
                "auto_save": self._auto_save,
                "storage_dir": self._storage_dir,
            }

    def reset(self) -> None:
        with self._lock:
            self._active_session = None
            self._sessions.clear()


def get_trajectory_recorder() -> TrajectoryRecorder:
    return TrajectoryRecorder.get_instance()
