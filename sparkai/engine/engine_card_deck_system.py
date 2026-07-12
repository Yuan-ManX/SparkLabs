"""
SparkLabs Engine - Card & Deck Game System

A card game mechanics engine for the SparkLabs AI-native game engine.
Provides collectible card definitions, deck construction, in-match play
loops, and turn-based combat resolution similar to Hearthstone, MTG, and
Slay the Spire.

The system models the full lifecycle of a card game: card catalog
registration, deck building and validation, match creation, mulligan,
draw, main phase actions (playing minions, spells, weapons), combat
resolution through damage and healing, turn rotation with mana ramp,
and end-of-game detection.

Architecture:
  CardDeckSystem (singleton)
    |-- CardType, CardRarity, CardElement, DeckArchetype, GamePhase,
       CardStatus, TargetType, EffectType, DeckFormat, CardDeckEventKind
    |-- CardDefinition, CardInstance, Deck, CardEffect, MatchState,
       PlayerState, CardDeckConfig, CardDeckStats, CardDeckSnapshot,
       CardDeckEvent
    |-- get_card_deck_system

Core Capabilities:
  - register_card / remove_card / get_card / list_cards: manage the
    collectible card catalog indexed by card_id.
  - register_deck / remove_deck / get_deck / list_decks / validate_deck:
    build, inspect, and validate player decks against format rules.
  - shuffle_deck / draw_card: manipulate a deck draw pile.
  - create_match / get_match / list_matches / end_turn / play_card /
    deal_damage / heal_target: run matches with turn rotation, mana
    ramp, and combat resolution.
  - get_player_state / get_board_state / calculate_deck_stats: inspect
    match and deck state for UIs and balancing tools.
  - set_config / get_config: global tuning for hand size, board size,
    starting health, mana cap, deck size, and mulligan count.
  - tick: advance the simulation and expire transient effects.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability, auditing, and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`CardDeckSystem.get_instance` or the module-level
:func:`get_card_deck_system` factory.
"""

from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_CARDS: int = 1000
_MAX_DECKS: int = 500
_MAX_MATCHES: int = 200
_MAX_INSTANCES: int = 50000
_MAX_EVENTS: int = 10000
_MAX_DECK_LOG: int = 200


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 timestamp string."""
    return datetime.now().isoformat()


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier with an optional prefix."""
    base = "%016x" % random.getrandbits(64)
    base = base[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_int(value: Any, default: int = 0) -> int:
    """Coerce a value to int, falling back to default on failure."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce a value to float, falling back to default on failure."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a numeric value into the inclusive range [lo, hi]."""
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict oldest entries from a list until it fits within max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _enum_value(value: Any, enum_cls: type) -> Optional[str]:
    """Normalize an enum member, name, or value string into its value.

    Returns None when the input does not match any member of the enum.
    """
    if isinstance(value, enum_cls):
        return value.value
    if isinstance(value, str):
        for member in enum_cls:
            if value == member.value or value == member.name:
                return member.value
    return None


def _dataclass_to_dict(obj: Any) -> Any:
    """Recursively convert a dataclass (or container) into plain dicts.

    Checks ``__dataclass_fields__`` BEFORE ``to_dict`` so that dataclasses
    are serialized from their field definitions and never accidentally
    delegate to a custom ``to_dict`` that may itself call this helper
    (which would cause unbounded recursion).
    """
    if obj is None:
        return None
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _dataclass_to_dict(v) for k, v in obj.__dict__.items()}
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, list):
        return [_dataclass_to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, tuple):
        return list(obj)
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CardType(str, Enum):
    """Broad classification of a card."""
    MINION = "minion"
    SPELL = "spell"
    WEAPON = "weapon"
    ENCHANTMENT = "enchantment"
    LOCATION = "location"
    HERO = "hero"
    TOKEN = "token"


class CardRarity(str, Enum):
    """Rarity tier controlling drop rates and per-deck limits."""
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class CardElement(str, Enum):
    """Elemental school a card belongs to."""
    NEUTRAL = "neutral"
    FIRE = "fire"
    WATER = "water"
    EARTH = "earth"
    AIR = "air"
    LIGHT = "light"
    DARK = "dark"
    ARCANE = "arcane"
    NATURE = "nature"


class DeckArchetype(str, Enum):
    """Strategic archetype describing a deck's play pattern."""
    AGGRO = "aggro"
    CONTROL = "control"
    COMBO = "combo"
    MIDRANGE = "midrange"
    RAMP = "ramp"
    TEMPO = "tempo"
    MILL = "mill"


class GamePhase(str, Enum):
    """Phases within a single turn."""
    MULLIGAN = "mulligan"
    DRAW = "draw"
    MAIN = "main"
    COMBAT = "combat"
    END = "end"
    CLEANUP = "cleanup"


class CardStatus(str, Enum):
    """Where a card instance currently resides."""
    IN_DECK = "in_deck"
    IN_HAND = "in_hand"
    ON_BOARD = "on_board"
    IN_GRAVEYARD = "in_graveyard"
    BANISHED = "banished"
    EXHAUSTED = "exhausted"


class TargetType(str, Enum):
    """Targeting restrictions for a card or effect."""
    NONE = "none"
    ANY_MINION = "any_minion"
    ANY_CHARACTER = "any_character"
    FRIENDLY_MINION = "friendly_minion"
    ENEMY_MINION = "enemy_minion"
    FRIENDLY_CHARACTER = "friendly_character"
    ENEMY_CHARACTER = "enemy_character"
    ALL_MINIONS = "all_minions"
    ALL_CHARACTERS = "all_characters"
    ADJACENT = "adjacent"


class EffectType(str, Enum):
    """Discrete effect kinds that can be attached to a card."""
    DAMAGE = "damage"
    HEAL = "heal"
    DRAW_CARD = "draw_card"
    SUMMON = "summon"
    BUFF = "buff"
    DEBUFF = "debuff"
    DESTROY = "destroy"
    TRANSFORM = "transform"
    DISCARD = "discard"
    MILL = "mill"
    DISCOVER = "discover"
    RANDOM = "random"
    TRIGGER_DEATHRATTLE = "trigger_deathrattle"
    RESTORE_MANA = "restore_mana"
    REDUCE_COST = "reduce_cost"


class DeckFormat(str, Enum):
    """Constructed format governing card pool legality."""
    STANDARD = "standard"
    WILD = "wild"
    CLASSIC = "classic"
    DRAFT = "draft"
    ARENA = "arena"
    CONSTRUCTED = "constructed"


