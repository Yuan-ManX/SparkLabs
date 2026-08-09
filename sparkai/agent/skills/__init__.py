"""
SparkAI Agent - Game Skill System"""

from sparkai.agent.skills.base import Skill, SkillRegistry
from sparkai.agent.skills.template import TemplateSkill, TemplateLibrary
from sparkai.agent.skills.debug import DebugSkill, DebugProtocol

__all__ = [
    "Skill",
    "SkillRegistry",
    "TemplateSkill",
    "TemplateLibrary",
    "DebugSkill",
    "DebugProtocol",
]
