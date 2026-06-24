"""
SparkLabs Engine - Entity Component System Core

A lightweight, high-performance Entity Component System (ECS) implementation
with sparse-set component storage, typed component queries, and dependency-aware
system scheduling. Entities are pure identifiers, components are plain data
containers, and systems encapsulate all behavior.

Architecture:
  EntityComponentEngine (Singleton)
    |-- Entity             — lightweight identifier with tags and active state
    |-- Component          — base class for all component data
    |-- System             — processing logic with query/filter capabilities
    |-- ComponentManager   — sparse-set storage for O(1) lookup
    |-- SystemManager      — dependency-ordered system execution
    |-- QueryResult        — filtered view of entities matching a component set

Component Storage:
  Uses sparse-set layout where each component type has a dense packed array
  and a sparse mapping from entity index to dense array index. This provides
  O(1) add/remove/get and cache-friendly iteration over all entities with
  a given component type.

Usage:
    engine = get_entity_component_engine()
    entity = engine.create_entity(name="Player", tags=["player", "hero"])
    engine.add_component(entity.id, HealthComponent(health=100))
    engine.add_system(HealthSystem(), priority=50)
    engine.update(delta_time)
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ComponentStorageType(Enum):
    """Storage layout strategy for component data."""
    SPARSE_SET = "sparse_set"
    PACKED_ARRAY = "packed_array"
    HASH_MAP = "hash_map"


class SystemExecutionPhase(Enum):
    """Ordered execution phases within a single frame update."""
    PRE_UPDATE = "pre_update"
    UPDATE = "update"
    POST_UPDATE = "post_update"
    PRE_RENDER = "pre_render"
    RENDER = "render"
    POST_RENDER = "post_render"


class EntityState(Enum):
    """Lifecycle state of an entity."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_DESTROY = "pending_destroy"
    DESTROYED = "destroyed"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Entity:
    """Lightweight game entity identifier with metadata.

    Entities are pure identifiers that gain behavior through attached
    components. They carry no data other than identity, tags, and
    lifecycle state. Component data is stored externally in the
    ComponentManager for cache-friendly iteration.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    tags: List[str] = field(default_factory=list)
    state: EntityState = EntityState.ACTIVE
    layer: int = 0
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    creation_time: float = field(default_factory=_time_module.time)
    last_update_time: float = 0.0

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        if tag in self.tags:
            self.tags.remove(tag)

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def add_child(self, child_id: str) -> None:
        if child_id not in self.children_ids:
            self.children_ids.append(child_id)

    def remove_child(self, child_id: str) -> None:
        if child_id in self.children_ids:
            self.children_ids.remove(child_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tags": list(self.tags),
            "state": self.state.value,
            "layer": self.layer,
            "parent_id": self.parent_id,
            "children_ids": list(self.children_ids),
            "creation_time": self.creation_time,
            "last_update_time": self.last_update_time,
        }


@dataclass
class Component:
    """Base class for all component data containers.

    Components are pure data with no behavior. Each component type
    defines a unique type_id used by the storage system for O(1)
    array-based lookup. Components belong to exactly one entity.
    """
    component_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    entity_id: str = ""
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "entity_id": self.entity_id,
            "is_active": self.is_active,
        }


@dataclass
class System:
    """Base class for all system processing logic.

    Systems operate on entities that match a required component set.
    Each system declares its component requirements and execution
    dependencies. The SystemManager handles dependency ordering and
    filters entities before passing them to the system's update method.
    """
    system_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    is_active: bool = True
    priority: int = 50
    phase: SystemExecutionPhase = SystemExecutionPhase.UPDATE

    # Component type names required by this system
    required_components: List[str] = field(default_factory=list)
    # Component type names that are optional (processed if present)
    optional_components: List[str] = field(default_factory=list)
    # System IDs that must execute before this system
    dependencies: List[str] = field(default_factory=list)
    # Entities that matched the last query
    _matched_entities: List[str] = field(default_factory=list, repr=False)

    def query(self, component_manager: ComponentManager) -> List[str]:
        """Discover entities that match this system's component requirements."""
        if not self.required_components:
            return []
        candidates = component_manager.get_entities_with_components(
            self.required_components
        )
        self._matched_entities = candidates
        return candidates

    def update(self, delta_time: float, entities: List[str],
               component_manager: ComponentManager) -> None:
        """Process matching entities. Override in subclasses."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_id": self.system_id,
            "name": self.name,
            "is_active": self.is_active,
            "priority": self.priority,
            "phase": self.phase.value,
            "required_components": list(self.required_components),
            "optional_components": list(self.optional_components),
            "dependencies": list(self.dependencies),
            "matched_entity_count": len(self._matched_entities),
        }


@dataclass
class QueryResult:
    """Result of a component query against the entity storage.

    Provides a filtered iterator over entities that possess all
    required components. Supports both single-component and
    multi-component queries with optional exclusion filters.
    """
    entity_ids: List[str] = field(default_factory=list)
    required_types: List[str] = field(default_factory=list)
    excluded_types: List[str] = field(default_factory=list)
    total_matched: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_ids": list(self.entity_ids),
            "required_types": list(self.required_types),
            "excluded_types": list(self.excluded_types),
            "total_matched": self.total_matched,
        }


# ---------------------------------------------------------------------------
# ComponentManager — Sparse-Set Component Storage
# ---------------------------------------------------------------------------

class ComponentManager:
    """Manages component data using sparse-set storage for O(1) operations.

    Each component type maintains a sparse array (entity index → dense index)
    and a dense packed array of component instances. This enables:
    - O(1) addition, removal, and lookup
    - Cache-friendly iteration over all entities with a given component
    - Efficient multi-component intersection queries
    """

    def __init__(self) -> None:
        # Sparse maps: entity_id → dense_index for each component type
        self._sparse: Dict[str, Dict[str, int]] = defaultdict(dict)
        # Dense packed arrays of component instances
        self._dense: Dict[str, List[Component]] = defaultdict(list)
        # Entity-to-dense-index mapping (reverse of sparse)
        self._entity_indices: Dict[str, Dict[str, int]] = defaultdict(dict)
        # All registered component type names
        self._component_types: Set[str] = set()
        # Entity index → component type set for fast intersection queries
        self._entity_component_map: Dict[str, Set[str]] = defaultdict(set)
        # Stats tracking
        self._add_count: int = 0
        self._remove_count: int = 0
        self._query_count: int = 0

    def register_component_type(self, type_name: str) -> None:
        """Register a new component type for storage."""
        if type_name not in self._component_types:
            self._component_types.add(type_name)
            self._sparse[type_name] = {}
            self._dense[type_name] = []

    def add_component(self, entity_id: str, component: Component,
                      component_type: str) -> bool:
        """Add a component to an entity. Returns True if added, False if already present."""
        if component_type not in self._component_types:
            self.register_component_type(component_type)

        sparse_map = self._sparse[component_type]
        if entity_id in sparse_map:
            return False

        dense_array = self._dense[component_type]
        index = len(dense_array)
        dense_array.append(component)
        sparse_map[entity_id] = index
        self._entity_indices[entity_id][component_type] = index
        self._entity_component_map[entity_id].add(component_type)
        self._add_count += 1
        return True

    def remove_component(self, entity_id: str,
                         component_type: str) -> Optional[Component]:
        """Remove a component from an entity. Returns the removed component or None."""
        sparse_map = self._sparse.get(component_type, {})
        if entity_id not in sparse_map:
            return None

        index = sparse_map[entity_id]
        dense_array = self._dense[component_type]

        # Swap-remove: move last element to the removed position
        removed = dense_array[index]
        last_index = len(dense_array) - 1
        if index != last_index:
            last_component = dense_array[last_index]
            last_entity_id = last_component.entity_id
            dense_array[index] = last_component
            sparse_map[last_entity_id] = index
            self._entity_indices[last_entity_id][component_type] = index

        dense_array.pop()
        del sparse_map[entity_id]
        self._entity_indices[entity_id].pop(component_type, None)
        self._entity_component_map[entity_id].discard(component_type)
        self._remove_count += 1
        return removed

    def get_component(self, entity_id: str,
                      component_type: str) -> Optional[Component]:
        """Get a component by entity and type. O(1) lookup."""
        sparse_map = self._sparse.get(component_type, {})
        index = sparse_map.get(entity_id)
        if index is None:
            return None
        return self._dense[component_type][index]

    def has_component(self, entity_id: str, component_type: str) -> bool:
        """Check if an entity has a specific component type. O(1)."""
        return component_type in self._entity_component_map.get(entity_id, set())

    def get_entities_with_component(self, component_type: str) -> List[str]:
        """Get all entity IDs that have a specific component type."""
        sparse_map = self._sparse.get(component_type, {})
        return list(sparse_map.keys())

    def get_entities_with_components(self, component_types: List[str]) -> List[str]:
        """Get entity IDs that have ALL specified component types."""
        self._query_count += 1
        if not component_types:
            return []

        # Start with the smallest component set for efficiency
        sorted_types = sorted(component_types,
                              key=lambda ct: len(self._sparse.get(ct, {})))
        result = set(self._sparse.get(sorted_types[0], {}).keys())

        for ct in sorted_types[1:]:
            ct_set = self._sparse.get(ct, {})
            result.intersection_update(ct_set.keys())
            if not result:
                break

        return list(result)

    def get_components_for_entity(self, entity_id: str) -> Dict[str, Component]:
        """Get all components attached to an entity."""
        component_types = self._entity_component_map.get(entity_id, set())
        result = {}
        for ct in component_types:
            comp = self.get_component(entity_id, ct)
            if comp is not None:
                result[ct] = comp
        return result

    def remove_all_components(self, entity_id: str) -> int:
        """Remove all components from an entity. Returns count of removed components."""
        component_types = list(self._entity_component_map.get(entity_id, set()))
        count = 0
        for ct in component_types:
            if self.remove_component(entity_id, ct) is not None:
                count += 1
        return count

    def get_component_count(self, component_type: str) -> int:
        """Get the number of entities with a particular component type."""
        return len(self._dense.get(component_type, []))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "component_types": len(self._component_types),
            "component_type_names": list(self._component_types),
            "total_components": sum(len(d) for d in self._dense.values()),
            "add_count": self._add_count,
            "remove_count": self._remove_count,
            "query_count": self._query_count,
            "per_type_counts": {
                ct: len(self._dense.get(ct, []))
                for ct in self._component_types
            },
        }


# ---------------------------------------------------------------------------
# SystemManager — Dependency-Ordered System Execution
# ---------------------------------------------------------------------------

class SystemManager:
    """Manages system registration, dependency ordering, and execution.

    Systems are sorted topologically based on declared dependencies and
    priority values. Systems with the same priority that share no
    dependencies may be executed concurrently in future versions.
    """

    def __init__(self) -> None:
        self._systems: Dict[str, System] = {}
        self._phase_systems: Dict[SystemExecutionPhase, List[str]] = defaultdict(list)
        self._execution_order: List[str] = []
        self._dirty_order: bool = True
        self._frame_count: int = 0
        self._total_execution_time: float = 0.0

    def add_system(self, system: System) -> None:
        """Register a system for execution."""
        self._systems[system.system_id] = system
        self._phase_systems[system.phase].append(system.system_id)
        self._dirty_order = True

    def remove_system(self, system_id: str) -> bool:
        """Remove a registered system."""
        system = self._systems.pop(system_id, None)
        if system is None:
            return False
        phase_list = self._phase_systems.get(system.phase, [])
        if system_id in phase_list:
            phase_list.remove(system_id)
        self._dirty_order = True
        return True

    def get_system(self, system_id: str) -> Optional[System]:
        """Get a registered system by ID."""
        return self._systems.get(system_id)

    def _compute_execution_order(self) -> None:
        """Compute topological sort of systems based on dependencies and priority."""
        if not self._dirty_order:
            return

        ordered: List[str] = []
        visited: Set[str] = set()
        temp_mark: Set[str] = set()

        def visit(sid: str) -> None:
            if sid in temp_mark:
                return
            if sid not in visited:
                temp_mark.add(sid)
                system = self._systems.get(sid)
                if system:
                    for dep_id in system.dependencies:
                        if dep_id in self._systems:
                            visit(dep_id)
                temp_mark.discard(sid)
                visited.add(sid)
                ordered.append(sid)

        # Sort by priority within each phase, then topological sort
        for phase in SystemExecutionPhase:
            phase_ids = self._phase_systems.get(phase, [])
            phase_ids.sort(key=lambda sid: self._systems[sid].priority)
            for sid in phase_ids:
                visit(sid)

        self._execution_order = ordered
        self._dirty_order = False

    def execute_phase(self, phase: SystemExecutionPhase, delta_time: float,
                      component_manager: ComponentManager) -> None:
        """Execute all systems registered for a given phase."""
        self._compute_execution_order()
        phase_ids = self._phase_systems.get(phase, [])
        for sid in self._execution_order:
            if sid not in phase_ids:
                continue
            system = self._systems.get(sid)
            if system is None or not system.is_active:
                continue
            entities = system.query(component_manager)
            start_time = _time_module.time()
            system.update(delta_time, entities, component_manager)
            elapsed = _time_module.time() - start_time
            self._total_execution_time += elapsed
        self._frame_count += 1

    def update_all(self, delta_time: float,
                   component_manager: ComponentManager) -> None:
        """Execute all systems across all phases in order."""
        for phase in SystemExecutionPhase:
            self.execute_phase(phase, delta_time, component_manager)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "system_count": len(self._systems),
            "phase_counts": {
                p.value: len(self._phase_systems.get(p, []))
                for p in SystemExecutionPhase
            },
            "execution_order": list(self._execution_order),
            "frame_count": self._frame_count,
            "total_execution_time": self._total_execution_time,
            "average_execution_time": (
                self._total_execution_time / max(self._frame_count, 1)
            ),
        }


# ---------------------------------------------------------------------------
# EntityComponentEngine — Unified ECS Singleton
# ---------------------------------------------------------------------------

class EntityComponentEngine:
    """Unified Entity Component System engine for SparkLabs.

    Manages the full lifecycle of entities, components, and systems.
    Provides a clean API for creating entities, attaching components,
    and running system updates each frame. Uses sparse-set storage
    for O(1) component operations and dependency-ordered execution.
    """

    _instance: Optional["EntityComponentEngine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "EntityComponentEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EntityComponentEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._entities: Dict[str, Entity] = {}
        self._component_manager = ComponentManager()
        self._system_manager = SystemManager()
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        self._layer_index: Dict[int, Set[str]] = defaultdict(set)
        self._pending_destroy: List[str] = []
        self._entity_count: int = 0
        self._frame_count: int = 0

    # ---- Entity Management ----

    def create_entity(self, name: str = "", tags: Optional[List[str]] = None,
                      layer: int = 0,
                      parent_id: Optional[str] = None) -> Entity:
        """Create a new entity with optional name, tags, and parent."""
        entity = Entity(name=name, tags=tags or [], layer=layer,
                        parent_id=parent_id)
        self._entities[entity.id] = entity
        self._entity_count += 1

        for tag in entity.tags:
            self._tag_index[tag].add(entity.id)
        self._layer_index[layer].add(entity.id)

        if parent_id and parent_id in self._entities:
            self._entities[parent_id].add_child(entity.id)

        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by its ID."""
        return self._entities.get(entity_id)

    def destroy_entity(self, entity_id: str) -> bool:
        """Mark an entity for destruction at the end of the current frame."""
        entity = self._entities.get(entity_id)
        if entity is None:
            return False
        entity.state = EntityState.PENDING_DESTROY
        self._pending_destroy.append(entity_id)
        return True

    def destroy_entity_immediate(self, entity_id: str) -> bool:
        """Immediately destroy an entity and all its components."""
        entity = self._entities.pop(entity_id, None)
        if entity is None:
            return False

        for tag in entity.tags:
            tag_set = self._tag_index.get(tag)
            if tag_set:
                tag_set.discard(entity_id)
        layer_set = self._layer_index.get(entity.layer)
        if layer_set:
            layer_set.discard(entity_id)

        self._component_manager.remove_all_components(entity_id)
        self._entity_count -= 1
        return True

    def _process_destroyed(self) -> None:
        """Process all entities marked for destruction."""
        for entity_id in self._pending_destroy:
            self.destroy_entity_immediate(entity_id)
        self._pending_destroy.clear()

    # ---- Component Management ----

    def add_component(self, entity_id: str, component: Component,
                      component_type: str) -> bool:
        """Attach a component to an entity."""
        if entity_id not in self._entities:
            return False
        component.entity_id = entity_id
        return self._component_manager.add_component(entity_id, component,
                                                     component_type)

    def remove_component(self, entity_id: str,
                         component_type: str) -> Optional[Component]:
        """Remove a component from an entity."""
        return self._component_manager.remove_component(entity_id, component_type)

    def get_component(self, entity_id: str,
                      component_type: str) -> Optional[Component]:
        """Get a component from an entity."""
        return self._component_manager.get_component(entity_id, component_type)

    def has_component(self, entity_id: str, component_type: str) -> bool:
        """Check if an entity has a specific component type."""
        return self._component_manager.has_component(entity_id, component_type)

    def get_entity_components(self, entity_id: str) -> Dict[str, Component]:
        """Get all components attached to an entity."""
        return self._component_manager.get_components_for_entity(entity_id)

    # ---- System Management ----

    def add_system(self, system: System) -> None:
        """Register a system for execution."""
        self._system_manager.add_system(system)

    def remove_system(self, system_id: str) -> bool:
        """Remove a registered system."""
        return self._system_manager.remove_system(system_id)

    def get_system(self, system_id: str) -> Optional[System]:
        """Get a registered system by ID."""
        return self._system_manager.get_system(system_id)

    # ---- Query Methods ----

    def query_entities(self, required: List[str],
                       excluded: Optional[List[str]] = None) -> QueryResult:
        """Query entities that have all required components and none of the excluded."""
        entity_ids = self._component_manager.get_entities_with_components(required)
        if excluded:
            excluded_set = set()
            for ex_type in excluded:
                excluded_set.update(
                    self._component_manager.get_entities_with_component(ex_type)
                )
            entity_ids = [eid for eid in entity_ids if eid not in excluded_set]

        return QueryResult(
            entity_ids=entity_ids,
            required_types=list(required),
            excluded_types=list(excluded or []),
            total_matched=len(entity_ids),
        )

    def find_by_tag(self, tag: str) -> List[Entity]:
        """Find all entities with a specific tag."""
        entity_ids = self._tag_index.get(tag, set())
        return [self._entities[eid] for eid in entity_ids if eid in self._entities]

    def find_by_layer(self, layer: int) -> List[Entity]:
        """Find all entities on a specific layer."""
        entity_ids = self._layer_index.get(layer, set())
        return [self._entities[eid] for eid in entity_ids if eid in self._entities]

    # ---- Update Loop ----

    def update(self, delta_time: float) -> None:
        """Execute one frame of the ECS update loop."""
        if delta_time <= 0.0:
            return

        self._system_manager.update_all(delta_time, self._component_manager)
        self._process_destroyed()
        self._frame_count += 1

    # ---- Stats ----

    def get_stats(self) -> Dict[str, Any]:
        return {
            "entity_count": len(self._entities),
            "total_entities_created": self._entity_count,
            "pending_destroy": len(self._pending_destroy),
            "tag_count": len(self._tag_index),
            "layer_count": len(self._layer_index),
            "frame_count": self._frame_count,
            "component_manager": self._component_manager.get_stats(),
            "system_manager": self._system_manager.get_stats(),
        }

    def get_status(self) -> Dict[str, Any]:
        return self.get_stats()


# ---------------------------------------------------------------------------
# Convenience Accessor
# ---------------------------------------------------------------------------

def get_entity_component_engine() -> EntityComponentEngine:
    """Get the global EntityComponentEngine singleton instance."""
    return EntityComponentEngine()