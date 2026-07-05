"""
SparkLabs Agent - AI Experience Tailor

A personalization agent for the SparkLabs AI-native game engine. It
analyzes player behavior, predicts preferences, and dynamically adjusts
content, difficulty, and pacing to craft a unique experience for each
player. The tailor maintains per-player profiles, preference vectors,
skill assessments, and engagement histories, and produces real-time
adjustment recommendations.

Architecture:
  ExperienceTailor (singleton)
    |-- PlayerProfile, PreferenceVector, SkillAssessment, EngagementRecord,
       AdjustmentRecommendation, ExperienceSession, ExperienceStats,
       ExperienceSnapshot, ExperienceEvent
    |-- PlayerArchetype, EngagementLevel, AdjustmentType, ContentCategory,
       SkillDimension, ExperienceEventKind

Core Capabilities:
  - register_player / get_player / list_players: player profile lifecycle
    with archetype classification and skill tracking.
  - record_engagement: log a player's engagement event (session length,
    content type, emotional response) and update the profile.
  - assess_skill: update multi-dimensional skill ratings (combat, puzzle,
    exploration, social, resource management).
  - update_preferences: adjust the player's preference vector across
    content categories.
  - recommend_adjustment: produce a real-time recommendation for
    difficulty, pacing, content type, or reward tuning.
  - get_session / list_sessions: per-session experience tracking.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`ExperienceTailor.get_instance` or the module-level
:func:`get_experience_tailor` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PLAYERS: int = 5000
_MAX_PROFILES: int = 5000
_MAX_ENGAGEMENTS: int = 10000
_MAX_ASSESSMENTS: int = 5000
_MAX_RECOMMENDATIONS: int = 5000
_MAX_SESSIONS: int = 5000
_MAX_EVENTS: int = 5000


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
    if isinstance(value, (list, tuple)):
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


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class PlayerArchetype(Enum):
    """Classification of player behavioral archetypes."""
    EXPLORER = "explorer"
    ACHIEVER = "achiever"
    SOCIALITE = "socialite"
    KILLER = "killer"
    COMPLETIONIST = "completionist"
    SPEEDRUNNER = "speedrunner"
    STORYTELLER = "storyteller"
    BUILDER = "builder"
    STRATEGIST = "strategist"
    CASUAL = "casual"


class EngagementLevel(Enum):
    """How engaged a player was during a session."""
    DISENGAGED = "disengaged"
    PASSIVE = "passive"
    ENGAGED = "engaged"
    HIGHLY_ENGAGED = "highly_engaged"
    FLOW_STATE = "flow_state"


class AdjustmentType(Enum):
    """Types of real-time adjustments the tailor can recommend."""
    DIFFICULTY = "difficulty"
    PACING = "pacing"
    CONTENT_TYPE = "content_type"
    REWARD_FREQUENCY = "reward_frequency"
    NARRATIVE_BRANCH = "narrative_branch"
    TUTORIAL_HINT = "tutorial_hint"
    CHALLENGE_SPIKE = "challenge_spike"
    REST_PERIOD = "rest_period"


class ContentCategory(Enum):
    """Categories of game content for preference tracking."""
    COMBAT = "combat"
    PUZZLE = "puzzle"
    EXPLORATION = "exploration"
    DIALOGUE = "dialogue"
    CRAFTING = "crafting"
    TRADING = "trading"
    BOSS_FIGHT = "boss_fight"
    STEALTH = "stealth"
    RACING = "racing"
    BUILDING = "building"
    STORY = "story"
    MINIGAME = "minigame"


class SkillDimension(Enum):
    """Dimensions along which player skill is assessed."""
    COMBAT = "combat"
    PUZZLE_SOLVING = "puzzle_solving"
    EXPLORATION = "exploration"
    SOCIAL = "social"
    RESOURCE_MGMT = "resource_mgmt"
    REACTION_TIME = "reaction_time"
    STRATEGY = "strategy"
    CREATIVITY = "creativity"


class ExperienceEventKind(Enum):
    """Audit event types emitted by the experience tailor."""
    PLAYER_REGISTERED = "player_registered"
    ENGAGEMENT_RECORDED = "engagement_recorded"
    SKILL_ASSESSED = "skill_assessed"
    PREFERENCES_UPDATED = "preferences_updated"
    ADJUSTMENT_RECOMMENDED = "adjustment_recommended"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class PreferenceVector:
    """A player's preference scores across content categories."""
    player_id: str = ""
    combat: float = 0.5
    puzzle: float = 0.5
    exploration: float = 0.5
    dialogue: float = 0.5
    crafting: float = 0.5
    trading: float = 0.5
    boss_fight: float = 0.5
    stealth: float = 0.5
    racing: float = 0.5
    building: float = 0.5
    story: float = 0.5
    minigame: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)

    def get_score(self, category: str) -> float:
        return getattr(self, category, 0.5)


