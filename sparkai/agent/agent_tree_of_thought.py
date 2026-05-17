"""
SparkLabs Agent - Tree-of-Thought Reasoning Engine

Multi-branch cognitive reasoning system for the SparkLabs AI-native
game engine. Models thought exploration as a traversable tree where
each node represents a partial solution, branches represent lines of
reasoning, and sessions orchestrate the search through problem space.

Architecture:
  TreeOfThought
    |-- ThinkingSession (orchestrated exploration with traversal strategy)
    |-- ReasoningBranch (linear chain of thought nodes)
    |-- ThoughtNode (single reasoning step with scoring)
    |-- HeuristicScoringEngine (relevance, feasibility, creativity, completeness)

Supports BFS, DFS, best-first, and beam-search traversal strategies
across game design, code architecture, level design, narrative,
mechanics, balancing, puzzle design, and AI behavior domains.

Usage:
    tot = get_tree_of_thought()
    session = tot.create_session(
        problem_statement="Design a boss fight for Act 3",
        domain=ThoughtDomain.GAME_DESIGN,
        strategy=TraversalStrategy.BFS,
    )
    tot.expand(session.id, session.branches["root"].id, "Phase-based dragon with elemental attacks")
    tot.evaluate_node(session.id, "node-2")
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TraversalStrategy(Enum):
    BFS = "bfs"
    DFS = "dfs"
    BEST_FIRST = "best_first"
    BEAM_SEARCH = "beam_search"


class ThoughtDomain(Enum):
    GAME_DESIGN = "game_design"
    CODE_ARCHITECTURE = "code_architecture"
    LEVEL_DESIGN = "level_design"
    NARRATIVE = "narrative"
    MECHANICS = "mechanics"
    BALANCING = "balancing"
    PUZZLE_DESIGN = "puzzle_design"
    AI_BEHAVIOR = "ai_behavior"


class NodeStatus(Enum):
    ACTIVE = "active"
    EVALUATED = "evaluated"
    PRUNED = "pruned"
    SELECTED = "selected"


class BranchStatus(Enum):
    EXPLORING = "exploring"
    COMPLETED = "completed"
    PRUNED = "pruned"


@dataclass
class ThoughtNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    content: str = ""
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    depth: int = 0
    score: float = 0.0
    status: NodeStatus = NodeStatus.ACTIVE
    branch_id: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "depth": self.depth,
            "score": self.score,
            "status": self.status.value,
            "branch_id": self.branch_id,
            "created_at": self.created_at,
        }


@dataclass
class ReasoningBranch:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    root_node_id: str = ""
    leaf_node_id: str = ""
    nodes: List[str] = field(default_factory=list)
    total_score: float = 0.0
    depth: int = 0
    status: BranchStatus = BranchStatus.EXPLORING
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "root_node_id": self.root_node_id,
            "leaf_node_id": self.leaf_node_id,
            "nodes": self.nodes,
            "total_score": self.total_score,
            "depth": self.depth,
            "status": self.status.value,
            "created_at": self.created_at,
        }


@dataclass
class ThinkingSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    problem_statement: str = ""
    domain: ThoughtDomain = ThoughtDomain.GAME_DESIGN
    branches: Dict[str, ReasoningBranch] = field(default_factory=dict)
    node_count: int = 0
    branch_count: int = 0
    traversal_strategy: TraversalStrategy = TraversalStrategy.BFS
    max_depth: int = 5
    max_branches: int = 8
    best_solution: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "problem_statement": self.problem_statement,
            "domain": self.domain.value,
            "branches": {k: v.to_dict() for k, v in self.branches.items()},
            "node_count": self.node_count,
            "branch_count": self.branch_count,
            "traversal_strategy": self.traversal_strategy.value,
            "max_depth": self.max_depth,
            "max_branches": self.max_branches,
            "best_solution": self.best_solution,
            "created_at": self.created_at,
        }


class TreeOfThought:
    """
    Tree-of-thought reasoning engine with multi-branch exploration,
    heuristic scoring, self-consistency, and backtracking.
    """

    _instance: Optional["TreeOfThought"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        self._sessions: Dict[str, ThinkingSession] = {}
        self._nodes: Dict[str, ThoughtNode] = {}
        self._session_count: int = 0
        self._node_count: int = 0
        self._branch_count: int = 0
        self._domain_breakdown: Dict[str, int] = defaultdict(int)

    @classmethod
    def get_instance(cls) -> "TreeOfThought":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Session Lifecycle
    # ------------------------------------------------------------------

    def create_session(
        self,
        problem_statement: str,
        domain: ThoughtDomain = ThoughtDomain.GAME_DESIGN,
        strategy: TraversalStrategy = TraversalStrategy.BFS,
        max_depth: int = 5,
        max_branches: int = 8,
    ) -> ThinkingSession:
        with self._lock:
            self._session_count += 1
            session = ThinkingSession(
                problem_statement=problem_statement,
                domain=domain,
                traversal_strategy=strategy,
                max_depth=max_depth,
                max_branches=max_branches,
            )
            root_branch = ReasoningBranch()
            root_node = ThoughtNode(
                content=f"[ROOT] {problem_statement[:80]}",
                depth=0,
                status=NodeStatus.ACTIVE,
                branch_id=root_branch.id,
            )
            root_branch.root_node_id = root_node.id
            root_branch.leaf_node_id = root_node.id
            root_branch.nodes.append(root_node.id)

            self._nodes[root_node.id] = root_node
            self._node_count += 1
            session.node_count += 1

            session.branches[root_branch.id] = root_branch
            session.branch_count += 1
            self._branch_count += 1

            self._sessions[session.id] = session
            self._domain_breakdown[domain.value] += 1
            return session

    def get_session(self, session_id: str) -> Optional[ThinkingSession]:
        return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    # Node and Branch Manipulation
    # ------------------------------------------------------------------

    def expand(
        self,
        session_id: str,
        branch_id: str,
        thought_content: str,
    ) -> Optional[ThoughtNode]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            branch = session.branches.get(branch_id)
            if branch is None or branch.status == BranchStatus.PRUNED:
                return None

            parent_node = self._nodes.get(branch.leaf_node_id)
            if parent_node is None:
                return None

            if parent_node.depth >= session.max_depth:
                return None

            node = ThoughtNode(
                content=thought_content,
                parent_id=parent_node.id,
                depth=parent_node.depth + 1,
                status=NodeStatus.ACTIVE,
                branch_id=branch_id,
            )
            self._nodes[node.id] = node
            self._node_count += 1
            session.node_count += 1

            parent_node.children_ids.append(node.id)
            branch.nodes.append(node.id)
            branch.leaf_node_id = node.id
            branch.depth = node.depth

            return node

    def branch(
        self,
        session_id: str,
        parent_node_id: str,
        thought_content: str,
    ) -> Optional[ReasoningBranch]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            if session.branch_count >= session.max_branches:
                return None

            parent_node = self._nodes.get(parent_node_id)
            if parent_node is None:
                return None

            new_branch = ReasoningBranch()
            root_node = ThoughtNode(
                content=thought_content,
                parent_id=parent_node.id,
                depth=parent_node.depth + 1,
                status=NodeStatus.ACTIVE,
                branch_id=new_branch.id,
            )

            new_branch.root_node_id = root_node.id
            new_branch.leaf_node_id = root_node.id
            new_branch.nodes.append(root_node.id)
            new_branch.depth = root_node.depth

            self._nodes[root_node.id] = root_node
            self._node_count += 1
            session.node_count += 1

            parent_node.children_ids.append(root_node.id)

            session.branches[new_branch.id] = new_branch
            session.branch_count += 1
            self._branch_count += 1

            return new_branch

    def prune(self, session_id: str, branch_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False

            branch = session.branches.get(branch_id)
            if branch is None:
                return False

            branch.status = BranchStatus.PRUNED
            for node_id in branch.nodes:
                node = self._nodes.get(node_id)
                if node is not None and node.status != NodeStatus.SELECTED:
                    node.status = NodeStatus.PRUNED
            return True

    def backtrack(
        self,
        session_id: str,
        branch_id: str,
        to_node_id: str,
    ) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False

            branch = session.branches.get(branch_id)
            if branch is None:
                return False

            if to_node_id not in branch.nodes:
                return False

            target_index = branch.nodes.index(to_node_id)
            pruned_ids = branch.nodes[target_index + 1:]
            for node_id in pruned_ids:
                node = self._nodes.get(node_id)
                if node is not None:
                    node.status = NodeStatus.PRUNED
                    if node.parent_id:
                        parent = self._nodes.get(node.parent_id)
                        if parent is not None and node_id in parent.children_ids:
                            parent.children_ids.remove(node_id)

            branch.nodes = branch.nodes[:target_index + 1]
            branch.leaf_node_id = to_node_id
            branch.status = BranchStatus.EXPLORING

            target_node = self._nodes.get(to_node_id)
            if target_node is not None:
                branch.depth = target_node.depth

            return True

    # ------------------------------------------------------------------
    # Heuristic Scoring Engine
    # ------------------------------------------------------------------

    def evaluate_node(self, session_id: str, node_id: str) -> Optional[float]:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return None

            session = self._sessions.get(session_id)
            if session is None:
                return None

            problem = session.problem_statement.lower()

            relevance = self._score_relevance(node.content, problem)
            feasibility = self._score_feasibility(node.content)
            creativity = self._score_creativity(node.content)
            completeness = self._score_completeness(node)

            score = (
                relevance * 0.35
                + feasibility * 0.30
                + creativity * 0.20
                + completeness * 0.15
            )
            node.score = round(score, 4)
            node.status = NodeStatus.EVALUATED

            branch = session.branches.get(node.branch_id)
            if branch is not None:
                branch_scores = [
                    self._nodes[nid].score
                    for nid in branch.nodes
                    if nid in self._nodes
                ]
                branch.total_score = sum(branch_scores) / max(len(branch_scores), 1)

            return node.score

    def _score_relevance(self, content: str, problem: str) -> float:
        content_lower = content.lower()
        keywords = {w for w in problem.split() if len(w) > 3}
        if not keywords:
            return 0.5
        matches = sum(1 for kw in keywords if kw in content_lower)
        ratio = matches / len(keywords)
        return min(1.0, 0.3 + ratio * 0.7)

    def _score_feasibility(self, content: str) -> float:
        feasibility_markers = [
            "implement", "build", "create", "setup", "configure",
            "asset", "component", "module", "system", "pipeline",
            "step", "phase", "stage", "level", "scene",
            "script", "blueprint", "template", "pattern",
        ]
        content_lower = content.lower()
        marker_hits = sum(1 for m in feasibility_markers if m in content_lower)
        base = min(0.8, 0.3 + marker_hits * 0.1)
        if len(content) > 40:
            base += 0.1
        if any(w in content_lower for w in ["specific", "concrete", "precise"]):
            base += 0.1
        return min(1.0, base)

    def _score_creativity(self, content: str) -> float:
        novelty_markers = [
            "novel", "unique", "original", "twist", "surprise",
            "emergent", "dynamic", "procedural", "generative",
            "unexpected", "nonlinear", "adaptive", "evolving",
            "hybrid", "fusion", "remix", "subvert", "flip",
        ]
        content_lower = content.lower()
        marker_hits = sum(1 for m in novelty_markers if m in content_lower)
        score = min(0.9, 0.2 + marker_hits * 0.12)
        if len(content) > 60:
            score += 0.05
        return min(1.0, score)

    def _score_completeness(self, node: ThoughtNode) -> float:
        score = 0.0
        content_len = len(node.content)
        if content_len > 20:
            score += 0.15
        if content_len > 60:
            score += 0.15
        if content_len > 120:
            score += 0.1
        content_lower = node.content.lower()
        closure_markers = [
            "therefore", "thus", "finally", "outcome", "result",
            "conclusion", "solution", "complete", "resolved", "finished",
        ]
        marker_hits = sum(1 for m in closure_markers if m in content_lower)
        score += min(0.3, marker_hits * 0.1)
        if node.children_ids:
            score = min(score, 0.7)
        else:
            score += 0.15
        return min(0.95, score)

    # ------------------------------------------------------------------
    # Self-Consistency and Path Selection
    # ------------------------------------------------------------------

    def self_consistency(
        self,
        session_id: str,
        num_samples: int = 3,
    ) -> Optional[str]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            completed_branches = [
                b for b in session.branches.values()
                if b.status == BranchStatus.COMPLETED
            ]
            if not completed_branches:
                active_branches = [
                    b for b in session.branches.values()
                    if b.status == BranchStatus.EXPLORING
                ]
                candidates = active_branches + completed_branches
            else:
                candidates = completed_branches

            if not candidates:
                return None

            scored_candidates: List[Tuple[ReasoningBranch, float]] = []
            for branch in candidates:
                scores = [
                    self._nodes[nid].score
                    for nid in branch.nodes
                    if nid in self._nodes
                ]
                avg = sum(scores) / max(len(scores), 1) if scores else 0.0
                depth_bonus = min(0.2, branch.depth * 0.04)
                scored_candidates.append((branch, avg + depth_bonus))

            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            top = scored_candidates[:num_samples]

            if not top:
                return None

            best_branch = top[0]
            self._select_branch_nodes(session, best_branch[0])

            leaf = self._nodes.get(best_branch[0].leaf_node_id)
            best_solution = leaf.content if leaf else best_branch[0].nodes[-1]
            session.best_solution = best_solution
            return best_solution

    def select_best_path(self, session_id: str) -> Optional[str]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            best_branch: Optional[ReasoningBranch] = None
            best_score = -float("inf")

            for branch in session.branches.values():
                if branch.status == BranchStatus.PRUNED:
                    continue
                scores = [
                    self._nodes[nid].score
                    for nid in branch.nodes
                    if nid in self._nodes
                ]
                avg = sum(scores) / max(len(scores), 1) if scores else 0.0
                combined = avg + branch.depth * 0.05
                if combined > best_score:
                    best_score = combined
                    best_branch = branch

            if best_branch is None:
                return None

            self._select_branch_nodes(session, best_branch)
            best_branch.status = BranchStatus.COMPLETED

            leaf = self._nodes.get(best_branch.leaf_node_id)
            best_solution = leaf.content if leaf else best_branch.nodes[-1]
            session.best_solution = best_solution
            return best_solution

    def _select_branch_nodes(
        self, session: ThinkingSession, branch: ReasoningBranch
    ) -> None:
        for nid in branch.nodes:
            node = self._nodes.get(nid)
            if node is not None:
                node.status = NodeStatus.SELECTED

    def get_reasoning_trace(self, session_id: str) -> List[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if session is None or session.best_solution is None:
            return []

        best_branch: Optional[ReasoningBranch] = None
        best_score = -float("inf")
        for branch in session.branches.values():
            scores = [
                self._nodes[nid].score
                for nid in branch.nodes
                if nid in self._nodes
            ]
            avg = sum(scores) / max(len(scores), 1) if scores else 0.0
            combined = avg + branch.depth * 0.05
            if combined > best_score:
                best_score = combined
                best_branch = branch

        if best_branch is None:
            return []

        trace: List[Dict[str, Any]] = []
        for nid in best_branch.nodes:
            node = self._nodes.get(nid)
            if node is not None:
                trace.append(node.to_dict())
        return trace

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            active_sessions = sum(
                1 for s in self._sessions.values()
                if s.best_solution is None
            )
            completed_sessions = sum(
                1 for s in self._sessions.values()
                if s.best_solution is not None
            )
            total_nodes = sum(s.node_count for s in self._sessions.values())
            total_branches = sum(s.branch_count for s in self._sessions.values())
            pruned_branches = sum(
                1 for s in self._sessions.values()
                for b in s.branches.values()
                if b.status == BranchStatus.PRUNED
            )

            return {
                "session_count": self._session_count,
                "node_count": self._node_count,
                "branch_count": self._branch_count,
                "active_sessions": active_sessions,
                "completed_sessions": completed_sessions,
                "total_nodes_allocated": total_nodes,
                "total_branches_allocated": total_branches,
                "pruned_branches": pruned_branches,
                "domain_breakdown": dict(self._domain_breakdown),
            }


def get_tree_of_thought() -> TreeOfThought:
    return TreeOfThought.get_instance()