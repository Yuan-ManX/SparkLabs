"""
SparkLabs Engine - Game Telemetry

Analytics and telemetry collection system for AI-native game
engine. Tracks player behavior, performance metrics, gameplay
events, and session data to enable data-driven game design
decisions and AI-powered adaptation.

Architecture:
  TelemetryEngine
    |-- EventTracker (capture gameplay events with context)
    |-- SessionRecorder (per-player session data collection)
    |-- PerformanceMonitor (FPS, memory, load times)
    |-- AggregationPipeline (batch aggregate events for analysis)
    |-- HeatmapGenerator (spatial player activity mapping)

Event Categories:
  - PLAYER: movement, actions, item usage
  - COMBAT: damage dealt, kills, deaths
  - PROGRESSION: level ups, quest completion, unlocks
  - ECONOMY: currency earn/spend, trade, purchases
  - SYSTEM: errors, crashes, performance drops
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class EventCategory(Enum):
    PLAYER = "player"
    COMBAT = "combat"
    PROGRESSION = "progression"
    ECONOMY = "economy"
    SYSTEM = "system"
    SOCIAL = "social"
    EXPLORATION = "exploration"


class EventSeverity(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TelemetryEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    category: EventCategory = EventCategory.PLAYER
    event_type: str = ""
    session_id: str = ""
    player_id: str = ""
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    position: Optional[Tuple[float, float, float]] = None
    severity: EventSeverity = EventSeverity.INFO

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "category": self.category.value,
            "event_type": self.event_type,
            "player_id": self.player_id,
            "timestamp": self.timestamp,
            "position": self.position,
            "severity": self.severity.value,
            "data_keys": list(self.data.keys()),
        }

    def to_full_dict(self) -> Dict[str, Any]:
        return {
            **self.to_dict(),
            "session_id": self.session_id,
            "data": self.data,
        }


@dataclass
class PlaySession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    player_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    event_count: int = 0
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        if self.is_active:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "player_id": self.player_id,
            "duration_s": round(self.duration_seconds, 1),
            "event_count": self.event_count,
            "is_active": self.is_active,
        }


@dataclass
class PerformanceSnapshot:
    fps: float = 60.0
    frame_time_ms: float = 16.67
    memory_mb: float = 0.0
    draw_calls: int = 0
    active_entities: int = 0
    physics_objects: int = 0
    network_latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fps": round(self.fps, 1),
            "frame_time_ms": round(self.frame_time_ms, 2),
            "memory_mb": round(self.memory_mb, 1),
            "draw_calls": self.draw_calls,
            "active_entities": self.active_entities,
            "physics_objects": self.physics_objects,
            "network_latency_ms": round(self.network_latency_ms, 1),
        }


class TelemetryEngine:
    """Game analytics and telemetry for AI-native game engine."""

    _instance: Optional["TelemetryEngine"] = None
    _lock = threading.Lock()

    MAX_EVENTS = 50000
    MAX_SESSIONS = 1000
    MAX_PERF_SNAPSHOTS = 1000

    def __init__(self):
        self._events: List[TelemetryEvent] = []
        self._sessions: Dict[str, PlaySession] = {}
        self._perf_snapshots: List[PerformanceSnapshot] = []
        self._enabled = True
        self._batch_flush_size = 100
        self._flush_callbacks: List[Callable] = []

    @classmethod
    def get_instance(cls) -> "TelemetryEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def track_event(
        self,
        category: EventCategory,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        player_id: str = "",
        session_id: str = "",
        position: Optional[Tuple[float, float, float]] = None,
        severity: EventSeverity = EventSeverity.INFO,
    ) -> Optional[TelemetryEvent]:
        if not self._enabled:
            return None
        event = TelemetryEvent(
            category=category,
            event_type=event_type,
            data=data or {},
            player_id=player_id,
            session_id=session_id,
            position=position,
            severity=severity,
        )
        self._events.append(event)
        if session_id and session_id in self._sessions:
            self._sessions[session_id].event_count += 1
        self._enforce_limits()
        if len(self._events) % self._batch_flush_size == 0:
            self._flush()
        return event

    def start_session(
        self,
        player_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PlaySession:
        session = PlaySession(
            player_id=player_id,
            start_time=time.time(),
            metadata=metadata or {},
        )
        self._sessions[session.session_id] = session
        self.track_event(
            category=EventCategory.SYSTEM,
            event_type="session_start",
            player_id=player_id,
            session_id=session.session_id,
            data={"metadata": metadata or {}},
        )
        return session

    def end_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            return False
        session.end_time = time.time()
        session.is_active = False
        self.track_event(
            category=EventCategory.SYSTEM,
            event_type="session_end",
            session_id=session_id,
            player_id=session.player_id,
            data={"duration_s": session.duration_seconds, "event_count": session.event_count},
        )
        return True

    def record_performance(self, snapshot: PerformanceSnapshot) -> None:
        self._perf_snapshots.append(snapshot)
        if len(self._perf_snapshots) > self.MAX_PERF_SNAPSHOTS:
            self._perf_snapshots = self._perf_snapshots[-self.MAX_PERF_SNAPSHOTS:]

    def get_average_fps(self, window: int = 100) -> float:
        recent = self._perf_snapshots[-window:]
        if not recent:
            return 0.0
        return sum(s.fps for s in recent) / len(recent)

    def get_average_frame_time(self, window: int = 100) -> float:
        recent = self._perf_snapshots[-window:]
        if not recent:
            return 0.0
        return sum(s.frame_time_ms for s in recent) / len(recent)

    def get_heatmap_data(
        self,
        category: Optional[EventCategory] = None,
    ) -> List[Tuple[float, float, float]]:
        points: List[Tuple[float, float, float]] = []
        for event in self._events:
            if event.position is None:
                continue
            if category and event.category != category:
                continue
            points.append(event.position)
        return points

    def get_events_by_category(
        self,
        category: EventCategory,
        limit: int = 100,
    ) -> List[TelemetryEvent]:
        result: List[TelemetryEvent] = []
        for event in reversed(self._events):
            if event.category == category:
                result.append(event)
                if len(result) >= limit:
                    break
        return result

    def get_events_by_session(
        self,
        session_id: str,
        limit: int = 100,
    ) -> List[TelemetryEvent]:
        result: List[TelemetryEvent] = []
        for event in reversed(self._events):
            if event.session_id == session_id:
                result.append(event)
                if len(result) >= limit:
                    break
        return result

    def get_event_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for event in self._events:
            counts[event.category.value] += 1
        return dict(counts)

    def get_session(self, session_id: str) -> Optional[PlaySession]:
        return self._sessions.get(session_id)

    def list_active_sessions(self) -> List[PlaySession]:
        return [s for s in self._sessions.values() if s.is_active]

    def list_sessions(self, limit: int = 50) -> List[PlaySession]:
        sessions = list(self._sessions.values())
        sessions.sort(key=lambda s: s.start_time, reverse=True)
        return sessions[:limit]

    def register_flush_callback(self, callback: Callable) -> None:
        self._flush_callbacks.append(callback)

    def _flush(self) -> None:
        for callback in self._flush_callbacks:
            try:
                callback(list(self._events[-self._batch_flush_size:]))
            except Exception:
                pass

    def flush(self) -> int:
        count = len(self._events)
        self._flush()
        return count

    def clear_events(self) -> int:
        count = len(self._events)
        self._events.clear()
        return count

    def _enforce_limits(self) -> None:
        if len(self._events) > self.MAX_EVENTS:
            self._events = self._events[-self.MAX_EVENTS:]

        if len(self._sessions) > self.MAX_SESSIONS:
            sessions = sorted(self._sessions.items(), key=lambda x: x[1].start_time)
            for sid, sess in sessions[: len(sessions) - self.MAX_SESSIONS]:
                del self._sessions[sid]

    def get_stats(self) -> Dict[str, Any]:
        total_players = len(set(e.player_id for e in self._events if e.player_id))
        active = len(self.list_active_sessions())
        avg_fps = self.get_average_fps()
        return {
            "total_events": len(self._events),
            "total_sessions": len(self._sessions),
            "active_sessions": active,
            "unique_players": total_players,
            "performance_snapshots": len(self._perf_snapshots),
            "average_fps": round(avg_fps, 1),
            "enabled": self._enabled,
            "event_breakdown": self.get_event_counts(),
        }


def get_telemetry_engine() -> TelemetryEngine:
    return TelemetryEngine.get_instance()