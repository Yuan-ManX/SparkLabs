"""
SparkLabs Engine - Layered Locomotion Choreographer"""

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

class LocomotionChoreographyPhase(Enum):
    """Phases of the layered locomotion cycle."""
    NAVIGATE = "navigate"    # goal-directed steering
    AVOID = "avoid"          # obstacle evasion
    FORM = "form"            # group cohesion / spacing
    SIGN = "sign"            # idiosyncratic motion signature
    BLEND = "blend"          # weighted blend into a single directive


class NavigationIntent(Enum):
    """Why an entity is steering toward a goal."""
    DIRECT = "direct"        # head straight to the goal
    INTERCEPT = "intercept"  # head to where a moving goal will be
    FLEE = "flee"            # head away from the goal
    PATROL = "patrol"        # cycle through a set of goals
    HOLD = "hold"            # stay near the goal


class AvoidanceKind(Enum):
    """What an entity is dodging."""
    NONE = "none"
    STATIC_OBSTACLE = "static_obstacle"
    MOVING_AGENT = "moving_agent"
    HAZARD_ZONE = "hazard_zone"
    CROWD = "crowd"


class FormationRole(Enum):
    """How an entity fits into a group shape."""
    LEADER = "leader"
    WING = "wing"
    CORE = "core"
    SCOUT = "scout"
    LONE = "lone"


class MotionSignature(Enum):
    """How an entity uniquely moves."""
    LITERAL = "literal"      # no embellishment, follow the blend exactly
    DRIFTING = "drifting"    # slow wandering bias
    PULSE = "pulse"          # surging, sinusoidal forward weight
    WEAVING = "weaving"      # side-to-side lateral bias
    STOMPING = "stomping"    # quantized, heavy steps
    GLIDING = "gliding"      # low-amplitude smooth bias


class LocomotionState(Enum):
    """State of an entity's blended locomotion."""
    IDLE = "idle"
    SEEKING = "seeking"
    DODGING = "dodging"
    HOLDING_FORM = "holding_form"
    MOVING = "moving"
    ARRIVED = "arrived"


class MotionVitality(Enum):
    """Overall vitality of the locomotion field."""
    DORMANT = "dormant"      # no profiles registered
    COHERENT = "coherent"    # everyone arrived, motion settled
    FLOWING = "flowing"      # active, well-blended motion
    FRACTURED = "fractured"  # high avoidance pressure, jittery
    JAMMED = "jammed"        # too many stuck entities


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NavigationLayer:
    """Goal-directed steering layer."""
    entity_id: str
    goal_position: Dict[str, float]
    steering_vector: Dict[str, float]
    speed: float
    intent: NavigationIntent
    distance_to_goal: float


@dataclass
class AvoidanceLayer:
    """Obstacle evasion layer."""
    entity_id: str
    evasion_vector: Dict[str, float]
    primary_kind: AvoidanceKind
    pressure: float                  # 0.0-1.0
    nearby_count: int


@dataclass
class FormationLayer:
    """Group cohesion / spacing layer."""
    entity_id: str
    role: FormationRole
    squad_id: str
    cohesion_vector: Dict[str, float]
    spacing: float
    squad_size: int


@dataclass
class SignatureLayer:
    """Idiosyncratic motion signature layer."""
    entity_id: str
    signature: MotionSignature
    bias_vector: Dict[str, float]
    amplitude: float
    frequency: float


@dataclass
class LocomotionDirective:
    """The blended unified directive emitted per entity per tick."""
    entity_id: str
    linear_vector: Dict[str, float]
    angular: float
    speed: float
    confidence: float
    state: LocomotionState
    layers: Dict[str, Any]
    cycle: int


