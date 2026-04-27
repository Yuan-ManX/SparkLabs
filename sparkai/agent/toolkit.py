"""
SparkAI Agent - Tool Registry and Execution
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Awaitable


@dataclass
class ToolParameter:
    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Any = None


@dataclass
class Tool:
    name: str
    description: str = ""
    category: str = "general"
    parameters: List[ToolParameter] = field(default_factory=list)
    handler: Optional[Callable] = None
    return_type: str = "any"

    async def execute(self, params: Dict[str, Any]) -> Any:
        if self.handler is None:
            return f"Tool '{self.name}' has no handler"
        if asyncio.iscoroutinefunction(self.handler):
            return await self.handler(params)
        return self.handler(params)

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                }
                for p in self.parameters
            ],
            "return_type": self.return_type,
        }


class ToolRegistry:
    """
    Registry and execution engine for agent tools.
    Provides tool discovery, registration, and execution.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[Tool]:
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def list_categories(self) -> List[str]:
        return list(set(t.category for t in self._tools.values()))

    def get_schemas(self) -> List[Dict[str, Any]]:
        return [tool.get_schema() for tool in self._tools.values()]

    async def execute(self, name: str, params: Dict[str, Any]) -> Any:
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")
        return await tool.execute(params)


def create_engine_tools() -> List[Tool]:
    """Create built-in engine tools for game development."""

    async def create_scene(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "create_scene",
            "name": params.get("name", "Untitled Scene"),
            "status": "created",
        }

    async def create_entity(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "create_entity",
            "name": params.get("name", "Entity"),
            "position": params.get("position", [0, 0, 0]),
            "status": "created",
        }

    async def generate_asset(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "generate_asset",
            "prompt": params.get("prompt", ""),
            "asset_type": params.get("asset_type", "image"),
            "status": "generated",
        }

    async def configure_npc(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "configure_npc",
            "npc_id": params.get("npc_id", ""),
            "personality": params.get("personality", {}),
            "status": "configured",
        }

    async def generate_narrative(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "generate_narrative",
            "prompt": params.get("prompt", ""),
            "genre": params.get("genre", "fantasy"),
            "status": "generated",
        }

    async def create_workflow(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "create_workflow",
            "name": params.get("name", "Workflow"),
            "nodes": params.get("nodes", []),
            "status": "created",
        }

    async def adjust_gameplay(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "adjust_gameplay",
            "parameter": params.get("parameter", "difficulty"),
            "value": params.get("value", 1.0),
            "status": "adjusted",
        }

    async def generate_code(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "generate_code",
            "language": params.get("language", "python"),
            "prompt": params.get("prompt", ""),
            "status": "generated",
        }

    return [
        Tool(
            name="create_scene",
            description="Create a new game scene",
            category="engine",
            parameters=[
                ToolParameter(name="name", type="string", description="Scene name"),
            ],
            handler=create_scene,
        ),
        Tool(
            name="create_entity",
            description="Create a game entity in the scene",
            category="engine",
            parameters=[
                ToolParameter(name="name", type="string", description="Entity name"),
                ToolParameter(name="position", type="array", description="Position [x,y,z]", required=False),
            ],
            handler=create_entity,
        ),
        Tool(
            name="generate_asset",
            description="Generate a game asset using AI",
            category="asset",
            parameters=[
                ToolParameter(name="prompt", type="string", description="Asset description"),
                ToolParameter(name="asset_type", type="string", description="Asset type", required=False),
            ],
            handler=generate_asset,
        ),
        Tool(
            name="configure_npc",
            description="Configure an NPC's personality and behavior",
            category="npc",
            parameters=[
                ToolParameter(name="npc_id", type="string", description="NPC identifier"),
                ToolParameter(name="personality", type="object", description="Personality traits", required=False),
            ],
            handler=configure_npc,
        ),
        Tool(
            name="generate_narrative",
            description="Generate narrative content",
            category="narrative",
            parameters=[
                ToolParameter(name="prompt", type="string", description="Narrative prompt"),
                ToolParameter(name="genre", type="string", description="Story genre", required=False),
            ],
            handler=generate_narrative,
        ),
        Tool(
            name="create_workflow",
            description="Create an AI workflow graph",
            category="workflow",
            parameters=[
                ToolParameter(name="name", type="string", description="Workflow name"),
                ToolParameter(name="nodes", type="array", description="Node definitions", required=False),
            ],
            handler=create_workflow,
        ),
        Tool(
            name="adjust_gameplay",
            description="Adjust gameplay parameters",
            category="gameplay",
            parameters=[
                ToolParameter(name="parameter", type="string", description="Parameter name"),
                ToolParameter(name="value", type="number", description="New value"),
            ],
            handler=adjust_gameplay,
        ),
        Tool(
            name="generate_code",
            description="Generate game code",
            category="code",
            parameters=[
                ToolParameter(name="language", type="string", description="Programming language"),
                ToolParameter(name="prompt", type="string", description="Code description"),
            ],
            handler=generate_code,
        ),
    ]
