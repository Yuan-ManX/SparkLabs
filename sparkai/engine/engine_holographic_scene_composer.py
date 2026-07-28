"""
SparkLabs Engine - Holographic Scene Composer

The EngineHolographicSceneComposer projects game scenes as multi-layer
holographic overlays, where each layer represents a different semantic
aspect of the scene. Unlike traditional render passes that only handle
visual data, the composer blends physical, emotional, narrative, and
strategic layers into a unified scene experience.

Each layer vibrates at its own frequency and has its own coherence.
The composer can focus on one layer (making it dominant), blend multiple
layers, or refract them (allowing one layer to bend and influence
another). This creates emergent scene qualities: a battle scene where
the emotional layer dominates feels different from one where the
strategic layer dominates, even if the physical layout is identical.

When layers are in harmony, the scene achieves "holographic coherence"
- a state where all aspects reinforce each other. When layers conflict,
the scene becomes "refracted" - creating tension and dissonance that
can be used for dramatic effect.

Architecture:
  PROJECT   ->  FOCUS      ->  BLEND      ->  REFRACT     ->  RESOLVE
  (register    (set the      (merge        (let layers       (produce
   semantic    dominant      multiple      cross-              the final
   layers)     layer and     layers into   contaminate        scene
               suppress      a unified     and bend each      output
               others)       field)        other)             with
                                                              coherence
                                                              score)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import math
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

class ComposerPhase(Enum):
    """Phases of the holographic composition cycle."""
    PROJECT = "project"       # register and project semantic layers
    FOCUS = "focus"           # set dominant layer
    BLEND = "blend"           # merge layers into unified field
    REFRACT = "refract"       # let layers cross-contaminate
    RESOLVE = "resolve"       # produce final scene output


class SemanticLayerType(Enum):
    """Types of semantic layers in a scene."""
    PHYSICAL = "physical"         # spatial layout, objects, terrain
    EMOTIONAL = "emotional"       # mood, atmosphere, tension
    NARRATIVE = "narrative"       # story beats, plot threads
    STRATEGIC = "strategic"       # tactical opportunities, threats
    SOCIAL = "social"             # relationship dynamics
    AESTHETIC = "aesthetic"       # visual style, color, lighting
    CAUSAL = "causal"             # cause-effect chains
    TEMPORAL = "temporal"         # time pressure, pacing


class SceneCoherenceState(Enum):
    """Overall coherence of the composed scene."""
    HARMONIOUS = "harmonious"     # layers reinforce each other
    BALANCED = "balanced"         # layers coexist neutrally
    TENSION = "tension"           # layers create productive friction
    DISSONANT = "dissonant"       # layers conflict destructively
    CHAOTIC = "chaotic"           # no coherent pattern


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SemanticLayer:
    """A single semantic layer of a scene."""
    layer_id: str
    label: str
    layer_type: SemanticLayerType
    intensity: float = 0.5          # current activation (0.0-1.0)
    target_intensity: float = 0.5   # where intensity is heading
    frequency: float = 0.5          # vibration rate (0.0-1.0)
    coherence: float = 0.5          # internal consistency (0.0-1.0)
    weight: float = 1.0             # influence weight in blend
    color: str = "#888888"          # visual representation
    description: str = ""
    elements: List[str] = field(default_factory=list)  # scene element IDs
    last_updated: float = field(default_factory=time.time)


@dataclass
class LayerRefraction:
    """A refraction relationship where one layer bends another."""
    source_layer: str
    target_layer: str
    bend_factor: float = 0.3        # how much source bends target (0.0-1.0)
    direction: str = "amplify"      # amplify, attenuate, distort, shift


@dataclass
class SceneElement:
    """An element within a scene that belongs to layers."""
    element_id: str
    label: str
    layer_ids: Set[str] = field(default_factory=set)
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComposedScene:
    """The final resolved scene output."""
    scene_id: str
    dominant_layer: Optional[str]
    coherence_state: SceneCoherenceState
    coherence_score: float             # 0.0-1.0
    layer_intensities: Dict[str, float]
    refraction_count: int
    element_count: int
    timestamp: float = field(default_factory=time.time)
    description: str = ""


# =============================================================================
# Engine
# =============================================================================

class EngineHolographicSceneComposer:
    """
    Thread-safe singleton for holographic scene composition.

    Usage:
        composer = EngineHolographicSceneComposer.get_instance()
        composer.register_layer("lyr_phys", "Physical", SemanticLayerType.PHYSICAL, 0.8)
        composer.register_layer("lyr_emo", "Emotional", SemanticLayerType.EMOTIONAL, 0.6)
        composer.focus_layer("lyr_phys")
        composer.refract("lyr_emo", "lyr_phys", bend_factor=0.4, direction="amplify")
        composer.cycle()
    """

    _instance: Optional["EngineHolographicSceneComposer"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._layers: Dict[str, SemanticLayer] = {}
        self._refractions: Dict[str, List[LayerRefraction]] = {}  # src -> [refractions]
        self._elements: Dict[str, SceneElement] = {}
        self._scenes: Deque[ComposedScene] = deque(maxlen=50)
        self._dominant_layer: Optional[str] = None
        self._phase: ComposerPhase = ComposerPhase.PROJECT
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_layers": 0,
            "total_refractions": 0,
            "total_elements": 0,
            "total_scenes_composed": 0,
            "avg_coherence": 0.0,
            "last_coherence_state": "balanced",
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineHolographicSceneComposer":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Layer Registration
    # -------------------------------------------------------------------------

    def register_layer(
        self,
        layer_id: str,
        label: str,
        layer_type: SemanticLayerType,
        intensity: float = 0.5,
        frequency: float = 0.5,
        weight: float = 1.0,
        color: str = "#888888",
        description: str = "",
    ) -> Dict[str, Any]:
        """Register a new semantic layer."""
        with self._global_lock:
            if layer_id in self._layers:
                return {"error": f"Layer already registered: {layer_id}"}
            layer = SemanticLayer(
                layer_id=layer_id,
                label=label,
                layer_type=layer_type,
                intensity=max(0.0, min(1.0, intensity)),
                target_intensity=max(0.0, min(1.0, intensity)),
                frequency=max(0.0, min(1.0, frequency)),
                weight=max(0.0, weight),
                color=color,
                description=description,
            )
            self._layers[layer_id] = layer
            self._refractions[layer_id] = []
            self._stats["total_layers"] = len(self._layers)
            self._record_event("layer_registered", {
                "layer_id": layer_id, "type": layer_type.value,
            })
            return {
                "layer_id": layer_id,
                "label": label,
                "type": layer_type.value,
                "intensity": layer.intensity,
                "frequency": layer.frequency,
                "weight": layer.weight,
            }

    def remove_layer(self, layer_id: str) -> Dict[str, Any]:
        """Remove a semantic layer."""
        with self._global_lock:
            if layer_id not in self._layers:
                return {"error": f"Layer not found: {layer_id}"}
            del self._layers[layer_id]
            # Clean up refractions
            del self._refractions[layer_id]
            for src in self._refractions:
                self._refractions[src] = [
                    r for r in self._refractions[src] if r.target_layer != layer_id
                ]
            if self._dominant_layer == layer_id:
                self._dominant_layer = None
            # Clean up elements
            for elem in self._elements.values():
                elem.layer_ids.discard(layer_id)
            self._stats["total_layers"] = len(self._layers)
            self._stats["total_refractions"] = sum(len(r) for r in self._refractions.values())
            return {"removed": layer_id}

    def set_layer_intensity(self, layer_id: str, intensity: float) -> Dict[str, Any]:
        """Set the target intensity of a layer."""
        with self._global_lock:
            layer = self._layers.get(layer_id)
            if layer is None:
                return {"error": f"Layer not found: {layer_id}"}
            layer.target_intensity = max(0.0, min(1.0, intensity))
            layer.last_updated = time.time()
            return {
                "layer_id": layer_id,
                "current_intensity": layer.intensity,
                "target_intensity": layer.target_intensity,
            }

    def set_layer_weight(self, layer_id: str, weight: float) -> Dict[str, Any]:
        """Set the blend weight of a layer."""
        with self._global_lock:
            layer = self._layers.get(layer_id)
            if layer is None:
                return {"error": f"Layer not found: {layer_id}"}
            layer.weight = max(0.0, weight)
            return {"layer_id": layer_id, "weight": layer.weight}

    # -------------------------------------------------------------------------
    # Focus Management
    # -------------------------------------------------------------------------

    def focus_layer(self, layer_id: str) -> Dict[str, Any]:
        """Set the dominant layer, suppressing others."""
        with self._global_lock:
            if layer_id not in self._layers:
                return {"error": f"Layer not found: {layer_id}"}
            self._dominant_layer = layer_id
            self._record_event("focused", {"layer_id": layer_id})
            return {
                "dominant_layer": layer_id,
                "label": self._layers[layer_id].label,
            }

    def clear_focus(self) -> Dict[str, Any]:
        """Clear the dominant layer, returning to balanced mode."""
        with self._global_lock:
            old = self._dominant_layer
            self._dominant_layer = None
            return {"cleared_focus": old}

    # -------------------------------------------------------------------------
    # Refraction Management
    # -------------------------------------------------------------------------

    def refract(
        self,
        source_layer: str,
        target_layer: str,
        bend_factor: float = 0.3,
        direction: str = "amplify",
    ) -> Dict[str, Any]:
        """Create a refraction where one layer bends another."""
        with self._global_lock:
            if source_layer not in self._layers:
                return {"error": f"Source layer not found: {source_layer}"}
            if target_layer not in self._layers:
                return {"error": f"Target layer not found: {target_layer}"}
            if direction not in ("amplify", "attenuate", "distort", "shift"):
                return {"error": f"Invalid direction: {direction}"}
            refraction = LayerRefraction(
                source_layer=source_layer,
                target_layer=target_layer,
                bend_factor=max(0.0, min(1.0, bend_factor)),
                direction=direction,
            )
            self._refractions[source_layer].append(refraction)
            self._stats["total_refractions"] = sum(len(r) for r in self._refractions.values())
            self._record_event("refracted", {
                "source": source_layer, "target": target_layer, "direction": direction,
            })
            return {
                "source_layer": source_layer,
                "target_layer": target_layer,
                "bend_factor": refraction.bend_factor,
                "direction": refraction.direction,
            }

    def unrefract(self, source_layer: str, target_layer: str) -> Dict[str, Any]:
        """Remove a refraction relationship."""
        with self._global_lock:
            if source_layer not in self._refractions:
                return {"error": f"Source layer not found: {source_layer}"}
            before = len(self._refractions[source_layer])
            self._refractions[source_layer] = [
                r for r in self._refractions[source_layer] if r.target_layer != target_layer
            ]
            after = len(self._refractions[source_layer])
            self._stats["total_refractions"] = sum(len(r) for r in self._refractions.values())
            return {"removed": before - after}

    # -------------------------------------------------------------------------
    # Element Management
    # -------------------------------------------------------------------------

    def add_element(
        self,
        element_id: str,
        label: str,
        layer_ids: Optional[List[str]] = None,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add a scene element associated with one or more layers."""
        with self._global_lock:
            if element_id in self._elements:
                return {"error": f"Element already exists: {element_id}"}
            valid_layers = set()
            for lid in (layer_ids or []):
                if lid in self._layers:
                    valid_layers.add(lid)
                    self._layers[lid].elements.append(element_id)
            element = SceneElement(
                element_id=element_id,
                label=label,
                layer_ids=valid_layers,
                position=position,
                properties=properties or {},
            )
            self._elements[element_id] = element
            self._stats["total_elements"] = len(self._elements)
            return {
                "element_id": element_id,
                "label": label,
                "layer_ids": list(valid_layers),
                "position": list(position),
            }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single composition cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            # PROJECT: no-op (layers registered via API)
            self._phase = ComposerPhase.PROJECT
            phase_outputs["project"] = {"total_layers": len(self._layers)}
            # FOCUS: move intensities toward target, amplify dominant
            self._phase = ComposerPhase.FOCUS
            phase_outputs["focus"] = self._phase_focus()
            # BLEND: merge layers into unified field
            self._phase = ComposerPhase.BLEND
            phase_outputs["blend"] = self._phase_blend()
            # REFRACT: apply cross-layer contamination
            self._phase = ComposerPhase.REFRACT
            phase_outputs["refract"] = self._phase_refract()
            # RESOLVE: produce final scene
            self._phase = ComposerPhase.RESOLVE
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

    def _phase_focus(self) -> Dict[str, Any]:
        """FOCUS: move intensities toward target and amplify dominant layer."""
        focused = 0
        for layer in self._layers.values():
            diff = layer.target_intensity - layer.intensity
            if abs(diff) > 0.01:
                layer.intensity += diff * (0.2 + layer.frequency * 0.3)
                focused += 1
        # Amplify dominant layer, suppress others
        if self._dominant_layer and self._dominant_layer in self._layers:
            dominant = self._layers[self._dominant_layer]
            dominant.intensity = min(1.0, dominant.intensity + 0.05)
            for layer in self._layers.values():
                if layer.layer_id != self._dominant_layer:
                    layer.intensity = max(0.0, layer.intensity - 0.02)
        return {"focused": focused, "dominant": self._dominant_layer}

    def _phase_blend(self) -> Dict[str, Any]:
        """BLEND: compute coherence from layer alignment."""
        if not self._layers:
            return {"blended": 0, "avg_coherence": 0.0}
        total_coherence = 0.0
        for layer in self._layers.values():
            # Coherence is how close intensity is to target
            alignment = 1.0 - abs(layer.intensity - layer.target_intensity)
            layer.coherence = max(0.0, min(1.0, alignment * 0.7 + layer.coherence * 0.3))
            total_coherence += layer.coherence
        avg = total_coherence / len(self._layers)
        return {"blended": len(self._layers), "avg_coherence": round(avg, 4)}

    def _phase_refract(self) -> Dict[str, Any]:
        """REFRACT: apply cross-layer contamination."""
        applied = 0
        for source_id, refractions in self._refractions.items():
            source = self._layers.get(source_id)
            if source is None:
                continue
            for refraction in refractions:
                target = self._layers.get(refraction.target_layer)
                if target is None:
                    continue
                influence = source.intensity * refraction.bend_factor * 0.15
                if refraction.direction == "amplify":
                    target.target_intensity = min(1.0, target.target_intensity + influence)
                elif refraction.direction == "attenuate":
                    target.target_intensity = max(0.0, target.target_intensity - influence)
                elif refraction.direction == "distort":
                    # Distort adds noise to the target
                    import random as _rng
                    noise = (_rng.random() - 0.5) * influence * 2
                    target.target_intensity = max(0.0, min(1.0, target.target_intensity + noise))
                elif refraction.direction == "shift":
                    # Shift moves the target toward the source's intensity
                    diff = source.intensity - target.target_intensity
                    target.target_intensity = max(0.0, min(1.0, target.target_intensity + diff * influence))
                applied += 1
        return {"refractions_applied": applied}

    def _phase_resolve(self) -> Dict[str, Any]:
        """RESOLVE: produce the final composed scene."""
        if not self._layers:
            return {"resolved": False, "reason": "no layers"}
        # Calculate overall coherence
        intensities = {lid: l.intensity for lid, l in self._layers.items()}
        coherences = [l.coherence for l in self._layers.values()]
        avg_coherence = sum(coherences) / len(coherences) if coherences else 0.0
        # Determine coherence state
        variance = 0.0
        if len(intensities) > 1:
            mean_i = sum(intensities.values()) / len(intensities)
            variance = sum((i - mean_i) ** 2 for i in intensities.values()) / len(intensities)
        if avg_coherence > 0.8 and variance < 0.05:
            state = SceneCoherenceState.HARMONIOUS
        elif avg_coherence > 0.6:
            state = SceneCoherenceState.BALANCED
        elif avg_coherence > 0.4:
            state = SceneCoherenceState.TENSION
        elif avg_coherence > 0.2:
            state = SceneCoherenceState.DISSONANT
        else:
            state = SceneCoherenceState.CHAOTIC
        scene = ComposedScene(
            scene_id=f"scene_{self._cycle_count}_{int(time.time() * 1000)}",
            dominant_layer=self._dominant_layer,
            coherence_state=state,
            coherence_score=avg_coherence,
            layer_intensities=intensities,
            refraction_count=sum(len(r) for r in self._refractions.values()),
            element_count=len(self._elements),
            description=f"Scene with {len(self._layers)} layers, state={state.value}",
        )
        self._scenes.append(scene)
        self._stats["total_scenes_composed"] = len(self._scenes)
        self._stats["avg_coherence"] = avg_coherence
        self._stats["last_coherence_state"] = state.value
        self._record_event("resolved", {
            "scene_id": scene.scene_id,
            "state": state.value,
            "coherence": round(avg_coherence, 4),
        })
        return {
            "resolved": True,
            "scene_id": scene.scene_id,
            "coherence_state": state.value,
            "coherence_score": round(avg_coherence, 4),
            "dominant_layer": self._dominant_layer,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get global composer status."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_layers": len(self._layers),
                "dominant_layer": self._dominant_layer,
                "stats": dict(self._stats),
            }

    def list_layers(self) -> List[Dict[str, Any]]:
        """List all semantic layers."""
        with self._global_lock:
            return [
                {
                    "layer_id": l.layer_id,
                    "label": l.label,
                    "type": l.layer_type.value,
                    "intensity": round(l.intensity, 4),
                    "target_intensity": round(l.target_intensity, 4),
                    "frequency": l.frequency,
                    "coherence": round(l.coherence, 4),
                    "weight": l.weight,
                    "color": l.color,
                    "element_count": len(l.elements),
                    "is_dominant": l.layer_id == self._dominant_layer,
                }
                for l in self._layers.values()
            ]

    def get_layer(self, layer_id: str) -> Optional[Dict[str, Any]]:
        """Get details of one layer."""
        with self._global_lock:
            layer = self._layers.get(layer_id)
            if layer is None:
                return None
            return {
                "layer_id": layer.layer_id,
                "label": layer.label,
                "type": layer.layer_type.value,
                "intensity": layer.intensity,
                "target_intensity": layer.target_intensity,
                "frequency": layer.frequency,
                "coherence": layer.coherence,
                "weight": layer.weight,
                "color": layer.color,
                "description": layer.description,
                "elements": layer.elements,
                "is_dominant": layer.layer_id == self._dominant_layer,
                "refractions_out": len(self._refractions.get(layer_id, [])),
            }

    def get_refractions(self, layer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get refraction relationships."""
        with self._global_lock:
            result = []
            for src, refrs in self._refractions.items():
                if layer_id and src != layer_id:
                    continue
                for r in refrs:
                    result.append({
                        "source_layer": r.source_layer,
                        "target_layer": r.target_layer,
                        "bend_factor": r.bend_factor,
                        "direction": r.direction,
                    })
            return result

    def get_scenes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent composed scenes."""
        with self._global_lock:
            return [
                {
                    "scene_id": s.scene_id,
                    "dominant_layer": s.dominant_layer,
                    "coherence_state": s.coherence_state.value,
                    "coherence_score": round(s.coherence_score, 4),
                    "layer_intensities": {k: round(v, 4) for k, v in s.layer_intensities.items()},
                    "refraction_count": s.refraction_count,
                    "element_count": s.element_count,
                    "timestamp": s.timestamp,
                    "description": s.description,
                }
                for s in list(self._scenes)[-limit:]
            ]

    def get_elements(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get scene elements."""
        with self._global_lock:
            return [
                {
                    "element_id": e.element_id,
                    "label": e.label,
                    "layer_ids": list(e.layer_ids),
                    "position": list(e.position),
                    "properties": dict(e.properties),
                }
                for e in list(self._elements.values())[:limit]
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent composer events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire composer."""
        with self._global_lock:
            n = len(self._layers)
            self._layers.clear()
            self._refractions.clear()
            self._elements.clear()
            self._scenes.clear()
            self._dominant_layer = None
            self._phase = ComposerPhase.PROJECT
            self._cycle_count = 0
            self._events_log.clear()
            self._stats = {
                "total_layers": 0,
                "total_refractions": 0,
                "total_elements": 0,
                "total_scenes_composed": 0,
                "avg_coherence": 0.0,
                "last_coherence_state": "balanced",
                "last_cycle_time_ms": 0.0,
            }
            self._record_event("composer_reset", {"cleared_layers": n})
            return {"reset": True, "cleared_layers": n}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _update_stats(self) -> None:
        """Update aggregate statistics."""
        self._stats["total_refractions"] = sum(len(r) for r in self._refractions.values())
        self._stats["total_elements"] = len(self._elements)

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record a composer event."""
        self._events_log.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