@dataclass
class SkillAssessment:
    """Multi-dimensional skill rating for a player."""
    assessment_id: str = field(default_factory=lambda: _new_id("skl"))
    player_id: str = ""
    combat: float = 0.0
    puzzle_solving: float = 0.0
    exploration: float = 0.0
    social: float = 0.0
    resource_mgmt: float = 0.0
    reaction_time: float = 0.0
    strategy: float = 0.0
    creativity: float = 0.0
    overall: float = 0.0
    assessed_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EngagementRecord:
    """A single engagement event logged for a player."""
    record_id: str = field(default_factory=lambda: _new_id("eng"))
    player_id: str = ""
    session_id: str = ""
    content_category: str = ContentCategory.COMBAT.value
    duration_seconds: int = 0
    engagement_level: str = EngagementLevel.ENGAGED.value
    emotional_response: float = 0.5
    challenge_felt: float = 0.5
    success: bool = True
    timestamp: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerProfile:
    """A complete player profile with archetype and aggregate stats."""
    player_id: str = field(default_factory=lambda: _new_id("plr"))
    name: str = ""
    archetype: str = PlayerArchetype.EXPLORER.value
    level: int = 1
    total_playtime_seconds: int = 0
    total_sessions: int = 0
    avg_session_length: int = 0
    last_active: str = field(default_factory=_now)
    created_at: str = field(default_factory=_now)
    preferences: PreferenceVector = field(default_factory=PreferenceVector)
    skill: SkillAssessment = field(default_factory=SkillAssessment)
    current_difficulty: float = 0.5
    current_pacing: float = 0.5
    flow_state_count: int = 0
    frustration_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AdjustmentRecommendation:
    """A real-time recommendation for game adjustment."""
    recommendation_id: str = field(default_factory=lambda: _new_id("rec"))
    player_id: str = ""
    session_id: str = ""
    adjustment_type: str = AdjustmentType.DIFFICULTY.value
    current_value: float = 0.5
    recommended_value: float = 0.5
    confidence: float = 0.5
    rationale: str = ""
    priority: int = 0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ExperienceSession:
    """A single play session with start/end tracking."""
    session_id: str = field(default_factory=lambda: _new_id("ses"))
    player_id: str = ""
    started_at: str = field(default_factory=_now)
    ended_at: str = ""
    duration_seconds: int = 0
    avg_engagement: float = 0.5
    peak_engagement: float = 0.5
    content_categories: List[str] = field(default_factory=list)
    adjustments_applied: int = 0
    ended: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ExperienceStats:
    """Aggregate counters for the experience tailor."""
    total_players: int = 0
    total_engagements: int = 0
    total_assessments: int = 0
    total_recommendations: int = 0
    total_sessions: int = 0
    active_sessions: int = 0
    avg_skill: float = 0.0
    avg_engagement: float = 0.0
    flow_state_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ExperienceSnapshot:
    """Immutable point-in-time capture of tailor state."""
    players: Dict[str, Any] = field(default_factory=dict)
    engagements: Dict[str, Any] = field(default_factory=dict)
    recommendations: Dict[str, Any] = field(default_factory=dict)
    sessions: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ExperienceEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: str = ExperienceEventKind.PLAYER_REGISTERED.value
    player_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Experience Tailor Singleton
# ---------------------------------------------------------------------------


