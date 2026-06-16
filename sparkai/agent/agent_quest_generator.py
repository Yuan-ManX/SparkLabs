"""
SparkLabs Agent - Quest Generator

AI-driven quest generation system for the SparkLabs AI-native game engine.
Generates quests with objectives, branching paths, rewards, story arcs,
and narrative coherence. Supports single quest creation, random quest
generation, quest chain composition, and quest validation.

Architecture:
  QuestGeneratorEngine (Singleton)
    |-- QuestType (categorization of quest archetypes)
    |-- QuestDifficulty (scaling tier for rewards and objectives)
    |-- QuestStatus (lifecycle state machine)
    |-- ObjectiveType (concrete task types within a quest)
    |-- QuestObjective (individual task with progress tracking)
    |-- QuestReward (structured reward package)
    |-- QuestDefinition (complete quest data model)
    |-- QuestChain (ordered sequence of interconnected quests)
"""

from __future__ import annotations

import json
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------


class QuestType(Enum):
    """Categorization of quest archetypes and gameplay patterns."""

    MAIN_STORY = "main_story"
    SIDE_QUEST = "side_quest"
    FETCH = "fetch"
    KILL = "kill"
    ESCORT = "escort"
    EXPLORATION = "exploration"
    PUZZLE = "puzzle"
    DELIVERY = "delivery"
    DEFENSE = "defense"
    TIMED = "timed"
    COLLECTION = "collection"
    CRAFTING = "crafting"
    BOSS_FIGHT = "boss_fight"
    STEALTH = "stealth"
    DIALOGUE = "dialogue"


class QuestDifficulty(Enum):
    """Scaling tier that controls reward magnitude and objective complexity."""

    TRIVIAL = "trivial"
    EASY = "easy"
    MODERATE = "moderate"
    CHALLENGING = "challenging"
    HARD = "hard"
    EXTREME = "extreme"
    LEGENDARY = "legendary"


class QuestStatus(Enum):
    """Lifecycle states for quest progression tracking."""

    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    LOCKED = "locked"


class ObjectiveType(Enum):
    """Concrete task types that compose a quest's objectives."""

    COLLECT_ITEM = "collect_item"
    KILL_ENEMY = "kill_enemy"
    REACH_LOCATION = "reach_location"
    TALK_TO_NPC = "talk_to_npc"
    SOLVE_PUZZLE = "solve_puzzle"
    ESCORT_NPC = "escort_npc"
    DEFEND_POINT = "defend_point"
    DELIVER_ITEM = "deliver_item"
    CRAFT_ITEM = "craft_item"
    SURVIVE_TIME = "survive_time"
    ACTIVATE_OBJECT = "activate_object"
    STEALTH_PASS = "stealth_pass"


# ------------------------------------------------------------------
# Difficulty scaling tables
# ------------------------------------------------------------------

DIFFICULTY_MULTIPLIERS: Dict[QuestDifficulty, float] = {
    QuestDifficulty.TRIVIAL: 0.3,
    QuestDifficulty.EASY: 0.6,
    QuestDifficulty.MODERATE: 1.0,
    QuestDifficulty.CHALLENGING: 1.5,
    QuestDifficulty.HARD: 2.2,
    QuestDifficulty.EXTREME: 3.5,
    QuestDifficulty.LEGENDARY: 5.0,
}

DIFFICULTY_OBJECTIVE_COUNTS: Dict[QuestDifficulty, Tuple[int, int]] = {
    QuestDifficulty.TRIVIAL: (1, 1),
    QuestDifficulty.EASY: (1, 2),
    QuestDifficulty.MODERATE: (2, 3),
    QuestDifficulty.CHALLENGING: (3, 4),
    QuestDifficulty.HARD: (3, 5),
    QuestDifficulty.EXTREME: (4, 6),
    QuestDifficulty.LEGENDARY: (5, 8),
}

DIFFICULTY_TIME_ESTIMATES: Dict[QuestDifficulty, Tuple[float, float]] = {
    QuestDifficulty.TRIVIAL: (2.0, 5.0),
    QuestDifficulty.EASY: (5.0, 12.0),
    QuestDifficulty.MODERATE: (10.0, 25.0),
    QuestDifficulty.CHALLENGING: (20.0, 45.0),
    QuestDifficulty.HARD: (35.0, 70.0),
    QuestDifficulty.EXTREME: (60.0, 120.0),
    QuestDifficulty.LEGENDARY: (90.0, 240.0),
}

# ------------------------------------------------------------------
# Quest-type-to-objective mapping
# ------------------------------------------------------------------

