"""
SparkLabs Engine - Quantum State Projector"""

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

class QuantumPhase(Enum):
    """Phases of the quantum state cycle."""
    SUPERPOSE = "superpose"
    ENTANGLE = "entangle"
    EVOLVE = "evolve"
    DECOHERE = "decohere"
    COLLAPSE = "collapse"


class ObservationType(Enum):
    """Types of observations that can collapse wave functions."""
    PLAYER_INTERACT = "player_interact"
    PLAYER_PERCEIVE = "player_perceive"
    AGENT_PERCEIVE = "agent_perceive"
    AGENT_INTERACT = "agent_interact"
    PROXIMITY = "proximity"
    SCRIPTED = "scripted"
    COLLISION = "collision"


class EntanglementType(Enum):
    """Types of quantum entanglement between objects."""
    CORRELATED = "correlated"      # same state collapsed
    ANTI_CORRELATED = "anti"       # opposite state collapsed
    CONDITIONAL = "conditional"    # state depends on partner


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class QuantumState:
    """A single potential state in a superposition."""
    state_id: str
    label: str                    # human-readable state name
    amplitude: float              # probability amplitude (complex, but we use real)
    probability: float            # |amplitude|^2, normalized to [0, 1]
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuantumObject:
    """A game object existing in quantum superposition."""
    object_id: str
    object_type: str              # "chest", "door", "npc", "item", etc.
    # Possible states in superposition
    states: List[QuantumState]
    # Current collapsed state (None if still in superposition)
    collapsed_state_id: Optional[str] = None
    # Whether the object is currently in superposition
    in_superposition: bool = True
    # Entanglement links: object_id -> EntanglementType
    entanglements: Dict[str, EntanglementType] = field(default_factory=dict)
    # Coherence level (1.0 = fully coherent superposition, 0.0 = collapsed)
    coherence: float = 1.0
    # Decoherence rate (how fast superposition decays)
    decoherence_rate: float = 0.05
    # Number of times this object has been observed/collapsed
    collapse_count: int = 0
    # Metadata
    created_at: float = field(default_factory=time.time)
    last_collapsed_at: float = 0.0
    last_evolved_at: float = field(default_factory=time.time)


@dataclass
class EntanglementLink:
    """A quantum entanglement link between two objects."""
    object_a: str
    object_b: str
    link_type: EntanglementType
    strength: float               # 0.0 - 1.0
    created_at: float
    # For conditional entanglement: which state of A maps to which state of B
    state_mapping: Dict[str, str] = field(default_factory=dict)


@dataclass
class CollapseEvent:
    """A recorded wave function collapse event."""
    event_id: str
    object_id: str
    observation_type: ObservationType
    collapsed_state_id: str
    collapsed_label: str
    prior_probabilities: Dict[str, float]
    timestamp: float
    observer: str = ""
    # Entanglement cascade: objects affected by this collapse
    cascade_affected: List[str] = field(default_factory=list)


@dataclass
class QuantumStats:
    """Aggregate statistics for the quantum projector."""
    total_objects: int = 0
    total_superpositions: int = 0
    total_collapses: int = 0
    total_entanglements: int = 0
    total_observations: int = 0
    total_cascade_collapses: int = 0
    total_tunneling_events: int = 0
    avg_coherence: float = 1.0
    superposition_ratio: float = 1.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Engine Quantum State Projector
# =============================================================================

