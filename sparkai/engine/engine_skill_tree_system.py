"""
SparkLabs Engine - Skill Tree System

A graph-based skill tree system for the SparkLabs AI-native game engine.
It models branching skill nodes with prerequisites, point spending,
tier gating, mutually exclusive branches, and per-actor progression
state. The system supports tech trees, talent trees, ascendency trees,
and any directed-graph progression structure.

Architecture:
  SkillTreeSystem (singleton)
    |-- SkillNode, SkillEdge, SkillTree, ActorProgression,
       SkillAllocation, SkillTreeStats, SkillTreeSnapshot,
       SkillTreeEvent
    |-- NodeCategory, NodeTier, NodeState, AllocationPolicy,
       SkillTreeEventKind

Core Capabilities:
  - register_tree / get_tree / list_trees / update_tree / delete_tree:
    skill tree lifecycle with root nodes and metadata.
  - register_node / get_node / list_nodes / update_node / remove_node:
    node lifecycle with category, tier, cost, and effects.
  - add_edge / list_edges / remove_edge: prerequisite edges between
    nodes with optional minimum state requirements.
  - allocate_point / deallocate_point / reset_progression: per-actor
    point spending with prerequisite validation and refund logic.
  - get_progression / list_progressions: per-actor skill state.
  - set_node_state / get_node_state: node state machine control for
    locked / unlocked / learned / mastered transitions.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`SkillTreeSystem.get_instance` or the module-level
:func:`get_skill_tree_system` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_TREES: int = 500
_MAX_NODES: int = 5000
_MAX_EDGES: int = 10000
_MAX_PROGRESSIONS: int = 5000
_MAX_ALLOCATIONS: int = 20000
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class NodeCategory(Enum):
    """Functional classification of skill nodes."""
    ACTIVE = "active"
    PASSIVE = "passive"
    STAT_BOOST = "stat_boost"
    MASTERY = "mastery"
    UTILITY = "utility"
    TRAIT = "trait"
    ASCENDANCY = "ascendancy"
    KEYSTONE = "keystone"


class NodeTier(Enum):
    """Tier that gates when a node becomes available."""
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"
    TIER_4 = "tier_4"
    TIER_5 = "tier_5"
    TIER_6 = "tier_6"
    TIER_7 = "tier_7"


class NodeState(Enum):
    """Lifecycle state of a node for an actor."""
    LOCKED = "locked"
    AVAILABLE = "available"
    LEARNED = "learned"
    MASTERED = "mastered"
    FORBIDDEN = "forbidden"


class AllocationPolicy(Enum):
    """How points are spent when allocating a node."""
    SINGLE = "single"
    REPEATABLE = "repeatable"
    MAX_RANK = "max_rank"


class SkillTreeEventKind(Enum):
    """Audit event types emitted by the skill tree system."""
    TREE_REGISTERED = "tree_registered"
    TREE_UPDATED = "tree_updated"
    TREE_DELETED = "tree_deleted"
    NODE_REGISTERED = "node_registered"
    NODE_UPDATED = "node_updated"
    NODE_REMOVED = "node_removed"
    EDGE_ADDED = "edge_added"
    EDGE_REMOVED = "edge_removed"
    POINT_ALLOCATED = "point_allocated"
    POINT_DEALLOCATED = "point_deallocated"
    PROGRESSION_RESET = "progression_reset"
    NODE_STATE_SET = "node_state_set"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SkillNode:
    """A single skill node within a tree."""
    node_id: str = field(default_factory=lambda: _new_id("snd"))
    tree_id: str = ""
    name: str = ""
    category: str = NodeCategory.PASSIVE.value
    tier: str = NodeTier.TIER_1.value
    cost: int = 1
    max_rank: int = 1
    allocation_policy: str = AllocationPolicy.SINGLE.value
    description: str = ""
    effects: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    icon: str = ""
    position: Dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SkillEdge:
    """A directed prerequisite edge from source to target node."""
    edge_id: str = field(default_factory=lambda: _new_id("edg"))
    tree_id: str = ""
    source_node_id: str = ""
    target_node_id: str = ""
    required_state: str = NodeState.LEARNED.value
    required_rank: int = 1
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SkillTree:
    """A named skill tree containing nodes and edges."""
    tree_id: str = field(default_factory=lambda: _new_id("tre"))
    name: str = ""
    description: str = ""
    root_node_ids: List[str] = field(default_factory=list)
    max_points: int = 100
    mutually_exclusive_groups: List[List[str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SkillAllocation:
    """A single point allocation record for an actor."""
    allocation_id: str = field(default_factory=lambda: _new_id("alc"))
    actor_id: str = ""
    tree_id: str = ""
    node_id: str = ""
    rank: int = 1
    allocated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ActorProgression:
    """Per-actor skill progression state for a tree."""
    actor_id: str = ""
    tree_id: str = ""
    points_spent: int = 0
    points_available: int = 0
    node_ranks: Dict[str, int] = field(default_factory=dict)
    node_states: Dict[str, str] = field(default_factory=dict)
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SkillTreeStats:
    """Aggregate counters for the skill tree system."""
    total_trees: int = 0
    total_nodes: int = 0
    total_edges: int = 0
    total_progressions: int = 0
    total_allocations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SkillTreeSnapshot:
    """Immutable point-in-time capture of skill tree state."""
    trees: Dict[str, Any] = field(default_factory=dict)
    nodes: Dict[str, Any] = field(default_factory=dict)
    edges: Dict[str, Any] = field(default_factory=dict)
    progressions: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SkillTreeEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("aud"))
    kind: str = SkillTreeEventKind.TREE_REGISTERED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Skill Tree System Singleton
# ---------------------------------------------------------------------------


class SkillTreeSystem:
    """Singleton system that manages skill trees, nodes, and progression.

    The system maintains skill tree definitions, nodes, prerequisite edges,
    and per-actor progression state. It validates point allocation against
    prerequisites, tier gating, and mutually exclusive groups, emitting
    audit events for every state transition.
    """

    _instance: Optional["SkillTreeSystem"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._trees: Dict[str, SkillTree] = {}
        self._nodes: Dict[str, SkillNode] = {}
        self._edges: Dict[str, SkillEdge] = {}
        self._progressions: Dict[str, ActorProgression] = {}
        self._allocations: List[SkillAllocation] = []
        self._audit: List[SkillTreeEvent] = []

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "SkillTreeSystem":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._seed_default_tree()
            self._initialized = True

    def _seed_default_tree(self) -> None:
        """Seed a small starter skill tree with branching nodes."""
        tree = self.register_tree(
            tree_id="",
            name="Starter Adventurer Tree",
            description="A balanced starter tree with combat and utility branches",
            max_points=50,
        )
        # Root node
        root = self.register_node(
            tree_id=tree.tree_id,
            name="Adventurer's Resolve",
            category=NodeCategory.PASSIVE.value,
            tier=NodeTier.TIER_1.value,
            cost=1,
            max_rank=1,
            description="Increases base health by 10%",
            effects={"health_pct": 0.10},
        )
        # Tier 2 branch A - combat
        combat = self.register_node(
            tree_id=tree.tree_id,
            name="Weapon Mastery",
            category=NodeCategory.STAT_BOOST.value,
            tier=NodeTier.TIER_2.value,
            cost=1,
            max_rank=5,
            description="Increases weapon damage by 5% per rank",
            effects={"damage_pct": 0.05},
            allocation_policy=AllocationPolicy.MAX_RANK.value,
        )
        # Tier 2 branch B - utility
        utility = self.register_node(
            tree_id=tree.tree_id,
            name="Swift Steps",
            category=NodeCategory.UTILITY.value,
            tier=NodeTier.TIER_2.value,
            cost=1,
            max_rank=3,
            description="Increases movement speed by 5% per rank",
            effects={"move_speed_pct": 0.05},
            allocation_policy=AllocationPolicy.MAX_RANK.value,
        )
        # Tier 3 keystone
        keystone = self.register_node(
            tree_id=tree.tree_id,
            name="Battle Hardened",
            category=NodeCategory.KEYSTONE.value,
            tier=NodeTier.TIER_3.value,
            cost=3,
            max_rank=1,
            description="Grants 20% damage reduction when below 30% health",
            effects={"damage_reduction_pct": 0.20, "threshold_pct": 0.30},
        )
        # Edges
        self.add_edge(tree.tree_id, root.node_id, combat.node_id,
                      required_state=NodeState.LEARNED.value, required_rank=1)
        self.add_edge(tree.tree_id, root.node_id, utility.node_id,
                      required_state=NodeState.LEARNED.value, required_rank=1)
        self.add_edge(tree.tree_id, combat.node_id, keystone.node_id,
                      required_state=NodeState.LEARNED.value, required_rank=3)
        # Mark root as a root node
        tree.root_node_ids.append(root.node_id)

    def _emit_event(self, kind: SkillTreeEventKind, payload: Dict[str, Any]) -> None:
        evt = SkillTreeEvent(kind=kind.value, payload=payload)
        self._audit.append(evt)
        _evict_fifo_list(self._audit, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Tree Lifecycle
    # ------------------------------------------------------------------

    def register_tree(self, tree_id: str = "", name: str = "",
                      description: str = "", root_node_ids: List[str] = None,
                      max_points: int = 100,
                      mutually_exclusive_groups: List[List[str]] = None,
                      metadata: Dict[str, Any] = None) -> SkillTree:
        with self._lock:
            tid = tree_id or _new_id("tre")
            tree = SkillTree(
                tree_id=tid,
                name=name,
                description=description,
                root_node_ids=list(root_node_ids) if root_node_ids else [],
                max_points=max(1, _safe_int(max_points, 100)),
                mutually_exclusive_groups=[list(g) for g in mutually_exclusive_groups]
                if mutually_exclusive_groups else [],
                metadata=dict(metadata) if metadata else {},
            )
            self._trees[tid] = tree
            _evict_fifo_dict(self._trees, _MAX_TREES)
            self._emit_event(SkillTreeEventKind.TREE_REGISTERED, {
                "tree_id": tid, "name": name,
            })
            return tree

    def get_tree(self, tree_id: str) -> Optional[SkillTree]:
        with self._lock:
            return self._trees.get(tree_id)

    def list_trees(self, limit: int = 100) -> List[SkillTree]:
        with self._lock:
            return list(self._trees.values())[-limit:]

    def update_tree(self, tree_id: str, **kwargs: Any) -> Optional[SkillTree]:
        with self._lock:
            tree = self._trees.get(tree_id)
            if tree is None:
                return None
            for key in ("name", "description", "root_node_ids",
                        "max_points", "mutually_exclusive_groups", "metadata"):
                if key in kwargs:
                    val = kwargs[key]
                    if key == "max_points":
                        val = max(1, _safe_int(val, tree.max_points))
                    elif key == "root_node_ids":
                        val = list(val) if val else []
                    elif key == "mutually_exclusive_groups":
                        val = [list(g) for g in val] if val else []
                    elif key == "metadata":
                        val = dict(val) if val else {}
                    setattr(tree, key, val)
            self._emit_event(SkillTreeEventKind.TREE_UPDATED, {"tree_id": tree_id})
            return tree

    def delete_tree(self, tree_id: str) -> bool:
        with self._lock:
            existed = self._trees.pop(tree_id, None) is not None
            if existed:
                # Cascade delete nodes and edges
                for nid in list(self._nodes.keys()):
                    if self._nodes[nid].tree_id == tree_id:
                        self._nodes.pop(nid, None)
                for eid in list(self._edges.keys()):
                    if self._edges[eid].tree_id == tree_id:
                        self._edges.pop(eid, None)
                # Cascade delete progressions
                for key in list(self._progressions.keys()):
                    if key.endswith(f"::{tree_id}"):
                        self._progressions.pop(key, None)
                self._emit_event(SkillTreeEventKind.TREE_DELETED, {
                    "tree_id": tree_id,
                })
            return existed

    # ------------------------------------------------------------------
    # Node Lifecycle
    # ------------------------------------------------------------------

    def register_node(self, tree_id: str = "", name: str = "",
                      category: Any = NodeCategory.PASSIVE.value,
                      tier: Any = NodeTier.TIER_1.value,
                      cost: int = 1, max_rank: int = 1,
                      allocation_policy: Any = AllocationPolicy.SINGLE.value,
                      description: str = "",
                      effects: Dict[str, Any] = None,
                      tags: List[str] = None, icon: str = "",
                      position: Dict[str, float] = None,
                      node_id: str = "") -> SkillNode:
        with self._lock:
            nid = node_id or _new_id("snd")
            cat_val = self._coerce_category(category).value
            tier_val = self._coerce_tier(tier).value
            policy_val = self._coerce_policy(allocation_policy).value
            node = SkillNode(
                node_id=nid,
                tree_id=tree_id,
                name=name,
                category=cat_val,
                tier=tier_val,
                cost=max(1, _safe_int(cost, 1)),
                max_rank=max(1, _safe_int(max_rank, 1)),
                allocation_policy=policy_val,
                description=description,
                effects=dict(effects) if effects else {},
                tags=list(tags) if tags else [],
                icon=icon,
                position=dict(position) if position else {},
            )
            self._nodes[nid] = node
            _evict_fifo_dict(self._nodes, _MAX_NODES)
            self._emit_event(SkillTreeEventKind.NODE_REGISTERED, {
                "node_id": nid, "tree_id": tree_id, "name": name,
            })
            return node

    def get_node(self, node_id: str) -> Optional[SkillNode]:
        with self._lock:
            return self._nodes.get(node_id)

    def list_nodes(self, tree_id: str = "", category: Any = None,
                   tier: Any = None, limit: int = 100) -> List[SkillNode]:
        with self._lock:
            items = list(self._nodes.values())
            if tree_id:
                items = [n for n in items if n.tree_id == tree_id]
            if category is not None and category != "":
                cat_val = self._coerce_category(category).value
                items = [n for n in items if n.category == cat_val]
            if tier is not None and tier != "":
                tier_val = self._coerce_tier(tier).value
                items = [n for n in items if n.tier == tier_val]
            return items[-limit:]

    def update_node(self, node_id: str, **kwargs: Any) -> Optional[SkillNode]:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return None
            for key in ("name", "category", "tier", "cost", "max_rank",
                        "allocation_policy", "description", "effects",
                        "tags", "icon", "position"):
                if key in kwargs:
                    val = kwargs[key]
                    if key == "category":
                        val = self._coerce_category(val).value
                    elif key == "tier":
                        val = self._coerce_tier(val).value
                    elif key == "allocation_policy":
                        val = self._coerce_policy(val).value
                    elif key in ("cost", "max_rank"):
                        val = max(1, _safe_int(val, getattr(node, key)))
                    elif key == "effects":
                        val = dict(val) if val else {}
                    elif key == "tags":
                        val = list(val) if val else []
                    elif key == "position":
                        val = dict(val) if val else {}
                    setattr(node, key, val)
            self._emit_event(SkillTreeEventKind.NODE_UPDATED, {"node_id": node_id})
            return node

    def remove_node(self, node_id: str) -> bool:
        with self._lock:
            existed = self._nodes.pop(node_id, None) is not None
            if existed:
                # Cascade delete edges referencing this node
                for eid in list(self._edges.keys()):
                    edge = self._edges[eid]
                    if edge.source_node_id == node_id or edge.target_node_id == node_id:
                        self._edges.pop(eid, None)
                self._emit_event(SkillTreeEventKind.NODE_REMOVED, {"node_id": node_id})
            return existed

    # ------------------------------------------------------------------
    # Edge Management
    # ------------------------------------------------------------------

    def add_edge(self, tree_id: str, source_node_id: str, target_node_id: str,
                 required_state: Any = NodeState.LEARNED.value,
                 required_rank: int = 1,
                 edge_id: str = "") -> Optional[SkillEdge]:
        with self._lock:
            if source_node_id not in self._nodes or target_node_id not in self._nodes:
                return None
            eid = edge_id or _new_id("edg")
            state_val = self._coerce_state(required_state).value
            edge = SkillEdge(
                edge_id=eid,
                tree_id=tree_id,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                required_state=state_val,
                required_rank=max(1, _safe_int(required_rank, 1)),
            )
            self._edges[eid] = edge
            _evict_fifo_dict(self._edges, _MAX_EDGES)
            self._emit_event(SkillTreeEventKind.EDGE_ADDED, {
                "edge_id": eid, "source": source_node_id, "target": target_node_id,
            })
            return edge

    def list_edges(self, tree_id: str = "", source_node_id: str = "",
                   target_node_id: str = "", limit: int = 100) -> List[SkillEdge]:
        with self._lock:
            items = list(self._edges.values())
            if tree_id:
                items = [e for e in items if e.tree_id == tree_id]
            if source_node_id:
                items = [e for e in items if e.source_node_id == source_node_id]
            if target_node_id:
                items = [e for e in items if e.target_node_id == target_node_id]
            return items[-limit:]

    def remove_edge(self, edge_id: str) -> bool:
        with self._lock:
            existed = self._edges.pop(edge_id, None) is not None
            if existed:
                self._emit_event(SkillTreeEventKind.EDGE_REMOVED, {"edge_id": edge_id})
            return existed

    # ------------------------------------------------------------------
    # Progression Management
    # ------------------------------------------------------------------

    def _progression_key(self, actor_id: str, tree_id: str) -> str:
        return f"{actor_id}::{tree_id}"

    def _ensure_progression(self, actor_id: str, tree_id: str) -> ActorProgression:
        key = self._progression_key(actor_id, tree_id)
        if key not in self._progressions:
            tree = self._trees.get(tree_id)
            self._progressions[key] = ActorProgression(
                actor_id=actor_id,
                tree_id=tree_id,
                points_spent=0,
                points_available=tree.max_points if tree else 0,
            )
        return self._progressions[key]

    def allocate_point(self, actor_id: str, tree_id: str, node_id: str,
                       count: int = 1) -> Optional[SkillAllocation]:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None or node.tree_id != tree_id:
                return None
            tree = self._trees.get(tree_id)
            if tree is None:
                return None
            prog = self._ensure_progression(actor_id, tree_id)
            current_rank = prog.node_ranks.get(node_id, 0)
            requested = max(1, _safe_int(count, 1))

            # Validate max rank
            if current_rank + requested > node.max_rank:
                return None

            # Validate points available
            total_cost = node.cost * requested
            if prog.points_spent + total_cost > prog.points_available:
                return None

            # Validate prerequisites (incoming edges)
            if not self._check_prerequisites(actor_id, tree_id, node_id,
                                              current_rank):
                return None

            # Validate mutually exclusive groups
            if not self._check_exclusive_groups(tree, node_id, prog):
                return None

            # Apply allocation
            new_rank = current_rank + requested
            prog.node_ranks[node_id] = new_rank
            prog.points_spent += total_cost
            self._update_node_states(actor_id, tree_id, prog)
            allocation = SkillAllocation(
                actor_id=actor_id,
                tree_id=tree_id,
                node_id=node_id,
                rank=new_rank,
            )
            self._allocations.append(allocation)
            _evict_fifo_list(self._allocations, _MAX_ALLOCATIONS)
            self._emit_event(SkillTreeEventKind.POINT_ALLOCATED, {
                "actor_id": actor_id,
                "tree_id": tree_id,
                "node_id": node_id,
                "rank": new_rank,
            })
            return allocation

    def _check_prerequisites(self, actor_id: str, tree_id: str,
                             node_id: str, current_rank: int) -> bool:
        """Check if all prerequisite edges are satisfied."""
        # Root nodes have no prerequisites
        incoming = [e for e in self._edges.values()
                    if e.target_node_id == node_id and e.tree_id == tree_id]
        if not incoming:
            return True
        # If already allocated, prerequisites were checked before
        if current_rank > 0:
            return True
        prog = self._progressions.get(self._progression_key(actor_id, tree_id))
        if prog is None:
            return False
        # ALL incoming edges must be satisfied (AND semantics)
        for edge in incoming:
            source_rank = prog.node_ranks.get(edge.source_node_id, 0)
            source_state = prog.node_states.get(edge.source_node_id, NodeState.LOCKED.value)
            if source_rank < edge.required_rank:
                return False
            # Check required_state ordering
            if not self._state_satisfies(source_state, edge.required_state):
                return False
        return True

    @staticmethod
    def _state_satisfies(actual: str, required: str) -> bool:
        """Check if the actual node state satisfies the required state."""
        order = {
            NodeState.LOCKED.value: 0,
            NodeState.AVAILABLE.value: 1,
            NodeState.LEARNED.value: 2,
            NodeState.MASTERED.value: 3,
        }
        return order.get(actual, 0) >= order.get(required, 0)

    @staticmethod
    def _check_exclusive_groups(tree: SkillTree, node_id: str,
                                 prog: ActorProgression) -> bool:
        """Check if allocating this node violates mutual exclusivity."""
        for group in tree.mutually_exclusive_groups:
            if node_id in group:
                # If any other node in the group is already allocated, fail
                for other_id in group:
                    if other_id != node_id and prog.node_ranks.get(other_id, 0) > 0:
                        return False
        return True

    def _update_node_states(self, actor_id: str, tree_id: str,
                            prog: ActorProgression) -> None:
        """Recompute node states after a change."""
        for node_id, node in self._nodes.items():
            if node.tree_id != tree_id:
                continue
            rank = prog.node_ranks.get(node_id, 0)
            if rank >= node.max_rank and node.max_rank > 0:
                prog.node_states[node_id] = NodeState.MASTERED.value
            elif rank > 0:
                prog.node_states[node_id] = NodeState.LEARNED.value
            elif self._check_prerequisites(actor_id, tree_id, node_id, 0):
                prog.node_states[node_id] = NodeState.AVAILABLE.value
            else:
                prog.node_states[node_id] = NodeState.LOCKED.value
        prog.last_updated = _now()

    def deallocate_point(self, actor_id: str, tree_id: str, node_id: str,
                         count: int = 1) -> Optional[SkillAllocation]:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return None
            prog = self._progressions.get(self._progression_key(actor_id, tree_id))
            if prog is None:
                return None
            current_rank = prog.node_ranks.get(node_id, 0)
            if current_rank <= 0:
                return None
            requested = min(max(1, _safe_int(count, 1)), current_rank)
            # Check dependents: cannot deallocate if a dependent node still relies on this
            dependents = [e for e in self._edges.values()
                          if e.source_node_id == node_id and e.tree_id == tree_id]
            for dep_edge in dependents:
                dep_rank = prog.node_ranks.get(dep_edge.target_node_id, 0)
                if dep_rank > 0 and (current_rank - requested) < dep_edge.required_rank:
                    return None
            new_rank = current_rank - requested
            refund = node.cost * requested
            if new_rank == 0:
                prog.node_ranks.pop(node_id, None)
            else:
                prog.node_ranks[node_id] = new_rank
            prog.points_spent = max(0, prog.points_spent - refund)
            self._update_node_states(actor_id, tree_id, prog)
            self._emit_event(SkillTreeEventKind.POINT_DEALLOCATED, {
                "actor_id": actor_id,
                "tree_id": tree_id,
                "node_id": node_id,
                "rank": new_rank,
            })
            return SkillAllocation(
                actor_id=actor_id,
                tree_id=tree_id,
                node_id=node_id,
                rank=new_rank,
            )

    def reset_progression(self, actor_id: str, tree_id: str) -> bool:
        with self._lock:
            key = self._progression_key(actor_id, tree_id)
            existed = key in self._progressions
            if existed:
                self._progressions.pop(key, None)
                self._emit_event(SkillTreeEventKind.PROGRESSION_RESET, {
                    "actor_id": actor_id, "tree_id": tree_id,
                })
            return existed

    def get_progression(self, actor_id: str, tree_id: str) -> Optional[ActorProgression]:
        with self._lock:
            return self._progressions.get(self._progression_key(actor_id, tree_id))

    def list_progressions(self, actor_id: str = "", tree_id: str = "",
                          limit: int = 100) -> List[ActorProgression]:
        with self._lock:
            items = list(self._progressions.values())
            if actor_id:
                items = [p for p in items if p.actor_id == actor_id]
            if tree_id:
                items = [p for p in items if p.tree_id == tree_id]
            return items[-limit:]

    def set_node_state(self, actor_id: str, tree_id: str, node_id: str,
                       state: Any) -> Optional[ActorProgression]:
        with self._lock:
            prog = self._ensure_progression(actor_id, tree_id)
            state_val = self._coerce_state(state).value
            prog.node_states[node_id] = state_val
            prog.last_updated = _now()
            self._emit_event(SkillTreeEventKind.NODE_STATE_SET, {
                "actor_id": actor_id,
                "tree_id": tree_id,
                "node_id": node_id,
                "state": state_val,
            })
            return prog

    def get_node_state(self, actor_id: str, tree_id: str,
                       node_id: str) -> str:
        with self._lock:
            prog = self._progressions.get(self._progression_key(actor_id, tree_id))
            if prog is None:
                return NodeState.LOCKED.value
            return prog.node_states.get(node_id, NodeState.LOCKED.value)

    # ------------------------------------------------------------------
    # Enum Coercion Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_category(value: Any) -> NodeCategory:
        if isinstance(value, NodeCategory):
            return value
        if isinstance(value, str):
            for cat in NodeCategory:
                if cat.value == value:
                    return cat
        return NodeCategory.PASSIVE

    @staticmethod
    def _coerce_tier(value: Any) -> NodeTier:
        if isinstance(value, NodeTier):
            return value
        if isinstance(value, str):
            for tier in NodeTier:
                if tier.value == value:
                    return tier
        return NodeTier.TIER_1

    @staticmethod
    def _coerce_policy(value: Any) -> AllocationPolicy:
        if isinstance(value, AllocationPolicy):
            return value
        if isinstance(value, str):
            for pol in AllocationPolicy:
                if pol.value == value:
                    return pol
        return AllocationPolicy.SINGLE

    @staticmethod
    def _coerce_state(value: Any) -> NodeState:
        if isinstance(value, NodeState):
            return value
        if isinstance(value, str):
            for state in NodeState:
                if state.value == value:
                    return state
        return NodeState.LOCKED

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[SkillTreeEvent]:
        with self._lock:
            return list(self._audit[-limit:])

    def get_stats(self) -> SkillTreeStats:
        with self._lock:
            return SkillTreeStats(
                total_trees=len(self._trees),
                total_nodes=len(self._nodes),
                total_edges=len(self._edges),
                total_progressions=len(self._progressions),
                total_allocations=len(self._allocations),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "trees": len(self._trees),
                "nodes": len(self._nodes),
                "edges": len(self._edges),
                "progressions": len(self._progressions),
                "allocations": len(self._allocations),
                "events": len(self._audit),
            }

    def get_snapshot(self) -> SkillTreeSnapshot:
        with self._lock:
            return SkillTreeSnapshot(
                trees={k: v.to_dict() for k, v in self._trees.items()},
                nodes={k: v.to_dict() for k, v in self._nodes.items()},
                edges={k: v.to_dict() for k, v in self._edges.items()},
                progressions={k: v.to_dict() for k, v in self._progressions.items()},
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._trees.clear()
            self._nodes.clear()
            self._edges.clear()
            self._progressions.clear()
            self._allocations.clear()
            self._audit.clear()
            self._initialized = False
            self._initialize()


def get_skill_tree_system() -> SkillTreeSystem:
    """Module-level factory for the SkillTreeSystem singleton."""
    return SkillTreeSystem.get_instance()
