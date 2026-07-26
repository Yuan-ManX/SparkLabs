"""
SparkLabs Agent - Memory Crystal Lattice

The AgentMemoryCrystalLattice models agent memory as a growing crystal
lattice. Rather than treating memories as static records that are simply
stored and retrieved, it treats them as crystalline structures that
nucleate from experience, grow along crystallographic axes, anneal under
reflection, fracture under contradictory stress, and recrystallize into
new stable forms.

This crystalline metaphor captures how memory actually works in minds:
memories do not sit unchanged in storage. They grow richer each time they
are recalled (growth along axes). They settle and stabilize during rest
(annealing). They crack when conflicting evidence appears (fracture).
And from the fragments, new integrated understandings form
(recrystallization). Two related memories can twin together, and clusters
of crystals develop grain boundaries that define memory neighborhoods.

Core concepts:
  - SEED        : a nucleation site where a memory crystal begins
  - AXIS        : a crystallographic direction along which a memory grows
  - LATTICE     : the structural type determining growth and cleavage
  - COHERENCE   : how well-aligned the crystal's internal structure is
  - STRESS      : accumulated internal tension from contradictions
  - GRAIN       : a neighborhood of related crystals sharing boundaries

Lattice types:
  IONIC        : episodic memories, strong but brittle, cleaves cleanly
  COVALENT     : semantic memories, directional bonds, very stable
  METALLIC     : procedural memories, ductile and malleable, flows
  MOLECULAR    : emotional memories, soft and volatile, sublimates
  COORDINATION : spatial memories, geometric and structured, symmetric

Crystal events:
  SEED_FORMATION    : a new crystal seed nucleates from experience
  CRYSTAL_GROWTH    : a crystal grows along one of its axes
  ANNEALING_RELIEF  : internal stress is relieved through reflection
  CRYSTAL_FRACTURE  : a crystal breaks under accumulated stress
  RECRYSTALLIZATION : fractured fragments reform into a new crystal
  TWINNING          : two related crystals merge into a twinned pair
  GRAIN_BOUNDARY    : a boundary forms between neighboring crystals

Architecture:
  NUCLEATE  ->  GROW   ->  ANNEAL     ->  FRACTURE  ->  RECRYSTALLIZE
  (seeds      (crystals   (internal      (stress       (fragments
   form from    grow along   stress is      causes         recombine
   experience)  their axes)  relieved)      fractures)     into new
                                                            crystals)

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
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class LatticeType(Enum):
    """Structural types of memory crystals."""
    IONIC = "ionic"            # episodic, strong but brittle
    COVALENT = "covalent"      # semantic, directional, stable
    METALLIC = "metallic"      # procedural, ductile, malleable
    MOLECULAR = "molecular"    # emotional, soft, volatile
    COORDINATION = "coordination"  # spatial, geometric, symmetric


class CrystalPhase(Enum):
    """Phases of the memory crystal lattice cycle."""
    NUCLEATE = "nucleate"
    GROW = "grow"
    ANNEAL = "anneal"
    FRACTURE = "fracture"
    RECRYSTALLIZE = "recrystallize"


class CrystalEvent(Enum):
    """Events that occur during the crystal lattice cycle."""
    SEED_FORMATION = "seed_formation"
    CRYSTAL_GROWTH = "crystal_growth"
    ANNEALING_RELIEF = "annealing_relief"
    CRYSTAL_FRACTURE = "crystal_fracture"
    RECRYSTALLIZATION = "recrystallization"
    TWINNING = "twinning"
    GRAIN_BOUNDARY = "grain_boundary"


# =============================================================================
# Default Parameters by Lattice Type
# =============================================================================

# Default coherence for each lattice type
DEFAULT_LATTICE_COHERENCE: Dict[LatticeType, float] = {
    LatticeType.IONIC: 0.7,
    LatticeType.COVALENT: 0.85,
    LatticeType.METALLIC: 0.6,
    LatticeType.MOLECULAR: 0.4,
    LatticeType.COORDINATION: 0.75,
}

# Default growth rate for each lattice type
DEFAULT_LATTICE_GROWTH: Dict[LatticeType, float] = {
    LatticeType.IONIC: 0.08,
    LatticeType.COVALENT: 0.05,
    LatticeType.METALLIC: 0.12,
    LatticeType.MOLECULAR: 0.15,
    LatticeType.COORDINATION: 0.07,
}

# Default stress tolerance for each lattice type
DEFAULT_LATTICE_TOLERANCE: Dict[LatticeType, float] = {
    LatticeType.IONIC: 0.5,        # brittle, low tolerance
    LatticeType.COVALENT: 0.8,     # very tolerant
    LatticeType.METALLIC: 0.7,     # ductile, tolerant
    LatticeType.MOLECULAR: 0.3,    # soft, low tolerance
    LatticeType.COORDINATION: 0.6,
}

# Default number of growth axes for each lattice type
DEFAULT_LATTICE_AXES: Dict[LatticeType, int] = {
    LatticeType.IONIC: 3,
    LatticeType.COVALENT: 4,
    LatticeType.METALLIC: 6,
    LatticeType.MOLECULAR: 2,
    LatticeType.COORDINATION: 5,
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class CrystalSeed:
    """A memory crystal growing in the lattice."""
    crystal_id: str
    label: str
    lattice_type: LatticeType
    # Current size of the crystal (0.0-1.0)
    size: float
    # Target size the crystal is growing toward
    target_size: float
    # Internal coherence / structural alignment (0.0-1.0)
    coherence: float
    # Accumulated internal stress (0.0-1.0)
    stress: float
    # Stress tolerance before fracture
    stress_tolerance: float
    # Number of growth axes
    axis_count: int
    # Growth progress along each axis (list of 0.0-1.0)
    axis_progress: List[float]
    # Whether the crystal has fractured
    fractured: bool = False
    # Whether the crystal has recrystallized from fragments
    recrystallized: bool = False
    # ID of the twin crystal if twinned
    twin_id: Optional[str] = None
    # Emotional charge bound to the memory
    emotional_charge: float = 0.3
    # Number of recall events (growth events)
    recall_count: int = 0
    age_cycles: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class CrystalFragment:
    """A fragment from a fractured crystal awaiting recrystallization."""
    fragment_id: str
    source_crystal_id: str
    lattice_type: LatticeType
    # Size of the fragment relative to original crystal
    size: float
    # Coherence inherited from the parent
    coherence: float
    # Whether the fragment has recombined into a new crystal
    recombined: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class GrainBoundary:
    """A boundary between two neighboring crystals / grain neighborhoods."""
    boundary_id: str
    crystal_a_id: str
    crystal_b_id: str
    # Strength of the boundary connection (0.0-1.0)
    strength: float
    # Mismatch between the two crystal orientations (0.0-1.0)
    mismatch: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class CrystalStats:
    """Aggregate statistics for the crystal lattice."""
    total_crystals: int = 0
    total_fragments: int = 0
    total_boundaries: int = 0
    total_events: int = 0
    total_seeds_formed: int = 0
    total_growth_events: int = 0
    total_fractures: int = 0
    total_recrystallizations: int = 0
    total_twinnings: int = 0
    total_annealings: int = 0
    avg_coherence: float = 0.0
    avg_stress: float = 0.0
    avg_size: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Agent Memory Crystal Lattice
# =============================================================================

class AgentMemoryCrystalLattice:
    """
    Singleton agent subsystem that models memory as a growing crystal
    lattice where experiences nucleate seeds, seeds grow along axes,
    crystals anneal under reflection, fracture under stress, and
    recrystallize from fragments.

    The lattice runs a 5-phase cycle:
      1. NUCLEATE      - New crystal seeds form from experiences
      2. GROW          - Existing crystals grow along their axes
      3. ANNEAL        - Internal stress is relieved through reflection
      4. FRACTURE      - Over-stressed crystals break into fragments
      5. RECRYSTALLIZE - Fragments recombine into new stable crystals

    The crystalline metaphor ensures memory feels alive: memories grow
    richer with recall, stabilize with reflection, and transform through
    contradiction rather than being static records.
    """

    _instance: Optional["AgentMemoryCrystalLattice"] = None
    _instance_lock = threading.Lock()

    # Configuration
    MAX_CRYSTALS = 100
    MAX_FRAGMENTS = 150
    MAX_BOUNDARIES = 200
    MAX_EVENT_HISTORY = 200
    MAX_TWIN_LINKS_PER_CRYSTAL = 4
    # Minimum and maximum size
    MIN_SIZE = 0.0
    MAX_SIZE = 1.0
    # How fast size moves toward target
    SIZE_ADJUSTMENT_RATE = 0.1
    # Natural stress accumulation per cycle (from entropy)
    NATURAL_STRESS_GAIN = 0.02
    # How much stress annealing relieves
    ANNEALING_RELIEF_RATE = 0.15
    # How much coherence annealing restores
    ANNEALING_COHERENCE_GAIN = 0.05
    # Minimum coherence
    MIN_COHERENCE = 0.0
    MAX_COHERENCE = 1.0
    # Minimum and maximum stress
    MIN_STRESS = 0.0
    MAX_STRESS = 1.0
    # Growth per recall event
    GROWTH_PER_RECALL = 0.06
    # Stress added by contradictory recall
    CONTRADICTION_STRESS = 0.2
    # Probability of spontaneous seed formation per cycle
    SPONTANEOUS_SEED_PROBABILITY = 0.15
    # Recrystallization: minimum fragments needed
    RECRYSTALLIZATION_MIN_FRAGMENTS = 2
    # Recrystallization probability per eligible fragment
    RECRYSTALLIZATION_PROBABILITY = 0.4
    # Twinning coherence threshold (crystals must be similar)
    TWINNING_COHERENCE_THRESHOLD = 0.6
    # Twinning probability for eligible pairs
    TWINNING_PROBABILITY = 0.2
    # Grain boundary formation distance (size similarity)
    BOUNDARY_SIMILARITY_THRESHOLD = 0.25

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._crystals: Dict[str, CrystalSeed] = {}
        self._fragments: Deque[CrystalFragment] = deque(maxlen=self.MAX_FRAGMENTS)
        self._boundaries: Deque[GrainBoundary] = deque(maxlen=self.MAX_BOUNDARIES)
        self._event_history: Deque[Dict[str, Any]] = deque(
            maxlen=self.MAX_EVENT_HISTORY
        )
        self._stats = CrystalStats()
        self._cycle_count: int = 0
        self._active: bool = False
        self._fragment_counter: int = 0
        self._boundary_counter: int = 0
        self._event_counter: int = 0

    @classmethod
    def get_instance(cls) -> "AgentMemoryCrystalLattice":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Crystal Management
    # -------------------------------------------------------------------------

    def register_crystal(
        self,
        crystal_id: str,
        label: str,
        lattice_type: str = "ionic",
        size: Optional[float] = None,
        coherence: Optional[float] = None,
        stress_tolerance: Optional[float] = None,
        axis_count: Optional[int] = None,
        emotional_charge: float = 0.3,
    ) -> Dict[str, Any]:
        """Register a new memory crystal in the lattice."""
        with self._lock:
            if crystal_id in self._crystals:
                return {"error": f"Crystal already registered: {crystal_id}"}
            if len(self._crystals) >= self.MAX_CRYSTALS:
                return {"error": "Maximum crystals reached"}

            try:
                ltype = LatticeType(lattice_type)
            except ValueError:
                return {"error": f"Unknown lattice type: {lattice_type}"}

            if size is None:
                size = 0.2
            size = max(self.MIN_SIZE, min(self.MAX_SIZE, float(size)))

            if coherence is None:
                coherence = DEFAULT_LATTICE_COHERENCE.get(ltype, 0.5)
            coherence = max(self.MIN_COHERENCE, min(self.MAX_COHERENCE, float(coherence)))

            if stress_tolerance is None:
                stress_tolerance = DEFAULT_LATTICE_TOLERANCE.get(ltype, 0.5)
            stress_tolerance = max(0.1, min(1.0, float(stress_tolerance)))

            if axis_count is None:
                axis_count = DEFAULT_LATTICE_AXES.get(ltype, 3)
            axis_count = max(1, min(8, int(axis_count)))

            crystal = CrystalSeed(
                crystal_id=crystal_id,
                label=label,
                lattice_type=ltype,
                size=size,
                target_size=size,
                coherence=coherence,
                stress=0.0,
                stress_tolerance=stress_tolerance,
                axis_count=axis_count,
                axis_progress=[size] * axis_count,
                emotional_charge=max(0.0, min(1.0, float(emotional_charge))),
            )
            self._crystals[crystal_id] = crystal

            # Check for grain boundaries with existing crystals
            self._check_grain_boundaries(crystal_id)

            self._stats.total_crystals = len(self._crystals)
            return self._crystal_to_dict(crystal)

    def get_crystal(self, crystal_id: str) -> Dict[str, Any]:
        """Get the state of a specific crystal."""
        with self._lock:
            crystal = self._crystals.get(crystal_id)
            if crystal is None:
                return {"error": f"Crystal not found: {crystal_id}"}
            return self._crystal_to_dict(crystal)

    def list_crystals(
        self, lattice_type: Optional[str] = None, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """List crystals, optionally filtered by lattice type."""
        with self._lock:
            crystals = list(self._crystals.values())
            if lattice_type:
                try:
                    ltype = LatticeType(lattice_type)
                    crystals = [c for c in crystals if c.lattice_type == ltype]
                except ValueError:
                    return []
            crystals = crystals[:limit]
            return [self._crystal_to_dict(c) for c in crystals]

    def remove_crystal(self, crystal_id: str) -> Dict[str, Any]:
        """Remove a crystal from the lattice."""
        with self._lock:
            if crystal_id not in self._crystals:
                return {"removed": False, "crystal_id": crystal_id}
            # Remove boundaries referencing this crystal
            self._boundaries = deque(
                (b for b in self._boundaries
                 if b.crystal_a_id != crystal_id and b.crystal_b_id != crystal_id),
                maxlen=self.MAX_BOUNDARIES,
            )
            del self._crystals[crystal_id]
            self._stats.total_crystals = len(self._crystals)
            self._stats.total_boundaries = len(self._boundaries)
            return {"removed": True, "crystal_id": crystal_id}

    def set_crystal_target_size(
        self, crystal_id: str, target_size: float, description: str = ""
    ) -> Dict[str, Any]:
        """Set the target size a crystal is growing toward."""
        with self._lock:
            crystal = self._crystals.get(crystal_id)
            if crystal is None:
                return {"error": f"Crystal not found: {crystal_id}"}
            target_size = max(self.MIN_SIZE, min(self.MAX_SIZE, float(target_size)))
            crystal.target_size = target_size
            return {
                "crystal_id": crystal_id,
                "target_size": target_size,
                "description": description,
            }

    def recall_crystal(
        self, crystal_id: str, is_contradictory: bool = False
    ) -> Dict[str, Any]:
        """Recall a memory crystal, triggering growth or stress."""
        with self._lock:
            crystal = self._crystals.get(crystal_id)
            if crystal is None:
                return {"error": f"Crystal not found: {crystal_id}"}

            crystal.recall_count += 1
            if is_contradictory:
                crystal.stress = min(
                    self.MAX_STRESS, crystal.stress + self.CONTRADICTION_STRESS
                )
            else:
                # Growth along the least-developed axis
                min_idx = crystal.axis_progress.index(min(crystal.axis_progress))
                crystal.axis_progress[min_idx] = min(
                    self.MAX_SIZE,
                    crystal.axis_progress[min_idx] + self.GROWTH_PER_RECALL,
                )
                crystal.target_size = min(
                    self.MAX_SIZE, crystal.target_size + self.GROWTH_PER_RECALL * 0.5
                )

            return self._crystal_to_dict(crystal)

    # -------------------------------------------------------------------------
    # Fragment Management
    # -------------------------------------------------------------------------

    def list_fragments(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List crystal fragments awaiting recrystallization."""
        with self._lock:
            fragments = list(self._fragments)[:limit]
            return [self._fragment_to_dict(f) for f in fragments]

    def remove_fragment(self, fragment_id: str) -> Dict[str, Any]:
        """Remove a fragment from the pool."""
        with self._lock:
            before = len(self._fragments)
            self._fragments = deque(
                (f for f in self._fragments if f.fragment_id != fragment_id),
                maxlen=self.MAX_FRAGMENTS,
            )
            removed = before - len(self._fragments)
            return {"removed": removed > 0, "fragment_id": fragment_id}

    # -------------------------------------------------------------------------
    # Grain Boundary Management
    # -------------------------------------------------------------------------

    def list_boundaries(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List grain boundaries between crystals."""
        with self._lock:
            boundaries = list(self._boundaries)[:limit]
            return [self._boundary_to_dict(b) for b in boundaries]

    def get_boundary(self, boundary_id: str) -> Dict[str, Any]:
        """Get a specific grain boundary."""
        with self._lock:
            for b in self._boundaries:
                if b.boundary_id == boundary_id:
                    return self._boundary_to_dict(b)
            return {"error": f"Boundary not found: {boundary_id}"}

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single memory crystal lattice cycle.

        Phases: NUCLEATE -> GROW -> ANNEAL -> FRACTURE -> RECRYSTALLIZE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: NUCLEATE - new seeds form from experiences
            nucleate_info = self._nucleate_phase()

            # Phase 2: GROW - existing crystals grow along their axes
            grow_info = self._grow_phase()

            # Phase 3: ANNEAL - internal stress is relieved
            anneal_info = self._anneal_phase()

            # Phase 4: FRACTURE - over-stressed crystals break
            fracture_info = self._fracture_phase()

            # Phase 5: RECRYSTALLIZE - fragments recombine
            recrystallize_info = self._recrystallize_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()

            phase = CrystalPhase.RECRYSTALLIZE
            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "nucleate": nucleate_info,
                "grow": grow_info,
                "anneal": anneal_info,
                "fracture": fracture_info,
                "recrystallize": recrystallize_info,
                "total_crystals": len(self._crystals),
                "total_fragments": len(self._fragments),
                "total_boundaries": len(self._boundaries),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _nucleate_phase(self) -> Dict[str, Any]:
        """Phase 1: New crystal seeds form from experiences."""
        seeds_formed = 0
        # Spontaneous seed formation
        if (len(self._crystals) < self.MAX_CRYSTALS
                and random.random() < self.SPONTANEOUS_SEED_PROBABILITY):
            ltype = random.choice(list(LatticeType))
            seed_id = f"auto_seed_{self._cycle_count}_{seeds_formed}"
            label = f"Spontaneous {ltype.value} memory"
            result = self.register_crystal(
                seed_id, label, ltype.value,
                size=0.15, emotional_charge=random.uniform(0.1, 0.5),
            )
            if "error" not in result:
                seeds_formed += 1
                self._record_event(
                    CrystalEvent.SEED_FORMATION,
                    intensity=0.3,
                    crystal_ids=[seed_id],
                    description=f"Spontaneous {ltype.value} seed nucleated",
                )

        self._stats.total_seeds_formed += seeds_formed
        return {
            "seeds_formed": seeds_formed,
            "spontaneous": seeds_formed,
        }

    def _grow_phase(self) -> Dict[str, Any]:
        """Phase 2: Existing crystals grow along their axes."""
        growth_events = 0
        for crystal in self._crystals.values():
            crystal.age_cycles += 1
            # Grow toward target size
            if crystal.size < crystal.target_size:
                growth = self.SIZE_ADJUSTMENT_RATE * crystal.coherence
                crystal.size = min(crystal.target_size, crystal.size + growth)
                growth_events += 1
            # Grow axes proportionally
            growth_rate = DEFAULT_LATTICE_GROWTH.get(crystal.lattice_type, 0.08)
            for i in range(len(crystal.axis_progress)):
                if crystal.axis_progress[i] < crystal.size:
                    crystal.axis_progress[i] = min(
                        crystal.size,
                        crystal.axis_progress[i] + growth_rate * 0.5,
                    )

        self._stats.total_growth_events += growth_events
        return {"growth_events": growth_events, "crystals_grown": growth_events}

    def _anneal_phase(self) -> Dict[str, Any]:
        """Phase 3: Internal stress is relieved through reflection."""
        annealed = 0
        total_relief = 0.0
        for crystal in self._crystals.values():
            if crystal.stress > 0:
                relief = min(crystal.stress, self.ANNEALING_RELIEF_RATE * crystal.coherence)
                crystal.stress -= relief
                total_relief += relief
                if relief > 0.01:
                    annealed += 1
            # Coherence slowly restores during annealing
            if crystal.coherence < self.MAX_COHERENCE:
                crystal.coherence = min(
                    self.MAX_COHERENCE,
                    crystal.coherence + self.ANNEALING_COHERENCE_GAIN * 0.5,
                )

        if annealed > 0:
            self._record_event(
                CrystalEvent.ANNEALING_RELIEF,
                intensity=min(1.0, total_relief),
                crystal_ids=[],
                description=f"{annealed} crystals annealed, stress relieved: {total_relief:.3f}",
            )
        self._stats.total_annealings += annealed
        return {
            "crystals_annealed": annealed,
            "total_relief": round(total_relief, 4),
        }

    def _fracture_phase(self) -> Dict[str, Any]:
        """Phase 4: Over-stressed crystals break into fragments."""
        fractures = 0
        fragments_created = 0
        to_remove: List[str] = []
        for crystal_id, crystal in self._crystals.items():
            # Natural stress accumulation
            crystal.stress = min(
                self.MAX_STRESS,
                crystal.stress + self.NATURAL_STRESS_GAIN,
            )
            # Check for fracture
            if crystal.stress >= crystal.stress_tolerance and not crystal.fractured:
                crystal.fractured = True
                fractures += 1
                # Create 2-3 fragments
                num_fragments = random.randint(2, 3)
                frag_size = crystal.size / num_fragments
                for _ in range(num_fragments):
                    self._fragment_counter += 1
                    frag = CrystalFragment(
                        fragment_id=f"frag_{self._fragment_counter}",
                        source_crystal_id=crystal_id,
                        lattice_type=crystal.lattice_type,
                        size=frag_size,
                        coherence=crystal.coherence * random.uniform(0.5, 0.9),
                    )
                    self._fragments.append(frag)
                    fragments_created += 1
                self._record_event(
                    CrystalEvent.CRYSTAL_FRACTURE,
                    intensity=crystal.stress,
                    crystal_ids=[crystal_id],
                    description=f"Crystal '{crystal.label}' fractured into {num_fragments} fragments",
                )
                to_remove.append(crystal_id)

        for cid in to_remove:
            self.remove_crystal(cid)

        self._stats.total_fractures += fractures
        self._stats.total_fragments = len(self._fragments)
        return {
            "crystals_fractured": fractures,
            "fragments_created": fragments_created,
        }

    def _recrystallize_phase(self) -> Dict[str, Any]:
        """Phase 5: Fragments recombine into new stable crystals."""
        recrystallizations = 0
        twinnings = 0

        # Recrystallization: combine fragments of the same lattice type
        available = [f for f in self._fragments if not f.recombined]
        if len(available) >= self.RECRYSTALLIZATION_MIN_FRAGMENTS:
            # Group by lattice type
            by_type: Dict[LatticeType, List[CrystalFragment]] = {}
            for frag in available:
                by_type.setdefault(frag.lattice_type, []).append(frag)

            for ltype, frags in by_type.items():
                if (len(frags) >= self.RECRYSTALLIZATION_MIN_FRAGMENTS
                        and random.random() < self.RECRYSTALLIZATION_PROBABILITY
                        and len(self._crystals) < self.MAX_CRYSTALS):
                    # Combine 2-3 fragments
                    combine_count = min(len(frags), random.randint(2, 3))
                    selected = frags[:combine_count]
                    for f in selected:
                        f.recombined = True
                    new_size = min(self.MAX_SIZE, sum(f.size for f in selected))
                    new_coherence = sum(f.coherence for f in selected) / combine_count
                    new_id = f"recryst_{self._cycle_count}_{recrystallizations}"
                    result = self.register_crystal(
                        new_id,
                        f"Recrystallized {ltype.value} memory",
                        ltype.value,
                        size=new_size,
                        coherence=new_coherence,
                        emotional_charge=0.4,
                    )
                    if "error" not in result:
                        recrystallizations += 1
                        self._record_event(
                            CrystalEvent.RECRYSTALLIZATION,
                            intensity=new_coherence,
                            crystal_ids=[new_id],
                            description=f"{combine_count} fragments recrystallized into '{new_id}'",
                        )

        # Twinning: two similar crystals merge into a twinned pair
        crystal_list = list(self._crystals.values())
        for i in range(len(crystal_list)):
            for j in range(i + 1, len(crystal_list)):
                a = crystal_list[i]
                b = crystal_list[j]
                if (a.twin_id is None and b.twin_id is None
                        and a.lattice_type == b.lattice_type
                        and abs(a.coherence - b.coherence) < self.TWINNING_COHERENCE_THRESHOLD
                        and random.random() < self.TWINNING_PROBABILITY):
                    a.twin_id = b.crystal_id
                    b.twin_id = a.crystal_id
                    twinnings += 1
                    self._record_event(
                        CrystalEvent.TWINNING,
                        intensity=(a.coherence + b.coherence) / 2,
                        crystal_ids=[a.crystal_id, b.crystal_id],
                        description=f"Crystals '{a.label}' and '{b.label}' twinned",
                    )

        # Remove recombined fragments
        self._fragments = deque(
            (f for f in self._fragments if not f.recombined),
            maxlen=self.MAX_FRAGMENTS,
        )

        self._stats.total_recrystallizations += recrystallizations
        self._stats.total_twinnings += twinnings
        self._stats.total_fragments = len(self._fragments)
        return {
            "recrystallizations": recrystallizations,
            "twinnings": twinnings,
        }

    def _check_grain_boundaries(self, new_crystal_id: str) -> None:
        """Check if a new crystal forms grain boundaries with existing ones."""
        new_crystal = self._crystals.get(new_crystal_id)
        if new_crystal is None:
            return
        for other_id, other in self._crystals.items():
            if other_id == new_crystal_id:
                continue
            if other.lattice_type != new_crystal.lattice_type:
                continue
            size_diff = abs(new_crystal.size - other.size)
            if size_diff < self.BOUNDARY_SIMILARITY_THRESHOLD:
                self._boundary_counter += 1
                boundary = GrainBoundary(
                    boundary_id=f"gb_{self._boundary_counter}",
                    crystal_a_id=new_crystal_id,
                    crystal_b_id=other_id,
                    strength=1.0 - size_diff,
                    mismatch=size_diff,
                )
                self._boundaries.append(boundary)
                self._record_event(
                    CrystalEvent.GRAIN_BOUNDARY,
                    intensity=1.0 - size_diff,
                    crystal_ids=[new_crystal_id, other_id],
                    description=f"Grain boundary formed between '{new_crystal.label}' and '{other.label}'",
                )

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
        """Get the overall status of the crystal lattice."""
        with self._lock:
            self._stats.total_crystals = len(self._crystals)
            self._stats.total_fragments = len(self._fragments)
            self._stats.total_boundaries = len(self._boundaries)
            self._stats.total_events = len(self._event_history)
            self._update_avg_metrics()
            return {
                "total_crystals": self._stats.total_crystals,
                "total_fragments": self._stats.total_fragments,
                "total_boundaries": self._stats.total_boundaries,
                "active": self._active,
                "cycle_count": self._cycle_count,
                "stats": {
                    "total_events": self._stats.total_events,
                    "total_seeds_formed": self._stats.total_seeds_formed,
                    "total_growth_events": self._stats.total_growth_events,
                    "total_fractures": self._stats.total_fractures,
                    "total_recrystallizations": self._stats.total_recrystallizations,
                    "total_twinnings": self._stats.total_twinnings,
                    "total_annealings": self._stats.total_annealings,
                    "avg_coherence": round(self._stats.avg_coherence, 4),
                    "avg_stress": round(self._stats.avg_stress, 4),
                    "avg_size": round(self._stats.avg_size, 4),
                    "last_cycle_time_ms": self._stats.last_cycle_time_ms,
                },
            }

    def get_events(
        self, lattice_type: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent crystal events, optionally filtered by lattice type."""
        with self._lock:
            events = list(self._event_history)
            if lattice_type:
                events = [e for e in events if e.get("lattice_type") == lattice_type]
            return events[:limit]

    def reset(self) -> Dict[str, Any]:
        """Reset the crystal lattice to its initial state."""
        with self._lock:
            self._crystals.clear()
            self._fragments.clear()
            self._boundaries.clear()
            self._event_history.clear()
            self._stats = CrystalStats()
            self._cycle_count = 0
            self._active = False
            self._fragment_counter = 0
            self._boundary_counter = 0
            self._event_counter = 0
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _record_event(
        self,
        event: CrystalEvent,
        intensity: float,
        crystal_ids: List[str],
        description: str,
    ) -> None:
        """Record a crystal event in the history."""
        self._event_counter += 1
        self._event_history.append({
            "event_id": f"ce_{self._event_counter}",
            "event_type": event.value,
            "intensity": round(max(0.0, min(1.0, intensity)), 4),
            "crystal_ids": crystal_ids,
            "description": description,
            "timestamp": time.time(),
        })

    def _update_avg_metrics(self) -> None:
        """Update average metrics from current crystals."""
        if not self._crystals:
            self._stats.avg_coherence = 0.0
            self._stats.avg_stress = 0.0
            self._stats.avg_size = 0.0
            return
        n = len(self._crystals)
        self._stats.avg_coherence = sum(c.coherence for c in self._crystals.values()) / n
        self._stats.avg_stress = sum(c.stress for c in self._crystals.values()) / n
        self._stats.avg_size = sum(c.size for c in self._crystals.values()) / n

    def _crystal_to_dict(self, crystal: CrystalSeed) -> Dict[str, Any]:
        """Convert a crystal to a dictionary representation."""
        return {
            "crystal_id": crystal.crystal_id,
            "label": crystal.label,
            "lattice_type": crystal.lattice_type.value,
            "size": round(crystal.size, 4),
            "target_size": round(crystal.target_size, 4),
            "coherence": round(crystal.coherence, 4),
            "stress": round(crystal.stress, 4),
            "stress_tolerance": round(crystal.stress_tolerance, 4),
            "axis_count": crystal.axis_count,
            "axis_progress": [round(p, 4) for p in crystal.axis_progress],
            "fractured": crystal.fractured,
            "recrystallized": crystal.recrystallized,
            "twin_id": crystal.twin_id,
            "emotional_charge": round(crystal.emotional_charge, 4),
            "recall_count": crystal.recall_count,
            "age_cycles": crystal.age_cycles,
            "timestamp": crystal.timestamp,
        }

    def _fragment_to_dict(self, frag: CrystalFragment) -> Dict[str, Any]:
        """Convert a fragment to a dictionary representation."""
        return {
            "fragment_id": frag.fragment_id,
            "source_crystal_id": frag.source_crystal_id,
            "lattice_type": frag.lattice_type.value,
            "size": round(frag.size, 4),
            "coherence": round(frag.coherence, 4),
            "recombined": frag.recombined,
            "timestamp": frag.timestamp,
        }

    def _boundary_to_dict(self, b: GrainBoundary) -> Dict[str, Any]:
        """Convert a grain boundary to a dictionary representation."""
        return {
            "boundary_id": b.boundary_id,
            "crystal_a_id": b.crystal_a_id,
            "crystal_b_id": b.crystal_b_id,
            "strength": round(b.strength, 4),
            "mismatch": round(b.mismatch, 4),
            "timestamp": b.timestamp,
        }
