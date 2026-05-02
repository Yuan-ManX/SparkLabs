"""
SparkLabs Engine - Serialization System

Bi-directional scene and entity serialization for AI-generated
game content. Supports JSON interchange, binary packing for
runtime performance, and schema versioning for forward/backward
compatibility between engine versions.

Architecture:
  Serializer
    |-- SceneSerializer (full scene graph with entity hierarchy)
    |-- EntitySerializer (component data, transforms, properties)
    |-- AssetSerializer (texture references, audio clips, prefabs)
    |-- SchemaValidator (version-based field migration)

Serialization Formats:
  - JSON_READABLE: human-readable, AI-friendly interchange format
  - JSON_COMPACT: minimal JSON for network transfer
  - BINARY_BLOB: optimized for runtime loading/saving
  - YAML_LAYOUT: level design layout format

Usage:
    ser = Serializer(schema_version=2)
    json_str = ser.serialize_scene(scene, format="json_readable")
    loaded_scene = ser.deserialize_scene(json_str)
    binary_blob = ser.serialize_to_binary(world_data)
"""
from __future__ import annotations

import json
import struct
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class SerialFormat(Enum):
    JSON_READABLE = auto()
    JSON_COMPACT = auto()
    BINARY_BLOB = auto()
    YAML_LAYOUT = auto()


@dataclass
class SchemaVersion:
    major: int = 1
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "SchemaVersion") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SchemaVersion):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def is_compatible(self, other: "SchemaVersion") -> bool:
        return self.major == other.major


@dataclass
class SerializedEntity:
    id: str = ""
    name: str = ""
    type: str = "entity"
    parent_id: Optional[str] = None
    position: Tuple[float, float] = (0.0, 0.0)
    rotation: float = 0.0
    scale: Tuple[float, float] = (1.0, 1.0)
    visible: bool = True
    locked: bool = False
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)


@dataclass
class SerializedScene:
    id: str = ""
    name: str = ""
    schema_version: SchemaVersion = field(default_factory=SchemaVersion)
    entities: Dict[str, SerializedEntity] = field(default_factory=dict)
    root_entities: List[str] = field(default_factory=list)
    scene_properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    modified_at: float = 0.0


