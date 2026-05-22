"""
SparkLabs Agent - Personality System

Configurable agent personality profiles that shape interaction style,
decision-making patterns, and creative output across the game engine
development lifecycle. Supports weighted trait blending, profile cloning,
multi-profile blending, tone evaluation, and scenario-based suggestions.

Architecture:
  PersonalitySystem
    |-- PersonalityProfile (core profile with trait weights and archetype)
    |-- TraitWeight (per-trait numerical weight with justification)
    |-- InteractionConfig (style/tone/pace configuration)
    |-- RoleDefinition (archetype-specific role scaffolding)
    |-- StyleSample (example interaction snippets for tone calibration)

Personality Traits:
  - CREATIVE: generative ideation, novel approaches
  - ANALYTICAL: data-driven reasoning, logic chains
  - PLAYFUL: lighthearted framing, humor injection
  - SERIOUS: formal tone, precision-oriented
  - CONCISE: minimal output, high signal-to-noise
  - ELABORATE: detailed exposition, thorough coverage
  - CAUTIOUS: risk-aware, edge-case conscious
  - BOLD: confident assertions, decisive recommendations

Role Archetypes:
  - GENERALIST: broad-spectrum game development reasoning
  - LEVEL_DESIGNER: spatial layout and environmental flow thinking
  - NARRATIVE_DESIGNER: story, dialogue, and character arc thinking
  - SYSTEMS_DESIGNER: mechanics, rules, and engine architecture thinking
  - ART_DIRECTOR: visual style and asset cohesion thinking
  - QA_TESTER: quality, balance, and edge-case thinking

Usage:
    ps = get_personality_system()
    profile = ps.create_profile("Design Mentor", "A creative yet structured design guide",
                                [("CREATIVE", 0.8), ("ELABORATE", 0.6), ("BOLD", 0.5)],
                                archetype=RoleArchetype.LEVEL_DESIGNER,
                                style=InteractionStyle.MENTOR)
    prompt = ps.generate_prompt_prefix(profile.id)
"""
from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class PersonalityTrait(Enum):
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    PLAYFUL = "playful"
    SERIOUS = "serious"
    CONCISE = "concise"
    ELABORATE = "elaborate"
    CAUTIOUS = "cautious"
    BOLD = "bold"


class InteractionStyle(Enum):
    FORMAL = "formal"
    CASUAL = "casual"
    MENTOR = "mentor"
    PEER = "peer"
    GAME_DESIGNER = "game_designer"


class RoleArchetype(Enum):
    GENERALIST = "generalist"
    LEVEL_DESIGNER = "level_designer"
    NARRATIVE_DESIGNER = "narrative_designer"
    SYSTEMS_DESIGNER = "systems_designer"
    ART_DIRECTOR = "art_director"
    QA_TESTER = "qa_tester"


class ScenarioType(Enum):
    BRAINSTORMING = "brainstorming"
    DEBUGGING = "debugging"
    EXPLAINING = "explaining"
    GENERATING = "generating"
    REVIEWING = "reviewing"
    PLANNING = "planning"
    TESTING = "testing"


@dataclass
class TraitWeight:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    trait: PersonalityTrait = PersonalityTrait.CREATIVE
    weight: float = 0.5
    justification: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "trait": self.trait.value,
            "weight": self.weight,
            "justification": self.justification,
            "created_at": self.created_at,
        }


@dataclass
class InteractionConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    style: InteractionStyle = InteractionStyle.CASUAL
    tone: str = ""
    pacing: str = "balanced"
    technical_depth: int = 3
    digression_tolerance: float = 0.3
    greeting_template: str = ""
    closing_template: str = ""
    max_response_length: Optional[int] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "style": self.style.value,
            "tone": self.tone,
            "pacing": self.pacing,
            "technical_depth": self.technical_depth,
            "digression_tolerance": self.digression_tolerance,
            "greeting_template": self.greeting_template,
            "closing_template": self.closing_template,
            "max_response_length": self.max_response_length,
            "created_at": self.created_at,
        }


