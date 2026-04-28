"""
SparkAI Agent - Studio Directors (Tier 1)

Directors guard the creative and technical vision of the game.
They coordinate across departments and make strategic decisions.

Tier 1 agents have the broadest scope and can delegate to
any Tier 2 or Tier 3 agent.
"""

from sparkai.agent.base import SparkAgent, AgentCapability, AgentRole


class CreativeDirector(SparkAgent):
    """
    Guards the creative vision of the game.
    Coordinates design, narrative, and art direction.
    Ensures all game elements serve the core experience.
    """

    def __init__(self, agent_id=None):
        super().__init__(
            name="Creative Director",
            role=AgentRole.DIRECTOR,
            capabilities=[
                AgentCapability.WORKFLOW_ORCHESTRATION,
                AgentCapability.NARRATIVE_GENERATION,
                AgentCapability.GAMEPLAY_DESIGN,
                AgentCapability.WORLD_BUILDING,
                AgentCapability.QUALITY_REVIEW,
            ],
            agent_id=agent_id,
        )


class TechnicalDirector(SparkAgent):
    """
    Guards the technical architecture and performance.
    Coordinates engine, systems programming, and optimization.
    Ensures the game runs smoothly across target platforms.
    """

    def __init__(self, agent_id=None):
        super().__init__(
            name="Technical Director",
            role=AgentRole.DIRECTOR,
            capabilities=[
                AgentCapability.WORKFLOW_ORCHESTRATION,
                AgentCapability.CODE_GENERATION,
                AgentCapability.SCENE_MANAGEMENT,
                AgentCapability.QUALITY_REVIEW,
                AgentCapability.TESTING,
            ],
            agent_id=agent_id,
        )


class Producer(SparkAgent):
    """
    Manages project scope, timeline, and resource allocation.
    Coordinates between creative and technical teams.
    Ensures deliverables meet quality gates on schedule.
    """

    def __init__(self, agent_id=None):
        super().__init__(
            name="Producer",
            role=AgentRole.DIRECTOR,
            capabilities=[
                AgentCapability.WORKFLOW_ORCHESTRATION,
                AgentCapability.QUALITY_REVIEW,
                AgentCapability.TESTING,
                AgentCapability.DEPLOYMENT,
            ],
            agent_id=agent_id,
        )
