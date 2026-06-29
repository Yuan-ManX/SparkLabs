"""
SparkLabs Agent - Autonomous Mission Planning and Execution System

Autonomous mission planning, decomposition, and execution framework for the
SparkLabs AI-native game engine. Allows higher-level orchestrators to
declare high-level goals, decompose them into structured objectives and
concrete plans, and execute those missions while monitoring progress.

Architecture:
  AutonomousMissionSystem (Singleton)
    |-- MissionPriority (urgency/importance tier)
    |-- MissionStatus (lifecycle state of a mission)
    |-- MissionObjective (decomposed sub-goal with success criteria)
    |-- MissionPlan (structured plan of objectives and schedule)
    |-- Mission (top-level goal container with an optional plan)
    |-- MissionSystemSnapshot (point-in-time state capture for recovery)

The system is intentionally framework-agnostic: it does not assume a
specific execution backend. Mission execution is simulated so the
lifecycle can progress without external dependencies, while still
honoring objective dependencies and priority ordering.
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


_time = _time_module


# =============================================================================
# Enums
# =============================================================================


class MissionPriority(Enum):
    """Priority tiers controlling scheduling order and resource allocation.

    Higher-priority missions preempt lower-priority ones when system
    resources are constrained.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"


class MissionStatus(Enum):
    """Lifecycle states for a mission.

    Tracks the progression of a mission from initial declaration through
    planning, execution, monitoring, and terminal states.
    """

    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


# Priority ordering weights; higher value means higher priority.
_PRIORITY_WEIGHTS: Dict[MissionPriority, int] = {
    MissionPriority.LOW: 1,
    MissionPriority.MEDIUM: 25,
    MissionPriority.HIGH: 50,
    MissionPriority.CRITICAL: 75,
    MissionPriority.URGENT: 100,
}

# Active (non-terminal) mission statuses.
_ACTIVE_STATUSES = {
    MissionStatus.PENDING,
    MissionStatus.PLANNING,
    MissionStatus.EXECUTING,
    MissionStatus.MONITORING,
}


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class MissionObjective:
    """A decomposed sub-goal contributing to a mission.

    Attributes:
        objective_id: Auto-generated unique identifier for the objective.
        description: Detailed narrative description of the goal.
        success_criteria: Machine-readable criteria used to verify completion.
        priority: Importance tier of this objective.
        status: Current lifecycle state of the objective.
        dependencies: Objective IDs that must complete before this one.
    """

    objective_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""
    success_criteria: Dict[str, Any] = field(default_factory=dict)
    priority: MissionPriority = MissionPriority.MEDIUM
    status: str = "pending"
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "description": self.description,
            "success_criteria": dict(self.success_criteria),
            "priority": self.priority.value,
            "status": self.status,
            "dependencies": list(self.dependencies),
        }


@dataclass
class MissionPlan:
    """A structured plan for a mission composed of objectives.

    Attributes:
        plan_id: Auto-generated unique identifier for the plan.
        mission_id: ID of the mission this plan belongs to.
        objectives: Ordered list of objectives to achieve.
        schedule: Mapping of objective_id to scheduled execution time.
        estimated_duration: Estimated total execution time in seconds.
        risk_assessment: Qualitative risk profile for the plan.
    """

    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    mission_id: str = ""
    objectives: List[MissionObjective] = field(default_factory=list)
    schedule: Dict[str, float] = field(default_factory=dict)
    estimated_duration: float = 0.0
    risk_assessment: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "mission_id": self.mission_id,
            "objectives": [o.to_dict() for o in self.objectives],
            "schedule": dict(self.schedule),
            "estimated_duration": self.estimated_duration,
            "risk_assessment": dict(self.risk_assessment),
        }


@dataclass
class Mission:
    """A top-level autonomous goal with an optional structured plan.

    Attributes:
        mission_id: Auto-generated unique identifier for the mission.
        name: Human-readable short label.
        description: Detailed narrative description of the goal.
        priority: Importance tier controlling scheduling order.
        status: Current lifecycle state of the mission.
        plan: The decomposed plan for this mission, if any.
        progress: Normalized completion ratio in [0.0, 1.0].
        created_at: POSIX timestamp of mission creation.
    """

    mission_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    priority: MissionPriority = MissionPriority.MEDIUM
    status: MissionStatus = MissionStatus.PENDING
    plan: Optional[MissionPlan] = None
    progress: float = 0.0
    created_at: float = field(default_factory=_time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "plan": self.plan.to_dict() if self.plan else None,
            "progress": self.progress,
            "created_at": self.created_at,
        }


@dataclass
class MissionSystemSnapshot:
    """Point-in-time capture of the autonomous mission system state.

    Attributes:
        snapshot_id: Auto-generated unique identifier for the snapshot.
        captured_at: POSIX timestamp of capture.
        mission_count: Number of missions captured.
        missions: Serialized list of all known missions.
        system_status: Aggregate status dictionary at capture time.
    """

    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    captured_at: float = field(default_factory=_time.time)
    mission_count: int = 0
    missions: List[Dict[str, Any]] = field(default_factory=list)
    system_status: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at,
            "mission_count": self.mission_count,
            "missions": self.missions,
            "system_status": self.system_status,
        }


# =============================================================================
# AutonomousMissionSystem (Singleton)
# =============================================================================


