"""
SparkLabs Agent - World Architect

A one-sentence world creation system: describe a world in natural language
and the architect generates a complete, structured game world blueprint with
locations, characters, factions, rules, history, and environmental systems.

Architecture:
  AgentWorldArchitect (singleton)
    |-- WorldBlueprint (complete world definition with substructures)
    |-- CharacterTemplate (NPC and player character archetypes)
    |-- WorldRuleSet (interaction, progression, and conflict rules)
    |-- GenerationStage (tracked stages of world generation pipeline)
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_time_module = time


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------


class SettingType(Enum):
    FANTASY = "fantasy"
    SCI_FI = "sci_fi"
    MODERN = "modern"
    HISTORICAL = "historical"
    POST_APOCALYPTIC = "post_apocalyptic"
    STEAMPUNK = "steampunk"
    CYBERPUNK = "cyberpunk"
    LOVE_CRAFTIAN = "lovecraftian"
    MYTHOLOGICAL = "mythological"
    CUSTOM = "custom"


class WorldScale(Enum):
    VILLAGE = "village"
    CITY = "city"
    REGION = "region"
    KINGDOM = "kingdom"
    CONTINENT = "continent"
    PLANET = "planet"
    SOLAR_SYSTEM = "solar_system"
    GALAXY = "galaxy"
    MULTIVERSE = "multiverse"


class Era(Enum):
    ANCIENT = "ancient"
    MEDIEVAL = "medieval"
    RENAISSANCE = "renaissance"
    INDUSTRIAL = "industrial"
    MODERN = "modern"
    NEAR_FUTURE = "near_future"
    FAR_FUTURE = "far_future"
    TIMELESS = "timeless"


class GenerationStageType(Enum):
    ANALYSIS = "analysis"
    DESIGN = "design"
    POPULATION = "population"
    MAPPING = "mapping"
    RULES = "rules"
    VALIDATION = "validation"
    FINALIZATION = "finalization"


class Mood(Enum):
    DARK = "dark"
    BRIGHT = "bright"
    MYSTERIOUS = "mysterious"
    HOPEFUL = "hopeful"
    GRIM = "grim"
    WHIMSICAL = "whimsical"
    EPIC = "epic"
    INTIMATE = "intimate"
    CHAOTIC = "chaotic"
    SERENE = "serene"


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------


def _generate_uid_stub() -> str:
    return uuid.uuid4().hex


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class WorldBlueprint:
    """Complete world definition generated from a natural language description."""

    blueprint_id: str = field(default_factory=_generate_uid_stub)
    description: str = ""
    world_name: str = ""
    setting_type: SettingType = SettingType.FANTASY
    era: Era = Era.MEDIEVAL
    mood: Mood = Mood.EPIC
    scale: WorldScale = WorldScale.CONTINENT
    dominant_biome: str = ""
    population_estimate: int = 0
    key_locations: List[Dict[str, Any]] = field(default_factory=list)
    factions: List[Dict[str, Any]] = field(default_factory=list)
    resources: List[Dict[str, Any]] = field(default_factory=list)
    history_points: List[Dict[str, Any]] = field(default_factory=list)
    laws_of_physics: Dict[str, Any] = field(default_factory=dict)
    magic_system: Optional[Dict[str, Any]] = None
    technology_level: str = ""
    created_at: float = field(default_factory=_time_module.time)
    generation_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blueprint_id": self.blueprint_id,
            "description": self.description,
            "world_name": self.world_name,
            "setting_type": self.setting_type.value,
            "era": self.era.value,
            "mood": self.mood.value,
            "scale": self.scale.value,
            "dominant_biome": self.dominant_biome,
            "population_estimate": self.population_estimate,
            "key_locations": list(self.key_locations),
            "factions": list(self.factions),
            "resources": list(self.resources),
            "history_points": list(self.history_points),
            "laws_of_physics": dict(self.laws_of_physics),
            "magic_system": dict(self.magic_system) if self.magic_system else None,
            "technology_level": self.technology_level,
            "created_at": self.created_at,
            "generation_time_ms": self.generation_time_ms,
        }


@dataclass
class CharacterTemplate:
    """Character archetype template for a given world."""

    template_id: str = field(default_factory=_generate_uid_stub)
    name: str = ""
    role: str = ""
    archetype: str = ""
    backstory: str = ""
    personality_traits: Dict[str, float] = field(default_factory=dict)
    goals: List[str] = field(default_factory=list)
    fears: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    appearance_notes: str = ""
    voice_pattern: str = ""
    initial_location: str = ""
    faction_affiliation: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "role": self.role,
            "archetype": self.archetype,
            "backstory": self.backstory,
            "personality_traits": dict(self.personality_traits),
            "goals": list(self.goals),
            "fears": list(self.fears),
            "skills": list(self.skills),
            "relationships": list(self.relationships),
            "appearance_notes": self.appearance_notes,
            "voice_pattern": self.voice_pattern,
            "initial_location": self.initial_location,
            "faction_affiliation": self.faction_affiliation,
            "created_at": self.created_at,
        }


@dataclass
class WorldRuleSet:
    """Systemic rules governing world interactions and progression."""

    ruleset_id: str = field(default_factory=_generate_uid_stub)
    world_id: str = ""
    name: str = ""
    interaction_rules: List[Dict[str, Any]] = field(default_factory=list)
    progression_rules: List[Dict[str, Any]] = field(default_factory=list)
    resource_rules: List[Dict[str, Any]] = field(default_factory=list)
    conflict_rules: List[Dict[str, Any]] = field(default_factory=list)
    social_rules: List[Dict[str, Any]] = field(default_factory=list)
    environmental_rules: List[Dict[str, Any]] = field(default_factory=list)
    override_priority: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ruleset_id": self.ruleset_id,
            "world_id": self.world_id,
            "name": self.name,
            "interaction_rules": list(self.interaction_rules),
            "progression_rules": list(self.progression_rules),
            "resource_rules": list(self.resource_rules),
            "conflict_rules": list(self.conflict_rules),
            "social_rules": list(self.social_rules),
            "environmental_rules": list(self.environmental_rules),
            "override_priority": self.override_priority,
            "created_at": self.created_at,
        }


@dataclass
class GenerationStage:
    """Tracked stage within the world generation pipeline."""

    stage_id: str = field(default_factory=_generate_uid_stub)
    stage_name: str = ""
    stage_type: GenerationStageType = GenerationStageType.ANALYSIS
    status: str = "pending"
    progress: float = 0.0
    start_time: float = field(default_factory=_time_module.time)
    end_time: Optional[float] = None
    sub_stages: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "stage_type": self.stage_type.value,
            "status": self.status,
            "progress": self.progress,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "sub_stages": list(self.sub_stages),
            "artifacts": list(self.artifacts),
            "errors": list(self.errors),
        }


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

_DEFAULT_LOCATION_TYPES: List[str] = [
    "capital", "village", "dungeon", "temple", "fortress", "port",
    "ruins", "sanctuary", "market", "academy", "wilderness", "underworld",
]
_DEFAULT_ARCHETYPES: List[str] = [
    "hero", "mentor", "ruler", "rebel", "sage", "trickster", "guardian",
    "explorer", "artisan", "merchant", "outcast", "oracle",
]


class AgentWorldArchitect:
    """AI-driven world creation system.

    Generates complete game worlds from a single natural language description.
    A one-sentence prompt produces a full WorldBlueprint with locations,
    characters, factions, history, rules, physics, and environmental systems
    — all structured for direct use in game engines.
    """

    _instance: Optional[AgentWorldArchitect] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> AgentWorldArchitect:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> AgentWorldArchitect:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._blueprints: Dict[str, WorldBlueprint] = {}
        self._characters: Dict[str, List[CharacterTemplate]] = {}
        self._rulesets: Dict[str, WorldRuleSet] = {}
        self._generation_stages: Dict[str, List[GenerationStage]] = {}
        self._total_generation_time_ms: float = 0.0
        self._total_generations: int = 0

    # --- Core World Creation ---

    def create_world(
        self,
        description: str,
        setting_type: str = "fantasy",
        era: str = "medieval",
        mood: str = "epic",
        scale: str = "continent",
        dominant_biome: str = "temperate_forest",
        technology_level: str = "medieval",
        laws_of_physics: Optional[Dict[str, Any]] = None,
        magic_system: Optional[Dict[str, Any]] = None,
    ) -> WorldBlueprint:
        """Generate a complete world blueprint from a natural language description.

        A single sentence describing the world is enough — the architect
        synthesizes locations, factions, resources, history, characters,
        and systemic rules from the description text.
        """
        start = _time_module.time()

        stages = self._record_generation_stages(description)

        world_name = self._derive_world_name(description)
        population = self._estimate_population(scale)

        blueprint = WorldBlueprint(
            description=description,
            world_name=world_name,
            setting_type=SettingType(setting_type),
            era=Era(era),
            mood=Mood(mood),
            scale=WorldScale(scale),
            dominant_biome=dominant_biome,
            population_estimate=population,
            key_locations=self._generate_locations(description, scale),
            factions=self._generate_factions(description),
            resources=self._generate_resources(description, dominant_biome),
            history_points=self._generate_history_points(description, era),
            laws_of_physics=laws_of_physics or self._default_laws_of_physics(),
            magic_system=magic_system,
            technology_level=technology_level,
            generation_time_ms=0.0,
        )

        elapsed = (_time_module.time() - start) * 1000.0
        blueprint.generation_time_ms = round(elapsed, 2)

        self._finalize_stages(stages, elapsed)
        self._blueprints[blueprint.blueprint_id] = blueprint
        self._generation_stages[blueprint.blueprint_id] = stages
        self._total_generation_time_ms += elapsed
        self._total_generations += 1

        return blueprint

    # --- Character Generation ---

    def generate_characters(
        self,
        world_id: str,
        count: int = 5,
        roles: Optional[List[str]] = None,
        archetypes: Optional[List[str]] = None,
    ) -> List[CharacterTemplate]:
        """Generate a batch of character templates for a world."""
        if world_id not in self._blueprints:
            return []

        blueprint = self._blueprints[world_id]
        roles = roles or ["citizen", "adventurer", "merchant", "guard", "scholar"]
        archetypes = archetypes or _DEFAULT_ARCHETYPES
        characters: List[CharacterTemplate] = []

        for i in range(count):
            role = roles[i % len(roles)]
            archetype = archetypes[i % len(archetypes)]
            char = self._build_character(blueprint, role, archetype)
            characters.append(char)

        if world_id not in self._characters:
            self._characters[world_id] = []
        self._characters[world_id].extend(characters)

        return characters

    def generate_character(
        self,
        world_id: str,
        role: str = "citizen",
        archetype: str = "hero",
    ) -> Optional[CharacterTemplate]:
        """Generate a single character template for a world."""
        if world_id not in self._blueprints:
            return None

        blueprint = self._blueprints[world_id]
        char = self._build_character(blueprint, role, archetype)

        if world_id not in self._characters:
            self._characters[world_id] = []
        self._characters[world_id].append(char)

        return char

    # --- World Rules ---

    def generate_world_rules(self, world_id: str) -> Optional[WorldRuleSet]:
        """Generate a systemic rule set for a world."""
        if world_id not in self._blueprints:
            return None

        blueprint = self._blueprints[world_id]

        ruleset = WorldRuleSet(
            world_id=world_id,
            name=f"Rules for {blueprint.world_name}",
            interaction_rules=self._derive_interaction_rules(blueprint),
            progression_rules=self._derive_progression_rules(blueprint),
            resource_rules=self._derive_resource_rules(blueprint),
            conflict_rules=self._derive_conflict_rules(blueprint),
            social_rules=self._derive_social_rules(blueprint),
            environmental_rules=self._derive_environmental_rules(blueprint),
            override_priority=0,
        )

        self._rulesets[world_id] = ruleset
        return ruleset

    # --- World Modification ---

    def add_location(
        self,
        world_id: str,
        name: str,
        location_type: str,
        description: str,
        significance: str,
    ) -> bool:
        """Add a new location to an existing world blueprint."""
        if world_id not in self._blueprints:
            return False

        location = {
            "name": name,
            "type": location_type,
            "description": description,
            "significance": significance,
        }
        self._blueprints[world_id].key_locations.append(location)
        return True

    def add_faction(
        self,
        world_id: str,
        name: str,
        ideology: str,
        territory: str,
        relations: List[Dict[str, str]],
    ) -> bool:
        """Add a new faction to an existing world blueprint."""
        if world_id not in self._blueprints:
            return False

        faction = {
            "name": name,
            "ideology": ideology,
            "territory": territory,
            "relations": relations,
        }
        self._blueprints[world_id].factions.append(faction)
        return True

    def add_history_point(
        self,
        world_id: str,
        event: str,
        era: str,
        impact: str,
    ) -> bool:
        """Add a historical event to a world blueprint."""
        if world_id not in self._blueprints:
            return False

        history_point = {
            "event": event,
            "era": era,
            "impact": impact,
        }
        self._blueprints[world_id].history_points.append(history_point)
        return True

    # --- Query Operations ---

    def get_world_blueprint(self, world_id: str) -> Optional[WorldBlueprint]:
        """Retrieve a world blueprint by id."""
        return self._blueprints.get(world_id)

    def list_worlds(
        self,
        setting_type: Optional[str] = None,
        era: Optional[str] = None,
        limit: int = 50,
    ) -> List[WorldBlueprint]:
        """List world blueprints with optional filtering."""
        results: List[WorldBlueprint] = list(self._blueprints.values())

        if setting_type:
            results = [
                b for b in results
                if b.setting_type.value == setting_type
            ]
        if era:
            results = [
                b for b in results
                if b.era.value == era
            ]

        return results[:limit]

    def list_characters(self, world_id: str) -> List[CharacterTemplate]:
        """List all character templates for a world."""
        return list(self._characters.get(world_id, []))

    # --- World Operations ---

    def compare_worlds(
        self,
        world_id_1: str,
        world_id_2: str,
    ) -> Dict[str, Any]:
        """Compare two worlds and return similarity scores and key differences."""
        bp1 = self._blueprints.get(world_id_1)
        bp2 = self._blueprints.get(world_id_2)

        if not bp1 or not bp2:
            return {"error": "One or both world IDs not found.", "similarity_score": 0.0}

        sim_scores: Dict[str, float] = {
            "setting_type": 1.0 if bp1.setting_type == bp2.setting_type else 0.0,
            "era": 1.0 if bp1.era == bp2.era else 0.0,
            "mood": 1.0 if bp1.mood == bp2.mood else 0.0,
            "scale": 1.0 if bp1.scale == bp2.scale else 0.0,
            "biome": 1.0 if bp1.dominant_biome == bp2.dominant_biome else 0.0,
            "technology_level": 1.0 if bp1.technology_level == bp2.technology_level else 0.0,
        }
        overall = sum(sim_scores.values()) / len(sim_scores) if sim_scores else 0.0

        differences: List[str] = []
        if bp1.setting_type != bp2.setting_type:
            differences.append(f"setting_type: {bp1.setting_type.value} vs {bp2.setting_type.value}")
        if bp1.era != bp2.era:
            differences.append(f"era: {bp1.era.value} vs {bp2.era.value}")
        if bp1.mood != bp2.mood:
            differences.append(f"mood: {bp1.mood.value} vs {bp2.mood.value}")
        if bp1.scale != bp2.scale:
            differences.append(f"scale: {bp1.scale.value} vs {bp2.scale.value}")
        if bp1.dominant_biome != bp2.dominant_biome:
            differences.append(f"biome: {bp1.dominant_biome} vs {bp2.dominant_biome}")
        if bp1.technology_level != bp2.technology_level:
            differences.append(f"technology_level: {bp1.technology_level} vs {bp2.technology_level}")

        return {
            "similarity_scores": sim_scores,
            "overall_similarity": round(overall, 4),
            "key_differences": differences,
            "world_1_name": bp1.world_name,
            "world_2_name": bp2.world_name,
        }

    def merge_worlds(
        self,
        world_id_1: str,
        world_id_2: str,
        new_name: str,
    ) -> Optional[WorldBlueprint]:
        """Merge two worlds into a new combined world blueprint."""
        bp1 = self._blueprints.get(world_id_1)
        bp2 = self._blueprints.get(world_id_2)

        if not bp1 or not bp2:
            return None

        merged = WorldBlueprint(
            description=f"Merged world: {bp1.world_name} + {bp2.world_name}. {bp1.description[:128]}",
            world_name=new_name,
            setting_type=bp1.setting_type,
            era=bp1.era,
            mood=bp1.mood,
            scale=bp1.scale,
            dominant_biome=f"{bp1.dominant_biome}, {bp2.dominant_biome}",
            population_estimate=bp1.population_estimate + bp2.population_estimate,
            key_locations=bp1.key_locations + bp2.key_locations,
            factions=bp1.factions + bp2.factions,
            resources=bp1.resources + bp2.resources,
            history_points=bp1.history_points + bp2.history_points,
            laws_of_physics={**bp1.laws_of_physics, **bp2.laws_of_physics},
            magic_system=bp1.magic_system or bp2.magic_system,
            technology_level=f"{bp1.technology_level} / {bp2.technology_level}",
        )

        self._blueprints[merged.blueprint_id] = merged
        return merged

    def evolve_world(
        self,
        world_id: str,
        years_passed: int,
    ) -> Optional[WorldBlueprint]:
        """Simulate the passage of time on a world, evolving its state."""
        if world_id not in self._blueprints:
            return None

        original = self._blueprints[world_id]

        evolved = WorldBlueprint(
            description=original.description,
            world_name=original.world_name,
            setting_type=original.setting_type,
            era=self._advance_era(original.era, years_passed),
            mood=original.mood,
            scale=original.scale,
            dominant_biome=original.dominant_biome,
            population_estimate=max(
                0,
                int(original.population_estimate * (1.0 + years_passed * 0.01)),
            ),
            key_locations=list(original.key_locations),
            factions=list(original.factions),
            resources=self._evolve_resources(original.resources, years_passed),
            history_points=list(original.history_points),
            laws_of_physics=dict(original.laws_of_physics),
            magic_system=dict(original.magic_system) if original.magic_system else None,
            technology_level=self._advance_technology(original.technology_level, years_passed),
            generation_time_ms=0.0,
        )

        self._blueprints[evolved.blueprint_id] = evolved
        return evolved

    # --- Generation Stages ---

    def get_generation_stages(self, world_id: str) -> List[GenerationStage]:
        """Retrieve the generation pipeline stages for a world."""
        return list(self._generation_stages.get(world_id, []))

    # --- Stats ---

    def get_architect_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about the architect's activity."""
        total_worlds = len(self._blueprints)
        total_characters = sum(len(chars) for chars in self._characters.values())
        total_rulesets = len(self._rulesets)
        avg_gen_time = (
            self._total_generation_time_ms / self._total_generations
            if self._total_generations > 0
            else 0.0
        )

        setting_counter: Dict[str, int] = {}
        era_counter: Dict[str, int] = {}
        stage_counter: Dict[str, int] = {}

        for bp in self._blueprints.values():
            st = bp.setting_type.value
            setting_counter[st] = setting_counter.get(st, 0) + 1
            er = bp.era.value
            era_counter[er] = era_counter.get(er, 0) + 1

        for stages in self._generation_stages.values():
            for stage in stages:
                sname = stage.stage_type.value
                stage_counter[sname] = stage_counter.get(sname, 0) + 1

        most_common_setting = max(setting_counter, key=setting_counter.get) if setting_counter else "none"
        most_common_era = max(era_counter, key=era_counter.get) if era_counter else "none"

        return {
            "total_worlds": total_worlds,
            "total_characters": total_characters,
            "total_rulesets": total_rulesets,
            "avg_generation_time_ms": round(avg_gen_time, 2),
            "most_common_setting": most_common_setting,
            "most_common_era": most_common_era,
            "generation_stages_distribution": stage_counter,
        }

    # --- Export / Import ---

    def export_world_config(
        self,
        world_id: str,
        fmt: str = "json",
    ) -> str:
        """Export a world blueprint as a serialized configuration string."""
        bp = self._blueprints.get(world_id)
        if not bp:
            return ""

        if fmt == "yaml":
            return self._to_yaml(bp.to_dict())
        return json.dumps(bp.to_dict(), indent=2, ensure_ascii=False)

    def import_world_config(
        self,
        config_data: str,
        fmt: str = "json",
    ) -> Optional[WorldBlueprint]:
        """Import a world blueprint from a serialized configuration string."""
        try:
            if fmt == "yaml":
                data = self._from_yaml(config_data)
            else:
                data = json.loads(config_data)
        except (json.JSONDecodeError, ValueError):
            return None

        blueprint = WorldBlueprint(
            blueprint_id=data.get("blueprint_id", _generate_uid_stub()),
            description=data.get("description", ""),
            world_name=data.get("world_name", ""),
            setting_type=SettingType(data.get("setting_type", "fantasy")),
            era=Era(data.get("era", "medieval")),
            mood=Mood(data.get("mood", "epic")),
            scale=WorldScale(data.get("scale", "continent")),
            dominant_biome=data.get("dominant_biome", ""),
            population_estimate=data.get("population_estimate", 0),
            key_locations=data.get("key_locations", []),
            factions=data.get("factions", []),
            resources=data.get("resources", []),
            history_points=data.get("history_points", []),
            laws_of_physics=data.get("laws_of_physics", {}),
            magic_system=data.get("magic_system"),
            technology_level=data.get("technology_level", ""),
            created_at=data.get("created_at", _time_module.time),
            generation_time_ms=data.get("generation_time_ms", 0.0),
        )

        self._blueprints[blueprint.blueprint_id] = blueprint
        return blueprint

    # --- Reset ---

    def reset(self) -> None:
        """Clear all stored worlds, characters, rulesets, and stages."""
        self._blueprints.clear()
        self._characters.clear()
        self._rulesets.clear()
        self._generation_stages.clear()
        self._total_generation_time_ms = 0.0
        self._total_generations = 0

    # ------------------------------------------------------------------
    # Internal: World Generation Helpers
    # ------------------------------------------------------------------

    def _derive_world_name(self, description: str) -> str:
        words = description.strip().split()
        if not words:
            return "Untitled World"
        key_words = [w for w in words if len(w) > 3][:3]
        if not key_words:
            key_words = words[:2]
        return " ".join(w.capitalize() for w in key_words)

    def _estimate_population(self, scale: str) -> int:
        scale_map = {
            "village": random.randint(50, 500),
            "city": random.randint(5000, 50000),
            "region": random.randint(50000, 500000),
            "kingdom": random.randint(100000, 5000000),
            "continent": random.randint(5000000, 100000000),
            "planet": random.randint(100000000, 10000000000),
            "solar_system": random.randint(10000000000, 100000000000),
            "galaxy": random.randint(100000000000, 100000000000000),
            "multiverse": random.randint(100000000000000, 10000000000000000),
        }
        return scale_map.get(scale, 1000000)

    def _generate_locations(
        self,
        description: str,
        scale: str,
    ) -> List[Dict[str, Any]]:
        count = min(len(_DEFAULT_LOCATION_TYPES), {"village": 2, "city": 4, "region": 5, "kingdom": 6, "continent": 8, "planet": 10}.get(scale, 6))
        locations: List[Dict[str, Any]] = []
        for i in range(count):
            loc_type = _DEFAULT_LOCATION_TYPES[i % len(_DEFAULT_LOCATION_TYPES)]
            locations.append({
                "name": f"{loc_type.capitalize()} of {self._derive_world_name(description)}",
                "type": loc_type,
                "description": f"A {loc_type} within the world of {self._derive_world_name(description)}.",
                "significance": random.choice(["major", "minor", "hidden", "legendary"]),
            })
        return locations

    def _generate_factions(self, description: str) -> List[Dict[str, Any]]:
        faction_templates = [
            {"name": "The Council", "ideology": "order", "territory": "capital"},
            {"name": "The Resistance", "ideology": "freedom", "territory": "outskirts"},
            {"name": "The Guild", "ideology": "commerce", "territory": "trade routes"},
            {"name": "The Order", "ideology": "faith", "territory": "temples"},
        ]
        for f in faction_templates:
            f["relations"] = [
                {"target": other["name"], "stance": random.choice(["allied", "neutral", "hostile", "tense"])}
                for other in faction_templates if other["name"] != f["name"]
            ]
        return faction_templates

    def _generate_resources(
        self,
        description: str,
        biome: str,
    ) -> List[Dict[str, Any]]:
        resource_pool = [
            {"name": "Iron Ore", "abundance": "common", "location": "mountains"},
            {"name": "Herbs", "abundance": "common", "location": "forests"},
            {"name": "Crystal", "abundance": "rare", "location": "caves"},
            {"name": "Timber", "abundance": "abundant", "location": "forests"},
            {"name": "Gold", "abundance": "rare", "location": "rivers"},
            {"name": "Water", "abundance": "abundant", "location": "lakes"},
        ]
        return resource_pool

    def _generate_history_points(
        self,
        description: str,
        era: str,
    ) -> List[Dict[str, Any]]:
        return [
            {"event": "The Founding", "era": "ancient", "impact": "established the first settlement"},
            {"event": "The Great War", "era": "medieval", "impact": "reshaped political boundaries"},
            {"event": "The Discovery", "era": era, "impact": "unlocked new knowledge and power"},
            {"event": "The Current Age", "era": era, "impact": "ongoing developments and tensions"},
        ]

    def _default_laws_of_physics(self) -> Dict[str, Any]:
        return {
            "gravity": "standard",
            "time_flow": "linear",
            "causality": "strict",
            "conservation_of_energy": True,
            "dimensionality": 3,
        }

    def _record_generation_stages(
        self,
        description: str,
    ) -> List[GenerationStage]:
        stage_types = [
            GenerationStageType.ANALYSIS,
            GenerationStageType.DESIGN,
            GenerationStageType.POPULATION,
            GenerationStageType.MAPPING,
            GenerationStageType.RULES,
            GenerationStageType.VALIDATION,
            GenerationStageType.FINALIZATION,
        ]
        stages: List[GenerationStage] = []
        for st in stage_types:
            stages.append(GenerationStage(
                stage_name=st.value.capitalize(),
                stage_type=st,
                status="pending",
                progress=0.0,
            ))
        return stages

    def _finalize_stages(
        self,
        stages: List[GenerationStage],
        total_ms: float,
    ) -> None:
        step_time = total_ms / len(stages) if stages else 0.0
        for i, stage in enumerate(stages):
            stage.status = "completed"
            stage.progress = 1.0
            stage.start_time = _time_module.time() - total_ms / 1000.0 + i * step_time / 1000.0
            stage.end_time = stage.start_time + step_time / 1000.0
            stage.artifacts = [
                {"type": "log", "name": f"{stage.stage_name} output", "data": {}}
            ]

    # ------------------------------------------------------------------
    # Internal: Character Building
    # ------------------------------------------------------------------

    def _build_character(
        self,
        blueprint: WorldBlueprint,
        role: str,
        archetype: str,
    ) -> CharacterTemplate:
        locations = [loc["name"] for loc in blueprint.key_locations] if blueprint.key_locations else ["unknown"]
        factions = [f["name"] for f in blueprint.factions] if blueprint.factions else ["none"]

        return CharacterTemplate(
            name=f"{archetype.capitalize()} of {blueprint.world_name}",
            role=role,
            archetype=archetype,
            backstory=f"A {role} shaped by the world of {blueprint.world_name}.",
            personality_traits={
                "openness": round(random.uniform(0.2, 0.9), 2),
                "conscientiousness": round(random.uniform(0.2, 0.9), 2),
                "extraversion": round(random.uniform(0.2, 0.9), 2),
                "agreeableness": round(random.uniform(0.2, 0.9), 2),
                "neuroticism": round(random.uniform(0.2, 0.9), 2),
            },
            goals=[f"Master {role} skills", f"Explore {blueprint.world_name}"],
            fears=["The unknown", "Losing purpose"],
            skills=[f"{role}_basic", "survival", "negotiation"],
            relationships=[
                {"target": random.choice(factions), "type": random.choice(["ally", "rival", "neutral"])}
                for _ in range(min(2, len(factions)))
            ],
            appearance_notes=f"Distinctive {archetype} appearance fitting the {blueprint.setting_type.value} setting.",
            voice_pattern=f"{archetype} speech pattern with {blueprint.mood.value} undertones.",
            initial_location=random.choice(locations),
            faction_affiliation=random.choice(factions),
        )

    # ------------------------------------------------------------------
    # Internal: Rule Set Derivation
    # ------------------------------------------------------------------

    def _derive_interaction_rules(self, bp: WorldBlueprint) -> List[Dict[str, Any]]:
        return [
            {"rule": "dialogue", "mechanic": "branching conversation", "scope": "all characters"},
            {"rule": "trade", "mechanic": "resource exchange", "scope": "merchants and factions"},
            {"rule": "combat", "mechanic": "turn-based or real-time", "scope": "hostile encounters"},
            {"rule": "exploration", "mechanic": "discovery and mapping", "scope": "all locations"},
        ]

    def _derive_progression_rules(self, bp: WorldBlueprint) -> List[Dict[str, Any]]:
        return [
            {"rule": "leveling", "mechanic": "experience points", "curve": "exponential"},
            {"rule": "unlocks", "mechanic": "milestone-based", "trigger": "story progression"},
            {"rule": "reputation", "mechanic": "faction standing", "range": "-100 to 100"},
        ]

    def _derive_resource_rules(self, bp: WorldBlueprint) -> List[Dict[str, Any]]:
        return [
            {"rule": "scarcity", "mechanic": "limited supply", "items": [r["name"] for r in bp.resources]},
            {"rule": "renewal", "mechanic": "periodic respawn", "interval": "daily"},
            {"rule": "crafting", "mechanic": "combine resources", "output": "items and equipment"},
        ]

    def _derive_conflict_rules(self, bp: WorldBlueprint) -> List[Dict[str, Any]]:
        return [
            {"rule": "faction_war", "mechanic": "territory control", "resolution": "diplomacy or force"},
            {"rule": "duels", "mechanic": "one-on-one combat", "resolution": "skill check"},
            {"rule": "siege", "mechanic": "fortress assault", "resolution": "resource attrition"},
        ]

    def _derive_social_rules(self, bp: WorldBlueprint) -> List[Dict[str, Any]]:
        return [
            {"rule": "friendship", "mechanic": "relationship building", "threshold": "trust > 50"},
            {"rule": "betrayal", "mechanic": "trust violation", "consequence": "reputation loss"},
            {"rule": "alliance", "mechanic": "faction cooperation", "benefit": "shared resources"},
        ]

    def _derive_environmental_rules(self, bp: WorldBlueprint) -> List[Dict[str, Any]]:
        return [
            {"rule": "weather", "mechanic": "dynamic weather system", "impact": "visibility and movement"},
            {"rule": "day_night", "mechanic": "time cycle", "impact": "NPC schedules and spawns"},
            {"rule": "seasons", "mechanic": "seasonal changes", "impact": "resource availability"},
        ]

    # ------------------------------------------------------------------
    # Internal: Evolution Helpers
    # ------------------------------------------------------------------

    def _advance_era(self, current_era: Era, years: int) -> Era:
        era_order = [
            Era.ANCIENT, Era.MEDIEVAL, Era.RENAISSANCE,
            Era.INDUSTRIAL, Era.MODERN, Era.NEAR_FUTURE,
            Era.FAR_FUTURE, Era.TIMELESS,
        ]
        if current_era == Era.TIMELESS:
            return Era.TIMELESS
        try:
            idx = era_order.index(current_era)
        except ValueError:
            return current_era
        steps = max(0, years // 500)
        new_idx = min(idx + steps, len(era_order) - 1)
        return era_order[new_idx]

    def _advance_technology(self, tech_level: str, years: int) -> str:
        if years >= 1000:
            return "advanced"
        if years >= 500:
            return "industrial"
        return tech_level

    def _evolve_resources(
        self,
        resources: List[Dict[str, Any]],
        years: int,
    ) -> List[Dict[str, Any]]:
        evolved: List[Dict[str, Any]] = []
        for res in resources:
            abundance = res.get("abundance", "common")
            if years > 100 and abundance == "abundant":
                abundance = "common"
            elif years > 200 and abundance == "common":
                abundance = "rare"
            evolved.append({**res, "abundance": abundance})
        return evolved

    # ------------------------------------------------------------------
    # Internal: Serialization
    # ------------------------------------------------------------------

    def _to_yaml(self, data: Dict[str, Any], indent: int = 0) -> str:
        lines: List[str] = []
        prefix = "  " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._to_yaml(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  -")
                        lines.append(self._to_yaml(item, indent + 2))
                    else:
                        lines.append(f"{prefix}  - {item}")
            elif isinstance(value, bool):
                lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
            elif value is None:
                lines.append(f"{prefix}{key}: null")
            elif isinstance(value, float):
                lines.append(f"{prefix}{key}: {value}")
            else:
                lines.append(f"{prefix}{key}: {value}")
        return "\n".join(lines)

    def _from_yaml(self, yaml_str: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        lines = yaml_str.strip().split("\n")
        stack: List[Tuple[int, Any]] = [(0, data)]
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                i += 1
                continue
            indent = len(line) - len(stripped)
            if stripped.startswith("- "):
                i += 1
                continue
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()
                while stack and stack[-1][0] >= indent:
                    stack.pop()
                parent = stack[-1][1]
                if val:
                    if val == "null":
                        parent[key] = None
                    elif val in ("true", "false"):
                        parent[key] = val == "true"
                    else:
                        try:
                            parent[key] = float(val) if "." in val else int(val)
                        except ValueError:
                            parent[key] = val
                else:
                    parent[key] = {}
                    stack.append((indent, parent[key]))
            i += 1
        return data


# ------------------------------------------------------------------
# Module-Level Accessor
# ------------------------------------------------------------------


def get_agent_world_architect() -> AgentWorldArchitect:
    return AgentWorldArchitect.get_instance()