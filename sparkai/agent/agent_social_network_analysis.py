"""
SparkLabs Agent - Social Network Analysis Engine

This module implements graph-theoretic analysis on top of the social
relationship model used by AI agents operating inside the SparkLabs AI-native
game engine. While :mod:`agent_social_relationship` tracks per-pair
relationship state, this engine provides whole-graph analytical capabilities:
centrality measures, community detection, clique analysis, and aggregate
network metrics.

Core concepts:

  1. Centrality Measures
       The engine computes four classic node-importance scores for every
       agent: degree, betweenness, closeness, and eigenvector centrality.
       PageRank is also available for influence-aware ranking. All scores are
       normalised into [0.0, 1.0] and accompanied by a rank within the graph.

  2. Community Detection
       Three complementary algorithms are provided: Louvain-style greedy
       modularity optimisation, asynchronous label propagation, and clique
       percolation. Each produces :class:`Community` records with member
       sets, internal/external edge counts, density, and the modularity
       contribution reported by the algorithm.

  3. Clique Analysis
       The engine enumerates maximal, maximum, and k-cliques. The resulting
       :class:`Clique` records carry member sets, edge counts, and density,
       which is useful for identifying tightly-cohesive subgroups.

  4. Network Metrics
       Whole-graph properties (density, diameter, average path length,
       clustering coefficient, and degree assortativity) are computed on
       demand and cached as :class:`NetworkMetricReport` instances.

Architecture:
  SocialNetworkAnalysisEngine (Singleton, double-checked locking with
                               threading.RLock)
    |-- NetworkAgent                -- a node in the social graph
    |-- NetworkEdge                 -- a (possibly bidirectional) link
    |-- CentralityScore             -- one centrality reading for one agent
    |-- Community                   -- a detected community
    |-- Clique                      -- a maximal/maximum/k-clique
    |-- NetworkMetricReport         -- one graph-level metric
    |-- InfluenceProfile            -- combined influence reading
    |-- SocialNetworkStats          -- aggregate engine statistics
    |-- SocialNetworkSnapshot       -- complete engine state snapshot
    |-- SocialNetworkEvent          -- observable engine lifecycle event

All public mutating methods are protected by a re-entrant lock so the engine
is safe to call from multiple agent threads. Bounded in-memory stores use
FIFO eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import math
import random
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_AGENTS: int = 1000
_MAX_EDGES: int = 5000
_MAX_CENTRALITIES: int = 4000
_MAX_COMMUNITIES: int = 500
_MAX_CLIQUES: int = 2000
_MAX_METRICS: int = 500
_MAX_INFLUENCES: int = 1000
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Algorithm constants
# ---------------------------------------------------------------------------

_POWER_ITERATIONS: int = 10
_PAGERANK_DAMPING: float = 0.85
_LOUVAIN_PASSES: int = 3
_LABEL_PROPAGATION_ITERATIONS: int = 10
_K_CLIQUE_SIZE: int = 3
_MIN_SEED_AGENTS: int = 1


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return a UTC ISO-8601 timestamp string terminated with 'Z'."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id() -> str:
    """Generate a short unique identifier for a record."""
    return uuid.uuid4().hex[:16]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive [low, high] range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds.

    Python dicts preserve insertion order (3.7+), so the first key returned
    by iteration is the oldest. This implements FIFO eviction.
    """
    while len(store) > max_size:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a list until within bounds."""
    while len(store) > max_size:
        store.pop(0)


def _safe_div(numerator: float, denominator: float) -> float:
    """Return numerator/denominator or 0.0 if denominator is zero."""
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _sort_key(score: "CentralityScore") -> float:
    """Sort key for centrality scores: highest score first, ties broken by id."""
    return (-score.score, score.agent_id)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CentralityType(Enum):
    """Centrality measure computed for an individual agent."""
    DEGREE = "degree"
    BETWEENNESS = "betweenness"
    CLOSENESS = "closeness"
    EIGENVECTOR = "eigenvector"
    PAGERANK = "pagerank"


class CommunityAlgorithm(Enum):
    """Algorithm used to detect communities in the social graph."""
    LOUVAIN = "louvain"
    LABEL_PROPAGATION = "label_propagation"
    CLIQUE_PERCOLATION = "clique_percolation"


class NetworkMetric(Enum):
    """Aggregate network-level metric computed for the social graph."""
    DENSITY = "density"
    DIAMETER = "diameter"
    AVERAGE_PATH_LENGTH = "average_path_length"
    CLUSTERING_COEFFICIENT = "clustering_coefficient"
    ASSORTATIVITY = "assortativity"


class CliqueType(Enum):
    """Type of clique enumerated by the clique-finding routines."""
    MAXIMAL = "maximal"
    MAXIMUM = "maximum"
    K_CLIQUE = "k_clique"


class InfluenceLevel(Enum):
    """Discrete influence level derived from the influence score."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    INFLUENTIAL = "influential"


class SocialNetworkEventKind(Enum):
    """Observable lifecycle events emitted by the social network engine."""
    AGENT_REGISTERED = "agent_registered"
    EDGE_ADDED = "edge_added"
    EDGE_REMOVED = "edge_removed"
    CENTRALITY_COMPUTED = "centrality_computed"
    COMMUNITY_DETECTED = "community_detected"
    CLIQUE_FOUND = "clique_found"
    METRIC_COMPUTED = "metric_computed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class NetworkAgent:
    """A node in the social network analysis graph."""
    agent_id: str
    name: str
    joined_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this agent to a JSON-friendly dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "joined_at": self.joined_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class NetworkEdge:
    """A (possibly bidirectional) edge in the social graph."""
    edge_id: str
    source_id: str
    target_id: str
    weight: float
    relationship_type: str
    bidirectional: bool
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this edge to a JSON-friendly dictionary."""
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "weight": self.weight,
            "relationship_type": self.relationship_type,
            "bidirectional": self.bidirectional,
            "created_at": self.created_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class CentralityScore:
    """A centrality measurement for a single agent."""
    agent_id: str
    centrality_type: CentralityType
    score: float
    rank: int
    computed_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this centrality score to a JSON-friendly dictionary."""
        return {
            "agent_id": self.agent_id,
            "centrality_type": self.centrality_type.value,
            "score": self.score,
            "rank": self.rank,
            "computed_at": self.computed_at,
        }


@dataclass
class Community:
    """A detected community of agents in the social graph."""
    community_id: str
    member_ids: List[str]
    internal_edges: int
    external_edges: int
    density: float
    algorithm: CommunityAlgorithm
    modularity: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this community to a JSON-friendly dictionary."""
        return {
            "community_id": self.community_id,
            "member_ids": list(self.member_ids),
            "internal_edges": self.internal_edges,
            "external_edges": self.external_edges,
            "density": self.density,
            "algorithm": self.algorithm.value,
            "modularity": self.modularity,
        }


@dataclass
class Clique:
    """A clique detected in the social graph."""
    clique_id: str
    member_ids: List[str]
    size: int
    edge_count: int
    density: float
    clique_type: CliqueType

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this clique to a JSON-friendly dictionary."""
        return {
            "clique_id": self.clique_id,
            "member_ids": list(self.member_ids),
            "size": self.size,
            "edge_count": self.edge_count,
            "density": self.density,
            "clique_type": self.clique_type.value,
        }


