"""
SparkLabs Agent - AI Spawn Director

An AI spawn director for the SparkLabs AI-native game engine. It manages
enemy and NPC spawning in real-time by selecting spawn points based on
player proximity, line-of-sight avoidance, and spawn budget; composing
waves with enemy mixes and timing; and scaling difficulty based on
player performance. Unlike scripted spawn tables, this agent makes
continuous spawn decisions that fuse AI judgment with engine entity
lifecycle, producing emergent combat encounters that adapt to player
skill and pacing.

Architecture:
  SpawnDirector (singleton)
    |-- SpawnPoint, SpawnWave, SpawnGroup, SpawnBudget,
       SpawnDirectorStats, SpawnDirectorSnapshot, SpawnDirectorEvent
    |-- SpawnKind, SpawnPriority, SpawnEventKind

Core Capabilities:
  - register_spawn_point / get_spawn_point / list_spawn_points /
    remove_spawn_point: spawn point lifecycle with position, capacity,
    cooldown, and team.
  - register_wave / get_wave / list_waves / remove_wave: wave definitions
    with enemy groups, timing, and trigger conditions.
  - register_group / get_group / list_groups / remove_group: enemy group
    templates with member composition and budget cost.
  - set_budget / get_budget: spawn budget management (concurrent entity
    cap, cost per spawn).
  - select_spawn_point: AI-driven spawn point selection based on player
    position, distance preference, and availability.
  - evaluate_wave: check if a wave's trigger conditions are met.
  - trigger_wave: activate a wave, spawning its groups over time.
  - tick: advance the spawn simulation, processing active waves and
    cooldowns.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`SpawnDirector.get_instance` or the module-level
:func:`get_spawn_director` factory.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_SPAWN_POINTS: int = 2000
_MAX_WAVES: int = 500
_MAX_GROUPS: int = 500
_MAX_EVENTS: int = 5000
_MAX_ACTIVE_WAVES: int = 50


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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


def _vec_distance(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


# Distance scoring weights for spawn point selection
_DISTANCE_WEIGHT: float = 0.4
_COOLDOWN_WEIGHT: float = 0.3
_CAPACITY_WEIGHT: float = 0.3

# Ideal spawn distance range
_IDEAL_MIN_DISTANCE: float = 20.0
_IDEAL_MAX_DISTANCE: float = 80.0


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class SpawnKind(Enum):
    """Functional kinds of spawn encounters."""
    WAVE = "wave"
    PATROL = "patrol"
    AMBUSH = "ambush"
    BOSS = "boss"
    ESCORT = "escort"
    SURVIVAL = "survival"


class SpawnPriority(Enum):
    """Priority levels for spawn scheduling."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class SpawnEventKind(Enum):
    """Audit event types emitted by the spawn director."""
    SPAWN_POINT_REGISTERED = "spawn_point_registered"
    SPAWN_POINT_REMOVED = "spawn_point_removed"
    WAVE_REGISTERED = "wave_registered"
    WAVE_REMOVED = "wave_removed"
    GROUP_REGISTERED = "group_registered"
    GROUP_REMOVED = "group_removed"
    BUDGET_SET = "budget_set"
    SPAWN_POINT_SELECTED = "spawn_point_selected"
    WAVE_TRIGGERED = "wave_triggered"
    WAVE_COMPLETED = "wave_completed"
    ENTITY_SPAWNED = "entity_spawned"
    TICK_COMPLETED = "tick_completed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SpawnPoint:
    """A named spawn point in 3D space."""
    point_id: str = ""
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    team_id: str = ""
    capacity: int = 5
    current_count: int = 0
    cooldown_seconds: float = 5.0
    last_spawn_time: float = 0.0
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SpawnGroup:
    """A template for a group of enemies to spawn together."""
    group_id: str = ""
    name: str = ""
    enemy_type: str = ""
    count: int = 3
    formation: str = "cluster"
    budget_cost: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SpawnWave:
    """A wave definition with groups, timing, and trigger conditions."""
    wave_id: str = ""
    name: str = ""
    kind: str = SpawnKind.WAVE.value
    group_ids: List[str] = field(default_factory=list)
    delay_between_groups: float = 2.0
    trigger_distance: float = 50.0
    trigger_health_pct: float = 0.0
    priority: str = SpawnPriority.NORMAL.value
    max_concurrent: int = 10
    active: bool = True
    triggered: bool = False
    completed: bool = False
    groups_spawned: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SpawnBudget:
    """Spawn budget controlling concurrent entity limits."""
    max_concurrent: int = 20
    current_count: int = 0
    cost_per_spawn: int = 1
    refill_rate: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SpawnDirectorStats:
    """Aggregate statistics for the spawn director."""
    total_spawn_points: int = 0
    total_waves: int = 0
    total_groups: int = 0
    total_waves_triggered: int = 0
    total_waves_completed: int = 0
    total_entities_spawned: int = 0
    total_ticks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SpawnDirectorSnapshot:
    """Point-in-time snapshot of spawn director state."""
    total_spawn_points: int = 0
    total_waves: int = 0
    active_waves: int = 0
    current_budget: int = 0
    simulation_time: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SpawnDirectorEvent:
    """An audit event emitted by the spawn director."""
    event_id: str = ""
    kind: str = SpawnEventKind.SPAWN_POINT_REGISTERED.value
    timestamp: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Spawn Director Singleton
