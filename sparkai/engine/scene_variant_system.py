"""
SparkLabs Engine - Scene Variant System

Scene variant branching and inheritance management for the
AI-native game engine. Enables inherited scene variants similar
to Godot's inherited scenes and GDevelop's scene variants.
Supports parent-child scene relationships, property override
tracking, scene diffing, and variant promotion workflows.

Architecture:
  SceneVariantSystem
    |-- SceneVariant (individual variant with inherited data)
    |-- VariantDiff (computed difference between two variants)
    |-- VariantTree (hierarchical parent-child relationship)
    |-- OverrideTracker (keypath-based property override storage)
    |-- ConflictResolver (merge conflict resolution engine)

Variant Types:
  - BASE: root variant with no parent, the source of truth
  - INHERITED: derives from a parent, may add own data
  - OVERRIDE: inherits but overrides specific parent properties
  - EXPERIMENTAL: tentative branch for testing changes
  - PUBLISHED: finalized variant ready for production use

Merge Strategies:
  - KEEP_PARENT: parent values take precedence over child overrides
  - KEEP_CHILD: child overrides take precedence over parent values
  - KEEP_BOTH: non-conflicting merges flow through, conflicts logged
  - MANUAL: conflicts require explicit resolution via resolution map
"""

from __future__ import annotations

import copy
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class VariantType(Enum):
    BASE = auto()
    INHERITED = auto()
    OVERRIDE = auto()
    EXPERIMENTAL = auto()
    PUBLISHED = auto()


class MergeStrategy(Enum):
    KEEP_PARENT = auto()
    KEEP_CHILD = auto()
    KEEP_BOTH = auto()
    MANUAL = auto()


@dataclass
class SceneVariant:
    variant_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    parent_variant_id: Optional[str] = None
    variant_type: VariantType = VariantType.BASE
    scene_data: Dict[str, Any] = field(default_factory=dict)
    overrides: Dict[str, Any] = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    modified: float = field(default_factory=time.time)
    version: int = 1
    author: str = ""

    def get_effective_data(self) -> Dict[str, Any]:
        data = copy.deepcopy(self.scene_data)
        for key_path, value in self.overrides.items():
            self._set_nested_value(data, key_path, value)
        return data

    @staticmethod
    def _set_nested_value(data: Dict[str, Any], key_path: str, value: Any) -> None:
        keys = key_path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    @staticmethod
    def _get_nested_value(data: Dict[str, Any], key_path: str) -> Any:
        keys = key_path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    @staticmethod
    def _delete_nested_value(data: Dict[str, Any], key_path: str) -> bool:
        keys = key_path.split(".")
        current = data
        for key in keys[:-1]:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return False
        if isinstance(current, dict) and keys[-1] in current:
            del current[keys[-1]]
            return True
        return False

    def collect_all_keys(self) -> Set[str]:
        keys: Set[str] = set()
        self._collect_keys(self.scene_data, "", keys)
        for key_path in self.overrides.keys():
            keys.add(key_path)
        return keys

    @staticmethod
    def _collect_keys(data: Dict[str, Any], prefix: str, keys: Set[str]) -> None:
        for key, value in data.items():
            full_path = f"{prefix}.{key}" if prefix else key
            keys.add(full_path)
            if isinstance(value, dict):
                SceneVariant._collect_keys(value, full_path, keys)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "name": self.name,
            "parent_variant_id": self.parent_variant_id,
            "variant_type": self.variant_type.name,
            "data_keys": len(self.scene_data),
            "override_count": len(self.overrides),
            "version": self.version,
            "author": self.author,
            "created": self.created,
            "modified": self.modified,
        }


@dataclass
class VariantDiff:
    diff_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    variant_a_id: str = ""
    variant_b_id: str = ""
    added_keys: List[str] = field(default_factory=list)
    removed_keys: List[str] = field(default_factory=list)
    changed_keys: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def has_changes(self) -> bool:
        return bool(self.added_keys or self.removed_keys or self.changed_keys)

    @property
    def change_count(self) -> int:
        return len(self.added_keys) + len(self.removed_keys) + len(self.changed_keys)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diff_id": self.diff_id,
            "variant_a_id": self.variant_a_id,
            "variant_b_id": self.variant_b_id,
            "added": self.added_keys,
            "removed": self.removed_keys,
            "changed": {k: {"old": str(v[0])[:80], "new": str(v[1])[:80]} for k, v in self.changed_keys.items()},
            "change_count": self.change_count,
            "timestamp": self.timestamp,
        }


