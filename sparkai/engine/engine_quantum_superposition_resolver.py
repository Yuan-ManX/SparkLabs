"""
SparkLabs Engine - Quantum Superposition Resolver"""

from __future__ import annotations

import logging
import math
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

class CollapsePhase(Enum):
    """Phases of the quantum superposition resolution cycle."""
    REGISTER_SUPERPOSITION = "register_superposition"  # register superposition fields for fresh entities
    EVOLVE = "evolve"              # evolve amplitudes (drift toward eigenstates or maintain coherence)
    INTERFERE = "interfere"        # compute interference between overlapping superpositions
    COLLAPSE = "collapse"          # trigger observation collapse (probabilistically pick an eigenstate)
    EMIT = "emit"                  # emit resolved eigenstates with their probabilities


class EigenstateKind(Enum):
    """The kind of outcome an eigenstate represents."""
    LOCATION = "location"          # where something is
    ATTRIBUTE = "attribute"        # what property it has
    INTENT = "intent"              # what an NPC wants
    RELATION = "relation"          # how entities relate
    EVENT = "event"                # what will happen


class CoherenceRegime(Enum):
    """The coherence regime a superposition is currently in."""
    COHERENT = "coherent"            # superposition stable, amplitudes preserved
    DECOHERING = "decohering"        # superposition beginning to drift
    DECOHERED = "decohered"          # superposition collapsed/lost
    RECURRENCE = "recurrence"        # previously-decohered field re-cohering


class InterferenceMode(Enum):
    """How two overlapping superpositions interfered."""
    CONSTRUCTIVE = "constructive"    # amplitudes reinforce
    DESTRUCTIVE = "destructive"      # amplitudes cancel
    MIXED = "mixed"                  # partial reinforcement/cancellation
    NONE = "none"                    # no interaction


class FieldState(Enum):
    """State of an individual superposition field."""
    RAW = "raw"                      # registered but not yet evolved
    EVOLVED = "evolved"              # amplitudes evolved
    INTERFERED = "interfered"        # interference computed
    COLLAPSED = "collapsed"          # observation collapsed eigenstate
    EMITTED = "emitted"              # eigenstate emitted


