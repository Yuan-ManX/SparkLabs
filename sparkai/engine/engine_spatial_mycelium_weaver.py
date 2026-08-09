"""
SparkLabs Engine - Spatial Mycelium Weaver"""

from __future__ import annotations

import logging
import math
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

class HyphaType(Enum):
    """Types of hyphae in the mycelium network."""
    EXPLORATORY = "exploratory"    # pathfinding probes
    TRANSPORT = "transport"        # logistics corridors
    NUTRIENT = "nutrient"          # resource distribution
    DEFENSE = "defense"            # border patrol
    REPRODUCTIVE = "reproductive"  # spawn point generation


class MyceliumPhase(Enum):
    """Phases of the mycelium weaver cycle."""
    GERMINATE = "germinate"
    EXTEND = "extend"
    ANASTOMOSE = "anastomose"
    FRUIT = "fruit"
    DECOMPOSE = "decompose"


class MyceliumEvent(Enum):
    """Events that occur during the mycelium cycle."""
    GERMINATION = "germination"
    HYPHAL_EXTENSION = "hyphal_extension"
    ANASTOMOSIS = "anastomosis"
    FRUITING = "fruiting"
    DECOMPOSITION = "decomposition"
    NUTRIENT_SURGE = "nutrient_surge"
    NETWORK_PRUNING = "network_pruning"


# =============================================================================
# Default Parameters by Hypha Type
# =============================================================================

# Default vitality for each hypha type
DEFAULT_HYPHA_VITALITY: Dict[HyphaType, float] = {
    HyphaType.EXPLORATORY: 0.4,
    HyphaType.TRANSPORT: 0.85,
    HyphaType.NUTRIENT: 0.6,
    HyphaType.DEFENSE: 0.9,
    HyphaType.REPRODUCTIVE: 0.5,
}

# Default flow capacity for each hypha type
DEFAULT_HYPHA_FLOW_CAPACITY: Dict[HyphaType, float] = {
    HyphaType.EXPLORATORY: 0.3,
    HyphaType.TRANSPORT: 0.95,
    HyphaType.NUTRIENT: 0.6,
    HyphaType.DEFENSE: 0.4,
    HyphaType.REPRODUCTIVE: 0.5,
}

# Default growth rate for each hypha type
DEFAULT_HYPHA_GROWTH: Dict[HyphaType, float] = {
    HyphaType.EXPLORATORY: 0.15,
    HyphaType.TRANSPORT: 0.05,
    HyphaType.NUTRIENT: 0.08,
    HyphaType.DEFENSE: 0.03,
    HyphaType.REPRODUCTIVE: 0.1,
}

