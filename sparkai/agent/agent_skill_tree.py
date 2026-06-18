"""
SparkLabs Agent - Skill Tree Engine

AI-driven skill tree and progression system for the AI-native game engine.
Designs skill trees, ability progression paths, unlock requirements, and
character build optimization. Generates class-specific skill trees, evaluates
build viability, and finds optimal skill allocations for given point budgets.

Architecture:
  SkillTreeEngine (Singleton)
    |-- SkillNode (individual skill node in the tree)
    |-- SkillTree (complete skill tree for a character class)
    |-- BuildOptimization (optimized skill allocation result)
    |-- ClassTemplate (predefined archetype configurations)
    |-- SynergyEvaluator (node-to-node synergy scoring)
    |-- GreedyOptimizer (point-budget allocation algorithm)
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------


class SkillCategory(Enum):
    """Category of a skill defining its primary gameplay domain."""
    COMBAT = "combat"
    DEFENSE = "defense"
    MAGIC = "magic"
    UTILITY = "utility"
    MOVEMENT = "movement"
    CRAFTING = "crafting"
    SOCIAL = "social"
    STEALTH = "stealth"
    SURVIVAL = "survival"
    LEADERSHIP = "leadership"


class SkillTier(Enum):
    """Progression tier indicating a skill's position in the tree."""
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"
    TIER_4 = "tier_4"
    TIER_5 = "tier_5"
    ULTIMATE = "ultimate"


class SkillType(Enum):
    """Activation type defining how a skill is triggered or sustained."""
    PASSIVE = "passive"
    ACTIVE = "active"
    AURA = "aura"
    TRIGGER = "trigger"
    CHANNELED = "channeled"
    TOGGLE = "toggle"


# ------------------------------------------------------------------
# Tier progression constants
# ------------------------------------------------------------------

TIER_ORDER: List[SkillTier] = [
    SkillTier.TIER_1,
    SkillTier.TIER_2,
    SkillTier.TIER_3,
    SkillTier.TIER_4,
    SkillTier.TIER_5,
    SkillTier.ULTIMATE,
]

TIER_UNLOCK_COSTS: Dict[SkillTier, int] = {
    SkillTier.TIER_1: 1,
    SkillTier.TIER_2: 2,
    SkillTier.TIER_3: 3,
    SkillTier.TIER_4: 5,
    SkillTier.TIER_5: 8,
    SkillTier.ULTIMATE: 12,
}

TIER_MAX_LEVELS: Dict[SkillTier, int] = {
    SkillTier.TIER_1: 5,
    SkillTier.TIER_2: 4,
    SkillTier.TIER_3: 3,
    SkillTier.TIER_4: 3,
    SkillTier.TIER_5: 2,
    SkillTier.ULTIMATE: 1,
}


# ------------------------------------------------------------------
# Class archetype definitions
# ------------------------------------------------------------------

CLASS_ARCHETYPES: Dict[str, Dict[str, Any]] = {
    "warrior": {
        "primary_categories": [SkillCategory.COMBAT, SkillCategory.DEFENSE, SkillCategory.LEADERSHIP],
        "secondary_categories": [SkillCategory.SURVIVAL, SkillCategory.MOVEMENT],
        "description": "A melee specialist focused on combat prowess, defensive fortitude, and battlefield leadership.",
        "stat_focus": {"strength": 0.8, "vitality": 0.7, "endurance": 0.6},
        "skill_name_prefixes": [
            "Power", "Mighty", "Iron", "Steel", "Battle", "War", "Shield",
            "Valor", "Fortitude", "Courage", "Fury", "Warlord",
        ],
        "skill_name_suffixes": [
            "Strike", "Slam", "Wall", "Guard", "Charge", "Roar", "Cleave",
            "Bash", "Rage", "Stance", "Formation", "Command",
        ],
    },
    "mage": {
        "primary_categories": [SkillCategory.MAGIC, SkillCategory.UTILITY],
        "secondary_categories": [SkillCategory.COMBAT, SkillCategory.SURVIVAL],
        "description": "A spellcaster specializing in arcane arts, elemental manipulation, and magical utility.",
        "stat_focus": {"intelligence": 0.9, "wisdom": 0.7, "spirit": 0.6},
        "skill_name_prefixes": [
            "Arcane", "Mystic", "Eldritch", "Elemental", "Astral", "Runic",
            "Celestial", "Infernal", "Glacial", "Storm", "Void", "Ethereal",
        ],
        "skill_name_suffixes": [
            "Bolt", "Ward", "Surge", "Blast", "Nova", "Rift", "Conjuration",
            "Barrier", "Channel", "Pulse", "Convergence", "Invocation",
        ],
    },
    "rogue": {
        "primary_categories": [SkillCategory.STEALTH, SkillCategory.MOVEMENT, SkillCategory.COMBAT],
        "secondary_categories": [SkillCategory.UTILITY, SkillCategory.SOCIAL],
        "description": "A shadowy operative specializing in stealth, mobility, and precision strikes.",
        "stat_focus": {"agility": 0.9, "dexterity": 0.8, "cunning": 0.6},
        "skill_name_prefixes": [
            "Shadow", "Silent", "Ghost", "Night", "Venom", "Phantom",
            "Assassin", "Swift", "Deadly", "Cunning", "Shroud", "Dagger",
        ],
        "skill_name_suffixes": [
            "Strike", "Step", "Blade", "Cloak", "Takedown", "Vanish",
            "Ambush", "Evasion", "Backstab", "Misdirection", "Fade", "Lunge",
        ],
    },
    "ranger": {
        "primary_categories": [SkillCategory.COMBAT, SkillCategory.SURVIVAL, SkillCategory.MOVEMENT],
        "secondary_categories": [SkillCategory.UTILITY, SkillCategory.STEALTH],
        "description": "A wilderness expert skilled in ranged combat, tracking, and survival techniques.",
        "stat_focus": {"dexterity": 0.7, "perception": 0.8, "agility": 0.6},
        "skill_name_prefixes": [
            "Eagle", "Wild", "Hunter", "Tracker", "Long", "Forest",
            "Predator", "Scout", "Pathfinder", "Hawkeye", "Nature", "Wind",
        ],
        "skill_name_suffixes": [
            "Shot", "Mark", "Arrow", "Quiver", "Sight", "Trap",
            "Volley", "Snipe", "Stalk", "Pounce", "Call", "Focus",
        ],
    },
    "cleric": {
        "primary_categories": [SkillCategory.MAGIC, SkillCategory.DEFENSE, SkillCategory.LEADERSHIP],
        "secondary_categories": [SkillCategory.UTILITY, SkillCategory.SURVIVAL],
        "description": "A divine healer and protector who channels sacred energy to aid allies and ward off darkness.",
        "stat_focus": {"wisdom": 0.8, "spirit": 0.8, "vitality": 0.5},
        "skill_name_prefixes": [
            "Divine", "Holy", "Sacred", "Blessed", "Radiant", "Celestial",
            "Righteous", "Seraphic", "Hallowed", "Reverent", "Sanctified", "Devout",
        ],
        "skill_name_suffixes": [
            "Heal", "Light", "Aegis", "Benediction", "Smite", "Sanctuary",
            "Resurrection", "Cleanse", "Miracle", "Prayer", "Consecration", "Judgment",
        ],
    },
    "paladin": {
        "primary_categories": [SkillCategory.COMBAT, SkillCategory.DEFENSE, SkillCategory.LEADERSHIP],
        "secondary_categories": [SkillCategory.MAGIC, SkillCategory.SURVIVAL],
        "description": "A holy warrior combining martial prowess with divine magic to protect the righteous.",
        "stat_focus": {"strength": 0.6, "vitality": 0.7, "spirit": 0.6},
        "skill_name_prefixes": [
            "Templar", "Crusader", "Justicar", "Guardian", "Sentinel", "Oath",
            "Aegis", "Bulwark", "Defender", "Protector", "Vindicator", "Champion",
        ],
        "skill_name_suffixes": [
            "Strike", "Shield", "Aura", "Judgment", "Retribution", "Valor",
            "Consecration", "Ward", "Bastion", "Crusade", "Vow", "Fortress",
        ],
    },
    "necromancer": {
        "primary_categories": [SkillCategory.MAGIC, SkillCategory.SURVIVAL, SkillCategory.LEADERSHIP],
        "secondary_categories": [SkillCategory.COMBAT, SkillCategory.UTILITY],
        "description": "A dark magic practitioner who commands the dead and drains life force from enemies.",
        "stat_focus": {"intelligence": 0.8, "spirit": 0.7, "endurance": 0.5},
        "skill_name_prefixes": [
            "Bone", "Grave", "Death", "Soul", "Dread", "Wraith",
            "Corpse", "Plague", "Decay", "Lich", "Reaper", "Necrotic",
        ],
        "skill_name_suffixes": [
            "Drain", "Summon", "Curse", "Blight", "Specter", "Rot",
            "Harvest", "Marrow", "Shroud", "Leech", "Remnant", "Desecration",
        ],
    },
    "bard": {
        "primary_categories": [SkillCategory.SOCIAL, SkillCategory.MAGIC, SkillCategory.UTILITY],
        "secondary_categories": [SkillCategory.MOVEMENT, SkillCategory.LEADERSHIP],
        "description": "A performer whose music and tales inspire allies, enchant foes, and shape the world around them.",
        "stat_focus": {"charisma": 0.9, "dexterity": 0.5, "intelligence": 0.5},
        "skill_name_prefixes": [
            "Melodic", "Harmonic", "Lyric", "Ballad", "Sonnet", "Rhythm",
            "Chorus", "Elegy", "Anthem", "Aria", "Serenade", "Ode",
        ],
        "skill_name_suffixes": [
            "Song", "Tune", "Verse", "Refrain", "Chord", "Stanza",
            "Performance", "Resonance", "Cadence", "Encore", "Crescendo", "Allegro",
        ],
    },
    "monk": {
        "primary_categories": [SkillCategory.COMBAT, SkillCategory.MOVEMENT, SkillCategory.DEFENSE],
        "secondary_categories": [SkillCategory.UTILITY, SkillCategory.SURVIVAL],
        "description": "A disciplined martial artist who channels inner energy for devastating unarmed combat.",
        "stat_focus": {"agility": 0.7, "dexterity": 0.7, "spirit": 0.6},
        "skill_name_prefixes": [
            "Chi", "Zen", "Fist", "Palm", "Kick", "Monk",
            "Dragon", "Tiger", "Crane", "Serpent", "Mantra", "Flowing",
        ],
        "skill_name_suffixes": [
            "Strike", "Form", "Stance", "Meditation", "Flow", "Kata",
            "Combo", "Focus", "Breath", "Technique", "Harmony", "Discipline",
        ],
    },
    "druid": {
        "primary_categories": [SkillCategory.MAGIC, SkillCategory.SURVIVAL, SkillCategory.UTILITY],
        "secondary_categories": [SkillCategory.COMBAT, SkillCategory.MOVEMENT],
        "description": "A nature-bound shapeshifter who wields primal magic and commands the forces of the wild.",
        "stat_focus": {"wisdom": 0.7, "spirit": 0.7, "vitality": 0.5},
        "skill_name_prefixes": [
            "Wild", "Verdant", "Primal", "Grove", "Thorn", "Feral",
            "Ancient", "Shaman", "Gaia", "Bramble", "Lunar", "Solar",
        ],
        "skill_name_suffixes": [
            "Form", "Growth", "Claw", "Root", "Vine", "Bloom",
            "Fang", "Hibernate", "Regrowth", "Totem", "Swarm", "Cyclone",
        ],
    },
}


