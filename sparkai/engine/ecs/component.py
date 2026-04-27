"""
SparkLabs ECS - Component Base and Registry

Components are pure data containers. They define what an entity IS,
not what it DOES. Systems handle behavior.

Each component type is registered globally so that systems can query
entities by component type, and AI agents can reason about
component composition.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, TypeVar

T = TypeVar("T", bound="Component")


class Component:
    """
    Base class for all ECS components.

    Components hold data only. They should not contain logic.
    AI agents can read and write component data to control entities.
    """

    component_type: str = "component"

    def __init__(self, **kwargs: Any):
        self.id: str = str(uuid.uuid4())
        self.entity_id: Optional[str] = None
        self.enabled: bool = True
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "component_type": self.component_type,
            "id": self.id,
            "entity_id": self.entity_id,
            "enabled": self.enabled,
        }
        for key, value in self.__dict__.items():
            if key not in ("id", "entity_id", "enabled", "component_type"):
                if hasattr(value, "to_dict"):
                    result[key] = value.to_dict()
                elif isinstance(value, (list, tuple)):
                    result[key] = [
                        item.to_dict() if hasattr(item, "to_dict") else item
                        for item in value
                    ]
                else:
                    result[key] = value
        return result

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        filtered = {
            k: v for k, v in data.items()
            if k not in ("component_type", "id", "entity_id")
        }
        instance = cls(**filtered)
        if "id" in data:
            instance.id = data["id"]
        if "entity_id" in data:
            instance.entity_id = data["entity_id"]
        if "enabled" in data:
            instance.enabled = data["enabled"]
        return instance

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id[:8]}, entity={self.entity_id})"


class ComponentRegistry:
    """
    Global registry for component types.

    Allows systems and AI agents to discover available component types,
    create components by type name, and inspect component schemas.
    """

    _types: Dict[str, Type[Component]] = {}

    @classmethod
    def register(cls, component_class: Type[Component]) -> Type[Component]:
        type_name = component_class.component_type
        cls._types[type_name] = component_class
        return component_class

    @classmethod
    def get(cls, type_name: str) -> Optional[Type[Component]]:
        return cls._types.get(type_name)

    @classmethod
    def create(cls, type_name: str, **kwargs: Any) -> Optional[Component]:
        component_class = cls._types.get(type_name)
        if component_class:
            return component_class(**kwargs)
        return None

    @classmethod
    def list_types(cls) -> List[str]:
        return list(cls._types.keys())

    @classmethod
    def get_schema(cls, type_name: str) -> Optional[Dict[str, Any]]:
        component_class = cls._types.get(type_name)
        if not component_class:
            return None
        instance = component_class()
        return instance.to_dict()

    @classmethod
    def clear(cls) -> None:
        cls._types.clear()


def component(cls: Type[Component]) -> Type[Component]:
    """Decorator to auto-register a component class."""
    ComponentRegistry.register(cls)
    return cls
