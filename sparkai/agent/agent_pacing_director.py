"""
SparkLabs Agent - AI Pacing Director

Orchstrates the rhythm of player experience by tuning intensity curves,
action/lull cycles, and engagement feedback. Prevents burnout from
sustained high intensity and boredom from prolonged lulls, steering the
player toward a sustained flow state.

Consumes gameplay telemetry (kills, deaths, objectives, movement,
resource changes) and emits pacing directives (spawn enemies, dial
difficulty, trigger narrative beats, suggest rests) that other engine
subsystems can consume.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> float:
    return time.time()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * _clamp(t, 0.0, 1.0)


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_CURVES = 200
_MAX_DIRECTIVES = 5000
_MAX_TELEMETRY = 5000
_MAX_EVENTS = 5000
_INTENSITY_HISTORY = 600


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PacingPhase(str, Enum):
    """Macro rhythm phase the experience is currently in."""
    LULL = "lull"
    BUILDUP = "buildup"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    REST = "rest"


class EngagementLevel(str, Enum):
    """Categorical label for the player's engagement state."""
    BORED = "bored"
    ENGAGED = "engaged"
    FLOW = "flow"
    EXCITED = "excited"
    OVERWHELMED = "overwhelmed"
    BURNOUT = "burnout"


class DirectiveKind(str, Enum):
    """Type of pacing directive issued to other systems."""
    SPAWN_ENEMIES = "spawn_enemies"
    DESPAWN_ENEMIES = "despawn_enemies"
    ADJUST_DIFFICULTY = "adjust_difficulty"
    TRIGGER_NARRATIVE = "trigger_narrative"
    TRIGGER_REST = "trigger_rest"
    TRIGGER_CHALLENGE = "trigger_challenge"
    TRIGGER_REWARD = "trigger_reward"
    ADJUST_PACING = "adjust_pacing"
    SET_INTENSITY_TARGET = "set_intensity_target"
    SUGGEST_SAVE_POINT = "suggest_save_point"


class TelemetryKind(str, Enum):
    """Category of gameplay telemetry signal."""
    KILL = "kill"
    DEATH = "death"
    DAMAGE_DEALT = "damage_dealt"
    DAMAGE_TAKEN = "damage_taken"
    OBJECTIVE = "objective"
    MOVEMENT = "movement"
    RESOURCE_GAIN = "resource_gain"
    RESOURCE_LOSS = "resource_loss"
    IDLE = "idle"
    COMBO = "combo"
    FAIL = "fail"
    CUSTOM = "custom"


class PacingEventKind(str, Enum):
    CURVE_REGISTERED = "curve_registered"
    CURVE_REMOVED = "curve_removed"
    CURVE_ACTIVATED = "curve_activated"
    TELEMETRY_RECEIVED = "telemetry_received"
    DIRECTIVE_ISSUED = "directive_issued"
    DIRECTIVE_CONSUMED = "directive_consumed"
    PHASE_CHANGED = "phase_changed"
    INTENSITY_UPDATED = "intensity_updated"
    ENGAGEMENT_UPDATED = "engagement_updated"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class IntensityKeyframe:
    """A single point on an intensity curve."""
    time: float
    intensity: float
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PacingCurve:
    """A scripted intensity curve over time."""
    curve_id: str
    name: str = ""
    duration: float = 300.0
    loop: bool = True
    keyframes: List[IntensityKeyframe] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TelemetrySample:
    """A single gameplay telemetry signal."""
    sample_id: str
    kind: str
    timestamp: float
    player_id: str = ""
    intensity_delta: float = 0.0
    value: float = 0.0
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PacingDirective:
    """A directive issued by the pacing director to other systems."""
    directive_id: str
    kind: str
    timestamp: float
    intensity_target: float = 0.5
    phase: str = PacingPhase.BUILDUP.value
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    consumed: bool = False
    consumed_by: str = ""
    expires_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EngagementState:
    """Snapshot of the player's engagement metrics."""
    level: str = EngagementLevel.ENGAGED.value
    intensity: float = 0.5
    flow_score: float = 0.5
    challenge: float = 0.5
    skill: float = 0.5
    fatigue: float = 0.0
    boredom: float = 0.0
    frustration: float = 0.0
    last_kill_time: float = 0.0
    last_death_time: float = 0.0
    kill_streak: int = 0
    death_streak: int = 0
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PacingConfig:
    target_flow_score: float = 0.7
    intensity_smoothing: float = 0.15
    fatigue_decay_per_tick: float = 0.005
    fatigue_gain_per_kill: float = 0.02
    fatigue_gain_per_death: float = 0.04
    boredom_gain_per_idle_tick: float = 0.01
    boredom_decay_per_event: float = 0.05
    frustration_gain_per_fail: float = 0.03
    frustration_decay_per_tick: float = 0.008
    phase_change_threshold: float = 0.25
    climax_intensity_threshold: float = 0.85
    lull_intensity_threshold: float = 0.25
    rest_duration: float = 30.0
    max_directives: int = 200
    auto_issue_directives: bool = True
    default_curve_id: str = "curve_default_arc"

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PacingStats:
    total_telemetry: int = 0
    total_directives_issued: int = 0
    total_directives_consumed: int = 0
    total_phase_changes: int = 0
    average_intensity: float = 0.5
    average_flow_score: float = 0.5
    time_in_flow: float = 0.0
    time_in_burnout: float = 0.0
    time_in_boredom: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PacingSnapshot:
    engagement: Dict[str, Any] = field(default_factory=dict)
    phase: str = PacingPhase.BUILDUP.value
    intensity: float = 0.5
    active_curve_id: str = ""
    curves: List[Dict[str, Any]] = field(default_factory=list)
    pending_directives: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PacingEvent:
    event_id: str
    kind: str
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Pacing Director
# ---------------------------------------------------------------------------

