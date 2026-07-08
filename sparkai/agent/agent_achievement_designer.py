"""
SparkLabs Agent - AI Achievement Designer

An AI achievement design agent for the SparkLabs AI-native game engine. It
designs achievement definitions with categories, reward structures, rarity
tiers, and difficulty scoring. The designer composes achievement chains,
generates design suggestions from game context, and tracks the lifecycle
of achievement proposals from draft through approval.

Architecture:
  AchievementDesigner (singleton)
    |-- AchievementDesign, AchievementChain, DifficultyAssessment,
       DesignSuggestion, DesignerStats, DesignerSnapshot, DesignerEvent
    |-- AchievementTier, DesignerCategory, DesignerRarity,
       DesignerStatus, DesignerEventKind

Core Capabilities:
  - register_design / get_design / list_designs / update_design /
    remove_design: achievement design lifecycle management.
  - create_chain / get_chain / list_chains / update_chain / remove_chain:
    sequential achievement chains with ordered milestones.
  - add_to_chain / remove_from_chain: add or remove designs from a chain.
  - assess_difficulty: compute a multi-factor difficulty score for a design
    based on rarity, time pressure, skill ceiling, and grind factor.
  - suggest_designs: generate AI design suggestions from a game context
    payload (genre, themes, mechanics, existing designs).
  - approve_design / reject_design: lifecycle transitions with rationale.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`AchievementDesigner.get_instance` or the module-level
:func:`get_achievement_designer` factory.
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

_MAX_DESIGNS: int = 1000
_MAX_CHAINS: int = 500
_MAX_SUGGESTIONS: int = 1000
_MAX_DIFFICULTY_ASSESSMENTS: int = 1000
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


class AchievementTier(Enum):
    """Rarity tiers that gate achievement prestige and reward scaling."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class DesignerCategory(Enum):
    """Categories that classify the gameplay domain of an achievement."""
    COMBAT = "combat"
    EXPLORATION = "exploration"
    COLLECTION = "collection"
    SOCIAL = "social"
    SPEEDRUN = "speedrun"
    CHALLENGE = "challenge"
    MASTERY = "mastery"
    NARRATIVE = "narrative"
    HIDDEN = "hidden"


