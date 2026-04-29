"""
SparkAI Agent - Studio Coordinator

Full studio hierarchy coordination system that mirrors a real game
studio's organizational structure. The StudioCoordinator manages
agent assignment, task delegation, and cross-department coordination
across the complete game development lifecycle.

Architecture:
  StudioCoordinator
    |-- StudioHierarchy (3-tier agent organization)
    |-- DepartmentRegistry (department definitions and agents)
    |-- TaskRouter (intelligent task-to-agent routing)
    |-- CoordinationLog (cross-department coordination history)

Studio Hierarchy:
  Tier 1 - Directors (strategic vision, cross-domain coordination)
    Creative Director, Technical Director, Producer

  Tier 2 - Department Leads (domain coordination, specialist delegation)
    Game Designer, Lead Programmer, Art Director,
    Audio Director, Narrative Director, QA Lead

  Tier 3 - Specialists (focused execution on single domain)
    Gameplay Programmer, Engine Programmer, AI Programmer,
    Level Designer, World Builder, Sound Designer,
    Writer, QA Tester, Technical Artist, UX Designer

Coordination Patterns:
  - Vertical: Director -> Lead -> Specialist (chain of command)
  - Horizontal: Lead <-> Lead (cross-department sync)
  - Ad-hoc: Specialist <-> Specialist (peer collaboration)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentTier(Enum):
    DIRECTOR = "director"
    LEAD = "lead"
    SPECIALIST = "specialist"


class Department(Enum):
    CREATIVE = "creative"
    PROGRAMMING = "programming"
    ART = "art"
    AUDIO = "audio"
    NARRATIVE = "narrative"
    QA = "qa"
    PRODUCTION = "production"


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class CoordinationType(Enum):
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    AD_HOC = "ad_hoc"
    BROADCAST = "broadcast"


@dataclass
class StudioAgent:
    """An agent in the studio hierarchy."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    role: str = ""
    tier: AgentTier = AgentTier.SPECIALIST
    department: Department = Department.PROGRAMMING
    capabilities: List[str] = field(default_factory=list)
    current_task: Optional[str] = None
    task_count: int = 0
    completed_count: int = 0
    is_available: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "tier": self.tier.value,
            "department": self.department.value,
            "capabilities": self.capabilities,
            "current_task": self.current_task,
            "task_count": self.task_count,
            "completed_count": self.completed_count,
            "is_available": self.is_available,
        }


@dataclass
class StudioTask:
    """A task assigned within the studio."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    department: Department = Department.PROGRAMMING
    assigned_to: Optional[str] = None
    delegated_by: Optional[str] = None
    parent_task_id: Optional[str] = None
    child_task_ids: List[str] = field(default_factory=list)
    status: str = "pending"
    required_capabilities: List[str] = field(default_factory=list)
    result: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description[:200],
            "priority": self.priority.value,
            "department": self.department.value,
            "assigned_to": self.assigned_to,
            "delegated_by": self.delegated_by,
            "parent_task_id": self.parent_task_id,
            "child_task_ids": self.child_task_ids,
            "status": self.status,
            "required_capabilities": self.required_capabilities,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class CoordinationEntry:
    """Record of a coordination event between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    coordination_type: CoordinationType = CoordinationType.VERTICAL
    from_agent_id: str = ""
    from_agent_role: str = ""
    to_agent_id: str = ""
    to_agent_role: str = ""
    task_id: Optional[str] = None
    message: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "coordination_type": self.coordination_type.value,
            "from_agent_id": self.from_agent_id,
            "from_agent_role": self.from_agent_role,
            "to_agent_id": self.to_agent_id,
            "to_agent_role": self.to_agent_role,
            "task_id": self.task_id,
            "message": self.message[:200],
            "created_at": self.created_at,
        }


_DIRECTOR_DEFS = [
    {"name": "Creative Director", "role": "creative_director", "department": Department.CREATIVE, "capabilities": ["vision", "design_review", "narrative_oversight", "art_direction"]},
    {"name": "Technical Director", "role": "technical_director", "department": Department.PROGRAMMING, "capabilities": ["architecture", "performance", "code_review", "engine_oversight"]},
    {"name": "Producer", "role": "producer", "department": Department.PRODUCTION, "capabilities": ["scheduling", "scope", "resource_allocation", "milestone_tracking"]},
]

