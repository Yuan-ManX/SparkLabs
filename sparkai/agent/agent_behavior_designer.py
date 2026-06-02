"""
SparkLabs Agent - Behavior Designer

AI-driven NPC behavior design system that constructs intelligent
decision frameworks for non-player characters. Generates behavior trees,
finite state machines, and composable action patterns from archetype
profiles and gameplay requirements.

Architecture:
  AgentBehaviorDesigner (Singleton)
    |-- BehaviorTreeNode (atomic decision unit in a behavior tree)
    |-- BehaviorTree (hierarchical composition of decision nodes)
    |-- StateTransition (event-driven edge between FSM states)
    |-- StateMachine (finite state machine for NPC lifecycle)
    |-- ActionPattern (reusable action template with costs)
    |-- NPCBehaviorProfile (personality-driven behavior config)

Design Principles:
  - COMPOSABLE: behaviors assemble from reusable atomic patterns
  - ADAPTIVE: runtime parameter tuning via archetype profiles
  - DETERMINISTIC: predictable evaluation with stochastic exploration
  - TRACEABLE: full execution simulation and complexity analysis
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


class BehaviorNodeType(Enum):
    SELECTOR = "selector"
    SEQUENCE = "sequence"
    CONDITION = "condition"
    ACTION = "action"
    DECORATOR = "decorator"
    PARALLEL = "parallel"
    RANDOM = "random"
    PRIORITY = "priority"


class StateMachineState(Enum):
    IDLE = "idle"
    PATROL = "patrol"
    ALERT = "alert"
    COMBAT = "combat"
    FLEE = "flee"
    SEARCH = "search"
    GUARD = "guard"
    REST = "rest"
    TRADE = "trade"
    DIALOGUE = "dialogue"


class BehaviorArchetype(Enum):
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    COWARD = "coward"
    CURIOUS = "curious"
    TERRITORIAL = "territorial"
    SOCIAL = "social"
    SOLITARY = "solitary"
    GUARDIAN = "guardian"
    PREDATOR = "predator"
    PREY = "prey"


class ActionType(Enum):
    MOVE_TO = "move_to"
    ATTACK = "attack"
    DEFEND = "defend"
    HEAL = "heal"
    GATHER = "gather"
    BUILD = "build"
    TALK = "talk"
    FLEE = "flee"
    HIDE = "hide"
    PATROL = "patrol"


ARCHETYPE_PROFILES: Dict[str, Dict[str, float]] = {
    BehaviorArchetype.AGGRESSIVE.value: {
        "aggression": 0.90, "courage": 0.85, "sociability": 0.20,
        "curiosity": 0.35, "loyalty": 0.40, "threat_threshold": 0.25,
    },
    BehaviorArchetype.DEFENSIVE.value: {
        "aggression": 0.30, "courage": 0.60, "sociability": 0.45,
        "curiosity": 0.30, "loyalty": 0.70, "threat_threshold": 0.50,
    },
    BehaviorArchetype.COWARD.value: {
        "aggression": 0.10, "courage": 0.15, "sociability": 0.25,
        "curiosity": 0.20, "loyalty": 0.30, "threat_threshold": 0.10,
    },
    BehaviorArchetype.CURIOUS.value: {
        "aggression": 0.25, "courage": 0.55, "sociability": 0.60,
        "curiosity": 0.90, "loyalty": 0.35, "threat_threshold": 0.65,
    },
    BehaviorArchetype.TERRITORIAL.value: {
        "aggression": 0.75, "courage": 0.70, "sociability": 0.15,
        "curiosity": 0.30, "loyalty": 0.55, "threat_threshold": 0.20,
    },
    BehaviorArchetype.SOCIAL.value: {
        "aggression": 0.15, "courage": 0.40, "sociability": 0.95,
        "curiosity": 0.55, "loyalty": 0.50, "threat_threshold": 0.60,
    },
    BehaviorArchetype.SOLITARY.value: {
        "aggression": 0.35, "courage": 0.50, "sociability": 0.10,
        "curiosity": 0.45, "loyalty": 0.20, "threat_threshold": 0.35,
    },
    BehaviorArchetype.GUARDIAN.value: {
        "aggression": 0.55, "courage": 0.80, "sociability": 0.40,
        "curiosity": 0.25, "loyalty": 0.90, "threat_threshold": 0.30,
    },
    BehaviorArchetype.PREDATOR.value: {
        "aggression": 0.80, "courage": 0.75, "sociability": 0.15,
        "curiosity": 0.50, "loyalty": 0.10, "threat_threshold": 0.15,
    },
    BehaviorArchetype.PREY.value: {
        "aggression": 0.05, "courage": 0.20, "sociability": 0.55,
        "curiosity": 0.40, "loyalty": 0.60, "threat_threshold": 0.08,
    },
}

DEFAULT_ACTION_PATTERNS: Dict[str, Dict[str, Any]] = {
    ActionType.MOVE_TO.value: {
        "target_selection": "nearest_waypoint",
        "duration_ms": 1500,
        "animation": "walk_cycle",
        "success_rate": 0.95,
        "cost": 1.0,
    },
    ActionType.ATTACK.value: {
        "target_selection": "nearest_enemy",
        "duration_ms": 800,
        "animation": "attack_swing",
        "success_rate": 0.80,
        "cost": 5.0,
    },
    ActionType.DEFEND.value: {
        "target_selection": "self",
        "duration_ms": 1200,
        "animation": "shield_raise",
        "success_rate": 0.90,
        "cost": 3.0,
    },
    ActionType.HEAL.value: {
        "target_selection": "lowest_health_ally",
        "duration_ms": 2000,
        "animation": "heal_cast",
        "success_rate": 0.85,
        "cost": 8.0,
    },
    ActionType.GATHER.value: {
        "target_selection": "nearest_resource",
        "duration_ms": 3000,
        "animation": "gather_loop",
        "success_rate": 0.70,
        "cost": 2.0,
    },
    ActionType.BUILD.value: {
        "target_selection": "construction_site",
        "duration_ms": 5000,
        "animation": "build_hammer",
        "success_rate": 0.75,
        "cost": 10.0,
    },
    ActionType.TALK.value: {
        "target_selection": "nearest_npc",
        "duration_ms": 2500,
        "animation": "talk_idle",
        "success_rate": 0.90,
        "cost": 0.5,
    },
    ActionType.FLEE.value: {
        "target_selection": "furthest_safe_point",
        "duration_ms": 1000,
        "animation": "sprint_cycle",
        "success_rate": 0.85,
        "cost": 6.0,
    },
    ActionType.HIDE.value: {
        "target_selection": "nearest_cover",
        "duration_ms": 1500,
        "animation": "crouch_idle",
        "success_rate": 0.88,
        "cost": 4.0,
    },
    ActionType.PATROL.value: {
        "target_selection": "next_patrol_point",
        "duration_ms": 2000,
        "animation": "walk_cycle",
        "success_rate": 0.92,
        "cost": 1.5,
    },
}

BEHAVIOR_TREE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "combat_engagement": {
        "description": "Engage threats with escalating response levels",
        "root_type": BehaviorNodeType.SELECTOR,
        "nodes": [
            {"type": BehaviorNodeType.CONDITION, "name": "enemy_in_range",
             "condition_expression": "distance_to_nearest_enemy < attack_range"},
            {"type": BehaviorNodeType.SEQUENCE, "name": "attack_sequence",
             "children": [
                 {"type": BehaviorNodeType.DECORATOR, "name": "cooldown_check",
                  "condition_expression": "last_attack_time + cooldown < now"},
                 {"type": BehaviorNodeType.ACTION, "name": "execute_attack",
                  "action_config": {"target": "nearest_enemy", "damage_multiplier": 1.0}},
             ]},
            {"type": BehaviorNodeType.SEQUENCE, "name": "pursue_enemy",
             "children": [
                 {"type": BehaviorNodeType.ACTION, "name": "move_toward_enemy",
                  "action_config": {"speed": "chase", "target": "last_known_position"}},
                 {"type": BehaviorNodeType.ACTION, "name": "scan_surroundings",
                  "action_config": {"cone_angle": 90, "range": "vision_range"}},
             ]},
            {"type": BehaviorNodeType.ACTION, "name": "return_to_patrol",
             "action_config": {"target": "home_waypoint"}},
        ],
    },
    "flee_and_hide": {
        "description": "Prioritize survival through escape and concealment",
        "root_type": BehaviorNodeType.PRIORITY,
        "nodes": [
            {"type": BehaviorNodeType.CONDITION, "name": "threat_detected",
             "condition_expression": "threat_level > threat_threshold", "priority": 10},
            {"type": BehaviorNodeType.SELECTOR, "name": "escape_options", "priority": 9,
             "children": [
                 {"type": BehaviorNodeType.SEQUENCE, "name": "hide_first",
                  "children": [
                      {"type": BehaviorNodeType.CONDITION, "name": "cover_nearby",
                       "condition_expression": "distance_to_nearest_cover < hide_range"},
                      {"type": BehaviorNodeType.ACTION, "name": "take_cover",
                       "action_config": {"target": "nearest_cover", "stance": "crouched"}},
                  ]},
                 {"type": BehaviorNodeType.ACTION, "name": "flee_direction",
                  "action_config": {"direction": "away_from_threat", "speed": "sprint"}},
             ]},
            {"type": BehaviorNodeType.ACTION, "name": "resume_idle",
             "action_config": {"mode": "idle"}, "priority": 1},
        ],
    },
    "guard_post": {
        "description": "Defend a designated area with threat assessment",
        "root_type": BehaviorNodeType.SEQUENCE,
        "nodes": [
            {"type": BehaviorNodeType.ACTION, "name": "scan_perimeter",
             "action_config": {"angle_step": 15, "pause_between": 500}},
            {"type": BehaviorNodeType.CONDITION, "name": "intruder_spotted",
             "condition_expression": "any_npc_in_restricted_zone"},
            {"type": BehaviorNodeType.SELECTOR, "name": "intruder_response",
             "children": [
                 {"type": BehaviorNodeType.RANDOM, "name": "vocal_warning",
                  "children": [
                      {"type": BehaviorNodeType.ACTION, "name": "shout_warning",
                       "action_config": {"message": "halt", "radius": "voice_range"}},
                      {"type": BehaviorNodeType.ACTION, "name": "blow_whistle",
                       "action_config": {"alert_allies": True}},
                  ]},
                 {"type": BehaviorNodeType.ACTION, "name": "engage_intruder",
                  "action_config": {"target": "intruder", "force_level": "lethal"}},
             ]},
        ],
    },
    "merchant_routine": {
        "description": "Daily merchant behavior with customer interaction",
        "root_type": BehaviorNodeType.PRIORITY,
        "nodes": [
            {"type": BehaviorNodeType.CONDITION, "name": "shop_closed",
             "condition_expression": "current_time not in operating_hours", "priority": 10},
            {"type": BehaviorNodeType.ACTION, "name": "close_shop",
             "action_config": {"animation": "close_shutters"}, "priority": 9},
            {"type": BehaviorNodeType.SEQUENCE, "name": "serve_customers", "priority": 8,
             "children": [
                 {"type": BehaviorNodeType.CONDITION, "name": "customer_waiting",
                  "condition_expression": "customer_queue_size > 0"},
                 {"type": BehaviorNodeType.PARALLEL, "name": "process_transaction",
                  "children": [
                      {"type": BehaviorNodeType.ACTION, "name": "greet_customer",
                       "action_config": {"greeting_pool": "merchant_greetings"}},
                      {"type": BehaviorNodeType.ACTION, "name": "display_wares",
                       "action_config": {"layout": "counter_display"}},
                      {"type": BehaviorNodeType.ACTION, "name": "complete_sale",
                       "action_config": {"currency_type": "gold"}},
                  ]},
             ]},
            {"type": BehaviorNodeType.SEQUENCE, "name": "maintain_stock", "priority": 5,
             "children": [
                 {"type": BehaviorNodeType.CONDITION, "name": "inventory_low",
                  "condition_expression": "item_count < restock_threshold"},
                 {"type": BehaviorNodeType.ACTION, "name": "restock_shelves",
                  "action_config": {"source": "warehouse_inventory"}},
             ]},
            {"type": BehaviorNodeType.ACTION, "name": "idle_at_counter",
             "action_config": {"idle_animations": ["polish_counter", "count_coins", "read_ledger"]}},
        ],
    },
    "social_explorer": {
        "description": "Explore environment while engaging with other NPCs",
        "root_type": BehaviorNodeType.SELECTOR,
        "nodes": [
            {"type": BehaviorNodeType.SEQUENCE, "name": "social_interaction",
             "children": [
                 {"type": BehaviorNodeType.CONDITION, "name": "npc_nearby",
                  "condition_expression": "distance_to_nearest_friendly_npc < interaction_range"},
                 {"type": BehaviorNodeType.RANDOM, "name": "social_actions",
                  "children": [
                      {"type": BehaviorNodeType.ACTION, "name": "start_conversation",
                       "action_config": {"topic_pool": "small_talk"}},
                      {"type": BehaviorNodeType.ACTION, "name": "share_item",
                       "action_config": {"item_category": "gift"}},
                      {"type": BehaviorNodeType.ACTION, "name": "tell_joke",
                       "action_config": {"humor_pool": "npc_jokes"}},
                  ]},
             ]},
            {"type": BehaviorNodeType.SEQUENCE, "name": "explore_area",
             "children": [
                 {"type": BehaviorNodeType.ACTION, "name": "pick_random_point",
                  "action_config": {"radius": "wander_range", "bias": "unvisited"}},
                 {"type": BehaviorNodeType.ACTION, "name": "move_to_point",
                  "action_config": {"speed": "walk"}},
                 {"type": BehaviorNodeType.ACTION, "name": "investigate_point",
                  "action_config": {"duration_ms": 1500, "animation": "look_around"}},
             ]},
        ],
    },
}


@dataclass
class BehaviorTreeNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_type: BehaviorNodeType = BehaviorNodeType.ACTION
    name: str = ""
    children_ids: List[str] = field(default_factory=list)
    condition_expression: str = ""
    action_config: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    cooldown_ms: int = 0
    interruptible: bool = True
    parent_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "name": self.name,
            "children_ids": list(self.children_ids),
            "condition_expression": self.condition_expression,
            "action_config": dict(self.action_config),
            "priority": self.priority,
            "cooldown_ms": self.cooldown_ms,
            "interruptible": self.interruptible,
            "parent_id": self.parent_id,
        }


@dataclass
class BehaviorTree:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    root_node_id: str = ""
    all_nodes: List[BehaviorTreeNode] = field(default_factory=list)
    npc_id: str = ""
    archetype: str = ""
    description: str = ""
    complexity_score: float = 0.0
    execution_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "id": self.id,
            "root_node_id": self.root_node_id,
            "node_count": len(self.all_nodes),
            "npc_id": self.npc_id,
            "archetype": self.archetype,
            "description": self.description,
            "complexity_score": round(self.complexity_score, 2),
            "execution_stats": dict(self.execution_stats),
            "nodes": [n.to_dict() for n in self.all_nodes],
        }


@dataclass
class StateTransition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_state: str = ""
    to_state: str = ""
    conditions: List[str] = field(default_factory=list)
    priority: int = 0
    cooldown: float = 0.0
    trigger_events: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "id": self.id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "conditions": list(self.conditions),
            "priority": self.priority,
            "cooldown": self.cooldown,
            "trigger_events": list(self.trigger_events),
        }


@dataclass
class StateMachine:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    npc_id: str = ""
    states: List[str] = field(default_factory=list)
    transitions: List[StateTransition] = field(default_factory=list)
    initial_state: str = ""
    current_state: str = ""
    state_history: List[Tuple[str, float]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "id": self.id,
            "npc_id": self.npc_id,
            "state_count": len(self.states),
            "transition_count": len(self.transitions),
            "initial_state": self.initial_state,
            "current_state": self.current_state,
            "state_history_length": len(self.state_history),
            "states": list(self.states),
            "transitions": [t.to_dict() for t in self.transitions],
            "state_history": [
                {"state": s, "timestamp": ts} for s, ts in self.state_history[-20:]
            ],
        }


@dataclass
class ActionPattern:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    action_type: str = ActionType.PATROL.value
    target_selection: str = ""
    duration_ms: int = 1000
    animation: str = ""
    success_rate: float = 0.80
    cost: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "id": self.id,
            "name": self.name,
            "action_type": self.action_type,
            "target_selection": self.target_selection,
            "duration_ms": self.duration_ms,
            "animation": self.animation,
            "success_rate": round(self.success_rate, 4),
            "cost": round(self.cost, 2),
        }


@dataclass
class NPCBehaviorProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    npc_id: str = ""
    archetype: str = BehaviorArchetype.SOLITARY.value
    aggression: float = 0.35
    courage: float = 0.50
    sociability: float = 0.10
    curiosity: float = 0.45
    loyalty: float = 0.20
    threat_threshold: float = 0.35
    behavior_tree_id: str = ""
    state_machine_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "id": self.id,
            "npc_id": self.npc_id,
            "archetype": self.archetype,
            "aggression": round(self.aggression, 4),
            "courage": round(self.courage, 4),
            "sociability": round(self.sociability, 4),
            "curiosity": round(self.curiosity, 4),
            "loyalty": round(self.loyalty, 4),
            "threat_threshold": round(self.threat_threshold, 4),
            "behavior_tree_id": self.behavior_tree_id,
            "state_machine_id": self.state_machine_id,
        }


class AgentBehaviorDesigner:
    """
    AI-driven NPC behavior design system for behavior trees, state
    machines, and action patterns.

    Generates complete decision frameworks from archetype profiles,
    composes behavior trees from modular node definitions, simulates
    execution for validation, and optimizes runtime performance.

    Usage:
        designer = get_agent_behavior_designer()
        profile = designer.create_profile("guard_01", BehaviorArchetype.GUARDIAN)
        tree = designer.design_behavior_tree(profile, BehaviorArchetype.GUARDIAN)
        machine = designer.design_state_machine(profile, BehaviorArchetype.GUARDIAN)
        patterns = designer.generate_action_patterns(BehaviorArchetype.GUARDIAN)
        stats = designer.get_stats()
    """

    _instance: Optional["AgentBehaviorDesigner"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_TREES = 250
    _MAX_MACHINES = 200
    _MAX_PATTERNS = 500
    _MAX_PROFILES = 500

    def __new__(cls) -> "AgentBehaviorDesigner":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentBehaviorDesigner":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._trees: Dict[str, BehaviorTree] = {}
        self._machines: Dict[str, StateMachine] = {}
        self._patterns: Dict[str, ActionPattern] = {}
        self._profiles: Dict[str, NPCBehaviorProfile] = {}
        self._node_registry: Dict[str, BehaviorTreeNode] = {}
        self._transition_registry: Dict[str, StateTransition] = {}
        self._stats: Dict[str, Any] = {
            "trees_designed": 0,
            "state_machines_designed": 0,
            "action_patterns_generated": 0,
            "profiles_created": 0,
            "complexity_analyses": 0,
            "execution_simulations": 0,
            "performance_optimizations": 0,
        }

    def create_profile(
        self,
        npc_id: str,
        archetype: BehaviorArchetype,
    ) -> NPCBehaviorProfile:
        _time_module.sleep(0.001)
        traits = ARCHETYPE_PROFILES.get(archetype.value, ARCHETYPE_PROFILES[BehaviorArchetype.SOLITARY.value])

        profile = NPCBehaviorProfile(
            npc_id=npc_id,
            archetype=archetype.value,
            aggression=traits["aggression"],
            courage=traits["courage"],
            sociability=traits["sociability"],
            curiosity=traits["curiosity"],
            loyalty=traits["loyalty"],
            threat_threshold=traits["threat_threshold"],
        )

        if len(self._profiles) >= self._MAX_PROFILES:
            oldest_key = next(iter(self._profiles))
            del self._profiles[oldest_key]

        self._profiles[profile.id] = profile
        self._stats["profiles_created"] += 1
        return profile

    def design_behavior_tree(
        self,
        npc_profile: NPCBehaviorProfile,
        archetype: BehaviorArchetype,
    ) -> BehaviorTree:
        _time_module.sleep(0.001)

        templates = self._select_tree_templates(archetype)
        template = templates[hash(npc_profile.npc_id + archetype.value) % len(templates)]

        tree = BehaviorTree(
            npc_id=npc_profile.npc_id,
            archetype=archetype.value,
            description=template.get("description", f"Behavior tree for {archetype.value} archetype"),
        )

        nodes: List[BehaviorTreeNode] = []
        node_stack: List[Tuple[Dict[str, Any], str]] = []
        root_spec = {"type": template.get("root_type", BehaviorNodeType.SELECTOR),
                     "name": "root", "children": template.get("nodes", [])}
        node_stack.append((root_spec, ""))

        while node_stack:
            spec, parent_id = node_stack.pop()
            node = BehaviorTreeNode(
                node_type=spec.get("type", BehaviorNodeType.ACTION),
                name=spec.get("name", f"node_{uuid.uuid4().hex[:6]}"),
                condition_expression=spec.get("condition_expression", ""),
                action_config=spec.get("action_config", {}),
                priority=spec.get("priority", 0),
                cooldown_ms=spec.get("cooldown_ms", 0),
                interruptible=spec.get("interruptible", True),
                parent_id=parent_id,
            )

            if parent_id:
                for existing in nodes:
                    if existing.id == parent_id:
                        existing.children_ids.append(node.id)
                        break

            children = spec.get("children", [])
            for child_spec in reversed(children):
                node_stack.append((child_spec, node.id))

            nodes.append(node)
            self._node_registry[node.id] = node

        if nodes:
            tree.root_node_id = nodes[0].id
        tree.all_nodes = nodes

        tree.complexity_score = self._compute_tree_complexity(tree)
        tree.execution_stats = {"estimated_ticks_per_eval": len(nodes) * 2,
                                "max_depth": self._compute_node_depth(tree),
                                "branch_factor": self._compute_branch_factor(tree)}

        if len(self._trees) >= self._MAX_TREES:
            oldest_key = next(iter(self._trees))
            del self._trees[oldest_key]

        self._trees[tree.id] = tree
        npc_profile.behavior_tree_id = tree.id
        self._stats["trees_designed"] += 1
        return tree

    def compose_behavior_tree_from_nodes(
        self,
        nodes: List[BehaviorTreeNode],
    ) -> BehaviorTree:
        _time_module.sleep(0.001)

        tree = BehaviorTree(
            description="Composed behavior tree from node definitions",
        )

        tree.all_nodes = list(nodes)
        for node in nodes:
            self._node_registry[node.id] = node

        root_candidates = [n for n in nodes if not n.parent_id]
        if root_candidates:
            tree.root_node_id = root_candidates[0].id

        tree.complexity_score = self._compute_tree_complexity(tree)
        tree.execution_stats = {"estimated_ticks_per_eval": len(nodes) * 2,
                                "max_depth": self._compute_node_depth(tree),
                                "branch_factor": self._compute_branch_factor(tree)}

        if len(self._trees) >= self._MAX_TREES:
            oldest_key = next(iter(self._trees))
            del self._trees[oldest_key]

        self._trees[tree.id] = tree
        return tree

    def add_behavior_node(
        self,
        parent_id: str,
        node_type: BehaviorNodeType,
        config: Dict[str, Any],
    ) -> Optional[BehaviorTreeNode]:
        _time_module.sleep(0.001)

        node = BehaviorTreeNode(
            node_type=node_type,
            name=config.get("name", f"node_{uuid.uuid4().hex[:6]}"),
            condition_expression=config.get("condition_expression", ""),
            action_config=config.get("action_config", {}),
            priority=config.get("priority", 0),
            cooldown_ms=config.get("cooldown_ms", 0),
            interruptible=config.get("interruptible", True),
            parent_id=parent_id,
        )

        if parent_id and parent_id in self._node_registry:
            self._node_registry[parent_id].children_ids.append(node.id)

        self._node_registry[node.id] = node

        for tree in self._trees.values():
            if parent_id in {n.id for n in tree.all_nodes}:
                tree.all_nodes.append(node)
                tree.complexity_score = self._compute_tree_complexity(tree)
                break

        return node

    def design_state_machine(
        self,
        npc_profile: NPCBehaviorProfile,
        archetype: BehaviorArchetype,
    ) -> StateMachine:
        _time_module.sleep(0.001)

        state_set = self._generate_states_for_archetype(archetype, npc_profile)
        transitions = self._generate_transitions_for_states(state_set, npc_profile)

        machine = StateMachine(
            npc_id=npc_profile.npc_id,
            states=list(state_set),
            transitions=transitions,
            initial_state=StateMachineState.IDLE.value,
            current_state=StateMachineState.IDLE.value,
            state_history=[(StateMachineState.IDLE.value, _time_module.time())],
        )

        for trans in transitions:
            self._transition_registry[trans.id] = trans

        if len(self._machines) >= self._MAX_MACHINES:
            oldest_key = next(iter(self._machines))
            del self._machines[oldest_key]

        self._machines[machine.id] = machine
        npc_profile.state_machine_id = machine.id
        self._stats["state_machines_designed"] += 1
        return machine

    def add_state_transition(
        self,
        state_machine_id: str,
        from_state: str,
        to_state: str,
        conditions: List[str],
    ) -> Optional[StateTransition]:
        _time_module.sleep(0.001)

        machine = self._machines.get(state_machine_id)
        if machine is None:
            return None

        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            conditions=list(conditions),
        )
        machine.transitions.append(transition)
        self._transition_registry[transition.id] = transition

        if to_state not in machine.states:
            machine.states.append(to_state)

        return transition

    def generate_action_patterns(
        self,
        archetype: BehaviorArchetype,
    ) -> List[ActionPattern]:
        _time_module.sleep(0.001)

        profiles = ARCHETYPE_PROFILES.get(archetype.value, ARCHETYPE_PROFILES[BehaviorArchetype.SOLITARY.value])
        patterns: List[ActionPattern] = []
        aggression = profiles["aggression"]
        courage = profiles["courage"]
        sociability = profiles["sociability"]

        primary_actions: List[Tuple[ActionType, float]] = []

        if aggression > 0.60:
            primary_actions.append((ActionType.ATTACK, aggression * 0.40))
            primary_actions.append((ActionType.DEFEND, aggression * 0.20))
        elif aggression > 0.30:
            primary_actions.append((ActionType.DEFEND, aggression * 0.30))
            primary_actions.append((ActionType.PATROL, 0.25))

        if courage < 0.25:
            primary_actions.append((ActionType.FLEE, (1.0 - courage) * 0.30))
            primary_actions.append((ActionType.HIDE, (1.0 - courage) * 0.25))
        else:
            primary_actions.append((ActionType.PATROL, courage * 0.20))

        if sociability > 0.50:
            primary_actions.append((ActionType.TALK, sociability * 0.30))
            primary_actions.append((ActionType.GATHER, sociability * 0.15))

        primary_actions.append((ActionType.MOVE_TO, 0.20))

        if not primary_actions:
            primary_actions = [(ActionType.IDLE, 1.0)]

        for action_type, weight in primary_actions:
            default = DEFAULT_ACTION_PATTERNS.get(action_type.value, {})
            pattern = ActionPattern(
                name=f"{action_type.value}_{uuid.uuid4().hex[:6]}",
                action_type=action_type.value,
                target_selection=default.get("target_selection", ""),
                duration_ms=default.get("duration_ms", 1000),
                animation=default.get("animation", ""),
                success_rate=default.get("success_rate", 0.80),
                cost=round(default.get("cost", 1.0) * (1.0 + (0.5 - weight)) / 1.5, 2),
            )
            patterns.append(pattern)
            self._patterns[pattern.id] = pattern

        self._stats["action_patterns_generated"] += len(patterns)
        return patterns

    def analyze_behavior_complexity(
        self,
        tree_id: str,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)

        tree = self._trees.get(tree_id)
        if tree is None:
            return {"error": "Tree not found"}

        total_nodes = len(tree.all_nodes)
        depth = self._compute_node_depth(tree)
        branch_factor = self._compute_branch_factor(tree)

        action_count = sum(1 for n in tree.all_nodes if n.node_type == BehaviorNodeType.ACTION)
        condition_count = sum(1 for n in tree.all_nodes if n.node_type == BehaviorNodeType.CONDITION)
        selector_count = sum(1 for n in tree.all_nodes if n.node_type == BehaviorNodeType.SELECTOR)
        sequence_count = sum(1 for n in tree.all_nodes if n.node_type == BehaviorNodeType.SEQUENCE)
        parallel_count = sum(1 for n in tree.all_nodes if n.node_type == BehaviorNodeType.PARALLEL)
        decorator_count = sum(1 for n in tree.all_nodes if n.node_type == BehaviorNodeType.DECORATOR)
        random_count = sum(1 for n in tree.all_nodes if n.node_type == BehaviorNodeType.RANDOM)
        priority_count = sum(1 for n in tree.all_nodes if n.node_type == BehaviorNodeType.PRIORITY)

        max_children = 0
        for node in tree.all_nodes:
            max_children = max(max_children, len(node.children_ids))

        score = (
            total_nodes * 0.15 + depth * 0.25 + max_children * 0.20 +
            action_count * 0.15 + condition_count * 0.10 + parallel_count * 0.15
        )
        score = round(min(10.0, score), 2)
        tree.complexity_score = score

        self._stats["complexity_analyses"] += 1
        return {
            "tree_id": tree.id,
            "total_nodes": total_nodes,
            "max_depth": depth,
            "max_branch_factor": max_children,
            "action_nodes": action_count,
            "condition_nodes": condition_count,
            "selector_nodes": selector_count,
            "sequence_nodes": sequence_count,
            "parallel_nodes": parallel_count,
            "decorator_nodes": decorator_count,
            "random_nodes": random_count,
            "priority_nodes": priority_count,
            "complexity_score": score,
            "archetype": tree.archetype,
        }

    def simulate_behavior_execution(
        self,
        tree_id: str,
        scenario: Dict[str, Any],
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)

        tree = self._trees.get(tree_id)
        if tree is None:
            return {"error": "Tree not found"}

        max_ticks = scenario.get("max_ticks", 30)
        scenario_context = scenario.get("context", {})
        trace: List[Dict[str, Any]] = []
        executed_count = 0
        condition_pass_count = 0
        condition_fail_count = 0

        node_map: Dict[str, BehaviorTreeNode] = {n.id: n for n in tree.all_nodes}
        current_nodes: List[str] = [tree.root_node_id] if tree.root_node_id else []

        for tick in range(max_ticks):
            tick_log: Dict[str, Any] = {"tick": tick, "evaluated": [], "state_changes": []}

            next_nodes: List[str] = []
            for node_id in current_nodes:
                node = node_map.get(node_id)
                if node is None:
                    continue

                if node.node_type == BehaviorNodeType.ACTION:
                    executed_count += 1
                    tick_log["evaluated"].append({
                        "node_id": node.id, "name": node.name,
                        "type": "action", "result": "executed",
                    })
                    next_nodes.extend(node.children_ids)

                elif node.node_type == BehaviorNodeType.CONDITION:
                    expr = node.condition_expression
                    simulated_result = self._evaluate_condition_simulation(
                        expr, scenario_context, tick
                    )
                    if simulated_result:
                        condition_pass_count += 1
                        tick_log["evaluated"].append({
                            "node_id": node.id, "name": node.name,
                            "type": "condition", "result": "passed",
                        })
                        next_nodes.extend(node.children_ids)
                    else:
                        condition_fail_count += 1
                        tick_log["evaluated"].append({
                            "node_id": node.id, "name": node.name,
                            "type": "condition", "result": "failed",
                        })

                elif node.node_type in (BehaviorNodeType.SELECTOR, BehaviorNodeType.SEQUENCE,
                                         BehaviorNodeType.PARALLEL, BehaviorNodeType.RANDOM):
                    children = node.children_ids[:]
                    if node.node_type == BehaviorNodeType.RANDOM and children:
                        random.shuffle(children)
                    next_nodes.extend(children)
                    tick_log["evaluated"].append({
                        "node_id": node.id, "name": node.name,
                        "type": node.node_type.value, "result": "branching",
                        "children_evaluated": len(children),
                    })

                elif node.node_type == BehaviorNodeType.PRIORITY:
                    sorted_children = sorted(
                        [(cid, node_map[cid]) for cid in node.children_ids if cid in node_map],
                        key=lambda x: x[1].priority if x[1] else 0,
                        reverse=True,
                    )
                    next_nodes.extend([cid for cid, _ in sorted_children])
                    tick_log["evaluated"].append({
                        "node_id": node.id, "name": node.name,
                        "type": "priority", "result": "ordered",
                    })

            current_nodes = next_nodes
            trace.append(tick_log)

            if not current_nodes:
                trace.append({"tick": tick + 1, "terminal": True, "message": "All nodes exhausted"})
                break

        self._stats["execution_simulations"] += 1
        return {
            "tree_id": tree.id,
            "tree_description": tree.description,
            "ticks_simulated": len(trace),
            "actions_executed": executed_count,
            "conditions_passed": condition_pass_count,
            "conditions_failed": condition_fail_count,
            "total_nodes_visited": condition_pass_count + condition_fail_count + executed_count,
            "trace": trace,
            "scenario": {k: str(v) for k, v in scenario.items() if k != "context"},
        }

    def optimize_behavior_performance(
        self,
        tree_id: str,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)

        tree = self._trees.get(tree_id)
        if tree is None:
            return {"error": "Tree not found"}

        optimizations: List[Dict[str, Any]] = []
        original_node_count = len(tree.all_nodes)

        unreachable_ids: List[str] = []
        reachable: set = set()
        if tree.root_node_id:
            stack = [tree.root_node_id]
            while stack:
                current = stack.pop()
                if current in reachable:
                    continue
                reachable.add(current)
                for node in tree.all_nodes:
                    if node.id == current:
                        stack.extend(node.children_ids)
                        break

        for node in tree.all_nodes:
            if node.id not in reachable:
                unreachable_ids.append(node.id)
                optimizations.append({
                    "type": "remove_unreachable",
                    "node_id": node.id,
                    "node_name": node.name,
                })

        if unreachable_ids:
            tree.all_nodes = [n for n in tree.all_nodes if n.id not in unreachable_ids]
            for node in tree.all_nodes:
                node.children_ids = [cid for cid in node.children_ids if cid not in unreachable_ids]

        high_cost_actions = [
            n for n in tree.all_nodes
            if n.node_type == BehaviorNodeType.ACTION and len(n.children_ids) == 0
            and n.cooldown_ms < 200
        ]
        for node in high_cost_actions:
            node.cooldown_ms = max(node.cooldown_ms, 200)
            optimizations.append({
                "type": "add_cooldown",
                "node_id": node.id,
                "node_name": node.name,
                "new_cooldown_ms": node.cooldown_ms,
            })

        parallel_nodes = [n for n in tree.all_nodes if n.node_type == BehaviorNodeType.PARALLEL]
        for node in parallel_nodes:
            if len(node.children_ids) > 6:
                node.children_ids = node.children_ids[:6]
                optimizations.append({
                    "type": "limit_parallel_children",
                    "node_id": node.id,
                    "node_name": node.name,
                    "trimmed_from": len(node.children_ids),
                })

        tree.complexity_score = self._compute_tree_complexity(tree)
        tree.execution_stats["optimized"] = True
        tree.execution_stats["original_node_count"] = original_node_count

        self._stats["performance_optimizations"] += 1
        return {
            "tree_id": tree.id,
            "original_node_count": original_node_count,
            "optimized_node_count": len(tree.all_nodes),
            "nodes_removed": original_node_count - len(tree.all_nodes),
            "optimizations_applied": len(optimizations),
            "optimizations": optimizations,
            "final_complexity_score": tree.complexity_score,
        }

    def compose_action_pattern(
        self,
        pattern_type: ActionType,
    ) -> ActionPattern:
        _time_module.sleep(0.001)

        default = DEFAULT_ACTION_PATTERNS.get(pattern_type.value, {
            "target_selection": "nearest", "duration_ms": 1000,
            "animation": "idle", "success_rate": 0.80, "cost": 1.0,
        })

        pattern = ActionPattern(
            name=f"composed_{pattern_type.value}_{uuid.uuid4().hex[:6]}",
            action_type=pattern_type.value,
            target_selection=default.get("target_selection", ""),
            duration_ms=default.get("duration_ms", 1000),
            animation=default.get("animation", ""),
            success_rate=default.get("success_rate", 0.80),
            cost=default.get("cost", 1.0),
        )

        self._patterns[pattern.id] = pattern
        return pattern

    def get_tree(self, tree_id: str) -> Optional[BehaviorTree]:
        _time_module.sleep(0.001)
        return self._trees.get(tree_id)

    def get_machine(self, machine_id: str) -> Optional[StateMachine]:
        _time_module.sleep(0.001)
        return self._machines.get(machine_id)

    def get_profile(self, profile_id: str) -> Optional[NPCBehaviorProfile]:
        _time_module.sleep(0.001)
        return self._profiles.get(profile_id)

    def get_pattern(self, pattern_id: str) -> Optional[ActionPattern]:
        _time_module.sleep(0.001)
        return self._patterns.get(pattern_id)

    def list_trees(self) -> List[BehaviorTree]:
        _time_module.sleep(0.001)
        return list(self._trees.values())

    def list_machines(self) -> List[StateMachine]:
        _time_module.sleep(0.001)
        return list(self._machines.values())

    def list_patterns(self) -> List[ActionPattern]:
        _time_module.sleep(0.001)
        return list(self._patterns.values())

    def list_profiles(self) -> List[NPCBehaviorProfile]:
        _time_module.sleep(0.001)
        return list(self._profiles.values())

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "total_trees": len(self._trees),
            "total_machines": len(self._machines),
            "total_patterns": len(self._patterns),
            "total_profiles": len(self._profiles),
            "total_nodes_registered": len(self._node_registry),
            "total_transitions_registered": len(self._transition_registry),
            "trees_designed": self._stats["trees_designed"],
            "state_machines_designed": self._stats["state_machines_designed"],
            "action_patterns_generated": self._stats["action_patterns_generated"],
            "profiles_created": self._stats["profiles_created"],
            "complexity_analyses": self._stats["complexity_analyses"],
            "execution_simulations": self._stats["execution_simulations"],
            "performance_optimizations": self._stats["performance_optimizations"],
            "average_tree_complexity": round(
                sum(t.complexity_score for t in self._trees.values()) /
                max(1, len(self._trees)), 2
            ),
            "available_archetypes": [a.value for a in BehaviorArchetype],
            "available_node_types": [n.value for n in BehaviorNodeType],
            "available_states": [s.value for s in StateMachineState],
            "available_action_types": [a.value for a in ActionType],
            "available_tree_templates": list(BEHAVIOR_TREE_TEMPLATES.keys()),
            "default_action_pattern_count": len(DEFAULT_ACTION_PATTERNS),
            "max_trees": self._MAX_TREES,
            "max_machines": self._MAX_MACHINES,
            "max_patterns": self._MAX_PATTERNS,
            "max_profiles": self._MAX_PROFILES,
        }

    def _select_tree_templates(
        self,
        archetype: BehaviorArchetype,
    ) -> List[Dict[str, Any]]:
        _time_module.sleep(0.001)

        templates_by_archetype: Dict[BehaviorArchetype, List[str]] = {
            BehaviorArchetype.AGGRESSIVE: ["combat_engagement"],
            BehaviorArchetype.DEFENSIVE: ["guard_post", "combat_engagement"],
            BehaviorArchetype.COWARD: ["flee_and_hide"],
            BehaviorArchetype.CURIOUS: ["social_explorer"],
            BehaviorArchetype.TERRITORIAL: ["guard_post", "combat_engagement"],
            BehaviorArchetype.SOCIAL: ["social_explorer", "merchant_routine"],
            BehaviorArchetype.SOLITARY: ["social_explorer"],
            BehaviorArchetype.GUARDIAN: ["guard_post", "combat_engagement"],
            BehaviorArchetype.PREDATOR: ["combat_engagement"],
            BehaviorArchetype.PREY: ["flee_and_hide"],
        }

        template_keys = templates_by_archetype.get(archetype, ["social_explorer"])
        return [BEHAVIOR_TREE_TEMPLATES[k] for k in template_keys if k in BEHAVIOR_TREE_TEMPLATES]

    def _generate_states_for_archetype(
        self,
        archetype: BehaviorArchetype,
        profile: NPCBehaviorProfile,
    ) -> List[str]:
        _time_module.sleep(0.001)

        states: List[str] = [StateMachineState.IDLE.value]

        if archetype in (BehaviorArchetype.GUARDIAN, BehaviorArchetype.DEFENSIVE,
                          BehaviorArchetype.TERRITORIAL):
            states.append(StateMachineState.GUARD.value)

        if archetype in (BehaviorArchetype.AGGRESSIVE, BehaviorArchetype.PREDATOR,
                          BehaviorArchetype.GUARDIAN, BehaviorArchetype.DEFENSIVE,
                          BehaviorArchetype.TERRITORIAL):
            states.append(StateMachineState.COMBAT.value)
            states.append(StateMachineState.ALERT.value)
            states.append(StateMachineState.SEARCH.value)

        if profile.courage < 0.40 or archetype in (BehaviorArchetype.COWARD, BehaviorArchetype.PREY):
            states.append(StateMachineState.FLEE.value)

        if archetype in (BehaviorArchetype.SOCIAL, BehaviorArchetype.CURIOUS):
            states.append(StateMachineState.DIALOGUE.value)
            states.append(StateMachineState.TRADE.value)

        states.append(StateMachineState.PATROL.value)
        states.append(StateMachineState.REST.value)

        return states

    def _generate_transitions_for_states(
        self,
        states: List[str],
        profile: NPCBehaviorProfile,
    ) -> List[StateTransition]:
        _time_module.sleep(0.001)

        transitions: List[StateTransition] = []
        state_set = set(states)

        if StateMachineState.IDLE.value in state_set and StateMachineState.PATROL.value in state_set:
            transitions.append(StateTransition(
                from_state=StateMachineState.IDLE.value,
                to_state=StateMachineState.PATROL.value,
                conditions=["time_since_startup > 2.0"],
                priority=5,
                trigger_events=["on_spawn", "on_wake"],
            ))

        if StateMachineState.PATROL.value in state_set and StateMachineState.ALERT.value in state_set:
            transitions.append(StateTransition(
                from_state=StateMachineState.PATROL.value,
                to_state=StateMachineState.ALERT.value,
                conditions=["hostile_detected", f"threat_level > {profile.threat_threshold}"],
                priority=8,
                trigger_events=["on_threat_detected", "on_suspicious_sound"],
            ))

        if StateMachineState.ALERT.value in state_set and StateMachineState.COMBAT.value in state_set:
            transitions.append(StateTransition(
                from_state=StateMachineState.ALERT.value,
                to_state=StateMachineState.COMBAT.value,
                conditions=["enemy_in_attack_range", "hostile_confirmed"],
                priority=9,
                trigger_events=["on_enemy_visible", "on_attacked"],
            ))

        if StateMachineState.COMBAT.value in state_set and StateMachineState.FLEE.value in state_set:
            transitions.append(StateTransition(
                from_state=StateMachineState.COMBAT.value,
                to_state=StateMachineState.FLEE.value,
                conditions=["health_below_threshold", "enemy_overwhelming"],
                priority=10,
                cooldown=5.0,
                trigger_events=["on_health_critical", "on_ally_defeated"],
            ))

        if StateMachineState.ALERT.value in state_set and StateMachineState.SEARCH.value in state_set:
            transitions.append(StateTransition(
                from_state=StateMachineState.ALERT.value,
                to_state=StateMachineState.SEARCH.value,
                conditions=["threat_lost", "line_of_sight_broken"],
                priority=6,
                trigger_events=["on_threat_hidden", "on_search_started"],
            ))

        if StateMachineState.SEARCH.value in state_set and StateMachineState.PATROL.value in state_set:
            transitions.append(StateTransition(
                from_state=StateMachineState.SEARCH.value,
                to_state=StateMachineState.PATROL.value,
                conditions=["search_timer_expired", "no_threat_found"],
                priority=3,
                cooldown=10.0,
                trigger_events=["on_search_complete", "on_all_clear"],
            ))

        if StateMachineState.FLEE.value in state_set and StateMachineState.IDLE.value in state_set:
            transitions.append(StateTransition(
                from_state=StateMachineState.FLEE.value,
                to_state=StateMachineState.IDLE.value,
                conditions=["safe_distance_reached", "threat_eliminated"],
                priority=4,
                cooldown=8.0,
                trigger_events=["on_safe_arrival", "on_threat_gone"],
            ))

        if StateMachineState.PATROL.value in state_set and StateMachineState.REST.value in state_set:
            transitions.append(StateTransition(
                from_state=StateMachineState.PATROL.value,
                to_state=StateMachineState.REST.value,
                conditions=["fatigue_above_threshold", "patrol_cycle_complete"],
                priority=2,
                trigger_events=["on_fatigue", "on_patrol_done"],
            ))

        if StateMachineState.REST.value in state_set and StateMachineState.IDLE.value in state_set:
            transitions.append(StateTransition(
                from_state=StateMachineState.REST.value,
                to_state=StateMachineState.IDLE.value,
                conditions=["rest_duration_complete"],
                priority=1,
                trigger_events=["on_rest_complete"],
            ))

        if StateMachineState.GUARD.value in state_set and StateMachineState.ALERT.value in state_set:
            transitions.append(StateTransition(
                from_state=StateMachineState.GUARD.value,
                to_state=StateMachineState.ALERT.value,
                conditions=["intruder_spotted"],
                priority=8,
                trigger_events=["on_intruder_detected"],
            ))

        if StateMachineState.DIALOGUE.value in state_set and StateMachineState.IDLE.value in state_set:
            transitions.append(StateTransition(
                from_state=StateMachineState.DIALOGUE.value,
                to_state=StateMachineState.IDLE.value,
                conditions=["conversation_ended", "interaction_timeout"],
                priority=2,
                trigger_events=["on_dialogue_complete"],
            ))

        return transitions

    def _compute_tree_complexity(self, tree: BehaviorTree) -> float:
        _time_module.sleep(0.001)

        if not tree.all_nodes:
            return 0.0

        total = len(tree.all_nodes)
        depth = self._compute_node_depth(tree)
        branch = self._compute_branch_factor(tree)

        action_ratio = sum(1 for n in tree.all_nodes
                           if n.node_type == BehaviorNodeType.ACTION) / max(total, 1)
        condition_ratio = sum(1 for n in tree.all_nodes
                              if n.node_type == BehaviorNodeType.CONDITION) / max(total, 1)
        parallel_ratio = sum(1 for n in tree.all_nodes
                             if n.node_type == BehaviorNodeType.PARALLEL) / max(total, 1)

        score = (
            total * 0.10 + depth * 0.25 + branch * 0.15 +
            action_ratio * 2.0 + condition_ratio * 1.5 + parallel_ratio * 3.0
        )
        return round(min(10.0, score), 2)

    def _compute_node_depth(self, tree: BehaviorTree) -> int:
        _time_module.sleep(0.001)

        if not tree.root_node_id:
            return 0

        node_map = {n.id: n for n in tree.all_nodes}

        def depth(node_id: str, d: int = 0) -> int:
            node = node_map.get(node_id)
            if node is None or not node.children_ids:
                return d
            return max((depth(cid, d + 1) for cid in node.children_ids), default=d)

        return depth(tree.root_node_id)

    def _compute_branch_factor(self, tree: BehaviorTree) -> float:
        _time_module.sleep(0.001)

        if not tree.all_nodes:
            return 0.0

        child_counts = [len(n.children_ids) for n in tree.all_nodes if n.children_ids]
        if not child_counts:
            return 0.0

        return round(sum(child_counts) / len(child_counts), 2)

    def _evaluate_condition_simulation(
        self,
        expression: str,
        context: Dict[str, Any],
        tick: int,
    ) -> bool:
        _time_module.sleep(0.001)

        if not expression:
            return True

        expression_lower = expression.lower()

        if "distance" in expression_lower or "range" in expression_lower:
            return tick % 3 != 0
        if "threat" in expression_lower:
            return tick % 4 == 0 and tick > 2
        if "health" in expression_lower or "hp" in expression_lower:
            return tick > 5
        if "fatigue" in expression_lower or "rest" in expression_lower:
            return tick % 7 == 0
        if "time" in expression_lower or "timer" in expression_lower:
            return tick % 2 == 0
        if "in_range" in expression_lower or "nearby" in expression_lower:
            return tick % 3 != 1

        return tick % 2 == 0


def get_agent_behavior_designer() -> AgentBehaviorDesigner:
    return AgentBehaviorDesigner.get_instance()