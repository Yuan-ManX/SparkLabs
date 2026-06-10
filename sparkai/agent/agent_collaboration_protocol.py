"""
SparkLabs Agent - Collaboration Protocol Engine

Structured inter-agent handoff and teamwork coordination for
AI-native game creation. Manages delegation, consultation,
escalation, broadcast, and chain-based collaboration between
specialized agents with formalized handoff records.

Architecture:
  CollaborationProtocolEngine
    |-- CollaborationRequest (formal work proposal)
    |-- TeamFormation (role-based team assembly)
    |-- HandoffRecord (structured task transfer)
    |-- CollaborationSession (active teamwork context)

Handoff Types:
  - DELEGATE: transfer ownership of a task
  - CONSULT: request expert opinion, retains ownership
  - ESCALATE: raise issue to coordinator or lead
  - BROADCAST: notify all team members
  - CHAIN: sequential handoff through multiple agents

Agent Roles:
  - LEAD: team direction and final decisions
  - SPECIALIST: domain expertise execution
  - REVIEWER: quality validation and feedback
  - OBSERVER: passive monitoring and reporting
  - COORDINATOR: workflow management and assignment

Usage:
    engine = CollaborationProtocolEngine()
    request = engine.propose_collaboration(
        "agent_001", "Design the boss fight sequence",
        required_roles=["specialist", "reviewer"],
    )
    team = engine.form_team(request.id, ["agent_002", "agent_003"], "agent_001")
    handoff = engine.initiate_handoff(
        team.id, "agent_001", "agent_002",
        "Create boss AI behavior tree",
    )
    engine.accept_handoff(handoff.id, "agent_002")
    engine.complete_handoff(handoff.id, {"blueprint": "boss_ai_v2"})
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class HandoffType(Enum):
    DELEGATE = "delegate"
    CONSULT = "consult"
    ESCALATE = "escalate"
    BROADCAST = "broadcast"
    CHAIN = "chain"


class ProtocolState(Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class AgentRole(Enum):
    LEAD = "lead"
    SPECIALIST = "specialist"
    REVIEWER = "reviewer"
    OBSERVER = "observer"
    COORDINATOR = "coordinator"


@dataclass
class CollaborationRequest:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    initiator_id: str = ""
    task_description: str = ""
    required_roles: List[str] = field(default_factory=list)
    state: ProtocolState = ProtocolState.PROPOSED
    created_at: float = field(default_factory=time.time)
    responses: Dict[str, str] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "initiator_id": self.initiator_id,
            "task_description": self.task_description,
            "required_roles": self.required_roles,
            "state": self.state.value,
            "created_at": self.created_at,
            "response_count": len(self.responses),
            "responses": self.responses,
            "notes": self.notes,
        }


@dataclass
class TeamFormation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    request_id: str = ""
    member_ids: List[str] = field(default_factory=list)
    lead_id: str = ""
    roles: Dict[str, str] = field(default_factory=dict)
    formed_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "member_count": len(self.member_ids),
            "members": self.member_ids,
            "lead_id": self.lead_id,
            "roles": self.roles,
            "formed_at": self.formed_at,
        }


@dataclass
class HandoffRecord:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    team_id: str = ""
    from_agent: str = ""
    to_agent: str = ""
    task_context: str = ""
    handoff_type: HandoffType = HandoffType.DELEGATE
    state: ProtocolState = ProtocolState.PROPOSED
    created_at: float = field(default_factory=time.time)
    accepted_at: Optional[float] = None
    completed_at: Optional[float] = None
    notes: str = ""
    results: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "task_context": self.task_context[:120],
            "handoff_type": self.handoff_type.value,
            "state": self.state.value,
            "created_at": self.created_at,
            "accepted_at": self.accepted_at,
            "completed_at": self.completed_at,
            "notes": self.notes,
            "results": self.results,
            "duration_seconds": (
                (self.completed_at - self.created_at)
                if self.completed_at else None
            ),
        }


@dataclass
class CollaborationSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    team_id: str = ""
    team: Optional[TeamFormation] = None
    handoffs: List[HandoffRecord] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    state: ProtocolState = ProtocolState.IN_PROGRESS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "team": self.team.to_dict() if self.team else None,
            "handoff_count": len(self.handoffs),
            "active_handoffs": sum(
                1 for h in self.handoffs
                if h.state in (ProtocolState.PROPOSED, ProtocolState.ACCEPTED, ProtocolState.IN_PROGRESS)
            ),
            "completed_handoffs": sum(
                1 for h in self.handoffs
                if h.state == ProtocolState.COMPLETED
            ),
            "message_count": len(self.messages),
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "state": self.state.value,
        }


class CollaborationProtocolEngine:
    """
    Structured inter-agent handoff and teamwork coordination engine.

    Manages collaboration requests, team formation, handoff records,
    and active collaboration sessions. Supports delegation, consultation,
    escalation, broadcast, and chain-based handoff workflows between
    specialized AI agents for game creation.
    """

    _instance: Optional["CollaborationProtocolEngine"] = None

    @classmethod
    def get_instance(cls) -> "CollaborationProtocolEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._requests: Dict[str, CollaborationRequest] = {}
        self._teams: Dict[str, TeamFormation] = {}
        self._handoffs: Dict[str, HandoffRecord] = {}
        self._sessions: Dict[str, CollaborationSession] = {}
        self._request_count: int = 0
        self._team_count: int = 0
        self._handoff_count: int = 0
        self._session_count: int = 0
        self._rejected_count: int = 0
        self._completed_handoff_count: int = 0
        self._agent_registry: Dict[str, Dict[str, Any]] = {}

    def propose_collaboration(
        self,
        initiator_id: str,
        task_description: str,
        required_roles: Optional[List[str]] = None,
    ) -> CollaborationRequest:
        request = CollaborationRequest(
            initiator_id=initiator_id,
            task_description=task_description,
            required_roles=required_roles or [],
        )
        self._requests[request.id] = request
        self._request_count += 1
        self._ensure_agent_registered(initiator_id)
        return request

    def form_team(
        self,
        request_id: str,
        member_ids: Optional[List[str]] = None,
        lead_id: str = "",
    ) -> TeamFormation:
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Collaboration request not found: {request_id}")

        member_ids = member_ids or []
        if lead_id and lead_id not in member_ids:
            member_ids.insert(0, lead_id)

        roles: Dict[str, str] = {}
        if lead_id:
            roles[lead_id] = AgentRole.LEAD.value
        for mid in member_ids:
            if mid not in roles:
                roles[mid] = AgentRole.SPECIALIST.value

        team = TeamFormation(
            request_id=request_id,
            member_ids=member_ids,
            lead_id=lead_id,
            roles=roles,
        )
        self._teams[team.id] = team
        self._team_count += 1

        for mid in member_ids:
            self._ensure_agent_registered(mid)

        request.state = ProtocolState.ACCEPTED

        session = CollaborationSession(
            team_id=team.id,
            team=team,
        )
        self._sessions[session.id] = session
        self._session_count += 1

        return team

    def initiate_handoff(
        self,
        team_id: str,
        from_agent: str,
        to_agent: str,
        task_context: str,
        handoff_type: str = "delegate",
    ) -> HandoffRecord:
        team = self._teams.get(team_id)
        if not team:
            raise ValueError(f"Team not found: {team_id}")

        if from_agent not in team.member_ids:
            raise ValueError(
                f"Agent {from_agent} is not a member of team {team_id}"
            )
        if to_agent not in team.member_ids:
            raise ValueError(
                f"Agent {to_agent} is not a member of team {team_id}"
            )

        ht = HandoffType(handoff_type)

        handoff = HandoffRecord(
            team_id=team_id,
            from_agent=from_agent,
            to_agent=to_agent,
            task_context=task_context,
            handoff_type=ht,
        )
        self._handoffs[handoff.id] = handoff
        self._handoff_count += 1

        session = self._find_session_by_team(team_id)
        if session:
            session.handoffs.append(handoff)

        return handoff

    def accept_handoff(
        self,
        handoff_id: str,
        agent_id: str,
        notes: str = "",
    ) -> bool:
        handoff = self._handoffs.get(handoff_id)
        if not handoff:
            return False

        if handoff.state != ProtocolState.PROPOSED:
            return False

        if agent_id != handoff.to_agent:
            return False

        handoff.state = ProtocolState.ACCEPTED
        handoff.accepted_at = time.time()
        handoff.notes = notes

        handoff.state = ProtocolState.IN_PROGRESS
        self._ensure_agent_registered(agent_id)
        return True

    def complete_handoff(
        self,
        handoff_id: str,
        results: Optional[Dict[str, Any]] = None,
    ) -> bool:
        handoff = self._handoffs.get(handoff_id)
        if not handoff:
            return False

        if handoff.state not in (ProtocolState.ACCEPTED, ProtocolState.IN_PROGRESS):
            return False

        handoff.state = ProtocolState.COMPLETED
        handoff.completed_at = time.time()
        handoff.results = results or {}
        self._completed_handoff_count += 1

        session = self._find_session_by_team(handoff.team_id)
        if session:
            all_done = True
            for h in session.handoffs:
                if h.id == handoff_id:
                    continue
                if h.state not in (ProtocolState.COMPLETED, ProtocolState.REJECTED):
                    all_done = False
                    break
            if all_done and session.handoffs:
                session.state = ProtocolState.COMPLETED
                session.ended_at = time.time()

        return True

    def reject_handoff(
        self,
        handoff_id: str,
        agent_id: str,
        reason: str = "",
    ) -> bool:
        handoff = self._handoffs.get(handoff_id)
        if not handoff:
            return False

        if handoff.state != ProtocolState.PROPOSED:
            return False

        if agent_id != handoff.to_agent:
            return False

        handoff.state = ProtocolState.REJECTED
        handoff.notes = reason
        self._rejected_count += 1
        return True

    def get_active_sessions(self) -> List[CollaborationSession]:
        return [
            session for session in self._sessions.values()
            if session.state == ProtocolState.IN_PROGRESS
        ]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if session:
            return session.to_dict()
        return None

    def get_team_handoffs(self, team_id: str) -> List[HandoffRecord]:
        session = self._find_session_by_team(team_id)
        if session:
            return session.handoffs
        return [
            h for h in self._handoffs.values()
            if h.team_id == team_id
        ]

    def get_agent_workload(self, agent_id: str) -> Dict[str, Any]:
        active_handoffs = 0
        pending_handoffs = 0
        completed_handoffs = 0
        rejected_handoffs = 0

        for handoff in self._handoffs.values():
            if handoff.to_agent == agent_id:
                if handoff.state == ProtocolState.PROPOSED:
                    pending_handoffs += 1
                elif handoff.state in (ProtocolState.ACCEPTED, ProtocolState.IN_PROGRESS):
                    active_handoffs += 1
                elif handoff.state == ProtocolState.COMPLETED:
                    completed_handoffs += 1
                elif handoff.state == ProtocolState.REJECTED:
                    rejected_handoffs += 1

            if handoff.from_agent == agent_id:
                if handoff.state == ProtocolState.PROPOSED:
                    pending_handoffs += 1

        teams_leading = sum(
            1 for t in self._teams.values()
            if t.lead_id == agent_id
        )
        teams_member = sum(
            1 for t in self._teams.values()
            if agent_id in t.member_ids
        )

        total_handoffs = active_handoffs + pending_handoffs + completed_handoffs + rejected_handoffs

        return {
            "agent_id": agent_id,
            "active_handoffs": active_handoffs,
            "pending_handoffs": pending_handoffs,
            "completed_handoffs": completed_handoffs,
            "rejected_handoffs": rejected_handoffs,
            "total_handoffs_involved": total_handoffs,
            "teams_leading": teams_leading,
            "teams_as_member": teams_member,
            "utilization_percent": (
                round(active_handoffs / max(total_handoffs, 1) * 100, 1)
                if total_handoffs > 0 else 0.0
            ),
        }

    def broadcast_message(
        self,
        team_id: str,
        sender_id: str,
        message: str,
        priority: int = 0,
    ) -> bool:
        team = self._teams.get(team_id)
        if not team:
            return False

        if sender_id not in team.member_ids:
            return False

        session = self._find_session_by_team(team_id)
        if not session:
            return False

        session.messages.append({
            "id": uuid.uuid4().hex,
            "sender_id": sender_id,
            "message": message,
            "priority": priority,
            "timestamp": time.time(),
        })
        return True

    def resolve_conflict(
        self,
        team_id: str,
        agent_a: str,
        agent_b: str,
        mediator_id: str = "",
    ) -> Dict[str, Any]:
        team = self._teams.get(team_id)
        if not team:
            return {"error": "Team not found", "resolved": False}

        if agent_a not in team.member_ids or agent_b not in team.member_ids:
            return {"error": "One or both agents not in team", "resolved": False}

        conflicting_handoffs: List[str] = []
        for handoff in self._handoffs.values():
            if handoff.team_id != team_id:
                continue
            if handoff.state != ProtocolState.COMPLETED:
                continue
            agents = {handoff.from_agent, handoff.to_agent}
            if agent_a in agents and agent_b in agents:
                conflicting_handoffs.append(handoff.id)

        mediator = mediator_id if mediator_id and mediator_id in team.member_ids else team.lead_id

        resolution_strategy = "lead_decision"
        if mediator == agent_a or mediator == agent_b:
            resolution_strategy = "self_resolution"

        resolved = len(conflicting_handoffs) > 0 or bool(mediator)

        return {
            "team_id": team_id,
            "agent_a": agent_a,
            "agent_b": agent_b,
            "mediator": mediator,
            "resolved": resolved,
            "resolution_strategy": resolution_strategy,
            "conflicting_handoffs": conflicting_handoffs,
            "conflict_count": len(conflicting_handoffs),
            "resolved_at": time.time(),
        }

    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        request = self._requests.get(request_id)
        if request:
            return request.to_dict()
        return None

    def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        team = self._teams.get(team_id)
        if team:
            return team.to_dict()
        return None

    def get_handoff(self, handoff_id: str) -> Optional[Dict[str, Any]]:
        handoff = self._handoffs.get(handoff_id)
        if handoff:
            return handoff.to_dict()
        return None

    def list_teams(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._teams.values()]

    def list_requests(self, state_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        if state_filter:
            ps = ProtocolState(state_filter)
            return [r.to_dict() for r in self._requests.values() if r.state == ps]
        return [r.to_dict() for r in self._requests.values()]

    def _find_session_by_team(self, team_id: str) -> Optional[CollaborationSession]:
        for session in self._sessions.values():
            if session.team_id == team_id:
                return session
        return None

    def _ensure_agent_registered(self, agent_id: str) -> None:
        if agent_id not in self._agent_registry:
            self._agent_registry[agent_id] = {
                "registered_at": time.time(),
                "total_handoffs_received": 0,
                "total_handoffs_sent": 0,
                "teams_joined": 0,
            }

    def register_agent_expertise(
        self,
        agent_id: str,
        domains: List[str],
        proficiency_levels: Optional[Dict[str, float]] = None,
    ) -> None:
        """Register an agent's expertise domains and proficiency levels for 
        intelligent task-to-agent assignment.
        
        Args:
            agent_id: Unique agent identifier
            domains: List of expertise domains (e.g., 'combat_design', 'level_art')
            proficiency_levels: Optional proficiency scores per domain (0.0-1.0)
        """
        self._ensure_agent_registered(agent_id)
        levels = proficiency_levels or {}
        self._agent_registry[agent_id].update({
            "expertise_domains": domains,
            "proficiency_levels": {d: levels.get(d, 0.5) for d in domains},
            "expertise_registered_at": time.time(),
        })

    def assign_by_expertise(
        self,
        team_id: str,
        task_context: str,
        handoff_type: str = "delegate",
    ) -> Optional[HandoffRecord]:
        """Auto-assign a task to the most qualified agent in a team based on 
        domain expertise matching.
        
        Uses keyword overlap scoring between the task context and registered 
        agent expertise domains to compute the best assignment.
        """
        team = self._teams.get(team_id)
        if not team:
            return None

        task_lower = task_context.lower()
        task_keywords = set(task_lower.replace(",", " ").replace(".", " ").split())

        best_agent_id: str = ""
        best_score: float = -1.0

        for member_id in team.member_ids:
            agent_info = self._agent_registry.get(member_id, {})
            domains = agent_info.get("expertise_domains", [])
            levels = agent_info.get("proficiency_levels", {})

            if not domains:
                score = 0.0
            else:
                score = sum(
                    levels.get(d, 0.5) * 2.0 if d.lower() in task_lower else 0.0
                    for d in domains
                )
                for kw in task_keywords:
                    for d in domains:
                        if kw in d.lower() or d.lower() in kw:
                            score += levels.get(d, 0.5)

            # Penalize agents with high active workload
            workload = self.get_agent_workload(member_id)
            active = workload.get("active_handoffs", 0)
            score = score * (1.0 / max(1.0, 1.0 + active * 0.15))

            if score > best_score:
                best_score = score
                best_agent_id = member_id

        if not best_agent_id:
            return None

        # Find the team lead as the delegator
        from_agent = team.lead_id if team.lead_id else team.member_ids[0]
        if from_agent == best_agent_id and len(team.member_ids) > 1:
            from_agent = [m for m in team.member_ids if m != best_agent_id][0]

        return self.initiate_handoff(
            team_id=team_id,
            from_agent=from_agent,
            to_agent=best_agent_id,
            task_context=f"[Auto-assigned] {task_context}",
            handoff_type=handoff_type,
        )

    def balance_workload(self, team_id: str) -> List[Dict[str, Any]]:
        """Analyze and suggest workload balancing recommendations for a team.
        
        Returns a list of suggested reassignments to distribute work evenly.
        """
        team = self._teams.get(team_id)
        if not team:
            return []

        workloads = {}
        for member_id in team.member_ids:
            wl = self.get_agent_workload(member_id)
            workloads[member_id] = wl["active_handoffs"]

        if not workloads:
            return []

        avg_workload = sum(workloads.values()) / len(workloads)
        max_workload = max(workloads.values())
        min_workload = min(workloads.values())

        recommendations = []
        overloaded = [mid for mid, wl in workloads.items() if wl > avg_workload + 1]
        underloaded = [mid for mid, wl in workloads.items() if wl < avg_workload]

        for over in overloaded:
            for under in underloaded:
                suggestions = []
                for handoff in self._handoffs.values():
                    if handoff.team_id == team_id and handoff.to_agent == over:
                        if handoff.state in (ProtocolState.PROPOSED, ProtocolState.ACCEPTED):
                            suggestions.append({
                                "handoff_id": handoff.id,
                                "task": handoff.task_context[:60],
                                "state": handoff.state.value,
                            })
                if suggestions:
                    recommendations.append({
                        "from_agent": over,
                        "to_agent": under,
                        "from_workload": workloads[over],
                        "to_workload": workloads[under],
                        "suggested_transfers": suggestions[:2],
                    })

        return {
            "team_id": team_id,
            "average_workload": round(avg_workload, 1),
            "max_workload": max_workload,
            "min_workload": min_workload,
            "is_balanced": max_workload - min_workload <= 1,
            "member_workloads": workloads,
            "recommendations": recommendations,
        }

    def get_team_efficiency(self, team_id: str) -> Dict[str, Any]:
        """Calculate comprehensive team performance metrics."""
        team = self._teams.get(team_id)
        if not team:
            return {"error": "Team not found"}

        team_handoffs = [h for h in self._handoffs.values() if h.team_id == team_id]
        completed = [h for h in team_handoffs if h.state == ProtocolState.COMPLETED]
        rejected = [h for h in team_handoffs if h.state == ProtocolState.REJECTED]

        # Completion time metrics
        completion_times = []
        for h in completed:
            if h.completed_at and h.created_at:
                completion_times.append(h.completed_at - h.created_at)

        avg_completion_time = (
            round(sum(completion_times) / len(completion_times), 2)
            if completion_times else 0.0
        )

        # Per-agent efficiency
        agent_metrics = {}
        for member_id in team.member_ids:
            agent_completed = sum(
                1 for h in completed if h.to_agent == member_id or h.from_agent == member_id
            )
            agent_total = sum(
                1 for h in team_handoffs
                if h.to_agent == member_id or h.from_agent == member_id
            )
            agent_metrics[member_id] = {
                "completed": agent_completed,
                "total": agent_total,
                "completion_rate": (
                    round(agent_completed / max(agent_total, 1), 3)
                    if agent_total > 0 else 0.0
                ),
            }

        handoff_type_breakdown = {}
        for h in team_handoffs:
            ht = h.handoff_type.value
            if ht not in handoff_type_breakdown:
                handoff_type_breakdown[ht] = {"total": 0, "completed": 0}
            handoff_type_breakdown[ht]["total"] += 1
            if h.state == ProtocolState.COMPLETED:
                handoff_type_breakdown[ht]["completed"] += 1

        session = self._find_session_by_team(team_id)
        return {
            "team_id": team_id,
            "member_count": len(team.member_ids),
            "total_handoffs": len(team_handoffs),
            "completed_handoffs": len(completed),
            "rejected_handoffs": len(rejected),
            "pending_handoffs": len(team_handoffs) - len(completed) - len(rejected),
            "overall_completion_rate": (
                round(len(completed) / max(len(team_handoffs), 1), 3)
                if team_handoffs else 0.0
            ),
            "avg_completion_time_seconds": avg_completion_time,
            "total_messages": len(session.messages) if session else 0,
            "per_agent_metrics": agent_metrics,
            "handoff_type_breakdown": {
                k: {**v, "success_rate": round(v["completed"] / max(v["total"], 1), 3)}
                for k, v in handoff_type_breakdown.items()
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        role_distribution: Dict[str, int] = {}
        for team in self._teams.values():
            for role in team.roles.values():
                role_distribution[role] = role_distribution.get(role, 0) + 1

        handoff_type_distribution: Dict[str, int] = {}
        for handoff in self._handoffs.values():
            ht = handoff.handoff_type.value
            handoff_type_distribution[ht] = handoff_type_distribution.get(ht, 0) + 1

        handoff_state_distribution: Dict[str, int] = {}
        for handoff in self._handoffs.values():
            st = handoff.state.value
            handoff_state_distribution[st] = handoff_state_distribution.get(st, 0) + 1

        total_messages = sum(
            len(s.messages) for s in self._sessions.values()
        )

        avg_team_size = 0.0
        if self._team_count > 0:
            total_members = sum(len(t.member_ids) for t in self._teams.values())
            avg_team_size = round(total_members / self._team_count, 1)

        pending_total = handoff_state_distribution.get("proposed", 0)

        return {
            "total_requests": self._request_count,
            "total_teams": self._team_count,
            "total_handoffs": self._handoff_count,
            "total_sessions": self._session_count,
            "completed_handoffs": self._completed_handoff_count,
            "rejected_handoffs": self._rejected_count,
            "active_sessions": len(self.get_active_sessions()),
            "registered_agents": len(self._agent_registry),
            "pending_handoffs": pending_total,
            "completion_rate": (
                round(self._completed_handoff_count / max(self._handoff_count, 1), 3)
                if self._handoff_count > 0 else 0.0
            ),
            "rejection_rate": (
                round(self._rejected_count / max(self._handoff_count, 1), 3)
                if self._handoff_count > 0 else 0.0
            ),
            "total_messages": total_messages,
            "avg_team_size": avg_team_size,
            "by_handoff_type": handoff_type_distribution,
            "by_handoff_state": handoff_state_distribution,
            "by_role": role_distribution,
            "available_handoff_types": [ht.value for ht in HandoffType],
            "available_agent_roles": [ar.value for ar in AgentRole],
            "available_states": [ps.value for ps in ProtocolState],
        }

    def reset(self) -> None:
        self._requests.clear()
        self._teams.clear()
        self._handoffs.clear()
        self._sessions.clear()
        self._request_count = 0
        self._team_count = 0
        self._handoff_count = 0
        self._session_count = 0
        self._rejected_count = 0
        self._completed_handoff_count = 0
        self._agent_registry.clear()


_collaboration_protocol = CollaborationProtocolEngine.get_instance()


def get_collaboration_protocol() -> CollaborationProtocolEngine:
    return _collaboration_protocol