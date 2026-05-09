"""
SparkLabs Agent - Context Assembler

Builds rich, structured context payloads for LLM calls by
aggregating game state, agent history, tool availability, and
project metadata into coherent context windows. Enables agents
to make informed decisions with full situational awareness.

Architecture:
  ContextAssembler
    |-- GameStateSnapshot (serialize current game world state)
    |-- AgentHistoryCollector (gather recent agent interactions)
    |-- ToolCapabilityIndex (list available tools and their specs)
    |-- ProjectMetadataLayer (game name, genre, tech stack)
    |-- ContextCompressor (trim context to fit token budgets)

Context Sources (assembled into unified context):
  - GAME_STATE: current entities, scenes, variables
  - AGENT_HISTORY: recent agent actions and outcomes
  - TOOL_CATALOG: what tools can this agent invoke
  - PROJECT_META: project name, genre, platform, resolution
  - ENGINE_STATUS: FPS, memory, active systems
  - USER_PREFERENCES: user-configured defaults and style guides
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ContextSource(Enum):
    GAME_STATE = "game_state"
    AGENT_HISTORY = "agent_history"
    TOOL_CATALOG = "tool_catalog"
    PROJECT_META = "project_meta"
    ENGINE_STATUS = "engine_status"
    USER_PREFERENCES = "user_preferences"
    ASSET_REGISTRY = "asset_registry"
    SCENE_GRAPH = "scene_graph"


class ContextFormat(Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    YAML_LIKE = "yaml_like"
    PROSE = "prose"


@dataclass
class ToolSpec:
    tool_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    category: str = ""
    parameters_schema: Dict[str, Any] = field(default_factory=dict)
    returns: str = ""
    example: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": self.parameters_schema,
            "returns": self.returns,
            "example": self.example,
        }


@dataclass
class StateSnapshot:
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    active_scene: str = ""
    entity_count: int = 0
    system_statuses: Dict[str, bool] = field(default_factory=dict)
    recent_logs: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_scene": self.active_scene,
            "entity_count": self.entity_count,
            "systems": self.system_statuses,
            "recent_logs": self.recent_logs[-5:],
        }


@dataclass
class AgentActionRecord:
    record_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_name: str = ""
    action: str = ""
    outcome: str = ""
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "action": self.action,
            "outcome": self.outcome,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ProjectMeta:
    project_id: str = ""
    name: str = "Untitled Game"
    genre: str = "platformer"
    platform: str = "web"
    resolution: str = "1920x1080"
    language: str = "typescript"
    art_style: str = "pixel_art"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "genre": self.genre,
            "platform": self.platform,
            "resolution": self.resolution,
            "language": self.language,
            "art_style": self.art_style,
        }


@dataclass
class AssembledContext:
    context_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    format: ContextFormat = ContextFormat.MARKDOWN
    sections: Dict[str, str] = field(default_factory=dict)
    estimated_tokens: int = 0
    created_at: float = field(default_factory=time.time)

    def get_full_text(self) -> str:
        parts = []
        order = [
            ContextSource.PROJECT_META.value,
            ContextSource.ENGINE_STATUS.value,
            ContextSource.GAME_STATE.value,
            ContextSource.TOOL_CATALOG.value,
            ContextSource.AGENT_HISTORY.value,
            ContextSource.USER_PREFERENCES.value,
        ]
        for section in order:
            if section in self.sections:
                parts.append(self.sections[section])
        return "\n\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "format": self.format.value,
            "sections": list(self.sections.keys()),
            "estimated_tokens": self.estimated_tokens,
            "full_text_preview": self.get_full_text()[:500],
        }


class ContextAssembler:
    """Rich context assembly for LLM calls in game development agents."""

    _instance: Optional["ContextAssembler"] = None
    _lock = threading.Lock()

    MAX_HISTORY_RECORDS = 200
    MAX_TOOLS = 500
    DEFAULT_TOKEN_BUDGET = 4000

    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}
        self._history: deque = deque(maxlen=self.MAX_HISTORY_RECORDS)
        self._project_meta = ProjectMeta()
        self._state_snapshots: Dict[str, StateSnapshot] = {}
        self._user_preferences: Dict[str, str] = {}
        self._token_budget = self.DEFAULT_TOKEN_BUDGET

    @classmethod
    def get_instance(cls) -> "ContextAssembler":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def register_tool(
        self,
        name: str,
        description: str = "",
        category: str = "",
        parameters_schema: Optional[Dict[str, Any]] = None,
        returns: str = "",
        example: str = "",
    ) -> ToolSpec:
        tool = ToolSpec(
            name=name,
            description=description,
            category=category,
            parameters_schema=parameters_schema or {},
            returns=returns,
            example=example,
        )
        self._tools[tool.tool_id] = tool
        return tool

    def set_project_meta(
        self,
        name: str = "",
        genre: str = "",
        platform: str = "",
        resolution: str = "",
        language: str = "",
        art_style: str = "",
        description: str = "",
    ) -> None:
        if name:
            self._project_meta.name = name
        if genre:
            self._project_meta.genre = genre
        if platform:
            self._project_meta.platform = platform
        if resolution:
            self._project_meta.resolution = resolution
        if language:
            self._project_meta.language = language
        if art_style:
            self._project_meta.art_style = art_style
        if description:
            self._project_meta.description = description

    def set_user_preference(self, key: str, value: str) -> None:
        self._user_preferences[key] = value

    def record_action(
        self,
        agent_name: str,
        action: str,
        outcome: str,
        duration_ms: float = 0.0,
    ) -> AgentActionRecord:
        record = AgentActionRecord(
            agent_name=agent_name,
            action=action,
            outcome=outcome,
            duration_ms=duration_ms,
        )
        self._history.append(record)
        return record

    def take_state_snapshot(
        self,
        active_scene: str = "",
        entity_count: int = 0,
        system_statuses: Optional[Dict[str, bool]] = None,
    ) -> StateSnapshot:
        snapshot = StateSnapshot(
            active_scene=active_scene,
            entity_count=entity_count,
            system_statuses=system_statuses or {},
        )
        self._state_snapshots[snapshot.snapshot_id] = snapshot
        return snapshot

    def assemble(
        self,
        format: ContextFormat = ContextFormat.MARKDOWN,
        sources: Optional[List[ContextSource]] = None,
        include_recent_history: int = 10,
    ) -> AssembledContext:
        sources = sources or list(ContextSource)
        ctx = AssembledContext(format=format)

        if ContextSource.PROJECT_META in sources:
            meta = self._project_meta
            ctx.sections[ContextSource.PROJECT_META.value] = (
                "## Project Information\n"
                f"- Name: {meta.name}\n"
                f"- Genre: {meta.genre}\n"
                f"- Platform: {meta.platform}\n"
                f"- Resolution: {meta.resolution}\n"
                f"- Language: {meta.language}\n"
                f"- Art Style: {meta.art_style}\n"
                f"- Description: {meta.description or 'N/A'}"
            )

        if ContextSource.ENGINE_STATUS in sources and self._state_snapshots:
            latest = max(
                self._state_snapshots.values(),
                key=lambda s: s.timestamp,
            )
            ctx.sections[ContextSource.ENGINE_STATUS.value] = (
                "## Engine Status\n"
                f"- Active Scene: {latest.active_scene or 'none'}\n"
                f"- Entities: {latest.entity_count}\n"
                f"- Active Systems: {', '.join(k for k, v in latest.system_statuses.items() if v)}"
            )

        if ContextSource.GAME_STATE in sources:
            ctx.sections[ContextSource.GAME_STATE.value] = (
                "## Game State\n"
                "The game world is currently active and ready for modifications. "
                "Entities, components, and scene graph are accessible through the ECS API."
            )

        if ContextSource.TOOL_CATALOG in sources:
            lines = ["## Available Tools"]
            for cat in sorted(set(t.category for t in self._tools.values())):
                cat_tools = [t for t in self._tools.values() if t.category == cat]
                if cat_tools:
                    lines.append(f"\n### {cat.replace('_', ' ').title()}")
                    for tool in cat_tools[:5]:
                        lines.append(
                            f"- **{tool.name}**: {tool.description} "
                            f"({', '.join(tool.parameters_schema.keys()) if tool.parameters_schema else 'no params'})"
                        )
            ctx.sections[ContextSource.TOOL_CATALOG.value] = "\n".join(lines)

        if ContextSource.AGENT_HISTORY in sources:
            recent = list(self._history)[-include_recent_history:]
            lines = ["## Recent Agent Actions"]
            for i, rec in enumerate(recent, 1):
                lines.append(
                    f"{i}. [{rec.agent_name}] {rec.action} → {rec.outcome} "
                    f"({rec.duration_ms:.0f}ms)"
                )
            ctx.sections[ContextSource.AGENT_HISTORY.value] = "\n".join(lines)

        if ContextSource.USER_PREFERENCES in sources and self._user_preferences:
            lines = ["## User Preferences"]
            for k, v in self._user_preferences.items():
                lines.append(f"- {k}: {v}")
            ctx.sections[ContextSource.USER_PREFERENCES.value] = "\n".join(lines)

        full_text = ctx.get_full_text()
        ctx.estimated_tokens = len(full_text.split())
        return ctx

    def assemble_for_tool(
        self,
        tool_name: str,
        include_tool_spec: bool = True,
    ) -> AssembledContext:
        ctx = self.assemble(
            sources=[
                ContextSource.PROJECT_META,
                ContextSource.ENGINE_STATUS,
                ContextSource.AGENT_HISTORY,
            ],
            include_recent_history=5,
        )

        if include_tool_spec:
            matching = [
                t for t in self._tools.values() if t.name == tool_name
            ]
            if matching:
                tool = matching[0]
                ctx.sections[ContextSource.TOOL_CATALOG.value] = (
                    "## Tool Specification\n"
                    f"- Name: {tool.name}\n"
                    f"- Description: {tool.description}\n"
                    f"- Parameters: {json.dumps(tool.parameters_schema, indent=2)}\n"
                    f"- Returns: {tool.returns}\n"
                    f"- Example: {tool.example}"
                )

        return ctx

    def assemble_minimal(self, purpose: str = "") -> AssembledContext:
        ctx = AssembledContext(format=ContextFormat.PROSE, sections={})
        if purpose:
            ctx.sections["purpose"] = f"## Task\n{purpose}"
        ctx.sections["project"] = (
            "## Project\n"
            f"Working on **{self._project_meta.name}**, "
            f"a {self._project_meta.genre} game for {self._project_meta.platform}."
        )
        return ctx

    def get_tool(self, tool_id: str) -> Optional[ToolSpec]:
        return self._tools.get(tool_id)

    def list_tools(self, category: Optional[str] = None) -> List[ToolSpec]:
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def list_categories(self) -> List[str]:
        return sorted(set(t.category for t in self._tools.values()))

    def get_recent_history(self, limit: int = 20) -> List[AgentActionRecord]:
        return list(self._history)[-limit:]

    def clear_history(self) -> None:
        self._history.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "registered_tools": len(self._tools),
            "tool_categories": len(self.list_categories()),
            "history_records": len(self._history),
            "state_snapshots": len(self._state_snapshots),
            "user_preferences": len(self._user_preferences),
            "token_budget": self._token_budget,
            "project_name": self._project_meta.name,
            "recent_success_rate": round(
                sum(
                    1 for r in list(self._history)[-20:] if "success" in r.outcome.lower()
                ) / max(1, min(20, len(self._history))),
                3,
            ),
        }


def get_context_assembler() -> ContextAssembler:
    return ContextAssembler.get_instance()