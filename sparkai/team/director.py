"""
SparkAI Team - Director Agent
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from enum import Enum

from sparkai.agent.base import SparkAgent, AgentCapability, AgentTask


class DirectorRole(Enum):
    CREATIVE_DIRECTOR = "creative_director"
    TECHNICAL_DIRECTOR = "technical_director"
    PRODUCER = "producer"


class TeamDirector(SparkAgent):
    """
    Tier 1 Director agent in the team hierarchy.
    Directors set vision, approve designs, and escalate issues.
    """

    def __init__(
        self,
        name: str,
        role: DirectorRole = DirectorRole.CREATIVE_DIRECTOR,
    ):
        caps = self._get_capabilities(role)
        super().__init__(name=name, role=role.value, capabilities=caps)
        self.director_role = role
        self._vision: str = ""
        self._design_reviews: List[Dict[str, Any]] = []
        self._escalated_issues: List[Dict[str, Any]] = []

    def set_vision(self, vision: str) -> None:
        self._vision = vision
        self._memory.remember(
            content=f"Vision set: {vision}",
            memory_type="long_term",
            importance=0.9,
        )

    def get_vision(self) -> str:
        return self._vision

    async def approve_design(self, design_doc: str) -> Dict[str, Any]:
        review = {
            "design": design_doc[:500],
            "approved": True,
            "feedback": "",
        }
        if self._llm:
            prompt = (
                f"As {self.name} ({self.director_role.value}), review this design:\n"
                f"{design_doc}\n\n"
                f"Project vision: {self._vision}\n"
                f"Approve or reject with feedback."
            )
            response = await self._llm.generate(prompt)
            review["feedback"] = response
            review["approved"] = "reject" not in response.lower()

        self._design_reviews.append(review)
        return review

    def escalate_issue(self, issue: str, priority: str = "high") -> Dict[str, Any]:
        escalation = {
            "issue": issue,
            "priority": priority,
            "escalated_by": self.name,
            "role": self.director_role.value,
        }
        self._escalated_issues.append(escalation)
        return escalation

    def get_design_reviews(self) -> List[Dict[str, Any]]:
        return self._design_reviews

    def get_escalated_issues(self) -> List[Dict[str, Any]]:
        return self._escalated_issues

    def _get_capabilities(self, role: DirectorRole) -> List[AgentCapability]:
        if role == DirectorRole.CREATIVE_DIRECTOR:
            return [AgentCapability.REASONING, AgentCapability.NARRATIVE_GENERATION, AgentCapability.WORLD_BUILDING]
        elif role == DirectorRole.TECHNICAL_DIRECTOR:
            return [AgentCapability.REASONING, AgentCapability.CODE_GENERATION, AgentCapability.QUALITY_REVIEW]
        else:
            return [AgentCapability.REASONING, AgentCapability.WORKFLOW_ORCHESTRATION, AgentCapability.DEPLOYMENT]
