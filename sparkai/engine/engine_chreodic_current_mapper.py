"""
SparkLabs Engine - Chreodic Current Mapper"""

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

class ChreodicPhase(Enum):
    """Phases of the chreodic current mapping cycle."""
    REGISTER_TRANSITION = "register_transition"        # register state-transition events observed in the world
    CARVE_GROOVE = "carve_groove"                      # deepen chreode grooves; pioneer new grooves for novel transitions
    COMPUTE_CURRENT_BIAS = "compute_current_bias"      # compute flow biases from groove depth
    RENDER_FLOW_LINES = "render_flow_lines"            # render editor flow lines per chreode (thickness = groove depth)
    EMIT_CHREODIC_MAP = "emit_chreodic_map"            # emit the full chreodic map with grooves, biases, flow lines


class TransitionKind(Enum):
    """The kind of state transition observed."""
    STATE_CHANGE = "state_change"          # generic state change
    LOCATION_SHIFT = "location_shift"      # entity moves between locations
    ATTRIBUTE_DRIFT = "attribute_drift"    # property value drifts
    INTENT_SHIFT = "intent_shift"          # NPC intent changes
    RELATION_CHANGE = "relation_change"    # relation between entities changes


class GrooveOrigin(Enum):
    """How a chreode groove came into being."""
    PIONEERED = "pioneered"      # newly carved for a novel transition
    REINFORCED = "reinforced"    # existing groove, transition repeated
    DEEPENED = "deepened"        # groove crossed a depth threshold
    MERGED = "merged"            # two grooves merged into one
    DECAYED = "decayed"          # groove depth eroded over time


class CurrentBiasMode(Enum):
    """How a groove biases nearby state space."""
    ATTRACT = "attract"          # pulls nearby transitions toward the groove
    REPEL = "repel"              # pushes nearby transitions away
    NEUTRAL = "neutral"          # no bias yet
    VORTEX = "vortex"            # strong attractor, captures nearby transitions
    LAMINAR = "laminar"          # smooth parallel flow, low bias


class FlowLineState(Enum):
    """State of an individual chreodic flow line."""
    REGISTERED = "registered"    # transition registered, groove not yet carved
    CARVED = "carved"            # groove carved / deepened
    BIASED = "biased"            # current bias computed
    RENDERED = "rendered"        # flow line rendered with thickness
    EMITTED = "emitted"          # flow line emitted in chreodic map


