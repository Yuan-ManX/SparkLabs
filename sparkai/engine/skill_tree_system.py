"""
SparkLabs Engine - Skill Tree System

Hierarchical character progression through branching skill trees.
Manages node unlocking, point allocation, prerequisites, synergies,
and specializations with support for multi-class and hybrid builds.

Architecture:
  SkillTreeSystem
    |-- TreeRegistry (per-character-class skill tree definitions)
    |-- NodeUnlocker (prerequisite-aware node activation)
    |-- PointAllocator (skill point economy and distribution)
    |-- SynergyDetector (inter-tree and cross-node synergy bonuses)
    |-- SpecializationTracker (branch depth mastery tracking)

Node Types:
  - ABILITY: unlocks a new active ability
  - PASSIVE: permanent statistical improvement
  - MODIFIER: alters existing ability behavior
  - GATEWAY: prerequisite-only connector node
  - MASTERY: ultimate/capstone node
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class NodeType(Enum):
    ABILITY = "ability"
    PASSIVE = "passive"
    MODIFIER = "modifier"
    GATEWAY = "gateway"
    MASTERY = "mastery"


class NodeState(Enum):
    LOCKED = "locked"
    AVAILABLE = "available"
    UNLOCKED = "unlocked"
    MAXED = "maxed"


@dataclass
class SkillNode:
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    node_type: NodeType = NodeType.PASSIVE
    tier: int = 0
    cost: int = 1
    max_rank: int = 1
    current_rank: int = 0
    state: NodeState = NodeState.LOCKED
    prerequisites: List[str] = field(default_factory=list)
    attribute_modifiers: Dict[str, float] = field(default_factory=dict)
    unlocks_ability: str = ""
    x_position: float = 0.0
    y_position: float = 0.0
    icon_key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "type": self.node_type.value,
            "tier": self.tier,
            "cost": self.cost,
            "rank": f"{self.current_rank}/{self.max_rank}",
            "state": self.state.value,
            "modifiers": self.attribute_modifiers,
        }


@dataclass
class SkillTree:
    tree_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    class_name: str = ""
    description: str = ""
    nodes: Dict[str, SkillNode] = field(default_factory=dict)
    root_node_ids: List[str] = field(default_factory=list)
    max_tier: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tree_id": self.tree_id,
            "name": self.name,
            "class_name": self.class_name,
            "total_nodes": len(self.nodes),
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
        }


@dataclass
class CharacterSkills:
    character_id: str
    available_points: int = 0
    spent_points: int = 0
    unlocked_nodes: Dict[str, int] = field(default_factory=dict)
    active_tree_ids: List[str] = field(default_factory=list)


class SkillTreeSystem:
    _instance: Optional[SkillTreeSystem] = None

    def __init__(self):
        self._trees: Dict[str, SkillTree] = {}
        self._characters: Dict[str, CharacterSkills] = {}
        self._synergy_bonuses: Dict[str, Dict[str, float]] = {}

    @classmethod
    def get_instance(cls) -> SkillTreeSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_tree(self, tree: SkillTree) -> str:
        self._trees[tree.tree_id] = tree
        self._evaluate_availability(tree.tree_id)
        return tree.tree_id

    def _evaluate_availability(self, tree_id: str):
        tree = self._trees.get(tree_id)
        if tree is None:
            return
        for node_id, node in tree.nodes.items():
            if node.current_rank >= node.max_rank:
                node.state = NodeState.MAXED
                continue
            if node.current_rank > 0:
                node.state = NodeState.UNLOCKED
                continue
            prereqs_met = True
            if node.prerequisites:
                for prereq_id in node.prerequisites:
                    prereq = tree.nodes.get(prereq_id)
                    if prereq is None or prereq.current_rank == 0:
                        prereqs_met = False
                        break
            else:
                prereqs_met = node_id in tree.root_node_ids

            if prereqs_met:
                node.state = NodeState.AVAILABLE

    def create_character(self, character_id: str, initial_points: int = 0) -> CharacterSkills:
        char = CharacterSkills(
            character_id=character_id,
            available_points=initial_points,
        )
        self._characters[character_id] = char
        return char

    def add_points(self, character_id: str, points: int) -> int:
        char = self._characters.get(character_id)
        if char is None:
            return 0
        char.available_points += points
        return char.available_points

    def unlock_node(
        self, character_id: str, tree_id: str, node_id: str
    ) -> bool:
        tree = self._trees.get(tree_id)
        if tree is None:
            return False
        char = self._characters.get(character_id)
        if char is None:
            return False

        node = tree.nodes.get(node_id)
        if node is None:
            return False

        if node.state not in (NodeState.AVAILABLE, NodeState.UNLOCKED):
            return False

        if node.current_rank >= node.max_rank:
            return False

        if char.available_points < node.cost:
            return False

        char.available_points -= node.cost
        char.spent_points += node.cost
        node.current_rank += 1

        if tree_id not in char.active_tree_ids:
            char.active_tree_ids.append(tree_id)

        char.unlocked_nodes[node_id] = node.current_rank
        self._evaluate_availability(tree_id)
        return True

    def get_node_state(
        self, character_id: str, tree_id: str, node_id: str
    ) -> Optional[Dict[str, Any]]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return None
        node = tree.nodes.get(node_id)
        if node is None:
            return None
        return {
            "node_id": node_id,
            "state": node.state.value,
            "rank": node.current_rank,
            "max_rank": node.max_rank,
            "cost": node.cost,
            "can_unlock": node.state in (NodeState.AVAILABLE, NodeState.UNLOCKED)
            and node.current_rank < node.max_rank,
        }

    def get_available_nodes(
        self, character_id: str, tree_id: str
    ) -> List[SkillNode]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return []
        return [n for n in tree.nodes.values() if n.state == NodeState.AVAILABLE]

    def get_unlocked_modifiers(self, character_id: str) -> Dict[str, float]:
        char = self._characters.get(character_id)
        if char is None:
            return {}
        modifiers: Dict[str, float] = {}
        for tree_id, tree in self._trees.items():
            for node_id, rank in char.unlocked_nodes.items():
                node = tree.nodes.get(node_id)
                if node:
                    for attr, value in node.attribute_modifiers.items():
                        modifiers[attr] = modifiers.get(attr, 0.0) + value * rank
        return modifiers

    def define_synergy(self, node_a: str, node_b: str, bonus: Dict[str, float]):
        key = f"{node_a}_{node_b}"
        self._synergy_bonuses[key] = bonus

    def get_synergy_bonuses(self, character_id: str) -> Dict[str, float]:
        char = self._characters.get(character_id)
        if char is None:
            return {}
        unlocked = set(char.unlocked_nodes.keys())
        bonuses: Dict[str, float] = {}
        for key, bonus in self._synergy_bonuses.items():
            parts = key.split("_")
            if len(parts) >= 2:
                node_a, node_b = parts[0], "_".join(parts[1:])
                if node_a in unlocked and node_b in unlocked:
                    for attr, value in bonus.items():
                        bonuses[attr] = bonuses.get(attr, 0.0) + value
        return bonuses

    def get_tree_summary(self, tree_id: str) -> Optional[Dict[str, Any]]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return None
        tiers = {}
        for node in tree.nodes.values():
            tier_key = f"tier_{node.tier}"
            if tier_key not in tiers:
                tiers[tier_key] = {"total": 0, "unlocked": 0}
            tiers[tier_key]["total"] += 1
            if node.current_rank > 0:
                tiers[tier_key]["unlocked"] += 1
        return {
            "tree_id": tree_id,
            "name": tree.name,
            "total_nodes": len(tree.nodes),
            "tiers": tiers,
        }

    def get_stats(self) -> Dict[str, Any]:
        total_nodes = sum(len(t.nodes) for t in self._trees.values())
        return {
            "total_trees": len(self._trees),
            "total_nodes": total_nodes,
            "total_characters": len(self._characters),
            "synergies_defined": len(self._synergy_bonuses),
            "trees": {tid: t.name for tid, t in self._trees.items()},
        }


def get_skill_tree_system() -> SkillTreeSystem:
    return SkillTreeSystem.get_instance()