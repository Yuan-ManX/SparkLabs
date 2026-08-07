"""
SparkLabs Engine - Quantum Reality Forge

The EngineQuantumRealityForge models how game reality is forged from a
quantum foam of possibilities. Rather than treating the game world as a
single deterministic state, the forge treats it as a superposition of
competing possibility-states that entangle, anneal, and collapse into
the experienced reality.

Reality in a game world is not a single thread of "what is" - it is a
field of "what could be" that the engine constantly forges into "what
is now." Each region, each NPC, each event exists as a cloud of
possibility amplitudes that interfere, entangle, and eventually collapse
into the actual game state the player experiences.

The forge models four quantum operations:
  - Superposition: maintain multiple possibility-states for one entity
  - Entanglement: link two entities so collapsing one affects the other
  - Annealing: gradually cool the field, letting high-energy
    impossibilities fade while stable possibilities strengthen
  - Collapse: when an observer (player, narrative event) probes a
    region, the superposition collapses into a single experienced state

This produces a game world that is genuinely alive with potential - where
unvisited regions exist as probability clouds, where distant events can
be entangled so that resolving one shapes the other, and where the act
of observation (player attention) literally forges reality.

Architecture:
  SUPERPOSE  ->  ENTANGLE  ->  ANNEAL   ->  COLLAPSE  ->  FORGE
  (generate  (link related (cool the    (observer     (solidify
   multiple   possibilities field, let  probes and    collapsed
   possible   so they        unstable    collapses     states into
   states     shape each     states      superposition experienced
   for each   other)         fade)       into one)     game reality)
   entity)

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

class ForgePhase(Enum):
    """Phases of the quantum reality forge cycle."""
    SUPERPOSE = "superpose"    # generate multiple possible states
    ENTANGLE = "entangle"      # link related possibilities
    ANNEAL = "anneal"          # cool the field, fade unstable states
    COLLAPSE = "collapse"      # observer probes collapse superposition
    FORGE = "forge"            # solidify collapsed states into reality


class PossibilityClass(Enum):
    """Categories of possibility-states."""
    SPATIAL = "spatial"          # where something is
    TEMPORAL = "temporal"        # when something happens
    IDENTITY = "identity"        # what something is
    EVENT = "event"              # what will happen
    RELATION = "relation"        # how entities connect
    STATE = "state"              # condition of an entity


class AmplitudeState(Enum):
    """Lifecycle of a possibility amplitude."""
    NASCENT = "nascent"          # just spawned, uncertain
    STABILIZING = "stabilizing"  # gaining weight through annealing
    DOMINANT = "dominant"        # leading candidate
    DECAYING = "decaying"        # losing weight
    COLLAPSED = "collapsed"      # selected as the actual state
    EVAPORATED = "evaporated"    # faded out completely


class EntanglementType(Enum):
    """How two possibility clouds are entangled."""
    CORRELATED = "correlated"      # collapse one, the other aligns
    ANTI_CORRELATED = "anti"       # collapse one, the other inverts
    CONDITIONAL = "conditional"    # collapse one, the other constrained
    RESONANT = "resonant"          # amplitudes reinforce
    CAUSAL = "causal"              # one's collapse triggers the other


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PossibilityAmplitude:
    """One possible state of an entity in superposition."""
    amplitude_id: str
    region_id: str
    entity_label: str
    possibility_class: PossibilityClass
    state_description: str
    amplitude: float = 0.5         # probability weight (0.0-1.0, normalized)
    raw_weight: float = 0.5        # unnormalized weight
    energy: float = 0.5            # instability (0.0=stable, 1.0=chaotic)
    state: AmplitudeState = AmplitudeState.NASCENT
    created_at: float = field(default_factory=time.time)
    collapsed_at: Optional[float] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class EntanglementLink:
    """A quantum entanglement between two possibility clouds."""
    link_id: str
    region_a: str
    entity_a: str
    region_b: str
    entity_b: str
    entanglement_type: EntanglementType
    strength: float = 0.5          # how strongly they affect each other
    created_at: float = field(default_factory=time.time)
    triggered: bool = False


@dataclass
class CollapseEvent:
    """Record of a superposition collapse triggered by an observer."""
    event_id: str
    region_id: str
    observer: str
    entity_label: str
    collapsed_amplitude: str
    rejected_count: int
    timestamp: float = field(default_factory=time.time)
    cascaded: List[str] = field(default_factory=list)  # regions affected by entanglement


@dataclass
class ForgedReality:
    """A piece of game reality that has been forged from collapse."""
    reality_id: str
    region_id: str
    entity_label: str
    state_description: str
    forged_from: str               # amplitude_id
    forged_at: float = field(default_factory=time.time)
    stability: float = 1.0         # how settled (decays back to possibility over time)


@dataclass
class ForgeRegion:
    """Per-region forge state."""
    region_id: str
    label: str
    amplitudes: Dict[str, PossibilityAmplitude] = field(default_factory=dict)
    entanglements: List[str] = field(default_factory=list)  # link_ids
    forged: Dict[str, ForgedReality] = field(default_factory=dict)
    temperature: float = 1.0       # annealing temperature (1.0=hot, 0.0=frozen)
    observer_present: bool = False
    last_observed: float = 0.0


# =============================================================================
# Forge
# =============================================================================

class EngineQuantumRealityForge:
    """
    Thread-safe singleton orchestrating quantum reality forging across regions.

    Usage:
        forge = EngineQuantumRealityForge.get_instance()
        forge.register_region("r_forest", "Mystic Forest")
        forge.superpose("r_forest", "Forest Spirit", PossibilityClass.IDENTITY,
                       "Benevolent", raw_weight=0.6, energy=0.3)
        forge.superpose("r_forest", "Forest Spirit", PossibilityClass.IDENTITY,
                       "Malevolent", raw_weight=0.4, energy=0.5)
        forge.entangle("r_forest", "Forest Spirit", "r_village", "Village Mood",
                      EntanglementType.CORRELATED, strength=0.7)
        forge.observe("r_forest", "player_1", "Forest Spirit")
        forge.cycle()
    """

    _instance: Optional["EngineQuantumRealityForge"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._regions: Dict[str, ForgeRegion] = {}
        self._entanglements: Dict[str, EntanglementLink] = {}
        self._collapses: Deque[CollapseEvent] = deque(maxlen=200)
        self._phase: ForgePhase = ForgePhase.SUPERPOSE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_regions": 0,
            "total_amplitudes": 0,
            "total_entanglements": 0,
            "total_collapses": 0,
            "total_forged": 0,
            "total_evaporated": 0,
            "active_superpositions": 0,
            "avg_temperature": 0.0,
            "avg_energy": 0.0,
            "cascaded_collapses": 0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineQuantumRealityForge":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Region Management
    # -------------------------------------------------------------------------

    def register_region(self, region_id: str, label: str, temperature: float = 1.0) -> Dict[str, Any]:
        """Register a new region with the forge."""
        with self._global_lock:
            if region_id in self._regions:
                return {"error": f"Region already registered: {region_id}"}
            self._regions[region_id] = ForgeRegion(
                region_id=region_id,
                label=label,
                temperature=max(0.0, min(1.0, temperature)),
            )
            self._stats["total_regions"] = len(self._regions)
            self._record_event("region_registered", {"region_id": region_id, "label": label})
            return {"region_id": region_id, "label": label, "temperature": self._regions[region_id].temperature}

    def remove_region(self, region_id: str) -> Dict[str, Any]:
        """Remove a region from the forge."""
        with self._global_lock:
            if region_id not in self._regions:
                return {"error": f"Region not found: {region_id}"}
            r = self._regions.pop(region_id)
            # remove entanglements involving this region
            to_remove = [lid for lid, l in self._entanglements.items()
                         if l.region_a == region_id or l.region_b == region_id]
            for lid in to_remove:
                self._entanglements.pop(lid, None)
            self._stats["total_regions"] = len(self._regions)
            self._stats["total_entanglements"] = len(self._entanglements)
            return {"removed": region_id, "amplitudes": len(r.amplitudes), "forged": len(r.forged)}

    # -------------------------------------------------------------------------
    # Superposition
    # -------------------------------------------------------------------------

    def superpose(
        self,
        region_id: str,
        entity_label: str,
        possibility_class: PossibilityClass,
        state_description: str,
        raw_weight: float = 0.5,
        energy: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Add a possibility amplitude to a region's superposition."""
        with self._global_lock:
            r = self._regions.get(region_id)
            if r is None:
                return {"error": f"Region not found: {region_id}"}
            amp_id = f"amp_{region_id}_{entity_label}_{len(r.amplitudes)}"
            amp = PossibilityAmplitude(
                amplitude_id=amp_id,
                region_id=region_id,
                entity_label=entity_label,
                possibility_class=possibility_class,
                state_description=state_description,
                raw_weight=max(0.01, raw_weight),
                energy=max(0.0, min(1.0, energy)),
                tags=tags or [],
            )
            r.amplitudes[amp_id] = amp
            self._normalize_region(region_id)
            self._update_counts()
            self._record_event("amplitude_superposed", {
                "region_id": region_id, "amplitude_id": amp_id,
                "entity": entity_label, "state": state_description,
            })
            return {
                "amplitude_id": amp_id,
                "region_id": region_id,
                "entity_label": entity_label,
                "possibility_class": possibility_class.value,
                "state_description": state_description,
                "amplitude": amp.amplitude,
                "energy": amp.energy,
            }

    # -------------------------------------------------------------------------
    # Entanglement
    # -------------------------------------------------------------------------

    def entangle(
        self,
        region_a: str,
        entity_a: str,
        region_b: str,
        entity_b: str,
        entanglement_type: EntanglementType,
        strength: float = 0.5,
    ) -> Dict[str, Any]:
        """Entangle two possibility clouds across regions."""
        with self._global_lock:
            if region_a not in self._regions or region_b not in self._regions:
                return {"error": "Region not found"}
            link_id = f"ent_{len(self._entanglements)}"
            link = EntanglementLink(
                link_id=link_id,
                region_a=region_a,
                entity_a=entity_a,
                region_b=region_b,
                entity_b=entity_b,
                entanglement_type=entanglement_type,
                strength=max(0.0, min(1.0, strength)),
            )
            self._entanglements[link_id] = link
            self._regions[region_a].entanglements.append(link_id)
            self._regions[region_b].entanglements.append(link_id)
            self._stats["total_entanglements"] = len(self._entanglements)
            self._record_event("entanglement_created", {
                "link_id": link_id, "region_a": region_a, "region_b": region_b,
                "type": entanglement_type.value,
            })
            return {
                "link_id": link_id,
                "region_a": region_a,
                "entity_a": entity_a,
                "region_b": region_b,
                "entity_b": entity_b,
                "entanglement_type": entanglement_type.value,
                "strength": link.strength,
            }

    # -------------------------------------------------------------------------
    # Observation & Collapse
    # -------------------------------------------------------------------------

    def observe(self, region_id: str, observer: str, entity_label: str) -> Dict[str, Any]:
        """An observer probes a region, collapsing the entity's superposition."""
        with self._global_lock:
            r = self._regions.get(region_id)
            if r is None:
                return {"error": f"Region not found: {region_id}"}
            r.observer_present = True
            r.last_observed = time.time()
            # find amplitudes for this entity that are not yet collapsed
            candidates = [
                a for a in r.amplitudes.values()
                if a.entity_label == entity_label and a.state not in (AmplitudeState.COLLAPSED, AmplitudeState.EVAPORATED)
            ]
            if not candidates:
                return {"error": f"No superposition to collapse for {entity_label} in {region_id}"}
            # weighted random selection by amplitude
            total = sum(a.amplitude for a in candidates)
            if total <= 0:
                # uniform fallback
                chosen = random.choice(candidates)
            else:
                roll = random.random() * total
                acc = 0.0
                chosen = candidates[0]
                for a in candidates:
                    acc += a.amplitude
                    if roll <= acc:
                        chosen = a
                        break
            # collapse: chosen becomes actual, others evaporate
            chosen.state = AmplitudeState.COLLAPSED
            chosen.collapsed_at = time.time()
            rejected = 0
            for a in candidates:
                if a is not chosen:
                    a.state = AmplitudeState.EVAPORATED
                    rejected += 1
            event_id = f"col_{len(self._collapses)}"
            event = CollapseEvent(
                event_id=event_id,
                region_id=region_id,
                observer=observer,
                entity_label=entity_label,
                collapsed_amplitude=chosen.amplitude_id,
                rejected_count=rejected,
            )
            # cascade through entanglements
            cascaded: List[str] = []
            for link_id in r.entanglements:
                link = self._entanglements.get(link_id)
                if link is None or link.triggered:
                    continue
                # only cascade if this region/entity is one side of the link
                if link.region_a == region_id and link.entity_a == entity_label:
                    other_region = link.region_b
                    other_entity = link.entity_b
                elif link.region_b == region_id and link.entity_b == entity_label:
                    other_region = link.region_a
                    other_entity = link.entity_a
                else:
                    continue
                cascade_result = self._cascade_collapse(other_region, other_entity, link, chosen)
                if cascade_result is not None:
                    cascaded.append(other_region)
                    link.triggered = True
            event.cascaded = cascaded
            self._collapses.append(event)
            self._stats["total_collapses"] += 1
            self._stats["cascaded_collapses"] += len(cascaded)
            self._record_event("superposition_collapsed", {
                "region_id": region_id, "entity": entity_label,
                "chosen": chosen.amplitude_id, "rejected": rejected,
                "cascaded": cascaded,
            })
            return {
                "event_id": event_id,
                "region_id": region_id,
                "observer": observer,
                "entity_label": entity_label,
                "collapsed_amplitude": chosen.amplitude_id,
                "collapsed_state": chosen.state_description,
                "rejected_count": rejected,
                "cascaded_regions": cascaded,
            }

    def _cascade_collapse(
        self,
        region_id: str,
        entity_label: str,
        link: EntanglementLink,
        source: PossibilityAmplitude,
    ) -> Optional[str]:
        """Cascade a collapse through an entanglement link."""
        r = self._regions.get(region_id)
        if r is None:
            return None
        candidates = [
            a for a in r.amplitudes.values()
            if a.entity_label == entity_label and a.state not in (AmplitudeState.COLLAPSED, AmplitudeState.EVAPORATED)
        ]
        if not candidates:
            return None
        # select based on entanglement type
        if link.entanglement_type == EntanglementType.CORRELATED:
            # pick the candidate most similar in description length (proxy)
            target_len = len(source.state_description)
            chosen = min(candidates, key=lambda a: abs(len(a.state_description) - target_len))
        elif link.entanglement_type == EntanglementType.ANTI_CORRELATED:
            # pick the candidate most different
            target_len = len(source.state_description)
            chosen = max(candidates, key=lambda a: abs(len(a.state_description) - target_len))
        elif link.entanglement_type == EntanglementType.CAUSAL:
            # pick the dominant one
            chosen = max(candidates, key=lambda a: a.amplitude)
        else:
            # weighted random
            total = sum(a.amplitude for a in candidates)
            if total <= 0:
                chosen = random.choice(candidates)
            else:
                roll = random.random() * total
                acc = 0.0
                chosen = candidates[0]
                for a in candidates:
                    acc += a.amplitude
                    if roll <= acc:
                        chosen = a
                        break
        chosen.state = AmplitudeState.COLLAPSED
        chosen.collapsed_at = time.time()
        for a in candidates:
            if a is not chosen:
                a.state = AmplitudeState.EVAPORATED
        return chosen.amplitude_id

    # -------------------------------------------------------------------------
    # Phase: SUPERPOSE - generate new possibilities
    # -------------------------------------------------------------------------

    def _phase_superpose(self) -> Dict[str, Any]:
        """Generate spontaneous new possibilities in cold regions."""
        spawned = 0
        for r in self._regions.values():
            # cold regions spontaneously generate new possibilities
            if r.temperature < 0.5 and random.random() < 0.15:
                # pick a random entity in the region to spawn a variant for
                entities = list({a.entity_label for a in r.amplitudes.values()})
                if not entities:
                    continue
                entity = random.choice(entities)
                amp_id = f"amp_{r.region_id}_{entity}_{len(r.amplitudes)}_spont"
                amp = PossibilityAmplitude(
                    amplitude_id=amp_id,
                    region_id=r.region_id,
                    entity_label=entity,
                    possibility_class=PossibilityClass.STATE,
                    state_description=f"spontaneous variant {spawned}",
                    raw_weight=0.2,
                    energy=r.temperature,
                    state=AmplitudeState.NASCENT,
                )
                r.amplitudes[amp_id] = amp
                spawned += 1
        if spawned > 0:
            for rid in self._regions:
                self._normalize_region(rid)
            self._update_counts()
        return {"spontaneous_spawned": spawned}

    # -------------------------------------------------------------------------
    # Phase: ENTANGLE - discover new entanglements
    # -------------------------------------------------------------------------

    def _phase_entangle(self) -> Dict[str, Any]:
        """Discover latent entanglements between regions with shared entities."""
        discovered = 0
        region_ids = list(self._regions.keys())
        for i in range(len(region_ids)):
            for j in range(i + 1, len(region_ids)):
                ra = self._regions[region_ids[i]]
                rb = self._regions[region_ids[j]]
                # find shared entity labels
                entities_a = {a.entity_label for a in ra.amplitudes.values()}
                entities_b = {a.entity_label for a in rb.amplitudes.values()}
                shared = entities_a & entities_b
                for entity in shared:
                    # check if already entangled
                    already = False
                    for lid in ra.entanglements:
                        link = self._entanglements.get(lid)
                        if link is None:
                            continue
                        if ((link.region_a == ra.region_id and link.entity_a == entity and
                             link.region_b == rb.region_id) or
                            (link.region_b == ra.region_id and link.entity_b == entity and
                             link.region_a == rb.region_id)):
                            already = True
                            break
                    if already:
                        continue
                    if random.random() < 0.2:
                        etype = random.choice(list(EntanglementType))
                        result = self.entangle(
                            ra.region_id, entity, rb.region_id, entity, etype, strength=0.4
                        )
                        if "link_id" in result:
                            discovered += 1
        return {"entanglements_discovered": discovered}

    # -------------------------------------------------------------------------
    # Phase: ANNEAL - cool the field, fade unstable states
    # -------------------------------------------------------------------------

    def _phase_anneal(self) -> Dict[str, Any]:
        """Cool the field, let unstable amplitudes decay."""
        faded = 0
        stabilized = 0
        total_temp = 0.0
        total_energy = 0.0
        amp_count = 0
        for r in self._regions.values():
            # cool down
            r.temperature = max(0.0, r.temperature - 0.05)
            if r.observer_present:
                # observing keeps region warmer (more generative)
                r.temperature = max(r.temperature, 0.3)
                r.observer_present = False  # reset; observer must re-observe
            total_temp += r.temperature
            for a in r.amplitudes.values():
                if a.state in (AmplitudeState.COLLAPSED, AmplitudeState.EVAPORATED):
                    continue
                # high-energy amplitudes decay faster in cold regions
                decay = a.energy * (1.0 - r.temperature) * 0.1
                a.raw_weight = max(0.0, a.raw_weight - decay)
                if a.raw_weight < 0.05:
                    a.state = AmplitudeState.EVAPORATED
                    faded += 1
                elif a.raw_weight > 0.5 and a.state == AmplitudeState.NASCENT:
                    a.state = AmplitudeState.STABILIZING
                    stabilized += 1
                elif a.raw_weight > 0.7 and a.state == AmplitudeState.STABILIZING:
                    a.state = AmplitudeState.DOMINANT
                total_energy += a.energy
                amp_count += 1
            self._normalize_region(r.region_id)
        self._stats["total_evaporated"] += faded
        self._stats["avg_temperature"] = total_temp / max(1, len(self._regions))
        self._stats["avg_energy"] = total_energy / max(1, amp_count)
        return {"faded": faded, "stabilized": stabilized}

    # -------------------------------------------------------------------------
    # Phase: COLLAPSE - auto-collapse dominant amplitudes
    # -------------------------------------------------------------------------

    def _phase_collapse(self) -> Dict[str, Any]:
        """Auto-collapse dominant amplitudes that have been stable."""
        auto_collapsed = 0
        for r in self._regions.values():
            for a in list(r.amplitudes.values()):
                if a.state != AmplitudeState.DOMINANT:
                    continue
                # dominant amplitudes in cold regions auto-collapse
                if r.temperature < 0.3 and a.amplitude > 0.7:
                    a.state = AmplitudeState.COLLAPSED
                    a.collapsed_at = time.time()
                    # evaporate competitors for the same entity
                    for other in r.amplitudes.values():
                        if (other.entity_label == a.entity_label and
                            other is not a and
                            other.state not in (AmplitudeState.COLLAPSED, AmplitudeState.EVAPORATED)):
                            other.state = AmplitudeState.EVAPORATED
                    auto_collapsed += 1
                    self._record_event("auto_collapse", {
                        "region_id": r.region_id, "amplitude_id": a.amplitude_id,
                    })
        self._stats["total_collapses"] += auto_collapsed
        return {"auto_collapsed": auto_collapsed}

    # -------------------------------------------------------------------------
    # Phase: FORGE - solidify collapsed amplitudes into reality
    # -------------------------------------------------------------------------

    def _phase_forge(self) -> Dict[str, Any]:
        """Forge collapsed amplitudes into stable game reality."""
        forged = 0
        for r in self._regions.values():
            for a in list(r.amplitudes.values()):
                if a.state != AmplitudeState.COLLAPSED:
                    continue
                # check if already forged
                already = any(
                    fr.forged_from == a.amplitude_id for fr in r.forged.values()
                )
                if already:
                    continue
                reality_id = f"real_{r.region_id}_{len(r.forged)}"
                forged_reality = ForgedReality(
                    reality_id=reality_id,
                    region_id=r.region_id,
                    entity_label=a.entity_label,
                    state_description=a.state_description,
                    forged_from=a.amplitude_id,
                    stability=1.0 - a.energy * 0.3,
                )
                r.forged[reality_id] = forged_reality
                forged += 1
                self._record_event("reality_forged", {
                    "region_id": r.region_id, "reality_id": reality_id,
                    "entity": a.entity_label, "state": a.state_description,
                })
        self._stats["total_forged"] += forged
        # decay stability of old forged realities (they become possibility again)
        for r in self._regions.values():
            for fr in r.forged.values():
                fr.stability = max(0.0, fr.stability - 0.02)
        return {"forged": forged}

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single quantum reality forge cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = ForgePhase.SUPERPOSE
            phase_outputs["superpose"] = self._phase_superpose()
            self._phase = ForgePhase.ENTANGLE
            phase_outputs["entangle"] = self._phase_entangle()
            self._phase = ForgePhase.ANNEAL
            phase_outputs["anneal"] = self._phase_anneal()
            self._phase = ForgePhase.COLLAPSE
            phase_outputs["collapse"] = self._phase_collapse()
            self._phase = ForgePhase.FORGE
            phase_outputs["forge"] = self._phase_forge()
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
        """Run multiple cycles in sequence and return final stats."""
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

    def get_region_state(self, region_id: str) -> Dict[str, Any]:
        """Get full state of a region in the forge."""
        with self._global_lock:
            r = self._regions.get(region_id)
            if r is None:
                return {"error": f"Region not found: {region_id}"}
            return {
                "region_id": region_id,
                "label": r.label,
                "temperature": r.temperature,
                "observer_present": r.observer_present,
                "last_observed": r.last_observed,
                "total_amplitudes": len(r.amplitudes),
                "active_amplitudes": sum(
                    1 for a in r.amplitudes.values()
                    if a.state not in (AmplitudeState.COLLAPSED, AmplitudeState.EVAPORATED)
                ),
                "total_forged": len(r.forged),
                "amplitudes": [
                    {
                        "amplitude_id": a.amplitude_id,
                        "entity_label": a.entity_label,
                        "possibility_class": a.possibility_class.value,
                        "state_description": a.state_description,
                        "amplitude": a.amplitude,
                        "energy": a.energy,
                        "state": a.state.value,
                        "tags": a.tags,
                    }
                    for a in r.amplitudes.values()
                ],
                "forged_realities": [
                    {
                        "reality_id": fr.reality_id,
                        "entity_label": fr.entity_label,
                        "state_description": fr.state_description,
                        "stability": fr.stability,
                        "forged_from": fr.forged_from,
                    }
                    for fr in r.forged.values()
                ],
            }

    def get_entanglements(self, region_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get entanglements, optionally filtered by region."""
        with self._global_lock:
            result = []
            for link in self._entanglements.values():
                if region_id and link.region_a != region_id and link.region_b != region_id:
                    continue
                result.append({
                    "link_id": link.link_id,
                    "region_a": link.region_a,
                    "entity_a": link.entity_a,
                    "region_b": link.region_b,
                    "entity_b": link.entity_b,
                    "entanglement_type": link.entanglement_type.value,
                    "strength": link.strength,
                    "triggered": link.triggered,
                })
            return result

    def get_collapses(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent collapse events."""
        with self._global_lock:
            recent = list(self._collapses)[-limit:]
            return [
                {
                    "event_id": e.event_id,
                    "region_id": e.region_id,
                    "observer": e.observer,
                    "entity_label": e.entity_label,
                    "collapsed_amplitude": e.collapsed_amplitude,
                    "rejected_count": e.rejected_count,
                    "cascaded": e.cascaded,
                    "timestamp": e.timestamp,
                }
                for e in recent
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events from the log."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get forge status."""
        with self._global_lock:
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "stats": dict(self._stats),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the entire forge."""
        with self._global_lock:
            count = len(self._regions)
            self._regions.clear()
            self._entanglements.clear()
            self._collapses.clear()
            self._events_log.clear()
            self._cycle_count = 0
            self._phase = ForgePhase.SUPERPOSE
            self._stats = {
                "total_regions": 0,
                "total_amplitudes": 0,
                "total_entanglements": 0,
                "total_collapses": 0,
                "total_forged": 0,
                "total_evaporated": 0,
                "active_superpositions": 0,
                "avg_temperature": 0.0,
                "avg_energy": 0.0,
                "cascaded_collapses": 0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "regions_removed": count}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _normalize_region(self, region_id: str) -> None:
        """Normalize amplitudes in a region so they sum to 1.0."""
        r = self._regions.get(region_id)
        if r is None:
            return
        active = [a for a in r.amplitudes.values()
                  if a.state not in (AmplitudeState.COLLAPSED, AmplitudeState.EVAPORATED)]
        if not active:
            return
        total = sum(a.raw_weight for a in active)
        if total <= 0:
            return
        for a in active:
            a.amplitude = a.raw_weight / total

    def _update_counts(self) -> None:
        total_amp = sum(len(r.amplitudes) for r in self._regions.values())
        active = sum(
            1 for r in self._regions.values() for a in r.amplitudes.values()
            if a.state not in (AmplitudeState.COLLAPSED, AmplitudeState.EVAPORATED)
        )
        self._stats["total_amplitudes"] = total_amp
        self._stats["active_superpositions"] = active
        self._stats["total_entanglements"] = len(self._entanglements)

    def _update_stats(self) -> None:
        self._update_counts()
        total_forged = sum(len(r.forged) for r in self._regions.values())
        self._stats["total_forged"] = total_forged

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "timestamp": time.time(),
            "type": event_type,
            **payload,
        })
