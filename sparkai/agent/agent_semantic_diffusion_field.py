"""
SparkLabs Agent - Semantic Diffusion Field

The AgentSemanticDiffusionField models how knowledge, meaning, and
understanding spread through agent populations as a diffusion process.
Agents are nodes in a semantic field where knowledge packets propagate
along social connections, similar to how particles diffuse through a
medium.

Unlike simple message passing, diffusion has gradients, decay, and
crystallization. Knowledge that reaches sufficient saturation in a
population crystallizes into "shared understanding" - a stable belief
that resists erosion. This creates emergent culture: ideas that spread
widely enough become part of the collective consciousness.

The field also models semantic resistance: agents can resist certain
knowledge based on their disposition, creating pockets of divergence
where different populations hold incompatible beliefs. This produces
realistic cultural fragmentation and ideological conflict.

Architecture:
  EMIT       ->  PROPAGATE   ->  ABSORB     ->  DECAY      ->  CRYSTALLIZE
  (introduce    (push         (agents         (let stale     (when
   knowledge    knowledge     absorb          knowledge      saturation
   packets      along         diffused        fade to        is high
   into the     social        knowledge       keep field     enough,
   field)       edges)        at varying      dynamic)       lock into
                              rates)                         shared belief)

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

class DiffusionPhase(Enum):
    """Phases of the semantic diffusion cycle."""
    EMIT = "emit"                # introduce knowledge packets
    PROPAGATE = "propagate"      # push along social edges
    ABSORB = "absorb"            # agents absorb knowledge
    DECAY = "decay"              # stale knowledge fades
    CRYSTALLIZE = "crystallize"  # high saturation locks into belief


class KnowledgeType(Enum):
    """Nature of the diffusing knowledge."""
    FACT = "fact"                # verifiable information
    SKILL = "skill"              # learnable capability
    RUMOR = "rumor"              # unverified information
    BELIEF = "belief"            # ideological conviction
    EMOTION = "emotion"          # emotional state
    TECHNIQUE = "technique"      # procedural knowledge


class AgentRole(Enum):
    """Role of an agent in the diffusion network."""
    SOURCE = "source"            # innovator, emits knowledge
    CONDUIT = "conduit"          # passes knowledge along
    SINK = "sink"                # absorbs but doesn't spread
    BARRIER = "barrier"          # resists diffusion
    AMPLIFIER = "amplifier"      # boosts knowledge strength


class CrystallizationState(Enum):
    """Whether knowledge has crystallized into shared belief."""
    FLUID = "fluid"              # still diffusing
    SATURATING = "saturating"    # approaching crystallization
    CRYSTALLIZED = "crystallized"  # locked into shared belief


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class DiffusionNode:
    """An agent node in the diffusion field."""
    agent_id: str
    role: AgentRole = AgentRole.CONDUIT
    permeability: float = 0.5       # how easily knowledge enters (0.0-1.0)
    retention: float = 0.5          # how well knowledge is kept (0.0-1.0)
    resistance: Dict[str, float] = field(default_factory=dict)  # per-type resistance
    absorbed: Dict[str, float] = field(default_factory=dict)    # knowledge_id -> saturation
    crystallized: Set[str] = field(default_factory=set)          # locked beliefs
    total_emitted: int = 0
    total_absorbed: int = 0


@dataclass
class DiffusionEdge:
    """A social connection between two agents."""
    source_id: str
    target_id: str
    bandwidth: float = 0.5          # how much knowledge flows (0.0-1.0)
    latency: float = 0.0            # delay before propagation (cycles)
    filter_types: Set[KnowledgeType] = field(default_factory=set)  # blocked types


@dataclass
class KnowledgePacket:
    """A unit of diffusing knowledge."""
    knowledge_id: str
    label: str
    knowledge_type: KnowledgeType
    origin_id: str                  # emitting agent
    strength: float = 1.0           # current signal strength
    initial_strength: float = 1.0
    emitted_at: float = field(default_factory=time.time)
    saturation_map: Dict[str, float] = field(default_factory=dict)  # agent_id -> level
    crystallization: CrystallizationState = CrystallizationState.FLUID
    total_hops: int = 0
    description: str = ""


@dataclass
class PropagationWave:
    """A wave of knowledge moving through the network."""
    wave_id: str
    knowledge_id: str
    from_agent: str
    to_agent: str
    strength: float
    hop: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class CrystallizedBelief:
    """A belief that has crystallized across the population."""
    belief_id: str
    knowledge_id: str
    label: str
    saturation_count: int           # how many agents hold it
    avg_saturation: float           # average strength
    crystallized_at: float = field(default_factory=time.time)


# =============================================================================
# Engine
# =============================================================================

class AgentSemanticDiffusionField:
    """
    Thread-safe singleton orchestrating semantic diffusion across agents.

    Usage:
        field = AgentSemanticDiffusionField.get_instance()
        field.register_agent("hero", AgentRole.SOURCE, permeability=0.8)
        field.register_agent("npc_1", AgentRole.CONDUIT)
        field.connect("hero", "npc_1", bandwidth=0.7)
        field.emit("k_1", "Secret Map Location", KnowledgeType.FACT, "hero")
        field.cycle()
    """

    _instance: Optional["AgentSemanticDiffusionField"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._nodes: Dict[str, DiffusionNode] = {}
        self._edges: Dict[str, Dict[str, DiffusionEdge]] = {}  # src -> {tgt -> edge}
        self._packets: Dict[str, KnowledgePacket] = {}
        self._waves: Deque[PropagationWave] = deque(maxlen=500)
        self._beliefs: Dict[str, CrystallizedBelief] = {}
        self._phase: DiffusionPhase = DiffusionPhase.EMIT
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_agents": 0,
            "total_connections": 0,
            "total_packets": 0,
            "total_waves": 0,
            "total_crystallized": 0,
            "avg_saturation": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentSemanticDiffusionField":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Agent Registration
    # -------------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        role: AgentRole = AgentRole.CONDUIT,
        permeability: float = 0.5,
        retention: float = 0.5,
    ) -> Dict[str, Any]:
        """Register a new agent node in the diffusion field."""
        with self._global_lock:
            if agent_id in self._nodes:
                return {"error": f"Agent already registered: {agent_id}"}
            node = DiffusionNode(
                agent_id=agent_id,
                role=role,
                permeability=max(0.0, min(1.0, permeability)),
                retention=max(0.0, min(1.0, retention)),
            )
            self._nodes[agent_id] = node
            self._edges[agent_id] = {}
            self._stats["total_agents"] = len(self._nodes)
            self._record_event("agent_registered", {"agent_id": agent_id, "role": role.value})
            return {
                "agent_id": agent_id,
                "role": role.value,
                "permeability": node.permeability,
                "retention": node.retention,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent from the field."""
        with self._global_lock:
            if agent_id not in self._nodes:
                return {"error": f"Agent not found: {agent_id}"}
            del self._nodes[agent_id]
            # Clean up edges
            del self._edges[agent_id]
            for src in self._edges:
                self._edges[src].pop(agent_id, None)
            self._stats["total_agents"] = len(self._nodes)
            self._stats["total_connections"] = sum(len(e) for e in self._edges.values())
            return {"removed": agent_id}

    def set_resistance(
        self, agent_id: str, knowledge_type: KnowledgeType, resistance: float
    ) -> Dict[str, Any]:
        """Set an agent's resistance to a specific knowledge type."""
        with self._global_lock:
            node = self._nodes.get(agent_id)
            if node is None:
                return {"error": f"Agent not found: {agent_id}"}
            node.resistance[knowledge_type.value] = max(0.0, min(1.0, resistance))
            return {
                "agent_id": agent_id,
                "knowledge_type": knowledge_type.value,
                "resistance": node.resistance[knowledge_type.value],
            }

    # -------------------------------------------------------------------------
    # Connection Management
    # -------------------------------------------------------------------------

    def connect(
        self,
        source_id: str,
        target_id: str,
        bandwidth: float = 0.5,
        latency: float = 0.0,
        filter_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a directed social connection between two agents."""
        with self._global_lock:
            if source_id not in self._nodes:
                return {"error": f"Source agent not found: {source_id}"}
            if target_id not in self._nodes:
                return {"error": f"Target agent not found: {target_id}"}
            blocked = set()
            if filter_types:
                for ft in filter_types:
                    try:
                        blocked.add(KnowledgeType(ft))
                    except ValueError:
                        pass
            edge = DiffusionEdge(
                source_id=source_id,
                target_id=target_id,
                bandwidth=max(0.0, min(1.0, bandwidth)),
                latency=max(0.0, latency),
                filter_types=blocked,
            )
            self._edges[source_id][target_id] = edge
            self._stats["total_connections"] = sum(len(e) for e in self._edges.values())
            self._record_event("connected", {
                "source": source_id, "target": target_id, "bandwidth": bandwidth,
            })
            return {
                "source_id": source_id,
                "target_id": target_id,
                "bandwidth": edge.bandwidth,
                "latency": edge.latency,
                "filtered_types": [t.value for t in edge.filter_types],
            }

    def disconnect(self, source_id: str, target_id: str) -> Dict[str, Any]:
        """Remove a connection between two agents."""
        with self._global_lock:
            if source_id not in self._edges or target_id not in self._edges[source_id]:
                return {"error": f"Connection not found: {source_id} -> {target_id}"}
            del self._edges[source_id][target_id]
            self._stats["total_connections"] = sum(len(e) for e in self._edges.values())
            return {"disconnected": f"{source_id} -> {target_id}"}

    # -------------------------------------------------------------------------
    # Knowledge Emission
    # -------------------------------------------------------------------------

    def emit(
        self,
        knowledge_id: str,
        label: str,
        knowledge_type: KnowledgeType,
        origin_id: str,
        strength: float = 1.0,
        description: str = "",
    ) -> Dict[str, Any]:
        """Emit a new knowledge packet from an agent into the field."""
        with self._global_lock:
            if origin_id not in self._nodes:
                return {"error": f"Origin agent not found: {origin_id}"}
            if knowledge_id in self._packets:
                return {"error": f"Knowledge already exists: {knowledge_id}"}
            packet = KnowledgePacket(
                knowledge_id=knowledge_id,
                label=label,
                knowledge_type=knowledge_type,
                origin_id=origin_id,
                strength=max(0.0, min(1.0, strength)),
                initial_strength=max(0.0, min(1.0, strength)),
                description=description,
            )
            # Origin agent immediately has full saturation
            packet.saturation_map[origin_id] = 1.0
            self._nodes[origin_id].absorbed[knowledge_id] = 1.0
            self._nodes[origin_id].total_emitted += 1
            self._packets[knowledge_id] = packet
            self._stats["total_packets"] = len(self._packets)
            self._record_event("emitted", {
                "knowledge_id": knowledge_id,
                "origin": origin_id,
                "type": knowledge_type.value,
            })
            return {
                "knowledge_id": knowledge_id,
                "label": label,
                "type": knowledge_type.value,
                "origin_id": origin_id,
                "strength": packet.strength,
            }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single diffusion cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            # EMIT: no-op (packets emitted via API)
            self._phase = DiffusionPhase.EMIT
            phase_outputs["emit"] = {"active_packets": len(self._packets)}
            # PROPAGATE: push knowledge along edges
            self._phase = DiffusionPhase.PROPAGATE
            phase_outputs["propagate"] = self._phase_propagate()
            # ABSORB: agents absorb diffused knowledge
            self._phase = DiffusionPhase.ABSORB
            phase_outputs["absorb"] = self._phase_absorb()
            # DECAY: let stale knowledge fade
            self._phase = DiffusionPhase.DECAY
            phase_outputs["decay"] = self._phase_decay()
            # CRYSTALLIZE: lock high-saturation knowledge into beliefs
            self._phase = DiffusionPhase.CRYSTALLIZE
            phase_outputs["crystallize"] = self._phase_crystallize()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles."""
        if cycles < 1 or cycles > 1000:
            return {"error": "cycles must be 1-1000"}
        for _ in range(cycles):
            self.cycle()
        return {
            "cycles_run": cycles,
            "final_phase": self._phase.value,
            "stats": dict(self._stats),
        }

    def _phase_propagate(self) -> Dict[str, Any]:
        """PROPAGATE: push knowledge along social edges."""
        waves_created = 0
        new_waves: List[PropagationWave] = []
        for packet in self._packets.values():
            if packet.crystallization == CrystallizationState.CRYSTALLIZED:
                continue
            if packet.strength < 0.05:
                continue
            for agent_id, saturation in list(packet.saturation_map.items()):
                if saturation < 0.1:
                    continue
                edges = self._edges.get(agent_id, {})
                for target_id, edge in edges.items():
                    # Check if target already has high saturation
                    current = packet.saturation_map.get(target_id, 0.0)
                    if current >= 0.95:
                        continue
                    # Check type filter
                    if packet.knowledge_type in edge.filter_types:
                        continue
                    # Calculate propagation strength
                    prop_strength = (
                        saturation
                        * edge.bandwidth
                        * packet.strength
                        * 0.25
                    )
                    if prop_strength < 0.01:
                        continue
                    wave = PropagationWave(
                        wave_id=f"wave_{packet.knowledge_id}_{agent_id}_{target_id}_{self._cycle_count}",
                        knowledge_id=packet.knowledge_id,
                        from_agent=agent_id,
                        to_agent=target_id,
                        strength=prop_strength,
                        hop=packet.total_hops + 1,
                    )
                    new_waves.append(wave)
                    waves_created += 1
        # Apply waves
        for wave in new_waves:
            self._waves.append(wave)
            packet = self._packets.get(wave.knowledge_id)
            if packet is None:
                continue
            current = packet.saturation_map.get(wave.to_agent, 0.0)
            packet.saturation_map[wave.to_agent] = min(1.0, current + wave.strength)
            packet.total_hops = max(packet.total_hops, wave.hop)
        self._stats["total_waves"] = len(self._waves)
        return {"waves_created": waves_created, "total_waves": len(self._waves)}

    def _phase_absorb(self) -> Dict[str, Any]:
        """ABSORB: agents absorb knowledge at varying rates based on role."""
        absorbed_count = 0
        for node in self._nodes.values():
            if node.role == AgentRole.BARRIER:
                continue
            for packet in self._packets.values():
                saturation = packet.saturation_map.get(node.agent_id, 0.0)
                if saturation < 0.01:
                    continue
                # Check type-specific resistance
                resistance = node.resistance.get(packet.knowledge_type.value, 0.0)
                effective_sat = saturation * (1.0 - resistance)
                if effective_sat < 0.01:
                    continue
                current = node.absorbed.get(packet.knowledge_id, 0.0)
                # Absorption rate depends on permeability and role
                rate = node.permeability * 0.3
                if node.role == AgentRole.SINK:
                    rate *= 1.5
                elif node.role == AgentRole.AMPLIFIER:
                    rate *= 1.2
                new_level = min(1.0, current + effective_sat * rate)
                if new_level > current + 0.001:
                    node.absorbed[packet.knowledge_id] = new_level
                    node.total_absorbed += 1
                    absorbed_count += 1
                # Amplifiers boost the packet strength
                if node.role == AgentRole.AMPLIFIER and new_level > 0.3:
                    packet.strength = min(1.0, packet.strength + 0.02)
        return {"absorbed_count": absorbed_count}

    def _phase_decay(self) -> Dict[str, Any]:
        """DECAY: let knowledge fade to keep the field dynamic."""
        decayed_packets = 0
        for packet in self._packets.values():
            if packet.crystallization == CrystallizationState.CRYSTALLIZED:
                continue
            packet.strength = max(0.0, packet.strength - 0.03)
            if packet.strength < 0.01:
                decayed_packets += 1
            # Decay saturation for non-origin agents
            for agent_id in list(packet.saturation_map.keys()):
                if agent_id == packet.origin_id:
                    continue
                node = self._nodes.get(agent_id)
                if node is None:
                    continue
                # Retention determines how fast knowledge decays
                decay_rate = (1.0 - node.retention) * 0.05
                current = packet.saturation_map[agent_id]
                packet.saturation_map[agent_id] = max(0.0, current - decay_rate)
                # Also decay absorbed level
                absorbed = node.absorbed.get(packet.knowledge_id, 0.0)
                node.absorbed[packet.knowledge_id] = max(0.0, absorbed - decay_rate * 0.5)
        return {"decayed_packets": decayed_packets}

    def _phase_crystallize(self) -> Dict[str, Any]:
        """CRYSTALLIZE: when saturation is high enough, lock into shared belief."""
        crystallized = 0
        for packet in self._packets.values():
            if packet.crystallization == CrystallizationState.CRYSTALLIZED:
                continue
            # Count agents with significant saturation
            saturated = sum(1 for s in packet.saturation_map.values() if s > 0.3)
            total_agents = len(self._nodes)
            if total_agents == 0:
                continue
            saturation_ratio = saturated / total_agents
            if saturation_ratio >= 0.6:
                packet.crystallization = CrystallizationState.CRYSTALLIZED
                belief = CrystallizedBelief(
                    belief_id=f"belief_{packet.knowledge_id}",
                    knowledge_id=packet.knowledge_id,
                    label=packet.label,
                    saturation_count=saturated,
                    avg_saturation=sum(packet.saturation_map.values()) / len(packet.saturation_map) if packet.saturation_map else 0.0,
                )
                self._beliefs[belief.belief_id] = belief
                # Mark crystallized agents
                for agent_id, sat in packet.saturation_map.items():
                    if sat > 0.3:
                        self._nodes[agent_id].crystallized.add(packet.knowledge_id)
                crystallized += 1
                self._stats["total_crystallized"] = len(self._beliefs)
                self._record_event("crystallized", {
                    "knowledge_id": packet.knowledge_id,
                    "saturated_agents": saturated,
                    "ratio": saturation_ratio,
                })
            elif saturation_ratio >= 0.4:
                packet.crystallization = CrystallizationState.SATURATING
        return {"crystallized": crystallized, "total_beliefs": len(self._beliefs)}

    # -------------------------------------------------------------------------
    # Queries
    # ----------------------------------------------------------------============

    def get_status(self) -> Dict[str, Any]:
        """Get global field status."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_agents": len(self._nodes),
                "total_connections": sum(len(e) for e in self._edges.values()),
                "total_packets": len(self._packets),
                "total_beliefs": len(self._beliefs),
                "stats": dict(self._stats),
            }

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get details of an agent in the field."""
        with self._global_lock:
            node = self._nodes.get(agent_id)
            if node is None:
                return None
            return {
                "agent_id": node.agent_id,
                "role": node.role.value,
                "permeability": node.permeability,
                "retention": node.retention,
                "resistance": dict(node.resistance),
                "absorbed": dict(node.absorbed),
                "crystallized": list(node.crystallized),
                "total_emitted": node.total_emitted,
                "total_absorbed": node.total_absorbed,
                "connections": len(self._edges.get(agent_id, {})),
            }

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents in the field."""
        with self._global_lock:
            return [
                {
                    "agent_id": n.agent_id,
                    "role": n.role.value,
                    "permeability": n.permeability,
                    "retention": n.retention,
                    "absorbed_count": len(n.absorbed),
                    "crystallized_count": len(n.crystallized),
                }
                for n in self._nodes.values()
            ]

    def get_packet(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a knowledge packet."""
        with self._global_lock:
            packet = self._packets.get(knowledge_id)
            if packet is None:
                return None
            return {
                "knowledge_id": packet.knowledge_id,
                "label": packet.label,
                "type": packet.knowledge_type.value,
                "origin_id": packet.origin_id,
                "strength": packet.strength,
                "initial_strength": packet.initial_strength,
                "crystallization": packet.crystallization.value,
                "total_hops": packet.total_hops,
                "saturation_map": dict(packet.saturation_map),
                "saturated_agents": sum(1 for s in packet.saturation_map.values() if s > 0.1),
            }

    def list_packets(self) -> List[Dict[str, Any]]:
        """List all knowledge packets."""
        with self._global_lock:
            return [
                {
                    "knowledge_id": p.knowledge_id,
                    "label": p.label,
                    "type": p.knowledge_type.value,
                    "origin": p.origin_id,
                    "strength": p.strength,
                    "crystallization": p.crystallization.value,
                    "saturated_agents": sum(1 for s in p.saturation_map.values() if s > 0.1),
                }
                for p in self._packets.values()
            ]

    def get_beliefs(self) -> List[Dict[str, Any]]:
        """Get all crystallized beliefs."""
        with self._global_lock:
            return [
                {
                    "belief_id": b.belief_id,
                    "knowledge_id": b.knowledge_id,
                    "label": b.label,
                    "saturation_count": b.saturation_count,
                    "avg_saturation": b.avg_saturation,
                    "crystallized_at": b.crystallized_at,
                }
                for b in self._beliefs.values()
            ]

    def get_waves(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent propagation waves."""
        with self._global_lock:
            return [
                {
                    "wave_id": w.wave_id,
                    "knowledge_id": w.knowledge_id,
                    "from": w.from_agent,
                    "to": w.to_agent,
                    "strength": w.strength,
                    "hop": w.hop,
                }
                for w in list(self._waves)[-limit:]
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent field events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire field."""
        with self._global_lock:
            n = len(self._nodes)
            self._nodes.clear()
            self._edges.clear()
            self._packets.clear()
            self._waves.clear()
            self._beliefs.clear()
            self._phase = DiffusionPhase.EMIT
            self._cycle_count = 0
            self._events_log.clear()
            self._stats = {
                "total_agents": 0,
                "total_connections": 0,
                "total_packets": 0,
                "total_waves": 0,
                "total_crystallized": 0,
                "avg_saturation": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            self._record_event("field_reset", {"cleared_agents": n})
            return {"reset": True, "cleared_agents": n}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _update_stats(self) -> None:
        """Recompute aggregate statistics."""
        if not self._packets:
            self._stats["avg_saturation"] = 0.0
            return
        total_sat = 0.0
        count = 0
        for packet in self._packets.values():
            for s in packet.saturation_map.values():
                total_sat += s
                count += 1
        self._stats["avg_saturation"] = total_sat / count if count > 0 else 0.0

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record a field event."""
        self._events_log.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
