"""
SparkLabs Agent - Variable Introspection Engine

Multi-scope variable system providing AI agents with structured
awareness of game state. Manages variable definitions across
global, scene, object, temporary, and persistent scopes with
typed value tracking, versioned snapshots, and diff computation.

Architecture:
  VariableIntrospectionEngine
    |-- Registry (variable definition catalog with scope indexing)
    |-- Instance Store (per-scope value instances with versioning)
    |-- AI Context Builder (scope-filtered human-readable state dumps)
    |-- Snapshot Engine (point-in-time state capture and diffing)
    |-- Watch System (callback registration for value changes)

Variable kinds span numbers, strings, booleans, structures,
arrays, references, colors, and vector types to cover all
common game engine data representations.
"""

from __future__ import annotations

import copy
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class VariableScope(Enum):
    GLOBAL = "global"
    SCENE = "scene"
    OBJECT = "object"
    TEMPORARY = "temporary"
    PERSISTENT = "persistent"


class VariableKind(Enum):
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    STRUCTURE = "structure"
    ARRAY = "array"
    REFERENCE = "reference"
    COLOR = "color"
    VECTOR2 = "vector2"
    VECTOR3 = "vector3"


@dataclass
class VariableDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    scope: VariableScope = VariableScope.GLOBAL
    kind: VariableKind = VariableKind.NUMBER
    default_value: Any = 0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""
    is_readonly: bool = False
    is_hidden: bool = False
    tags: List[str] = field(default_factory=list)
    ai_visible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "scope": self.scope.value,
            "kind": self.kind.value,
            "default_value": self.default_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "description": self.description[:100],
            "is_readonly": self.is_readonly,
            "is_hidden": self.is_hidden,
            "tags": self.tags,
            "ai_visible": self.ai_visible,
        }


@dataclass
class VariableInstance:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    definition_id: str = ""
    current_value: Any = None
    scope: VariableScope = VariableScope.GLOBAL
    owner_id: str = ""
    last_modified: float = field(default_factory=time.time)
    modified_by: str = ""
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "definition_id": self.definition_id,
            "current_value": str(self.current_value)[:80],
            "scope": self.scope.value,
            "owner_id": self.owner_id,
            "last_modified": self.last_modified,
            "modified_by": self.modified_by,
            "version": self.version,
        }


