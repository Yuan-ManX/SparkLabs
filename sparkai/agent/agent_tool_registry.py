"""
SparkLabs Agent - Tool Registry

A singleton standardized tool schema and registry system for the SparkLabs
AI game engine. Manages tool discovery, schema validation, parameter
verification, and auto-generation of tool metadata.

Architecture:
  ToolRegistry (singleton)
    |-- ToolSchema (tool definition with parameters, return type)
    |-- ToolBinding (registered tool instance with metadata)
    |-- ToolInvocation (record of a tool call with result)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


class ToolCategory(Enum):
    GAME_ENGINE = "game_engine"
    AI_AGENT = "ai_agent"
    RENDERING = "rendering"
    AUDIO = "audio"
    PHYSICS = "physics"
    SCRIPTING = "scripting"
    UTILITY = "utility"


class ParameterType(Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ENUM = "enum"
    ARRAY = "array"
    OBJECT = "object"
    FILE_PATH = "file_path"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class ParameterSchema:
    name: str
    type: ParameterType
    description: str = ""
    required: bool = False
    default: Any = None
    enum_values: List[str] = field(default_factory=list)
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "required": self.required,
            "default": self.default,
        }
        if self.enum_values:
            result["enum_values"] = list(self.enum_values)
        if self.min_value is not None:
            result["min_value"] = self.min_value
        if self.max_value is not None:
            result["max_value"] = self.max_value
        return result


@dataclass
class ToolSchema:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.UTILITY
    parameters: List[ParameterSchema] = field(default_factory=list)
    return_type: str = "any"
    return_description: str = ""
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    is_async: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": [p.to_dict() for p in self.parameters],
            "return_type": self.return_type,
            "return_description": self.return_description,
            "tags": list(self.tags),
            "version": self.version,
            "is_async": self.is_async,
        }


@dataclass
class ToolBinding:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    schema_id: str = ""
    handler_name: str = ""
    is_active: bool = True
    registered_at: float = field(default_factory=_time_module.time)
    call_count: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "schema_id": self.schema_id,
            "handler_name": self.handler_name,
            "is_active": self.is_active,
            "registered_at": self.registered_at,
            "call_count": self.call_count,
            "last_error": self.last_error,
        }


@dataclass
class ToolInvocation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tool_name: str = ""
    schema_id: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    status: str = "success"
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "schema_id": self.schema_id,
            "parameters": dict(self.parameters),
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "timestamp": self.timestamp,
        }


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

MAX_PARAMETERS: int = 20
MAX_TOOLS_PER_CATEGORY: int = 100
INVOCATION_HISTORY_SIZE: int = 500

# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------


class ToolRegistry:
    """Standardized tool schema and registry system.

    Manages tool discovery, schema validation, parameter verification,
    and auto-generation of tool metadata for the SparkLabs AI game engine.
    """

    _instance: Optional[ToolRegistry] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> ToolRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> ToolRegistry:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._schemas: Dict[str, ToolSchema] = {}
        self._bindings: Dict[str, ToolBinding] = {}
        self._invocations: List[ToolInvocation] = []
        self._category_counts: Dict[str, int] = {
            c.value: 0 for c in ToolCategory
        }
        self._tag_index: Dict[str, List[str]] = {}

    def _get_or_create_singleton(self) -> ToolRegistry:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_schemas": len(self._schemas),
            "total_bindings": len(self._bindings),
            "active_bindings": sum(1 for b in self._bindings.values() if b.is_active),
            "total_invocations": len(self._invocations),
            "successful_invocations": sum(
                1 for i in self._invocations if i.status == "success"
            ),
            "failed_invocations": sum(
                1 for i in self._invocations if i.status == "error"
            ),
            "category_counts": dict(self._category_counts),
            "tag_index_size": sum(len(v) for v in self._tag_index.values()),
        }

    # --- Registration ---

    def register_tool(
        self,
        name: str,
        description: str,
        category: str,
        parameters: List[Dict[str, Any]],
        return_type: str = "any",
        return_description: str = "",
        tags: Optional[List[str]] = None,
    ) -> ToolSchema:
        if name in self._schemas:
            raise ValueError(f"Tool '{name}' is already registered")

        tool_category = ToolCategory(category)

        category_key = tool_category.value
        if self._category_counts.get(category_key, 0) >= MAX_TOOLS_PER_CATEGORY:
            raise ValueError(
                f"Category '{category_key}' has reached maximum tool limit "
                f"({MAX_TOOLS_PER_CATEGORY})"
            )

        if len(parameters) > MAX_PARAMETERS:
            raise ValueError(
                f"Tool '{name}' exceeds maximum parameter count "
                f"({MAX_PARAMETERS})"
            )

        parsed_params: List[ParameterSchema] = []
        for p in parameters:
            param_type = ParameterType(p.get("type", "string"))
            parsed_params.append(
                ParameterSchema(
                    name=p["name"],
                    type=param_type,
                    description=p.get("description", ""),
                    required=p.get("required", False),
                    default=p.get("default"),
                    enum_values=p.get("enum_values", []),
                    min_value=p.get("min_value"),
                    max_value=p.get("max_value"),
                )
            )

        tag_list = list(tags) if tags else []

        schema = ToolSchema(
            name=name,
            description=description,
            category=tool_category,
            parameters=parsed_params,
            return_type=return_type,
            return_description=return_description,
            tags=tag_list,
        )

        self._schemas[name] = schema
        self._category_counts[category_key] = (
            self._category_counts.get(category_key, 0) + 1
        )

        for tag in tag_list:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(name)

        return schema

    # --- Lookup ---

    def get_tool(self, name: str) -> Optional[ToolSchema]:
        return self._schemas.get(name)

    def list_tools(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[ToolSchema]:
        results: List[ToolSchema] = []

        if tag and tag in self._tag_index:
            candidates = set(self._tag_index[tag])
            for name in candidates:
                schema = self._schemas.get(name)
                if schema is not None:
                    results.append(schema)
        else:
            results = list(self._schemas.values())

        if category:
            results = [s for s in results if s.category.value == category]

        return results

    # --- Validation ---

    def validate_parameters(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        schema = self._schemas.get(tool_name)
        if schema is None:
            return False, [f"Tool '{tool_name}' not found"]

        errors: List[str] = []

        provided_keys = set(parameters.keys())
        param_map = {p.name: p for p in schema.parameters}

        for param_def in schema.parameters:
            if param_def.required and param_def.name not in provided_keys:
                errors.append(
                    f"Missing required parameter: '{param_def.name}'"
                )

        for key, value in parameters.items():
            if key not in param_map:
                errors.append(f"Unknown parameter: '{key}'")
                continue

            param_def = param_map[key]
            valid, msg = self._validate_parameter(param_def, value)
            if not valid:
                errors.append(f"Parameter '{key}': {msg}")

        return len(errors) == 0, errors

    def _validate_parameter(
        self,
        param_def: ParameterSchema,
        value: Any,
    ) -> Tuple[bool, str]:
        if value is None:
            if param_def.required:
                return False, "required parameter cannot be None"
            return True, ""

        ptype = param_def.type

        if ptype == ParameterType.STRING:
            if not isinstance(value, str):
                return False, f"expected string, got {type(value).__name__}"
        elif ptype == ParameterType.INTEGER:
            if not isinstance(value, int) or isinstance(value, bool):
                return False, f"expected integer, got {type(value).__name__}"
            if param_def.min_value is not None and value < param_def.min_value:
                return False, f"value {value} below minimum {param_def.min_value}"
            if param_def.max_value is not None and value > param_def.max_value:
                return False, f"value {value} above maximum {param_def.max_value}"
        elif ptype == ParameterType.FLOAT:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return False, f"expected float, got {type(value).__name__}"
            if param_def.min_value is not None and value < param_def.min_value:
                return False, f"value {value} below minimum {param_def.min_value}"
            if param_def.max_value is not None and value > param_def.max_value:
                return False, f"value {value} above maximum {param_def.max_value}"
        elif ptype == ParameterType.BOOLEAN:
            if not isinstance(value, bool):
                return False, f"expected boolean, got {type(value).__name__}"
        elif ptype == ParameterType.ENUM:
            if not isinstance(value, str):
                return False, f"expected string for enum, got {type(value).__name__}"
            if param_def.enum_values and value not in param_def.enum_values:
                return False, (
                    f"value '{value}' not in allowed values: "
                    f"{param_def.enum_values}"
                )
        elif ptype == ParameterType.ARRAY:
            if not isinstance(value, list):
                return False, f"expected array, got {type(value).__name__}"
        elif ptype == ParameterType.OBJECT:
            if not isinstance(value, dict):
                return False, f"expected object, got {type(value).__name__}"
        elif ptype == ParameterType.FILE_PATH:
            if not isinstance(value, str):
                return False, f"expected file path string, got {type(value).__name__}"

        return True, ""

    # --- Invocation Tracking ---

    def record_invocation(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Any,
        error: Optional[str],
        duration_ms: float,
    ) -> ToolInvocation:
        schema = self._schemas.get(tool_name)
        schema_id = schema.id if schema else ""

        invocation = ToolInvocation(
            tool_name=tool_name,
            schema_id=schema_id,
            parameters=dict(parameters),
            result=result,
            error=error,
            duration_ms=duration_ms,
            status="error" if error else "success",
        )

        self._invocations.append(invocation)

        if len(self._invocations) > INVOCATION_HISTORY_SIZE:
            self._invocations = self._invocations[-INVOCATION_HISTORY_SIZE:]

        if schema_id and schema_id in self._bindings:
            binding = self._bindings[schema_id]
            binding.call_count += 1
            if error:
                binding.last_error = error

        return invocation

    # --- OpenAI Schema Generation ---

    def generate_openai_schema(self, tool_name: str) -> Dict[str, Any]:
        schema = self._schemas.get(tool_name)
        if schema is None:
            raise ValueError(f"Tool '{tool_name}' not found")

        properties: Dict[str, Any] = {}
        required_list: List[str] = []

        for param in schema.parameters:
            prop: Dict[str, Any] = {
                "description": param.description,
            }

            ptype = param.type
            if ptype == ParameterType.STRING:
                prop["type"] = "string"
            elif ptype == ParameterType.INTEGER:
                prop["type"] = "integer"
            elif ptype == ParameterType.FLOAT:
                prop["type"] = "number"
            elif ptype == ParameterType.BOOLEAN:
                prop["type"] = "boolean"
            elif ptype == ParameterType.ENUM:
                prop["type"] = "string"
                if param.enum_values:
                    prop["enum"] = list(param.enum_values)
            elif ptype == ParameterType.ARRAY:
                prop["type"] = "array"
            elif ptype == ParameterType.OBJECT:
                prop["type"] = "object"
            elif ptype == ParameterType.FILE_PATH:
                prop["type"] = "string"

            if param.default is not None:
                prop["default"] = param.default

            properties[param.name] = prop

            if param.required:
                required_list.append(param.name)

        function_def: Dict[str, Any] = {
            "name": schema.name,
            "description": schema.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required_list,
            },
        }

        return {
            "type": "function",
            "function": function_def,
        }

    # --- Binding Management ---

    def bind_handler(
        self,
        tool_name: str,
        handler_name: str,
    ) -> ToolBinding:
        schema = self._schemas.get(tool_name)
        if schema is None:
            raise ValueError(f"Tool '{tool_name}' not found")

        binding = ToolBinding(
            schema_id=schema.id,
            handler_name=handler_name,
        )
        self._bindings[schema.id] = binding
        return binding

    def unbind_handler(self, tool_name: str) -> None:
        schema = self._schemas.get(tool_name)
        if schema is None:
            return
        binding = self._bindings.get(schema.id)
        if binding is not None:
            binding.is_active = False

    def get_binding(self, tool_name: str) -> Optional[ToolBinding]:
        schema = self._schemas.get(tool_name)
        if schema is None:
            return None
        return self._bindings.get(schema.id)

    # --- Management ---

    def unregister_tool(self, name: str) -> bool:
        schema = self._schemas.pop(name, None)
        if schema is None:
            return False

        category_key = schema.category.value
        self._category_counts[category_key] = max(
            0, self._category_counts.get(category_key, 0) - 1
        )

        for tag in schema.tags:
            if tag in self._tag_index:
                names = self._tag_index[tag]
                if name in names:
                    names.remove(name)

        self._bindings.pop(schema.id, None)

        return True

    def get_invocation_history(
        self,
        tool_name: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[ToolInvocation]:
        results = list(self._invocations)
        if tool_name:
            results = [
                i for i in results if i.tool_name == tool_name
            ]
        if limit is not None and limit > 0:
            results = results[-limit:]
        return results


def get_tool_registry() -> ToolRegistry:
    return ToolRegistry.get_instance()