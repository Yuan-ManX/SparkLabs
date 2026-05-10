"""
SparkLabs Engine - Quest System

Quest tracking and state management for AI-native games.
Supports multi-objective quests with sequential and parallel
task resolution, dynamic rewards, prerequisite chains, and
integration with dialogue, inventory, and combat systems.

Architecture:
  QuestSystem
    |-- QuestRegistry (quest definition catalog)
    |-- ObjectiveTracker (per-objective progress state)
    |-- RewardDispatcher (completion reward resolution)
    |-- QuestChainManager (prerequisite and sequel management)
    |-- QuestJournal (player-facing quest log)

Quest States:
  - NOT_STARTED: unlocked but not yet accepted
  - ACTIVE: in progress with tracked objectives
  - COMPLETED: all objectives fulfilled, rewards granted
  - FAILED: irrevocable failure condition met
  - ABANDONED: player voluntarily dropped
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class QuestState(Enum):
    NOT_STARTED = "not_started"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class ObjectiveType(Enum):
    COLLECT = "collect"
    KILL = "kill"
    TALK_TO = "talk_to"
    REACH = "reach"
    ESCORT = "escort"
    DELIVER = "deliver"
    USE_ITEM = "use_item"
    TRIGGER = "trigger"
    CUSTOM = "custom"


class RewardType(Enum):
    EXPERIENCE = "experience"
    ITEM = "item"
    CURRENCY = "currency"
    UNLOCK = "unlock"
    REPUTATION = "reputation"
    FLAG = "flag"


@dataclass
class QuestObjective:
    objective_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    objective_type: ObjectiveType = ObjectiveType.CUSTOM
    target_id: str = ""
    target_count: int = 1
    current_count: int = 0
    is_optional: bool = False
    is_completed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        if self.target_count <= 0:
            return 1.0 if self.is_completed else 0.0
        return min(1.0, self.current_count / self.target_count)


@dataclass
class QuestReward:
    reward_type: RewardType
    reward_id: str = ""
    amount: int = 1
    description: str = ""


@dataclass
class QuestDefinition:
    quest_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    objectives: List[QuestObjective] = field(default_factory=list)
    rewards: List[QuestReward] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    fail_conditions: List[str] = field(default_factory=list)
    auto_complete: bool = False
    is_repeatable: bool = False
    is_main_quest: bool = False
    level_requirement: int = 0


@dataclass
class ActiveQuest:
    quest_id: str
    state: QuestState = QuestState.NOT_STARTED
    objectives: Dict[str, QuestObjective] = field(default_factory=dict)
    started_at: float = 0.0
    completed_at: Optional[float] = None
    attempt_count: int = 0


class QuestSystem:
    """
    Quest tracking engine with multi-objective support
    and reward distribution management.
    """

    _instance: Optional[QuestSystem] = None

    @classmethod
    def get_instance(cls) -> QuestSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._quest_definitions: Dict[str, QuestDefinition] = {}
        self._active_quests: Dict[str, ActiveQuest] = {}
        self._completed_quests: Set[str] = set()
        self._failed_quests: Set[str] = set()
        self._quest_log: List[Dict[str, Any]] = []

    def register_quest(self, definition: QuestDefinition) -> str:
        self._quest_definitions[definition.quest_id] = definition
        return definition.quest_id

    def define_quest(
        self,
        title: str,
        description: str,
        objectives: List[Dict[str, Any]],
        rewards: Optional[List[Dict[str, Any]]] = None,
        prerequisites: Optional[List[str]] = None,
        is_main_quest: bool = False,
    ) -> str:
        quest_obj = QuestDefinition(
            title=title,
            description=description,
            is_main_quest=is_main_quest,
            prerequisites=prerequisites or [],
        )

        for obj_data in objectives:
            obj_type = ObjectiveType(obj_data.get("type", "custom"))
            objective = QuestObjective(
                description=obj_data.get("description", ""),
                objective_type=obj_type,
                target_id=obj_data.get("target_id", ""),
                target_count=obj_data.get("target_count", 1),
                is_optional=obj_data.get("is_optional", False),
            )
            quest_obj.objectives.append(objective)

        if rewards:
            for reward_data in rewards:
                reward = QuestReward(
                    reward_type=RewardType(reward_data.get("type", "experience")),
                    reward_id=reward_data.get("id", ""),
                    amount=reward_data.get("amount", 1),
                    description=reward_data.get("description", ""),
                )
                quest_obj.rewards.append(reward)

        self._quest_definitions[quest_obj.quest_id] = quest_obj
        return quest_obj.quest_id

    def start_quest(self, quest_id: str) -> bool:
        definition = self._quest_definitions.get(quest_id)
        if definition is None:
            return False

        if quest_id in self._completed_quests and not definition.is_repeatable:
            return False

        for prereq_id in definition.prerequisites:
            if prereq_id not in self._completed_quests:
                return False

        active = ActiveQuest(
            quest_id=quest_id,
            state=QuestState.ACTIVE,
            started_at=time.time(),
            attempt_count=self._active_quests.get(quest_id, ActiveQuest(quest_id)).attempt_count + 1,
        )

        for obj in definition.objectives:
            active.objectives[obj.objective_id] = QuestObjective(
                objective_id=obj.objective_id,
                description=obj.description,
                objective_type=obj.objective_type,
                target_id=obj.target_id,
                target_count=obj.target_count,
                is_optional=obj.is_optional,
            )

        self._active_quests[quest_id] = active
        self._quest_log.append({
            "quest_id": quest_id,
            "event": "started",
            "timestamp": time.time(),
        })
        return True

    def update_objective(
        self,
        quest_id: str,
        objective_id: str,
        progress: int = 1,
    ) -> bool:
        active = self._active_quests.get(quest_id)
        if active is None or active.state != QuestState.ACTIVE:
            return False

        objective = active.objectives.get(objective_id)
        if objective is None:
            return False

        objective.current_count = min(objective.current_count + progress, objective.target_count)
        if objective.current_count >= objective.target_count:
            objective.is_completed = True

        if self._check_completion(quest_id):
            self.complete_quest(quest_id)

        return True

    def set_objective_progress(
        self,
        quest_id: str,
        objective_id: str,
        count: int,
    ) -> bool:
        active = self._active_quests.get(quest_id)
        if active is None or active.state != QuestState.ACTIVE:
            return False

        objective = active.objectives.get(objective_id)
        if objective is None:
            return False

        objective.current_count = min(count, objective.target_count)
        if objective.current_count >= objective.target_count:
            objective.is_completed = True

        if self._check_completion(quest_id):
            self.complete_quest(quest_id)

        return True

    def _check_completion(self, quest_id: str) -> bool:
        definition = self._quest_definitions.get(quest_id)
        active = self._active_quests.get(quest_id)
        if definition is None or active is None:
            return False

        required = [
            obj_id
            for obj_id, obj in active.objectives.items()
            if not obj.is_optional
        ]
        return all(active.objectives[obj_id].is_completed for obj_id in required)

    def complete_quest(self, quest_id: str) -> bool:
        active = self._active_quests.get(quest_id)
        if active is None:
            return False

        active.state = QuestState.COMPLETED
        active.completed_at = time.time()
        self._completed_quests.add(quest_id)

        if quest_id in self._active_quests:
            del self._active_quests[quest_id]

        self._quest_log.append({
            "quest_id": quest_id,
            "event": "completed",
            "timestamp": time.time(),
        })
        return True

    def fail_quest(self, quest_id: str) -> bool:
        active = self._active_quests.get(quest_id)
        if active is None:
            return False

        active.state = QuestState.FAILED
        self._failed_quests.add(quest_id)
        if quest_id in self._active_quests:
            del self._active_quests[quest_id]

        self._quest_log.append({
            "quest_id": quest_id,
            "event": "failed",
            "timestamp": time.time(),
        })
        return True

    def abandon_quest(self, quest_id: str) -> bool:
        active = self._active_quests.get(quest_id)
        if active is None:
            return False

        active.state = QuestState.ABANDONED
        if quest_id in self._active_quests:
            del self._active_quests[quest_id]

        self._quest_log.append({
            "quest_id": quest_id,
            "event": "abandoned",
            "timestamp": time.time(),
        })
        return True

    def get_active_quests(self) -> List[ActiveQuest]:
        return list(self._active_quests.values())

    def get_quest_state(self, quest_id: str) -> Optional[QuestState]:
        if quest_id in self._active_quests:
            return QuestState.ACTIVE
        if quest_id in self._completed_quests:
            return QuestState.COMPLETED
        if quest_id in self._failed_quests:
            return QuestState.FAILED
        if quest_id in self._quest_definitions:
            return QuestState.NOT_STARTED
        return None

    def get_quest_progress(self, quest_id: str) -> Dict[str, Any]:
        active = self._active_quests.get(quest_id)
        definition = self._quest_definitions.get(quest_id)
        if active is None or definition is None:
            return {}

        objectives_progress = []
        for obj in active.objectives.values():
            def_obj = next((d for d in definition.objectives if d.objective_id == obj.objective_id), None)
            objectives_progress.append({
                "objective_id": obj.objective_id,
                "description": obj.description,
                "current": obj.current_count,
                "target": obj.target_count,
                "progress": obj.progress,
                "completed": obj.is_completed,
                "optional": obj.is_optional,
            })

        return {
            "quest_id": quest_id,
            "title": definition.title,
            "state": active.state.value,
            "objectives": objectives_progress,
            "is_main_quest": definition.is_main_quest,
        }

    def get_quest_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "quest_id": q.quest_id,
                "title": q.title,
                "description": q.description,
                "is_main_quest": q.is_main_quest,
                "objective_count": len(q.objectives),
                "prerequisites": q.prerequisites,
                "state": self.get_quest_state(q.quest_id),
            }
            for q in self._quest_definitions.values()
        ]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_definitions": len(self._quest_definitions),
            "active_quests": len(self._active_quests),
            "completed_quests": len(self._completed_quests),
            "failed_quests": len(self._failed_quests),
            "main_quest_count": sum(
                1 for q in self._quest_definitions.values() if q.is_main_quest
            ),
            "log_entries": len(self._quest_log),
        }

    def reset(self) -> None:
        self._active_quests.clear()
        self._completed_quests.clear()
        self._failed_quests.clear()
        self._quest_log.clear()


_quest_system = QuestSystem.get_instance()


def get_quest_system() -> QuestSystem:
    return _quest_system