"""
SparkLabs Engine - Scene Inheritance

Scene inheritance and prefab derivation system. Templates can be created
with a hierarchy of root nodes, derived from parent templates with property
overrides, and instantiated into runtime scene instances. The system
preserves derivation chains so that changes to a parent template can be
propagated to derived templates and instances.

Architecture:
  SceneInheritanceSystem (Singleton)
    |-- SceneNode      (a single node within a scene tree)
    |-- SceneTemplate  (a reusable, derivable scene definition)
    |-- SceneInstance  (a runtime instantiation of a template)
    |-- SceneInheritanceSnapshot (immutable snapshot of system state)

Lifecycle:
  1. create_template(name, root_nodes, overrides) -> SceneTemplate
  2. derive_template(parent_id, name, overrides) -> SceneTemplate
  3. instantiate(template_id) -> SceneInstance
  4. apply_overrides(instance, overrides) -> SceneInstance
  5. get_snapshot() -> SceneInheritanceSnapshot
  6. reset() -> None

Usage:
    system = get_scene_inheritance_system()
    parent = system.create_template("base_enemy", [SceneNode("n1", "root", "enemy")])
    derived = system.derive_template(parent.template_id, "fast_enemy", {"n1": {"speed": 10}})
    instance = system.instantiate(derived.template_id)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SceneNode:
    """A single node within a scene tree.

    Attributes:
        node_id: Unique identifier for the node within its scene.
        name: Human-readable name of the node.
        node_type: Type category of the node (e.g. ``enemy``, ``trigger``).
        properties: Mutable property bag for the node.
        children: List of child node ids.
    """
    node_id: str = ""
    name: str = ""
    node_type: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type,
            "properties": dict(self.properties),
            "children": list(self.children),
        }

    def clone(self) -> "SceneNode":
        """Return a deep-enough copy of this node."""
        return SceneNode(
            node_id=self.node_id,
            name=self.name,
            node_type=self.node_type,
            properties=dict(self.properties),
            children=list(self.children),
        )


@dataclass
class SceneTemplate:
    """A reusable, derivable scene definition.

    Attributes:
        template_id: Unique identifier (auto-generated).
        name: Human-readable name of the template.
        root_nodes: Top-level nodes that compose the template.
        parent_template: Identifier of the parent template, if derived.
        overrides: Property overrides applied on top of the parent template.
        version: Monotonically increasing version counter.
    """
    template_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    root_nodes: List[SceneNode] = field(default_factory=list)
    parent_template: Optional[str] = None
    overrides: Dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "root_nodes": [n.to_dict() for n in self.root_nodes],
            "parent_template": self.parent_template,
            "overrides": dict(self.overrides),
            "version": self.version,
        }


@dataclass
class SceneInstance:
    """A runtime instantiation of a scene template.

    Attributes:
        instance_id: Unique identifier (auto-generated).
        template_id: Identifier of the template this instance was built from.
        nodes: The materialized node list after overrides have been applied.
        overrides_applied: The overrides that were applied to this instance.
    """
    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    template_id: str = ""
    nodes: List[SceneNode] = field(default_factory=list)
    overrides_applied: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "template_id": self.template_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "overrides_applied": dict(self.overrides_applied),
        }


@dataclass
class SceneInheritanceSnapshot:
    """Immutable snapshot of the scene inheritance system state.

    Attributes:
        total_templates: Number of registered templates.
        total_instances: Number of instances created since the last reset.
        templates: Serialized templates captured at snapshot time.
        derivation_depth: Maximum derivation chain length observed.
        timestamp: Time the snapshot was taken.
    """
    total_templates: int = 0
    total_instances: int = 0
    templates: List[Dict[str, Any]] = field(default_factory=list)
    derivation_depth: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_templates": self.total_templates,
            "total_instances": self.total_instances,
            "templates": list(self.templates),
            "derivation_depth": self.derivation_depth,
            "timestamp": self.timestamp,
        }


# =============================================================================
# Scene Inheritance System (Singleton)
# =============================================================================


class SceneInheritanceSystem:
    """Singleton scene inheritance and prefab derivation system.

    Stores templates indexed by id, tracks derivation chains, and produces
    runtime instances by resolving parent overrides. All public methods
    are thread-safe.

    Typical usage::

        system = SceneInheritanceSystem.get_instance()
        base = system.create_template("base", [SceneNode("n1", "root", "entity")])
        child = system.derive_template(base.template_id, "child", {"n1": {"hp": 50}})
        inst = system.instantiate(child.template_id)
    """

    _instance: Optional["SceneInheritanceSystem"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "SceneInheritanceSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton.
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._initialized: bool = True
        self._templates: Dict[str, SceneTemplate] = {}
        self._instances: Dict[str, SceneInstance] = {}
        self._instance_count: int = 0

    @classmethod
    def get_instance(cls) -> "SceneInheritanceSystem":
        """Return the singleton SceneInheritanceSystem instance (thread-safe)."""
        return cls()

    # ------------------------------------------------------------------
    # Template Management
    # ------------------------------------------------------------------

    def create_template(
        self,
        name: str,
        root_nodes: Optional[List[SceneNode]] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> SceneTemplate:
        """Create and register a new top-level scene template.

        Args:
            name: Human-readable name of the template.
            root_nodes: Top-level nodes composing the template.
            overrides: Optional overrides to attach to the template.

        Returns:
            The newly created SceneTemplate.
        """
        with self._instance_lock:
            template = SceneTemplate(
                name=name,
                root_nodes=[n.clone() for n in (root_nodes or [])],
                overrides=dict(overrides) if overrides else {},
            )
            self._templates[template.template_id] = template
            return template

    def derive_template(
        self,
        parent_id: str,
        name: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> SceneTemplate:
        """Derive a new template from an existing parent template.

        The derived template inherits the parent's resolved node hierarchy
        and attaches the provided overrides on top of the parent's overrides.

        Args:
            parent_id: Identifier of the parent template.
            name: Human-readable name of the derived template.
            overrides: Property overrides to apply on top of the parent.

        Returns:
            The newly derived SceneTemplate.

        Raises:
            KeyError: If the parent template id is not registered.
        """
        with self._instance_lock:
            parent = self._templates.get(parent_id)
            if parent is None:
                raise KeyError(f"Unknown parent template: {parent_id}")

            # Resolve the effective hierarchy by walking the derivation chain.
            resolved_nodes = self._resolve_nodes(parent_id)

            merged_overrides = dict(parent.overrides)
            if overrides:
                merged_overrides = self._merge_overrides(merged_overrides, overrides)

            derived = SceneTemplate(
                name=name,
                root_nodes=resolved_nodes,
                parent_template=parent_id,
                overrides=merged_overrides,
            )
            self._templates[derived.template_id] = derived
            return derived

    def instantiate(self, template_id: str) -> SceneInstance:
        """Materialize a runtime instance from a template.

        Args:
            template_id: Identifier of the template to instantiate.

        Returns:
            A new SceneInstance with the resolved node hierarchy.

        Raises:
            KeyError: If the template id is not registered.
        """
        with self._instance_lock:
            if template_id not in self._templates:
                raise KeyError(f"Unknown template: {template_id}")

            template = self._templates[template_id]
            resolved_nodes = self._resolve_nodes(template_id)
            # Apply template overrides onto the resolved nodes.
            self._apply_overrides_to_nodes(resolved_nodes, template.overrides)

            instance = SceneInstance(
                template_id=template_id,
                nodes=resolved_nodes,
                overrides_applied=dict(template.overrides),
            )
            self._instances[instance.instance_id] = instance
            self._instance_count += 1
            return instance

    def apply_overrides(
        self,
        instance: SceneInstance,
        overrides: Dict[str, Any],
    ) -> SceneInstance:
        """Apply additional overrides to an existing instance in place.

        Args:
            instance: The instance to mutate.
            overrides: Property overrides keyed by node id.

        Returns:
            The same instance, with overrides applied and recorded.
        """
        with self._instance_lock:
            self._apply_overrides_to_nodes(instance.nodes, overrides)
            merged = self._merge_overrides(instance.overrides_applied, overrides)
            instance.overrides_applied = merged
            return instance

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_template(self, template_id: str) -> Optional[SceneTemplate]:
        """Return the template with the given id, if registered."""
        with self._instance_lock:
            return self._templates.get(template_id)

    def get_all_templates(self) -> List[SceneTemplate]:
        """Return a copy of all registered templates."""
        with self._instance_lock:
            return list(self._templates.values())

    def get_instance_by_id(self, instance_id: str) -> Optional[SceneInstance]:
        """Return the instance with the given id, if it exists."""
        with self._instance_lock:
            return self._instances.get(instance_id)

    # ------------------------------------------------------------------
    # Status and Snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current system state."""
        with self._instance_lock:
            derived = sum(
                1 for t in self._templates.values() if t.parent_template is not None
            )
            return {
                "total_templates": len(self._templates),
                "root_templates": len(self._templates) - derived,
                "derived_templates": derived,
                "total_instances": self._instance_count,
            }

    def get_snapshot(self) -> SceneInheritanceSnapshot:
        """Capture an immutable snapshot of the system state."""
        with self._instance_lock:
            templates = [t.to_dict() for t in self._templates.values()]
            max_depth = 0
            for template in self._templates.values():
                depth = self._derivation_depth(template.template_id)
                if depth > max_depth:
                    max_depth = depth
            return SceneInheritanceSnapshot(
                total_templates=len(self._templates),
                total_instances=self._instance_count,
                templates=templates,
                derivation_depth=max_depth,
                timestamp=time.time(),
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all templates, instances, and counters."""
        with self._instance_lock:
            self._templates.clear()
            self._instances.clear()
            self._instance_count = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_nodes(self, template_id: str) -> List[SceneNode]:
        """Resolve the effective node hierarchy for a template by walking
        its derivation chain and merging overrides at each level.
        """
        template = self._templates.get(template_id)
        if template is None:
            return []

        if template.parent_template is None:
            base_nodes = [n.clone() for n in template.root_nodes]
        else:
            parent_nodes = self._resolve_nodes(template.parent_template)
            base_nodes = [n.clone() for n in parent_nodes]

        # Apply this template's own overrides last so they win.
        self._apply_overrides_to_nodes(base_nodes, template.overrides)
        return base_nodes

    @staticmethod
    def _apply_overrides_to_nodes(
        nodes: List[SceneNode],
        overrides: Dict[str, Any],
    ) -> None:
        """Apply a per-node override map onto a list of nodes in place."""
        if not overrides:
            return
        node_map = {n.node_id: n for n in nodes}
        for node_id, props in overrides.items():
            node = node_map.get(node_id)
            if node is None or not isinstance(props, dict):
                continue
            for key, value in props.items():
                node.properties[key] = value

    @staticmethod
    def _merge_overrides(
        base: Dict[str, Any],
        extra: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Merge two override maps. ``extra`` takes precedence over ``base``."""
        merged = dict(base)
        for node_id, props in extra.items():
            if not isinstance(props, dict):
                merged[node_id] = props
                continue
            current = merged.get(node_id, {})
            if not isinstance(current, dict):
                current = {}
            current.update(props)
            merged[node_id] = current
        return merged

    def _derivation_depth(self, template_id: str) -> int:
        """Compute the derivation chain length for a template."""
        depth = 0
        current_id = template_id
        visited = set()
        while current_id is not None and current_id not in visited:
            visited.add(current_id)
            template = self._templates.get(current_id)
            if template is None:
                break
            if template.parent_template is None:
                break
            depth += 1
            current_id = template.parent_template
        return depth


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_scene_inheritance_system() -> SceneInheritanceSystem:
    """Return the singleton SceneInheritanceSystem instance."""
    return SceneInheritanceSystem.get_instance()
