"""
SparkLabs Agent - AI-Native Game Brain

The high-level cognitive controller that fuses the unified AgentKernel with
the KernelEngineIntegrator to provide real-time game direction. The brain
converts live engine signals into directorial decisions: when to raise
difficulty, when to slow pacing, when to inject narrative beats, and when
to surface emergent gameplay opportunities.

Unlike low-level agents that operate on individual tasks, the Game Brain
operates on the *experience curve* of the game as a whole. It continuously
models player state, narrative tension, mechanical load, and aesthetic
coherence, then issues directorial commands through the integrator.

Architecture:
  GameBrain (Singleton)
    |-- PlayerModeler        -> tracks skill, fatigue, frustration, delight
    |-- PacingDirector       -> shapes tension/release curves over time
    |-- DifficultyTuner      -> adjusts challenge parameters in real time
    |-- NarrativeConductor   -> injects story beats at dramatic inflection points
    |-- EmergenceDetector    -> spots emergent gameplay patterns worth amplifying
    |-- CoherenceGuard       -> prevents contradictory direction signals
    |-- DirectiveQueue       -> serializes directorial intents into engine commands

Cognitive Cadence (per brain tick):
  observe player + world -> model experience -> decide directive -> dispatch
  -> observe outcome -> refine player model -> learn

Original SparkLabs design - real-time directorial cognition for AI-native games.
"""

from __future__ import annotations

import logging
import math
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Brain Enums
# =============================================================================


class BrainPhase(Enum):
    """Phases of a single brain tick."""
    OBSERVE = "observe"
    MODEL = "model"
    DECIDE = "decide"
    DISPATCH = "dispatch"
    REFINE = "refine"
    LEARN = "learn"


class DirectiveKind(Enum):
    """Kinds of directorial directives the brain can issue."""
    ADJUST_DIFFICULTY = "adjust_difficulty"
    SHIFT_PACING = "shift_pacing"
    INJECT_NARRATIVE = "inject_narrative"
    HIGHLIGHT_EMERGENCE = "highlight_emergence"
    CALM_PLAYER = "calm_player"
    CHALLENGE_PLAYER = "challenge_player"
    REWARD_PLAYER = "reward_player"
    CHANGE_SCENE_MOOD = "change_scene_mood"
    SPAWN_EVENT = "spawn_event"
    DESPAWN_ELEMENT = "despawn_element"
    CUSTOM = "custom"


class PlayerMood(Enum):
    """Coarse player mood classification driving directorial decisions."""
    ELATED = "elated"
    ENGAGED = "engaged"
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    BORED = "bored"
    OVERWHELMED = "overwhelmed"


class PacingZone(Enum):
    """Pacing zones the brain steers the experience toward."""
    INTRO = "intro"            # gentle onboarding
    RISING = "rising"          # escalation
    PEAK = "peak"              # climactic
    RELIEF = "relief"          # cooldown after peak
    PLATEAU = "plateau"        # sustained engagement
    FINALE = "finale"          # closing arc


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class PlayerState:
    """Live model of the player's skill, fatigue, and emotional state."""
    skill: float = 0.5          # 0..1 estimated player skill
    fatigue: float = 0.0        # 0..1 cumulative fatigue
    frustration: float = 0.0    # 0..1 recent frustration
    delight: float = 0.5        # 0..1 recent delight
    engagement: float = 0.5     # 0..1 attention depth
    retries: int = 0            # consecutive retries
    successes: int = 0          # consecutive successes
    session_seconds: float = 0.0
    last_updated: float = field(default_factory=time.time)

    def mood(self) -> PlayerMood:
        """Derive a coarse mood from the model."""
        if self.frustration > 0.7:
            return PlayerMood.FRUSTRATED
        if self.delight > 0.75 and self.engagement > 0.6:
            return PlayerMood.ELATED
        if self.engagement > 0.6:
            return PlayerMood.ENGAGED
        if self.fatigue > 0.7 or self.engagement < 0.25:
            return PlayerMood.BORED
        if self.frustration > 0.4 and self.skill < 0.4:
            return PlayerMood.OVERWHELMED
        return PlayerMood.NEUTRAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill": round(self.skill, 3),
            "fatigue": round(self.fatigue, 3),
            "frustration": round(self.frustration, 3),
            "delight": round(self.delight, 3),
            "engagement": round(self.engagement, 3),
            "retries": self.retries,
            "successes": self.successes,
            "session_seconds": round(self.session_seconds, 1),
            "mood": self.mood().value,
        }