class PacingDirector:
    """AI director that orchestrates gameplay intensity and engagement rhythm."""

    _instance: Optional["PacingDirector"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._curves: Dict[str, PacingCurve] = {}
        self._telemetry: List[TelemetrySample] = []
        self._directives: List[PacingDirective] = []
        self._events: List[PacingEvent] = []
        self._intensity_history: List[float] = []
        self._engagement = EngagementState()
        self._stats = PacingStats()
        self._config = PacingConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._directive_counter: int = 0
        self._telemetry_counter: int = 0
        self._phase: str = PacingPhase.BUILDUP.value
        self._active_curve_id: str = ""
        self._curve_time: float = 0.0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "PacingDirector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed default pacing curves and an initial engagement state."""
        default_curve = PacingCurve(
            curve_id=self._config.default_curve_id,
            name="Default Narrative Arc",
            duration=600.0,
            loop=True,
            keyframes=[
                IntensityKeyframe(time=0.0, intensity=0.2, label="intro"),
                IntensityKeyframe(time=60.0, intensity=0.35, label="rising_action"),
                IntensityKeyframe(time=180.0, intensity=0.55, label="midpoint"),
                IntensityKeyframe(time=300.0, intensity=0.75, label="escalation"),
                IntensityKeyframe(time=450.0, intensity=0.95, label="climax"),
                IntensityKeyframe(time=540.0, intensity=0.6, label="denouement"),
                IntensityKeyframe(time=600.0, intensity=0.25, label="resolution"),
            ],
        )
        self._curves[default_curve.curve_id] = default_curve

        boss_curve = PacingCurve(
            curve_id="curve_boss_encounter",
            name="Boss Encounter",
            duration=180.0,
            loop=False,
            keyframes=[
                IntensityKeyframe(time=0.0, intensity=0.6, label="approach"),
                IntensityKeyframe(time=30.0, intensity=0.8, label="phase_one"),
                IntensityKeyframe(time=90.0, intensity=0.9, label="phase_two"),
                IntensityKeyframe(time=150.0, intensity=1.0, label="final_phase"),
                IntensityKeyframe(time=180.0, intensity=0.4, label="victory"),
            ],
        )
        self._curves[boss_curve.curve_id] = boss_curve

        exploration_curve = PacingCurve(
            curve_id="curve_exploration",
            name="Open Exploration",
            duration=240.0,
            loop=True,
            keyframes=[
                IntensityKeyframe(time=0.0, intensity=0.15, label="calm"),
                IntensityKeyframe(time=60.0, intensity=0.3, label="discovery"),
                IntensityKeyframe(time=120.0, intensity=0.25, label="wandering"),
                IntensityKeyframe(time=180.0, intensity=0.4, label="encounter"),
                IntensityKeyframe(time=240.0, intensity=0.2, label="return"),
            ],
        )
        self._curves[exploration_curve.curve_id] = exploration_curve

        self._active_curve_id = default_curve.curve_id
        self._engagement = EngagementState(
            level=EngagementLevel.ENGAGED.value,
            intensity=0.3,
            flow_score=0.5,
            challenge=0.4,
            skill=0.5,
            fatigue=0.0,
            boredom=0.0,
            frustration=0.0,
            updated_at=_now(),
        )
        self._intensity_history = [0.3]
        self._phase = PacingPhase.BUILDUP.value
        self._initialized = True

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def _next_event_id(self) -> str:
        self._event_counter += 1
        return f"pevt_{self._event_counter:08d}"

    def _next_directive_id(self) -> str:
        self._directive_counter += 1
        return f"dir_{self._directive_counter:08d}"

    def _next_telemetry_id(self) -> str:
        self._telemetry_counter += 1
        return f"ts_{self._telemetry_counter:08d}"

    def _record_event(self, kind: str, **kwargs: Any) -> PacingEvent:
        event = PacingEvent(
            event_id=self._next_event_id(),
            kind=kind,
            timestamp=_now(),
            **kwargs,
        )
        self._events.append(event)
        if len(self._events) > _MAX_EVENTS:
            self._events = self._events[-_MAX_EVENTS:]
        return event

    # ------------------------------------------------------------------
    # Curve Management
    # ------------------------------------------------------------------

    def register_curve(self, curve: PacingCurve) -> Dict[str, Any]:
        if len(self._curves) >= _MAX_CURVES and curve.curve_id not in self._curves:
            oldest_id = next(iter(self._curves))
            if oldest_id != self._config.default_curve_id:
                self._curves.pop(oldest_id, None)
        was_new = curve.curve_id not in self._curves
        self._curves[curve.curve_id] = curve
        self._record_event(
            PacingEventKind.CURVE_REGISTERED if was_new else PacingEventKind.CONFIG_UPDATED,
            details={"curve_id": curve.curve_id, "name": curve.name, "duration": curve.duration},
        )
        return {"curve_id": curve.curve_id, "registered": True}

    def remove_curve(self, curve_id: str) -> Dict[str, Any]:
        if curve_id == self._config.default_curve_id:
            return {"curve_id": curve_id, "removed": False, "reason": "default curve cannot be removed"}
        if curve_id not in self._curves:
            return {"curve_id": curve_id, "removed": False, "reason": "not found"}
        self._curves.pop(curve_id)
        if self._active_curve_id == curve_id:
            self._active_curve_id = self._config.default_curve_id
            self._curve_time = 0.0
        self._record_event(PacingEventKind.CURVE_REMOVED, details={"curve_id": curve_id})
        return {"curve_id": curve_id, "removed": True}

    def get_curve(self, curve_id: str) -> Optional[PacingCurve]:
        return self._curves.get(curve_id)

    def list_curves(self, limit: int = 100) -> List[PacingCurve]:
        return list(self._curves.values())[:max(0, min(limit, len(self._curves)))]

    def activate_curve(self, curve_id: str, start_time: float = 0.0) -> Dict[str, Any]:
        if curve_id not in self._curves:
            return {"curve_id": curve_id, "activated": False, "reason": "not found"}
        self._active_curve_id = curve_id
        self._curve_time = start_time
        self._record_event(
            PacingEventKind.CURVE_ACTIVATED,
            details={"curve_id": curve_id, "start_time": start_time},
        )
        return {"curve_id": curve_id, "activated": True, "start_time": start_time}

    def get_active_curve(self) -> Dict[str, Any]:
        curve = self._curves.get(self._active_curve_id)
        if curve is None:
            return {"curve_id": "", "name": "", "curve_time": self._curve_time}
        return {"curve_id": curve.curve_id, "name": curve.name, "curve_time": self._curve_time, "duration": curve.duration}

    # ------------------------------------------------------------------
    # Curve intensity evaluation
    # ------------------------------------------------------------------

    def _evaluate_curve(self, curve: PacingCurve, time_in_curve: float) -> float:
        if not curve.keyframes:
            return 0.5
        keyframes = sorted(curve.keyframes, key=lambda k: k.time)
        if curve.loop and curve.duration > 0:
            t = time_in_curve % curve.duration
        else:
            t = _clamp(time_in_curve, 0.0, curve.duration)
        if t <= keyframes[0].time:
            return _clamp(keyframes[0].intensity, 0.0, 1.0)
        if t >= keyframes[-1].time:
            return _clamp(keyframes[-1].intensity, 0.0, 1.0)
        for i in range(len(keyframes) - 1):
            k0 = keyframes[i]
            k1 = keyframes[i + 1]
            if k0.time <= t <= k1.time:
                span = max(k1.time - k0.time, 1e-6)
                local_t = (t - k0.time) / span
                # Smootherstep interpolation
                smooth_t = local_t * local_t * local_t * (local_t * (local_t * 6.0 - 15.0) + 10.0)
                return _clamp(_lerp(k0.intensity, k1.intensity, smooth_t), 0.0, 1.0)
        return _clamp(keyframes[-1].intensity, 0.0, 1.0)

    # ------------------------------------------------------------------
    # Telemetry ingestion
    # ------------------------------------------------------------------

    def submit_telemetry(self, sample: TelemetrySample) -> Dict[str, Any]:
        if len(self._telemetry) >= _MAX_TELEMETRY:
            self._telemetry = self._telemetry[-_MAX_TELEMETRY + 1:]
        self._telemetry.append(sample)
        self._stats.total_telemetry += 1

        # Update engagement based on telemetry kind
        eng = self._engagement
        if sample.kind == TelemetryKind.KILL.value:
            eng.kill_streak = max(eng.kill_streak, 0) + 1
            eng.death_streak = 0
            eng.last_kill_time = sample.timestamp
            eng.fatigue = _clamp(eng.fatigue + self._config.fatigue_gain_per_kill, 0.0, 1.0)
            eng.boredom = _clamp(eng.boredom - self._config.boredom_decay_per_event, 0.0, 1.0)
            eng.challenge = _clamp(eng.challenge + 0.02, 0.0, 1.0)
        elif sample.kind == TelemetryKind.DEATH.value:
            eng.death_streak += 1
            eng.kill_streak = 0
            eng.last_death_time = sample.timestamp
            eng.fatigue = _clamp(eng.fatigue + self._config.fatigue_gain_per_death, 0.0, 1.0)
            eng.frustration = _clamp(eng.frustration + 0.05, 0.0, 1.0)
            eng.challenge = _clamp(eng.challenge + 0.05, 0.0, 1.0)
        elif sample.kind == TelemetryKind.OBJECTIVE.value:
            eng.boredom = _clamp(eng.boredom - self._config.boredom_decay_per_event * 2.0, 0.0, 1.0)
            eng.frustration = _clamp(eng.frustration - 0.03, 0.0, 1.0)
        elif sample.kind == TelemetryKind.FAIL.value:
            eng.frustration = _clamp(eng.frustration + self._config.frustration_gain_per_fail, 0.0, 1.0)
        elif sample.kind == TelemetryKind.IDLE.value:
            eng.boredom = _clamp(eng.boredom + self._config.boredom_gain_per_idle_tick, 0.0, 1.0)
        elif sample.kind == TelemetryKind.COMBO.value:
            eng.flow_score = _clamp(eng.flow_score + 0.05, 0.0, 1.0)
            eng.boredom = _clamp(eng.boredom - self._config.boredom_decay_per_event, 0.0, 1.0)
        eng.updated_at = _now()

        self._update_engagement_level()
        self._record_event(
            PacingEventKind.TELEMETRY_RECEIVED,
            details={
                "sample_id": sample.sample_id,
                "kind": sample.kind,
                "intensity_delta": sample.intensity_delta,
                "engagement_level": self._engagement.level,
            },
        )
        return {"sample_id": sample.sample_id, "engagement_level": self._engagement.level}

    # ------------------------------------------------------------------
    # Engagement level computation
    # ------------------------------------------------------------------

    def _update_engagement_level(self) -> None:
        """Derive categorical engagement level from numeric metrics."""
        eng = self._engagement
        # Flow score balances challenge and skill
        challenge_skill_gap = abs(eng.challenge - eng.skill)
        if eng.challenge > eng.skill + 0.2:
            eng.flow_score = _clamp(eng.flow_score - 0.02, 0.0, 1.0)
        elif eng.challenge < eng.skill - 0.2:
            eng.flow_score = _clamp(eng.flow_score - 0.01, 0.0, 1.0)
        else:
            eng.flow_score = _clamp(eng.flow_score + 0.02, 0.0, 1.0)

        # Determine categorical level
        if eng.fatigue > 0.7 or eng.frustration > 0.7:
            level = EngagementLevel.BURNOUT.value
        elif eng.fatigue > 0.5 or eng.frustration > 0.5:
            level = EngagementLevel.OVERWHELMED.value
        elif eng.boredom > 0.6:
            level = EngagementLevel.BORED.value
        elif eng.flow_score > 0.7 and eng.fatigue < 0.3:
            level = EngagementLevel.FLOW.value
        elif eng.flow_score > 0.5:
            level = EngagementLevel.ENGAGED.value
        else:
            level = EngagementLevel.ENGAGED.value

        if eng.level != level:
            eng.level = level
            self._record_event(
                PacingEventKind.ENGAGEMENT_UPDATED,
                details={"level": level, "flow_score": eng.flow_score},
            )

    def get_engagement(self) -> EngagementState:
        return self._engagement

    def set_engagement(self, engagement: EngagementState) -> Dict[str, Any]:
        self._engagement = engagement
        self._update_engagement_level()
        return {"updated": True, "level": self._engagement.level}

    # ------------------------------------------------------------------
    # Directive management
    # ------------------------------------------------------------------

    def issue_directive(self, directive: PacingDirective) -> Dict[str, Any]:
        if len(self._directives) >= self._config.max_directives:
            # Remove oldest consumed directive
            for i, d in enumerate(self._directives):
                if d.consumed:
                    self._directives.pop(i)
                    break
            else:
                self._directives.pop(0)
        self._directives.append(directive)
        self._stats.total_directives_issued += 1
        self._record_event(
            PacingEventKind.DIRECTIVE_ISSUED,
            details={
                "directive_id": directive.directive_id,
                "kind": directive.kind,
                "intensity_target": directive.intensity_target,
                "phase": directive.phase,
                "priority": directive.priority,
            },
        )
        return {"directive_id": directive.directive_id, "issued": True}

    def consume_directive(self, directive_id: str, consumed_by: str = "") -> Dict[str, Any]:
        for d in self._directives:
            if d.directive_id == directive_id:
                if d.consumed:
                    return {"directive_id": directive_id, "consumed": False, "reason": "already consumed"}
                d.consumed = True
                d.consumed_by = consumed_by
                self._stats.total_directives_consumed += 1
                self._record_event(
                    PacingEventKind.DIRECTIVE_CONSUMED,
                    details={"directive_id": directive_id, "consumed_by": consumed_by},
                )
                return {"directive_id": directive_id, "consumed": True}
        return {"directive_id": directive_id, "consumed": False, "reason": "not found"}

    def get_directive(self, directive_id: str) -> Optional[PacingDirective]:
        for d in self._directives:
            if d.directive_id == directive_id:
                return d
        return None

    def list_directives(self, kind: Optional[str] = None, consumed: Optional[bool] = None, limit: int = 100) -> List[PacingDirective]:
        results: List[PacingDirective] = []
        for d in self._directives:
            if kind is not None and d.kind != kind:
                continue
            if consumed is not None and d.consumed != consumed:
                continue
            results.append(d)
        return list(reversed(results))[:max(0, min(limit, len(results)))]

    def _auto_issue_directive(self) -> None:
        """Automatically issue a directive based on current engagement state."""
        if not self._config.auto_issue_directives:
            return
        eng = self._engagement
        now = _now()
        if eng.level == EngagementLevel.BURNOUT.value:
            self.issue_directive(PacingDirective(
                directive_id=self._next_directive_id(),
                kind=DirectiveKind.TRIGGER_REST.value,
                timestamp=now,
                intensity_target=self._config.lull_intensity_threshold,
                phase=PacingPhase.REST.value,
                parameters={"duration": self._config.rest_duration, "reason": "burnout_detected"},
                priority=9,
                expires_at=now + self._config.rest_duration,
            ))
        elif eng.level == EngagementLevel.OVERWHELMED.value:
            self.issue_directive(PacingDirective(
                directive_id=self._next_directive_id(),
                kind=DirectiveKind.ADJUST_DIFFICULTY.value,
                timestamp=now,
                intensity_target=max(0.2, eng.intensity - 0.2),
                phase=self._phase,
                parameters={"delta": -0.2, "reason": "overwhelmed"},
                priority=7,
                expires_at=now + 15.0,
            ))
        elif eng.level == EngagementLevel.BORED.value:
            self.issue_directive(PacingDirective(
                directive_id=self._next_directive_id(),
                kind=DirectiveKind.TRIGGER_CHALLENGE.value,
                timestamp=now,
                intensity_target=min(1.0, eng.intensity + 0.25),
                phase=PacingPhase.BUILDUP.value,
                parameters={"delta": 0.25, "reason": "boredom_detected"},
                priority=7,
                expires_at=now + 20.0,
            ))
        elif eng.level == EngagementLevel.FLOW.value and eng.kill_streak > 0 and eng.kill_streak % 5 == 0:
            self.issue_directive(PacingDirective(
                directive_id=self._next_directive_id(),
                kind=DirectiveKind.TRIGGER_REWARD.value,
                timestamp=now,
                intensity_target=eng.intensity,
                phase=self._phase,
                parameters={"kill_streak": eng.kill_streak, "reason": "flow_reward"},
                priority=5,
                expires_at=now + 10.0,
            ))

    # ------------------------------------------------------------------
    # Phase management
    # ------------------------------------------------------------------

    def get_phase(self) -> str:
        return self._phase

    def set_phase(self, phase: str) -> Dict[str, Any]:
        previous = self._phase
        self._phase = phase
        if previous != phase:
            self._stats.total_phase_changes += 1
            self._record_event(
                PacingEventKind.PHASE_CHANGED,
                details={"previous": previous, "current": phase},
            )
        return {"phase": phase, "previous": previous}

    def _update_phase(self, intensity: float) -> None:
        """Auto-derive phase from intensity level."""
        new_phase = self._phase
        if intensity >= self._config.climax_intensity_threshold:
            new_phase = PacingPhase.CLIMAX.value
        elif intensity <= self._config.lull_intensity_threshold:
            if self._engagement.fatigue > 0.5:
                new_phase = PacingPhase.REST.value
            else:
                new_phase = PacingPhase.LULL.value
        elif self._phase == PacingPhase.LULL.value or self._phase == PacingPhase.REST.value:
            new_phase = PacingPhase.BUILDUP.value
        elif self._phase == PacingPhase.CLIMAX.value and intensity < self._config.climax_intensity_threshold - 0.1:
            new_phase = PacingPhase.RESOLUTION.value
        self.set_phase(new_phase)

    # ------------------------------------------------------------------
    # Intensity management
    # ------------------------------------------------------------------

    def get_intensity(self) -> float:
        return self._engagement.intensity

    def set_intensity(self, intensity: float) -> Dict[str, Any]:
        intensity = _clamp(intensity, 0.0, 1.0)
        previous = self._engagement.intensity
        self._engagement.intensity = intensity
        self._intensity_history.append(intensity)
        if len(self._intensity_history) > _INTENSITY_HISTORY:
            self._intensity_history = self._intensity_history[-_INTENSITY_HISTORY:]
        self._update_phase(intensity)
        self._record_event(
            PacingEventKind.INTENSITY_UPDATED,
            details={"previous": previous, "current": intensity, "phase": self._phase},
        )
        return {"intensity": intensity, "phase": self._phase}

    def get_intensity_history(self, limit: int = 100) -> List[float]:
        return list(self._intensity_history)[-max(0, min(limit, len(self._intensity_history))):]

    # ------------------------------------------------------------------
    # Tick / lifecycle
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 0.016, current_time: float = 0.0) -> Dict[str, Any]:
        self._tick_count += 1
        self._stats.tick_count = self._tick_count

        # Advance curve time
        self._curve_time += delta_time

        # Evaluate target intensity from active curve
        curve = self._curves.get(self._active_curve_id)
        if curve is not None and curve.enabled:
            target = self._evaluate_curve(curve, self._curve_time)
            # Smooth toward target
            smoothing = max(self._config.intensity_smoothing, 1e-6)
            current = self._engagement.intensity
            new_intensity = _lerp(current, target, min(1.0, delta_time / smoothing))
            self._engagement.intensity = _clamp(new_intensity, 0.0, 1.0)
            self._intensity_history.append(self._engagement.intensity)
            if len(self._intensity_history) > _INTENSITY_HISTORY:
                self._intensity_history = self._intensity_history[-_INTENSITY_HISTORY:]
            self._update_phase(self._engagement.intensity)

        # Decay fatigue, boredom, frustration over time
        eng = self._engagement
        eng.fatigue = _clamp(eng.fatigue - self._config.fatigue_decay_per_tick, 0.0, 1.0)
        eng.frustration = _clamp(eng.frustration - self._config.frustration_decay_per_tick, 0.0, 1.0)
        # Skill slowly tracks challenge
        if eng.challenge > eng.skill:
            eng.skill = _clamp(eng.skill + 0.001, 0.0, 1.0)
        elif eng.challenge < eng.skill - 0.1:
            eng.skill = _clamp(eng.skill - 0.0005, 0.0, 1.0)

        self._update_engagement_level()

        # Update time-in-state stats
        if eng.level == EngagementLevel.FLOW.value:
            self._stats.time_in_flow += delta_time
        elif eng.level == EngagementLevel.BURNOUT.value:
            self._stats.time_in_burnout += delta_time
        elif eng.level == EngagementLevel.BORED.value:
            self._stats.time_in_boredom += delta_time

        # Update average stats
        if self._intensity_history:
            self._stats.average_intensity = sum(self._intensity_history) / len(self._intensity_history)
        self._stats.average_flow_score = eng.flow_score

        # Auto-issue directives
        self._auto_issue_directive()

        # Expire old directives
        now = _now()
        self._directives = [d for d in self._directives if d.expires_at == 0.0 or d.expires_at > now or d.consumed]

        self._record_event(
            PacingEventKind.TICK,
            details={
                "delta_time": delta_time,
                "tick": self._tick_count,
                "intensity": eng.intensity,
                "phase": self._phase,
                "engagement": eng.level,
            },
        )
        if len(self._events) > _MAX_EVENTS:
            self._events = self._events[-_MAX_EVENTS:]

        return {
            "tick": self._tick_count,
            "delta_time": delta_time,
            "intensity": eng.intensity,
            "phase": self._phase,
            "engagement": eng.level,
        }

    def get_config(self) -> PacingConfig:
        return self._config

    def set_config(self, config: PacingConfig) -> Dict[str, Any]:
        self._config = config
        self._record_event(PacingEventKind.CONFIG_UPDATED, details={"target_flow_score": config.target_flow_score})
        return {"updated": True}

    def list_events(self, kind: Optional[str] = None, limit: int = 100) -> List[PacingEvent]:
        results: List[PacingEvent] = []
        for e in self._events:
            if kind is not None and e.kind != kind:
                continue
            results.append(e)
        return list(reversed(results))[:max(0, min(limit, len(results)))]

    def get_stats(self) -> PacingStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "phase": self._phase,
            "intensity": self._engagement.intensity,
            "engagement_level": self._engagement.level,
            "flow_score": self._engagement.flow_score,
            "total_curves": len(self._curves),
            "active_curve_id": self._active_curve_id,
            "pending_directives": sum(1 for d in self._directives if not d.consumed),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> PacingSnapshot:
        return PacingSnapshot(
            engagement=self._engagement.to_dict(),
            phase=self._phase,
            intensity=self._engagement.intensity,
            active_curve_id=self._active_curve_id,
            curves=[c.to_dict() for c in self._curves.values()],
            pending_directives=sum(1 for d in self._directives if not d.consumed),
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
            timestamp=_now(),
        )

    def reset(self) -> Dict[str, Any]:
        self._curves.clear()
        self._telemetry.clear()
        self._directives.clear()
        self._events.clear()
        self._intensity_history.clear()
        self._engagement = EngagementState()
        self._stats = PacingStats()
        self._tick_count = 0
        self._event_counter = 0
        self._directive_counter = 0
        self._telemetry_counter = 0
        self._phase = PacingPhase.BUILDUP.value
        self._active_curve_id = ""
        self._curve_time = 0.0
        self._initialized = False
        self._seed()
        self._record_event(PacingEventKind.RESET)
        return {"reset": True, "initialized": self._initialized}


def get_pacing_director() -> PacingDirector:
    return PacingDirector.get_instance()