class VariableIntrospectionEngine:
    """Multi-scope variable system for AI state awareness."""

    _instance: Optional["VariableIntrospectionEngine"] = None
    _lock = threading.Lock()

    MAX_DEFINITIONS = 1000
    MAX_INSTANCES = 5000

    def __init__(self):
        self._definitions: Dict[str, VariableDefinition] = {}
        self._instances: Dict[str, VariableInstance] = {}
        self._def_by_scope: Dict[VariableScope, List[str]] = defaultdict(list)
        self._inst_by_def: Dict[str, List[str]] = defaultdict(list)
        self._name_index: Dict[str, str] = {}
        self._watchers: Dict[str, List[str]] = defaultdict(list)
        self._total_snapshots: int = 0

    @classmethod
    def get_instance(cls) -> "VariableIntrospectionEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def register_variable(
        self,
        name: str,
        scope: VariableScope,
        kind: VariableKind,
        default: Any,
        description: str = "",
    ) -> Optional[VariableDefinition]:
        if len(self._definitions) >= self.MAX_DEFINITIONS:
            return None

        defn = VariableDefinition(
            name=name,
            scope=scope,
            kind=kind,
            default_value=default,
            description=description,
        )

        self._definitions[defn.id] = defn
        self._def_by_scope[scope].append(defn.id)
        self._name_index[f"{scope.value}:{name}"] = defn.id

        instance = VariableInstance(
            definition_id=defn.id,
            current_value=default,
            scope=scope,
            version=1,
        )
        self._instances[instance.id] = instance
        self._inst_by_def[defn.id].append(instance.id)

        return defn

    def set_value(
        self, definition_id: str, value: Any, actor: str = ""
    ) -> Optional[VariableInstance]:
        defn = self._definitions.get(definition_id)
        if defn is None:
            return None
        if defn.is_readonly:
            return None

        if defn.min_value is not None and isinstance(value, (int, float)):
            if value < defn.min_value:
                value = defn.min_value
        if defn.max_value is not None and isinstance(value, (int, float)):
            if value > defn.max_value:
                value = defn.max_value

        instance_ids = self._inst_by_def.get(definition_id, [])
        if not instance_ids:
            return None

        instance_id = instance_ids[0]
        instance = self._instances.get(instance_id)
        if instance is None:
            return None

        instance.current_value = value
        instance.last_modified = time.time()
        instance.modified_by = actor
        instance.version += 1

        for callback_id in self._watchers.get(definition_id, []):
            pass

        return instance

    def get_value(self, definition_id: str) -> Any:
        instance_ids = self._inst_by_def.get(definition_id, [])
        if not instance_ids:
            return None
        instance = self._instances.get(instance_ids[0])
        if instance is None:
            return None
        return instance.current_value

    def get_ai_context(self, scope: VariableScope) -> str:
        lines: List[str] = []
        lines.append(f"=== Variable Scope: {scope.value} ===")

        def_ids = self._def_by_scope.get(scope, [])
        for def_id in def_ids:
            defn = self._definitions.get(def_id)
            if defn is None or not defn.ai_visible or defn.is_hidden:
                continue
            instance_ids = self._inst_by_def.get(def_id, [])
            value = None
            if instance_ids:
                inst = self._instances.get(instance_ids[0])
                if inst:
                    value = inst.current_value
            lines.append(
                f"  {defn.name} ({defn.kind.value}): {value}"
                + (f" [{defn.description}]" if defn.description else "")
            )

        return "\n".join(lines)

    def snapshot_state(self) -> dict:
        snapshot: Dict[str, Any] = {}
        for scope in VariableScope:
            scope_data: Dict[str, Any] = {}
            def_ids = self._def_by_scope.get(scope, [])
            for def_id in def_ids:
                defn = self._definitions.get(def_id)
                if defn is None:
                    continue
                instance_ids = self._inst_by_def.get(def_id, [])
                value = None
                version = 0
                if instance_ids:
                    inst = self._instances.get(instance_ids[0])
                    if inst:
                        value = inst.current_value
                        version = inst.version
                scope_data[defn.name] = {
                    "value": value,
                    "version": version,
                    "kind": defn.kind.value,
                }
            snapshot[scope.value] = scope_data

        self._total_snapshots += 1
        return {
            "snapshot_id": uuid.uuid4().hex[:12],
            "timestamp": time.time(),
            "data": snapshot,
        }

    def diff_state(self, snapshot_a: dict, snapshot_b: dict) -> dict:
        diffs: List[Dict[str, Any]] = []
        data_a = snapshot_a.get("data", {})
        data_b = snapshot_b.get("data", {})

        for scope_value in set(data_a.keys()) | set(data_b.keys()):
            vars_a = data_a.get(scope_value, {})
            vars_b = data_b.get(scope_value, {})
            for var_name in set(vars_a.keys()) | set(vars_b.keys()):
                val_a = vars_a.get(var_name, {})
                val_b = vars_b.get(var_name, {})
                if val_a.get("value") != val_b.get("value"):
                    diffs.append({
                        "scope": scope_value,
                        "variable": var_name,
                        "old_value": val_a.get("value"),
                        "new_value": val_b.get("value"),
                        "old_version": val_a.get("version"),
                        "new_version": val_b.get("version"),
                    })

        return {
            "snapshot_a_id": snapshot_a.get("snapshot_id"),
            "snapshot_b_id": snapshot_b.get("snapshot_id"),
            "total_diffs": len(diffs),
            "diffs": diffs,
        }

    def watch_variable(self, definition_id: str, callback_id: str = "") -> bool:
        if definition_id not in self._definitions:
            return False
        watch_id = callback_id or uuid.uuid4().hex[:8]
        self._watchers[definition_id].append(watch_id)
        return True

    def get_stats(self) -> dict:
        scope_counts: Dict[str, int] = defaultdict(int)
        kind_counts: Dict[str, int] = defaultdict(int)
        for defn in self._definitions.values():
            scope_counts[defn.scope.value] += 1
            kind_counts[defn.kind.value] += 1

        total_watchers = sum(len(w) for w in self._watchers.values())

        return {
            "total_definitions": len(self._definitions),
            "total_instances": len(self._instances),
            "scope_distribution": dict(scope_counts),
            "kind_distribution": dict(kind_counts),
            "total_snapshots_taken": self._total_snapshots,
            "active_watchers": total_watchers,
            "max_definitions": self.MAX_DEFINITIONS,
            "max_instances": self.MAX_INSTANCES,
        }


def get_variable_introspection() -> VariableIntrospectionEngine:
    return VariableIntrospectionEngine.get_instance()