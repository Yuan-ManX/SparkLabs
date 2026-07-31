"""
SparkLabs Engine - Emergent Quest Composer

The EngineEmergentQuestComposer grows quests out of the world-state
rather than hand-authoring them. A world is a fabric of tensions,
shortages, debts, and surpluses; when one part of the world shifts,
the shift propagates outward. Where the propagating pressure crosses
a threshold it crystalizes into a quest-shaped tension, the quest is
commissioned to one or more agents, and once the agents act, the
quest resolves back into the world-state that birthed it.

A quest that the designer drops in from outside tends to feel pasted
on; a quest that the world grows from its own pressures tends to feel
inevitable - the player can feel that someone, somewhere, needed this
done.

Architecture:
  SENSE       ->  PROPAGATE   ->  CRYSTALIZE  ->  COMMISSION  ->  RESOLVE
  (the world    (each shift     (where the      (the quest is    (once the
   reports a    radiates        pressure        handed to        agents act,
   shift)       outward as      crosses a       agents)          the quest
                pressure)       threshold it    commission->     folds back
                                becomes a       resolve->...     into the
                                quest-shaped    over cycles)     world that
                                tension)                        birthed it)

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
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class QuestPhase(Enum):
    """Phases of the emergent quest cycle."""
    SENSE = "sense"              # the world reports a shift
    PROPAGATE = "propagate"      # the shift radiates outward as pressure
    CRYSTALIZE = "crystalize"    # pressure crosses a threshold and forms a quest
    COMMISSION = "commission"    # the quest is handed to agents
    RESOLVE = "resolve"          # the quest folds back into the world


class ShiftKind(Enum):
    """The kind of shift the world reports."""
    SHORTAGE = "shortage"        # something has run scarce
    SURPLUS = "surplus"          # something has piled up
    DEBT = "debt"                # an obligation has come due
    GRIEVANCE = "grievance"      # someone has been wronged
    OPPORTUNITY = "opportunity"  # an opening has appeared
    THREAT = "threat"            # something dangerous has emerged


class PressureRelation(Enum):
    """How a propagated pressure relates to its source shift."""
    AMPLIFYING = "amplifying"    # the pressure grows as it travels
    DAMPING = "damping"          # the pressure shrinks as it travels
    REROUTING = "rerouting"      # the pressure shifts to a new region
    STABILIZING = "stabilizing"  # the pressure self-corrects


class QuestState(Enum):
    """State of an individual emergent quest."""
    LATENT = "latent"            # pressure exists, no quest yet
    CRYSTALIZED = "crystalized"  # pressure crossed threshold, quest formed
    COMMISSIONED = "commissioned"  # handed to agents
    IN_PROGRESS = "in_progress"  # agents are acting on it
    RESOLVED = "resolved"        # agents acted, quest folds back into world
    ABANDONED = "abandoned"      # pressure faded before resolution


class QuestShape(Enum):
    """The shape the crystalized quest takes."""
    FETCH = "fetch"              # bring something from where it is to where it is not
    ESCORT = "escort"            # move something fragile through danger
    MEDIATE = "mediate"          # stand between two opposing pressures
    ELIMINATE = "eliminate"      # remove the source of a threat
    REPAIR = "repair"            # mend what the shift broke
    DISCOVER = "discover"        # find out what the shift uncovered


class WorldVitality(Enum):
    """The overall vitality of the emergent quest ecosystem."""
    DORMANT = "dormant"          # few shifts, few quests
    STIRRING = "stirring"        # shifts coming, quests beginning to form
    FLOWING = "flowing"          # healthy quest generation and resolution
    OVERLOADED = "overloaded"    # too many quests, not enough resolution
    COLLAPSED = "collapsed"      # resolution has failed across the board


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class WorldShift:
    """A shift the world reports to the composer."""
    shift_id: str
    region: str
    kind: ShiftKind
    magnitude: float = 0.5             # 0.0-1.0, how big the shift is
    note: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class PropagatedPressure:
    """A pressure radiated outward from a world shift."""
    pressure_id: str
    source_shift_id: str
    target_region: str
    relation: PressureRelation
    intensity: float = 0.3             # 0.0-1.0
    distance: int = 1                  # how many hops from the source


@dataclass
class EmergentQuest:
    """A quest crystalized from accumulated pressure."""
    quest_id: str
    source_shift_id: str
    shape: QuestShape
    region: str
    tension: float = 0.5               # 0.0-1.0, how urgent
    coherence: float = 0.0             # 0.0-1.0, how well-formed
    assigned_agents: List[str] = field(default_factory=list)
    resolution_pressure: float = 0.0   # 0.0-1.0, accumulated progress
    state: QuestState = QuestState.LATENT
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    note: str = ""


@dataclass
class QuestRegion:
    """Per-region quest ecosystem state."""
    region_id: str
    shifts: List[WorldShift] = field(default_factory=list)
    pressures: List[PropagatedPressure] = field(default_factory=list)
    quests: Dict[str, EmergentQuest] = field(default_factory=dict)
    pressure_total: float = 0.0
    total_sensed: int = 0
    total_propagated: int = 0
    total_crystalized: int = 0
    total_commissioned: int = 0
    total_resolved: int = 0
    total_abandoned: int = 0


# =============================================================================
# Composer
# =============================================================================

class EngineEmergentQuestComposer:
    """
    Thread-safe singleton orchestrating emergent quest composition.

    Usage:
        composer = EngineEmergentQuestComposer.get_instance()
        composer.register_region("frontier")
        composer.sense_shift("frontier", "s1", ShiftKind.THREAT, 0.6)
        composer.cycle()
        state = composer.get_region_state("frontier")
    """

    _instance: Optional["EngineEmergentQuestComposer"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _PROPAGATE_HOP_DECAY = 0.7           # intensity lost per hop
    _PROPAGATE_MAX_HOPS = 3              # how far a pressure radiates
    _CRYSTALIZE_THRESHOLD = 0.4          # intensity needed to form a quest
    _COMMISSION_MAX_AGENTS = 3           # agents assigned per quest
    _RESOLVE_PROGRESS_PER_AGENT = 0.25   # progress per cycle per assigned agent
    _VITALITY_OVERLOAD_THRESHOLD = 8     # unresolved quests before overload
    _MAX_SHIFTS_PER_REGION = 60
    _MAX_PRESSURES_PER_REGION = 100
    _MAX_QUESTS_PER_REGION = 60
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._regions: Dict[str, QuestRegion] = {}
        self._phase: QuestPhase = QuestPhase.SENSE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineEmergentQuestComposer":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    def _init_stats(self) -> None:
        self._stats = {
            "total_regions": 0,
            "total_shifts": 0,
            "total_propagated": 0,
            "total_crystalized": 0,
            "total_commissioned": 0,
            "total_resolved": 0,
            "total_abandoned": 0,
            "open_quests": 0,
            "avg_tension": 0.0,
            "avg_coherence": 0.0,
            "vitality": WorldVitality.DORMANT.value,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._regions:
            return
        tensions: List[float] = []
        coherences: List[float] = []
        open_quests = 0
        for region in self._regions.values():
            for quest in region.quests.values():
                if quest.state in (QuestState.CRYSTALIZED, QuestState.COMMISSIONED,
                                   QuestState.IN_PROGRESS):
                    open_quests += 1
                    tensions.append(quest.tension)
                    coherences.append(quest.coherence)
        self._stats["total_regions"] = len(self._regions)
        self._stats["open_quests"] = open_quests
        self._stats["avg_tension"] = (
            sum(tensions) / len(tensions) if tensions else 0.0
        )
        self._stats["avg_coherence"] = (
            sum(coherences) / len(coherences) if coherences else 0.0
        )
        # Derive overall vitality from open quests and resolution ratio.
        self._stats["vitality"] = self._derive_vitality().value

    def _derive_vitality(self) -> WorldVitality:
        open_quests = self._stats.get("open_quests", 0)
        resolved = self._stats.get("total_resolved", 0)
        abandoned = self._stats.get("total_abandoned", 0)
        total_finished = resolved + abandoned
        if open_quests >= self._VITALITY_OVERLOAD_THRESHOLD:
            return WorldVitality.OVERLOADED
        if total_finished > 0 and resolved / total_finished < 0.3:
            return WorldVitality.COLLAPSED
        if open_quests == 0 and total_finished == 0:
            return WorldVitality.DORMANT
        if open_quests > 0 and total_finished == 0:
            return WorldVitality.STIRRING
        return WorldVitality.FLOWING

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Region Management
    # -------------------------------------------------------------------------

    def register_region(self, region_id: str) -> Dict[str, Any]:
        """Register a new world region for emergent quest composition."""
        with self._global_lock:
            if region_id in self._regions:
                return {"error": f"Region already registered: {region_id}"}
            region = QuestRegion(region_id=region_id)
            self._regions[region_id] = region
            self._record_event("region_registered", {"region_id": region_id})
            return {
                "region_id": region_id,
                "pressure_total": region.pressure_total,
            }

    def remove_region(self, region_id: str) -> Dict[str, Any]:
        with self._global_lock:
            region = self._regions.pop(region_id, None)
            if region is None:
                return {"error": f"Region not found: {region_id}"}
            self._record_event("region_removed", {"region_id": region_id})
            return {
                "removed": region_id,
                "cleared_shifts": len(region.shifts),
                "cleared_pressures": len(region.pressures),
                "cleared_quests": len(region.quests),
            }

    # -------------------------------------------------------------------------
    # Shift Intake
    # -------------------------------------------------------------------------

    def sense_shift(self, region_id: str, shift_id: str, kind: ShiftKind,
                    magnitude: float = 0.5, note: str = "") -> Dict[str, Any]:
        """Sense a world shift in a region."""
        with self._global_lock:
            region = self._regions.get(region_id)
            if region is None:
                return {"error": f"Region not found: {region_id}"}
            # Reject duplicate shift ids within the region.
            if any(s.shift_id == shift_id for s in region.shifts):
                return {"error": f"Shift already exists: {shift_id}"}
            shift = WorldShift(
                shift_id=shift_id,
                region=region_id,
                kind=kind,
                magnitude=max(0.0, min(1.0, magnitude)),
                note=note,
            )
            region.shifts.append(shift)
            if len(region.shifts) > self._MAX_SHIFTS_PER_REGION:
                region.shifts = region.shifts[-self._MAX_SHIFTS_PER_REGION:]
            region.total_sensed += 1
            self._stats["total_shifts"] += 1
            self._record_event("shift_sensed", {
                "region_id": region_id,
                "shift_id": shift_id,
                "kind": kind.value,
                "magnitude": shift.magnitude,
            })
            return {
                "region_id": region_id,
                "shift_id": shift_id,
                "kind": kind.value,
                "magnitude": shift.magnitude,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single emergent quest cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = QuestPhase.SENSE
            phase_outputs["sense"] = self._phase_sense()
            self._phase = QuestPhase.PROPAGATE
            phase_outputs["propagate"] = self._phase_propagate()
            self._phase = QuestPhase.CRYSTALIZE
            phase_outputs["crystalize"] = self._phase_crystalize()
            self._phase = QuestPhase.COMMISSION
            phase_outputs["commission"] = self._phase_commission()
            self._phase = QuestPhase.RESOLVE
            phase_outputs["resolve"] = self._phase_resolve()
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
        """Sense phase: freshly sensed shifts are confirmed into region pressure."""
        sensed = 0
        for region in self._regions.values():
            for shift in region.shifts:
                # Only shifts not yet propagated contribute to base pressure.
                # We detect this by checking if any pressure cites this shift.
                already_propagated = any(
                    p.source_shift_id == shift.shift_id for p in region.pressures
                )
                if already_propagated:
                    continue
                # The shift adds its magnitude to the region's base pressure.
                region.pressure_total = min(
                    1.0, region.pressure_total + shift.magnitude * 0.3
                )
                sensed += 1
        self._record_event("phase_sense", {"sensed": sensed})
        return {"sensed": sensed}

    def _phase_propagate(self) -> Dict[str, Any]:
        """Propagate phase: shifts radiate outward as pressure."""
        propagated = 0
        for region in self._regions.values():
            new_pressures: List[PropagatedPressure] = []
            for shift in region.shifts:
                # Skip shifts that have already been propagated.
                if any(p.source_shift_id == shift.shift_id for p in region.pressures):
                    continue
                # Radiate to neighboring regions up to the hop cap.
                # Neighbors are the other regions in the world.
                neighbors = [r for r in self._regions if r != region.region_id]
                random.shuffle(neighbors)
                for hop in range(min(self._PROPAGATE_MAX_HOPS, len(neighbors))):
                    target = neighbors[hop]
                    intensity = shift.magnitude * (self._PROPAGATE_HOP_DECAY ** (hop + 1))
                    relation = self._classify_relation(shift, hop)
                    pressure = PropagatedPressure(
                        pressure_id=f"press_{shift.shift_id}_{target}_{self._cycle_count}",
                        source_shift_id=shift.shift_id,
                        target_region=target,
                        relation=relation,
                        intensity=max(0.0, min(1.0, intensity)),
                        distance=hop + 1,
                    )
                    new_pressures.append(pressure)
                    propagated += 1
                    # Also deposit the pressure into the target region.
                    target_region = self._regions.get(target)
                    if target_region is not None:
                        target_region.pressure_total = min(
                            1.0, target_region.pressure_total + pressure.intensity * 0.2
                        )
                        target_region.pressures.append(pressure)
                        if len(target_region.pressures) > self._MAX_PRESSURES_PER_REGION:
                            target_region.pressures = \
                                target_region.pressures[-self._MAX_PRESSURES_PER_REGION:]
            # Append locally sourced pressures too (the shift also pressures its own region).
            for shift in region.shifts:
                if any(p.source_shift_id == shift.shift_id and
                       p.target_region == region.region_id
                       for p in region.pressures):
                    continue
                local = PropagatedPressure(
                    pressure_id=f"press_{shift.shift_id}_{region.region_id}_local_{self._cycle_count}",
                    source_shift_id=shift.shift_id,
                    target_region=region.region_id,
                    relation=PressureRelation.STABILIZING,
                    intensity=max(0.0, min(1.0, shift.magnitude * 0.5)),
                    distance=0,
                )
                region.pressures.append(local)
                propagated += 1
            region.pressures.extend(new_pressures)
            if len(region.pressures) > self._MAX_PRESSURES_PER_REGION:
                region.pressures = region.pressures[-self._MAX_PRESSURES_PER_REGION:]
            region.total_propagated += propagated
        self._stats["total_propagated"] += propagated
        self._record_event("phase_propagate", {"propagated": propagated})
        return {"propagated": propagated}

    def _phase_crystalize(self) -> Dict[str, Any]:
        """Crystalize phase: pressure above threshold becomes a quest."""
        crystalized = 0
        for region in self._regions.values():
            # Aggregate pressure intensity per source shift in this region.
            shift_intensity: Dict[str, float] = {}
            for pressure in region.pressures:
                if pressure.target_region != region.region_id:
                    continue
                shift_intensity[pressure.source_shift_id] = (
                    shift_intensity.get(pressure.source_shift_id, 0.0)
                    + pressure.intensity
                )
            for shift_id, intensity in shift_intensity.items():
                if intensity < self._CRYSTALIZE_THRESHOLD:
                    continue
                # Skip if a quest already exists for this shift.
                if any(q.source_shift_id == shift_id for q in region.quests.values()):
                    continue
                shift = next((s for s in region.shifts if s.shift_id == shift_id), None)
                if shift is None:
                    continue
                shape = self._derive_shape(shift)
                quest = EmergentQuest(
                    quest_id=f"quest_{shift_id}_{self._cycle_count}",
                    source_shift_id=shift_id,
                    shape=shape,
                    region=region.region_id,
                    tension=max(0.0, min(1.0, intensity)),
                    coherence=self._derive_coherence(intensity, shift.magnitude),
                    state=QuestState.CRYSTALIZED,
                    note=self._quest_note(shape, shift),
                )
                region.quests[quest.quest_id] = quest
                if len(region.quests) > self._MAX_QUESTS_PER_REGION:
                    # Drop the oldest resolved or abandoned quest.
                    oldest_id = min(
                        region.quests,
                        key=lambda qid: region.quests[qid].created_at,
                    )
                    region.quests.pop(oldest_id, None)
                crystalized += 1
                region.total_crystalized += 1
        self._stats["total_crystalized"] += crystalized
        self._record_event("phase_crystalize", {"crystalized": crystalized})
        return {"crystalized": crystalized}

    def _phase_commission(self) -> Dict[str, Any]:
        """Commission phase: crystalized quests are handed to agents."""
        commissioned = 0
        for region in self._regions.values():
            for quest in region.quests.values():
                if quest.state != QuestState.CRYSTALIZED:
                    continue
                # Synthesize agent assignments based on the quest shape.
                agents = self._assign_agents(quest)
                quest.assigned_agents = agents
                quest.state = QuestState.COMMISSIONED
                region.total_commissioned += 1
                commissioned += 1
        self._stats["total_commissioned"] += commissioned
        self._record_event("phase_commission", {"commissioned": commissioned})
        return {"commissioned": commissioned}

    def _phase_resolve(self) -> Dict[str, Any]:
        """Resolve phase: commissioned quests accumulate progress toward resolution."""
        resolved = 0
        abandoned = 0
        for region in self._regions.values():
            for quest in list(region.quests.values()):
                if quest.state == QuestState.COMMISSIONED:
                    quest.state = QuestState.IN_PROGRESS
                if quest.state != QuestState.IN_PROGRESS:
                    continue
                # Each assigned agent contributes progress per cycle.
                progress = self._RESOLVE_PROGRESS_PER_AGENT * max(1, len(quest.assigned_agents))
                # Coherence multiplies how cleanly progress accrues.
                progress *= (0.5 + quest.coherence * 0.5)
                quest.resolution_pressure = min(1.0, quest.resolution_pressure + progress)
                if quest.resolution_pressure >= 1.0:
                    quest.state = QuestState.RESOLVED
                    quest.resolved_at = time.time()
                    region.total_resolved += 1
                    resolved += 1
                    # Resolution bleeds tension out of the region.
                    region.pressure_total = max(0.0, region.pressure_total - quest.tension * 0.3)
                else:
                    # Tension slowly fades if progress is slow, leading to abandonment.
                    quest.tension = max(0.0, quest.tension - 0.05)
                    if quest.tension <= 0.05:
                        quest.state = QuestState.ABANDONED
                        quest.resolved_at = time.time()
                        region.total_abandoned += 1
                        abandoned += 1
        self._stats["total_resolved"] += resolved
        self._stats["total_abandoned"] += abandoned
        self._record_event("phase_resolve", {
            "resolved": resolved,
            "abandoned": abandoned,
        })
        return {"resolved": resolved, "abandoned": abandoned}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _classify_relation(self, shift: WorldShift, hop: int) -> PressureRelation:
        """Classify how a shift's pressure relates to its propagation."""
        # Threats amplify as they travel; surpluses damp; opportunities reroute.
        if shift.kind == ShiftKind.THREAT:
            return PressureRelation.AMPLIFYING
        if shift.kind == ShiftKind.SURPLUS:
            return PressureRelation.DAMPING
        if shift.kind == ShiftKind.OPPORTUNITY:
            return PressureRelation.REROUTING
        # Shortages and grievances stabilize over distance.
        return PressureRelation.STABILIZING

    def _derive_shape(self, shift: WorldShift) -> QuestShape:
        """Derive the shape a crystalized quest should take from its source shift."""
        mapping = {
            ShiftKind.SHORTAGE: QuestShape.FETCH,
            ShiftKind.SURPLUS: QuestShape.ESCORT,
            ShiftKind.DEBT: QuestShape.MEDIATE,
            ShiftKind.GRIEVANCE: QuestShape.MEDIATE,
            ShiftKind.OPPORTUNITY: QuestShape.DISCOVER,
            ShiftKind.THREAT: QuestShape.ELIMINATE,
        }
        # Repair covers shifts that broke something rather than introduced a new thing.
        if shift.kind in (ShiftKind.SHORTAGE, ShiftKind.THREAT) and shift.magnitude > 0.7:
            return QuestShape.REPAIR
        return mapping.get(shift.kind, QuestShape.DISCOVER)

    def _derive_coherence(self, intensity: float, magnitude: float) -> float:
        """Derive how well-formed a crystalized quest is."""
        # Coherence rises when intensity and magnitude agree.
        agreement = 1.0 - abs(intensity - magnitude)
        return max(0.0, min(1.0, 0.4 + agreement * 0.5))

    def _assign_agents(self, quest: EmergentQuest) -> List[str]:
        """Synthesize agent assignments for a quest based on its shape."""
        # Each shape prefers a different agent roster.
        rosters = {
            QuestShape.FETCH: ["sim_courier", "sim_scout"],
            QuestShape.ESCORT: ["sim_guardian", "sim_courier"],
            QuestShape.MEDIATE: ["sim_diplomat"],
            QuestShape.ELIMINATE: ["sim_guardian", "sim_hunter"],
            QuestShape.REPAIR: ["sim_builder"],
            QuestShape.DISCOVER: ["sim_scout", "sim_scholar"],
        }
        roster = rosters.get(quest.shape, ["sim_courier"])
        return roster[:self._COMMISSION_MAX_AGENTS]

    def _quest_note(self, shape: QuestShape, shift: WorldShift) -> str:
        """Compose a short note describing the crystalized quest."""
        return f"a {shape.value} quest grown from a {shift.kind.value} in {shift.region}"

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_region_state(self, region_id: str) -> Dict[str, Any]:
        with self._global_lock:
            region = self._regions.get(region_id)
            if region is None:
                return {"error": f"Region not found: {region_id}"}
            return {
                "region_id": region_id,
                "pressure_total": region.pressure_total,
                "shifts_count": len(region.shifts),
                "pressures_count": len(region.pressures),
                "quests_count": len(region.quests),
                "total_sensed": region.total_sensed,
                "total_propagated": region.total_propagated,
                "total_crystalized": region.total_crystalized,
                "total_commissioned": region.total_commissioned,
                "total_resolved": region.total_resolved,
                "total_abandoned": region.total_abandoned,
            }

    def get_quest(self, region_id: str, quest_id: str) -> Dict[str, Any]:
        with self._global_lock:
            region = self._regions.get(region_id)
            if region is None:
                return {"error": f"Region not found: {region_id}"}
            quest = region.quests.get(quest_id)
            if quest is None:
                return {"error": f"Quest not found: {quest_id}"}
            return {
                "quest_id": quest.quest_id,
                "source_shift_id": quest.source_shift_id,
                "shape": quest.shape.value,
                "region": quest.region,
                "tension": quest.tension,
                "coherence": quest.coherence,
                "assigned_agents": quest.assigned_agents,
                "resolution_pressure": quest.resolution_pressure,
                "state": quest.state.value,
                "created_at": quest.created_at,
                "resolved_at": quest.resolved_at,
                "note": quest.note,
            }

    def get_quests(self, region_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            region = self._regions.get(region_id)
            if region is None:
                return {"error": f"Region not found: {region_id}"}
            quests = sorted(
                region.quests.values(),
                key=lambda q: q.created_at,
                reverse=True,
            )[:limit]
            return {
                "region_id": region_id,
                "quests": [
                    {
                        "quest_id": q.quest_id,
                        "shape": q.shape.value,
                        "state": q.state.value,
                        "tension": q.tension,
                        "coherence": q.coherence,
                        "assigned_agents": q.assigned_agents,
                    }
                    for q in quests
                ],
            }

    def get_pressures(self, region_id: str, limit: int = 30) -> Dict[str, Any]:
        with self._global_lock:
            region = self._regions.get(region_id)
            if region is None:
                return {"error": f"Region not found: {region_id}"}
            pressures = region.pressures[-limit:]
            return {
                "region_id": region_id,
                "pressures": [
                    {
                        "pressure_id": p.pressure_id,
                        "source_shift_id": p.source_shift_id,
                        "target_region": p.target_region,
                        "relation": p.relation.value,
                        "intensity": p.intensity,
                        "distance": p.distance,
                    }
                    for p in pressures
                ],
            }

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "regions": len(self._regions),
                "stats": dict(self._stats),
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic regions and shifts, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_regions()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_regions(self) -> None:
        """Seed a small synthetic world with distinct regions and shifts."""
        seed_regions = ["sim_frontier", "sim_capital", "sim_border"]
        for region_id in seed_regions:
            if region_id not in self._regions:
                self.register_region(region_id)
        # Seed shifts across regions.
        seed_shifts = [
            ("sim_frontier", "sim_s1", ShiftKind.THREAT, 0.7, "raiders sighted"),
            ("sim_frontier", "sim_s2", ShiftKind.OPPORTUNITY, 0.5, "a ruin exposed"),
            ("sim_capital", "sim_s3", ShiftKind.SHORTAGE, 0.6, "grain running low"),
            ("sim_capital", "sim_s4", ShiftKind.GRIEVANCE, 0.4, "a faction snubbed"),
            ("sim_border", "sim_s5", ShiftKind.DEBT, 0.5, "a treaty coming due"),
            ("sim_border", "sim_s6", ShiftKind.SURPLUS, 0.3, "a harvest surplus"),
        ]
        for region_id, shift_id, kind, magnitude, note in seed_shifts:
            region = self._regions.get(region_id)
            if region is None:
                continue
            if not any(s.shift_id == shift_id for s in region.shifts):
                self.sense_shift(region_id, shift_id, kind, magnitude=magnitude, note=note)

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._regions.clear()
            self._events_log.clear()
            self._phase = QuestPhase.SENSE
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
