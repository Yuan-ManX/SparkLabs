"""
SparkLabs Engine - Magic System

A comprehensive Magic, Spell, and Ability system for the SparkLabs
AI-native game engine. Manages spell definitions, ability casting with
cooldowns, mana/energy resource management, spell effects across multiple
spell schools, casting chains, and status effects produced by spells.

Architecture:
  MagicSystemEngine (singleton)
    |-- SpellDefinition     — registered spell template with effects
    |-- SpellEffect         — atomic effect applied by a spell
    |-- CastingInstance     — in-flight cast with progress tracking
    |-- CooldownRecord      — per-caster cooldown tracking
    |-- ResourcePool        — mana/energy/rage pool with regen
    |-- CastingChain        — triggered follow-up spell sequence
    |-- MagicStats          — aggregate counters
    |-- MagicSnapshot        — immutable state snapshot
    |-- MagicEvent          — audit log entry
    |-- SpellSchool         — 15 magical disciplines
    |-- SpellTier           — 8 power tiers
    |-- SpellType           — 12 spell categories
    |-- DamageType          — 11 damage categories
    |-- TargetType          — 10 targeting modes
    |-- CastingState        — 6 cast lifecycle phases
    |-- ResourceType        — 8 resource pools
    |-- EffectType          — 18 effect categories
    |-- MagicEventKind      — 10 audit event kinds
    |-- SpellStatus         — 5 spell lifecycle states

Core Capabilities:
  - register_spell / learn_spell / equip_spell: spell lifecycle management
  - cast_spell / cancel_cast / tick_casting: cast execution pipeline
  - tick_cooldowns: advance and expire cooldowns
  - create_resource_pool / consume_resource / restore_resource / tick_resources
  - register_chain / trigger_chain: chained spell sequences
  - apply_spell_effects: compute and return spell effects
  - get_stats / get_status / get_snapshot / list_events: observability
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import datetime as _datetime


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_SPELLS = 2000
_MAX_CASTS = 1000
_MAX_COOLDOWNS = 5000
_MAX_RESOURCE_POOLS = 5000
_MAX_CHAINS = 500
_MAX_EVENTS = 3000


def _now_ts() -> str:
    """Return the current UTC time as an ISO-8601 string with 'Z' suffix."""
    return _datetime.datetime.utcnow().isoformat() + "Z"


def _now_epoch() -> float:
    """Return the current time as a Unix epoch float."""
    return time.time()


def _gen_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class SpellSchool(Enum):
    """Magical disciplines grouped by elemental and arcane origin."""
    ARCANE = "arcane"
    FIRE = "fire"
    FROST = "frost"
    LIGHTNING = "lightning"
    NATURE = "nature"
    SHADOW = "shadow"
    HOLY = "holy"
    VOID = "void"
    EARTH = "earth"
    AIR = "air"
    WATER = "water"
    MIND = "mind"
    TIME = "time"
    BLOOD = "blood"
    SUMMONING = "summoning"


class SpellTier(Enum):
    """Power tiers ranked from weakest to strongest."""
    CANTRIP = "cantrip"
    NOVICE = "novice"
    APPRENTICE = "apprentice"
    ADEPT = "adept"
    EXPERT = "expert"
    MASTER = "master"
    ARCHMAGE = "archmage"
    DIVINE = "divine"


class SpellType(Enum):
    """Functional categories of spells."""
    PROJECTILE = "projectile"
    AOE = "aoe"
    BUFF = "buff"
    DEBUFF = "debuff"
    HEAL = "heal"
    SHIELD = "shield"
    SUMMON = "summon"
    TELEPORT = "teleport"
    UTILITY = "utility"
    PASSIVE = "passive"
    CHANNEL = "channel"
    TRAP = "trap"


class DamageType(Enum):
    """Damage categories determining resistance and mitigation."""
    PHYSICAL = "physical"
    MAGICAL = "magical"
    PURE = "pure"
    TRUE = "true"
    FIRE = "fire"
    FROST = "frost"
    LIGHTNING = "lightning"
    HOLY = "holy"
    SHADOW = "shadow"
    POISON = "poison"
    ACID = "acid"


class TargetType(Enum):
    """Targeting modes determining how a spell selects its targets."""
    SELF = "self"
    SINGLE_ENEMY = "single_enemy"
    SINGLE_ALLY = "single_ally"
    ALL_ENEMIES = "all_enemies"
    ALL_ALLIES = "all_allies"
    AREA_CIRCLE = "area_circle"
    AREA_CONE = "area_cone"
    AREA_LINE = "area_line"
    POINT = "point"
    GROUND = "ground"


class CastingState(Enum):
    """Lifecycle states of a CastingInstance."""
    READY = "ready"
    CASTING = "casting"
    COOLDOWN = "cooldown"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
    CHANNELING = "channeling"


class ResourceType(Enum):
    """Resource pools that spells may consume or restore."""
    MANA = "mana"
    ENERGY = "energy"
    RAGE = "rage"
    FOCUS = "focus"
    FURY = "fury"
    SOUL = "soul"
    HEALTH = "health"
    STAMINA = "stamina"


class EffectType(Enum):
    """Effect categories produced when a spell resolves."""
    DAMAGE = "damage"
    HEALING = "healing"
    SHIELD = "shield"
    BUFF = "buff"
    DEBUFF = "debuff"
    KNOCKBACK = "knockback"
    STUN = "stun"
    SLOW = "slow"
    HASTE = "haste"
    ROOT = "root"
    SILENCE = "silence"
    FEAR = "fear"
    TELEPORT = "teleport"
    SUMMON = "summon"
    DISPEL = "dispel"
    LIFESTEAL = "lifesteal"
    MANA_DRAIN = "mana_drain"
    MANA_RESTORE = "mana_restore"


class MagicEventKind(Enum):
    """Audit event kinds emitted by the magic system."""
    SPELL_REGISTERED = "spell_registered"
    SPELL_CAST = "spell_cast"
    CAST_FAILED = "cast_failed"
    COOLDOWN_STARTED = "cooldown_started"
    COOLDOWN_FINISHED = "cooldown_finished"
    EFFECT_APPLIED = "effect_applied"
    RESOURCE_CONSUMED = "resource_consumed"
    RESOURCE_RESTORED = "resource_restored"
    CHAIN_TRIGGERED = "chain_triggered"
    SPELL_LEARNED = "spell_learned"


class SpellStatus(Enum):
    """Lifecycle states of a SpellDefinition for a given caster registry."""
    LOCKED = "locked"
    LEARNED = "learned"
    EQUIPPED = "equipped"
    ACTIVE = "active"
    ON_COOLDOWN = "on_cooldown"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SpellEffect:
    """A single atomic effect produced by a spell when it resolves."""
    id: str = field(default_factory=lambda: _gen_id("eff"))
    effect_type: EffectType = EffectType.DAMAGE
    value: float = 0.0
    duration: float = 0.0
    tick_interval: float = 0.0
    chance: float = 1.0
    target_type: TargetType = TargetType.SINGLE_ENEMY
    damage_type: DamageType = DamageType.MAGICAL
    stacking: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "effect_type": self.effect_type.value,
            "value": self.value,
            "duration": self.duration,
            "tick_interval": self.tick_interval,
            "chance": self.chance,
            "target_type": self.target_type.value,
            "damage_type": self.damage_type.value,
            "stacking": self.stacking,
            "metadata": dict(self.metadata),
        }


@dataclass
class SpellDefinition:
    """A registered spell template describing cost, timing, and effects."""
    id: str = field(default_factory=lambda: _gen_id("spell"))
    name: str = ""
    school: SpellSchool = SpellSchool.ARCANE
    tier: SpellTier = SpellTier.NOVICE
    spell_type: SpellType = SpellType.PROJECTILE
    description: str = ""
    mana_cost: float = 0.0
    energy_cost: float = 0.0
    cast_time: float = 1.0
    cooldown: float = 0.0
    range: float = 0.0
    target_type: TargetType = TargetType.SINGLE_ENEMY
    effects: List[SpellEffect] = field(default_factory=list)
    required_level: int = 1
    spell_status: SpellStatus = SpellStatus.LOCKED
    cast_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "school": self.school.value,
            "tier": self.tier.value,
            "spell_type": self.spell_type.value,
            "description": self.description,
            "mana_cost": self.mana_cost,
            "energy_cost": self.energy_cost,
            "cast_time": self.cast_time,
            "cooldown": self.cooldown,
            "range": self.range,
            "target_type": self.target_type.value,
            "effects": [e.to_dict() for e in self.effects],
            "required_level": self.required_level,
            "spell_status": self.spell_status.value,
            "cast_count": self.cast_count,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class CastingInstance:
    """An in-flight spell cast with progress and consumed resources."""
    id: str = field(default_factory=lambda: _gen_id("cast"))
    spell_id: str = ""
    caster_id: str = ""
    target_id: Optional[str] = None
    target_position: Optional[Dict[str, float]] = None
    state: CastingState = CastingState.READY
    start_time: float = field(default_factory=_now_epoch)
    end_time: float = 0.0
    progress: float = 0.0
    consumed_resources: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "spell_id": self.spell_id,
            "caster_id": self.caster_id,
            "target_id": self.target_id,
            "target_position": dict(self.target_position) if self.target_position else None,
            "state": self.state.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "progress": self.progress,
            "consumed_resources": dict(self.consumed_resources),
            "metadata": dict(self.metadata),
        }


@dataclass
class CooldownRecord:
    """A per-caster cooldown entry for a spell."""
    id: str = field(default_factory=lambda: _gen_id("cd"))
    spell_id: str = ""
    caster_id: str = ""
    start_time: float = field(default_factory=_now_epoch)
    end_time: float = 0.0
    remaining: float = 0.0
    duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "spell_id": self.spell_id,
            "caster_id": self.caster_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "remaining": self.remaining,
            "duration": self.duration,
        }


@dataclass
class ResourcePool:
    """A regenerating resource pool owned by an entity."""
    id: str = field(default_factory=lambda: _gen_id("pool"))
    entity_id: str = ""
    resource_type: ResourceType = ResourceType.MANA
    current: float = 0.0
    maximum: float = 0.0
    regen_rate: float = 0.0
    regen_delay: float = 0.0
    last_regen_time: float = field(default_factory=_now_epoch)
    modifiers: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "resource_type": self.resource_type.value,
            "current": self.current,
            "maximum": self.maximum,
            "regen_rate": self.regen_rate,
            "regen_delay": self.regen_delay,
            "last_regen_time": self.last_regen_time,
            "modifiers": dict(self.modifiers),
        }


@dataclass
class CastingChain:
    """A chain that triggers follow-up spells when a trigger spell resolves."""
    id: str = field(default_factory=lambda: _gen_id("chain"))
    name: str = ""
    trigger_spell_id: str = ""
    chained_spell_ids: List[str] = field(default_factory=list)
    chain_delay: float = 0.0
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger_spell_id": self.trigger_spell_id,
            "chained_spell_ids": list(self.chained_spell_ids),
            "chain_delay": self.chain_delay,
            "conditions": dict(self.conditions),
            "metadata": dict(self.metadata),
        }


@dataclass
class MagicStats:
    """Aggregate counters describing magic system usage."""
    total_spells: int = 0
    total_casts: int = 0
    successful_casts: int = 0
    failed_casts: int = 0
    active_cooldowns: int = 0
    total_resource_pools: int = 0
    total_chains: int = 0
    by_school: Dict[str, int] = field(default_factory=dict)
    by_tier: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_spells": self.total_spells,
            "total_casts": self.total_casts,
            "successful_casts": self.successful_casts,
            "failed_casts": self.failed_casts,
            "active_cooldowns": self.active_cooldowns,
            "total_resource_pools": self.total_resource_pools,
            "total_chains": self.total_chains,
            "by_school": dict(self.by_school),
            "by_tier": dict(self.by_tier),
        }


@dataclass
class MagicSnapshot:
    """An immutable snapshot of the magic system's state."""
    spells: List[SpellDefinition] = field(default_factory=list)
    casts: List[CastingInstance] = field(default_factory=list)
    cooldowns: List[CooldownRecord] = field(default_factory=list)
    resource_pools: List[ResourcePool] = field(default_factory=list)
    chains: List[CastingChain] = field(default_factory=list)
    stats: MagicStats = field(default_factory=MagicStats)
    timestamp: str = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spells": [s.to_dict() for s in self.spells],
            "casts": [c.to_dict() for c in self.casts],
            "cooldowns": [c.to_dict() for c in self.cooldowns],
            "resource_pools": [r.to_dict() for r in self.resource_pools],
            "chains": [c.to_dict() for c in self.chains],
            "stats": self.stats.to_dict(),
            "timestamp": self.timestamp,
        }


