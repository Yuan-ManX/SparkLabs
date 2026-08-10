"""
SparkLabs Engine - Perceptual Grain Modulator"""

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

class GrainPhase(Enum):
    """Phases of the perceptual grain cycle."""
    SAMPLE = "sample"          # read the current perceptual demand signals
    ANALYZE = "analyze"        # compute legibility budget and engagement deficit
    MODULATE = "modulate"      # adjust each scene's grain level
    RENDER = "render"          # emit a grain signature per scene
    SETTLE = "settle"          # dampen oscillation, record settled signature


class GrainLevel(Enum):
    """The grain level on the fine -> coarse continuum."""
    ULTRA_FINE = "ultra_fine"    # every leaf and rivet legible
    FINE = "fine"                # most surface detail legible
    MEDIUM = "medium"            # shapes and key features legible
    COARSE = "coarse"            # only silhouettes and mood survive
    ULTRA_COARSE = "ultra_coarse"  # only gesture and atmosphere survive


class DemandSignal(Enum):
    """The perceptual demand signals a scene reports."""
    ATTENTION_LOAD = "attention_load"            # how much focus the scene asks for
    EMOTIONAL_WEIGHT = "emotional_weight"        # how heavy the scene feels
    NARRATIVE_VELOCITY = "narrative_velocity"    # how fast the story is moving
    SENSORIMOTOR_DEMAND = "sensorimotor_demand"  # how much doing the scene asks for
    SCENE_DENSITY = "scene_density"              # how much stuff is packed in


class FadeBehavior(Enum):
    """What happens to a detail when grain coarsens past it."""
    PRESERVE = "preserve"    # the detail survives even at coarse grain
    SOFTEN = "soften"        # the detail softens but stays visible
    BLUR = "blur"            # the detail blurs into an impression
    DROP = "drop"            # the detail vanishes, leaving only mood


class GrainState(Enum):
    """State of an individual scene's grain modulation."""
    SAMPLING = "sampling"            # demand signals are being read
    ANALYZING = "analyzing"          # budget and deficit are being computed
    MODULATING = "modulating"        # grain level is being adjusted
    RENDERING = "rendering"          # signature is being emitted
    SETTLED = "settled"              # signature has settled
    OVERCORRECTING = "overcorrecting"  # grain is swinging too fast


class GrainVitality(Enum):
    """The overall vitality of the perceptual grain ecosystem."""
    DORMANT = "dormant"              # few scenes, little demand
    TRACKING = "tracking"            # scenes are being sampled and analyzed
    RESPONSIVE = "responsive"        # grain is breathing cleanly with demand
    OVERCORRECTING = "overcorrecting"  # grain is swinging too fast
    SATURATED = "saturated"          # too many scenes at the same grain extreme


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SceneDemand:
    """A single demand signal reported for a scene."""
    scene_id: str
    signal: DemandSignal
    value: float = 0.5                  # 0.0-1.0
    note: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class GrainSignature:
    """The grain signature emitted for a scene."""
    scene_id: str
    grain_level: GrainLevel = GrainLevel.MEDIUM
    legibility_budget: float = 0.5      # 0.0-1.0, how much detail the player can absorb
    engagement_deficit: float = 0.0     # 0.0-1.0, how much detail would pull them in
    survives: List[str] = field(default_factory=list)   # details that survive at this grain
    fades: List[str] = field(default_factory=list)      # details that fade at this grain
    focal_priority: float = 0.5         # 0.0-1.0, where the eye should be drawn
    timestamp: float = field(default_factory=time.time)


@dataclass
class ModulatorCycleResult:
    """Summary of a single perceptual grain cycle."""
    cycle_count: int
    phase: GrainPhase
    scenes_sampled: int = 0
    grain_adjustments: int = 0
    signatures_emitted: int = 0
    oscillations_dampened: int = 0
    overcorrections: int = 0


# =============================================================================
# Modulator
# =============================================================================

