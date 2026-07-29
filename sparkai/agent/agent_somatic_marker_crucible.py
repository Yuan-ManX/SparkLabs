"""
SparkLabs Agent - Somatic Marker Crucible

The AgentSomaticMarkerCrucible models how agents forge somatic markers -
the bodily-emotional associations that guide decision-making beneath
conscious reasoning. Drawing from somatic marker hypothesis, the crucible
treats gut feelings, hunches, and intuitions not as mysterious noise
but as forged associations between situations and somatic (bodily)
states that have been tempered through experience.

Rational deliberation is the visible tip of decision-making; somatic
markers are the invisible base. When a seasoned warrior feels unease
before a battle that looks favorable on paper, that unease is a somatic
marker - a forged association between this situation-pattern and the
bodily state of alarm, tempered by past experiences where similar
patterns preceded ambush. The marker is not a thought; it is a bodily
signal that shapes which options feel right.

The crucible models five forces:
  - Sensing: agents sense situations and their concurrent bodily state
  - Imprinting: strong situation-state pairings imprint as markers
  - Tempering: repeated experiences temper markers, sharpening or
    dulling them based on consistency
  - Alloying: related markers alloy into compound dispositions that
    apply across broader situation classes
  - Casting: alloyed markers are cast into decision heuristics that
    bias option selection before deliberation begins

This produces agents whose decisions are shaped by an embodied wisdom
that grows from experience - where the body learns before the mind
understands, and where gut feelings carry the compressed weight of
lived history.

Architecture:
  SENSE    ->  IMPRINT  ->  TEMPER   ->  ALLOY    ->  CAST
  (agent    (strong      (repeated    (related     (alloyed
   senses    situation-   experiences markers       markers cast
   situation state       temper       alloy into    into decision
   and its  pairings     markers,     compound      heuristics
   bodily   imprint as   sharpening   dispositions  that bias
   state)   markers)     or dulling)  across        option
                                                situation     selection
                                                classes)      before
                                                              deliberation)

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

class CruciblePhase(Enum):
    """Phases of the somatic marker crucible cycle."""
    SENSE = "sense"           # agent senses situations and bodily state
    IMPRINT = "imprint"       # strong pairings imprint as markers
    TEMPER = "temper"         # repetition tempers markers
    ALLOY = "alloy"           # related markers alloy into dispositions
    CAST = "cast"             # markers cast into decision heuristics


class SomaticDomain(Enum):
    """Domains of bodily/emotional sensation."""
    VISCERAL = "visceral"       # gut, stomach, chest tightness
    KINESTHETIC = "kinesthetic"  # muscle tension, posture, readiness
    THERMAL = "thermal"         # warmth, coldness, flushing
    CARDIAC = "cardiac"         # heartbeat, pulse rate
    RESPIRATORY = "respiratory"  # breathing depth, rate
    FACIAL = "facial"           # micro-expressions, jaw tension
    AUTONOMIC = "autonomic"     # sweat, pupillary response
    PROPRIOCEPTIVE = "proprioceptive"  # balance, spatial orientation


class SituationArchetype(Enum):
    """Archetypes of situations that trigger somatic responses."""
    COMBAT = "combat"           # physical conflict
    SOCIAL = "social"           # interpersonal interaction
    EXPLORATION = "exploration"  # unknown territory
    DECISION = "decision"       # fork in the road
    LOSS = "loss"               # bereavement, failure
    GAIN = "gain"               # acquisition, success
    BETRAYAL = "betrayal"       # trust violated
    REVELATION = "revelation"   # truth disclosed
    DANGER = "danger"           # threat to safety
    INTIMACY = "intimacy"       # closeness, vulnerability
    RITUAL = "ritual"           # ceremony, tradition
    TRANSITION = "transition"   # crossing a threshold


class MarkerState(Enum):
    """State of a somatic marker in its lifecycle."""
    FRESH = "fresh"             # newly imprinted, volatile
    TEMPERING = "tempering"     # being refined by repetition
    STABLE = "stable"           # well-tempered, reliable
    ALLOYED = "alloyed"         # merged into a compound disposition
    DULL = "dull"               # weakened through inconsistency
    CAST = "cast"               # cast into a decision heuristic


class ValencePolarity(Enum):
    """The polarity of a somatic marker's emotional charge."""
    APPROACH = "approach"       # positive, drawing toward
    AVOID = "avoid"             # negative, pushing away
    AMBIVALENT = "ambivalent"   # mixed, oscillating
    NEUTRAL = "neutral"         # no strong charge


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SomaticMarker:
    """A forged association between a situation and a bodily state."""
    marker_id: str
    agent_id: str
    archetype: SituationArchetype
    domain: SomaticDomain
    label: str
    valence: ValencePolarity
    intensity: float = 0.5          # strength of the bodily signal (0.0-1.0)
    confidence: float = 0.3         # how reliable the marker is (0.0-1.0)
    state: MarkerState = MarkerState.FRESH
    tempering_count: int = 0        # how many times tempered
    consistency: float = 0.5        # how consistent the pairing has been
    last_triggered: float = 0.0
    forged_at: float = field(default_factory=time.time)
    trigger_threshold: float = 0.4  # intensity needed to activate
    situation_tags: List[str] = field(default_factory=list)
    bodily_signature: str = ""      # description of the bodily sensation
    decision_bias: float = 0.0      # how strongly it biases decisions