class CardDeckEventKind(str, Enum):
    """Audit event kinds emitted by the card and deck system."""
    CARD_DRAWN = "card_drawn"
    CARD_PLAYED = "card_played"
    CARD_DESTROYED = "card_destroyed"
    DECK_SHUFFLED = "deck_shuffled"
    TURN_STARTED = "turn_started"
    TURN_ENDED = "turn_ended"
    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CardEffect:
    """A discrete effect produced when a card is played."""
    effect_id: str
    effect_type: str
    value: int
    target_type: str = TargetType.NONE.value
    condition: str = ""
    trigger: str = ""
    duration: int = 0
    is_persistent: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CardDefinition:
    """Immutable definition of a collectible card."""
    card_id: str
    name: str
    card_type: str
    rarity: str
    element: str
    cost: int
    attack: int = 0
    health: int = 0
    text: str = ""
    flavor_text: str = ""
    effects: List[CardEffect] = field(default_factory=list)
    target_type: str = TargetType.NONE.value
    is_collectible: bool = True
    max_per_deck: int = 2
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CardInstance:
    """A runtime instantiation of a CardDefinition inside a match."""
    instance_id: str
    card_id: str
    owner_id: str
    status: str
    current_attack: int = 0
    current_health: int = 0
    current_cost: int = 0
    buffs: List[Dict[str, Any]] = field(default_factory=list)
    enchantments: List[Dict[str, Any]] = field(default_factory=list)
    summoning_sick: bool = True
    turn_played: int = 0
    position: int = -1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Deck:
    """A constructed deck owned by a player."""
    deck_id: str
    name: str
    owner_id: str
    archetype: str
    format: str
    hero_id: str
    card_ids: List[str] = field(default_factory=list)
    sideboard: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerState:
    """Per-player state within a match."""
    player_id: str
    match_id: str
    hero_id: str
    health: int = 30
    armor: int = 0
    max_health: int = 30
    mana: int = 0
    max_mana: int = 0
    overload: int = 0
    hand: List[str] = field(default_factory=list)
    deck_remaining: int = 30
    graveyard: List[str] = field(default_factory=list)
    fatigue_count: int = 0
    has_mulliganed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MatchState:
    """Full state of an in-progress match."""
    match_id: str
    players: List[PlayerState] = field(default_factory=list)
    current_player: str = ""
    turn_number: int = 1
    phase: str = GamePhase.MAIN.value
    board_state: Dict[str, List[str]] = field(default_factory=dict)
    active_effects: List[Dict[str, Any]] = field(default_factory=list)
    winner: str = ""
    started_at: str = field(default_factory=_now)
    ended_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CardDeckConfig:
    """Global tuning parameters for the card and deck system."""
    max_hand_size: int = 10
    max_board_size: int = 7
    starting_health: int = 30
    starting_mana: int = 0
    max_mana: int = 10
    mana_per_turn: int = 1
    deck_size: int = 30
    starting_hand: int = 3
    max_overload: int = 10
    mulligan_count: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CardDeckStats:
    """Aggregate statistics for the card and deck system."""
    total_cards: int = 0
    total_decks: int = 0
    total_matches: int = 0
    active_matches: int = 0
    cards_played: int = 0
    cards_drawn: int = 0
    games_completed: int = 0
    avg_game_length: float = 0.0
    total_events: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CardDeckSnapshot:
    """Point-in-time snapshot of system counters."""
    timestamp: str = field(default_factory=_now)
    cards_count: int = 0
    decks_count: int = 0
    matches_count: int = 0
    active_matches: int = 0
    config: CardDeckConfig = field(default_factory=CardDeckConfig)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CardDeckEvent:
    """An audit event emitted by the card and deck system."""
    event_id: str
    kind: str
    timestamp: str
    player_id: str = ""
    card_id: str = ""
    match_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Singleton Plumbing
# ---------------------------------------------------------------------------

_lock = threading.RLock()
_instance: Optional["CardDeckSystem"] = None


# ---------------------------------------------------------------------------
# Card & Deck System
# ---------------------------------------------------------------------------


