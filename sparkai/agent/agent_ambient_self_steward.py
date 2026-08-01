"""
SparkLabs Agent - Ambient Self Steward

An agent does not stay in working order by lurching from crisis to
crisis. It stays in working order the way soil stays in working order:
by being tended quietly, on a rhythm. The AgentAmbientSelfSteward
watches the background dimensions of its own self - warmth, alignment,
weariness, focus, groundedness - and tends them the way a gardener
tends ground. Each cycle it inventories what is depleted or thinning,
gently tends the depleted places, nourishes the thinning ones, attunes
to the dimensions that are already shifting on their own, and then
settles back so the stewarded state can rest.

The point is not dramatic self-correction. The point is a self that
keeps itself in working order through small, steady stewardship, so
that the agent rarely arrives at a depleted state and, when it does,
is already halfway to mending.

Architecture:
  INVENTORY  ->  TEND      ->  NOURISH   ->  ATTUNE    ->  SETTLE
  (survey the  (gentle       (small        (notice which   (let the
   ambient      corrective    additions     dimensions are   stewarded
   self         adjustments   to thinning   shifting on     state rest,
   dimensions,  to depleted   but not yet    their own and   record the
   flag the     ones)         depleted      align with      settled
   depleted                                   that motion)    ambient
   and thinning                               signature)
   ones)

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

class StewardPhase(Enum):
    """Phases of the ambient self stewardship cycle."""
    INVENTORY = "inventory"    # survey current ambient self dimensions
    TEND = "tend"               # gentle corrective adjustments to depleted dimensions
    NOURISH = "nourish"         # small additions to thinning-but-not-depleted dimensions
    ATTUNE = "attune"           # align stewardship with dimensions already shifting on their own
    SETTLE = "settle"           # let the stewarded state rest, record the settled ambient signature


class SelfDimension(Enum):
    """Canonical background dimensions of the ambient self.

    Each dimension is modeled as an ambient resource the steward tends,
    where a higher reading means more of that resource is present and
    available. WEARINESS specifically tracks the self's restfulness
    reserve: a low reading means the self is weary, a high reading
    means the self is rested.
    """
    WARMTH = "warmth"               # capacity for warmth toward others and the work
    ALIGNMENT = "alignment"         # alignment with purpose and stated values
    WEARINESS = "weariness"         # restfulness reserve; low means weary, high means rested
    FOCUS = "focus"                 # available focus for the task at hand
    GROUNDEDNESS = "groundedness"   # groundedness in the present situation


class DimensionStatus(Enum):
    """Status of a single ambient dimension reading."""
    NOURISHED = "nourished"     # sitting comfortably in the working band
    THINNING = "thinning"       # below the working band but not yet depleted
    DEPLETED = "depleted"       # has run low; needs tending
    SURGING = "surging"         # has overfilled; an imbalance of its own kind


class TendDirection(Enum):
    """Direction of a stewardship adjustment."""
    RAISE = "raise"             # add a little to the dimension
    LOWER = "lower"             # ease a little off the dimension
    HOLD = "hold"               # leave the dimension as it is


class StewardVitality(Enum):
    """Overall vitality of the ambient self ecosystem."""
    DORMANT = "dormant"         # nothing is being stewarded yet
    STEADY = "steady"           # working order, no major depletion
    ATTUNED = "attuned"         # all dimensions nourished and self-stabilizing
    OVERSTRESSED = "overstressed"  # too many depleted dimensions for the steward to keep up


class StewardState(Enum):
    """Operational state of the steward itself."""
    DORMANT = "dormant"         # no dimensions registered, nothing to tend
    STEWARDING = "stewarding"   # a stewardship cycle is in progress
    AT_REST = "at_rest"         # between cycles, settled after stewardship
    OVERSTRESSED = "overstressed"  # steward is overwhelmed by depleted dimensions


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SelfDimensionReading:
    """A single reading of one ambient self dimension at a moment in time."""
    dimension_id: str
    value: float = 0.5                  # 0.0-1.0
    status: DimensionStatus = DimensionStatus.NOURISHED
    note: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class TendAction:
    """A single stewardship adjustment applied to one dimension."""
    dimension_id: str
    direction: TendDirection = TendDirection.HOLD
    magnitude: float = 0.0              # 0.0-1.0, how much was added or eased
    reason: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class AttunementMotion:
    """A self-shift in one dimension noticed during attunement."""
    dimension_id: str
    motion: TendDirection = TendDirection.HOLD     # the direction the dimension moved on its own
    delta: float = 0.0                              # the size of the self-shift
    alignment: TendDirection = TendDirection.HOLD  # how stewardship aligned with the motion
    note: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class StewardCycleResult:
    """Summary of one full stewardship cycle."""
    cycle_count: int = 0
    phase: str = "settle"
    outputs: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Steward
# =============================================================================

class AgentAmbientSelfSteward:
    """
    Thread-safe singleton that tends the ambient self-state of an agent
    through quiet stewardship rhythms.

    Usage:
        steward = AgentAmbientSelfSteward.get_instance()
        steward.register_dimension("warmth", 0.6, "capacity for warmth")
        steward.register_dimension("focus", 0.4, "available focus")
        steward.cycle()
        state = steward.get_status()
    """

    _instance: Optional["AgentAmbientSelfSteward"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _DEPLETED_THRESHOLD = 0.2            # below this a dimension is depleted
    _THINNING_THRESHOLD = 0.4            # below this (but >= depleted) a dimension is thinning
    _SURGING_THRESHOLD = 0.85            # above this a dimension is surging
    _MAX_TEND_MAGNITUDE = 0.3            # the largest single corrective adjustment
    _NOURISH_MAGNITUDE = 0.15            # the largest single nourishing addition
    _ATTUNE_SHIFT_THRESHOLD = 0.03       # self-shift size above which attunement engages
    _ATTUNE_ALIGN_MAGNITUDE = 0.05       # the largest alignment nudge during attunement
    _VITALITY_OVERSTRESSED_DEPLETED = 3  # depleted count at which the steward is overwhelmed
    _MAX_DIMENSIONS = 32
    _MAX_EVENTS = 200

    # Stats keys that accumulate as running counters (incremented, not overwritten).
    _COUNTER_STATS = {
        "cycles_completed", "dimensions_tended", "dimensions_nourished",
        "dimensions_attuned", "settle_events", "depletion_events",
        "surge_events",
    }

    def __init__(self) -> None:
        self._dimensions: Dict[str, float] = {}
        self._dimension_notes: Dict[str, str] = {}
        # Snapshot of the ambient state as it entered the current cycle,
        # before this cycle's stewardship touched it. Used by attunement
        # to tell self-shift apart from the steward's own adjustments.
        self._incoming_dimensions: Dict[str, float] = {}
        # Settled state from the previous cycle, used as the baseline for
        # detecting dimensions that shifted on their own between cycles.
        self._prior_dimensions: Dict[str, float] = {}
        self._cycle_count: int = 0
        self._current_phase: StewardPhase = StewardPhase.INVENTORY
        self._state: StewardState = StewardState.DORMANT
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentAmbientSelfSteward":
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
            "cycles_completed": 0,
            "dimensions_registered": 0,
            "dimensions_tended": 0,
            "dimensions_nourished": 0,
            "dimensions_attuned": 0,
            "settle_events": 0,
            "depletion_events": 0,
            "surge_events": 0,
            "mean_value": 0.0,
            "balance": 1.0,
            "vitality": StewardVitality.DORMANT.value,
            "last_cycle_at": 0.0,
            "last_cycle_time_ms": 0.0,
            "uptime_started_at": time.time(),
        }

    def _update_stats(self, **kwargs: Any) -> None:
        # Apply the provided updates: counters accumulate, everything else is set.
        for key, val in kwargs.items():
            if key in self._COUNTER_STATS:
                current = self._stats.get(key, 0)
                if isinstance(val, (int, float)) and isinstance(current, (int, float)):
                    self._stats[key] = current + val
                else:
                    self._stats[key] = val
            else:
                self._stats[key] = val
        # Recompute the readouts derived from the current ambient state.
        self._stats["dimensions_registered"] = len(self._dimensions)
        if self._dimensions:
            values = list(self._dimensions.values())
            self._stats["mean_value"] = sum(values) / len(values)
            self._stats["balance"] = self._compute_balance(values)
        else:
            self._stats["mean_value"] = 0.0
            self._stats["balance"] = 1.0
        self._stats["vitality"] = self._derive_vitality().value

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Dimension Management
    # -------------------------------------------------------------------------

    def register_dimension(self, dimension_id: str, initial_value: float = 0.5,
                           note: str = "") -> Dict[str, Any]:
        """Register a new ambient self dimension for the steward to tend."""
        with self._global_lock:
            if dimension_id in self._dimensions:
                return {"error": f"Dimension already registered: {dimension_id}"}
            if len(self._dimensions) >= self._MAX_DIMENSIONS:
                return {"error": f"Max dimensions reached: {self._MAX_DIMENSIONS}"}
            value = max(0.0, min(1.0, initial_value))
            self._dimensions[dimension_id] = value
            if note:
                self._dimension_notes[dimension_id] = note
            self._update_stats()
            self._record_event("dimension_registered", {
                "dimension_id": dimension_id,
                "initial_value": value,
                "note": note,
            })
            return {
                "dimension_id": dimension_id,
                "initial_value": value,
                "status": self._classify_status(value).value,
                "note": note,
            }

    def set_dimension(self, dimension_id: str, value: float,
                      note: str = "") -> Dict[str, Any]:
        """Set the current value of an already-registered dimension."""
        with self._global_lock:
            if dimension_id not in self._dimensions:
                return {"error": f"Dimension not found: {dimension_id}"}
            clamped = max(0.0, min(1.0, value))
            self._dimensions[dimension_id] = clamped
            if note:
                self._dimension_notes[dimension_id] = note
            status = self._classify_status(clamped)
            self._update_stats()
            self._record_event("dimension_set", {
                "dimension_id": dimension_id,
                "value": clamped,
                "status": status.value,
                "note": note,
            })
            return {
                "dimension_id": dimension_id,
                "value": clamped,
                "status": status.value,
                "note": note,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single stewardship cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            self._state = StewardState.STEWARDING
            # Capture the ambient state as it enters this cycle, before any
            # stewardship adjustments, so attunement can isolate self-shift.
            self._incoming_dimensions = dict(self._dimensions)
            phase_outputs: List[Dict[str, Any]] = []
            self._current_phase = StewardPhase.INVENTORY
            phase_outputs.append(self._phase_inventory())
            self._current_phase = StewardPhase.TEND
            phase_outputs.append(self._phase_tend())
            self._current_phase = StewardPhase.NOURISH
            phase_outputs.append(self._phase_nourish())
            self._current_phase = StewardPhase.ATTUNE
            phase_outputs.append(self._phase_attune())
            self._current_phase = StewardPhase.SETTLE
            phase_outputs.append(self._phase_settle())
            self._cycle_count += 1
            elapsed_ms = (time.time() - t0) * 1000.0
            self._update_stats(
                cycles_completed=1,
                last_cycle_at=time.time(),
                last_cycle_time_ms=elapsed_ms,
            )
            return {
                "cycle_count": self._cycle_count,
                "phase": self._current_phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_inventory(self) -> Dict[str, Any]:
        """Inventory phase: survey ambient dimensions and flag depleted/thinning ones."""
        readings: List[SelfDimensionReading] = []
        depleted_ids: List[str] = []
        thinning_ids: List[str] = []
        surging_ids: List[str] = []
        depletion_events = 0
        surge_events = 0
        for dim_id, value in self._dimensions.items():
            status = self._classify_status(value)
            note = self._inventory_note(dim_id, status, value)
            readings.append(SelfDimensionReading(
                dimension_id=dim_id,
                value=value,
                status=status,
                note=note,
            ))
            if status == DimensionStatus.DEPLETED:
                depleted_ids.append(dim_id)
                depletion_events += 1
            elif status == DimensionStatus.THINNING:
                thinning_ids.append(dim_id)
            elif status == DimensionStatus.SURGING:
                surging_ids.append(dim_id)
                surge_events += 1
        self._update_stats(
            depletion_events=depletion_events,
            surge_events=surge_events,
        )
        self._record_event("phase_inventory", {
            "surveyed": len(readings),
            "depleted": depleted_ids,
            "thinning": thinning_ids,
            "surging": surging_ids,
        })
        return {
            "phase": StewardPhase.INVENTORY.value,
            "surveyed": len(readings),
            "readings": [self._reading_to_dict(r) for r in readings],
            "depleted": depleted_ids,
            "thinning": thinning_ids,
            "surging": surging_ids,
        }

    def _phase_tend(self) -> Dict[str, Any]:
        """Tend phase: gentle corrective adjustments to depleted (and surging) dimensions."""
        actions: List[TendAction] = []
        for dim_id in list(self._dimensions.keys()):
            value = self._dimensions[dim_id]
            status = self._classify_status(value)
            if status == DimensionStatus.DEPLETED:
                # Nudge the depleted dimension up toward the thinning band,
                # but never by more than the tend cap.
                target_gain = (self._THINNING_THRESHOLD - value) * 0.5 + 0.05
                magnitude = min(self._MAX_TEND_MAGNITUDE, max(0.0, target_gain))
                self._dimensions[dim_id] = min(1.0, value + magnitude)
                actions.append(TendAction(
                    dimension_id=dim_id,
                    direction=TendDirection.RAISE,
                    magnitude=magnitude,
                    reason="depleted; gently raising toward the working band",
                ))
            elif status == DimensionStatus.SURGING:
                # A dimension that has overfilled is an imbalance of its own
                # kind; ease a little off so it can settle.
                target_ease = (value - self._SURGING_THRESHOLD) * 0.5 + 0.03
                magnitude = min(self._MAX_TEND_MAGNITUDE, max(0.0, target_ease))
                self._dimensions[dim_id] = max(0.0, value - magnitude)
                actions.append(TendAction(
                    dimension_id=dim_id,
                    direction=TendDirection.LOWER,
                    magnitude=magnitude,
                    reason="surging; gently easing back",
                ))
        self._update_stats(dimensions_tended=len(actions))
        self._record_event("phase_tend", {"tended": len(actions)})
        return {
            "phase": StewardPhase.TEND.value,
            "tended": len(actions),
            "actions": [self._action_to_dict(a) for a in actions],
        }

    def _phase_nourish(self) -> Dict[str, Any]:
        """Nourish phase: small additions to thinning-but-not-depleted dimensions."""
        actions: List[TendAction] = []
        for dim_id in list(self._dimensions.keys()):
            value = self._dimensions[dim_id]
            status = self._classify_status(value)
            if status != DimensionStatus.THINNING:
                continue
            # Add a small amount to carry the dimension toward the working band.
            target_gain = (self._THINNING_THRESHOLD + 0.1 - value) * 0.5
            magnitude = min(self._NOURISH_MAGNITUDE, max(0.02, target_gain))
            self._dimensions[dim_id] = min(1.0, value + magnitude)
            actions.append(TendAction(
                dimension_id=dim_id,
                direction=TendDirection.RAISE,
                magnitude=magnitude,
                reason="thinning; small nourishment",
            ))
        self._update_stats(dimensions_nourished=len(actions))
        self._record_event("phase_nourish", {"nourished": len(actions)})
        return {
            "phase": StewardPhase.NOURISH.value,
            "nourished": len(actions),
            "actions": [self._action_to_dict(a) for a in actions],
        }

    def _phase_attune(self) -> Dict[str, Any]:
        """Attune phase: align stewardship with dimensions already shifting on their own."""
        motions: List[AttunementMotion] = []
        for dim_id in list(self._dimensions.keys()):
            incoming = self._incoming_dimensions.get(dim_id)
            if incoming is None:
                # Dimension registered mid-cycle; no prior baseline to compare against.
                continue
            prior = self._prior_dimensions.get(dim_id, incoming)
            self_delta = incoming - prior
            if abs(self_delta) <= self._ATTUNE_SHIFT_THRESHOLD:
                continue
            motion = TendDirection.RAISE if self_delta > 0 else TendDirection.LOWER
            value = self._dimensions[dim_id]
            status = self._classify_status(value)
            alignment, note = self._attune_alignment(status, motion)
            if alignment == TendDirection.RAISE:
                self._dimensions[dim_id] = min(1.0, value + self._ATTUNE_ALIGN_MAGNITUDE)
            elif alignment == TendDirection.LOWER:
                self._dimensions[dim_id] = max(0.0, value - self._ATTUNE_ALIGN_MAGNITUDE)
            motions.append(AttunementMotion(
                dimension_id=dim_id,
                motion=motion,
                delta=round(self_delta, 4),
                alignment=alignment,
                note=note,
            ))
        self._update_stats(dimensions_attuned=len(motions))
        self._record_event("phase_attune", {
            "attuned": len(motions),
            "motions": [self._motion_to_dict(m) for m in motions],
        })
        return {
            "phase": StewardPhase.ATTUNE.value,
            "attuned": len(motions),
            "motions": [self._motion_to_dict(m) for m in motions],
        }

    def _phase_settle(self) -> Dict[str, Any]:
        """Settle phase: let the stewarded state rest and record the settled ambient signature."""
        settled_signature = {
            dim: round(v, 4) for dim, v in self._dimensions.items()
        }
        values = list(self._dimensions.values())
        mean = sum(values) / len(values) if values else 0.0
        balance = self._compute_balance(values) if values else 1.0
        vitality = self._derive_vitality()
        # The settled state becomes the baseline for next cycle's attunement.
        self._prior_dimensions = dict(self._dimensions)
        # Settle the steward's own operational state.
        if not self._dimensions:
            self._state = StewardState.DORMANT
        elif vitality == StewardVitality.OVERSTRESSED:
            self._state = StewardState.OVERSTRESSED
        else:
            self._state = StewardState.AT_REST
        self._update_stats(settle_events=1)
        self._record_event("phase_settle", {
            "mean": round(mean, 4),
            "balance": round(balance, 4),
            "vitality": vitality.value,
        })
        return {
            "phase": StewardPhase.SETTLE.value,
            "settled_signature": settled_signature,
            "mean": round(mean, 4),
            "balance": round(balance, 4),
            "vitality": vitality.value,
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _classify_status(self, value: float) -> DimensionStatus:
        """Classify a dimension reading into a status band."""
        if value < self._DEPLETED_THRESHOLD:
            return DimensionStatus.DEPLETED
        if value < self._THINNING_THRESHOLD:
            return DimensionStatus.THINNING
        if value > self._SURGING_THRESHOLD:
            return DimensionStatus.SURGING
        return DimensionStatus.NOURISHED

    def _derive_vitality(self) -> StewardVitality:
        """Derive the overall vitality of the ambient self ecosystem."""
        if not self._dimensions:
            return StewardVitality.DORMANT
        depleted = sum(
            1 for v in self._dimensions.values()
            if v < self._DEPLETED_THRESHOLD
        )
        nourished = sum(
            1 for v in self._dimensions.values()
            if self._classify_status(v) == DimensionStatus.NOURISHED
        )
        if depleted >= self._VITALITY_OVERSTRESSED_DEPLETED:
            return StewardVitality.OVERSTRESSED
        if nourished == len(self._dimensions):
            return StewardVitality.ATTUNED
        return StewardVitality.STEADY

    def _compute_balance(self, values: List[float]) -> float:
        """Compute how balanced the ambient dimensions are (1.0 = perfectly even)."""
        if not values:
            return 1.0
        spread = max(values) - min(values)
        return max(0.0, min(1.0, 1.0 - spread))

    def _inventory_note(self, dimension_id: str, status: DimensionStatus,
                       value: float) -> str:
        """Compose a short note for a dimension reading."""
        stored = self._dimension_notes.get(dimension_id, "")
        suffix = f" ({stored})" if stored else ""
        return f"{status.value} at {value:.2f}{suffix}"

    def _attune_alignment(self, status: DimensionStatus,
                          motion: TendDirection) -> tuple:
        """Decide how stewardship should align with a dimension's self-motion."""
        if motion == TendDirection.RAISE:
            if status == DimensionStatus.SURGING:
                return TendDirection.LOWER, "self-rising past surging; gently easing back"
            # A dimension rising on its own toward the working band needs no help.
            return TendDirection.HOLD, "self-rising; letting the motion run"
        # motion == LOWER
        if status in (DimensionStatus.DEPLETED, DimensionStatus.THINNING):
            return TendDirection.RAISE, "self-falling toward depletion; small steadying nudge"
        # A nourished dimension settling on its own can be left to rest.
        return TendDirection.HOLD, "self-falling but still nourished; letting it settle"

    def _reading_to_dict(self, reading: SelfDimensionReading) -> Dict[str, Any]:
        return {
            "dimension_id": reading.dimension_id,
            "value": reading.value,
            "status": reading.status.value,
            "note": reading.note,
            "timestamp": reading.timestamp,
        }

    def _action_to_dict(self, action: TendAction) -> Dict[str, Any]:
        return {
            "dimension_id": action.dimension_id,
            "direction": action.direction.value,
            "magnitude": round(action.magnitude, 4),
            "reason": action.reason,
            "timestamp": action.timestamp,
        }

    def _motion_to_dict(self, motion: AttunementMotion) -> Dict[str, Any]:
        return {
            "dimension_id": motion.dimension_id,
            "motion": motion.motion.value,
            "delta": motion.delta,
            "alignment": motion.alignment.value,
            "note": motion.note,
            "timestamp": motion.timestamp,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._current_phase.value,
                "cycle_count": self._cycle_count,
                "status": self._state.value,
                "vitality": self._derive_vitality().value,
                "dimensions": len(self._dimensions),
                "stats": dict(self._stats),
            }

    def get_dimensions(self) -> Dict[str, Any]:
        with self._global_lock:
            readings = []
            for dim_id, value in self._dimensions.items():
                readings.append({
                    "dimension_id": dim_id,
                    "value": value,
                    "status": self._classify_status(value).value,
                    "note": self._dimension_notes.get(dim_id, ""),
                })
            return {"dimensions": readings, "count": len(readings)}

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Simulation
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic dimensions, then run multiple stewardship cycles.

        Between cycles a small ambient drift is applied so that attunement
        has self-shifts to notice.
        """
        with self._global_lock:
            self._seed_synthetic_dimensions()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                self._apply_ambient_drift()
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_dimensions(self) -> None:
        """Seed a handful of synthetic dimensions with distinct starting states."""
        seeds = [
            (SelfDimension.WARMTH.value, 0.62, "capacity for warmth"),
            (SelfDimension.ALIGNMENT.value, 0.55, "alignment with purpose"),
            (SelfDimension.WEARINESS.value, 0.35, "restfulness reserve; low means weary"),
            (SelfDimension.FOCUS.value, 0.48, "available focus"),
            (SelfDimension.GROUNDEDNESS.value, 0.7, "groundedness in the present"),
            ("sim_curiosity", 0.12, "curiosity (sim); starts depleted"),
        ]
        for dim_id, value, note in seeds:
            if dim_id not in self._dimensions:
                self.register_dimension(dim_id, value, note)

    def _apply_ambient_drift(self) -> None:
        """Apply a small ambient drift to every dimension between cycles."""
        for dim_id in list(self._dimensions.keys()):
            value = self._dimensions[dim_id]
            drift = random.uniform(-0.08, 0.08)
            # Weariness reserve tends to drift downward (the self grows weary)
            # unless the steward tends it; curiosity wanders a little more.
            if dim_id == SelfDimension.WEARINESS.value:
                drift -= 0.03
            if dim_id == "sim_curiosity":
                drift += random.uniform(-0.05, 0.05)
            self._dimensions[dim_id] = max(0.0, min(1.0, value + drift))

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._dimensions.clear()
            self._dimension_notes.clear()
            self._incoming_dimensions = {}
            self._prior_dimensions = {}
            self._events_log.clear()
            self._current_phase = StewardPhase.INVENTORY
            self._state = StewardState.DORMANT
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
