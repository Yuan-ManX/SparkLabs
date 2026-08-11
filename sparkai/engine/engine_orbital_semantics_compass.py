"""
SparkLabs Engine - Orbital Semantics Compass"""

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

class OrbitalPhase(Enum):
    """Phases of the orbital semantics compass cycle."""
    REGISTER_CONCEPT = "register_concept"      # register concept-stars with their semantic mass and orbital bodies
    PROPAGATE_ORBITS = "propagate_orbits"      # propagate each body's angular position along its orbit for this cycle
    COMPUTE_DRIFT = "compute_drift"            # compute orbital drift: eccentricity changes, radius perturbations
    DETECT_ESCAPES = "detect_escapes"          # detect bodies escaping orbit vs newly captured bodies
    EMIT_ORBITAL_MAP = "emit_orbital_map"      # emit the orbital semantics map with stars, bodies, paths for the editor


class ConceptKind(Enum):
    """The kind of concept-star at the center of an orbital system."""
    CONCRETE = "concrete"              # concrete, grounded concept
    ABSTRACT = "abstract"              # abstract idea
    RELATIONAL = "relational"          # relation between entities
    PROCEDURAL = "procedural"          # process or action


class OrbitClass(Enum):
    """The classification of an orbital body's orbit around its concept-star."""
    CANONICAL = "canonical"            # tight, stable orbit - the canonical sense
    METAPHORICAL = "metaphorical"      # wide eccentric orbit - metaphorical sense
    EDGE = "edge"                      # drifting wide orbit - edge sense
    ESCAPING = "escaping"              # exceeding escape velocity - detaching sense


class SenseFacet(Enum):
    """The semantic facet an orbital body emphasizes (encoded by angular position)."""
    LITERAL = "literal"                # literal denotation
    FIGURATIVE = "figurative"          # figurative connotation
    CONTEXTUAL = "contextual"          # context-dependent sense
    CONNOTATIVE = "connotative"        # emotional or cultural connotation
    TECHNICAL = "technical"            # specialized domain sense


class BodyState(Enum):
    """State of an individual orbital body through the cycle."""
    PENDING = "pending"                # registered but not yet processed
    REGISTERED = "registered"          # confirmed and classified
    PROPAGATED = "propagated"          # angular position stepped
    DRIFTED = "drifted"                # drift computed and applied
    ANALYZED = "analyzed"              # escape/capture analyzed
    EMITTED = "emitted"                # emitted into the orbital map


