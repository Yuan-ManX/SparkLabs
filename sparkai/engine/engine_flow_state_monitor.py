"""
SparkLabs Engine - Flow State Monitor Engine

A real-time flow state detection and monitoring engine based on
Csikszentmihalyi's flow theory. Monitors the challenge-skill balance
to detect and maintain player "flow" state, aggregating gameplay
signals into flow readings and producing adaptation suggestions that
keep players within the flow channel.

Architecture:
  FlowStateMonitorEngine (singleton)
    |-- PlayerSignal (atomic gameplay signal from a player)
    |-- FlowReading (computed flow state snapshot for a player)
    |-- FlowHistory (aggregated flow readings over a tick range)
    |-- AdaptationSuggestion (parameter change recommendation)
    |-- FlowProfile (per-player long-term flow characteristics)
    |-- FlowState (8 flow channels from flow theory)
    |-- ChallengeLevel (5 challenge tiers)
    |-- SkillLevel (6 skill tiers)
    |-- SignalType (6 gameplay signal categories)

Core Capabilities:
  - register_player: Create a flow profile for a new player
  - record_signal: Capture a gameplay signal for flow analysis
  - calculate_flow_state: Compute the current flow state from recent signals
  - get_flow_history: Aggregate flow readings over a tick range
  - suggest_adaptation: Recommend game parameter changes to maintain flow
  - update_skill_level: Adjust a player's skill tier
  - get_flow_profile / get_current_reading: Per-player queries
  - analyze_flow_patterns: Detect patterns in flow state transitions
  - get_players_in_state: Find all players in a specific flow state
  - get_stats: Global engine statistics and health summary
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_time_module = time


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class FlowState(Enum):
    """The 8 flow channels from Csikszentmihalyi's flow theory."""
    FLOW = "flow"
    ANXIETY = "anxiety"
    AROUSAL = "arousal"
    CONTROL = "control"
    RELAXATION = "relaxation"
    BOREDOM = "boredom"
    APATHY = "apathy"
    WORRY = "worry"


class ChallengeLevel(Enum):
    """Five tiers describing the perceived difficulty of the current task."""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class SkillLevel(Enum):
    """Six tiers describing a player's demonstrated proficiency."""
    NOVICE = "novice"
    BEGINNER = "beginner"
    COMPETENT = "competent"
    PROFICIENT = "proficient"
    EXPERT = "expert"
    MASTER = "master"


class SignalType(Enum):
    """Categories of gameplay signals used to infer flow state."""
    PERFORMANCE = "performance"
    ENGAGEMENT = "engagement"
    FRUSTRATION = "frustration"
    EXPLORATION = "exploration"
    MASTERY = "mastery"
    FATIGUE = "fatigue"


# ---------------------------------------------------------------------------
# Flow Theory Configuration Tables
# ---------------------------------------------------------------------------

# Numeric mapping for skill tiers (0.0 - 1.0)
SKILL_LEVEL_VALUES: Dict[SkillLevel, float] = {
    SkillLevel.NOVICE: 0.10,
    SkillLevel.BEGINNER: 0.25,
    SkillLevel.COMPETENT: 0.45,
    SkillLevel.PROFICIENT: 0.60,
    SkillLevel.EXPERT: 0.80,
    SkillLevel.MASTER: 0.95,
}

# Threshold lookup tables for mapping numeric scores to enum tiers
SKILL_THRESHOLDS: List[Tuple[float, SkillLevel]] = [
    (0.83, SkillLevel.MASTER),
    (0.66, SkillLevel.EXPERT),
    (0.50, SkillLevel.PROFICIENT),
    (0.33, SkillLevel.COMPETENT),
    (0.16, SkillLevel.BEGINNER),
    (0.00, SkillLevel.NOVICE),
]

CHALLENGE_THRESHOLDS: List[Tuple[float, ChallengeLevel]] = [
    (0.80, ChallengeLevel.VERY_HIGH),
    (0.60, ChallengeLevel.HIGH),
    (0.40, ChallengeLevel.MODERATE),
    (0.20, ChallengeLevel.LOW),
    (0.00, ChallengeLevel.VERY_LOW),
]