@dataclass
class PacingState:
    """Tracks the current pacing position and trajectory."""
    zone: PacingZone = PacingZone.INTRO
    tension: float = 0.3        # 0..1 current dramatic tension
    target_tension: float = 0.5 # 0..1 desired tension
    time_in_zone: float = 0.0   # seconds in current zone
    peak_count: int = 0         # number of peaks experienced

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone": self.zone.value,
            "tension": round(self.tension, 3),
            "target_tension": round(self.target_tension, 3),
            "time_in_zone": round(self.time_in_zone, 1),
            "peak_count": self.peak_count,
        }


@dataclass
class Directive:
    """A directorial directive issued by the brain."""
    directive_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    kind: DirectiveKind = DirectiveKind.CUSTOM
    intent: str = ""                  # human-readable intent summary
    args: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0                 # higher = more urgent
    confidence: float = 0.5           # 0..1 brain confidence in this directive
    issued_at: float = field(default_factory=time.time)
    expected_effect: str = ""


@dataclass
class BrainTickResult:
    """Result of one brain tick for observability."""
    tick: int = 0
    phase: BrainPhase = BrainPhase.OBSERVE
    player_modeled: bool = False
    pacing_updated: bool = False
    directives_issued: int = 0
    emergence_detected: bool = False
    duration_s: float = 0.0
    notes: List[str] = field(default_factory=list)


# =============================================================================
# Player Modeler
# =============================================================================


