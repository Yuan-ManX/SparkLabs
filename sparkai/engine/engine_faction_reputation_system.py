"""
SparkLabs Engine - Faction & Reputation System

Manages NPC factions, player reputation standings, faction relationships,
and reputation-based gameplay consequences. Players build or lose standing
with factions through quests, kills, donations, and diplomatic actions.
Reputation tiers unlock rewards, change NPC hostility states, and gate
access to faction-specific content.

Architecture:
  FactionReputationSystem (singleton)
    |-- FactionTier, FactionAttitude, FactionRelation, ReputationEventKind
    |-- FactionDefinition, FactionReward, PlayerReputation, ReputationEntry,
       DiplomaticAction, FactionWar, FactionReputationConfig, FactionStats,
       FactionSnapshot, FactionEvent
    |-- get_faction_reputation_system

Core Capabilities:
  - register_faction / remove_faction / get_faction / list_factions
  - register_reward / remove_reward / get_reward / list_rewards
  - gain_reputation / lose_reputation / set_reputation / get_reputation
  - list_player_reputations / get_reputation_tier
  - register_relation / get_relation / list_relations
  - create_diplomatic_action / accept_diplomatic_action / reject_diplomatic_action
  - declare_war / end_war / get_war / list_wars
  - check_hostility / get_available_rewards / claim_reward
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`FactionReputationSystem.get_instance` or the module-level
:func:`get_faction_reputation_system` factory.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_FACTIONS: int = 200
_MAX_REWARDS: int = 1000
_MAX_PLAYER_REPUTATIONS: int = 100000
_MAX_RELATIONS: int = 5000
_MAX_DIPLOMATIC_ACTIONS: int = 5000
_MAX_WARS: int = 500
_MAX_ENTRIES: int = 50000
_MAX_EVENTS: int = 10000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


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


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _dataclass_to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "__dataclass_fields__"):
                result[k] = _dataclass_to_dict(v)
            elif hasattr(v, "to_dict") and callable(v.to_dict):
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
# Enums
# ---------------------------------------------------------------------------

class FactionTier(str, Enum):
    """Reputation tier thresholds."""
    EXALTED = "exalted"
    REVERED = "revered"
    HONORED = "honored"
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    UNFRIENDLY = "unfriendly"
    HOSTILE = "hostile"
    HATED = "hated"


class FactionAttitude(str, Enum):
    """Default attitude of a faction toward players."""
    ALLY = "ally"
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    WARY = "wary"
    HOSTILE = "hostile"
    ENEMY = "enemy"


class FactionRelation(str, Enum):
    """Relationship between two factions."""
    ALLIED = "allied"
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    RIVAL = "rival"
    AT_WAR = "at_war"


class DiplomaticActionType(str, Enum):
    """Types of diplomatic actions between factions."""
    PEACE_TREATY = "peace_treaty"
    TRADE_AGREEMENT = "trade_agreement"
    MILITARY_ALLIANCE = "military_alliance"
    NON_AGGRESSION = "non_aggression"
    CESSATION = "cessation"
    EMBARGO = "embargo"


class DiplomaticActionStatus(str, Enum):
    """Status of a diplomatic action."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class FactionWarStatus(str, Enum):
    """Status of a faction war."""
    DECLARED = "declared"
    ACTIVE = "active"
    CEASEFIRE = "ceasefire"
    ENDED = "ended"
    CANCELLED = "cancelled"


class FactionWarOutcome(str, Enum):
    """Outcome of a faction war."""
    PENDING = "pending"
    FACTION_A_WIN = "faction_a_win"
    FACTION_B_WIN = "faction_b_win"
    DRAW = "draw"
    WHITE_PEACE = "white_peace"


class ReputationEventKind(str, Enum):
    """Audit event types emitted by the faction reputation system."""
    FACTION_REGISTERED = "faction_registered"
    FACTION_REMOVED = "faction_removed"
    REPUTATION_GAINED = "reputation_gained"
    REPUTATION_LOST = "reputation_lost"
    REPUTATION_SET = "reputation_set"
    REWARD_REGISTERED = "reward_registered"
    REWARD_REMOVED = "reward_removed"
    REWARD_CLAIMED = "reward_claimed"
    RELATION_REGISTERED = "relation_registered"
    DIPLOMATIC_CREATED = "diplomatic_created"
    DIPLOMATIC_ACCEPTED = "diplomatic_accepted"
    DIPLOMATIC_REJECTED = "diplomatic_rejected"
    WAR_DECLARED = "war_declared"
    WAR_STARTED = "war_started"
    WAR_ENDED = "war_ended"
    WAR_CANCELLED = "war_cancelled"
    TIER_CHANGED = "tier_changed"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Reputation Tier Thresholds
# ---------------------------------------------------------------------------

TIER_THRESHOLDS: Dict[str, Tuple[float, float]] = {
    FactionTier.HATED.value: (-100000, -10000),
    FactionTier.HOSTILE.value: (-10000, -3000),
    FactionTier.UNFRIENDLY.value: (-3000, -500),
    FactionTier.NEUTRAL.value: (-500, 500),
    FactionTier.FRIENDLY.value: (500, 3000),
    FactionTier.HONORED.value: (3000, 9000),
    FactionTier.REVERED.value: (9000, 21000),
    FactionTier.EXALTED.value: (21000, 100000),
}


def _tier_from_reputation(rep: float) -> str:
    """Determine the reputation tier from a raw reputation value."""
    for tier_name in [
        FactionTier.HATED.value,
        FactionTier.HOSTILE.value,
        FactionTier.UNFRIENDLY.value,
        FactionTier.NEUTRAL.value,
        FactionTier.FRIENDLY.value,
        FactionTier.HONORED.value,
        FactionTier.REVERED.value,
        FactionTier.EXALTED.value,
    ]:
        lo, hi = TIER_THRESHOLDS[tier_name]
        if lo <= rep < hi:
            return tier_name
    if rep >= 21000:
        return FactionTier.EXALTED.value
    return FactionTier.HATED.value