class DesignerRarity(Enum):
    """Rarity bands that scale difficulty and reward magnitude."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class DesignerStatus(Enum):
    """Lifecycle states for an achievement design proposal."""
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETIRED = "retired"


class DesignerEventKind(Enum):
    """Audit event types emitted by the designer."""
    DESIGN_REGISTERED = "design_registered"
    DESIGN_UPDATED = "design_updated"
    DESIGN_APPROVED = "design_approved"
    DESIGN_REJECTED = "design_rejected"
    DESIGN_RETIRED = "design_retired"
    CHAIN_CREATED = "chain_created"
    CHAIN_UPDATED = "chain_updated"
    CHAIN_REMOVED = "chain_removed"
    SUGGESTION_GENERATED = "suggestion_generated"
    DIFFICULTY_SCORED = "difficulty_scored"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class AchievementDesign:
    """A designed achievement definition with rewards and criteria."""
    design_id: str = field(default_factory=lambda: _new_id("ach"))
    name: str = ""
    description: str = ""
    category: str = DesignerCategory.COMBAT.value
    tier: str = AchievementTier.BRONZE.value
    rarity: str = DesignerRarity.COMMON.value
    status: str = DesignerStatus.DRAFT.value
    hidden: bool = False
    points: int = 10
    criteria: Dict[str, Any] = field(default_factory=dict)
    rewards: Dict[str, Any] = field(default_factory=dict)
    prerequisite_design_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    icon: str = ""
    flavor_text: str = ""
    estimated_completion_rate: float = 0.5
    difficulty_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AchievementChain:
    """An ordered sequence of achievement designs forming a progression."""
    chain_id: str = field(default_factory=lambda: _new_id("chn"))
    name: str = ""
    description: str = ""
    design_ids: List[str] = field(default_factory=list)
    chain_type: str = "linear"
    reward_bonus: float = 0.0
    total_points: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DifficultyAssessment:
    """Multi-factor difficulty assessment for an achievement design."""
    assessment_id: str = field(default_factory=lambda: _new_id("dAs"))
    design_id: str = ""
    rarity_factor: float = 0.0
    time_pressure_factor: float = 0.0
    skill_ceiling_factor: float = 0.0
    grind_factor: float = 0.0
    complexity_factor: float = 0.0
    overall_score: float = 0.0
    assessment_notes: str = ""
    assessed_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DesignSuggestion:
    """An AI-generated suggestion for a new achievement design."""
    suggestion_id: str = field(default_factory=lambda: _new_id("dsg"))
    name: str = ""
    description: str = ""
    category: str = DesignerCategory.COMBAT.value
    tier: str = AchievementTier.BRONZE.value
    rarity: str = DesignerRarity.COMMON.value
    suggested_criteria: Dict[str, Any] = field(default_factory=dict)
    suggested_rewards: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    confidence: float = 0.5
    context_hash: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DesignerStats:
    """Aggregate counters for the designer."""
    total_designs: int = 0
    total_chains: int = 0
    total_suggestions: int = 0
    total_assessments: int = 0
    designs_by_status: Dict[str, int] = field(default_factory=dict)
    designs_by_category: Dict[str, int] = field(default_factory=dict)
    designs_by_tier: Dict[str, int] = field(default_factory=dict)
    avg_difficulty: float = 0.0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DesignerSnapshot:
    """Immutable point-in-time capture of designer state."""
    designs: Dict[str, Any] = field(default_factory=dict)
    chains: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    assessments: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DesignerEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("dev"))
    kind: str = DesignerEventKind.DESIGN_REGISTERED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Achievement Designer Singleton
# ---------------------------------------------------------------------------


# Rarity difficulty weights for scoring
_RARITY_WEIGHTS: Dict[str, float] = {
    DesignerRarity.COMMON.value: 0.2,
    DesignerRarity.UNCOMMON.value: 0.35,
    DesignerRarity.RARE.value: 0.5,
    DesignerRarity.EPIC.value: 0.7,
    DesignerRarity.LEGENDARY.value: 0.85,
    DesignerRarity.MYTHIC.value: 1.0,
}

# Tier difficulty weights for scoring
_TIER_WEIGHTS: Dict[str, float] = {
    AchievementTier.BRONZE.value: 0.2,
    AchievementTier.SILVER.value: 0.4,
    AchievementTier.GOLD.value: 0.6,
    AchievementTier.PLATINUM.value: 0.8,
    AchievementTier.DIAMOND.value: 1.0,
}


class AchievementDesigner:
    """Singleton agent that designs achievements with AI-driven suggestions.

    The designer maintains achievement designs (proposed definitions with
    criteria and rewards), achievement chains (ordered progression
    sequences), difficulty assessments (multi-factor scoring), and design
    suggestions (AI-generated proposals from game context). It tracks the
    lifecycle of designs from draft through approval.
    """

    _instance: Optional["AchievementDesigner"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._designs: Dict[str, AchievementDesign] = {}
        self._chains: Dict[str, AchievementChain] = {}
        self._suggestions: List[DesignSuggestion] = []
        self._assessments: Dict[str, DifficultyAssessment] = {}
        self._events: List[DesignerEvent] = []
        self._designs_by_category: Dict[str, List[str]] = {}
        self._designs_by_tier: Dict[str, List[str]] = {}
        self._designs_by_status: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AchievementDesigner":
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
        """Seed a small set of default achievement designs and a chain."""
        defaults = [
            ("ach_first_blood", "First Blood", "Defeat your first enemy in combat.",
             DesignerCategory.COMBAT, AchievementTier.BRONZE, DesignerRarity.COMMON,
             10, False, {"action": "defeat_enemy", "count": 1},
             {"xp": 50, "gold": 10}, ["combat", "starter"]),
            ("ach_explorer", "Trailblazer", "Discover 10 unique locations.",
             DesignerCategory.EXPLORATION, AchievementTier.SILVER, DesignerRarity.UNCOMMON,
             25, False, {"action": "discover_location", "count": 10},
             {"xp": 200, "gold": 50}, ["exploration", "discovery"]),
            ("ach_collector", "Pack Rat", "Collect 50 unique items.",
             DesignerCategory.COLLECTION, AchievementTier.SILVER, DesignerRarity.UNCOMMON,
             30, False, {"action": "collect_item", "count": 50},
             {"xp": 250, "gold": 75}, ["collection", "items"]),
            ("ach_master", "Combat Master", "Defeat 1000 enemies without falling.",
             DesignerCategory.MASTERY, AchievementTier.PLATINUM, DesignerRarity.LEGENDARY,
             200, False, {"action": "defeat_enemy", "count": 1000, "no_death": True},
             {"xp": 5000, "gold": 2000, "title": "Combat Master"}, ["combat", "mastery"]),
            ("ach_hidden", "???", "Hidden achievement - discover it to reveal.",
             DesignerCategory.HIDDEN, AchievementTier.GOLD, DesignerRarity.EPIC,
             75, True, {"action": "secret_trigger"},
             {"xp": 1000, "gold": 500}, ["hidden", "secret"]),
        ]
        for did, name, desc, cat, tier, rarity, pts, hidden, criteria, rewards, tags in defaults:
            design = AchievementDesign(
                design_id=did,
                name=name,
                description=desc,
                category=cat.value,
                tier=tier.value,
                rarity=rarity.value,
                status=DesignerStatus.APPROVED.value,
                hidden=hidden,
                points=pts,
                criteria=criteria,
                rewards=rewards,
                tags=tags,
                estimated_completion_rate=_clamp(1.0 - _RARITY_WEIGHTS[rarity.value]),
            )
            self._designs[did] = design
            self._index_design(did, cat.value, tier.value, DesignerStatus.APPROVED.value)
            self._record_event(DesignerEventKind.DESIGN_REGISTERED, {"design_id": did, "name": name})

        # Seed a chain
        chain = AchievementChain(
            chain_id="chn_combat_progression",
            name="Combat Progression",
            description="Progress from first blood to combat mastery",
            design_ids=["ach_first_blood", "ach_master"],
            chain_type="linear",
            reward_bonus=0.1,
            total_points=210,
            tags=["combat", "progression"],
        )
        self._chains[chain.chain_id] = chain
        self._record_event(DesignerEventKind.CHAIN_CREATED, {"chain_id": chain.chain_id})

    def _index_design(self, design_id: str, category: str, tier: str, status: str) -> None:
        self._designs_by_category.setdefault(category, []).append(design_id)
        self._designs_by_tier.setdefault(tier, []).append(design_id)
        self._designs_by_status.setdefault(status, []).append(design_id)

    def _unindex_design(self, design_id: str, category: str, tier: str, status: str) -> None:
        if category in self._designs_by_category:
            try:
                self._designs_by_category[category].remove(design_id)
            except ValueError:
                pass
        if tier in self._designs_by_tier:
            try:
                self._designs_by_tier[tier].remove(design_id)
            except ValueError:
                pass
        if status in self._designs_by_status:
            try:
                self._designs_by_status[status].remove(design_id)
            except ValueError:
                pass

    def _record_event(self, kind: DesignerEventKind, payload: Dict[str, Any]) -> None:
        event = DesignerEvent(kind=kind.value, payload=payload)
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Design Lifecycle
    # ------------------------------------------------------------------

    def register_design(
        self,
        design_id: str = "",
        name: str = "",
        description: str = "",
        category: str = DesignerCategory.COMBAT.value,
        tier: str = AchievementTier.BRONZE.value,
        rarity: str = DesignerRarity.COMMON.value,
        status: str = DesignerStatus.DRAFT.value,
        hidden: bool = False,
        points: int = 10,
        criteria: Optional[Dict[str, Any]] = None,
        rewards: Optional[Dict[str, Any]] = None,
        prerequisite_design_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        icon: str = "",
        flavor_text: str = "",
        estimated_completion_rate: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AchievementDesign:
        with self._lock:
            did = design_id or _new_id("ach")
            if did in self._designs:
                return self._designs[did]
            design = AchievementDesign(
                design_id=did,
                name=name,
                description=description,
                category=category,
                tier=tier,
                rarity=rarity,
                status=status,
                hidden=hidden,
                points=_safe_int(points, 10),
                criteria=criteria or {},
                rewards=rewards or {},
                prerequisite_design_ids=prerequisite_design_ids or [],
                tags=tags or [],
                icon=icon,
                flavor_text=flavor_text,
                estimated_completion_rate=_clamp(estimated_completion_rate),
                metadata=metadata or {},
            )
            self._designs[did] = design
            _evict_fifo_dict(self._designs, _MAX_DESIGNS)
            self._index_design(did, category, tier, status)
            self._record_event(DesignerEventKind.DESIGN_REGISTERED, {"design_id": did, "name": name})
            return design

    def get_design(self, design_id: str) -> Optional[AchievementDesign]:
        with self._lock:
            return self._designs.get(design_id)

    def list_designs(
        self,
        category: str = "",
        tier: str = "",
        rarity: str = "",
        status: str = "",
        hidden: Optional[bool] = None,
        limit: int = 100,
    ) -> List[AchievementDesign]:
        with self._lock:
            results: List[AchievementDesign] = []
            for design in self._designs.values():
                if category and design.category != category:
                    continue
                if tier and design.tier != tier:
                    continue
                if rarity and design.rarity != rarity:
                    continue
                if status and design.status != status:
                    continue
                if hidden is not None and design.hidden != hidden:
                    continue
                results.append(design)
            return results[: max(0, min(limit, len(results)))]

    def update_design(self, design_id: str, **kwargs: Any) -> Optional[AchievementDesign]:
        with self._lock:
            design = self._designs.get(design_id)
            if design is None:
                return None
            old_category = design.category
            old_tier = design.tier
            old_status = design.status
            for key, value in kwargs.items():
                if hasattr(design, key) and key != "design_id" and key != "created_at":
                    setattr(design, key, value)
            design.updated_at = _now()
            if design.category != old_category or design.tier != old_tier or design.status != old_status:
                self._unindex_design(design_id, old_category, old_tier, old_status)
                self._index_design(design_id, design.category, design.tier, design.status)
            self._record_event(DesignerEventKind.DESIGN_UPDATED, {"design_id": design_id})
            return design

    def remove_design(self, design_id: str) -> bool:
        with self._lock:
            design = self._designs.pop(design_id, None)
            if design is None:
                return False
            self._unindex_design(design_id, design.category, design.tier, design.status)
            # Remove from any chains
            for chain in self._chains.values():
                if design_id in chain.design_ids:
                    chain.design_ids = [d for d in chain.design_ids if d != design_id]
                    chain.updated_at = _now()
            self._record_event(DesignerEventKind.DESIGN_RETIRED, {"design_id": design_id})
            return True

    # ------------------------------------------------------------------
    # Chain Management
    # ------------------------------------------------------------------

    def create_chain(
        self,
        chain_id: str = "",
        name: str = "",
        description: str = "",
        design_ids: Optional[List[str]] = None,
        chain_type: str = "linear",
        reward_bonus: float = 0.0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AchievementChain:
        with self._lock:
            cid = chain_id or _new_id("chn")
            if cid in self._chains:
                return self._chains[cid]
            valid_design_ids = [d for d in (design_ids or []) if d in self._designs]
            total_points = sum(self._designs[d].points for d in valid_design_ids if d in self._designs)
            chain = AchievementChain(
                chain_id=cid,
                name=name,
                description=description,
                design_ids=valid_design_ids,
                chain_type=chain_type,
                reward_bonus=_safe_float(reward_bonus),
                total_points=total_points,
                tags=tags or [],
                metadata=metadata or {},
            )
            self._chains[cid] = chain
            _evict_fifo_dict(self._chains, _MAX_CHAINS)
            self._record_event(DesignerEventKind.CHAIN_CREATED, {"chain_id": cid, "name": name})
            return chain

    def get_chain(self, chain_id: str) -> Optional[AchievementChain]:
        with self._lock:
            return self._chains.get(chain_id)

    def list_chains(self, limit: int = 100) -> List[AchievementChain]:
        with self._lock:
            return list(self._chains.values())[: max(0, min(limit, len(self._chains)))]

    def update_chain(self, chain_id: str, **kwargs: Any) -> Optional[AchievementChain]:
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return None
            for key, value in kwargs.items():
                if hasattr(chain, key) and key not in ("chain_id", "created_at"):
                    if key == "design_ids":
                        value = [d for d in (value or []) if d in self._designs]
                    setattr(chain, key, value)
            chain.total_points = sum(self._designs[d].points for d in chain.design_ids if d in self._designs)
            chain.updated_at = _now()
            self._record_event(DesignerEventKind.CHAIN_UPDATED, {"chain_id": chain_id})
            return chain

    def remove_chain(self, chain_id: str) -> bool:
        with self._lock:
            existed = self._chains.pop(chain_id, None) is not None
            if existed:
                self._record_event(DesignerEventKind.CHAIN_REMOVED, {"chain_id": chain_id})
            return existed

    def add_to_chain(self, chain_id: str, design_id: str, position: int = -1) -> Optional[AchievementChain]:
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return None
            if design_id not in self._designs:
                return None
            if design_id not in chain.design_ids:
                if position < 0 or position >= len(chain.design_ids):
                    chain.design_ids.append(design_id)
                else:
                    chain.design_ids.insert(position, design_id)
                chain.total_points = sum(self._designs[d].points for d in chain.design_ids if d in self._designs)
                chain.updated_at = _now()
                self._record_event(DesignerEventKind.CHAIN_UPDATED, {"chain_id": chain_id, "added": design_id})
            return chain

    def remove_from_chain(self, chain_id: str, design_id: str) -> Optional[AchievementChain]:
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return None
            if design_id in chain.design_ids:
                chain.design_ids = [d for d in chain.design_ids if d != design_id]
                chain.total_points = sum(self._designs[d].points for d in chain.design_ids if d in self._designs)
                chain.updated_at = _now()
                self._record_event(DesignerEventKind.CHAIN_UPDATED, {"chain_id": chain_id, "removed": design_id})
            return chain

    # ------------------------------------------------------------------
    # Difficulty Assessment
    # ------------------------------------------------------------------

    def assess_difficulty(
        self,
        design_id: str,
        time_pressure: float = 0.0,
        skill_ceiling: float = 0.0,
        grind_factor: float = 0.0,
        complexity: float = 0.0,
        notes: str = "",
    ) -> Optional[DifficultyAssessment]:
        with self._lock:
            design = self._designs.get(design_id)
            if design is None:
                return None
            rarity_factor = _RARITY_WEIGHTS.get(design.rarity, 0.5)
            tp = _clamp(time_pressure)
            sc = _clamp(skill_ceiling)
            gf = _clamp(grind_factor)
            cx = _clamp(complexity)
            overall = _clamp(
                0.30 * rarity_factor
                + 0.20 * tp
                + 0.25 * sc
                + 0.15 * gf
                + 0.10 * cx
            )
            assessment = DifficultyAssessment(
                design_id=design_id,
                rarity_factor=rarity_factor,
                time_pressure_factor=tp,
                skill_ceiling_factor=sc,
                grind_factor=gf,
                complexity_factor=cx,
                overall_score=overall,
                assessment_notes=notes,
            )
            self._assessments[assessment.assessment_id] = assessment
            _evict_fifo_dict(self._assessments, _MAX_DIFFICULTY_ASSESSMENTS)
            design.difficulty_score = overall
            design.updated_at = _now()
            self._record_event(DesignerEventKind.DIFFICULTY_SCORED, {
                "design_id": design_id,
                "score": overall,
            })
            return assessment

    def get_assessment(self, assessment_id: str) -> Optional[DifficultyAssessment]:
        with self._lock:
            return self._assessments.get(assessment_id)

    def list_assessments(self, design_id: str = "", limit: int = 100) -> List[DifficultyAssessment]:
        with self._lock:
            results = [a for a in self._assessments.values() if not design_id or a.design_id == design_id]
            return results[: max(0, min(limit, len(results)))]

    # ------------------------------------------------------------------
    # Design Suggestions
    # ------------------------------------------------------------------

    def suggest_designs(
        self,
        context: Optional[Dict[str, Any]] = None,
        count: int = 5,
    ) -> List[DesignSuggestion]:
        with self._lock:
            ctx = context or {}
            genre = ctx.get("genre", "action")
            themes = ctx.get("themes", ["combat", "exploration"])
            mechanics = ctx.get("mechanics", ["combat"])
            existing_count = len(self._designs)
            suggestions: List[DesignSuggestion] = []

            # Generate suggestions based on themes and mechanics
            suggestion_templates: List[Tuple[str, str, str, DesignerCategory, AchievementTier, DesignerRarity, Dict[str, Any], Dict[str, Any], str]] = [
                ("Weapon Virtuoso", "Master every weapon type in the game",
                 "Encourages players to explore all weapon mechanics",
                 DesignerCategory.MASTERY, AchievementTier.GOLD, DesignerRarity.EPIC,
                 {"action": "master_weapon", "count": "all"},
                 {"xp": 2000, "title": "Weapon Virtuoso"},
                 "Mastery achievements drive long-term engagement with core mechanics"),
                ("Cartographer", "Reveal the entire world map",
                 "Rewards thorough exploration of the game world",
                 DesignerCategory.EXPLORATION, AchievementTier.SILVER, DesignerRarity.UNCOMMON,
                 {"action": "reveal_map", "coverage": 1.0},
                 {"xp": 500, "gold": 200},
                 "Exploration achievements extend playtime and discoverability"),
                ("Flawless Victory", "Defeat a boss without taking damage",
                 "High-skill achievement for expert players",
                 DesignerCategory.CHALLENGE, AchievementTier.PLATINUM, DesignerRarity.LEGENDARY,
                 {"action": "defeat_boss", "no_damage": True},
                 {"xp": 3000, "gold": 1000, "title": "Flawless"},
                 "Challenge achievements create aspirational goals and community bragging rights"),
                ("Social Butterfly", "Form a party with 5 different players",
                 "Encourages social interaction and community building",
                 DesignerCategory.SOCIAL, AchievementTier.BRONZE, DesignerRarity.COMMON,
                 {"action": "party_with_player", "count": 5},
                 {"xp": 100, "gold": 50},
                 "Social achievements foster community and retention"),
                ("Speed Demon", "Complete the main campaign in under 5 hours",
                 "Rewards skilled and efficient playthroughs",
                 DesignerCategory.SPEEDRUN, AchievementTier.DIAMOND, DesignerRarity.MYTHIC,
                 {"action": "complete_campaign", "time_limit_hours": 5},
                 {"xp": 5000, "gold": 3000, "title": "Speed Demon"},
                 "Speedrun achievements create replay value and community competition"),
                ("Lore Master", "Discover all hidden lore entries",
                 "Rewards deep engagement with narrative content",
                 DesignerCategory.NARRATIVE, AchievementTier.GOLD, DesignerRarity.EPIC,
                 {"action": "discover_lore", "count": "all"},
                 {"xp": 1500, "gold": 500},
                 "Narrative achievements deepen player investment in the world"),
                ("The Collector", "Obtain one of every collectible item",
                 "Drives completionist behavior and content discovery",
                 DesignerCategory.COLLECTION, AchievementTier.PLATINUM, DesignerRarity.LEGENDARY,
                 {"action": "collect_item", "count": "all"},
                 {"xp": 4000, "gold": 2000, "title": "Collector"},
                 "Collection achievements maximize content utilization"),
                ("Untouchable", "Survive 10 minutes in survival mode without healing",
                 "Tests player skill and game knowledge",
                 DesignerCategory.CHALLENGE, AchievementTier.GOLD, DesignerRarity.EPIC,
                 {"action": "survive_duration", "minutes": 10, "no_heal": True},
                 {"xp": 2500, "gold": 800},
                 "Survival challenges create tension and showcase mastery"),
            ]

            # Filter by themes/mechanics if provided
            for name, desc, rationale, cat, tier, rarity, criteria, rewards, reason in suggestion_templates:
                if len(suggestions) >= count:
                    break
                # Boost confidence if themes match
                confidence = 0.5
                cat_value = cat.value
                if cat_value in themes or any(t in cat_value for t in themes):
                    confidence = 0.8
                if any(m in cat_value for m in mechanics):
                    confidence = min(1.0, confidence + 0.1)

                suggestion = DesignSuggestion(
                    name=name,
                    description=desc,
                    category=cat_value,
                    tier=tier.value,
                    rarity=rarity.value,
                    suggested_criteria=criteria,
                    suggested_rewards=rewards,
                    rationale=rationale,
                    confidence=confidence,
                    context_hash=f"{genre}:{','.join(sorted(themes))}",
                )
                suggestions.append(suggestion)
                self._suggestions.append(suggestion)
                _evict_fifo_list(self._suggestions, _MAX_SUGGESTIONS)
                self._record_event(DesignerEventKind.SUGGESTION_GENERATED, {
                    "name": name,
                    "confidence": confidence,
                })

            return suggestions

    def list_suggestions(self, limit: int = 100) -> List[DesignSuggestion]:
        with self._lock:
            return list(self._suggestions)[: max(0, min(limit, len(self._suggestions)))]

    # ------------------------------------------------------------------
    # Lifecycle Transitions
    # ------------------------------------------------------------------

    def approve_design(self, design_id: str, rationale: str = "") -> Optional[AchievementDesign]:
        with self._lock:
            design = self._designs.get(design_id)
            if design is None:
                return None
            old_status = design.status
            design.status = DesignerStatus.APPROVED.value
            design.updated_at = _now()
            if old_status != design.status:
                self._unindex_design(design_id, design.category, design.tier, old_status)
                self._index_design(design_id, design.category, design.tier, design.status)
            self._record_event(DesignerEventKind.DESIGN_APPROVED, {
                "design_id": design_id,
                "rationale": rationale,
            })
            return design

    def reject_design(self, design_id: str, rationale: str = "") -> Optional[AchievementDesign]:
        with self._lock:
            design = self._designs.get(design_id)
            if design is None:
                return None
            old_status = design.status
            design.status = DesignerStatus.REJECTED.value
            design.updated_at = _now()
            if old_status != design.status:
                self._unindex_design(design_id, design.category, design.tier, old_status)
                self._index_design(design_id, design.category, design.tier, design.status)
            self._record_event(DesignerEventKind.DESIGN_REJECTED, {
                "design_id": design_id,
                "rationale": rationale,
            })
            return design

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[DesignerEvent]:
        with self._lock:
            return list(self._events)[: max(0, min(limit, len(self._events)))]

    def get_stats(self) -> DesignerStats:
        with self._lock:
            by_status: Dict[str, int] = {}
            by_category: Dict[str, int] = {}
            by_tier: Dict[str, int] = {}
            total_difficulty = 0.0
            difficulty_count = 0
            for design in self._designs.values():
                by_status[design.status] = by_status.get(design.status, 0) + 1
                by_category[design.category] = by_category.get(design.category, 0) + 1
                by_tier[design.tier] = by_tier.get(design.tier, 0) + 1
                if design.difficulty_score > 0:
                    total_difficulty += design.difficulty_score
                    difficulty_count += 1
            return DesignerStats(
                total_designs=len(self._designs),
                total_chains=len(self._chains),
                total_suggestions=len(self._suggestions),
                total_assessments=len(self._assessments),
                designs_by_status=by_status,
                designs_by_category=by_category,
                designs_by_tier=by_tier,
                avg_difficulty=(total_difficulty / difficulty_count) if difficulty_count else 0.0,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "designs": len(self._designs),
                "chains": len(self._chains),
                "suggestions": len(self._suggestions),
                "assessments": len(self._assessments),
                "events": len(self._events),
            }

    def get_snapshot(self) -> DesignerSnapshot:
        with self._lock:
            return DesignerSnapshot(
                designs={k: v.to_dict() for k, v in self._designs.items()},
                chains={k: v.to_dict() for k, v in self._chains.items()},
                suggestions=[s.to_dict() for s in self._suggestions],
                assessments={k: v.to_dict() for k, v in self._assessments.items()},
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._designs.clear()
            self._chains.clear()
            self._suggestions.clear()
            self._assessments.clear()
            self._events.clear()
            self._designs_by_category.clear()
            self._designs_by_tier.clear()
            self._designs_by_status.clear()
            self._seed_defaults()


def get_achievement_designer() -> AchievementDesigner:
    """Factory that returns the singleton AchievementDesigner instance."""
    return AchievementDesigner.get_instance()
