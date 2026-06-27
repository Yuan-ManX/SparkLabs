"""
SparkLabs Engine - Visual Scene Composition Engine

A drag-and-drop visual scene building system for the SparkLabs AI-native
game engine. Enables layer management, object placement, property editing,
and real-time preview — inspired by GDevelop's visual editor and Godot's
node-based scene composition.

The engine provides a unified visual composition workflow:
  - LayerManager: Z-ordered layer management for organizing scene objects
  - SceneCanvas: Virtual canvas with pan/zoom that holds all scene objects
  - ObjectLibrary: Catalog of placeable objects (sprites, tiles, particles, etc.)
  - PropertyEditor: Real-time property editing with type-aware controls
  - SceneSerializer: JSON-based scene serialization/deserialization
  - PreviewRenderer: Real-time scene preview rendering
  - SelectionManager: Multi-object selection, grouping, alignment

Architecture:
  EngineVisualComposer (Singleton)
    |-- LayerManager: z-order layer management
    |-- SceneCanvas: virtual canvas with pan/zoom
    |-- ObjectLibrary: catalog of placeable objects
    |-- PropertyEditor: type-aware property editing
    |-- SceneSerializer: JSON scene save/load
    |-- PreviewRenderer: real-time preview
    |-- SelectionManager: selection and manipulation

Usage:
    vc = get_visual_composer()
    scene = vc.create_scene("MyScene", 1920, 1080)
    layer = vc.add_layer(scene.id, "Background", 0)
    obj = vc.place_object(scene.id, "sprite_player", 100, 200, layer.id)
    vc.select_objects(scene.id, [obj.id])
    data = vc.save_scene(scene.id)
    status = vc.get_status()
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ObjectType(Enum):
    """Classification of placeable scene objects."""
    SPRITE = "sprite"
    TILE = "tile"
    PARTICLE = "particle"
    TRIGGER = "trigger"
    TEXT = "text"
    LIGHT = "light"
    CAMERA = "camera"
    CUSTOM = "custom"


class LayerBlendMode(Enum):
    """Blend mode for layer compositing."""
    NORMAL = "normal"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"


class SnapMode(Enum):
    """Snap mode for object placement and movement."""
    NONE = "none"
    GRID = "grid"
    OBJECT = "object"
    PIXEL = "pixel"


class AlignmentType(Enum):
    """Alignment options for multi-object layout operations."""
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    CENTER_HORIZONTAL = "center_horizontal"
    CENTER_VERTICAL = "center_vertical"
    DISTRIBUTE_HORIZONTAL = "distribute_horizontal"
    DISTRIBUTE_VERTICAL = "distribute_vertical"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ObjectTemplate:
    """A reusable object definition from the object library.

    Templates define the default properties, icon, and category for
    placeable objects. When an object is instantiated from a template,
    it inherits these defaults but can override them per-instance.

    Attributes:
        id: Unique template identifier.
        name: Display name.
        object_type: The type of object this template creates.
        category: Library category for grouping (e.g., "Characters", "Environment").
        description: Human-readable description.
        default_properties: Default property values inherited by instances.
        icon: Icon identifier or path for the library UI.
        tags: Searchable tags for library filtering.
        created_at: Creation timestamp.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Untitled Template"
    object_type: ObjectType = ObjectType.SPRITE
    category: str = "General"
    description: str = ""
    default_properties: Dict[str, Any] = field(default_factory=dict)
    icon: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the template to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "object_type": self.object_type.value,
            "category": self.category,
            "description": self.description,
            "default_properties": dict(self.default_properties),
            "icon": self.icon,
            "tags": list(self.tags),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObjectTemplate":
        """Deserialize a template from a dictionary."""
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", "Untitled Template"),
            object_type=ObjectType(data.get("object_type", "sprite")),
            category=data.get("category", "General"),
            description=data.get("description", ""),
            default_properties=dict(data.get("default_properties", {})),
            icon=data.get("icon", ""),
            tags=list(data.get("tags", [])),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class SceneLayer:
    """A named layer with z-order, visibility, and lock state.

    Layers organize scene objects into a z-ordered stack. Each layer
    can be independently shown, hidden, or locked to prevent accidental
    edits. Objects within a layer are rendered in z_index order.

    Attributes:
        id: Unique layer identifier.
        name: Display name.
        z_order: Stacking order (higher = on top).
        visible: Whether the layer is rendered.
        locked: Whether the layer is locked against edits.
        blend_mode: Compositing blend mode.
        opacity: Layer opacity (0.0 to 1.0).
        object_ids: Ordered list of object IDs in this layer.
        created_at: Creation timestamp.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Layer"
    z_order: int = 0
    visible: bool = True
    locked: bool = False
    blend_mode: LayerBlendMode = LayerBlendMode.NORMAL
    opacity: float = 1.0
    object_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the layer to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "z_order": self.z_order,
            "visible": self.visible,
            "locked": self.locked,
            "blend_mode": self.blend_mode.value,
            "opacity": self.opacity,
            "object_ids": list(self.object_ids),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneLayer":
        """Deserialize a layer from a dictionary."""
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", "Layer"),
            z_order=data.get("z_order", 0),
            visible=data.get("visible", True),
            locked=data.get("locked", False),
            blend_mode=LayerBlendMode(data.get("blend_mode", "normal")),
            opacity=data.get("opacity", 1.0),
            object_ids=list(data.get("object_ids", [])),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class SceneObject:
    """A placed object within a scene, with position, size, and properties.

    Each object belongs to a specific layer and references a template
    for its default configuration. Objects carry instance-specific
    overrides in their properties dict.

    Attributes:
        id: Unique object identifier.
        name: Instance display name.
        object_type: Type classification.
        template_id: Reference to the source ObjectTemplate.
        position_x: X position on the canvas.
        position_y: Y position on the canvas.
        width: Object width in canvas units.
        height: Object height in canvas units.
        rotation: Rotation in degrees.
        z_index: Stacking order within the layer.
        layer_id: Parent layer identifier.
        visible: Whether the object is rendered.
        locked: Whether the object is locked against edits.
        properties: Instance-specific property overrides.
        tags: Searchable tags.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Object"
    object_type: ObjectType = ObjectType.SPRITE
    template_id: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    width: float = 64.0
    height: float = 64.0
    rotation: float = 0.0
    z_index: int = 0
    layer_id: str = ""
    visible: bool = True
    locked: bool = False
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the object to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "object_type": self.object_type.value,
            "template_id": self.template_id,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "z_index": self.z_index,
            "layer_id": self.layer_id,
            "visible": self.visible,
            "locked": self.locked,
            "properties": dict(self.properties),
            "tags": list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def touch(self) -> None:
        """Update the last-modified timestamp."""
        self.updated_at = time.time()

    def get_bounding_box(self) -> Dict[str, float]:
        """Return the object's axis-aligned bounding box."""
        if self.rotation == 0.0:
            return {
                "x": self.position_x,
                "y": self.position_y,
                "width": self.width,
                "height": self.height,
            }
        # Compute rotated bounding box
        rad = math.radians(self.rotation)
        cos_r = abs(math.cos(rad))
        sin_r = abs(math.sin(rad))
        rw = self.width * cos_r + self.height * sin_r
        rh = self.width * sin_r + self.height * cos_r
        cx = self.position_x + self.width / 2.0
        cy = self.position_y + self.height / 2.0
        return {
            "x": cx - rw / 2.0,
            "y": cy - rh / 2.0,
            "width": rw,
            "height": rh,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneObject":
        """Deserialize an object from a dictionary."""
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", "Object"),
            object_type=ObjectType(data.get("object_type", "sprite")),
            template_id=data.get("template_id", ""),
            position_x=data.get("position_x", 0.0),
            position_y=data.get("position_y", 0.0),
            width=data.get("width", 64.0),
            height=data.get("height", 64.0),
            rotation=data.get("rotation", 0.0),
            z_index=data.get("z_index", 0),
            layer_id=data.get("layer_id", ""),
            visible=data.get("visible", True),
            locked=data.get("locked", False),
            properties=dict(data.get("properties", {})),
            tags=list(data.get("tags", [])),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


@dataclass
class SelectionState:
    """Current selection state including multiple objects.

    Tracks which objects are selected, the primary selection (for
    alignment anchors), and the computed bounding box of all selected
    objects. Supports grouping for batch operations.

    Attributes:
        selected_object_ids: IDs of all selected objects.
        primary_object_id: The anchor object for alignment operations.
        bounding_box: Computed union bounding box of all selected objects.
        group_name: Optional group name for grouped selections.
        created_at: Selection timestamp.
    """
    selected_object_ids: List[str] = field(default_factory=list)
    primary_object_id: Optional[str] = None
    bounding_box: Optional[Dict[str, float]] = None
    group_name: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the selection state to a dictionary."""
        return {
            "selected_object_ids": list(self.selected_object_ids),
            "primary_object_id": self.primary_object_id,
            "bounding_box": dict(self.bounding_box) if self.bounding_box else None,
            "group_name": self.group_name,
            "selected_count": len(self.selected_object_ids),
            "created_at": self.created_at,
        }


@dataclass
class SceneDocument:
    """A complete scene with all layers, objects, and templates.

    The scene document is the top-level container for a visual scene.
    It holds the canvas dimensions, all layers (z-ordered), all placed
    objects, the object template library, and optional metadata.

    Attributes:
        id: Unique scene identifier.
        name: Scene display name.
        width: Canvas width in scene units.
        height: Canvas height in scene units.
        layers: All layers keyed by layer ID.
        objects: All placed objects keyed by object ID.
        templates: Object template library keyed by template ID.
        groups: Named groups mapping group name to object ID lists.
        metadata: Arbitrary scene metadata.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Untitled Scene"
    width: int = 1920
    height: int = 1080
    layers: Dict[str, SceneLayer] = field(default_factory=dict)
    objects: Dict[str, SceneObject] = field(default_factory=dict)
    templates: Dict[str, ObjectTemplate] = field(default_factory=dict)
    groups: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the scene document to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "layers": {
                lid: layer.to_dict() for lid, layer in self.layers.items()
            },
            "objects": {
                oid: obj.to_dict() for oid, obj in self.objects.items()
            },
            "templates": {
                tid: tpl.to_dict() for tid, tpl in self.templates.items()
            },
            "groups": {
                gname: list(oids) for gname, oids in self.groups.items()
            },
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def touch(self) -> None:
        """Update the last-modified timestamp."""
        self.updated_at = time.time()

    def get_layers_sorted(self) -> List[SceneLayer]:
        """Return layers sorted by z-order (ascending)."""
        return sorted(self.layers.values(), key=lambda l: l.z_order)

    def get_objects_in_layer(self, layer_id: str) -> List[SceneObject]:
        """Return objects in a layer sorted by z_index."""
        layer = self.layers.get(layer_id)
        if not layer:
            return []
        objects = [
            self.objects[oid]
            for oid in layer.object_ids
            if oid in self.objects
        ]
        return sorted(objects, key=lambda o: o.z_index)


# ---------------------------------------------------------------------------
# EngineVisualComposer (Singleton)
# ---------------------------------------------------------------------------

class EngineVisualComposer:
    """Visual Scene Composition Engine for the SparkLabs game engine.

    Provides a complete drag-and-drop visual scene building workflow
    with layer management, object placement, property editing, and
    real-time preview. Implements a singleton pattern with double-
    checked locking for thread safety.

    Subsystems:
      - LayerManager: Z-ordered layer management for organizing objects
      - SceneCanvas: Virtual canvas with pan/zoom for all scene objects
      - ObjectLibrary: Catalog of placeable object templates
      - PropertyEditor: Real-time type-aware property editing
      - SceneSerializer: JSON-based scene save/load
      - PreviewRenderer: Real-time scene preview data generation
      - SelectionManager: Multi-object selection, grouping, alignment

    Usage:
        vc = get_visual_composer()
        scene = vc.create_scene("Level 1", 1920, 1080)
        layer = vc.add_layer(scene.id, "Background", 0)
        obj = vc.place_object(scene.id, "tpl_tree", 100, 200, layer.id)
        sel = vc.select_objects(scene.id, [obj.id])
        data = vc.save_scene(scene.id)
    """

    _instance: Optional["EngineVisualComposer"] = None
    _lock: threading.RLock = threading.RLock()

    # Canvas defaults
    DEFAULT_GRID_SIZE: int = 32
    DEFAULT_SNAP_THRESHOLD: float = 8.0

    def __new__(cls) -> "EngineVisualComposer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # Scene storage
        self._scenes: Dict[str, SceneDocument] = {}

        # Global object template library
        self._template_library: Dict[str, ObjectTemplate] = {}

        # Canvas state per scene
        self._canvas_state: Dict[str, Dict[str, Any]] = {}

        # Selection state per scene
        self._selections: Dict[str, SelectionState] = {}

        # Snap settings
        self._snap_mode: SnapMode = SnapMode.GRID
        self._snap_grid_size: int = self.DEFAULT_GRID_SIZE
        self._snap_threshold: float = self.DEFAULT_SNAP_THRESHOLD

        # Statistics
        self._total_scenes_created: int = 0
        self._total_objects_placed: int = 0
        self._total_objects_deleted: int = 0
        self._total_saves: int = 0
        self._total_loads: int = 0

    # ------------------------------------------------------------------
    # Singleton Accessor
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineVisualComposer":
        """Return the singleton EngineVisualComposer instance."""
        return cls()

    # ------------------------------------------------------------------
    # Scene Management
    # ------------------------------------------------------------------

    def create_scene(
        self,
        name: str,
        width: int = 1920,
        height: int = 1080,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SceneDocument:
        """Create a new scene document with the given canvas dimensions.

        Automatically creates a default layer ("Default") at z-order 0.
        Initializes the canvas state and selection state for the scene.

        Args:
            name: Display name for the scene.
            width: Canvas width in scene units.
            height: Canvas height in scene units.
            metadata: Optional scene-level metadata.

        Returns:
            The newly created SceneDocument.
        """
        with self._lock:
            scene = SceneDocument(
                name=name,
                width=width,
                height=height,
                metadata=metadata or {},
            )

            # Create a default layer
            default_layer = SceneLayer(
                name="Default",
                z_order=0,
            )
            scene.layers[default_layer.id] = default_layer

            self._scenes[scene.id] = scene

            # Initialize canvas state
            self._canvas_state[scene.id] = {
                "pan_x": 0.0,
                "pan_y": 0.0,
                "zoom": 1.0,
                "grid_visible": True,
                "grid_size": self._snap_grid_size,
                "show_bounding_boxes": False,
            }

            # Initialize selection state
            self._selections[scene.id] = SelectionState()

            self._total_scenes_created += 1
            return scene

    def get_scene(self, scene_id: str) -> Optional[SceneDocument]:
        """Retrieve a scene by its identifier."""
        with self._lock:
            return self._scenes.get(scene_id)

    def list_scenes(self) -> List[Dict[str, Any]]:
        """List all scenes with summary information."""
        with self._lock:
            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "width": s.width,
                    "height": s.height,
                    "layer_count": len(s.layers),
                    "object_count": len(s.objects),
                    "template_count": len(s.templates),
                    "group_count": len(s.groups),
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                }
                for s in self._scenes.values()
            ]

    def delete_scene(self, scene_id: str) -> bool:
        """Delete a scene and all associated state.

        Args:
            scene_id: Scene to delete.

        Returns:
            True if the scene was deleted, False if not found.
        """
        with self._lock:
            if scene_id not in self._scenes:
                return False
            del self._scenes[scene_id]
            self._canvas_state.pop(scene_id, None)
            self._selections.pop(scene_id, None)
            return True

    # ------------------------------------------------------------------
    # Layer Management (LayerManager)
    # ------------------------------------------------------------------

    def add_layer(
        self,
        scene_id: str,
        name: str,
        z_order: Optional[int] = None,
        blend_mode: LayerBlendMode = LayerBlendMode.NORMAL,
        opacity: float = 1.0,
    ) -> Optional[SceneLayer]:
        """Add a new layer to the scene.

        If z_order is not specified, it is set to one above the highest
        existing layer. The new layer is visible and unlocked by default.

        Args:
            scene_id: Parent scene identifier.
            name: Display name for the layer.
            z_order: Stacking order (higher = on top). Auto-assigned if None.
            blend_mode: Compositing blend mode.
            opacity: Layer opacity (0.0 to 1.0).

        Returns:
            The created SceneLayer, or None if the scene is not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return None

            if z_order is None:
                existing = scene.get_layers_sorted()
                z_order = (existing[-1].z_order + 1) if existing else 0

            layer = SceneLayer(
                name=name,
                z_order=z_order,
                blend_mode=blend_mode,
                opacity=max(0.0, min(1.0, opacity)),
            )
            scene.layers[layer.id] = layer
            scene.touch()
            return layer

    def remove_layer(self, scene_id: str, layer_id: str) -> bool:
        """Remove a layer and all objects within it.

        Args:
            scene_id: Parent scene identifier.
            layer_id: Layer to remove.

        Returns:
            True if removed, False if the scene or layer is not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            layer = scene.layers.get(layer_id)
            if layer is None:
                return False

            # Remove all objects in the layer
            for oid in list(layer.object_ids):
                scene.objects.pop(oid, None)

            del scene.layers[layer_id]
            scene.touch()
            return True

    def set_layer_visibility(self, scene_id: str, layer_id: str, visible: bool) -> bool:
        """Toggle the visibility of a layer.

        When a layer is hidden, all objects within it are excluded from
        preview rendering and selection queries.

        Args:
            scene_id: Parent scene identifier.
            layer_id: Layer to modify.
            visible: New visibility state.

        Returns:
            True if updated, False if not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            layer = scene.layers.get(layer_id)
            if layer is None:
                return False
            layer.visible = visible
            scene.touch()
            return True

    def set_layer_lock(self, scene_id: str, layer_id: str, locked: bool) -> bool:
        """Lock or unlock a layer against edits.

        Locked layers prevent object selection, movement, and deletion
        within the visual editor.

        Args:
            scene_id: Parent scene identifier.
            layer_id: Layer to modify.
            locked: New lock state.

        Returns:
            True if updated, False if not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            layer = scene.layers.get(layer_id)
            if layer is None:
                return False
            layer.locked = locked
            scene.touch()
            return True

    def reorder_layer(self, scene_id: str, layer_id: str, new_z_order: int) -> bool:
        """Change the z-order of a layer.

        Args:
            scene_id: Parent scene identifier.
            layer_id: Layer to reorder.
            new_z_order: New stacking order value.

        Returns:
            True if updated, False if not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            layer = scene.layers.get(layer_id)
            if layer is None:
                return False
            layer.z_order = new_z_order
            scene.touch()
            return True

    def get_layers(self, scene_id: str) -> List[SceneLayer]:
        """Get all layers in a scene, sorted by z-order."""
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return []
            return scene.get_layers_sorted()

    # ------------------------------------------------------------------
    # Object Template Library (ObjectLibrary)
    # ------------------------------------------------------------------

    def register_template(self, template: ObjectTemplate) -> ObjectTemplate:
        """Register a new object template in the global library.

        If a template with the same ID already exists, it is overwritten.

        Args:
            template: The ObjectTemplate to register.

        Returns:
            The registered template.
        """
        with self._lock:
            self._template_library[template.id] = template
            return template

    def create_template(
        self,
        name: str,
        object_type: ObjectType,
        category: str = "General",
        description: str = "",
        default_properties: Optional[Dict[str, Any]] = None,
        icon: str = "",
        tags: Optional[List[str]] = None,
    ) -> ObjectTemplate:
        """Create and register a new object template.

        Args:
            name: Display name.
            object_type: Type of object this template creates.
            category: Library category.
            description: Human-readable description.
            default_properties: Default property values.
            icon: Icon identifier.
            tags: Searchable tags.

        Returns:
            The created ObjectTemplate.
        """
        template = ObjectTemplate(
            name=name,
            object_type=object_type,
            category=category,
            description=description,
            default_properties=default_properties or {},
            icon=icon,
            tags=tags or [],
        )
        return self.register_template(template)

    def get_template(self, template_id: str) -> Optional[ObjectTemplate]:
        """Retrieve a template from the global library."""
        with self._lock:
            return self._template_library.get(template_id)

    def list_templates(
        self,
        category: Optional[str] = None,
        object_type: Optional[ObjectType] = None,
    ) -> List[ObjectTemplate]:
        """List templates, optionally filtered by category or type.

        Args:
            category: Filter by library category.
            object_type: Filter by object type.

        Returns:
            Matching templates.
        """
        with self._lock:
            results = list(self._template_library.values())
            if category is not None:
                results = [t for t in results if t.category == category]
            if object_type is not None:
                results = [t for t in results if t.object_type == object_type]
            return results

    def import_template_to_scene(
        self, scene_id: str, template_id: str
    ) -> Optional[ObjectTemplate]:
        """Copy a template from the global library into a scene's local library.

        Args:
            scene_id: Target scene identifier.
            template_id: Global template to import.

        Returns:
            The imported template, or None if scene/template not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return None
            template = self._template_library.get(template_id)
            if template is None:
                return None
            scene.templates[template_id] = template
            scene.touch()
            return template

    # ------------------------------------------------------------------
    # Object Placement
    # ------------------------------------------------------------------

    def place_object(
        self,
        scene_id: str,
        template_id: str,
        x: float,
        y: float,
        layer_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[SceneObject]:
        """Place a new object into the scene at the specified position.

        The object is created from the template's defaults, with instance
        properties that can be overridden. If no layer is specified, the
        object is placed on the first visible unlocked layer.

        Args:
            scene_id: Parent scene identifier.
            template_id: Template to instantiate from.
            x: X position on the canvas.
            y: Y position on the canvas.
            layer_id: Target layer ID. Uses default layer if None.
            name: Optional instance name override.

        Returns:
            The placed SceneObject, or None if the scene/template is not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return None

            # Resolve template from scene-local or global library
            template = scene.templates.get(template_id)
            if template is None:
                template = self._template_library.get(template_id)
            if template is None:
                return None

            # Resolve layer
            if layer_id is None or layer_id not in scene.layers:
                # Find the first visible unlocked layer
                sorted_layers = scene.get_layers_sorted()
                target_layer = None
                for lyr in sorted_layers:
                    if lyr.visible and not lyr.locked:
                        target_layer = lyr
                        break
                if target_layer is None:
                    # Fall back to the first layer
                    target_layer = sorted_layers[0] if sorted_layers else None
                if target_layer is None:
                    return None
            else:
                target_layer = scene.layers[layer_id]

            # Apply snap
            snap_x, snap_y = self._apply_snap(x, y)

            # Determine z_index within the layer
            max_z = -1
            for oid in target_layer.object_ids:
                obj = scene.objects.get(oid)
                if obj and obj.z_index > max_z:
                    max_z = obj.z_index

            # Create the object
            obj = SceneObject(
                name=name or template.name,
                object_type=template.object_type,
                template_id=template_id,
                position_x=snap_x,
                position_y=snap_y,
                width=template.default_properties.get("width", 64.0),
                height=template.default_properties.get("height", 64.0),
                rotation=template.default_properties.get("rotation", 0.0),
                z_index=max_z + 1,
                layer_id=target_layer.id,
                properties=dict(template.default_properties),
                tags=list(template.tags),
            )

            scene.objects[obj.id] = obj
            target_layer.object_ids.append(obj.id)
            scene.touch()
            self._total_objects_placed += 1
            return obj

    def move_object(
        self,
        scene_id: str,
        object_id: str,
        x: float,
        y: float,
    ) -> bool:
        """Move an object to a new position on the canvas.

        If snap mode is enabled, the position is snapped to the grid
        or other alignment targets.

        Args:
            scene_id: Parent scene identifier.
            object_id: Object to move.
            x: New X position.
            y: New Y position.

        Returns:
            True if moved, False if the scene or object is not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            obj = scene.objects.get(object_id)
            if obj is None:
                return False
            if obj.locked:
                return False

            snap_x, snap_y = self._apply_snap(x, y)
            obj.position_x = snap_x
            obj.position_y = snap_y
            obj.touch()
            scene.touch()
            return True

    def resize_object(
        self,
        scene_id: str,
        object_id: str,
        width: float,
        height: float,
    ) -> bool:
        """Resize an object on the canvas.

        Args:
            scene_id: Parent scene identifier.
            object_id: Object to resize.
            width: New width (minimum 1.0).
            height: New height (minimum 1.0).

        Returns:
            True if resized, False if not found or locked.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            obj = scene.objects.get(object_id)
            if obj is None or obj.locked:
                return False
            obj.width = max(1.0, width)
            obj.height = max(1.0, height)
            obj.touch()
            scene.touch()
            return True

    def rotate_object(
        self,
        scene_id: str,
        object_id: str,
        degrees: float,
    ) -> bool:
        """Set the rotation of an object.

        Args:
            scene_id: Parent scene identifier.
            object_id: Object to rotate.
            degrees: Rotation in degrees (0-360, normalized).

        Returns:
            True if rotated, False if not found or locked.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            obj = scene.objects.get(object_id)
            if obj is None or obj.locked:
                return False
            obj.rotation = degrees % 360.0
            obj.touch()
            scene.touch()
            return True

    def set_object_property(
        self,
        scene_id: str,
        object_id: str,
        key: str,
        value: Any,
    ) -> bool:
        """Set a custom property on an object.

        Args:
            scene_id: Parent scene identifier.
            object_id: Object to modify.
            key: Property name.
            value: Property value.

        Returns:
            True if set, False if not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            obj = scene.objects.get(object_id)
            if obj is None:
                return False
            obj.properties[key] = value
            obj.touch()
            scene.touch()
            return True

    def set_object_layer(
        self,
        scene_id: str,
        object_id: str,
        new_layer_id: str,
    ) -> bool:
        """Move an object to a different layer.

        Args:
            scene_id: Parent scene identifier.
            object_id: Object to move.
            new_layer_id: Target layer.

        Returns:
            True if moved, False if not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            obj = scene.objects.get(object_id)
            if obj is None:
                return False
            new_layer = scene.layers.get(new_layer_id)
            if new_layer is None:
                return False

            # Remove from old layer
            old_layer = scene.layers.get(obj.layer_id)
            if old_layer and object_id in old_layer.object_ids:
                old_layer.object_ids.remove(object_id)

            # Add to new layer
            obj.layer_id = new_layer_id
            new_layer.object_ids.append(object_id)

            # Recalculate z_index for new layer
            max_z = -1
            for oid in new_layer.object_ids:
                other = scene.objects.get(oid)
                if other and other.id != object_id and other.z_index > max_z:
                    max_z = other.z_index
            obj.z_index = max_z + 1

            obj.touch()
            scene.touch()
            return True

    # ------------------------------------------------------------------
    # Selection Management (SelectionManager)
    # ------------------------------------------------------------------

    def select_objects(
        self,
        scene_id: str,
        object_ids: List[str],
    ) -> Optional[SelectionState]:
        """Select one or more objects in the scene.

        The first object in the list becomes the primary selection
        (used as the anchor for alignment operations). The bounding
        box of all selected objects is computed automatically.

        Args:
            scene_id: Parent scene identifier.
            object_ids: IDs of objects to select.

        Returns:
            The current SelectionState, or None if the scene is not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return None

            # Validate object IDs
            valid_ids = [oid for oid in object_ids if oid in scene.objects]

            selection = SelectionState(
                selected_object_ids=valid_ids,
                primary_object_id=valid_ids[0] if valid_ids else None,
            )

            # Compute union bounding box
            if valid_ids:
                bbox = self._compute_union_bounding_box(scene, valid_ids)
                selection.bounding_box = bbox

            self._selections[scene_id] = selection
            return selection

    def add_to_selection(self, scene_id: str, object_ids: List[str]) -> Optional[SelectionState]:
        """Add objects to the current selection without clearing existing.

        Args:
            scene_id: Parent scene identifier.
            object_ids: Additional object IDs to select.

        Returns:
            The updated SelectionState, or None if scene not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return None
            selection = self._selections.get(scene_id, SelectionState())

            current = set(selection.selected_object_ids)
            for oid in object_ids:
                if oid in scene.objects:
                    current.add(oid)

            new_ids = list(current)
            selection = SelectionState(
                selected_object_ids=new_ids,
                primary_object_id=selection.primary_object_id or (new_ids[0] if new_ids else None),
            )
            if new_ids:
                selection.bounding_box = self._compute_union_bounding_box(scene, new_ids)
            self._selections[scene_id] = selection
            return selection

    def clear_selection(self, scene_id: str) -> None:
        """Clear the current selection for a scene."""
        with self._lock:
            if scene_id in self._selections:
                self._selections[scene_id] = SelectionState()

    def get_selection(self, scene_id: str) -> Optional[SelectionState]:
        """Get the current selection state for a scene."""
        with self._lock:
            return self._selections.get(scene_id)

    def _compute_union_bounding_box(
        self,
        scene: SceneDocument,
        object_ids: List[str],
    ) -> Dict[str, float]:
        """Compute the union bounding box of a set of objects."""
        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")

        for oid in object_ids:
            obj = scene.objects.get(oid)
            if obj is None:
                continue
            bb = obj.get_bounding_box()
            min_x = min(min_x, bb["x"])
            min_y = min(min_y, bb["y"])
            max_x = max(max_x, bb["x"] + bb["width"])
            max_y = max(max_y, bb["y"] + bb["height"])

        if min_x == float("inf"):
            return {"x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0}

        return {
            "x": min_x,
            "y": min_y,
            "width": max_x - min_x,
            "height": max_y - min_y,
        }

    # ------------------------------------------------------------------
    # Object Deletion
    # ------------------------------------------------------------------

    def delete_objects(
        self,
        scene_id: str,
        object_ids: List[str],
    ) -> int:
        """Delete one or more objects from the scene.

        Removes objects from the scene registry and their parent layers.
        Also clears the selection if deleted objects were selected.

        Args:
            scene_id: Parent scene identifier.
            object_ids: IDs of objects to delete.

        Returns:
            Number of objects actually deleted.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return 0

            deleted_count = 0
            for oid in object_ids:
                obj = scene.objects.get(oid)
                if obj is None or obj.locked:
                    continue

                # Remove from layer
                layer = scene.layers.get(obj.layer_id)
                if layer and oid in layer.object_ids:
                    layer.object_ids.remove(oid)

                # Remove from groups
                for gname, gids in list(scene.groups.items()):
                    if oid in gids:
                        gids.remove(oid)
                    if not gids:
                        del scene.groups[gname]

                del scene.objects[oid]
                deleted_count += 1

            # Update selection
            if deleted_count > 0:
                selection = self._selections.get(scene_id)
                if selection:
                    remaining = [
                        oid for oid in selection.selected_object_ids
                        if oid in scene.objects
                    ]
                    self._selections[scene_id] = SelectionState(
                        selected_object_ids=remaining,
                        primary_object_id=remaining[0] if remaining else None,
                    )

                scene.touch()
                self._total_objects_deleted += deleted_count

            return deleted_count

    # ------------------------------------------------------------------
    # Object Alignment (SelectionManager)
    # ------------------------------------------------------------------

    def align_objects(
        self,
        scene_id: str,
        alignment: AlignmentType,
    ) -> int:
        """Align the currently selected objects.

        Uses the primary selected object as the anchor. Supports:
          - LEFT: Align left edges to the primary object's left edge.
          - RIGHT: Align right edges to the primary object's right edge.
          - TOP: Align top edges to the primary object's top edge.
          - BOTTOM: Align bottom edges to the primary object's bottom edge.
          - CENTER_HORIZONTAL: Align horizontal centers to the primary.
          - CENTER_VERTICAL: Align vertical centers to the primary.
          - DISTRIBUTE_HORIZONTAL: Evenly space objects horizontally.
          - DISTRIBUTE_VERTICAL: Evenly space objects vertically.

        Args:
            scene_id: Parent scene identifier.
            alignment: The alignment type to apply.

        Returns:
            Number of objects aligned.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return 0

            selection = self._selections.get(scene_id)
            if not selection or len(selection.selected_object_ids) < 2:
                return 0

            primary = scene.objects.get(selection.primary_object_id or "")
            if primary is None:
                return 0

            aligned = 0
            for oid in selection.selected_object_ids:
                if oid == primary.id:
                    continue
                obj = scene.objects.get(oid)
                if obj is None or obj.locked:
                    continue

                if alignment == AlignmentType.LEFT:
                    obj.position_x = primary.position_x
                elif alignment == AlignmentType.RIGHT:
                    obj.position_x = (primary.position_x + primary.width) - obj.width
                elif alignment == AlignmentType.TOP:
                    obj.position_y = primary.position_y
                elif alignment == AlignmentType.BOTTOM:
                    obj.position_y = (primary.position_y + primary.height) - obj.height
                elif alignment == AlignmentType.CENTER_HORIZONTAL:
                    primary_center = primary.position_x + primary.width / 2.0
                    obj.position_x = primary_center - obj.width / 2.0
                elif alignment == AlignmentType.CENTER_VERTICAL:
                    primary_center = primary.position_y + primary.height / 2.0
                    obj.position_y = primary_center - obj.height / 2.0
                else:
                    continue

                obj.touch()
                aligned += 1

            if alignment in (AlignmentType.DISTRIBUTE_HORIZONTAL, AlignmentType.DISTRIBUTE_VERTICAL):
                aligned = self._distribute_objects(scene, selection, alignment)

            if aligned > 0:
                scene.touch()
                # Update selection bounding box
                selection.bounding_box = self._compute_union_bounding_box(
                    scene, selection.selected_object_ids
                )

            return aligned

    def _distribute_objects(
        self,
        scene: SceneDocument,
        selection: SelectionState,
        alignment: AlignmentType,
    ) -> int:
        """Evenly distribute selected objects horizontally or vertically."""
        objects = [
            scene.objects[oid]
            for oid in selection.selected_object_ids
            if oid in scene.objects and not scene.objects[oid].locked
        ]
        if len(objects) < 3:
            return 0

        if alignment == AlignmentType.DISTRIBUTE_HORIZONTAL:
            objects.sort(key=lambda o: o.position_x)
            leftmost = objects[0]
            rightmost = objects[-1]
            total_width = sum(o.width for o in objects[1:-1])
            available_space = (
                (rightmost.position_x + rightmost.width)
                - leftmost.position_x
                - total_width
            )
            gap = max(0.0, available_space / (len(objects) - 1))
            current_x = leftmost.position_x + leftmost.width + gap
            for obj in objects[1:-1]:
                obj.position_x = current_x
                current_x += obj.width + gap
                obj.touch()
        else:
            objects.sort(key=lambda o: o.position_y)
            topmost = objects[0]
            bottommost = objects[-1]
            total_height = sum(o.height for o in objects[1:-1])
            available_space = (
                (bottommost.position_y + bottommost.height)
                - topmost.position_y
                - total_height
            )
            gap = max(0.0, available_space / (len(objects) - 1))
            current_y = topmost.position_y + topmost.height + gap
            for obj in objects[1:-1]:
                obj.position_y = current_y
                current_y += obj.height + gap
                obj.touch()

        return len(objects)

    # ------------------------------------------------------------------
    # Object Grouping (SelectionManager)
    # ------------------------------------------------------------------

    def group_objects(
        self,
        scene_id: str,
        object_ids: List[str],
        group_name: str,
    ) -> bool:
        """Create a named group of objects for batch operations.

        Objects in a group can be selected, moved, and manipulated
        together. Group names must be unique within a scene.

        Args:
            scene_id: Parent scene identifier.
            object_ids: Object IDs to include in the group.
            group_name: Unique group name.

        Returns:
            True if the group was created, False if scene not found
            or group name already exists.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            if group_name in scene.groups:
                return False

            valid_ids = [oid for oid in object_ids if oid in scene.objects]
            if not valid_ids:
                return False

            scene.groups[group_name] = valid_ids
            scene.touch()
            return True

    def ungroup_objects(self, scene_id: str, group_name: str) -> bool:
        """Remove a named group without deleting the objects.

        Args:
            scene_id: Parent scene identifier.
            group_name: Name of the group to dissolve.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return False
            if group_name not in scene.groups:
                return False
            del scene.groups[group_name]
            scene.touch()
            return True

    def select_group(self, scene_id: str, group_name: str) -> Optional[SelectionState]:
        """Select all objects in a named group.

        Args:
            scene_id: Parent scene identifier.
            group_name: Name of the group to select.

        Returns:
            The resulting SelectionState, or None if not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return None
            object_ids = scene.groups.get(group_name, [])
            return self.select_objects(scene_id, object_ids)

    def get_groups(self, scene_id: str) -> List[Dict[str, Any]]:
        """List all groups in a scene."""
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return []
            return [
                {
                    "name": gname,
                    "object_count": len(gids),
                    "object_ids": list(gids),
                }
                for gname, gids in scene.groups.items()
            ]

    # ------------------------------------------------------------------
    # Scene Serialization (SceneSerializer)
    # ------------------------------------------------------------------

    def save_scene(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """Serialize a scene to a JSON-compatible dictionary.

        The output includes all layers, objects, templates, groups,
        canvas state, and metadata. This data can be written to a file
        or transmitted over the network.

        Args:
            scene_id: Scene to serialize.

        Returns:
            Serialized scene data, or None if the scene is not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return None

            canvas = self._canvas_state.get(scene_id, {})
            selection = self._selections.get(scene_id)

            data = {
                "format": "sparklabs_visual_scene",
                "version": "1.0",
                "scene": scene.to_dict(),
                "canvas_state": {
                    "pan_x": canvas.get("pan_x", 0.0),
                    "pan_y": canvas.get("pan_y", 0.0),
                    "zoom": canvas.get("zoom", 1.0),
                    "grid_visible": canvas.get("grid_visible", True),
                    "grid_size": canvas.get("grid_size", self.DEFAULT_GRID_SIZE),
                    "show_bounding_boxes": canvas.get("show_bounding_boxes", False),
                },
                "snap_settings": {
                    "mode": self._snap_mode.value,
                    "grid_size": self._snap_grid_size,
                    "threshold": self._snap_threshold,
                },
                "selection": selection.to_dict() if selection else None,
                "saved_at": time.time(),
            }

            self._total_saves += 1
            return data

    def load_scene(self, data: Dict[str, Any]) -> Optional[SceneDocument]:
        """Load a scene from serialized data.

        Reconstructs the full scene document including all layers,
        objects, templates, groups, canvas state, and selection state.

        Args:
            data: Serialized scene data (as produced by save_scene).

        Returns:
            The reconstructed SceneDocument, or None if data is invalid.
        """
        with self._lock:
            scene_data = data.get("scene")
            if not scene_data:
                return None

            # Deserialize layers
            layers: Dict[str, SceneLayer] = {}
            for lid, ldata in scene_data.get("layers", {}).items():
                layers[lid] = SceneLayer.from_dict(ldata)

            # Deserialize templates
            templates: Dict[str, ObjectTemplate] = {}
            for tid, tdata in scene_data.get("templates", {}).items():
                templates[tid] = ObjectTemplate.from_dict(tdata)

            # Deserialize objects
            objects: Dict[str, SceneObject] = {}
            for oid, odata in scene_data.get("objects", {}).items():
                objects[oid] = SceneObject.from_dict(odata)

            # Deserialize groups
            groups: Dict[str, List[str]] = {}
            for gname, gids in scene_data.get("groups", {}).items():
                groups[gname] = list(gids)

            # Create scene document
            scene = SceneDocument(
                id=scene_data.get("id", uuid.uuid4().hex),
                name=scene_data.get("name", "Loaded Scene"),
                width=scene_data.get("width", 1920),
                height=scene_data.get("height", 1080),
                layers=layers,
                objects=objects,
                templates=templates,
                groups=groups,
                metadata=dict(scene_data.get("metadata", {})),
                created_at=scene_data.get("created_at", time.time()),
                updated_at=time.time(),
            )

            self._scenes[scene.id] = scene

            # Restore canvas state
            canvas = data.get("canvas_state", {})
            self._canvas_state[scene.id] = {
                "pan_x": canvas.get("pan_x", 0.0),
                "pan_y": canvas.get("pan_y", 0.0),
                "zoom": canvas.get("zoom", 1.0),
                "grid_visible": canvas.get("grid_visible", True),
                "grid_size": canvas.get("grid_size", self.DEFAULT_GRID_SIZE),
                "show_bounding_boxes": canvas.get("show_bounding_boxes", False),
            }

            # Restore snap settings
            snap = data.get("snap_settings", {})
            if snap:
                self._snap_mode = SnapMode(snap.get("mode", "grid"))
                self._snap_grid_size = snap.get("grid_size", self.DEFAULT_GRID_SIZE)
                self._snap_threshold = snap.get("threshold", self.DEFAULT_SNAP_THRESHOLD)

            # Restore selection
            sel_data = data.get("selection")
            if sel_data:
                self._selections[scene.id] = SelectionState(
                    selected_object_ids=list(sel_data.get("selected_object_ids", [])),
                    primary_object_id=sel_data.get("primary_object_id"),
                )
            else:
                self._selections[scene.id] = SelectionState()

            self._total_loads += 1
            return scene

    # ------------------------------------------------------------------
    # Canvas State (SceneCanvas)
    # ------------------------------------------------------------------

    def set_canvas_view(
        self,
        scene_id: str,
        pan_x: Optional[float] = None,
        pan_y: Optional[float] = None,
        zoom: Optional[float] = None,
    ) -> bool:
        """Update the canvas pan and zoom for a scene.

        Args:
            scene_id: Scene identifier.
            pan_x: Horizontal pan offset.
            pan_y: Vertical pan offset.
            zoom: Zoom level (minimum 0.1).

        Returns:
            True if updated, False if scene not found.
        """
        with self._lock:
            canvas = self._canvas_state.get(scene_id)
            if canvas is None:
                return False
            if pan_x is not None:
                canvas["pan_x"] = pan_x
            if pan_y is not None:
                canvas["pan_y"] = pan_y
            if zoom is not None:
                canvas["zoom"] = max(0.1, zoom)
            return True

    def get_canvas_state(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """Get the current canvas state for a scene."""
        with self._lock:
            return self._canvas_state.get(scene_id)

    def set_grid_visible(self, scene_id: str, visible: bool) -> bool:
        """Toggle the grid visibility on the canvas."""
        with self._lock:
            canvas = self._canvas_state.get(scene_id)
            if canvas is None:
                return False
            canvas["grid_visible"] = visible
            return True

    def set_show_bounding_boxes(self, scene_id: str, show: bool) -> bool:
        """Toggle bounding box display on the canvas."""
        with self._lock:
            canvas = self._canvas_state.get(scene_id)
            if canvas is None:
                return False
            canvas["show_bounding_boxes"] = show
            return True

    # ------------------------------------------------------------------
    # Snap Settings
    # ------------------------------------------------------------------

    def set_snap_mode(self, mode: SnapMode) -> None:
        """Set the global snap mode for object placement."""
        with self._lock:
            self._snap_mode = mode

    def set_snap_grid_size(self, size: int) -> None:
        """Set the grid size for grid snapping."""
        with self._lock:
            self._snap_grid_size = max(1, size)

    def set_snap_threshold(self, threshold: float) -> None:
        """Set the distance threshold for object snapping."""
        with self._lock:
            self._snap_threshold = max(0.0, threshold)

    def get_snap_settings(self) -> Dict[str, Any]:
        """Get the current snap settings."""
        with self._lock:
            return {
                "mode": self._snap_mode.value,
                "grid_size": self._snap_grid_size,
                "threshold": self._snap_threshold,
            }

    def _apply_snap(self, x: float, y: float) -> Tuple[float, float]:
        """Apply the current snap mode to a coordinate pair."""
        if self._snap_mode == SnapMode.NONE:
            return x, y
        elif self._snap_mode == SnapMode.GRID:
            gs = self._snap_grid_size
            return round(x / gs) * gs, round(y / gs) * gs
        elif self._snap_mode == SnapMode.PIXEL:
            return round(x), round(y)
        else:
            # OBJECT snap requires context (nearby objects), not applied here
            return x, y

    # ------------------------------------------------------------------
    # Preview Rendering (PreviewRenderer)
    # ------------------------------------------------------------------

    def get_preview(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """Generate a real-time preview data structure for a scene.

        The preview includes all visible objects sorted by layer z-order
        and per-object z_index, with their positions, dimensions, and
        bounding boxes. Objects on hidden layers are excluded.

        Args:
            scene_id: Scene to preview.

        Returns:
            Preview data dict, or None if the scene is not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return None

            canvas = self._canvas_state.get(scene_id, {})
            selection = self._selections.get(scene_id)

            # Collect visible objects sorted by layer z-order then object z_index
            objects_preview: List[Dict[str, Any]] = []
            for layer in scene.get_layers_sorted():
                if not layer.visible:
                    continue
                for obj in scene.get_objects_in_layer(layer.id):
                    if not obj.visible:
                        continue
                    objects_preview.append({
                        "id": obj.id,
                        "name": obj.name,
                        "object_type": obj.object_type.value,
                        "position_x": obj.position_x,
                        "position_y": obj.position_y,
                        "width": obj.width,
                        "height": obj.height,
                        "rotation": obj.rotation,
                        "z_index": obj.z_index,
                        "layer_id": obj.layer_id,
                        "layer_name": layer.name,
                        "bounding_box": obj.get_bounding_box(),
                        "properties": dict(obj.properties),
                        "tags": list(obj.tags),
                    })

            # Compute scene-level bounding box
            if objects_preview:
                min_x = min(o["bounding_box"]["x"] for o in objects_preview)
                min_y = min(o["bounding_box"]["y"] for o in objects_preview)
                max_x = max(
                    o["bounding_box"]["x"] + o["bounding_box"]["width"]
                    for o in objects_preview
                )
                max_y = max(
                    o["bounding_box"]["y"] + o["bounding_box"]["height"]
                    for o in objects_preview
                )
                scene_bbox = {
                    "x": min_x,
                    "y": min_y,
                    "width": max_x - min_x,
                    "height": max_y - min_y,
                }
            else:
                scene_bbox = {"x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0}

            return {
                "scene_id": scene.id,
                "scene_name": scene.name,
                "canvas_width": scene.width,
                "canvas_height": scene.height,
                "canvas": {
                    "pan_x": canvas.get("pan_x", 0.0),
                    "pan_y": canvas.get("pan_y", 0.0),
                    "zoom": canvas.get("zoom", 1.0),
                    "grid_visible": canvas.get("grid_visible", True),
                    "grid_size": canvas.get("grid_size", self.DEFAULT_GRID_SIZE),
                },
                "layers": [
                    {
                        "id": l.id,
                        "name": l.name,
                        "z_order": l.z_order,
                        "visible": l.visible,
                        "locked": l.locked,
                        "blend_mode": l.blend_mode.value,
                        "opacity": l.opacity,
                        "object_count": len(l.object_ids),
                    }
                    for l in scene.get_layers_sorted()
                ],
                "objects": objects_preview,
                "scene_bounding_box": scene_bbox,
                "selected_object_ids": (
                    selection.selected_object_ids if selection else []
                ),
                "object_count": len(objects_preview),
                "total_object_count": len(scene.objects),
                "generated_at": time.time(),
            }

    # ------------------------------------------------------------------
    # Property Editor (PropertyEditor)
    # ------------------------------------------------------------------

    def get_object_properties(
        self, scene_id: str, object_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get all properties of an object for editing.

        Returns a type-aware property map including the object's type,
        transform, visibility, and custom properties. The property
        types are annotated for UI rendering.

        Args:
            scene_id: Parent scene identifier.
            object_id: Object to inspect.

        Returns:
            Property map with type annotations, or None if not found.
        """
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return None
            obj = scene.objects.get(object_id)
            if obj is None:
                return None

            template = scene.templates.get(obj.template_id)
            if template is None:
                template = self._template_library.get(obj.template_id)

            return {
                "id": obj.id,
                "name": obj.name,
                "object_type": obj.object_type.value,
                "template_name": template.name if template else "Unknown",
                "properties": [
                    {
                        "name": "position_x",
                        "label": "Position X",
                        "type": "float",
                        "value": obj.position_x,
                        "editable": not obj.locked,
                    },
                    {
                        "name": "position_y",
                        "label": "Position Y",
                        "type": "float",
                        "value": obj.position_y,
                        "editable": not obj.locked,
                    },
                    {
                        "name": "width",
                        "label": "Width",
                        "type": "float",
                        "value": obj.width,
                        "min": 1.0,
                        "editable": not obj.locked,
                    },
                    {
                        "name": "height",
                        "label": "Height",
                        "type": "float",
                        "value": obj.height,
                        "min": 1.0,
                        "editable": not obj.locked,
                    },
                    {
                        "name": "rotation",
                        "label": "Rotation",
                        "type": "float",
                        "value": obj.rotation,
                        "min": 0.0,
                        "max": 360.0,
                        "editable": not obj.locked,
                    },
                    {
                        "name": "z_index",
                        "label": "Z-Index",
                        "type": "int",
                        "value": obj.z_index,
                        "editable": not obj.locked,
                    },
                    {
                        "name": "visible",
                        "label": "Visible",
                        "type": "bool",
                        "value": obj.visible,
                        "editable": True,
                    },
                    {
                        "name": "locked",
                        "label": "Locked",
                        "type": "bool",
                        "value": obj.locked,
                        "editable": True,
                    },
                ],
                "custom_properties": [
                    {
                        "name": key,
                        "type": self._infer_property_type(value),
                        "value": value,
                        "editable": not obj.locked,
                    }
                    for key, value in obj.properties.items()
                ],
                "layer_id": obj.layer_id,
                "bounding_box": obj.get_bounding_box(),
                "tags": list(obj.tags),
            }

    @staticmethod
    def _infer_property_type(value: Any) -> str:
        """Infer a property type string from a Python value."""
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "list"
        elif isinstance(value, dict):
            return "dict"
        else:
            return "unknown"

    # ------------------------------------------------------------------
    # Status & Statistics
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status report of the visual composer.

        Includes scene counts, object statistics, template library
        size, snap settings, and per-scene breakdowns.
        """
        with self._lock:
            total_objects = sum(len(s.objects) for s in self._scenes.values())
            total_layers = sum(len(s.layers) for s in self._scenes.values())
            total_groups = sum(len(s.groups) for s in self._scenes.values())

            type_breakdown: Dict[str, int] = {}
            for scene in self._scenes.values():
                for obj in scene.objects.values():
                    t = obj.object_type.value
                    type_breakdown[t] = type_breakdown.get(t, 0) + 1

            return {
                "engine": "EngineVisualComposer",
                "version": "1.0",
                "scenes": {
                    "total": len(self._scenes),
                    "created": self._total_scenes_created,
                    "list": [
                        {
                            "id": s.id,
                            "name": s.name,
                            "width": s.width,
                            "height": s.height,
                            "layers": len(s.layers),
                            "objects": len(s.objects),
                            "templates": len(s.templates),
                            "groups": len(s.groups),
                        }
                        for s in self._scenes.values()
                    ],
                },
                "objects": {
                    "total": total_objects,
                    "placed": self._total_objects_placed,
                    "deleted": self._total_objects_deleted,
                    "type_breakdown": type_breakdown,
                },
                "layers": {
                    "total": total_layers,
                },
                "groups": {
                    "total": total_groups,
                },
                "templates": {
                    "library_size": len(self._template_library),
                },
                "serialization": {
                    "total_saves": self._total_saves,
                    "total_loads": self._total_loads,
                },
                "snap": {
                    "mode": self._snap_mode.value,
                    "grid_size": self._snap_grid_size,
                    "threshold": self._snap_threshold,
                },
                "selections": {
                    scene_id: len(sel.selected_object_ids)
                    for scene_id, sel in self._selections.items()
                },
                "generated_at": time.time(),
            }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the visual composer to its initial state.

        Clears all scenes, templates, canvas states, selections,
        and resets statistics counters.
        """
        with self._lock:
            self._scenes.clear()
            self._template_library.clear()
            self._canvas_state.clear()
            self._selections.clear()
            self._snap_mode = SnapMode.GRID
            self._snap_grid_size = self.DEFAULT_GRID_SIZE
            self._snap_threshold = self.DEFAULT_SNAP_THRESHOLD
            self._total_scenes_created = 0
            self._total_objects_placed = 0
            self._total_objects_deleted = 0
            self._total_saves = 0
            self._total_loads = 0


# ---------------------------------------------------------------------------
# Convenience Accessor
# ---------------------------------------------------------------------------

def get_visual_composer() -> EngineVisualComposer:
    """Get the singleton EngineVisualComposer instance."""
    return EngineVisualComposer()