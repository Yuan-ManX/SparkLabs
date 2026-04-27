"""
SparkLabs ECS - Entity

Entities are lightweight containers with unique IDs.
They hold references to components but contain no logic themselves.
AI agents compose entities by adding/removing components dynamically.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Set, Type, TypeVar

from sparkai.engine.ecs.component import Component, ComponentRegistry

T = TypeVar("T", bound="Component")


class Entity:
    """
    Core entity in the ECS architecture.

    An entity is an identifier that groups related components.
    The composition of components defines what the entity IS.
    AI agents can query, add, and remove components at runtime.
    """

    def __init__(self, name: str = "Entity", entity_id: Optional[str] = None):
        self.id: str = entity_id or str(uuid.uuid4())
        self.name: str = name
        self._components: Dict[str, Component] = {}
        self._tags: Set[str] = set()
        self._parent: Optional[str] = None
        self._children: List[str] = []
        self.enabled: bool = True
        self._world_id: Optional[str] = None

    def add_component(self, component: Component) -> Component:
        component.entity_id = self.id
        self._components[component.component_type] = component
        return component

    def remove_component(self, component_type: str) -> Optional[Component]:
        return self._components.pop(component_type, None)

    def get_component(self, component_type: str) -> Optional[Component]:
        return self._components.get(component_type)

    def has_component(self, *component_types: str) -> bool:
        return all(ct in self._components for ct in component_types)

    def get_components(self) -> Dict[str, Component]:
        return dict(self._components)

    def add_tag(self, tag: str) -> None:
        self._tags.add(tag)

    def remove_tag(self, tag: str) -> None:
        self._tags.discard(tag)

    def has_tag(self, tag: str) -> bool:
        return tag in self._tags

    @property
    def tags(self) -> Set[str]:
        return self._tags.copy()

    def set_parent(self, parent_id: Optional[str]) -> None:
        self._parent = parent_id

    @property
    def parent(self) -> Optional[str]:
        return self._parent

    @property
    def children(self) -> List[str]:
        return list(self._children)

    def add_child(self, child_id: str) -> None:
        if child_id not in self._children:
            self._children.append(child_id)

    def remove_child(self, child_id: str) -> None:
        if child_id in self._children:
            self._children.remove(child_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "tags": list(self._tags),
            "parent": self._parent,
            "children": self._children,
            "components": {
                ct: comp.to_dict() for ct, comp in self._components.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        entity = cls(name=data.get("name", "Entity"), entity_id=data.get("id"))
        entity.enabled = data.get("enabled", True)
        entity._parent = data.get("parent")
        entity._children = data.get("children", [])
        for tag in data.get("tags", []):
            entity.add_tag(tag)
        for ct, comp_data in data.get("components", {}).items():
            comp = ComponentRegistry.create(ct, **{
                k: v for k, v in comp_data.items()
                if k not in ("component_type", "id", "entity_id")
            })
            if comp:
                if "id" in comp_data:
                    comp.id = comp_data["id"]
                entity.add_component(comp)
        return entity

    def __repr__(self) -> str:
        comps = ", ".join(self._components.keys())
        return f"Entity({self.name}, components=[{comps}])"


class EntityManager:
    """
    Manages all entities in a world.

    Provides efficient queries by component type and tag,
    supporting AI agent scene analysis and manipulation.
    """

    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        self._component_index: Dict[str, Set[str]] = {}
        self._tag_index: Dict[str, Set[str]] = {}

    def create_entity(self, name: str = "Entity") -> Entity:
        entity = Entity(name=name)
        self._entities[entity.id] = entity
        return entity

    def add_entity(self, entity: Entity) -> Entity:
        self._entities[entity.id] = entity
        for ct in entity.get_components():
            self._index_component(entity.id, ct)
        for tag in entity.tags:
            self._index_tag(entity.id, tag)
        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self._entities.get(entity_id)

    def remove_entity(self, entity_id: str) -> Optional[Entity]:
        entity = self._entities.pop(entity_id, None)
        if entity:
            for ct in entity.get_components():
                if ct in self._component_index:
                    self._component_index[ct].discard(entity_id)
            for tag in entity.tags:
                if tag in self._tag_index:
                    self._tag_index[tag].discard(entity_id)
        return entity

    def query(self, *component_types: str) -> List[Entity]:
        if not component_types:
            return list(self._entities.values())
        result_sets = []
        for ct in component_types:
            ids = self._component_index.get(ct, set())
            result_sets.append(ids)
        if not result_sets:
            return []
        common_ids = set.intersection(*result_sets) if result_sets else set()
        return [
            self._entities[eid] for eid in common_ids
            if eid in self._entities
        ]

    def query_by_tag(self, tag: str) -> List[Entity]:
        ids = self._tag_index.get(tag, set())
        return [self._entities[eid] for eid in ids if eid in self._entities]

    def find_by_name(self, name: str) -> Optional[Entity]:
        for entity in self._entities.values():
            if entity.name == name:
                return entity
        return None

    def _index_component(self, entity_id: str, component_type: str) -> None:
        if component_type not in self._component_index:
            self._component_index[component_type] = set()
        self._component_index[component_type].add(entity_id)

    def _index_tag(self, entity_id: str, tag: str) -> None:
        if tag not in self._tag_index:
            self._tag_index[tag] = set()
        self._tag_index[tag].add(entity_id)

    def on_component_added(self, entity_id: str, component_type: str) -> None:
        self._index_component(entity_id, component_type)

    def on_component_removed(self, entity_id: str, component_type: str) -> None:
        if component_type in self._component_index:
            self._component_index[component_type].discard(entity_id)

    def on_tag_added(self, entity_id: str, tag: str) -> None:
        self._index_tag(entity_id, tag)

    def on_tag_removed(self, entity_id: str, tag: str) -> None:
        if tag in self._tag_index:
            self._tag_index[tag].discard(entity_id)

    @property
    def count(self) -> int:
        return len(self._entities)

    def all_entities(self) -> List[Entity]:
        return list(self._entities.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "entities": [e.to_dict() for e in self._entities.values()],
        }
