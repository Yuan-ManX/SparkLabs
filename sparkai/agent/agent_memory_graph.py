"""
SparkLabs Agent - Memory Graph

Cross-session persistent memory with vector embeddings simulation, knowledge graph
construction, semantic search, and context-aware retrieval for long-running AI agents.
Provides intelligent memory consolidation that strengthens important memories and
prunes stale ones, maintaining a high-quality knowledge base over time.

Architecture:
  AgentMemoryGraph (Singleton)
    |-- MemoryNode (discrete memory units with embeddings)
    |-- MemoryEdge (typed relationships between nodes)
    |-- KnowledgeGraph (composite view of nodes and edges)
    |-- SearchQuery (parameterized retrieval requests)
    |-- RetrievalResult (scored and ranked matches)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MemoryCategory(Enum):
    FACT = "fact"
    CONCEPT = "concept"
    RELATION = "relation"
    EVENT = "event"
    PROCEDURE = "procedure"
    PREFERENCE = "preference"
    INSIGHT = "insight"


class RelationType(Enum):
    RELATES_TO = "relates_to"
    PRECEDES = "precedes"
    CAUSES = "causes"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    REFINES = "refines"
    DEPENDS_ON = "depends_on"


class MemoryStrength(Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    CORE = "core"
    ETERNAL = "eternal"


class SearchStrategy(Enum):
    EXACT = "exact"
    SEMANTIC = "semantic"
    TEMPORAL = "temporal"
    GRAPH_WALK = "graph_walk"
    HYBRID = "hybrid"


@dataclass
class MemoryNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    category: MemoryCategory = MemoryCategory.FACT
    content: str = ""
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5
    session_id: str = ""
    embedding_sim: float = 0.0
    strength: MemoryStrength = MemoryStrength.MODERATE
    access_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "category": self.category.value, "content": self.content,
            "tags": list(self.tags), "importance": round(self.importance, 4),
            "session_id": self.session_id,
            "embedding_sim": round(self.embedding_sim, 4),
            "strength": self.strength.value, "access_count": self.access_count,
            "created_at": self.created_at, "last_accessed_at": self.last_accessed_at,
        }

@dataclass
class MemoryEdge:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.RELATES_TO
    weight: float = 0.5
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "source_id": self.source_id, "target_id": self.target_id,
            "relation_type": self.relation_type.value, "weight": round(self.weight, 4),
            "created_at": self.created_at,
        }

@dataclass
class KnowledgeGraph:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_ids: List[str] = field(default_factory=list)
    edge_ids: List[str] = field(default_factory=list)
    root_id: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "node_ids": list(self.node_ids),
            "edge_ids": list(self.edge_ids),
            "node_count": len(self.node_ids), "edge_count": len(self.edge_ids),
            "root_id": self.root_id, "created_at": self.created_at,
        }

@dataclass
class SearchQuery:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    query_text: str = ""
    strategy: SearchStrategy = SearchStrategy.SEMANTIC
    max_results: int = 10
    min_relevance: float = 0.3
    categories: List[MemoryCategory] = field(default_factory=list)
    session_id: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "query_text": self.query_text,
            "strategy": self.strategy.value, "max_results": self.max_results,
            "min_relevance": self.min_relevance,
            "categories": [c.value for c in self.categories],
            "session_id": self.session_id, "created_at": self.created_at,
        }

@dataclass
class RetrievalResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_id: str = ""
    relevance_score: float = 0.0
    match_type: str = ""
    retrieval_timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "node_id": self.node_id,
            "relevance_score": round(self.relevance_score, 4),
            "match_type": self.match_type,
            "retrieval_timestamp": self.retrieval_timestamp,
        }


class AgentMemoryGraph:
    """Cross-session persistent memory graph with vector embeddings and semantic search."""

    _instance: Optional["AgentMemoryGraph"] = None
    _lock = threading.RLock()

    _STRENGTH_SCORE: Dict[MemoryStrength, float] = {
        MemoryStrength.WEAK: 0.1,
        MemoryStrength.MODERATE: 0.4,
        MemoryStrength.STRONG: 0.7,
        MemoryStrength.CORE: 0.9,
        MemoryStrength.ETERNAL: 1.0,
    }

    _STRENGTH_MERGE_THRESHOLD: float = 0.35
    _CONSOLIDATION_SIMILARITY_THRESHOLD: float = 0.7
    _STRENGTH_ORDERING: List[MemoryStrength] = [
        MemoryStrength.WEAK, MemoryStrength.MODERATE, MemoryStrength.STRONG,
        MemoryStrength.CORE, MemoryStrength.ETERNAL,
    ]

    def __init__(self) -> None:
        self._nodes: Dict[str, MemoryNode] = {}
        self._edges: Dict[str, MemoryEdge] = {}
        self._session_indices: Dict[str, List[str]] = {}
        self._search_history: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "AgentMemoryGraph":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Node & Edge ----
    def add_node(self, category: str, content: str,
                 tags: Optional[List[str]] = None,
                 importance: float = 0.5,
                 session_id: str = "",
                 embedding_sim: float = 0.0) -> MemoryNode:
        try:
            cat = MemoryCategory(category.lower())
        except ValueError:
            cat = MemoryCategory.FACT
        node = MemoryNode(category=cat, content=content,
                          tags=tags or [],
                          importance=min(1.0, max(0.0, importance)),
                          session_id=session_id,
                          embedding_sim=min(1.0, max(0.0, embedding_sim)),
                          strength=self._derive_strength(importance))
        self._nodes[node.id] = node
        if session_id:
            self._session_indices.setdefault(session_id, []).append(node.id)
        return node

    def add_edge(self, source_id: str, target_id: str,
                 relation_type: str = "relates_to",
                 weight: float = 0.5) -> Optional[MemoryEdge]:
        if source_id not in self._nodes or target_id not in self._nodes:
            return None
        try:
            rel = RelationType(relation_type.lower())
        except ValueError:
            rel = RelationType.RELATES_TO
        edge = MemoryEdge(source_id=source_id, target_id=target_id,
                          relation_type=rel,
                          weight=min(1.0, max(0.0, weight)))
        self._edges[edge.id] = edge
        return edge

    # ---- Search & Retrieval ----

    def search(self, query: str, strategy: str = "semantic",
               max_results: int = 10, min_relevance: float = 0.3,
               categories: Optional[List[str]] = None) -> List[RetrievalResult]:
        try:
            strat = SearchStrategy(strategy.lower())
        except ValueError:
            strat = SearchStrategy.SEMANTIC
        target_cats: List[MemoryCategory] = list(MemoryCategory)
        if categories:
            target_cats = []
            for c in categories:
                try:
                    target_cats.append(MemoryCategory(c.lower()))
                except ValueError:
                    pass
        sq = SearchQuery(query_text=query, strategy=strat, max_results=max_results,
                         min_relevance=min_relevance, categories=target_cats)
        results: List[RetrievalResult] = []
        now = time.time()
        for node in self._nodes.values():
            if node.category not in target_cats:
                continue
            rel = self._score_node(node, query, strat)
            if rel >= min_relevance:
                results.append(RetrievalResult(node_id=node.id, relevance_score=rel,
                                               match_type=strat.value))
                node.access_count += 1
                node.last_accessed_at = now
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        trimmed = results[:max_results]
        self._search_history.append({
            "query_id": sq.id, "query_text": query,
            "results_count": len(trimmed), "timestamp": now,
        })
        return trimmed

    def graph_walk(self, start_node_id: str, max_depth: int = 3,
                   relation_filter: Optional[str] = None,
                   max_nodes: int = 50) -> List[MemoryNode]:
        if start_node_id not in self._nodes:
            return []
        visited: set = {start_node_id}
        frontier: List[tuple] = [(start_node_id, 0)]
        result: List[MemoryNode] = [self._nodes[start_node_id]]
        rel_type: Optional[RelationType] = None
        if relation_filter:
            try:
                rel_type = RelationType(relation_filter.lower())
            except ValueError:
                pass
        while frontier and len(result) < max_nodes:
            cur, depth = frontier.pop(0)
            if depth >= max_depth:
                continue
            for nb in self._get_neighbors(cur, rel_type):
                if nb not in visited and len(result) < max_nodes:
                    visited.add(nb)
                    result.append(self._nodes[nb])
                    frontier.append((nb, depth + 1))
        now = time.time()
        for node in result:
            node.access_count += 1
            node.last_accessed_at = now
        return result

    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        node_ids = self._session_indices.get(session_id, [])
        nodes = [self._nodes[nid] for nid in node_ids if nid in self._nodes]
        if not nodes:
            return {"session_id": session_id, "node_count": 0, "nodes": []}
        categories: Dict[str, int] = {}
        total_importance = 0.0
        for node in nodes:
            categories[node.category.value] = categories.get(node.category.value, 0) + 1
            total_importance += node.importance
        return {
            "session_id": session_id, "node_count": len(nodes),
            "nodes": [n.to_dict() for n in nodes], "categories": categories,
            "avg_importance": round(total_importance / len(nodes), 4),
            "earliest_at": min(n.created_at for n in nodes),
            "latest_at": max(n.created_at for n in nodes),
        }

    # ---- Memory Lifecycle ----

    def consolidate_memories(self, older_than_seconds: float = 3600.0) -> Dict[str, Any]:
        now = time.time()
        cutoff = now - older_than_seconds
        merged, strengthened = 0, 0
        old = [n for n in self._nodes.values() if n.created_at <= cutoff]
        for i, a in enumerate(old):
            if a.id not in self._nodes:
                continue
            for b in old[i + 1:]:
                if b.id not in self._nodes or a.category != b.category:
                    continue
                if self._compute_similarity(a, b) >= self._CONSOLIDATION_SIMILARITY_THRESHOLD:
                    if self._STRENGTH_SCORE[b.strength] <= self._STRENGTH_MERGE_THRESHOLD:
                        merged += self._merge_nodes(a, b)
                    else:
                        self._strengthen_node(a)
                        strengthened += 1
        for node in [n for n in self._nodes.values() if n.access_count >= 10]:
            if self._STRENGTH_SCORE[node.strength] < self._STRENGTH_SCORE[MemoryStrength.STRONG]:
                self._strengthen_node(node)
                strengthened += 1
        return {
            "consolidated_at": now, "merged_count": merged,
            "strengthened_count": strengthened, "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
        }

    def forget_stale(self, threshold_strength: str = "weak",
                     max_age_seconds: float = 86400.0) -> int:
        try:
            thresh = MemoryStrength(threshold_strength.lower())
        except ValueError:
            thresh = MemoryStrength.WEAK
        cutoff = time.time() - max_age_seconds
        to_remove = [nid for nid, n in self._nodes.items()
                     if self._STRENGTH_SCORE[n.strength] <= self._STRENGTH_SCORE[thresh]
                     and n.last_accessed_at <= cutoff]
        self._remove_nodes(to_remove)
        return len(to_remove)

    # ---- Export & Statistics ----

    def export_subgraph(self, root_id: str, depth: int = 2) -> Dict[str, Any]:
        if root_id not in self._nodes:
            return {"root_id": root_id, "node_count": 0, "edge_count": 0, "nodes": [], "edges": []}
        vnodes = self.graph_walk(root_id, max_depth=depth)
        vids = {n.id for n in vnodes}
        sedges = [e.to_dict() for e in self._edges.values() if e.source_id in vids and e.target_id in vids]
        return {
            "root_id": root_id, "node_count": len(vnodes), "edge_count": len(sedges),
            "nodes": [n.to_dict() for n in vnodes], "edges": sedges,
        }

    def get_stats(self) -> Dict[str, Any]:
        cat_counts: Dict[str, int] = {}
        str_counts: Dict[str, int] = {}
        rel_counts: Dict[str, int] = {}
        total_access, total_importance = 0, 0.0
        for node in self._nodes.values():
            cat_counts[node.category.value] = cat_counts.get(node.category.value, 0) + 1
            str_counts[node.strength.value] = str_counts.get(node.strength.value, 0) + 1
            total_access += node.access_count
            total_importance += node.importance
        for edge in self._edges.values():
            rel_counts[edge.relation_type.value] = rel_counts.get(edge.relation_type.value, 0) + 1
        nc = len(self._nodes)
        avg_weight = sum(e.weight for e in self._edges.values()) / max(1, len(self._edges))
        return {
            "total_nodes": nc, "total_edges": len(self._edges),
            "total_sessions": len(self._session_indices),
            "nodes_by_category": cat_counts, "nodes_by_strength": str_counts,
            "edges_by_relation": rel_counts, "avg_edge_weight": round(avg_weight, 4),
            "avg_importance": round(total_importance / nc, 4) if nc else 0.0,
            "total_access_count": total_access,
            "avg_access_per_node": round(total_access / nc, 1) if nc else 0.0,
            "search_history_entries": len(self._search_history),
        }

    def compute_node_importance(self, node_id: str) -> float:
        node = self._nodes.get(node_id)
        if node is None:
            return 0.0
        edge_count, total_weight = 0, 0.0
        for edge in self._edges.values():
            if edge.source_id == node_id or edge.target_id == node_id:
                edge_count += 1
                total_weight += edge.weight
        age_days = (time.time() - node.created_at) / 86400.0
        recency_factor = 1.0 / (1.0 + age_days * 0.1)
        access_factor = math.log1p(node.access_count) / math.log1p(100)
        connectedness = min(1.0, edge_count / 20.0)
        weight_factor = min(1.0, total_weight / max(1, edge_count))
        score = (0.25 * connectedness + 0.20 * weight_factor + 0.20
                 * self._STRENGTH_SCORE[node.strength] + 0.20 * recency_factor
                 + 0.15 * access_factor)
        return round(min(1.0, score), 4)

    # ---- Internal Helpers ----

    @staticmethod
    def _derive_strength(importance: float) -> MemoryStrength:
        if importance >= 0.9:
            return MemoryStrength.CORE
        if importance >= 0.7:
            return MemoryStrength.STRONG
        if importance >= 0.4:
            return MemoryStrength.MODERATE
        return MemoryStrength.WEAK

    def _score_node(self, node: MemoryNode, query: str, strategy: SearchStrategy) -> float:
        ql = query.lower()
        cl = node.content.lower()
        score = 0.0
        if strategy in (SearchStrategy.EXACT, SearchStrategy.HYBRID):
            if ql in cl:
                score += 0.5
            for tag in node.tags:
                if ql in tag.lower():
                    score += 0.15
        if strategy in (SearchStrategy.SEMANTIC, SearchStrategy.HYBRID):
            score += node.embedding_sim * 0.4 + self._token_overlap(ql, cl) * 0.3
        if strategy == SearchStrategy.TEMPORAL:
            recency = 1.0 / (1.0 + (time.time() - node.created_at) / 86400.0)
            score += recency * 0.4 + node.importance * 0.3
        score += node.importance * 0.1
        return round(min(1.0, score), 4)

    @staticmethod
    def _token_overlap(a: str, b: str) -> float:
        tokens_a = set(a.lower().split())
        tokens_b = set(b.lower().split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        return len(intersection) / max(len(tokens_a), len(tokens_b))

    def _get_neighbors(self, node_id: str,
                       relation_filter: Optional[RelationType] = None) -> List[str]:
        result: List[str] = []
        for edge in self._edges.values():
            if relation_filter is not None and edge.relation_type != relation_filter:
                continue
            if edge.source_id == node_id:
                result.append(edge.target_id)
            elif edge.target_id == node_id:
                result.append(edge.source_id)
        return result

    def _compute_similarity(self, a: MemoryNode, b: MemoryNode) -> float:
        to = 0.0
        if a.tags and b.tags:
            sa, sb = set(a.tags), set(b.tags)
            to = len(sa & sb) / max(len(sa), len(sb))
        return 0.6 * self._token_overlap(a.content, b.content) + 0.4 * to

    def _merge_nodes(self, survivor: MemoryNode, absorbed: MemoryNode) -> int:
        if absorbed.id not in self._nodes:
            return 0
        survivor.access_count += absorbed.access_count
        survivor.last_accessed_at = max(survivor.last_accessed_at, absorbed.last_accessed_at)
        survivor.importance = max(survivor.importance, absorbed.importance)
        survivor.tags = list(set(survivor.tags + absorbed.tags))
        survivor.embedding_sim = (survivor.embedding_sim + absorbed.embedding_sim) / 2.0
        for edge in list(self._edges.values()):
            if edge.source_id == absorbed.id:
                self._edges[uuid.uuid4().hex] = MemoryEdge(
                    source_id=survivor.id, target_id=edge.target_id,
                    relation_type=edge.relation_type, weight=edge.weight)
            elif edge.target_id == absorbed.id:
                self._edges[uuid.uuid4().hex] = MemoryEdge(
                    source_id=edge.source_id, target_id=survivor.id,
                    relation_type=edge.relation_type, weight=edge.weight)
        for sid, nids in self._session_indices.items():
            if absorbed.id in nids:
                self._session_indices[sid] = [survivor.id if n == absorbed.id else n for n in nids]
        del self._nodes[absorbed.id]
        return 1

    def _strengthen_node(self, node: MemoryNode) -> None:
        idx = self._STRENGTH_ORDERING.index(node.strength) if node.strength in self._STRENGTH_ORDERING else 0
        if idx < len(self._STRENGTH_ORDERING) - 1 and node.strength != MemoryStrength.ETERNAL:
            node.strength = self._STRENGTH_ORDERING[idx + 1]

    def _remove_nodes(self, node_ids: List[str]) -> None:
        remove_set = set(node_ids)
        for nid in node_ids:
            self._nodes.pop(nid, None)
        to_remove = [eid for eid, e in self._edges.items() if e.source_id in remove_set or e.target_id in remove_set]
        for eid in to_remove:
            self._edges.pop(eid, None)
        for sid, nids in self._session_indices.items():
            self._session_indices[sid] = [n for n in nids if n not in remove_set]


def get_memory_graph() -> AgentMemoryGraph:
    return AgentMemoryGraph.get_instance()