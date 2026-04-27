"""
SparkAI Team - Lead Agent
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from enum import Enum

from sparkai.agent.base import SparkAgent, AgentCapability, AgentTask


class LeadRole(Enum):
    GAME_DESIGNER = "game_designer"
    LEAD_PROGRAMMER = "lead_programmer"
    ART_DIRECTOR = "art_director"
    AUDIO_DIRECTOR = "audio_director"
    NARRATIVE_DIRECTOR = "narrative_director"
    QA_LEAD = "qa_lead"
    RELEASE_MANAGER = "release_manager"


class TeamLead(SparkAgent):
    """
    Tier 2 Lead agent in the team hierarchy.
    Leads delegate tasks, conduct reviews, and report progress.
    """

    def __init__(
        self,
        name: str,
        role: LeadRole = LeadRole.GAME_DESIGNER,
    ):
        caps = self._get_capabilities(role)
        super().__init__(name=name, role=role.value, capabilities=caps)
        self.lead_role = role
        self._specialists: List[Dict[str, Any]] = []
        self._pending_reviews: List[Dict[str, Any]] = []

    def add_specialist(self, specialist_id: str, specialist_name: str, domain: str) -> None:
        self._specialists.append({
            "id": specialist_id,
            "name": specialist_name,
            "domain": domain,
        })

    def get_specialists(self) -> List[Dict[str, Any]]:
        return self._specialists

    async def delegate_task(self, task: AgentTask, specialist_id: str) -> Dict[str, Any]:
        delegation = {
            "task_id": task.id,
            "task_title": task.title,
            "delegated_to": specialist_id,
            "delegated_by": self.name,
            "status": "delegated",
        }
        return delegation

    async def conduct_review(self, work: str, review_type: str = "general") -> Dict[str, Any]:
        review = {
            "work": work[:500],
            "review_type": review_type,
            "reviewer": self.name,
            "approved": True,
            "feedback": "",
        }
        if self._llm:
            prompt = (
                f"As {self.name} ({self.lead_role.value}), review this work:\n"
                f"{work}\n\n"
                f"Review type: {review_type}\n"
                f"Provide detailed feedback."
            )
            response = await self._llm.generate(prompt)
            review["feedback"] = response
            review["approved"] = "reject" not in response.lower()

        self._pending_reviews.append(review)
        return review

    def report_progress(self) -> Dict[str, Any]:
        return {
            "lead": self.name,
            "role": self.lead_role.value,
            "specialist_count": len(self._specialists),
            "pending_reviews": len(self._pending_reviews),
            "task_history": len(self._task_history),
        }

    def _get_capabilities(self, role: LeadRole) -> List[AgentCapability]:
        mapping = {
            LeadRole.GAME_DESIGNER: [AgentCapability.REASONING, AgentCapability.GAMEPLAY_DESIGN, AgentCapability.WORLD_BUILDING],
            LeadRole.LEAD_PROGRAMMER: [AgentCapability.REASONING, AgentCapability.CODE_GENERATION, AgentCapability.QUALITY_REVIEW],
            LeadRole.ART_DIRECTOR: [AgentCapability.REASONING, AgentCapability.ASSET_GENERATION],
            LeadRole.AUDIO_DIRECTOR: [AgentCapability.REASONING, AgentCapability.AUDIO_GENERATION],
            LeadRole.NARRATIVE_DIRECTOR: [AgentCapability.REASONING, AgentCapability.NARRATIVE_GENERATION],
            LeadRole.QA_LEAD: [AgentCapability.REASONING, AgentCapability.QUALITY_REVIEW, AgentCapability.TESTING],
            LeadRole.RELEASE_MANAGER: [AgentCapability.REASONING, AgentCapability.DEPLOYMENT, AgentCapability.WORKFLOW_ORCHESTRATION],
        }
        return mapping.get(role, [AgentCapability.REASONING])
