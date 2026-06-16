"""
SparkLabs Agent - Dynamic Difficulty Adjustment

Real-time difficulty adaptation system that monitors player performance
and intelligently adjusts game difficulty parameters to maintain optimal
challenge and engagement within the AI-native game engine.

Architecture:
  DynamicDifficultyEngine (singleton)
    |-- DifficultyProfile (per-player difficulty state and configuration)
    |-- PerformanceMetrics (raw gameplay measurement data points)
    |-- DifficultyAdjustment (individual parameter change records)
    |-- PlayerState assessment (struggling -> bored spectrum)
    |-- Strategy-driven adjustment (gradual/aggressive/conservative/adaptive/predictive)

Adjustment Strategies:
  - GRADUAL: small incremental changes for subtle tuning
  - AGGRESSIVE: large swings to rapidly find optimal difficulty
  - CONSERVATIVE: prefers lower difficulty, slow to increase
  - ADAPTIVE: responds to rate-of-change in player state
  - PREDICTIVE: anticipates needs from historical performance patterns
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------


class DifficultyParameter(Enum):
    """Tunable game difficulty dimensions for dynamic adjustment."""
    ENEMY_HEALTH = "enemy_health"
    ENEMY_DAMAGE = "enemy_damage"
    ENEMY_SPEED = "enemy_speed"
    ENEMY_COUNT = "enemy_count"
    ENEMY_AI = "enemy_ai"
    SPAWN_RATE = "spawn_rate"
    RESOURCE_DROP = "resource_drop"
    TIME_LIMIT = "time_limit"
    CHECKPOINT_FREQUENCY = "checkpoint_frequency"
    PUZZLE_COMPLEXITY = "puzzle_complexity"
    BOSS_PHASES = "boss_phases"
    ITEM_AVAILABILITY = "item_availability"


class AdjustmentStrategy(Enum):
    """Approach used when modifying difficulty parameters."""
    GRADUAL = "gradual"
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"
    ADAPTIVE = "adaptive"
    PREDICTIVE = "predictive"


class PlayerState(Enum):
    """Player performance classification for difficulty targeting."""
    STRUGGLING = "struggling"
    CHALLENGED = "challenged"
    COMFORTABLE = "comfortable"
    DOMINATING = "dominating"
    BORED = "bored"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class DifficultyProfile:
    """Per-player difficulty configuration and historical state."""
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    player_id: str = ""
    current_state: PlayerState = PlayerState.CHALLENGED
    baseline_difficulty: float = 0.5
    current_difficulty: float = 0.5
    adaptation_rate: float = 0.1
    strategy: AdjustmentStrategy = AdjustmentStrategy.GRADUAL
    history: List[DifficultyAdjustment] = field(default_factory=list)
    parameters: Dict[DifficultyParameter, Dict[str, float]] = field(default_factory=dict)
    min_difficulty: float = 0.1
    max_difficulty: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "player_id": self.player_id,
            "current_state": self.current_state.value,
            "baseline_difficulty": self.baseline_difficulty,
            "current_difficulty": round(self.current_difficulty, 4),
            "adaptation_rate": self.adaptation_rate,
            "strategy": self.strategy.value,
            "parameter_count": len(self.parameters),
            "adjustment_count": len(self.history),
            "min_difficulty": self.min_difficulty,
            "max_difficulty": self.max_difficulty,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class DifficultyAdjustment:
    """Record of a single difficulty parameter change."""
    adjustment_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    profile_id: str = ""
    parameter: DifficultyParameter = DifficultyParameter.ENEMY_HEALTH
    old_value: float = 1.0
    new_value: float = 1.0
    reason: str = ""
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)
    player_state_before: PlayerState = PlayerState.CHALLENGED
    player_state_after: PlayerState = PlayerState.CHALLENGED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adjustment_id": self.adjustment_id,
            "profile_id": self.profile_id,
            "parameter": self.parameter.value,
            "old_value": round(self.old_value, 4),
            "new_value": round(self.new_value, 4),
            "reason": self.reason,
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp,
            "player_state_before": self.player_state_before.value,
            "player_state_after": self.player_state_after.value,
        }


@dataclass
class PerformanceMetrics:
    """Raw gameplay performance measurements for a player at a point in time."""
    metrics_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    player_id: str = ""
    deaths_per_minute: float = 0.0
    kill_efficiency: float = 0.5
    completion_speed: float = 0.5
    accuracy: float = 0.5
    resource_efficiency: float = 0.5
    damage_taken: float = 0.0
    damage_dealt: float = 0.0
    combo_rate: float = 0.0
    exploration_rate: float = 0.5
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics_id": self.metrics_id,
            "player_id": self.player_id,
            "deaths_per_minute": self.deaths_per_minute,
            "kill_efficiency": round(self.kill_efficiency, 3),
            "completion_speed": round(self.completion_speed, 3),
            "accuracy": round(self.accuracy, 3),
            "resource_efficiency": round(self.resource_efficiency, 3),
            "damage_taken": round(self.damage_taken, 1),
            "damage_dealt": round(self.damage_dealt, 1),
            "combo_rate": round(self.combo_rate, 3),
            "exploration_rate": round(self.exploration_rate, 3),
            "timestamp": self.timestamp,
        }


# ------------------------------------------------------------------
# DynamicDifficultyEngine Singleton
# ------------------------------------------------------------------


class DynamicDifficultyEngine:
    """
    Singleton system for real-time dynamic difficulty adjustment.

    Monitors player performance metrics, classifies player state on the
    struggling-to-bored spectrum, and applies strategy-driven parameter
    adjustments to keep every player in the optimal challenge zone.
    """

    _instance: Optional[DynamicDifficultyEngine] = None
    _lock = threading.RLock()

    # Default parameter ranges (min, max, initial)
    _DEFAULT_PARAMETER_RANGES: Dict[DifficultyParameter, Tuple[float, float, float]] = {
        DifficultyParameter.ENEMY_HEALTH: (0.3, 1.8, 1.0),
        DifficultyParameter.ENEMY_DAMAGE: (0.2, 1.7, 1.0),
        DifficultyParameter.ENEMY_SPEED: (0.5, 1.6, 1.0),
        DifficultyParameter.ENEMY_COUNT: (0.3, 2.0, 1.0),
        DifficultyParameter.ENEMY_AI: (0.2, 1.5, 0.8),
        DifficultyParameter.SPAWN_RATE: (0.2, 1.8, 1.0),
        DifficultyParameter.RESOURCE_DROP: (0.3, 1.7, 1.0),
        DifficultyParameter.TIME_LIMIT: (0.5, 1.5, 1.0),
        DifficultyParameter.CHECKPOINT_FREQUENCY: (0.3, 1.8, 1.0),
        DifficultyParameter.PUZZLE_COMPLEXITY: (0.2, 1.6, 0.8),
        DifficultyParameter.BOSS_PHASES: (0.5, 1.8, 1.0),
        DifficultyParameter.ITEM_AVAILABILITY: (0.3, 1.7, 1.0),
    }

    def __new__(cls) -> DynamicDifficultyEngine:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> DynamicDifficultyEngine:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.__init__()
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        with self._lock:
            if hasattr(self, "_initialized") and self._initialized:
                return
            self._profiles: Dict[str, DifficultyProfile] = {}
            self._metrics_history: Dict[str, deque] = {}
            self._adjustments: List[DifficultyAdjustment] = []
            self._state_transition_log: deque = deque(maxlen=500)
            self._stats: Dict[str, Any] = {
                "total_profiles": 0,
                "total_metrics_received": 0,
                "total_adjustments": 0,
                "state_distribution": {s.value: 0 for s in PlayerState},
                "strategy_distribution": {s.value: 0 for s in AdjustmentStrategy},
            }
            self._initialized = True

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def create_profile(
        self,
        player_id: str,
        baseline_difficulty: float = 0.5,
        strategy: str = "gradual",
    ) -> DifficultyProfile:
        """Create a new difficulty profile for a player."""
        with self._lock:
            baseline = max(0.05, min(0.95, baseline_difficulty))
            try:
                strat = AdjustmentStrategy(strategy.lower())
            except ValueError:
                strat = AdjustmentStrategy.GRADUAL

            profile = DifficultyProfile(
                player_id=player_id,
                baseline_difficulty=baseline,
                current_difficulty=baseline,
                strategy=strat,
                current_state=PlayerState.CHALLENGED,
            )

            # Initialize default parameter values scaled to baseline
            for param, (p_min, p_max, p_default) in self._DEFAULT_PARAMETER_RANGES.items():
                scaled = p_default * baseline
                profile.parameters[param] = {
                    "min": p_min,
                    "max": p_max,
                    "current": round(min(max(scaled, p_min), p_max), 4),
                }

            profile.min_difficulty = 0.05
            profile.max_difficulty = 0.95

            self._profiles[profile.profile_id] = profile
            self._metrics_history[profile.profile_id] = deque(maxlen=100)
            self._stats["total_profiles"] += 1
            self._stats["strategy_distribution"][strat.value] += 1

            return profile

    def get_profile(self, player_id: str) -> Optional[DifficultyProfile]:
        """Retrieve the difficulty profile for a given player."""
        with self._lock:
            for profile in self._profiles.values():
                if profile.player_id == player_id:
                    return profile
            return None

    def set_parameter(
        self,
        player_id: str,
        parameter: str,
        min_val: float,
        max_val: float,
        current: float,
    ) -> Optional[DifficultyProfile]:
        """Override a specific difficulty parameter range for a player."""
        with self._lock:
            profile = self.get_profile(player_id)
            if profile is None:
                return None

            try:
                param = DifficultyParameter(parameter.lower())
            except ValueError:
                return None

            clamped_min = max(0.01, min_val)
            clamped_max = min(10.0, max(clamped_min + 0.01, max_val))
            clamped_current = max(clamped_min, min(clamped_max, current))

            profile.parameters[param] = {
                "min": round(clamped_min, 4),
                "max": round(clamped_max, 4),
                "current": round(clamped_current, 4),
            }
            profile.updated_at = time.time()

            return profile

    def set_strategy(self, player_id: str, strategy: str) -> bool:
        """Change the adjustment strategy for a player's profile."""
        with self._lock:
            profile = self.get_profile(player_id)
            if profile is None:
                return False
            try:
                new_strategy = AdjustmentStrategy(strategy.lower())
            except ValueError:
                return False

            old_strategy = profile.strategy
            profile.strategy = new_strategy
            profile.updated_at = time.time()

            self._stats["strategy_distribution"][old_strategy.value] -= 1
            self._stats["strategy_distribution"][new_strategy.value] += 1

            return True

    # ------------------------------------------------------------------
    # Metrics Collection
    # ------------------------------------------------------------------

    def update_metrics(
        self,
        player_id: str,
        metrics_data: Dict[str, Any],
    ) -> Optional[PerformanceMetrics]:
        """Record a new set of performance metrics for a player."""
        with self._lock:
            profile = self.get_profile(player_id)
            if profile is None:
                return None

            metrics = PerformanceMetrics(
                player_id=player_id,
                deaths_per_minute=float(metrics_data.get("deaths_per_minute", 0.0)),
                kill_efficiency=float(metrics_data.get("kill_efficiency", 0.5)),
                completion_speed=float(metrics_data.get("completion_speed", 0.5)),
                accuracy=float(metrics_data.get("accuracy", 0.5)),
                resource_efficiency=float(metrics_data.get("resource_efficiency", 0.5)),
                damage_taken=float(metrics_data.get("damage_taken", 0.0)),
                damage_dealt=float(metrics_data.get("damage_dealt", 0.0)),
                combo_rate=float(metrics_data.get("combo_rate", 0.0)),
                exploration_rate=float(metrics_data.get("exploration_rate", 0.5)),
            )

            self._metrics_history[profile.profile_id].append(metrics)
            self._stats["total_metrics_received"] += 1

            return metrics

    # ------------------------------------------------------------------
    # Player State Assessment
    # ------------------------------------------------------------------

    def assess_player_state(self, player_id: str) -> Optional[PlayerState]:
        """Classify the current player state based on recent performance."""
        with self._lock:
            profile = self.get_profile(player_id)
            if profile is None:
                return None

            metrics_deque = self._metrics_history.get(profile.profile_id, deque())
            if not metrics_deque:
                return PlayerState.CHALLENGED

            # Use a weighted window of recent metrics, favoring recency
            recent_metrics = list(metrics_deque)
            window = min(10, len(recent_metrics))
            recent = recent_metrics[-window:]
            weights = [1.0 + (i * 0.1) for i in range(window)]
            weight_sum = sum(weights)

            def weighted_avg(attr: str) -> float:
                total = sum(
                    getattr(m, attr, 0.0) * w for m, w in zip(recent, weights)
                )
                return total / weight_sum if weight_sum > 0 else 0.0

            avg_deaths = weighted_avg("deaths_per_minute")
            avg_kill_eff = weighted_avg("kill_efficiency")
            avg_speed = weighted_avg("completion_speed")
            avg_accuracy = weighted_avg("accuracy")
            avg_resource_eff = weighted_avg("resource_efficiency")
            avg_damage_ratio = 0.0
            total_dmg_taken = sum(m.damage_taken for m in recent)
            total_dmg_dealt = sum(m.damage_dealt for m in recent)
            if total_dmg_dealt > 0:
                avg_damage_ratio = total_dmg_taken / total_dmg_dealt

            # Composite scoring for classification
            struggle_score = 0.0

            # High death rate contributes to struggling
            if avg_deaths > 0.5:
                struggle_score += 0.35
            elif avg_deaths > 0.2:
                struggle_score += 0.2
            elif avg_deaths > 0.1:
                struggle_score += 0.08

            # Low kill efficiency contributes to struggling
            if avg_kill_eff < 0.3:
                struggle_score += 0.25
            elif avg_kill_eff < 0.5:
                struggle_score += 0.12

            # Slow completion contributes to struggling
            if avg_speed < 0.3:
                struggle_score += 0.2
            elif avg_speed < 0.5:
                struggle_score += 0.08

            # Low accuracy contributes to struggling
            if avg_accuracy < 0.4:
                struggle_score += 0.1

            # Poor damage ratio contributes to struggling
            if avg_damage_ratio > 1.5:
                struggle_score += 0.1

            # Boredom detection indicators
            boredom_score = 0.0
            if avg_deaths < 0.02:
                boredom_score += 0.15
            if avg_kill_eff > 0.9:
                boredom_score += 0.2
            if avg_speed > 0.9:
                boredom_score += 0.15
            if avg_accuracy > 0.9:
                boredom_score += 0.15
            if avg_resource_eff > 0.9:
                boredom_score += 0.1
            if avg_damage_ratio < 0.1 and total_dmg_dealt > 0:
                boredom_score += 0.1

            # Dominating indicators (sub-boredom but well above challenged)
            dominating_score = 0.0
            if avg_deaths < 0.05:
                dominating_score += 0.15
            if avg_kill_eff > 0.85:
                dominating_score += 0.15
            if avg_speed > 0.8:
                dominating_score += 0.1
            if avg_accuracy > 0.85:
                dominating_score += 0.1
            if avg_resource_eff > 0.8:
                dominating_score += 0.1

            # Determine state with hysteresis: prefer staying in current state
            # unless evidence strongly supports a transition
            old_state = profile.current_state

            if struggle_score >= 0.4:
                new_state = PlayerState.STRUGGLING
            elif struggle_score >= 0.2:
                new_state = PlayerState.CHALLENGED
            elif boredom_score >= 0.65:
                new_state = PlayerState.BORED
            elif dominating_score >= 0.45:
                new_state = PlayerState.DOMINATING
            elif dominating_score >= 0.25:
                new_state = PlayerState.COMFORTABLE
            elif avg_speed > 0.7 and avg_kill_eff > 0.7:
                new_state = PlayerState.COMFORTABLE
            else:
                new_state = PlayerState.CHALLENGED

            # Apply hysteresis: harder to transition upward (easier) than downward (harder)
            state_order = [
                PlayerState.STRUGGLING,
                PlayerState.CHALLENGED,
                PlayerState.COMFORTABLE,
                PlayerState.DOMINATING,
                PlayerState.BORED,
            ]
            old_idx = state_order.index(old_state)
            new_idx = state_order.index(new_state)

            # If moving to an easier state (up), require stronger evidence
            if new_idx > old_idx and new_idx - old_idx == 1:
                if new_state == PlayerState.BORED and boredom_score < 0.7:
                    new_state = PlayerState.DOMINATING
                elif new_state == PlayerState.DOMINATING and dominating_score < 0.5:
                    new_state = PlayerState.COMFORTABLE

            profile.current_state = new_state

            if new_state != old_state:
                self._state_transition_log.append({
                    "player_id": player_id,
                    "profile_id": profile.profile_id,
                    "from_state": old_state.value,
                    "to_state": new_state.value,
                    "struggle_score": round(struggle_score, 3),
                    "boredom_score": round(boredom_score, 3),
                    "timestamp": time.time(),
                })

            return new_state

    # ------------------------------------------------------------------
    # Difficulty Adjustment
    # ------------------------------------------------------------------

    def adjust_difficulty(self, player_id: str) -> List[DifficultyAdjustment]:
        """Evaluate and apply difficulty adjustments for a player."""
        with self._lock:
            profile = self.get_profile(player_id)
            if profile is None:
                return []

            # Assess current state first
            state_before = profile.current_state
            self.assess_player_state(player_id)
            state_after = profile.current_state

            metrics_deque = self._metrics_history.get(profile.profile_id, deque())
            if not metrics_deque:
                return []

            recent_metrics = list(metrics_deque)
            adjustments: List[DifficultyAdjustment] = []

            # Determine target direction
            direction = self._compute_adjustment_direction(state_after)

            # Get strategy-specific magnitude
            magnitude = self._compute_adjustment_magnitude(
                profile.strategy, profile, recent_metrics
            )

            # Calculate confidence based on metric stability
            confidence = self._compute_confidence(recent_metrics, profile)

            # Apply adjustments to each parameter
            for param, param_data in profile.parameters.items():
                old_val = param_data["current"]
                p_min = param_data["min"]
                p_max = param_data["max"]

                if direction == 0 and state_after == PlayerState.CHALLENGED:
                    # Optimal zone: only micro-adjust
                    new_val = old_val
                else:
                    # Calculate change scaled to the parameter range
                    param_range = p_max - p_min
                    change = direction * magnitude * param_range

                    # Apply strategy-specific modifiers
                    change = self._apply_strategy_modifier(
                        profile.strategy, param, change, recent_metrics, profile
                    )

                    new_val = old_val + change
                    new_val = max(p_min, min(p_max, new_val))
                    new_val = round(new_val, 4)

                # Only record if there was a meaningful change
                if abs(new_val - old_val) > 0.0001:
                    param_data["current"] = new_val

                    reason = self._generate_reason(param, direction, state_after)

                    adjustment = DifficultyAdjustment(
                        profile_id=profile.profile_id,
                        parameter=param,
                        old_value=old_val,
                        new_value=new_val,
                        reason=reason,
                        confidence=confidence,
                        player_state_before=state_before,
                        player_state_after=state_after,
                    )
                    adjustments.append(adjustment)
                    profile.history.append(adjustment)
                    self._adjustments.append(adjustment)

            # Update composite difficulty from parameter average
            if adjustments:
                self._update_composite_difficulty(profile)

            profile.updated_at = time.time()
            self._stats["total_adjustments"] += len(adjustments)

            # Update state distribution tracking
            self._stats["state_distribution"][state_after.value] += 1

            return adjustments

    def _compute_adjustment_direction(self, state: PlayerState) -> float:
        """Determine adjustment direction: positive = harder, negative = easier."""
        direction_map = {
            PlayerState.STRUGGLING: -0.8,
            PlayerState.CHALLENGED: 0.0,
            PlayerState.COMFORTABLE: 0.2,
            PlayerState.DOMINATING: 0.4,
            PlayerState.BORED: 0.7,
        }
        return direction_map.get(state, 0.0)

    def _compute_adjustment_magnitude(
        self,
        strategy: AdjustmentStrategy,
        profile: DifficultyProfile,
        recent_metrics: List[PerformanceMetrics],
    ) -> float:
        """Compute the raw adjustment magnitude based on strategy."""
        base_rate = profile.adaptation_rate

        if strategy == AdjustmentStrategy.GRADUAL:
            return base_rate * 0.5
        elif strategy == AdjustmentStrategy.AGGRESSIVE:
            return base_rate * 2.5
        elif strategy == AdjustmentStrategy.CONSERVATIVE:
            # Smaller increases, normal decreases
            direction = self._compute_adjustment_direction(profile.current_state)
            if direction > 0:
                return base_rate * 0.2
            return base_rate * 0.8
        elif strategy == AdjustmentStrategy.ADAPTIVE:
            # Magnitude scales with rate of state change
            if len(profile.history) < 3:
                return base_rate
            recent_adjustments = profile.history[-3:]
            avg_magnitude = sum(
                abs(a.new_value - a.old_value) for a in recent_adjustments
            ) / 3.0
            # If state is changing rapidly, amplify; if stable, reduce
            state_changes = sum(
                1 for a in recent_adjustments
                if a.player_state_before != a.player_state_after
            )
            if state_changes >= 2:
                return base_rate * 1.8
            elif state_changes == 0:
                return base_rate * 0.4
            return base_rate
        elif strategy == AdjustmentStrategy.PREDICTIVE:
            # Look at trend over history to anticipate needs
            if len(profile.history) < 5:
                return base_rate
            window = profile.history[-5:]
            direction_trend = sum(
                self._compute_adjustment_direction(a.player_state_after)
                for a in window
            ) / 5.0
            current_direction = self._compute_adjustment_direction(profile.current_state)
            # If trend suggests worsening, preemptively increase magnitude
            if current_direction > 0 and direction_trend > current_direction:
                return base_rate * 1.5
            elif current_direction < 0 and direction_trend < current_direction:
                return base_rate * 1.3
            return base_rate

        return base_rate

    def _apply_strategy_modifier(
        self,
        strategy: AdjustmentStrategy,
        param: DifficultyParameter,
        change: float,
        recent_metrics: List[PerformanceMetrics],
        profile: DifficultyProfile,
    ) -> float:
        """Apply per-parameter strategy modifiers."""
        modified = change

        # CONSERVATIVE: harder to increase enemy stats
        if strategy == AdjustmentStrategy.CONSERVATIVE:
            offensive_params = {
                DifficultyParameter.ENEMY_HEALTH,
                DifficultyParameter.ENEMY_DAMAGE,
                DifficultyParameter.ENEMY_SPEED,
                DifficultyParameter.ENEMY_COUNT,
                DifficultyParameter.ENEMY_AI,
                DifficultyParameter.SPAWN_RATE,
                DifficultyParameter.PUZZLE_COMPLEXITY,
                DifficultyParameter.BOSS_PHASES,
            }
            if param in offensive_params and change > 0:
                modified *= 0.5

        # AGGRESSIVE: boost enemy-related changes
        if strategy == AdjustmentStrategy.AGGRESSIVE:
            combat_params = {
                DifficultyParameter.ENEMY_HEALTH,
                DifficultyParameter.ENEMY_DAMAGE,
                DifficultyParameter.ENEMY_SPEED,
                DifficultyParameter.ENEMY_COUNT,
                DifficultyParameter.ENEMY_AI,
            }
            if param in combat_params:
                modified *= 1.3

        # PREDICTIVE: use performance trends for specific params
        if strategy == AdjustmentStrategy.PREDICTIVE and len(recent_metrics) >= 3:
            recent = recent_metrics[-3:]
            if param == DifficultyParameter.ENEMY_DAMAGE:
                dmg_trend = [m.damage_taken for m in recent]
                if len(dmg_trend) >= 2 and dmg_trend[-1] > dmg_trend[0] * 1.3:
                    modified *= 0.8  # Player taking more damage, ease off
            elif param == DifficultyParameter.ENEMY_HEALTH:
                kill_trend = [m.kill_efficiency for m in recent]
                if len(kill_trend) >= 2 and kill_trend[-1] > kill_trend[0] * 1.2:
                    modified *= 1.2  # Player killing faster, boost health more

        # ADAPTIVE: modulate based on parameter responsiveness
        if strategy == AdjustmentStrategy.ADAPTIVE:
            history_for_param = [
                adj for adj in profile.history[-5:] if adj.parameter == param
            ]
            if len(history_for_param) >= 2:
                last_change = history_for_param[-1]
                time_since = time.time() - last_change.timestamp
                if time_since < 5.0:
                    modified *= 0.3  # Very recent change, slow down
                elif time_since < 15.0:
                    modified *= 0.6

        return modified

    def _compute_confidence(
        self,
        recent_metrics: List[PerformanceMetrics],
        profile: DifficultyProfile,
    ) -> float:
        """Estimate confidence in the adjustment decision."""
        if len(recent_metrics) < 2:
            return 0.3

        # Higher confidence with more data points
        sample_confidence = min(0.9, 0.3 + len(recent_metrics) * 0.03)

        # Higher confidence with stable metrics (low variance)
        if len(recent_metrics) >= 3:
            efficiencies = [m.kill_efficiency for m in recent_metrics[-5:]]
            if len(efficiencies) >= 2:
                mean_eff = sum(efficiencies) / len(efficiencies)
                variance = sum((e - mean_eff) ** 2 for e in efficiencies) / len(efficiencies)
                stability = max(0.0, 1.0 - variance * 5.0)
                sample_confidence = sample_confidence * 0.5 + stability * 0.5

        # Lower confidence if very few adjustments in history
        if len(profile.history) < 3:
            sample_confidence *= 0.7

        # Higher confidence with consistent state
        if len(profile.history) >= 5:
            recent_states = [a.player_state_after for a in profile.history[-5:]]
            unique_states = len(set(recent_states))
            if unique_states == 1:
                sample_confidence *= 1.1  # Stable state = confident assessment
            elif unique_states >= 4:
                sample_confidence *= 0.8  # Volatile state = less confident

        return round(min(0.95, max(0.1, sample_confidence)), 2)

    def _generate_reason(
        self,
        param: DifficultyParameter,
        direction: float,
        state: PlayerState,
    ) -> str:
        """Generate a human-readable reason for a difficulty adjustment."""
        param_labels: Dict[DifficultyParameter, str] = {
            DifficultyParameter.ENEMY_HEALTH: "enemy health",
            DifficultyParameter.ENEMY_DAMAGE: "enemy damage",
            DifficultyParameter.ENEMY_SPEED: "enemy speed",
            DifficultyParameter.ENEMY_COUNT: "enemy count",
            DifficultyParameter.ENEMY_AI: "enemy AI aggressiveness",
            DifficultyParameter.SPAWN_RATE: "spawn rate",
            DifficultyParameter.RESOURCE_DROP: "resource drop rate",
            DifficultyParameter.TIME_LIMIT: "time limit",
            DifficultyParameter.CHECKPOINT_FREQUENCY: "checkpoint frequency",
            DifficultyParameter.PUZZLE_COMPLEXITY: "puzzle complexity",
            DifficultyParameter.BOSS_PHASES: "boss phase count",
            DifficultyParameter.ITEM_AVAILABILITY: "item availability",
        }

        label = param_labels.get(param, param.value)

        action = "increasing" if direction > 0.1 else "decreasing" if direction < -0.1 else "maintaining"
        context = f"player state: {state.value}"

        return f"{action} {label} ({context})"

    def _update_composite_difficulty(self, profile: DifficultyProfile) -> None:
        """Update the composite difficulty score from parameter values."""
        if not profile.parameters:
            return

        normalized_values = []
        for param_data in profile.parameters.values():
            p_min = param_data["min"]
            p_max = param_data["max"]
            p_val = param_data["current"]
            if p_max > p_min:
                normalized = (p_val - p_min) / (p_max - p_min)
                normalized_values.append(normalized)

        if normalized_values:
            profile.current_difficulty = round(
                sum(normalized_values) / len(normalized_values), 4
            )

    # ------------------------------------------------------------------
    # Difficulty Recommendations
    # ------------------------------------------------------------------

    def get_recommended_difficulty(self, player_id: str) -> Optional[float]:
        """Get the current recommended composite difficulty for a player."""
        with self._lock:
            profile = self.get_profile(player_id)
            if profile is None:
                return None
            return profile.current_difficulty

    def get_difficulty_history(self, player_id: str) -> List[DifficultyAdjustment]:
        """Retrieve all historical difficulty adjustments for a player."""
        with self._lock:
            profile = self.get_profile(player_id)
            if profile is None:
                return []
            return list(profile.history)

    # ------------------------------------------------------------------
    # State Analysis
    # ------------------------------------------------------------------

    def get_state_transitions(
        self,
        player_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get state transition log, optionally filtered by player."""
        with self._lock:
            all_transitions = list(self._state_transition_log)
            if player_id:
                return [t for t in all_transitions if t["player_id"] == player_id]
            return all_transitions

    def get_player_state_summary(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of the player's current difficulty state."""
        with self._lock:
            profile = self.get_profile(player_id)
            if profile is None:
                return None

            history = profile.history
            state_counts: Dict[str, int] = {}
            for adj in history:
                state_counts[adj.player_state_after.value] = (
                    state_counts.get(adj.player_state_after.value, 0) + 1
                )

            recent_adjustments = history[-10:] if len(history) >= 10 else history
            avg_confidence = (
                sum(a.confidence for a in recent_adjustments) / len(recent_adjustments)
                if recent_adjustments else 0.0
            )

            return {
                "player_id": player_id,
                "profile_id": profile.profile_id,
                "current_state": profile.current_state.value,
                "current_difficulty": profile.current_difficulty,
                "baseline_difficulty": profile.baseline_difficulty,
                "strategy": profile.strategy.value,
                "total_adjustments": len(history),
                "state_history": state_counts,
                "average_confidence": round(avg_confidence, 2),
                "parameters_active": len(profile.parameters),
                "last_updated": profile.updated_at,
            }

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def reset_profile(self, player_id: str) -> bool:
        """Reset a player's difficulty profile to baseline."""
        with self._lock:
            profile = self.get_profile(player_id)
            if profile is None:
                return False

            baseline = profile.baseline_difficulty
            for param, (p_min, p_max, p_default) in self._DEFAULT_PARAMETER_RANGES.items():
                scaled = p_default * baseline
                profile.parameters[param] = {
                    "min": p_min,
                    "max": p_max,
                    "current": round(min(max(scaled, p_min), p_max), 4),
                }

            profile.current_difficulty = baseline
            profile.current_state = PlayerState.CHALLENGED
            profile.updated_at = time.time()

            return True

    def export_profile(self, player_id: str) -> Optional[str]:
        """Export a player's difficulty profile as a JSON string."""
        with self._lock:
            profile = self.get_profile(player_id)
            if profile is None:
                return None

            export_data = {
                "profile": profile.to_dict(),
                "parameters": {
                    p.value: v for p, v in profile.parameters.items()
                },
                "history": [adj.to_dict() for adj in profile.history],
            }
            return json.dumps(export_data, indent=2)

    def import_profile(self, json_data: str) -> Optional[DifficultyProfile]:
        """Import a previously exported difficulty profile from JSON."""
        with self._lock:
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError:
                return None

            profile_data = data.get("profile", {})
            params_data = data.get("parameters", {})

            player_id = profile_data.get("player_id", "")
            if not player_id:
                return None

            try:
                strategy = AdjustmentStrategy(
                    profile_data.get("strategy", "gradual")
                )
            except ValueError:
                strategy = AdjustmentStrategy.GRADUAL

            try:
                state = PlayerState(
                    profile_data.get("current_state", "challenged")
                )
            except ValueError:
                state = PlayerState.CHALLENGED

            profile = DifficultyProfile(
                player_id=player_id,
                baseline_difficulty=float(profile_data.get("baseline_difficulty", 0.5)),
                current_difficulty=float(profile_data.get("current_difficulty", 0.5)),
                strategy=strategy,
                current_state=state,
                min_difficulty=float(profile_data.get("min_difficulty", 0.1)),
                max_difficulty=float(profile_data.get("max_difficulty", 1.0)),
            )

            for param_key, param_vals in params_data.items():
                try:
                    param = DifficultyParameter(param_key)
                except ValueError:
                    continue
                profile.parameters[param] = {
                    "min": float(param_vals.get("min", 0.1)),
                    "max": float(param_vals.get("max", 1.0)),
                    "current": float(param_vals.get("current", 1.0)),
                }

            self._profiles[profile.profile_id] = profile
            self._metrics_history[profile.profile_id] = deque(maxlen=100)
            self._stats["total_profiles"] += 1
            self._stats["strategy_distribution"][strategy.value] += 1

            return profile

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for the dynamic difficulty engine."""
        with self._lock:
            param_usage: Dict[str, int] = {}
            for profile in self._profiles.values():
                for param in profile.parameters:
                    key = param.value
                    param_usage[key] = param_usage.get(key, 0) + 1

            avg_difficulty = 0.0
            if self._profiles:
                avg_difficulty = sum(
                    p.current_difficulty for p in self._profiles.values()
                ) / len(self._profiles)

            recent_adjustments = self._adjustments[-100:] if len(self._adjustments) > 100 else self._adjustments
            param_adjustment_counts: Dict[str, int] = {}
            for adj in recent_adjustments:
                key = adj.parameter.value
                param_adjustment_counts[key] = param_adjustment_counts.get(key, 0) + 1

            return {
                "total_profiles": self._stats["total_profiles"],
                "active_profiles": len(self._profiles),
                "total_metrics_received": self._stats["total_metrics_received"],
                "total_adjustments": self._stats["total_adjustments"],
                "total_state_transitions": len(self._state_transition_log),
                "average_difficulty": round(avg_difficulty, 4),
                "state_distribution": dict(self._stats["state_distribution"]),
                "strategy_distribution": dict(self._stats["strategy_distribution"]),
                "parameter_usage": param_usage,
                "recent_parameter_adjustments": param_adjustment_counts,
                "max_history_per_profile": (
                    self._metrics_history[next(iter(self._metrics_history))].maxlen
                    if self._metrics_history else 0
                ),
            }


# ------------------------------------------------------------------
# Module-level accessor
# ------------------------------------------------------------------


def get_dynamic_difficulty() -> DynamicDifficultyEngine:
    """Return the singleton DynamicDifficultyEngine instance."""
    return DynamicDifficultyEngine.get_instance()