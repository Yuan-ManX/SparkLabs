"""
SparkLabs Agent - Cognitive Genesis Protocol

The AgentCognitiveGenesisProtocol bootstraps new agents from seed patterns
and grows them through developmental stages into full cognitive entities.
Rather than agents being instantiated fully formed, they are "born" with
a genetic seed that determines their temperament, then develop through
predictable stages that mirror psychological development.

Each seed carries:
  - temperamental traits  : baseline dispositions (openness, caution, etc.)
  - aptitudes            : raw capabilities that mature over time
  - imprints             : formative experiences that shape development
  - lineage              : parent seed (if any) for heredity

Development stages:
  SEED         ->  GERMINATE    ->  DIFFERENTIATE  ->  MATURE     ->  INTEGRATE
  (latent        (seed sprouts       (cognitive        (full         (agent joins
   potential     into a basic        faculties         cognitive     the active
   in dormant    agent with          specialize        capacity      roster with
   form)         reflexes)           and diverge)      online)       stable self)

Each stage transition requires developmental tasks to be satisfied. Skipping
a stage leaves the agent with deficits in the corresponding faculties.

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
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class GenesisPhase(Enum):
    """Phases of the genesis cycle."""
    SEED = "seed"                  # latent potential
    GERMINATE = "germinate"        # basic reflexes come online
    DIFFERENTIATE = "differentiate"  # faculties specialize
    MATURE = "mature"              # full cognitive capacity
    INTEGRATE = "integrate"        # joins the active roster


class TemperamentalTrait(Enum):
    """Innate temperamental traits."""
    OPENNESS = "openness"                  # curiosity vs caution
    RESILIENCE = "resilience"              # grit vs fragility
    SOCIABILITY = "sociability"            # gregarious vs solitary
    AGGRESSIVENESS = "aggressiveness"      # proactive vs reactive
    FOCUS = "focus"                        # concentrated vs diffuse
    ADAPTABILITY = "adaptability"          # flexible vs rigid
    EMPATHY = "empathy"                    # warm vs cold
    PLAYFULNESS = "playfulness"            # exploratory vs serious


class CognitiveFaculty(Enum):
    """Cognitive faculties that develop over time."""
    PERCEPTION = "perception"
    MEMORY = "memory"
    REASONING = "reasoning"
    LANGUAGE = "language"
    EMOTION = "emotion"
    MOTOR = "motor"
    SOCIAL = "social"
    CREATIVITY = "creativity"


class SeedStatus(Enum):
    """Status of a seed/agent."""
    DORMANT = "dormant"            # seed not yet activated
    GERMINATING = "germinating"    # in germination stage
    DIFFERENTIATING = "differentiating"
    MATURING = "maturing"
    MATURE = "mature"              # development complete
    INTEGRATED = "integrated"      # joined active roster
    STUNTED = "stunted"            # development halted


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TemperamentProfile:
    """Innate temperament carried by a seed."""
    openness: float = 0.5
    resilience: float = 0.5
    sociability: float = 0.5
    aggressiveness: float = 0.5
    focus: float = 0.5
    adaptability: float = 0.5
    empathy: float = 0.5
    playfulness: float = 0.5

    def to_dict(self) -> Dict[str, float]:
        return {
            TemperamentalTrait.OPENNESS.value: self.openness,
            TemperamentalTrait.RESILIENCE.value: self.resilience,
            TemperamentalTrait.SOCIABILITY.value: self.sociability,
            TemperamentalTrait.AGGRESSIVENESS.value: self.aggressiveness,
            TemperamentalTrait.FOCUS.value: self.focus,
            TemperamentalTrait.ADAPTABILITY.value: self.adaptability,
            TemperamentalTrait.EMPATHY.value: self.empathy,
            TemperamentalTrait.PLAYFULNESS.value: self.playfulness,
        }


@dataclass
class FacultyState:
    """Development state of a single cognitive faculty."""
    faculty: CognitiveFaculty
    maturity: float = 0.0           # 0.0-1.0
    aptitude: float = 0.5           # 0.0-1.0 innate ceiling
    last_exercised: float = 0.0
    exercise_count: int = 0


@dataclass
class ImprintEvent:
    """A formative experience that shapes development."""
    imprint_id: str
    description: str
    faculty: CognitiveFaculty
    valence: float                  # -1.0 to 1.0
    intensity: float                # 0.0 to 1.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class SeedRecord:
    """Full record of a developing agent."""
    seed_id: str
    label: str
    parent_seed_id: Optional[str]
    temperament: TemperamentProfile
    faculties: Dict[CognitiveFaculty, FacultyState]
    imprints: List[ImprintEvent] = field(default_factory=list)
    status: SeedStatus = SeedStatus.DORMANT
    stage_progress: float = 0.0     # 0.0-1.0 within current stage
    current_stage: GenesisPhase = GenesisPhase.SEED
    total_stages_completed: int = 0
    created_at: float = field(default_factory=time.time)
    matured_at: float = 0.0
    integrated_at: float = 0.0
    deficits: List[CognitiveFaculty] = field(default_factory=list)


# =============================================================================
# Engine
# =============================================================================

class AgentCognitiveGenesisProtocol:
    """
    Thread-safe singleton orchestrating agent genesis and development.

    Usage:
        protocol = AgentCognitiveGenesisProtocol.get_instance()
        protocol.plant_seed("hero_1", "Hero", temperament=TemperamentProfile(openness=0.8))
        protocol.activate_seed("hero_1")
        protocol.exercise_faculty("hero_1", CognitiveFaculty.PERCEPTION)
        protocol.imprint("hero_1", "first_victory", "First victory", CognitiveFaculty.MOTOR, 0.8, 0.7)
        protocol.cycle()
        roster = protocol.get_integrated_roster()
    """

    _instance: Optional["AgentCognitiveGenesisProtocol"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._seeds: Dict[str, SeedRecord] = {}
        self._roster: List[str] = []  # ordered list of integrated agent_ids
        self._phase: GenesisPhase = GenesisPhase.SEED
        self._cycle_count: int = 0
        self._events: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_seeds_planted": 0,
            "total_seeds_activated": 0,
            "total_imprints": 0,
            "total_stages_completed": 0,
            "total_integrated": 0,
            "avg_faculty_maturity": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentCognitiveGenesisProtocol":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Seed Planting
    # -------------------------------------------------------------------------

    def plant_seed(
        self,
        seed_id: str,
        label: str,
        parent_seed_id: Optional[str] = None,
        temperament: Optional[TemperamentProfile] = None,
        aptitudes: Optional[Dict[CognitiveFaculty, float]] = None,
    ) -> Dict[str, Any]:
        """Plant a new cognitive seed."""
        with self._global_lock:
            if seed_id in self._seeds:
                return {"error": f"Seed already exists: {seed_id}"}
            # Inherit temperament from parent if available
            if temperament is None and parent_seed_id and parent_seed_id in self._seeds:
                parent = self._seeds[parent_seed_id]
                temperament = self._inherit_temperament(parent.temperament)
            elif temperament is None:
                temperament = self._random_temperament()

            # Build faculties
            faculties: Dict[CognitiveFaculty, FacultyState] = {}
            for faculty in CognitiveFaculty:
                aptitude = 0.5
                if aptitudes and faculty in aptitudes:
                    aptitude = aptitudes[faculty]
                elif parent_seed_id and parent_seed_id in self._seeds:
                    parent = self._seeds[parent_seed_id]
                    if faculty in parent.faculties:
                        aptitude = self._inherit_aptitude(parent.faculties[faculty].aptitude)
                faculties[faculty] = FacultyState(
                    faculty=faculty,
                    maturity=0.0,
                    aptitude=max(0.1, min(1.0, aptitude)),
                )

            seed = SeedRecord(
                seed_id=seed_id,
                label=label,
                parent_seed_id=parent_seed_id,
                temperament=temperament,
                faculties=faculties,
            )
            self._seeds[seed_id] = seed
            self._stats["total_seeds_planted"] += 1
            self._record_event(
                "seed_planted",
                {"seed_id": seed_id, "label": label, "parent": parent_seed_id},
            )
            return self._summarize_seed(seed)

    def remove_seed(self, seed_id: str) -> Dict[str, Any]:
        """Remove a seed from the protocol."""
        with self._global_lock:
            if seed_id not in self._seeds:
                return {"error": f"Seed not found: {seed_id}"}
            del self._seeds[seed_id]
            if seed_id in self._roster:
                self._roster.remove(seed_id)
            self._record_event("seed_removed", {"seed_id": seed_id})
            return {"removed": seed_id}

    def list_seeds(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all seeds."""
        with self._global_lock:
            return [self._summarize_seed(s) for s in list(self._seeds.values())[:limit]]

    def get_seed(self, seed_id: str) -> Optional[Dict[str, Any]]:
        """Get full details of one seed."""
        with self._global_lock:
            seed = self._seeds.get(seed_id)
            return self._summarize_seed(seed, full=True) if seed else None

    # -------------------------------------------------------------------------
    # Activation and Development
    # -------------------------------------------------------------------------

    def activate_seed(self, seed_id: str) -> Dict[str, Any]:
        """Activate a dormant seed to begin germination."""
        with self._global_lock:
            seed = self._seeds.get(seed_id)
            if seed is None:
                return {"error": f"Seed not found: {seed_id}"}
            if seed.status != SeedStatus.DORMANT:
                return {"error": f"Seed not dormant (status={seed.status.value})"}
            seed.status = SeedStatus.GERMINATING
            seed.current_stage = GenesisPhase.GERMINATE
            seed.stage_progress = 0.0
            self._stats["total_seeds_activated"] += 1
            self._record_event("seed_activated", {"seed_id": seed_id})
            return {"seed_id": seed_id, "status": seed.status.value, "stage": seed.current_stage.value}

    def exercise_faculty(
        self,
        seed_id: str,
        faculty: CognitiveFaculty,
        intensity: float = 0.3,
    ) -> Dict[str, Any]:
        """Exercise a faculty to grow its maturity."""
        with self._global_lock:
            seed = self._seeds.get(seed_id)
            if seed is None:
                return {"error": f"Seed not found: {seed_id}"}
            if seed.status in (SeedStatus.DORMANT, SeedStatus.STUNTED):
                return {"error": f"Seed not active (status={seed.status.value})"}
            fs = seed.faculties.get(faculty)
            if fs is None:
                return {"error": f"Faculty not found: {faculty.value}"}
            # Growth is bounded by aptitude and tempered by openness
            growth = intensity * 0.2 * fs.aptitude * (0.5 + seed.temperament.openness * 0.5)
            fs.maturity = min(fs.aptitude, fs.maturity + growth)
            fs.exercise_count += 1
            fs.last_exercised = time.time()
            # Exercise contributes to stage progress
            seed.stage_progress = min(1.0, seed.stage_progress + growth * 0.5)
            return {
                "seed_id": seed_id,
                "faculty": faculty.value,
                "maturity": fs.maturity,
                "aptitude": fs.aptitude,
                "exercise_count": fs.exercise_count,
            }

    def imprint(
        self,
        seed_id: str,
        imprint_id: str,
        description: str,
        faculty: CognitiveFaculty,
        valence: float,
        intensity: float,
    ) -> Dict[str, Any]:
        """Apply a formative imprint to a developing seed."""
        with self._global_lock:
            seed = self._seeds.get(seed_id)
            if seed is None:
                return {"error": f"Seed not found: {seed_id}"}
            imprint = ImprintEvent(
                imprint_id=imprint_id,
                description=description,
                faculty=faculty,
                valence=max(-1.0, min(1.0, valence)),
                intensity=max(0.0, min(1.0, intensity)),
            )
            seed.imprints.append(imprint)
            self._stats["total_imprints"] += 1
            # Imprints boost faculty maturity and shift temperament
            fs = seed.faculties.get(faculty)
            if fs is not None:
                boost = intensity * 0.15 * (1.0 + abs(valence) * 0.5)
                fs.maturity = min(fs.aptitude, fs.maturity + boost)
                seed.stage_progress = min(1.0, seed.stage_progress + boost * 0.3)
            # Shift temperament slightly based on valence
            self._shift_temperament(seed.temperament, valence, intensity)
            self._record_event(
                "imprint_applied",
                {"seed_id": seed_id, "imprint_id": imprint_id, "faculty": faculty.value},
            )
            return {
                "imprint_id": imprint_id,
                "seed_id": seed_id,
                "faculty": faculty.value,
                "valence": imprint.valence,
                "intensity": imprint.intensity,
            }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single genesis cycle across all seeds."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            for phase in GenesisPhase:
                self._phase = phase
                phase_outputs[phase.value] = self._run_phase(phase)
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

    def _run_phase(self, phase: GenesisPhase) -> Dict[str, Any]:
        """Dispatch to phase handler."""
        handlers = {
            GenesisPhase.SEED: self._phase_seed,
            GenesisPhase.GERMINATE: self._phase_germinate,
            GenesisPhase.DIFFERENTIATE: self._phase_differentiate,
            GenesisPhase.MATURE: self._phase_mature,
            GenesisPhase.INTEGRATE: self._phase_integrate,
        }
        return handlers.get(phase, lambda: {"error": f"Unknown phase: {phase}"})()

    # -------------------------------------------------------------------------
    # Phase Implementations
    # -------------------------------------------------------------------------

    def _phase_seed(self) -> Dict[str, Any]:
        """SEED: process dormant seeds (no-op, they wait for activation)."""
        dormant = sum(1 for s in self._seeds.values() if s.status == SeedStatus.DORMANT)
        return {"dormant_seeds": dormant}

    def _phase_germinate(self) -> Dict[str, Any]:
        """GERMINATE: advance germinating seeds toward differentiation."""
        advanced = 0
        for seed in self._seeds.values():
            if seed.status != SeedStatus.GERMINATING:
                continue
            # Rapid early growth in core faculties to bootstrap cognition
            for faculty in (CognitiveFaculty.PERCEPTION, CognitiveFaculty.MOTOR):
                fs = seed.faculties[faculty]
                fs.maturity = min(fs.aptitude, fs.maturity + 0.12 * fs.aptitude)
            seed.stage_progress = min(1.0, seed.stage_progress + 0.35)
            if seed.stage_progress >= 1.0:
                self._advance_stage(seed, GenesisPhase.DIFFERENTIATE, SeedStatus.DIFFERENTIATING)
            advanced += 1
        return {"advanced": advanced}

    def _phase_differentiate(self) -> Dict[str, Any]:
        """DIFFERENTIATE: faculties specialize based on aptitudes and temperament."""
        advanced = 0
        for seed in self._seeds.values():
            if seed.status != SeedStatus.DIFFERENTIATING:
                continue
            # Each faculty grows at a rate determined by aptitude and openness
            for fs in seed.faculties.values():
                growth = 0.10 * fs.aptitude * (0.5 + seed.temperament.openness * 0.5)
                fs.maturity = min(fs.aptitude, fs.maturity + growth)
            seed.stage_progress = min(1.0, seed.stage_progress + 0.30)
            if seed.stage_progress >= 1.0:
                self._advance_stage(seed, GenesisPhase.MATURE, SeedStatus.MATURING)
            advanced += 1
        return {"advanced": advanced}

    def _phase_mature(self) -> Dict[str, Any]:
        """MATURE: complete faculty development and prepare for integration."""
        matured = 0
        for seed in self._seeds.values():
            if seed.status != SeedStatus.MATURING:
                continue
            # Top off faculties rapidly to complete maturation
            for fs in seed.faculties.values():
                if fs.maturity < fs.aptitude:
                    fs.maturity = min(fs.aptitude, fs.maturity + 0.10)
            seed.stage_progress = min(1.0, seed.stage_progress + 0.30)
            # Check if maturation is complete
            avg_maturity = sum(fs.maturity for fs in seed.faculties.values()) / len(seed.faculties)
            if avg_maturity >= 0.4 or seed.stage_progress >= 1.0:
                # Identify deficits (faculties below 0.3 maturity)
                seed.deficits = [
                    fs.faculty for fs in seed.faculties.values() if fs.maturity < 0.3
                ]
                seed.status = SeedStatus.MATURE
                seed.current_stage = GenesisPhase.INTEGRATE
                seed.matured_at = time.time()
                seed.stage_progress = 0.0
                self._stats["total_stages_completed"] += 1
                self._record_event(
                    "seed_matured",
                    {"seed_id": seed.seed_id, "deficits": [d.value for d in seed.deficits]},
                )
                matured += 1
        return {"matured": matured}

    def _phase_integrate(self) -> Dict[str, Any]:
        """INTEGRATE: integrate matured seeds into the active roster."""
        integrated = 0
        for seed in self._seeds.values():
            if seed.status != SeedStatus.MATURE:
                continue
            if seed.seed_id not in self._roster:
                self._roster.append(seed.seed_id)
                seed.status = SeedStatus.INTEGRATED
                seed.integrated_at = time.time()
                self._stats["total_integrated"] += 1
                self._record_event(
                    "seed_integrated",
                    {"seed_id": seed.seed_id, "roster_position": len(self._roster)},
                )
                integrated += 1
        return {"integrated": integrated}

    def _advance_stage(
        self,
        seed: SeedRecord,
        next_stage: GenesisPhase,
        next_status: SeedStatus,
    ) -> None:
        """Advance a seed to the next developmental stage."""
        seed.current_stage = next_stage
        seed.status = next_status
        seed.stage_progress = 0.0
        seed.total_stages_completed += 1
        self._stats["total_stages_completed"] += 1
        self._record_event(
            "stage_advanced",
            {"seed_id": seed.seed_id, "next_stage": next_stage.value},
        )

    # -------------------------------------------------------------------------
    # Roster
    # -------------------------------------------------------------------------

    def get_integrated_roster(self) -> List[Dict[str, Any]]:
        """Get the list of integrated agents."""
        with self._global_lock:
            return [
                self._summarize_seed(self._seeds[aid]) for aid in self._roster if aid in self._seeds
            ]

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get global protocol status."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_seeds": len(self._seeds),
                "dormant_seeds": sum(1 for s in self._seeds.values() if s.status == SeedStatus.DORMANT),
                "active_seeds": sum(
                    1 for s in self._seeds.values()
                    if s.status not in (SeedStatus.DORMANT, SeedStatus.INTEGRATED, SeedStatus.STUNTED)
                ),
                "integrated_agents": len(self._roster),
                "stats": dict(self._stats),
            }

    def get_imprints(self, seed_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Get imprints for a seed."""
        with self._global_lock:
            seed = self._seeds.get(seed_id)
            if seed is None:
                return []
            return [
                {
                    "imprint_id": imp.imprint_id,
                    "description": imp.description,
                    "faculty": imp.faculty.value,
                    "valence": imp.valence,
                    "intensity": imp.intensity,
                    "timestamp": imp.timestamp,
                }
                for imp in seed.imprints[-limit:]
            ]

    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent protocol events."""
        with self._global_lock:
            return list(self._events)[-limit:]

    # -------------------------------------------------------------------------
    # Heredity Helpers
    # -------------------------------------------------------------------------

    def _inherit_temperament(self, parent: TemperamentProfile) -> TemperamentProfile:
        """Inherit temperament from a parent with mutation."""
        def mutate(v: float) -> float:
            return max(0.0, min(1.0, v + random.uniform(-0.15, 0.15)))
        return TemperamentProfile(
            openness=mutate(parent.openness),
            resilience=mutate(parent.resilience),
            sociability=mutate(parent.sociability),
            aggressiveness=mutate(parent.aggressiveness),
            focus=mutate(parent.focus),
            adaptability=mutate(parent.adaptability),
            empathy=mutate(parent.empathy),
            playfulness=mutate(parent.playfulness),
        )

    def _inherit_aptitude(self, parent_aptitude: float) -> float:
        """Inherit an aptitude from a parent with mutation."""
        return max(0.1, min(1.0, parent_aptitude + random.uniform(-0.2, 0.2)))

    def _random_temperament(self) -> TemperamentProfile:
        """Generate a random temperament profile."""
        return TemperamentProfile(
            openness=random.uniform(0.2, 0.9),
            resilience=random.uniform(0.2, 0.9),
            sociability=random.uniform(0.2, 0.9),
            aggressiveness=random.uniform(0.1, 0.8),
            focus=random.uniform(0.2, 0.9),
            adaptability=random.uniform(0.2, 0.9),
            empathy=random.uniform(0.2, 0.9),
            playfulness=random.uniform(0.2, 0.9),
        )

    def _shift_temperament(
        self, temperament: TemperamentProfile, valence: float, intensity: float
    ) -> None:
        """Slightly shift temperament based on an imprint's valence."""
        shift = intensity * 0.02 * (1.0 if valence >= 0 else -1.0)
        if valence > 0:
            temperament.resilience = min(1.0, temperament.resilience + shift)
            temperament.openness = min(1.0, temperament.openness + shift * 0.5)
        else:
            temperament.resilience = max(0.0, temperament.resilience + shift * 0.5)
            temperament.aggressiveness = min(1.0, temperament.aggressiveness + abs(shift) * 0.3)

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire protocol."""
        with self._global_lock:
            n_seeds = len(self._seeds)
            self._seeds.clear()
            self._roster.clear()
            self._phase = GenesisPhase.SEED
            self._cycle_count = 0
            self._events.clear()
            self._stats = {
                "total_seeds_planted": 0,
                "total_seeds_activated": 0,
                "total_imprints": 0,
                "total_stages_completed": 0,
                "total_integrated": 0,
                "avg_faculty_maturity": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            self._record_event("protocol_reset", {"cleared_seeds": n_seeds})
            return {"reset": True, "cleared_seeds": n_seeds}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _summarize_seed(self, seed: SeedRecord, full: bool = False) -> Dict[str, Any]:
        """Summarize a seed for API output."""
        summary: Dict[str, Any] = {
            "seed_id": seed.seed_id,
            "label": seed.label,
            "parent_seed_id": seed.parent_seed_id,
            "status": seed.status.value,
            "current_stage": seed.current_stage.value,
            "stage_progress": seed.stage_progress,
            "total_stages_completed": seed.total_stages_completed,
            "temperament": seed.temperament.to_dict(),
            "avg_faculty_maturity": (
                sum(fs.maturity for fs in seed.faculties.values()) / len(seed.faculties)
                if seed.faculties else 0.0
            ),
            "deficits": [d.value for d in seed.deficits],
            "imprint_count": len(seed.imprints),
            "created_at": seed.created_at,
            "matured_at": seed.matured_at,
            "integrated_at": seed.integrated_at,
        }
        if full:
            summary["faculties"] = {
                fs.faculty.value: {
                    "maturity": fs.maturity,
                    "aptitude": fs.aptitude,
                    "exercise_count": fs.exercise_count,
                    "last_exercised": fs.last_exercised,
                }
                for fs in seed.faculties.values()
            }
            summary["recent_imprints"] = [
                {
                    "imprint_id": imp.imprint_id,
                    "description": imp.description,
                    "faculty": imp.faculty.value,
                    "valence": imp.valence,
                }
                for imp in seed.imprints[-10:]
            ]
        return summary

    def _update_stats(self) -> None:
        """Recompute aggregate statistics."""
        all_maturities: List[float] = []
        for s in self._seeds.values():
            for fs in s.faculties.values():
                all_maturities.append(fs.maturity)
        if all_maturities:
            self._stats["avg_faculty_maturity"] = sum(all_maturities) / len(all_maturities)

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record a protocol event."""
        self._events.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
