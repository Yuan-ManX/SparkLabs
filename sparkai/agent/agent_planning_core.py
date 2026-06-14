"""
Agent Planning Core - Goal-oriented action planning system for AI agents.
Implements hierarchical task networks, STRIPS-style planning, and
real-time plan adaptation for intelligent game agent behavior.
"""

import threading
import uuid
import heapq
import time as _time_module
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Callable


class PlanStatus(Enum):
    """Status of a planning process."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REPLANNING = "replanning"


class ActionType(Enum):
    """Types of actions in the planning domain."""
    PRIMITIVE = "primitive"
    COMPOSITE = "composite"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    PARALLEL = "parallel"


@dataclass
class WorldState:
    """Representation of the world state for planning."""
    state_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    facts: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "facts": self.facts,
            "timestamp": self.timestamp,
        }

    def satisfies(self, conditions: Dict[str, Any]) -> bool:
        """Check if this state satisfies given conditions."""
        for key, value in conditions.items():
            if key not in self.facts or self.facts[key] != value:
                return False
        return True


@dataclass
class PlanAction:
    """A single action in a plan."""
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    action_type: ActionType = ActionType.PRIMITIVE
    preconditions: Dict[str, Any] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)
    cost: float = 1.0
    duration: float = 0.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    children: List['PlanAction'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "action_type": self.action_type.value,
            "preconditions": self.preconditions,
            "effects": self.effects,
            "cost": self.cost,
            "duration": self.duration,
            "parameters": self.parameters,
        }


@dataclass
class Plan:
    """A complete plan consisting of ordered actions."""
    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    goal: Dict[str, Any] = field(default_factory=dict)
    actions: List[PlanAction] = field(default_factory=list)
    current_index: int = 0
    status: PlanStatus = PlanStatus.IDLE
    total_cost: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "agent_id": self.agent_id,
            "goal": self.goal,
            "actions": [a.to_dict() for a in self.actions],
            "current_index": self.current_index,
            "status": self.status.value,
            "total_cost": self.total_cost,
            "actions_count": len(self.actions),
        }


@dataclass
class Goal:
    """A goal for the planning system."""
    goal_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    target_state: Dict[str, Any] = field(default_factory=dict)
    priority: float = 1.0
    deadline: Optional[float] = None
    parent_goal: Optional[str] = None
    sub_goals: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "name": self.name,
            "target_state": self.target_state,
            "priority": self.priority,
            "deadline": self.deadline,
            "parent_goal": self.parent_goal,
            "sub_goals": self.sub_goals,
        }


class AgentPlanningCore:
    """
    Goal-oriented action planning system for AI agents.
    Implements STRIPS planning, hierarchical task decomposition,
    and real-time plan adaptation.
    """

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._action_library: Dict[str, PlanAction] = {}
            self._plans: Dict[str, Plan] = {}
            self._goals: Dict[str, Goal] = {}
            self._world_states: Dict[str, WorldState] = {}
            self._goal_queue: List[Tuple[float, str, str]] = []
            self._plan_history: Dict[str, List[Dict[str, Any]]] = {}
            self._initialized = True

    @classmethod
    def get_instance(cls) -> 'AgentPlanningCore':
        return cls()

    def register_action(self, name: str, preconditions: Dict[str, Any],
                        effects: Dict[str, Any], cost: float = 1.0,
                        duration: float = 0.0) -> PlanAction:
        """Register an action in the action library."""
        action = PlanAction(
            name=name,
            preconditions=preconditions,
            effects=effects,
            cost=cost,
            duration=duration,
        )
        self._action_library[name] = action
        return action

    def register_composite_action(self, name: str, children: List[PlanAction],
                                  preconditions: Dict[str, Any] = None) -> PlanAction:
        """Register a composite action composed of sub-actions."""
        combined_effects: Dict[str, Any] = {}
        for child in children:
            combined_effects.update(child.effects)

        action = PlanAction(
            name=name,
            action_type=ActionType.COMPOSITE,
            preconditions=preconditions or {},
            effects=combined_effects,
            cost=sum(c.cost for c in children),
            children=children,
        )
        self._action_library[name] = action
        return action

    def create_goal(self, name: str, target_state: Dict[str, Any],
                    priority: float = 1.0, parent_goal: Optional[str] = None) -> Goal:
        """Create a new goal for planning."""
        goal = Goal(
            name=name,
            target_state=target_state,
            priority=priority,
            parent_goal=parent_goal,
        )
        self._goals[goal.goal_id] = goal
        if parent_goal and parent_goal in self._goals:
            self._goals[parent_goal].sub_goals.append(goal.goal_id)
        heapq.heappush(self._goal_queue, (-priority, goal.goal_id, _time_module.time()))
        return goal

    def plan(self, agent_id: str, goal_id: str,
             current_state: Dict[str, Any]) -> Optional[Plan]:
        """Generate a plan to achieve a goal from the current state."""
        goal = self._goals.get(goal_id)
        if not goal:
            return None

        state = WorldState(facts=dict(current_state))
        self._world_states[state.state_id] = state

        plan = Plan(agent_id=agent_id, goal=goal.target_state, status=PlanStatus.PLANNING)

        actions = self._backward_search(state, goal.target_state, set())
        if actions is None:
            plan.status = PlanStatus.FAILED
            self._plans[plan.plan_id] = plan
            return plan

        plan.actions = list(reversed(actions))
        plan.total_cost = sum(a.cost for a in plan.actions)
        plan.status = PlanStatus.IDLE
        self._plans[plan.plan_id] = plan
        return plan

    def _backward_search(self, state: WorldState, goal: Dict[str, Any],
                         visited: Set[str], depth: int = 0) -> Optional[List[PlanAction]]:
        """Backward search from goal to current state."""
        if depth > 50:
            return None

        if state.satisfies(goal):
            return []

        remaining = {k: v for k, v in goal.items() if not state.satisfies({k: v})}

        for action_name, action in self._action_library.items():
            if action_name in visited:
                continue

            effects = action.effects
            if not any(k in effects for k in remaining):
                continue

            new_state_facts = dict(state.facts)
            new_state_facts.update(effects)
            new_state = WorldState(facts=new_state_facts)

            new_visited = visited | {action_name}
            result = self._backward_search(new_state, goal, new_visited, depth + 1)
            if result is not None:
                result.append(action)
                return result

        return None

    def forward_plan(self, agent_id: str, goal_id: str,
                     current_state: Dict[str, Any]) -> Optional[Plan]:
        """Generate a plan using forward search from current state."""
        goal = self._goals.get(goal_id)
        if not goal:
            return None

        state = WorldState(facts=dict(current_state))
        self._world_states[state.state_id] = state

        queue: List[Tuple[float, str, WorldState, List[PlanAction]]] = []
        heapq.heappush(queue, (0.0, uuid.uuid4().hex, state, []))

        visited = set()
        visited.add(frozenset(state.facts.items()))

        while queue:
            cost, _, current, actions = heapq.heappop(queue)

            if current.satisfies(goal.target_state):
                plan = Plan(agent_id=agent_id, goal=goal.target_state)
                plan.actions = actions
                plan.total_cost = cost
                plan.status = PlanStatus.IDLE
                self._plans[plan.plan_id] = plan
                return plan

            if len(actions) > 30:
                continue

            for action_name, action in self._action_library.items():
                if not current.satisfies(action.preconditions):
                    continue

                new_facts = dict(current.facts)
                new_facts.update(action.effects)
                new_state = WorldState(facts=new_facts)
                state_key = frozenset(new_state.facts.items())

                if state_key in visited:
                    continue
                visited.add(state_key)

                new_cost = cost + action.cost
                heapq.heappush(queue, (new_cost, uuid.uuid4().hex, new_state, actions + [action]))

        plan = Plan(agent_id=agent_id, goal=goal.target_state, status=PlanStatus.FAILED)
        self._plans[plan.plan_id] = plan
        return plan

    def execute_plan(self, plan_id: str, action_executor: Callable[[PlanAction], bool]) -> PlanStatus:
        """Execute a plan step by step."""
        plan = self._plans.get(plan_id)
        if not plan:
            return PlanStatus.FAILED

        plan.status = PlanStatus.EXECUTING

        while plan.current_index < len(plan.actions):
            action = plan.actions[plan.current_index]
            success = action_executor(action)

            self._plan_history.setdefault(plan_id, []).append({
                "action": action.name,
                "success": success,
                "timestamp": _time_module.time(),
            })

            if not success:
                plan.status = PlanStatus.FAILED
                return PlanStatus.FAILED

            plan.current_index += 1

        plan.status = PlanStatus.COMPLETED
        plan.completed_at = _time_module.time()
        return PlanStatus.COMPLETED

    def replan(self, plan_id: str, current_state: Dict[str, Any]) -> Optional[Plan]:
        """Replan from current state if execution fails."""
        plan = self._plans.get(plan_id)
        if not plan:
            return None

        remaining_goal = dict(plan.goal)
        for action in plan.actions[:plan.current_index]:
            remaining_goal.update({k: v for k, v in action.effects.items()
                                   if k not in remaining_goal or remaining_goal[k] != v})

        goal_id = plan.goal.get("_goal_id", "")
        if not goal_id:
            goal = self.create_goal("replan_temp", remaining_goal)
            goal_id = goal.goal_id

        return self.forward_plan(plan.agent_id, goal_id, current_state)

    def decompose_goal(self, goal_id: str) -> List[Goal]:
        """Decompose a complex goal into sub-goals."""
        goal = self._goals.get(goal_id)
        if not goal:
            return []

        sub_goals = []
        key_groups = self._group_state_keys(goal.target_state)

        for i, keys in enumerate(key_groups):
            sub_target = {k: goal.target_state[k] for k in keys}
            sub_goal = self.create_goal(
                name=f"{goal.name}_sub_{i}",
                target_state=sub_target,
                priority=goal.priority * 0.9,
                parent_goal=goal_id,
            )
            sub_goals.append(sub_goal)

        return sub_goals

    def _group_state_keys(self, state: Dict[str, Any]) -> List[List[str]]:
        """Group related state keys together."""
        keys = list(state.keys())
        if len(keys) <= 3:
            return [keys]
        chunk_size = max(1, len(keys) // 3)
        return [keys[i:i + chunk_size] for i in range(0, len(keys), chunk_size)]

    def get_next_goal(self) -> Optional[Goal]:
        """Get the highest priority goal from the queue."""
        while self._goal_queue:
            _, goal_id, _ = heapq.heappop(self._goal_queue)
            if goal_id in self._goals:
                return self._goals[goal_id]
        return None

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get a plan by ID."""
        return self._plans.get(plan_id)

    def list_goals(self) -> List[Goal]:
        """List all registered goals."""
        return list(self._goals.values())

    def list_actions(self) -> List[PlanAction]:
        """List all registered actions."""
        return list(self._action_library.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get planning system statistics."""
        return {
            "total_actions": len(self._action_library),
            "total_goals": len(self._goals),
            "total_plans": len(self._plans),
            "completed_plans": sum(1 for p in self._plans.values() if p.status == PlanStatus.COMPLETED),
            "failed_plans": sum(1 for p in self._plans.values() if p.status == PlanStatus.FAILED),
            "pending_goals": len(self._goal_queue),
        }


def get_planning_core() -> AgentPlanningCore:
    return AgentPlanningCore.get_instance()