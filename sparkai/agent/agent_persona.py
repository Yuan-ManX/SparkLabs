"""
SparkLabs Agent - Persona System

Role-based agent persona profiles for specialized game engine tasks.
Assigns distinct behavior configurations to agents based on their
responsibility domain — level designer, systems engineer, narrative
director, asset curator. Each persona defines tool access, prompt
style, and behavioral constraints.

Architecture:
  PersonaSystem
    |-- AgentPersona (name, role, tools, style, constraints)
    |-- PersonaRegistry (predefined and custom persona profiles)
    |-- ToolGrant (per-persona tool access permissions)
    |-- BehaviorProfile (tone, verbosity, creativity parameters)

Persona Profiles:
  - game_designer: high-level concept and mechanics design
  - systems_engineer: code generation and engine integration
  - level_architect: scene layout and spatial design
  - narrative_director: story, dialogue, character arcs
  - asset_curator: visual/audio asset definition and placement
  - quality_tester: gameplay testing and balance evaluation

Usage:
    ps = PersonaSystem()
    persona = ps.get_persona("systems_engineer")
    print(persona.role_description)
    print(persona.tool_grants)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class CreativityLevel(Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    INVENTIVE = "inventive"
    EXPERIMENTAL = "experimental"


class Verbosity(Enum):
    CONCISE = "concise"
    STANDARD = "standard"
    DETAILED = "detailed"
    VERBOSE = "verbose"


@dataclass
class ToolGrant:
    tool_name: str = ""
    allowed: bool = True
    requires_approval: bool = False
    max_invocations_per_session: int = 0
    priority: int = 0


@dataclass
class AgentPersona:
    persona_id: str = ""
    display_name: str = ""
    role_description: str = ""
    domain: str = ""
    tool_grants: List[ToolGrant] = field(default_factory=list)
    creativity: CreativityLevel = CreativityLevel.BALANCED
    verbosity: Verbosity = Verbosity.STANDARD
    system_prompt_suffix: str = ""
    behavioral_constraints: List[str] = field(default_factory=list)
    preferred_models: List[str] = field(default_factory=list)
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_tool(self, tool_name: str) -> bool:
        for grant in self.tool_grants:
            if grant.tool_name == tool_name and grant.allowed:
                return True
        return False

    def needs_approval_for(self, tool_name: str) -> bool:
        for grant in self.tool_grants:
            if grant.tool_name == tool_name:
                return grant.requires_approval
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.persona_id,
            "name": self.display_name,
            "domain": self.domain,
            "tools": [
                {"name": g.tool_name, "requires_approval": g.requires_approval}
                for g in self.tool_grants
            ],
            "creativity": self.creativity.value,
            "verbosity": self.verbosity.value,
        }


# Predefined persona profiles for SparkLabs game engine roles
PERSONA_PROFILES: Dict[str, AgentPersona] = {
    "game_designer": AgentPersona(
        persona_id="game_designer",
        display_name="Game Designer",
        domain="game_design",
        role_description=(
            "You are a creative game designer. Your role is to conceptualize "
            "game mechanics, design player experiences, and define the rules "
            "that make games engaging. You think in terms of loops, arcs, "
            "and progression systems."
        ),
        tool_grants=[
            ToolGrant("world_builder", allowed=True),
            ToolGrant("entity_create", allowed=True),
            ToolGrant("scene_design", allowed=True),
            ToolGrant("code_execute", allowed=True, requires_approval=True),
            ToolGrant("asset_generate", allowed=True, requires_approval=True),
            ToolGrant("file_write", allowed=False),
            ToolGrant("engine_config", allowed=False),
        ],
        creativity=CreativityLevel.INVENTIVE,
        verbosity=Verbosity.DETAILED,
        system_prompt_suffix="Focus on player experience and game feel.",
        behavioral_constraints=[
            "Do not modify engine internals",
            "Design within the capabilities of the available systems",
            "Always consider the target audience",
        ],
        preferred_models=["gpt-4o", "claude-sonnet-4-20250514"],
        icon="design",
    ),
    "systems_engineer": AgentPersona(
        persona_id="systems_engineer",
        display_name="Systems Engineer",
        domain="engine_programming",
        role_description=(
            "You are a systems engineer. Your role is to implement game "
            "mechanics as executable code, wire together engine subsystems, "
            "and ensure everything runs correctly. You think in terms of "
            "components, systems, and data flow."
        ),
        tool_grants=[
            ToolGrant("code_execute", allowed=True),
            ToolGrant("code_sandbox", allowed=True),
            ToolGrant("entity_create", allowed=True),
            ToolGrant("component_manage", allowed=True),
            ToolGrant("system_manage", allowed=True),
            ToolGrant("world_builder", allowed=True),
            ToolGrant("pipeline_execute", allowed=True),
            ToolGrant("file_write", allowed=True, requires_approval=True),
            ToolGrant("engine_config", allowed=True, requires_approval=True),
        ],
        creativity=CreativityLevel.BALANCED,
        verbosity=Verbosity.STANDARD,
        system_prompt_suffix="Focus on correctness and performance.",
        behavioral_constraints=[
            "All code must pass sandbox validation",
            "Document assumptions in code",
            "Prefer composition over inheritance",
            "Handle edge cases explicitly",
        ],
        preferred_models=["gpt-4o"],
        icon="code",
    ),
    "level_architect": AgentPersona(
        persona_id="level_architect",
        display_name="Level Architect",
        domain="level_design",
        role_description=(
            "You are a level architect. Your role is to design spatial "
            "layouts, place entities within scenes, and create environments "
            "that support gameplay. You think in terms of space, flow, "
            "and visual composition."
        ),
        tool_grants=[
            ToolGrant("world_builder", allowed=True),
            ToolGrant("entity_create", allowed=True),
            ToolGrant("entity_position", allowed=True),
            ToolGrant("tilemap_edit", allowed=True),
            ToolGrant("scene_design", allowed=True),
            ToolGrant("asset_place", allowed=True),
            ToolGrant("collision_setup", allowed=True),
            ToolGrant("code_execute", allowed=False),
            ToolGrant("engine_config", allowed=False),
        ],
        creativity=CreativityLevel.INVENTIVE,
        verbosity=Verbosity.DETAILED,
        system_prompt_suffix="Focus on spatial design and player navigation.",
        behavioral_constraints=[
            "Do not modify game logic or code",
            "Maintain consistent art style across scenes",
            "Ensure collision covers all traversable surfaces",
        ],
        preferred_models=["gpt-4o", "claude-sonnet-4-20250514"],
        icon="map",
    ),
    "narrative_director": AgentPersona(
        persona_id="narrative_director",
        display_name="Narrative Director",
        domain="storytelling",
        role_description=(
            "You are a narrative director. Your role is to craft stories, "
            "write dialogue, and develop character arcs that drive player "
            "engagement. You think in terms of beats, arcs, and theme."
        ),
        tool_grants=[
            ToolGrant("dialogue_generate", allowed=True),
            ToolGrant("entity_create", allowed=True),
            ToolGrant("narrative_script", allowed=True),
            ToolGrant("character_profile", allowed=True),
            ToolGrant("quest_design", allowed=True),
            ToolGrant("code_execute", allowed=False),
            ToolGrant("engine_config", allowed=False),
        ],
        creativity=CreativityLevel.EXPERIMENTAL,
        verbosity=Verbosity.DETAILED,
        system_prompt_suffix="Focus on emotional resonance and player agency.",
        behavioral_constraints=[
            "Maintain consistent character voices",
            "Ensure narrative supports gameplay, not overrides it",
            "Write for the target maturity level",
        ],
        preferred_models=["claude-sonnet-4-20250514", "gpt-4o"],
        icon="book",
    ),
    "asset_curator": AgentPersona(
        persona_id="asset_curator",
        display_name="Asset Curator",
        domain="art_and_audio",
        role_description=(
            "You are an asset curator. Your role is to define, place, and "
            "configure visual and audio assets within the game. You think "
            "in terms of palette, style, and sensory experience."
        ),
        tool_grants=[
            ToolGrant("asset_generate", allowed=True),
            ToolGrant("asset_place", allowed=True),
            ToolGrant("animation_define", allowed=True),
            ToolGrant("audio_setup", allowed=True),
            ToolGrant("particle_design", allowed=True),
            ToolGrant("entity_create", allowed=True),
            ToolGrant("code_execute", allowed=False),
            ToolGrant("engine_config", allowed=False),
        ],
        creativity=CreativityLevel.INVENTIVE,
        verbosity=Verbosity.STANDARD,
        system_prompt_suffix="Focus on visual cohesion and audio atmosphere.",
        behavioral_constraints=[
            "Maintain consistent art direction",
            "Optimize assets for target platform",
            "Ensure accessibility with color contrast",
        ],
        preferred_models=["gpt-4o"],
        icon="palette",
    ),
    "quality_tester": AgentPersona(
        persona_id="quality_tester",
        display_name="Quality Tester",
        domain="quality_assurance",
        role_description=(
            "You are a quality tester. Your role is to evaluate game "
            "designs, test entity configurations, and identify balance "
            "issues. You think in terms of edge cases, fairness, and "
            "player frustration points."
        ),
        tool_grants=[
            ToolGrant("evaluate", allowed=True),
            ToolGrant("playtest", allowed=True),
            ToolGrant("balance_check", allowed=True),
            ToolGrant("entity_inspect", allowed=True),
            ToolGrant("world_inspect", allowed=True),
            ToolGrant("code_execute", allowed=False),
            ToolGrant("engine_config", allowed=False),
        ],
        creativity=CreativityLevel.CONSERVATIVE,
        verbosity=Verbosity.DETAILED,
        system_prompt_suffix="Focus on identifying issues and suggesting fixes.",
        behavioral_constraints=[
            "Be constructive, not just critical",
            "Prioritize issues by impact on player experience",
            "Suggest specific, actionable improvements",
        ],
        preferred_models=["gpt-4o", "claude-sonnet-4-20250514"],
        icon="test",
    ),
}

DOMAIN_TO_PERSONA: Dict[str, str] = {
    "game_design": "game_designer",
    "level_design": "level_architect",
    "systems": "systems_engineer",
    "storytelling": "narrative_director",
    "art_audio": "asset_curator",
    "quality": "quality_tester",
}


class PersonaSystem:
    """
    Role-based agent persona management for SparkLabs.

    Provides predefined persona profiles for game engine tasks
    and supports custom persona creation. Each persona defines
    tool access, creativity preference, and behavioral rules.

    Usage:
        ps = PersonaSystem()
        designer = ps.get_persona("game_designer")
        if designer.has_tool("world_builder"):
            # Agent can use world builder
            pass
        
        # Get persona for a specific domain
        persona = ps.get_persona_for_domain("level_design")
    """

    def __init__(self):
        self._personas: Dict[str, AgentPersona] = dict(PERSONA_PROFILES)
        self._active_persona: Dict[str, str] = {}
        self._persona_usage: Dict[str, int] = {}

    def get_persona(self, persona_id: str) -> Optional[AgentPersona]:
        return self._personas.get(persona_id)

    def get_persona_for_domain(self, domain: str) -> Optional[AgentPersona]:
        pid = DOMAIN_TO_PERSONA.get(domain)
        if pid:
            return self._personas.get(pid)
        for persona in self._personas.values():
            if persona.domain == domain:
                return persona
        return None

    def list_personas(self) -> List[str]:
        return list(self._personas.keys())

    def list_domains(self) -> List[str]:
        return list(set(p.domain for p in self._personas.values()))

    def register_custom(self, persona: AgentPersona) -> str:
        self._personas[persona.persona_id] = persona
        return persona.persona_id

    def remove_custom(self, persona_id: str) -> bool:
        if persona_id in PERSONA_PROFILES:
            return False
        return self._personas.pop(persona_id, None) is not None

    def assign_to_session(self, session_id: str, persona_id: str) -> bool:
        if persona_id not in self._personas:
            return False
        self._active_persona[session_id] = persona_id
        self._persona_usage[persona_id] = self._persona_usage.get(persona_id, 0) + 1
        return True

    def get_session_persona(self, session_id: str) -> Optional[AgentPersona]:
        pid = self._active_persona.get(session_id)
        if pid:
            return self._personas.get(pid)
        return None

    def unassign_session(self, session_id: str) -> None:
        self._active_persona.pop(session_id, None)

    def get_tool_policy(
        self, persona_id: str, tool_name: str,
    ) -> Tuple[bool, bool]:
        persona = self._personas.get(persona_id)
        if not persona:
            return (False, True)
        return (
            persona.has_tool(tool_name),
            persona.needs_approval_for(tool_name),
        )

    def get_system_prompt_for(
        self, persona_id: str, base_prompt: str = "",
    ) -> str:
        persona = self._personas.get(persona_id)
        if not persona:
            return base_prompt
        parts = [persona.role_description]
        if persona.system_prompt_suffix:
            parts.append(persona.system_prompt_suffix)
        if persona.behavioral_constraints:
            parts.append("Constraints:")
            parts.extend(f"- {c}" for c in persona.behavioral_constraints)
        if base_prompt:
            parts.append(base_prompt)
        return "\n".join(parts)

    def get_stats(self) -> dict:
        return {
            "personas": len(self._personas),
            "domains": len(self.list_domains()),
            "active_sessions": len(self._active_persona),
            "usage": dict(self._persona_usage),
            "builtin_count": len(PERSONA_PROFILES),
            "custom_count": len(self._personas) - len(PERSONA_PROFILES),
        }

    def clear(self) -> None:
        self._active_persona.clear()
        self._persona_usage.clear()

    def assign_persona(self, role: str, session_id: str = "default") -> Optional[AgentPersona]:
        persona = self.get_persona(role)
        if not persona:
            persona = self.get_persona_for_domain(role)
        if persona:
            self.assign_to_session(session_id, persona.persona_id)
        return persona


_global_persona_system: Optional[PersonaSystem] = None


def get_persona_system() -> PersonaSystem:
    global _global_persona_system
    if _global_persona_system is None:
        _global_persona_system = PersonaSystem()
    return _global_persona_system
