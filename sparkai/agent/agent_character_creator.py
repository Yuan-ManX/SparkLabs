"""
SparkLabs Agent - Character Creator

AI-driven character creation system for the SparkLabs AI-native game engine.
Generates player characters, NPCs, enemies, bosses with complete attributes,
backstories, abilities, and visual descriptions. Supports intelligent stat
allocation based on class, race bonuses, role-appropriate equipment, and
thematic design for bosses with unique mechanics and multiple phases.

Architecture:
  CharacterCreatorEngine (Singleton)
    |-- CharacterRole (narrative role categorization)
    |-- CharacterClass (combat archetype classification)
    |-- CharacterRace (species and heritage definition)
    |-- Alignment (moral and ethical compass)
    |-- CharacterAttribute (individual stat with bounds)
    |-- CharacterAbility (action or spell definition)
    |-- CharacterProfile (complete character data model)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# Enums
# =============================================================================


class CharacterRole(Enum):
    """Narrative role categorization defining how a character interacts with the game world."""

    PLAYER = "player"
    NPC = "npc"
    ENEMY = "enemy"
    BOSS = "boss"
    COMPANION = "companion"
    MERCHANT = "merchant"
    QUEST_GIVER = "quest_giver"
    TRAINER = "trainer"
    GUARDIAN = "guardian"
    VILLAIN = "villain"


class CharacterClass(Enum):
    """Combat archetype classification defining primary ability and stat orientation."""

    WARRIOR = "warrior"
    MAGE = "mage"
    ROGUE = "rogue"
    RANGER = "ranger"
    CLERIC = "cleric"
    PALADIN = "paladin"
    DRUID = "druid"
    NECROMANCER = "necromancer"
    BARD = "bard"
    MONK = "monk"
    BARBARIAN = "barbarian"
    SORCERER = "sorcerer"
    WARLOCK = "warlock"
    ALCHEMIST = "alchemist"
    ENGINEER = "engineer"


class CharacterRace(Enum):
    """Species and heritage definition affecting base stats and racial traits."""

    HUMAN = "human"
    ELF = "elf"
    DWARF = "dwarf"
    ORC = "orc"
    GOBLIN = "goblin"
    DRAGONBORN = "dragonborn"
    TIEFLING = "tiefling"
    HALFLING = "halfling"
    GNOME = "gnome"
    FAIRY = "fairy"
    UNDEAD = "undead"
    ELEMENTAL = "elemental"
    BEASTKIN = "beastkin"
    CELESTIAL = "celestial"
    DEMONIC = "demonic"


class Alignment(Enum):
    """Moral and ethical compass governing character behavior and decision-making tendencies."""

    LAWFUL_GOOD = "lawful_good"
    NEUTRAL_GOOD = "neutral_good"
    CHAOTIC_GOOD = "chaotic_good"
    LAWFUL_NEUTRAL = "lawful_neutral"
    TRUE_NEUTRAL = "true_neutral"
    CHAOTIC_NEUTRAL = "chaotic_neutral"
    LAWFUL_EVIL = "lawful_evil"
    NEUTRAL_EVIL = "neutral_evil"
    CHAOTIC_EVIL = "chaotic_evil"


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class CharacterAttribute:
    """Individual character stat with current value and configurable bounds.

    Attributes:
        attr_id: Unique identifier for this attribute instance.
        name: Display name of the attribute (e.g. "Strength", "Intelligence").
        value: Current numeric value of the attribute.
        min_value: Minimum allowed value for this attribute.
        max_value: Maximum allowed value for this attribute.
        description: Human-readable description of what this attribute governs.
    """

    attr_id: str
    name: str
    value: float
    min_value: float = 1.0
    max_value: float = 100.0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the attribute to a dictionary."""
        return {
            "attr_id": self.attr_id,
            "name": self.name,
            "value": self.value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "description": self.description,
        }


@dataclass
class CharacterAbility:
    """Combat or utility ability with scaling parameters and unlock conditions.

    Attributes:
        ability_id: Unique identifier for this ability.
        name: Display name of the ability.
        description: Flavor and mechanical description of the ability's effect.
        damage: Base damage value dealt by the ability.
        cooldown: Cooldown duration in seconds between uses.
        mana_cost: Mana or energy resource cost to activate.
        level_required: Minimum character level needed to unlock this ability.
        effects: List of additional effect descriptors (e.g. "stun", "bleed", "burn").
    """

    ability_id: str
    name: str
    description: str = ""
    damage: float = 0.0
    cooldown: float = 0.0
    mana_cost: float = 0.0
    level_required: int = 1
    effects: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the ability to a dictionary."""
        return {
            "ability_id": self.ability_id,
            "name": self.name,
            "description": self.description,
            "damage": self.damage,
            "cooldown": self.cooldown,
            "mana_cost": self.mana_cost,
            "level_required": self.level_required,
            "effects": list(self.effects),
        }


@dataclass
class CharacterProfile:
    """Complete character data model bundling all identity, mechanical, and narrative data.

    Attributes:
        profile_id: Universally unique identifier for this character.
        name: Character's display name.
        role: Narrative role this character serves in the game world.
        char_class: Combat archetype class.
        race: Species and heritage.
        level: Current power level of the character.
        alignment: Moral and ethical alignment determining behavioral tendencies.
        attributes: Collection of core stats (strength, agility, intelligence, etc.).
        abilities: Collection of unlocked combat and utility abilities.
        backstory: Narrative history and origin story of the character.
        appearance: Visual and physical description for rendering and narrative.
        personality_traits: Key behavioral descriptors.
        equipment: List of equipped items, weapons, and armor.
        faction: Political or social group affiliation.
        created_at: Timestamp of character creation.
    """

    profile_id: str
    name: str
    role: CharacterRole
    char_class: CharacterClass
    race: CharacterRace
    level: int
    alignment: Alignment
    attributes: List[CharacterAttribute] = field(default_factory=list)
    abilities: List[CharacterAbility] = field(default_factory=list)
    backstory: str = ""
    appearance: str = ""
    personality_traits: List[str] = field(default_factory=list)
    equipment: List[str] = field(default_factory=list)
    faction: str = ""
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the full profile to a dictionary."""
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "role": self.role.value,
            "char_class": self.char_class.value,
            "race": self.race.value,
            "level": self.level,
            "alignment": self.alignment.value,
            "attributes": [a.to_dict() for a in self.attributes],
            "abilities": [a.to_dict() for a in self.abilities],
            "backstory": self.backstory,
            "appearance": self.appearance,
            "personality_traits": list(self.personality_traits),
            "equipment": list(self.equipment),
            "faction": self.faction,
            "created_at": self.created_at,
        }


# =============================================================================
# Procedural Generation Data Pools
# =============================================================================

# Base attributes shared across all character classes
_BASE_ATTRIBUTE_NAMES: List[str] = [
    "Strength",
    "Agility",
    "Intelligence",
    "Vitality",
    "Wisdom",
    "Dexterity",
    "Charisma",
    "Endurance",
    "Perception",
    "Willpower",
]

_BASE_ATTRIBUTE_DESCRIPTIONS: Dict[str, str] = {
    "Strength": "Physical power, melee damage, and carrying capacity.",
    "Agility": "Speed, dodge chance, and attack speed.",
    "Intelligence": "Magical power, spell complexity, and knowledge-based checks.",
    "Vitality": "Health points, stamina, and resistance to physical ailments.",
    "Wisdom": "Mana regeneration, insight, and resistance to mental effects.",
    "Dexterity": "Precision, critical hit chance, and ranged accuracy.",
    "Charisma": "Social influence, persuasion, and companion morale.",
    "Endurance": "Damage resistance, stamina pool, and survival in harsh conditions.",
    "Perception": "Detection of traps, hidden enemies, and environmental details.",
    "Willpower": "Mental fortitude, fear resistance, and concentration maintenance.",
}

# Class-based attribute weight multipliers (controls stat distribution)
_CLASS_ATTRIBUTE_WEIGHTS: Dict[CharacterClass, Dict[str, float]] = {
    CharacterClass.WARRIOR: {
        "Strength": 2.0, "Vitality": 1.5, "Endurance": 1.5,
        "Agility": 0.8, "Dexterity": 0.8, "Intelligence": 0.4,
        "Wisdom": 0.5, "Charisma": 0.6, "Perception": 0.6, "Willpower": 0.8,
    },
    CharacterClass.MAGE: {
        "Intelligence": 2.5, "Wisdom": 1.8, "Willpower": 1.5,
        "Strength": 0.3, "Vitality": 0.5, "Agility": 0.5,
        "Dexterity": 0.6, "Endurance": 0.4, "Charisma": 0.6, "Perception": 0.8,
    },
    CharacterClass.ROGUE: {
        "Dexterity": 2.2, "Agility": 2.0, "Perception": 1.5,
        "Strength": 0.6, "Intelligence": 0.5, "Wisdom": 0.5,
        "Vitality": 0.7, "Charisma": 0.8, "Endurance": 0.5, "Willpower": 0.6,
    },
    CharacterClass.RANGER: {
        "Dexterity": 2.0, "Perception": 1.8, "Agility": 1.5,
        "Strength": 0.7, "Wisdom": 1.2, "Vitality": 0.8,
        "Endurance": 1.0, "Intelligence": 0.5, "Charisma": 0.6, "Willpower": 0.7,
    },
    CharacterClass.CLERIC: {
        "Wisdom": 2.2, "Vitality": 1.5, "Willpower": 1.5,
        "Strength": 0.6, "Charisma": 1.2, "Intelligence": 0.8,
        "Agility": 0.5, "Dexterity": 0.5, "Endurance": 0.7, "Perception": 0.6,
    },
    CharacterClass.PALADIN: {
        "Strength": 1.8, "Vitality": 1.8, "Charisma": 1.5,
        "Wisdom": 0.8, "Endurance": 1.2, "Willpower": 1.0,
        "Agility": 0.5, "Dexterity": 0.5, "Intelligence": 0.5, "Perception": 0.6,
    },
    CharacterClass.DRUID: {
        "Wisdom": 2.0, "Vitality": 1.3, "Agility": 1.2,
        "Intelligence": 1.0, "Perception": 1.0, "Willpower": 1.2,
        "Strength": 0.6, "Dexterity": 0.6, "Endurance": 0.8, "Charisma": 0.7,
    },
    CharacterClass.NECROMANCER: {
        "Intelligence": 2.3, "Willpower": 1.8, "Wisdom": 1.0,
        "Vitality": 0.6, "Strength": 0.4, "Agility": 0.4,
        "Dexterity": 0.5, "Endurance": 0.5, "Charisma": 0.4, "Perception": 0.7,
    },
    CharacterClass.BARD: {
        "Charisma": 2.5, "Agility": 1.3, "Dexterity": 1.3,
        "Intelligence": 0.8, "Wisdom": 0.8, "Perception": 0.9,
        "Strength": 0.4, "Vitality": 0.6, "Endurance": 0.5, "Willpower": 0.7,
    },
    CharacterClass.MONK: {
        "Agility": 2.0, "Willpower": 1.8, "Dexterity": 1.5,
        "Wisdom": 1.2, "Strength": 0.8, "Vitality": 0.8,
        "Endurance": 0.7, "Perception": 0.9, "Intelligence": 0.5, "Charisma": 0.5,
    },
    CharacterClass.BARBARIAN: {
        "Strength": 2.3, "Vitality": 2.0, "Endurance": 1.8,
        "Agility": 0.6, "Willpower": 0.7, "Dexterity": 0.5,
        "Intelligence": 0.2, "Wisdom": 0.3, "Charisma": 0.5, "Perception": 0.5,
    },
    CharacterClass.SORCERER: {
        "Intelligence": 2.0, "Charisma": 1.8, "Willpower": 1.3,
        "Wisdom": 0.8, "Agility": 0.7, "Dexterity": 0.7,
        "Strength": 0.3, "Vitality": 0.5, "Endurance": 0.4, "Perception": 0.6,
    },
    CharacterClass.WARLOCK: {
        "Charisma": 2.2, "Intelligence": 1.8, "Willpower": 1.5,
        "Wisdom": 0.6, "Agility": 0.5, "Dexterity": 0.5,
        "Strength": 0.3, "Vitality": 0.6, "Endurance": 0.5, "Perception": 0.7,
    },
    CharacterClass.ALCHEMIST: {
        "Intelligence": 2.0, "Dexterity": 1.5, "Perception": 1.5,
        "Wisdom": 1.0, "Agility": 0.8, "Willpower": 0.8,
        "Strength": 0.4, "Vitality": 0.6, "Endurance": 0.5, "Charisma": 0.6,
    },
    CharacterClass.ENGINEER: {
        "Intelligence": 2.2, "Dexterity": 1.8, "Perception": 1.3,
        "Wisdom": 0.8, "Agility": 0.7, "Willpower": 0.7,
        "Strength": 0.5, "Vitality": 0.6, "Endurance": 0.5, "Charisma": 0.6,
    },
}

# Race-based attribute bonuses (additive after class weighting)
_RACE_ATTRIBUTE_BONUSES: Dict[CharacterRace, Dict[str, float]] = {
    CharacterRace.HUMAN: {"Charisma": 2.0, "Endurance": 1.5},
    CharacterRace.ELF: {"Agility": 3.0, "Perception": 2.0},
    CharacterRace.DWARF: {"Strength": 2.0, "Vitality": 3.0},
    CharacterRace.ORC: {"Strength": 4.0, "Endurance": 2.0},
    CharacterRace.GOBLIN: {"Agility": 3.0, "Dexterity": 2.0},
    CharacterRace.DRAGONBORN: {"Strength": 3.0, "Willpower": 2.0},
    CharacterRace.TIEFLING: {"Intelligence": 2.0, "Charisma": 2.0},
    CharacterRace.HALFLING: {"Agility": 2.0, "Dexterity": 3.0},
    CharacterRace.GNOME: {"Intelligence": 3.0, "Wisdom": 2.0},
    CharacterRace.FAIRY: {"Agility": 4.0, "Charisma": 2.0},
    CharacterRace.UNDEAD: {"Vitality": 2.0, "Willpower": 3.0},
    CharacterRace.ELEMENTAL: {"Intelligence": 2.0, "Endurance": 2.0},
    CharacterRace.BEASTKIN: {"Strength": 2.0, "Agility": 2.0},
    CharacterRace.CELESTIAL: {"Wisdom": 3.0, "Willpower": 3.0},
    CharacterRace.DEMONIC: {"Strength": 2.0, "Intelligence": 2.0},
}

# Name pools for random generation
_FIRST_NAMES_HUMAN: List[str] = [
    "Aldric", "Brynn", "Cedric", "Dorian", "Elara", "Fynn", "Gareth",
    "Helena", "Isolde", "Jorah", "Kael", "Lyra", "Magnus", "Nyssa",
    "Orin", "Petra", "Quinn", "Rowan", "Seren", "Thalia", "Ulric",
    "Valen", "Willow", "Xander", "Yara", "Zephyr",
]
_FIRST_NAMES_ELF: List[str] = [
    "Aerendir", "Belenor", "Caenthir", "Daeleth", "Eryndor", "Faeris",
    "Galaen", "Haelwyn", "Ithilwen", "Jaereth", "Kaelen", "Liriel",
    "Maeglin", "Naeris", "Oropher", "Phaedra", "Quelith", "Rivallon",
]
_FIRST_NAMES_DWARF: List[str] = [
    "Baldrek", "Durgan", "Faldrek", "Gormak", "Haldrek", "Kazgor",
    "Moradin", "Norgrim", "Rurik", "Thaldrek", "Ulfgar", "Valdrek",
]
_FIRST_NAMES_ORC: List[str] = [
    "Gorak", "Krogar", "Morgath", "Ragnok", "Shagra", "Throk",
    "Urag", "Vargash", "Zogath", "Drakka", "Gnarsh", "Moktar",
]
_FIRST_NAMES_OTHER: List[str] = [
    "Astra", "Blix", "Cinder", "Draven", "Echo", "Flint", "Glimmer",
    "Hex", "Ivy", "Jinx", "Kestrel", "Luna", "Mist", "Nyx", "Opal",
]

# Surname pool
_SURNAMES: List[str] = [
    "Ashford", "Blackwood", "Crestfall", "Dawnstrider", "Ebonhart",
    "Frostborne", "Grimward", "Hawthorn", "Ironvein", "Jadeheart",
    "Kingsley", "Lightbringer", "Moonshadow", "Nightwind", "Oakenshield",
    "Proudmoore", "Quickblade", "Ravenwood", "Stormwind", "Thornfield",
    "Underwood", "Vexmoor", "Whitestone", "Yewheart", "Zenith",
]

# Faction names
_FACTIONS: List[str] = [
    "The Iron Vanguard", "Arcane Consortium", "Shadow Syndicate",
    "Emerald Wardens", "Crimson Order", "Silver Dawn",
    "The Free Marches", "Obsidian Circle", "Golden Concordat",
    "Stormguard Legion", "The Unseen Hand", "Celestial Accord",
]

# Location names
_LOCATIONS: List[str] = [
    "Ravenwatch", "Duskhollow", "Ironforge", "Silverbrook",
    "Thornhaven", "Darkwater", "Sunspire", "Grimmoor",
    "Brightfield", "Shadowfen", "Frostpeak", "Embervale",
]

# Personality traits pool
_PERSONALITY_TRAITS: List[str] = [
    "Brave", "Cautious", "Charismatic", "Cunning", "Curious",
    "Determined", "Diplomatic", "Fierce", "Generous", "Gruff",
    "Honorable", "Impulsive", "Loyal", "Mysterious", "Optimistic",
    "Pessimistic", "Pragmatic", "Reckless", "Sarcastic", "Stoic",
    "Suspicious", "Warm", "Wise", "Witty", "Zealous",
]

# Backstory templates by role
_BACKSTORY_TEMPLATES: Dict[CharacterRole, List[str]] = {
    CharacterRole.PLAYER: [
        "A wandering {race} {char_class} from {location}, driven by a personal quest for redemption after a tragic loss.",
        "Born to a humble family in {location}, this {race} {char_class} discovered their latent power when their village was threatened.",
        "Once a student at a prestigious academy, this {race} {char_class} abandoned formal training to seek real-world experience.",
        "A survivor of a great war, this {race} {char_class} now travels the land seeking purpose and a place to belong.",
        "Raised by mentors in the hidden enclaves of {location}, this {race} {char_class} carries ancient secrets and a mysterious destiny.",
    ],
    CharacterRole.NPC: [
        "A lifelong resident of {location}, this {race} {char_class} knows every alley and rumor in town.",
        "Having traveled from a distant land, this {race} {char_class} settled in {location} to start a quiet life.",
        "This {race} {char_class} works a humble trade in {location}, dreaming of adventure beyond the city walls.",
        "A former adventurer who retired to {location}, this {race} {char_class} now offers wisdom to wanderers.",
    ],
    CharacterRole.ENEMY: [
        "A {race} {char_class} corrupted by dark forces, now serving a greater evil that promises power.",
        "Once a guardian of {location}, this {race} {char_class} turned to banditry after being betrayed.",
        "A merciless {race} {char_class} who preys on travelers near {location}, driven by greed and savagery.",
        "A fanatical cultist of {race} origin, trained as a {char_class}, spreading chaos in the name of a dark deity.",
    ],
    CharacterRole.BOSS: [
        "The {race} {char_class} who once ruled {location} with wisdom, now twisted by forbidden magic into a tyrannical overlord.",
        "A {race} {char_class} of legendary power, sealed away for centuries beneath {location}, now unleashed by foolish treasure hunters.",
        "This {race} {char_class} commands an army of darkness from their fortress deep within {location}, seeking to reshape the world.",
        "An ancient {race} {char_class} who made a pact with shadowy entities, gaining immortality at the cost of their soul.",
    ],
    CharacterRole.COMPANION: [
        "A loyal {race} {char_class} who befriended the hero during a tavern brawl in {location}, seeking adventure and camaraderie.",
        "This {race} {char_class} was rescued from captors in {location} and now fights alongside their liberator with unwavering devotion.",
    ],
    CharacterRole.MERCHANT: [
        "A shrewd {race} {char_class} who built a trading empire from a single market stall in {location}.",
        "This {race} {char_class} travels between settlements, peddling rare goods acquired through questionable means.",
    ],
    CharacterRole.QUEST_GIVER: [
        "A respected {race} {char_class} elder of {location}, seeking aid for a problem beyond their community's ability to solve.",
        "A mysterious {race} {char_class} who appears in {location} with urgent tasks and promises of rich rewards.",
    ],
    CharacterRole.TRAINER: [
        "A veteran {race} {char_class} who retired from adventuring to train the next generation in {location}.",
        "This {race} {char_class} mastered their art through decades of practice and now teaches in a secluded school near {location}.",
    ],
    CharacterRole.GUARDIAN: [
        "Appointed by the council of {location}, this {race} {char_class} stands vigilant against all threats to the realm.",
        "A {race} {char_class} bound by an ancient oath to protect the sacred sites surrounding {location}.",
    ],
    CharacterRole.VILLAIN: [
        "A {race} {char_class} who believes their cruel methods are justified, seeking to impose order on {location} through absolute control.",
        "A charismatic {race} {char_class} manipulating the politics of {location} from the shadows, orchestrating chaos for personal gain.",
    ],
}

# Default backstory fallback
_DEFAULT_BACKSTORY: str = (
    "A mysterious {race} {char_class} whose past is shrouded in secrecy, "
    "wandering from {location} with unknown intentions."
)

# Appearance templates by race
_APPEARANCE_TEMPLATES: Dict[CharacterRace, List[str]] = {
    CharacterRace.HUMAN: [
        "Tall and broad-shouldered with weathered skin and a strong jawline. Short-cropped brown hair and determined green eyes.",
        "Lean and athletic with fair skin. Long auburn hair tied back, revealing sharp blue eyes and a confident smirk.",
        "Medium build with olive complexion and calloused hands. Dark curly hair and warm brown eyes that convey quiet wisdom.",
    ],
    CharacterRace.ELF: [
        "Tall and slender with porcelain skin and angular features. Long silver hair cascades past pointed ears, framing luminous violet eyes.",
        "Graceful with golden skin and emerald eyes. Flowing blonde hair adorned with delicate forest blooms. Elegant pointed ears.",
        "Athletic build with pale complexion. Dark hair braided with silver thread. Piercing grey eyes that seem to see through time.",
    ],
    CharacterRace.DWARF: [
        "Stocky and muscular with ruddy skin. Thick braided auburn beard adorned with iron rings. Deep-set brown eyes under bushy brows.",
        "Short and powerfully built with tanned skin. Immaculate black beard woven into intricate patterns. Piercing blue eyes.",
        "Broad and stout with granite-grey skin tone. Long white beard reaching the belt. Mithril-bright eyes that glint in darkness.",
    ],
    CharacterRace.ORC: [
        "Towering and muscular with green-grey skin. Prominent lower tusks and ritual scarification across the chest. Yellow eyes burning with intensity.",
        "Hulking frame with dark green hide. War-painted face and sharpened tusks. One eye clouded from battle, the other burning red.",
    ],
    CharacterRace.GOBLIN: [
        "Small and wiry with mottled green skin. Large pointed ears and clever yellow eyes. Nimble fingers constantly in motion.",
        "Diminutive with leathery grey-green hide. Overly large ears and a toothy grin. Quick, darting orange eyes miss nothing.",
    ],
    CharacterRace.DRAGONBORN: [
        "Imposing reptilian form with burnished bronze scales. A crest of horns crowns the draconic head. Molten gold eyes and a powerful tail.",
        "Sleek draconic build with deep crimson scales. Sharp facial horns and a frilled crest. Smoldering orange eyes with vertical slit pupils.",
    ],
    CharacterRace.TIEFLING: [
        "Humanoid with deep crimson skin. Curved ram-like horns sweep back from the temples. Solid black eyes and a sinuous tail. Faint infernal script glimmers on the arms.",
        "Lithe build with violet skin tone. Small ridged horns and golden eyes without pupils. A forked tail sways with subtle menace.",
    ],
    CharacterRace.HALFLING: [
        "Small and round with rosy cheeks and curly brown hair. Bright hazel eyes and an ever-present cheerful smile. Bare, calloused feet.",
        "Compact and nimble with sun-kissed skin. Sandy blonde hair tucked under a cap. Mischievous green eyes that sparkle with curiosity.",
    ],
    CharacterRace.GNOME: [
        "Tiny frame with expressive features and nut-brown skin. Wild white hair sticks out in all directions. Overly large blue eyes behind wire-rimmed spectacles.",
        "Petite build with fair complexion. Vibrant turquoise hair gathered in complex braids. Clever grey eyes that analyze everything.",
    ],
    CharacterRace.FAIRY: [
        "Tiny winged being with iridescent skin that shifts color. Delicate translucent wings shimmer with inner light. Large luminous eyes.",
        "Minuscule ethereal form surrounded by a faint glow. Butterfly-like wings in prismatic hues. Enormous silver eyes dominate the delicate face.",
    ],
    CharacterRace.UNDEAD: [
        "Gaunt figure with pale, desiccated skin stretched over visible bone structure. Glowing points of blue light where eyes once were.",
        "Skeletal form wrapped in tattered burial cloth. Faint runes pulse along exposed bones. A ghostly blue flame flickers in hollow eye sockets.",
    ],
    CharacterRace.ELEMENTAL: [
        "Humanoid shape formed from living stone and crystal veins. Geometric features and pulsing mineral deposits. Eyes like faceted gemstones.",
        "Swirling form of water and mist barely maintaining a humanoid silhouette. Bioluminescent blue patterns trace through the transparent body.",
    ],
    CharacterRace.BEASTKIN: [
        "Humanoid with feline features, covered in sleek black fur. Golden slit-pupiled eyes and tufted ears. A long tail flicks with predatory grace.",
        "Wolf-like humanoid with thick grey fur and lupine facial structure. Amber eyes reflect ambient light. Clawed hands and digitigrade legs.",
    ],
    CharacterRace.CELESTIAL: [
        "Radiant humanoid form with skin that softly glows with inner light. Feathery wing-like energy trails from the shoulders. Eyes like twin suns.",
        "Serene features with luminous pearl-white skin. A halo of soft light orbits the head. Eyes hold the depth of a star-filled sky.",
    ],
    CharacterRace.DEMONIC: [
        "Impressive horned figure with dark crimson skin and obsidian claws. Bat-like wings fold against a muscular back. Burning eyes peer from a shadowed face.",
        "Sinister form with charcoal-black hide and jagged bone protrusions. Multiple horns curve wickedly. Smoldering ember-colored eyes.",
    ],
}

# Default appearance fallback
_DEFAULT_APPEARANCE: str = "A {race} {char_class} of average height and build, wearing practical traveling clothes."

