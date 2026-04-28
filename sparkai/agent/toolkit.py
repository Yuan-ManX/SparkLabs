"""
SparkAI Agent - Tool Registry, Execution, and Composable Toolsets

Tools are the action interface for agents. Each tool defines a
name, parameters, and an async handler. Tools are organized into
composable toolsets that can be loaded per agent role.

Toolset composition enables:
  - Role-based tool loading (directors get orchestration tools)
  - Domain-specific tool bundles (engine, asset, npc, narrative)
  - Dynamic tool registration at runtime
  - Tool chaining and pipeline execution
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

    def load_toolset(self, tools: List[Tool]) -> None:
        for tool in tools:
            self.register(tool)

    def unload_toolset(self, tool_names: List[str]) -> None:
        for name in tool_names:
            self.unregister(name)


class Toolset:
    """
    A named, composable bundle of tools.

    Toolsets group related tools by domain or role, enabling
    agents to load capabilities in bulk rather than one by one.
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._tools: List[Tool] = []

    def add(self, tool: Tool) -> "Toolset":
        self._tools.append(tool)
        return self

    def tools(self) -> List[Tool]:
        return list(self._tools)

    def tool_names(self) -> List[str]:
        return [t.name for t in self._tools]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "tool_count": len(self._tools),
            "tools": [t.name for t in self._tools],
        }


class ToolsetRegistry:
    """
    Global registry for named toolsets.
    Agents query toolsets by name to load domain-specific capabilities.
    """

    _toolsets: Dict[str, Toolset] = {}

    @classmethod
    def register(cls, toolset: Toolset) -> None:
        cls._toolsets[toolset.name] = toolset

    @classmethod
    def get(cls, name: str) -> Optional[Toolset]:
        return cls._toolsets.get(name)

    @classmethod
    def list_toolsets(cls) -> List[Toolset]:
        return list(cls._toolsets.values())

    @classmethod
    def list_names(cls) -> List[str]:
        return list(cls._toolsets.keys())

    @classmethod
    def clear(cls) -> None:
        cls._toolsets.clear()


def create_engine_toolset() -> Toolset:
    """Core engine tools for world, entity, and scene management."""

    async def create_world(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "create_world",
            "name": params.get("name", "World"),
            "status": "created",
        }

    async def create_entity(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "create_entity",
            "name": params.get("name", "Entity"),
            "position": params.get("position", [0, 0, 0]),
            "components": params.get("components", []),
            "tags": params.get("tags", []),
            "status": "created",
        }

    async def add_component(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "add_component",
            "entity_id": params.get("entity_id", ""),
            "component_type": params.get("component_type", ""),
            "data": params.get("data", {}),
            "status": "added",
        }

    async def remove_component(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "remove_component",
            "entity_id": params.get("entity_id", ""),
            "component_type": params.get("component_type", ""),
            "status": "removed",
        }

    async def create_scene(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "create_scene",
            "name": params.get("name", "Untitled Scene"),
            "status": "created",
        }

    async def query_entities(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "query_entities",
            "filter": params.get("filter", {}),
            "status": "queried",
        }

    return Toolset("engine", "Core engine tools for world and entity management").add(Tool(
        name="create_world",
        description="Create a new ECS world",
        category="engine",
        parameters=[
            ToolParameter(name="name", type="string", description="World name"),
        ],
        handler=create_world,
    )).add(Tool(
        name="create_entity",
        description="Create a game entity in a world",
        category="engine",
        parameters=[
            ToolParameter(name="name", type="string", description="Entity name"),
            ToolParameter(name="position", type="array", description="Position [x,y,z]", required=False),
            ToolParameter(name="components", type="array", description="Initial components", required=False),
            ToolParameter(name="tags", type="array", description="Entity tags", required=False),
        ],
        handler=create_entity,
    )).add(Tool(
        name="add_component",
        description="Add a component to an entity",
        category="engine",
        parameters=[
            ToolParameter(name="entity_id", type="string", description="Target entity ID"),
            ToolParameter(name="component_type", type="string", description="Component type name"),
            ToolParameter(name="data", type="object", description="Component data", required=False),
        ],
        handler=add_component,
    )).add(Tool(
        name="remove_component",
        description="Remove a component from an entity",
        category="engine",
        parameters=[
            ToolParameter(name="entity_id", type="string", description="Target entity ID"),
            ToolParameter(name="component_type", type="string", description="Component type to remove"),
        ],
        handler=remove_component,
    )).add(Tool(
        name="create_scene",
        description="Create a new game scene",
        category="engine",
        parameters=[
            ToolParameter(name="name", type="string", description="Scene name"),
        ],
        handler=create_scene,
    )).add(Tool(
        name="query_entities",
        description="Query entities by filter criteria",
        category="engine",
        parameters=[
            ToolParameter(name="filter", type="object", description="Query filter", required=False),
        ],
        handler=query_entities,
    ))


