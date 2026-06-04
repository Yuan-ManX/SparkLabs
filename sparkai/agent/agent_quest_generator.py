"""
SparkLabs Agent - Quest Generator

Dynamic quest generation system for procedural game content.
Creates multi-stage quests with objectives, rewards, dependencies,
and adaptive difficulty based on player progression.

Architecture:
  AgentQuestGenerator (Singleton)
    |-- Quest Template Library (categorized quest patterns)
    |-- Objective Chain Builder (sequential/parallel objective trees)
    |-- Reward Calculator (balanced reward distribution)
    |-- Difficulty Scaler (player-level-adaptive difficulty)
    |-- Quest Dependency Graph (prerequisite and follow-up quests)
    |-- Quest State Machine (tracking quest lifecycle)
    |-- Narrative Hook Generator (quest story and motivation)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class QuestCategory(Enum):
    MAIN_STORY = "main_story"
    SIDE_QUEST = "side_quest"
    FETCH = "fetch"
    ESCORT = "escort"
    ELIMINATION = "elimination"
    EXPLORATION = "exploration"
    PUZZLE = "puzzle"
    DELIVERY = "delivery"
    COLLECTION = "collection"
    DEFENSE = "defense"
    ESCORT_MISSION = "escort_mission"
    BOSS_BATTLE = "boss_battle"


class QuestStatus(Enum):
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    LOCKED = "locked"


class ObjectiveType(Enum):
    KILL = "kill"
    COLLECT = "collect"
    TALK = "talk"
    REACH = "reach"
    ESCORT = "escort"
    DEFEND = "defend"
    ACTIVATE = "activate"
    DELIVER = "deliver"
    INVESTIGATE = "investigate"
    CRAFT = "craft"
    ESCORT_TO = "escort_to"
    PROTECT = "protect"


class RewardType(Enum):
    EXPERIENCE = "experience"
    GOLD = "gold"
    ITEM = "item"
    SKILL = "skill"
    REPUTATION = "reputation"
    UNLOCK = "unlock"
    ABILITY = "ability"


class DifficultyLevel(Enum):
    TRIVIAL = "trivial"
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class QuestObjective:
    """A single objective within a quest."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    objective_type: ObjectiveType = ObjectiveType.COLLECT
    description: str = ""
    target_id: str = ""
    target_count: int = 1
    current_count: int = 0
    is_optional: bool = False
    is_complete: bool = False
    order_index: int = 0
    location_hint: str = ""
    time_limit: float = 0.0
    prerequisites: List[str] = field(default_factory=list)

    def progress(self) -> float:
        if self.target_count == 0:
            return 1.0
        return min(1.0, self.current_count / self.target_count)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "objective_type": self.objective_type.value,
            "description": self.description,
            "target_id": self.target_id,
            "target_count": self.target_count,
            "current_count": self.current_count,
            "is_optional": self.is_optional,
            "is_complete": self.is_complete,
            "progress": round(self.progress(), 2),
            "order_index": self.order_index,
        }


@dataclass
class QuestReward:
    """Reward for completing a quest."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    reward_type: RewardType = RewardType.EXPERIENCE
    amount: float = 100.0
    item_id: str = ""
    item_name: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "reward_type": self.reward_type.value,
            "amount": self.amount,
            "item_id": self.item_id,
            "item_name": self.item_name,
            "description": self.description,
        }


@dataclass
class Quest:
    """A complete quest definition."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    category: QuestCategory = QuestCategory.SIDE_QUEST
    status: QuestStatus = QuestStatus.AVAILABLE
    difficulty: DifficultyLevel = DifficultyLevel.NORMAL
    description: str = ""
    story_hook: str = ""
    giver_id: str = ""
    objectives: List[QuestObjective] = field(default_factory=list)
    rewards: List[QuestReward] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    follow_ups: List[str] = field(default_factory=list)
    min_level: int = 1
    max_level: int = 100
    time_limit: float = 0.0
    is_repeatable: bool = False
    created_at: float = field(default_factory=_time_module.time)
    completed_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def progress(self) -> float:
        if not self.objectives:
            return 0.0
        required = [o for o in self.objectives if not o.is_optional]
        if not required:
            return 0.0
        completed = sum(1 for o in required if o.is_complete)
        return completed / len(required)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category.value,
            "status": self.status.value,
            "difficulty": self.difficulty.value,
            "description": self.description,
            "story_hook": self.story_hook,
            "giver_id": self.giver_id,
            "objective_count": len(self.objectives),
            "reward_count": len(self.rewards),
            "progress": round(self.progress(), 2),
            "min_level": self.min_level,
            "is_repeatable": self.is_repeatable,
            "objectives": [o.to_dict() for o in self.objectives],
            "rewards": [r.to_dict() for r in self.rewards],
        }


