"""
SparkLabs Engine - Configuration Manager

Project and engine configuration system for the SparkLabs
AI-native game engine. Provides a centralized configuration
store with schema validation, environment variable resolution,
hot-reload support, and YAML/JSON serialization. AI agents
use this to manage game project settings, engine parameters,
and deployment configurations.

Architecture:
  ConfigManager
    |-- ConfigStore (layered key/value store with defaults)
    |-- ConfigSchema (JSON Schema validation for settings)
    |-- ConfigWatcher (file-based hot-reload on changes)
    |-- EnvResolver (${VAR} template substitution)
    |-- ConfigSection (project, engine, build, deploy)
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union


class ConfigScope(Enum):
    PROJECT = "project"
    ENGINE = "engine"
    BUILD = "build"
    DEPLOY = "deploy"
    RUNTIME = "runtime"
    USER = "user"


@dataclass
class ConfigEntry:
    key: str
    value: Any
    scope: ConfigScope = ConfigScope.PROJECT
    description: str = ""
    default_value: Any = None
    value_type: str = "string"
    required: bool = False
    overridden: bool = False
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "scope": self.scope.value,
            "description": self.description,
            "default_value": self.default_value,
            "value_type": self.value_type,
            "required": self.required,
        }


@dataclass
class ConfigSchema:
    schema_id: str
    properties: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)

    def validate(self, config: Dict[str, Any]) -> List[str]:
        errors = []
        for key in self.required:
            if key not in config:
                errors.append(f"Missing required field: {key}")
        for key, prop in self.properties.items():
            if key not in config:
                continue
            val = config[key]
            expected_type = prop.get("type", "string")
            if expected_type == "number" and not isinstance(val, (int, float)):
                errors.append(f"Field '{key}' should be a number, got {type(val).__name__}")
            elif expected_type == "integer" and not isinstance(val, int):
                errors.append(f"Field '{key}' should be an integer, got {type(val).__name__}")
            elif expected_type == "boolean" and not isinstance(val, bool):
                errors.append(f"Field '{key}' should be a boolean, got {type(val).__name__}")
            if "enum" in prop and val not in prop["enum"]:
                errors.append(f"Field '{key}' value '{val}' not in allowed values: {prop['enum']}")
        return errors

    def to_dict(self) -> dict:
        return {
            "schema_id": self.schema_id,
            "properties": self.properties,
            "required": self.required,
        }


class ConfigManager:
    """
    Central configuration manager for the game engine.

    Maintains a hierarchical key/value store scoped by domain
    (project, engine, build, deploy, runtime, user). Supports
    default values, environment variable overrides, schema
    validation, and hot-reload from JSON files. AI agents
    read and write configuration through this interface.
    """

    _instance: Optional["ConfigManager"] = None

    def __init__(self):
        self._entries: Dict[str, ConfigEntry] = {}
        self._schemas: Dict[str, ConfigSchema] = {}
        self._overrides: Dict[str, Any] = {}
        self._change_listeners: List[Callable] = []
        self._config_file_path: str = ""
        self._last_load_time: float = 0.0
        self._dirty: bool = False
        self._init_defaults()

    @classmethod
    def get_instance(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set(
        self,
        key: str,
        value: Any,
        scope: ConfigScope = ConfigScope.PROJECT,
        description: str = "",
        value_type: str = "",
    ) -> ConfigEntry:
        entry = self._entries.get(key, ConfigEntry(
            key=key,
            value=value,
            scope=scope,
            default_value=value,
            value_type=value_type or self._infer_type(value),
            description=description,
        ))
        entry.value = value
        entry.overridden = key in self._overrides
        entry.updated_at = time.time()
        if scope != entry.scope:
            entry.scope = scope
        if description:
            entry.description = description
        self._entries[key] = entry
        self._dirty = True
        self._notify_change(key, value)
        return entry

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._overrides:
            return self._overrides[key]
        entry = self._entries.get(key)
        return entry.value if entry else default

    def get_string(self, key: str, default: str = "") -> str:
        val = self.get(key, default)
        return str(val) if val is not None else default

    def get_int(self, key: str, default: int = 0) -> int:
        val = self.get(key, default)
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        val = self.get(key, default)
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = self.get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes", "on")
        try:
            return bool(val)
        except (ValueError, TypeError):
            return default

    def has(self, key: str) -> bool:
        return key in self._entries

    def delete(self, key: str) -> bool:
        if key in self._entries:
            del self._entries[key]
            self._overrides.pop(key, None)
            self._dirty = True
            return True
        return False

    def set_override(self, key: str, value: Any) -> None:
        self._overrides[key] = value

    def clear_overrides(self) -> None:
        self._overrides.clear()

    def list_keys(self, scope: Optional[ConfigScope] = None, prefix: str = "") -> List[str]:
        keys = []
        for key, entry in self._entries.items():
            if scope and entry.scope != scope:
                continue
            if prefix and not key.startswith(prefix):
                continue
            keys.append(key)
        return sorted(keys)

    def get_scope(self, scope: ConfigScope) -> Dict[str, Any]:
        return {
            key: entry.value
            for key, entry in self._entries.items()
            if entry.scope == scope
        }

    def get_all(self) -> Dict[str, Any]:
        result = {}
        for scope in ConfigScope:
            result[scope.value] = self.get_scope(scope)
        return result

    def register_schema(self, schema: ConfigSchema) -> None:
        self._schemas[schema.schema_id] = schema

    def validate_scope(self, scope: ConfigScope) -> List[str]:
        errors = []
        schema = self._schemas.get(f"{scope.value}_schema")
        if not schema:
            return errors
        config = self.get_scope(scope)
        errors.extend(schema.validate(config))
        return errors

    def validate_all(self) -> Dict[str, List[str]]:
        return {scope.value: self.validate_scope(scope) for scope in ConfigScope}

    def load_from_file(self, file_path: str) -> int:
        if not os.path.exists(file_path):
            return 0
        count = 0
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            for key, value in data.items():
                scope_raw = value.get("scope", "project") if isinstance(value, dict) else "project"
                try:
                    scope = ConfigScope(scope_raw)
                except ValueError:
                    scope = ConfigScope.PROJECT
                actual_value = value.get("value", value) if isinstance(value, dict) else value
                self.set(key, actual_value, scope)
                count += 1
            self._config_file_path = file_path
            self._last_load_time = time.time()
            self._dirty = False
        except (json.JSONDecodeError, IOError):
            pass
        return count

    def save_to_file(self, file_path: str = "") -> int:
        path = file_path or self._config_file_path
        if not path:
            return 0
        try:
            data = {key: {"value": entry.value, "scope": entry.scope.value}
                    for key, entry in self._entries.items()}
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            self._dirty = False
            return len(data)
        except IOError:
            return 0

    def on_change(self, listener: Callable[[str, Any], None]) -> None:
        self._change_listeners.append(listener)

    def _notify_change(self, key: str, value: Any) -> None:
        for listener in self._change_listeners:
            try:
                listener(key, value)
            except Exception:
                pass

    def _init_defaults(self) -> None:
        defaults = {
            ("project.name", "Untitled Project", ConfigScope.PROJECT),
            ("project.version", "0.1.0", ConfigScope.PROJECT),
            ("project.author", "", ConfigScope.PROJECT),
            ("render.width", 1920, ConfigScope.ENGINE),
            ("render.height", 1080, ConfigScope.ENGINE),
            ("render.target_fps", 60, ConfigScope.ENGINE),
            ("render.vsync", True, ConfigScope.ENGINE),
            ("physics.gravity_x", 0.0, ConfigScope.ENGINE),
            ("physics.gravity_y", 980.0, ConfigScope.ENGINE),
            ("physics.time_scale", 1.0, ConfigScope.ENGINE),
            ("build.target_platform", "web", ConfigScope.BUILD),
            ("build.optimization_level", "standard", ConfigScope.BUILD),
            ("deploy.base_url", "", ConfigScope.DEPLOY),
            ("runtime.debug_mode", False, ConfigScope.RUNTIME),
            ("runtime.log_level", "info", ConfigScope.RUNTIME),
        }
        for key, value, scope in defaults:
            self.set(key=key, value=value, scope=scope)

    @staticmethod
    def _infer_type(value: Any) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return "string"

    def get_stats(self) -> dict:
        return {
            "total_entries": len(self._entries),
            "by_scope": {s.value: len(self.get_scope(s)) for s in ConfigScope},
            "overrides": len(self._overrides),
            "schemas": list(self._schemas.keys()),
            "config_file": self._config_file_path,
            "dirty": self._dirty,
        }

    def reset(self) -> None:
        self._entries.clear()
        self._overrides.clear()
        self._schemas.clear()
        self._change_listeners.clear()
        self._config_file_path = ""
        self._dirty = False
        self._init_defaults()


def get_config_manager() -> ConfigManager:
    return ConfigManager.get_instance()