class Vitality(Enum):
    """Overall vitality of the orbital semantics ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    ORBITING = "orbiting"
    DYNAMIC = "dynamic"
    CHAOTIC = "chaotic"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ConceptStar:
    """A concept-star at the center of an orbital semantic system."""
    concept_id: str
    concept_handle: str
    label: str
    semantic_mass: float                          # gravitational pull on meanings, 0.1-10.0
    kind: ConceptKind = ConceptKind.ABSTRACT
    escape_velocity: float = 1.0                  # threshold above which a body escapes
    active: bool = True
    vitality: Vitality = Vitality.DORMANT
    created_at: float = field(default_factory=time.time)
    last_propagated_at: float = 0.0
    note: str = ""


@dataclass
class OrbitalBody:
    """A semantic meaning orbiting a concept-star."""
    body_id: str
    concept_id: str
    label: str
    orbital_radius: float                         # distance from the core sense, >= 0.0
    angular_position: float                       # radians, which facet of the concept it emphasizes
    eccentricity: float                           # 0.0 (circular) - 0.95 (highly variable)
    orbit_class: OrbitClass = OrbitClass.CANONICAL
    sense_facet: SenseFacet = SenseFacet.LITERAL
    angular_velocity: float = 0.1                 # radians stepped per cycle
    drift_rate: float = 0.0                       # radius perturbation per cycle
    escape_signal: float = 0.0                    # 0.0-1.0, fraction of escape velocity reached
    captured: bool = False                        # True if newly captured this cycle
    state: BodyState = BodyState.PENDING
    created_at: float = field(default_factory=time.time)
    last_drift_at: float = 0.0
    note: str = ""


# =============================================================================
# Compass
# =============================================================================

class OrbitalSemanticsCompass:
    """
    Thread-safe singleton that tracks semantic meanings as orbital bodies
    circling concept-stars.

    Concept-stars are keyed internally by concept_handle so that each logical
    concept owns exactly one entry. The concept_id is a generated handle for
    external lookups; lookups by concept_id fall back to a linear scan of
    the registered concept-stars.

    Usage:
        compass = OrbitalSemanticsCompass.get_instance()
        compass.register_concept(
            concept_handle="concept::resonance",
            label="Resonance",
            semantic_mass=4.5,
        )
        compass.cycle()
        concept = compass.get_concept(concept_id)
        orbital_map = compass.get_orbital_map()
    """

    _instance: Optional["OrbitalSemanticsCompass"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Capacity caps.
    _MAX_CONCEPTS = 60
    _MAX_EVENTS = 200
    _MAX_BODIES = 200
    _MAX_PATHS = 120
    _MAX_DRIFTS = 200
    _MAX_ESCAPES = 60

    # Domain tuning constants.
    _TWO_PI = 2.0 * math.pi
    _MAX_ECCENTRICITY = 0.95                # cap on orbit variability
    _MIN_SEMANTIC_MASS = 0.1
    _MAX_SEMANTIC_MASS = 10.0
    _ANGULAR_VELOCITY_BASE = 0.1            # radians per cycle for a unit-mass star
    _ESCAPE_VELOCITY_BASE = 1.0             # base escape velocity scale
    _CANONICAL_RADIUS_MAX = 1.5             # orbits inside this are canonical
    _METAPHORICAL_RADIUS_MAX = 4.0          # orbits inside this are metaphorical
    _EDGE_RADIUS_MAX = 7.0                  # orbits inside this are edge senses
    _DRIFT_SCALE = 0.05                     # base radius perturbation magnitude
    _CAPTURE_RADIUS = 6.0                   # bodies within this radius are captured candidates

    def __init__(self) -> None:
        # Internal dict keyed by concept_handle (NOT concept_id).
        self._concepts: Dict[str, ConceptStar] = {}
        self._bodies: Dict[str, OrbitalBody] = {}
        self._paths: Dict[str, Dict[str, Any]] = {}
        self._drifts: Dict[str, Dict[str, Any]] = {}
        self._escapes: Dict[str, Dict[str, Any]] = {}
        self._phase: OrbitalPhase = OrbitalPhase.REGISTER_CONCEPT
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._concepts:
            self._seed_synthetic_concepts()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "OrbitalSemanticsCompass":
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
            "concepts_registered": 0,
            "phase_runs": 0,
            "bodies_propagated": 0,
            "drifts_computed": 0,
            "escapes_detected": 0,
            "captures_detected": 0,
            "orbital_maps_emitted": 0,
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
    # Parsing Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _parse_concept_kind(value: Any) -> ConceptKind:
        """Parse a ConceptKind from a string, enum, or None."""
        if value is None:
            return ConceptKind.ABSTRACT
        if isinstance(value, ConceptKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in ConceptKind:
                if kind.value == lowered:
                    return kind
        return ConceptKind.ABSTRACT

    @staticmethod
    def _parse_sense_facet(value: Any) -> SenseFacet:
        """Parse a SenseFacet from a string, enum, or None."""
        if value is None:
            return SenseFacet.LITERAL
        if isinstance(value, SenseFacet):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for facet in SenseFacet:
                if facet.value == lowered:
                    return facet
        return SenseFacet.LITERAL

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_orbit_class(self, radius: float, eccentricity: float) -> OrbitClass:
        """Classify an orbit by its radius and eccentricity."""
        if radius <= self._CANONICAL_RADIUS_MAX and eccentricity < 0.3:
            return OrbitClass.CANONICAL
        if radius <= self._METAPHORICAL_RADIUS_MAX:
            return OrbitClass.METAPHORICAL
        if radius <= self._EDGE_RADIUS_MAX:
            return OrbitClass.EDGE
        return OrbitClass.ESCAPING

    def _classify_sense_facet(self, angular_position: float) -> SenseFacet:
        """Classify the sense facet from the angular position (radians)."""
        # Map angular sectors to facets. Wrap into [0, 2*pi).
        angle = angular_position % self._TWO_PI
        sector = int((angle / self._TWO_PI) * len(SenseFacet)) % len(SenseFacet)
        return list(SenseFacet)[sector]

    def _compute_angular_velocity(self, semantic_mass: float, radius: float) -> float:
        """Compute angular velocity for a body orbiting a concept-star.

        Tighter orbits around heavier stars advance faster (Kepler-style).
        """
        mass = max(semantic_mass, self._MIN_SEMANTIC_MASS)
        radius_safe = max(radius, 0.1)
        # Inner bodies move faster; heavier stars pull harder.
        velocity = self._ANGULAR_VELOCITY_BASE * math.sqrt(mass / radius_safe)
        # Keep within a sensible per-cycle bound.
        return max(0.01, min(velocity, self._TWO_PI))

    def _compute_escape_velocity(self, semantic_mass: float) -> float:
        """Compute the escape velocity threshold for a concept-star."""
        mass = max(semantic_mass, self._MIN_SEMANTIC_MASS)
        return self._ESCAPE_VELOCITY_BASE * math.sqrt(mass)

    def _color_for_orbit_class(self, orbit_class: OrbitClass) -> str:
        """Map an orbit class to a preview color for the editor path."""
        if orbit_class == OrbitClass.CANONICAL:
            return "#FFD700"  # gold - the canonical core sense
        if orbit_class == OrbitClass.METAPHORICAL:
            return "#FF4500"  # orange-red - wide metaphorical sense
        if orbit_class == OrbitClass.EDGE:
            return "#9370DB"  # medium purple - drifting edge sense
        return "#8B0000"      # dark red - escaping sense

    # -------------------------------------------------------------------------
    # Concept Management
    # -------------------------------------------------------------------------

    def register_concept(
        self,
        concept_handle: str,
        label: str,
        semantic_mass: float = 1.0,
        kind: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new concept-star with its semantic mass."""
        with self._global_lock:
            if concept_handle in self._concepts:
                return {"error": f"Concept already registered: {concept_handle}"}
            if len(self._concepts) >= self._MAX_CONCEPTS:
                return {"error": f"Concept cap reached ({self._MAX_CONCEPTS})"}

            concept_id = f"conc_{concept_handle}_{int(time.time() * 1000)}_{random.randint(100, 999)}"

            mass = max(
                self._MIN_SEMANTIC_MASS,
                min(self._MAX_SEMANTIC_MASS, float(semantic_mass)),
            )
            parsed_kind = self._parse_concept_kind(kind)
            escape_v = self._compute_escape_velocity(mass)

            concept = ConceptStar(
                concept_id=concept_id,
                concept_handle=concept_handle,
                label=label,
                semantic_mass=mass,
                kind=parsed_kind,
                escape_velocity=escape_v,
                active=True,
                vitality=Vitality.DORMANT,
                created_at=time.time(),
                last_propagated_at=0.0,
                note=note,
            )
            self._concepts[concept_handle] = concept
            self._update_stats(concepts_registered=1)
            self._record_event("concept_registered", {
                "concept_id": concept_id,
                "concept_handle": concept_handle,
                "label": label,
                "semantic_mass": mass,
                "kind": parsed_kind.value,
                "escape_velocity": escape_v,
            })

            # Seed a few orbital bodies for the new concept so cycles produce
            # meaningful output immediately.
            self._seed_bodies_for_concept(concept)

            return {
                "concept_id": concept_id,
                "concept_handle": concept_handle,
                "label": label,
                "semantic_mass": mass,
                "kind": parsed_kind.value,
                "escape_velocity": escape_v,
            }

    def _seed_bodies_for_concept(self, concept: ConceptStar) -> None:
        """Seed a small set of orbital bodies for a freshly registered concept."""
        # Pull a few canonical, metaphorical, and edge senses for the concept.
        body_specs = [
            ("Canonical sense", 0.8, 0.0, 0.05, SenseFacet.LITERAL),
            ("Metaphorical sense", 2.5, math.pi * 0.5, 0.45, SenseFacet.FIGURATIVE),
            ("Edge sense", 5.5, math.pi * 1.2, 0.75, SenseFacet.CONNOTATIVE),
        ]
        for label, radius, angle, ecc, facet in body_specs:
            if len(self._bodies) >= self._MAX_BODIES:
                break
            body_id = (
                f"body_{concept.concept_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            orbit_class = self._classify_orbit_class(radius, ecc)
            angular_v = self._compute_angular_velocity(concept.semantic_mass, radius)
            body = OrbitalBody(
                body_id=body_id,
                concept_id=concept.concept_id,
                label=label,
                orbital_radius=radius,
                angular_position=angle,
                eccentricity=ecc,
                orbit_class=orbit_class,
                sense_facet=facet,
                angular_velocity=angular_v,
                drift_rate=0.0,
                escape_signal=0.0,
                captured=False,
                state=BodyState.PENDING,
                created_at=time.time(),
                last_drift_at=0.0,
                note="seeded",
            )
            self._bodies[body_id] = body

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single orbital semantics compass cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic concepts on the very first cycle if none exist.
            if not self._concepts and self._cycle_count == 0:
                self._seed_synthetic_concepts()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = OrbitalPhase.REGISTER_CONCEPT
            phase_outputs.append(self._phase_register_concept())
            self._phase = OrbitalPhase.PROPAGATE_ORBITS
            phase_outputs.append(self._phase_propagate_orbits())
            self._phase = OrbitalPhase.COMPUTE_DRIFT
            phase_outputs.append(self._phase_compute_drift())
            self._phase = OrbitalPhase.DETECT_ESCAPES
            phase_outputs.append(self._phase_detect_escapes())
            self._phase = OrbitalPhase.EMIT_ORBITAL_MAP
            phase_outputs.append(self._phase_emit_orbital_map())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_register_concept(self) -> Dict[str, Any]:
        """Register phase: confirm pending concept-stars and their orbital bodies."""
        registered_concepts = 0
        registered_bodies = 0
        mass_sum = 0.0
        for concept in self._concepts.values():
            # Recompute escape velocity in case semantic_mass was adjusted.
            concept.escape_velocity = self._compute_escape_velocity(concept.semantic_mass)
            mass_sum += concept.semantic_mass
            # Confirm any pending bodies attached to this concept.
            for body in self._bodies.values():
                if body.concept_id != concept.concept_id:
                    continue
                if body.state == BodyState.PENDING:
                    body.orbit_class = self._classify_orbit_class(
                        body.orbital_radius, body.eccentricity,
                    )
                    body.sense_facet = self._classify_sense_facet(body.angular_position)
                    body.angular_velocity = self._compute_angular_velocity(
                        concept.semantic_mass, body.orbital_radius,
                    )
                    body.state = BodyState.REGISTERED
                    registered_bodies += 1
            registered_concepts += 1
        avg_mass = (mass_sum / registered_concepts) if registered_concepts > 0 else 0.0
        self._update_stats(phase_runs=1)
        self._record_event("phase_register_concept", {
            "registered_concepts": registered_concepts,
            "registered_bodies": registered_bodies,
            "avg_semantic_mass": avg_mass,
        })
        return {
            "phase": "register_concept",
            "registered_concepts": registered_concepts,
            "registered_bodies": registered_bodies,
            "avg_semantic_mass": avg_mass,
        }

    def _phase_propagate_orbits(self) -> Dict[str, Any]:
        """Propagate phase: advance each body's angular position along its orbit."""
        propagated = 0
        for body in self._bodies.values():
            if body.state != BodyState.REGISTERED:
                continue
            # Advance angular position, mod 2*pi to keep it bounded.
            body.angular_position = (
                body.angular_position + body.angular_velocity
            ) % self._TWO_PI
            # Re-classify the facet since the angle moved.
            body.sense_facet = self._classify_sense_facet(body.angular_position)
            body.state = BodyState.PROPAGATED
            propagated += 1
        # Stamp the concept-stars with the propagation time.
        for concept in self._concepts.values():
            concept.last_propagated_at = time.time()
        self._update_stats(phase_runs=1, bodies_propagated=propagated)
        self._record_event("phase_propagate_orbits", {"propagated": propagated})
        return {"phase": "propagate_orbits", "propagated": propagated}

    def _phase_compute_drift(self) -> Dict[str, Any]:
        """Drift phase: compute eccentricity changes and radius perturbations."""
        drifts_computed = 0
        for body in self._bodies.values():
            if body.state != BodyState.PROPAGATED:
                continue
            # Eccentricity drifts slightly each cycle, clamped to the cap.
            ecc_delta = random.uniform(-self._DRIFT_SCALE, self._DRIFT_SCALE)
            body.eccentricity = max(
                0.0, min(self._MAX_ECCENTRICITY, body.eccentricity + ecc_delta),
            )
            # Radius perturbs based on eccentricity; high eccentricity wobbles more.
            radius_delta = random.uniform(-1.0, 1.0) * self._DRIFT_SCALE * (1.0 + body.eccentricity)
            body.orbital_radius = max(0.05, body.orbital_radius + radius_delta)
            body.drift_rate = abs(radius_delta)
            body.orbit_class = self._classify_orbit_class(
                body.orbital_radius, body.eccentricity,
            )
            body.last_drift_at = time.time()
            body.state = BodyState.DRIFTED

            # Record the drift entry.
            drift_id = (
                f"drift_{body.body_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            drift_entry = {
                "drift_id": drift_id,
                "body_id": body.body_id,
                "concept_id": body.concept_id,
                "radius_delta": radius_delta,
                "eccentricity_delta": ecc_delta,
                "new_radius": body.orbital_radius,
                "new_eccentricity": body.eccentricity,
                "orbit_class": body.orbit_class.value,
                "created_at": body.last_drift_at,
            }
            # Cap the drift collection.
            if len(self._drifts) >= self._MAX_DRIFTS:
                oldest_key = next(iter(self._drifts))
                self._drifts.pop(oldest_key, None)
            self._drifts[drift_id] = drift_entry
            drifts_computed += 1
        self._update_stats(phase_runs=1, drifts_computed=drifts_computed)
        self._record_event("phase_compute_drift", {"drifts_computed": drifts_computed})
        return {"phase": "compute_drift", "drifts_computed": drifts_computed}

    def _phase_detect_escapes(self) -> Dict[str, Any]:
        """Detect phase: find bodies escaping orbit vs newly captured bodies."""
        escapes_detected = 0
        captures_detected = 0
        for body in self._bodies.values():
            if body.state != BodyState.DRIFTED:
                continue
            concept = self._find_concept_by_id(body.concept_id)
            escape_v = concept.escape_velocity if concept else self._ESCAPE_VELOCITY_BASE
            # Body speed scales with angular velocity times radius (tangential speed).
            tangential_speed = body.angular_velocity * body.orbital_radius
            body.escape_signal = min(1.0, tangential_speed / max(escape_v, 0.001))
            # Newly captured if inside the capture radius AND flagged as escaping
            # last cycle but now back inside.
            if body.orbital_radius <= self._CAPTURE_RADIUS and body.captured:
                # Already counted as captured previously; keep the flag for one cycle.
                body.captured = False
            if body.escape_signal >= 1.0 or body.orbital_radius > self._EDGE_RADIUS_MAX:
                # Body is escaping - record the escape event.
                escape_id = (
                    f"esc_{body.body_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                escape_entry = {
                    "escape_id": escape_id,
                    "body_id": body.body_id,
                    "concept_id": body.concept_id,
                    "escape_signal": body.escape_signal,
                    "tangential_speed": tangential_speed,
                    "escape_velocity": escape_v,
                    "orbital_radius": body.orbital_radius,
                    "kind": "escape",
                    "created_at": time.time(),
                }
                # Cap the escape collection.
                if len(self._escapes) >= self._MAX_ESCAPES:
                    oldest_key = next(iter(self._escapes))
                    self._escapes.pop(oldest_key, None)
                self._escapes[escape_id] = escape_entry
                body.orbit_class = OrbitClass.ESCAPING
                escapes_detected += 1
            elif body.orbital_radius <= self._CANONICAL_RADIUS_MAX and body.captured is False:
                # Candidate for fresh capture if it pulled back into a tight orbit.
                # We mark it captured so the next cycle can confirm it stayed.
                body.captured = True
                capture_id = (
                    f"cap_{body.body_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                capture_entry = {
                    "escape_id": capture_id,
                    "body_id": body.body_id,
                    "concept_id": body.concept_id,
                    "orbital_radius": body.orbital_radius,
                    "orbit_class": body.orbit_class.value,
                    "kind": "capture",
                    "created_at": time.time(),
                }
                if len(self._escapes) >= self._MAX_ESCAPES:
                    oldest_key = next(iter(self._escapes))
                    self._escapes.pop(oldest_key, None)
                self._escapes[capture_id] = capture_entry
                captures_detected += 1
            body.state = BodyState.ANALYZED
        self._update_stats(
            phase_runs=1,
            escapes_detected=escapes_detected,
            captures_detected=captures_detected,
        )
        self._record_event("phase_detect_escapes", {
            "escapes_detected": escapes_detected,
            "captures_detected": captures_detected,
        })
        return {
            "phase": "detect_escapes",
            "escapes_detected": escapes_detected,
            "captures_detected": captures_detected,
        }

    def _phase_emit_orbital_map(self) -> Dict[str, Any]:
        """Emit phase: emit the full orbital map with stars, bodies, paths."""
        emitted = 0
        for body in self._bodies.values():
            if body.state != BodyState.ANALYZED:
                continue
            body.state = BodyState.EMITTED
            emitted += 1
        # Stamp concept-stars vitality based on the body population.
        for concept in self._concepts.values():
            concept.vitality = self._derive_vitality(concept.concept_id)
        # Build editor paths - one concentric path per body's orbit.
        for body in self._bodies.values():
            if body.state != BodyState.EMITTED:
                continue
            path_id = (
                f"path_{body.body_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            path = {
                "path_id": path_id,
                "body_id": body.body_id,
                "concept_id": body.concept_id,
                "orbital_radius": body.orbital_radius,
                "eccentricity": body.eccentricity,
                "orbit_class": body.orbit_class.value,
                "sense_facet": body.sense_facet.value,
                "color": self._color_for_orbit_class(body.orbit_class),
                "line_weight": 0.5 + (1.0 - body.eccentricity) * 2.0,
                "visible": True,
                "preview_url": f"/preview/orbital/{path_id}.svg",
                "state": "emitted",
                "created_at": time.time(),
            }
            # Cap the path collection.
            if len(self._paths) >= self._MAX_PATHS:
                oldest_key = next(iter(self._paths))
                self._paths.pop(oldest_key, None)
            self._paths[path_id] = path
        map_size = (
            len(self._concepts) + len(self._bodies)
            + len(self._paths) + len(self._escapes)
        )
        self._update_stats(phase_runs=1, orbital_maps_emitted=1)
        self._record_event("phase_emit_orbital_map", {
            "emitted": emitted,
            "map_size": map_size,
        })
        return {
            "phase": "emit_orbital_map",
            "emitted": emitted,
            "map_size": map_size,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_concept_by_id(self, concept_id: str) -> Optional[ConceptStar]:
        """Find a concept-star by its concept_id (linear scan over handles)."""
        for concept in self._concepts.values():
            if concept.concept_id == concept_id:
                return concept
        return None

    def _derive_vitality(self, concept_id: str) -> Vitality:
        """Derive vitality for a concept-star from its body population."""
        body_count = sum(
            1 for b in self._bodies.values() if b.concept_id == concept_id
        )
        escaping_count = sum(
            1 for b in self._bodies.values()
            if b.concept_id == concept_id and b.orbit_class == OrbitClass.ESCAPING
        )
        if body_count == 0:
            return Vitality.DORMANT
        if escaping_count >= 2:
            return Vitality.CHAOTIC
        if body_count <= 1:
            return Vitality.STIRRING
        if body_count <= 3:
            return Vitality.ORBITING
        return Vitality.DYNAMIC

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_concepts(self) -> None:
        """Seed a few synthetic concept-stars on the first cycle if empty."""
        seeds = [
            (
                "concept::resonance",
                "Resonance",
                4.5,
                ConceptKind.ABSTRACT,
            ),
            (
                "concept::bridge",
                "Bridge",
                2.5,
                ConceptKind.RELATIONAL,
            ),
            (
                "concept::forge",
                "Forge",
                3.2,
                ConceptKind.PROCEDURAL,
            ),
        ]
        for concept_handle, label, semantic_mass, kind in seeds:
            if concept_handle in self._concepts:
                continue
            if len(self._concepts) >= self._MAX_CONCEPTS:
                break
            self.register_concept(
                concept_handle=concept_handle,
                label=label,
                semantic_mass=semantic_mass,
                kind=kind.value,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _concept_to_dict(self, concept: ConceptStar) -> Dict[str, Any]:
        return {
            "concept_id": concept.concept_id,
            "concept_handle": concept.concept_handle,
            "label": concept.label,
            "semantic_mass": concept.semantic_mass,
            "kind": concept.kind.value,
            "escape_velocity": concept.escape_velocity,
            "active": concept.active,
            "vitality": concept.vitality.value,
            "created_at": concept.created_at,
            "last_propagated_at": concept.last_propagated_at,
            "note": concept.note,
        }

    def _body_to_dict(self, body: OrbitalBody) -> Dict[str, Any]:
        return {
            "body_id": body.body_id,
            "concept_id": body.concept_id,
            "label": body.label,
            "orbital_radius": body.orbital_radius,
            "angular_position": body.angular_position,
            "eccentricity": body.eccentricity,
            "orbit_class": body.orbit_class.value,
            "sense_facet": body.sense_facet.value,
            "angular_velocity": body.angular_velocity,
            "drift_rate": body.drift_rate,
            "escape_signal": body.escape_signal,
            "captured": body.captured,
            "state": body.state.value,
            "created_at": body.created_at,
            "last_drift_at": body.last_drift_at,
            "note": body.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "concepts": len(self._concepts),
                "bodies": len(self._bodies),
                "paths": len(self._paths),
                "drifts": len(self._drifts),
                "escapes": len(self._escapes),
                "stats": dict(self._stats),
            }

    def get_concepts(self, limit: int = 50) -> Dict[str, Any]:
        with self._global_lock:
            concepts = sorted(
                self._concepts.values(),
                key=lambda c: c.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(concepts),
                "concepts": [
                    {
                        "concept_id": c.concept_id,
                        "concept_handle": c.concept_handle,
                        "label": c.label,
                        "semantic_mass": c.semantic_mass,
                        "kind": c.kind.value,
                        "escape_velocity": c.escape_velocity,
                        "vitality": c.vitality.value,
                        "active": c.active,
                    }
                    for c in concepts
                ],
            }

    def get_concept(self, concept_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by concept_handle, NOT concept_id, so we
        # MUST iterate over values and match on the concept_id attribute.
        with self._global_lock:
            for concept in self._concepts.values():
                if concept.concept_id == concept_id:
                    return self._concept_to_dict(concept)
            return {
                "error": f"Concept not found: {concept_id}",
                "concept_id": concept_id,
            }

    def get_orbital_map(self) -> Dict[str, Any]:
        """Return the full orbital map with concepts, bodies, paths, and escapes."""
        with self._global_lock:
            return {
                "concepts": [self._concept_to_dict(c) for c in self._concepts.values()],
                "bodies": [self._body_to_dict(b) for b in self._bodies.values()],
                "paths": list(self._paths.values()),
                "drifts": list(self._drifts.values()),
                "escapes": list(self._escapes.values()),
                "concept_count": len(self._concepts),
                "body_count": len(self._bodies),
                "path_count": len(self._paths),
                "drift_count": len(self._drifts),
                "escape_count": len(self._escapes),
                "cycle_count": self._cycle_count,
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic concepts if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._concepts:
                self._seed_synthetic_concepts()
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
            self._concepts.clear()
            self._bodies.clear()
            self._paths.clear()
            self._drifts.clear()
            self._escapes.clear()
            self._phase = OrbitalPhase.REGISTER_CONCEPT
            self._cycle_count = 0
            self._init_stats()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }
