"""
SparkLabs Agent - Axiological Lattice Weaver

The AgentAxiologicalLatticeWeaver models how agents weave their values
(axiology = the philosophical study of value) into a lattice structure
that guides their decisions and identity.

Values are not static labels in an agent's mind - they form a living
lattice where some values support others (a value of "loyalty" might
support "friendship"), some conflict (a value of "honesty" might conflict
with "kindness" when the truth hurts), and the lattice can restructure
when values clash or when new experiences demand new values.

The lattice is a directed graph where:
  - Nodes are values (e.g., courage, wisdom, freedom, duty)
  - Supporting edges (A -> B) mean "A supports/upholds B"
  - Conflicting edges (A --| B) mean "A contradicts B"
  - Root values are foundational, rarely questioned
  - Leaf values are situational, easily pruned

The weaver models how the lattice grows, tensions, prunes, grafts, and
blooms - producing a living value system that shapes agent behavior
organically rather than through rigid rules.

Architecture:
  WEAVE     ->  TENSION  ->  PRUNE    ->  GRAFT    ->  BLOOM
  (new        (conflicting (weak or    (new value   (coherent
   values     values       contradicted branches    value clusters
   woven      create       values are   grafted     crystallize
   into       tension      pruned from  onto        into guiding
   lattice,   that         the lattice, stronger     principles
   forming    stresses     freeing      roots)       that direct
   links)     structure    the agent                 behavior)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
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

class LatticePhase(Enum):
    """Phases of the axiological lattice weave cycle."""
    WEAVE = "weave"         # new values woven into the lattice
    TENSION = "tension"     # conflicting values create tension
    PRUNE = "prune"         # weak/contradicted values pruned
    GRAFT = "graft"         # new branches grafted onto roots
    BLOOM = "bloom"         # coherent clusters bloom into principles


class ValueCategory(Enum):
    """Categories of values an agent can hold."""
    MORAL = "moral"             # right/wrong (justice, honesty, mercy)
    ETHICAL = "ethical"         # conduct/code (loyalty, duty, honor)
    AESTHETIC = "aesthetic"     # beauty/taste (elegance, harmony, grit)
    EPISTEMIC = "epistemic"     # knowledge/truth (curiosity, wisdom, rigor)
    VITAL = "vital"             # life/survival (freedom, safety, growth)
    SOCIAL = "social"           # relations (friendship, community, trust)
    SPIRITUAL = "spiritual"     # meaning/faith (hope, fate, devotion)
    PRAGMATIC = "pragmatic"     # utility (efficiency, adaptability, craft)


class ValueTier(Enum):
    """How deeply rooted a value is in the agent's identity."""
    ROOT = "root"           # foundational, rarely questioned
    CORE = "core"           # central to identity
    BRANCH = "branch"       # derived from core values
    LEAF = "leaf"           # situational, easily pruned
    WILTING = "wilting"     # losing vitality, soon pruned
    BLOOMED = "bloomed"     # crystallized into a guiding principle


class EdgeType(Enum):
    """Types of edges between values in the lattice."""
    SUPPORTS = "supports"       # A upholds/reinforces B
    CONFLICTS = "conflicts"     # A contradicts B
    DERIVES = "derives"         # A is derived from B
    SUPERSEDES = "supersedes"   # A replaces/outgrows B


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AxiologicalValue:
    """A value node in the agent's axiological lattice."""
    value_id: str
    label: str
    category: ValueCategory
    tier: ValueTier = ValueTier.LEAF
    vitality: float = 0.5          # how alive/active the value is (0.0-1.0)
    conviction: float = 0.5        # how strongly held (0.0-1.0)
    elasticity: float = 0.3        # how flexible/adaptable (0.0-1.0)
    tension: float = 0.0           # accumulated tension from conflicts
    root_strength: float = 0.0     # how deeply rooted (computed)
    bloomed: bool = False          # whether it has bloomed into a principle
    created_at: float = field(default_factory=time.time)
    last_weaved: float = field(default_factory=time.time)
    support_count: int = 0         # how many values support this one
    conflict_count: int = 0        # how many values conflict with this one


@dataclass
class ValueEdge:
    """An edge connecting two values in the lattice."""
    edge_id: str
    source: str                    # source value_id
    target: str                    # target value_id
    edge_type: EdgeType
    strength: float = 0.5          # how strong the connection is
    created_at: float = field(default_factory=time.time)


