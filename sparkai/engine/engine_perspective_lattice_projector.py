"""
SparkLabs Engine - Perspective Lattice Projector"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class PerspectivePhase(Enum):
    """Phases of the perspective lattice cycle."""
    ORIENT = "orient"            # orient the lattice to the scene context
    PROJECT = "project"          # each perspective projects its concerns
    INTERSECT = "intersect"      # find where projections cross and form edges
    FOCUS = "focus"              # condense toward the most coherent whole
    RESOLVE = "resolve"          # resolve perspective conflicts and settle


class PerspectiveKind(Enum):
    """The kind of perspective a node represents."""
    CAMERA = "camera"            # where the eye is drawn
    AUDIO = "audio"              # where the ear is drawn
    NARRATIVE = "narrative"      # where the story is drawn
    SOCIAL = "social"            # where the crowd is drawn
    SPATIAL = "spatial"          # where the geometry is drawn


class IntersectionKind(Enum):
    """How two projected perspectives relate where they cross."""
    REINFORCING = "reinforcing"      # the perspectives amplify the same concern
    CONFLICTING = "conflicting"      # the perspectives pull in opposite directions
    COMPLEMENTARY = "complementary"  # the perspectives cover different concerns
    MASKING = "masking"            # one perspective occludes the other


class LatticeState(Enum):
    """State of a per-scene perspective lattice."""
    UNORIENTED = "unoriented"    # no orientation set yet
    ORIENTED = "oriented"        # oriented to the scene context
    PROJECTED = "projected"      # perspectives have projected their concerns
    INTERSECTED = "intersected"  # lattice edges have formed
    FOCUSED = "focused"          # the lattice has condensed to a focus
    RESOLVED = "resolved"        # conflicts have settled


class FocusCoherence(Enum):
    """How coherent the lattice's multi-perspective focus is."""
    FRAGMENTED = "fragmented"    # perspectives disagree widely
    PARTIAL = "partial"          # some perspectives agree
    COHERENT = "coherent"        # most perspectives agree
    LOCKED = "locked"            # the lattice has settled on a single focus


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PerspectiveNode:
    """A single perspective held against the scene."""
    node_id: str
    kind: PerspectiveKind
    weight: float = 0.5                  # 0.0-1.0, how strongly this perspective presses
    focus_target: str = ""                # what the perspective is concerned with
    projected_intensity: float = 0.0      # 0.0-1.0, how strongly it projected this cycle
    state: LatticeState = LatticeState.UNORIENTED
    created_at: float = field(default_factory=time.time)


@dataclass
class LatticeEdge:
    """An intersection between two projected perspectives."""
    edge_id: str
    node_a_id: str
    node_b_id: str
    intersection_kind: IntersectionKind
    weight: float = 0.0                   # 0.0-1.0, how strongly they cross
    created_at: float = field(default_factory=time.time)


@dataclass
class SceneOrientation:
    """How the lattice is oriented to a scene."""
    scene_id: str
    anchor_point: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    framing: str = "default"
    oriented_at: float = field(default_factory=time.time)


@dataclass
class PerspectiveLattice:
    """Per-scene lattice of co-existing perspectives."""
    scene_id: str
    nodes: Dict[str, PerspectiveNode] = field(default_factory=dict)
    edges: Dict[str, LatticeEdge] = field(default_factory=dict)
    orientation: Optional[SceneOrientation] = None
    state: LatticeState = LatticeState.UNORIENTED
    focus_coherence: FocusCoherence = FocusCoherence.FRAGMENTED
    focus_score: float = 0.0              # 0.0-1.0
    total_oriented: int = 0
    total_projected: int = 0
    total_intersected: int = 0
    total_focused: int = 0
    total_resolved: int = 0
    total_conflicts_damped: int = 0


# =============================================================================
# Projector
# =============================================================================

