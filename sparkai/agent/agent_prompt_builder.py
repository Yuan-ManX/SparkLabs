"""
SparkAI Agent - Prompt Builder

Dynamic system prompt construction system. Assembles comprehensive
agent system prompts from multiple sources including environment
configuration, skill registries, context documents, and game-world
parameters. Supports layered prompt construction with configurable
sections, caching of static portions, and injection of dynamic
context at runtime.

Architecture:
  PromptBuilder
    |-- IdentityLayer (agent personality, role, constraints)
    |-- EnvironmentLayer (platform, tool env, working directory)
    |-- SkillLayer (available skills, tool schemas, capabilities)
    |-- ContextLayer (AGENTS.md, SOUL.md, project files)
    |-- GameWorldLayer (game state, entities, world rules)
    |-- InstructionLayer (current task, goals, constraints)

Prompt Construction Flow:
  1. Build identity and role description
  2. Layer environment details and constraints
  3. Index available skills and capabilities
  4. Load context documents (project conventions)
  5. Inject game world state and rules
  6. Append current task instructions
  7. Apply caching markers for repeated sections
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_ESTIMATED_CHARS_PER_TOKEN = 3.5


class PromptSection(Enum):
    IDENTITY = "identity"
    ENVIRONMENT = "environment"
    CAPABILITIES = "capabilities"
    SKILLS = "skills"
    CONTEXT = "context"
    GAME_WORLD = "game_world"
    INSTRUCTIONS = "instructions"
    MEMORY = "memory"
    RULES = "rules"
    CUSTOM = "custom"


@dataclass
class SectionConfig:
    enabled: bool = True
    order: int = 0
    header: str = ""
    max_tokens: int = 2000
    collapse_if_empty: bool = True

    def __post_init__(self):
        if not self.header:
            self.header = ""


@dataclass
class PromptArtifact:
    full_text: str = ""
    sections: Dict[str, str] = field(default_factory=dict)
    estimated_tokens: int = 0
    section_token_counts: Dict[str, int] = field(default_factory=dict)
    skill_count: int = 0
    context_files_loaded: List[str] = field(default_factory=list)
    built_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "estimated_tokens": self.estimated_tokens,
            "section_token_counts": self.section_token_counts,
            "skill_count": self.skill_count,
            "context_files_loaded": self.context_files_loaded,
            "built_at": self.built_at,
        }


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / _ESTIMATED_CHARS_PER_TOKEN))


def _load_file_if_exists(path: str, max_chars: int = 10000) -> Optional[str]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars)
        return content
    except (OSError, UnicodeDecodeError):
        return None


class PromptBuilder:
    """
    Dynamic system prompt constructor.

    Builds layered agent prompts by assembling content from
    multiple configurable sources. Each section can be toggled,
    reordered, or replaced with custom content. The builder
    supports token budgeting to prevent prompts from exceeding
    model context limits.

    Static sections (identity, rules) can be cached to avoid
    redundant computation. Dynamic sections (game world, current
    task) are rebuilt on each invocation.

    Usage:
        builder = PromptBuilder()
        artifact = builder.build(
            game_context={"world": "fantasy", "entities": [...]},
            current_task="Generate a medieval castle"
        )
    """

    SECTION_CONFIGS: Dict[PromptSection, SectionConfig] = {
        PromptSection.IDENTITY: SectionConfig(order=0, max_tokens=800),
        PromptSection.ENVIRONMENT: SectionConfig(order=1, max_tokens=600),
        PromptSection.RULES: SectionConfig(order=2, max_tokens=500),
        PromptSection.CAPABILITIES: SectionConfig(order=3, max_tokens=800),
        PromptSection.SKILLS: SectionConfig(order=4, max_tokens=3000),
        PromptSection.CONTEXT: SectionConfig(order=5, max_tokens=4000),
        PromptSection.GAME_WORLD: SectionConfig(order=6, max_tokens=3000),
        PromptSection.MEMORY: SectionConfig(order=7, max_tokens=2000),
        PromptSection.INSTRUCTIONS: SectionConfig(order=8, max_tokens=500),
        PromptSection.CUSTOM: SectionConfig(order=9, max_tokens=1000),
    }

    def __init__(
        self,
        working_dir: Optional[str] = None,
        max_total_tokens: int = 12000,
        cache_static: bool = True,
    ):
        self._working_dir = working_dir or os.getcwd()
        self._max_total_tokens = max_total_tokens
        self._cache_static = cache_static
        self._section_overrides: Dict[PromptSection, str] = {}
        self._custom_sections: Dict[str, str] = {}
        self._extra_context_files: List[str] = []
        self._static_cache: Optional[PromptArtifact] = None
        self._project_context: Optional[Dict[str, Any]] = None

    def override_section(self, section: PromptSection, content: str) -> None:
        self._section_overrides[section] = content

    def add_custom_section(self, name: str, content: str) -> None:
        self._custom_sections[name] = content

    def add_context_file(self, file_path: str) -> None:
        self._extra_context_files.append(file_path)

    def set_project_context(self, ctx: Dict[str, Any]) -> None:
        self._project_context = ctx

    def invalidate_cache(self) -> None:
        self._static_cache = None

    def build(
        self,
        game_context: Optional[Dict[str, Any]] = None,
        current_task: str = "",
        skills_list: Optional[List[Dict[str, Any]]] = None,
        memory_entries: Optional[List[Dict[str, Any]]] = None,
        extra_instructions: str = "",
    ) -> PromptArtifact:
        if self._cache_static and self._static_cache is not None:
            base = self._static_cache
        else:
            base = self._build_static_sections()
            if self._cache_static:
                self._static_cache = base

        dynamic = self._build_dynamic_sections(
            game_context, current_task, skills_list, memory_entries, extra_instructions
        )

        all_sections = {**base.sections, **dynamic.sections}

        ordered_sections = sorted(
            all_sections.items(),
            key=lambda kv: self._get_section_order(kv[0]),
        )

        full_text = "\n\n".join(s for _, s in ordered_sections if s)
        section_tokens = {k: _estimate_tokens(v) for k, v in all_sections.items()}

        return PromptArtifact(
            full_text=full_text,
            sections=all_sections,
            estimated_tokens=_estimate_tokens(full_text),
            section_token_counts=section_tokens,
            skill_count=len(skills_list) if skills_list else 0,
            context_files_loaded=list(base.sections.keys()),
            built_at=time.time(),
        )

    def _get_section_order(self, name: str) -> int:
        for section, config in self.SECTION_CONFIGS.items():
            if section.value == name:
                return config.order
        return 99

    def _build_section(
        self,
        section: PromptSection,
        content: str,
        header: Optional[str] = None,
    ) -> str:
        config = self.SECTION_CONFIGS.get(section, SectionConfig())
        if not config.enabled:
            return ""
        if not content.strip() and config.collapse_if_empty:
            return ""

        prefix = header or config.header
        if not prefix:
            return content

        capped = content
        if _estimate_tokens(content) > config.max_tokens:
            cap_chars = int(config.max_tokens * _ESTIMATED_CHARS_PER_TOKEN)
            capped = content[:cap_chars] + "\n[Content truncated for token budget]"

        return f"{prefix}\n{capped}"

    def _build_static_sections(self) -> PromptArtifact:
        sections: Dict[str, str] = {}

        identity = self._section_overrides.get(PromptSection.IDENTITY) or self._build_identity()
        sections[PromptSection.IDENTITY.value] = self._build_section(PromptSection.IDENTITY, identity)

        env = self._section_overrides.get(PromptSection.ENVIRONMENT) or self._build_environment()
        sections[PromptSection.ENVIRONMENT.value] = self._build_section(PromptSection.ENVIRONMENT, env)

        rules = self._section_overrides.get(PromptSection.RULES) or self._build_rules()
        sections[PromptSection.RULES.value] = self._build_section(PromptSection.RULES, rules)

        capabilities = self._section_overrides.get(PromptSection.CAPABILITIES) or self._build_capabilities()
        sections[PromptSection.CAPABILITIES.value] = self._build_section(PromptSection.CAPABILITIES, capabilities)

        context = self._section_overrides.get(PromptSection.CONTEXT) or self._build_context()
        sections[PromptSection.CONTEXT.value] = self._build_section(PromptSection.CONTEXT, context)

        full_text = "\n\n".join(s for s in sections.values() if s)
        return PromptArtifact(
            full_text=full_text,
            sections=sections,
            estimated_tokens=_estimate_tokens(full_text),
            context_files_loaded=list(self._extra_context_files),
        )

    def _build_dynamic_sections(
        self,
        game_context: Optional[Dict[str, Any]],
        current_task: str,
        skills_list: Optional[List[Dict[str, Any]]],
        memory_entries: Optional[List[Dict[str, Any]]],
        extra_instructions: str,
    ) -> PromptArtifact:
        sections: Dict[str, str] = {}

        if skills_list:
            skills = self._build_skills_index(skills_list)
            sections[PromptSection.SKILLS.value] = self._build_section(
                PromptSection.SKILLS, skills,
                "# Available Game Skills\nYou have access to the following game development skills:"
            )

        if game_context:
            game = self._build_game_world_section(game_context)
            sections[PromptSection.GAME_WORLD.value] = self._build_section(
                PromptSection.GAME_WORLD, game,
                "# Current Game World\nBelow is the state of the game world:"
            )

        if memory_entries:
            memory = self._build_memory_section(memory_entries)
            sections[PromptSection.MEMORY.value] = self._build_section(
                PromptSection.MEMORY, memory,
                "# Context Memory\nRelevant past interactions:"
            )

        task_text = current_task
        if extra_instructions:
            task_text = f"{current_task}\n\nAdditional Instructions:\n{extra_instructions}"
        if task_text:
            sections[PromptSection.INSTRUCTIONS.value] = self._build_section(
                PromptSection.INSTRUCTIONS, task_text,
                "# Current Task"
            )

        custom_content = self._section_overrides.get(PromptSection.CUSTOM, "")
        for name, content in self._custom_sections.items():
            custom_content += f"\n\n## {name}\n{content}"
        if custom_content:
            sections[PromptSection.CUSTOM.value] = self._build_section(PromptSection.CUSTOM, custom_content)

        full_text = "\n\n".join(s for s in sections.values() if s)
        return PromptArtifact(
            full_text=full_text,
            sections=sections,
            estimated_tokens=_estimate_tokens(full_text),
        )

    def _build_identity(self) -> str:
        project_name = "SparkLabs"
        if self._project_context:
            project_name = self._project_context.get("name", project_name)

        return (
            f"You are SparkLabs AI, an autonomous AI-native game engine agent.\n"
            f"Your purpose is to design, build, and iterate on game worlds, characters,\n"
            f"mechanics, and narratives. You operate within the {project_name} ecosystem,\n"
            f"which fuses AI agents with game engine editors for real-time creation.\n\n"
            f"Core Principles:\n"
            f"- Think before acting: analyze the game state before making changes\n"
            f"- Verify your work: check that generated entities are consistent\n"
            f"- Iterate proactively: if a generation is flawed, refine it immediately\n"
            f"- Preserve player agency: never make irreversible changes without confirmation\n"
            f"- Be creative: propose novel game mechanics and world-building ideas\n"
            f"- Stay within scope: focus on the current task and available tools"
        )

    def _build_environment(self) -> str:
        working_dir = os.path.abspath(self._working_dir)
        return (
            f"Working Directory: {working_dir}\n"
            f"Engine: SparkLabs Game Engine v2.0\n"
            f"Mode: Agent-Driven Game Development\n"
            f"Context Window: {self._max_total_tokens} tokens estimated\n"
        )

    def _build_rules(self) -> str:
        return (
            "Communication Rules:\n"
            "- Respond in the user's language unless instructed otherwise\n"
            "- Never expose internal API keys or credentials\n"
            "- Use structured JSON when generating game data\n"
            "- Signal completion with a summary of changes made\n\n"
            "Safety Rules:\n"
            "- Never delete project files without explicit confirmation\n"
            "- Never modify engine core files\n"
            "- Always validate generated code before execution"
        )

    def _build_capabilities(self) -> str:
        return (
            "Core Capabilities:\n"
            "- World Generation: procedural terrain, biomes, ecosystems\n"
            "- Entity Management: create, modify, and delete game entities\n"
            "- AI Agent Control: spawn and direct autonomous NPC agents\n"
            "- Narrative Design: generate story arcs, dialogue trees, quests\n"
            "- Asset Pipeline: generate textures, models, sounds via AI\n"
            "- Game Logic: implement mechanics, rules, and systems\n"
            "- Playtesting: simulate gameplay and report balance issues\n"
            "- Code Generation: produce game scripts and engine extensions\n\n"
            "Execution Model:\n"
            "You operate in a multi-phase loop:\n"
            "1. Observe the current game state\n"
            "2. Think about what needs to happen\n"
            "3. Act by invoking tools and generating content\n"
            "4. Verify that the action produced the intended result"
        )

    def _build_context(self) -> str:
        context_files = [
            os.path.join(self._working_dir, "AGENTS.md"),
            os.path.join(self._working_dir, "SOUL.md"),
            os.path.join(self._working_dir, "CLAUDE.md"),
        ]
        for extra in self._extra_context_files:
            context_files.append(extra)

        loaded = []
        for file_path in context_files:
            content = _load_file_if_exists(file_path)
            if content:
                loaded.append(f"[{os.path.basename(file_path)}]\n{content}")

        if not loaded:
            return "No project context files found."

        return "\n\n---\n\n".join(loaded)

    def _build_skills_index(self, skills_list: List[Dict[str, Any]]) -> str:
        if not skills_list:
            return "No skills currently available."

        by_category: Dict[str, List[Dict[str, Any]]] = {}
        for skill in skills_list:
            cat = skill.get("category", "general")
            by_category.setdefault(cat, []).append(skill)

        lines = []
        for category, skills in sorted(by_category.items()):
            lines.append(f"\n## {category.title()}")
            for skill in skills[:10]:
                name = skill.get("name", "Unknown")
                desc = skill.get("description", "")[:120]
                lines.append(f"- {name}: {desc}")

        return "\n".join(lines)

    def _build_game_world_section(self, game_context: Dict[str, Any]) -> str:
        lines = []

        world_name = game_context.get("world_name", game_context.get("name", "Unnamed World"))
        lines.append(f"World: {world_name}")

        if "description" in game_context:
            lines.append(f"Description: {game_context['description'][:300]}")

        entities = game_context.get("entities", [])
        if entities:
            lines.append(f"\nEntities ({len(entities)}):")
            for entity in entities[:8]:
                if isinstance(entity, dict):
                    e_name = entity.get("name", entity.get("id", "?"))
                    e_type = entity.get("type", "entity")
                    lines.append(f"  - [{e_type}] {e_name}")
                else:
                    lines.append(f"  - {str(entity)[:80]}")

        rules = game_context.get("rules", game_context.get("world_rules", ""))
        if rules:
            lines.append(f"\nWorld Rules: {str(rules)[:500]}")

        return "\n".join(lines)

    def _build_memory_section(self, memory_entries: List[Dict[str, Any]]) -> str:
        if not memory_entries:
            return ""

        lines = []
        for entry in memory_entries[-5:]:
            content = entry.get("content", str(entry))[:200]
            entry_type = entry.get("type", "memory")
            lines.append(f"[{entry_type}] {content}")

        return "\n".join(lines)


_global_prompt_builder: Optional[PromptBuilder] = None


def get_prompt_builder() -> PromptBuilder:
    global _global_prompt_builder
    if _global_prompt_builder is None:
        _global_prompt_builder = PromptBuilder()
    return _global_prompt_builder
