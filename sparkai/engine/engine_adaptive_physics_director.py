"""
SparkLabs Engine - Adaptive Physics Director

An AI director specialized in real-time physics parameter tuning.
Monitors player behavior signals (movement, deaths, jumps, wall-touches)
and dynamically adjusts physics parameters to keep the player in the
flow channel - the zone where challenge matches skill.

Original SparkLabs design:
  1. Flow Channel Model - Player skill is estimated from behavior
     signals. The director targets a difficulty slightly above the
     estimated skill, producing the "flow" state described by
     Csikszentmihalyi: neither anxiety (too hard) nor boredom (too easy).
  2. Physics Parameter Surface - Exposes tunable parameters with
     safe bounds: gravity, friction, restitution, wall_slide_speed,
     jump_strength, move_speed_max, air_control, coyote_time.
  3. Signal Aggregation - Player behavior signals are aggregated
     over a sliding window (last N ticks) to smooth noise:
       - death_rate: deaths per minute
       - jump_frequency: jumps per minute
       - wall_touch_rate: wall contacts per minute
       - avg_speed: average horizontal velocity
       - stall_ratio: fraction of ticks with near-zero velocity
  4. PID-style Adjustment - Each parameter has its own controller
     that computes a correction based on the gap between current
     skill estimate and target difficulty. Corrections are bounded
     to prevent oscillation.
  5. Physics Profiles - Successful parameter sets are persisted as
     "physics profiles" keyed by genre + flow state. Profiles enable
     fast convergence on subsequent sessions.
  6. Wall-Slide Intelligence - The director recognizes when a player
     is in a wall-slide context (parkour/platformer) and adjusts
     wall_slide_speed and wall_jump_kickback separately from the
     main physics surface.

This director complements the CognitiveGameEngine's TUNE_PHYSICS
action by providing continuous, fine-grained parameter control
between cognitive ticks. It runs at a higher frequency than the
cognitive tick (e.g., every 10 ticks) for smooth adaptation.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class FlowState(Enum):
    """Player's current flow state."""
    BOREDOM = "boredom"      # skill > challenge
    FLOW = "flow"            # skill ~= challenge
    ANXIETY = "anxiety"      # skill < challenge
    UNKNOWN = "unknown"


class PhysicsProfileGenre(Enum):
    """Genre tags for persisted physics profiles."""
    PLATFORMER = "platformer"
    PARKOUR = "parkour"
    SHOOTER = "shooter"
    TOP_DOWN = "top_down"
    GENERIC = "generic"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class PhysicsParameters:
    """
    Tunable physics parameters with safe bounds. Each parameter has a
    min, max, and current value. Bounds are enforced by the director.
    """
    gravity: float = 0.55                # 0.0 to 2.0
    friction: float = 0.85               # 0.5 to 0.99 (multiplicative)
    restitution: float = 0.2             # 0.0 to 0.8 (bounciness)
    wall_slide_speed: float = 2.0        # 0.0 to 6.0
    wall_jump_kickback: float = 6.0      # 0.0 to 12.0
    jump_strength: float = 11.0          # 4.0 to 18.0
    move_speed_max: float = 4.2          # 1.0 to 10.0
    air_control: float = 0.6             # 0.0 to 1.0
    coyote_time: float = 6.0             # 0 to 20 ticks
    enemy_speed_scale: float = 1.0       # 0.3 to 2.5
    difficulty_multiplier: float = 1.0   # 0.5 to 1.5

    # Bounds table (name -> (min, max))
    BOUNDS: Dict[str, Tuple[float, float]] = field(
        default_factory=lambda: {
            "gravity": (0.0, 2.0),
            "friction": (0.5, 0.99),
            "restitution": (0.0, 0.8),
            "wall_slide_speed": (0.0, 6.0),
            "wall_jump_kickback": (0.0, 12.0),
            "jump_strength": (4.0, 18.0),
            "move_speed_max": (1.0, 10.0),
            "air_control": (0.0, 1.0),
            "coyote_time": (0.0, 20.0),
            "enemy_speed_scale": (0.3, 2.5),
            "difficulty_multiplier": (0.5, 1.5),
        },
        repr=False,
    )

    def get(self, name: str) -> float:
        return getattr(self, name)

    def set(self, name: str, value: float) -> None:
        bounds = self.BOUNDS.get(name)
        if bounds is None:
            return
        lo, hi = bounds
        clamped = max(lo, min(hi, value))
        setattr(self, name, clamped)

    def to_dict(self) -> Dict[str, float]:
        return {
            "gravity": self.gravity,
            "friction": self.friction,
            "restitution": self.restitution,
            "wall_slide_speed": self.wall_slide_speed,
            "wall_jump_kickback": self.wall_jump_kickback,
            "jump_strength": self.jump_strength,
            "move_speed_max": self.move_speed_max,
            "air_control": self.air_control,
            "coyote_time": self.coyote_time,
            "enemy_speed_scale": self.enemy_speed_scale,
            "difficulty_multiplier": self.difficulty_multiplier,
        }


