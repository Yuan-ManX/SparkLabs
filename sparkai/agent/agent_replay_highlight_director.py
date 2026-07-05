"""
SparkLabs Agent - AI Replay Highlight Director

A replay highlight director agent for the SparkLabs AI-native game engine. It
analyzes gameplay replay streams to identify highlight-worthy moments,
curates highlight reels, and tags moments by significance, novelty, skill,
and drama. The director composes compilations from disparate gameplay
sessions and scores each moment with a multi-factor significance model.

Architecture:
  ReplayHighlightDirector (singleton)
    |-- HighlightMoment, HighlightReel, MomentAnalysis,
       HighlightTag, DirectorStats, DirectorSnapshot, DirectorEvent
    |-- HighlightCategory, MomentSignificance, HighlightTagKind,
       DirectorEventKind

Core Capabilities:
  - register_replay / get_replay / list_replays / remove_replay: replay
    stream lifecycle management.
  - record_moment / get_moment / list_moments: highlight moment capture
    with category, timestamp, and actor context.
  - analyze_moment: compute a multi-factor significance score from
    rarity, skill, drama, and impact dimensions.
  - curate_reel / get_reel / list_reels / remove_reel: compose highlight
    reels from filtered and ranked moments.
  - tag_moment / list_tags: attach semantic tags to moments for search
    and filtering.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`ReplayHighlightDirector.get_instance` or the module-level
:func:`get_replay_highlight_director` factory.
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

_MAX_REPLAYS: int = 500
_MAX_MOMENTS: int = 5000
_MAX_REELS: int = 200
_MAX_TAGS: int = 3000
_MAX_ANALYSES: int = 2000
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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = low
    if v < low:
        return low
    if v > high:
        return high
    return v


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class HighlightCategory(Enum):
    """Categories that classify the type of highlight moment."""
    KILL = "kill"
    COMBO = "combo"
    SAVE = "save"
    CLUTCH = "clutch"
    FAIL = "fail"
    DISCOVERY = "discovery"
    SPEEDRUN = "speedrun"
    SKILL_SHOT = "skill_shot"
    TEAM_PLAY = "team_play"
    COMEBACK = "comeback"
    BOSS_DEFEAT = "boss_defeat"
    RARE_EVENT = "rare_event"


class MomentSignificance(Enum):
    """Significance bands that gate inclusion in highlight reels."""
    TRIVIAL = "trivial"
    MINOR = "minor"
    NOTABLE = "notable"
    SIGNIFICANT = "significant"
    EPIC = "epic"
    LEGENDARY = "legendary"


class HighlightTagKind(Enum):
    """Semantic tag kinds for organizing highlight moments."""
    GAMEPLAY = "gameplay"
    EMOTIONAL = "emotional"
    TECHNICAL = "technical"
    SOCIAL = "social"
    NARRATIVE = "narrative"
    STATISTICAL = "statistical"


class DirectorEventKind(Enum):
    """Audit event types emitted by the director."""
    REPLAY_REGISTERED = "replay_registered"
    REPLAY_REMOVED = "replay_removed"
    MOMENT_RECORDED = "moment_recorded"
    MOMENT_ANALYZED = "moment_analyzed"
    REEL_CURATED = "reel_curated"
    REEL_REMOVED = "reel_removed"
    TAG_ADDED = "tag_added"
    TAG_REMOVED = "tag_removed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ReplayStream:
    """A gameplay replay stream with metadata and duration."""
    replay_id: str = field(default_factory=lambda: _new_id("rpl"))
    session_id: str = ""
    player_id: str = ""
    game_mode: str = ""
    map_name: str = ""
    duration_ms: int = 0
    started_at: str = ""
    ended_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HighlightMoment:
    """A highlight moment captured within a replay stream."""
    moment_id: str = field(default_factory=lambda: _new_id("hmt"))
    replay_id: str = ""
    category: str = HighlightCategory.KILL.value
    timestamp_ms: int = 0
    duration_ms: int = 5000
    actor_id: str = ""
    target_id: str = ""
    position: Dict[str, float] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    significance: str = MomentSignificance.NOTABLE.value
    significance_score: float = 0.0
    description: str = ""
    thumbnail_url: str = ""
    clip_url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MomentAnalysis:
    """Multi-factor analysis of a highlight moment's significance."""
    analysis_id: str = field(default_factory=lambda: _new_id("man"))
    moment_id: str = ""
    rarity_factor: float = 0.0
    skill_factor: float = 0.0
    drama_factor: float = 0.0
    impact_factor: float = 0.0
    novelty_factor: float = 0.0
    overall_score: float = 0.0
    significance_band: str = MomentSignificance.NOTABLE.value
    analysis_notes: str = ""
    analyzed_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HighlightReel:
    """A curated compilation of highlight moments."""
    reel_id: str = field(default_factory=lambda: _new_id("rel"))
    name: str = ""
    description: str = ""
    moment_ids: List[str] = field(default_factory=list)
    total_duration_ms: int = 0
    curation_criteria: Dict[str, Any] = field(default_factory=dict)
    min_significance: str = MomentSignificance.NOTABLE.value
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HighlightTag:
    """A semantic tag attached to a highlight moment."""
    tag_id: str = field(default_factory=lambda: _new_id("tag"))
    moment_id: str = ""
    kind: str = HighlightTagKind.GAMEPLAY.value
    value: str = ""
    weight: float = 0.5
    source: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DirectorStats:
    """Aggregate counters for the director."""
    total_replays: int = 0
    total_moments: int = 0
    total_reels: int = 0
    total_tags: int = 0
    total_analyses: int = 0
    moments_by_category: Dict[str, int] = field(default_factory=dict)
    moments_by_significance: Dict[str, int] = field(default_factory=dict)
    avg_significance_score: float = 0.0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DirectorSnapshot:
    """Immutable point-in-time capture of director state."""
    replays: Dict[str, Any] = field(default_factory=dict)
    moments: Dict[str, Any] = field(default_factory=dict)
    reels: Dict[str, Any] = field(default_factory=dict)
    tags: List[Dict[str, Any]] = field(default_factory=list)
    analyses: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DirectorEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("dev"))
    kind: str = DirectorEventKind.REPLAY_REGISTERED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Significance Scoring Helpers
