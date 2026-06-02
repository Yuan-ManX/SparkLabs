"""
SparkLabs Agent - Multi-Agent Coordinator

AI-driven multi-agent coordination system for complex game scenarios.
Manages agent teams, role assignments, communication channels, task
allocation, synergy networks, and tactical formation positioning.

Architecture:
  AgentMultiAgentCoordinator
    |-- AgentTeam (squad composition with formation patterns)
    |-- TeamMember (individual agent role within a team)
    |-- CoordinationEvent (inter-agent messaging event)
    |-- TaskAllocation (capability-driven task distribution)
    |-- CapabilityMatrix (agent skill vector assessment)
    |-- SynergyNetwork (pair-wise agent synergy graph)

Coordination Modes:
  - HIERARCHICAL: top-down command from team leader
  - CONSENSUS: unanimous agreement among team members
  - AUCTION: bid-based task claiming
  - VOTING: democratic decision by majority
  - SWARM: emergent behavior from simple rules
  - COMMAND_CHAIN: sequential delegated authority
  - ROLE_BASED: role-determined action routing
  - AUCTION_MARKET: resource-allocated bidding
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TeamRole(Enum):
    LEADER = "leader"
    SCOUT = "scout"
    TANK = "tank"
    HEALER = "healer"
    DPS = "dps"
    SUPPORT = "support"
    SNIPER = "sniper"
    ENGINEER = "engineer"
    DIPLOMAT = "diplomat"
    INFILTRATOR = "infiltrator"


class CoordinationMode(Enum):
    HIERARCHICAL = "hierarchical"
    CONSENSUS = "consensus"
    AUCTION = "auction"
    VOTING = "voting"
    SWARM = "swarm"
    COMMAND_CHAIN = "command_chain"
    ROLE_BASED = "role_based"
    AUCTION_MARKET = "auction_market"


class CommunicationChannel(Enum):
    BROADCAST = "broadcast"
    DIRECT = "direct"
    WHISPER = "whisper"
    TEAM = "team"
    FACTION = "faction"
    GLOBAL = "global"
    EMERGENCY = "emergency"


class AgentState(Enum):
    IDLE = "idle"
    BUSY = "busy"
    WAITING = "waiting"
    NEEDS_HELP = "needs_help"
    RETREATING = "retreating"
    COORDINATING = "coordinating"
    EXECUTING = "executing"


# Pre-defined formation patterns for tactical positioning
FORMATION_PATTERNS: Dict[str, List[Tuple[float, float]]] = {
    "line": [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (4.0, 0.0),
             (5.0, 0.0), (6.0, 0.0), (7.0, 0.0), (8.0, 0.0), (9.0, 0.0)],
    "wedge": [(0.0, 0.0), (1.0, -0.5), (1.0, 0.5), (2.0, -1.0), (2.0, 1.0),
              (3.0, -1.5), (3.0, 1.5), (4.0, -2.0), (4.0, 2.0), (5.0, -2.5)],
    "circle": [(0.0, 3.0), (1.85, 2.31), (2.85, 0.93), (2.85, -0.93),
               (1.85, -2.31), (0.0, -3.0), (-1.85, -2.31), (-2.85, -0.93),
               (-2.85, 0.93), (-1.85, 2.31)],
    "diamond": [(0.0, 3.0), (1.5, 1.5), (3.0, 0.0), (1.5, -1.5), (0.0, -3.0),
                (-1.5, -1.5), (-3.0, 0.0), (-1.5, 1.5), (0.0, 0.0), (0.0, 0.0)],
    "column": [(0.0, 0.0), (0.0, 2.0), (0.0, 4.0), (0.0, 6.0), (0.0, 8.0),
               (0.0, 10.0), (0.0, 12.0), (0.0, 14.0), (0.0, 16.0), (0.0, 18.0)],
    "v_shape": [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 3.0), (4.0, 4.0),
                (-1.0, 1.0), (-2.0, 2.0), (-3.0, 3.0), (-4.0, 4.0),
                (0.0, 5.0)],
    "flanking": [(0.0, 0.0), (3.0, 2.0), (-3.0, 2.0), (6.0, 4.0), (-6.0, 4.0),
                 (1.5, -2.0), (-1.5, -2.0), (4.5, -4.0), (-4.5, -4.0),
                 (0.0, 6.0)],
    "arrowhead": [(0.0, 0.0), (1.0, 0.5), (1.0, -0.5), (2.0, 1.0), (2.0, -1.0),
                  (3.0, 0.0), (4.0, 0.5), (4.0, -0.5), (5.0, 0.0), (6.0, 0.0)],
    "shield_wall": [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (4.0, 0.0),
                    (0.0, -1.0), (1.0, -1.0), (2.0, -1.0), (3.0, -1.0),
                    (4.0, -1.0)],
    "scattered": [(0.0, 0.0), (2.5, -1.2), (-3.1, 2.3), (1.8, -3.4), (-2.0, -1.8),
                  (3.8, 1.1), (-1.5, 3.6), (4.2, -2.9), (-4.0, -0.5),
                  (0.7, 4.1)],
}

# Role capability profiles - base aptitude vectors per role
ROLE_CAPABILITY_PROFILES: Dict[TeamRole, Dict[str, float]] = {
    TeamRole.LEADER: {"combat": 0.65, "healing": 0.15, "scouting": 0.40,
                      "crafting": 0.20, "stealth": 0.20, "social": 0.95,
                      "command": 0.95, "tactics": 0.90, "resilience": 0.60},
    TeamRole.SCOUT: {"combat": 0.35, "healing": 0.05, "scouting": 0.95,
                     "crafting": 0.10, "stealth": 0.85, "social": 0.25,
                     "command": 0.15, "tactics": 0.45, "resilience": 0.30},
    TeamRole.TANK: {"combat": 0.80, "healing": 0.10, "scouting": 0.15,
                    "crafting": 0.10, "stealth": 0.05, "social": 0.20,
                    "command": 0.30, "tactics": 0.35, "resilience": 0.95},
    TeamRole.HEALER: {"combat": 0.15, "healing": 0.95, "scouting": 0.15,
                      "crafting": 0.30, "stealth": 0.15, "social": 0.50,
                      "command": 0.20, "tactics": 0.20, "resilience": 0.40},
    TeamRole.DPS: {"combat": 0.95, "healing": 0.05, "scouting": 0.20,
                   "crafting": 0.05, "stealth": 0.25, "social": 0.10,
                   "command": 0.10, "tactics": 0.30, "resilience": 0.25},
    TeamRole.SUPPORT: {"combat": 0.40, "healing": 0.65, "scouting": 0.25,
                       "crafting": 0.55, "stealth": 0.15, "social": 0.60,
                       "command": 0.50, "tactics": 0.45, "resilience": 0.50},
    TeamRole.SNIPER: {"combat": 0.90, "healing": 0.05, "scouting": 0.60,
                      "crafting": 0.05, "stealth": 0.70, "social": 0.05,
                      "command": 0.05, "tactics": 0.25, "resilience": 0.15},
    TeamRole.ENGINEER: {"combat": 0.30, "healing": 0.10, "scouting": 0.20,
                        "crafting": 0.95, "stealth": 0.15, "social": 0.25,
                        "command": 0.35, "tactics": 0.55, "resilience": 0.45},
    TeamRole.DIPLOMAT: {"combat": 0.10, "healing": 0.20, "scouting": 0.20,
                        "crafting": 0.15, "stealth": 0.10, "social": 0.98,
                        "command": 0.60, "tactics": 0.50, "resilience": 0.35},
    TeamRole.INFILTRATOR: {"combat": 0.55, "healing": 0.05, "scouting": 0.75,
                           "crafting": 0.15, "stealth": 0.95, "social": 0.45,
                           "command": 0.10, "tactics": 0.30, "resilience": 0.30},
}

# Coordination strategy configurations per coordination mode
COORDINATION_STRATEGIES: Dict[CoordinationMode, Dict[str, Any]] = {
    CoordinationMode.HIERARCHICAL: {
        "decision_speed": 0.85, "accuracy": 0.70, "adaptability": 0.30,
        "communication_cost": 0.20, "conflict_resolution": "leader_decides",
        "min_members": 2, "requires_leader": True,
    },
    CoordinationMode.CONSENSUS: {
        "decision_speed": 0.25, "accuracy": 0.95, "adaptability": 0.50,
        "communication_cost": 0.80, "conflict_resolution": "unanimous",
        "min_members": 3, "requires_leader": False,
    },
    CoordinationMode.AUCTION: {
        "decision_speed": 0.60, "accuracy": 0.80, "adaptability": 0.65,
        "communication_cost": 0.55, "conflict_resolution": "highest_bid",
        "min_members": 2, "requires_leader": False,
    },
    CoordinationMode.VOTING: {
        "decision_speed": 0.55, "accuracy": 0.75, "adaptability": 0.55,
        "communication_cost": 0.45, "conflict_resolution": "majority",
        "min_members": 3, "requires_leader": False,
    },
    CoordinationMode.SWARM: {
        "decision_speed": 0.70, "accuracy": 0.60, "adaptability": 0.90,
        "communication_cost": 0.30, "conflict_resolution": "emergent",
        "min_members": 4, "requires_leader": False,
    },
    CoordinationMode.COMMAND_CHAIN: {
        "decision_speed": 0.50, "accuracy": 0.82, "adaptability": 0.40,
        "communication_cost": 0.35, "conflict_resolution": "chain_of_command",
        "min_members": 3, "requires_leader": True,
    },
    CoordinationMode.ROLE_BASED: {
        "decision_speed": 0.65, "accuracy": 0.78, "adaptability": 0.60,
        "communication_cost": 0.40, "conflict_resolution": "role_priority",
        "min_members": 2, "requires_leader": False,
    },
    CoordinationMode.AUCTION_MARKET: {
        "decision_speed": 0.45, "accuracy": 0.85, "adaptability": 0.55,
        "communication_cost": 0.65, "conflict_resolution": "market_price",
        "min_members": 3, "requires_leader": False,
    },
}

# Mission type templates for team composition optimization
MISSION_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "assault": {
        "priority_roles": [TeamRole.LEADER, TeamRole.TANK, TeamRole.DPS, TeamRole.HEALER],
        "secondary_roles": [TeamRole.SUPPORT, TeamRole.SNIPER],
        "preferred_formation": "wedge",
        "ideal_size": 6,
    },
    "reconnaissance": {
        "priority_roles": [TeamRole.SCOUT, TeamRole.INFILTRATOR, TeamRole.SNIPER],
        "secondary_roles": [TeamRole.LEADER, TeamRole.ENGINEER],
        "preferred_formation": "scattered",
        "ideal_size": 4,
    },
    "defense": {
        "priority_roles": [TeamRole.TANK, TeamRole.ENGINEER, TeamRole.SUPPORT],
        "secondary_roles": [TeamRole.LEADER, TeamRole.DPS, TeamRole.SNIPER],
        "preferred_formation": "shield_wall",
        "ideal_size": 7,
    },
    "diplomacy": {
        "priority_roles": [TeamRole.DIPLOMAT, TeamRole.LEADER],
        "secondary_roles": [TeamRole.SUPPORT, TeamRole.SCOUT],
        "preferred_formation": "circle",
        "ideal_size": 3,
    },
    "infiltration": {
        "priority_roles": [TeamRole.INFILTRATOR, TeamRole.SCOUT],
        "secondary_roles": [TeamRole.ENGINEER, TeamRole.SNIPER],
        "preferred_formation": "scattered",
        "ideal_size": 3,
    },
    "escort": {
        "priority_roles": [TeamRole.TANK, TeamRole.HEALER, TeamRole.LEADER],
        "secondary_roles": [TeamRole.DPS, TeamRole.SUPPORT, TeamRole.SCOUT],
        "preferred_formation": "diamond",
        "ideal_size": 6,
    },
    "siege": {
        "priority_roles": [TeamRole.ENGINEER, TeamRole.TANK, TeamRole.DPS],
        "secondary_roles": [TeamRole.LEADER, TeamRole.SUPPORT, TeamRole.SNIPER],
        "preferred_formation": "line",
        "ideal_size": 7,
    },
    "rescue": {
        "priority_roles": [TeamRole.HEALER, TeamRole.SCOUT, TeamRole.TANK],
        "secondary_roles": [TeamRole.LEADER, TeamRole.SUPPORT],
        "preferred_formation": "v_shape",
        "ideal_size": 5,
    },
}


@dataclass
class CoordinationEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str = ""
    source_agent: str = ""
    target_agents: List[str] = field(default_factory=list)
    message: str = ""
    priority: int = 1
    timestamp: float = field(default_factory=lambda: _time_module.time())
    requires_response: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "source_agent": self.source_agent,
            "target_agents": self.target_agents,
            "message": self.message,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "requires_response": self.requires_response,
        }


@dataclass
class TeamMember:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    role: TeamRole = TeamRole.SUPPORT
    assigned_task: str = ""
    capability_vector: Dict[str, float] = field(default_factory=dict)
    readiness: float = 1.0
    trust_level: float = 0.5
    contribution_score: float = 0.0
    state: AgentState = AgentState.IDLE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "role": self.role.value,
            "assigned_task": self.assigned_task,
            "capability_vector": self.capability_vector,
            "readiness": self.readiness,
            "trust_level": self.trust_level,
            "contribution_score": self.contribution_score,
            "state": self.state.value,
        }


@dataclass
class AgentTeam:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    members: List[TeamMember] = field(default_factory=list)
    team_role: TeamRole = TeamRole.LEADER
    coordination_mode: CoordinationMode = CoordinationMode.HIERARCHICAL
    formation_pattern: str = "line"
    comm_channel: CommunicationChannel = CommunicationChannel.TEAM
    objective: str = ""
    cohesion_score: float = 0.5
    synergy_bonuses: Dict[str, float] = field(default_factory=dict)
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "member_count": len(self.members),
            "members": [m.to_dict() for m in self.members],
            "team_role": self.team_role.value,
            "coordination_mode": self.coordination_mode.value,
            "formation_pattern": self.formation_pattern,
            "comm_channel": self.comm_channel.value,
            "objective": self.objective,
            "cohesion_score": self.cohesion_score,
            "synergy_bonuses": self.synergy_bonuses,
            "active": self.active,
        }


@dataclass
class TaskAllocation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_description: str = ""
    required_capabilities: Dict[str, float] = field(default_factory=dict)
    assigned_agent: str = ""
    priority: int = 1
    deadline: float = 0.0
    status: str = "pending"
    dependency_tasks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_description": self.task_description,
            "required_capabilities": self.required_capabilities,
            "assigned_agent": self.assigned_agent,
            "priority": self.priority,
            "deadline": self.deadline,
            "status": self.status,
            "dependency_tasks": self.dependency_tasks,
        }


@dataclass
class CapabilityMatrix:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    capabilities: Dict[str, float] = field(default_factory=dict)
    specialization: str = "generalist"
    level: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "specialization": self.specialization,
            "level": self.level,
        }


@dataclass
class SynergyNetwork:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_pairs: List[Tuple[str, str]] = field(default_factory=list)
    synergy_type: str = "complementary"
    synergy_strength: float = 0.0
    shared_history_count: int = 0
    combined_capability_bonus: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_pairs": [list(pair) for pair in self.agent_pairs],
            "synergy_type": self.synergy_type,
            "synergy_strength": self.synergy_strength,
            "shared_history_count": self.shared_history_count,
            "combined_capability_bonus": self.combined_capability_bonus,
        }


class AgentMultiAgentCoordinator:
    """
    AI-driven multi-agent coordination system for complex game scenarios.

    Orchestrates agent teams through role assignment, capability-based
    task allocation, synergy computation, communication broadcasting,
    and tactical formation positioning across multiple coordination modes.
    """

    _instance: Optional[AgentMultiAgentCoordinator] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> AgentMultiAgentCoordinator:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> AgentMultiAgentCoordinator:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._teams: Dict[str, AgentTeam] = {}
        self._tasks: Dict[str, TaskAllocation] = {}
        self._capability_matrices: Dict[str, CapabilityMatrix] = {}
        self._synergy_networks: Dict[str, SynergyNetwork] = {}
        self._event_log: List[CoordinationEvent] = []
        self._team_count: int = 0
        self._task_count: int = 0
        self._completed_task_count: int = 0
        self._failed_task_count: int = 0
        self._coordination_rounds: int = 0
        self._formation_positions: Dict[str, List[Tuple[float, float]]] = {}
        self._initialized: bool = True

    def form_team(
        self,
        name: str,
        members: List[Dict[str, Any]],
        coordination_mode: str = "hierarchical",
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        mode = CoordinationMode(coordination_mode)
        team_members: List[TeamMember] = []

        for member_data in members:
            role = TeamRole(member_data.get("role", "support"))
            profile = ROLE_CAPABILITY_PROFILES.get(role, ROLE_CAPABILITY_PROFILES[TeamRole.SUPPORT])
            member = TeamMember(
                agent_id=member_data.get("agent_id", uuid.uuid4().hex),
                role=role,
                capability_vector=dict(profile),
                readiness=member_data.get("readiness", 1.0),
            )
            team_members.append(member)

        team = AgentTeam(
            name=name,
            members=team_members,
            coordination_mode=mode,
            formation_pattern=self._default_formation_for_mode(mode),
            objective="",
            cohesion_score=0.5,
        )
        self._teams[team.id] = team
        self._team_count += 1

        self._event_log.append(CoordinationEvent(
            event_type="team_formed",
            source_agent="coordinator",
            target_agents=[m.agent_id for m in team_members],
            message=f"Team '{name}' formed with {len(team_members)} members",
            priority=3,
        ))
        return team.to_dict()

    def assign_roles(
        self,
        team_id: str,
        member_roles: Dict[str, str],
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        team = self._teams.get(team_id)
        if not team:
            return {"error": "Team not found"}

        assigned: List[str] = []
        for member in team.members:
            if member.agent_id in member_roles:
                new_role = TeamRole(member_roles[member.agent_id])
                member.role = new_role
                profile = ROLE_CAPABILITY_PROFILES.get(new_role, ROLE_CAPABILITY_PROFILES[TeamRole.SUPPORT])
                member.capability_vector = dict(profile)
                assigned.append(member.agent_id)

        self._event_log.append(CoordinationEvent(
            event_type="roles_assigned",
            source_agent="coordinator",
            target_agents=assigned,
            message=f"Roles assigned for team {team_id}: {member_roles}",
            priority=2,
        ))
        return {"team_id": team_id, "assigned": assigned}

    def allocate_task(
        self,
        team_id: str,
        task: Dict[str, Any],
        capabilities_needed: Dict[str, float],
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        team = self._teams.get(team_id)
        if not team:
            return {"error": "Team not found"}

        best_member: Optional[TeamMember] = None
        best_score: float = -1.0

        for member in team.members:
            if member.state != AgentState.IDLE and member.state != AgentState.WAITING:
                continue
            score = self._compute_capability_match(member.capability_vector, capabilities_needed)
            score *= member.readiness * member.trust_level
            if score > best_score:
                best_score = score
                best_member = member

        if best_member is None:
            return {"error": "No available member found for task"}

        allocation = TaskAllocation(
            task_description=task.get("description", ""),
            required_capabilities=dict(capabilities_needed),
            assigned_agent=best_member.agent_id,
            priority=task.get("priority", 1),
            deadline=task.get("deadline", _time_module.time() + 3600.0),
            status="assigned",
        )
        self._tasks[allocation.id] = allocation
        self._task_count += 1
        best_member.assigned_task = allocation.id
        best_member.state = AgentState.BUSY

        self._event_log.append(CoordinationEvent(
            event_type="task_allocated",
            source_agent="coordinator",
            target_agents=[best_member.agent_id],
            message=f"Task '{task.get('description', '')}' allocated to {best_member.agent_id}",
            priority=task.get("priority", 1),
        ))
        return allocation.to_dict()

    def compute_capability_matrix(self, agent_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        if agent_id in self._capability_matrices:
            return self._capability_matrices[agent_id].to_dict()

        base_caps: Dict[str, float] = {
            "stealth": random.uniform(0.1, 0.9),
            "combat": random.uniform(0.1, 0.9),
            "social": random.uniform(0.1, 0.9),
            "crafting": random.uniform(0.1, 0.9),
            "scouting": random.uniform(0.1, 0.9),
            "healing": random.uniform(0.1, 0.9),
        }

        dominant = max(base_caps, key=lambda k: base_caps[k])
        level = 1
        if base_caps[dominant] > 0.7:
            level = 3
        elif base_caps[dominant] > 0.5:
            level = 2

        matrix = CapabilityMatrix(
            agent_id=agent_id,
            capabilities=base_caps,
            specialization=dominant,
            level=level,
        )
        self._capability_matrices[agent_id] = matrix
        return matrix.to_dict()

    def calculate_synergy(
        self,
        agent_a: str,
        agent_b: str,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        pair_key = self._synergy_pair_key(agent_a, agent_b)
        if pair_key in self._synergy_networks:
            return self._synergy_networks[pair_key].to_dict()

        matrix_a = self._capability_matrices.get(agent_a)
        matrix_b = self._capability_matrices.get(agent_b)

        if matrix_a is None:
            self.compute_capability_matrix(agent_a)
            matrix_a = self._capability_matrices[agent_a]
        if matrix_b is None:
            self.compute_capability_matrix(agent_b)
            matrix_b = self._capability_matrices[agent_b]

        caps_a = matrix_a.capabilities
        caps_b = matrix_b.capabilities

        complementary_score = 0.0
        overlap_score = 0.0
        for key in caps_a:
            diff = abs(caps_a[key] - caps_b[key])
            if diff > 0.4:
                complementary_score += 1.0
            elif diff < 0.2:
                overlap_score += 1.0

        synergy_strength = (complementary_score * 0.7 + overlap_score * 0.3) / max(len(caps_a), 1)
        synergy_strength = min(1.0, synergy_strength + random.uniform(-0.05, 0.05))

        if synergy_strength > 0.6:
            synergy_type = "complementary"
        elif synergy_strength > 0.3:
            synergy_type = "moderate"
        else:
            synergy_type = "weak"

        network = SynergyNetwork(
            agent_pairs=[(agent_a, agent_b)],
            synergy_type=synergy_type,
            synergy_strength=round(synergy_strength, 3),
            shared_history_count=random.randint(0, 10),
            combined_capability_bonus=round(synergy_strength * 0.3, 3),
        )
        self._synergy_networks[pair_key] = network
        return network.to_dict()

    def coordinate_action(
        self,
        team_id: str,
        action_type: str,
        target: str,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        team = self._teams.get(team_id)
        if not team:
            return {"error": "Team not found"}

        strategy = COORDINATION_STRATEGIES.get(
            team.coordination_mode,
            COORDINATION_STRATEGIES[CoordinationMode.HIERARCHICAL],
        )

        leader: Optional[TeamMember] = None
        for member in team.members:
            if member.role == TeamRole.LEADER:
                leader = member
                break

        if strategy["requires_leader"] and leader is None:
            return {"error": "Leader required but not found for this coordination mode"}

        coord_result: Dict[str, Any] = {
            "team_id": team_id,
            "action_type": action_type,
            "target": target,
            "coordination_mode": team.coordination_mode.value,
            "decision_speed": strategy["decision_speed"],
            "expected_accuracy": strategy["accuracy"],
            "participants": [],
        }

        for member in team.members:
            if member.state == AgentState.IDLE:
                member.state = AgentState.COORDINATING
                coord_result["participants"].append({
                    "agent_id": member.agent_id,
                    "role": member.role.value,
                    "readiness": member.readiness,
                })

        self._coordination_rounds += 1
        self._event_log.append(CoordinationEvent(
            event_type="action_coordinated",
            source_agent=leader.agent_id if leader else "coordinator",
            target_agents=[p["agent_id"] for p in coord_result["participants"]],
            message=f"Coordinated {action_type} on {target}",
            priority=2,
        ))
        return coord_result

    def broadcast_message(
        self,
        channel: str,
        message: str,
        targets: List[str],
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        comm_channel = CommunicationChannel(channel)
        event = CoordinationEvent(
            event_type="broadcast",
            source_agent="coordinator",
            target_agents=list(targets),
            message=message,
            priority=2 if comm_channel == CommunicationChannel.EMERGENCY else 1,
            requires_response=comm_channel in (
                CommunicationChannel.DIRECT,
                CommunicationChannel.EMERGENCY,
            ),
        )
        self._event_log.append(event)
        return event.to_dict()

    def resolve_task_conflict(
        self,
        task_id: str,
        conflicting_agents: List[str],
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        task = self._tasks.get(task_id)
        if not task:
            return {"error": "Task not found"}

        if len(conflicting_agents) <= 1:
            winner = conflicting_agents[0] if conflicting_agents else ""
            task.assigned_agent = winner
            task.status = "assigned"
            return {"task_id": task_id, "winner": winner, "method": "no_conflict"}

        scores: Dict[str, float] = {}
        for agent_id in conflicting_agents:
            matrix = self._capability_matrices.get(agent_id)
            if matrix:
                scores[agent_id] = self._compute_capability_match(
                    matrix.capabilities, task.required_capabilities
                )
            else:
                scores[agent_id] = random.uniform(0.1, 0.5)

        winner = max(scores, key=lambda k: scores[k])
        task.assigned_agent = winner
        task.status = "assigned"

        self._event_log.append(CoordinationEvent(
            event_type="conflict_resolved",
            source_agent="coordinator",
            target_agents=conflicting_agents,
            message=f"Task conflict resolved for {task_id}: {winner} wins",
            priority=3,
        ))
        return {
            "task_id": task_id,
            "winner": winner,
            "scores": scores,
            "method": "capability_score",
        }

    def optimize_team_composition(
        self,
        mission_type: str,
        available_agents: List[str],
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        template = MISSION_TEMPLATES.get(mission_type)
        if not template:
            template = MISSION_TEMPLATES["assault"]

        priority_roles: List[TeamRole] = template["priority_roles"]
        secondary_roles: List[TeamRole] = template["secondary_roles"]
        ideal_size = template["ideal_size"]

        role_assignments: Dict[str, str] = {}
        assigned_agents: List[str] = []
        remaining_agents = list(available_agents)

        for role in priority_roles:
            if not remaining_agents:
                break
            best_agent = self._find_best_agent_for_role(remaining_agents, role)
            if best_agent:
                role_assignments[best_agent] = role.value
                assigned_agents.append(best_agent)
                remaining_agents.remove(best_agent)

        for role in secondary_roles:
            if len(assigned_agents) >= ideal_size or not remaining_agents:
                break
            best_agent = self._find_best_agent_for_role(remaining_agents, role)
            if best_agent:
                role_assignments[best_agent] = role.value
                assigned_agents.append(best_agent)
                remaining_agents.remove(best_agent)

        formation = template["preferred_formation"]
        positions = FORMATION_PATTERNS.get(formation, FORMATION_PATTERNS["line"])

        return {
            "mission_type": mission_type,
            "ideal_size": ideal_size,
            "team_size": len(assigned_agents),
            "role_assignments": role_assignments,
            "preferred_formation": formation,
            "formation_positions": positions[:len(assigned_agents)],
            "coverage": round(len(assigned_agents) / ideal_size, 2) if ideal_size > 0 else 0,
        }

    def evaluate_team_performance(
        self,
        team_id: str,
        metrics: Dict[str, float],
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        team = self._teams.get(team_id)
        if not team:
            return {"error": "Team not found"}

        results: Dict[str, Any] = {
            "team_id": team_id,
            "team_name": team.name,
            "cohesion": team.cohesion_score,
        }

        task_completion = metrics.get("task_completion", 0.0)
        survival = metrics.get("survival", 1.0)
        efficiency = metrics.get("efficiency", 0.5)
        synergy = metrics.get("synergy", team.cohesion_score)
        adaptability = metrics.get("adaptability", 0.5)

        overall = (
            task_completion * 0.35
            + survival * 0.20
            + efficiency * 0.20
            + synergy * 0.15
            + adaptability * 0.10
        )
        results["overall_score"] = round(overall, 3)
        results["breakdown"] = {
            "task_completion": task_completion,
            "survival": survival,
            "efficiency": efficiency,
            "synergy": synergy,
            "adaptability": adaptability,
        }

        if overall >= 0.7:
            results["rating"] = "excellent"
            team.cohesion_score = min(1.0, team.cohesion_score + 0.05)
        elif overall >= 0.5:
            results["rating"] = "good"
        elif overall >= 0.3:
            results["rating"] = "adequate"
            team.cohesion_score = max(0.1, team.cohesion_score - 0.02)
        else:
            results["rating"] = "poor"
            team.cohesion_score = max(0.1, team.cohesion_score - 0.05)

        for member in team.members:
            member.contribution_score += overall * 0.1
            member.state = AgentState.IDLE
            member.readiness = min(1.0, member.readiness + 0.05)

        return results

    def compute_formation_positions(
        self,
        team_id: str,
        formation_type: str,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        team = self._teams.get(team_id)
        if not team:
            return {"error": "Team not found"}

        positions = FORMATION_PATTERNS.get(formation_type)
        if not positions:
            positions = FORMATION_PATTERNS["line"]

        team.formation_pattern = formation_type
        member_positions: Dict[str, Tuple[float, float]] = {}

        for idx, member in enumerate(team.members):
            if idx < len(positions):
                pos = positions[idx]
                jitter_x = random.uniform(-0.3, 0.3)
                jitter_y = random.uniform(-0.3, 0.3)
                member_positions[member.agent_id] = (
                    round(pos[0] + jitter_x, 2),
                    round(pos[1] + jitter_y, 2),
                )
            else:
                member_positions[member.agent_id] = (
                    round(random.uniform(-5.0, 5.0), 2),
                    round(random.uniform(-5.0, 5.0), 2),
                )

        self._formation_positions[team_id] = [
            member_positions[m.agent_id] for m in team.members
        ]
        team.formation_pattern = formation_type

        return {
            "team_id": team_id,
            "formation_type": formation_type,
            "positions": {
                agent_id: {"x": pos[0], "y": pos[1]}
                for agent_id, pos in member_positions.items()
            },
            "member_count": len(team.members),
        }

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        mode_counts: Dict[str, int] = {}
        role_counts: Dict[str, int] = {}
        for team in self._teams.values():
            mode_counts[team.coordination_mode.value] = (
                mode_counts.get(team.coordination_mode.value, 0) + 1
            )
            for member in team.members:
                role_counts[member.role.value] = (
                    role_counts.get(member.role.value, 0) + 1
                )

        return {
            "total_teams": self._team_count,
            "active_teams": sum(1 for t in self._teams.values() if t.active),
            "total_tasks": self._task_count,
            "completed_tasks": self._completed_task_count,
            "failed_tasks": self._failed_task_count,
            "task_success_rate": (
                round(self._completed_task_count / self._task_count, 3)
                if self._task_count > 0 else 0.0
            ),
            "coordination_rounds": self._coordination_rounds,
            "capability_matrices_computed": len(self._capability_matrices),
            "synergy_networks_computed": len(self._synergy_networks),
            "total_events_logged": len(self._event_log),
            "by_coordination_mode": mode_counts,
            "by_member_role": role_counts,
            "available_formations": list(FORMATION_PATTERNS.keys()),
            "available_mission_types": list(MISSION_TEMPLATES.keys()),
            "available_coordination_modes": [m.value for m in CoordinationMode],
            "available_communication_channels": [c.value for c in CommunicationChannel],
            "available_team_roles": [r.value for r in TeamRole],
        }

    def _compute_capability_match(
        self,
        agent_caps: Dict[str, float],
        required_caps: Dict[str, float],
    ) -> float:
        _time_module.sleep(0.001)
        if not required_caps:
            return 1.0
        total = 0.0
        weight_sum = 0.0
        for key, required in required_caps.items():
            agent_val = agent_caps.get(key, 0.0)
            match = 1.0 - abs(agent_val - required)
            total += match * required
            weight_sum += required
        return total / weight_sum if weight_sum > 0 else 0.0

    def _default_formation_for_mode(self, mode: CoordinationMode) -> str:
        _time_module.sleep(0.001)
        mapping = {
            CoordinationMode.HIERARCHICAL: "wedge",
            CoordinationMode.CONSENSUS: "circle",
            CoordinationMode.AUCTION: "scattered",
            CoordinationMode.VOTING: "circle",
            CoordinationMode.SWARM: "scattered",
            CoordinationMode.COMMAND_CHAIN: "column",
            CoordinationMode.ROLE_BASED: "line",
            CoordinationMode.AUCTION_MARKET: "scattered",
        }
        return mapping.get(mode, "line")

    def _find_best_agent_for_role(
        self,
        agent_ids: List[str],
        role: TeamRole,
    ) -> Optional[str]:
        _time_module.sleep(0.001)
        profile = ROLE_CAPABILITY_PROFILES.get(role, ROLE_CAPABILITY_PROFILES[TeamRole.SUPPORT])
        best_agent: Optional[str] = None
        best_score = -1.0

        for agent_id in agent_ids:
            matrix = self._capability_matrices.get(agent_id)
            if matrix is None:
                self.compute_capability_matrix(agent_id)
                matrix = self._capability_matrices[agent_id]
            if matrix is None:
                continue
            score = self._compute_capability_match(matrix.capabilities, profile)
            if score > best_score:
                best_score = score
                best_agent = agent_id

        return best_agent

    def _synergy_pair_key(self, agent_a: str, agent_b: str) -> str:
        _time_module.sleep(0.001)
        return "_".join(sorted([agent_a, agent_b]))


def get_multi_agent_coordinator() -> AgentMultiAgentCoordinator:
    return AgentMultiAgentCoordinator.get_instance()