class PlayerModeler:
    """
    Maintains a live model of the player by aggregating engine events.
    Updates skill, fatigue, frustration, delight, and engagement from
    observable signals (successes, retries, time, input cadence).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state: PlayerState = PlayerState()
        self._event_buffer: Deque[Dict[str, Any]] = deque(maxlen=64)
        self._last_input_time: float = time.time()

    def ingest(self, event: Dict[str, Any]) -> None:
        """Ingest a single engine event and update the player model."""
        with self._lock:
            self._event_buffer.append(event)
            kind = event.get("kind", "")
            data = event.get("data", {}) or {}

            now = time.time()
            elapsed = now - self._state.last_updated
            self._state.last_updated = now
            self._state.session_seconds += elapsed

            if kind == "player_input":
                self._state.engagement = min(1.0, self._state.engagement + 0.02)
                self._last_input_time = now
                self._state.fatigue = max(0.0, self._state.fatigue - 0.005)
            elif kind == "game_state_change":
                transition = data.get("transition", "")
                if transition == "success" or data.get("success"):
                    self._state.successes += 1
                    self._state.retries = 0
                    self._state.delight = min(1.0, self._state.delight + 0.1)
                    self._state.frustration = max(0.0, self._state.frustration - 0.15)
                    self._state.skill = min(1.0, self._state.skill + 0.01)
                elif transition == "failure" or data.get("failure"):
                    self._state.retries += 1
                    self._state.successes = 0
                    self._state.frustration = min(1.0, self._state.frustration + 0.1)
                    self._state.delight = max(0.0, self._state.delight - 0.05)
            elif kind == "collision":
                # Minor collisions nudge frustration upward
                self._state.frustration = min(1.0, self._state.frustration + 0.02)
            elif kind == "performance":
                # Low FPS or stutter increases fatigue
                fps = data.get("fps", 60)
                if fps < 30:
                    self._state.fatigue = min(1.0, self._state.fatigue + 0.01)

            # Decay engagement and delight over time
            self._state.engagement = max(0.0, self._state.engagement - 0.001 * elapsed)
            self._state.delight = max(0.0, self._state.delight - 0.002 * elapsed)
            # Fatigue grows slowly with session time
            self._state.fatigue = min(1.0, self._state.fatigue + 0.0005 * elapsed)

    def state(self) -> PlayerState:
        with self._lock:
            # Return a copy
            return PlayerState(
                skill=self._state.skill,
                fatigue=self._state.fatigue,
                frustration=self._state.frustration,
                delight=self._state.delight,
                engagement=self._state.engagement,
                retries=self._state.retries,
                successes=self._state.successes,
                session_seconds=self._state.session_seconds,
                last_updated=self._state.last_updated,
            )

    def reset(self) -> None:
        with self._lock:
            self._state = PlayerState()
            self._event_buffer.clear()


# =============================================================================
# Pacing Director
# =============================================================================


class PacingDirector:
    """
    Steers the dramatic pacing of the game. Maintains a tension curve
    and decides when to transition between pacing zones based on player
    state and elapsed time.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state: PacingState = PacingState()

    def update(self, player: PlayerState, dt: float) -> PacingState:
        """Advance pacing by dt seconds, given the current player state."""
        with self._lock:
            self._state.time_in_zone += dt

            # Move tension toward target
            delta = self._state.target_tension - self._state.tension
            self._state.tension = max(0.0, min(1.0, self._state.tension + delta * 0.1))

            # Decide zone transitions
            mood = player.mood()
            time_in_zone = self._state.time_in_zone

            if self._state.zone == PacingZone.INTRO and time_in_zone > 30:
                self._transition(PacingZone.RISING)
            elif self._state.zone == PacingZone.RISING:
                if mood == PlayerMood.FRUSTRATED and time_in_zone > 20:
                    self._transition(PacingZone.RELIEF)
                elif time_in_zone > 60 and self._state.tension > 0.6:
                    self._transition(PacingZone.PEAK)
            elif self._state.zone == PacingZone.PEAK:
                if time_in_zone > 25:
                    self._transition(PacingZone.RELIEF)
            elif self._state.zone == PacingZone.RELIEF:
                if time_in_zone > 20:
                    self._transition(PacingZone.PLATEAU)
            elif self._state.zone == PacingZone.PLATEAU:
                if mood == PlayerMood.BORED and time_in_zone > 30:
                    self._transition(PacingZone.RISING)
                elif player.session_seconds > 600 and time_in_zone > 45:
                    self._transition(PacingZone.FINALE)

            # Adjust target tension based on zone
            targets = {
                PacingZone.INTRO: 0.3,
                PacingZone.RISING: 0.6,
                PacingZone.PEAK: 0.9,
                PacingZone.RELIEF: 0.25,
                PacingZone.PLATEAU: 0.5,
                PacingZone.FINALE: 0.95,
            }
            self._state.target_tension = targets.get(self._state.zone, 0.5)

            # Modulate target by player mood
            if mood == PlayerMood.FRUSTRATED:
                self._state.target_tension = max(0.1, self._state.target_tension - 0.2)
            elif mood == PlayerMood.ELATED:
                self._state.target_tension = min(1.0, self._state.target_tension + 0.1)

            return self._state

    def _transition(self, new_zone: PacingZone) -> None:
        if new_zone == self._state.zone:
            return
        logger.debug("Pacing transition: %s -> %s", self._state.zone.value, new_zone.value)
        if new_zone == PacingZone.PEAK:
            self._state.peak_count += 1
        self._state.zone = new_zone
        self._state.time_in_zone = 0.0

    def state(self) -> PacingState:
        with self._lock:
            return PacingState(
                zone=self._state.zone,
                tension=self._state.tension,
                target_tension=self._state.target_tension,
                time_in_zone=self._state.time_in_zone,
                peak_count=self._state.peak_count,
            )

    def reset(self) -> None:
        with self._lock:
            self._state = PacingState()


# =============================================================================
# Difficulty Tuner
# =============================================================================


