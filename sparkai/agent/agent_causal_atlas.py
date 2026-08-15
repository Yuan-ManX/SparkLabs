"""
SparkLabs Agent - Causal Atlas

A causal graph that records cause-effect relationships between world events.
The atlas enables deep "why" reasoning: instead of just observing that the
world changed, the agent can trace the causal chain that led to the change
and reason about what interventions would produce different outcomes.

Each edge in the graph represents a causal link:
    cause_event -> effect_event  (with confidence, temporal delay, context)

The atlas supports:
  - record(cause, effect)     : add a causal edge
  - explain(event)            : trace backward to find root causes
  - predict(action)           : trace forward to find likely effects
  - find_path(a, b)           : find a causal chain from a to b
  - intervene(action, target) : simulate cutting a causal link

This is the deep-reasoning backbone that turns observation into understanding.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CausalEvent:
    """A single event node in the causal graph."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    label: str = ""
    event_type: str = ""  # action | state_change | observation | failure | success
    entity_id: str = ""
    scene_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "event_type": self.event_type,
            "entity_id": self.entity_id,
            "scene_id": self.scene_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class CausalEdge:
    """A directed causal link between two events."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    cause_id: str = ""
    effect_id: str = ""
    confidence: float = 0.5
    delay_ms: float = 0.0
    context: str = ""
    observation_count: int = 1
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cause_id": self.cause_id,
            "effect_id": self.effect_id,
            "confidence": round(self.confidence, 4),
            "delay_ms": round(self.delay_ms, 2),
            "context": self.context,
            "observation_count": self.observation_count,
            "created_at": self.created_at,
        }


@dataclass
class CausalChain:
    """A traced path through the causal graph."""

    events: List[CausalEvent] = field(default_factory=list)
    edges: List[CausalEdge] = field(default_factory=list)
    total_confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self.events],
            "edges": [e.to_dict() for e in self.edges],
            "total_confidence": round(self.total_confidence, 4),
            "length": len(self.events),
        }


class CausalAtlas:
    """
    A causal graph that captures cause-effect relationships in the game world.

    The atlas is built incrementally: every time the agent or engine performs
    an action and observes a result, a causal edge is recorded. Over time,
    the graph becomes a rich model of how the world works, enabling:

      - Root cause analysis (why did the score drop?)
      - Effect prediction (what will happen if I spawn this entity?)
      - Intervention planning (which link should I cut to prevent X?)
    """

    def __init__(self, max_events: int = 2000, max_edges: int = 5000) -> None:
        self._events: Dict[str, CausalEvent] = {}
        self._edges: Dict[str, CausalEdge] = {}
        # Adjacency: cause_id -> list of (edge_id, effect_id)
        self._forward: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        # Reverse adjacency: effect_id -> list of (edge_id, cause_id)
        self._backward: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        # Label index for fuzzy lookup
        self._label_index: Dict[str, Set[str]] = defaultdict(set)

        self._max_events = max_events
        self._max_edges = max_edges
        self._total_recorded: int = 0

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(
        self,
        cause_label: str,
        effect_label: str,
        cause_type: str = "action",
        effect_type: str = "state_change",
        entity_id: str = "",
        scene_id: str = "",
        confidence: float = 0.6,
        delay_ms: float = 0.0,
        context: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        Record a causal relationship: cause -> effect.

        Returns (cause_event_id, effect_event_id).
        """
        cause = CausalEvent(
            label=cause_label,
            event_type=cause_type,
            entity_id=entity_id,
            scene_id=scene_id,
            metadata=metadata or {},
        )
        effect = CausalEvent(
            label=effect_label,
            event_type=effect_type,
            entity_id=entity_id,
            scene_id=scene_id,
            metadata=metadata or {},
        )

        self._add_event(cause)
        self._add_event(effect)

        # Check if an edge with the same cause->effect already exists
        existing_edge_id = self._find_edge(cause.id, effect.id)
        if existing_edge_id:
            edge = self._edges[existing_edge_id]
            edge.observation_count += 1
            # Update confidence with a weighted average
            edge.confidence = edge.confidence * 0.7 + confidence * 0.3
        else:
            edge = CausalEdge(
                cause_id=cause.id,
                effect_id=effect.id,
                confidence=confidence,
                delay_ms=delay_ms,
                context=context,
            )
            self._add_edge(edge)

        self._total_recorded += 1
        return cause.id, effect.id

    def record_action_result(
        self,
        action_type: str,
        action_params: Dict[str, Any],
        result: str,
        success: bool,
        entity_id: str = "",
        scene_id: str = "",
    ) -> Tuple[str, str]:
        """
        Convenience method: record an engine action and its observable result.
        """
        cause_label = f"{action_type}({', '.join(f'{k}={v}' for k, v in action_params.items())})"
        effect_label = f"result={result}, success={success}"
        return self.record(
            cause_label=cause_label,
            effect_label=effect_label,
            cause_type="action",
            effect_type="success" if success else "failure",
            entity_id=entity_id,
            scene_id=scene_id,
            confidence=0.7 if success else 0.5,
            context=action_type,
        )

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def explain(self, event_label: str, max_depth: int = 5) -> CausalChain:
        """
        Trace backward from an event to find its root causes.

        Performs a breadth-first search through the reverse adjacency graph,
        accumulating the causal chain with confidence decay at each hop.
        """
        start_ids = self._find_events_by_label(event_label)
        if not start_ids:
            return CausalChain()

        # BFS backward
        visited: Set[str] = set()
        queue: deque = deque()
        chain_events: List[CausalEvent] = []
        chain_edges: List[CausalEdge] = []
        total_conf = 1.0

        for sid in start_ids:
            if sid not in visited:
                visited.add(sid)
                queue.append((sid, 0))

        while queue:
            eid, depth = queue.popleft()
            if depth >= max_depth:
                continue
            event = self._events.get(eid)
            if event:
                chain_events.append(event)

            for edge_id, cause_id in self._backward.get(eid, []):
                edge = self._edges.get(edge_id)
                if edge and cause_id not in visited:
                    visited.add(cause_id)
                    chain_edges.append(edge)
                    total_conf *= edge.confidence
                    queue.append((cause_id, depth + 1))

        # Sort by timestamp
        chain_events.sort(key=lambda e: e.timestamp)
        return CausalChain(
            events=chain_events,
            edges=chain_edges,
            total_confidence=total_conf,
        )

    def predict(self, action_label: str, max_depth: int = 5) -> CausalChain:
        """
        Trace forward from an action to predict its likely effects.

        Performs a breadth-first search through the forward adjacency graph.
        """
        start_ids = self._find_events_by_label(action_label)
        if not start_ids:
            return CausalChain()

        visited: Set[str] = set()
        queue: deque = deque()
        chain_events: List[CausalEvent] = []
        chain_edges: List[CausalEdge] = []
        total_conf = 1.0

        for sid in start_ids:
            if sid not in visited:
                visited.add(sid)
                queue.append((sid, 0))

        while queue:
            eid, depth = queue.popleft()
            if depth >= max_depth:
                continue
            event = self._events.get(eid)
            if event:
                chain_events.append(event)

            for edge_id, effect_id in self._forward.get(eid, []):
                edge = self._edges.get(edge_id)
                if edge and effect_id not in visited:
                    visited.add(effect_id)
                    chain_edges.append(edge)
                    total_conf *= edge.confidence
                    queue.append((effect_id, depth + 1))

        chain_events.sort(key=lambda e: e.timestamp)
        return CausalChain(
            events=chain_events,
            edges=chain_edges,
            total_confidence=total_conf,
        )

    def find_path(self, from_label: str, to_label: str, max_depth: int = 8) -> CausalChain:
        """
        Find a causal chain connecting two events.
        """
        start_ids = self._find_events_by_label(from_label)
        end_ids = set(self._find_events_by_label(to_label))
        if not start_ids or not end_ids:
            return CausalChain()

        # BFS from start to end
        visited: Set[str] = set()
        parent: Dict[str, Tuple[str, str]] = {}  # node -> (parent_node, edge_id)

        queue: deque = deque()
        for sid in start_ids:
            visited.add(sid)
            queue.append(sid)

        found: Optional[str] = None
        while queue:
            eid = queue.popleft()
            if eid in end_ids:
                found = eid
                break
            for edge_id, effect_id in self._forward.get(eid, []):
                if effect_id not in visited:
                    visited.add(effect_id)
                    parent[effect_id] = (eid, edge_id)
                    queue.append(effect_id)

        if found is None:
            return CausalChain()

        # Reconstruct path
        chain_events: List[CausalEvent] = []
        chain_edges: List[CausalEdge] = []
        total_conf = 1.0
        current = found
        while current in parent:
            parent_node, edge_id = parent[current]
            edge = self._edges.get(edge_id)
            if edge:
                chain_edges.append(edge)
                total_conf *= edge.confidence
            event = self._events.get(current)
            if event:
                chain_events.append(event)
            current = parent_node

        # Add the start event
        start_event = self._events.get(current)
        if start_event:
            chain_events.append(start_event)

        chain_events.reverse()
        chain_edges.reverse()
        return CausalChain(
            events=chain_events,
            edges=chain_edges,
            total_confidence=total_conf,
        )

    # ------------------------------------------------------------------
    # Statistics & Export
    # ------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """Return aggregate statistics about the causal graph."""
        avg_conf = 0.0
        if self._edges:
            avg_conf = sum(e.confidence for e in self._edges.values()) / len(self._edges)

        # Find the strongest causal links
        top_edges = sorted(self._edges.values(), key=lambda e: e.confidence * e.observation_count, reverse=True)[:5]

        return {
            "total_events": len(self._events),
            "total_edges": len(self._edges),
            "total_recorded": self._total_recorded,
            "avg_confidence": round(avg_conf, 4),
            "top_links": [
                {
                    "cause": self._events.get(e.cause_id, CausalEvent()).label,
                    "effect": self._events.get(e.effect_id, CausalEvent()).label,
                    "confidence": round(e.confidence, 4),
                    "observations": e.observation_count,
                }
                for e in top_edges
            ],
        }

    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent events."""
        sorted_events = sorted(self._events.values(), key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in sorted_events[:limit]]

    def get_edges(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent edges."""
        sorted_edges = sorted(self._edges.values(), key=lambda e: e.created_at, reverse=True)
        return [e.to_dict() for e in sorted_edges[:limit]]

    def clear(self) -> None:
        """Reset the atlas."""
        self._events.clear()
        self._edges.clear()
        self._forward.clear()
        self._backward.clear()
        self._label_index.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _add_event(self, event: CausalEvent) -> None:
        self._events[event.id] = event
        self._label_index[event.label.lower()].add(event.id)
        # Enforce capacity
        if len(self._events) > self._max_events:
            oldest = min(self._events.values(), key=lambda e: e.timestamp)
            self._remove_event(oldest.id)

    def _add_edge(self, edge: CausalEdge) -> None:
        self._edges[edge.id] = edge
        self._forward[edge.cause_id].append((edge.id, edge.effect_id))
        self._backward[edge.effect_id].append((edge.id, edge.cause_id))
        if len(self._edges) > self._max_edges:
            oldest = min(self._edges.values(), key=lambda e: e.created_at)
            self._remove_edge(oldest.id)

    def _find_edge(self, cause_id: str, effect_id: str) -> Optional[str]:
        for edge_id, eid in self._forward.get(cause_id, []):
            if eid == effect_id:
                return edge_id
        return None

    def _find_events_by_label(self, label: str) -> List[str]:
        """Find event IDs by exact or partial label match."""
        label_lower = label.lower()
        # Exact match
        if label_lower in self._label_index:
            return list(self._label_index[label_lower])
        # Partial match
        results: List[str] = []
        for indexed_label, ids in self._label_index.items():
            if label_lower in indexed_label:
                results.extend(ids)
        return results

    def _remove_event(self, event_id: str) -> None:
        event = self._events.pop(event_id, None)
        if event:
            self._label_index[event.label.lower()].discard(event_id)
            if not self._label_index[event.label.lower()]:
                del self._label_index[event.label.lower()]

    def _remove_edge(self, edge_id: str) -> None:
        edge = self._edges.pop(edge_id, None)
        if edge:
            self._forward[edge.cause_id] = [
                (eid, eff) for eid, eff in self._forward.get(edge.cause_id, []) if eid != edge_id
            ]
            self._backward[edge.effect_id] = [
                (eid, cau) for eid, cau in self._backward.get(edge.effect_id, []) if eid != edge_id
            ]


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

_causal_atlas: Optional[CausalAtlas] = None


def get_causal_atlas() -> CausalAtlas:
    """Get the shared CausalAtlas singleton."""
    global _causal_atlas
    if _causal_atlas is None:
        _causal_atlas = CausalAtlas()
    return _causal_atlas
