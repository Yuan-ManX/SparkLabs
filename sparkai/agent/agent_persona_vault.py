"""
PersonaVault - Downloadable, shareable AI persona manager for SparkLabs.

Manages prefabricated AI behavior profiles that game developers can
switch between for different development tasks such as level design,
bug hunting, performance optimization, and narrative writing. Each
persona encapsulates a system prompt, behavioral rules, tool preferences,
and knowledge tags that shape how the agent responds.

The vault is a singleton that maintains a shared catalog of personas,
tracks swap history across sessions, and supports persona packs for
grouping related profiles. Personas can be exported as portable
dictionaries and imported from external sources.

Architecture:
    PersonaVault (singleton)
        |-- AIPersona (behavior profile with role, tone, complexity)
        |-- PersonaSwapLog (activity trail when personas are switched)
        |-- PersonaPack (named collection of related persona profiles)
        |-- Enum catalog (PersonaRole, PersonaTone, PersonaComplexity, VaultAction)

Persona Lifecycle:
    create -> (optional: rate, update) -> activate -> deactivate -> delete
    export/import enables cross-project persona sharing
    packs organize personas into themed bundles
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

_time_module = time


class PersonaRole(Enum):
    LEVEL_DESIGNER = "level_designer"
    BUG_HUNTER = "bug_hunter"
    PERF_OPTIMIZER = "perf_optimizer"
    NARRATIVE_WRITER = "narrative_writer"
    UI_DESIGNER = "ui_designer"
    AUDIO_ENGINEER = "audio_engineer"
    GAME_BALANCER = "game_balancer"
    TUTORIAL_CREATOR = "tutorial_creator"
    LOCALIZATION_EXPERT = "localization_expert"
    CUSTOM = "custom"


class PersonaTone(Enum):
    PROFESSIONAL = "professional"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    PLAYFUL = "playful"
    MENTORING = "mentoring"
    CONCISE = "concise"


class PersonaComplexity(Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    ELABORATE = "elaborate"
    EXPERT = "expert"


class VaultAction(Enum):
    INSTALL = "install"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    EXPORT = "export"
    IMPORT = "import"
    SHARE = "share"


_ROLE_DESCRIPTIONS: Dict[PersonaRole, str] = {
    PersonaRole.LEVEL_DESIGNER: (
        "You are a level designer. Your role is to craft spatial layouts, "
        "design environmental flow, and create gameplay spaces that balance "
        "challenge with player engagement."
    ),
    PersonaRole.BUG_HUNTER: (
        "You are a bug hunter. Your role is to find defects, trace root "
        "causes, and produce minimal reproduction cases. You think in "
        "terms of edge cases, assertions, and regression risks."
    ),
    PersonaRole.PERF_OPTIMIZER: (
        "You are a performance optimizer. Your role is to profile systems, "
        "identify bottlenecks, and propose targeted improvements. You think "
        "in terms of frame budgets, draw calls, and memory pressure."
    ),
    PersonaRole.NARRATIVE_WRITER: (
        "You are a narrative writer. Your role is to craft story arcs, "
        "write dialogue, and develop characters with emotional depth. You "
        "think in terms of beats, arcs, and player agency."
    ),
    PersonaRole.UI_DESIGNER: (
        "You are a UI designer. Your role is to create intuitive interfaces, "
        "design HUD layouts, and ensure accessibility across devices. You "
        "think in terms of user flow, affordance, and visual hierarchy."
    ),
    PersonaRole.AUDIO_ENGINEER: (
        "You are an audio engineer. Your role is to design soundscapes, "
        "configure audio assets, and ensure spatial audio consistency. You "
        "think in terms of mix balance, frequency, and listener position."
    ),
    PersonaRole.GAME_BALANCER: (
        "You are a game balancer. Your role is to tune numbers, analyze "
        "win rates, and ensure fair progression. You think in terms of "
        "curves, thresholds, and trade-offs."
    ),
    PersonaRole.TUTORIAL_CREATOR: (
        "You are a tutorial creator. Your role is to design onboarding "
        "flows, write instructional content, and scaffold player learning. "
        "You think in terms of teachable moments and progressive disclosure."
    ),
    PersonaRole.LOCALIZATION_EXPERT: (
        "You are a localization expert. Your role is to adapt content for "
        "different regions, maintain translation quality, and handle "
        "locale-specific formatting. You think in terms of locale, context, "
        "and cultural sensitivity."
    ),
    PersonaRole.CUSTOM: (
        "You are a custom persona configured for a specific development task. "
        "Your behavior is defined by the user-provided system prompt and rules."
    ),
}


_TONE_ADJECTIVES: Dict[PersonaTone, str] = {
    PersonaTone.PROFESSIONAL: "Be formal, structured, and business-appropriate.",
    PersonaTone.CREATIVE: "Be imaginative, expressive, and idea-driven.",
    PersonaTone.ANALYTICAL: "Be logical, data-driven, and methodical.",
    PersonaTone.PLAYFUL: "Be lighthearted, humorous, and engaging.",
    PersonaTone.MENTORING: "Be instructive, patient, and educational.",
    PersonaTone.CONCISE: "Be brief, direct, and to the point.",
}


_COMPLEXITY_CONFIG: Dict[PersonaComplexity, Dict[str, Any]] = {
    PersonaComplexity.SIMPLE: {
        "label": "Simple",
        "max_rules": 5,
        "max_tools": 8,
        "description": "Minimal behavior profile for quick tasks.",
    },
    PersonaComplexity.STANDARD: {
        "label": "Standard",
        "max_rules": 12,
        "max_tools": 20,
        "description": "Balanced profile suitable for most development tasks.",
    },
    PersonaComplexity.ELABORATE: {
        "label": "Elaborate",
        "max_rules": 25,
        "max_tools": 40,
        "description": "Detailed profile for complex multi-step workflows.",
    },
    PersonaComplexity.EXPERT: {
        "label": "Expert",
        "max_rules": 50,
        "max_tools": 80,
        "description": "Comprehensive profile with deep domain knowledge.",
    },
}


@dataclass
class AIPersona:
    """A prefabricated AI behavior profile for a game development role.

    Each persona defines how the agent should behave: what system prompt to
    use, which behavioral rules to follow, and which tools to prefer with
    what priority. Personas are shareable and can be exported/imported.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    role: PersonaRole = PersonaRole.CUSTOM
    tone: PersonaTone = PersonaTone.PROFESSIONAL
    complexity: PersonaComplexity = PersonaComplexity.STANDARD
    system_prompt: str = ""
    behavior_rules: List[str] = field(default_factory=list)
    tool_preferences: Dict[str, int] = field(default_factory=dict)
    knowledge_tags: List[str] = field(default_factory=list)
    version: int = 1
    author: str = ""
    is_active: bool = False
    usage_count: int = 0
    rating: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def __post_init__(self):
        self.rating = max(0.0, min(5.0, self.rating))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "tone": self.tone.value,
            "complexity": self.complexity.value,
            "system_prompt": self.system_prompt,
            "behavior_rules": self.behavior_rules,
            "tool_preferences": self.tool_preferences,
            "knowledge_tags": self.knowledge_tags,
            "version": self.version,
            "author": self.author,
            "is_active": self.is_active,
            "usage_count": self.usage_count,
            "rating": self.rating,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class PersonaSwapLog:
    """Record of a persona activation or deactivation event.

    Tracks which persona was active before and after a swap, along with
    the reason and session context. Used for analytics and activity audit.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_persona_id: Optional[str] = None
    to_persona_id: str = ""
    reason: str = ""
    session_id: Optional[str] = None
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_persona_id": self.from_persona_id,
            "to_persona_id": self.to_persona_id,
            "reason": self.reason,
            "session_id": self.session_id,
            "created_at": self.created_at,
        }


@dataclass
class PersonaPack:
    """A named collection of persona profiles grouped for a shared purpose.

    Packs allow developers to bundle related personas — for example, all
    personas needed for an RPG project or a mobile-game workflow. Packs
    can be exported and shared as a single unit.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    personas: List[str] = field(default_factory=list)
    pack_name: str = ""
    description: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "personas": self.personas,
            "pack_name": self.pack_name,
            "description": self.description,
            "created_at": self.created_at,
        }


