"""
SparkLabs Agent Behavior Planner

Autonomous behavior planning system that enables agents to decompose
high-level goals into executable action sequences. Supports priority
scheduling, precondition validation, and dynamic replanning.
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GoalCategory(str, Enum):
    """Category of an agent's goal."""
    SURVIVAL = "survival"
    COMBAT = "combat"
    SOCIAL = "social"
    EXPLORATION = "exploration"
    RESOURCE = "resource"
    CRAFTING = "crafting"
    QUEST = "quest"
    IDLE = "idle"
    CUSTOM = "custom"


class GoalPriority(str, Enum):
    """Priority level for goal scheduling."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class GoalStatus(str, Enum):
    """Execution status of a goal."""
    PENDING = "pending"
    PLANNING = "planning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionType(str, Enum):
    """Type of executable action."""
    MOVE = "move"
    INTERACT = "interact"
    COLLECT = "collect"
    ATTACK = "attack"
    USE_ITEM = "use_item"
    CRAFT = "craft"
    DIALOGUE = "dialogue"
    WAIT = "wait"
    PATROL = "patrol"
    FLEE = "flee"
    CUSTOM = "custom"


class ActionStatus(str, Enum):
    """Status of an individual action."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class PlanResult(str, Enum):
    """Result of a planning attempt."""
    SUCCESS = "success"
    NO_VALID_PLAN = "no_valid_plan"
    PRECONDITIONS_NOT_MET = "preconditions_not_met"
    RESOURCES_INSUFFICIENT = "resources_insufficient"
    CONFLICT_DETECTED = "conflict_detected"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Precondition:
    """A condition that must be satisfied before an action or goal can execute."""
    condition_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    key: str = ""
    operator: str = "eq"
    value: Any = None
    is_met: bool = False

    def evaluate(self, state: Dict[str, Any]) -> bool:
        actual = state.get(self.key)
        operators = {
            "eq": lambda a, v: a == v,
            "neq": lambda a, v: a != v,
            "gt": lambda a, v: a > v,
            "gte": lambda a, v: a >= v,
            "lt": lambda a, v: a < v,
            "lte": lambda a, v: a <= v,
            "in": lambda a, v: a in v,
            "contains": lambda a, v: v in a,
            "exists": lambda a, v: a is not None,
        }
        op = operators.get(self.operator)
        if op is None:
            return False
        self.is_met = op(actual, self.value)
        return self.is_met

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "key": self.key,
            "operator": self.operator,
            "value": self.value,
            "is_met": self.is_met,
        }


@dataclass
class ActionEffect:
    """An effect applied to the world state when an action completes."""
    key: str = ""
    operation: str = "set"
    value: Any = None
    duration: float = 0.0

    def apply(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if self.operation == "set":
            state[self.key] = self.value
        elif self.operation == "add":
            state[self.key] = state.get(self.key, 0) + self.value
        elif self.operation == "multiply":
            state[self.key] = state.get(self.key, 0) * self.value
        elif self.operation == "remove":
            state.pop(self.key, None)
        return state

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "operation": self.operation,
            "value": self.value,
            "duration": self.duration,
        }


@dataclass
class ActionDefinition:
    """A definition of an executable action."""
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    action_type: ActionType = ActionType.MOVE
    name: str = ""
    description: str = ""
    cost: float = 1.0
    duration: float = 0.5
    preconditions: List[Precondition] = field(default_factory=list)
    effects: List[ActionEffect] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: ActionStatus = ActionStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "name": self.name,
            "description": self.description,
            "cost": self.cost,
            "duration": self.duration,
            "preconditions": [p.to_dict() for p in self.preconditions],
            "effects": [e.to_dict() for e in self.effects],
            "parameters": self.parameters,
            "status": self.status.value,
            "retry_count": self.retry_count,
        }


@dataclass
class Goal:
    """A high-level goal that can be decomposed into actions."""
    goal_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    category: GoalCategory = GoalCategory.CUSTOM
    priority: GoalPriority = GoalPriority.NORMAL
    status: GoalStatus = GoalStatus.PENDING
    preconditions: List[Precondition] = field(default_factory=list)
    success_conditions: List[Precondition] = field(default_factory=list)
    action_ids: List[str] = field(default_factory=list)
    current_action_index: int = 0
    parent_goal_id: str = ""
    sub_goal_ids: List[str] = field(default_factory=list)
    assigned_agent_id: str = ""
    created_at: float = field(default_factory=_time_module.time)
    completed_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def progress(self) -> float:
        if not self.action_ids:
            return 0.0
        return self.current_action_index / len(self.action_ids)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "name": self.name,
            "category": self.category.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "preconditions": [p.to_dict() for p in self.preconditions],
            "success_conditions": [c.to_dict() for c in self.success_conditions],
            "action_ids": self.action_ids,
            "current_action_index": self.current_action_index,
            "progress": self.progress(),
            "parent_goal_id": self.parent_goal_id,
            "sub_goal_ids": self.sub_goal_ids,
            "assigned_agent_id": self.assigned_agent_id,
            "metadata": self.metadata,
        }


