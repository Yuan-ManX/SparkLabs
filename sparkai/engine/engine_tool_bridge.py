"""
SparkLabs Engine - Agent Tool Bridge

Bridge layer that exposes engine operations as callable tool functions
for AI agents. Agents interact with the engine through a unified tool
protocol rather than direct engine API calls, providing abstraction,
validation, and safety boundaries.

Architecture:
  AgentToolBridge
    |-- ToolRegistry (discoverable tool listing with schemas)
    |-- PermissionManager (capability-based access control)
    |-- ResultFormatter (structured output for agent consumption)
    |-- RateLimiter (prevent runaway agent operations)
    |-- AuditLogger (record all agent-engine interactions)

Tool Categories:
  - scene_manipulation: create, modify, arrange scene objects
  - entity_operations: spawn, delete, transform entities
  - component_management: add, remove, configure components
  - resource_handling: load, unload, reference assets
  - inspector_access: read properties and runtime state
  - build_control: trigger builds, exports, packaging
  - playback_control: play, pause, step game simulation
"""

from __future__ import annotations

import functools
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ToolCategory(Enum):
    SCENE = "scene_manipulation"
    ENTITY = "entity_operations"
    COMPONENT = "component_management"
    RESOURCE = "resource_handling"
    INSPECTOR = "inspector_access"
    BUILD = "build_control"
    PLAYBACK = "playback_control"
    META = "meta_tools"


class ToolPermission(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class ToolSchema:
    name: str
    description: str
    category: ToolCategory
    parameters: List[Dict[str, Any]]
    returns: Dict[str, str]
    permission_required: ToolPermission = ToolPermission.READ
    estimated_cost_ms: float = 10.0
    idempotent: bool = False
    deprecated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters,
            "returns": self.returns,
            "permission_required": self.permission_required.value,
            "estimated_cost_ms": self.estimated_cost_ms,
            "idempotent": self.idempotent,
            "deprecated": self.deprecated,
        }


@dataclass
class ToolInvocation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tool_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    source_agent: str = ""
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    success: bool = False
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "parameters_summary": {k: str(v)[:50] for k, v in list(self.parameters.items())[:5]},
            "source_agent": self.source_agent,
            "duration_ms": round(self.duration_ms, 2),
            "success": self.success,
            "result": self.result,
            "error": self.error,
        }