class CardDeckSystem:
    """Manages the card catalog, deck registry, and match simulation.

    The system is a process-wide singleton. Obtain it via
    :meth:`get_instance` or the module-level :func:`get_card_deck_system`
    factory; do not instantiate it directly in application code.
    """

    _init_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cards: Dict[str, CardDefinition] = {}
        self._decks: Dict[str, Deck] = {}
        self._matches: Dict[str, MatchState] = {}
        self._instances: Dict[str, CardInstance] = {}
        self._events: List[CardDeckEvent] = []
        # Per-match draw piles: match_id -> player_id -> list of card_ids.
        self._draw_piles: Dict[str, Dict[str, List[str]]] = {}
        self._config = CardDeckConfig()
        self._stats = CardDeckStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._instance_counter: int = 0
        self._match_counter: int = 0
        self._initialized: bool = False
        self._seed()

    @classmethod
    def get_instance(cls) -> "CardDeckSystem":
        """Return the singleton instance, creating it on first call."""
        global _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = cls()
        return _instance

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: CardDeckEventKind,
        player_id: str = "",
        card_id: str = "",
        match_id: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an audit event to the in-memory event log."""
        event_id = f"evt_{self._event_counter}"
        self._event_counter += 1
        event = CardDeckEvent(
            event_id=event_id,
            kind=kind.value,
            timestamp=_now(),
            player_id=player_id,
            card_id=card_id,
            match_id=match_id,
            data=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)
        self._stats.total_events = len(self._events)

    def _new_instance_id(self) -> str:
        """Return a fresh unique card instance id."""
        iid = f"inst_{self._instance_counter}"
        self._instance_counter += 1
        return iid

    def _new_match_id(self) -> str:
        """Return a fresh unique match id."""
        mid = f"match_{self._match_counter:03d}"
        self._match_counter += 1
        return mid

    def _instantiate(self, card_id: str, owner_id: str, status: str) -> CardInstance:
        """Create and register a CardInstance from a card definition."""
        definition = self._cards.get(card_id)
        inst = CardInstance(
            instance_id=self._new_instance_id(),
            card_id=card_id,
            owner_id=owner_id,
            status=status,
            current_attack=definition.attack if definition else 0,
            current_health=definition.health if definition else 0,
            current_cost=definition.cost if definition else 0,
        )
        if len(self._instances) >= _MAX_INSTANCES:
            oldest = next(iter(self._instances), None)
            if oldest:
                self._instances.pop(oldest, None)
        self._instances[inst.instance_id] = inst
        return inst

    def _resolve_target(
        self, match: MatchState, target_id: str
    ) -> Tuple[Optional[str], Any]:
        """Resolve a target id to either a player or a card instance.

        Returns ("player", PlayerState), ("minion", CardInstance), or
        (None, None) when the target cannot be found.
        """
        if not target_id:
            return None, None
        for player in match.players:
            if player.player_id == target_id:
                return "player", player
        inst = self._instances.get(target_id)
        if inst is not None:
            return "minion", inst
        return None, None

    def _player(self, match: MatchState, player_id: str) -> Optional[PlayerState]:
        """Look up a player state within a match."""
        for player in match.players:
            if player.player_id == player_id:
                return player
        return None

    def _opponent(self, match: MatchState, player_id: str) -> Optional[PlayerState]:
        """Look up the opposing player state within a match."""
        for player in match.players:
            if player.player_id != player_id:
                return player
        return None

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed a realistic starting catalog, decks, and active matches."""
        # --- Card catalog ---------------------------------------------------
        # Each tuple maps to:
        # (card_id, name, card_type, rarity, element, cost, attack, health,
        #  text, flavor_text, effects, target_type, is_collectible, max_per_deck)
        seed_cards: List[Tuple[Any, ...]] = [
            # Fire school
            ("fireball_burst", "Fireball Burst", CardType.SPELL, CardRarity.COMMON,
             CardElement.FIRE, 4, 0, 0, "Deal 5 damage to a minion.",
             "A concentrated sphere of roaring flame.",
             [CardEffect(effect_id="eff_fireball_dmg", effect_type=EffectType.DAMAGE.value,
                         value=5, target_type=TargetType.ANY_MINION.value)],
             TargetType.ANY_MINION.value, True, 2),
            ("flame_imp", "Flame Imp", CardType.MINION, CardRarity.COMMON,
             CardElement.FIRE, 1, 3, 2, "Aggressive opener that burns the enemy.",
             "Small, hot-tempered, and always hungry.",
             [], TargetType.NONE.value, True, 2),
            ("ember_wolf", "Ember Wolf", CardType.MINION, CardRarity.COMMON,
             CardElement.FIRE, 2, 2, 2, "A loyal beast of cinder and ash.",
             "Its howl crackles across the dunes.",
             [], TargetType.NONE.value, True, 2),
            ("magma_giant", "Magma Giant", CardType.MINION, CardRarity.EPIC,
             CardElement.FIRE, 7, 8, 8, "A towering colossus of cooled lava.",
             "Each footfall leaves the earth scorched.",
             [], TargetType.NONE.value, True, 1),
            ("scorching_blast", "Scorching Blast", CardType.SPELL, CardRarity.RARE,
             CardElement.FIRE, 5, 0, 0, "Deal 4 damage to all enemy minions.",
             "The battlefield becomes an oven.",
             [CardEffect(effect_id="eff_scorch_dmg", effect_type=EffectType.DAMAGE.value,
                         value=4, target_type=TargetType.ENEMY_MINION.value)],
             TargetType.ENEMY_MINION.value, True, 2),
            # Water school
            ("water_elemental", "Water Elemental", CardType.MINION, CardRarity.RARE,
             CardElement.WATER, 4, 3, 6, "Freezes targets it damages.",
             "A tide given form and purpose.",
             [], TargetType.NONE.value, True, 2),
            ("tide_caller", "Tide Caller", CardType.MINION, CardRarity.COMMON,
             CardElement.WATER, 3, 2, 4, "Draws strength from the depths.",
             "It sings the ocean awake.",
             [], TargetType.NONE.value, True, 2),
            ("frost_nova", "Frost Nova", CardType.SPELL, CardRarity.RARE,
             CardElement.WATER, 5, 0, 0, "Freeze all enemy minions.",
             "Winter arrives in a single breath.",
             [CardEffect(effect_id="eff_frost_debuff", effect_type=EffectType.DEBUFF.value,
                         value=0, target_type=TargetType.ENEMY_MINION.value, duration=1)],
             TargetType.ENEMY_MINION.value, True, 2),
            ("ocean_serpent", "Ocean Serpent", CardType.MINION, CardRarity.EPIC,
             CardElement.WATER, 6, 5, 7, "A leviathan that swallows ships whole.",
             "Sailors whisper its name and pray.",
             [], TargetType.NONE.value, True, 1),
            # Earth school
            ("earth_golem", "Earth Golem", CardType.MINION, CardRarity.RARE,
             CardElement.EARTH, 6, 7, 8, "An unyielding guardian of stone.",
             "Carved from the bones of the world.",
             [], TargetType.NONE.value, True, 2),
            ("stone_guardian", "Stone Guardian", CardType.MINION, CardRarity.COMMON,
             CardElement.EARTH, 4, 3, 5, "A patient defender of the realm.",
             "It waits, and the mountain waits with it.",
             [], TargetType.NONE.value, True, 2),
            ("quake_tremor", "Quake Tremor", CardType.SPELL, CardRarity.COMMON,
             CardElement.EARTH, 4, 0, 0, "Deal 3 damage to all minions.",
             "The ground shrugs, and armies fall.",
             [CardEffect(effect_id="eff_quake_dmg", effect_type=EffectType.DAMAGE.value,
                         value=3, target_type=TargetType.ALL_MINIONS.value)],
             TargetType.ALL_MINIONS.value, True, 2),
            ("mountain_titan", "Mountain Titan", CardType.MINION, CardRarity.LEGENDARY,
             CardElement.EARTH, 8, 8, 10, "The living summit of an ancient peak.",
             "Legends say it naps for centuries.",
             [], TargetType.NONE.value, True, 1),
            # Air school
            ("wind_fury", "Wind Fury", CardType.SPELL, CardRarity.COMMON,
             CardElement.AIR, 3, 0, 0, "Give a friendly minion +2 attack.",
             "A gale sharpens every blade.",
             [CardEffect(effect_id="eff_wind_buff", effect_type=EffectType.BUFF.value,
                         value=2, target_type=TargetType.FRIENDLY_MINION.value)],
             TargetType.FRIENDLY_MINION.value, True, 2),
            ("storm_harpy", "Storm Harpy", CardType.MINION, CardRarity.COMMON,
             CardElement.AIR, 3, 4, 3, "Swoops from the thunderheads.",
             "Her shriek rides the lightning.",
             [], TargetType.NONE.value, True, 2),
            ("thunder_bird", "Thunder Bird", CardType.MINION, CardRarity.RARE,
             CardElement.AIR, 5, 4, 5, "Channels lightning through its feathers.",
             "The storm follows it across continents.",
             [], TargetType.NONE.value, True, 2),
            ("cyclone_djinn", "Cyclone Djinn", CardType.MINION, CardRarity.EPIC,
             CardElement.AIR, 6, 5, 6, "A spirit woven from the spinning wind.",
             "It grants wishes it immediately forgets.",
             [], TargetType.NONE.value, True, 1),
            # Light school
            ("light_heal", "Light Heal", CardType.SPELL, CardRarity.COMMON,
             CardElement.LIGHT, 2, 0, 0, "Restore 6 health to a character.",
             "A warm radiance that knits flesh together.",
             [CardEffect(effect_id="eff_heal_light", effect_type=EffectType.HEAL.value,
                         value=6, target_type=TargetType.ANY_CHARACTER.value)],
             TargetType.ANY_CHARACTER.value, True, 2),
            ("dawn_paladin", "Dawn Paladin", CardType.MINION, CardRarity.RARE,
             CardElement.LIGHT, 4, 3, 5, "A champion wreathed in morning light.",
             "Her oath outlasts the longest night.",
             [], TargetType.NONE.value, True, 2),
            ("radiant_angel", "Radiant Angel", CardType.MINION, CardRarity.EPIC,
             CardElement.LIGHT, 6, 5, 6, "Heals its allies at the end of each turn.",
             "Mercy given wings and a sword.",
             [], TargetType.NONE.value, True, 1),
            ("sun_burst", "Sun Burst", CardType.SPELL, CardRarity.RARE,
             CardElement.LIGHT, 5, 0, 0, "Deal 4 damage and restore 4 health.",
             "Dawn and ruin, delivered together.",
             [CardEffect(effect_id="eff_sun_dmg", effect_type=EffectType.DAMAGE.value,
                         value=4, target_type=TargetType.ANY_MINION.value),
              CardEffect(effect_id="eff_sun_heal", effect_type=EffectType.HEAL.value,
                         value=4, target_type=TargetType.FRIENDLY_CHARACTER.value)],
             TargetType.ANY_MINION.value, True, 2),
            # Dark school
            ("shadow_strike", "Shadow Strike", CardType.SPELL, CardRarity.COMMON,
             CardElement.DARK, 3, 0, 0, "Deal 4 damage to a character.",
             "A blade that drinks the light.",
             [CardEffect(effect_id="eff_shadow_dmg", effect_type=EffectType.DAMAGE.value,
                         value=4, target_type=TargetType.ANY_CHARACTER.value)],
             TargetType.ANY_CHARACTER.value, True, 2),
            ("void_wraith", "Void Wraith", CardType.MINION, CardRarity.COMMON,
             CardElement.DARK, 3, 3, 3, "Feeds on discarded memories.",
             "It wears the faces it has consumed.",
             [], TargetType.NONE.value, True, 2),
            ("death_knight", "Death Knight", CardType.MINION, CardRarity.EPIC,
             CardElement.DARK, 5, 4, 6, "Raises a fallen minion when it enters play.",
             "Loyalty outlasts the grave.",
             [], TargetType.NONE.value, True, 1),
            ("soul_reaper", "Soul Reaper", CardType.MINION, CardRarity.LEGENDARY,
             CardElement.DARK, 7, 6, 8, "Gains power from every death nearby.",
             "It harvests what others leave behind.",
             [], TargetType.NONE.value, True, 1),
            # Arcane school
            ("arcane_intellect", "Arcane Intellect", CardType.SPELL, CardRarity.COMMON,
             CardElement.ARCANE, 3, 0, 0, "Draw 2 cards.",
             "Knowledge flows in rivulets of starlight.",
             [CardEffect(effect_id="eff_arcane_draw", effect_type=EffectType.DRAW_CARD.value,
                         value=2, target_type=TargetType.FRIENDLY_CHARACTER.value)],
             TargetType.NONE.value, True, 2),
            ("mana_wyrm", "Mana Wyrm", CardType.MINION, CardRarity.COMMON,
             CardElement.ARCANE, 1, 1, 3, "Grows each time you cast a spell.",
             "It feeds on incantations.",
             [], TargetType.NONE.value, True, 2),
            ("spellbreaker", "Spellbreaker", CardType.MINION, CardRarity.RARE,
             CardElement.ARCANE, 4, 4, 3, "Silences a target minion on entry.",
             "Its whisper unravels enchantments.",
             [], TargetType.ANY_MINION.value, True, 2),
            ("archmage", "Archmage", CardType.MINION, CardRarity.EPIC,
             CardElement.ARCANE, 6, 4, 7, "Spells cost one less while it lives.",
             "A library given legs and a stern expression.",
             [], TargetType.NONE.value, True, 1),
            # Nature school
            ("nature_bloom", "Nature Bloom", CardType.SPELL, CardRarity.COMMON,
             CardElement.NATURE, 2, 0, 0, "Restore 2 mana crystals.",
             "The grove returns what was spent.",
             [CardEffect(effect_id="eff_bloom_mana", effect_type=EffectType.RESTORE_MANA.value,
                         value=2, target_type=TargetType.FRIENDLY_CHARACTER.value)],
             TargetType.NONE.value, True, 2),
            ("treant_guardian", "Treant Guardian", CardType.MINION, CardRarity.COMMON,
             CardElement.NATURE, 3, 2, 4, "A rooted sentinel of the deep woods.",
             "It remembers every name carved into its bark.",
             [], TargetType.NONE.value, True, 2),
            ("wild_growth", "Wild Growth", CardType.SPELL, CardRarity.COMMON,
             CardElement.NATURE, 2, 0, 0, "Gain an empty mana crystal.",
             "The forest expands its canopy.",
             [CardEffect(effect_id="eff_growth_mana", effect_type=EffectType.RESTORE_MANA.value,
                         value=1, target_type=TargetType.FRIENDLY_CHARACTER.value)],
             TargetType.NONE.value, True, 2),
            # Neutral school
            ("goblin_raider", "Goblin Raider", CardType.MINION, CardRarity.COMMON,
             CardElement.NEUTRAL, 2, 2, 2, "A quick and greedy skirmisher.",
             "If it shines, it is already gone.",
             [], TargetType.NONE.value, True, 2),
            ("iron_sentinel", "Iron Sentinel", CardType.MINION, CardRarity.RARE,
             CardElement.NEUTRAL, 5, 5, 7, "A wall of polished steel.",
             "It has never taken a step backward.",
             [], TargetType.NONE.value, True, 2),
            ("mythic_dragon", "Mythic Dragon", CardType.MINION, CardRarity.LEGENDARY,
             CardElement.NEUTRAL, 8, 8, 8, "An ancient wyrm of living myth.",
             "Its shadow darkens entire kingdoms.",
             [], TargetType.NONE.value, True, 1),
            ("tavern_brawler", "Tavern Brawler", CardType.MINION, CardRarity.COMMON,
             CardElement.NEUTRAL, 1, 1, 3, "Tougher than the ale it drinks.",
             "Every brawl is a reunion.",
             [], TargetType.NONE.value, True, 2),
            ("silverback_gorilla", "Silverback Gorilla", CardType.MINION,
             CardRarity.COMMON, CardElement.NEUTRAL, 3, 1, 4,
             "A stoic ape that protects its troop.",
             "Beat its chest and it beats back.",
             [], TargetType.NONE.value, True, 2),
            ("wandering_merchant", "Wandering Merchant", CardType.MINION,
             CardRarity.RARE, CardElement.NEUTRAL, 2, 2, 3,
             "Discover a card from your deck when played.",
             "Every road is a marketplace to him.",
             [], TargetType.NONE.value, True, 2),
            ("war_torch", "War Torch", CardType.WEAPON, CardRarity.COMMON,
             CardElement.NEUTRAL, 2, 2, 0, "A blazing brand swung in melee.",
             "Crude, bright, and effective.",
             [], TargetType.NONE.value, True, 2),
        ]

        for entry in seed_cards:
            (cid, name, ctype, rarity, element, cost, atk, hp, text, flavor,
             effects, ttype, collectible, max_per) = entry
            definition = CardDefinition(
                card_id=cid,
                name=name,
                card_type=_enum_value(ctype, CardType) or ctype.value,
                rarity=_enum_value(rarity, CardRarity) or rarity.value,
                element=_enum_value(element, CardElement) or element.value,
                cost=cost,
                attack=atk,
                health=hp,
                text=text,
                flavor_text=flavor,
                effects=list(effects),
                target_type=_enum_value(ttype, TargetType) or ttype.value,
                is_collectible=collectible,
                max_per_deck=max_per,
            )
            self._cards[definition.card_id] = definition

        # --- Decks ----------------------------------------------------------
        deck_flame = Deck(
            deck_id="deck_flame_aggro",
            name="Flame Aggro",
            owner_id="player_001",
            archetype=DeckArchetype.AGGRO.value,
            format=DeckFormat.STANDARD.value,
            hero_id="hero_pyromancer",
            card_ids=[
                "flame_imp", "flame_imp", "ember_wolf", "ember_wolf",
                "goblin_raider", "goblin_raider", "tavern_brawler",
                "tavern_brawler", "wind_fury", "wind_fury", "shadow_strike",
                "shadow_strike", "fireball_burst", "fireball_burst",
                "scorching_blast", "scorching_blast", "storm_harpy",
                "storm_harpy", "stone_guardian", "stone_guardian",
                "dawn_paladin", "dawn_paladin", "water_elemental",
                "water_elemental", "iron_sentinel", "iron_sentinel",
                "magma_giant", "thunder_bird", "mythic_dragon",
                "war_torch",
            ],
            stats={"wins": 14, "losses": 6},
        )
        deck_tide = Deck(
            deck_id="deck_tide_control",
            name="Tide Control",
            owner_id="player_002",
            archetype=DeckArchetype.CONTROL.value,
            format=DeckFormat.STANDARD.value,
            hero_id="hero_tideweaver",
            card_ids=[
                "water_elemental", "water_elemental", "tide_caller",
                "tide_caller", "frost_nova", "frost_nova", "light_heal",
                "light_heal", "arcane_intellect", "arcane_intellect",
                "stone_guardian", "stone_guardian", "dawn_paladin",
                "dawn_paladin", "earth_golem", "earth_golem",
                "scorching_blast", "scorching_blast", "ocean_serpent",
                "thunder_bird", "thunder_bird", "iron_sentinel",
                "iron_sentinel", "cyclone_djinn", "radiant_angel",
                "death_knight", "mountain_titan", "soul_reaper",
                "mythic_dragon", "war_torch",
            ],
            stats={"wins": 9, "losses": 11},
        )
        deck_earth = Deck(
            deck_id="deck_earth_midrange",
            name="Earth Midrange",
            owner_id="player_003",
            archetype=DeckArchetype.MIDRANGE.value,
            format=DeckFormat.STANDARD.value,
            hero_id="hero_geomancer",
            card_ids=[
                "stone_guardian", "stone_guardian", "treant_guardian",
                "treant_guardian", "wild_growth", "wild_growth",
                "nature_bloom", "nature_bloom", "tavern_brawler",
                "tavern_brawler", "goblin_raider", "goblin_raider",
                "earth_golem", "earth_golem", "quake_tremor",
                "quake_tremor", "dawn_paladin", "dawn_paladin",
                "iron_sentinel", "iron_sentinel", "thunder_bird",
                "thunder_bird", "water_elemental", "water_elemental",
                "magma_giant", "cyclone_djinn", "mountain_titan",
                "radiant_angel", "mythic_dragon", "war_torch",
            ],
            stats={"wins": 12, "losses": 8},
        )
        deck_wind = Deck(
            deck_id="deck_wind_combo",
            name="Wind Combo",
            owner_id="player_004",
            archetype=DeckArchetype.COMBO.value,
            format=DeckFormat.WILD.value,
            hero_id="hero_stormcaller",
            card_ids=[
                "mana_wyrm", "mana_wyrm", "arcane_intellect",
                "arcane_intellect", "wind_fury", "wind_fury",
                "storm_harpy", "storm_harpy", "shadow_strike",
                "shadow_strike", "spellbreaker", "spellbreaker",
                "dawn_paladin", "dawn_paladin", "thunder_bird",
                "thunder_bird", "water_elemental", "water_elemental",
                "archmage", "cyclone_djinn", "radiant_angel",
                "death_knight", "scorching_blast", "sun_burst",
                "sun_burst", "ocean_serpent", "soul_reaper",
                "mythic_dragon", "war_torch", "nature_bloom",
            ],
            stats={"wins": 7, "losses": 13},
        )
        deck_neutral = Deck(
            deck_id="deck_neutral_draft",
            name="Neutral Draft",
            owner_id="player_005",
            archetype=DeckArchetype.TEMPO.value,
            format=DeckFormat.DRAFT.value,
            hero_id="hero_wanderer",
            card_ids=[
                "tavern_brawler", "tavern_brawler", "goblin_raider",
                "goblin_raider", "silverback_gorilla", "silverback_gorilla",
                "wandering_merchant", "wandering_merchant", "iron_sentinel",
                "iron_sentinel", "storm_harpy", "storm_harpy",
                "stone_guardian", "stone_guardian", "light_heal",
                "light_heal", "wind_fury", "wind_fury", "shadow_strike",
                "shadow_strike", "thunder_bird", "thunder_bird",
                "dawn_paladin", "dawn_paladin", "earth_golem",
                "water_elemental", "magma_giant", "cyclone_djinn",
                "mythic_dragon", "war_torch",
            ],
            stats={"wins": 5, "losses": 5},
        )
        for deck in (deck_flame, deck_tide, deck_earth, deck_wind, deck_neutral):
            self._decks[deck.deck_id] = deck

        # --- Active matches -------------------------------------------------
        self._seed_match(
            match_id="match_001",
            player_specs=[
                ("player_001", "hero_pyromancer", "deck_flame_aggro"),
                ("player_002", "hero_tideweaver", "deck_tide_control"),
            ],
            turn_number=3,
            current_player="player_001",
        )
        self._seed_match(
            match_id="match_002",
            player_specs=[
                ("player_003", "hero_geomancer", "deck_earth_midrange"),
                ("player_004", "hero_stormcaller", "deck_wind_combo"),
            ],
            turn_number=5,
            current_player="player_004",
        )

        # --- Stats ----------------------------------------------------------
        self._stats.total_cards = len(self._cards)
        self._stats.total_decks = len(self._decks)
        self._stats.total_matches = len(self._matches)
        self._stats.active_matches = len(self._matches)
        self._initialized = True

    def _seed_match(
        self,
        match_id: str,
        player_specs: List[Tuple[str, str, str]],
        turn_number: int,
        current_player: str,
    ) -> None:
        """Build a seeded match with hands, draw piles, and board minions."""
        match = MatchState(
            match_id=match_id,
            current_player=current_player,
            turn_number=turn_number,
            phase=GamePhase.MAIN.value,
            started_at=_now(),
        )
        draw_piles: Dict[str, List[str]] = {}
        for player_id, hero_id, deck_id in player_specs:
            deck = self._decks.get(deck_id)
            pool = list(deck.card_ids) if deck else []
            random.shuffle(pool)
            # Pull a starting hand and a few board minions from the pool.
            starting = pool[: self._config.starting_hand]
            pool = pool[self._config.starting_hand:]
            board_count = min(2, len(pool))
            board_cards = pool[:board_count]
            pool = pool[board_count:]

            player = PlayerState(
                player_id=player_id,
                match_id=match_id,
                hero_id=hero_id,
                health=self._config.starting_health,
                max_health=self._config.starting_health,
                mana=min(self._config.max_mana, turn_number),
                max_mana=min(self._config.max_mana, turn_number),
                deck_remaining=len(pool),
            )
            match.board_state[player_id] = []
            # Hand instances.
            for card_id in starting:
                inst = self._instantiate(card_id, player_id, CardStatus.IN_HAND.value)
                player.hand.append(inst.instance_id)
            # Board instances.
            for card_id in board_cards:
                inst = self._instantiate(card_id, player_id, CardStatus.ON_BOARD.value)
                inst.summoning_sick = False
                inst.turn_played = max(1, turn_number - 1)
                inst.position = len(match.board_state[player_id])
                match.board_state[player_id].append(inst.instance_id)
            match.players.append(player)
            draw_piles[player_id] = pool

        self._matches[match.match_id] = match
        self._draw_piles[match.match_id] = draw_piles
        self._record_event(
            CardDeckEventKind.GAME_STARTED,
            match_id=match.match_id,
            data={"players": [p.player_id for p in match.players],
                  "turn": turn_number},
        )

    # ------------------------------------------------------------------
    # Card Catalog Management
    # ------------------------------------------------------------------

    def register_card(
        self,
        card_id: str,
        name: str,
        card_type: str,
        rarity: str,
        element: str,
        cost: int,
        attack: int = 0,
        health: int = 0,
        text: str = "",
        flavor_text: str = "",
        effects: Optional[List[CardEffect]] = None,
        target_type: str = TargetType.NONE.value,
        is_collectible: bool = True,
        max_per_deck: int = 2,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[CardDefinition]]:
        """Register a new card definition in the catalog."""
        with self._lock:
            if not card_id or not name:
                return False, "missing_required_fields", None
            ctype = _enum_value(card_type, CardType)
            if ctype is None:
                return False, "invalid_card_type", None
            crar = _enum_value(rarity, CardRarity)
            if crar is None:
                return False, "invalid_rarity", None
            celm = _enum_value(element, CardElement)
            if celm is None:
                return False, "invalid_element", None
            ctgt = _enum_value(target_type, TargetType)
            if ctgt is None:
                ctgt = TargetType.NONE.value
            if cost < 0:
                return False, "invalid_cost", None
            if card_id in self._cards:
                return False, "already_exists", None
            if len(self._cards) >= _MAX_CARDS:
                oldest = next(iter(self._cards), None)
                if oldest:
                    self._cards.pop(oldest, None)
            definition = CardDefinition(
                card_id=card_id,
                name=name,
                card_type=ctype,
                rarity=crar,
                element=celm,
                cost=int(cost),
                attack=int(attack),
                health=int(health),
                text=text,
                flavor_text=flavor_text,
                effects=list(effects) if effects else [],
                target_type=ctgt,
                is_collectible=is_collectible,
                max_per_deck=int(max_per_deck),
                metadata=metadata or {},
            )
            self._cards[card_id] = definition
            self._stats.total_cards = len(self._cards)
            self._record_event(
                CardDeckEventKind.CARD_PLAYED,
                card_id=card_id,
                data={"action": "registered", "name": name, "type": ctype},
            )
            return True, "ok", definition

    def get_card(self, card_id: str) -> Optional[CardDefinition]:
        """Return a card definition by id, or None if not found."""
        return self._cards.get(card_id)

    def list_cards(
        self, card_type: str = "", rarity: str = "", element: str = ""
    ) -> List[CardDefinition]:
        """List card definitions, optionally filtered by type, rarity, element."""
        results: List[CardDefinition] = []
        for card in self._cards.values():
            if card_type and card.card_type != card_type:
                continue
            if rarity and card.rarity != rarity:
                continue
            if element and card.element != element:
                continue
            results.append(card)
        return results

    def remove_card(self, card_id: str) -> Tuple[bool, str]:
        """Remove a card definition from the catalog."""
        with self._lock:
            if card_id not in self._cards:
                return False, "not_found"
            # Block removal when the card is still part of a constructed deck.
            for deck in self._decks.values():
                if card_id in deck.card_ids or card_id in deck.sideboard:
                    return False, "in_use"
            self._cards.pop(card_id, None)
            self._stats.total_cards = len(self._cards)
            self._record_event(
                CardDeckEventKind.CARD_DESTROYED,
                card_id=card_id,
                data={"action": "removed"},
            )
            return True, "ok"

    # ------------------------------------------------------------------
    # Deck Management
    # ------------------------------------------------------------------

    def register_deck(
        self,
        deck_id: str,
        name: str,
        owner_id: str,
        archetype: str,
        format: str,
        hero_id: str,
        card_ids: Optional[List[str]] = None,
        sideboard: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Deck]]:
        """Register a new constructed deck."""
        with self._lock:
            if not deck_id or not name or not owner_id or not hero_id:
                return False, "missing_required_fields", None
            if _enum_value(archetype, DeckArchetype) is None:
                return False, "invalid_archetype", None
            if _enum_value(format, DeckFormat) is None:
                return False, "invalid_format", None
            if deck_id in self._decks:
                return False, "already_exists", None
            if len(self._decks) >= _MAX_DECKS:
                oldest = next(iter(self._decks), None)
                if oldest:
                    self._decks.pop(oldest, None)
            deck = Deck(
                deck_id=deck_id,
                name=name,
                owner_id=owner_id,
                archetype=_enum_value(archetype, DeckArchetype),
                format=_enum_value(format, DeckFormat),
                hero_id=hero_id,
                card_ids=list(card_ids) if card_ids else [],
                sideboard=list(sideboard) if sideboard else [],
                metadata=metadata or {},
                created_at=_now(),
                updated_at=_now(),
            )
            self._decks[deck_id] = deck
            self._stats.total_decks = len(self._decks)
            self._record_event(
                CardDeckEventKind.DECK_SHUFFLED,
                player_id=owner_id,
                data={"action": "deck_registered", "deck_id": deck_id, "name": name},
            )
            return True, "ok", deck

    def get_deck(self, deck_id: str) -> Optional[Deck]:
        """Return a deck by id, or None if not found."""
        return self._decks.get(deck_id)

    def list_decks(self, owner_id: str = "", archetype: str = "") -> List[Deck]:
        """List decks, optionally filtered by owner and archetype."""
        results: List[Deck] = []
        for deck in self._decks.values():
            if owner_id and deck.owner_id != owner_id:
                continue
            if archetype and deck.archetype != archetype:
                continue
            results.append(deck)
        return results

    def remove_deck(self, deck_id: str) -> Tuple[bool, str]:
        """Remove a deck from the registry."""
        with self._lock:
            if deck_id not in self._decks:
                return False, "not_found"
            deck = self._decks.pop(deck_id, None)
            self._stats.total_decks = len(self._decks)
            if deck is not None:
                self._record_event(
                    CardDeckEventKind.DECK_SHUFFLED,
                    player_id=deck.owner_id,
                    data={"action": "deck_removed", "deck_id": deck_id},
                )
            return True, "ok"

    def shuffle_deck(self, deck_id: str) -> Tuple[bool, str]:
        """Randomize the order of a deck's draw pile."""
        with self._lock:
            deck = self._decks.get(deck_id)
            if deck is None:
                return False, "not_found"
            random.shuffle(deck.card_ids)
            deck.updated_at = _now()
            self._record_event(
                CardDeckEventKind.DECK_SHUFFLED,
                player_id=deck.owner_id,
                data={"deck_id": deck_id},
            )
            return True, "ok"

    def draw_card(
        self, deck_id: str, count: int = 1
    ) -> Tuple[bool, str, List[CardInstance]]:
        """Draw one or more cards from the top of a deck.

        Drawn cards are instantiated with status ``IN_HAND`` and owned by
        the deck's owner. The deck's ``card_ids`` list is consumed.
        """
        with self._lock:
            deck = self._decks.get(deck_id)
            if deck is None:
                return False, "not_found", []
            if count <= 0:
                return False, "invalid_count", []
            if len(deck.card_ids) < count:
                return False, "insufficient_cards", []
            drawn: List[CardInstance] = []
            for _ in range(count):
                card_id = deck.card_ids.pop(0)
                inst = self._instantiate(card_id, deck.owner_id, CardStatus.IN_HAND.value)
                drawn.append(inst)
            deck.updated_at = _now()
            self._stats.cards_drawn += len(drawn)
            self._record_event(
                CardDeckEventKind.CARD_DRAWN,
                player_id=deck.owner_id,
                data={"deck_id": deck_id, "count": len(drawn),
                      "cards": [i.card_id for i in drawn]},
            )
            return True, "ok", drawn

    # ------------------------------------------------------------------
    # Match Lifecycle
    # ------------------------------------------------------------------

    def create_match(
        self,
        player_ids: List[str],
        format: str = DeckFormat.STANDARD.value,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[MatchState]]:
        """Create a new match between two or more players."""
        with self._lock:
            if not player_ids or len(player_ids) < 2:
                return False, "need_at_least_two_players", None
            fmt = _enum_value(format, DeckFormat)
            if fmt is None:
                return False, "invalid_format", None
            if len(self._matches) >= _MAX_MATCHES:
                oldest = next(iter(self._matches), None)
                if oldest:
                    self._matches.pop(oldest, None)
                    self._draw_piles.pop(oldest, None)
            match_id = self._new_match_id()
            match = MatchState(
                match_id=match_id,
                current_player=player_ids[0],
                turn_number=1,
                phase=GamePhase.MAIN.value,
                started_at=_now(),
                metadata=metadata or {"format": fmt},
            )
            draw_piles: Dict[str, List[str]] = {}
            for idx, player_id in enumerate(player_ids):
                hero_id = f"hero_{player_id}"
                # Seed a draw pile from a representative card pool so that
                # end-of-turn draws work even without an explicit deck link.
                pool = [
                    "goblin_raider", "ember_wolf", "stone_guardian",
                    "wind_fury", "light_heal", "shadow_strike",
                    "arcane_intellect", "nature_bloom", "tavern_brawler",
                    "iron_sentinel", "water_elemental", "earth_golem",
                    "dawn_paladin", "thunder_bird", "storm_harpy",
                    "treant_guardian", "spellbreaker", "magma_giant",
                    "ocean_serpent", "cyclone_djinn", "mythic_dragon",
                    "war_torch", "frost_nova", "sun_burst",
                    "radiant_angel", "death_knight", "mountain_titan",
                    "soul_reaper", "silverback_gorilla", "wandering_merchant",
                ]
                random.shuffle(pool)
                starting = pool[: self._config.starting_hand]
                pool = pool[self._config.starting_hand:]
                player = PlayerState(
                    player_id=player_id,
                    match_id=match_id,
                    hero_id=hero_id,
                    health=self._config.starting_health,
                    max_health=self._config.starting_health,
                    mana=max(self._config.starting_mana, self._config.mana_per_turn),
                    max_mana=max(self._config.starting_mana, self._config.mana_per_turn),
                    deck_remaining=len(pool),
                )
                match.board_state[player_id] = []
                for card_id in starting:
                    inst = self._instantiate(card_id, player_id, CardStatus.IN_HAND.value)
                    player.hand.append(inst.instance_id)
                match.players.append(player)
                draw_piles[player_id] = pool
            self._matches[match_id] = match
            self._draw_piles[match_id] = draw_piles
            self._stats.total_matches = len(self._matches)
            self._stats.active_matches = sum(
                1 for m in self._matches.values() if not m.winner
            )
            self._record_event(
                CardDeckEventKind.GAME_STARTED,
                match_id=match_id,
                data={"players": list(player_ids), "format": fmt},
            )
            return True, "ok", match

    def get_match(self, match_id: str) -> Optional[MatchState]:
        """Return a match by id, or None if not found."""
        return self._matches.get(match_id)

    def list_matches(self, status: str = "") -> List[MatchState]:
        """List matches, optionally filtered by status.

        ``status`` accepts ``"active"`` or ``"finished"``; an empty string
        returns every match.
        """
        results: List[MatchState] = []
        for match in self._matches.values():
            if status == "active" and match.winner:
                continue
            if status == "finished" and not match.winner:
                continue
            results.append(match)
        return results

    # ------------------------------------------------------------------
    # Match Actions
    # ------------------------------------------------------------------

    def play_card(
        self,
        match_id: str,
        player_id: str,
        card_id: str,
        target_id: str = "",
    ) -> Tuple[bool, str, Optional[MatchState]]:
        """Play a card from the player's hand onto the match board."""
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                return False, "match_not_found", None
            if match.winner:
                return False, "match_already_finished", None
            if match.current_player != player_id:
                return False, "not_your_turn", None
            player = self._player(match, player_id)
            if player is None:
                return False, "player_not_in_match", None
            # Locate the matching instance in hand.
            hand_inst: Optional[CardInstance] = None
            for iid in player.hand:
                inst = self._instances.get(iid)
                if inst is not None and inst.card_id == card_id:
                    hand_inst = inst
                    break
            if hand_inst is None:
                return False, "card_not_in_hand", None
            if player.mana < hand_inst.current_cost:
                return False, "insufficient_mana", None
            definition = self._cards.get(hand_inst.card_id)
            if definition is None:
                return False, "card_definition_missing", None

            # Pay the cost and remove from hand.
            player.mana -= hand_inst.current_cost
            player.hand.remove(hand_inst.instance_id)

            if definition.card_type == CardType.MINION.value:
                if len(match.board_state.get(player_id, [])) >= self._config.max_board_size:
                    # Refund and return to hand when the board is full.
                    player.mana += hand_inst.current_cost
                    player.hand.append(hand_inst.instance_id)
                    return False, "board_full", None
                hand_inst.status = CardStatus.ON_BOARD.value
                hand_inst.summoning_sick = True
                hand_inst.turn_played = match.turn_number
                hand_inst.position = len(match.board_state[player_id])
                match.board_state.setdefault(player_id, []).append(hand_inst.instance_id)
            elif definition.card_type == CardType.WEAPON.value:
                hand_inst.status = CardStatus.ON_BOARD.value
                hand_inst.position = -1
            else:
                # Spells and other types resolve immediately and are spent.
                hand_inst.status = CardStatus.IN_GRAVEYARD.value
                player.graveyard.append(hand_inst.instance_id)

            # Resolve attached effects.
            for effect in definition.effects:
                self._apply_effect(match, player_id, effect, target_id)

            self._stats.cards_played += 1
            self._record_event(
                CardDeckEventKind.CARD_PLAYED,
                player_id=player_id,
                card_id=card_id,
                match_id=match_id,
                data={"cost": hand_inst.current_cost, "target": target_id},
            )
            return True, "ok", match

    def _apply_effect(
        self,
        match: MatchState,
        player_id: str,
        effect: CardEffect,
        target_id: str,
    ) -> None:
        """Apply a single card effect to the match state."""
        etype = effect.effect_type
        if etype == EffectType.DAMAGE.value:
            self._deal_damage_internal(match, target_id, effect.value, player_id)
        elif etype == EffectType.HEAL.value:
            self._heal_internal(match, target_id, effect.value)
        elif etype == EffectType.DRAW_CARD.value:
            player = self._player(match, player_id)
            if player is not None:
                self._draw_for_player(match, player, effect.value)
        elif etype == EffectType.BUFF.value:
            kind, target = self._resolve_target(match, target_id)
            if kind == "minion" and target is not None:
                target.current_attack += effect.value
                target.buffs.append({"type": "buff", "attack": effect.value})
        elif etype == EffectType.DEBUFF.value:
            kind, target = self._resolve_target(match, target_id)
            if kind == "minion" and target is not None:
                target.current_attack = max(0, target.current_attack - effect.value)
                target.buffs.append({"type": "debuff", "attack": -effect.value})
        elif etype == EffectType.RESTORE_MANA.value:
            player = self._player(match, player_id)
            if player is not None:
                player.mana = min(player.max_mana, player.mana + effect.value)
        elif etype == EffectType.DESTROY.value:
            kind, target = self._resolve_target(match, target_id)
            if kind == "minion" and target is not None:
                self._destroy_minion(match, target)
        elif etype == EffectType.SUMMON.value:
            # Summon a generic token onto the owner's board when space allows.
            board = match.board_state.setdefault(player_id, [])
            if len(board) < self._config.max_board_size:
                token = self._instantiate("goblin_raider", player_id, CardStatus.ON_BOARD.value)
                token.summoning_sick = True
                token.turn_played = match.turn_number
                token.position = len(board)
                board.append(token.instance_id)
        else:
            # Other effect kinds (transform, discover, mill, random, etc.)
            # are recorded but not fully resolved in this lightweight engine.
            match.active_effects.append(
                {"effect_id": effect.effect_id, "type": etype, "value": effect.value,
                 "duration": effect.duration}
            )

    def _draw_for_player(self, match: MatchState, player: PlayerState, count: int) -> None:
        """Draw cards from a player's match draw pile into their hand."""
        pile = self._draw_piles.get(match.match_id, {}).get(player.player_id, [])
        for _ in range(max(0, count)):
            if len(player.hand) >= self._config.max_hand_size:
                # Overdraw burns the card straight to the graveyard.
                if pile:
                    burned = pile.pop(0)
                    player.deck_remaining = len(pile)
                    self._record_event(
                        CardDeckEventKind.CARD_DESTROYED,
                        player_id=player.player_id,
                        match_id=match.match_id,
                        data={"action": "overdraw_burn", "card_id": burned},
                    )
                continue
            if not pile:
                # Fatigue damages the player when the draw pile is empty.
                player.fatigue_count += 1
                fatigue = player.fatigue_count
                self._deal_damage_internal(match, player.player_id, fatigue, "")
                continue
            card_id = pile.pop(0)
            inst = self._instantiate(card_id, player.player_id, CardStatus.IN_HAND.value)
            player.hand.append(inst.instance_id)
            player.deck_remaining = len(pile)
            self._stats.cards_drawn += 1
            self._record_event(
                CardDeckEventKind.CARD_DRAWN,
                player_id=player.player_id,
                match_id=match.match_id,
                data={"card_id": card_id},
            )

    def end_turn(
        self, match_id: str, player_id: str
    ) -> Tuple[bool, str, Optional[MatchState]]:
        """End the current player's turn and advance to the next player."""
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                return False, "match_not_found", None
            if match.winner:
                return False, "match_already_finished", None
            if match.current_player != player_id:
                return False, "not_your_turn", None
            match.phase = GamePhase.END.value
            self._record_event(
                CardDeckEventKind.TURN_ENDED,
                player_id=player_id,
                match_id=match_id,
                data={"turn": match.turn_number},
            )
            # Rotate to the next player in turn order.
            ids = [p.player_id for p in match.players]
            idx = ids.index(player_id)
            next_id = ids[(idx + 1) % len(ids)]
            match.current_player = next_id
            match.turn_number += 1
            match.phase = GamePhase.MAIN.value
            next_player = self._player(match, next_id)
            if next_player is not None:
                next_player.max_mana = min(
                    self._config.max_mana,
                    next_player.max_mana + self._config.mana_per_turn,
                )
                next_player.mana = next_player.max_mana
                # Refresh friendly minions: summoning sickness wears off.
                for iid in match.board_state.get(next_id, []):
                    inst = self._instances.get(iid)
                    if inst is not None:
                        inst.summoning_sick = False
                # Opening draw for the turn.
                self._draw_for_player(match, next_player, 1)
            self._record_event(
                CardDeckEventKind.TURN_STARTED,
                player_id=next_id,
                match_id=match_id,
                data={"turn": match.turn_number},
            )
            return True, "ok", match

    def deal_damage(
        self,
        match_id: str,
        target_id: str,
        amount: int,
        source_id: str = "",
    ) -> Tuple[bool, str, Optional[MatchState]]:
        """Deal damage to a player or minion in a match."""
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                return False, "match_not_found", None
            if amount <= 0:
                return False, "invalid_amount", None
            self._deal_damage_internal(match, target_id, amount, source_id)
            return True, "ok", match

    def _deal_damage_internal(
        self,
        match: MatchState,
        target_id: str,
        amount: int,
        source_id: str,
    ) -> None:
        """Apply damage resolution and trigger death and win checks."""
        kind, target = self._resolve_target(match, target_id)
        if kind == "player" and target is not None:
            player: PlayerState = target
            remaining = amount
            if player.armor > 0:
                absorbed = min(player.armor, remaining)
                player.armor -= absorbed
                remaining -= absorbed
            player.health -= remaining
            if player.health <= 0:
                player.health = 0
                opponent = self._opponent(match, player.player_id)
                match.winner = opponent.player_id if opponent else ""
                match.phase = GamePhase.END.value
                match.ended_at = _now()
                self._stats.games_completed += 1
                self._record_event(
                    CardDeckEventKind.GAME_ENDED,
                    player_id=player.player_id,
                    match_id=match.match_id,
                    data={"winner": match.winner},
                )
        elif kind == "minion" and target is not None:
            inst: CardInstance = target
            inst.current_health -= amount
            if inst.current_health <= 0:
                self._destroy_minion(match, inst)

    def _destroy_minion(self, match: MatchState, inst: CardInstance) -> None:
        """Move a minion to its owner's graveyard and off the board."""
        inst.status = CardStatus.IN_GRAVEYARD.value
        board = match.board_state.get(inst.owner_id, [])
        if inst.instance_id in board:
            board.remove(inst.instance_id)
        owner = self._player(match, inst.owner_id)
        if owner is not None:
            owner.graveyard.append(inst.instance_id)
        self._record_event(
            CardDeckEventKind.CARD_DESTROYED,
            player_id=inst.owner_id,
            card_id=inst.card_id,
            match_id=match.match_id,
            data={"instance_id": inst.instance_id},
        )

    def heal_target(
        self, match_id: str, target_id: str, amount: int
    ) -> Tuple[bool, str, Optional[MatchState]]:
        """Restore health to a player or minion in a match."""
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                return False, "match_not_found", None
            if amount <= 0:
                return False, "invalid_amount", None
            self._heal_internal(match, target_id, amount)
            return True, "ok", match

    def _heal_internal(self, match: MatchState, target_id: str, amount: int) -> None:
        """Apply healing resolution to a player or minion."""
        kind, target = self._resolve_target(match, target_id)
        if kind == "player" and target is not None:
            player: PlayerState = target
            player.health = min(player.max_health, player.health + amount)
        elif kind == "minion" and target is not None:
            inst: CardInstance = target
            definition = self._cards.get(inst.card_id)
            cap = definition.health if definition else inst.current_health + amount
            inst.current_health = min(cap, inst.current_health + amount)

    # ------------------------------------------------------------------
    # Match & Deck Inspection
    # ------------------------------------------------------------------

    def get_player_state(
        self, match_id: str, player_id: str
    ) -> Optional[PlayerState]:
        """Return the player state for a player in a match."""
        match = self._matches.get(match_id)
        if match is None:
            return None
        return self._player(match, player_id)

    def get_board_state(self, match_id: str) -> Dict[str, Any]:
        """Return the full board state for a match as a serializable dict."""
        match = self._matches.get(match_id)
        if match is None:
            return {}
        result: Dict[str, Any] = {}
        for player_id, instance_ids in match.board_state.items():
            result[player_id] = [
                self._instances[iid].to_dict()
                for iid in instance_ids
                if iid in self._instances
            ]
        return result

    def calculate_deck_stats(self, deck_id: str) -> Optional[Dict[str, Any]]:
        """Compute a mana curve and distribution breakdown for a deck."""
        deck = self._decks.get(deck_id)
        if deck is None:
            return None
        mana_curve: Dict[int, int] = {}
        by_type: Dict[str, int] = {}
        by_rarity: Dict[str, int] = {}
        by_element: Dict[str, int] = {}
        total_cost = 0
        count = 0
        for card_id in deck.card_ids:
            card = self._cards.get(card_id)
            if card is None:
                continue
            count += 1
            total_cost += card.cost
            mana_curve[card.cost] = mana_curve.get(card.cost, 0) + 1
            by_type[card.card_type] = by_type.get(card.card_type, 0) + 1
            by_rarity[card.rarity] = by_rarity.get(card.rarity, 0) + 1
            by_element[card.element] = by_element.get(card.element, 0) + 1
        avg_cost = (total_cost / count) if count else 0.0
        return {
            "deck_id": deck_id,
            "total_cards": count,
            "avg_cost": round(avg_cost, 2),
            "mana_curve": dict(sorted(mana_curve.items())),
            "by_type": by_type,
            "by_rarity": by_rarity,
            "by_element": by_element,
        }

    def validate_deck(self, deck_id: str) -> Tuple[bool, str, List[str]]:
        """Validate a deck against format and construction rules."""
        deck = self._decks.get(deck_id)
        if deck is None:
            return False, "not_found", []
        issues: List[str] = []
        size = len(deck.card_ids)
        if size != self._config.deck_size:
            issues.append(
                f"deck_size_mismatch: has {size}, expected {self._config.deck_size}"
            )
        counts: Dict[str, int] = {}
        for card_id in deck.card_ids:
            card = self._cards.get(card_id)
            if card is None:
                issues.append(f"unknown_card: {card_id}")
                continue
            if not card.is_collectible:
                issues.append(f"non_collectible: {card_id}")
            counts[card_id] = counts.get(card_id, 0) + 1
        for card_id, cnt in counts.items():
            card = self._cards.get(card_id)
            if card is not None and cnt > card.max_per_deck:
                issues.append(
                    f"over_limit: {card_id} has {cnt}, max {card.max_per_deck}"
                )
        if not deck.hero_id:
            issues.append("missing_hero")
        if issues:
            return False, "validation_failed", issues
        return True, "ok", []

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the simulation, expiring transient active effects."""
        with self._lock:
            self._tick_count += 1
            expired_effects: List[Dict[str, Any]] = []
            for match in self._matches.values():
                if match.winner:
                    continue
                remaining: List[Dict[str, Any]] = []
                for effect in match.active_effects:
                    duration = _safe_int(effect.get("duration"), 0)
                    if duration > 0:
                        duration -= 1
                        effect["duration"] = duration
                        if duration > 0:
                            remaining.append(effect)
                        else:
                            expired_effects.append(effect)
                    else:
                        remaining.append(effect)
                match.active_effects = remaining
            if expired_effects:
                self._record_event(
                    CardDeckEventKind.TURN_ENDED,
                    data={"action": "tick_expired_effects",
                          "count": len(expired_effects)},
                )
            active = sum(1 for m in self._matches.values() if not m.winner)
            self._stats.active_matches = active
            return {
                "tick_count": self._tick_count,
                "dt": dt,
                "active_matches": active,
                "expired_effects": len(expired_effects),
            }

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def get_config(self) -> CardDeckConfig:
        """Return the current system configuration."""
        return self._config

    def set_config(self, updates: Dict[str, Any]) -> Tuple[bool, str, CardDeckConfig]:
        """Apply a partial update to the system configuration."""
        with self._lock:
            if not isinstance(updates, dict):
                return False, "invalid_updates", self._config
            applied: List[str] = []
            for key, value in updates.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
                    applied.append(key)
            self._record_event(
                CardDeckEventKind.GAME_STARTED,
                data={"action": "config_updated", "fields": applied},
            )
            return True, "ok", self._config

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(
        self, limit: int = 100, match_id: str = "", event_type: str = ""
    ) -> List[CardDeckEvent]:
        """Return recent audit events, newest first, with optional filters."""
        results: List[CardDeckEvent] = []
        cap = max(0, int(limit))
        for event in reversed(self._events):
            if match_id and event.match_id != match_id:
                continue
            if event_type and event.kind != event_type:
                continue
            results.append(event)
            if len(results) >= cap:
                break
        return results

    def get_stats(self) -> CardDeckStats:
        """Return aggregate system statistics."""
        self._stats.total_cards = len(self._cards)
        self._stats.total_decks = len(self._decks)
        self._stats.total_matches = len(self._matches)
        self._stats.active_matches = sum(1 for m in self._matches.values() if not m.winner)
        self._stats.total_events = len(self._events)
        completed = [m for m in self._matches.values() if m.winner]
        if completed:
            lengths = []
            for m in completed:
                try:
                    start = datetime.fromisoformat(m.started_at)
                    end = datetime.fromisoformat(m.ended_at)
                    lengths.append((end - start).total_seconds())
                except (TypeError, ValueError):
                    continue
            if lengths:
                self._stats.avg_game_length = round(
                    sum(lengths) / len(lengths), 2
                )
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        """Return a concise status summary of the system."""
        return {
            "initialized": self._initialized,
            "total_cards": len(self._cards),
            "total_decks": len(self._decks),
            "total_matches": len(self._matches),
            "active_matches": sum(1 for m in self._matches.values() if not m.winner),
            "total_instances": len(self._instances),
            "cards_played": self._stats.cards_played,
            "cards_drawn": self._stats.cards_drawn,
            "games_completed": self._stats.games_completed,
            "total_events": len(self._events),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> CardDeckSnapshot:
        """Return a point-in-time snapshot of system counters and config."""
        return CardDeckSnapshot(
            timestamp=_now(),
            cards_count=len(self._cards),
            decks_count=len(self._decks),
            matches_count=len(self._matches),
            active_matches=sum(1 for m in self._matches.values() if not m.winner),
            config=self._config,
        )

    def reset(self) -> Tuple[bool, str]:
        """Clear all state and re-seed the system from scratch."""
        with self._init_lock:
            self._cards.clear()
            self._decks.clear()
            self._matches.clear()
            self._instances.clear()
            self._events.clear()
            self._draw_piles.clear()
            self._stats = CardDeckStats()
            self._config = CardDeckConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._instance_counter = 0
            self._match_counter = 0
            self._initialized = False
            self._seed()
        self._record_event(
            CardDeckEventKind.GAME_ENDED,
            data={"action": "system_reset"},
        )
        return True, "ok"


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_card_deck_system() -> CardDeckSystem:
    """Return the shared CardDeckSystem singleton instance."""
    return CardDeckSystem.get_instance()
