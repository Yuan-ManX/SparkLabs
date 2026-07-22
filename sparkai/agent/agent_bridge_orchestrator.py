"""
SparkLabs Agent - Bridge Orchestrator

The BridgeOrchestrator is the cognitive layer that sits between the
AiNativeGameBridge (which collects telemetry) and the directive
composition (which tells the running game how to adapt). It transforms
raw player behavior signals into purposeful game adaptation decisions.

Original SparkLabs design:
  1. Player Modeling - Builds a running model of the player's skill,
     engagement, frustration, and mastery from telemetry frames.
  2. Intent Inference - Infers what the player is trying to achieve
     (explore, speedrun, complete objective, etc.) from movement
     patterns and event sequences.
  3. Strategy Selection - Picks an adaptation strategy based on the
     player model and current flow state:
       - nurture: help a struggling player
       - challenge: push a bored player
       - reward: celebrate mastery
       - redirect: nudge a stuck player
       - observe: no intervention, gather more data
  4. Directive Authoring - Composes a coherent set of directives that
     execute the chosen strategy. Avoids contradictory directives
     (e.g., simultaneously making the game easier and harder).
  5. Coherence Check - Validates that new directives don't conflict
     with recently issued directives. Applies a cooldown to avoid
     directive flooding.
  6. Outcome Tracking - Records the outcome of each directive (did
     the player's state improve?) for future strategy selection.

The orchestrator is intentionally lightweight (no LLM calls per frame)
and uses heuristic reasoning informed by the existing agent ecosystem.
It runs at the bridge tick frequency (~60Hz) so decisions must be fast.

Thread-safe singleton: use get_instance().
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

class PlayerIntent(Enum):
    """Inferred player intent from behavior."""
    EXPLORE = "explore"          # wandering, looking around
    SPEEDRUN = "speedrun"        # moving fast, skipping content
    COMPLETIONIST = "completionist"  # collecting everything
    STRUGGLING = "struggling"    # dying frequently, low progress
    MASTERED = "mastered"        # high skill, low death
    UNKNOWN = "unknown"


class AdaptationStrategy(Enum):
    """High-level adaptation strategy."""
    NURTURE = "nurture"          # help struggling player
    CHALLENGE = "challenge"      # push bored player
    REWARD = "reward"            # celebrate mastery
    REDIRECT = "redirect"        # nudge stuck player
    OBSERVE = "observe"          # no intervention
    INTRODUCE = "introduce"      # introduce new element to refresh


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class PlayerModel:
    """Running model of the player's state and behavior."""
    skill_estimate: float = 0.5         # 0.0 (novice) to 1.0 (expert)
    engagement: float = 0.5             # 0.0 (bored) to 1.0 (engaged)
    frustration: float = 0.0            # 0.0 to 1.0
    mastery: float = 0.0                # 0.0 to 1.0
    intent: PlayerIntent = PlayerIntent.UNKNOWN
    last_death_tick: int = -1
    last_collect_tick: int = -1
    consecutive_deaths: int = 0
    consecutive_collects: int = 0
    avg_progress_rate: float = 0.0      # x-velocity avg
    avg_input_rate: float = 0.0         # actions per second
    exploration_radius: float = 0.0     # max distance from start
    # Predictive churn risk (0.0 = stable, 1.0 = about to quit)
    churn_risk: float = 0.0
    # Engagement trend: -1.0 (declining) to +1.0 (rising)
    engagement_trend: float = 0.0
    # Rolling engagement history for trend detection
    _engagement_history: Deque[float] = field(default_factory=lambda: deque(maxlen=30))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_estimate": round(self.skill_estimate, 3),
            "engagement": round(self.engagement, 3),
            "frustration": round(self.frustration, 3),
            "mastery": round(self.mastery, 3),
            "intent": self.intent.value,
            "consecutive_deaths": self.consecutive_deaths,
            "consecutive_collects": self.consecutive_collects,
            "avg_progress_rate": round(self.avg_progress_rate, 3),
            "exploration_radius": round(self.exploration_radius, 3),
            "churn_risk": round(self.churn_risk, 3),
            "engagement_trend": round(self.engagement_trend, 3),
        }