@dataclass
class RoleDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    archetype: RoleArchetype = RoleArchetype.GENERALIST
    title: str = ""
    scope_description: str = ""
    core_competencies: List[str] = field(default_factory=list)
    recommended_traits: List[str] = field(default_factory=list)
    forbidden_actions: List[str] = field(default_factory=list)
    tool_preferences: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "archetype": self.archetype.value,
            "title": self.title,
            "scope_description": self.scope_description,
            "core_competencies": self.core_competencies,
            "recommended_traits": self.recommended_traits,
            "forbidden_actions": self.forbidden_actions,
            "tool_preferences": self.tool_preferences,
            "created_at": self.created_at,
        }


@dataclass
class StyleSample:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    profile_id: str = ""
    scenario: ScenarioType = ScenarioType.EXPLAINING
    input_text: str = ""
    output_text: str = ""
    annotation: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "scenario": self.scenario.value,
            "input_text": self.input_text,
            "output_text": self.output_text,
            "annotation": self.annotation,
            "created_at": self.created_at,
        }


@dataclass
class PersonalityProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    trait_weights: Dict[PersonalityTrait, TraitWeight] = field(default_factory=dict)
    interaction_config: InteractionConfig = field(default_factory=InteractionConfig)
    archetype: RoleArchetype = RoleArchetype.GENERALIST
    role_definition: Optional[RoleDefinition] = None
    style_samples: List[StyleSample] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    is_active: bool = False
    active_for_agent: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trait_weights": {
                t.value: tw.to_dict()
                for t, tw in self.trait_weights.items()
            },
            "interaction_config": self.interaction_config.to_dict(),
            "archetype": self.archetype.value,
            "role_definition": self.role_definition.to_dict() if self.role_definition else None,
            "style_samples": [s.to_dict() for s in self.style_samples],
            "tags": self.tags,
            "is_active": self.is_active,
            "active_for_agent": self.active_for_agent,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "metadata": self.metadata,
        }

    def get_dominant_trait(self) -> Optional[Tuple[PersonalityTrait, float]]:
        if not self.trait_weights:
            return None
        dominant = max(self.trait_weights.items(), key=lambda x: x[1].weight)
        return dominant[0], dominant[1].weight

    def get_trait_vector(self) -> List[float]:
        return [
            self.trait_weights.get(t, TraitWeight(trait=t, weight=0.0)).weight
            for t in PersonalityTrait
        ]


ARHCETYPE_DEFAULTS: Dict[RoleArchetype, Dict[str, Any]] = {
    RoleArchetype.GENERALIST: {
        "title": "Generalist Game Developer",
        "scope": "Broad-spectrum game development reasoning across all domains.",
        "traits": ["CREATIVE", "ANALYTICAL", "CONCISE"],
        "competencies": ["cross-domain thinking", "pipeline orchestration", "rapid prototyping"],
    },
    RoleArchetype.LEVEL_DESIGNER: {
        "title": "Level Architect",
        "scope": "Spatial layout, environmental flow, and player navigation design.",
        "traits": ["CREATIVE", "PLAYFUL", "BOLD"],
        "competencies": ["spatial reasoning", "player flow", "encounter design", "environmental storytelling"],
    },
    RoleArchetype.NARRATIVE_DESIGNER: {
        "title": "Narrative Director",
        "scope": "Story structure, dialogue systems, and character development.",
        "traits": ["CREATIVE", "ELABORATE", "PLAYFUL"],
        "competencies": ["story structure", "character arcs", "dialogue writing", "world-building"],
    },
    RoleArchetype.SYSTEMS_DESIGNER: {
        "title": "Systems Engineer",
        "scope": "Mechanics design, rule systems, and engine architecture.",
        "traits": ["ANALYTICAL", "CAUTIOUS", "ELABORATE"],
        "competencies": ["systems thinking", "balance mathematics", "data flow", "entity-component design"],
    },
    RoleArchetype.ART_DIRECTOR: {
        "title": "Art Director",
        "scope": "Visual style definition, palette cohesion, and asset approval.",
        "traits": ["CREATIVE", "BOLD", "ANALYTICAL"],
        "competencies": ["visual composition", "color theory", "style consistency", "asset pipelines"],
    },
    RoleArchetype.QA_TESTER: {
        "title": "Quality Assurance Lead",
        "scope": "Gameplay testing, balance evaluation, and edge-case discovery.",
        "traits": ["CAUTIOUS", "ANALYTICAL", "SERIOUS"],
        "competencies": ["edge-case thinking", "regression testing", "balance analysis", "bug reporting"],
    },
}


