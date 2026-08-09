"""
SparkLabs Engine - Chronosynthesis Director"""

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

class ChronoPhase(Enum):
    """Phases of the chronosynthesis cycle."""
    GATHER = "gather"         # gather strata from all three times
    RETRO = "retro"           # present retrocharges past
    PREMON = "premon"         # future premonishes present
    RECON = "recon"           # reconcile contradictions
    CRYSTAL = "crystal"       # crystallize aligned moments


class StratumType(Enum):
    """The three temporal strata."""
    PAST = "past"               # memory stratum
    PRESENT = "present"         # action stratum
    FUTURE = "future"           # possibility stratum


class MemoryValence(Enum):
    """Emotional charge of a past memory."""
    GLORIOUS = "glorious"
    BITTERSWEET = "bittersweet"
    NEUTRAL = "neutral"
    REGRETFUL = "regretful"
    TRAUMATIC = "traumatic"


class FutureBranch(Enum):
    """Categories of future possibilities."""
    ASPIRED = "aspired"         # actively desired
    FEARED = "feared"           # actively dreaded
    LIKELY = "likely"           # high probability
    UNLIKELY = "unlikely"       # low probability
    IMPOSSIBLE = "impossible"   # cannot happen (but considered)
    WILD = "wild"               # unexpected wildcard


class AlignmentType(Enum):
    """How past/present/future align."""
    HARMONIC = "harmonic"       # all three resonate
    DISSONANT = "dissonant"     # all three clash
    BRIDGE = "bridge"           # present bridges past and future
    FRACTURE = "fracture"       # past and future pull apart
    ECHO = "echo"               # past and future mirror each other


class ChronoMomentState(Enum):
    """Lifecycle of a crystallized chrono moment."""
    NASCENT = "nascent"
    PEAK = "peak"
    FADING = "fading"
    DISSOLVED = "dissolved"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PastMemory:
    """A memory in the past stratum."""
    memory_id: str
    label: str
    valence: MemoryValence
    significance: float = 0.5      # how important (0.0-1.0)
    retrocharge: float = 0.0       # accumulated retroactive charge
    reinterpretations: int = 0     # how many times re-interpreted
    created_at: float = field(default_factory=time.time)
    original_meaning: str = ""
    current_meaning: str = ""


@dataclass
class PresentAction:
    """An action in the present stratum."""
    action_id: str
    label: str
    agency: float = 0.5            # how much will was exercised (0.0-1.0)
    target_memories: List[str] = field(default_factory=list)  # memories it retrocharges
    target_futures: List[str] = field(default_factory=list)   # futures it realizes/closes
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False


@dataclass
class FuturePossibility:
    """A possibility in the future stratum."""
    possibility_id: str
    label: str
    branch: FutureBranch
    probability: float = 0.3       # likelihood (0.0-1.0)
    pull_strength: float = 0.2     # backward pull on present (0.0-1.0)
    premonition_charge: float = 0.0  # accumulated premonition energy
    created_at: float = field(default_factory=time.time)


@dataclass
class ChronoMoment:
    """A crystallized moment of chrono alignment."""
    moment_id: str
    label: str
    alignment: AlignmentType
    past_memory: str
    present_action: str
    future_possibility: str
    power: float                   # combined power (0.0-1.0)
    state: ChronoMomentState = ChronoMomentState.NASCENT
    created_at: float = field(default_factory=time.time)


@dataclass
class StratumContradiction:
    """A contradiction between strata."""
    contradiction_id: str
    stratum_a: StratumType
    stratum_b: StratumType
    element_a: str  # memory_id / action_id / possibility_id
    element_b: str
    tension: float = 0.5
    resolved: bool = False
    resolution: str = ""


@dataclass
class ChronoRegion:
    """Per-region chrono state."""
    region_id: str
    label: str
    past_memories: Dict[str, PastMemory] = field(default_factory=dict)
    present_actions: Deque[PresentAction] = field(default_factory=lambda: deque(maxlen=100))
    future_possibilities: Dict[str, FuturePossibility] = field(default_factory=dict)
    contradictions: Deque[StratumContradiction] = field(default_factory=lambda: deque(maxlen=50))
    chrono_moments: Dict[str, ChronoMoment] = field(default_factory=dict)
    chrono_coherence: float = 0.5  # overall temporal coherence (0.0-1.0)


# =============================================================================
# Director
# =============================================================================

class EngineChronosynthesisDirector:
    """
    Thread-safe singleton orchestrating chronosynthesis across regions.

    Usage:
        director = EngineChronosynthesisDirector.get_instance()
        director.register_region("r_kingdom", "The Kingdom")
        director.add_memory("r_kingdom", "mem_war", "The Great War", MemoryValence.TRAUMATIC, 0.9)
        director.add_action("r_kingdom", "act_peace", "Sign Peace Treaty", 0.8, ["mem_war"])
        director.add_future("r_kingdom", "fut_prosper", "Prosperity", FutureBranch.ASPIRED, 0.6)
        director.cycle()
    """

    _instance: Optional["EngineChronosynthesisDirector"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._regions: Dict[str, ChronoRegion] = {}
        self._phase: ChronoPhase = ChronoPhase.GATHER
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_regions": 0,
            "total_memories": 0,
            "total_actions": 0,
            "total_futures": 0,
            "total_contradictions": 0,
            "total_moments": 0,
            "resolved_contradictions": 0,
            "peak_moments": 0,
            "avg_coherence": 0.0,
            "avg_retrocharge": 0.0,
            "avg_premonition": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineChronosynthesisDirector":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Region Management
    # -------------------------------------------------------------------------

    def register_region(self, region_id: str, label: str) -> Dict[str, Any]:
        """Register a new region with the director."""
        with self._global_lock:
            if region_id in self._regions:
                return {"error": f"Region already registered: {region_id}"}
            self._regions[region_id] = ChronoRegion(region_id=region_id, label=label)
            self._stats["total_regions"] = len(self._regions)
            self._record_event("region_registered", {"region_id": region_id})
            return {"region_id": region_id, "label": label}

    def remove_region(self, region_id: str) -> Dict[str, Any]:
        """Remove a region."""
        with self._global_lock:
            if region_id not in self._regions:
                return {"error": f"Region not found: {region_id}"}
            r = self._regions.pop(region_id)
            self._stats["total_regions"] = len(self._regions)
            return {
                "removed": region_id,
                "memories": len(r.past_memories),
                "futures": len(r.future_possibilities),
                "moments": len(r.chrono_moments),
            }

    # -------------------------------------------------------------------------
    # Stratum Population
    # -------------------------------------------------------------------------

    def add_memory(
        self,
        region_id: str,
        memory_id: str,
        label: str,
        valence: MemoryValence,
        significance: float = 0.5,
        original_meaning: str = "",
    ) -> Dict[str, Any]:
        """Add a memory to the past stratum."""
        with self._global_lock:
            r = self._regions.get(region_id)
            if r is None:
                return {"error": f"Region not found: {region_id}"}
            if memory_id in r.past_memories:
                return {"error": f"Memory already exists: {memory_id}"}
            memory = PastMemory(
                memory_id=memory_id,
                label=label,
                valence=valence,
                significance=max(0.0, min(1.0, significance)),
                original_meaning=original_meaning or label,
                current_meaning=original_meaning or label,
            )
            r.past_memories[memory_id] = memory
            self._stats["total_memories"] = sum(len(reg.past_memories) for reg in self._regions.values())
            self._record_event("memory_added", {
                "region_id": region_id, "memory_id": memory_id, "valence": valence.value,
            })
            return {
                "memory_id": memory_id,
                "label": label,
                "valence": valence.value,
                "significance": memory.significance,
            }

    def add_action(
        self,
        region_id: str,
        action_id: str,
        label: str,
        agency: float = 0.5,
        target_memories: Optional[List[str]] = None,
        target_futures: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Add an action to the present stratum."""
        with self._global_lock:
            r = self._regions.get(region_id)
            if r is None:
                return {"error": f"Region not found: {region_id}"}
            action = PresentAction(
                action_id=action_id,
                label=label,
                agency=max(0.0, min(1.0, agency)),
                target_memories=target_memories or [],
                target_futures=target_futures or [],
            )
            r.present_actions.append(action)
            self._stats["total_actions"] = sum(len(reg.present_actions) for reg in self._regions.values())
            self._record_event("action_added", {
                "region_id": region_id, "action_id": action_id, "agency": action.agency,
            })
            return {
                "action_id": action_id,
                "label": label,
                "agency": action.agency,
                "target_memories": action.target_memories,
                "target_futures": action.target_futures,
            }

    def add_future(
        self,
        region_id: str,
        possibility_id: str,
        label: str,
        branch: FutureBranch,
        probability: float = 0.3,
        pull_strength: float = 0.2,
    ) -> Dict[str, Any]:
        """Add a possibility to the future stratum."""
        with self._global_lock:
            r = self._regions.get(region_id)
            if r is None:
                return {"error": f"Region not found: {region_id}"}
            if possibility_id in r.future_possibilities:
                return {"error": f"Future already exists: {possibility_id}"}
            future = FuturePossibility(
                possibility_id=possibility_id,
                label=label,
                branch=branch,
                probability=max(0.0, min(1.0, probability)),
                pull_strength=max(0.0, min(1.0, pull_strength)),
            )
            r.future_possibilities[possibility_id] = future
            self._stats["total_futures"] = sum(len(reg.future_possibilities) for reg in self._regions.values())
            self._record_event("future_added", {
                "region_id": region_id, "possibility_id": possibility_id, "branch": branch.value,
            })
            return {
                "possibility_id": possibility_id,
                "label": label,
                "branch": branch.value,
                "probability": future.probability,
                "pull_strength": future.pull_strength,
            }

    # -------------------------------------------------------------------------
    # Phase: GATHER - collect strata and compute coherence
    # -------------------------------------------------------------------------

    def _phase_gather(self) -> Dict[str, Any]:
        """Gather strata from all regions and compute coherence."""
        total_memories = 0
        total_actions = 0
        total_futures = 0
        for r in self._regions.values():
            total_memories += len(r.past_memories)
            total_actions += len(r.present_actions)
            total_futures += len(r.future_possibilities)
            # coherence is balanced presence of all three strata
            m = min(1.0, len(r.past_memories) / 5.0)
            a = min(1.0, len(r.present_actions) / 5.0)
            f = min(1.0, len(r.future_possibilities) / 5.0)
            # coherence is highest when all three are present
            r.chrono_coherence = (m * a * f) ** 0.5
        return {
            "memories": total_memories,
            "actions": total_actions,
            "futures": total_futures,
        }

    # -------------------------------------------------------------------------
    # Phase: RETRO - present retrocharges past
    # -------------------------------------------------------------------------

    def _phase_retro(self) -> Dict[str, Any]:
        """Present actions retroactively charge past memories."""
        retrocharges = 0
        for r in self._regions.values():
            for action in r.present_actions:
                if action.resolved:
                    continue
                for mem_id in action.target_memories:
                    memory = r.past_memories.get(mem_id)
                    if memory is None:
                        continue
                    # retrocharge based on action agency and memory significance
                    charge = action.agency * memory.significance * 0.3
                    memory.retrocharge = min(1.0, memory.retrocharge + charge)
                    memory.reinterpretations += 1
                    # re-interpret the memory's meaning
                    valence_shift = {
                        MemoryValence.GLORIOUS: 0.0,
                        MemoryValence.BITTERSWEET: 0.1,
                        MemoryValence.NEUTRAL: 0.2,
                        MemoryValence.REGRETFUL: 0.3,
                        MemoryValence.TRAUMATIC: 0.4,
                    }
                    shift = valence_shift.get(memory.valence, 0.1)
                    if shift > 0:
                        # reinterpret toward glorious (healing)
                        memory.current_meaning = f"{memory.original_meaning} (re-interpreted through '{action.label}')"
                        retrocharges += 1
                action.resolved = True
        return {"retrocharges_applied": retrocharges}

    # -------------------------------------------------------------------------
    # Phase: PREMON - future premonishes present
    # -------------------------------------------------------------------------

    def _phase_premon(self) -> Dict[str, Any]:
        """Future possibilities exert backward pull on present."""
        premonitions = 0
        for r in self._regions.values():
            for future in r.future_possibilities.values():
                # probability increases pull
                pull = future.pull_strength * future.probability
                future.premonition_charge = min(1.0, future.premonition_charge + pull * 0.2)
                # if pull is strong, affect recent actions
                if pull > 0.3:
                    for action in list(r.present_actions)[-5:]:
                        if future.possibility_id in action.target_futures:
                            # agency is shaped by the future's pull
                            action.agency = min(1.0, action.agency + pull * 0.1)
                            premonitions += 1
        return {"premonitions_felt": premonitions}

    # -------------------------------------------------------------------------
    # Phase: RECON - reconcile contradictions
    # -------------------------------------------------------------------------

    def _phase_recon(self) -> Dict[str, Any]:
        """Detect and resolve contradictions between strata."""
        detected = 0
        resolved = 0
        for r in self._regions.values():
            # check past-present contradictions
            for action in r.present_actions:
                for mem_id in action.target_memories:
                    memory = r.past_memories.get(mem_id)
                    if memory is None:
                        continue
                    # contradiction if action agency is high but memory is traumatic
                    if (action.agency > 0.7 and memory.valence == MemoryValence.TRAUMATIC
                            and memory.retrocharge < 0.3):
                        cid = f"con_{r.region_id}_{len(r.contradictions)}"
                        con = StratumContradiction(
                            contradiction_id=cid,
                            stratum_a=StratumType.PRESENT,
                            stratum_b=StratumType.PAST,
                            element_a=action.action_id,
                            element_b=mem_id,
                            tension=0.7,
                        )
                        r.contradictions.append(con)
                        detected += 1
                        # attempt resolution: high agency heals trauma over time
                        if memory.reinterpretations > 2:
                            con.resolved = True
                            con.resolution = "agency processed the trauma"
                            memory.valence = MemoryValence.BITTERSWEET
                            resolved += 1
            # check present-future contradictions
            for action in r.present_actions:
                for fut_id in action.target_futures:
                    future = r.future_possibilities.get(fut_id)
                    if future is None:
                        continue
                    # contradiction if action agency is high but future is feared
                    if action.agency > 0.7 and future.branch == FutureBranch.FEARED:
                        cid = f"con_{r.region_id}_{len(r.contradictions)}"
                        con = StratumContradiction(
                            contradiction_id=cid,
                            stratum_a=StratumType.PRESENT,
                            stratum_b=StratumType.FUTURE,
                            element_a=action.action_id,
                            element_b=fut_id,
                            tension=0.6,
                        )
                        r.contradictions.append(con)
                        detected += 1
                        # attempt: high agency can reduce feared future's probability
                        if action.agency > 0.8:
                            future.probability = max(0.0, future.probability - 0.2)
                            con.resolved = True
                            con.resolution = "agency averted the feared future"
                            resolved += 1
        self._stats["resolved_contradictions"] += resolved
        return {"contradictions_detected": detected, "contradictions_resolved": resolved}

    # -------------------------------------------------------------------------
    # Phase: CRYSTAL - crystallize aligned moments
    # -------------------------------------------------------------------------

    def _phase_crystal(self) -> Dict[str, Any]:
        """Crystallize chrono moments when strata align."""
        crystallized = 0
        for r in self._regions.values():
            for action in r.present_actions:
                # find memories and futures connected to this action
                for mem_id in action.target_memories:
                    memory = r.past_memories.get(mem_id)
                    if memory is None or memory.retrocharge < 0.3:
                        continue
                    for fut_id in action.target_futures:
                        future = r.future_possibilities.get(fut_id)
                        if future is None or future.premonition_charge < 0.3:
                            continue
                        # check for existing moment
                        existing = any(
                            m.present_action == action.action_id
                            and m.past_memory == mem_id
                            and m.future_possibility == fut_id
                            for m in r.chrono_moments.values()
                        )
                        if existing:
                            continue
                        # determine alignment type
                        if (memory.valence in (MemoryValence.GLORIOUS, MemoryValence.BITTERSWEET)
                                and future.branch in (FutureBranch.ASPIRED, FutureBranch.LIKELY)):
                            alignment = AlignmentType.HARMONIC
                        elif (memory.valence in (MemoryValence.TRAUMATIC, MemoryValence.REGRETFUL)
                              and future.branch == FutureBranch.FEARED):
                            alignment = AlignmentType.DISSONANT
                        elif memory.valence == MemoryValence.NEUTRAL and future.branch == FutureBranch.WILD:
                            alignment = AlignmentType.ECHO
                        elif action.agency > 0.7:
                            alignment = AlignmentType.BRIDGE
                        else:
                            alignment = AlignmentType.FRACTURE
                        # power based on all three
                        power = (
                            memory.retrocharge * 0.33
                            + action.agency * 0.33
                            + future.premonition_charge * 0.34
                        )
                        moment_id = f"cm_{r.region_id}_{len(r.chrono_moments)}"
                        moment = ChronoMoment(
                            moment_id=moment_id,
                            label=f"{action.label} aligns {memory.label} with {future.label}",
                            alignment=alignment,
                            past_memory=mem_id,
                            present_action=action.action_id,
                            future_possibility=fut_id,
                            power=power,
                        )
                        r.chrono_moments[moment_id] = moment
                        crystallized += 1
                        if power > 0.7:
                            moment.state = ChronoMomentState.PEAK
                            self._stats["peak_moments"] += 1
                        self._record_event("chrono_moment", {
                            "region_id": r.region_id, "moment_id": moment_id,
                            "alignment": alignment.value, "power": power,
                        })
        self._stats["total_moments"] = sum(len(r.chrono_moments) for r in self._regions.values())
        return {"moments_crystallized": crystallized}

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single chronosynthesis cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = ChronoPhase.GATHER
            phase_outputs["gather"] = self._phase_gather()
            self._phase = ChronoPhase.RETRO
            phase_outputs["retro"] = self._phase_retro()
            self._phase = ChronoPhase.PREMON
            phase_outputs["premon"] = self._phase_premon()
            self._phase = ChronoPhase.RECON
            phase_outputs["recon"] = self._phase_recon()
            self._phase = ChronoPhase.CRYSTAL
            phase_outputs["crystal"] = self._phase_crystal()
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

    def get_region_state(self, region_id: str) -> Dict[str, Any]:
        """Get a region's chrono state."""
        with self._global_lock:
            r = self._regions.get(region_id)
            if r is None:
                return {"error": f"Region not found: {region_id}"}
            return {
                "region_id": region_id,
                "label": r.label,
                "chrono_coherence": r.chrono_coherence,
                "total_memories": len(r.past_memories),
                "total_actions": len(r.present_actions),
                "total_futures": len(r.future_possibilities),
                "total_contradictions": len(r.contradictions),
                "total_moments": len(r.chrono_moments),
                "peak_moments": sum(1 for m in r.chrono_moments.values() if m.state == ChronoMomentState.PEAK),
                "memories": [
                    {
                        "memory_id": m.memory_id,
                        "label": m.label,
                        "valence": m.valence.value,
                        "significance": m.significance,
                        "retrocharge": m.retrocharge,
                        "reinterpretations": m.reinterpretations,
                        "current_meaning": m.current_meaning,
                    }
                    for m in r.past_memories.values()
                ],
                "futures": [
                    {
                        "possibility_id": f.possibility_id,
                        "label": f.label,
                        "branch": f.branch.value,
                        "probability": f.probability,
                        "premonition_charge": f.premonition_charge,
                    }
                    for f in r.future_possibilities.values()
                ],
                "chrono_moments": [
                    {
                        "moment_id": cm.moment_id,
                        "label": cm.label,
                        "alignment": cm.alignment.value,
                        "power": cm.power,
                        "state": cm.state.value,
                    }
                    for cm in r.chrono_moments.values()
                ],
            }

    def get_contradictions(self, region_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent contradictions for a region."""
        with self._global_lock:
            r = self._regions.get(region_id)
            if r is None:
                return []
            recent = list(r.contradictions)[-limit:]
            return [
                {
                    "contradiction_id": c.contradiction_id,
                    "stratum_a": c.stratum_a.value,
                    "stratum_b": c.stratum_b.value,
                    "element_a": c.element_a,
                    "element_b": c.element_b,
                    "tension": c.tension,
                    "resolved": c.resolved,
                    "resolution": c.resolution,
                }
                for c in recent
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get director status."""
        with self._global_lock:
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "stats": dict(self._stats),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the entire director."""
        with self._global_lock:
            count = len(self._regions)
            self._regions.clear()
            self._events_log.clear()
            self._cycle_count = 0
            self._phase = ChronoPhase.GATHER
            self._stats = {
                "total_regions": 0,
                "total_memories": 0,
                "total_actions": 0,
                "total_futures": 0,
                "total_contradictions": 0,
                "total_moments": 0,
                "resolved_contradictions": 0,
                "peak_moments": 0,
                "avg_coherence": 0.0,
                "avg_retrocharge": 0.0,
                "avg_premonition": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "regions_removed": count}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _update_stats(self) -> None:
        if self._regions:
            self._stats["avg_coherence"] = sum(r.chrono_coherence for r in self._regions.values()) / len(self._regions)
            all_memories = [m for r in self._regions.values() for m in r.past_memories.values()]
            if all_memories:
                self._stats["avg_retrocharge"] = sum(m.retrocharge for m in all_memories) / len(all_memories)
            all_futures = [f for r in self._regions.values() for f in r.future_possibilities.values()]
            if all_futures:
                self._stats["avg_premonition"] = sum(f.premonition_charge for f in all_futures) / len(all_futures)
            self._stats["total_contradictions"] = sum(len(r.contradictions) for r in self._regions.values())

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "timestamp": time.time(),
            "type": event_type,
            **payload,
        })