@dataclass
class PlayerSignals:
    """Aggregated player behavior signals over a sliding window."""
    death_rate: float = 0.0          # deaths per minute
    jump_frequency: float = 0.0      # jumps per minute
    wall_touch_rate: float = 0.0     # wall contacts per minute
    avg_speed: float = 0.0           # average horizontal velocity
    stall_ratio: float = 0.0         # fraction of ticks with near-zero velocity
    collectible_rate: float = 0.0    # collectibles per minute
    progress_rate: float = 0.0       # level progress per minute

    def to_dict(self) -> Dict[str, float]:
        return {
            "death_rate": self.death_rate,
            "jump_frequency": self.jump_frequency,
            "wall_touch_rate": self.wall_touch_rate,
            "avg_speed": self.avg_speed,
            "stall_ratio": self.stall_ratio,
            "collectible_rate": self.collectible_rate,
            "progress_rate": self.progress_rate,
        }


@dataclass
class FlowEstimate:
    """Estimated player skill and target difficulty."""
    skill_estimate: float = 0.5      # 0.0 (novice) to 1.0 (expert)
    target_difficulty: float = 0.5   # 0.0 (relaxed) to 1.0 (intense)
    flow_state: FlowState = FlowState.UNKNOWN
    confidence: float = 0.3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_estimate": self.skill_estimate,
            "target_difficulty": self.target_difficulty,
            "flow_state": self.flow_state.value,
            "confidence": self.confidence,
        }


@dataclass
class PhysicsProfile:
    """A persisted physics parameter set keyed by genre + flow state."""
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    genre: PhysicsProfileGenre = PhysicsProfileGenre.GENERIC
    flow_state: FlowState = FlowState.FLOW
    parameters: PhysicsParameters = field(default_factory=PhysicsParameters)
    success_score: float = 0.5        # 0.0 to 1.0
    sample_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)


# =============================================================================
# Signal Aggregator
# =============================================================================