def create_asset_toolset() -> Toolset:
    """Asset generation and management tools."""

    async def generate_asset(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "generate_asset",
            "prompt": params.get("prompt", ""),
            "asset_type": params.get("asset_type", "image"),
            "style": params.get("style", "default"),
            "status": "generated",
        }

    async def import_asset(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "import_asset",
            "path": params.get("path", ""),
            "asset_type": params.get("asset_type", "image"),
            "status": "imported",
        }

    async def list_assets(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "list_assets",
            "filter": params.get("filter", {}),
            "status": "listed",
        }

    return Toolset("asset", "Asset generation and management tools").add(Tool(
        name="generate_asset",
        description="Generate a game asset using AI",
        category="asset",
        parameters=[
            ToolParameter(name="prompt", type="string", description="Asset description"),
            ToolParameter(name="asset_type", type="string", description="Asset type (image, mesh, audio, texture)", required=False),
            ToolParameter(name="style", type="string", description="Visual style", required=False),
        ],
        handler=generate_asset,
    )).add(Tool(
        name="import_asset",
        description="Import an external asset file",
        category="asset",
        parameters=[
            ToolParameter(name="path", type="string", description="File path"),
            ToolParameter(name="asset_type", type="string", description="Asset type", required=False),
        ],
        handler=import_asset,
    )).add(Tool(
        name="list_assets",
        description="List available assets",
        category="asset",
        parameters=[
            ToolParameter(name="filter", type="object", description="Filter criteria", required=False),
        ],
        handler=list_assets,
    ))


def create_npc_toolset() -> Toolset:
    """NPC creation, configuration, and behavior tools."""

    async def configure_npc(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "configure_npc",
            "npc_id": params.get("npc_id", ""),
            "personality": params.get("personality", {}),
            "behavior": params.get("behavior", "autonomous"),
            "status": "configured",
        }

    async def set_npc_dialogue(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "set_npc_dialogue",
            "npc_id": params.get("npc_id", ""),
            "dialogue_tree": params.get("dialogue_tree", {}),
            "status": "set",
        }

    async def set_npc_behavior(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "set_npc_behavior",
            "npc_id": params.get("npc_id", ""),
            "behavior_type": params.get("behavior_type", "autonomous"),
            "parameters": params.get("parameters", {}),
            "status": "set",
        }

    return Toolset("npc", "NPC creation and behavior tools").add(Tool(
        name="configure_npc",
        description="Configure an NPC's personality and behavior",
        category="npc",
        parameters=[
            ToolParameter(name="npc_id", type="string", description="NPC identifier"),
            ToolParameter(name="personality", type="object", description="Personality traits", required=False),
            ToolParameter(name="behavior", type="string", description="Behavior mode", required=False),
        ],
        handler=configure_npc,
    )).add(Tool(
        name="set_npc_dialogue",
        description="Set an NPC's dialogue tree",
        category="npc",
        parameters=[
            ToolParameter(name="npc_id", type="string", description="NPC identifier"),
            ToolParameter(name="dialogue_tree", type="object", description="Dialogue tree definition"),
        ],
        handler=set_npc_dialogue,
    )).add(Tool(
        name="set_npc_behavior",
        description="Set an NPC's behavior pattern",
        category="npc",
        parameters=[
            ToolParameter(name="npc_id", type="string", description="NPC identifier"),
            ToolParameter(name="behavior_type", type="string", description="Behavior type"),
            ToolParameter(name="parameters", type="object", description="Behavior parameters", required=False),
        ],
        handler=set_npc_behavior,
    ))


