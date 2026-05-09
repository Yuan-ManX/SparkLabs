"""
SparkLabs Agent - Prompt Template Library

Structured prompt template management for AI-native game engine
agents. Provides versioned, composable prompt templates with
variable interpolation, conditional blocks, and chain-of-thought
patterns tailored for game development tasks.

Architecture:
  PromptTemplateLib
    |-- TemplateEntry (single versioned prompt template)
    |-- TemplateCategory (organization by domain)
    |-- VariableResolver (interpolate template variables)
    |-- ComposeEngine (chain templates into multi-turn prompts)
    |-- TemplateValidator (structural and semantic validation)

Template Domains:
  - game_design: concept generation, mechanics design
  - code_gen: script generation, system implementation
  - level_design: layout, terrain, obstacle placement
  - dialogue: NPC dialogue, quest text, narration
  - art_direction: visual style, palette, asset descriptions
  - debugging: error analysis, fix suggestions
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TemplateDomain(Enum):
    GAME_DESIGN = "game_design"
    CODE_GEN = "code_gen"
    LEVEL_DESIGN = "level_design"
    DIALOGUE = "dialogue"
    ART_DIRECTION = "art_direction"
    DEBUGGING = "debugging"
    GENERAL = "general"


class TemplateRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class VariableDef:
    name: str
    default: str = ""
    description: str = ""
    required: bool = False


@dataclass
class TemplateEntry:
    template_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    domain: TemplateDomain = TemplateDomain.GENERAL
    role: TemplateRole = TemplateRole.USER
    content: str = ""
    variables: List[VariableDef] = field(default_factory=list)
    version: int = 1
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0

    def resolve(self, variable_values: Dict[str, str]) -> str:
        result = self.content
        for var_def in self.variables:
            value = variable_values.get(var_def.name, var_def.default)
            if var_def.required and not value:
                raise ValueError(f"Required variable '{var_def.name}' not provided")
            placeholder = "{{" + var_def.name + "}}"
            result = result.replace(placeholder, value or "")
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "domain": self.domain.value,
            "role": self.role.value,
            "version": self.version,
            "tags": self.tags,
            "usage_count": self.usage_count,
            "variable_count": len(self.variables),
        }


@dataclass
class ComposedPrompt:
    compose_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    messages: List[Dict[str, str]] = field(default_factory=list)

    def add_system(self, content: str) -> None:
        self.messages.append({"role": "system", "content": content})

    def add_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compose_id": self.compose_id,
            "name": self.name,
            "messages": self.messages,
            "message_count": len(self.messages),
        }


class PromptTemplateLib:
    """Structured prompt template library for AI game engine agents."""

    _instance: Optional["PromptTemplateLib"] = None
    _lock = threading.Lock()

    MAX_TEMPLATES = 1000

    def __init__(self):
        self._templates: Dict[str, TemplateEntry] = {}
        self._composed: Dict[str, ComposedPrompt] = {}
        self._register_default_templates()

    @classmethod
    def get_instance(cls) -> "PromptTemplateLib":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _register_default_templates(self) -> None:
        defaults = [
            TemplateEntry(
                name="game_concept_generator",
                description="Generate a complete game concept from a theme",
                domain=TemplateDomain.GAME_DESIGN,
                role=TemplateRole.USER,
                content=(
                    "Design a complete game concept based on the following theme: {{theme}}\n\n"
                    "Include:\n"
                    "1. Genre and target platform: {{platform}}\n"
                    "2. Core gameplay loop\n"
                    "3. Unique selling points\n"
                    "4. Target audience: {{audience}}\n"
                    "5. Art style direction\n\n"
                    "Additional constraints: {{constraints}}"
                ),
                variables=[
                    VariableDef("theme", "space exploration", "Central theme of the game"),
                    VariableDef("platform", "PC", "Target platform"),
                    VariableDef("audience", "casual gamers", "Target player demographic"),
                    VariableDef("constraints", "2D pixel art", "Technical or design constraints"),
                ],
            ),
            TemplateEntry(
                name="code_system_generator",
                description="Generate game system implementation code",
                domain=TemplateDomain.CODE_GEN,
                role=TemplateRole.USER,
                content=(
                    "Implement a {{system_type}} system for a {{genre}} game.\n"
                    "Language: {{language}}\n"
                    "Requirements:\n{{requirements}}\n\n"
                    "The system should handle:\n{{features}}"
                ),
                variables=[
                    VariableDef("system_type", "combat", "Type of game system"),
                    VariableDef("genre", "RPG", "Game genre"),
                    VariableDef("language", "typescript", "Programming language"),
                    VariableDef("requirements", "Performance critical", "Key requirements"),
                    VariableDef("features", "damage calculation", "Feature list"),
                ],
            ),
            TemplateEntry(
                name="level_layout_designer",
                description="Design a game level layout",
                domain=TemplateDomain.LEVEL_DESIGN,
                role=TemplateRole.USER,
                content=(
                    "Design a level layout for a {{genre}} game.\n"
                    "Level theme: {{theme}}\n"
                    "Difficulty: {{difficulty}}\n"
                    "Size: {{width}}x{{height}} tiles\n\n"
                    "Describe the spatial arrangement of:\n"
                    "1. Starting area\n"
                    "2. Main challenge zones\n"
                    "3. Enemy placement pattern\n"
                    "4. Collectible distribution\n"
                    "5. Boss arena or exit zone"
                ),
                variables=[
                    VariableDef("genre", "platformer", "Game genre"),
                    VariableDef("theme", "forest", "Level visual theme"),
                    VariableDef("difficulty", "medium", "Difficulty level"),
                    VariableDef("width", "64", "Level width in tiles"),
                    VariableDef("height", "32", "Level height in tiles"),
                ],
            ),
            TemplateEntry(
                name="npc_dialogue_writer",
                description="Generate NPC dialogue trees",
                domain=TemplateDomain.DIALOGUE,
                role=TemplateRole.USER,
                content=(
                    "Write dialogue for an NPC named {{npc_name}}.\n"
                    "Role: {{npc_role}}\n"
                    "Personality: {{personality}}\n"
                    "Quest context: {{quest_context}}\n\n"
                    "Generate {{branch_count}} dialogue branches with responses for:\n"
                    "1. Friendly approach\n"
                    "2. Hostile approach\n"
                    "3. Neutral inquiry\n"
                    "4. Quest completion acknowledgment"
                ),
                variables=[
                    VariableDef("npc_name", "Elder Thorne", "NPC character name"),
                    VariableDef("npc_role", "quest giver", "NPC's role in the game"),
                    VariableDef("personality", "wise and cryptic", "NPC personality traits"),
                    VariableDef("quest_context", "find the lost artifact", "Quest background"),
                    VariableDef("branch_count", "3", "Number of dialogue branches"),
                ],
            ),
            TemplateEntry(
                name="debug_error_analyzer",
                description="Analyze game errors and suggest fixes",
                domain=TemplateDomain.DEBUGGING,
                role=TemplateRole.USER,
                content=(
                    "Analyze the following error from a {{engine}} game:\n\n"
                    "Error: {{error_message}}\n"
                    "Stack trace: {{stack_trace}}\n"
                    "Game context: {{game_context}}\n\n"
                    "Provide:\n"
                    "1. Root cause analysis\n"
                    "2. Step-by-step fix instructions\n"
                    "3. Prevention tip for future development"
                ),
                variables=[
                    VariableDef("engine", "SparkLabs", "Game engine name"),
                    VariableDef("error_message", "", "The error message", required=True),
                    VariableDef("stack_trace", "N/A", "Full stack trace"),
                    VariableDef("game_context", "player movement", "What the game was doing"),
                ],
            ),
        ]
        for tmpl in defaults:
            self._templates[tmpl.template_id] = tmpl

    def create_template(
        self,
        name: str,
        content: str,
        domain: TemplateDomain = TemplateDomain.GENERAL,
        role: TemplateRole = TemplateRole.USER,
        description: str = "",
        variables: Optional[List[VariableDef]] = None,
        tags: Optional[List[str]] = None,
    ) -> TemplateEntry:
        template = TemplateEntry(
            name=name,
            description=description,
            domain=domain,
            role=role,
            content=content,
            variables=variables or [],
            tags=tags or [],
        )
        self._templates[template.template_id] = template
        return template

    def get_template(self, template_id: str) -> Optional[TemplateEntry]:
        return self._templates.get(template_id)

    def find_by_name(self, name: str) -> Optional[TemplateEntry]:
        for tmpl in self._templates.values():
            if tmpl.name == name:
                return tmpl
        return None

    def resolve_template(
        self,
        template_id: str,
        variables: Dict[str, str],
    ) -> Optional[str]:
        template = self._templates.get(template_id)
        if not template:
            return None
        try:
            result = template.resolve(variables)
            template.usage_count += 1
            return result
        except ValueError:
            return None

    def compose_prompt(
        self,
        name: str,
        template_ids: List[str],
        variables_list: List[Dict[str, str]],
    ) -> Optional[ComposedPrompt]:
        composed = ComposedPrompt(name=name)
        for tmpl_id, vars_ in zip(template_ids, variables_list):
            resolved = self.resolve_template(tmpl_id, vars_)
            if resolved is None:
                return None
            template = self._templates.get(tmpl_id)
            if template:
                if template.role == TemplateRole.SYSTEM:
                    composed.add_system(resolved)
                elif template.role == TemplateRole.USER:
                    composed.add_user(resolved)
                elif template.role == TemplateRole.ASSISTANT:
                    composed.add_assistant(resolved)
        self._composed[composed.compose_id] = composed
        return composed

    def list_templates(
        self,
        domain: Optional[TemplateDomain] = None,
        tag: Optional[str] = None,
    ) -> List[TemplateEntry]:
        templates = list(self._templates.values())
        if domain:
            templates = [t for t in templates if t.domain == domain]
        if tag:
            templates = [t for t in templates if tag in t.tags]
        return templates

    def update_template(
        self,
        template_id: str,
        content: str,
    ) -> Optional[TemplateEntry]:
        template = self._templates.get(template_id)
        if template:
            template.content = content
            template.version += 1
            template.created_at = time.time()
        return template

    def delete_template(self, template_id: str) -> bool:
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def get_variables(self, template_id: str) -> List[VariableDef]:
        template = self._templates.get(template_id)
        if template:
            return template.variables
        return []

    def get_stats(self) -> Dict[str, Any]:
        domains: Dict[str, int] = {}
        for tmpl in self._templates.values():
            d = tmpl.domain.value
            domains[d] = domains.get(d, 0) + 1
        return {
            "total_templates": len(self._templates),
            "total_composed": len(self._composed),
            "total_usage": sum(t.usage_count for t in self._templates.values()),
            "domains": domains,
            "most_used": max(
                self._templates.values(),
                key=lambda t: t.usage_count,
            ).name if self._templates else None,
        }


def get_prompt_template_lib() -> PromptTemplateLib:
    return PromptTemplateLib.get_instance()