"""
SparkLabs Engine - Stratified Atmosphere Weaver

The EngineStratifiedAtmosphereWeaver builds atmosphere as a stack of
distinct layers rather than a single global mood. Surface, wind, light,
sound, and social strata each carry their own contribution. The weaver
collects those contributions, arranges them into a vertical stratified
structure, mediates between layers where they pull against one another,
blends the mediated strata toward a coherent whole, and lets the whole
settle over the world.

A flat atmospheric state tends to feel painted on; a stratified one,
where each layer can be heard separately before they merge, tends to
feel like the world actually has air in it - one stratum can shift
while the others hold, and the relationship between them does the work.

Architecture:
  LAYER     ->  STRATIFY  ->  MEDIATE  ->  BLEND  ->  SETTLE
  (each       (arrange the   (where      (blend the  (let the
   layer      layers into     layers      stratified  blended
   reports    a vertical      conflict,   layers      atmosphere
   its        stratified      mediate     toward a    settle
   contrib-   structure)      between     coherent    over the
   ution)                     them)       whole)      world)

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

class StratifiedAtmospherePhase(Enum):
    """Phases of the stratified atmosphere cycle."""
    LAYER = "layer"            # each atmospheric layer reports its contribution
    STRATIFY = "stratify"      # arrange layers into a vertical stratified structure
    MEDIATE = "mediate"        # where layers conflict, mediate between them
    BLEND = "blend"            # blend the stratified layers toward a coherent whole
    SETTLE = "settle"          # let the blended atmosphere settle over the world


class AtmosphereLayerKind(Enum):
    """The kind of stratum an atmospheric layer belongs to."""
    SURFACE = "surface"        # ground-level texture: dust, fog, ground mist
    WIND = "wind"              # air movement and pressure
    LIGHT = "light"            # illumination, color of light, shadow
    SOUND = "sound"            # ambient sound field
    SOCIAL = "social"          # crowd mood and collective attention


class LayerRelation(Enum):
    """How an upper stratum relates to the stratum beneath it."""
    HARMONIZING = "harmonizing"      # the two layers reinforce each other
    CONTRASTING = "contrasting"      # the two layers pull against each other
    DOMINATING = "dominating"        # the upper layer overrides the lower
    SUBORDINATING = "subordinating"  # the upper layer yields to the lower


class StratumState(Enum):
    """Lifecycle state of an atmospheric layer within the cycle."""
    RAW = "raw"                # contribution reported, not yet placed
    STRATIFIED = "stratified"  # placed into the vertical structure
    MEDIATED = "mediated"      # conflicts with neighbors resolved
    BLENDED = "blended"        # folded into the coherent whole
    SETTLED = "settled"        # settled over the world


class AtmosphereMood(Enum):
    """The overall mood the settled atmosphere conveys."""
    TURBULENT = "turbulent"        # many layers fighting, low coherence
    RESTLESS = "restless"          # motion across strata, not yet resolved
    CONTEMPLATIVE = "contemplative"  # layered but quiet, settled
    SERENE = "serene"              # harmonized across all strata
    EERIE = "eerie"                # one stratum dominates against the others


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class LayerContribution:
    """A single atmospheric layer's reported contribution."""
    layer_id: str
    kind: AtmosphereLayerKind
    intensity: float = 0.5              # 0.0-1.0, how strongly it asserts
    hue: float = 0.5                    # 0.0-1.0, color / tonal position
    texture_note: str = ""              # short text describing the texture
    state: StratumState = StratumState.RAW
    settled_intensity: float = 0.0      # intensity after settle decay
    created_at: float = field(default_factory=time.time)


@dataclass
class StratumEdge:
    """A vertical edge between an upper stratum and the stratum beneath it."""
    edge_id: str
    upper_layer_id: str
    lower_layer_id: str
    relation: LayerRelation = LayerRelation.HARMONIZING
    weight: float = 0.5                 # 0.0-1.0, how strongly they couple


@dataclass
class MediationRecord:
    """Record of how a mediating edge resolved a layer conflict."""
    edge_id: str
    resolution: LayerRelation            # the relation settled on after mediation
    intensity_delta: float = 0.0         # how much intensity was traded across


@dataclass
class AtmosphereStratum:
    """Per-world stratified atmosphere state."""
    world_id: str
    layers: List[LayerContribution] = field(default_factory=list)
    edges: List[StratumEdge] = field(default_factory=list)
    mediations: List[MediationRecord] = field(default_factory=list)
    mood: AtmosphereMood = AtmosphereMood.CONTEMPLATIVE
    coherence: float = 0.0               # 0.0-1.0, how coherent the whole is
    settled_intensity: float = 0.0       # 0.0-1.0, settled overall intensity
    total_layered: int = 0
    total_stratified: int = 0
    total_mediated: int = 0
    total_blended: int = 0
    total_settled: int = 0


