"""
SparkLabs Engine - Living World System

A living world simulation engine for the SparkLabs AI-native game
engine. It models ecosystems, NPC societies, and emergent events that
evolve independently of player actions, creating a dynamic, responsive
game environment. The system advances simulation ticks, tracks
population dynamics, manages faction relationships, and triggers
contextual world events.

Architecture:
  LivingWorldSystem (singleton)
    |-- WorldRegion, EcosystemState, NPCCommunity, FactionRelation,
       WorldEvent, SimulationTick, LivingWorldStats, LivingWorldSnapshot,
       LivingWorldEvent
    |-- BiomeType, PopulationTrend, FactionStance, EventSeverity,
       EventCategory, LivingWorldEventKind

Core Capabilities:
  - register_region / get_region / list_regions: spatial partitioning of
    the world into biomes with carrying capacity and climate data.
  - register_community / get_community / list_communities: NPC
    population groups with needs, resources, and mood.
  - register_faction / set_faction_stance: faction lifecycle and
    inter-faction relationship management.
  - advance_tick: advance the simulation by one tick, updating
    populations, resources, moods, and triggering events.
  - trigger_event / resolve_event / list_events: world event lifecycle
    with severity, category, and affected regions.
  - get_ecosystem / update_ecosystem: per-region ecosystem state
    tracking with flora, fauna, and weather.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`LivingWorldSystem.get_instance` or the module-level
:func:`get_living_world_system` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_REGIONS: int = 500
_MAX_COMMUNITIES: int = 2000
_MAX_FACTIONS: int = 500
_MAX_RELATIONS: int = 5000
_MAX_EVENTS: int = 3000
_MAX_TICKS: int = 5000
_MAX_AUDIT_EVENTS: int = 5000


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


class BiomeType(Enum):
    """Biome categories for world regions."""
    FOREST = "forest"
    DESERT = "desert"
    TUNDRA = "tundra"
    GRASSLAND = "grassland"
    WETLAND = "wetland"
    MOUNTAIN = "mountain"
    COASTAL = "coastal"
    URBAN = "urban"
    VOLCANIC = "volcanic"
    ARCTIC = "arctic"


class PopulationTrend(Enum):
    """Direction of population change in a community."""
    GROWING = "growing"
    STABLE = "stable"
    DECLINING = "declining"
    CRASHING = "crashing"
    BOOMING = "booming"


class FactionStance(Enum):
    """Relationship stance between two factions."""
    ALLIED = "allied"
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    WARY = "wary"
    HOSTILE = "hostile"
    AT_WAR = "at_war"


class EventSeverity(Enum):
    """Impact level of a world event."""
    TRIVIAL = "trivial"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CATASTROPHIC = "catastrophic"


class EventCategory(Enum):
    """Category of world events."""
    ECOLOGICAL = "ecological"
    SOCIAL = "social"
    ECONOMIC = "economic"
    POLITICAL = "political"
    SUPERNATURAL = "supernatural"
    WEATHER = "weather"
    CONFLICT = "conflict"
    DISCOVERY = "discovery"
    MIGRATION = "migration"
    PLAGUE = "plague"


class LivingWorldEventKind(Enum):
    """Audit event types emitted by the living world system."""
    REGION_REGISTERED = "region_registered"
    COMMUNITY_REGISTERED = "community_registered"
    FACTION_REGISTERED = "faction_registered"
    STANCE_UPDATED = "stance_updated"
    TICK_ADVANCED = "tick_advanced"
    EVENT_TRIGGERED = "event_triggered"
    EVENT_RESOLVED = "event_resolved"
    ECOSYSTEM_UPDATED = "ecosystem_updated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class WorldRegion:
    """A spatial partition of the world with a biome and climate."""
    region_id: str = field(default_factory=lambda: _new_id("rgn"))
    name: str = ""
    biome: str = BiomeType.FOREST.value
    climate_temp: float = 20.0
    climate_humidity: float = 0.5
    carrying_capacity: int = 1000
    area_sqkm: float = 100.0
    coordinates: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EcosystemState:
    """Per-region ecosystem state tracking flora, fauna, and weather."""
    ecosystem_id: str = field(default_factory=lambda: _new_id("eco"))
    region_id: str = ""
    flora_density: float = 0.5
    fauna_density: float = 0.5
    water_availability: float = 0.5
    soil_fertility: float = 0.5
    pollution_level: float = 0.0
    biodiversity_index: float = 0.5
    weather_condition: str = "clear"
    season: str = "spring"
    last_updated_tick: int = 0
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NPCCommunity:
    """A population group of NPCs with needs, resources, and mood."""
    community_id: str = field(default_factory=lambda: _new_id("com"))
    name: str = ""
    region_id: str = ""
    faction_id: str = ""
    population: int = 100
    trend: str = PopulationTrend.STABLE.value
    mood: float = 0.5
    prosperity: float = 0.5
    food_supply: float = 0.5
    safety_level: float = 0.5
    culture: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FactionRelation:
    """A directed relationship between two factions."""
    relation_id: str = field(default_factory=lambda: _new_id("rel"))
    faction_a: str = ""
    faction_b: str = ""
    stance: str = FactionStance.NEUTRAL.value
    trust: float = 0.5
    trade_volume: float = 0.0
    last_conflict_tick: int = -1
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WorldEvent:
    """An emergent event in the world with severity and scope."""
    event_id: str = field(default_factory=lambda: _new_id("wev"))
    name: str = ""
    category: str = EventCategory.ECOLOGICAL.value
    severity: str = EventSeverity.MINOR.value
    region_ids: List[str] = field(default_factory=list)
    community_ids: List[str] = field(default_factory=list)
    description: str = ""
    triggered_tick: int = 0
    resolved_tick: int = -1
    resolved: bool = False
    impact_score: float = 0.3
    resolution_notes: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SimulationTick:
    """A single advancement of the world simulation."""
    tick_id: str = field(default_factory=lambda: _new_id("tick"))
    tick_number: int = 0
    regions_updated: int = 0
    communities_updated: int = 0
    events_triggered: int = 0
    events_resolved: int = 0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LivingWorldStats:
    """Aggregate counters for the living world."""
    total_regions: int = 0
    total_communities: int = 0
    total_factions: int = 0
    total_relations: int = 0
    total_events: int = 0
    active_events: int = 0
    total_ticks: int = 0
    current_tick: int = 0
    total_population: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LivingWorldSnapshot:
    """Immutable point-in-time capture of world state."""
    regions: Dict[str, Any] = field(default_factory=dict)
    communities: Dict[str, Any] = field(default_factory=dict)
    factions: Dict[str, Any] = field(default_factory=dict)
    events: Dict[str, Any] = field(default_factory=dict)
    ecosystems: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LivingWorldEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("aud"))
    kind: str = LivingWorldEventKind.REGION_REGISTERED.value
    region_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Living World System Singleton
# ---------------------------------------------------------------------------


class LivingWorldSystem:
    """Singleton system that simulates a living, evolving game world.

    The system maintains regions, communities, factions, ecosystems, and
    events. Each tick advances population dynamics, updates moods and
    resources, and may trigger emergent world events based on the
    current state.
    """

    _instance: Optional["LivingWorldSystem"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._regions: Dict[str, WorldRegion] = {}
        self._ecosystems: Dict[str, EcosystemState] = {}
        self._communities: Dict[str, NPCCommunity] = {}
        self._factions: Dict[str, str] = {}
        self._faction_names: Dict[str, str] = {}
        self._relations: Dict[str, FactionRelation] = {}
        self._events: Dict[str, WorldEvent] = {}
        self._ticks: List[SimulationTick] = []
        self._audit: List[LivingWorldEvent] = []
        self._current_tick: int = 0

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "LivingWorldSystem":
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

    def _emit(self, kind: LivingWorldEventKind, region_id: str = "",
              payload: Optional[Dict[str, Any]] = None) -> None:
        event = LivingWorldEvent(
            kind=kind.value,
            region_id=region_id,
            payload=payload or {},
        )
        self._audit.append(event)
        _evict_fifo_list(self._audit, _MAX_AUDIT_EVENTS)

    def _coerce_biome(self, value: Any) -> BiomeType:
        if isinstance(value, BiomeType):
            return value
        if isinstance(value, str) and value:
            try:
                return BiomeType(value)
            except ValueError:
                pass
        return BiomeType.FOREST

    def _coerce_trend(self, value: Any) -> PopulationTrend:
        if isinstance(value, PopulationTrend):
            return value
        if isinstance(value, str) and value:
            try:
                return PopulationTrend(value)
            except ValueError:
                pass
        return PopulationTrend.STABLE

    def _coerce_stance(self, value: Any) -> FactionStance:
        if isinstance(value, FactionStance):
            return value
        if isinstance(value, str) and value:
            try:
                return FactionStance(value)
            except ValueError:
                pass
        return FactionStance.NEUTRAL

    def _coerce_severity(self, value: Any) -> EventSeverity:
        if isinstance(value, EventSeverity):
            return value
        if isinstance(value, str) and value:
            try:
                return EventSeverity(value)
            except ValueError:
                pass
        return EventSeverity.MINOR

    def _coerce_category(self, value: Any) -> EventCategory:
        if isinstance(value, EventCategory):
            return value
        if isinstance(value, str) and value:
            try:
                return EventCategory(value)
            except ValueError:
                pass
        return EventCategory.ECOLOGICAL

    def _relation_key(self, a: str, b: str) -> str:
        return f"{a}:{b}"

    # ------------------------------------------------------------------
    # Region Management
    # ------------------------------------------------------------------

    def register_region(
        self,
        name: str,
        biome: Any = BiomeType.FOREST.value,
        climate_temp: Any = 20.0,
        climate_humidity: Any = 0.5,
        carrying_capacity: Any = 1000,
        area_sqkm: Any = 100.0,
        coordinates: Any = None,
        tags: Any = None,
        region_id: str = "",
    ) -> WorldRegion:
        """Register a new world region."""
        with self._lock:
            biome_enum = self._coerce_biome(biome)
            rid = region_id if region_id else _new_id("rgn")
            region = WorldRegion(
                region_id=rid,
                name=name,
                biome=biome_enum.value,
                climate_temp=_safe_float(climate_temp, 20.0),
                climate_humidity=_safe_float(climate_humidity, 0.5),
                carrying_capacity=_safe_int(carrying_capacity, 1000),
                area_sqkm=_safe_float(area_sqkm, 100.0),
                coordinates=dict(coordinates) if coordinates else {},
                tags=list(tags) if tags else [],
            )
            self._regions[rid] = region
            _evict_fifo_dict(self._regions, _MAX_REGIONS)
            eco = EcosystemState(region_id=rid)
            self._ecosystems[rid] = eco
            self._emit(LivingWorldEventKind.REGION_REGISTERED, rid,
                       {"name": name, "biome": biome_enum.value})
            return region

    def get_region(self, region_id: str) -> Optional[WorldRegion]:
        with self._lock:
            return self._regions.get(region_id)

    def list_regions(self, biome: Any = None, limit: int = 100) -> List[WorldRegion]:
        with self._lock:
            items = list(self._regions.values())
            if biome is not None and biome != "":
                b = self._coerce_biome(biome).value
                items = [r for r in items if r.biome == b]
            return items[:limit]

    # ------------------------------------------------------------------
    # Ecosystem Management
    # ------------------------------------------------------------------

    def get_ecosystem(self, region_id: str) -> Optional[EcosystemState]:
        with self._lock:
            return self._ecosystems.get(region_id)

    def update_ecosystem(
        self,
        region_id: str,
        flora_density: Any = None,
        fauna_density: Any = None,
        water_availability: Any = None,
        soil_fertility: Any = None,
        pollution_level: Any = None,
        biodiversity_index: Any = None,
        weather_condition: str = "",
        season: str = "",
    ) -> Optional[EcosystemState]:
        """Update the ecosystem state of a region."""
        with self._lock:
            eco = self._ecosystems.get(region_id)
            if eco is None:
                return None
            if flora_density is not None:
                eco.flora_density = _safe_float(flora_density, eco.flora_density)
            if fauna_density is not None:
                eco.fauna_density = _safe_float(fauna_density, eco.fauna_density)
            if water_availability is not None:
                eco.water_availability = _safe_float(water_availability, eco.water_availability)
            if soil_fertility is not None:
                eco.soil_fertility = _safe_float(soil_fertility, eco.soil_fertility)
            if pollution_level is not None:
                eco.pollution_level = _safe_float(pollution_level, eco.pollution_level)
            if biodiversity_index is not None:
                eco.biodiversity_index = _safe_float(biodiversity_index, eco.biodiversity_index)
            if weather_condition:
                eco.weather_condition = weather_condition
            if season:
                eco.season = season
            eco.last_updated_tick = self._current_tick
            eco.updated_at = _now()
            self._emit(LivingWorldEventKind.ECOSYSTEM_UPDATED, region_id,
                       {"flora": eco.flora_density, "fauna": eco.fauna_density})
            return eco

    # ------------------------------------------------------------------
    # Community Management
    # ------------------------------------------------------------------

    def register_community(
        self,
        name: str,
        region_id: str = "",
        faction_id: str = "",
        population: Any = 100,
        trend: Any = PopulationTrend.STABLE.value,
        mood: Any = 0.5,
        prosperity: Any = 0.5,
        food_supply: Any = 0.5,
        safety_level: Any = 0.5,
        culture: str = "",
        community_id: str = "",
    ) -> NPCCommunity:
        """Register a new NPC community."""
        with self._lock:
            cid = community_id if community_id else _new_id("com")
            community = NPCCommunity(
                community_id=cid,
                name=name,
                region_id=region_id,
                faction_id=faction_id,
                population=_safe_int(population, 100),
                trend=self._coerce_trend(trend).value,
                mood=_safe_float(mood, 0.5),
                prosperity=_safe_float(prosperity, 0.5),
                food_supply=_safe_float(food_supply, 0.5),
                safety_level=_safe_float(safety_level, 0.5),
                culture=culture,
            )
            self._communities[cid] = community
            _evict_fifo_dict(self._communities, _MAX_COMMUNITIES)
            self._emit(LivingWorldEventKind.COMMUNITY_REGISTERED, region_id,
                       {"name": name, "population": community.population})
            return community

    def get_community(self, community_id: str) -> Optional[NPCCommunity]:
        with self._lock:
            return self._communities.get(community_id)

    def list_communities(self, region_id: str = "", limit: int = 100) -> List[NPCCommunity]:
        with self._lock:
            items = list(self._communities.values())
            if region_id:
                items = [c for c in items if c.region_id == region_id]
            return items[:limit]

    # ------------------------------------------------------------------
    # Faction Management
    # ------------------------------------------------------------------

    def register_faction(self, faction_id: str = "", name: str = "") -> str:
        """Register a new faction and return its ID."""
        with self._lock:
            fid = faction_id if faction_id else _new_id("fct")
            self._factions[fid] = name or fid
            self._faction_names[fid] = name or fid
            self._emit(LivingWorldEventKind.FACTION_REGISTERED, "",
                       {"faction_id": fid, "name": name})
            return fid

    def set_faction_stance(
        self,
        faction_a: str,
        faction_b: str,
        stance: Any = FactionStance.NEUTRAL.value,
        trust: Any = 0.5,
        trade_volume: Any = 0.0,
    ) -> FactionRelation:
        """Set or update the relationship between two factions."""
        with self._lock:
            stance_enum = self._coerce_stance(stance)
            key = self._relation_key(faction_a, faction_b)
            rel = self._relations.get(key)
            if rel is None:
                rel = FactionRelation(
                    faction_a=faction_a,
                    faction_b=faction_b,
                    stance=stance_enum.value,
                    trust=_safe_float(trust, 0.5),
                    trade_volume=_safe_float(trade_volume, 0.0),
                )
            else:
                rel.stance = stance_enum.value
                rel.trust = _safe_float(trust, rel.trust)
                rel.trade_volume = _safe_float(trade_volume, rel.trade_volume)
                rel.updated_at = _now()
            self._relations[key] = rel
            _evict_fifo_dict(self._relations, _MAX_RELATIONS)
            self._emit(LivingWorldEventKind.STANCE_UPDATED, "",
                       {"a": faction_a, "b": faction_b, "stance": stance_enum.value})
            return rel

    def get_faction_stance(self, faction_a: str, faction_b: str) -> Optional[FactionRelation]:
        with self._lock:
            return self._relations.get(self._relation_key(faction_a, faction_b))

    def list_factions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"faction_id": fid, "name": name}
                    for fid, name in self._factions.items()]

    def list_relations(self, faction_id: str = "", limit: int = 100) -> List[FactionRelation]:
        with self._lock:
            items = list(self._relations.values())
            if faction_id:
                items = [r for r in items if r.faction_a == faction_id or r.faction_b == faction_id]
            return items[:limit]

    # ------------------------------------------------------------------
    # Simulation Tick
    # ------------------------------------------------------------------

    def advance_tick(self) -> SimulationTick:
        """Advance the world simulation by one tick."""
        with self._lock:
            self._current_tick += 1
            tick_num = self._current_tick
            regions_updated = 0
            communities_updated = 0
            events_triggered = 0
            events_resolved = 0
            # Update ecosystems with small random-like drift
            for eco in self._ecosystems.values():
                drift = 0.02
                eco.flora_density = max(0.0, min(1.0, eco.flora_density + drift * (0.5 - eco.flora_density)))
                eco.fauna_density = max(0.0, min(1.0, eco.fauna_density + drift * (0.5 - eco.fauna_density)))
                eco.water_availability = max(0.0, min(1.0, eco.water_availability + drift * (0.5 - eco.water_availability)))
                eco.last_updated_tick = tick_num
                eco.updated_at = _now()
                regions_updated += 1
            # Update communities based on ecosystem and trend
            for com in self._communities.values():
                eco = self._ecosystems.get(com.region_id)
                if eco:
                    com.food_supply = max(0.0, min(1.0,
                        (com.food_supply + eco.flora_density + eco.fauna_density) / 3))
                    if eco.pollution_level > 0.5:
                        com.mood = max(0.0, com.mood - 0.05)
                    else:
                        com.mood = max(0.0, min(1.0, com.mood + 0.02))
                # Population dynamics
                if com.trend == PopulationTrend.GROWING.value:
                    com.population = int(com.population * 1.02)
                elif com.trend == PopulationTrend.BOOMING.value:
                    com.population = int(com.population * 1.08)
                elif com.trend == PopulationTrend.DECLINING.value:
                    com.population = int(com.population * 0.98)
                elif com.trend == PopulationTrend.CRASHING.value:
                    com.population = int(com.population * 0.90)
                com.updated_at = _now()
                communities_updated += 1
            # Auto-resolve old events
            for ev in self._events.values():
                if not ev.resolved and (tick_num - ev.triggered_tick) > 10:
                    ev.resolved = True
                    ev.resolved_tick = tick_num
                    ev.resolution_notes = "Auto-resolved after timeout"
                    events_resolved += 1
            tick = SimulationTick(
                tick_number=tick_num,
                regions_updated=regions_updated,
                communities_updated=communities_updated,
                events_triggered=events_triggered,
                events_resolved=events_resolved,
            )
            self._ticks.append(tick)
            _evict_fifo_list(self._ticks, _MAX_TICKS)
            self._emit(LivingWorldEventKind.TICK_ADVANCED, "",
                       {"tick": tick_num, "regions": regions_updated,
                        "communities": communities_updated})
            return tick

    # ------------------------------------------------------------------
    # World Events
    # ------------------------------------------------------------------

    def trigger_event(
        self,
        name: str,
        category: Any = EventCategory.ECOLOGICAL.value,
        severity: Any = EventSeverity.MINOR.value,
        region_ids: Any = None,
        community_ids: Any = None,
        description: str = "",
        impact_score: Any = 0.3,
        event_id: str = "",
    ) -> WorldEvent:
        """Trigger a new world event."""
        with self._lock:
            cat = self._coerce_category(category)
            sev = self._coerce_severity(severity)
            eid = event_id if event_id else _new_id("wev")
            event = WorldEvent(
                event_id=eid,
                name=name,
                category=cat.value,
                severity=sev.value,
                region_ids=list(region_ids) if region_ids else [],
                community_ids=list(community_ids) if community_ids else [],
                description=description,
                triggered_tick=self._current_tick,
                impact_score=_safe_float(impact_score, 0.3),
            )
            self._events[eid] = event
            _evict_fifo_dict(self._events, _MAX_EVENTS)
            self._emit(LivingWorldEventKind.EVENT_TRIGGERED, "",
                       {"event_id": eid, "name": name, "severity": sev.value})
            return event

    def resolve_event(self, event_id: str, resolution_notes: str = "") -> Optional[WorldEvent]:
        """Resolve an active world event."""
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return None
            event.resolved = True
            event.resolved_tick = self._current_tick
            event.resolution_notes = resolution_notes
            self._emit(LivingWorldEventKind.EVENT_RESOLVED, "",
                       {"event_id": event_id, "tick": self._current_tick})
            return event

    def get_event(self, event_id: str) -> Optional[WorldEvent]:
        with self._lock:
            return self._events.get(event_id)

    def list_events(self, active_only: bool = False, category: Any = None,
                    severity: Any = None, limit: int = 100) -> List[WorldEvent]:
        with self._lock:
            items = list(self._events.values())
            if active_only:
                items = [e for e in items if not e.resolved]
            if category is not None and category != "":
                cat_val = self._coerce_category(category).value
                items = [e for e in items if e.category == cat_val]
            if severity is not None and severity != "":
                sev_val = self._coerce_severity(severity).value
                items = [e for e in items if e.severity == sev_val]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_audit_events(self, limit: int = 100) -> List[LivingWorldEvent]:
        with self._lock:
            return list(self._audit[-limit:])

    def list_ticks(self, limit: int = 100) -> List[SimulationTick]:
        with self._lock:
            return list(self._ticks[-limit:])

    def get_stats(self) -> LivingWorldStats:
        with self._lock:
            total_pop = sum(c.population for c in self._communities.values())
            active = sum(1 for e in self._events.values() if not e.resolved)
            return LivingWorldStats(
                total_regions=len(self._regions),
                total_communities=len(self._communities),
                total_factions=len(self._factions),
                total_relations=len(self._relations),
                total_events=len(self._events),
                active_events=active,
                total_ticks=len(self._ticks),
                current_tick=self._current_tick,
                total_population=total_pop,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "regions": len(self._regions),
                "communities": len(self._communities),
                "factions": len(self._factions),
                "relations": len(self._relations),
                "events": len(self._events),
                "ecosystems": len(self._ecosystems),
                "current_tick": self._current_tick,
            }

    def get_snapshot(self) -> LivingWorldSnapshot:
        with self._lock:
            return LivingWorldSnapshot(
                regions={k: v.to_dict() for k, v in list(self._regions.items())[:50]},
                communities={k: v.to_dict() for k, v in list(self._communities.items())[:50]},
                factions={k: v for k, v in list(self._factions.items())[:50]},
                events={k: v.to_dict() for k, v in list(self._events.items())[:50]},
                ecosystems={k: v.to_dict() for k, v in list(self._ecosystems.items())[:50]},
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._regions.clear()
            self._ecosystems.clear()
            self._communities.clear()
            self._factions.clear()
            self._faction_names.clear()
            self._relations.clear()
            self._events.clear()
            self._ticks.clear()
            self._audit.clear()
            self._current_tick = 0


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_living_world_system() -> LivingWorldSystem:
    """Return the singleton LivingWorldSystem instance."""
    return LivingWorldSystem.get_instance()