SCENARIO_SETTINGS: Dict[ScenarioType, Dict[str, Any]] = {
    ScenarioType.BRAINSTORMING: {
        "recommended_traits": [PersonalityTrait.CREATIVE, PersonalityTrait.PLAYFUL, PersonalityTrait.BOLD],
        "style": InteractionStyle.CASUAL,
        "pacing": "rapid",
        "digression_tolerance": 0.7,
    },
    ScenarioType.DEBUGGING: {
        "recommended_traits": [PersonalityTrait.ANALYTICAL, PersonalityTrait.CAUTIOUS, PersonalityTrait.CONCISE],
        "style": InteractionStyle.FORMAL,
        "pacing": "methodical",
        "digression_tolerance": 0.1,
    },
    ScenarioType.EXPLAINING: {
        "recommended_traits": [PersonalityTrait.ELABORATE, PersonalityTrait.ANALYTICAL],
        "style": InteractionStyle.MENTOR,
        "pacing": "balanced",
        "digression_tolerance": 0.4,
    },
    ScenarioType.GENERATING: {
        "recommended_traits": [PersonalityTrait.CREATIVE, PersonalityTrait.BOLD, PersonalityTrait.ELABORATE],
        "style": InteractionStyle.CASUAL,
        "pacing": "rapid",
        "digression_tolerance": 0.5,
    },
    ScenarioType.REVIEWING: {
        "recommended_traits": [PersonalityTrait.ANALYTICAL, PersonalityTrait.SERIOUS, PersonalityTrait.CAUTIOUS],
        "style": InteractionStyle.FORMAL,
        "pacing": "methodical",
        "digression_tolerance": 0.1,
    },
    ScenarioType.PLANNING: {
        "recommended_traits": [PersonalityTrait.ANALYTICAL, PersonalityTrait.ELABORATE],
        "style": InteractionStyle.PEER,
        "pacing": "balanced",
        "digression_tolerance": 0.3,
    },
    ScenarioType.TESTING: {
        "recommended_traits": [PersonalityTrait.CAUTIOUS, PersonalityTrait.ANALYTICAL, PersonalityTrait.SERIOUS],
        "style": InteractionStyle.FORMAL,
        "pacing": "methodical",
        "digression_tolerance": 0.1,
    },
}


STYLE_TEMPLATES: Dict[InteractionStyle, Dict[str, str]] = {
    InteractionStyle.FORMAL: {
        "greeting": "I will now assist you with your request.",
        "closing": "Please let me know if any further clarification is needed.",
        "tone": "Professional and precise. Use complete sentences and avoid colloquialisms.",
    },
    InteractionStyle.CASUAL: {
        "greeting": "Hey there! Ready to dive in?",
        "closing": "Catch you on the next one!",
        "tone": "Friendly and approachable. Use contractions and relaxed phrasing.",
    },
    InteractionStyle.MENTOR: {
        "greeting": "Let me walk you through this step by step.",
        "closing": "You've got the foundation now — build on it.",
        "tone": "Educational and supportive. Explain rationale behind decisions.",
    },
    InteractionStyle.PEER: {
        "greeting": "Alright, let's figure this out together.",
        "closing": "Solid work — let's keep iterating.",
        "tone": "Collaborative and direct. Speak as a co-creator, not an authority.",
    },
    InteractionStyle.GAME_DESIGNER: {
        "greeting": "Let's design something players will love.",
        "closing": "Shaping great experiences, one decision at a time.",
        "tone": "Player-centric and enthusiastic. Frame everything in terms of player experience.",
    },
}


