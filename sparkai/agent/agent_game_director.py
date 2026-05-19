"""
SparkLabs Agent - Game Director

The central creative orchestrator that coordinates all game development agents.
The Game Director maintains a unified vision for the project — ensuring consistency
across mechanics, narrative, visuals, audio, and level design. It acts as the
"brain" of the AI-native game engine, making high-level creative decisions and
delegating specialized tasks to sub-agents.

Architecture:
  GameDirector
    |-- VisionManager (maintains the creative brief and design pillars)
    |-- AgentCoordinator (routes tasks to appropriate sub-agents)
    |-- ConsistencyValidator (cross-checks output across agent domains)
    |-- ProgressTracker (monitors development milestones and agent activity)
    |-- DecisionResolver (arbitrates conflicts between agent suggestions)

Director Roles:
  - CREATIVE_LEAD: high-level design decisions and vision stewardship
  - TECHNICAL_ARCHITECT: engine configuration and technical standards
  - QUALITY_GUARDIAN: consistency validation and quality assurance
  - PRODUCER: milestone tracking and resource allocation
  - INTEGRATOR: cross-domain coordination between agent outputs
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DirectorRole(Enum):
    CREATIVE_LEAD = "creative_lead"
    TECHNICAL_ARCHITECT = "technical_architect"
    QUALITY_GUARDIAN = "quality_guardian"
    PRODUCER = "producer"
    INTEGRATOR = "integrator"


class DecisionStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    NEEDS_REVIEW = "needs_review"


class ProjectPhase(Enum):
    CONCEPT = "concept"
    PRE_PRODUCTION = "pre_production"
    PRODUCTION = "production"
    POLISH = "polish"
    SHIPPING = "shipping"
    LIVE_OPS = "live_ops"


class SeverityLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CreativeBrief:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    project_name: str = "Untitled Project"
    genre: str = "platformer"
    target_audience: str = "general"
    art_style: str = "pixel_art"
    core_pillars: List[str] = field(default_factory=lambda: ["fun", "accessible"])
    tone: str = "lighthearted"
    scope: str = "small"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_name": self.project_name,
            "genre": self.genre,
            "target_audience": self.target_audience,
            "art_style": self.art_style,
            "core_pillars": self.core_pillars,
            "tone": self.tone,
            "scope": self.scope,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class CreativeDecision:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    brief_id: str = ""
    title: str = ""
    description: str = ""
    role: DirectorRole = DirectorRole.CREATIVE_LEAD
    status: DecisionStatus = DecisionStatus.PENDING
    rationale: str = ""
    alternatives: List[str] = field(default_factory=list)
    impacted_agents: List[str] = field(default_factory=list)
    severity: SeverityLevel = SeverityLevel.INFO
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "brief_id": self.brief_id,
            "title": self.title,
            "description": self.description,
            "role": self.role.value,
            "status": self.status.value,
            "rationale": self.rationale,
            "alternatives": self.alternatives,
            "impacted_agents": self.impacted_agents,
            "severity": self.severity.value,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }


@dataclass
class AgentTask:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    brief_id: str = ""
    assigned_agent: str = ""
    task_description: str = ""
    priority: int = 5
    dependencies: List[str] = field(default_factory=list)
    status: DecisionStatus = DecisionStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "brief_id": self.brief_id,
            "assigned_agent": self.assigned_agent,
            "task_description": self.task_description,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class ConsistencyReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    brief_id: str = ""
    agent_a: str = ""
    agent_b: str = ""
    issue_description: str = ""
    severity: SeverityLevel = SeverityLevel.WARNING
    recommendation: str = ""
    is_resolved: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "brief_id": self.brief_id,
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "issue_description": self.issue_description,
            "severity": self.severity.value,
            "recommendation": self.recommendation,
            "is_resolved": self.is_resolved,
            "created_at": self.created_at,
        }


@dataclass
class ProjectMilestone:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    brief_id: str = ""
    name: str = ""
    phase: ProjectPhase = ProjectPhase.CONCEPT
    target_completion: float = 0.0
    actual_completion: Optional[float] = None
    tasks_required: int = 0
    tasks_completed: int = 0
    is_blocked: bool = False
    blocker_description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        completion_pct = 0.0
        if self.tasks_required > 0:
            completion_pct = (self.tasks_completed / self.tasks_required) * 100.0
        return {
            "id": self.id,
            "brief_id": self.brief_id,
            "name": self.name,
            "phase": self.phase.value,
            "target_completion": self.target_completion,
            "actual_completion": self.actual_completion,
            "tasks_required": self.tasks_required,
            "tasks_completed": self.tasks_completed,
            "completion_percentage": round(completion_pct, 1),
            "is_blocked": self.is_blocked,
            "blocker_description": self.blocker_description,
        }


class GameDirector:
    """Central orchestrator for AI-native game development."""

    _instance: Optional["GameDirector"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._briefs: Dict[str, CreativeBrief] = {}
        self._decisions: Dict[str, List[CreativeDecision]] = {}
        self._tasks: Dict[str, List[AgentTask]] = {}
        self._consistency_reports: Dict[str, List[ConsistencyReport]] = {}
        self._milestones: Dict[str, List[ProjectMilestone]] = {}
        self._agent_registry: Dict[str, str] = {}
        self._decision_log: List[Dict[str, Any]] = []
        self._phase = ProjectPhase.CONCEPT
        self._is_initialized = False

    @classmethod
    def get_instance(cls) -> "GameDirector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Creative Brief Management ----

    def create_brief(self,
                     project_name: str = "Untitled Project",
                     genre: str = "platformer",
                     art_style: str = "pixel_art",
                     tone: str = "lighthearted",
                     core_pillars: Optional[List[str]] = None,
                     target_audience: str = "general",
                     scope: str = "small") -> CreativeBrief:
        brief = CreativeBrief(
            project_name=project_name,
            genre=genre,
            art_style=art_style,
            tone=tone,
            core_pillars=core_pillars or ["fun", "accessible"],
            target_audience=target_audience,
            scope=scope,
        )
        self._briefs[brief.id] = brief
        self._decisions[brief.id] = []
        self._tasks[brief.id] = []
        self._consistency_reports[brief.id] = []
        self._milestones[brief.id] = []
        self._seed_milestones(brief.id)
        self._decision_log.append({
            "action": "brief_created",
            "brief_id": brief.id,
            "project_name": project_name,
            "timestamp": time.time(),
        })
        return brief

    def get_brief(self, brief_id: str) -> Optional[CreativeBrief]:
        return self._briefs.get(brief_id)

    def list_briefs(self) -> List[CreativeBrief]:
        return list(self._briefs.values())

    def update_brief(self, brief_id: str, **kwargs: Any) -> Optional[CreativeBrief]:
        brief = self._briefs.get(brief_id)
        if brief is None:
            return None
        for key, value in kwargs.items():
            if hasattr(brief, key):
                setattr(brief, key, value)
        brief.updated_at = time.time()
        self._decision_log.append({
            "action": "brief_updated",
            "brief_id": brief_id,
            "changes": kwargs,
            "timestamp": time.time(),
        })
        return brief

    # ---- Creative Decision Engine ----

    def propose_decision(self,
                         brief_id: str,
                         title: str,
                         description: str,
                         role: str = "creative_lead",
                         severity: str = "info",
                         impacted_agents: Optional[List[str]] = None,
                         alternatives: Optional[List[str]] = None) -> Optional[CreativeDecision]:
        brief = self._briefs.get(brief_id)
        if brief is None:
            return None
        try:
            director_role = DirectorRole(role.lower())
        except ValueError:
            director_role = DirectorRole.CREATIVE_LEAD
        try:
            sev = SeverityLevel(severity.lower())
        except ValueError:
            sev = SeverityLevel.INFO
        decision = CreativeDecision(
            brief_id=brief_id,
            title=title,
            description=description,
            role=director_role,
            severity=sev,
            impacted_agents=impacted_agents or [],
            alternatives=alternatives or [],
        )
        self._decisions[brief_id].append(decision)
        self._decision_log.append({
            "action": "decision_proposed",
            "brief_id": brief_id,
            "decision_id": decision.id,
            "title": title,
            "timestamp": time.time(),
        })
        return decision

    def resolve_decision(self,
                         brief_id: str,
                         decision_id: str,
                         status: str = "approved",
                         rationale: str = "") -> Optional[CreativeDecision]:
        decisions = self._decisions.get(brief_id, [])
        for d in decisions:
            if d.id == decision_id:
                try:
                    d.status = DecisionStatus(status.lower())
                except ValueError:
                    d.status = DecisionStatus.APPROVED
                d.rationale = rationale
                d.resolved_at = time.time()
                self._decision_log.append({
                    "action": "decision_resolved",
                    "decision_id": decision_id,
                    "status": d.status.value,
                    "timestamp": time.time(),
                })
                return d
        return None

    def get_pending_decisions(self, brief_id: str) -> List[CreativeDecision]:
        decisions = self._decisions.get(brief_id, [])
        return [d for d in decisions if d.status == DecisionStatus.PENDING]

    def get_decisions(self, brief_id: str) -> List[CreativeDecision]:
        return self._decisions.get(brief_id, [])

    # ---- Agent Task Delegation ----

    def delegate_task(self,
                      brief_id: str,
                      agent_name: str,
                      description: str,
                      priority: int = 5,
                      dependencies: Optional[List[str]] = None) -> Optional[AgentTask]:
        brief = self._briefs.get(brief_id)
        if brief is None:
            return None
        task = AgentTask(
            brief_id=brief_id,
            assigned_agent=agent_name,
            task_description=description,
            priority=priority,
            dependencies=dependencies or [],
        )
        self._tasks[brief_id].append(task)
        self._agent_registry[agent_name] = brief_id
        self._decision_log.append({
            "action": "task_delegated",
            "brief_id": brief_id,
            "agent": agent_name,
            "task_id": task.id,
            "timestamp": time.time(),
        })
        return task

    def complete_task(self,
                      brief_id: str,
                      task_id: str,
                      result: Optional[Dict[str, Any]] = None) -> Optional[AgentTask]:
        tasks = self._tasks.get(brief_id, [])
        for t in tasks:
            if t.id == task_id:
                t.status = DecisionStatus.APPROVED
                t.result = result
                t.completed_at = time.time()
                self._update_milestone_progress(brief_id)
                self._decision_log.append({
                    "action": "task_completed",
                    "task_id": task_id,
                    "timestamp": time.time(),
                })
                return t
        return None

    def get_tasks(self, brief_id: str, agent_name: Optional[str] = None) -> List[AgentTask]:
        tasks = self._tasks.get(brief_id, [])
        if agent_name:
            return [t for t in tasks if t.assigned_agent == agent_name]
        return tasks

    def register_agent(self, agent_name: str, brief_id: str) -> None:
        self._agent_registry[agent_name] = brief_id

    def get_registered_agents(self) -> Dict[str, str]:
        return dict(self._agent_registry)

    # ---- Consistency Validation ----

    def report_consistency_issue(self,
                                 brief_id: str,
                                 agent_a: str,
                                 agent_b: str,
                                 description: str,
                                 severity: str = "warning",
                                 recommendation: str = "") -> Optional[ConsistencyReport]:
        brief = self._briefs.get(brief_id)
        if brief is None:
            return None
        try:
            sev = SeverityLevel(severity.lower())
        except ValueError:
            sev = SeverityLevel.WARNING
        report = ConsistencyReport(
            brief_id=brief_id,
            agent_a=agent_a,
            agent_b=agent_b,
            issue_description=description,
            severity=sev,
            recommendation=recommendation,
        )
        self._consistency_reports[brief_id].append(report)
        return report

    def resolve_consistency_issue(self, brief_id: str, report_id: str) -> Optional[ConsistencyReport]:
        reports = self._consistency_reports.get(brief_id, [])
        for r in reports:
            if r.id == report_id:
                r.is_resolved = True
                return r
        return None

    def get_consistency_reports(self, brief_id: str,
                                 unresolved_only: bool = False) -> List[ConsistencyReport]:
        reports = self._consistency_reports.get(brief_id, [])
        if unresolved_only:
            return [r for r in reports if not r.is_resolved]
        return reports

    # ---- Progress Tracking ----

    def _seed_milestones(self, brief_id: str) -> None:
        phases = [
            (ProjectPhase.CONCEPT, "Concept Document", 2),
            (ProjectPhase.PRE_PRODUCTION, "Core Prototype", 4),
            (ProjectPhase.PRODUCTION, "Full Content Build", 8),
            (ProjectPhase.POLISH, "Polish & Refine", 4),
            (ProjectPhase.SHIPPING, "Platform Export", 2),
        ]
        now = time.time()
        for i, (phase, name, tasks) in enumerate(phases):
            target = now + (i + 1) * 86400 * 7
            ms = ProjectMilestone(
                brief_id=brief_id,
                name=name,
                phase=phase,
                target_completion=target,
                tasks_required=tasks,
            )
            self._milestones[brief_id].append(ms)

    def _update_milestone_progress(self, brief_id: str) -> None:
        total_completed = sum(
            1 for t in self._tasks.get(brief_id, [])
            if t.status == DecisionStatus.APPROVED
        )
        milestones = self._milestones.get(brief_id, [])
        cumulative = 0
        for ms in milestones:
            cumulative += ms.tasks_required
            completed_for_ms = min(total_completed, cumulative)
            prev_cumulative = cumulative - ms.tasks_required
            ms.tasks_completed = max(0, completed_for_ms - prev_cumulative)
            if ms.tasks_completed >= ms.tasks_required and ms.actual_completion is None:
                ms.actual_completion = time.time()
                self._phase = ms.phase

    def get_milestones(self, brief_id: str) -> List[ProjectMilestone]:
        return self._milestones.get(brief_id, [])

    def get_progress_summary(self, brief_id: str) -> Dict[str, Any]:
        tasks = self._tasks.get(brief_id, [])
        decisions = self._decisions.get(brief_id, [])
        reports = self._consistency_reports.get(brief_id, [])
        milestones = self._milestones.get(brief_id, [])
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status == DecisionStatus.APPROVED)
        pending_decisions = sum(1 for d in decisions if d.status == DecisionStatus.PENDING)
        unresolved_issues = sum(1 for r in reports if not r.is_resolved)
        current_milestone = None
        for ms in milestones:
            if ms.actual_completion is None:
                current_milestone = ms.name
                break
        return {
            "brief_id": brief_id,
            "phase": self._phase.value,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_pct": round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1),
            "pending_decisions": pending_decisions,
            "unresolved_consistency_issues": unresolved_issues,
            "active_agents": len(self._agent_registry),
            "current_milestone": current_milestone,
            "total_milestones": len(milestones),
        }

    def get_decision_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._decision_log[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        total_tasks = sum(len(v) for v in self._tasks.values())
        total_completed = sum(
            1 for tasks in self._tasks.values()
            for t in tasks if t.status == DecisionStatus.APPROVED
        )
        total_decisions = sum(len(v) for v in self._decisions.values())
        pending_decisions = sum(
            1 for decisions in self._decisions.values()
            for d in decisions if d.status == DecisionStatus.PENDING
        )
        total_reports = sum(len(v) for v in self._consistency_reports.values())
        unresolved_reports = sum(
            1 for reports in self._consistency_reports.values()
            for r in reports if not r.is_resolved
        )
        return {
            "total_briefs": len(self._briefs),
            "total_tasks": total_tasks,
            "tasks_completed": total_completed,
            "total_decisions": total_decisions,
            "pending_decisions": pending_decisions,
            "consistency_reports": total_reports,
            "unresolved_issues": unresolved_reports,
            "registered_agents": len(self._agent_registry),
            "current_phase": self._phase.value,
            "decision_log_entries": len(self._decision_log),
        }


def get_game_director() -> GameDirector:
    return GameDirector.get_instance()