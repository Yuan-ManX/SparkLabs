"""
SparkLabs Engine - Emergent Topology Composer"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class TopologyPhase(Enum):
    """Phases of the emergent topology cycle."""
    SEED = "seed"            # place initial seed nodes
    FLOW = "flow"            # desire and attention flow along edges
    CONVERGE = "converge"    # flows meet and accumulate at junctions
    CRYSTAL = "crystal"      # new places crystallize at convergence points
    ANNEAL = "anneal"        # topology settles into stable form


class PlaceType(Enum):
    """Types of places in the emergent topology."""
    ORIGIN = "origin"            # starting place
    HUB = "hub"                  # high-convergence meeting point
    PATHWAY = "pathway"          # flow corridor
    LANDMARK = "landmark"        # attractor with narrative weight
    THRESHOLD = "threshold"      # boundary between regions
    REFUGE = "refuge"            # safe, low-flow place
    HAZARD = "hazard"            # repulsive, dangerous place
    RUIN = "ruin"                # faded, abandoned place
    NEXUS = "nexus"              # highest convergence, crystallized


class FlowType(Enum):
    """Types of flows that traverse the topology."""
    MOVEMENT = "movement"        # player traversal
    NARRATIVE = "narrative"      # story-driven flow
    COMMERCE = "commerce"        # economic exchange
    SOCIAL = "social"            # NPC interaction
    EXPLORATION = "exploration"  # curiosity-driven
    CONFLICT = "conflict"        # hostile encounters
    PILGRIMAGE = "pilgrimage"    # goal-directed journey


class PlaceState(Enum):
    """Lifecycle of a place in the topology."""
    DORMANT = "dormant"          # exists but no flow
    FLOWING = "flowing"          # active flow passing through
    CONVERGING = "converging"    # multiple flows meeting
    CRYSTALLIZED = "crystallized"  # stable, established place
    FADING = "fading"            # losing flow, becoming ruin
    ABANDONED = "abandoned"      # no flow for extended period


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TopologyPlace:
    """A place (node) in the emergent topology."""
    place_id: str
    label: str
    place_type: PlaceType
    x: float                       # normalized x (0.0-1.0)
    y: float                       # normalized y (0.0-1.0)
    attraction: float = 0.5        # how strongly it draws flow (0.0-1.0)
    repulsion: float = 0.0         # how strongly it pushes flow away (0.0-1.0)
    flow_accumulated: float = 0.0  # total flow that has passed through
    convergence: float = 0.0       # current convergence level
    state: PlaceState = PlaceState.DORMANT
    connections: List[str] = field(default_factory=list)  # connected place_ids
    narrative_weight: float = 0.0  # story significance
    created_at: float = field(default_factory=time.time)
    last_visited: float = field(default_factory=time.time)
    crystallization_progress: float = 0.0  # 0.0-1.0, toward CRYSTALLIZED


@dataclass
class TopologyFlow:
    """A flow traversing the topology."""
    flow_id: str
    flow_type: FlowType
    source_place: str
    target_place: str
    intensity: float = 0.5
    direction: float = 0.0         # angle in radians
    age: int = 0                   # cycles since spawned
    active: bool = True


@dataclass
class TopologyRegion:
    """A region formed by clustered places."""
    region_id: str
    label: str
    member_places: Set[str] = field(default_factory=set)
    center_x: float = 0.5
    center_y: float = 0.5
    coherence: float = 0.0         # how tightly bound (0.0-1.0)
    created_at: float = field(default_factory=time.time)


# =============================================================================
# Composer
# =============================================================================

class EngineEmergentTopologyComposer:
    """
    Thread-safe singleton orchestrating emergent topology composition.

    Usage:
        composer = EngineEmergentTopologyComposer.get_instance()
        composer.seed_place("p_start", "Origin", PlaceType.ORIGIN, 0.5, 0.5, attraction=0.9)
        composer.seed_place("p_forest", "Forest Edge", PlaceType.PATHWAY, 0.3, 0.6, attraction=0.4)
        composer.connect_places("p_start", "p_forest")
        composer.spawn_flow("f_1", FlowType.MOVEMENT, "p_start", "p_forest", intensity=0.7)
        composer.cycle()
    """

    _instance: Optional["EngineEmergentTopologyComposer"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._places: Dict[str, TopologyPlace] = {}
        self._flows: Deque[TopologyFlow] = deque(maxlen=500)
        self._active_flows: Dict[str, TopologyFlow] = {}
        self._regions: Dict[str, TopologyRegion] = {}
        self._phase: TopologyPhase = TopologyPhase.SEED
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_places": 0,
            "total_flows": 0,
            "active_flows": 0,
            "total_regions": 0,
            "crystallized_places": 0,
            "fading_places": 0,
            "abandoned_places": 0,
            "avg_convergence": 0.0,
            "avg_attraction": 0.0,
            "total_flow_accumulated": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineEmergentTopologyComposer":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Place Management
    # -------------------------------------------------------------------------

    def seed_place(
        self,
        place_id: str,
        label: str,
        place_type: PlaceType,
        x: float,
        y: float,
        attraction: float = 0.5,
        repulsion: float = 0.0,
        narrative_weight: float = 0.0,
    ) -> Dict[str, Any]:
        """Seed a new place in the topology."""
        with self._global_lock:
            if place_id in self._places:
                return {"error": f"Place already exists: {place_id}"}
            place = TopologyPlace(
                place_id=place_id,
                label=label,
                place_type=place_type,
                x=max(0.0, min(1.0, x)),
                y=max(0.0, min(1.0, y)),
                attraction=max(0.0, min(1.0, attraction)),
                repulsion=max(0.0, min(1.0, repulsion)),
                narrative_weight=max(0.0, min(1.0, narrative_weight)),
            )
            self._places[place_id] = place
            self._stats["total_places"] = len(self._places)
            self._record_event("place_seeded", {
                "place_id": place_id, "type": place_type.value, "x": place.x, "y": place.y,
            })
            return {
                "place_id": place_id,
                "label": label,
                "place_type": place_type.value,
                "x": place.x,
                "y": place.y,
                "attraction": place.attraction,
            }

    def remove_place(self, place_id: str) -> Dict[str, Any]:
        """Remove a place from the topology."""
        with self._global_lock:
            if place_id not in self._places:
                return {"error": f"Place not found: {place_id}"}
            p = self._places.pop(place_id)
            # remove from connections
            for other in self._places.values():
                if place_id in other.connections:
                    other.connections.remove(place_id)
            # remove flows involving this place
            for fid in list(self._active_flows.keys()):
                f = self._active_flows[fid]
                if f.source_place == place_id or f.target_place == place_id:
                    del self._active_flows[fid]
            self._stats["total_places"] = len(self._places)
            return {"removed": place_id, "label": p.label}

    def connect_places(self, place_a: str, place_b: str) -> Dict[str, Any]:
        """Connect two places, allowing flow between them."""
        with self._global_lock:
            if place_a not in self._places or place_b not in self._places:
                return {"error": "Place not found"}
            if place_a == place_b:
                return {"error": "Cannot connect place to itself"}
            pa = self._places[place_a]
            pb = self._places[place_b]
            if place_b not in pa.connections:
                pa.connections.append(place_b)
            if place_a not in pb.connections:
                pb.connections.append(place_a)
            self._record_event("places_connected", {
                "place_a": place_a, "place_b": place_b,
            })
            return {
                "place_a": place_a,
                "place_b": place_b,
                "a_connections": pa.connections,
                "b_connections": pb.connections,
            }

    # -------------------------------------------------------------------------
    # Flow Management
    # -------------------------------------------------------------------------

    def spawn_flow(
        self,
        flow_id: str,
        flow_type: FlowType,
        source_place: str,
        target_place: str,
        intensity: float = 0.5,
    ) -> Dict[str, Any]:
        """Spawn a new flow from source to target."""
        with self._global_lock:
            if source_place not in self._places or target_place not in self._places:
                return {"error": "Place not found"}
            source = self._places[source_place]
            target = self._places[target_place]
            # compute direction
            dx = target.x - source.x
            dy = target.y - source.y
            direction = math.atan2(dy, dx)
            flow = TopologyFlow(
                flow_id=flow_id,
                flow_type=flow_type,
                source_place=source_place,
                target_place=target_place,
                intensity=max(0.0, min(1.0, intensity)),
                direction=direction,
            )
            self._active_flows[flow_id] = flow
            self._flows.append(flow)
            self._stats["total_flows"] = len(self._flows)
            self._stats["active_flows"] = len(self._active_flows)
            self._record_event("flow_spawned", {
                "flow_id": flow_id, "type": flow_type.value,
                "source": source_place, "target": target_place,
            })
            return {
                "flow_id": flow_id,
                "flow_type": flow_type.value,
                "source": source_place,
                "target": target_place,
                "intensity": flow.intensity,
                "direction": flow.direction,
            }

    # -------------------------------------------------------------------------
    # Phase: SEED - spontaneous new places
    # -------------------------------------------------------------------------

    def _phase_seed(self) -> Dict[str, Any]:
        """Spontaneously seed new places where attraction is high."""
        seeded = 0
        # find high-attraction areas without nearby places
        for _ in range(3):  # attempt a few times
            x = random.random()
            y = random.random()
            # check distance to existing places
            min_dist = float("inf")
            nearest_id = None
            for pid, p in self._places.items():
                d = math.sqrt((p.x - x) ** 2 + (p.y - y) ** 2)
                if d < min_dist:
                    min_dist = d
                    nearest_id = pid
            # only seed if far enough from existing places
            if min_dist > 0.15 and random.random() < 0.3:
                place_id = f"p_spont_{self._cycle_count}_{seeded}"
                ptype = random.choice([PlaceType.PATHWAY, PlaceType.LANDMARK, PlaceType.REFUGE])
                result = self.seed_place(
                    place_id, f"Spontaneous {seeded}", ptype, x, y,
                    attraction=random.uniform(0.3, 0.6),
                )
                if "error" not in result:
                    seeded += 1
                    # connect to nearest
                    if nearest_id:
                        self.connect_places(place_id, nearest_id)
        return {"spontaneous_seeded": seeded}

    # -------------------------------------------------------------------------
    # Phase: FLOW - advance flows, accumulate at places
    # -------------------------------------------------------------------------

    def _phase_flow(self) -> Dict[str, Any]:
        """Advance active flows and accumulate at target places."""
        advanced = 0
        arrived = 0
        for fid in list(self._active_flows.keys()):
            f = self._active_flows[fid]
            f.age += 1
            # flow arrives at target after 1-2 cycles
            if f.age >= 1:
                target = self._places.get(f.target_place)
                if target:
                    target.flow_accumulated += f.intensity
                    target.convergence = min(1.0, target.convergence + f.intensity * 0.2)
                    target.last_visited = time.time()
                    if target.state == PlaceState.DORMANT:
                        target.state = PlaceState.FLOWING
                    arrived += 1
                # flow expires
                del self._active_flows[fid]
            else:
                advanced += 1
        self._stats["active_flows"] = len(self._active_flows)
        return {"flows_advanced": advanced, "flows_arrived": arrived}

    # -------------------------------------------------------------------------
    # Phase: CONVERGE - accumulate convergence at junctions
    # -------------------------------------------------------------------------

    def _phase_converge(self) -> Dict[str, Any]:
        """Places with multiple connections accumulate convergence."""
        converging = 0
        for p in self._places.values():
            # convergence based on number of connections and flow accumulated
            conn_factor = min(1.0, len(p.connections) / 5.0)
            flow_factor = min(1.0, p.flow_accumulated / 5.0)
            p.convergence = min(1.0, conn_factor * 0.5 + flow_factor * 0.5)
            if p.convergence > 0.5 and p.state == PlaceState.FLOWING:
                p.state = PlaceState.CONVERGING
                converging += 1
                # crystallization progresses
                p.crystallization_progress = min(1.0, p.crystallization_progress + 0.1)
            elif p.convergence > 0.3:
                # slow crystallization
                p.crystallization_progress = min(1.0, p.crystallization_progress + 0.03)
        return {"converging_places": converging}

    # -------------------------------------------------------------------------
    # Phase: CRYSTAL - crystallize places with high convergence
    # -------------------------------------------------------------------------

    def _phase_crystal(self) -> Dict[str, Any]:
        """Crystallize places that have reached sufficient convergence."""
        crystallized = 0
        promoted = 0
        for p in self._places.values():
            if p.crystallization_progress >= 0.8 and p.state in (PlaceState.CONVERGING, PlaceState.FLOWING):
                p.state = PlaceState.CRYSTALLIZED
                crystallized += 1
                # promote type based on convergence
                if p.convergence > 0.8 and p.place_type != PlaceType.NEXUS:
                    old_type = p.place_type
                    p.place_type = PlaceType.NEXUS
                    promoted += 1
                    self._record_event("place_promoted", {
                        "place_id": p.place_id, "from": old_type.value, "to": "nexus",
                    })
                elif p.convergence > 0.6 and p.place_type == PlaceType.PATHWAY:
                    p.place_type = PlaceType.HUB
                    promoted += 1
        return {"crystallized": crystallized, "promoted": promoted}

    # -------------------------------------------------------------------------
    # Phase: ANNEAL - settle topology, fade abandoned places
    # -------------------------------------------------------------------------

    def _phase_anneal(self) -> Dict[str, Any]:
        """Settle topology and fade abandoned places."""
        faded = 0
        abandoned = 0
        smoothed = 0
        now = time.time()
        for p in self._places.values():
            # places not visited recently fade
            age = now - p.last_visited
            if age > 30 and p.state != PlaceState.ABANDONED:
                if p.state == PlaceState.CRYSTALLIZED:
                    # crystallized places resist fading
                    p.state = PlaceState.FADING
                    faded += 1
                elif p.state in (PlaceState.FLOWING, PlaceState.CONVERGING):
                    p.state = PlaceState.FADING
                    faded += 1
            elif age > 60 and p.state == PlaceState.FADING:
                p.state = PlaceState.ABANDONED
                if p.place_type not in (PlaceType.RUIN, PlaceType.HAZARD):
                    p.place_type = PlaceType.RUIN
                abandoned += 1
            # smooth attraction toward convergence equilibrium
            target_attr = 0.3 + p.convergence * 0.5
            drift = (target_attr - p.attraction) * 0.1
            p.attraction = max(0.0, min(1.0, p.attraction + drift))
            smoothed += 1
        # cluster places into regions
        self._form_regions()
        return {
            "faded": faded,
            "abandoned": abandoned,
            "smoothed": smoothed,
            "regions": len(self._regions),
        }

    def _form_regions(self) -> None:
        """Cluster crystallized places into regions."""
        crystallized = {pid: p for pid, p in self._places.items() if p.state == PlaceState.CRYSTALLIZED}
        if len(crystallized) < 2:
            return
        # simple clustering: group by proximity
        assigned: Set[str] = set()
        new_regions: Dict[str, TopologyRegion] = {}
        region_counter = 0
        for pid, p in crystallized.items():
            if pid in assigned:
                continue
            # start a new region
            region_id = f"reg_{region_counter}"
            region_counter += 1
            members = {pid}
            assigned.add(pid)
            # find nearby crystallized places
            for oid, op in crystallized.items():
                if oid in assigned:
                    continue
                d = math.sqrt((p.x - op.x) ** 2 + (p.y - op.y) ** 2)
                if d < 0.25:
                    members.add(oid)
                    assigned.add(oid)
            if len(members) >= 2:
                # compute center
                xs = [crystallized[mid].x for mid in members]
                ys = [crystallized[mid].y for mid in members]
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                # coherence based on average convergence
                avg_conv = sum(crystallized[mid].convergence for mid in members) / len(members)
                region = TopologyRegion(
                    region_id=region_id,
                    label=f"Region {region_counter}",
                    member_places=members,
                    center_x=cx,
                    center_y=cy,
                    coherence=avg_conv,
                )
                new_regions[region_id] = region
        self._regions = new_regions
        self._stats["total_regions"] = len(self._regions)

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single emergent topology cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = TopologyPhase.SEED
            phase_outputs["seed"] = self._phase_seed()
            self._phase = TopologyPhase.FLOW
            phase_outputs["flow"] = self._phase_flow()
            self._phase = TopologyPhase.CONVERGE
            phase_outputs["converge"] = self._phase_converge()
            self._phase = TopologyPhase.CRYSTAL
            phase_outputs["crystal"] = self._phase_crystal()
            self._phase = TopologyPhase.ANNEAL
            phase_outputs["anneal"] = self._phase_anneal()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple cycles in sequence."""
        if cycles < 1:
            cycles = 1
        if cycles > 100:
            cycles = 100
        for _ in range(cycles):
            self.cycle()
        return {"cycles_run": cycles, "stats": dict(self._stats)}

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_place(self, place_id: str) -> Dict[str, Any]:
        """Get a place's state."""
        with self._global_lock:
            p = self._places.get(place_id)
            if p is None:
                return {"error": f"Place not found: {place_id}"}
            return {
                "place_id": p.place_id,
                "label": p.label,
                "place_type": p.place_type.value,
                "x": p.x,
                "y": p.y,
                "attraction": p.attraction,
                "repulsion": p.repulsion,
                "flow_accumulated": p.flow_accumulated,
                "convergence": p.convergence,
                "state": p.state.value,
                "connections": p.connections,
                "narrative_weight": p.narrative_weight,
                "crystallization_progress": p.crystallization_progress,
            }

    def get_all_places(self) -> List[Dict[str, Any]]:
        """Get all places in the topology."""
        with self._global_lock:
            return [
                {
                    "place_id": p.place_id,
                    "label": p.label,
                    "place_type": p.place_type.value,
                    "x": p.x,
                    "y": p.y,
                    "attraction": p.attraction,
                    "convergence": p.convergence,
                    "state": p.state.value,
                    "connections_count": len(p.connections),
                    "flow_accumulated": p.flow_accumulated,
                }
                for p in self._places.values()
            ]

    def get_regions(self) -> List[Dict[str, Any]]:
        """Get all formed regions."""
        with self._global_lock:
            return [
                {
                    "region_id": r.region_id,
                    "label": r.label,
                    "member_count": len(r.member_places),
                    "members": list(r.member_places),
                    "center_x": r.center_x,
                    "center_y": r.center_y,
                    "coherence": r.coherence,
                }
                for r in self._regions.values()
            ]

    def get_active_flows(self) -> List[Dict[str, Any]]:
        """Get currently active flows."""
        with self._global_lock:
            return [
                {
                    "flow_id": f.flow_id,
                    "flow_type": f.flow_type.value,
                    "source": f.source_place,
                    "target": f.target_place,
                    "intensity": f.intensity,
                    "age": f.age,
                }
                for f in self._active_flows.values()
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get composer status."""
        with self._global_lock:
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "stats": dict(self._stats),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the entire composer."""
        with self._global_lock:
            count = len(self._places)
            self._places.clear()
            self._flows.clear()
            self._active_flows.clear()
            self._regions.clear()
            self._events_log.clear()
            self._cycle_count = 0
            self._phase = TopologyPhase.SEED
            self._stats = {
                "total_places": 0,
                "total_flows": 0,
                "active_flows": 0,
                "total_regions": 0,
                "crystallized_places": 0,
                "fading_places": 0,
                "abandoned_places": 0,
                "avg_convergence": 0.0,
                "avg_attraction": 0.0,
                "total_flow_accumulated": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "places_removed": count}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _update_stats(self) -> None:
        if self._places:
            self._stats["avg_convergence"] = sum(p.convergence for p in self._places.values()) / len(self._places)
            self._stats["avg_attraction"] = sum(p.attraction for p in self._places.values()) / len(self._places)
            self._stats["total_flow_accumulated"] = sum(p.flow_accumulated for p in self._places.values())
            self._stats["crystallized_places"] = sum(1 for p in self._places.values() if p.state == PlaceState.CRYSTALLIZED)
            self._stats["fading_places"] = sum(1 for p in self._places.values() if p.state == PlaceState.FADING)
            self._stats["abandoned_places"] = sum(1 for p in self._places.values() if p.state == PlaceState.ABANDONED)
        self._stats["active_flows"] = len(self._active_flows)

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "timestamp": time.time(),
            "type": event_type,
            **payload,
        })
