"""
SparkLabs Agent - Autonomous Creator Engine

AI-driven autonomous content generation system for the SparkLabs AI-native game
engine. Generates game content including levels, quests, NPCs, items, and
mechanics without human intervention. Combines procedural generation with
AI-driven design decisions to produce coherent, theme-consistent game content
at scale.

Architecture:
  AutonomousCreatorEngine (Singleton)
    |-- ContentCategory (classification of content types)
    |-- GenerationStrategy (algorithmic approach selection)
    |-- ContentQuality (lifecycle quality states)
    |-- ComplexityLevel (content scope and depth tiers)
    |-- ThemeCategory (narrative and aesthetic themes)
    |-- ContentSpec (generation request specification)
    |-- GeneratedContent (output wrapper with metadata)
    |-- LevelBlueprint (room layout and enemy placement)
    |-- QuestDefinition (objectives, rewards, branching)
    |-- NPCProfile (personality, dialogue, behavior)
    |-- ItemTemplate (stats, rarity, crafting, lore)
    |-- CreatorSession (aggregated generation session)
    |-- LevelGenerator (blueprint and layout generation)
    |-- QuestGenerator (quest chain and branching creation)
    |-- NPCGenerator (personality and dialogue generation)
    |-- ItemGenerator (template creation with stats and lore)
    |-- MechanicDesigner (game mechanics and rules design)
    |-- ContentValidator (constraint and quality validation)
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import threading
import time as _time_module
import uuid
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# Enums
# =============================================================================


class ContentCategory(Enum):
    """Classification of game content types that can be autonomously generated."""
    LEVEL = "level"
    QUEST = "quest"
    NPC = "npc"
    ITEM = "item"
    MECHANIC = "mechanic"
    DIALOGUE = "dialogue"
    ENVIRONMENT = "environment"
    PUZZLE = "puzzle"
    BOSS = "boss"
    ACHIEVEMENT = "achievement"


class GenerationStrategy(Enum):
    """Algorithmic approach for content generation."""
    RULE_BASED = "rule_based"
    TEMPLATE_DRIVEN = "template_driven"
    PROCEDURAL = "procedural"
    AI_GENERATED = "ai_generated"
    HYBRID = "hybrid"
    EVOLUTIONARY = "evolutionary"


class ContentQuality(Enum):
    """Lifecycle states tracking content quality progression."""
    DRAFT = "draft"
    REVIEWED = "reviewed"
    POLISHED = "polished"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class ComplexityLevel(Enum):
    """Tiers defining the scope and depth of generated content."""
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EPIC = "epic"


class ThemeCategory(Enum):
    """Narrative and aesthetic themes for content generation."""
    FANTASY = "fantasy"
    SCI_FI = "sci_fi"
    HORROR = "horror"
    MEDIEVAL = "medieval"
    MODERN = "modern"
    POST_APOCALYPTIC = "post_apocalyptic"
    STEAMPUNK = "steampunk"
    CYBERPUNK = "cyberpunk"


# =============================================================================
# Complexity scaling tables
# =============================================================================

COMPLEXITY_MULTIPLIERS: Dict[ComplexityLevel, float] = {
    ComplexityLevel.TRIVIAL: 0.25,
    ComplexityLevel.SIMPLE: 0.5,
    ComplexityLevel.MODERATE: 1.0,
    ComplexityLevel.COMPLEX: 2.0,
    ComplexityLevel.EPIC: 4.0,
}

COMPLEXITY_ROOM_RANGES: Dict[ComplexityLevel, Tuple[int, int]] = {
    ComplexityLevel.TRIVIAL: (1, 3),
    ComplexityLevel.SIMPLE: (3, 6),
    ComplexityLevel.MODERATE: (5, 10),
    ComplexityLevel.COMPLEX: (8, 18),
    ComplexityLevel.EPIC: (15, 35),
}

COMPLEXITY_OBJECTIVE_RANGES: Dict[ComplexityLevel, Tuple[int, int]] = {
    ComplexityLevel.TRIVIAL: (1, 1),
    ComplexityLevel.SIMPLE: (1, 2),
    ComplexityLevel.MODERATE: (2, 4),
    ComplexityLevel.COMPLEX: (3, 6),
    ComplexityLevel.EPIC: (5, 10),
}

COMPLEXITY_ITEM_COUNTS: Dict[ComplexityLevel, Tuple[int, int]] = {
    ComplexityLevel.TRIVIAL: (1, 3),
    ComplexityLevel.SIMPLE: (3, 6),
    ComplexityLevel.MODERATE: (5, 10),
    ComplexityLevel.COMPLEX: (8, 16),
    ComplexityLevel.EPIC: (12, 25),
}

# =============================================================================
# Generation data pools
# =============================================================================

ROOM_TYPES: List[str] = [
    "Entrance", "Corridor", "Chamber", "Arena", "Treasury",
    "Armory", "Library", "Throne Room", "Dungeon", "Laboratory",
    "Garden", "Observatory", "Catacombs", "Forge", "Sanctuary",
    "Barracks", "Kitchen", "Great Hall", "Prison", "Secret Passage",
]

ENEMY_TYPES: List[str] = [
    "Skeleton Warrior", "Shadow Assassin", "Fire Elemental", "Goblin Scout",
    "Dark Mage", "Iron Golem", "Vampire Thrall", "Crystal Spider",
    "Orc Berserker", "Wraith", "Venom Drake", "Clockwork Sentinel",
    "Blight Hound", "Storm Caller", "Bone Revenant", "Frost Giant",
]

TREASURE_TYPES: List[str] = [
    "Gold Coins", "Enchanted Gem", "Ancient Scroll", "Magic Ring",
    "Health Potion", "Mana Crystal", "Shadow Cloak", "Dragon Scale",
    "Phoenix Feather", "Runed Amulet", "Celestial Key", "Obsidian Shard",
    "Elixir of Power", "Mithril Ore", "Arcane Tome", "Thunderstone",
]

NPC_ROLES: List[str] = [
    "Blacksmith", "Merchant", "Guard Captain", "Innkeeper", "Scholar",
    "Alchemist", "Ranger", "Priest", "Thief", "Bard", "Knight",
    "Hunter", "Fisherman", "Miner", "Farmer", "Noble", "Beggar",
    "Spy", "Healer", "Sage",
]

PERSONALITY_POOL: List[str] = [
    "Brave", "Cautious", "Charismatic", "Cunning", "Curious",
    "Determined", "Diplomatic", "Fierce", "Generous", "Gruff",
    "Honorable", "Impulsive", "Loyal", "Mysterious", "Optimistic",
    "Pessimistic", "Pragmatic", "Reckless", "Sarcastic", "Stoic",
    "Suspicious", "Warm", "Wise", "Witty", "Zealous",
]

DIALOGUE_TEMPLATES: List[str] = [
    "Greetings, traveler. What brings you to these parts?",
    "I've been expecting someone like you. There's work to be done.",
    "Careful now — these lands are not what they used to be.",
    "You look like you could handle yourself. I have a proposition.",
    "Word travels fast. I heard about your deeds at {location}.",
    "The old legends speak of one who would come. Perhaps it is you.",
    "I don't trust easily, but you seem different from the others.",
    "There's a rumor going around about a hidden treasure nearby.",
    "My shop is open to all — as long as you have the coin.",
    "Stay awhile and listen. I have a story worth telling.",
]

ITEM_CATEGORIES: List[str] = [
    "Weapon", "Armor", "Consumable", "Material", "Quest Item",
    "Accessory", "Artifact", "Tool", "Key Item", "Treasure",
]

ITEM_RARITIES: List[str] = [
    "common", "uncommon", "rare", "epic", "legendary", "mythic",
]

RARITY_WEIGHTS: Dict[str, float] = {
    "common": 0.5, "uncommon": 1.0, "rare": 1.8,
    "epic": 3.0, "legendary": 5.0, "mythic": 8.0,
}

NPC_NAMES: List[str] = [
    "Aldric Stoneforge", "Brynn Willowbrook", "Cedric Darkwater",
    "Dorian Ashford", "Elara Moonshadow", "Fynn Ironvein",
    "Gareth Blackwood", "Helena Crestfall", "Isolde Dawnstrider",
    "Jorah Nightwind", "Kael Stormwind", "Lyra Thornfield",
    "Magnus Ebonhart", "Nyssa Jadeheart", "Orin Quickblade",
    "Petra Ravenwood", "Quinn Lightbringer", "Rowan Frostborne",
    "Seren Whitestone", "Thalia Grimward",
]

FACTION_NAMES: List[str] = [
    "The Iron Vanguard", "Arcane Consortium", "Shadow Syndicate",
    "Emerald Wardens", "Crimson Order", "Silver Dawn",
    "The Free Marches", "Obsidian Circle", "Golden Concordat",
    "Stormguard Legion", "The Unseen Hand", "Celestial Accord",
]

LOCATION_NAMES: List[str] = [
    "Whispering Woods", "Crimson Canyon", "Frostpeak Summit",
    "Sunken Catacombs", "Emberfall Village", "Ironhold Keep",
    "Shadowfen Marsh", "Thunder Ridge", "Silent Monastery",
    "The Drowned Harbor", "Obsidian Depths", "Verdant Hollow",
    "Ashwind Plateau", "Stormbreak Tower", "Goldenfields",
    "The Shattered Spire", "Mistveil Basin", "Cinderforge Mines",
    "Bleakshore Coast", "Starfall Observatory",
]

MECHANIC_TYPES: List[str] = [
    "Combat", "Movement", "Resource", "Social", "Crafting",
    "Puzzle", "Stealth", "Exploration", "Progression", "Economy",
]

MECHANIC_TEMPLATES: List[Dict[str, Any]] = [
    {"name": "Double Jump", "type": "Movement", "desc": "Allows a second jump while airborne.", "complexity": 0.3},
    {"name": "Combo System", "type": "Combat", "desc": "Chaining attacks increases damage multiplier.", "complexity": 0.6},
    {"name": "Crafting Grid", "type": "Crafting", "desc": "Combine materials in a grid to create items.", "complexity": 0.5},
    {"name": "Stealth Takedown", "type": "Stealth", "desc": "Silently eliminate unaware enemies from behind.", "complexity": 0.4},
    {"name": "Elemental Affinity", "type": "Combat", "desc": "Attacks gain elemental properties based on equipped gear.", "complexity": 0.7},
    {"name": "Dialogue Choice", "type": "Social", "desc": "Branching dialogue options that affect story outcomes.", "complexity": 0.5},
    {"name": "Resource Gathering", "type": "Resource", "desc": "Harvest materials from the environment for crafting.", "complexity": 0.2},
    {"name": "Lockpicking Minigame", "type": "Puzzle", "desc": "Interactive lockpicking challenge to open chests.", "complexity": 0.3},
    {"name": "Skill Tree", "type": "Progression", "desc": "Branching upgrade paths unlocked with experience points.", "complexity": 0.8},
    {"name": "Trading Economy", "type": "Economy", "desc": "Dynamic pricing based on supply and demand across regions.", "complexity": 0.6},
    {"name": "Wall Running", "type": "Movement", "desc": "Run along vertical surfaces for a short duration.", "complexity": 0.3},
    {"name": "Parry System", "type": "Combat", "desc": "Timed blocks that deflect attacks and stagger enemies.", "complexity": 0.5},
    {"name": "Enchanting", "type": "Crafting", "desc": "Imbue equipment with magical properties using reagents.", "complexity": 0.6},
    {"name": "Reputation System", "type": "Social", "desc": "Factions react to player actions with attitude changes.", "complexity": 0.7},
    {"name": "Day/Night Cycle", "type": "Exploration", "desc": "World changes based on time of day, affecting NPCs and enemies.", "complexity": 0.5},
]

ACHIEVEMENT_TEMPLATES: List[Dict[str, str]] = [
    {"title": "First Steps", "description": "Complete the tutorial quest."},
    {"title": "Treasure Hunter", "description": "Open 50 treasure chests."},
    {"title": "Slayer", "description": "Defeat 100 enemies."},
    {"title": "Master Crafter", "description": "Craft 25 unique items."},
    {"title": "Explorer", "description": "Discover all regions on the map."},
    {"title": "Social Butterfly", "description": "Befriend 10 NPCs."},
    {"title": "Boss Breaker", "description": "Defeat the first major boss."},
    {"title": "Completionist", "description": "Complete all side quests in a region."},
]

THEME_ENEMY_MAP: Dict[ThemeCategory, List[str]] = {
    ThemeCategory.FANTASY: ["Skeleton Warrior", "Dark Mage", "Orc Berserker", "Wraith", "Bone Revenant", "Goblin Scout"],
    ThemeCategory.SCI_FI: ["Robot Sentinel", "Alien Drone", "Plasma Trooper", "Hologram Guard", "Cyborg Assassin", "AI Construct"],
    ThemeCategory.HORROR: ["Wraith", "Vampire Thrall", "Blight Hound", "Crystal Spider", "Shadow Assassin", "Bone Revenant"],
    ThemeCategory.MEDIEVAL: ["Iron Golem", "Skeleton Warrior", "Orc Berserker", "Bandit Lord", "Knight Errant", "Frost Giant"],
    ThemeCategory.MODERN: ["Mercenary", "Gang Leader", "Riot Drone", "Hacker", "Sniper", "Armored Enforcer"],
    ThemeCategory.POST_APOCALYPTIC: ["Blight Hound", "Venom Drake", "Wasteland Raider", "Mutant Brute", "Scrap Golem", "Radiation Wraith"],
    ThemeCategory.STEAMPUNK: ["Clockwork Sentinel", "Iron Golem", "Steam Knight", "Gear Spider", "Automaton Guard", "Airship Pirate"],
    ThemeCategory.CYBERPUNK: ["Cyborg Enforcer", "Netrunner", "Drone Swarm", "Corporate Agent", "Augmented Samurai", "Data Wraith"],
}

THEME_LOCATION_MAP: Dict[ThemeCategory, List[str]] = {
    ThemeCategory.FANTASY: ["Whispering Woods", "Emberfall Village", "Shadowfen Marsh", "Verdant Hollow", "The Shattered Spire"],
    ThemeCategory.SCI_FI: ["Nebula Station", "Quantum Lab", "Deep Space Array", "Orbital Platform", "Xenobiology Dome"],
    ThemeCategory.HORROR: ["Sunken Catacombs", "Silent Monastery", "The Drowned Harbor", "Mistveil Basin", "Bleakshore Coast"],
    ThemeCategory.MEDIEVAL: ["Ironhold Keep", "Crimson Canyon", "Goldenfields", "Thunder Ridge", "Emberfall Village"],
    ThemeCategory.MODERN: ["Downtown District", "Industrial Zone", "Harbor Warehouse", "Suburban Heights", "Corporate Plaza"],
    ThemeCategory.POST_APOCALYPTIC: ["Ashwind Plateau", "The Shattered Spire", "Bleakshore Coast", "Cinderforge Mines", "Obsidian Depths"],
    ThemeCategory.STEAMPUNK: ["Cinderforge Mines", "Stormbreak Tower", "Ironhold Keep", "Clockwork Plaza", "Aether Docks"],
    ThemeCategory.CYBERPUNK: ["Neon District", "Data Spire", "Underground Grid", "Corporate Tower", "Chrome Alley"],
}


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class ContentSpec:
    """Specification for a content generation request.

    Defines the parameters that guide the autonomous generation process,
    including the type of content to create, the thematic framework,
    complexity level, constraints, and the generation strategy to employ.
    """
    spec_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    category: ContentCategory = ContentCategory.LEVEL
    theme: ThemeCategory = ThemeCategory.FANTASY
    complexity: ComplexityLevel = ComplexityLevel.MODERATE
    constraints: Dict[str, Any] = field(default_factory=dict)
    seed_phrase: str = ""
    generation_strategy: GenerationStrategy = GenerationStrategy.HYBRID
    output_format: str = "json"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "category": self.category.value,
            "theme": self.theme.value,
            "complexity": self.complexity.value,
            "constraints": self.constraints,
            "seed_phrase": self.seed_phrase,
            "generation_strategy": self.generation_strategy.value,
            "output_format": self.output_format,
        }


@dataclass
class GeneratedContent:
    """Wrapper for generated content with quality and performance metadata.

    Contains the result data from a generation operation along with
    quality assessment scores, generation timing, revision tracking,
    and dependency information for content relationship management.
    """
    content_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    spec: ContentSpec = field(default_factory=ContentSpec)
    result_data: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    generation_time_ms: float = 0.0
    revision_count: int = 0
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_id": self.content_id,
            "spec": self.spec.to_dict(),
            "result_data": self.result_data,
            "quality_score": self.quality_score,
            "generation_time_ms": self.generation_time_ms,
            "revision_count": self.revision_count,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "created_at": self.created_at,
        }


@dataclass
class LevelBlueprint:
    """Blueprint for a game level with room layout and enemy placement.

    Defines the spatial structure of a level including room count
    and types, enemy distribution across rooms, treasure placement,
    difficulty curve parameters, and room connectivity graph.
    """
    blueprint_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    theme: ThemeCategory = ThemeCategory.FANTASY
    room_count: int = 5
    enemy_distribution: Dict[str, int] = field(default_factory=dict)
    treasure_placement: Dict[str, List[str]] = field(default_factory=dict)
    difficulty_curve: List[float] = field(default_factory=list)
    connectivity_map: Dict[str, List[str]] = field(default_factory=dict)
    rooms: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blueprint_id": self.blueprint_id,
            "name": self.name,
            "theme": self.theme.value,
            "room_count": self.room_count,
            "enemy_distribution": self.enemy_distribution,
            "treasure_placement": self.treasure_placement,
            "difficulty_curve": self.difficulty_curve,
            "connectivity_map": self.connectivity_map,
            "rooms": self.rooms,
            "created_at": self.created_at,
        }


@dataclass
class QuestDefinition:
    """Definition of a quest with objectives, rewards, and branching paths.

    Specifies the complete quest structure including title, narrative
    description, sequential objectives, completion rewards, NPC
    relationships, prerequisites, story context, and branching options.
    """
    quest_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    objectives: List[Dict[str, Any]] = field(default_factory=list)
    rewards: Dict[str, Any] = field(default_factory=dict)
    npc_givers: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    story_context: str = ""
    branching_paths: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quest_id": self.quest_id,
            "title": self.title,
            "objectives": self.objectives,
            "rewards": self.rewards,
            "npc_givers": self.npc_givers,
            "prerequisites": self.prerequisites,
            "story_context": self.story_context,
            "branching_paths": self.branching_paths,
            "created_at": self.created_at,
        }


@dataclass
class NPCProfile:
    """Profile for a non-player character with personality and dialogue.

    Defines a complete NPC including name, role, personality traits,
    dialogue pool, behavior tree structure, faction affiliation, and
    narrative backstory for world-building.
    """
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    role: str = ""
    personality_traits: List[str] = field(default_factory=list)
    dialogue_pool: List[str] = field(default_factory=list)
    behavior_tree: Dict[str, Any] = field(default_factory=dict)
    faction: str = ""
    backstory: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "role": self.role,
            "personality_traits": self.personality_traits,
            "dialogue_pool": self.dialogue_pool,
            "behavior_tree": self.behavior_tree,
            "faction": self.faction,
            "backstory": self.backstory,
            "created_at": self.created_at,
        }


@dataclass
class ItemTemplate:
    """Template for a game item with stats, rarity, crafting, and lore.

    Defines a complete item including name, category, stat modifiers,
    rarity tier, crafting recipe if applicable, lore text for
    narrative flavor, and a visual description for rendering.
    """
    item_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: str = ""
    stats: Dict[str, float] = field(default_factory=dict)
    rarity: str = "common"
    crafting_recipe: Dict[str, Any] = field(default_factory=dict)
    lore_text: str = ""
    visual_description: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "category": self.category,
            "stats": self.stats,
            "rarity": self.rarity,
            "crafting_recipe": self.crafting_recipe,
            "lore_text": self.lore_text,
            "visual_description": self.visual_description,
            "created_at": self.created_at,
        }


@dataclass
class CreatorSession:
    """Aggregated session tracking all generated content from a creator run.

    Records all content items generated during a session, total
    generation time, strategy usage distribution, and quality
    distribution across all generated content.
    """
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    generated_contents: List[GeneratedContent] = field(default_factory=list)
    total_generation_time: float = 0.0
    strategy_usage: Dict[str, int] = field(default_factory=dict)
    quality_distribution: Dict[str, int] = field(default_factory=dict)
    started_at: float = field(default_factory=_time_module.time)
    completed_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "content_count": len(self.generated_contents),
            "total_generation_time": round(self.total_generation_time, 3),
            "strategy_usage": self.strategy_usage,
            "quality_distribution": self.quality_distribution,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# =============================================================================
# Generator Components
# =============================================================================


class LevelGenerator:
    """Generates level blueprints with room layouts and enemy placement.

    Creates procedurally generated level structures including room
    definitions, connectivity graphs, enemy distribution scaled to
    complexity, treasure placement, and difficulty curves.
    """

    def generate(self, theme: ThemeCategory, complexity: ComplexityLevel, rng: random.Random) -> LevelBlueprint:
        """Generate a complete level blueprint.

        Args:
            theme: Thematic category for the level's aesthetic.
            complexity: Complexity tier controlling room count and depth.
            rng: Seeded random number generator for deterministic output.

        Returns:
            A fully populated LevelBlueprint with rooms, enemies, and treasures.
        """
        min_rooms, max_rooms = COMPLEXITY_ROOM_RANGES.get(complexity, (3, 8))
        room_count = rng.randint(min_rooms, max_rooms)
        locations = THEME_LOCATION_MAP.get(theme, LOCATION_NAMES)
        location = rng.choice(locations)

        blueprint = LevelBlueprint(
            name=f"{location} - {complexity.value.title()} Level",
            theme=theme,
            room_count=room_count,
        )

        # Generate rooms
        room_types = rng.sample(ROOM_TYPES, min(room_count, len(ROOM_TYPES)))
        if len(room_types) < room_count:
            room_types += rng.choices(ROOM_TYPES, k=room_count - len(room_types))

        rooms: List[Dict[str, Any]] = []
        connectivity: Dict[str, List[str]] = {}
        enemies: Dict[str, int] = defaultdict(int)
        treasures: Dict[str, List[str]] = {}

        enemy_pool = THEME_ENEMY_MAP.get(theme, ENEMY_TYPES)
        multiplier = COMPLEXITY_MULTIPLIERS.get(complexity, 1.0)

        for i in range(room_count):
            room_id = f"room_{i}"
            room_type = room_types[i]
            enemy_count = max(0, int(rng.randint(1, 4) * multiplier))
            room_enemies = rng.choices(enemy_pool, k=enemy_count)

            for enemy in room_enemies:
                enemies[enemy] = enemies.get(enemy, 0) + 1

            treasure_count = rng.randint(0, 3)
            room_treasures = rng.sample(TREASURE_TYPES, min(treasure_count, len(TREASURE_TYPES)))
            treasures[room_id] = room_treasures

            rooms.append({
                "room_id": room_id,
                "type": room_type,
                "enemy_count": enemy_count,
                "enemies": room_enemies,
                "treasure_count": treasure_count,
                "treasures": room_treasures,
                "is_boss_room": (i == room_count - 1),
                "is_entrance": (i == 0),
            })

        # Build connectivity (linear with some branches)
        for i in range(room_count):
            conns: List[str] = []
            if i > 0:
                conns.append(f"room_{i - 1}")
            if i < room_count - 1:
                conns.append(f"room_{i + 1}")
            # Add occasional branching connections
            if i > 1 and rng.random() < 0.3:
                branch_target = rng.randint(0, i - 1)
                if f"room_{branch_target}" not in conns:
                    conns.append(f"room_{branch_target}")
            connectivity[f"room_{i}"] = conns

        # Difficulty curve (increasing toward boss room)
        difficulty_curve = []
        for i in range(room_count):
            progress = i / max(room_count - 1, 1)
            curve_value = 0.2 + (progress * 0.8)
            difficulty_curve.append(round(curve_value * multiplier, 2))

        blueprint.rooms = rooms
        blueprint.connectivity_map = dict(connectivity)
        blueprint.enemy_distribution = dict(enemies)
        blueprint.treasure_placement = treasures
        blueprint.difficulty_curve = difficulty_curve

        return blueprint


class QuestGenerator:
    """Generates quest chains with branching paths and rewards.

    Creates quests with theme-appropriate objectives, narrative
    context, NPC involvement, branching decision paths, and
    rewards scaled to complexity.
    """

    def generate(self, theme: ThemeCategory, complexity: ComplexityLevel, rng: random.Random) -> QuestDefinition:
        """Generate a complete quest definition.

        Args:
            theme: Thematic category for the quest's narrative.
            complexity: Complexity tier controlling objective count and branching.
            rng: Seeded random number generator for deterministic output.

        Returns:
            A fully populated QuestDefinition with objectives and rewards.
        """
        min_obj, max_obj = COMPLEXITY_OBJECTIVE_RANGES.get(complexity, (2, 4))
        objective_count = rng.randint(min_obj, max_obj)
        multiplier = COMPLEXITY_MULTIPLIERS.get(complexity, 1.0)

        location = rng.choice(THEME_LOCATION_MAP.get(theme, LOCATION_NAMES))
        giver = rng.choice(NPC_NAMES)

        quest_title_templates = [
            f"The Mystery of {location}",
            f"Shadows over {location}",
            f"Lost Treasures of {location}",
            f"The {theme.value.title()} Challenge",
            f"Echoes from {location}",
            f"Into the Depths",
            f"The Forgotten Path",
            f"Rise of the {rng.choice(['Ancient', 'Fallen', 'Lost', 'Dark'])} One",
        ]
        title = rng.choice(quest_title_templates)

        objectives: List[Dict[str, Any]] = []
        objective_types = ["explore", "collect", "defeat", "rescue", "investigate", "deliver", "activate", "protect"]

        for i in range(objective_count):
            obj_type = rng.choice(objective_types)
            obj_location = rng.choice(THEME_LOCATION_MAP.get(theme, LOCATION_NAMES))
            target_count = max(1, rng.randint(1, 5) * int(multiplier))

            obj = {
                "order": i + 1,
                "type": obj_type,
                "description": f"{obj_type.title()} {target_count} target(s) in {obj_location}",
                "target_count": target_count,
                "location": obj_location,
                "is_critical": (i == 0 or i == objective_count - 1),
            }
            objectives.append(obj)

        # Rewards
        rewards = {
            "experience": int(100 * objective_count * multiplier),
            "currency": int(50 * objective_count * multiplier),
            "items": rng.sample(TREASURE_TYPES, min(3, len(TREASURE_TYPES))),
            "reputation": {rng.choice(FACTION_NAMES): rng.randint(10, 50)},
        }

        # Branching paths
        branching_paths: List[Dict[str, Any]] = []
        if complexity in (ComplexityLevel.COMPLEX, ComplexityLevel.EPIC):
            branch_count = rng.randint(1, 3)
            for _ in range(branch_count):
                branching_paths.append({
                    "decision_point": f"After objective {rng.randint(1, max(1, objective_count - 1))}",
                    "option_a": f"Help the {rng.choice(['villagers', 'rebels', 'merchants', 'guards'])}",
                    "option_b": f"Side with the {rng.choice(['bandits', 'nobles', 'cultists', 'invaders'])}",
                    "consequence_a": rng.choice(["Gain ally support", "Receive rare item", "Open new area", "Faction loyalty"]),
                    "consequence_b": rng.choice(["Gain dark power", "Receive gold", "Secret knowledge", "Enemy becomes ally"]),
                })

        story_context = (
            f"In the {theme.value.replace('_', ' ')} realm of {location}, "
            f"{giver} seeks aid. A {rng.choice(['growing threat', 'ancient mystery', 'hidden danger', 'forgotten legend'])} "
            f"has emerged, and only a brave adventurer can unravel the truth."
        )

        return QuestDefinition(
            title=title,
            objectives=objectives,
            rewards=rewards,
            npc_givers=[giver],
            story_context=story_context,
            branching_paths=branching_paths,
        )


class NPCGenerator:
    """Generates NPC profiles with personalities and dialogue.

    Creates NPCs with role-appropriate names, personality traits,
    dialogue pools, behavior trees, faction affiliations, and
    narrative backstories.
    """

    def generate(self, theme: ThemeCategory, role: str, rng: random.Random) -> NPCProfile:
        """Generate a complete NPC profile.

        Args:
            theme: Thematic category influencing NPC flavor.
            role: Specific NPC role (e.g., Blacksmith, Merchant). Random if empty.
            rng: Seeded random number generator for deterministic output.

        Returns:
            A fully populated NPCProfile with personality and dialogue.
        """
        if not role:
            role = rng.choice(NPC_ROLES)

        name = rng.choice(NPC_NAMES)
        trait_count = rng.randint(3, 5)
        personality = rng.sample(PERSONALITY_POOL, min(trait_count, len(PERSONALITY_POOL)))

        # Dialogue pool
        dialogue_count = rng.randint(3, 6)
        dialogue_pool = rng.sample(DIALOGUE_TEMPLATES, min(dialogue_count, len(DIALOGUE_TEMPLATES)))
        location = rng.choice(THEME_LOCATION_MAP.get(theme, LOCATION_NAMES))
        dialogue_pool = [d.format(location=location) for d in dialogue_pool]

        # Behavior tree
        behavior_tree = {
            "idle": {
                "actions": rng.sample(["pace", "sit", "read", "tend_shop", "patrol", "meditate", "train"], 2),
                "transition_to": "greet" if rng.random() < 0.7 else "idle",
            },
            "greet": {
                "actions": ["greet_player", "play_dialogue"],
                "transition_to": "interact" if rng.random() < 0.8 else "idle",
            },
            "interact": {
                "actions": rng.sample(["offer_quest", "open_shop", "share_rumor", "give_advice", "tell_story"], 2),
                "transition_to": "idle",
            },
            "threatened": {
                "actions": ["flee", "call_guards"],
                "transition_to": "idle",
            },
        }

        faction = rng.choice(FACTION_NAMES)
        backstory = (
            f"A {role.lower()} living in {location}, {name} is known for being "
            f"{rng.choice(personality).lower()} and {rng.choice(personality).lower()}. "
            f"They have served the {faction} for {rng.randint(2, 20)} years and "
            f"{rng.choice(['keep many secrets', 'know everyone in town', 'dream of adventure', 'distrust outsiders'])}."
        )

        return NPCProfile(
            name=name,
            role=role,
            personality_traits=personality,
            dialogue_pool=dialogue_pool,
            behavior_tree=behavior_tree,
            faction=faction,
            backstory=backstory,
        )


class ItemGenerator:
    """Generates item templates with stats and lore.

    Creates items with rarity-scaled stats, theme-appropriate names,
    crafting recipes, narrative lore text, and visual descriptions
    for rendering systems.
    """

    def generate(self, theme: ThemeCategory, rarity: str, rng: random.Random) -> ItemTemplate:
        """Generate a complete item template.

        Args:
            theme: Thematic category influencing item flavor.
            rarity: Rarity tier controlling stat magnitude. Defaults to 'common'.
            rng: Seeded random number generator for deterministic output.

        Returns:
            A fully populated ItemTemplate with stats and lore.
        """
        if rarity not in ITEM_RARITIES:
            rarity = "common"

        category = rng.choice(ITEM_CATEGORIES)
        rarity_weight = RARITY_WEIGHTS.get(rarity, 1.0)

        # Generate stats
        stat_names = ["attack", "defense", "speed", "magic", "health", "stamina", "critical_chance", "durability"]
        stat_count = rng.randint(2, 5)
        selected_stats = rng.sample(stat_names, min(stat_count, len(stat_names)))
        stats = {
            stat: round(rng.uniform(1.0, 10.0) * rarity_weight, 1)
            for stat in selected_stats
        }

        # Item name
        rarity_prefixes = {
            "common": ["Rusty", "Worn", "Basic", "Simple", "Plain"],
            "uncommon": ["Fine", "Sturdy", "Polished", "Quality", "Reinforced"],
            "rare": ["Enchanted", "Arcane", "Mystical", "Runed", "Blessed"],
            "epic": ["Legendary", "Heroic", "Mythic", "Ancient", "Divine"],
            "legendary": ["Eternal", "Celestial", "Primordial", "Immortal", "Transcendent"],
            "mythic": ["Godforged", "Cosmic", "Infinite", "Absolute", "Void-Touched"],
        }
        item_bases = ["Sword", "Shield", "Staff", "Bow", "Armor", "Ring", "Amulet", "Blade", "Helm", "Gauntlets"]
        prefix = rng.choice(rarity_prefixes.get(rarity, rarity_prefixes["common"]))
        base = rng.choice(item_bases)
        item_name = f"{prefix} {base}"

        # Crafting recipe for non-common items
        crafting_recipe: Dict[str, Any] = {}
        if rarity not in ("common",):
            material_count = rng.randint(2, 4)
            materials = rng.sample(TREASURE_TYPES, min(material_count, len(TREASURE_TYPES)))
            crafting_recipe = {
                "materials": {mat: rng.randint(1, 5) for mat in materials},
                "required_level": max(1, int(rarity_weight * 5)),
                "crafting_time": round(rarity_weight * 2.0, 1),
            }

        # Lore text
        lore_templates = [
            f"Forged in the depths of {rng.choice(THEME_LOCATION_MAP.get(theme, LOCATION_NAMES))}, this {base.lower()} carries the weight of centuries.",
            f"A {base.lower()} once wielded by {rng.choice(['a forgotten hero', 'an ancient king', 'a dark lord', 'a wandering sage'])}, now lost to time.",
            f"Whispers say this {base.lower()} was blessed by the {rng.choice(FACTION_NAMES)} in a ritual that lasted {rng.randint(3, 9)} days.",
            f"Discovered in the ruins of {rng.choice(THEME_LOCATION_MAP.get(theme, LOCATION_NAMES))}, radiating an otherworldly aura.",
            f"Crafted by the master artisan {rng.choice(NPC_NAMES)} using techniques lost to the modern world.",
        ]
        lore_text = rng.choice(lore_templates)

        # Visual description
        visual_templates = [
            f"A {rarity} {category.lower()} with {rng.choice(['gleaming', 'weathered', 'ornate', 'smoldering', 'shimmering'])} surface and {rng.choice(['golden', 'silver', 'crimson', 'azure', 'ebony'])} accents.",
            f"Glowing runes pulse along the edges of this {rarity} {category.lower()}, casting faint {rng.choice(['blue', 'red', 'green', 'purple', 'gold'])} light.",
            f"This {rarity} {category.lower()} features intricate engravings depicting {rng.choice(['ancient battles', 'mythical creatures', 'celestial patterns', 'forgotten languages'])}.",
        ]
        visual_description = rng.choice(visual_templates)

        return ItemTemplate(
            name=item_name,
            category=category,
            stats=stats,
            rarity=rarity,
            crafting_recipe=crafting_recipe,
            lore_text=lore_text,
            visual_description=visual_description,
        )


class MechanicDesigner:
    """Designs game mechanics and rules.

    Creates game mechanics by selecting from template pools and
    customizing parameters based on theme and complexity. Supports
    combat, movement, crafting, social, puzzle, and economy mechanics.
    """

    def design(self, category: ContentCategory, theme: ThemeCategory, rng: random.Random) -> Dict[str, Any]:
        """Design a game mechanic appropriate for the given category and theme.

        Args:
            category: Content category determining the mechanic domain.
            theme: Thematic category influencing mechanic flavor.
            rng: Seeded random number generator for deterministic output.

        Returns:
            A dictionary with mechanic name, type, description, parameters, and rules.
        """
        theme_str = theme.value.replace("_", " ").title()

        # Filter mechanics relevant to the category
        type_map = {
            ContentCategory.MECHANIC: ["Combat", "Movement", "Resource", "Crafting", "Progression"],
            ContentCategory.PUZZLE: ["Puzzle", "Movement"],
            ContentCategory.BOSS: ["Combat", "Movement"],
            ContentCategory.LEVEL: ["Movement", "Exploration", "Combat"],
            ContentCategory.ENVIRONMENT: ["Exploration", "Movement", "Resource"],
        }
        relevant_types = type_map.get(category, ["Combat", "Movement", "Resource"])

        # Select from templates
        candidates = [m for m in MECHANIC_TEMPLATES if m["type"] in relevant_types]
        if not candidates:
            candidates = MECHANIC_TEMPLATES

        selected = rng.choice(candidates)
        complexity = selected["complexity"]

        # Generate parameters
        parameters = {
            "cooldown_seconds": round(rng.uniform(1.0, 15.0), 1),
            "power_cost": rng.randint(5, 50),
            "duration_seconds": round(rng.uniform(0.5, 10.0), 1) if complexity > 0.3 else 0.0,
            "unlock_level": rng.randint(1, 20),
            "max_level": rng.randint(1, 10),
            "scaling_factor": round(rng.uniform(0.5, 2.0), 2),
            "theme": theme_str,
        }

        # Generate rules
        rules = [
            f"Can be used every {parameters['cooldown_seconds']} seconds",
            f"Requires level {parameters['unlock_level']} to unlock",
            f"Scales at {parameters['scaling_factor']}x per upgrade level",
        ]
        if parameters["duration_seconds"] > 0:
            rules.append(f"Effect lasts {parameters['duration_seconds']} seconds")

        return {
            "mechanic_name": selected["name"],
            "mechanic_type": selected["type"],
            "description": selected["desc"],
            "parameters": parameters,
            "rules": rules,
            "category": category.value,
            "theme": theme.value,
            "creation_timestamp": _time_module.time(),
        }


class ContentValidator:
    """Validates generated content against constraints.

    Performs quality assessment on generated content by checking
    structural completeness, constraint satisfaction, theme
    consistency, and complexity appropriateness.
    """

    def validate(self, content: GeneratedContent) -> Dict[str, Any]:
        """Validate generated content against constraints and quality criteria.

        Args:
            content: The GeneratedContent instance to validate.

        Returns:
            A dictionary with validation results including score, issues, and verdict.
        """
        issues: List[str] = []
        score = 0.0
        max_score = 10.0

        # Check content has result data
        if not content.result_data:
            issues.append("Content has no result data")
            return {"valid": False, "score": 0.0, "issues": issues, "verdict": "rejected"}

        # Structural completeness checks per category
        category = content.spec.category
        result = content.result_data

        if category == ContentCategory.LEVEL:
            if "rooms" in result and len(result["rooms"]) > 0:
                score += 3.0
            else:
                issues.append("Level has no rooms")
            if "connectivity_map" in result and len(result["connectivity_map"]) > 0:
                score += 2.0
            else:
                issues.append("Level has no connectivity map")
            if "enemy_distribution" in result:
                score += 1.0
            if "treasure_placement" in result:
                score += 1.0
            if "difficulty_curve" in result and len(result.get("difficulty_curve", [])) > 0:
                score += 1.0

        elif category == ContentCategory.QUEST:
            if "objectives" in result and len(result["objectives"]) > 0:
                score += 3.0
            else:
                issues.append("Quest has no objectives")
            if "rewards" in result and result["rewards"]:
                score += 2.0
            if "story_context" in result and result["story_context"]:
                score += 2.0
            if "npc_givers" in result and result["npc_givers"]:
                score += 1.0

        elif category == ContentCategory.NPC:
            if "name" in result and result["name"]:
                score += 2.0
            if "personality_traits" in result and result["personality_traits"]:
                score += 2.0
            if "dialogue_pool" in result and result["dialogue_pool"]:
                score += 2.0
            if "behavior_tree" in result and result["behavior_tree"]:
                score += 1.0
            if "backstory" in result and result["backstory"]:
                score += 1.0

        elif category == ContentCategory.ITEM:
            if "stats" in result and result["stats"]:
                score += 3.0
            if "rarity" in result:
                score += 2.0
            if "lore_text" in result and result["lore_text"]:
                score += 1.0
            if "crafting_recipe" in result and result["crafting_recipe"]:
                score += 1.0

        elif category == ContentCategory.MECHANIC:
            if "mechanic_name" in result:
                score += 3.0
            if "parameters" in result and result["parameters"]:
                score += 3.0
            if "rules" in result and result["rules"]:
                score += 2.0

        else:
            # Generic content validation
            if len(result) > 0:
                score += min(5.0, len(result) * 0.5)
            else:
                issues.append("Content has empty result data")

        # Constraint checks
        constraints = content.spec.constraints
        for key, expected in constraints.items():
            if key in result:
                actual = result[key]
                if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                    if actual < expected * 0.5:
                        issues.append(f"Constraint '{key}': {actual} is below minimum {expected * 0.5}")
                elif isinstance(expected, str) and isinstance(actual, str):
                    if expected.lower() not in actual.lower():
                        issues.append(f"Constraint '{key}': expected '{expected}' not found")
                score += 0.5

        # Complexity appropriateness
        complexity_mult = COMPLEXITY_MULTIPLIERS.get(content.spec.complexity, 1.0)
        if complexity_mult > 1.0:
            if category == ContentCategory.LEVEL and len(result.get("rooms", [])) < 3:
                issues.append("Complex level has too few rooms")
            elif category == ContentCategory.QUEST and len(result.get("objectives", [])) < 2:
                issues.append("Complex quest has too few objectives")

        score = min(max_score, score)
        quality = score / max_score

        verdict = "accepted"
        if quality < 0.3:
            verdict = "rejected"
        elif quality < 0.6:
            verdict = "needs_revision"

        return {
            "valid": quality >= 0.3,
            "score": round(quality, 2),
            "raw_score": round(score, 1),
            "max_score": max_score,
            "issues": issues,
            "verdict": verdict,
            "content_id": content.content_id,
            "category": category.value,
            "complexity": content.spec.complexity.value,
            "validated_at": _time_module.time(),
        }


# =============================================================================
# AutonomousCreatorEngine (Singleton)
# =============================================================================


class AutonomousCreatorEngine:
    """Autonomous Creator Engine for AI-driven game content generation.

    Orchestrates all content generation subsystems including level
    generation, quest creation, NPC profiling, item template design,
    and mechanic definition. Combines procedural generation with
    AI-driven design decisions to produce coherent, theme-consistent
    game content autonomously without human intervention.

    Usage:
        creator = AutonomousCreatorEngine.get_instance()
        spec = ContentSpec(category=ContentCategory.LEVEL, theme=ThemeCategory.FANTASY)
        content = creator.create_content(spec)
        blueprint = creator.generate_level(ThemeCategory.FANTASY, ComplexityLevel.MODERATE)
        stats = creator.get_creator_stats()
    """

    _instance: Optional["AutonomousCreatorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_CONTENTS: int = 5000
    _MAX_SESSIONS: int = 200

    def __new__(cls) -> "AutonomousCreatorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AutonomousCreatorEngine":
        """Return the singleton AutonomousCreatorEngine instance, initializing if needed."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._contents: Dict[str, GeneratedContent] = {}
        self._sessions: Dict[str, CreatorSession] = {}
        self._level_generator = LevelGenerator()
        self._quest_generator = QuestGenerator()
        self._npc_generator = NPCGenerator()
        self._item_generator = ItemGenerator()
        self._mechanic_designer = MechanicDesigner()
        self._content_validator = ContentValidator()
        self._total_generated: int = 0
        self._total_validation_time: float = 0.0
        self._strategy_counts: Dict[str, int] = defaultdict(int)
        self._category_counts: Dict[str, int] = defaultdict(int)
        self._quality_scores: List[float] = []
        self._recent_actions: deque = deque(maxlen=100)

    # ------------------------------------------------------------------
    # Core Content Creation
    # ------------------------------------------------------------------

    def create_content(self, spec: ContentSpec) -> GeneratedContent:
        """Generate content based on the provided specification.

        Routes the specification to the appropriate generator based on
        content category, measures generation time, validates the result,
        and stores the generated content with quality metadata.

        Args:
            spec: ContentSpec defining what to generate and how.

        Returns:
            A GeneratedContent instance with result data and quality score.
        """
        with self._lock:
            self._enforce_max_contents()

            start_time = _time_module.time()
            seed = self._derive_seed(spec)
            rng = random.Random(seed)

            result_data: Dict[str, Any] = {}

            if spec.category == ContentCategory.LEVEL:
                blueprint = self._level_generator.generate(spec.theme, spec.complexity, rng)
                result_data = blueprint.to_dict()
            elif spec.category == ContentCategory.QUEST:
                quest = self._quest_generator.generate(spec.theme, spec.complexity, rng)
                result_data = quest.to_dict()
            elif spec.category == ContentCategory.NPC:
                role = spec.constraints.get("role", "")
                npc = self._npc_generator.generate(spec.theme, role, rng)
                result_data = npc.to_dict()
            elif spec.category == ContentCategory.ITEM:
                rarity = spec.constraints.get("rarity", "common")
                item = self._item_generator.generate(spec.theme, rarity, rng)
                result_data = item.to_dict()
            elif spec.category == ContentCategory.MECHANIC:
                mechanic = self._mechanic_designer.design(spec.category, spec.theme, rng)
                result_data = mechanic
            elif spec.category == ContentCategory.DIALOGUE:
                result_data = self._generate_dialogue(spec.theme, rng)
            elif spec.category == ContentCategory.ENVIRONMENT:
                result_data = self._generate_environment(spec.theme, spec.complexity, rng)
            elif spec.category == ContentCategory.PUZZLE:
                result_data = self._generate_puzzle(spec.theme, spec.complexity, rng)
            elif spec.category == ContentCategory.BOSS:
                result_data = self._generate_boss(spec.theme, spec.complexity, rng)
            elif spec.category == ContentCategory.ACHIEVEMENT:
                result_data = self._generate_achievement(spec.theme, rng)
            else:
                result_data = {"error": f"Unknown category: {spec.category.value}"}

            generation_time = round((_time_module.time() - start_time) * 1000, 2)

            tags = [
                spec.category.value,
                spec.theme.value,
                spec.complexity.value,
                spec.generation_strategy.value,
            ]

            content = GeneratedContent(
                spec=spec,
                result_data=result_data,
                generation_time_ms=generation_time,
                tags=tags,
            )

            # Validate
            validation = self._content_validator.validate(content)
            content.quality_score = validation["score"]

            self._contents[content.content_id] = content
            self._total_generated += 1
            self._strategy_counts[spec.generation_strategy.value] += 1
            self._category_counts[spec.category.value] += 1
            self._quality_scores.append(content.quality_score)

            self._recent_actions.append({
                "action": "create_content",
                "content_id": content.content_id,
                "category": spec.category.value,
                "theme": spec.theme.value,
                "quality_score": content.quality_score,
                "generation_time_ms": generation_time,
                "timestamp": _time_module.time(),
            })

            return content

    # ------------------------------------------------------------------
    # Specialized Generation Methods
    # ------------------------------------------------------------------

    def generate_level(
        self,
        theme: ThemeCategory = ThemeCategory.FANTASY,
        complexity: ComplexityLevel = ComplexityLevel.MODERATE,
        seed: str = "",
    ) -> LevelBlueprint:
        """Generate a level blueprint directly.

        Convenience method that creates a ContentSpec internally and
        returns the LevelBlueprint result directly.

        Args:
            theme: Thematic category for the level.
            complexity: Complexity tier controlling room count.
            seed: Optional seed phrase for deterministic generation.

        Returns:
            A fully populated LevelBlueprint.
        """
        spec = ContentSpec(
            category=ContentCategory.LEVEL,
            theme=theme,
            complexity=complexity,
            seed_phrase=seed,
            generation_strategy=GenerationStrategy.PROCEDURAL,
        )
        content = self.create_content(spec)
        return self._level_generator.generate(
            theme, complexity, random.Random(self._derive_seed(spec))
        )

    def generate_quest(
        self,
        theme: ThemeCategory = ThemeCategory.FANTASY,
        complexity: ComplexityLevel = ComplexityLevel.MODERATE,
        seed: str = "",
    ) -> QuestDefinition:
        """Generate a quest definition directly.

        Args:
            theme: Thematic category for the quest.
            complexity: Complexity tier controlling objectives.
            seed: Optional seed phrase for deterministic generation.

        Returns:
            A fully populated QuestDefinition.
        """
        spec = ContentSpec(
            category=ContentCategory.QUEST,
            theme=theme,
            complexity=complexity,
            seed_phrase=seed,
            generation_strategy=GenerationStrategy.TEMPLATE_DRIVEN,
        )
        self.create_content(spec)
        return self._quest_generator.generate(
            theme, complexity, random.Random(self._derive_seed(spec))
        )

    def generate_npc(
        self,
        theme: ThemeCategory = ThemeCategory.FANTASY,
        role: str = "",
        seed: str = "",
    ) -> NPCProfile:
        """Generate an NPC profile directly.

        Args:
            theme: Thematic category for the NPC.
            role: Specific NPC role. Random if empty.
            seed: Optional seed phrase for deterministic generation.

        Returns:
            A fully populated NPCProfile.
        """
        spec = ContentSpec(
            category=ContentCategory.NPC,
            theme=theme,
            complexity=ComplexityLevel.SIMPLE,
            seed_phrase=seed,
            constraints={"role": role},
            generation_strategy=GenerationStrategy.AI_GENERATED,
        )
        self.create_content(spec)
        return self._npc_generator.generate(
            theme, role, random.Random(self._derive_seed(spec))
        )

    def generate_item(
        self,
        theme: ThemeCategory = ThemeCategory.FANTASY,
        rarity: str = "common",
        seed: str = "",
    ) -> ItemTemplate:
        """Generate an item template directly.

        Args:
            theme: Thematic category for the item.
            rarity: Rarity tier (common, uncommon, rare, epic, legendary, mythic).
            seed: Optional seed phrase for deterministic generation.

        Returns:
            A fully populated ItemTemplate.
        """
        spec = ContentSpec(
            category=ContentCategory.ITEM,
            theme=theme,
            complexity=ComplexityLevel.SIMPLE,
            seed_phrase=seed,
            constraints={"rarity": rarity},
            generation_strategy=GenerationStrategy.TEMPLATE_DRIVEN,
        )
        self.create_content(spec)
        return self._item_generator.generate(
            theme, rarity, random.Random(self._derive_seed(spec))
        )

    def design_mechanic(
        self,
        category: ContentCategory = ContentCategory.MECHANIC,
        theme: ThemeCategory = ThemeCategory.FANTASY,
    ) -> Dict[str, Any]:
        """Design a game mechanic directly.

        Args:
            category: Content category determining the mechanic domain.
            theme: Thematic category for the mechanic.

        Returns:
            A dictionary with mechanic definition.
        """
        spec = ContentSpec(
            category=category,
            theme=theme,
            complexity=ComplexityLevel.MODERATE,
            generation_strategy=GenerationStrategy.RULE_BASED,
        )
        self.create_content(spec)
        return self._mechanic_designer.design(
            category, theme, random.Random(self._derive_seed(spec))
        )

    def validate_content(self, content: GeneratedContent) -> Dict[str, Any]:
        """Validate generated content and return quality assessment.

        Args:
            content: The GeneratedContent instance to validate.

        Returns:
            A dictionary with validation score, issues, and verdict.
        """
        with self._lock:
            start = _time_module.time()
            result = self._content_validator.validate(content)
            self._total_validation_time += _time_module.time() - start
            return result

    def batch_generate(self, specs: List[ContentSpec]) -> List[GeneratedContent]:
        """Generate content for multiple specifications in batch.

        Processes each spec sequentially, collecting all generated
        content items. Each spec produces independent content with
        its own seed-derived randomness.

        Args:
            specs: List of ContentSpec instances to process.

        Returns:
            List of GeneratedContent instances in the same order as specs.
        """
        results: List[GeneratedContent] = []
        for spec in specs:
            content = self.create_content(spec)
            results.append(content)
        return results

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def start_session(self) -> CreatorSession:
        """Start a new creator session for tracking batch generation.

        Returns:
            A new CreatorSession instance ready for content accumulation.
        """
        with self._lock:
            self._enforce_max_sessions()
            session = CreatorSession()
            self._sessions[session.session_id] = session
            return session

    def add_to_session(self, session_id: str, content: GeneratedContent) -> bool:
        """Add a generated content item to an existing session.

        Args:
            session_id: ID of the target session.
            content: GeneratedContent to add.

        Returns:
            True if the session was found and content added, False otherwise.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.generated_contents.append(content)
            session.total_generation_time += content.generation_time_ms
            strategy = content.spec.generation_strategy.value
            session.strategy_usage[strategy] = session.strategy_usage.get(strategy, 0) + 1
            quality_key = f"{content.quality_score:.1f}"
            session.quality_distribution[quality_key] = session.quality_distribution.get(quality_key, 0) + 1
            return True

    def complete_session(self, session_id: str) -> Optional[CreatorSession]:
        """Mark a session as complete and finalize its statistics.

        Args:
            session_id: ID of the session to complete.

        Returns:
            The completed CreatorSession, or None if not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.completed_at = _time_module.time()
            return session

    # ------------------------------------------------------------------
    # Statistics & Retrieval
    # ------------------------------------------------------------------

    def get_creator_stats(self) -> Dict[str, Any]:
        """Return comprehensive statistics about the creator engine.

        Returns:
            A dictionary with total counts, category distribution,
            strategy distribution, quality metrics, and recent activity.
        """
        with self._lock:
            avg_quality = (
                round(sum(self._quality_scores) / len(self._quality_scores), 3)
                if self._quality_scores
                else 0.0
            )

            avg_generation_time = (
                round(
                    sum(c.generation_time_ms for c in self._contents.values())
                    / max(len(self._contents), 1),
                    2,
                )
            )

            quality_buckets: Dict[str, int] = {"low": 0, "medium": 0, "high": 0, "excellent": 0}
            for s in self._quality_scores:
                if s < 0.3:
                    quality_buckets["low"] += 1
                elif s < 0.6:
                    quality_buckets["medium"] += 1
                elif s < 0.85:
                    quality_buckets["high"] += 1
                else:
                    quality_buckets["excellent"] += 1

            return {
                "total_generated": self._total_generated,
                "stored_contents": len(self._contents),
                "active_sessions": len(self._sessions),
                "average_quality_score": avg_quality,
                "average_generation_time_ms": avg_generation_time,
                "total_validation_time_s": round(self._total_validation_time, 3),
                "category_distribution": dict(self._category_counts),
                "strategy_distribution": dict(self._strategy_counts),
                "quality_buckets": quality_buckets,
                "max_contents": self._MAX_CONTENTS,
                "max_sessions": self._MAX_SESSIONS,
                "recent_actions": list(self._recent_actions)[-20:],
            }

    def get_content(self, content_id: str) -> Optional[GeneratedContent]:
        """Retrieve a generated content item by its ID.

        Args:
            content_id: The unique identifier of the content.

        Returns:
            The GeneratedContent if found, None otherwise.
        """
        with self._lock:
            return self._contents.get(content_id)

    def list_contents(
        self,
        category: Optional[ContentCategory] = None,
        theme: Optional[ThemeCategory] = None,
        min_quality: float = 0.0,
    ) -> List[GeneratedContent]:
        """List generated contents filtered by optional criteria.

        Args:
            category: Filter by content category.
            theme: Filter by theme.
            min_quality: Minimum quality score threshold.

        Returns:
            List of matching GeneratedContent instances.
        """
        with self._lock:
            results = list(self._contents.values())
            if category is not None:
                results = [c for c in results if c.spec.category == category]
            if theme is not None:
                results = [c for c in results if c.spec.theme == theme]
            if min_quality > 0:
                results = [c for c in results if c.quality_score >= min_quality]
            return results

    def get_session(self, session_id: str) -> Optional[CreatorSession]:
        """Retrieve a creator session by its ID.

        Args:
            session_id: The unique identifier of the session.

        Returns:
            The CreatorSession if found, None otherwise.
        """
        with self._lock:
            return self._sessions.get(session_id)

    def reset(self) -> None:
        """Reset the engine to its initial state, clearing all content and sessions."""
        with self._lock:
            self._contents.clear()
            self._sessions.clear()
            self._total_generated = 0
            self._total_validation_time = 0.0
            self._strategy_counts.clear()
            self._category_counts.clear()
            self._quality_scores.clear()
            self._recent_actions.clear()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _derive_seed(self, spec: ContentSpec) -> int:
        """Derive a deterministic integer seed from the ContentSpec.

        Uses the seed_phrase if provided, otherwise hashes the spec
        properties to produce a consistent random seed.

        Args:
            spec: The ContentSpec to derive a seed from.

        Returns:
            An integer seed for random.Random initialization.
        """
        if spec.seed_phrase:
            source = f"{spec.seed_phrase}:{spec.category.value}:{spec.theme.value}:{spec.complexity.value}"
        else:
            source = f"{spec.spec_id}:{spec.category.value}:{spec.theme.value}:{_time_module.time()}"
        hash_bytes = hashlib.sha256(source.encode("utf-8")).digest()
        return int.from_bytes(hash_bytes[:8], "big")

    def _generate_dialogue(self, theme: ThemeCategory, rng: random.Random) -> Dict[str, Any]:
        """Generate a dialogue set for the given theme.

        Args:
            theme: Thematic category.
            rng: Seeded random number generator.

        Returns:
            A dictionary with dialogue lines and metadata.
        """
        location = rng.choice(THEME_LOCATION_MAP.get(theme, LOCATION_NAMES))
        npc_name = rng.choice(NPC_NAMES)
        line_count = rng.randint(3, 7)
        lines = rng.sample(DIALOGUE_TEMPLATES, min(line_count, len(DIALOGUE_TEMPLATES)))
        lines = [l.format(location=location) for l in lines]

        return {
            "dialogue_id": uuid.uuid4().hex,
            "speaker": npc_name,
            "location": location,
            "theme": theme.value,
            "lines": lines,
            "line_count": len(lines),
            "mood": rng.choice(["friendly", "mysterious", "urgent", "sad", "cheerful", "ominous"]),
        }

    def _generate_environment(
        self, theme: ThemeCategory, complexity: ComplexityLevel, rng: random.Random
    ) -> Dict[str, Any]:
        """Generate an environment description for the given theme.

        Args:
            theme: Thematic category.
            complexity: Complexity tier.
            rng: Seeded random number generator.

        Returns:
            A dictionary with environment definition.
        """
        location = rng.choice(THEME_LOCATION_MAP.get(theme, LOCATION_NAMES))
        weather_options = {
            ThemeCategory.FANTASY: ["clear", "misty", "stormy", "moonlit"],
            ThemeCategory.SCI_FI: ["artificial_lighting", "zero_gravity", "plasma_storm"],
            ThemeCategory.HORROR: ["foggy", "pitch_black", "blood_moon"],
            ThemeCategory.MEDIEVAL: ["overcast", "sunny", "drizzling"],
            ThemeCategory.MODERN: ["clear", "rainy", "overcast", "sunny"],
            ThemeCategory.POST_APOCALYPTIC: ["toxic_haze", "ash_fall", "radiation_storm"],
            ThemeCategory.STEAMPUNK: ["smoggy", "gear_work_hum", "steam_vent"],
            ThemeCategory.CYBERPUNK: ["neon_rain", "data_storm", "acid_mist"],
        }

        return {
            "environment_id": uuid.uuid4().hex,
            "name": f"{location} Environment",
            "theme": theme.value,
            "location": location,
            "weather": rng.choice(weather_options.get(theme, ["clear"])),
            "time_of_day": rng.choice(["dawn", "day", "dusk", "night"]),
            "ambient_sounds": rng.sample(
                ["wind", "water_drip", "distant_thunder", "crackling_fire", "echoing_steps", "machinery_hum"],
                rng.randint(2, 4),
            ),
            "complexity": complexity.value,
        }

    def _generate_puzzle(
        self, theme: ThemeCategory, complexity: ComplexityLevel, rng: random.Random
    ) -> Dict[str, Any]:
        """Generate a puzzle definition for the given theme.

        Args:
            theme: Thematic category.
            complexity: Complexity tier.
            rng: Seeded random number generator.

        Returns:
            A dictionary with puzzle definition.
        """
        puzzle_types = ["pattern_match", "sequence_solve", "spatial_rotate", "symbol_decode", "pressure_plate", "light_beam"]
        puzzle_type = rng.choice(puzzle_types)
        multiplier = COMPLEXITY_MULTIPLIERS.get(complexity, 1.0)
        steps = max(2, int(3 * multiplier))

        return {
            "puzzle_id": uuid.uuid4().hex,
            "puzzle_type": puzzle_type,
            "theme": theme.value,
            "complexity": complexity.value,
            "steps_required": steps,
            "time_limit_seconds": round(30.0 * multiplier, 0),
            "hint": f"Look for the {rng.choice(['glowing', 'hidden', 'rotating', 'ancient'])} symbols.",
            "reward": rng.choice(TREASURE_TYPES),
            "fail_consequence": rng.choice(["retry", "damage", "spawn_enemy", "lock_path"]),
        }

    def _generate_boss(
        self, theme: ThemeCategory, complexity: ComplexityLevel, rng: random.Random
    ) -> Dict[str, Any]:
        """Generate a boss definition for the given theme.

        Args:
            theme: Thematic category.
            complexity: Complexity tier.
            rng: Seeded random number generator.

        Returns:
            A dictionary with boss definition.
        """
        enemy_pool = THEME_ENEMY_MAP.get(theme, ENEMY_TYPES)
        multiplier = COMPLEXITY_MULTIPLIERS.get(complexity, 1.0)
        phase_count = 1 if complexity == ComplexityLevel.TRIVIAL else rng.randint(2, 4)

        phases: List[Dict[str, Any]] = []
        for i in range(phase_count):
            phases.append({
                "phase": i + 1,
                "name": f"Phase {i + 1}: {rng.choice(['Wrath', 'Shadows', 'Fury', 'Despair', 'Ascension', 'Corruption'])}",
                "health_threshold": round(1.0 - (i / phase_count), 2),
                "new_abilities": rng.sample(
                    ["aoe_attack", "summon_minions", "teleport", "shield", "rage_mode", "elemental_shift"],
                    rng.randint(1, 3),
                ),
                "damage_multiplier": round(1.0 + (i * 0.3), 1),
            })

        return {
            "boss_id": uuid.uuid4().hex,
            "name": f"{rng.choice(['Overlord', 'Titan', 'Ancient', 'Dread', 'Void'])} {rng.choice(enemy_pool)}",
            "theme": theme.value,
            "complexity": complexity.value,
            "health": int(500 * multiplier),
            "damage": int(30 * multiplier),
            "phases": phases,
            "phase_count": phase_count,
            "arena": rng.choice(THEME_LOCATION_MAP.get(theme, LOCATION_NAMES)),
            "loot_table": rng.sample(TREASURE_TYPES, min(4, len(TREASURE_TYPES))),
            "intro_dialogue": f"You dare enter my domain? You will not leave {rng.choice(['alive', 'unchanged', 'the same', 'in one piece'])}!",
        }

    def _generate_achievement(self, theme: ThemeCategory, rng: random.Random) -> Dict[str, Any]:
        """Generate an achievement definition for the given theme.

        Args:
            theme: Thematic category.
            rng: Seeded random number generator.

        Returns:
            A dictionary with achievement definition.
        """
        template = rng.choice(ACHIEVEMENT_TEMPLATES)
        return {
            "achievement_id": uuid.uuid4().hex,
            "title": template["title"],
            "description": template["description"],
            "theme": theme.value,
            "points": rng.choice([5, 10, 15, 25, 50, 100]),
            "is_hidden": rng.random() < 0.2,
            "icon": rng.choice(["star", "trophy", "shield", "crown", "gem", "sword"]),
        }

    def _enforce_max_contents(self) -> None:
        """Evict oldest contents when storage exceeds the maximum limit."""
        if len(self._contents) >= self._MAX_CONTENTS:
            sorted_contents = sorted(
                self._contents.items(),
                key=lambda item: item[1].created_at,
            )
            overflow = len(self._contents) - self._MAX_CONTENTS + 1
            for cid, _ in sorted_contents[:overflow]:
                self._contents.pop(cid, None)

    def _enforce_max_sessions(self) -> None:
        """Evict oldest sessions when storage exceeds the maximum limit."""
        if len(self._sessions) >= self._MAX_SESSIONS:
            sorted_sessions = sorted(
                self._sessions.items(),
                key=lambda item: item[1].started_at,
            )
            overflow = len(self._sessions) - self._MAX_SESSIONS + 1
            for sid, _ in sorted_sessions[:overflow]:
                self._sessions.pop(sid, None)


# =============================================================================
# Module-level convenience accessor
# =============================================================================


def get_autonomous_creator() -> AutonomousCreatorEngine:
    """Return the singleton AutonomousCreatorEngine instance."""
    return AutonomousCreatorEngine.get_instance()