# Default vitality decay rate per cycle
DEFAULT_HYPHA_DECAY: Dict[HyphaType, float] = {
    HyphaType.EXPLORATORY: 0.08,
    HyphaType.TRANSPORT: 0.02,
    HyphaType.NUTRIENT: 0.05,
    HyphaType.DEFENSE: 0.01,
    HyphaType.REPRODUCTIVE: 0.06,
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class MyceliumNode:
    """A location node in the mycelium network."""
    node_id: str
    label: str
    # Position in the game world (x, y, z)
    position: Tuple[float, float, float]
    # Nutrient level at this node (0.0-1.0)
    nutrient_level: float
    # Whether this node is a source of nutrients
    is_source: bool
    # Whether this node is a sink (consumes nutrients)
    is_sink: bool
    # Number of hyphae connected to this node
    degree: int = 0
    last_updated: float = field(default_factory=time.time)


@dataclass
class HyphaLink:
    """A hypha connecting two nodes in the mycelium network."""
    hypha_id: str
    hypha_type: HyphaType
    source_id: str
    target_id: str
    # Current flow through this hypha (0.0-1.0)
    flow: float
    # Maximum flow capacity
    flow_capacity: float
    # Vitality / health (0.0-1.0)
    vitality: float
    # Target vitality (for restoration)
    target_vitality: float
    # Growth progress (0.0-1.0), 1.0 = fully established
    growth: float
    # Length of the hypha (distance between nodes)
    length: float
    # Whether this hypha is part of a loop (post-anastomosis)
    in_loop: bool = False
    age_cycles: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class FruitingBody:
    """A waypoint / spawn point that emerged from dense network regions."""
    fruit_id: str
    node_id: str
    # Type of fruiting body
    fruit_type: str
    # Maturity (0.0-1.0), spawns when mature
    maturity: float
    # Nutrient cost to produce
    nutrient_cost: float
    # Whether this fruit has spawned
    spawned: bool = False
    age_cycles: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class MyceliumStats:
    """Aggregate statistics for the mycelium weaver."""
    total_nodes: int = 0
    total_hyphae: int = 0
    total_fruiting_bodies: int = 0
    total_events: int = 0
    total_germinations: int = 0
    total_extensions: int = 0
    total_anastomoses: int = 0
    total_fruittings: int = 0
    total_decompositions: int = 0
    total_nutrient_surges: int = 0
    total_prunings: int = 0
    total_loops: int = 0
    avg_vitality: float = 0.0
    avg_flow: float = 0.0
    avg_growth: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Engine Spatial Mycelium Weaver
# =============================================================================

class EngineSpatialMyceliumWeaver:
    """
    Singleton engine subsystem that models spatial connectivity as a
    mycelium network growing through the game world.

    The weaver runs a 5-phase cycle:
      1. GERMINATE   - New hyphae sprout from nutrient-rich nodes
      2. EXTEND      - Existing hyphae extend toward nearby nodes
      3. ANASTOMOSE  - Growing hyphae fronts meet and fuse into loops
      4. FRUIT       - Dense network regions produce fruiting bodies
      5. DECOMPOSE   - Unused hyphae decay and recycle their nutrients

    The mycelial metaphor ensures spatial networks feel alive: paths grow
    organically toward interesting locations, strengthen with use, and
    atrophy without traffic, creating a self-maintaining navigation graph.
    """

    _instance: Optional["EngineSpatialMyceliumWeaver"] = None
    _instance_lock = threading.Lock()

    # Configuration
    MAX_NODES = 80
    MAX_HYPHAE = 300
    MAX_FRUITING_BODIES = 60
    MAX_EVENT_HISTORY = 200
    MAX_HYPHAE_PER_NODE = 10
    # Minimum and maximum vitality
    MIN_VITALITY = 0.0
    MAX_VITALITY = 1.0
    # How fast vitality moves toward target
    VITALITY_ADJUSTMENT_RATE = 0.1
    # Natural vitality restoration per cycle (for used hyphae)
    VITALITY_RESTORATION = 0.05
    # Minimum and maximum flow
    MIN_FLOW = 0.0
    MAX_FLOW = 1.0
    # How fast flow responds to demand
    FLOW_ADJUSTMENT_RATE = 0.15
    # Minimum and maximum nutrient
    MIN_NUTRIENT = 0.0
    MAX_NUTRIENT = 1.0
    # Nutrient generation rate for source nodes
    NUTRIENT_GENERATION_RATE = 0.1
    # Nutrient consumption rate for sink nodes
    NUTRIENT_CONSUMPTION_RATE = 0.08
    # Minimum vitality before decomposition
    DECOMPOSITION_THRESHOLD = 0.1
    # Minimum growth for a hypha to be considered established
    ESTABLISHED_GROWTH_THRESHOLD = 0.7
    # Fruit formation threshold (node degree and nutrient)
    FRUIT_DEGREE_THRESHOLD = 3
    FRUIT_NUTRIENT_THRESHOLD = 0.6
    # Fruit maturation rate per cycle
    FRUIT_MATURATION_RATE = 0.12
    # Probability of spontaneous germination at a source node
    GERMINATION_PROBABILITY = 0.2
    # Maximum hypha length for connection
    MAX_HYPHA_LENGTH = 100.0
    # Anastomosis probability when two fronts are near
    ANASTOMOSIS_PROBABILITY = 0.3

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._nodes: Dict[str, MyceliumNode] = {}
        self._hyphae: Dict[str, HyphaLink] = {}
        self._fruiting_bodies: Deque[FruitingBody] = deque(
            maxlen=self.MAX_FRUITING_BODIES
        )
        self._event_history: Deque[Dict[str, Any]] = deque(
            maxlen=self.MAX_EVENT_HISTORY
        )
        self._stats = MyceliumStats()
        self._cycle_count: int = 0
        self._active: bool = False
        self._hypha_counter: int = 0
        self._fruit_counter: int = 0
        self._event_counter: int = 0

    @classmethod
    def get_instance(cls) -> "EngineSpatialMyceliumWeaver":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Node Management
    # -------------------------------------------------------------------------

    def register_node(
        self,
        node_id: str,
        label: str,
        position: Optional[List[float]] = None,
        nutrient_level: Optional[float] = None,
        is_source: bool = False,
        is_sink: bool = False,
    ) -> Dict[str, Any]:
        """Register a new location node in the mycelium network."""
        with self._lock:
            if node_id in self._nodes:
                return {"error": f"Node already registered: {node_id}"}
            if len(self._nodes) >= self.MAX_NODES:
                return {"error": "Maximum nodes reached"}

            if position is None:
                position = (0.0, 0.0, 0.0)
            elif len(position) < 3:
                position = tuple(position) + (0.0,) * (3 - len(position))
            else:
                position = tuple(position[:3])

            if nutrient_level is None:
                nutrient_level = 0.5 if is_source else 0.3
            nutrient_level = max(self.MIN_NUTRIENT, min(self.MAX_NUTRIENT, float(nutrient_level)))

            node = MyceliumNode(
                node_id=node_id,
                label=label,
                position=position,
                nutrient_level=nutrient_level,
                is_source=is_source,
                is_sink=is_sink,
            )
            self._nodes[node_id] = node
            self._stats.total_nodes = len(self._nodes)
            return self._node_to_dict(node)

    def get_node(self, node_id: str) -> Dict[str, Any]:
        """Get the state of a specific node."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return {"error": f"Node not found: {node_id}"}
            return self._node_to_dict(node)

    def list_nodes(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List all nodes in the network."""
        with self._lock:
            nodes = list(self._nodes.values())[:limit]
            return [self._node_to_dict(n) for n in nodes]

    def remove_node(self, node_id: str) -> Dict[str, Any]:
        """Remove a node and all its connected hyphae."""
        with self._lock:
            if node_id not in self._nodes:
                return {"removed": False, "node_id": node_id}
            # Remove all hyphae connected to this node
            to_remove = [
                hid for hid, h in self._hyphae.items()
                if h.source_id == node_id or h.target_id == node_id
            ]
            for hid in to_remove:
                del self._hyphae[hid]
            del self._nodes[node_id]
            self._stats.total_nodes = len(self._nodes)
            self._stats.total_hyphae = len(self._hyphae)
            return {"removed": True, "node_id": node_id, "hyphae_removed": len(to_remove)}

    def set_node_nutrient(
        self, node_id: str, nutrient_level: float, description: str = ""
    ) -> Dict[str, Any]:
        """Set the nutrient level at a node."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return {"error": f"Node not found: {node_id}"}
            nutrient_level = max(self.MIN_NUTRIENT, min(self.MAX_NUTRIENT, float(nutrient_level)))
            node.nutrient_level = nutrient_level
            node.last_updated = time.time()
            return {
                "node_id": node_id,
                "nutrient_level": nutrient_level,
                "description": description,
            }

    # -------------------------------------------------------------------------
    # Hypha Management
    # -------------------------------------------------------------------------

    def register_hypha(
        self,
        source_id: str,
        target_id: str,
        hypha_type: str = "exploratory",
        flow: Optional[float] = None,
        vitality: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Register a new hypha connecting two nodes."""
        with self._lock:
            if source_id not in self._nodes:
                return {"error": f"Source node not found: {source_id}"}
            if target_id not in self._nodes:
                return {"error": f"Target node not found: {target_id}"}
            if source_id == target_id:
                return {"error": "Source and target cannot be the same node"}
            if len(self._hyphae) >= self.MAX_HYPHAE:
                return {"error": "Maximum hyphae reached"}

            # Check degree limits
            source_node = self._nodes[source_id]
            target_node = self._nodes[target_id]
            if source_node.degree >= self.MAX_HYPHAE_PER_NODE:
                return {"error": f"Source node at max degree: {source_id}"}
            if target_node.degree >= self.MAX_HYPHAE_PER_NODE:
                return {"error": f"Target node at max degree: {target_id}"}

            try:
                htype = HyphaType(hypha_type)
            except ValueError:
                return {"error": f"Unknown hypha type: {hypha_type}"}

            # Check for duplicate connection
            for h in self._hyphae.values():
                if ((h.source_id == source_id and h.target_id == target_id)
                        or (h.source_id == target_id and h.target_id == source_id)):
                    return {"error": f"Hypha already exists between {source_id} and {target_id}"}

            # Calculate length
            length = self._distance(source_node.position, target_node.position)
            if length > self.MAX_HYPHA_LENGTH:
                return {"error": f"Hypha length {length:.1f} exceeds max {self.MAX_HYPHA_LENGTH}"}

            if flow is None:
                flow = 0.2
            flow = max(self.MIN_FLOW, min(self.MAX_FLOW, float(flow)))

            if vitality is None:
                vitality = DEFAULT_HYPHA_VITALITY.get(htype, 0.5)
            vitality = max(self.MIN_VITALITY, min(self.MAX_VITALITY, float(vitality)))

            flow_capacity = DEFAULT_HYPHA_FLOW_CAPACITY.get(htype, 0.5)

            self._hypha_counter += 1
            hypha_id = f"hypha_{self._hypha_counter}"
            hypha = HyphaLink(
                hypha_id=hypha_id,
                hypha_type=htype,
                source_id=source_id,
                target_id=target_id,
                flow=flow,
                flow_capacity=flow_capacity,
                vitality=vitality,
                target_vitality=vitality,
                growth=0.3,
                length=length,
            )
            self._hyphae[hypha_id] = hypha
            source_node.degree += 1
            target_node.degree += 1

            self._record_event(
                MyceliumEvent.GERMINATION,
                intensity=vitality,
                node_ids=[source_id, target_id],
                hypha_ids=[hypha_id],
                description=f"Hypha '{hypha_id}' germinated: {source_id} -> {target_id} ({htype.value})",
            )
            self._stats.total_hyphae = len(self._hyphae)
            self._stats.total_germinations += 1
            return self._hypha_to_dict(hypha)

    def get_hypha(self, hypha_id: str) -> Dict[str, Any]:
        """Get the state of a specific hypha."""
        with self._lock:
            hypha = self._hyphae.get(hypha_id)
            if hypha is None:
                return {"error": f"Hypha not found: {hypha_id}"}
            return self._hypha_to_dict(hypha)

    def list_hyphae(
        self, hypha_type: Optional[str] = None, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """List hyphae, optionally filtered by type."""
        with self._lock:
            hyphae = list(self._hyphae.values())
            if hypha_type:
                try:
                    htype = HyphaType(hypha_type)
                    hyphae = [h for h in hyphae if h.hypha_type == htype]
                except ValueError:
                    return []
            hyphae = hyphae[:limit]
            return [self._hypha_to_dict(h) for h in hyphae]

    def remove_hypha(self, hypha_id: str) -> Dict[str, Any]:
        """Remove a hypha from the network."""
        with self._lock:
            hypha = self._hyphae.get(hypha_id)
            if hypha is None:
                return {"removed": False, "hypha_id": hypha_id}
            # Decrement node degrees
            source = self._nodes.get(hypha.source_id)
            target = self._nodes.get(hypha.target_id)
            if source:
                source.degree = max(0, source.degree - 1)
            if target:
                target.degree = max(0, target.degree - 1)
            del self._hyphae[hypha_id]
            self._stats.total_hyphae = len(self._hyphae)
            return {"removed": True, "hypha_id": hypha_id}

    def set_hypha_flow(self, hypha_id: str, flow: float, description: str = "") -> Dict[str, Any]:
        """Set the flow through a hypha (simulating traffic)."""
        with self._lock:
            hypha = self._hyphae.get(hypha_id)
            if hypha is None:
                return {"error": f"Hypha not found: {hypha_id}"}
            flow = max(self.MIN_FLOW, min(hypha.flow_capacity, float(flow)))
            hypha.flow = flow
            # High flow restores vitality
            if flow > 0.5:
                hypha.target_vitality = min(self.MAX_VITALITY, hypha.target_vitality + 0.1)
                self._record_event(
                    MyceliumEvent.NUTRIENT_SURGE,
                    intensity=flow,
                    node_ids=[hypha.source_id, hypha.target_id],
                    hypha_ids=[hypha_id],
                    description=f"Nutrient surge on '{hypha_id}': flow={flow:.2f}",
                )
                self._stats.total_nutrient_surges += 1
            return {
                "hypha_id": hypha_id,
                "flow": flow,
                "target_vitality": hypha.target_vitality,
                "description": description,
            }

    # -------------------------------------------------------------------------
    # Fruiting Body Management
    # -------------------------------------------------------------------------

    def list_fruiting_bodies(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List fruiting bodies (waypoints) in the network."""
        with self._lock:
            fruits = list(self._fruiting_bodies)[:limit]
            return [self._fruit_to_dict(f) for f in fruits]

    def get_fruiting_body(self, fruit_id: str) -> Dict[str, Any]:
        """Get a specific fruiting body."""
        with self._lock:
            for f in self._fruiting_bodies:
                if f.fruit_id == fruit_id:
                    return self._fruit_to_dict(f)
            return {"error": f"Fruiting body not found: {fruit_id}"}

    def remove_fruiting_body(self, fruit_id: str) -> Dict[str, Any]:
        """Remove a fruiting body."""
        with self._lock:
            before = len(self._fruiting_bodies)
            self._fruiting_bodies = deque(
                (f for f in self._fruiting_bodies if f.fruit_id != fruit_id),
                maxlen=self.MAX_FRUITING_BODIES,
            )
            removed = before - len(self._fruiting_bodies)
            return {"removed": removed > 0, "fruit_id": fruit_id}

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single mycelium weaver cycle.

        Phases: GERMINATE -> EXTEND -> ANASTOMOSE -> FRUIT -> DECOMPOSE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: GERMINATE - new hyphae sprout from nutrient-rich nodes
            germinate_info = self._germinate_phase()

            # Phase 2: EXTEND - existing hyphae grow toward targets
            extend_info = self._extend_phase()

            # Phase 3: ANASTOMOSE - hyphae fronts meet and fuse into loops
            anastomose_info = self._anastomosis_phase()

            # Phase 4: FRUIT - dense network regions produce fruiting bodies
            fruit_info = self._fruit_phase()

            # Phase 5: DECOMPOSE - unused hyphae decay and recycle
            decompose_info = self._decompose_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()

            phase = MyceliumPhase.DECOMPOSE
            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "germinate": germinate_info,
                "extend": extend_info,
                "anastomose": anastomose_info,
                "fruit": fruit_info,
                "decompose": decompose_info,
                "total_nodes": len(self._nodes),
                "total_hyphae": len(self._hyphae),
                "total_fruiting_bodies": len(self._fruiting_bodies),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _germinate_phase(self) -> Dict[str, Any]:
        """Phase 1: New hyphae sprout from nutrient-rich nodes."""
        germinations = 0
        for node in list(self._nodes.values()):
            if (node.nutrient_level > 0.5
                    and node.degree < self.MAX_HYPHAE_PER_NODE
                    and len(self._hyphae) < self.MAX_HYPHAE
                    and random.random() < self.GERMINATION_PROBABILITY * node.nutrient_level):
                # Find a nearby node to connect to
                candidates = []
                for other_id, other in self._nodes.items():
                    if other_id == node.node_id:
                        continue
                    if other.degree >= self.MAX_HYPHAE_PER_NODE:
                        continue
                    # Check if already connected
                    already = False
                    for h in self._hyphae.values():
                        if ((h.source_id == node.node_id and h.target_id == other_id)
                                or (h.source_id == other_id and h.target_id == node.node_id)):
                            already = True
                            break
                    if already:
                        continue
                    dist = self._distance(node.position, other.position)
                    if dist < self.MAX_HYPHA_LENGTH:
                        candidates.append((other_id, dist))

                if candidates:
                    candidates.sort(key=lambda x: x[1])
                    target_id = candidates[0][0]
                    htype = random.choice(list(HyphaType))
                    result = self.register_hypha(
                        node.node_id, target_id, htype.value
                    )
                    if "error" not in result:
                        germinations += 1

        return {"germinations": germinations}

    def _extend_phase(self) -> Dict[str, Any]:
        """Phase 2: Existing hyphae extend (grow toward full establishment)."""
        extensions = 0
        for hypha in self._hyphae.values():
            hypha.age_cycles += 1
            growth_rate = DEFAULT_HYPHA_GROWTH.get(hypha.hypha_type, 0.08)
            if hypha.growth < 1.0:
                hypha.growth = min(1.0, hypha.growth + growth_rate)
                extensions += 1
            # Vitality moves toward target
            if hypha.vitality < hypha.target_vitality:
                hypha.vitality = min(
                    hypha.target_vitality,
                    hypha.vitality + self.VITALITY_ADJUSTMENT_RATE,
                )
            # High flow restores vitality
            if hypha.flow > 0.3:
                hypha.vitality = min(
                    self.MAX_VITALITY,
                    hypha.vitality + self.VITALITY_RESTORATION * hypha.flow,
                )

        # Nutrient flow from sources to sinks
        for node in self._nodes.values():
            if node.is_source:
                node.nutrient_level = min(
                    self.MAX_NUTRIENT,
                    node.nutrient_level + self.NUTRIENT_GENERATION_RATE,
                )
            elif node.is_sink:
                node.nutrient_level = max(
                    self.MIN_NUTRIENT,
                    node.nutrient_level - self.NUTRIENT_CONSUMPTION_RATE,
                )

        if extensions > 0:
            self._record_event(
                MyceliumEvent.HYPHAL_EXTENSION,
                intensity=0.4,
                node_ids=[],
                hypha_ids=[],
                description=f"{extensions} hyphae extended",
            )
        self._stats.total_extensions += extensions
        return {"extensions": extensions}

    def _anastomosis_phase(self) -> Dict[str, Any]:
        """Phase 3: Hyphae fronts meet and fuse into loops."""
        anastomoses = 0
        hypha_list = list(self._hyphae.values())
        # Check pairs of hyphae that share no nodes but are close
        for i in range(len(hypha_list)):
            for j in range(i + 1, len(hypha_list)):
                a = hypha_list[i]
                b = hypha_list[j]
                if a.in_loop or b.in_loop:
                    continue
                # Check if they share a node (already connected)
                shared = {a.source_id, a.target_id} & {b.source_id, b.target_id}
                if shared:
                    continue
                # Check if connecting would create a loop
                # (A->B and C->D, if we connect B->C and A,B,C,D are distinct, it's a path)
                # Anastomosis: create a new hypha between the endpoints
                if random.random() < self.ANASTOMOSIS_PROBABILITY * 0.1:
                    # Pick endpoints to connect
                    endpoint_a = a.target_id if random.random() < 0.5 else a.source_id
                    endpoint_b = b.target_id if random.random() < 0.5 else b.source_id
                    if endpoint_a == endpoint_b:
                        continue
                    if len(self._hyphae) >= self.MAX_HYPHAE:
                        break
                    result = self.register_hypha(
                        endpoint_a, endpoint_b, "transport"
                    )
                    if "error" not in result:
                        a.in_loop = True
                        b.in_loop = True
                        new_hypha = self._hyphae.get(result["hypha_id"])
                        if new_hypha:
                            new_hypha.in_loop = True
                        anastomoses += 1
                        self._record_event(
                            MyceliumEvent.ANASTOMOSIS,
                            intensity=0.7,
                            node_ids=[endpoint_a, endpoint_b],
                            hypha_ids=[result["hypha_id"]],
                            description=f"Anastomosis: {a.hypha_id} and {b.hypha_id} fused via {result['hypha_id']}",
                        )

        self._stats.total_anastomoses += anastomoses
        self._stats.total_loops = sum(1 for h in self._hyphae.values() if h.in_loop)
        return {"anastomoses": anastomoses, "total_loops": self._stats.total_loops}

    def _fruit_phase(self) -> Dict[str, Any]:
        """Phase 4: Dense network regions produce fruiting bodies."""
        fruitings = 0
        for node in list(self._nodes.values()):
            if (node.degree >= self.FRUIT_DEGREE_THRESHOLD
                    and node.nutrient_level >= self.FRUIT_NUTRIENT_THRESHOLD
                    and len(self._fruiting_bodies) < self.MAX_FRUITING_BODIES
                    and random.random() < 0.15):
                # Check if this node already has an unspawned fruit
                existing = any(
                    f.node_id == node.node_id and not f.spawned
                    for f in self._fruiting_bodies
                )
                if existing:
                    continue
                self._fruit_counter += 1
                fruit = FruitingBody(
                    fruit_id=f"fruit_{self._fruit_counter}",
                    node_id=node.node_id,
                    fruit_type=random.choice(["waypoint", "spawn_point", "landmark", "fast_travel"]),
                    maturity=0.2,
                    nutrient_cost=0.3,
                )
                self._fruiting_bodies.append(fruit)
                node.nutrient_level = max(
                    self.MIN_NUTRIENT, node.nutrient_level - fruit.nutrient_cost
                )
                fruitings += 1
                self._record_event(
                    MyceliumEvent.FRUITING,
                    intensity=node.nutrient_level,
                    node_ids=[node.node_id],
                    hypha_ids=[],
                    description=f"Fruiting body '{fruit.fruit_id}' emerged at '{node.label}' ({fruit.fruit_type})",
                )

        # Mature existing fruits
        for fruit in self._fruiting_bodies:
            if not fruit.spawned:
                fruit.age_cycles += 1
                fruit.maturity = min(1.0, fruit.maturity + self.FRUIT_MATURATION_RATE)
                if fruit.maturity >= 1.0:
                    fruit.spawned = True

        self._stats.total_fruittings += fruitings
        self._stats.total_fruiting_bodies = len(self._fruiting_bodies)
        return {
            "fruitings": fruitings,
            "mature_fruits": sum(1 for f in self._fruiting_bodies if f.spawned),
        }

    def _decompose_phase(self) -> Dict[str, Any]:
        """Phase 5: Unused hyphae decay and recycle their nutrients."""
        decompositions = 0
        prunings = 0
        to_remove: List[str] = []
        for hypha_id, hypha in self._hyphae.items():
            # Vitality decay based on hypha type
            decay = DEFAULT_HYPHA_DECAY.get(hypha.hypha_type, 0.05)
            # Low-flow hyphae decay faster
            if hypha.flow < 0.1:
                decay *= 2.0
            hypha.vitality = max(self.MIN_VITALITY, hypha.vitality - decay)
            hypha.target_vitality = max(self.MIN_VITALITY, hypha.target_vitality - decay * 0.5)

            if hypha.vitality < self.DECOMPOSITION_THRESHOLD:
                to_remove.append(hypha_id)
                # Recycle nutrients to connected nodes
                source = self._nodes.get(hypha.source_id)
                target = self._nodes.get(hypha.target_id)
                recycled = hypha.vitality * 0.1
                if source:
                    source.nutrient_level = min(
                        self.MAX_NUTRIENT, source.nutrient_level + recycled
                    )
                if target:
                    target.nutrient_level = min(
                        self.MAX_NUTRIENT, target.nutrient_level + recycled
                    )
                if hypha.flow < 0.05:
                    prunings += 1
                else:
                    decompositions += 1

        for hid in to_remove:
            self.remove_hypha(hid)

        if to_remove:
            self._record_event(
                MyceliumEvent.DECOMPOSITION,
                intensity=0.3,
                node_ids=[],
                hypha_ids=to_remove[:5],
                description=f"{len(to_remove)} hyphae decomposed ({prunings} pruned)",
            )
        self._stats.total_decompositions += decompositions
        self._stats.total_prunings += prunings
        return {
            "decompositions": decompositions,
            "prunings": prunings,
            "total_removed": len(to_remove),
        }

    # -------------------------------------------------------------------------
    # Simulation & Status
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles and return the final status."""
        cycles = max(1, min(100, int(cycles)))
        last_cycle = None
        for _ in range(cycles):
            last_cycle = self.run_cycle()
        return {
            "cycles_run": cycles,
            "last_cycle": last_cycle,
            "status": self.get_status(),
        }

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the mycelium weaver."""
        with self._lock:
            self._stats.total_nodes = len(self._nodes)
            self._stats.total_hyphae = len(self._hyphae)
            self._stats.total_fruiting_bodies = len(self._fruiting_bodies)
            self._stats.total_events = len(self._event_history)
            self._stats.total_loops = sum(1 for h in self._hyphae.values() if h.in_loop)
            self._update_avg_metrics()
            return {
                "total_nodes": self._stats.total_nodes,
                "total_hyphae": self._stats.total_hyphae,
                "total_fruiting_bodies": self._stats.total_fruiting_bodies,
                "total_loops": self._stats.total_loops,
                "active": self._active,
                "cycle_count": self._cycle_count,
                "stats": {
                    "total_events": self._stats.total_events,
                    "total_germinations": self._stats.total_germinations,
                    "total_extensions": self._stats.total_extensions,
                    "total_anastomoses": self._stats.total_anastomoses,
                    "total_fruittings": self._stats.total_fruittings,
                    "total_decompositions": self._stats.total_decompositions,
                    "total_nutrient_surges": self._stats.total_nutrient_surges,
                    "total_prunings": self._stats.total_prunings,
                    "avg_vitality": round(self._stats.avg_vitality, 4),
                    "avg_flow": round(self._stats.avg_flow, 4),
                    "avg_growth": round(self._stats.avg_growth, 4),
                    "last_cycle_time_ms": self._stats.last_cycle_time_ms,
                },
            }

    def get_events(
        self, node_id: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent mycelium events, optionally filtered by node."""
        with self._lock:
            events = list(self._event_history)
            if node_id:
                events = [e for e in events if node_id in e.get("node_ids", [])]
            return events[:limit]

    def reset(self) -> Dict[str, Any]:
        """Reset the mycelium weaver to its initial state."""
        with self._lock:
            self._nodes.clear()
            self._hyphae.clear()
            self._fruiting_bodies.clear()
            self._event_history.clear()
            self._stats = MyceliumStats()
            self._cycle_count = 0
            self._active = False
            self._hypha_counter = 0
            self._fruit_counter = 0
            self._event_counter = 0
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _distance(
        self, a: Tuple[float, float, float], b: Tuple[float, float, float]
    ) -> float:
        """Calculate Euclidean distance between two 3D points."""
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def _record_event(
        self,
        event: MyceliumEvent,
        intensity: float,
        node_ids: List[str],
        hypha_ids: List[str],
        description: str,
    ) -> None:
        """Record a mycelium event in the history."""
        self._event_counter += 1
        self._event_history.append({
            "event_id": f"me_{self._event_counter}",
            "event_type": event.value,
            "intensity": round(max(0.0, min(1.0, intensity)), 4),
            "node_ids": node_ids,
            "hypha_ids": hypha_ids,
            "description": description,
            "timestamp": time.time(),
        })

    def _update_avg_metrics(self) -> None:
        """Update average metrics from current hyphae."""
        if not self._hyphae:
            self._stats.avg_vitality = 0.0
            self._stats.avg_flow = 0.0
            self._stats.avg_growth = 0.0
            return
        n = len(self._hyphae)
        self._stats.avg_vitality = sum(h.vitality for h in self._hyphae.values()) / n
        self._stats.avg_flow = sum(h.flow for h in self._hyphae.values()) / n
        self._stats.avg_growth = sum(h.growth for h in self._hyphae.values()) / n

    def _node_to_dict(self, node: MyceliumNode) -> Dict[str, Any]:
        """Convert a node to a dictionary representation."""
        return {
            "node_id": node.node_id,
            "label": node.label,
            "position": list(node.position),
            "nutrient_level": round(node.nutrient_level, 4),
            "is_source": node.is_source,
            "is_sink": node.is_sink,
            "degree": node.degree,
            "last_updated": node.last_updated,
        }

    def _hypha_to_dict(self, hypha: HyphaLink) -> Dict[str, Any]:
        """Convert a hypha to a dictionary representation."""
        return {
            "hypha_id": hypha.hypha_id,
            "hypha_type": hypha.hypha_type.value,
            "source_id": hypha.source_id,
            "target_id": hypha.target_id,
            "flow": round(hypha.flow, 4),
            "flow_capacity": round(hypha.flow_capacity, 4),
            "vitality": round(hypha.vitality, 4),
            "target_vitality": round(hypha.target_vitality, 4),
            "growth": round(hypha.growth, 4),
            "length": round(hypha.length, 4),
            "in_loop": hypha.in_loop,
            "age_cycles": hypha.age_cycles,
            "timestamp": hypha.timestamp,
        }

    def _fruit_to_dict(self, fruit: FruitingBody) -> Dict[str, Any]:
        """Convert a fruiting body to a dictionary representation."""
        return {
            "fruit_id": fruit.fruit_id,
            "node_id": fruit.node_id,
            "fruit_type": fruit.fruit_type,
            "maturity": round(fruit.maturity, 4),
            "nutrient_cost": round(fruit.nutrient_cost, 4),
            "spawned": fruit.spawned,
            "age_cycles": fruit.age_cycles,
            "timestamp": fruit.timestamp,
        }
