"""
SparkLabs Agent - Frame Architect"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class ShotType(Enum):
    """Cinematographic shot types."""
    EXTREME_WIDE = "extreme_wide"
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    OVER_THE_SHOULDER = "over_the_shoulder"
    POINT_OF_VIEW = "point_of_view"
    AERIAL = "aerial"
    TRACKING = "tracking"
    ORBIT = "orbit"


class CameraAngle(Enum):
    """Camera angle relative to subject."""
    EYE_LEVEL = "eye_level"
    LOW_ANGLE = "low_angle"
    HIGH_ANGLE = "high_angle"
    DUTCH_TILT = "dutch_tilt"
    BIRDS_EYE = "birds_eye"
    WORMS_EYE = "worms_eye"


class LightingMood(Enum):
    """Lighting mood for the frame."""
    NATURAL = "natural"
    DRAMATIC = "dramatic"
    SOFT = "soft"
    HIGH_CONTRAST = "high_contrast"
    WARM = "warm"
    COLD = "cold"
    NEON = "neon"
    GOLDEN_HOUR = "golden_hour"
    NIGHT = "night"
    EERIE = "eerie"


class TransitionType(Enum):
    """Transition between frames/scenes."""
    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"
    WHIP_PAN = "whip_pan"
    ZOOM = "zoom"
    DOLLY = "dolly"
    IRIS = "iris"
    NONE = "none"


class FramePhase(Enum):
    """Phases of the frame architect cycle."""
    ANALYZE = "analyze"
    COMPOSE = "compose"
    DIRECT = "direct"
    TRANSITION = "transition"
    REVIEW = "review"


class SceneIntensity(Enum):
    """Calculated intensity level of the current scene."""
    CALM = 0
    MODERATE = 1
    INTENSE = 2
    PEAK = 3
    CHAOTIC = 4


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class SceneContext:
    """Extracted features from the current game state."""
    player_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    player_velocity: float = 0.0
    player_health: float = 1.0
    player_health_trend: str = "stable"  # "rising", "falling", "stable"
    action_intensity: float = 0.0  # 0.0 = idle, 1.0 = max combat
    enemy_count_nearby: int = 0
    narrative_tension: float = 0.2  # from StoryDirector
    emotional_context: str = "neutral"  # "tense", "joyful", "sad", "fearful", "neutral"
    environment_type: str = "outdoor"  # "indoor", "outdoor", "underground", "sky"
    time_of_day: str = "day"  # "dawn", "day", "dusk", "night"
    is_cutscene: bool = False
    is_boss_fight: bool = False
    is_dialogue: bool = False


@dataclass
class FrameDirective:
    """A single cinematographic frame directive emitted by the architect."""
    directive_id: str
    shot_type: ShotType
    camera_angle: CameraAngle
    lighting_mood: LightingMood
    transition: TransitionType
    focal_point: Tuple[float, float, float]
    depth_of_field: float  # 0.0 = infinite, 1.0 = very shallow
    field_of_view: float  # in degrees, 15-120
    camera_distance: float  # in world units
    camera_height: float  # in world units
    shake_intensity: float  # 0.0 = none, 1.0 = max
    movement_speed: float  # camera movement speed multiplier
    duration_hint: float  # suggested duration in seconds
    rationale: str  # why this frame was chosen
    timestamp: float = field(default_factory=time.time)


@dataclass
class FrameArchitectStats:
    """Statistics for the frame architect."""
    total_cycles: int = 0
    total_directives_emitted: int = 0
    total_transitions: int = 0
    avg_intensity: float = 0.0
    most_used_shot: str = ""
    most_used_lighting: str = ""
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Agent Frame Architect
# =============================================================================

class AgentFrameArchitect:
    """
    Singleton agent that generates real-time cinematographic frame directives.

    The architect runs a 5-phase cycle:
      1. ANALYZE   - Extract scene features from game state
      2. COMPOSE   - Select shot strategy based on intensity and context
      3. DIRECT    - Emit a structured frame directive
      4. TRANSITION- Manage cuts, pacing, and transitions
      5. REVIEW    - Verify frame quality and adjust

    The architect responds to narrative tension (from AgentStoryDirector),
    player state (from the game bridge), and engine metrics to create
    cinematically compelling frame compositions in real-time.
    """

    _instance: Optional["AgentFrameArchitect"] = None
    _instance_lock = threading.Lock()

    # Shot selection matrix: intensity -> preferred shots
    INTENSITY_SHOT_MAP: Dict[SceneIntensity, List[ShotType]] = {
        SceneIntensity.CALM: [ShotType.WIDE, ShotType.MEDIUM, ShotType.AERIAL],
        SceneIntensity.MODERATE: [ShotType.MEDIUM, ShotType.TRACKING, ShotType.OVER_THE_SHOULDER],
        SceneIntensity.INTENSE: [ShotType.CLOSE_UP, ShotType.TRACKING, ShotType.OVER_THE_SHOULDER],
        SceneIntensity.PEAK: [ShotType.EXTREME_CLOSE_UP, ShotType.TRACKING, ShotType.POINT_OF_VIEW],
        SceneIntensity.CHAOTIC: [ShotType.POINT_OF_VIEW, ShotType.EXTREME_CLOSE_UP, ShotType.TRACKING],
    }

    # Lighting selection by emotional context
    EMOTION_LIGHTING_MAP: Dict[str, List[LightingMood]] = {
        "neutral": [LightingMood.NATURAL, LightingMood.SOFT],
        "tense": [LightingMood.DRAMATIC, LightingMood.HIGH_CONTRAST, LightingMood.EERIE],
        "joyful": [LightingMood.WARM, LightingMood.GOLDEN_HOUR],
        "sad": [LightingMood.COLD, LightingMood.SOFT],
        "fearful": [LightingMood.EERIE, LightingMood.NIGHT, LightingMood.HIGH_CONTRAST],
    }

    # Transition pacing by intensity change
    TRANSITION_MAP: Dict[str, TransitionType] = {
        "calm_to_intense": TransitionType.CUT,
        "intense_to_calm": TransitionType.DISSOLVE,
        "same_intensity": TransitionType.CUT,
        "cutscene_enter": TransitionType.FADE,
        "cutscene_exit": TransitionType.FADE,
        "dialogue_shift": TransitionType.DOLLY,
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._stats = FrameArchitectStats()
        self._directive_history: Deque[FrameDirective] = deque(maxlen=100)
        self._current_directive: Optional[FrameDirective] = None
        self._current_context: SceneContext = SceneContext()
        self._current_intensity: SceneIntensity = SceneIntensity.CALM
        self._previous_intensity: SceneIntensity = SceneIntensity.CALM
        self._cycle_count: int = 0
        self._last_cycle_at: float = 0.0
        self._cycle_interval_s: float = 1.0  # Run every 1 second
        self._active: bool = False
        self._shot_usage: Dict[str, int] = {}
        self._lighting_usage: Dict[str, int] = {}

    @classmethod
    def get_instance(cls) -> "AgentFrameArchitect":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Phase 1: ANALYZE - Extract scene features
    # -------------------------------------------------------------------------

    def update_context(self, player_pos: Optional[List[float]] = None,
                       player_velocity: Optional[float] = None,
                       player_health: Optional[float] = None,
                       player_health_trend: Optional[str] = None,
                       action_intensity: Optional[float] = None,
                       enemy_count: Optional[int] = None,
                       narrative_tension: Optional[float] = None,
                       emotional_context: Optional[str] = None,
                       environment_type: Optional[str] = None,
                       time_of_day: Optional[str] = None,
                       is_cutscene: Optional[bool] = None,
                       is_boss_fight: Optional[bool] = None,
                       is_dialogue: Optional[bool] = None) -> Dict[str, Any]:
        """Update the current scene context. Returns the updated context."""
        with self._lock:
            ctx = self._current_context
            if player_pos is not None:
                ctx.player_position = tuple(player_pos[:3]) if len(player_pos) >= 3 else (0.0, 0.0, 0.0)
            if player_velocity is not None:
                ctx.player_velocity = max(0.0, float(player_velocity))
            if player_health is not None:
                ctx.player_health = max(0.0, min(1.0, float(player_health)))
            if player_health_trend is not None:
                ctx.player_health_trend = player_health_trend
            if action_intensity is not None:
                ctx.action_intensity = max(0.0, min(1.0, float(action_intensity)))
            if enemy_count is not None:
                ctx.enemy_count_nearby = max(0, int(enemy_count))
            if narrative_tension is not None:
                ctx.narrative_tension = max(0.0, min(1.0, float(narrative_tension)))
            if emotional_context is not None:
                ctx.emotional_context = emotional_context
            if environment_type is not None:
                ctx.environment_type = environment_type
            if time_of_day is not None:
                ctx.time_of_day = time_of_day
            if is_cutscene is not None:
                ctx.is_cutscene = bool(is_cutscene)
            if is_boss_fight is not None:
                ctx.is_boss_fight = bool(is_boss_fight)
            if is_dialogue is not None:
                ctx.is_dialogue = bool(is_dialogue)
            return self._context_to_dict(ctx)

    def _calculate_intensity(self, ctx: SceneContext) -> SceneIntensity:
        """Calculate the overall scene intensity from context features."""
        # Weighted combination of factors
        score = 0.0
        score += ctx.action_intensity * 0.35
        score += ctx.narrative_tension * 0.25
        score += min(ctx.enemy_count_nearby / 5.0, 1.0) * 0.20
        score += (1.0 - ctx.player_health) * 0.15 if ctx.player_health_trend == "falling" else 0.0
        score += 0.20 if ctx.is_boss_fight else 0.0

        if score < 0.15:
            return SceneIntensity.CALM
        elif score < 0.35:
            return SceneIntensity.MODERATE
        elif score < 0.55:
            return SceneIntensity.INTENSE
        elif score < 0.75:
            return SceneIntensity.PEAK
        else:
            return SceneIntensity.CHAOTIC

    # -------------------------------------------------------------------------
    # Phase 2: COMPOSE - Select shot strategy
    # -------------------------------------------------------------------------

    def _select_shot(self, intensity: SceneIntensity, ctx: SceneContext) -> ShotType:
        """Select a shot type based on intensity and context."""
        # Special cases first
        if ctx.is_cutscene:
            # Cutscenes prefer wider, more cinematic shots
            return random.choice([ShotType.WIDE, ShotType.MEDIUM, ShotType.AERIAL])
        if ctx.is_dialogue:
            return random.choice([ShotType.OVER_THE_SHOULDER, ShotType.CLOSE_UP, ShotType.MEDIUM])
        if ctx.is_boss_fight:
            return random.choice([ShotType.WIDE, ShotType.TRACKING, ShotType.MEDIUM])

        # General case: use intensity map
        shots = self.INTENSITY_SHOT_MAP.get(intensity, [ShotType.MEDIUM])
        return random.choice(shots)

    def _select_angle(self, shot: ShotType, intensity: SceneIntensity,
                      ctx: SceneContext) -> CameraAngle:
        """Select camera angle based on shot and context."""
        if shot == ShotType.AERIAL:
            return CameraAngle.BIRDS_EYE
        if shot == ShotType.POINT_OF_VIEW:
            return CameraAngle.EYE_LEVEL

        if ctx.is_boss_fight:
            # Low angle makes bosses look imposing
            return random.choice([CameraAngle.LOW_ANGLE, CameraAngle.EYE_LEVEL])

        if intensity in (SceneIntensity.PEAK, SceneIntensity.CHAOTIC):
            return random.choice([CameraAngle.LOW_ANGLE, CameraAngle.DUTCH_TILT, CameraAngle.EYE_LEVEL])

        if ctx.emotional_context == "fearful":
            return random.choice([CameraAngle.HIGH_ANGLE, CameraAngle.DUTCH_TILT])

        return random.choice([CameraAngle.EYE_LEVEL, CameraAngle.EYE_LEVEL, CameraAngle.HIGH_ANGLE])

    def _select_lighting(self, ctx: SceneContext) -> LightingMood:
        """Select lighting mood based on emotional context and environment."""
        # Time of day overrides
        if ctx.time_of_day == "night":
            return random.choice([LightingMood.NIGHT, LightingMood.NEON, LightingMood.EERIE])
        if ctx.time_of_day == "dusk":
            return random.choice([LightingMood.GOLDEN_HOUR, LightingMood.WARM])
        if ctx.time_of_day == "dawn":
            return LightingMood.GOLDEN_HOUR

        # Environment overrides
        if ctx.environment_type == "underground":
            return random.choice([LightingMood.EERIE, LightingMood.DRAMATIC])

        # Emotional context mapping
        moods = self.EMOTION_LIGHTING_MAP.get(ctx.emotional_context, [LightingMood.NATURAL])
        return random.choice(moods)

    def _select_transition(self, prev_intensity: SceneIntensity,
                           curr_intensity: SceneIntensity,
                           ctx: SceneContext) -> TransitionType:
        """Select transition type based on intensity change."""
        if ctx.is_cutscene and self._current_directive is None:
            return self.TRANSITION_MAP["cutscene_enter"]

        if prev_intensity == curr_intensity:
            return self.TRANSITION_MAP["same_intensity"]

        if curr_intensity.value > prev_intensity.value:
            return self.TRANSITION_MAP["calm_to_intense"]
        else:
            return self.TRANSITION_MAP["intense_to_calm"]

    def _calculate_dof(self, shot: ShotType, intensity: SceneIntensity) -> float:
        """Calculate depth of field (0=infinite, 1=very shallow)."""
        if shot in (ShotType.EXTREME_CLOSE_UP, ShotType.CLOSE_UP):
            return random.uniform(0.6, 0.9)
        if shot == ShotType.OVER_THE_SHOULDER:
            return random.uniform(0.4, 0.7)
        if intensity in (SceneIntensity.PEAK, SceneIntensity.CHAOTIC):
            return random.uniform(0.2, 0.5)  # deeper focus for action
        return random.uniform(0.1, 0.3)

    def _calculate_fov(self, shot: ShotType, intensity: SceneIntensity) -> float:
        """Calculate field of view in degrees."""
        if shot == ShotType.EXTREME_WIDE or shot == ShotType.AERIAL:
            return random.uniform(80, 110)
        if shot == ShotType.WIDE:
            return random.uniform(60, 80)
        if shot == ShotType.MEDIUM:
            return random.uniform(45, 60)
        if shot in (ShotType.CLOSE_UP, ShotType.EXTREME_CLOSE_UP):
            return random.uniform(25, 40)
        if intensity in (SceneIntensity.PEAK, SceneIntensity.CHAOTIC):
            return random.uniform(50, 70)  # wider for action awareness
        return random.uniform(40, 55)

    def _calculate_shake(self, intensity: SceneIntensity, ctx: SceneContext) -> float:
        """Calculate camera shake intensity."""
        if intensity == SceneIntensity.CHAOTIC:
            return random.uniform(0.4, 0.8)
        if intensity == SceneIntensity.PEAK:
            return random.uniform(0.2, 0.5)
        if ctx.is_boss_fight and intensity.value >= SceneIntensity.INTENSE.value:
            return random.uniform(0.15, 0.35)
        return 0.0

    # -------------------------------------------------------------------------
    # Phase 3: DIRECT - Emit frame directive
    # -------------------------------------------------------------------------

    def _compose_directive(self, ctx: SceneContext, intensity: SceneIntensity) -> FrameDirective:
        """Compose a complete frame directive from context and intensity."""
        shot = self._select_shot(intensity, ctx)
        angle = self._select_angle(shot, intensity, ctx)
        lighting = self._select_lighting(ctx)
        transition = self._select_transition(self._previous_intensity, intensity, ctx)
        dof = self._calculate_dof(shot, intensity)
        fov = self._calculate_fov(shot, intensity)
        shake = self._calculate_shake(intensity, ctx)

        # Camera positioning
        if shot == ShotType.AERIAL:
            distance = random.uniform(30, 60)
            height = random.uniform(40, 80)
        elif shot in (ShotType.EXTREME_WIDE, ShotType.WIDE):
            distance = random.uniform(15, 30)
            height = random.uniform(5, 15)
        elif shot == ShotType.MEDIUM:
            distance = random.uniform(5, 10)
            height = random.uniform(2, 5)
        elif shot in (ShotType.CLOSE_UP, ShotType.EXTREME_CLOSE_UP):
            distance = random.uniform(1, 3)
            height = random.uniform(1.5, 2.5)
        else:
            distance = random.uniform(5, 12)
            height = random.uniform(2, 6)

        # Focal point = player position
        focal = ctx.player_position

        # Duration hint
        if ctx.is_cutscene:
            duration = random.uniform(3.0, 6.0)
        elif intensity in (SceneIntensity.PEAK, SceneIntensity.CHAOTIC):
            duration = random.uniform(0.8, 1.5)  # fast cuts
        elif intensity == SceneIntensity.CALM:
            duration = random.uniform(3.0, 5.0)  # slow, lingering
        else:
            duration = random.uniform(1.5, 3.0)

        # Movement speed
        if shot == ShotType.TRACKING:
            movement = random.uniform(1.2, 2.0)
        elif shot == ShotType.ORBIT:
            movement = random.uniform(0.5, 1.0)
        elif intensity in (SceneIntensity.PEAK, SceneIntensity.CHAOTIC):
            movement = random.uniform(1.0, 1.8)
        else:
            movement = random.uniform(0.3, 0.8)

        rationale = self._build_rationale(shot, angle, lighting, intensity, ctx)

        directive = FrameDirective(
            directive_id=f"frame_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
            shot_type=shot,
            camera_angle=angle,
            lighting_mood=lighting,
            transition=transition,
            focal_point=focal,
            depth_of_field=dof,
            field_of_view=fov,
            camera_distance=distance,
            camera_height=height,
            shake_intensity=shake,
            movement_speed=movement,
            duration_hint=duration,
            rationale=rationale,
        )

        # Track usage
        self._shot_usage[shot.value] = self._shot_usage.get(shot.value, 0) + 1
        self._lighting_usage[lighting.value] = self._lighting_usage.get(lighting.value, 0) + 1

        return directive

    def _build_rationale(self, shot: ShotType, angle: CameraAngle,
                         lighting: LightingMood, intensity: SceneIntensity,
                         ctx: SceneContext) -> str:
        """Build a human-readable rationale for the frame choice."""
        parts: List[str] = []
        parts.append(f"{intensity.name.lower()} scene")
        if ctx.is_boss_fight:
            parts.append("boss encounter")
        if ctx.is_dialogue:
            parts.append("dialogue moment")
        if ctx.is_cutscene:
            parts.append("cinematic sequence")
        parts.append(f"shot={shot.value}")
        parts.append(f"angle={angle.value}")
        parts.append(f"lighting={lighting.value}")
        if ctx.emotional_context != "neutral":
            parts.append(f"emotion={ctx.emotional_context}")
        return ", ".join(parts)

    # -------------------------------------------------------------------------
    # Phase 4: TRANSITION - Manage cuts and pacing
    # -------------------------------------------------------------------------

    def _manage_transition(self, directive: FrameDirective,
                           prev_directive: Optional[FrameDirective]) -> None:
        """Apply transition logic between previous and current directive."""
        if prev_directive is None:
            return

        # If same shot type and similar context, prefer no transition
        if (directive.shot_type == prev_directive.shot_type and
                directive.lighting_mood == prev_directive.lighting_mood):
            directive.transition = TransitionType.NONE

        # Track transition
        if directive.transition != TransitionType.NONE:
            self._stats.total_transitions += 1

    # -------------------------------------------------------------------------
    # Phase 5: REVIEW - Verify frame quality
    # -------------------------------------------------------------------------

    def _review_directive(self, directive: FrameDirective,
                          ctx: SceneContext, intensity: SceneIntensity) -> bool:
        """Review the directive for quality. Returns True if acceptable."""
        # Check for valid ranges
        if not (15.0 <= directive.field_of_view <= 120.0):
            return False
        if not (0.0 <= directive.depth_of_field <= 1.0):
            return False
        if not (0.0 <= directive.shake_intensity <= 1.0):
            return False
        if directive.camera_distance < 0:
            return False
        # Cutscenes should not have shake
        if ctx.is_cutscene and directive.shake_intensity > 0.1:
            directive.shake_intensity = 0.0
        # Dialogue should use moderate DOF
        if ctx.is_dialogue and directive.depth_of_field < 0.3:
            directive.depth_of_field = 0.5
        return True

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single frame architect cycle.

        Phases: ANALYZE -> COMPOSE -> DIRECT -> TRANSITION -> REVIEW
        """
        start_time = time.time()
        with self._lock:
            self._active = True
            phase = FramePhase.ANALYZE

            # Phase 1: ANALYZE
            ctx = self._current_context
            intensity = self._calculate_intensity(ctx)
            self._previous_intensity = self._current_intensity
            self._current_intensity = intensity

            # Phase 2: COMPOSE
            phase = FramePhase.COMPOSE
            directive = self._compose_directive(ctx, intensity)

            # Phase 3: DIRECT
            phase = FramePhase.DIRECT
            self._manage_transition(directive, self._current_directive)

            # Phase 4: TRANSITION
            phase = FramePhase.TRANSITION

            # Phase 5: REVIEW
            phase = FramePhase.REVIEW
            accepted = self._review_directive(directive, ctx, intensity)

            if accepted:
                self._current_directive = directive
                self._directive_history.append(directive)
                self._stats.total_directives_emitted += 1

            # Update stats
            self._cycle_count += 1
            self._stats.total_cycles = self._cycle_count
            self._stats.avg_intensity = (
                (self._stats.avg_intensity * (self._cycle_count - 1) + intensity.value)
                / self._cycle_count
            )
            self._stats.most_used_shot = max(self._shot_usage, key=self._shot_usage.get) if self._shot_usage else ""
            self._stats.most_used_lighting = max(self._lighting_usage, key=self._lighting_usage.get) if self._lighting_usage else ""
            self._stats.active = True
            self._last_cycle_at = time.time()
            self._stats.last_cycle_time_ms = (time.time() - start_time) * 1000

            return {
                "phase": phase.value,
                "intensity": intensity.name.lower(),
                "intensity_score": self._intensity_score(ctx),
                "directive": self._directive_to_dict(directive) if accepted else None,
                "accepted": accepted,
                "cycle": self._cycle_count,
            }

    def _intensity_score(self, ctx: SceneContext) -> float:
        """Return the raw intensity score (0.0-1.0)."""
        score = 0.0
        score += ctx.action_intensity * 0.35
        score += ctx.narrative_tension * 0.25
        score += min(ctx.enemy_count_nearby / 5.0, 1.0) * 0.20
        score += (1.0 - ctx.player_health) * 0.15 if ctx.player_health_trend == "falling" else 0.0
        score += 0.20 if ctx.is_boss_fight else 0.0
        return round(min(score, 1.0), 3)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the frame architect."""
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "current_intensity": self._current_intensity.name.lower(),
                "intensity_score": self._intensity_score(self._current_context),
                "current_context": self._context_to_dict(self._current_context),
                "current_directive": self._directive_to_dict(self._current_directive) if self._current_directive else None,
                "stats": {
                    "total_cycles": self._stats.total_cycles,
                    "total_directives_emitted": self._stats.total_directives_emitted,
                    "total_transitions": self._stats.total_transitions,
                    "avg_intensity": round(self._stats.avg_intensity, 3),
                    "most_used_shot": self._stats.most_used_shot,
                    "most_used_lighting": self._stats.most_used_lighting,
                    "last_cycle_time_ms": round(self._stats.last_cycle_time_ms, 2),
                    "active": self._stats.active,
                },
            }

    def get_directives(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent frame directives."""
        with self._lock:
            history = list(self._directive_history)
            if limit > 0:
                history = history[-limit:]
            return [self._directive_to_dict(d) for d in reversed(history)]

    def get_current_directive(self) -> Optional[Dict[str, Any]]:
        """Get the current active frame directive."""
        with self._lock:
            return self._directive_to_dict(self._current_directive) if self._current_directive else None

    def get_shot_distribution(self) -> Dict[str, Any]:
        """Get the distribution of shot types used."""
        with self._lock:
            total = sum(self._shot_usage.values()) or 1
            return {
                "shot_usage": dict(self._shot_usage),
                "lighting_usage": dict(self._lighting_usage),
                "shot_percentages": {k: round(v / total * 100, 1) for k, v in self._shot_usage.items()},
            }

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles with simulated game state changes."""
        with self._lock:
            emotions = ["neutral", "tense", "joyful", "sad", "fearful"]
            environments = ["outdoor", "indoor", "underground", "sky"]
            times = ["dawn", "day", "dusk", "night"]
            directives_emitted = 0

            for i in range(cycles):
                # Simulate varying game state
                self.update_context(
                    player_pos=[random.uniform(-50, 50), 0, random.uniform(-50, 50)],
                    player_velocity=random.uniform(0, 20),
                    player_health=random.uniform(0.2, 1.0),
                    player_health_trend=random.choice(["rising", "falling", "stable"]),
                    action_intensity=random.uniform(0, 1),
                    enemy_count=random.randint(0, 8),
                    narrative_tension=random.uniform(0, 1),
                    emotional_context=random.choice(emotions),
                    environment_type=random.choice(environments),
                    time_of_day=random.choice(times),
                    is_cutscene=(i % 7 == 0),
                    is_boss_fight=(i % 5 == 0),
                    is_dialogue=(i % 6 == 0),
                )
                result = self.run_cycle()
                if result.get("accepted"):
                    directives_emitted += 1

            return {
                "cycles_run": cycles,
                "directives_emitted": directives_emitted,
                "final_intensity": self._current_intensity.name.lower(),
                "final_intensity_score": self._intensity_score(self._current_context),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the frame architect to initial state."""
        with self._lock:
            self._stats = FrameArchitectStats()
            self._directive_history.clear()
            self._current_directive = None
            self._current_context = SceneContext()
            self._current_intensity = SceneIntensity.CALM
            self._previous_intensity = SceneIntensity.CALM
            self._cycle_count = 0
            self._last_cycle_at = 0.0
            self._active = False
            self._shot_usage.clear()
            self._lighting_usage.clear()
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _context_to_dict(self, ctx: SceneContext) -> Dict[str, Any]:
        return {
            "player_position": list(ctx.player_position),
            "player_velocity": round(ctx.player_velocity, 2),
            "player_health": round(ctx.player_health, 3),
            "player_health_trend": ctx.player_health_trend,
            "action_intensity": round(ctx.action_intensity, 3),
            "enemy_count_nearby": ctx.enemy_count_nearby,
            "narrative_tension": round(ctx.narrative_tension, 3),
            "emotional_context": ctx.emotional_context,
            "environment_type": ctx.environment_type,
            "time_of_day": ctx.time_of_day,
            "is_cutscene": ctx.is_cutscene,
            "is_boss_fight": ctx.is_boss_fight,
            "is_dialogue": ctx.is_dialogue,
        }

    def _directive_to_dict(self, d: FrameDirective) -> Dict[str, Any]:
        return {
            "directive_id": d.directive_id,
            "shot_type": d.shot_type.value,
            "camera_angle": d.camera_angle.value,
            "lighting_mood": d.lighting_mood.value,
            "transition": d.transition.value,
            "focal_point": list(d.focal_point),
            "depth_of_field": round(d.depth_of_field, 3),
            "field_of_view": round(d.field_of_view, 1),
            "camera_distance": round(d.camera_distance, 2),
            "camera_height": round(d.camera_height, 2),
            "shake_intensity": round(d.shake_intensity, 3),
            "movement_speed": round(d.movement_speed, 3),
            "duration_hint": round(d.duration_hint, 2),
            "rationale": d.rationale,
            "timestamp": d.timestamp,
        }