# =============================================================================
# Weaver
# =============================================================================

class EngineStratifiedAtmosphereWeaver:
    """
    Thread-safe singleton orchestrating stratified atmosphere composition.

    Usage:
        weaver = EngineStratifiedAtmosphereWeaver.get_instance()
        weaver.register_world("valley")
        weaver.add_layer("valley", "l1", AtmosphereLayerKind.WIND, 0.6, 0.4, "dry gusts")
        weaver.cycle()
        state = weaver.get_world_state("valley")
    """

    _instance: Optional["EngineStratifiedAtmosphereWeaver"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _STRATIFY_MAX_LAYERS = 8              # how many layers participate in a single stack
    _MEDIATE_CONTRAST_THRESHOLD = 0.4     # hue gap above which layers contrast
    _BLEND_COHERENCE_GAIN = 0.1           # coherence gained per blended edge
    _SETTLE_DECAY = 0.05                  # intensity bled off per settle pass
    _MAX_LAYERS_PER_WORLD = 30
    _MAX_EDGES_PER_WORLD = 80
    _MAX_WORLDS = 30
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._worlds: Dict[str, AtmosphereStratum] = {}
        self._phase: StratifiedAtmospherePhase = StratifiedAtmospherePhase.LAYER
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineStratifiedAtmosphereWeaver":
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
            "total_worlds": 0,
            "total_layers": 0,
            "total_edges": 0,
            "total_mediations": 0,
            "settled_layers": 0,
            "avg_coherence": 0.0,
            "avg_settled_intensity": 0.0,
            "mood_distribution": {},
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._worlds:
            return
        coherences: List[float] = []
        intensities: List[float] = []
        mood_counts: Dict[str, int] = {}
        settled_layers = 0
        total_layers = 0
        total_edges = 0
        total_mediations = 0
        for stratum in self._worlds.values():
            coherences.append(stratum.coherence)
            intensities.append(stratum.settled_intensity)
            mood_counts[stratum.mood.value] = mood_counts.get(stratum.mood.value, 0) + 1
            for layer in stratum.layers:
                total_layers += 1
                if layer.state == StratumState.SETTLED:
                    settled_layers += 1
            total_edges += len(stratum.edges)
            total_mediations += len(stratum.mediations)
        self._stats["total_worlds"] = len(self._worlds)
        self._stats["total_layers"] = total_layers
        self._stats["total_edges"] = total_edges
        self._stats["total_mediations"] = total_mediations
        self._stats["settled_layers"] = settled_layers
        self._stats["avg_coherence"] = (
            sum(coherences) / len(coherences) if coherences else 0.0
        )
        self._stats["avg_settled_intensity"] = (
            sum(intensities) / len(intensities) if intensities else 0.0
        )
        self._stats["mood_distribution"] = mood_counts

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # World Management
    # -------------------------------------------------------------------------

    def register_world(self, world_id: str) -> Dict[str, Any]:
        """Register a new world for stratified atmosphere composition."""
        with self._global_lock:
            if len(self._worlds) >= self._MAX_WORLDS and world_id not in self._worlds:
                return {"error": f"World capacity reached ({self._MAX_WORLDS})"}
            if world_id in self._worlds:
                return {"error": f"World already registered: {world_id}"}
            stratum = AtmosphereStratum(world_id=world_id)
            self._worlds[world_id] = stratum
            self._record_event("world_registered", {"world_id": world_id})
            return {
                "world_id": world_id,
                "layers": 0,
                "edges": 0,
                "mood": stratum.mood.value,
            }

    def remove_world(self, world_id: str) -> Dict[str, Any]:
        with self._global_lock:
            stratum = self._worlds.pop(world_id, None)
            if stratum is None:
                return {"error": f"World not found: {world_id}"}
            self._record_event("world_removed", {"world_id": world_id})
            return {
                "removed": world_id,
                "cleared_layers": len(stratum.layers),
                "cleared_edges": len(stratum.edges),
                "cleared_mediations": len(stratum.mediations),
            }

    # -------------------------------------------------------------------------
    # Layer Intake
    # -------------------------------------------------------------------------

    def add_layer(self, world_id: str, layer_id: str, kind: AtmosphereLayerKind,
                  intensity: float = 0.5, hue: float = 0.5,
                  texture_note: str = "") -> Dict[str, Any]:
        """Add an atmospheric layer to a world's stratum."""
        with self._global_lock:
            stratum = self._worlds.get(world_id)
            if stratum is None:
                return {"error": f"World not found: {world_id}"}
            if any(l.layer_id == layer_id for l in stratum.layers):
                return {"error": f"Layer already exists: {layer_id}"}
            if len(stratum.layers) >= self._MAX_LAYERS_PER_WORLD:
                return {"error": f"Layer capacity reached for world: {world_id}"}
            layer = LayerContribution(
                layer_id=layer_id,
                kind=kind,
                intensity=max(0.0, min(1.0, intensity)),
                hue=max(0.0, min(1.0, hue)),
                texture_note=texture_note,
                state=StratumState.RAW,
                settled_intensity=max(0.0, min(1.0, intensity)),
            )
            stratum.layers.append(layer)
            self._record_event("layer_added", {
                "world_id": world_id,
                "layer_id": layer_id,
                "kind": kind.value,
                "intensity": layer.intensity,
                "hue": layer.hue,
            })
            return {
                "world_id": world_id,
                "layer_id": layer_id,
                "kind": kind.value,
                "intensity": layer.intensity,
                "hue": layer.hue,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single stratified atmosphere cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = StratifiedAtmospherePhase.LAYER
            phase_outputs["layer"] = self._phase_layer()
            self._phase = StratifiedAtmospherePhase.STRATIFY
            phase_outputs["stratify"] = self._phase_stratify()
            self._phase = StratifiedAtmospherePhase.MEDIATE
            phase_outputs["mediate"] = self._phase_mediate()
            self._phase = StratifiedAtmospherePhase.BLEND
            phase_outputs["blend"] = self._phase_blend()
            self._phase = StratifiedAtmospherePhase.SETTLE
            phase_outputs["settle"] = self._phase_settle()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_layer(self) -> Dict[str, Any]:
        """Layer phase: each layer reports (confirms) its current contribution."""
        reported = 0
        for stratum in self._worlds.values():
            for layer in stratum.layers:
                # Reset to RAW at the start of each cycle so the stack can rebuild.
                layer.state = StratumState.RAW
                # Carry the prior settled intensity as the new working intensity,
                # with a small drift so the layer is alive rather than frozen.
                drift = random.uniform(-0.02, 0.02)
                layer.intensity = max(
                    0.0, min(1.0, layer.settled_intensity + drift)
                )
                reported += 1
            stratum.total_layered += reported
        self._record_event("phase_layer", {"reported": reported})
        return {"reported": reported}

    def _phase_stratify(self) -> Dict[str, Any]:
        """Stratify phase: arrange layers into a vertical stratified structure."""
        total_edges = 0
        for stratum in self._worlds.values():
            # Clear the prior cycle's edges so stratification is recomputed.
            stratum.edges.clear()
            # Order layers by kind to give the stack a consistent vertical layout:
            # surface at the bottom, social at the top.
            kind_order = [
                AtmosphereLayerKind.SURFACE,
                AtmosphereLayerKind.WIND,
                AtmosphereLayerKind.LIGHT,
                AtmosphereLayerKind.SOUND,
                AtmosphereLayerKind.SOCIAL,
            ]
            ordered = sorted(
                stratum.layers,
                key=lambda l: kind_order.index(l.kind) if l.kind in kind_order else len(kind_order),
            )
            # Only the top N layers participate in the stack.
            stack = ordered[:self._STRATIFY_MAX_LAYERS]
            for i in range(1, len(stack)):
                upper = stack[i]
                lower = stack[i - 1]
                relation = self._classify_relation(upper, lower)
                # Coupling weight rises with how close the two intensities are.
                weight = 1.0 - abs(upper.intensity - lower.intensity)
                weight = max(0.0, min(1.0, weight))
                edge = StratumEdge(
                    edge_id=f"edge_{lower.layer_id}_{upper.layer_id}_{self._cycle_count}",
                    upper_layer_id=upper.layer_id,
                    lower_layer_id=lower.layer_id,
                    relation=relation,
                    weight=weight,
                )
                stratum.edges.append(edge)
                total_edges += 1
                upper.state = StratumState.STRATIFIED
                lower.state = StratumState.STRATIFIED
            if len(stratum.edges) > self._MAX_EDGES_PER_WORLD:
                stratum.edges = stratum.edges[-self._MAX_EDGES_PER_WORLD:]
            stratum.total_stratified += total_edges
        self._record_event("phase_stratify", {"edges_built": total_edges})
        return {"edges_built": total_edges}

    def _phase_mediate(self) -> Dict[str, Any]:
        """Mediate phase: where layers conflict, mediate between them."""
        mediated = 0
        for stratum in self._worlds.values():
            stratum.mediations.clear()
            for edge in stratum.edges:
                upper = next(
                    (l for l in stratum.layers if l.layer_id == edge.upper_layer_id),
                    None,