@dataclass
class NetworkMetricReport:
    """A single network-level metric measurement."""
    metric_type: NetworkMetric
    value: float
    computed_at: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this metric report to a JSON-friendly dictionary."""
        return {
            "metric_type": self.metric_type.value,
            "value": self.value,
            "computed_at": self.computed_at,
            "details": dict(self.details) if self.details else {},
        }


@dataclass
class InfluenceProfile:
    """A combined influence reading for an agent."""
    agent_id: str
    influence_score: float
    betweenness: float
    pagerank: float
    community_count: int
    influence_level: InfluenceLevel
    computed_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this influence profile to a JSON-friendly dictionary."""
        return {
            "agent_id": self.agent_id,
            "influence_score": self.influence_score,
            "betweenness": self.betweenness,
            "pagerank": self.pagerank,
            "community_count": self.community_count,
            "influence_level": self.influence_level.value,
            "computed_at": self.computed_at,
        }


@dataclass
class SocialNetworkStats:
    """Aggregate statistics about the social network analysis engine."""
    total_agents: int
    total_edges: int
    total_communities: int
    total_cliques: int
    density: float
    avg_degree: float
    max_degree: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these statistics to a JSON-friendly dictionary."""
        return {
            "total_agents": self.total_agents,
            "total_edges": self.total_edges,
            "total_communities": self.total_communities,
            "total_cliques": self.total_cliques,
            "density": self.density,
            "avg_degree": self.avg_degree,
            "max_degree": self.max_degree,
        }


@dataclass
class SocialNetworkEvent:
    """An observable lifecycle event emitted by the engine."""
    event_id: str
    kind: SocialNetworkEventKind
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a JSON-friendly dictionary."""
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload) if self.payload else {},
        }


@dataclass
class SocialNetworkSnapshot:
    """A complete snapshot of the social network analysis engine state."""
    initialized: bool
    agents: List[NetworkAgent]
    edges: List[NetworkEdge]
    centralities: List[CentralityScore]
    communities: List[Community]
    cliques: List[Clique]
    metrics: List[NetworkMetricReport]
    events: List[SocialNetworkEvent]
    stats: SocialNetworkStats

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "initialized": self.initialized,
            "agents": [a.to_dict() for a in self.agents],
            "edges": [e.to_dict() for e in self.edges],
            "centralities": [c.to_dict() for c in self.centralities],
            "communities": [c.to_dict() for c in self.communities],
            "cliques": [c.to_dict() for c in self.cliques],
            "metrics": [m.to_dict() for m in self.metrics],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


# ---------------------------------------------------------------------------
# Social Network Analysis Engine (Singleton with double-checked locking)
# ---------------------------------------------------------------------------