@dataclass
class CompoundDisposition:
    """A disposition formed by alloying related markers."""
    disposition_id: str
    agent_id: str
    label: str
    contributing_markers: List[str] = field(default_factory=list)
    valence: ValencePolarity = ValencePolarity.NEUTRAL
    strength: float = 0.5
    breadth: float = 0.3           # how broadly it applies
    forged_at: float = field(default_factory=time.time)
    cast_into_heuristic: bool = False


@dataclass
class DecisionHeuristic:
    """A decision heuristic cast from alloyed markers."""
    heuristic_id: str
    agent_id: str
    source_disposition: str
    label: str
    bias_strength: float            # how strongly it biases (0.0-1.0)
    applies_to: List[SituationArchetype] = field(default_factory=list)
    description: str = ""
    cast_at: float = field(default_factory=time.time)
    activation_count: int = 0


@dataclass
class SomaticAgent:
    """Per-agent crucible state."""
    agent_id: str
    markers: Dict[str, SomaticMarker] = field(default_factory=dict)
    dispositions: Dict[str, CompoundDisposition] = field(default_factory=dict)
    heuristics: Dict[str, DecisionHeuristic] = field(default_factory=dict)
    sensitivity: float = 0.5         # how easily markers imprint (0.0-1.0)
    tempering_rate: float = 0.5      # how quickly markers temper (0.0-1.0)
    alloy_threshold: int = 3         # markers needed to form a disposition
    total_markers_forged: int = 0
    total_dispositions: int = 0
    total_heuristics: int = 0


# =============================================================================
# Crucible
# =============================================================================

