"""
SparkLabs Agent - World Conductor

A singleton orchestration agent that coordinates ALL engine systems into
a unified living world. The World Conductor executes cross-system ticks,
propagates events between systems, detects emergent opportunities, and
provides a single dashboard for world state awareness.

The conductor fuses AI agent reasoning with game engine coordination:
  - Unified tick across all engine subsystems
  - Cross-system event propagation (weather affects photography, cooking, etc.)
  - Emergent opportunity detection (golden hour photography, seasonal recipes)
  - Priority-based system scheduling
  - World state aggregation and health monitoring
  - AI-driven world event generation spanning multiple systems

Architecture:
  WorldConductor (singleton)
    |-- ConductorPriority, SystemHealth, CrossSystemEventKind, OpportunityKind
    |-- SystemRegistration, CrossSystemEvent, WorldOpportunity, ConductorConfig,
       ConductorStats, ConductorSnapshot, ConductorEvent
    |-- get_world_conductor

Core Capabilities:
  - register_system / unregister_system / get_system / list_systems
  - tick_all / tick_system / get_unified_status
  - emit_cross_system_event / subscribe_to_event / list_cross_system_events
  - detect_opportunities / get_opportunities / dismiss_opportunity
  - get_world_dashboard / get_system_health / get_tick_schedule
  - set_priority / get_priority
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_SYSTEMS: int = 200
_MAX_CROSS_SYSTEM_EVENTS: int = 10000
_MAX_OPPORTUNITIES: int = 500
_MAX_SUBSCRIPTIONS: int = 1000
_MAX_EVENTS: int = 10000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


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

class ConductorPriority(str, Enum):
    """Execution priority for system ticks."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class SystemHealth(str, Enum):
    """Health status of a registered system."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"
    OFFLINE = "offline"
    UNREGISTERED = "unregistered"


class CrossSystemEventKind(str, Enum):
    """Types of cross-system events propagated by the conductor."""
    WEATHER_CHANGED = "weather_changed"
    TIME_OF_DAY_CHANGED = "time_of_day_changed"
    SEASON_CHANGED = "season_changed"
    PLAYER_LEVEL_CHANGED = "player_level_changed"
    WORLD_EVENT_TRIGGERED = "world_event_triggered"
    SYSTEM_TICK_COMPLETED = "system_tick_completed"
    OPPORTUNITY_DETECTED = "opportunity_detected"
    SYSTEM_REGISTERED = "system_registered"
    SYSTEM_UNREGISTERED = "system_unregistered"
    SYSTEM_ERROR = "system_error"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


class OpportunityKind(str, Enum):
    """Types of emergent opportunities the conductor detects."""
    PHOTOGRAPHY_GOLDEN_HOUR = "photography_golden_hour"
    PHOTOGRAPHY_NIGHT_SCENE = "photography_night_scene"
    COOKING_SEASONAL = "cooking_seasonal"
    DUNGEON_RESET = "dungeon_reset"
    HOUSING_NEIGHBORHOOD_EVENT = "housing_neighborhood_event"
    PET_BONDING = "pet_bonding"
    WEALTHY_MARKET = "wealthy_market"
    FACTION_EVENT = "faction_event"
    ACHIEVEMENT_MILESTONE = "achievement_milestone"
    GENERAL = "general"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SystemRegistration:
    """Registration record for an engine system."""
    system_id: str
    system_name: str
    system_type: str = ""
    priority: str = ConductorPriority.NORMAL.value
    tick_enabled: bool = True
    tick_interval: float = 1.0
    last_tick: float = 0.0
    last_status: Dict[str, Any] = field(default_factory=dict)
    health: str = SystemHealth.HEALTHY.value
    error_count: int = 0
    tick_count: int = 0
    registered_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CrossSystemEvent:
    """An event propagated across systems."""
    event_id: str
    kind: str
    source_system: str
    target_systems: List[str] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_now)
    propagated: bool = False
    propagation_results: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WorldOpportunity:
    """An emergent opportunity detected across systems."""
    opportunity_id: str
    kind: str
    title: str
    description: str = ""
    source_system: str = ""
    target_systems: List[str] = field(default_factory=list)
    priority: str = ConductorPriority.NORMAL.value
    confidence: float = 0.5
    recommended_actions: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    expires_at: float = 0.0
    dismissed: bool = False
    detected_at: float = field(default_factory=_now)

    @property
    def is_expired(self) -> bool:
        if self.expires_at <= 0:
            return False
        return _now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["is_expired"] = self.is_expired
        return d


@dataclass
class EventSubscription:
    """A subscription to cross-system events."""
    subscription_id: str
    subscriber_system: str
    event_kind: str = ""
    callback_name: str = ""
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ConductorConfig:
    """Global tuning parameters."""
    max_systems: int = 200
    tick_batch_size: int = 10
    tick_timeout_seconds: float = 5.0
    enable_opportunity_detection: bool = True
    enable_cross_system_events: bool = True
    opportunity_check_interval: float = 60.0
    health_check_interval: float = 30.0
    max_error_count_before_offline: int = 5
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ConductorStats:
    """Aggregate statistics."""
    total_systems: int = 0
    total_ticks: int = 0
    total_cross_system_events: int = 0
    total_opportunities: int = 0
    total_propagations: int = 0
    total_errors: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ConductorSnapshot:
    """Full state snapshot."""
    systems: List[Dict[str, Any]] = field(default_factory=list)
    cross_system_events: List[Dict[str, Any]] = field(default_factory=list)
    opportunities: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ConductorEvent:
    """An audit event."""
    event_id: str
    kind: str
    timestamp: float
    system_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# World Conductor
# ---------------------------------------------------------------------------

class WorldConductor:
    """Orchestrates all engine systems into a unified living world."""

    _instance: Optional["WorldConductor"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._systems: Dict[str, SystemRegistration] = {}
        self._system_instances: Dict[str, Any] = {}
        self._cross_system_events: List[CrossSystemEvent] = []
        self._subscriptions: Dict[str, List[EventSubscription]] = {}
        self._opportunities: Dict[str, WorldOpportunity] = {}
        self._events: List[ConductorEvent] = []
        self._stats = ConductorStats()
        self._config = ConductorConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._last_opportunity_check: float = 0.0
        self._last_health_check: float = 0.0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "WorldConductor":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        with self._init_lock:
            if self._initialized:
                return

            # Register core engine systems
            core_systems = [
                ("atmospheric_cycle", "Atmospheric Cycle System", "engine", ConductorPriority.HIGH.value, 1.0),
                ("photography_mode", "Photography Mode System", "engine", ConductorPriority.NORMAL.value, 2.0),
                ("cooking_alchemy", "Cooking & Alchemy System", "engine", ConductorPriority.NORMAL.value, 1.0),
                ("pet_companion", "Pet Companion System", "engine", ConductorPriority.NORMAL.value, 5.0),
                ("dungeon_instance", "Dungeon Instance System", "engine", ConductorPriority.NORMAL.value, 5.0),
                ("player_housing", "Player Housing System", "engine", ConductorPriority.NORMAL.value, 5.0),
                ("living_world", "Living World System", "engine", ConductorPriority.HIGH.value, 2.0),
                ("narrative_director", "Narrative Director", "engine", ConductorPriority.NORMAL.value, 3.0),
                ("economy_simulator", "Economy Simulator", "engine", ConductorPriority.LOW.value, 10.0),
                ("social_platform", "Social Platform", "engine", ConductorPriority.LOW.value, 10.0),
            ]
            for sid, name, stype, priority, interval in core_systems:
                reg = SystemRegistration(
                    system_id=sid, system_name=name, system_type=stype,
                    priority=priority, tick_interval=interval,
                )
                self._systems[sid] = reg

            self._stats.total_systems = len(self._systems)
            self._initialized = True

    def _emit(self, kind: str, **kwargs: Any) -> None:
        self._event_counter += 1
        event = ConductorEvent(
            event_id=f"wcevt_{self._event_counter:08d}",
            kind=kind,
            timestamp=_now(),
            **kwargs,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # System Registration
    # ------------------------------------------------------------------

    def register_system(
        self, system_id: str, system_name: str, system_type: str = "",
        priority: str = ConductorPriority.NORMAL.value,
        tick_enabled: bool = True, tick_interval: float = 1.0,
        system_instance: Any = None,
    ) -> Tuple[bool, str, Optional[SystemRegistration]]:
        if system_id in self._systems:
            return False, "already_exists", None
        reg = SystemRegistration(
            system_id=system_id, system_name=system_name, system_type=system_type,
            priority=priority, tick_enabled=tick_enabled, tick_interval=tick_interval,
        )
        self._systems[system_id] = reg
        if system_instance is not None:
            self._system_instances[system_id] = system_instance
        self._stats.total_systems = len(self._systems)
        self._emit(CrossSystemEventKind.SYSTEM_REGISTERED.value,
                   system_id=system_id,
                   description=f"System registered: {system_name}")
        return True, "registered", reg

    def unregister_system(self, system_id: str) -> Tuple[bool, str]:
        if system_id not in self._systems:
            return False, "not_found"
        del self._systems[system_id]
        if system_id in self._system_instances:
            del self._system_instances[system_id]
        self._stats.total_systems = len(self._systems)
        self._emit(CrossSystemEventKind.SYSTEM_UNREGISTERED.value,
                   system_id=system_id,
                   description=f"System unregistered: {system_id}")
        return True, "removed"

    def get_system(self, system_id: str) -> Optional[SystemRegistration]:
        return self._systems.get(system_id)

    def list_systems(self, system_type: str = "") -> List[SystemRegistration]:
        if system_type:
            return [s for s in self._systems.values() if s.system_type == system_type]
        return list(self._systems.values())

    def set_priority(self, system_id: str, priority: str) -> Tuple[bool, str]:
        reg = self._systems.get(system_id)
        if reg is None:
            return False, "not_found"
        reg.priority = priority
        return True, "updated"

    def get_priority(self, system_id: str) -> Optional[str]:
        reg = self._systems.get(system_id)
        if reg is None:
            return None
        return reg.priority

    # ------------------------------------------------------------------
    # Unified Tick
    # ------------------------------------------------------------------

    def tick_all(self) -> Dict[str, Any]:
        """Execute tick on all registered systems, ordered by priority."""
        self._tick_count += 1
        results: Dict[str, Any] = {}
        priority_order = [
            ConductorPriority.CRITICAL.value,
            ConductorPriority.HIGH.value,
            ConductorPriority.NORMAL.value,
            ConductorPriority.LOW.value,
            ConductorPriority.BACKGROUND.value,
        ]

        for priority in priority_order:
            for sys_id, reg in self._systems.items():
                if reg.priority != priority:
                    continue
                if not reg.tick_enabled:
                    continue
                elapsed = _now() - reg.last_tick
                if elapsed < reg.tick_interval:
                    continue
                result = self._tick_system_internal(sys_id, reg)
                results[sys_id] = result

        self._stats.tick_count = self._tick_count

        # Check for opportunities periodically
        if self._config.enable_opportunity_detection:
            if _now() - self._last_opportunity_check >= self._config.opportunity_check_interval:
                self._detect_opportunities_internal()
                self._last_opportunity_check = _now()

        # Health check periodically
        if _now() - self._last_health_check >= self._config.health_check_interval:
            self._check_health()
            self._last_health_check = _now()

        self._emit(CrossSystemEventKind.TICK.value,
                   description=f"Conductor tick #{self._tick_count}")
        return {
            "tick_count": self._tick_count,
            "systems_ticked": len(results),
            "results": results,
        }

    def tick_system(self, system_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Tick a single system by ID."""
        reg = self._systems.get(system_id)
        if reg is None:
            return False, "not_found", {}
        if not reg.tick_enabled:
            return False, "disabled", {}
        result = self._tick_system_internal(system_id, reg)
        return True, "ticked", result

    def _tick_system_internal(self, system_id: str, reg: SystemRegistration) -> Dict[str, Any]:
        """Execute tick on a system instance if available."""
        result: Dict[str, Any] = {"system_id": system_id, "status": "ok"}
        try:
            instance = self._system_instances.get(system_id)
            if instance is not None and hasattr(instance, "tick"):
                tick_result = instance.tick()
                if isinstance(tick_result, dict):
                    result = tick_result
                result["system_id"] = system_id
                result["status"] = "ok"
            else:
                result["status"] = "no_instance"
            reg.last_tick = _now()
            reg.tick_count += 1
            reg.health = SystemHealth.HEALTHY.value
            reg.error_count = 0
        except Exception as e:
            reg.error_count += 1
            reg.health = SystemHealth.ERROR.value if reg.error_count >= self._config.max_error_count_before_offline else SystemHealth.DEGRADED.value
            if reg.error_count >= self._config.max_error_count_before_offline:
                reg.health = SystemHealth.OFFLINE.value
                reg.tick_enabled = False
            result = {"system_id": system_id, "status": "error", "error": str(e)}
            self._stats.total_errors += 1
            self._emit(CrossSystemEventKind.SYSTEM_ERROR.value,
                       system_id=system_id,
                       description=f"System error: {system_id} - {e}")
        return result

    def _check_health(self) -> None:
        """Check health of all systems."""
        for sys_id, reg in self._systems.items():
            if reg.health == SystemHealth.OFFLINE.value:
                continue
            if reg.error_count > 0 and reg.error_count < self._config.max_error_count_before_offline:
                reg.health = SystemHealth.DEGRADED.value
            elif reg.error_count == 0:
                reg.health = SystemHealth.HEALTHY.value

    # ------------------------------------------------------------------
    # Cross-System Events
    # ------------------------------------------------------------------

    def emit_cross_system_event(
        self, kind: str, source_system: str,
        target_systems: Optional[List[str]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[CrossSystemEvent]]:
        if not self._config.enable_cross_system_events:
            return False, "disabled", None
        event_id = _new_id("cse")
        targets = target_systems or []
        if not targets:
            targets = [sid for sid in self._systems.keys() if sid != source_system]
        event = CrossSystemEvent(
            event_id=event_id,
            kind=kind,
            source_system=source_system,
            target_systems=targets,
            payload=payload or {},
        )
        self._cross_system_events.append(event)
        _evict_fifo_list(self._cross_system_events, _MAX_CROSS_SYSTEM_EVENTS)
        self._stats.total_cross_system_events += 1

        # Propagate to subscribers
        propagated = 0
        for target in targets:
            subs = self._subscriptions.get(f"{target}:{kind}", [])
            subs += self._subscriptions.get(f"{target}:", [])
            if subs:
                event.propagation_results[target] = True
                propagated += 1
            else:
                event.propagation_results[target] = False
        if propagated > 0:
            event.propagated = True
            self._stats.total_propagations += propagated

        self._emit(CrossSystemEventKind.WORLD_EVENT_TRIGGERED.value,
                   system_id=source_system,
                   description=f"Cross-system event: {kind} from {source_system}")
        return True, "emitted", event

    def subscribe_to_event(
        self, subscriber_system: str, event_kind: str = "",
        callback_name: str = "",
    ) -> Tuple[bool, str, Optional[EventSubscription]]:
        sub_id = _new_id("sub")
        sub = EventSubscription(
            subscription_id=sub_id,
            subscriber_system=subscriber_system,
            event_kind=event_kind,
            callback_name=callback_name,
        )
        key = f"{subscriber_system}:{event_kind}" if event_kind else f"{subscriber_system}:"
        self._subscriptions.setdefault(key, []).append(sub)
        return True, "subscribed", sub

    def list_cross_system_events(self, limit: int = 100, kind: str = "") -> List[CrossSystemEvent]:
        events = self._cross_system_events
        if kind:
            events = [e for e in events if e.kind == kind]
        if limit > 0:
            events = events[-limit:]
        return list(events)

    # ------------------------------------------------------------------
    # Opportunity Detection
    # ------------------------------------------------------------------

    def detect_opportunities(self) -> List[WorldOpportunity]:
        """Detect emergent opportunities across systems."""
        if not self._config.enable_opportunity_detection:
            return []
        return self._detect_opportunities_internal()

    def _detect_opportunities_internal(self) -> List[WorldOpportunity]:
        """Internal opportunity detection logic."""
        detected: List[WorldOpportunity] = []

        # Check atmospheric cycle for golden hour
        atmos = self._system_instances.get("atmospheric_cycle")
        if atmos is not None:
            try:
                status = atmos.get_status() if hasattr(atmos, "get_status") else {}
                current_hour = status.get("current_hour", 12.0)
                active_weather = status.get("active_weather", "clear")

                if 5.5 <= current_hour <= 8.0:
                    opp = WorldOpportunity(
                        opportunity_id=_new_id("opp"),
                        kind=OpportunityKind.PHOTOGRAPHY_GOLDEN_HOUR.value,
                        title="Golden Hour Photography",
                        description="Sunrise is happening - perfect time for photography challenges",
                        source_system="atmospheric_cycle",
                        target_systems=["photography_mode"],
                        priority=ConductorPriority.HIGH.value,
                        confidence=0.9,
                        recommended_actions=[
                            "Notify players about golden hour",
                            "Activate photography challenges",
                            "Suggest warm filter presets",
                        ],
                        context={"hour": current_hour, "weather": active_weather},
                        expires_at=_now() + 1800,
                    )
                    self._opportunities[opp.opportunity_id] = opp
                    detected.append(opp)

                if 17.0 <= current_hour <= 19.5:
                    opp = WorldOpportunity(
                        opportunity_id=_new_id("opp"),
                        kind=OpportunityKind.PHOTOGRAPHY_GOLDEN_HOUR.value,
                        title="Sunset Photography",
                        description="Sunset is happening - golden hour photography opportunity",
                        source_system="atmospheric_cycle",
                        target_systems=["photography_mode"],
                        priority=ConductorPriority.HIGH.value,
                        confidence=0.9,
                        recommended_actions=[
                            "Notify players about sunset",
                            "Boost photography challenge rewards",
                        ],
                        context={"hour": current_hour, "weather": active_weather},
                        expires_at=_now() + 1800,
                    )
                    self._opportunities[opp.opportunity_id] = opp
                    detected.append(opp)

                if current_hour >= 21 or current_hour <= 4:
                    opp = WorldOpportunity(
                        opportunity_id=_new_id("opp"),
                        kind=OpportunityKind.PHOTOGRAPHY_NIGHT_SCENE.value,
                        title="Night Photography",
                        description="Night time - ideal for star photography and night scenes",
                        source_system="atmospheric_cycle",
                        target_systems=["photography_mode"],
                        priority=ConductorPriority.NORMAL.value,
                        confidence=0.7,
                        recommended_actions=[
                            "Suggest night camera preset",
                            "Activate Starry Night challenge",
                        ],
                        context={"hour": current_hour, "weather": active_weather},
                        expires_at=_now() + 3600,
                    )
                    self._opportunities[opp.opportunity_id] = opp
                    detected.append(opp)

                if active_weather == "fog":
                    opp = WorldOpportunity(
                        opportunity_id=_new_id("opp"),
                        kind=OpportunityKind.GENERAL.value,
                        title="Misty Atmosphere",
                        description="Foggy weather creates unique photography and exploration opportunities",
                        source_system="atmospheric_cycle",
                        target_systems=["photography_mode", "living_world"],
                        priority=ConductorPriority.NORMAL.value,
                        confidence=0.6,
                        recommended_actions=[
                            "Suggest soft filter for photography",
                            "Increase ambient mystery in narrative",
                        ],
                        context={"weather": active_weather},
                        expires_at=_now() + 3600,
                    )
                    self._opportunities[opp.opportunity_id] = opp
                    detected.append(opp)

            except Exception:
                pass

        # Check cooking/alchemy for seasonal opportunities
        cooking = self._system_instances.get("cooking_alchemy")
        if cooking is not None:
            try:
                opp = WorldOpportunity(
                    opportunity_id=_new_id("opp"),
                    kind=OpportunityKind.COOKING_SEASONAL.value,
                    title="Seasonal Recipe Discovery",
                    description="New seasonal ingredients may be available for cooking",
                    source_system="cooking_alchemy",
                    target_systems=["cooking_alchemy"],
                    priority=ConductorPriority.LOW.value,
                    confidence=0.4,
                    recommended_actions=[
                        "Check for seasonal ingredient spawns",
                        "Offer recipe discovery quests",
                    ],
                    expires_at=_now() + 7200,
                )
                self._opportunities[opp.opportunity_id] = opp
                detected.append(opp)
            except Exception:
                pass

        # Clean up expired opportunities
        expired_ids = [oid for oid, opp in self._opportunities.items() if opp.is_expired]
        for oid in expired_ids:
            del self._opportunities[oid]

        if detected:
            self._stats.total_opportunities += len(detected)
            self._emit(CrossSystemEventKind.OPPORTUNITY_DETECTED.value,
                       description=f"Detected {len(detected)} opportunities")

        return detected

    def get_opportunities(self, active_only: bool = True) -> List[WorldOpportunity]:
        if active_only:
            return [o for o in self._opportunities.values() if not o.dismissed and not o.is_expired]
        return list(self._opportunities.values())

    def dismiss_opportunity(self, opportunity_id: str) -> Tuple[bool, str]:
        opp = self._opportunities.get(opportunity_id)
        if opp is None:
            return False, "not_found"
        opp.dismissed = True
        return True, "dismissed"

    # ------------------------------------------------------------------
    # World Dashboard
    # ------------------------------------------------------------------

    def get_world_dashboard(self) -> Dict[str, Any]:
        """Get a unified dashboard of all world systems."""
        dashboard: Dict[str, Any] = {
            "conductor_tick_count": self._tick_count,
            "total_systems": len(self._systems),
            "healthy_systems": sum(1 for s in self._systems.values() if s.health == SystemHealth.HEALTHY.value),
            "degraded_systems": sum(1 for s in self._systems.values() if s.health == SystemHealth.DEGRADED.value),
            "error_systems": sum(1 for s in self._systems.values() if s.health == SystemHealth.ERROR.value),
            "offline_systems": sum(1 for s in self._systems.values() if s.health == SystemHealth.OFFLINE.value),
            "active_opportunities": len([o for o in self._opportunities.values() if not o.dismissed and not o.is_expired]),
            "cross_system_events": len(self._cross_system_events),
            "systems": {},
        }

        for sys_id, reg in self._systems.items():
            instance = self._system_instances.get(sys_id)
            sys_status: Dict[str, Any] = {
                "name": reg.system_name,
                "type": reg.system_type,
                "priority": reg.priority,
                "health": reg.health,
                "tick_count": reg.tick_count,
                "error_count": reg.error_count,
                "last_tick": reg.last_tick,
            }
            if instance is not None and hasattr(instance, "get_status"):
                try:
                    sys_status["system_status"] = instance.get_status()
                except Exception:
                    sys_status["system_status"] = {"error": "status_unavailable"}
            dashboard["systems"][sys_id] = sys_status

        return dashboard

    def get_system_health(self, system_id: str = "") -> Dict[str, Any]:
        if system_id:
            reg = self._systems.get(system_id)
            if reg is None:
                return {"health": SystemHealth.UNREGISTERED.value}
            return {
                "system_id": system_id,
                "name": reg.system_name,
                "health": reg.health,
                "error_count": reg.error_count,
                "tick_count": reg.tick_count,
                "last_tick": reg.last_tick,
                "tick_enabled": reg.tick_enabled,
            }
        return {
            sid: {
                "name": reg.system_name,
                "health": reg.health,
                "error_count": reg.error_count,
            }
            for sid, reg in self._systems.items()
        }

    def get_tick_schedule(self) -> List[Dict[str, Any]]:
        """Get the scheduled tick order for all systems."""
        priority_order = [
            ConductorPriority.CRITICAL.value,
            ConductorPriority.HIGH.value,
            ConductorPriority.NORMAL.value,
            ConductorPriority.LOW.value,
            ConductorPriority.BACKGROUND.value,
        ]
        schedule: List[Dict[str, Any]] = []
        for priority in priority_order:
            for sys_id, reg in self._systems.items():
                if reg.priority == priority:
                    schedule.append({
                        "system_id": sys_id,
                        "name": reg.system_name,
                        "priority": priority,
                        "tick_interval": reg.tick_interval,
                        "tick_enabled": reg.tick_enabled,
                        "next_tick_in": max(0, reg.tick_interval - (_now() - reg.last_tick)) if reg.last_tick > 0 else 0,
                    })
        return schedule

    def get_unified_status(self) -> Dict[str, Any]:
        """Get unified status from all connected systems."""
        status: Dict[str, Any] = {
            "conductor": self.get_status(),
            "systems": {},
        }
        for sys_id, instance in self._system_instances.items():
            if hasattr(instance, "get_status"):
                try:
                    status["systems"][sys_id] = instance.get_status()
                except Exception:
                    status["systems"][sys_id] = {"error": "unavailable"}
        return status

    # ------------------------------------------------------------------
    # Tick / Config / Status
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        return self.tick_all()

    def set_config(self, config: Dict[str, Any]) -> Tuple[bool, str, ConductorConfig]:
        if not isinstance(config, dict):
            return False, "invalid_config", self._config
        for key, value in config.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        self._emit(CrossSystemEventKind.CONFIG_UPDATED.value,
                   description="Config updated")
        return True, "updated", self._config

    def get_config(self) -> ConductorConfig:
        return self._config

    def list_events(self, limit: int = 100, kind: str = "") -> List[ConductorEvent]:
        events = self._events if not kind else [e for e in self._events if e.kind == kind]
        if limit > 0:
            events = events[-limit:]
        return list(events)

    def get_stats(self) -> ConductorStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_systems": len(self._systems),
            "total_instances": len(self._system_instances),
            "healthy_systems": sum(1 for s in self._systems.values() if s.health == SystemHealth.HEALTHY.value),
            "degraded_systems": sum(1 for s in self._systems.values() if s.health == SystemHealth.DEGRADED.value),
            "error_systems": sum(1 for s in self._systems.values() if s.health == SystemHealth.ERROR.value),
            "offline_systems": sum(1 for s in self._systems.values() if s.health == SystemHealth.OFFLINE.value),
            "active_opportunities": len([o for o in self._opportunities.values() if not o.dismissed and not o.is_expired]),
            "total_cross_system_events": len(self._cross_system_events),
            "total_errors": self._stats.total_errors,
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> ConductorSnapshot:
        return ConductorSnapshot(
            systems=[s.to_dict() for s in self._systems.values()],
            cross_system_events=[e.to_dict() for e in self._cross_system_events[-50:]],
            opportunities=[o.to_dict() for o in self._opportunities.values()],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> Tuple[bool, str]:
        with self._init_lock:
            self._systems.clear()
            self._system_instances.clear()
            self._cross_system_events.clear()
            self._subscriptions.clear()
            self._opportunities.clear()
            self._events.clear()
            self._stats = ConductorStats()
            self._config = ConductorConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._last_opportunity_check = 0.0
            self._last_health_check = 0.0
            self._initialized = False
            self._seed()
            self._emit(CrossSystemEventKind.RESET.value,
                       description="Conductor reset")
        return True, "reset"


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

def get_world_conductor() -> WorldConductor:
    return WorldConductor.get_instance()
