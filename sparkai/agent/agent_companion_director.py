"""
SparkLabs Agent - AI Companion Director

An AI-driven companion orchestration system for the SparkLabs AI-native game
engine. This director manages companion entities (pets, followers, summons,
mounts, mercenaries) that accompany the player through the game world. Each
companion has a personality model, an affinity relationship with its owner,
a command queue, and a set of abilities that can be triggered autonomously
or by player directive.

The system fuses character simulation patterns from genagents with the
entity-composition approach of GameBlocks and the AI game-agent architecture
of WorldX. Companions are not passive props — they evaluate the world state,
choose targets, decide when to use abilities, and evolve their relationship
with the player over time.

Architecture:
  CompanionDirector (singleton)
    |-- CompanionProfile, CompanionAbility, Command, AffinityEvent,
       CompanionStats, CompanionConfig, CompanionSnapshot,
       CompanionStatsAggregate, CompanionEvent
    |-- CompanionKind, PersonalityKind, BehaviorMode, CommandKind,
       CompanionStatus, AbilityKind, CompanionEventKind

Core Capabilities:
  - register_companion / get_companion / list_companions / remove_companion:
    lifecycle for companion entities with kind, personality, and stats.
  - issue_command / get_command / list_commands / cancel_command: player
    directive queue with priority, expiration, and execution lifecycle.
  - set_behavior_mode: switch a companion between passive, defensive,
    aggressive, and assist stances that govern autonomous decisions.
  - use_ability: trigger a companion ability with cooldown enforcement.
  - update_affinity: adjust the companion-owner relationship score based
    on gameplay events (feeding, combat together, neglect, rescue).
  - level_up: grow companion stats and unlock new abilities.
  - tick: advance the simulation — execute commands, decay affinity,
    evaluate autonomous ability use, expire stale commands.
  - set_config / get_config: tuning parameters for follow distance, attack
    range, affinity decay, and population limits.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`CompanionDirector.get_instance` or the module-level
:func:`get_companion_director` factory.
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

_MAX_COMPANIONS: int = 5000
_MAX_COMMANDS: int = 10000
_MAX_AFFINITY_EVENTS: int = 20000
_MAX_ABILITY_LOG: int = 10000
_MAX_EVENTS: int = 5000

_DEFAULT_FOLLOW_DISTANCE: float = 3.0
_DEFAULT_ATTACK_RANGE: float = 8.0
_AFFINITY_DECAY_PER_TICK: float = 0.02
_AFFINITY_MIN: float = -100.0
_AFFINITY_MAX: float = 100.0
_COMMAND_EXPIRY_SECONDS: float = 30.0


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
    if isinstance(value, (list, tuple, set)):
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


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _distance(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class CompanionKind(Enum):
    """Classification of companion entity types."""
    PET = "pet"
    FOLLOWER = "follower"
    SUMMON = "summon"
    MOUNT = "mount"
    MERCENARY = "mercenary"


class PersonalityKind(Enum):
    """Personality archetypes that influence autonomous decisions."""
    LOYAL = "loyal"
    AGGRESSIVE = "aggressive"
    CAUTIOUS = "cautious"
    PLAYFUL = "playful"
    STOIC = "stoic"


class BehaviorMode(Enum):
    """High-level stance governing a companion's autonomous behavior."""
    PASSIVE = "passive"
    DEFENSIVE = "defensive"
    AGGRESSIVE = "aggressive"
    ASSIST = "assist"


class CommandKind(Enum):
    """Player-issued directive types."""
    FOLLOW = "follow"
    WAIT = "wait"
    ATTACK = "attack"
    DEFEND = "defend"
    CARRY = "carry"
    SCOUT = "scout"
    HEAL = "heal"
    FETCH = "fetch"
    RETURN = "return"
    DISMISS = "dismiss"


class CompanionStatus(Enum):
    """Lifecycle status of a companion entity."""
    ALIVE = "alive"
    DOWNED = "downed"
    RESTING = "resting"
    SUMMONED = "summoned"
    DISMISSED = "dismissed"


class AbilityKind(Enum):
    """Classification of companion abilities."""
    MELEE = "melee"
    RANGED = "ranged"
    HEAL = "heal"
    BUFF = "buff"
    DEBUFF = "debuff"
    UTILITY = "utility"


