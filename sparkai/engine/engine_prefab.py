"""
SparkLabs Engine - Prefab System

Reusable game object template system that enables rapid game development
through composable, nestable prefabs. Provides prefab instantiation with
property overrides, variant management, and AI-driven prefab generation
and optimization.

Architecture:
  PrefabSystem (Singleton)
    |-- PrefabDefinition (template with components and properties)
    |-- PrefabInstance (runtime instance with overrides)
    |-- PrefabVariant (derived prefab with modifications)
    |-- PrefabLibrary (organized collection of prefabs)
    |-- PrefabGenerator (AI-driven prefab creation)

Prefab Features:
  - Hierarchical prefab nesting with parent-child relationships
  - Property overrides for per-instance customization
  - Variant system for creating derived prefabs
  - Component-based prefab composition
  - Prefab library with categorization and search
  - AI-assisted prefab generation from descriptions

Usage:
    ps = get_prefab_system()
    ps.initialize()

    # Create a prefab
    prefab = ps.create_prefab("enemy_slime", PrefabCategory.CHARACTER, {
        "components": ["sprite", "physics", "ai_behavior"],
        "properties": {"health": 100, "speed": 2.0},
    })

    # Instantiate a prefab
    instance = ps.instantiate("enemy_slime", position=(100, 200),
                              overrides={"health": 150})

    # Generate prefabs with AI
    ps.generate_prefabs("Create assets for a fantasy RPG", count=5)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class PrefabCategory(Enum):
    """Categories for organizing prefabs."""
    CHARACTER = "character"        # Player, NPC, enemy characters
    ENVIRONMENT = "environment"    # Terrain, buildings, scenery
    ITEM = "item"                  # Collectibles, inventory items
    UI = "ui"                      # UI elements and widgets
    EFFECT = "effect"              # Particles, visual effects
    AUDIO = "audio"                # Audio sources and emitters
    LIGHTING = "lighting"          # Light sources and probes
    TRIGGER = "trigger"            # Trigger zones and volumes
    CAMERA = "camera"              # Camera configurations
    CUSTOM = "custom"              # User-defined categories


class PrefabState(Enum):
    """Lifecycle states of a prefab."""
    DRAFT = "draft"          # Being created/edited
    ACTIVE = "active"        # Ready for use
    DEPRECATED = "deprecated"  # No longer recommended
    ARCHIVED = "archived"    # Historical reference only


class OverrideMode(Enum):
    """How property overrides are applied."""
    REPLACE = "replace"      # Replace the default value
    MERGE = "merge"          # Merge with default (for dicts/lists)
    ADD = "add"              # Add to default value
    MULTIPLY = "multiply"    # Multiply default value


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class PrefabComponent:
    """A component attached to a prefab."""
    component_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    component_type: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type,
            "properties": self.properties,
            "enabled": self.enabled,
        }


@dataclass
class PropertyOverride:
    """An override for a prefab property."""
    property_path: str = ""  # e.g., "transform.position" or "sprite.color"
    original_value: Any = None
    override_value: Any = None
    mode: OverrideMode = OverrideMode.REPLACE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_path": self.property_path,
            "original_value": self.original_value,
            "override_value": self.override_value,
            "mode": self.mode.value,
        }


@dataclass
class PrefabDefinition:
    """Template definition for a reusable game object."""
    prefab_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    category: PrefabCategory = PrefabCategory.CUSTOM
    description: str = ""
    components: List[PrefabComponent] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)  # Child prefab IDs
    parent_id: Optional[str] = None
    state: PrefabState = PrefabState.DRAFT
    tags: List[str] = field(default_factory=list)
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prefab_id": self.prefab_id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "components": [c.to_dict() for c in self.components],
            "properties": self.properties,
            "children": self.children,
            "parent_id": self.parent_id,
            "state": self.state.value,
            "tags": self.tags,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "usage_count": self.usage_count,
        }


@dataclass
class PrefabInstance:
    """A runtime instance of a prefab."""
    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    prefab_id: str = ""
    prefab_name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    overrides: List[PropertyOverride] = field(default_factory=list)
    active: bool = True
    created_at: float = field(default_factory=time.time)
    scene_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "prefab_id": self.prefab_id,
            "prefab_name": self.prefab_name,
            "position": list(self.position),
            "rotation": list(self.rotation),
            "scale": list(self.scale),
            "overrides": [o.to_dict() for o in self.overrides],
            "active": self.active,
            "created_at": self.created_at,
            "scene_id": self.scene_id,
        }


@dataclass
class PrefabVariant:
    """A derived variant of a base prefab."""
    variant_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    base_prefab_id: str = ""
    description: str = ""
    overrides: List[PropertyOverride] = field(default_factory=list)
    added_components: List[PrefabComponent] = field(default_factory=list)
    removed_components: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "name": self.name,
            "base_prefab_id": self.base_prefab_id,
            "description": self.description,
            "overrides": [o.to_dict() for o in self.overrides],
            "added_components": [c.to_dict() for c in self.added_components],
            "removed_components": self.removed_components,
            "created_at": self.created_at,
        }


@dataclass
class PrefabLibrary:
    """Organized collection of prefabs."""
    library_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    prefabs: Dict[str, PrefabDefinition] = field(default_factory=dict)
    variants: Dict[str, PrefabVariant] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "library_id": self.library_id,
            "name": self.name,
            "description": self.description,
            "prefab_count": len(self.prefabs),
            "variant_count": len(self.variants),
            "created_at": self.created_at,
        }


# =============================================================================
# PrefabSystem (Singleton)
# =============================================================================


class PrefabSystem:
    """Reusable game object template system for rapid game development.

    Provides prefab creation, instantiation, variant management, and
    AI-driven prefab generation. Supports hierarchical nesting and
    property overrides for flexible game object composition.

    Usage:
        ps = PrefabSystem.get_instance()
        ps.initialize()

        prefab = ps.create_prefab("enemy", PrefabCategory.CHARACTER, {
            "components": ["sprite", "physics"],
            "properties": {"health": 100},
        })

        instance = ps.instantiate("enemy", position=(100, 200))
    """

    _instance: Optional["PrefabSystem"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if PrefabSystem._instance is not None:
            raise RuntimeError("Use PrefabSystem.get_instance()")
        self._initialized: bool = False
        self._lock = threading.RLock()
        self._prefabs: Dict[str, PrefabDefinition] = {}
        self._instances: Dict[str, PrefabInstance] = {}
        self._variants: Dict[str, PrefabVariant] = {}
        self._libraries: Dict[str, PrefabLibrary] = {}
        self._total_instantiations: int = 0

    @classmethod
    def get_instance(cls) -> "PrefabSystem":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            if self._initialized:
                return {"status": "already_initialized", "success": True}

            self._register_default_prefabs()
            self._initialized = True

            return {
                "status": "initialized",
                "success": True,
                "prefabs_registered": len(self._prefabs),
            }

    def shutdown(self) -> Dict[str, Any]:
        with self._lock:
            self._initialized = False
            return {
                "success": True,
                "total_instantiations": self._total_instantiations,
                "active_instances": len(self._instances),
            }

    def _register_default_prefabs(self) -> None:
        """Register built-in prefab templates."""
        defaults = [
            PrefabDefinition(
                name="player_character",
                category=PrefabCategory.CHARACTER,
                description="Default player character with movement and physics",
                components=[
                    PrefabComponent(component_type="sprite", properties={"texture": "player"}),
                    PrefabComponent(component_type="physics_body", properties={"body_type": "dynamic"}),
                    PrefabComponent(component_type="collider", properties={"shape": "box"}),
                    PrefabComponent(component_type="player_controller", properties={"speed": 200.0}),
                ],
                properties={"health": 100, "max_health": 100, "speed": 200.0},
                tags=["player", "character", "default"],
            ),
            PrefabDefinition(
                name="enemy_basic",
                category=PrefabCategory.CHARACTER,
                description="Basic enemy with AI patrol behavior",
                components=[
                    PrefabComponent(component_type="sprite", properties={"texture": "enemy"}),
                    PrefabComponent(component_type="physics_body", properties={"body_type": "dynamic"}),
                    PrefabComponent(component_type="collider", properties={"shape": "box"}),
                    PrefabComponent(component_type="ai_patrol", properties={"patrol_points": []}),
                ],
                properties={"health": 50, "damage": 10, "speed": 100.0},
                tags=["enemy", "character", "default"],
            ),
            PrefabDefinition(
                name="collectible_coin",
                category=PrefabCategory.ITEM,
                description="Collectible coin with pickup effect",
                components=[
                    PrefabComponent(component_type="sprite", properties={"texture": "coin"}),
                    PrefabComponent(component_type="collider", properties={"shape": "circle", "is_trigger": True}),
                    PrefabComponent(component_type="pickup", properties={"value": 10}),
                ],
                properties={"value": 10, "collectible": True},
                tags=["item", "collectible", "default"],
            ),
            PrefabDefinition(
                name="platform_moving",
                category=PrefabCategory.ENVIRONMENT,
                description="Moving platform with waypoint system",
                components=[
                    PrefabComponent(component_type="sprite", properties={"texture": "platform"}),
                    PrefabComponent(component_type="physics_body", properties={"body_type": "kinematic"}),
                    PrefabComponent(component_type="collider", properties={"shape": "box"}),
                    PrefabComponent(component_type="waypoint_mover", properties={"waypoints": [], "speed": 50.0}),
                ],
                properties={"speed": 50.0},
                tags=["environment", "platform", "default"],
            ),
            PrefabDefinition(
                name="checkpoint_flag",
                category=PrefabCategory.TRIGGER,
                description="Checkpoint flag for saving progress",
                components=[
                    PrefabComponent(component_type="sprite", properties={"texture": "flag"}),
                    PrefabComponent(component_type="collider", properties={"shape": "box", "is_trigger": True}),
                    PrefabComponent(component_type="checkpoint", properties={"activated": False}),
                ],
                properties={"activated": False},
                tags=["trigger", "checkpoint", "default"],
            ),
            PrefabDefinition(
                name="particle_explosion",
                category=PrefabCategory.EFFECT,
                description="Explosion particle effect",
                components=[
                    PrefabComponent(component_type="particle_emitter", properties={
                        "particle_count": 20,
                        "duration": 1.0,
                        "colors": [(255, 100, 0), (255, 200, 0)],
                    }),
                ],
                properties={"auto_destroy": True, "duration": 1.0},
                tags=["effect", "particle", "default"],
            ),
        ]

        for prefab in defaults:
            prefab.state = PrefabState.ACTIVE
            self._prefabs[prefab.name] = prefab

    # -------------------------------------------------------------------------
    # Prefab Creation
    # -------------------------------------------------------------------------

    def create_prefab(self, name: str, category: PrefabCategory,
                      config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new prefab definition."""
        with self._lock:
            if name in self._prefabs:
                return {"success": False, "error": f"Prefab '{name}' already exists"}

            components = []
            for comp_data in config.get("components", []):
                if isinstance(comp_data, str):
                    components.append(PrefabComponent(component_type=comp_data))
                elif isinstance(comp_data, dict):
                    components.append(PrefabComponent(
                        component_type=comp_data.get("type", ""),
                        properties=comp_data.get("properties", {}),
                    ))

            prefab = PrefabDefinition(
                name=name,
                category=category,
                description=config.get("description", ""),
                components=components,
                properties=config.get("properties", {}),
                tags=config.get("tags", []),
                parent_id=config.get("parent_id"),
            )

            self._prefabs[name] = prefab
            return {"success": True, "prefab": prefab.to_dict()}

    def get_prefab(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a prefab definition by name."""
        prefab = self._prefabs.get(name)
        return prefab.to_dict() if prefab else None

    def list_prefabs(self, category: Optional[PrefabCategory] = None) -> List[Dict[str, Any]]:
        """List all prefabs, optionally filtered by category."""
        prefabs = self._prefabs.values()
        if category:
            prefabs = [p for p in prefabs if p.category == category]
        return [p.to_dict() for p in prefabs]

    def update_prefab(self, name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a prefab definition."""
        with self._lock:
            prefab = self._prefabs.get(name)
            if not prefab:
                return {"success": False, "error": f"Prefab '{name}' not found"}

            if "components" in updates:
                prefab.components = []
                for comp_data in updates["components"]:
                    if isinstance(comp_data, str):
                        prefab.components.append(PrefabComponent(component_type=comp_data))
                    elif isinstance(comp_data, dict):
                        prefab.components.append(PrefabComponent(
                            component_type=comp_data.get("type", ""),
                            properties=comp_data.get("properties", {}),
                        ))

            if "properties" in updates:
                prefab.properties.update(updates["properties"])

            if "tags" in updates:
                prefab.tags = updates["tags"]

            if "description" in updates:
                prefab.description = updates["description"]

            prefab.version += 1
            prefab.updated_at = time.time()

            return {"success": True, "prefab": prefab.to_dict()}

    def delete_prefab(self, name: str) -> Dict[str, Any]:
        """Delete a prefab definition."""
        with self._lock:
            if name not in self._prefabs:
                return {"success": False, "error": f"Prefab '{name}' not found"}

            # Remove instances referencing this prefab
            to_remove = [
                iid for iid, inst in self._instances.items()
                if inst.prefab_name == name
            ]
            for iid in to_remove:
                del self._instances[iid]

            del self._prefabs[name]
            return {"success": True, "name": name, "instances_removed": len(to_remove)}

    # -------------------------------------------------------------------------
    # Instantiation
    # -------------------------------------------------------------------------

    def instantiate(self, prefab_name: str,
                    position: Tuple[float, float, float] = (0, 0, 0),
                    rotation: Tuple[float, float, float] = (0, 0, 0),
                    scale: Tuple[float, float, float] = (1, 1, 1),
                    overrides: Optional[Dict[str, Any]] = None,
                    scene_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a runtime instance of a prefab."""
        with self._lock:
            prefab = self._prefabs.get(prefab_name)
            if not prefab:
                return {"success": False, "error": f"Prefab '{prefab_name}' not found"}

            if prefab.state != PrefabState.ACTIVE:
                return {"success": False, "error": f"Prefab '{prefab_name}' is {prefab.state.value}"}

            # Build property overrides
            property_overrides = []
            if overrides:
                for path, value in overrides.items():
                    original = self._get_nested_property(prefab.properties, path)
                    property_overrides.append(PropertyOverride(
                        property_path=path,
                        original_value=original,
                        override_value=value,
                    ))

            instance = PrefabInstance(
                prefab_id=prefab.prefab_id,
                prefab_name=prefab_name,
                position=position,
                rotation=rotation,
                scale=scale,
                overrides=property_overrides,
                scene_id=scene_id,
            )

            self._instances[instance.instance_id] = instance
            prefab.usage_count += 1
            self._total_instantiations += 1

            return {"success": True, "instance": instance.to_dict()}

    def instantiate_many(self, prefab_name: str,
                         positions: List[Tuple[float, float, float]],
                         overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create multiple instances of a prefab."""
        instances = []
        for pos in positions:
            result = self.instantiate(prefab_name, position=pos, overrides=overrides)
            if result["success"]:
                instances.append(result["instance"])

        return {"success": True, "instances": instances, "count": len(instances)}

    def get_instance(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get a prefab instance by ID."""
        instance = self._instances.get(instance_id)
        return instance.to_dict() if instance else None

    def destroy_instance(self, instance_id: str) -> Dict[str, Any]:
        """Destroy a prefab instance."""
        with self._lock:
            if instance_id not in self._instances:
                return {"success": False, "error": "Instance not found"}
            del self._instances[instance_id]
            return {"success": True, "instance_id": instance_id}

    def list_instances(self, prefab_name: Optional[str] = None,
                       scene_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List instances, optionally filtered by prefab or scene."""
        instances = self._instances.values()
        if prefab_name:
            instances = [i for i in instances if i.prefab_name == prefab_name]
        if scene_id:
            instances = [i for i in instances if i.scene_id == scene_id]
        return [i.to_dict() for i in instances]

    def _get_nested_property(self, props: Dict[str, Any], path: str) -> Any:
        """Get a nested property value by dot-separated path."""
        parts = path.split(".")
        current = props
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    # -------------------------------------------------------------------------
    # Variant Management
    # -------------------------------------------------------------------------

    def create_variant(self, name: str, base_prefab_name: str,
                       overrides: Optional[Dict[str, Any]] = None,
                       description: str = "") -> Dict[str, Any]:
        """Create a variant of an existing prefab."""
        with self._lock:
            base = self._prefabs.get(base_prefab_name)
            if not base:
                return {"success": False, "error": f"Base prefab '{base_prefab_name}' not found"}

            property_overrides = []
            if overrides:
                for path, value in overrides.items():
                    original = self._get_nested_property(base.properties, path)
                    property_overrides.append(PropertyOverride(
                        property_path=path,
                        original_value=original,
                        override_value=value,
                    ))

            variant = PrefabVariant(
                name=name,
                base_prefab_id=base.prefab_id,
                description=description,
                overrides=property_overrides,
            )

            self._variants[name] = variant
            return {"success": True, "variant": variant.to_dict()}

    def get_variant(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a variant by name."""
        variant = self._variants.get(name)
        return variant.to_dict() if variant else None

    def list_variants(self, base_prefab_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List variants, optionally filtered by base prefab."""
        variants = self._variants.values()
        if base_prefab_name:
            base = self._prefabs.get(base_prefab_name)
            if base:
                variants = [v for v in variants if v.base_prefab_id == base.prefab_id]
        return [v.to_dict() for v in variants]

    # -------------------------------------------------------------------------
    # Library Management
    # -------------------------------------------------------------------------

    def create_library(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new prefab library."""
        with self._lock:
            if name in self._libraries:
                return {"success": False, "error": f"Library '{name}' already exists"}
            library = PrefabLibrary(name=name, description=description)
            self._libraries[name] = library
            return {"success": True, "library": library.to_dict()}

    def add_to_library(self, library_name: str, prefab_name: str) -> Dict[str, Any]:
        """Add a prefab to a library."""
        with self._lock:
            library = self._libraries.get(library_name)
            if not library:
                return {"success": False, "error": f"Library '{library_name}' not found"}

            prefab = self._prefabs.get(prefab_name)
            if not prefab:
                return {"success": False, "error": f"Prefab '{prefab_name}' not found"}

            library.prefabs[prefab_name] = prefab
            return {"success": True, "library": library_name, "prefab": prefab_name}

    def list_libraries(self) -> List[Dict[str, Any]]:
        """List all prefab libraries."""
        return [lib.to_dict() for lib in self._libraries.values()]

    # -------------------------------------------------------------------------
    # AI-Driven Prefab Generation
    # -------------------------------------------------------------------------

    def generate_prefabs(self, description: str, count: int = 5) -> Dict[str, Any]:
        """Generate prefabs from a natural language description."""
        generated = []

        # Parse description keywords
        desc_lower = description.lower()
        categories = {
            "character": PrefabCategory.CHARACTER,
            "enemy": PrefabCategory.CHARACTER,
            "player": PrefabCategory.CHARACTER,
            "npc": PrefabCategory.CHARACTER,
            "item": PrefabCategory.ITEM,
            "weapon": PrefabCategory.ITEM,
            "collectible": PrefabCategory.ITEM,
            "platform": PrefabCategory.ENVIRONMENT,
            "building": PrefabCategory.ENVIRONMENT,
            "effect": PrefabCategory.EFFECT,
            "particle": PrefabCategory.EFFECT,
            "ui": PrefabCategory.UI,
            "button": PrefabCategory.UI,
            "camera": PrefabCategory.CAMERA,
            "trigger": PrefabCategory.TRIGGER,
        }

        detected_category = PrefabCategory.CUSTOM
        for keyword, cat in categories.items():
            if keyword in desc_lower:
                detected_category = cat
                break

        # Generate prefabs based on description
        for i in range(count):
            name = f"generated_{detected_category.value}_{i + 1}_{uuid.uuid4().hex[:6]}"
            components = []

            if detected_category == PrefabCategory.CHARACTER:
                if "enemy" in desc_lower:
                    components = [
                        PrefabComponent(component_type="sprite"),
                        PrefabComponent(component_type="physics_body"),
                        PrefabComponent(component_type="collider"),
                        PrefabComponent(component_type="ai_behavior"),
                    ]
                else:
                    components = [
                        PrefabComponent(component_type="sprite"),
                        PrefabComponent(component_type="physics_body"),
                        PrefabComponent(component_type="collider"),
                        PrefabComponent(component_type="controller"),
                    ]
            elif detected_category == PrefabCategory.ITEM:
                components = [
                    PrefabComponent(component_type="sprite"),
                    PrefabComponent(component_type="collider", properties={"is_trigger": True}),
                    PrefabComponent(component_type="pickup"),
                ]
            elif detected_category == PrefabCategory.ENVIRONMENT:
                components = [
                    PrefabComponent(component_type="sprite"),
                    PrefabComponent(component_type="physics_body", properties={"body_type": "static"}),
                    PrefabComponent(component_type="collider"),
                ]

            prefab = PrefabDefinition(
                name=name,
                category=detected_category,
                description=f"AI-generated: {description}",
                components=components,
                properties={"generated": True, "description": description},
                tags=[detected_category.value, "ai_generated"],
            )

            self._prefabs[name] = prefab
            generated.append(prefab.to_dict())

        return {
            "success": True,
            "generated": len(generated),
            "category": detected_category.value,
            "prefabs": generated,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def search_prefabs(self, query: str) -> List[Dict[str, Any]]:
        """Search prefabs by name, description, or tags."""
        query_lower = query.lower()
        results = []
        for prefab in self._prefabs.values():
            if (query_lower in prefab.name.lower() or
                query_lower in prefab.description.lower() or
                any(query_lower in tag.lower() for tag in prefab.tags)):
                results.append(prefab.to_dict())
        return results

    def get_status(self) -> Dict[str, Any]:
        """Get current system status."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "prefabs": len(self._prefabs),
                "instances": len(self._instances),
                "variants": len(self._variants),
                "libraries": len(self._libraries),
                "total_instantiations": self._total_instantiations,
                "categories": {c.value: len([p for p in self._prefabs.values() if p.category == c])
                              for c in PrefabCategory},
            }


# ── Module Accessor ──

def get_prefab_system() -> PrefabSystem:
    """Get the singleton prefab system instance."""
    return PrefabSystem.get_instance()