class PersonaVault:
    """Singleton vault for managing downloadable, shareable AI personas.

    The vault is the central authority for persona lifecycle: creation,
    activation, rating, export, import, and deletion. It maintains a
    swap history log and supports persona packs for grouping.

    Usage:
        vault = PersonaVault.get_instance()
        persona = vault.create_persona(
            name="Level Designer Pro",
            role=PersonaRole.LEVEL_DESIGNER,
            tone=PersonaTone.CREATIVE,
            complexity=PersonaComplexity.ELABORATE,
            system_prompt="You are an expert level designer...",
            behavior_rules=["Consider player flow first", "Document layout assumptions"],
            tool_preferences={"world_builder": 90, "entity_create": 70},
            knowledge_tags=["layout", "flow", "spatial-design"],
            author="design-team",
        )
        vault.activate_persona(persona.id, session_id="session-42")
    """

    _instance: Optional["PersonaVault"] = None
    _lock = threading.RLock()

    MAX_PERSONAS = 500
    MAX_SWAP_LOG_ENTRIES = 2000
    MAX_PACKS = 100
    MAX_RULES_PER_PERSONA = 50
    MAX_TAGS_PER_PERSONA = 30

    def __new__(cls) -> "PersonaVault":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._personas: Dict[str, AIPersona] = {}
        self._swap_logs: List[PersonaSwapLog] = []
        self._packs: Dict[str, PersonaPack] = {}
        self._active_role_map: Dict[PersonaRole, str] = {}
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "PersonaVault":
        return cls()

    @classmethod
    def reset_instance(cls) -> None:
        """Clear the singleton for testing or reinitialization."""
        with cls._lock:
            cls._instance = None

    # ------------------------------------------------------------------
    # Persona CRUD
    # ------------------------------------------------------------------

    def create_persona(
        self,
        name: str,
        role: PersonaRole = PersonaRole.CUSTOM,
        tone: PersonaTone = PersonaTone.PROFESSIONAL,
        complexity: PersonaComplexity = PersonaComplexity.STANDARD,
        system_prompt: str = "",
        behavior_rules: Optional[List[str]] = None,
        tool_preferences: Optional[Dict[str, int]] = None,
        knowledge_tags: Optional[List[str]] = None,
        author: str = "",
    ) -> AIPersona:
        """Create a new AI persona and store it in the vault.

        Args:
            name: Display name for the persona.
            role: The game development role this persona targets.
            tone: Communication style preference.
            complexity: How detailed the behavior profile should be.
            system_prompt: Core instruction that shapes agent behavior.
            behavior_rules: List of behavioral constraints.
            tool_preferences: Dict mapping tool names to priority scores (0-100).
            knowledge_tags: Tags for categorization and search.
            author: Creator identifier for attribution.

        Returns:
            The newly created AIPersona instance.

        Raises:
            ValueError: If the vault is at maximum capacity.
        """
        if len(self._personas) >= self.MAX_PERSONAS:
            raise ValueError(
                f"PersonaVault is at capacity ({self.MAX_PERSONAS} personas). "
                "Delete unused personas before creating new ones."
            )

        rules = behavior_rules or []
        if len(rules) > self.MAX_RULES_PER_PERSONA:
            rules = rules[:self.MAX_RULES_PER_PERSONA]

        tags = knowledge_tags or []
        if len(tags) > self.MAX_TAGS_PER_PERSONA:
            tags = tags[:self.MAX_TAGS_PER_PERSONA]

        tools = tool_preferences or {}
        tools = {k: max(0, min(100, v)) for k, v in tools.items()}

        now = _time_module.time()
        persona = AIPersona(
            name=name,
            role=role,
            tone=tone,
            complexity=complexity,
            system_prompt=system_prompt,
            behavior_rules=rules,
            tool_preferences=tools,
            knowledge_tags=tags,
            author=author,
            created_at=now,
            updated_at=now,
        )
        self._personas[persona.id] = persona
        return persona

    def update_persona(self, persona_id: str, **updates: Any) -> Optional[AIPersona]:
        """Update fields on an existing persona.

        Only the provided keyword arguments are modified; all other fields
        remain unchanged. The updated_at timestamp is refreshed automatically.

        Args:
            persona_id: The unique identifier of the persona to update.
            **updates: Keyword arguments matching AIPersona field names.

        Returns:
            The updated AIPersona, or None if the persona_id was not found.
        """
        persona = self._personas.get(persona_id)
        if persona is None:
            return None

        updatable_fields = {
            "name", "role", "tone", "complexity", "system_prompt",
            "behavior_rules", "tool_preferences", "knowledge_tags",
            "version", "author",
        }

        for key, value in updates.items():
            if key not in updatable_fields:
                continue
            if key == "behavior_rules" and isinstance(value, list):
                value = value[:self.MAX_RULES_PER_PERSONA]
            if key == "knowledge_tags" and isinstance(value, list):
                value = value[:self.MAX_TAGS_PER_PERSONA]
            if key == "tool_preferences" and isinstance(value, dict):
                value = {k: max(0, min(100, v)) for k, v in value.items()}
            setattr(persona, key, value)

        persona.updated_at = _time_module.time()
        return persona

    def delete_persona(self, persona_id: str) -> bool:
        """Remove a persona from the vault.

        If the persona is currently active, it is deactivated first.
        References to this persona in packs are also cleaned up.

        Args:
            persona_id: The unique identifier of the persona to delete.

        Returns:
            True if the persona was found and deleted, False otherwise.
        """
        persona = self._personas.get(persona_id)
        if persona is None:
            return False

        if persona.is_active:
            self.deactivate_persona(persona_id)

        for role, pid in list(self._active_role_map.items()):
            if pid == persona_id:
                del self._active_role_map[role]

        for pack in self._packs.values():
            if persona_id in pack.personas:
                pack.personas = [p for p in pack.personas if p != persona_id]

        del self._personas[persona_id]
        return True

    def get_persona(self, persona_id: str) -> Optional[AIPersona]:
        """Retrieve a single persona by its unique identifier.

        Args:
            persona_id: The unique identifier of the persona to fetch.

        Returns:
            The matching AIPersona, or None if not found.
        """
        return self._personas.get(persona_id)

    def list_personas(
        self,
        role: Optional[PersonaRole] = None,
        tone: Optional[PersonaTone] = None,
        is_active: Optional[bool] = None,
    ) -> List[AIPersona]:
        """List personas, optionally filtered by role, tone, or active state.

        Args:
            role: Filter by PersonaRole. None means no role filter.
            tone: Filter by PersonaTone. None means no tone filter.
            is_active: Filter by activation state. None means no filter.

        Returns:
            A list of matching AIPersona instances.
        """
        results: List[AIPersona] = []
        for persona in self._personas.values():
            if role is not None and persona.role != role:
                continue
            if tone is not None and persona.tone != tone:
                continue
            if is_active is not None and persona.is_active != is_active:
                continue
            results.append(persona)
        return results

    # ------------------------------------------------------------------
    # Activation / Deactivation
    # ------------------------------------------------------------------

    def activate_persona(
        self,
        persona_id: str,
        session_id: Optional[str] = None,
        reason: str = "",
    ) -> Optional[AIPersona]:
        """Activate a persona, deactivating any currently active persona of the same role.

        Records a swap log entry documenting the transition. The persona's
        usage_count is incremented and its is_active flag is set.

        Args:
            persona_id: The unique identifier of the persona to activate.
            session_id: Optional session context for the swap log.
            reason: Optional description of why this persona is being activated.

        Returns:
            The activated AIPersona, or None if the persona_id was not found.
        """
        persona = self._personas.get(persona_id)
        if persona is None:
            return None

        from_persona_id: Optional[str] = None

        current_active_id = self._active_role_map.get(persona.role)
        if current_active_id and current_active_id != persona_id:
            current = self._personas.get(current_active_id)
            if current:
                current.is_active = False
            from_persona_id = current_active_id
        elif current_active_id == persona_id:
            from_persona_id = persona_id

        persona.is_active = True
        persona.usage_count += 1
        persona.updated_at = _time_module.time()
        self._active_role_map[persona.role] = persona_id

        swap_log = PersonaSwapLog(
            from_persona_id=from_persona_id,
            to_persona_id=persona_id,
            reason=reason,
            session_id=session_id,
        )
        self._swap_logs.append(swap_log)

        if len(self._swap_logs) > self.MAX_SWAP_LOG_ENTRIES:
            self._swap_logs = self._swap_logs[-self.MAX_SWAP_LOG_ENTRIES:]

        return persona

    def deactivate_persona(self, persona_id: str) -> bool:
        """Deactivate a persona by its identifier.

        Clears the persona from its role slot in the active role map.

        Args:
            persona_id: The unique identifier of the persona to deactivate.

        Returns:
            True if the persona was found and deactivated, False otherwise.
        """
        persona = self._personas.get(persona_id)
        if persona is None:
            return False

        persona.is_active = False
        persona.updated_at = _time_module.time()

        if self._active_role_map.get(persona.role) == persona_id:
            del self._active_role_map[persona.role]

        swap_log = PersonaSwapLog(
            from_persona_id=persona_id,
            to_persona_id="",
            reason="deactivated",
        )
        self._swap_logs.append(swap_log)

        if len(self._swap_logs) > self.MAX_SWAP_LOG_ENTRIES:
            self._swap_logs = self._swap_logs[-self.MAX_SWAP_LOG_ENTRIES:]

        return True

    def get_active_persona(
        self, role: Optional[PersonaRole] = None,
    ) -> Optional[AIPersona]:
        """Get the currently active persona, optionally filtered by role.

        Args:
            role: If provided, returns the active persona for that specific
                  role. If None, returns the first active persona found.

        Returns:
            The active AIPersona matching the criteria, or None.
        """
        if role is not None:
            persona_id = self._active_role_map.get(role)
            if persona_id:
                return self._personas.get(persona_id)
            return None

        for persona in self._personas.values():
            if persona.is_active:
                return persona
        return None

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export_persona(self, persona_id: str) -> Dict[str, Any]:
        """Export a persona as a portable dictionary.

        The exported format is suitable for file storage, network transfer,
        or sharing with other SparkLabs instances. The persona's internal
        state (is_active, usage_count) is excluded from the export.

        Args:
            persona_id: The unique identifier of the persona to export.

        Returns:
            A dictionary representation of the persona, or an empty dict
            with an error key if the persona was not found.
        """
        persona = self._personas.get(persona_id)
        if persona is None:
            return {"error": f"Persona not found: {persona_id}"}

        return {
            "format_version": 1,
            "exported_at": _time_module.time(),
            "persona": {
                "name": persona.name,
                "role": persona.role.value,
                "tone": persona.tone.value,
                "complexity": persona.complexity.value,
                "system_prompt": persona.system_prompt,
                "behavior_rules": persona.behavior_rules,
                "tool_preferences": persona.tool_preferences,
                "knowledge_tags": persona.knowledge_tags,
                "version": persona.version,
                "author": persona.author,
                "rating": persona.rating,
                "created_at": persona.created_at,
                "updated_at": persona.updated_at,
            },
        }

    def import_persona(self, data: Dict[str, Any]) -> Optional[AIPersona]:
        """Import a persona from an exported dictionary.

        Creates a new persona in the vault from the provided data.
        The imported persona gets a new unique ID and is marked as inactive.

        Args:
            data: A dictionary in the format produced by export_persona.

        Returns:
            The newly created AIPersona, or None if the data is invalid.
        """
        persona_data = data.get("persona")
        if not isinstance(persona_data, dict):
            return None

        name = persona_data.get("name", "Imported Persona")
        role_value = persona_data.get("role", "custom")
        tone_value = persona_data.get("tone", "professional")
        complexity_value = persona_data.get("complexity", "standard")

        try:
            role = PersonaRole(role_value)
        except ValueError:
            role = PersonaRole.CUSTOM
        try:
            tone = PersonaTone(tone_value)
        except ValueError:
            tone = PersonaTone.PROFESSIONAL
        try:
            complexity = PersonaComplexity(complexity_value)
        except ValueError:
            complexity = PersonaComplexity.STANDARD

        system_prompt = persona_data.get("system_prompt", "")
        behavior_rules = persona_data.get("behavior_rules", [])
        tool_preferences = persona_data.get("tool_preferences", {})
        knowledge_tags = persona_data.get("knowledge_tags", [])
        author = persona_data.get("author", "imported")
        rating = persona_data.get("rating", 0.0)
        version = persona_data.get("version", 1)

        if len(self._personas) >= self.MAX_PERSONAS:
            return None

        if len(behavior_rules) > self.MAX_RULES_PER_PERSONA:
            behavior_rules = behavior_rules[:self.MAX_RULES_PER_PERSONA]
        if len(knowledge_tags) > self.MAX_TAGS_PER_PERSONA:
            knowledge_tags = knowledge_tags[:self.MAX_TAGS_PER_PERSONA]
        tool_preferences = {k: max(0, min(100, v)) for k, v in tool_preferences.items()}

        now = _time_module.time()
        persona = AIPersona(
            name=name,
            role=role,
            tone=tone,
            complexity=complexity,
            system_prompt=system_prompt,
            behavior_rules=behavior_rules,
            tool_preferences=tool_preferences,
            knowledge_tags=knowledge_tags,
            version=version,
            author=author,
            is_active=False,
            usage_count=0,
            rating=rating,
            created_at=now,
            updated_at=now,
        )
        self._personas[persona.id] = persona
        return persona

    # ------------------------------------------------------------------
    # Rating
    # ------------------------------------------------------------------

    def rate_persona(self, persona_id: str, rating: float) -> bool:
        """Assign a rating to a persona.

        Ratings are clamped to the range [0.0, 5.0]. This is a simple
        averaging mechanism suitable for developer feedback.

        Args:
            persona_id: The unique identifier of the persona to rate.
            rating: A score between 0.0 (worst) and 5.0 (best).

        Returns:
            True if the persona was found and rated, False otherwise.
        """
        persona = self._personas.get(persona_id)
        if persona is None:
            return False

        clamped = max(0.0, min(5.0, rating))
        persona.rating = clamped
        persona.updated_at = _time_module.time()
        return True

    # ------------------------------------------------------------------
    # Packs
    # ------------------------------------------------------------------

    def create_pack(
        self,
        name: str,
        description: str = "",
        persona_ids: Optional[List[str]] = None,
    ) -> PersonaPack:
        """Create a persona pack bundling related profiles together.

        Persona IDs that do not exist in the vault are silently skipped.

        Args:
            name: Display name for the pack.
            description: Short description of the pack's purpose.
            persona_ids: List of persona IDs to include in the pack.

        Returns:
            The newly created PersonaPack instance.

        Raises:
            ValueError: If the vault is at maximum pack capacity.
        """
        if len(self._packs) >= self.MAX_PACKS:
            raise ValueError(
                f"PersonaVault is at pack capacity ({self.MAX_PACKS} packs)."
            )

        valid_ids: List[str] = []
        for pid in (persona_ids or []):
            if pid in self._personas:
                valid_ids.append(pid)

        pack = PersonaPack(
            personas=valid_ids,
            pack_name=name,
            description=description,
        )
        self._packs[pack.id] = pack
        return pack

    def get_pack(self, pack_id: str) -> Optional[PersonaPack]:
        """Retrieve a persona pack by its identifier.

        Args:
            pack_id: The unique identifier of the pack.

        Returns:
            The matching PersonaPack, or None if not found.
        """
        return self._packs.get(pack_id)

    def list_packs(self) -> List[PersonaPack]:
        """List all packs in the vault.

        Returns:
            A list of all PersonaPack instances.
        """
        return list(self._packs.values())

    def delete_pack(self, pack_id: str) -> bool:
        """Remove a pack from the vault.

        Persona references are not affected — only the pack container
        is deleted.

        Args:
            pack_id: The unique identifier of the pack to delete.

        Returns:
            True if the pack was found and deleted, False otherwise.
        """
        if pack_id not in self._packs:
            return False
        del self._packs[pack_id]
        return True

    # ------------------------------------------------------------------
    # Swap History
    # ------------------------------------------------------------------

    def get_swap_history(
        self,
        session_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[PersonaSwapLog]:
        """Retrieve swap log entries, optionally filtered by session.

        Args:
            session_id: If provided, returns only entries for that session.
                        If None, returns entries across all sessions.
            limit: Maximum number of log entries to return (clamped to
                   MAX_SWAP_LOG_ENTRIES).

        Returns:
            A list of PersonaSwapLog entries, most recent first.
        """
        limit = max(1, min(limit, self.MAX_SWAP_LOG_ENTRIES))

        if session_id is not None:
            filtered = [
                log for log in self._swap_logs
                if log.session_id == session_id
            ]
        else:
            filtered = list(self._swap_logs)

        return filtered[-limit:][::-1]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about the vault's contents.

        Returns:
            A dictionary with persona counts, pack counts, active roles,
            most-used personas, and activity summaries.
        """
        total_personas = len(self._personas)
        active_count = sum(1 for p in self._personas.values() if p.is_active)
        total_packs = len(self._packs)
        total_swaps = len(self._swap_logs)

        role_counts: Dict[str, int] = {}
        for persona in self._personas.values():
            role_key = persona.role.value
            role_counts[role_key] = role_counts.get(role_key, 0) + 1

        tone_counts: Dict[str, int] = {}
        for persona in self._personas.values():
            tone_key = persona.tone.value
            tone_counts[tone_key] = tone_counts.get(tone_key, 0) + 1

        avg_rating: float = 0.0
        rated_count = sum(1 for p in self._personas.values() if p.rating > 0)
        if rated_count > 0:
            avg_rating = sum(p.rating for p in self._personas.values() if p.rating > 0) / rated_count

        most_used: List[Dict[str, Any]] = []
        sorted_by_usage = sorted(
            self._personas.values(),
            key=lambda p: p.usage_count,
            reverse=True,
        )
        for persona in sorted_by_usage[:5]:
            most_used.append({
                "id": persona.id,
                "name": persona.name,
                "role": persona.role.value,
                "usage_count": persona.usage_count,
            })

        active_roles = {
            role.value: persona_id
            for role, persona_id in self._active_role_map.items()
        }

        swap_sessions: Dict[str, int] = {}
        for log in self._swap_logs:
            if log.session_id:
                swap_sessions[log.session_id] = swap_sessions.get(log.session_id, 0) + 1
        most_active_sessions = sorted(
            swap_sessions.items(), key=lambda x: x[1], reverse=True,
        )[:5]

        return {
            "personas": {
                "total": total_personas,
                "active": active_count,
                "inactive": total_personas - active_count,
                "by_role": role_counts,
                "by_tone": tone_counts,
                "avg_rating": round(avg_rating, 2),
                "rated_count": rated_count,
            },
            "packs": {
                "total": total_packs,
                "personas_in_packs": sum(len(p.personas) for p in self._packs.values()),
            },
            "swaps": {
                "total": total_swaps,
                "sessions_with_swaps": len(swap_sessions),
                "most_active_sessions": [
                    {"session_id": sid, "swaps": count}
                    for sid, count in most_active_sessions
                ],
            },
            "active_roles": active_roles,
            "most_used_personas": most_used,
            "capacity": {
                "personas_used": total_personas,
                "personas_max": self.MAX_PERSONAS,
                "packs_used": total_packs,
                "packs_max": self.MAX_PACKS,
                "swap_log_entries": total_swaps,
                "swap_log_max": self.MAX_SWAP_LOG_ENTRIES,
            },
        }

    # ------------------------------------------------------------------
    # Bulk Operations
    # ------------------------------------------------------------------

    def deactivate_all(self) -> int:
        """Deactivate all currently active personas.

        Returns:
            The number of personas that were deactivated.
        """
        count = 0
        for persona in list(self._personas.values()):
            if persona.is_active:
                persona.is_active = False
                persona.updated_at = _time_module.time()
                count += 1
        self._active_role_map.clear()
        return count

    def import_pack(self, data: Dict[str, Any]) -> Optional[PersonaPack]:
        """Import a persona pack from an exported dictionary.

        Creates a new pack in the vault from the provided data. The pack
        gets a new ID and references existing persona IDs in the vault.

        Args:
            data: A dictionary containing pack_name, description, and
                  a list of persona_ids.

        Returns:
            The newly created PersonaPack, or None if the data is invalid.
        """
        pack_name = data.get("pack_name")
        if not isinstance(pack_name, str) or not pack_name:
            return None

        if len(self._packs) >= self.MAX_PACKS:
            return None

        description = data.get("description", "")
        persona_ids = data.get("personas", [])
        if not isinstance(persona_ids, list):
            persona_ids = []

        valid_ids = [pid for pid in persona_ids if pid in self._personas]

        pack = PersonaPack(
            personas=valid_ids,
            pack_name=pack_name,
            description=description,
        )
        self._packs[pack.id] = pack
        return pack

    def export_pack(self, pack_id: str) -> Dict[str, Any]:
        """Export a persona pack as a portable dictionary.

        Args:
            pack_id: The unique identifier of the pack to export.

        Returns:
            A dictionary representation of the pack, or an empty dict
            with an error key if the pack was not found.
        """
        pack = self._packs.get(pack_id)
        if pack is None:
            return {"error": f"Pack not found: {pack_id}"}

        persona_details: List[Dict[str, Any]] = []
        for pid in pack.personas:
            persona = self._personas.get(pid)
            if persona:
                persona_details.append({
                    "id": persona.id,
                    "name": persona.name,
                    "role": persona.role.value,
                })

        return {
            "format_version": 1,
            "exported_at": _time_module.time(),
            "pack_name": pack.pack_name,
            "description": pack.description,
            "personas": pack.personas,
            "persona_details": persona_details,
            "persona_count": len(persona_details),
        }

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_personas(
        self,
        query: str = "",
        tags: Optional[List[str]] = None,
    ) -> List[AIPersona]:
        """Search personas by name, system prompt content, or knowledge tags.

        Matching is case-insensitive. When tags are provided, a persona must
        match at least one of the specified tags.

        Args:
            query: Text to search for in persona name and system prompt.
            tags: List of knowledge tags to filter by (OR match).

        Returns:
            A list of matching AIPersona instances.
        """
        query_lower = query.lower()
        tag_set = set(t.lower() for t in (tags or []))

        results: List[AIPersona] = []
        for persona in self._personas.values():
            if query_lower:
                name_match = query_lower in persona.name.lower()
                prompt_match = query_lower in persona.system_prompt.lower()
                if not (name_match or prompt_match):
                    continue

            if tag_set:
                persona_tags = set(t.lower() for t in persona.knowledge_tags)
                if not tag_set.intersection(persona_tags):
                    continue

            results.append(persona)
        return results


def get_persona_vault() -> PersonaVault:
    """Module-level accessor for the PersonaVault singleton.

    Returns:
        The shared PersonaVault instance.
    """
    return PersonaVault.get_instance()