class AutonomousMissionSystem:
    """Autonomous mission planning and execution system (singleton).

    Orchestrates the full mission lifecycle: declaration, goal
    decomposition into objectives and a plan, simulated execution, and
    progress monitoring. The system is thread-safe.

    Usage:
        system = get_autonomous_mission_system()
        mission = system.create_mission(
            name="Establish Forward Base",
            description="Secure and equip a forward operating base.",
            priority=MissionPriority.HIGH,
        )
        plan = system.decompose_mission(mission.mission_id)
        system.execute_mission(mission.mission_id)
        report = system.monitor_mission(mission.mission_id)
    """

    _instance: Optional["AutonomousMissionSystem"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_MISSIONS: int = 1000

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._missions: Dict[str, Mission] = {}
        self._stats: Dict[str, Any] = {
            "total_created": 0,
            "total_decomposed": 0,
            "total_executed": 0,
            "total_aborted": 0,
            "total_completed": 0,
            "total_failed": 0,
        }
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "AutonomousMissionSystem":
        """Return the singleton AutonomousMissionSystem instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Mission Creation & Decomposition
    # ------------------------------------------------------------------

    def create_mission(
        self,
        name: str,
        description: str,
        priority: MissionPriority = MissionPriority.MEDIUM,
    ) -> Mission:
        """Create a new mission in the PENDING state.

        Args:
            name: Human-readable short label for the mission.
            description: Detailed narrative description of the goal.
            priority: Priority tier for scheduling. Defaults to MEDIUM.

        Returns:
            The newly created Mission instance in PENDING status.
        """
        with self._instance_lock:
            self._enforce_max_missions()
            mission = Mission(
                name=name,
                description=description,
                priority=priority,
                status=MissionStatus.PENDING,
            )
            self._missions[mission.mission_id] = mission
            self._stats["total_created"] += 1
            return mission

    def decompose_mission(self, mission_id: str) -> Optional[MissionPlan]:
        """Decompose a mission goal into a structured plan.

        Simulates goal decomposition by deriving a small set of canonical
        objective archetypes (analyze, prepare, execute, verify, finalize)
        from the mission description. Objectives carry dependencies that
        enforce a sequential baseline, and the plan is attached to the
        mission. The mission status advances to PLANNING.

        Args:
            mission_id: ID of the mission to decompose.

        Returns:
            The generated MissionPlan, or None if the mission is not
            found or is already in a terminal state.
        """
        with self._instance_lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                return None
            if mission.status in (
                MissionStatus.COMPLETED,
                MissionStatus.FAILED,
                MissionStatus.ABORTED,
            ):
                return None

            mission.status = MissionStatus.PLANNING
            keyword = (mission.description or mission.name or "mission").strip().lower() or "mission"
            objective_specs = self._derive_objective_specs(keyword)
            objectives: List[MissionObjective] = []
            for spec in objective_specs:
                objective = MissionObjective(
                    description=spec["description"],
                    success_criteria=spec["success_criteria"],
                    priority=spec["priority"],
                    status="pending",
                    dependencies=list(spec["dependencies"]),
                )
                objectives.append(objective)

            schedule = {
                o.objective_id: float(index) * 10.0
                for index, o in enumerate(objectives)
            }
            plan = MissionPlan(
                mission_id=mission.mission_id,
                objectives=objectives,
                schedule=schedule,
                estimated_duration=float(len(objectives)) * 10.0,
                risk_assessment={
                    "level": "moderate",
                    "factors": ["dependency_chain", "resource_contention"],
                },
            )
            mission.plan = plan
            self._stats["total_decomposed"] += 1
            return plan

    # ------------------------------------------------------------------
    # Execution & Monitoring
    # ------------------------------------------------------------------

    def execute_mission(self, mission_id: str) -> bool:
        """Execute a mission by simulating completion of its objectives.

        Iterates over the mission plan's objectives in dependency order,
        marking each as completed. Progress is updated after each
        objective. The mission transitions through EXECUTING and
        MONITORING before reaching COMPLETED (or FAILED if no plan).

        Args:
            mission_id: ID of the mission to execute.

        Returns:
            True if the mission reached COMPLETED, False if the mission
            was not found, had no plan, or entered a failed state.
        """
        with self._instance_lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                return False
            if mission.status == MissionStatus.COMPLETED:
                return True
            if mission.status in (MissionStatus.FAILED, MissionStatus.ABORTED):
                return False
            if mission.plan is None:
                mission.status = MissionStatus.FAILED
                self._stats["total_failed"] += 1
                return False

            mission.status = MissionStatus.EXECUTING
            objectives = mission.plan.objectives
            total = max(1, len(objectives))
            completed = 0
            for objective in objectives:
                # Honor dependency ordering: skip if a dependency failed.
                deps_ok = all(
                    any(
                        o.objective_id == dep_id and o.status == "completed"
                        for o in objectives
                    )
                    for dep_id in objective.dependencies
                )
                if not deps_ok:
                    objective.status = "blocked"
                    continue
                objective.status = "completed"
                completed += 1
                mission.progress = completed / total

            mission.status = MissionStatus.MONITORING
            if completed == 0:
                mission.status = MissionStatus.FAILED
                self._stats["total_failed"] += 1
                return False

            mission.progress = 1.0 if completed == total else mission.progress
            mission.status = MissionStatus.COMPLETED
            self._stats["total_executed"] += 1
            self._stats["total_completed"] += 1
            return True

    def monitor_mission(self, mission_id: str) -> Dict[str, Any]:
        """Return a monitoring report for a mission.

        Summarizes the mission's current status, progress, and per-objective
        state. Useful for dashboards and orchestrators that need to observe
        ongoing missions without mutating them.

        Args:
            mission_id: ID of the mission to monitor.

        Returns:
            A report dictionary, or an error dict if not found.
        """
        with self._instance_lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                return {
                    "status": "error",
                    "error": "mission_not_found",
                    "mission_id": mission_id,
                }
            plan = mission.plan
            objectives = []
            if plan is not None:
                for o in plan.objectives:
                    objectives.append({
                        "objective_id": o.objective_id,
                        "description": o.description,
                        "status": o.status,
                        "priority": o.priority.value,
                    })
            return {
                "mission_id": mission.mission_id,
                "name": mission.name,
                "status": mission.status.value,
                "priority": mission.priority.value,
                "progress": mission.progress,
                "objective_count": len(objectives),
                "objectives": objectives,
                "has_plan": plan is not None,
            }

    def abort_mission(self, mission_id: str) -> bool:
        """Abort a mission, marking remaining work as abandoned.

        Abortion is permitted from any non-terminal state. Pending
        objectives are marked aborted. The mission is moved to ABORTED.

        Args:
            mission_id: ID of the mission to abort.

        Returns:
            True if the mission was aborted, False if it was not found
            or already in a terminal state.
        """
        with self._instance_lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                return False
            if mission.status in (
                MissionStatus.COMPLETED,
                MissionStatus.FAILED,
                MissionStatus.ABORTED,
            ):
                return False
            if mission.plan is not None:
                for objective in mission.plan.objectives:
                    if objective.status not in ("completed", "failed"):
                        objective.status = "aborted"
            mission.status = MissionStatus.ABORTED
            self._stats["total_aborted"] += 1
            return True

    # ------------------------------------------------------------------
    # Retrieval & Status
    # ------------------------------------------------------------------

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        """Retrieve a mission by ID."""
        with self._instance_lock:
            return self._missions.get(mission_id)

    def get_active_missions(self) -> List[Mission]:
        """Return all missions currently in an active (non-terminal) state.

        Ordered by priority (highest first) and then by creation time.
        """
        with self._instance_lock:
            missions = [m for m in self._missions.values() if m.status in _ACTIVE_STATUSES]
            missions.sort(
                key=lambda m: (
                    -_PRIORITY_WEIGHTS.get(m.priority, 0),
                    m.created_at,
                )
            )
            return missions

    def get_status(self) -> Dict[str, Any]:
        """Return aggregate status of the mission system."""
        with self._instance_lock:
            status_counts: Dict[str, int] = {}
            priority_counts: Dict[str, int] = {}
            for mission in self._missions.values():
                status_counts[mission.status.value] = status_counts.get(mission.status.value, 0) + 1
                priority_counts[mission.priority.value] = priority_counts.get(mission.priority.value, 0) + 1
            return {
                "mission_count": len(self._missions),
                "status_counts": status_counts,
                "priority_counts": priority_counts,
                "stats": dict(self._stats),
            }

    def get_snapshot(self) -> MissionSystemSnapshot:
        """Capture a point-in-time snapshot of the system state."""
        with self._instance_lock:
            status = self.get_status()
            return MissionSystemSnapshot(
                captured_at=_time.time(),
                mission_count=len(self._missions),
                missions=[m.to_dict() for m in self._missions.values()],
                system_status=status,
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all missions and reset statistics."""
        with self._instance_lock:
            self._missions.clear()
            self._stats = {
                "total_created": 0,
                "total_decomposed": 0,
                "total_executed": 0,
                "total_aborted": 0,
                "total_completed": 0,
                "total_failed": 0,
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enforce_max_missions(self) -> None:
        """Evict the oldest completed missions when the cap is exceeded."""
        if len(self._missions) <= self._MAX_MISSIONS:
            return
        terminal = [
            m for m in self._missions.values()
            if m.status in (MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.ABORTED)
        ]
        terminal.sort(key=lambda m: m.created_at)
        excess = len(self._missions) - self._MAX_MISSIONS
        for mission in terminal[:excess]:
            self._missions.pop(mission.mission_id, None)

    def _derive_objective_specs(self, keyword: str) -> List[Dict[str, Any]]:
        """Derive canonical objective archetypes for a mission keyword."""
        return [
            {
                "description": f"Analyze requirements for {keyword}",
                "success_criteria": {"analysis_complete": True},
                "priority": MissionPriority.HIGH,
                "dependencies": [],
            },
            {
                "description": f"Prepare resources for {keyword}",
                "success_criteria": {"resources_ready": True},
                "priority": MissionPriority.MEDIUM,
                "dependencies": [],
            },
            {
                "description": f"Execute {keyword}",
                "success_criteria": {"execution_complete": True},
                "priority": MissionPriority.CRITICAL,
                "dependencies": [],
            },
            {
                "description": f"Verify outcomes of {keyword}",
                "success_criteria": {"verification_passed": True},
                "priority": MissionPriority.MEDIUM,
                "dependencies": [],
            },
            {
                "description": f"Finalize {keyword}",
                "success_criteria": {"finalized": True},
                "priority": MissionPriority.LOW,
                "dependencies": [],
            },
        ]


# =============================================================================
# Module-level factory
# =============================================================================


def get_autonomous_mission_system() -> AutonomousMissionSystem:
    """Return the singleton AutonomousMissionSystem instance."""
    return AutonomousMissionSystem.get_instance()
