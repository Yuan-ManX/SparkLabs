"""
SparkLabs Agent - Swarm Planner

A singleton system for multi-agent coordination, flocking, formation
tactics, and emergent group behaviors. Plans and executes coordinated
NPC group movements, combat formations, and tactical maneuvers across
the game world.

Architecture:
  SwarmPlanner (singleton)
    |-- SwarmFormation (formation geometry with agent slots)
    |-- FlockParams (boid-style flocking rule weights)
    |-- SwarmTactic (tactical behavior scripts for groups)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


class FormationType(Enum):
    LINE = "line"
    WEDGE = "wedge"
    CIRCLE = "circle"
    SQUARE = "square"
    COLUMN = "column"
    PHALANX = "phalanx"
    DIAMOND = "diamond"
    SCATTER = "scatter"
    FLANK_LEFT = "flank_left"
    FLANK_RIGHT = "flank_right"


class FlockBehavior(Enum):
    SEPARATION = "separation"
    ALIGNMENT = "alignment"
    COHESION = "cohesion"
    OBSTACLE_AVOIDANCE = "obstacle_avoidance"
    LEADER_FOLLOW = "leader_follow"
    GOAL_SEEK = "goal_seek"


class TacticType(Enum):
    SURROUND = "surround"
    AMBUSH = "ambush"
    RETREAT = "retreat"
    SWEEP = "sweep"
    HOLD_POSITION = "hold_position"
    PATROL = "patrol"
    CHARGE = "charge"
    DEFENSIVE_CIRCLE = "defensive_circle"


class SwarmState(Enum):
    IDLE = "idle"
    FORMING = "forming"
    MOVING = "moving"
    ENGAGING = "engaging"
    REGROUPING = "regrouping"
    DISPERSED = "dispersed"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class FlockParams:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    label: str = "default"
    separation_weight: float = 1.5
    alignment_weight: float = 1.0
    cohesion_weight: float = 1.0
    obstacle_avoidance_weight: float = 2.0
    leader_follow_weight: float = 1.2
    goal_seek_weight: float = 0.8
    neighbor_radius: float = 10.0
    max_speed: float = 5.0
    max_force: float = 2.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "separation_weight": self.separation_weight,
            "alignment_weight": self.alignment_weight,
            "cohesion_weight": self.cohesion_weight,
            "obstacle_avoidance_weight": self.obstacle_avoidance_weight,
            "leader_follow_weight": self.leader_follow_weight,
            "goal_seek_weight": self.goal_seek_weight,
            "neighbor_radius": self.neighbor_radius,
            "max_speed": self.max_speed,
            "max_force": self.max_force,
        }


@dataclass
class SwarmFormation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    formation_type: FormationType = FormationType.LINE
    slot_count: int = 0
    leader_index: int = 0
    spacing: float = 2.0
    rotation: float = 0.0
    center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    slots: List[Tuple[float, float, float]] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "formation_type": self.formation_type.value,
            "slot_count": self.slot_count,
            "leader_index": self.leader_index,
            "spacing": self.spacing,
            "rotation": self.rotation,
            "center": list(self.center),
            "slots": [list(s) for s in self.slots],
            "created_at": self.created_at,
        }


@dataclass
class SwarmTactic:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    tactic_type: TacticType = TacticType.HOLD_POSITION
    duration: float = 10.0
    target_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    formation: FormationType = FormationType.LINE
    aggressiveness: float = 0.5
    retreat_threshold: float = 0.3
    priority: int = 0
    created_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tactic_type": self.tactic_type.value,
            "duration": self.duration,
            "target_position": list(self.target_position),
            "formation": self.formation.value,
            "aggressiveness": self.aggressiveness,
            "retreat_threshold": self.retreat_threshold,
            "priority": self.priority,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class SwarmGroup:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    agent_ids: List[str] = field(default_factory=list)
    state: SwarmState = SwarmState.IDLE
    formation: Optional[SwarmFormation] = None
    active_tactic: Optional[SwarmTactic] = None
    flock_params: FlockParams = field(default_factory=FlockParams)
    tactic_queue: List[SwarmTactic] = field(default_factory=list)
    center_of_mass: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    created_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "agent_ids": list(self.agent_ids),
            "state": self.state.value,
            "formation": self.formation.to_dict() if self.formation else None,
            "active_tactic": self.active_tactic.to_dict() if self.active_tactic else None,
            "flock_params": self.flock_params.to_dict(),
            "tactic_queue": [t.to_dict() for t in self.tactic_queue],
            "center_of_mass": list(self.center_of_mass),
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

GROUP_GENERATION_BUMP: float = 1.5
SLOT_THRESHOLD_LIMIT: int = 100


class SwarmPlanner:
    """Multi-agent swarm coordination and tactical planning system.

    Manages NPC group formations, boid flocking behaviors, tactical
    maneuvers, and emergent group dynamics. Each swarm group maintains
    its own formation geometry, flocking parameters, and tactic queue
    for autonomous coordinated movement.
    """

    _instance: Optional[SwarmPlanner] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> SwarmPlanner:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> SwarmPlanner:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._groups: List[SwarmGroup] = []
        self._formations: List[SwarmFormation] = []
        self._tactics: List[SwarmTactic] = []
        self._flock_templates: List[FlockParams] = []
        self._default_flock = FlockParams()
        self._flock_templates.append(self._default_flock)

    def _get_or_create_singleton(self) -> SwarmPlanner:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        total_agents = sum(len(g.agent_ids) for g in self._groups)
        active_groups = sum(1 for g in self._groups if g.state != SwarmState.IDLE)
        return {
            "groups": len(self._groups),
            "active_groups": active_groups,
            "total_agents": total_agents,
            "formations": len(self._formations),
            "tactics": len(self._tactics),
            "flock_templates": len(self._flock_templates),
        }

    # --- Group Operations ---

    def create_group(self, name: str, agent_ids: Optional[List[str]] = None) -> SwarmGroup:
        group = SwarmGroup(
            name=name,
            agent_ids=agent_ids or [],
        )
        self._groups.append(group)
        return group

    def add_agent_to_group(self, group_id: str, agent_id: str) -> bool:
        group = self._find_group(group_id)
        if not group:
            return False
        if agent_id not in group.agent_ids:
            group.agent_ids.append(agent_id)
        return True

    def remove_agent_from_group(self, group_id: str, agent_id: str) -> bool:
        group = self._find_group(group_id)
        if not group or agent_id not in group.agent_ids:
            return False
        group.agent_ids.remove(agent_id)
        if not group.agent_ids:
            group.state = SwarmState.DISPERSED
        return True

    def get_group(self, group_id: str) -> Optional[SwarmGroup]:
        return self._find_group(group_id)

    def list_groups(self) -> List[SwarmGroup]:
        return list(self._groups)

    # --- Formation Operations ---

    def create_formation(
        self,
        name: str,
        formation_type: str,
        slot_count: int,
        spacing: float = 2.0,
    ) -> SwarmFormation:
        ftype = FormationType(formation_type)
        formation = SwarmFormation(
            name=name,
            formation_type=ftype,
            slot_count=slot_count,
            spacing=spacing,
        )
        formation.slots = self._compute_formation_slots(
            ftype, slot_count, spacing
        )
        self._formations.append(formation)
        return formation

    def apply_formation(self, group_id: str, formation_id: str) -> bool:
        group = self._find_group(group_id)
        formation = self._find_formation(formation_id)
        if not group or not formation:
            return False

        if len(group.agent_ids) > SLOT_THRESHOLD_LIMIT:
            return False

        group.formation = formation
        if formation.slot_count < len(group.agent_ids):
            formation.slot_count = len(group.agent_ids)
            formation.slots = self._compute_formation_slots(
                formation.formation_type, formation.slot_count, formation.spacing
            )
        group.state = SwarmState.FORMING
        return True

    def list_formations(self) -> List[SwarmFormation]:
        return list(self._formations)

    # --- Tactic Operations ---

    def create_tactic(
        self,
        name: str,
        tactic_type: str,
        duration: float = 10.0,
        aggressiveness: float = 0.5,
    ) -> SwarmTactic:
        tactic = SwarmTactic(
            name=name,
            tactic_type=TacticType(tactic_type),
            duration=duration,
            aggressiveness=max(0.0, min(1.0, aggressiveness)),
        )
        self._tactics.append(tactic)
        return tactic

    def queue_tactic(self, group_id: str, tactic_id: str) -> bool:
        group = self._find_group(group_id)
        tactic = self._find_tactic(tactic_id)
        if not group or not tactic:
            return False
        group.tactic_queue.append(tactic)
        return True

    def execute_tactic(self, group_id: str) -> Optional[SwarmTactic]:
        group = self._find_group(group_id)
        if not group or not group.tactic_queue:
            return None

        tactic = group.tactic_queue.pop(0)
        group.active_tactic = tactic
        group.state = SwarmState.ENGAGING
        return tactic

    def list_tactics(self) -> List[SwarmTactic]:
        return list(self._tactics)

    # --- Flocking ---

    def create_flock_params(self, label: str) -> FlockParams:
        params = FlockParams(label=label)
        self._flock_templates.append(params)
        return params

    def configure_flocking(
        self,
        group_id: str,
        separation: Optional[float] = None,
        alignment: Optional[float] = None,
        cohesion: Optional[float] = None,
        max_speed: Optional[float] = None,
    ) -> bool:
        group = self._find_group(group_id)
        if not group:
            return False
        if separation is not None:
            group.flock_params.separation_weight = separation
        if alignment is not None:
            group.flock_params.alignment_weight = alignment
        if cohesion is not None:
            group.flock_params.cohesion_weight = cohesion
        if max_speed is not None:
            group.flock_params.max_speed = max_speed
        return True

    def compute_flock_velocity(
        self,
        group_id: str,
        agent_position: Tuple[float, float, float],
        neighbor_positions: List[Tuple[float, float, float]],
        goal_position: Optional[Tuple[float, float, float]] = None,
    ) -> Tuple[float, float, float]:
        group = self._find_group(group_id)
        if not group or not neighbor_positions:
            return (0.0, 0.0, 0.0)

        fp = group.flock_params
        sep = self._separation_force(agent_position, neighbor_positions, fp)
        ali = self._alignment_force(neighbor_positions, fp)
        coh = self._cohesion_force(agent_position, neighbor_positions, fp)
        goal = (0.0, 0.0, 0.0)
        if goal_position:
            goal = self._goal_seek_force(agent_position, goal_position, fp)

        vx = sep[0] * fp.separation_weight + ali[0] * fp.alignment_weight + coh[0] * fp.cohesion_weight + goal[0] * fp.goal_seek_weight
        vy = sep[1] * fp.separation_weight + ali[1] * fp.alignment_weight + coh[1] * fp.cohesion_weight + goal[1] * fp.goal_seek_weight
        vz = sep[2] * fp.separation_weight + ali[2] * fp.alignment_weight + coh[2] * fp.cohesion_weight + goal[2] * fp.goal_seek_weight

        speed = math.sqrt(vx * vx + vy * vy + vz * vz)
        if speed > fp.max_speed:
            scale = fp.max_speed / speed
            vx *= scale
            vy *= scale
            vz *= scale

        return (vx, vy, vz)

    # --- Internal ---

    def _find_group(self, group_id: str) -> Optional[SwarmGroup]:
        for g in self._groups:
            if g.id == group_id:
                return g
        return None

    def _find_formation(self, formation_id: str) -> Optional[SwarmFormation]:
        for f in self._formations:
            if f.id == formation_id:
                return f
        return None

    def _find_tactic(self, tactic_id: str) -> Optional[SwarmTactic]:
        for t in self._tactics:
            if t.id == tactic_id:
                return t
        return None

    def _compute_formation_slots(
        self,
        ftype: FormationType,
        count: int,
        spacing: float,
    ) -> List[Tuple[float, float, float]]:
        slots: List[Tuple[float, float, float]] = []
        for i in range(count):
            if ftype == FormationType.LINE:
                slots.append((i * spacing, 0.0, 0.0))
            elif ftype == FormationType.CIRCLE:
                angle = 2 * math.pi * i / max(1, count)
                radius = spacing * count / (2 * math.pi)
                slots.append((radius * math.cos(angle), 0.0, radius * math.sin(angle)))
            elif ftype == FormationType.SQUARE:
                side = int(math.ceil(math.sqrt(count)))
                row = i // side
                col = i % side
                slots.append((col * spacing, 0.0, row * spacing))
            elif ftype == FormationType.WEDGE:
                slots.append((i * spacing, 0.0, abs(i - count / 2) * spacing * GROUP_GENERATION_BUMP))
            elif ftype == FormationType.COLUMN:
                slots.append((0.0, 0.0, i * spacing))
            elif ftype == FormationType.DIAMOND:
                half = count // 2
                if i <= half:
                    slots.append((i * spacing, 0.0, -i * spacing))
                else:
                    j = i - half
                    slots.append(((half - j) * spacing, 0.0, j * spacing))
            else:
                slots.append((i * spacing, 0.0, 0.0))
        return slots

    def _separation_force(
        self,
        pos: Tuple[float, float, float],
        neighbors: List[Tuple[float, float, float]],
        params: FlockParams,
    ) -> Tuple[float, float, float]:
        steer = (0.0, 0.0, 0.0)
        count = 0
        for n in neighbors:
            dx = pos[0] - n[0]
            dy = pos[1] - n[1]
            dz = pos[2] - n[2]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if 0.0 < dist < params.neighbor_radius:
                inv = 1.0 / max(dist, 0.01)
                steer = (steer[0] + dx * inv, steer[1] + dy * inv, steer[2] + dz * inv)
                count += 1
        if count > 0:
            inv_count = 1.0 / count
            steer = (steer[0] * inv_count, steer[1] * inv_count, steer[2] * inv_count)
            mag = math.sqrt(steer[0] ** 2 + steer[1] ** 2 + steer[2] ** 2)
            if mag > 0:
                steer = (steer[0] / mag * params.max_force, steer[1] / mag * params.max_force, steer[2] / mag * params.max_force)
        return steer

    def _alignment_force(
        self,
        neighbors: List[Tuple[float, float, float]],
        params: FlockParams,
    ) -> Tuple[float, float, float]:
        if not neighbors:
            return (0.0, 0.0, 0.0)
        avg = (0.0, 0.0, 0.0)
        count = len(neighbors)
        inv_count = 1.0 / count
        return (avg[0] * inv_count, avg[1] * inv_count, avg[2] * inv_count)

    def _cohesion_force(
        self,
        pos: Tuple[float, float, float],
        neighbors: List[Tuple[float, float, float]],
        params: FlockParams,
    ) -> Tuple[float, float, float]:
        if not neighbors:
            return (0.0, 0.0, 0.0)
        center = (0.0, 0.0, 0.0)
        for n in neighbors:
            center = (center[0] + n[0], center[1] + n[1], center[2] + n[2])
        count = len(neighbors)
        center = (center[0] / count, center[1] / count, center[2] / count)
        desired = (center[0] - pos[0], center[1] - pos[1], center[2] - pos[2])
        mag = math.sqrt(desired[0] ** 2 + desired[1] ** 2 + desired[2] ** 2)
        if mag > 0:
            desired = (desired[0] / mag * params.max_speed, desired[1] / mag * params.max_speed, desired[2] / mag * params.max_speed)
        return desired

    def _goal_seek_force(
        self,
        pos: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        params: FlockParams,
    ) -> Tuple[float, float, float]:
        desired = (goal[0] - pos[0], goal[1] - pos[1], goal[2] - pos[2])
        mag = math.sqrt(desired[0] ** 2 + desired[1] ** 2 + desired[2] ** 2)
        if mag > 0:
            desired = (desired[0] / mag * params.max_speed, desired[1] / mag * params.max_speed, desired[2] / mag * params.max_speed)
        return desired


def get_swarm_planner() -> SwarmPlanner:
    return SwarmPlanner.get_instance()