class ExperienceTailor:
    """Singleton agent that personalizes game experiences per player.

    The tailor maintains player profiles with preference vectors and
    skill assessments, logs engagement events, and produces real-time
    adjustment recommendations to keep players in the flow channel
    between boredom and frustration.
    """

    _instance: Optional["ExperienceTailor"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._players: Dict[str, PlayerProfile] = {}
        self._engagements: Dict[str, EngagementRecord] = {}
        self._assessments: Dict[str, SkillAssessment] = {}
        self._recommendations: Dict[str, AdjustmentRecommendation] = {}
        self._sessions: Dict[str, ExperienceSession] = {}
        self._events: List[ExperienceEvent] = []
        self._player_engagements: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "ExperienceTailor":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._initialized = True

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(self, kind: ExperienceEventKind, player_id: str = "",
              payload: Optional[Dict[str, Any]] = None) -> None:
        event = ExperienceEvent(
            kind=kind.value,
            player_id=player_id,
            payload=payload or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _coerce_archetype(self, value: Any) -> PlayerArchetype:
        if isinstance(value, PlayerArchetype):
            return value
        if isinstance(value, str) and value:
            try:
                return PlayerArchetype(value)
            except ValueError:
                pass
        return PlayerArchetype.EXPLORER

    def _coerce_engagement(self, value: Any) -> EngagementLevel:
        if isinstance(value, EngagementLevel):
            return value
        if isinstance(value, str) and value:
            try:
                return EngagementLevel(value)
            except ValueError:
                pass
        return EngagementLevel.ENGAGED

    def _coerce_adjustment(self, value: Any) -> AdjustmentType:
        if isinstance(value, AdjustmentType):
            return value
        if isinstance(value, str) and value:
            try:
                return AdjustmentType(value)
            except ValueError:
                pass
        return AdjustmentType.DIFFICULTY

    def _coerce_content(self, value: Any) -> ContentCategory:
        if isinstance(value, ContentCategory):
            return value
        if isinstance(value, str) and value:
            try:
                return ContentCategory(value)
            except ValueError:
                pass
        return ContentCategory.COMBAT

    def _compute_overall_skill(self, skill: SkillAssessment) -> float:
        dims = [skill.combat, skill.puzzle_solving, skill.exploration,
                skill.social, skill.resource_mgmt, skill.reaction_time,
                skill.strategy, skill.creativity]
        return sum(dims) / len(dims) if dims else 0.0

    def _infer_archetype(self, prefs: PreferenceVector, skill: SkillAssessment) -> PlayerArchetype:
        """Infer the player archetype from preferences and skills."""
        scores = {
            PlayerArchetype.EXPLORER: (prefs.exploration + skill.exploration) / 2,
            PlayerArchetype.ACHIEVER: (prefs.boss_fight + skill.combat) / 2,
            PlayerArchetype.SOCIALITE: (prefs.dialogue + skill.social) / 2,
            PlayerArchetype.KILLER: (prefs.combat + skill.combat) / 2,
            PlayerArchetype.COMPLETIONIST: (prefs.puzzle + skill.puzzle_solving) / 2,
            PlayerArchetype.BUILDER: (prefs.building + prefs.crafting) / 2,
            PlayerArchetype.STRATEGIST: (skill.strategy + skill.resource_mgmt) / 2,
            PlayerArchetype.STORYTELLER: (prefs.story + skill.creativity) / 2,
            PlayerArchetype.CASUAL: 0.3,
        }
        best = max(scores, key=scores.get)
        return best if scores[best] > 0.4 else PlayerArchetype.CASUAL

    # ------------------------------------------------------------------
    # Player Lifecycle
    # ------------------------------------------------------------------

    def register_player(
        self,
        name: str = "",
        archetype: Any = PlayerArchetype.EXPLORER.value,
        level: Any = 1,
        player_id: str = "",
        preferences: Any = None,
    ) -> PlayerProfile:
        """Register a new player profile."""
        with self._lock:
            pid = player_id if player_id else _new_id("plr")
            arch = self._coerce_archetype(archetype)
            profile = PlayerProfile(
                player_id=pid,
                name=name,
                archetype=arch.value,
                level=_safe_int(level, 1),
            )
            if preferences and isinstance(preferences, dict):
                for key, val in preferences.items():
                    if hasattr(profile.preferences, key):
                        setattr(profile.preferences, key, _safe_float(val, 0.5))
            profile.preferences.player_id = pid
            profile.skill.player_id = pid
            self._players[pid] = profile
            _evict_fifo_dict(self._players, _MAX_PLAYERS)
            self._player_engagements[pid] = []
            self._emit(ExperienceEventKind.PLAYER_REGISTERED, pid,
                       {"name": name, "archetype": arch.value})
            return profile

    def get_player(self, player_id: str) -> Optional[PlayerProfile]:
        with self._lock:
            return self._players.get(player_id)

    def list_players(self, archetype: Any = None, limit: int = 100) -> List[PlayerProfile]:
        with self._lock:
            items = list(self._players.values())
            if archetype is not None and archetype != "":
                a = self._coerce_archetype(archetype).value
                items = [p for p in items if p.archetype == a]
            return items[:limit]

    # ------------------------------------------------------------------
    # Engagement Tracking
    # ------------------------------------------------------------------

    def record_engagement(
        self,
        player_id: str,
        session_id: str = "",
        content_category: Any = ContentCategory.COMBAT.value,
        duration_seconds: Any = 0,
        engagement_level: Any = EngagementLevel.ENGAGED.value,
        emotional_response: Any = 0.5,
        challenge_felt: Any = 0.5,
        success: Any = True,
    ) -> EngagementRecord:
        """Record a player engagement event and update the profile."""
        with self._lock:
            player = self._players.get(player_id)
            if player is None:
                raise ValueError(f"Player not found: {player_id}")
            cat = self._coerce_content(content_category)
            eng = self._coerce_engagement(engagement_level)
            record = EngagementRecord(
                player_id=player_id,
                session_id=session_id,
                content_category=cat.value,
                duration_seconds=_safe_int(duration_seconds, 0),
                engagement_level=eng.value,
                emotional_response=_safe_float(emotional_response, 0.5),
                challenge_felt=_safe_float(challenge_felt, 0.5),
                success=bool(success),
            )
            self._engagements[record.record_id] = record
            _evict_fifo_dict(self._engagements, _MAX_ENGAGEMENTS)
            self._player_engagements.setdefault(player_id, []).append(record.record_id)
            # Update player aggregate stats
            player.total_playtime_seconds += record.duration_seconds
            player.last_active = _now()
            if eng == EngagementLevel.FLOW_STATE:
                player.flow_state_count += 1
            if record.emotional_response < 0.2 and record.challenge_felt > 0.8:
                player.frustration_count += 1
            # Update preference for this content category
            pref_score = getattr(player.preferences, cat.value, 0.5)
            emotional_weight = _safe_float(emotional_response, 0.5)
            new_score = (pref_score * 0.8) + (emotional_weight * 0.2)
            setattr(player.preferences, cat.value, max(0.0, min(1.0, new_score)))
            # Re-infer archetype periodically
            if len(self._player_engagements.get(player_id, [])) % 10 == 0:
                player.archetype = self._infer_archetype(player.preferences, player.skill).value
            self._emit(ExperienceEventKind.ENGAGEMENT_RECORDED, player_id,
                       {"category": cat.value, "engagement": eng.value,
                        "duration": record.duration_seconds})
            return record

    def get_engagement(self, record_id: str) -> Optional[EngagementRecord]:
        with self._lock:
            return self._engagements.get(record_id)

    def list_engagements(self, player_id: str = "", limit: int = 100) -> List[EngagementRecord]:
        with self._lock:
            items = list(self._engagements.values())
            if player_id:
                items = [e for e in items if e.player_id == player_id]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Skill Assessment
    # ------------------------------------------------------------------

    def assess_skill(
        self,
        player_id: str,
        combat: Any = None,
        puzzle_solving: Any = None,
        exploration: Any = None,
        social: Any = None,
        resource_mgmt: Any = None,
        reaction_time: Any = None,
        strategy: Any = None,
        creativity: Any = None,
    ) -> SkillAssessment:
        """Update a player's multi-dimensional skill assessment."""
        with self._lock:
            player = self._players.get(player_id)
            if player is None:
                raise ValueError(f"Player not found: {player_id}")
            skill = player.skill
            if combat is not None:
                skill.combat = _safe_float(combat, skill.combat)
            if puzzle_solving is not None:
                skill.puzzle_solving = _safe_float(puzzle_solving, skill.puzzle_solving)
            if exploration is not None:
                skill.exploration = _safe_float(exploration, skill.exploration)
            if social is not None:
                skill.social = _safe_float(social, skill.social)
            if resource_mgmt is not None:
                skill.resource_mgmt = _safe_float(resource_mgmt, skill.resource_mgmt)
            if reaction_time is not None:
                skill.reaction_time = _safe_float(reaction_time, skill.reaction_time)
            if strategy is not None:
                skill.strategy = _safe_float(strategy, skill.strategy)
            if creativity is not None:
                skill.creativity = _safe_float(creativity, skill.creativity)
            skill.overall = self._compute_overall_skill(skill)
            skill.assessed_at = _now()
            assessment = SkillAssessment(
                player_id=player_id,
                combat=skill.combat,
                puzzle_solving=skill.puzzle_solving,
                exploration=skill.exploration,
                social=skill.social,
                resource_mgmt=skill.resource_mgmt,
                reaction_time=skill.reaction_time,
                strategy=skill.strategy,
                creativity=skill.creativity,
                overall=skill.overall,
            )
            self._assessments[assessment.assessment_id] = assessment
            _evict_fifo_dict(self._assessments, _MAX_ASSESSMENTS)
            self._emit(ExperienceEventKind.SKILL_ASSESSED, player_id,
                       {"overall": skill.overall})
            return assessment

    # ------------------------------------------------------------------
    # Preference Management
    # ------------------------------------------------------------------

    def update_preferences(
        self,
        player_id: str,
        **kwargs: Any,
    ) -> Optional[PreferenceVector]:
        """Update a player's preference vector."""
        with self._lock:
            player = self._players.get(player_id)
            if player is None:
                return None
            for key, val in kwargs.items():
                if hasattr(player.preferences, key):
                    setattr(player.preferences, key, _safe_float(val, 0.5))
            self._emit(ExperienceEventKind.PREFERENCES_UPDATED, player_id,
                       {"fields": list(kwargs.keys())})
            return player.preferences

    # ------------------------------------------------------------------
    # Adjustment Recommendations
    # ------------------------------------------------------------------

    def recommend_adjustment(
        self,
        player_id: str,
        adjustment_type: Any = AdjustmentType.DIFFICULTY.value,
        session_id: str = "",
        current_value: Any = 0.5,
        confidence: Any = 0.5,
        rationale: str = "",
    ) -> AdjustmentRecommendation:
        """Produce a real-time adjustment recommendation for a player."""
        with self._lock:
            player = self._players.get(player_id)
            if player is None:
                raise ValueError(f"Player not found: {player_id}")
            adj = self._coerce_adjustment(adjustment_type)
            cur = _safe_float(current_value, 0.5)
            conf = _safe_float(confidence, 0.5)
            # Compute recommended value based on player state
            skill_overall = player.skill.overall
            recent_engagements = self._player_engagements.get(player_id, [])
            recent_records = [self._engagements[rid] for rid in recent_engagements[-5:]
                              if rid in self._engagements]
            avg_challenge = (sum(r.challenge_felt for r in recent_records) / len(recent_records)
                             if recent_records else 0.5)
            avg_emotional = (sum(r.emotional_response for r in recent_records) / len(recent_records)
                             if recent_records else 0.5)
            recommended = cur
            priority = 0
            if adj == AdjustmentType.DIFFICULTY:
                # Flow channel: keep challenge slightly above skill
                target = min(1.0, skill_overall + 0.1)
                if avg_challenge > skill_overall + 0.3:
                    recommended = max(0.0, cur - 0.15)
                    priority = 2
                    if not rationale:
                        rationale = "Player is over-challenged; reducing difficulty to prevent frustration"
                elif avg_challenge < skill_overall - 0.2:
                    recommended = min(1.0, cur + 0.1)
                    priority = 1
                    if not rationale:
                        rationale = "Player is under-challenged; increasing difficulty to maintain engagement"
                else:
                    recommended = target
                    if not rationale:
                        rationale = "Player is in the flow channel"
            elif adj == AdjustmentType.PACING:
                if avg_emotional < 0.3:
                    recommended = max(0.0, cur - 0.2)
                    priority = 3
                    if not rationale:
                        rationale = "Low emotional response; slowing pace for recovery"
                elif avg_emotional > 0.8 and avg_challenge > 0.7:
                    recommended = min(1.0, cur + 0.15)
                    priority = 2
                    if not rationale:
                        rationale = "High engagement and challenge; accelerating pace"
                else:
                    recommended = cur
                    if not rationale:
                        rationale = "Pacing is appropriate"
            elif adj == AdjustmentType.CONTENT_TYPE:
                # Recommend the content category with highest preference
                best_cat = max(ContentCategory, key=lambda c: player.preferences.get_score(c.value))
                recommended = float(best_cat.value == ContentCategory.COMBAT.value)
                if not rationale:
                    rationale = f"Recommending {best_cat.value} content based on preferences"
                priority = 1
            elif adj == AdjustmentType.REWARD_FREQUENCY:
                if player.frustration_count > 3:
                    recommended = min(1.0, cur + 0.2)
                    priority = 3
                    if not rationale:
                        rationale = "High frustration detected; increasing reward frequency"
                elif player.flow_state_count > 3:
                    recommended = max(0.0, cur - 0.1)
                    priority = 1
                    if not rationale:
                        rationale = "Player is in flow; reducing reward frequency to maintain intrinsic motivation"
                else:
                    recommended = cur
                    if not rationale:
                        rationale = "Reward frequency is balanced"
            elif adj == AdjustmentType.TUTORIAL_HINT:
                if skill_overall < 0.3 and avg_challenge > 0.6:
                    recommended = 1.0
                    priority = 3
                    if not rationale:
                        rationale = "Low skill and high challenge; providing tutorial hint"
                else:
                    recommended = 0.0
                    if not rationale:
                        rationale = "No tutorial hint needed"
            elif adj == AdjustmentType.CHALLENGE_SPIKE:
                if player.flow_state_count > 2 and avg_emotional > 0.7:
                    recommended = 1.0
                    priority = 2
                    if not rationale:
                        rationale = "Player is ready for a challenge spike"
                else:
                    recommended = 0.0
                    if not rationale:
                        rationale = "No challenge spike needed"
            elif adj == AdjustmentType.REST_PERIOD:
                if avg_emotional < 0.2 and player.frustration_count > 2:
                    recommended = 1.0
                    priority = 3
                    if not rationale:
                        rationale = "Player needs a rest period to recover"
                else:
                    recommended = 0.0
                    if not rationale:
                        rationale = "No rest period needed"
            elif adj == AdjustmentType.NARRATIVE_BRANCH:
                if player.archetype == PlayerArchetype.STORYTELLER.value:
                    recommended = 1.0
                    priority = 2
                    if not rationale:
                        rationale = "Storyteller archetype; offering narrative branch"
                else:
                    recommended = 0.0
                    if not rationale:
                        rationale = "No narrative branch needed"
            rec = AdjustmentRecommendation(
                player_id=player_id,
                session_id=session_id,
                adjustment_type=adj.value,
                current_value=cur,
                recommended_value=max(0.0, min(1.0, recommended)),
                confidence=conf,
                rationale=rationale,
                priority=priority,
            )
            self._recommendations[rec.recommendation_id] = rec
            _evict_fifo_dict(self._recommendations, _MAX_RECOMMENDATIONS)
            self._emit(ExperienceEventKind.ADJUSTMENT_RECOMMENDED, player_id,
                       {"type": adj.value, "recommended": rec.recommended_value,
                        "priority": priority})
            return rec

    def get_recommendation(self, recommendation_id: str) -> Optional[AdjustmentRecommendation]:
        with self._lock:
            return self._recommendations.get(recommendation_id)

    def list_recommendations(self, player_id: str = "", limit: int = 100) -> List[AdjustmentRecommendation]:
        with self._lock:
            items = list(self._recommendations.values())
            if player_id:
                items = [r for r in items if r.player_id == player_id]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def start_session(
        self,
        player_id: str,
        session_id: str = "",
    ) -> ExperienceSession:
        """Start a new experience tracking session for a player."""
        with self._lock:
            player = self._players.get(player_id)
            if player is None:
                raise ValueError(f"Player not found: {player_id}")
            sid = session_id if session_id else _new_id("ses")
            session = ExperienceSession(
                session_id=sid,
                player_id=player_id,
            )
            self._sessions[sid] = session
            _evict_fifo_dict(self._sessions, _MAX_SESSIONS)
            player.total_sessions += 1
            self._emit(ExperienceEventKind.SESSION_STARTED, player_id,
                       {"session_id": sid})
            return session

    def end_session(
        self,
        session_id: str,
        avg_engagement: Any = 0.5,
        peak_engagement: Any = 0.5,
        content_categories: Any = None,
    ) -> Optional[ExperienceSession]:
        """End an active experience session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.ended = True
            session.ended_at = _now()
            session.avg_engagement = _safe_float(avg_engagement, 0.5)
            session.peak_engagement = _safe_float(peak_engagement, 0.5)
            session.content_categories = list(content_categories) if content_categories else []
            # Update player's average session length
            player = self._players.get(session.player_id)
            if player:
                total_time = player.total_playtime_seconds
                total_sessions = max(1, player.total_sessions)
                player.avg_session_length = total_time // total_sessions
            self._emit(ExperienceEventKind.SESSION_ENDED, session.player_id,
                       {"session_id": session_id, "avg_engagement": session.avg_engagement})
            return session

    def get_session(self, session_id: str) -> Optional[ExperienceSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self, player_id: str = "", limit: int = 100) -> List[ExperienceSession]:
        with self._lock:
            items = list(self._sessions.values())
            if player_id:
                items = [s for s in items if s.player_id == player_id]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[ExperienceEvent]:
        with self._lock:
            return list(self._events[-limit:])

    def list_assessments(self, player_id: str = "", limit: int = 100) -> List[SkillAssessment]:
        with self._lock:
            items = list(self._assessments.values())
            if player_id:
                items = [a for a in items if a.player_id == player_id]
            return items[-limit:]

    def get_stats(self) -> ExperienceStats:
        with self._lock:
            active = sum(1 for s in self._sessions.values() if not s.ended)
            skills = [p.skill.overall for p in self._players.values() if p.skill.overall > 0]
            engagements = list(self._engagements.values())
            avg_eng = (sum(e.emotional_response for e in engagements) / len(engagements)
                       if engagements else 0.0)
            total_flow = sum(p.flow_state_count for p in self._players.values())
            total_sessions = sum(p.total_sessions for p in self._players.values())
            flow_rate = total_flow / max(1, total_sessions)
            return ExperienceStats(
                total_players=len(self._players),
                total_engagements=len(self._engagements),
                total_assessments=len(self._assessments),
                total_recommendations=len(self._recommendations),
                total_sessions=len(self._sessions),
                active_sessions=active,
                avg_skill=round(sum(skills) / len(skills), 3) if skills else 0.0,
                avg_engagement=round(avg_eng, 3),
                flow_state_rate=round(flow_rate, 3),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "players": len(self._players),
                "engagements": len(self._engagements),
                "assessments": len(self._assessments),
                "recommendations": len(self._recommendations),
                "sessions": len(self._sessions),
                "events": len(self._events),
            }

    def get_snapshot(self) -> ExperienceSnapshot:
        with self._lock:
            return ExperienceSnapshot(
                players={k: v.to_dict() for k, v in list(self._players.items())[:50]},
                engagements={k: v.to_dict() for k, v in list(self._engagements.items())[:50]},
                recommendations={k: v.to_dict() for k, v in list(self._recommendations.items())[:50]},
                sessions={k: v.to_dict() for k, v in list(self._sessions.items())[:50]},
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._players.clear()
            self._engagements.clear()
            self._assessments.clear()
            self._recommendations.clear()
            self._sessions.clear()
            self._events.clear()
            self._player_engagements.clear()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_experience_tailor() -> ExperienceTailor:
    """Return the singleton ExperienceTailor instance."""
    return ExperienceTailor.get_instance()