@dataclass
class PlayerPreferenceProfile:
    """Tracks which gameplay activities the player engages with most.

    The profile accumulates weighted engagement scores for each activity
    type. Over time, this reveals whether the player prefers combat,
    collection, exploration, or platforming. The orchestrator uses this
    to customize directives - e.g., a combat-loving player gets CHALLENGE
    with enemy spawns, while a collector gets REWARD with collectible spawns.
    """
    combat_score: float = 0.0        # accumulated from enemy_kill events
    collection_score: float = 0.0    # accumulated from collect events
    exploration_score: float = 0.0   # accumulated from movement diversity
    platforming_score: float = 0.0   # accumulated from jump/wall_jump events
    # Normalized preferences (0.0 to 1.0 each, sum may exceed 1.0)
    combat_preference: float = 0.25
    collection_preference: float = 0.25
    exploration_preference: float = 0.25
    platforming_preference: float = 0.25
    # Total events counted for confidence weighting
    total_events: int = 0
    # Dominant preference (updated after enough data)
    dominant: str = "balanced"

    def record_event(self, event: str, engagement: float) -> None:
        """Record a gameplay event and accumulate the relevant score."""
        weight = max(0.1, engagement)  # weight by current engagement
        if event == "enemy_kill":
            self.combat_score += 1.0 * weight
            self.total_events += 1
        elif event == "collect":
            self.collection_score += 1.0 * weight
            self.total_events += 1
        elif event in ("jump", "wall_jump", "wall_slide"):
            self.platforming_score += 0.5 * weight
            self.total_events += 1
        elif event == "explore" or event == "move":
            self.exploration_score += 0.3 * weight
            self.total_events += 1
        self._recompute_preferences()

    def record_movement(self, vx: float, vy: float, exploration_radius: float) -> None:
        """Record movement data to update exploration score."""
        # Diverse vertical movement suggests exploration
        if abs(vy) > 2.0:
            self.exploration_score += 0.1
        # Large exploration radius suggests exploration preference
        if exploration_radius > 500:
            self.exploration_score += 0.05
        self._recompute_preferences()

    def _recompute_preferences(self) -> None:
        """Recompute normalized preferences from accumulated scores."""
        total = self.combat_score + self.collection_score + self.exploration_score + self.platforming_score
        if total < 0.001:
            return
        self.combat_preference = self.combat_score / total
        self.collection_preference = self.collection_score / total
        self.exploration_preference = self.exploration_score / total
        self.platforming_preference = self.platforming_score / total
        # Determine dominant preference (needs at least 10 events for confidence)
        if self.total_events < 10:
            self.dominant = "balanced"
            return
        prefs = {
            "combat": self.combat_preference,
            "collection": self.collection_preference,
            "exploration": self.exploration_preference,
            "platforming": self.platforming_preference,
        }
        max_pref = max(prefs.values())
        if max_pref < 0.35:
            self.dominant = "balanced"
        else:
            self.dominant = max(prefs, key=prefs.get)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "combat_score": round(self.combat_score, 2),
            "collection_score": round(self.collection_score, 2),
            "exploration_score": round(self.exploration_score, 2),
            "platforming_score": round(self.platforming_score, 2),
            "combat_preference": round(self.combat_preference, 3),
            "collection_preference": round(self.collection_preference, 3),
            "exploration_preference": round(self.exploration_preference, 3),
            "platforming_preference": round(self.platforming_preference, 3),
            "total_events": self.total_events,
            "dominant": self.dominant,
        }


@dataclass
class DirectiveRecord:
    """Record of an issued directive and its observed outcome."""
    directive_id: str
    directive_type: str
    strategy: AdaptationStrategy
    issued_at_tick: int
    issued_at_time: float
    params: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_at: float = 0.0
    outcome: str = ""              # "positive", "negative", "neutral", "unknown"
    outcome_observed_at_tick: int = 0


@dataclass
class StrategyContext:
    """Context for a single strategy selection decision."""
    tick: int
    player_model: PlayerModel
    flow_state: str
    skill_estimate: float
    target_difficulty: float
    recent_strategies: List[AdaptationStrategy]
    recent_outcomes: List[str]
    session_frames: int


# =============================================================================
# Bridge Orchestrator
# =============================================================================