# ---------------------------------------------------------------------------


# Category base weights for significance scoring
_CATEGORY_WEIGHTS: Dict[str, float] = {
    HighlightCategory.KILL.value: 0.4,
    HighlightCategory.COMBO.value: 0.6,
    HighlightCategory.SAVE.value: 0.55,
    HighlightCategory.CLUTCH.value: 0.75,
    HighlightCategory.FAIL.value: 0.3,
    HighlightCategory.DISCOVERY.value: 0.45,
    HighlightCategory.SPEEDRUN.value: 0.7,
    HighlightCategory.SKILL_SHOT.value: 0.65,
    HighlightCategory.TEAM_PLAY.value: 0.5,
    HighlightCategory.COMEBACK.value: 0.8,
    HighlightCategory.BOSS_DEFEAT.value: 0.7,
    HighlightCategory.RARE_EVENT.value: 0.85,
}

# Significance band thresholds
_SIGNIFICANCE_BANDS: List[Tuple[float, MomentSignificance]] = [
    (0.85, MomentSignificance.LEGENDARY),
    (0.70, MomentSignificance.EPIC),
    (0.55, MomentSignificance.SIGNIFICANT),
    (0.40, MomentSignificance.NOTABLE),
    (0.20, MomentSignificance.MINOR),
    (0.0, MomentSignificance.TRIVIAL),
]


def _band_for_score(score: float) -> str:
    for threshold, band in _SIGNIFICANCE_BANDS:
        if score >= threshold:
            return band.value
    return MomentSignificance.TRIVIAL.value


# ---------------------------------------------------------------------------
# Replay Highlight Director Singleton
# ---------------------------------------------------------------------------