_LEAD_DEFS = [
    {"name": "Game Designer", "role": "game_designer", "department": Department.CREATIVE, "capabilities": ["mechanics", "balance", "systems_design", "prototyping"]},
    {"name": "Lead Programmer", "role": "lead_programmer", "department": Department.PROGRAMMING, "capabilities": ["code_architecture", "engine_integration", "code_review", "debugging"]},
    {"name": "Art Director", "role": "art_director", "department": Department.ART, "capabilities": ["visual_style", "asset_pipeline", "rendering", "animation"]},
    {"name": "Audio Director", "role": "audio_director", "department": Department.AUDIO, "capabilities": ["sound_design", "music", "mixing", "spatial_audio"]},
    {"name": "Narrative Director", "role": "narrative_director", "department": Department.NARRATIVE, "capabilities": ["story", "dialogue", "quest_design", "world_building"]},
    {"name": "QA Lead", "role": "qa_lead", "department": Department.QA, "capabilities": ["testing", "bug_triage", "quality_gates", "regression"]},
]

_SPECIALIST_DEFS = [
    {"name": "Gameplay Programmer", "role": "gameplay_programmer", "department": Department.PROGRAMMING, "capabilities": ["gameplay_code", "input_handling", "mechanics_implementation"]},
    {"name": "Engine Programmer", "role": "engine_programmer", "department": Department.PROGRAMMING, "capabilities": ["engine_core", "rendering", "physics", "optimization"]},
    {"name": "AI Programmer", "role": "ai_programmer", "department": Department.PROGRAMMING, "capabilities": ["behavior_trees", "pathfinding", "decision_making", "neural_networks"]},
    {"name": "Level Designer", "role": "level_designer", "department": Department.CREATIVE, "capabilities": ["level_layout", "encounter_design", "pacing", "flow"]},
    {"name": "World Builder", "role": "world_builder", "department": Department.CREATIVE, "capabilities": ["terrain", "biomes", "environment", "procedural_generation"]},
    {"name": "Sound Designer", "role": "sound_designer", "department": Department.AUDIO, "capabilities": ["sfx", "ambient", "foley", "audio_implementation"]},
    {"name": "Writer", "role": "writer", "department": Department.NARRATIVE, "capabilities": ["dialogue", "lore", "item_descriptions", "cutscenes"]},
    {"name": "QA Tester", "role": "qa_tester", "department": Department.QA, "capabilities": ["manual_testing", "automated_tests", "regression", "compatibility"]},
    {"name": "Technical Artist", "role": "technical_artist", "department": Department.ART, "capabilities": ["shaders", "vfx", "optimization", "pipeline_tools"]},
    {"name": "UX Designer", "role": "ux_designer", "department": Department.ART, "capabilities": ["ui_design", "accessibility", "usability", "prototyping"]},
]


class TaskRouter:
    """
    Routes tasks to the most appropriate agent based on
    capabilities, availability, and workload.
    """

    def find_best_agent(
        self,
        agents: List[StudioAgent],
        required_capabilities: List[str],
        department: Optional[Department] = None,
        prefer_tier: Optional[AgentTier] = None,
    ) -> Optional[StudioAgent]:
        candidates = [a for a in agents if a.is_available]
        if not candidates:
            return None

        if department:
            dept_candidates = [a for a in candidates if a.department == department]
            if dept_candidates:
                candidates = dept_candidates

        scored: List[tuple] = []
        for agent in candidates:
            cap_match = len(set(agent.capabilities) & set(required_capabilities))
            workload = agent.task_count - agent.completed_count
            tier_bonus = 0
            if prefer_tier and agent.tier == prefer_tier:
                tier_bonus = 2
            score = cap_match * 3 - workload + tier_bonus
            scored.append((score, agent))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else None


