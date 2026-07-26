"""
SparkLabs Agent - Motivation Chemistry Engine

The AgentMotivationChemistryEngine models NPC motivations as a reactive
chemical solution. Rather than static motivation values, each motivation
is a chemical element with concentration, valence, and reactivity.
Events act as catalysts that trigger reactions, bonds form between
compatible elements creating compound motivations, and unstable
compounds precipitate out of solution.

This chemistry metaphor captures the dynamic, transformative nature of
motivation: a moment of betrayal can catalyze LOYALTY into RESENTMENT,
a heroic deed can bond COURAGE and DUTY into VALOR, and suppressed
AMBITION can decay into APATHY.

Motivational elements (the periodic table of NPC drives):
  AMBITION   - desire for power and achievement
  LOYALTY    - devotion to a cause or person
  FEAR       - avoidance and self-preservation
  CURIOSITY  - drive to explore and understand
  DUTY       - sense of obligation
  GREED      - desire for material gain
  LOVE       - emotional attachment
  PRIDE      - self-worth and dignity
  WRATH      - anger and desire for retribution
  HOPE       - optimism and forward-looking drive

Compound motivations formed by bonding:
  AMBITION + FEAR    = CAUTIOUS_AMBITION
  LOYALTY + DUTY     = DEVOTION
  COURAGE + DUTY     = VALOR
  GREED + FEAR       = PARANOIA
  LOVE + WRATH       = JEALOUSY
  AMBITION + PRIDE   = ARROGANCE
  HOPE + CURIOSITY   = WONDER
  WRATH + DUTY       = RIGHTEOUS_FURY

Architecture:
  DISSOLVE    ->  BOND     ->  REACT    ->  PRECIPITATE  ->  STABILIZE
  (elements      (affinity     (catalysts    (compounds       (decay and
   enter          bonding       trigger       crystallize      equilibrium
   solution)      between       reactions)    from solution)    restoration)

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
from itertools import combinations
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class MotivationElement(Enum):
    """Base motivational elements - the periodic table of NPC drives."""
    AMBITION = "ambition"
    LOYALTY = "loyalty"
    FEAR = "fear"
    CURIOSITY = "curiosity"
    DUTY = "duty"
    GREED = "greed"
    LOVE = "love"
    PRIDE = "pride"
    WRATH = "wrath"
    HOPE = "hope"


class ChemistryPhase(Enum):
    """Phases of the motivation chemistry cycle."""
    DISSOLVE = "dissolve"
    BOND = "bond"
    REACT = "react"
    PRECIPITATE = "precipitate"
    STABILIZE = "stabilize"


class CatalystType(Enum):
    """Types of events that catalyze motivation reactions."""
    BETRAYAL = "betrayal"
    ACHIEVEMENT = "achievement"
    LOSS = "loss"
    DISCOVERY = "discovery"
    CONFLICT = "conflict"
    KINDNESS = "kindness"
    HUMILIATION = "humiliation"
    INSPIRATION = "inspiration"
    THREAT = "threat"
    REWARD = "reward"


class BondType(Enum):
    """Types of bonds between motivational elements."""
    COVALENT = "covalent"      # strong shared bond (positive compounds)
    IONIC = "ionic"            # charged attraction (mixed compounds)
    METALLIC = "metallic"      # fluid network bond (flexible compounds)
    UNSTABLE = "unstable"      # weak bond, prone to breakdown


# =============================================================================
# Chemistry Tables
# =============================================================================

# Affinity matrix: which elements bond together and how strongly
# Positive = attractive (can bond), Negative = repulsive (cannot bond)
ELEMENT_AFFINITY: Dict[MotivationElement, Dict[MotivationElement, float]] = {
    MotivationElement.AMBITION: {
        MotivationElement.FEAR: 0.6, MotivationElement.PRIDE: 0.8,
        MotivationElement.GREED: 0.5, MotivationElement.DUTY: 0.3,
        MotivationElement.LOYALTY: -0.4, MotivationElement.LOVE: -0.2,
        MotivationElement.CURIOSITY: 0.4, MotivationElement.HOPE: 0.5,
        MotivationElement.WRATH: 0.3,
    },
    MotivationElement.LOYALTY: {
        MotivationElement.DUTY: 0.9, MotivationElement.LOVE: 0.7,
        MotivationElement.PRIDE: 0.4, MotivationElement.HOPE: 0.5,
        MotivationElement.AMBITION: -0.4, MotivationElement.GREED: -0.6,
        MotivationElement.WRATH: 0.3, MotivationElement.FEAR: -0.3,
        MotivationElement.CURIOSITY: 0.2,
    },
    MotivationElement.FEAR: {
        MotivationElement.GREED: 0.6, MotivationElement.AMBITION: 0.6,
        MotivationElement.DUTY: -0.3, MotivationElement.PRIDE: 0.4,
        MotivationElement.WRATH: 0.4, MotivationElement.LOVE: -0.5,
        MotivationElement.HOPE: -0.7, MotivationElement.CURIOSITY: 0.3,
        MotivationElement.LOYALTY: -0.3,
    },
    MotivationElement.CURIOSITY: {
        MotivationElement.HOPE: 0.8, MotivationElement.AMBITION: 0.4,
        MotivationElement.FEAR: 0.3, MotivationElement.LOVE: 0.3,
        MotivationElement.DUTY: -0.2, MotivationElement.GREED: 0.3,
        MotivationElement.PRIDE: 0.2, MotivationElement.WRATH: -0.3,
        MotivationElement.LOYALTY: 0.2,
    },
    MotivationElement.DUTY: {
        MotivationElement.LOYALTY: 0.9, MotivationElement.PRIDE: 0.6,
        MotivationElement.AMBITION: 0.3, MotivationElement.FEAR: -0.3,
        MotivationElement.GREED: -0.4, MotivationElement.LOVE: 0.4,
        MotivationElement.HOPE: 0.5, MotivationElement.WRATH: 0.4,
        MotivationElement.CURIOSITY: -0.2,
    },
    MotivationElement.GREED: {
        MotivationElement.FEAR: 0.6, MotivationElement.AMBITION: 0.5,
        MotivationElement.PRIDE: 0.3, MotivationElement.LOYALTY: -0.6,
        MotivationElement.DUTY: -0.4, MotivationElement.LOVE: -0.3,
        MotivationElement.CURIOSITY: 0.3, MotivationElement.WRATH: 0.4,
        MotivationElement.HOPE: -0.2,
    },
    MotivationElement.LOVE: {
        MotivationElement.LOYALTY: 0.7, MotivationElement.HOPE: 0.8,
        MotivationElement.DUTY: 0.4, MotivationElement.CURIOSITY: 0.3,
        MotivationElement.FEAR: -0.5, MotivationElement.GREED: -0.3,
        MotivationElement.WRATH: 0.6, MotivationElement.AMBITION: -0.2,
        MotivationElement.PRIDE: 0.2,
    },
    MotivationElement.PRIDE: {
        MotivationElement.AMBITION: 0.8, MotivationElement.DUTY: 0.6,
        MotivationElement.LOYALTY: 0.4, MotivationElement.FEAR: 0.4,
        MotivationElement.GREED: 0.3, MotivationElement.WRATH: 0.7,
        MotivationElement.HOPE: 0.3, MotivationElement.LOVE: 0.2,
        MotivationElement.CURIOSITY: 0.2,
    },
    MotivationElement.WRATH: {
        MotivationElement.PRIDE: 0.7, MotivationElement.LOVE: 0.6,
        MotivationElement.DUTY: 0.4, MotivationElement.FEAR: 0.4,
        MotivationElement.GREED: 0.4, MotivationElement.AMBITION: 0.3,
        MotivationElement.LOYALTY: 0.3, MotivationElement.HOPE: -0.5,
        MotivationElement.CURIOSITY: -0.3,
    },
    MotivationElement.HOPE: {
        MotivationElement.CURIOSITY: 0.8, MotivationElement.LOVE: 0.8,
        MotivationElement.LOYALTY: 0.5, MotivationElement.DUTY: 0.5,
        MotivationElement.AMBITION: 0.5, MotivationElement.FEAR: -0.7,
        MotivationElement.GREED: -0.2, MotivationElement.PRIDE: 0.3,
        MotivationElement.WRATH: -0.5,
    },
}

# Catalyst reaction table: what each catalyst does to elements
CATALYST_REACTIONS: Dict[CatalystType, Dict[MotivationElement, float]] = {
    CatalystType.BETRAYAL: {
        MotivationElement.LOYALTY: -0.3, MotivationElement.WRATH: +0.25,
        MotivationElement.FEAR: +0.15, MotivationElement.PRIDE: -0.1,
        MotivationElement.LOVE: -0.2, MotivationElement.AMBITION: +0.1,
        MotivationElement.HOPE: -0.15, MotivationElement.GREED: +0.05,
        MotivationElement.CURIOSITY: 0.0, MotivationElement.DUTY: -0.1,
    },
    CatalystType.ACHIEVEMENT: {
        MotivationElement.PRIDE: +0.25, MotivationElement.AMBITION: +0.2,
        MotivationElement.HOPE: +0.2, MotivationElement.FEAR: -0.1,
        MotivationElement.LOYALTY: +0.05, MotivationElement.DUTY: +0.1,
        MotivationElement.LOVE: +0.05, MotivationElement.GREED: +0.1,
        MotivationElement.WRATH: -0.1, MotivationElement.CURIOSITY: +0.1,
    },
    CatalystType.LOSS: {
        MotivationElement.FEAR: +0.2, MotivationElement.WRATH: +0.15,
        MotivationElement.HOPE: -0.2, MotivationElement.LOVE: -0.15,
        MotivationElement.PRIDE: -0.15, MotivationElement.LOYALTY: -0.1,
        MotivationElement.AMBITION: -0.1, MotivationElement.GREED: +0.1,
        MotivationElement.DUTY: +0.05, MotivationElement.CURIOSITY: -0.05,
    },
    CatalystType.DISCOVERY: {
        MotivationElement.CURIOSITY: +0.3, MotivationElement.HOPE: +0.2,
        MotivationElement.AMBITION: +0.1, MotivationElement.FEAR: -0.1,
        MotivationElement.PRIDE: +0.1, MotivationElement.LOVE: +0.05,
        MotivationElement.GREED: +0.1, MotivationElement.DUTY: -0.05,
        MotivationElement.WRATH: -0.1, MotivationElement.LOYALTY: 0.0,
    },
    CatalystType.CONFLICT: {
        MotivationElement.WRATH: +0.25, MotivationElement.FEAR: +0.15,
        MotivationElement.PRIDE: +0.1, MotivationElement.DUTY: +0.15,
        MotivationElement.LOYALTY: +0.1, MotivationElement.AMBITION: +0.1,
        MotivationElement.HOPE: -0.15, MotivationElement.LOVE: -0.1,
        MotivationElement.CURIOSITY: -0.1, MotivationElement.GREED: 0.0,
    },
    CatalystType.KINDNESS: {
        MotivationElement.LOVE: +0.25, MotivationElement.LOYALTY: +0.2,
        MotivationElement.HOPE: +0.2, MotivationElement.FEAR: -0.15,
        MotivationElement.WRATH: -0.2, MotivationElement.GREED: -0.1,
        MotivationElement.DUTY: +0.1, MotivationElement.PRIDE: -0.05,
        MotivationElement.CURIOSITY: +0.05, MotivationElement.AMBITION: -0.05,
    },
    CatalystType.HUMILIATION: {
        MotivationElement.WRATH: +0.3, MotivationElement.FEAR: +0.1,
        MotivationElement.PRIDE: -0.25, MotivationElement.AMBITION: -0.15,
        MotivationElement.HOPE: -0.2, MotivationElement.LOVE: -0.1,
        MotivationElement.LOYALTY: -0.1, MotivationElement.GREED: +0.1,
        MotivationElement.DUTY: -0.05, MotivationElement.CURIOSITY: -0.05,
    },
    CatalystType.INSPIRATION: {
        MotivationElement.HOPE: +0.3, MotivationElement.AMBITION: +0.2,
        MotivationElement.CURIOSITY: +0.2, MotivationElement.PRIDE: +0.15,
        MotivationElement.LOYALTY: +0.15, MotivationElement.DUTY: +0.15,
        MotivationElement.FEAR: -0.2, MotivationElement.WRATH: -0.15,
        MotivationElement.GREED: -0.1, MotivationElement.LOVE: +0.1,
    },
    CatalystType.THREAT: {
        MotivationElement.FEAR: +0.3, MotivationElement.DUTY: +0.15,
        MotivationElement.LOYALTY: +0.1, MotivationElement.WRATH: +0.15,
        MotivationElement.AMBITION: -0.1, MotivationElement.CURIOSITY: -0.15,
        MotivationElement.HOPE: -0.15, MotivationElement.LOVE: -0.05,
        MotivationElement.GREED: +0.05, MotivationElement.PRIDE: +0.05,
    },
    CatalystType.REWARD: {
        MotivationElement.GREED: +0.25, MotivationElement.PRIDE: +0.2,
        MotivationElement.AMBITION: +0.15, MotivationElement.HOPE: +0.15,
        MotivationElement.LOYALTY: +0.1, MotivationElement.DUTY: +0.1,
        MotivationElement.FEAR: -0.1, MotivationElement.WRATH: -0.1,
        MotivationElement.CURIOSITY: +0.05, MotivationElement.LOVE: +0.05,
    },
}

# Compound motivation definitions
COMPOUND_DEFINITIONS: Dict[str, Tuple[MotivationElement, MotivationElement, BondType, float]] = {
    # name: (element_a, element_b, bond_type, minimum_concentration)
    "cautious_ambition": (MotivationElement.AMBITION, MotivationElement.FEAR, BondType.IONIC, 0.3),
    "devotion": (MotivationElement.LOYALTY, MotivationElement.DUTY, BondType.COVALENT, 0.3),
    "valor": (MotivationElement.PRIDE, MotivationElement.DUTY, BondType.COVALENT, 0.3),
    "paranoia": (MotivationElement.GREED, MotivationElement.FEAR, BondType.UNSTABLE, 0.3),
    "jealousy": (MotivationElement.LOVE, MotivationElement.WRATH, BondType.UNSTABLE, 0.3),
    "arrogance": (MotivationElement.AMBITION, MotivationElement.PRIDE, BondType.METALLIC, 0.3),
    "wonder": (MotivationElement.CURIOSITY, MotivationElement.HOPE, BondType.COVALENT, 0.3),
    "righteous_fury": (MotivationElement.WRATH, MotivationElement.DUTY, BondType.COVALENT, 0.3),
    "vengeful_pride": (MotivationElement.WRATH, MotivationElement.PRIDE, BondType.IONIC, 0.3),
    "protective_love": (MotivationElement.LOVE, MotivationElement.DUTY, BondType.COVALENT, 0.3),
    "restless_curiosity": (MotivationElement.CURIOSITY, MotivationElement.FEAR, BondType.IONIC, 0.3),
    "courageous_hope": (MotivationElement.HOPE, MotivationElement.PRIDE, BondType.COVALENT, 0.3),
    "ambitious_greed": (MotivationElement.AMBITION, MotivationElement.GREED, BondType.METALLIC, 0.3),
    "loyal_defiance": (MotivationElement.LOYALTY, MotivationElement.WRATH, BondType.IONIC, 0.3),
    "hopeful_ambition": (MotivationElement.HOPE, MotivationElement.AMBITION, BondType.COVALENT, 0.3),
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class MotivationSolution:
    """The chemical solution of motivations for one NPC."""
    npc_id: str
    # Element concentrations (0.0 - 1.0)
    concentrations: Dict[MotivationElement, float]
    # Active bonds between elements
    bonds: List["MotivationBond"] = field(default_factory=list)
    # Precipitated compound motivations
    compounds: List["CompoundMotivation"] = field(default_factory=list)
    # Solution temperature (emotional intensity, 0.0 - 1.0)
    temperature: float = 0.5
    # Solution pressure (stress level, 0.0 - 1.0)
    pressure: float = 0.3
    # pH balance (optimism vs cynicism, -1.0 to 1.0)
    ph_balance: float = 0.0
    # Metadata
    created_at: float = field(default_factory=time.time)
    last_reaction_at: float = field(default_factory=time.time)
    reaction_count: int = 0


@dataclass
class MotivationBond:
    """A bond between two motivational elements."""
    element_a: MotivationElement
    element_b: MotivationElement
    bond_type: BondType
    strength: float            # 0.0 - 1.0
    formed_at: float
    # Compound this bond contributes to (if any)
    compound_name: Optional[str] = None


@dataclass
class CompoundMotivation:
    """A compound motivation formed from bonded elements."""
    name: str
    elements: Tuple[MotivationElement, MotivationElement]
    bond_type: BondType
    concentration: float       # 0.0 - 1.0
    stability: float           # 0.0 - 1.0, unstable compounds decay
    formed_at: float
    # Behavioral signature: how this compound influences actions
    behavioral_drive: str      # e.g., "risk_taking", "protection", "obsession"


@dataclass
class CatalystEvent:
    """A recorded catalyst event that triggered reactions."""
    event_id: str
    catalyst_type: CatalystType
    npc_id: str
    timestamp: float
    # Elements affected and their deltas
    element_deltas: Dict[MotivationElement, float]
    # Compounds formed or broken
    compounds_formed: List[str] = field(default_factory=list)
    compounds_broken: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class ChemistryStats:
    """Aggregate statistics for the chemistry engine."""
    total_solutions: int = 0
    total_catalysts_applied: int = 0
    total_reactions: int = 0
    total_compounds_formed: int = 0
    total_compounds_broken: int = 0
    total_bonds_formed: int = 0
    total_bonds_broken: int = 0
    avg_temperature: float = 0.5
    avg_pressure: float = 0.3
    avg_ph_balance: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Agent Motivation Chemistry Engine
# =============================================================================

class AgentMotivationChemistryEngine:
    """
    Singleton agent that models NPC motivations as a reactive chemical
    solution where elements bond, react, and transform.

    The engine runs a 5-phase cycle:
      1. DISSOLVE     - Elements enter/refresh in the solution
      2. BOND         - Compatible elements form bonds based on affinity
      3. REACT        - Pending catalysts trigger element transformations
      4. PRECIPITATE  - Stable bonds crystallize into compound motivations
      5. STABILIZE    - Unstable compounds decay, solution reaches equilibrium

    The chemistry metaphor captures how motivations transform through
    experience: betrayal catalyzes loyalty into wrath, achievement
    bonds pride with ambition, and suppressed hope decays into apathy.
    """

    _instance: Optional["AgentMotivationChemistryEngine"] = None
    _instance_lock = threading.Lock()

    # Configuration
    MAX_SOLUTIONS = 200
    MAX_CATALYST_HISTORY = 100
    # Decay rate per cycle for un-reinforced elements
    ELEMENT_DECAY_RATE = 0.02
    # Minimum concentration to remain in solution
    MIN_CONCENTRATION = 0.05
    # Maximum concentration
    MAX_CONCENTRATION = 1.0
    # Bond formation threshold (affinity must exceed this)
    BOND_THRESHOLD = 0.3
    # Compound formation requires both elements above this concentration
    COMPOUND_MIN_CONCENTRATION = 0.3
    # Unstable compound decay rate per cycle
    UNSTABLE_DECAY_RATE = 0.1
    # Temperature increase per catalyst
    CATALYST_TEMPERATURE_BOOST = 0.1
    # Pressure increase per catalyst
    CATALYST_PRESSURE_BOOST = 0.05
    # Natural cooling per cycle
    NATURAL_COOLING = 0.03
    # Natural pressure release per cycle
    NATURAL_PRESSURE_RELEASE = 0.02

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._solutions: Dict[str, MotivationSolution] = {}
        self._pending_catalysts: Deque[CatalystEvent] = deque(maxlen=self.MAX_CATALYST_HISTORY)
        self._catalyst_history: Deque[CatalystEvent] = deque(maxlen=self.MAX_CATALYST_HISTORY)
        self._stats = ChemistryStats()
        self._cycle_count: int = 0
        self._active: bool = False

    @classmethod
    def get_instance(cls) -> "AgentMotivationChemistryEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Solution Management
    # -------------------------------------------------------------------------

    def create_solution(self, npc_id: str,
                        initial_concentrations: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Create a new motivation solution for an NPC."""
        with self._lock:
            if npc_id in self._solutions:
                return {"error": f"Solution already exists: {npc_id}"}
            if len(self._solutions) >= self.MAX_SOLUTIONS:
                return {"error": "Maximum solutions reached"}

            concentrations: Dict[MotivationElement, float] = {}
            for elem in MotivationElement:
                if initial_concentrations and elem.value in initial_concentrations:
                    val = max(0.0, min(self.MAX_CONCENTRATION,
                                       float(initial_concentrations[elem.value])))
                else:
                    val = round(random.uniform(0.1, 0.5), 3)
                concentrations[elem] = val

            solution = MotivationSolution(
                npc_id=npc_id,
                concentrations=concentrations,
            )
            self._solutions[npc_id] = solution
            self._stats.total_solutions += 1
            return self._solution_to_dict(solution)

    def get_solution(self, npc_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            sol = self._solutions.get(npc_id)
            return self._solution_to_dict(sol) if sol else None

    def list_solutions(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            results = [self._solution_to_dict(s) for s in self._solutions.values()]
            results.sort(key=lambda s: s.get("last_reaction_at", 0), reverse=True)
            return results[:limit]

    def remove_solution(self, npc_id: str) -> Dict[str, Any]:
        with self._lock:
            if npc_id not in self._solutions:
                return {"removed": False}
            del self._solutions[npc_id]
            return {"removed": True, "npc_id": npc_id}

    # -------------------------------------------------------------------------
    # Catalyst Application
    # -------------------------------------------------------------------------

    def apply_catalyst(self, npc_id: str, catalyst_type: str,
                       intensity: float = 0.5,
                       description: str = "") -> Dict[str, Any]:
        """Apply a catalyst event to an NPC's motivation solution."""
        with self._lock:
            sol = self._solutions.get(npc_id)
            if sol is None:
                return {"error": f"Solution not found: {npc_id}"}
            try:
                cat = CatalystType(catalyst_type)
            except ValueError:
                return {"error": f"Unknown catalyst type: {catalyst_type}"}

            intensity = max(0.0, min(1.0, float(intensity)))
            reactions = CATALYST_REACTIONS.get(cat, {})
            element_deltas: Dict[MotivationElement, float] = {}
            compounds_formed: List[str] = []
            compounds_broken: List[str] = []

            # Apply element concentration changes
            for elem, delta in reactions.items():
                scaled_delta = delta * intensity
                old_val = sol.concentrations.get(elem, 0.0)
                new_val = max(0.0, min(self.MAX_CONCENTRATION, old_val + scaled_delta))
                if abs(new_val - old_val) > 0.001:
                    sol.concentrations[elem] = round(new_val, 4)
                    element_deltas[elem] = round(scaled_delta, 4)

            # Increase temperature and pressure
            sol.temperature = min(1.0, sol.temperature + self.CATALYST_TEMPERATURE_BOOST * intensity)
            sol.pressure = min(1.0, sol.pressure + self.CATALYST_PRESSURE_BOOST * intensity)

            # Check for new compound formations
            for comp_name, (elem_a, elem_b, bond_type, min_conc) in COMPOUND_DEFINITIONS.items():
                conc_a = sol.concentrations.get(elem_a, 0.0)
                conc_b = sol.concentrations.get(elem_b, 0.0)
                if conc_a >= min_conc and conc_b >= min_conc:
                    # Check if compound already exists
                    existing = next((c for c in sol.compounds if c.name == comp_name), None)
                    if existing is None:
                        # Form new compound
                        affinity = self._get_affinity(elem_a, elem_b)
                        compound_conc = min(conc_a, conc_b) * (0.5 + affinity * 0.5)
                        stability = self._compute_stability(bond_type, affinity, sol.temperature)
                        behavioral_drive = self._get_behavioral_drive(comp_name)
                        compound = CompoundMotivation(
                            name=comp_name,
                            elements=(elem_a, elem_b),
                            bond_type=bond_type,
                            concentration=round(compound_conc, 4),
                            stability=round(stability, 4),
                            formed_at=time.time(),
                            behavioral_drive=behavioral_drive,
                        )
                        sol.compounds.append(compound)
                        compounds_formed.append(comp_name)
                        self._stats.total_compounds_formed += 1

            # Check for compound breakdown (if elements dropped too low)
            for compound in list(sol.compounds):
                elem_a, elem_b = compound.elements
                if sol.concentrations.get(elem_a, 0.0) < self.MIN_CONCENTRATION or \
                   sol.concentrations.get(elem_b, 0.0) < self.MIN_CONCENTRATION:
                    compounds_broken.append(compound.name)
                    sol.compounds.remove(compound)
                    self._stats.total_compounds_broken += 1

            sol.reaction_count += 1
            sol.last_reaction_at = time.time()
            self._stats.total_catalysts_applied += 1
            self._stats.total_reactions += 1

            catalyst_event = CatalystEvent(
                event_id=f"cat_{npc_id}_{int(sol.last_reaction_at * 1000)}",
                catalyst_type=cat,
                npc_id=npc_id,
                timestamp=sol.last_reaction_at,
                element_deltas=element_deltas,
                compounds_formed=compounds_formed,
                compounds_broken=compounds_broken,
                description=description or f"{cat.value} catalyst applied",
            )
            self._catalyst_history.append(catalyst_event)

            return {
                "event_id": catalyst_event.event_id,
                "npc_id": npc_id,
                "catalyst": cat.value,
                "intensity": round(intensity, 3),
                "element_deltas": {k.value: v for k, v in element_deltas.items()},
                "compounds_formed": compounds_formed,
                "compounds_broken": compounds_broken,
                "temperature": round(sol.temperature, 3),
                "pressure": round(sol.pressure, 3),
                "solution": self._solution_to_dict(sol),
            }

    # -------------------------------------------------------------------------
    # Phase Implementations
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single chemistry cycle.

        Phases: DISSOLVE -> BOND -> REACT -> PRECIPITATE -> STABILIZE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: DISSOLVE
            phase = ChemistryPhase.DISSOLVE
            dissolve_info = self._dissolve_phase()

            # Phase 2: BOND
            phase = ChemistryPhase.BOND
            bond_info = self._bond_phase()

            # Phase 3: REACT
            phase = ChemistryPhase.REACT
            react_info = self._react_phase()

            # Phase 4: PRECIPITATE
            phase = ChemistryPhase.PRECIPITATE
            precipitate_info = self._precipitate_phase()

            # Phase 5: STABILIZE
            phase = ChemistryPhase.STABILIZE
            stabilize_info = self._stabilize_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()

            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "dissolve": dissolve_info,
                "bond": bond_info,
                "react": react_info,
                "precipitate": precipitate_info,
                "stabilize": stabilize_info,
                "total_solutions": len(self._solutions),
                "total_compounds": sum(len(s.compounds) for s in self._solutions.values()),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _dissolve_phase(self) -> Dict[str, Any]:
        """Phase 1: Elements dissolve/refresh in solutions."""
        refreshed = 0
        for sol in self._solutions.values():
            # Very slight natural fluctuation
            for elem in sol.concentrations:
                if sol.concentrations[elem] > self.MIN_CONCENTRATION:
                    fluctuation = random.uniform(-0.005, 0.005)
                    sol.concentrations[elem] = max(
                        0.0, min(self.MAX_CONCENTRATION,
                                 sol.concentrations[elem] + fluctuation))
                    refreshed += 1
        return {"elements_refreshed": refreshed}

    def _bond_phase(self) -> Dict[str, Any]:
        """Phase 2: Compatible elements form bonds based on affinity."""
        bonds_formed = 0
        bonds_broken = 0
        for sol in self._solutions.values():
            # Check all element pairs for bonding
            existing_pairs = {(b.element_a, b.element_b) for b in sol.bonds}
            for elem_a, elem_b in combinations(MotivationElement, 2):
                conc_a = sol.concentrations.get(elem_a, 0.0)
                conc_b = sol.concentrations.get(elem_b, 0.0)
                if conc_a < self.MIN_CONCENTRATION or conc_b < self.MIN_CONCENTRATION:
                    continue
                affinity = self._get_affinity(elem_a, elem_b)
                pair = (elem_a, elem_b)
                pair_rev = (elem_b, elem_a)

                if affinity >= self.BOND_THRESHOLD:
                    if pair not in existing_pairs and pair_rev not in existing_pairs:
                        # Form new bond
                        bond_type = self._determine_bond_type(affinity)
                        bond_strength = affinity * min(conc_a, conc_b)
                        # Find compound name if applicable
                        comp_name = self._find_compound_name(elem_a, elem_b)
                        bond = MotivationBond(
                            element_a=elem_a,
                            element_b=elem_b,
                            bond_type=bond_type,
                            strength=round(bond_strength, 4),
                            formed_at=time.time(),
                            compound_name=comp_name,
                        )
                        sol.bonds.append(bond)
                        bonds_formed += 1
                        self._stats.total_bonds_formed += 1
                else:
                    # Check if existing bond should break
                    for bond in list(sol.bonds):
                        if (bond.element_a == elem_a and bond.element_b == elem_b) or \
                           (bond.element_a == elem_b and bond.element_b == elem_a):
                            if affinity < 0:
                                sol.bonds.remove(bond)
                                bonds_broken += 1
                                self._stats.total_bonds_broken += 1
                            break

            # Limit bonds per solution
            if len(sol.bonds) > 15:
                sol.bonds.sort(key=lambda b: b.strength, reverse=True)
                sol.bonds = sol.bonds[:15]

        return {"bonds_formed": bonds_formed, "bonds_broken": bonds_broken}

    def _react_phase(self) -> Dict[str, Any]:
        """Phase 3: Process pending reactions (temperature/pressure effects)."""
        reactions = 0
        for sol in self._solutions.values():
            # High temperature amplifies dominant elements
            if sol.temperature > 0.7:
                dominant = max(sol.concentrations.items(), key=lambda x: x[1])
                if dominant[1] > 0.5:
                    boost = 0.02 * (sol.temperature - 0.7)
                    sol.concentrations[dominant[0]] = min(
                        self.MAX_CONCENTRATION, dominant[1] + boost)
                    reactions += 1
            # High pressure suppresses weak elements
            if sol.pressure > 0.7:
                for elem in list(sol.concentrations.keys()):
                    if sol.concentrations[elem] < 0.2:
                        sol.concentrations[elem] = max(
                            0.0, sol.concentrations[elem] - 0.01)
                        reactions += 1
            # pH balance shifts based on hope vs fear
            hope_conc = sol.concentrations.get(MotivationElement.HOPE, 0.0)
            fear_conc = sol.concentrations.get(MotivationElement.FEAR, 0.0)
            target_ph = (hope_conc - fear_conc)
            sol.ph_balance = round(sol.ph_balance * 0.9 + target_ph * 0.1, 4)

        return {"reactions_triggered": reactions}

    def _precipitate_phase(self) -> Dict[str, Any]:
        """Phase 4: Stable bonds crystallize into compound motivations."""
        compounds_formed = 0
        for sol in self._solutions.values():
            for comp_name, (elem_a, elem_b, bond_type, min_conc) in COMPOUND_DEFINITIONS.items():
                conc_a = sol.concentrations.get(elem_a, 0.0)
                conc_b = sol.concentrations.get(elem_b, 0.0)
                if conc_a >= min_conc and conc_b >= min_conc:
                    existing = next((c for c in sol.compounds if c.name == comp_name), None)
                    if existing is None:
                        affinity = self._get_affinity(elem_a, elem_b)
                        if affinity >= self.BOND_THRESHOLD:
                            compound_conc = min(conc_a, conc_b) * (0.5 + affinity * 0.5)
                            stability = self._compute_stability(bond_type, affinity, sol.temperature)
                            behavioral_drive = self._get_behavioral_drive(comp_name)
                            compound = CompoundMotivation(
                                name=comp_name,
                                elements=(elem_a, elem_b),
                                bond_type=bond_type,
                                concentration=round(compound_conc, 4),
                                stability=round(stability, 4),
                                formed_at=time.time(),
                                behavioral_drive=behavioral_drive,
                            )
                            sol.compounds.append(compound)
                            compounds_formed += 1
                            self._stats.total_compounds_formed += 1
                    else:
                        # Update existing compound concentration
                        affinity = self._get_affinity(elem_a, elem_b)
                        target_conc = min(conc_a, conc_b) * (0.5 + affinity * 0.5)
                        existing.concentration = round(
                            existing.concentration * 0.7 + target_conc * 0.3, 4)

        return {"compounds_formed": compounds_formed}

    def _stabilize_phase(self) -> Dict[str, Any]:
        """Phase 5: Decay unstable compounds, cool solution, release pressure."""
        compounds_decayed = 0
        bonds_decayed = 0
        for sol in self._solutions.values():
            # Decay unstable compounds
            for compound in list(sol.compounds):
                if compound.bond_type == BondType.UNSTABLE:
                    compound.stability -= self.UNSTABLE_DECAY_RATE
                    compound.concentration = max(0.0, compound.concentration - self.UNSTABLE_DECAY_RATE)
                    if compound.stability <= 0 or compound.concentration <= self.MIN_CONCENTRATION:
                        sol.compounds.remove(compound)
                        compounds_decayed += 1
                        self._stats.total_compounds_broken += 1

            # Natural element decay (very slow)
            for elem in list(sol.concentrations.keys()):
                if sol.concentrations[elem] > self.MIN_CONCENTRATION:
                    sol.concentrations[elem] = max(
                        0.0, sol.concentrations[elem] - self.ELEMENT_DECAY_RATE)

            # Cool down temperature
            sol.temperature = max(0.1, sol.temperature - self.NATURAL_COOLING)
            # Release pressure
            sol.pressure = max(0.0, sol.pressure - self.NATURAL_PRESSURE_RELEASE)

            # Decay weak bonds
            for bond in list(sol.bonds):
                bond.strength -= 0.01
                if bond.strength <= 0.05:
                    sol.bonds.remove(bond)
                    bonds_decayed += 1
                    self._stats.total_bonds_broken += 1

        return {
            "compounds_decayed": compounds_decayed,
            "bonds_decayed": bonds_decayed,
        }

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _get_affinity(self, a: MotivationElement, b: MotivationElement) -> float:
        """Get the affinity between two elements (symmetric)."""
        if a == b:
            return 0.0
        # Try both orderings
        if a in ELEMENT_AFFINITY and b in ELEMENT_AFFINITY[a]:
            return ELEMENT_AFFINITY[a][b]
        if b in ELEMENT_AFFINITY and a in ELEMENT_AFFINITY[b]:
            return ELEMENT_AFFINITY[b][a]
        return 0.0

    def _determine_bond_type(self, affinity: float) -> BondType:
        """Determine bond type from affinity strength."""
        if affinity >= 0.7:
            return BondType.COVALENT
        elif affinity >= 0.5:
            return BondType.METALLIC
        elif affinity >= 0.3:
            return BondType.IONIC
        else:
            return BondType.UNSTABLE

    def _compute_stability(self, bond_type: BondType, affinity: float,
                           temperature: float) -> float:
        """Compute the stability of a compound."""
        base_stability = {
            BondType.COVALENT: 0.8,
            BondType.METALLIC: 0.6,
            BondType.IONIC: 0.5,
            BondType.UNSTABLE: 0.3,
        }.get(bond_type, 0.4)
        # High temperature reduces stability
        temp_penalty = temperature * 0.2
        # High affinity increases stability
        affinity_bonus = affinity * 0.2
        return max(0.0, min(1.0, base_stability - temp_penalty + affinity_bonus))

    def _find_compound_name(self, a: MotivationElement,
                            b: MotivationElement) -> Optional[str]:
        """Find the compound name for a pair of elements."""
        for name, (elem_a, elem_b, _, _) in COMPOUND_DEFINITIONS.items():
            if (elem_a == a and elem_b == b) or (elem_a == b and elem_b == a):
                return name
        return None

    def _get_behavioral_drive(self, compound_name: str) -> str:
        """Get the behavioral drive signature for a compound."""
        drives = {
            "cautious_ambition": "calculated_risk_taking",
            "devotion": "selfless_protection",
            "valor": "heroic_courage",
            "paranoia": "defensive_hoarding",
            "jealousy": "possessive_guarding",
            "arrogance": "dominant_assertion",
            "wonder": "exploratory_curiosity",
            "righteous_fury": "crusading_zeal",
            "vengeful_pride": "retributive_action",
            "protective_love": "guardian_instinct",
            "restless_curiosity": "reckless_exploration",
            "courageous_hope": "optimistic_bravery",
            "ambitious_greed": "acquisitive_drive",
            "loyal_defiance": "stubborn_resistance",
            "hopeful_ambition": "visionary_pursuit",
        }
        return drives.get(compound_name, "undefined_drive")

    def _update_avg_metrics(self) -> None:
        """Update average metrics across all solutions."""
        if not self._solutions:
            return
        total_temp = sum(s.temperature for s in self._solutions.values())
        total_press = sum(s.pressure for s in self._solutions.values())
        total_ph = sum(s.ph_balance for s in self._solutions.values())
        n = len(self._solutions)
        self._stats.avg_temperature = round(total_temp / n, 4)
        self._stats.avg_pressure = round(total_press / n, 4)
        self._stats.avg_ph_balance = round(total_ph / n, 4)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            total_compounds = sum(len(s.compounds) for s in self._solutions.values())
            total_bonds = sum(len(s.bonds) for s in self._solutions.values())
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "total_solutions": len(self._solutions),
                "total_compounds": total_compounds,
                "total_bonds": total_bonds,
                "stats": self._stats_to_dict(),
            }

    def list_catalyst_events(self, npc_id: Optional[str] = None,
                             limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            events = list(self._catalyst_history)
            if npc_id:
                events = [e for e in events if e.npc_id == npc_id]
            events.sort(key=lambda e: e.timestamp, reverse=True)
            return [self._catalyst_to_dict(e) for e in events[:limit]]

    def list_compounds(self, npc_id: Optional[str] = None,
                       limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            results = []
            for sol in self._solutions.values():
                if npc_id and sol.npc_id != npc_id:
                    continue
                for comp in sol.compounds:
                    results.append({
                        "npc_id": sol.npc_id,
                        "name": comp.name,
                        "elements": [e.value for e in comp.elements],
                        "bond_type": comp.bond_type.value,
                        "concentration": comp.concentration,
                        "stability": comp.stability,
                        "behavioral_drive": comp.behavioral_drive,
                        "formed_at": comp.formed_at,
                    })
            results.sort(key=lambda c: c.get("concentration", 0), reverse=True)
            return results[:limit]

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles and optionally seed random data."""
        with self._lock:
            # Seed sample solutions if empty
            if not self._solutions:
                archetypes = {
                    "knight": {"duty": 0.8, "loyalty": 0.7, "pride": 0.5, "fear": 0.2},
                    "merchant": {"greed": 0.7, "ambition": 0.6, "curiosity": 0.4, "fear": 0.3},
                    "scholar": {"curiosity": 0.8, "hope": 0.6, "ambition": 0.3, "duty": 0.4},
                    "guard": {"duty": 0.7, "fear": 0.4, "loyalty": 0.5, "wrath": 0.3},
                    "healer": {"love": 0.7, "hope": 0.6, "duty": 0.5, "empathy": 0.6},
                }
                for name, conc in archetypes.items():
                    self.create_solution(f"sim_{name}", conc)

            # Apply random catalysts
            catalyst_types = [c.value for c in CatalystType]
            for _ in range(cycles):
                # Apply a random catalyst to a random solution
                if self._solutions:
                    npc_id = random.choice(list(self._solutions.keys()))
                    cat = random.choice(catalyst_types)
                    self.apply_catalyst(npc_id, cat, intensity=random.uniform(0.3, 0.8))
                self.run_cycle()

            return {
                "cycles_run": cycles,
                "final_status": self.get_status(),
                "final_stats": self._stats_to_dict(),
            }

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            count = len(self._solutions)
            self._solutions.clear()
            self._pending_catalysts.clear()
            self._catalyst_history.clear()
            self._stats = ChemistryStats()
            self._cycle_count = 0
            self._active = False
            return {"reset": True, "cleared_solutions": count}

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _solution_to_dict(self, sol: MotivationSolution) -> Dict[str, Any]:
        return {
            "npc_id": sol.npc_id,
            "concentrations": {k.value: round(v, 4) for k, v in sol.concentrations.items()},
            "bonds": [
                {
                    "element_a": b.element_a.value,
                    "element_b": b.element_b.value,
                    "bond_type": b.bond_type.value,
                    "strength": round(b.strength, 4),
                    "compound_name": b.compound_name,
                }
                for b in sol.bonds
            ],
            "compounds": [
                {
                    "name": c.name,
                    "elements": [e.value for e in c.elements],
                    "bond_type": c.bond_type.value,
                    "concentration": round(c.concentration, 4),
                    "stability": round(c.stability, 4),
                    "behavioral_drive": c.behavioral_drive,
                    "formed_at": c.formed_at,
                }
                for c in sol.compounds
            ],
            "temperature": round(sol.temperature, 4),
            "pressure": round(sol.pressure, 4),
            "ph_balance": round(sol.ph_balance, 4),
            "reaction_count": sol.reaction_count,
            "created_at": sol.created_at,
            "last_reaction_at": sol.last_reaction_at,
        }

    def _catalyst_to_dict(self, e: CatalystEvent) -> Dict[str, Any]:
        return {
            "event_id": e.event_id,
            "catalyst_type": e.catalyst_type.value,
            "npc_id": e.npc_id,
            "timestamp": e.timestamp,
            "element_deltas": {k.value: v for k, v in e.element_deltas.items()},
            "compounds_formed": e.compounds_formed,
            "compounds_broken": e.compounds_broken,
            "description": e.description,
        }

    def _stats_to_dict(self) -> Dict[str, Any]:
        return {
            "total_solutions": self._stats.total_solutions,
            "total_catalysts_applied": self._stats.total_catalysts_applied,
            "total_reactions": self._stats.total_reactions,
            "total_compounds_formed": self._stats.total_compounds_formed,
            "total_compounds_broken": self._stats.total_compounds_broken,
            "total_bonds_formed": self._stats.total_bonds_formed,
            "total_bonds_broken": self._stats.total_bonds_broken,
            "avg_temperature": self._stats.avg_temperature,
            "avg_pressure": self._stats.avg_pressure,
            "avg_ph_balance": self._stats.avg_ph_balance,
            "last_cycle_time_ms": self._stats.last_cycle_time_ms,
            "active": self._stats.active,
        }
