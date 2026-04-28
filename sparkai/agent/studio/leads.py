"""
SparkAI Agent - Studio Leads (Tier 2)

Leads own their domain and coordinate specialists within it.
They can delegate to Tier 3 specialists and escalate to
Tier 1 directors when cross-domain coordination is needed.
"""

from sparkai.agent.base import SparkAgent, AgentCapability, AgentRole


class GameDesigner(SparkAgent):
    """
    Owns game design: mechanics, systems, balance, and player experience.
    Coordinates with level designers and gameplay programmers.
    """

    def __init__(self, agent_id=None):
        super().__init__(
            name="Game Designer",
            role=AgentRole.LEAD,
            capabilities=[
                AgentCapability.GAMEPLAY_DESIGN,
                AgentCapability.WORLD_BUILDING,
                AgentCapability.NARRATIVE_GENERATION,
                AgentCapability.QUALITY_REVIEW,
            ],
            agent_id=agent_id,
        )


class LeadProgrammer(SparkAgent):
    """
    Owns code architecture, engine integration, and technical standards.
    Coordinates with engine, AI, and gameplay programmers.
    """

    def __init__(self, agent_id=None):
        super().__init__(
            name="Lead Programmer",
            role=AgentRole.LEAD,
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.SCENE_MANAGEMENT,
                AgentCapability.QUALITY_REVIEW,
                AgentCapability.TESTING,
            ],
            agent_id=agent_id,
        )


class ArtDirector(SparkAgent):
    """
    Owns visual style, asset pipeline, and art quality.
    Coordinates with technical artists and asset generators.
    """

    def __init__(self, agent_id=None):
        super().__init__(
            name="Art Director",
            role=AgentRole.LEAD,
            capabilities=[
                AgentCapability.ASSET_GENERATION,
                AgentCapability.QUALITY_REVIEW,
                AgentCapability.WORLD_BUILDING,
            ],
            agent_id=agent_id,
        )


class NarrativeDirector(SparkAgent):
    """
    Owns story, dialogue, quests, and narrative systems.
    Coordinates with writers and NPC designers.
    """

    def __init__(self, agent_id=None):
        super().__init__(
            name="Narrative Director",
            role=AgentRole.LEAD,
            capabilities=[
                AgentCapability.NARRATIVE_GENERATION,
                AgentCapability.NPC_CONTROL,
                AgentCapability.WORLD_BUILDING,
                AgentCapability.QUALITY_REVIEW,
            ],
            agent_id=agent_id,
        )


class QALead(SparkAgent):
    """
    Owns quality assurance: testing, bug triage, and release readiness.
    Coordinates with QA testers and performance analysts.
    """

    def __init__(self, agent_id=None):
        super().__init__(
            name="QA Lead",
            role=AgentRole.LEAD,
            capabilities=[
                AgentCapability.QUALITY_REVIEW,
                AgentCapability.TESTING,
                AgentCapability.CODE_GENERATION,
            ],
            agent_id=agent_id,
        )
