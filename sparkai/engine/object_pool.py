"""
Object Pool System - Pre-allocated object reuse for performance-critical game objects.

Architecture:
    ObjectPoolSystem/
    |-- PoolStrategy (allocation strategy enumeration)
    |-- PoolConfig (pool configuration dataclass)
    |-- PooledObject (pool-aware wrapper dataclass)
    |-- ObjectPool (typed pool with acquire/release lifecycle)
    |-- ObjectPoolSystem (global pool orchestration)

Manages pools of reusable game objects to eliminate GC pressure from frequent
instantiation/destruction patterns. Supports auto-expansion, shrink-on-idle,
and LIFO/FIFO acquisition strategies.
"""

from __future__ import annotations

import uuid
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

T = TypeVar("T")


class PoolStrategy(Enum):
    LIFO = auto()
    FIFO = auto()


@dataclass
class PoolConfig:
    initial_size: int = 16
    max_size: int = 256
    auto_expand: bool = True
    shrink_on_idle: bool = False
    idle_timeout: float = 60.0
    strategy: PoolStrategy = PoolStrategy.LIFO
    factory_kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PooledObject:
    object_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    instance: Any = None
    acquired_at: float = 0.0
    active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "active": self.active,
            "acquired_at": self.acquired_at,
        }


class ObjectPool:
    def __init__(self, factory: Callable[[], T], config: Optional[PoolConfig] = None):
        self._factory = factory
        self._config = config or PoolConfig()
        self._available: deque[PooledObject] = deque()
        self._active: Dict[str, PooledObject] = {}
        self._total_created: int = 0
        self._total_acquired: int = 0
        self._total_released: int = 0
        self._peak_active: int = 0
        self._pool_id: str = str(uuid.uuid4())

        for _ in range(self._config.initial_size):
            self._preallocate()

    def _preallocate(self) -> PooledObject:
        instance = self._factory(**self._config.factory_kwargs)
        obj = PooledObject(instance=instance)
        self._available.append(obj)
        self._total_created += 1
        return obj

    def acquire(self) -> PooledObject:
        if not self._available:
            if self._config.auto_expand and self._total_created < self._config.max_size:
                obj = self._preallocate()
            else:
                raise RuntimeError(
                    f"Object pool exhausted: {self._total_created}/{self._config.max_size}"
                )
        else:
            if self._config.strategy == PoolStrategy.LIFO:
                obj = self._available.pop()
            else:
                obj = self._available.popleft()

        obj.acquired_at = time.time()
        obj.active = True
        self._active[obj.object_id] = obj
        self._total_acquired += 1
        self._peak_active = max(self._peak_active, len(self._active))
        return obj

    def release(self, obj: PooledObject) -> bool:
        if obj.object_id not in self._active:
            return False
        del self._active[obj.object_id]
        obj.active = False
        obj.acquired_at = 0.0
        self._available.append(obj)
        self._total_released += 1
        return True

    def shrink(self) -> int:
        if not self._config.shrink_on_idle:
            return 0
        now = time.time()
        removed = 0
        min_keep = self._config.initial_size
        while len(self._available) > min_keep:
            oldest = self._available[0]
            if oldest.acquired_at > 0 and (now - oldest.acquired_at) < self._config.idle_timeout:
                break
            self._available.popleft()
            self._total_created -= 1
            removed += 1
        return removed

    def prewarm(self, count: int) -> int:
        created = 0
        while self._total_created < self._config.max_size and created < count:
            self._preallocate()
            created += 1
        return created

    def reset(self, reinitialize: bool = False) -> None:
        if reinitialize:
            self._available.clear()
            self._active.clear()
            self._total_created = 0
            for _ in range(self._config.initial_size):
                self._preallocate()
        else:
            for obj in list(self._active.values()):
                self.release(obj)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "pool_id": self._pool_id,
            "available": len(self._available),
            "active": len(self._active),
            "total_created": self._total_created,
            "total_acquired": self._total_acquired,
            "total_released": self._total_released,
            "peak_active": self._peak_active,
            "max_size": self._config.max_size,
            "strategy": self._config.strategy.name,
        }

    @property
    def active_count(self) -> int:
        return len(self._active)

    @property
    def available_count(self) -> int:
        return len(self._available)


class ObjectPoolSystem:
    _instance: Optional["ObjectPoolSystem"] = None

    def __init__(self):
        self._pools: Dict[str, ObjectPool] = {}
        self._type_registry: Dict[str, Type] = {}

    @classmethod
    def get_instance(cls) -> "ObjectPoolSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_pool(
        self,
        pool_name: str,
        factory: Callable[[], T],
        config: Optional[PoolConfig] = None,
    ) -> ObjectPool:
        if pool_name in self._pools:
            raise ValueError(f"Pool '{pool_name}' already exists")
        pool = ObjectPool(factory, config)
        self._pools[pool_name] = pool
        return pool

    def get_pool(self, pool_name: str) -> Optional[ObjectPool]:
        return self._pools.get(pool_name)

    def acquire(self, pool_name: str) -> Optional[PooledObject]:
        pool = self._pools.get(pool_name)
        if not pool:
            return None
        return pool.acquire()

    def release(self, pool_name: str, obj: PooledObject) -> bool:
        pool = self._pools.get(pool_name)
        if not pool:
            return False
        return pool.release(obj)

    def remove_pool(self, pool_name: str) -> bool:
        if pool_name in self._pools:
            del self._pools[pool_name]
            return True
        return False

    def list_pools(self) -> List[str]:
        return list(self._pools.keys())

    def shrink_all(self) -> Dict[str, int]:
        return {name: pool.shrink() for name, pool in self._pools.items()}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "pool_count": len(self._pools),
            "pools": {name: pool.get_stats() for name, pool in self._pools.items()},
            "total_active": sum(p.active_count for p in self._pools.values()),
            "total_available": sum(p.available_count for p in self._pools.values()),
        }


def get_object_pool_system() -> ObjectPoolSystem:
    return ObjectPoolSystem.get_instance()