class BridgeOrchestrator:
    """
    The cognitive layer that composes purposeful directives from raw
    telemetry. Maintains a per-session player model and selects
    adaptation strategies based on the model and flow state.

    Thread-safe singleton: use get_instance().
    """

    _instance: Optional["BridgeOrchestrator"] = None
    _instance_lock = threading.Lock()

    # Cooldowns (in ticks) to prevent directive flooding
    _COOLDOWN_SPAWN_ENTITY = 90         # ~1.5s
    _COOLDOWN_TUNE_PHYSICS = 180        # ~3s
    _COOLDOWN_TUNE_DIFFICULTY = 240     # ~4s
    _COOLDOWN_TRIGGER_EVENT = 120       # ~2s
    _COOLDOWN_MORPH_ENTITY = 300        # ~5s

    # Frustration thresholds
    _FRUSTRATION_DEATH_SPIKE = 3        # consecutive deaths for "spike"
    _FRUSTRATION_STUCK_TICKS = 90       # ticks with no progress for "stuck"

    # Mastery thresholds
    _MASTERY_KILLS_THRESHOLD = 10
    _MASTERY_NO_DEATH_FRAMES = 240

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # Per-session state
        self._player_models: Dict[str, PlayerModel] = {}
        self._preference_profiles: Dict[str, PlayerPreferenceProfile] = {}
        self._directive_records: Dict[str, Deque[DirectiveRecord]] = {}
        self._cooldowns: Dict[str, Dict[str, int]] = {}  # session_id -> {directive_type: cooldown_until_tick}
        self._last_strategy: Dict[str, AdaptationStrategy] = {}
        self._last_strategy_tick: Dict[str, int] = {}
        self._session_metadata: Dict[str, Dict[str, str]] = {}  # session_id -> {game_id, genre, title}
        self._session_insights: Dict[str, Dict[str, Any]] = {}  # session_id -> accumulated insights
        # Aggregated stats
        self._total_decisions: int = 0
        self._total_directives_authored: int = 0
        self._total_positive_outcomes: int = 0
        self._total_negative_outcomes: int = 0
        self._strategy_usage: Dict[str, int] = {s.value: 0 for s in AdaptationStrategy}
        # Cross-session learning stats
        self._insights_stored: int = 0
        self._insights_retrieved: int = 0
        self._memory_link: Optional[Any] = None
        # Predictive stats
        self._churn_interventions: int = 0

    @classmethod
    def get_instance(cls) -> "BridgeOrchestrator":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ---- Public API ----

    def init_session(
        self,
        session_id: str,
        game_id: str = "",
        genre: str = "",
        title: str = "",
    ) -> None:
        """Initialize orchestrator state for a new session.

        Retrieves past insights from the AgentMemoryOrchestrator for the
        same genre/game so the orchestrator can start with context from
        previous sessions instead of learning from scratch each time.
        """
        with self._lock:
            if session_id not in self._player_models:
                self._player_models[session_id] = PlayerModel()
                self._preference_profiles[session_id] = PlayerPreferenceProfile()
                self._directive_records[session_id] = deque(maxlen=64)
                self._cooldowns[session_id] = {}
                self._last_strategy[session_id] = AdaptationStrategy.OBSERVE
                self._last_strategy_tick[session_id] = 0
                self._session_metadata[session_id] = {
                    "game_id": game_id,
                    "genre": genre,
                    "title": title,
                }
                self._session_insights[session_id] = {
                    "frames_processed": 0,
                    "deaths": 0,
                    "collects": 0,
                    "kills": 0,
                    "wall_jumps": 0,
                    "strategies_used": {},
                    "positive_directives": 0,
                    "negative_directives": 0,
                }
            # Retrieve past insights for this genre/game (outside lock to avoid deadlock)
        self._retrieve_past_insights(session_id, genre, game_id)

    def cleanup_session(self, session_id: str) -> None:
        """Store session insights to memory, then remove orchestrator state."""
        # Store insights before clearing (outside lock to avoid deadlock)
        self._store_session_insights(session_id)
        with self._lock:
            self._player_models.pop(session_id, None)
            self._preference_profiles.pop(session_id, None)
            self._directive_records.pop(session_id, None)
            self._cooldowns.pop(session_id, None)
            self._last_strategy.pop(session_id, None)
            self._last_strategy_tick.pop(session_id, None)
            self._session_metadata.pop(session_id, None)
            self._session_insights.pop(session_id, None)

    def update_player_model(
        self,
        session_id: str,
        frame: Any,
        flow_state: str,
        skill_estimate: float,
        target_difficulty: float,
    ) -> PlayerModel:
        """
        Update the player model with a new telemetry frame.
        The frame is expected to be a TelemetryFrame-like object with
        attributes: tick, player_x, player_y, player_vx, player_vy,
        player_health, events, score, lives, enemy_count, collectible_count.
        """
        with self._lock:
            if session_id not in self._player_models:
                self.init_session(session_id)
            model = self._player_models[session_id]
            profile = self._preference_profiles.get(session_id)
            if profile is None:
                profile = PlayerPreferenceProfile()
                self._preference_profiles[session_id] = profile
            insights = self._session_insights.get(session_id, {})

            tick = getattr(frame, "tick", 0)
            events = list(getattr(frame, "events", []) or [])

            # Track session-level insight counters
            insights["frames_processed"] = insights.get("frames_processed", 0) + 1

            # Update consecutive counts
            if "death" in events:
                model.last_death_tick = tick
                model.consecutive_deaths += 1
                model.consecutive_collects = 0
                model.frustration = min(1.0, model.frustration + 0.15)
                insights["deaths"] = insights.get("deaths", 0) + 1
            else:
                model.consecutive_deaths = max(0, model.consecutive_deaths - 1) if model.consecutive_deaths > 0 else 0
                model.frustration = max(0.0, model.frustration - 0.005)

            if "collect" in events:
                model.last_collect_tick = tick
                model.consecutive_collects += 1
                model.engagement = min(1.0, model.engagement + 0.05)
                insights["collects"] = insights.get("collects", 0) + 1
            else:
                model.engagement = max(0.2, model.engagement - 0.002)

            if "enemy_kill" in events:
                model.mastery = min(1.0, model.mastery + 0.03)
                model.engagement = min(1.0, model.engagement + 0.04)
                insights["kills"] = insights.get("kills", 0) + 1

            if "wall_jump" in events:
                model.mastery = min(1.0, model.mastery + 0.02)
                model.skill_estimate = min(1.0, model.skill_estimate + 0.01)
                insights["wall_jumps"] = insights.get("wall_jumps", 0) + 1

            # Update preference profile from events and movement
            for evt in events:
                profile.record_event(evt, model.engagement)
            vx = getattr(frame, "player_vx", 0.0)
            vy = getattr(frame, "player_vy", 0.0)
            profile.record_movement(vx, vy, model.exploration_radius)

            # Update progress rate (smoothed)
            vx_abs = abs(vx)
            model.avg_progress_rate = model.avg_progress_rate * 0.9 + vx_abs * 0.1

            # Update exploration radius
            px = abs(getattr(frame, "player_x", 0.0))
            if px > model.exploration_radius:
                model.exploration_radius = px

            # Update skill estimate from flow state
            if skill_estimate > 0:
                model.skill_estimate = model.skill_estimate * 0.85 + skill_estimate * 0.15

            # Update engagement trend and churn risk
            model._engagement_history.append(model.engagement)
            if len(model._engagement_history) >= 10:
                recent_half = list(model._engagement_history)[-5:]
                older_half = list(model._engagement_history)[:5]
                recent_avg = sum(recent_half) / len(recent_half)
                older_avg = sum(older_half) / len(older_half)
                model.engagement_trend = max(-1.0, min(1.0, recent_avg - older_avg))
            model.churn_risk = self._compute_churn_risk(model, tick)

            # Infer intent
            model.intent = self._infer_intent(model, tick, flow_state)

            # Mastery boost if no deaths for a long time
            if model.consecutive_deaths == 0 and tick > model.last_death_tick + self._MASTERY_NO_DEATH_FRAMES:
                if model.last_death_tick >= 0:  # had at least one death before
                    model.mastery = min(1.0, model.mastery + 0.001)

            return model

    def compose_directives(
        self,
        session_id: str,
        frame: Any,
        flow_state: str,
        skill_estimate: float,
        target_difficulty: float,
        existing_directives: List[Any],
    ) -> List[Dict[str, Any]]:
        """
        Compose a coherent set of directives based on the player model
        and current state. Returns a list of directive dicts ready to
        be turned into BridgeDirective objects by the caller.

        existing_directives: directives already composed for this frame
        (e.g., by the heuristic reasoner). The orchestrator may
        supplement or replace these.
        """
        with self._lock:
            if session_id not in self._player_models:
                self.init_session(session_id)
            model = self._player_models[session_id]
            tick = getattr(frame, "tick", 0)

            # Select strategy. Only record strategy-change tick so that
            # _select_strategy can detect "strategy held for N ticks".
            strategy = self._select_strategy(session_id, model, flow_state, tick, skill_estimate, target_difficulty)
            if strategy != self._last_strategy.get(session_id):
                self._last_strategy_tick[session_id] = tick
            self._last_strategy[session_id] = strategy
            self._strategy_usage[strategy.value] += 1
            self._total_decisions += 1
            # Track per-session strategy usage for insight storage
            insights = self._session_insights.get(session_id, {})
            su = insights.get("strategies_used", {})
            su[strategy.value] = su.get(strategy.value, 0) + 1
            insights["strategies_used"] = su

            # Author directives based on strategy
            directives = self._author_directives(
                session_id, strategy, frame, model, flow_state,
                skill_estimate, target_difficulty, tick,
            )

            # Record directives for outcome tracking
            now = time.time()
            for d in directives:
                record = DirectiveRecord(
                    directive_id=d["directive_id"],
                    directive_type=d["directive_type"],
                    strategy=strategy,
                    issued_at_tick=tick,
                    issued_at_time=now,
                    params=dict(d.get("params", {})),
                )
                self._directive_records[session_id].append(record)
            self._total_directives_authored += len(directives)

            return directives

    def acknowledge_directives(
        self,
        session_id: str,
        applied: List[Dict[str, Any]],
    ) -> None:
        """Record which directives were successfully applied by the client."""
        with self._lock:
            if session_id not in self._directive_records:
                return
            records_by_id = {r.directive_id: r for r in self._directive_records[session_id]}
            for ack in applied:
                did = ack.get("directive_id", "")
                if did in records_by_id:
                    records_by_id[did].acknowledged = True
                    records_by_id[did].acknowledged_at = ack.get("applied_at", time.time())

    def observe_outcomes(
        self,
        session_id: str,
        frame: Any,
    ) -> None:
        """
        Observe the outcome of previously issued directives by checking
        whether the player's state improved after the directive was
        applied. Called every frame.
        """
        with self._lock:
            if session_id not in self._directive_records:
                return
            records = self._directive_records[session_id]
            if not records:
                return
            tick = getattr(frame, "tick", 0)
            events = list(getattr(frame, "events", []) or [])
            model = self._player_models.get(session_id)
            if model is None:
                return

            # Only check outcomes for directives that have been acknowledged
            # and haven't had their outcome observed yet
            for record in records:
                if record.outcome or not record.acknowledged:
                    continue
                # Wait at least 30 ticks after acknowledgment before judging outcome
                if tick - record.issued_at_tick < 30:
                    continue

                outcome = self._judge_outcome(record, frame, model, tick, events)
                if outcome:
                    record.outcome = outcome
                    record.outcome_observed_at_tick = tick
                    insights = self._session_insights.get(session_id, {})
                    if outcome == "positive":
                        self._total_positive_outcomes += 1
                        insights["positive_directives"] = insights.get("positive_directives", 0) + 1
                    elif outcome == "negative":
                        self._total_negative_outcomes += 1
                        insights["negative_directives"] = insights.get("negative_directives", 0) + 1

    def get_player_model(self, session_id: str) -> Optional[PlayerModel]:
        with self._lock:
            return self._player_models.get(session_id)

    def get_last_strategy(self, session_id: str) -> AdaptationStrategy:
        with self._lock:
            return self._last_strategy.get(session_id, AdaptationStrategy.OBSERVE)

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_decisions": self._total_decisions,
                "total_directives_authored": self._total_directives_authored,
                "total_positive_outcomes": self._total_positive_outcomes,
                "total_negative_outcomes": self._total_negative_outcomes,
                "strategy_usage": dict(self._strategy_usage),
                "active_sessions": len(self._player_models),
                "insights_stored": self._insights_stored,
                "insights_retrieved": self._insights_retrieved,
                "memory_linked": self._memory_link is not None,
                "churn_interventions": self._churn_interventions,
            }

    def get_session_insights(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the accumulated insights for a session."""
        with self._lock:
            insights = self._session_insights.get(session_id)
            if insights is None:
                return None
            metadata = self._session_metadata.get(session_id, {})
            model = self._player_models.get(session_id)
            profile = self._preference_profiles.get(session_id)
            return {
                "session_id": session_id,
                "game_id": metadata.get("game_id", ""),
                "genre": metadata.get("genre", ""),
                "title": metadata.get("title", ""),
                "frames_processed": insights.get("frames_processed", 0),
                "deaths": insights.get("deaths", 0),
                "collects": insights.get("collects", 0),
                "kills": insights.get("kills", 0),
                "wall_jumps": insights.get("wall_jumps", 0),
                "strategies_used": dict(insights.get("strategies_used", {})),
                "positive_directives": insights.get("positive_directives", 0),
                "negative_directives": insights.get("negative_directives", 0),
                "final_skill": round(model.skill_estimate, 3) if model else 0.0,
                "final_mastery": round(model.mastery, 3) if model else 0.0,
                "final_engagement": round(model.engagement, 3) if model else 0.0,
                "final_frustration": round(model.frustration, 3) if model else 0.0,
                "final_intent": model.intent.value if model else "unknown",
                "churn_risk": round(model.churn_risk, 3) if model else 0.0,
                "engagement_trend": round(model.engagement_trend, 3) if model else 0.0,
                "preference_profile": profile.to_dict() if profile else None,
            }

    def get_preference_profile(self, session_id: str) -> Optional[PlayerPreferenceProfile]:
        """Get the player preference profile for a session."""
        with self._lock:
            return self._preference_profiles.get(session_id)

    def reset(self) -> None:
        with self._lock:
            self._player_models.clear()
            self._preference_profiles.clear()
            self._directive_records.clear()
            self._cooldowns.clear()
            self._last_strategy.clear()
            self._last_strategy_tick.clear()
            self._session_metadata.clear()
            self._session_insights.clear()
            self._total_decisions = 0
            self._total_directives_authored = 0
            self._total_positive_outcomes = 0
            self._total_negative_outcomes = 0
            self._strategy_usage = {s.value: 0 for s in AdaptationStrategy}
            self._insights_stored = 0
            self._insights_retrieved = 0

    # ---- Internal: Churn Prediction ----

    def _compute_churn_risk(self, model: PlayerModel, tick: int) -> float:
        """Compute the probability that the player is about to quit.

        Combines multiple signals:
          - High frustration + declining engagement = high churn risk
          - Sustained low engagement = moderate churn risk
          - Recent deaths with no recovery = escalating risk
          - Negative engagement trend amplifies risk

        Returns a value from 0.0 (stable) to 1.0 (about to quit).
        """
        risk = 0.0
        # Frustration contribution (0.0 to 0.4)
        if model.frustration > 0.3:
            risk += model.frustration * 0.4
        # Low engagement contribution (0.0 to 0.3)
        if model.engagement < 0.4:
            risk += (0.4 - model.engagement) * 0.5
        # Declining engagement trend amplifies risk (0.0 to 0.2)
        if model.engagement_trend < -0.1:
            risk += abs(model.engagement_trend) * 0.2
        # Consecutive deaths amplify risk (0.0 to 0.2)
        if model.consecutive_deaths >= 2:
            risk += min(0.2, model.consecutive_deaths * 0.05)
        # High skill + low engagement = boredom churn (0.0 to 0.1)
        if model.skill_estimate > 0.7 and model.engagement < 0.3:
            risk += 0.1
        return min(1.0, risk)

    # ---- Internal: Strategy Selection ----

    def _select_strategy(
        self,
        session_id: str,
        model: PlayerModel,
        flow_state: str,
        tick: int,
        skill_estimate: float,
        target_difficulty: float,
    ) -> AdaptationStrategy:
        """Select an adaptation strategy based on the player model and flow state.

        Incorporates predictive churn detection: when churn risk is high,
        the orchestrator proactively intervenes with preference-tailored
        directives before the player quits.
        """
        # Don't switch strategies too quickly
        last_tick = self._last_strategy_tick.get(session_id, 0)
        last_strategy = self._last_strategy.get(session_id, AdaptationStrategy.OBSERVE)
        if tick - last_tick < 60 and last_strategy != AdaptationStrategy.OBSERVE:
            # Keep current strategy for at least 1 second
            return last_strategy

        # Critical churn risk: proactive intervention with player's preferred content
        if model.churn_risk > 0.65:
            profile = self._preference_profiles.get(session_id)
            if profile and profile.dominant == "combat":
                return AdaptationStrategy.CHALLENGE
            elif profile and profile.dominant == "collection":
                return AdaptationStrategy.REWARD
            elif profile and profile.dominant == "exploration":
                return AdaptationStrategy.INTRODUCE
            # Default churn intervention: nurture to reduce frustration
            return AdaptationStrategy.NURTURE

        # Frustration-driven: nurture
        if model.frustration > 0.6 or model.consecutive_deaths >= self._FRUSTRATION_DEATH_SPIKE:
            return AdaptationStrategy.NURTURE

        # Stuck: redirect
        if model.avg_progress_rate < 0.5 and model.engagement < 0.4:
            return AdaptationStrategy.REDIRECT

        # Boredom: challenge or introduce
        if flow_state == "boredom" and model.mastery > 0.5:
            # High mastery + boredom = introduce something new
            if model.mastery > 0.7:
                return AdaptationStrategy.INTRODUCE
            return AdaptationStrategy.CHALLENGE

        # Anxiety: nurture (gently)
        if flow_state == "anxiety" and skill_estimate < 0.4:
            return AdaptationStrategy.NURTURE

        # Mastery: reward
        if model.mastery > 0.7 and model.consecutive_collects >= 3:
            return AdaptationStrategy.REWARD

        # Flow state: observe (let the player enjoy the flow)
        if flow_state == "flow":
            return AdaptationStrategy.OBSERVE

        # Default: observe
        return AdaptationStrategy.OBSERVE

    # ---- Internal: Intent Inference ----

    def _infer_intent(
        self,
        model: PlayerModel,
        tick: int,
        flow_state: str,
    ) -> PlayerIntent:
        """Infer the player's intent from their behavior."""
        # Struggling: many deaths, low progress
        if model.consecutive_deaths >= 2 or model.frustration > 0.5:
            return PlayerIntent.STRUGGLING

        # Speedrun: high progress rate, low engagement with collectibles
        if model.avg_progress_rate > 4.0 and model.consecutive_collects == 0:
            return PlayerIntent.SPEEDRUN

        # Completionist: lots of collects, moderate progress
        if model.consecutive_collects >= 3:
            return PlayerIntent.COMPLETIONIST

        # Mastered: high skill, no recent deaths
        if model.mastery > 0.7 and model.consecutive_deaths == 0:
            return PlayerIntent.MASTERED

        # Explore: low progress rate, but engaged
        if model.avg_progress_rate < 1.5 and model.engagement > 0.5:
            return PlayerIntent.EXPLORE

        return PlayerIntent.UNKNOWN

    # ---- Internal: Directive Authoring ----

    def _author_directives(
        self,
        session_id: str,
        strategy: AdaptationStrategy,
        frame: Any,
        model: PlayerModel,
        flow_state: str,
        skill_estimate: float,
        target_difficulty: float,
        tick: int,
    ) -> List[Dict[str, Any]]:
        """Author a coherent set of directives for the chosen strategy.

        Directive content is customized based on the player's preference
        profile so that interventions feel natural rather than generic.
        """
        directives: List[Dict[str, Any]] = []
        px = getattr(frame, "player_x", 0.0)
        py = getattr(frame, "player_y", 0.0)
        health = getattr(frame, "player_health", 100.0)
        profile = self._preference_profiles.get(session_id)

        if strategy == AdaptationStrategy.NURTURE:
            # Help struggling player: spawn content matching their preference
            if self._off_cooldown(session_id, "spawn_entity", tick):
                if health < 50:
                    # Spawn a healing collectible for low-health players
                    directives.append(self._make_directive(
                        "spawn_entity",
                        {"entity_type": "collectible", "x": px + 80, "y": py - 60,
                         "color": "#10b981"},
                        priority=2,
                    ))
                elif profile and profile.dominant == "combat":
                    # Combat-preferring player: spawn a weak enemy for confidence
                    directives.append(self._make_directive(
                        "spawn_entity",
                        {"entity_type": "enemy", "x": px + 120, "y": py - 20,
                         "vx": -0.5, "color": "#fbbf24", "width": 20, "height": 20},
                        priority=2,
                    ))
            if self._off_cooldown(session_id, "tune_difficulty", tick):
                directives.append(self._make_directive(
                    "tune_difficulty",
                    {"enemy_speed_multiplier": 0.85, "duration_ticks": 180},
                    priority=2,
                ))
            if self._off_cooldown(session_id, "trigger_event", tick):
                directives.append(self._make_directive(
                    "trigger_event",
                    {"event": "pacing_nudge", "message": "Take a breath - you've got this!"},
                    priority=1,
                ))

        elif strategy == AdaptationStrategy.CHALLENGE:
            # Push bored player with their preferred challenge type
            if self._off_cooldown(session_id, "spawn_entity", tick):
                if profile and profile.dominant == "collection":
                    # Collector: spawn a collectible in a risky position
                    directives.append(self._make_directive(
                        "spawn_entity",
                        {"entity_type": "collectible", "x": px + 300, "y": py - 150,
                         "color": "#fbbf24"},
                        priority=1,
                    ))
                else:
                    # Default or combat-preferring: spawn an enemy
                    directives.append(self._make_directive(
                        "spawn_entity",
                        {"entity_type": "enemy", "x": px + 250, "y": py - 40,
                         "vx": -1.5, "color": "#ef4444"},
                        priority=1,
                    ))
            if self._off_cooldown(session_id, "tune_difficulty", tick):
                if profile and profile.dominant == "platforming":
                    # Platformer: increase gravity for tighter challenge
                    directives.append(self._make_directive(
                        "tune_physics",
                        {"gravity_multiplier": 1.1},
                        priority=1,
                    ))
                else:
                    directives.append(self._make_directive(
                        "tune_difficulty",
                        {"enemy_speed_multiplier": 1.15, "duration_ticks": 240},
                        priority=1,
                    ))

        elif strategy == AdaptationStrategy.REWARD:
            # Celebrate mastery with the player's preferred reward type
            if self._off_cooldown(session_id, "trigger_event", tick):
                directives.append(self._make_directive(
                    "trigger_event",
                    {"event": "celebration", "message": "Masterful play!"},
                    priority=2,
                ))
            if self._off_cooldown(session_id, "spawn_entity", tick):
                if profile and profile.dominant == "combat":
                    # Combat lover: spawn a slow enemy for satisfying kill
                    directives.append(self._make_directive(
                        "spawn_entity",
                        {"entity_type": "enemy", "x": px + 150, "y": py - 20,
                         "vx": -0.3, "color": "#fbbf24", "width": 32, "height": 32},
                        priority=2,
                    ))
                else:
                    # Default: spawn a golden collectible
                    directives.append(self._make_directive(
                        "spawn_entity",
                        {"entity_type": "collectible", "x": px + 100, "y": py - 80,
                         "color": "#fbbf24"},
                        priority=2,
                    ))

        elif strategy == AdaptationStrategy.REDIRECT:
            # Nudge stuck player: pacing nudge, slight physics tweak
            if self._off_cooldown(session_id, "trigger_event", tick):
                directives.append(self._make_directive(
                    "trigger_event",
                    {"event": "pacing_nudge", "message": "Try moving forward!",
                     "hint_x": px + 100},
                    priority=2,
                ))
            if self._off_cooldown(session_id, "tune_physics", tick):
                # Slightly boost jump to help unstick
                directives.append(self._make_directive(
                    "tune_physics",
                    {"jump_strength_multiplier": 1.05},
                    priority=1,
                ))

        elif strategy == AdaptationStrategy.INTRODUCE:
            # Introduce the player's least-experienced activity type for variety
            if self._off_cooldown(session_id, "spawn_entity", tick):
                # Determine what to introduce based on preference gaps
                if profile and profile.dominant == "combat":
                    # Combat-heavy player: introduce a collectible to discover
                    directives.append(self._make_directive(
                        "spawn_entity",
                        {"entity_type": "collectible", "x": px - 150, "y": py - 120,
                         "color": "#a855f7", "width": 28, "height": 28},
                        priority=2,
                    ))
                else:
                    # Default: spawn an enemy in an unexpected position
                    directives.append(self._make_directive(
                        "spawn_entity",
                        {"entity_type": "enemy", "x": px - 150, "y": py - 120,
                         "vx": 1.0, "color": "#a855f7", "width": 28, "height": 28},
                        priority=2,
                    ))
            if self._off_cooldown(session_id, "tune_physics", tick):
                # Slightly reduce gravity for a floaty section
                directives.append(self._make_directive(
                    "tune_physics",
                    {"gravity_multiplier": 0.92},
                    priority=1,
                ))

        elif strategy == AdaptationStrategy.OBSERVE:
            # Observe: emit a no_op to sync flow state, no intervention
            directives.append(self._make_directive(
                "no_op",
                {"flow_state": flow_state,
                 "skill_estimate": skill_estimate,
                 "target_difficulty": target_difficulty},
                priority=0,
            ))

        return directives

    # ---- Internal: Cooldown Management ----

    def _off_cooldown(
        self,
        session_id: str,
        directive_type: str,
        current_tick: int,
    ) -> bool:
        """Check if a directive type is off cooldown for this session."""
        cooldowns = self._cooldowns.get(session_id, {})
        cooldown_until = cooldowns.get(directive_type, 0)
        if current_tick < cooldown_until:
            return False
        # Set new cooldown
        cd_ticks = {
            "spawn_entity": self._COOLDOWN_SPAWN_ENTITY,
            "tune_physics": self._COOLDOWN_TUNE_PHYSICS,
            "tune_difficulty": self._COOLDOWN_TUNE_DIFFICULTY,
            "trigger_event": self._COOLDOWN_TRIGGER_EVENT,
            "morph_entity": self._COOLDOWN_MORPH_ENTITY,
        }.get(directive_type, 60)
        cooldowns[directive_type] = current_tick + cd_ticks
        self._cooldowns[session_id] = cooldowns
        return True

    # ---- Internal: Outcome Judgment ----

    def _judge_outcome(
        self,
        record: DirectiveRecord,
        frame: Any,
        model: PlayerModel,
        tick: int,
        events: List[str],
    ) -> str:
        """Judge whether a directive had a positive, negative, or neutral outcome."""
        dt = tick - record.issued_at_tick
        if dt < 30:
            return ""

        # For nurture directives: positive if player stopped dying
        if record.strategy == AdaptationStrategy.NURTURE:
            if "death" not in events and model.consecutive_deaths == 0:
                return "positive"
            if "death" in events:
                return "negative"

        # For challenge directives: positive if player made progress without dying
        elif record.strategy == AdaptationStrategy.CHALLENGE:
            if "enemy_kill" in events:
                return "positive"
            if "death" in events:
                return "negative"

        # For reward directives: positive if engagement stays high
        elif record.strategy == AdaptationStrategy.REWARD:
            if model.engagement > 0.6:
                return "positive"

        # For redirect directives: positive if player starts progressing
        elif record.strategy == AdaptationStrategy.REDIRECT:
            if model.avg_progress_rate > 1.0:
                return "positive"

        # For introduce directives: positive if engagement increases
        elif record.strategy == AdaptationStrategy.INTRODUCE:
            if model.engagement > 0.5 and "death" not in events:
                return "positive"
            if "death" in events:
                return "negative"

        return "neutral"

    # ---- Internal: Helpers ----

    def _make_directive(
        self,
        directive_type: str,
        params: Dict[str, Any],
        priority: int = 0,
    ) -> Dict[str, Any]:
        return {
            "directive_id": uuid.uuid4().hex[:12],
            "directive_type": directive_type,
            "params": params,
            "priority": priority,
        }

    # ---- Internal: Cross-Session Memory Integration ----

    def _ensure_memory_link(self) -> Any:
        """Lazy-connect to AgentMemoryOrchestrator for cross-session learning."""
        if self._memory_link is not None:
            return self._memory_link if self._memory_link is not False else None
        try:
            from sparkai.agent.agent_memory_orchestrator import AgentMemoryOrchestrator
            self._memory_link = AgentMemoryOrchestrator.get_instance()
            return self._memory_link
        except Exception as e:
            logger.warning("AgentMemoryOrchestrator link failed: %s", e)
            self._memory_link = False
            return None

    def _store_session_insights(self, session_id: str) -> None:
        """Store a session's accumulated insights into the persistent memory.

        Called automatically when a session is cleaned up. The insight is
        stored with genre/game tags so future sessions for the same genre
        can retrieve and benefit from past learnings. Includes the player
        preference profile so future sessions start with known preferences.
        """
        memory = self._ensure_memory_link()
        if memory is None:
            return
        with self._lock:
            insights = self._session_insights.get(session_id)
            metadata = self._session_metadata.get(session_id, {})
            model = self._player_models.get(session_id)
            profile = self._preference_profiles.get(session_id)
        if insights is None or insights.get("frames_processed", 0) == 0:
            return
        genre = metadata.get("genre", "unknown")
        game_id = metadata.get("game_id", "")
        title = metadata.get("title", "")
        frames = insights.get("frames_processed", 0)
        deaths = insights.get("deaths", 0)
        collects = insights.get("collects", 0)
        kills = insights.get("kills", 0)
        wall_jumps = insights.get("wall_jumps", 0)
        pos = insights.get("positive_directives", 0)
        neg = insights.get("negative_directives", 0)
        strategies = insights.get("strategies_used", {})
        top_strategy = max(strategies, key=strategies.get) if strategies else "none"
        skill = round(model.skill_estimate, 3) if model else 0.0
        mastery = round(model.mastery, 3) if model else 0.0
        intent = model.intent.value if model else "unknown"
        churn = round(model.churn_risk, 3) if model else 0.0
        dominant_pref = profile.dominant if profile else "balanced"
        # Compose a concise insight summary
        content = (
            f"Bridge session [{genre}/{title}] {frames} frames: "
            f"deaths={deaths} collects={collects} kills={kills} wall_jumps={wall_jumps} | "
            f"directives: +{pos} -{neg} | top_strategy={top_strategy} | "
            f"skill={skill} mastery={mastery} intent={intent} | "
            f"pref={dominant_pref} churn={churn}"
        )
        try:
            memory.store_memory(
                content=content,
                category="bridge_insight",
                priority="medium",
                context={
                    "genre": genre,
                    "game_id": game_id,
                    "frames": frames,
                    "deaths": deaths,
                    "collects": collects,
                    "kills": kills,
                    "positive_directives": pos,
                    "negative_directives": neg,
                    "top_strategy": top_strategy,
                    "final_skill": skill,
                    "final_mastery": mastery,
                    "final_intent": intent,
                    "churn_risk": churn,
                    "dominant_preference": dominant_pref,
                    "combat_pref": round(profile.combat_preference, 3) if profile else 0.25,
                    "collection_pref": round(profile.collection_preference, 3) if profile else 0.25,
                    "exploration_pref": round(profile.exploration_preference, 3) if profile else 0.25,
                    "platforming_pref": round(profile.platforming_preference, 3) if profile else 0.25,
                },
                tags=["bridge", genre, f"game:{game_id}"] if game_id else ["bridge", genre],
                ttl=86400.0 * 7,  # 7 days
            )
            with self._lock:
                self._insights_stored += 1
            logger.info("Stored bridge insight for session %s (genre=%s)", session_id, genre)
        except Exception as e:
            logger.warning("Failed to store bridge insight: %s", e)

    def _retrieve_past_insights(self, session_id: str, genre: str, game_id: str) -> None:
        """Retrieve past session insights for the same genre/game.

        Called automatically when a session is initialized. The retrieved
        insights are used to prime the player model with expectations from
        past sessions (e.g., if players typically struggle with this genre,
        start with a lower skill estimate). Player preferences from past
        sessions are also restored so the orchestrator can tailor directives
        from the very first frame.
        """
        if not genre:
            return
        memory = self._ensure_memory_link()
        if memory is None:
            return
        try:
            results = memory.retrieve_memories(
                category="bridge_insight",
                query_tags=[genre] if not game_id else [genre, f"game:{game_id}"],
                limit=10,
            )
            if not results:
                return
            with self._lock:
                self._insights_retrieved += len(results)
                if session_id in self._player_models:
                    model = self._player_models[session_id]
                    # Prime the player model with aggregated past insights
                    total_sessions = len(results)
                    avg_skill = 0.0
                    avg_mastery = 0.0
                    death_heavy = 0
                    # Aggregate preference scores from past sessions
                    agg_combat = 0.0
                    agg_collection = 0.0
                    agg_exploration = 0.0
                    agg_platforming = 0.0
                    for r in results:
                        ctx = r.context if hasattr(r, "context") else r.get("context", {})
                        avg_skill += float(ctx.get("final_skill", 0.5))
                        avg_mastery += float(ctx.get("final_mastery", 0.0))
                        if ctx.get("deaths", 0) > ctx.get("collects", 0):
                            death_heavy += 1
                        agg_combat += float(ctx.get("combat_pref", 0.25))
                        agg_collection += float(ctx.get("collection_pref", 0.25))
                        agg_exploration += float(ctx.get("exploration_pref", 0.25))
                        agg_platforming += float(ctx.get("platforming_pref", 0.25))
                    if total_sessions > 0:
                        avg_skill /= total_sessions
                        avg_mastery /= total_sessions
                        # Bias initial skill estimate toward past average
                        model.skill_estimate = (model.skill_estimate + avg_skill) / 2.0
                        # If most past sessions were death-heavy, start with
                        # slightly elevated frustration anticipation
                        if death_heavy > total_sessions / 2:
                            model.frustration = 0.1
                        # Restore preference profile from past sessions
                        profile = self._preference_profiles.get(session_id)
                        if profile is None:
                            profile = PlayerPreferenceProfile()
                            self._preference_profiles[session_id] = profile
                        profile.combat_preference = agg_combat / total_sessions
                        profile.collection_preference = agg_collection / total_sessions
                        profile.exploration_preference = agg_exploration / total_sessions
                        profile.platforming_preference = agg_platforming / total_sessions
                        # Determine dominant from restored preferences
                        prefs = {
                            "combat": profile.combat_preference,
                            "collection": profile.collection_preference,
                            "exploration": profile.exploration_preference,
                            "platforming": profile.platforming_preference,
                        }
                        max_pref = max(prefs.values())
                        if max_pref < 0.35:
                            profile.dominant = "balanced"
                        else:
                            profile.dominant = max(prefs, key=prefs.get)
                        profile.total_events = total_sessions * 10  # confidence marker
            logger.info(
                "Retrieved %d past insights for session %s (genre=%s)",
                len(results), session_id, genre,
            )
        except Exception as e:
            logger.warning("Failed to retrieve past insights: %s", e)


# =============================================================================
# Module-level Convenience
# =============================================================================

def get_orchestrator() -> BridgeOrchestrator:
    """Get the singleton BridgeOrchestrator instance."""
    return BridgeOrchestrator.get_instance()