# ------------------------------------------------------------------
# Category synergy matrix for build optimization
# ------------------------------------------------------------------

CATEGORY_SYNERGY: Dict[SkillCategory, Dict[SkillCategory, float]] = {
    SkillCategory.COMBAT: {
        SkillCategory.MOVEMENT: 0.7, SkillCategory.DEFENSE: 0.6,
        SkillCategory.STEALTH: 0.5, SkillCategory.LEADERSHIP: 0.4,
    },
    SkillCategory.DEFENSE: {
        SkillCategory.SURVIVAL: 0.7, SkillCategory.COMBAT: 0.6,
        SkillCategory.LEADERSHIP: 0.5, SkillCategory.MAGIC: 0.3,
    },
    SkillCategory.MAGIC: {
        SkillCategory.UTILITY: 0.7, SkillCategory.COMBAT: 0.5,
        SkillCategory.DEFENSE: 0.3, SkillCategory.SOCIAL: 0.3,
    },
    SkillCategory.UTILITY: {
        SkillCategory.MAGIC: 0.7, SkillCategory.CRAFTING: 0.6,
        SkillCategory.MOVEMENT: 0.4, SkillCategory.SOCIAL: 0.4,
    },
    SkillCategory.MOVEMENT: {
        SkillCategory.COMBAT: 0.7, SkillCategory.STEALTH: 0.6,
        SkillCategory.UTILITY: 0.4, SkillCategory.SURVIVAL: 0.3,
    },
    SkillCategory.CRAFTING: {
        SkillCategory.UTILITY: 0.6, SkillCategory.SURVIVAL: 0.5,
        SkillCategory.MAGIC: 0.3, SkillCategory.DEFENSE: 0.3,
    },
    SkillCategory.SOCIAL: {
        SkillCategory.LEADERSHIP: 0.8, SkillCategory.UTILITY: 0.4,
        SkillCategory.STEALTH: 0.3, SkillCategory.MAGIC: 0.3,
    },
    SkillCategory.STEALTH: {
        SkillCategory.MOVEMENT: 0.6, SkillCategory.COMBAT: 0.5,
        SkillCategory.SOCIAL: 0.3, SkillCategory.UTILITY: 0.3,
    },
    SkillCategory.SURVIVAL: {
        SkillCategory.DEFENSE: 0.7, SkillCategory.MOVEMENT: 0.3,
        SkillCategory.CRAFTING: 0.5, SkillCategory.UTILITY: 0.4,
    },
    SkillCategory.LEADERSHIP: {
        SkillCategory.SOCIAL: 0.8, SkillCategory.DEFENSE: 0.5,
        SkillCategory.COMBAT: 0.4, SkillCategory.MAGIC: 0.3,
    },
}


# ------------------------------------------------------------------
# Stat bonus definitions
# ------------------------------------------------------------------

STAT_NAMES: List[str] = [
    "strength", "agility", "intelligence", "wisdom", "vitality",
    "dexterity", "spirit", "endurance", "charisma", "perception",
    "cunning", "luck",
]

