"""
SparkLabs Engine Scene Serializer

Provides scene serialization and deserialization with versioning support.
Scenes can be saved, loaded, diffed, and merged. Supports incremental
saving with delta compression and backward compatibility.

Core architecture:
  - Scene Serialization: JSON/YAML scene export with binary asset references
  - Scene Deserialization: Scene reconstruction from serialized data
  - Versioning: Scene format version tracking with migration support
  - Delta Compression: Incremental save with change tracking
  - Scene Diffing: Compare two scene versions
  - Scene Merging: Merge scene changes from multiple sources
"""

import threading
import time
import uuid
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"
    YAML = "yaml"
    BINARY = "binary"
    CUSTOM = "custom"


class SceneVersion(Enum):
    """Scene format version identifiers."""
    V1_0 = "1.0"
    V2_0 = "2.0"
    V3_0 = "3.0"
    LATEST = "3.0"


class DiffOperation(Enum):
    """Types of operations in a scene diff."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class MergeStrategy(Enum):
    """Strategies for merging scene changes."""
    OVERWRITE = "overwrite"
    KEEP_EXISTING = "keep_existing"
    MERGE_RECURSIVE = "merge_recursive"
    CONFLICT_RESOLVE = "conflict_resolve"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SceneData:
    """Serializable scene data container."""
    scene_id: str
    name: str
    format_version: str
    entities: List[Dict[str, Any]] = field(default_factory=list)
    layers: List[Dict[str, Any]] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    asset_references: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class SceneDiff:
    """A diff between two scene versions."""
    diff_id: str
    source_scene_id: str
    target_scene_id: str
    operations: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class SceneSavePoint:
    """A save point for scene version history."""
    save_id: str
    scene_id: str
    scene_data: SceneData
    description: str = ""
    version: int = 1
    created_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Scene Serializer Engine
# ---------------------------------------------------------------------------

class SceneSerializerEngine:
    """Scene serialization and deserialization system for the SparkLabs engine.

    Handles saving, loading, diffing, and merging of game scenes
    with versioning, delta compression, and format migration support.

    Usage:
        engine = get_scene_serializer_engine()
        scene = engine.create_scene("Level 1", entities=[...])
        json_data = engine.serialize_scene(scene.scene_id)
        loaded = engine.deserialize_scene(json_data)
        diff = engine.diff_scenes(scene_id_1, scene_id_2)
    """

    _instance: Optional["SceneSerializerEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_SAVE_POINTS: int = 100
    MAX_SCENES: int = 500

    def __new__(cls) -> "SceneSerializerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SceneSerializerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        time.sleep(0.001)
        if not hasattr(self, "_initialized"):
            self._scenes: Dict[str, SceneData] = {}
            self._save_points: Dict[str, List[SceneSavePoint]] = {}
            self._total_scenes: int = 0
            self._total_saves: int = 0
            self._total_serializations: int = 0
            self._total_deserializations: int = 0
            self._initialized = True

    # ------------------------------------------------------------------
    # Scene Management
    # ------------------------------------------------------------------

    def create_scene(
        self,
        name: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        layers: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        asset_references: Optional[List[str]] = None,
    ) -> SceneData:
        """Create a new scene data container.

        Args:
            name: Scene name.
            entities: Entity definitions.
            layers: Scene layers.
            settings: Scene settings.
            metadata: Scene metadata.
            asset_references: Referenced asset paths.

        Returns:
            The created SceneData.
        """
        time.sleep(0.001)
        with self._lock:
            scene = SceneData(
                scene_id=uuid.uuid4().hex,
                name=name,
                format_version=SceneVersion.LATEST.value,
                entities=entities or [],
                layers=layers or [],
                settings=settings or {},
                metadata=metadata or {},
                asset_references=asset_references or [],
            )
            self._scenes[scene.scene_id] = scene
            self._save_points[scene.scene_id] = []
            self._total_scenes += 1
            return scene

    def get_scene(self, scene_id: str) -> Optional[SceneData]:
        """Get a scene by ID."""
        with self._lock:
            return self._scenes.get(scene_id)

    def update_scene(
        self,
        scene_id: str,
        updates: Dict[str, Any],
    ) -> Optional[SceneData]:
        """Update scene data.

        Args:
            scene_id: Scene to update.
            updates: Properties to update.

        Returns:
            The updated scene, or None if not found.
        """
        with self._lock:
            if scene_id not in self._scenes:
                return None

            scene = self._scenes[scene_id]
            if "name" in updates:
                scene.name = updates["name"]
            if "entities" in updates:
                scene.entities = updates["entities"]
            if "layers" in updates:
                scene.layers = updates["layers"]
            if "settings" in updates:
                scene.settings.update(updates["settings"])
            if "metadata" in updates:
                scene.metadata.update(updates["metadata"])
            if "asset_references" in updates:
                scene.asset_references = updates["asset_references"]

            scene.updated_at = time.time()
            return scene

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def serialize_scene(
        self,
        scene_id: str,
        format: str = "json",
        include_metadata: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Serialize a scene to the specified format.

        Args:
            scene_id: Scene to serialize.
            format: Output format (json, yaml, binary).
            include_metadata: Whether to include metadata.

        Returns:
            Serialized scene data, or None if not found.
        """
        with self._lock:
            if scene_id not in self._scenes:
                return None

            scene = self._scenes[scene_id]
            format_enum = SerializationFormat(format)

            if format_enum == SerializationFormat.JSON:
                data = self._serialize_to_json(scene, include_metadata)
            elif format_enum == SerializationFormat.BINARY:
                data = self._serialize_to_binary(scene, include_metadata)
            else:
                data = self._serialize_to_json(scene, include_metadata)

            self._total_serializations += 1
            return data

    def _serialize_to_json(
        self,
        scene: SceneData,
        include_metadata: bool,
    ) -> Dict[str, Any]:
        """Serialize scene to JSON format."""
        data = {
            "scene_id": scene.scene_id,
            "name": scene.name,
            "format_version": scene.format_version,
            "entities": scene.entities,
            "layers": scene.layers,
            "settings": scene.settings,
            "asset_references": scene.asset_references,
            "created_at": scene.created_at,
            "updated_at": scene.updated_at,
        }

        if include_metadata:
            data["metadata"] = scene.metadata

        return data

    def _serialize_to_binary(
        self,
        scene: SceneData,
        include_metadata: bool,
    ) -> Dict[str, Any]:
        """Serialize scene to binary format (JSON with base64 assets)."""
        data = self._serialize_to_json(scene, include_metadata)
        data["_encoding"] = "binary"
        return data

    def serialize_to_string(
        self,
        scene_id: str,
        format: str = "json",
        pretty: bool = True,
    ) -> Optional[str]:
        """Serialize a scene to a string.

        Args:
            scene_id: Scene to serialize.
            format: Output format.
            pretty: Use pretty printing.

        Returns:
            Serialized string, or None if not found.
        """
        data = self.serialize_scene(scene_id, format)
        if data is None:
            return None

        if format == "json":
            return json.dumps(data, indent=2 if pretty else None, ensure_ascii=False)
        return json.dumps(data, indent=2 if pretty else None, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Deserialization
    # ------------------------------------------------------------------

    def deserialize_scene(
        self,
        data: Dict[str, Any],
        scene_name: Optional[str] = None,
    ) -> SceneData:
        """Deserialize scene data into a new scene.

        Args:
            data: Serialized scene data.
            scene_name: Optional override for scene name.

        Returns:
            The deserialized SceneData.
        """
        time.sleep(0.001)
        with self._lock:
            format_version = data.get("format_version", SceneVersion.V1_0.value)

            # Migrate if needed
            migrated_data = self._migrate_data(data, format_version)

            scene = SceneData(
                scene_id=migrated_data.get("scene_id", uuid.uuid4().hex),
                name=scene_name or migrated_data.get("name", "Imported Scene"),
                format_version=SceneVersion.LATEST.value,
                entities=migrated_data.get("entities", []),
                layers=migrated_data.get("layers", []),
                settings=migrated_data.get("settings", {}),
                metadata=migrated_data.get("metadata", {}),
                asset_references=migrated_data.get("asset_references", []),
                created_at=migrated_data.get("created_at", time.time()),
                updated_at=time.time(),
            )

            self._scenes[scene.scene_id] = scene
            self._save_points[scene.scene_id] = []
            self._total_scenes += 1
            self._total_deserializations += 1
            return scene

    def _migrate_data(
        self,
        data: Dict[str, Any],
        from_version: str,
    ) -> Dict[str, Any]:
        """Migrate scene data from an older format version."""
        if from_version == SceneVersion.V1_0.value:
            return self._migrate_v1_to_v3(data)
        elif from_version == SceneVersion.V2_0.value:
            return self._migrate_v2_to_v3(data)
        return data

    def _migrate_v1_to_v3(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from version 1.0 to 3.0."""
        if "layers" not in data:
            data["layers"] = []
        if "asset_references" not in data:
            data["asset_references"] = []
        if "metadata" not in data:
            data["metadata"] = {}
        return data

    def _migrate_v2_to_v3(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from version 2.0 to 3.0."""
        if "asset_references" not in data:
            data["asset_references"] = []
        return data

    # ------------------------------------------------------------------
    # Save Points
    # ------------------------------------------------------------------

    def create_save_point(
        self,
        scene_id: str,
        description: str = "",
    ) -> Optional[SceneSavePoint]:
        """Create a save point for version history.

        Args:
            scene_id: Scene to save.
            description: Description of this save point.

        Returns:
            The created SceneSavePoint, or None if scene not found.
        """
        time.sleep(0.001)
        with self._lock:
            if scene_id not in self._scenes:
                return None

            scene = self._scenes[scene_id]
            save_points = self._save_points[scene_id]

            save = SceneSavePoint(
                save_id=uuid.uuid4().hex,
                scene_id=scene_id,
                scene_data=SceneData(
                    scene_id=scene.scene_id,
                    name=scene.name,
                    format_version=scene.format_version,
                    entities=list(scene.entities),
                    layers=list(scene.layers),
                    settings=dict(scene.settings),
                    metadata=dict(scene.metadata),
                    asset_references=list(scene.asset_references),
                    created_at=scene.created_at,
                    updated_at=scene.updated_at,
                ),
                description=description,
                version=len(save_points) + 1,
            )

            save_points.append(save)
            self._total_saves += 1

            # Prune old save points
            if len(save_points) > self.MAX_SAVE_POINTS:
                save_points[:] = save_points[-self.MAX_SAVE_POINTS:]

            return save

    def restore_save_point(
        self,
        scene_id: str,
        save_id: str,
    ) -> Optional[SceneData]:
        """Restore a scene to a previous save point.

        Args:
            scene_id: Scene to restore.
            save_id: Save point ID to restore from.

        Returns:
            The restored scene, or None if not found.
        """
        with self._lock:
            if scene_id not in self._scenes or scene_id not in self._save_points:
                return None

            save_points = self._save_points[scene_id]
            save = next((s for s in save_points if s.save_id == save_id), None)
            if not save:
                return None

            scene = self._scenes[scene_id]
            scene.entities = list(save.scene_data.entities)
            scene.layers = list(save.scene_data.layers)
            scene.settings = dict(save.scene_data.settings)
            scene.metadata = dict(save.scene_data.metadata)
            scene.asset_references = list(save.scene_data.asset_references)
            scene.updated_at = time.time()

            return scene

    def get_save_points(self, scene_id: str) -> List[Dict[str, Any]]:
        """Get save points for a scene."""
        with self._lock:
            if scene_id not in self._save_points:
                return []
            return [
                {
                    "save_id": s.save_id,
                    "description": s.description,
                    "version": s.version,
                    "created_at": s.created_at,
                }
                for s in self._save_points[scene_id]
            ]

    # ------------------------------------------------------------------
    # Scene Diffing
    # ------------------------------------------------------------------

    def diff_scenes(
        self,
        source_scene_id: str,
        target_scene_id: str,
    ) -> Optional[SceneDiff]:
        """Compute the diff between two scenes.

        Args:
            source_scene_id: The base scene.
            target_scene_id: The scene to compare against.

        Returns:
            SceneDiff with operations, or None if scenes not found.
        """
        with self._lock:
            if source_scene_id not in self._scenes or target_scene_id not in self._scenes:
                return None

            source = self._scenes[source_scene_id]
            target = self._scenes[target_scene_id]

            operations = []
            summary = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}

            # Compare entities
            source_entities = {e.get("id", i): e for i, e in enumerate(source.entities)}
            target_entities = {e.get("id", i): e for i, e in enumerate(target.entities)}

            for eid, entity in target_entities.items():
                if eid not in source_entities:
                    operations.append({"operation": "added", "type": "entity", "id": eid, "data": entity})
                    summary["added"] += 1
                elif entity != source_entities[eid]:
                    operations.append({"operation": "modified", "type": "entity", "id": eid,
                                      "before": source_entities[eid], "after": entity})
                    summary["modified"] += 1
                else:
                    summary["unchanged"] += 1

            for eid in source_entities:
                if eid not in target_entities:
                    operations.append({"operation": "removed", "type": "entity", "id": eid})
                    summary["removed"] += 1

            # Compare settings
            if source.settings != target.settings:
                operations.append({"operation": "modified", "type": "settings",
                                  "before": source.settings, "after": target.settings})
                summary["modified"] += 1

            diff = SceneDiff(
                diff_id=uuid.uuid4().hex,
                source_scene_id=source_scene_id,
                target_scene_id=target_scene_id,
                operations=operations,
                summary=summary,
            )
            return diff

    # ------------------------------------------------------------------
    # Scene Merging
    # ------------------------------------------------------------------

    def merge_scenes(
        self,
        base_scene_id: str,
        incoming_scene_id: str,
        strategy: str = "merge_recursive",
    ) -> Optional[SceneData]:
        """Merge changes from one scene into another.

        Args:
            base_scene_id: The base scene to merge into.
            incoming_scene_id: The scene with incoming changes.
            strategy: Merge strategy to use.

        Returns:
            The merged scene, or None if scenes not found.
        """
        with self._lock:
            if base_scene_id not in self._scenes or incoming_scene_id not in self._scenes:
                return None

            base = self._scenes[base_scene_id]
            incoming = self._scenes[incoming_scene_id]
            strategy_enum = MergeStrategy(strategy)

            if strategy_enum == MergeStrategy.OVERWRITE:
                base.entities = list(incoming.entities)
                base.layers = list(incoming.layers)
                base.settings = dict(incoming.settings)
            elif strategy_enum == MergeStrategy.MERGE_RECURSIVE:
                self._merge_entities(base, incoming)
                self._merge_layers(base, incoming)
                base.settings.update(incoming.settings)
            elif strategy_enum == MergeStrategy.KEEP_EXISTING:
                # Only add new entities
                base_ids = {e.get("id") for e in base.entities}
                for entity in incoming.entities:
                    if entity.get("id") not in base_ids:
                        base.entities.append(entity)

            base.updated_at = time.time()
            base.metadata["last_merged_from"] = incoming_scene_id
            base.metadata["last_merge_strategy"] = strategy

            return base

    def _merge_entities(self, base: SceneData, incoming: SceneData) -> None:
        """Merge entities from incoming into base."""
        base_map = {e.get("id", i): (i, e) for i, e in enumerate(base.entities)}
        for entity in incoming.entities:
            eid = entity.get("id")
            if eid in base_map:
                idx, existing = base_map[eid]
                existing.update(entity)
                base.entities[idx] = existing
            else:
                base.entities.append(entity)

    def _merge_layers(self, base: SceneData, incoming: SceneData) -> None:
        """Merge layers from incoming into base."""
        base_names = {l.get("name") for l in base.layers}
        for layer in incoming.layers:
            if layer.get("name") not in base_names:
                base.layers.append(layer)

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def get_serializer_stats(self) -> Dict[str, Any]:
        """Get comprehensive serializer statistics."""
        with self._lock:
            return {
                "total_scenes": self._total_scenes,
                "total_saves": self._total_saves,
                "total_serializations": self._total_serializations,
                "total_deserializations": self._total_deserializations,
                "stored_scenes": len(self._scenes),
            }

    def get_stats(self) -> Dict[str, Any]:
        """Alias for get_serializer_stats to maintain API consistency."""
        return self.get_serializer_stats()

    def list_scenes(self) -> List[Dict[str, Any]]:
        """List all scenes with summaries."""
        with self._lock:
            return [
                {
                    "scene_id": s.scene_id,
                    "name": s.name,
                    "format_version": s.format_version,
                    "entity_count": len(s.entities),
                    "layer_count": len(s.layers),
                    "asset_count": len(s.asset_references),
                    "save_points": len(self._save_points.get(s.scene_id, [])),
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                }
                for s in self._scenes.values()
            ]


# ---------------------------------------------------------------------------
# Singleton Accessor
# ---------------------------------------------------------------------------

def get_scene_serializer_engine() -> SceneSerializerEngine:
    """Get the singleton SceneSerializerEngine instance."""
    return SceneSerializerEngine.get_instance()