class StudioCoordinator:
    """
    Full studio hierarchy coordination system for the SparkLabs
    AI-Native Game Engine.

    Manages agent assignment, task delegation, and cross-department
    coordination across the complete game development lifecycle.

    Usage:
        studio = StudioCoordinator()
        task_id = studio.assign_task("Implement player movement", "programming", ["gameplay_code"])
        agents = studio.get_department_agents("programming")
        print(studio.get_hierarchy())
    """

    def __init__(self):
        self._agents: Dict[str, StudioAgent] = {}
        self._tasks: Dict[str, StudioTask] = {}
        self._coordination_log: List[CoordinationEntry] = []
        self._router = TaskRouter()
        self._seed_studio()

    def _seed_studio(self) -> None:
        for defn in _DIRECTOR_DEFS:
            agent = StudioAgent(
                name=defn["name"],
                role=defn["role"],
                tier=AgentTier.DIRECTOR,
                department=defn["department"],
                capabilities=defn["capabilities"],
            )
            self._agents[agent.id] = agent

        for defn in _LEAD_DEFS:
            agent = StudioAgent(
                name=defn["name"],
                role=defn["role"],
                tier=AgentTier.LEAD,
                department=defn["department"],
                capabilities=defn["capabilities"],
            )
            self._agents[agent.id] = agent

        for defn in _SPECIALIST_DEFS:
            agent = StudioAgent(
                name=defn["name"],
                role=defn["role"],
                tier=AgentTier.SPECIALIST,
                department=defn["department"],
                capabilities=defn["capabilities"],
            )
            self._agents[agent.id] = agent

    def get_hierarchy(self) -> Dict[str, Any]:
        directors = [a.to_dict() for a in self._agents.values() if a.tier == AgentTier.DIRECTOR]
        leads = [a.to_dict() for a in self._agents.values() if a.tier == AgentTier.LEAD]
        specialists = [a.to_dict() for a in self._agents.values() if a.tier == AgentTier.SPECIALIST]
        return {
            "directors": directors,
            "leads": leads,
            "specialists": specialists,
            "total_agents": len(self._agents),
        }

    def get_department_agents(self, department: str) -> List[Dict[str, Any]]:
        dept = Department(department)
        agents = [a for a in self._agents.values() if a.department == dept]
        return [a.to_dict() for a in sorted(agents, key=lambda a: a.tier.value)]

    def assign_task(
        self,
        title: str,
        department: str = "programming",
        required_capabilities: Optional[List[str]] = None,
        priority: int = 2,
        description: str = "",
        delegated_by: Optional[str] = None,
    ) -> Optional[str]:
        dept = Department(department)
        task = StudioTask(
            title=title,
            description=description,
            priority=TaskPriority(priority),
            department=dept,
            required_capabilities=required_capabilities or [],
            delegated_by=delegated_by,
        )

        agents = list(self._agents.values())
        best = self._router.find_best_agent(agents, task.required_capabilities, dept)
        if best:
            task.assigned_to = best.id
            best.current_task = task.id
            best.task_count += 1
            best.is_available = False
            task.status = "assigned"

            if delegated_by:
                self._log_coordination(
                    CoordinationType.VERTICAL,
                    delegated_by, "", best.id, best.role,
                    task.id, f"Delegated: {title}",
                )
        else:
            task.status = "unassigned"

        self._tasks[task.id] = task
        return task.id

    def complete_task(self, task_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.status = "completed"
        task.result = result or {}
        task.completed_at = time.time()

        if task.assigned_to:
            agent = self._agents.get(task.assigned_to)
            if agent:
                agent.completed_count += 1
                agent.current_task = None
                agent.is_available = True

        return True

    def delegate_task(self, from_agent_id: str, task_title: str, target_department: str, capabilities: Optional[List[str]] = None) -> Optional[str]:
        from_agent = self._agents.get(from_agent_id)
        if not from_agent:
            return None

        task_id = self.assign_task(
            title=task_title,
            department=target_department,
            required_capabilities=capabilities or [],
            delegated_by=from_agent_id,
        )

        if task_id:
            self._log_coordination(
                CoordinationType.VERTICAL,
                from_agent_id, from_agent.role,
                "", "",
                task_id, f"Delegated: {task_title}",
            )

        return task_id

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    def list_tasks(self, status: Optional[str] = None, department: Optional[str] = None) -> List[Dict[str, Any]]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if department:
            tasks = [t for t in tasks if t.department == Department(department)]
        return [t.to_dict() for t in sorted(tasks, key=lambda t: t.priority.value)]

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        agent = self._agents.get(agent_id)
        return agent.to_dict() if agent else None

    def find_agent_by_role(self, role: str) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._agents.values() if a.role == role]

    def _log_coordination(self, ctype: CoordinationType, from_id: str, from_role: str, to_id: str, to_role: str, task_id: Optional[str], message: str) -> None:
        entry = CoordinationEntry(
            coordination_type=ctype,
            from_agent_id=from_id,
            from_agent_role=from_role,
            to_agent_id=to_id,
            to_agent_role=to_role,
            task_id=task_id,
            message=message,
        )
        self._coordination_log.append(entry)

    def get_coordination_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._coordination_log[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        by_tier: Dict[str, int] = {}
        by_dept: Dict[str, int] = {}
        for a in self._agents.values():
            by_tier[a.tier.value] = by_tier.get(a.tier.value, 0) + 1
            by_dept[a.department.value] = by_dept.get(a.department.value, 0) + 1

        by_status: Dict[str, int] = {}
        for t in self._tasks.values():
            by_status[t.status] = by_status.get(t.status, 0) + 1

        return {
            "total_agents": len(self._agents),
            "by_tier": by_tier,
            "by_department": by_dept,
            "total_tasks": len(self._tasks),
            "tasks_by_status": by_status,
            "available_agents": sum(1 for a in self._agents.values() if a.is_available),
            "coordination_events": len(self._coordination_log),
        }


_global_studio: Optional[StudioCoordinator] = None


def get_studio_coordinator() -> StudioCoordinator:
    """Get the global StudioCoordinator singleton."""
    global _global_studio
    if _global_studio is None:
        _global_studio = StudioCoordinator()
    return _global_studio


def reset_studio_coordinator() -> None:
    """Reset the global StudioCoordinator singleton."""
    global _global_studio
    _global_studio = None
