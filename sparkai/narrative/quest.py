"""
SparkAI Narrative - Quest Generation System
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class QuestType(Enum):
    MAIN = "main"
    SIDE = "side"
    DAILY = "daily"
    CHAIN = "chain"
    HIDDEN = "hidden"


class QuestStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QuestObjective:
    description: str = ""
    target: str = ""
    current_progress: int = 0
    required_progress: int = 1
    optional: bool = False

    def is_complete(self) -> bool:
        return self.current_progress >= self.required_progress

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "target": self.target,
            "current_progress": self.current_progress,
            "required_progress": self.required_progress,
            "optional": self.optional,
        }


@dataclass
class QuestReward:
    experience: int = 0
    gold: int = 0
    items: List[str] = field(default_factory=list)
    unlock_quest: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experience": self.experience,
            "gold": self.gold,
            "items": self.items,
            "unlock_quest": self.unlock_quest,
        }


@dataclass
class QuestTemplate:
    name: str = ""
    quest_type: QuestType = QuestType.SIDE
    description: str = ""
    objectives: List[str] = field(default_factory=list)
    rewards: Dict[str, Any] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)
    genre: str = "fantasy"


class QuestGenerator:
    """
    Procedural quest generation system.
    Creates quests from templates with dynamic objectives and rewards.
    """

    def __init__(self):
        self._templates: Dict[str, QuestTemplate] = {}
        self._generated_quests: Dict[str, Dict] = {}
        self._register_default_templates()

    def register_template(self, template: QuestTemplate) -> None:
        self._templates[template.name] = template

    def generate_quest(
        self,
        template_name: str,
        name: Optional[str] = None,
        quest_type: Optional[QuestType] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        template = self._templates.get(template_name)
        if not template:
            return {"error": f"Template '{template_name}' not found"}

        quest_id = str(uuid.uuid4())
        objectives = []
        for obj_desc in template.objectives:
            desc = self._customize_text(obj_desc, context or {})
            objectives.append(QuestObjective(
                description=desc,
                target=self._extract_target(desc),
                required_progress=self._estimate_progress(desc),
            ))

        rewards = QuestReward(
            experience=template.rewards.get("experience", 100),
            gold=template.rewards.get("gold", 50),
            items=template.rewards.get("items", []),
        )

        quest = {
            "id": quest_id,
            "name": name or template.name,
            "type": (quest_type or template.quest_type).value,
            "description": self._customize_text(template.description, context or {}),
            "status": QuestStatus.NOT_STARTED.value,
            "objectives": [o.to_dict() for o in objectives],
            "rewards": rewards.to_dict(),
            "prerequisites": template.prerequisites,
            "genre": template.genre,
        }

        self._generated_quests[quest_id] = quest
        return quest

    def list_templates(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "type": t.quest_type.value,
                "description": t.description,
                "genre": t.genre,
            }
            for t in self._templates.values()
        ]

    def get_quest(self, quest_id: str) -> Optional[Dict[str, Any]]:
        return self._generated_quests.get(quest_id)

    def _register_default_templates(self) -> None:
        self.register_template(QuestTemplate(
            name="hunt", quest_type=QuestType.SIDE, genre="fantasy",
            description="Hunt {target_creature} in the {location}.",
            objectives=["Defeat {count} {target_creature}", "Collect {count} {drop_item}"],
            rewards={"experience": 150, "gold": 75},
        ))
        self.register_template(QuestTemplate(
            name="fetch", quest_type=QuestType.SIDE, genre="fantasy",
            description="Retrieve the {item_name} from {location}.",
            objectives=["Travel to {location}", "Find the {item_name}", "Return to {quest_giver}"],
            rewards={"experience": 100, "gold": 50},
        ))
        self.register_template(QuestTemplate(
            name="escort", quest_type=QuestType.SIDE, genre="fantasy",
            description="Escort {npc_name} safely to {destination}.",
            objectives=["Meet {npc_name}", "Protect {npc_name} from enemies", "Reach {destination}"],
            rewards={"experience": 200, "gold": 100},
        ))
        self.register_template(QuestTemplate(
            name="investigate", quest_type=QuestType.MAIN, genre="fantasy",
            description="Investigate the mysterious {event} at {location}.",
            objectives=["Travel to {location}", "Search for clues about {event}", "Report findings"],
            rewards={"experience": 300, "gold": 150},
        ))
        self.register_template(QuestTemplate(
            name="defend", quest_type=QuestType.MAIN, genre="fantasy",
            description="Defend {location} from the {enemy} invasion.",
            objectives=["Prepare defenses at {location}", "Survive {count} waves of {enemy}", "Defeat the {enemy} leader"],
            rewards={"experience": 400, "gold": 200},
        ))
        self.register_template(QuestTemplate(
            name="puzzle", quest_type=QuestType.SIDE, genre="fantasy",
            description="Solve the ancient puzzle in {location}.",
            objectives=["Find the puzzle room in {location}", "Solve the {count} riddles", "Unlock the treasure"],
            rewards={"experience": 250, "gold": 120},
        ))

    def _customize_text(self, text: str, context: Dict[str, Any]) -> str:
        for key, value in context.items():
            placeholder = "{" + key + "}"
            text = text.replace(placeholder, str(value))
        return text

    def _extract_target(self, description: str) -> str:
        words = description.split()
        for i, word in enumerate(words):
            if word.lower() in ["defeat", "find", "collect", "defeat", "search", "protect"]:
                if i + 1 < len(words):
                    return words[i + 1]
        return "target"

    def _estimate_progress(self, description: str) -> int:
        import re
        numbers = re.findall(r"\d+", description)
        if numbers:
            return int(numbers[0])
        return 1