# Equipment by class
_EQUIPMENT_BY_CLASS: Dict[CharacterClass, List[str]] = {
    CharacterClass.WARRIOR: [
        "Steel Longsword", "Iron Shield", "Plate Armor", "Heavy Gauntlets",
    ],
    CharacterClass.MAGE: [
        "Arcane Staff", "Enchanted Robes", "Spell Tome", "Mana Crystal",
    ],
    CharacterClass.ROGUE: [
        "Twin Daggers", "Leather Armor", "Lockpick Set", "Smoke Bombs",
    ],
    CharacterClass.RANGER: [
        "Longbow", "Leather Armor", "Quiver of Arrows", "Hunting Knife",
    ],
    CharacterClass.CLERIC: [
        "Blessed Mace", "Chain Mail", "Holy Symbol", "Healing Salves",
    ],
    CharacterClass.PALADIN: [
        "Holy Greatsword", "Full Plate Armor", "Sacred Shield", "Blessed Amulet",
    ],
    CharacterClass.DRUID: [
        "Wooden Staff", "Hide Armor", "Herbal Pouch", "Nature Talisman",
    ],
    CharacterClass.NECROMANCER: [
        "Bone Wand", "Dark Robes", "Skull Amulet", "Soul Vial",
    ],
    CharacterClass.BARD: [
        "Lute", "Rapier", "Fine Clothing", "Performance Mask",
    ],
    CharacterClass.MONK: [
        "Quarterstaff", "Monk Robes", "Prayer Beads", "Meditation Mat",
    ],
    CharacterClass.BARBARIAN: [
        "Great Axe", "Hide Armor", "War Paint", "Totem Necklace",
    ],
    CharacterClass.SORCERER: [
        "Crystal Orb", "Silk Robes", "Dragon Scale", "Power Ring",
    ],
    CharacterClass.WARLOCK: [
        "Pact Blade", "Shadow Cloak", "Eldritch Grimoire", "Soul Shard",
    ],
    CharacterClass.ALCHEMIST: [
        "Alchemy Kit", "Reagent Satchel", "Protective Goggles", "Bomb Flask",
    ],
    CharacterClass.ENGINEER: [
        "Wrench", "Tool Belt", "Mechanical Gauntlet", "Blueprint Scroll",
    ],
}

# Role-specific equipment overrides
_ROLE_EQUIPMENT: Dict[CharacterRole, List[str]] = {
    CharacterRole.MERCHANT: ["Merchant Scales", "Coin Purse", "Trade Ledger", "Signet Ring"],
    CharacterRole.QUEST_GIVER: ["Sealed Scroll", "Town Map", "Official Seal", "Cipher Ring"],
    CharacterRole.TRAINER: ["Training Manual", "Wooden Practice Weapon", "Evaluation Ledger", "Whistle"],
    CharacterRole.GUARDIAN: ["Guard Armor", "Signal Horn", "City Keys", "Patrol Route Map"],
}

# Ability templates by class
_ABILITY_TEMPLATES: Dict[CharacterClass, List[Dict[str, Any]]] = {
    CharacterClass.WARRIOR: [
        {"name": "Power Strike", "desc": "A devastating overhead swing that crushes enemy defenses.", "damage_factor": 1.8, "cooldown": 6.0, "mana_cost": 15.0, "effects": ["armor_break"]},
        {"name": "Shield Bash", "desc": "Slam the shield into the enemy, stunning them briefly.", "damage_factor": 0.6, "cooldown": 8.0, "mana_cost": 10.0, "effects": ["stun"]},
        {"name": "War Cry", "desc": "A rallying shout that bolsters allies and intimidates foes.", "damage_factor": 0.0, "cooldown": 20.0, "mana_cost": 25.0, "effects": ["buff_allies", "intimidate"]},
        {"name": "Whirlwind", "desc": "Spin with weapon extended, striking all nearby enemies.", "damage_factor": 1.2, "cooldown": 12.0, "mana_cost": 30.0, "effects": ["aoe"]},
    ],
    CharacterClass.MAGE: [
        {"name": "Fireball", "desc": "Launch a sphere of flame that explodes on impact.", "damage_factor": 2.0, "cooldown": 8.0, "mana_cost": 40.0, "effects": ["burn", "aoe"]},
        {"name": "Ice Lance", "desc": "A piercing shard of ice that slows the target.", "damage_factor": 1.5, "cooldown": 5.0, "mana_cost": 25.0, "effects": ["slow", "pierce"]},
        {"name": "Arcane Shield", "desc": "Create a barrier of magical energy that absorbs damage.", "damage_factor": 0.0, "cooldown": 15.0, "mana_cost": 35.0, "effects": ["shield"]},
        {"name": "Lightning Bolt", "desc": "Call down a bolt of lightning that chains between enemies.", "damage_factor": 1.7, "cooldown": 10.0, "mana_cost": 45.0, "effects": ["chain", "shock"]},
    ],
    CharacterClass.ROGUE: [
        {"name": "Backstab", "desc": "A precise strike from the shadows dealing critical damage.", "damage_factor": 2.5, "cooldown": 6.0, "mana_cost": 15.0, "effects": ["critical", "bleed"]},
        {"name": "Shadow Step", "desc": "Blink behind the target, avoiding detection momentarily.", "damage_factor": 0.0, "cooldown": 12.0, "mana_cost": 20.0, "effects": ["teleport", "stealth"]},
        {"name": "Poison Blade", "desc": "Coat the weapon in venom that deals damage over time.", "damage_factor": 0.8, "cooldown": 10.0, "mana_cost": 15.0, "effects": ["poison", "dot"]},
        {"name": "Eviscerate", "desc": "A flurry of rapid strikes targeting vital areas.", "damage_factor": 1.6, "cooldown": 8.0, "mana_cost": 25.0, "effects": ["multi_hit"]},
    ],
    CharacterClass.RANGER: [
        {"name": "Precision Shot", "desc": "A carefully aimed arrow that hits weak points with lethal accuracy.", "damage_factor": 2.2, "cooldown": 7.0, "mana_cost": 20.0, "effects": ["armor_pierce"]},
        {"name": "Rain of Arrows", "desc": "Fire a volley that blankets an area with falling projectiles.", "damage_factor": 1.0, "cooldown": 14.0, "mana_cost": 35.0, "effects": ["aoe"]},
        {"name": "Trap", "desc": "Set a snare that roots and damages enemies who trigger it.", "damage_factor": 1.3, "cooldown": 18.0, "mana_cost": 25.0, "effects": ["root", "trap"]},
        {"name": "Hunter's Mark", "desc": "Mark an enemy, increasing damage they take from all sources.", "damage_factor": 0.0, "cooldown": 15.0, "mana_cost": 15.0, "effects": ["debuff"]},
    ],
    CharacterClass.CLERIC: [
        {"name": "Heal", "desc": "Restore health to a wounded ally with divine light.", "damage_factor": 0.0, "cooldown": 4.0, "mana_cost": 30.0, "effects": ["heal"]},
        {"name": "Smite", "desc": "Channel divine fury into a searing bolt of holy energy.", "damage_factor": 1.8, "cooldown": 8.0, "mana_cost": 35.0, "effects": ["holy"]},
        {"name": "Blessing", "desc": "Imbue an ally with divine favor, boosting their combat prowess.", "damage_factor": 0.0, "cooldown": 12.0, "mana_cost": 25.0, "effects": ["buff"]},
        {"name": "Purify", "desc": "Cleanse harmful effects from allies and deal light damage to undead.", "damage_factor": 0.5, "cooldown": 10.0, "mana_cost": 20.0, "effects": ["cleanse", "anti_undead"]},
    ],
    CharacterClass.PALADIN: [
        {"name": "Divine Strike", "desc": "Weapon glows with holy light, dealing bonus radiant damage.", "damage_factor": 1.6, "cooldown": 6.0, "mana_cost": 20.0, "effects": ["holy"]},
        {"name": "Lay on Hands", "desc": "Touch an ally to restore a significant amount of health.", "damage_factor": 0.0, "cooldown": 30.0, "mana_cost": 50.0, "effects": ["heal"]},
        {"name": "Aura of Courage", "desc": "Emit an aura that protects nearby allies from fear effects.", "damage_factor": 0.0, "cooldown": 25.0, "mana_cost": 40.0, "effects": ["aura", "fear_immune"]},
        {"name": "Judgment", "desc": "Pronounce judgment on a foe, dealing damage and reducing their defenses.", "damage_factor": 1.4, "cooldown": 10.0, "mana_cost": 30.0, "effects": ["debuff"]},
    ],
    CharacterClass.DRUID: [
        {"name": "Entangling Roots", "desc": "Vines erupt from the ground, immobilizing enemies in an area.", "damage_factor": 0.4, "cooldown": 12.0, "mana_cost": 30.0, "effects": ["root", "aoe"]},
        {"name": "Moonfire", "desc": "A beam of lunar energy burns the target with celestial fire.", "damage_factor": 1.5, "cooldown": 5.0, "mana_cost": 25.0, "effects": ["burn", "dot"]},
        {"name": "Wild Shape", "desc": "Transform into a beast, gaining new abilities and stats.", "damage_factor": 0.0, "cooldown": 20.0, "mana_cost": 50.0, "effects": ["transform"]},
        {"name": "Regrowth", "desc": "Nature's energy mends wounds over time.", "damage_factor": 0.0, "cooldown": 6.0, "mana_cost": 28.0, "effects": ["heal_over_time"]},
    ],
    CharacterClass.NECROMANCER: [
        {"name": "Raise Dead", "desc": "Reanimate a fallen corpse to fight as a skeletal minion.", "damage_factor": 0.0, "cooldown": 15.0, "mana_cost": 50.0, "effects": ["summon"]},
        {"name": "Life Drain", "desc": "Siphon life force from the target, healing the caster.", "damage_factor": 1.0, "cooldown": 8.0, "mana_cost": 25.0, "effects": ["lifesteal", "dot"]},
        {"name": "Bone Spear", "desc": "Launch a sharpened bone projectile that pierces through enemies.", "damage_factor": 1.6, "cooldown": 5.0, "mana_cost": 20.0, "effects": ["pierce"]},
        {"name": "Curse of Decay", "desc": "Place a curse that steadily erodes the target's health and defenses.", "damage_factor": 0.7, "cooldown": 12.0, "mana_cost": 35.0, "effects": ["curse", "dot", "debuff"]},
    ],
    CharacterClass.BARD: [
        {"name": "Inspiring Melody", "desc": "Play a tune that boosts ally attack power and morale.", "damage_factor": 0.0, "cooldown": 10.0, "mana_cost": 25.0, "effects": ["buff"]},
        {"name": "Dissonant Chord", "desc": "A harsh musical note that deals sonic damage and disorients.", "damage_factor": 1.3, "cooldown": 6.0, "mana_cost": 20.0, "effects": ["confuse"]},
        {"name": "Lullaby", "desc": "A soothing melody that puts enemies to sleep.", "damage_factor": 0.0, "cooldown": 20.0, "mana_cost": 35.0, "effects": ["sleep"]},
        {"name": "Heroic Ballad", "desc": "Recount a legendary tale, granting allies temporary damage immunity.", "damage_factor": 0.0, "cooldown": 60.0, "mana_cost": 60.0, "effects": ["immunity"]},
    ],
    CharacterClass.MONK: [
        {"name": "Flurry of Blows", "desc": "Unleash a rapid series of unarmed strikes.", "damage_factor": 1.4, "cooldown": 4.0, "mana_cost": 15.0, "effects": ["multi_hit"]},
        {"name": "Meditate", "desc": "Enter a meditative state, rapidly restoring energy and focus.", "damage_factor": 0.0, "cooldown": 15.0, "mana_cost": 0.0, "effects": ["self_regen"]},
        {"name": "Palm Strike", "desc": "A focused chi strike that bypasses armor and stuns briefly.", "damage_factor": 1.8, "cooldown": 10.0, "mana_cost": 25.0, "effects": ["armor_ignore", "stun"]},
        {"name": "Dodge Roll", "desc": "Perform an acrobatic evasion, becoming briefly untargetable.", "damage_factor": 0.0, "cooldown": 7.0, "mana_cost": 10.0, "effects": ["evade"]},
    ],
    CharacterClass.BARBARIAN: [
        {"name": "Rage", "desc": "Enter a berserk fury, massively increasing damage and resistance.", "damage_factor": 0.0, "cooldown": 30.0, "mana_cost": 0.0, "effects": ["self_buff", "damage_boost", "resist_boost"]},
        {"name": "Cleave", "desc": "A wide sweeping strike that hits multiple enemies at once.", "damage_factor": 1.3, "cooldown": 6.0, "mana_cost": 20.0, "effects": ["aoe"]},
        {"name": "Shattering Slam", "desc": "Slam the ground, creating a shockwave that damages and slows nearby foes.", "damage_factor": 1.1, "cooldown": 12.0, "mana_cost": 25.0, "effects": ["aoe", "slow"]},
        {"name": "Bloodlust", "desc": "Each hit fuels further bloodthirst, increasing attack speed temporarily.", "damage_factor": 0.0, "cooldown": 18.0, "mana_cost": 15.0, "effects": ["attack_speed_buff"]},
    ],
    CharacterClass.SORCERER: [
        {"name": "Meteor Swarm", "desc": "Call down a barrage of small meteors that scorch the earth.", "damage_factor": 1.8, "cooldown": 20.0, "mana_cost": 60.0, "effects": ["aoe", "burn"]},
        {"name": "Gust", "desc": "A blast of wind that pushes enemies back and disrupts formations.", "damage_factor": 0.5, "cooldown": 8.0, "mana_cost": 20.0, "effects": ["knockback"]},
        {"name": "Mana Surge", "desc": "Channel raw arcane energy into a devastating beam.", "damage_factor": 2.5, "cooldown": 15.0, "mana_cost": 55.0, "effects": ["pierce"]},
        {"name": "Blink", "desc": "Instantly teleport a short distance.", "damage_factor": 0.0, "cooldown": 5.0, "mana_cost": 10.0, "effects": ["teleport"]},
    ],
    CharacterClass.WARLOCK: [
        {"name": "Eldritch Blast", "desc": "Fire a bolt of crackling dark energy at the target.", "damage_factor": 1.5, "cooldown": 3.0, "mana_cost": 15.0, "effects": ["dark"]},
        {"name": "Demon Pact", "desc": "Summon a temporary demonic ally to fight alongside.", "damage_factor": 0.0, "cooldown": 25.0, "mana_cost": 50.0, "effects": ["summon", "dark"]},
        {"name": "Soul Leech", "desc": "Drain the target's essence, healing and empowering the caster.", "damage_factor": 1.2, "cooldown": 10.0, "mana_cost": 30.0, "effects": ["lifesteal", "self_buff"]},
        {"name": "Shadowbolt Volley", "desc": "Unleash a spread of shadow projectiles.", "damage_factor": 1.0, "cooldown": 8.0, "mana_cost": 35.0, "effects": ["aoe", "dark"]},
    ],
    CharacterClass.ALCHEMIST: [
        {"name": "Explosive Flask", "desc": "Hurl a volatile concoction that explodes on impact.", "damage_factor": 1.5, "cooldown": 8.0, "mana_cost": 20.0, "effects": ["aoe", "burn"]},
        {"name": "Healing Salve", "desc": "Apply a restorative ointment to close wounds quickly.", "damage_factor": 0.0, "cooldown": 5.0, "mana_cost": 15.0, "effects": ["heal"]},
        {"name": "Acid Spray", "desc": "Spray corrosive acid that eats through armor.", "damage_factor": 0.9, "cooldown": 6.0, "mana_cost": 18.0, "effects": ["armor_break", "dot"]},
        {"name": "Mutagen", "desc": "Drink an unstable elixir that temporarily morphs the body for combat.", "damage_factor": 0.0, "cooldown": 22.0, "mana_cost": 35.0, "effects": ["transform", "self_buff"]},
    ],
    CharacterClass.ENGINEER: [
        {"name": "Turret Deploy", "desc": "Place an automated turret that fires at nearby enemies.", "damage_factor": 0.6, "cooldown": 15.0, "mana_cost": 40.0, "effects": ["summon", "persistent"]},
        {"name": "Overcharge", "desc": "Overload the weapon with excess energy for a powerful shot.", "damage_factor": 2.2, "cooldown": 10.0, "mana_cost": 30.0, "effects": ["armor_pierce"]},
        {"name": "Repair Kit", "desc": "Use mechanical expertise to restore durability to equipment.", "damage_factor": 0.0, "cooldown": 12.0, "mana_cost": 20.0, "effects": ["repair"]},
        {"name": "Grenade", "desc": "Lob an explosive device that detonates after a short delay.", "damage_factor": 1.8, "cooldown": 10.0, "mana_cost": 25.0, "effects": ["aoe"]},
    ],
}

