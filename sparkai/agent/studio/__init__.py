"""
SparkAI Agent - Studio Hierarchy

A coordinated team of specialized game development agents
organized into a studio hierarchy with three tiers:
  Tier 1 - Directors: Strategic vision and coordination
  Tier 2 - Leads: Domain ownership and team management
  Tier 3 - Specialists: Focused execution in specific domains

Each agent has defined responsibilities, quality gates,
and escalation paths within the studio structure.
"""

from sparkai.agent.studio.directors import (
    CreativeDirector,
    TechnicalDirector,
    Producer,
)
from sparkai.agent.studio.leads import (
    GameDesigner,
    LeadProgrammer,
    ArtDirector,
    NarrativeDirector,
    QALead,
)
from sparkai.agent.studio.specialists import (
    GameplayProgrammer,
    EngineProgrammer,
    AIProgrammer,
    LevelDesigner,
    WorldBuilder,
    SoundDesigner,
    Writer,
    QATester,
)

__all__ = [
    "CreativeDirector",
    "TechnicalDirector",
    "Producer",
    "GameDesigner",
    "LeadProgrammer",
    "ArtDirector",
    "NarrativeDirector",
    "QALead",
    "GameplayProgrammer",
    "EngineProgrammer",
    "AIProgrammer",
    "LevelDesigner",
    "WorldBuilder",
    "SoundDesigner",
    "Writer",
    "QATester",
]