@dataclass
class MagicEvent:
    """An audit log entry emitted by the magic system."""
    id: str = field(default_factory=lambda: _gen_id("evt"))
    kind: MagicEventKind = MagicEventKind.SPELL_REGISTERED
    timestamp: str = field(default_factory=_now_ts)
    data: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "data": dict(self.data),
            "description": self.description,
        }


# ---------------------------------------------------------------------------
# MagicSystemEngine — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class MagicSystemEngine:
    """
    Central engine for managing spells, casts, cooldowns, resource pools,
    and casting chains within the SparkLabs AI-native game engine.

    Thread-safe via a reentrant lock. Use get_magic_system_engine() or
    MagicSystemEngine.get_instance() to obtain the singleton.

    Usage:
        engine = get_magic_system_engine()
        spell = engine.register_spell("Fireball", SpellSchool.FIRE, ...)
        cast = engine.cast_spell(spell.id, "player_1", target_id="enemy_1")
        engine.tick_casting(0.1)
    """

    _instance: Optional["MagicSystemEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "MagicSystemEngine":
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
        with self._lock:
            if self._initialized:
                return

            # Spell registry keyed by spell id.
            self._spells: Dict[str, SpellDefinition] = {}
            # Casts keyed by cast id.
            self._casts: Dict[str, CastingInstance] = {}
            # Cooldowns keyed by composite "{caster_id}:{spell_id}".
            self._cooldowns: Dict[str, CooldownRecord] = {}
            # Resource pools keyed by composite "{entity_id}:{resource_type}".
            self._resource_pools: Dict[str, ResourcePool] = {}
            # Chains keyed by chain id.
            self._chains: Dict[str, CastingChain] = {}
            # Audit events kept in FIFO order with capacity eviction.
            self._events: deque = deque(maxlen=_MAX_EVENTS)

            # Aggregate counters maintained for fast stats retrieval.
            self._total_casts: int = 0
            self._successful_casts: int = 0
            self._failed_casts: int = 0

            self._initialized = True
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "MagicSystemEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with seed spells, resource pools, chains, and a cooldown."""
        # Spell 1: Fireball
        fireball_effects = [
            SpellEffect(
                effect_type=EffectType.DAMAGE,
                value=80.0,
                damage_type=DamageType.FIRE,
                target_type=TargetType.SINGLE_ENEMY,
            ),
            SpellEffect(
                effect_type=EffectType.DEBUFF,
                value=15.0,
                duration=6.0,
                tick_interval=1.5,
                chance=0.8,
                damage_type=DamageType.FIRE,
                target_type=TargetType.SINGLE_ENEMY,
                stacking=False,
                metadata={"name": "burn"},
            ),
        ]
        fireball = self.register_spell(
            name="Fireball",
            school=SpellSchool.FIRE,
            tier=SpellTier.EXPERT,
            spell_type=SpellType.PROJECTILE,
            description="Hurls a ball of fire dealing damage and applying a burn debuff.",
            mana_cost=30.0,
            cast_time=1.5,
            cooldown=6.0,
            range=40.0,
            target_type=TargetType.SINGLE_ENEMY,
            effects=fireball_effects,
            required_level=8,
        )

        # Spell 2: Ice Lance
        ice_lance_effects = [
            SpellEffect(
                effect_type=EffectType.DAMAGE,
                value=50.0,
                damage_type=DamageType.FROST,
                target_type=TargetType.SINGLE_ENEMY,
            ),
            SpellEffect(
                effect_type=EffectType.SLOW,
                value=40.0,
                duration=4.0,
                chance=1.0,
                damage_type=DamageType.FROST,
                target_type=TargetType.SINGLE_ENEMY,
            ),
        ]
        ice_lance = self.register_spell(
            name="Ice Lance",
            school=SpellSchool.FROST,
            tier=SpellTier.ADEPT,
            spell_type=SpellType.PROJECTILE,
            description="Launches a shard of ice that damages and slows the target.",
            mana_cost=20.0,
            cast_time=1.0,
            cooldown=3.0,
            range=35.0,
            target_type=TargetType.SINGLE_ENEMY,
            effects=ice_lance_effects,
            required_level=5,
        )

        # Spell 3: Greater Heal
        greater_heal_effects = [
            SpellEffect(
                effect_type=EffectType.HEALING,
                value=150.0,
                damage_type=DamageType.HOLY,
                target_type=TargetType.SINGLE_ALLY,
            ),
        ]
        greater_heal = self.register_spell(
            name="Greater Heal",
            school=SpellSchool.HOLY,
            tier=SpellTier.EXPERT,
            spell_type=SpellType.HEAL,
            description="Restores a large amount of health to an ally.",
            mana_cost=40.0,
            cast_time=2.0,
            cooldown=8.0,
            range=25.0,
            target_type=TargetType.SINGLE_ALLY,
            effects=greater_heal_effects,
            required_level=8,
        )

        # Spell 4: Mana Shield
        mana_shield_effects = [
            SpellEffect(
                effect_type=EffectType.SHIELD,
                value=100.0,
                damage_type=DamageType.MAGICAL,
                target_type=TargetType.SELF,
                duration=10.0,
            ),
        ]
        mana_shield = self.register_spell(
            name="Mana Shield",
            school=SpellSchool.ARCANE,
            tier=SpellTier.APPRENTICE,
            spell_type=SpellType.SHIELD,
            description="Creates a protective shield around the caster.",
            mana_cost=25.0,
            cast_time=0.5,
            cooldown=10.0,
            range=0.0,
            target_type=TargetType.SELF,
            effects=mana_shield_effects,
            required_level=3,
        )

        # Spell 5: Chain Lightning
        chain_lightning_effects = [
            SpellEffect(
                effect_type=EffectType.DAMAGE,
                value=60.0,
                damage_type=DamageType.LIGHTNING,
                target_type=TargetType.ALL_ENEMIES,
            ),
            SpellEffect(
                effect_type=EffectType.STUN,
                value=1.0,
                duration=1.5,
                chance=0.5,
                damage_type=DamageType.LIGHTNING,
                target_type=TargetType.ALL_ENEMIES,
            ),
        ]
        chain_lightning = self.register_spell(
            name="Chain Lightning",
            school=SpellSchool.LIGHTNING,
            tier=SpellTier.MASTER,
            spell_type=SpellType.AOE,
            description="Calls down lightning that strikes all enemies and may stun them.",
            mana_cost=50.0,
            cast_time=1.8,
            cooldown=12.0,
            range=30.0,
            target_type=TargetType.ALL_ENEMIES,
            effects=chain_lightning_effects,
            required_level=15,
        )

        # Spell 6: Arcane Intellect
        arcane_intellect_effects = [
            SpellEffect(
                effect_type=EffectType.BUFF,
                value=30.0,
                duration=1800.0,
                damage_type=DamageType.MAGICAL,
                target_type=TargetType.SINGLE_ALLY,
                metadata={"buff": "intellect"},
            ),
            SpellEffect(
                effect_type=EffectType.MANA_RESTORE,
                value=30.0,
                damage_type=DamageType.MAGICAL,
                target_type=TargetType.SINGLE_ALLY,
            ),
        ]
        arcane_intellect = self.register_spell(
            name="Arcane Intellect",
            school=SpellSchool.ARCANE,
            tier=SpellTier.NOVICE,
            spell_type=SpellType.BUFF,
            description="Increases an ally's mana pool and restores a small amount.",
            mana_cost=10.0,
            cast_time=1.0,
            cooldown=0.0,
            range=25.0,
            target_type=TargetType.SINGLE_ALLY,
            effects=arcane_intellect_effects,
            required_level=1,
        )

        # Status overrides: Fireball and Ice Lance LEARNED, the rest ACTIVE.
        fireball.spell_status = SpellStatus.LEARNED
        ice_lance.spell_status = SpellStatus.LEARNED
        greater_heal.spell_status = SpellStatus.ACTIVE
        mana_shield.spell_status = SpellStatus.ACTIVE
        chain_lightning.spell_status = SpellStatus.ACTIVE
        arcane_intellect.spell_status = SpellStatus.ACTIVE

        # Resource pools: player_1 mana, player_1 health, enemy_1 mana.
        self.create_resource_pool(
            entity_id="player_1",
            resource_type=ResourceType.MANA,
            maximum=200.0,
            regen_rate=5.0,
        )
        # Override seed current to 150 (default would be maximum).
        player_mana = self.get_resource_pool("player_1", ResourceType.MANA)
        if player_mana is not None:
            player_mana.current = 150.0

        self.create_resource_pool(
            entity_id="player_1",
            resource_type=ResourceType.HEALTH,
            maximum=1000.0,
            regen_rate=0.0,
        )
        player_health = self.get_resource_pool("player_1", ResourceType.HEALTH)
        if player_health is not None:
            player_health.current = 850.0

        self.create_resource_pool(
            entity_id="enemy_1",
            resource_type=ResourceType.MANA,
            maximum=100.0,
            regen_rate=2.0,
        )
        enemy_mana = self.get_resource_pool("enemy_1", ResourceType.MANA)
        if enemy_mana is not None:
            enemy_mana.current = 80.0

        # Casting chains.
        self.register_chain(
            name="Fireball Combo",
            trigger_spell_id=fireball.id,
            chained_spell_ids=[ice_lance.id],
            chain_delay=0.5,
            conditions={"auto": True},
        )
        self.register_chain(
            name="Lightning Storm",
            trigger_spell_id=chain_lightning.id,
            chained_spell_ids=[],
            chain_delay=0.0,
            conditions={},
        )

        # Seed cooldown: Ice Lance for player_1 with remaining 2.5s.
        cd_key = f"player_1:{ice_lance.id}"
        now = _now_epoch()
        self._cooldowns[cd_key] = CooldownRecord(
            spell_id=ice_lance.id,
            caster_id="player_1",
            start_time=now - 0.5,
            end_time=now + 2.5,
            remaining=2.5,
            duration=ice_lance.cooldown,
        )

    # ------------------------------------------------------------------
    # Spell Registration & Lifecycle
    # ------------------------------------------------------------------

    def register_spell(
        self,
        name: str,
        school: SpellSchool,
        tier: SpellTier,
        spell_type: SpellType,
        description: str,
        mana_cost: float,
        cast_time: float,
        cooldown: float,
        range: float,
        target_type: TargetType,
        effects: List[SpellEffect],
        required_level: int,
    ) -> SpellDefinition:
        """Register a new spell template and emit a SPELL_REGISTERED event."""
        with self._lock:
            if len(self._spells) >= _MAX_SPELLS:
                # FIFO eviction: drop the oldest spell.
                oldest_id = next(iter(self._spells), None)
                if oldest_id is not None:
                    self._spells.pop(oldest_id, None)

            spell = SpellDefinition(
                name=name,
                school=school,
                tier=tier,
                spell_type=spell_type,
                description=description,
                mana_cost=mana_cost,
                energy_cost=0.0,
                cast_time=cast_time,
                cooldown=cooldown,
                range=range,
                target_type=target_type,
                effects=list(effects) if effects else [],
                required_level=required_level,
                spell_status=SpellStatus.LOCKED,
            )
            self._spells[spell.id] = spell

            self._emit_event(
                MagicEventKind.SPELL_REGISTERED,
                {"spell_id": spell.id, "name": name, "school": school.value},
                f"Spell registered: {name}",
            )
            return spell

    def list_spells(
        self,
        school: Optional[SpellSchool] = None,
        tier: Optional[SpellTier] = None,
        spell_type: Optional[SpellType] = None,
    ) -> List[SpellDefinition]:
        """Return spells filtered by optional school, tier, and spell_type."""
        with self._lock:
            spells = list(self._spells.values())
        result: List[SpellDefinition] = []
        for spell in spells:
            if school is not None and spell.school != school:
                continue
            if tier is not None and spell.tier != tier:
                continue
            if spell_type is not None and spell.spell_type != spell_type:
                continue
            result.append(spell)
        return result

    def get_spell(self, spell_id: str) -> Optional[SpellDefinition]:
        """Return a spell by id, or None if not found."""
        with self._lock:
            return self._spells.get(spell_id)

    def learn_spell(self, spell_id: str) -> SpellDefinition:
        """Mark a spell as LEARNED and emit a SPELL_LEARNED event."""
        with self._lock:
            spell = self._spells.get(spell_id)
            if spell is None:
                raise KeyError(f"Spell not found: {spell_id}")
            spell.spell_status = SpellStatus.LEARNED
            self._emit_event(
                MagicEventKind.SPELL_LEARNED,
                {"spell_id": spell_id, "name": spell.name},
                f"Spell learned: {spell.name}",
            )
            return spell

    def equip_spell(self, spell_id: str) -> SpellDefinition:
        """Mark a spell as EQUIPPED (must be learned or active first)."""
        with self._lock:
            spell = self._spells.get(spell_id)
            if spell is None:
                raise KeyError(f"Spell not found: {spell_id}")
            spell.spell_status = SpellStatus.EQUIPPED
            return spell

    # ------------------------------------------------------------------
    # Casting
    # ------------------------------------------------------------------

    def cast_spell(
        self,
        spell_id: str,
        caster_id: str,
        target_id: Optional[str] = None,
        target_position: Optional[Dict[str, float]] = None,
    ) -> CastingInstance:
        """Attempt to cast a spell, validating status, resources, and cooldowns."""
        with self._lock:
            spell = self._spells.get(spell_id)
            if spell is None:
                failed = CastingInstance(
                    spell_id=spell_id,
                    caster_id=caster_id,
                    target_id=target_id,
                    target_position=target_position,
                    state=CastingState.FAILED,
                )
                self._record_failed_cast(failed, "spell_not_found")
                return failed

            # Spell must be in a usable status.
            if spell.spell_status not in (
                SpellStatus.LEARNED,
                SpellStatus.EQUIPPED,
                SpellStatus.ACTIVE,
            ):
                failed = CastingInstance(
                    spell_id=spell_id,
                    caster_id=caster_id,
                    target_id=target_id,
                    target_position=target_position,
                    state=CastingState.FAILED,
                )
                self._record_failed_cast(failed, "spell_not_usable")
                return failed

            # Cooldown check.
            cd_key = f"{caster_id}:{spell_id}"
            existing_cd = self._cooldowns.get(cd_key)
            if existing_cd is not None and existing_cd.remaining > 0:
                failed = CastingInstance(
                    spell_id=spell_id,
                    caster_id=caster_id,
                    target_id=target_id,
                    target_position=target_position,
                    state=CastingState.FAILED,
                )
                self._record_failed_cast(failed, "on_cooldown")
                return failed

            # Resource check: mana and energy.
            consumed: Dict[str, float] = {}
            if spell.mana_cost > 0:
                mana_pool = self._resource_pools.get(f"{caster_id}:{ResourceType.MANA.value}")
                if mana_pool is None or mana_pool.current < spell.mana_cost:
                    failed = CastingInstance(
                        spell_id=spell_id,
                        caster_id=caster_id,
                        target_id=target_id,
                        target_position=target_position,
                        state=CastingState.FAILED,
                    )
                    self._record_failed_cast(failed, "insufficient_mana")
                    return failed
                consumed["mana"] = spell.mana_cost
            if spell.energy_cost > 0:
                energy_pool = self._resource_pools.get(f"{caster_id}:{ResourceType.ENERGY.value}")
                if energy_pool is None or energy_pool.current < spell.energy_cost:
                    failed = CastingInstance(
                        spell_id=spell_id,
                        caster_id=caster_id,
                        target_id=target_id,
                        target_position=target_position,
                        state=CastingState.FAILED,
                    )
                    self._record_failed_cast(failed, "insufficient_energy")
                    return failed
                consumed["energy"] = spell.energy_cost

            # Evict oldest cast if capacity reached.
            if len(self._casts) >= _MAX_CASTS:
                oldest_id = next(iter(self._casts), None)
                if oldest_id is not None:
                    self._casts.pop(oldest_id, None)

            # Consume resources now (cast is committed).
            if "mana" in consumed:
                mana_pool = self._resource_pools.get(f"{caster_id}:{ResourceType.MANA.value}")
                if mana_pool is not None:
                    mana_pool.current = max(0.0, mana_pool.current - consumed["mana"])
                    self._emit_event(
                        MagicEventKind.RESOURCE_CONSUMED,
                        {
                            "entity_id": caster_id,
                            "resource": ResourceType.MANA.value,
                            "amount": consumed["mana"],
                            "remaining": mana_pool.current,
                        },
                        f"Consumed {consumed['mana']} mana from {caster_id}",
                    )
            if "energy" in consumed:
                energy_pool = self._resource_pools.get(f"{caster_id}:{ResourceType.ENERGY.value}")
                if energy_pool is not None:
                    energy_pool.current = max(0.0, energy_pool.current - consumed["energy"])
                    self._emit_event(
                        MagicEventKind.RESOURCE_CONSUMED,
                        {
                            "entity_id": caster_id,
                            "resource": ResourceType.ENERGY.value,
                            "amount": consumed["energy"],
                            "remaining": energy_pool.current,
                        },
                        f"Consumed {consumed['energy']} energy from {caster_id}",
                    )

            cast = CastingInstance(
                spell_id=spell_id,
                caster_id=caster_id,
                target_id=target_id,
                target_position=target_position,
                start_time=_now_epoch(),
                consumed_resources=dict(consumed),
            )

            spell.cast_count += 1
            self._total_casts += 1

            # Instant cast: apply effects immediately and start cooldown.
            if spell.cast_time <= 0:
                self._apply_spell_effects_internal(spell_id, caster_id, target_id)
                self._start_cooldown(spell, caster_id)
                cast.state = CastingState.READY
                cast.progress = 1.0
                cast.end_time = _now_epoch()
                self._successful_casts += 1
                self._emit_event(
                    MagicEventKind.SPELL_CAST,
                    {
                        "cast_id": cast.id,
                        "spell_id": spell_id,
                        "caster_id": caster_id,
                        "target_id": target_id,
                        "instant": True,
                    },
                    f"Instant cast: {spell.name}",
                )
            else:
                cast.state = CastingState.CASTING
                cast.progress = 0.0
                cast.end_time = cast.start_time + spell.cast_time
                self._emit_event(
                    MagicEventKind.SPELL_CAST,
                    {
                        "cast_id": cast.id,
                        "spell_id": spell_id,
                        "caster_id": caster_id,
                        "target_id": target_id,
                        "instant": False,
                    },
                    f"Cast started: {spell.name}",
                )

            self._casts[cast.id] = cast
            return cast

    def _record_failed_cast(self, cast: CastingInstance, reason: str) -> None:
        """Record a failed cast and emit a CAST_FAILED event."""
        self._total_casts += 1
        self._failed_casts += 1
        if len(self._casts) >= _MAX_CASTS:
            oldest_id = next(iter(self._casts), None)
            if oldest_id is not None:
                self._casts.pop(oldest_id, None)
        self._casts[cast.id] = cast
        self._emit_event(
            MagicEventKind.CAST_FAILED,
            {
                "cast_id": cast.id,
                "spell_id": cast.spell_id,
                "caster_id": cast.caster_id,
                "reason": reason,
            },
            f"Cast failed ({reason})",
        )

    def _start_cooldown(self, spell: SpellDefinition, caster_id: str) -> None:
        """Start a cooldown record for a spell if it has a non-zero cooldown."""
        if spell.cooldown <= 0:
            return
        cd_key = f"{caster_id}:{spell.id}"
        now = _now_epoch()
        record = CooldownRecord(
            spell_id=spell.id,
            caster_id=caster_id,
            start_time=now,
            end_time=now + spell.cooldown,
            remaining=spell.cooldown,
            duration=spell.cooldown,
        )
        if len(self._cooldowns) >= _MAX_COOLDOWNS:
            oldest_key = next(iter(self._cooldowns), None)
            if oldest_key is not None:
                self._cooldowns.pop(oldest_key, None)
        self._cooldowns[cd_key] = record
        self._emit_event(
            MagicEventKind.COOLDOWN_STARTED,
            {
                "spell_id": spell.id,
                "caster_id": caster_id,
                "duration": spell.cooldown,
            },
            f"Cooldown started for {spell.name}",
        )

    def cancel_cast(self, cast_id: str) -> Optional[CastingInstance]:
        """Cancel an in-flight cast, marking it INTERRUPTED."""
        with self._lock:
            cast = self._casts.get(cast_id)
            if cast is None:
                return None
            if cast.state == CastingState.CASTING or cast.state == CastingState.CHANNELING:
                cast.state = CastingState.INTERRUPTED
            return cast

    def get_cast(self, cast_id: str) -> Optional[CastingInstance]:
        """Return a cast by id."""
        with self._lock:
            return self._casts.get(cast_id)

    def list_casts(self, caster_id: Optional[str] = None) -> List[CastingInstance]:
        """Return casts optionally filtered by caster."""
        with self._lock:
            casts = list(self._casts.values())
        if caster_id is None:
            return casts
        return [c for c in casts if c.caster_id == caster_id]

    def tick_casting(self, delta_time: float) -> List[CastingInstance]:
        """Advance all CASTING casts by delta_time; finish completed ones.

        When a cast reaches progress 1.0, its effects are applied, its
        state is set to READY, its cooldown is started, and any chains
        whose trigger is this spell are fired.
        """
        if delta_time <= 0:
            return []
        finished: List[CastingInstance] = []
        with self._lock:
            for cast in list(self._casts.values()):
                if cast.state != CastingState.CASTING:
                    continue
                spell = self._spells.get(cast.spell_id)
                if spell is None:
                    cast.state = CastingState.FAILED
                    continue
                if spell.cast_time > 0:
                    cast.progress += delta_time / spell.cast_time
                else:
                    cast.progress = 1.0
                if cast.progress >= 1.0:
                    cast.progress = 1.0
                    cast.end_time = _now_epoch()
                    cast.state = CastingState.READY
                    self._successful_casts += 1
                    self._apply_spell_effects_internal(
                        cast.spell_id, cast.caster_id, cast.target_id
                    )
                    self._start_cooldown(spell, cast.caster_id)
                    self._trigger_chains_for_spell(cast.spell_id, cast.caster_id, cast.target_id)
                    finished.append(cast)
        return finished

    # ------------------------------------------------------------------
    # Cooldowns
    # ------------------------------------------------------------------

    def tick_cooldowns(self, delta_time: float) -> List[CooldownRecord]:
        """Advance all active cooldowns by delta_time; return finished records."""
        if delta_time <= 0:
            return []
        finished: List[CooldownRecord] = []
        with self._lock:
            expired_keys: List[str] = []
            for key, record in self._cooldowns.items():
                if record.remaining <= 0:
                    continue
                record.remaining = max(0.0, record.remaining - delta_time)
                if record.remaining <= 0:
                    finished.append(record)
                    expired_keys.append(key)
            for key in expired_keys:
                record = self._cooldowns.pop(key, None)
                if record is not None:
                    self._emit_event(
                        MagicEventKind.COOLDOWN_FINISHED,
                        {
                            "spell_id": record.spell_id,
                            "caster_id": record.caster_id,
                        },
                        f"Cooldown finished for spell {record.spell_id}",
                    )
        return finished

    def get_cooldown(self, spell_id: str, caster_id: str) -> Optional[CooldownRecord]:
        """Return the cooldown record for a spell/caster pair, if any."""
        with self._lock:
            return self._cooldowns.get(f"{caster_id}:{spell_id}")

    def list_cooldowns(self, caster_id: Optional[str] = None) -> List[CooldownRecord]:
        """Return cooldown records optionally filtered by caster."""
        with self._lock:
            records = list(self._cooldowns.values())
        if caster_id is None:
            return records
        return [r for r in records if r.caster_id == caster_id]

    # ------------------------------------------------------------------
    # Resource Pools
    # ------------------------------------------------------------------

    def create_resource_pool(
        self,
        entity_id: str,
        resource_type: ResourceType,
        maximum: float,
        regen_rate: float,
    ) -> ResourcePool:
        """Create a new resource pool, initializing current to maximum."""
        with self._lock:
            if len(self._resource_pools) >= _MAX_RESOURCE_POOLS:
                oldest_key = next(iter(self._resource_pools), None)
                if oldest_key is not None:
                    self._resource_pools.pop(oldest_key, None)
            pool = ResourcePool(
                entity_id=entity_id,
                resource_type=resource_type,
                current=maximum,
                maximum=maximum,
                regen_rate=regen_rate,
                regen_delay=0.0,
                last_regen_time=_now_epoch(),
            )
            self._resource_pools[f"{entity_id}:{resource_type.value}"] = pool
            return pool

    def get_resource_pool(
        self,
        entity_id: str,
        resource_type: ResourceType,
    ) -> Optional[ResourcePool]:
        """Return the resource pool for an entity and resource type."""
        with self._lock:
            return self._resource_pools.get(f"{entity_id}:{resource_type.value}")

    def consume_resource(
        self,
        entity_id: str,
        resource_type: ResourceType,
        amount: float,
    ) -> ResourcePool:
        """Consume amount from a resource pool, clamping at 0."""
        with self._lock:
            pool = self._resource_pools.get(f"{entity_id}:{resource_type.value}")
            if pool is None:
                raise KeyError(
                    f"Resource pool not found: {entity_id}:{resource_type.value}"
                )
            pool.current = max(0.0, pool.current - amount)
            self._emit_event(
                MagicEventKind.RESOURCE_CONSUMED,
                {
                    "entity_id": entity_id,
                    "resource": resource_type.value,
                    "amount": amount,
                    "remaining": pool.current,
                },
                f"Consumed {amount} {resource_type.value} from {entity_id}",
            )
            return pool

    def restore_resource(
        self,
        entity_id: str,
        resource_type: ResourceType,
        amount: float,
    ) -> ResourcePool:
        """Restore amount to a resource pool, clamping at maximum."""
        with self._lock:
            pool = self._resource_pools.get(f"{entity_id}:{resource_type.value}")
            if pool is None:
                raise KeyError(
                    f"Resource pool not found: {entity_id}:{resource_type.value}"
                )
            pool.current = min(pool.maximum, pool.current + amount)
            self._emit_event(
                MagicEventKind.RESOURCE_RESTORED,
                {
                    "entity_id": entity_id,
                    "resource": resource_type.value,
                    "amount": amount,
                    "remaining": pool.current,
                },
                f"Restored {amount} {resource_type.value} to {entity_id}",
            )
            return pool

    def set_resource(
        self,
        entity_id: str,
        resource_type: ResourceType,
        value: float,
    ) -> ResourcePool:
        """Set a resource pool's current value, clamped to [0, maximum]."""
        with self._lock:
            pool = self._resource_pools.get(f"{entity_id}:{resource_type.value}")
            if pool is None:
                raise KeyError(
                    f"Resource pool not found: {entity_id}:{resource_type.value}"
                )
            pool.current = max(0.0, min(pool.maximum, value))
            return pool

    def tick_resources(self, delta_time: float) -> List[ResourcePool]:
        """Regenerate all resource pools based on regen_rate.

        Only regenerates if regen_delay seconds have elapsed since the
        last regen tick for the pool. Pools with regen_rate <= 0 are
        skipped. Clamps current at maximum.
        """
        if delta_time <= 0:
            return []
        updated: List[ResourcePool] = []
        now = _now_epoch()
        with self._lock:
            for pool in self._resource_pools.values():
                if pool.regen_rate <= 0:
                    continue
                if pool.regen_delay > 0 and (now - pool.last_regen_time) < pool.regen_delay:
                    continue
                if pool.current >= pool.maximum:
                    continue
                pool.current = min(
                    pool.maximum, pool.current + pool.regen_rate * delta_time
                )
                pool.last_regen_time = now
                updated.append(pool)
        return updated

    # ------------------------------------------------------------------
    # Casting Chains
    # ------------------------------------------------------------------

    def register_chain(
        self,
        name: str,
        trigger_spell_id: str,
        chained_spell_ids: List[str],
        chain_delay: float,
        conditions: Dict[str, Any],
    ) -> CastingChain:
        """Register a casting chain that triggers follow-up spells."""
        with self._lock:
            if len(self._chains) >= _MAX_CHAINS:
                oldest_id = next(iter(self._chains), None)
                if oldest_id is not None:
                    self._chains.pop(oldest_id, None)
            chain = CastingChain(
                name=name,
                trigger_spell_id=trigger_spell_id,
                chained_spell_ids=list(chained_spell_ids),
                chain_delay=chain_delay,
                conditions=dict(conditions) if conditions else {},
            )
            self._chains[chain.id] = chain
            return chain

    def list_chains(self) -> List[CastingChain]:
        """Return all registered chains."""
        with self._lock:
            return list(self._chains.values())

    def get_chain(self, chain_id: str) -> Optional[CastingChain]:
        """Return a chain by id."""
        with self._lock:
            return self._chains.get(chain_id)

    def trigger_chain(
        self,
        spell_id: str,
        caster_id: str,
        target_id: Optional[str],
    ) -> List[str]:
        """Trigger all chains whose trigger spell matches spell_id.

        Each chained spell is cast with zero mana cost. Returns the list
        of chained spell IDs that were successfully triggered.
        """
        triggered: List[str] = []
        with self._lock:
            for chain in self._chains.values():
                if chain.trigger_spell_id != spell_id:
                    continue
                # Evaluate conditions: empty conditions always pass.
                if not self._evaluate_chain_conditions(chain, caster_id, target_id):
                    continue
                for chained_id in chain.chained_spell_ids:
                    chained_spell = self._spells.get(chained_id)
                    if chained_spell is None:
                        continue
                    # Temporarily zero the mana cost so the chained spell casts for free.
                    original_cost = chained_spell.mana_cost
                    chained_spell.mana_cost = 0.0
                    try:
                        cast = self.cast_spell(chained_id, caster_id, target_id)
                        if cast.state != CastingState.FAILED:
                            triggered.append(chained_id)
                    finally:
                        chained_spell.mana_cost = original_cost
                self._emit_event(
                    MagicEventKind.CHAIN_TRIGGERED,
                    {
                        "chain_id": chain.id,
                        "trigger_spell_id": spell_id,
                        "chained_spell_ids": triggered,
                        "caster_id": caster_id,
                    },
                    f"Chain triggered: {chain.name}",
                )
        return triggered

    def _trigger_chains_for_spell(
        self,
        spell_id: str,
        caster_id: str,
        target_id: Optional[str],
    ) -> None:
        """Internal helper to fire all chains triggered by a resolved spell."""
        for chain in self._chains.values():
            if chain.trigger_spell_id != spell_id:
                continue
            if not self._evaluate_chain_conditions(chain, caster_id, target_id):
                continue
            for chained_id in chain.chained_spell_ids:
                chained_spell = self._spells.get(chained_id)
                if chained_spell is None:
                    continue
                original_cost = chained_spell.mana_cost
                chained_spell.mana_cost = 0.0
                try:
                    self.cast_spell(chained_id, caster_id, target_id)
                finally:
                    chained_spell.mana_cost = original_cost
            self._emit_event(
                MagicEventKind.CHAIN_TRIGGERED,
                {
                    "chain_id": chain.id,
                    "trigger_spell_id": spell_id,
                    "chained_spell_ids": list(chain.chained_spell_ids),
                    "caster_id": caster_id,
                },
                f"Chain triggered for {spell_id}",
            )

    def _evaluate_chain_conditions(
        self,
        chain: CastingChain,
        caster_id: str,
        target_id: Optional[str],
    ) -> bool:
        """Evaluate chain conditions. Empty conditions always pass.

        Supported condition keys:
          - "auto": when True the chain always fires automatically.
          - "min_chained": minimum number of chained spells that must exist.
          - "caster": required caster id.
        """
        if not chain.conditions:
            return True
        if chain.conditions.get("auto"):
            return True
        required_caster = chain.conditions.get("caster")
        if required_caster is not None and required_caster != caster_id:
            return False
        min_chained = chain.conditions.get("min_chained")
        if min_chained is not None and len(chain.chained_spell_ids) < int(min_chained):
            return False
        return True

    # ------------------------------------------------------------------
    # Spell Effects
    # ------------------------------------------------------------------

    def apply_spell_effects(
        self,
        spell_id: str,
        caster_id: str,
        target_id: str,
    ) -> List[SpellEffect]:
        """Compute and return the effects produced by a spell.

        Effects with a chance < 1.0 are probabilistically included.
        """
        with self._lock:
            return self._apply_spell_effects_internal(spell_id, caster_id, target_id)

    def _apply_spell_effects_internal(
        self,
        spell_id: str,
        caster_id: str,
        target_id: Optional[str],
    ) -> List[SpellEffect]:
        """Internal effect application that emits EFFECT_APPLIED events."""
        spell = self._spells.get(spell_id)
        if spell is None:
            return []
        applied: List[SpellEffect] = []
        import random as _random
        for effect in spell.effects:
            # Probabilistic inclusion based on effect chance.
            if effect.chance < 1.0 and _random.random() > effect.chance:
                continue
            applied.append(effect)
            self._emit_event(
                MagicEventKind.EFFECT_APPLIED,
                {
                    "spell_id": spell_id,
                    "effect_id": effect.id,
                    "effect_type": effect.effect_type.value,
                    "value": effect.value,
                    "caster_id": caster_id,
                    "target_id": target_id,
                },
                f"Effect applied: {effect.effect_type.value}",
            )
        return applied

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _emit_event(
        self,
        kind: MagicEventKind,
        data: Dict[str, Any],
        description: str = "",
    ) -> MagicEvent:
        """Record an audit event (caller must hold self._lock)."""
        event = MagicEvent(
            kind=kind,
            data=dict(data) if data else {},
            description=description,
        )
        self._events.append(event)
        return event

    def list_events(
        self,
        kind: Optional[MagicEventKind] = None,
        limit: int = 100,
    ) -> List[MagicEvent]:
        """Return audit events optionally filtered by kind, limited to limit."""
        with self._lock:
            events = list(self._events)
        if kind is not None:
            events = [e for e in events if e.kind == kind]
        if limit > 0:
            events = events[-limit:]
        return events

    # ------------------------------------------------------------------
    # Stats / Status / Snapshot
    # ------------------------------------------------------------------

    def get_stats(self) -> MagicStats:
        """Compute and return aggregate magic system stats."""
        with self._lock:
            by_school: Dict[str, int] = {}
            by_tier: Dict[str, int] = {}
            for spell in self._spells.values():
                school_key = spell.school.value
                tier_key = spell.tier.value
                by_school[school_key] = by_school.get(school_key, 0) + 1
                by_tier[tier_key] = by_tier.get(tier_key, 0) + 1
            active_cooldowns = sum(
                1 for r in self._cooldowns.values() if r.remaining > 0
            )
            return MagicStats(
                total_spells=len(self._spells),
                total_casts=self._total_casts,
                successful_casts=self._successful_casts,
                failed_casts=self._failed_casts,
                active_cooldowns=active_cooldowns,
                total_resource_pools=len(self._resource_pools),
                total_chains=len(self._chains),
                by_school=by_school,
                by_tier=by_tier,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current magic system state."""
        with self._lock:
            stats = self.get_stats()
            return {
                "initialized": self._initialized,
                "total_spells": len(self._spells),
                "total_casts": len(self._casts),
                "active_casts": sum(
                    1 for c in self._casts.values()
                    if c.state == CastingState.CASTING
                ),
                "total_cooldowns": len(self._cooldowns),
                "active_cooldowns": sum(
                    1 for r in self._cooldowns.values() if r.remaining > 0
                ),
                "total_resource_pools": len(self._resource_pools),
                "total_chains": len(self._chains),
                "total_events": len(self._events),
                "stats": stats.to_dict(),
            }

    def get_snapshot(self) -> MagicSnapshot:
        """Capture an immutable snapshot of the magic system state."""
        with self._lock:
            stats = self.get_stats()
            return MagicSnapshot(
                spells=list(self._spells.values()),
                casts=list(self._casts.values()),
                cooldowns=list(self._cooldowns.values()),
                resource_pools=list(self._resource_pools.values()),
                chains=list(self._chains.values()),
                stats=stats,
                timestamp=_now_ts(),
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all spells, casts, cooldowns, resource pools, chains, and events.

        Restores the engine to its initial state, including the seed data.
        """
        with self._lock:
            self._spells.clear()
            self._casts.clear()
            self._cooldowns.clear()
            self._resource_pools.clear()
            self._chains.clear()
            self._events.clear()
            self._total_casts = 0
            self._successful_casts = 0
            self._failed_casts = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_magic_system_engine() -> MagicSystemEngine:
    """Return the singleton MagicSystemEngine instance."""
    return MagicSystemEngine.get_instance()