class Vitality(Enum):
    """Overall vitality of the chreodic ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    FLOWING = "flowing"
    SURGING = "surging"
    SATURATED = "saturated"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TransitionEvent:
    """A single observed state-transition event."""
    event_id: str
    source_state: str
    target_state: str
    label: str = ""
    kind: TransitionKind = TransitionKind.STATE_CHANGE
    weight: float = 1.0           # how strongly this transition was observed
    observed_at: float = field(default_factory=time.time)


@dataclass
class ChreodeGroove:
    """A chreode groove: a deepened pathway between two states."""
    groove_id: str
    transition_signature: str     # canonical "source->target" key (natural key)
    source_state: str
    target_state: str
    depth: float = 0.0            # 0.0-1.0, how deep the groove is
    transition_count: int = 0
    origin: GrooveOrigin = GrooveOrigin.PIONEERED
    flow_bias: CurrentBiasMode = CurrentBiasMode.NEUTRAL
    bias_strength: float = 0.0    # 0.0-1.0
    thickness: float = 0.0        # rendered thickness, derived from depth
    state: FlowLineState = FlowLineState.REGISTERED
    vitality: Vitality = Vitality.DORMANT
    created_at: float = field(default_factory=time.time)
    last_carved_at: float = 0.0
    last_rendered_at: float = 0.0
    note: str = ""


# =============================================================================
# Mapper
# =============================================================================

class ChreodicCurrentMapper:
    """
    Thread-safe singleton that maps chreodic currents in world state.

    Chreode grooves are keyed internally by transition_signature (the
    canonical "source->target" string) so that each transition pathway
    owns exactly one groove. The groove_id is a generated handle for
    external lookups; lookups by groove_id fall back to a linear scan
    of the registered grooves.

    Usage:
        mapper = ChreodicCurrentMapper.get_instance()
        mapper.register_transition(
            source_state="calm",
            target_state="alert",
            label="calm->alert",
        )
        mapper.cycle()
        groove = mapper.get_groove(groove_id)
    """

    _instance: Optional["ChreodicCurrentMapper"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Capacity caps.
    _MAX_GROOVES = 60
    _MAX_EVENTS = 200
    _MAX_PENDING_TRANSITIONS = 40

    # Domain tuning constants.
    _CARVE_INCREMENT = 0.12        # depth added per unit reinforcement weight
    _PIONEER_DEPTH = 0.1           # starting depth for a newly pioneered groove
    _DECAY_PER_CYCLE = 0.02        # depth eroded per cycle (entropy on idle grooves)
    _DEEPEN_THRESHOLD = 0.6        # depth above which origin becomes DEEPENED
    _VORTEX_THRESHOLD = 0.8        # depth above which bias becomes VORTEX
    _ATTRACT_THRESHOLD = 0.3       # depth above which bias becomes ATTRACT
    _LAMINAR_THRESHOLD = 0.15      # depth above which bias becomes LAMINAR
    _THICKNESS_SCALE = 8.0         # max rendered line thickness in editor units
    _VITALITY_SURGING_FRACTION = 0.6
    _VITALITY_SATURATED_FRACTION = 0.9

    def __init__(self) -> None:
        # Internal dict keyed by transition_signature (NOT groove_id).
        self._grooves: Dict[str, ChreodeGroove] = {}
        # Pending transition events queued by register_transition(); consumed by REGISTER_TRANSITION phase.
        self._pending_transitions: Deque[TransitionEvent] = deque(maxlen=self._MAX_PENDING_TRANSITIONS)
        # Accumulated carve weights per signature, populated by REGISTER_TRANSITION, consumed by CARVE_GROOVE.
        self._pending_carves: Dict[str, float] = {}
        self._phase: ChreodicPhase = ChreodicPhase.REGISTER_TRANSITION
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        # Seed synthetic data so simulate() works without an external API.
        if not self._grooves:
            self._seed_synthetic_grooves()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "ChreodicCurrentMapper":
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
            "uptime_started_at": time.time(),
            "transitions_registered": 0,
            "grooves_registered": 0,
            "phase_runs": 0,
            "grooves_carved": 0,
            "grooves_pioneered": 0,
            "biases_computed": 0,
            "flow_lines_rendered": 0,
            "chreodic_maps_emitted": 0,
            "grooves_emitted": 0,
            "events_recorded": 0,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if key not in self._stats:
                # Ignore unknown keys to keep callers simple.
                continue
            current = self._stats[key]
            if isinstance(current, (int, float)) and isinstance(value, (int, float)):
                self._stats[key] = current + value
            else:
                self._stats[key] = value

    def _record_event(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload or {},
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })
        self._stats["events_recorded"] += 1

    # -------------------------------------------------------------------------
    # Signature / Parsing Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _signature(source: str, target: str) -> str:
        """Canonical transition signature used as the natural groove key."""
        return f"{source}->{target}"

    @staticmethod
    def _parse_transition_kind(value: Any) -> TransitionKind:
        """Parse a TransitionKind from a string, enum, or None."""
        if value is None:
            return TransitionKind.STATE_CHANGE
        if isinstance(value, TransitionKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in TransitionKind:
                if kind.value == lowered:
                    return kind
        return TransitionKind.STATE_CHANGE

    # -------------------------------------------------------------------------
    # Transition Registration
    # -------------------------------------------------------------------------

    def register_transition(
        self,
        source_state: str,
        target_state: str,
        label: Optional[str] = None,
        kind: Any = None,
        weight: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Register a new state-transition event for processing in the next cycle."""
        with self._global_lock:
            if len(self._pending_transitions) >= self._MAX_PENDING_TRANSITIONS:
                return {"error": f"Pending transition cap reached ({self._MAX_PENDING_TRANSITIONS})"}
            source = str(source_state).strip()
            target = str(target_state).strip()
            if not source or not target:
                return {"error": "source_state and target_state must be non-empty"}
            signature = self._signature(source, target)
            event_id = f"tev_{int(time.time() * 1000)}_{random.randint(100, 999)}"
            kind_enum = self._parse_transition_kind(kind)
            w = 1.0 if weight is None else max(0.0, float(weight))
            lbl = label or signature
            event = TransitionEvent(
                event_id=event_id,
                source_state=source,
                target_state=target,
                label=lbl,
                kind=kind_enum,
                weight=w,
                observed_at=time.time(),
            )
            self._pending_transitions.append(event)
            self._update_stats(transitions_registered=1)
            self._record_event("transition_registered", {
                "event_id": event_id,
                "source_state": source,
                "target_state": target,
                "signature": signature,
                "kind": kind_enum.value,
                "weight": w,
            })
            return {
                "event_id": event_id,
                "transition_signature": signature,
                "source_state": source,
                "target_state": target,
                "kind": kind_enum.value,
                "weight": w,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single chreodic current mapping cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic transitions on the very first cycle if nothing exists.
            if not self._grooves and not self._pending_transitions and self._cycle_count == 0:
                self._seed_synthetic_grooves()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = ChreodicPhase.REGISTER_TRANSITION
            phase_outputs.append(self._phase_register_transition())
            self._phase = ChreodicPhase.CARVE_GROOVE
            phase_outputs.append(self._phase_carve_groove())
            self._phase = ChreodicPhase.COMPUTE_CURRENT_BIAS
            phase_outputs.append(self._phase_compute_current_bias())
            self._phase = ChreodicPhase.RENDER_FLOW_LINES
            phase_outputs.append(self._phase_render_flow_lines())
            self._phase = ChreodicPhase.EMIT_CHREODIC_MAP
            phase_outputs.append(self._phase_emit_chreodic_map())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_register_transition(self) -> Dict[str, Any]:
        """Register phase: drain pending transitions and create or note grooves."""
        registered = 0
        reinforced = 0
        while self._pending_transitions:
            event = self._pending_transitions.popleft()
            signature = self._signature(event.source_state, event.target_state)
            existing = self._grooves.get(signature)
            if existing is None:
                if len(self._grooves) >= self._MAX_GROOVES:
                    # Cap reached; cannot pioneer new grooves this cycle.
                    break
                groove_id = f"groove_{int(time.time() * 1000)}_{random.randint(100, 999)}"
                groove = ChreodeGroove(
                    groove_id=groove_id,
                    transition_signature=signature,
                    source_state=event.source_state,
                    target_state=event.target_state,
                    depth=0.0,
                    transition_count=0,
                    origin=GrooveOrigin.PIONEERED,
                    flow_bias=CurrentBiasMode.NEUTRAL,
                    bias_strength=0.0,
                    thickness=0.0,
                    state=FlowLineState.REGISTERED,
                    vitality=Vitality.DORMANT,
                    created_at=time.time(),
                    last_carved_at=0.0,
                    last_rendered_at=0.0,
                    note=event.label,
                )
                self._grooves[signature] = groove
                self._pending_carves[signature] = self._pending_carves.get(signature, 0.0) + event.weight
                registered += 1
            else:
                # Reinforce an existing groove: queue weight for the carve phase.
                self._pending_carves[signature] = self._pending_carves.get(signature, 0.0) + event.weight
                # Reset a previously-emitted groove so it gets re-carved this cycle.
                if existing.state == FlowLineState.EMITTED:
                    existing.state = FlowLineState.REGISTERED
                reinforced += 1
        self._update_stats(phase_runs=1, grooves_registered=registered)
        self._record_event("phase_register_transition", {
            "registered": registered,
            "reinforced": reinforced,
        })
        return {
            "phase": "register_transition",
            "registered": registered,
            "reinforced": reinforced,
        }

    def _phase_carve_groove(self) -> Dict[str, Any]:
        """Carve phase: deepen grooves for observed transitions, pioneer new ones, apply entropy decay."""
        carved = 0
        pioneered = 0
        deepened = 0
        now = time.time()
        # Apply background entropy decay to grooves not being carved this cycle.
        for groove in self._grooves.values():
            if groove.state == FlowLineState.REGISTERED:
                continue  # will be carved below
            if groove.transition_count > 0:
                groove.depth = max(0.0, groove.depth - self._DECAY_PER_CYCLE)
                if groove.depth <= 0.0 and groove.origin != GrooveOrigin.DECAYED:
                    groove.origin = GrooveOrigin.DECAYED
        # Carve grooves that have pending transitions registered this cycle.
        for groove in self._grooves.values():
            if groove.state != FlowLineState.REGISTERED:
                continue
            weight = self._pending_carves.pop(groove.transition_signature, 0.0)
            previous_depth = groove.depth
            is_new = groove.transition_count == 0
            if is_new:
                groove.depth = min(1.0, self._PIONEER_DEPTH + weight * self._CARVE_INCREMENT)
                groove.origin = GrooveOrigin.PIONEERED
                pioneered += 1
            else:
                groove.depth = min(1.0, groove.depth + self._CARVE_INCREMENT * weight)
                if groove.depth >= self._DEEPEN_THRESHOLD and previous_depth < self._DEEPEN_THRESHOLD:
                    groove.origin = GrooveOrigin.DEEPENED
                    deepened += 1
                else:
                    groove.origin = GrooveOrigin.REINFORCED
            groove.transition_count += max(1, int(round(weight)))
            groove.last_carved_at = now
            groove.state = FlowLineState.CARVED
            carved += 1
        self._update_stats(phase_runs=1, grooves_carved=carved, grooves_pioneered=pioneered)
        self._record_event("phase_carve_groove", {
            "carved": carved,
            "pioneered": pioneered,
            "deepened": deepened,
        })
        return {
            "phase": "carve_groove",
            "carved": carved,
            "pioneered": pioneered,
            "deepened": deepened,
        }

    def _phase_compute_current_bias(self) -> Dict[str, Any]:
        """Bias phase: compute flow bias mode and strength from groove depth."""
        biased = 0
        for groove in self._grooves.values():
            if groove.state != FlowLineState.CARVED:
                continue
            groove.flow_bias = self._classify_bias(groove.depth)
            groove.bias_strength = groove.depth  # strength tracks depth
            groove.state = FlowLineState.BIASED
            biased += 1
        self._update_stats(phase_runs=1, biases_computed=biased)
        self._record_event("phase_compute_current_bias", {"biased": biased})
        return {"phase": "compute_current_bias", "biased": biased}

    def _phase_render_flow_lines(self) -> Dict[str, Any]:
        """Render phase: set flow-line thickness from groove depth."""
        rendered = 0
        now = time.time()
        for groove in self._grooves.values():
            if groove.state != FlowLineState.BIASED:
                continue
            groove.thickness = self._depth_to_thickness(groove.depth)
            groove.last_rendered_at = now
            groove.state = FlowLineState.RENDERED
            rendered += 1
        self._update_stats(phase_runs=1, flow_lines_rendered=rendered)
        self._record_event("phase_render_flow_lines", {"rendered": rendered})
        return {"phase": "render_flow_lines", "rendered": rendered}

    def _phase_emit_chreodic_map(self) -> Dict[str, Any]:
        """Emit phase: finalize grooves and emit the chreodic map."""
        emitted = 0
        for groove in self._grooves.values():
            if groove.state != FlowLineState.RENDERED:
                continue
            groove.vitality = self._derive_vitality()
            groove.state = FlowLineState.EMITTED
            emitted += 1
        self._update_stats(phase_runs=1, chreodic_maps_emitted=1, grooves_emitted=emitted)
        self._record_event("phase_emit_chreodic_map", {"emitted": emitted})
        return {"phase": "emit_chreodic_map", "emitted": emitted}

    # -------------------------------------------------------------------------
    # Bias / Vitality Helpers
    # -------------------------------------------------------------------------

    def _classify_bias(self, depth: float) -> CurrentBiasMode:
        """Classify the current bias mode from groove depth."""
        if depth >= self._VORTEX_THRESHOLD:
            return CurrentBiasMode.VORTEX
        if depth >= self._ATTRACT_THRESHOLD:
            return CurrentBiasMode.ATTRACT
        if depth >= self._LAMINAR_THRESHOLD:
            return CurrentBiasMode.LAMINAR
        return CurrentBiasMode.NEUTRAL

    def _depth_to_thickness(self, depth: float) -> float:
        """Map groove depth (0.0-1.0) to an editor line thickness."""
        clamped = max(0.0, min(1.0, depth))
        return round(clamped * self._THICKNESS_SCALE, 3)

    def _derive_vitality(self) -> Vitality:
        """Derive overall ecosystem vitality from the groove population."""
        count = len(self._grooves)
        if count == 0:
            return Vitality.DORMANT
        if count <= 2:
            return Vitality.STIRRING
        if count <= 7:
            return Vitality.FLOWING
        if count <= 12:
            return Vitality.SURGING
        return Vitality.SATURATED

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_grooves(self) -> None:
        """Seed a few synthetic transition events if collections are empty."""
        if self._grooves or self._pending_transitions:
            return
        seeds = [
            ("calm", "alert", "calm->alert", TransitionKind.STATE_CHANGE, 1.0),
            ("alert", "engaged", "alert->engaged", TransitionKind.INTENT_SHIFT, 1.2),
            ("engaged", "calm", "engaged->calm", TransitionKind.STATE_CHANGE, 0.8),
            ("town", "forest", "town->forest", TransitionKind.LOCATION_SHIFT, 1.0),
            ("forest", "town", "forest->town", TransitionKind.LOCATION_SHIFT, 0.9),
        ]
        for source, target, label, kind, weight in seeds:
            if len(self._pending_transitions) >= self._MAX_PENDING_TRANSITIONS:
                break
            self.register_transition(
                source_state=source,
                target_state=target,
                label=label,
                kind=kind.value,
                weight=weight,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _groove_to_dict(self, groove: ChreodeGroove) -> Dict[str, Any]:
        return {
            "groove_id": groove.groove_id,
            "transition_signature": groove.transition_signature,
            "source_state": groove.source_state,
            "target_state": groove.target_state,
            "depth": groove.depth,
            "transition_count": groove.transition_count,
            "origin": groove.origin.value,
            "flow_bias": groove.flow_bias.value,
            "bias_strength": groove.bias_strength,
            "thickness": groove.thickness,
            "state": groove.state.value,
            "vitality": groove.vitality.value,
            "created_at": groove.created_at,
            "last_carved_at": groove.last_carved_at,
            "last_rendered_at": groove.last_rendered_at,
            "note": groove.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "grooves": len(self._grooves),
                "pending_transitions": len(self._pending_transitions),
                "stats": dict(self._stats),
            }

    def get_grooves(self, limit: int = 50) -> Dict[str, Any]:
        with self._global_lock:
            grooves = sorted(
                self._grooves.values(),
                key=lambda g: g.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(grooves),
                "grooves": [
                    {
                        "groove_id": g.groove_id,
                        "transition_signature": g.transition_signature,
                        "source_state": g.source_state,
                        "target_state": g.target_state,
                        "depth": g.depth,
                        "transition_count": g.transition_count,
                        "origin": g.origin.value,
                        "flow_bias": g.flow_bias.value,
                        "bias_strength": g.bias_strength,
                        "thickness": g.thickness,
                        "state": g.state.value,
                        "vitality": g.vitality.value,
                    }
                    for g in grooves
                ],
            }

    def get_groove(self, groove_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by transition_signature, NOT groove_id, so
        # we MUST iterate over values and match on the groove_id attribute.
        with self._global_lock:
            for groove in self._grooves.values():
                if groove.groove_id == groove_id:
                    return self._groove_to_dict(groove)
            return {"error": f"Groove not found: {groove_id}", "groove_id": groove_id}

    def get_chreodic_map(self) -> Dict[str, Any]:
        """Return the full chreodic map: grooves, biases, and flow lines."""
        with self._global_lock:
            grooves = sorted(self._grooves.values(), key=lambda g: g.depth, reverse=True)
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "groove_count": len(grooves),
                "grooves": [self._groove_to_dict(g) for g in grooves],
                "vitality": self._derive_vitality().value,
                "stats": dict(self._stats),
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic transitions if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._grooves and not self._pending_transitions:
                self._seed_synthetic_grooves()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._grooves.clear()
            self._pending_transitions.clear()
            self._pending_carves.clear()
            self._events_log.clear()
            self._phase = ChreodicPhase.REGISTER_TRANSITION
            self._cycle_count = 0
            self._init_stats()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }
