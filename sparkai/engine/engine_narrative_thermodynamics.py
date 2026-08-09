"""
SparkLabs Engine - Narrative Thermodynamics"""

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

class ThermoPhase(Enum):
    """Phases of the narrative thermodynamics cycle."""
    RADIATE = "radiate"     # story sources radiate narrative energy
    CONDUCT = "conduct"     # adjacent elements conduct energy
    CONVECT = "convect"     # genre currents carry energy in bulk
    ENTROPY = "entropy"     # stories lose specificity as they spread
    PHASE = "phase"         # energy thresholds trigger phase transitions


class NarrativeGenre(Enum):
    """Genres that function as states of matter for narrative energy."""
    COMEDY = "comedy"           # light, expansive (gas-like)
    DRAMA = "drama"             # moderate, structured (liquid-like)
    TRAGEDY = "tragedy"         # heavy, compressed (solid-like)
    MYSTERY = "mystery"         # diffuse, searching (plasma-like)
    HORROR = "horror"           # dense, contracting (black-hole-like)
    ADVENTURE = "adventure"     # energetic, flowing (fluid-like)
    ROMANCE = "romance"         # warm, circulating (thermal-like)
    EPIQUE = "epic"            # massive, gravitating (stellar-like)


class EnergyType(Enum):
    """Types of narrative energy."""
    TENSION = "tension"         # conflict-driven energy
    EMOTION = "emotion"         # feeling-driven energy
    MYSTERY_ENERGY = "mystery"  # unknown-driven energy
    ACTION = "action"           # motion-driven energy
    REVELATION = "revelation"   # truth-driven energy
    BONDING = "bonding"         # connection-driven energy
    DREAD = "dread"             # fear-driven energy
    HOPE = "hope"               # aspiration-driven energy


class StoryState(Enum):
    """State of a story node in the thermodynamic system."""
    DORMANT = "dormant"         # minimal energy
    WARMING = "warming"         # gaining energy
    ACTIVE = "active"           # actively radiating
    INTENSE = "intense"         # high energy, near phase transition
    TRANSITIONING = "transitioning"  # undergoing phase transition
    DISSIPATED = "dissipated"   # energy has dispersed
    CRYSTALLIZED = "crystallized"    # permanently locked into a form


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class StoryNode:
    """A node in the narrative thermodynamic system."""
    node_id: str
    label: str
    genre: NarrativeGenre
    energy: float = 0.3             # total narrative energy (0.0-1.0)
    temperature: float = 0.3        # narrative heat (0.0-1.0)
    entropy: float = 0.1            # how dispersed/generalized (0.0-1.0)
    specificity: float = 0.9        # how specific/detailed (0.0-1.0)
    state: StoryState = StoryState.DORMANT
    energy_profile: Dict[str, float] = field(default_factory=dict)  # EnergyType -> amount
    x: float = 0.5                  # position in narrative space
    y: float = 0.5
    neighbors: Set[str] = field(default_factory=set)
    radiation_rate: float = 0.1     # how fast it radiates energy
    conduction_rate: float = 0.15   # how fast it conducts to neighbors
    created_at: float = field(default_factory=time.time)
    last_phase_transition: Optional[str] = None  # previous genre
    phase_transition_count: int = 0


@dataclass
class GenreCurrent:
    """A convection current carrying narrative energy in a genre direction."""
    current_id: str
    source_genre: NarrativeGenre
    target_genre: NarrativeGenre
    strength: float
    direction_x: float
    direction_y: float
    created_at: float = field(default_factory=time.time)


@dataclass
class PhaseTransition:
    """Record of a narrative phase transition."""
    transition_id: str
    node_id: str
    from_genre: NarrativeGenre
    to_genre: NarrativeGenre
    trigger_energy: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class EntropyEvent:
    """Record of a story losing specificity."""
    event_id: str
    node_id: str
    specificity_lost: float
    entropy_gained: float
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# Narrative Thermodynamics Engine
# =============================================================================

