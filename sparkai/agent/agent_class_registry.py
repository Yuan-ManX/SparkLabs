"""
SparkLabs Agent - Class Registry

Meta-object reflection system for game entity types.
Enables AI agents to discover entity types, their properties,
methods, and inheritance relationships at runtime. Powers
intelligent code generation, validation, and auto-completion
by giving the agent a complete catalog of available game types.

Architecture:
  ClassRegistry
    |-- TypeDescriptor (name, properties, methods, base type)
    |-- PropertyDescriptor (name, dtype, default, constraints)
    |-- MethodDescriptor (name, params, return type)
    |-- InheritanceGraph (type hierarchy navigation)
    |-- TypeValidator (type compatibility checking)

Design mirrors the introspection capabilities found in
game engines where reflection enables editors, serialization,
and scripting bindings to work with any type dynamically.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class DataType(Enum):
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    VECTOR2 = "vector2"
    COLOR = "color"
    OBJECT = "object"
    ARRAY = "array"
    DICT = "dict"
    ANY = "any"


@dataclass
class PropertyDescriptor:
    name: str
    data_type: DataType
    default_value: Any = None
    description: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    enum_values: Optional[List[str]] = None
    required: bool = False
    read_only: bool = False
    tags: List[str] = field(default_factory=list)


@dataclass
class MethodDescriptor:
    name: str
    description: str = ""
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    return_type: DataType = DataType.ANY
    return_description: str = ""


@dataclass
class TypeDescriptor:
    type_name: str
    display_name: str
    category: str
    description: str
    base_type: Optional[str] = None
    properties: Dict[str, PropertyDescriptor] = field(default_factory=dict)
    methods: Dict[str, MethodDescriptor] = field(default_factory=dict)
    is_abstract: bool = False
    is_scriptable: bool = True
    tags: List[str] = field(default_factory=list)
    icon: str = "cube"

    def to_dict(self) -> dict:
        return {
            "type_name": self.type_name,
            "display_name": self.display_name,
            "category": self.category,
            "description": self.description,
            "base_type": self.base_type,
            "properties": {
                k: {
                    "name": v.name,
                    "data_type": v.data_type.value,
                    "default": v.default_value,
                    "description": v.description,
                    "required": v.required,
                    "read_only": v.read_only,
                }
                for k, v in self.properties.items()
            },
            "is_abstract": self.is_abstract,
            "tags": self.tags,
        }

    def get_all_properties(self, include_inherited: bool = False) -> List[PropertyDescriptor]:
        return list(self.properties.values())

    def get_all_methods(self) -> List[MethodDescriptor]:
        return list(self.methods.values())


class ClassRegistry:
    """
    Meta-object reflection system for game entity types.

    Game engines need runtime type information for editors,
    serialization, and scripting. This registry catalogs all
    entity types with their properties and methods, enabling
    AI agents to understand the available building blocks and
    generate correct, validated code.
    """

    _instance: Optional["ClassRegistry"] = None

    BUILTIN_CATEGORIES = [
        "entity",
        "component",
        "behavior",
        "resource",
        "node",
        "system",
        "ui_widget",
        "effect",
        "shader",
        "script",
    ]

    def __init__(self):
        self._types: Dict[str, TypeDescriptor] = {}
        self._category_index: Dict[str, List[str]] = {c: [] for c in self.BUILTIN_CATEGORIES}
        self._tag_index: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()
        self._register_builtins()

    @classmethod
    def get_instance(cls) -> "ClassRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_type(
        self,
        type_name: str,
        display_name: str,
        category: str,
        description: str = "",
        base_type: Optional[str] = None,
        is_abstract: bool = False,
        tags: Optional[List[str]] = None,
    ) -> TypeDescriptor:
        with self._lock:
            if type_name in self._types:
                return self._types[type_name]

            descriptor = TypeDescriptor(
                type_name=type_name,
                display_name=display_name,
                category=category,
                description=description,
                base_type=base_type,
                is_abstract=is_abstract,
                tags=tags or [],
            )
            self._types[type_name] = descriptor

            if category in self._category_index:
                self._category_index[category].append(type_name)
            else:
                self._category_index.setdefault(category, []).append(type_name)

            for tag in descriptor.tags:
                self._tag_index.setdefault(tag, set()).add(type_name)

            return descriptor

    def add_property(
        self,
        type_name: str,
        name: str,
        data_type: DataType,
        default_value: Any = None,
        description: str = "",
        **kwargs,
    ) -> bool:
        with self._lock:
            td = self._types.get(type_name)
            if not td:
                return False
            td.properties[name] = PropertyDescriptor(
                name=name,
                data_type=data_type,
                default_value=default_value,
                description=description,
                **kwargs,
            )
            return True

    def add_method(
        self,
        type_name: str,
        name: str,
        description: str = "",
        return_type: DataType = DataType.ANY,
        parameters: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        with self._lock:
            td = self._types.get(type_name)
            if not td:
                return False
            td.methods[name] = MethodDescriptor(
                name=name,
                description=description,
                return_type=return_type,
                parameters=parameters or [],
            )
            return True

    def get(self, type_name: str) -> Optional[TypeDescriptor]:
        return self._types.get(type_name)

    def get_base_chain(self, type_name: str) -> List[str]:
        chain = []
        current = type_name
        while current:
            td = self._types.get(current)
            if not td:
                break
            chain.append(current)
            current = td.base_type
            if current and current == chain[-1]:
                break
        return chain

    def inherits_from(self, type_name: str, base_name: str) -> bool:
        return base_name in self.get_base_chain(type_name)

    def find_by_category(self, category: str) -> List[TypeDescriptor]:
        names = self._category_index.get(category, [])
        return [self._types[n] for n in names if n in self._types]

    def find_by_tag(self, tag: str) -> List[TypeDescriptor]:
        names = self._tag_index.get(tag, set())
        return [self._types[n] for n in names if n in self._types]

    def search(self, query: str) -> List[TypeDescriptor]:
        q = query.lower()
        results = []
        for td in self._types.values():
            if (
                q in td.type_name.lower()
                or q in td.display_name.lower()
                or q in td.description.lower()
            ):
                results.append(td)
        return results

    def list_all(self) -> List[TypeDescriptor]:
        return list(self._types.values())

    def list_categories(self) -> List[str]:
        return sorted(self._category_index.keys())

    def _register_builtins(self) -> None:
        builtins = [
            ("Node2D", "Node 2D", "node", "Base 2D node with position/rotation/scale"),
            ("Sprite", "Sprite", "node", "2D sprite rendering node", "Node2D"),
            ("AnimatedSprite", "Animated Sprite", "node", "Frame-based animated sprite", "Sprite"),
            ("TileMap", "Tile Map", "node", "Grid-based tile map", "Node2D"),
            ("Camera2D", "Camera 2D", "node", "2D camera with scrolling", "Node2D"),
            ("CollisionShape2D", "Collision Shape 2D", "component", "Physics collision shape"),
            ("RigidBody2D", "Rigid Body 2D", "entity", "Physics-driven 2D body"),
            ("CharacterBody2D", "Character Body 2D", "entity", "Script-controlled 2D body"),
            ("Area2D", "Area 2D", "entity", "Detection zone for overlap checks"),
            ("ParticleEmitter2D", "Particle Emitter 2D", "effect", "2D particle effects"),
            ("Light2D", "Light 2D", "effect", "2D dynamic point light"),
            ("AudioStreamPlayer2D", "Audio Stream Player 2D", "system", "Positional 2D audio"),
            ("AnimationPlayer", "Animation Player", "system", "Keyframe animation controller"),
            ("Timer", "Timer", "system", "Countdown timer with signal"),
            ("TextureResource", "Texture", "resource", "2D image resource"),
            ("SpriteSheetResource", "Sprite Sheet", "resource", "Sprite sheet resource"),
            ("FontResource", "Font", "resource", "Bitmap font resource"),
            ("AudioResource", "Audio Clip", "resource", "Audio asset resource"),
            ("UILabel", "Label", "ui_widget", "Text display widget"),
            ("UIButton", "Button", "ui_widget", "Clickable button widget"),
            ("UIPanel", "Panel", "ui_widget", "Container panel widget"),
            ("UIProgressBar", "Progress Bar", "ui_widget", "Fill-based progress widget"),
            ("Script", "Script", "script", "Game logic script"),
            ("GameManager", "Game Manager", "script", "Global game state manager"),
            ("PlayerController", "Player Controller", "script", "Player input controller"),
            ("EnemyAI", "Enemy AI", "script", "NPC enemy behavior"),
        ]

        for entry in builtins:
            self.register_type(
                type_name=entry[0],
                display_name=entry[1],
                category=entry[2],
                description=entry[3],
                base_type=entry[4] if len(entry) > 4 else None,
            )

        self.add_property("Node2D", "position", DataType.VECTOR2, {"x": 0, "y": 0})
        self.add_property("Node2D", "rotation", DataType.FLOAT, 0.0)
        self.add_property("Node2D", "scale", DataType.VECTOR2, {"x": 1, "y": 1})
        self.add_property("Node2D", "visible", DataType.BOOL, True)
        self.add_property("Node2D", "z_index", DataType.INT, 0)
        self.add_property("Sprite", "texture", DataType.OBJECT)
        self.add_property("Sprite", "color", DataType.COLOR, "#FFFFFF")
        self.add_property("RigidBody2D", "mass", DataType.FLOAT, 1.0)
        self.add_property("RigidBody2D", "gravity_scale", DataType.FLOAT, 1.0)
        self.add_property("CharacterBody2D", "speed", DataType.FLOAT, 200.0)
        self.add_property("CharacterBody2D", "jump_velocity", DataType.FLOAT, -400.0)
        self.add_property("UIButton", "text", DataType.STRING, "Button")
        self.add_property("UIButton", "disabled", DataType.BOOL, False)

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "total_types": len(self._types),
                "categories": self.list_categories(),
                "types_by_category": {
                    c: len(names) for c, names in self._category_index.items()
                },
                "total_tags": len(self._tag_index),
            }

    def reset(self) -> None:
        with self._lock:
            self._types.clear()
            self._category_index = {c: [] for c in self.BUILTIN_CATEGORIES}
            self._tag_index.clear()
            self._register_builtins()


def get_class_registry() -> ClassRegistry:
    return ClassRegistry.get_instance()
