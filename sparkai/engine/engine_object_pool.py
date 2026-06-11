"""
SparkLabs Engine - Intelligent Object Pool

Predictive game object pool system with automatic sizing, memory
optimization, and usage-based demand forecasting. Inspired by Phaser's
Group system and Godot's node pooling, this module provides a central
object lifecycle manager that minimizes garbage collection pressure by
recycling frequently-used game objects.

Architecture:
  EngineObjectPool (singleton orchestrator)
    |-- PoolConfig (per-pool sizing & strategy configuration)
    |-- PooledObject (tracked lifecycle state for each pooled instance)
    |-- PoolStats (runtime telemetry & utilization metrics)
    |-- DemandPredictor (exponential smoothing forecast engine)
    |-- AllocationEngine (policy-driven borrow/return dispatch)

Features:
  - Six pool strategies: FIXED_SIZE, DYNAMIC_GROWTH, PREDICTIVE,
    ADAPTIVE, LAZY, EAGER
  - Five warmup modes: NONE, INCREMENTAL, BATCH, BACKGROUND, PROACTIVE
  - Five allocation policies: ROUND_ROBIN, LEAST_USED, MOST_READY,
    PRIORITY_BASED, RANDOM
  - Predictive demand smoothing with configurable time windows
  - Automatic pool resizing based on historical usage patterns
  - Thread-safe borrow/return with reentrant locking
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PoolStrategy(str, Enum):
    """Growth and sizing strategy for an object pool."""
    FIXED_SIZE = "fixed_size"
    DYNAMIC_GROWTH = "dynamic_growth"
    PREDICTIVE = "predictive"
    ADAPTIVE = "adaptive"
    LAZY = "lazy"
    EAGER = "eager"


class ObjectState(str, Enum):
    """Lifecycle state of a pooled object."""
    AVAILABLE = "available"
    IN_USE = "in_use"
    RESERVED = "reserved"
    RECYCLING = "recycling"
    DISABLED = "disabled"
    WARMING = "warming"


class AllocationPolicy(str, Enum):
    """Determines which available object to hand out on borrow."""
    ROUND_ROBIN = "round_robin"
    LEAST_USED = "least_used"
    MOST_READY = "most_ready"
    PRIORITY_BASED = "priority_based"
    RANDOM = "random"


class WarmupMode(str, Enum):
    """Controls how a pool pre-allocates objects on startup."""
    NONE = "none"
    INCREMENTAL = "incremental"
    BATCH = "batch"
    BACKGROUND = "background"
    PROACTIVE = "proactive"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class PooledObject:
    """Represents a single tracked object within a pool."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pool_id: str = ""
    object_type: str = "generic"
    state: ObjectState = ObjectState.AVAILABLE
    data: Dict[str, Any] = field(default_factory=dict)
    last_used: float = field(default_factory=_time_module.time)
    borrow_count: int = 0
    creation_time: float = field(default_factory=_time_module.time)
    recycle_count: int = 0
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pool_id": self.pool_id,
            "object_type": self.object_type,
            "state": self.state.value,
            "data": self.data,
            "last_used": self.last_used,
            "borrow_count": self.borrow_count,
            "creation_time": self.creation_time,
            "recycle_count": self.recycle_count,
            "priority": self.priority,
        }


