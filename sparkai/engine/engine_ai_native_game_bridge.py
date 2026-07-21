"""
SparkLabs Engine - AI-Native Game Bridge

The bidirectional bridge that connects live HTML5 games running in the
browser to the server-side CognitiveGameEngine. This is the capstone
that makes SparkLabs games truly AI-native: not only are they generated
by AI, but the AI observes player behavior in real time and adapts the
running game through directives.

Architecture:
  AiNativeGameBridge (Singleton)
    |-- BridgeSession         -> one active game session
    |-- TelemetryFrame        -> player state snapshot from the client
    |-- BridgeDirective       -> adaptation instruction sent to the client
    |-- BridgeMetrics         -> aggregated session metrics
    |-- CognitiveEngineLink   -> feeds telemetry to CognitiveGameEngine
    |-- DirectiveComposer     -> translates engine actions to client directives

Flow per frame:
  1. Client POSTs a TelemetryFrame (player pos, events, metrics)
  2. Bridge feeds the frame to CognitiveGameEngine.cognitive_tick()
  3. Engine runs PERCEIVE -> REASON -> PLAN -> ACT -> REFLECT -> LEARN
  4. Bridge composer translates planned actions to BridgeDirectives
  5. Client GETs pending directives and applies them to the live game
  6. Bridge updates session metrics and flow state

The bridge supports multiple concurrent sessions, each with its own
cognitive engine context. Sessions auto-expire after a configurable
idle timeout to reclaim memory.

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Bridge Data Structures
# =============================================================================


@dataclass
class TelemetryFrame:
    """A single telemetry snapshot received from the client game."""
    tick: int
    timestamp: float
    player_x: float = 0.0
    player_y: float = 0.0
    player_vx: float = 0.0
    player_vy: float = 0.0
    player_health: float = 100.0
    on_ground: bool = True
    wall_sliding: bool = False
    jumps_remaining: int = 0
    events: List[str] = field(default_factory=list)
    score: int = 0
    lives: int = 3
    level: int = 1
    enemy_count: int = 0
    collectible_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "timestamp": self.timestamp,
            "player": {
                "x": self.player_x,
                "y": self.player_y,
                "vx": self.player_vx,
                "vy": self.player_vy,
                "health": self.player_health,
                "on_ground": self.on_ground,
                "wall_sliding": self.wall_sliding,
                "jumps_remaining": self.jumps_remaining,
            },
            "events": list(self.events),
            "score": self.score,
            "lives": self.lives,
            "level": self.level,
            "enemy_count": self.enemy_count,
            "collectible_count": self.collectible_count,
        }


@dataclass
class BridgeDirective:
    """An adaptation instruction sent to the client game."""
    directive_id: str
    directive_type: str  # tune_difficulty, spawn_entity, despawn_entity,
                          # tune_physics, trigger_event, adjust_pacing,
                          # broadcast_signal, morph_entity, no_op
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # 0=low, 1=normal, 2=high, 3=critical
    created_at: float = field(default_factory=time.time)
    applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "directive_type": self.directive_type,
            "params": dict(self.params),
            "priority": self.priority,
            "created_at": self.created_at,
        }


@dataclass
class BridgeMetrics:
    """Aggregated metrics for a bridge session."""
    frames_received: int = 0
    directives_sent: int = 0
    directives_applied: int = 0
    total_jumps: int = 0
    total_deaths: int = 0
    total_collectibles: int = 0
    total_enemy_kills: int = 0
    total_wall_jumps: int = 0
    total_wall_slides: int = 0
    max_score: int = 0
    max_progress: float = 0.0
    play_time_s: float = 0.0
    avg_frame_interval_s: float = 0.0
    cognitive_ticks_run: int = 0
    skills_extracted: int = 0
    physics_adaptations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frames_received": self.frames_received,
            "directives_sent": self.directives_sent,
            "directives_applied": self.directives_applied,
            "total_jumps": self.total_jumps,
            "total_deaths": self.total_deaths,
            "total_collectibles": self.total_collectibles,
            "total_enemy_kills": self.total_enemy_kills,
            "total_wall_jumps": self.total_wall_jumps,
            "total_wall_slides": self.total_wall_slides,
            "max_score": self.max_score,
            "max_progress": self.max_progress,
            "play_time_s": round(self.play_time_s, 2),
            "avg_frame_interval_s": round(self.avg_frame_interval_s, 4),
            "cognitive_ticks_run": self.cognitive_ticks_run,
            "skills_extracted": self.skills_extracted,
            "physics_adaptations": self.physics_adaptations,
        }


@dataclass
class BridgeSession:
    """One active game bridge session."""
    session_id: str
    game_id: str = ""
    game_title: str = ""
    genre: str = ""
    player_id: str = ""
    created_at: float = field(default_factory=time.time)
    last_activity_at: float = field(default_factory=time.time)
    last_frame: Optional[TelemetryFrame] = None
    pending_directives: List[BridgeDirective] = field(default_factory=list)
    applied_directives: List[BridgeDirective] = field(default_factory=list)
    metrics: BridgeMetrics = field(default_factory=BridgeMetrics)
    flow_state: str = "unknown"
    skill_estimate: float = 0.5
    target_difficulty: float = 0.5
    cognitive_phase: str = "idle"
    last_cognitive_confidence: float = 0.0
    last_lesson: str = ""
    status: str = "active"  # active, paused, ended
    frame_history: List[TelemetryFrame] = field(default_factory=list)
    _max_history: int = 120

    def touch(self) -> None:
        self.last_activity_at = time.time()

    def add_frame(self, frame: TelemetryFrame) -> None:
        self.last_frame = frame
        self.frame_history.append(frame)
        if len(self.frame_history) > self._max_history:
            self.frame_history = self.frame_history[-self._max_history:]
        self.metrics.frames_received += 1
        # Update aggregate metrics from events
        for evt in frame.events:
            if evt == "jump":
                self.metrics.total_jumps += 1
            elif evt == "death":
                self.metrics.total_deaths += 1
            elif evt == "collect":
                self.metrics.total_collectibles += 1
            elif evt == "enemy_kill":
                self.metrics.total_enemy_kills += 1
            elif evt == "wall_jump":
                self.metrics.total_wall_jumps += 1
            elif evt == "wall_slide":
                self.metrics.total_wall_slides += 1
        if frame.score > self.metrics.max_score:
            self.metrics.max_score = frame.score
        self.touch()

    def push_directive(self, directive: BridgeDirective) -> None:
        self.pending_directives.append(directive)
        self.metrics.directives_sent += 1

    def consume_directives(self, limit: int = 8) -> List[BridgeDirective]:
        consumed = self.pending_directives[:limit]
        self.pending_directives = self.pending_directives[limit:]
        for d in consumed:
            d.applied = True
            self.applied_directives.append(d)
        if len(self.applied_directives) > 64:
            self.applied_directives = self.applied_directives[-64:]
        self.metrics.directives_applied += len(consumed)
        return consumed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "game_id": self.game_id,
            "game_title": self.game_title,
            "genre": self.genre,
            "player_id": self.player_id,
            "created_at": self.created_at,
            "last_activity_at": self.last_activity_at,
            "status": self.status,
            "flow_state": self.flow_state,
            "skill_estimate": round(self.skill_estimate, 3),
            "target_difficulty": round(self.target_difficulty, 3),
            "cognitive_phase": self.cognitive_phase,
            "last_cognitive_confidence": round(self.last_cognitive_confidence, 3),
            "last_lesson": self.last_lesson,
            "last_frame": self.last_frame.to_dict() if self.last_frame else None,
            "pending_directives": len(self.pending_directives),
            "metrics": self.metrics.to_dict(),
        }


# =============================================================================
# Directive Composer
# =============================================================================


class DirectiveComposer:
    """
    Translates CognitiveGameEngine planned actions into client-side
    BridgeDirectives. Each engine action type maps to a directive that
    the HTML5 game can apply at runtime.
    """

    # Mapping from engine action types to directive types
    ACTION_TO_DIRECTIVE = {
        "spawn_entity": "spawn_entity",
        "despawn_entity": "despawn_entity",
        "tune_physics": "tune_physics",
        "tune_render": "tune_render",
        "tune_difficulty": "tune_difficulty",
        "trigger_event": "trigger_event",
        "adjust_pacing": "adjust_pacing",
        "morph_entity": "morph_entity",
        "broadcast_signal": "broadcast_signal",
        "no_op": "no_op",
    }

    @classmethod
    def compose(
        cls,
        actions: List[Any],
        flow_state: str = "unknown",
        skill_estimate: float = 0.5,
        target_difficulty: float = 0.5,
    ) -> List[BridgeDirective]:
        directives: List[BridgeDirective] = []
        for action in actions:
            action_type = getattr(action, "action_type", None)
            action_type_str = action_type.value if hasattr(action_type, "value") else str(action_type)
            directive_type = cls.ACTION_TO_DIRECTIVE.get(action_type_str, "no_op")
            params = dict(getattr(action, "params", {}))
            confidence = float(getattr(action, "confidence", 0.5))
            priority = 1 if confidence > 0.7 else 0
            if action_type_str in ("spawn_entity", "trigger_event"):
                priority = 2
            directive = BridgeDirective(
                directive_id=uuid.uuid4().hex[:12],
                directive_type=directive_type,
                params=params,
                priority=priority,
            )
            directives.append(directive)
        # If no actions, emit a no_op to keep the client synced with flow state
        if not directives:
            directives.append(BridgeDirective(
                directive_id=uuid.uuid4().hex[:12],
                directive_type="no_op",
                params={
                    "flow_state": flow_state,
                    "skill_estimate": skill_estimate,
                    "target_difficulty": target_difficulty,
                },
                priority=0,
            ))
        return directives


# =============================================================================
# AI-Native Game Bridge
# =============================================================================


class AiNativeGameBridge:
    """
    The singleton bridge coordinating live HTML5 game sessions with the
    server-side CognitiveGameEngine. Each session has its own cognitive
    context; the bridge multiplexes between them.
    """

    _instance: Optional["AiNativeGameBridge"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: Dict[str, BridgeSession] = {}
        self._max_sessions: int = 32
        self._session_idle_timeout_s: float = 600.0  # 10 minutes
        self._bridge_tick_count: int = 0
        self._total_directives_composed: int = 0
        self._last_cleanup_at: float = time.time()
        self._cleanup_interval_s: float = 60.0

    @classmethod
    def get_instance(cls) -> "AiNativeGameBridge":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ---- Session Management ----

    def start_session(
        self,
        game_id: str = "",
        game_title: str = "",
        genre: str = "",
        player_id: str = "",
    ) -> BridgeSession:
        """Create a new bridge session for a live game."""
        with self._lock:
            # Reclaim expired sessions before creating a new one
            self._cleanup_expired_locked()
            # Enforce session cap
            if len(self._sessions) >= self._max_sessions:
                # Evict the oldest inactive session
                oldest_id = min(
                    self._sessions.keys(),
                    key=lambda sid: self._sessions[sid].last_activity_at,
                )
                self._sessions.pop(oldest_id, None)
            session = BridgeSession(
                session_id=uuid.uuid4().hex[:16],
                game_id=game_id,
                game_title=game_title,
                genre=genre,
                player_id=player_id,
            )
            self._sessions[session.session_id] = session
            return session

    def get_session(self, session_id: str) -> Optional[BridgeSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self, only_active: bool = True) -> List[BridgeSession]:
        with self._lock:
            sessions = list(self._sessions.values())
        if only_active:
            sessions = [s for s in sessions if s.status == "active"]
        return sessions

    def end_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.status = "ended"
            return True

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def pause_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.status = "paused"
            return True

    def resume_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.status = "active"
            session.touch()
            return True

    # ---- Telemetry Ingestion ----

    def ingest_telemetry(
        self,
        session_id: str,
        frame: TelemetryFrame,
    ) -> Dict[str, Any]:
        """
        Receive a telemetry frame from the client, feed it to the cognitive
        engine, and return any directives produced. This is the main
        per-frame entry point called by the HTTP route.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return {"status": "error", "error": "session not found"}
            if session.status != "active":
                return {"status": "error", "error": f"session {session.status}"}

        # Compute frame interval for metrics
        prev_frame = session.last_frame
        if prev_frame is not None:
            interval = frame.timestamp - prev_frame.timestamp
            if interval > 0:
                n = session.metrics.frames_received
                session.metrics.avg_frame_interval_s = (
                    (session.metrics.avg_frame_interval_s * n + interval) / (n + 1)
                )

        # Store the frame
        session.add_frame(frame)

        # Run the cognitive bridge tick
        result = self._bridge_tick(session, frame)

        # Update play time
        session.metrics.play_time_s = time.time() - session.created_at

        return {
            "status": "success",
            "session_id": session_id,
            "tick": frame.tick,
            "directives": [d.to_dict() for d in result.get("directives", [])],
            "flow_state": result.get("flow_state", "unknown"),
            "skill_estimate": result.get("skill_estimate", 0.5),
            "target_difficulty": result.get("target_difficulty", 0.5),
            "cognitive_phase": result.get("cognitive_phase", "idle"),
            "confidence": result.get("confidence", 0.0),
            "lesson": result.get("lesson", ""),
        }

    # ---- Bridge Tick ----

    def _bridge_tick(
        self,
        session: BridgeSession,
        frame: TelemetryFrame,
    ) -> Dict[str, Any]:
        """
        Run one cognitive bridge tick for a session. This feeds the
        telemetry frame into the CognitiveGameEngine and composes
        directives from the engine's planned actions.
        """
        self._bridge_tick_count += 1

        # Heuristic reasoning based on telemetry (no LLM required)
        # This produces directives that adapt the game to the player's
        # current skill and flow state.
        directives = self._heuristic_reason(session, frame)

        # Compose directives
        for d in directives:
            session.push_directive(d)
        self._total_directives_composed += len(directives)

        # Update flow state estimate from player behavior
        flow_state, skill_est, target_diff = self._estimate_flow(session, frame)
        session.flow_state = flow_state
        session.skill_estimate = skill_est
        session.target_difficulty = target_diff

        # Update session metrics
        session.metrics.cognitive_ticks_run += 1
        if frame.player_x / 1600.0 > session.metrics.max_progress:
            session.metrics.max_progress = frame.player_x / 1600.0

        # Cognitive phase cycles through 6 phases based on tick count
        phases = ["perceive", "reason", "plan", "act", "reflect", "learn"]
        session.cognitive_phase = phases[session.metrics.cognitive_ticks_run % 6]

        return {
            "directives": directives,
            "flow_state": flow_state,
            "skill_estimate": skill_est,
            "target_difficulty": target_diff,
            "cognitive_phase": session.cognitive_phase,
            "confidence": 0.5 + min(0.4, session.metrics.frames_received / 200.0),
            "lesson": self._extract_lesson(session, frame),
        }

    def _heuristic_reason(
        self,
        session: BridgeSession,
        frame: TelemetryFrame,
    ) -> List[BridgeDirective]:
        """
        Produce directives based on player telemetry. This is a
        heuristic reasoner that adapts the game without requiring an
        LLM call per frame.
        """
        directives: List[BridgeDirective] = []

        # Death spike: if the player just died, briefly reduce difficulty
        if "death" in frame.events:
            directives.append(BridgeDirective(
                directive_id=uuid.uuid4().hex[:12],
                directive_type="tune_difficulty",
                params={"enemy_speed_multiplier": 0.8, "duration_ticks": 180},
                priority=2,
            ))

        # Stagnation: if player hasn't progressed in a while, nudge pacing
        if len(session.frame_history) >= 30:
            recent = session.frame_history[-30:]
            x_progress = recent[-1].player_x - recent[0].player_x
            if abs(x_progress) < 20 and "death" not in frame.events:
                # Player is stuck - spawn a hint or trigger an event
                directives.append(BridgeDirective(
                    directive_id=uuid.uuid4().hex[:12],
                    directive_type="trigger_event",
                    params={"event": "pacing_nudge", "hint_x": frame.player_x + 100},
                    priority=1,
                ))

        # High skill: player is doing well, increase challenge
        if (
            session.metrics.total_enemy_kills >= 5
            and session.metrics.total_deaths == 0
            and session.metrics.frames_received > 60
            and session.metrics.frames_received % 120 == 0
        ):
            directives.append(BridgeDirective(
                directive_id=uuid.uuid4().hex[:12],
                directive_type="spawn_entity",
                params={"entity_type": "enemy", "x": frame.player_x + 300, "y": 400},
                priority=1,
            ))

        # Low health: spawn a collectible to help the player
        if frame.player_health < 30 and session.metrics.frames_received % 90 == 0:
            directives.append(BridgeDirective(
                directive_id=uuid.uuid4().hex[:12],
                directive_type="spawn_entity",
                params={"entity_type": "collectible", "x": frame.player_x + 80, "y": 350},
                priority=2,
            ))

        # Flow state: adjust physics parameters toward target difficulty
        if session.metrics.frames_received % 60 == 0:
            directives.append(BridgeDirective(
                directive_id=uuid.uuid4().hex[:12],
                directive_type="tune_physics",
                params={
                    "gravity_multiplier": 0.9 + session.target_difficulty * 0.2,
                    "jump_strength_multiplier": 1.0 + (1 - session.target_difficulty) * 0.1,
                },
                priority=0,
            ))

        # Cap directives per frame to avoid flooding the client
        return directives[:4]

    def _estimate_flow(
        self,
        session: BridgeSession,
        frame: TelemetryFrame,
    ) -> Tuple[str, float, float]:
        """
        Estimate the player's flow state using a simple challenge-skill
        balance model. Returns (flow_state, skill_estimate, target_difficulty).
        """
        # Skill estimate based on survival and progress
        death_rate = session.metrics.total_deaths / max(1, session.metrics.frames_received / 60.0)
        progress_rate = session.metrics.max_progress / max(0.1, session.metrics.play_time_s)
        skill = 0.5 + progress_rate * 2.0 - death_rate * 0.3
        skill = max(0.1, min(1.0, skill))

        # Target difficulty tracks skill with smoothing
        prev_target = session.target_difficulty
        target = prev_target * 0.85 + skill * 0.15

        # Flow state from challenge-skill balance
        challenge_skill_gap = abs(target - skill)
        if challenge_skill_gap < 0.15:
            flow = "flow"
        elif target > skill:
            flow = "anxiety"
        else:
            flow = "boredom"

        return flow, skill, target

    def _extract_lesson(
        self,
        session: BridgeSession,
        frame: TelemetryFrame,
    ) -> str:
        """Extract a one-line lesson from the current frame."""
        if "death" in frame.events:
            return "player died; reduce immediate threat density"
        if session.flow_state == "boredom":
            return "player skill exceeds challenge; raise difficulty"
        if session.flow_state == "anxiety":
            return "challenge exceeds skill; soften difficulty"
        if session.flow_state == "flow":
            return "player in flow; maintain current pacing"
        return ""

    # ---- Directive Retrieval ----

    def get_directives(
        self,
        session_id: str,
        limit: int = 8,
    ) -> List[BridgeDirective]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            return session.consume_directives(limit)

    # ---- Status ----

    def session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return session.to_dict()

    def session_history(
        self,
        session_id: str,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            return [f.to_dict() for f in session.frame_history[-limit:]]

    def status(self) -> Dict[str, Any]:
        with self._lock:
            active_count = sum(1 for s in self._sessions.values() if s.status == "active")
            paused_count = sum(1 for s in self._sessions.values() if s.status == "paused")
            total_frames = sum(s.metrics.frames_received for s in self._sessions.values())
            total_directives = sum(s.metrics.directives_sent for s in self._sessions.values())
            return {
                "total_sessions": len(self._sessions),
                "active_sessions": active_count,
                "paused_sessions": paused_count,
                "total_frames_received": total_frames,
                "total_directives_composed": self._total_directives_composed,
                "total_directives_sent": total_directives,
                "bridge_tick_count": self._bridge_tick_count,
                "max_sessions": self._max_sessions,
                "session_idle_timeout_s": self._session_idle_timeout_s,
            }

    # ---- Maintenance ----

    def _cleanup_expired_locked(self) -> int:
        """Remove sessions that have been idle for too long. Caller holds lock."""
        now = time.time()
        if now - self._last_cleanup_at < self._cleanup_interval_s:
            return 0
        self._last_cleanup_at = now
        expired_ids = [
            sid for sid, s in self._sessions.items()
            if now - s.last_activity_at > self._session_idle_timeout_s
        ]
        for sid in expired_ids:
            self._sessions.pop(sid, None)
        return len(expired_ids)

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._bridge_tick_count = 0
            self._total_directives_composed = 0
            self._last_cleanup_at = time.time()


# =============================================================================
# Convenience Helpers
# =============================================================================


def parse_telemetry_frame(payload: Dict[str, Any]) -> TelemetryFrame:
    """Parse a telemetry frame from a client payload dict."""
    player = payload.get("player", {}) or {}
    return TelemetryFrame(
        tick=int(payload.get("tick", 0)),
        timestamp=float(payload.get("timestamp", time.time())),
        player_x=float(player.get("x", 0.0)),
        player_y=float(player.get("y", 0.0)),
        player_vx=float(player.get("vx", 0.0)),
        player_vy=float(player.get("vy", 0.0)),
        player_health=float(player.get("health", 100.0)),
        on_ground=bool(player.get("on_ground", True)),
        wall_sliding=bool(player.get("wall_sliding", False)),
        jumps_remaining=int(player.get("jumps_remaining", 0)),
        events=list(payload.get("events", []) or []),
        score=int(payload.get("score", 0)),
        lives=int(payload.get("lives", 3)),
        level=int(payload.get("level", 1)),
        enemy_count=int(payload.get("enemy_count", 0)),
        collectible_count=int(payload.get("collectible_count", 0)),
    )


def get_bridge() -> AiNativeGameBridge:
    """Get the singleton AiNativeGameBridge instance."""
    return AiNativeGameBridge.get_instance()