BUILTIN_TOOLS: Dict[str, Dict[str, Any]] = {
    "scene.list_entities": {
        "description": "List all entities in the current scene with optional filtering",
        "category": ToolCategory.SCENE,
        "parameters": [
            {"name": "scene_name", "type": "string", "required": False, "description": "Scene to query"},
            {"name": "entity_type", "type": "string", "required": False, "description": "Filter by entity type"},
            {"name": "tag_filter", "type": "string", "required": False, "description": "Filter by tag"},
            {"name": "limit", "type": "integer", "required": False, "description": "Max results (default 50)"},
        ],
        "returns": {"entities": "array of entity descriptors"},
        "permission": ToolPermission.READ,
        "idempotent": True,
    },
    "scene.find_entity_by_name": {
        "description": "Locate an entity by its display name or ID prefix",
        "category": ToolCategory.SCENE,
        "parameters": [
            {"name": "name", "type": "string", "required": True, "description": "Entity name or ID prefix"},
            {"name": "scene_name", "type": "string", "required": False, "description": "Scope to specific scene"},
        ],
        "returns": {"entity": "matched entity descriptor or null"},
        "permission": ToolPermission.READ,
        "idempotent": True,
    },
    "entity.create": {
        "description": "Spawn a new game entity with specified type and initial properties",
        "category": ToolCategory.ENTITY,
        "parameters": [
            {"name": "entity_type", "type": "string", "required": True, "description": "Type: sprite, mesh, light, camera, etc."},
            {"name": "name", "type": "string", "required": False, "description": "Display name"},
            {"name": "position", "type": "array", "required": False, "description": "[x, y, z] world position"},
            {"name": "properties", "type": "object", "required": False, "description": "Initial property overrides"},
        ],
        "returns": {"entity_id": "string"},
        "permission": ToolPermission.WRITE,
    },
    "entity.delete": {
        "description": "Remove an entity from the scene",
        "category": ToolCategory.ENTITY,
        "parameters": [
            {"name": "entity_id", "type": "string", "required": True, "description": "Target entity ID"},
            {"name": "recursive", "type": "boolean", "required": False, "description": "Also delete children"},
        ],
        "returns": {"deleted_count": "integer"},
        "permission": ToolPermission.WRITE,
    },
    "entity.transform": {
        "description": "Set or modify an entity's transform (position, rotation, scale)",
        "category": ToolCategory.ENTITY,
        "parameters": [
            {"name": "entity_id", "type": "string", "required": True, "description": "Target entity ID"},
            {"name": "position", "type": "array", "required": False, "description": "[x, y, z]"},
            {"name": "rotation", "type": "array", "required": False, "description": "[x, y, z] euler angles"},
            {"name": "scale", "type": "array", "required": False, "description": "[x, y, z]"},
            {"name": "relative", "type": "boolean", "required": False, "description": "Apply relative to current"},
        ],
        "returns": {"transform": "new transform values"},
        "permission": ToolPermission.WRITE,
    },
    "entity.duplicate": {
        "description": "Clone an existing entity with optional offset",
        "category": ToolCategory.ENTITY,
        "parameters": [
            {"name": "entity_id", "type": "string", "required": True, "description": "Source entity"},
            {"name": "offset", "type": "array", "required": False, "description": "[x, y, z] position offset"},
            {"name": "count", "type": "integer", "required": False, "description": "Number of copies"},
        ],
        "returns": {"entity_ids": "array of new entity IDs"},
        "permission": ToolPermission.WRITE,
    },
    "component.add": {
        "description": "Attach a component to an entity",
        "category": ToolCategory.COMPONENT,
        "parameters": [
            {"name": "entity_id", "type": "string", "required": True},
            {"name": "component_type", "type": "string", "required": True, "description": "e.g., RigidBody, Collider, Script"},
            {"name": "config", "type": "object", "required": False, "description": "Component configuration"},
        ],
        "returns": {"component_id": "string"},
        "permission": ToolPermission.WRITE,
    },
    "component.remove": {
        "description": "Detach a component from an entity",
        "category": ToolCategory.COMPONENT,
        "parameters": [
            {"name": "entity_id", "type": "string", "required": True},
            {"name": "component_type", "type": "string", "required": True},
        ],
        "returns": {"removed": "boolean"},
        "permission": ToolPermission.WRITE,
    },
    "component.list": {
        "description": "List all components attached to an entity",
        "category": ToolCategory.COMPONENT,
        "parameters": [
            {"name": "entity_id", "type": "string", "required": True},
        ],
        "returns": {"components": "array of component descriptors"},
        "permission": ToolPermission.READ,
        "idempotent": True,
    },
    "inspector.get_property": {
        "description": "Read a property value from an entity or component",
        "category": ToolCategory.INSPECTOR,
        "parameters": [
            {"name": "entity_id", "type": "string", "required": True},
            {"name": "property_path", "type": "string", "required": True, "description": "Dot-notation path: transform.position.x"},
        ],
        "returns": {"value": "any"},
        "permission": ToolPermission.READ,
        "idempotent": True,
    },
    "inspector.set_property": {
        "description": "Set a property value on an entity or component",
        "category": ToolCategory.INSPECTOR,
        "parameters": [
            {"name": "entity_id", "type": "string", "required": True},
            {"name": "property_path", "type": "string", "required": True},
            {"name": "value", "type": "any", "required": True},
        ],
        "returns": {"previous_value": "any"},
        "permission": ToolPermission.WRITE,
    },
    "inspector.batch_get": {
        "description": "Read multiple properties across entities in one call",
        "category": ToolCategory.INSPECTOR,
        "parameters": [
            {"name": "queries", "type": "array", "required": True, "description": "[{entity_id, property_path}, ...]"},
        ],
        "returns": {"results": "array of {entity_id, property_path, value}"},
        "permission": ToolPermission.READ,
        "idempotent": True,
    },
    "resource.load": {
        "description": "Load or reference a game asset",
        "category": ToolCategory.RESOURCE,
        "parameters": [
            {"name": "asset_path", "type": "string", "required": True},
            {"name": "asset_type", "type": "string", "required": False, "description": "texture, mesh, audio, font, etc."},
        ],
        "returns": {"asset_id": "string"},
        "permission": ToolPermission.READ,
    },
    "resource.import": {
        "description": "Import an external asset into the project",
        "category": ToolCategory.RESOURCE,
        "parameters": [
            {"name": "source_path", "type": "string", "required": True},
            {"name": "destination", "type": "string", "required": False},
            {"name": "import_settings", "type": "object", "required": False},
        ],
        "returns": {"asset_id": "string"},
        "permission": ToolPermission.WRITE,
    },
    "build.trigger": {
        "description": "Start a project build with specified configuration",
        "category": ToolCategory.BUILD,
        "parameters": [
            {"name": "platform", "type": "string", "required": True, "description": "web, windows, macos, linux, android, ios"},
            {"name": "config_name", "type": "string", "required": False},
            {"name": "output_path", "type": "string", "required": False},
        ],
        "returns": {"build_id": "string"},
        "permission": ToolPermission.EXECUTE,
    },
    "build.status": {
        "description": "Check the status of a running or completed build",
        "category": ToolCategory.BUILD,
        "parameters": [
            {"name": "build_id", "type": "string", "required": True},
        ],
        "returns": {"status": "string", "progress": "float"},
        "permission": ToolPermission.READ,
        "idempotent": True,
    },
    "playback.start": {
        "description": "Enter play mode to test the game",
        "category": ToolCategory.PLAYBACK,
        "parameters": [
            {"name": "start_scene", "type": "string", "required": False},
        ],
        "returns": {"session_id": "string"},
        "permission": ToolPermission.EXECUTE,
    },
    "playback.stop": {
        "description": "Exit play mode and return to editor",
        "category": ToolCategory.PLAYBACK,
        "parameters": [],
        "returns": {"edited": "boolean"},
        "permission": ToolPermission.EXECUTE,
    },
    "playback.pause": {
        "description": "Pause the running game",
        "category": ToolCategory.PLAYBACK,
        "parameters": [],
        "returns": {"paused": "boolean"},
        "permission": ToolPermission.EXECUTE,
    },
    "playback.step": {
        "description": "Advance one frame in pause mode",
        "category": ToolCategory.PLAYBACK,
        "parameters": [],
        "returns": {"frame": "integer"},
        "permission": ToolPermission.EXECUTE,
    },
    "meta.list_tools": {
        "description": "List all available tools with their schemas",
        "category": ToolCategory.META,
        "parameters": [
            {"name": "category", "type": "string", "required": False},
            {"name": "permission", "type": "string", "required": False},
        ],
        "returns": {"tools": "array of tool schemas"},
        "permission": ToolPermission.READ,
        "idempotent": True,
    },
    "meta.describe_tool": {
        "description": "Get detailed schema for a specific tool",
        "category": ToolCategory.META,
        "parameters": [
            {"name": "tool_name", "type": "string", "required": True},
        ],
        "returns": {"schema": "tool schema object"},
        "permission": ToolPermission.READ,
        "idempotent": True,
    },
}