@dataclass
class PoolConfig:
    """Configuration and runtime sizing parameters for a pool."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pool_name: str = "default_pool"
    strategy: PoolStrategy = PoolStrategy.DYNAMIC_GROWTH
    initial_size: int = 16
    max_size: int = 1024
    growth_factor: float = 1.5
    warmup_mode: WarmupMode = WarmupMode.INCREMENTAL
    allocation_policy: AllocationPolicy = AllocationPolicy.ROUND_ROBIN
    object_factory: str = "default_factory"
    reset_on_recycle: bool = True
    stats_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pool_name": self.pool_name,
            "strategy": self.strategy.value,
            "initial_size": self.initial_size,
            "max_size": self.max_size,
            "growth_factor": self.growth_factor,
            "warmup_mode": self.warmup_mode.value,
            "allocation_policy": self.allocation_policy.value,
            "object_factory": self.object_factory,
            "reset_on_recycle": self.reset_on_recycle,
            "stats_enabled": self.stats_enabled,
        }


@dataclass
class PoolStats:
    """Runtime telemetry snapshot for a single pool."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pool_id: str = ""
    total_objects: int = 0
    available: int = 0
    in_use: int = 0
    reserved: int = 0
    peak_usage: int = 0
    total_borrows: int = 0
    total_returns: int = 0
    miss_count: int = 0
    avg_borrow_time_us: float = 0.0
    recycle_rate: float = 0.0
    memory_estimate_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pool_id": self.pool_id,
            "total_objects": self.total_objects,
            "available": self.available,
            "in_use": self.in_use,
            "reserved": self.reserved,
            "peak_usage": self.peak_usage,
            "total_borrows": self.total_borrows,
            "total_returns": self.total_returns,
            "miss_count": self.miss_count,
            "avg_borrow_time_us": self.avg_borrow_time_us,
            "recycle_rate": self.recycle_rate,
            "memory_estimate_bytes": self.memory_estimate_bytes,
        }


# ---------------------------------------------------------------------------
# Demand Predictor — internal helper
# ---------------------------------------------------------------------------

class _DemandPredictor:
    """
    Simple exponential smoothing forecaster for pool usage demand.

    Maintains a rolling window of borrow counts and uses exponential
    smoothing to predict short-term future demand.
    """

    DEFAULT_ALPHA = 0.3    # smoothing factor (0 = pure history, 1 = pure latest)
    MAX_SAMPLES = 120       # keep up to 2 minutes of per-second samples

    def __init__(self) -> None:
        self._history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.MAX_SAMPLES)
        )
        self._smoothed: Dict[str, float] = {}
        self._last_predictions: Dict[str, float] = {}

    def record_borrow(self, pool_id: str, timestamp: float) -> None:
        """Record a borrow event at the given timestamp."""
        self._history[pool_id].append(timestamp)

    def predict(self, pool_id: str, time_window_seconds: float) -> int:
        """
        Predict the number of borrows expected in the next
        *time_window_seconds* using exponential smoothing over
        historical borrow rates.
        """
        history = self._history.get(pool_id)
        if not history or len(history) < 2:
            self._last_predictions[pool_id] = 0.0
            return 0

        now = _time_module.time()
        cutoff = now - time_window_seconds
        recent = [t for t in history if t >= cutoff]
        rate = len(recent) / max(time_window_seconds, 0.001)

        previous_smoothed = self._smoothed.get(pool_id, rate)
        smoothed = self.DEFAULT_ALPHA * rate + (1.0 - self.DEFAULT_ALPHA) * previous_smoothed
        self._smoothed[pool_id] = smoothed

        prediction = max(1, int(smoothed * time_window_seconds))
        self._last_predictions[pool_id] = float(prediction)
        return prediction

    def get_smoothed_rate(self, pool_id: str) -> float:
        """Return the current smoothed borrow rate for a pool."""
        return self._smoothed.get(pool_id, 0.0)

    def reset_pool(self, pool_id: str) -> None:
        """Clear prediction history for a pool."""
        self._history.pop(pool_id, None)
        self._smoothed.pop(pool_id, None)
        self._last_predictions.pop(pool_id, None)


# ---------------------------------------------------------------------------
# EngineObjectPool — Thread-Safe Singleton
# ---------------------------------------------------------------------------