class EnginePerspectiveLatticeProjector:
    """
    Thread-safe singleton orchestrating a lattice of co-existing
    perspectives over one or more scenes.

    Usage:
        projector = EnginePerspectiveLatticeProjector.get_instance()
        projector.register_scene("courtyard")
        projector.orient_scene("courtyard", 1.0, 0.5, 0.0, "wide")
        projector.add_perspective("courtyard", "cam1", PerspectiveKind.CAMERA, 0.7, "the gate")
        projector.cycle()
        state = projector.get_scene_state("courtyard")
    """

    _instance: Optional["EnginePerspectiveLatticeProjector"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _INTERSECT_THRESHOLD = 0.3          # weight needed to form a lattice edge
    _FOCUS_MAX_NODES = 8               # nodes that contribute to the focus
    _RESOLVE_CONFLICT_DECAY = 0.2      # weight lost per cycle on conflicting edges
    _MAX_NODES_PER_SCENE = 20
    _MAX_EDGES_PER_SCENE = 60
    _MAX_SCENES = 30
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._scenes: Dict[str, PerspectiveLattice] = {}
        self._phase: PerspectivePhase = PerspectivePhase.ORIENT
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EnginePerspectiveLatticeProjector":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    def _init_stats(self) -> None:
        self._stats = {
            "total_scenes": 0,
            "total_nodes": 0,
            "total_edges": 0,
            "total_oriented": 0,
            "total_projected": 0,
            "total_intersected": 0,
            "total_focused": 0,
            "total_resolved": 0,
            "total_conflicts_damped": 0,
            "open_nodes": 0,
            "avg_intensity": 0.0,
            "avg_edge_weight": 0.0,
            "focus_coherence": FocusCoherence.FRAGMENTED.value,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._scenes:
            return
        intensities: List[float] = []
        edge_weights: List[float] = []
        open_nodes = 0
        coherence_votes: List[FocusCoherence] = []
        for lattice in self._scenes.values():
            for node in lattice.nodes.values():
                if node.state in (LatticeState.PROJECTED, LatticeState.INTERSECTED,
                                  LatticeState.FOCUSED, LatticeState.RESOLVED):
                    open_nodes += 1
                    intensities.append(node.projected_intensity)
            for edge in lattice.edges.values():
                edge_weights.append(edge.weight)
            coherence_votes.append(lattice.focus_coherence)
        self._stats["total_scenes"] = len(self._scenes)
        self._stats["total_nodes"] = sum(len(l.nodes) for l in self._scenes.values())
        self._stats["total_edges"] = sum(len(l.edges) for l in self._scenes.values())
        self._stats["open_nodes"] = open_nodes
        self._stats["avg_intensity"] = (
            sum(intensities) / len(intensities) if intensities else 0.0
        )
        self._stats["avg_edge_weight"] = (
            sum(edge_weights) / len(edge_weights) if edge_weights else 0.0
        )
        self._stats["focus_coherence"] = self._derive_focus_coherence(coherence_votes).value

    def _derive_focus_coherence(self, votes: List[FocusCoherence]) -> FocusCoherence:
        if not votes:
            return FocusCoherence.FRAGMENTED
        # Rank coherence levels and take the median vote across scenes.
        rank = {
            FocusCoherence.FRAGMENTED: 0,
            FocusCoherence.PARTIAL: 1,
            FocusCoherence.COHERENT: 2,
            FocusCoherence.LOCKED: 3,
        }
        inverse = {v: k for k, v in rank.items()}
        ordered = sorted(rank[v] for v in votes)
        median = ordered[len(ordered) // 2]
        return inverse[median]

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Scene Management
    # -------------------------------------------------------------------------

    def register_scene(self, scene_id: str) -> Dict[str, Any]:
        """Register a new scene for perspective lattice projection."""
        with self._global_lock:
            if scene_id in self._scenes:
                return {"error": f"Scene already registered: {scene_id}"}
            if len(self._scenes) >= self._MAX_SCENES:
                return {"error": f"Scene cap reached ({self._MAX_SCENES})"}
            lattice = PerspectiveLattice(scene_id=scene_id)
            self._scenes[scene_id] = lattice
            self._record_event("scene_registered", {"scene_id": scene_id})
            return {
                "scene_id": scene_id,
                "state": lattice.state.value,
            }

    def remove_scene(self, scene_id: str) -> Dict[str, Any]:
        with self._global_lock:
            lattice = self._scenes.pop(scene_id, None)
            if lattice is None:
                return {"error": f"Scene not found: {scene_id}"}
            self._record_event("scene_removed", {
                "scene_id": scene_id,
                "cleared_nodes": len(lattice.nodes),
                "cleared_edges": len(lattice.edges),
            })
            return {
                "removed": scene_id,
                "cleared_nodes": len(lattice.nodes),
                "cleared_edges": len(lattice.edges),
            }

    def orient_scene(self, scene_id: str, anchor_x: float, anchor_y: float,
                     anchor_z: float, framing: str = "default") -> Dict[str, Any]:
        """Orient a scene's lattice to a context anchor and framing."""
        with self._global_lock:
            lattice = self._scenes.get(scene_id)
            if lattice is None:
                return {"error": f"Scene not found: {scene_id}"}
            orientation = SceneOrientation(
                scene_id=scene_id,
                anchor_point=[float(anchor_x), float(anchor_y), float(anchor_z)],
                framing=framing,
            )
            lattice.orientation = orientation
            lattice.state = LatticeState.ORIENTED
            # Re-orienting demotes nodes back to ORIENTED so they re-project cleanly.
            for node in lattice.nodes.values():
                node.state = LatticeState.ORIENTED
            lattice.total_oriented += 1
            self._record_event("scene_oriented", {
                "scene_id": scene_id,
                "anchor": orientation.anchor_point,
                "framing": framing,
            })
            return {
                "scene_id": scene_id,
                "anchor_point": orientation.anchor_point,
                "framing": framing,
                "state": lattice.state.value,
            }

    def add_perspective(self, scene_id: str, node_id: str, kind: PerspectiveKind,
                        weight: float = 0.5, focus_target: str = "") -> Dict[str, Any]:
        """Add a perspective node to a scene's lattice."""
        with self._global_lock:
            lattice = self._scenes.get(scene_id)
            if lattice is None:
                return {"error": f"Scene not found: {scene_id}"}
            if node_id in lattice.nodes:
                return {"error": f"Perspective already exists: {node_id}"}
            if len(lattice.nodes) >= self._MAX_NODES_PER_SCENE:
                return {"error": f"Node cap reached for scene ({self._MAX_NODES_PER_SCENE})"}
            # A new node starts at the lattice's orientation floor.
            initial_state = (
                LatticeState.ORIENTED if lattice.orientation is not None
                else LatticeState.UNORIENTED
            )
            node = PerspectiveNode(
                node_id=node_id,
                kind=kind,
                weight=max(0.0, min(1.0, weight)),
                focus_target=focus_target,
                state=initial_state,
            )
            lattice.nodes[node_id] = node
            self._record_event("perspective_added", {
                "scene_id": scene_id,
                "node_id": node_id,
                "kind": kind.value,
                "weight": node.weight,
                "focus_target": focus_target,
            })
            return {
                "scene_id": scene_id,
                "node_id": node_id,
                "kind": kind.value,
                "weight": node.weight,
                "focus_target": focus_target,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single perspective lattice cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = PerspectivePhase.ORIENT
            phase_outputs["orient"] = self._phase_orient()
            self._phase = PerspectivePhase.PROJECT
            phase_outputs["project"] = self._phase_project()
            self._phase = PerspectivePhase.INTERSECT
            phase_outputs["intersect"] = self._phase_intersect()
            self._phase = PerspectivePhase.FOCUS
            phase_outputs["focus"] = self._phase_focus()
            self._phase = PerspectivePhase.RESOLVE
            phase_outputs["resolve"] = self._phase_resolve()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_orient(self) -> Dict[str, Any]:
        """Orient phase: confirm each lattice's orientation to its scene."""
        oriented = 0
        for lattice in self._scenes.values():
            # Without an orientation the lattice cannot be projected.
            if lattice.orientation is None:
                continue
            lattice.state = LatticeState.ORIENTED
            for node in lattice.nodes.values():
                node.state = LatticeState.ORIENTED
            oriented += 1
        self._stats["total_oriented"] += oriented
        self._record_event("phase_orient", {"oriented": oriented})
        return {"oriented": oriented}

    def _phase_project(self) -> Dict[str, Any]:
        """Project phase: each perspective node projects its concerns onto the scene."""
        projected = 0
        for lattice in self._scenes.values():
            if lattice.orientation is None:
                continue
            scene_projected = 0
            for node in lattice.nodes.values():
                intensity = self._project_node(lattice, node)
                node.projected_intensity = intensity
                node.state = LatticeState.PROJECTED
                projected += 1
                scene_projected += 1
            lattice.state = LatticeState.PROJECTED
            lattice.total_projected += scene_projected
        self._stats["total_projected"] += projected
        self._record_event("phase_project", {"projected": projected})
        return {"projected": projected}

    def _phase_intersect(self) -> Dict[str, Any]:
        """Intersect phase: find where projected perspectives cross and form edges."""
        formed = 0
        refreshed = 0
        for lattice in self._scenes.values():
            if lattice.state != LatticeState.PROJECTED:
                continue
            # Rebuild edges from current node intensities each cycle.
            lattice.edges.clear()
            scene_formed = 0
            node_list = list(lattice.nodes.values())
            for i in range(len(node_list)):
                for j in range(i + 1, len(node_list)):
                    a = node_list[i]
                    b = node_list[j]
                    weight = self._intersection_weight(a, b)
                    if weight < self._INTERSECT_THRESHOLD:
                        continue
                    kind = self._classify_intersection(a, b, weight)
                    edge = LatticeEdge(
                        edge_id=f"edge_{a.node_id}_{b.node_id}_{self._cycle_count}",
                        node_a_id=a.node_id,
                        node_b_id=b.node_id,
                        intersection_kind=kind,
                        weight=weight,
                    )
                    lattice.edges[edge.edge_id] = edge
                    formed += 1
                    refreshed += 1
                    scene_formed += 1
            if len(lattice.edges) > self._MAX_EDGES_PER_SCENE:
                # Keep the strongest edges when over the cap.
                keep = sorted(
                    lattice.edges.values(),
                    key=lambda e: e.weight,
                    reverse=True,
                )[:self._MAX_EDGES_PER_SCENE]
                lattice.edges = {e.edge_id: e for e in keep}
            lattice.state = LatticeState.INTERSECTED
            lattice.total_intersected += scene_formed
        self._stats["total_intersected"] += formed
        self._record_event("phase_intersect", {
            "formed": formed,
            "refreshed": refreshed,
        })
        return {"formed": formed, "refreshed": refreshed}

    def _phase_focus(self) -> Dict[str, Any]:
        """Focus phase: condense the lattice toward the most coherent multi-perspective whole."""
        focused = 0
        for lattice in self._scenes.values():
            if lattice.state != LatticeState.INTERSECTED:
                continue
            score, coherence = self._compute_focus(lattice)
            lattice.focus_score = score
            lattice.focus_coherence = coherence
            # Promote the strongest nodes into the focus; fade the rest slightly.
            ranked = sorted(
                lattice.nodes.values(),
                key=lambda n: n.projected_intensity,
                reverse=True,
            )
            for idx, node in enumerate(ranked):
                if idx < self._FOCUS_MAX_NODES:
                    node.state = LatticeState.FOCUSED
                else:
                    node.projected_intensity = max(
                        0.0, node.projected_intensity - 0.1
                    )
            lattice.state = LatticeState.FOCUSED
            lattice.total_focused += 1
            focused += 1
        self._stats["total_focused"] += focused
        self._record_event("phase_focus", {"focused": focused})
        return {"focused": focused}

    def _phase_resolve(self) -> Dict[str, Any]:
        """Resolve phase: dampen conflicting edges and settle the lattice."""
        damped = 0
        resolved = 0
        for lattice in self._scenes.values():
            if lattice.state != LatticeState.FOCUSED:
                continue
            scene_damped = 0
            for edge in list(lattice.edges.values()):
                node_a = lattice.nodes.get(edge.node_a_id)
                node_b = lattice.nodes.get(edge.node_b_id)
                if node_a is None or node_b is None:
                    lattice.edges.pop(edge.edge_id, None)
                    continue
                damped_flag = self._resolve_edge(edge, node_a, node_b)
                if damped_flag:
                    damped += 1
                    scene_damped += 1
                # Drop edges that have decayed below the threshold.
                if edge.weight < self._INTERSECT_THRESHOLD:
                    lattice.edges.pop(edge.edge_id, None)
            for node in lattice.nodes.values():
                if node.state == LatticeState.FOCUSED:
                    node.state = LatticeState.RESOLVED
            lattice.state = LatticeState.RESOLVED
            lattice.total_resolved += 1
            lattice.total_conflicts_damped += scene_damped
            resolved += 1
        self._stats["total_resolved"] += resolved
        self._stats["total_conflicts_damped"] += damped
        self._record_event("phase_resolve", {
            "resolved": resolved,
            "damped": damped,
        })
        return {"resolved": resolved, "damped": damped}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _project_node(self, lattice: PerspectiveLattice, node: PerspectiveNode) -> float:
        """Project a single perspective node's concerns onto the scene."""
        # The anchor pulls the projection toward or away from the focus target.
        anchor = lattice.orientation.anchor_point if lattice.orientation else [0.0, 0.0, 0.0]
        anchor_mag = sum(abs(c) for c in anchor) / 3.0
        # Weight is the base; the anchor modulates; a focus target sharpens it.
        base = node.weight
        focus_factor = 0.8 if node.focus_target else 0.5
        intensity = base * (0.6 + anchor_mag * 0.4) * focus_factor
        # Spatial perspectives are sensitive to the anchor; audio less so.
        if node.kind == PerspectiveKind.SPATIAL:
            intensity *= (0.7 + anchor_mag * 0.3)
        elif node.kind == PerspectiveKind.AUDIO:
            intensity *= 0.9
        # A little stochastic jitter keeps the lattice from locking dead.
        intensity += random.uniform(-0.03, 0.03)
        return max(0.0, min(1.0, intensity))

    def _intersection_weight(self, a: PerspectiveNode, b: PerspectiveNode) -> float:
        """How strongly two projected perspectives cross."""
        # Intensity agreement drives the crossing strength.
        agreement = 1.0 - abs(a.projected_intensity - b.projected_intensity)
        crossing = (a.projected_intensity + b.projected_intensity) * 0.5 * agreement
        # A shared focus target sharpens the crossing.
        if a.focus_target and a.focus_target == b.focus_target:
            crossing = min(1.0, crossing + 0.2)
        return max(0.0, min(1.0, crossing))

    def _classify_intersection(self, a: PerspectiveNode, b: PerspectiveNode,
                               weight: float) -> IntersectionKind:
        """Classify how two projected perspectives relate where they cross."""
        complementary_pairs = {
            (PerspectiveKind.CAMERA, PerspectiveKind.AUDIO),
            (PerspectiveKind.AUDIO, PerspectiveKind.CAMERA),
            (PerspectiveKind.SPATIAL, PerspectiveKind.SOCIAL),
            (PerspectiveKind.SOCIAL, PerspectiveKind.SPATIAL),
            (PerspectiveKind.NARRATIVE, PerspectiveKind.CAMERA),
            (PerspectiveKind.CAMERA, PerspectiveKind.NARRATIVE),
        }
        same_target = bool(a.focus_target and a.focus_target == b.focus_target)
        # Same kind on the same target reinforce one another.
        if same_target and a.kind == b.kind:
            return IntersectionKind.REINFORCING
        if (a.kind, b.kind) in complementary_pairs:
            return IntersectionKind.COMPLEMENTARY
        # If one perspective massively outweighs the other, it masks it.
        if a.projected_intensity > 0.0 and b.projected_intensity > 0.0:
            ratio = max(a.projected_intensity, b.projected_intensity) / \
                    min(a.projected_intensity, b.projected_intensity)
            if ratio >= 3.0:
                return IntersectionKind.MASKING
        # Different targets with high weight pull in opposite directions.
        if not same_target and weight >= 0.6:
            return IntersectionKind.CONFLICTING
        return IntersectionKind.COMPLEMENTARY

    def _compute_focus(self, lattice: PerspectiveLattice) -> Tuple[float, FocusCoherence]:
        """Compute the lattice's focus score and coherence level."""
        nodes = list(lattice.nodes.values())
        if not nodes:
            return 0.0, FocusCoherence.FRAGMENTED
        ranked = sorted(nodes, key=lambda n: n.projected_intensity, reverse=True)
        top = ranked[:self._FOCUS_MAX_NODES]
        avg = sum(n.projected_intensity for n in top) / len(top) if top else 0.0
        # Coherence rises when the top nodes agree in intensity.
        if len(top) >= 2:
            spread = max(n.projected_intensity for n in top) - \
                     min(n.projected_intensity for n in top)
        else:
            spread = 0.0
        # Reinforcing edges raise coherence; conflicting edges lower it.
        reinforcing = sum(
            1 for e in lattice.edges.values()
            if e.intersection_kind == IntersectionKind.REINFORCING
        )
        conflicting = sum(
            1 for e in lattice.edges.values()
            if e.intersection_kind == IntersectionKind.CONFLICTING
        )
        coherence_score = avg - spread * 0.5 + reinforcing * 0.05 - conflicting * 0.1
        coherence_score = max(0.0, min(1.0, coherence_score))
        if coherence_score >= 0.75 and conflicting == 0:
            coherence = FocusCoherence.LOCKED
        elif coherence_score >= 0.55:
            coherence = FocusCoherence.COHERENT
        elif coherence_score >= 0.3:
            coherence = FocusCoherence.PARTIAL
        else:
            coherence = FocusCoherence.FRAGMENTED
        return coherence_score, coherence

    def _resolve_edge(self, edge: LatticeEdge, node_a: PerspectiveNode,
                     node_b: PerspectiveNode) -> bool:
        """Resolve a single lattice edge; dampen it if it is conflicting."""
        if edge.intersection_kind == IntersectionKind.CONFLICTING:
            edge.weight = max(0.0, edge.weight - self._RESOLVE_CONFLICT_DECAY)
            # Conflict pulls both nodes' intensity down a little.
            node_a.projected_intensity = max(
                0.0, node_a.projected_intensity - 0.05
            )
            node_b.projected_intensity = max(
                0.0, node_b.projected_intensity - 0.05
            )
            return True
        if edge.intersection_kind == IntersectionKind.REINFORCING:
            # Reinforcing edges settle toward a stable weight.
            edge.weight = min(1.0, edge.weight + 0.05)
        return False

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "scenes": len(self._scenes),
                "stats": dict(self._stats),
            }

    def get_scene_state(self, scene_id: str) -> Dict[str, Any]:
        with self._global_lock:
            lattice = self._scenes.get(scene_id)
            if lattice is None:
                return {"error": f"Scene not found: {scene_id}"}
            return {
                "scene_id": scene_id,
                "state": lattice.state.value,
                "focus_coherence": lattice.focus_coherence.value,
                "focus_score": lattice.focus_score,
                "nodes_count": len(lattice.nodes),
                "edges_count": len(lattice.edges),
                "orientation": (
                    {
                        "anchor_point": lattice.orientation.anchor_point,
                        "framing": lattice.orientation.framing,
                    }
                    if lattice.orientation is not None else None
                ),
                "total_oriented": lattice.total_oriented,
                "total_projected": lattice.total_projected,
                "total_intersected": lattice.total_intersected,
                "total_focused": lattice.total_focused,
                "total_resolved": lattice.total_resolved,
                "total_conflicts_damped": lattice.total_conflicts_damped,
            }

    def get_nodes(self, scene_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            lattice = self._scenes.get(scene_id)
            if lattice is None:
                return {"error": f"Scene not found: {scene_id}"}
            nodes = sorted(
                lattice.nodes.values(),
                key=lambda n: n.created_at,
                reverse=True,
            )[:limit]
            return {
                "scene_id": scene_id,
                "nodes": [
                    {
                        "node_id": n.node_id,
                        "kind": n.kind.value,
                        "weight": n.weight,
                        "focus_target": n.focus_target,
                        "projected_intensity": n.projected_intensity,
                        "state": n.state.value,
                    }
                    for n in nodes
                ],
            }

    def get_edges(self, scene_id: str, limit: int = 30) -> Dict[str, Any]:
        with self._global_lock:
            lattice = self._scenes.get(scene_id)
            if lattice is None:
                return {"error": f"Scene not found: {scene_id}"}
            edges = sorted(
                lattice.edges.values(),
                key=lambda e: e.weight,
                reverse=True,
            )[:limit]
            return {
                "scene_id": scene_id,
                "edges": [
                    {
                        "edge_id": e.edge_id,
                        "node_a_id": e.node_a_id,
                        "node_b_id": e.node_b_id,
                        "intersection_kind": e.intersection_kind.value,
                        "weight": e.weight,
                    }
                    for e in edges
                ],
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Simulation
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic scenes and perspectives, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_scenes()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_scenes(self) -> None:
        """Seed a small synthetic world with scenes and perspective nodes."""
        seed_scenes = [
            ("sim_courtyard", 1.0, 0.5, 0.0, "wide"),
            ("sim_tavern", 0.2, 0.8, 0.1, "intimate"),
            ("sim_ridge", 5.0, 2.0, 0.0, "vista"),
        ]
        for scene_id, ax, ay, az, framing in seed_scenes:
            if scene_id not in self._scenes:
                self.register_scene(scene_id)
            self.orient_scene(scene_id, ax, ay, az, framing)
        # Seed perspective nodes across the scenes.
        seed_perspectives = [
            ("sim_courtyard", "sim_cam_a", PerspectiveKind.CAMERA, 0.7, "the gate"),
            ("sim_courtyard", "sim_aud_a", PerspectiveKind.AUDIO, 0.5, "the gate"),
            ("sim_courtyard", "sim_nar_a", PerspectiveKind.NARRATIVE, 0.6, "the gate"),
            ("sim_courtyard", "sim_soc_a", PerspectiveKind.SOCIAL, 0.4, "the well"),
            ("sim_courtyard", "sim_spa_a", PerspectiveKind.SPATIAL, 0.5, "the well"),
            ("sim_tavern", "sim_cam_b", PerspectiveKind.CAMERA, 0.6, "the hearth"),
            ("sim_tavern", "sim_aud_b", PerspectiveKind.AUDIO, 0.8, "the hearth"),
            ("sim_tavern", "sim_soc_b", PerspectiveKind.SOCIAL, 0.5, "the bar"),
            ("sim_ridge", "sim_cam_c", PerspectiveKind.CAMERA, 0.8, "the valley"),
            ("sim_ridge", "sim_spa_c", PerspectiveKind.SPATIAL, 0.7, "the valley"),
            ("sim_ridge", "sim_nar_c", PerspectiveKind.NARRATIVE, 0.3, "the old road"),
        ]
        for scene_id, node_id, kind, weight, focus_target in seed_perspectives:
            lattice = self._scenes.get(scene_id)
            if lattice is None:
                continue
            if node_id not in lattice.nodes:
                self.add_perspective(
                    scene_id, node_id, kind,
                    weight=weight, focus_target=focus_target,
                )

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._scenes.clear()
            self._events_log.clear()
            self._phase = PerspectivePhase.ORIENT
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
