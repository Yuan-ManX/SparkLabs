"""
SparkLabs Agent - Decision Graph Engine

Graph-based decision-making engine that enables agents to navigate complex
decision spaces through structured decision graphs. Supports multi-branch
evaluation, probabilistic path selection, and runtime graph optimization.

Architecture:
  DecisionGraphEngine (Singleton)
    |-- DecisionNode (atomic decision point with conditions)
    |-- DecisionEdge (weighted transition between nodes)
    |-- DecisionGraph (complete decision structure)
    |-- PathEvaluator (evaluates and scores decision paths)
    |-- GraphOptimizer (prunes and optimizes decision graphs)

Decision Node Types:
  - CONDITION: branch based on condition evaluation
  - ACTION: execute a specific action
  - SEQUENCE: ordered sequence of child decisions
  - PARALLEL: concurrent decision branches
  - SELECTOR: try children until one succeeds
  - FALLBACK: primary with fallback options

Usage:
    dg = DecisionGraphEngine.get_instance()
    dg.initialize()

    graph = dg.create_graph("combat_decision", DecisionNodeType.SELECTOR)
    dg.add_node(graph.graph_id, DecisionNode(
        node_id="attack_check",
        node_type=DecisionNodeType.CONDITION,
        condition="target_in_range",
    ))
    result = dg.evaluate(graph.graph_id, world_state)
    dg.shutdown()
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# =============================================================================
# Enums
# =============================================================================


class DecisionNodeType(Enum):
    """Types of decision nodes in the graph."""
    CONDITION = "condition"      # Evaluate a condition, branch on result
    ACTION = "action"            # Execute a concrete action
    SEQUENCE = "sequence"        # Execute children in order
    PARALLEL = "parallel"        # Execute children concurrently
    SELECTOR = "selector"        # Try children until one succeeds
    FALLBACK = "fallback"         # Primary with fallback alternatives
    LOOP = "loop"                # Repeat a sub-graph
    RANDOM = "random"            # Probabilistic selection
    PRIORITY = "priority"        # Highest priority child first
    DEFERRED = "deferred"        # Delayed decision evaluation


class DecisionStatus(Enum):
    """Status of a decision node evaluation."""
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"
    PENDING = "pending"
    TIMEOUT = "timeout"
    INTERRUPTED = "interrupted"


class GraphOptimizationStrategy(Enum):
    """Strategies for optimizing decision graphs."""
    PRUNE_UNREACHABLE = "prune_unreachable"
    MERGE_EQUIVALENT = "merge_equivalent"
    REORDER_PRIORITIES = "reorder_priorities"
    SHORTCUT_PATHS = "shortcut_paths"
    CACHE_SUBGRAPHS = "cache_subgraphs"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class DecisionNode:
    """A single node in a decision graph."""
    node_id: str
    node_type: DecisionNodeType
    name: str = ""
    description: str = ""
    condition: Optional[str] = None
    action: Optional[str] = None
    action_params: Dict[str, Any] = field(default_factory=dict)
    child_ids: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    probability: float = 1.0
    priority: int = 0
    max_retries: int = 1
    timeout_ms: float = 5000.0
    loop_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "description": self.description,
            "condition": self.condition,
            "action": self.action,
            "action_params": self.action_params,
            "child_ids": self.child_ids,
            "parent_id": self.parent_id,
            "probability": self.probability,
            "priority": self.priority,
            "max_retries": self.max_retries,
            "timeout_ms": self.timeout_ms,
            "loop_count": self.loop_count,
            "metadata": self.metadata,
        }


@dataclass
class DecisionEdge:
    """A weighted edge between two decision nodes."""
    edge_id: str
    source_id: str
    target_id: str
    weight: float = 1.0
    condition: Optional[str] = None
    label: str = ""
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "weight": self.weight,
            "condition": self.condition,
            "label": self.label,
            "priority": self.priority,
        }


@dataclass
class DecisionGraph:
    """A complete decision graph structure."""
    graph_id: str
    name: str
    root_node_id: str
    description: str = ""
    nodes: Dict[str, DecisionNode] = field(default_factory=dict)
    edges: Dict[str, DecisionEdge] = field(default_factory=dict)
    node_count: int = 0
    edge_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "root_node_id": self.root_node_id,
            "description": self.description,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges.values()],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


@dataclass
class DecisionPath:
    """A traced path through the decision graph."""
    path_id: str
    graph_id: str
    node_ids: List[str]
    visited_nodes: List[str]
    decisions: List[Dict[str, Any]]
    status: DecisionStatus = DecisionStatus.PENDING
    score: float = 0.0
    duration_ms: float = 0.0
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "graph_id": self.graph_id,
            "node_ids": self.node_ids,
            "visited_nodes": self.visited_nodes,
            "decisions": self.decisions,
            "status": self.status.value,
            "score": self.score,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class EvaluationContext:
    """Context for graph evaluation."""
    context_id: str
    agent_id: str
    world_state: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    blackboard: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    max_depth: int = 50
    current_depth: int = 0
    timeout_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)


# =============================================================================
# Decision Graph Engine
# =============================================================================


class DecisionGraphEngine:
    """
    Graph-based decision engine for AI game agents.
    Enables structured decision-making through graph traversal and evaluation.
    """

    _instance: Optional["DecisionGraphEngine"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if DecisionGraphEngine._instance is not None:
            raise RuntimeError("Use DecisionGraphEngine.get_instance()")
        self._initialized: bool = False
        self._graphs: Dict[str, DecisionGraph] = {}
        self._paths: Dict[str, DecisionPath] = {}
        self._path_history: List[DecisionPath] = []
        self._condition_evaluators: Dict[str, Callable] = {}
        self._action_executors: Dict[str, Callable] = {}
        self._node_evaluators: Dict[DecisionNodeType, Callable] = {}
        self._stats: Dict[str, Any] = {
            "total_evaluations": 0,
            "successful_evaluations": 0,
            "failed_evaluations": 0,
            "total_paths_traced": 0,
            "avg_path_length": 0.0,
            "avg_duration_ms": 0.0,
        }
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "DecisionGraphEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the decision graph engine with default evaluators."""
        with self._lock:
            if self._initialized:
                return
            self._node_evaluators[DecisionNodeType.CONDITION] = self._evaluate_condition_node
            self._node_evaluators[DecisionNodeType.ACTION] = self._evaluate_action_node
            self._node_evaluators[DecisionNodeType.SEQUENCE] = self._evaluate_sequence_node
            self._node_evaluators[DecisionNodeType.PARALLEL] = self._evaluate_parallel_node
            self._node_evaluators[DecisionNodeType.SELECTOR] = self._evaluate_selector_node
            self._node_evaluators[DecisionNodeType.FALLBACK] = self._evaluate_fallback_node
            self._node_evaluators[DecisionNodeType.LOOP] = self._evaluate_loop_node
            self._node_evaluators[DecisionNodeType.RANDOM] = self._evaluate_random_node
            self._node_evaluators[DecisionNodeType.PRIORITY] = self._evaluate_priority_node
            self._node_evaluators[DecisionNodeType.DEFERRED] = self._evaluate_deferred_node

            # Register default condition evaluators
            self._condition_evaluators["always_true"] = lambda ctx: True
            self._condition_evaluators["always_false"] = lambda ctx: False
            self._condition_evaluators["random_chance"] = lambda ctx: random.random() < 0.5
            self._condition_evaluators["has_target"] = lambda ctx: bool(ctx.world_state.get("target"))
            self._initialized = True

    def create_graph(self, name: str, root_type: DecisionNodeType = DecisionNodeType.SELECTOR,
                     description: str = "") -> DecisionGraph:
        """Create a new decision graph."""
        with self._lock:
            graph_id = uuid.uuid4().hex[:12]
            root_node = DecisionNode(
                node_id="root",
                node_type=root_type,
                name="Root",
                description=f"Root node for {name}",
            )
            graph = DecisionGraph(
                graph_id=graph_id,
                name=name,
                root_node_id="root",
                description=description,
                nodes={"root": root_node},
                node_count=1,
            )
            self._graphs[graph_id] = graph
            return graph

    def add_node(self, graph_id: str, node: DecisionNode) -> Optional[DecisionNode]:
        """Add a node to a decision graph."""
        with self._lock:
            graph = self._graphs.get(graph_id)
            if not graph:
                return None
            if node.node_id in graph.nodes:
                return None
            graph.nodes[node.node_id] = node
            graph.node_count = len(graph.nodes)
            graph.updated_at = time.time()
            return node

    def add_edge(self, graph_id: str, source_id: str, target_id: str,
                 weight: float = 1.0, condition: Optional[str] = None,
                 label: str = "") -> Optional[DecisionEdge]:
        """Add an edge between two nodes in a graph."""
        with self._lock:
            graph = self._graphs.get(graph_id)
            if not graph:
                return None
            if source_id not in graph.nodes or target_id not in graph.nodes:
                return None
            edge_id = uuid.uuid4().hex[:12]
            edge = DecisionEdge(
                edge_id=edge_id,
                source_id=source_id,
                target_id=target_id,
                weight=weight,
                condition=condition,
                label=label,
            )
            graph.edges[edge_id] = edge
            graph.edge_count = len(graph.edges)
            graph.updated_at = time.time()
            return edge

    def add_child(self, graph_id: str, parent_id: str,
                  child_type: DecisionNodeType, name: str = "",
                  condition: Optional[str] = None, action: Optional[str] = None,
                  **kwargs: Any) -> Optional[DecisionNode]:
        """Add a child node to a parent node."""
        with self._lock:
            graph = self._graphs.get(graph_id)
            if not graph:
                return None
            if parent_id not in graph.nodes:
                return None
            child_id = uuid.uuid4().hex[:12]
            child = DecisionNode(
                node_id=child_id,
                node_type=child_type,
                name=name,
                condition=condition,
                action=action,
                parent_id=parent_id,
                **kwargs,
            )
            graph.nodes[child_id] = child
            graph.nodes[parent_id].child_ids.append(child_id)
            graph.node_count = len(graph.nodes)
            graph.updated_at = time.time()
            return child

    def evaluate(self, graph_id: str, world_state: Dict[str, Any],
                 agent_id: str = "default", variables: Optional[Dict[str, Any]] = None,
                 max_depth: int = 50, timeout_ms: float = 30000.0) -> DecisionPath:
        """Evaluate a decision graph from its root node."""
        with self._lock:
            graph = self._graphs.get(graph_id)
            if not graph:
                return DecisionPath(
                    path_id=uuid.uuid4().hex[:12],
                    graph_id=graph_id,
                    node_ids=[],
                    visited_nodes=[],
                    decisions=[],
                    status=DecisionStatus.FAILURE,
                )

            path_id = uuid.uuid4().hex[:12]
            path = DecisionPath(
                path_id=path_id,
                graph_id=graph_id,
                node_ids=[],
                visited_nodes=[],
                decisions=[],
            )

            ctx = EvaluationContext(
                context_id=uuid.uuid4().hex[:12],
                agent_id=agent_id,
                world_state=world_state,
                variables=variables or {},
                max_depth=max_depth,
                timeout_at=time.time() + timeout_ms / 1000.0,
            )

            start_time = time.time()
            root = graph.nodes.get(graph.root_node_id)
            if root:
                self._traverse_node(graph, root, ctx, path)

            path.duration_ms = (time.time() - start_time) * 1000.0
            path.completed_at = time.time()
            self._paths[path_id] = path
            self._path_history.append(path)

            # Update stats
            self._stats["total_evaluations"] += 1
            if path.status == DecisionStatus.SUCCESS:
                self._stats["successful_evaluations"] += 1
            else:
                self._stats["failed_evaluations"] += 1
            self._stats["total_paths_traced"] += 1
            total_paths = self._stats["total_paths_traced"]
            self._stats["avg_path_length"] = (
                (self._stats["avg_path_length"] * (total_paths - 1) + len(path.visited_nodes)) / total_paths
            )
            self._stats["avg_duration_ms"] = (
                (self._stats["avg_duration_ms"] * (total_paths - 1) + path.duration_ms) / total_paths
            )

            return path

    def _traverse_node(self, graph: DecisionGraph, node: DecisionNode,
                       ctx: EvaluationContext, path: DecisionPath) -> DecisionStatus:
        """Traverse and evaluate a single node."""
        if ctx.current_depth >= ctx.max_depth:
            return DecisionStatus.FAILURE
        if ctx.timeout_at and time.time() > ctx.timeout_at:
            return DecisionStatus.TIMEOUT

        path.visited_nodes.append(node.node_id)
        ctx.current_depth += 1

        evaluator = self._node_evaluators.get(node.node_type)
        if evaluator:
            status = evaluator(graph, node, ctx, path)
        else:
            status = DecisionStatus.FAILURE

        path.node_ids.append(node.node_id)
        path.decisions.append({
            "node_id": node.node_id,
            "node_type": node.node_type.value,
            "name": node.name,
            "status": status.value,
            "depth": ctx.current_depth,
        })

        return status

    def _evaluate_condition_node(self, graph: DecisionGraph, node: DecisionNode,
                                  ctx: EvaluationContext, path: DecisionPath) -> DecisionStatus:
        """Evaluate a condition node."""
        condition_name = node.condition or "always_true"
        evaluator = self._condition_evaluators.get(condition_name)
        if evaluator is None:
            return DecisionStatus.FAILURE

        result = evaluator(ctx)
        if result:
            # Follow children on success
            for child_id in node.child_ids:
                child = graph.nodes.get(child_id)
                if child:
                    status = self._traverse_node(graph, child, ctx, path)
                    if status == DecisionStatus.SUCCESS:
                        return DecisionStatus.SUCCESS
            return DecisionStatus.SUCCESS
        return DecisionStatus.FAILURE

    def _evaluate_action_node(self, graph: DecisionGraph, node: DecisionNode,
                               ctx: EvaluationContext, path: DecisionPath) -> DecisionStatus:
        """Evaluate an action node."""
        action_name = node.action or "noop"
        executor = self._action_executors.get(action_name)
        if executor:
            try:
                result = executor(ctx, node.action_params)
                if result:
                    path.score += 1.0
                    return DecisionStatus.SUCCESS
            except Exception:
                pass
            return DecisionStatus.FAILURE
        return DecisionStatus.SUCCESS

    def _evaluate_sequence_node(self, graph: DecisionGraph, node: DecisionNode,
                                 ctx: EvaluationContext, path: DecisionPath) -> DecisionStatus:
        """Evaluate children in sequence."""
        for child_id in node.child_ids:
            child = graph.nodes.get(child_id)
            if child:
                status = self._traverse_node(graph, child, ctx, path)
                if status != DecisionStatus.SUCCESS:
                    return status
        return DecisionStatus.SUCCESS

    def _evaluate_parallel_node(self, graph: DecisionGraph, node: DecisionNode,
                                 ctx: EvaluationContext, path: DecisionPath) -> DecisionStatus:
        """Evaluate children in parallel (simulated)."""
        success_count = 0
        for child_id in node.child_ids:
            child = graph.nodes.get(child_id)
            if child:
                status = self._traverse_node(graph, child, ctx, path)
                if status == DecisionStatus.SUCCESS:
                    success_count += 1
        return DecisionStatus.SUCCESS if success_count > 0 else DecisionStatus.FAILURE

    def _evaluate_selector_node(self, graph: DecisionGraph, node: DecisionNode,
                                 ctx: EvaluationContext, path: DecisionPath) -> DecisionStatus:
        """Evaluate children until one succeeds."""
        for child_id in node.child_ids:
            child = graph.nodes.get(child_id)
            if child:
                status = self._traverse_node(graph, child, ctx, path)
                if status == DecisionStatus.SUCCESS:
                    return DecisionStatus.SUCCESS
        return DecisionStatus.FAILURE

    def _evaluate_fallback_node(self, graph: DecisionGraph, node: DecisionNode,
                                 ctx: EvaluationContext, path: DecisionPath) -> DecisionStatus:
        """Evaluate primary then fallback children."""
        if not node.child_ids:
            return DecisionStatus.FAILURE
        primary = graph.nodes.get(node.child_ids[0])
        if primary:
            status = self._traverse_node(graph, primary, ctx, path)
            if status == DecisionStatus.SUCCESS:
                return DecisionStatus.SUCCESS
        for child_id in node.child_ids[1:]:
            child = graph.nodes.get(child_id)
            if child:
                status = self._traverse_node(graph, child, ctx, path)
                if status == DecisionStatus.SUCCESS:
                    return DecisionStatus.SUCCESS
        return DecisionStatus.FAILURE

    def _evaluate_loop_node(self, graph: DecisionGraph, node: DecisionNode,
                             ctx: EvaluationContext, path: DecisionPath) -> DecisionStatus:
        """Evaluate a sub-graph in a loop."""
        for i in range(node.loop_count):
            for child_id in node.child_ids:
                child = graph.nodes.get(child_id)
                if child:
                    status = self._traverse_node(graph, child, ctx, path)
                    if status == DecisionStatus.FAILURE:
                        return DecisionStatus.FAILURE
        return DecisionStatus.SUCCESS

    def _evaluate_random_node(self, graph: DecisionGraph, node: DecisionNode,
                               ctx: EvaluationContext, path: DecisionPath) -> DecisionStatus:
        """Probabilistically select a child based on weights."""
        if not node.child_ids:
            return DecisionStatus.FAILURE
        weights = []
        for child_id in node.child_ids:
            child = graph.nodes.get(child_id)
            weights.append(child.probability if child else 0.0)
        total = sum(weights) or 1.0
        weights = [w / total for w in weights]
        selected = random.choices(node.child_ids, weights=weights, k=1)[0]
        child = graph.nodes.get(selected)
        if child:
            return self._traverse_node(graph, child, ctx, path)
        return DecisionStatus.FAILURE

    def _evaluate_priority_node(self, graph: DecisionGraph, node: DecisionNode,
                                 ctx: EvaluationContext, path: DecisionPath) -> DecisionStatus:
        """Evaluate children by priority order."""
        sorted_children = sorted(
            node.child_ids,
            key=lambda cid: graph.nodes.get(cid, DecisionNode(node_id="", node_type=DecisionNodeType.CONDITION)).priority,
            reverse=True,
        )
        for child_id in sorted_children:
            child = graph.nodes.get(child_id)
            if child:
                status = self._traverse_node(graph, child, ctx, path)
                if status == DecisionStatus.SUCCESS:
                    return DecisionStatus.SUCCESS
        return DecisionStatus.FAILURE

    def _evaluate_deferred_node(self, graph: DecisionGraph, node: DecisionNode,
                                 ctx: EvaluationContext, path: DecisionPath) -> DecisionStatus:
        """Deferred evaluation - stored for later execution."""
        ctx.blackboard[f"deferred_{node.node_id}"] = {
            "node": node,
            "context": ctx,
            "timestamp": time.time(),
        }
        return DecisionStatus.PENDING

    def register_condition(self, name: str, evaluator: Callable[[EvaluationContext], bool]) -> None:
        """Register a custom condition evaluator."""
        with self._lock:
            self._condition_evaluators[name] = evaluator

    def register_action(self, name: str, executor: Callable[[EvaluationContext, Dict[str, Any]], bool]) -> None:
        """Register a custom action executor."""
        with self._lock:
            self._action_executors[name] = executor

    def optimize_graph(self, graph_id: str,
                       strategy: GraphOptimizationStrategy = GraphOptimizationStrategy.PRUNE_UNREACHABLE) -> Dict[str, Any]:
        """Optimize a decision graph using the specified strategy."""
        with self._lock:
            graph = self._graphs.get(graph_id)
            if not graph:
                return {"error": "Graph not found", "success": False}

            result = {"success": True, "strategy": strategy.value, "changes": []}

            if strategy == GraphOptimizationStrategy.PRUNE_UNREACHABLE:
                reachable = self._find_reachable_nodes(graph)
                pruned = []
                for node_id in list(graph.nodes.keys()):
                    if node_id not in reachable and node_id != graph.root_node_id:
                        del graph.nodes[node_id]
                        pruned.append(node_id)
                graph.node_count = len(graph.nodes)
                result["changes"] = [f"Pruned {len(pruned)} unreachable nodes"]

            elif strategy == GraphOptimizationStrategy.MERGE_EQUIVALENT:
                merged = self._merge_equivalent_nodes(graph)
                result["changes"] = [f"Merged {merged} equivalent node pairs"]

            elif strategy == GraphOptimizationStrategy.REORDER_PRIORITIES:
                # Sort children by evaluation frequency
                for node in graph.nodes.values():
                    if node.node_type in (DecisionNodeType.PRIORITY, DecisionNodeType.SELECTOR):
                        node.child_ids.sort(
                            key=lambda cid: graph.nodes.get(cid, DecisionNode(
                                node_id="", node_type=DecisionNodeType.CONDITION
                            )).priority,
                            reverse=True,
                        )
                result["changes"] = ["Reordered child priorities"]

            graph.updated_at = time.time()
            return result

    def _find_reachable_nodes(self, graph: DecisionGraph) -> Set[str]:
        """Find all nodes reachable from the root."""
        reachable: Set[str] = set()
        stack = [graph.root_node_id]
        while stack:
            node_id = stack.pop()
            if node_id in reachable:
                continue
            reachable.add(node_id)
            node = graph.nodes.get(node_id)
            if node:
                stack.extend(node.child_ids)
        return reachable

    def _merge_equivalent_nodes(self, graph: DecisionGraph) -> int:
        """Merge nodes with equivalent structure."""
        merged = 0
        nodes = list(graph.nodes.values())
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                a, b = nodes[i], nodes[j]
                if (a.node_type == b.node_type and
                        a.condition == b.condition and
                        a.action == b.action and
                        a.child_ids == b.child_ids):
                    # Redirect edges to a, remove b
                    for edge in list(graph.edges.values()):
                        if edge.target_id == b.node_id:
                            edge.target_id = a.node_id
                    del graph.nodes[b.node_id]
                    merged += 1
        graph.node_count = len(graph.nodes)
        return merged

    def get_graph(self, graph_id: str) -> Optional[DecisionGraph]:
        """Get a decision graph by ID."""
        return self._graphs.get(graph_id)

    def list_graphs(self) -> List[DecisionGraph]:
        """List all decision graphs."""
        return list(self._graphs.values())

    def get_path(self, path_id: str) -> Optional[DecisionPath]:
        """Get a decision path by ID."""
        return self._paths.get(path_id)

    def list_paths(self, graph_id: Optional[str] = None,
                   limit: int = 50) -> List[DecisionPath]:
        """List decision paths, optionally filtered by graph."""
        paths = list(self._paths.values()) + self._path_history
        if graph_id:
            paths = [p for p in paths if p.graph_id == graph_id]
        paths.sort(key=lambda p: p.started_at, reverse=True)
        return paths[:limit]

    def get_status(self) -> Dict[str, Any]:
        """Get engine status and statistics."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "graph_count": len(self._graphs),
                "path_count": len(self._paths),
                "path_history_count": len(self._path_history),
                "condition_evaluators": list(self._condition_evaluators.keys()),
                "action_executors": list(self._action_executors.keys()),
                "stats": self._stats,
            }

    def delete_graph(self, graph_id: str) -> bool:
        """Delete a decision graph."""
        with self._lock:
            if graph_id in self._graphs:
                del self._graphs[graph_id]
                return True
            return False

    def shutdown(self) -> None:
        """Shutdown the decision graph engine."""
        with self._lock:
            self._graphs.clear()
            self._paths.clear()
            self._path_history.clear()
            self._condition_evaluators.clear()
            self._action_executors.clear()
            self._initialized = False


# =============================================================================
# Predefined Decision Graph Templates
# =============================================================================

_DECISION_GRAPH_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "combat": {
        "name": "Combat Decision Tree",
        "root_type": DecisionNodeType.SELECTOR,
        "children": [
            {"type": DecisionNodeType.CONDITION, "name": "Enemy in Range", "condition": "always_true",
             "children": [
                 {"type": DecisionNodeType.PRIORITY, "name": "Combat Actions",
                  "children": [
                      {"type": DecisionNodeType.ACTION, "name": "Attack", "action": "attack", "priority": 10},
                      {"type": DecisionNodeType.ACTION, "name": "Defend", "action": "defend", "priority": 5},
                      {"type": DecisionNodeType.ACTION, "name": "Flee", "action": "flee", "priority": 1},
                  ]},
             ]},
            {"type": DecisionNodeType.ACTION, "name": "Patrol", "action": "patrol"},
        ],
    },
    "navigation": {
        "name": "Navigation Decision Tree",
        "root_type": DecisionNodeType.SEQUENCE,
        "children": [
            {"type": DecisionNodeType.CONDITION, "name": "Has Destination", "condition": "always_true"},
            {"type": DecisionNodeType.FALLBACK, "name": "Path to Target",
             "children": [
                 {"type": DecisionNodeType.ACTION, "name": "Direct Path", "action": "move_direct"},
                 {"type": DecisionNodeType.ACTION, "name": "Find Route", "action": "find_route"},
             ]},
            {"type": DecisionNodeType.ACTION, "name": "Move", "action": "move"},
        ],
    },
    "interaction": {
        "name": "Interaction Decision Tree",
        "root_type": DecisionNodeType.RANDOM,
        "children": [
            {"type": DecisionNodeType.ACTION, "name": "Greet", "action": "greet", "probability": 0.4},
            {"type": DecisionNodeType.ACTION, "name": "Trade", "action": "trade", "probability": 0.3},
            {"type": DecisionNodeType.ACTION, "name": "Quest", "action": "offer_quest", "probability": 0.2},
            {"type": DecisionNodeType.ACTION, "name": "Ignore", "action": "ignore", "probability": 0.1},
        ],
    },
}


def create_template_graph(engine: DecisionGraphEngine, template_name: str) -> Optional[DecisionGraph]:
    """Create a decision graph from a predefined template."""
    template = _DECISION_GRAPH_TEMPLATES.get(template_name)
    if not template:
        return None

    graph = engine.create_graph(
        name=template["name"],
        root_type=template["root_type"],
    )

    def _build_children(parent_id: str, children: list):
        for child_def in children:
            child_type = child_def["type"]
            child = engine.add_child(
                graph.graph_id, parent_id, child_type,
                name=child_def.get("name", ""),
                condition=child_def.get("condition"),
                action=child_def.get("action"),
                priority=child_def.get("priority", 0),
                probability=child_def.get("probability", 1.0),
            )
            if child and "children" in child_def:
                _build_children(child.node_id, child_def["children"])

    _build_children("root", template["children"])
    return graph