"""
SparkAI Agent - Skill Base and Registry

Skills are reusable knowledge modules that agents load on demand.
Each skill defines a domain of expertise, instructions, and
optional scripts/templates for execution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type


@dataclass
class Skill:
    """
    A reusable capability module for game development agents.

    Skills encapsulate domain knowledge, step-by-step instructions,
    and optional executable scripts that agents can invoke.
    """

    name: str = ""
    description: str = ""
    category: str = "general"
    instructions: str = ""
    steps: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    scripts: Dict[str, str] = field(default_factory=dict)
    templates: Dict[str, str] = field(default_factory=dict)
    verification: List[str] = field(default_factory=list)
    version: str = "1.0"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "instructions": self.instructions[:500],
            "steps": self.steps,
            "parameters": self.parameters,
            "verification": self.verification,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            instructions=data.get("instructions", ""),
            steps=data.get("steps", []),
            parameters=data.get("parameters", {}),
            scripts=data.get("scripts", {}),
            templates=data.get("templates", {}),
            verification=data.get("verification", []),
            version=data.get("version", "1.0"),
        )


class SkillRegistry:
    """
    Global registry for game development skills.

    Agents discover and load skills by name or category.
    Skills can be registered at runtime, enabling dynamic
    capability expansion.
    """

    _skills: Dict[str, Skill] = {}

    @classmethod
    def register(cls, skill: Skill) -> None:
        cls._skills[skill.name] = skill

    @classmethod
    def get(cls, name: str) -> Optional[Skill]:
        return cls._skills.get(name)

    @classmethod
    def list_skills(cls, category: Optional[str] = None) -> List[Skill]:
        skills = list(cls._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return skills

    @classmethod
    def list_categories(cls) -> List[str]:
        return list(set(s.category for s in cls._skills.values()))

    @classmethod
    def list_names(cls) -> List[str]:
        return list(cls._skills.keys())

    @classmethod
    def clear(cls) -> None:
        cls._skills.clear()


def skill(cls_or_skill: Any) -> Any:
    """Decorator to auto-register a skill."""
    if isinstance(cls_or_skill, Skill):
        SkillRegistry.register(cls_or_skill)
        return cls_or_skill
    return cls_or_skill