class EngineQuantumStateProjector:
    """
    Singleton engine module that models game objects in quantum
    superposition, enabling genuinely unpredictable but coherent worlds.

    The projector runs a 5-phase cycle:
      1. SUPERPOSE  - Objects enter or refresh their superposition states
      2. ENTANGLE   - Compatible objects become quantum-entangled
      3. EVOLVE     - Wave functions evolve (probabilities shift over time)
      4. DECOHERE   - Natural decoherence moves objects toward definite states
      5. COLLAPSE   - Pending observations trigger wave function collapse

    The quantum metaphor ensures that game worlds feel alive and
    uncertain: the same location can yield different experiences on
    different playthroughs, while remaining internally consistent.
    """

    _instance: Optional["EngineQuantumStateProjector"] = None
    _instance_lock = threading.Lock()

    # Configuration
    MAX_OBJECTS = 300
    MAX_COLLAPSE_HISTORY = 100
    # Minimum probability for a state to remain in superposition
    MIN_STATE_PROBABILITY = 0.01
    # Coherence threshold for decoherence collapse
    DECOHERENCE_COLLAPSE_THRESHOLD = 0.15
    # Maximum entanglements per object
    MAX_ENTANGLEMENTS_PER_OBJECT = 5
    # Entanglement formation probability per cycle
    ENTANGLEMENT_FORMATION_CHANCE = 0.3
    # Wave function evolution rate
    EVOLUTION_RATE = 0.05
    # Quantum tunneling probability per cycle
    TUNNELING_CHANCE = 0.02

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._objects: Dict[str, QuantumObject] = {}
        self._entanglements: Dict[str, EntanglementLink] = {}
        self._pending_observations: Deque[Tuple[str, ObservationType, str]] = deque()
        self._collapse_history: Deque[CollapseEvent] = deque(maxlen=self.MAX_COLLAPSE_HISTORY)
        self._stats = QuantumStats()
        self._cycle_count: int = 0
        self._active: bool = False

    @classmethod
    def get_instance(cls) -> "EngineQuantumStateProjector":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Object Management
    # -------------------------------------------------------------------------

    def register_object(self, object_id: str, object_type: str,
                        states: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Register a new quantum object with possible states.

        Each state dict should have: state_id, label, properties (optional),
        probability (optional, will be normalized).
        """
        with self._lock:
            if object_id in self._objects:
                return {"error": f"Object already exists: {object_id}"}
            if len(self._objects) >= self.MAX_OBJECTS:
                return {"error": "Maximum objects reached"}
            if not states or len(states) < 2:
                return {"error": "Object must have at least 2 states"}

            quantum_states: List[QuantumState] = []
            # Parse and normalize probabilities
            raw_probs = []
            for s in states:
                sid = str(s.get("state_id", f"state_{len(quantum_states)}"))
                label = str(s.get("label", sid))
                props = s.get("properties", {})
                prob = float(s.get("probability", 1.0 / len(states)))
                raw_probs.append(max(0.0, prob))
                quantum_states.append(QuantumState(
                    state_id=sid,
                    label=label,
                    amplitude=0.0,  # computed below
                    probability=0.0,
                    properties=props,
                ))

            # Normalize probabilities
            total = sum(raw_probs)
            if total <= 0:
                total = len(raw_probs)
                raw_probs = [1.0 / total] * len(raw_probs)
            for i, qs in enumerate(quantum_states):
                qs.probability = round(raw_probs[i] / total, 6)
                qs.amplitude = round(math.sqrt(qs.probability), 6)

            obj = QuantumObject(
                object_id=object_id,
                object_type=object_type,
                states=quantum_states,
            )
            self._objects[object_id] = obj
            self._stats.total_objects += 1
            self._stats.total_superpositions += 1
            return self._object_to_dict(obj)

    def get_object(self, object_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            obj = self._objects.get(object_id)
            return self._object_to_dict(obj) if obj else None

    def list_objects(self, object_type: Optional[str] = None,
                     superposition_only: bool = False,
                     limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            results = []
            for obj in self._objects.values():
                if object_type and obj.object_type != object_type:
                    continue
                if superposition_only and not obj.in_superposition:
                    continue
                results.append(self._object_to_dict(obj))
            results.sort(key=lambda o: o.get("created_at", 0), reverse=True)
            return results[:limit]

    def remove_object(self, object_id: str) -> Dict[str, Any]:
        with self._lock:
            if object_id not in self._objects:
                return {"removed": False}
            # Remove entanglement links
            link_ids_to_remove = [
                lid for lid, link in self._entanglements.items()
                if link.object_a == object_id or link.object_b == object_id
            ]
            for lid in link_ids_to_remove:
                # Also clean up the partner's entanglement dict
                link = self._entanglements[lid]
                partner = link.object_b if link.object_a == object_id else link.object_a
                if partner in self._objects:
                    self._objects[partner].entanglements.pop(object_id, None)
                del self._entanglements[lid]
            del self._objects[object_id]
            return {"removed": True, "object_id": object_id,
                    "cleaned_entanglements": len(link_ids_to_remove)}

    # -------------------------------------------------------------------------
    # Entanglement Management
    # -------------------------------------------------------------------------

    def entangle_objects(self, object_a: str, object_b: str,
                         link_type: str = "correlated") -> Dict[str, Any]:
        """Create a quantum entanglement between two objects."""
        with self._lock:
            if object_a not in self._objects or object_b not in self._objects:
                return {"error": "One or both objects not found"}
            if object_a == object_b:
                return {"error": "Cannot entangle object with itself"}
            try:
                ent_type = EntanglementType(link_type)
            except ValueError:
                return {"error": f"Unknown entanglement type: {link_type}"}

            obj_a = self._objects[object_a]
            obj_b = self._objects[object_b]
            if len(obj_a.entanglements) >= self.MAX_ENTANGLEMENTS_PER_OBJECT or \
               len(obj_b.entanglements) >= self.MAX_ENTANGLEMENTS_PER_OBJECT:
                return {"error": "Maximum entanglements per object reached"}

            # Check if already entangled
            if object_b in obj_a.entanglements:
                return {"error": "Objects already entangled"}

            link_id = f"ent_{object_a}_{object_b}"
            link = EntanglementLink(
                object_a=object_a,
                object_b=object_b,
                link_type=ent_type,
                strength=round(random.uniform(0.5, 1.0), 4),
                created_at=time.time(),
            )

            # For conditional entanglement, create state mapping
            if ent_type == EntanglementType.CONDITIONAL:
                states_a = [s.state_id for s in obj_a.states]
                states_b = [s.state_id for s in obj_b.states]
                min_len = min(len(states_a), len(states_b))
                for i in range(min_len):
                    link.state_mapping[states_a[i]] = states_b[i]

            self._entanglements[link_id] = link
            obj_a.entanglements[object_b] = ent_type
            obj_b.entanglements[object_a] = ent_type
            self._stats.total_entanglements += 1
            return {
                "link_id": link_id,
                "object_a": object_a,
                "object_b": object_b,
                "link_type": ent_type.value,
                "strength": link.strength,
                "state_mapping": link.state_mapping,
            }

    def list_entanglements(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            results = []
            for link in self._entanglements.values():
                results.append({
                    "link_id": f"ent_{link.object_a}_{link.object_b}",
                    "object_a": link.object_a,
                    "object_b": link.object_b,
                    "link_type": link.link_type.value,
                    "strength": link.strength,
                    "created_at": link.created_at,
                    "state_mapping": link.state_mapping,
                })
            results.sort(key=lambda l: l.get("created_at", 0), reverse=True)
            return results[:limit]

    # -------------------------------------------------------------------------
    # Observation and Collapse
    # -------------------------------------------------------------------------

    def observe(self, object_id: str, observation_type: str = "player_interact",
                observer: str = "player") -> Dict[str, Any]:
        """Observe a quantum object, collapsing its wave function."""
        with self._lock:
            obj = self._objects.get(object_id)
            if obj is None:
                return {"error": f"Object not found: {object_id}"}
            try:
                obs_type = ObservationType(observation_type)
            except ValueError:
                return {"error": f"Unknown observation type: {observation_type}"}

            if not obj.in_superposition:
                # Already collapsed
                collapsed = next((s for s in obj.states if s.state_id == obj.collapsed_state_id), None)
                return {
                    "object_id": object_id,
                    "already_collapsed": True,
                    "collapsed_state_id": obj.collapsed_state_id,
                    "collapsed_label": collapsed.label if collapsed else "",
                    "observer": observer,
                }

            # Collapse the wave function using weighted random selection
            prior_probs = {s.state_id: s.probability for s in obj.states}
            state_ids = [s.state_id for s in obj.states]
            weights = [s.probability for s in obj.states]
            collapsed_id = random.choices(state_ids, weights=weights, k=1)[0]
            collapsed_state = next(s for s in obj.states if s.state_id == collapsed_id)

            # Apply collapse
            obj.in_superposition = False
            obj.collapsed_state_id = collapsed_id
            obj.coherence = 0.0
            obj.collapse_count += 1
            obj.last_collapsed_at = time.time()

            # Handle entanglement cascade
            cascade_affected: List[str] = []
            for partner_id, ent_type in obj.entanglements.items():
                partner = self._objects.get(partner_id)
                if partner is None or not partner.in_superposition:
                    continue
                # Determine partner's collapsed state based on entanglement type
                link = None
                for l in self._entanglements.values():
                    if (l.object_a == object_id and l.object_b == partner_id) or \
                       (l.object_a == partner_id and l.object_b == object_id):
                        link = l
                        break
                if link is None:
                    continue

                if ent_type == EntanglementType.CORRELATED:
                    # Partner collapses to same state_id (if it exists)
                    if collapsed_id in [s.state_id for s in partner.states]:
                        partner_state_id = collapsed_id
                    else:
                        partner_state_id = random.choice([s.state_id for s in partner.states])
                elif ent_type == EntanglementType.ANTI_CORRELATED:
                    # Partner collapses to different state
                    other_states = [s.state_id for s in partner.states if s.state_id != collapsed_id]
                    partner_state_id = random.choice(other_states) if other_states else \
                        random.choice([s.state_id for s in partner.states])
                elif ent_type == EntanglementType.CONDITIONAL:
                    # Use state mapping
                    partner_state_id = link.state_mapping.get(collapsed_id,
                        random.choice([s.state_id for s in partner.states]))
                else:
                    partner_state_id = random.choice([s.state_id for s in partner.states])

                # Collapse partner
                partner.in_superposition = False
                partner.collapsed_state_id = partner_state_id
                partner.coherence = 0.0
                partner.collapse_count += 1
                partner.last_collapsed_at = time.time()
                cascade_affected.append(partner_id)
                self._stats.total_cascade_collapses += 1

            # Record collapse event
            event = CollapseEvent(
                event_id=f"col_{object_id}_{int(time.time() * 1000)}",
                object_id=object_id,
                observation_type=obs_type,
                collapsed_state_id=collapsed_id,
                collapsed_label=collapsed_state.label,
                prior_probabilities=prior_probs,
                timestamp=time.time(),
                observer=observer,
                cascade_affected=cascade_affected,
            )
            self._collapse_history.append(event)
            self._stats.total_collapses += 1
            self._stats.total_observations += 1

            return {
                "event_id": event.event_id,
                "object_id": object_id,
                "observation_type": obs_type.value,
                "collapsed_state_id": collapsed_id,
                "collapsed_label": collapsed_state.label,
                "collapsed_properties": collapsed_state.properties,
                "prior_probabilities": prior_probs,
                "cascade_affected": cascade_affected,
                "observer": observer,
            }

    def reset_superposition(self, object_id: str) -> Dict[str, Any]:
        """Reset an object back into superposition (re-superpose)."""
        with self._lock:
            obj = self._objects.get(object_id)
            if obj is None:
                return {"error": f"Object not found: {object_id}"}
            # Re-normalize probabilities
            n = len(obj.states)
            for s in obj.states:
                s.probability = round(1.0 / n, 6)
                s.amplitude = round(math.sqrt(1.0 / n), 6)
            obj.in_superposition = True
            obj.collapsed_state_id = None
            obj.coherence = 1.0
            return self._object_to_dict(obj)

    # -------------------------------------------------------------------------
    # Phase Implementations
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single quantum state cycle.

        Phases: SUPERPOSE -> ENTANGLE -> EVOLVE -> DECOHERE -> COLLAPSE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: SUPERPOSE
            phase = QuantumPhase.SUPERPOSE
            superpose_info = self._superpose_phase()

            # Phase 2: ENTANGLE
            phase = QuantumPhase.ENTANGLE
            entangle_info = self._entangle_phase()

            # Phase 3: EVOLVE
            phase = QuantumPhase.EVOLVE
            evolve_info = self._evolve_phase()

            # Phase 4: DECOHERE
            phase = QuantumPhase.DECOHERE
            decohere_info = self._decohere_phase()

            # Phase 5: COLLAPSE
            phase = QuantumPhase.COLLAPSE
            collapse_info = self._collapse_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_stats()

            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "superpose": superpose_info,
                "entangle": entangle_info,
                "evolve": evolve_info,
                "decohere": decohere_info,
                "collapse": collapse_info,
                "total_objects": len(self._objects),
                "in_superposition": sum(1 for o in self._objects.values() if o.in_superposition),
                "total_entanglements": len(self._entanglements),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _superpose_phase(self) -> Dict[str, Any]:
        """Phase 1: Objects maintain or refresh their superposition."""
        refreshed = 0
        for obj in self._objects.values():
            if obj.in_superposition:
                # Slight probability fluctuation
                for s in obj.states:
                    if s.probability > self.MIN_STATE_PROBABILITY:
                        fluctuation = random.uniform(-0.01, 0.01)
                        s.probability = max(0.0, s.probability + fluctuation)
                        refreshed += 1
                # Re-normalize
                self._normalize_probabilities(obj)
        return {"states_refreshed": refreshed}

    def _entangle_phase(self) -> Dict[str, Any]:
        """Phase 2: Compatible objects may become entangled."""
        new_entanglements = 0
        superposed_objects = [
            obj for obj in self._objects.values() if obj.in_superposition
        ]
        if len(superposed_objects) < 2:
            return {"new_entanglements": 0}

        # Randomly attempt to entangle pairs
        attempts = min(5, len(superposed_objects))
        for _ in range(attempts):
            if random.random() > self.ENTANGLEMENT_FORMATION_CHANCE:
                continue
            obj_a = random.choice(superposed_objects)
            obj_b = random.choice(superposed_objects)
            if obj_a.object_id == obj_b.object_id:
                continue
            if obj_b.object_id in obj_a.entanglements:
                continue
            if len(obj_a.entanglements) >= self.MAX_ENTANGLEMENTS_PER_OBJECT or \
               len(obj_b.entanglements) >= self.MAX_ENTANGLEMENTS_PER_OBJECT:
                continue
            # Only entangle objects of the same type
            if obj_a.object_type != obj_b.object_type:
                continue
            link_type = random.choice(list(EntanglementType)).value
            result = self.entangle_objects(obj_a.object_id, obj_b.object_id, link_type)
            if "error" not in result:
                new_entanglements += 1

        return {"new_entanglements": new_entanglements}

    def _evolve_phase(self) -> Dict[str, Any]:
        """Phase 3: Wave functions evolve (probabilities shift)."""
        evolved = 0
        tunneled = 0
        for obj in self._objects.values():
            if not obj.in_superposition:
                continue
            # Evolve probabilities
            if len(obj.states) > 1:
                # Shift probability mass between states
                shifts = [random.gauss(0, self.EVOLUTION_RATE) for _ in obj.states]
                for i, s in enumerate(obj.states):
                    s.probability = max(0.0, s.probability + shifts[i])
                self._normalize_probabilities(obj)
                evolved += 1

            # Quantum tunneling: small chance to swap dominant state
            if random.random() < self.TUNNELING_CHANCE and len(obj.states) > 1:
                # Find dominant and weakest state
                sorted_states = sorted(obj.states, key=lambda s: s.probability)
                weakest = sorted_states[0]
                dominant = sorted_states[-1]
                # Swap some probability mass
                swap = weakest.probability * 0.5
                weakest.probability += swap
                dominant.probability -= swap
                self._normalize_probabilities(obj)
                tunneled += 1

        self._stats.total_tunneling_events += tunneled
        return {"objects_evolved": evolved, "tunneling_events": tunneled}

    def _decohere_phase(self) -> Dict[str, Any]:
        """Phase 4: Natural decoherence moves objects toward definite states."""
        decohered = 0
        auto_collapsed = 0
        for obj in self._objects.values():
            if not obj.in_superposition:
                continue
            # Reduce coherence
            obj.coherence = max(0.0, obj.coherence - obj.decoherence_rate)
            decohered += 1
            # If coherence drops below threshold, auto-collapse
            if obj.coherence <= self.DECOHERENCE_COLLAPSE_THRESHOLD:
                # Collapse to most probable state
                dominant = max(obj.states, key=lambda s: s.probability)
                obj.in_superposition = False
                obj.collapsed_state_id = dominant.state_id
                obj.coherence = 0.0
                obj.collapse_count += 1
                obj.last_collapsed_at = time.time()
                auto_collapsed += 1
                self._stats.total_collapses += 1

        return {
            "objects_decohered": decohered,
            "auto_collapsed": auto_collapsed,
        }

    def _collapse_phase(self) -> Dict[str, Any]:
        """Phase 5: Process pending observations."""
        collapses = 0
        while self._pending_observations:
            object_id, obs_type, observer = self._pending_observations.popleft()
            result = self.observe(object_id, obs_type.value, observer)
            if "error" not in result:
                collapses += 1
        return {"observations_processed": collapses}

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _normalize_probabilities(self, obj: QuantumObject) -> None:
        """Normalize state probabilities to sum to 1.0."""
        total = sum(s.probability for s in obj.states)
        if total <= 0:
            n = len(obj.states)
            for s in obj.states:
                s.probability = round(1.0 / n, 6)
                s.amplitude = round(math.sqrt(1.0 / n), 6)
        else:
            for s in obj.states:
                s.probability = round(s.probability / total, 6)
                s.amplitude = round(math.sqrt(s.probability), 6)

    def _update_stats(self) -> None:
        """Update aggregate statistics."""
        if not self._objects:
            return
        total_coherence = sum(o.coherence for o in self._objects.values())
        superposed = sum(1 for o in self._objects.values() if o.in_superposition)
        n = len(self._objects)
        self._stats.avg_coherence = round(total_coherence / n, 4)
        self._stats.superposition_ratio = round(superposed / n, 4)

    def queue_observation(self, object_id: str, observation_type: str,
                          observer: str = "player") -> Dict[str, Any]:
        """Queue an observation for the next collapse phase."""
        with self._lock:
            try:
                obs_type = ObservationType(observation_type)
            except ValueError:
                return {"error": f"Unknown observation type: {observation_type}"}
            if object_id not in self._objects:
                return {"error": f"Object not found: {object_id}"}
            self._pending_observations.append((object_id, obs_type, observer))
            return {"queued": True, "object_id": object_id,
                    "observation_type": obs_type.value, "observer": observer}

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "total_objects": len(self._objects),
                "in_superposition": sum(1 for o in self._objects.values() if o.in_superposition),
                "collapsed": sum(1 for o in self._objects.values() if not o.in_superposition),
                "total_entanglements": len(self._entanglements),
                "stats": self._stats_to_dict(),
            }

    def list_collapse_events(self, object_id: Optional[str] = None,
                             limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            events = list(self._collapse_history)
            if object_id:
                events = [e for e in events if e.object_id == object_id]
            events.sort(key=lambda e: e.timestamp, reverse=True)
            return [self._collapse_to_dict(e) for e in events[:limit]]

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles and optionally seed random data."""
        with self._lock:
            # Seed sample objects if empty
            if not self._objects:
                sample_objects = [
                    ("q_chest_1", "chest", [
                        {"state_id": "empty", "label": "Empty", "probability": 0.3},
                        {"state_id": "gold", "label": "Gold Filled", "probability": 0.4},
                        {"state_id": "trap", "label": "Trapped", "probability": 0.3},
                    ]),
                    ("q_chest_2", "chest", [
                        {"state_id": "empty", "label": "Empty", "probability": 0.3},
                        {"state_id": "gold", "label": "Gold Filled", "probability": 0.4},
                        {"state_id": "trap", "label": "Trapped", "probability": 0.3},
                    ]),
                    ("q_door_1", "door", [
                        {"state_id": "locked", "label": "Locked", "probability": 0.4},
                        {"state_id": "unlocked", "label": "Unlocked", "probability": 0.4},
                        {"state_id": "broken", "label": "Broken", "probability": 0.2},
                    ]),
                    ("q_npc_1", "npc", [
                        {"state_id": "friendly", "label": "Friendly", "probability": 0.5},
                        {"state_id": "hostile", "label": "Hostile", "probability": 0.3},
                        {"state_id": "neutral", "label": "Neutral", "probability": 0.2},
                    ]),
                ]
                for oid, otype, states in sample_objects:
                    self.register_object(oid, otype, states)
                # Entangle the two chests
                self.entangle_objects("q_chest_1", "q_chest_2", "anti")

            for _ in range(cycles):
                # Occasionally observe a random object
                if self._objects and random.random() < 0.3:
                    superposed = [o for o in self._objects.values() if o.in_superposition]
                    if superposed:
                        target = random.choice(superposed)
                        self.observe(target.object_id, "agent_perceive", "sim_agent")
                self.run_cycle()

            return {
                "cycles_run": cycles,
                "final_status": self.get_status(),
                "final_stats": self._stats_to_dict(),
            }

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            count = len(self._objects)
            ent_count = len(self._entanglements)
            self._objects.clear()
            self._entanglements.clear()
            self._pending_observations.clear()
            self._collapse_history.clear()
            self._stats = QuantumStats()
            self._cycle_count = 0
            self._active = False
            return {"reset": True, "cleared_objects": count,
                    "cleared_entanglements": ent_count}

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _object_to_dict(self, obj: QuantumObject) -> Dict[str, Any]:
        return {
            "object_id": obj.object_id,
            "object_type": obj.object_type,
            "states": [
                {
                    "state_id": s.state_id,
                    "label": s.label,
                    "amplitude": round(s.amplitude, 6),
                    "probability": round(s.probability, 6),
                    "properties": s.properties,
                }
                for s in obj.states
            ],
            "collapsed_state_id": obj.collapsed_state_id,
            "in_superposition": obj.in_superposition,
            "entanglements": {k: v.value for k, v in obj.entanglements.items()},
            "coherence": round(obj.coherence, 4),
            "decoherence_rate": obj.decoherence_rate,
            "collapse_count": obj.collapse_count,
            "created_at": obj.created_at,
            "last_collapsed_at": obj.last_collapsed_at,
            "last_evolved_at": obj.last_evolved_at,
        }

    def _collapse_to_dict(self, e: CollapseEvent) -> Dict[str, Any]:
        return {
            "event_id": e.event_id,
            "object_id": e.object_id,
            "observation_type": e.observation_type.value,
            "collapsed_state_id": e.collapsed_state_id,
            "collapsed_label": e.collapsed_label,
            "prior_probabilities": {k: round(v, 6) for k, v in e.prior_probabilities.items()},
            "timestamp": e.timestamp,
            "observer": e.observer,
            "cascade_affected": e.cascade_affected,
        }

    def _stats_to_dict(self) -> Dict[str, Any]:
        return {
            "total_objects": self._stats.total_objects,
            "total_superpositions": self._stats.total_superpositions,
            "total_collapses": self._stats.total_collapses,
            "total_entanglements": self._stats.total_entanglements,
            "total_observations": self._stats.total_observations,
            "total_cascade_collapses": self._stats.total_cascade_collapses,
            "total_tunneling_events": self._stats.total_tunneling_events,
            "avg_coherence": self._stats.avg_coherence,
            "superposition_ratio": self._stats.superposition_ratio,
            "last_cycle_time_ms": self._stats.last_cycle_time_ms,
            "active": self._stats.active,
        }