@dataclass
class LocomotionProfile:
    """A registered entity's locomotion profile."""
    profile_id: str
    entity_id: str
    goal_position: Dict[str, float]
    current_position: Dict[str, float]
    speed: float = 1.0
    signature: MotionSignature = MotionSignature.LITERAL
    role: FormationRole = FormationRole.LONE
    intent: NavigationIntent = NavigationIntent.DIRECT
    squad_id: str = "solo"
    last_directive: Optional[LocomotionDirective] = None
    created_at: float = field(default_factory=time.time)
    total_directives: int = 0
    distance_traveled: float = 0.0


# =============================================================================
# Choreographer
# =============================================================================

class LayeredLocomotionChoreographer:
    """
    Thread-safe singleton orchestrating multi-layer locomotion blending.

    Usage:
        choreo = LayeredLocomotionChoreographer.get_instance()
        choreo.register_profile("e1", {"x": 10, "y": 0})
        choreo.cycle()
        status = choreo.get_status()
    """

    _instance: Optional["LayeredLocomotionChoreographer"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _MAX_PROFILES = 50
    _MAX_EVENTS = 200
    _BLEND_WEIGHT_NAV = 0.45
    _BLEND_WEIGHT_AVOID = 0.30
    _BLEND_WEIGHT_FORM = 0.15
    _BLEND_WEIGHT_SIGN = 0.10
    _ARRIVAL_DISTANCE = 0.5
    _AVOID_RADIUS = 3.0
    _VITALITY_JAM_THRESHOLD = 12
    _STEP_DT = 1.0  # tick delta for position integration

    def __init__(self) -> None:
        self._profiles: Dict[str, LocomotionProfile] = {}
        self._phase: LocomotionChoreographyPhase = LocomotionChoreographyPhase.NAVIGATE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "LayeredLocomotionChoreographer":
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
            "total_profiles": 0,
            "active_profiles": 0,
            "total_directives": 0,
            "total_navigations": 0,
            "total_avoidances": 0,
            "total_formations": 0,
            "total_signatures": 0,
            "arrivals": 0,
            "avg_confidence": 0.0,
            "avg_speed": 0.0,
            "avg_pressure": 0.0,
            "vitality": MotionVitality.DORMANT.value,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self, **kwargs: Any) -> None:
        # Aggregate per-profile stats after a cycle.
        active = len(self._profiles)
        confidences: List[float] = []
        speeds: List[float] = []
        pressures: List[float] = []
        arrivals = 0
        for profile in self._profiles.values():
            directive = profile.last_directive
            if directive is None:
                continue
            confidences.append(directive.confidence)
            speeds.append(directive.speed)
            layers = self._pending.get(profile.entity_id, {})
            avoid_layer = layers.get("avoid")
            pressures.append(avoid_layer.pressure if avoid_layer else 0.0)
            if directive.state == LocomotionState.ARRIVED:
                arrivals += 1
        self._stats["active_profiles"] = active
        self._stats["arrivals"] = arrivals
        self._stats["avg_confidence"] = (
            sum(confidences) / len(confidences) if confidences else 0.0
        )
        self._stats["avg_speed"] = sum(speeds) / len(speeds) if speeds else 0.0
        self._stats["avg_pressure"] = (
            sum(pressures) / len(pressures) if pressures else 0.0
        )
        # Derive overall vitality from the blended field.
        self._stats["vitality"] = self._derive_vitality().value
        # Allow optional overrides.
        for key, value in kwargs.items():
            self._stats[key] = value

    def _derive_vitality(self) -> MotionVitality:
        active = self._stats.get("active_profiles", 0)
        if active == 0:
            return MotionVitality.DORMANT
        arrivals = self._stats.get("arrivals", 0)
        avg_conf = self._stats.get("avg_confidence", 0.0)
        avg_pressure = self._stats.get("avg_pressure", 0.0)
        if arrivals == active:
            return MotionVitality.COHERENT
        if avg_pressure > 0.6:
            return MotionVitality.FRACTURED
        if active >= self._VITALITY_JAM_THRESHOLD and avg_conf < 0.3:
            return MotionVitality.JAMMED
        return MotionVitality.FLOWING

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Vector helpers (operate on dict vectors of any dimension)
    # -------------------------------------------------------------------------

    @staticmethod
    def _vec_sub(a: Dict[str, float], b: Dict[str, float]) -> Dict[str, float]:
        keys = set(a) | set(b)
        return {k: a.get(k, 0.0) - b.get(k, 0.0) for k in keys}

    @staticmethod
    def _vec_add(a: Dict[str, float], b: Dict[str, float]) -> Dict[str, float]:
        keys = set(a) | set(b)
        return {k: a.get(k, 0.0) + b.get(k, 0.0) for k in keys}

    @staticmethod
    def _vec_scale(v: Dict[str, float], s: float) -> Dict[str, float]:
        return {k: val * s for k, val in v.items()}

    @staticmethod
    def _vec_magnitude(v: Dict[str, float]) -> float:
        return math.sqrt(sum(val * val for val in v.values()))

    def _vec_normalize(self, v: Dict[str, float]) -> Dict[str, float]:
        mag = self._vec_magnitude(v)
        if mag < 1e-9:
            return {k: 0.0 for k in v}
        return {k: val / mag for k, val in v.items()}

    # -------------------------------------------------------------------------
    # Profile Management
    # -------------------------------------------------------------------------

    def register_profile(self, entity_id: str, goal_position: Dict[str, float],
                         speed: Optional[float] = None,
                         signature: Optional[str] = None) -> Dict[str, Any]:
        """Register a new entity locomotion profile."""
        with self._global_lock:
            if entity_id in self._profiles:
                return {"error": f"Profile already registered: {entity_id}"}
            if len(self._profiles) >= self._MAX_PROFILES:
                return {"error": f"Profile cap reached ({self._MAX_PROFILES})"}
            try:
                sig = MotionSignature(signature) if signature else MotionSignature.LITERAL
            except ValueError:
                return {"error": f"Invalid signature: {signature}"}
            profile = LocomotionProfile(
                profile_id=f"profile_{entity_id}",
                entity_id=entity_id,
                goal_position=dict(goal_position),
                current_position={k: 0.0 for k in goal_position},
                speed=float(speed) if speed is not None else 1.0,
                signature=sig,
            )
            self._profiles[entity_id] = profile
            self._stats["total_profiles"] += 1
            self._record_event("profile_registered", {
                "entity_id": entity_id,
                "goal_position": profile.goal_position,
                "speed": profile.speed,
                "signature": sig.value,
            })
            return {
                "profile_id": profile.profile_id,
                "entity_id": entity_id,
                "goal_position": profile.goal_position,
                "current_position": profile.current_position,
                "speed": profile.speed,
                "signature": sig.value,
            }

    def remove_profile(self, entity_id: str) -> Dict[str, Any]:
        with self._global_lock:
            profile = self._profiles.pop(entity_id, None)
            if profile is None:
                return {"error": f"Profile not found: {entity_id}"}
            self._record_event("profile_removed", {"entity_id": entity_id})
            return {"removed": entity_id}

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single layered locomotion cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            self._pending = {}
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = LocomotionChoreographyPhase.NAVIGATE
            phase_outputs.append(self._phase_navigate())
            self._phase = LocomotionChoreographyPhase.AVOID
            phase_outputs.append(self._phase_avoid())
            self._phase = LocomotionChoreographyPhase.FORM
            phase_outputs.append(self._phase_form())
            self._phase = LocomotionChoreographyPhase.SIGN
            phase_outputs.append(self._phase_sign())
            self._phase = LocomotionChoreographyPhase.BLEND
            phase_outputs.append(self._phase_blend())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_navigate(self) -> Dict[str, Any]:
        """NAVIGATE: compute goal-directed steering for each profile."""
        navigated = 0
        for profile in self._profiles.values():
            nav = self._compute_navigation(profile)
            self._pending.setdefault(profile.entity_id, {})["navigate"] = nav
            navigated += 1
        self._stats["total_navigations"] += navigated
        self._record_event("phase_navigate", {"navigated": navigated})
        return {
            "phase": LocomotionChoreographyPhase.NAVIGATE.value,
            "navigated": navigated,
        }

    def _phase_avoid(self) -> Dict[str, Any]:
        """AVOID: compute obstacle evasion for each profile."""
        avoided = 0
        for profile in self._profiles.values():
            avd = self._compute_avoidance(profile)
            self._pending.setdefault(profile.entity_id, {})["avoid"] = avd
            if avd.primary_kind != AvoidanceKind.NONE:
                avoided += 1
        self._stats["total_avoidances"] += avoided
        self._record_event("phase_avoid", {"avoided": avoided})
        return {
            "phase": LocomotionChoreographyPhase.AVOID.value,
            "avoided": avoided,
        }

    def _phase_form(self) -> Dict[str, Any]:
        """FORM: compute formation cohesion for each profile."""
        formed = 0
        for profile in self._profiles.values():
            form = self._compute_formation(profile)
            self._pending.setdefault(profile.entity_id, {})["form"] = form
            if form.role != FormationRole.LONE:
                formed += 1
        self._stats["total_formations"] += formed
        self._record_event("phase_form", {"formed": formed})
        return {
            "phase": LocomotionChoreographyPhase.FORM.value,
            "formed": formed,
        }

    def _phase_sign(self) -> Dict[str, Any]:
        """SIGN: apply idiosyncratic motion signature for each profile."""
        signed = 0
        for profile in self._profiles.values():
            sig = self._compute_signature(profile)
            self._pending.setdefault(profile.entity_id, {})["sign"] = sig
            if sig.signature != MotionSignature.LITERAL:
                signed += 1
        self._stats["total_signatures"] += signed
        self._record_event("phase_sign", {"signed": signed})
        return {
            "phase": LocomotionChoreographyPhase.SIGN.value,
            "signed": signed,
        }

    def _phase_blend(self) -> Dict[str, Any]:
        """BLEND: weighted blend of all layers into a unified directive."""
        blended = 0
        for profile in self._profiles.values():
            directive = self._blend_layers(profile)
            profile.last_directive = directive
            profile.total_directives += 1
            # Integrate position by the blended linear vector.
            step = self._vec_scale(directive.linear_vector, self._STEP_DT)
            profile.current_position = {
                k: profile.current_position.get(k, 0.0) + step.get(k, 0.0)
                for k in set(profile.current_position) | set(step)
            }
            profile.distance_traveled += self._vec_magnitude(step)
            blended += 1
        self._stats["total_directives"] += blended
        self._record_event("phase_blend", {"blended": blended})
        return {
            "phase": LocomotionChoreographyPhase.BLEND.value,
            "blended": blended,
        }

    # -------------------------------------------------------------------------
    # Layer computations
    # -------------------------------------------------------------------------

    def _compute_navigation(self, profile: LocomotionProfile) -> NavigationLayer:
        goal = profile.goal_position
        cur = profile.current_position
        diff = self._vec_sub(goal, cur)
        distance = self._vec_magnitude(diff)
        direction = self._vec_normalize(diff)
        steering = self._vec_scale(direction, profile.speed)
        if distance <= self._ARRIVAL_DISTANCE:
            intent = NavigationIntent.HOLD
        else:
            intent = profile.intent
        return NavigationLayer(
            entity_id=profile.entity_id,
            goal_position=dict(goal),
            steering_vector=steering,
            speed=profile.speed,
            intent=intent,
            distance_to_goal=distance,
        )

    def _compute_avoidance(self, profile: LocomotionProfile) -> AvoidanceLayer:
        evasion = {k: 0.0 for k in profile.current_position}
        nearby = 0
        primary_kind = AvoidanceKind.NONE
        max_pressure = 0.0
        for other in self._profiles.values():
            if other.entity_id == profile.entity_id:
                continue
            diff = self._vec_sub(profile.current_position, other.current_position)
            dist = self._vec_magnitude(diff)
            if dist >= self._AVOID_RADIUS or dist < 1e-6:
                continue
            nearby += 1
            strength = (self._AVOID_RADIUS - dist) / self._AVOID_RADIUS
            push = self._vec_scale(self._vec_normalize(diff), strength)
            evasion = self._vec_add(evasion, push)
            max_pressure = max(max_pressure, strength)
            if strength > 0.5:
                primary_kind = AvoidanceKind.MOVING_AGENT
        # A dense cluster of nearby agents reads as a crowd.
        if nearby >= 3 and primary_kind == AvoidanceKind.NONE:
            primary_kind = AvoidanceKind.CROWD
        pressure = min(1.0, max_pressure)
        return AvoidanceLayer(
            entity_id=profile.entity_id,
            evasion_vector=evasion,
            primary_kind=primary_kind,
            pressure=pressure,
            nearby_count=nearby,
        )

    def _compute_formation(self, profile: LocomotionProfile) -> FormationLayer:
        squadmates = [
            p for p in self._profiles.values()
            if p.squad_id == profile.squad_id and p.entity_id != profile.entity_id
        ]
        if not squadmates or profile.squad_id == "solo":
            return FormationLayer(
                entity_id=profile.entity_id,
                role=FormationRole.LONE,
                squad_id=profile.squad_id,
                cohesion_vector={k: 0.0 for k in profile.current_position},
                spacing=0.0,
                squad_size=1,
            )
        # Centroid of the squad (including self).
        members = squadmates + [profile]
        centroid: Dict[str, float] = {}
        for m in members:
            for k, v in m.current_position.items():
                centroid[k] = centroid.get(k, 0.0) + v
        centroid = {k: v / len(members) for k, v in centroid.items()}
        cohesion = self._vec_normalize(self._vec_sub(centroid, profile.current_position))
        spacing = (
            sum(self._vec_magnitude(self._vec_sub(profile.current_position, m.current_position))
                for m in squadmates) / len(squadmates)
        )
        return FormationLayer(
            entity_id=profile.entity_id,
            role=profile.role,
            squad_id=profile.squad_id,
            cohesion_vector=cohesion,
            spacing=spacing,
            squad_size=len(members),
        )

    def _compute_signature(self, profile: LocomotionProfile) -> SignatureLayer:
        sig = profile.signature
        bias: Dict[str, float] = {k: 0.0 for k in profile.current_position}
        amplitude = 0.0
        frequency = 1.0
        if sig == MotionSignature.LITERAL:
            pass
        elif sig == MotionSignature.DRIFTING:
            bias = {k: random.uniform(-0.1, 0.1) for k in bias}
            amplitude = 0.1
            frequency = 1.0
        elif sig == MotionSignature.PULSE:
            # Forward weight surges sinusoidally across the cycle.
            phase = (self._cycle_count % 10) / 10.0
            surge = 0.5 + 0.5 * math.sin(phase * 2 * math.pi)
            bias = {k: surge * 0.2 for k in bias}
            amplitude = 0.2
            frequency = 2.0
        elif sig == MotionSignature.WEAVING:
            # Lateral bias alternates by cycle parity.
            lateral = 0.3 if (self._cycle_count % 2 == 0) else -0.3
            keys = list(bias.keys())
            if keys:
                bias[keys[0]] = lateral
            amplitude = 0.3
            frequency = 1.0
        elif sig == MotionSignature.STOMPING:
            # Quantized heavy steps; only every third tick carries weight.
            step = 1.0 if (self._cycle_count % 3 == 0) else 0.0
            bias = {k: step * 0.4 for k in bias}
            amplitude = 0.4
            frequency = 0.33
        elif sig == MotionSignature.GLIDING:
            # Low-amplitude smooth sinusoidal bias.
            phase = (self._cycle_count % 12) / 12.0
            glide = 0.1 * math.sin(phase * 2 * math.pi)
            bias = {k: glide for k in bias}
            amplitude = 0.1
            frequency = 1.0
        return SignatureLayer(
            entity_id=profile.entity_id,
            signature=sig,
            bias_vector=bias,
            amplitude=amplitude,
            frequency=frequency,
        )

    def _blend_layers(self, profile: LocomotionProfile) -> LocomotionDirective:
        layers = self._pending.get(profile.entity_id, {})
        nav = layers.get("navigate")
        avd = layers.get("avoid")
        form = layers.get("form")
        sig = layers.get("sign")
        # Fallbacks if a layer is missing (defensive; should not normally happen).
        if nav is None:
            nav = self._compute_navigation(profile)
        if avd is None:
            avd = self._compute_avoidance(profile)
        if form is None:
            form = self._compute_formation(profile)
        if sig is None:
            sig = self._compute_signature(profile)

        nav_vec = self._vec_scale(nav.steering_vector, self._BLEND_WEIGHT_NAV)
        avd_vec = self._vec_scale(avd.evasion_vector, self._BLEND_WEIGHT_AVOID)
        form_vec = self._vec_scale(form.cohesion_vector, self._BLEND_WEIGHT_FORM)
        sig_vec = self._vec_scale(sig.bias_vector, self._BLEND_WEIGHT_SIGN)
        linear = self._vec_add(self._vec_add(nav_vec, avd_vec),
                               self._vec_add(form_vec, sig_vec))

        pressure = avd.pressure
        # Avoidance pressure slows the entity; it cannot fully halt it.
        speed = profile.speed * (1.0 - pressure * 0.5)
        # Confidence drops with avoidance pressure and rises near the goal.
        arrival_factor = max(0.0, 1.0 - nav.distance_to_goal / 10.0)
        confidence = max(0.0, min(1.0, 0.8 - pressure * 0.5 + arrival_factor * 0.2))

        # Derive the locomotion state from the dominant layer signal.
        if nav.distance_to_goal <= self._ARRIVAL_DISTANCE:
            state = LocomotionState.ARRIVED
        elif pressure > 0.4:
            state = LocomotionState.DODGING
        elif form.role != FormationRole.LONE and self._vec_magnitude(form.cohesion_vector) > 0.3:
            state = LocomotionState.HOLDING_FORM
        elif self._vec_magnitude(linear) < 1e-3:
            state = LocomotionState.IDLE
        else:
            state = LocomotionState.MOVING

        # Angular hint derived from the lateral component of the linear vector.
        angular = 0.0
        keys = list(linear.keys())
        if len(keys) >= 2:
            angular = math.atan2(linear.get(keys[1], 0.0), linear.get(keys[0], 0.0))

        return LocomotionDirective(
            entity_id=profile.entity_id,
            linear_vector=linear,
            angular=angular,
            speed=speed,
            confidence=confidence,
            state=state,
            layers={
                "navigate": self._layer_to_dict(nav, "navigate"),
                "avoid": self._layer_to_dict(avd, "avoid"),
                "form": self._layer_to_dict(form, "form"),
                "sign": self._layer_to_dict(sig, "sign"),
            },
            cycle=self._cycle_count,
        )

    # -------------------------------------------------------------------------
    # Serialization helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _layer_to_dict(layer: Any, kind: str) -> Dict[str, Any]:
        if kind == "navigate":
            return {
                "entity_id": layer.entity_id,
                "goal_position": layer.goal_position,
                "steering_vector": layer.steering_vector,
                "speed": layer.speed,
                "intent": layer.intent.value,
                "distance_to_goal": layer.distance_to_goal,
            }
        if kind == "avoid":
            return {
                "entity_id": layer.entity_id,
                "evasion_vector": layer.evasion_vector,
                "primary_kind": layer.primary_kind.value,
                "pressure": layer.pressure,
                "nearby_count": layer.nearby_count,
            }
        if kind == "form":
            return {
                "entity_id": layer.entity_id,
                "role": layer.role.value,
                "squad_id": layer.squad_id,
                "cohesion_vector": layer.cohesion_vector,
                "spacing": layer.spacing,
                "squad_size": layer.squad_size,
            }
        if kind == "sign":
            return {
                "entity_id": layer.entity_id,
                "signature": layer.signature.value,
                "bias_vector": layer.bias_vector,
                "amplitude": layer.amplitude,
                "frequency": layer.frequency,
            }
        return {}

    @staticmethod
    def _directive_to_dict(directive: LocomotionDirective) -> Dict[str, Any]:
        return {
            "entity_id": directive.entity_id,
            "linear_vector": directive.linear_vector,
            "angular": directive.angular,
            "speed": directive.speed,
            "confidence": directive.confidence,
            "state": directive.state.value,
            "layers": directive.layers,
            "cycle": directive.cycle,
        }

    @staticmethod
    def _profile_to_dict(profile: LocomotionProfile) -> Dict[str, Any]:
        return {
            "profile_id": profile.profile_id,
            "entity_id": profile.entity_id,
            "goal_position": profile.goal_position,
            "current_position": profile.current_position,
            "speed": profile.speed,
            "signature": profile.signature.value,
            "role": profile.role.value,
            "intent": profile.intent.value,
            "squad_id": profile.squad_id,
            "total_directives": profile.total_directives,
            "distance_traveled": profile.distance_traveled,
            "created_at": profile.created_at,
            "last_directive": (
                LayeredLocomotionChoreographer._directive_to_dict(profile.last_directive)
                if profile.last_directive else None
            ),
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "profiles": len(self._profiles),
                "stats": dict(self._stats),
            }

    def get_profiles(self) -> List[Dict[str, Any]]:
        with self._global_lock:
            return [self._profile_to_dict(p) for p in self._profiles.values()]

    def get_profile(self, profile_id: str) -> Dict[str, Any]:
        with self._global_lock:
            # Accept either the profile_id or the entity_id.
            profile = self._profiles.get(profile_id)
            if profile is None:
                for p in self._profiles.values():
                    if p.profile_id == profile_id:
                        profile = p
                        break
            if profile is None:
                return {"error": f"Profile not found: {profile_id}"}
            return self._profile_to_dict(profile)

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic profiles, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_profiles()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_profiles(self) -> None:
        """Seed a small synthetic set of entity locomotion profiles."""
        seeds = [
            ("sim_alpha", {"x": 8.0, "y": 0.0}, 1.2, "pulse", "leader", "sim_squad_a"),
            ("sim_beta", {"x": 8.0, "y": 2.0}, 1.0, "weaving", "wing", "sim_squad_a"),
            ("sim_gamma", {"x": 8.0, "y": -2.0}, 1.0, "drifting", "wing", "sim_squad_a"),
            ("sim_delta", {"x": -5.0, "y": 5.0}, 1.5, "stomping", "lone", "solo"),
            ("sim_epsilon", {"x": 0.0, "y": 10.0}, 0.8, "gliding", "scout", "sim_squad_b"),
            ("sim_zeta", {"x": 1.0, "y": 10.0}, 0.8, "literal", "core", "sim_squad_b"),
        ]
        for entity_id, goal, speed, signature, role, squad_id in seeds:
            if entity_id in self._profiles:
                continue
            if len(self._profiles) >= self._MAX_PROFILES:
                break
            try:
                sig = MotionSignature(signature)
            except ValueError:
                sig = MotionSignature.LITERAL
            try:
                role_enum = FormationRole(role)
            except ValueError:
                role_enum = FormationRole.LONE
            profile = LocomotionProfile(
                profile_id=f"profile_{entity_id}",
                entity_id=entity_id,
                goal_position=dict(goal),
                current_position={k: 0.0 for k in goal},
                speed=float(speed),
                signature=sig,
                role=role_enum,
                squad_id=squad_id,
            )
            self._profiles[entity_id] = profile
            self._stats["total_profiles"] += 1

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._profiles.clear()
            self._pending.clear()
            self._events_log.clear()
            self._phase = LocomotionChoreographyPhase.NAVIGATE
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
