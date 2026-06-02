"""
SparkLabs Agent - Quest Composer

AI-driven quest and mission chain composition system with branching
narratives. Generates complete quest structures — single quests, multi-step
quest chains, branching decision points, and balanced reward distributions —
all managed through a singleton composition engine.

Architecture:
  AgentQuestComposer (singleton)
    |-- QuestObjective (individual task within a quest)
    |-- QuestNode (single quest with objectives and rewards)
    |-- QuestChain (ordered or branching sequence of quests)
    |-- BranchingCondition (narrative decision point logic)
    |-- RewardBundle (structured reward package)
    |-- QuestNarrative (dialogue, lore, and character arc integration)
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


class QuestType(Enum):
    MAIN_STORY = "main_story"
    SIDE_QUEST = "side_quest"
    FACTION_QUEST = "faction_quest"
    COMPANION_QUEST = "companion_quest"
    RANDOM_ENCOUNTER = "random_encounter"
    DAILY_CHALLENGE = "daily_challenge"
    GUILD_CONTRACT = "guild_contract"
    WORLD_EVENT = "world_event"
    HIDDEN_QUEST = "hidden_quest"
    ESCORT = "escort"


class QuestStatus(Enum):
    NOT_STARTED = "not_started"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"
    LOCKED = "locked"
    HIDDEN = "hidden"


class ObjectiveType(Enum):
    KILL = "kill"
    COLLECT = "collect"
    DELIVER = "deliver"
    ESCORT = "escort"
    INVESTIGATE = "investigate"
    CRAFT = "craft"
    DESTROY = "destroy"
    DEFEND = "defend"
    CAPTURE = "capture"
    NEGOTIATE = "negotiate"


class RewardCategory(Enum):
    EXPERIENCE = "experience"
    CURRENCY = "currency"
    ITEM = "item"
    REPUTATION = "reputation"
    SKILL = "skill"
    COMPANION = "companion"
    UNLOCK = "unlock"
    TITLE = "title"
    COSMETIC = "cosmetic"
    BLUEPRINT = "blueprint"


# ------------------------------------------------------------------
# Pre-defined quest templates keyed by QuestType
# ------------------------------------------------------------------

QUEST_TEMPLATES: Dict[QuestType, Dict[str, Any]] = {
    QuestType.MAIN_STORY: {
        "default_title": "Echoes of the Forgotten Realm",
        "default_objective_count": 4,
        "base_experience": 500,
        "base_currency": 150,
        "difficulty_modifier": 1.0,
        "narrative_tone": "epic",
        "estimated_duration_min": 45,
    },
    QuestType.SIDE_QUEST: {
        "default_title": "A Villager's Plea",
        "default_objective_count": 2,
        "base_experience": 120,
        "base_currency": 40,
        "difficulty_modifier": 0.6,
        "narrative_tone": "casual",
        "estimated_duration_min": 15,
    },
    QuestType.FACTION_QUEST: {
        "default_title": "Allegiance Forged in Shadow",
        "default_objective_count": 3,
        "base_experience": 300,
        "base_currency": 100,
        "difficulty_modifier": 0.8,
        "narrative_tone": "political",
        "estimated_duration_min": 30,
    },
    QuestType.COMPANION_QUEST: {
        "default_title": "Bound by Oath",
        "default_objective_count": 3,
        "base_experience": 250,
        "base_currency": 80,
        "difficulty_modifier": 0.7,
        "narrative_tone": "personal",
        "estimated_duration_min": 30,
    },
    QuestType.RANDOM_ENCOUNTER: {
        "default_title": "Strange Tidings on the Road",
        "default_objective_count": 1,
        "base_experience": 60,
        "base_currency": 15,
        "difficulty_modifier": 0.4,
        "narrative_tone": "surprise",
        "estimated_duration_min": 5,
    },
    QuestType.DAILY_CHALLENGE: {
        "default_title": "Today's Trial",
        "default_objective_count": 1,
        "base_experience": 80,
        "base_currency": 25,
        "difficulty_modifier": 0.5,
        "narrative_tone": "repeatable",
        "estimated_duration_min": 10,
    },
    QuestType.GUILD_CONTRACT: {
        "default_title": "Guild Missive: Contract Accepted",
        "default_objective_count": 2,
        "base_experience": 200,
        "base_currency": 120,
        "difficulty_modifier": 0.7,
        "narrative_tone": "professional",
        "estimated_duration_min": 20,
    },
    QuestType.WORLD_EVENT: {
        "default_title": "The Sky Shatters",
        "default_objective_count": 5,
        "base_experience": 800,
        "base_currency": 300,
        "difficulty_modifier": 1.3,
        "narrative_tone": "cataclysmic",
        "estimated_duration_min": 60,
    },
    QuestType.HIDDEN_QUEST: {
        "default_title": "Whispers Beneath the Stone",
        "default_objective_count": 2,
        "base_experience": 350,
        "base_currency": 200,
        "difficulty_modifier": 0.9,
        "narrative_tone": "mysterious",
        "estimated_duration_min": 20,
    },
    QuestType.ESCORT: {
        "default_title": "Safe Passage",
        "default_objective_count": 2,
        "base_experience": 180,
        "base_currency": 90,
        "difficulty_modifier": 0.65,
        "narrative_tone": "protective",
        "estimated_duration_min": 25,
    },
}

# ------------------------------------------------------------------
# Pre-defined reward tables keyed by player level bracket
# ------------------------------------------------------------------

REWARD_TABLES: Dict[str, Dict[str, Any]] = {
    "novice": {
        "level_range": (1, 10),
        "experience_scalar": 1.0,
        "currency_scalar": 1.0,
        "item_rarity_weights": {"common": 0.70, "uncommon": 0.25, "rare": 0.04, "epic": 0.01},
        "max_item_count": 1,
    },
    "adept": {
        "level_range": (11, 25),
        "experience_scalar": 2.5,
        "currency_scalar": 3.0,
        "item_rarity_weights": {"common": 0.40, "uncommon": 0.35, "rare": 0.18, "epic": 0.07},
        "max_item_count": 2,
    },
    "veteran": {
        "level_range": (26, 45),
        "experience_scalar": 6.0,
        "currency_scalar": 8.0,
        "item_rarity_weights": {"common": 0.15, "uncommon": 0.30, "rare": 0.35, "epic": 0.20},
        "max_item_count": 3,
    },
    "master": {
        "level_range": (46, 70),
        "experience_scalar": 14.0,
        "currency_scalar": 20.0,
        "item_rarity_weights": {"common": 0.05, "uncommon": 0.15, "rare": 0.35, "epic": 0.45},
        "max_item_count": 4,
    },
    "legendary": {
        "level_range": (71, 100),
        "experience_scalar": 30.0,
        "currency_scalar": 50.0,
        "item_rarity_weights": {"common": 0.00, "uncommon": 0.05, "rare": 0.25, "epic": 0.70},
        "max_item_count": 5,
    },
}

# ------------------------------------------------------------------
# Pre-defined narrative themes
# ------------------------------------------------------------------

NARRATIVE_THEMES: List[str] = [
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

NARRATIVE_ARC_TEMPLATES: Dict[str, List[str]] = {
    "hero_journey": [
        "call_to_action",
        "first_trial",
        "deepening_conflict",
        "crisis_point",
        "climactic_resolution",
    ],
    "mystery_unfolding": [
        "initial_discovery",
        "gathering_clues",
        "red_herring",
        "revelation",
        "confrontation",
    ],
    "faction_war": [
        "choosing_sides",
        "guerrilla_skirmish",
        "alliance_forging",
        "major_battle",
        "aftermath",
    ],
    "personal_vendetta": [
        "the_wrong",
        "hunting_the_trail",
        "moral_dilemma",
        "the_showdown",
        "forgiveness_or_destruction",
    ],
    "world_threat": [
        "omen_of_doom",
        "gathering_allies",
        "race_against_time",
        "siege_preparation",
        "final_stand",
    ],
}


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class QuestObjective:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    objective_type: ObjectiveType = ObjectiveType.KILL
    target_description: str = ""
    target_count: int = 1
    current_progress: int = 0
    is_optional: bool = False
    time_limit_sec: int = 0
    location_hint: str = ""
    completion_dialogue: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "objective_type": self.objective_type.value,
            "target_description": self.target_description,
            "target_count": self.target_count,
            "current_progress": self.current_progress,
            "is_optional": self.is_optional,
            "time_limit_sec": self.time_limit_sec,
            "location_hint": self.location_hint,
            "completion_dialogue": self.completion_dialogue,
        }


@dataclass
class BranchingCondition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    condition_type: str = "CHOICE"
    condition_data: Dict[str, Any] = field(default_factory=dict)
    true_quest_id: str = ""
    false_quest_id: str = ""
    default_quest_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "condition_type": self.condition_type,
            "condition_data": self.condition_data,
            "true_quest_id": self.true_quest_id,
            "false_quest_id": self.false_quest_id,
            "default_quest_id": self.default_quest_id,
        }


@dataclass
class RewardBundle:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    experience: int = 0
    currency_amount: int = 0
    currency_type: str = "gold"
    items: List[str] = field(default_factory=list)
    reputation_changes: Dict[str, int] = field(default_factory=dict)
    skill_unlocks: List[str] = field(default_factory=list)
    cosmetics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "experience": self.experience,
            "currency_amount": self.currency_amount,
            "currency_type": self.currency_type,
            "items": self.items,
            "reputation_changes": self.reputation_changes,
            "skill_unlocks": self.skill_unlocks,
            "cosmetics": self.cosmetics,
        }


@dataclass
class QuestNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    quest_type: QuestType = QuestType.SIDE_QUEST
    title: str = ""
    description: str = ""
    objectives: List[QuestObjective] = field(default_factory=list)
    rewards: List[RewardBundle] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    next_quests: List[str] = field(default_factory=list)
    npc_giver_id: str = ""
    min_level: int = 1
    faction_requirement: str = ""
    estimated_duration_min: int = 15
    branching_conditions: List[BranchingCondition] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "quest_type": self.quest_type.value,
            "title": self.title,
            "description": self.description,
            "objectives": [o.to_dict() for o in self.objectives],
            "rewards": [r.to_dict() for r in self.rewards],
            "prerequisites": self.prerequisites,
            "next_quests": self.next_quests,
            "npc_giver_id": self.npc_giver_id,
            "min_level": self.min_level,
            "faction_requirement": self.faction_requirement,
            "estimated_duration_min": self.estimated_duration_min,
            "branching_conditions": [b.to_dict() for b in self.branching_conditions],
        }


@dataclass
class QuestChain:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    root_quest_id: str = ""
    all_quests: List[QuestNode] = field(default_factory=list)
    narrative_theme: str = ""
    is_linear: bool = True
    total_quests: int = 0
    estimated_total_time: int = 0
    reward_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "root_quest_id": self.root_quest_id,
            "all_quests": [q.to_dict() for q in self.all_quests],
            "narrative_theme": self.narrative_theme,
            "is_linear": self.is_linear,
            "total_quests": self.total_quests,
            "estimated_total_time": self.estimated_total_time,
            "reward_summary": self.reward_summary,
        }


@dataclass
class QuestNarrative:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    quest_id: str = ""
    intro_text: str = ""
    progress_text: str = ""
    completion_text: str = ""
    failure_text: str = ""
    dialogues: List[Dict[str, str]] = field(default_factory=list)
    lore_hooks: List[str] = field(default_factory=list)
    character_arc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "quest_id": self.quest_id,
            "intro_text": self.intro_text,
            "progress_text": self.progress_text,
            "completion_text": self.completion_text,
            "failure_text": self.failure_text,
            "dialogues": self.dialogues,
            "lore_hooks": self.lore_hooks,
            "character_arc": self.character_arc,
        }


# ------------------------------------------------------------------
# Agent Quest Composer (Singleton)
# ------------------------------------------------------------------


class AgentQuestComposer:
    """AI-driven quest and mission chain composition system.

    Composes individual quests and multi-step quest chains with branching
    narrative support. Manages objective tracking, reward balancing,
    difficulty computation, and narrative dialogue generation across
    all quest types and narrative themes.
    """

    _instance: Optional[AgentQuestComposer] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> AgentQuestComposer:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> AgentQuestComposer:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._quests: Dict[str, QuestNode] = {}
        self._quest_chains: Dict[str, QuestChain] = {}
        self._narratives: Dict[str, QuestNarrative] = {}
        self._composition_log: List[Dict[str, Any]] = []

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        total_objectives = sum(
            len(q.objectives) for q in self._quests.values()
        )
        total_branches = sum(
            len(q.branching_conditions) for q in self._quests.values()
        )
        chain_quest_total = sum(
            c.total_quests for c in self._quest_chains.values()
        )
        return {
            "total_quests": len(self._quests),
            "total_quest_chains": len(self._quest_chains),
            "total_narratives": len(self._narratives),
            "total_objectives": total_objectives,
            "total_branching_conditions": total_branches,
            "chain_quest_total": chain_quest_total,
            "composition_log_entries": len(self._composition_log),
        }

    # --- Quest Composition ---

    def compose_quest(
        self,
        title: str,
        quest_type: QuestType,
        objectives: List[Dict[str, Any]],
        rewards: List[Dict[str, Any]],
    ) -> QuestNode:
        _time_module.sleep(0.001)
        template = QUEST_TEMPLATES.get(quest_type, QUEST_TEMPLATES[QuestType.SIDE_QUEST])
        title = title or template["default_title"]

        quest_objectives: List[QuestObjective] = []
        for obj_data in objectives:
            obj_type = ObjectiveType(obj_data.get("objective_type", "collect"))
            quest_objectives.append(
                QuestObjective(
                    objective_type=obj_type,
                    target_description=obj_data.get("target_description", ""),
                    target_count=obj_data.get("target_count", 1),
                    is_optional=obj_data.get("is_optional", False),
                    time_limit_sec=obj_data.get("time_limit_sec", 0),
                    location_hint=obj_data.get("location_hint", ""),
                    completion_dialogue=obj_data.get("completion_dialogue", ""),
                )
            )

        quest_rewards: List[RewardBundle] = []
        for rw_data in rewards:
            quest_rewards.append(
                RewardBundle(
                    experience=rw_data.get("experience", template["base_experience"]),
                    currency_amount=rw_data.get("currency_amount", template["base_currency"]),
                    currency_type=rw_data.get("currency_type", "gold"),
                    items=rw_data.get("items", []),
                    reputation_changes=rw_data.get("reputation_changes", {}),
                    skill_unlocks=rw_data.get("skill_unlocks", []),
                    cosmetics=rw_data.get("cosmetics", []),
                )
            )

        quest = QuestNode(
            quest_type=quest_type,
            title=title,
            description=f"{template['narrative_tone'].title()} quest: {title}",
            objectives=quest_objectives,
            rewards=quest_rewards,
            min_level=1,
            estimated_duration_min=template["estimated_duration_min"],
        )
        self._quests[quest.id] = quest
        self._composition_log.append({
            "action": "quest_composed",
            "quest_id": quest.id,
            "title": title,
            "quest_type": quest_type.value,
        })
        return quest

    def compose_quest_chain(
        self,
        name: str,
        theme: str,
        quest_count: int,
        narrative_arc: str,
    ) -> QuestChain:
        _time_module.sleep(0.001)
        if theme not in NARRATIVE_THEMES:
            theme = "discovery"

        arc_beats = NARRATIVE_ARC_TEMPLATES.get(
            narrative_arc,
            NARRATIVE_ARC_TEMPLATES["hero_journey"],
        )
        actual_count = min(quest_count, len(arc_beats))
        chain_quests: List[QuestNode] = []
        root_id = ""

        for index in range(actual_count):
            beat_name = arc_beats[index].replace("_", " ").title()
            quest_type = QuestType.MAIN_STORY
            if index == 0:
                quest_type = QuestType.MAIN_STORY
            elif index % 3 == 0:
                quest_type = QuestType.SIDE_QUEST

            template = QUEST_TEMPLATES[quest_type]
            obj = QuestObjective(
                objective_type=ObjectiveType.INVESTIGATE,
                target_description=f"Complete the '{beat_name}' story milestone",
                target_count=1,
            )
            rw = RewardBundle(
                experience=int(template["base_experience"] * (1 + index * 0.5)),
                currency_amount=int(template["base_currency"] * (1 + index * 0.3)),
            )
            quest = QuestNode(
                quest_type=quest_type,
                title=f"{name}: {beat_name}",
                description=f"Chapter {index + 1} of the {theme} saga",
                objectives=[obj],
                rewards=[rw],
                estimated_duration_min=template["estimated_duration_min"],
            )
            self._quests[quest.id] = quest
            chain_quests.append(quest)
            if index == 0:
                root_id = quest.id
            if index > 0:
                chain_quests[index - 1].next_quests.append(quest.id)
                quest.prerequisites.append(chain_quests[index - 1].id)

        total_time = sum(q.estimated_duration_min for q in chain_quests)
        total_exp = sum(
            (r.experience for q in chain_quests for r in q.rewards), 0
        )

        chain = QuestChain(
            name=name,
            root_quest_id=root_id,
            all_quests=chain_quests,
            narrative_theme=theme,
            is_linear=True,
            total_quests=len(chain_quests),
            estimated_total_time=total_time,
            reward_summary={
                "total_experience": total_exp,
                "quest_count": len(chain_quests),
                "theme": theme,
            },
        )
        self._quest_chains[chain.id] = chain
        self._composition_log.append({
            "action": "chain_composed",
            "chain_id": chain.id,
            "name": name,
            "quest_count": len(chain_quests),
        })
        return chain

    # --- Branching & Linking ---

    def add_branching_point(
        self,
        quest_id: str,
        branch_config: Dict[str, Any],
    ) -> Optional[BranchingCondition]:
        _time_module.sleep(0.001)
        quest = self._quests.get(quest_id)
        if quest is None:
            return None

        condition = BranchingCondition(
            condition_type=branch_config.get("condition_type", "CHOICE"),
            condition_data=branch_config.get("condition_data", {}),
            true_quest_id=branch_config.get("true_quest_id", ""),
            false_quest_id=branch_config.get("false_quest_id", ""),
            default_quest_id=branch_config.get("default_quest_id", ""),
        )
        quest.branching_conditions.append(condition)
        self._composition_log.append({
            "action": "branching_added",
            "quest_id": quest_id,
            "condition_type": condition.condition_type,
        })
        return condition

    def connect_quests(
        self,
        source_id: str,
        target_id: str,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> bool:
        _time_module.sleep(0.001)
        source = self._quests.get(source_id)
        target = self._quests.get(target_id)
        if source is None or target is None:
            return False
        if target_id not in source.next_quests:
            source.next_quests.append(target_id)
        if source_id not in target.prerequisites:
            target.prerequisites.append(source_id)
        if conditions:
            source.branching_conditions.append(
                BranchingCondition(
                    condition_type=conditions.get("condition_type", "CHOICE"),
                    condition_data=conditions.get("condition_data", {}),
                    true_quest_id=target_id,
                    default_quest_id=target_id,
                )
            )
        self._composition_log.append({
            "action": "quests_connected",
            "source_id": source_id,
            "target_id": target_id,
        })
        return True

    # --- Computation & Analysis ---

    def compute_difficulty_rating(self, quest: QuestNode) -> float:
        _time_module.sleep(0.001)
        template = QUEST_TEMPLATES.get(quest.quest_type, QUEST_TEMPLATES[QuestType.SIDE_QUEST])
        base = template["difficulty_modifier"] * 10.0
        objective_weight = len(quest.objectives) * 2.5
        min_level_weight = max(0, (quest.min_level - 1) * 0.5)
        objective_complexity = 0.0
        for obj in quest.objectives:
            if obj.target_count > 5:
                objective_complexity += 1.5
            if obj.time_limit_sec > 0:
                objective_complexity += 2.0
            if not obj.is_optional:
                objective_complexity += 1.0
        branch_weight = len(quest.branching_conditions) * 1.5
        rating = base + objective_weight + min_level_weight + objective_complexity + branch_weight
        return round(rating, 2)

    def compute_reward_balance(self, quest_chain_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        chain = self._quest_chains.get(quest_chain_id)
        if chain is None:
            return {"error": "chain_not_found"}

        quests = chain.all_quests
        total_exp = 0
        total_currency = 0
        all_items: List[str] = []
        for quest in quests:
            for rw in quest.rewards:
                total_exp += rw.experience
                total_currency += rw.currency_amount
                all_items.extend(rw.items)

        avg_exp_per_quest = total_exp / max(len(quests), 1)
        avg_currency_per_quest = total_currency / max(len(quests), 1)
        is_balanced = True
        for quest in quests:
            quest_exp = sum(r.experience for r in quest.rewards)
            if avg_exp_per_quest > 0:
                deviation = abs(quest_exp - avg_exp_per_quest) / avg_exp_per_quest
                if deviation > 0.5:
                    is_balanced = False
                    break

        return {
            "chain_id": quest_chain_id,
            "total_experience": total_exp,
            "total_currency": total_currency,
            "total_unique_items": len(set(all_items)),
            "average_exp_per_quest": round(avg_exp_per_quest, 2),
            "average_currency_per_quest": round(avg_currency_per_quest, 2),
            "is_balanced": is_balanced,
        }

    def generate_quest_dialogue(
        self,
        quest_id: str,
        character_id: str,
    ) -> Optional[QuestNarrative]:
        _time_module.sleep(0.001)
        quest = self._quests.get(quest_id)
        if quest is None:
            return None

        narrative = QuestNarrative(
            quest_id=quest_id,
            intro_text=f"A sense of purpose fills the air as you accept '{quest.title}'.",
            progress_text=f"Your journey through '{quest.title}' continues — stay vigilant.",
            completion_text=f"Triumph! '{quest.title}' has been completed. The realm remembers your deeds.",
            failure_text=f"'{quest.title}' has slipped from your grasp, but all is not lost.",
            dialogues=[
                {
                    "speaker": character_id,
                    "text": f"Are you ready to undertake '{quest.title}'?",
                    "stage": "intro",
                },
                {
                    "speaker": character_id,
                    "text": "Keep pushing forward. The task is not yet done.",
                    "stage": "progress",
                },
                {
                    "speaker": character_id,
                    "text": "Well done, adventurer. Your efforts will not be forgotten.",
                    "stage": "completion",
                },
            ],
            lore_hooks=[f"The legend of '{quest.title}' shall be etched into the chronicles."],
            character_arc=f"{character_id} grows through witnessing the resolution of '{quest.title}'.",
        )
        self._narratives[narrative.id] = narrative
        return narrative

    def validate_quest_chain_completion(self, chain_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        chain = self._quest_chains.get(chain_id)
        if chain is None:
            return {"valid": False, "error": "chain_not_found"}

        issues: List[str] = []
        quest_ids = {q.id for q in chain.all_quests}

        for quest in chain.all_quests:
            for prereq_id in quest.prerequisites:
                if prereq_id not in quest_ids:
                    issues.append(f"Quest {quest.id} has unknown prerequisite {prereq_id}")

        reachable: set = set()
        root = None
        for q in chain.all_quests:
            if q.id == chain.root_quest_id:
                root = q
                break
        if root is None:
            return {"valid": False, "error": "root_quest_not_in_chain"}

        stack = [root]
        while stack:
            current = stack.pop()
            if current.id in reachable:
                continue
            reachable.add(current.id)
            for next_id in current.next_quests:
                for q in chain.all_quests:
                    if q.id == next_id and q.id not in reachable:
                        stack.append(q)

        unreachable = quest_ids - reachable
        if unreachable:
            issues.append(f"Unreachable quests: {unreachable}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "reachable_count": len(reachable),
            "total_count": len(quest_ids),
        }

    def optimize_quest_pacing(self, chain_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        chain = self._quest_chains.get(chain_id)
        if chain is None:
            return {"error": "chain_not_found"}

        quests = chain.all_quests
        if not quests:
            return {"error": "empty_chain"}

        durations = [q.estimated_duration_min for q in quests]
        avg_duration = sum(durations) / len(durations)
        variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
        std_dev = math.sqrt(variance)

        pacing_score = 100.0
        if avg_duration > 0:
            cv = std_dev / avg_duration
            if cv > 0.8:
                pacing_score = max(10.0, 100.0 - (cv - 0.8) * 50.0)
            elif cv < 0.15:
                pacing_score = max(30.0, 100.0 - (0.15 - cv) * 100.0)

        adjustments: List[Dict[str, Any]] = []
        for quest in quests:
            if quest.estimated_duration_min > avg_duration * 1.8:
                adjustments.append({
                    "quest_id": quest.id,
                    "current_duration": quest.estimated_duration_min,
                    "suggested_duration": int(avg_duration * 1.5),
                    "action": "shorten",
                })
            elif quest.estimated_duration_min < avg_duration * 0.3:
                adjustments.append({
                    "quest_id": quest.id,
                    "current_duration": quest.estimated_duration_min,
                    "suggested_duration": int(avg_duration * 0.5),
                    "action": "extend",
                })

        return {
            "chain_id": chain_id,
            "average_duration_min": round(avg_duration, 1),
            "std_dev_min": round(std_dev, 1),
            "pacing_score": round(pacing_score, 1),
            "adjustments": adjustments,
            "total_quests": len(quests),
        }

    # --- Accessors ---

    def get_quest(self, quest_id: str) -> Optional[QuestNode]:
        _time_module.sleep(0.001)
        return self._quests.get(quest_id)

    def get_chain(self, chain_id: str) -> Optional[QuestChain]:
        _time_module.sleep(0.001)
        return self._quest_chains.get(chain_id)

    def get_narrative(self, narrative_id: str) -> Optional[QuestNarrative]:
        _time_module.sleep(0.001)
        return self._narratives.get(narrative_id)

    def list_quests(self) -> List[QuestNode]:
        _time_module.sleep(0.001)
        return list(self._quests.values())

    def list_chains(self) -> List[QuestChain]:
        _time_module.sleep(0.001)
        return list(self._quest_chains.values())

    def list_narratives(self) -> List[QuestNarrative]:
        _time_module.sleep(0.001)
        return list(self._narratives.values())


# ------------------------------------------------------------------
# Module-level convenience accessor
# ------------------------------------------------------------------


def get_agent_quest_composer() -> AgentQuestComposer:
    """Return the singleton AgentQuestComposer instance."""
    return AgentQuestComposer.get_instance()