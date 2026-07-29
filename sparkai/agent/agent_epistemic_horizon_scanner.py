"""
SparkLabs Agent - Epistemic Horizon Scanner

The AgentEpistemicHorizonScanner models how agents scan their epistemic
horizons - the shifting boundary between what they know, what they know
they don't know, and what they don't know they don't know. Rather than
treating knowledge as a static inventory, the scanner treats it as a
living frontier that expands, contracts, and sometimes inverts when
assumptions collapse.

Knowledge is not a territory to be mapped once - it is a horizon to be
scanned continuously. An agent's epistemic horizon has three zones:
  - The Known: facts the agent holds with confidence
  - The Known-Unknown: gaps the agent is aware of and can explore
  - The Unknown-Unknown: blind spots the agent cannot even perceive

The scanner models how these zones shift. Exploration converts
known-unknowns into knowns. Surprise converts unknown-unknowns into
known-unknowns (the moment of "I didn't know I didn't know that!").
And doubt can demote knowns back into known-unknowns when confidence
shatters.

The scanner also models epistemic inversion - the rare moment when an
agent discovers that something it held as known is actually wrong, and
the entire horizon reconfigures around the new truth. This is the
deepest form of learning: not adding to what you know, but restructuring
what you thought you knew.

Architecture:
  SCAN     ->  EXPLORE  ->  ASSIMILATE ->  DOUBT    ->  INVERT
  (scan    (explore    (new          (confidence   (horizon
   the     known-      knowledge     erosion      inverts when
   horizon unknowns    assimilates   demotes      core beliefs
   for     and         into the      knowns to    collapse)
   gaps    blind       known zone)   known-       ) 
   spots)  spots)                    unknowns)

Thread-safe singleton: use get_instance().
"""

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

class ScannerPhase(Enum):
    """Phases of the epistemic horizon scan cycle."""
    SCAN = "scan"           # scan the horizon for gaps and blind spots
    EXPLORE = "explore"     # explore known-unknowns and blind spots
    ASSIMILATE = "assimilate"  # new knowledge enters the known zone
    DOUBT = "doubt"         # confidence erosion demotes knowns
    INVERT = "invert"       # horizon inverts when core beliefs collapse


class KnowledgeZone(Enum):
    """The three zones of the epistemic horizon."""
    KNOWN = "known"                 # confident knowledge
    KNOWN_UNKNOWN = "known_unknown"  # aware of the gap
    UNKNOWN_UNKNOWN = "unknown_unknown"  # blind spot
    DISPUTED = "disputed"           # contested knowledge
    COLLAPSED = "collapsed"         # belief that has collapsed


class KnowledgeDomain(Enum):
    """Domains of knowledge an agent can hold."""
    SPATIAL = "spatial"             # where things are
    SOCIAL = "social"               # who others are
    MECHANICAL = "mechanical"       # how things work
    NARRATIVE = "narrative"         # what the story is
    TEMPORAL = "temporal"           # when things happen
    CAUSAL = "causal"               # why things happen
    SELF = "self"                   # who the agent is
    OTHER = "other"                 # what others think


class BeliefStability(Enum):
    """How stable a belief is against doubt."""
    BEDROCK = "bedrock"             # foundational, rarely doubted
    SOLID = "solid"                 # well-established
    WOBBLY = "wobbly"               # starting to shake
    CRUMBLING = "crumbling"         # near collapse
    SHATTERED = "shattered"         # collapsed


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class KnowledgeNode:
    """A node in the agent's knowledge graph."""
    node_id: str
    domain: KnowledgeDomain
    label: str
    zone: KnowledgeZone = KnowledgeZone.UNKNOWN_UNKNOWN
    confidence: float = 0.0         # how confident (0.0-1.0)
    stability: BeliefStability = BeliefStability.SHATTERED
    evidence_count: int = 0
    contradictions: int = 0
    dependencies: List[str] = field(default_factory=list)  # node_ids this depends on
    dependents: List[str] = field(default_factory=list)    # node_ids that depend on this
    last_scanned: float = field(default_factory=time.time)
    discovered_at: float = field(default_factory=time.time)
    content: str = ""