class SignalAggregator:
    """
    Aggregates raw player behavior events over a sliding window to
    produce smoothed PlayerSignals.
    """

    def __init__(self, window_ticks: int = 600) -> None:
        # 600 ticks = 10 seconds at 60fps
        self._lock = threading.RLock()
        self._window_ticks = window_ticks
        self._deaths: Deque[int] = deque(maxlen=window_ticks)
        self._jumps: Deque[int] = deque(maxlen=window_ticks)
        self._wall_touches: Deque[int] = deque(maxlen=window_ticks)
        self._speeds: Deque[float] = deque(maxlen=window_ticks)
        self._stalls: Deque[bool] = deque(maxlen=window_ticks)
        self._collectibles: Deque[int] = deque(maxlen=window_ticks)
        self._progress: Deque[float] = deque(maxlen=window_ticks)
        self._current_tick: int = 0

    def record_tick(
        self,
        tick: int,
        died: bool = False,
        jumped: bool = False,
        wall_touch: bool = False,
        speed: float = 0.0,
        collected: bool = False,
        progress_delta: float = 0.0,
    ) -> None:
        with self._lock:
            self._current_tick = tick
            self._deaths.append(1 if died else 0)
            self._jumps.append(1 if jumped else 0)
            self._wall_touches.append(1 if wall_touch else 0)
            self._speeds.append(speed)
            self._stalls.append(abs(speed) < 0.5)
            self._collectibles.append(1 if collected else 0)
            self._progress.append(progress_delta)

    def compute_signals(self) -> PlayerSignals:
        """Compute smoothed signals over the current window."""
        with self._lock:
            if not self._speeds:
                return PlayerSignals()

            # Convert tick counts to per-minute rates (assuming 60 fps)
            # If window has 600 ticks, that's 10 seconds, so per-minute = sum * 6
            ticks_in_window = len(self._speeds)
            per_minute_multiplier = 60.0 / max(1, ticks_in_window / 60.0)

            death_rate = sum(self._deaths) * per_minute_multiplier
            jump_frequency = sum(self._jumps) * per_minute_multiplier
            wall_touch_rate = sum(self._wall_touches) * per_minute_multiplier
            collectible_rate = sum(self._collectibles) * per_minute_multiplier
            progress_rate = sum(self._progress) * per_minute_multiplier

            avg_speed = sum(self._speeds) / len(self._speeds) if self._speeds else 0.0
            stall_count = sum(1 for s in self._stalls if s)
            stall_ratio = stall_count / len(self._stalls) if self._stalls else 0.0

            return PlayerSignals(
                death_rate=death_rate,
                jump_frequency=jump_frequency,
                wall_touch_rate=wall_touch_rate,
                avg_speed=avg_speed,
                stall_ratio=stall_ratio,
                collectible_rate=collectible_rate,
                progress_rate=progress_rate,
            )

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "window_ticks": self._window_ticks,
                "current_tick": self._current_tick,
                "samples": len(self._speeds),
            }


# =============================================================================
# Flow Estimator
# =============================================================================