def create_narrative_toolset() -> Toolset:
    """Story, quest, and narrative generation tools."""

    async def generate_narrative(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "generate_narrative",
            "prompt": params.get("prompt", ""),
            "genre": params.get("genre", "fantasy"),
            "tone": params.get("tone", "epic"),
            "status": "generated",
        }

    async def create_quest(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "create_quest",
            "name": params.get("name", "Quest"),
            "quest_type": params.get("quest_type", "main"),
            "objectives": params.get("objectives", []),
            "rewards": params.get("rewards", {}),
            "status": "created",
        }

    async def create_dialogue(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "create_dialogue",
            "characters": params.get("characters", []),
            "context": params.get("context", ""),
            "tone": params.get("tone", "neutral"),
            "status": "created",
        }

    return Toolset("narrative", "Story and narrative generation tools").add(Tool(
        name="generate_narrative",
        description="Generate narrative content",
        category="narrative",
        parameters=[
            ToolParameter(name="prompt", type="string", description="Narrative prompt"),
            ToolParameter(name="genre", type="string", description="Story genre", required=False),
            ToolParameter(name="tone", type="string", description="Narrative tone", required=False),
        ],
        handler=generate_narrative,
    )).add(Tool(
        name="create_quest",
        description="Create a quest with objectives and rewards",
        category="narrative",
        parameters=[
            ToolParameter(name="name", type="string", description="Quest name"),
            ToolParameter(name="quest_type", type="string", description="Quest type (main, side, dynamic)", required=False),
            ToolParameter(name="objectives", type="array", description="Quest objectives", required=False),
            ToolParameter(name="rewards", type="object", description="Quest rewards", required=False),
        ],
        handler=create_quest,
    )).add(Tool(
        name="create_dialogue",
        description="Create dialogue between characters",
        category="narrative",
        parameters=[
            ToolParameter(name="characters", type="array", description="Character names"),
            ToolParameter(name="context", type="string", description="Dialogue context", required=False),
            ToolParameter(name="tone", type="string", description="Dialogue tone", required=False),
        ],
        handler=create_dialogue,
    ))


def create_gameplay_toolset() -> Toolset:
    """Gameplay mechanics, balance, and difficulty tools."""

    async def adjust_gameplay(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "adjust_gameplay",
            "parameter": params.get("parameter", "difficulty"),
            "value": params.get("value", 1.0),
            "scope": params.get("scope", "global"),
            "status": "adjusted",
        }

    async def create_mechanic(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "create_mechanic",
            "name": params.get("name", "Mechanic"),
            "mechanic_type": params.get("mechanic_type", "combat"),
            "rules": params.get("rules", {}),
            "status": "created",
        }

    async def balance_check(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "balance_check",
            "system": params.get("system", "combat"),
            "metrics": params.get("metrics", []),
            "status": "checked",
        }

    return Toolset("gameplay", "Gameplay mechanics and balance tools").add(Tool(
        name="adjust_gameplay",
        description="Adjust gameplay parameters",
        category="gameplay",
        parameters=[
            ToolParameter(name="parameter", type="string", description="Parameter name"),
            ToolParameter(name="value", type="number", description="New value"),
            ToolParameter(name="scope", type="string", description="Scope (global, local)", required=False),
        ],
        handler=adjust_gameplay,
    )).add(Tool(
        name="create_mechanic",
        description="Create a new gameplay mechanic",
        category="gameplay",
        parameters=[
            ToolParameter(name="name", type="string", description="Mechanic name"),
            ToolParameter(name="mechanic_type", type="string", description="Mechanic type", required=False),
            ToolParameter(name="rules", type="object", description="Mechanic rules", required=False),
        ],
        handler=create_mechanic,
    )).add(Tool(
        name="balance_check",
        description="Check game balance for a system",
        category="gameplay",
        parameters=[
            ToolParameter(name="system", type="string", description="System to check"),
            ToolParameter(name="metrics", type="array", description="Metrics to evaluate", required=False),
        ],
        handler=balance_check,
    ))


def create_code_toolset() -> Toolset:
    """Code generation, review, and refactoring tools."""

    async def generate_code(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "generate_code",
            "language": params.get("language", "python"),
            "prompt": params.get("prompt", ""),
            "context": params.get("context", ""),
            "status": "generated",
        }

    async def review_code(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "review_code",
            "code": params.get("code", ""),
            "focus": params.get("focus", "quality"),
            "status": "reviewed",
        }

    async def refactor_code(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "refactor_code",
            "code": params.get("code", ""),
            "target": params.get("target", "readability"),
            "status": "refactored",
        }

    return Toolset("code", "Code generation and review tools").add(Tool(
        name="generate_code",
        description="Generate game code",
        category="code",
        parameters=[
            ToolParameter(name="language", type="string", description="Programming language"),
            ToolParameter(name="prompt", type="string", description="Code description"),
            ToolParameter(name="context", type="string", description="Code context", required=False),
        ],
        handler=generate_code,
    )).add(Tool(
        name="review_code",
        description="Review code for quality and issues",
        category="code",
        parameters=[
            ToolParameter(name="code", type="string", description="Code to review"),
            ToolParameter(name="focus", type="string", description="Review focus (quality, security, performance)", required=False),
        ],
        handler=review_code,
    )).add(Tool(
        name="refactor_code",
        description="Refactor code for clarity or performance",
        category="code",
        parameters=[
            ToolParameter(name="code", type="string", description="Code to refactor"),
            ToolParameter(name="target", type="string", description="Refactoring target", required=False),
        ],
        handler=refactor_code,
    ))