STAT_POOL_BY_CATEGORY: Dict[SkillCategory, List[str]] = {
    SkillCategory.COMBAT: ["strength", "agility", "dexterity", "endurance"],
    SkillCategory.DEFENSE: ["vitality", "endurance", "strength", "spirit"],
    SkillCategory.MAGIC: ["intelligence", "wisdom", "spirit"],
    SkillCategory.UTILITY: ["intelligence", "cunning", "perception"],
    SkillCategory.MOVEMENT: ["agility", "dexterity", "endurance"],
    SkillCategory.CRAFTING: ["dexterity", "intelligence", "cunning"],
    SkillCategory.SOCIAL: ["charisma", "cunning", "perception"],
    SkillCategory.STEALTH: ["agility", "dexterity", "cunning"],
    SkillCategory.SURVIVAL: ["vitality", "endurance", "wisdom"],
    SkillCategory.LEADERSHIP: ["charisma", "wisdom", "spirit"],
}


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class SkillNode:
    """A single skill node within a skill tree.

    Represents an unlockable ability with its own progression, requirements,
    and connections to other nodes in the tree.
    """
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: SkillCategory = SkillCategory.COMBAT
    tier: SkillTier = SkillTier.TIER_1
    skill_type: SkillType = SkillType.ACTIVE
    description: str = ""
    effect_description: str = ""
    max_level: int = 5
    current_level: int = 0
    requirements: Dict[str, Any] = field(default_factory=lambda: {
        "level_required": 0,
        "prerequisites": [],
    })
    unlock_cost: int = 1
    stat_bonuses: Dict[str, float] = field(default_factory=dict)
    parent_nodes: List[str] = field(default_factory=list)
    child_nodes: List[str] = field(default_factory=list)
    position_x: float = 0.0
    position_y: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "category": self.category.value,
            "tier": self.tier.value,
            "skill_type": self.skill_type.value,
            "description": self.description,
            "effect_description": self.effect_description,
            "max_level": self.max_level,
            "current_level": self.current_level,
            "requirements": dict(self.requirements),
            "unlock_cost": self.unlock_cost,
            "stat_bonuses": dict(self.stat_bonuses),
            "parent_nodes": list(self.parent_nodes),
            "child_nodes": list(self.child_nodes),
            "position_x": self.position_x,
            "position_y": self.position_y,
        }

    def is_unlocked(self) -> bool:
        return self.current_level > 0

    def is_max_level(self) -> bool:
        return self.current_level >= self.max_level

    def total_stat_value(self) -> float:
        if not self.stat_bonuses:
            return 0.0
        return sum(abs(v) for v in self.stat_bonuses.values())


@dataclass
class SkillTree:
    """A complete skill tree for a specific character class.

    Contains all skill nodes, their connections, and metadata about
    the class and total progression capacity.
    """
    tree_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    character_class: str = ""
    total_nodes: int = 0
    nodes: Dict[str, SkillNode] = field(default_factory=dict)
    max_points: int = 50
    description: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tree_id": self.tree_id,
            "name": self.name,
            "character_class": self.character_class,
            "total_nodes": self.total_nodes,
            "node_count": len(self.nodes),
            "max_points": self.max_points,
            "description": self.description,
            "created_at": self.created_at,
            "nodes": [n.to_dict() for n in self.nodes.values()],
        }

    def get_root_nodes(self) -> List[SkillNode]:
        return [n for n in self.nodes.values() if not n.parent_nodes]

    def get_unlocked_nodes(self) -> List[SkillNode]:
        return [n for n in self.nodes.values() if n.is_unlocked()]

    def get_by_tier(self, tier: SkillTier) -> List[SkillNode]:
        return [n for n in self.nodes.values() if n.tier == tier]

    def get_node(self, node_id: str) -> Optional[SkillNode]:
        return self.nodes.get(node_id)


@dataclass
class BuildOptimization:
    """Result of a build optimization run.

    Contains the selected nodes, total score, and metadata about
    the optimization parameters used.
    """
    opt_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tree_id: str = ""
    target_role: str = ""
    max_points: int = 0
    selected_nodes: List[str] = field(default_factory=list)
    build_score: float = 0.0
    build_name: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opt_id": self.opt_id,
            "tree_id": self.tree_id,
            "target_role": self.target_role,
            "max_points": self.max_points,
            "selected_nodes": list(self.selected_nodes),
            "selected_count": len(self.selected_nodes),
            "build_score": round(self.build_score, 4),
            "build_name": self.build_name,
            "description": self.description,
        }


# ------------------------------------------------------------------
# SkillTreeEngine Singleton
# ------------------------------------------------------------------


