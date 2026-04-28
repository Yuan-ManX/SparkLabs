"""
SparkAI Agent - Studio Specialists (Tier 3)

Specialists execute focused work within their domain.
They cannot delegate further and report results to their
assigned Lead or Director.
"""

from sparkai.agent.base import SparkAgent, AgentCapability, AgentRole


class GameplayProgrammer(SparkAgent):
    """Implements game mechanics, controls, and player-facing systems."""

    def __init__(self, agent_id=None):
        super().__init__(
            name="Gameplay Programmer",
            role=AgentRole.SPECIALIST,
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.GAMEPLAY_DESIGN,
            ],
            agent_id=agent_id,
        )


class EngineProgrammer(SparkAgent):
    """Implements core engine systems: ECS, rendering, physics."""

    def __init__(self, agent_id=None):
        super().__init__(
            name="Engine Programmer",
            role=AgentRole.SPECIALIST,
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.SCENE_MANAGEMENT,
            ],
            agent_id=agent_id,
        )


class AIProgrammer(SparkAgent):
    """Implements AI systems: NPC behavior, pathfinding, decision trees."""

    def __init__(self, agent_id=None):
        super().__init__(
            name="AI Programmer",
            role=AgentRole.SPECIALIST,
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.NPC_CONTROL,
            ],
            agent_id=agent_id,
        )


class LevelDesigner(SparkAgent):
    """Designs and builds game levels, encounters, and pacing."""

    def __init__(self, agent_id=None):
        super().__init__(
            name="Level Designer",
            role=AgentRole.SPECIALIST,
            capabilities=[
                AgentCapability.WORLD_BUILDING,
                AgentCapability.GAMEPLAY_DESIGN,
                AgentCapability.SCENE_MANAGEMENT,
            ],
            agent_id=agent_id,
        )


class WorldBuilder(SparkAgent):
    """Creates game worlds: terrain, environments, atmosphere."""

    def __init__(self, agent_id=None):
        super().__init__(
            name="World Builder",
            role=AgentRole.SPECIALIST,
            capabilities=[
                AgentCapability.WORLD_BUILDING,
                AgentCapability.ASSET_GENERATION,
                AgentCapability.SCENE_MANAGEMENT,
            ],
            agent_id=agent_id,
        )


class SoundDesigner(SparkAgent):
    """Creates audio: sound effects, music, ambient audio."""

    def __init__(self, agent_id=None):
        super().__init__(
            name="Sound Designer",
            role=AgentRole.SPECIALIST,
            capabilities=[
                AgentCapability.AUDIO_GENERATION,
            ],
            agent_id=agent_id,
        )


class Writer(SparkAgent):
    """Creates narrative content: dialogue, lore, quest text."""

    def __init__(self, agent_id=None):
        super().__init__(
            name="Writer",
            role=AgentRole.SPECIALIST,
            capabilities=[
                AgentCapability.NARRATIVE_GENERATION,
            ],
            agent_id=agent_id,
        )


class QATester(SparkAgent):
    """Tests game builds, reports bugs, verifies fixes."""

    def __init__(self, agent_id=None):
        super().__init__(
            name="QA Tester",
            role=AgentRole.WORKER,
            capabilities=[
                AgentCapability.TESTING,
                AgentCapability.QUALITY_REVIEW,
            ],
            agent_id=agent_id,
        )