def _is_hostile_tier(tier: str) -> bool:
    return tier in (FactionTier.HATED.value, FactionTier.HOSTILE.value)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class FactionReward:
    """A reward unlocked at a specific reputation tier."""
    reward_id: str
    faction_id: str
    name: str
    description: str = ""
    required_tier: str = FactionTier.FRIENDLY.value
    reward_type: str = "item"
    reward_data: Dict[str, Any] = field(default_factory=dict)
    one_time: bool = True
    claimed_by: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FactionDefinition:
    """An NPC faction definition."""
    faction_id: str
    name: str
    description: str = ""
    default_attitude: str = FactionAttitude.NEUTRAL.value
    base_reputation: float = 0.0
    icon: str = ""
    color: str = ""
    leader_npc: str = ""
    headquarters_location: str = ""
    is_hostile_by_default: bool = False
    rewards: List[FactionReward] = field(default_factory=list)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ReputationEntry:
    """A single reputation change record."""
    entry_id: str
    faction_id: str
    player_id: str
    change: float = 0.0
    reason: str = ""
    source: str = ""
    timestamp: float = field(default_factory=_now)
    old_value: float = 0.0
    new_value: float = 0.0
    old_tier: str = FactionTier.NEUTRAL.value
    new_tier: str = FactionTier.NEUTRAL.value

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerReputation:
    """A player's standing with a faction."""
    faction_id: str
    player_id: str
    reputation: float = 0.0
    tier: str = FactionTier.NEUTRAL.value
    lifetime_gained: float = 0.0
    lifetime_lost: float = 0.0
    total_interactions: int = 0
    last_interaction: float = 0.0
    claimed_rewards: List[str] = field(default_factory=list)
    is_hostile: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FactionRelationEntry:
    """Relationship between two factions."""
    relation_id: str
    faction_a: str
    faction_b: str
    relation: str = FactionRelation.NEUTRAL.value
    strength: float = 0.0
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DiplomaticAction:
    """A diplomatic action proposed between factions."""
    action_id: str
    action_type: str = DiplomaticActionType.PEACE_TREATY.value
    proposer_faction: str = ""
    target_faction: str = ""
    player_id: str = ""
    description: str = ""
    status: str = DiplomaticActionStatus.PENDING.value
    proposed_at: float = field(default_factory=_now)
    resolved_at: float = 0.0
    expires_at: float = 0.0
    terms: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FactionWar:
    """A war between two factions."""
    war_id: str
    faction_a: str
    faction_b: str
    status: str = FactionWarStatus.DECLARED.value
    outcome: str = FactionWarOutcome.PENDING.value
    declared_at: float = field(default_factory=_now)
    started_at: float = 0.0
    ended_at: float = 0.0
    declarer_player: str = ""
    faction_a_score: float = 0.0
    faction_b_score: float = 0.0
    casualties_a: int = 0
    casualties_b: int = 0
    terms: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FactionReputationConfig:
    """Global tuning parameters."""
    max_factions: int = 200
    max_rewards: int = 1000
    max_player_reputations: int = 100000
    max_relations: int = 5000
    max_diplomatic_actions: int = 5000
    max_wars: int = 500
    max_entries: int = 50000
    reputation_cap: float = 100000.0
    reputation_floor: float = -100000.0
    decay_rate: float = 0.0
    decay_interval: float = 86400.0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FactionStats:
    """Aggregate statistics."""
    total_factions: int = 0
    total_rewards: int = 0
    total_player_reputations: int = 0
    total_relations: int = 0
    total_diplomatic_actions: int = 0
    pending_diplomatic_actions: int = 0
    total_wars: int = 0
    active_wars: int = 0
    total_reputation_gained: float = 0.0
    total_reputation_lost: float = 0.0
    hostile_factions: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FactionSnapshot:
    """Full state snapshot."""
    factions: List[Dict[str, Any]] = field(default_factory=list)
    relations: List[Dict[str, Any]] = field(default_factory=list)
    wars: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FactionEvent:
    """An audit event."""
    event_id: str
    kind: str
    timestamp: float
    faction_id: str = ""
    player_id: str = ""
    target_faction_id: str = ""
    war_id: str = ""
    action_id: str = ""
    reward_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Faction Reputation System
# ---------------------------------------------------------------------------