class AgentToolBridge:
    """
    Bridge connecting AI agents to engine capabilities via a unified
    tool-calling protocol. Agents discover, invoke, and receive results
    from engine operations through this bridge rather than calling
    engine APIs directly.

    Provides capability-based permissions, rate limiting, audit logging,
    and structured result formatting optimized for agent consumption.
    """

    _instance: Optional["AgentToolBridge"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_RATE_PER_SECOND = 50
    MAX_AUDIT_LOG = 1000
    MAX_CUSTOM_TOOLS = 200

    def __init__(self):
        self._tools: Dict[str, ToolSchema] = {}
        self._tool_handlers: Dict[str, Callable] = {}
        self._invocations: List[ToolInvocation] = []
        self._agent_permissions: Dict[str, List[ToolPermission]] = {}
        self._rate_limits: Dict[str, List[float]] = {}
        self._disabled_tools: Set[str] = set()
        self._mock_mode: bool = True
        self._total_invocations: int = 0
        self._error_count: int = 0

        self._register_builtin_tools()

    @classmethod
    def get_instance(cls) -> "AgentToolBridge":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Tool Registration
    # ------------------------------------------------------------------

    def _register_builtin_tools(self) -> None:
        for tool_name, spec in BUILTIN_TOOLS.items():
            schema = ToolSchema(
                name=tool_name,
                description=spec["description"],
                category=spec["category"],
                parameters=spec["parameters"],
                returns=spec["returns"],
                permission_required=spec["permission"],
                idempotent=spec.get("idempotent", False),
            )
            self._tools[tool_name] = schema

    def register_tool(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        parameters: List[Dict[str, Any]],
        returns: Dict[str, str],
        handler: Callable,
        permission: ToolPermission = ToolPermission.READ,
        idempotent: bool = False,
    ) -> bool:
        if name in self._tools:
            return False
        if len(self._tools) >= self.MAX_CUSTOM_TOOLS + len(BUILTIN_TOOLS):
            return False

        schema = ToolSchema(
            name=name,
            description=description,
            category=category,
            parameters=parameters,
            returns=returns,
            permission_required=permission,
            idempotent=idempotent,
        )
        self._tools[name] = schema
        self._tool_handlers[name] = handler
        return True

    def unregister_tool(self, name: str) -> bool:
        if name in BUILTIN_TOOLS:
            return False
        self._tools.pop(name, None)
        self._tool_handlers.pop(name, None)
        return True

    # ------------------------------------------------------------------
    # Tool Invocation
    # ------------------------------------------------------------------

    def invoke(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        agent_id: str = "anonymous",
    ) -> Dict[str, Any]:
        invocation = ToolInvocation(
            tool_name=tool_name,
            parameters=parameters,
            source_agent=agent_id,
        )
        start = time.time()

        # Validate tool exists
        schema = self._tools.get(tool_name)
        if schema is None:
            invocation.success = False
            invocation.error = f"Unknown tool: {tool_name}"
            invocation.duration_ms = (time.time() - start) * 1000
            self._record(invocation)
            return {"success": False, "error": invocation.error}

        if tool_name in self._disabled_tools:
            invocation.success = False
            invocation.error = f"Tool disabled: {tool_name}"
            invocation.duration_ms = (time.time() - start) * 1000
            self._record(invocation)
            return {"success": False, "error": invocation.error}

        # Permission check
        if not self._check_permission(agent_id, schema.permission_required):
            invocation.success = False
            invocation.error = f"Permission denied: need {schema.permission_required.value}"
            invocation.duration_ms = (time.time() - start) * 1000
            self._record(invocation)
            return {"success": False, "error": invocation.error}

        # Rate limit check
        if not self._check_rate_limit(agent_id):
            invocation.success = False
            invocation.error = "Rate limit exceeded"
            invocation.duration_ms = (time.time() - start) * 1000
            self._record(invocation)
            return {"success": False, "error": invocation.error}

        # Validate parameters
        validation_error = self._validate_params(schema, parameters)
        if validation_error:
            invocation.success = False
            invocation.error = validation_error
            invocation.duration_ms = (time.time() - start) * 1000
            self._record(invocation)
            return {"success": False, "error": validation_error}

        # Execute
        try:
            handler = self._tool_handlers.get(tool_name)
            if handler is not None:
                result = handler(**parameters)
            else:
                result = self._mock_execute(tool_name, parameters)

            invocation.success = True
            invocation.result = result
        except Exception as e:
            invocation.success = False
            invocation.error = str(e)
            self._error_count += 1

        invocation.duration_ms = (time.time() - start) * 1000
        self._record(invocation)

        return {
            "success": invocation.success,
            "result": invocation.result if invocation.success else None,
            "error": invocation.error,
            "tool": tool_name,
            "duration_ms": round(invocation.duration_ms, 2),
            "invocation_id": invocation.id,
        }

    def _mock_execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        results: Dict[str, Dict[str, Any]] = {
            "scene.list_entities": {
                "entities": [
                    {"id": "ent_001", "type": "sprite", "name": "Player", "position": [0, 0, 0]},
                    {"id": "ent_002", "type": "sprite", "name": "Enemy1", "position": [5, 0, 0]},
                    {"id": "ent_003", "type": "mesh", "name": "Ground", "position": [0, -2, 0]},
                    {"id": "ent_004", "type": "camera", "name": "MainCamera", "position": [0, 10, 20]},
                    {"id": "ent_005", "type": "light", "name": "SunLight", "position": [10, 20, 10]},
                ],
                "total": 5,
            },
            "scene.find_entity_by_name": {
                "entity": {"id": "ent_001", "type": "sprite", "name": params.get("name", "Player")},
                "found": True,
            },
            "entity.create": {
                "entity_id": uuid.uuid4().hex,
                "type": params.get("entity_type", "sprite"),
                "position": params.get("position", [0, 0, 0]),
            },
            "entity.delete": {
                "deleted_count": 1,
                "entity_id": params.get("entity_id", ""),
            },
            "entity.transform": {
                "entity_id": params.get("entity_id", ""),
                "transform": {
                    "position": params.get("position", [0, 0, 0]),
                    "rotation": params.get("rotation", [0, 0, 0]),
                    "scale": params.get("scale", [1, 1, 1]),
                },
            },
            "entity.duplicate": {
                "entity_ids": [uuid.uuid4().hex for _ in range(params.get("count", 1))],
                "source": params.get("entity_id", ""),
            },
            "component.add": {
                "component_id": uuid.uuid4().hex,
                "type": params.get("component_type", ""),
                "entity_id": params.get("entity_id", ""),
            },
            "component.remove": {
                "removed": True,
            },
            "component.list": {
                "components": [
                    {"type": "Transform", "id": uuid.uuid4().hex},
                    {"type": "SpriteRenderer", "id": uuid.uuid4().hex},
                    {"type": params.get("component_type", "Unknown"), "id": uuid.uuid4().hex},
                ],
            },
            "inspector.get_property": {
                "value": "mock_value",
                "entity_id": params.get("entity_id", ""),
                "property_path": params.get("property_path", ""),
            },
            "inspector.set_property": {
                "previous_value": "old_mock_value",
                "new_value": params.get("value"),
            },
            "inspector.batch_get": {
                "results": [
                    {"entity_id": q.get("entity_id", ""), "property_path": q.get("property_path", ""), "value": "batch_value"}
                    for q in params.get("queries", [])
                ],
            },
            "resource.load": {
                "asset_id": uuid.uuid4().hex,
                "path": params.get("asset_path", ""),
            },
            "resource.import": {
                "asset_id": uuid.uuid4().hex,
                "source": params.get("source_path", ""),
            },
            "build.trigger": {
                "build_id": uuid.uuid4().hex,
                "platform": params.get("platform", "web"),
            },
            "build.status": {
                "status": "completed",
                "progress": 1.0,
            },
            "playback.start": {
                "session_id": uuid.uuid4().hex,
            },
            "playback.stop": {
                "edited": False,
            },
            "playback.pause": {
                "paused": True,
            },
            "playback.step": {
                "frame": 42,
            },
            "meta.list_tools": {
                "tools": [s.to_dict() for s in self._tools.values()],
            },
            "meta.describe_tool": {
                "schema": self._tools.get(params.get("tool_name", "")),
            },
        }
        return results.get(tool_name, {"mock": True, "tool": tool_name})

    def _validate_params(self, schema: ToolSchema, params: Dict[str, Any]) -> Optional[str]:
        for param in schema.parameters:
            if param.get("required") and param["name"] not in params:
                return f"Missing required parameter: {param['name']}"
        return None

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def grant_permission(self, agent_id: str, permission: ToolPermission) -> None:
        if agent_id not in self._agent_permissions:
            self._agent_permissions[agent_id] = []
        if permission not in self._agent_permissions[agent_id]:
            self._agent_permissions[agent_id].append(permission)

    def revoke_permission(self, agent_id: str, permission: ToolPermission) -> None:
        if agent_id in self._agent_permissions:
            perms = self._agent_permissions[agent_id]
            if permission in perms:
                perms.remove(permission)

    def _check_permission(self, agent_id: str, required: ToolPermission) -> bool:
        if self._mock_mode:
            return True
        perms = self._agent_permissions.get(agent_id, [ToolPermission.READ])
        return ToolPermission.ADMIN in perms or required in perms

    # ------------------------------------------------------------------
    # Rate Limiting
    # ------------------------------------------------------------------

    def _check_rate_limit(self, agent_id: str) -> bool:
        if agent_id not in self._rate_limits:
            self._rate_limits[agent_id] = []
            return True

        now = time.time()
        window = [t for t in self._rate_limits[agent_id] if now - t < 1.0]
        self._rate_limits[agent_id] = window
        return len(window) < self.MAX_RATE_PER_SECOND

    def _record_rate(self, agent_id: str) -> None:
        if agent_id not in self._rate_limits:
            self._rate_limits[agent_id] = []
        self._rate_limits[agent_id].append(time.time())

    # ------------------------------------------------------------------
    # Audit Logging
    # ------------------------------------------------------------------

    def _record(self, invocation: ToolInvocation) -> None:
        with self._lock:
            self._invocations.append(invocation)
            while len(self._invocations) > self.MAX_AUDIT_LOG:
                self._invocations.pop(0)
            self._total_invocations += 1

    def get_audit_log(self, limit: int = 50, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        entries = self._invocations
        if agent_id:
            entries = [e for e in entries if e.source_agent == agent_id]
        return [e.to_dict() for e in entries[-limit:]]

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        permission: Optional[ToolPermission] = None,
    ) -> List[ToolSchema]:
        results = list(self._tools.values())
        if category:
            results = [t for t in results if t.category == category]
        if permission:
            results = [t for t in results if t.permission_required == permission]
        return results

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        schema = self._tools.get(tool_name)
        if schema:
            return schema.to_dict()
        return None

    def get_available_tools_for_agent(self, agent_id: str) -> List[ToolSchema]:
        agent_perms = self._agent_permissions.get(agent_id, [ToolPermission.READ])
        return [
            t for t in self._tools.values()
            if t.permission_required in agent_perms or ToolPermission.ADMIN in agent_perms
        ]

    def disable_tool(self, tool_name: str) -> None:
        self._disabled_tools.add(tool_name)

    def enable_tool(self, tool_name: str) -> None:
        self._disabled_tools.discard(tool_name)

    def set_mock_mode(self, enabled: bool) -> None:
        self._mock_mode = enabled

    def get_stats(self) -> Dict[str, Any]:
        recent = self._invocations[-100:] if self._invocations else []
        success_rate = (
            sum(1 for i in recent if i.success) / max(1, len(recent))
        ) if recent else 1.0

        categories = {}
        for inv in self._invocations:
            schema = self._tools.get(inv.tool_name)
            if schema:
                cat = schema.category.value
                categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_invocations": self._total_invocations,
            "error_count": self._error_count,
            "registered_tools": len(self._tools),
            "custom_tools": len(self._tool_handlers),
            "disabled_tools": len(self._disabled_tools),
            "recent_success_rate": round(success_rate, 3),
            "audit_log_size": len(self._invocations),
            "registered_agents": len(self._agent_permissions),
            "mock_mode": self._mock_mode,
            "invocations_by_category": categories,
            "max_rate_per_second": self.MAX_RATE_PER_SECOND,
        }


def get_agent_tool_bridge() -> AgentToolBridge:
    return AgentToolBridge.get_instance()