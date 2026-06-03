"""
SparkLabs Agent - Skill Generator

AI-driven autonomous skill generation system for the SparkLabs AI-native
game engine. Generates complete skill definitions with parameters, dependencies,
compositions, and evolution pathways. Produces skill trees, decomposes complex
skills, adapts existing skills to new contexts, and evaluates skill viability
across diverse game design scenarios.

Architecture:
  AgentSkillGenerator (Singleton)
    |-- Skill Synthesizer (generate novel skills from game context)
    |-- Template Engine (create reusable skill blueprints)
    |-- Composition Engine (merge component skills into compound skills)
    |-- Decomposition Engine (break complex skills into sub-skills)
    |-- Evaluation Engine (score skill viability and synergy)
    |-- Adaptation Engine (evolve skills for new contexts)
    |-- Skill Tree Generator (hierarchical skill progression graphs)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SkillCategory(Enum):
    COMBAT = "combat"
    CRAFTING = "crafting"
    SOCIAL = "social"
    EXPLORATION = "exploration"
    STEALTH = "stealth"
    MAGIC = "magic"
    TECHNOLOGY = "technology"
    SURVIVAL = "survival"
    LEADERSHIP = "leadership"
    DIPLOMACY = "diplomacy"


class ComplexityLevel(Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"
    LEGENDARY = "legendary"


SKILL_CATEGORY_POOL: List[SkillCategory] = [
    SkillCategory.COMBAT,
    SkillCategory.CRAFTING,
    SkillCategory.SOCIAL,
    SkillCategory.EXPLORATION,
    SkillCategory.STEALTH,
    SkillCategory.MAGIC,
    SkillCategory.TECHNOLOGY,
    SkillCategory.SURVIVAL,
    SkillCategory.LEADERSHIP,
    SkillCategory.DIPLOMACY,
]

COMPLEXITY_WEIGHTS: Dict[ComplexityLevel, Dict[str, Any]] = {
    ComplexityLevel.BASIC: {
        "param_count_range": (1, 3),
        "prerequisite_count": 0,
        "confidence_base": 0.90,
        "training_data_factor": 1.0,
        "synergy_factor": 0.1,
    },
    ComplexityLevel.INTERMEDIATE: {
        "param_count_range": (2, 5),
        "prerequisite_count": 1,
        "confidence_base": 0.80,
        "training_data_factor": 2.0,
        "synergy_factor": 0.2,
    },
    ComplexityLevel.ADVANCED: {
        "param_count_range": (3, 7),
        "prerequisite_count": 2,
        "confidence_base": 0.70,
        "training_data_factor": 3.0,
        "synergy_factor": 0.3,
    },
    ComplexityLevel.EXPERT: {
        "param_count_range": (4, 9),
        "prerequisite_count": 3,
        "confidence_base": 0.60,
        "training_data_factor": 4.5,
        "synergy_factor": 0.4,
    },
    ComplexityLevel.MASTER: {
        "param_count_range": (5, 12),
        "prerequisite_count": 4,
        "confidence_base": 0.50,
        "training_data_factor": 6.0,
        "synergy_factor": 0.5,
    },
    ComplexityLevel.LEGENDARY: {
        "param_count_range": (6, 15),
        "prerequisite_count": 5,
        "confidence_base": 0.40,
        "training_data_factor": 8.0,
        "synergy_factor": 0.6,
    },
}

CATEGORY_SYNERGY_MATRIX: Dict[SkillCategory, Dict[SkillCategory, float]] = {
    SkillCategory.COMBAT: {
        SkillCategory.STEALTH: 0.6,
        SkillCategory.SURVIVAL: 0.5,
        SkillCategory.MAGIC: 0.7,
        SkillCategory.TECHNOLOGY: 0.55,
        SkillCategory.LEADERSHIP: 0.4,
    },
    SkillCategory.CRAFTING: {
        SkillCategory.TECHNOLOGY: 0.75,
        SkillCategory.SURVIVAL: 0.6,
        SkillCategory.EXPLORATION: 0.45,
        SkillCategory.MAGIC: 0.4,
    },
    SkillCategory.SOCIAL: {
        SkillCategory.DIPLOMACY: 0.85,
        SkillCategory.LEADERSHIP: 0.75,
        SkillCategory.STEALTH: 0.3,
    },
    SkillCategory.EXPLORATION: {
        SkillCategory.SURVIVAL: 0.7,
        SkillCategory.STEALTH: 0.5,
        SkillCategory.CRAFTING: 0.45,
        SkillCategory.MAGIC: 0.35,
    },
    SkillCategory.STEALTH: {
        SkillCategory.COMBAT: 0.6,
        SkillCategory.EXPLORATION: 0.5,
        SkillCategory.SOCIAL: 0.3,
    },
    SkillCategory.MAGIC: {
        SkillCategory.COMBAT: 0.7,
        SkillCategory.CRAFTING: 0.4,
        SkillCategory.EXPLORATION: 0.35,
        SkillCategory.LEADERSHIP: 0.3,
    },
    SkillCategory.TECHNOLOGY: {
        SkillCategory.CRAFTING: 0.75,
        SkillCategory.COMBAT: 0.55,
        SkillCategory.SURVIVAL: 0.5,
        SkillCategory.EXPLORATION: 0.4,
    },
    SkillCategory.SURVIVAL: {
        SkillCategory.EXPLORATION: 0.7,
        SkillCategory.CRAFTING: 0.6,
        SkillCategory.COMBAT: 0.5,
        SkillCategory.STEALTH: 0.35,
    },
    SkillCategory.LEADERSHIP: {
        SkillCategory.SOCIAL: 0.75,
        SkillCategory.DIPLOMACY: 0.7,
        SkillCategory.COMBAT: 0.4,
        SkillCategory.MAGIC: 0.3,
    },
    SkillCategory.DIPLOMACY: {
        SkillCategory.SOCIAL: 0.85,
        SkillCategory.LEADERSHIP: 0.7,
        SkillCategory.STEALTH: 0.25,
    },
}

PREREQUISITE_POOL: Dict[SkillCategory, List[str]] = {
    SkillCategory.COMBAT: [
        "strength_training", "weapon_familiarity", "stamina_conditioning",
        "tactical_awareness", "reflex_honing", "combat_stance",
        "armor_proficiency", "shield_basics", "dual_wielding",
    ],
    SkillCategory.CRAFTING: [
        "material_knowledge", "tool_mastery", "workshop_setup",
        "blueprint_reading", "quality_inspection", "resource_gathering",
        "precision_work", "design_theory", "smithing_basics",
    ],
    SkillCategory.SOCIAL: [
        "charisma_training", "etiquette_knowledge", "negotiation_basics",
        "persuasion_techniques", "crowd_reading", "storytelling",
        "empathy_development", "networking", "conflict_mediation",
    ],
    SkillCategory.EXPLORATION: [
        "navigation_basics", "survival_training", "climbing_proficiency",
        "swimming_capability", "tracking_skills", "map_reading",
        "terrain_assessment", "weather_prediction", "foraging",
    ],
    SkillCategory.STEALTH: [
        "silent_movement", "shadow_blending", "camouflage_techniques",
        "lock_picking", "trap_disarming", "pickpocketing",
        "disguise_arts", "eavesdropping", "concealment",
    ],
    SkillCategory.MAGIC: [
        "mana_control", "spell_theory", "ritual_casting",
        "elemental_affinity", "rune_inscription", "arcane_meditation",
        "enchanting_basics", "conjuration_fundamentals", "warding",
    ],
    SkillCategory.TECHNOLOGY: [
        "engineering_math", "circuit_theory", "mechanical_aptitude",
        "coding_basics", "robotics_foundations", "systems_design",
        "hacking_introduction", "cybernetics_theory", "energy_management",
    ],
    SkillCategory.SURVIVAL: [
        "fire_starting", "shelter_building", "water_purification",
        "food_preservation", "first_aid", "weather_resistance",
        "hunting_basics", "trapping", "wildcraft_identification",
    ],
    SkillCategory.LEADERSHIP: [
        "team_management", "strategic_planning", "delegation_skills",
        "motivation_techniques", "crisis_management", "vision_casting",
        "mentorship", "resource_allocation", "decision_making",
    ],
    SkillCategory.DIPLOMACY: [
        "cultural_awareness", "language_proficiency", "treaty_drafting",
        "mediation_skills", "trade_negotiation", "protocol_knowledge",
        "alliance_building", "threat_assessment", "political_theory",
    ],
}

PARAMETER_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "generic": [
        {"name": "cooldown_seconds", "type": "float", "default": 10.0, "min": 0.0, "max": 300.0},
        {"name": "duration_seconds", "type": "float", "default": 5.0, "min": 0.5, "max": 120.0},
        {"name": "range", "type": "float", "default": 10.0, "min": 1.0, "max": 100.0},
        {"name": "resource_cost", "type": "float", "default": 20.0, "min": 0.0, "max": 500.0},
    ],
    SkillCategory.COMBAT: [
        {"name": "damage", "type": "float", "default": 25.0, "min": 1.0, "max": 1000.0},
        {"name": "critical_chance", "type": "float", "default": 0.1, "min": 0.0, "max": 1.0},
        {"name": "armor_penetration", "type": "float", "default": 0.0, "min": 0.0, "max": 1.0},
        {"name": "knockback_force", "type": "float", "default": 0.0, "min": 0.0, "max": 50.0},
    ],
    SkillCategory.MAGIC: [
        {"name": "mana_cost", "type": "float", "default": 30.0, "min": 5.0, "max": 500.0},
        {"name": "spell_power", "type": "float", "default": 20.0, "min": 1.0, "max": 500.0},
        {"name": "cast_time", "type": "float", "default": 1.5, "min": 0.0, "max": 10.0},
        {"name": "elemental_type", "type": "string", "default": "arcane", "options": ["fire", "ice", "lightning", "arcane", "nature", "shadow"]},
    ],
    SkillCategory.CRAFTING: [
        {"name": "material_quality", "type": "float", "default": 0.5, "min": 0.0, "max": 1.0},
        {"name": "crafting_speed", "type": "float", "default": 1.0, "min": 0.5, "max": 5.0},
        {"name": "durability_bonus", "type": "float", "default": 0.0, "min": 0.0, "max": 100.0},
        {"name": "recipe_level", "type": "int", "default": 1, "min": 1, "max": 100},
    ],
    SkillCategory.SOCIAL: [
        {"name": "influence_range", "type": "float", "default": 15.0, "min": 5.0, "max": 200.0},
        {"name": "persuasion_power", "type": "float", "default": 0.3, "min": 0.0, "max": 1.0},
        {"name": "reputation_cost", "type": "float", "default": 0.0, "min": 0.0, "max": 100.0},
        {"name": "target_count", "type": "int", "default": 1, "min": 1, "max": 50},
    ],
    SkillCategory.EXPLORATION: [
        {"name": "detection_radius", "type": "float", "default": 30.0, "min": 5.0, "max": 500.0},
        {"name": "movement_speed_mult", "type": "float", "default": 1.2, "min": 1.0, "max": 3.0},
        {"name": "vision_range", "type": "float", "default": 50.0, "min": 10.0, "max": 500.0},
        {"name": "fatigue_cost", "type": "float", "default": 15.0, "min": 0.0, "max": 100.0},
    ],
    SkillCategory.STEALTH: [
        {"name": "visibility_modifier", "type": "float", "default": 0.5, "min": 0.0, "max": 1.0},
        {"name": "noise_level", "type": "float", "default": 0.2, "min": 0.0, "max": 1.0},
        {"name": "detection_threshold", "type": "float", "default": 0.7, "min": 0.0, "max": 1.0},
        {"name": "backstab_multiplier", "type": "float", "default": 2.0, "min": 1.0, "max": 5.0},
    ],
    SkillCategory.TECHNOLOGY: [
        {"name": "tech_level", "type": "int", "default": 1, "min": 1, "max": 10},
        {"name": "power_consumption", "type": "float", "default": 50.0, "min": 0.0, "max": 1000.0},
        {"name": "hacking_speed", "type": "float", "default": 1.0, "min": 0.5, "max": 5.0},
        {"name": "system_stability", "type": "float", "default": 0.8, "min": 0.1, "max": 1.0},
    ],
    SkillCategory.SURVIVAL: [
        {"name": "resistance_factor", "type": "float", "default": 0.3, "min": 0.0, "max": 1.0},
        {"name": "resource_efficiency", "type": "float", "default": 1.0, "min": 0.5, "max": 3.0},
        {"name": "healing_power", "type": "float", "default": 10.0, "min": 1.0, "max": 200.0},
        {"name": "endurance_bonus", "type": "float", "default": 20.0, "min": 0.0, "max": 200.0},
    ],
    SkillCategory.LEADERSHIP: [
        {"name": "command_range", "type": "float", "default": 25.0, "min": 5.0, "max": 300.0},
        {"name": "morale_boost", "type": "float", "default": 0.15, "min": 0.0, "max": 1.0},
        {"name": "follower_cap", "type": "int", "default": 5, "min": 1, "max": 100},
        {"name": "tactical_bonus", "type": "float", "default": 0.1, "min": 0.0, "max": 0.5},
    ],
    SkillCategory.DIPLOMACY: [
        {"name": "treaty_duration", "type": "float", "default": 300.0, "min": 60.0, "max": 3600.0},
        {"name": "trust_threshold", "type": "float", "default": 0.5, "min": 0.0, "max": 1.0},
        {"name": "trade_discount", "type": "float", "default": 0.1, "min": 0.0, "max": 0.5},
        {"name": "faction_standing", "type": "float", "default": 10.0, "min": 0.0, "max": 100.0},
    ],
}

SKILL_NAMES: Dict[SkillCategory, List[Tuple[str, str]]] = {
    SkillCategory.COMBAT: [
        ("Whirlwind Slash", "A spinning attack that strikes all nearby enemies"),
        ("Power Strike", "A devastating blow that penetrates armor"),
        ("Shield Wall", "Raise a protective barrier that absorbs incoming damage"),
        ("Berserker Rage", "Enter a frenzied state with increased damage and speed"),
        ("Counter Stance", "Parry incoming attacks and retaliate with lethal precision"),
        ("War Cry", "Unleash a mighty shout that intimidates foes and buffs allies"),
        ("Flurry", "A rapid sequence of strikes that overwhelm defenses"),
        ("Crippling Shot", "Target enemy weak points to slow and debilitate"),
    ],
    SkillCategory.CRAFTING: [
        ("Masterwork Forge", "Craft items with superior quality and durability"),
        ("Enchanted Infusion", "Imbue crafted items with magical properties"),
        ("Rapid Assembly", "Dramatically increase crafting speed for basic items"),
        ("Blueprint Innovation", "Create new recipes by combining known schematics"),
        ("Recycling Expert", "Salvage materials from unwanted equipment"),
        ("Fortification", "Reinforce crafted items for increased longevity"),
    ],
    SkillCategory.SOCIAL: [
        ("Silver Tongue", "Persuade merchants for better prices and rare items"),
        ("Inspire Loyalty", "Strengthen bonds with companions and followers"),
        ("Rumor Network", "Gather intelligence from ambient social interactions"),
        ("Crowd Rallier", "Motivate crowds to support your cause"),
        ("Charming Presence", "Passively improve first impressions with NPCs"),
    ],
    SkillCategory.EXPLORATION: [
        ("Eagle Eye", "Reveal hidden objects and points of interest at range"),
        ("Pioneer's Stride", "Move faster across all terrain types"),
        ("Dungeon Sense", "Detect traps, secret passages, and treasure caches"),
        ("Mountaineer", "Scale sheer cliffs and navigate vertical environments"),
        ("Cartographer", "Automatically map explored areas with detailed annotations"),
    ],
    SkillCategory.STEALTH: [
        ("Shadow Cloak", "Become nearly invisible in low-light conditions"),
        ("Silent Takedown", "Eliminate unaware targets without alerting others"),
        ("Pickpocket Mastery", "Steal from NPCs with reduced detection risk"),
        ("Trap Expert", "Disarm, reset, or craft traps in the environment"),
        ("Ghost Walk", "Move without leaving footprints or sound"),
    ],
    SkillCategory.MAGIC: [
        ("Arcane Barrage", "Unleash a volley of magical projectiles"),
        ("Elemental Ward", "Create a barrier attuned to a chosen element"),
        ("Teleportation Rune", "Mark a location for instantaneous return"),
        ("Mana Surge", "Temporarily amplify all spell effects at mana cost"),
        ("Summon Familiar", "Call forth a loyal magical companion"),
    ],
    SkillCategory.TECHNOLOGY: [
        ("Drone Deployment", "Launch a reconnaissance drone to scout ahead"),
        ("Overclock", "Temporarily boost tech device performance"),
        ("EMP Pulse", "Disable enemy electronics in an area"),
        ("Auto-Turret", "Deploy an automated defensive turret"),
        ("Cybernetic Enhancement", "Permanently upgrade a body part with tech"),
    ],
    SkillCategory.SURVIVAL: [
        ("Firestarter", "Ignite campfires and torches without tools"),
        ("Herbal Remedy", "Craft healing salves from gathered herbs"),
        ("Iron Stomach", "Consume normally inedible resources safely"),
        ("Weatherproof", "Gain resistance to extreme climate effects"),
        ("Tracker", "Follow creature trails and identify recent activity"),
    ],
    SkillCategory.LEADERSHIP: [
        ("Battle Command", "Direct allies to focus fire on a single target"),
        ("Inspiring Speech", "Boost the morale and combat effectiveness of your team"),
        ("Logistics Expert", "Increase party inventory capacity and resource sharing"),
        ("Formation Tactics", "Arrange your party in defensive or offensive formations"),
        ("Delegate", "Assign autonomous tasks to companions"),
    ],
    SkillCategory.DIPLOMACY: [
        ("Ceasefire Negotiation", "End hostile encounters through dialogue"),
        ("Trade Alliance", "Establish beneficial trade agreements with factions"),
        ("Cultural Ambassador", "Gain favor with foreign nations through understanding"),
        ("Peacekeeper", "Mediate conflicts between NPC factions"),
        ("Strategic Treaty", "Form military and economic pacts between powers"),
    ],
}

OUTPUT_SCHEMA_TEMPLATES: Dict[SkillCategory, Dict[str, Any]] = {
    SkillCategory.COMBAT: {
        "type": "combat_effect",
        "fields": ["damage_dealt", "status_effects", "area_of_effect", "combo_potential"],
    },
    SkillCategory.CRAFTING: {
        "type": "crafting_result",
        "fields": ["item_created", "quality_rating", "material_consumed", "bonus_stats"],
    },
    SkillCategory.SOCIAL: {
        "type": "social_outcome",
        "fields": ["reputation_change", "npc_attitude", "information_gained", "favor_earned"],
    },
    SkillCategory.EXPLORATION: {
        "type": "exploration_result",
        "fields": ["areas_revealed", "items_discovered", "landmarks_found", "dangers_identified"],
    },
    SkillCategory.STEALTH: {
        "type": "stealth_outcome",
        "fields": ["detection_level", "items_acquired", "enemies_bypassed", "alert_status"],
    },
    SkillCategory.MAGIC: {
        "type": "magical_effect",
        "fields": ["spell_power_used", "elemental_affinity", "mana_efficiency", "collateral_effects"],
    },
    SkillCategory.TECHNOLOGY: {
        "type": "tech_result",
        "fields": ["device_status", "power_drain", "effect_radius", "system_integrity"],
    },
    SkillCategory.SURVIVAL: {
        "type": "survival_effect",
        "fields": ["condition_recovery", "resource_gained", "hazard_mitigated", "endurance_saved"],
    },
    SkillCategory.LEADERSHIP: {
        "type": "command_effect",
        "fields": ["followers_affected", "morale_change", "tactical_advantage", "coordination_bonus"],
    },
    SkillCategory.DIPLOMACY: {
        "type": "diplomatic_result",
        "fields": ["treaty_terms", "faction_standing_change", "trade_benefits", "alliance_strength"],
    },
}

TRAINING_DATA_TEMPLATES: Dict[SkillCategory, List[str]] = {
    SkillCategory.COMBAT: [
        "combat_scenarios.json", "damage_calibration.csv", "enemy_stat_blocks.yaml",
        "weapon_balance_data.json", "combat_playtests.log",
    ],
    SkillCategory.CRAFTING: [
        "recipe_database.json", "material_properties.csv", "crafting_economy.yaml",
        "item_stat_distributions.json", "player_crafting_sessions.log",
    ],
    SkillCategory.SOCIAL: [
        "dialogue_trees.json", "npc_personality_profiles.csv", "social_graph.yaml",
        "reputation_systems.json", "social_interaction_logs.log",
    ],
    SkillCategory.EXPLORATION: [
        "terrain_maps.json", "poi_distributions.csv", "exploration_metrics.yaml",
        "discovery_patterns.json", "player_movement_heatmaps.log",
    ],
    SkillCategory.STEALTH: [
        "detection_models.json", "visibility_grids.csv", "stealth_mechanics.yaml",
        "guard_patrol_routes.json", "stealth_mission_logs.log",
    ],
    SkillCategory.MAGIC: [
        "spell_grimoires.json", "elemental_interactions.csv", "mana_systems.yaml",
        "spell_effect_particles.json", "magic_balance_tests.log",
    ],
    SkillCategory.TECHNOLOGY: [
        "tech_trees.json", "device_specifications.csv", "power_systems.yaml",
        "hacking_minigames.json", "technology_progression.log",
    ],
    SkillCategory.SURVIVAL: [
        "resource_database.json", "biome_difficulty.csv", "survival_conditions.yaml",
        "crafting_survival.json", "survival_session_logs.log",
    ],
    SkillCategory.LEADERSHIP: [
        "follower_archetypes.json", "command_structures.csv", "morale_systems.yaml",
        "tactical_formations.json", "leadership_scenarios.log",
    ],
    SkillCategory.DIPLOMACY: [
        "faction_relations.json", "treaty_templates.csv", "diplomatic_protocols.yaml",
        "trade_agreements.json", "diplomatic_events.log",
    ],
}


@dataclass
class GeneratedSkill:
    skill_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    category: SkillCategory = SkillCategory.COMBAT
    complexity: ComplexityLevel = ComplexityLevel.BASIC
    prerequisites: List[str] = field(default_factory=list)
    training_data: List[str] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    version: str = "1.0"
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "complexity": self.complexity.value,
            "prerequisites": self.prerequisites,
            "training_data": self.training_data,
            "parameters": self.parameters,
            "output_schema": self.output_schema,
            "confidence": round(self.confidence, 4),
            "version": self.version,
            "created_at": self.created_at,
        }


@dataclass
class SkillTemplate:
    template_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: SkillCategory = SkillCategory.COMBAT
    parameter_schema: List[Dict[str, Any]] = field(default_factory=list)
    default_actions: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "category": self.category.value,
            "parameter_schema": self.parameter_schema,
            "default_actions": self.default_actions,
            "constraints": self.constraints,
            "examples": self.examples,
            "created_at": self.created_at,
        }


@dataclass
class SkillComposition:
    composition_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    component_skills: List[str] = field(default_factory=list)
    composition_logic: Dict[str, Any] = field(default_factory=dict)
    output_skill_id: str = ""
    synergy_score: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "composition_id": self.composition_id,
            "name": self.name,
            "component_skills": self.component_skills,
            "composition_logic": self.composition_logic,
            "output_skill_id": self.output_skill_id,
            "synergy_score": round(self.synergy_score, 4),
            "created_at": self.created_at,
        }


class AgentSkillGenerator:
    """AI-driven autonomous skill generation system for the SparkLabs game engine.

    Generates complete skill definitions with parameters, dependencies,
    compositions, and evolution pathways. Produces skill trees, decomposes
    complex skills, adapts existing skills to new contexts, and evaluates
    skill viability across diverse game design scenarios.

    Usage:
        gen = AgentSkillGenerator.get_instance()
        skill = gen.generate_skill("Create a fire-based combat skill")
        template = gen.create_template("Combat Skill Blueprint", SkillCategory.COMBAT)
        composition = gen.compose_skills(["skill_a", "skill_b"], "composite")
    """

    _instance: Optional["AgentSkillGenerator"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_SKILLS: int = 500
    MAX_TEMPLATES: int = 200
    MAX_COMPOSITIONS: int = 300
    MIN_CONFIDENCE_FOR_ACCEPTANCE: float = 0.3
    DEFAULT_TREE_DEPTH: int = 5
    DEFAULT_TREE_BREADTH: int = 4
    ADAPTATION_VARIATION_FACTOR: float = 0.25
    REFINEMENT_ITERATIONS: int = 3

    def __new__(cls) -> "AgentSkillGenerator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentSkillGenerator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        _time_module.sleep(0.001)
        if not hasattr(self, "_initialized"):
            self._skills: Dict[str, GeneratedSkill] = {}
            self._templates: Dict[str, SkillTemplate] = {}
            self._compositions: Dict[str, SkillComposition] = {}
            self._skill_by_category: Dict[str, List[str]] = {}
            self._skill_by_complexity: Dict[str, List[str]] = {}
            self._template_by_category: Dict[str, List[str]] = {}
            self._composition_by_output: Dict[str, str] = {}
            self._skill_name_index: Dict[str, str] = {}
            self._total_skills_generated: int = 0
            self._total_templates_created: int = 0
            self._total_compositions_formed: int = 0
            self._total_skills_composed: int = 0
            self._total_skills_decomposed: int = 0
            self._total_skills_adapted: int = 0
            self._total_skill_trees_generated: int = 0
            self._total_batches_processed: int = 0
            self._total_refinements_applied: int = 0
            for cat in SkillCategory:
                self._skill_by_category[cat.value] = []
                self._template_by_category[cat.value] = []
            for cl in ComplexityLevel:
                self._skill_by_complexity[cl.value] = []
            self._initialized = True

    def generate_skill(
        self,
        description: str = "",
        category: Optional[SkillCategory] = None,
        complexity: Optional[ComplexityLevel] = None,
        name: Optional[str] = None,
        override_training_data: Optional[List[str]] = None,
        override_parameters: Optional[List[Dict[str, Any]]] = None,
    ) -> GeneratedSkill:
        """Generate a novel skill definition based on game design context.

        Synthesizes a complete skill with appropriate parameters, prerequisites,
        training data references, and output schema for the specified category
        and complexity level.

        Args:
            description: Natural language description of the desired skill.
            category: Game design category for the skill. Auto-detected if None.
            complexity: Complexity level. Derived heuristically if None.
            name: Explicit skill name. Auto-generated if None.
            override_training_data: Custom training data references.
            override_parameters: Custom parameter definitions.

        Returns:
            A fully populated GeneratedSkill dataclass instance.
        """
        _time_module.sleep(0.001)
        rng = random.Random()

        if category is None:
            category = self._infer_category(description, rng)
        if complexity is None:
            complexity = self._infer_complexity(description, rng)

        weights = COMPLEXITY_WEIGHTS[complexity]

        if name is None:
            name = self._generate_skill_name(category, rng)
        while name in self._skill_name_index:
            name = self._generate_skill_name(category, rng)

        prereqs = self._generate_prerequisites(category, complexity, rng)

        if override_training_data is not None:
            training_data = list(override_training_data)
        else:
            training_data = self._generate_training_data(category, rng)

        if override_parameters is not None:
            parameters = list(override_parameters)
        else:
            parameters = self._generate_parameters(category, complexity, rng)

        output_schema = OUTPUT_SCHEMA_TEMPLATES.get(
            category, {"type": "generic_effect", "fields": ["result", "side_effects"]}
        )

        confidence = weights["confidence_base"] * rng.uniform(0.8, 1.2)
        confidence = min(1.0, max(0.1, confidence))

        skill = GeneratedSkill(
            name=name,
            description=description or self._derive_description(name, category, complexity),
            category=category,
            complexity=complexity,
            prerequisites=prereqs,
            training_data=training_data,
            parameters=parameters,
            output_schema=dict(output_schema),
            confidence=round(confidence, 4),
        )
        self._skills[skill.skill_id] = skill
        self._skill_name_index[skill.name] = skill.skill_id
        self._skill_by_category.setdefault(category.value, []).append(skill.skill_id)
        self._skill_by_complexity.setdefault(complexity.value, []).append(skill.skill_id)
        self._total_skills_generated += 1

        if len(self._skills) > self.MAX_SKILLS:
            self._evict_oldest_skills()

        return skill

    def create_template(
        self,
        name: str = "",
        category: SkillCategory = SkillCategory.COMBAT,
        parameter_schema: Optional[List[Dict[str, Any]]] = None,
        default_actions: Optional[List[Dict[str, Any]]] = None,
        constraints: Optional[List[Dict[str, Any]]] = None,
        examples: Optional[List[Dict[str, Any]]] = None,
    ) -> SkillTemplate:
        """Create a reusable skill template blueprint.

        Templates define parameter schemas, default action sequences,
        constraints, and usage examples that can be instantiated into
        concrete GeneratedSkill instances.

        Args:
            name: Template display name.
            category: Skill category for the template.
            parameter_schema: Schema defining valid parameters.
            default_actions: Default action sequences for the skill.
            constraints: Usage constraints and limitations.
            examples: Example skill instantiations from this template.

        Returns:
            A SkillTemplate dataclass instance.
        """
        _time_module.sleep(0.001)
        rng = random.Random()

        if not name:
            name = f"Template-{category.value}-{self._total_templates_created + 1:04d}"

        if parameter_schema is None:
            parameter_schema = PARAMETER_TEMPLATES.get(
                category, PARAMETER_TEMPLATES["generic"]
            )

        if default_actions is None:
            default_actions = self._derive_default_actions(category, rng)

        if constraints is None:
            constraints = self._derive_constraints(category, rng)

        if examples is None:
            examples = self._derive_examples(category, rng)

        template = SkillTemplate(
            template_id=uuid.uuid4().hex,
            name=name,
            category=category,
            parameter_schema=parameter_schema,
            default_actions=default_actions,
            constraints=constraints,
            examples=examples,
        )
        self._templates[template.template_id] = template
        self._template_by_category.setdefault(category.value, []).append(template.template_id)
        self._total_templates_created += 1

        if len(self._templates) > self.MAX_TEMPLATES:
            self._evict_oldest_templates()

        return template

    def compose_skills(
        self,
        skill_ids: List[str],
        composition_name: str = "",
        composition_strategy: str = "merge",
    ) -> Optional[SkillComposition]:
        """Compose multiple skills into a compound skill.

        Merges component skills into a unified composition, computing
        synergy scores and generating composition logic that defines
        how the skills interact.

        Args:
            skill_ids: IDs of component skills to compose.
            composition_name: Name for the resulting composition.
            composition_strategy: Strategy for merging: merge, chain, or overlay.

        Returns:
            A SkillComposition dataclass instance, or None if composition fails.
        """
        _time_module.sleep(0.001)
        if len(skill_ids) < 2:
            return None

        rng = random.Random()
        resolved: List[GeneratedSkill] = []
        for sid in skill_ids:
            skill = self._skills.get(sid)
            if skill is None:
                continue
            resolved.append(skill)

        if len(resolved) < 2:
            return None

        if not composition_name:
            composition_name = f"Composition-{self._total_compositions_formed + 1:04d}"

        categories = list(set(s.category for s in resolved))
        dominant = max(set(categories), key=categories.count)

        synergy = self._compute_composition_synergy(resolved, dominant)

        merged_params: List[Dict[str, Any]] = []
        seen_param_names: set = set()
        for skill in resolved:
            for param in skill.parameters:
                pname = param.get("name", "")
                if pname and pname not in seen_param_names:
                    merged_params.append(dict(param))
                    seen_param_names.add(pname)

        avg_confidence = sum(s.confidence for s in resolved) / len(resolved)
        complexity = self._derive_composition_complexity(resolved)

        composition_logic: Dict[str, Any] = {
            "strategy": composition_strategy,
            "component_count": len(resolved),
            "input_skill_ids": skill_ids,
            "execution_order": skill_ids if composition_strategy == "chain" else None,
            "overlay_targets": {} if composition_strategy == "overlay" else None,
            "merged_parameters": merged_params,
            "synergy_score": round(synergy, 4),
        }

        output_skill = GeneratedSkill(
            name=composition_name,
            description=f"Composite skill formed from {len(resolved)} component skills",
            category=dominant,
            complexity=complexity,
            prerequisites=list(set(p for s in resolved for p in s.prerequisites)),
            training_data=list(set(d for s in resolved for d in s.training_data)),
            parameters=merged_params,
            output_schema=OUTPUT_SCHEMA_TEMPLATES.get(
                dominant, {"type": "composite_effect", "fields": ["combined_results"]}
            ),
            confidence=round(avg_confidence, 4),
        )
        self._skills[output_skill.skill_id] = output_skill
        self._skill_name_index[output_skill.name] = output_skill.skill_id
        self._skill_by_category.setdefault(dominant.value, []).append(output_skill.skill_id)
        self._skill_by_complexity.setdefault(complexity.value, []).append(output_skill.skill_id)
        self._total_skills_composed += 1

        composition = SkillComposition(
            name=composition_name,
            component_skills=skill_ids,
            composition_logic=composition_logic,
            output_skill_id=output_skill.skill_id,
            synergy_score=round(synergy, 4),
        )
        self._compositions[composition.composition_id] = composition
        self._composition_by_output[output_skill.skill_id] = composition.composition_id
        self._total_compositions_formed += 1

        if len(self._compositions) > self.MAX_COMPOSITIONS:
            self._evict_oldest_compositions()

        return composition

    def decompose_skill(
        self,
        skill_id: str,
        target_complexity: ComplexityLevel = ComplexityLevel.BASIC,
    ) -> List[GeneratedSkill]:
        """Decompose a complex skill into simpler sub-skills.

        Breaks down a high-complexity skill into multiple lower-complexity
        skills that individually represent constituent aspects.

        Args:
            skill_id: ID of the skill to decompose.
            target_complexity: Desired complexity level for sub-skills.

        Returns:
            A list of GeneratedSkill instances representing sub-skills.
        """
        _time_module.sleep(0.001)
        skill = self._skills.get(skill_id)
        if skill is None:
            return []

        rng = random.Random()
        current = COMPLEXITY_WEIGHTS[skill.complexity]
        target = COMPLEXITY_WEIGHTS[target_complexity]

        sub_count = min(
            current["param_count_range"][1] // max(target["param_count_range"][0], 1),
            6,
        )

        if sub_count < 2:
            return []

        sub_skills: List[GeneratedSkill] = []
        params_pool = list(skill.parameters)
        rng.shuffle(params_pool)

        params_per_sub = max(1, len(params_pool) // sub_count)

        for i in range(sub_count):
            start = i * params_per_sub
            end = start + params_per_sub if i < sub_count - 1 else len(params_pool)
            sub_params = params_pool[start:end]

            sub_name = f"{skill.name} - Part {i + 1}"

            sub_skill = self.generate_skill(
                description=f"Decomposed sub-skill from {skill.name}",
                category=skill.category,
                complexity=target_complexity,
                name=sub_name,
                override_training_data=list(skill.training_data),
                override_parameters=sub_params,
            )
            sub_skills.append(sub_skill)

        self._total_skills_decomposed += 1
        return sub_skills

    def evaluate_skill(
        self,
        skill_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluate a skill's viability, balance, and synergy.

        Produces a comprehensive evaluation report including balance
        scoring, synergy with a given context, and improvement
        recommendations.

        Args:
            skill_id: ID of the skill to evaluate.
            context: Optional game context for contextual evaluation.

        Returns:
            A dictionary with evaluation metrics and recommendations.
        """
        _time_module.sleep(0.001)
        skill = self._skills.get(skill_id)
        if skill is None:
            return {"error": f"Skill '{skill_id}' not found", "success": False}

        rng = random.Random()

        balance_score = self._compute_balance_score(skill, rng)
        viability_score = self._compute_viability_score(skill, rng)
        synergy_context = self._compute_context_synergy(skill, context, rng)
        overall_score = (
            balance_score * 0.35 + viability_score * 0.35 + synergy_context * 0.30
        )

        recommendations: List[Dict[str, str]] = []
        if balance_score < 0.5:
            recommendations.append({
                "type": "rebalance",
                "detail": "Parameter values may need adjustment for fair gameplay",
            })
        if viability_score < 0.4:
            recommendations.append({
                "type": "refine",
                "detail": "Skill may lack practical applicability in current game design",
            })
        if skill.confidence < 0.5:
            recommendations.append({
                "type": "validate",
                "detail": "Low confidence suggests more training data is needed",
            })
        if len(skill.prerequisites) > 5:
            recommendations.append({
                "type": "simplify",
                "detail": "Too many prerequisites may limit accessibility",
            })

        return {
            "success": True,
            "skill_id": skill.skill_id,
            "skill_name": skill.name,
            "category": skill.category.value,
            "complexity": skill.complexity.value,
            "balance_score": round(balance_score, 4),
            "viability_score": round(viability_score, 4),
            "context_synergy": round(synergy_context, 4),
            "overall_score": round(overall_score, 4),
            "confidence": round(skill.confidence, 4),
            "parameter_count": len(skill.parameters),
            "prerequisite_count": len(skill.prerequisites),
            "recommendations": recommendations,
        }

    def adapt_skill(
        self,
        skill_id: str,
        target_category: SkillCategory,
        variation_factor: Optional[float] = None,
        preserve_core: bool = True,
    ) -> Optional[GeneratedSkill]:
        """Adapt an existing skill to a new category.

        Transforms a skill from its current category to a target category,
        adjusting parameters, output schemas, and training data references
        while optionally preserving core mechanics.

        Args:
            skill_id: ID of the skill to adapt.
            target_category: Target category for adaptation.
            variation_factor: How much to vary (0.0 = identical params, 1.0 = fully randomized).
            preserve_core: Whether to preserve core skill identity.

        Returns:
            A new GeneratedSkill instance adapted to the target category.
        """
        _time_module.sleep(0.001)
        skill = self._skills.get(skill_id)
        if skill is None:
            return None

        if variation_factor is None:
            variation_factor = self.ADAPTATION_VARIATION_FACTOR

        rng = random.Random()

        adapted_name = f"{skill.name} ({target_category.value})"
        while adapted_name in self._skill_name_index:
            adapted_name = f"{skill.name} ({target_category.value}-{rng.randint(1, 99)})"

        if preserve_core:
            adapted_params = list(skill.parameters)
            for param in adapted_params:
                if rng.random() < variation_factor:
                    if param.get("type") == "float":
                        default_val = param.get("default", 0.0)
                        param["default"] = round(
                            default_val * rng.uniform(0.5, 1.5), 2
                        )
                    elif param.get("type") == "int":
                        default_val = param.get("default", 0)
                        param["default"] = int(default_val * rng.uniform(0.5, 1.5))
        else:
            adapted_params = self._generate_parameters(
                target_category, skill.complexity, rng
            )

        new_training_data = list(skill.training_data)
        target_training = TRAINING_DATA_TEMPLATES.get(target_category, [])
        new_training_data.extend(
            td for td in target_training[:2] if td not in new_training_data
        )

        new_prerequisites = list(skill.prerequisites)
        target_prereq_pool = PREREQUISITE_POOL.get(target_category, [])
        if target_prereq_pool:
            new_prereqs_needed = COMPLEXITY_WEIGHTS[skill.complexity][
                "prerequisite_count"
            ]
            current = len(new_prerequisites)
            to_add = max(0, new_prereqs_needed - current)
            candidates = [p for p in target_prereq_pool if p not in new_prerequisites]
            rng.shuffle(candidates)
            new_prerequisites.extend(candidates[:to_add])

        confidence = skill.confidence * rng.uniform(0.7, 0.95)

        adapted = GeneratedSkill(
            name=adapted_name,
            description=f"Adapted from {skill.name}: {skill.description}",
            category=target_category,
            complexity=skill.complexity,
            prerequisites=new_prerequisites,
            training_data=new_training_data,
            parameters=adapted_params,
            output_schema=OUTPUT_SCHEMA_TEMPLATES.get(
                target_category,
                {"type": "adapted_effect", "fields": ["adapted_result"]},
            ),
            confidence=round(confidence, 4),
        )
        self._skills[adapted.skill_id] = adapted
        self._skill_name_index[adapted.name] = adapted.skill_id
        self._skill_by_category.setdefault(target_category.value, []).append(
            adapted.skill_id
        )
        self._skill_by_complexity.setdefault(skill.complexity.value, []).append(
            adapted.skill_id
        )
        self._total_skills_adapted += 1
        return adapted

    def generate_skill_tree(
        self,
        root_category: SkillCategory = SkillCategory.COMBAT,
        depth: Optional[int] = None,
        breadth: Optional[int] = None,
        root_description: str = "",
    ) -> Dict[str, Any]:
        """Generate a hierarchical skill progression tree.

        Builds a multi-level skill tree with parent-child relationships,
        where each node is a GeneratedSkill and edges represent
        prerequisite dependencies.

        Args:
            root_category: Skill category for the root node.
            depth: Maximum depth of the tree. Uses DEFAULT_TREE_DEPTH if None.
            breadth: Maximum children per node. Uses DEFAULT_TREE_BREADTH if None.
            root_description: Description for the root skill.

        Returns:
            A dictionary representing the complete skill tree structure.
        """
        _time_module.sleep(0.001)
        if depth is None:
            depth = self.DEFAULT_TREE_DEPTH
        if breadth is None:
            breadth = self.DEFAULT_TREE_BREADTH

        rng = random.Random()

        complexities: List[ComplexityLevel] = [
            ComplexityLevel.BASIC,
            ComplexityLevel.INTERMEDIATE,
            ComplexityLevel.ADVANCED,
            ComplexityLevel.EXPERT,
            ComplexityLevel.MASTER,
            ComplexityLevel.LEGENDARY,
        ]

        root_complexity = ComplexityLevel.BASIC
        root = self.generate_skill(
            description=root_description or f"Root skill for {root_category.value} tree",
            category=root_category,
            complexity=root_complexity,
            name=f"{root_category.value.title()} Foundation",
        )

        tree: Dict[str, Any] = {
            "tree_id": uuid.uuid4().hex,
            "root_category": root_category.value,
            "root_skill_id": root.skill_id,
            "root_name": root.name,
            "max_depth": depth,
            "max_breadth": breadth,
            "total_nodes": 1,
            "nodes": {root.skill_id: self._tree_node_info(root, 0)},
            "edges": [],
            "layers": {},
            "created_at": _time_module.time(),
        }

        current_layer: List[GeneratedSkill] = [root]
        layer_index = 0
        tree["layers"][str(layer_index)] = [root.skill_id]

        for layer in range(1, depth):
            next_layer: List[GeneratedSkill] = []
            layer_ids: List[str] = []

            for parent in current_layer:
                child_count = rng.randint(1, breadth)
                parent_complexity = complexities.index(parent.complexity)
                child_complexity = complexities[
                    min(parent_complexity + 1, len(complexities) - 1)
                ]

                for _ in range(child_count):
                    child_name = f"{parent.name} - Branch {rng.randint(1, 99)}"
                    while child_name in self._skill_name_index:
                        child_name = f"{parent.name} - Branch {rng.randint(1, 99)}"

                    child = self.generate_skill(
                        description=f"Child skill in {root_category.value} tree, layer {layer}",
                        category=root_category,
                        complexity=child_complexity,
                        name=child_name,
                    )

                    child.prerequisites = [parent.skill_id]

                    next_layer.append(child)
                    layer_ids.append(child.skill_id)
                    tree["nodes"][child.skill_id] = self._tree_node_info(child, layer)
                    tree["edges"].append({
                        "from": parent.skill_id,
                        "to": child.skill_id,
                        "layer": layer,
                    })
                    tree["total_nodes"] += 1

            if next_layer:
                tree["layers"][str(layer)] = layer_ids
                current_layer = next_layer
                layer_index = layer

        self._total_skill_trees_generated += 1
        return tree

    def batch_generate_skills(
        self,
        count: int = 10,
        categories: Optional[List[SkillCategory]] = None,
        complexity_distribution: Optional[Dict[ComplexityLevel, float]] = None,
    ) -> List[GeneratedSkill]:
        """Generate multiple skills in a single batch operation.

        Produces a collection of skills across specified categories
        with configurable complexity distribution.

        Args:
            count: Number of skills to generate.
            categories: Categories to distribute skills across. Uses all if None.
            complexity_distribution: Weight distribution for complexity levels.

        Returns:
            A list of GeneratedSkill instances.
        """
        _time_module.sleep(0.001)
        rng = random.Random()
        skills: List[GeneratedSkill] = []

        if categories is None:
            categories = list(SKILL_CATEGORY_POOL)

        if complexity_distribution is None:
            complexity_distribution = {
                ComplexityLevel.BASIC: 0.30,
                ComplexityLevel.INTERMEDIATE: 0.25,
                ComplexityLevel.ADVANCED: 0.20,
                ComplexityLevel.EXPERT: 0.12,
                ComplexityLevel.MASTER: 0.08,
                ComplexityLevel.LEGENDARY: 0.05,
            }

        for _ in range(count):
            category = rng.choice(categories)
            complexity = self._weighted_choice(rng, complexity_distribution)
            if complexity is None:
                complexity = ComplexityLevel.BASIC

            skill = self.generate_skill(
                description=f"Batch-generated {category.value} skill",
                category=category,
                complexity=complexity,
            )
            skills.append(skill)

        self._total_batches_processed += 1
        return skills

    def refine_skill_parameters(
        self,
        skill_id: str,
        refinement_goals: Optional[Dict[str, Any]] = None,
        iterations: Optional[int] = None,
    ) -> Optional[GeneratedSkill]:
        """Iteratively refine a skill's parameters for better balance.

        Applies parameter tuning across multiple iterations, adjusting
        values based on refinement goals such as balancing, scaling,
        or improving accessibility.

        Args:
            skill_id: ID of the skill to refine.
            refinement_goals: Dict with goals like balance_target, scale_factor.
            iterations: Number of refinement iterations. Uses default if None.

        Returns:
            The refined GeneratedSkill instance, or None if skill not found.
        """
        _time_module.sleep(0.001)
        skill = self._skills.get(skill_id)
        if skill is None:
            return None

        if iterations is None:
            iterations = self.REFINEMENT_ITERATIONS

        rng = random.Random()
        goals = refinement_goals or {}

        balance_target = goals.get("balance_target", 0.7)
        scale_factor = goals.get("scale_factor", 1.0)
        normalize = goals.get("normalize", True)

        for _ in range(iterations):
            for param in skill.parameters:
                if param.get("type") == "float":
                    default_val = param.get("default", 0.0)
                    min_val = param.get("min", 0.0)
                    max_val = param.get("max", 1.0)

                    if normalize:
                        current_range = max_val - min_val
                        if current_range > 0:
                            normalized = (default_val - min_val) / current_range
                            gap = balance_target - normalized
                            adjusted = normalized + gap * 0.3 * rng.uniform(0.8, 1.2)
                            adjusted = max(0.0, min(1.0, adjusted))
                            param["default"] = round(
                                min_val + adjusted * current_range, 2
                            )

                    param["default"] = round(
                        param["default"] * scale_factor, 2
                    )
                    param["default"] = max(
                        param.get("min", 0.0),
                        min(param.get("max", float("inf")), param["default"]),
                    )

                elif param.get("type") == "int":
                    default_val = param.get("default", 0)
                    if scale_factor != 1.0:
                        param["default"] = max(0, int(default_val * scale_factor))
                    param["default"] = max(
                        param.get("min", 0),
                        min(param.get("max", 2**31 - 1), param["default"]),
                    )

        skill.version = self._bump_version(skill.version)
        skill.confidence = min(1.0, skill.confidence * 1.05)
        self._total_refinements_applied += 1
        return skill

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive AgentSkillGenerator subsystem statistics."""
        _time_module.sleep(0.001)
        total_skills = len(self._skills)
        total_templates = len(self._templates)
        total_compositions = len(self._compositions)

        by_category: Dict[str, int] = {}
        for cat_val, skill_ids in self._skill_by_category.items():
            by_category[cat_val] = len(skill_ids)

        by_complexity: Dict[str, int] = {}
        for cl_val, skill_ids in self._skill_by_complexity.items():
            by_complexity[cl_val] = len(skill_ids)

        avg_confidence = 0.0
        if total_skills > 0:
            avg_confidence = round(
                sum(s.confidence for s in self._skills.values()) / total_skills, 4
            )

        avg_params = 0.0
        if total_skills > 0:
            avg_params = round(
                sum(len(s.parameters) for s in self._skills.values()) / total_skills, 2
            )

        return {
            "total_skills": total_skills,
            "total_templates": total_templates,
            "total_compositions": total_compositions,
            "skills_by_category": by_category,
            "skills_by_complexity": by_complexity,
            "average_confidence": avg_confidence,
            "average_parameters_per_skill": avg_params,
            "skills_generated_lifetime": self._total_skills_generated,
            "templates_created_lifetime": self._total_templates_created,
            "compositions_formed_lifetime": self._total_compositions_formed,
            "skills_composed_lifetime": self._total_skills_composed,
            "skills_decomposed_lifetime": self._total_skills_decomposed,
            "skills_adapted_lifetime": self._total_skills_adapted,
            "skill_trees_generated_lifetime": self._total_skill_trees_generated,
            "batches_processed_lifetime": self._total_batches_processed,
            "refinements_applied_lifetime": self._total_refinements_applied,
            "max_skills": self.MAX_SKILLS,
            "max_templates": self.MAX_TEMPLATES,
            "max_compositions": self.MAX_COMPOSITIONS,
        }

    def list_skills(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._skills.values()]

    def list_templates(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._templates.values()]

    def get_skill(self, skill_id: str) -> Optional[GeneratedSkill]:
        """Retrieve a generated skill by its ID."""
        return self._skills.get(skill_id)

    def get_skill_by_name(self, name: str) -> Optional[GeneratedSkill]:
        """Retrieve a generated skill by its name."""
        sid = self._skill_name_index.get(name)
        if sid:
            return self._skills.get(sid)
        return None

    def get_template(self, template_id: str) -> Optional[SkillTemplate]:
        """Retrieve a skill template by its ID."""
        return self._templates.get(template_id)

    def get_composition(self, composition_id: str) -> Optional[SkillComposition]:
        """Retrieve a skill composition by its ID."""
        return self._compositions.get(composition_id)

    def list_skills_by_category(
        self, category: SkillCategory, limit: int = 50
    ) -> List[GeneratedSkill]:
        """List all skills in a given category."""
        ids = self._skill_by_category.get(category.value, [])
        return [self._skills[i] for i in ids[:limit] if i in self._skills]

    def list_skills_by_complexity(
        self, complexity: ComplexityLevel, limit: int = 50
    ) -> List[GeneratedSkill]:
        """List all skills at a given complexity level."""
        ids = self._skill_by_complexity.get(complexity.value, [])
        return [self._skills[i] for i in ids[:limit] if i in self._skills]

    def list_templates_by_category(
        self, category: SkillCategory, limit: int = 50
    ) -> List[SkillTemplate]:
        """List all templates in a given category."""
        ids = self._template_by_category.get(category.value, [])
        return [self._templates[i] for i in ids[:limit] if i in self._templates]

    def reset(self) -> None:
        """Reset the entire skill generator state."""
        with self._lock:
            self._skills.clear()
            self._templates.clear()
            self._compositions.clear()
            self._skill_by_category.clear()
            self._skill_by_complexity.clear()
            self._template_by_category.clear()
            self._composition_by_output.clear()
            self._skill_name_index.clear()
            for cat in SkillCategory:
                self._skill_by_category[cat.value] = []
                self._template_by_category[cat.value] = []
            for cl in ComplexityLevel:
                self._skill_by_complexity[cl.value] = []
            self._total_skills_generated = 0
            self._total_templates_created = 0
            self._total_compositions_formed = 0
            self._total_skills_composed = 0
            self._total_skills_decomposed = 0
            self._total_skills_adapted = 0
            self._total_skill_trees_generated = 0
            self._total_batches_processed = 0
            self._total_refinements_applied = 0

    def _infer_category(
        self, description: str, rng: random.Random
    ) -> SkillCategory:
        _time_module.sleep(0.001)
        desc_lower = description.lower()

        keyword_map: Dict[SkillCategory, List[str]] = {
            SkillCategory.COMBAT: [
                "attack", "damage", "weapon", "fight", "battle", "war", "strike",
                "combat", "slash", "hit", "defense", "armor", "shield",
            ],
            SkillCategory.CRAFTING: [
                "craft", "forge", "build", "create", "make", "construct",
                "recipe", "material", "smith", "assemble",
            ],
            SkillCategory.SOCIAL: [
                "talk", "speak", "negotiate", "persuade", "charm", "convince",
                "social", "conversation", "dialogue", "rumor",
            ],
            SkillCategory.EXPLORATION: [
                "explore", "discover", "scout", "find", "search", "reveal",
                "map", "terrain", "navigation", "travel",
            ],
            SkillCategory.STEALTH: [
                "stealth", "sneak", "hide", "invisible", "shadow",
                "silent", "pickpocket", "disguise", "camouflage",
            ],
            SkillCategory.MAGIC: [
                "magic", "spell", "mana", "arcane", "elemental", "sorcery",
                "enchant", "ritual", "wizard", "mage",
            ],
            SkillCategory.TECHNOLOGY: [
                "tech", "robot", "cyber", "hack", "drone", "device",
                "engineer", "circuit", "digital", "program",
            ],
            SkillCategory.SURVIVAL: [
                "survive", "endure", "resist", "heal", "recover",
                "weather", "fire", "shelter", "food", "water",
            ],
            SkillCategory.LEADERSHIP: [
                "lead", "command", "rally", "inspire", "direct",
                "manage", "delegate", "formation", "tactics",
            ],
            SkillCategory.DIPLOMACY: [
                "diplomacy", "treaty", "alliance", "peace", "negotiate",
                "trade", "faction", "politics", "ambassador",
            ],
        }

        scored: List[Tuple[SkillCategory, int]] = []
        for cat, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if kw in desc_lower)
            if score > 0:
                scored.append((cat, score))

        if scored:
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[0][0]

        return rng.choice(SKILL_CATEGORY_POOL)

    def _infer_complexity(
        self, description: str, rng: random.Random
    ) -> ComplexityLevel:
        _time_module.sleep(0.001)
        desc_lower = description.lower()

        high_indicators = [
            "master", "legendary", "ultimate", "supreme", "godlike",
            "devastating", "cataclysmic", "perfect", "complete",
        ]
        advanced_indicators = [
            "advanced", "expert", "elite", "superior", "powerful",
            "complex", "sophisticated", "intricate",
        ]
        intermediate_indicators = [
            "intermediate", "moderate", "improved", "enhanced",
            "strengthened", "developed",
        ]
        basic_indicators = [
            "basic", "simple", "fundamental", "beginner", "novice",
            "starter", "initial", "entry",
        ]

        if any(ind in desc_lower for ind in high_indicators):
            return rng.choice([ComplexityLevel.MASTER, ComplexityLevel.LEGENDARY])
        if any(ind in desc_lower for ind in advanced_indicators):
            return rng.choice(
                [ComplexityLevel.ADVANCED, ComplexityLevel.EXPERT]
            )
        if any(ind in desc_lower for ind in intermediate_indicators):
            return ComplexityLevel.INTERMEDIATE
        if any(ind in desc_lower for ind in basic_indicators):
            return ComplexityLevel.BASIC

        return rng.choice(
            [
                ComplexityLevel.BASIC,
                ComplexityLevel.BASIC,
                ComplexityLevel.INTERMEDIATE,
                ComplexityLevel.ADVANCED,
            ]
        )

    def _generate_skill_name(
        self, category: SkillCategory, rng: random.Random
    ) -> str:
        _time_module.sleep(0.001)
        pool = SKILL_NAMES.get(category, SKILL_NAMES[SkillCategory.COMBAT])
        if not pool:
            return f"Skill-{category.value}-{self._total_skills_generated + 1:04d}"

        name, _ = rng.choice(pool)
        return name

    def _derive_description(
        self, name: str, category: SkillCategory, complexity: ComplexityLevel
    ) -> str:
        _time_module.sleep(0.001)
        pool = SKILL_NAMES.get(category, SKILL_NAMES[SkillCategory.COMBAT])
        for skill_name, desc in pool:
            if skill_name == name:
                return f"[{complexity.value}] {desc}"
        return f"A {complexity.value} {category.value} skill"

    def _generate_prerequisites(
        self,
        category: SkillCategory,
        complexity: ComplexityLevel,
        rng: random.Random,
    ) -> List[str]:
        _time_module.sleep(0.001)
        required = COMPLEXITY_WEIGHTS[complexity]["prerequisite_count"]
        pool = PREREQUISITE_POOL.get(category, PREREQUISITE_POOL[SkillCategory.COMBAT])
        if not pool:
            return []
        rng.shuffle(pool)
        return pool[:required]

    def _generate_training_data(
        self, category: SkillCategory, rng: random.Random
    ) -> List[str]:
        _time_module.sleep(0.001)
        pool = TRAINING_DATA_TEMPLATES.get(
            category, TRAINING_DATA_TEMPLATES[SkillCategory.COMBAT]
        )
        rng.shuffle(pool)
        return pool[: rng.randint(1, min(4, len(pool)))]

    def _generate_parameters(
        self,
        category: SkillCategory,
        complexity: ComplexityLevel,
        rng: random.Random,
    ) -> List[Dict[str, Any]]:
        _time_module.sleep(0.001)
        weights = COMPLEXITY_WEIGHTS[complexity]
        param_range = weights["param_count_range"]
        param_count = rng.randint(param_range[0], param_range[1])

        generic_params = PARAMETER_TEMPLATES.get("generic", [])
        category_params = PARAMETER_TEMPLATES.get(category, [])

        all_params = list(category_params)
        for gp in generic_params:
            if gp["name"] not in {p["name"] for p in all_params}:
                all_params.append(gp)

        rng.shuffle(all_params)
        selected = all_params[: min(param_count, len(all_params))]

        result: List[Dict[str, Any]] = []
        seen: set = set()
        for param in selected:
            name = param.get("name", "")
            if name in seen:
                continue
            seen.add(name)
            copy = dict(param)
            if copy.get("type") == "float":
                copy["default"] = round(
                    copy.get("default", 0.0) * rng.uniform(0.7, 1.3), 2
                )
                copy["default"] = max(
                    copy.get("min", 0.0),
                    min(copy.get("max", float("inf")), copy["default"]),
                )
            result.append(copy)

        return result

    def _derive_default_actions(
        self, category: SkillCategory, rng: random.Random
    ) -> List[Dict[str, Any]]:
        _time_module.sleep(0.001)
        action_sets: Dict[SkillCategory, List[Dict[str, Any]]] = {
            SkillCategory.COMBAT: [
                {"action": "execute_attack", "target": "enemy", "priority": "high"},
                {"action": "calculate_damage", "formula": "base_damage * (1 + power_scale)", "priority": "critical"},
                {"action": "apply_status_effects", "status_list": [], "priority": "medium"},
            ],
            SkillCategory.MAGIC: [
                {"action": "consume_mana", "amount": "mana_cost", "priority": "high"},
                {"action": "cast_effect", "type": "elemental_type", "priority": "critical"},
                {"action": "trigger_cooldown", "duration": "cooldown_seconds", "priority": "high"},
            ],
            SkillCategory.CRAFTING: [
                {"action": "check_resources", "required": [], "priority": "high"},
                {"action": "execute_craft", "recipe": "selected_recipe", "priority": "critical"},
                {"action": "apply_quality_bonus", "factor": "material_quality", "priority": "medium"},
            ],
            SkillCategory.SOCIAL: [
                {"action": "initiate_dialogue", "target": "npc", "priority": "high"},
                {"action": "perform_check", "skill": "persuasion", "priority": "critical"},
                {"action": "update_reputation", "amount": "reputation_cost", "priority": "medium"},
            ],
            SkillCategory.EXPLORATION: [
                {"action": "scan_environment", "radius": "detection_radius", "priority": "high"},
                {"action": "reveal_points", "type": "hidden", "priority": "critical"},
                {"action": "update_map", "detail": "cartographer", "priority": "low"},
            ],
            SkillCategory.STEALTH: [
                {"action": "calculate_detection", "vs": "detection_threshold", "priority": "high"},
                {"action": "reduce_visibility", "factor": "visibility_modifier", "priority": "critical"},
                {"action": "execute_stealth_action", "noise": "noise_level", "priority": "high"},
            ],
            SkillCategory.TECHNOLOGY: [
                {"action": "power_on_device", "consumption": "power_consumption", "priority": "high"},
                {"action": "execute_tech_effect", "level": "tech_level", "priority": "critical"},
                {"action": "check_stability", "threshold": "system_stability", "priority": "medium"},
            ],
            SkillCategory.SURVIVAL: [
                {"action": "assess_condition", "severity": "current_hazard", "priority": "high"},
                {"action": "apply_survival_skill", "efficiency": "resource_efficiency", "priority": "critical"},
                {"action": "recover_endurance", "amount": "endurance_bonus", "priority": "medium"},
            ],
            SkillCategory.LEADERSHIP: [
                {"action": "evaluate_formation", "followers": "follower_cap", "priority": "high"},
                {"action": "issue_command", "type": "tactical", "priority": "critical"},
                {"action": "boost_morale", "amount": "morale_boost", "priority": "medium"},
            ],
            SkillCategory.DIPLOMACY: [
                {"action": "assess_standing", "faction": "target_faction", "priority": "high"},
                {"action": "negotiate_terms", "duration": "treaty_duration", "priority": "critical"},
                {"action": "apply_trade_discount", "amount": "trade_discount", "priority": "low"},
            ],
        }
        return action_sets.get(category, [
            {"action": "execute_skill", "priority": "critical"},
            {"action": "consume_resources", "amount": "resource_cost", "priority": "high"},
        ])

    def _derive_constraints(
        self, category: SkillCategory, rng: random.Random
    ) -> List[Dict[str, Any]]:
        _time_module.sleep(0.001)
        base_constraints: List[Dict[str, Any]] = [
            {"type": "cooldown_minimum", "value": 1.0, "description": "Minimum cooldown in seconds"},
            {"type": "requires_line_of_sight", "value": True, "description": "Skill requires line of sight to target"},
        ]

        category_constraints: Dict[SkillCategory, List[Dict[str, Any]]] = {
            SkillCategory.COMBAT: [
                {"type": "requires_weapon", "value": True, "description": "Must have a weapon equipped"},
                {"type": "max_targets", "value": 5, "description": "Maximum number of targets per use"},
            ],
            SkillCategory.MAGIC: [
                {"type": "requires_mana", "value": True, "description": "Must have sufficient mana"},
                {"type": "cannot_silence", "value": True, "description": "Cannot be used while silenced"},
            ],
            SkillCategory.CRAFTING: [
                {"type": "requires_workshop", "value": True, "description": "Must be at a crafting station"},
                {"type": "max_quality", "value": 100, "description": "Upper quality cap"},
            ],
            SkillCategory.SOCIAL: [
                {"type": "requires_npc_nearby", "value": True, "description": "Must have NPC within range"},
                {"type": "min_reputation", "value": -50, "description": "Minimum reputation threshold"},
            ],
            SkillCategory.EXPLORATION: [
                {"type": "requires_outdoors", "value": False, "description": "Can be used indoors or outdoors"},
                {"type": "max_elevation", "value": 5000, "description": "Maximum elevation for use"},
            ],
            SkillCategory.STEALTH: [
                {"type": "not_in_combat", "value": True, "description": "Cannot be used during active combat"},
                {"type": "max_light_level", "value": 0.8, "description": "Maximum ambient light level"},
            ],
            SkillCategory.TECHNOLOGY: [
                {"type": "requires_power", "value": True, "description": "Requires power source"},
                {"type": "max_emp_interference", "value": 0.3, "description": "Maximum EMP interference level"},
            ],
            SkillCategory.SURVIVAL: [
                {"type": "max_hazard_severity", "value": 5, "description": "Maximum hazard severity applicable"},
                {"type": "requires_resource", "value": True, "description": "Requires consumable resources"},
            ],
            SkillCategory.LEADERSHIP: [
                {"type": "min_followers", "value": 1, "description": "Minimum followers required"},
                {"type": "max_command_range", "value": 300, "description": "Maximum command range in meters"},
            ],
            SkillCategory.DIPLOMACY: [
                {"type": "requires_neutral_standing", "value": True, "description": "Must not be at war"},
                {"type": "max_treaty_duration", "value": 3600, "description": "Maximum treaty duration in seconds"},
            ],
        }

        specific = category_constraints.get(category, [])
        return base_constraints + specific

    def _derive_examples(
        self, category: SkillCategory, rng: random.Random
    ) -> List[Dict[str, Any]]:
        _time_module.sleep(0.001)
        pool = SKILL_NAMES.get(category, SKILL_NAMES[SkillCategory.COMBAT])
        examples: List[Dict[str, Any]] = []
        sample_size = min(3, len(pool))
        for name, desc in rng.sample(pool, sample_size):
            examples.append({
                "skill_name": name,
                "description": desc,
                "category": category.value,
            })
        return examples

    def _compute_composition_synergy(
        self,
        skills: List[GeneratedSkill],
        dominant: SkillCategory,
    ) -> float:
        _time_module.sleep(0.001)
        if len(skills) < 2:
            return 0.0

        total = 0.0
        count = 0
        for i, skill_a in enumerate(skills):
            for skill_b in skills[i + 1:]:
                pair_synergy = 0.0

                synergy_row = CATEGORY_SYNERGY_MATRIX.get(
                    skill_a.category, {}
                )
                pair_synergy += synergy_row.get(skill_b.category, 0.0) * 0.3

                synergy_row_b = CATEGORY_SYNERGY_MATRIX.get(
                    skill_b.category, {}
                )
                pair_synergy += synergy_row_b.get(skill_a.category, 0.0) * 0.3

                complexity_diff = abs(
                    list(ComplexityLevel).index(skill_a.complexity)
                    - list(ComplexityLevel).index(skill_b.complexity)
                )
                pair_synergy += max(0.0, 1.0 - complexity_diff * 0.15) * 0.2

                param_names_a = {p.get("name") for p in skill_a.parameters}
                param_names_b = {p.get("name") for p in skill_b.parameters}
                if param_names_a and param_names_b:
                    overlap = len(param_names_a & param_names_b) / max(
                        len(param_names_a | param_names_b), 1
                    )
                    pair_synergy += (1.0 - overlap) * 0.2

                total += pair_synergy
                count += 1

        if count == 0:
            return 0.0
        return min(1.0, total / count)

    def _derive_composition_complexity(
        self, skills: List[GeneratedSkill]
    ) -> ComplexityLevel:
        _time_module.sleep(0.001)
        if not skills:
            return ComplexityLevel.BASIC

        complexities = list(ComplexityLevel)
        max_index = max(complexities.index(s.complexity) for s in skills)
        avg_index = sum(complexities.index(s.complexity) for s in skills) / len(skills)
        adjusted = int(math.ceil((max_index + avg_index) / 2))
        adjusted = min(adjusted, len(complexities) - 1)
        return complexities[adjusted]

    def _compute_balance_score(
        self, skill: GeneratedSkill, rng: random.Random
    ) -> float:
        _time_module.sleep(0.001)
        score = 0.5

        if skill.parameters:
            param_values = []
            for p in skill.parameters:
                if p.get("type") in ("float", "int"):
                    default_val = p.get("default", 0)
                    min_val = p.get("min", 0)
                    max_val = p.get("max", 1)
                    if max_val > min_val:
                        normalized = (default_val - min_val) / (max_val - min_val)
                        param_values.append(normalized)
            if param_values:
                avg_normalized = sum(param_values) / len(param_values)
                spread = abs(avg_normalized - 0.5)
                score += (0.5 - spread) * 0.4

        weights = COMPLEXITY_WEIGHTS[skill.complexity]
        expected_prereqs = weights["prerequisite_count"]
        actual_prereqs = len(skill.prerequisites)
        prereq_deviation = abs(expected_prereqs - actual_prereqs) / max(
            expected_prereqs, 1
        )
        score -= prereq_deviation * 0.3

        score *= rng.uniform(0.85, 1.15)
        return max(0.0, min(1.0, score))

    def _compute_viability_score(
        self, skill: GeneratedSkill, rng: random.Random
    ) -> float:
        _time_module.sleep(0.001)
        score = skill.confidence * 0.4

        weights = COMPLEXITY_WEIGHTS[skill.complexity]
        expected_params = sum(weights["param_count_range"]) / 2
        actual_params = len(skill.parameters)
        if expected_params > 0:
            param_ratio = min(actual_params / expected_params, 2.0)
            score += param_ratio * 0.25

        if skill.training_data:
            score += min(len(skill.training_data) / 5.0, 1.0) * 0.15

        if skill.output_schema:
            schema_fields = len(skill.output_schema.get("fields", []))
            score += min(schema_fields / 4.0, 1.0) * 0.1

        score += rng.uniform(0.0, 0.1)
        return max(0.0, min(1.0, score))

    def _compute_context_synergy(
        self,
        skill: GeneratedSkill,
        context: Optional[Dict[str, Any]],
        rng: random.Random,
    ) -> float:
        _time_module.sleep(0.001)
        if context is None:
            return 0.5

        score = 0.5

        if "target_category" in context:
            target_cat = context["target_category"]
            if isinstance(target_cat, str):
                synergy_row = CATEGORY_SYNERGY_MATRIX.get(skill.category, {})
                for cat in SkillCategory:
                    if cat.value == target_cat:
                        score += synergy_row.get(cat, 0.0) * 0.5
                        break

        if "expected_complexity" in context:
            expected_cl = context["expected_complexity"]
            if isinstance(expected_cl, str):
                for cl in ComplexityLevel:
                    if cl.value == expected_cl:
                        diff = abs(
                            list(ComplexityLevel).index(skill.complexity)
                            - list(ComplexityLevel).index(cl)
                        )
                        score -= diff * 0.1
                        break

        if "required_params" in context:
            required = set(context["required_params"])
            skill_params = {p.get("name", "") for p in skill.parameters}
            if required:
                coverage = len(required & skill_params) / len(required)
                score += coverage * 0.3

        score *= rng.uniform(0.9, 1.1)
        return max(0.0, min(1.0, score))

    def _weighted_choice(
        self, rng: random.Random, distribution: Dict[Any, float]
    ) -> Any:
        _time_module.sleep(0.001)
        items = list(distribution.items())
        if not items:
            return None
        total = sum(weight for _, weight in items)
        if total <= 0:
            return items[0][0]
        roll = rng.uniform(0, total)
        cumulative = 0.0
        for key, weight in items:
            cumulative += weight
            if roll <= cumulative:
                return key
        return items[-1][0]

    def _tree_node_info(
        self, skill: GeneratedSkill, layer: int
    ) -> Dict[str, Any]:
        return {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "category": skill.category.value,
            "complexity": skill.complexity.value,
            "layer": layer,
            "parameter_count": len(skill.parameters),
            "prerequisite_count": len(skill.prerequisites),
            "confidence": round(skill.confidence, 4),
        }

    def _bump_version(self, version: str) -> str:
        _time_module.sleep(0.001)
        parts = version.split(".")
        if len(parts) < 2:
            return f"{version}.1"
        minor = int(parts[-1]) + 1
        parts[-1] = str(minor)
        return ".".join(parts)

    def _evict_oldest_skills(self) -> None:
        _time_module.sleep(0.001)
        excess = len(self._skills) - self.MAX_SKILLS
        if excess <= 0:
            return
        sorted_skills = sorted(
            self._skills.items(),
            key=lambda kv: (kv[1].confidence, kv[1].created_at),
        )
        for skill_id, skill in sorted_skills[:excess]:
            self._skills.pop(skill_id, None)
            self._skill_name_index.pop(skill.name, None)
            cat_list = self._skill_by_category.get(skill.category.value, [])
            if skill_id in cat_list:
                cat_list.remove(skill_id)
            cl_list = self._skill_by_complexity.get(skill.complexity.value, [])
            if skill_id in cl_list:
                cl_list.remove(skill_id)

    def _evict_oldest_templates(self) -> None:
        _time_module.sleep(0.001)
        excess = len(self._templates) - self.MAX_TEMPLATES
        if excess <= 0:
            return
        sorted_templates = sorted(
            self._templates.items(),
            key=lambda kv: kv[1].created_at,
        )
        for tid, template in sorted_templates[:excess]:
            self._templates.pop(tid, None)
            cat_list = self._template_by_category.get(template.category.value, [])
            if tid in cat_list:
                cat_list.remove(tid)

    def _evict_oldest_compositions(self) -> None:
        _time_module.sleep(0.001)
        excess = len(self._compositions) - self.MAX_COMPOSITIONS
        if excess <= 0:
            return
        sorted_compositions = sorted(
            self._compositions.items(),
            key=lambda kv: (kv[1].synergy_score, kv[1].created_at),
        )
        for cid, composition in sorted_compositions[:excess]:
            self._compositions.pop(cid, None)
            self._composition_by_output.pop(composition.output_skill_id, None)


def get_skill_generator() -> AgentSkillGenerator:
    """Return the singleton AgentSkillGenerator instance."""
    return AgentSkillGenerator.get_instance()