QUEST_OBJECTIVE_PATTERNS: Dict[QuestType, List[Tuple[ObjectiveType, int, str]]] = {
    QuestType.FETCH: [
        (ObjectiveType.COLLECT_ITEM, 3, "Gather {target} from {location}"),
        (ObjectiveType.DELIVER_ITEM, 1, "Return {target} to {giver_npc}"),
    ],
    QuestType.KILL: [
        (ObjectiveType.KILL_ENEMY, 5, "Eliminate {count} {target}"),
        (ObjectiveType.REACH_LOCATION, 1, "Report to {giver_npc}"),
    ],
    QuestType.ESCORT: [
        (ObjectiveType.ESCORT_NPC, 1, "Escort {target} safely to {location}"),
        (ObjectiveType.DEFEND_POINT, 1, "Protect {target} from hostiles"),
    ],
    QuestType.EXPLORATION: [
        (ObjectiveType.REACH_LOCATION, 3, "Discover {location}"),
        (ObjectiveType.ACTIVATE_OBJECT, 1, "Activate the ancient mechanism"),
    ],
    QuestType.PUZZLE: [
        (ObjectiveType.SOLVE_PUZZLE, 1, "Solve the {location} puzzle"),
        (ObjectiveType.ACTIVATE_OBJECT, 1, "Activate the unlocked chamber"),
    ],
    QuestType.DELIVERY: [
        (ObjectiveType.COLLECT_ITEM, 1, "Pick up {target} from {giver_npc}"),
        (ObjectiveType.DELIVER_ITEM, 1, "Deliver {target} to {location}"),
    ],
    QuestType.DEFENSE: [
        (ObjectiveType.DEFEND_POINT, 1, "Defend {location} from waves of enemies"),
        (ObjectiveType.KILL_ENEMY, 10, "Repel all invading forces"),
    ],
    QuestType.TIMED: [
        (ObjectiveType.REACH_LOCATION, 2, "Race to {location} before time expires"),
        (ObjectiveType.SURVIVE_TIME, 1, "Survive for {count} seconds"),
    ],
    QuestType.COLLECTION: [
        (ObjectiveType.COLLECT_ITEM, 5, "Collect {count} {target} from {location}"),
        (ObjectiveType.DELIVER_ITEM, 1, "Bring the collection to {giver_npc}"),
    ],
    QuestType.CRAFTING: [
        (ObjectiveType.COLLECT_ITEM, 3, "Gather materials for crafting"),
        (ObjectiveType.CRAFT_ITEM, 1, "Craft {target} at the workbench"),
    ],
    QuestType.BOSS_FIGHT: [
        (ObjectiveType.KILL_ENEMY, 1, "Defeat {target}"),
        (ObjectiveType.COLLECT_ITEM, 1, "Claim the trophy from {target}"),
    ],
    QuestType.STEALTH: [
        (ObjectiveType.STEALTH_PASS, 1, "Infiltrate {location} without detection"),
        (ObjectiveType.COLLECT_ITEM, 1, "Retrieve {target} from the guarded vault"),
    ],
    QuestType.DIALOGUE: [
        (ObjectiveType.TALK_TO_NPC, 3, "Speak with {target}"),
        (ObjectiveType.TALK_TO_NPC, 1, "Report findings to {giver_npc}"),
    ],
    QuestType.MAIN_STORY: [
        (ObjectiveType.REACH_LOCATION, 1, "Travel to {location}"),
        (ObjectiveType.KILL_ENEMY, 3, "Clear the path of hostiles"),
        (ObjectiveType.TALK_TO_NPC, 1, "Confer with {target}"),
        (ObjectiveType.ACTIVATE_OBJECT, 1, "Trigger the story event"),
    ],
    QuestType.SIDE_QUEST: [
        (ObjectiveType.COLLECT_ITEM, 2, "Retrieve {target} from {location}"),
        (ObjectiveType.TALK_TO_NPC, 1, "Return to {giver_npc}"),
    ],
}

# ------------------------------------------------------------------
# Thematic descriptions per quest type
# ------------------------------------------------------------------

QUEST_THEMES: Dict[QuestType, List[str]] = {
    QuestType.FETCH: [
        "A traveler lost their heirloom and needs it recovered.",
        "The local merchant requires rare herbs for a potion.",
        "Someone dropped a valuable item in a dangerous area.",
    ],
    QuestType.KILL: [
        "A pack of beasts has been terrorizing the outskirts.",
        "Bandits have set up camp near the trade route.",
        "A rogue creature threatens the village's safety.",
    ],
    QuestType.ESCORT: [
        "A merchant caravan needs protection through hostile territory.",
        "An important diplomat must reach the summit safely.",
        "Refugees require an escort to the neighboring settlement.",
    ],
    QuestType.EXPLORATION: [
        "Ancient ruins have been spotted beyond the mountains.",
        "Rumors speak of a hidden cave filled with forgotten treasures.",
        "An uncharted island has appeared on the horizon.",
    ],
    QuestType.PUZZLE: [
        "A sealed door blocks passage to the inner sanctum.",
        "Strange runes light up when approached — they must be decoded.",
        "The temple's mechanism requires three keys to unlock.",
    ],
    QuestType.DELIVERY: [
        "An urgent package must reach the outpost by nightfall.",
        "Medicine needs to be delivered to the quarantine zone.",
        "A sealed letter must be handed to the captain personally.",
    ],
    QuestType.DEFENSE: [
        "The settlement walls are under siege by raiders.",
        "A strategic outpost must be held at all costs.",
        "The ritual circle must be protected while the mages finish.",
    ],
    QuestType.TIMED: [
        "A bomb has been planted and the fuse is burning.",
        "The antidote must be administered before the poison spreads.",
        "A distress beacon will only transmit for a limited window.",
    ],
    QuestType.COLLECTION: [
        "A scholar seeks rare botanical specimens for research.",
        "The guild needs proof of extermination — collect the trophies.",
        "A collector is paying handsomely for ancient artifacts.",
    ],
    QuestType.CRAFTING: [
        "The blacksmith needs rare ore to forge a masterwork blade.",
        "A tailored garment requires exotic materials to complete.",
        "The alchemist has the formula but lacks the ingredients.",
    ],
    QuestType.BOSS_FIGHT: [
        "A towering beast has emerged from the depths.",
        "The warlord challenges any who dare to face them.",
        "An ancient guardian awakens to test the worthy.",
    ],
    QuestType.STEALTH: [
        "Infiltrate the fortress and steal the battle plans.",
        "Slip past the guards and retrieve the evidence unnoticed.",
        "A silent approach is the only way past the sentries.",
    ],
    QuestType.DIALOGUE: [
        "A series of interrogations will uncover the conspiracy.",
        "Diplomatic negotiations must prevent an all-out war.",
        "Information must be gathered from rival informants.",
    ],
    QuestType.MAIN_STORY: [
        "The fate of the realm hinges on this critical mission.",
        "A prophecy foretells this moment — the path is now clear.",
        "Dark forces gather, and only decisive action can stop them.",
    ],
    QuestType.SIDE_QUEST: [
        "A villager has a personal request for a passing adventurer.",
        "A small errand that could make a big difference.",
        "A local problem that needs a helping hand.",
    ],
}

# ------------------------------------------------------------------
# Location and NPC name pools for random generation
# ------------------------------------------------------------------

LOCATION_POOL: List[str] = [
    "Whispering Woods",
    "Crimson Canyon",
    "Frostpeak Summit",
    "Sunken Catacombs",
    "Emberfall Village",
    "Ironhold Keep",
    "Shadowfen Marsh",
    "Thunder Ridge",
    "Silent Monastery",
    "The Drowned Harbor",
    "Obsidian Depths",
    "Verdant Hollow",
    "Ashwind Plateau",
    "Stormbreak Tower",
    "Goldenfields",
    "The Shattered Spire",
    "Mistveil Basin",
    "Cinderforge Mines",
    "Bleakshore Coast",
    "Starfall Observatory",
]

NPC_NAME_POOL: List[str] = [
    "Captain Aldric",
    "Elder Marwen",
    "Scholar Thera",
    "Blacksmith Orin",
    "Ranger Kael",
    "Merchant Lira",
    "Priestess Veyna",
    "Warden Doran",
    "Alchemist Sybil",
    "Scout Fenris",
    "Baroness Isolde",
    "Huntsman Garrick",
    "Sage Elowen",
    "Guard Commander Thorne",
    "Innkeeper Mera",
    "Cartographer Bram",
    "Apothecary Nevin",
    "Dockmaster Soren",
    "Chronicler Petra",
    "Envoy Riven",
]

ENEMY_NAME_POOL: List[str] = [
    "Shadow Stalker",
    "Crimson Reaver",
    "Frost Wyrm",
    "Iron Golem",
    "Blight Hound",
    "Storm Elemental",
    "Bone Revenant",
    "Venomfang Drake",
    "Crystal Spider",
    "Magma Brute",
    "Wraith Captain",
    "Thorn Beast",
    "Clockwork Sentinel",
    "Abyssal Horror",
    "Thunder Roc",
]

ITEM_NAME_POOL: List[str] = [
    "Moonstone Shard",
    "Ancient Tome",
    "Enchanted Blade",
    "Phoenix Feather",
    "Dragon Scale",
    "Vial of Echoes",
    "Runed Amulet",
    "Shadow Essence",
    "Celestial Key",
    "Ironwood Plank",
    "Crystal Lens",
    "Serpent Venom",
    "Star Chart",
    "Obsidian Core",
    "Potion of Vigor",
]

STORY_THEMES: List[str] = [
    "redemption",
    "vengeance",
    "discovery",
    "survival",
    "conquest",
    "betrayal",
    "sacrifice",
    "rebirth",
    "corruption",
    "unity",
    "exile",
    "prophecy",
    "revolution",
    "guardianship",
    "ascension",
]

STORY_BEATS: List[str] = [
    "call_to_action",
    "first_trial",
    "gathering_allies",
    "deepening_conflict",
    "crisis_point",
    "race_against_time",
    "revelation",
    "the_showdown",
    "climactic_resolution",
    "aftermath",
]


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class QuestObjective:
    """A single objective within a quest with progress tracking."""

    objective_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    type: ObjectiveType = ObjectiveType.COLLECT_ITEM
    description: str = ""
    target_count: int = 1
    current_count: int = 0
    target_id: str = ""
    location: str = ""
    is_optional: bool = False
    order: int = 0

    def progress(self) -> float:
        if self.target_count <= 0:
            return 1.0
        return min(1.0, self.current_count / self.target_count)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "type": self.type.value,
            "description": self.description,
            "target_count": self.target_count,
            "current_count": self.current_count,
            "target_id": self.target_id,
            "location": self.location,
            "is_optional": self.is_optional,
            "order": self.order,
            "progress": round(self.progress(), 2),
        }


@dataclass
class QuestReward:
    """Structured reward package for quest completion."""

    reward_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    experience: int = 0
    currency: int = 0
    items: List[str] = field(default_factory=list)
    reputation: Dict[str, int] = field(default_factory=dict)
    unlocks: List[str] = field(default_factory=list)
    special_rewards: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reward_id": self.reward_id,
            "experience": self.experience,
            "currency": self.currency,
            "items": self.items,
            "reputation": self.reputation,
            "unlocks": self.unlocks,
            "special_rewards": self.special_rewards,
        }


@dataclass
class QuestDefinition:
    """Complete quest definition with objectives, rewards, and narrative data."""

    quest_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    description: str = ""
    quest_type: QuestType = QuestType.SIDE_QUEST
    difficulty: QuestDifficulty = QuestDifficulty.MODERATE
    objectives: List[QuestObjective] = field(default_factory=list)
    rewards: QuestReward = field(default_factory=QuestReward)
    prerequisites: List[str] = field(default_factory=list)
    next_quests: List[str] = field(default_factory=list)
    giver_npc_id: str = ""
    target_npc_id: str = ""
    location: str = ""
    story_arc: str = ""
    is_repeatable: bool = False
    time_limit: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quest_id": self.quest_id,
            "title": self.title,
            "description": self.description,
            "quest_type": self.quest_type.value,
            "difficulty": self.difficulty.value,
            "objectives": [o.to_dict() for o in self.objectives],
            "rewards": self.rewards.to_dict(),
            "prerequisites": self.prerequisites,
            "next_quests": self.next_quests,
            "giver_npc_id": self.giver_npc_id,
            "target_npc_id": self.target_npc_id,
            "location": self.location,
            "story_arc": self.story_arc,
            "is_repeatable": self.is_repeatable,
            "time_limit": self.time_limit,
            "created_at": self.created_at,
        }


@dataclass
class QuestChain:
    """Ordered sequence of interconnected quests forming a story arc."""

    chain_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    quests: List[QuestDefinition] = field(default_factory=list)
    story_summary: str = ""
    is_sequential: bool = True
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "quests": [q.to_dict() for q in self.quests],
            "story_summary": self.story_summary,
            "is_sequential": self.is_sequential,
            "created_at": self.created_at,
        }


# ------------------------------------------------------------------
# Quest Generator Engine (Singleton)
# ------------------------------------------------------------------


class QuestGeneratorEngine:
    """AI-driven quest generation system for the SparkLabs game engine.

    Generates quests with objectives, branching paths, rewards, story arcs,
    and narrative coherence. Supports single quest creation, random quest
    generation, quest chain composition, and quest validation.

    Usage:
        engine = QuestGeneratorEngine.get_instance()
        quest = engine.create_quest("The Lost Relic", QuestType.FETCH, ...)
        chain = engine.generate_quest_chain("The Dark Prophecy", QuestType.MAIN_STORY, 5)
    """

    _instance: Optional["QuestGeneratorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "QuestGeneratorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "QuestGeneratorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._quests: Dict[str, QuestDefinition] = {}
        self._chains: Dict[str, QuestChain] = {}
        self._total_generated: int = 0

    # ------------------------------------------------------------------
    # Core Quest Creation
    # ------------------------------------------------------------------

    def create_quest(
        self,
        title: str,
        quest_type: QuestType = QuestType.SIDE_QUEST,
        difficulty: QuestDifficulty = QuestDifficulty.MODERATE,
        giver_npc_id: str = "",
        description: str = "",
        location: str = "",
    ) -> QuestDefinition:
        """Create a new quest definition with the given parameters.

        Args:
            title: Display name of the quest.
            quest_type: Category of quest archetype.
            difficulty: Scaling tier for rewards and objectives.
            giver_npc_id: ID of the NPC who gives the quest.
            description: Narrative description of the quest.
            location: Primary location where the quest takes place.

        Returns:
            A fully initialized QuestDefinition instance.
        """
        with self._lock:
            if not description:
                description = self._generate_description(quest_type, location)

            quest = QuestDefinition(
                title=title,
                description=description,
                quest_type=quest_type,
                difficulty=difficulty,
                giver_npc_id=giver_npc_id,
                location=location,
            )
            self._quests[quest.quest_id] = quest
            self._total_generated += 1
            return quest

    def _generate_description(
        self, quest_type: QuestType, location: str
    ) -> str:
        """Generate a default narrative description for a quest type."""
        descriptions: Dict[QuestType, str] = {
            QuestType.FETCH: f"A request to retrieve a valuable item from {location or 'a distant area'}.",
            QuestType.KILL: f"Hostile forces in {location or 'the region'} must be eliminated.",
            QuestType.ESCORT: f"An important figure needs safe passage through {location or 'dangerous territory'}.",
            QuestType.EXPLORATION: f"Uncharted areas of {location or 'the world'} await discovery.",
            QuestType.PUZZLE: f"An ancient puzzle in {location or 'a forgotten place'} must be solved.",
            QuestType.DELIVERY: f"A critical package must be delivered to {location or 'its destination'}.",
            QuestType.DEFENSE: f"{location or 'A strategic position'} must be defended at all costs.",
            QuestType.TIMED: f"Time is running out — {location or 'the target'} must be reached quickly.",
            QuestType.COLLECTION: f"Rare items scattered across {location or 'the land'} need to be gathered.",
            QuestType.CRAFTING: f"Materials must be gathered and crafted at {location or 'the workshop'}.",
            QuestType.BOSS_FIGHT: f"A formidable foe awaits at {location or 'the battle arena'}.",
            QuestType.STEALTH: f"A silent infiltration of {location or 'the guarded compound'} is required.",
            QuestType.DIALOGUE: f"Important conversations must take place in {location or 'the meeting hall'}.",
            QuestType.MAIN_STORY: f"The story unfolds at {location or 'a pivotal location'}.",
            QuestType.SIDE_QUEST: f"A local task in {location or 'the area'} needs attention.",
        }
        return descriptions.get(quest_type, descriptions[QuestType.SIDE_QUEST])

    def add_objective(
        self,
        quest_id: str,
        objective_type: ObjectiveType = ObjectiveType.COLLECT_ITEM,
        description: str = "",
        target_count: int = 1,
        target_id: str = "",
        location: str = "",
        is_optional: bool = False,
        order: int = 0,
    ) -> Optional[QuestObjective]:
        """Add an objective to an existing quest.

        Args:
            quest_id: ID of the quest to add the objective to.
            objective_type: Type of task for this objective.
            description: Human-readable description of the objective.
            target_count: Number of times the objective must be completed.
            target_id: ID of the target entity (item, NPC, enemy, etc.).
            location: Location where the objective takes place.
            is_optional: Whether this objective is required for quest completion.
            order: Display order of the objective within the quest.

        Returns:
            The created QuestObjective, or None if the quest is not found.
        """
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return None

            objective = QuestObjective(
                type=objective_type,
                description=description,
                target_count=target_count,
                target_id=target_id,
                location=location or quest.location,
                is_optional=is_optional,
                order=order if order > 0 else len(quest.objectives) + 1,
            )
            quest.objectives.append(objective)
            return objective

    def set_rewards(
        self,
        quest_id: str,
        experience: int = 0,
        currency: int = 0,
        items: Optional[List[str]] = None,
        reputation: Optional[Dict[str, int]] = None,
        unlocks: Optional[List[str]] = None,
    ) -> Optional[QuestReward]:
        """Set the reward package for an existing quest.

        Args:
            quest_id: ID of the quest to set rewards for.
            experience: Experience points awarded on completion.
            currency: Currency amount awarded on completion.
            items: List of item IDs awarded.
            reputation: Dict mapping faction IDs to reputation changes.
            unlocks: List of unlockable IDs granted.

        Returns:
            The updated QuestReward, or None if the quest is not found.
        """
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return None

            quest.rewards = QuestReward(
                experience=experience,
                currency=currency,
                items=items or [],
                reputation=reputation or {},
                unlocks=unlocks or [],
            )
            return quest.rewards

    # ------------------------------------------------------------------
    # Random Quest Generation
    # ------------------------------------------------------------------

    def generate_random_quest(
        self,
        difficulty: Optional[QuestDifficulty] = None,
        location: str = "",
    ) -> QuestDefinition:
        """Generate a fully randomized quest with appropriate objectives and rewards.

        Creates a quest with varied objective combinations based on the selected
        quest type, appropriate rewards scaled to difficulty, thematic descriptions
        matching the quest type, and logical prerequisites and follow-up quests.

        Args:
            difficulty: Optional override for difficulty. Randomly chosen if None.
            location: Optional location override. Randomly chosen if empty.

        Returns:
            A fully populated QuestDefinition with randomized content.
        """
        with self._lock:
            rng = random.Random()

            if difficulty is None:
                difficulty = rng.choice(list(QuestDifficulty))

            quest_type = rng.choice(list(QuestType))
            if not location:
                location = rng.choice(LOCATION_POOL)

            giver_npc = rng.choice(NPC_NAME_POOL)
            target_npc = rng.choice(NPC_NAME_POOL)

            themes = QUEST_THEMES.get(quest_type, QUEST_THEMES[QuestType.SIDE_QUEST])
            description = rng.choice(themes)

            quest = QuestDefinition(
                title=self._generate_quest_title(quest_type, location, rng),
                description=description,
                quest_type=quest_type,
                difficulty=difficulty,
                giver_npc_id=giver_npc,
                target_npc_id=target_npc if quest_type in (QuestType.DIALOGUE, QuestType.ESCORT) else "",
                location=location,
                time_limit=self._generate_time_limit(quest_type, difficulty, rng),
                story_arc=rng.choice(STORY_THEMES),
            )

            self._populate_objectives(quest, difficulty, rng)
            self._populate_rewards(quest, difficulty, rng)

            self._quests[quest.quest_id] = quest
            self._total_generated += 1
            return quest

    def _generate_quest_title(
        self, quest_type: QuestType, location: str, rng: random.Random
    ) -> str:
        """Generate a thematic title for a quest based on its type."""
        title_templates: Dict[QuestType, List[str]] = {
            QuestType.FETCH: [
                f"Lost and Found in {location}",
                f"The Missing Heirloom",
                f"Gathering at {location}",
            ],
            QuestType.KILL: [
                f"Clearing {location}",
                f"Bounty of {location}",
                f"Extermination Order",
            ],
            QuestType.ESCORT: [
                f"Safe Passage through {location}",
                f"Guardian of the Road",
                f"The Journey to {location}",
            ],
            QuestType.EXPLORATION: [
                f"Charting {location}",
                f"Into the Unknown",
                f"Secrets of {location}",
            ],
            QuestType.PUZZLE: [
                f"The Riddle of {location}",
                f"Unlocking {location}",
                f"Echoes of the Past",
            ],
            QuestType.DELIVERY: [
                f"Urgent Dispatch to {location}",
                f"Special Delivery",
                f"Courier to {location}",
            ],
            QuestType.DEFENSE: [
                f"Hold the Line at {location}",
                f"Fortifying {location}",
                f"Last Stand",
            ],
            QuestType.TIMED: [
                f"Race Against the Clock",
                f"Before It's Too Late",
                f"Countdown at {location}",
            ],
            QuestType.COLLECTION: [
                f"Rare Specimens of {location}",
                f"The Collector's Request",
                f"Trophy Hunt",
            ],
            QuestType.CRAFTING: [
                f"Masterwork of {location}",
                f"Forge and Flame",
                f"The Artisan's Challenge",
            ],
            QuestType.BOSS_FIGHT: [
                f"Confrontation at {location}",
                f"The Beast of {location}",
                f"Trial by Combat",
            ],
            QuestType.STEALTH: [
                f"Infiltrating {location}",
                f"Shadow Operation",
                f"Silent Approach",
            ],
            QuestType.DIALOGUE: [
                f"Words of Power",
                f"The Council at {location}",
                f"Diplomatic Channels",
            ],
            QuestType.MAIN_STORY: [
                f"The Turning Point",
                f"Destiny Calls",
                f"Fate of {location}",
            ],
            QuestType.SIDE_QUEST: [
                f"A Favor for a Friend",
                f"Trouble in {location}",
                f"Helping Hands",
            ],
        }
        templates = title_templates.get(quest_type, title_templates[QuestType.SIDE_QUEST])
        return rng.choice(templates)

    def _populate_objectives(
        self,
        quest: QuestDefinition,
        difficulty: QuestDifficulty,
        rng: random.Random,
    ) -> None:
        """Populate a quest with type-appropriate objectives scaled to difficulty."""
        patterns = QUEST_OBJECTIVE_PATTERNS.get(
            quest.quest_type,
            QUEST_OBJECTIVE_PATTERNS[QuestType.SIDE_QUEST],
        )

        min_count, max_count = DIFFICULTY_OBJECTIVE_COUNTS.get(
            difficulty, (2, 3)
        )
        target_objective_count = rng.randint(min_count, max_count)

        multiplier = DIFFICULTY_MULTIPLIERS.get(difficulty, 1.0)

        for i in range(target_objective_count):
            pattern_index = i % len(patterns)
            obj_type, base_count, desc_template = patterns[pattern_index]

            count = max(1, int(base_count * multiplier))

            target_id = ""
            if obj_type == ObjectiveType.KILL_ENEMY:
                target_id = rng.choice(ENEMY_NAME_POOL)
            elif obj_type in (ObjectiveType.COLLECT_ITEM, ObjectiveType.DELIVER_ITEM, ObjectiveType.CRAFT_ITEM):
                target_id = rng.choice(ITEM_NAME_POOL)
            elif obj_type in (ObjectiveType.TALK_TO_NPC, ObjectiveType.ESCORT_NPC):
                target_id = rng.choice(NPC_NAME_POOL)

            description = desc_template.format(
                target=target_id or "the objective",
                location=quest.location or "the area",
                count=count,
                giver_npc=quest.giver_npc_id or "the quest giver",
            )

            objective = QuestObjective(
                type=obj_type,
                description=description,
                target_count=count,
                target_id=target_id,
                location=quest.location,
                is_optional=(i > 0 and rng.random() < 0.2),
                order=i + 1,
            )
            quest.objectives.append(objective)

    def _populate_rewards(
        self,
        quest: QuestDefinition,
        difficulty: QuestDifficulty,
        rng: random.Random,
    ) -> None:
        """Populate a quest with rewards scaled to difficulty and objectives."""
        multiplier = DIFFICULTY_MULTIPLIERS.get(difficulty, 1.0)
        objective_count = len(quest.objectives)

        base_exp = 100 * objective_count
        base_currency = 50 * objective_count

        item_count = min(len(quest.objectives), 3)
        reward_items: List[str] = []
        for _ in range(max(0, int(item_count * multiplier * 0.6))):
            reward_items.append(rng.choice(ITEM_NAME_POOL))

        reputation: Dict[str, int] = {}
        if rng.random() < 0.5:
            rep_faction = rng.choice(["The Council", "Shadow Guild", "Merchant Alliance", "Ranger Corps"])
            reputation[rep_faction] = rng.randint(10, 50) * int(multiplier)

        unlocks: List[str] = []
        if difficulty in (QuestDifficulty.HARD, QuestDifficulty.EXTREME, QuestDifficulty.LEGENDARY):
            if rng.random() < 0.4:
                unlocks.append(f"unlock_{rng.choice(['area', 'skill', 'recipe', 'faction'])}")

        special_rewards: List[str] = []
        if difficulty == QuestDifficulty.LEGENDARY:
            special_rewards.append(rng.choice(["Title: Champion", "Mount: War Steed", "Achievement: Legendary"]))
        elif difficulty == QuestDifficulty.EXTREME:
            if rng.random() < 0.5:
                special_rewards.append(rng.choice(["Rare Blueprint", "Unique Cosmetic", "Faction Banner"]))

        quest.rewards = QuestReward(
            experience=int(base_exp * multiplier),
            currency=int(base_currency * multiplier),
            items=reward_items,
            reputation=reputation,
            unlocks=unlocks,
            special_rewards=special_rewards,
        )

    def _generate_time_limit(
        self,
        quest_type: QuestType,
        difficulty: QuestDifficulty,
        rng: random.Random,
    ) -> float:
        """Generate an optional time limit for timed quests."""
        if quest_type != QuestType.TIMED:
            return 0.0

        min_time, max_time = DIFFICULTY_TIME_ESTIMATES.get(
            difficulty, (10.0, 25.0)
        )
        return round(rng.uniform(min_time, max_time * 1.5), 1)

    # ------------------------------------------------------------------
    # Quest Chain Generation
    # ------------------------------------------------------------------

    def generate_quest_chain(
        self,
        name: str,
        quest_type: QuestType = QuestType.MAIN_STORY,
        count: int = 3,
        difficulty_progression: bool = True,
        story_theme: str = "",
    ) -> QuestChain:
        """Generate a coherent quest chain with progressive difficulty and narrative.

        Creates a sequence of quests with interconnected objectives, narrative
        continuity between quests, and difficulty that ramps toward a climactic
        final quest. Each quest in the chain logically follows from the previous.

        Args:
            name: Display name for the quest chain.
            quest_type: Base quest type for the chain.
            count: Number of quests in the chain (minimum 2).
            difficulty_progression: Whether difficulty increases through the chain.
            story_theme: Narrative theme for the chain. Picked randomly if empty.

        Returns:
            A QuestChain with interconnected quests forming a story arc.
        """
        with self._lock:
            rng = random.Random()
            actual_count = max(2, min(count, 10))

            if not story_theme:
                story_theme = rng.choice(STORY_THEMES)

            difficulty_order: List[QuestDifficulty] = [
                QuestDifficulty.EASY,
                QuestDifficulty.MODERATE,
                QuestDifficulty.CHALLENGING,
                QuestDifficulty.HARD,
                QuestDifficulty.EXTREME,
                QuestDifficulty.LEGENDARY,
            ]

            locations = rng.sample(LOCATION_POOL, min(actual_count, len(LOCATION_POOL)))
            beats = STORY_BEATS[:actual_count]
            if actual_count > len(STORY_BEATS):
                beats = STORY_BEATS + [
                    f"chapter_{i}" for i in range(len(STORY_BEATS), actual_count)
                ]

            chain_quests: List[QuestDefinition] = []
            prev_quest_id: Optional[str] = None

            for i in range(actual_count):
                if difficulty_progression:
                    progress = i / max(actual_count - 1, 1)
                    diff_index = min(
                        int(progress * (len(difficulty_order) - 1)),
                        len(difficulty_order) - 1,
                    )
                    difficulty = difficulty_order[diff_index]
                else:
                    difficulty = QuestDifficulty.MODERATE

                loc = locations[i] if i < len(locations) else rng.choice(LOCATION_POOL)
                beat_name = beats[i].replace("_", " ").title()

                quest = QuestDefinition(
                    title=f"{name}: {beat_name}",
                    description=self._build_chain_description(story_theme, i, actual_count, beat_name),
                    quest_type=quest_type,
                    difficulty=difficulty,
                    giver_npc_id=rng.choice(NPC_NAME_POOL),
                    location=loc,
                    story_arc=story_theme,
                    prerequisites=[prev_quest_id] if prev_quest_id else [],
                )

                self._populate_objectives(quest, difficulty, rng)
                self._populate_rewards(quest, difficulty, rng)

                if prev_quest_id:
                    prev_quest = self._quests.get(prev_quest_id)
                    if prev_quest:
                        prev_quest.next_quests.append(quest.quest_id)

                self._quests[quest.quest_id] = quest
                self._total_generated += 1
                chain_quests.append(quest)
                prev_quest_id = quest.quest_id

            chain = QuestChain(
                name=name,
                quests=chain_quests,
                story_summary=f"A {actual_count}-part {story_theme} saga unfolding across {quest_type.value} quests.",
                is_sequential=True,
            )
            self._chains[chain.chain_id] = chain
            return chain

    def _build_chain_description(
        self,
        theme: str,
        index: int,
        total: int,
        beat_name: str,
    ) -> str:
        """Build a narrative description for a quest in a chain."""
        if index == 0:
            return f"The {theme} saga begins. {beat_name} — the first step on a perilous journey."
        elif index == total - 1:
            return f"The {theme} reaches its climax. {beat_name} — the final confrontation awaits."
        else:
            return f"Chapter {index + 1} of the {theme} saga. {beat_name} — the path grows darker."

    # ------------------------------------------------------------------
    # Quest Linking
    # ------------------------------------------------------------------

    def link_quests(
        self,
        quest_a_id: str,
        quest_b_id: str,
    ) -> Optional[QuestDefinition]:
        """Link two quests so that quest_b becomes a follow-up to quest_a.

        Args:
            quest_a_id: ID of the prerequisite quest.
            quest_b_id: ID of the follow-up quest.

        Returns:
            The updated quest_a QuestDefinition, or None if either quest is not found.
        """
        with self._lock:
            quest_a = self._quests.get(quest_a_id)
            quest_b = self._quests.get(quest_b_id)
            if quest_a is None or quest_b is None:
                return None

            if quest_b_id not in quest_a.next_quests:
                quest_a.next_quests.append(quest_b_id)
            if quest_a_id not in quest_b.prerequisites:
                quest_b.prerequisites.append(quest_a_id)
            return quest_a

    # ------------------------------------------------------------------
    # Validation & Estimation
    # ------------------------------------------------------------------

    def validate_quest(self, quest_id: str) -> Dict[str, Any]:
        """Validate a quest for completeness and correctness.

        Checks that the quest has required fields populated, objectives are
        valid, rewards are balanced for the difficulty, and prerequisites
        exist in the registry.

        Args:
            quest_id: ID of the quest to validate.

        Returns:
            A dict with validation results including valid flag and issues list.
        """
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return {"valid": False, "error": "Quest not found", "issues": []}

            issues: List[str] = []

            if not quest.title:
                issues.append("Quest has no title")
            if not quest.description:
                issues.append("Quest has no description")
            if not quest.objectives:
                issues.append("Quest has no objectives")
            if not quest.location:
                issues.append("Quest has no location")

            required_objectives = [o for o in quest.objectives if not o.is_optional]
            if not required_objectives:
                issues.append("Quest has no required objectives")

            for obj in quest.objectives:
                if not obj.description:
                    issues.append(f"Objective {obj.objective_id} has no description")
                if obj.target_count <= 0:
                    issues.append(f"Objective {obj.objective_id} has invalid target_count")

            multiplier = DIFFICULTY_MULTIPLIERS.get(quest.difficulty, 1.0)
            expected_exp_min = int(50 * len(required_objectives) * multiplier)
            if quest.rewards.experience < expected_exp_min * 0.3:
                issues.append("Reward experience is too low for the difficulty")

            for prereq_id in quest.prerequisites:
                if prereq_id not in self._quests:
                    issues.append(f"Prerequisite quest {prereq_id} not found in registry")

            for next_id in quest.next_quests:
                if next_id not in self._quests:
                    issues.append(f"Next quest {next_id} not found in registry")

            return {
                "valid": len(issues) == 0,
                "quest_id": quest_id,
                "title": quest.title,
                "issues": issues,
                "objective_count": len(quest.objectives),
                "required_objective_count": len(required_objectives),
                "reward_total": quest.rewards.to_dict(),
            }

    def estimate_completion_time(self, quest_id: str) -> float:
        """Estimate the time in minutes required to complete a quest.

        Calculates based on objective count, objective types, difficulty,
        and any time limit set on the quest.

        Args:
            quest_id: ID of the quest to estimate.

        Returns:
            Estimated completion time in minutes. Returns 0.0 if quest not found.
        """
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return 0.0

            if quest.time_limit > 0:
                return quest.time_limit

            base_time = 0.0
            for obj in quest.objectives:
                if obj.type == ObjectiveType.KILL_ENEMY:
                    base_time += obj.target_count * 1.5
                elif obj.type == ObjectiveType.REACH_LOCATION:
                    base_time += 3.0
                elif obj.type == ObjectiveType.COLLECT_ITEM:
                    base_time += obj.target_count * 2.0
                elif obj.type == ObjectiveType.ESCORT_NPC:
                    base_time += 8.0
                elif obj.type == ObjectiveType.DEFEND_POINT:
                    base_time += 5.0
                elif obj.type == ObjectiveType.SOLVE_PUZZLE:
                    base_time += 6.0
                elif obj.type == ObjectiveType.SURVIVE_TIME:
                    base_time += obj.target_count * 1.0
                elif obj.type == ObjectiveType.CRAFT_ITEM:
                    base_time += obj.target_count * 3.0
                elif obj.type == ObjectiveType.STEALTH_PASS:
                    base_time += 5.0
                else:
                    base_time += 2.0

            multiplier = DIFFICULTY_MULTIPLIERS.get(quest.difficulty, 1.0)
            return round(base_time * multiplier * 0.8, 1)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_quest(self, quest_id: str) -> Optional[QuestDefinition]:
        """Retrieve a quest by its ID."""
        with self._lock:
            return self._quests.get(quest_id)

    def list_quests(
        self,
        quest_type: Optional[QuestType] = None,
        difficulty: Optional[QuestDifficulty] = None,
        status: Optional[QuestStatus] = None,
    ) -> List[QuestDefinition]:
        """List quests filtered by optional criteria.

        Args:
            quest_type: Filter by quest type. All types if None.
            difficulty: Filter by difficulty. All difficulties if None.
            status: Filter by status. Not currently enforced in registry.

        Returns:
            A list of QuestDefinition instances matching the filters.
        """
        with self._lock:
            results = list(self._quests.values())
            if quest_type is not None:
                results = [q for q in results if q.quest_type == quest_type]
            if difficulty is not None:
                results = [q for q in results if q.difficulty == difficulty]
            if status is not None:
                _ = status  # Status filtering placeholder for future state tracking
            return results

    def get_chain(self, chain_id: str) -> Optional[QuestChain]:
        """Retrieve a quest chain by its ID."""
        with self._lock:
            return self._chains.get(chain_id)

    def list_chains(self) -> List[QuestChain]:
        """List all generated quest chains."""
        with self._lock:
            return list(self._chains.values())

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive generation statistics.

        Returns:
            A dict with total counts, type distribution, difficulty distribution,
            and chain statistics.
        """
        with self._lock:
            type_counts: Dict[str, int] = {}
            diff_counts: Dict[str, int] = {}
            total_objectives = 0
            total_reward_exp = 0
            total_reward_currency = 0

            for quest in self._quests.values():
                type_counts[quest.quest_type.value] = type_counts.get(quest.quest_type.value, 0) + 1
                diff_counts[quest.difficulty.value] = diff_counts.get(quest.difficulty.value, 0) + 1
                total_objectives += len(quest.objectives)
                total_reward_exp += quest.rewards.experience
                total_reward_currency += quest.rewards.currency

            chain_quest_total = sum(len(c.quests) for c in self._chains.values())

            return {
                "total_quests": len(self._quests),
                "total_quests_generated": self._total_generated,
                "total_chains": len(self._chains),
                "total_objectives": total_objectives,
                "total_reward_experience": total_reward_exp,
                "total_reward_currency": total_reward_currency,
                "avg_objectives_per_quest": round(total_objectives / max(len(self._quests), 1), 2),
                "type_distribution": type_counts,
                "difficulty_distribution": diff_counts,
                "chain_quest_total": chain_quest_total,
            }


# ------------------------------------------------------------------
# Module-level convenience accessor
# ------------------------------------------------------------------


def get_quest_generator() -> QuestGeneratorEngine:
    """Return the singleton QuestGeneratorEngine instance."""
    return QuestGeneratorEngine.get_instance()