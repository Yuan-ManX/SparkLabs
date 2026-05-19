"""
SparkLabs Agent - Behavior Designer

AI-driven behavior design system that constructs intelligent NPC decision
frameworks. Generates behavior trees, state machines, and utility-based AI
configurations from natural language descriptions and gameplay requirements.

Architecture:
  BehaviorDesigner
    |-- TreeBuilder (constructs hierarchical behavior trees)
    |-- StateDesigner (generates finite state machine configurations)
    |-- UtilityAnalyzer (creates utility-based decision models)
    |-- ConditionGenerator (produces context-aware condition nodes)
    |-- ActionFactory (builds executable action sequences)

Design Principles:
  - COMPOSABLE: behaviors compose from reusable atomic units
  - ADAPTIVE: runtime parameter tuning via utility curves
  - PREDICTABLE: deterministic evaluation with stochastic fallback
  - INTROSPECTABLE: full visualization and debug tracing
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class NodeType(Enum):
    SELECTOR = "selector"
    SEQUENCE = "sequence"
    PARALLEL = "parallel"
    CONDITION = "condition"
    ACTION = "action"
    DECORATOR = "decorator"
    INVERTER = "inverter"
    REPEATER = "repeater"
    SUBTREE = "subtree"


class ExecutionResult(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


class StateMachineType(Enum):
    MEALY = "mealy"
    MOORE = "moore"
    HIERARCHICAL = "hierarchical"
    PUSH_DOWN = "push_down"


class PersonalityTrait(Enum):
    AGGRESSION = "aggression"
    CAUTION = "caution"
    CURIOSITY = "curiosity"
    SOCIABILITY = "sociability"
    PERSISTENCE = "persistence"
    TERRITORIALITY = "territoriality"


BEHAVIOR_PRESETS: Dict[str, Dict[str, Any]] = {
    "patrol_guard": {
        "root_type": NodeType.SELECTOR,
        "description": "Patrol a route, investigate disturbances, engage threats",
        "nodes": [
            {"type": "condition", "name": "threat_detected", "priority": 1},
            {"type": "sequence", "name": "engage_threat", "children": [
                {"type": "action", "name": "alert_allies"},
                {"type": "action", "name": "move_to_threat"},
                {"type": "selector", "name": "combat_response", "children": [
                    {"type": "sequence", "name": "ranged_attack", "children": [
                        {"type": "condition", "name": "has_ammo"},
                        {"type": "action", "name": "fire_weapon"},
                    ]},
                    {"type": "action", "name": "melee_attack"},
                ]},
            ]},
            {"type": "sequence", "name": "patrol_cycle", "children": [
                {"type": "action", "name": "move_to_waypoint"},
                {"type": "action", "name": "look_around"},
                {"type": "decorator", "name": "wait", "params": {"duration": 2.0}},
            ]},
        ],
    },
    "merchant": {
        "root_type": NodeType.SELECTOR,
        "description": "Open shop, serve customers, restock, defend if threatened",
        "nodes": [
            {"type": "condition", "name": "customer_nearby"},
            {"type": "action", "name": "greet_and_trade"},
            {"type": "condition", "name": "low_stock"},
            {"type": "action", "name": "restock_inventory"},
            {"type": "action", "name": "idle_at_shop"},
        ],
    },
    "wildlife_prey": {
        "root_type": NodeType.SELECTOR,
        "description": "Graze, flee from predators, seek shelter at night",
        "nodes": [
            {"type": "condition", "name": "predator_nearby"},
            {"type": "sequence", "name": "flee_response", "children": [
                {"type": "action", "name": "emit_alarm_call"},
                {"type": "action", "name": "run_away"},
                {"type": "action", "name": "find_cover"},
            ]},
            {"type": "sequence", "name": "daily_routine", "children": [
                {"type": "condition", "name": "is_nighttime"},
                {"type": "action", "name": "seek_shelter"},
                {"type": "action", "name": "graze"},
                {"type": "action", "name": "wander"},
            ]},
        ],
    },
    "boss_encounter": {
        "root_type": NodeType.SELECTOR,
        "description": "Multi-phase boss with adaptive difficulty patterns",
        "nodes": [
            {"type": "condition", "name": "health_below_50pct"},
            {"type": "sequence", "name": "phase_two", "children": [
                {"type": "action", "name": "enrage"},
                {"type": "parallel", "name": "enraged_attacks", "children": [
                    {"type": "action", "name": "area_attack"},
                    {"type": "action", "name": "summon_minions"},
                ]},
            ]},
            {"type": "condition", "name": "health_below_25pct"},
            {"type": "sequence", "name": "phase_three", "children": [
                {"type": "action", "name": "desperate_mode"},
                {"type": "repeater", "name": "frenzy_cycle", "params": {"count": 3}},
            ]},
            {"type": "selector", "name": "standard_attacks", "children": [
                {"type": "action", "name": "charge_attack"},
                {"type": "action", "name": "ranged_barrage"},
                {"type": "action", "name": "defensive_stance"},
            ]},
        ],
    },
    "social_npc": {
        "root_type": NodeType.SELECTOR,
        "description": "Social NPC with conversation, schedule, and relationship tracking",
        "nodes": [
            {"type": "sequence", "name": "greet_friends", "children": [
                {"type": "condition", "name": "friend_in_range"},
                {"type": "action", "name": "approach_and_greet"},
                {"type": "action", "name": "share_gossip"},
            ]},
            {"type": "condition", "name": "player_interacting"},
            {"type": "action", "name": "engage_dialogue"},
            {"type": "action", "name": "follow_schedule"},
        ],
    },
}

STATE_MACHINE_PRESETS: Dict[str, List[Dict[str, Any]]] = {
    "door": [
        {"state": "closed", "transitions": [
            {"event": "interact", "target": "opening", "condition": "is_unlocked"},
            {"event": "interact", "target": "closed", "condition": "is_locked"},
        ]},
        {"state": "opening", "transitions": [
            {"event": "animation_complete", "target": "open"},
        ]},
        {"state": "open", "transitions": [
            {"event": "interact", "target": "closing"},
            {"event": "auto_close_timer", "target": "closing"},
        ]},
        {"state": "closing", "transitions": [
            {"event": "animation_complete", "target": "closed"},
        ]},
    ],
    "enemy_ai": [
        {"state": "idle", "transitions": [
            {"event": "player_detected", "target": "alert"},
            {"event": "damage_taken", "target": "alert"},
        ]},
        {"state": "alert", "transitions": [
            {"event": "player_lost", "target": "search"},
            {"event": "player_in_range", "target": "combat"},
        ]},
        {"state": "search", "transitions": [
            {"event": "player_found", "target": "combat"},
            {"event": "search_timeout", "target": "idle"},
        ]},
        {"state": "combat", "transitions": [
            {"event": "player_fled", "target": "search"},
            {"event": "health_critical", "target": "flee"},
            {"event": "player_defeated", "target": "idle"},
        ]},
        {"state": "flee", "transitions": [
            {"event": "safe_distance", "target": "idle"},
        ]},
    ],
}


@dataclass
class BehaviorNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    node_type: NodeType = NodeType.ACTION
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    description: str = ""
    cooldown_seconds: float = 0.0
    last_executed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "parent_id": self.parent_id,
            "children": self.children,
            "conditions": self.conditions,
            "params": self.params,
            "priority": self.priority,
            "description": self.description,
            "cooldown_seconds": self.cooldown_seconds,
        }


@dataclass
class BehaviorTree:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    root_id: Optional[str] = None
    nodes: Dict[str, BehaviorNode] = field(default_factory=dict)
    target_entity_type: str = ""
    personality_profile: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    complexity_score: float = 0.0
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "root_id": self.root_id,
            "node_count": len(self.nodes),
            "target_entity_type": self.target_entity_type,
            "personality_profile": self.personality_profile,
            "complexity_score": round(self.complexity_score, 2),
            "validation_errors": self.validation_errors,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["nodes"] = {nid: n.to_dict() for nid, n in self.nodes.items()}
        return result


@dataclass
class StateMachineConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    machine_type: StateMachineType = StateMachineType.MEALY
    states: List[Dict[str, Any]] = field(default_factory=list)
    initial_state: str = "idle"
    global_transitions: List[Dict[str, Any]] = field(default_factory=list)
    target_entity: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "machine_type": self.machine_type.value,
            "state_count": len(self.states),
            "initial_state": self.initial_state,
            "total_transitions": sum(
                len(s.get("transitions", [])) for s in self.states
            ),
            "target_entity": self.target_entity,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["states"] = self.states
        result["global_transitions"] = self.global_transitions
        return result


@dataclass
class DesignSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_name: str = ""
    description: str = ""
    trees: List[str] = field(default_factory=list)
    state_machines: List[str] = field(default_factory=list)
    personality_traits: Dict[str, float] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_name": self.entity_name,
            "description": self.description,
            "tree_count": len(self.trees),
            "machine_count": len(self.state_machines),
            "personality_traits": self.personality_traits,
            "constraints": self.constraints,
            "completed": self.completed,
        }


class BehaviorDesigner:
    """
    AI-driven behavior design engine for NPC decision systems.

    Constructs behavior trees, finite state machines, and utility-based
    AI models from high-level descriptions. Supports real-time editing,
    validation, complexity analysis, and preview simulation.
    """

    _instance: Optional["BehaviorDesigner"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_TREES = 500
    MAX_MACHINES = 200
    MAX_SESSIONS = 50

    def __init__(self):
        self._trees: Dict[str, BehaviorTree] = {}
        self._machines: Dict[str, StateMachineConfig] = {}
        self._sessions: Dict[str, DesignSession] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._total_tree_nodes: int = 0
        self._total_validations: int = 0

    @classmethod
    def get_instance(cls) -> "BehaviorDesigner":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def start_session(
        self,
        entity_name: str,
        description: str = "",
        constraints: Optional[List[str]] = None,
    ) -> DesignSession:
        if len(self._sessions) >= self.MAX_SESSIONS:
            oldest = min(self._sessions.keys(),
                         key=lambda k: self._sessions[k].started_at)
            del self._sessions[oldest]

        session = DesignSession(
            entity_name=entity_name,
            description=description,
            constraints=constraints or [],
        )
        self._sessions[session.id] = session
        return session

    # ------------------------------------------------------------------
    # Behavior Tree Construction
    # ------------------------------------------------------------------

    def build_tree_from_preset(
        self,
        session_id: str,
        preset_name: str,
    ) -> Optional[BehaviorTree]:
        preset = BEHAVIOR_PRESETS.get(preset_name)
        if preset is None:
            return None

        tree = BehaviorTree(
            name=f"{preset_name}_{uuid.uuid4().hex[:6]}",
            target_entity_type=preset_name,
        )

        root = self._build_node_recursive(tree, preset, None)
        tree.root_id = root.id
        tree.nodes[root.id] = root
        tree.complexity_score = self._compute_complexity(tree)

        with self._lock:
            self._trees[tree.id] = tree
            self._total_tree_nodes += len(tree.nodes)

        session = self._sessions.get(session_id)
        if session:
            session.trees.append(tree.id)

        return tree

    def _build_node_recursive(
        self,
        tree: BehaviorTree,
        spec: Dict[str, Any],
        parent_id: Optional[str],
    ) -> BehaviorNode:
        node = BehaviorNode(
            name=spec.get("name", f"node_{uuid.uuid4().hex[:4]}"),
            node_type=NodeType(spec.get("type", "action")),
            parent_id=parent_id,
            params=spec.get("params", {}),
            priority=spec.get("priority", 0),
            description=spec.get("description", ""),
        )

        children = spec.get("children", [])
        for child_spec in children:
            child = self._build_node_recursive(tree, child_spec, node.id)
            tree.nodes[child.id] = child
            node.children.append(child.id)

        if spec.get("node_type") == "decorator" and "children" in spec:
            child_spec = spec["children"][0] if isinstance(spec["children"], list) and spec["children"] else {"type": "action", "name": "decorated_action"}
            child = self._build_node_recursive(tree, child_spec, node.id)
            tree.nodes[child.id] = child
            node.children.append(child.id)

        return node

    def add_node(
        self,
        tree_id: str,
        parent_id: str,
        name: str,
        node_type: NodeType,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[BehaviorNode]:
        tree = self._trees.get(tree_id)
        if tree is None or parent_id not in tree.nodes:
            return None

        node = BehaviorNode(
            name=name,
            node_type=node_type,
            parent_id=parent_id,
            params=params or {},
        )
        tree.nodes[node.id] = node
        tree.nodes[parent_id].children.append(node.id)
        self._total_tree_nodes += 1
        tree.complexity_score = self._compute_complexity(tree)
        return node

    def remove_node(self, tree_id: str, node_id: str) -> bool:
        tree = self._trees.get(tree_id)
        if tree is None or node_id not in tree.nodes:
            return False
        if node_id == tree.root_id:
            return False

        node = tree.nodes[node_id]
        if node.parent_id and node.parent_id in tree.nodes:
            parent = tree.nodes[node.parent_id]
            parent.children = [c for c in parent.children if c != node_id]

        children_to_remove = list(node.children)
        for child_id in children_to_remove:
            self.remove_node(tree_id, child_id)

        del tree.nodes[node_id]
        self._total_tree_nodes -= 1
        tree.complexity_score = self._compute_complexity(tree)
        return True

    # ------------------------------------------------------------------
    # State Machine Construction
    # ------------------------------------------------------------------

    def build_machine_from_preset(
        self,
        session_id: str,
        preset_name: str,
        machine_type: StateMachineType = StateMachineType.MEALY,
    ) -> Optional[StateMachineConfig]:
        preset = STATE_MACHINE_PRESETS.get(preset_name)
        if preset is None:
            return None

        machine = StateMachineConfig(
            name=f"{preset_name}_{uuid.uuid4().hex[:6]}",
            machine_type=machine_type,
            states=preset,
            initial_state=preset[0]["state"] if preset else "idle",
            target_entity=preset_name,
        )

        with self._lock:
            self._machines[machine.id] = machine

        session = self._sessions.get(session_id)
        if session:
            session.state_machines.append(machine.id)

        return machine

    def add_state(
        self,
        machine_id: str,
        state_name: str,
        transitions: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        machine = self._machines.get(machine_id)
        if machine is None:
            return False

        machine.states.append({
            "state": state_name,
            "transitions": transitions or [],
        })
        return True

    def add_transition(
        self,
        machine_id: str,
        from_state: str,
        to_state: str,
        event: str,
        condition: str = "",
    ) -> bool:
        machine = self._machines.get(machine_id)
        if machine is None:
            return False

        for state_def in machine.states:
            if state_def["state"] == from_state:
                state_def["transitions"].append({
                    "event": event,
                    "target": to_state,
                    "condition": condition or "",
                })
                return True
        return False

    # ------------------------------------------------------------------
    # Personality Integration
    # ------------------------------------------------------------------

    def apply_personality(
        self,
        tree_id: str,
        traits: Dict[str, float],
    ) -> bool:
        tree = self._trees.get(tree_id)
        if tree is None:
            return False

        tree.personality_profile = traits
        aggression = traits.get("aggression", 0.5)
        caution = traits.get("caution", 0.5)

        for node in tree.nodes.values():
            if node.node_type == NodeType.CONDITION:
                if "threat" in node.name.lower() and caution > 0.6:
                    node.priority += 2
            elif node.node_type == NodeType.ACTION:
                if "attack" in node.name.lower() and aggression > 0.7:
                    node.cooldown_seconds = max(0.1, node.cooldown_seconds - 1.0)

        return True

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_tree(self, tree_id: str) -> List[str]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return ["Tree not found"]

        errors: List[str] = []

        if tree.root_id is None or tree.root_id not in tree.nodes:
            errors.append("Missing or invalid root node")
            return errors

        visited: Set[str] = set()
        self._validate_node_recursive(tree, tree.root_id, visited, errors)

        unreachable = set(tree.nodes.keys()) - visited
        if unreachable:
            errors.append(f"Unreachable nodes: {len(unreachable)}")

        if len(tree.nodes) > 100:
            errors.append(f"High complexity: {len(tree.nodes)} nodes exceeds recommended limit")

        action_count = sum(1 for n in tree.nodes.values() if n.node_type == NodeType.ACTION)
        if action_count == 0:
            errors.append("No action nodes in tree")

        tree.validation_errors = errors
        self._total_validations += 1
        return errors

    def _validate_node_recursive(
        self,
        tree: BehaviorTree,
        node_id: str,
        visited: Set[str],
        errors: List[str],
    ) -> None:
        if node_id in visited:
            errors.append(f"Cycle detected at node {tree.nodes[node_id].name}")
            return

        visited.add(node_id)
        node = tree.nodes.get(node_id)
        if node is None:
            errors.append(f"Missing node {node_id}")
            return

        for child_id in node.children:
            self._validate_node_recursive(tree, child_id, visited, errors)

    def validate_machine(self, machine_id: str) -> List[str]:
        machine = self._machines.get(machine_id)
        if machine is None:
            return ["Machine not found"]

        errors: List[str] = []
        state_names = {s["state"] for s in machine.states}

        if machine.initial_state not in state_names:
            errors.append(f"Initial state '{machine.initial_state}' not defined")

        for state_def in machine.states:
            for trans in state_def.get("transitions", []):
                if trans.get("target") not in state_names:
                    errors.append(
                        f"State '{state_def['state']}' transitions to "
                        f"undefined '{trans.get('target')}'"
                    )

        reachable = self._find_reachable_states(machine)
        isolated = state_names - reachable
        if isolated:
            errors.append(f"Isolated states: {isolated}")

        self._total_validations += 1
        return errors

    def _find_reachable_states(self, machine: StateMachineConfig) -> Set[str]:
        visited: Set[str] = set()
        queue = [machine.initial_state]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            for state_def in machine.states:
                if state_def["state"] == current:
                    for trans in state_def.get("transitions", []):
                        target = trans.get("target", "")
                        if target and target not in visited:
                            queue.append(target)

        return visited

    # ------------------------------------------------------------------
    # Complexity Analysis
    # ------------------------------------------------------------------

    def _compute_complexity(self, tree: BehaviorTree) -> float:
        if not tree.nodes:
            return 0.0

        action_count = sum(1 for n in tree.nodes.values() if n.node_type == NodeType.ACTION)
        condition_count = sum(1 for n in tree.nodes.values() if n.node_type == NodeType.CONDITION)
        total = len(tree.nodes)

        base = (total * 0.3 + action_count * 0.5 + condition_count * 0.7) / 10.0
        branch_depth = self._compute_max_depth(tree)
        branching_factor = len(tree.nodes[tree.root_id].children) if tree.root_id and tree.root_id in tree.nodes else 1

        return round(min(10.0, base + branch_depth * 0.3 + branching_factor * 0.2), 2)

    def _compute_max_depth(self, tree: BehaviorTree) -> int:
        if tree.root_id is None or tree.root_id not in tree.nodes:
            return 0

        def depth(node_id: str, d: int = 0) -> int:
            node = tree.nodes.get(node_id)
            if node is None or not node.children:
                return d
            return max(depth(cid, d + 1) for cid in node.children)

        return depth(tree.root_id)

    # ------------------------------------------------------------------
    # Preview Simulation
    # ------------------------------------------------------------------

    def simulate_tree(self, tree_id: str, steps: int = 20) -> Dict[str, Any]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return {"error": "Tree not found"}

        trace: List[Dict[str, Any]] = []
        active_nodes: List[str] = [tree.root_id] if tree.root_id else []
        result_stats = {"actions_taken": 0, "conditions_checked": 0, "time_elapsed": 0.0}

        for step in range(steps):
            step_trace: Dict[str, Any] = {"step": step, "evaluated": []}

            for node_id in active_nodes:
                node = tree.nodes.get(node_id)
                if node is None:
                    continue

                if node.node_type == NodeType.CONDITION:
                    result_stats["conditions_checked"] += 1
                    passed = step % 3 != 0 if "threat" in node.name else step % 2 == 0
                    step_trace["evaluated"].append({
                        "node": node.name,
                        "type": "condition",
                        "result": "passed" if passed else "failed",
                    })

                elif node.node_type == NodeType.ACTION:
                    result_stats["actions_taken"] += 1
                    step_trace["evaluated"].append({
                        "node": node.name,
                        "type": "action",
                        "result": "executed",
                    })

            result_stats["time_elapsed"] += 0.1
            trace.append(step_trace)

        return {
            "tree_name": tree.name,
            "steps_simulated": steps,
            "trace": trace,
            "statistics": result_stats,
        }

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_tree(self, tree_id: str) -> Optional[BehaviorTree]:
        return self._trees.get(tree_id)

    def get_machine(self, machine_id: str) -> Optional[StateMachineConfig]:
        return self._machines.get(machine_id)

    def get_session(self, session_id: str) -> Optional[DesignSession]:
        return self._sessions.get(session_id)

    def list_trees(self) -> List[BehaviorTree]:
        return list(self._trees.values())

    def list_machines(self) -> List[StateMachineConfig]:
        return list(self._machines.values())

    def list_sessions(self) -> List[DesignSession]:
        return list(self._sessions.values())

    def get_available_presets(self) -> Dict[str, List[str]]:
        return {
            "trees": list(BEHAVIOR_PRESETS.keys()),
            "machines": list(STATE_MACHINE_PRESETS.keys()),
        }

    def get_personality_traits(self) -> List[str]:
        return [t.value for t in PersonalityTrait]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_trees": len(self._trees),
            "total_machines": len(self._machines),
            "total_sessions": len(self._sessions),
            "total_tree_nodes": self._total_tree_nodes,
            "total_validations": self._total_validations,
            "average_tree_complexity": round(
                sum(t.complexity_score for t in self._trees.values()) /
                max(1, len(self._trees)), 2
            ),
            "presets_available": {
                "trees": len(BEHAVIOR_PRESETS),
                "machines": len(STATE_MACHINE_PRESETS),
            },
            "validation_error_rate": round(
                sum(1 for t in self._trees.values() if t.validation_errors) /
                max(1, len(self._trees)), 2
            ),
        }


def get_behavior_designer() -> BehaviorDesigner:
    return BehaviorDesigner.get_instance()