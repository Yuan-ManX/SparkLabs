"""
SparkAI Team - Specialist Agent
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from enum import Enum

from sparkai.agent.base import SparkAgent, AgentCapability


class SpecialistRole(Enum):
    GAMEPLAY_PROGRAMMER = "gameplay_programmer"
    ENGINE_PROGRAMMER = "engine_programmer"
    AI_PROGRAMMER = "ai_programmer"
    NETWORK_PROGRAMMER = "network_programmer"
    TOOLS_PROGRAMMER = "tools_programmer"
    UI_PROGRAMMER = "ui_programmer"
    SYSTEMS_DESIGNER = "systems_designer"
    LEVEL_DESIGNER = "level_designer"
    ECONOMY_DESIGNER = "economy_designer"
    TECHNICAL_ARTIST = "technical_artist"
    SOUND_DESIGNER = "sound_designer"
    WRITER = "writer"
    WORLD_BUILDER = "world_builder"
    UX_DESIGNER = "ux_designer"
    PROTOTYPER = "prototyper"
    PERFORMANCE_ANALYST = "performance_analyst"
    DEVOPS_ENGINEER = "devops_engineer"
    QA_TESTER = "qa_tester"
    ACCESSIBILITY_SPECIALIST = "accessibility_specialist"


class TeamSpecialist(SparkAgent):
    """
    Tier 3 Specialist agent in the team hierarchy.
    Specialists execute tasks and can request clarification.
    """

    def __init__(
        self,
        name: str,
        role: SpecialistRole = SpecialistRole.GAMEPLAY_PROGRAMMER,
    ):
        caps = self._get_capabilities(role)
        super().__init__(name=name, role=role.value, capabilities=caps)
        self.specialist_role = role
        self._domain_expertise: str = ""
        self._submitted_work: List[Dict[str, Any]] = []

    def set_domain_expertise(self, expertise: str) -> None:
        self._domain_expertise = expertise

    async def submit_work(self, work: str, task_id: str = "") -> Dict[str, Any]:
        submission = {
            "task_id": task_id,
            "work": work,
            "submitted_by": self.name,
            "role": self.specialist_role.value,
        }
        self._submitted_work.append(submission)
        return submission

    async def request_clarification(self, question: str, task_id: str = "") -> Dict[str, Any]:
        return {
            "task_id": task_id,
            "question": question,
            "requested_by": self.name,
            "role": self.specialist_role.value,
        }

    def get_submitted_work(self) -> List[Dict[str, Any]]:
        return self._submitted_work

    def _get_capabilities(self, role: SpecialistRole) -> List[AgentCapability]:
        mapping = {
            SpecialistRole.GAMEPLAY_PROGRAMMER: [AgentCapability.CODE_GENERATION, AgentCapability.GAMEPLAY_DESIGN],
            SpecialistRole.ENGINE_PROGRAMMER: [AgentCapability.CODE_GENERATION],
            SpecialistRole.AI_PROGRAMMER: [AgentCapability.CODE_GENERATION, AgentCapability.NPC_CONTROL],
            SpecialistRole.NETWORK_PROGRAMMER: [AgentCapability.CODE_GENERATION],
            SpecialistRole.TOOLS_PROGRAMMER: [AgentCapability.CODE_GENERATION],
            SpecialistRole.UI_PROGRAMMER: [AgentCapability.CODE_GENERATION],
            SpecialistRole.SYSTEMS_DESIGNER: [AgentCapability.GAMEPLAY_DESIGN, AgentCapability.WORLD_BUILDING],
            SpecialistRole.LEVEL_DESIGNER: [AgentCapability.WORLD_BUILDING, AgentCapability.GAMEPLAY_DESIGN],
            SpecialistRole.ECONOMY_DESIGNER: [AgentCapability.GAMEPLAY_DESIGN],
            SpecialistRole.TECHNICAL_ARTIST: [AgentCapability.ASSET_GENERATION],
            SpecialistRole.SOUND_DESIGNER: [AgentCapability.AUDIO_GENERATION],
            SpecialistRole.WRITER: [AgentCapability.NARRATIVE_GENERATION],
            SpecialistRole.WORLD_BUILDER: [AgentCapability.WORLD_BUILDING, AgentCapability.ASSET_GENERATION],
            SpecialistRole.UX_DESIGNER: [AgentCapability.REASONING],
            SpecialistRole.PROTOTYPER: [AgentCapability.CODE_GENERATION, AgentCapability.GAMEPLAY_DESIGN],
            SpecialistRole.PERFORMANCE_ANALYST: [AgentCapability.QUALITY_REVIEW],
            SpecialistRole.DEVOPS_ENGINEER: [AgentCapability.DEPLOYMENT],
            SpecialistRole.QA_TESTER: [AgentCapability.TESTING, AgentCapability.QUALITY_REVIEW],
            SpecialistRole.ACCESSIBILITY_SPECIALIST: [AgentCapability.QUALITY_REVIEW],
        }
        return mapping.get(role, [AgentCapability.REASONING])