class EngineNarrativeThermodynamics:
    """
    Thread-safe singleton orchestrating narrative thermodynamics.

    Usage:
        thermo = EngineNarrativeThermodynamics.get_instance()
        thermo.add_story("s_battle", "Battle of the Gate",
                        NarrativeGenre.ADVENTURE, energy=0.7, temp=0.8)
        thermo.add_story("s_funeral", "Hero's Funeral",
                        NarrativeGenre.TRAGEDY, energy=0.5, temp=0.3)
        thermo.link_stories("s_battle", "s_funeral")
        thermo.cycle()
    """

    _instance: Optional["EngineNarrativeThermodynamics"] = None
    _lock = threading.RLock()

    # Genre transition thresholds (energy level needed to transition)
    _GENRE_THRESHOLDS = {
        NarrativeGenre.COMEDY: 0.3,
        NarrativeGenre.DRAMA: 0.5,
        NarrativeGenre.ADVENTURE: 0.6,
        NarrativeGenre.ROMANCE: 0.55,
        NarrativeGenre.MYSTERY: 0.65,
        NarrativeGenre.EPIQUE: 0.75,
        NarrativeGenre.TRAGEDY: 0.7,
        NarrativeGenre.HORROR: 0.8,
    }

    # Genre energy affinity (which energy types each genre amplifies)
    _GENRE_ENERGY_AFFINITY = {
        NarrativeGenre.COMEDY: {EnergyType.EMOTION: 0.8, EnergyType.BONDING: 0.6},
        NarrativeGenre.DRAMA: {EnergyType.EMOTION: 0.9, EnergyType.TENSION: 0.7},
        NarrativeGenre.TRAGEDY: {EnergyType.EMOTION: 0.95, EnergyType.DREAD: 0.6},
        NarrativeGenre.MYSTERY: {EnergyType.MYSTERY_ENERGY: 0.95, EnergyType.REVELATION: 0.7},
        NarrativeGenre.HORROR: {EnergyType.DREAD: 0.95, EnergyType.TENSION: 0.8},
        NarrativeGenre.ADVENTURE: {EnergyType.ACTION: 0.9, EnergyType.TENSION: 0.6},
        NarrativeGenre.ROMANCE: {EnergyType.BONDING: 0.9, EnergyType.EMOTION: 0.8},
        NarrativeGenre.EPIQUE: {EnergyType.ACTION: 0.8, EnergyType.HOPE: 0.7, EnergyType.REVELATION: 0.6},
    }

    def __init__(self) -> None:
        self._nodes: Dict[str, StoryNode] = {}
        self._currents: Deque[GenreCurrent] = deque(maxlen=50)
        self._transitions: Deque[PhaseTransition] = deque(maxlen=100)
        self._entropy_events: Deque[EntropyEvent] = deque(maxlen=100)
        self._phase: ThermoPhase = ThermoPhase.RADIATE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=300)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {
            "total_nodes": 0,
            "total_edges": 0,
            "total_currents": 0,
            "total_transitions": 0,
            "total_entropy_events": 0,
            "avg_energy": 0.0,
            "avg_temperature": 0.0,
            "avg_entropy": 0.0,
            "avg_specificity": 0.0,
            "dormant_nodes": 0,
            "active_nodes": 0,
            "intense_nodes": 0,
            "crystallized_nodes": 0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineNarrativeThermodynamics":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Node Management
    # -------------------------------------------------------------------------

    def add_story(
        self,
        node_id: str,
        label: str,
        genre: NarrativeGenre,
        energy: float = 0.3,
        temperature: float = 0.3,
        x: float = 0.5,
        y: float = 0.5,
        energy_profile: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Add a story node to the thermodynamic system."""
        with self._global_lock:
            if node_id in self._nodes:
                return {"error": f"Story already exists: {node_id}"}
            # parse energy profile
            profile: Dict[str, float] = {}
            if energy_profile:
                for k, v in energy_profile.items():
                    try:
                        etype = EnergyType(k)
                        profile[etype.value] = max(0.0, min(1.0, v))
                    except ValueError:
                        pass
            # if no profile, create one based on genre affinity
            if not profile:
                affinity = self._GENRE_ENERGY_AFFINITY.get(genre, {})
                for etype, weight in affinity.items():
                    profile[etype.value] = energy * weight
            node = StoryNode(
                node_id=node_id,
                label=label,
                genre=genre,
                energy=max(0.0, min(1.0, energy)),
                temperature=max(0.0, min(1.0, temperature)),
                x=max(0.0, min(1.0, x)),
                y=max(0.0, min(1.0, y)),
                energy_profile=profile,
            )
            node.state = self._compute_state(node)
            self._nodes[node_id] = node
            self._record_event("story_added", {
                "node_id": node_id, "genre": genre.value,
                "energy": node.energy,
            })
            self._update_stats()
            return {
                "node_id": node_id, "label": label,
                "genre": genre.value, "energy": node.energy,
                "temperature": node.temperature,
                "state": node.state.value,
            }

    def remove_story(self, node_id: str) -> Dict[str, Any]:
        """Remove a story node."""
        with self._global_lock:
            if node_id not in self._nodes:
                return {"error": f"Story not found: {node_id}"}
            n = self._nodes.pop(node_id)
            # remove from neighbors
            for other in self._nodes.values():
                other.neighbors.discard(node_id)
            self._update_stats()
            return {"removed": node_id, "label": n.label}

    def link_stories(self, node_a: str, node_b: str) -> Dict[str, Any]:
        """Link two stories as neighbors for conduction."""
        with self._global_lock:
            if node_a not in self._nodes:
                return {"error": f"Story not found: {node_a}"}
            if node_b not in self._nodes:
                return {"error": f"Story not found: {node_b}"}
            self._nodes[node_a].neighbors.add(node_b)
            self._nodes[node_b].neighbors.add(node_a)
            self._update_stats()
            return {"linked": [node_a, node_b]}

    def unlink_stories(self, node_a: str, node_b: str) -> Dict[str, Any]:
        """Unlink two stories."""
        with self._global_lock:
            if node_a in self._nodes:
                self._nodes[node_a].neighbors.discard(node_b)
            if node_b in self._nodes:
                self._nodes[node_b].neighbors.discard(node_a)
            self._update_stats()
            return {"unlinked": [node_a, node_b]}

    def inject_energy(
        self, node_id: str, energy_type: str, amount: float,
    ) -> Dict[str, Any]:
        """Inject narrative energy into a story node."""
        with self._global_lock:
            n = self._nodes.get(node_id)
            if n is None:
                return {"error": f"Story not found: {node_id}"}
            try:
                etype = EnergyType(energy_type)
            except ValueError:
                return {"error": f"Invalid energy type: {energy_type}"}
            amount = max(0.0, min(1.0, amount))
            n.energy_profile[etype.value] = n.energy_profile.get(etype.value, 0.0) + amount
            n.energy = min(1.0, n.energy + amount * 0.3)
            n.temperature = min(1.0, n.temperature + amount * 0.2)
            n.state = self._compute_state(n)
            self._record_event("energy_injected", {
                "node_id": node_id, "energy_type": etype.value, "amount": amount,
            })
            return {
                "node_id": node_id,
                "energy_type": etype.value,
                "total": n.energy_profile[etype.value],
                "node_energy": n.energy,
                "state": n.state.value,
            }

    # -------------------------------------------------------------------------
    # Phase: RADIATE - story sources radiate energy outward
    # -------------------------------------------------------------------------

    def _phase_radiate(self) -> Dict[str, Any]:
        """Story nodes radiate narrative energy to nearby nodes."""
        radiated = 0
        node_list = list(self._nodes.values())
        for source in node_list:
            if source.state in (StoryState.DISSIPATED, StoryState.CRYSTALLIZED):
                continue
            if source.energy < 0.2:
                continue
            # radiate to nearby nodes (based on position distance)
            for target in node_list:
                if target.node_id == source.node_id:
                    continue
                if target.state in (StoryState.DISSIPATED, StoryState.CRYSTALLIZED):
                    continue
                dist = math.sqrt(
                    (source.x - target.x) ** 2 + (source.y - target.y) ** 2
                )
                if dist > 0.3:
                    continue  # too far for radiation
                # radiation falls off with distance
                radiation = source.energy * source.radiation_rate * (1.0 - dist / 0.3)
                # only radiate compatible energy types
                source_affinity = self._GENRE_ENERGY_AFFINITY.get(source.genre, {})
                target_affinity = self._GENRE_ENERGY_AFFINITY.get(target.genre, {})
                for etype_val, amount in source.energy_profile.items():
                    try:
                        etype = EnergyType(etype_val)
                    except ValueError:
                        continue
                    target_weight = target_affinity.get(etype, 0.3)
                    transferred = radiation * amount * target_weight * 0.3
                    if transferred > 0.01:
                        target.energy_profile[etype_val] = min(
                            1.0, target.energy_profile.get(etype_val, 0.0) + transferred
                        )
                        target.energy = min(1.0, target.energy + transferred * 0.2)
                        target.temperature = min(
                            1.0, target.temperature + transferred * 0.1
                        )
                        radiated += 1
            # source loses a small amount of energy from radiation
            source.energy = max(0.0, source.energy - source.energy * 0.02)
        # update states
        for n in self._nodes.values():
            n.state = self._compute_state(n)
        return {"radiation_events": radiated}

    # -------------------------------------------------------------------------
    # Phase: CONDUCT - adjacent elements conduct energy directly
    # -------------------------------------------------------------------------

    def _phase_conduct(self) -> Dict[str, Any]:
        """Linked stories conduct energy between each other."""
        conducted = 0
        for n in self._nodes.values():
            if n.state in (StoryState.DISSIPATED, StoryState.CRYSTALLIZED):
                continue
            for neighbor_id in n.neighbors:
                neighbor = self._nodes.get(neighbor_id)
                if neighbor is None:
                    continue
                if neighbor.state in (StoryState.DISSIPATED, StoryState.CRYSTALLIZED):
                    continue
                # conduction equalizes temperature between neighbors
                temp_diff = n.temperature - neighbor.temperature
                if abs(temp_diff) < 0.01:
                    continue
                transfer = temp_diff * n.conduction_rate * 0.5
                n.temperature -= transfer
                neighbor.temperature += transfer
                # also conduct some energy
                energy_transfer = (n.energy - neighbor.energy) * n.conduction_rate * 0.2
                n.energy -= energy_transfer
                neighbor.energy += energy_transfer
                # conduct energy profile components
                for etype_val in list(n.energy_profile.keys()):
                    n_amount = n.energy_profile.get(etype_val, 0.0)
                    nb_amount = neighbor.energy_profile.get(etype_val, 0.0)
                    diff = n_amount - nb_amount
                    if abs(diff) > 0.01:
                        cond = diff * n.conduction_rate * 0.3
                        n.energy_profile[etype_val] = n_amount - cond
                        neighbor.energy_profile[etype_val] = nb_amount + cond
                        conducted += 1
        for n in self._nodes.values():
            n.state = self._compute_state(n)
        return {"conduction_events": conducted}

    # -------------------------------------------------------------------------
    # Phase: CONVECT - genre currents carry energy in bulk
    # -------------------------------------------------------------------------

    def _phase_convect(self) -> Dict[str, Any]:
        """Genre currents carry narrative energy in bulk flows."""
        currents_created = 0
        # find nodes with high energy that can start a current
        high_energy = [
            n for n in self._nodes.values()
            if n.energy > 0.5 and n.state not in
            (StoryState.DISSIPATED, StoryState.CRYSTALLIZED)
        ]
        for source in high_energy:
            if random.random() > 0.2:
                continue  # not every high-energy node starts a current
            # pick a target genre (different from source)
            other_genres = [g for g in NarrativeGenre if g != source.genre]
            target_genre = random.choice(other_genres)
            # direction toward nearest node of target genre
            target_nodes = [
                n for n in self._nodes.values()
                if n.genre == target_genre and n.node_id != source.node_id
            ]
            if not target_nodes:
                continue
            nearest = min(
                target_nodes,
                key=lambda n: math.sqrt(
                    (n.x - source.x) ** 2 + (n.y - source.y) ** 2
                ),
            )
            dx = nearest.x - source.x
            dy = nearest.y - source.y
            dist = math.sqrt(dx * dx + dy * dy) + 0.01
            current = GenreCurrent(
                current_id=f"c_{source.node_id}_{target_genre.value}_{self._cycle_count}",
                source_genre=source.genre,
                target_genre=target_genre,
                strength=source.energy * 0.3,
                direction_x=dx / dist,
                direction_y=dy / dist,
            )
            self._currents.append(current)
            currents_created += 1
            # carry energy along the current direction
            for n in self._nodes.values():
                if n.node_id == source.node_id:
                    continue
                if n.state in (StoryState.DISSIPATED, StoryState.CRYSTALLIZED):
                    continue
                # check if node is in the current's path
                nx = n.x - source.x
                ny = n.y - source.y
                projection = (nx * current.direction_x + ny * current.direction_y)
                if projection < 0:
                    continue  # behind the source
                # carry some energy
                carried = current.strength * 0.05
                n.energy = min(1.0, n.energy + carried)
                n.temperature = min(1.0, n.temperature + carried * 0.5)
            self._record_event("current_formed", {
                "source": source.node_id,
                "from_genre": source.genre.value,
                "to_genre": target_genre.value,
            })
        for n in self._nodes.values():
            n.state = self._compute_state(n)
        self._stats["total_currents"] = len(self._currents)
        return {"currents_created": currents_created}

    # -------------------------------------------------------------------------
    # Phase: ENTROPY - stories lose specificity as they spread
    # -------------------------------------------------------------------------

    def _phase_entropy(self) -> Dict[str, Any]:
        """Stories lose specificity and gain entropy over time."""
        entropy_events = 0
        for n in self._nodes.values():
            if n.state == StoryState.CRYSTALLIZED:
                continue  # crystallized stories don't lose specificity
            # entropy increases with energy and time
            entropy_gain = n.energy * 0.02 + 0.005
            n.entropy = min(1.0, n.entropy + entropy_gain)
            # specificity decreases as entropy increases
            specificity_loss = entropy_gain * 0.8
            n.specificity = max(0.1, n.specificity - specificity_loss)
            # high-entropy stories dissipate
            if n.entropy > 0.8 and n.state != StoryState.DISSIPATED:
                n.energy *= 0.7
                n.state = StoryState.DISSIPATED
                self._record_event("story_dissipated", {
                    "node_id": n.node_id, "entropy": n.entropy,
                })
            elif n.entropy > 0.05:
                event_id = f"ent_{n.node_id}_{self._cycle_count}"
                self._entropy_events.append(EntropyEvent(
                    event_id=event_id,
                    node_id=n.node_id,
                    specificity_lost=specificity_loss,
                    entropy_gained=entropy_gain,
                ))
                entropy_events += 1
        for n in self._nodes.values():
            if n.state != StoryState.DISSIPATED:
                n.state = self._compute_state(n)
        self._stats["total_entropy_events"] = len(self._entropy_events)
        return {"entropy_events": entropy_events}

    # -------------------------------------------------------------------------
    # Phase: PHASE - energy thresholds trigger phase transitions
    # -------------------------------------------------------------------------

    def _phase_phase(self) -> Dict[str, Any]:
        """Narrative phase transitions when energy crosses thresholds."""
        transitions = 0
        for n in self._nodes.values():
            if n.state in (StoryState.DISSIPATED, StoryState.CRYSTALLIZED):
                continue
            # check if energy exceeds current genre's threshold
            threshold = self._GENRE_THRESHOLDS.get(n.genre, 0.7)
            if n.energy < threshold:
                continue
            # high energy triggers a phase transition to a heavier genre
            genre_progression = {
                NarrativeGenre.COMEDY: [NarrativeGenre.DRAMA, NarrativeGenre.ADVENTURE],
                NarrativeGenre.DRAMA: [NarrativeGenre.TRAGEDY, NarrativeGenre.MYSTERY],
                NarrativeGenre.ADVENTURE: [NarrativeGenre.EPIQUE, NarrativeGenre.DRAMA],
                NarrativeGenre.ROMANCE: [NarrativeGenre.DRAMA, NarrativeGenre.TRAGEDY],
                NarrativeGenre.MYSTERY: [NarrativeGenre.HORROR, NarrativeGenre.DRAMA],
                NarrativeGenre.TRAGEDY: [NarrativeGenre.HORROR, NarrativeGenre.EPIQUE],
                NarrativeGenre.HORROR: [NarrativeGenre.EPIQUE, NarrativeGenre.TRAGEDY],
                NarrativeGenre.EPIQUE: [NarrativeGenre.TRAGEDY, NarrativeGenre.HORROR],
            }
            candidates = genre_progression.get(n.genre, [NarrativeGenre.DRAMA])
            # pick the candidate with highest energy affinity
            best = max(
                candidates,
                key=lambda g: sum(
                    self._GENRE_ENERGY_AFFINITY.get(g, {}).get(
                        EnergyType(k), 0.0
                    ) * v
                    for k, v in n.energy_profile.items()
                ),
            )
            old_genre = n.genre
            n.genre = best
            n.last_phase_transition = old_genre.value
            n.phase_transition_count += 1
            n.state = StoryState.TRANSITIONING
            # energy drops after transition (like releasing heat)
            n.energy *= 0.6
            n.temperature *= 0.5
            transition = PhaseTransition(
                transition_id=f"pt_{n.node_id}_{self._cycle_count}",
                node_id=n.node_id,
                from_genre=old_genre,
                to_genre=best,
                trigger_energy=n.energy,
            )
            self._transitions.append(transition)
            transitions += 1
            self._record_event("phase_transition", {
                "node_id": n.node_id,
                "from": old_genre.value, "to": best.value,
            })
            # very high transition count leads to crystallization
            if n.phase_transition_count >= 3:
                n.state = StoryState.CRYSTALLIZED
                self._record_event("story_crystallized", {
                    "node_id": n.node_id,
                    "genre": n.genre.value,
                })
        for n in self._nodes.values():
            if n.state != StoryState.TRANSITIONING:
                n.state = self._compute_state(n)
            elif n.energy < 0.3:
                n.state = self._compute_state(n)
        self._stats["total_transitions"] = len(self._transitions)
        return {"phase_transitions": transitions}

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single narrative thermodynamics cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = ThermoPhase.RADIATE
            phase_outputs["radiate"] = self._phase_radiate()
            self._phase = ThermoPhase.CONDUCT
            phase_outputs["conduct"] = self._phase_conduct()
            self._phase = ThermoPhase.CONVECT
            phase_outputs["convect"] = self._phase_convect()
            self._phase = ThermoPhase.ENTROPY
            phase_outputs["entropy"] = self._phase_entropy()
            self._phase = ThermoPhase.PHASE
            phase_outputs["phase"] = self._phase_phase()
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

    def get_story(self, node_id: str) -> Dict[str, Any]:
        """Get a story node's state."""
        with self._global_lock:
            n = self._nodes.get(node_id)
            if n is None:
                return {"error": f"Story not found: {node_id}"}
            return self._node_to_dict(n)

    def get_all_stories(self) -> List[Dict[str, Any]]:
        """Get all story nodes."""
        with self._global_lock:
            return [self._node_to_dict(n) for n in self._nodes.values()]

    def get_transitions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent phase transitions."""
        with self._global_lock:
            recent = list(self._transitions)[-limit:]
            return [
                {
                    "transition_id": t.transition_id,
                    "node_id": t.node_id,
                    "from_genre": t.from_genre.value,
                    "to_genre": t.to_genre.value,
                    "trigger_energy": t.trigger_energy,
                }
                for t in recent
            ]

    def get_currents(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get active genre currents."""
        with self._global_lock:
            recent = list(self._currents)[-limit:]
            return [
                {
                    "current_id": c.current_id,
                    "source_genre": c.source_genre.value,
                    "target_genre": c.target_genre.value,
                    "strength": c.strength,
                }
                for c in recent
            ]

    def get_entropy_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent entropy events."""
        with self._global_lock:
            recent = list(self._entropy_events)[-limit:]
            return [
                {
                    "event_id": e.event_id,
                    "node_id": e.node_id,
                    "specificity_lost": e.specificity_lost,
                    "entropy_gained": e.entropy_gained,
                }
                for e in recent
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get thermodynamics status."""
        with self._global_lock:
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "stats": dict(self._stats),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the entire system."""
        with self._global_lock:
            count = len(self._nodes)
            self._nodes.clear()
            self._currents.clear()
            self._transitions.clear()
            self._entropy_events.clear()
            self._events_log.clear()
            self._cycle_count = 0
            self._phase = ThermoPhase.RADIATE
            self._stats = {
                "total_nodes": 0,
                "total_edges": 0,
                "total_currents": 0,
                "total_transitions": 0,
                "total_entropy_events": 0,
                "avg_energy": 0.0,
                "avg_temperature": 0.0,
                "avg_entropy": 0.0,
                "avg_specificity": 0.0,
                "dormant_nodes": 0,
                "active_nodes": 0,
                "intense_nodes": 0,
                "crystallized_nodes": 0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "stories_removed": count}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _compute_state(self, n: StoryNode) -> StoryState:
        """Compute the state of a story node based on its energy."""
        if n.state == StoryState.CRYSTALLIZED:
            return StoryState.CRYSTALLIZED
        if n.energy < 0.15:
            return StoryState.DORMANT
        if n.energy < 0.35:
            return StoryState.WARMING
        if n.energy < 0.6:
            return StoryState.ACTIVE
        if n.energy < 0.8:
            return StoryState.INTENSE
        return StoryState.INTENSE

    def _node_to_dict(self, n: StoryNode) -> Dict[str, Any]:
        """Convert a story node to a dictionary."""
        return {
            "node_id": n.node_id,
            "label": n.label,
            "genre": n.genre.value,
            "energy": n.energy,
            "temperature": n.temperature,
            "entropy": n.entropy,
            "specificity": n.specificity,
            "state": n.state.value,
            "energy_profile": dict(n.energy_profile),
            "x": n.x,
            "y": n.y,
            "neighbors": list(n.neighbors),
            "phase_transition_count": n.phase_transition_count,
            "last_phase_transition": n.last_phase_transition,
        }

    def _update_stats(self) -> None:
        """Update global stats."""
        total_energy = 0.0
        total_temp = 0.0
        total_entropy = 0.0
        total_spec = 0.0
        total_edges = 0
        dormant = 0
        active = 0
        intense = 0
        crystallized = 0
        for n in self._nodes.values():
            total_energy += n.energy
            total_temp += n.temperature
            total_entropy += n.entropy
            total_spec += n.specificity
            total_edges += len(n.neighbors)
            if n.state == StoryState.DORMANT:
                dormant += 1
            elif n.state in (StoryState.ACTIVE, StoryState.WARMING):
                active += 1
            elif n.state == StoryState.INTENSE:
                intense += 1
            elif n.state == StoryState.CRYSTALLIZED:
                crystallized += 1
        self._stats["total_nodes"] = len(self._nodes)
        self._stats["total_edges"] = total_edges // 2  # each edge counted twice
        self._stats["dormant_nodes"] = dormant
        self._stats["active_nodes"] = active
        self._stats["intense_nodes"] = intense
        self._stats["crystallized_nodes"] = crystallized
        if self._nodes:
            self._stats["avg_energy"] = total_energy / len(self._nodes)
            self._stats["avg_temperature"] = total_temp / len(self._nodes)
            self._stats["avg_entropy"] = total_entropy / len(self._nodes)
            self._stats["avg_specificity"] = total_spec / len(self._nodes)

    def _record_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Record an event in the log."""
        self._events_log.append({
            "event_type": event_type,
            "data": data,
            "cycle": self._cycle_count,
            "timestamp": time.time(),
        })
