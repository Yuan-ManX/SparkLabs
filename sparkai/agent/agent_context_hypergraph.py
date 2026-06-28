"""
SparkLabs Agent - Context Hypergraph Engine

Hypergraph-based context representation for multi-modal agent reasoning.
Extends traditional graph representations with hyperedges that connect
multiple nodes simultaneously, enabling richer context modeling for
game world understanding and agent decision-making.

Architecture:
  ContextHypergraphEngine (Singleton)
    |-- HyperNode (context entity with multi-dimensional attributes)
    |-- HyperEdge (n-ary relationship connecting multiple nodes)
    |-- ContextLayer (semantic grouping of related nodes and edges)
    |-- ContextQuery (structured query against the hypergraph)
    |-- ContextInference (reasoning over the hypergraph structure)

Context Layers:
  - ENTITY: game objects, characters, items
  - TEMPORAL: time-based relationships and events
  - SPATIAL: spatial relationships and positioning
  - CAUSAL: cause-effect relationships
  - SEMANTIC: abstract concepts and meanings
  - SOCIAL: relationship networks and social structures

Usage:
    ch = ContextHypergraphEngine.get_instance()
    ch.initialize()

    ch.add_node("player_1", ContextLayer.ENTITY, {"type": "player", "position": [0, 0, 0]})
    ch.add_hyperedge(["player_1", "npc_1", "quest_1"], ContextLayer.CAUSAL, "gives_quest")
    result = ch.query("player_1", layer=ContextLayer.SOCIAL, depth=3)
    ch.shutdown()
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class ContextLayer(Enum):
    """Semantic layers for organizing context nodes."""
    ENTITY = "entity"          # Game objects, characters, items
    TEMPORAL = "temporal"      # Time-based relationships
    SPATIAL = "spatial"        # Spatial positioning
    CAUSAL = "causal"          # Cause-effect chains
    SEMANTIC = "semantic"      # Abstract concepts
    SOCIAL = "social"          # Relationship networks
    BEHAVIORAL = "behavioral"  # Behavior patterns
    NARRATIVE = "narrative"    # Story elements
    AUDITORY = "auditory"      # Sound and audio cues
    VISUAL = "visual"          # Visual features


class NodeType(Enum):
    """Types of hypergraph nodes."""
    OBJECT = "object"
    AGENT = "agent"
    LOCATION = "location"
    EVENT = "event"
    CONCEPT = "concept"
    STATE = "state"
    ACTION = "action"
    RELATION = "relation"


class HyperEdgeType(Enum):
    """Types of hyperedges."""
    INTERACTION = "interaction"     # Multi-agent interaction
    TRANSFORMATION = "transformation"  # State change involving multiple entities
    CONSTRAINT = "constraint"       # Multi-entity constraint
    ASSOCIATION = "association"     # Loose multi-entity relationship
    DEPENDENCY = "dependency"       # Multi-entity dependency chain
    COMPOSITION = "composition"     # Part-whole relationship
    TEMPORAL = "temporal"           # Time-based multi-entity relationship


class QueryMode(Enum):
    """Query traversal modes."""
    BFS = "bfs"
    DFS = "dfs"
    RANDOM_WALK = "random_walk"
    RELEVANCE_RANKED = "relevance_ranked"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class HyperNode:
    """A node in the context hypergraph."""
    node_id: str
    layer: ContextLayer
    node_type: NodeType = NodeType.OBJECT
    attributes: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    importance: float = 0.5
    confidence: float = 1.0
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "layer": self.layer.value,
            "node_type": self.node_type.value,
            "attributes": self.attributes,
            "importance": self.importance,
            "confidence": self.confidence,
            "tags": self.tags,
            "access_count": self.access_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


@dataclass
class HyperEdge:
    """A hyperedge connecting multiple nodes."""
    edge_id: str
    node_ids: List[str]
    layer: ContextLayer
    edge_type: HyperEdgeType = HyperEdgeType.ASSOCIATION
    label: str = ""
    weight: float = 1.0
    confidence: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    is_directed: bool = False
    source_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def arity(self) -> int:
        return len(self.node_ids)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "node_ids": self.node_ids,
            "layer": self.layer.value,
            "edge_type": self.edge_type.value,
            "label": self.label,
            "weight": self.weight,
            "confidence": self.confidence,
            "arity": self.arity,
            "is_directed": self.is_directed,
            "source_id": self.source_id,
            "attributes": self.attributes,
            "created_at": self.created_at,
        }


@dataclass
class ContextSubgraph:
    """A subgraph extracted from the hypergraph."""
    subgraph_id: str
    nodes: List[HyperNode]
    edges: List[HyperEdge]
    center_node_id: Optional[str] = None
    layer_filter: Optional[ContextLayer] = None
    depth: int = 0
    relevance_score: float = 0.0
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subgraph_id": self.subgraph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "center_node_id": self.center_node_id,
            "depth": self.depth,
            "relevance_score": self.relevance_score,
            "summary": self.summary,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }


@dataclass
class ContextQuery:
    """A structured query against the hypergraph."""
    query_id: str
    text: str = ""
    node_ids: List[str] = field(default_factory=list)
    layers: List[ContextLayer] = field(default_factory=list)
    node_types: List[NodeType] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    max_depth: int = 3
    max_results: int = 50
    mode: QueryMode = QueryMode.BFS
    filter_fn: Optional[Callable[[HyperNode], bool]] = None
    created_at: float = field(default_factory=time.time)


# =============================================================================
# Context Hypergraph Engine
# =============================================================================


class ContextHypergraphEngine:
    """
    Hypergraph-based context engine for AI game agents.
    Enables rich multi-dimensional context representation and reasoning.
    """

    _instance: Optional["ContextHypergraphEngine"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if ContextHypergraphEngine._instance is not None:
            raise RuntimeError("Use ContextHypergraphEngine.get_instance()")
        self._initialized: bool = False
        self._nodes: Dict[str, HyperNode] = {}
        self._edges: Dict[str, HyperEdge] = {}
        self._layers: Dict[ContextLayer, List[str]] = {}
        self._node_edges: Dict[str, List[str]] = {}  # node_id -> edge_ids
        self._adjacency: Dict[str, Dict[str, float]] = {}  # node_id -> {neighbor_id: weight}
        self._subgraphs: Dict[str, ContextSubgraph] = {}
        self._stats: Dict[str, Any] = {
            "total_queries": 0,
            "total_nodes_added": 0,
            "total_edges_added": 0,
            "nodes_by_layer": {},
            "edges_by_layer": {},
        }
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "ContextHypergraphEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the hypergraph engine."""
        with self._lock:
            if self._initialized:
                return
            for layer in ContextLayer:
                self._layers[layer] = []
            self._initialized = True

    def add_node(self, node_id: str, layer: ContextLayer,
                 node_type: NodeType = NodeType.OBJECT,
                 attributes: Optional[Dict[str, Any]] = None,
                 **kwargs: Any) -> Optional[HyperNode]:
        """Add a node to the hypergraph."""
        with self._lock:
            if node_id in self._nodes:
                # Update existing node
                existing = self._nodes[node_id]
                if attributes:
                    existing.attributes.update(attributes)
                existing.updated_at = time.time()
                existing.access_count += 1
                return existing

            node = HyperNode(
                node_id=node_id,
                layer=layer,
                node_type=node_type,
                attributes=attributes or {},
                **kwargs,
            )
            self._nodes[node_id] = node
            self._layers[layer].append(node_id)
            self._adjacency[node_id] = {}
            self._node_edges[node_id] = []
            self._stats["total_nodes_added"] += 1
            self._stats["nodes_by_layer"][layer.value] = (
                self._stats["nodes_by_layer"].get(layer.value, 0) + 1
            )
            return node

    def add_hyperedge(self, node_ids: List[str], layer: ContextLayer,
                      label: str = "", edge_type: HyperEdgeType = HyperEdgeType.ASSOCIATION,
                      weight: float = 1.0, **kwargs: Any) -> Optional[HyperEdge]:
        """Add a hyperedge connecting multiple nodes."""
        with self._lock:
            # Ensure all nodes exist
            for nid in node_ids:
                if nid not in self._nodes:
                    return None

            edge_id = uuid.uuid4().hex[:12]
            edge = HyperEdge(
                edge_id=edge_id,
                node_ids=list(node_ids),
                layer=layer,
                edge_type=edge_type,
                label=label,
                weight=weight,
                **kwargs,
            )
            self._edges[edge_id] = edge

            # Update node-edge index and adjacency
            for nid in node_ids:
                if nid not in self._node_edges:
                    self._node_edges[nid] = []
                self._node_edges[nid].append(edge_id)

                # Update adjacency with all other nodes in the hyperedge
                for other_id in node_ids:
                    if other_id != nid:
                        if other_id not in self._adjacency[nid]:
                            self._adjacency[nid][other_id] = 0.0
                        self._adjacency[nid][other_id] += weight

            self._stats["total_edges_added"] += 1
            self._stats["edges_by_layer"][layer.value] = (
                self._stats["edges_by_layer"].get(layer.value, 0) + 1
            )
            return edge

    def query(self, query_text: str = "", node_ids: Optional[List[str]] = None,
              layers: Optional[List[ContextLayer]] = None,
              max_depth: int = 3, max_results: int = 50,
              mode: QueryMode = QueryMode.BFS) -> ContextSubgraph:
        """Query the hypergraph for context."""
        with self._lock:
            self._stats["total_queries"] += 1

            query_obj = ContextQuery(
                query_id=uuid.uuid4().hex[:12],
                text=query_text,
                node_ids=node_ids or [],
                layers=layers or [],
                max_depth=max_depth,
                max_results=max_results,
                mode=mode,
            )

            subgraph = self._execute_query(query_obj)
            self._subgraphs[subgraph.subgraph_id] = subgraph
            return subgraph

    def _execute_query(self, query: ContextQuery) -> ContextSubgraph:
        """Execute a structured query against the hypergraph."""
        # Determine seed nodes
        seed_nodes: List[str] = list(query.node_ids)

        if not seed_nodes and query.text:
            # Text-based seed search
            seed_nodes = self._search_nodes_by_text(query.text)

        if not seed_nodes:
            seed_nodes = list(self._nodes.keys())[:query.max_results]

        # Filter by layers
        if query.layers:
            seed_nodes = [nid for nid in seed_nodes
                          if self._nodes.get(nid, HyperNode(node_id=nid, layer=ContextLayer.ENTITY)).layer in query.layers]

        if query.node_types:
            seed_nodes = [nid for nid in seed_nodes
                          if self._nodes.get(nid, HyperNode(node_id=nid, layer=ContextLayer.ENTITY)).node_type in query.node_types]

        if query.tags:
            seed_nodes = [nid for nid in seed_nodes
                          if any(t in (self._nodes.get(nid, HyperNode(node_id=nid, layer=ContextLayer.ENTITY)).tags) for t in query.tags)]

        if query.filter_fn:
            seed_nodes = [nid for nid in seed_nodes
                          if query.filter_fn(self._nodes.get(nid, HyperNode(node_id=nid, layer=ContextLayer.ENTITY)))]

        # Traverse to build subgraph
        visited_nodes: Dict[str, HyperNode] = {}
        visited_edges: Dict[str, HyperEdge] = {}
        center_id = seed_nodes[0] if seed_nodes else None

        if query.mode == QueryMode.BFS:
            self._bfs_traverse(seed_nodes, query.max_depth, query.max_results,
                               visited_nodes, visited_edges, query.layers)
        elif query.mode == QueryMode.DFS:
            self._dfs_traverse(seed_nodes, query.max_depth, query.max_results,
                               visited_nodes, visited_edges, query.layers)
        elif query.mode == QueryMode.RANDOM_WALK:
            self._random_walk_traverse(seed_nodes, query.max_depth, query.max_results,
                                       visited_nodes, visited_edges, query.layers)
        else:
            self._bfs_traverse(seed_nodes, query.max_depth, query.max_results,
                               visited_nodes, visited_edges, query.layers)

        # Generate summary
        summary = self._generate_subgraph_summary(visited_nodes, visited_edges)

        return ContextSubgraph(
            subgraph_id=uuid.uuid4().hex[:12],
            nodes=list(visited_nodes.values()),
            edges=list(visited_edges.values()),
            center_node_id=center_id,
            layer_filter=query.layers[0] if query.layers else None,
            depth=query.max_depth,
            relevance_score=len(visited_nodes) / max(len(self._nodes), 1),
            summary=summary,
        )

    def _bfs_traverse(self, seed_nodes: List[str], max_depth: int, max_results: int,
                      visited_nodes: Dict[str, HyperNode], visited_edges: Dict[str, HyperEdge],
                      layer_filter: List[ContextLayer]) -> None:
        """BFS traversal from seed nodes."""
        from collections import deque

        queue = deque([(nid, 0) for nid in seed_nodes])
        while queue and len(visited_nodes) < max_results:
            current_id, depth = queue.popleft()
            if current_id in visited_nodes or depth > max_depth:
                continue

            node = self._nodes.get(current_id)
            if node is None:
                continue
            if layer_filter and node.layer not in layer_filter:
                continue

            visited_nodes[current_id] = node
            node.access_count += 1

            # Add connected edges
            for edge_id in self._node_edges.get(current_id, []):
                edge = self._edges.get(edge_id)
                if edge and edge_id not in visited_edges:
                    visited_edges[edge_id] = edge
                    for nid in edge.node_ids:
                        if nid not in visited_nodes and depth < max_depth:
                            queue.append((nid, depth + 1))

    def _dfs_traverse(self, seed_nodes: List[str], max_depth: int, max_results: int,
                      visited_nodes: Dict[str, HyperNode], visited_edges: Dict[str, HyperEdge],
                      layer_filter: List[ContextLayer]) -> None:
        """DFS traversal from seed nodes."""
        def _dfs(current_id: str, depth: int):
            if current_id in visited_nodes or depth > max_depth or len(visited_nodes) >= max_results:
                return
            node = self._nodes.get(current_id)
            if node is None:
                return
            if layer_filter and node.layer not in layer_filter:
                return
            visited_nodes[current_id] = node
            node.access_count += 1
            for edge_id in self._node_edges.get(current_id, []):
                edge = self._edges.get(edge_id)
                if edge and edge_id not in visited_edges:
                    visited_edges[edge_id] = edge
                    for nid in edge.node_ids:
                        _dfs(nid, depth + 1)

        for nid in seed_nodes:
            _dfs(nid, 0)

    def _random_walk_traverse(self, seed_nodes: List[str], max_depth: int, max_results: int,
                              visited_nodes: Dict[str, HyperNode], visited_edges: Dict[str, HyperEdge],
                              layer_filter: List[ContextLayer]) -> None:
        """Random walk traversal from seed nodes."""
        import random

        current = seed_nodes[0] if seed_nodes else None
        if not current:
            return

        for _ in range(max_results):
            node = self._nodes.get(current)
            if node is None:
                break
            if layer_filter and node.layer not in layer_filter:
                continue
            visited_nodes[current] = node
            node.access_count += 1

            # Add connected edges
            for edge_id in self._node_edges.get(current, []):
                edge = self._edges.get(edge_id)
                if edge and edge_id not in visited_edges:
                    visited_edges[edge_id] = edge

            # Random next node
            neighbors = list(self._adjacency.get(current, {}).keys())
            if not neighbors:
                break
            current = random.choice(neighbors)

    def _search_nodes_by_text(self, text: str) -> List[str]:
        """Search nodes by text matching against attributes and tags."""
        results: List[Tuple[str, float]] = []
        text_lower = text.lower()

        for node_id, node in self._nodes.items():
            score = 0.0
            if text_lower in node_id.lower():
                score += 3.0
            for tag in node.tags:
                if text_lower in tag.lower():
                    score += 2.0
            for key, value in node.attributes.items():
                if text_lower in str(key).lower():
                    score += 1.0
                if text_lower in str(value).lower():
                    score += 1.0
            if score > 0:
                results.append((node_id, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:50]]

    def _generate_subgraph_summary(self, nodes: Dict[str, HyperNode],
                                    edges: Dict[str, HyperEdge]) -> str:
        """Generate a textual summary of the subgraph."""
        layer_counts: Dict[str, int] = {}
        for node in nodes.values():
            layer_counts[node.layer.value] = layer_counts.get(node.layer.value, 0) + 1

        edge_type_counts: Dict[str, int] = {}
        for edge in edges.values():
            edge_type_counts[edge.edge_type.value] = edge_type_counts.get(edge.edge_type.value, 0) + 1

        parts = [f"Subgraph with {len(nodes)} nodes and {len(edges)} hyperedges"]
        if layer_counts:
            parts.append(f"Layers: {', '.join(f'{k}={v}' for k, v in layer_counts.items())}")
        if edge_type_counts:
            parts.append(f"Edge types: {', '.join(f'{k}={v}' for k, v in edge_type_counts.items())}")

        return ". ".join(parts)

    def get_neighbors(self, node_id: str, depth: int = 1,
                      layer: Optional[ContextLayer] = None) -> List[HyperNode]:
        """Get neighboring nodes within a given depth."""
        with self._lock:
            neighbors: Dict[str, HyperNode] = {}
            stack = [(node_id, 0)]
            while stack:
                current_id, d = stack.pop()
                if d > depth or current_id in neighbors:
                    continue
                node = self._nodes.get(current_id)
                if node is None:
                    continue
                if layer and node.layer != layer:
                    continue
                if current_id != node_id:
                    neighbors[current_id] = node
                for adj_id in self._adjacency.get(current_id, {}):
                    if adj_id not in neighbors:
                        stack.append((adj_id, d + 1))
            return list(neighbors.values())

    def get_node(self, node_id: str) -> Optional[HyperNode]:
        """Get a node by ID."""
        node = self._nodes.get(node_id)
        if node:
            node.access_count += 1
        return node

    def get_edge(self, edge_id: str) -> Optional[HyperEdge]:
        """Get an edge by ID."""
        return self._edges.get(edge_id)

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and its connected edges."""
        with self._lock:
            if node_id not in self._nodes:
                return False
            node = self._nodes[node_id]
            self._layers[node.layer].remove(node_id)

            # Remove connected edges
            edge_ids = list(self._node_edges.get(node_id, []))
            for edge_id in edge_ids:
                if edge_id in self._edges:
                    del self._edges[edge_id]

            if node_id in self._node_edges:
                del self._node_edges[node_id]
            if node_id in self._adjacency:
                # Remove node from other adjacency lists
                for other_id in self._adjacency[node_id]:
                    if other_id in self._adjacency:
                        self._adjacency[other_id].pop(node_id, None)
                del self._adjacency[node_id]
            del self._nodes[node_id]
            return True

    def remove_edge(self, edge_id: str) -> bool:
        """Remove a hyperedge."""
        with self._lock:
            if edge_id not in self._edges:
                return False
            edge = self._edges[edge_id]
            for nid in edge.node_ids:
                if nid in self._node_edges:
                    self._node_edges[nid].remove(edge_id)
            del self._edges[edge_id]
            return True

    def update_node(self, node_id: str, attributes: Optional[Dict[str, Any]] = None,
                    importance: Optional[float] = None, confidence: Optional[float] = None,
                    tags: Optional[List[str]] = None) -> Optional[HyperNode]:
        """Update a node's attributes."""
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return None
            if attributes:
                node.attributes.update(attributes)
            if importance is not None:
                node.importance = importance
            if confidence is not None:
                node.confidence = confidence
            if tags is not None:
                node.tags = tags
            node.updated_at = time.time()
            return node

    def list_nodes(self) -> List[HyperNode]:
        """List all nodes in the hypergraph."""
        with self._lock:
            return list(self._nodes.values())

    def list_edges(self) -> List[HyperEdge]:
        """List all hyperedges in the hypergraph."""
        with self._lock:
            return list(self._edges.values())

    def get_status(self) -> Dict[str, Any]:
        """Get engine status and statistics."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
                "subgraph_count": len(self._subgraphs),
                "nodes_by_layer": {k.value: len(v) for k, v in self._layers.items()},
                "edges_by_layer": self._stats["edges_by_layer"],
                "stats": self._stats,
            }

    def clear(self) -> None:
        """Clear all data from the hypergraph."""
        with self._lock:
            self._nodes.clear()
            self._edges.clear()
            self._layers = {layer: [] for layer in ContextLayer}
            self._node_edges.clear()
            self._adjacency.clear()
            self._subgraphs.clear()

    def shutdown(self) -> None:
        """Shutdown the hypergraph engine."""
        with self._lock:
            self.clear()
            self._initialized = False