def create_workflow_toolset() -> Toolset:
    """Workflow orchestration and pipeline tools."""

    async def create_workflow(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "create_workflow",
            "name": params.get("name", "Workflow"),
            "nodes": params.get("nodes", []),
            "connections": params.get("connections", []),
            "status": "created",
        }

    async def execute_workflow(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "execute_workflow",
            "workflow_id": params.get("workflow_id", ""),
            "inputs": params.get("inputs", {}),
            "status": "executed",
        }

    return Toolset("workflow", "Workflow orchestration tools").add(Tool(
        name="create_workflow",
        description="Create an AI workflow graph",
        category="workflow",
        parameters=[
            ToolParameter(name="name", type="string", description="Workflow name"),
            ToolParameter(name="nodes", type="array", description="Node definitions", required=False),
            ToolParameter(name="connections", type="array", description="Node connections", required=False),
        ],
        handler=create_workflow,
    )).add(Tool(
        name="execute_workflow",
        description="Execute a workflow by ID",
        category="workflow",
        parameters=[
            ToolParameter(name="workflow_id", type="string", description="Workflow ID"),
            ToolParameter(name="inputs", type="object", description="Workflow inputs", required=False),
        ],
        handler=execute_workflow,
    ))


def create_testing_toolset() -> Toolset:
    """Testing, debugging, and quality assurance tools."""

    async def run_tests(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "run_tests",
            "scope": params.get("scope", "all"),
            "test_type": params.get("test_type", "unit"),
            "status": "completed",
        }

    async def diagnose_error(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "diagnose_error",
            "error_message": params.get("error_message", ""),
            "context": params.get("context", ""),
            "status": "diagnosed",
        }

    async def validate_scene(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "validate_scene",
            "scene_id": params.get("scene_id", ""),
            "checks": params.get("checks", ["physics", "rendering", "ai"]),
            "status": "validated",
        }

    return Toolset("testing", "Testing and quality assurance tools").add(Tool(
        name="run_tests",
        description="Run test suite",
        category="testing",
        parameters=[
            ToolParameter(name="scope", type="string", description="Test scope", required=False),
            ToolParameter(name="test_type", type="string", description="Test type", required=False),
        ],
        handler=run_tests,
    )).add(Tool(
        name="diagnose_error",
        description="Diagnose an error using debug protocol",
        category="testing",
        parameters=[
            ToolParameter(name="error_message", type="string", description="Error message"),
            ToolParameter(name="context", type="string", description="Error context", required=False),
        ],
        handler=diagnose_error,
    )).add(Tool(
        name="validate_scene",
        description="Validate a scene for common issues",
        category="testing",
        parameters=[
            ToolParameter(name="scene_id", type="string", description="Scene ID"),
            ToolParameter(name="checks", type="array", description="Validation checks", required=False),
        ],
        handler=validate_scene,
    ))


def create_orchestration_toolset() -> Toolset:
    """Agent orchestration and delegation tools for directors and leads."""

    async def delegate_task(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "delegate_task",
            "task_description": params.get("task_description", ""),
            "target_role": params.get("target_role", "specialist"),
            "capability": params.get("capability", "reasoning"),
            "status": "delegated",
        }

    async def create_plan(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "create_plan",
            "goal": params.get("goal", ""),
            "steps": params.get("steps", []),
            "verification_gates": params.get("verification_gates", []),
            "status": "created",
        }

    async def review_progress(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "review_progress",
            "plan_id": params.get("plan_id", ""),
            "status": "reviewed",
        }

    return Toolset("orchestration", "Agent orchestration and delegation tools").add(Tool(
        name="delegate_task",
        description="Delegate a task to another agent",
        category="orchestration",
        parameters=[
            ToolParameter(name="task_description", type="string", description="Task to delegate"),
            ToolParameter(name="target_role", type="string", description="Target agent role", required=False),
            ToolParameter(name="capability", type="string", description="Required capability", required=False),
        ],
        handler=delegate_task,
    )).add(Tool(
        name="create_plan",
        description="Create an execution plan",
        category="orchestration",
        parameters=[
            ToolParameter(name="goal", type="string", description="Plan goal"),
            ToolParameter(name="steps", type="array", description="Plan steps", required=False),
            ToolParameter(name="verification_gates", type="array", description="Verification criteria", required=False),
        ],
        handler=create_plan,
    )).add(Tool(
        name="review_progress",
        description="Review progress on a plan",
        category="orchestration",
        parameters=[
            ToolParameter(name="plan_id", type="string", description="Plan ID"),
        ],
        handler=review_progress,
    ))