@dataclass
class EpistemicAgent:
    """Per-agent scanner state."""
    agent_id: str
    nodes: Dict[str, KnowledgeNode] = field(default_factory=dict)
    total_discoveries: int = 0
    total_assimilations: int = 0
    total_doubts: int = 0
    total_inversions: int = 0
    epistemic_curiosity: float = 0.5  # drive to explore (0.0-1.0)
    horizon_breadth: float = 0.0     # how wide the known zone is
    horizon_depth: float = 0.0       # how deep the confidence goes
    blind_spot_count: int = 0


@dataclass
class EpistemicInversion:
    """Record of a horizon inversion event."""
    inversion_id: str
    agent_id: str
    collapsed_node: str
    cascaded_nodes: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# Scanner
# =============================================================================

class AgentEpistemicHorizonScanner:
    """
    Thread-safe singleton orchestrating epistemic horizon scanning.

    Usage:
        scanner = AgentEpistemicHorizonScanner.get_instance()
        scanner.register_agent("hero", curiosity=0.8)
        scanner.add_node("hero", "k_forest_loc", KnowledgeDomain.SPATIAL,
                        "Forest Location", KnowledgeZone.KNOWN_UNKNOWN)
        scanner.explore("hero", "k_forest_loc")
        scanner.cycle()
    """

    _instance: Optional["AgentEpistemicHorizonScanner"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._agents: Dict[str, EpistemicAgent] = {}
        self._inversions: Deque[EpistemicInversion] = deque(maxlen=100)
        self._phase: ScannerPhase = ScannerPhase.SCAN
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_agents": 0,
            "total_nodes": 0,
            "known_nodes": 0,
            "known_unknown_nodes": 0,
            "unknown_unknown_nodes": 0,
            "disputed_nodes": 0,
            "collapsed_nodes": 0,
            "total_discoveries": 0,
            "total_assimilations": 0,
            "total_doubts": 0,
            "total_inversions": 0,
            "avg_confidence": 0.0,
            "avg_horizon_breadth": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentEpistemicHorizonScanner":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Agent Registration
    # -------------------------------------------------------------------------

    def register_agent(self, agent_id: str, curiosity: float = 0.5) -> Dict[str, Any]:
        """Register a new agent with the scanner."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            self._agents[agent_id] = EpistemicAgent(
                agent_id=agent_id,
                epistemic_curiosity=max(0.0, min(1.0, curiosity)),
            )
            self._stats["total_agents"] = len(self._agents)
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "curiosity": self._agents[agent_id].epistemic_curiosity,
                "nodes": 0,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent from the scanner."""
        with self._global_lock:
            if agent_id not in self._agents:
                return {"error": f"Agent not found: {agent_id}"}
            a = self._agents.pop(agent_id)
            self._stats["total_agents"] = len(self._agents)
            return {"removed": agent_id, "nodes": len(a.nodes)}

    # -------------------------------------------------------------------------
    # Node Management
    # -------------------------------------------------------------------------

    def add_node(
        self,
        agent_id: str,
        node_id: str,
        domain: KnowledgeDomain,
        label: str,
        zone: KnowledgeZone = KnowledgeZone.UNKNOWN_UNKNOWN,
        confidence: float = 0.0,
        content: str = "",
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Add a knowledge node to an agent's horizon."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            if node_id in a.nodes:
                return {"error": f"Node already exists: {node_id}"}
            node = KnowledgeNode(
                node_id=node_id,
                domain=domain,
                label=label,
                zone=zone,
                confidence=max(0.0, min(1.0, confidence)),
                stability=self._confidence_to_stability(confidence),
                content=content,
                dependencies=dependencies or [],
            )
            a.nodes[node_id] = node
            # update dependents
            for dep_id in node.dependencies:
                dep = a.nodes.get(dep_id)
                if dep and node_id not in dep.dependents:
                    dep.dependents.append(node_id)
            self._update_horizon_metrics(agent_id)
            self._record_event("node_added", {
                "agent_id": agent_id, "node_id": node_id,
                "zone": zone.value, "domain": domain.value,
            })
            return {
                "node_id": node_id,
                "domain": domain.value,
                "label": label,
                "zone": zone.value,
                "confidence": node.confidence,
            }

    def explore(self, agent_id: str, node_id: str) -> Dict[str, Any]:
        """Agent explores a known-unknown, potentially assimilating it."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            node = a.nodes.get(node_id)
            if node is None:
                return {"error": f"Node not found: {node_id}"}
            if node.zone != KnowledgeZone.KNOWN_UNKNOWN:
                return {"error": f"Node is not explorable (zone={node.zone.value})"}
            # exploration has a chance of success based on curiosity
            success_chance = a.epistemic_curiosity * 0.7 + 0.2
            if random.random() < success_chance:
                # exploration succeeds - move toward known
                node.confidence = min(1.0, node.confidence + 0.3)
                node.evidence_count += 1
                if node.confidence > 0.5:
                    node.zone = KnowledgeZone.KNOWN
                    node.stability = self._confidence_to_stability(node.confidence)
                    a.total_assimilations += 1
                    self._record_event("knowledge_assimilated", {
                        "agent_id": agent_id, "node_id": node_id,
                        "confidence": node.confidence,
                    })
                return {
                    "node_id": node_id,
                    "explored": True,
                    "assimilated": node.zone == KnowledgeZone.KNOWN,
                    "confidence": node.confidence,
                    "zone": node.zone.value,
                }
            else:
                # exploration fails but gains some confidence
                node.confidence = min(1.0, node.confidence + 0.1)
                node.evidence_count += 1
                return {
                    "node_id": node_id,
                    "explored": False,
                    "confidence": node.confidence,
                    "zone": node.zone.value,
                }

    def discover_blind_spot(
        self,
        agent_id: str,
        node_id: str,
        domain: KnowledgeDomain,
        label: str,
    ) -> Dict[str, Any]:
        """Agent discovers an unknown-unknown, converting it to known-unknown."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            if node_id in a.nodes:
                node = a.nodes[node_id]
                if node.zone == KnowledgeZone.UNKNOWN_UNKNOWN:
                    node.zone = KnowledgeZone.KNOWN_UNKNOWN
                    a.total_discoveries += 1
                    self._record_event("blind_spot_discovered", {
                        "agent_id": agent_id, "node_id": node_id,
                    })
                    return {"node_id": node_id, "discovered": True, "zone": node.zone.value}
                return {"node_id": node_id, "discovered": False, "zone": node.zone.value}
            # create new node as known-unknown
            result = self.add_node(agent_id, node_id, domain, label, KnowledgeZone.KNOWN_UNKNOWN, 0.1)
            if "error" not in result:
                a.total_discoveries += 1
                self._record_event("blind_spot_discovered", {
                    "agent_id": agent_id, "node_id": node_id,
                })
            return result

    def challenge(self, agent_id: str, node_id: str) -> Dict[str, Any]:
        """Challenge a known node, potentially introducing doubt."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            node = a.nodes.get(node_id)
            if node is None:
                return {"error": f"Node not found: {node_id}"}
            if node.zone != KnowledgeZone.KNOWN:
                return {"error": f"Node is not known (zone={node.zone.value})"}
            # challenge reduces confidence
            node.contradictions += 1
            node.confidence = max(0.0, node.confidence - 0.25)
            node.stability = self._confidence_to_stability(node.confidence)
            if node.confidence < 0.3:
                node.zone = KnowledgeZone.DISPUTED
                a.total_doubts += 1
                self._record_event("knowledge_disputed", {
                    "agent_id": agent_id, "node_id": node_id,
                    "confidence": node.confidence,
                })
            return {
                "node_id": node_id,
                "challenged": True,
                "confidence": node.confidence,
                "zone": node.zone.value,
                "stability": node.stability.value,
            }

    # -------------------------------------------------------------------------
    # Phase: SCAN - scan the horizon for gaps and blind spots
    # -------------------------------------------------------------------------

    def _phase_scan(self) -> Dict[str, Any]:
        """Scan horizons for gaps and discover blind spots."""
        discovered = 0
        for a in self._agents.values():
            # curiosity drives blind spot discovery
            if random.random() > a.epistemic_curiosity * 0.3:
                continue
            # discover a random blind spot in a domain the agent has little knowledge of
            domains_present = {n.domain for n in a.nodes.values()}
            all_domains = set(KnowledgeDomain)
            missing_domains = all_domains - domains_present
            if missing_domains:
                domain = random.choice(list(missing_domains))
                node_id = f"k_bs_{a.agent_id}_{len(a.nodes)}"
                result = self.discover_blind_spot(a.agent_id, node_id, domain, f"Blind spot in {domain.value}")
                if "error" not in result:
                    discovered += 1
            # also scan for unknown-unknowns that might be adjacent to known nodes
            for node in list(a.nodes.values()):
                if node.zone != KnowledgeZone.KNOWN:
                    continue
                # chance to discover adjacent unknown
                if random.random() < 0.15:
                    adj_id = f"k_adj_{node.node_id}_{len(a.nodes)}"
                    adj_domain = node.domain
                    result = self.add_node(
                        a.agent_id, adj_id, adj_domain,
                        f"Adjacent to {node.label}",
                        KnowledgeZone.UNKNOWN_UNKNOWN, 0.0,
                    )
                    if "error" not in result:
                        discovered += 1
        return {"blind_spots_discovered": discovered}

    # -------------------------------------------------------------------------
    # Phase: EXPLORE - explore known-unknowns
    # -------------------------------------------------------------------------

    def _phase_explore(self) -> Dict[str, Any]:
        """Agents explore their known-unknowns."""
        explored = 0
        for a in self._agents.values():
            known_unknowns = [n for n in a.nodes.values() if n.zone == KnowledgeZone.KNOWN_UNKNOWN]
            if not known_unknowns:
                continue
            # explore a random subset based on curiosity
            num_to_explore = max(1, int(len(known_unknowns) * a.epistemic_curiosity * 0.5))
            for node in random.sample(known_unknowns, min(num_to_explore, len(known_unknowns))):
                result = self.explore(a.agent_id, node.node_id)
                if result.get("explored"):
                    explored += 1
        return {"nodes_explored": explored}

    # -------------------------------------------------------------------------
    # Phase: ASSIMILATE - new knowledge stabilizes
    # -------------------------------------------------------------------------

    def _phase_assimilate(self) -> Dict[str, Any]:
        """Assimilated knowledge stabilizes and spreads to dependents."""
        assimilated = 0
        for a in self._agents.values():
            for node in a.nodes.values():
                if node.zone != KnowledgeZone.KNOWN:
                    continue
                # known nodes gain stability over time
                if node.stability == BeliefStability.WOBBLY and node.confidence > 0.6:
                    node.stability = BeliefStability.SOLID
                    assimilated += 1
                elif node.stability == BeliefStability.SOLID and node.confidence > 0.8 and node.evidence_count > 3:
                    node.stability = BeliefStability.BEDROCK
                    assimilated += 1
                # knowledge spreads to dependent nodes
                for dep_id in node.dependents:
                    dep = a.nodes.get(dep_id)
                    if dep is None:
                        continue
                    if dep.zone == KnowledgeZone.UNKNOWN_UNKNOWN:
                        dep.zone = KnowledgeZone.KNOWN_UNKNOWN
                        dep.confidence = max(dep.confidence, node.confidence * 0.3)
        return {"nodes_stabilized": assimilated}

    # -------------------------------------------------------------------------
    # Phase: DOUBT - confidence erosion
    # -------------------------------------------------------------------------

    def _phase_doubt(self) -> Dict[str, Any]:
        """Random doubts erode confidence in known nodes."""
        doubted = 0
        for a in self._agents.values():
            for node in a.nodes.values():
                if node.zone != KnowledgeZone.KNOWN:
                    continue
                # bedrock beliefs rarely doubt
                doubt_chance = {
                    BeliefStability.BEDROCK: 0.02,
                    BeliefStability.SOLID: 0.05,
                    BeliefStability.WOBBLY: 0.15,
                    BeliefStability.CRUMBLING: 0.3,
                    BeliefStability.SHATTERED: 0.0,
                }
                chance = doubt_chance.get(node.stability, 0.05)
                if random.random() < chance:
                    node.confidence = max(0.0, node.confidence - 0.08)
                    node.stability = self._confidence_to_stability(node.confidence)
                    if node.confidence < 0.3:
                        node.zone = KnowledgeZone.DISPUTED
                        a.total_doubts += 1
                        doubted += 1
        return {"nodes_doubted": doubted}

    # -------------------------------------------------------------------------
    # Phase: INVERT - horizon inverts when core beliefs collapse
    # -------------------------------------------------------------------------

    def _phase_invert(self) -> Dict[str, Any]:
        """Horizon inverts when bedrock beliefs collapse."""
        inversions = 0
        cascaded = 0
        for a in self._agents.values():
            for node in list(a.nodes.values()):
                # only shattered bedrock beliefs trigger inversion
                if node.stability != BeliefStability.SHATTERED:
                    continue
                if node.zone != KnowledgeZone.DISPUTED and node.zone != KnowledgeZone.COLLAPSED:
                    continue
                # collapse this node
                node.zone = KnowledgeZone.COLLAPSED
                inversion_id = f"inv_{a.agent_id}_{a.total_inversions}"
                inversion = EpistemicInversion(
                    inversion_id=inversion_id,
                    agent_id=a.agent_id,
                    collapsed_node=node.node_id,
                )
                # cascade to dependents
                for dep_id in node.dependents:
                    dep = a.nodes.get(dep_id)
                    if dep is None:
                        continue
                    if dep.zone == KnowledgeZone.KNOWN:
                        dep.confidence = max(0.0, dep.confidence - 0.4)
                        dep.stability = self._confidence_to_stability(dep.confidence)
                        if dep.confidence < 0.3:
                            dep.zone = KnowledgeZone.DISPUTED
                        inversion.cascaded_nodes.append(dep_id)
                        cascaded += 1
                a.total_inversions += 1
                inversions += 1
                self._inversions.append(inversion)
                self._record_event("horizon_inversion", {
                    "agent_id": a.agent_id, "node_id": node.node_id,
                    "cascaded": len(inversion.cascaded_nodes),
                })
        self._stats["total_inversions"] = sum(a.total_inversions for a in self._agents.values())
        return {
            "inversions": inversions,
            "cascaded_nodes": cascaded,
        }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single epistemic horizon scan cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = ScannerPhase.SCAN
            phase_outputs["scan"] = self._phase_scan()
            self._phase = ScannerPhase.EXPLORE
            phase_outputs["explore"] = self._phase_explore()
            self._phase = ScannerPhase.ASSIMILATE
            phase_outputs["assimilate"] = self._phase_assimilate()
            self._phase = ScannerPhase.DOUBT
            phase_outputs["doubt"] = self._phase_doubt()
            self._phase = ScannerPhase.INVERT
            phase_outputs["invert"] = self._phase_invert()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            # update per-agent horizon metrics
            for aid in self._agents:
                self._update_horizon_metrics(aid)
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

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Get an agent's full epistemic state."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            zone_counts = {z.value: 0 for z in KnowledgeZone}
            for node in a.nodes.values():
                zone_counts[node.zone.value] += 1
            return {
                "agent_id": agent_id,
                "total_nodes": len(a.nodes),
                "zone_counts": zone_counts,
                "epistemic_curiosity": a.epistemic_curiosity,
                "horizon_breadth": a.horizon_breadth,
                "horizon_depth": a.horizon_depth,
                "total_discoveries": a.total_discoveries,
                "total_assimilations": a.total_assimilations,
                "total_doubts": a.total_doubts,
                "total_inversions": a.total_inversions,
                "nodes": [
                    {
                        "node_id": n.node_id,
                        "domain": n.domain.value,
                        "label": n.label,
                        "zone": n.zone.value,
                        "confidence": n.confidence,
                        "stability": n.stability.value,
                        "evidence_count": n.evidence_count,
                        "contradictions": n.contradictions,
                        "dependencies": n.dependencies,
                        "dependents": n.dependents,
                    }
                    for n in a.nodes.values()
                ],
            }

    def get_inversions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent epistemic inversions."""
        with self._global_lock:
            recent = list(self._inversions)[-limit:]
            return [
                {
                    "inversion_id": inv.inversion_id,
                    "agent_id": inv.agent_id,
                    "collapsed_node": inv.collapsed_node,
                    "cascaded_nodes": inv.cascaded_nodes,
                    "timestamp": inv.timestamp,
                }
                for inv in recent
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get scanner status."""
        with self._global_lock:
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "stats": dict(self._stats),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the entire scanner."""
        with self._global_lock:
            count = len(self._agents)
            self._agents.clear()
            self._inversions.clear()
            self._events_log.clear()
            self._cycle_count = 0
            self._phase = ScannerPhase.SCAN
            self._stats = {
                "total_agents": 0,
                "total_nodes": 0,
                "known_nodes": 0,
                "known_unknown_nodes": 0,
                "unknown_unknown_nodes": 0,
                "disputed_nodes": 0,
                "collapsed_nodes": 0,
                "total_discoveries": 0,
                "total_assimilations": 0,
                "total_doubts": 0,
                "total_inversions": 0,
                "avg_confidence": 0.0,
                "avg_horizon_breadth": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "agents_removed": count}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _confidence_to_stability(self, confidence: float) -> BeliefStability:
        """Map confidence to stability."""
        if confidence >= 0.85:
            return BeliefStability.BEDROCK
        elif confidence >= 0.6:
            return BeliefStability.SOLID
        elif confidence >= 0.35:
            return BeliefStability.WOBBLY
        elif confidence >= 0.1:
            return BeliefStability.CRUMBLING
        else:
            return BeliefStability.SHATTERED

    def _update_horizon_metrics(self, agent_id: str) -> None:
        """Update horizon breadth and depth for an agent."""
        a = self._agents.get(agent_id)
        if a is None:
            return
        total = len(a.nodes)
        if total == 0:
            a.horizon_breadth = 0.0
            a.horizon_depth = 0.0
            return
        known = sum(1 for n in a.nodes.values() if n.zone == KnowledgeZone.KNOWN)
        a.horizon_breadth = known / total
        known_nodes = [n for n in a.nodes.values() if n.zone == KnowledgeZone.KNOWN]
        if known_nodes:
            a.horizon_depth = sum(n.confidence for n in known_nodes) / len(known_nodes)
        else:
            a.horizon_depth = 0.0
        a.blind_spot_count = sum(1 for n in a.nodes.values() if n.zone == KnowledgeZone.UNKNOWN_UNKNOWN)

    def _update_stats(self) -> None:
        all_nodes = [n for a in self._agents.values() for n in a.nodes.values()]
        if all_nodes:
            self._stats["total_nodes"] = len(all_nodes)
            self._stats["known_nodes"] = sum(1 for n in all_nodes if n.zone == KnowledgeZone.KNOWN)
            self._stats["known_unknown_nodes"] = sum(1 for n in all_nodes if n.zone == KnowledgeZone.KNOWN_UNKNOWN)
            self._stats["unknown_unknown_nodes"] = sum(1 for n in all_nodes if n.zone == KnowledgeZone.UNKNOWN_UNKNOWN)
            self._stats["disputed_nodes"] = sum(1 for n in all_nodes if n.zone == KnowledgeZone.DISPUTED)
            self._stats["collapsed_nodes"] = sum(1 for n in all_nodes if n.zone == KnowledgeZone.COLLAPSED)
            self._stats["avg_confidence"] = sum(n.confidence for n in all_nodes) / len(all_nodes)
        all_agents = list(self._agents.values())
        if all_agents:
            self._stats["avg_horizon_breadth"] = sum(a.horizon_breadth for a in all_agents) / len(all_agents)
        self._stats["total_discoveries"] = sum(a.total_discoveries for a in all_agents)
        self._stats["total_assimilations"] = sum(a.total_assimilations for a in all_agents)
        self._stats["total_doubts"] = sum(a.total_doubts for a in all_agents)

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "timestamp": time.time(),
            "type": event_type,
            **payload,
        })
