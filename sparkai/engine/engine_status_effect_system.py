"""
SparkLabs Engine - Status Effect and Resistance System

A comprehensive Status Effect, Resistance, and Immunity system for the
SparkLabs AI-native game engine. Manages status effect definitions,
elemental resistances and immunities, effect stacking policies, effect
chains, and per-entity effect application with full resistance and
susceptibility calculations.

Architecture:
  StatusEffectSystemEngine (singleton)
    |-- StatusEffectDefinition   — registered effect template
    |-- ActiveEffect             — effect instance applied to an entity
    |-- ResistanceProfile        — per-entity resistances/immunities/susceptibility
    |-- EffectChain              — triggered follow-up effect sequence
    |-- StatusEffectStats        — aggregate counters
    |-- StatusEffectSnapshot     — immutable state snapshot
    |-- StatusEffectEvent        — audit log entry
    |-- EffectCategory           — 4 effect categories
    |-- EffectElement            — 15 elemental schools
    |-- StackingPolicy           — 6 stacking behaviors
    |-- DispelType               — 7 dispel classifications
    |-- EffectSeverity           — 5 severity tiers
    |-- ResistanceTier           — 6 resistance classifications
    |-- StatusEffectEventKind    — 10 audit event kinds

Core Capabilities:
  - register_effect / list_effects / get_effect: effect registry management
  - create_resistance_profile / set_resistance / set_immunity / set_susceptibility
  - apply_effect: immunity checks, resistance mitigation, stacking resolution
  - tick_effects: advance durations, process damage/heal ticks, expire + chain
  - dispel_effect / dispel_by_category / dispel_by_element / refresh_effect
  - register_chain / trigger_chain: chained follow-up effects
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

_MAX_EFFECTS = 2000
_MAX_ENTITY_EFFECTS = 10000
_MAX_RESISTANCES = 5000
_MAX_CHAINS = 500
_MAX_EVENTS = 2000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return _datetime.datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value to the inclusive [low, high] range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _expires_in(seconds: float) -> str:
    """Return an ISO-8601 UTC timestamp 'seconds' from now."""
    delta = _datetime.timedelta(seconds=max(0.0, seconds))
    return (_datetime.datetime.utcnow() + delta).isoformat() + "Z"


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class EffectCategory(Enum):
    """Top-level classification of a status effect."""
    DEBUFF = "debuff"
    BUFF = "buff"
    NEUTRAL = "neutral"
    SPECIAL = "special"


class EffectElement(Enum):
    """Elemental schools governing resistance and immunity interactions."""
    PHYSICAL = "physical"
    FIRE = "fire"
    FROST = "frost"
    LIGHTNING = "lightning"
    NATURE = "nature"
    SHADOW = "shadow"
    HOLY = "holy"
    ARCANE = "arcane"
    POISON = "poison"
    ACID = "acid"
    EARTH = "earth"
    AIR = "air"
    WATER = "water"
    MENTAL = "mental"
    TRUE = "true"


class StackingPolicy(Enum):
    """Behavior when an effect is re-applied to an entity already affected."""
    NO_STACK = "no_stack"
    STACK_REFRESH = "stack_refresh"
    STACK_DURATION = "stack_duration"
    STACK_INTENSITY = "stack_intensity"
    STACK_BOTH = "stack_both"
    REPLACE = "replace"


class DispelType(Enum):
    """Classification determining how an effect may be removed."""
    UNDISPELLABLE = "undispellable"
    MAGIC = "magic"
    CURSE = "curse"
    POISON = "poison"
    DISEASE = "disease"
    PHYSICAL = "physical"
    ENCHANTMENT = "enchantment"


class EffectSeverity(Enum):
    """Relative power tier of a status effect."""
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    SEVERE = "severe"
    EXTREME = "extreme"


class ResistanceTier(Enum):
    """Qualitative bucket for a numeric resistance or susceptibility value."""
    IMMUNE = "immune"
    HIGHLY_RESISTANT = "highly_resistant"
    RESISTANT = "resistant"
    NORMAL = "normal"
    SUSCEPTIBLE = "susceptible"
    HIGHLY_SUSCEPTIBLE = "highly_susceptible"


class StatusEffectEventKind(Enum):
    """Audit event kinds emitted by the status effect system."""
    EFFECT_REGISTERED = "effect_registered"
    EFFECT_APPLIED = "effect_applied"
    EFFECT_TICKED = "effect_ticked"
    EFFECT_EXPIRED = "effect_expired"
    EFFECT_DISPELLED = "effect_dispelled"
    EFFECT_REFRESHED = "effect_refreshed"
    RESISTANCE_SET = "resistance_set"
    IMMUNITY_SET = "immunity_set"
    CHAIN_TRIGGERED = "chain_triggered"
    CHAIN_COMPLETED = "chain_completed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class StatusEffectDefinition:
    """A registered status effect template describing behavior and metadata."""
    effect_id: str = field(default_factory=lambda: _new_id("eff"))
    name: str = ""
    description: str = ""
    category: EffectCategory = EffectCategory.DEBUFF
    element: EffectElement = EffectElement.PHYSICAL
    severity: EffectSeverity = EffectSeverity.MODERATE
    stacking_policy: StackingPolicy = StackingPolicy.NO_STACK
    dispel_type: DispelType = DispelType.MAGIC
    base_duration: float = 0.0
    tick_interval: float = 1.0
    base_intensity: float = 1.0
    stat_modifiers: Dict[str, float] = field(default_factory=dict)
    damage_per_tick: float = 0.0
    heal_per_tick: float = 0.0
    dispellable: bool = True
    chain_effect_id: Optional[str] = None
    icon: str = ""
    color: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "element": self.element.value,
            "severity": self.severity.value,
            "stacking_policy": self.stacking_policy.value,
            "dispel_type": self.dispel_type.value,
            "base_duration": self.base_duration,
            "tick_interval": self.tick_interval,
            "base_intensity": self.base_intensity,
            "stat_modifiers": dict(self.stat_modifiers),
            "damage_per_tick": self.damage_per_tick,
            "heal_per_tick": self.heal_per_tick,
            "dispellable": self.dispellable,
            "chain_effect_id": self.chain_effect_id,
            "icon": self.icon,
            "color": self.color,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class ActiveEffect:
    """A live status effect instance applied to a specific entity."""
    active_id: str = field(default_factory=lambda: _new_id("active"))
    entity_id: str = ""
    effect_id: str = ""
    effect_name: str = ""
    category: EffectCategory = EffectCategory.DEBUFF
    element: EffectElement = EffectElement.PHYSICAL
    remaining_duration: float = 0.0
    current_intensity: float = 1.0
    tick_timer: float = 0.0
    stacks: int = 1
    applied_at: str = field(default_factory=_now)
    expires_at: str = ""
    source_entity_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_id": self.active_id,
            "entity_id": self.entity_id,
            "effect_id": self.effect_id,
            "effect_name": self.effect_name,
            "category": self.category.value,
            "element": self.element.value,
            "remaining_duration": self.remaining_duration,
            "current_intensity": self.current_intensity,
            "tick_timer": self.tick_timer,
            "stacks": self.stacks,
            "applied_at": self.applied_at,
            "expires_at": self.expires_at,
            "source_entity_id": self.source_entity_id,
            "metadata": dict(self.metadata),
        }


@dataclass
class ResistanceProfile:
    """Per-entity resistance, immunity, and susceptibility configuration."""
    profile_id: str = field(default_factory=lambda: _new_id("res"))
    entity_id: str = ""
    resistances: Dict[EffectElement, float] = field(default_factory=dict)
    immunities: List[EffectElement] = field(default_factory=list)
    susceptibility: Dict[EffectElement, float] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "entity_id": self.entity_id,
            "resistances": {k.value: v for k, v in self.resistances.items()},
            "immunities": [e.value for e in self.immunities],
            "susceptibility": {k.value: v for k, v in self.susceptibility.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class EffectChain:
    """A sequence of follow-up effects triggered when an effect expires."""
    chain_id: str = field(default_factory=lambda: _new_id("chain"))
    name: str = ""
    trigger_effect_id: str = ""
    chained_effect_ids: List[str] = field(default_factory=list)
    chain_delay: float = 0.5
    propagation_type: str = "sequential"
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "trigger_effect_id": self.trigger_effect_id,
            "chained_effect_ids": list(self.chained_effect_ids),
            "chain_delay": self.chain_delay,
            "propagation_type": self.propagation_type,
            "created_at": self.created_at,
        }


@dataclass
class StatusEffectStats:
    """Aggregate counters describing status effect system usage."""
    total_definitions: int = 0
    total_active_effects: int = 0
    total_resistance_profiles: int = 0
    total_chains: int = 0
    active_by_category: Dict[str, int] = field(default_factory=dict)
    active_by_element: Dict[str, int] = field(default_factory=dict)
    avg_duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_definitions": self.total_definitions,
            "total_active_effects": self.total_active_effects,
            "total_resistance_profiles": self.total_resistance_profiles,
            "total_chains": self.total_chains,
            "active_by_category": dict(self.active_by_category),
            "active_by_element": dict(self.active_by_element),
            "avg_duration": self.avg_duration,
        }


@dataclass
class StatusEffectEvent:
    """An audit log entry emitted by the status effect system."""
    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: StatusEffectEventKind = StatusEffectEventKind.EFFECT_REGISTERED
    timestamp: str = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
        }


@dataclass
class StatusEffectSnapshot:
    """An immutable snapshot of the status effect system's state."""
    initialized: bool = False
    definitions: List[StatusEffectDefinition] = field(default_factory=list)
    active_effects: List[ActiveEffect] = field(default_factory=list)
    resistance_profiles: List[ResistanceProfile] = field(default_factory=list)
    chains: List[EffectChain] = field(default_factory=list)
    events: List[StatusEffectEvent] = field(default_factory=list)
    stats: StatusEffectStats = field(default_factory=StatusEffectStats)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initialized": self.initialized,
            "definitions": [d.to_dict() for d in self.definitions],
            "active_effects": [a.to_dict() for a in self.active_effects],
            "resistance_profiles": [r.to_dict() for r in self.resistance_profiles],
            "chains": [c.to_dict() for c in self.chains],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