class Serializer:
    """
    Game content serializer supporting multiple formats.

    Provides schema-aware serialization and deserialization
    of scenes and entities. Supports version-based field
    migration for content created in older engine versions.
    """

    _instance: Optional["Serializer"] = None

    def __init__(self, schema_version: SchemaVersion | None = None):
        self._schema_version = schema_version or SchemaVersion(2, 0, 0)
        self._migrations: Dict[str, List[callable]] = {}
        self._register_default_migrations()

    @classmethod
    def get_instance(cls) -> "Serializer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def schema_version(self) -> SchemaVersion:
        return self._schema_version

    def serialize_scene(
        self,
        scene: Any,
        format: SerialFormat = SerialFormat.JSON_READABLE,
        indent: int = 2,
    ) -> str:
        serialized = self._extract_scene_data(scene)
        self._attach_schema_header(serialized)

        if format == SerialFormat.JSON_READABLE:
            return json.dumps(serialized, indent=indent, ensure_ascii=False)
        elif format == SerialFormat.JSON_COMPACT:
            return json.dumps(serialized, separators=(",", ":"), ensure_ascii=False)
        else:
            compact = json.dumps(serialized, separators=(",", ":"), ensure_ascii=False)
            return compact

    def deserialize_scene(
        self,
        data: str,
        validate_schema: bool = True,
    ) -> SerializedScene:
        source = json.loads(data)
        schema_ver = self._extract_schema_version(source)

        if validate_schema and schema_ver is not None:
            if schema_ver.major > self._schema_version.major:
                raise ValueError(
                    f"Schema version {schema_ver} is newer than engine version "
                    f"{self._schema_version}. Content may not be compatible."
                )

        if schema_ver is not None and schema_ver < self._schema_version:
            source = self._migrate_content(source, schema_ver)

        return self._build_scene_from_data(source)

    def serialize_entity(self, entity: Any, format: SerialFormat = SerialFormat.JSON_COMPACT) -> str:
        entity_data = self._extract_entity_data(entity)
        if format == SerialFormat.JSON_READABLE:
            return json.dumps(entity_data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(entity_data, separators=(",", ":"), ensure_ascii=False)

    def deserialize_entity(self, data: str) -> SerializedEntity:
        raw = json.loads(data)
        return SerializedEntity(
            id=raw.get("id", ""),
            name=raw.get("name", ""),
            type=raw.get("type", "entity"),
            parent_id=raw.get("parent_id"),
            position=tuple(raw.get("position", (0.0, 0.0))),
            rotation=raw.get("rotation", 0.0),
            scale=tuple(raw.get("scale", (1.0, 1.0))),
            visible=raw.get("visible", True),
            locked=raw.get("locked", False),
            components=raw.get("components", {}),
            properties=raw.get("properties", {}),
            tags=raw.get("tags", []),
            children=raw.get("children", []),
        )

    def serialize_to_binary(self, scene: Any) -> bytes:
        compact = self.serialize_scene(scene, format=SerialFormat.JSON_COMPACT)
        encoded = compact.encode("utf-8")
        header = struct.pack(
            "!4sIII",
            b"SPRK",
            self._schema_version.major,
            self._schema_version.minor,
            self._schema_version.patch,
        )
        return header + encoded

    def deserialize_from_binary(self, blob: bytes) -> SerializedScene:
        if len(blob) < 16:
            raise ValueError("Binary blob too short for header")
        magic, _, _, _ = struct.unpack("!4sIII", blob[:16])
        if magic != b"SPRK":
            raise ValueError("Not a SparkLabs binary blob")
        json_bytes = blob[16:]
        return self.deserialize_scene(json_bytes.decode("utf-8"))

    def serialize_to_yaml(self, scene: Any) -> str:
        data = self._extract_scene_data(scene)
        return self._format_as_yaml(data)

    def get_schema_info(self) -> Dict[str, Any]:
        return {
            "current_version": str(self._schema_version),
            "format": "SparkLabs Scene Graph",
            "supported_formats": ["json_readable", "json_compact", "binary_blob", "yaml_layout"],
            "migration_paths": list(self._migrations.keys()),
            "entity_properties": [
                "id", "name", "type", "parent_id", "position", "rotation",
                "scale", "visible", "locked", "components", "properties",
                "tags", "children",
            ],
        }

    def _extract_scene_data(self, scene: Any) -> Dict[str, Any]:
        if isinstance(scene, dict):
            return scene
        if hasattr(scene, "to_dict"):
            return scene.to_dict()
        if isinstance(scene, SerializedScene):
            return {
                "id": scene.id,
                "name": scene.name,
                "entities": {
                    eid: self._entity_to_dict(ent)
                    for eid, ent in scene.entities.items()
                },
                "root_entities": scene.root_entities,
                "scene_properties": scene.scene_properties,
                "metadata": scene.metadata,
            }
        return {
            "id": getattr(scene, "id", str(uuid.uuid4())),
            "name": getattr(scene, "name", "Untitled"),
            "entities": {},
            "root_entities": [],
            "scene_properties": {},
            "metadata": {},
        }

    def _extract_entity_data(self, entity: Any) -> Dict[str, Any]:
        if isinstance(entity, dict):
            return entity
        if isinstance(entity, SerializedEntity):
            return self._entity_to_dict(entity)
        return {
            "id": getattr(entity, "id", str(uuid.uuid4())),
            "name": getattr(entity, "name", "Entity"),
            "type": getattr(entity, "type", "entity"),
            "position": getattr(entity, "position", (0.0, 0.0)),
            "rotation": getattr(entity, "rotation", 0.0),
        }

    def _entity_to_dict(self, entity: SerializedEntity) -> Dict[str, Any]:
        return {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type,
            "parent_id": entity.parent_id,
            "position": list(entity.position),
            "rotation": entity.rotation,
            "scale": list(entity.scale),
            "visible": entity.visible,
            "locked": entity.locked,
            "components": entity.components,
            "properties": entity.properties,
            "tags": entity.tags,
            "children": entity.children,
        }

    def _attach_schema_header(self, data: Dict[str, Any]) -> None:
        data["schema_version"] = str(self._schema_version)
        data["engine"] = "SparkLabs AI Engine"

    def _extract_schema_version(self, data: Dict[str, Any]) -> Optional[SchemaVersion]:
        ver_str = data.get("schema_version")
        if not ver_str:
            return None
        parts = ver_str.split(".")
        if len(parts) != 3:
            return None
        try:
            return SchemaVersion(int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            return None

    def _build_scene_from_data(self, data: Dict[str, Any]) -> SerializedScene:
        entities: Dict[str, SerializedEntity] = {}
        for eid, raw in data.get("entities", {}).items():
            entities[eid] = SerializedEntity(
                id=raw.get("id", eid),
                name=raw.get("name", "Entity"),
                type=raw.get("type", "entity"),
                parent_id=raw.get("parent_id"),
                position=tuple(raw.get("position", (0.0, 0.0))),
                rotation=raw.get("rotation", 0.0),
                scale=tuple(raw.get("scale", (1.0, 1.0))),
                visible=raw.get("visible", True),
                locked=raw.get("locked", False),
                components=raw.get("components", {}),
                properties=raw.get("properties", {}),
                tags=raw.get("tags", []),
                children=raw.get("children", []),
            )
        return SerializedScene(
            id=data.get("id", ""),
            name=data.get("name", ""),
            entities=entities,
            root_entities=data.get("root_entities", []),
            scene_properties=data.get("scene_properties", {}),
            metadata=data.get("metadata", {}),
        )

    def _migrate_content(self, data: Dict[str, Any], from_version: SchemaVersion) -> Dict[str, Any]:
        mig_key = str(from_version)
        if mig_key in self._migrations:
            for migration_fn in self._migrations[mig_key]:
                try:
                    data = migration_fn(data)
                except Exception:
                    continue
        return data

    def _register_default_migrations(self) -> None:
        def v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:
            for ent in data.get("entities", {}).values():
                if "components" not in ent:
                    ent["components"] = {}
                if "tags" not in ent:
                    ent["tags"] = []
                if "children" not in ent:
                    ent["children"] = []
            return data

        self._migrations["1.0.0"] = [v1_to_v2]

    def _format_as_yaml(self, data: Dict[str, Any], indent: int = 0) -> str:
        lines = []
        prefix = "  " * indent

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._format_as_yaml(value, indent + 1))
                elif isinstance(value, str):
                    lines.append(f'{prefix}{key}: "{value}"')
                elif isinstance(value, bool):
                    lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
                elif value is None:
                    lines.append(f"{prefix}{key}: null")
                else:
                    lines.append(f"{prefix}{key}: {value}")
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}- ")
                    lines.append(self._format_as_yaml(item, indent + 2))
                else:
                    lines.append(f"{prefix}- {item}")
        else:
            lines.append(f"{prefix}{data}")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "schema_version": str(self._schema_version),
            "migration_count": len(self._migrations),
            "supported_formats": [f.name.lower() for f in SerialFormat],
        }


def get_serializer() -> Serializer:
    return Serializer.get_instance()
