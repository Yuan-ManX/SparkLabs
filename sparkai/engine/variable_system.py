"""
SparkLabs Engine - Variable System

Structured variable management for scene-local, global, and
object-scoped data. Supports typed variables, expression
evaluation, event-driven change tracking, and structure
serialization — the data backbone for AI-generated game logic.

Architecture:
  VariableSystem
    |-- VariableScope (GLOBAL, SCENE, OBJECT, TEMPORARY)
    |-- TypedVariable (NUMBER, STRING, BOOLEAN, ARRAY, STRUCT)
    |-- ExpressionEngine (arithmetic/string/logical evaluation)
    |-- ChangeTracker (variable mutation history and undo)

Variable Types:
  - NUMBER: integer or floating point
  - STRING: text value with interpolation support
  - BOOLEAN: true/false with toggle operations
  - ARRAY: ordered collection with push/pop/splice
  - STRUCT: key-value composite with nested access

Variable Scopes:
  - GLOBAL: persists across all scenes
  - SCENE: per-scene, cleared on scene change
  - OBJECT: per-object, cleared when object destroyed
  - TEMPORARY: ephemeral, cleared each frame

Usage:
    vs = VariableSystem()
    vs.set("player_health", 100, scope=Scope.SCENE)
    vs.set("high_score", 0, scope=Scope.GLOBAL)
    vs.increment("coins", 10)
    result = vs.evaluate("$player_health > 0 and $coins >= 100")
    vs.watch("player_health", lambda old, new: update_hud(new))
"""
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


class Scope(Enum):
    GLOBAL = auto()
    SCENE = auto()
    OBJECT = auto()
    TEMPORARY = auto()


class VarType(Enum):
    NUMBER = auto()
    STRING = auto()
    BOOLEAN = auto()
    ARRAY = auto()
    STRUCT = auto()
    ANY = auto()


@dataclass
class VariableDefinition:
    name: str = ""
    var_type: VarType = VarType.ANY
    scope: Scope = Scope.SCENE
    default_value: Any = 0
    current_value: Any = None
    description: str = ""
    created_at: float = 0.0
    modified_at: float = 0.0
    version: int = 0

    def __post_init__(self):
        if self.current_value is None:
            self.current_value = self.default_value

    def set(self, value: Any) -> Any:
        old = self.current_value
        self.current_value = value
        self.modified_at = time.monotonic()
        self.version += 1
        return old

    def get_typed(self) -> Any:
        if self.var_type == VarType.NUMBER:
            try:
                return float(self.current_value)
            except (ValueError, TypeError):
                return 0.0
        elif self.var_type == VarType.STRING:
            return str(self.current_value)
        elif self.var_type == VarType.BOOLEAN:
            return bool(self.current_value)
        return self.current_value


class VariableStore:
    def __init__(self):
        self._variables: Dict[str, VariableDefinition] = {}

    def get(self, name: str, default: Any = None) -> Any:
        var = self._variables.get(name)
        return var.current_value if var else default

    def set(self, name: str, value: Any, var_type: VarType = VarType.ANY, description: str = "") -> Any:
        if name in self._variables:
            return self._variables[name].set(value)
        var = VariableDefinition(
            name=name, var_type=var_type,
            default_value=value, current_value=value,
            description=description, created_at=time.monotonic(),
            modified_at=time.monotonic(),
        )
        self._variables[name] = var
        return None

    def remove(self, name: str) -> bool:
        return self._variables.pop(name, None) is not None

    def exists(self, name: str) -> bool:
        return name in self._variables

    def get_all(self) -> Dict[str, Any]:
        return {name: var.current_value for name, var in self._variables.items()}

    def clear(self) -> None:
        self._variables.clear()

    def get_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": v.name, "type": v.var_type.name.lower(),
                "value": v.current_value, "description": v.description,
                "version": v.version,
            }
            for v in self._variables.values()
        ]