class FactionReputationSystem:
    """Manages NPC factions, player reputation, and faction diplomacy."""

    _instance: Optional["FactionReputationSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._factions: Dict[str, FactionDefinition] = {}
        self._rewards: Dict[str, FactionReward] = {}
        self._player_reps: Dict[str, PlayerReputation] = {}
        self._relations: Dict[str, FactionRelationEntry] = {}
        self._diplomatic_actions: Dict[str, DiplomaticAction] = {}
        self._wars: Dict[str, FactionWar] = {}
        self._entries: List[ReputationEntry] = []
        self._events: List[FactionEvent] = []
        self._stats = FactionStats()
        self._config = FactionReputationConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._entry_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "FactionReputationSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed initial factions, rewards, relations, and player reputations."""
        with self._init_lock:
            if self._initialized:
                return

            # Faction 1: Iron Guard (city guards, law enforcement)
            f1 = FactionDefinition(
                faction_id="faction_iron_guard",
                name="Iron Guard",
                description="The city guard faction, upholding law and order.",
                default_attitude=FactionAttitude.NEUTRAL.value,
                base_reputation=0.0,
                icon="shield_gold",
                color="#c0c0c0",
                leader_npc="npc_commander_steel",
                headquarters_location="city_barracks",
                is_hostile_by_default=False,
            )
            f1.rewards = [
                FactionReward(
                    reward_id="reward_guard_discount",
                    faction_id="faction_iron_guard",
                    name="Guard Discount",
                    description="10% discount at guard-aligned merchants.",
                    required_tier=FactionTier.FRIENDLY.value,
                    reward_type="discount",
                    reward_data={"discount_percent": 10},
                ),
                FactionReward(
                    reward_id="reward_guard_aura",
                    faction_id="faction_iron_guard",
                    name="Guard Aura",
                    description="Permanent defense buff when in city limits.",
                    required_tier=FactionTier.HONORED.value,
                    reward_type="buff",
                    reward_data={"buff_id": "buff_guard_aura", "defense_bonus": 15},
                ),
                FactionReward(
                    reward_id="reward_guard_mount",
                    faction_id="faction_iron_guard",
                    name="Guard Steed",
                    description="Unlock the Iron Guard stallion mount.",
                    required_tier=FactionTier.REVERED.value,
                    reward_type="mount",
                    reward_data={"mount_id": "mount_iron_steed"},
                ),
            ]
            self._factions[f1.faction_id] = f1
            for rw in f1.rewards:
                self._rewards[rw.reward_id] = rw

            # Faction 2: Shadow Syndicate (thieves, underground)
            f2 = FactionDefinition(
                faction_id="faction_shadow_syndicate",
                name="Shadow Syndicate",
                description="An underground network of thieves and smugglers.",
                default_attitude=FactionAttitude.WARY.value,
                base_reputation=-500.0,
                icon="dagger_purple",
                color="#4a0e4e",
                leader_npc="npc_master_shade",
                headquarters_location="sewer_hideout",
                is_hostile_by_default=False,
            )
            f2.rewards = [
                FactionReward(
                    reward_id="reward_syndicate_lockpick",
                    faction_id="faction_shadow_syndicate",
                    name="Master Lockpick",
                    description="Grants a reusable master lockpick.",
                    required_tier=FactionTier.FRIENDLY.value,
                    reward_type="item",
                    reward_data={"item_id": "item_master_lockpick"},
                ),
                FactionReward(
                    reward_id="reward_syndicate_smuggle",
                    faction_id="faction_shadow_syndicate",
                    name="Smuggler Routes",
                    description="Unlock hidden trade routes for better prices.",
                    required_tier=FactionTier.HONORED.value,
                    reward_type="unlock",
                    reward_data={"route_id": "route_smuggler_pass"},
                ),
            ]
            self._factions[f2.faction_id] = f2
            for rw in f2.rewards:
                self._rewards[rw.reward_id] = rw

            # Faction 3: Arcane Circle (mages, scholars)
            f3 = FactionDefinition(
                faction_id="faction_arcane_circle",
                name="Arcane Circle",
                description="A council of mages and scholars pursuing magical knowledge.",
                default_attitude=FactionAttitude.FRIENDLY.value,
                base_reputation=500.0,
                icon="rune_blue",
                color="#1a5276",
                leader_npc="npc_archmage_eldric",
                headquarters_location="tower_of_wisdom",
                is_hostile_by_default=False,
            )
            f3.rewards = [
                FactionReward(
                    reward_id="reward_arcane_scroll",
                    faction_id="faction_arcane_circle",
                    name="Free Spell Scroll",
                    description="Receive a free spell scroll each week.",
                    required_tier=FactionTier.FRIENDLY.value,
                    reward_type="item",
                    reward_data={"item_id": "scroll_random_spell"},
                ),
                FactionReward(
                    reward_id="reward_arcane_library",
                    faction_id="faction_arcane_circle",
                    name="Library Access",
                    description="Access to the restricted arcane library.",
                    required_tier=FactionTier.HONORED.value,
                    reward_type="unlock",
                    reward_data={"area_id": "area_restricted_library"},
                ),
                FactionReward(
                    reward_id="reward_arcane_portal",
                    faction_id="faction_arcane_circle",
                    name="Portal Network",
                    description="Unlock personal portal network between major cities.",
                    required_tier=FactionTier.EXALTED.value,
                    reward_type="ability",
                    reward_data={"ability_id": "ability_portal_network"},
                ),
            ]
            self._factions[f3.faction_id] = f3
            for rw in f3.rewards:
                self._rewards[rw.reward_id] = rw

            # Faction 4: Crimson Horde (hostile raiders)
            f4 = FactionDefinition(
                faction_id="faction_crimson_horde",
                name="Crimson Horde",
                description="A savage horde of raiders, hostile to all civilization.",
                default_attitude=FactionAttitude.HOSTILE.value,
                base_reputation=-5000.0,
                icon="skull_red",
                color="#8b0000",
                leader_npc="npc_warlord_garsh",
                headquarters_location="wasteland_camp",
                is_hostile_by_default=True,
            )
            self._factions[f4.faction_id] = f4

            # Faction 5: Merchants Guild
            f5 = FactionDefinition(
                faction_id="faction_merchants_guild",
                name="Merchants Guild",
                description="A wealthy guild of traders and shopkeepers.",
                default_attitude=FactionAttitude.NEUTRAL.value,
                base_reputation=0.0,
                icon="coin_gold",
                color="#b8860b",
                leader_npc="npc_guildmaster_coin",
                headquarters_location="market_square",
                is_hostile_by_default=False,
            )
            f5.rewards = [
                FactionReward(
                    reward_id="reward_merchant_discount",
                    faction_id="faction_merchants_guild",
                    name="Trade Discount",
                    description="5% discount on all merchant purchases.",
                    required_tier=FactionTier.FRIENDLY.value,
                    reward_type="discount",
                    reward_data={"discount_percent": 5},
                ),
                FactionReward(
                    reward_id="reward_merchant_stall",
                    faction_id="faction_merchants_guild",
                    name="Personal Stall",
                    description="Unlock a personal market stall for selling goods.",
                    required_tier=FactionTier.HONORED.value,
                    reward_type="unlock",
                    reward_data={"stall_id": "stall_player_owned"},
                ),
            ]
            self._factions[f5.faction_id] = f5
            for rw in f5.rewards:
                self._rewards[rw.reward_id] = rw

            # Player reputations
            rep_data = [
                ("faction_iron_guard", "player_starter", 2500.0),
                ("faction_shadow_syndicate", "player_starter", -200.0),
                ("faction_arcane_circle", "player_starter", 3200.0),
                ("faction_crimson_horde", "player_starter", -6000.0),
                ("faction_merchants_guild", "player_starter", 800.0),
                ("faction_iron_guard", "player_veteran", 12000.0),
                ("faction_arcane_circle", "player_veteran", 15000.0),
                ("faction_merchants_guild", "player_veteran", 5500.0),
                ("faction_crimson_horde", "player_veteran", -8000.0),
            ]
            for fid, pid, rep_val in rep_data:
                tier = _tier_from_reputation(rep_val)
                pr = PlayerReputation(
                    faction_id=fid,
                    player_id=pid,
                    reputation=rep_val,
                    tier=tier,
                    lifetime_gained=max(0.0, rep_val),
                    lifetime_lost=max(0.0, -rep_val),
                    total_interactions=5,
                    last_interaction=_now() - 3600,
                    is_hostile=_is_hostile_tier(tier),
                )
                key = f"{pid}:{fid}"
                self._player_reps[key] = pr

            # Relations
            relations = [
                ("rel_001", "faction_iron_guard", "faction_merchants_guild", FactionRelation.FRIENDLY.value, 0.7),
                ("rel_002", "faction_iron_guard", "faction_shadow_syndicate", FactionRelation.RIVAL.value, -0.6),
                ("rel_003", "faction_iron_guard", "faction_crimson_horde", FactionRelation.AT_WAR.value, -1.0),
                ("rel_004", "faction_arcane_circle", "faction_merchants_guild", FactionRelation.NEUTRAL.value, 0.1),
                ("rel_005", "faction_arcane_circle", "faction_crimson_horde", FactionRelation.RIVAL.value, -0.8),
                ("rel_006", "faction_shadow_syndicate", "faction_crimson_horde", FactionRelation.NEUTRAL.value, -0.2),
            ]
            for rid, fa, fb, rel, strength in relations:
                self._relations[rid] = FactionRelationEntry(
                    relation_id=rid,
                    faction_a=fa,
                    faction_b=fb,
                    relation=rel,
                    strength=strength,
                )

            # Wars
            self._wars["war_starter_01"] = FactionWar(
                war_id="war_starter_01",
                faction_a="faction_iron_guard",
                faction_b="faction_crimson_horde",
                status=FactionWarStatus.ACTIVE.value,
                outcome=FactionWarOutcome.PENDING.value,
                declared_at=_now() - 86400 * 7,
                started_at=_now() - 86400 * 6,
                declarer_player="npc_commander_steel",
                faction_a_score=150.0,
                faction_b_score=80.0,
                casualties_a=45,
                casualties_b=120,
            )

            # Diplomatic action
            self._diplomatic_actions["diplo_starter_01"] = DiplomaticAction(
                action_id="diplo_starter_01",
                action_type=DiplomaticActionType.TRADE_AGREEMENT.value,
                proposer_faction="faction_merchants_guild",
                target_faction="faction_arcane_circle",
                player_id="player_starter",
                description="Propose a trade agreement for arcane goods.",
                status=DiplomaticActionStatus.PENDING.value,
                proposed_at=_now() - 3600,
                expires_at=_now() + 86400,
            )

            self._update_stats()
            self._initialized = True

    def _update_stats(self) -> None:
        self._stats.total_factions = len(self._factions)
        self._stats.total_rewards = len(self._rewards)
        self._stats.total_player_reputations = len(self._player_reps)
        self._stats.total_relations = len(self._relations)
        self._stats.total_diplomatic_actions = len(self._diplomatic_actions)
        self._stats.pending_diplomatic_actions = sum(
            1 for a in self._diplomatic_actions.values()
            if a.status == DiplomaticActionStatus.PENDING.value
        )
        self._stats.total_wars = len(self._wars)
        self._stats.active_wars = sum(
            1 for w in self._wars.values()
            if w.status in (FactionWarStatus.DECLARED.value, FactionWarStatus.ACTIVE.value)
        )
        self._stats.hostile_factions = sum(
            1 for f in self._factions.values() if f.is_hostile_by_default
        )

    def _record_event(
        self,
        kind: str,
        faction_id: str = "",
        player_id: str = "",
        target_faction_id: str = "",
        war_id: str = "",
        action_id: str = "",
        reward_id: str = "",
        description: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = FactionEvent(
            event_id=f"evt_{self._event_counter:08d}",
            kind=kind,
            timestamp=_now(),
            faction_id=faction_id,
            player_id=player_id,
            target_faction_id=target_faction_id,
            war_id=war_id,
            action_id=action_id,
            reward_id=reward_id,
            description=description,
            details=details or {},
        )
        self._events.append(event)
        self._event_counter += 1
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _add_entry(
        self,
        faction_id: str,
        player_id: str,
        change: float,
        reason: str,
        source: str,
        old_val: float,
        new_val: float,
        old_tier: str,
        new_tier: str,
    ) -> ReputationEntry:
        entry = ReputationEntry(
            entry_id=f"rep_{self._entry_counter:08d}",
            faction_id=faction_id,
            player_id=player_id,
            change=change,
            reason=reason,
            source=source,
            timestamp=_now(),
            old_value=old_val,
            new_value=new_val,
            old_tier=old_tier,
            new_tier=new_tier,
        )
        self._entries.append(entry)
        self._entry_counter += 1
        _evict_fifo_list(self._entries, _MAX_ENTRIES)
        return entry

    # ------------------------------------------------------------------
    # Faction management
    # ------------------------------------------------------------------

    def register_faction(
        self,
        faction_id: str,
        name: str,
        description: str = "",
        default_attitude: str = FactionAttitude.NEUTRAL.value,
        base_reputation: float = 0.0,
        icon: str = "",
        color: str = "",
        leader_npc: str = "",
        headquarters_location: str = "",
        is_hostile_by_default: bool = False,
    ) -> Tuple[bool, str, Optional[FactionDefinition]]:
        if faction_id in self._factions:
            return False, "exists", None
        if len(self._factions) >= _MAX_FACTIONS:
            return False, "capacity", None
        faction = FactionDefinition(
            faction_id=faction_id,
            name=name,
            description=description,
            default_attitude=default_attitude,
            base_reputation=base_reputation,
            icon=icon,
            color=color,
            leader_npc=leader_npc,
            headquarters_location=headquarters_location,
            is_hostile_by_default=is_hostile_by_default,
        )
        self._factions[faction_id] = faction
        self._record_event(
            ReputationEventKind.FACTION_REGISTERED.value,
            faction_id=faction_id,
            description=f"Faction '{name}' registered",
        )
        self._update_stats()
        return True, "registered", faction

    def remove_faction(self, faction_id: str) -> Tuple[bool, str]:
        if faction_id not in self._factions:
            return False, "not_found"
        del self._factions[faction_id]
        for rid in list(self._rewards.keys()):
            if self._rewards[rid].faction_id == faction_id:
                del self._rewards[rid]
        for key in list(self._player_reps.keys()):
            if self._player_reps[key].faction_id == faction_id:
                del self._player_reps[key]
        for rid in list(self._relations.keys()):
            rel = self._relations[rid]
            if rel.faction_a == faction_id or rel.faction_b == faction_id:
                del self._relations[rid]
        self._record_event(
            ReputationEventKind.FACTION_REMOVED.value,
            faction_id=faction_id,
            description=f"Faction removed",
        )
        self._update_stats()
        return True, "removed"

    def get_faction(self, faction_id: str) -> Optional[FactionDefinition]:
        return self._factions.get(faction_id)

    def list_factions(
        self, attitude: str = "", limit: int = 50, offset: int = 0
    ) -> List[FactionDefinition]:
        factions = list(self._factions.values())
        if attitude:
            factions = [f for f in factions if f.default_attitude == attitude]
        return factions[offset : offset + limit]

    # ------------------------------------------------------------------
    # Reward management
    # ------------------------------------------------------------------

    def register_reward(
        self,
        reward_id: str,
        faction_id: str,
        name: str,
        description: str = "",
        required_tier: str = FactionTier.FRIENDLY.value,
        reward_type: str = "item",
        reward_data: Optional[Dict[str, Any]] = None,
        one_time: bool = True,
    ) -> Tuple[bool, str, Optional[FactionReward]]:
        if reward_id in self._rewards:
            return False, "exists", None
        if faction_id not in self._factions:
            return False, "faction_not_found", None
        if len(self._rewards) >= _MAX_REWARDS:
            return False, "capacity", None
        reward = FactionReward(
            reward_id=reward_id,
            faction_id=faction_id,
            name=name,
            description=description,
            required_tier=required_tier,
            reward_type=reward_type,
            reward_data=reward_data or {},
            one_time=one_time,
        )
        self._rewards[reward_id] = reward
        faction = self._factions[faction_id]
        faction.rewards.append(reward)
        self._record_event(
            ReputationEventKind.REWARD_REGISTERED.value,
            faction_id=faction_id,
            reward_id=reward_id,
            description=f"Reward '{name}' registered",
        )
        self._update_stats()
        return True, "registered", reward

    def remove_reward(self, reward_id: str) -> Tuple[bool, str]:
        reward = self._rewards.get(reward_id)
        if reward is None:
            return False, "not_found"
        del self._rewards[reward_id]
        faction = self._factions.get(reward.faction_id)
        if faction:
            faction.rewards = [r for r in faction.rewards if r.reward_id != reward_id]
        self._record_event(
            ReputationEventKind.REWARD_REMOVED.value,
            faction_id=reward.faction_id,
            reward_id=reward_id,
            description=f"Reward '{reward.name}' removed",
        )
        self._update_stats()
        return True, "removed"

    def get_reward(self, reward_id: str) -> Optional[FactionReward]:
        return self._rewards.get(reward_id)

    def list_rewards(
        self, faction_id: str = "", limit: int = 50, offset: int = 0
    ) -> List[FactionReward]:
        rewards = list(self._rewards.values())
        if faction_id:
            rewards = [r for r in rewards if r.faction_id == faction_id]
        return rewards[offset : offset + limit]

    # ------------------------------------------------------------------
    # Reputation management
    # ------------------------------------------------------------------

    def _get_or_create_player_rep(
        self, faction_id: str, player_id: str
    ) -> Optional[PlayerReputation]:
        faction = self._factions.get(faction_id)
        if faction is None:
            return None
        key = f"{player_id}:{faction_id}"
        pr = self._player_reps.get(key)
        if pr is None:
            base = faction.base_reputation
            tier = _tier_from_reputation(base)
            pr = PlayerReputation(
                faction_id=faction_id,
                player_id=player_id,
                reputation=base,
                tier=tier,
                is_hostile=_is_hostile_tier(tier) or faction.is_hostile_by_default,
            )
            self._player_reps[key] = pr
            self._update_stats()
        return pr

    def gain_reputation(
        self,
        faction_id: str,
        player_id: str,
        amount: float,
        reason: str = "",
        source: str = "",
    ) -> Tuple[bool, str, Optional[PlayerReputation]]:
        pr = self._get_or_create_player_rep(faction_id, player_id)
        if pr is None:
            return False, "faction_not_found", None
        old_val = pr.reputation
        old_tier = pr.tier
        pr.reputation = _clamp(
            pr.reputation + amount,
            self._config.reputation_floor,
            self._config.reputation_cap,
        )
        pr.tier = _tier_from_reputation(pr.reputation)
        pr.lifetime_gained += amount
        pr.total_interactions += 1
        pr.last_interaction = _now()
        pr.is_hostile = _is_hostile_tier(pr.tier)
        self._add_entry(
            faction_id, player_id, amount, reason, source,
            old_val, pr.reputation, old_tier, pr.tier,
        )
        self._stats.total_reputation_gained += amount
        self._record_event(
            ReputationEventKind.REPUTATION_GAINED.value,
            faction_id=faction_id,
            player_id=player_id,
            description=f"Gained {amount} reputation with {faction_id}",
            details={"amount": amount, "reason": reason, "source": source},
        )
        if old_tier != pr.tier:
            self._record_event(
                ReputationEventKind.TIER_CHANGED.value,
                faction_id=faction_id,
                player_id=player_id,
                description=f"Tier changed: {old_tier} -> {pr.tier}",
                details={"old_tier": old_tier, "new_tier": pr.tier},
            )
        return True, "gained", pr

    def lose_reputation(
        self,
        faction_id: str,
        player_id: str,
        amount: float,
        reason: str = "",
        source: str = "",
    ) -> Tuple[bool, str, Optional[PlayerReputation]]:
        return self.gain_reputation(faction_id, player_id, -amount, reason, source)

    def set_reputation(
        self,
        faction_id: str,
        player_id: str,
        value: float,
        reason: str = "",
    ) -> Tuple[bool, str, Optional[PlayerReputation]]:
        pr = self._get_or_create_player_rep(faction_id, player_id)
        if pr is None:
            return False, "faction_not_found", None
        old_val = pr.reputation
        old_tier = pr.tier
        pr.reputation = _clamp(
            value,
            self._config.reputation_floor,
            self._config.reputation_cap,
        )
        pr.tier = _tier_from_reputation(pr.reputation)
        pr.total_interactions += 1
        pr.last_interaction = _now()
        pr.is_hostile = _is_hostile_tier(pr.tier)
        change = pr.reputation - old_val
        if change > 0:
            pr.lifetime_gained += change
        else:
            pr.lifetime_lost += abs(change)
        self._add_entry(
            faction_id, player_id, change, reason, "set",
            old_val, pr.reputation, old_tier, pr.tier,
        )
        self._record_event(
            ReputationEventKind.REPUTATION_SET.value,
            faction_id=faction_id,
            player_id=player_id,
            description=f"Reputation set to {pr.reputation}",
            details={"old_value": old_val, "new_value": pr.reputation},
        )
        if old_tier != pr.tier:
            self._record_event(
                ReputationEventKind.TIER_CHANGED.value,
                faction_id=faction_id,
                player_id=player_id,
                description=f"Tier changed: {old_tier} -> {pr.tier}",
                details={"old_tier": old_tier, "new_tier": pr.tier},
            )
        return True, "set", pr

    def get_reputation(
        self, faction_id: str, player_id: str
    ) -> Optional[PlayerReputation]:
        key = f"{player_id}:{faction_id}"
        return self._player_reps.get(key)

    def list_player_reputations(
        self, player_id: str, tier: str = "", limit: int = 50, offset: int = 0
    ) -> List[PlayerReputation]:
        reps = [
            pr for pr in self._player_reps.values()
            if pr.player_id == player_id
        ]
        if tier:
            reps = [r for r in reps if r.tier == tier]
        return reps[offset : offset + limit]

    def get_reputation_tier(
        self, faction_id: str, player_id: str
    ) -> str:
        pr = self.get_reputation(faction_id, player_id)
        if pr is None:
            faction = self._factions.get(faction_id)
            if faction:
                return _tier_from_reputation(faction.base_reputation)
            return FactionTier.NEUTRAL.value
        return pr.tier

    # ------------------------------------------------------------------
    # Relation management
    # ------------------------------------------------------------------

    def register_relation(
        self,
        relation_id: str,
        faction_a: str,
        faction_b: str,
        relation: str = FactionRelation.NEUTRAL.value,
        strength: float = 0.0,
    ) -> Tuple[bool, str, Optional[FactionRelationEntry]]:
        if relation_id in self._relations:
            return False, "exists", None
        if faction_a not in self._factions or faction_b not in self._factions:
            return False, "faction_not_found", None
        if len(self._relations) >= _MAX_RELATIONS:
            return False, "capacity", None
        entry = FactionRelationEntry(
            relation_id=relation_id,
            faction_a=faction_a,
            faction_b=faction_b,
            relation=relation,
            strength=strength,
        )
        self._relations[relation_id] = entry
        self._record_event(
            ReputationEventKind.RELATION_REGISTERED.value,
            faction_id=faction_a,
            target_faction_id=faction_b,
            description=f"Relation '{relation}' between {faction_a} and {faction_b}",
        )
        self._update_stats()
        return True, "registered", entry

    def get_relation(
        self, faction_a: str, faction_b: str
    ) -> Optional[FactionRelationEntry]:
        for rel in self._relations.values():
            if (rel.faction_a == faction_a and rel.faction_b == faction_b) or \
               (rel.faction_a == faction_b and rel.faction_b == faction_a):
                return rel
        return None

    def list_relations(
        self, faction_id: str = "", limit: int = 50, offset: int = 0
    ) -> List[FactionRelationEntry]:
        rels = list(self._relations.values())
        if faction_id:
            rels = [r for r in rels if r.faction_a == faction_id or r.faction_b == faction_id]
        return rels[offset : offset + limit]

    # ------------------------------------------------------------------
    # Diplomatic actions
    # ------------------------------------------------------------------

    def create_diplomatic_action(
        self,
        action_id: str,
        action_type: str = DiplomaticActionType.PEACE_TREATY.value,
        proposer_faction: str = "",
        target_faction: str = "",
        player_id: str = "",
        description: str = "",
        expires_at: float = 0.0,
        terms: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[DiplomaticAction]]:
        if action_id in self._diplomatic_actions:
            return False, "exists", None
        if proposer_faction and proposer_faction not in self._factions:
            return False, "proposer_not_found", None
        if target_faction and target_faction not in self._factions:
            return False, "target_not_found", None
        if len(self._diplomatic_actions) >= _MAX_DIPLOMATIC_ACTIONS:
            return False, "capacity", None
        action = DiplomaticAction(
            action_id=action_id,
            action_type=action_type,
            proposer_faction=proposer_faction,
            target_faction=target_faction,
            player_id=player_id,
            description=description,
            status=DiplomaticActionStatus.PENDING.value,
            expires_at=expires_at,
            terms=terms or {},
        )
        self._diplomatic_actions[action_id] = action
        self._record_event(
            ReputationEventKind.DIPLOMATIC_CREATED.value,
            faction_id=proposer_faction,
            target_faction_id=target_faction,
            action_id=action_id,
            player_id=player_id,
            description=f"Diplomatic action '{action_type}' proposed",
        )
        self._update_stats()
        return True, "created", action

    def accept_diplomatic_action(
        self, action_id: str
    ) -> Tuple[bool, str, Optional[DiplomaticAction]]:
        action = self._diplomatic_actions.get(action_id)
        if action is None:
            return False, "not_found", None
        if action.status != DiplomaticActionStatus.PENDING.value:
            return False, "not_pending", None
        action.status = DiplomaticActionStatus.ACCEPTED.value
        action.resolved_at = _now()
        self._record_event(
            ReputationEventKind.DIPLOMATIC_ACCEPTED.value,
            faction_id=action.proposer_faction,
            target_faction_id=action.target_faction,
            action_id=action_id,
            description=f"Diplomatic action '{action.action_type}' accepted",
        )
        self._update_stats()
        return True, "accepted", action

    def reject_diplomatic_action(
        self, action_id: str
    ) -> Tuple[bool, str, Optional[DiplomaticAction]]:
        action = self._diplomatic_actions.get(action_id)
        if action is None:
            return False, "not_found", None
        if action.status != DiplomaticActionStatus.PENDING.value:
            return False, "not_pending", None
        action.status = DiplomaticActionStatus.REJECTED.value
        action.resolved_at = _now()
        self._record_event(
            ReputationEventKind.DIPLOMATIC_REJECTED.value,
            faction_id=action.proposer_faction,
            target_faction_id=action.target_faction,
            action_id=action_id,
            description=f"Diplomatic action '{action.action_type}' rejected",
        )
        self._update_stats()
        return True, "rejected", action

    def get_diplomatic_action(
        self, action_id: str
    ) -> Optional[DiplomaticAction]:
        return self._diplomatic_actions.get(action_id)

    def list_diplomatic_actions(
        self,
        status: str = "",
        faction_id: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[DiplomaticAction]:
        actions = list(self._diplomatic_actions.values())
        if status:
            actions = [a for a in actions if a.status == status]
        if faction_id:
            actions = [
                a for a in actions
                if a.proposer_faction == faction_id or a.target_faction == faction_id
            ]
        return actions[offset : offset + limit]

    # ------------------------------------------------------------------
    # Wars
    # ------------------------------------------------------------------

    def declare_war(
        self,
        war_id: str,
        faction_a: str,
        faction_b: str,
        declarer_player: str = "",
    ) -> Tuple[bool, str, Optional[FactionWar]]:
        if war_id in self._wars:
            return False, "exists", None
        if faction_a not in self._factions or faction_b not in self._factions:
            return False, "faction_not_found", None
        if len(self._wars) >= _MAX_WARS:
            return False, "capacity", None
        war = FactionWar(
            war_id=war_id,
            faction_a=faction_a,
            faction_b=faction_b,
            status=FactionWarStatus.DECLARED.value,
            declarer_player=declarer_player,
        )
        self._wars[war_id] = war
        self._record_event(
            ReputationEventKind.WAR_DECLARED.value,
            faction_id=faction_a,
            target_faction_id=faction_b,
            war_id=war_id,
            player_id=declarer_player,
            description=f"War declared between {faction_a} and {faction_b}",
        )
        self._update_stats()
        return True, "declared", war

    def start_war(
        self, war_id: str
    ) -> Tuple[bool, str, Optional[FactionWar]]:
        war = self._wars.get(war_id)
        if war is None:
            return False, "not_found", None
        if war.status != FactionWarStatus.DECLARED.value:
            return False, "not_declared", None
        war.status = FactionWarStatus.ACTIVE.value
        war.started_at = _now()
        self._record_event(
            ReputationEventKind.WAR_STARTED.value,
            faction_id=war.faction_a,
            target_faction_id=war.faction_b,
            war_id=war_id,
            description=f"War {war_id} started",
        )
        self._update_stats()
        return True, "started", war

    def end_war(
        self,
        war_id: str,
        outcome: str = FactionWarOutcome.DRAW.value,
    ) -> Tuple[bool, str, Optional[FactionWar]]:
        war = self._wars.get(war_id)
        if war is None:
            return False, "not_found", None
        if war.status not in (FactionWarStatus.ACTIVE.value, FactionWarStatus.CEASEFIRE.value):
            return False, "not_active", None
        war.status = FactionWarStatus.ENDED.value
        war.outcome = outcome
        war.ended_at = _now()
        self._record_event(
            ReputationEventKind.WAR_ENDED.value,
            faction_id=war.faction_a,
            target_faction_id=war.faction_b,
            war_id=war_id,
            description=f"War {war_id} ended with outcome {outcome}",
        )
        self._update_stats()
        return True, "ended", war

    def cancel_war(
        self, war_id: str
    ) -> Tuple[bool, str, Optional[FactionWar]]:
        war = self._wars.get(war_id)
        if war is None:
            return False, "not_found", None
        if war.status not in (FactionWarStatus.DECLARED.value, FactionWarStatus.ACTIVE.value):
            return False, "cannot_cancel", None
        war.status = FactionWarStatus.CANCELLED.value
        war.ended_at = _now()
        self._record_event(
            ReputationEventKind.WAR_CANCELLED.value,
            faction_id=war.faction_a,
            target_faction_id=war.faction_b,
            war_id=war_id,
            description=f"War {war_id} cancelled",
        )
        self._update_stats()
        return True, "cancelled", war

    def get_war(self, war_id: str) -> Optional[FactionWar]:
        return self._wars.get(war_id)

    def list_wars(
        self,
        status: str = "",
        faction_id: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[FactionWar]:
        wars = list(self._wars.values())
        if status:
            wars = [w for w in wars if w.status == status]
        if faction_id:
            wars = [w for w in wars if w.faction_a == faction_id or w.faction_b == faction_id]
        return wars[offset : offset + limit]

    # ------------------------------------------------------------------
    # Hostility and rewards
    # ------------------------------------------------------------------

    def check_hostility(
        self, faction_id: str, player_id: str
    ) -> bool:
        pr = self.get_reputation(faction_id, player_id)
        if pr is not None:
            return pr.is_hostile
        faction = self._factions.get(faction_id)
        if faction:
            return faction.is_hostile_by_default
        return False

    def get_available_rewards(
        self, faction_id: str, player_id: str
    ) -> List[FactionReward]:
        pr = self.get_reputation(faction_id, player_id)
        tier = pr.tier if pr else FactionTier.NEUTRAL.value
        tier_order = [
            FactionTier.HATED.value,
            FactionTier.HOSTILE.value,
            FactionTier.UNFRIENDLY.value,
            FactionTier.NEUTRAL.value,
            FactionTier.FRIENDLY.value,
            FactionTier.HONORED.value,
            FactionTier.REVERED.value,
            FactionTier.EXALTED.value,
        ]
        try:
            tier_idx = tier_order.index(tier)
        except ValueError:
            tier_idx = 3
        claimed = pr.claimed_rewards if pr else []
        available = []
        for reward in self._rewards.values():
            if reward.faction_id != faction_id:
                continue
            try:
                req_idx = tier_order.index(reward.required_tier)
            except ValueError:
                continue
            if req_idx <= tier_idx:
                if reward.one_time and reward.reward_id in claimed:
                    continue
                available.append(reward)
        return available

    def claim_reward(
        self, faction_id: str, player_id: str, reward_id: str
    ) -> Tuple[bool, str, Optional[FactionReward]]:
        reward = self._rewards.get(reward_id)
        if reward is None:
            return False, "reward_not_found", None
        if reward.faction_id != faction_id:
            return False, "faction_mismatch", None
        pr = self.get_reputation(faction_id, player_id)
        if pr is None:
            return False, "no_reputation", None
        available = self.get_available_rewards(faction_id, player_id)
        if reward not in available:
            return False, "requirements_not_met", None
        if reward.one_time and reward.reward_id in pr.claimed_rewards:
            return False, "already_claimed", None
        pr.claimed_rewards.append(reward.reward_id)
        reward.claimed_by.append(player_id)
        self._record_event(
            ReputationEventKind.REWARD_CLAIMED.value,
            faction_id=faction_id,
            player_id=player_id,
            reward_id=reward_id,
            description=f"Reward '{reward.name}' claimed by {player_id}",
        )
        return True, "claimed", reward

    # ------------------------------------------------------------------
    # System operations
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        self._tick_count += 1
        now = _now()
        expired = 0
        for action in self._diplomatic_actions.values():
            if (
                action.status == DiplomaticActionStatus.PENDING.value
                and action.expires_at > 0
                and now > action.expires_at
            ):
                action.status = DiplomaticActionStatus.EXPIRED.value
                expired += 1
        if self._config.decay_rate > 0:
            interval = self._config.decay_interval
            for pr in self._player_reps.values():
                if pr.last_interaction > 0 and (now - pr.last_interaction) > interval:
                    if pr.reputation > 0:
                        pr.reputation = max(0.0, pr.reputation - self._config.decay_rate)
                    elif pr.reputation < 0:
                        pr.reputation = min(0.0, pr.reputation + self._config.decay_rate)
                    pr.tier = _tier_from_reputation(pr.reputation)
                    pr.is_hostile = _is_hostile_tier(pr.tier)
        self._record_event(
            ReputationEventKind.TICK.value,
            description=f"Tick #{self._tick_count}, expired {expired} actions",
        )
        return {
            "tick_count": self._tick_count,
            "expired_actions": expired,
        }

    def set_config(self, config: Dict[str, Any]) -> FactionReputationConfig:
        if "max_factions" in config:
            self._config.max_factions = _safe_int(config["max_factions"], self._config.max_factions)
        if "max_rewards" in config:
            self._config.max_rewards = _safe_int(config["max_rewards"], self._config.max_rewards)
        if "max_player_reputations" in config:
            self._config.max_player_reputations = _safe_int(config["max_player_reputations"], self._config.max_player_reputations)
        if "max_relations" in config:
            self._config.max_relations = _safe_int(config["max_relations"], self._config.max_relations)
        if "max_diplomatic_actions" in config:
            self._config.max_diplomatic_actions = _safe_int(config["max_diplomatic_actions"], self._config.max_diplomatic_actions)
        if "max_wars" in config:
            self._config.max_wars = _safe_int(config["max_wars"], self._config.max_wars)
        if "max_entries" in config:
            self._config.max_entries = _safe_int(config["max_entries"], self._config.max_entries)
        if "reputation_cap" in config:
            self._config.reputation_cap = _safe_float(config["reputation_cap"], self._config.reputation_cap)
        if "reputation_floor" in config:
            self._config.reputation_floor = _safe_float(config["reputation_floor"], self._config.reputation_floor)
        if "decay_rate" in config:
            self._config.decay_rate = _safe_float(config["decay_rate"], self._config.decay_rate)
        if "decay_interval" in config:
            self._config.decay_interval = _safe_float(config["decay_interval"], self._config.decay_interval)
        if "tick_rate_hz" in config:
            self._config.tick_rate_hz = _safe_float(config["tick_rate_hz"], self._config.tick_rate_hz)
        self._record_event(
            ReputationEventKind.CONFIG_UPDATED.value,
            description="Configuration updated",
        )
        return self._config

    def get_config(self) -> FactionReputationConfig:
        return self._config

    def list_events(
        self,
        faction_id: str = "",
        player_id: str = "",
        limit: int = 100,
    ) -> List[FactionEvent]:
        events = list(self._events)
        if faction_id:
            events = [e for e in events if e.faction_id == faction_id]
        if player_id:
            events = [e for e in events if e.player_id == player_id]
        return events[-limit:]

    def list_entries(
        self,
        faction_id: str = "",
        player_id: str = "",
        limit: int = 100,
    ) -> List[ReputationEntry]:
        entries = list(self._entries)
        if faction_id:
            entries = [e for e in entries if e.faction_id == faction_id]
        if player_id:
            entries = [e for e in entries if e.player_id == player_id]
        return entries[-limit:]

    def get_stats(self) -> FactionStats:
        self._update_stats()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        self._update_stats()
        return {
            "initialized": self._initialized,
            "total_factions": len(self._factions),
            "total_rewards": len(self._rewards),
            "total_player_reputations": len(self._player_reps),
            "total_relations": len(self._relations),
            "pending_diplomatic_actions": sum(
                1 for a in self._diplomatic_actions.values()
                if a.status == DiplomaticActionStatus.PENDING.value
            ),
            "active_wars": sum(
                1 for w in self._wars.values()
                if w.status in (FactionWarStatus.DECLARED.value, FactionWarStatus.ACTIVE.value)
            ),
            "total_entries": len(self._entries),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> FactionSnapshot:
        self._update_stats()
        return FactionSnapshot(
            factions=[f.to_dict() for f in self._factions.values()],
            relations=[r.to_dict() for r in self._relations.values()],
            wars=[w.to_dict() for w in self._wars.values()],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> Dict[str, Any]:
        with self._init_lock:
            self._factions.clear()
            self._rewards.clear()
            self._player_reps.clear()
            self._relations.clear()
            self._diplomatic_actions.clear()
            self._wars.clear()
            self._entries.clear()
            self._events.clear()
            self._stats = FactionStats()
            self._config = FactionReputationConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._entry_counter = 0
            self._initialized = False
            self._seed()
        self._record_event(
            ReputationEventKind.RESET.value,
            description="System reset and re-seeded",
        )
        return self.get_status()


def get_faction_reputation_system() -> FactionReputationSystem:
    """Factory function for the singleton FactionReputationSystem."""
    return FactionReputationSystem.get_instance()
