"""
SparkAI Agent - Game Context

Maintains the complete state of the game being built by the AI engine.
The game context is the single source of truth for all game artifacts,
tracking entities, scenes, assets, pipeline progress, and project metadata.

Context architecture:
  GameContext
    |-- Project metadata (name, genre, description, version)
    |-- Entity registry (all game entities with components)
    |-- Scene graph (scene hierarchy and relationships)
    |-- Asset library (generated and imported assets)
    |-- Pipeline state (generation progress and results)
    |-- World model (game rules, physics, AI parameters)
    |-- Change history (undo/redo snapshots)

The context enables agents to reason about the current game state
and make informed decisions about what to create or modify next.
"""

from __future__ import annotations

import copy
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GameGenre(Enum):
    PLATFORMER = "platformer"
    RPG = "rpg"
    SHOOTER = "shooter"
    PUZZLE = "puzzle"
    STRATEGY = "strategy"
    ADVENTURE = "adventure"
    SIMULATION = "simulation"
    RACING = "racing"
    FIGHTING = "fighting"
    SANDBOX = "sandbox"
    HORROR = "horror"
    SPORTS = "sports"


class PipelinePhase(Enum):
    IDLE = "idle"
    ANALYZING = "analyzing"
    DESIGNING = "designing"
    SCAFFOLDING = "scaffolding"
    IMPLEMENTING = "implementing"
    INTEGRATING = "integrating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class AssetType(Enum):
    IMAGE = "image"
    TEXTURE = "texture"
    SPRITE = "sprite"
    MESH = "mesh"
    AUDIO = "audio"
    MUSIC = "music"
    SCRIPT = "script"
    PREFAB = "prefab"
    SCENE = "scene"
    FONT = "font"
    SHADER = "shader"
    ANIMATION = "animation"
    VIDEO = "video"


@dataclass
class EntityRecord:
    """Record of a game entity in the context."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    entity_type: str = "generic"
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    scene_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "position": self.position,
            "rotation": self.rotation,
            "scale": self.scale,
            "components": self.components,
            "tags": self.tags,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "scene_id": self.scene_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }


@dataclass
class SceneRecord:
    """Record of a game scene in the context."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    entities: List[str] = field(default_factory=list)
    systems: List[str] = field(default_factory=list)
    world_id: str = ""
    is_active: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "entities": self.entities,
            "systems": self.systems,
            "world_id": self.world_id,
            "is_active": self.is_active,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class AssetRecord:
    """Record of a game asset in the context."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    asset_type: AssetType = AssetType.IMAGE
    path: str = ""
    prompt: str = ""
    style: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "asset_type": self.asset_type.value,
            "path": self.path,
            "prompt": self.prompt,
            "style": self.style,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class PipelineState:
    """Current state of the game generation pipeline."""
    phase: PipelinePhase = PipelinePhase.IDLE
    current_stage: str = ""
    stages_completed: List[str] = field(default_factory=list)
    stage_results: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "current_stage": self.current_stage,
            "stages_completed": self.stages_completed,
            "stage_results": self.stage_results,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


@dataclass
class WorldModel:
    """Game world rules and parameters."""
    gravity: List[float] = field(default_factory=lambda: [0.0, -9.81, 0.0])
    time_scale: float = 1.0
    physics_enabled: bool = True
    collision_layers: Dict[str, int] = field(default_factory=dict)
    game_rules: Dict[str, Any] = field(default_factory=dict)
    ai_parameters: Dict[str, Any] = field(default_factory=dict)
    rendering_settings: Dict[str, Any] = field(default_factory=dict)
    audio_settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gravity": self.gravity,
            "time_scale": self.time_scale,
            "physics_enabled": self.physics_enabled,
            "collision_layers": self.collision_layers,
            "game_rules": self.game_rules,
            "ai_parameters": self.ai_parameters,
            "rendering_settings": self.rendering_settings,
            "audio_settings": self.audio_settings,
        }


@dataclass
class ContextSnapshot:
    """A snapshot of the game context for undo/redo."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""
    timestamp: float = field(default_factory=time.time)
    entity_count: int = 0
    scene_count: int = 0
    asset_count: int = 0
    data: Dict[str, Any] = field(default_factory=dict)