# Boss phase descriptors
_BOSS_PHASE_NAMES: List[str] = [
    "Phase of Wrath", "Phase of Shadows", "Phase of Ruin",
    "Phase of Despair", "Phase of Fury", "Phase of Ascension",
    "Phase of Corruption", "Phase of Eternity",
]

# Boss theme modifiers
_BOSS_THEMES: List[str] = [
    "dark", "elemental", "ancient", "cursed", "corrupted",
    "mechanical", "draconic", "void", "nature", "undead",
]

# Enemy difficulty scaling multipliers
_DIFFICULTY_SCALING: Dict[str, float] = {
    "easy": 0.7,
    "normal": 1.0,
    "hard": 1.4,
    "elite": 1.8,
    "deadly": 2.5,
}


# =============================================================================
# CharacterCreatorEngine (Singleton)
# =============================================================================


class CharacterCreatorEngine:
    """
    AI-driven character creation system for the AI-native game engine.

    Generates complete character profiles with intelligent attribute
    distribution, class and race synergy, role-appropriate equipment,
    and thematic backstory generation. Supports player characters,
    NPCs, enemies, bosses, companions, and specialized roles.

    Usage:
        creator = get_character_creator()
        hero = creator.create_character("Kael", CharacterRole.PLAYER,
            CharacterClass.MAGE, CharacterRace.ELF, level=5,
            alignment=Alignment.CHAOTIC_GOOD)
        boss = creator.generate_boss("Vorlag the Devourer", level=30, theme="dark")
        stats = creator.get_stats()
    """

    _instance: Optional["CharacterCreatorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "CharacterCreatorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "CharacterCreatorEngine":
        """Return the singleton CharacterCreatorEngine instance, initializing if needed."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize internal storage and counters."""
        if self._initialized:
            return
        self._initialized = True
        self._profiles: Dict[str, CharacterProfile] = {}
        self._abilities_store: Dict[str, Dict[str, CharacterAbility]] = {}
        self._total_created: int = 0
        self._total_abilities_added: int = 0
        self._recent_actions: deque = deque(maxlen=50)

    # ------------------------------------------------------------------
    # Core Character Creation
    # ------------------------------------------------------------------

    def create_character(
        self,
        name: str,
        role: CharacterRole,
        char_class: CharacterClass,
        race: CharacterRace,
        level: int = 1,
        alignment: Optional[Alignment] = None,
    ) -> CharacterProfile:
        """Create a character profile with specified parameters and generated details.

        Args:
            name: Display name for the character.
            role: Narrative role in the game world.
            char_class: Combat archetype class.
            race: Species and heritage.
            level: Power level, clamped to 1-100.
            alignment: Moral alignment; randomly selected if not provided.

        Returns:
            A fully populated CharacterProfile.
        """
        with self._lock:
            level = max(1, min(level, 100))
            if alignment is None:
                alignment = random.choice(list(Alignment))

            profile_id = str(uuid.uuid4())
            attributes = self._generate_attributes(char_class, race, level)
            abilities = self._generate_class_abilities(char_class, level)
            backstory = self._compose_backstory(role, race, char_class)
            appearance = self._generate_appearance(race, char_class)
            personality = self._select_personality(role)
            equipment = self._select_equipment(role, char_class)
            faction = random.choice(_FACTIONS)

            profile = CharacterProfile(
                profile_id=profile_id,
                name=name,
                role=role,
                char_class=char_class,
                race=race,
                level=level,
                alignment=alignment,
                attributes=attributes,
                abilities=abilities,
                backstory=backstory,
                appearance=appearance,
                personality_traits=personality,
                equipment=equipment,
                faction=faction,
                created_at=_time_module.time(),
            )

            self._profiles[profile_id] = profile
            self._abilities_store[profile_id] = {a.ability_id: a for a in abilities}
            self._total_created += 1
            self._recent_actions.append({
                "action": "create_character",
                "profile_id": profile_id,
                "name": name,
                "role": role.value,
                "class": char_class.value,
                "race": race.value,
                "level": level,
                "timestamp": _time_module.time(),
            })
            return profile

    def generate_random_character(
        self,
        role: Optional[CharacterRole] = None,
        level: Optional[int] = None,
    ) -> CharacterProfile:
        """Generate a fully randomized character with appropriate stats for class and race.

        Args:
            role: Narrative role; randomly selected if not provided.
            level: Power level; randomized between 1 and 50 if not provided.

        Returns:
            A randomly generated CharacterProfile.
        """
        with self._lock:
            if role is None:
                role = random.choice(list(CharacterRole))
            if level is None:
                level = random.randint(1, 50)

            char_class = random.choice(list(CharacterClass))
            race = random.choice(list(CharacterRace))
            alignment = random.choice(list(Alignment))
            name = self._generate_random_name(race)

            return self.create_character(
                name=name,
                role=role,
                char_class=char_class,
                race=race,
                level=level,
                alignment=alignment,
            )

    def generate_enemy(
        self,
        name: str,
        level: int,
        difficulty: str = "normal",
    ) -> CharacterProfile:
        """Generate an enemy character scaled to level and difficulty.

        Args:
            name: Display name for the enemy.
            level: Power level of the enemy.
            difficulty: Scaling tier (easy, normal, hard, elite, deadly).

        Returns:
            An enemy CharacterProfile with scaled stats and abilities.
        """
        with self._lock:
            char_class = random.choice(list(CharacterClass))
            race = random.choice(list(CharacterRace))
            alignment = random.choice([
                Alignment.CHAOTIC_EVIL,
                Alignment.NEUTRAL_EVIL,
                Alignment.LAWFUL_EVIL,
            ])

            scale = _DIFFICULTY_SCALING.get(difficulty, 1.0)
            scaled_level = max(1, min(100, int(level * scale)))

            profile = self.create_character(
                name=name,
                role=CharacterRole.ENEMY,
                char_class=char_class,
                race=race,
                level=scaled_level,
                alignment=alignment,
            )

            # Apply difficulty scaling to attributes
            with self._lock:
                for attr in profile.attributes:
                    attr.value = min(attr.max_value, attr.value * scale)
                    attr.value = round(attr.value, 1)

            return profile

    def generate_boss(
        self,
        name: str,
        level: int,
        theme: str = "dark",
    ) -> CharacterProfile:
        """Generate a boss character with unique mechanics, multiple phases,
        and thematic design.

        Args:
            name: Display name for the boss.
            level: Power level of the boss (typically higher than player level).
            theme: Thematic descriptor (dark, elemental, ancient, cursed,
                corrupted, mechanical, draconic, void, nature, undead).

        Returns:
            A boss CharacterProfile with special abilities and multi-phase design.
        """
        with self._lock:
            if theme not in _BOSS_THEMES:
                theme = "dark"

            # Boss classes are typically imposing archetypes
            boss_classes = [
                CharacterClass.WARRIOR, CharacterClass.MAGE,
                CharacterClass.PALADIN, CharacterClass.NECROMANCER,
                CharacterClass.BARBARIAN, CharacterClass.WARLOCK,
                CharacterClass.SORCERER,
            ]
            char_class = random.choice(boss_classes)

            # Boss races lean toward powerful or exotic
            boss_races = [
                CharacterRace.DRAGONBORN, CharacterRace.DEMONIC,
                CharacterRace.UNDEAD, CharacterRace.ELEMENTAL,
                CharacterRace.CELESTIAL, CharacterRace.ORC,
            ]
            race = random.choice(boss_races)

            alignment = random.choice([
                Alignment.CHAOTIC_EVIL,
                Alignment.LAWFUL_EVIL,
                Alignment.NEUTRAL_EVIL,
            ])

            profile = self.create_character(
                name=name,
                role=CharacterRole.BOSS,
                char_class=char_class,
                race=race,
                level=level,
                alignment=alignment,
            )

            # Override backstory with boss-specific narrative
            location = random.choice(_LOCATIONS)
            template = random.choice(_BACKSTORY_TEMPLATES.get(CharacterRole.BOSS, [str(_DEFAULT_BACKSTORY)]))
            profile.backstory = template.format(
                race=race.value, char_class=char_class.value, location=location
            )
            # Inject theme and phase information into backstory
            phase_1 = random.choice(_BOSS_PHASE_NAMES)
            phase_2 = random.choice(_BOSS_PHASE_NAMES)
            while phase_2 == phase_1:
                phase_2 = random.choice(_BOSS_PHASE_NAMES)
            profile.backstory += (
                f" The boss cycles through two phases in combat: {phase_1} (theme: {theme}) "
                f"and {phase_2}, each with distinct abilities and attack patterns."
            )

            # Boss gets extra abilities beyond class basics
            boss_extra_abilities = self._generate_boss_special_abilities(theme, level)
            for ab in boss_extra_abilities:
                profile.abilities.append(ab)
                self._abilities_store.setdefault(profile.profile_id, {})[ab.ability_id] = ab
                self._total_abilities_added += 1

            # Boss equipment is thematically imposing
            profile.equipment = self._generate_boss_equipment(theme, char_class)

            # Boost boss attributes by 1.5x
            for attr in profile.attributes:
                attr.value = min(attr.max_value, attr.value * 1.5)
                attr.value = round(attr.value, 1)

            return profile

    def generate_npc(
        self,
        name: str,
        role: CharacterRole,
        location: str = "",
    ) -> CharacterProfile:
        """Generate an NPC with role-appropriate stats, personality, and equipment.

        Args:
            name: Display name for the NPC.
            role: Narrative role (merchant, quest_giver, trainer, guardian, etc.).
            location: Town or region the NPC inhabits.

        Returns:
            An NPC CharacterProfile tailored to the specified role.
        """
        with self._lock:
            if not location:
                location = random.choice(_LOCATIONS)

            # Non-combat NPCs have lower levels
            npc_level_roles = {
                CharacterRole.MERCHANT: random.randint(2, 12),
                CharacterRole.QUEST_GIVER: random.randint(5, 20),
                CharacterRole.TRAINER: random.randint(15, 40),
                CharacterRole.GUARDIAN: random.randint(10, 30),
                CharacterRole.COMPANION: random.randint(3, 15),
                CharacterRole.VILLAIN: random.randint(20, 60),
            }
            level = npc_level_roles.get(role, random.randint(1, 15))

            char_class = random.choice(list(CharacterClass))
            race = random.choice(list(CharacterRace))
            alignment = random.choice(list(Alignment))

            profile = self.create_character(
                name=name,
                role=role,
                char_class=char_class,
                race=race,
                level=level,
                alignment=alignment,
            )

            # NPCs get location-specific backstory
            template = random.choice(
                _BACKSTORY_TEMPLATES.get(role, [str(_DEFAULT_BACKSTORY)])
            )
            profile.backstory = template.format(
                race=race.value, char_class=char_class.value, location=location
            )

            # Role-specific equipment override
            if role in _ROLE_EQUIPMENT:
                profile.equipment = list(_ROLE_EQUIPMENT[role])

            return profile

    # ------------------------------------------------------------------
    # Ability Management
    # ------------------------------------------------------------------

    def add_ability(
        self,
        profile_id: str,
        name: str,
        description: str = "",
        damage: float = 0.0,
        cooldown: float = 0.0,
        mana_cost: float = 0.0,
        level_required: int = 1,
        effects: Optional[List[str]] = None,
    ) -> Optional[CharacterAbility]:
        """Add a custom ability to an existing character.

        Args:
            profile_id: ID of the character to add the ability to.
            name: Display name of the ability.
            description: Flavor and mechanical description.
            damage: Base damage value.
            cooldown: Cooldown duration in seconds.
            mana_cost: Resource cost to activate.
            level_required: Minimum level to use this ability.
            effects: List of effect descriptors.

        Returns:
            The created CharacterAbility, or None if the profile is not found.
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None

            ability = CharacterAbility(
                ability_id=str(uuid.uuid4()),
                name=name,
                description=description,
                damage=damage,
                cooldown=cooldown,
                mana_cost=mana_cost,
                level_required=level_required,
                effects=effects or [],
            )

            profile.abilities.append(ability)
            self._abilities_store.setdefault(profile_id, {})[ability.ability_id] = ability
            self._total_abilities_added += 1
            self._recent_actions.append({
                "action": "add_ability",
                "profile_id": profile_id,
                "ability_name": name,
                "timestamp": _time_module.time(),
            })
            return ability

    # ------------------------------------------------------------------
    # Power Calculation
    # ------------------------------------------------------------------

    def calculate_power_level(self, profile_id: str) -> int:
        """Calculate an aggregate power score from attributes, abilities, and level.

        The power level is computed by summing the weighted attribute values,
        adding ability damage contributions, and factoring in the character level.

        Args:
            profile_id: ID of the character to evaluate.

        Returns:
            Integer power level score.
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return 0

            # Sum all attribute values
            attr_sum = sum(attr.value for attr in profile.attributes)

            # Sum all ability damage values
            ability_power = sum(ab.damage for ab in profile.abilities)

            # Factor in ability count (more abilities = more versatility)
            ability_count_bonus = len(profile.abilities) * 3

            # Level contributes directly
            level_factor = profile.level * 5

            # Compute weighted aggregate
            power = int(
                (attr_sum * 0.5)
                + (ability_power * 0.8)
                + ability_count_bonus
                + level_factor
            )

            return max(0, power)

    # ------------------------------------------------------------------
    # Backstory Generation
    # ------------------------------------------------------------------

    def generate_backstory(self, profile_id: str) -> str:
        """Generate or regenerate a backstory for an existing character.

        Args:
            profile_id: ID of the character to generate a backstory for.

        Returns:
            The generated backstory string, or empty string if not found.
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return ""

            backstory = self._compose_backstory(
                profile.role, profile.race, profile.char_class
            )
            profile.backstory = backstory
            self._recent_actions.append({
                "action": "generate_backstory",
                "profile_id": profile_id,
                "timestamp": _time_module.time(),
            })
            return backstory

    # ------------------------------------------------------------------
    # Retrieval and Listing
    # ------------------------------------------------------------------

    def get_character(self, profile_id: str) -> Optional[CharacterProfile]:
        """Retrieve a character by profile ID.

        Args:
            profile_id: The unique identifier of the character.

        Returns:
            The CharacterProfile if found, None otherwise.
        """
        with self._lock:
            return self._profiles.get(profile_id)

    def list_characters(
        self,
        role: Optional[CharacterRole] = None,
        char_class: Optional[CharacterClass] = None,
        race: Optional[CharacterRace] = None,
    ) -> List[CharacterProfile]:
        """List characters filtered by optional criteria.

        Args:
            role: Filter by narrative role.
            char_class: Filter by combat class.
            race: Filter by species.

        Returns:
            List of matching CharacterProfile instances.
        """
        with self._lock:
            results: List[CharacterProfile] = []
            for profile in self._profiles.values():
                if role is not None and profile.role != role:
                    continue
                if char_class is not None and profile.char_class != char_class:
                    continue
                if race is not None and profile.race != race:
                    continue
                results.append(profile)
            return results

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about all characters managed by this engine.

        Returns:
            Dictionary with creation counts, role distribution, class distribution,
            race distribution, and recent actions.
        """
        with self._lock:
            role_counts: Dict[str, int] = {}
            class_counts: Dict[str, int] = {}
            race_counts: Dict[str, int] = {}
            total_power = 0

            for profile in self._profiles.values():
                role_counts[profile.role.value] = (
                    role_counts.get(profile.role.value, 0) + 1
                )
                class_counts[profile.char_class.value] = (
                    class_counts.get(profile.char_class.value, 0) + 1
                )
                race_counts[profile.race.value] = (
                    race_counts.get(profile.race.value, 0) + 1
                )
                total_power += self.calculate_power_level(profile.profile_id)

            return {
                "total_characters_created": self._total_created,
                "active_profiles": len(self._profiles),
                "total_abilities_added": self._total_abilities_added,
                "characters_by_role": role_counts,
                "characters_by_class": class_counts,
                "characters_by_race": race_counts,
                "average_power_level": (
                    int(total_power / len(self._profiles))
                    if self._profiles
                    else 0
                ),
                "recent_actions": list(self._recent_actions),
            }

    # ------------------------------------------------------------------
    # Internal Generation Helpers
    # ------------------------------------------------------------------

    def _generate_attributes(
        self,
        char_class: CharacterClass,
        race: CharacterRace,
        level: int,
    ) -> List[CharacterAttribute]:
        """Generate attribute list with class-weighted and race-bonused values.

        Args:
            char_class: Combat archetype for weight multipliers.
            race: Species for additive bonuses.
            level: Character level for scaling.

        Returns:
            List of CharacterAttribute instances with computed values.
        """
        weights = _CLASS_ATTRIBUTE_WEIGHTS.get(char_class, {})
        bonuses = _RACE_ATTRIBUTE_BONUSES.get(race, {})
        base_value = 5.0 + (level * 1.5)
        attributes: List[CharacterAttribute] = []

        for attr_name in _BASE_ATTRIBUTE_NAMES:
            weight = weights.get(attr_name, 1.0)
            bonus = bonuses.get(attr_name, 0.0)
            raw_value = (base_value * weight) + bonus + random.uniform(-2.0, 2.0)
            value = max(1.0, min(100.0, raw_value))
            attr = CharacterAttribute(
                attr_id=str(uuid.uuid4()),
                name=attr_name,
                value=round(value, 1),
                min_value=1.0,
                max_value=100.0,
                description=_BASE_ATTRIBUTE_DESCRIPTIONS.get(attr_name, ""),
            )
            attributes.append(attr)

        return attributes

    def _generate_class_abilities(
        self,
        char_class: CharacterClass,
        level: int,
    ) -> List[CharacterAbility]:
        """Generate class-appropriate abilities based on character level.

        Args:
            char_class: Combat archetype for ability pool selection.
            level: Character level determining which abilities are unlocked.

        Returns:
            List of unlocked CharacterAbility instances.
        """
        templates = _ABILITY_TEMPLATES.get(char_class, [])
        abilities: List[CharacterAbility] = []

        for tmpl in templates:
            if level >= tmpl.get("level_required", 1):
                damage = round(tmpl.get("damage_factor", 1.0) * level * 3.5, 1)
                ability = CharacterAbility(
                    ability_id=str(uuid.uuid4()),
                    name=tmpl["name"],
                    description=tmpl.get("desc", ""),
                    damage=damage,
                    cooldown=tmpl.get("cooldown", 6.0),
                    mana_cost=tmpl.get("mana_cost", 20.0),
                    level_required=tmpl.get("level_required", 1),
                    effects=list(tmpl.get("effects", [])),
                )
                abilities.append(ability)

        return abilities

    def _generate_boss_special_abilities(
        self, theme: str, level: int
    ) -> List[CharacterAbility]:
        """Generate boss-specific thematic abilities.

        Args:
            theme: Boss theme descriptor.
            level: Boss level for scaling.

        Returns:
            List of boss-only CharacterAbility instances.
        """
        theme_abilities: Dict[str, List[Dict[str, Any]]] = {
            "dark": [
                {"name": "Shadow Nova", "desc": "Releases a burst of pure darkness, damaging all nearby enemies.", "damage_factor": 2.5, "cooldown": 18.0, "mana_cost": 60.0, "effects": ["aoe", "dark", "blind"]},
                {"name": "Void Grasp", "desc": "Tentacles of shadow pull a target closer and deal continuous damage.", "damage_factor": 1.5, "cooldown": 12.0, "mana_cost": 40.0, "effects": ["pull", "dot"]},
            ],
            "elemental": [
                {"name": "Elemental Fury", "desc": "Unleashes a storm of all four elements simultaneously.", "damage_factor": 3.0, "cooldown": 25.0, "mana_cost": 80.0, "effects": ["aoe", "burn", "freeze", "shock"]},
                {"name": "Prismatic Barrier", "desc": "Surrounds self with rotating elemental shields.", "damage_factor": 0.0, "cooldown": 20.0, "mana_cost": 50.0, "effects": ["shield", "reflect"]},
            ],
            "ancient": [
                {"name": "Timeless Curse", "desc": "Afflicts enemies with accelerated decay, reducing all stats.", "damage_factor": 0.8, "cooldown": 22.0, "mana_cost": 55.0, "effects": ["curse", "stat_debuff"]},
                {"name": "Echo of Ages", "desc": "Summons spectral echoes of ancient warriors.", "damage_factor": 1.3, "cooldown": 18.0, "mana_cost": 65.0, "effects": ["summon", "aoe"]},
            ],
            "cursed": [
                {"name": "Agony Field", "desc": "Creates an area where all enemies suffer continuous torment.", "damage_factor": 1.0, "cooldown": 16.0, "mana_cost": 55.0, "effects": ["zone", "dot", "slow"]},
                {"name": "Soul Rend", "desc": "Tears at the target's soul, dealing massive damage and stealing life.", "damage_factor": 3.0, "cooldown": 20.0, "mana_cost": 70.0, "effects": ["lifesteal", "fear"]},
            ],
            "corrupted": [
                {"name": "Corruption Wave", "desc": "A wave of corruption spreads outward, twisting the very ground.", "damage_factor": 2.0, "cooldown": 18.0, "mana_cost": 60.0, "effects": ["aoe", "zone"]},
                {"name": "Maddening Whispers", "desc": "Psychic assault that confuses and damages enemies.", "damage_factor": 1.2, "cooldown": 14.0, "mana_cost": 45.0, "effects": ["confuse", "fear"]},
            ],
            "mechanical": [
                {"name": "Missile Salvo", "desc": "Launches a barrage of homing missiles.", "damage_factor": 1.8, "cooldown": 14.0, "mana_cost": 50.0, "effects": ["aoe", "homing"]},
                {"name": "Overdrive", "desc": "Temporarily supercharges all systems for massively increased output.", "damage_factor": 0.0, "cooldown": 30.0, "mana_cost": 40.0, "effects": ["self_buff", "damage_boost", "speed_boost"]},
            ],
            "draconic": [
                {"name": "Dragon Breath", "desc": "Exhales a cone of elemental devastation.", "damage_factor": 2.8, "cooldown": 16.0, "mana_cost": 70.0, "effects": ["aoe", "burn"]},
                {"name": "Tail Sweep", "desc": "A massive tail swipe that knocks back all nearby enemies.", "damage_factor": 1.5, "cooldown": 10.0, "mana_cost": 30.0, "effects": ["aoe", "knockback"]},
            ],
            "void": [
                {"name": "Gravity Well", "desc": "Creates a singularity that pulls in and crushes enemies.", "damage_factor": 2.2, "cooldown": 20.0, "mana_cost": 65.0, "effects": ["pull", "aoe", "slow"]},
                {"name": "Null Field", "desc": "Creates a zone of nothingness that nullifies all magic.", "damage_factor": 0.0, "cooldown": 25.0, "mana_cost": 75.0, "effects": ["silence", "zone"]},
            ],
            "nature": [
                {"name": "Verdant Wrath", "desc": "Summons a forest of thorned vines that ensnare and lacerate.", "damage_factor": 1.7, "cooldown": 18.0, "mana_cost": 55.0, "effects": ["root", "dot", "aoe"]},
                {"name": "Natural Rebirth", "desc": "Fully regenerates health and clears all debuffs.", "damage_factor": 0.0, "cooldown": 60.0, "mana_cost": 100.0, "effects": ["full_heal", "cleanse"]},
            ],
            "undead": [
                {"name": "Necrotic Plague", "desc": "Spreads a rotting disease that jumps between enemies.", "damage_factor": 0.9, "cooldown": 15.0, "mana_cost": 50.0, "effects": ["spread", "dot", "debuff"]},
                {"name": "Bone Storm", "desc": "Creates a whirlwind of razor-sharp bone shards.", "damage_factor": 2.0, "cooldown": 18.0, "mana_cost": 60.0, "effects": ["aoe", "bleed"]},
            ],
        }

        pool = theme_abilities.get(theme, theme_abilities["dark"])
        abilities: List[CharacterAbility] = []
        for tmpl in pool:
            damage = round(tmpl.get("damage_factor", 1.0) * level * 4.0, 1)
            ability = CharacterAbility(
                ability_id=str(uuid.uuid4()),
                name=tmpl["name"],
                description=tmpl.get("desc", ""),
                damage=damage,
                cooldown=tmpl.get("cooldown", 18.0),
                mana_cost=tmpl.get("mana_cost", 60.0),
                level_required=max(1, level - 3),
                effects=list(tmpl.get("effects", [])),
            )
            abilities.append(ability)

        return abilities

    def _compose_backstory(
        self,
        role: CharacterRole,
        race: CharacterRace,
        char_class: CharacterClass,
    ) -> str:
        """Compose a narrative backstory using role-based templates.

        Args:
            role: Narrative role.
            race: Species.
            char_class: Combat class.

        Returns:
            Formatted backstory string.
        """
        location = random.choice(_LOCATIONS)
        templates = _BACKSTORY_TEMPLATES.get(role, [])
        if not templates:
            template = str(_DEFAULT_BACKSTORY)
        else:
            template = random.choice(templates)

        return template.format(
            race=race.value,
            char_class=char_class.value,
            location=location,
        )

    def _generate_appearance(
        self,
        race: CharacterRace,
        char_class: CharacterClass,
    ) -> str:
        """Generate a visual appearance description based on race and class.

        Args:
            race: Species determining physical traits.
            char_class: Combat class influencing attire.

        Returns:
            Formatted appearance description.
        """
        templates = _APPEARANCE_TEMPLATES.get(race, [str(_DEFAULT_APPEARANCE)])
        if not templates:
            appearance = str(_DEFAULT_APPEARANCE)
        else:
            appearance = random.choice(templates)

        return appearance.format(
            race=race.value,
            char_class=char_class.value,
        )

    def _select_personality(self, role: CharacterRole) -> List[str]:
        """Select between 3 and 5 personality traits appropriate for the role.

        Args:
            role: Narrative role.

        Returns:
            List of personality trait strings.
        """
        count = random.randint(3, 5)
        # Build role-biased trait pools for more thematically consistent personalities
        role_biased_traits: Dict[CharacterRole, List[str]] = {
            CharacterRole.PLAYER: ["Brave", "Determined", "Curious", "Loyal", "Impulsive"],
            CharacterRole.ENEMY: ["Fierce", "Reckless", "Suspicious", "Cunning", "Zealous"],
            CharacterRole.BOSS: ["Fierce", "Determined", "Cunning", "Stoic", "Zealous"],
            CharacterRole.MERCHANT: ["Charismatic", "Cautious", "Pragmatic", "Witty", "Sarcastic"],
            CharacterRole.QUEST_GIVER: ["Wise", "Diplomatic", "Optimistic", "Pragmatic", "Stoic"],
            CharacterRole.TRAINER: ["Stoic", "Wise", "Honorable", "Pragmatic", "Gruff"],
            CharacterRole.GUARDIAN: ["Honorable", "Loyal", "Stoic", "Brave", "Determined"],
            CharacterRole.VILLAIN: ["Cunning", "Mysterious", "Charismatic", "Fierce", "Pragmatic"],
            CharacterRole.COMPANION: ["Loyal", "Warm", "Optimistic", "Witty", "Brave"],
        }

        biased = role_biased_traits.get(role, _PERSONALITY_TRAITS)
        general = [t for t in _PERSONALITY_TRAITS if t not in biased]

        # Weight toward role-appropriate traits: 60% biased, 40% general
        selected: List[str] = []
        biased_count = min(count, len(biased))
        selected.extend(random.sample(biased, biased_count))
        remaining = count - biased_count
        if remaining > 0 and general:
            selected.extend(random.sample(general, min(remaining, len(general))))

        return selected[:count]

    def _select_equipment(
        self,
        role: CharacterRole,
        char_class: CharacterClass,
    ) -> List[str]:
        """Select role and class appropriate equipment.

        Args:
            role: Narrative role.
            char_class: Combat class.

        Returns:
            List of equipment item strings.
        """
        if role in _ROLE_EQUIPMENT:
            return list(_ROLE_EQUIPMENT[role])

        class_gear = _EQUIPMENT_BY_CLASS.get(char_class, [])
        if not class_gear:
            return ["Traveling Clothes", "Walking Stick"]

        return list(class_gear)

    def _generate_random_name(self, race: CharacterRace) -> str:
        """Generate a random name appropriate for the given race.

        Args:
            race: Character species.

        Returns:
            A full name string (first + surname).
        """
        if race == CharacterRace.HUMAN:
            first = random.choice(_FIRST_NAMES_HUMAN)
        elif race == CharacterRace.ELF:
            first = random.choice(_FIRST_NAMES_ELF)
        elif race == CharacterRace.DWARF:
            first = random.choice(_FIRST_NAMES_DWARF)
        elif race == CharacterRace.ORC:
            first = random.choice(_FIRST_NAMES_ORC)
        else:
            first = random.choice(_FIRST_NAMES_OTHER)

        surname = random.choice(_SURNAMES)
        return f"{first} {surname}"

    def _generate_boss_equipment(
        self, theme: str, char_class: CharacterClass
    ) -> List[str]:
        """Generate thematically appropriate boss equipment.

        Args:
            theme: Boss theme descriptor.
            char_class: Boss combat class.

        Returns:
            List of equipment item strings with thematic prefixes.
        """
        base_gear = _EQUIPMENT_BY_CLASS.get(char_class, ["Dark Blade", "Shadow Armor"])
        theme_prefixes: Dict[str, str] = {
            "dark": "Shadowforged",
            "elemental": "Elementium",
            "ancient": "Primordial",
            "cursed": "Cursed",
            "corrupted": "Corrupted",
            "mechanical": "Clockwork",
            "draconic": "Dragonscale",
            "void": "Void-Touched",
            "nature": "Thornwoven",
            "undead": "Bonecraft",
        }
        prefix = theme_prefixes.get(theme, "Dark")
        return [f"{prefix} {item}" for item in base_gear]


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_character_creator() -> CharacterCreatorEngine:
    """Return the singleton CharacterCreatorEngine instance."""
    return CharacterCreatorEngine.get_instance()