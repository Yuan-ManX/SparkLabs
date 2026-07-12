"""
SparkLabs Agent - AI Quest Generator

An AI-native fusion module that dynamically creates quests, missions, and
objectives for the SparkLabs game engine. The generator treats quest design
as a living system: reusable templates are assembled from objective and
reward blueprints, then instantiated into live quests that carry difficulty
scaling, branching paths, chain linkage, and deterministic pacing that
reacts to the live game context and the player's history.

This module embodies the AI-native principle: a quest is not a static asset
but an adaptive construction that scales to player skill, shifts difficulty
on the fly as the world state changes, layers branching choices across the
narrative, and records a full event timeline that can be replayed, audited,
and tuned.

Architecture:
  AIQuestGenerator (singleton)
    |-- QuestObjective, QuestReward, QuestRequirement, QuestBranch,
        QuestChain, QuestTemplate, QuestInstance, PlayerQuestProfile,
        QuestGenConfig, QuestGenStats, QuestGenSnapshot, QuestGenEvent
    |-- QuestType, QuestStatus, QuestDifficulty, ObjectiveType,
        ObjectiveStatus, QuestCategory, RewardType, QuestPriority,
        QuestGenEventKind

Core Capabilities:
  - register_template / get_template / list_templates / remove_template /
    update_template: quest template library management across every quest
    type, category, and difficulty.
  - generate_quest / generate_from_template / generate_chain: deterministic
    quest and chain generation from templates and themes.
  - auto_generate_quest / auto_generate_chain: AI-driven personalized quest
    and chain generation driven by player profile and world context.
  - get_quest / list_quests / remove_quest / accept_quest / complete_quest /
    fail_quest / expire_quest / abandon_quest: quest instance lifecycle
    management with status transitions.
  - update_objective / get_objective / list_objectives: objective progress
    tracking with status propagation.
  - get_chain / list_chains / advance_chain / remove_chain: quest chain
    management with sequential quest unlocking.
  - register_player_profile / get_player_profile / update_player_profile /
    list_player_profiles / remove_player_profile: player profile library
    with quest history and preference tracking.
  - create_branch / get_branch / list_branches / remove_branch /
    choose_branch: branching narrative paths with consequence tracking.
  - suggest_difficulty / optimize_quest_flow: AI-driven difficulty and
    pacing analysis driven by player skill and history.
  - list_events / get_stats / get_status / get_snapshot / set_config /
    get_config / tick / reset: observability, tuning, and state management.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_TEMPLATES: int = 500
_MAX_QUESTS: int = 5000
_MAX_CHAINS: int = 200
_MAX_PLAYER_PROFILES: int = 1000
_MAX_BRANCHES: int = 500
_MAX_EVENTS: int = 8000
_MAX_OBJECTIVES_PER_QUEST: int = 16
_MAX_REWARDS_PER_QUEST: int = 12
_MAX_QUESTS_PER_CHAIN: int = 10
_MAX_QUESTS_PER_PLAYER: int = 50


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    # Check __dataclass_fields__ BEFORE to_dict to avoid recursion when a
    # dataclass also defines a to_dict method that delegates back here.
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        if hasattr(instance, "to_dict") and callable(instance.to_dict):
            return instance.to_dict()
        return {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = low
    if v < low:
        return low
    if v > high:
        return high
    return v


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Quest Knowledge Tables
# ---------------------------------------------------------------------------

# Maps a quest category to the objective types that fit it. Used by the
# template selection logic to pick objectives that match a requested
# category when no explicit template is supplied.
_CATEGORY_OBJECTIVE_MAP: Dict["QuestCategory", List["ObjectiveType"]] = {}


# Maps a quest difficulty to a level scaling band. Each entry is the
# (min_level_offset, max_level_offset, reward_multiplier) tuple. The level
# offset is added to the player level to compute the recommended quest
# level, and the reward multiplier scales the base reward amounts.
_DIFFICULTY_BANDS: Dict["QuestDifficulty", Tuple[int, int, float]] = {}


# Maps a quest type to its default priority. Event and main story quests
# rank above daily and side quests when the system auto-selects a priority.
_TYPE_DEFAULT_PRIORITY: Dict["QuestType", "QuestPriority"] = {}


# Theme keyword table used by auto_generate_quest and auto_generate_chain.
# Each entry is (keywords, quest_type, category, difficulty). The first
# matching entry wins. This drives deterministic context-to-quest mapping.
_THEME_KEYWORDS: List[Tuple[List[str], "QuestType", "QuestCategory",
                            "QuestDifficulty"]] = []


# Quest name fragments used by auto generation. The generator combines a
# verb, a subject, and an optional qualifier to build a readable quest name.
_QUEST_NAME_VERBS: List[str] = []
_QUEST_NAME_SUBJECTS: List[str] = []
_QUEST_NAME_QUALIFIERS: List[str] = []


# Quest description templates per quest type. The {subject} and {location}
# placeholders are filled from the world context.
_QUEST_DESCRIPTION_TEMPLATES: Dict["QuestType", List[str]] = {}


# Quest flow suggestion templates used by optimize_quest_flow. Each entry
# is a (condition, suggestion_text) pair evaluated against player stats.
_FLOW_SUGGESTION_RULES: List[Tuple[str, str]] = []


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class QuestType(str, Enum):
    """Top-level classification of a quest's narrative role."""
    MAIN_STORY = "main_story"
    SIDE_QUEST = "side_quest"
    DAILY = "daily"
    WEEKLY = "weekly"
    EVENT = "event"
    HIDDEN = "hidden"
    ESCORT = "escort"
    BOUNTY = "bounty"
    DELIVERY = "delivery"
    INVESTIGATION = "investigation"
    COLLECTION = "collection"
    DEFENSE = "defense"
    RESCUE = "rescue"
    RETRIEVAL = "retrieval"


class QuestStatus(str, Enum):
    """Lifecycle state of a quest instance."""
    DRAFT = "draft"
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    LOCKED = "locked"


class QuestDifficulty(str, Enum):
    """Difficulty tier that scales quest level and rewards."""
    TRIVIAL = "trivial"
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    EXTREME = "extreme"
    LEGENDARY = "legendary"


class ObjectiveType(str, Enum):
    """Classification of an objective's required action."""
    REACH_LOCATION = "reach_location"
    TALK_TO_NPC = "talk_to_npc"
    DEFEAT_ENEMIES = "defeat_enemies"
    COLLECT_ITEMS = "collect_items"
    ESCORT_NPC = "escort_npc"
    PROTECT_TARGET = "protect_target"
    SOLVE_PUZZLE = "solve_puzzle"
    SURVIVE_WAVES = "survive_waves"
    CRAFT_ITEM = "craft_item"
    EXPLORE_AREA = "explore_area"


class ObjectiveStatus(str, Enum):
    """Lifecycle state of a single quest objective."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    OPTIONAL = "optional"


class QuestCategory(str, Enum):
    """Gameplay category that groups quests by activity type."""
    COMBAT = "combat"
    EXPLORATION = "exploration"
    SOCIAL = "social"
    CRAFTING = "crafting"
    COLLECTION = "collection"
    STORY = "story"
    EVENT = "event"
    REPEATABLE = "repeatable"


class RewardType(str, Enum):
    """Type of reward granted on quest completion."""
    EXPERIENCE = "experience"
    GOLD = "gold"
    ITEM = "item"
    SKILL = "skill"
    REPUTATION = "reputation"
    ACHIEVEMENT = "achievement"
    COSMETIC = "cosmetic"
    UNLOCK = "unlock"


class QuestPriority(str, Enum):
    """Scheduling priority that orders quest availability for players."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class QuestGenEventKind(str, Enum):
    """Audit event kind recorded on the generator timeline."""
    QUEST_CREATED = "quest_created"
    QUEST_REMOVED = "quest_removed"
    QUEST_ACCEPTED = "quest_accepted"
    QUEST_COMPLETED = "quest_completed"
    QUEST_FAILED = "quest_failed"
    OBJECTIVE_UPDATED = "objective_updated"
    CHAIN_GENERATED = "chain_generated"
    CONFIG_CHANGED = "config_changed"
    SYSTEM_RESET = "system_reset"


# Populate the knowledge tables now that the enums exist.
_CATEGORY_OBJECTIVE_MAP = {
    QuestCategory.COMBAT: [
        ObjectiveType.DEFEAT_ENEMIES,
        ObjectiveType.SURVIVE_WAVES,
        ObjectiveType.PROTECT_TARGET,
    ],
    QuestCategory.EXPLORATION: [
        ObjectiveType.REACH_LOCATION,
        ObjectiveType.EXPLORE_AREA,
        ObjectiveType.SOLVE_PUZZLE,
    ],
    QuestCategory.SOCIAL: [
        ObjectiveType.TALK_TO_NPC,
        ObjectiveType.ESCORT_NPC,
    ],
    QuestCategory.CRAFTING: [
        ObjectiveType.CRAFT_ITEM,
        ObjectiveType.COLLECT_ITEMS,
    ],
    QuestCategory.COLLECTION: [
        ObjectiveType.COLLECT_ITEMS,
        ObjectiveType.REACH_LOCATION,
    ],
    QuestCategory.STORY: [
        ObjectiveType.TALK_TO_NPC,
        ObjectiveType.REACH_LOCATION,
        ObjectiveType.DEFEAT_ENEMIES,
        ObjectiveType.SOLVE_PUZZLE,
    ],
    QuestCategory.EVENT: [
        ObjectiveType.SURVIVE_WAVES,
        ObjectiveType.DEFEAT_ENEMIES,
        ObjectiveType.COLLECT_ITEMS,
    ],
    QuestCategory.REPEATABLE: [
        ObjectiveType.COLLECT_ITEMS,
        ObjectiveType.DEFEAT_ENEMIES,
        ObjectiveType.REACH_LOCATION,
    ],
}

_DIFFICULTY_BANDS = {
    QuestDifficulty.TRIVIAL: (-3, -1, 0.5),
    QuestDifficulty.EASY: (-1, 1, 0.8),
    QuestDifficulty.NORMAL: (0, 2, 1.0),
    QuestDifficulty.HARD: (2, 4, 1.5),
    QuestDifficulty.EXTREME: (4, 6, 2.2),
    QuestDifficulty.LEGENDARY: (6, 10, 3.5),
}

_TYPE_DEFAULT_PRIORITY = {
    QuestType.MAIN_STORY: QuestPriority.HIGH,
    QuestType.SIDE_QUEST: QuestPriority.NORMAL,
    QuestType.DAILY: QuestPriority.LOW,
    QuestType.WEEKLY: QuestPriority.NORMAL,
    QuestType.EVENT: QuestPriority.URGENT,
    QuestType.HIDDEN: QuestPriority.NORMAL,
    QuestType.ESCORT: QuestPriority.NORMAL,
    QuestType.BOUNTY: QuestPriority.NORMAL,
    QuestType.DELIVERY: QuestPriority.LOW,
    QuestType.INVESTIGATION: QuestPriority.NORMAL,
    QuestType.COLLECTION: QuestPriority.LOW,
    QuestType.DEFENSE: QuestPriority.HIGH,
    QuestType.RESCUE: QuestPriority.URGENT,
    QuestType.RETRIEVAL: QuestPriority.NORMAL,
}

_THEME_KEYWORDS = [
    (["slay", "beast", "monster", "dragon", "creature", "hunt",
      "kill"], QuestType.BOUNTY, QuestCategory.COMBAT, QuestDifficulty.HARD),
    (["deliver", "letter", "package", "parcel", "message",
      "courier"], QuestType.DELIVERY, QuestCategory.SOCIAL,
     QuestDifficulty.EASY),
    (["explore", "ruins", "dungeon", "cave", "tomb", "crypt",
      "discover"], QuestType.INVESTIGATION, QuestCategory.EXPLORATION,
     QuestDifficulty.NORMAL),
    (["escort", "merchant", "traveler", "noble", "guide",
      "protect"], QuestType.ESCORT, QuestCategory.SOCIAL,
     QuestDifficulty.NORMAL),
    (["collect", "gather", "herbs", "materials", "ingredients",
      "harvest"], QuestType.COLLECTION, QuestCategory.COLLECTION,
     QuestDifficulty.EASY),
    (["defend", "village", "fortress", "town", "outpost", "siege",
      "wave"], QuestType.DEFENSE, QuestCategory.COMBAT,
     QuestDifficulty.HARD),
    (["investigate", "mystery", "clue", "secret", "unknown",
      "puzzle"], QuestType.INVESTIGATION, QuestCategory.EXPLORATION,
     QuestDifficulty.NORMAL),
    (["retrieve", "artifact", "relic", "treasure", "recover",
      "steal"], QuestType.RETRIEVAL, QuestCategory.EXPLORATION,
     QuestDifficulty.HARD),
    (["rescue", "hostage", "captured", "prison", "save",
      "free"], QuestType.RESCUE, QuestCategory.COMBAT,
     QuestDifficulty.EXTREME),
    (["story", "main", "prophecy", "destiny", "hero",
      "legacy"], QuestType.MAIN_STORY, QuestCategory.STORY,
     QuestDifficulty.NORMAL),
]

_QUEST_NAME_VERBS = [
    "Slay", "Hunt", "Deliver", "Explore", "Escort", "Collect", "Defend",
    "Investigate", "Retrieve", "Rescue", "Recover", "Protect", "Uncover",
    "Forge", "Reclaim", "Vanquish",
]

_QUEST_NAME_SUBJECTS = [
    "the Beast", "the Dragon", "the Letter", "the Ruins", "the Merchant",
    "the Herbs", "the Village", "the Mystery", "the Artifact", "the Captive",
    "the Relic", "the Outpost", "the Crypt", "the Bandit Lord",
    "the Lost Heir", "the Shadow Cult", "the Ancient Tome",
    "the Forgotten King", "the Wandering Sage", "the Cursed Blade",
]

_QUEST_NAME_QUALIFIERS = [
    "of Oakhaven", "in the Deep Woods", "at Dawn", "beneath the Mountain",
    "of the Northern Reach", "in the Ruined Keep", "of the Forgotten Coast",
    "at the Crossroads", "of the Iron Vanguard", "in the Hollow",
    "of the Pale Moon", "in the Shattered Valley",
]

_QUEST_DESCRIPTION_TEMPLATES = {
    QuestType.BOUNTY: [
        "A fearsome {subject} has been terrorizing the region. Hunt it down "
        "and bring peace to the locals.",
        "The bounty board offers coin for the defeat of {subject}. Track it "
        "to its lair and end its threat.",
    ],
    QuestType.DELIVERY: [
        "A sealed letter must reach {subject} before nightfall. The road is "
        "long and not without peril.",
        "Deliver this package to {subject} in the next settlement. Speed and "
        "discretion are essential.",
    ],
    QuestType.INVESTIGATION: [
        "Strange occurrences surround {subject}. Investigate the site and "
        "uncover the truth hidden beneath the surface.",
        "Travel to {subject} and piece together the clues left behind by "
        "those who came before.",
    ],
    QuestType.ESCORT: [
        "Escort {subject} safely to the destination. The roads are watched "
        "by those who mean harm.",
        "{subject} has requested an armed escort through dangerous "
        "territory. Keep them safe at all costs.",
    ],
    QuestType.COLLECTION: [
        "Gather the rare materials found near {subject}. The local crafter "
        "needs them for an important project.",
        "Collect the herbs and reagents that grow around {subject}. The "
        "apothecary will reward your effort.",
    ],
    QuestType.DEFENSE: [
        "Defend {subject} from the incoming assault. Hold the line until "
        "reinforcements arrive.",
        "Waves of enemies march on {subject}. Stand firm and repel every "
        "attack until dawn.",
    ],
    QuestType.RESCUE: [
        "Captives are held at {subject}. Infiltrate the stronghold and bring "
        "them home alive.",
        "A prisoner of war is held somewhere near {subject}. Find them and "
        "lead them to safety.",
    ],
    QuestType.RETRIEVAL: [
        "A powerful artifact rests within {subject}. Recover it before it "
        "falls into the wrong hands.",
        "The relic of {subject} was stolen. Track the thieves and reclaim "
        "what was taken.",
    ],
    QuestType.MAIN_STORY: [
        "The fate of the realm turns on your actions at {subject}. Fulfill "
        "your destiny and shape the age to come.",
        "Travel to {subject} and confront the truth that has shaped your "
        "journey from the start.",
    ],
    QuestType.SIDE_QUEST: [
        "A villager near {subject} needs a capable hand. The task is small "
        "but the gratitude is genuine.",
        "Word has reached you of opportunity near {subject}. Investigate and "
        "decide for yourself.",
    ],
    QuestType.DAILY: [
        "Repeatable work is available near {subject}. Return each day for a "
        "fresh assignment.",
        "The local guild offers a daily contract tied to {subject}. Complete "
        "it for steady reward.",
    ],
    QuestType.WEEKLY: [
        "A weekly challenge beckons from {subject}. The reward scales with "
        "your resolve.",
        "The council has posted a weekly task near {subject}. See it through "
        "before the week ends.",
    ],
    QuestType.EVENT: [
        "A limited-time event unfolds at {subject}. Join the effort before "
        "the window closes.",
        "Festivity and danger await at {subject}. Take part in the event "
        "while it lasts.",
    ],
    QuestType.HIDDEN: [
        "A hidden path leads toward {subject}. Few know of it, and fewer "
        "still return to tell of it.",
        "Rumors whisper of something buried at {subject}. Seek it out if you "
        "dare.",
    ],
}

_FLOW_SUGGESTION_RULES = [
    ("low_completion_rate",
     "Player completion rate is below 40 percent. Recommend offering "
     "lower-difficulty quests and shorter chains to rebuild momentum."),
    ("high_failure_rate",
     "Failure rate exceeds 25 percent. Suggest trimming hard and extreme "
     "quests from the active rotation until the player regains confidence."),
    ("stale_active_quests",
     "The player holds more than 8 active quests at once. Recommend "
     "completing or abandoning older quests before assigning new ones."),
    ("chain_stall",
     "Chain progress has stalled for over 3 quests. Suggest advancing the "
     "oldest open chain before generating new side content."),
    ("difficulty_spike",
     "Recent difficulty has jumped two tiers in a row. Recommend a brief "
     "respite with a normal or easy quest to balance pacing."),
    ("category_monotony",
     "The last 5 quests share the same category. Suggest rotating to a new "
     "category to keep the experience varied."),
    ("repeatable_grind",
     "Repeatable quests dominate recent activity. Suggest weaving in a "
     "story or exploration quest to break the grind."),
    ("level_gap",
     "Player level is more than 5 levels above the recommended quest level. "
     "Suggest raising the difficulty tier to keep rewards meaningful."),
    ("level_strain",
     "Player level is more than 3 levels below the recommended quest level. "
     "Suggest lowering the difficulty or offering a leveling quest first."),
    ("no_recent_event",
     "No event quest has been offered recently. Suggest surfacing a "
     "time-limited event to renew engagement."),
]


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class QuestObjective:
    """A single objective within a quest, with a target and progress."""
    objective_id: str
    objective_type: str
    target: str
    count: int = 1
    current: int = 0
    status: str = "pending"
    description: str = ""
    optional: bool = False
    order: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QuestReward:
    """A reward granted upon quest or objective completion."""
    reward_id: str
    reward_type: str
    amount: int = 0
    item_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QuestRequirement:
    """A prerequisite that must be met before a quest becomes available."""
    requirement_id: str
    requirement_type: str
    target: str
    value: int = 0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QuestBranch:
    """A branching narrative path attached to a quest."""
    branch_id: str
    quest_id: str
    name: str
    description: str = ""
    choice_label: str = ""
    consequences: List[str] = field(default_factory=list)
    objective_overrides: List[Dict[str, Any]] = field(default_factory=list)
    reward_overrides: List[Dict[str, Any]] = field(default_factory=list)
    next_quest_template_id: str = ""
    chosen: bool = False
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QuestChain:
    """A linked sequence of quests that unfold as a larger arc."""
    chain_id: str
    name: str
    theme: str
    description: str = ""
    quest_ids: List[str] = field(default_factory=list)
    template_ids: List[str] = field(default_factory=list)
    current_index: int = 0
    total_quests: int = 0
    completed_quests: int = 0
    status: str = "available"
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QuestTemplate:
    """A reusable blueprint for generating quest instances."""
    template_id: str
    name: str
    quest_type: str
    category: str
    difficulty: str
    description: str
    priority: str = "normal"
    min_level: int = 1
    max_level: int = 99
    recommended_level: int = 1
    time_limit: float = 0.0
    repeatable: bool = False
    objectives: List[QuestObjective] = field(default_factory=list)
    rewards: List[QuestReward] = field(default_factory=list)
    requirements: List[QuestRequirement] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QuestInstance:
    """A live quest instantiated from a template or generated on demand."""
    quest_id: str
    template_id: str
    name: str
    quest_type: str
    category: str
    difficulty: str
    description: str
    priority: str = "normal"
    status: str = "available"
    player_id: str = ""
    player_level: int = 1
    recommended_level: int = 1
    time_limit: float = 0.0
    time_remaining: float = 0.0
    chain_id: str = ""
    chain_index: int = -1
    objectives: List[QuestObjective] = field(default_factory=list)
    rewards: List[QuestReward] = field(default_factory=list)
    requirements: List[QuestRequirement] = field(default_factory=list)
    branch_ids: List[str] = field(default_factory=list)
    accepted_at: str = ""
    completed_at: str = ""
    expired_at: str = ""
    failed_at: str = ""
    fail_reason: str = ""
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerQuestProfile:
    """A player's quest history, preferences, and skill ratings."""
    player_id: str
    name: str
    level: int = 1
    faction: str = ""
    active_quests: List[str] = field(default_factory=list)
    completed_quests: List[str] = field(default_factory=list)
    failed_quests: List[str] = field(default_factory=list)
    abandoned_quests: List[str] = field(default_factory=list)
    preferred_categories: List[str] = field(default_factory=list)
    preferred_difficulty: str = "normal"
    quest_completion_rate: float = 0.0
    total_quests_attempted: int = 0
    total_quests_completed: int = 0
    chain_progress: Dict[str, int] = field(default_factory=dict)
    skill_ratings: Dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QuestGenConfig:
    """Global tuning parameters for the quest generator."""
    max_templates: int = 500
    max_quests: int = 5000
    max_chains: int = 200
    max_player_profiles: int = 1000
    max_branches: int = 500
    max_events: int = 8000
    max_objectives_per_quest: int = 16
    max_rewards_per_quest: int = 12
    max_quests_per_chain: int = 10
    max_quests_per_player: int = 50
    default_difficulty: str = "normal"
    default_priority: str = "normal"
    auto_accept: bool = False
    auto_complete_objectives: bool = False
    enable_branching: bool = True
    enable_chains: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QuestGenStats:
    """Aggregate counters describing generator activity."""
    total_templates: int = 0
    total_quests: int = 0
    total_chains: int = 0
    total_player_profiles: int = 0
    total_branches: int = 0
    active_quests: int = 0
    completed_quests: int = 0
    failed_quests: int = 0
    expired_quests: int = 0
    total_generated: int = 0
    total_auto_generated: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QuestGenSnapshot:
    """Full state snapshot for persistence and inspection."""
    timestamp: str = field(default_factory=_now)
    templates: List[Dict[str, Any]] = field(default_factory=list)
    quests: List[Dict[str, Any]] = field(default_factory=list)
    chains: List[Dict[str, Any]] = field(default_factory=list)
    player_profiles: List[Dict[str, Any]] = field(default_factory=list)
    branches: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QuestGenEvent:
    """An audit event recorded on the generator timeline."""
    event_id: str
    timestamp: str
    event_type: str
    quest_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# AI Quest Generator Singleton
# ---------------------------------------------------------------------------


# Module-level lock and singleton holder for double-checked locking.
_lock = threading.RLock()
_instance: Optional["AIQuestGenerator"] = None


class AIQuestGenerator:
    """
    AI-native fusion module that dynamically creates quests, missions, and
    objectives for the SparkLabs game engine. The generator owns the quest
    template library, live quest registry, quest chains, player profiles,
    and branching paths as a single coherent state machine.

    Implements a singleton via module-level double-checked locking. All
    mutations to internal state are guarded by an instance lock so the
    generator is safe to call from multiple threads. Seed population is
    guarded by a dedicated init lock so re-entrancy during reset cannot
    double-seed the canonical dataset.

    AI methods (auto_generate_quest, auto_generate_chain,
    suggest_difficulty, optimize_quest_flow) use deterministic logic driven
    by theme keyword tables, difficulty bands, and player skill ratings so
    results are reproducible across runs without external network calls.
    """

    _init_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Construction and Singleton
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._templates: Dict[str, QuestTemplate] = {}
        self._quests: Dict[str, QuestInstance] = {}
        self._chains: Dict[str, QuestChain] = {}
        self._player_profiles: Dict[str, PlayerQuestProfile] = {}
        self._branches: Dict[str, QuestBranch] = {}
        self._events: List[QuestGenEvent] = []
        self._config = QuestGenConfig()
        self._stats = QuestGenStats()
        self._tick_count: int = 0
        self._generate_counter: int = 0
        self._auto_generate_counter: int = 0
        self._complete_counter: int = 0
        self._fail_counter: int = 0
        self._expire_counter: int = 0
        self._initialized: bool = False
        self.initialize()

    @classmethod
    def get_instance(cls) -> "AIQuestGenerator":
        global _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = cls()
        return _instance

    def initialize(self) -> None:
        """Idempotently initialize and seed the generator."""
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._seed()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, quest_id: str = "",
              description: str = "",
              data: Optional[Dict[str, Any]] = None) -> None:
        event = QuestGenEvent(
            event_id=_new_id("evt"),
            timestamp=_now(),
            event_type=event_type,
            quest_id=quest_id,
            description=description,
            metadata=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, self._config.max_events)

    def _refresh_stats(self) -> None:
        self._stats.total_templates = len(self._templates)
        self._stats.total_quests = len(self._quests)
        self._stats.total_chains = len(self._chains)
        self._stats.total_player_profiles = len(self._player_profiles)
        self._stats.total_branches = len(self._branches)
        self._stats.active_quests = sum(
            1 for q in self._quests.values()
            if q.status in (QuestStatus.AVAILABLE.value,
                            QuestStatus.ACTIVE.value)
        )
        self._stats.completed_quests = sum(
            1 for q in self._quests.values()
            if q.status == QuestStatus.COMPLETED.value
        )
        self._stats.failed_quests = sum(
            1 for q in self._quests.values()
            if q.status == QuestStatus.FAILED.value
        )
        self._stats.expired_quests = sum(
            1 for q in self._quests.values()
            if q.status == QuestStatus.EXPIRED.value
        )
        self._stats.total_generated = self._generate_counter
        self._stats.total_auto_generated = self._auto_generate_counter
        self._stats.tick_count = self._tick_count

    def _resolve_difficulty(self, difficulty: str) -> str:
        """Resolve a difficulty string falling back to the config default."""
        if difficulty:
            diff_enum = _coerce_enum(QuestDifficulty, difficulty)
            if diff_enum is not None:
                return diff_enum.value
            return str(difficulty).lower()
        return self._config.default_difficulty

    def _resolve_priority(self, priority: str,
                          quest_type_enum: Optional[QuestType] = None) -> str:
        """Resolve a priority string, falling back to the type default."""
        if priority:
            pri_enum = _coerce_enum(QuestPriority, priority)
            if pri_enum is not None:
                return pri_enum.value
            return str(priority).lower()
        if quest_type_enum is not None:
            return _TYPE_DEFAULT_PRIORITY.get(
                quest_type_enum, QuestPriority.NORMAL
            ).value
        return self._config.default_priority

    def _compute_recommended_level(self, player_level: int,
                                   difficulty_enum: QuestDifficulty) -> int:
        """Compute the recommended quest level from player level and band."""
        band = _DIFFICULTY_BANDS.get(difficulty_enum, (0, 2, 1.0))
        min_offset, max_offset, _ = band
        # Use the midpoint of the band as the default offset.
        offset = (min_offset + max_offset) // 2
        recommended = max(1, _safe_int(player_level, 1) + offset)
        return recommended

    def _scale_rewards(self, rewards: List[QuestReward],
                       difficulty_enum: QuestDifficulty) -> List[QuestReward]:
        """Return a copy of rewards with amounts scaled by difficulty band."""
        band = _DIFFICULTY_BANDS.get(difficulty_enum, (0, 2, 1.0))
        multiplier = band[2]
        scaled: List[QuestReward] = []
        for reward in rewards:
            scaled.append(QuestReward(
                reward_id=reward.reward_id,
                reward_type=reward.reward_type,
                amount=max(0, int(round(reward.amount * multiplier))),
                item_id=reward.item_id,
                description=reward.description,
                metadata=dict(reward.metadata),
            ))
        return scaled

    def _clone_objectives(self, objectives: List[QuestObjective]) -> List[QuestObjective]:
        """Produce a deep copy of a list of objectives for a new instance."""
        cloned: List[QuestObjective] = []
        for idx, obj in enumerate(objectives):
            cloned.append(QuestObjective(
                objective_id=_new_id("obj"),
                objective_type=obj.objective_type,
                target=obj.target,
                count=max(1, obj.count),
                current=0,
                status=ObjectiveStatus.PENDING.value,
                description=obj.description,
                optional=bool(obj.optional),
                order=idx,
                metadata=dict(obj.metadata),
            ))
        return cloned

    def _clone_rewards(self, rewards: List[QuestReward]) -> List[QuestReward]:
        """Produce a deep copy of a list of rewards for a new instance."""
        cloned: List[QuestReward] = []
        for reward in rewards:
            cloned.append(QuestReward(
                reward_id=_new_id("rew"),
                reward_type=reward.reward_type,
                amount=max(0, reward.amount),
                item_id=reward.item_id,
                description=reward.description,
                metadata=dict(reward.metadata),
            ))
        return cloned

    def _clone_requirements(self,
                            requirements: List[QuestRequirement]) -> List[QuestRequirement]:
        """Produce a deep copy of a list of requirements for a new instance."""
        cloned: List[QuestRequirement] = []
        for req in requirements:
            cloned.append(QuestRequirement(
                requirement_id=_new_id("req"),
                requirement_type=req.requirement_type,
                target=req.target,
                value=req.value,
                description=req.description,
            ))
        return cloned

    def _theme_to_quest_spec(self, theme: str) -> Tuple[QuestType,
                                                        QuestCategory,
                                                        QuestDifficulty]:
        """Map a theme string to a quest type, category, and difficulty.

        Returns the first keyword group that matches the lowercased theme.
        Falls back to a side quest with normal difficulty when no keywords
        match.
        """
        if not theme:
            return (QuestType.SIDE_QUEST, QuestCategory.STORY,
                    QuestDifficulty.NORMAL)
        lowered = theme.lower()
        for keywords, q_type, category, difficulty in _THEME_KEYWORDS:
            for kw in keywords:
                if kw in lowered:
                    return q_type, category, difficulty
        return (QuestType.SIDE_QUEST, QuestCategory.STORY,
                QuestDifficulty.NORMAL)

    def _build_quest_name(self, verb: str, subject: str,
                          qualifier: str = "") -> str:
        """Assemble a readable quest name from fragments."""
        base = f"{verb} {subject}"
        if qualifier:
            return f"{base} {qualifier}"
        return base

    def _build_quest_description(self, quest_type_enum: QuestType,
                                 subject: str) -> str:
        """Build a description from the type's template list."""
        templates = _QUEST_DESCRIPTION_TEMPLATES.get(quest_type_enum, [])
        if not templates:
            return f"A quest centered on {subject}."
        # Pick deterministically by hashing the subject so the same subject
        # always yields the same description text.
        idx = hash(subject) % len(templates) if subject else 0
        template = templates[idx]
        try:
            return template.format(subject=subject or "the region")
        except (KeyError, IndexError):
            return template

    def _select_template_for_context(self, quest_type_enum: QuestType,
                                     category_enum: QuestCategory,
                                     difficulty_enum: QuestDifficulty,
                                     player_level: int) -> Optional[QuestTemplate]:
        """Pick the best matching enabled template for a context.

        Selection prefers an exact match on type, category, and difficulty,
        then relaxes difficulty, then category, then type. Returns None when
        no enabled template is available.
        """
        candidates = [
            t for t in self._templates.values()
            if t.enabled
            and t.quest_type == quest_type_enum.value
            and t.category == category_enum.value
            and t.difficulty == difficulty_enum.value
            and t.min_level <= player_level <= t.max_level
        ]
        if candidates:
            return candidates[0]
        # Relax difficulty.
        candidates = [
            t for t in self._templates.values()
            if t.enabled
            and t.quest_type == quest_type_enum.value
            and t.category == category_enum.value
            and t.min_level <= player_level <= t.max_level
        ]
        if candidates:
            return candidates[0]
        # Relax category.
        candidates = [
            t for t in self._templates.values()
            if t.enabled
            and t.quest_type == quest_type_enum.value
            and t.min_level <= player_level <= t.max_level
        ]
        if candidates:
            return candidates[0]
        # Relax type.
        candidates = [
            t for t in self._templates.values()
            if t.enabled
            and t.category == category_enum.value
            and t.min_level <= player_level <= t.max_level
        ]
        if candidates:
            return candidates[0]
        # Any enabled template within level range.
        candidates = [
            t for t in self._templates.values()
            if t.enabled and t.min_level <= player_level <= t.max_level
        ]
        if candidates:
            return candidates[0]
        return None

    def _instantiate_template(self, template: QuestTemplate,
                              player_level: int,
                              difficulty_enum: QuestDifficulty,
                              chain_id: str = "",
                              chain_index: int = -1,
                              player_id: str = "",
                              metadata: Optional[Dict[str, Any]] = None
                              ) -> QuestInstance:
        """Build a live QuestInstance from a template."""
        recommended = self._compute_recommended_level(
            player_level, difficulty_enum
        )
        rewards = self._scale_rewards(template.rewards, difficulty_enum)
        objectives = self._clone_objectives(template.objectives)
        requirements = self._clone_requirements(template.requirements)
        priority_enum = _coerce_enum(QuestPriority, template.priority,
                                     QuestPriority.NORMAL)
        quest_id = _new_id("quest")
        instance = QuestInstance(
            quest_id=quest_id,
            template_id=template.template_id,
            name=template.name,
            quest_type=template.quest_type,
            category=template.category,
            difficulty=difficulty_enum.value,
            description=template.description,
            priority=priority_enum.value,
            status=QuestStatus.AVAILABLE.value,
            player_id=player_id,
            player_level=max(1, _safe_int(player_level, 1)),
            recommended_level=recommended,
            time_limit=_safe_float(template.time_limit, 0.0),
            time_remaining=_safe_float(template.time_limit, 0.0),
            chain_id=chain_id,
            chain_index=chain_index,
            objectives=objectives,
            rewards=rewards,
            requirements=requirements,
            branch_ids=[],
            accepted_at="",
            completed_at="",
            expired_at="",
            failed_at="",
            fail_reason="",
            created_at=_now(),
            metadata=metadata or {"template_id": template.template_id},
        )
        return instance

    def _check_requirements(self, requirements: List[QuestRequirement],
                            player_profile: Optional[PlayerQuestProfile]) -> bool:
        """Verify that a player profile satisfies a list of requirements."""
        if not requirements:
            return True
        if player_profile is None:
            return False
        for req in requirements:
            if req.requirement_type == "level":
                if player_profile.level < _safe_int(req.value, 0):
                    return False
            elif req.requirement_type == "quest":
                if req.target not in player_profile.completed_quests:
                    return False
            elif req.requirement_type == "faction":
                if player_profile.faction != req.target:
                    return False
            elif req.requirement_type == "item":
                # Item checks are deferred to the inventory system. Treat as
                # satisfied so generation is not blocked by missing state.
                continue
        return True

    def _evaluate_flow_suggestions(self,
                                   profile: PlayerQuestProfile) -> List[str]:
        """Evaluate the flow suggestion rules against a player profile."""
        suggestions: List[str] = []
        completion_rate = _safe_float(profile.quest_completion_rate, 0.0)
        attempted = _safe_int(profile.total_quests_attempted, 0)
        completed = _safe_int(profile.total_quests_completed, 0)
        failed = len(profile.failed_quests)
        active = len(profile.active_quests)
        if attempted > 0 and completion_rate < 0.4:
            suggestions.append(_FLOW_SUGGESTION_RULES[0][1])
        if attempted > 4 and failed > 0 and (failed / max(1, attempted)) > 0.25:
            suggestions.append(_FLOW_SUGGESTION_RULES[1][1])
        if active > 8:
            suggestions.append(_FLOW_SUGGESTION_RULES[2][1])
        stalled_chains = [
            cid for cid, idx in profile.chain_progress.items()
            if idx >= 0 and idx < _MAX_QUESTS_PER_CHAIN
        ]
        if len(stalled_chains) > 3:
            suggestions.append(_FLOW_SUGGESTION_RULES[3][1])
        # Category monotony: examine the last preferred categories.
        if len(profile.preferred_categories) == 1:
            suggestions.append(_FLOW_SUGGESTION_RULES[5][1])
        if profile.preferred_difficulty == QuestDifficulty.TRIVIAL.value:
            suggestions.append(_FLOW_SUGGESTION_RULES[8][1])
        if not suggestions:
            suggestions.append(
                "Quest pacing is within healthy bounds. No urgent changes "
                "are needed at this time."
            )
        return suggestions

    # ------------------------------------------------------------------
    # Template Management
    # ------------------------------------------------------------------

    def register_template(self, template_id, name, quest_type,
                          category, difficulty, description,
                          priority="normal", min_level=1, max_level=99,
                          recommended_level=1, time_limit=0.0,
                          repeatable=False, objectives=None, rewards=None,
                          requirements=None, tags=None, enabled=True,
                          metadata=None) -> Tuple[bool, str, Optional[QuestTemplate]]:
        """Register a quest template in the generator library."""
        with self._lock:
            if not template_id:
                return False, "invalid_template_id", None
            if template_id in self._templates:
                return False, "template_exists", None
            if len(self._templates) >= self._config.max_templates:
                return False, "templates_capacity", None
            type_enum = _coerce_enum(QuestType, quest_type, QuestType.SIDE_QUEST)
            cat_enum = _coerce_enum(QuestCategory, category,
                                    QuestCategory.STORY)
            diff_enum = _coerce_enum(QuestDifficulty, difficulty,
                                     QuestDifficulty.NORMAL)
            pri_enum = _coerce_enum(QuestPriority, priority,
                                    QuestPriority.NORMAL)
            now = _now()
            template = QuestTemplate(
                template_id=template_id,
                name=name,
                quest_type=type_enum.value,
                category=cat_enum.value,
                difficulty=diff_enum.value,
                description=description or "",
                priority=pri_enum.value,
                min_level=max(1, _safe_int(min_level, 1)),
                max_level=max(1, _safe_int(max_level, 99)),
                recommended_level=max(1, _safe_int(recommended_level, 1)),
                time_limit=max(0.0, _safe_float(time_limit, 0.0)),
                repeatable=bool(repeatable),
                objectives=list(objectives) if objectives else [],
                rewards=list(rewards) if rewards else [],
                requirements=list(requirements) if requirements else [],
                tags=list(tags) if tags else [],
                enabled=bool(enabled),
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            self._templates[template_id] = template
            self._emit(
                QuestGenEventKind.QUEST_CREATED.value,
                description=f"Template '{name}' registered",
                data={"template_id": template_id,
                      "quest_type": type_enum.value,
                      "category": cat_enum.value,
                      "difficulty": diff_enum.value},
            )
            return True, "registered", template

    def get_template(self, template_id) -> Optional[QuestTemplate]:
        with self._lock:
            return self._templates.get(template_id)

    def list_templates(self, quest_type=None, category=None,
                       difficulty=None, enabled=None, limit=100) -> List[QuestTemplate]:
        with self._lock:
            items = list(self._templates.values())
            if quest_type is not None:
                type_enum = _coerce_enum(QuestType, quest_type)
                if type_enum is not None:
                    items = [t for t in items
                             if t.quest_type == type_enum.value]
                else:
                    items = [t for t in items
                             if t.quest_type == quest_type]
            if category is not None:
                cat_enum = _coerce_enum(QuestCategory, category)
                if cat_enum is not None:
                    items = [t for t in items
                             if t.category == cat_enum.value]
                else:
                    items = [t for t in items if t.category == category]
            if difficulty is not None:
                diff_enum = _coerce_enum(QuestDifficulty, difficulty)
                if diff_enum is not None:
                    items = [t for t in items
                             if t.difficulty == diff_enum.value]
                else:
                    items = [t for t in items if t.difficulty == difficulty]
            if enabled is not None:
                items = [t for t in items if t.enabled == bool(enabled)]
            if limit and limit > 0:
                items = items[:limit]
            return items

    def remove_template(self, template_id) -> Tuple[bool, str]:
        with self._lock:
            if template_id not in self._templates:
                return False, "not_found"
            del self._templates[template_id]
            self._emit(
                QuestGenEventKind.QUEST_REMOVED.value,
                description=f"Template '{template_id}' removed",
            )
            return True, "removed"

    def update_template(self, template_id, **kwargs) -> Tuple[bool, str, Optional[QuestTemplate]]:
        """Apply keyword updates to an existing quest template."""
        with self._lock:
            template = self._templates.get(template_id)
            if template is None:
                return False, "not_found", None
            if not kwargs:
                return False, "no_updates", template
            updatable = {
                "name", "description", "min_level", "max_level",
                "recommended_level", "time_limit", "repeatable", "enabled",
            }
            for key, value in kwargs.items():
                if key == "quest_type":
                    enum_val = _coerce_enum(QuestType, value, QuestType.SIDE_QUEST)
                    template.quest_type = enum_val.value
                elif key == "category":
                    enum_val = _coerce_enum(QuestCategory, value,
                                            QuestCategory.STORY)
                    template.category = enum_val.value
                elif key == "difficulty":
                    enum_val = _coerce_enum(QuestDifficulty, value,
                                            QuestDifficulty.NORMAL)
                    template.difficulty = enum_val.value
                elif key == "priority":
                    enum_val = _coerce_enum(QuestPriority, value,
                                            QuestPriority.NORMAL)
                    template.priority = enum_val.value
                elif key == "tags" and isinstance(value, list):
                    template.tags = list(value)
                elif key == "metadata" and isinstance(value, dict):
                    template.metadata.update(value)
                elif key == "objectives" and isinstance(value, list):
                    template.objectives = list(value)
                elif key == "rewards" and isinstance(value, list):
                    template.rewards = list(value)
                elif key == "requirements" and isinstance(value, list):
                    template.requirements = list(value)
                elif key in updatable:
                    if key in ("min_level", "max_level", "recommended_level"):
                        setattr(template, key,
                                max(1, _safe_int(value,
                                        getattr(template, key))))
                    elif key == "time_limit":
                        setattr(template, key,
                                max(0.0, _safe_float(value,
                                        getattr(template, key))))
                    elif key in ("repeatable", "enabled"):
                        setattr(template, key, bool(value))
                    else:
                        setattr(template, key, value)
            template.updated_at = _now()
            self._emit(
                QuestGenEventKind.QUEST_CREATED.value,
                description=f"Template '{template_id}' updated",
                data={"keys": list(kwargs.keys())},
            )
            return True, "updated", template

    # ------------------------------------------------------------------
    # Quest Generation
    # ------------------------------------------------------------------

    def generate_quest(self, player_level, quest_type="side_quest",
                       difficulty="normal", context="", name="",
                       description="", priority="", chain_id="",
                       chain_index=-1, player_id="",
                       metadata=None) -> Tuple[bool, str, Optional[QuestInstance]]:
        """Generate a quest instance directly from parameters."""
        with self._lock:
            if len(self._quests) >= self._config.max_quests:
                return False, "quests_capacity", None
            type_enum = _coerce_enum(QuestType, quest_type,
                                     QuestType.SIDE_QUEST)
            diff_enum = _coerce_enum(QuestDifficulty, difficulty,
                                     QuestDifficulty.NORMAL)
            cat_enum = QuestCategory.STORY
            # Infer a category from the type when possible.
            if type_enum in (QuestType.BOUNTY, QuestType.DEFENSE,
                             QuestType.RESCUE):
                cat_enum = QuestCategory.COMBAT
            elif type_enum in (QuestType.INVESTIGATION, QuestType.RETRIEVAL,
                               QuestType.HIDDEN):
                cat_enum = QuestCategory.EXPLORATION
            elif type_enum in (QuestType.DELIVERY, QuestType.ESCORT):
                cat_enum = QuestCategory.SOCIAL
            elif type_enum in (QuestType.COLLECTION,):
                cat_enum = QuestCategory.COLLECTION
            elif type_enum in (QuestType.DAILY, QuestType.WEEKLY):
                cat_enum = QuestCategory.REPEATABLE
            elif type_enum in (QuestType.EVENT,):
                cat_enum = QuestCategory.EVENT
            elif type_enum in (QuestType.MAIN_STORY,):
                cat_enum = QuestCategory.STORY

            level = max(1, _safe_int(player_level, 1))
            recommended = self._compute_recommended_level(level, diff_enum)
            priority_value = self._resolve_priority(priority, type_enum)

            quest_name = name or self._build_quest_name(
                _QUEST_NAME_VERBS[hash(context) % len(_QUEST_NAME_VERBS)]
                if context else "Seek",
                _QUEST_NAME_SUBJECTS[hash(quest_type) % len(_QUEST_NAME_SUBJECTS)]
                if quest_type else "the Unknown",
            )
            quest_desc = description or self._build_quest_description(
                type_enum, context or "the region"
            )

            # Build default objectives from the category map.
            obj_types = _CATEGORY_OBJECTIVE_MAP.get(cat_enum,
                                                    [ObjectiveType.REACH_LOCATION])
            objectives: List[QuestObjective] = []
            for idx, ot in enumerate(obj_types[:3]):
                objectives.append(QuestObjective(
                    objective_id=_new_id("obj"),
                    objective_type=ot.value,
                    target=context or "the target",
                    count=1,
                    current=0,
                    status=ObjectiveStatus.PENDING.value,
                    description=f"{ot.value.replace('_', ' ').title()} "
                                f"at {context or 'the location'}.",
                    optional=False,
                    order=idx,
                ))

            # Build default rewards scaled by difficulty.
            base_rewards = [
                QuestReward(
                    reward_id=_new_id("rew"),
                    reward_type=RewardType.EXPERIENCE.value,
                    amount=100,
                ),
                QuestReward(
                    reward_id=_new_id("rew"),
                    reward_type=RewardType.GOLD.value,
                    amount=50,
                ),
            ]
            rewards = self._scale_rewards(base_rewards, diff_enum)

            quest_id = _new_id("quest")
            instance = QuestInstance(
                quest_id=quest_id,
                template_id="",
                name=quest_name,
                quest_type=type_enum.value,
                category=cat_enum.value,
                difficulty=diff_enum.value,
                description=quest_desc,
                priority=priority_value,
                status=QuestStatus.AVAILABLE.value,
                player_id=player_id,
                player_level=level,
                recommended_level=recommended,
                time_limit=0.0,
                time_remaining=0.0,
                chain_id=chain_id,
                chain_index=chain_index,
                objectives=objectives,
                rewards=rewards,
                requirements=[],
                branch_ids=[],
                accepted_at="",
                completed_at="",
                expired_at="",
                failed_at="",
                fail_reason="",
                created_at=_now(),
                metadata=metadata or {"generated": True,
                                      "context": context},
            )
            self._quests[quest_id] = instance
            self._generate_counter += 1
            self._emit(
                QuestGenEventKind.QUEST_CREATED.value,
                quest_id=quest_id,
                description=f"Quest '{quest_name}' generated",
                data={"quest_id": quest_id,
                      "quest_type": type_enum.value,
                      "difficulty": diff_enum.value,
                      "player_level": level,
                      "context": context},
            )
            return True, "generated", instance

    def generate_from_template(self, template_id, player_level,
                               difficulty="", player_id="",
                               chain_id="", chain_index=-1,
                               metadata=None) -> Tuple[bool, str, Optional[QuestInstance]]:
        """Generate a quest instance from a registered template."""
        with self._lock:
            template = self._templates.get(template_id)
            if template is None:
                return False, "template_not_found", None
            if not template.enabled:
                return False, "template_disabled", None
            if len(self._quests) >= self._config.max_quests:
                return False, "quests_capacity", None
            level = max(1, _safe_int(player_level, 1))
            if level < template.min_level or level > template.max_level:
                return False, "level_out_of_range", None
            diff_enum = _coerce_enum(QuestDifficulty, difficulty or
                                     template.difficulty,
                                     QuestDifficulty.NORMAL)
            instance = self._instantiate_template(
                template=template,
                player_level=level,
                difficulty_enum=diff_enum,
                chain_id=chain_id,
                chain_index=chain_index,
                player_id=player_id,
                metadata=metadata or {"template_id": template_id,
                                      "generated_from_template": True},
            )
            self._quests[instance.quest_id] = instance
            self._generate_counter += 1
            self._emit(
                QuestGenEventKind.QUEST_CREATED.value,
                quest_id=instance.quest_id,
                description=f"Quest '{instance.name}' generated from template",
                data={"quest_id": instance.quest_id,
                      "template_id": template_id,
                      "difficulty": diff_enum.value,
                      "player_level": level},
            )
            return True, "generated", instance

    def generate_chain(self, theme, quest_count, player_level,
                       difficulty="", metadata=None) -> Tuple[bool, str, Optional[QuestChain]]:
        """Generate a chain of linked quests from a theme."""
        with self._lock:
            if not self._config.enable_chains:
                return False, "chains_disabled", None
            if len(self._chains) >= self._config.max_chains:
                return False, "chains_capacity", None
            count = _safe_int(quest_count, 1)
            if count <= 0:
                return False, "invalid_quest_count", None
            if count > self._config.max_quests_per_chain:
                count = self._config.max_quests_per_chain
            level = max(1, _safe_int(player_level, 1))
            type_enum, cat_enum, diff_enum = self._theme_to_quest_spec(theme)
            if difficulty:
                overridden = _coerce_enum(QuestDifficulty, difficulty)
                if overridden is not None:
                    diff_enum = overridden
            chain_id = _new_id("chain")
            quest_ids: List[str] = []
            template_ids: List[str] = []
            for idx in range(count):
                # Try to find a template for each step; fall back to direct
                # generation when no template matches.
                template = self._select_template_for_context(
                    type_enum, cat_enum, diff_enum, level
                )
                if template is not None:
                    instance = self._instantiate_template(
                        template=template,
                        player_level=level,
                        difficulty_enum=diff_enum,
                        chain_id=chain_id,
                        chain_index=idx,
                        metadata={"chain_id": chain_id,
                                  "chain_index": idx,
                                  "theme": theme},
                    )
                    template_ids.append(template.template_id)
                else:
                    verb = _QUEST_NAME_VERBS[idx % len(_QUEST_NAME_VERBS)]
                    subject = _QUEST_NAME_SUBJECTS[
                        (idx + hash(theme)) % len(_QUEST_NAME_SUBJECTS)
                    ]
                    qualifier = _QUEST_NAME_QUALIFIERS[
                        idx % len(_QUEST_NAME_QUALIFIERS)
                    ]
                    quest_name = self._build_quest_name(verb, subject, qualifier)
                    quest_desc = self._build_quest_description(type_enum, subject)
                    obj_types = _CATEGORY_OBJECTIVE_MAP.get(
                        cat_enum, [ObjectiveType.REACH_LOCATION]
                    )
                    objectives = []
                    for o_idx, ot in enumerate(obj_types[:2]):
                        objectives.append(QuestObjective(
                            objective_id=_new_id("obj"),
                            objective_type=ot.value,
                            target=subject,
                            count=1 + idx,
                            current=0,
                            status=ObjectiveStatus.PENDING.value,
                            description=f"Step {idx + 1}: {ot.value.replace('_', ' ').title()}.",
                            optional=False,
                            order=o_idx,
                        ))
                    base_rewards = [
                        QuestReward(
                            reward_id=_new_id("rew"),
                            reward_type=RewardType.EXPERIENCE.value,
                            amount=100 * (idx + 1),
                        ),
                    ]
                    rewards = self._scale_rewards(base_rewards, diff_enum)
                    instance = QuestInstance(
                        quest_id=_new_id("quest"),
                        template_id="",
                        name=quest_name,
                        quest_type=type_enum.value,
                        category=cat_enum.value,
                        difficulty=diff_enum.value,
                        description=quest_desc,
                        priority=self._resolve_priority("", type_enum),
                        status=QuestStatus.LOCKED.value if idx > 0
                        else QuestStatus.AVAILABLE.value,
                        player_id="",
                        player_level=level,
                        recommended_level=self._compute_recommended_level(
                            level, diff_enum),
                        time_limit=0.0,
                        time_remaining=0.0,
                        chain_id=chain_id,
                        chain_index=idx,
                        objectives=objectives,
                        rewards=rewards,
                        requirements=[],
                        branch_ids=[],
                        created_at=_now(),
                        metadata={"chain_id": chain_id,
                                  "chain_index": idx,
                                  "theme": theme,
                                  "generated": True},
                    )
                self._quests[instance.quest_id] = instance
                self._generate_counter += 1
                quest_ids.append(instance.quest_id)
            chain = QuestChain(
                chain_id=chain_id,
                name=f"{theme.title()} Chain",
                theme=theme or "untold",
                description=f"A {count}-quest chain themed around {theme}.",
                quest_ids=quest_ids,
                template_ids=template_ids,
                current_index=0,
                total_quests=count,
                completed_quests=0,
                status=QuestStatus.AVAILABLE.value,
                created_at=_now(),
                metadata=metadata or {"theme": theme,
                                      "difficulty": diff_enum.value},
            )
            self._chains[chain_id] = chain
            self._emit(
                QuestGenEventKind.CHAIN_GENERATED.value,
                description=f"Chain '{chain.name}' generated",
                data={"chain_id": chain_id,
                      "theme": theme,
                      "quest_count": count,
                      "difficulty": diff_enum.value},
            )
            return True, "chain_generated", chain

    def auto_generate_quest(self, player_profile, world_context) -> Tuple[bool, str, Optional[QuestInstance]]:
        """AI-generate a personalized quest from a player profile and world.

        Uses the player's preferred categories and difficulty to select a
        matching template, then instantiates it with a difficulty scaled to
        the player's skill ratings. Falls back to direct generation when no
        template matches.
        """
        with self._lock:
            if player_profile is None:
                return False, "invalid_profile", None
            if not isinstance(player_profile, PlayerQuestProfile):
                return False, "invalid_profile_type", None
            if len(self._quests) >= self._config.max_quests:
                return False, "quests_capacity", None
            level = max(1, player_profile.level)
            # Pick a difficulty from the player's preference, scaled by
            # completion rate.
            base_diff = _coerce_enum(QuestDifficulty,
                                     player_profile.preferred_difficulty,
                                     QuestDifficulty.NORMAL)
            completion = _clamp(_safe_float(
                player_profile.quest_completion_rate, 0.5), 0.0, 1.0)
            if completion > 0.8 and base_diff.value not in (
                    QuestDifficulty.EXTREME.value,
                    QuestDifficulty.LEGENDARY.value):
                # Bump up one tier for high-performing players.
                order = list(QuestDifficulty)
                idx = order.index(base_diff)
                base_diff = order[min(idx + 1, len(order) - 1)]
            elif completion < 0.3 and base_diff.value not in (
                    QuestDifficulty.TRIVIAL.value,
                    QuestDifficulty.EASY.value):
                order = list(QuestDifficulty)
                idx = order.index(base_diff)
                base_diff = order[max(idx - 1, 0)]
            # Pick a category from preferences or from world context.
            category_enum = QuestCategory.STORY
            if player_profile.preferred_categories:
                pref = player_profile.preferred_categories[0]
                cat = _coerce_enum(QuestCategory, pref)
                if cat is not None:
                    category_enum = cat
            # Infer a quest type from world context keywords.
            type_enum, ctx_cat, ctx_diff = self._theme_to_quest_spec(
                world_context or ""
            )
            if ctx_cat is not None:
                category_enum = ctx_cat
            # Try to find a matching template.
            template = self._select_template_for_context(
                type_enum, category_enum, base_diff, level
            )
            if template is not None:
                instance = self._instantiate_template(
                    template=template,
                    player_level=level,
                    difficulty_enum=base_diff,
                    player_id=player_profile.player_id,
                    metadata={"auto_generated": True,
                              "world_context": world_context,
                              "player_id": player_profile.player_id},
                )
            else:
                verb = _QUEST_NAME_VERBS[
                    hash(world_context) % len(_QUEST_NAME_VERBS)
                ] if world_context else "Seek"
                subject = _QUEST_NAME_SUBJECTS[
                    hash(player_profile.player_id) % len(_QUEST_NAME_SUBJECTS)
                ]
                quest_name = self._build_quest_name(verb, subject)
                quest_desc = self._build_quest_description(
                    type_enum, world_context or "the region"
                )
                obj_types = _CATEGORY_OBJECTIVE_MAP.get(
                    category_enum, [ObjectiveType.REACH_LOCATION]
                )
                objectives = []
                for o_idx, ot in enumerate(obj_types[:3]):
                    objectives.append(QuestObjective(
                        objective_id=_new_id("obj"),
                        objective_type=ot.value,
                        target=world_context or "the target",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description=f"Auto: {ot.value.replace('_', ' ').title()}.",
                        optional=False,
                        order=o_idx,
                    ))
                base_rewards = [
                    QuestReward(
                        reward_id=_new_id("rew"),
                        reward_type=RewardType.EXPERIENCE.value,
                        amount=120,
                    ),
                    QuestReward(
                        reward_id=_new_id("rew"),
                        reward_type=RewardType.GOLD.value,
                        amount=60,
                    ),
                ]
                rewards = self._scale_rewards(base_rewards, base_diff)
                instance = QuestInstance(
                    quest_id=_new_id("quest"),
                    template_id="",
                    name=quest_name,
                    quest_type=type_enum.value,
                    category=category_enum.value,
                    difficulty=base_diff.value,
                    description=quest_desc,
                    priority=self._resolve_priority("", type_enum),
                    status=QuestStatus.AVAILABLE.value,
                    player_id=player_profile.player_id,
                    player_level=level,
                    recommended_level=self._compute_recommended_level(
                        level, base_diff),
                    time_limit=0.0,
                    time_remaining=0.0,
                    chain_id="",
                    chain_index=-1,
                    objectives=objectives,
                    rewards=rewards,
                    requirements=[],
                    branch_ids=[],
                    created_at=_now(),
                    metadata={"auto_generated": True,
                              "world_context": world_context},
                )
            self._quests[instance.quest_id] = instance
            self._generate_counter += 1
            self._auto_generate_counter += 1
            self._emit(
                QuestGenEventKind.QUEST_CREATED.value,
                quest_id=instance.quest_id,
                description=f"Auto-generated quest '{instance.name}'",
                data={"quest_id": instance.quest_id,
                      "player_id": player_profile.player_id,
                      "difficulty": base_diff.value,
                      "world_context": world_context},
            )
            return True, "auto_generated", instance

    def auto_generate_chain(self, player_profile, theme, length) -> Tuple[bool, str, Optional[QuestChain]]:
        """AI-generate a quest chain tailored to a player profile."""
        with self._lock:
            if player_profile is None:
                return False, "invalid_profile", None
            if not isinstance(player_profile, PlayerQuestProfile):
                return False, "invalid_profile_type", None
            if not self._config.enable_chains:
                return False, "chains_disabled", None
            if len(self._chains) >= self._config.max_chains:
                return False, "chains_capacity", None
            count = _safe_int(length, 3)
            if count <= 0:
                count = 3
            if count > self._config.max_quests_per_chain:
                count = self._config.max_quests_per_chain
            level = max(1, player_profile.level)
            type_enum, cat_enum, diff_enum = self._theme_to_quest_spec(
                theme or ""
            )
            # Honor player's preferred difficulty when lower than the theme
            # default, so chains do not overwhelm the player.
            pref_diff = _coerce_enum(QuestDifficulty,
                                     player_profile.preferred_difficulty)
            if pref_diff is not None:
                order = list(QuestDifficulty)
                theme_idx = order.index(diff_enum)
                pref_idx = order.index(pref_diff)
                # Use the lower of the two to respect player comfort.
                diff_enum = order[min(theme_idx, pref_idx)]
            chain_id = _new_id("chain")
            quest_ids: List[str] = []
            template_ids: List[str] = []
            for idx in range(count):
                template = self._select_template_for_context(
                    type_enum, cat_enum, diff_enum, level
                )
                if template is not None:
                    instance = self._instantiate_template(
                        template=template,
                        player_level=level,
                        difficulty_enum=diff_enum,
                        chain_id=chain_id,
                        chain_index=idx,
                        player_id=player_profile.player_id,
                        metadata={"auto_generated": True,
                                  "chain_id": chain_id,
                                  "chain_index": idx,
                                  "theme": theme},
                    )
                    template_ids.append(template.template_id)
                else:
                    verb = _QUEST_NAME_VERBS[idx % len(_QUEST_NAME_VERBS)]
                    subject = _QUEST_NAME_SUBJECTS[
                        (idx + hash(theme)) % len(_QUEST_NAME_SUBJECTS)
                    ]
                    quest_name = self._build_quest_name(
                        verb, subject,
                        _QUEST_NAME_QUALIFIERS[idx % len(_QUEST_NAME_QUALIFIERS)]
                    )
                    quest_desc = self._build_quest_description(type_enum, subject)
                    obj_types = _CATEGORY_OBJECTIVE_MAP.get(
                        cat_enum, [ObjectiveType.REACH_LOCATION]
                    )
                    objectives = []
                    for o_idx, ot in enumerate(obj_types[:2]):
                        objectives.append(QuestObjective(
                            objective_id=_new_id("obj"),
                            objective_type=ot.value,
                            target=subject,
                            count=1 + idx,
                            current=0,
                            status=ObjectiveStatus.PENDING.value,
                            description=f"Chain step {idx + 1}.",
                            optional=False,
                            order=o_idx,
                        ))
                    rewards = self._scale_rewards(
                        [QuestReward(
                            reward_id=_new_id("rew"),
                            reward_type=RewardType.EXPERIENCE.value,
                            amount=120 * (idx + 1),
                        )],
                        diff_enum,
                    )
                    instance = QuestInstance(
                        quest_id=_new_id("quest"),
                        template_id="",
                        name=quest_name,
                        quest_type=type_enum.value,
                        category=cat_enum.value,
                        difficulty=diff_enum.value,
                        description=quest_desc,
                        priority=self._resolve_priority("", type_enum),
                        status=QuestStatus.LOCKED.value if idx > 0
                        else QuestStatus.AVAILABLE.value,
                        player_id=player_profile.player_id,
                        player_level=level,
                        recommended_level=self._compute_recommended_level(
                            level, diff_enum),
                        time_limit=0.0,
                        time_remaining=0.0,
                        chain_id=chain_id,
                        chain_index=idx,
                        objectives=objectives,
                        rewards=rewards,
                        requirements=[],
                        branch_ids=[],
                        created_at=_now(),
                        metadata={"auto_generated": True,
                                  "chain_id": chain_id,
                                  "chain_index": idx,
                                  "theme": theme},
                    )
                self._quests[instance.quest_id] = instance
                self._generate_counter += 1
                self._auto_generate_counter += 1
                quest_ids.append(instance.quest_id)
            chain = QuestChain(
                chain_id=chain_id,
                name=f"{(theme or 'Untold').title()} Saga",
                theme=theme or "untold",
                description=f"An auto-generated {count}-quest chain for "
                            f"{player_profile.name}.",
                quest_ids=quest_ids,
                template_ids=template_ids,
                current_index=0,
                total_quests=count,
                completed_quests=0,
                status=QuestStatus.AVAILABLE.value,
                created_at=_now(),
                metadata={"auto_generated": True,
                          "player_id": player_profile.player_id,
                          "theme": theme,
                          "difficulty": diff_enum.value},
            )
            self._chains[chain_id] = chain
            self._emit(
                QuestGenEventKind.CHAIN_GENERATED.value,
                description=f"Auto-generated chain '{chain.name}'",
                data={"chain_id": chain_id,
                      "player_id": player_profile.player_id,
                      "theme": theme,
                      "quest_count": count},
            )
            return True, "auto_generated", chain

    # ------------------------------------------------------------------
    # Quest Instance Lifecycle
    # ------------------------------------------------------------------

    def get_quest(self, quest_id) -> Optional[QuestInstance]:
        with self._lock:
            return self._quests.get(quest_id)

    def list_quests(self, quest_type=None, category=None, difficulty=None,
                    status=None, player_id=None, chain_id=None,
                    limit=100) -> List[QuestInstance]:
        with self._lock:
            items = list(self._quests.values())
            if quest_type is not None:
                type_enum = _coerce_enum(QuestType, quest_type)
                if type_enum is not None:
                    items = [q for q in items
                             if q.quest_type == type_enum.value]
                else:
                    items = [q for q in items
                             if q.quest_type == quest_type]
            if category is not None:
                cat_enum = _coerce_enum(QuestCategory, category)
                if cat_enum is not None:
                    items = [q for q in items
                             if q.category == cat_enum.value]
                else:
                    items = [q for q in items if q.category == category]
            if difficulty is not None:
                diff_enum = _coerce_enum(QuestDifficulty, difficulty)
                if diff_enum is not None:
                    items = [q for q in items
                             if q.difficulty == diff_enum.value]
                else:
                    items = [q for q in items if q.difficulty == difficulty]
            if status is not None:
                status_enum = _coerce_enum(QuestStatus, status)
                if status_enum is not None:
                    items = [q for q in items
                             if q.status == status_enum.value]
                else:
                    items = [q for q in items if q.status == status]
            if player_id is not None:
                items = [q for q in items if q.player_id == player_id]
            if chain_id is not None:
                items = [q for q in items if q.chain_id == chain_id]
            if limit and limit > 0:
                items = items[-limit:]
            return items

    def remove_quest(self, quest_id) -> Tuple[bool, str]:
        with self._lock:
            if quest_id not in self._quests:
                return False, "not_found"
            del self._quests[quest_id]
            # Detach the quest from any chain that held it.
            for chain in self._chains.values():
                if quest_id in chain.quest_ids:
                    chain.quest_ids.remove(quest_id)
                    chain.total_quests = len(chain.quest_ids)
            self._emit(
                QuestGenEventKind.QUEST_REMOVED.value,
                quest_id=quest_id,
                description=f"Quest '{quest_id}' removed",
            )
            return True, "removed"

    def accept_quest(self, quest_id, player_id) -> Tuple[bool, str, Optional[QuestInstance]]:
        """Accept an available quest on behalf of a player."""
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return False, "not_found", None
            if quest.status not in (QuestStatus.AVAILABLE.value,
                                    QuestStatus.LOCKED.value):
                return False, "not_available", quest
            # Check requirements against the player profile if present.
            profile = self._player_profiles.get(player_id)
            if profile is not None and quest.requirements:
                if not self._check_requirements(quest.requirements, profile):
                    return False, "requirements_not_met", quest
            # Enforce per-player active quest cap.
            if profile is not None:
                active = [
                    q for q in self._quests.values()
                    if q.player_id == player_id
                    and q.status == QuestStatus.ACTIVE.value
                ]
                if len(active) >= self._config.max_quests_per_player:
                    return False, "player_quest_cap", quest
            quest.status = QuestStatus.ACTIVE.value
            quest.player_id = player_id
            quest.accepted_at = _now()
            if profile is not None:
                if quest_id not in profile.active_quests:
                    profile.active_quests.append(quest_id)
                profile.total_quests_attempted += 1
                profile.updated_at = _now()
                # Recompute completion rate.
                attempted = max(1, profile.total_quests_attempted)
                profile.quest_completion_rate = round(
                    profile.total_quests_completed / attempted, 4
                )
            self._emit(
                QuestGenEventKind.QUEST_ACCEPTED.value,
                quest_id=quest_id,
                description=f"Quest '{quest.name}' accepted by {player_id}",
                data={"quest_id": quest_id,
                      "player_id": player_id},
            )
            return True, "accepted", quest

    def complete_quest(self, quest_id) -> Tuple[bool, str, Optional[QuestInstance]]:
        """Mark an active quest as completed and grant rewards."""
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return False, "not_found", None
            if quest.status != QuestStatus.ACTIVE.value:
                return False, "not_active", quest
            # Verify all non-optional objectives are completed.
            blocking = [
                o for o in quest.objectives
                if not o.optional and o.status != ObjectiveStatus.COMPLETED.value
            ]
            if blocking:
                return False, "objectives_incomplete", quest
            quest.status = QuestStatus.COMPLETED.value
            quest.completed_at = _now()
            self._complete_counter += 1
            # Update the player profile.
            profile = self._player_profiles.get(quest.player_id) if quest.player_id else None
            if profile is not None:
                if quest_id in profile.active_quests:
                    profile.active_quests.remove(quest_id)
                if quest_id not in profile.completed_quests:
                    profile.completed_quests.append(quest_id)
                profile.total_quests_completed += 1
                attempted = max(1, profile.total_quests_attempted)
                profile.quest_completion_rate = round(
                    profile.total_quests_completed / attempted, 4
                )
                profile.updated_at = _now()
            # Advance the chain if this quest belonged to one.
            if quest.chain_id:
                chain = self._chains.get(quest.chain_id)
                if chain is not None:
                    chain.completed_quests += 1
                    if chain.current_index < chain.total_quests - 1:
                        chain.current_index += 1
                        # Unlock the next quest in the chain.
                        if chain.current_index < len(chain.quest_ids):
                            next_id = chain.quest_ids[chain.current_index]
                            next_quest = self._quests.get(next_id)
                            if next_quest is not None and \
                                    next_quest.status == QuestStatus.LOCKED.value:
                                next_quest.status = QuestStatus.AVAILABLE.value
                    else:
                        chain.status = QuestStatus.COMPLETED.value
                    if profile is not None:
                        profile.chain_progress[quest.chain_id] = chain.current_index
            self._emit(
                QuestGenEventKind.QUEST_COMPLETED.value,
                quest_id=quest_id,
                description=f"Quest '{quest.name}' completed",
                data={"quest_id": quest_id,
                      "player_id": quest.player_id,
                      "rewards": len(quest.rewards)},
            )
            return True, "completed", quest

    def fail_quest(self, quest_id, reason="") -> Tuple[bool, str]:
        """Mark an active quest as failed."""
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return False, "not_found"
            if quest.status not in (QuestStatus.ACTIVE.value,
                                    QuestStatus.AVAILABLE.value):
                return False, "not_active"
            quest.status = QuestStatus.FAILED.value
            quest.failed_at = _now()
            quest.fail_reason = reason or "unspecified"
            self._fail_counter += 1
            profile = self._player_profiles.get(quest.player_id) if quest.player_id else None
            if profile is not None:
                if quest_id in profile.active_quests:
                    profile.active_quests.remove(quest_id)
                if quest_id not in profile.failed_quests:
                    profile.failed_quests.append(quest_id)
                attempted = max(1, profile.total_quests_attempted)
                profile.quest_completion_rate = round(
                    profile.total_quests_completed / attempted, 4
                )
                profile.updated_at = _now()
            self._emit(
                QuestGenEventKind.QUEST_FAILED.value,
                quest_id=quest_id,
                description=f"Quest '{quest.name}' failed: {quest.fail_reason}",
                data={"quest_id": quest_id,
                      "reason": quest.fail_reason,
                      "player_id": quest.player_id},
            )
            return True, "failed"

    def expire_quest(self, quest_id) -> Tuple[bool, str]:
        """Mark a quest as expired due to time running out."""
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return False, "not_found"
            if quest.status not in (QuestStatus.ACTIVE.value,
                                    QuestStatus.AVAILABLE.value):
                return False, "not_expirable"
            quest.status = QuestStatus.EXPIRED.value
            quest.expired_at = _now()
            self._expire_counter += 1
            profile = self._player_profiles.get(quest.player_id) if quest.player_id else None
            if profile is not None:
                if quest_id in profile.active_quests:
                    profile.active_quests.remove(quest_id)
                profile.updated_at = _now()
            self._emit(
                QuestGenEventKind.QUEST_FAILED.value,
                quest_id=quest_id,
                description=f"Quest '{quest.name}' expired",
                data={"quest_id": quest_id,
                      "player_id": quest.player_id},
            )
            return True, "expired"

    def abandon_quest(self, quest_id) -> Tuple[bool, str]:
        """Let a player abandon an active quest without failing it."""
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return False, "not_found"
            if quest.status != QuestStatus.ACTIVE.value:
                return False, "not_active"
            profile = self._player_profiles.get(quest.player_id) if quest.player_id else None
            if profile is not None:
                if quest_id in profile.active_quests:
                    profile.active_quests.remove(quest_id)
                if quest_id not in profile.abandoned_quests:
                    profile.abandoned_quests.append(quest_id)
                profile.updated_at = _now()
            quest.status = QuestStatus.AVAILABLE.value
            quest.player_id = ""
            quest.accepted_at = ""
            self._emit(
                QuestGenEventKind.QUEST_REMOVED.value,
                quest_id=quest_id,
                description=f"Quest '{quest.name}' abandoned",
                data={"quest_id": quest_id},
            )
            return True, "abandoned"

    # ------------------------------------------------------------------
    # Objective Management
    # ------------------------------------------------------------------

    def update_objective(self, quest_id, objective_id, progress=0,
                         status="") -> Tuple[bool, str, Optional[QuestObjective]]:
        """Update an objective's progress and status within a quest."""
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return False, "quest_not_found", None
            target_obj: Optional[QuestObjective] = None
            for obj in quest.objectives:
                if obj.objective_id == objective_id:
                    target_obj = obj
                    break
            if target_obj is None:
                return False, "objective_not_found", None
            if quest.status != QuestStatus.ACTIVE.value:
                return False, "quest_not_active", target_obj
            progress_val = _safe_int(progress, 0)
            if progress_val != 0:
                target_obj.current = max(0, target_obj.current + progress_val)
                if target_obj.current > target_obj.count:
                    target_obj.current = target_obj.count
                if target_obj.current >= target_obj.count:
                    if target_obj.status != ObjectiveStatus.COMPLETED.value:
                        target_obj.status = ObjectiveStatus.COMPLETED.value
                else:
                    if target_obj.status == ObjectiveStatus.PENDING.value:
                        target_obj.status = ObjectiveStatus.IN_PROGRESS.value
            if status:
                status_enum = _coerce_enum(ObjectiveStatus, status)
                if status_enum is not None:
                    target_obj.status = status_enum.value
            self._emit(
                QuestGenEventKind.OBJECTIVE_UPDATED.value,
                quest_id=quest_id,
                description=f"Objective '{objective_id}' updated",
                data={"quest_id": quest_id,
                      "objective_id": objective_id,
                      "progress": progress_val,
                      "current": target_obj.current,
                      "count": target_obj.count,
                      "status": target_obj.status},
            )
            return True, "updated", target_obj

    def get_objective(self, quest_id, objective_id) -> Optional[QuestObjective]:
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return None
            for obj in quest.objectives:
                if obj.objective_id == objective_id:
                    return obj
            return None

    def list_objectives(self, quest_id) -> List[QuestObjective]:
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return []
            return list(quest.objectives)

    # ------------------------------------------------------------------
    # Chain Management
    # ------------------------------------------------------------------

    def get_chain(self, chain_id) -> Optional[QuestChain]:
        with self._lock:
            return self._chains.get(chain_id)

    def list_chains(self, theme=None, status=None,
                    limit=100) -> List[QuestChain]:
        with self._lock:
            items = list(self._chains.values())
            if theme is not None:
                items = [c for c in items if c.theme == theme]
            if status is not None:
                status_enum = _coerce_enum(QuestStatus, status)
                if status_enum is not None:
                    items = [c for c in items if c.status == status_enum.value]
                else:
                    items = [c for c in items if c.status == status]
            if limit and limit > 0:
                items = items[-limit:]
            return items

    def advance_chain(self, chain_id, player_id) -> Tuple[bool, str, Optional[QuestInstance]]:
        """Generate or unlock the next quest in a chain."""
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return False, "chain_not_found", None
            if chain.status == QuestStatus.COMPLETED.value:
                return False, "chain_completed", None
            if chain.current_index >= chain.total_quests:
                return False, "chain_exhausted", None
            if chain.current_index >= len(chain.quest_ids):
                return False, "chain_index_out_of_range", None
            next_quest_id = chain.quest_ids[chain.current_index]
            next_quest = self._quests.get(next_quest_id)
            if next_quest is None:
                return False, "quest_not_found", None
            if next_quest.status == QuestStatus.LOCKED.value:
                next_quest.status = QuestStatus.AVAILABLE.value
            if next_quest.status == QuestStatus.AVAILABLE.value:
                next_quest.player_id = player_id
                next_quest.status = QuestStatus.ACTIVE.value
                next_quest.accepted_at = _now()
                profile = self._player_profiles.get(player_id)
                if profile is not None:
                    if next_quest_id not in profile.active_quests:
                        profile.active_quests.append(next_quest_id)
                    profile.total_quests_attempted += 1
                    profile.chain_progress[chain_id] = chain.current_index
                    profile.updated_at = _now()
            self._emit(
                QuestGenEventKind.CHAIN_GENERATED.value,
                quest_id=next_quest_id,
                description=f"Chain '{chain.name}' advanced to step "
                            f"{chain.current_index + 1}",
                data={"chain_id": chain_id,
                      "quest_id": next_quest_id,
                      "player_id": player_id,
                      "step": chain.current_index + 1},
            )
            return True, "advanced", next_quest

    def remove_chain(self, chain_id) -> Tuple[bool, str]:
        with self._lock:
            if chain_id not in self._chains:
                return False, "not_found"
            chain = self._chains[chain_id]
            # Remove all quests that belonged only to this chain.
            for quest_id in list(chain.quest_ids):
                quest = self._quests.get(quest_id)
                if quest is not None and quest.chain_id == chain_id:
                    if quest.status not in (QuestStatus.ACTIVE.value,
                                            QuestStatus.COMPLETED.value):
                        del self._quests[quest_id]
            del self._chains[chain_id]
            self._emit(
                QuestGenEventKind.QUEST_REMOVED.value,
                description=f"Chain '{chain_id}' removed",
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Player Profile Management
    # ------------------------------------------------------------------

    def register_player_profile(self, player_id, name, level=1,
                                faction="", preferred_categories=None,
                                preferred_difficulty="normal",
                                metadata=None) -> Tuple[bool, str, Optional[PlayerQuestProfile]]:
        """Register a player quest profile."""
        with self._lock:
            if not player_id:
                return False, "invalid_player_id", None
            if player_id in self._player_profiles:
                return False, "profile_exists", None
            if len(self._player_profiles) >= self._config.max_player_profiles:
                return False, "profiles_capacity", None
            diff_enum = _coerce_enum(QuestDifficulty, preferred_difficulty,
                                     QuestDifficulty.NORMAL)
            now = _now()
            profile = PlayerQuestProfile(
                player_id=player_id,
                name=name,
                level=max(1, _safe_int(level, 1)),
                faction=faction or "",
                active_quests=[],
                completed_quests=[],
                failed_quests=[],
                abandoned_quests=[],
                preferred_categories=list(preferred_categories)
                if preferred_categories else [],
                preferred_difficulty=diff_enum.value,
                quest_completion_rate=0.0,
                total_quests_attempted=0,
                total_quests_completed=0,
                chain_progress={},
                skill_ratings={},
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            self._player_profiles[player_id] = profile
            self._emit(
                QuestGenEventKind.QUEST_ACCEPTED.value,
                description=f"Player profile '{name}' registered",
                data={"player_id": player_id,
                      "level": profile.level,
                      "faction": profile.faction},
            )
            return True, "registered", profile

    def get_player_profile(self, player_id) -> Optional[PlayerQuestProfile]:
        with self._lock:
            return self._player_profiles.get(player_id)

    def update_player_profile(self, player_id, **kwargs) -> Tuple[bool, str, Optional[PlayerQuestProfile]]:
        """Apply keyword updates to an existing player profile."""
        with self._lock:
            profile = self._player_profiles.get(player_id)
            if profile is None:
                return False, "not_found", None
            if not kwargs:
                return False, "no_updates", profile
            updatable = {
                "name", "level", "faction",
            }
            for key, value in kwargs.items():
                if key == "preferred_difficulty":
                    enum_val = _coerce_enum(QuestDifficulty, value,
                                            QuestDifficulty.NORMAL)
                    profile.preferred_difficulty = enum_val.value
                elif key == "preferred_categories" and isinstance(value, list):
                    profile.preferred_categories = list(value)
                elif key == "active_quests" and isinstance(value, list):
                    profile.active_quests = list(value)
                elif key == "completed_quests" and isinstance(value, list):
                    profile.completed_quests = list(value)
                elif key == "failed_quests" and isinstance(value, list):
                    profile.failed_quests = list(value)
                elif key == "abandoned_quests" and isinstance(value, list):
                    profile.abandoned_quests = list(value)
                elif key == "chain_progress" and isinstance(value, dict):
                    profile.chain_progress = dict(value)
                elif key == "skill_ratings" and isinstance(value, dict):
                    profile.skill_ratings = dict(value)
                elif key == "metadata" and isinstance(value, dict):
                    profile.metadata.update(value)
                elif key in updatable:
                    if key == "level":
                        profile.level = max(1, _safe_int(value, profile.level))
                    else:
                        setattr(profile, key, value)
            profile.updated_at = _now()
            self._emit(
                QuestGenEventKind.QUEST_ACCEPTED.value,
                description=f"Profile '{player_id}' updated",
                data={"keys": list(kwargs.keys())},
            )
            return True, "updated", profile

    def list_player_profiles(self, faction=None, min_level=None,
                             limit=100) -> List[PlayerQuestProfile]:
        with self._lock:
            items = list(self._player_profiles.values())
            if faction is not None:
                items = [p for p in items if p.faction == faction]
            if min_level is not None:
                min_val = _safe_int(min_level, 0)
                items = [p for p in items if p.level >= min_val]
            if limit and limit > 0:
                items = items[:limit]
            return items

    def remove_player_profile(self, player_id) -> Tuple[bool, str]:
        with self._lock:
            if player_id not in self._player_profiles:
                return False, "not_found"
            del self._player_profiles[player_id]
            self._emit(
                QuestGenEventKind.QUEST_REMOVED.value,
                description=f"Player profile '{player_id}' removed",
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Branching
    # ------------------------------------------------------------------

    def create_branch(self, branch_id, quest_id, name,
                      description="", choice_label="",
                      consequences=None, objective_overrides=None,
                      reward_overrides=None, next_quest_template_id="",
                      metadata=None) -> Tuple[bool, str, Optional[QuestBranch]]:
        """Create a branching path attached to a quest."""
        with self._lock:
            if not self._config.enable_branching:
                return False, "branching_disabled", None
            if not branch_id:
                return False, "invalid_branch_id", None
            if branch_id in self._branches:
                return False, "branch_exists", None
            if len(self._branches) >= self._config.max_branches:
                return False, "branches_capacity", None
            quest = self._quests.get(quest_id)
            if quest is None:
                return False, "quest_not_found", None
            branch = QuestBranch(
                branch_id=branch_id,
                quest_id=quest_id,
                name=name,
                description=description or "",
                choice_label=choice_label or name,
                consequences=list(consequences) if consequences else [],
                objective_overrides=list(objective_overrides)
                if objective_overrides else [],
                reward_overrides=list(reward_overrides)
                if reward_overrides else [],
                next_quest_template_id=next_quest_template_id or "",
                chosen=False,
                created_at=_now(),
                metadata=metadata or {},
            )
            self._branches[branch_id] = branch
            if branch_id not in quest.branch_ids:
                quest.branch_ids.append(branch_id)
            self._emit(
                QuestGenEventKind.QUEST_CREATED.value,
                quest_id=quest_id,
                description=f"Branch '{name}' created for quest '{quest_id}'",
                data={"branch_id": branch_id,
                      "quest_id": quest_id},
            )
            return True, "created", branch

    def get_branch(self, branch_id) -> Optional[QuestBranch]:
        with self._lock:
            return self._branches.get(branch_id)

    def list_branches(self, quest_id=None, limit=100) -> List[QuestBranch]:
        with self._lock:
            items = list(self._branches.values())
            if quest_id is not None:
                items = [b for b in items if b.quest_id == quest_id]
            if limit and limit > 0:
                items = items[:limit]
            return items

    def remove_branch(self, branch_id) -> Tuple[bool, str]:
        with self._lock:
            if branch_id not in self._branches:
                return False, "not_found"
            branch = self._branches[branch_id]
            quest = self._quests.get(branch.quest_id)
            if quest is not None and branch_id in quest.branch_ids:
                quest.branch_ids.remove(branch_id)
            del self._branches[branch_id]
            return True, "removed"

    def choose_branch(self, quest_id, branch_id) -> Tuple[bool, str, Optional[QuestInstance]]:
        """Select a branch for a quest and apply its consequences."""
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return False, "quest_not_found", None
            branch = self._branches.get(branch_id)
            if branch is None:
                return False, "branch_not_found", None
            if branch.quest_id != quest_id:
                return False, "branch_quest_mismatch", quest
            if branch.chosen:
                return False, "branch_already_chosen", quest
            branch.chosen = True
            # Mark any sibling branches as unavailable by leaving them
            # unchosen; the caller can remove them if desired.
            # Apply objective overrides if provided.
            for override in branch.objective_overrides:
                if not isinstance(override, dict):
                    continue
                target_id = override.get("objective_id")
                if not target_id:
                    continue
                for obj in quest.objectives:
                    if obj.objective_id == target_id:
                        if "count" in override:
                            obj.count = max(1, _safe_int(override["count"], obj.count))
                        if "target" in override:
                            obj.target = str(override["target"])
                        if "description" in override:
                            obj.description = str(override["description"])
                        if "status" in override:
                            status_enum = _coerce_enum(ObjectiveStatus,
                                                       override["status"])
                            if status_enum is not None:
                                obj.status = status_enum.value
                        break
            # Apply reward overrides if provided.
            for override in branch.reward_overrides:
                if not isinstance(override, dict):
                    continue
                target_id = override.get("reward_id")
                if not target_id:
                    continue
                for reward in quest.rewards:
                    if reward.reward_id == target_id:
                        if "amount" in override:
                            reward.amount = max(0, _safe_int(
                                override["amount"], reward.amount))
                        if "item_id" in override:
                            reward.item_id = str(override["item_id"])
                        break
            self._emit(
                QuestGenEventKind.QUEST_ACCEPTED.value,
                quest_id=quest_id,
                description=f"Branch '{branch.name}' chosen for quest '{quest_id}'",
                data={"quest_id": quest_id,
                      "branch_id": branch_id,
                      "consequences": branch.consequences},
            )
            return True, "chosen", quest

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def suggest_difficulty(self, player_profile) -> Tuple[bool, str, Optional[QuestDifficulty]]:
        """AI-suggest a difficulty tier based on player skill and history.

        Combines the player's preferred difficulty with their completion
        rate to recommend a tier. High completion rates lift the tier;
        low completion rates lower it.
        """
        with self._lock:
            if player_profile is None:
                return False, "invalid_profile", None
            if not isinstance(player_profile, PlayerQuestProfile):
                return False, "invalid_profile_type", None
            base = _coerce_enum(QuestDifficulty,
                                player_profile.preferred_difficulty,
                                QuestDifficulty.NORMAL)
            completion = _clamp(_safe_float(
                player_profile.quest_completion_rate, 0.5), 0.0, 1.0)
            order = list(QuestDifficulty)
            idx = order.index(base)
            if completion > 0.8 and idx < len(order) - 1:
                suggested = order[idx + 1]
            elif completion < 0.3 and idx > 0:
                suggested = order[idx - 1]
            else:
                suggested = base
            self._emit(
                QuestGenEventKind.OBJECTIVE_UPDATED.value,
                description=f"Suggested difficulty '{suggested.value}' "
                            f"for {player_profile.name}",
                data={"player_id": player_profile.player_id,
                      "base": base.value,
                      "suggested": suggested.value,
                      "completion_rate": completion},
            )
            return True, "suggested", suggested

    def optimize_quest_flow(self, player_profile) -> Tuple[bool, str, List[str]]:
        """AI-suggest improvements to a player's quest pacing."""
        with self._lock:
            if player_profile is None:
                return False, "invalid_profile", []
            if not isinstance(player_profile, PlayerQuestProfile):
                return False, "invalid_profile_type", []
            suggestions = self._evaluate_flow_suggestions(player_profile)
            self._emit(
                QuestGenEventKind.OBJECTIVE_UPDATED.value,
                description=f"Flow optimized for {player_profile.name}",
                data={"player_id": player_profile.player_id,
                      "suggestion_count": len(suggestions)},
            )
            return True, "optimized", suggestions

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit=100, event_type=None) -> List[QuestGenEvent]:
        with self._lock:
            items = list(self._events)
            if event_type is not None:
                type_enum = _coerce_enum(QuestGenEventKind, event_type)
                if type_enum is not None:
                    items = [e for e in items
                             if e.event_type == type_enum.value]
                else:
                    items = [e for e in items if e.event_type == event_type]
            if limit and limit > 0:
                items = items[-limit:]
            return items

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            self._refresh_stats()
            return {
                "initialized": self._initialized,
                "templates": len(self._templates),
                "quests": len(self._quests),
                "chains": len(self._chains),
                "player_profiles": len(self._player_profiles),
                "branches": len(self._branches),
                "active_quests": self._stats.active_quests,
                "completed_quests": self._stats.completed_quests,
                "failed_quests": self._stats.failed_quests,
                "expired_quests": self._stats.expired_quests,
                "total_generated": self._stats.total_generated,
                "total_auto_generated": self._stats.total_auto_generated,
                "events": len(self._events),
                "tick_count": self._tick_count,
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            self._refresh_stats()
            return self._stats.to_dict()

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            self._refresh_stats()
            snapshot = QuestGenSnapshot(
                timestamp=_now(),
                templates=[t.to_dict() for t in list(self._templates.values())[:50]],
                quests=[q.to_dict() for q in list(self._quests.values())[-100:]],
                chains=[c.to_dict() for c in list(self._chains.values())[-50:]],
                player_profiles=[p.to_dict() for p in list(self._player_profiles.values())[:50]],
                branches=[b.to_dict() for b in list(self._branches.values())[-50:]],
                events=[e.to_dict() for e in self._events[-100:]],
                stats=self._stats.to_dict(),
            )
            return snapshot.to_dict()

    # ------------------------------------------------------------------
    # Config and Tick
    # ------------------------------------------------------------------

    def get_config(self) -> QuestGenConfig:
        with self._lock:
            return self._config

    def set_config(self, **kwargs) -> Tuple[bool, str, QuestGenConfig]:
        """Apply keyword config updates to the generator."""
        with self._lock:
            if not kwargs:
                return False, "no_updates", self._config
            known = set(self._config.__dataclass_fields__.keys())
            int_keys = {
                "max_templates", "max_quests", "max_chains",
                "max_player_profiles", "max_branches", "max_events",
                "max_objectives_per_quest", "max_rewards_per_quest",
                "max_quests_per_chain", "max_quests_per_player",
            }
            bool_keys = {
                "auto_accept", "auto_complete_objectives",
                "enable_branching", "enable_chains",
            }
            for key, value in kwargs.items():
                if key not in known or key == "metadata":
                    if key == "metadata" and isinstance(value, dict):
                        self._config.metadata.update(value)
                    continue
                if key in int_keys:
                    setattr(self._config, key,
                            max(1, _safe_int(value, getattr(self._config, key))))
                elif key in bool_keys:
                    setattr(self._config, key, bool(value))
                elif key == "default_difficulty":
                    diff_enum = _coerce_enum(QuestDifficulty, value)
                    if diff_enum is not None:
                        self._config.default_difficulty = diff_enum.value
                elif key == "default_priority":
                    pri_enum = _coerce_enum(QuestPriority, value)
                    if pri_enum is not None:
                        self._config.default_priority = pri_enum.value
                else:
                    setattr(self._config, key, value)
            self._emit(
                QuestGenEventKind.CONFIG_CHANGED.value,
                description="Config updated",
                data={"keys": list(kwargs.keys())},
            )
            return True, "updated", self._config

    def tick(self, dt=1.0) -> Dict[str, Any]:
        """Advance the generator by one tick, resolving transient states."""
        with self._lock:
            self._tick_count += 1
            quests_expired = 0
            objectives_completed = 0
            chains_advanced = 0
            # Decrement time limits and expire timed-out quests.
            dt_val = max(0.0, _safe_float(dt, 1.0))
            for quest in self._quests.values():
                if quest.status != QuestStatus.ACTIVE.value:
                    continue
                if quest.time_limit > 0:
                    quest.time_remaining = max(
                        0.0, quest.time_remaining - dt_val
                    )
                    if quest.time_remaining <= 0:
                        quest.status = QuestStatus.EXPIRED.value
                        quest.expired_at = _now()
                        quests_expired += 1
                        self._expire_counter += 1
                # Auto-complete objectives if the flag is set.
                if self._config.auto_complete_objectives:
                    for obj in quest.objectives:
                        if obj.status == ObjectiveStatus.IN_PROGRESS.value:
                            obj.current = obj.count
                            obj.status = ObjectiveStatus.COMPLETED.value
                            objectives_completed += 1
            # Advance chains whose current quest has been completed.
            for chain in self._chains.values():
                if chain.status == QuestStatus.COMPLETED.value:
                    continue
                if chain.current_index >= len(chain.quest_ids):
                    continue
                current_id = chain.quest_ids[chain.current_index]
                current_quest = self._quests.get(current_id)
                if current_quest is not None and \
                        current_quest.status == QuestStatus.COMPLETED.value:
                    if chain.current_index < chain.total_quests - 1:
                        chain.current_index += 1
                        if chain.current_index < len(chain.quest_ids):
                            next_id = chain.quest_ids[chain.current_index]
                            next_quest = self._quests.get(next_id)
                            if next_quest is not None and \
                                    next_quest.status == QuestStatus.LOCKED.value:
                                next_quest.status = QuestStatus.AVAILABLE.value
                        chains_advanced += 1
                    else:
                        chain.status = QuestStatus.COMPLETED.value
            self._refresh_stats()
            return {
                "tick": self._tick_count,
                "dt": dt_val,
                "quests_expired": quests_expired,
                "objectives_completed": objectives_completed,
                "chains_advanced": chains_advanced,
                "active_quests": self._stats.active_quests,
                "total_quests": self._stats.total_quests,
                "total_templates": self._stats.total_templates,
                "total_chains": self._stats.total_chains,
                "total_generated": self._stats.total_generated,
            }

    def reset(self) -> None:
        """Clear all generator state and re-seed the canonical dataset."""
        with self._lock:
            self._templates.clear()
            self._quests.clear()
            self._chains.clear()
            self._player_profiles.clear()
            self._branches.clear()
            self._events.clear()
            self._config = QuestGenConfig()
            self._stats = QuestGenStats()
            self._tick_count = 0
            self._generate_counter = 0
            self._auto_generate_counter = 0
            self._complete_counter = 0
            self._fail_counter = 0
            self._expire_counter = 0
            self._initialized = False
            self._seed()
            self._emit(
                QuestGenEventKind.SYSTEM_RESET.value,
                description="Generator reset and re-seeded",
            )

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the generator with a canonical set of quest content."""
        self._seed_templates()
        self._seed_quests()
        self._seed_chains()
        self._seed_player_profiles()
        self._seed_branches()
        self._seed_events()
        self._refresh_stats()
        self._initialized = True

    def _seed_templates(self) -> None:
        """Seed 8 quest templates spanning the major quest types."""
        templates = [
            QuestTemplate(
                template_id="slay_the_beast",
                name="Slay the Beast",
                quest_type=QuestType.BOUNTY.value,
                category=QuestCategory.COMBAT.value,
                difficulty=QuestDifficulty.HARD.value,
                description="A fearsome beast has been terrorizing the "
                            "outlying farms. Track it to its lair and put "
                            "an end to its rampage.",
                priority=QuestPriority.HIGH.value,
                min_level=5,
                max_level=40,
                recommended_level=10,
                time_limit=0.0,
                repeatable=False,
                objectives=[
                    QuestObjective(
                        objective_id="obj_slay_beast_track",
                        objective_type=ObjectiveType.EXPLORE_AREA.value,
                        target="Beast Lair",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Track the beast to its lair in the "
                                    "Deep Woods.",
                        optional=False,
                        order=0,
                    ),
                    QuestObjective(
                        objective_id="obj_slay_beast_defeat",
                        objective_type=ObjectiveType.DEFEAT_ENEMIES.value,
                        target="Thornback Beast",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Defeat the Thornback Beast.",
                        optional=False,
                        order=1,
                    ),
                ],
                rewards=[
                    QuestReward(
                        reward_id="rew_slay_beast_xp",
                        reward_type=RewardType.EXPERIENCE.value,
                        amount=500,
                        description="Experience for slaying the beast.",
                    ),
                    QuestReward(
                        reward_id="rew_slay_beast_gold",
                        reward_type=RewardType.GOLD.value,
                        amount=250,
                        description="Gold reward from the bounty board.",
                    ),
                    QuestReward(
                        reward_id="rew_slay_beast_item",
                        reward_type=RewardType.ITEM.value,
                        amount=1,
                        item_id="item_thornback_pelt",
                        description="The pelt of the Thornback Beast.",
                    ),
                ],
                requirements=[
                    QuestRequirement(
                        requirement_id="req_slay_beast_level",
                        requirement_type="level",
                        target="player",
                        value=5,
                        description="Must be at least level 5.",
                    ),
                ],
                tags=["combat", "bounty", "beast"],
                enabled=True,
                metadata={"seeded": True, "region": "deep_woods"},
            ),
            QuestTemplate(
                template_id="deliver_the_letter",
                name="Deliver the Letter",
                quest_type=QuestType.DELIVERY.value,
                category=QuestCategory.SOCIAL.value,
                difficulty=QuestDifficulty.EASY.value,
                description="A sealed letter must reach the magistrate in "
                            "the next town before nightfall. The road is "
                            "watched, so travel with care.",
                priority=QuestPriority.LOW.value,
                min_level=1,
                max_level=20,
                recommended_level=3,
                time_limit=1800.0,
                repeatable=True,
                objectives=[
                    QuestObjective(
                        objective_id="obj_deliver_letter_get",
                        objective_type=ObjectiveType.TALK_TO_NPC.value,
                        target="Courier Master",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Speak with the Courier Master to "
                                    "receive the letter.",
                        optional=False,
                        order=0,
                    ),
                    QuestObjective(
                        objective_id="obj_deliver_letter_reach",
                        objective_type=ObjectiveType.REACH_LOCATION.value,
                        target="Magistrate Office",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Reach the Magistrate Office in "
                                    "Oakhaven.",
                        optional=False,
                        order=1,
                    ),
                    QuestObjective(
                        objective_id="obj_deliver_letter_hand",
                        objective_type=ObjectiveType.TALK_TO_NPC.value,
                        target="Magistrate",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Hand the letter to the Magistrate.",
                        optional=False,
                        order=2,
                    ),
                ],
                rewards=[
                    QuestReward(
                        reward_id="rew_deliver_letter_xp",
                        reward_type=RewardType.EXPERIENCE.value,
                        amount=80,
                    ),
                    QuestReward(
                        reward_id="rew_deliver_letter_gold",
                        reward_type=RewardType.GOLD.value,
                        amount=40,
                    ),
                    QuestReward(
                        reward_id="rew_deliver_letter_rep",
                        reward_type=RewardType.REPUTATION.value,
                        amount=10,
                        description="Reputation with Oakhaven.",
                    ),
                ],
                requirements=[],
                tags=["social", "delivery", "repeatable"],
                enabled=True,
                metadata={"seeded": True, "region": "oakhaven"},
            ),
            QuestTemplate(
                template_id="explore_the_ruins",
                name="Explore the Ruins",
                quest_type=QuestType.INVESTIGATION.value,
                category=QuestCategory.EXPLORATION.value,
                difficulty=QuestDifficulty.NORMAL.value,
                description="Ancient ruins have been discovered east of the "
                            "city. Explore them and uncover what lies within.",
                priority=QuestPriority.NORMAL.value,
                min_level=4,
                max_level=35,
                recommended_level=8,
                time_limit=0.0,
                repeatable=False,
                objectives=[
                    QuestObjective(
                        objective_id="obj_explore_ruins_reach",
                        objective_type=ObjectiveType.REACH_LOCATION.value,
                        target="Sunken Ruins",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Reach the Sunken Ruins.",
                        optional=False,
                        order=0,
                    ),
                    QuestObjective(
                        objective_id="obj_explore_ruins_explore",
                        objective_type=ObjectiveType.EXPLORE_AREA.value,
                        target="Sunken Ruins Interior",
                        count=3,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Explore 3 chambers within the ruins.",
                        optional=False,
                        order=1,
                    ),
                    QuestObjective(
                        objective_id="obj_explore_ruins_puzzle",
                        objective_type=ObjectiveType.SOLVE_PUZZLE.value,
                        target="Sealed Door",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Solve the puzzle of the sealed door.",
                        optional=False,
                        order=2,
                    ),
                ],
                rewards=[
                    QuestReward(
                        reward_id="rew_explore_ruins_xp",
                        reward_type=RewardType.EXPERIENCE.value,
                        amount=300,
                    ),
                    QuestReward(
                        reward_id="rew_explore_ruins_item",
                        reward_type=RewardType.ITEM.value,
                        amount=1,
                        item_id="item_ancient_tome",
                        description="An ancient tome recovered from the ruins.",
                    ),
                ],
                requirements=[
                    QuestRequirement(
                        requirement_id="req_explore_ruins_level",
                        requirement_type="level",
                        target="player",
                        value=4,
                    ),
                ],
                tags=["exploration", "investigation", "ruins"],
                enabled=True,
                metadata={"seeded": True, "region": "sunken_ruins"},
            ),
            QuestTemplate(
                template_id="escort_the_merchant",
                name="Escort the Merchant",
                quest_type=QuestType.ESCORT.value,
                category=QuestCategory.SOCIAL.value,
                difficulty=QuestDifficulty.NORMAL.value,
                description="A traveling merchant needs an armed escort "
                            "through the bandit-infested pass. Keep her "
                            "safe until she reaches the next town.",
                priority=QuestPriority.NORMAL.value,
                min_level=3,
                max_level=30,
                recommended_level=6,
                time_limit=0.0,
                repeatable=False,
                objectives=[
                    QuestObjective(
                        objective_id="obj_escort_merchant_talk",
                        objective_type=ObjectiveType.TALK_TO_NPC.value,
                        target="Vessa Threadgold",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Speak with Vessa Threadgold to "
                                    "begin the escort.",
                        optional=False,
                        order=0,
                    ),
                    QuestObjective(
                        objective_id="obj_escort_merchant_escort",
                        objective_type=ObjectiveType.ESCORT_NPC.value,
                        target="Vessa Threadgold",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Escort Vessa through the Bandit Pass.",
                        optional=False,
                        order=1,
                    ),
                    QuestObjective(
                        objective_id="obj_escort_merchant_protect",
                        objective_type=ObjectiveType.PROTECT_TARGET.value,
                        target="Vessa Threadgold",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Keep Vessa alive until arrival.",
                        optional=False,
                        order=2,
                    ),
                ],
                rewards=[
                    QuestReward(
                        reward_id="rew_escort_merchant_xp",
                        reward_type=RewardType.EXPERIENCE.value,
                        amount=220,
                    ),
                    QuestReward(
                        reward_id="rew_escort_merchant_gold",
                        reward_type=RewardType.GOLD.value,
                        amount=150,
                    ),
                    QuestReward(
                        reward_id="rew_escort_merchant_rep",
                        reward_type=RewardType.REPUTATION.value,
                        amount=15,
                        description="Reputation with the Merchant Guild.",
                    ),
                ],
                requirements=[
                    QuestRequirement(
                        requirement_id="req_escort_merchant_level",
                        requirement_type="level",
                        target="player",
                        value=3,
                    ),
                ],
                tags=["social", "escort", "protection"],
                enabled=True,
                metadata={"seeded": True, "region": "bandit_pass"},
            ),
            QuestTemplate(
                template_id="collect_herbs",
                name="Collect Herbs",
                quest_type=QuestType.COLLECTION.value,
                category=QuestCategory.COLLECTION.value,
                difficulty=QuestDifficulty.EASY.value,
                description="The apothecary needs fresh herbs from the "
                            "meadow. Gather a bundle and return for payment.",
                priority=QuestPriority.LOW.value,
                min_level=1,
                max_level=25,
                recommended_level=2,
                time_limit=0.0,
                repeatable=True,
                objectives=[
                    QuestObjective(
                        objective_id="obj_collect_herbs_reach",
                        objective_type=ObjectiveType.REACH_LOCATION.value,
                        target="Oakhaven Meadow",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Reach the Oakhaven Meadow.",
                        optional=False,
                        order=0,
                    ),
                    QuestObjective(
                        objective_id="obj_collect_herbs_gather",
                        objective_type=ObjectiveType.COLLECT_ITEMS.value,
                        target="Moonpetal Herb",
                        count=8,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Gather 8 Moonpetal Herbs.",
                        optional=False,
                        order=1,
                    ),
                ],
                rewards=[
                    QuestReward(
                        reward_id="rew_collect_herbs_xp",
                        reward_type=RewardType.EXPERIENCE.value,
                        amount=60,
                    ),
                    QuestReward(
                        reward_id="rew_collect_herbs_gold",
                        reward_type=RewardType.GOLD.value,
                        amount=30,
                    ),
                ],
                requirements=[],
                tags=["collection", "gathering", "repeatable"],
                enabled=True,
                metadata={"seeded": True, "region": "oakhaven_meadow"},
            ),
            QuestTemplate(
                template_id="defend_the_village",
                name="Defend the Village",
                quest_type=QuestType.DEFENSE.value,
                category=QuestCategory.COMBAT.value,
                difficulty=QuestDifficulty.HARD.value,
                description="A bandit warband marches on Oakhaven. Man the "
                            "walls and repel every wave until dawn.",
                priority=QuestPriority.HIGH.value,
                min_level=6,
                max_level=45,
                recommended_level=12,
                time_limit=0.0,
                repeatable=False,
                objectives=[
                    QuestObjective(
                        objective_id="obj_defend_village_waves",
                        objective_type=ObjectiveType.SURVIVE_WAVES.value,
                        target="Bandit Warband",
                        count=5,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Survive 5 waves of attackers.",
                        optional=False,
                        order=0,
                    ),
                    QuestObjective(
                        objective_id="obj_defend_village_defeat",
                        objective_type=ObjectiveType.DEFEAT_ENEMIES.value,
                        target="Bandit Captain",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Defeat the Bandit Captain.",
                        optional=False,
                        order=1,
                    ),
                ],
                rewards=[
                    QuestReward(
                        reward_id="rew_defend_village_xp",
                        reward_type=RewardType.EXPERIENCE.value,
                        amount=450,
                    ),
                    QuestReward(
                        reward_id="rew_defend_village_gold",
                        reward_type=RewardType.GOLD.value,
                        amount=200,
                    ),
                    QuestReward(
                        reward_id="rew_defend_village_item",
                        reward_type=RewardType.ITEM.value,
                        amount=1,
                        item_id="item_oakhaven_crest",
                        description="The crest of Oakhaven for your service.",
                    ),
                ],
                requirements=[
                    QuestRequirement(
                        requirement_id="req_defend_village_level",
                        requirement_type="level",
                        target="player",
                        value=6,
                    ),
                ],
                tags=["combat", "defense", "village"],
                enabled=True,
                metadata={"seeded": True, "region": "oakhaven"},
            ),
            QuestTemplate(
                template_id="investigate_the_mystery",
                name="Investigate the Mystery",
                quest_type=QuestType.INVESTIGATION.value,
                category=QuestCategory.EXPLORATION.value,
                difficulty=QuestDifficulty.NORMAL.value,
                description="Strange lights have appeared over the old "
                            "watchtower. Investigate the site and uncover "
                            "the source of the phenomenon.",
                priority=QuestPriority.NORMAL.value,
                min_level=5,
                max_level=40,
                recommended_level=9,
                time_limit=0.0,
                repeatable=False,
                objectives=[
                    QuestObjective(
                        objective_id="obj_investigate_mystery_reach",
                        objective_type=ObjectiveType.REACH_LOCATION.value,
                        target="Old Watchtower",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Reach the Old Watchtower.",
                        optional=False,
                        order=0,
                    ),
                    QuestObjective(
                        objective_id="obj_investigate_mystery_clues",
                        objective_type=ObjectiveType.EXPLORE_AREA.value,
                        target="Watchtower Clues",
                        count=4,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Find 4 clues around the watchtower.",
                        optional=False,
                        order=1,
                    ),
                    QuestObjective(
                        objective_id="obj_investigate_mystery_puzzle",
                        objective_type=ObjectiveType.SOLVE_PUZZLE.value,
                        target="Runed Altar",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Decipher the runed altar.",
                        optional=False,
                        order=2,
                    ),
                ],
                rewards=[
                    QuestReward(
                        reward_id="rew_investigate_mystery_xp",
                        reward_type=RewardType.EXPERIENCE.value,
                        amount=350,
                    ),
                    QuestReward(
                        reward_id="rew_investigate_mystery_skill",
                        reward_type=RewardType.SKILL.value,
                        amount=1,
                        item_id="skill_arcane_sight",
                        description="Learn the Arcane Sight skill.",
                    ),
                ],
                requirements=[
                    QuestRequirement(
                        requirement_id="req_investigate_mystery_level",
                        requirement_type="level",
                        target="player",
                        value=5,
                    ),
                ],
                tags=["exploration", "mystery", "puzzle"],
                enabled=True,
                metadata={"seeded": True, "region": "old_watchtower"},
            ),
            QuestTemplate(
                template_id="retrieve_the_artifact",
                name="Retrieve the Artifact",
                quest_type=QuestType.RETRIEVAL.value,
                category=QuestCategory.EXPLORATION.value,
                difficulty=QuestDifficulty.EXTREME.value,
                description="A powerful artifact lies deep within the "
                            "Forgotten Vault. Retrieve it before the "
                            "Shadow Cult can claim it.",
                priority=QuestPriority.URGENT.value,
                min_level=15,
                max_level=60,
                recommended_level=25,
                time_limit=0.0,
                repeatable=False,
                objectives=[
                    QuestObjective(
                        objective_id="obj_retrieve_artifact_reach",
                        objective_type=ObjectiveType.REACH_LOCATION.value,
                        target="Forgotten Vault",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Reach the Forgotten Vault entrance.",
                        optional=False,
                        order=0,
                    ),
                    QuestObjective(
                        objective_id="obj_retrieve_artifact_defeat",
                        objective_type=ObjectiveType.DEFEAT_ENEMIES.value,
                        target="Vault Guardian",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Defeat the Vault Guardian.",
                        optional=False,
                        order=1,
                    ),
                    QuestObjective(
                        objective_id="obj_retrieve_artifact_collect",
                        objective_type=ObjectiveType.COLLECT_ITEMS.value,
                        target="Sunstone Relic",
                        count=1,
                        current=0,
                        status=ObjectiveStatus.PENDING.value,
                        description="Recover the Sunstone Relic.",
                        optional=False,
                        order=2,
                    ),
                ],
                rewards=[
                    QuestReward(
                        reward_id="rew_retrieve_artifact_xp",
                        reward_type=RewardType.EXPERIENCE.value,
                        amount=1200,
                    ),
                    QuestReward(
                        reward_id="rew_retrieve_artifact_item",
                        reward_type=RewardType.ITEM.value,
                        amount=1,
                        item_id="item_sunstone_relic",
                        description="The Sunstone Relic itself.",
                    ),
                    QuestReward(
                        reward_id="rew_retrieve_artifact_achievement",
                        reward_type=RewardType.ACHIEVEMENT.value,
                        amount=1,
                        item_id="achievement_relic_hunter",
                        description="Relic Hunter achievement unlocked.",
                    ),
                ],
                requirements=[
                    QuestRequirement(
                        requirement_id="req_retrieve_artifact_level",
                        requirement_type="level",
                        target="player",
                        value=15,
                    ),
                ],
                tags=["exploration", "retrieval", "artifact", "extreme"],
                enabled=True,
                metadata={"seeded": True, "region": "forgotten_vault"},
            ),
        ]
        for template in templates:
            self._templates[template.template_id] = template

    def _seed_quests(self) -> None:
        """Seed 5 quest instances generated from the seeded templates."""
        quest_specs = [
            ("quest_slay_beast_inst", "slay_the_beast", 10,
             QuestDifficulty.HARD, QuestStatus.AVAILABLE.value, "", "", -1),
            ("quest_deliver_letter_inst", "deliver_the_letter", 3,
             QuestDifficulty.EASY, QuestStatus.AVAILABLE.value, "", "", -1),
            ("quest_explore_ruins_inst", "explore_the_ruins", 8,
             QuestDifficulty.NORMAL, QuestStatus.AVAILABLE.value, "", "", -1),
            ("quest_collect_herbs_inst", "collect_herbs", 2,
             QuestDifficulty.EASY, QuestStatus.AVAILABLE.value, "", "", -1),
            ("quest_defend_village_inst", "defend_the_village", 12,
             QuestDifficulty.HARD, QuestStatus.AVAILABLE.value, "", "", -1),
        ]
        for (quest_id, template_id, level, diff_enum, status,
             player_id, chain_id, chain_idx) in quest_specs:
            template = self._templates.get(template_id)
            if template is None:
                continue
            instance = self._instantiate_template(
                template=template,
                player_level=level,
                difficulty_enum=diff_enum,
                chain_id=chain_id,
                chain_index=chain_idx,
                player_id=player_id,
                metadata={"seeded": True,
                          "template_id": template_id},
            )
            instance.quest_id = quest_id
            instance.status = status
            self._quests[quest_id] = instance
            self._generate_counter += 1

    def _seed_chains(self) -> None:
        """Seed 3 quest chains: bandit_arc, dragon_saga, lost_kingdom."""
        # Bandit Arc: a 3-quest chain built from existing seeded quests.
        bandit_quest_ids = [
            "quest_defend_village_inst",
            "quest_slay_beast_inst",
            "quest_explore_ruins_inst",
        ]
        bandit_chain = QuestChain(
            chain_id="chain_bandit_arc",
            name="Bandit Arc",
            theme="bandit",
            description="A three-quest arc tracking the bandit threat "
                        "from village defense to lair assault.",
            quest_ids=list(bandit_quest_ids),
            template_ids=["defend_the_village", "slay_the_beast",
                          "explore_the_ruins"],
            current_index=0,
            total_quests=3,
            completed_quests=0,
            status=QuestStatus.AVAILABLE.value,
            created_at=_now(),
            metadata={"seeded": True, "theme": "bandit"},
        )
        self._chains[bandit_chain.chain_id] = bandit_chain
        # Link the quests back to the chain.
        for idx, qid in enumerate(bandit_quest_ids):
            quest = self._quests.get(qid)
            if quest is not None:
                quest.chain_id = bandit_chain.chain_id
                quest.chain_index = idx
                if idx > 0:
                    quest.status = QuestStatus.LOCKED.value

        # Dragon Saga: a 3-quest chain generated fresh for the seed.
        dragon_quest_ids: List[str] = []
        dragon_templates = ["slay_the_beast", "retrieve_the_artifact",
                            "investigate_the_mystery"]
        for idx, tmpl_id in enumerate(dragon_templates):
            template = self._templates.get(tmpl_id)
            if template is None:
                continue
            instance = self._instantiate_template(
                template=template,
                player_level=20,
                difficulty_enum=QuestDifficulty.EXTREME,
                chain_id="chain_dragon_saga",
                chain_index=idx,
                metadata={"seeded": True, "chain_id": "chain_dragon_saga",
                          "chain_index": idx, "theme": "dragon"},
            )
            instance.quest_id = f"quest_dragon_saga_{idx + 1}"
            instance.name = f"Dragon Saga Chapter {idx + 1}"
            instance.status = (QuestStatus.LOCKED.value if idx > 0
                                else QuestStatus.AVAILABLE.value)
            self._quests[instance.quest_id] = instance
            self._generate_counter += 1
            dragon_quest_ids.append(instance.quest_id)
        dragon_chain = QuestChain(
            chain_id="chain_dragon_saga",
            name="Dragon Saga",
            theme="dragon",
            description="An epic three-quest saga culminating in the "
                        "confrontation with the ancient dragon.",
            quest_ids=dragon_quest_ids,
            template_ids=dragon_templates,
            current_index=0,
            total_quests=len(dragon_quest_ids),
            completed_quests=0,
            status=QuestStatus.AVAILABLE.value,
            created_at=_now(),
            metadata={"seeded": True, "theme": "dragon",
                      "difficulty": QuestDifficulty.EXTREME.value},
        )
        self._chains[dragon_chain.chain_id] = dragon_chain

        # Lost Kingdom: a 3-quest chain mixing exploration and retrieval.
        lost_quest_ids: List[str] = []
        lost_templates = ["explore_the_ruins", "investigate_the_mystery",
                          "retrieve_the_artifact"]
        for idx, tmpl_id in enumerate(lost_templates):
            template = self._templates.get(tmpl_id)
            if template is None:
                continue
            instance = self._instantiate_template(
                template=template,
                player_level=15,
                difficulty_enum=QuestDifficulty.HARD,
                chain_id="chain_lost_kingdom",
                chain_index=idx,
                metadata={"seeded": True, "chain_id": "chain_lost_kingdom",
                          "chain_index": idx, "theme": "lost_kingdom"},
            )
            instance.quest_id = f"quest_lost_kingdom_{idx + 1}"
            instance.name = f"Lost Kingdom Chapter {idx + 1}"
            instance.status = (QuestStatus.LOCKED.value if idx > 0
                                else QuestStatus.AVAILABLE.value)
            self._quests[instance.quest_id] = instance
            self._generate_counter += 1
            lost_quest_ids.append(instance.quest_id)
        lost_chain = QuestChain(
            chain_id="chain_lost_kingdom",
            name="Lost Kingdom",
            theme="lost_kingdom",
            description="A three-quest chain uncovering the secrets of "
                        "the Lost Kingdom and reclaiming its greatest "
                        "treasure.",
            quest_ids=lost_quest_ids,
            template_ids=lost_templates,
            current_index=0,
            total_quests=len(lost_quest_ids),
            completed_quests=0,
            status=QuestStatus.AVAILABLE.value,
            created_at=_now(),
            metadata={"seeded": True, "theme": "lost_kingdom",
                      "difficulty": QuestDifficulty.HARD.value},
        )
        self._chains[lost_chain.chain_id] = lost_chain

    def _seed_player_profiles(self) -> None:
        """Seed 5 player profiles spanning different play styles."""
        profiles = [
            PlayerQuestProfile(
                player_id="player_kael",
                name="Kael Ironhand",
                level=12,
                faction="iron_vanguard",
                active_quests=["quest_slay_beast_inst"],
                completed_quests=["quest_collect_herbs_inst"],
                failed_quests=[],
                abandoned_quests=[],
                preferred_categories=[QuestCategory.COMBAT.value,
                                      QuestCategory.EXPLORATION.value],
                preferred_difficulty=QuestDifficulty.HARD.value,
                quest_completion_rate=0.85,
                total_quests_attempted=8,
                total_quests_completed=7,
                chain_progress={"chain_bandit_arc": 0},
                skill_ratings={"combat": 0.9, "exploration": 0.7,
                               "social": 0.4},
                created_at=_now(),
                updated_at=_now(),
                metadata={"seeded": True, "class": "warrior"},
            ),
            PlayerQuestProfile(
                player_id="player_vessa",
                name="Vessa Threadgold",
                level=6,
                faction="merchant_guild",
                active_quests=["quest_deliver_letter_inst"],
                completed_quests=[],
                failed_quests=[],
                abandoned_quests=[],
                preferred_categories=[QuestCategory.SOCIAL.value,
                                      QuestCategory.COLLECTION.value],
                preferred_difficulty=QuestDifficulty.EASY.value,
                quest_completion_rate=0.6,
                total_quests_attempted=5,
                total_quests_completed=3,
                chain_progress={},
                skill_ratings={"social": 0.8, "collection": 0.7,
                               "combat": 0.3},
                created_at=_now(),
                updated_at=_now(),
                metadata={"seeded": True, "class": "merchant"},
            ),
            PlayerQuestProfile(
                player_id="player_pip",
                name="Pip the Quick",
                level=3,
                faction="oakhaven",
                active_quests=["quest_collect_herbs_inst"],
                completed_quests=[],
                failed_quests=["quest_deliver_letter_inst"],
                abandoned_quests=[],
                preferred_categories=[QuestCategory.COLLECTION.value],
                preferred_difficulty=QuestDifficulty.TRIVIAL.value,
                quest_completion_rate=0.25,
                total_quests_attempted=4,
                total_quests_completed=1,
                chain_progress={},
                skill_ratings={"collection": 0.5, "exploration": 0.4,
                               "combat": 0.2},
                created_at=_now(),
                updated_at=_now(),
                metadata={"seeded": True, "class": "gatherer"},
            ),
            PlayerQuestProfile(
                player_id="player_lyra",
                name="Lyra Moonwhisper",
                level=18,
                faction="arcane_circle",
                active_quests=["quest_explore_ruins_inst"],
                completed_quests=["quest_slay_beast_inst",
                                  "quest_defend_village_inst"],
                failed_quests=[],
                abandoned_quests=[],
                preferred_categories=[QuestCategory.EXPLORATION.value,
                                      QuestCategory.STORY.value],
                preferred_difficulty=QuestDifficulty.NORMAL.value,
                quest_completion_rate=0.9,
                total_quests_attempted=12,
                total_quests_completed=11,
                chain_progress={"chain_dragon_saga": 0,
                                "chain_lost_kingdom": 0},
                skill_ratings={"exploration": 0.95, "combat": 0.7,
                               "social": 0.6},
                created_at=_now(),
                updated_at=_now(),
                metadata={"seeded": True, "class": "mage"},
            ),
            PlayerQuestProfile(
                player_id="player_garrick",
                name="Garrick Stoneheart",
                level=25,
                faction="iron_vanguard",
                active_quests=[],
                completed_quests=["quest_slay_beast_inst",
                                  "quest_defend_village_inst",
                                  "quest_explore_ruins_inst"],
                failed_quests=[],
                abandoned_quests=["quest_collect_herbs_inst"],
                preferred_categories=[QuestCategory.COMBAT.value,
                                      QuestCategory.STORY.value],
                preferred_difficulty=QuestDifficulty.EXTREME.value,
                quest_completion_rate=0.75,
                total_quests_attempted=10,
                total_quests_completed=7,
                chain_progress={"chain_bandit_arc": 2,
                                "chain_dragon_saga": 0},
                skill_ratings={"combat": 0.98, "exploration": 0.6,
                               "social": 0.5},
                created_at=_now(),
                updated_at=_now(),
                metadata={"seeded": True, "class": "paladin"},
            ),
        ]
        for profile in profiles:
            self._player_profiles[profile.player_id] = profile

    def _seed_branches(self) -> None:
        """Seed 4 quest branches tied to the seeded quest instances."""
        branch_specs = [
            ("branch_slay_beast_mercy", "quest_slay_beast_inst",
             "Show Mercy", "Spare the beast and seek to calm it.",
             "Spare the Thornback Beast",
             ["Beast becomes a passive ally",
              "Reputation with druids increased"],
             [{"objective_id": "obj_slay_beast_defeat",
               "target": "Thornback Beast (Calmed)",
               "description": "Calm the Thornback Beast instead of "
                              "slaying it."}],
             [{"reward_id": "rew_slay_beast_gold",
               "amount": 100}],
             "", {"seeded": True, "path": "mercy"}),
            ("branch_slay_beast_slay", "quest_slay_beast_inst",
             "Slay Outright", "Kill the beast and claim the full bounty.",
             "Slay the Thornback Beast",
             ["Full bounty paid",
              "Reputation with farmers increased"],
             [],
             [{"reward_id": "rew_slay_beast_gold",
               "amount": 300}],
             "", {"seeded": True, "path": "slay"}),
            ("branch_deliver_letter_open", "quest_deliver_letter_inst",
             "Open the Letter", "Read the sealed letter before delivery.",
             "Open the sealed letter",
             ["Learn a state secret",
              "Risk angering the magistrate"],
             [{"objective_id": "obj_deliver_letter_hand",
               "description": "Deliver the letter (now opened) to the "
                              "Magistrate."}],
             [{"reward_id": "rew_deliver_letter_rep",
               "amount": -5}],
             "", {"seeded": True, "path": "open"}),
            ("branch_deliver_letter_sealed", "quest_deliver_letter_inst",
             "Deliver Sealed", "Deliver the letter untouched.",
             "Deliver the letter sealed",
             ["Magistrate's trust earned",
              "Reputation with the court increased"],
             [],
             [{"reward_id": "rew_deliver_letter_rep",
               "amount": 20}],
             "", {"seeded": True, "path": "sealed"}),
        ]
        for (branch_id, quest_id, name, desc, choice, consequences,
             obj_overrides, rew_overrides, next_tmpl, meta) in branch_specs:
            branch = QuestBranch(
                branch_id=branch_id,
                quest_id=quest_id,
                name=name,
                description=desc,
                choice_label=choice,
                consequences=list(consequences),
                objective_overrides=list(obj_overrides),
                reward_overrides=list(rew_overrides),
                next_quest_template_id=next_tmpl,
                chosen=False,
                created_at=_now(),
                metadata=meta,
            )
            self._branches[branch_id] = branch
            quest = self._quests.get(quest_id)
            if quest is not None and branch_id not in quest.branch_ids:
                quest.branch_ids.append(branch_id)

    def _seed_events(self) -> None:
        """Seed 6 audit events marking the initial dataset population."""
        events = [
            QuestGenEvent(
                event_id="evt_seed_templates",
                timestamp=_now(),
                event_type=QuestGenEventKind.QUEST_CREATED.value,
                quest_id="",
                description="Seeded 8 quest templates",
                metadata={"seeded": True, "count": 8},
            ),
            QuestGenEvent(
                event_id="evt_seed_quests",
                timestamp=_now(),
                event_type=QuestGenEventKind.QUEST_CREATED.value,
                quest_id="quest_slay_beast_inst",
                description="Seeded 5 quest instances",
                metadata={"seeded": True, "count": 5},
            ),
            QuestGenEvent(
                event_id="evt_seed_chains",
                timestamp=_now(),
                event_type=QuestGenEventKind.CHAIN_GENERATED.value,
                quest_id="",
                description="Seeded 3 quest chains",
                metadata={"seeded": True, "count": 3},
            ),
            QuestGenEvent(
                event_id="evt_seed_profiles",
                timestamp=_now(),
                event_type=QuestGenEventKind.QUEST_ACCEPTED.value,
                quest_id="",
                description="Seeded 5 player profiles",
                metadata={"seeded": True, "count": 5},
            ),
            QuestGenEvent(
                event_id="evt_seed_branches",
                timestamp=_now(),
                event_type=QuestGenEventKind.QUEST_CREATED.value,
                quest_id="quest_slay_beast_inst",
                description="Seeded 4 quest branches",
                metadata={"seeded": True, "count": 4},
            ),
            QuestGenEvent(
                event_id="evt_seed_system",
                timestamp=_now(),
                event_type=QuestGenEventKind.SYSTEM_RESET.value,
                quest_id="",
                description="Generator initialized with canonical dataset",
                metadata={"seeded": True,
                          "templates": 8,
                          "quests": 5,
                          "chains": 3,
                          "profiles": 5,
                          "branches": 4},
            ),
        ]
        for event in events:
            self._events.append(event)


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_ai_quest_generator() -> AIQuestGenerator:
    """Factory function returning the singleton AIQuestGenerator instance."""
    return AIQuestGenerator.get_instance()


__all__ = [
    # Enums
    "QuestType",
    "QuestStatus",
    "QuestDifficulty",
    "ObjectiveType",
    "ObjectiveStatus",
    "QuestCategory",
    "RewardType",
    "QuestPriority",
    "QuestGenEventKind",
    # Data classes
    "QuestObjective",
    "QuestReward",
    "QuestRequirement",
    "QuestBranch",
    "QuestChain",
    "QuestTemplate",
    "QuestInstance",
    "PlayerQuestProfile",
    "QuestGenConfig",
    "QuestGenStats",
    "QuestGenSnapshot",
    "QuestGenEvent",
    # Main system class
    "AIQuestGenerator",
    # Factory
    "get_ai_quest_generator",
]