@dataclass
class BehaviorProfile:
    """Behavior configuration for an agent."""
    agent_id: str = ""
    name: str = "Agent"
    personality_traits: Dict[str, float] = field(default_factory=lambda: {
        "aggression": 0.3,
        "curiosity": 0.5,
        "sociability": 0.5,
        "caution": 0.4,
        "persistence": 0.6,
    })
    active_goals: List[str] = field(default_factory=list)
    completed_goals: List[str] = field(default_factory=list)
    goal_history: List[Dict[str, Any]] = field(default_factory=list)
    blacklisted_actions: Set[str] = field(default_factory=set)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "personality_traits": self.personality_traits,
            "active_goals": self.active_goals,
            "completed_goals": self.completed_goals,
            "goal_history": self.goal_history[-10:],
            "blacklisted_actions": list(self.blacklisted_actions),
        }


# ---------------------------------------------------------------------------
# Agent Behavior Planner
# ---------------------------------------------------------------------------

class AgentBehaviorPlanner:
    """
    Autonomous behavior planning system that decomposes high-level goals
    into executable action sequences with priority scheduling and dynamic
    replanning capabilities.
    """

    _instance: Optional["AgentBehaviorPlanner"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "AgentBehaviorPlanner":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentBehaviorPlanner":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._profiles: Dict[str, BehaviorProfile] = {}
        self._goals: Dict[str, Goal] = {}
        self._actions: Dict[str, ActionDefinition] = {}
        self._action_library: Dict[str, ActionDefinition] = {}
        self._world_state: Dict[str, Any] = {}
        self._planning_cache: Dict[str, List[str]] = {}
        self._total_goals_created: int = 0
        self._total_goals_completed: int = 0
        self._total_actions_executed: int = 0

        # Initialize default action library
        self._init_action_library()

    def _init_action_library(self) -> None:
        """Initialize the default action library with common actions."""
        defaults = [
            ActionDefinition(
                action_type=ActionType.MOVE, name="Move To",
                description="Move to a target location",
                cost=1.0, duration=1.0,
                parameters={"speed": "walk"},
            ),
            ActionDefinition(
                action_type=ActionType.INTERACT, name="Interact",
                description="Interact with a target object",
                cost=1.0, duration=0.5,
            ),
            ActionDefinition(
                action_type=ActionType.COLLECT, name="Collect",
                description="Collect a resource or item",
                cost=1.5, duration=2.0,
            ),
            ActionDefinition(
                action_type=ActionType.ATTACK, name="Attack",
                description="Attack a target entity",
                cost=2.0, duration=1.0,
            ),
            ActionDefinition(
                action_type=ActionType.WAIT, name="Wait",
                description="Wait for a duration",
                cost=0.5, duration=1.0,
            ),
            ActionDefinition(
                action_type=ActionType.PATROL, name="Patrol",
                description="Patrol between waypoints",
                cost=2.0, duration=5.0,
            ),
            ActionDefinition(
                action_type=ActionType.FLEE, name="Flee",
                description="Flee from danger",
                cost=3.0, duration=2.0,
            ),
            ActionDefinition(
                action_type=ActionType.USE_ITEM, name="Use Item",
                description="Use an inventory item",
                cost=1.0, duration=1.0,
            ),
        ]
        for action in defaults:
            self._action_library[action.action_id] = action

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        name: str = "Agent",
        personality_traits: Optional[Dict[str, float]] = None,
    ) -> BehaviorProfile:
        """Register an agent with behavior planning."""
        with self._lock:
            profile = BehaviorProfile(
                agent_id=agent_id,
                name=name,
                personality_traits=personality_traits or {},
            )
            self._profiles[agent_id] = profile
            return profile

    def get_profile(self, agent_id: str) -> Optional[BehaviorProfile]:
        """Get an agent's behavior profile."""
        return self._profiles.get(agent_id)

    # ------------------------------------------------------------------
    # Goal Management
    # ------------------------------------------------------------------

    def create_goal(
        self,
        name: str = "Goal",
        category: GoalCategory = GoalCategory.CUSTOM,
        priority: GoalPriority = GoalPriority.NORMAL,
        assigned_agent_id: str = "",
        parent_goal_id: str = "",
        preconditions: Optional[List[Precondition]] = None,
        success_conditions: Optional[List[Precondition]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Goal:
        """Create a new goal."""
        with self._lock:
            goal = Goal(
                name=name,
                category=category,
                priority=priority,
                assigned_agent_id=assigned_agent_id,
                parent_goal_id=parent_goal_id,
                preconditions=preconditions or [],
                success_conditions=success_conditions or [],
                metadata=metadata or {},
            )
            self._goals[goal.goal_id] = goal
            self._total_goals_created += 1

            # Link to parent
            if parent_goal_id and parent_goal_id in self._goals:
                self._goals[parent_goal_id].sub_goal_ids.append(goal.goal_id)

            # Link to agent
            if assigned_agent_id and assigned_agent_id in self._profiles:
                self._profiles[assigned_agent_id].active_goals.append(goal.goal_id)

            return goal

    def add_action_to_goal(
        self, goal_id: str, action_id: str
    ) -> bool:
        """Add an action to a goal's action sequence."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return False
            if action_id not in self._actions and action_id not in self._action_library:
                return False
            goal.action_ids.append(action_id)
            return True

    def plan_goal(self, goal_id: str) -> PlanResult:
        """
        Plan actions for a goal. Attempts to find a valid sequence
        of actions that satisfy the goal's preconditions and lead to
        the success conditions.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return PlanResult.NO_VALID_PLAN

            # Check preconditions
            for precondition in goal.preconditions:
                if not precondition.evaluate(self._world_state):
                    return PlanResult.PRECONDITIONS_NOT_MET

            goal.status = GoalStatus.PLANNING

            # Clear existing plan
            goal.action_ids.clear()
            goal.current_action_index = 0

            # Simple planning: find actions whose effects match success conditions
            success_keys = {c.key for c in goal.success_conditions}
            available_actions = {
                **self._action_library,
                **self._actions,
            }

            # Filter actions by agent's blacklist
            agent_id = goal.assigned_agent_id
            if agent_id and agent_id in self._profiles:
                blacklist = self._profiles[agent_id].blacklisted_actions
                available_actions = {
                    k: v for k, v in available_actions.items()
                    if k not in blacklist
                }

            for action_id, action in available_actions.items():
                for effect in action.effects:
                    if effect.key in success_keys:
                        # Check action preconditions
                        all_met = all(
                            p.evaluate(self._world_state)
                            for p in action.preconditions
                        )
                        if all_met:
                            goal.action_ids.append(action_id)

            if goal.action_ids:
                goal.status = GoalStatus.ACTIVE
                return PlanResult.SUCCESS

            goal.status = GoalStatus.PENDING
            return PlanResult.NO_VALID_PLAN

    def execute_goal_step(self, goal_id: str) -> Optional[ActionDefinition]:
        """Execute the next action in a goal's sequence."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None or goal.status != GoalStatus.ACTIVE:
                return None

            if goal.current_action_index >= len(goal.action_ids):
                goal.status = GoalStatus.COMPLETED
                goal.completed_at = _time_module.time()
                self._total_goals_completed += 1

                # Update agent profile
                agent_id = goal.assigned_agent_id
                if agent_id and agent_id in self._profiles:
                    profile = self._profiles[agent_id]
                    profile.goal_history.append({
                        "goal_id": goal_id,
                        "name": goal.name,
                        "completed_at": goal.completed_at,
                    })
                    if goal_id in profile.active_goals:
                        profile.active_goals.remove(goal_id)
                    profile.completed_goals.append(goal_id)

                return None

            action_id = goal.action_ids[goal.current_action_index]
            action = self._actions.get(action_id) or self._action_library.get(action_id)
            if action is None:
                goal.current_action_index += 1
                return None

            # Check preconditions
            for precondition in action.preconditions:
                if not precondition.evaluate(self._world_state):
                    action.status = ActionStatus.BLOCKED
                    if action.retry_count < action.max_retries:
                        action.retry_count += 1
                        return None
                    action.status = ActionStatus.FAILED
                    goal.current_action_index += 1
                    return None

            action.status = ActionStatus.EXECUTING
            self._total_actions_executed += 1

            # Apply effects
            for effect in action.effects:
                effect.apply(self._world_state)

            action.status = ActionStatus.COMPLETED
            goal.current_action_index += 1
            return action

    def cancel_goal(self, goal_id: str) -> bool:
        """Cancel a goal."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return False
            goal.status = GoalStatus.CANCELLED
            return True

    def suspend_goal(self, goal_id: str) -> bool:
        """Suspend a goal."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return False
            goal.status = GoalStatus.SUSPENDED
            return True

    def resume_goal(self, goal_id: str) -> bool:
        """Resume a suspended goal."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None or goal.status != GoalStatus.SUSPENDED:
                return False
            goal.status = GoalStatus.ACTIVE
            return True

    # ------------------------------------------------------------------
    # Action Library
    # ------------------------------------------------------------------

    def register_action(self, action: ActionDefinition) -> ActionDefinition:
        """Register a custom action in the action library."""
        with self._lock:
            self._actions[action.action_id] = action
            return action

    def create_action(
        self,
        action_type: ActionType = ActionType.CUSTOM,
        name: str = "Custom Action",
        cost: float = 1.0,
        duration: float = 0.5,
        preconditions: Optional[List[Precondition]] = None,
        effects: Optional[List[ActionEffect]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ActionDefinition:
        """Create a custom action."""
        action = ActionDefinition(
            action_type=action_type,
            name=name,
            cost=cost,
            duration=duration,
            preconditions=preconditions or [],
            effects=effects or [],
            parameters=parameters or {},
        )
        self._actions[action.action_id] = action
        return action

    # ------------------------------------------------------------------
    # World State
    # ------------------------------------------------------------------

    def set_world_state(self, key: str, value: Any) -> None:
        """Set a world state variable."""
        with self._lock:
            self._world_state[key] = value

    def get_world_state(self, key: str, default: Any = None) -> Any:
        """Get a world state variable."""
        return self._world_state.get(key, default)

    def update_world_state(self, updates: Dict[str, Any]) -> None:
        """Batch update world state variables."""
        with self._lock:
            self._world_state.update(updates)

    # ------------------------------------------------------------------
    # Priority Scheduling
    # ------------------------------------------------------------------

    def get_priority_order(self) -> int:
        return {
            GoalPriority.CRITICAL: 0,
            GoalPriority.HIGH: 1,
            GoalPriority.NORMAL: 2,
            GoalPriority.LOW: 3,
            GoalPriority.BACKGROUND: 4,
        }

    def get_next_goal(self, agent_id: str) -> Optional[Goal]:
        """Get the highest priority active goal for an agent."""
        profile = self._profiles.get(agent_id)
        if profile is None:
            return None

        active_goals = []
        for goal_id in profile.active_goals:
            goal = self._goals.get(goal_id)
            if goal and goal.status == GoalStatus.ACTIVE:
                active_goals.append(goal)

        if not active_goals:
            return None

        order = self.get_priority_order()
        active_goals.sort(key=lambda g: order.get(g.priority, 99))
        return active_goals[0] if active_goals else None

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        return self._goals.get(goal_id)

    def get_action(self, action_id: str) -> Optional[ActionDefinition]:
        """Get an action by ID."""
        return self._actions.get(action_id) or self._action_library.get(action_id)

    def get_all_goals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all goals."""
        goals = list(self._goals.values())[:limit]
        return [g.to_dict() for g in goals]

    def get_all_profiles(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all behavior profiles."""
        profiles = list(self._profiles.values())[:limit]
        return [p.to_dict() for p in profiles]

    def get_all_actions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all registered actions."""
        all_actions = {**self._action_library, **self._actions}
        actions = list(all_actions.values())[:limit]
        return [a.to_dict() for a in actions]

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        status_counts = {}
        for goal in self._goals.values():
            s = goal.status.value
            status_counts[s] = status_counts.get(s, 0) + 1

        return {
            "total_profiles": len(self._profiles),
            "total_goals": len(self._goals),
            "total_actions": len(self._actions) + len(self._action_library),
            "total_created": self._total_goals_created,
            "total_completed": self._total_goals_completed,
            "total_executed": self._total_actions_executed,
            "goal_status_distribution": status_counts,
            "world_state_keys": list(self._world_state.keys()),
            "active_agents": len([
                p for p in self._profiles.values() if p.active_goals
            ]),
        }


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_behavior_planner() -> AgentBehaviorPlanner:
    """Get or create the singleton AgentBehaviorPlanner instance."""
    return AgentBehaviorPlanner.get_instance()