class SocialNetworkAnalysisEngine:
    """Graph-theoretic social network analysis engine for AI agents.

    The engine maintains a directed/undirected weighted graph of agents and
    relationships, and exposes a wide range of analytical capabilities:
    centrality measures, community detection, clique enumeration, network
    metrics, and combined influence profiles. It is a thread-safe singleton
    accessed via :meth:`get_instance` or the module-level
    :func:`get_social_network_analysis` helper.

    Usage:
        engine = get_social_network_analysis()
        engine.register_agent("agent_alpha")
        engine.add_edge("agent_alpha", "agent_beta", weight=1.5,
                        relationship_type="ally")
        ranked = engine.rank_by_centrality(CentralityType.DEGREE, limit=10)
    """

    _instance: Optional["SocialNetworkAnalysisEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # -- Construction (double-checked locking) ---------------------------

    def __new__(cls) -> "SocialNetworkAnalysisEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        # Fast path: already initialized singleton.
        if self._initialized:
            return
        with self._lock:
            # Second check inside the lock to guard against concurrent
            # construction.
            if self._initialized:
                return

            # Primary graph stores keyed by id.
            self._agents: Dict[str, NetworkAgent] = {}
            self._edges: Dict[str, NetworkEdge] = {}

            # Adjacency structures (rebuilt on edge mutation). They live
            # alongside the primary stores for fast analysis.
            self._out_neighbors: Dict[str, Dict[str, float]] = {}
            self._in_neighbors: Dict[str, Dict[str, float]] = {}

            # Cached analysis results.
            self._centralities: Dict[str, CentralityScore] = {}
            self._communities: Dict[str, Community] = {}
            self._cliques: Dict[str, Clique] = {}
            self._metrics: Dict[str, NetworkMetricReport] = {}
            self._influences: Dict[str, InfluenceProfile] = {}

            # Event log and counters.
            self._events: List[SocialNetworkEvent] = []
            self._edge_counter: int = 0
            self._centrality_counter: int = 0
            self._community_counter: int = 0
            self._clique_counter: int = 0
            self._metric_counter: int = 0
            self._influence_counter: int = 0

            self._initialized: bool = True

            # Seed baseline social network analysis data.
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "SocialNetworkAnalysisEngine":
        """Return the singleton SocialNetworkAnalysisEngine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str, name: str = "") -> NetworkAgent:
        """Create (or return an existing) :class:`NetworkAgent`.

        Args:
            agent_id: Unique identifier of the agent to register.
            name: Human-readable name. Defaults to ``agent_id`` when empty.

        Returns:
            The :class:`NetworkAgent` for the given id. If the agent was
            already registered, the existing record is returned unchanged.
        """
        with self._lock:
            if agent_id in self._agents:
                return self._agents[agent_id]
            display_name = name or agent_id
            agent = NetworkAgent(
                agent_id=agent_id,
                name=display_name,
                joined_at=_now(),
                metadata={},
            )
            self._agents[agent_id] = agent
            self._out_neighbors.setdefault(agent_id, {})
            self._in_neighbors.setdefault(agent_id, {})
            _evict_fifo_dict(self._agents, _MAX_AGENTS)
            self._record_event(
                SocialNetworkEventKind.AGENT_REGISTERED,
                {"agent_id": agent_id, "name": display_name},
            )
            return agent

    def get_agent(self, agent_id: str) -> Optional[NetworkAgent]:
        """Return a single agent by id, or None if not found."""
        with self._lock:
            return self._agents.get(agent_id)

    def list_agents(self) -> List[NetworkAgent]:
        """Return all registered agents in insertion order."""
        with self._lock:
            return list(self._agents.values())

    def _ensure_agent_locked(self, agent_id: str) -> NetworkAgent:
        """Return the agent record, creating one if missing.

        Assumes the caller already holds ``self._lock``.
        """
        agent = self._agents.get(agent_id)
        if agent is not None:
            return agent
        agent = NetworkAgent(
            agent_id=agent_id,
            name=agent_id,
            joined_at=_now(),
            metadata={},
        )
        self._agents[agent_id] = agent
        self._out_neighbors.setdefault(agent_id, {})
        self._in_neighbors.setdefault(agent_id, {})
        _evict_fifo_dict(self._agents, _MAX_AGENTS)
        self._record_event(
            SocialNetworkEventKind.AGENT_REGISTERED,
            {"agent_id": agent_id, "name": agent_id},
        )
        return agent

    # ------------------------------------------------------------------
    # Edge management
    # ------------------------------------------------------------------

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        weight: float = 1.0,
        relationship_type: str = "general",
        bidirectional: bool = True,
    ) -> Optional[NetworkEdge]:
        """Add a weighted edge between two agents.

        Self-loops (source == target) are rejected and ``None`` is returned.
        When ``bidirectional`` is true, the edge is also recorded in the
        reverse direction for analytical convenience; the same edge id
        represents both directions in that case.

        Args:
            source_id: Source agent id. Created if not already registered.
            target_id: Target agent id. Created if not already registered.
            weight: Positive edge weight. Negative weights are clamped to 0.
            relationship_type: Free-form relationship label.
            bidirectional: When true, the edge is treated as undirected for
                graph algorithms.

        Returns:
            The created :class:`NetworkEdge`, or ``None`` if the edge was
            a self-loop.
        """
        with self._lock:
            if source_id == target_id:
                return None
            self._ensure_agent_locked(source_id)
            self._ensure_agent_locked(target_id)

            edge = NetworkEdge(
                edge_id=_new_id(),
                source_id=source_id,
                target_id=target_id,
                weight=_clamp(float(weight), 0.0, float("inf")),
                relationship_type=relationship_type or "general",
                bidirectional=bool(bidirectional),
                created_at=_now(),
                metadata={},
            )
            self._edges[edge.edge_id] = edge
            self._edge_counter += 1
            _evict_fifo_dict(self._edges, _MAX_EDGES)

            # Update adjacency structures.
            self._out_neighbors.setdefault(source_id, {})[target_id] = edge.weight
            self._in_neighbors.setdefault(target_id, {})[source_id] = edge.weight
            if edge.bidirectional:
                self._out_neighbors.setdefault(target_id, {})[source_id] = edge.weight
                self._in_neighbors.setdefault(source_id, {})[target_id] = edge.weight

            self._record_event(
                SocialNetworkEventKind.EDGE_ADDED,
                {
                    "edge_id": edge.edge_id,
                    "source_id": source_id,
                    "target_id": target_id,
                    "weight": edge.weight,
                    "bidirectional": edge.bidirectional,
                },
            )
            return edge

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge by id. Returns ``True`` if the edge was removed.

        The reverse-direction entries are also removed when the edge was
        bidirectional, keeping the adjacency structures consistent.
        """
        with self._lock:
            edge = self._edges.pop(edge_id, None)
            if edge is None:
                return False
            self._out_neighbors.get(edge.source_id, {}).pop(edge.target_id, None)
            self._in_neighbors.get(edge.target_id, {}).pop(edge.source_id, None)
            if edge.bidirectional:
                self._out_neighbors.get(edge.target_id, {}).pop(edge.source_id, None)
                self._in_neighbors.get(edge.source_id, {}).pop(edge.target_id, None)
            self._record_event(
                SocialNetworkEventKind.EDGE_REMOVED,
                {
                    "edge_id": edge_id,
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                },
            )
            return True

    def get_edge(self, edge_id: str) -> Optional[NetworkEdge]:
        """Return an edge by id, or ``None`` if not found."""
        with self._lock:
            return self._edges.get(edge_id)

    def list_edges(self, agent_id: Optional[str] = None) -> List[NetworkEdge]:
        """List edges, optionally filtered to a single agent.

        When ``agent_id`` is given, edges incident to that agent (in either
        direction) are returned.
        """
        with self._lock:
            if agent_id is None:
                return list(self._edges.values())
            return [
                e for e in self._edges.values()
                if e.source_id == agent_id or e.target_id == agent_id
            ]

    def get_neighbors(
        self,
        agent_id: str,
        include_bidirectional: bool = True,
    ) -> List[NetworkAgent]:
        """Return agents directly connected to ``agent_id``.

        When ``include_bidirectional`` is true, neighbors reached through
        edges whose ``bidirectional`` flag is set are also returned, treating
        those edges as undirected.
        """
        with self._lock:
            if agent_id not in self._agents:
                return []
            neighbor_ids: Set[str] = set()
            for nid in self._out_neighbors.get(agent_id, {}):
                neighbor_ids.add(nid)
            for nid in self._in_neighbors.get(agent_id, {}):
                neighbor_ids.add(nid)
            if not include_bidirectional:
                # Restrict to outgoing edges that are not bidirectional.
                for edge in self._edges.values():
                    if edge.source_id == agent_id and not edge.bidirectional:
                        neighbor_ids.add(edge.target_id)
                    elif edge.target_id == agent_id and not edge.bidirectional:
                        neighbor_ids.add(edge.source_id)
            return [
                self._agents[nid] for nid in neighbor_ids
                if nid in self._agents and nid != agent_id
            ]

    # ------------------------------------------------------------------
    # Adjacency helpers (used by the algorithm implementations)
    # ------------------------------------------------------------------

    def _undirected_adjacency(self) -> Dict[str, Set[str]]:
        """Return an undirected adjacency map (agent_id -> neighbor set).

        Assumes the caller already holds ``self._lock``. Bidirectional edges
        contribute both directions; directed edges contribute only the
        source-to-target direction.
        """
        adj: Dict[str, Set[str]] = {a: set() for a in self._agents}
        for edge in self._edges.values():
            if edge.source_id not in adj or edge.target_id not in adj:
                continue
            adj[edge.source_id].add(edge.target_id)
            if edge.bidirectional:
                adj[edge.target_id].add(edge.source_id)
        return adj

    def _weighted_undirected_adjacency(self) -> Dict[str, Dict[str, float]]:
        """Return a weighted undirected adjacency map.

        Assumes the caller already holds ``self._lock``.
        """
        adj: Dict[str, Dict[str, float]] = {a: {} for a in self._agents}
        for edge in self._edges.values():
            if edge.source_id not in adj or edge.target_id not in adj:
                continue
            adj[edge.source_id][edge.target_id] = max(
                adj[edge.source_id].get(edge.target_id, 0.0), edge.weight
            )
            if edge.bidirectional:
                adj[edge.target_id][edge.source_id] = max(
                    adj[edge.target_id].get(edge.source_id, 0.0), edge.weight
                )
        return adj

    # ------------------------------------------------------------------
    # Centrality measures
    # ------------------------------------------------------------------

    def compute_centrality(
        self,
        agent_id: str,
        centrality_type: CentralityType,
    ) -> Optional[CentralityScore]:
        """Compute a single centrality measure for a single agent.

        Args:
            agent_id: Identifier of the agent to score.
            centrality_type: Which centrality measure to compute.

        Returns:
            A :class:`CentralityScore` for the agent, or ``None`` if the
            agent is not registered.
        """
        with self._lock:
            if agent_id not in self._agents:
                return None
            adj = self._undirected_adjacency()
            scores = self._compute_centrality_map(centrality_type, adj)
            score = scores.get(agent_id, 0.0)
            # Compute ranks so the returned score carries a stable rank.
            ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
            rank = 1
            for idx, (nid, _) in enumerate(ranked, start=1):
                if nid == agent_id:
                    rank = idx
                    break
            record = CentralityScore(
                agent_id=agent_id,
                centrality_type=centrality_type,
                score=round(score, 6),
                rank=rank,
                computed_at=_now(),
            )
            self._centralities[f"{centrality_type.value}:{agent_id}"] = record
            self._centrality_counter += 1
            _evict_fifo_dict(self._centralities, _MAX_CENTRALITIES)
            self._record_event(
                SocialNetworkEventKind.CENTRALITY_COMPUTED,
                {
                    "agent_id": agent_id,
                    "centrality_type": centrality_type.value,
                    "score": record.score,
                    "rank": record.rank,
                },
            )
            return record

    def compute_all_centralities(
        self,
        agent_id: str,
    ) -> List[CentralityScore]:
        """Compute degree, betweenness, closeness, and eigenvector centralities.

        PageRank is computed separately as it is more naturally grouped with
        the other influence measures.
        """
        with self._lock:
            results: List[CentralityScore] = []
            for ctype in (
                CentralityType.DEGREE,
                CentralityType.BETWEENNESS,
                CentralityType.CLOSENESS,
                CentralityType.EIGENVECTOR,
            ):
                record = self.compute_centrality(agent_id, ctype)
                if record is not None:
                    results.append(record)
            return results

    def rank_by_centrality(
        self,
        centrality_type: CentralityType,
        limit: int = 10,
    ) -> List[CentralityScore]:
        """Return the top agents ranked by a centrality measure.

        The entire graph is scored; the top ``limit`` results are returned
        in descending score order. For agents in disconnected components,
        betweenness/closeness scores may be zero.
        """
        with self._lock:
            n = max(0, int(limit))
            adj = self._undirected_adjacency()
            scores = self._compute_centrality_map(centrality_type, adj)
            ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
            now = _now()
            results: List[CentralityScore] = []
            for rank, (nid, score) in enumerate(ranked, start=1):
                if n > 0 and rank > n:
                    break
                record = CentralityScore(
                    agent_id=nid,
                    centrality_type=centrality_type,
                    score=round(score, 6),
                    rank=rank,
                    computed_at=now,
                )
                self._centralities[f"{centrality_type.value}:{nid}"] = record
                results.append(record)
            self._centrality_counter += len(results)
            _evict_fifo_dict(self._centralities, _MAX_CENTRALITIES)
            self._record_event(
                SocialNetworkEventKind.CENTRALITY_COMPUTED,
                {
                    "centrality_type": centrality_type.value,
                    "ranking_size": len(results),
                },
            )
            return results

    def _compute_centrality_map(
        self,
        centrality_type: CentralityType,
        adj: Dict[str, Set[str]],
    ) -> Dict[str, float]:
        """Compute a {agent_id: score} map for the chosen centrality type.

        Assumes the caller already holds ``self._lock``. All returned scores
        are normalised into [0.0, 1.0].
        """
        if centrality_type == CentralityType.DEGREE:
            return self._degree_centrality(adj)
        if centrality_type == CentralityType.BETWEENNESS:
            return self._betweenness_centrality(adj)
        if centrality_type == CentralityType.CLOSENESS:
            return self._closeness_centrality(adj)
        if centrality_type == CentralityType.EIGENVECTOR:
            return self._eigenvector_centrality(adj)
        if centrality_type == CentralityType.PAGERANK:
            return self._pagerank_centrality(adj)
        return {a: 0.0 for a in adj}

    def _degree_centrality(
        self,
        adj: Dict[str, Set[str]],
    ) -> Dict[str, float]:
        """Compute normalised degree centrality.

        The score for each node is ``degree / (n - 1)`` for a graph of ``n``
        nodes, with isolated nodes receiving 0.0.
        """
        n = len(adj)
        if n <= 1:
            return {a: 0.0 for a in adj}
        denom = float(n - 1)
        return {a: len(neighbors) / denom for a, neighbors in adj.items()}

    def _betweenness_centrality(
        self,
        adj: Dict[str, Set[str]],
    ) -> Dict[str, float]:
        """Compute Brandes-style betweenness centrality on the undirected view.

        Scores are normalised by ``(n - 1)(n - 2) / 2`` for ``n >= 3``.
        For small or sparse graphs the score is simply divided by the
        maximum so the result lies in [0.0, 1.0].
        """
        nodes = list(adj.keys())
        n = len(nodes)
        if n <= 2:
            return {a: 0.0 for a in nodes}
        raw: Dict[str, float] = {a: 0.0 for a in nodes}
        for source in nodes:
            # Single-source shortest paths via BFS.
            stack: List[str] = []
            predecessors: Dict[str, List[str]] = {a: [] for a in nodes}
            sigma: Dict[str, int] = {a: 0 for a in nodes}
            sigma[source] = 1
            distance: Dict[str, int] = {a: -1 for a in nodes}
            distance[source] = 0
            queue: deque = deque([source])
            while queue:
                v = queue.popleft()
                stack.append(v)
                for w in adj.get(v, set()):
                    if distance[w] < 0:
                        queue.append(w)
                        distance[w] = distance[v] + 1
                    if distance[w] == distance[v] + 1:
                        sigma[w] += sigma[v]
                        predecessors[w].append(v)
            delta: Dict[str, float] = {a: 0.0 for a in nodes}
            while stack:
                w = stack.pop()
                for v in predecessors[w]:
                    if sigma[w] == 0:
                        continue
                    contribution = (sigma[v] / sigma[w]) * (1.0 + delta[w])
                    delta[v] += contribution
                if w != source:
                    raw[w] += delta[w]
        # Normalise: divide each by 2 (undirected double counting) and then
        # by the theoretical maximum for the graph.
        scale = max(1.0, ((n - 1) * (n - 2)) / 2.0)
        return {a: _clamp((raw[a] / 2.0) / scale) for a in nodes}

    def _closeness_centrality(
        self,
        adj: Dict[str, Set[str]],
    ) -> Dict[str, float]:
        """Compute normalised closeness centrality.

        Closeness is ``(n - 1) / sum_of_distances``. Nodes that cannot reach
        others in the undirected view are scored 0.0. Results are normalised
        so the maximum score equals 1.0.
        """
        nodes = list(adj.keys())
        n = len(nodes)
        if n <= 1:
            return {a: 0.0 for a in nodes}
        raw: Dict[str, float] = {}
        for source in nodes:
            distance = self._bfs_distances(source, adj)
            total = sum(distance.values())
            reachable = sum(1 for d in distance.values() if d > 0)
            if total == 0 or reachable < n - 1:
                raw[source] = 0.0
            else:
                raw[source] = (n - 1) / total
        return self._normalise_to_unit(raw)

    def _eigenvector_centrality(
        self,
        adj: Dict[str, Set[str]],
    ) -> Dict[str, float]:
        """Compute eigenvector centrality via power iteration.

        After ``_POWER_ITERATIONS`` iterations the raw scores are normalised
        to [0.0, 1.0] by dividing by the maximum absolute value.
        """
        nodes = list(adj.keys())
        if not nodes:
            return {}
        # Initialise with uniform scores.
        scores = {a: 1.0 / len(nodes) for a in nodes}
        for _ in range(_POWER_ITERATIONS):
            new_scores: Dict[str, float] = {a: 0.0 for a in nodes}
            for a, neighbors in adj.items():
                contribution = 0.0
                for b in neighbors:
                    contribution += scores.get(b, 0.0)
                new_scores[a] = contribution
            # Re-normalise to unit sum to keep the iteration stable.
            total = sum(new_scores.values())
            if total <= 0:
                break
            scores = {a: v / total for a, v in new_scores.items()}
        return self._normalise_to_unit(scores)

    def _pagerank_centrality(
        self,
        adj: Dict[str, Set[str]],
    ) -> Dict[str, float]:
        """Compute PageRank-style centrality on the undirected view.

        With damping factor ``_PAGERANK_DAMPING`` the stationary distribution
        is approximated by ``_POWER_ITERATIONS`` power-iteration steps. The
        result is normalised so the maximum score is 1.0.
        """
        nodes = list(adj.keys())
        if not nodes:
            return {}
        damping = _PAGERANK_DAMPING
        n = len(nodes)
        initial = 1.0 / n
        scores = {a: initial for a in nodes}
        for _ in range(_POWER_ITERATIONS):
            new_scores: Dict[str, float] = {a: (1.0 - damping) / n for a in nodes}
            for a, neighbors in adj.items():
                degree = len(neighbors)
                if degree == 0:
                    continue
                share = scores[a] / degree
                for b in neighbors:
                    new_scores[b] += damping * share
            scores = new_scores
        return self._normalise_to_unit(scores)

    def _normalise_to_unit(self, raw: Dict[str, float]) -> Dict[str, float]:
        """Normalise a score map so its maximum becomes 1.0 (or 0.0 if empty)."""
        if not raw:
            return {}
        max_value = max(raw.values())
        if max_value <= 0:
            return {a: 0.0 for a in raw}
        return {a: _clamp(v / max_value) for a, v in raw.items()}

    def _bfs_distances(
        self,
        source: str,
        adj: Dict[str, Set[str]],
    ) -> Dict[str, int]:
        """Return BFS shortest-path distances from ``source`` to every node.

        Unreachable nodes are given distance 0, which the closeness routine
        interprets as "not in the same component" and contributes 0.0.
        """
        distance: Dict[str, int] = {a: 0 for a in adj}
        distance[source] = 0
        visited: Set[str] = {source}
        queue: deque = deque([(source, 0)])
        while queue:
            node, dist = queue.popleft()
            for neighbor in adj.get(node, set()):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                distance[neighbor] = dist + 1
                queue.append((neighbor, dist + 1))
        return distance

    # ------------------------------------------------------------------
    # Community detection
    # ------------------------------------------------------------------

    def detect_communities(
        self,
        algorithm: CommunityAlgorithm,
    ) -> List[Community]:
        """Detect communities in the social graph using the chosen algorithm.

        The cached community store is replaced by the freshly detected
        communities so the latest detection is always reflected in
        :meth:`list_communities` and :meth:`get_community`.
        """
        with self._lock:
            adj = self._undirected_adjacency()
            if algorithm == CommunityAlgorithm.LOUVAIN:
                labels = self._louvain_communities(adj)
            elif algorithm == CommunityAlgorithm.LABEL_PROPAGATION:
                labels = self._label_propagation(adj)
            else:
                labels = self._clique_percolation(adj)

            # Clear previous communities; cache the freshly detected ones.
            self._communities.clear()
            now = _now()
            for idx, (members, internal, external) in enumerate(labels, start=1):
                if not members:
                    continue
                community = Community(
                    community_id=_new_id(),
                    member_ids=sorted(members),
                    internal_edges=internal,
                    external_edges=external,
                    density=self._community_density(members, internal),
                    algorithm=algorithm,
                    modularity=self._modularity_for_community(members, adj),
                )
                self._communities[community.community_id] = community
                self._community_counter += 1
            _evict_fifo_dict(self._communities, _MAX_COMMUNITIES)

            self._record_event(
                SocialNetworkEventKind.COMMUNITY_DETECTED,
                {
                    "algorithm": algorithm.value,
                    "community_count": len(self._communities),
                },
            )
            return list(self._communities.values())

    def get_community(self, community_id: str) -> Optional[Community]:
        """Return a single community by id, or ``None`` if not found."""
        with self._lock:
            return self._communities.get(community_id)

    def list_communities(self) -> List[Community]:
        """Return all currently cached communities."""
        with self._lock:
            return list(self._communities.values())

    def _louvain_communities(
        self,
        adj: Dict[str, Set[str]],
    ) -> List[Tuple[Set[str], int, int]]:
        """Louvain-style greedy modularity optimisation.

        Each node starts in its own community. For a small number of passes,
        nodes are moved to the neighbour community that most improves a
        local modularity estimate. The output is a list of
        ``(members, internal_edges, external_edges)`` tuples.
        """
        nodes = list(adj.keys())
        if not nodes:
            return []
        community_of: Dict[str, int] = {a: i for i, a in enumerate(nodes)}
        # Total degree (sum of weighted degrees; here using unweighted degree).
        total_degree = sum(len(neighbors) for neighbors in adj.values())
        if total_degree == 0:
            return [(set([a]), 0, 0) for a in nodes]

        def degree_of(node: str) -> int:
            """Return the unweighted degree of ``node`` in the undirected view."""
            return len(adj.get(node, set()))

        for _ in range(_LOUVAIN_PASSES):
            moved = False
            for node in nodes:
                current_label = community_of[node]
                # Compute degree contributions to the current community.
                community_nodes: Dict[int, Set[str]] = {}
                for n, lbl in community_of.items():
                    community_nodes.setdefault(lbl, set()).add(n)
                own_community = community_nodes[current_label]
                own_community.discard(node)
                sum_to_current = sum(
                    1 for n in own_community if n in adj.get(node, set())
                )
                k_i = degree_of(node)
                m2 = total_degree * 2
                # Evaluate each neighbour's community.
                best_label = current_label
                best_delta = 0.0
                neighbour_labels: Set[int] = set()
                for n in adj.get(node, set()):
                    neighbour_labels.add(community_of[n])
                for label in neighbour_labels:
                    if label == current_label:
                        continue
                    target_community = community_nodes[label]
                    sum_to_target = sum(
                        1 for n in target_community if n in adj.get(node, set())
                    )
                    sum_tot_target = sum(
                        degree_of(n) for n in target_community
                    )
                    delta = (
                        (sum_to_target / m2)
                        - (sum_tot_target * k_i) / (m2 * m2)
                        - (sum_to_current / m2)
                        + ((sum_tot_target + k_i) * k_i) / (m2 * m2)
                    )
                    if delta > best_delta:
                        best_delta = delta
                        best_label = label
                if best_label != current_label:
                    community_of[node] = best_label
                    moved = True
            if not moved:
                break

        return self._labels_to_communities(community_of, adj)

    def _label_propagation(
        self,
        adj: Dict[str, Set[str]],
    ) -> List[Tuple[Set[str], int, int]]:
        """Asynchronous label propagation community detection.

        Each node is initialised with a unique label, then iterates a
        fixed number of rounds, adopting the most-frequent label of its
        neighbours (deterministic tie-break by label id).
        """
        nodes = list(adj.keys())
        if not nodes:
            return []
        labels: Dict[str, int] = {a: i for i, a in enumerate(nodes)}
        for _ in range(_LABEL_PROPAGATION_ITERATIONS):
            for node in nodes:
                neighbors = adj.get(node, set())
                if not neighbors:
                    continue
                counts: Dict[int, int] = {}
                for n in neighbors:
                    lbl = labels[n]
                    counts[lbl] = counts.get(lbl, 0) + 1
                # Pick the label with the highest count (lowest label id
                # as a deterministic tie-breaker).
                best_label = max(counts.items(), key=lambda pair: (pair[1], -pair[0]))[0]
                labels[node] = best_label
        return self._labels_to_communities(labels, adj)

    def _clique_percolation(
        self,
        adj: Dict[str, Set[str]],
    ) -> List[Tuple[Set[str], int, int]]:
        """Clique-percolation community detection (k-clique merging).

        Finds all k-cliques (``_K_CLIQUE_SIZE``) and merges any two cliques
        that share at least ``k - 1`` members. The result is a list of
        merged communities expressed as ``(members, internal_edges,
        external_edges)`` tuples.
        """
        nodes = list(adj.keys())
        if not nodes:
            return []
        cliques = self._enumerate_k_cliques(nodes, _K_CLIQUE_SIZE, adj)
        # Union-Find for clique merging.
        parent: Dict[int, int] = {i: i for i in range(len(cliques))}

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra == rb:
                return
            parent[ra] = rb

        for i in range(len(cliques)):
            for j in range(i + 1, len(cliques)):
                if len(cliques[i] & cliques[j]) >= _K_CLIQUE_SIZE - 1:
                    union(i, j)
        merged: Dict[int, Set[str]] = {}
        for i, members in enumerate(cliques):
            merged.setdefault(find(i), set()).update(members)
        return self._member_sets_to_communities(merged, adj)

    def _enumerate_k_cliques(
        self,
        nodes: List[str],
        k: int,
        adj: Dict[str, Set[str]],
    ) -> List[Set[str]]:
        """Enumerate all k-cliques via the Bron-Kerbosch-with-pivot algorithm.

        The implementation is a straightforward recursive enumeration that
        collects ``set`` cliques of size ``k``. It is suitable for the
        moderate-sized graphs typically analysed by the engine.
        """
        results: List[Set[str]] = []

        def expand(candidates: Set[str], current: Set[str]) -> None:
            if len(current) == k:
                results.append(set(current))
                return
            if len(current) + len(candidates) < k:
                return
            pivot_candidates = candidates
            # Pick a pivot to bound the search; here we use any single
            # candidate as a simple pivot heuristic.
            for node in list(candidates):
                new_current = set(current)
                new_current.add(node)
                new_candidates = {n for n in candidates if n in adj.get(node, set())}
                expand(new_candidates, new_current)
                candidates.remove(node)

        initial = {n for n in nodes if len(adj.get(n, set())) >= k - 1}
        expand(initial, set())
        return results

    def _labels_to_communities(
        self,
        labels: Dict[str, int],
        adj: Dict[str, Set[str]],
    ) -> List[Tuple[Set[str], int, int]]:
        """Group nodes by integer label into community tuples."""
        groups: Dict[int, Set[str]] = {}
        for node, label in labels.items():
            groups.setdefault(label, set()).add(node)
        return self._member_sets_to_communities(groups, adj)

    def _member_sets_to_communities(
        self,
        groups: Dict[Any, Set[str]],
        adj: Dict[str, Set[str]],
    ) -> List[Tuple[Set[str], int, int]]:
        """Convert member-id sets into ``(members, internal, external)`` tuples."""
        communities: List[Tuple[Set[str], int, int]] = []
        for members in groups.values():
            if not members:
                continue
            internal = 0
            external = 0
            member_list = list(members)
            for i in range(len(member_list)):
                for j in range(i + 1, len(member_list)):
                    a, b = member_list[i], member_list[j]
                    if b in adj.get(a, set()):
                        internal += 1
                    else:
                        external += 1
            communities.append((set(members), internal, external))
        return communities

    def _community_density(
        self,
        members: Iterable[str],
        internal_edges: int,
    ) -> float:
        """Compute the density of a single community.

        Density is ``2 * internal_edges / (n * (n - 1))`` for ``n > 1``,
        and 0.0 for trivial one-node communities.
        """
        n = sum(1 for _ in members)
        if n <= 1:
            return 0.0
        return (2.0 * internal_edges) / float(n * (n - 1))

    def _modularity_for_community(
        self,
        members: Iterable[str],
        adj: Dict[str, Set[str]],
    ) -> float:
        """Compute a modularity contribution estimate for a single community.

        The full modularity requires the partition-level calculation; this
        per-community value is the ``(L_c / m) - (d_c / 2m)^2`` term using
        unweighted degrees and ``m`` being the total edge count.
        """
        members = set(members)
        if not members:
            return 0.0
        total_edges = 0
        for neighbors in adj.values():
            total_edges += len(neighbors)
        m = total_edges // 2
        if m == 0:
            return 0.0
        l_c = 0
        d_c = 0
        for a in members:
            for b in adj.get(a, set()):
                if b in members:
                    l_c += 1
            d_c += len(adj.get(a, set()))
        l_c //= 2
        return round((l_c / m) - ((d_c / (2.0 * m)) ** 2), 6)

    # ------------------------------------------------------------------
    # Clique analysis
    # ------------------------------------------------------------------

    def find_cliques(
        self,
        clique_type: CliqueType,
        min_size: int = 3,
    ) -> List[Clique]:
        """Find cliques in the social graph of the requested type.

        ``MAXIMAL`` cliques are stored as-is; ``MAXIMUM`` returns only the
        cliques of largest size; ``K_CLIQUE`` returns every clique of size
        exactly ``min_size``.
        """
        with self._lock:
            adj = self._undirected_adjacency()
            nodes = list(adj.keys())
            if not nodes:
                return []

            # Enumerate all maximal cliques via Bron-Kerbosch with pivoting.
            maximal = self._enumerate_maximal_cliques(nodes, adj)
            minimal = max(2, int(min_size))
            maximal = [set(c) for c in maximal if len(c) >= minimal]

            # Clear previous cliques and re-store the freshly discovered ones.
            self._cliques.clear()
            results: List[Clique] = []
            if clique_type == CliqueType.K_CLIQUE:
                all_k_cliques: List[Set[str]] = []
                for clique in maximal:
                    all_k_cliques.extend(
                        self._subsets_of_size(clique, minimal)
                    )
                target_sets = all_k_cliques
            elif clique_type == CliqueType.MAXIMUM:
                if not maximal:
                    target_sets = []
                else:
                    max_size = max(len(c) for c in maximal)
                    target_sets = [c for c in maximal if len(c) == max_size]
            else:  # MAXIMAL
                target_sets = maximal

            now = _now()
            for members in target_sets:
                if not members:
                    continue
                size = len(members)
                edge_count = (size * (size - 1)) // 2
                clique = Clique(
                    clique_id=_new_id(),
                    member_ids=sorted(members),
                    size=size,
                    edge_count=edge_count,
                    density=1.0,
                    clique_type=clique_type,
                )
                self._cliques[clique.clique_id] = clique
                results.append(clique)
                self._clique_counter += 1
            _evict_fifo_dict(self._cliques, _MAX_CLIQUES)
            self._record_event(
                SocialNetworkEventKind.CLIQUE_FOUND,
                {
                    "clique_type": clique_type.value,
                    "clique_count": len(results),
                    "min_size": minimal,
                },
            )
            return results

    def get_clique(self, clique_id: str) -> Optional[Clique]:
        """Return a single clique by id, or ``None`` if not found."""
        with self._lock:
            return self._cliques.get(clique_id)

    def list_cliques(self, min_size: int = 3) -> List[Clique]:
        """List all currently cached cliques with at least ``min_size`` members."""
        with self._lock:
            return [c for c in self._cliques.values() if c.size >= max(2, int(min_size))]

    def _enumerate_maximal_cliques(
        self,
        nodes: List[str],
        adj: Dict[str, Set[str]],
    ) -> List[Set[str]]:
        """Enumerate maximal cliques using Bron-Kerbosch with pivoting."""
        results: List[Set[str]] = []

        def bron_kerbosch(r: Set[str], p: Set[str], x: Set[str]) -> None:
            if not p and not x:
                results.append(set(r))
                return
            pivot = max(p | x, key=lambda n: len(p & adj.get(n, set())))
            for node in list(p - adj.get(pivot, set())):
                neighbors = adj.get(node, set())
                bron_kerbosch(
                    r | {node},
                    p & neighbors,
                    x & neighbors,
                )
                p.remove(node)
                x.add(node)

        bron_kerbosch(set(), set(nodes), set())
        return results

    def _subsets_of_size(
        self,
        members: Set[str],
        size: int,
    ) -> List[Set[str]]:
        """Return every subset of ``members`` with exactly ``size`` elements."""
        items = sorted(members)
        total = len(items)
        if size > total:
            return []

        def recurse(start: int, current: List[str]) -> List[Set[str]]:
            if len(current) == size:
                return [set(current)]
            if start >= total:
                return []
            out: List[Set[str]] = []
            # Include current.
            out.extend(recurse(start + 1, current + [items[start]]))
            # Exclude current.
            out.extend(recurse(start + 1, current))
            return out

        return recurse(0, [])

    # ------------------------------------------------------------------
    # Network metrics
    # ------------------------------------------------------------------

    def compute_metric(self, metric_type: NetworkMetric) -> NetworkMetricReport:
        """Compute a single network-level metric and cache the result."""
        with self._lock:
            if metric_type == NetworkMetric.DENSITY:
                value, details = self._compute_density()
            elif metric_type == NetworkMetric.DIAMETER:
                value, details = self._compute_diameter()
            elif metric_type == NetworkMetric.AVERAGE_PATH_LENGTH:
                value, details = self._compute_average_path_length()
            elif metric_type == NetworkMetric.CLUSTERING_COEFFICIENT:
                value, details = self._compute_clustering_coefficient()
            else:  # ASSORTATIVITY
                value, details = self._compute_assortativity()
            report = NetworkMetricReport(
                metric_type=metric_type,
                value=round(value, 6),
                computed_at=_now(),
                details=details,
            )
            self._metrics[metric_type.value] = report
            self._metric_counter += 1
            _evict_fifo_dict(self._metrics, _MAX_METRICS)
            self._record_event(
                SocialNetworkEventKind.METRIC_COMPUTED,
                {
                    "metric_type": metric_type.value,
                    "value": report.value,
                },
            )
            return report

    def compute_all_metrics(self) -> List[NetworkMetricReport]:
        """Compute every supported network metric and return the reports."""
        with self._lock:
            return [
                self.compute_metric(metric)
                for metric in (
                    NetworkMetric.DENSITY,
                    NetworkMetric.DIAMETER,
                    NetworkMetric.AVERAGE_PATH_LENGTH,
                    NetworkMetric.CLUSTERING_COEFFICIENT,
                    NetworkMetric.ASSORTATIVITY,
                )
            ]

    def _compute_density(self) -> Tuple[float, Dict[str, Any]]:
        """Compute the density of the undirected view of the social graph.

        Density is ``2 * |E| / (n * (n - 1))`` for ``n > 1``.
        """
        nodes = list(self._agents.keys())
        n = len(nodes)
        if n <= 1:
            return 0.0, {"nodes": n, "edges": 0, "max_edges": 0}
        edge_count = sum(1 for e in self._edges.values())
        max_edges = n * (n - 1)
        return (2.0 * edge_count) / float(max_edges), {
            "nodes": n,
            "edges": edge_count,
            "max_edges": max_edges,
        }

    def _compute_diameter(self) -> Tuple[float, Dict[str, Any]]:
        """Compute the longest shortest path over all node pairs.

        For disconnected graphs the diameter is reported over the largest
        connected component; the component size is included in details.
        """
        adj = self._undirected_adjacency()
        nodes = list(adj.keys())
        if not nodes:
            return 0.0, {"nodes": 0, "components": 0}
        max_distance = 0
        largest_component = 0
        components = 0
        for source in nodes:
            distances = self._bfs_distances(source, adj)
            reachable = [d for d in distances.values() if d > 0]
            if not reachable:
                continue
            components += 1
            local_max = max(reachable)
            if local_max > max_distance:
                max_distance = local_max
            if len(reachable) > largest_component:
                largest_component = len(reachable)
        return float(max_distance), {
            "nodes": len(nodes),
            "components": components,
            "largest_component_size": largest_component,
        }

    def _compute_average_path_length(self) -> Tuple[float, Dict[str, Any]]:
        """Compute the average shortest-path length over connected pairs."""
        adj = self._undirected_adjacency()
        nodes = list(adj.keys())
        if not nodes:
            return 0.0, {"nodes": 0}
        total_distance = 0
        pair_count = 0
        for source in nodes:
            distances = self._bfs_distances(source, adj)
            for d in distances.values():
                if d > 0:
                    total_distance += d
                    pair_count += 1
        average = _safe_div(total_distance, pair_count)
        return average, {
            "nodes": len(nodes),
            "connected_pairs": pair_count,
        }

    def _compute_clustering_coefficient(self) -> Tuple[float, Dict[str, Any]]:
        """Compute the average local clustering coefficient.

        Local clustering coefficient of node ``v`` is the fraction of pairs
        of ``v``'s neighbours that are themselves connected. The result is
        the mean across all nodes (zero for isolated nodes).
        """
        adj = self._undirected_adjacency()
        if not adj:
            return 0.0, {"nodes": 0}
        total = 0.0
        per_node: Dict[str, float] = {}
        for node, neighbors in adj.items():
            k = len(neighbors)
            if k < 2:
                per_node[node] = 0.0
                continue
            links = 0
            neighbor_list = list(neighbors)
            for i in range(len(neighbor_list)):
                for j in range(i + 1, len(neighbor_list)):
                    a, b = neighbor_list[i], neighbor_list[j]
                    if b in adj.get(a, set()):
                        links += 1
            coefficient = (2.0 * links) / float(k * (k - 1))
            per_node[node] = coefficient
            total += coefficient
        return total / len(adj), {
            "nodes": len(adj),
            "per_node": {n: round(v, 6) for n, v in per_node.items()},
        }

    def _compute_assortativity(self) -> Tuple[float, Dict[str, Any]]:
        """Compute degree assortativity via the standard Pearson formula.

        Uses the unweighted undirected degree sequence. Returns 0.0 for
        trivial or fully uniform degree sequences.
        """
        adj = self._undirected_adjacency()
        nodes = list(adj.keys())
        if not nodes:
            return 0.0, {"nodes": 0}
        degrees = [len(adj.get(n, set())) for n in nodes]
        n = len(degrees)
        if n < 2:
            return 0.0, {"nodes": n}
        mean_degree = sum(degrees) / n
        if mean_degree == 0:
            return 0.0, {"nodes": n, "mean_degree": 0.0}
        # Compute via the edge-list formulation.
        edge_endpoints: List[Tuple[int, int]] = []
        for a, neighbors in adj.items():
            for b in neighbors:
                if a < b:
                    edge_endpoints.append((len(adj.get(a, set())), len(adj.get(b, set()))))
        m = len(edge_endpoints)
        if m == 0:
            return 0.0, {"nodes": n, "edges": 0}
        sum1 = sum(d_a + d_b for d_a, d_b in edge_endpoints)
        sum2 = sum(d_a * d_b for d_a, d_b in edge_endpoints)
        sum3 = sum((d_a + d_b) ** 2 for d_a, d_b in edge_endpoints)
        numerator = (
            (sum2 / m)
            - (sum1 / (2.0 * m)) ** 2
        )
        denominator = (
            (sum3 / (2.0 * m))
            - (sum1 / (2.0 * m)) ** 2
        )
        if denominator == 0:
            return 0.0, {"nodes": n, "edges": m}
        return numerator / denominator, {
            "nodes": n,
            "edges": m,
            "mean_degree": round(mean_degree, 6),
        }

    # ------------------------------------------------------------------
    # Influence profiles
    # ------------------------------------------------------------------

    def compute_influence(self, agent_id: str) -> InfluenceProfile:
        """Compute a combined influence profile for an agent.

        The influence score combines betweenness, PageRank, and the number
        of communities the agent participates in. Agents that are missing
        from the graph receive a zero-valued profile.
        """
        with self._lock:
            if agent_id not in self._agents:
                profile = InfluenceProfile(
                    agent_id=agent_id,
                    influence_score=0.0,
                    betweenness=0.0,
                    pagerank=0.0,
                    community_count=0,
                    influence_level=InfluenceLevel.LOW,
                    computed_at=_now(),
                )
                self._influences[agent_id] = profile
                self._influence_counter += 1
                _evict_fifo_dict(self._influences, _MAX_INFLUENCES)
                return profile

            adj = self._undirected_adjacency()
            betweenness_map = self._betweenness_centrality(adj)
            pagerank_map = self._pagerank_centrality(adj)
            betweenness = betweenness_map.get(agent_id, 0.0)
            pagerank = pagerank_map.get(agent_id, 0.0)
            community_count = sum(
                1 for c in self._communities.values() if agent_id in c.member_ids
            )
            # Influence = 0.5 * betweenness + 0.4 * pagerank + 0.1 * min(community_count, 5) / 5
            community_term = min(community_count, 5) / 5.0
            influence_score = _clamp(
                0.5 * betweenness + 0.4 * pagerank + 0.1 * community_term
            )
            profile = InfluenceProfile(
                agent_id=agent_id,
                influence_score=round(influence_score, 6),
                betweenness=round(betweenness, 6),
                pagerank=round(pagerank, 6),
                community_count=community_count,
                influence_level=self._influence_level(influence_score),
                computed_at=_now(),
            )
            self._influences[agent_id] = profile
            self._influence_counter += 1
            _evict_fifo_dict(self._influences, _MAX_INFLUENCES)
            return profile

    def rank_by_influence(self, limit: int = 10) -> List[InfluenceProfile]:
        """Compute influence for every agent and return the top ``limit``."""
        with self._lock:
            profiles = [self.compute_influence(a) for a in self._agents]
            profiles.sort(
                key=lambda p: (-p.influence_score, p.agent_id),
            )
            n = max(0, int(limit))
            return profiles[:n] if n > 0 else profiles

    def _influence_level(self, score: float) -> InfluenceLevel:
        """Map a continuous influence score to a discrete level."""
        if score < 0.2:
            return InfluenceLevel.LOW
        if score < 0.5:
            return InfluenceLevel.MEDIUM
        if score < 0.8:
            return InfluenceLevel.HIGH
        return InfluenceLevel.INFLUENTIAL

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: SocialNetworkEventKind,
        payload: Dict[str, Any],
    ) -> None:
        """Record an observable social network event.

        Assumes the caller already holds ``self._lock``. The event log is
        bounded by ``_MAX_EVENTS`` with FIFO eviction.
        """
        event = SocialNetworkEvent(
            event_id=_new_id(),
            kind=kind,
            timestamp=_now(),
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, limit: int = 100) -> List[SocialNetworkEvent]:
        """Return the most recent events, newest first."""
        with self._lock:
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(self._events))[:n]

    def get_stats(self) -> SocialNetworkStats:
        """Return aggregate statistics about the social network engine."""
        with self._lock:
            agents = list(self._agents.values())
            edges = list(self._edges.values())
            n = len(agents)
            total_undirected_edges = 0
            degree_counts: Dict[str, int] = {a.agent_id: 0 for a in agents}
            for edge in edges:
                total_undirected_edges += 1
                degree_counts[edge.source_id] = degree_counts.get(edge.source_id, 0) + 1
                if edge.bidirectional:
                    degree_counts[edge.target_id] = degree_counts.get(edge.target_id, 0) + 1
                else:
                    # In directed edges, count the target as reachable but
                    # do not double-count degree unless the edge is treated
                    # as bidirectional. We do not penalise directed edges
                    # for the purpose of this aggregate.
                    pass
            max_degree = max(degree_counts.values()) if degree_counts else 0
            avg_degree = (
                sum(degree_counts.values()) / n if n > 0 else 0.0
            )
            density = 0.0
            if n > 1:
                density = (2.0 * total_undirected_edges) / float(n * (n - 1))
            return SocialNetworkStats(
                total_agents=n,
                total_edges=len(edges),
                total_communities=len(self._communities),
                total_cliques=len(self._cliques),
                density=round(density, 6),
                avg_degree=round(avg_degree, 4),
                max_degree=max_degree,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics."""
        with self._lock:
            stats = self.get_stats()
            status: Dict[str, Any] = {
                "initialized": self._initialized,
                "total_agents": stats.total_agents,
                "total_edges": stats.total_edges,
                "total_communities": stats.total_communities,
                "total_cliques": stats.total_cliques,
                "total_centralities": len(self._centralities),
                "total_metrics": len(self._metrics),
                "total_influences": len(self._influences),
                "total_events": len(self._events),
                "counters": {
                    "edge_counter": self._edge_counter,
                    "centrality_counter": self._centrality_counter,
                    "community_counter": self._community_counter,
                    "clique_counter": self._clique_counter,
                    "metric_counter": self._metric_counter,
                    "influence_counter": self._influence_counter,
                },
                "stats": stats.to_dict(),
                "capacities": {
                    "max_agents": _MAX_AGENTS,
                    "max_edges": _MAX_EDGES,
                    "max_centralities": _MAX_CENTRALITIES,
                    "max_communities": _MAX_COMMUNITIES,
                    "max_cliques": _MAX_CLIQUES,
                    "max_metrics": _MAX_METRICS,
                    "max_influences": _MAX_INFLUENCES,
                    "max_events": _MAX_EVENTS,
                },
                "algorithm_constants": {
                    "power_iterations": _POWER_ITERATIONS,
                    "pagerank_damping": _PAGERANK_DAMPING,
                    "louvain_passes": _LOUVAIN_PASSES,
                    "label_propagation_iterations": _LABEL_PROPAGATION_ITERATIONS,
                    "k_clique_size": _K_CLIQUE_SIZE,
                },
            }
            return status

    def get_snapshot(self) -> SocialNetworkSnapshot:
        """Return a complete snapshot of the social network engine state."""
        with self._lock:
            return SocialNetworkSnapshot(
                initialized=self._initialized,
                agents=list(self._agents.values()),
                edges=list(self._edges.values()),
                centralities=list(self._centralities.values()),
                communities=list(self._communities.values()),
                cliques=list(self._cliques.values()),
                metrics=list(self._metrics.values()),
                events=list(self._events),
                stats=self.get_stats(),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all tracked state and re-seed baseline data.

        Unlike some sibling engines, this method re-seeds the baseline
        social graph after clearing, restoring the engine to a freshly
        initialized state.
        """
        with self._lock:
            self._agents.clear()
            self._edges.clear()
            self._out_neighbors.clear()
            self._in_neighbors.clear()
            self._centralities.clear()
            self._communities.clear()
            self._cliques.clear()
            self._metrics.clear()
            self._influences.clear()
            self._events.clear()
            self._edge_counter = 0
            self._centrality_counter = 0
            self._community_counter = 0
            self._clique_counter = 0
            self._metric_counter = 0
            self._influence_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline SparkLabs social network data.

        Seeds two clearly-separated communities (warriors and mages) of
        four agents each with dense internal edges, plus two bridge edges
        linking the two communities. A small selection of analysis results
        is pre-computed so the engine is immediately queryable.
        """
        # --- Agents ----------------------------------------------------
        warrior_ids = ["w1", "w2", "w3", "w4"]
        mage_ids = ["m1", "m2", "m3", "m4"]
        for wid in warrior_ids:
            self._ensure_agent_locked(wid)
        for mid in mage_ids:
            self._ensure_agent_locked(mid)

        # --- Edges: dense intra-community connections ------------------
        # Warriors: complete graph minus a single edge to keep it interesting.
        warrior_edges = [
            ("w1", "w2", 1.0),
            ("w1", "w3", 1.0),
            ("w1", "w4", 0.8),
            ("w2", "w3", 1.0),
            ("w2", "w4", 0.8),
            ("w3", "w4", 0.8),
        ]
        for a, b, w in warrior_edges:
            self.add_edge(a, b, weight=w, relationship_type="ally", bidirectional=True)

        # Mages: complete graph with one less dense edge.
        mage_edges = [
            ("m1", "m2", 1.0),
            ("m1", "m3", 1.0),
            ("m1", "m4", 0.8),
            ("m2", "m3", 0.8),
            ("m2", "m4", 0.8),
            ("m3", "m4", 0.8),
        ]
        for a, b, w in mage_edges:
            self.add_edge(a, b, weight=w, relationship_type="ally", bidirectional=True)

        # --- Bridge edges between the two communities -----------------
        self.add_edge("w1", "m1", weight=0.5, relationship_type="rival", bidirectional=True)
        self.add_edge("w3", "m2", weight=0.4, relationship_type="rival", bidirectional=True)

        # --- Pre-computed analysis results -----------------------------
        # Detect a single Louvain community partition to demonstrate the
        # analysis pipeline without requiring external calls.
        self.detect_communities(CommunityAlgorithm.LOUVAIN)
        # Enumerate maximal cliques of size 3+ so the engine returns
        # at least one clique in its snapshot out of the box.
        self.find_cliques(CliqueType.MAXIMAL, min_size=3)


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_social_network_analysis() -> SocialNetworkAnalysisEngine:
    """Return the singleton SocialNetworkAnalysisEngine instance."""
    return SocialNetworkAnalysisEngine.get_instance()