class SkillTreeEngine:
    """AI-driven skill tree and progression system for the SparkLabs game engine.

    Designs skill trees, ability progression paths, unlock requirements,
    and character build optimization. Generates class-specific skill trees
    with logical category distributions and finds optimal skill allocations
    for given point budgets.

    Usage:
        engine = SkillTreeEngine.get_instance()
        tree = engine.generate_class_skill_tree("warrior", 20)
        build = engine.optimize_build(tree.tree_id, "dps", 30)
    """

    _instance: Optional[SkillTreeEngine] = None
    _lock: threading.RLock = threading.RLock()

    MAX_TREES: int = 100
    MAX_NODES_PER_TREE: int = 200
    MAX_BUILD_OPTIMIZATIONS: int = 200

    def __new__(cls) -> SkillTreeEngine:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> SkillTreeEngine:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        with self._lock:
            if hasattr(self, "_initialized") and self._initialized:
                return
            self._trees: Dict[str, SkillTree] = {}
            self._optimizations: Dict[str, BuildOptimization] = {}
            self._node_index: Dict[str, str] = {}  # node_id -> tree_id
            self._stats: Dict[str, Any] = {
                "total_trees_created": 0,
                "total_nodes_created": 0,
                "total_optimizations_run": 0,
                "total_connections_made": 0,
            }
            self._initialized = True

    # ------------------------------------------------------------------
    # Tree Creation
    # ------------------------------------------------------------------

    def create_skill_tree(
        self,
        name: str,
        character_class: str,
        description: str = "",
    ) -> SkillTree:
        """Create a new empty skill tree for a character class.

        Args:
            name: Display name for the skill tree.
            character_class: The character class this tree belongs to.
            description: Optional description of the tree's purpose.

        Returns:
            A new SkillTree instance.
        """
        with self._lock:
            tree = SkillTree(
                name=name,
                character_class=character_class,
                description=description,
            )
            self._trees[tree.tree_id] = tree
            self._stats["total_trees_created"] += 1

            if len(self._trees) > self.MAX_TREES:
                self._evict_oldest_trees()

            return tree

    def add_skill_node(
        self,
        tree_id: str,
        name: str,
        category: SkillCategory,
        tier: SkillTier,
        skill_type: SkillType,
        description: str = "",
        effect_description: str = "",
        max_level: int = 5,
        unlock_cost: int = 1,
        stat_bonuses: Optional[Dict[str, float]] = None,
        position_x: float = 0.0,
        position_y: float = 0.0,
    ) -> Optional[SkillNode]:
        """Add a skill node to an existing skill tree.

        Args:
            tree_id: ID of the target skill tree.
            name: Display name of the skill.
            category: Skill category.
            tier: Progression tier of the node.
            skill_type: Activation type of the skill.
            description: Description of the skill.
            effect_description: Description of the skill's effect.
            max_level: Maximum level this skill can reach.
            unlock_cost: Point cost to unlock this skill.
            stat_bonuses: Dict mapping stat names to bonus values.
            position_x: X coordinate for tree layout.
            position_y: Y coordinate for tree layout.

        Returns:
            The created SkillNode, or None if the tree is not found.
        """
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return None

            if len(tree.nodes) >= self.MAX_NODES_PER_TREE:
                return None

            if max_level <= 0:
                max_level = TIER_MAX_LEVELS.get(tier, 5)

            if unlock_cost <= 0:
                unlock_cost = TIER_UNLOCK_COSTS.get(tier, 1)

            node = SkillNode(
                name=name,
                category=category,
                tier=tier,
                skill_type=skill_type,
                description=description,
                effect_description=effect_description,
                max_level=max_level,
                unlock_cost=unlock_cost,
                stat_bonuses=stat_bonuses or {},
                position_x=position_x,
                position_y=position_y,
            )
            tree.nodes[node.node_id] = node
            tree.total_nodes = len(tree.nodes)
            self._node_index[node.node_id] = tree_id
            self._stats["total_nodes_created"] += 1

            return node

    # ------------------------------------------------------------------
    # Node Connections
    # ------------------------------------------------------------------

    def connect_nodes(
        self,
        parent_node_id: str,
        child_node_id: str,
    ) -> Optional[SkillNode]:
        """Connect two nodes in a parent-child relationship.

        The parent must be at a lower or equal tier compared to the child.
        This establishes a dependency where the parent must be unlocked
        before the child becomes available.

        Args:
            parent_node_id: ID of the parent node.
            child_node_id: ID of the child node.

        Returns:
            The child SkillNode with updated parent references, or None on failure.
        """
        with self._lock:
            parent_tree_id = self._node_index.get(parent_node_id)
            child_tree_id = self._node_index.get(child_node_id)

            if parent_tree_id is None or child_tree_id is None:
                return None
            if parent_tree_id != child_tree_id:
                return None

            tree = self._trees.get(parent_tree_id)
            if tree is None:
                return None

            parent_node = tree.nodes.get(parent_node_id)
            child_node = tree.nodes.get(child_node_id)

            if parent_node is None or child_node is None:
                return None

            parent_tier_idx = TIER_ORDER.index(parent_node.tier)
            child_tier_idx = TIER_ORDER.index(child_node.tier)

            if child_tier_idx <= parent_tier_idx:
                return None

            if child_node_id in parent_node.parent_nodes:
                return None

            if parent_node_id not in child_node.parent_nodes:
                child_node.parent_nodes.append(parent_node_id)
            if child_node_id not in parent_node.child_nodes:
                parent_node.child_nodes.append(child_node_id)

            self._stats["total_connections_made"] += 1
            return child_node

    def set_requirements(
        self,
        node_id: str,
        level_required: int = 0,
        prerequisites: Optional[List[str]] = None,
    ) -> Optional[SkillNode]:
        """Set unlock requirements for a skill node.

        Requirements can include a minimum character level and a list of
        prerequisite node IDs that must be unlocked first.

        Args:
            node_id: ID of the node to update.
            level_required: Minimum character level needed.
            prerequisites: List of node IDs that must be unlocked first.

        Returns:
            The updated SkillNode, or None if not found.
        """
        with self._lock:
            tree_id = self._node_index.get(node_id)
            if tree_id is None:
                return None

            tree = self._trees.get(tree_id)
            if tree is None:
                return None

            node = tree.nodes.get(node_id)
            if node is None:
                return None

            node.requirements["level_required"] = max(0, level_required)
            if prerequisites is not None:
                valid_prereqs = [p for p in prerequisites if p in tree.nodes]
                node.requirements["prerequisites"] = valid_prereqs
                for p in valid_prereqs:
                    if node_id not in tree.nodes[p].child_nodes:
                        tree.nodes[p].child_nodes.append(node_id)
                    if p not in node.parent_nodes:
                        node.parent_nodes.append(p)

            return node

    # ------------------------------------------------------------------
    # Skill Progression
    # ------------------------------------------------------------------

    def unlock_skill(self, node_id: str) -> Optional[SkillNode]:
        """Unlock a skill node, setting its current level to 1.

        Checks prerequisites before unlocking. If the node is already
        unlocked, this has no effect.

        Args:
            node_id: ID of the node to unlock.

        Returns:
            The unlocked SkillNode, or None if prerequisites are not met.
        """
        with self._lock:
            tree_id = self._node_index.get(node_id)
            if tree_id is None:
                return None

            tree = self._trees.get(tree_id)
            if tree is None:
                return None

            node = tree.nodes.get(node_id)
            if node is None:
                return None

            if node.is_unlocked():
                return node

            if not self._check_prerequisites(node, tree):
                return None

            node.current_level = 1
            return node

    def level_up_skill(self, node_id: str) -> Optional[SkillNode]:
        """Increase a skill's current level by 1.

        The skill must already be unlocked and not at max level.

        Args:
            node_id: ID of the node to level up.

        Returns:
            The leveled SkillNode, or None if conditions are not met.
        """
        with self._lock:
            tree_id = self._node_index.get(node_id)
            if tree_id is None:
                return None

            tree = self._trees.get(tree_id)
            if tree is None:
                return None

            node = tree.nodes.get(node_id)
            if node is None:
                return None

            if not node.is_unlocked():
                return None

            if node.is_max_level():
                return None

            node.current_level += 1
            return node

    def _check_prerequisites(self, node: SkillNode, tree: SkillTree) -> bool:
        """Verify that all prerequisites for a node are met."""
        prereqs = node.requirements.get("prerequisites", [])
        for prereq_id in prereqs:
            prereq_node = tree.nodes.get(prereq_id)
            if prereq_node is None or not prereq_node.is_unlocked():
                return False

        for parent_id in node.parent_nodes:
            parent_node = tree.nodes.get(parent_id)
            if parent_node is None or not parent_node.is_unlocked():
                return False

        return True

    # ------------------------------------------------------------------
    # Class Skill Tree Generation
    # ------------------------------------------------------------------

    def generate_class_skill_tree(
        self,
        character_class: str,
        num_nodes: int = 20,
    ) -> Optional[SkillTree]:
        """Generate a complete skill tree for a specific character class.

        Creates a structured tree with nodes distributed across tiers and
        categories appropriate for the class archetype. Nodes are connected
        in a logical progression from lower to higher tiers.

        Args:
            character_class: The class name (e.g., "warrior", "mage", "rogue").
            num_nodes: Total number of nodes to generate.

        Returns:
            A fully populated SkillTree, or None if the class is unsupported.
        """
        with self._lock:
            class_key = character_class.lower().strip()
            archetype = CLASS_ARCHETYPES.get(class_key)
            if archetype is None:
                supported = list(CLASS_ARCHETYPES.keys())
                return None

            rng = random.Random()

            tree_name = f"{class_key.title()} Skill Tree"
            tree = self.create_skill_tree(
                name=tree_name,
                character_class=class_key,
                description=archetype["description"],
            )
            if tree is None:
                return None

            primary_cats = archetype["primary_categories"]
            secondary_cats = archetype["secondary_categories"]
            prefixes = archetype["skill_name_prefixes"]
            suffixes = archetype["skill_name_suffixes"]
            stat_focus = archetype["stat_focus"]

            total_points = 0
            tier_distribution = self._compute_tier_distribution(num_nodes, rng)
            previous_tier_nodes: List[SkillNode] = []

            for tier in TIER_ORDER:
                nodes_in_tier = tier_distribution.get(tier, 0)
                if nodes_in_tier <= 0:
                    continue

                tier_nodes: List[SkillNode] = []

                for i in range(nodes_in_tier):
                    if i < nodes_in_tier * 0.7:
                        category = rng.choice(primary_cats)
                    else:
                        category = rng.choice(secondary_cats)

                    skill_name = self._generate_skill_name(
                        prefixes, suffixes, tree.nodes, rng
                    )

                    skill_type = self._select_skill_type(category, tier, rng)

                    max_level = TIER_MAX_LEVELS.get(tier, 5)
                    unlock_cost = TIER_UNLOCK_COSTS.get(tier, 1)
                    total_points += unlock_cost * max_level

                    stat_bonuses = self._generate_stat_bonuses(
                        category, tier, stat_focus, rng
                    )

                    effect = self._generate_effect_description(
                        skill_name, category, tier, skill_type, rng
                    )

                    desc = (
                        f"A {tier.value.replace('_', ' ')} {category.value} "
                        f"{skill_type.value} skill."
                    )

                    pos_x = 100.0 + (TIER_ORDER.index(tier) * 180.0)
                    pos_y = 50.0 + (i * 120.0)

                    node = self.add_skill_node(
                        tree_id=tree.tree_id,
                        name=skill_name,
                        category=category,
                        tier=tier,
                        skill_type=skill_type,
                        description=desc,
                        effect_description=effect,
                        max_level=max_level,
                        unlock_cost=unlock_cost,
                        stat_bonuses=stat_bonuses,
                        position_x=pos_x,
                        position_y=pos_y,
                    )
                    if node is None:
                        continue

                    tier_nodes.append(node)

                for node in tier_nodes:
                    for prev_node in previous_tier_nodes:
                        if rng.random() < 0.4:
                            self.connect_nodes(prev_node.node_id, node.node_id)
                    if previous_tier_nodes and not node.parent_nodes:
                        parent = rng.choice(previous_tier_nodes)
                        self.connect_nodes(parent.node_id, node.node_id)

                if tier == SkillTier.TIER_1:
                    for node in tier_nodes:
                        node.requirements["level_required"] = 0
                elif tier == SkillTier.TIER_2:
                    for node in tier_nodes:
                        node.requirements["level_required"] = 5
                elif tier == SkillTier.TIER_3:
                    for node in tier_nodes:
                        node.requirements["level_required"] = 10
                elif tier == SkillTier.TIER_4:
                    for node in tier_nodes:
                        node.requirements["level_required"] = 20
                elif tier == SkillTier.TIER_5:
                    for node in tier_nodes:
                        node.requirements["level_required"] = 35
                elif tier == SkillTier.ULTIMATE:
                    for node in tier_nodes:
                        node.requirements["level_required"] = 50

                previous_tier_nodes = tier_nodes

            tree.max_points = max(30, total_points)
            tree.total_nodes = len(tree.nodes)
            return tree

    def _compute_tier_distribution(
        self, num_nodes: int, rng: random.Random
    ) -> Dict[SkillTier, int]:
        """Distribute nodes across tiers with a pyramid-like structure."""
        if num_nodes <= 6:
            return {
                SkillTier.TIER_1: num_nodes,
                SkillTier.TIER_2: 0,
                SkillTier.TIER_3: 0,
                SkillTier.TIER_4: 0,
                SkillTier.TIER_5: 0,
                SkillTier.ULTIMATE: 0,
            }

        weights = {
            SkillTier.TIER_1: 0.30,
            SkillTier.TIER_2: 0.25,
            SkillTier.TIER_3: 0.20,
            SkillTier.TIER_4: 0.13,
            SkillTier.TIER_5: 0.08,
            SkillTier.ULTIMATE: 0.04,
        }

        distribution: Dict[SkillTier, int] = {}
        allocated = 0
        tiers = TIER_ORDER

        for i, tier in enumerate(tiers):
            if i == len(tiers) - 1:
                distribution[tier] = max(0, num_nodes - allocated)
            else:
                count = max(0, int(num_nodes * weights[tier]))
                distribution[tier] = count
                allocated += count

        for tier in tiers:
            if distribution.get(tier, 0) == 0 and allocated < num_nodes:
                distribution[tier] = 1
                allocated += 1

        return distribution

    def _generate_skill_name(
        self,
        prefixes: List[str],
        suffixes: List[str],
        existing_nodes: Dict[str, SkillNode],
        rng: random.Random,
    ) -> str:
        """Generate a unique skill name from prefix and suffix pools."""
        existing_names = {n.name for n in existing_nodes.values()}
        attempts = 0
        while attempts < 100:
            name = f"{rng.choice(prefixes)} {rng.choice(suffixes)}"
            if name not in existing_names:
                return name
            attempts += 1
        return f"Skill-{len(existing_nodes) + 1:03d}"

    def _select_skill_type(
        self,
        category: SkillCategory,
        tier: SkillTier,
        rng: random.Random,
    ) -> SkillType:
        """Select an appropriate skill type based on category and tier."""
        type_weights: Dict[SkillType, float] = {
            SkillType.PASSIVE: 0.25,
            SkillType.ACTIVE: 0.35,
            SkillType.AURA: 0.15,
            SkillType.TRIGGER: 0.10,
            SkillType.CHANNELED: 0.10,
            SkillType.TOGGLE: 0.05,
        }

        if category == SkillCategory.DEFENSE:
            type_weights[SkillType.PASSIVE] = 0.35
            type_weights[SkillType.AURA] = 0.20
        elif category == SkillCategory.MAGIC:
            type_weights[SkillType.CHANNELED] = 0.20
            type_weights[SkillType.ACTIVE] = 0.30
        elif category == SkillCategory.STEALTH:
            type_weights[SkillType.TRIGGER] = 0.20
            type_weights[SkillType.TOGGLE] = 0.15

        if tier == SkillTier.ULTIMATE:
            type_weights = {
                SkillType.ACTIVE: 0.50,
                SkillType.CHANNELED: 0.30,
                SkillType.AURA: 0.20,
            }

        items = list(type_weights.items())
        total = sum(w for _, w in items)
        roll = rng.uniform(0, total)
        cumulative = 0.0
        for skill_type, weight in items:
            cumulative += weight
            if roll <= cumulative:
                return skill_type
        return SkillType.ACTIVE

    def _generate_stat_bonuses(
        self,
        category: SkillCategory,
        tier: SkillTier,
        stat_focus: Dict[str, float],
        rng: random.Random,
    ) -> Dict[str, float]:
        """Generate stat bonuses for a skill node based on its category and tier."""
        tier_multiplier = {
            SkillTier.TIER_1: 1.0,
            SkillTier.TIER_2: 1.5,
            SkillTier.TIER_3: 2.2,
            SkillTier.TIER_4: 3.0,
            SkillTier.TIER_5: 4.5,
            SkillTier.ULTIMATE: 7.0,
        }.get(tier, 1.0)

        bonuses: Dict[str, float] = {}
        stat_pool = STAT_POOL_BY_CATEGORY.get(category, ["strength", "agility"])
        num_bonuses = rng.randint(1, min(3, len(stat_pool)))

        selected_stats = rng.sample(stat_pool, num_bonuses)

        for stat in selected_stats:
            base = rng.uniform(1.0, 5.0)
            focus_mult = stat_focus.get(stat, 0.3)
            value = round(base * tier_multiplier * (0.5 + focus_mult), 1)
            bonuses[stat] = value

        return bonuses

    def _generate_effect_description(
        self,
        skill_name: str,
        category: SkillCategory,
        tier: SkillTier,
        skill_type: SkillType,
        rng: random.Random,
    ) -> str:
        """Generate a descriptive effect string for a skill."""
        effect_templates: Dict[SkillCategory, List[str]] = {
            SkillCategory.COMBAT: [
                "Deals {damage} physical damage to target.",
                "Increases attack speed by {pct}% for {dur} seconds.",
                "Unleashes a flurry of {hits} strikes.",
            ],
            SkillCategory.DEFENSE: [
                "Reduces incoming damage by {pct}%.",
                "Grants a shield absorbing {amount} damage.",
                "Increases armor rating by {amount}.",
            ],
            SkillCategory.MAGIC: [
                "Deals {damage} magical damage to all enemies in range.",
                "Restores {amount} mana over {dur} seconds.",
                "Summons an elemental entity for {dur} seconds.",
            ],
            SkillCategory.UTILITY: [
                "Reduces cooldown of all abilities by {pct}%.",
                "Increases resource generation by {amount}%.",
                "Grants immunity to crowd control for {dur} seconds.",
            ],
            SkillCategory.MOVEMENT: [
                "Increases movement speed by {pct}% for {dur} seconds.",
                "Allows dashing through enemies.",
                "Grants the ability to double-jump.",
            ],
            SkillCategory.CRAFTING: [
                "Increases crafting success rate by {pct}%.",
                "Reduces material costs by {pct}%.",
                "Unlocks access to rare recipes.",
            ],
            SkillCategory.SOCIAL: [
                "Improves merchant prices by {pct}%.",
                "Increases NPC faction reputation gain.",
                "Unlocks special dialogue options.",
            ],
            SkillCategory.STEALTH: [
                "Becomes invisible for {dur} seconds.",
                "Increases critical hit chance from stealth by {pct}%.",
                "Reduces detection radius by {pct}%.",
            ],
            SkillCategory.SURVIVAL: [
                "Restores {amount} health over {dur} seconds.",
                "Reduces environmental damage by {pct}%.",
                "Increases maximum stamina by {amount}.",
            ],
            SkillCategory.LEADERSHIP: [
                "Allies gain {pct}% increased damage for {dur} seconds.",
                "Summons reinforcements to aid in battle.",
                "Increases party size limit by {amount}.",
            ],
        }

        templates = effect_templates.get(category, ["Provides a beneficial effect."])
        template = rng.choice(templates)

        tier_values = {
            SkillTier.TIER_1: (5, 15, 3),
            SkillTier.TIER_2: (10, 30, 5),
            SkillTier.TIER_3: (20, 50, 8),
            SkillTier.TIER_4: (35, 80, 12),
            SkillTier.TIER_5: (50, 120, 18),
            SkillTier.ULTIMATE: (80, 200, 30),
        }
        base_val, base_pct, base_dur = tier_values.get(tier, (5, 15, 3))

        return template.format(
            damage=rng.randint(base_val, base_val * 2),
            pct=rng.randint(base_pct, base_pct * 2),
            dur=rng.randint(base_dur, base_dur * 2),
            amount=rng.randint(base_val, base_val * 2),
            hits=rng.randint(2, 5),
        )

    # ------------------------------------------------------------------
    # Build Optimization
    # ------------------------------------------------------------------

    def optimize_build(
        self,
        tree_id: str,
        target_role: str,
        max_points: int,
    ) -> Optional[BuildOptimization]:
        """Find the optimal skill allocation for a given point budget.

        Uses a greedy algorithm with heuristic scoring that evaluates each
        node's stat bonuses, synergy with already-selected nodes, and
        cost efficiency. Nodes are ranked by value-per-point and selected
        until the point budget is exhausted.

        Args:
            tree_id: ID of the skill tree to optimize.
            target_role: The target role for optimization (e.g., "dps", "tank", "support").
            max_points: Maximum skill points available for allocation.

        Returns:
            A BuildOptimization with selected nodes and build score.
        """
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return None

            if max_points <= 0:
                return None

            role_stats = self._get_role_stat_weights(target_role)

            candidates: List[Tuple[SkillNode, float]] = []

            for node in tree.nodes.values():
                if node.unlock_cost > max_points:
                    continue

                base_value = self._evaluate_node_value(node, role_stats)

                tier_bonus = (TIER_ORDER.index(node.tier) + 1) * 1.5
                type_bonus = self._get_skill_type_bonus(node.skill_type)
                cost_efficiency = (base_value + tier_bonus + type_bonus) / max(node.unlock_cost, 1)

                candidates.append((node, cost_efficiency))

            candidates.sort(key=lambda x: x[1], reverse=True)

            selected: List[SkillNode] = []
            selected_ids: Set[str] = set()
            points_spent = 0
            total_score = 0.0

            for node, efficiency in candidates:
                if points_spent + node.unlock_cost > max_points:
                    continue

                if not self._can_select_node(node, selected_ids, tree):
                    continue

                synergy_bonus = self._compute_synergy_bonus(node, selected, role_stats)
                node_value = efficiency * node.unlock_cost + synergy_bonus

                selected.append(node)
                selected_ids.add(node.node_id)
                points_spent += node.unlock_cost
                total_score += node_value

            build_name = f"{tree.character_class.title()} {target_role.title()} Build"
            description = (
                f"Optimized {target_role} build for {tree.character_class} "
                f"with {max_points} points. Selected {len(selected)} nodes "
                f"spending {points_spent} points."
            )

            optimization = BuildOptimization(
                tree_id=tree_id,
                target_role=target_role,
                max_points=max_points,
                selected_nodes=[n.node_id for n in selected],
                build_score=round(total_score, 4),
                build_name=build_name,
                description=description,
            )
            self._optimizations[optimization.opt_id] = optimization
            self._stats["total_optimizations_run"] += 1

            if len(self._optimizations) > self.MAX_BUILD_OPTIMIZATIONS:
                self._evict_oldest_optimizations()

            return optimization

    def _get_role_stat_weights(self, target_role: str) -> Dict[str, float]:
        """Get stat importance weights for a given role."""
        role = target_role.lower().strip()
        role_weights: Dict[str, Dict[str, float]] = {
            "dps": {
                "strength": 0.8, "agility": 0.7, "dexterity": 0.8,
                "intelligence": 0.5, "cunning": 0.4,
                "perception": 0.3, "luck": 0.2, "endurance": 0.3,
            },
            "tank": {
                "vitality": 0.9, "endurance": 0.8, "strength": 0.6,
                "defense": 0.7, "spirit": 0.4, "wisdom": 0.3,
                "agility": 0.2, "luck": 0.1,
            },
            "support": {
                "wisdom": 0.8, "spirit": 0.8, "intelligence": 0.7,
                "charisma": 0.6, "perception": 0.5,
                "vitality": 0.3, "endurance": 0.3,
            },
            "caster": {
                "intelligence": 0.9, "wisdom": 0.7, "spirit": 0.7,
                "perception": 0.4, "cunning": 0.3,
                "vitality": 0.2, "agility": 0.2,
            },
            "hybrid": {
                "strength": 0.5, "agility": 0.5, "intelligence": 0.5,
                "dexterity": 0.5, "vitality": 0.4, "spirit": 0.4,
                "wisdom": 0.4, "endurance": 0.4,
            },
        }

        weights = role_weights.get(role, role_weights["hybrid"])
        for stat in STAT_NAMES:
            if stat not in weights:
                weights[stat] = 0.1
        return weights

    def _evaluate_node_value(
        self, node: SkillNode, role_stats: Dict[str, float]
    ) -> float:
        """Evaluate a node's base value given role stat weights."""
        if not node.stat_bonuses:
            return 1.0

        total = 0.0
        for stat, bonus in node.stat_bonuses.items():
            weight = role_stats.get(stat, 0.1)
            total += abs(bonus) * weight

        return total * node.max_level * 0.5

    def _get_skill_type_bonus(self, skill_type: SkillType) -> float:
        """Get a bonus multiplier for a skill type."""
        type_bonuses: Dict[SkillType, float] = {
            SkillType.PASSIVE: 2.0,
            SkillType.ACTIVE: 1.5,
            SkillType.AURA: 2.5,
            SkillType.TRIGGER: 1.8,
            SkillType.CHANNELED: 1.2,
            SkillType.TOGGLE: 1.7,
        }
        return type_bonuses.get(skill_type, 1.0)

    def _can_select_node(
        self,
        node: SkillNode,
        selected_ids: Set[str],
        tree: SkillTree,
    ) -> bool:
        """Check if a node can be selected given current selections."""
        if node.node_id in selected_ids:
            return False

        for parent_id in node.parent_nodes:
            if parent_id not in selected_ids:
                prereq_node = tree.nodes.get(parent_id)
                if prereq_node is not None and prereq_node.tier != SkillTier.TIER_1:
                    return False

        return True

    def _compute_synergy_bonus(
        self,
        node: SkillNode,
        selected: List[SkillNode],
        role_stats: Dict[str, float],
    ) -> float:
        """Compute synergy bonus between a candidate node and already selected nodes."""
        if not selected:
            return 0.0

        total_synergy = 0.0

        for selected_node in selected:
            cat_synergy = CATEGORY_SYNERGY.get(node.category, {}).get(
                selected_node.category, 0.0
            )

            if selected_node.node_id in node.parent_nodes or node.node_id in selected_node.child_nodes:
                cat_synergy += 0.3

            stat_overlap = 0
            for stat in node.stat_bonuses:
                if stat in selected_node.stat_bonuses:
                    stat_overlap += 1
            if stat_overlap > 0:
                cat_synergy += stat_overlap * 0.15

            total_synergy += cat_synergy

        return total_synergy * 0.5

    # ------------------------------------------------------------------
    # Tree Validation
    # ------------------------------------------------------------------

    def validate_tree(self, tree_id: str) -> Dict[str, Any]:
        """Validate a skill tree's structure and integrity.

        Checks for orphaned nodes, circular dependencies, invalid tier
        transitions, missing connections, and overall tree health.

        Args:
            tree_id: ID of the skill tree to validate.

        Returns:
            A dict with validation results including issues found and scores.
        """
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return {"valid": False, "error": "Tree not found"}

            issues: List[Dict[str, Any]] = []
            warnings: List[Dict[str, Any]] = []

            if not tree.nodes:
                issues.append({
                    "type": "empty_tree",
                    "message": "Tree has no nodes.",
                    "severity": "error",
                })
                return {
                    "valid": False,
                    "tree_id": tree_id,
                    "tree_name": tree.name,
                    "character_class": tree.character_class,
                    "total_nodes": 0,
                    "issues": issues,
                    "warnings": warnings,
                    "health_score": 0.0,
                }

            root_nodes = tree.get_root_nodes()
            if not root_nodes:
                issues.append({
                    "type": "no_root_nodes",
                    "message": "Tree has no root nodes. Every tree needs at least one entry point.",
                    "severity": "error",
                })

            tiers_present: Set[SkillTier] = set()
            for node in tree.nodes.values():
                tiers_present.add(node.tier)

                if node.tier != SkillTier.TIER_1 and not node.parent_nodes:
                    warnings.append({
                        "type": "orphan_node",
                        "node_id": node.node_id,
                        "node_name": node.name,
                        "tier": node.tier.value,
                        "message": f"Node '{node.name}' at {node.tier.value} has no parent connections.",
                        "severity": "warning",
                    })

                for parent_id in node.parent_nodes:
                    parent = tree.nodes.get(parent_id)
                    if parent is None:
                        issues.append({
                            "type": "broken_reference",
                            "node_id": node.node_id,
                            "node_name": node.name,
                            "missing_parent_id": parent_id,
                            "message": f"Node '{node.name}' references non-existent parent.",
                            "severity": "error",
                        })
                    elif TIER_ORDER.index(parent.tier) >= TIER_ORDER.index(node.tier):
                        issues.append({
                            "type": "invalid_tier_progression",
                            "node_id": node.node_id,
                            "node_name": node.name,
                            "parent_tier": parent.tier.value,
                            "node_tier": node.tier.value,
                            "message": f"Parent '{parent.name}' is at {parent.tier.value} but child is at {node.tier.value}.",
                            "severity": "error",
                        })

                for child_id in node.child_nodes:
                    if child_id not in tree.nodes:
                        issues.append({
                            "type": "broken_reference",
                            "node_id": node.node_id,
                            "node_name": node.name,
                            "missing_child_id": child_id,
                            "message": f"Node '{node.name}' references non-existent child.",
                            "severity": "error",
                        })

            if self._has_circular_dependency(tree):
                issues.append({
                    "type": "circular_dependency",
                    "message": "Tree contains circular dependencies between nodes.",
                    "severity": "error",
                })

            tier_counts: Dict[str, int] = {}
            for tier in TIER_ORDER:
                tier_counts[tier.value] = len(tree.get_by_tier(tier))

            category_counts: Dict[str, int] = {}
            for node in tree.nodes.values():
                category_counts[node.category.value] = category_counts.get(node.category.value, 0) + 1

            total_issues = len([i for i in issues if i["severity"] == "error"])
            total_warnings = len(warnings)
            health_score = 1.0
            if total_issues > 0:
                health_score = max(0.0, 1.0 - total_issues * 0.2)
            if total_warnings > 0:
                health_score = max(0.0, health_score - total_warnings * 0.05)

            return {
                "valid": total_issues == 0,
                "tree_id": tree_id,
                "tree_name": tree.name,
                "character_class": tree.character_class,
                "total_nodes": tree.total_nodes,
                "max_points": tree.max_points,
                "tier_distribution": tier_counts,
                "category_distribution": category_counts,
                "root_nodes": [n.name for n in root_nodes],
                "issues": issues,
                "warnings": warnings,
                "health_score": round(health_score, 4),
            }

    def _has_circular_dependency(self, tree: SkillTree) -> bool:
        """Detect circular dependencies in the tree using DFS."""
        visited: Set[str] = set()
        recursion_stack: Set[str] = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            recursion_stack.add(node_id)

            node = tree.nodes.get(node_id)
            if node is not None:
                for child_id in node.child_nodes:
                    if child_id not in visited:
                        if dfs(child_id):
                            return True
                    elif child_id in recursion_stack:
                        return True

            recursion_stack.discard(node_id)
            return False

        for node_id in tree.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False

    # ------------------------------------------------------------------
    # Tree Retrieval
    # ------------------------------------------------------------------

    def get_tree(self, tree_id: str) -> Optional[SkillTree]:
        """Retrieve a skill tree by its ID."""
        return self._trees.get(tree_id)

    def list_trees(self) -> List[SkillTree]:
        """List all skill trees."""
        return list(self._trees.values())

    def list_trees_by_class(self, character_class: str) -> List[SkillTree]:
        """List all skill trees for a specific character class."""
        class_key = character_class.lower().strip()
        return [t for t in self._trees.values() if t.character_class == class_key]

    def get_optimization(self, opt_id: str) -> Optional[BuildOptimization]:
        """Retrieve a build optimization by its ID."""
        return self._optimizations.get(opt_id)

    def list_optimizations(self, tree_id: Optional[str] = None) -> List[BuildOptimization]:
        """List all build optimizations, optionally filtered by tree ID."""
        if tree_id is not None:
            return [o for o in self._optimizations.values() if o.tree_id == tree_id]
        return list(self._optimizations.values())

    # ------------------------------------------------------------------
    # Comparison & Analysis
    # ------------------------------------------------------------------

    def compare_builds(
        self, opt_ids: List[str]
    ) -> Dict[str, Any]:
        """Compare multiple build optimizations side by side.

        Args:
            opt_ids: List of optimization IDs to compare.

        Returns:
            A dict with comparative data for each build.
        """
        with self._lock:
            builds: List[Dict[str, Any]] = []
            best_score = -1.0
            best_id: Optional[str] = None

            for oid in opt_ids:
                opt = self._optimizations.get(oid)
                if opt is None:
                    continue

                tree = self._trees.get(opt.tree_id)
                tree_name = tree.name if tree else "unknown"

                build_data = {
                    "opt_id": opt.opt_id,
                    "build_name": opt.build_name,
                    "tree_name": tree_name,
                    "target_role": opt.target_role,
                    "max_points": opt.max_points,
                    "nodes_selected": len(opt.selected_nodes),
                    "build_score": opt.build_score,
                }
                builds.append(build_data)

                if opt.build_score > best_score:
                    best_score = opt.build_score
                    best_id = opt.opt_id

            return {
                "builds_compared": len(builds),
                "builds": builds,
                "best_build_id": best_id,
                "best_score": best_score,
            }

    def export_tree(self, tree_id: str) -> Optional[Dict[str, Any]]:
        """Export a skill tree as a serializable dict.

        Returns the full tree structure including all nodes and their
        connections, suitable for serialization or API responses.
        """
        tree = self._trees.get(tree_id)
        if tree is None:
            return None
        return tree.to_dict()

    def import_tree(self, data: Dict[str, Any]) -> Optional[SkillTree]:
        """Import a skill tree from a serialized dict.

        Args:
            data: Dict containing tree data in the format produced by export_tree.

        Returns:
            The imported SkillTree, or None if the data is invalid.
        """
        with self._lock:
            tree = SkillTree(
                name=data.get("name", "Imported Tree"),
                character_class=data.get("character_class", ""),
                description=data.get("description", ""),
                max_points=data.get("max_points", 50),
            )
            self._trees[tree.tree_id] = tree

            for node_data in data.get("nodes", []):
                category = SkillCategory(node_data.get("category", "combat"))
                tier = SkillTier(node_data.get("tier", "tier_1"))
                skill_type = SkillType(node_data.get("skill_type", "active"))

                node = SkillNode(
                    node_id=node_data.get("node_id", uuid.uuid4().hex),
                    name=node_data.get("name", ""),
                    category=category,
                    tier=tier,
                    skill_type=skill_type,
                    description=node_data.get("description", ""),
                    effect_description=node_data.get("effect_description", ""),
                    max_level=node_data.get("max_level", 5),
                    current_level=node_data.get("current_level", 0),
                    requirements=node_data.get("requirements", {}),
                    unlock_cost=node_data.get("unlock_cost", 1),
                    stat_bonuses=node_data.get("stat_bonuses", {}),
                    parent_nodes=node_data.get("parent_nodes", []),
                    child_nodes=node_data.get("child_nodes", []),
                    position_x=node_data.get("position_x", 0.0),
                    position_y=node_data.get("position_y", 0.0),
                )
                tree.nodes[node.node_id] = node
                self._node_index[node.node_id] = tree.tree_id

            tree.total_nodes = len(tree.nodes)
            self._stats["total_trees_created"] += 1
            return tree

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for the skill tree engine."""
        with self._lock:
            total_nodes = sum(t.total_nodes for t in self._trees.values())
            total_optimizations = len(self._optimizations)

            class_counts: Dict[str, int] = {}
            for tree in self._trees.values():
                cc = tree.character_class
                class_counts[cc] = class_counts.get(cc, 0) + 1

            avg_nodes_per_tree = (
                total_nodes / len(self._trees) if self._trees else 0.0
            )

            tier_counts: Dict[str, int] = {}
            category_counts: Dict[str, int] = {}
            for tree in self._trees.values():
                for node in tree.nodes.values():
                    tier_counts[node.tier.value] = tier_counts.get(node.tier.value, 0) + 1
                    category_counts[node.category.value] = category_counts.get(node.category.value, 0) + 1

            return {
                "total_trees": len(self._trees),
                "total_nodes": total_nodes,
                "total_optimizations": total_optimizations,
                "avg_nodes_per_tree": round(avg_nodes_per_tree, 1),
                "trees_by_class": class_counts,
                "nodes_by_tier": tier_counts,
                "nodes_by_category": category_counts,
                "available_classes": list(CLASS_ARCHETYPES.keys()),
                "available_categories": [c.value for c in SkillCategory],
                "available_tiers": [t.value for t in SkillTier],
                "available_skill_types": [st.value for st in SkillType],
                "total_trees_created_lifetime": self._stats["total_trees_created"],
                "total_nodes_created_lifetime": self._stats["total_nodes_created"],
                "total_optimizations_run_lifetime": self._stats["total_optimizations_run"],
                "total_connections_made_lifetime": self._stats["total_connections_made"],
            }

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire skill tree engine state."""
        with self._lock:
            self._trees.clear()
            self._optimizations.clear()
            self._node_index.clear()
            self._stats = {
                "total_trees_created": 0,
                "total_nodes_created": 0,
                "total_optimizations_run": 0,
                "total_connections_made": 0,
            }

    def _evict_oldest_trees(self) -> None:
        """Remove the oldest trees when the maximum count is exceeded."""
        excess = len(self._trees) - self.MAX_TREES
        if excess <= 0:
            return
        sorted_trees = sorted(
            self._trees.items(), key=lambda kv: kv[1].created_at
        )
        for tid, tree in sorted_trees[:excess]:
            for node_id in tree.nodes:
                self._node_index.pop(node_id, None)
            self._trees.pop(tid, None)

    def _evict_oldest_optimizations(self) -> None:
        """Remove the lowest-scoring optimizations when the maximum is exceeded."""
        excess = len(self._optimizations) - self.MAX_BUILD_OPTIMIZATIONS
        if excess <= 0:
            return
        sorted_opts = sorted(
            self._optimizations.items(), key=lambda kv: kv[1].build_score
        )
        for oid, _ in sorted_opts[:excess]:
            self._optimizations.pop(oid, None)


# ------------------------------------------------------------------
# Module-level accessor
# ------------------------------------------------------------------


def get_skill_tree_engine() -> SkillTreeEngine:
    """Return the singleton SkillTreeEngine instance."""
    return SkillTreeEngine.get_instance()