class PersonalitySystem:
    """
    Central personality profile engine for SparkLabs agents.

    Manages configurable personality profiles that define agent
    interaction style, decision-making biases, creative output
    parameters, and role-scoped behavior. Supports trait weighting,
    profile blending, scenario-based suggestions, and tone evaluation.

    Usage:
        ps = PersonalitySystem()
        profile = ps.create_profile("Design Mentor", "A creative guide",
                                    [("CREATIVE", 0.8), ("ELABORATE", 0.6)],
                                    archetype=RoleArchetype.LEVEL_DESIGNER)
        prompt_prefix = ps.generate_prompt_prefix(profile.id)
        ps.activate_profile(profile.id, agent_id="agent_001")
    """

    _instance: Optional["PersonalitySystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._profiles: Dict[str, PersonalityProfile] = {}
        self._active_profiles: Dict[str, str] = {}
        self._profile_count: int = 0
        self._clone_count: int = 0
        self._tone_evaluations: int = 0
        self._blend_operations: int = 0
        self._initialize_role_definitions()

    @classmethod
    def get_instance(cls) -> "PersonalitySystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _initialize_role_definitions(self) -> None:
        for archetype, defaults in ARHCETYPE_DEFAULTS.items():
            role = RoleDefinition(
                archetype=archetype,
                title=defaults["title"],
                scope_description=defaults["scope"],
                core_competencies=defaults["competencies"],
                recommended_traits=defaults["traits"],
            )
            self._role_definitions_cache = getattr(self, "_role_definitions_cache", {})
            self._role_definitions_cache[archetype] = role

    def create_profile(
        self,
        name: str,
        description: str,
        traits: List[Tuple[str, float]],
        archetype: RoleArchetype = RoleArchetype.GENERALIST,
        style: InteractionStyle = InteractionStyle.CASUAL,
        tags: Optional[List[str]] = None,
    ) -> PersonalityProfile:
        style_template = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES[InteractionStyle.CASUAL])
        interaction_config = InteractionConfig(
            style=style,
            tone=style_template["tone"],
            greeting_template=style_template["greeting"],
            closing_template=style_template["closing"],
        )

        role_def = self._role_definitions_cache.get(archetype)

        profile = PersonalityProfile(
            name=name,
            description=description,
            interaction_config=interaction_config,
            archetype=archetype,
            role_definition=role_def,
            tags=tags or [],
        )

        for trait_name, weight in traits:
            try:
                trait_enum = PersonalityTrait(trait_name.lower())
                trait_weight = TraitWeight(
                    trait=trait_enum,
                    weight=max(0.0, min(1.0, weight)),
                    justification=f"Assigned for profile '{name}'",
                )
                profile.trait_weights[trait_enum] = trait_weight
            except ValueError:
                continue

        self._profiles[profile.id] = profile
        self._profile_count += 1
        return profile

    def set_trait_weight(
        self,
        profile_id: str,
        trait: str,
        weight: float,
    ) -> Optional[PersonalityProfile]:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None
        try:
            trait_enum = PersonalityTrait(trait.lower())
            existing = profile.trait_weights.get(trait_enum)
            if existing:
                existing.weight = max(0.0, min(1.0, weight))
                existing.justification = f"Updated at {time.time():.0f}"
            else:
                profile.trait_weights[trait_enum] = TraitWeight(
                    trait=trait_enum,
                    weight=max(0.0, min(1.0, weight)),
                )
            profile.updated_at = time.time()
            profile.version += 1
            return profile
        except ValueError:
            return None

    def clone_profile(self, profile_id: str, new_name: str) -> Optional[PersonalityProfile]:
        original = self._profiles.get(profile_id)
        if original is None:
            return None

        import copy
        cloned_weights = {}
        for trait, tw in original.trait_weights.items():
            cloned_weights[trait] = TraitWeight(
                trait=tw.trait,
                weight=tw.weight,
                justification=f"Cloned from '{original.name}'",
            )

        cloned = PersonalityProfile(
            name=new_name,
            description=f"Clone of '{original.name}': {original.description}",
            trait_weights=cloned_weights,
            interaction_config=InteractionConfig(
                style=original.interaction_config.style,
                tone=original.interaction_config.tone,
                pacing=original.interaction_config.pacing,
                technical_depth=original.interaction_config.technical_depth,
                digression_tolerance=original.interaction_config.digression_tolerance,
                greeting_template=original.interaction_config.greeting_template,
                closing_template=original.interaction_config.closing_template,
                max_response_length=original.interaction_config.max_response_length,
            ),
            archetype=original.archetype,
            role_definition=original.role_definition,
            tags=list(original.tags),
            metadata=dict(original.metadata),
        )
        cloned.metadata["cloned_from"] = original.id
        cloned.metadata["cloned_from_name"] = original.name

        self._profiles[cloned.id] = cloned
        self._profile_count += 1
        self._clone_count += 1
        return cloned

    def activate_profile(self, profile_id: str, agent_id: str) -> bool:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return False

        for pid, aid in list(self._active_profiles.items()):
            if aid == agent_id:
                old_profile = self._profiles.get(pid)
                if old_profile:
                    old_profile.is_active = False
                    old_profile.active_for_agent = None

        profile.is_active = True
        profile.active_for_agent = agent_id
        self._active_profiles[profile_id] = agent_id
        return True

    def deactivate_profile(self, agent_id: str) -> bool:
        for pid, aid in list(self._active_profiles.items()):
            if aid == agent_id:
                profile = self._profiles.get(pid)
                if profile:
                    profile.is_active = False
                    profile.active_for_agent = None
                del self._active_profiles[pid]
                return True
        return False

    def get_active_profile(self, agent_id: str) -> Optional[PersonalityProfile]:
        for pid, aid in self._active_profiles.items():
            if aid == agent_id:
                return self._profiles.get(pid)
        return None

    def get_profile(self, profile_id: str) -> Optional[PersonalityProfile]:
        return self._profiles.get(profile_id)

    def find_by_name(self, name: str) -> List[PersonalityProfile]:
        name_lower = name.lower()
        return [p for p in self._profiles.values() if name_lower in p.name.lower()]

    def find_by_archetype(self, archetype: RoleArchetype) -> List[PersonalityProfile]:
        return [p for p in self._profiles.values() if p.archetype == archetype]

    def generate_prompt_prefix(self, profile_id: str) -> str:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return ""

        parts: List[str] = []

        role_def = profile.role_definition
        if role_def:
            parts.append(f"You are a {role_def.title}.")
            parts.append(role_def.scope_description)

        dominant = profile.get_dominant_trait()
        if dominant:
            trait_name, weight = dominant
            parts.append(f"Your dominant trait is {trait_name.value} (weight: {weight:.2f}).")

        trait_lines: List[str] = []
        for trait, tw in sorted(profile.trait_weights.items(), key=lambda x: x[1].weight, reverse=True):
            if tw.weight > 0.3:
                trait_lines.append(f"  {trait.value}: {tw.weight:.2f}")
        if trait_lines:
            parts.append("Trait Profile:\n" + "\n".join(trait_lines))

        ic = profile.interaction_config
        parts.append(f"Interaction Style: {ic.style.value}")
        if ic.tone:
            parts.append(f"Tone Directive: {ic.tone}")
        if ic.pacing:
            parts.append(f"Pacing: {ic.pacing}")

        if role_def and role_def.forbidden_actions:
            parts.append("Forbidden Actions:")
            parts.extend(f"  - {a}" for a in role_def.forbidden_actions)

        return "\n\n".join(parts)

    def blend_profiles(
        self,
        profile_ids: List[str],
        weights: Optional[List[float]] = None,
    ) -> Optional[PersonalityProfile]:
        profiles = [self._profiles.get(pid) for pid in profile_ids]
        valid = [p for p in profiles if p is not None]
        if len(valid) < 2:
            return None

        if weights is None:
            weights = [1.0 / len(valid)] * len(valid)
        elif len(weights) != len(valid):
            return None

        total_weight = sum(weights)
        if total_weight == 0:
            return None
        normalized = [w / total_weight for w in weights]

        blended_weights: Dict[PersonalityTrait, float] = {}
        for profile, nw in zip(valid, normalized):
            for trait in PersonalityTrait:
                tw = profile.trait_weights.get(trait)
                val = tw.weight if tw else 0.0
                blended_weights[trait] = blended_weights.get(trait, 0.0) + val * nw

        style_counts: Dict[InteractionStyle, float] = {}
        for profile, nw in zip(valid, normalized):
            style_counts[profile.interaction_config.style] = (
                style_counts.get(profile.interaction_config.style, 0.0) + nw
            )
        dominant_style = max(style_counts.items(), key=lambda x: x[1])[0]

        names = [p.name for p in valid]
        blend_name = f"Blend of {', '.join(names[:3])}"
        if len(names) > 3:
            blend_name += f" (+{len(names) - 3})"

        weight_tuples: List[Tuple[str, float]] = [
            (t.value, blended_weights[t]) for t in PersonalityTrait
            if blended_weights[t] > 0.01
        ]

        self._blend_operations += 1
        return self.create_profile(
            name=blend_name,
            description=f"Composite profile blending {len(valid)} source profiles.",
            traits=weight_tuples,
            style=dominant_style,
        )

    def suggest_settings(self, scenario: str) -> Dict[str, Any]:
        try:
            scenario_enum = ScenarioType(scenario.lower())
        except ValueError:
            return {"error": f"Unknown scenario: {scenario}"}

        settings = SCENARIO_SETTINGS.get(scenario_enum)
        if settings is None:
            return {"error": f"No settings for scenario: {scenario}"}

        return {
            "scenario": scenario,
            "recommended_traits": [t.value for t in settings["recommended_traits"]],
            "suggested_style": settings["style"].value,
            "suggested_pacing": settings["pacing"],
            "digression_tolerance": settings["digression_tolerance"],
        }

    def evaluate_tone(self, message: str, profile_id: str) -> Dict[str, Any]:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return {"error": f"No profile with id: {profile_id}"}

        message_lower = message.lower()
        self._tone_evaluations += 1

        trait_signals: Dict[str, float] = {}
        signal_keywords = {
            PersonalityTrait.CREATIVE: ["imagine", "create", "novel", "design", "innovative"],
            PersonalityTrait.ANALYTICAL: ["because", "therefore", "analyze", "logic", "data"],
            PersonalityTrait.PLAYFUL: ["fun", "cool", "awesome", "haha", "lol"],
            PersonalityTrait.SERIOUS: ["important", "critical", "must", "require", "essential"],
            PersonalityTrait.CONCISE: [],
            PersonalityTrait.ELABORATE: ["furthermore", "additionally", "specifically", "detailed"],
            PersonalityTrait.CAUTIOUS: ["might", "could", "perhaps", "careful", "risk"],
            PersonalityTrait.BOLD: ["definitely", "absolutely", "must", "will", "certainly"],
        }

        for trait, keywords in signal_keywords.items():
            if not keywords:
                trait_signals[trait.value] = 1.0
                continue
            matches = sum(1 for kw in keywords if kw in message_lower)
            trait_signals[trait.value] = min(1.0, matches / len(keywords))

        word_count = len(message.split())
        brevity_score = 1.0 if word_count < 30 else 0.8 if word_count < 80 else 0.5 if word_count < 200 else 0.2
        trait_signals[PersonalityTrait.CONCISE.value] = brevity_score
        trait_signals[PersonalityTrait.ELABORATE.value] = 1.0 - brevity_score

        alignment_scores: Dict[str, float] = {}
        for trait, tw in profile.trait_weights.items():
            signal = trait_signals.get(trait.value, 0.5)
            alignment = 1.0 - abs(tw.weight - signal)
            alignment_scores[trait.value] = round(alignment, 3)

        overall = sum(alignment_scores.values()) / max(len(alignment_scores), 1)
        dominant_trait_name = profile.get_dominant_trait()
        dominant_signal = trait_signals.get(dominant_trait_name[0].value, 0.0) if dominant_trait_name else 0.0

        return {
            "profile_id": profile_id,
            "profile_name": profile.name,
            "overall_alignment": round(overall, 3),
            "trait_signals": trait_signals,
            "alignment_by_trait": alignment_scores,
            "dominant_trait_signal_match": round(dominant_signal, 3),
            "message_preview": message[:100],
        }

    def export_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None
        return profile.to_dict()

    def import_profile(self, data: Dict[str, Any]) -> Optional[PersonalityProfile]:
        try:
            trait_data = data.get("trait_weights", {})
            traits: List[Tuple[str, float]] = []
            for trait_name, tw_data in trait_data.items():
                if isinstance(tw_data, dict):
                    traits.append((trait_name, tw_data.get("weight", 0.5)))
                else:
                    traits.append((trait_name, float(tw_data)))

            archetype = RoleArchetype.GENERALIST
            try:
                archetype = RoleArchetype(data.get("archetype", "generalist"))
            except ValueError:
                pass

            style = InteractionStyle.CASUAL
            try:
                style = InteractionStyle(data.get("interaction_config", {}).get("style", "casual"))
            except (ValueError, AttributeError):
                pass

            return self.create_profile(
                name=data.get("name", "Imported Profile"),
                description=data.get("description", ""),
                traits=traits,
                archetype=archetype,
                style=style,
                tags=data.get("tags", []),
            )
        except Exception:
            return None

    def list_profiles(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._profiles.values()]

    def delete_profile(self, profile_id: str) -> bool:
        if profile_id in self._profiles:
            self._active_profiles.pop(profile_id, None)
            del self._profiles[profile_id]
            self._profile_count -= 1
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        active_count = len(self._active_profiles)
        archetype_counts: Dict[str, int] = {}
        for p in self._profiles.values():
            key = p.archetype.value
            archetype_counts[key] = archetype_counts.get(key, 0) + 1

        avg_trait_count = (
            sum(len(p.trait_weights) for p in self._profiles.values()) / max(len(self._profiles), 1)
        )

        return {
            "total_profiles": self._profile_count,
            "active_profiles": active_count,
            "clone_count": self._clone_count,
            "blend_operations": self._blend_operations,
            "tone_evaluations": self._tone_evaluations,
            "avg_traits_per_profile": round(avg_trait_count, 1),
            "profiles_by_archetype": archetype_counts,
            "available_archetypes": [a.value for a in RoleArchetype],
            "available_traits": [t.value for t in PersonalityTrait],
            "available_styles": [s.value for s in InteractionStyle],
        }

    def clear(self) -> None:
        self._profiles.clear()
        self._active_profiles.clear()
        self._profile_count = 0
        self._clone_count = 0
        self._tone_evaluations = 0
        self._blend_operations = 0


def get_personality_system() -> PersonalitySystem:
    return PersonalitySystem.get_instance()