class GameContext:
    """
    Central game state manager for the SparkLabs AI-Native Game Engine.

    The GameContext maintains the complete state of the game being built,
    serving as the single source of truth for all game artifacts. Agents
    query the context to understand the current state and make decisions
    about what to create or modify.

    Features:
    - Entity registry with component tracking
    - Scene graph management
    - Asset library with metadata
    - Pipeline progress tracking
    - World model configuration
    - Undo/redo with context snapshots
    - Change notification via event bus integration
    """

    def __init__(self, max_snapshots: int = 50):
        self._project_name: str = "Untitled Project"
        self._project_description: str = ""
        self._genre: Optional[GameGenre] = None
        self._version: str = "0.1.0"
        self._entities: Dict[str, EntityRecord] = {}
        self._scenes: Dict[str, SceneRecord] = {}
        self._assets: Dict[str, AssetRecord] = {}
        self._pipeline = PipelineState()
        self._world_model = WorldModel()
        self._metadata: Dict[str, Any] = {}
        self._snapshots: List[ContextSnapshot] = []
        self._max_snapshots = max_snapshots
        self._snapshot_index: int = -1
        self._created_at: float = time.time()
        self._modified_at: float = time.time()

    # === Project Metadata ===

    def set_project_info(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        genre: Optional[GameGenre] = None,
        version: Optional[str] = None,
    ) -> None:
        if name is not None:
            self._project_name = name
        if description is not None:
            self._project_description = description
        if genre is not None:
            self._genre = genre
        if version is not None:
            self._version = version
        self._modified_at = time.time()

    def get_project_info(self) -> Dict[str, Any]:
        return {
            "name": self._project_name,
            "description": self._project_description,
            "genre": self._genre.value if self._genre else None,
            "version": self._version,
            "created_at": self._created_at,
            "modified_at": self._modified_at,
        }

    # === Entity Management ===

    def add_entity(self, entity: EntityRecord) -> EntityRecord:
        self._entities[entity.id] = entity
        if entity.scene_id and entity.scene_id in self._scenes:
            scene = self._scenes[entity.scene_id]
            if entity.id not in scene.entities:
                scene.entities.append(entity.id)
        self._modified_at = time.time()
        return entity

    def get_entity(self, entity_id: str) -> Optional[EntityRecord]:
        return self._entities.get(entity_id)

    def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> Optional[EntityRecord]:
        entity = self._entities.get(entity_id)
        if not entity:
            return None
        for key, value in updates.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        entity.modified_at = time.time()
        self._modified_at = time.time()
        return entity

    def remove_entity(self, entity_id: str) -> bool:
        if entity_id not in self._entities:
            return False
        entity = self._entities[entity_id]
        if entity.scene_id and entity.scene_id in self._scenes:
            scene = self._scenes[entity.scene_id]
            if entity_id in scene.entities:
                scene.entities.remove(entity_id)
        if entity.parent_id and entity.parent_id in self._entities:
            parent = self._entities[entity.parent_id]
            if entity_id in parent.children_ids:
                parent.children_ids.remove(entity_id)
        del self._entities[entity_id]
        self._modified_at = time.time()
        return True

    def list_entities(
        self,
        scene_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[EntityRecord]:
        entities = list(self._entities.values())
        if scene_id:
            entities = [e for e in entities if e.scene_id == scene_id]
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]
        if tags:
            entities = [e for e in entities if any(t in e.tags for t in tags)]
        return entities

    def find_entities_by_component(self, component_type: str) -> List[EntityRecord]:
        return [
            e for e in self._entities.values()
            if component_type in e.components
        ]

    # === Scene Management ===

    def add_scene(self, scene: SceneRecord) -> SceneRecord:
        self._scenes[scene.id] = scene
        self._modified_at = time.time()
        return scene

    def get_scene(self, scene_id: str) -> Optional[SceneRecord]:
        return self._scenes.get(scene_id)

    def remove_scene(self, scene_id: str) -> bool:
        if scene_id not in self._scenes:
            return False
        scene = self._scenes[scene_id]
        for entity_id in scene.entities:
            if entity_id in self._entities:
                self._entities[entity_id].scene_id = ""
        del self._scenes[scene_id]
        self._modified_at = time.time()
        return True

    def list_scenes(self) -> List[SceneRecord]:
        return list(self._scenes.values())

    def set_active_scene(self, scene_id: str) -> bool:
        for scene in self._scenes.values():
            scene.is_active = (scene.id == scene_id)
        return scene_id in self._scenes

    def get_active_scene(self) -> Optional[SceneRecord]:
        for scene in self._scenes.values():
            if scene.is_active:
                return scene
        return None

    # === Asset Management ===

    def add_asset(self, asset: AssetRecord) -> AssetRecord:
        self._assets[asset.id] = asset
        self._modified_at = time.time()
        return asset

    def get_asset(self, asset_id: str) -> Optional[AssetRecord]:
        return self._assets.get(asset_id)

    def remove_asset(self, asset_id: str) -> bool:
        if asset_id in self._assets:
            del self._assets[asset_id]
            self._modified_at = time.time()
            return True
        return False

    def list_assets(
        self,
        asset_type: Optional[AssetType] = None,
        tags: Optional[List[str]] = None,
    ) -> List[AssetRecord]:
        assets = list(self._assets.values())
        if asset_type:
            assets = [a for a in assets if a.asset_type == asset_type]
        if tags:
            assets = [a for a in assets if any(t in a.tags for t in tags)]
        return assets

    # === Pipeline State ===

    def get_pipeline_state(self) -> PipelineState:
        return self._pipeline

    def update_pipeline(
        self,
        phase: Optional[PipelinePhase] = None,
        current_stage: Optional[str] = None,
        stage_result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> PipelineState:
        if phase is not None:
            self._pipeline.phase = phase
            if phase == PipelinePhase.ANALYZING and self._pipeline.started_at is None:
                self._pipeline.started_at = time.time()
            if phase == PipelinePhase.COMPLETED:
                self._pipeline.completed_at = time.time()
        if current_stage is not None:
            self._pipeline.current_stage = current_stage
        if stage_result is not None and current_stage:
            self._pipeline.stage_results[current_stage] = stage_result
            if current_stage not in self._pipeline.stages_completed:
                self._pipeline.stages_completed.append(current_stage)
        if error is not None:
            self._pipeline.error = error
        self._modified_at = time.time()
        return self._pipeline

    def reset_pipeline(self) -> None:
        self._pipeline = PipelineState()

    # === World Model ===

    def get_world_model(self) -> WorldModel:
        return self._world_model

    def update_world_model(self, updates: Dict[str, Any]) -> WorldModel:
        for key, value in updates.items():
            if hasattr(self._world_model, key):
                setattr(self._world_model, key, value)
        self._modified_at = time.time()
        return self._world_model

    # === Snapshots (Undo/Redo) ===

    def create_snapshot(self, label: str = "") -> ContextSnapshot:
        snapshot = ContextSnapshot(
            label=label or f"Snapshot at {time.strftime('%H:%M:%S')}",
            entity_count=len(self._entities),
            scene_count=len(self._scenes),
            asset_count=len(self._assets),
            data={
                "project_name": self._project_name,
                "project_description": self._project_description,
                "genre": self._genre.value if self._genre else None,
                "version": self._version,
                "entities": {eid: e.to_dict() for eid, e in self._entities.items()},
                "scenes": {sid: s.to_dict() for sid, s in self._scenes.items()},
                "assets": {aid: a.to_dict() for aid, a in self._assets.items()},
                "world_model": self._world_model.to_dict(),
                "metadata": copy.deepcopy(self._metadata),
            },
        )
        if self._snapshot_index < len(self._snapshots) - 1:
            self._snapshots = self._snapshots[:self._snapshot_index + 1]
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]
        self._snapshot_index = len(self._snapshots) - 1
        return snapshot

    def restore_snapshot(self, snapshot_id: str) -> bool:
        snapshot = None
        for i, s in enumerate(self._snapshots):
            if s.id == snapshot_id:
                snapshot = s
                self._snapshot_index = i
                break
        if not snapshot:
            return False
        data = snapshot.data
        self._project_name = data.get("project_name", "Untitled Project")
        self._project_description = data.get("project_description", "")
        genre_val = data.get("genre")
        self._genre = GameGenre(genre_val) if genre_val else None
        self._version = data.get("version", "0.1.0")
        self._entities = {
            eid: EntityRecord(**edata) for eid, edata in data.get("entities", {}).items()
        }
        self._scenes = {
            sid: SceneRecord(**sdata) for sid, sdata in data.get("scenes", {}).items()
        }
        self._assets = {
            aid: self._dict_to_asset_record(adata)
            for aid, adata in data.get("assets", {}).items()
        }
        wm = data.get("world_model", {})
        for key, value in wm.items():
            if hasattr(self._world_model, key):
                setattr(self._world_model, key, value)
        self._metadata = data.get("metadata", {})
        self._modified_at = time.time()
        return True

    def _dict_to_asset_record(self, data: Dict[str, Any]) -> AssetRecord:
        at = data.pop("asset_type", "image")
        if isinstance(at, str):
            try:
                data["asset_type"] = AssetType(at)
            except ValueError:
                data["asset_type"] = AssetType.IMAGE
        else:
            data["asset_type"] = at
        return AssetRecord(**data)

    def list_snapshots(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": s.id,
                "label": s.label,
                "timestamp": s.timestamp,
                "entity_count": s.entity_count,
                "scene_count": s.scene_count,
                "asset_count": s.asset_count,
            }
            for s in self._snapshots
        ]

    def can_undo(self) -> bool:
        return self._snapshot_index > 0

    def can_redo(self) -> bool:
        return self._snapshot_index < len(self._snapshots) - 1

    def undo(self) -> bool:
        if not self.can_undo():
            return False
        self._snapshot_index -= 1
        snapshot = self._snapshots[self._snapshot_index]
        return self.restore_snapshot(snapshot.id)

    def redo(self) -> bool:
        if not self.can_redo():
            return False
        self._snapshot_index += 1
        snapshot = self._snapshots[self._snapshot_index]
        return self.restore_snapshot(snapshot.id)

    # === Context Summary ===

    def get_summary(self) -> Dict[str, Any]:
        return {
            "project": self.get_project_info(),
            "entity_count": len(self._entities),
            "scene_count": len(self._scenes),
            "asset_count": len(self._assets),
            "pipeline": self._pipeline.to_dict(),
            "world_model": self._world_model.to_dict(),
            "snapshot_count": len(self._snapshots),
            "can_undo": self.can_undo(),
            "can_redo": self.can_redo(),
        }

    def get_full_state(self) -> Dict[str, Any]:
        return {
            "project": self.get_project_info(),
            "entities": {eid: e.to_dict() for eid, e in self._entities.items()},
            "scenes": {sid: s.to_dict() for sid, s in self._scenes.items()},
            "assets": {aid: a.to_dict() for aid, a in self._assets.items()},
            "pipeline": self._pipeline.to_dict(),
            "world_model": self._world_model.to_dict(),
            "metadata": self._metadata,
        }

    def reset(self) -> None:
        """Reset the entire game context to a fresh state."""
        self._project_name = "Untitled Project"
        self._project_description = ""
        self._genre = None
        self._version = "0.1.0"
        self._entities.clear()
        self._scenes.clear()
        self._assets.clear()
        self._pipeline = PipelineState()
        self._world_model = WorldModel()
        self._metadata.clear()
        self._snapshots.clear()
        self._snapshot_index = -1
        self._created_at = time.time()
        self._modified_at = time.time()


_global_context: Optional[GameContext] = None


def get_game_context() -> GameContext:
    """Get the global GameContext singleton."""
    global _global_context
    if _global_context is None:
        _global_context = GameContext()
    return _global_context


def reset_game_context() -> None:
    """Reset the global GameContext singleton."""
    global _global_context
    _global_context = None