class SceneVariantSystem:
    """
    Scene variant branching and inheritance management engine.

    Manages scene variants in a hierarchical tree structure where
    child variants inherit from parent scenes and may override
    specific properties. Supports creating branches, applying
    overrides, merging changes between variants, computing diffs,
    resolving conflicts, and promoting experimental variants to
    published status. AI agents use this system to explore scene
    variations while maintaining a coherent inheritance chain.
    """

    _instance: Optional["SceneVariantSystem"] = None

    def __init__(self):
        self._variants: Dict[str, SceneVariant] = {}
        self._diffs: List[VariantDiff] = []
        self._total_branches_created: int = 0
        self._total_merges: int = 0
        self._total_overrides_applied: int = 0
        self._enabled: bool = True

    @classmethod
    def get_instance(cls) -> "SceneVariantSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_variant(
        self,
        name: str,
        parent_id: Optional[str] = None,
        scene_data: Optional[Dict[str, Any]] = None,
        author: str = "",
    ) -> Optional[SceneVariant]:
        if not self._enabled:
            return None

        if parent_id is not None and parent_id not in self._variants:
            return None

        if parent_id is None:
            variant_type = VariantType.BASE
        else:
            parent = self._variants[parent_id]
            if parent.variant_type == VariantType.EXPERIMENTAL:
                variant_type = VariantType.EXPERIMENTAL
            else:
                variant_type = VariantType.INHERITED

        variant = SceneVariant(
            name=name,
            parent_variant_id=parent_id,
            variant_type=variant_type,
            scene_data=scene_data or {},
            author=author,
        )

        self._variants[variant.variant_id] = variant
        return variant

    def create_branch(
        self,
        parent_id: str,
        branch_name: str,
        author: str = "",
    ) -> Optional[SceneVariant]:
        parent = self._variants.get(parent_id)
        if parent is None:
            return None

        effective_data = parent.get_effective_data()

        branch = SceneVariant(
            name=branch_name,
            parent_variant_id=parent_id,
            variant_type=VariantType.INHERITED,
            scene_data=copy.deepcopy(effective_data),
            author=author,
        )

        self._variants[branch.variant_id] = branch
        self._total_branches_created += 1
        return branch

    def apply_override(
        self,
        variant_id: str,
        key_path: str,
        value: Any,
    ) -> bool:
        variant = self._variants.get(variant_id)
        if variant is None:
            return False

        current_value = variant._get_nested_value(variant.scene_data, key_path)

        if current_value == value:
            variant.overrides.pop(key_path, None)
            return True

        variant.overrides[key_path] = value
        variant.modified = time.time()
        variant.version += 1
        self._total_overrides_applied += 1
        return True

    def remove_override(self, variant_id: str, key_path: str) -> bool:
        variant = self._variants.get(variant_id)
        if variant is None:
            return False

        if key_path in variant.overrides:
            del variant.overrides[key_path]
            variant.modified = time.time()
            variant.version += 1
            return True
        return False

    def get_effective_value(self, variant_id: str, key_path: str) -> Any:
        variant = self._variants.get(variant_id)
        if variant is None:
            return None

        if key_path in variant.overrides:
            return variant.overrides[key_path]

        value = variant._get_nested_value(variant.scene_data, key_path)
        if value is not None:
            return value

        if variant.parent_variant_id:
            return self._resolve_from_ancestry(variant.parent_variant_id, key_path)

        return None

    def _resolve_from_ancestry(self, variant_id: str, key_path: str) -> Any:
        variant = self._variants.get(variant_id)
        if variant is None:
            return None

        if key_path in variant.overrides:
            return variant.overrides[key_path]

        value = variant._get_nested_value(variant.scene_data, key_path)
        if value is not None:
            return value

        if variant.parent_variant_id:
            return self._resolve_from_ancestry(variant.parent_variant_id, key_path)

        return None

    def merge_to_parent(
        self,
        variant_id: str,
        strategy: MergeStrategy = MergeStrategy.KEEP_CHILD,
    ) -> Optional[SceneVariant]:
        variant = self._variants.get(variant_id)
        if variant is None:
            return None

        if variant.parent_variant_id is None:
            return variant

        parent = self._variants.get(variant.parent_variant_id)
        if parent is None:
            return None

        effective_child_data = variant.get_effective_data()

        if strategy == MergeStrategy.KEEP_CHILD:
            parent.scene_data = copy.deepcopy(effective_child_data)
        elif strategy == MergeStrategy.KEEP_PARENT:
            variant.overrides.clear()
            variant.scene_data = copy.deepcopy(parent.get_effective_data())
        elif strategy == MergeStrategy.KEEP_BOTH:
            for key in variant.overrides:
                parent._set_nested_value(
                    parent.scene_data, key, variant.overrides[key]
                )
            for key_path, value in effective_child_data.items():
                if key_path not in parent.scene_data:
                    parent._set_nested_value(parent.scene_data, key_path, value)
        elif strategy == MergeStrategy.MANUAL:
            parent.scene_data = copy.deepcopy(effective_child_data)

        parent.modified = time.time()
        parent.version += 1
        self._total_merges += 1
        return parent

    def diff_variants(
        self,
        variant_a_id: str,
        variant_b_id: str,
    ) -> Optional[VariantDiff]:
        variant_a = self._variants.get(variant_a_id)
        variant_b = self._variants.get(variant_b_id)
        if variant_a is None or variant_b is None:
            return None

        diff = VariantDiff(
            variant_a_id=variant_a_id,
            variant_b_id=variant_b_id,
        )

        data_a = variant_a.get_effective_data()
        data_b = variant_b.get_effective_data()

        keys_a = variant_a.collect_all_keys()
        keys_b = variant_b.collect_all_keys()

        all_keys = keys_a | keys_b

        for key in sorted(all_keys):
            in_a = key in keys_a
            in_b = key in keys_b

            if in_a and not in_b:
                diff.removed_keys.append(key)
            elif in_b and not in_a:
                diff.added_keys.append(key)
            else:
                val_a = variant_a._get_nested_value(data_a, key)
                val_b = variant_b._get_nested_value(data_b, key)
                if val_a != val_b:
                    diff.changed_keys[key] = (val_a, val_b)

        self._diffs.append(diff)
        return diff

    def resolve_conflicts(
        self,
        variant_id: str,
        resolution_map: Dict[str, Any],
    ) -> Optional[SceneVariant]:
        variant = self._variants.get(variant_id)
        if variant is None:
            return None

        for key_path, resolved_value in resolution_map.items():
            variant._set_nested_value(variant.scene_data, key_path, resolved_value)
            variant.overrides.pop(key_path, None)

        variant.modified = time.time()
        variant.version += 1
        return variant

    def promote_to_published(self, variant_id: str) -> Optional[SceneVariant]:
        variant = self._variants.get(variant_id)
        if variant is None:
            return None

        if variant.variant_type in (VariantType.BASE, VariantType.PUBLISHED):
            return variant

        variant.variant_type = VariantType.PUBLISHED
        variant.modified = time.time()
        variant.version += 1

        return variant

    def get_variant_tree(self, root_id: str) -> Dict[str, Any]:
        variant = self._variants.get(root_id)
        if variant is None:
            return {}

        return self._build_tree_node(root_id)

    def _build_tree_node(self, variant_id: str) -> Dict[str, Any]:
        variant = self._variants[variant_id]
        children = self._find_children(variant_id)

        child_nodes = []
        for child in children:
            child_nodes.append(self._build_tree_node(child.variant_id))

        return {
            "variant_id": variant.variant_id,
            "name": variant.name,
            "variant_type": variant.variant_type.name,
            "version": variant.version,
            "override_count": len(variant.overrides),
            "children": child_nodes,
        }

    def _find_children(self, parent_id: str) -> List[SceneVariant]:
        return [
            v for v in self._variants.values()
            if v.parent_variant_id == parent_id
        ]

    def list_variants(
        self,
        variant_type: Optional[VariantType] = None,
        author: Optional[str] = None,
    ) -> List[SceneVariant]:
        result = list(self._variants.values())
        if variant_type is not None:
            result = [v for v in result if v.variant_type == variant_type]
        if author is not None:
            result = [v for v in result if v.author == author]
        return sorted(result, key=lambda v: v.modified, reverse=True)

    def get_variant(self, variant_id: str) -> Optional[SceneVariant]:
        return self._variants.get(variant_id)

    def find_variant_by_name(self, name: str) -> Optional[SceneVariant]:
        for v in self._variants.values():
            if v.name == name:
                return v
        return None

    def get_ancestry_chain(self, variant_id: str) -> List[SceneVariant]:
        chain: List[SceneVariant] = []
        current = self._variants.get(variant_id)
        while current is not None:
            chain.insert(0, current)
            if current.parent_variant_id:
                current = self._variants.get(current.parent_variant_id)
            else:
                break
        return chain

    def get_root_variant(self, variant_id: str) -> Optional[SceneVariant]:
        chain = self.get_ancestry_chain(variant_id)
        return chain[0] if chain else None

    def compute_depth(self, variant_id: str) -> int:
        depth = 0
        current = self._variants.get(variant_id)
        while current is not None and current.parent_variant_id:
            depth += 1
            current = self._variants.get(current.parent_variant_id)
        return depth

    def find_conflicts(self, variant_id: str) -> Dict[str, Any]:
        variant = self._variants.get(variant_id)
        if variant is None or variant.parent_variant_id is None:
            return {}

        parent = self._variants.get(variant.parent_variant_id)
        if parent is None:
            return {}

        parent_effective = parent.get_effective_data()

        conflicts: Dict[str, Any] = {}
        for key_path, child_value in variant.overrides.items():
            parent_value = variant._get_nested_value(parent_effective, key_path)
            if parent_value is not None and parent_value != child_value:
                conflicts[key_path] = {
                    "parent_value": parent_value,
                    "child_value": child_value,
                }

        return conflicts

    def rebase_variant(self, variant_id: str) -> Optional[SceneVariant]:
        variant = self._variants.get(variant_id)
        if variant is None or variant.parent_variant_id is None:
            return variant

        parent = self._variants.get(variant.parent_variant_id)
        if parent is None:
            return variant

        parent_effective = parent.get_effective_data()
        current_overrides = dict(variant.overrides)

        variant.scene_data = copy.deepcopy(parent_effective)
        variant.overrides.clear()

        for key_path, value in current_overrides.items():
            parent_value = variant._get_nested_value(parent_effective, key_path)
            if parent_value != value:
                variant.overrides[key_path] = value

        variant.modified = time.time()
        variant.version += 1
        return variant

    def delete_variant(self, variant_id: str) -> bool:
        children = self._find_children(variant_id)
        if children:
            first_child = children[0]
            first_child.parent_variant_id = None
            for child in children[1:]:
                child.parent_variant_id = first_child.variant_id

        if variant_id in self._variants:
            del self._variants[variant_id]
            return True
        return False

    def clone_variant(self, variant_id: str, new_name: str, author: str = "") -> Optional[SceneVariant]:
        original = self._variants.get(variant_id)
        if original is None:
            return None

        clone = SceneVariant(
            name=new_name,
            parent_variant_id=original.parent_variant_id,
            variant_type=VariantType.EXPERIMENTAL,
            scene_data=copy.deepcopy(original.scene_data),
            overrides=copy.deepcopy(original.overrides),
            author=author,
        )

        self._variants[clone.variant_id] = clone
        return clone

    def get_stats(self) -> Dict[str, Any]:
        by_type: Dict[str, int] = {}
        for v in self._variants.values():
            type_name = v.variant_type.name
            by_type[type_name] = by_type.get(type_name, 0) + 1

        max_depth = 0
        for v in self._variants.values():
            depth = self.compute_depth(v.variant_id)
            if depth > max_depth:
                max_depth = depth

        base_count = sum(1 for v in self._variants.values() if v.parent_variant_id is None)

        return {
            "total_variants": len(self._variants),
            "by_type": by_type,
            "max_depth": max_depth,
            "total_branches_created": self._total_branches_created,
            "total_merges": self._total_merges,
            "total_overrides_applied": self._total_overrides_applied,
            "total_diffs_computed": len(self._diffs),
            "base_variants": base_count,
            "enabled": self._enabled,
        }

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def reset(self) -> None:
        self._variants.clear()
        self._diffs.clear()
        self._total_branches_created = 0
        self._total_merges = 0
        self._total_overrides_applied = 0


def get_scene_variant_system() -> SceneVariantSystem:
    return SceneVariantSystem.get_instance()