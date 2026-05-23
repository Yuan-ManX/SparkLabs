"""
SparkLabs Agent - Chain-of-Thought Engine

A structured reasoning system that traces step-by-step logic chains
for agent decision-making in the SparkLabs AI-native game engine.
Models reasoning as a traversable thought tree where each node captures
a discrete cognitive step with confidence scoring, evidence linking,
and branching support for alternative reasoning paths.

Architecture:
  ChainOfThoughtEngine
    |-- ThoughtChain (full reasoning session anchored to a question)
    |-- ReasoningNode (single cognitive step in the thought tree)
    |-- ReasoningTrace (serializable record of the reasoning path)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ReasoningStep(Enum):
    OBSERVATION = "observation"
    ANALYSIS = "analysis"
    HYPOTHESIS = "hypothesis"
    DEDUCTION = "deduction"
    VERIFICATION = "verification"
    CONCLUSION = "conclusion"
    REFLECTION = "reflection"
    REVISION = "revision"
    BRANCH = "branch"


class ThoughtState(Enum):
    DRAFT = "draft"
    DEVELOPING = "developing"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    PENDING = "pending"


_STEP_ORDER: Dict[ReasoningStep, int] = {
    ReasoningStep.OBSERVATION: 0,
    ReasoningStep.ANALYSIS: 1,
    ReasoningStep.HYPOTHESIS: 2,
    ReasoningStep.DEDUCTION: 3,
    ReasoningStep.VERIFICATION: 4,
    ReasoningStep.CONCLUSION: 5,
    ReasoningStep.REFLECTION: 6,
    ReasoningStep.REVISION: 7,
    ReasoningStep.BRANCH: 8,
}


_STATE_RANK: Dict[ThoughtState, int] = {
    ThoughtState.DRAFT: 0,
    ThoughtState.DEVELOPING: 1,
    ThoughtState.PENDING: 2,
    ThoughtState.CONFIRMED: 3,
    ThoughtState.REJECTED: 4,
}


@dataclass
class ReasoningNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    chain_id: str = ""
    parent_id: Optional[str] = None
    step_type: ReasoningStep = ReasoningStep.OBSERVATION
    content: str = ""
    label: str = ""
    confidence: float = 0.0
    evidence: str = ""
    state: ThoughtState = ThoughtState.DRAFT
    depth: int = 0
    children_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    evaluated_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chain_id": self.chain_id,
            "parent_id": self.parent_id,
            "step_type": self.step_type.value,
            "content": self.content,
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "evidence": self.evidence[:200],
            "state": self.state.value,
            "depth": self.depth,
            "children_ids": self.children_ids,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "evaluated_at": self.evaluated_at,
        }

    def to_summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "step_type": self.step_type.value,
            "content": self.content[:120],
            "confidence": round(self.confidence, 4),
            "state": self.state.value,
            "depth": self.depth,
            "children_count": len(self.children_ids),
        }

    def add_child(self, child_id: str) -> None:
        if child_id not in self.children_ids:
            self.children_ids.append(child_id)

    def remove_child(self, child_id: str) -> bool:
        if child_id in self.children_ids:
            self.children_ids.remove(child_id)
            return True
        return False


@dataclass
class ThoughtChain:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    question: str = ""
    context: str = ""
    agent_id: str = ""
    nodes: Dict[str, ReasoningNode] = field(default_factory=dict)
    root_node_id: Optional[str] = None
    conclusion: str = ""
    confidence: float = 0.0
    state: ThoughtState = ThoughtState.DRAFT
    step_count: int = 0
    max_depth: int = 0
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    finalized_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "context": self.context[:300],
            "agent_id": self.agent_id,
            "node_count": len(self.nodes),
            "root_node_id": self.root_node_id,
            "conclusion": self.conclusion[:300],
            "confidence": round(self.confidence, 4),
            "state": self.state.value,
            "step_count": self.step_count,
            "max_depth": self.max_depth,
            "tags": self.tags,
            "created_at": self.created_at,
            "finalized_at": self.finalized_at,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["nodes"] = [node.to_dict() for node in self.nodes.values()]
        return result

    def get_node(self, node_id: str) -> Optional[ReasoningNode]:
        return self.nodes.get(node_id)

    def get_root(self) -> Optional[ReasoningNode]:
        if self.root_node_id is None:
            return None
        return self.nodes.get(self.root_node_id)

    def get_leaf_nodes(self) -> List[ReasoningNode]:
        return [n for n in self.nodes.values() if not n.children_ids]

    def get_nodes_by_type(self, step_type: ReasoningStep) -> List[ReasoningNode]:
        return [n for n in self.nodes.values() if n.step_type == step_type]

    def get_nodes_by_state(self, state: ThoughtState) -> List[ReasoningNode]:
        return [n for n in self.nodes.values() if n.state == state]

    def get_path_to_root(self, node_id: str) -> List[ReasoningNode]:
        path: List[ReasoningNode] = []
        current = self.nodes.get(node_id)
        visited: set = set()
        while current is not None and current.id not in visited:
            visited.add(current.id)
            path.insert(0, current)
            if current.parent_id is None:
                break
            current = self.nodes.get(current.parent_id)
        return path

    def get_branch_paths(self) -> List[List[ReasoningNode]]:
        leaves = self.get_leaf_nodes()
        return [self.get_path_to_root(leaf.id) for leaf in leaves]

    def get_depth_distribution(self) -> Dict[int, int]:
        distribution: Dict[int, int] = {}
        for node in self.nodes.values():
            distribution[node.depth] = distribution.get(node.depth, 0) + 1
        return distribution

    def get_confidence_metrics(self) -> Dict[str, float]:
        confidences = [n.confidence for n in self.nodes.values() if n.confidence > 0]
        if not confidences:
            return {"min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0}
        sorted_conf = sorted(confidences)
        n = len(sorted_conf)
        if n % 2 == 1:
            median = sorted_conf[n // 2]
        else:
            median = (sorted_conf[n // 2 - 1] + sorted_conf[n // 2]) / 2.0
        return {
            "min": round(min(confidences), 4),
            "max": round(max(confidences), 4),
            "mean": round(sum(confidences) / n, 4),
            "median": round(median, 4),
        }

    def get_step_type_distribution(self) -> Dict[str, int]:
        distribution: Dict[str, int] = {}
        for node in self.nodes.values():
            key = node.step_type.value
            distribution[key] = distribution.get(key, 0) + 1
        return distribution

    def compute_best_path(self) -> List[ReasoningNode]:
        paths = self.get_branch_paths()
        if not paths:
            return []
        best_path: List[ReasoningNode] = []
        best_score = -float("inf")
        for path in paths:
            confidences = [n.confidence for n in path]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            depth_bonus = len(path) * 0.01
            score = avg_conf + depth_bonus
            if score > best_score:
                best_score = score
                best_path = path
        return best_path


@dataclass
class ReasoningTrace:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    chain_id: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chain_id": self.chain_id,
            "step_count": len(self.steps),
            "event_count": len(self.events),
            "metrics": self.metrics,
            "created_at": self.created_at,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chain_id": self.chain_id,
            "steps": self.steps,
            "events": self.events,
            "metrics": self.metrics,
            "created_at": self.created_at,
        }

    def record_step(self, node: ReasoningNode) -> None:
        self.steps.append(node.to_summary())

    def record_event(self, event_type: str, detail: str = "", data: Optional[Dict[str, Any]] = None) -> None:
        self.events.append({
            "timestamp": time.time(),
            "event_type": event_type,
            "detail": detail,
            "data": data or {},
        })

    def compute_metrics(self, chain: ThoughtChain) -> None:
        confidence_metrics = chain.get_confidence_metrics()
        step_types = chain.get_step_type_distribution()
        self.metrics = {
            "total_nodes": len(chain.nodes),
            "total_steps": chain.step_count,
            "max_depth": chain.max_depth,
            "branch_count": len(chain.get_leaf_nodes()),
            "confidence": confidence_metrics,
            "step_type_distribution": step_types,
            "duration_seconds": round(
                (chain.finalized_at or time.time()) - chain.created_at, 2
            ),
            "final_confidence": round(chain.confidence, 4),
        }


class ChainOfThoughtEngine:
    """
    Structured reasoning engine that traces step-by-step logic chains
    for agent decision-making. Models reasoning as a traversable thought
    tree with branching, confidence scoring, evidence tracking, and
    trace recording for post-hoc analysis.
    """

    _instance: Optional["ChainOfThoughtEngine"] = None
    _lock = threading.RLock()

    _MAX_CHAIN_DEPTH: int = 20
    _MAX_NODES_PER_CHAIN: int = 200
    _MAX_CHAINS: int = 100
    _MAX_TRACES: int = 500
    _CONFIDENCE_THRESHOLD: float = 0.6
    _DEPTH_PENALTY_FACTOR: float = 0.02

    def __init__(self) -> None:
        self._chains: Dict[str, ThoughtChain] = {}
        self._traces: Dict[str, ReasoningTrace] = {}
        self._active_trace_map: Dict[str, str] = {}
        self._total_chains_created: int = 0
        self._total_nodes_created: int = 0
        self._total_traces_created: int = 0

    @classmethod
    def get_instance(cls) -> "ChainOfThoughtEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Chain Lifecycle
    # ------------------------------------------------------------------

    def start_chain(
        self,
        question: str,
        context: str = "",
        agent_id: str = "",
        tags: Optional[List[str]] = None,
    ) -> ThoughtChain:
        with self._lock:
            self._enforce_max_chains()

            chain = ThoughtChain(
                question=question,
                context=context,
                agent_id=agent_id,
                state=ThoughtState.DRAFT,
                tags=tags or [],
            )

            root_node = ReasoningNode(
                chain_id=chain.id,
                step_type=ReasoningStep.OBSERVATION,
                content=f"[ROOT] {question[:200]}",
                label="root",
                confidence=1.0,
                state=ThoughtState.CONFIRMED,
                depth=0,
            )

            self._register_node(chain, root_node)
            chain.root_node_id = root_node.id
            chain.max_depth = 0

            self._chains[chain.id] = chain
            self._total_chains_created += 1

            trace = ReasoningTrace(chain_id=chain.id)
            trace.record_event("chain_started", detail=question[:200])
            self._traces[trace.id] = trace
            self._active_trace_map[chain.id] = trace.id
            self._total_traces_created += 1

            return chain

    def get_chain(self, chain_id: str) -> Optional[ThoughtChain]:
        return self._chains.get(chain_id)

    # ------------------------------------------------------------------
    # Node Operations
    # ------------------------------------------------------------------

    def add_reasoning_step(
        self,
        chain_id: str,
        step_type: ReasoningStep,
        content: str,
        confidence: float = 0.0,
        evidence: str = "",
        parent_id: Optional[str] = None,
        label: str = "",
    ) -> Optional[ReasoningNode]:
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return None

            if chain.state in (ThoughtState.CONFIRMED, ThoughtState.REJECTED):
                return None

            if len(chain.nodes) >= self._MAX_NODES_PER_CHAIN:
                return None

            parent_node: Optional[ReasoningNode] = None
            effective_parent_id = parent_id or chain.root_node_id

            if effective_parent_id is not None:
                parent_node = chain.nodes.get(effective_parent_id)
                if parent_node is None:
                    return None
                depth = parent_node.depth + 1
            else:
                depth = 0

            if depth > self._MAX_CHAIN_DEPTH:
                return None

            clamped_confidence = max(0.0, min(1.0, confidence))
            if clamped_confidence > 0:
                clamped_confidence = self._apply_depth_penalty(clamped_confidence, depth)

            node = ReasoningNode(
                chain_id=chain_id,
                parent_id=effective_parent_id,
                step_type=step_type,
                content=content,
                label=label,
                confidence=clamped_confidence,
                evidence=evidence,
                state=ThoughtState.DRAFT,
                depth=depth,
            )

            self._register_node(chain, node)

            if parent_node is not None:
                parent_node.add_child(node.id)

            chain.step_count += 1
            if depth > chain.max_depth:
                chain.max_depth = depth

            chain.state = ThoughtState.DEVELOPING

            trace = self._get_active_trace(chain_id)
            if trace is not None:
                trace.record_step(node)
                trace.record_event(
                    "step_added",
                    detail=f"{step_type.value}: {content[:80]}",
                    data={"node_id": node.id, "depth": depth, "confidence": clamped_confidence},
                )

            return node

    def add_branch(
        self,
        chain_id: str,
        parent_node_id: str,
        branch_label: str = "",
        initial_content: str = "",
    ) -> Optional[ReasoningNode]:
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return None

            if chain.state in (ThoughtState.CONFIRMED, ThoughtState.REJECTED):
                return None

            parent_node = chain.nodes.get(parent_node_id)
            if parent_node is None:
                return None

            if len(chain.nodes) >= self._MAX_NODES_PER_CHAIN:
                return None

            depth = parent_node.depth + 1
            if depth > self._MAX_CHAIN_DEPTH:
                return None

            node = ReasoningNode(
                chain_id=chain_id,
                parent_id=parent_node_id,
                step_type=ReasoningStep.BRANCH,
                content=initial_content or f"Alternative path from: {parent_node.content[:60]}",
                label=branch_label,
                confidence=parent_node.confidence * 0.8,
                state=ThoughtState.DRAFT,
                depth=depth,
            )

            self._register_node(chain, node)
            parent_node.add_child(node.id)

            chain.step_count += 1
            if depth > chain.max_depth:
                chain.max_depth = depth

            chain.state = ThoughtState.DEVELOPING

            trace = self._get_active_trace(chain_id)
            if trace is not None:
                trace.record_step(node)
                trace.record_event(
                    "branch_created",
                    detail=f"Branch '{branch_label}' from node {parent_node_id[:8]}",
                    data={"node_id": node.id, "parent_id": parent_node_id, "depth": depth},
                )

            return node

    def evaluate_node(
        self,
        chain_id: str,
        node_id: str,
        new_confidence: Optional[float] = None,
        new_state: Optional[ThoughtState] = None,
        evidence: str = "",
    ) -> Optional[ReasoningNode]:
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return None

            node = chain.nodes.get(node_id)
            if node is None:
                return None

            if new_confidence is not None:
                clamped = max(0.0, min(1.0, new_confidence))
                node.confidence = self._apply_depth_penalty(clamped, node.depth)

            if new_state is not None:
                node.state = new_state

            if evidence:
                if node.evidence:
                    node.evidence += " | " + evidence
                else:
                    node.evidence = evidence

            node.evaluated_at = time.time()

            trace = self._get_active_trace(chain_id)
            if trace is not None:
                trace.record_event(
                    "node_evaluated",
                    detail=f"Node {node_id[:8]}: confidence={node.confidence}, state={node.state.value}",
                    data={"node_id": node_id, "confidence": node.confidence, "state": node.state.value},
                )

            return node

    def revise_node(
        self,
        chain_id: str,
        node_id: str,
        new_content: str,
        new_confidence: Optional[float] = None,
    ) -> Optional[ReasoningNode]:
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return None

            node = chain.nodes.get(node_id)
            if node is None:
                return None

            revision = ReasoningNode(
                chain_id=chain_id,
                parent_id=node.parent_id,
                step_type=ReasoningStep.REVISION,
                content=new_content,
                label=f"revision-of-{node_id[:8]}",
                confidence=new_confidence or node.confidence,
                evidence=f"Revises node {node_id[:8]}",
                state=ThoughtState.DRAFT,
                depth=node.depth,
                metadata={"revises_node_id": node_id, "original_content": node.content[:200]},
            )

            self._register_node(chain, revision)

            if node.parent_id:
                parent = chain.nodes.get(node.parent_id)
                if parent is not None:
                    parent.add_child(revision.id)

            chain.step_count += 1

            trace = self._get_active_trace(chain_id)
            if trace is not None:
                trace.record_step(revision)
                trace.record_event(
                    "node_revised",
                    detail=f"Revised node {node_id[:8]}",
                    data={"original_node_id": node_id, "revision_node_id": revision.id},
                )

            return revision

    # ------------------------------------------------------------------
    # Chain Finalization and Analysis
    # ------------------------------------------------------------------

    def finalize_chain(
        self,
        chain_id: str,
        conclusion: str = "",
        confidence: float = 0.0,
    ) -> Optional[ThoughtChain]:
        with self._lock:
            chain = self._chains.get(chain_id)
            if chain is None:
                return None

            if conclusion:
                clamped_confidence = max(0.0, min(1.0, confidence))
                conclusion_node = ReasoningNode(
                    chain_id=chain_id,
                    step_type=ReasoningStep.CONCLUSION,
                    content=conclusion,
                    label="final-conclusion",
                    confidence=clamped_confidence,
                    state=ThoughtState.CONFIRMED,
                    depth=chain.max_depth + 1,
                )
                self._register_node(chain, conclusion_node)
                chain.step_count += 1
                chain.max_depth = max(chain.max_depth, conclusion_node.depth)
                chain.conclusion = conclusion
                chain.confidence = clamped_confidence

            chain.state = ThoughtState.CONFIRMED
            chain.finalized_at = time.time()

            if not chain.conclusion and chain.nodes:
                best_path = chain.compute_best_path()
                if best_path:
                    chain.conclusion = best_path[-1].content
                    chain.confidence = best_path[-1].confidence

            trace = self._get_active_trace(chain_id)
            if trace is not None:
                trace.compute_metrics(chain)
                trace.record_event(
                    "chain_finalized",
                    detail=f"Final confidence: {chain.confidence}",
                    data={"conclusion": chain.conclusion[:200], "confidence": chain.confidence},
                )
                if chain_id in self._active_trace_map:
                    del self._active_trace_map[chain_id]

            self._enforce_max_traces()
            return chain

    def trace_chain(self, chain_id: str) -> Optional[ReasoningTrace]:
        for trace in self._traces.values():
            if trace.chain_id == chain_id:
                return trace
        return None

    def get_active_chains(self) -> List[ThoughtChain]:
        return [
            c for c in self._chains.values()
            if c.state not in (ThoughtState.CONFIRMED, ThoughtState.REJECTED)
        ]

    def get_completed_chains(self) -> List[ThoughtChain]:
        return [
            c for c in self._chains.values()
            if c.state == ThoughtState.CONFIRMED
        ]

    def get_chains_by_agent(self, agent_id: str) -> List[ThoughtChain]:
        return [c for c in self._chains.values() if c.agent_id == agent_id]

    # ------------------------------------------------------------------
    # Visualization and Export
    # ------------------------------------------------------------------

    def visualize_chain(self, chain_id: str) -> Dict[str, Any]:
        chain = self._chains.get(chain_id)
        if chain is None:
            return {}

        nodes_visual: List[Dict[str, Any]] = []
        edges_visual: List[Dict[str, Any]] = []

        visited: set = set()
        queue: List[Optional[str]] = [chain.root_node_id]

        while queue:
            node_id = queue.pop(0)
            if node_id is None or node_id in visited:
                continue
            visited.add(node_id)

            node = chain.nodes.get(node_id)
            if node is None:
                continue

            nodes_visual.append({
                "id": node.id,
                "label": node.label or node.step_type.value,
                "content": node.content[:100],
                "step_type": node.step_type.value,
                "confidence": round(node.confidence, 4),
                "state": node.state.value,
                "depth": node.depth,
            })

            for child_id in node.children_ids:
                edges_visual.append({
                    "from": node.id,
                    "to": child_id,
                })
                if child_id not in visited:
                    queue.append(child_id)

        best_path = chain.compute_best_path()
        best_path_ids = {n.id for n in best_path}

        return {
            "chain_id": chain.id,
            "question": chain.question,
            "nodes": nodes_visual,
            "edges": edges_visual,
            "total_nodes": len(nodes_visual),
            "total_edges": len(edges_visual),
            "max_depth": chain.max_depth,
            "branch_factor": self._compute_branch_factor(chain),
            "best_path_node_ids": list(best_path_ids),
            "best_path_length": len(best_path),
            "conclusion": chain.conclusion[:300],
            "confidence": round(chain.confidence, 4),
            "state": chain.state.value,
        }

    def export_chain(self, chain_id: str) -> Dict[str, Any]:
        chain = self._chains.get(chain_id)
        if chain is None:
            return {}

        trace = self.trace_chain(chain_id)
        result = chain.to_full_dict()
        if trace is not None:
            result["trace"] = trace.to_full_dict()
        result["visualization"] = self.visualize_chain(chain_id)
        return result

    def compare_chains(self, chain_id_a: str, chain_id_b: str) -> Dict[str, Any]:
        chain_a = self._chains.get(chain_id_a)
        chain_b = self._chains.get(chain_id_b)

        if chain_a is None or chain_b is None:
            return {}

        return {
            "chain_a": {
                "id": chain_a.id,
                "question": chain_a.question[:100],
                "node_count": len(chain_a.nodes),
                "max_depth": chain_a.max_depth,
                "confidence": round(chain_a.confidence, 4),
                "state": chain_a.state.value,
                "step_types": chain_a.get_step_type_distribution(),
                "confidence_metrics": chain_a.get_confidence_metrics(),
            },
            "chain_b": {
                "id": chain_b.id,
                "question": chain_b.question[:100],
                "node_count": len(chain_b.nodes),
                "max_depth": chain_b.max_depth,
                "confidence": round(chain_b.confidence, 4),
                "state": chain_b.state.value,
                "step_types": chain_b.get_step_type_distribution(),
                "confidence_metrics": chain_b.get_confidence_metrics(),
            },
            "comparison": {
                "node_count_diff": len(chain_a.nodes) - len(chain_b.nodes),
                "depth_diff": chain_a.max_depth - chain_b.max_depth,
                "confidence_diff": round(chain_a.confidence - chain_b.confidence, 4),
            },
        }

    # ------------------------------------------------------------------
    # Statistics and Housekeeping
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            active = self.get_active_chains()
            completed = self.get_completed_chains()

            total_nodes = sum(len(c.nodes) for c in self._chains.values())
            total_steps = sum(c.step_count for c in self._chains.values())

            step_type_totals: Dict[str, int] = {}
            state_totals: Dict[str, int] = {}
            for chain in self._chains.values():
                for node in chain.nodes.values():
                    st = node.step_type.value
                    step_type_totals[st] = step_type_totals.get(st, 0) + 1
                    ss = node.state.value
                    state_totals[ss] = state_totals.get(ss, 0) + 1

            confidences = [
                c.confidence for c in self._chains.values()
                if c.confidence > 0
            ]
            avg_confidence = (
                round(sum(confidences) / len(confidences), 4)
                if confidences else 0.0
            )

            durations = [
                (c.finalized_at or time.time()) - c.created_at
                for c in self._chains.values()
            ]
            avg_duration = (
                round(sum(durations) / len(durations), 2)
                if durations else 0.0
            )

            return {
                "total_chains_created": self._total_chains_created,
                "total_chains_stored": len(self._chains),
                "active_chains": len(active),
                "completed_chains": len(completed),
                "total_nodes_allocated": self._total_nodes_created,
                "total_nodes_active": total_nodes,
                "total_steps": total_steps,
                "total_traces": len(self._traces),
                "step_type_distribution": step_type_totals,
                "node_state_distribution": state_totals,
                "average_chain_confidence": avg_confidence,
                "average_chain_duration_seconds": avg_duration,
                "max_chains_limit": self._MAX_CHAINS,
                "max_chain_depth_limit": self._MAX_CHAIN_DEPTH,
                "max_nodes_per_chain_limit": self._MAX_NODES_PER_CHAIN,
            }

    def reset(self) -> None:
        with self._lock:
            self._chains.clear()
            self._traces.clear()
            self._active_trace_map.clear()
            self._total_chains_created = 0
            self._total_nodes_created = 0
            self._total_traces_created = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _register_node(self, chain: ThoughtChain, node: ReasoningNode) -> None:
        chain.nodes[node.id] = node
        self._total_nodes_created += 1

    def _get_active_trace(self, chain_id: str) -> Optional[ReasoningTrace]:
        trace_id = self._active_trace_map.get(chain_id)
        if trace_id is None:
            return None
        return self._traces.get(trace_id)

    def _apply_depth_penalty(self, confidence: float, depth: int) -> float:
        if depth <= 1:
            return confidence
        penalty = 1.0 - (self._DEPTH_PENALTY_FACTOR * (depth - 1))
        penalty = max(0.3, penalty)
        return round(confidence * penalty, 4)

    def _compute_branch_factor(self, chain: ThoughtChain) -> float:
        non_leaf = [n for n in chain.nodes.values() if n.children_ids]
        if not non_leaf:
            return 0.0
        total_children = sum(len(n.children_ids) for n in non_leaf)
        return round(total_children / len(non_leaf), 2)

    def _enforce_max_chains(self) -> None:
        if len(self._chains) >= self._MAX_CHAINS:
            eviction_order = sorted(
                self._chains.values(),
                key=lambda c: (
                    1 if c.state == ThoughtState.CONFIRMED else 0,
                    c.finalized_at or 0,
                ),
            )
            evict_count = max(1, len(self._chains) - self._MAX_CHAINS + 1)
            for chain in eviction_order[:evict_count]:
                self._chains.pop(chain.id, None)
                trace_id = self._active_trace_map.pop(chain.id, None)
                if trace_id:
                    self._traces.pop(trace_id, None)

    def _enforce_max_traces(self) -> None:
        if len(self._traces) > self._MAX_TRACES:
            excess = len(self._traces) - self._MAX_TRACES
            sorted_traces = sorted(
                self._traces.items(),
                key=lambda item: item[1].created_at,
            )
            for trace_id, _ in sorted_traces[:excess]:
                self._traces.pop(trace_id, None)


def get_chain_of_thought() -> ChainOfThoughtEngine:
    return ChainOfThoughtEngine.get_instance()