class Vitality(Enum):
    """Overall vitality of the superposition ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    FLOWING = "flowing"
    SURGING = "surging"
    SATURATED = "saturated"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Eigenstate:
    """A single possible outcome of a superposition field."""
    eigenstate_id: str
    label: str
    kind: EigenstateKind = EigenstateKind.ATTRIBUTE
    amplitude: complex = field(default_factory=lambda: complex(0.5, 0.0))  # complex amplitude
    probability: float = 0.25         # |amplitude|^2, normalized


@dataclass
class SuperpositionField:
    """A superposition field: a set of eigenstates held in coherent superposition."""
    field_id: str
    entity_id: str
    field_label: str
    eigenstates: List[Eigenstate] = field(default_factory=list)
    coherence: float = 1.0           # 0.0-1.0, 1.0 = fully coherent
    coherence_regime: CoherenceRegime = CoherenceRegime.COHERENT
    interference_mode: InterferenceMode = InterferenceMode.NONE
    observation_count: int = 0
    last_collapsed_eigenstate: Optional[str] = None
    state: FieldState = FieldState.RAW
    vitality: Vitality = Vitality.DORMANT
    created_at: float = field(default_factory=time.time)
    last_emitted_at: float = 0.0
    note: str = ""


# =============================================================================
# Resolver
# =============================================================================

class QuantumSuperpositionResolver:
    """
    Thread-safe singleton that resolves game-world superpositions.

    Superposition fields are keyed internally by entity_id so that each
    entity owns exactly one field. The field_id is a generated handle for
    external lookups; lookups by field_id fall back to a linear scan of
    the registered fields.

    Usage:
        resolver = QuantumSuperpositionResolver.get_instance()
        resolver.register_field(
            entity_id="field::mystery_chest",
            field_label="Mystery Chest",
            eigenstates=[
                {"eigenstate_id": "es_empty", "label": "empty"},
                {"eigenstate_id": "es_trapped", "label": "trapped"},
                {"eigenstate_id": "es_treasure", "label": "treasure"},
            ],
        )
        resolver.observe_field("field::mystery_chest")
        resolver.cycle()
        field = resolver.get_field(field_id)
    """

    _instance: Optional["QuantumSuperpositionResolver"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Capacity caps.
    _MAX_FIELDS = 60
    _MAX_EVENTS = 200
    _MAX_EIGENSTATES = 8
    _MAX_INTERACTIONS = 12

    # Domain tuning constants.
    _COHERENCE_DECAY = 0.05          # coherence lost per evolve phase
    _COLLAPSE_THRESHOLD = 0.5        # coherence below this triggers collapse
    _OBSERVATION_STRENGTH = 0.3      # how much an observation nudges toward collapse
    _PHASE_ROTATION_AMP = 0.1        # max radians of random phase rotation per evolve
    _DESTRUCTIVE_DAMPING = 0.3       # fraction amplitude reduced on destructive interference
    _VITALITY_SURGING_FRACTION = 0.6
    _VITALITY_SATURATED_FRACTION = 0.9

    def __init__(self) -> None:
        # Internal dict keyed by entity_id (NOT field_id).
        self._fields: Dict[str, SuperpositionField] = {}
        self._phase: CollapsePhase = CollapsePhase.REGISTER_SUPERPOSITION
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "QuantumSuperpositionResolver":
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
            "fields_registered": 0,
            "phase_runs": 0,
            "superpositions_evolved": 0,
            "interactions_computed": 0,
            "collapses_triggered": 0,
            "eigenstates_emitted": 0,
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
    # Amplitude Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _amplitude_to_dict(amp: complex) -> Dict[str, float]:
        """Serialize a complex amplitude to a JSON-friendly dict."""
        return {"real": amp.real, "imag": amp.imag}

    @staticmethod
    def _dict_to_amplitude(data: Any) -> complex:
        """Parse a complex amplitude from a dict, number, or None."""
        if data is None:
            return complex(0.5, 0.0)
        if isinstance(data, (int, float)):
            return complex(float(data), 0.0)
        if isinstance(data, dict):
            real = float(data.get("real", 0.5))
            imag = float(data.get("imag", 0.0))
            return complex(real, imag)
        return complex(0.5, 0.0)

    @staticmethod
    def _parse_eigenstate_kind(value: Any) -> EigenstateKind:
        """Parse an EigenstateKind from a string, enum, or None."""
        if value is None:
            return EigenstateKind.ATTRIBUTE
        if isinstance(value, EigenstateKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in EigenstateKind:
                if kind.value == lowered:
                    return kind
        return EigenstateKind.ATTRIBUTE

    def _normalize_amplitudes(self, eigenstates: List[Eigenstate]) -> None:
        """Normalize amplitudes so the sum of |amplitude|^2 equals 1.0."""
        if not eigenstates:
            return
        total = sum(abs(e.amplitude) ** 2 for e in eigenstates)
        if total <= 0.0:
            # Degenerate: distribute equal probability.
            even = 1.0 / math.sqrt(len(eigenstates))
            for e in eigenstates:
                e.amplitude = complex(even, 0.0)
        else:
            scale = 1.0 / math.sqrt(total)
            for e in eigenstates:
                e.amplitude = e.amplitude * scale
        # Refresh probability mirrors.
        for e in eigenstates:
            e.probability = abs(e.amplitude) ** 2

    # -------------------------------------------------------------------------
    # Field Management
    # -------------------------------------------------------------------------

    def register_field(
        self,
        entity_id: str,
        field_label: str,
        eigenstates: Optional[List[Dict[str, Any]]] = None,
        coherence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Register a new superposition field for an entity."""
        with self._global_lock:
            if entity_id in self._fields:
                return {"error": f"Field already registered for entity: {entity_id}"}
            if len(self._fields) >= self._MAX_FIELDS:
                return {"error": f"Field cap reached ({self._MAX_FIELDS})"}

            field_id = f"field_{entity_id}_{int(time.time() * 1000)}_{random.randint(100, 999)}"

            eigenstate_objs: List[Eigenstate] = []
            if eigenstates:
                for raw in eigenstates:
                    if not isinstance(raw, dict):
                        continue
                    es_id = str(raw.get("eigenstate_id") or f"es_{len(eigenstate_objs)}")
                    label = str(raw.get("label") or es_id)
                    kind = self._parse_eigenstate_kind(raw.get("kind"))
                    amp = self._dict_to_amplitude(raw.get("amplitude"))
                    eigenstate_objs.append(Eigenstate(
                        eigenstate_id=es_id,
                        label=label,
                        kind=kind,
                        amplitude=amp,
                        probability=abs(amp) ** 2,
                    ))
                # Cap the eigenstate count.
                if len(eigenstate_objs) > self._MAX_EIGENSTATES:
                    eigenstate_objs = eigenstate_objs[:self._MAX_EIGENSTATES]
            else:
                # Synthesize a small even superposition as a default.
                default_labels = ["alpha", "beta", "gamma"]
                even = 1.0 / math.sqrt(len(default_labels))
                for idx, label in enumerate(default_labels):
                    eigenstate_objs.append(Eigenstate(
                        eigenstate_id=f"es_{idx}_{field_id}",
                        label=label,
                        kind=EigenstateKind.ATTRIBUTE,
                        amplitude=complex(even, 0.0),
                        probability=even * even,
                    ))

            # Normalize AFTER all eigenstates are added.
            self._normalize_amplitudes(eigenstate_objs)

            coh = 1.0 if coherence is None else max(0.0, min(1.0, float(coherence)))

            super_field = SuperpositionField(
                field_id=field_id,
                entity_id=entity_id,
                field_label=field_label,
                eigenstates=eigenstate_objs,
                coherence=coh,
                coherence_regime=CoherenceRegime.COHERENT if coh > 0.7 else (
                    CoherenceRegime.DECOHERING if coh >= 0.3 else CoherenceRegime.DECOHERED
                ),
                interference_mode=InterferenceMode.NONE,
                observation_count=0,
                last_collapsed_eigenstate=None,
                state=FieldState.RAW,
                vitality=Vitality.DORMANT,
                created_at=time.time(),
                last_emitted_at=0.0,
                note="",
            )
            self._fields[entity_id] = super_field
            self._update_stats(fields_registered=1)
            self._record_event("field_registered", {
                "field_id": field_id,
                "entity_id": entity_id,
                "field_label": field_label,
                "eigenstate_count": len(eigenstate_objs),
                "coherence": coh,
            })
            return {
                "field_id": field_id,
                "entity_id": entity_id,
                "field_label": field_label,
                "eigenstate_count": len(eigenstate_objs),
                "coherence": coh,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single quantum superposition resolution cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic fields on the very first cycle if none exist.
            if not self._fields and self._cycle_count == 0:
                self._seed_synthetic_fields()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = CollapsePhase.REGISTER_SUPERPOSITION
            phase_outputs.append(self._phase_register_superposition())
            self._phase = CollapsePhase.EVOLVE
            phase_outputs.append(self._phase_evolve())
            self._phase = CollapsePhase.INTERFERE
            phase_outputs.append(self._phase_interfere())
            self._phase = CollapsePhase.COLLAPSE
            phase_outputs.append(self._phase_collapse())
            self._phase = CollapsePhase.EMIT
            phase_outputs.append(self._phase_emit())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_register_superposition(self) -> Dict[str, Any]:
        """Register phase: normalize raw fields and confirm them into the superposition."""
        registered = 0
        coherence_sum = 0.0
        for super_field in self._fields.values():
            if super_field.state != FieldState.RAW:
                continue
            self._normalize_amplitudes(super_field.eigenstates)
            super_field.state = FieldState.EVOLVED
            super_field.coherence_regime = self._classify_regime(super_field.coherence)
            registered += 1
            coherence_sum += super_field.coherence
        avg_coherence = (coherence_sum / registered) if registered > 0 else 0.0
        self._update_stats(phase_runs=1)
        self._record_event("phase_register_superposition", {
            "registered": registered,
            "avg_coherence": avg_coherence,
        })
        return {
            "phase": "register_superposition",
            "registered": registered,
            "avg_coherence": avg_coherence,
        }

    def _phase_evolve(self) -> Dict[str, Any]:
        """Evolve phase: apply coherence decay and small phase rotation to amplitudes."""
        evolved = 0
        for super_field in self._fields.values():
            if super_field.state != FieldState.EVOLVED:
                continue
            # Coherence decays a little each cycle.
            previous_coherence = super_field.coherence
            previous_regime = super_field.coherence_regime
            super_field.coherence = max(0.0, super_field.coherence - self._COHERENCE_DECAY)
            # Small random phase rotation per eigenstate.
            for eigenstate in super_field.eigenstates:
                theta = random.uniform(-self._PHASE_ROTATION_AMP, self._PHASE_ROTATION_AMP)
                rotator = complex(math.cos(theta), math.sin(theta))
                eigenstate.amplitude = eigenstate.amplitude * rotator
            self._normalize_amplitudes(super_field.eigenstates)
            # Reclassify coherence regime, honoring recurrence if a decohered
            # field somehow rose back above its prior level.
            super_field.coherence_regime = self._classify_regime(
                super_field.coherence,
                previous_regime=previous_regime,
                previous_coherence=previous_coherence,
            )
            super_field.state = FieldState.INTERFERED
            evolved += 1
        self._update_stats(phase_runs=1, superpositions_evolved=evolved)
        self._record_event("phase_evolve", {"evolved": evolved})
        return {"phase": "evolve", "evolved": evolved}

    def _phase_interfere(self) -> Dict[str, Any]:
        """Interfere phase: compute interference between eigenstates of the same kind."""
        interfered = 0
        for super_field in self._fields.values():
            if super_field.state != FieldState.INTERFERED:
                continue
            super_field.interference_mode = self._compute_interference(super_field)
            self._normalize_amplitudes(super_field.eigenstates)
            super_field.state = FieldState.COLLAPSED
            interfered += 1
        self._update_stats(phase_runs=1, interactions_computed=interfered)
        self._record_event("phase_interfere", {"interfered": interfered})
        return {"phase": "interfere", "interfered": interfered}

    def _phase_collapse(self) -> Dict[str, Any]:
        """Collapse phase: probabilistically pick an eigenstate when coherence drops or observation forces."""
        collapsed = 0
        for super_field in self._fields.values():
            if super_field.state != FieldState.COLLAPSED:
                continue
            should_collapse = (
                super_field.coherence < self._COLLAPSE_THRESHOLD
                or super_field.observation_count > 0
            )
            if should_collapse and super_field.eigenstates:
                chosen = self._pick_eigenstate(super_field)
                if chosen is not None:
                    # Zero out all amplitudes except the chosen one.
                    for eigenstate in super_field.eigenstates:
                        eigenstate.amplitude = complex(0.0, 0.0)
                        eigenstate.probability = 0.0
                    chosen.amplitude = complex(1.0, 0.0)
                    chosen.probability = 1.0
                    super_field.last_collapsed_eigenstate = chosen.label
                    super_field.coherence_regime = CoherenceRegime.DECOHERED
                    super_field.coherence = 0.0
                    super_field.observation_count += 1
                    collapsed += 1
            super_field.state = FieldState.EMITTED
        self._update_stats(phase_runs=1, collapses_triggered=collapsed)
        self._record_event("phase_collapse", {"collapsed": collapsed})
        return {"phase": "collapse", "collapsed": collapsed}

    def _phase_emit(self) -> Dict[str, Any]:
        """Emit phase: emit resolved eigenstates with their probabilities."""
        emitted = 0
        now = time.time()
        for super_field in self._fields.values():
            if super_field.state != FieldState.EMITTED:
                continue
            super_field.last_emitted_at = now
            super_field.vitality = self._derive_vitality()
            emitted += 1
        self._update_stats(phase_runs=1, eigenstates_emitted=emitted)
        self._record_event("phase_emit", {"emitted": emitted})
        return {"phase": "emit", "emitted": emitted}

    # -------------------------------------------------------------------------
    # Interference Helpers
    # -------------------------------------------------------------------------

    def _compute_interference(self, super_field: SuperpositionField) -> InterferenceMode:
        """Compute interference between eigenstates of the same kind within a field."""
        kind_groups: Dict[EigenstateKind, List[Eigenstate]] = {}
        for eigenstate in super_field.eigenstates:
            kind_groups.setdefault(eigenstate.kind, []).append(eigenstate)
        # Find the first group with at least two eigenstates to interfere.
        for group in kind_groups.values():
            if len(group) < 2:
                continue
            constructive = 0
            destructive = 0
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a = group[i].amplitude
                    b = group[j].amplitude
                    if abs(a) == 0.0 or abs(b) == 0.0:
                        continue
                    phase_a = math.atan2(a.imag, a.real)
                    phase_b = math.atan2(b.imag, b.real)
                    phase_diff = abs(phase_a - phase_b)
                    # Wrap to [0, pi].
                    if phase_diff > math.pi:
                        phase_diff = 2.0 * math.pi - phase_diff
                    if phase_diff < math.pi / 4.0:
                        constructive += 1
                    elif phase_diff > 3.0 * math.pi / 4.0:
                        # Destructive: reduce both amplitudes.
                        group[i].amplitude = group[i].amplitude * (1.0 - self._DESTRUCTIVE_DAMPING)
                        group[j].amplitude = group[j].amplitude * (1.0 - self._DESTRUCTIVE_DAMPING)
                        destructive += 1
            if constructive and destructive:
                return InterferenceMode.MIXED
            if constructive:
                return InterferenceMode.CONSTRUCTIVE
            if destructive:
                return InterferenceMode.DESTRUCTIVE
        return InterferenceMode.NONE

    def _pick_eigenstate(self, super_field: SuperpositionField) -> Optional[Eigenstate]:
        """Probabilistically pick an eigenstate weighted by its probability."""
        eigenstates = super_field.eigenstates
        if not eigenstates:
            return None
        total = sum(abs(e.amplitude) ** 2 for e in eigenstates)
        if total <= 0.0:
            # Fall back to uniform random pick.
            return random.choice(eigenstates)
        roll = random.uniform(0.0, total)
        cumulative = 0.0
        for eigenstate in eigenstates:
            cumulative += abs(eigenstate.amplitude) ** 2
            if roll <= cumulative:
                return eigenstate
        return eigenstates[-1]

    def _classify_regime(
        self,
        coherence: float,
        previous_regime: Optional[CoherenceRegime] = None,
        previous_coherence: Optional[float] = None,
    ) -> CoherenceRegime:
        """Classify the coherence regime from the current coherence value."""
        if coherence > 0.7:
            # If the field was previously decohered and coherence rose, mark recurrence.
            if previous_regime == CoherenceRegime.DECOHERED and previous_coherence is not None \
                    and coherence > previous_coherence:
                return CoherenceRegime.RECURRENCE
            return CoherenceRegime.COHERENT
        if coherence >= 0.3:
            return CoherenceRegime.DECOHERING
        return CoherenceRegime.DECOHERED

    # -------------------------------------------------------------------------
    # Observation
    # -------------------------------------------------------------------------

    def observe_field(self, entity_id: str) -> Dict[str, Any]:
        """Trigger an observation on a field; collapse happens on the next COLLAPSE phase."""
        with self._global_lock:
            super_field = self._fields.get(entity_id)
            if super_field is None:
                return {"error": f"Field not found: {entity_id}"}
            super_field.observation_count += 1
            # Observation also nudges coherence downward toward collapse.
            super_field.coherence = max(
                0.0,
                super_field.coherence - self._OBSERVATION_STRENGTH,
            )
            self._record_event("field_observed", {
                "entity_id": entity_id,
                "field_id": super_field.field_id,
                "observation_count": super_field.observation_count,
                "coherence": super_field.coherence,
            })
            return {
                "entity_id": entity_id,
                "field_id": super_field.field_id,
                "observation_count": super_field.observation_count,
                "coherence": super_field.coherence,
                "pending_collapse": True,
            }

    # -------------------------------------------------------------------------
    # Vitality
    # -------------------------------------------------------------------------

    def _derive_vitality(self) -> Vitality:
        """Derive overall ecosystem vitality from the field population."""
        count = len(self._fields)
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

    def _seed_synthetic_fields(self) -> None:
        """Seed a few synthetic superposition fields on the first cycle if empty."""
        seeds = [
            (
                "field::mystery_chest",
                "Mystery Chest",
                EigenstateKind.ATTRIBUTE,
                [
                    ("es_empty", "empty"),
                    ("es_trapped", "trapped"),
                    ("es_treasure", "treasure"),
                ],
                0.9,
            ),
            (
                "field::npc_intent",
                "NPC Intent",
                EigenstateKind.INTENT,
                [
                    ("es_betray", "betray"),
                    ("es_aid", "aid"),
                    ("es_flee", "flee"),
                ],
                0.8,
            ),
            (
                "field::hidden_door",
                "Hidden Door",
                EigenstateKind.LOCATION,
                [
                    ("es_vault", "leads_to_vault"),
                    ("es_trap", "leads_to_trap"),
                    ("es_sealed", "sealed"),
                ],
                0.7,
            ),
        ]
        for entity_id, label, kind, states, coherence in seeds:
            if entity_id in self._fields:
                continue
            if len(self._fields) >= self._MAX_FIELDS:
                break
            eigenstates_in: List[Dict[str, Any]] = []
            even = 1.0 / math.sqrt(len(states))
            for es_id, es_label in states:
                eigenstates_in.append({
                    "eigenstate_id": es_id,
                    "label": es_label,
                    "kind": kind.value,
                    "amplitude": {"real": even, "imag": 0.0},
                })
            self.register_field(
                entity_id=entity_id,
                field_label=label,
                eigenstates=eigenstates_in,
                coherence=coherence,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _eigenstate_to_dict(self, eigenstate: Eigenstate) -> Dict[str, Any]:
        return {
            "eigenstate_id": eigenstate.eigenstate_id,
            "label": eigenstate.label,
            "kind": eigenstate.kind.value,
            "amplitude": self._amplitude_to_dict(eigenstate.amplitude),
            "probability": eigenstate.probability,
        }

    def _field_to_dict(self, super_field: SuperpositionField) -> Dict[str, Any]:
        return {
            "field_id": super_field.field_id,
            "entity_id": super_field.entity_id,
            "field_label": super_field.field_label,
            "coherence": super_field.coherence,
            "coherence_regime": super_field.coherence_regime.value,
            "interference_mode": super_field.interference_mode.value,
            "observation_count": super_field.observation_count,
            "last_collapsed_eigenstate": super_field.last_collapsed_eigenstate,
            "state": super_field.state.value,
            "vitality": super_field.vitality.value,
            "eigenstate_count": len(super_field.eigenstates),
            "eigenstates": [self._eigenstate_to_dict(e) for e in super_field.eigenstates],
            "created_at": super_field.created_at,
            "last_emitted_at": super_field.last_emitted_at,
            "note": super_field.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "fields": len(self._fields),
                "stats": dict(self._stats),
            }

    def get_fields(self, limit: int = 50) -> Dict[str, Any]:
        with self._global_lock:
            fields = sorted(
                self._fields.values(),
                key=lambda f: f.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(fields),
                "fields": [
                    {
                        "field_id": f.field_id,
                        "entity_id": f.entity_id,
                        "field_label": f.field_label,
                        "coherence": f.coherence,
                        "coherence_regime": f.coherence_regime.value,
                        "interference_mode": f.interference_mode.value,
                        "state": f.state.value,
                        "vitality": f.vitality.value,
                        "eigenstate_count": len(f.eigenstates),
                        "last_collapsed_eigenstate": f.last_collapsed_eigenstate,
                    }
                    for f in fields
                ],
            }

    def get_field(self, field_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT field_id, so we MUST
        # iterate over values and match on the field_id attribute.
        with self._global_lock:
            for super_field in self._fields.values():
                if super_field.field_id == field_id:
                    return self._field_to_dict(super_field)
            return {"error": f"Field not found: {field_id}", "field_id": field_id}

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic fields if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._fields:
                self._seed_synthetic_fields()
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
            self._fields.clear()
            self._events_log.clear()
            self._phase = CollapsePhase.REGISTER_SUPERPOSITION
            self._cycle_count = 0
            self._init_stats()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }
