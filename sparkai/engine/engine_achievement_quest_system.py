"""
SparkLabs Engine - Achievement & Quest System

Provides achievement tracking, quest chains, daily/weekly quests, quest rewards,
progress tracking, and achievement categories. Designed as a self-contained
singleton system with seed data for immediate integration testing.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _now() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


_MAX_ACHIEVEMENTS = 1000
_MAX_PLAYER_ACHIEVEMENTS = 5000
_MAX_QUESTS = 1000
_MAX_PLAYER_QUESTS = 5000
_MAX_QUEST_CHAINS = 200


def _evict_fifo_list(items: List[Any], max_size: int) -> None:
    while len(items) > max_size:
        items.pop(0)


def _dataclass_to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for field_name in obj.__dataclass_fields__:
            val = getattr(obj, field_name)
            if hasattr(val, "to_dict") and callable(val.to_dict):
                result[field_name] = val.to_dict()
            elif isinstance(val, list):
                result[field_name] = [_dataclass_to_dict(item) for item in val]
            elif isinstance(val, tuple):
                result[field_name] = [_dataclass_to_dict(item) for item in val]
            elif isinstance(val, dict):
                result[field_name] = {k: _dataclass_to_dict(v) for k, v in val.items()}
            else:
                result[field_name] = val
        return result
    if isinstance(obj, list):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, tuple):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AchievementCategory(str, Enum):
    COMBAT = "combat"
    EXPLORATION = "exploration"
    COLLECTION = "collection"
    CRAFTING = "crafting"
    SOCIAL = "social"
    PVP = "pvp"
    PVE = "pve"
    ECONOMY = "economy"
    SPECIAL = "special"
    SEASONAL = "seasonal"


class AchievementTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class AchievementStatus(str, Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CLAIMED = "claimed"


class QuestType(str, Enum):
    MAIN_QUEST = "main_quest"
    SIDE_QUEST = "side_quest"
    DAILY = "daily"
    WEEKLY = "weekly"
    STORY = "story"
    EVENT = "event"
    HIDDEN = "hidden"


class QuestStatus(str, Enum):
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"
    CLAIMED = "claimed"
    LOCKED = "locked"


class QuestObjectiveType(str, Enum):
    KILL = "kill"
    COLLECT = "collect"
    TALK = "talk"
    REACH = "reach"
    USE = "use"
    ESCORT = "escort"
    DEFEND = "defend"
    DEFEAT = "defeat"


class QuestObjectiveStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class QuestChainStatus(str, Enum):
    LOCKED = "locked"
    ACTIVE = "active"
    COMPLETED = "completed"


class AchievementQuestEventKind(str, Enum):
    ACHIEVEMENT_REGISTERED = "achievement_registered"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    ACHIEVEMENT_PROGRESS = "achievement_progress"
    ACHIEVEMENT_CLAIMED = "achievement_claimed"
    QUEST_REGISTERED = "quest_registered"
    QUEST_ACCEPTED = "quest_accepted"
    QUEST_PROGRESS = "quest_progress"
    QUEST_COMPLETED = "quest_completed"
    QUEST_FAILED = "quest_failed"
    QUEST_ABANDONED = "quest_abandoned"
    QUEST_CLAIMED = "quest_claimed"
    CHAIN_REGISTERED = "chain_registered"
    CHAIN_COMPLETED = "chain_completed"
    DAILY_REFRESH = "daily_refresh"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AchievementCriteria:
    criteria_id: str
    description: str = ""
    target_value: int = 1
    current_value: int = 0
    metric: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AchievementDefinition:
    achievement_id: str
    name: str
    description: str = ""
    category: str = AchievementCategory.SPECIAL.value
    tier: str = AchievementTier.BRONZE.value
    criteria: List[AchievementCriteria] = field(default_factory=list)
    reward_gold: float = 1000.0
    reward_xp: int = 500
    reward_items: List[Dict[str, Any]] = field(default_factory=list)
    points: int = 10
    hidden: bool = False
    parent_achievement_id: str = ""
    prerequisite_achievement_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerAchievement:
    player_id: str
    achievement_id: str
    status: str = AchievementStatus.LOCKED.value
    progress: float = 0.0
    criteria_progress: Dict[str, int] = field(default_factory=dict)
    unlocked_at: float = 0.0
    completed_at: float = 0.0
    claimed_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QuestObjective:
    objective_id: str
    description: str = ""
    objective_type: str = QuestObjectiveType.KILL.value
    target_id: str = ""
    target_name: str = ""
    target_count: int = 1
    current_count: int = 0
    status: str = QuestObjectiveStatus.PENDING.value
    optional: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QuestDefinition:
    quest_id: str
    name: str
    description: str = ""
    quest_type: str = QuestType.SIDE_QUEST.value
    category: str = "general"
    objectives: List[QuestObjective] = field(default_factory=list)
    min_level: int = 1
    prerequisite_quest_ids: List[str] = field(default_factory=list)
    reward_gold: float = 1000.0
    reward_xp: int = 500
    reward_items: List[Dict[str, Any]] = field(default_factory=list)
    reward_achievements: List[str] = field(default_factory=list)
    next_quest_id: str = ""
    chain_id: str = ""
    repeatable: bool = False
    daily: bool = False
    weekly: bool = False
    expires_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerQuest:
    player_id: str
    quest_id: str
    status: str = QuestStatus.AVAILABLE.value
    accepted_at: float = field(default_factory=_now)
    completed_at: float = 0.0
    claimed_at: float = 0.0
    expires_at: float = 0.0
    objective_progress: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QuestChain:
    chain_id: str
    name: str
    description: str = ""
    quest_ids: List[str] = field(default_factory=list)
    reward_gold: float = 10000.0
    reward_xp: int = 5000
    reward_achievement_id: str = ""
    required_level: int = 1
    status: str = QuestChainStatus.LOCKED.value
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AchievementQuestConfig:
    max_achievements: int = 1000
    max_player_achievements: int = 5000
    max_quests: int = 1000
    max_player_quests: int = 5000
    max_quest_chains: int = 200
    daily_quest_limit: int = 10
    weekly_quest_limit: int = 25
    daily_refresh_hour: int = 0
    weekly_refresh_day: int = 0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AchievementQuestStats:
    total_achievements: int = 0
    total_player_achievements: int = 0
    unlocked_achievements: int = 0
    completed_achievements: int = 0
    claimed_achievements: int = 0
    total_quests: int = 0
    total_player_quests: int = 0
    active_quests: int = 0
    completed_quests: int = 0
    claimed_quests: int = 0
    total_chains: int = 0
    completed_chains: int = 0
    total_points_awarded: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AchievementQuestSnapshot:
    config: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    achievements: List[Dict[str, Any]] = field(default_factory=list)
    quests: List[Dict[str, Any]] = field(default_factory=list)
    chains: List[Dict[str, Any]] = field(default_factory=list)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AchievementQuestEvent:
    event_id: str
    kind: str
    timestamp: float
    achievement_id: str = ""
    quest_id: str = ""
    chain_id: str = ""
    player_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)

# ---------------------------------------------------------------------------
# Achievement Quest System
# ---------------------------------------------------------------------------

class AchievementQuestSystem:
    """Manages achievements, quests, quest chains, and progress tracking."""

    _instance: Optional["AchievementQuestSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._achievements: Dict[str, AchievementDefinition] = {}
        self._player_achievements: Dict[str, PlayerAchievement] = {}
        self._quests: Dict[str, QuestDefinition] = {}
        self._player_quests: Dict[str, PlayerQuest] = {}
        self._chains: Dict[str, QuestChain] = {}
        self._events: List[AchievementQuestEvent] = []
        self._stats = AchievementQuestStats()
        self._config = AchievementQuestConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "AchievementQuestSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed initial achievements, quests, chains, and player progress."""
        with self._init_lock:
            if self._initialized:
                return

            # Achievements
            ach1 = AchievementDefinition(
                achievement_id="ach_first_blood",
                name="First Blood",
                description="Defeat your first enemy in combat.",
                category=AchievementCategory.COMBAT.value,
                tier=AchievementTier.BRONZE.value,
                criteria=[
                    AchievementCriteria(
                        criteria_id="crit_first_blood",
                        description="Defeat 1 enemy",
                        target_value=1,
                        current_value=0,
                        metric="kills_total",
                    ),
                ],
                reward_gold=500.0,
                reward_xp=100,
                points=10,
            )
            self._achievements[ach1.achievement_id] = ach1

            ach2 = AchievementDefinition(
                achievement_id="ach_centurion",
                name="Centurion",
                description="Defeat 100 enemies in combat.",
                category=AchievementCategory.COMBAT.value,
                tier=AchievementTier.SILVER.value,
                criteria=[
                    AchievementCriteria(
                        criteria_id="crit_centurion",
                        description="Defeat 100 enemies",
                        target_value=100,
                        current_value=0,
                        metric="kills_total",
                    ),
                ],
                reward_gold=5000.0,
                reward_xp=2000,
                points=50,
                prerequisite_achievement_ids=["ach_first_blood"],
            )
            self._achievements[ach2.achievement_id] = ach2

            ach3 = AchievementDefinition(
                achievement_id="ach_explorer",
                name="World Explorer",
                description="Discover all regions in the world.",
                category=AchievementCategory.EXPLORATION.value,
                tier=AchievementTier.GOLD.value,
                criteria=[
                    AchievementCriteria(
                        criteria_id="crit_explorer",
                        description="Discover 20 regions",
                        target_value=20,
                        current_value=0,
                        metric="regions_discovered",
                    ),
                ],
                reward_gold=10000.0,
                reward_xp=5000,
                points=100,
            )
            self._achievements[ach3.achievement_id] = ach3

            ach4 = AchievementDefinition(
                achievement_id="ach_master_crafter",
                name="Master Crafter",
                description="Craft 1000 items.",
                category=AchievementCategory.CRAFTING.value,
                tier=AchievementTier.PLATINUM.value,
                criteria=[
                    AchievementCriteria(
                        criteria_id="crit_crafter",
                        description="Craft 1000 items",
                        target_value=1000,
                        current_value=0,
                        metric="items_crafted",
                    ),
                ],
                reward_gold=25000.0,
                reward_xp=10000,
                points=200,
            )
            self._achievements[ach4.achievement_id] = ach4

            ach5 = AchievementDefinition(
                achievement_id="ach_arena_champion",
                name="Arena Champion",
                description="Win 500 PvP arena matches.",
                category=AchievementCategory.PVP.value,
                tier=AchievementTier.DIAMOND.value,
                criteria=[
                    AchievementCriteria(
                        criteria_id="crit_arena",
                        description="Win 500 arena matches",
                        target_value=500,
                        current_value=0,
                        metric="arena_wins",
                    ),
                ],
                reward_gold=50000.0,
                reward_xp=20000,
                points=500,
                hidden=False,
            )
            self._achievements[ach5.achievement_id] = ach5

            ach6 = AchievementDefinition(
                achievement_id="ach_dungeon_conqueror",
                name="Dungeon Conqueror",
                description="Complete all dungeons in the realm.",
                category=AchievementCategory.PVE.value,
                tier=AchievementTier.GOLD.value,
                criteria=[
                    AchievementCriteria(
                        criteria_id="crit_dungeon",
                        description="Complete 50 dungeons",
                        target_value=50,
                        current_value=0,
                        metric="dungeons_completed",
                    ),
                ],
                reward_gold=15000.0,
                reward_xp=8000,
                points=150,
            )
            self._achievements[ach6.achievement_id] = ach6

            # Player achievements
            pa1 = PlayerAchievement(
                player_id="player_starter",
                achievement_id="ach_first_blood",
                status=AchievementStatus.COMPLETED.value,
                progress=1.0,
                criteria_progress={"crit_first_blood": 1},
                unlocked_at=_now() - 86400 * 5,
                completed_at=_now() - 86400 * 5,
            )
            self._player_achievements[f"{pa1.player_id}:{pa1.achievement_id}"] = pa1

            pa2 = PlayerAchievement(
                player_id="player_starter",
                achievement_id="ach_centurion",
                status=AchievementStatus.IN_PROGRESS.value,
                progress=0.35,
                criteria_progress={"crit_centurion": 35},
                unlocked_at=_now() - 86400 * 3,
            )
            self._player_achievements[f"{pa2.player_id}:{pa2.achievement_id}"] = pa2

            pa3 = PlayerAchievement(
                player_id="player_veteran",
                achievement_id="ach_first_blood",
                status=AchievementStatus.CLAIMED.value,
                progress=1.0,
                criteria_progress={"crit_first_blood": 1},
                unlocked_at=_now() - 86400 * 60,
                completed_at=_now() - 86400 * 60,
                claimed_at=_now() - 86400 * 59,
            )
            self._player_achievements[f"{pa3.player_id}:{pa3.achievement_id}"] = pa3

            pa4 = PlayerAchievement(
                player_id="player_veteran",
                achievement_id="ach_centurion",
                status=AchievementStatus.COMPLETED.value,
                progress=1.0,
                criteria_progress={"crit_centurion": 100},
                unlocked_at=_now() - 86400 * 30,
                completed_at=_now() - 86400 * 30,
            )
            self._player_achievements[f"{pa4.player_id}:{pa4.achievement_id}"] = pa4

            pa5 = PlayerAchievement(
                player_id="player_veteran",
                achievement_id="ach_explorer",
                status=AchievementStatus.IN_PROGRESS.value,
                progress=0.85,
                criteria_progress={"crit_explorer": 17},
                unlocked_at=_now() - 86400 * 20,
            )
            self._player_achievements[f"{pa5.player_id}:{pa5.achievement_id}"] = pa5

            pa6 = PlayerAchievement(
                player_id="player_veteran",
                achievement_id="ach_dungeon_conqueror",
                status=AchievementStatus.COMPLETED.value,
                progress=1.0,
                criteria_progress={"crit_dungeon": 50},
                unlocked_at=_now() - 86400 * 10,
                completed_at=_now() - 86400 * 10,
            )
            self._player_achievements[f"{pa6.player_id}:{pa6.achievement_id}"] = pa6

            # Quests
            quest1 = QuestDefinition(
                quest_id="quest_starter_01",
                name="The Journey Begins",
                description="Speak with the Elder in the starting village.",
                quest_type=QuestType.MAIN_QUEST.value,
                category="tutorial",
                min_level=1,
                objectives=[
                    QuestObjective(
                        objective_id="obj_talk_elder",
                        description="Talk to Elder Theron",
                        objective_type=QuestObjectiveType.TALK.value,
                        target_id="npc_elder_theron",
                        target_name="Elder Theron",
                        target_count=1,
                    ),
                    QuestObjective(
                        objective_id="obj_reach_forest",
                        description="Reach the Whispering Forest",
                        objective_type=QuestObjectiveType.REACH.value,
                        target_id="loc_whispering_forest",
                        target_name="Whispering Forest",
                        target_count=1,
                    ),
                ],
                reward_gold=500.0,
                reward_xp=200,
                reward_items=[{"item_id": "item_starter_sword", "quantity": 1}],
                next_quest_id="quest_starter_02",
                chain_id="chain_starter_saga",
            )
            self._quests[quest1.quest_id] = quest1

            quest2 = QuestDefinition(
                quest_id="quest_starter_02",
                name="Wolf Problem",
                description="Defeat 5 wolves terrorizing the village outskirts.",
                quest_type=QuestType.MAIN_QUEST.value,
                category="combat",
                min_level=2,
                prerequisite_quest_ids=["quest_starter_01"],
                objectives=[
                    QuestObjective(
                        objective_id="obj_kill_wolves",
                        description="Defeat 5 Dire Wolves",
                        objective_type=QuestObjectiveType.KILL.value,
                        target_id="mob_dire_wolf",
                        target_name="Dire Wolf",
                        target_count=5,
                    ),
                ],
                reward_gold=1500.0,
                reward_xp=800,
                reward_items=[{"item_id": "item_wolf_pelt", "quantity": 5}],
                next_quest_id="quest_starter_03",
                chain_id="chain_starter_saga",
            )
            self._quests[quest2.quest_id] = quest2

            quest3 = QuestDefinition(
                quest_id="quest_starter_03",
                name="The Lost Artifact",
                description="Recover the lost artifact from the bandit camp.",
                quest_type=QuestType.MAIN_QUEST.value,
                category="dungeon",
                min_level=5,
                prerequisite_quest_ids=["quest_starter_02"],
                objectives=[
                    QuestObjective(
                        objective_id="obj_defeat_bandit_leader",
                        description="Defeat the Bandit Leader",
                        objective_type=QuestObjectiveType.DEFEAT.value,
                        target_id="boss_bandit_leader",
                        target_name="Bandit Leader",
                        target_count=1,
                    ),
                    QuestObjective(
                        objective_id="obj_collect_artifact",
                        description="Collect the Ancient Artifact",
                        objective_type=QuestObjectiveType.COLLECT.value,
                        target_id="item_ancient_artifact",
                        target_name="Ancient Artifact",
                        target_count=1,
                    ),
                ],
                reward_gold=5000.0,
                reward_xp=3000,
                reward_items=[
                    {"item_id": "item_artifact_relic", "quantity": 1},
                ],
                reward_achievements=["ach_explorer"],
                chain_id="chain_starter_saga",
            )
            self._quests[quest3.quest_id] = quest3

            quest4 = QuestDefinition(
                quest_id="quest_daily_01",
                name="Daily Bounty Hunt",
                description="Defeat 10 enemies for a daily reward.",
                quest_type=QuestType.DAILY.value,
                category="daily",
                min_level=1,
                repeatable=True,
                daily=True,
                expires_at=_now() + 86400,
                objectives=[
                    QuestObjective(
                        objective_id="obj_daily_kills",
                        description="Defeat 10 enemies",
                        objective_type=QuestObjectiveType.KILL.value,
                        target_count=10,
                    ),
                ],
                reward_gold=1000.0,
                reward_xp=500,
            )
            self._quests[quest4.quest_id] = quest4

            quest5 = QuestDefinition(
                quest_id="quest_weekly_01",
                name="Weekly Dungeon Challenge",
                description="Complete 5 dungeon runs this week.",
                quest_type=QuestType.WEEKLY.value,
                category="weekly",
                min_level=10,
                repeatable=True,
                weekly=True,
                expires_at=_now() + 86400 * 7,
                objectives=[
                    QuestObjective(
                        objective_id="obj_weekly_dungeons",
                        description="Complete 5 dungeons",
                        objective_type=QuestObjectiveType.DEFEAT.value,
                        target_count=5,
                    ),
                ],
                reward_gold=10000.0,
                reward_xp=5000,
                reward_items=[{"item_id": "item_chest_weekly", "quantity": 1}],
            )
            self._quests[quest5.quest_id] = quest5

            quest6 = QuestDefinition(
                quest_id="quest_side_01",
                name="Herbalist's Request",
                description="Collect 20 healing herbs for the village herbalist.",
                quest_type=QuestType.SIDE_QUEST.value,
                category="gathering",
                min_level=3,
                repeatable=True,
                objectives=[
                    QuestObjective(
                        objective_id="obj_collect_herbs",
                        description="Collect 20 Healing Herbs",
                        objective_type=QuestObjectiveType.COLLECT.value,
                        target_id="item_healing_herb",
                        target_name="Healing Herb",
                        target_count=20,
                    ),
                ],
                reward_gold=800.0,
                reward_xp=400,
            )
            self._quests[quest6.quest_id] = quest6

            # Player quests
            pq1 = PlayerQuest(
                player_id="player_starter",
                quest_id="quest_starter_01",
                status=QuestStatus.ACTIVE.value,
                accepted_at=_now() - 3600,
                expires_at=_now() + 86400,
                objective_progress={"obj_talk_elder": 1, "obj_reach_forest": 0},
            )
            self._player_quests[f"{pq1.player_id}:{pq1.quest_id}"] = pq1

            pq2 = PlayerQuest(
                player_id="player_starter",
                quest_id="quest_daily_01",
                status=QuestStatus.ACTIVE.value,
                accepted_at=_now() - 3600 * 3,
                expires_at=_now() + 86400,
                objective_progress={"obj_daily_kills": 4},
            )
            self._player_quests[f"{pq2.player_id}:{pq2.quest_id}"] = pq2

            pq3 = PlayerQuest(
                player_id="player_veteran",
                quest_id="quest_starter_01",
                status=QuestStatus.CLAIMED.value,
                accepted_at=_now() - 86400 * 50,
                completed_at=_now() - 86400 * 49,
                claimed_at=_now() - 86400 * 49,
                objective_progress={"obj_talk_elder": 1, "obj_reach_forest": 1},
            )
            self._player_quests[f"{pq3.player_id}:{pq3.quest_id}"] = pq3

            pq4 = PlayerQuest(
                player_id="player_veteran",
                quest_id="quest_starter_02",
                status=QuestStatus.CLAIMED.value,
                accepted_at=_now() - 86400 * 48,
                completed_at=_now() - 86400 * 47,
                claimed_at=_now() - 86400 * 47,
                objective_progress={"obj_kill_wolves": 5},
            )
            self._player_quests[f"{pq4.player_id}:{pq4.quest_id}"] = pq4

            pq5 = PlayerQuest(
                player_id="player_veteran",
                quest_id="quest_starter_03",
                status=QuestStatus.ACTIVE.value,
                accepted_at=_now() - 86400 * 5,
                objective_progress={"obj_defeat_bandit_leader": 0, "obj_collect_artifact": 0},
            )
            self._player_quests[f"{pq5.player_id}:{pq5.quest_id}"] = pq5

            pq6 = PlayerQuest(
                player_id="player_veteran",
                quest_id="quest_weekly_01",
                status=QuestStatus.ACTIVE.value,
                accepted_at=_now() - 86400 * 2,
                expires_at=_now() + 86400 * 5,
                objective_progress={"obj_weekly_dungeons": 3},
            )
            self._player_quests[f"{pq6.player_id}:{pq6.quest_id}"] = pq6

            # Quest chains
            chain1 = QuestChain(
                chain_id="chain_starter_saga",
                name="The Starter Saga",
                description="The beginning of an epic adventure.",
                quest_ids=["quest_starter_01", "quest_starter_02", "quest_starter_03"],
                reward_gold=10000.0,
                reward_xp=5000,
                reward_achievement_id="ach_explorer",
                required_level=1,
                status=QuestChainStatus.ACTIVE.value,
            )
            self._chains[chain1.chain_id] = chain1

            chain2 = QuestChain(
                chain_id="chain_dungeon_master",
                name="Dungeon Master Chronicles",
                description="Conquer all dungeons in the realm.",
                quest_ids=[],
                reward_gold=50000.0,
                reward_xp=25000,
                reward_achievement_id="ach_dungeon_conqueror",
                required_level=20,
                status=QuestChainStatus.LOCKED.value,
            )
            self._chains[chain2.chain_id] = chain2

            self._refresh_stats()
            self._initialized = True

    def _refresh_stats(self) -> None:
        self._stats.total_achievements = len(self._achievements)
        self._stats.total_player_achievements = len(self._player_achievements)
        self._stats.unlocked_achievements = sum(
            1 for pa in self._player_achievements.values()
            if pa.status in (AchievementStatus.UNLOCKED.value, AchievementStatus.COMPLETED.value, AchievementStatus.CLAIMED.value)
        )
        self._stats.completed_achievements = sum(
            1 for pa in self._player_achievements.values()
            if pa.status in (AchievementStatus.COMPLETED.value, AchievementStatus.CLAIMED.value)
        )
        self._stats.claimed_achievements = sum(
            1 for pa in self._player_achievements.values()
            if pa.status == AchievementStatus.CLAIMED.value
        )
        self._stats.total_quests = len(self._quests)
        self._stats.total_player_quests = len(self._player_quests)
        self._stats.active_quests = sum(
            1 for pq in self._player_quests.values() if pq.status == QuestStatus.ACTIVE.value
        )
        self._stats.completed_quests = sum(
            1 for pq in self._player_quests.values()
            if pq.status in (QuestStatus.COMPLETED.value, QuestStatus.CLAIMED.value)
        )
        self._stats.claimed_quests = sum(
            1 for pq in self._player_quests.values() if pq.status == QuestStatus.CLAIMED.value
        )
        self._stats.total_chains = len(self._chains)
        self._stats.completed_chains = sum(
            1 for c in self._chains.values() if c.status == QuestChainStatus.COMPLETED.value
        )

    def _record_event(
        self,
        kind: str,
        achievement_id: str = "",
        quest_id: str = "",
        chain_id: str = "",
        player_id: str = "",
        description: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> AchievementQuestEvent:
        event = AchievementQuestEvent(
            event_id=f"evt_{self._event_counter:06d}",
            kind=kind,
            timestamp=_now(),
            achievement_id=achievement_id,
            quest_id=quest_id,
            chain_id=chain_id,
            player_id=player_id,
            description=description,
            details=details or {},
        )
        self._event_counter += 1
        self._events.append(event)
        _evict_fifo_list(self._events, 2000)
        return event

    # ------------------------------------------------------------------
    # Achievement management
    # ------------------------------------------------------------------

    def register_achievement(
        self,
        achievement_id: str,
        name: str,
        description: str = "",
        category: str = AchievementCategory.SPECIAL.value,
        tier: str = AchievementTier.BRONZE.value,
        reward_gold: float = 1000.0,
        reward_xp: int = 500,
        points: int = 10,
        hidden: bool = False,
    ) -> Tuple[bool, str, Optional[AchievementDefinition]]:
        if achievement_id in self._achievements:
            return False, "exists", None
        if len(self._achievements) >= _MAX_ACHIEVEMENTS:
            return False, "capacity", None
        achievement = AchievementDefinition(
            achievement_id=achievement_id,
            name=name,
            description=description,
            category=category,
            tier=tier,
            reward_gold=reward_gold,
            reward_xp=reward_xp,
            points=points,
            hidden=hidden,
        )
        self._achievements[achievement_id] = achievement
        self._record_event(
            AchievementQuestEventKind.ACHIEVEMENT_REGISTERED.value,
            achievement_id=achievement_id,
            description=f"Achievement '{name}' registered",
        )
        return True, "registered", achievement

    def remove_achievement(self, achievement_id: str) -> Tuple[bool, str]:
        if achievement_id not in self._achievements:
            return False, "not_found"
        del self._achievements[achievement_id]
        return True, "removed"

    def get_achievement(self, achievement_id: str) -> Optional[AchievementDefinition]:
        return self._achievements.get(achievement_id)

    def list_achievements(
        self,
        category: str = "",
        tier: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[AchievementDefinition]:
        achievements = list(self._achievements.values())
        if category:
            achievements = [a for a in achievements if a.category == category]
        if tier:
            achievements = [a for a in achievements if a.tier == tier]
        return achievements[offset : offset + limit]

    def unlock_achievement(
        self, player_id: str, achievement_id: str
    ) -> Tuple[bool, str, Optional[PlayerAchievement]]:
        achievement = self._achievements.get(achievement_id)
        if achievement is None:
            return False, "achievement_not_found", None
        key = f"{player_id}:{achievement_id}"
        pa = self._player_achievements.get(key)
        if pa is not None and pa.status != AchievementStatus.LOCKED.value:
            return False, "already_unlocked", None
        for prereq_id in achievement.prerequisite_achievement_ids:
            prereq_key = f"{player_id}:{prereq_id}"
            prereq = self._player_achievements.get(prereq_key)
            if prereq is None or prereq.status not in (
                AchievementStatus.COMPLETED.value,
                AchievementStatus.CLAIMED.value,
            ):
                return False, "prerequisite_not_met", None
        if pa is None:
            pa = PlayerAchievement(
                player_id=player_id,
                achievement_id=achievement_id,
            )
            self._player_achievements[key] = pa
        pa.status = AchievementStatus.UNLOCKED.value
        pa.unlocked_at = _now()
        self._record_event(
            AchievementQuestEventKind.ACHIEVEMENT_UNLOCKED.value,
            achievement_id=achievement_id,
            player_id=player_id,
            description=f"Achievement '{achievement.name}' unlocked for {player_id}",
        )
        return True, "unlocked", pa

    def update_achievement_progress(
        self, player_id: str, achievement_id: str, criteria_id: str, value: int
    ) -> Tuple[bool, str, Optional[PlayerAchievement]]:
        achievement = self._achievements.get(achievement_id)
        if achievement is None:
            return False, "achievement_not_found", None
        key = f"{player_id}:{achievement_id}"
        pa = self._player_achievements.get(key)
        if pa is None:
            pa = PlayerAchievement(
                player_id=player_id,
                achievement_id=achievement_id,
            )
            self._player_achievements[key] = pa
        if pa.status in (AchievementStatus.COMPLETED.value, AchievementStatus.CLAIMED.value):
            return False, "already_completed", None
        criteria = next((c for c in achievement.criteria if c.criteria_id == criteria_id), None)
        if criteria is None:
            return False, "criteria_not_found", None
        pa.criteria_progress[criteria_id] = max(
            pa.criteria_progress.get(criteria_id, 0), value
        )
        if pa.status == AchievementStatus.LOCKED.value:
            pa.status = AchievementStatus.IN_PROGRESS.value
        all_criteria_met = True
        for c in achievement.criteria:
            current = pa.criteria_progress.get(c.criteria_id, 0)
            if current < c.target_value:
                all_criteria_met = False
                break
        if all_criteria_met and achievement.criteria:
            pa.status = AchievementStatus.COMPLETED.value
            pa.completed_at = _now()
            pa.progress = 1.0
            self._record_event(
                AchievementQuestEventKind.ACHIEVEMENT_CLAIMED.value,
                achievement_id=achievement_id,
                player_id=player_id,
                description=f"Achievement '{achievement.name}' completed for {player_id}",
            )
        else:
            total_target = sum(c.target_value for c in achievement.criteria) if achievement.criteria else 1
            total_current = sum(
                pa.criteria_progress.get(c.criteria_id, 0) for c in achievement.criteria
            )
            pa.progress = total_current / total_target if total_target > 0 else 0.0
            self._record_event(
                AchievementQuestEventKind.ACHIEVEMENT_PROGRESS.value,
                achievement_id=achievement_id,
                player_id=player_id,
                description=f"Achievement progress: {pa.progress * 100:.1f}%",
            )
        return True, "updated", pa

    def claim_achievement(
        self, player_id: str, achievement_id: str
    ) -> Tuple[bool, str, Optional[PlayerAchievement]]:
        achievement = self._achievements.get(achievement_id)
        if achievement is None:
            return False, "achievement_not_found", None
        key = f"{player_id}:{achievement_id}"
        pa = self._player_achievements.get(key)
        if pa is None:
            return False, "not_unlocked", None
        if pa.status != AchievementStatus.COMPLETED.value:
            return False, "not_completed", None
        pa.status = AchievementStatus.CLAIMED.value
        pa.claimed_at = _now()
        self._stats.total_points_awarded += achievement.points
        self._record_event(
            AchievementQuestEventKind.ACHIEVEMENT_CLAIMED.value,
            achievement_id=achievement_id,
            player_id=player_id,
            description=f"Achievement '{achievement.name}' rewards claimed by {player_id}",
        )
        return True, "claimed", pa

    def get_player_achievement(
        self, player_id: str, achievement_id: str
    ) -> Optional[PlayerAchievement]:
        return self._player_achievements.get(f"{player_id}:{achievement_id}")

    def list_player_achievements(
        self,
        player_id: str,
        status: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[PlayerAchievement]:
        achievements = [
            pa for pa in self._player_achievements.values() if pa.player_id == player_id
        ]
        if status:
            achievements = [pa for pa in achievements if pa.status == status]
        return achievements[offset : offset + limit]

    def get_player_achievement_points(self, player_id: str) -> int:
        total = 0
        for pa in self._player_achievements.values():
            if pa.player_id != player_id:
                continue
            if pa.status in (AchievementStatus.COMPLETED.value, AchievementStatus.CLAIMED.value):
                achievement = self._achievements.get(pa.achievement_id)
                if achievement:
                    total += achievement.points
        return total

    # ------------------------------------------------------------------
    # Quest management
    # ------------------------------------------------------------------

    def register_quest(
        self,
        quest_id: str,
        name: str,
        description: str = "",
        quest_type: str = QuestType.SIDE_QUEST.value,
        category: str = "general",
        min_level: int = 1,
        reward_gold: float = 1000.0,
        reward_xp: int = 500,
        repeatable: bool = False,
        daily: bool = False,
        weekly: bool = False,
        chain_id: str = "",
        next_quest_id: str = "",
    ) -> Tuple[bool, str, Optional[QuestDefinition]]:
        if quest_id in self._quests:
            return False, "exists", None
        if len(self._quests) >= _MAX_QUESTS:
            return False, "capacity", None
        quest = QuestDefinition(
            quest_id=quest_id,
            name=name,
            description=description,
            quest_type=quest_type,
            category=category,
            min_level=min_level,
            reward_gold=reward_gold,
            reward_xp=reward_xp,
            repeatable=repeatable,
            daily=daily,
            weekly=weekly,
            chain_id=chain_id,
            next_quest_id=next_quest_id,
            expires_at=_now() + 86400 if daily else (_now() + 86400 * 7 if weekly else 0),
        )
        self._quests[quest_id] = quest
        self._record_event(
            AchievementQuestEventKind.QUEST_REGISTERED.value,
            quest_id=quest_id,
            description=f"Quest '{name}' registered",
        )
        return True, "registered", quest

    def remove_quest(self, quest_id: str) -> Tuple[bool, str]:
        if quest_id not in self._quests:
            return False, "not_found"
        del self._quests[quest_id]
        return True, "removed"

    def get_quest(self, quest_id: str) -> Optional[QuestDefinition]:
        return self._quests.get(quest_id)

    def list_quests(
        self,
        quest_type: str = "",
        category: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[QuestDefinition]:
        quests = list(self._quests.values())
        if quest_type:
            quests = [q for q in quests if q.quest_type == quest_type]
        if category:
            quests = [q for q in quests if q.category == category]
        return quests[offset : offset + limit]

    def accept_quest(
        self, player_id: str, quest_id: str
    ) -> Tuple[bool, str, Optional[PlayerQuest]]:
        quest = self._quests.get(quest_id)
        if quest is None:
            return False, "quest_not_found", None
        key = f"{player_id}:{quest_id}"
        existing = self._player_quests.get(key)
        if existing is not None and existing.status == QuestStatus.ACTIVE.value:
            return False, "already_active", None
        if not quest.repeatable and existing is not None and existing.status in (
            QuestStatus.COMPLETED.value,
            QuestStatus.CLAIMED.value,
        ):
            return False, "already_completed", None
        for prereq_id in quest.prerequisite_quest_ids:
            prereq_key = f"{player_id}:{prereq_id}"
            prereq = self._player_quests.get(prereq_key)
            if prereq is None or prereq.status not in (
                QuestStatus.COMPLETED.value,
                QuestStatus.CLAIMED.value,
            ):
                return False, "prerequisite_not_met", None
        pq = PlayerQuest(
            player_id=player_id,
            quest_id=quest_id,
            status=QuestStatus.ACTIVE.value,
            accepted_at=_now(),
            expires_at=quest.expires_at if quest.daily or quest.weekly else 0,
        )
        for obj in quest.objectives:
            pq.objective_progress[obj.objective_id] = 0
        self._player_quests[key] = pq
        self._record_event(
            AchievementQuestEventKind.QUEST_ACCEPTED.value,
            quest_id=quest_id,
            player_id=player_id,
            description=f"Quest '{quest.name}' accepted by {player_id}",
        )
        return True, "accepted", pq

    def update_quest_progress(
        self, player_id: str, quest_id: str, objective_id: str, count: int = 1
    ) -> Tuple[bool, str, Optional[PlayerQuest]]:
        quest = self._quests.get(quest_id)
        if quest is None:
            return False, "quest_not_found", None
        key = f"{player_id}:{quest_id}"
        pq = self._player_quests.get(key)
        if pq is None:
            return False, "not_accepted", None
        if pq.status != QuestStatus.ACTIVE.value:
            return False, "not_active", None
        objective = next((o for o in quest.objectives if o.objective_id == objective_id), None)
        if objective is None:
            return False, "objective_not_found", None
        pq.objective_progress[objective_id] = min(
            pq.objective_progress.get(objective_id, 0) + count,
            objective.target_count,
        )
        all_required_done = True
        for obj in quest.objectives:
            if obj.optional:
                continue
            if pq.objective_progress.get(obj.objective_id, 0) < obj.target_count:
                all_required_done = False
                break
        if all_required_done:
            pq.status = QuestStatus.COMPLETED.value
            pq.completed_at = _now()
            self._record_event(
                AchievementQuestEventKind.QUEST_COMPLETED.value,
                quest_id=quest_id,
                player_id=player_id,
                description=f"Quest '{quest.name}' completed by {player_id}",
            )
        else:
            self._record_event(
                AchievementQuestEventKind.QUEST_PROGRESS.value,
                quest_id=quest_id,
                player_id=player_id,
                description=f"Quest objective '{objective_id}' progress: {pq.objective_progress[objective_id]}/{objective.target_count}",
            )
        return True, "updated", pq

    def complete_quest(
        self, player_id: str, quest_id: str
    ) -> Tuple[bool, str, Optional[PlayerQuest]]:
        quest = self._quests.get(quest_id)
        if quest is None:
            return False, "quest_not_found", None
        key = f"{player_id}:{quest_id}"
        pq = self._player_quests.get(key)
        if pq is None:
            return False, "not_accepted", None
        if pq.status != QuestStatus.ACTIVE.value:
            return False, "not_active", None
        for obj in quest.objectives:
            if obj.optional:
                continue
            if pq.objective_progress.get(obj.objective_id, 0) < obj.target_count:
                pq.objective_progress[obj.objective_id] = obj.target_count
        pq.status = QuestStatus.COMPLETED.value
        pq.completed_at = _now()
        self._record_event(
            AchievementQuestEventKind.QUEST_COMPLETED.value,
            quest_id=quest_id,
            player_id=player_id,
            description=f"Quest '{quest.name}' completed by {player_id}",
        )
        return True, "completed", pq

    def fail_quest(
        self, player_id: str, quest_id: str
    ) -> Tuple[bool, str, Optional[PlayerQuest]]:
        quest = self._quests.get(quest_id)
        if quest is None:
            return False, "quest_not_found", None
        key = f"{player_id}:{quest_id}"
        pq = self._player_quests.get(key)
        if pq is None:
            return False, "not_accepted", None
        if pq.status != QuestStatus.ACTIVE.value:
            return False, "not_active", None
        pq.status = QuestStatus.FAILED.value
        self._record_event(
            AchievementQuestEventKind.QUEST_FAILED.value,
            quest_id=quest_id,
            player_id=player_id,
            description=f"Quest '{quest.name}' failed by {player_id}",
        )
        return True, "failed", pq

    def abandon_quest(
        self, player_id: str, quest_id: str
    ) -> Tuple[bool, str, Optional[PlayerQuest]]:
        quest = self._quests.get(quest_id)
        if quest is None:
            return False, "quest_not_found", None
        key = f"{player_id}:{quest_id}"
        pq = self._player_quests.get(key)
        if pq is None:
            return False, "not_accepted", None
        if pq.status not in (QuestStatus.ACTIVE.value, QuestStatus.AVAILABLE.value):
            return False, "invalid_state", None
        pq.status = QuestStatus.ABANDONED.value
        self._record_event(
            AchievementQuestEventKind.QUEST_ABANDONED.value,
            quest_id=quest_id,
            player_id=player_id,
            description=f"Quest '{quest.name}' abandoned by {player_id}",
        )
        return True, "abandoned", pq

    def claim_quest_rewards(
        self, player_id: str, quest_id: str
    ) -> Tuple[bool, str, Optional[PlayerQuest]]:
        quest = self._quests.get(quest_id)
        if quest is None:
            return False, "quest_not_found", None
        key = f"{player_id}:{quest_id}"
        pq = self._player_quests.get(key)
        if pq is None:
            return False, "not_accepted", None
        if pq.status != QuestStatus.COMPLETED.value:
            return False, "not_completed", None
        pq.status = QuestStatus.CLAIMED.value
        pq.claimed_at = _now()
        for ach_id in quest.reward_achievements:
            self.unlock_achievement(player_id, ach_id)
        if quest.next_quest_id:
            next_quest = self._quests.get(quest.next_quest_id)
            if next_quest is not None:
                self._check_chain_completion(player_id, quest.chain_id)
        self._record_event(
            AchievementQuestEventKind.QUEST_CLAIMED.value,
            quest_id=quest_id,
            player_id=player_id,
            description=f"Quest '{quest.name}' rewards claimed by {player_id}",
            details={"reward_gold": quest.reward_gold, "reward_xp": quest.reward_xp},
        )
        return True, "claimed", pq

    def get_player_quest(
        self, player_id: str, quest_id: str
    ) -> Optional[PlayerQuest]:
        return self._player_quests.get(f"{player_id}:{quest_id}")

    def list_player_quests(
        self,
        player_id: str,
        status: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[PlayerQuest]:
        quests = [pq for pq in self._player_quests.values() if pq.player_id == player_id]
        if status:
            quests = [pq for pq in quests if pq.status == status]
        return quests[offset : offset + limit]

    def _check_chain_completion(self, player_id: str, chain_id: str) -> None:
        if not chain_id:
            return
        chain = self._chains.get(chain_id)
        if chain is None:
            return
        all_done = True
        for qid in chain.quest_ids:
            pq = self._player_quests.get(f"{player_id}:{qid}")
            if pq is None or pq.status not in (
                QuestStatus.COMPLETED.value,
                QuestStatus.CLAIMED.value,
            ):
                all_done = False
                break
        if all_done:
            chain.status = QuestChainStatus.COMPLETED.value
            self._record_event(
                AchievementQuestEventKind.CHAIN_COMPLETED.value,
                chain_id=chain_id,
                player_id=player_id,
                description=f"Quest chain '{chain.name}' completed by {player_id}",
            )
            if chain.reward_achievement_id:
                self.unlock_achievement(player_id, chain.reward_achievement_id)

    # ------------------------------------------------------------------
    # Quest chain management
    # ------------------------------------------------------------------

    def register_chain(
        self,
        chain_id: str,
        name: str,
        description: str = "",
        reward_gold: float = 10000.0,
        reward_xp: int = 5000,
        reward_achievement_id: str = "",
        required_level: int = 1,
    ) -> Tuple[bool, str, Optional[QuestChain]]:
        if chain_id in self._chains:
            return False, "exists", None
        if len(self._chains) >= _MAX_QUEST_CHAINS:
            return False, "capacity", None
        chain = QuestChain(
            chain_id=chain_id,
            name=name,
            description=description,
            reward_gold=reward_gold,
            reward_xp=reward_xp,
            reward_achievement_id=reward_achievement_id,
            required_level=required_level,
        )
        self._chains[chain_id] = chain
        self._record_event(
            AchievementQuestEventKind.CHAIN_REGISTERED.value,
            chain_id=chain_id,
            description=f"Quest chain '{name}' registered",
        )
        return True, "registered", chain

    def get_chain(self, chain_id: str) -> Optional[QuestChain]:
        return self._chains.get(chain_id)

    def list_chains(
        self, status: str = "", limit: int = 50, offset: int = 0
    ) -> List[QuestChain]:
        chains = list(self._chains.values())
        if status:
            chains = [c for c in chains if c.status == status]
        return chains[offset : offset + limit]

    # ------------------------------------------------------------------
    # System operations
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        self._tick_count += 1
        now = _now()
        for pq in self._player_quests.values():
            if (
                pq.status == QuestStatus.ACTIVE.value
                and pq.expires_at > 0
                and now > pq.expires_at
            ):
                pq.status = QuestStatus.FAILED.value
        self._refresh_stats()
        self._record_event(
            AchievementQuestEventKind.TICK.value,
            description=f"Tick #{self._tick_count}",
        )
        return self.get_status()

    def set_config(self, config: Dict[str, Any]) -> AchievementQuestConfig:
        if "max_achievements" in config:
            self._config.max_achievements = _safe_int(
                config["max_achievements"], self._config.max_achievements
            )
        if "max_quests" in config:
            self._config.max_quests = _safe_int(config["max_quests"], self._config.max_quests)
        if "daily_quest_limit" in config:
            self._config.daily_quest_limit = _safe_int(
                config["daily_quest_limit"], self._config.daily_quest_limit
            )
        if "weekly_quest_limit" in config:
            self._config.weekly_quest_limit = _safe_int(
                config["weekly_quest_limit"], self._config.weekly_quest_limit
            )
        self._record_event(
            AchievementQuestEventKind.CONFIG_UPDATED.value,
            description="Configuration updated",
        )
        return self._config

    def get_config(self) -> AchievementQuestConfig:
        return self._config

    def list_events(
        self, player_id: str = "", limit: int = 50, offset: int = 0
    ) -> List[AchievementQuestEvent]:
        events = self._events
        if player_id:
            events = [e for e in events if e.player_id == player_id]
        return events[offset : offset + limit]

    def get_stats(self) -> AchievementQuestStats:
        self._refresh_stats()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        self._refresh_stats()
        return {
            "initialized": self._initialized,
            "total_achievements": len(self._achievements),
            "total_player_achievements": len(self._player_achievements),
            "total_quests": len(self._quests),
            "total_player_quests": len(self._player_quests),
            "total_chains": len(self._chains),
            "active_quests": sum(
                1 for pq in self._player_quests.values() if pq.status == QuestStatus.ACTIVE.value
            ),
            "completed_quests": sum(
                1 for pq in self._player_quests.values()
                if pq.status in (QuestStatus.COMPLETED.value, QuestStatus.CLAIMED.value)
            ),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> AchievementQuestSnapshot:
        self._refresh_stats()
        return AchievementQuestSnapshot(
            config=self._config.to_dict(),
            stats=self._stats.to_dict(),
            achievements=[a.to_dict() for a in list(self._achievements.values())[:50]],
            quests=[q.to_dict() for q in list(self._quests.values())[:50]],
            chains=[c.to_dict() for c in list(self._chains.values())[:50]],
            tick_count=self._tick_count,
            timestamp=_now(),
        )

    def reset(self) -> Dict[str, Any]:
        with self._init_lock:
            self._achievements.clear()
            self._player_achievements.clear()
            self._quests.clear()
            self._player_quests.clear()
            self._chains.clear()
            self._events.clear()
            self._stats = AchievementQuestStats()
            self._config = AchievementQuestConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._seed()
        self._record_event(
            AchievementQuestEventKind.RESET.value,
            description="System reset to seed state",
        )
        return self.get_status()


def get_achievement_quest_system() -> AchievementQuestSystem:
    """Factory function to get the AchievementQuestSystem singleton instance."""
    return AchievementQuestSystem.get_instance()