# ---------------------------------------------------------------------------


class SpawnDirector:
    """AI spawn director that manages real-time enemy spawning.

    Implements the singleton pattern with double-checked locking.
    """

    _instance: Optional["SpawnDirector"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._spawn_points: Dict[str, SpawnPoint] = {}
        self._waves: Dict[str, SpawnWave] = {}
        self._groups: Dict[str, SpawnGroup] = {}
        self._budget = SpawnBudget()
        self._events: List[SpawnDirectorEvent] = []
        self._simulation_time: float = 0.0
        self._stats = SpawnDirectorStats()
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "SpawnDirector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed initial spawn points, groups, and waves."""
        # Spawn points
        seeded_points = [
            SpawnPoint(
                point_id="spt_north_gate",
                name="North Gate",
                position=(0.0, 0.0, 50.0),
                team_id="enemy",
                capacity=8,
                current_count=0,
                cooldown_seconds=3.0,
                last_spawn_time=0.0,
                active=True,
            ),
            SpawnPoint(
                point_id="spt_south_gate",
                name="South Gate",
                position=(0.0, 0.0, -50.0),
                team_id="enemy",
                capacity=8,
                current_count=0,
                cooldown_seconds=3.0,
                last_spawn_time=0.0,
                active=True,
            ),
            SpawnPoint(
                point_id="spt_east_ambush",
                name="East Ambush",
                position=(40.0, 0.0, 0.0),
                team_id="enemy",
                capacity=4,
                current_count=0,
                cooldown_seconds=5.0,
                last_spawn_time=0.0,
                active=True,
            ),
            SpawnPoint(
                point_id="spt_west_ambush",
                name="West Ambush",
                position=(-40.0, 0.0, 0.0),
                team_id="enemy",
                capacity=4,
                current_count=0,
                cooldown_seconds=5.0,
                last_spawn_time=0.0,
                active=True,
            ),
            SpawnPoint(
                point_id="spt_boss_arena",
                name="Boss Arena Center",
                position=(0.0, 0.0, 0.0),
                team_id="boss",
                capacity=1,
                current_count=0,
                cooldown_seconds=30.0,
                last_spawn_time=0.0,
                active=True,
            ),
        ]
        for sp in seeded_points:
            self._spawn_points[sp.point_id] = sp

        # Groups
        seeded_groups = [
            SpawnGroup(
                group_id="grp_grunt_squad",
                name="Grunt Squad",
                enemy_type="grunt",
                count=4,
                formation="cluster",
                budget_cost=4,
            ),
            SpawnGroup(
                group_id="grp_archer_pair",
                name="Archer Pair",
                enemy_type="archer",
                count=2,
                formation="line",
                budget_cost=3,
            ),
            SpawnGroup(
                group_id="grp_heavy_brute",
                name="Heavy Brute",
                enemy_type="brute",
                count=1,
                formation="single",
                budget_cost=5,
            ),
            SpawnGroup(
                group_id="grp_swarm",
                name="Swarm",
                enemy_type="crawler",
                count=8,
                formation="spread",
                budget_cost=4,
            ),
            SpawnGroup(
                group_id="grp_boss",
                name="Boss",
                enemy_type="boss_titan",
                count=1,
                formation="single",
                budget_cost=10,
            ),
        ]
        for g in seeded_groups:
            self._groups[g.group_id] = g

        # Waves
        seeded_waves = [
            SpawnWave(
                wave_id="wv_intro_wave",
                name="Intro Wave",
                kind=SpawnKind.WAVE.value,
                group_ids=["grp_grunt_squad", "grp_archer_pair"],
                delay_between_groups=2.0,
                trigger_distance=40.0,
                trigger_health_pct=0.0,
                priority=SpawnPriority.NORMAL.value,
                max_concurrent=8,
                active=True,
            ),
            SpawnWave(
                wave_id="wv_ambush_east",
                name="East Ambush",
                kind=SpawnKind.AMBUSH.value,
                group_ids=["grp_swarm"],
                delay_between_groups=0.5,
                trigger_distance=35.0,
                trigger_health_pct=0.0,
                priority=SpawnPriority.HIGH.value,
                max_concurrent=10,
                active=True,
            ),
            SpawnWave(
                wave_id="wv_boss_encounter",
                name="Boss Encounter",
                kind=SpawnKind.BOSS.value,
                group_ids=["grp_boss", "grp_grunt_squad"],
                delay_between_groups=5.0,
                trigger_distance=20.0,
                trigger_health_pct=0.5,
                priority=SpawnPriority.CRITICAL.value,
                max_concurrent=5,
                active=True,
            ),
        ]
        for w in seeded_waves:
            self._waves[w.wave_id] = w

        self._budget = SpawnBudget(
            max_concurrent=20,
            current_count=0,
            cost_per_spawn=1,
            refill_rate=1.0,
        )
        self._stats.total_spawn_points = len(self._spawn_points)
        self._stats.total_waves = len(self._waves)
        self._stats.total_groups = len(self._groups)
        self._initialized = True

    def _emit(self, kind: str, payload: Dict[str, Any]) -> None:
        event = SpawnDirectorEvent(
            event_id=_new_id("sde"),
            kind=kind,
            timestamp=_now(),
            payload=payload,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Spawn Point Lifecycle
    # ------------------------------------------------------------------

    def register_spawn_point(self, point: SpawnPoint) -> SpawnPoint:
        if not point.point_id:
            point.point_id = _new_id("spt")
        if not point.name:
            point.name = point.point_id
        self._spawn_points[point.point_id] = point
        _evict_fifo_dict(self._spawn_points, _MAX_SPAWN_POINTS)
        self._stats.total_spawn_points = len(self._spawn_points)
        self._emit(
            SpawnEventKind.SPAWN_POINT_REGISTERED.value,
            {"point_id": point.point_id},
        )
        return point

    def get_spawn_point(self, point_id: str) -> Optional[SpawnPoint]:
        return self._spawn_points.get(point_id)

    def list_spawn_points(
        self,
        team_id: str = "",
        active_only: bool = False,
        limit: int = 100,
    ) -> List[SpawnPoint]:
        results: List[SpawnPoint] = []
        for sp in self._spawn_points.values():
            if team_id and sp.team_id != team_id:
                continue
            if active_only and not sp.active:
                continue
            results.append(sp)
        return results[:max(0, int(limit))]

    def remove_spawn_point(self, point_id: str) -> bool:
        existed = self._spawn_points.pop(point_id, None) is not None
        if existed:
            self._stats.total_spawn_points = len(self._spawn_points)
            self._emit(
                SpawnEventKind.SPAWN_POINT_REMOVED.value,
                {"point_id": point_id},
            )
        return existed

    # ------------------------------------------------------------------
    # Group Lifecycle
    # ------------------------------------------------------------------

    def register_group(self, group: SpawnGroup) -> SpawnGroup:
        if not group.group_id:
            group.group_id = _new_id("grp")
        if not group.name:
            group.name = group.group_id
        self._groups[group.group_id] = group
        _evict_fifo_dict(self._groups, _MAX_GROUPS)
        self._stats.total_groups = len(self._groups)
        self._emit(
            SpawnEventKind.GROUP_REGISTERED.value,
            {"group_id": group.group_id},
        )
        return group

    def get_group(self, group_id: str) -> Optional[SpawnGroup]:
        return self._groups.get(group_id)

    def list_groups(self, limit: int = 100) -> List[SpawnGroup]:
        results = list(self._groups.values())
        return results[:max(0, int(limit))]

    def remove_group(self, group_id: str) -> bool:
        existed = self._groups.pop(group_id, None) is not None
        if existed:
            self._stats.total_groups = len(self._groups)
            self._emit(
                SpawnEventKind.GROUP_REMOVED.value,
                {"group_id": group_id},
            )
        return existed

    # ------------------------------------------------------------------
    # Wave Lifecycle
    # ------------------------------------------------------------------

    def register_wave(self, wave: SpawnWave) -> SpawnWave:
        if not wave.wave_id:
            wave.wave_id = _new_id("wv")
        if not wave.name:
            wave.name = wave.wave_id
        if wave.kind not in [k.value for k in SpawnKind]:
            wave.kind = SpawnKind.WAVE.value
        if wave.priority not in [k.value for k in SpawnPriority]:
            wave.priority = SpawnPriority.NORMAL.value
        self._waves[wave.wave_id] = wave
        _evict_fifo_dict(self._waves, _MAX_WAVES)
        self._stats.total_waves = len(self._waves)
        self._emit(
            SpawnEventKind.WAVE_REGISTERED.value,
            {"wave_id": wave.wave_id, "kind": wave.kind},
        )
        return wave

    def get_wave(self, wave_id: str) -> Optional[SpawnWave]:
        return self._waves.get(wave_id)

    def list_waves(
        self,
        kind: str = "",
        active_only: bool = False,
        limit: int = 100,
    ) -> List[SpawnWave]:
        results: List[SpawnWave] = []
        for w in self._waves.values():
            if kind and w.kind != kind:
                continue
            if active_only and not w.active:
                continue
            results.append(w)
        return results[:max(0, int(limit))]

    def remove_wave(self, wave_id: str) -> bool:
        existed = self._waves.pop(wave_id, None) is not None
        if existed:
            self._stats.total_waves = len(self._waves)
            self._emit(
                SpawnEventKind.WAVE_REMOVED.value,
                {"wave_id": wave_id},
            )
        return existed

    # ------------------------------------------------------------------
    # Budget Management
    # ------------------------------------------------------------------

    def set_budget(self, budget: SpawnBudget) -> SpawnBudget:
        self._budget = budget
        self._emit(
            SpawnEventKind.BUDGET_SET.value,
            {"max_concurrent": budget.max_concurrent, "cost_per_spawn": budget.cost_per_spawn},
        )
        return self._budget

    def get_budget(self) -> SpawnBudget:
        return self._budget

    # ------------------------------------------------------------------
    # AI-Driven Spawn Point Selection
    # ------------------------------------------------------------------

    def select_spawn_point(
        self,
        player_position: Tuple[float, float, float],
        team_id: str = "enemy",
        max_distance: float = 200.0,
    ) -> Dict[str, Any]:
        """Select the best spawn point for spawning enemies near the player."""
        pp = tuple(player_position) if isinstance(player_position, list) else player_position
        best_point: Optional[SpawnPoint] = None
        best_score: float = -1.0
        for sp in self._spawn_points.values():
            if not sp.active:
                continue
            if team_id and sp.team_id != team_id:
                continue
            if sp.current_count >= sp.capacity:
                continue
            dist = _vec_distance(pp, sp.position)
            if dist > max_distance:
                continue
            cooldown_remaining = max(0.0, sp.cooldown_seconds - (self._simulation_time - sp.last_spawn_time))
            cooldown_factor = 1.0 - _clamp(cooldown_remaining / sp.cooldown_seconds) if sp.cooldown_seconds > 0 else 1.0
            if cooldown_remaining > 0:
                continue
            # Distance score: prefer points in the ideal range
            if dist < _IDEAL_MIN_DISTANCE:
                dist_score = dist / _IDEAL_MIN_DISTANCE * 0.5
            elif dist > _IDEAL_MAX_DISTANCE:
                dist_score = max(0.0, 1.0 - (dist - _IDEAL_MAX_DISTANCE) / max_distance)
            else:
                dist_score = 1.0
            capacity_factor = 1.0 - (sp.current_count / max(1, sp.capacity))
            score = (
                dist_score * _DISTANCE_WEIGHT
                + cooldown_factor * _COOLDOWN_WEIGHT
                + capacity_factor * _CAPACITY_WEIGHT
            )
            if score > best_score:
                best_score = score
                best_point = sp
        if best_point is None:
            self._emit(
                SpawnEventKind.SPAWN_POINT_SELECTED.value,
                {"found": False, "player_position": list(pp)},
            )
            return {
                "found": False,
                "point_id": "",
                "position": [0.0, 0.0, 0.0],
                "score": 0.0,
            }
        self._emit(
            SpawnEventKind.SPAWN_POINT_SELECTED.value,
            {
                "found": True,
                "point_id": best_point.point_id,
                "score": best_score,
                "distance": _vec_distance(pp, best_point.position),
            },
        )
        return {
            "found": True,
            "point_id": best_point.point_id,
            "name": best_point.name,
            "position": list(best_point.position),
            "team_id": best_point.team_id,
            "score": best_score,
            "current_count": best_point.current_count,
            "capacity": best_point.capacity,
        }

    # ------------------------------------------------------------------
    # Wave Evaluation and Triggering
    # ------------------------------------------------------------------

    def evaluate_wave(
        self,
        wave_id: str,
        player_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        player_health_pct: float = 1.0,
    ) -> Dict[str, Any]:
        """Check if a wave's trigger conditions are met."""
        wave = self._waves.get(wave_id)
        if wave is None:
            return {"found": False, "wave_id": wave_id, "ready": False}
        if wave.triggered or wave.completed or not wave.active:
            return {
                "found": True,
                "wave_id": wave_id,
                "ready": False,
                "reason": "already_triggered" if wave.triggered else ("completed" if wave.completed else "inactive"),
            }
        pp = tuple(player_position) if isinstance(player_position, list) else player_position
        # Find nearest spawn point to check distance
        min_dist = float("inf")
        for sp in self._spawn_points.values():
            if not sp.active:
                continue
            if sp.team_id != "enemy" and sp.team_id != "boss":
                continue
            dist = _vec_distance(pp, sp.position)
            if dist < min_dist:
                min_dist = dist
        distance_ready = min_dist <= wave.trigger_distance
        health_ready = player_health_pct <= wave.trigger_health_pct if wave.trigger_health_pct > 0 else True
        ready = distance_ready and health_ready
        return {
            "found": True,
            "wave_id": wave_id,
            "ready": ready,
            "distance_to_nearest": min_dist,
            "trigger_distance": wave.trigger_distance,
            "distance_ready": distance_ready,
            "health_ready": health_ready,
            "player_health_pct": player_health_pct,
        }

    def trigger_wave(self, wave_id: str) -> Dict[str, Any]:
        """Trigger a wave, marking it as active and spawning its first group."""
        wave = self._waves.get(wave_id)
        if wave is None:
            return {"found": False, "wave_id": wave_id, "triggered": False}
        if wave.triggered:
            return {"found": True, "wave_id": wave_id, "triggered": False, "reason": "already_triggered"}
        wave.triggered = True
        wave.groups_spawned = 0
        self._stats.total_waves_triggered += 1
        # Spawn the first group immediately
        spawned = 0
        if wave.group_ids:
            first_group_id = wave.group_ids[0]
            group = self._groups.get(first_group_id)
            if group:
                spawned = group.count
                wave.groups_spawned = 1
                self._stats.total_entities_spawned += spawned
                self._budget.current_count += group.budget_cost
        self._emit(
            SpawnEventKind.WAVE_TRIGGERED.value,
            {"wave_id": wave_id, "spawned": spawned},
        )
        return {
            "found": True,
            "wave_id": wave_id,
            "triggered": True,
            "spawned": spawned,
            "groups_total": len(wave.group_ids),
            "groups_spawned": wave.groups_spawned,
        }

    # ------------------------------------------------------------------
    # Simulation Tick
    # ------------------------------------------------------------------

    def tick(self, dt: float) -> Dict[str, Any]:
        """Advance the spawn simulation by dt seconds."""
        dt = _safe_float(dt, 0.016)
        self._simulation_time += dt
        self._stats.total_ticks += 1
        # Refill budget
        if self._budget.current_count > 0:
            refill = self._budget.refill_rate * dt
            self._budget.current_count = max(0, int(self._budget.current_count - refill))
        # Check triggered waves for completion
        waves_completed_this_tick = 0
        for wave in self._waves.values():
            if not wave.triggered or wave.completed:
                continue
            # Spawn next group if delay has passed
            if wave.groups_spawned < len(wave.group_ids):
                # In a real engine, we'd track per-group timing
                # For simulation, spawn one group per tick if budget allows
                next_group_id = wave.group_ids[wave.groups_spawned]
                group = self._groups.get(next_group_id)
                if group and self._budget.current_count + group.budget_cost <= self._budget.max_concurrent:
                    wave.groups_spawned += 1
                    self._stats.total_entities_spawned += group.count
                    self._budget.current_count += group.budget_cost
                    self._emit(
                        SpawnEventKind.ENTITY_SPAWNED.value,
                        {"wave_id": wave.wave_id, "group_id": next_group_id, "count": group.count},
                    )
            # Mark wave as completed when all groups are spawned
            if wave.groups_spawned >= len(wave.group_ids) and not wave.completed:
                wave.completed = True
                waves_completed_this_tick += 1
                self._stats.total_waves_completed += 1
                self._emit(
                    SpawnEventKind.WAVE_COMPLETED.value,
                    {"wave_id": wave.wave_id},
                )
        self._emit(
            SpawnEventKind.TICK_COMPLETED.value,
            {
                "dt": dt,
                "simulation_time": self._simulation_time,
                "waves_completed": waves_completed_this_tick,
            },
        )
        return {
            "simulation_time": self._simulation_time,
            "dt": dt,
            "budget_current": self._budget.current_count,
            "budget_max": self._budget.max_concurrent,
            "waves_completed": waves_completed_this_tick,
        }

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, kind: str = "", limit: int = 50) -> List[SpawnDirectorEvent]:
        results: List[SpawnDirectorEvent] = []
        for e in reversed(self._events):
            if kind and e.kind != kind:
                continue
            results.append(e)
            if len(results) >= max(1, int(limit)):
                break
        return results

    def get_stats(self) -> SpawnDirectorStats:
        self._stats.total_spawn_points = len(self._spawn_points)
        self._stats.total_waves = len(self._waves)
        self._stats.total_groups = len(self._groups)
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        active_waves = len([w for w in self._waves.values() if w.triggered and not w.completed])
        return {
            "initialized": self._initialized,
            "spawn_points": len(self._spawn_points),
            "waves": len(self._waves),
            "groups": len(self._groups),
            "active_waves": active_waves,
            "budget_current": self._budget.current_count,
            "budget_max": self._budget.max_concurrent,
            "simulation_time": self._simulation_time,
            "events": len(self._events),
        }

    def get_snapshot(self) -> SpawnDirectorSnapshot:
        active_waves = len([w for w in self._waves.values() if w.triggered and not w.completed])
        return SpawnDirectorSnapshot(
            total_spawn_points=len(self._spawn_points),
            total_waves=len(self._waves),
            active_waves=active_waves,
            current_budget=self._budget.current_count,
            simulation_time=self._simulation_time,
            timestamp=_now(),
        )

    def reset(self) -> None:
        with self._init_lock:
            self._spawn_points.clear()
            self._waves.clear()
            self._groups.clear()
            self._events.clear()
            self._simulation_time = 0.0
            self._stats = SpawnDirectorStats()
            self._seed()


# ---------------------------------------------------------------------------
# Module-level Factory
# ---------------------------------------------------------------------------


def get_spawn_director() -> SpawnDirector:
    """Return the singleton SpawnDirector instance."""
    return SpawnDirector.get_instance()