class DifficultyTuner:
    """
    Translates player skill and frustration into concrete difficulty
    parameters. Uses a simple PID-like controller to keep the player
    in the flow channel (challenge just above skill).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._difficulty: float = 0.5  # 0..1
        self._target: float = 0.55
        self._adjustment_history: Deque[float] = deque(maxlen=32)

    def update(self, player: PlayerState) -> float:
        """Return the new difficulty level (0..1)."""
        with self._lock:
            mood = player.mood()

            # Target difficulty hovers slightly above player skill
            self._target = min(1.0, player.skill + 0.1)

            # Frustrated players need relief
            if mood == PlayerMood.FRUSTRATED:
                self._target = max(0.1, player.skill - 0.15)
            elif mood == PlayerMood.OVERWHELMED:
                self._target = max(0.05, player.skill - 0.25)
            elif mood == PlayerMood.BORED:
                self._target = min(1.0, player.skill + 0.25)
            elif mood == PlayerMood.ELATED:
                self._target = min(1.0, player.skill + 0.2)

            # Move difficulty toward target
            delta = self._target - self._difficulty
            self._difficulty = max(0.0, min(1.0, self._difficulty + delta * 0.15))
            self._adjustment_history.append(self._difficulty)
            return self._difficulty

    def difficulty(self) -> float:
        with self._lock:
            return self._difficulty

    def target(self) -> float:
        with self._lock:
            return self._target

    def reset(self) -> None:
        with self._lock:
            self._difficulty = 0.5
            self._target = 0.55
            self._adjustment_history.clear()


# =============================================================================
# Narrative Conductor
# =============================================================================


class NarrativeConductor:
    """
    Decides when to inject narrative beats. Uses pacing zone transitions
    and player mood as primary triggers.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._last_beat_time: float = 0.0
        self._beat_count: int = 0
        self._min_interval: float = 15.0
        self._pending_beats: Deque[Dict[str, Any]] = deque()

    def consider(
        self,
        pacing: PacingState,
        player: PlayerState,
        current_time: float,
    ) -> Optional[Dict[str, Any]]:
        """Consider whether to inject a narrative beat right now."""
        with self._lock:
            if current_time - self._last_beat_time < self._min_interval:
                return None

            beat: Optional[Dict[str, Any]] = None

            # Inject beats on zone transitions
            if pacing.zone == PacingZone.PEAK and pacing.time_in_zone < 2:
                beat = {
                    "type": "climax",
                    "tone": "intense",
                    "intensity": 0.9,
                    "trigger": "peak_zone_enter",
                }
            elif pacing.zone == PacingZone.RELIEF and pacing.time_in_zone < 2:
                beat = {
                    "type": "breather",
                    "tone": "calm",
                    "intensity": 0.2,
                    "trigger": "relief_zone_enter",
                }
            elif pacing.zone == PacingZone.FINALE and pacing.time_in_zone < 2:
                beat = {
                    "type": "finale",
                    "tone": "epic",
                    "intensity": 1.0,
                    "trigger": "finale_zone_enter",
                }
            elif player.mood() == PlayerMood.FRUSTRATED and player.retries > 3:
                beat = {
                    "type": "encouragement",
                    "tone": "warm",
                    "intensity": 0.4,
                    "trigger": "high_retries",
                }
            elif player.mood() == PlayerMood.BORED and player.session_seconds > 60:
                beat = {
                    "type": "twist",
                    "tone": "intriguing",
                    "intensity": 0.6,
                    "trigger": "boredom",
                }

            if beat is not None:
                self._last_beat_time = current_time
                self._beat_count += 1
                beat["beat_id"] = f"beat_{self._beat_count:04d}"
                beat["timestamp"] = current_time
                return beat
            return None

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "beat_count": self._beat_count,
                "last_beat_time": self._last_beat_time,
                "min_interval": self._min_interval,
            }

    def reset(self) -> None:
        with self._lock:
            self._last_beat_time = 0.0
            self._beat_count = 0
            self._pending_beats.clear()


