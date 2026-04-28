"""
SparkAI Agent - Game Skill System

Reusable, evolving capabilities for game development.
Skills are composable knowledge modules that agents can load on demand.

Two core skill types:
  - TemplateSkill: Project scaffolding patterns that grow from experience
  - DebugSkill: Verified fix protocols that maintain a living knowledge base

Skills enable agents to scaffold stable architectures and systematically
repair integration errors rather than patching isolated syntax bugs.
"""

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