class AgentSomaticMarkerCrucible:
    """
    Thread-safe singleton orchestrating somatic marker forging.

    Usage:
        crucible = AgentSomaticMarkerCrucible.get_instance()
        crucible.register_agent("warrior", sensitivity=0.7, tempering_rate=0.6)
        crucible.sense_situation("warrior", "m_ambush_gut", SituationArchetype.COMBAT,
                                SomaticDomain.VISCERAL, "Gut dread before ambush",
                                ValencePolarity.AVOID, intensity=0.85, consistency=0.8)
        crucible.cycle()
    """

    _instance: Optional["AgentSomaticMarkerCrucible"] = None
    _lock = threading.RLock()

    # How much each tempering event sharpens confidence
    _TEMPERING_CONFIDENCE_BOOST = 0.08
    # How much inconsistency dulls a marker
    _INCONSISTENCY_DECAY = 0.12
    # Intensity threshold for imprinting a new marker
    _IMPRINT_THRESHOLD = 0.4
    # Minimum markers to alloy into a disposition
    _DEFAULT_ALLOY_THRESHOLD = 3
    # Bias strength per disposition when casting
    _CAST_BIAS_BASE = 0.3

    def __init__(self) -> None:
        self._agents: Dict[str, SomaticAgent] = {}
        self._phase: CruciblePhase = CruciblePhase.SENSE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=300)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {
            "total_agents": 0,
            "total_markers": 0,
            "total_dispositions": 0,
            "total_heuristics": 0,
            "fresh_markers": 0,
            "tempering_markers": 0,
            "stable_markers": 0,
            "alloyed_markers": 0,
            "dull_markers": 0,
            "cast_markers": 0,
            "avg_marker_confidence": 0.0,
            "avg_marker_intensity": 0.0,
            "total_tempering_events": 0,
            "total_alloy_events": 0,
            "total_cast_events": 0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentSomaticMarkerCrucible":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Agent Management
    # -------------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        sensitivity: float = 0.5,
        tempering_rate: float = 0.5,
        alloy_threshold: int = 3,
    ) -> Dict[str, Any]:
        """Register a new agent with the crucible."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            self._agents[agent_id] = SomaticAgent(
                agent_id=agent_id,
                sensitivity=max(0.0, min(1.0, sensitivity)),
                tempering_rate=max(0.0, min(1.0, tempering_rate)),
                alloy_threshold=max(2, alloy_threshold),
            )
            self._stats["total_agents"] = len(self._agents)
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "sensitivity": self._agents[agent_id].sensitivity,
                "tempering_rate": self._agents[agent_id].tempering_rate,
                "alloy_threshold": self._agents[agent_id].alloy_threshold,
                "markers": 0,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent from the crucible."""
        with self._global_lock:
            if agent_id not in self._agents:
                return {"error": f"Agent not found: {agent_id}"}
            a = self._agents.pop(agent_id)
            self._stats["total_agents"] = len(self._agents)
            return {
                "removed": agent_id,
                "markers": len(a.markers),
                "dispositions": len(a.dispositions),
                "heuristics": len(a.heuristics),
            }

    # -------------------------------------------------------------------------
    # Marker Management
    # -------------------------------------------------------------------------

    def sense_situation(
        self,
        agent_id: str,
        marker_id: str,
        archetype: SituationArchetype,
        domain: SomaticDomain,
        label: str,
        valence: ValencePolarity,
        intensity: float = 0.5,
        consistency: float = 0.5,
        situation_tags: Optional[List[str]] = None,
        bodily_signature: str = "",
    ) -> Dict[str, Any]:
        """Agent senses a situation and imprints a somatic marker."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            if marker_id in a.markers:
                # temper existing marker instead of imprinting new
                return self._temper_existing(a, marker_id, intensity, consistency)
            # check if intensity is high enough to imprint
            effective_intensity = intensity * (0.5 + a.sensitivity * 0.5)
            if effective_intensity < self._IMPRINT_THRESHOLD:
                return {
                    "marker_id": marker_id,
                    "imprinted": False,
                    "reason": "intensity below threshold",
                    "effective_intensity": effective_intensity,
                }
            marker = SomaticMarker(
                marker_id=marker_id,
                agent_id=agent_id,
                archetype=archetype,
                domain=domain,
                label=label,
                valence=valence,
                intensity=max(0.0, min(1.0, effective_intensity)),
                confidence=max(0.0, min(1.0, 0.3 + effective_intensity * 0.3)),
                state=MarkerState.FRESH,
                consistency=max(0.0, min(1.0, consistency)),
                situation_tags=situation_tags or [],
                bodily_signature=bodily_signature,
                trigger_threshold=max(0.2, 0.6 - effective_intensity * 0.3),
            )
            a.markers[marker_id] = marker
            a.total_markers_forged += 1
            self._record_event("marker_imprinted", {
                "agent_id": agent_id, "marker_id": marker_id,
                "archetype": archetype.value, "domain": domain.value,
                "valence": valence.value, "intensity": marker.intensity,
            })
            return {
                "marker_id": marker_id,
                "label": label,
                "archetype": archetype.value,
                "domain": domain.value,
                "valence": valence.value,
                "intensity": marker.intensity,
                "confidence": marker.confidence,
                "state": marker.state.value,
                "imprinted": True,
            }

    def trigger_marker(
        self, agent_id: str, marker_id: str, situation_intensity: float = 0.5,
    ) -> Dict[str, Any]:
        """Trigger an existing marker by encountering its situation again."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            marker = a.markers.get(marker_id)
            if marker is None:
                return {"error": f"Marker not found: {marker_id}"}
            if marker.state in (MarkerState.DULL,):
                return {"error": f"Marker is dull and inactive: {marker_id}"}
            # trigger if situation intensity exceeds threshold
            if situation_intensity < marker.trigger_threshold:
                return {
                    "marker_id": marker_id,
                    "triggered": False,
                    "reason": "situation_intensity below trigger_threshold",
                    "threshold": marker.trigger_threshold,
                }
            marker.last_triggered = time.time()
            marker.tempering_count += 1
            # tempering: increase confidence if consistent
            temper_boost = self._TEMPERING_CONFIDENCE_BOOST * a.tempering_rate
            if situation_intensity > marker.intensity * 0.7:
                marker.confidence = min(1.0, marker.confidence + temper_boost)
                marker.consistency = min(1.0, marker.consistency + 0.05)
            else:
                marker.consistency = max(0.0, marker.consistency - self._INCONSISTENCY_DECAY * 0.5)
            # state transitions
            if marker.state == MarkerState.FRESH and marker.tempering_count >= 2:
                marker.state = MarkerState.TEMPERING
            elif marker.state == MarkerState.TEMPERING and marker.confidence > 0.65:
                marker.state = MarkerState.STABLE
            self._record_event("marker_triggered", {
                "agent_id": agent_id, "marker_id": marker_id,
                "tempering_count": marker.tempering_count,
                "confidence": marker.confidence,
            })
            return {
                "marker_id": marker_id,
                "triggered": True,
                "state": marker.state.value,
                "tempering_count": marker.tempering_count,
                "confidence": marker.confidence,
                "consistency": marker.consistency,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single somatic marker crucible cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = CruciblePhase.SENSE
            phase_outputs["sense"] = self._phase_sense()
            self._phase = CruciblePhase.IMPRINT
            phase_outputs["imprint"] = self._phase_imprint()
            self._phase = CruciblePhase.TEMPER
            phase_outputs["temper"] = self._phase_temper()
            self._phase = CruciblePhase.ALLOY
            phase_outputs["alloy"] = self._phase_alloy()
            self._phase = CruciblePhase.CAST
            phase_outputs["cast"] = self._phase_cast()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_sense(self) -> Dict[str, Any]:
        """Sensing phase: markers that haven't been triggered recently fade slightly."""
        faded = 0
        now = time.time()
        for agent in self._agents.values():
            for marker in agent.markers.values():
                if marker.state in (MarkerState.ALLOYED, MarkerState.CAST):
                    continue
                # markers not triggered recently slowly fade
                if marker.last_triggered > 0:
                    elapsed = now - marker.last_triggered
                    if elapsed > 60:  # more than a minute since last trigger
                        marker.intensity = max(0.1, marker.intensity - 0.02)
                        faded += 1
        return {
            "markers_faded": faded,
            "active_markers": sum(
                1 for a in self._agents.values()
                for m in a.markers.values()
                if m.state not in (MarkerState.DULL,)
            ),
        }

    def _phase_imprint(self) -> Dict[str, Any]:
        """Imprinting phase: fresh markers gain stability."""
        stabilized = 0
        for agent in self._agents.values():
            for marker in agent.markers.values():
                if marker.state != MarkerState.FRESH:
                    continue
                # fresh markers with high consistency stabilize
                if marker.consistency > 0.5 and marker.tempering_count >= 1:
                    marker.state = MarkerState.TEMPERING
                    stabilized += 1
                # fresh markers with low consistency fade
                elif marker.consistency < 0.3:
                    marker.intensity = max(0.0, marker.intensity - 0.05)
        return {
            "fresh_markers_stabilized": stabilized,
            "total_fresh": sum(
                1 for a in self._agents.values()
                for m in a.markers.values()
                if m.state == MarkerState.FRESH
            ),
        }

    def _phase_temper(self) -> Dict[str, Any]:
        """Tempering phase: tempering markers gradually become stable."""
        tempered = 0
        dulled = 0
        for agent in self._agents.values():
            for marker in agent.markers.values():
                if marker.state != MarkerState.TEMPERING:
                    continue
                # gradual confidence increase
                marker.confidence = min(1.0, marker.confidence + 0.01 * agent.tempering_rate)
                # promote to stable if confident enough
                if marker.confidence > 0.65 and marker.tempering_count >= 3:
                    marker.state = MarkerState.STABLE
                    tempered += 1
                    self._record_event("marker_stabilized", {
                        "agent_id": agent.agent_id,
                        "marker_id": marker.marker_id,
                        "confidence": marker.confidence,
                    })
                # dull if consistency drops too low
                elif marker.consistency < 0.2:
                    marker.state = MarkerState.DULL
                    dulled += 1
        self._stats["total_tempering_events"] += tempered
        return {
            "markers_tempered_to_stable": tempered,
            "markers_dulled": dulled,
        }

    def _phase_alloy(self) -> Dict[str, Any]:
        """Alloy phase: stable markers with shared archetypes alloy into dispositions."""
        alloyed = 0
        dispositions_formed = 0
        for agent in self._agents.values():
            # group stable markers by archetype
            groups: Dict[SituationArchetype, List[SomaticMarker]] = {}
            for marker in agent.markers.values():
                if marker.state != MarkerState.STABLE:
                    continue
                groups.setdefault(marker.archetype, []).append(marker)
            for archetype, group in groups.items():
                if len(group) < agent.alloy_threshold:
                    continue
                # check if a disposition already exists for this archetype
                existing = None
                for d in agent.dispositions.values():
                    if any(m.archetype == archetype for m in group if m.marker_id in d.contributing_markers):
                        existing = d
                        break
                if existing:
                    # strengthen existing disposition
                    for m in group:
                        if m.marker_id not in existing.contributing_markers:
                            existing.contributing_markers.append(m.marker_id)
                            m.state = MarkerState.ALLOYED
                            alloyed += 1
                    existing.strength = min(1.0, existing.strength + 0.05)
                    existing.breadth = min(1.0, existing.breadth + 0.02)
                else:
                    # form new disposition
                    disp_id = f"disp_{archetype.value}_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
                    # determine aggregate valence
                    valences = [m.valence for m in group]
                    if all(v == ValencePolarity.APPROACH for v in valences):
                        agg_valence = ValencePolarity.APPROACH
                    elif all(v == ValencePolarity.AVOID for v in valences):
                        agg_valence = ValencePolarity.AVOID
                    elif len(set(valences)) > 1:
                        agg_valence = ValencePolarity.AMBIVALENT
                    else:
                        agg_valence = ValencePolarity.NEUTRAL
                    avg_strength = sum(m.intensity for m in group) / len(group)
                    disposition = CompoundDisposition(
                        disposition_id=disp_id,
                        agent_id=agent.agent_id,
                        label=f"{archetype.value.capitalize()} Disposition",
                        contributing_markers=[m.marker_id for m in group],
                        valence=agg_valence,
                        strength=avg_strength,
                        breadth=0.3 + len(group) * 0.05,
                    )
                    agent.dispositions[disp_id] = disposition
                    agent.total_dispositions += 1
                    for m in group:
                        m.state = MarkerState.ALLOYED
                        alloyed += 1
                    dispositions_formed += 1
                    self._record_event("disposition_alloyed", {
                        "agent_id": agent.agent_id,
                        "disposition_id": disp_id,
                        "archetype": archetype.value,
                        "contributors": len(group),
                        "valence": agg_valence.value,
                    })
        self._stats["total_alloy_events"] += dispositions_formed
        return {
            "markers_alloyed": alloyed,
            "dispositions_formed": dispositions_formed,
        }

    def _phase_cast(self) -> Dict[str, Any]:
        """Cast phase: strong dispositions are cast into decision heuristics."""
        cast = 0
        for agent in self._agents.values():
            for disp in agent.dispositions.values():
                if disp.cast_into_heuristic:
                    continue
                # only cast dispositions with sufficient strength
                if disp.strength < 0.5:
                    continue
                # find the archetype this disposition applies to
                applicable_archetypes = set()
                for mid in disp.contributing_markers:
                    m = agent.markers.get(mid)
                    if m:
                        applicable_archetypes.add(m.archetype)
                if not applicable_archetypes:
                    continue
                heuristic_id = f"heur_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
                bias = self._CAST_BIAS_BASE + disp.strength * 0.4
                # determine bias description
                if disp.valence == ValencePolarity.APPROACH:
                    desc = f"Tendency to approach {disp.label.lower()} situations"
                elif disp.valence == ValencePolarity.AVOID:
                    desc = f"Tendency to avoid {disp.label.lower()} situations"
                elif disp.valence == ValencePolarity.AMBIVALENT:
                    desc = f"Conflicted response to {disp.label.lower()} situations"
                else:
                    desc = f"Cautious engagement with {disp.label.lower()} situations"
                heuristic = DecisionHeuristic(
                    heuristic_id=heuristic_id,
                    agent_id=agent.agent_id,
                    source_disposition=disp.disposition_id,
                    label=f"{disp.label} Heuristic",
                    bias_strength=bias,
                    applies_to=list(applicable_archetypes),
                    description=desc,
                )
                agent.heuristics[heuristic_id] = heuristic
                agent.total_heuristics += 1
                disp.cast_into_heuristic = True
                cast += 1
                self._record_event("heuristic_cast", {
                    "agent_id": agent.agent_id,
                    "heuristic_id": heuristic_id,
                    "bias_strength": bias,
                    "applies_to": [a.value for a in applicable_archetypes],
                })
        self._stats["total_cast_events"] += cast
        return {
            "heuristics_cast": cast,
            "total_heuristics": sum(len(a.heuristics) for a in self._agents.values()),
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Get the full crucible state for an agent."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent_id,
                "sensitivity": a.sensitivity,
                "tempering_rate": a.tempering_rate,
                "alloy_threshold": a.alloy_threshold,
                "total_markers": len(a.markers),
                "total_dispositions": len(a.dispositions),
                "total_heuristics": len(a.heuristics),
                "markers": [self._serialize_marker(m) for m in a.markers.values()],
                "dispositions": [
                    {
                        "disposition_id": d.disposition_id,
                        "label": d.label,
                        "contributing_markers": list(d.contributing_markers),
                        "valence": d.valence.value,
                        "strength": d.strength,
                        "breadth": d.breadth,
                        "cast_into_heuristic": d.cast_into_heuristic,
                    }
                    for d in a.dispositions.values()
                ],
                "heuristics": [
                    {
                        "heuristic_id": h.heuristic_id,
                        "label": h.label,
                        "source_disposition": h.source_disposition,
                        "bias_strength": h.bias_strength,
                        "applies_to": [a.value for a in h.applies_to],
                        "description": h.description,
                        "activation_count": h.activation_count,
                    }
                    for h in a.heuristics.values()
                ],
            }

    def get_marker(self, agent_id: str, marker_id: str) -> Dict[str, Any]:
        """Get a specific marker."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            m = a.markers.get(marker_id)
            if m is None:
                return {"error": f"Marker not found: {marker_id}"}
            return self._serialize_marker(m)

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events log."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the crucible."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple cycles and return the final status."""
        with self._global_lock:
            for _ in range(max(1, cycles)):
                self.cycle()
            return self.get_status()

    def reset(self) -> Dict[str, Any]:
        """Reset the entire crucible."""
        with self._global_lock:
            self._agents.clear()
            self._phase = CruciblePhase.SENSE
            self._cycle_count = 0
            self._events_log.clear()
            self._init_stats()
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _temper_existing(
        self, agent: SomaticAgent, marker_id: str, intensity: float, consistency: float,
    ) -> Dict[str, Any]:
        """Temper an existing marker when the same situation is sensed again."""
        marker = agent.markers[marker_id]
        marker.tempering_count += 1
        marker.last_triggered = time.time()
        # adjust intensity toward the new reading
        marker.intensity = (marker.intensity + intensity) / 2
        # adjust consistency
        if abs(intensity - marker.intensity) < 0.2:
            marker.consistency = min(1.0, marker.consistency + 0.05)
        else:
            marker.consistency = max(0.0, marker.consistency - self._INCONSISTENCY_DECAY)
        # state transitions
        if marker.state == MarkerState.FRESH and marker.tempering_count >= 2:
            marker.state = MarkerState.TEMPERING
        elif marker.state == MarkerState.TEMPERING and marker.confidence > 0.65:
            marker.state = MarkerState.STABLE
        marker.confidence = min(1.0, marker.confidence + self._TEMPERING_CONFIDENCE_BOOST * agent.tempering_rate)
        return {
            "marker_id": marker_id,
            "tempered": True,
            "tempering_count": marker.tempering_count,
            "intensity": marker.intensity,
            "confidence": marker.confidence,
            "consistency": marker.consistency,
            "state": marker.state.value,
        }

    def _update_stats(self) -> None:
        total_markers = 0
        total_dispositions = 0
        total_heuristics = 0
        fresh = 0
        tempering = 0
        stable = 0
        alloyed = 0
        dull = 0
        cast = 0
        total_confidence = 0.0
        total_intensity = 0.0
        for agent in self._agents.values():
            total_markers += len(agent.markers)
            total_dispositions += len(agent.dispositions)
            total_heuristics += len(agent.heuristics)
            for m in agent.markers.values():
                total_confidence += m.confidence
                total_intensity += m.intensity
                if m.state == MarkerState.FRESH:
                    fresh += 1
                elif m.state == MarkerState.TEMPERING:
                    tempering += 1
                elif m.state == MarkerState.STABLE:
                    stable += 1
                elif m.state == MarkerState.ALLOYED:
                    alloyed += 1
                elif m.state == MarkerState.DULL:
                    dull += 1
                elif m.state == MarkerState.CAST:
                    cast += 1
        self._stats["total_markers"] = total_markers
        self._stats["total_dispositions"] = total_dispositions
        self._stats["total_heuristics"] = total_heuristics
        self._stats["fresh_markers"] = fresh
        self._stats["tempering_markers"] = tempering
        self._stats["stable_markers"] = stable
        self._stats["alloyed_markers"] = alloyed
        self._stats["dull_markers"] = dull
        self._stats["cast_markers"] = cast
        self._stats["avg_marker_confidence"] = (
            total_confidence / total_markers if total_markers else 0.0
        )
        self._stats["avg_marker_intensity"] = (
            total_intensity / total_markers if total_markers else 0.0
        )

    def _serialize_marker(self, m: SomaticMarker) -> Dict[str, Any]:
        return {
            "marker_id": m.marker_id,
            "agent_id": m.agent_id,
            "archetype": m.archetype.value,
            "domain": m.domain.value,
            "label": m.label,
            "valence": m.valence.value,
            "intensity": m.intensity,
            "confidence": m.confidence,
            "state": m.state.value,
            "tempering_count": m.tempering_count,
            "consistency": m.consistency,
            "last_triggered": m.last_triggered,
            "forged_at": m.forged_at,
            "trigger_threshold": m.trigger_threshold,
            "situation_tags": list(m.situation_tags),
            "bodily_signature": m.bodily_signature,
            "decision_bias": m.decision_bias,
        }

    def _init_stats(self) -> None:
        self._stats = {
            "total_agents": 0,
            "total_markers": 0,
            "total_dispositions": 0,
            "total_heuristics": 0,
            "fresh_markers": 0,
            "tempering_markers": 0,
            "stable_markers": 0,
            "alloyed_markers": 0,
            "dull_markers": 0,
            "cast_markers": 0,
            "avg_marker_confidence": 0.0,
            "avg_marker_intensity": 0.0,
            "total_tempering_events": 0,
            "total_alloy_events": 0,
            "total_cast_events": 0,
            "last_cycle_time_ms": 0.0,
        }

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
