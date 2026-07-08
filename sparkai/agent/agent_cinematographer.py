"""
SparkLabs Agent - Cinematographer

An AI cinematographer for the SparkLabs AI-native game engine. It performs
live, dynamic camera framing during gameplay by selecting shots, composing
sequences, rating dramatic tension, and shifting mood in real time. Unlike
scripted cutscene systems, this agent makes continuous cinematographic
decisions that fuse AI judgment with engine camera control, producing a
cinematic experience that adapts to emergent gameplay.

Architecture:
  Cinematographer (singleton)
    |-- CinemaShot, CinemaSequence, CinemaStats, CinemaSnapshot, CinemaEvent
    |-- CinemaShotType, CinemaFrameSize, CinemaMovement, CinemaMood,
       CinemaEventKind

Core Capabilities:
  - register_shot / get_shot / list_shots / update_shot / remove_shot:
    shot lifecycle management with type, frame size, movement, mood.
  - compose_sequence / get_sequence / list_sequences / remove_sequence:
    multi-shot cinematic sequences with looping and mood anchoring.
  - select_shot: AI-driven shot selection based on context (mood, action
    intensity, entity priority, scene phase).
  - transition_to: transition the active shot to a new one with blend.
  - rate_dramatic_tension: score the dramatic tension of a live scene.
  - shift_mood: shift the cinematographer mood, influencing shot selection.
  - set_focus: set the focus entity for framing decisions.
  - clear_queue: clear the pending shot queue.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`Cinematographer.get_instance` or the module-level
:func:`get_cinematographer` factory.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_SHOTS: int = 3000
_MAX_SEQUENCES: int = 1000
_MAX_QUEUE: int = 200
_MAX_EVENTS: int = 5000
_MAX_RATINGS: int = 2000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


# Shot type affinity per mood (higher = more fitting)
_MOOD_SHOT_AFFINITY: Dict[str, Dict[str, float]] = {
    "neutral": {
        "wide": 1.0, "medium": 1.0, "close_up": 0.8, "extreme_close_up": 0.4,
        "over_shoulder": 0.7, "aerial": 0.6, "tracking": 0.7, "dutch_angle": 0.3,
        "pov": 0.5, "establishing": 0.9,
    },
    "tense": {
        "wide": 0.6, "medium": 0.8, "close_up": 1.0, "extreme_close_up": 0.9,
        "over_shoulder": 0.9, "aerial": 0.4, "tracking": 0.8, "dutch_angle": 0.85,
        "pov": 0.7, "establishing": 0.3,
    },
    "triumphant": {
        "wide": 1.0, "medium": 0.8, "close_up": 0.7, "extreme_close_up": 0.4,
        "over_shoulder": 0.5, "aerial": 0.95, "tracking": 0.85, "dutch_angle": 0.2,
        "pov": 0.3, "establishing": 0.9,
    },
    "melancholy": {
        "wide": 0.9, "medium": 0.85, "close_up": 0.8, "extreme_close_up": 0.6,
        "over_shoulder": 0.7, "aerial": 0.7, "tracking": 0.5, "dutch_angle": 0.3,
        "pov": 0.4, "establishing": 0.75,
    },
    "action": {
        "wide": 0.7, "medium": 0.85, "close_up": 0.9, "extreme_close_up": 0.75,
        "over_shoulder": 0.8, "aerial": 0.85, "tracking": 1.0, "dutch_angle": 0.7,
        "pov": 0.85, "establishing": 0.4,
    },
    "intimate": {
        "wide": 0.3, "medium": 0.7, "close_up": 1.0, "extreme_close_up": 0.95,
        "over_shoulder": 0.9, "aerial": 0.1, "tracking": 0.4, "dutch_angle": 0.15,
        "pov": 0.6, "establishing": 0.2,
    },
    "mysterious": {
        "wide": 0.8, "medium": 0.75, "close_up": 0.85, "extreme_close_up": 0.7,
        "over_shoulder": 0.8, "aerial": 0.5, "tracking": 0.6, "dutch_angle": 0.9,
        "pov": 0.7, "establishing": 0.85,
    },
    "epic": {
        "wide": 1.0, "medium": 0.7, "close_up": 0.6, "extreme_close_up": 0.3,
        "over_shoulder": 0.4, "aerial": 1.0, "tracking": 0.9, "dutch_angle": 0.3,
        "pov": 0.2, "establishing": 1.0,
    },
}

_FRAME_SIZE_DURATION: Dict[str, float] = {
    "extreme_long": 4.0,
    "long": 3.0,
    "medium": 2.5,
    "close": 2.0,
    "extreme_close": 1.5,
}


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class CinemaShotType(Enum):
    """Cinematic shot types classified by framing and camera role."""
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    OVER_SHOULDER = "over_shoulder"
    AERIAL = "aerial"
    TRACKING = "tracking"
    DUTCH_ANGLE = "dutch_angle"
    POV = "pov"
    ESTABLISHING = "establishing"


class CinemaFrameSize(Enum):
    """Frame size categories determining subject distance."""
    EXTREME_LONG = "extreme_long"
    LONG = "long"
    MEDIUM = "medium"
    CLOSE = "close"
    EXTREME_CLOSE = "extreme_close"


class CinemaMovement(Enum):
    """Camera movement styles during a shot."""
    STATIC = "static"
    PAN = "pan"
    TILT = "tilt"
    DOLLY = "dolly"
    TRACK = "track"
    CRANE = "crane"
    HANDHELD = "handheld"
    ORBIT = "orbit"
    FOLLOW = "follow"


class CinemaMood(Enum):
    """Narrative moods that influence shot selection."""
    NEUTRAL = "neutral"
    TENSE = "tense"
    TRIUMPHANT = "triumphant"
    MELANCHOLY = "melancholy"
    ACTION = "action"
    INTIMATE = "intimate"
    MYSTERIOUS = "mysterious"
    EPIC = "epic"


class CinemaEventKind(Enum):
    """Audit event types emitted by the cinematographer."""
    SHOT_REGISTERED = "shot_registered"
    SHOT_REMOVED = "shot_removed"
    SHOT_SELECTED = "shot_selected"
    SHOT_TRANSITIONED = "shot_transitioned"
    SEQUENCE_COMPOSED = "sequence_composed"
    SEQUENCE_REMOVED = "sequence_removed"
    DRAMA_RATED = "drama_rated"
    MOOD_SHIFTED = "mood_shifted"
    FOCUS_SET = "focus_set"
    QUEUE_CLEARED = "queue_cleared"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CinemaShot:
    """A single cinematic shot definition."""
    shot_id: str = ""
    name: str = ""
    shot_type: str = CinemaShotType.MEDIUM.value
    frame_size: str = CinemaFrameSize.MEDIUM.value
    movement: str = CinemaMovement.STATIC.value
    mood: str = CinemaMood.NEUTRAL.value
    target_entity_id: str = ""
    position_offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    look_at_offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    fov: float = 60.0
    duration_seconds: float = 3.0
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CinemaSequence:
    """A composed sequence of shots forming a cinematic arc."""
    sequence_id: str = ""
    name: str = ""
    shot_ids: List[str] = field(default_factory=list)
    loop: bool = False
    total_duration: float = 0.0
    mood: str = CinemaMood.NEUTRAL.value
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CinemaStats:
    """Aggregate statistics for the cinematographer."""
    total_shots: int = 0
    total_sequences: int = 0
    total_shots_selected: int = 0
    total_transitions: int = 0
    total_sequences_composed: int = 0
    total_drama_ratings: int = 0
    total_mood_shifts: int = 0
    total_focus_changes: int = 0
    total_queue_clears: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CinemaSnapshot:
    """Point-in-time snapshot of cinematographer state."""
    current_mood: str = CinemaMood.NEUTRAL.value
    focus_entity_id: str = ""
    active_shot_id: str = ""
    queue_length: int = 0
    total_shots: int = 0
    total_sequences: int = 0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CinemaEvent:
    """An audit event emitted by the cinematographer."""
    event_id: str = ""
    kind: str = CinemaEventKind.SHOT_REGISTERED.value
    timestamp: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Cinematographer Singleton
# ---------------------------------------------------------------------------


class Cinematographer:
    """AI cinematographer that performs live camera framing decisions.

    Implements the singleton pattern with double-checked locking.
    """

    _instance: Optional["Cinematographer"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._shots: Dict[str, CinemaShot] = {}
        self._sequences: Dict[str, CinemaSequence] = {}
        self._queue: List[str] = []
        self._events: List[CinemaEvent] = []
        self._ratings: List[Dict[str, Any]] = []
        self._current_mood: str = CinemaMood.NEUTRAL.value
        self._focus_entity_id: str = ""
        self._active_shot_id: str = ""
        self._stats = CinemaStats()
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "Cinematographer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed initial shots and sequences."""
        seeded_shots = [
            CinemaShot(
                shot_id="csh_wide_establish",
                name="Wide Establishing",
                shot_type=CinemaShotType.ESTABLISHING.value,
                frame_size=CinemaFrameSize.EXTREME_LONG.value,
                movement=CinemaMovement.CRANE.value,
                mood=CinemaMood.EPIC.value,
                target_entity_id="",
                position_offset=(0.0, 15.0, -20.0),
                look_at_offset=(0.0, 0.0, 0.0),
                fov=75.0,
                duration_seconds=4.0,
                priority=10,
                metadata={"scene": "establishing"},
            ),
            CinemaShot(
                shot_id="csh_hero_tracking",
                name="Hero Tracking",
                shot_type=CinemaShotType.TRACKING.value,
                frame_size=CinemaFrameSize.MEDIUM.value,
                movement=CinemaMovement.TRACK.value,
                mood=CinemaMood.ACTION.value,
                target_entity_id="actor_hero_1",
                position_offset=(3.0, 2.0, -5.0),
                look_at_offset=(0.0, 1.0, 0.0),
                fov=50.0,
                duration_seconds=3.0,
                priority=8,
                metadata={"scene": "combat"},
            ),
            CinemaShot(
                shot_id="csh_boss_close",
                name="Boss Close-Up",
                shot_type=CinemaShotType.CLOSE_UP.value,
                frame_size=CinemaFrameSize.CLOSE.value,
                movement=CinemaMovement.STATIC.value,
                mood=CinemaMood.TENSE.value,
                target_entity_id="actor_boss_1",
                position_offset=(1.5, 2.0, -2.0),
                look_at_offset=(0.0, 1.5, 0.0),
                fov=35.0,
                duration_seconds=2.0,
                priority=9,
                metadata={"scene": "boss_intro"},
            ),
            CinemaShot(
                shot_id="csh_aerial_epic",
                name="Aerial Epic",
                shot_type=CinemaShotType.AERIAL.value,
                frame_size=CinemaFrameSize.EXTREME_LONG.value,
                movement=CinemaMovement.ORBIT.value,
                mood=CinemaMood.EPIC.value,
                target_entity_id="actor_hero_1",
                position_offset=(0.0, 30.0, 0.0),
                look_at_offset=(0.0, 0.0, 0.0),
                fov=80.0,
                duration_seconds=5.0,
                priority=7,
                metadata={"scene": "climax"},
            ),
            CinemaShot(
                shot_id="csh_intimate_otc",
                name="Intimate Over-Shoulder",
                shot_type=CinemaShotType.OVER_SHOULDER.value,
                frame_size=CinemaFrameSize.MEDIUM.value,
                movement=CinemaMovement.STATIC.value,
                mood=CinemaMood.INTIMATE.value,
                target_entity_id="actor_npc_1",
                position_offset=(1.0, 1.5, -2.5),
                look_at_offset=(0.0, 1.2, 0.0),
                fov=40.0,
                duration_seconds=3.5,
                priority=6,
                metadata={"scene": "dialogue"},
            ),
        ]
        for shot in seeded_shots:
            self._shots[shot.shot_id] = shot

        seeded_sequences = [
            CinemaSequence(
                sequence_id="cqs_boss_intro",
                name="Boss Introduction",
                shot_ids=["csh_wide_establish", "csh_boss_close", "csh_hero_tracking"],
                loop=False,
                total_duration=9.0,
                mood=CinemaMood.TENSE.value,
                metadata={"scene": "boss_intro"},
            ),
            CinemaSequence(
                sequence_id="cqs_dialogue",
                name="Dialogue Scene",
                shot_ids=["csh_intimate_otc", "csh_hero_tracking"],
                loop=True,
                total_duration=6.5,
                mood=CinemaMood.INTIMATE.value,
                metadata={"scene": "dialogue"},
            ),
        ]
        for seq in seeded_sequences:
            self._sequences[seq.sequence_id] = seq

        self._stats.total_shots = len(self._shots)
        self._stats.total_sequences = len(self._sequences)
        self._initialized = True

    def _emit(self, kind: str, payload: Optional[Dict[str, Any]] = None) -> None:
        event = CinemaEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            payload=payload or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Shot Lifecycle
    # ------------------------------------------------------------------

    def register_shot(self, shot: CinemaShot) -> CinemaShot:
        if not shot.shot_id:
            shot.shot_id = _new_id("csh")
        self._shots[shot.shot_id] = shot
        _evict_fifo_dict(self._shots, _MAX_SHOTS)
        self._stats.total_shots = len(self._shots)
        self._emit(CinemaEventKind.SHOT_REGISTERED.value, {"shot_id": shot.shot_id})
        return shot

    def get_shot(self, shot_id: str) -> Optional[CinemaShot]:
        return self._shots.get(shot_id)

    def list_shots(
        self,
        shot_type: str = "",
        mood: str = "",
        movement: str = "",
        limit: int = 50,
    ) -> List[CinemaShot]:
        results: List[CinemaShot] = []
        for shot in self._shots.values():
            if shot_type and shot.shot_type != shot_type:
                continue
            if mood and shot.mood != mood:
                continue
            if movement and shot.movement != movement:
                continue
            results.append(shot)
        results.sort(key=lambda s: s.priority, reverse=True)
        return results[:max(0, int(limit))]

    def update_shot(self, shot_id: str, updates: Dict[str, Any]) -> Optional[CinemaShot]:
        shot = self._shots.get(shot_id)
        if shot is None:
            return None
        for key, value in updates.items():
            if key == "shot_id":
                continue
            if hasattr(shot, key):
                if key in ("position_offset", "look_at_offset") and isinstance(value, list):
                    value = tuple(value)
                setattr(shot, key, value)
        return shot

    def remove_shot(self, shot_id: str) -> bool:
        existed = self._shots.pop(shot_id, None) is not None
        if existed:
            self._stats.total_shots = len(self._shots)
            self._emit(CinemaEventKind.SHOT_REMOVED.value, {"shot_id": shot_id})
            if self._active_shot_id == shot_id:
                self._active_shot_id = ""
            self._queue = [s for s in self._queue if s != shot_id]
        return existed

    # ------------------------------------------------------------------
    # Sequence Lifecycle
    # ------------------------------------------------------------------

    def compose_sequence(self, sequence: CinemaSequence) -> CinemaSequence:
        if not sequence.sequence_id:
            sequence.sequence_id = _new_id("cqs")
        if not sequence.shot_ids:
            sequence.shot_ids = []
        total = 0.0
        for sid in sequence.shot_ids:
            shot = self._shots.get(sid)
            if shot is not None:
                total += shot.duration_seconds
        if total > 0:
            sequence.total_duration = total
        self._sequences[sequence.sequence_id] = sequence
        _evict_fifo_dict(self._sequences, _MAX_SEQUENCES)
        self._stats.total_sequences = len(self._sequences)
        self._stats.total_sequences_composed += 1
        self._emit(
            CinemaEventKind.SEQUENCE_COMPOSED.value,
            {"sequence_id": sequence.sequence_id, "shot_count": len(sequence.shot_ids)},
        )
        return sequence

    def get_sequence(self, sequence_id: str) -> Optional[CinemaSequence]:
        return self._sequences.get(sequence_id)

    def list_sequences(self, mood: str = "", limit: int = 50) -> List[CinemaSequence]:
        results: List[CinemaSequence] = []
        for seq in self._sequences.values():
            if mood and seq.mood != mood:
                continue
            results.append(seq)
        return results[:max(0, int(limit))]

    def remove_sequence(self, sequence_id: str) -> bool:
        existed = self._sequences.pop(sequence_id, None) is not None
        if existed:
            self._stats.total_sequences = len(self._sequences)
            self._emit(CinemaEventKind.SEQUENCE_REMOVED.value, {"sequence_id": sequence_id})
        return existed

    # ------------------------------------------------------------------
    # AI-Driven Shot Selection
    # ------------------------------------------------------------------

    def select_shot(
        self,
        mood: str = "",
        action_intensity: float = 0.5,
        entity_priority: Dict[str, float] = None,
        prefer_type: str = "",
    ) -> Optional[CinemaShot]:
        """Select the best shot for the current context.

        Scoring: mood_affinity * 0.4 + intensity_match * 0.3 +
        entity_priority * 0.2 + type_preference * 0.1
        """
        mood_key = mood or self._current_mood
        affinity_table = _MOOD_SHOT_AFFINITY.get(mood_key, _MOOD_SHOT_AFFINITY["neutral"])
        intensity = _clamp(_safe_float(action_intensity, 0.5))

        best_shot: Optional[CinemaShot] = None
        best_score: float = -1.0

        for shot in self._shots.values():
            mood_score = affinity_table.get(shot.shot_type, 0.5)

            type_intensity_map = {
                "wide": 0.3, "medium": 0.5, "close_up": 0.7,
                "extreme_close_up": 0.85, "over_shoulder": 0.6,
                "aerial": 0.4, "tracking": 0.9, "dutch_angle": 0.8,
                "pov": 0.85, "establishing": 0.2,
            }
            type_intensity = type_intensity_map.get(shot.shot_type, 0.5)
            intensity_diff = abs(type_intensity - intensity)
            intensity_score = 1.0 - intensity_diff

            entity_score = 0.5
            if entity_priority and shot.target_entity_id:
                entity_score = _clamp(entity_priority.get(shot.target_entity_id, 0.5))

            type_pref = 1.0 if (not prefer_type or shot.shot_type == prefer_type) else 0.5

            score = (
                mood_score * 0.4
                + intensity_score * 0.3
                + entity_score * 0.2
                + type_pref * 0.1
            )
            score += shot.priority * 0.01

            if score > best_score:
                best_score = score
                best_shot = shot

        if best_shot is not None:
            self._active_shot_id = best_shot.shot_id
            self._stats.total_shots_selected += 1
            self._emit(
                CinemaEventKind.SHOT_SELECTED.value,
                {"shot_id": best_shot.shot_id, "score": round(best_score, 4)},
            )
        return best_shot

    def transition_to(self, shot_id: str) -> Optional[CinemaShot]:
        shot = self._shots.get(shot_id)
        if shot is None:
            return None
        old_id = self._active_shot_id
        self._active_shot_id = shot_id
        self._stats.total_transitions += 1
        self._emit(
            CinemaEventKind.SHOT_TRANSITIONED.value,
            {"from_shot_id": old_id, "to_shot_id": shot_id},
        )
        return shot

    def rate_dramatic_tension(
        self,
        entity_count: int = 0,
        action_intensity: float = 0.5,
        threat_level: float = 0.5,
        narrative_weight: float = 0.5,
    ) -> Dict[str, Any]:
        """Rate the dramatic tension of a live scene.

        Returns dict with ok, tension, band, factors.
        """
        ec = _safe_int(entity_count, 0)
        ai = _clamp(_safe_float(action_intensity, 0.5))
        tl = _clamp(_safe_float(threat_level, 0.5))
        nw = _clamp(_safe_float(narrative_weight, 0.5))

        entity_factor = _clamp(math.log10(ec + 1.0) / 2.0)
        tension = _clamp(
            entity_factor * 0.2 + ai * 0.3 + tl * 0.3 + nw * 0.2
        )

        if tension < 0.2:
            band = "calm"
        elif tension < 0.4:
            band = "rising"
        elif tension < 0.6:
            band = "intense"
        elif tension < 0.8:
            band = "climactic"
        else:
            band = "peak"

        rating = {
            "ok": True,
            "tension": round(tension, 4),
            "band": band,
            "factors": {
                "entity_factor": round(entity_factor, 4),
                "action_intensity": round(ai, 4),
                "threat_level": round(tl, 4),
                "narrative_weight": round(nw, 4),
            },
        }
        self._ratings.append(rating)
        _evict_fifo_list(self._ratings, _MAX_RATINGS)
        self._stats.total_drama_ratings += 1
        self._emit(
            CinemaEventKind.DRAMA_RATED.value,
            {"tension": round(tension, 4), "band": band},
        )
        return rating

    def shift_mood(self, mood: str) -> str:
        old = self._current_mood
        self._current_mood = mood
        self._stats.total_mood_shifts += 1
        self._emit(
            CinemaEventKind.MOOD_SHIFTED.value,
            {"from_mood": old, "to_mood": mood},
        )
        return mood

    def set_focus(self, entity_id: str) -> str:
        old = self._focus_entity_id
        self._focus_entity_id = entity_id
        self._stats.total_focus_changes += 1
        self._emit(
            CinemaEventKind.FOCUS_SET.value,
            {"from_entity_id": old, "to_entity_id": entity_id},
        )
        return entity_id

    def clear_queue(self) -> int:
        count = len(self._queue)
        self._queue.clear()
        self._stats.total_queue_clears += 1
        self._emit(CinemaEventKind.QUEUE_CLEARED.value, {"cleared_count": count})
        return count

    def enqueue_shot(self, shot_id: str) -> bool:
        if shot_id not in self._shots:
            return False
        self._queue.append(shot_id)
        _evict_fifo_list(self._queue, _MAX_QUEUE)
        return True

    def dequeue_shot(self) -> Optional[CinemaShot]:
        if not self._queue:
            return None
        shot_id = self._queue.pop(0)
        return self._shots.get(shot_id)

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, kind: str = "", limit: int = 50) -> List[CinemaEvent]:
        results: List[CinemaEvent] = []
        for event in reversed(self._events):
            if kind and event.kind != kind:
                continue
            results.append(event)
            if len(results) >= max(0, int(limit)):
                break
        return results

    def get_stats(self) -> CinemaStats:
        self._stats.total_shots = len(self._shots)
        self._stats.total_sequences = len(self._sequences)
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "shots": len(self._shots),
            "sequences": len(self._sequences),
            "queue_length": len(self._queue),
            "current_mood": self._current_mood,
            "focus_entity_id": self._focus_entity_id,
            "active_shot_id": self._active_shot_id,
            "events": len(self._events),
        }

    def get_snapshot(self) -> CinemaSnapshot:
        return CinemaSnapshot(
            current_mood=self._current_mood,
            focus_entity_id=self._focus_entity_id,
            active_shot_id=self._active_shot_id,
            queue_length=len(self._queue),
            total_shots=len(self._shots),
            total_sequences=len(self._sequences),
            timestamp=_now(),
        )

    def reset(self) -> None:
        with self._init_lock:
            self._shots.clear()
            self._sequences.clear()
            self._queue.clear()
            self._events.clear()
            self._ratings.clear()
            self._current_mood = CinemaMood.NEUTRAL.value
            self._focus_entity_id = ""
            self._active_shot_id = ""
            self._stats = CinemaStats()
            self._seed()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_cinematographer() -> Cinematographer:
    """Get the singleton Cinematographer instance."""
    return Cinematographer.get_instance()