class EnginePerceptualGrainModulator:
    """
    Thread-safe singleton orchestrating perceptual grain modulation.

    Usage:
        modulator = EnginePerceptualGrainModulator.get_instance()
        modulator.register_scene("market_square")
        modulator.report_demand("market_square", "attention_load", 0.8)
        modulator.cycle()
        signature = modulator.get_signature("market_square")
    """

    _instance: Optional["EnginePerceptualGrainModulator"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Tuning constants
    _MAX_SCENES = 64
    _MAX_DEMAND_SIGNALS = 8           # per scene, rolling window
    _MAX_FADES = 32                   # details that fade per signature
    _MAX_SURVIVES = 32                # details that survive per signature
    _MAX_EVENTS = 200
    _LEGIBILITY_DAMPING = 0.6         # how strongly demand shrinks the budget
    _ENGAGEMENT_GAIN = 0.5            # how strongly thin scenes widen the deficit
    _OSCILLATION_THRESHOLD = 2        # grain swings per cycle before damping
    _OVERCORRECTION_THRESHOLD = 3     # consecutive swings before overcorrecting
    _SETTLE_DECAY = 0.7               # how fast a fresh grain level settles

    # Mapping from grain level to a numeric position on the fine -> coarse axis.
    _GRAIN_ORDER: Dict[GrainLevel, int] = {
        GrainLevel.ULTRA_FINE: 0,
        GrainLevel.FINE: 1,
        GrainLevel.MEDIUM: 2,
        GrainLevel.COARSE: 3,
        GrainLevel.ULTRA_COARSE: 4,
    }

    def __init__(self) -> None:
        self._scenes: Dict[str, dict] = {}
        self._signatures: Dict[str, GrainSignature] = {}
        self._phase: GrainPhase = GrainPhase.SAMPLE
        self._state: GrainState = GrainState.SAMPLING
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EnginePerceptualGrainModulator":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    def _init_stats(self) -> Dict[str, Any]:
        self._stats = {
            "cycles_completed": 0,
            "scenes_sampled": 0,
            "grain_adjustments": 0,
            "fine_grain_emitted": 0,
            "coarse_grain_emitted": 0,
            "oscillations_dampened": 0,
            "overcorrections": 0,
            "last_cycle_at": 0.0,
            "uptime_started_at": time.time(),
        }
        return self._stats

    def _update_stats(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if key in self._stats:
                if isinstance(value, (int, float)):
                    self._stats[key] += value
                else:
                    self._stats[key] = value
            else:
                self._stats[key] = value

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Scene Management
    # -------------------------------------------------------------------------

    def register_scene(self, scene_id: str) -> Dict[str, Any]:
        """Register a new scene for perceptual grain modulation."""
        with self._global_lock:
            if scene_id in self._scenes:
                return {"error": f"Scene already registered: {scene_id}"}
            if len(self._scenes) >= self._MAX_SCENES:
                return {"error": f"Scene cap reached ({self._MAX_SCENES})"}
            self._scenes[scene_id] = {
                "demands": deque(maxlen=self._MAX_DEMAND_SIGNALS),
                "current_grain": GrainLevel.MEDIUM,
                "previous_grain": GrainLevel.MEDIUM,
                "swing_count": 0,
                "consecutive_swings": 0,
                "state": GrainState.SAMPLING,
                "settled_grain": GrainLevel.MEDIUM,
                "total_adjustments": 0,
                "last_sampled_at": 0.0,
            }
            self._signatures[scene_id] = GrainSignature(scene_id=scene_id)
            self._record_event("scene_registered", {"scene_id": scene_id})
            return {
                "scene_id": scene_id,
                "initial_grain": GrainLevel.MEDIUM.value,
            }

    def report_demand(self, scene_id: str, signal: str,
                      value: float, note: str = "") -> Dict[str, Any]:
        """Report a demand signal for a scene."""
        with self._global_lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return {"error": f"Scene not found: {scene_id}"}
            try:
                sig = DemandSignal(signal)
            except ValueError:
                return {"error": f"Invalid signal: {signal}"}
            clamped = max(0.0, min(1.0, value))
            demand = SceneDemand(
                scene_id=scene_id,
                signal=sig,
                value=clamped,
                note=note,
            )
            scene["demands"].append(demand)
            scene["last_sampled_at"] = time.time()
            self._record_event("demand_reported", {
                "scene_id": scene_id,
                "signal": sig.value,
                "value": clamped,
            })
            return {
                "scene_id": scene_id,
                "signal": sig.value,
                "value": clamped,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single perceptual grain cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = GrainPhase.SAMPLE
            phase_outputs.append({"phase": self._phase.value,
                                  **self._phase_sample()})
            self._phase = GrainPhase.ANALYZE
            phase_outputs.append({"phase": self._phase.value,
                                  **self._phase_analyze()})
            self._phase = GrainPhase.MODULATE
            phase_outputs.append({"phase": self._phase.value,
                                  **self._phase_modulate()})
            self._phase = GrainPhase.RENDER
            phase_outputs.append({"phase": self._phase.value,
                                  **self._phase_render()})
            self._phase = GrainPhase.SETTLE
            phase_outputs.append({"phase": self._phase.value,
                                  **self._phase_settle()})
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_at"] = time.time()
            elapsed_ms = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
                "elapsed_ms": elapsed_ms,
            }

    def _phase_sample(self) -> Dict[str, Any]:
        """Sample phase: read the current demand signals for each scene."""
        sampled = 0
        for scene_id, scene in self._scenes.items():
            scene["state"] = GrainState.SAMPLING
            demands = list(scene["demands"])
            if not demands:
                continue
            sampled += 1
        self._stats["scenes_sampled"] = sampled
        self._record_event("phase_sample", {"sampled": sampled})
        return {"sampled": sampled}

    def _phase_analyze(self) -> Dict[str, Any]:
        """Analyze phase: compute legibility budget and engagement deficit."""
        analyzed = 0
        for scene_id, scene in self._scenes.items():
            demands = list(scene["demands"])
            if not demands:
                continue
            scene["state"] = GrainState.ANALYZING
            # Average each signal across the rolling window.
            signal_avg: Dict[DemandSignal, float] = {}
            for demand in demands:
                signal_avg[demand.signal] = signal_avg.get(demand.signal, 0.0)
            for demand in demands:
                signal_avg[demand.signal] += demand.value
            for sig in signal_avg:
                signal_avg[sig] /= max(1, sum(
                    1 for d in demands if d.signal == sig
                ))
            attention = signal_avg.get(DemandSignal.ATTENTION_LOAD, 0.0)
            emotion = signal_avg.get(DemandSignal.EMOTIONAL_WEIGHT, 0.0)
            velocity = signal_avg.get(DemandSignal.NARRATIVE_VELOCITY, 0.0)
            sensorimotor = signal_avg.get(DemandSignal.SENSORIMOTOR_DEMAND, 0.0)
            density = signal_avg.get(DemandSignal.SCENE_DENSITY, 0.0)
            # Legibility budget shrinks when the scene is dense and demanding.
            demand_pressure = (
                attention * 0.3
                + density * 0.3
                + sensorimotor * 0.2
                + emotion * 0.1
                + velocity * 0.1
            )
            budget = max(0.0, min(1.0, 1.0 - demand_pressure * self._LEGIBILITY_DAMPING))
            # Engagement deficit grows when the scene is thin and the player
            # is under-engaged (low attention, low emotion, low velocity).
            thinness = 1.0 - (
                attention * 0.4 + emotion * 0.3 + velocity * 0.3
            )
            thinness = max(0.0, min(1.0, thinness))
            deficit = max(0.0, min(1.0, thinness * self._ENGAGEMENT_GAIN))
            signature = self._signatures[scene_id]
            signature.legibility_budget = budget
            signature.engagement_deficit = deficit
            analyzed += 1
        self._record_event("phase_analyze", {"analyzed": analyzed})
        return {"analyzed": analyzed}

    def _phase_modulate(self) -> Dict[str, Any]:
        """Modulate phase: adjust each scene's grain level."""
        adjustments = 0
        overcorrections = 0
        for scene_id, scene in self._scenes.items():
            signature = self._signatures[scene_id]
            demands = list(scene["demands"])
            if not demands:
                continue
            scene["state"] = GrainState.MODULATING
            old_grain = scene["current_grain"]
            # High demand pressure coarsens grain to protect legibility.
            # Low demand pressure fine-grains to draw the eye in.
            budget = signature.legibility_budget
            deficit = signature.engagement_deficit
            # Compute a target grain position on the fine -> coarse axis.
            # Coarseness rises as budget falls; fineness rises as deficit rises.
            coarseness = (1.0 - budget) * 0.7 - deficit * 0.4
            coarseness = max(0.0, min(1.0, coarseness))
            target_index = int(round(coarseness * (len(self._GRAIN_ORDER) - 1)))
            target_grain = next(
                g for g, i in self._GRAIN_ORDER.items() if i == target_index
            )
            if target_grain != old_grain:
                # Track swings to detect oscillation.
                if scene["previous_grain"] == target_grain and old_grain != target_grain:
                    # The scene is swinging back and forth.
                    scene["swing_count"] += 1
                    scene["consecutive_swings"] += 1
                else:
                    scene["consecutive_swings"] = 0
                # Damp oscillation by refusing to swing back too quickly.
                if scene["swing_count"] >= self._OSCILLATION_THRESHOLD:
                    # Hold the previous grain to dampen oscillation.
                    target_grain = old_grain
                    scene["swing_count"] = 0
                    self._stats["oscillations_dampened"] += 1
                if scene["consecutive_swings"] >= self._OVERCORRECTION_THRESHOLD:
                    scene["state"] = GrainState.OVERCORRECTING
                    self._stats["overcorrections"] += 1
                    overcorrections += 1
                if target_grain != old_grain:
                    scene["previous_grain"] = old_grain
                    scene["current_grain"] = target_grain
                    scene["total_adjustments"] += 1
                    adjustments += 1
        self._stats["grain_adjustments"] += adjustments
        self._record_event("phase_modulate", {
            "adjustments": adjustments,
            "overcorrections": overcorrections,
        })
        return {
            "adjustments": adjustments,
            "overcorrections": overcorrections,
        }

    def _phase_render(self) -> Dict[str, Any]:
        """Render phase: emit a grain signature per scene."""
        emitted = 0
        fine_emitted = 0
        coarse_emitted = 0
        for scene_id, scene in self._scenes.items():
            demands = list(scene["demands"])
            if not demands:
                continue
            scene["state"] = GrainState.RENDERING
            grain = scene["current_grain"]
            signature = self._signatures[scene_id]
            signature.grain_level = grain
            signature.timestamp = time.time()
            # Decide what survives and what fades at this grain level.
            survives, fades = self._classify_details(scene_id, grain)
            signature.survives = survives[:self._MAX_SURVIVES]
            signature.fades = fades[:self._MAX_FADES]
            # Focal priority rises when the scene is emotionally heavy and
            # the grain is coarse enough to demand a single focal point.
            emotion = self._average_signal(demands, DemandSignal.EMOTIONAL_WEIGHT)
            coarse_index = self._GRAIN_ORDER[grain] / (len(self._GRAIN_ORDER) - 1)
            signature.focal_priority = max(
                0.0, min(1.0, 0.3 + emotion * 0.4 + coarse_index * 0.3)
            )
            emitted += 1
            if grain in (GrainLevel.ULTRA_FINE, GrainLevel.FINE):
                fine_emitted += 1
            elif grain in (GrainLevel.COARSE, GrainLevel.ULTRA_COARSE):
                coarse_emitted += 1
        self._stats["fine_grain_emitted"] += fine_emitted
        self._stats["coarse_grain_emitted"] += coarse_emitted
        self._record_event("phase_render", {
            "emitted": emitted,
            "fine": fine_emitted,
            "coarse": coarse_emitted,
        })
        return {
            "emitted": emitted,
            "fine": fine_emitted,
            "coarse": coarse_emitted,
        }

    def _phase_settle(self) -> Dict[str, Any]:
        """Settle phase: let the modulated grain settle, dampen oscillation."""
        settled = 0
        for scene_id, scene in self._scenes.items():
            demands = list(scene["demands"])
            if not demands:
                continue
            scene["state"] = GrainState.SETTLED
            # Settled grain drifts toward the current grain under the settle decay.
            current = scene["current_grain"]
            settled_grain = scene["settled_grain"]
            current_index = self._GRAIN_ORDER[current]
            settled_index = self._GRAIN_ORDER[settled_grain]
            delta = current_index - settled_index
            if delta != 0:
                # Move the settled grain partway toward the current grain.
                new_index = settled_index + delta * (1.0 - self._SETTLE_DECAY)
                new_index = int(round(new_index))
                new_index = max(0, min(len(self._GRAIN_ORDER) - 1, new_index))
                scene["settled_grain"] = next(
                    g for g, i in self._GRAIN_ORDER.items() if i == new_index
                )
            settled += 1
        self._record_event("phase_settle", {"settled": settled})
        return {"settled": settled}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _average_signal(self, demands: List[SceneDemand],
                        signal: DemandSignal) -> float:
        """Average a single demand signal across the demand list."""
        values = [d.value for d in demands if d.signal == signal]
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _classify_details(self, scene_id: str,
                          grain: GrainLevel) -> tuple:
        """Classify which details survive and which fade at a given grain level."""
        # A small synthetic detail palette per scene. Downstream renderers
        # would supply the real detail list; this gives the signature shape.
        palette = [
            ("hero silhouette", FadeBehavior.PRESERVE),
            ("focal object", FadeBehavior.PRESERVE),
            ("key gesture", FadeBehavior.PRESERVE),
            ("primary light", FadeBehavior.SOFTEN),
            ("secondary light", FadeBehavior.SOFTEN),
            ("midground shapes", FadeBehavior.SOFTEN),
            ("background shapes", FadeBehavior.BLUR),
            ("surface texture", FadeBehavior.BLUR),
            ("foliage detail", FadeBehavior.BLUR),
            ("rivet and seam", FadeBehavior.DROP),
            ("specular highlight", FadeBehavior.DROP),
            ("ambient particle", FadeBehavior.DROP),
        ]
        # At finer grain, more details survive; at coarser grain, fewer do.
        grain_index = self._GRAIN_ORDER[grain]
        # Map grain index to a fade threshold: finer grain preserves more.
        # PRESERVE always survives. SOFTEN survives up to COARSE.
        # BLUR survives up to MEDIUM. DROP only survives at ULTRA_FINE.
        survive_levels = {
            FadeBehavior.PRESERVE: 4,  # survives at every grain
            FadeBehavior.SOFTEN: 3,    # survives up to and including COARSE
            FadeBehavior.BLUR: 2,      # survives up to and including MEDIUM
            FadeBehavior.DROP: 0,      # survives only at ULTRA_FINE
        }
        survives: List[str] = []
        fades: List[str] = []
        for label, behavior in palette:
            # Coarser grain has a higher index. A detail survives if the
            # grain index is at or below the behavior's survive level.
            if grain_index <= survive_levels[behavior]:
                survives.append(label)
            else:
                fades.append(f"{label} ({behavior.value})")
        # Tint the lists with the scene id so signatures are distinguishable.
        survives = [f"{scene_id}:{label}" for label in survives]
        fades = [f"{scene_id}:{label}" for label in fades]
        return survives, fades

    def _derive_vitality(self) -> GrainVitality:
        """Derive the overall vitality of the grain ecosystem."""
        if not self._scenes:
            return GrainVitality.DORMANT
        if self._stats.get("overcorrections", 0) > 0:
            return GrainVitality.OVERCORRECTING
        # SATURATED if most scenes sit at the same extreme.
        extremes = 0
        for scene in self._scenes.values():
            grain = scene["current_grain"]
            if grain in (GrainLevel.ULTRA_FINE, GrainLevel.ULTRA_COARSE):
                extremes += 1
        if extremes >= max(2, len(self._scenes) // 2):
            return GrainVitality.SATURATED
        if self._cycle_count < 2:
            return GrainVitality.TRACKING
        return GrainVitality.RESPONSIVE

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_signature(self, scene_id: str) -> Dict[str, Any]:
        with self._global_lock:
            scene = self._scenes.get(scene_id)
            if scene is None:
                return {"error": f"Scene not found: {scene_id}"}
            signature = self._signatures[scene_id]
            return {
                "scene_id": signature.scene_id,
                "grain_level": signature.grain_level.value,
                "settled_grain": scene["settled_grain"].value,
                "legibility_budget": signature.legibility_budget,
                "engagement_deficit": signature.engagement_deficit,
                "survives": list(signature.survives),
                "fades": list(signature.fades),
                "focal_priority": signature.focal_priority,
                "state": scene["state"].value,
                "timestamp": signature.timestamp,
            }

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "scenes": len(self._scenes),
                "vitality": self._derive_vitality().value,
                "stats": dict(self._stats),
            }

    def get_scenes(self) -> Dict[str, Any]:
        with self._global_lock:
            scenes = []
            for scene_id, scene in self._scenes.items():
                signature = self._signatures[scene_id]
                scenes.append({
                    "scene_id": scene_id,
                    "current_grain": scene["current_grain"].value,
                    "settled_grain": scene["settled_grain"].value,
                    "state": scene["state"].value,
                    "legibility_budget": signature.legibility_budget,
                    "engagement_deficit": signature.engagement_deficit,
                    "focal_priority": signature.focal_priority,
                    "demand_count": len(scene["demands"]),
                    "total_adjustments": scene["total_adjustments"],
                })
            return {"scenes": scenes, "count": len(scenes)}

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic scenes and demands, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_scenes()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_scenes(self) -> None:
        """Seed a small synthetic world with distinct scenes and demands."""
        seed_scenes = [
            ("sim_market_square", "attention_load", 0.85, "noon market crush"),
            ("sim_market_square", "scene_density", 0.9, "stalls and crowds"),
            ("sim_market_square", "emotional_weight", 0.4, "market chatter"),
            ("sim_cathedral", "emotional_weight", 0.8, "vaulted silence"),
            ("sim_cathedral", "attention_load", 0.3, "single candle"),
            ("sim_cathedral", "scene_density", 0.2, "empty nave"),
            ("sim_battlefield", "sensorimotor_demand", 0.9, "active melee"),
            ("sim_battlefield", "narrative_velocity", 0.8, "turning point"),
            ("sim_battlefield", "scene_density", 0.75, "two armies"),
            ("sim_quiet_road", "attention_load", 0.2, "empty horizon"),
            ("sim_quiet_road", "emotional_weight", 0.2, "calm walk"),
            ("sim_quiet_road", "narrative_velocity", 0.15, "slow afternoon"),
        ]
        seeded_scenes = set()
        for scene_id, signal, value, note in seed_scenes:
            if scene_id not in seeded_scenes:
                if scene_id not in self._scenes:
                    self.register_scene(scene_id)
                seeded_scenes.add(scene_id)
            self.report_demand(scene_id, signal, value, note=note)

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._scenes.clear()
            self._signatures.clear()
            self._events_log.clear()
            self._phase = GrainPhase.SAMPLE
            self._state = GrainState.SAMPLING
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