class AgentQuestGenerator:
    """
    Dynamic quest generation system.
    Singleton pattern with thread-safe initialization.
    """

    _instance: Optional["AgentQuestGenerator"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "AgentQuestGenerator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentQuestGenerator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._quests: Dict[str, Quest] = {}
        self._quest_dependencies: Dict[str, Set[str]] = {}
        self._total_generated: int = 0
        self._objective_templates: Dict[QuestCategory, List[Tuple[ObjectiveType, int, str]]] = {}
        self._setup_templates()

    def _setup_templates(self) -> None:
        self._objective_templates = {
            QuestCategory.FETCH: [
                (ObjectiveType.COLLECT, 3, "Gather {item} from {location}"),
                (ObjectiveType.DELIVER, 1, "Deliver {item} to {npc}"),
            ],
            QuestCategory.ELIMINATION: [
                (ObjectiveType.KILL, 5, "Defeat {count} {enemy}"),
                (ObjectiveType.REACH, 1, "Report to {npc}"),
            ],
            QuestCategory.EXPLORATION: [
                (ObjectiveType.REACH, 3, "Discover {location}"),
                (ObjectiveType.INVESTIGATE, 1, "Investigate {clue}"),
            ],
            QuestCategory.ESCORT: [
                (ObjectiveType.ESCORT_TO, 1, "Escort {npc} to {location}"),
                (ObjectiveType.PROTECT, 1, "Protect {npc} from danger"),
            ],
            QuestCategory.DEFENSE: [
                (ObjectiveType.DEFEND, 1, "Defend {location}"),
                (ObjectiveType.KILL, 10, "Defeat {count} waves of enemies"),
            ],
            QuestCategory.BOSS_BATTLE: [
                (ObjectiveType.KILL, 1, "Defeat {boss_name}"),
                (ObjectiveType.COLLECT, 1, "Claim the {item}"),
            ],
        }

    def generate_quest(
        self,
        title: str = "",
        category: QuestCategory = QuestCategory.SIDE_QUEST,
        difficulty: DifficultyLevel = DifficultyLevel.NORMAL,
        giver_id: str = "",
        min_level: int = 1,
        description: str = "",
        is_repeatable: bool = False,
    ) -> Quest:
        with self._lock:
            quest = Quest(
                title=title or f"Quest: {category.value.replace('_', ' ').title()}",
                category=category,
                difficulty=difficulty,
                giver_id=giver_id,
                min_level=min_level,
                description=description or f"A {category.value} quest for level {min_level}+ adventurers.",
                story_hook=self._generate_story_hook(category),
                is_repeatable=is_repeatable,
            )

            quest.objectives = self._generate_objectives(category, difficulty)
            quest.rewards = self._calculate_rewards(difficulty, len(quest.objectives))

            self._quests[quest.id] = quest
            self._quest_dependencies[quest.id] = set()
            self._total_generated += 1
            return quest

    def _generate_story_hook(self, category: QuestCategory) -> str:
        hooks = {
            QuestCategory.FETCH: "A mysterious stranger needs your help retrieving a lost artifact.",
            QuestCategory.ELIMINATION: "Dangerous creatures have been terrorizing the village.",
            QuestCategory.EXPLORATION: "An ancient map points to undiscovered ruins in the wilderness.",
            QuestCategory.ESCORT: "A merchant caravan needs protection through dangerous territory.",
            QuestCategory.DEFENSE: "The settlement is under threat and needs defenders.",
            QuestCategory.BOSS_BATTLE: "A powerful foe has emerged, challenging all who dare.",
            QuestCategory.MAIN_STORY: "The fate of the world hangs in the balance.",
            QuestCategory.PUZZLE: "Ancient mechanisms guard a long-forgotten secret.",
            QuestCategory.DELIVERY: "An urgent delivery must reach its destination.",
            QuestCategory.COLLECTION: "A collector seeks rare specimens from across the land.",
        }
        return hooks.get(category, "An adventure awaits those bold enough to accept.")

    def _generate_objectives(
        self, category: QuestCategory, difficulty: DifficultyLevel
    ) -> List[QuestObjective]:
        templates = self._objective_templates.get(
            category,
            [(ObjectiveType.COLLECT, 3, "Complete the task"), (ObjectiveType.REACH, 1, "Return to quest giver")],
        )

        diff_multiplier = {
            DifficultyLevel.TRIVIAL: 0.5,
            DifficultyLevel.EASY: 0.75,
            DifficultyLevel.NORMAL: 1.0,
            DifficultyLevel.HARD: 1.5,
            DifficultyLevel.EPIC: 2.0,
            DifficultyLevel.LEGENDARY: 3.0,
        }
        multiplier = diff_multiplier.get(difficulty, 1.0)

        objectives = []
        for i, (obj_type, base_count, desc_template) in enumerate(templates):
            count = max(1, int(base_count * multiplier))
            objective = QuestObjective(
                objective_type=obj_type,
                description=desc_template,
                target_count=count,
                is_optional=(i > 0 and random.random() < 0.3),
                order_index=i,
            )
            objectives.append(objective)
        return objectives

    def _calculate_rewards(
        self, difficulty: DifficultyLevel, objective_count: int
    ) -> List[QuestReward]:
        base_xp = 50 * objective_count
        base_gold = 25 * objective_count

        diff_multiplier = {
            DifficultyLevel.TRIVIAL: 0.3,
            DifficultyLevel.EASY: 0.6,
            DifficultyLevel.NORMAL: 1.0,
            DifficultyLevel.HARD: 1.8,
            DifficultyLevel.EPIC: 3.0,
            DifficultyLevel.LEGENDARY: 5.0,
        }
        multiplier = diff_multiplier.get(difficulty, 1.0)

        rewards = [
            QuestReward(
                reward_type=RewardType.EXPERIENCE,
                amount=base_xp * multiplier,
                description=f"{int(base_xp * multiplier)} experience points",
            ),
            QuestReward(
                reward_type=RewardType.GOLD,
                amount=base_gold * multiplier,
                description=f"{int(base_gold * multiplier)} gold",
            ),
        ]

        if difficulty in (DifficultyLevel.EPIC, DifficultyLevel.LEGENDARY):
            rewards.append(QuestReward(
                reward_type=RewardType.ITEM,
                item_name=f"Rare Item ({difficulty.value})",
                description=f"A {difficulty.value} reward item",
            ))

        return rewards

    def activate_quest(self, quest_id: str) -> bool:
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None or quest.status != QuestStatus.AVAILABLE:
                return False
            for prereq_id in quest.prerequisites:
                prereq = self._quests.get(prereq_id)
                if prereq is None or prereq.status != QuestStatus.COMPLETED:
                    return False
            quest.status = QuestStatus.ACTIVE
            return True

    def complete_objective(self, quest_id: str, objective_id: str) -> bool:
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return False
            for obj in quest.objectives:
                if obj.id == objective_id:
                    obj.current_count = obj.target_count
                    obj.is_complete = True
                    break
            if all(o.is_complete or o.is_optional for o in quest.objectives):
                quest.status = QuestStatus.COMPLETED
                quest.completed_at = _time_module.time()
            return True

    def progress_objective(
        self, quest_id: str, objective_id: str, amount: int = 1
    ) -> bool:
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return False
            for obj in quest.objectives:
                if obj.id == objective_id:
                    obj.current_count = min(obj.target_count, obj.current_count + amount)
                    if obj.current_count >= obj.target_count:
                        obj.is_complete = True
                    break
            if all(o.is_complete or o.is_optional for o in quest.objectives):
                quest.status = QuestStatus.COMPLETED
                quest.completed_at = _time_module.time()
            return True

    def fail_quest(self, quest_id: str) -> bool:
        with self._lock:
            quest = self._quests.get(quest_id)
            if quest is None:
                return False
            quest.status = QuestStatus.FAILED
            return True

    def add_dependency(self, quest_id: str, prerequisite_id: str) -> bool:
        with self._lock:
            if quest_id not in self._quests or prerequisite_id not in self._quests:
                return False
            self._quest_dependencies.setdefault(quest_id, set()).add(prerequisite_id)
            self._quests[quest_id].prerequisites.append(prerequisite_id)
            return True

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        return self._quests.get(quest_id)

    def get_available_quests(
        self, player_level: int = 1, category: Optional[QuestCategory] = None
    ) -> List[Quest]:
        available = []
        for quest in self._quests.values():
            if quest.status != QuestStatus.AVAILABLE:
                continue
            if player_level < quest.min_level or player_level > quest.max_level:
                continue
            if category and quest.category != category:
                continue
            available.append(quest)
        return available

    def get_active_quests(self) -> List[Quest]:
        return [q for q in self._quests.values() if q.status == QuestStatus.ACTIVE]

    def get_completed_quests(self) -> List[Quest]:
        return [q for q in self._quests.values() if q.status == QuestStatus.COMPLETED]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            status_counts = {}
            for q in self._quests.values():
                status_counts[q.status.value] = status_counts.get(q.status.value, 0) + 1

            cat_counts = {}
            for q in self._quests.values():
                cat_counts[q.category.value] = cat_counts.get(q.category.value, 0) + 1

            return {
                "total_quests": self._total_generated,
                "active_quests": len(self.get_active_quests()),
                "completed_quests": len(self.get_completed_quests()),
                "status_distribution": status_counts,
                "category_distribution": cat_counts,
            }

    def get_all_quests(self, limit: int = 20) -> List[Dict[str, Any]]:
        quests = list(self._quests.values())[:limit]
        return [q.to_dict() for q in quests]


def get_quest_generator() -> AgentQuestGenerator:
    return AgentQuestGenerator.get_instance()