class FlowEstimator:
    """
    Estimates player skill and target difficulty from aggregated
    behavior signals. Uses a weighted heuristic model.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._last_estimate: FlowEstimate = FlowEstimate()
        self._estimate_count: int = 0

    def estimate(self, signals: PlayerSignals) -> FlowEstimate:
        """
        Estimate player skill from signals. Higher collectible rate +
        lower death rate + higher progress rate = higher skill.
        """
        with self._lock:
            self._estimate_count += 1

        # Normalize signals to 0..1 skill contributions
        # Death rate: 0 deaths/min = 1.0, 6+ deaths/min = 0.0
        death_skill = max(0.0, 1.0 - signals.death_rate / 6.0)
        # Collectible rate: 0/min = 0.3, 6+/min = 1.0
        coll_skill = min(1.0, 0.3 + signals.collectible_rate / 8.0)
        # Progress rate: 0/min = 0.3, 60+/min = 1.0
        prog_skill = min(1.0, 0.3 + signals.progress_rate / 60.0)
        # Stall ratio: 0 stalls = 1.0, 50% stalls = 0.0
        stall_skill = max(0.0, 1.0 - signals.stall_ratio * 2.0)
        # Avg speed: 0 = 0.3, 4+ = 1.0
        speed_skill = min(1.0, 0.3 + signals.avg_speed / 6.0)

        # Weighted average
        skill = (
            0.30 * death_skill +
            0.20 * coll_skill +
            0.20 * prog_skill +
            0.15 * stall_skill +
            0.15 * speed_skill
        )
        skill = max(0.0, min(1.0, skill))

        # Target difficulty: slightly above skill (flow zone)
        target = max(0.1, min(1.0, skill + 0.15))

        # Determine flow state
        gap = target - skill
        if abs(gap) < 0.15:
            flow_state = FlowState.FLOW
        elif gap > 0.3:
            flow_state = FlowState.ANXIETY
        elif gap < -0.2:
            flow_state = FlowState.BOREDOM
        else:
            flow_state = FlowState.FLOW

        # Confidence based on sample size and signal variance
        confidence = min(1.0, 0.3 + 0.7 * min(1.0, self._estimate_count / 30.0))

        estimate = FlowEstimate(
            skill_estimate=skill,
            target_difficulty=target,
            flow_state=flow_state,
            confidence=confidence,
        )

        with self._lock:
            self._last_estimate = estimate

        return estimate

    def last_estimate(self) -> FlowEstimate:
        with self._lock:
            return self._last_estimate

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "estimate_count": self._estimate_count,
                "last_estimate": self._last_estimate.to_dict(),
            }


# =============================================================================
# Physics Controller (PID-style)
# =============================================================================

class PhysicsController:
    """
    A PID-style controller for a single physics parameter. Computes
    a correction based on the gap between current difficulty and target.
    """

    def __init__(self, parameter_name: str, kp: float = 0.05,
                 ki: float = 0.01, kd: float = 0.02,
                 max_correction: float = 0.15) -> None:
        self.parameter_name = parameter_name
        self.kp = kp  # proportional
        self.ki = ki  # integral
        self.kd = kd  # derivative
        self.max_correction = max_correction
        self._integral = 0.0
        self._last_error = 0.0
        self._lock = threading.RLock()

    def compute_correction(
        self, current_difficulty: float, target_difficulty: float,
    ) -> float:
        """Compute a normalized correction in [-1, 1]."""
        with self._lock:
            error = target_difficulty - current_difficulty
            self._integral += error
            self._integral = max(-10.0, min(10.0, self._integral))  # anti-windup
            derivative = error - self._last_error
            self._last_error = error

            correction = (
                self.kp * error +
                self.ki * self._integral +
                self.kd * derivative
            )
            return max(-self.max_correction, min(self.max_correction, correction))

    def reset(self) -> None:
        with self._lock:
            self._integral = 0.0
            self._last_error = 0.0


# =============================================================================
# Adaptive Physics Director
# =============================================================================

class AdaptivePhysicsDirector:
    """
    The adaptive physics director. Monitors player behavior, estimates
    skill, and tunes physics parameters to maintain flow. Persists
    successful parameter sets as physics profiles.

    Thread-safe singleton: use get_instance() to access.
    """

    _instance: Optional["AdaptivePhysicsDirector"] = None
    _instance_lock = threading.Lock()

    # Run adaptation every N ticks (default: every 10 ticks)
    _ADAPTATION_INTERVAL = 10

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._aggregator = SignalAggregator(window_ticks=600)
        self._estimator = FlowEstimator()

        # Per-parameter controllers
        self._controllers: Dict[str, PhysicsController] = {
            "gravity": PhysicsController("gravity", kp=0.08, max_correction=0.10),
            "friction": PhysicsController("friction", kp=0.03, max_correction=0.05),
            "jump_strength": PhysicsController("jump_strength", kp=0.06, max_correction=0.10),
            "move_speed_max": PhysicsController("move_speed_max", kp=0.05, max_correction=0.08),
            "enemy_speed_scale": PhysicsController("enemy_speed_scale", kp=0.08, max_correction=0.12),
            "difficulty_multiplier": PhysicsController("difficulty_multiplier", kp=0.06, max_correction=0.08),
            "wall_slide_speed": PhysicsController("wall_slide_speed", kp=0.04, max_correction=0.08),
            "wall_jump_kickback": PhysicsController("wall_jump_kickback", kp=0.04, max_correction=0.08),
        }

        # Current parameters
        self._parameters = PhysicsParameters()
        self._current_genre: PhysicsProfileGenre = PhysicsProfileGenre.GENERIC

        # Persisted profiles: (genre, flow_state) -> profile
        self._profiles: Dict[Tuple[PhysicsProfileGenre, FlowState], PhysicsProfile] = {}

        # Telemetry
        self._adaptation_count: int = 0
        self._last_adaptation_tick: int = 0
        self._last_signals: PlayerSignals = PlayerSignals()
        self._last_estimate: FlowEstimate = FlowEstimate()
        self._adjustments_history: Deque[Dict[str, Any]] = deque(maxlen=32)
        self._total_adjustments: int = 0

    @classmethod
    def get_instance(cls) -> "AdaptivePhysicsDirector":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ---- Signal Recording ----

    def record_tick(
        self,
        tick: int,
        died: bool = False,
        jumped: bool = False,
        wall_touch: bool = False,
        speed: float = 0.0,
        collected: bool = False,
        progress_delta: float = 0.0,
    ) -> None:
        """Record raw player behavior for one tick."""
        self._aggregator.record_tick(
            tick=tick, died=died, jumped=jumped, wall_touch=wall_touch,
            speed=speed, collected=collected, progress_delta=progress_delta,
        )

    # ---- Adaptation ----

    def adapt(self, tick: int) -> Optional[Dict[str, Any]]:
        """
        Run one adaptation pass. Returns a summary of adjustments made,
        or None if no adaptation was performed this tick.
        """
        if tick % self._ADAPTATION_INTERVAL != 0:
            return None

        with self._lock:
            self._adaptation_count += 1
            self._last_adaptation_tick = tick

        # Step 1: Compute aggregated signals
        signals = self._aggregator.compute_signals()
        with self._lock:
            self._last_signals = signals

        # Step 2: Estimate flow
        estimate = self._estimator.estimate(signals)
        with self._lock:
            self._last_estimate = estimate

        # Step 3: Load profile if available
        profile_key = (self._current_genre, estimate.flow_state)
        with self._lock:
            profile = self._profiles.get(profile_key)
            if profile is not None:
                # Merge profile parameters as a starting point
                self._parameters = PhysicsParameters(**{
                    k: v for k, v in profile.parameters.to_dict().items()
                })
                profile.last_used_at = time.time()
                profile.sample_count += 1

        # Step 4: Compute corrections
        current_difficulty = self._parameters.difficulty_multiplier
        target_difficulty = estimate.target_difficulty
        adjustments: Dict[str, float] = {}

        with self._lock:
            for name, controller in self._controllers.items():
                correction = controller.compute_correction(
                    current_difficulty, target_difficulty,
                )
                if abs(correction) < 0.001:
                    continue
                old_value = self._parameters.get(name)
                # Apply correction scaled by parameter's typical magnitude
                # Direction: if target > current, increase difficulty-related params
                if name in ("gravity", "enemy_speed_scale", "difficulty_multiplier"):
                    new_value = old_value * (1.0 + correction)
                elif name in ("friction",):
                    # Higher friction = easier control = lower difficulty
                    new_value = old_value * (1.0 - correction * 0.5)
                elif name in ("jump_strength", "move_speed_max"):
                    # Higher jump/speed = easier = lower difficulty
                    new_value = old_value * (1.0 - correction * 0.3)
                elif name in ("wall_slide_speed", "wall_jump_kickback"):
                    # Higher wall-slide/kickback = more capable = higher difficulty
                    new_value = old_value * (1.0 + correction * 0.5)
                else:
                    new_value = old_value * (1.0 + correction)

                self._parameters.set(name, new_value)
                adjustments[name] = new_value - old_value
                self._total_adjustments += 1

        # Step 5: Persist successful profiles
        if estimate.flow_state == FlowState.FLOW and estimate.confidence >= 0.6:
            self._persist_profile(self._current_genre, estimate.flow_state)

        # Step 6: Record adjustment history
        summary = {
            "tick": tick,
            "flow_state": estimate.flow_state.value,
            "skill_estimate": estimate.skill_estimate,
            "target_difficulty": estimate.target_difficulty,
            "adjustments": dict(adjustments),
            "adjustment_count": len(adjustments),
            "timestamp": time.time(),
        }
        with self._lock:
            self._adjustments_history.append(summary)

        return summary

    def _persist_profile(
        self, genre: PhysicsProfileGenre, flow_state: FlowState,
    ) -> None:
        """Persist the current parameters as a profile."""
        key = (genre, flow_state)
        with self._lock:
            existing = self._profiles.get(key)
            if existing is None:
                profile = PhysicsProfile(
                    genre=genre,
                    flow_state=flow_state,
                    parameters=PhysicsParameters(**self._parameters.to_dict()),
                    success_score=0.5,
                    sample_count=1,
                )
                self._profiles[key] = profile
            else:
                # Blend parameters with EMA
                current = self._parameters.to_dict()
                existing_dict = existing.parameters.to_dict()
                alpha = 0.2
                for k in current:
                    existing_dict[k] = (1 - alpha) * existing_dict[k] + alpha * current[k]
                existing.parameters = PhysicsParameters(**existing_dict)
                existing.success_score = min(1.0, existing.success_score + 0.05)
                existing.sample_count += 1

    # ---- Genre Management ----

    def set_genre(self, genre: str) -> None:
        """Set the current genre for profile matching."""
        try:
            self._current_genre = PhysicsProfileGenre(genre)
        except ValueError:
            self._current_genre = PhysicsProfileGenre.GENERIC

        # Load existing profile for FLOW state if available
        key = (self._current_genre, FlowState.FLOW)
        with self._lock:
            profile = self._profiles.get(key)
            if profile is not None:
                self._parameters = PhysicsParameters(**{
                    k: v for k, v in profile.parameters.to_dict().items()
                })

    # ---- Status & Telemetry ----

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "current_genre": self._current_genre.value,
                "parameters": self._parameters.to_dict(),
                "signals": self._last_signals.to_dict(),
                "flow_estimate": self._last_estimate.to_dict(),
                "aggregator": self._aggregator.stats(),
                "estimator": self._estimator.stats(),
                "adaptation_count": self._adaptation_count,
                "last_adaptation_tick": self._last_adaptation_tick,
                "total_adjustments": self._total_adjustments,
                "profiles_count": len(self._profiles),
                "last_adjustment": (
                    self._adjustments_history[-1] if self._adjustments_history else None
                ),
            }

    def history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._adjustments_history)[-limit:]

    def list_profiles(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "profile_id": p.profile_id,
                    "genre": p.genre.value,
                    "flow_state": p.flow_state.value,
                    "parameters": p.parameters.to_dict(),
                    "success_score": p.success_score,
                    "sample_count": p.sample_count,
                    "created_at": p.created_at,
                    "last_used_at": p.last_used_at,
                } for p in self._profiles.values()
            ]

    def reset(self) -> None:
        with self._lock:
            self._parameters = PhysicsParameters()
            self._current_genre = PhysicsProfileGenre.GENERIC
            for controller in self._controllers.values():
                controller.reset()
            self._adaptation_count = 0
            self._last_adaptation_tick = 0
            self._total_adjustments = 0
            self._adjustments_history.clear()
            self._last_signals = PlayerSignals()
            self._last_estimate = FlowEstimate()
        # Reset aggregator and estimator state
        self._aggregator = SignalAggregator(window_ticks=600)
        self._estimator = FlowEstimator()

    def reset_profiles(self) -> None:
        with self._lock:
            self._profiles.clear()


# =============================================================================
# Module-Level Convenience
# =============================================================================

def get_physics_director() -> AdaptivePhysicsDirector:
    """Get the singleton AdaptivePhysicsDirector instance."""
    return AdaptivePhysicsDirector.get_instance()


def adapt_physics(tick: int) -> Optional[Dict[str, Any]]:
    """Run one physics adaptation pass on the singleton director."""
    return get_physics_director().adapt(tick)