class EngineObjectPool:
    """
    Central intelligent object pool orchestrator.

    Manages multiple named pools, each with configurable strategies
    for sizing, warmup, allocation, and predictive demand forecasting.
    Pools recycle game objects to minimise garbage collection overhead,
    especially under heavy real-time workloads.

    Usage:
        pool = get_object_pool()
        cfg = pool.create_pool("projectiles", "bullet", {"initial_size": 64})
        obj = pool.borrow_object(cfg.id)
        pool.return_object(cfg.id, obj.id)
    """

    _instance: Optional["EngineObjectPool"] = None
    _lock = threading.RLock()

    # Default memory estimate per object (bytes) when no factory is registered
    DEFAULT_MEMORY_PER_OBJECT = 256

    def __new__(cls) -> "EngineObjectPool":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineObjectPool":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # Core pool storage
        self._pools: Dict[str, Dict[str, PooledObject]] = defaultdict(dict)
        self._pool_configs: Dict[str, PoolConfig] = {}
        self._pool_order: Dict[str, int] = {}     # pool_id -> creation ordinal

        # Allocation policy state
        self._round_robin_cursors: Dict[str, int] = defaultdict(int)
        self._allocation_history: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        self._borrow_timestamps: Dict[str, float] = {}

        # Prediction & stats
        self._prediction_model = _DemandPredictor()
        self._peak_usage: Dict[str, int] = defaultdict(int)
        self._miss_counts: Dict[str, int] = defaultdict(int)
        self._borrow_totals: Dict[str, int] = defaultdict(int)
        self._return_totals: Dict[str, int] = defaultdict(int)
        self._borrow_cumulative_us: Dict[str, float] = defaultdict(float)
        self._borrow_samples: Dict[str, int] = defaultdict(int)

        # Per-pool factory lookaside cache
        self._factory_registry: Dict[str, callable] = {}

    # ------------------------------------------------------------------
    # Pool Lifecycle
    # ------------------------------------------------------------------

    def create_pool(
        self,
        name: str,
        object_type: str,
        config_params: Optional[Dict[str, Any]] = None,
    ) -> PoolConfig:
        """
        Create a new object pool with the given name and object type.

        *config_params* may override any PoolConfig field: strategy,
        initial_size, max_size, growth_factor, warmup_mode,
        allocation_policy, object_factory, reset_on_recycle, stats_enabled.
        """
        params = config_params or {}

        strategy_raw = params.get("strategy", "dynamic_growth")
        try:
            strategy = PoolStrategy(strategy_raw)
        except ValueError:
            strategy = PoolStrategy.DYNAMIC_GROWTH

        warmup_raw = params.get("warmup_mode", "incremental")
        try:
            warmup_mode = WarmupMode(warmup_raw)
        except ValueError:
            warmup_mode = WarmupMode.INCREMENTAL

        policy_raw = params.get("allocation_policy", "round_robin")
        try:
            allocation_policy = AllocationPolicy(policy_raw)
        except ValueError:
            allocation_policy = AllocationPolicy.ROUND_ROBIN

        config = PoolConfig(
            pool_name=name,
            strategy=strategy,
            initial_size=params.get("initial_size", 16),
            max_size=params.get("max_size", 1024),
            growth_factor=params.get("growth_factor", 1.5),
            warmup_mode=warmup_mode,
            allocation_policy=allocation_policy,
            object_factory=params.get("object_factory", "default_factory"),
            reset_on_recycle=params.get("reset_on_recycle", True),
            stats_enabled=params.get("stats_enabled", True),
        )

        with self._lock:
            self._pool_configs[config.id] = config
            self._pool_order[config.id] = len(self._pool_order)

            # Pre-allocate initial objects based on warmup mode
            if config.warmup_mode == WarmupMode.BATCH:
                self._allocate_objects(
                    config.id, object_type, config.initial_size, ObjectState.WARMING,
                )

        # Trigger warmup for non-NONE modes
        if config.warmup_mode != WarmupMode.NONE:
            self.prewarm_pool(config.id, config.initial_size, background=False)

        return config

    # ------------------------------------------------------------------
    # Borrow / Return
    # ------------------------------------------------------------------

    def borrow_object(
        self,
        pool_id: str,
        required_properties: Optional[Dict[str, Any]] = None,
    ) -> Optional[PooledObject]:
        """
        Acquire an available object from the pool.

        If no object is available the pool may grow according to its
        strategy up to *max_size*. Returns None when the pool is fully
        exhausted.
        """
        config = self._pool_configs.get(pool_id)
        if config is None:
            return None

        start = _time_module.perf_counter()

        with self._lock:
            pool = self._pools[pool_id]

            # Find a candidate via allocation policy
            candidate = self._select_candidate(pool_id, pool)
            if candidate is None:
                # No available object — try to grow if strategy permits
                if self._can_grow(pool_id, config):
                    obj = PooledObject(
                        pool_id=pool_id,
                        object_type=config.pool_name,
                        state=ObjectState.IN_USE,
                        data=required_properties or {},
                    )
                    pool[obj.id] = obj
                    self._update_borrow_stats(obj, start, config)
                    return obj

                # Pool exhausted
                self._miss_counts[pool_id] += 1
                return None

            # Mark the candidate as in-use
            candidate.state = ObjectState.IN_USE
            candidate.last_used = _time_module.time()
            candidate.borrow_count += 1
            if required_properties:
                candidate.data.update(required_properties)

            self._update_borrow_stats(candidate, start, config)
            return candidate

    def return_object(self, pool_id: str, object_id: str) -> bool:
        """
        Return a borrowed object to the pool for reuse.

        If *reset_on_recycle* is enabled on the pool config the object's
        data dict is cleared before returning.
        """
        config = self._pool_configs.get(pool_id)
        if config is None:
            return False

        with self._lock:
            pool = self._pools.get(pool_id)
            if pool is None:
                return False

            obj = pool.get(object_id)
            if obj is None:
                return False

            if obj.state == ObjectState.DISABLED:
                return False

            obj.state = ObjectState.AVAILABLE
            obj.last_used = _time_module.time()
            obj.recycle_count += 1
            self._return_totals[pool_id] += 1

            if config.reset_on_recycle:
                obj.data.clear()

            return True

    # ------------------------------------------------------------------
    # Warmup & Resizing
    # ------------------------------------------------------------------

    def prewarm_pool(
        self,
        pool_id: str,
        count: int,
        background: bool = False,
    ) -> int:
        """
        Pre-allocate *count* objects into the pool.

        Objects are created in WARMING state and then transitioned to
        AVAILABLE. If *background* is True the operation may be
        dispatched asynchronously (stub — delegates to synchronous path).
        Returns the number of objects actually warmed.
        """
        config = self._pool_configs.get(pool_id)
        if config is None:
            return 0

        object_type = config.pool_name
        created = 0

        with self._lock:
            pool = self._pools[pool_id]
            current = len(pool)
            space = config.max_size - current
            to_create = min(count, max(0, space))

            if to_create <= 0:
                return 0

            # Batch allocate in WARMING state
            for _ in range(to_create):
                obj = PooledObject(
                    pool_id=pool_id,
                    object_type=object_type,
                    state=ObjectState.WARMING,
                )
                pool[obj.id] = obj
                created += 1

            # Transition warmed objects to AVAILABLE
            for obj in pool.values():
                if obj.state == ObjectState.WARMING:
                    obj.state = ObjectState.AVAILABLE

        # Background warmup path (stub — would spawn a thread in production)
        if background:
            pass

        return created

    def resize_pool(
        self,
        pool_id: str,
        new_max_size: int,
    ) -> Optional[PoolConfig]:
        """
        Resize the pool's capacity to *new_max_size*.

        If the new size is smaller than the current object count, excess
        objects are removed (disabled ones first, then least-used).
        """
        config = self._pool_configs.get(pool_id)
        if config is None or new_max_size < 1:
            return None

        with self._lock:
            pool = self._pools[pool_id]
            current = len(pool)

            if new_max_size < current:
                # Need to remove excess objects
                excess = current - new_max_size
                removed = 0

                # First remove DISABLED objects
                disabled_ids = [
                    oid for oid, o in pool.items()
                    if o.state == ObjectState.DISABLED
                ]
                for oid in disabled_ids[:excess]:
                    del pool[oid]
                    removed += 1

                # If still too many, remove least-used AVAILABLE objects
                if removed < excess:
                    available = [
                        (oid, o) for oid, o in pool.items()
                        if o.state == ObjectState.AVAILABLE
                    ]
                    available.sort(key=lambda item: item[1].borrow_count)
                    remaining = excess - removed
                    for oid, _ in available[:remaining]:
                        del pool[oid]
                        removed += 1

            config.max_size = new_max_size
            return config

    # ------------------------------------------------------------------
    # Recycling & GC
    # ------------------------------------------------------------------

    def recycle_pool(self, pool_id: str) -> int:
        """
        Force-recycle all IN_USE objects back to AVAILABLE.

        Returns the number of objects recycled.
        """
        config = self._pool_configs.get(pool_id)
        if config is None:
            return 0

        recycled = 0
        with self._lock:
            pool = self._pools.get(pool_id)
            if pool is None:
                return 0
            for obj in pool.values():
                if obj.state == ObjectState.IN_USE:
                    obj.state = ObjectState.AVAILABLE
                    obj.recycle_count += 1
                    if config.reset_on_recycle:
                        obj.data.clear()
                    recycled += 1
        return recycled

    def force_gc(self, pool_id: str) -> int:
        """
        Force garbage-collect excess objects from the pool.

        Removes all AVAILABLE objects that exceed the initial size
        (based on strategy). DISABLED objects are always collected.
        Returns the number of objects removed.
        """
        config = self._pool_configs.get(pool_id)
        if config is None:
            return 0

        removed = 0
        with self._lock:
            pool = self._pools.get(pool_id)
            if pool is None:
                return 0

            # Always remove DISABLED objects
            disabled_ids = [
                oid for oid, o in pool.items()
                if o.state == ObjectState.DISABLED
            ]
            for oid in disabled_ids:
                del pool[oid]
                removed += 1

            # For FIXED_SIZE / LAZY strategies, trim available objects
            if config.strategy in (PoolStrategy.FIXED_SIZE, PoolStrategy.LAZY):
                available = [
                    oid for oid, o in pool.items()
                    if o.state == ObjectState.AVAILABLE
                ]
                in_use_count = sum(
                    1 for o in pool.values()
                    if o.state == ObjectState.IN_USE
                )
                target = max(config.initial_size - in_use_count, 0)
                to_remove = max(len(available) - target, 0)
                for oid in available[:to_remove]:
                    del pool[oid]
                    removed += 1

        return removed

    # ------------------------------------------------------------------
    # Prediction & Optimisation
    # ------------------------------------------------------------------

    def predict_demand(self, pool_id: str, time_window_seconds: float = 5.0) -> int:
        """
        Predict the number of objects that will be borrowed in the next
        *time_window_seconds* seconds using exponential smoothing over
        historical borrow data.
        """
        config = self._pool_configs.get(pool_id)
        if config is None:
            return 0

        # The predictor has its own history; a real implementation would
        # feed borrow events into it during borrow_object() as well.
        # For now, simulate a demand-driven prediction using the smoothed
        # rate and the current in-use count.
        smoothed = self._prediction_model.get_smoothed_rate(pool_id)
        if smoothed > 0:
            return max(1, int(smoothed * time_window_seconds))

        # Fallback: use the raw prediction engine
        return self._prediction_model.predict(pool_id, time_window_seconds)

    def auto_optimize(self) -> Dict[str, Any]:
        """
        Run automatic optimization across all pools.

        Analyses recent usage patterns and adjusts pool sizes:
        - Pools with consistent misses get their capacity increased.
        - Pools with low utilization get trimmed back.
        - Predictive pools get their initial size adjusted.
        Returns a summary of adjustments made.
        """
        adjustments: List[Dict[str, Any]] = []
        now = _time_module.time()

        with self._lock:
            for pool_id, config in self._pool_configs.items():
                pool = self._pools.get(pool_id, {})
                total = len(pool)
                in_use = sum(
                    1 for o in pool.values()
                    if o.state == ObjectState.IN_USE
                )
                available = total - in_use

                # Calculate utilization over recent history
                history = self._allocation_history.get(pool_id, [])
                recent_minute = [
                    (_, t) for (_, t) in history
                    if now - t <= 60.0
                ]
                utilization = (
                    in_use / max(total, 1)
                    if total > 0
                    else 0.0
                )
                miss_count = self._miss_counts.get(pool_id, 0)

                adjustment = {
                    "pool_id": pool_id,
                    "pool_name": config.pool_name,
                    "action": "none",
                    "reason": "",
                }

                # Strategy-specific adjustments
                if config.strategy == PoolStrategy.FIXED_SIZE:
                    # FIXED_SIZE pools do not auto-resize
                    pass

                elif config.strategy == PoolStrategy.PREDICTIVE:
                    # Adjust initial size based on smoothed demand
                    demand = self.predict_demand(pool_id, time_window_seconds=10.0)
                    if demand > config.initial_size * 1.5:
                        new_initial = min(demand, config.max_size // 2)
                        if new_initial > config.initial_size:
                            config.initial_size = new_initial
                            adjustment["action"] = "increase_initial_size"
                            adjustment["reason"] = (
                                f"demand {demand} exceeds initial {config.initial_size}"
                            )
                            adjustment["new_initial_size"] = new_initial

                elif config.strategy == PoolStrategy.ADAPTIVE:
                    # Grow if we are consistently near capacity
                    if utilization > 0.85 and miss_count > 3:
                        new_max = min(
                            int(config.max_size * config.growth_factor),
                            config.max_size * 4,
                        )
                        if new_max > config.max_size:
                            config.max_size = new_max
                            adjustment["action"] = "grow_max_size"
                            adjustment["reason"] = (
                                f"utilization {utilization:.2f}, misses {miss_count}"
                            )
                            adjustment["new_max_size"] = new_max

                    # Shrink if we have too many idle objects
                    if utilization < 0.20 and available > config.initial_size * 2:
                        target_max = max(
                            config.initial_size,
                            int(config.max_size * 0.7),
                        )
                        if target_max < config.max_size:
                            self.resize_pool(pool_id, target_max)
                            adjustment["action"] = "shrink_max_size"
                            adjustment["reason"] = (
                                f"low utilization {utilization:.2f}"
                            )
                            adjustment["new_max_size"] = target_max

                elif config.strategy == PoolStrategy.DYNAMIC_GROWTH:
                    if available < 2 and config.max_size > total:
                        # Running low — grow if we haven't hit max
                        growth = max(1, int(total * (config.growth_factor - 1.0)))
                        to_add = min(growth, config.max_size - total)
                        if to_add > 0:
                            self.prewarm_pool(pool_id, to_add)
                            adjustment["action"] = "grow"
                            adjustment["reason"] = "low availability"
                            adjustment["objects_added"] = to_add

                elif config.strategy == PoolStrategy.EAGER:
                    # Eager pools always maintain their initial_size
                    if available < config.initial_size // 2:
                        deficit = config.initial_size - available
                        self.prewarm_pool(pool_id, deficit)
                        adjustment["action"] = "refill"
                        adjustment["reason"] = "eager pool below threshold"
                        adjustment["objects_added"] = deficit

                if adjustment["action"] != "none":
                    adjustments.append(adjustment)

        return {
            "pools_analyzed": len(self._pool_configs),
            "adjustments_made": len(adjustments),
            "adjustments": adjustments,
        }

    # ------------------------------------------------------------------
    # Candidate Selection — Allocation Policies
    # ------------------------------------------------------------------

    def _select_candidate(
        self,
        pool_id: str,
        pool: Dict[str, PooledObject],
    ) -> Optional[PooledObject]:
        """Select an available object based on the pool's allocation policy."""
        config = self._pool_configs.get(pool_id)
        if config is None:
            return None

        policy = config.allocation_policy
        candidates = [
            o for o in pool.values()
            if o.state == ObjectState.AVAILABLE
        ]
        if not candidates:
            return None

        if policy == AllocationPolicy.ROUND_ROBIN:
            cursor = self._round_robin_cursors[pool_id]
            idx = cursor % len(candidates)
            self._round_robin_cursors[pool_id] = cursor + 1
            return candidates[idx]

        elif policy == AllocationPolicy.LEAST_USED:
            candidates.sort(key=lambda o: o.borrow_count)
            return candidates[0]

        elif policy == AllocationPolicy.MOST_READY:
            # Objects that have been idle longest are "most ready"
            candidates.sort(key=lambda o: o.last_used)
            return candidates[0]

        elif policy == AllocationPolicy.PRIORITY_BASED:
            candidates.sort(key=lambda o: -o.priority)
            return candidates[0]

        elif policy == AllocationPolicy.RANDOM:
            import random
            return random.choice(candidates)

        # Fallback: return first available
        return candidates[0] if candidates else None

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _can_grow(self, pool_id: str, config: PoolConfig) -> bool:
        """Determine if the pool may grow based on its strategy."""
        pool = self._pools.get(pool_id, {})
        current = len(pool)

        if current >= config.max_size:
            return False

        if config.strategy == PoolStrategy.FIXED_SIZE:
            return False

        if config.strategy == PoolStrategy.LAZY:
            # LAZY only grows if ALL objects are in use
            available = sum(
                1 for o in pool.values()
                if o.state == ObjectState.AVAILABLE
            )
            return available == 0

        # DYNAMIC_GROWTH, PREDICTIVE, ADAPTIVE, EAGER all allow growth
        return True

    def _allocate_objects(
        self,
        pool_id: str,
        object_type: str,
        count: int,
        state: ObjectState,
    ) -> int:
        """Internal bulk allocation of pooled objects."""
        pool = self._pools[pool_id]
        created = 0
        for _ in range(count):
            obj = PooledObject(
                pool_id=pool_id,
                object_type=object_type,
                state=state,
            )
            pool[obj.id] = obj
            created += 1
        return created

    def _update_borrow_stats(
        self,
        obj: PooledObject,
        start: float,
        config: PoolConfig,
    ) -> None:
        """Update per-pool telemetry after a successful borrow."""
        pool_id = obj.pool_id
        self._borrow_totals[pool_id] += 1

        elapsed_us = (_time_module.perf_counter() - start) * 1_000_000.0
        self._borrow_cumulative_us[pool_id] += elapsed_us
        self._borrow_samples[pool_id] += 1

        # Track peak usage
        pool = self._pools.get(pool_id, {})
        in_use = sum(
            1 for o in pool.values()
            if o.state == ObjectState.IN_USE
        )
        self._peak_usage[pool_id] = max(self._peak_usage[pool_id], in_use)

        # Feed the prediction model
        self._prediction_model.record_borrow(pool_id, _time_module.time())

        # Log allocation history
        if config.stats_enabled:
            self._allocation_history[pool_id].append(
                (obj.id, _time_module.time())
            )
            # Prune old history entries beyond 5 minutes
            cutoff = _time_module.time() - 300.0
            self._allocation_history[pool_id] = [
                (oid, ts) for (oid, ts) in self._allocation_history[pool_id]
                if ts >= cutoff
            ]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_pool_stats(self, pool_id: str) -> Optional[PoolStats]:
        """Return a live PoolStats snapshot for a single pool."""
        config = self._pool_configs.get(pool_id)
        if config is None:
            return None

        with self._lock:
            pool = self._pools.get(pool_id, {})
            total = len(pool)
            available = sum(
                1 for o in pool.values()
                if o.state == ObjectState.AVAILABLE
            )
            in_use = sum(
                1 for o in pool.values()
                if o.state == ObjectState.IN_USE
            )
            reserved = sum(
                1 for o in pool.values()
                if o.state == ObjectState.RESERVED
            )

            total_borrows = self._borrow_totals.get(pool_id, 0)
            total_returns = self._return_totals.get(pool_id, 0)
            samples = self._borrow_samples.get(pool_id, 0)
            avg_us = (
                self._borrow_cumulative_us[pool_id] / samples
                if samples > 0
                else 0.0
            )

            recycle_rate = (
                total_returns / max(total_borrows, 1)
                if total_borrows > 0
                else 0.0
            )

            memory_estimate = total * self.DEFAULT_MEMORY_PER_OBJECT

            return PoolStats(
                pool_id=pool_id,
                total_objects=total,
                available=available,
                in_use=in_use,
                reserved=reserved,
                peak_usage=self._peak_usage.get(pool_id, 0),
                total_borrows=total_borrows,
                total_returns=total_returns,
                miss_count=self._miss_counts.get(pool_id, 0),
                avg_borrow_time_us=round(avg_us, 3),
                recycle_rate=round(recycle_rate, 4),
                memory_estimate_bytes=memory_estimate,
            )

    def get_global_stats(self) -> Dict[str, Any]:
        """Aggregate statistics across all pools."""
        with self._lock:
            total_objects = 0
            total_available = 0
            total_in_use = 0
            total_borrows = 0
            total_returns = 0
            total_misses = 0
            total_memory = 0

            for pool_id in self._pool_configs:
                stats = self.get_pool_stats(pool_id)
                if stats is None:
                    continue
                total_objects += stats.total_objects
                total_available += stats.available
                total_in_use += stats.in_use
                total_borrows += stats.total_borrows
                total_returns += stats.total_returns
                total_misses += stats.miss_count
                total_memory += stats.memory_estimate_bytes

            overall_recycle_rate = (
                total_returns / max(total_borrows, 1)
                if total_borrows > 0
                else 0.0
            )

            return {
                "total_pools": len(self._pool_configs),
                "total_objects": total_objects,
                "total_available": total_available,
                "total_in_use": total_in_use,
                "total_borrows": total_borrows,
                "total_returns": total_returns,
                "total_misses": total_misses,
                "overall_recycle_rate": round(overall_recycle_rate, 4),
                "total_memory_estimate_bytes": total_memory,
                "prediction_pools": len(self._prediction_model._smoothed),
            }

    def list_pools(self) -> List[Dict[str, Any]]:
        """Return a summary dict for each registered pool."""
        with self._lock:
            summaries: List[Dict[str, Any]] = []
            # Preserve creation order via _pool_order
            ordered = sorted(
                self._pool_configs.items(),
                key=lambda item: self._pool_order.get(item[0], 0),
            )
            for pool_id, config in ordered:
                pool = self._pools.get(pool_id, {})
                total = len(pool)
                available = sum(
                    1 for o in pool.values()
                    if o.state == ObjectState.AVAILABLE
                )
                in_use = total - available
                summaries.append({
                    "pool_id": pool_id,
                    "pool_name": config.pool_name,
                    "strategy": config.strategy.value,
                    "total_objects": total,
                    "available": available,
                    "in_use": in_use,
                    "max_size": config.max_size,
                    "utilization": round(in_use / max(total, 1), 4),
                })
            return summaries

    def get_status(self) -> Dict[str, Any]:
        """Return a full status report covering all pools and global stats."""
        return {
            "engine": "object_pool",
            "version": "1.0",
            "global_stats": self.get_global_stats(),
            "pools": self.list_pools(),
            "configs": {
                pid: c.to_dict()
                for pid, c in self._pool_configs.items()
            },
            "prediction_model": {
                "tracked_pools": list(self._prediction_model._smoothed.keys()),
                "smoothed_rates": dict(self._prediction_model._smoothed),
                "last_predictions": dict(self._prediction_model._last_predictions),
            },
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """
        Reset the entire object pool system.

        Clears all pools, configs, statistics, and prediction history.
        """
        with self._lock:
            self._pools.clear()
            self._pool_configs.clear()
            self._pool_order.clear()
            self._round_robin_cursors.clear()
            self._allocation_history.clear()
            self._borrow_timestamps.clear()
            self._peak_usage.clear()
            self._miss_counts.clear()
            self._borrow_totals.clear()
            self._return_totals.clear()
            self._borrow_cumulative_us.clear()
            self._borrow_samples.clear()
            self._factory_registry.clear()
            self._prediction_model = _DemandPredictor()


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_object_pool() -> EngineObjectPool:
    """Return the singleton EngineObjectPool instance."""
    return EngineObjectPool.get_instance()