@dataclass
class AxiologicalAgent:
    """An agent with an axiological lattice."""
    agent_id: str
    values: Dict[str, AxiologicalValue] = field(default_factory=dict)
    edges: Dict[str, ValueEdge] = field(default_factory=dict)
    principles: List[str] = field(default_factory=list)  # bloomed principles
    total_woven: int = 0
    total_pruned: int = 0
    total_grafted: int = 0
    total_bloomed: int = 0
    avg_vitality: float = 0.5
    avg_tension: float = 0.0
    coherence: float = 0.5         # how coherent the lattice is


@dataclass
class LatticeTension:
    """Record of a tension event between conflicting values."""
    tension_id: str
    agent_id: str
    value_a: str
    value_b: str
    tension_amount: float
    resolved: bool = False
    resolution: str = ""           # "pruned_a", "pruned_b", "integrated", "unresolved"
    timestamp: float = field(default_factory=time.time)


@dataclass
class BloomedPrinciple:
    """A value cluster that has bloomed into a guiding principle."""
    principle_id: str
    agent_id: str
    source_values: List[str]
    label: str
    strength: float
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# Lattice Weaver Engine
# =============================================================================

class AgentAxiologicalLatticeWeaver:
    """
    Thread-safe singleton orchestrating axiological lattice weaving.

    Usage:
        weaver = AgentAxiologicalLatticeWeaver.get_instance()
        weaver.register_agent("hero")
        weaver.weave_value("hero", "v_courage", "Courage", ValueCategory.MORAL,
                          ValueTier.CORE, vitality=0.8, conviction=0.7)
        weaver.weave_value("hero", "v_duty", "Duty", ValueCategory.ETHICAL,
                          ValueTier.ROOT, vitality=0.9, conviction=0.85)
        weaver.link_values("hero", "v_duty", "v_courage", EdgeType.SUPPORTS, 0.7)
        weaver.weave_value("hero", "v_honesty", "Honesty", ValueCategory.MORAL,
                          ValueTier.CORE, vitality=0.7, conviction=0.6)
        weaver.link_values("hero", "v_honesty", "v_courage", EdgeType.CONFLICTS, 0.4)
        weaver.cycle()
    """

    _instance: Optional["AgentAxiologicalLatticeWeaver"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._agents: Dict[str, AxiologicalAgent] = {}
        self._tensions: Deque[LatticeTension] = deque(maxlen=200)
        self._principles: Deque[BloomedPrinciple] = deque(maxlen=100)
        self._phase: LatticePhase = LatticePhase.WEAVE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=300)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {
            "total_agents": 0,
            "total_values": 0,
            "total_edges": 0,
            "total_principles": 0,
            "total_tensions": 0,
            "resolved_tensions": 0,
            "root_values": 0,
            "bloomed_values": 0,
            "avg_vitality": 0.0,
            "avg_tension": 0.0,
            "avg_coherence": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentAxiologicalLatticeWeaver":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Agent Management
    # -------------------------------------------------------------------------

    def register_agent(self, agent_id: str) -> Dict[str, Any]:
        """Register a new agent with an empty lattice."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already exists: {agent_id}"}
            self._agents[agent_id] = AxiologicalAgent(agent_id=agent_id)
            self._stats["total_agents"] = len(self._agents)
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {"agent_id": agent_id, "values": 0, "edges": 0}

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent and their lattice."""
        with self._global_lock:
            if agent_id not in self._agents:
                return {"error": f"Agent not found: {agent_id}"}
            a = self._agents.pop(agent_id)
            self._stats["total_agents"] = len(self._agents)
            self._update_stats()
            return {"removed": agent_id, "values_removed": len(a.values)}

    # -------------------------------------------------------------------------
    # Value Management
    # -------------------------------------------------------------------------

    def weave_value(
        self,
        agent_id: str,
        value_id: str,
        label: str,
        category: ValueCategory,
        tier: ValueTier = ValueTier.LEAF,
        vitality: float = 0.5,
        conviction: float = 0.5,
        elasticity: float = 0.3,
    ) -> Dict[str, Any]:
        """Weave a new value into an agent's lattice."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            if value_id in a.values:
                return {"error": f"Value already exists: {value_id}"}
            v = AxiologicalValue(
                value_id=value_id,
                label=label,
                category=category,
                tier=tier,
                vitality=max(0.0, min(1.0, vitality)),
                conviction=max(0.0, min(1.0, conviction)),
                elasticity=max(0.0, min(1.0, elasticity)),
                root_strength=self._compute_root_strength(tier, vitality, conviction),
            )
            a.values[value_id] = v
            a.total_woven += 1
            self._record_event("value_woven", {
                "agent_id": agent_id, "value_id": value_id,
                "category": category.value, "tier": tier.value,
            })
            self._update_stats()
            return {
                "value_id": value_id, "label": label,
                "category": category.value, "tier": tier.value,
                "vitality": v.vitality, "conviction": v.conviction,
            }

    def remove_value(self, agent_id: str, value_id: str) -> Dict[str, Any]:
        """Remove a value from an agent's lattice."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            if value_id not in a.values:
                return {"error": f"Value not found: {value_id}"}
            v = a.values.pop(value_id)
            # remove edges connected to this value
            to_remove = [
                eid for eid, e in a.edges.items()
                if e.source == value_id or e.target == value_id
            ]
            for eid in to_remove:
                a.edges.pop(eid, None)
            self._update_stats()
            return {"removed": value_id, "label": v.label}

    def link_values(
        self,
        agent_id: str,
        source: str,
        target: str,
        edge_type: EdgeType,
        strength: float = 0.5,
    ) -> Dict[str, Any]:
        """Link two values in the lattice with an edge."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            if source not in a.values:
                return {"error": f"Source value not found: {source}"}
            if target not in a.values:
                return {"error": f"Target value not found: {target}"}
            edge_id = f"e_{source}_{target}_{edge_type.value}"
            if edge_id in a.edges:
                return {"error": f"Edge already exists: {edge_id}"}
            edge = ValueEdge(
                edge_id=edge_id, source=source, target=target,
                edge_type=edge_type, strength=max(0.0, min(1.0, strength)),
            )
            a.edges[edge_id] = edge
            # update value connection counts
            if edge_type == EdgeType.SUPPORTS:
                a.values[target].support_count += 1
            elif edge_type == EdgeType.CONFLICTS:
                a.values[target].conflict_count += 1
                a.values[source].conflict_count += 1
            self._record_event("values_linked", {
                "agent_id": agent_id, "source": source,
                "target": target, "edge_type": edge_type.value,
            })
            self._update_stats()
            return {
                "edge_id": edge_id, "source": source, "target": target,
                "edge_type": edge_type.value, "strength": edge.strength,
            }

    # -------------------------------------------------------------------------
    # Phase: WEAVE - spontaneous value emergence
    # -------------------------------------------------------------------------

    def _phase_weave(self) -> Dict[str, Any]:
        """Spontaneous new values emerge from existing value clusters."""
        woven = 0
        for a in self._agents.values():
            # values with high vitality and conviction can spawn derived values
            for v in list(a.values.values()):
                if v.tier == ValueTier.WILTING:
                    continue
                if v.vitality < 0.5 or v.conviction < 0.5:
                    continue
                # chance to spawn a derived value
                spawn_chance = v.vitality * v.conviction * 0.15
                if random.random() > spawn_chance:
                    continue
                # create a derived value
                new_id = f"v_derived_{v.value_id}_{len(a.values)}"
                new_label = f"Derived from {v.label}"
                new_v = AxiologicalValue(
                    value_id=new_id,
                    label=new_label,
                    category=v.category,
                    tier=ValueTier.LEAF,
                    vitality=v.vitality * 0.6,
                    conviction=v.conviction * 0.5,
                    elasticity=0.5,
                    root_strength=0.1,
                )
                a.values[new_id] = new_v
                # create a derives edge
                edge_id = f"e_{v.value_id}_{new_id}_derives"
                a.edges[edge_id] = ValueEdge(
                    edge_id=edge_id, source=new_id, target=v.value_id,
                    edge_type=EdgeType.DERIVES, strength=0.6,
                )
                v.support_count += 1
                a.total_woven += 1
                woven += 1
                self._record_event("value_emerged", {
                    "agent_id": a.agent_id, "value_id": new_id,
                    "parent": v.value_id,
                })
            # update vitality - values slowly grow when supported
            for v in a.values.values():
                if v.tier == ValueTier.WILTING:
                    continue
                if v.support_count > 0:
                    v.vitality = min(1.0, v.vitality + 0.01 * v.support_count)
        self._update_stats()
        return {"values_emerged": woven}

    # -------------------------------------------------------------------------
    # Phase: TENSION - conflicts create tension
    # -------------------------------------------------------------------------

    def _phase_tension(self) -> Dict[str, Any]:
        """Conflicting values create tension in the lattice."""
        tensions_created = 0
        for a in self._agents.values():
            conflict_edges = [
                e for e in a.edges.values() if e.edge_type == EdgeType.CONFLICTS
            ]
            for edge in conflict_edges:
                va = a.values.get(edge.source)
                vb = a.values.get(edge.target)
                if va is None or vb is None:
                    continue
                if va.tier == ValueTier.WILTING or vb.tier == ValueTier.WILTING:
                    continue
                # tension is proportional to edge strength and both values' conviction
                tension = edge.strength * va.conviction * vb.conviction * 0.3
                va.tension = min(1.0, va.tension + tension)
                vb.tension = min(1.0, vb.tension + tension)
                # record tension event
                if tension > 0.05:
                    tension_id = f"t_{a.agent_id}_{edge.source}_{edge.target}_{self._cycle_count}"
                    self._tensions.append(LatticeTension(
                        tension_id=tension_id,
                        agent_id=a.agent_id,
                        value_a=edge.source,
                        value_b=edge.target,
                        tension_amount=tension,
                    ))
                    tensions_created += 1
                    self._record_event("tension_created", {
                        "agent_id": a.agent_id,
                        "value_a": edge.source, "value_b": edge.target,
                        "tension": tension,
                    })
        self._stats["total_tensions"] = len(self._tensions)
        return {"tensions_created": tensions_created}

    # -------------------------------------------------------------------------
    # Phase: PRUNE - weak/contradicted values are pruned
    # -------------------------------------------------------------------------

    def _phase_prune(self) -> Dict[str, Any]:
        """Weak or over-tensed values are pruned from the lattice."""
        pruned = 0
        for a in self._agents.values():
            to_prune: List[str] = []
            for vid, v in a.values.items():
                # prune values with very low vitality or very high tension
                if v.tier == ValueTier.ROOT:
                    continue  # never prune roots
                if v.vitality < 0.1 or v.tension > 0.8:
                    to_prune.append(vid)
                # wilt values with high tension
                elif v.tension > 0.5 and v.tier != ValueTier.WILTING:
                    v.tier = ValueTier.WILTING
                    v.vitality *= 0.7
                    self._record_event("value_wilted", {
                        "agent_id": a.agent_id, "value_id": vid,
                    })
            for vid in to_prune:
                v = a.values.pop(vid)
                # remove connected edges
                to_remove = [
                    eid for eid, e in a.edges.items()
                    if e.source == vid or e.target == vid
                ]
                for eid in to_remove:
                    a.edges.pop(eid, None)
                a.total_pruned += 1
                pruned += 1
                # mark tension as resolved
                for t in self._tensions:
                    if t.agent_id == a.agent_id and not t.resolved:
                        if t.value_a == vid or t.value_b == vid:
                            t.resolved = True
                            t.resolution = f"pruned_{vid}"
                self._record_event("value_pruned", {
                    "agent_id": a.agent_id, "value_id": vid,
                    "label": v.label,
                })
            # resolve tensions by integration (both values survive but tension drops)
            for t in list(self._tensions):
                if t.resolved:
                    continue
                if t.agent_id != a.agent_id:
                    continue
                va = a.values.get(t.value_a)
                vb = a.values.get(t.value_b)
                if va is None or vb is None:
                    continue
                # if both values have enough elasticity, tension resolves
                if va.elasticity + vb.elasticity > 0.8 and t.tension_amount < 0.15:
                    va.tension *= 0.5
                    vb.tension *= 0.5
                    t.resolved = True
                    t.resolution = "integrated"
                    self._stats["resolved_tensions"] += 1
        self._update_stats()
        return {"values_pruned": pruned}

    # -------------------------------------------------------------------------
    # Phase: GRAFT - new branches grafted onto stronger roots
    # -------------------------------------------------------------------------

    def _phase_graft(self) -> Dict[str, Any]:
        """Wilting values can be grafted onto stronger roots for support."""
        grafted = 0
        for a in self._agents.values():
            root_values = [
                v for v in a.values.values()
                if v.tier in (ValueTier.ROOT, ValueTier.CORE) and v.vitality > 0.5
            ]
            if not root_values:
                continue
            wilting = [
                v for v in a.values.values()
                if v.tier == ValueTier.WILTING and v.vitality > 0.15
            ]
            for w in wilting:
                # find a compatible root (same category or supporting category)
                compatible = [
                    r for r in root_values
                    if r.category == w.category or r.value_id != w.value_id
                ]
                if not compatible:
                    continue
                root = random.choice(compatible)
                # graft: create a support edge from root to wilting value
                edge_id = f"e_{root.value_id}_{w.value_id}_graft"
                if edge_id not in a.edges:
                    a.edges[edge_id] = ValueEdge(
                        edge_id=edge_id, source=root.value_id, target=w.value_id,
                        edge_type=EdgeType.SUPPORTS, strength=0.4,
                    )
                    w.support_count += 1
                # restore vitality
                w.vitality = min(0.6, w.vitality + 0.2)
                w.tension *= 0.5
                w.tier = ValueTier.BRANCH
                a.total_grafted += 1
                grafted += 1
                self._record_event("value_grafted", {
                    "agent_id": a.agent_id, "wilting": w.value_id,
                    "root": root.value_id,
                })
        self._update_stats()
        return {"values_grafted": grafted}

    # -------------------------------------------------------------------------
    # Phase: BLOOM - coherent clusters bloom into principles
    # -------------------------------------------------------------------------

    def _phase_bloom(self) -> Dict[str, Any]:
        """Coherent value clusters bloom into guiding principles."""
        bloomed = 0
        for a in self._agents.values():
            # find values with high vitality, high support, low tension
            for v in list(a.values.values()):
                if v.bloomed:
                    continue
                if v.tier == ValueTier.WILTING:
                    continue
                if v.vitality > 0.75 and v.support_count >= 2 and v.tension < 0.2:
                    v.bloomed = True
                    v.tier = ValueTier.BLOOMED
                    # find supporting values
                    supporters = [
                        e.source for e in a.edges.values()
                        if e.target == v.value_id and e.edge_type == EdgeType.SUPPORTS
                    ]
                    principle_id = f"p_{a.agent_id}_{v.value_id}_{self._cycle_count}"
                    principle = BloomedPrinciple(
                        principle_id=principle_id,
                        agent_id=a.agent_id,
                        source_values=supporters + [v.value_id],
                        label=f"Principle of {v.label}",
                        strength=v.vitality,
                    )
                    self._principles.append(principle)
                    a.principles.append(principle_id)
                    a.total_bloomed += 1
                    bloomed += 1
                    self._record_event("value_bloomed", {
                        "agent_id": a.agent_id, "value_id": v.value_id,
                        "principle_id": principle_id,
                    })
        self._update_stats()
        return {"values_bloomed": bloomed}

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single axiological lattice weave cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = LatticePhase.WEAVE
            phase_outputs["weave"] = self._phase_weave()
            self._phase = LatticePhase.TENSION
            phase_outputs["tension"] = self._phase_tension()
            self._phase = LatticePhase.PRUNE
            phase_outputs["prune"] = self._phase_prune()
            self._phase = LatticePhase.GRAFT
            phase_outputs["graft"] = self._phase_graft()
            self._phase = LatticePhase.BLOOM
            phase_outputs["bloom"] = self._phase_bloom()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            # update per-agent metrics
            for aid in self._agents:
                self._update_agent_metrics(aid)
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
        """Get an agent's full lattice state."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent_id,
                "value_count": len(a.values),
                "edge_count": len(a.edges),
                "principles": a.principles,
                "total_woven": a.total_woven,
                "total_pruned": a.total_pruned,
                "total_grafted": a.total_grafted,
                "total_bloomed": a.total_bloomed,
                "avg_vitality": a.avg_vitality,
                "avg_tension": a.avg_tension,
                "coherence": a.coherence,
                "values": [
                    {
                        "value_id": v.value_id,
                        "label": v.label,
                        "category": v.category.value,
                        "tier": v.tier.value,
                        "vitality": v.vitality,
                        "conviction": v.conviction,
                        "tension": v.tension,
                        "support_count": v.support_count,
                        "conflict_count": v.conflict_count,
                        "bloomed": v.bloomed,
                    }
                    for v in a.values.values()
                ],
                "edges": [
                    {
                        "edge_id": e.edge_id,
                        "source": e.source,
                        "target": e.target,
                        "edge_type": e.edge_type.value,
                        "strength": e.strength,
                    }
                    for e in a.edges.values()
                ],
            }

    def get_tensions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent tension events."""
        with self._global_lock:
            recent = list(self._tensions)[-limit:]
            return [
                {
                    "tension_id": t.tension_id,
                    "agent_id": t.agent_id,
                    "value_a": t.value_a,
                    "value_b": t.value_b,
                    "tension_amount": t.tension_amount,
                    "resolved": t.resolved,
                    "resolution": t.resolution,
                }
                for t in recent
            ]

    def get_principles(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get bloomed principles."""
        with self._global_lock:
            recent = list(self._principles)[-limit:]
            return [
                {
                    "principle_id": p.principle_id,
                    "agent_id": p.agent_id,
                    "source_values": p.source_values,
                    "label": p.label,
                    "strength": p.strength,
                }
                for p in recent
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get weaver status."""
        with self._global_lock:
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "stats": dict(self._stats),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the entire weaver."""
        with self._global_lock:
            count = len(self._agents)
            self._agents.clear()
            self._tensions.clear()
            self._principles.clear()
            self._events_log.clear()
            self._cycle_count = 0
            self._phase = LatticePhase.WEAVE
            self._stats = {
                "total_agents": 0,
                "total_values": 0,
                "total_edges": 0,
                "total_principles": 0,
                "total_tensions": 0,
                "resolved_tensions": 0,
                "root_values": 0,
                "bloomed_values": 0,
                "avg_vitality": 0.0,
                "avg_tension": 0.0,
                "avg_coherence": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "agents_removed": count}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _compute_root_strength(
        self, tier: ValueTier, vitality: float, conviction: float,
    ) -> float:
        """Compute how deeply rooted a value is."""
        tier_weight = {
            ValueTier.ROOT: 1.0,
            ValueTier.CORE: 0.7,
            ValueTier.BRANCH: 0.4,
            ValueTier.LEAF: 0.15,
            ValueTier.WILTING: 0.05,
            ValueTier.BLOOMED: 0.9,
        }
        return tier_weight.get(tier, 0.2) * (vitality * 0.5 + conviction * 0.5)

    def _update_agent_metrics(self, agent_id: str) -> None:
        """Update per-agent metrics."""
        a = self._agents.get(agent_id)
        if a is None:
            return
        if not a.values:
            a.avg_vitality = 0.0
            a.avg_tension = 0.0
            a.coherence = 0.0
            return
        a.avg_vitality = sum(v.vitality for v in a.values.values()) / len(a.values)
        a.avg_tension = sum(v.tension for v in a.values.values()) / len(a.values)
        # coherence: ratio of supports to total edges, adjusted by low tension
        support_edges = sum(
            1 for e in a.edges.values() if e.edge_type == EdgeType.SUPPORTS
        )
        conflict_edges = sum(
            1 for e in a.edges.values() if e.edge_type == EdgeType.CONFLICTS
        )
        total_edges = len(a.edges)
        if total_edges == 0:
            a.coherence = 0.5
        else:
            support_ratio = support_edges / total_edges
            tension_factor = 1.0 - a.avg_tension
            a.coherence = support_ratio * tension_factor

    def _update_stats(self) -> None:
        """Update global stats."""
        total_values = 0
        total_edges = 0
        root_count = 0
        bloomed_count = 0
        total_vitality = 0.0
        total_tension = 0.0
        total_coherence = 0.0
        for a in self._agents.values():
            total_values += len(a.values)
            total_edges += len(a.edges)
            for v in a.values.values():
                if v.tier == ValueTier.ROOT:
                    root_count += 1
                if v.bloomed:
                    bloomed_count += 1
                total_vitality += v.vitality
                total_tension += v.tension
            total_coherence += a.coherence
        self._stats["total_values"] = total_values
        self._stats["total_edges"] = total_edges
        self._stats["root_values"] = root_count
        self._stats["bloomed_values"] = bloomed_count
        self._stats["total_principles"] = len(self._principles)
        if total_values > 0:
            self._stats["avg_vitality"] = total_vitality / total_values
            self._stats["avg_tension"] = total_tension / total_values
        if self._agents:
            self._stats["avg_coherence"] = total_coherence / len(self._agents)

    def _record_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Record an event in the log."""
        self._events_log.append({
            "event_type": event_type,
            "data": data,
            "cycle": self._cycle_count,
            "timestamp": time.time(),
        })
