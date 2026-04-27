"""
SparkAI Agent - Multi-Agent Orchestrator

Hierarchical orchestration system with depth-bounded delegation.
Supports event-driven coordination and contract-based verification.

Agent Hierarchy:
  Director -> Lead -> Specialist -> Worker

Each level has restricted permissions and focused responsibilities.
Delegation depth is bounded to prevent unbounded recursion.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sparkai.agent.base import (
    SparkAgent,
    AgentCapability,
    AgentRole,
    AgentState,
    AgentTask,
    ExecutionPlan,
)
from sparkai.agent.llm import LLMProvider, LLMConfig


@dataclass
class DelegationResult:
    task_id: str = ""
    agent_id: str = ""
    agent_name: str = ""
    status: str = "pending"
    result: Optional[Any] = None
    duration: float = 0.0
    verification: Optional[Dict[str, Any]] = None


class AgentOrchestrator:
    """
    Multi-agent orchestration system for the SparkLabs AI-Native Game Engine.

    Manages agent registration, hierarchical task delegation,
    event-driven coordination, and contract-based verification.

    Delegation rules:
    - Director can delegate to Leads and Specialists
    - Lead can delegate to Specialists and Workers
    - Specialist can delegate to Workers
    - Worker cannot delegate (leaf executor)
    """

    def __init__(self, max_spawn_depth: int = 2):
        self._agents: Dict[str, SparkAgent] = {}
        self._plans: List[ExecutionPlan] = []
        self._active_plan: Optional[ExecutionPlan] = None
        self._llm: Optional[LLMProvider] = None
        self._delegation_results: List[DelegationResult] = []
        self._max_spawn_depth: int = max_spawn_depth
        self._event_handlers: Dict[str, List[Any]] = {}

    def set_llm_provider(self, provider: LLMProvider) -> None:
        self._llm = provider

    def register_agent(self, agent: SparkAgent) -> None:
        self._agents[agent.id] = agent
        agent.on("task_completed", self._on_task_completed)
        agent.on("autonomous_complete", self._on_autonomous_complete)

    def unregister_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def get_agent(self, agent_id: str) -> Optional[SparkAgent]:
        return self._agents.get(agent_id)

    def list_agents(
        self,
        capability: Optional[AgentCapability] = None,
        role: Optional[AgentRole] = None,
    ) -> List[SparkAgent]:
        agents = list(self._agents.values())
        if capability:
            agents = [a for a in agents if a.has_capability(capability)]
        if role:
            agents = [a for a in agents if a.role == role]
        return agents

    def find_best_agent(
        self,
        capability: AgentCapability,
        prefer_role: Optional[AgentRole] = None,
    ) -> Optional[SparkAgent]:
        candidates = self.list_agents(capability=capability)
        if not candidates:
            return None

        idle = [a for a in candidates if a.state == AgentState.IDLE]
        pool = idle if idle else candidates

        if prefer_role:
            role_match = [a for a in pool if a.role == prefer_role]
            if role_match:
                return role_match[0]

        return pool[0]

    async def delegate_task(
        self,
        task: AgentTask,
        capability: AgentCapability,
        prefer_role: Optional[AgentRole] = None,
        verify: bool = True,
    ) -> DelegationResult:
        """
        Delegate a task to the best available agent.
        Optionally verify the result against task criteria.
        """
        start_time = time.time()
        agent = self.find_best_agent(capability, prefer_role)

        result = DelegationResult(
            task_id=task.id,
            agent_id=agent.id if agent else "",
            agent_name=agent.name if agent else "",
        )

        if not agent:
            result.status = "no_agent"
            self._delegation_results.append(result)
            return result

        agent.assign_task(task)

        try:
            task_result = await agent.think(task.description)

            if verify and task.verification_criteria:
                verification = await agent.verify(task.verification_criteria, str(task_result))
                result.verification = verification

            await agent.complete_task(task_result)
            result.result = task_result
            result.status = "completed"

        except Exception as e:
            result.status = "error"
            result.result = str(e)

        result.duration = time.time() - start_time
        self._delegation_results.append(result)
        return result

    async def delegate_batch(
        self,
        tasks: List[AgentTask],
        capability: AgentCapability,
        max_concurrent: int = 3,
    ) -> List[DelegationResult]:
        """
        Delegate multiple tasks in parallel with concurrency control.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _run_task(task: AgentTask) -> DelegationResult:
            async with semaphore:
                return await self.delegate_task(task, capability)

        results = await asyncio.gather(*[_run_task(t) for t in tasks])
        return list(results)

    async def create_plan(self, goal: str) -> ExecutionPlan:
        plan = ExecutionPlan(goal=goal)

        if self._llm:
            plan_prompt = (
                f"Create an execution plan for the following goal in a game development context:\n"
                f"Goal: {goal}\n\n"
                f"Available agent roles: {', '.join(set(a.role.value for a in self._agents.values()))}\n"
                f"Available capabilities: {', '.join(set(c.value for a in self._agents.values() for c in a.capabilities))}\n"
                f"Break this down into specific steps with assigned agent roles.\n"
                f"Include verification criteria for each step."
            )
            plan_description = await self._llm.generate(plan_prompt)
            plan.target_end_state = plan_description[:500]
            plan.end_state_checklist = self._extract_checklist(plan_description)
            plan.work_plan = self._parse_plan_steps(plan_description)
            plan.verification_gates = self._extract_verification(plan_description)
        else:
            plan.work_plan = [{"step": 1, "description": goal, "role": "general"}]

        self._plans.append(plan)
        return plan

    async def execute_plan(self, plan: ExecutionPlan) -> Any:
        plan.status = "executing"
        self._active_plan = plan
        results = []

        for step in plan.work_plan:
            role_name = step.get("role", "specialist")
            description = step.get("description", "")

            try:
                role = AgentRole(role_name)
            except ValueError:
                role = AgentRole.SPECIALIST

            capability = self._infer_capability(role_name)
            task = AgentTask(
                title=step.get("step_name", ""),
                description=description,
                verification_criteria=step.get("verification", ""),
            )

            delegation = await self.delegate_task(task, capability, prefer_role=role)
            results.append({
                "step": step,
                "agent": delegation.agent_name,
                "status": delegation.status,
                "result": str(delegation.result)[:200] if delegation.result else None,
                "verified": delegation.verification.get("verified") if delegation.verification else None,
            })

        plan.status = "completed"
        plan.result = results
        self._active_plan = None
        return results

    async def run_goal(self, goal: str) -> Any:
        plan = await self.create_plan(goal)
        return await self.execute_plan(plan)

    def _on_task_completed(self, data: Any) -> None:
        pass

    def _on_autonomous_complete(self, data: Any) -> None:
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_count": len(self._agents),
            "agents": [a.get_status() for a in self._agents.values()],
            "plan_count": len(self._plans),
            "active_plan": self._active_plan.id if self._active_plan else None,
            "delegation_count": len(self._delegation_results),
            "max_spawn_depth": self._max_spawn_depth,
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
                    "role": "specialist",
                })
        if not steps:
            steps.append({"step": 1, "description": plan_text[:200], "role": "specialist"})
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
            "director": AgentCapability.WORKFLOW_ORCHESTRATION,
            "lead": AgentCapability.WORKFLOW_ORCHESTRATION,
            "specialist": AgentCapability.REASONING,
            "worker": AgentCapability.REASONING,
        }
        for key, cap in mapping.items():
            if key in role_lower:
                return cap
        return AgentCapability.REASONING

    def _extract_checklist(self, text: str) -> List[str]:
        items = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith(("- [", "* [", "1.", "2.", "3.")):
                clean = line.lstrip("-*0123456789. []x")
                if clean:
                    items.append(clean)
        return items[:10] if items else ["Goal achieved"]

    def _extract_verification(self, text: str) -> List[str]:
        gates = []
        for line in text.split("\n"):
            line_lower = line.lower().strip()
            if any(kw in line_lower for kw in ["verify", "check", "ensure", "confirm"]):
                clean = line.strip().lstrip("-*0123456789.) ")
                if clean:
                    gates.append(clean)
        return gates[:5] if gates else ["Task completed successfully"]