class ExpressionEngine:
    TOKEN_PATTERN = re.compile(r'\$(\w+(?:\.\w+)*)|(\d+\.?\d*)|(\band\b|\bor\b|\bnot\b)|(==|!=|>=|<=|>|<)|([+\-*/])|([()])|("[^"]*"|\'[^\']*\')|(\w+)|(\s+)')

    def __init__(self, resolver: Callable[[str], Any]):
        self._resolver = resolver

    def evaluate(self, expression: str) -> Any:
        resolved = self._resolve_variables(expression)
        try:
            return self._safe_eval(resolved)
        except Exception:
            return expression

    def evaluate_condition(self, expression: str) -> bool:
        result = self.evaluate(expression)
        if isinstance(result, bool):
            return result
        return bool(result)

    def resolve_value(self, expression: str) -> Any:
        if isinstance(expression, str) and expression.startswith("$"):
            return self._resolver(expression[1:])
        return expression

    def _resolve_variables(self, expression: str) -> str:
        def replace_var(match):
            var_path = match.group(0)[1:]
            value = self._resolver(var_path)
            if isinstance(value, str):
                return f'"{value}"'
            elif isinstance(value, bool):
                return str(value).lower()
            elif value is None:
                return "0"
            return str(value)

        return re.sub(r'\$(\w+(?:\.\w+)*)', replace_var, expression)

    def _safe_eval(self, expression: str) -> Any:
        expression = expression.replace(" and ", " and ")
        expression = expression.replace(" or ", " or ")
        expression = expression.replace(" not ", " not ")

        allowed_names = {"True": True, "False": False, "None": None}
        try:
            return eval(expression, {"__builtins__": {}}, allowed_names)
        except Exception:
            return expression