# =============================================================================
# Emergence Detector
# =============================================================================


class EmergenceDetector:
    """
    Spots emergent gameplay patterns: unusual entity interactions, repeated
    player strategies, surprising state combinations. When detected, the
    brain can amplify or formalize these patterns.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._event_signatures: Dict[str, int] = {}
        self._detections: Deque[Dict[str, Any]] = deque(maxlen=32)
        self._last_detection_time: float = 0.0

    def scan(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Scan recent events for emergent patterns."""
        if not events:
            return []
        with self._lock:
            detections: List[Dict[str, Any]] = []
            for event in events:
                signature = self._signature(event)
                self._event_signatures[signature] = (
                    self._event_signatures.get(signature, 0) + 1
                )
                # A signature appearing 5+ times in a window is "emergent"
                if self._event_signatures[signature] == 5:
                    detection = {
                        "detection_id": uuid.uuid4().hex[:10],
                        "signature": signature,
                        "count": 5,
                        "kind": event.get("kind", "unknown"),
                        "timestamp": time.time(),
                    }
                    self._detections.append(detection)
                    detections.append(detection)
                    self._last_detection_time = time.time()

            # Decay signature counts slowly
            for sig in list(self._event_signatures.keys()):
                self._event_signatures[sig] = max(
                    0, self._event_signatures[sig] - 1
                )
                if self._event_signatures[sig] == 0:
                    del self._event_signatures[sig]

            return detections

    def _signature(self, event: Dict[str, Any]) -> str:
        kind = event.get("kind", "unknown")
        data = event.get("data", {}) or {}
        # Use kind + sorted top-level data keys as signature
        keys = ",".join(sorted(str(k) for k in data.keys())) if isinstance(data, dict) else ""
        return f"{kind}|{keys}"

    def recent_detections(self, limit: int = 8) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._detections)[-limit:]

    def reset(self) -> None:
        with self._lock:
            self._event_signatures.clear()
            self._detections.clear()
            self._last_detection_time = 0.0


# =============================================================================
# Coherence Guard
# =============================================================================