# Base flow score per state before balance and intensity modulation
STATE_BASE_SCORE: Dict[FlowState, float] = {
    FlowState.FLOW: 0.90,
    FlowState.CONTROL: 0.70,
    FlowState.AROUSAL: 0.65,
    FlowState.RELAXATION: 0.50,
    FlowState.WORRY: 0.30,
    FlowState.BOREDOM: 0.20,
    FlowState.ANXIETY: 0.15,
    FlowState.APATHY: 0.05,
}

# 8-channel flow state lookup keyed by (challenge_bucket, skill_bucket)
# Buckets are collapsed from the fine-grained tiers into low/moderate/high.
FLOW_STATE_MAP: Dict[Tuple[str, str], FlowState] = {
    ("high", "high"): FlowState.FLOW,
    ("high", "moderate"): FlowState.AROUSAL,
    ("high", "low"): FlowState.ANXIETY,
    ("moderate", "high"): FlowState.CONTROL,
    ("moderate", "moderate"): FlowState.FLOW,
    ("moderate", "low"): FlowState.WORRY,
    ("low", "high"): FlowState.BOREDOM,
    ("low", "moderate"): FlowState.RELAXATION,
    ("low", "low"): FlowState.APATHY,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PlayerSignal:
    """A single gameplay signal captured from a player for flow analysis."""
    signal_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    player_id: str = ""
    signal_type: SignalType = SignalType.PERFORMANCE
    value: float = 0.0
    tick: int = 0
    timestamp: float = field(default_factory=_time_module.time)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "player_id": self.player_id,
            "signal_type": self.signal_type.value,
            "value": self.value,
            "tick": self.tick,
            "timestamp": self.timestamp,
            "context": self.context,
        }


@dataclass
class FlowReading:
    """A computed flow state snapshot for a single player at a point in time."""
    reading_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    player_id: str = ""
    tick: int = 0
    challenge_level: ChallengeLevel = ChallengeLevel.MODERATE
    skill_level: SkillLevel = SkillLevel.COMPETENT
    flow_state: FlowState = FlowState.FLOW
    flow_score: float = 0.0
    challenge_skill_ratio: float = 1.0
    engagement_score: float = 0.0
    frustration_score: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reading_id": self.reading_id,
            "player_id": self.player_id,
            "tick": self.tick,
            "challenge_level": self.challenge_level.value,
            "skill_level": self.skill_level.value,
            "flow_state": self.flow_state.value,
            "flow_score": self.flow_score,
            "challenge_skill_ratio": self.challenge_skill_ratio,
            "engagement_score": self.engagement_score,
            "frustration_score": self.frustration_score,
            "timestamp": self.timestamp,
        }


@dataclass
class FlowHistory:
    """Aggregated flow readings over a tick range for a single player."""
    history_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    player_id: str = ""
    readings: List[FlowReading] = field(default_factory=list)
    avg_flow_score: float = 0.0
    flow_duration: int = 0
    anxiety_duration: int = 0
    boredom_duration: int = 0
    state_transitions: Dict[str, int] = field(default_factory=dict)
    tick_range: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "history_id": self.history_id,
            "player_id": self.player_id,
            "reading_count": len(self.readings),
            "avg_flow_score": self.avg_flow_score,
            "flow_duration": self.flow_duration,
            "anxiety_duration": self.anxiety_duration,
            "boredom_duration": self.boredom_duration,
            "state_transitions": self.state_transitions,
            "tick_range": self.tick_range,
        }


@dataclass
class AdaptationSuggestion:
    """A recommendation for adjusting game parameters to maintain flow."""
    suggestion_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    player_id: str = ""
    current_state: FlowState = FlowState.FLOW
    suggested_action: str = ""
    parameter_changes: Dict[str, float] = field(default_factory=dict)
    priority: str = "low"
    reasoning: str = ""
    tick: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "player_id": self.player_id,
            "current_state": self.current_state.value,
            "suggested_action": self.suggested_action,
            "parameter_changes": self.parameter_changes,
            "priority": self.priority,
            "reasoning": self.reasoning,
            "tick": self.tick,
        }