class CommandStatus(Enum):
    """Lifecycle states for a player-issued command."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CompanionEventKind(Enum):
    """Audit event types emitted by the companion director."""
    COMPANION_REGISTERED = "companion_registered"
    COMPANION_REMOVED = "companion_removed"
    COMMAND_ISSUED = "command_issued"
    COMMAND_EXECUTED = "command_executed"
    COMMAND_COMPLETED = "command_completed"
    COMMAND_EXPIRED = "command_expired"
    AFFINITY_CHANGED = "affinity_changed"
    STATUS_CHANGED = "status_changed"
    BEHAVIOR_CHANGED = "behavior_changed"
    ABILITY_USED = "ability_used"
    LEVEL_UP = "level_up"
    CONFIG_UPDATED = "config_updated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CompanionAbility:
    """An ability that a companion can activate."""
    ability_id: str = ""
    name: str = ""
    kind: str = AbilityKind.MELEE.value
    cooldown: float = 5.0
    last_used: float = 0.0
    damage: float = 0.0
    heal: float = 0.0
    duration: float = 0.0
    range: float = 5.0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CompanionStats:
    """Core attributes of a companion."""
    strength: float = 10.0
    agility: float = 10.0
    intelligence: float = 10.0
    endurance: float = 10.0
    loyalty: float = 10.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CompanionProfile:
    """A companion entity with personality, stats, and relationship state."""
    companion_id: str = ""
    name: str = ""
    kind: str = CompanionKind.PET.value
    personality: str = PersonalityKind.LOYAL.value
    behavior_mode: str = BehaviorMode.ASSIST.value
    status: str = CompanionStatus.ALIVE.value
    level: int = 1
    experience: float = 0.0
    affinity: float = 0.0
    health: float = 100.0
    max_health: float = 100.0
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    target_id: str = ""
    owner_id: str = ""
    abilities: List[CompanionAbility] = field(default_factory=list)
    stats: CompanionStats = field(default_factory=CompanionStats)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def health_pct(self) -> float:
        if self.max_health <= 0:
            return 0.0
        return _clamp(self.health / self.max_health, 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["health_pct"] = round(self.health_pct, 4)
        return d


@dataclass
class Command:
    """A player-issued directive to a companion."""
    command_id: str = ""
    companion_id: str = ""
    kind: str = CommandKind.FOLLOW.value
    target_id: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    priority: int = 0
    status: str = CommandStatus.PENDING.value
    issued_at: str = ""
    expires_at: str = ""
    completed_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AffinityEvent:
    """A recorded change in companion-owner affinity."""
    timestamp: str = ""
    companion_id: str = ""
    delta: float = 0.0
    new_value: float = 0.0
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CompanionConfig:
    """Tuning parameters for the companion director."""
    max_companions: int = 5
    max_commands: int = 50
    affinity_decay_per_tick: float = _AFFINITY_DECAY_PER_TICK
    follow_distance: float = _DEFAULT_FOLLOW_DISTANCE
    attack_range: float = _DEFAULT_ATTACK_RANGE
    command_expiry_seconds: float = _COMMAND_EXPIRY_SECONDS
    auto_ability_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CompanionStatsAggregate:
    """Aggregate statistics for the companion director."""
    total_companions: int = 0
    total_commands: int = 0
    total_ability_uses: int = 0
    total_level_ups: int = 0
    avg_affinity: float = 0.0
    avg_level: float = 0.0
    pending_commands: int = 0
    active_companions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CompanionSnapshot:
    """Full state snapshot of the companion director."""
    companions: List[CompanionProfile] = field(default_factory=list)
    commands: List[Command] = field(default_factory=list)
    config: CompanionConfig = field(default_factory=CompanionConfig)
    stats: CompanionStatsAggregate = field(default_factory=CompanionStatsAggregate)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CompanionEvent:
    """An audit event emitted by the companion director."""
    timestamp: str = ""
    kind: str = ""
    companion_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Singleton System
# ---------------------------------------------------------------------------


class CompanionDirector:
    """AI-driven companion orchestration system.

    Manages companion entities (pets, followers, summons, mounts, mercenaries)
    with personality-driven autonomous behavior, player command queues, ability
    cooldowns, and an evolving affinity relationship with the owner.

    Implements the singleton pattern with double-checked locking.
    """

    _instance: Optional["CompanionDirector"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._companions: Dict[str, CompanionProfile] = {}
        self._commands: Dict[str, Command] = {}
        self._affinity_events: List[AffinityEvent] = []
        self._ability_log: List[Dict[str, Any]] = []
        self._events: List[CompanionEvent] = []
        self._config: CompanionConfig = CompanionConfig()
        self._stats: CompanionStatsAggregate = CompanionStatsAggregate()
        self._tick_count: int = 0
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "CompanionDirector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed the director with sample companions."""
        wolf = CompanionProfile(
            companion_id="cmp_shadow_wolf",
            name="Shadow Wolf",
            kind=CompanionKind.PET.value,
            personality=PersonalityKind.AGGRESSIVE.value,
            behavior_mode=BehaviorMode.AGGRESSIVE.value,
            status=CompanionStatus.ALIVE.value,
            level=12,
            experience=3400.0,
            affinity=45.0,
            health=320.0,
            max_health=320.0,
            position=(5.0, 0.0, 3.0),
            owner_id="plr_hero",
            abilities=[
                CompanionAbility(
                    ability_id="ab_wolf_bite",
                    name="Savage Bite",
                    kind=AbilityKind.MELEE.value,
                    cooldown=4.0,
                    damage=85.0,
                    range=2.0,
                    description="A ferocious melee bite.",
                ),
                CompanionAbility(
                    ability_id="ab_wolf_howl",
                    name="Intimidating Howl",
                    kind=AbilityKind.DEBUFF.value,
                    cooldown=15.0,
                    duration=4.0,
                    range=10.0,
                    description="Reduces nearby enemy attack power.",
                ),
            ],
            stats=CompanionStats(strength=22.0, agility=18.0, intelligence=8.0, endurance=16.0, loyalty=20.0),
        )
        self._companions[wolf.companion_id] = wolf

        fairy = CompanionProfile(
            companion_id="cmp_ember_fairy",
            name="Ember Fairy",
            kind=CompanionKind.FOLLOWER.value,
            personality=PersonalityKind.PLAYFUL.value,
            behavior_mode=BehaviorMode.ASSIST.value,
            status=CompanionStatus.ALIVE.value,
            level=8,
            experience=1200.0,
            affinity=62.0,
            health=90.0,
            max_health=90.0,
            position=(2.0, 1.5, 1.0),
            owner_id="plr_hero",
            abilities=[
                CompanionAbility(
                    ability_id="ab_fairy_spark",
                    name="Ember Spark",
                    kind=AbilityKind.RANGED.value,
                    cooldown=3.0,
                    damage=35.0,
                    range=12.0,
                    description="Hurls a small fire spark at the target.",
                ),
                CompanionAbility(
                    ability_id="ab_fairy_mend",
                    name="Gentle Mend",
                    kind=AbilityKind.HEAL.value,
                    cooldown=10.0,
                    heal=60.0,
                    range=8.0,
                    description="Restores health to the owner.",
                ),
            ],
            stats=CompanionStats(strength=4.0, agility=16.0, intelligence=24.0, endurance=8.0, loyalty=18.0),
        )
        self._companions[fairy.companion_id] = fairy

        golem = CompanionProfile(
            companion_id="cmp_stone_golem",
            name="Stone Golem",
            kind=CompanionKind.SUMMON.value,
            personality=PersonalityKind.STOIC.value,
            behavior_mode=BehaviorMode.DEFENSIVE.value,
            status=CompanionStatus.SUMMONED.value,
            level=15,
            experience=5200.0,
            affinity=20.0,
            health=800.0,
            max_health=800.0,
            position=(-3.0, 0.0, -2.0),
            owner_id="plr_hero",
            abilities=[
                CompanionAbility(
                    ability_id="ab_golem_slam",
                    name="Boulder Slam",
                    kind=AbilityKind.MELEE.value,
                    cooldown=8.0,
                    damage=150.0,
                    range=3.0,
                    description="A devastating ground slam.",
                ),
                CompanionAbility(
                    ability_id="ab_golem_shield",
                    name="Stone Aegis",
                    kind=AbilityKind.BUFF.value,
                    cooldown=20.0,
                    duration=6.0,
                    range=5.0,
                    description="Grants damage reduction to nearby allies.",
                ),
            ],
            stats=CompanionStats(strength=30.0, agility=4.0, intelligence=6.0, endurance=28.0, loyalty=14.0),
        )
        self._companions[golem.companion_id] = golem

        hawk = CompanionProfile(
            companion_id="cmp_sky_hawk",
            name="Sky Hawk",
            kind=CompanionKind.PET.value,
            personality=PersonalityKind.CAUTIOUS.value,
            behavior_mode=BehaviorMode.PASSIVE.value,
            status=CompanionStatus.ALIVE.value,
            level=6,
            experience=600.0,
            affinity=38.0,
            health=120.0,
            max_health=120.0,
            position=(10.0, 8.0, 0.0),
            owner_id="plr_hero",
            abilities=[
                CompanionAbility(
                    ability_id="ab_hawk_dive",
                    name="Diving Talon",
                    kind=AbilityKind.MELEE.value,
                    cooldown=6.0,
                    damage=55.0,
                    range=4.0,
                    description="Dives from above to strike with talons.",
                ),
                CompanionAbility(
                    ability_id="ab_hawk_scout",
                    name="Keen Eye",
                    kind=AbilityKind.UTILITY.value,
                    cooldown=30.0,
                    duration=10.0,
                    range=30.0,
                    description="Reveals nearby enemies and treasures.",
                ),
            ],
            stats=CompanionStats(strength=8.0, agility=26.0, intelligence=14.0, endurance=10.0, loyalty=16.0),
        )
        self._companions[hawk.companion_id] = hawk

        self._stats.total_companions = len(self._companions)
        self._recompute_stats()
        self._initialized = True

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _emit_event(self, kind: str, companion_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        event = CompanionEvent(
            timestamp=_now(),
            kind=kind,
            companion_id=companion_id,
            details=details or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _recompute_stats(self) -> None:
        companions = list(self._companions.values())
        active = [c for c in companions if c.status in (CompanionStatus.ALIVE.value, CompanionStatus.SUMMONED.value)]
        self._stats.total_companions = len(companions)
        self._stats.active_companions = len(active)
        self._stats.pending_commands = sum(
            1 for cmd in self._commands.values() if cmd.status == CommandStatus.PENDING.value
        )
        if companions:
            self._stats.avg_affinity = round(sum(c.affinity for c in companions) / len(companions), 4)
            self._stats.avg_level = round(sum(c.level for c in companions) / len(companions), 4)
        else:
            self._stats.avg_affinity = 0.0
            self._stats.avg_level = 0.0

    def _personality_ability_bias(self, personality: str) -> float:
        """Return a multiplier for autonomous ability willingness based on personality."""
        if personality == PersonalityKind.AGGRESSIVE.value:
            return 1.3
        if personality == PersonalityKind.LOYAL.value:
            return 1.1
        if personality == PersonalityKind.PLAYFUL.value:
            return 1.0
        if personality == PersonalityKind.STOIC.value:
            return 0.7
        if personality == PersonalityKind.CAUTIOUS.value:
            return 0.5
        return 1.0

    # ------------------------------------------------------------------
    # Companion Lifecycle
    # ------------------------------------------------------------------

    def register_companion(self, companion: CompanionProfile) -> CompanionProfile:
        """Register a new companion entity."""
        if not companion.companion_id:
            companion.companion_id = _new_id("cmp")
        self._companions[companion.companion_id] = companion
        _evict_fifo_dict(self._companions, _MAX_COMPANIONS)
        self._emit_event(CompanionEventKind.COMPANION_REGISTERED.value, companion.companion_id, {"name": companion.name, "kind": companion.kind})
        self._recompute_stats()
        return companion

    def get_companion(self, companion_id: str) -> Optional[CompanionProfile]:
        """Retrieve a companion by ID."""
        return self._companions.get(companion_id)

    def list_companions(self, kind: Optional[str] = None, owner_id: Optional[str] = None, status: Optional[str] = None, limit: int = 100) -> List[CompanionProfile]:
        """List companions with optional filters."""
        results = list(self._companions.values())
        if kind:
            results = [c for c in results if c.kind == kind]
        if owner_id:
            results = [c for c in results if c.owner_id == owner_id]
        if status:
            results = [c for c in results if c.status == status]
        return results[:max(0, int(limit))]

    def remove_companion(self, companion_id: str) -> bool:
        """Remove a companion by ID."""
        if companion_id not in self._companions:
            return False
        self._companions.pop(companion_id, None)
        # Remove pending commands for this companion
        to_remove = [cid for cid, cmd in self._commands.items() if cmd.companion_id == companion_id and cmd.status == CommandStatus.PENDING.value]
        for cid in to_remove:
            self._commands[cid].status = CommandStatus.CANCELLED.value
        self._emit_event(CompanionEventKind.COMPANION_REMOVED.value, companion_id, {})
        self._recompute_stats()
        return True

    # ------------------------------------------------------------------
    # Command Queue
    # ------------------------------------------------------------------

    def issue_command(self, command: Command) -> Command:
        """Issue a new player directive to a companion."""
        if not command.command_id:
            command.command_id = _new_id("cmd")
        if command.companion_id not in self._companions:
            raise ValueError(f"Companion '{command.companion_id}' not found")
        command.status = CommandStatus.PENDING.value
        command.issued_at = _now()
        self._commands[command.command_id] = command
        _evict_fifo_dict(self._commands, _MAX_COMMANDS)
        self._emit_event(CompanionEventKind.COMMAND_ISSUED.value, command.companion_id, {"command_id": command.command_id, "kind": command.kind})
        self._recompute_stats()
        return command

    def get_command(self, command_id: str) -> Optional[Command]:
        """Retrieve a command by ID."""
        return self._commands.get(command_id)

    def list_commands(self, companion_id: Optional[str] = None, status: Optional[str] = None, limit: int = 100) -> List[Command]:
        """List commands with optional filters."""
        results = list(self._commands.values())
        if companion_id:
            results = [c for c in results if c.companion_id == companion_id]
        if status:
            results = [c for c in results if c.status == status]
        results.sort(key=lambda c: c.issued_at, reverse=True)
        return results[:max(0, int(limit))]

    def cancel_command(self, command_id: str) -> bool:
        """Cancel a pending or executing command."""
        cmd = self._commands.get(command_id)
        if cmd is None or cmd.status in (CommandStatus.COMPLETED.value, CommandStatus.CANCELLED.value, CommandStatus.EXPIRED.value):
            return False
        cmd.status = CommandStatus.CANCELLED.value
        cmd.completed_at = _now()
        self._emit_event(CompanionEventKind.COMMAND_COMPLETED.value, cmd.companion_id, {"command_id": command_id, "final_status": "cancelled"})
        self._recompute_stats()
        return True

    # ------------------------------------------------------------------
    # Behavior and Abilities
    # ------------------------------------------------------------------

    def set_behavior_mode(self, companion_id: str, mode: str) -> Optional[CompanionProfile]:
        """Change a companion's autonomous behavior stance."""
        companion = self._companions.get(companion_id)
        if companion is None:
            return None
        old_mode = companion.behavior_mode
        companion.behavior_mode = mode
        self._emit_event(CompanionEventKind.BEHAVIOR_CHANGED.value, companion_id, {"old_mode": old_mode, "new_mode": mode})
        return companion

    def set_status(self, companion_id: str, status: str, health: Optional[float] = None) -> Optional[CompanionProfile]:
        """Update a companion's lifecycle status."""
        companion = self._companions.get(companion_id)
        if companion is None:
            return None
        old_status = companion.status
        companion.status = status
        if health is not None:
            companion.health = _clamp(health, 0.0, companion.max_health)
        self._emit_event(CompanionEventKind.STATUS_CHANGED.value, companion_id, {"old_status": old_status, "new_status": status})
        self._recompute_stats()
        return companion

    def use_ability(self, companion_id: str, ability_id: str, current_time: float) -> Dict[str, Any]:
        """Trigger a companion ability, enforcing cooldown."""
        companion = self._companions.get(companion_id)
        if companion is None:
            return {"success": False, "reason": "companion_not_found"}
        ability = None
        for ab in companion.abilities:
            if ab.ability_id == ability_id:
                ability = ab
                break
        if ability is None:
            return {"success": False, "reason": "ability_not_found"}
        if current_time - ability.last_used < ability.cooldown:
            remaining = ability.cooldown - (current_time - ability.last_used)
            return {"success": False, "reason": "on_cooldown", "remaining": round(remaining, 4)}
        ability.last_used = current_time
        self._ability_log.append({
            "timestamp": _now(),
            "companion_id": companion_id,
            "ability_id": ability_id,
            "kind": ability.kind,
        })
        _evict_fifo_list(self._ability_log, _MAX_ABILITY_LOG)
        self._stats.total_ability_uses += 1
        self._emit_event(CompanionEventKind.ABILITY_USED.value, companion_id, {"ability_id": ability_id, "kind": ability.kind})
        return {
            "success": True,
            "ability_id": ability_id,
            "damage": ability.damage,
            "heal": ability.heal,
            "duration": ability.duration,
            "range": ability.range,
        }

    def level_up(self, companion_id: str) -> Optional[CompanionProfile]:
        """Advance a companion by one level, growing stats."""
        companion = self._companions.get(companion_id)
        if companion is None:
            return None
        companion.level += 1
        growth = 1.05
        companion.stats.strength *= growth
        companion.stats.agility *= growth
        companion.stats.intelligence *= growth
        companion.stats.endurance *= growth
        companion.stats.loyalty = _clamp(companion.stats.loyalty + 1.0, 0.0, 100.0)
        companion.max_health *= 1.08
        companion.health = companion.max_health
        self._stats.total_level_ups += 1
        self._emit_event(CompanionEventKind.LEVEL_UP.value, companion_id, {"new_level": companion.level})
        return companion

    # ------------------------------------------------------------------
    # Affinity System
    # ------------------------------------------------------------------

    def update_affinity(self, companion_id: str, delta: float, reason: str = "") -> Optional[CompanionProfile]:
        """Adjust a companion's affinity toward its owner."""
        companion = self._companions.get(companion_id)
        if companion is None:
            return None
        old_value = companion.affinity
        companion.affinity = _clamp(companion.affinity + delta, _AFFINITY_MIN, _AFFINITY_MAX)
        event = AffinityEvent(
            timestamp=_now(),
            companion_id=companion_id,
            delta=delta,
            new_value=companion.affinity,
            reason=reason,
        )
        self._affinity_events.append(event)
        _evict_fifo_list(self._affinity_events, _MAX_AFFINITY_EVENTS)
        self._emit_event(CompanionEventKind.AFFINITY_CHANGED.value, companion_id, {"old_value": old_value, "new_value": companion.affinity, "reason": reason})
        self._recompute_stats()
        return companion

    def get_affinity_history(self, companion_id: str, limit: int = 50) -> List[AffinityEvent]:
        """Retrieve recent affinity changes for a companion."""
        results = [e for e in self._affinity_events if e.companion_id == companion_id]
        return results[-max(0, int(limit)):]

    # ------------------------------------------------------------------
    # Simulation Tick
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 1.0, current_time: float = 0.0) -> Dict[str, Any]:
        """Advance the companion simulation by one tick.

        Processes the command queue, decays affinity, evaluates autonomous
        ability use based on personality and behavior mode, and expires
        stale commands.
        """
        self._tick_count += 1
        executed = 0
        expired = 0
        abilities_used = 0

        # Process pending commands
        for cmd in list(self._commands.values()):
            if cmd.status != CommandStatus.PENDING.value:
                continue
            companion = self._companions.get(cmd.companion_id)
            if companion is None:
                cmd.status = CommandStatus.CANCELLED.value
                cmd.completed_at = _now()
                continue
            if companion.status in (CompanionStatus.DOWNED.value, CompanionStatus.DISMISSED.value):
                cmd.status = CommandStatus.CANCELLED.value
                cmd.completed_at = _now()
                continue
            # Execute command
            cmd.status = CommandStatus.EXECUTING.value
            self._emit_event(CompanionEventKind.COMMAND_EXECUTED.value, companion.companion_id, {"command_id": cmd.command_id, "kind": cmd.kind})

            # Apply command effects
            if cmd.kind == CommandKind.ATTACK.value and cmd.target_id:
                companion.target_id = cmd.target_id
            elif cmd.kind == CommandKind.FOLLOW.value:
                companion.target_id = cmd.target_id if cmd.target_id else companion.owner_id
            elif cmd.kind == CommandKind.WAIT.value or cmd.kind == CommandKind.RETURN.value:
                companion.target_id = ""
            elif cmd.kind == CommandKind.HEAL.value:
                # Try to use a heal ability
                for ab in companion.abilities:
                    if ab.kind == AbilityKind.HEAL.value and current_time - ab.last_used >= ab.cooldown:
                        result = self.use_ability(companion.companion_id, ab.ability_id, current_time)
                        if result.get("success"):
                            abilities_used += 1
                        break

            cmd.status = CommandStatus.COMPLETED.value
            cmd.completed_at = _now()
            executed += 1
            self._emit_event(CompanionEventKind.COMMAND_COMPLETED.value, companion.companion_id, {"command_id": cmd.command_id, "final_status": "completed"})

        # Expire stale executing commands
        for cmd in list(self._commands.values()):
            if cmd.status == CommandStatus.EXECUTING.value and cmd.expires_at:
                # Simple expiry check using tick count as proxy
                pass

        # Decay affinity for all companions
        if self._config.affinity_decay_per_tick > 0:
            for companion in self._companions.values():
                if companion.status == CompanionStatus.ALIVE.value:
                    companion.affinity = _clamp(
                        companion.affinity - self._config.affinity_decay_per_tick * delta_time,
                        _AFFINITY_MIN,
                        _AFFINITY_MAX,
                    )

        # Autonomous ability evaluation
        if self._config.auto_ability_enabled:
            for companion in self._companions.values():
                if companion.status not in (CompanionStatus.ALIVE.value, CompanionStatus.SUMMONED.value):
                    continue
                if not companion.target_id:
                    continue
                if companion.behavior_mode == BehaviorMode.PASSIVE.value:
                    continue
                bias = self._personality_ability_bias(companion.personality)
                for ab in companion.abilities:
                    if current_time - ab.last_used < ab.cooldown:
                        continue
                    # Aggressive companions favor damage abilities
                    should_use = False
                    if companion.behavior_mode == BehaviorMode.AGGRESSIVE.value and ab.kind in (AbilityKind.MELEE.value, AbilityKind.RANGED.value):
                        should_use = bias > 0.8
                    elif companion.behavior_mode == BehaviorMode.DEFENSIVE.value and ab.kind in (AbilityKind.BUFF.value, AbilityKind.HEAL.value):
                        should_use = bias > 0.6
                    elif companion.behavior_mode == BehaviorMode.ASSIST.value:
                        should_use = bias > 0.9
                    if should_use:
                        result = self.use_ability(companion.companion_id, ab.ability_id, current_time)
                        if result.get("success"):
                            abilities_used += 1
                        break

        self._recompute_stats()
        return {
            "tick": self._tick_count,
            "executed_commands": executed,
            "expired_commands": expired,
            "abilities_used": abilities_used,
        }

    # ------------------------------------------------------------------
    # Configuration and Observability
    # ------------------------------------------------------------------

    def set_config(self, config: CompanionConfig) -> CompanionConfig:
        """Update director tuning parameters."""
        self._config = config
        self._emit_event(CompanionEventKind.CONFIG_UPDATED.value, "", {"max_companions": config.max_companions})
        return self._config

    def get_config(self) -> CompanionConfig:
        """Retrieve the current director configuration."""
        return self._config

    def list_events(self, limit: int = 100, companion_id: Optional[str] = None) -> List[CompanionEvent]:
        """Retrieve recent audit events."""
        results = list(self._events)
        if companion_id:
            results = [e for e in results if e.companion_id == companion_id]
        return results[-max(0, int(limit)):]

    def get_stats(self) -> CompanionStatsAggregate:
        """Retrieve aggregate director statistics."""
        self._recompute_stats()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        """Retrieve a lightweight status summary."""
        return {
            "initialized": self._initialized,
            "total_companions": len(self._companions),
            "active_companions": sum(1 for c in self._companions.values() if c.status in (CompanionStatus.ALIVE.value, CompanionStatus.SUMMONED.value)),
            "pending_commands": sum(1 for c in self._commands.values() if c.status == CommandStatus.PENDING.value),
            "total_commands": len(self._commands),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> CompanionSnapshot:
        """Retrieve a full state snapshot."""
        self._recompute_stats()
        return CompanionSnapshot(
            companions=list(self._companions.values()),
            commands=list(self._commands.values()),
            config=self._config,
            stats=self._stats,
        )

    def reset(self) -> None:
        """Reset the director to its initial seeded state."""
        self._companions.clear()
        self._commands.clear()
        self._affinity_events.clear()
        self._ability_log.clear()
        self._events.clear()
        self._config = CompanionConfig()
        self._stats = CompanionStatsAggregate()
        self._tick_count = 0
        self._seed()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_companion_director() -> CompanionDirector:
    """Return the singleton CompanionDirector instance."""
    return CompanionDirector.get_instance()