class CoherenceGuard:
    """
    Prevents the brain from issuing contradictory directives in quick
    succession (e.g., calm_player followed immediately by challenge_player).
    Maintains a short history of issued directives and vetoes conflicts.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._history: Deque[Directive] = deque(maxlen=16)
        self._conflict_pairs: Dict[DirectiveKind, List[DirectiveKind]] = {
            DirectiveKind.CALM_PLAYER: [DirectiveKind.CHALLENGE_PLAYER, DirectiveKind.ADJUST_DIFFICULTY],
            DirectiveKind.CHALLENGE_PLAYER: [DirectiveKind.CALM_PLAYER, DirectiveKind.REWARD_PLAYER],
            DirectiveKind.REWARD_PLAYER: [DirectiveKind.CHALLENGE_PLAYER],
            DirectiveKind.SHIFT_PACING: [DirectiveKind.SHIFT_PACING],
        }
        self._cooldown_seconds: float = 5.0

    def approve(self, directive: Directive) -> bool:
        """Return True if the directive is coherent with recent history."""
        with self._lock:
            now = time.time()
            conflicts = self._conflict_pairs.get(directive.kind, [])
            for past in self._history:
                age = now - past.issued_at
                if age > self._cooldown_seconds:
                    continue
                if past.kind in conflicts:
                    logger.debug(
                        "CoherenceGuard veto: %s conflicts with recent %s",
                        directive.kind.value, past.kind.value,
                    )
                    return False
            self._history.append(directive)
            return True

    def recent(self, limit: int = 8) -> List[Directive]:
        with self._lock:
            return list(self._history)[-limit:]

    def reset(self) -> None:
        with self._lock:
            self._history.clear()


# =============================================================================
# Game Brain
# =============================================================================


class GameBrain:
    """
    Singleton AI-native game brain. Wires together the player modeler,
    pacing director, difficulty tuner, narrative conductor, emergence
    detector, and coherence guard into a single tick-driven cognition.
    """

    _instance: Optional["GameBrain"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if GameBrain._instance is not None:
            raise RuntimeError("Use GameBrain.get_instance()")
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._tick: int = 0
        self._last_tick_time: float = time.time()

        # Components
        self.player_modeler: PlayerModeler = PlayerModeler()
        self.pacing_director: PacingDirector = PacingDirector()
        self.difficulty_tuner: DifficultyTuner = DifficultyTuner()
        self.narrative_conductor: NarrativeConductor = NarrativeConductor()
        self.emergence_detector: EmergenceDetector = EmergenceDetector()
        self.coherence_guard: CoherenceGuard = CoherenceGuard()

        # Output queue
        self._directive_queue: Deque[Directive] = deque()
        self._dispatched: Deque[Directive] = deque(maxlen=64)
        self._last_result: Optional[BrainTickResult] = None
        self._results_history: Deque[BrainTickResult] = deque(maxlen=64)

        # Wiring
        self._integrator: Any = None
        self._engine_event_provider: Optional[Callable[[], List[Dict[str, Any]]]] = None

    @classmethod
    def get_instance(cls) -> "GameBrain":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            try:
                from sparkai.engine.engine_kernel_integration import (
                    KernelEngineIntegrator,
                )
                self._integrator = KernelEngineIntegrator.get_instance()
            except Exception as exc:
                logger.warning("KernelEngineIntegrator acquisition failed: %s", exc)
                self._integrator = None
            self._initialized = True
            logger.info("GameBrain initialized")

    # -------------------------------------------------------------------------
    # Wiring
    # -------------------------------------------------------------------------

    def set_engine_event_provider(
        self, provider: Callable[[], List[Dict[str, Any]]]
    ) -> None:
        """Set a callable that returns recent engine events as dicts."""
        with self._lock:
            self._engine_event_provider = provider

    # -------------------------------------------------------------------------
    # Brain Tick
    # -------------------------------------------------------------------------

    def tick(self) -> BrainTickResult:
        """Advance the brain by one cognitive tick."""
        if not self._initialized:
            self.initialize()

        start = time.time()
        self._tick += 1
        result = BrainTickResult(tick=self._tick, phase=BrainPhase.OBSERVE)

        # Phase 1: Observe - collect events from engine
        events: List[Dict[str, Any]] = []
        if self._engine_event_provider is not None:
            try:
                events = list(self._engine_event_provider() or [])
            except Exception as exc:
                logger.warning("Engine event provider failed: %s", exc)
                events = []

        # Phase 2: Model - update player and pacing models
        result.phase = BrainPhase.MODEL
        for event in events:
            self.player_modeler.ingest(event)
        result.player_modeled = True

        now = time.time()
        dt = now - self._last_tick_time
        self._last_tick_time = now

        player = self.player_modeler.state()
        pacing = self.pacing_director.update(player, dt)
        difficulty = self.difficulty_tuner.update(player)
        result.pacing_updated = True

        # Phase 3: Decide - generate directives
        result.phase = BrainPhase.DECIDE
        directives: List[Directive] = []

        # Difficulty directive when target shifted significantly
        if abs(self.difficulty_tuner.target() - self.difficulty_tuner.difficulty()) > 0.05:
            directives.append(Directive(
                kind=DirectiveKind.ADJUST_DIFFICULTY,
                intent=f"Adjust difficulty toward {self.difficulty_tuner.target():.2f}",
                args={
                    "current": self.difficulty_tuner.difficulty(),
                    "target": self.difficulty_tuner.target(),
                    "player_mood": player.mood().value,
                },
                priority=3,
                confidence=0.7,
                expected_effect="player_returns_to_flow_channel",
            ))

        # Pacing directive on zone transition
        if pacing.time_in_zone < 1.0:
            directives.append(Directive(
                kind=DirectiveKind.SHIFT_PACING,
                intent=f"Shift pacing to {pacing.zone.value}",
                args={
                    "zone": pacing.zone.value,
                    "tension": pacing.tension,
                    "target_tension": pacing.target_tension,
                },
                priority=5,
                confidence=0.85,
                expected_effect="dramatic_pacing_aligns_with_player_state",
            ))

        # Narrative directive
        beat = self.narrative_conductor.consider(pacing, player, now)
        if beat is not None:
            directives.append(Directive(
                kind=DirectiveKind.INJECT_NARRATIVE,
                intent=f"Inject {beat.get('type', 'narrative')} beat",
                args=beat,
                priority=4,
                confidence=0.8,
                expected_effect="player_engagement_renewed",
            ))

        # Emergence directives
        detections = self.emergence_detector.scan(events)
        if detections:
            result.emergence_detected = True
            for detection in detections[:2]:  # cap per tick
                directives.append(Directive(
                    kind=DirectiveKind.HIGHLIGHT_EMERGENCE,
                    intent=f"Highlight emergent pattern: {detection['signature']}",
                    args=detection,
                    priority=2,
                    confidence=0.6,
                    expected_effect="player_discovers_emergent_strategy",
                ))

        # Mood-driven directives
        mood = player.mood()
        if mood == PlayerMood.FRUSTRATED and player.retries > 4:
            directives.append(Directive(
                kind=DirectiveKind.CALM_PLAYER,
                intent="Reduce pressure to relieve frustration",
                args={"retries": player.retries, "frustration": player.frustration},
                priority=6,
                confidence=0.75,
                expected_effect="frustration_decreases",
            ))
        elif mood == PlayerMood.BORED and player.session_seconds > 90:
            directives.append(Directive(
                kind=DirectiveKind.CHALLENGE_PLAYER,
                intent="Increase stimulation to counter boredom",
                args={"session_seconds": player.session_seconds},
                priority=4,
                confidence=0.7,
                expected_effect="engagement_recovers",
            ))
        elif mood == PlayerMood.ELATED and player.successes > 3:
            directives.append(Directive(
                kind=DirectiveKind.REWARD_PLAYER,
                intent="Reward skilled play to reinforce engagement",
                args={"successes": player.successes},
                priority=3,
                confidence=0.8,
                expected_effect="delight_sustained",
            ))

        # Phase 4: Dispatch - filter through coherence guard and enqueue
        result.phase = BrainPhase.DISPATCH
        for directive in directives:
            if self.coherence_guard.approve(directive):
                self._directive_queue.append(directive)
                result.directives_issued += 1

        # Forward directives to the integrator as engine commands
        if self._integrator is not None:
            self._forward_to_integrator()

        # Phase 5: Refine - log observations
        result.phase = BrainPhase.REFINE
        if result.directives_issued == 0 and self._tick % 8 == 0:
            result.notes.append(
                f"Steady state: mood={mood.value}, zone={pacing.zone.value}, "
                f"tension={pacing.tension:.2f}, difficulty={difficulty:.2f}"
            )

        # Phase 6: Learn - record in history
        result.phase = BrainPhase.LEARN
        result.duration_s = time.time() - start
        with self._lock:
            self._last_result = result
            self._results_history.append(result)
        return result

    def _forward_to_integrator(self) -> None:
        """Translate queued directives into integrator engine commands."""
        if self._integrator is None:
            return
        try:
            from sparkai.engine.engine_kernel_integration import (
                EngineCommand, EngineCommandKind,
            )
        except Exception as exc:
            logger.warning("Could not import integrator command types: %s", exc)
            return

        # Map directive kinds to engine command kinds
        kind_map = {
            DirectiveKind.ADJUST_DIFFICULTY: EngineCommandKind.ADJUST_PARAMETER,
            DirectiveKind.SHIFT_PACING: EngineCommandKind.ADJUST_PARAMETER,
            DirectiveKind.INJECT_NARRATIVE: EngineCommandKind.TRIGGER_EVENT,
            DirectiveKind.HIGHLIGHT_EMERGENCE: EngineCommandKind.TRIGGER_EVENT,
            DirectiveKind.CALM_PLAYER: EngineCommandKind.ADJUST_PARAMETER,
            DirectiveKind.CHALLENGE_PLAYER: EngineCommandKind.ADJUST_PARAMETER,
            DirectiveKind.REWARD_PLAYER: EngineCommandKind.TRIGGER_EVENT,
            DirectiveKind.CHANGE_SCENE_MOOD: EngineCommandKind.ADJUST_PARAMETER,
            DirectiveKind.SPAWN_EVENT: EngineCommandKind.SPAWN_ENTITY,
            DirectiveKind.DESPAWN_ELEMENT: EngineCommandKind.DESPAWN_ENTITY,
            DirectiveKind.CUSTOM: EngineCommandKind.CUSTOM,
        }

        with self._lock:
            queued = list(self._directive_queue)
            self._directive_queue.clear()

        for directive in queued:
            cmd_kind = kind_map.get(directive.kind, EngineCommandKind.CUSTOM)
            cmd = EngineCommand(
                kind=cmd_kind,
                target=directive.intent,
                args={
                    "directive_kind": directive.kind.value,
                    "intent": directive.intent,
                    "confidence": directive.confidence,
                    **directive.args,
                },
                priority=directive.priority,
                issued_by="game_brain",
            )
            try:
                self._integrator.action_pipeline.enqueue(cmd)
                with self._lock:
                    self._dispatched.append(directive)
            except Exception as exc:
                logger.warning("Failed to forward directive: %s", exc)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def pending_directives(self) -> List[Directive]:
        with self._lock:
            return list(self._directive_queue)

    def dispatched_directives(self, limit: int = 16) -> List[Directive]:
        with self._lock:
            return list(self._dispatched)[-limit:]

    def player_snapshot(self) -> Dict[str, Any]:
        return self.player_modeler.state().to_dict()

    def pacing_snapshot(self) -> Dict[str, Any]:
        return self.pacing_director.state().to_dict()

    def difficulty_snapshot(self) -> Dict[str, Any]:
        return {
            "current": round(self.difficulty_tuner.difficulty(), 3),
            "target": round(self.difficulty_tuner.target(), 3),
        }

    def status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "tick": self._tick,
            "player": self.player_snapshot(),
            "pacing": self.pacing_snapshot(),
            "difficulty": self.difficulty_snapshot(),
            "narrative": self.narrative_conductor.stats(),
            "emergence_recent": self.emergence_detector.recent_detections(3),
            "coherence_recent": [
                {"kind": d.kind.value, "intent": d.intent, "priority": d.priority}
                for d in self.coherence_guard.recent(5)
            ],
            "pending_directives": len(self.pending_directives()),
            "dispatched_directives": len(self.dispatched_directives()),
            "last_tick": {
                "phase": self._last_result.phase.value if self._last_result else None,
                "directives_issued": self._last_result.directives_issued if self._last_result else 0,
                "emergence_detected": self._last_result.emergence_detected if self._last_result else False,
                "duration_s": self._last_result.duration_s if self._last_result else 0,
            } if self._last_result else None,
        }

    def reset(self) -> None:
        """Reset all brain state (preserves wiring)."""
        with self._lock:
            self.player_modeler.reset()
            self.pacing_director.reset()
            self.difficulty_tuner.reset()
            self.narrative_conductor.reset()
            self.emergence_detector.reset()
            self.coherence_guard.reset()
            self._directive_queue.clear()
            self._dispatched.clear()
            self._tick = 0
            self._last_tick_time = time.time()
            self._last_result = None
            self._results_history.clear()


# =============================================================================
# Module-level Convenience
# =============================================================================


def get_brain() -> GameBrain:
    """Return the singleton GameBrain instance."""
    return GameBrain.get_instance()


def quick_brain_status() -> Dict[str, Any]:
    """Return a quick status snapshot of the game brain."""
    return get_brain().status()