@dataclass
class FlowProfile:
    """Long-term flow characteristics for a single player."""
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    player_id: str = ""
    optimal_challenge_range: Tuple[float, float] = (0.4, 0.8)
    optimal_skill_zone: SkillLevel = SkillLevel.COMPETENT
    flow_tendency: float = 0.0
    anxiety_threshold: float = 0.8
    boredom_threshold: float = 0.3
    total_flow_time: int = 0
    total_play_time: int = 0
    flow_efficiency: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "player_id": self.player_id,
            "optimal_challenge_range": list(self.optimal_challenge_range),
            "optimal_skill_zone": self.optimal_skill_zone.value,
            "flow_tendency": self.flow_tendency,
            "anxiety_threshold": self.anxiety_threshold,
            "boredom_threshold": self.boredom_threshold,
            "total_flow_time": self.total_flow_time,
            "total_play_time": self.total_play_time,
            "flow_efficiency": self.flow_efficiency,
        }


# ---------------------------------------------------------------------------
# FlowStateMonitorEngine — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class FlowStateMonitorEngine:
    """
    Real-time flow state detection and monitoring engine.

    Aggregates gameplay signals into flow readings using the 8-channel
    challenge-skill model from Csikszentmihalyi's flow theory. Produces
    adaptation suggestions that adjust game parameters to keep players
    within the flow channel.

    Thread-safe via a reentrant lock. Use get_flow_state_monitor() or
    FlowStateMonitorEngine.get_instance() to obtain the singleton.

    Usage:
        monitor = get_flow_state_monitor()
        monitor.register_player("player_1", SkillLevel.BEGINNER)
        monitor.record_signal("player_1", SignalType.PERFORMANCE, 0.7)
        reading = monitor.calculate_flow_state("player_1")
        suggestion = monitor.suggest_adaptation("player_1")
    """

    _instance: Optional["FlowStateMonitorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    SIGNAL_WINDOW_SIZE: int = 50
    READING_HISTORY_SIZE: int = 500

    def __new__(cls) -> "FlowStateMonitorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._profiles: Dict[str, FlowProfile] = {}
        self._signals: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.SIGNAL_WINDOW_SIZE)
        )
        self._readings: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.READING_HISTORY_SIZE)
        )
        self._current_tick: int = 0
        self._total_signals: int = 0
        self._total_readings: int = 0
        self._total_suggestions: int = 0

    @classmethod
    def get_instance(cls) -> "FlowStateMonitorEngine":
        return cls()

    # ------------------------------------------------------------------
    # Player Registration and Profile Management
    # ------------------------------------------------------------------

    def register_player(
        self,
        player_id: str,
        initial_skill_level: SkillLevel = SkillLevel.NOVICE,
    ) -> FlowProfile:
        """Create a flow profile for a new player.

        If a profile already exists for the player, the existing profile
        is returned unchanged.
        """
        with self._lock:
            if player_id in self._profiles:
                return self._profiles[player_id]

            skill_value = SKILL_LEVEL_VALUES[initial_skill_level]
            profile = FlowProfile(
                player_id=player_id,
                optimal_skill_zone=initial_skill_level,
                optimal_challenge_range=(
                    max(0.0, skill_value * 0.8),
                    min(1.0, skill_value * 1.2),
                ),
                anxiety_threshold=min(1.0, skill_value + 0.3),
                boredom_threshold=max(0.0, skill_value - 0.3),
            )
            self._profiles[player_id] = profile
            return profile

    def update_skill_level(
        self,
        player_id: str,
        new_skill_level: SkillLevel,
    ) -> FlowProfile:
        """Update a player's skill level and recalibrate their flow profile.

        Adjusts the optimal challenge range, anxiety threshold, and boredom
        threshold to match the new skill tier. Registers the player if no
        profile exists yet.
        """
        with self._lock:
            profile = self._profiles.get(player_id)
            if profile is None:
                return self.register_player(player_id, new_skill_level)

            skill_value = SKILL_LEVEL_VALUES[new_skill_level]
            profile.optimal_skill_zone = new_skill_level
            profile.optimal_challenge_range = (
                max(0.0, skill_value * 0.8),
                min(1.0, skill_value * 1.2),
            )
            profile.anxiety_threshold = min(1.0, skill_value + 0.3)
            profile.boredom_threshold = max(0.0, skill_value - 0.3)
            return profile

    def get_flow_profile(self, player_id: str) -> Optional[FlowProfile]:
        """Retrieve the flow profile for a player, if one exists."""
        with self._lock:
            return self._profiles.get(player_id)

    # ------------------------------------------------------------------
    # Signal Recording
    # ------------------------------------------------------------------

    def record_signal(
        self,
        player_id: str,
        signal_type: SignalType,
        value: float,
        context: Optional[Dict[str, Any]] = None,
    ) -> PlayerSignal:
        """Capture a gameplay signal for a player and store it for flow analysis.

        Signal values are clamped to the [0.0, 1.0] range. The context dict
        may carry additional information such as explicit difficulty level,
        scene name, or encounter id.
        """
        with self._lock:
            self._current_tick += 1
            signal = PlayerSignal(
                player_id=player_id,
                signal_type=signal_type,
                value=max(0.0, min(1.0, value)),
                tick=self._current_tick,
                context=context or {},
            )
            self._signals[player_id].append(signal)
            self._total_signals += 1
            return signal

    # ------------------------------------------------------------------
    # Flow State Calculation
    # ------------------------------------------------------------------

    def calculate_flow_state(self, player_id: str) -> FlowReading:
        """Compute the current flow state from recent signals for a player.

        Aggregates the most recent gameplay signals to estimate the current
        challenge and skill levels, maps the combination to one of the 8
        flow channels, and derives a flow score (0.0 - 1.0) that reflects
        how close the player is to optimal flow.
        """
        with self._lock:
            profile = self._profiles.get(player_id)
            if profile is None:
                profile = self.register_player(player_id)

            signals = list(self._signals.get(player_id, []))

            # Aggregate signal values by type
            signal_values: Dict[SignalType, List[float]] = defaultdict(list)
            signal_contexts: List[Dict[str, Any]] = []
            for sig in signals:
                signal_values[sig.signal_type].append(sig.value)
                signal_contexts.append(sig.context)

            def _avg(values: List[float]) -> float:
                return sum(values) / len(values) if values else 0.0

            performance_score = _avg(signal_values.get(SignalType.PERFORMANCE, []))
            engagement_score = _avg(signal_values.get(SignalType.ENGAGEMENT, []))
            frustration_score = _avg(signal_values.get(SignalType.FRUSTRATION, []))
            exploration_score = _avg(signal_values.get(SignalType.EXPLORATION, []))
            mastery_score = _avg(signal_values.get(SignalType.MASTERY, []))
            fatigue_score = _avg(signal_values.get(SignalType.FATIGUE, []))

            profile_skill_value = SKILL_LEVEL_VALUES[profile.optimal_skill_zone]

            # Estimate skill level from performance and mastery signals.
            # The player's profile skill acts as a prior so that a few
            # signals do not drastically shift the estimate.
            if signals:
                skill_score = (
                    0.45 * performance_score
                    + 0.30 * mastery_score
                    + 0.15 * profile_skill_value
                    + 0.10 * exploration_score
                )
                # Fatigue reduces effective skill
                skill_score *= (1.0 - 0.15 * fatigue_score)
            else:
                skill_score = profile_skill_value

            skill_score = max(0.0, min(1.0, skill_score))

            # Estimate challenge level from frustration, the performance gap
            # relative to the player's skill prior, fatigue, and engagement.
            if signals:
                performance_gap = profile_skill_value - performance_score
                challenge_score = (
                    0.45 * frustration_score
                    + 0.25 * max(0.0, performance_gap)
                    + 0.15 * fatigue_score
                    + 0.15 * (1.0 - engagement_score)
                )
            else:
                challenge_score = 0.5

            # Factor in explicit difficulty from signal context if present
            for ctx in reversed(signal_contexts):
                if "difficulty" in ctx:
                    try:
                        context_difficulty = float(ctx["difficulty"])
                        challenge_score = 0.6 * challenge_score + 0.4 * context_difficulty
                    except (TypeError, ValueError):
                        pass
                    break

            challenge_score = max(0.0, min(1.0, challenge_score))

            # Map numeric scores to enum tiers
            challenge_level = self._score_to_challenge_level(challenge_score)
            skill_level = self._score_to_skill_level(skill_score)

            # Map challenge-skill combination to a flow state
            flow_state = self._map_flow_state(challenge_level, skill_level)

            # Calculate challenge-skill ratio (guarded against division by zero)
            if skill_score > 0.01:
                ratio = challenge_score / skill_score
            else:
                ratio = 10.0 if challenge_score > 0.01 else 1.0
            ratio = round(min(ratio, 10.0), 4)

            # Calculate flow score (0.0 - 1.0).
            # The score combines a state-based base value with a
            # balance-intensity product. Balance measures how close
            # challenge and skill are to each other; intensity measures
            # how high both values are. Flow requires both balance and
            # high intensity.
            balance = 1.0 - min(1.0, abs(challenge_score - skill_score))
            intensity = (challenge_score + skill_score) / 2.0
            base_score = STATE_BASE_SCORE[flow_state]
            flow_score = 0.4 * base_score + 0.6 * (balance * intensity)
            # Engagement provides a modest boost; frustration a modest penalty
            flow_score *= (1.0 + 0.10 * (engagement_score - 0.5))
            flow_score *= (1.0 - 0.15 * frustration_score)
            flow_score = max(0.0, min(1.0, flow_score))

            self._current_tick += 1
            reading = FlowReading(
                player_id=player_id,
                tick=self._current_tick,
                challenge_level=challenge_level,
                skill_level=skill_level,
                flow_state=flow_state,
                flow_score=round(flow_score, 4),
                challenge_skill_ratio=ratio,
                engagement_score=round(engagement_score, 4),
                frustration_score=round(frustration_score, 4),
            )

            self._readings[player_id].append(reading)
            self._total_readings += 1

            # Update profile statistics
            profile.total_play_time += 1
            if flow_state == FlowState.FLOW:
                profile.total_flow_time += 1
            if profile.total_play_time > 0:
                profile.flow_efficiency = (
                    profile.total_flow_time / profile.total_play_time
                )
                profile.flow_tendency = profile.flow_efficiency

            return reading

    def get_current_reading(self, player_id: str) -> Optional[FlowReading]:
        """Retrieve the most recent flow reading for a player, if any."""
        with self._lock:
            readings = self._readings.get(player_id)
            if readings and len(readings) > 0:
                return readings[-1]
            return None

    # ------------------------------------------------------------------
    # Flow History
    # ------------------------------------------------------------------

    def get_flow_history(
        self,
        player_id: str,
        tick_range: Optional[Dict[str, int]] = None,
    ) -> FlowHistory:
        """Aggregate flow readings over a tick range for a player.

        Args:
            player_id: The player whose readings should be aggregated.
            tick_range: Optional dict with "start" and "end" tick bounds.
                When omitted, all stored readings for the player are used.

        Returns:
            A FlowHistory with average flow score, per-state durations
            (measured in reading ticks), and a state transition map.
        """
        with self._lock:
            readings = list(self._readings.get(player_id, []))

        if tick_range:
            start = tick_range.get("start", 0)
            end = tick_range.get("end", 2**31 - 1)
            readings = [r for r in readings if start <= r.tick <= end]

        if not readings:
            return FlowHistory(
                player_id=player_id,
                readings=[],
                tick_range=tick_range or {},
            )

        avg_flow = sum(r.flow_score for r in readings) / len(readings)

        flow_duration = sum(1 for r in readings if r.flow_state == FlowState.FLOW)
        anxiety_duration = sum(1 for r in readings if r.flow_state == FlowState.ANXIETY)
        boredom_duration = sum(1 for r in readings if r.flow_state == FlowState.BOREDOM)

        # Count state transitions between consecutive readings
        transitions: Dict[str, int] = defaultdict(int)
        for i in range(1, len(readings)):
            prev_state = readings[i - 1].flow_state.value
            curr_state = readings[i].flow_state.value
            if prev_state != curr_state:
                key = f"{prev_state}->{curr_state}"
                transitions[key] += 1

        return FlowHistory(
            player_id=player_id,
            readings=readings,
            avg_flow_score=round(avg_flow, 4),
            flow_duration=flow_duration,
            anxiety_duration=anxiety_duration,
            boredom_duration=boredom_duration,
            state_transitions=dict(transitions),
            tick_range={"start": readings[0].tick, "end": readings[-1].tick},
        )

    # ------------------------------------------------------------------
    # Adaptation Suggestions
    # ------------------------------------------------------------------

    def suggest_adaptation(self, player_id: str) -> AdaptationSuggestion:
        """Suggest game parameter changes to maintain or restore flow.

        Produces a state-specific recommendation with concrete parameter
        changes (e.g., "reduce enemy_health by 15%") and a human-readable
        rationale. If no reading exists yet, one is computed first.
        """
        reading = self.get_current_reading(player_id)
        if reading is None:
            reading = self.calculate_flow_state(player_id)

        state = reading.flow_state

        with self._lock:
            self._current_tick += 1
            suggestion_tick = self._current_tick
            self._total_suggestions += 1

        challenge_desc = reading.challenge_level.value
        skill_desc = reading.skill_level.value

        if state == FlowState.ANXIETY:
            return AdaptationSuggestion(
                player_id=player_id,
                current_state=state,
                suggested_action="reduce_difficulty",
                parameter_changes={
                    "enemy_health": -0.15,
                    "enemy_damage": -0.10,
                    "enemy_count": -0.10,
                    "hint_frequency": 0.20,
                    "time_limit": 0.15,
                },
                priority="high",
                reasoning=(
                    f"Player is in ANXIETY (challenge={challenge_desc}, "
                    f"skill={skill_desc}). The challenge exceeds the player's "
                    f"current skill. Reducing enemy health by 15%, enemy damage "
                    f"by 10%, and enemy count by 10% should lower the challenge "
                    f"toward the flow channel. Increasing hint frequency will "
                    f"help the player develop effective strategies."
                ),
                tick=suggestion_tick,
            )

        if state == FlowState.BOREDOM:
            return AdaptationSuggestion(
                player_id=player_id,
                current_state=state,
                suggested_action="increase_difficulty",
                parameter_changes={
                    "enemy_health": 0.15,
                    "enemy_damage": 0.10,
                    "enemy_count": 0.15,
                    "enemy_variety": 0.20,
                    "complexity": 0.15,
                },
                priority="medium",
                reasoning=(
                    f"Player is in BOREDOM (challenge={challenge_desc}, "
                    f"skill={skill_desc}). The player's skill exceeds the "
                    f"current challenge. Increasing enemy health by 15%, enemy "
                    f"count by 15%, and introducing new enemy types should "
                    f"restore the challenge-skill balance."
                ),
                tick=suggestion_tick,
            )

        if state == FlowState.FLOW:
            return AdaptationSuggestion(
                player_id=player_id,
                current_state=state,
                suggested_action="maintain_parameters",
                parameter_changes={},
                priority="low",
                reasoning=(
                    f"Player is in FLOW (challenge={challenge_desc}, "
                    f"skill={skill_desc}, flow_score={reading.flow_score}). "
                    f"The challenge-skill balance is optimal. Maintain current "
                    f"game parameters to sustain the flow state."
                ),
                tick=suggestion_tick,
            )

        if state == FlowState.APATHY:
            return AdaptationSuggestion(
                player_id=player_id,
                current_state=state,
                suggested_action="increase_engagement",
                parameter_changes={
                    "tutorial_steps": 0.30,
                    "enemy_health": 0.10,
                    "guidance": 0.25,
                    "complexity": 0.10,
                },
                priority="high",
                reasoning=(
                    f"Player is in APATHY (challenge={challenge_desc}, "
                    f"skill={skill_desc}). Both challenge and skill are low. "
                    f"Provide tutorials to build skill while gradually increasing "
                    f"challenge. Adding guidance and tutorial steps will help "
                    f"the player engage with the game."
                ),
                tick=suggestion_tick,
            )

        if state == FlowState.AROUSAL:
            return AdaptationSuggestion(
                player_id=player_id,
                current_state=state,
                suggested_action="support_skill_growth",
                parameter_changes={
                    "hint_frequency": 0.10,
                    "practice_opportunities": 0.20,
                    "enemy_health": -0.05,
                },
                priority="medium",
                reasoning=(
                    f"Player is in AROUSAL (challenge={challenge_desc}, "
                    f"skill={skill_desc}). The player is engaged but slightly "
                    f"under-skilled for the current challenge. Providing practice "
                    f"opportunities and occasional hints will help the player "
                    f"develop skills toward flow."
                ),
                tick=suggestion_tick,
            )

        if state == FlowState.CONTROL:
            return AdaptationSuggestion(
                player_id=player_id,
                current_state=state,
                suggested_action="increase_challenge",
                parameter_changes={
                    "enemy_health": 0.10,
                    "enemy_count": 0.10,
                    "complexity": 0.10,
                },
                priority="low",
                reasoning=(
                    f"Player is in CONTROL (challenge={challenge_desc}, "
                    f"skill={skill_desc}). The player has high skill for a "
                    f"moderate challenge. Increasing challenge by 10% will "
                    f"push the player toward the flow channel."
                ),
                tick=suggestion_tick,
            )

        if state == FlowState.RELAXATION:
            return AdaptationSuggestion(
                player_id=player_id,
                current_state=state,
                suggested_action="gradually_increase_challenge",
                parameter_changes={
                    "enemy_health": 0.08,
                    "enemy_count": 0.05,
                    "complexity": 0.05,
                },
                priority="low",
                reasoning=(
                    f"Player is in RELAXATION (challenge={challenge_desc}, "
                    f"skill={skill_desc}). The player is relaxed with low "
                    f"challenge and moderate skill. Gradually increasing "
                    f"challenge will move the player toward flow without "
                    f"causing anxiety."
                ),
                tick=suggestion_tick,
            )

        # WORRY
        return AdaptationSuggestion(
            player_id=player_id,
            current_state=state,
            suggested_action="reduce_challenge_and_support",
            parameter_changes={
                "enemy_health": -0.10,
                "hint_frequency": 0.15,
                "enemy_count": -0.05,
            },
            priority="medium",
            reasoning=(
                f"Player is in WORRY (challenge={challenge_desc}, "
                f"skill={skill_desc}). The player faces moderate challenge "
                f"with low skill. Reducing enemy health by 10% and adding "
                f"hints will lower the challenge and support skill development."
            ),
            tick=suggestion_tick,
        )

    # ------------------------------------------------------------------
    # Pattern Analysis
    # ------------------------------------------------------------------

    def analyze_flow_patterns(self, player_id: str) -> Dict[str, Any]:
        """Analyze patterns in flow state transitions for a player.

        Returns state distribution, transition counts, the longest streak
        in any single state, flow stability, and an oscillation flag that
        is set when the player changes states frequently.
        """
        with self._lock:
            readings = list(self._readings.get(player_id, []))

        if not readings:
            return {
                "player_id": player_id,
                "reading_count": 0,
                "patterns": {},
            }

        # State frequency distribution
        state_counts: Dict[str, int] = defaultdict(int)
        for r in readings:
            state_counts[r.flow_state.value] += 1

        most_common_state = (
            max(state_counts.items(), key=lambda x: x[1])[0]
            if state_counts
            else None
        )

        # State transitions between consecutive readings
        transitions: Dict[str, int] = defaultdict(int)
        for i in range(1, len(readings)):
            prev = readings[i - 1].flow_state.value
            curr = readings[i].flow_state.value
            if prev != curr:
                transitions[f"{prev}->{curr}"] += 1

        total_transitions = sum(transitions.values())
        transition_rate = total_transitions / len(readings) if readings else 0.0

        # Longest streak in a single state
        longest_streak = 1
        longest_streak_state = readings[0].flow_state.value
        current_streak = 1
        current_streak_state = readings[0].flow_state.value
        for i in range(1, len(readings)):
            state_val = readings[i].flow_state.value
            if state_val == current_streak_state:
                current_streak += 1
            else:
                if current_streak > longest_streak:
                    longest_streak = current_streak
                    longest_streak_state = current_streak_state
                current_streak = 1
                current_streak_state = state_val
        if current_streak > longest_streak:
            longest_streak = current_streak
            longest_streak_state = current_streak_state

        avg_flow = sum(r.flow_score for r in readings) / len(readings)
        stability = 1.0 - transition_rate

        return {
            "player_id": player_id,
            "reading_count": len(readings),
            "state_distribution": dict(state_counts),
            "most_common_state": most_common_state,
            "state_transitions": dict(transitions),
            "total_transitions": total_transitions,
            "transition_rate": round(transition_rate, 4),
            "longest_streak": longest_streak,
            "longest_streak_state": longest_streak_state,
            "average_flow_score": round(avg_flow, 4),
            "flow_stability": round(stability, 4),
            "oscillating": transition_rate > 0.3,
            "tick_range": {"start": readings[0].tick, "end": readings[-1].tick},
        }

    # ------------------------------------------------------------------
    # Cross-Player Queries
    # ------------------------------------------------------------------

    def get_players_in_state(self, state: FlowState) -> List[str]:
        """Get all players whose most recent reading matches the given state."""
        with self._lock:
            result: List[str] = []
            for player_id, readings in self._readings.items():
                if readings and readings[-1].flow_state == state:
                    result.append(player_id)
            return result

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return global engine statistics and health summary."""
        with self._lock:
            state_distribution: Dict[str, int] = defaultdict(int)
            for readings in self._readings.values():
                if readings:
                    state_distribution[readings[-1].flow_state.value] += 1

            efficiencies = [p.flow_efficiency for p in self._profiles.values()]
            avg_efficiency = (
                sum(efficiencies) / len(efficiencies) if efficiencies else 0.0
            )

            return {
                "total_players": len(self._profiles),
                "total_signals": self._total_signals,
                "total_readings": self._total_readings,
                "total_suggestions": self._total_suggestions,
                "current_tick": self._current_tick,
                "current_state_distribution": dict(state_distribution),
                "average_flow_efficiency": round(avg_efficiency, 4),
                "players_in_flow": state_distribution.get(FlowState.FLOW.value, 0),
                "players_in_anxiety": state_distribution.get(FlowState.ANXIETY.value, 0),
                "players_in_boredom": state_distribution.get(FlowState.BOREDOM.value, 0),
                "players_in_apathy": state_distribution.get(FlowState.APATHY.value, 0),
            }

    # ------------------------------------------------------------------
    # Internal Mapping Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_to_challenge_level(score: float) -> ChallengeLevel:
        """Map a numeric challenge score (0.0-1.0) to a ChallengeLevel tier."""
        for threshold, level in CHALLENGE_THRESHOLDS:
            if score >= threshold:
                return level
        return ChallengeLevel.VERY_LOW

    @staticmethod
    def _score_to_skill_level(score: float) -> SkillLevel:
        """Map a numeric skill score (0.0-1.0) to a SkillLevel tier."""
        for threshold, level in SKILL_THRESHOLDS:
            if score >= threshold:
                return level
        return SkillLevel.NOVICE

    @staticmethod
    def _collapse_challenge(level: ChallengeLevel) -> str:
        """Collapse a 5-tier challenge level into a 3-bucket label."""
        if level in (ChallengeLevel.VERY_LOW, ChallengeLevel.LOW):
            return "low"
        if level == ChallengeLevel.MODERATE:
            return "moderate"
        return "high"

    @staticmethod
    def _collapse_skill(level: SkillLevel) -> str:
        """Collapse a 6-tier skill level into a 3-bucket label."""
        if level in (SkillLevel.NOVICE, SkillLevel.BEGINNER):
            return "low"
        if level in (SkillLevel.COMPETENT, SkillLevel.PROFICIENT):
            return "moderate"
        return "high"

    @classmethod
    def _map_flow_state(
        cls,
        challenge: ChallengeLevel,
        skill: SkillLevel,
    ) -> FlowState:
        """Map a challenge-skill combination to a FlowState.

        Uses the 8-channel model: the 5 challenge tiers and 6 skill tiers
        are collapsed into low/moderate/high buckets, then looked up in
        the FLOW_STATE_MAP table.
        """
        c = cls._collapse_challenge(challenge)
        s = cls._collapse_skill(skill)
        return FLOW_STATE_MAP.get((c, s), FlowState.FLOW)


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_flow_state_monitor() -> FlowStateMonitorEngine:
    """Return the singleton FlowStateMonitorEngine instance."""
    return FlowStateMonitorEngine.get_instance()