def create_audio_toolset() -> Toolset:
    """Audio generation and management tools."""

    async def generate_audio(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "generate_audio",
            "prompt": params.get("prompt", ""),
            "audio_type": params.get("audio_type", "sfx"),
            "duration": params.get("duration", 2.0),
            "status": "generated",
        }

    async def synthesize_voice(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "synthesize_voice",
            "text": params.get("text", ""),
            "voice_id": params.get("voice_id", "default"),
            "emotion": params.get("emotion", "neutral"),
            "status": "synthesized",
        }

    return Toolset("audio", "Audio generation and voice synthesis tools").add(Tool(
        name="generate_audio",
        description="Generate audio using AI",
        category="audio",
        parameters=[
            ToolParameter(name="prompt", type="string", description="Audio description"),
            ToolParameter(name="audio_type", type="string", description="Audio type (sfx, music, ambient)", required=False),
            ToolParameter(name="duration", type="number", description="Duration in seconds", required=False),
        ],
        handler=generate_audio,
    )).add(Tool(
        name="synthesize_voice",
        description="Synthesize voice from text",
        category="audio",
        parameters=[
            ToolParameter(name="text", type="string", description="Text to speak"),
            ToolParameter(name="voice_id", type="string", description="Voice ID", required=False),
            ToolParameter(name="emotion", type="string", description="Voice emotion", required=False),
        ],
        handler=synthesize_voice,
    ))


def create_video_toolset() -> Toolset:
    """Video rendering and storyboard tools."""

    async def render_video(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "render_video",
            "scene_id": params.get("scene_id", ""),
            "duration": params.get("duration", 5.0),
            "resolution": params.get("resolution", [1920, 1080]),
            "status": "rendered",
        }

    async def create_storyboard(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "create_storyboard",
            "narrative": params.get("narrative", ""),
            "shot_count": params.get("shot_count", 6),
            "style": params.get("style", "cinematic"),
            "status": "created",
        }

    return Toolset("video", "Video rendering and storyboard tools").add(Tool(
        name="render_video",
        description="Render a video from a scene",
        category="video",
        parameters=[
            ToolParameter(name="scene_id", type="string", description="Scene ID"),
            ToolParameter(name="duration", type="number", description="Duration in seconds", required=False),
            ToolParameter(name="resolution", type="array", description="Resolution [w, h]", required=False),
        ],
        handler=render_video,
    )).add(Tool(
        name="create_storyboard",
        description="Create a storyboard from narrative",
        category="video",
        parameters=[
            ToolParameter(name="narrative", type="string", description="Narrative description"),
            ToolParameter(name="shot_count", type="number", description="Number of shots", required=False),
            ToolParameter(name="style", type="string", description="Visual style", required=False),
        ],
        handler=create_storyboard,
    ))


_ROLE_TOOLSETS: Dict[str, List[str]] = {
    "director": ["engine", "orchestration", "narrative", "gameplay", "testing"],
    "lead": ["engine", "code", "gameplay", "testing", "orchestration"],
    "specialist": ["engine", "code"],
    "worker": ["engine"],
}


def get_toolsets_for_role(role: str) -> List[Toolset]:
    """Get the default toolsets for a given agent role."""
    toolset_names = _ROLE_TOOLSETS.get(role, ["engine"])
    result = []
    for name in toolset_names:
        ts = ToolsetRegistry.get(name)
        if ts:
            result.append(ts)
    return result


def get_tools_for_role(role: str) -> List[Tool]:
    """Get all tools for a given agent role."""
    tools = []
    for toolset in get_toolsets_for_role(role):
        tools.extend(toolset.tools())
    return tools


def create_engine_tools() -> List[Tool]:
    """Create built-in engine tools for backward compatibility."""
    return create_engine_toolset().tools()


def _register_all_toolsets() -> None:
    """Register all built-in toolsets."""
    for factory in [
        create_engine_toolset,
        create_asset_toolset,
        create_npc_toolset,
        create_narrative_toolset,
        create_gameplay_toolset,
        create_code_toolset,
        create_workflow_toolset,
        create_testing_toolset,
        create_orchestration_toolset,
        create_audio_toolset,
        create_video_toolset,
    ]:
        toolset = factory()
        ToolsetRegistry.register(toolset)


_register_all_toolsets()