# ---------------------------------------------------------------------------
# StatusEffectSystemEngine — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class StatusEffectSystemEngine:
    """
    Central engine for managing status effect definitions, active effects on
    entities, elemental resistance profiles, and effect chains within the
    SparkLabs AI-native game engine.

    Thread-safe via a reentrant lock. Use get_status_effect_system() or
    StatusEffectSystemEngine.get_instance() to obtain the singleton.

    Usage:
        engine = get_status_effect_system()
        poison = engine.register_effect("Poison", ..., element=EffectElement.POISON)
        engine.create_resistance_profile("player_1", resistances={EffectElement.FIRE: 0.5})
        engine.apply_effect("player_1", poison.effect_id, source_entity_id="trap_1")
        engine.tick_effects(0.1)
    """

    _instance: Optional["StatusEffectSystemEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "StatusEffectSystemEngine":
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

            # Status effect definitions keyed by effect id.
            self._definitions: Dict[str, StatusEffectDefinition] = {}
            # Active effects keyed by active id.
            self._active_effects: Dict[str, ActiveEffect] = {}
            # Resistance profiles keyed by entity id.
            self._resistance_profiles: Dict[str, ResistanceProfile] = {}
            # Effect chains keyed by chain id.
            self._chains: Dict[str, EffectChain] = {}
            # Audit events kept in FIFO order with capacity eviction.
            self._events: deque = deque(maxlen=_MAX_EVENTS)

            # Aggregate counters maintained for fast stats retrieval.
            self._total_definitions_registered: int = 0
            self._total_effects_applied: int = 0
            self._total_effects_expired: int = 0
            self._total_effects_dispelled: int = 0
            self._total_ticks_processed: int = 0
            self._total_chains_triggered: int = 0

            self._initialized: bool = True
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "StatusEffectSystemEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with seed effects, profiles, active effects, and a chain."""
        # 1. Poison — stacking damage-over-time debuff.
        poison = self.register_effect(
            name="Poison",
            description="A venomous toxin dealing damage over time and stacking in intensity.",
            category=EffectCategory.DEBUFF,
            element=EffectElement.POISON,
            severity=EffectSeverity.MODERATE,
            stacking_policy=StackingPolicy.STACK_INTENSITY,
            dispel_type=DispelType.POISON,
            base_duration=10.0,
            tick_interval=1.0,
            base_intensity=1.0,
            damage_per_tick=5.0,
            dispellable=True,
            tags=["dot", "venom"],
        )

        # 2. Burn — refreshing fire damage-over-time debuff.
        burn = self.register_effect(
            name="Burn",
            description="Searing flames that deal fire damage and refresh on reapplication.",
            category=EffectCategory.DEBUFF,
            element=EffectElement.FIRE,
            severity=EffectSeverity.MODERATE,
            stacking_policy=StackingPolicy.STACK_REFRESH,
            dispel_type=DispelType.MAGIC,
            base_duration=5.0,
            tick_interval=0.5,
            base_intensity=1.0,
            damage_per_tick=8.0,
            dispellable=True,
            tags=["dot", "fire"],
        )

        # 3. Freeze — hard slow that does not stack.
        freeze = self.register_effect(
            name="Freeze",
            description="Encases the target in ice, drastically reducing movement speed.",
            category=EffectCategory.DEBUFF,
            element=EffectElement.FROST,
            severity=EffectSeverity.MAJOR,
            stacking_policy=StackingPolicy.NO_STACK,
            dispel_type=DispelType.MAGIC,
            base_duration=3.0,
            tick_interval=1.0,
            base_intensity=1.0,
            stat_modifiers={"move_speed": -0.8},
            dispellable=True,
            tags=["control", "slow"],
        )

        # 4. Stun — severe hard control that cannot be dispelled.
        stun = self.register_effect(
            name="Stun",
            description="Renders the target unable to act for the duration.",
            category=EffectCategory.DEBUFF,
            element=EffectElement.PHYSICAL,
            severity=EffectSeverity.SEVERE,
            stacking_policy=StackingPolicy.NO_STACK,
            dispel_type=DispelType.PHYSICAL,
            base_duration=2.0,
            tick_interval=1.0,
            base_intensity=1.0,
            stat_modifiers={"action_speed": -1.0},
            dispellable=False,
            tags=["control", "hard_cc"],
        )

        # 5. Blessing of Strength — holy attack power buff that refreshes.
        blessing = self.register_effect(
            name="Blessing of Strength",
            description="A holy enchantment increasing attack power.",
            category=EffectCategory.BUFF,
            element=EffectElement.HOLY,
            severity=EffectSeverity.MODERATE,
            stacking_policy=StackingPolicy.STACK_REFRESH,
            dispel_type=DispelType.ENCHANTMENT,
            base_duration=30.0,
            tick_interval=1.0,
            base_intensity=1.0,
            stat_modifiers={"attack_power": 0.2},
            dispellable=True,
            tags=["buff", "holy"],
        )

        # 6. Haste — arcane speed buff that does not stack.
        haste = self.register_effect(
            name="Haste",
            description="Arcane acceleration boosting attack and movement speed.",
            category=EffectCategory.BUFF,
            element=EffectElement.ARCANE,
            severity=EffectSeverity.MAJOR,
            stacking_policy=StackingPolicy.NO_STACK,
            dispel_type=DispelType.MAGIC,
            base_duration=15.0,
            tick_interval=1.0,
            base_intensity=1.0,
            stat_modifiers={"attack_speed": 0.3, "move_speed": 0.2},
            dispellable=True,
            tags=["buff", "speed"],
        )

        # 7. Regeneration — healing-over-time that extends with reapplication.
        regen = self.register_effect(
            name="Regeneration",
            description="Natural mending restoring health over time, extending with reapplication.",
            category=EffectCategory.BUFF,
            element=EffectElement.NATURE,
            severity=EffectSeverity.MODERATE,
            stacking_policy=StackingPolicy.STACK_DURATION,
            dispel_type=DispelType.MAGIC,
            base_duration=10.0,
            tick_interval=1.0,
            base_intensity=1.0,
            heal_per_tick=10.0,
            dispellable=True,
            tags=["hot", "heal"],
        )

        # 8. Curse of Weakness — shadow curse sapping attack power.
        curse = self.register_effect(
            name="Curse of Weakness",
            description="A shadow curse sapping the target's attack power.",
            category=EffectCategory.DEBUFF,
            element=EffectElement.SHADOW,
            severity=EffectSeverity.MAJOR,
            stacking_policy=StackingPolicy.NO_STACK,
            dispel_type=DispelType.CURSE,
            base_duration=20.0,
            tick_interval=1.0,
            base_intensity=1.0,
            stat_modifiers={"attack_power": -0.3},
            dispellable=True,
            tags=["curse", "shadow"],
        )

        # Resistance profile 1: player_1.
        # Stun is a PHYSICAL-element effect, so PHYSICAL immunity grants Stun immunity.
        self.create_resistance_profile(
            entity_id="player_1",
            resistances={
                EffectElement.FIRE: 0.5,
                EffectElement.FROST: 0.3,
                EffectElement.POISON: 0.75,
            },
            immunities=[EffectElement.PHYSICAL],
            susceptibility={EffectElement.SHADOW: 1.5},
        )

        # Resistance profile 2: enemy_1.
        # Burn is a FIRE-element effect, so FIRE immunity grants Burn immunity.
        self.create_resistance_profile(
            entity_id="enemy_1",
            resistances={
                EffectElement.PHYSICAL: 0.2,
                EffectElement.FIRE: 0.9,
            },
            immunities=[EffectElement.FIRE],
            susceptibility={EffectElement.FROST: 1.5},
        )

        # Active effect 1: Poison already applied to player_1.
        poison_active = ActiveEffect(
            active_id=_new_id("active"),
            entity_id="player_1",
            effect_id=poison.effect_id,
            effect_name=poison.name,
            category=poison.category,
            element=poison.element,
            remaining_duration=8.0,
            current_intensity=1.0,
            tick_timer=0.5,
            stacks=1,
            applied_at=_now(),
            expires_at=_expires_in(8.0),
            source_entity_id="",
            metadata={"seed": True},
        )
        self._active_effects[poison_active.active_id] = poison_active

        # Active effect 2: Blessing of Strength already applied to player_1.
        blessing_active = ActiveEffect(
            active_id=_new_id("active"),
            entity_id="player_1",
            effect_id=blessing.effect_id,
            effect_name=blessing.name,
            category=blessing.category,
            element=blessing.element,
            remaining_duration=25.0,
            current_intensity=1.0,
            tick_timer=blessing.tick_interval,
            stacks=1,
            applied_at=_now(),
            expires_at=_expires_in(25.0),
            source_entity_id="",
            metadata={"seed": True},
        )
        self._active_effects[blessing_active.active_id] = blessing_active

        # Chain 1: Burn Spread — when Burn expires, chain to Poison and Freeze.
        self.register_chain(
            name="Burn Spread",
            trigger_effect_id=burn.effect_id,
            chained_effect_ids=[poison.effect_id, freeze.effect_id],
            chain_delay=0.5,
            propagation_type="sequential",
        )

    # ------------------------------------------------------------------
    # Effect Registry
    # ------------------------------------------------------------------

    def register_effect(
        self,
        name: str,
        description: str,
        category: EffectCategory,
        element: EffectElement,
        severity: EffectSeverity,
        stacking_policy: StackingPolicy,
        dispel_type: DispelType,
        base_duration: float,
        tick_interval: float = 1.0,
        base_intensity: float = 1.0,
        stat_modifiers: Optional[Dict[str, float]] = None,
        damage_per_tick: float = 0.0,
        heal_per_tick: float = 0.0,
        dispellable: bool = True,
        chain_effect_id: Optional[str] = None,
        icon: str = "",
        color: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StatusEffectDefinition:
        """Register a new status effect template and emit an EFFECT_REGISTERED event."""
        with self._lock:
            if len(self._definitions) >= _MAX_EFFECTS:
                # FIFO eviction: drop the oldest definition.
                oldest_id = next(iter(self._definitions), None)
                if oldest_id is not None:
                    self._definitions.pop(oldest_id, None)

            definition = StatusEffectDefinition(
                name=name,
                description=description,
                category=category,
                element=element,
                severity=severity,
                stacking_policy=stacking_policy,
                dispel_type=dispel_type,
                base_duration=base_duration,
                tick_interval=tick_interval,
                base_intensity=base_intensity,
                stat_modifiers=dict(stat_modifiers) if stat_modifiers else {},
                damage_per_tick=damage_per_tick,
                heal_per_tick=heal_per_tick,
                dispellable=dispellable,
                chain_effect_id=chain_effect_id,
                icon=icon,
                color=color,
                tags=list(tags) if tags else [],
                metadata=dict(metadata) if metadata else {},
            )
            self._definitions[definition.effect_id] = definition
            self._total_definitions_registered += 1
            self._record_event(
                StatusEffectEventKind.EFFECT_REGISTERED,
                {
                    "effect_id": definition.effect_id,
                    "name": name,
                    "element": element.value,
                    "category": category.value,
                },
            )
            return definition

    def list_effects(
        self,
        category: Optional[EffectCategory] = None,
        element: Optional[EffectElement] = None,
        severity: Optional[EffectSeverity] = None,
    ) -> List[StatusEffectDefinition]:
        """Return registered effects optionally filtered by category, element, and severity."""
        with self._lock:
            results: List[StatusEffectDefinition] = []
            for definition in self._definitions.values():
                if category is not None and definition.category != category:
                    continue
                if element is not None and definition.element != element:
                    continue
                if severity is not None and definition.severity != severity:
                    continue
                results.append(definition)
            return results

    def get_effect(self, effect_id: str) -> Optional[StatusEffectDefinition]:
        """Return a registered effect by id, or None if not found."""
        with self._lock:
            return self._definitions.get(effect_id)

    # ------------------------------------------------------------------
    # Resistance Profiles
    # ------------------------------------------------------------------

    def create_resistance_profile(
        self,
        entity_id: str,
        resistances: Optional[Dict[EffectElement, float]] = None,
        immunities: Optional[List[EffectElement]] = None,
        susceptibility: Optional[Dict[EffectElement, float]] = None,
    ) -> ResistanceProfile:
        """Create (or replace) a resistance profile for an entity.

        resistances maps EffectElement -> [0.0, 1.0] where 1.0 is full resistance.
        immunities is a list of elements the entity is fully immune to.
        susceptibility maps EffectElement -> [0.0, 2.0] where >1.0 amplifies effects.
        """
        with self._lock:
            if entity_id not in self._resistance_profiles:
                if len(self._resistance_profiles) >= _MAX_RESISTANCES:
                    # FIFO eviction: drop the oldest profile.
                    oldest_id = next(iter(self._resistance_profiles), None)
                    if oldest_id is not None:
                        self._resistance_profiles.pop(oldest_id, None)

            profile = ResistanceProfile(
                entity_id=entity_id,
                resistances=dict(resistances) if resistances else {},
                immunities=list(immunities) if immunities else [],
                susceptibility=dict(susceptibility) if susceptibility else {},
            )
            self._resistance_profiles[entity_id] = profile
            self._record_event(
                StatusEffectEventKind.RESISTANCE_SET,
                {
                    "entity_id": entity_id,
                    "action": "profile_created",
                    "resistances": len(profile.resistances),
                    "immunities": len(profile.immunities),
                },
            )
            return profile

    def get_resistance_profile(self, entity_id: str) -> Optional[ResistanceProfile]:
        """Return the resistance profile for an entity, or None if not found."""
        with self._lock:
            return self._resistance_profiles.get(entity_id)

    def list_resistance_profiles(self) -> List[ResistanceProfile]:
        """Return all registered resistance profiles."""
        with self._lock:
            return list(self._resistance_profiles.values())

    def set_resistance(
        self,
        entity_id: str,
        element: EffectElement,
        value: float,
    ) -> Optional[ResistanceProfile]:
        """Set the resistance value (0.0 to 1.0) for an element on an entity."""
        with self._lock:
            profile = self._resistance_profiles.get(entity_id)
            if profile is None:
                return None
            clamped = _clamp(value, 0.0, 1.0)
            profile.resistances[element] = clamped
            profile.updated_at = _now()
            tier = self._get_resistance_tier(clamped)
            self._record_event(
                StatusEffectEventKind.RESISTANCE_SET,
                {
                    "entity_id": entity_id,
                    "element": element.value,
                    "value": clamped,
                    "tier": tier.value,
                },
            )
            return profile

    def set_immunity(
        self,
        entity_id: str,
        element: EffectElement,
        immune: bool = True,
    ) -> Optional[ResistanceProfile]:
        """Add or remove an elemental immunity for an entity."""
        with self._lock:
            profile = self._resistance_profiles.get(entity_id)
            if profile is None:
                return None
            if immune:
                if element not in profile.immunities:
                    profile.immunities.append(element)
            else:
                if element in profile.immunities:
                    profile.immunities.remove(element)
            profile.updated_at = _now()
            self._record_event(
                StatusEffectEventKind.IMMUNITY_SET,
                {
                    "entity_id": entity_id,
                    "element": element.value,
                    "immune": immune,
                },
            )
            return profile

    def set_susceptibility(
        self,
        entity_id: str,
        element: EffectElement,
        value: float,
    ) -> Optional[ResistanceProfile]:
        """Set the susceptibility value (0.0 to 2.0, >1.0 amplifies) for an element."""
        with self._lock:
            profile = self._resistance_profiles.get(entity_id)
            if profile is None:
                return None
            clamped = _clamp(value, 0.0, 2.0)
            profile.susceptibility[element] = clamped
            profile.updated_at = _now()
            self._record_event(
                StatusEffectEventKind.RESISTANCE_SET,
                {
                    "entity_id": entity_id,
                    "element": element.value,
                    "susceptibility": clamped,
                },
            )
            return profile

    # ------------------------------------------------------------------
    # Effect Application
    # ------------------------------------------------------------------

    def apply_effect(
        self,
        entity_id: str,
        effect_id: str,
        source_entity_id: str = "",
        duration_override: Optional[float] = None,
        intensity_override: Optional[float] = None,
    ) -> Optional[ActiveEffect]:
        """Apply an effect to an entity with immunity and resistance resolution.

        Returns None if the effect is unknown, the entity is immune, or the
        stacking policy forbids stacking. Otherwise returns the active effect
        (newly created or updated in place for stack policies).
        """
        with self._lock:
            definition = self._definitions.get(effect_id)
            if definition is None:
                return None

            # Immunity check: fully immune elements reject the effect entirely.
            profile = self._resistance_profiles.get(entity_id)
            if profile is not None and definition.element in profile.immunities:
                return None

            # Resolve base values, allowing caller overrides.
            base_duration = (
                duration_override if duration_override is not None else definition.base_duration
            )
            base_intensity = (
                intensity_override if intensity_override is not None else definition.base_intensity
            )
            resisted_duration = self._compute_resisted_duration(
                base_duration, entity_id, definition.element
            )
            resisted_intensity = self._compute_resisted_intensity(
                base_intensity, entity_id, definition.element
            )

            # Locate any existing active instance of the same effect on the entity.
            existing: Optional[ActiveEffect] = None
            existing_id: Optional[str] = None
            for active_id, active in self._active_effects.items():
                if active.entity_id == entity_id and active.effect_id == effect_id:
                    existing = active
                    existing_id = active_id
                    break

            policy = definition.stacking_policy
            if existing is not None:
                if policy == StackingPolicy.NO_STACK:
                    return None
                if policy == StackingPolicy.STACK_REFRESH:
                    existing.remaining_duration = resisted_duration
                    existing.current_intensity = resisted_intensity
                    existing.tick_timer = definition.tick_interval
                    existing.stacks = 1
                    existing.expires_at = _expires_in(resisted_duration)
                    existing.source_entity_id = source_entity_id or existing.source_entity_id
                    self._total_effects_applied += 1
                    self._record_event(
                        StatusEffectEventKind.EFFECT_REFRESHED,
                        {
                            "active_id": existing.active_id,
                            "entity_id": entity_id,
                            "effect_id": effect_id,
                            "policy": policy.value,
                        },
                    )
                    return existing
                if policy == StackingPolicy.STACK_DURATION:
                    existing.remaining_duration += resisted_duration
                    existing.expires_at = _expires_in(existing.remaining_duration)
                    existing.stacks += 1
                    self._total_effects_applied += 1
                    self._record_event(
                        StatusEffectEventKind.EFFECT_REFRESHED,
                        {
                            "active_id": existing.active_id,
                            "entity_id": entity_id,
                            "effect_id": effect_id,
                            "policy": policy.value,
                        },
                    )
                    return existing
                if policy == StackingPolicy.STACK_INTENSITY:
                    existing.current_intensity += resisted_intensity
                    existing.stacks += 1
                    self._total_effects_applied += 1
                    self._record_event(
                        StatusEffectEventKind.EFFECT_REFRESHED,
                        {
                            "active_id": existing.active_id,
                            "entity_id": entity_id,
                            "effect_id": effect_id,
                            "policy": policy.value,
                        },
                    )
                    return existing
                if policy == StackingPolicy.STACK_BOTH:
                    existing.remaining_duration += resisted_duration
                    existing.current_intensity += resisted_intensity
                    existing.expires_at = _expires_in(existing.remaining_duration)
                    existing.stacks += 1
                    self._total_effects_applied += 1
                    self._record_event(
                        StatusEffectEventKind.EFFECT_REFRESHED,
                        {
                            "active_id": existing.active_id,
                            "entity_id": entity_id,
                            "effect_id": effect_id,
                            "policy": policy.value,
                        },
                    )
                    return existing
                if policy == StackingPolicy.REPLACE:
                    if existing_id is not None:
                        self._active_effects.pop(existing_id, None)
                    # Fall through to create a fresh active effect.
                else:
                    return None

            # FIFO eviction for the active effects store.
            if len(self._active_effects) >= _MAX_ENTITY_EFFECTS:
                oldest_id = next(iter(self._active_effects), None)
                if oldest_id is not None:
                    self._active_effects.pop(oldest_id, None)

            active = ActiveEffect(
                entity_id=entity_id,
                effect_id=effect_id,
                effect_name=definition.name,
                category=definition.category,
                element=definition.element,
                remaining_duration=resisted_duration,
                current_intensity=resisted_intensity,
                tick_timer=definition.tick_interval,
                stacks=1,
                source_entity_id=source_entity_id,
                expires_at=_expires_in(resisted_duration),
                metadata={},
            )
            self._active_effects[active.active_id] = active
            self._total_effects_applied += 1
            self._record_event(
                StatusEffectEventKind.EFFECT_APPLIED,
                {
                    "active_id": active.active_id,
                    "entity_id": entity_id,
                    "effect_id": effect_id,
                    "element": definition.element.value,
                    "duration": resisted_duration,
                    "intensity": resisted_intensity,
                },
            )
            return active

    def list_active_effects(
        self,
        entity_id: Optional[str] = None,
        category: Optional[EffectCategory] = None,
        element: Optional[EffectElement] = None,
    ) -> List[ActiveEffect]:
        """Return active effects optionally filtered by entity, category, and element."""
        with self._lock:
            results: List[ActiveEffect] = []
            for active in self._active_effects.values():
                if entity_id is not None and active.entity_id != entity_id:
                    continue
                if category is not None and active.category != category:
                    continue
                if element is not None and active.element != element:
                    continue
                results.append(active)
            return results

    def get_active_effect(self, active_id: str) -> Optional[ActiveEffect]:
        """Return an active effect by id, or None if not found."""
        with self._lock:
            return self._active_effects.get(active_id)

    # ------------------------------------------------------------------
    # Ticking
    # ------------------------------------------------------------------

    def tick_effects(self, delta_time: float) -> List[Dict[str, Any]]:
        """Advance all active effects by delta_time seconds.

        For each active effect:
          - remaining_duration and tick_timer are decremented,
          - damage_per_tick / heal_per_tick are applied when the tick fires,
          - effects with remaining_duration <= 0 are expired and removed,
          - chains whose trigger_effect_id matches an expired effect are fired.

        Returns a list of per-effect tick result dictionaries.
        """
        with self._lock:
            results: List[Dict[str, Any]] = []
            expired: List[tuple] = []

            for active_id, active in list(self._active_effects.items()):
                active.remaining_duration -= delta_time
                active.tick_timer -= delta_time

                tick_result: Dict[str, Any] = {
                    "active_id": active.active_id,
                    "entity_id": active.entity_id,
                    "effect_id": active.effect_id,
                    "effect_name": active.effect_name,
                    "damage": 0.0,
                    "healing": 0.0,
                    "expired": False,
                    "remaining_duration": active.remaining_duration,
                }

                definition = self._definitions.get(active.effect_id)
                tick_interval = (
                    definition.tick_interval
                    if definition is not None and definition.tick_interval > 0.0
                    else 1.0
                )

                # Process any catch-up ticks that elapsed within this frame.
                while active.tick_timer <= 0.0 and active.remaining_duration > 0.0:
                    if definition is not None:
                        # Intensity scales the per-tick damage and healing.
                        tick_result["damage"] += (
                            definition.damage_per_tick * active.current_intensity
                        )
                        tick_result["healing"] += (
                            definition.heal_per_tick * active.current_intensity
                        )
                    active.tick_timer += tick_interval
                    self._total_ticks_processed += 1
                    self._record_event(
                        StatusEffectEventKind.EFFECT_TICKED,
                        {
                            "active_id": active.active_id,
                            "entity_id": active.entity_id,
                            "effect_id": active.effect_id,
                            "damage": tick_result["damage"],
                            "healing": tick_result["healing"],
                        },
                    )

                if active.remaining_duration <= 0.0:
                    active.remaining_duration = 0.0
                    tick_result["expired"] = True
                    expired.append((active_id, active))

                results.append(tick_result)

            # Remove expired effects and trigger any registered chains.
            for active_id, active in expired:
                self._active_effects.pop(active_id, None)
                self._total_effects_expired += 1
                self._record_event(
                    StatusEffectEventKind.EFFECT_EXPIRED,
                    {
                        "active_id": active.active_id,
                        "entity_id": active.entity_id,
                        "effect_id": active.effect_id,
                    },
                )
                # Re-enter trigger_chain via the public API; the lock is reentrant.
                self.trigger_chain(
                    active.effect_id, active.entity_id, active.source_entity_id
                )

            return results

    # ------------------------------------------------------------------
    # Dispel / Refresh / Removal
    # ------------------------------------------------------------------

    def dispel_effect(self, active_id: str) -> Optional[ActiveEffect]:
        """Remove an active effect by id if it is dispellable. Returns the removed effect."""
        with self._lock:
            active = self._active_effects.get(active_id)
            if active is None:
                return None
            definition = self._definitions.get(active.effect_id)
            dispellable = definition.dispellable if definition is not None else True
            if not dispellable:
                return None
            self._active_effects.pop(active_id, None)
            self._total_effects_dispelled += 1
            self._record_event(
                StatusEffectEventKind.EFFECT_DISPELLED,
                {
                    "active_id": active_id,
                    "entity_id": active.entity_id,
                    "effect_id": active.effect_id,
                },
            )
            return active

    def dispel_by_category(
        self,
        entity_id: str,
        category: EffectCategory,
        count: int = 1,
    ) -> List[ActiveEffect]:
        """Dispel up to count dispellable effects of the given category on an entity."""
        with self._lock:
            dispelled: List[ActiveEffect] = []
            for active_id, active in list(self._active_effects.items()):
                if len(dispelled) >= count:
                    break
                if active.entity_id != entity_id or active.category != category:
                    continue
                definition = self._definitions.get(active.effect_id)
                dispellable = definition.dispellable if definition is not None else True
                if not dispellable:
                    continue
                self._active_effects.pop(active_id, None)
                self._total_effects_dispelled += 1
                self._record_event(
                    StatusEffectEventKind.EFFECT_DISPELLED,
                    {
                        "active_id": active_id,
                        "entity_id": active.entity_id,
                        "effect_id": active.effect_id,
                    },
                )
                dispelled.append(active)
            return dispelled

    def dispel_by_element(
        self,
        entity_id: str,
        element: EffectElement,
        count: int = 1,
    ) -> List[ActiveEffect]:
        """Dispel up to count dispellable effects of the given element on an entity."""
        with self._lock:
            dispelled: List[ActiveEffect] = []
            for active_id, active in list(self._active_effects.items()):
                if len(dispelled) >= count:
                    break
                if active.entity_id != entity_id or active.element != element:
                    continue
                definition = self._definitions.get(active.effect_id)
                dispellable = definition.dispellable if definition is not None else True
                if not dispellable:
                    continue
                self._active_effects.pop(active_id, None)
                self._total_effects_dispelled += 1
                self._record_event(
                    StatusEffectEventKind.EFFECT_DISPELLED,
                    {
                        "active_id": active_id,
                        "entity_id": active.entity_id,
                        "effect_id": active.effect_id,
                    },
                )
                dispelled.append(active)
            return dispelled

    def refresh_effect(
        self,
        active_id: str,
        duration: Optional[float] = None,
    ) -> Optional[ActiveEffect]:
        """Reset an active effect's remaining duration (and tick timer)."""
        with self._lock:
            active = self._active_effects.get(active_id)
            if active is None:
                return None
            definition = self._definitions.get(active.effect_id)
            new_duration = (
                duration if duration is not None else (
                    definition.base_duration if definition is not None else 0.0
                )
            )
            active.remaining_duration = new_duration
            active.expires_at = _expires_in(new_duration)
            if definition is not None:
                active.tick_timer = definition.tick_interval
            self._record_event(
                StatusEffectEventKind.EFFECT_REFRESHED,
                {
                    "active_id": active_id,
                    "entity_id": active.entity_id,
                    "duration": new_duration,
                },
            )
            return active

    def remove_active_effect(self, active_id: str) -> bool:
        """Unconditionally remove an active effect by id. Returns True if removed."""
        with self._lock:
            if active_id in self._active_effects:
                del self._active_effects[active_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Chains
    # ------------------------------------------------------------------

    def register_chain(
        self,
        name: str,
        trigger_effect_id: str,
        chained_effect_ids: List[str],
        chain_delay: float = 0.5,
        propagation_type: str = "sequential",
    ) -> EffectChain:
        """Register a chain of follow-up effects triggered when an effect expires."""
        with self._lock:
            if len(self._chains) >= _MAX_CHAINS:
                # FIFO eviction: drop the oldest chain.
                oldest_id = next(iter(self._chains), None)
                if oldest_id is not None:
                    self._chains.pop(oldest_id, None)

            chain = EffectChain(
                name=name,
                trigger_effect_id=trigger_effect_id,
                chained_effect_ids=list(chained_effect_ids) if chained_effect_ids else [],
                chain_delay=chain_delay,
                propagation_type=propagation_type,
            )
            self._chains[chain.chain_id] = chain
            return chain

    def list_chains(self) -> List[EffectChain]:
        """Return all registered effect chains."""
        with self._lock:
            return list(self._chains.values())

    def get_chain(self, chain_id: str) -> Optional[EffectChain]:
        """Return a chain by id, or None if not found."""
        with self._lock:
            return self._chains.get(chain_id)

    def trigger_chain(
        self,
        trigger_effect_id: str,
        target_entity_id: str,
        source_entity_id: str = "",
    ) -> List[ActiveEffect]:
        """Trigger all chains registered for trigger_effect_id on the target entity.

        Each chained effect is applied to the target. The chain_delay is recorded
        in the event payload but application is synchronous (no scheduler).
        """
        with self._lock:
            applied: List[ActiveEffect] = []
            matching = [
                c for c in self._chains.values()
                if c.trigger_effect_id == trigger_effect_id
            ]
            if not matching:
                return applied

            for chain in matching:
                self._total_chains_triggered += 1
                self._record_event(
                    StatusEffectEventKind.CHAIN_TRIGGERED,
                    {
                        "chain_id": chain.chain_id,
                        "name": chain.name,
                        "trigger_effect_id": trigger_effect_id,
                        "target_entity_id": target_entity_id,
                        "chain_delay": chain.chain_delay,
                    },
                )
                for chained_effect_id in chain.chained_effect_ids:
                    active = self.apply_effect(
                        target_entity_id,
                        chained_effect_id,
                        source_entity_id=source_entity_id,
                    )
                    if active is not None:
                        applied.append(active)
                self._record_event(
                    StatusEffectEventKind.CHAIN_COMPLETED,
                    {
                        "chain_id": chain.chain_id,
                        "name": chain.name,
                        "applied_count": len(applied),
                    },
                )
            return applied

    # ------------------------------------------------------------------
    # Internal Resistance Helpers
    # ------------------------------------------------------------------

    def _compute_resisted_duration(
        self,
        base_duration: float,
        entity_id: str,
        element: EffectElement,
    ) -> float:
        """Compute the resistance- and susceptibility-adjusted duration.

        Formula: base_duration * (1 - resistance) * (susceptibility if present else 1.0).
        Caller must hold self._lock.
        """
        profile = self._resistance_profiles.get(entity_id)
        resistance = 0.0
        susceptibility_factor = 1.0
        if profile is not None:
            resistance = profile.resistances.get(element, 0.0)
            if element in profile.susceptibility:
                susceptibility_factor = profile.susceptibility[element]
        result = base_duration * (1.0 - resistance) * susceptibility_factor
        return _clamp(result, 0.0, 86400.0)

    def _compute_resisted_intensity(
        self,
        base_intensity: float,
        entity_id: str,
        element: EffectElement,
    ) -> float:
        """Compute the resistance- and susceptibility-adjusted intensity.

        Formula: base_intensity * (1 - resistance) * (susceptibility if present else 1.0).
        Caller must hold self._lock.
        """
        profile = self._resistance_profiles.get(entity_id)
        resistance = 0.0
        susceptibility_factor = 1.0
        if profile is not None:
            resistance = profile.resistances.get(element, 0.0)
            if element in profile.susceptibility:
                susceptibility_factor = profile.susceptibility[element]
        result = base_intensity * (1.0 - resistance) * susceptibility_factor
        return _clamp(result, 0.0, 1000.0)

    def _get_resistance_tier(self, value: float) -> ResistanceTier:
        """Bucket a numeric resistance/susceptibility value into a qualitative tier."""
        if value < 0.0:
            return ResistanceTier.IMMUNE
        if value < 0.25:
            return ResistanceTier.HIGHLY_RESISTANT
        if value < 0.5:
            return ResistanceTier.RESISTANT
        if value < 0.75:
            return ResistanceTier.NORMAL
        if value < 1.0:
            return ResistanceTier.SUSCEPTIBLE
        return ResistanceTier.HIGHLY_SUSCEPTIBLE

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: StatusEffectEventKind,
        payload: Dict[str, Any],
    ) -> StatusEffectEvent:
        """Record an audit event (caller must hold self._lock)."""
        event = StatusEffectEvent(
            kind=kind,
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        return event

    def list_events(self, limit: int = 100) -> List[StatusEffectEvent]:
        """Return the most recent audit events, limited to limit."""
        with self._lock:
            events = list(self._events)
        if limit > 0:
            events = events[-limit:]
        return events

    # ------------------------------------------------------------------
    # Stats / Status / Snapshot
    # ------------------------------------------------------------------

    def get_stats(self) -> StatusEffectStats:
        """Compute and return aggregate status effect system stats."""
        with self._lock:
            by_category: Dict[str, int] = {}
            by_element: Dict[str, int] = {}
            total_duration = 0.0
            for active in self._active_effects.values():
                cat_key = active.category.value
                elem_key = active.element.value
                by_category[cat_key] = by_category.get(cat_key, 0) + 1
                by_element[elem_key] = by_element.get(elem_key, 0) + 1
                total_duration += active.remaining_duration

            count = len(self._active_effects)
            avg_duration = (total_duration / count) if count > 0 else 0.0

            return StatusEffectStats(
                total_definitions=len(self._definitions),
                total_active_effects=count,
                total_resistance_profiles=len(self._resistance_profiles),
                total_chains=len(self._chains),
                active_by_category=by_category,
                active_by_element=by_element,
                avg_duration=avg_duration,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current status effect system state."""
        with self._lock:
            stats = self.get_stats()
            return {
                "initialized": self._initialized,
                "total_definitions": len(self._definitions),
                "total_active_effects": len(self._active_effects),
                "total_resistance_profiles": len(self._resistance_profiles),
                "total_chains": len(self._chains),
                "total_events": len(self._events),
                "total_effects_applied": self._total_effects_applied,
                "total_effects_expired": self._total_effects_expired,
                "total_effects_dispelled": self._total_effects_dispelled,
                "total_ticks_processed": self._total_ticks_processed,
                "total_chains_triggered": self._total_chains_triggered,
                "stats": stats.to_dict(),
            }

    def get_snapshot(self) -> StatusEffectSnapshot:
        """Capture an immutable snapshot of the status effect system state."""
        with self._lock:
            stats = self.get_stats()
            return StatusEffectSnapshot(
                initialized=self._initialized,
                definitions=list(self._definitions.values()),
                active_effects=list(self._active_effects.values()),
                resistance_profiles=list(self._resistance_profiles.values()),
                chains=list(self._chains.values()),
                events=list(self._events),
                stats=stats,
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all definitions, active effects, profiles, chains, and events.

        Restores the engine to its initial state, including the seed data.
        """
        with self._lock:
            self._definitions.clear()
            self._active_effects.clear()
            self._resistance_profiles.clear()
            self._chains.clear()
            self._events.clear()
            self._total_definitions_registered = 0
            self._total_effects_applied = 0
            self._total_effects_expired = 0
            self._total_effects_dispelled = 0
            self._total_ticks_processed = 0
            self._total_chains_triggered = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_status_effect_system() -> StatusEffectSystemEngine:
    """Return the singleton StatusEffectSystemEngine instance."""
    return StatusEffectSystemEngine.get_instance()
