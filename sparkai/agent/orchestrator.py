"""
SparkAI Agent - Multi-Agent Orchestrator
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sparkai.agent.base import SparkAgent, AgentCapability, AgentState, AgentTask
from sparkai.agent.llm import LLMProvider, LLMConfig


@dataclass
class OrchestrationPlan:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    assigned_agents: Dict[str, str] = field(default_factory=dict)
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    result: Optional[Any] = None


class AgentOrchestrator:
    """
    Multi-agent orchestration system for coordinating AI agents.

    Manages agent registration, task delegation, and workflow execution
    across multiple agents with different capabilities.
    """

    def __init__(self):
        self._agents: Dict[str, SparkAgent] = {}
        self._plans: List[OrchestrationPlan] = []
        self._active_plan: Optional[OrchestrationPlan] = None
        self._llm: Optional[LLMProvider] = None

    def set_llm_provider(self, provider: LLMProvider) -> None:
        self._llm = provider

    def register_agent(self, agent: SparkAgent) -> None:
        self._agents[agent.id] = agent

    def unregister_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def get_agent(self, agent_id: str) -> Optional[SparkAgent]:
        return self._agents.get(agent_id)

    def list_agents(self, capability: Optional[AgentCapability] = None) -> List[SparkAgent]:
        agents = list(self._agents.values())
        if capability:
            agents = [a for a in agents if a.has_capability(capability)]
        return agents

    def find_best_agent(self, capability: AgentCapability) -> Optional[SparkAgent]:
        candidates = self.list_agents(capability)
        if not candidates:
            return None
        idle = [a for a in candidates if a.state == AgentState.IDLE]
        if idle:
            return idle[0]
        return candidates[0]

    async def delegate_task(
        self, task: AgentTask, capability: AgentCapability
    ) -> Optional[Any]:
        agent = self.find_best_agent(capability)
        if not agent:
            return None
        agent.assign_task(task)
        result = await agent.think(task.description)
        await agent.complete_task(result)
        return result

    async def create_plan(self, goal: str) -> OrchestrationPlan:
        plan = OrchestrationPlan(goal=goal)

        if self._llm:
            plan_prompt = (
                f"Create an execution plan for the following goal in a game development context:\n"
                f"Goal: {goal}\n\n"
                f"Available agent roles: {', '.join(a.role for a in self._agents.values())}\n"
                f"Break this down into specific steps with assigned agent roles."
            )
            plan_description = await self._llm.generate(plan_prompt)
            plan.steps = self._parse_plan_steps(plan_description)
        else:
            plan.steps = [{"step": 1, "description": goal, "role": "general"}]

        self._plans.append(plan)
        return plan

    async def execute_plan(self, plan: OrchestrationPlan) -> Any:
        plan.status = "executing"
        self._active_plan = plan
        results = []

        for step in plan.steps:
            role = step.get("role", "general")
            description = step.get("description", "")

            capability = self._infer_capability(role)
            agent = self.find_best_agent(capability)

            if agent:
                task = AgentTask(title=step.get("step_name", ""), description=description)
                result = await self.delegate_task(task, capability)
                results.append({"step": step, "agent": agent.name, "result": result})
            else:
                results.append({"step": step, "agent": None, "result": "No available agent"})

        plan.status = "completed"
        plan.result = results
        self._active_plan = None
        return results

    async def run_goal(self, goal: str) -> Any:
        plan = await self.create_plan(goal)
        return await self.execute_plan(plan)

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_count": len(self._agents),
            "agents": [a.get_status() for a in self._agents.values()],
            "plan_count": len(self._plans),
            "active_plan": self._active_plan.id if self._active_plan else None,
        }

    def _parse_plan_steps(self, plan_text: str) -> List[Dict[str, Any]]:
        steps = []
        lines = plan_text.strip().split("\n")
        for i, line in enumerate(lines):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                clean = line.lstrip("0123456789.-) ")
                steps.append({
                    "step": i + 1,
                    "description": clean,
                    "role": "general",
                })
        if not steps:
            steps.append({"step": 1, "description": plan_text[:200], "role": "general"})
        return steps

    def _infer_capability(self, role: str) -> AgentCapability:
        role_lower = role.lower()
        mapping = {
            "creative": AgentCapability.NARRATIVE_GENERATION,
            "technical": AgentCapability.CODE_GENERATION,
            "art": AgentCapability.ASSET_GENERATION,
            "design": AgentCapability.GAMEPLAY_DESIGN,
            "npc": AgentCapability.NPC_CONTROL,
            "scene": AgentCapability.SCENE_MANAGEMENT,
            "narrative": AgentCapability.NARRATIVE_GENERATION,
            "audio": AgentCapability.AUDIO_GENERATION,
            "video": AgentCapability.VIDEO_GENERATION,
            "qa": AgentCapability.QUALITY_REVIEW,
            "test": AgentCapability.TESTING,
        }
        for key, cap in mapping.items():
            if key in role_lower:
                return cap
        return AgentCapability.REASONING