class ReplayHighlightDirector:
    """Singleton agent that directs replay highlight curation.

    The director maintains replay streams (gameplay session recordings),
    highlight moments (notable events within replays), highlight reels
    (curated compilations), and moment analyses (multi-factor significance
    scoring). It tags moments with semantic labels for search and filters
    moments by category, significance, and tag when composing reels.
    """

    _instance: Optional["ReplayHighlightDirector"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._replays: Dict[str, ReplayStream] = {}
        self._moments: Dict[str, HighlightMoment] = {}
        self._reels: Dict[str, HighlightReel] = {}
        self._tags: List[HighlightTag] = []
        self._analyses: Dict[str, MomentAnalysis] = {}
        self._events: List[DirectorEvent] = []
        self._moments_by_replay: Dict[str, List[str]] = {}
        self._moments_by_category: Dict[str, List[str]] = {}
        self._tags_by_moment: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "ReplayHighlightDirector":
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
            self._seed_defaults()
            self._initialized = True

    def _seed_defaults(self) -> None:
        """Seed a default replay with sample moments and a reel."""
        replay = ReplayStream(
            replay_id="rpl_default_1",
            session_id="sess_demo",
            player_id="player_1",
            game_mode="adventure",
            map_name="dragon_lair",
            duration_ms=600000,
            started_at="2026-07-05T08:00:00Z",
            ended_at="2026-07-05T08:10:00Z",
            metadata={"difficulty": "hard"},
        )
        self._replays[replay.replay_id] = replay
        self._record_event(DirectorEventKind.REPLAY_REGISTERED, {"replay_id": replay.replay_id})

        # Seed sample moments
        sample_moments = [
            ("hmt_sample_1", "rpl_default_1", HighlightCategory.KILL, 30000, 4000,
             "player_1", "goblin_1", "First enemy defeated in the run",
             MomentSignificance.MINOR, 0.25),
            ("hmt_sample_2", "rpl_default_1", HighlightCategory.COMBO, 120000, 6000,
             "player_1", "goblin_pack", "10-hit combo on goblin pack",
             MomentSignificance.NOTABLE, 0.55),
            ("hmt_sample_3", "rpl_default_1", HighlightCategory.BOSS_DEFEAT, 580000, 12000,
             "player_1", "dragon_boss", "Defeated the dragon boss at 5% HP",
             MomentSignificance.LEGENDARY, 0.90),
        ]
        for mid, rid, cat, ts, dur, actor, target, desc, band, score in sample_moments:
            moment = HighlightMoment(
                moment_id=mid,
                replay_id=rid,
                category=cat.value,
                timestamp_ms=ts,
                duration_ms=dur,
                actor_id=actor,
                target_id=target,
                significance=band.value,
                significance_score=score,
                description=desc,
            )
            self._moments[mid] = moment
            self._moments_by_replay.setdefault(rid, []).append(mid)
            self._moments_by_category.setdefault(cat.value, []).append(mid)
            self._record_event(DirectorEventKind.MOMENT_RECORDED, {"moment_id": mid, "category": cat.value})

        # Seed a reel
        reel = HighlightReel(
            reel_id="rel_default_1",
            name="Best of Dragon Lair",
            description="Top highlights from the dragon lair run",
            moment_ids=["hmt_sample_2", "hmt_sample_3"],
            total_duration_ms=18000,
            min_significance=MomentSignificance.NOTABLE.value,
            tags=["combat", "boss"],
        )
        self._reels[reel.reel_id] = reel
        self._record_event(DirectorEventKind.REEL_CURATED, {"reel_id": reel.reel_id})

        # Seed a tag
        tag = HighlightTag(
            tag_id="tag_default_1",
            moment_id="hmt_sample_3",
            kind=HighlightTagKind.EMOTIONAL.value,
            value="clutch",
            weight=0.9,
            source="auto",
        )
        self._tags.append(tag)
        self._tags_by_moment.setdefault("hmt_sample_3", []).append(tag.tag_id)
        self._record_event(DirectorEventKind.TAG_ADDED, {"tag_id": tag.tag_id, "moment_id": "hmt_sample_3"})

    def _record_event(self, kind: DirectorEventKind, payload: Dict[str, Any]) -> None:
        event = DirectorEvent(kind=kind.value, payload=payload)
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Replay Lifecycle
    # ------------------------------------------------------------------

    def register_replay(
        self,
        replay_id: str = "",
        session_id: str = "",
        player_id: str = "",
        game_mode: str = "",
        map_name: str = "",
        duration_ms: int = 0,
        started_at: str = "",
        ended_at: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ReplayStream:
        with self._lock:
            rid = replay_id or _new_id("rpl")
            if rid in self._replays:
                return self._replays[rid]
            replay = ReplayStream(
                replay_id=rid,
                session_id=session_id,
                player_id=player_id,
                game_mode=game_mode,
                map_name=map_name,
                duration_ms=_safe_int(duration_ms),
                started_at=started_at,
                ended_at=ended_at,
                metadata=metadata or {},
            )
            self._replays[rid] = replay
            _evict_fifo_dict(self._replays, _MAX_REPLAYS)
            self._record_event(DirectorEventKind.REPLAY_REGISTERED, {"replay_id": rid})
            return replay

    def get_replay(self, replay_id: str) -> Optional[ReplayStream]:
        with self._lock:
            return self._replays.get(replay_id)

    def list_replays(
        self,
        player_id: str = "",
        game_mode: str = "",
        map_name: str = "",
        limit: int = 100,
    ) -> List[ReplayStream]:
        with self._lock:
            results: List[ReplayStream] = []
            for replay in self._replays.values():
                if player_id and replay.player_id != player_id:
                    continue
                if game_mode and replay.game_mode != game_mode:
                    continue
                if map_name and replay.map_name != map_name:
                    continue
                results.append(replay)
            return results[: max(0, min(limit, len(results)))]

    def remove_replay(self, replay_id: str) -> bool:
        with self._lock:
            existed = self._replays.pop(replay_id, None) is not None
            if existed:
                # Cascade delete moments
                moment_ids = self._moments_by_replay.pop(replay_id, [])
                for mid in moment_ids:
                    self._moments.pop(mid, None)
                    # Remove from categories
                    for cat_list in self._moments_by_category.values():
                        try:
                            cat_list.remove(mid)
                        except ValueError:
                            pass
                self._record_event(DirectorEventKind.REPLAY_REMOVED, {"replay_id": replay_id})
            return existed

    # ------------------------------------------------------------------
    # Moment Management
    # ------------------------------------------------------------------

    def record_moment(
        self,
        replay_id: str = "",
        category: str = HighlightCategory.KILL.value,
        timestamp_ms: int = 0,
        duration_ms: int = 5000,
        actor_id: str = "",
        target_id: str = "",
        position: Optional[Dict[str, float]] = None,
        context: Optional[Dict[str, Any]] = None,
        description: str = "",
        thumbnail_url: str = "",
        clip_url: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        moment_id: str = "",
    ) -> Optional[HighlightMoment]:
        with self._lock:
            mid = moment_id or _new_id("hmt")
            if mid in self._moments:
                return self._moments[mid]
            # Auto-compute initial significance from category
            cat_weight = _CATEGORY_WEIGHTS.get(category, 0.4)
            band = _band_for_score(cat_weight)
            moment = HighlightMoment(
                moment_id=mid,
                replay_id=replay_id,
                category=category,
                timestamp_ms=_safe_int(timestamp_ms),
                duration_ms=_safe_int(duration_ms, 5000),
                actor_id=actor_id,
                target_id=target_id,
                position=position or {},
                context=context or {},
                significance=band,
                significance_score=cat_weight,
                description=description,
                thumbnail_url=thumbnail_url,
                clip_url=clip_url,
                metadata=metadata or {},
            )
            self._moments[mid] = moment
            _evict_fifo_dict(self._moments, _MAX_MOMENTS)
            if replay_id:
                self._moments_by_replay.setdefault(replay_id, []).append(mid)
            self._moments_by_category.setdefault(category, []).append(mid)
            self._record_event(DirectorEventKind.MOMENT_RECORDED, {
                "moment_id": mid,
                "category": category,
                "replay_id": replay_id,
            })
            return moment

    def get_moment(self, moment_id: str) -> Optional[HighlightMoment]:
        with self._lock:
            return self._moments.get(moment_id)

    def list_moments(
        self,
        replay_id: str = "",
        category: str = "",
        significance: str = "",
        actor_id: str = "",
        limit: int = 100,
    ) -> List[HighlightMoment]:
        with self._lock:
            results: List[HighlightMoment] = []
            for moment in self._moments.values():
                if replay_id and moment.replay_id != replay_id:
                    continue
                if category and moment.category != category:
                    continue
                if significance and moment.significance != significance:
                    continue
                if actor_id and moment.actor_id != actor_id:
                    continue
                results.append(moment)
            # Sort by significance score descending
            results.sort(key=lambda m: m.significance_score, reverse=True)
            return results[: max(0, min(limit, len(results)))]

    # ------------------------------------------------------------------
    # Moment Analysis
    # ------------------------------------------------------------------

    def analyze_moment(
        self,
        moment_id: str,
        rarity: float = 0.0,
        skill: float = 0.0,
        drama: float = 0.0,
        impact: float = 0.0,
        novelty: float = 0.0,
        notes: str = "",
    ) -> Optional[MomentAnalysis]:
        with self._lock:
            moment = self._moments.get(moment_id)
            if moment is None:
                return None
            cat_weight = _CATEGORY_WEIGHTS.get(moment.category, 0.4)
            r = _clamp(rarity)
            s = _clamp(skill)
            d = _clamp(drama)
            i = _clamp(impact)
            n = _clamp(novelty)
            # Weighted combination: category base + factor contributions
            overall = _clamp(
                0.25 * cat_weight
                + 0.20 * r
                + 0.20 * s
                + 0.15 * d
                + 0.10 * i
                + 0.10 * n
            )
            band = _band_for_score(overall)
            analysis = MomentAnalysis(
                moment_id=moment_id,
                rarity_factor=r,
                skill_factor=s,
                drama_factor=d,
                impact_factor=i,
                novelty_factor=n,
                overall_score=overall,
                significance_band=band,
                analysis_notes=notes,
            )
            self._analyses[analysis.analysis_id] = analysis
            _evict_fifo_dict(self._analyses, _MAX_ANALYSES)
            # Update the moment with the new score and band
            moment.significance_score = overall
            moment.significance = band
            self._record_event(DirectorEventKind.MOMENT_ANALYZED, {
                "moment_id": moment_id,
                "score": overall,
                "band": band,
            })
            return analysis

    def get_analysis(self, analysis_id: str) -> Optional[MomentAnalysis]:
        with self._lock:
            return self._analyses.get(analysis_id)

    def list_analyses(self, moment_id: str = "", limit: int = 100) -> List[MomentAnalysis]:
        with self._lock:
            results = [a for a in self._analyses.values() if not moment_id or a.moment_id == moment_id]
            return results[: max(0, min(limit, len(results)))]

    # ------------------------------------------------------------------
    # Reel Curation
    # ------------------------------------------------------------------

    def curate_reel(
        self,
        name: str = "",
        description: str = "",
        replay_id: str = "",
        category: str = "",
        min_significance: str = MomentSignificance.NOTABLE.value,
        max_moments: int = 10,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        reel_id: str = "",
    ) -> HighlightReel:
        with self._lock:
            rid = reel_id or _new_id("rel")
            if rid in self._reels:
                return self._reels[rid]
            # Find the significance threshold
            sig_order = [b.value for _, b in _SIGNIFICANCE_BANDS]
            try:
                min_idx = sig_order.index(min_significance)
            except ValueError:
                min_idx = 2  # default to NOTABLE
            allowed_bands = set(sig_order[: min_idx + 1])
            # Filter and rank moments
            candidates: List[HighlightMoment] = []
            for moment in self._moments.values():
                if replay_id and moment.replay_id != replay_id:
                    continue
                if category and moment.category != category:
                    continue
                if moment.significance not in allowed_bands:
                    continue
                candidates.append(moment)
            candidates.sort(key=lambda m: m.significance_score, reverse=True)
            selected = candidates[: max(0, min(max_moments, len(candidates)))]
            total_duration = sum(m.duration_ms for m in selected)
            reel = HighlightReel(
                reel_id=rid,
                name=name,
                description=description,
                moment_ids=[m.moment_id for m in selected],
                total_duration_ms=total_duration,
                curation_criteria={
                    "replay_id": replay_id,
                    "category": category,
                    "min_significance": min_significance,
                    "max_moments": max_moments,
                },
                min_significance=min_significance,
                tags=tags or [],
                metadata=metadata or {},
            )
            self._reels[rid] = reel
            _evict_fifo_dict(self._reels, _MAX_REELS)
            self._record_event(DirectorEventKind.REEL_CURATED, {"reel_id": rid, "moments": len(selected)})
            return reel

    def get_reel(self, reel_id: str) -> Optional[HighlightReel]:
        with self._lock:
            return self._reels.get(reel_id)

    def list_reels(self, limit: int = 100) -> List[HighlightReel]:
        with self._lock:
            return list(self._reels.values())[: max(0, min(limit, len(self._reels)))]

    def remove_reel(self, reel_id: str) -> bool:
        with self._lock:
            existed = self._reels.pop(reel_id, None) is not None
            if existed:
                self._record_event(DirectorEventKind.REEL_REMOVED, {"reel_id": reel_id})
            return existed

    # ------------------------------------------------------------------
    # Tagging
    # ------------------------------------------------------------------

    def tag_moment(
        self,
        moment_id: str,
        kind: str = HighlightTagKind.GAMEPLAY.value,
        value: str = "",
        weight: float = 0.5,
        source: str = "manual",
    ) -> Optional[HighlightTag]:
        with self._lock:
            if moment_id not in self._moments:
                return None
            tag = HighlightTag(
                moment_id=moment_id,
                kind=kind,
                value=value,
                weight=_clamp(weight),
                source=source,
            )
            self._tags.append(tag)
            _evict_fifo_list(self._tags, _MAX_TAGS)
            self._tags_by_moment.setdefault(moment_id, []).append(tag.tag_id)
            self._record_event(DirectorEventKind.TAG_ADDED, {
                "tag_id": tag.tag_id,
                "moment_id": moment_id,
                "value": value,
            })
            return tag

    def list_tags(
        self,
        moment_id: str = "",
        kind: str = "",
        limit: int = 100,
    ) -> List[HighlightTag]:
        with self._lock:
            results: List[HighlightTag] = []
            for tag in self._tags:
                if moment_id and tag.moment_id != moment_id:
                    continue
                if kind and tag.kind != kind:
                    continue
                results.append(tag)
            return results[: max(0, min(limit, len(results)))]

    def remove_tag(self, tag_id: str) -> bool:
        with self._lock:
            for i, tag in enumerate(self._tags):
                if tag.tag_id == tag_id:
                    self._tags.pop(i)
                    moment_id = tag.moment_id
                    if moment_id in self._tags_by_moment:
                        try:
                            self._tags_by_moment[moment_id].remove(tag_id)
                        except ValueError:
                            pass
                    self._record_event(DirectorEventKind.TAG_REMOVED, {"tag_id": tag_id})
                    return True
            return False

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[DirectorEvent]:
        with self._lock:
            return list(self._events)[: max(0, min(limit, len(self._events)))]

    def get_stats(self) -> DirectorStats:
        with self._lock:
            by_category: Dict[str, int] = {}
            by_significance: Dict[str, int] = {}
            total_score = 0.0
            score_count = 0
            for moment in self._moments.values():
                by_category[moment.category] = by_category.get(moment.category, 0) + 1
                by_significance[moment.significance] = by_significance.get(moment.significance, 0) + 1
                if moment.significance_score > 0:
                    total_score += moment.significance_score
                    score_count += 1
            return DirectorStats(
                total_replays=len(self._replays),
                total_moments=len(self._moments),
                total_reels=len(self._reels),
                total_tags=len(self._tags),
                total_analyses=len(self._analyses),
                moments_by_category=by_category,
                moments_by_significance=by_significance,
                avg_significance_score=(total_score / score_count) if score_count else 0.0,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "replays": len(self._replays),
                "moments": len(self._moments),
                "reels": len(self._reels),
                "tags": len(self._tags),
                "analyses": len(self._analyses),
                "events": len(self._events),
            }

    def get_snapshot(self) -> DirectorSnapshot:
        with self._lock:
            return DirectorSnapshot(
                replays={k: v.to_dict() for k, v in self._replays.items()},
                moments={k: v.to_dict() for k, v in self._moments.items()},
                reels={k: v.to_dict() for k, v in self._reels.items()},
                tags=[t.to_dict() for t in self._tags],
                analyses={k: v.to_dict() for k, v in self._analyses.items()},
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._replays.clear()
            self._moments.clear()
            self._reels.clear()
            self._tags.clear()
            self._analyses.clear()
            self._events.clear()
            self._moments_by_replay.clear()
            self._moments_by_category.clear()
            self._tags_by_moment.clear()
            self._seed_defaults()


def get_replay_highlight_director() -> ReplayHighlightDirector:
    """Factory that returns the singleton ReplayHighlightDirector instance."""
    return ReplayHighlightDirector.get_instance()