class VariableSystem:
    _instance: Optional["VariableSystem"] = None

    def __init__(self):
        self._global_store = VariableStore()
        self._scene_store = VariableStore()
        self._object_stores: Dict[str, VariableStore] = {}
        self._temporary_store = VariableStore()
        self._watchers: Dict[str, List[Callable]] = {}
        self._change_history: List[Dict[str, Any]] = []
        self._expression_engine = ExpressionEngine(self.resolve)
        self._max_history: int = 100

    @classmethod
    def get_instance(cls) -> "VariableSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def expression_engine(self) -> ExpressionEngine:
        return self._expression_engine

    def resolve(self, name: str, default: Any = None) -> Any:
        parts = name.split(".")
        root = parts[0]

        value = self._temporary_store.get(root)
        if value is not None:
            return self._resolve_path(value, parts[1:])

        value = self._scene_store.get(root)
        if value is not None:
            return self._resolve_path(value, parts[1:])

        value = self._global_store.get(root)
        if value is not None:
            return self._resolve_path(value, parts[1:])

        return default

    def _resolve_path(self, value: Any, path_parts: List[str]) -> Any:
        current = value
        for part in path_parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
        return current

    def set(
        self,
        name: str,
        value: Any,
        scope: Scope = Scope.SCENE,
        var_type: VarType = VarType.ANY,
        object_id: Optional[str] = None,
        description: str = "",
    ) -> Any:
        old_value = self.resolve(name)

        if scope == Scope.GLOBAL:
            self._global_store.set(name, value, var_type, description)
        elif scope == Scope.TEMPORARY:
            self._temporary_store.set(name, value, var_type, description)
        elif scope == Scope.OBJECT and object_id:
            store = self._object_stores.setdefault(object_id, VariableStore())
            store.set(name, value, var_type, description)
        else:
            self._scene_store.set(name, value, var_type, description)

        self._record_change(name, old_value, value, scope)
        self._notify_watchers(name, old_value, value)
        return old_value

    def get(self, name: str, scope: Optional[Scope] = None, default: Any = None) -> Any:
        if scope == Scope.GLOBAL:
            return self._global_store.get(name, default)
        elif scope == Scope.SCENE:
            return self._scene_store.get(name, default)
        elif scope == Scope.TEMPORARY:
            return self._temporary_store.get(name, default)
        return self.resolve(name, default)

    def increment(self, name: str, amount: Union[int, float] = 1, scope: Scope = Scope.SCENE) -> Any:
        current = self.get(name, scope, 0)
        try:
            new_value = float(current) + float(amount)
        except (ValueError, TypeError):
            new_value = amount
        self.set(name, new_value, scope, VarType.NUMBER)
        return new_value

    def toggle(self, name: str, scope: Scope = Scope.SCENE) -> bool:
        current = self.get(name, scope, False)
        new_value = not bool(current)
        self.set(name, new_value, scope, VarType.BOOLEAN)
        return new_value

    def push(self, name: str, value: Any, scope: Scope = Scope.SCENE) -> List[Any]:
        current = self.get(name, scope, [])
        if not isinstance(current, list):
            current = []
        current.append(value)
        self.set(name, current, scope, VarType.ARRAY)
        return current

    def evaluate(self, expression: str) -> Any:
        return self._expression_engine.evaluate(expression)

    def condition(self, expression: str) -> bool:
        return self._expression_engine.evaluate_condition(expression)

    def watch(self, name: str, callback: Callable[[Any, Any], None]) -> None:
        if name not in self._watchers:
            self._watchers[name] = []
        self._watchers[name].append(callback)

    def unwatch(self, name: str, callback: Optional[Callable] = None) -> int:
        if name not in self._watchers:
            return 0
        if callback:
            self._watchers[name] = [cb for cb in self._watchers[name] if cb != callback]
        else:
            self._watchers[name].clear()
        return len(self._watchers[name])

    def get_object_variables(self, object_id: str) -> Dict[str, Any]:
        store = self._object_stores.get(object_id)
        return store.get_all() if store else {}

    def remove_object(self, object_id: str) -> bool:
        return self._object_stores.pop(object_id, None) is not None

    def clear_scope(self, scope: Scope) -> None:
        if scope == Scope.SCENE:
            self._scene_store.clear()
        elif scope == Scope.TEMPORARY:
            self._temporary_store.clear()
        elif scope == Scope.GLOBAL:
            self._global_store.clear()

    def clear_all(self) -> None:
        self._global_store.clear()
        self._scene_store.clear()
        self._object_stores.clear()
        self._temporary_store.clear()
        self._change_history.clear()

    def get_all(self, scope: Optional[Scope] = None) -> Dict[str, Any]:
        if scope == Scope.GLOBAL:
            return self._global_store.get_all()
        elif scope == Scope.SCENE:
            return self._scene_store.get_all()
        elif scope == Scope.TEMPORARY:
            return self._temporary_store.get_all()

        result = {}
        result.update(self._global_store.get_all())
        result.update(self._scene_store.get_all())
        result.update(self._temporary_store.get_all())
        return result

    def export_json(self) -> str:
        data = {
            "global": self._global_store.get_definitions(),
            "scene": self._scene_store.get_definitions(),
            "objects": {
                oid: store.get_definitions()
                for oid, store in self._object_stores.items()
            },
        }
        return json.dumps(data, indent=2)

    def import_json(self, json_str: str) -> None:
        data = json.loads(json_str)
        for v_data in data.get("global", []):
            self._global_store.set(v_data["name"], v_data.get("value"))
        for v_data in data.get("scene", []):
            self._scene_store.set(v_data["name"], v_data.get("value"))
        for oid, vdefs in data.get("objects", {}).items():
            store = self._object_stores.setdefault(oid, VariableStore())
            for v_data in vdefs:
                store.set(v_data["name"], v_data.get("value"))

    def _record_change(self, name: str, old: Any, new: Any, scope: Scope) -> None:
        record = {
            "name": name, "old_value": old, "new_value": new,
            "scope": scope.name.lower(), "timestamp": time.time(),
        }
        self._change_history.append(record)
        if len(self._change_history) > self._max_history:
            self._change_history.pop(0)

    def _notify_watchers(self, name: str, old: Any, new: Any) -> None:
        for cb in self._watchers.get(name, []):
            try:
                cb(old, new)
            except Exception:
                pass

    def get_stats(self) -> Dict[str, Any]:
        global_vars = len(self._global_store.get_all())
        scene_vars = len(self._scene_store.get_all())
        temp_vars = len(self._temporary_store.get_all())
        obj_vars = sum(len(s.get_all()) for s in self._object_stores.values())

        return {
            "global_count": global_vars,
            "scene_count": scene_vars,
            "temporary_count": temp_vars,
            "object_count": len(self._object_stores),
            "object_variable_count": obj_vars,
            "total_variables": global_vars + scene_vars + temp_vars + obj_vars,
            "active_watchers": sum(len(w) for w in self._watchers.values()),
            "history_size": len(self._change_history),
        }


def get_variable_system() -> VariableSystem:
    return VariableSystem.get_instance()
