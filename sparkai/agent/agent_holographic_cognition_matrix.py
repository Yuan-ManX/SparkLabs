"""
SparkLabs Agent - Holographic Cognition Matrix

The AgentHolographicCognitionMatrix models agent cognition as a holographic
interference pattern distributed across a cognitive substrate. Rather than
storing memories and thoughts as isolated records, it encodes them as wave
patterns that interfere across the whole substrate. Each fragment of the
hologram contains information about the entire cognitive field, enabling
holistic recall, associative reconstruction, and pattern completion from
partial cues.

This holographic metaphor captures how living cognition actually works:
memories are not filed in drawers, they are distributed interference
patterns. Recall does not retrieve a stored copy, it reconstructs the
whole from a fragment. Attention does not select a slot, it opens an
aperture through which patterns diffract. And forgetting does not delete
a file, it attenuates a wave until it can no longer reconstruct.

Core concepts:
  - FRINGE     : an encoded cognitive wave pattern on the substrate
  - AMPLITUDE  : the strength of a fringe pattern (0.0-1.0)
  - PHASE      : the angular alignment of a fringe (0.0-2*PI)
  - WAVELENGTH : the spatial frequency of the pattern
  - COHERENCE  : how stable the interference pattern is (0.0-1.0)
  - APERTURE   : a focus window through which patterns diffract
  - SUBSTRATE  : the holographic medium holding all fringes

Fringe types:
  SENSORY   : sensory input fringes, high frequency, fast attenuation
  MEMORY    : stored memory fringes, medium frequency, stable coherence
  CONCEPT   : abstract concept fringes, low frequency, long wavelength
  EMOTION   : emotional pattern fringes, irregular, high amplitude
  INTENT    : action intention fringes, focused, high coherence

Holographic events:
  FRINGE_ENCODED       : a new fringe pattern is encoded on the substrate
  INTERFERENCE_FORMED  : two fringes create a stable interference node
  RECONSTRUCTION       : a partial cue reconstructs a complete pattern
  DIFFRACTION          : a pattern diffracts through an attention aperture
  ATTENUATION          : a fringe pattern fades below reconstruction threshold
  SUBSTRATE_FLUSH      : attenuated fringes are flushed from the substrate
  COHERENCE_LOCK       : a fringe achieves maximum coherence stability

Architecture:
  ENCODE  ->  INTERFERE  ->  RECONSTRUCT  ->  DIFFRACT  ->  ATTENUATE
  (new    (fringes       (partial cues     (patterns     (unused
   info    interfere      reconstruct       diffract      patterns
   encoded across the     complete          through       fade,
   as a    substrate)     patterns from     attention     substrate
   fringe)                fragments)        apertures)    recovers)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class FringeType(Enum):
    """Types of cognitive fringe patterns."""
    SENSORY = "sensory"    # sensory input, high frequency, fast decay
    MEMORY = "memory"      # stored memory, medium frequency, stable
    CONCEPT = "concept"    # abstract concept, low frequency, long wave
    EMOTION = "emotion"    # emotional pattern, irregular, high amplitude
    INTENT = "intent"      # action intention, focused, high coherence


class HolographicPhase(Enum):
    """Phases of the holographic cognition cycle."""
    ENCODE = "encode"
    INTERFERE = "interfere"
    RECONSTRUCT = "reconstruct"
    DIFFRACT = "diffract"
    ATTENUATE = "attenuate"


class HolographicEvent(Enum):
    """Events that occur during the holographic cognition cycle."""
    FRINGE_ENCODED = "fringe_encoded"
    INTERFERENCE_FORMED = "interference_formed"
    RECONSTRUCTION = "reconstruction"
    DIFFRACTION = "diffraction"
    ATTENUATION = "attenuation"
    SUBSTRATE_FLUSH = "substrate_flush"
    COHERENCE_LOCK = "coherence_lock"


# =============================================================================
# Default Parameters by Fringe Type
# =============================================================================

DEFAULT_FRINGE_AMPLITUDE: Dict[FringeType, float] = {
    FringeType.SENSORY: 0.7,
    FringeType.MEMORY: 0.6,
    FringeType.CONCEPT: 0.5,
    FringeType.EMOTION: 0.8,
    FringeType.INTENT: 0.75,
}

DEFAULT_FRINGE_WAVELENGTH: Dict[FringeType, float] = {
    FringeType.SENSORY: 0.15,   # short wavelength, high spatial frequency
    FringeType.MEMORY: 0.35,    # medium wavelength
    FringeType.CONCEPT: 0.70,   # long wavelength, low spatial frequency
    FringeType.EMOTION: 0.25,   # medium-short, irregular
    FringeType.INTENT: 0.45,    # medium-long, focused
}

DEFAULT_FRINGE_COHERENCE: Dict[FringeType, float] = {
    FringeType.SENSORY: 0.5,
    FringeType.MEMORY: 0.8,
    FringeType.CONCEPT: 0.85,
    FringeType.EMOTION: 0.4,
    FringeType.INTENT: 0.9,
}

DEFAULT_FRINGE_ATTENUATION: Dict[FringeType, float] = {
    FringeType.SENSORY: 0.12,   # fast decay
    FringeType.MEMORY: 0.03,    # slow decay
    FringeType.CONCEPT: 0.01,   # very slow decay
    FringeType.EMOTION: 0.08,   # medium decay
    FringeType.INTENT: 0.05,    # medium-slow decay
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class CognitiveFringe:
    """A holographic fringe pattern encoded on the cognitive substrate."""
    fringe_id: str
    label: str
    fringe_type: FringeType
    amplitude: float
    phase: float          # angular alignment in radians [0, 2*PI)
    wavelength: float     # spatial frequency of the pattern
    coherence: float      # stability of the interference pattern
    attenuation_rate: float
    # Spatial coordinates on the cognitive substrate (normalized 0.0-1.0)
    position: Tuple[float, float]
    recall_count: int = 0
    locked: bool = False  # coherence-locked fringes resist attenuation
    age_cycles: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class InterferenceNode:
    """A stable interference node formed by two overlapping fringes."""
    node_id: str
    fringe_a_id: str
    fringe_b_id: str
    # Combined amplitude at the intersection point
    combined_amplitude: float
    # Whether the interference is constructive or destructive
    is_constructive: bool
    position: Tuple[float, float]
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReconstructionRecord:
    """A record of a holographic reconstruction from a partial cue."""
    reconstruction_id: str
    cue_fringe_id: str
    # Fringes that were reconstructed from the cue
    recovered_fringe_ids: List[str]
    fidelity: float        # how faithfully the original was reconstructed
    cue_strength: float    # strength of the partial cue
    timestamp: float = field(default_factory=time.time)


@dataclass
class ApertureWindow:
    """An attention aperture through which patterns diffract."""
    aperture_id: str
    label: str
    # Center of the aperture on the substrate
    center: Tuple[float, float]
    # Radius of the aperture (focus window)
    radius: float
    # Current openness (0.0 = closed, 1.0 = fully open)
    openness: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class HolographicStats:
    """Aggregate statistics for the holographic cognition matrix."""
    total_fringes: int = 0
    total_interference_nodes: int = 0
    total_reconstructions: int = 0
    total_apertures: int = 0
    total_events: int = 0
    total_fringe_encoded: int = 0
    total_interference_formed: int = 0
    total_reconstructions_made: int = 0
    total_diffractions: int = 0
    total_attenuations: int = 0
    total_substrate_flushes: int = 0
    total_coherence_locks: int = 0
    avg_amplitude: float = 0.0
    avg_coherence: float = 0.0
    last_cycle_time_ms: float = 0.0


# =============================================================================
# Holographic Cognition Matrix
# =============================================================================

class AgentHolographicCognitionMatrix:
    """
    Holographic cognition matrix that encodes agent cognition as distributed
    interference patterns on a cognitive substrate.

    Thread-safe singleton. Use get_instance() to obtain the global instance.
    """

    _instance: Optional["AgentHolographicCognitionMatrix"] = None
    _instance_lock = threading.Lock()

    # Configuration constants
    MAX_FRINGES = 200
    MAX_INTERFERENCE_NODES = 150
    MAX_RECONSTRUCTIONS = 100
    MAX_APERTURES = 20
    MAX_EVENTS = 500

    MIN_AMPLITUDE = 0.01
    MAX_AMPLITUDE = 1.0
    MIN_COHERENCE = 0.05
    MAX_COHERENCE = 1.0
    MIN_WAVELENGTH = 0.05
    MAX_WAVELENGTH = 1.0
    MIN_ATTENUATION = 0.0
    MAX_ATTENUATION = 0.5

    RECONSTRUCTION_THRESHOLD = 0.15      # cue strength needed to trigger recall
    INTERFERENCE_DISTANCE = 0.25          # max distance for interference
    COHERENCE_LOCK_THRESHOLD = 0.92       # coherence needed to lock a fringe
    ATTENUATION_FLUSH_THRESHOLD = 0.02    # below this amplitude, fringe is flushed
    DIFFRACTION_SPREAD = 0.4              # how much patterns spread through aperture

    def __init__(self) -> None:
        self._fringes: Dict[str, CognitiveFringe] = {}
        self._interference_nodes: Deque[InterferenceNode] = deque(maxlen=self.MAX_INTERFERENCE_NODES)
        self._reconstructions: Deque[ReconstructionRecord] = deque(maxlen=self.MAX_RECONSTRUCTIONS)
        self._apertures: Dict[str, ApertureWindow] = {}
        self._event_history: Deque[Dict[str, Any]] = deque(maxlen=self.MAX_EVENTS)
        self._fringe_counter: int = 0
        self._node_counter: int = 0
        self._reconstruction_counter: int = 0
        self._substrate_energy: float = 0.0
        self._stats = HolographicStats()
        self._cycle_count: int = 0
        self._active: bool = False
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentHolographicCognitionMatrix":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Fringe Management
    # -------------------------------------------------------------------------

    def register_fringe(
        self,
        fringe_id: str,
        label: str,
        fringe_type: str = "memory",
        amplitude: Optional[float] = None,
        phase: Optional[float] = None,
        wavelength: Optional[float] = None,
        coherence: Optional[float] = None,
        attenuation_rate: Optional[float] = None,
        position: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Encode a new cognitive fringe pattern on the substrate."""
        with self._lock:
            if fringe_id in self._fringes:
                return {"error": f"Fringe already exists: {fringe_id}"}
            if len(self._fringes) >= self.MAX_FRINGES:
                return {"error": "Substrate at maximum fringe capacity"}

            try:
                ftype = FringeType(fringe_type)
            except ValueError:
                return {"error": f"Unknown fringe type: {fringe_type}"}

            if amplitude is None:
                amplitude = DEFAULT_FRINGE_AMPLITUDE.get(ftype, 0.6)
            amplitude = max(self.MIN_AMPLITUDE, min(self.MAX_AMPLITUDE, float(amplitude)))

            if phase is None:
                phase = random.uniform(0.0, 2.0 * math.pi)
            phase = float(phase) % (2.0 * math.pi)

            if wavelength is None:
                wavelength = DEFAULT_FRINGE_WAVELENGTH.get(ftype, 0.35)
            wavelength = max(self.MIN_WAVELENGTH, min(self.MAX_WAVELENGTH, float(wavelength)))

            if coherence is None:
                coherence = DEFAULT_FRINGE_COHERENCE.get(ftype, 0.7)
            coherence = max(self.MIN_COHERENCE, min(self.MAX_COHERENCE, float(coherence)))

            if attenuation_rate is None:
                attenuation_rate = DEFAULT_FRINGE_ATTENUATION.get(ftype, 0.05)
            attenuation_rate = max(
                self.MIN_ATTENUATION, min(self.MAX_ATTENUATION, float(attenuation_rate))
            )

            if position is None:
                position = [random.random(), random.random()]
            else:
                if len(position) != 2:
                    return {"error": "position must have exactly 2 elements"}
                position = [
                    max(0.0, min(1.0, float(position[0]))),
                    max(0.0, min(1.0, float(position[1]))),
                ]

            fringe = CognitiveFringe(
                fringe_id=fringe_id,
                label=label,
                fringe_type=ftype,
                amplitude=amplitude,
                phase=phase,
                wavelength=wavelength,
                coherence=coherence,
                attenuation_rate=attenuation_rate,
                position=(position[0], position[1]),
            )
            self._fringes[fringe_id] = fringe
            self._substrate_energy += amplitude * coherence
            self._stats.total_fringes = len(self._fringes)

            self._record_event(
                HolographicEvent.FRINGE_ENCODED,
                intensity=amplitude,
                fringe_ids=[fringe_id],
                description=f"Fringe '{label}' ({ftype.value}) encoded on substrate",
            )
            return self._fringe_to_dict(fringe)

    def get_fringe(self, fringe_id: str) -> Dict[str, Any]:
        """Get the state of a specific cognitive fringe."""
        with self._lock:
            fringe = self._fringes.get(fringe_id)
            if fringe is None:
                return {"error": f"Fringe not found: {fringe_id}"}
            return self._fringe_to_dict(fringe)

    def list_fringes(
        self, fringe_type: Optional[str] = None, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """List fringes, optionally filtered by type."""
        with self._lock:
            fringes = list(self._fringes.values())
            if fringe_type:
                try:
                    ftype = FringeType(fringe_type)
                    fringes = [f for f in fringes if f.fringe_type == ftype]
                except ValueError:
                    return []
            fringes = fringes[:limit]
            return [self._fringe_to_dict(f) for f in fringes]

    def remove_fringe(self, fringe_id: str) -> Dict[str, Any]:
        """Remove a fringe from the substrate."""
        with self._lock:
            if fringe_id not in self._fringes:
                return {"removed": False, "fringe_id": fringe_id}
            # Remove interference nodes referencing this fringe
            self._interference_nodes = deque(
                (n for n in self._interference_nodes
                 if n.fringe_a_id != fringe_id and n.fringe_b_id != fringe_id),
                maxlen=self.MAX_INTERFERENCE_NODES,
            )
            fringe = self._fringes[fringe_id]
            self._substrate_energy = max(0.0, self._substrate_energy - fringe.amplitude * fringe.coherence)
            del self._fringes[fringe_id]
            self._stats.total_fringes = len(self._fringes)
            self._stats.total_interference_nodes = len(self._interference_nodes)
            return {"removed": True, "fringe_id": fringe_id}

    def set_fringe_amplitude(
        self, fringe_id: str, amplitude: float, description: str = ""
    ) -> Dict[str, Any]:
        """Set the amplitude of a fringe pattern."""
        with self._lock:
            fringe = self._fringes.get(fringe_id)
            if fringe is None:
                return {"error": f"Fringe not found: {fringe_id}"}
            old_energy = fringe.amplitude * fringe.coherence
            fringe.amplitude = max(self.MIN_AMPLITUDE, min(self.MAX_AMPLITUDE, float(amplitude)))
            self._substrate_energy += (fringe.amplitude * fringe.coherence) - old_energy
            return {
                "fringe_id": fringe_id,
                "amplitude": round(fringe.amplitude, 4),
                "description": description,
            }

    def lock_fringe_coherence(
        self, fringe_id: str, description: str = ""
    ) -> Dict[str, Any]:
        """Lock a fringe's coherence, making it resistant to attenuation."""
        with self._lock:
            fringe = self._fringes.get(fringe_id)
            if fringe is None:
                return {"error": f"Fringe not found: {fringe_id}"}
            fringe.locked = True
            fringe.coherence = self.MAX_COHERENCE
            self._record_event(
                HolographicEvent.COHERENCE_LOCK,
                intensity=1.0,
                fringe_ids=[fringe_id],
                description=f"Fringe '{fringe.label}' coherence locked",
            )
            return {
                "fringe_id": fringe_id,
                "locked": True,
                "coherence": round(fringe.coherence, 4),
                "description": description,
            }

    # -------------------------------------------------------------------------
    # Aperture Management
    # -------------------------------------------------------------------------

    def register_aperture(
        self,
        aperture_id: str,
        label: str,
        center: Optional[List[float]] = None,
        radius: float = 0.2,
        openness: float = 0.5,
    ) -> Dict[str, Any]:
        """Register an attention aperture on the substrate."""
        with self._lock:
            if aperture_id in self._apertures:
                return {"error": f"Aperture already exists: {aperture_id}"}
            if len(self._apertures) >= self.MAX_APERTURES:
                return {"error": "Maximum aperture count reached"}

            if center is None:
                center = [random.random(), random.random()]
            else:
                if len(center) != 2:
                    return {"error": "center must have exactly 2 elements"}
                center = [
                    max(0.0, min(1.0, float(center[0]))),
                    max(0.0, min(1.0, float(center[1]))),
                ]
            radius = max(0.05, min(0.5, float(radius)))
            openness = max(0.0, min(1.0, float(openness)))

            aperture = ApertureWindow(
                aperture_id=aperture_id,
                label=label,
                center=(center[0], center[1]),
                radius=radius,
                openness=openness,
            )
            self._apertures[aperture_id] = aperture
            self._stats.total_apertures = len(self._apertures)
            return self._aperture_to_dict(aperture)

    def list_apertures(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List all attention apertures."""
        with self._lock:
            return [self._aperture_to_dict(a) for a in list(self._apertures.values())[:limit]]

    def get_aperture(self, aperture_id: str) -> Dict[str, Any]:
        """Get a specific aperture."""
        with self._lock:
            aperture = self._apertures.get(aperture_id)
            if aperture is None:
                return {"error": f"Aperture not found: {aperture_id}"}
            return self._aperture_to_dict(aperture)

    def remove_aperture(self, aperture_id: str) -> Dict[str, Any]:
        """Remove an attention aperture."""
        with self._lock:
            if aperture_id not in self._apertures:
                return {"removed": False, "aperture_id": aperture_id}
            del self._apertures[aperture_id]
            self._stats.total_apertures = len(self._apertures)
            return {"removed": True, "aperture_id": aperture_id}

    def set_aperture_openness(
        self, aperture_id: str, openness: float, description: str = ""
    ) -> Dict[str, Any]:
        """Set the openness of an attention aperture."""
        with self._lock:
            aperture = self._apertures.get(aperture_id)
            if aperture is None:
                return {"error": f"Aperture not found: {aperture_id}"}
            aperture.openness = max(0.0, min(1.0, float(openness)))
            return {
                "aperture_id": aperture_id,
                "openness": round(aperture.openness, 4),
                "description": description,
            }

    # -------------------------------------------------------------------------
    # Interference Nodes
    # -------------------------------------------------------------------------

    def list_interference_nodes(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List interference nodes on the substrate."""
        with self._lock:
            nodes = list(self._interference_nodes)[:limit]
            return [self._node_to_dict(n) for n in nodes]

    def get_interference_node(self, node_id: str) -> Dict[str, Any]:
        """Get a specific interference node."""
        with self._lock:
            for n in self._interference_nodes:
                if n.node_id == node_id:
                    return self._node_to_dict(n)
            return {"error": f"Interference node not found: {node_id}"}

    # -------------------------------------------------------------------------
    # Reconstructions
    # -------------------------------------------------------------------------

    def list_reconstructions(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List holographic reconstruction records."""
        with self._lock:
            recs = list(self._reconstructions)[:limit]
            return [self._reconstruction_to_dict(r) for r in recs]

    def get_reconstruction(self, reconstruction_id: str) -> Dict[str, Any]:
        """Get a specific reconstruction record."""
        with self._lock:
            for r in self._reconstructions:
                if r.reconstruction_id == reconstruction_id:
                    return self._reconstruction_to_dict(r)
            return {"error": f"Reconstruction not found: {reconstruction_id}"}

    def trigger_reconstruction(
        self, cue_fringe_id: str, description: str = ""
    ) -> Dict[str, Any]:
        """
        Trigger a holographic reconstruction from a partial cue fringe.

        The cue fringe's wave pattern interferes with nearby fringes on the
        substrate, reconstructing patterns that share spatial or spectral
        overlap. This is the holographic recall mechanism.
        """
        with self._lock:
            cue = self._fringes.get(cue_fringe_id)
            if cue is None:
                return {"error": f"Cue fringe not found: {cue_fringe_id}"}

            cue_strength = cue.amplitude * cue.coherence
            if cue_strength < self.RECONSTRUCTION_THRESHOLD:
                return {"error": f"Cue strength {cue_strength:.3f} below threshold {self.RECONSTRUCTION_THRESHOLD}"}

            recovered: List[str] = []
            total_fidelity = 0.0
            for other in self._fringes.values():
                if other.fringe_id == cue_fringe_id:
                    continue
                # Spatial proximity
                dx = cue.position[0] - other.position[0]
                dy = cue.position[1] - other.position[1]
                distance = math.sqrt(dx * dx + dy * dy)
                if distance > self.INTERFERENCE_DISTANCE:
                    continue
                # Spectral compatibility (wavelength similarity)
                wl_ratio = min(cue.wavelength, other.wavelength) / max(cue.wavelength, other.wavelength)
                # Phase alignment
                phase_diff = abs(cue.phase - other.phase)
                phase_align = 1.0 - (min(phase_diff, 2 * math.pi - phase_diff) / math.pi)
                # Reconstruction fidelity
                spatial_factor = 1.0 - (distance / self.INTERFERENCE_DISTANCE)
                fidelity = (
                    cue_strength
                    * other.amplitude
                    * other.coherence
                    * spatial_factor
                    * wl_ratio
                    * (0.5 + 0.5 * phase_align)
                )
                if fidelity > self.RECONSTRUCTION_THRESHOLD * 0.5:
                    recovered.append(other.fringe_id)
                    total_fidelity += fidelity
                    other.recall_count += 1
                    # Reconstruction boosts coherence of recovered fringes
                    other.coherence = min(self.MAX_COHERENCE, other.coherence + 0.05)

            self._reconstruction_counter += 1
            avg_fidelity = (total_fidelity / max(1, len(recovered)))
            record = ReconstructionRecord(
                reconstruction_id=f"recon_{self._reconstruction_counter}",
                cue_fringe_id=cue_fringe_id,
                recovered_fringe_ids=recovered,
                fidelity=round(avg_fidelity, 4),
                cue_strength=round(cue_strength, 4),
            )
            self._reconstructions.append(record)

            self._record_event(
                HolographicEvent.RECONSTRUCTION,
                intensity=avg_fidelity,
                fringe_ids=[cue_fringe_id] + recovered,
                description=f"Reconstruction from cue '{cue.label}': {len(recovered)} fringes recovered",
            )
            return self._reconstruction_to_dict(record)

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run one holographic cognition cycle."""
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: ENCODE - newly added fringes settle onto the substrate
            encode_info = self._encode_phase()

            # Phase 2: INTERFERE - fringes create interference nodes
            interfere_info = self._interfere_phase()

            # Phase 3: RECONSTRUCT - spontaneous reconstructions from strong fringes
            reconstruct_info = self._reconstruct_phase()

            # Phase 4: DIFFRACT - patterns diffract through open apertures
            diffract_info = self._diffract_phase()

            # Phase 5: ATTENUATE - unused patterns fade, substrate recovers
            attenuate_info = self._attenuate_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()

            phase = HolographicPhase.ATTENUATE
            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "encode": encode_info,
                "interfere": interfere_info,
                "reconstruct": reconstruct_info,
                "diffract": diffract_info,
                "attenuate": attenuate_info,
                "total_fringes": len(self._fringes),
                "total_interference_nodes": len(self._interference_nodes),
                "total_reconstructions": len(self._reconstructions),
                "total_apertures": len(self._apertures),
                "substrate_energy": round(self._substrate_energy, 4),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _encode_phase(self) -> Dict[str, Any]:
        """Phase 1: Newly encoded fringes settle and align their phases."""
        encoded_settled = 0
        for fringe in self._fringes.values():
            fringe.age_cycles += 1
            # Fringes gradually self-align their phase toward their type's
            # natural coherence, stabilizing the interference pattern
            if not fringe.locked and fringe.coherence < self.MAX_COHERENCE:
                fringe.coherence = min(
                    self.MAX_COHERENCE,
                    fringe.coherence + 0.02 * fringe.amplitude,
                )
                encoded_settled += 1
        self._stats.total_fringe_encoded += encoded_settled
        return {
            "fringes_settled": encoded_settled,
            "total_fringes": len(self._fringes),
        }

    def _interfere_phase(self) -> Dict[str, Any]:
        """Phase 2: Overlapping fringes form interference nodes."""
        nodes_formed = 0
        fringe_list = list(self._fringes.values())
        # Limit pair checks to avoid quadratic blowup
        max_pairs = 80
        checked = 0
        for i in range(len(fringe_list)):
            for j in range(i + 1, len(fringe_list)):
                if checked >= max_pairs:
                    break
                checked += 1
                fa, fb = fringe_list[i], fringe_list[j]
                dx = fa.position[0] - fb.position[0]
                dy = fa.position[1] - fb.position[1]
                distance = math.sqrt(dx * dx + dy * dy)
                if distance > self.INTERFERENCE_DISTANCE:
                    continue
                # Check if node already exists
                already = any(
                    (n.fringe_a_id == fa.fringe_id and n.fringe_b_id == fb.fringe_id)
                    or (n.fringe_a_id == fb.fringe_id and n.fringe_b_id == fa.fringe_id)
                    for n in self._interference_nodes
                )
                if already:
                    continue
                # Phase difference determines constructive/destructive
                phase_diff = abs(fa.phase - fb.phase) % (2 * math.pi)
                is_constructive = phase_diff < math.pi / 2 or phase_diff > 3 * math.pi / 2
                if is_constructive:
                    combined = fa.amplitude * fa.coherence + fb.amplitude * fb.coherence
                else:
                    combined = abs(fa.amplitude * fa.coherence - fb.amplitude * fb.coherence)
                combined = min(self.MAX_AMPLITUDE, combined * 0.5)

                self._node_counter += 1
                mid_x = (fa.position[0] + fb.position[0]) / 2
                mid_y = (fa.position[1] + fb.position[1]) / 2
                node = InterferenceNode(
                    node_id=f"node_{self._node_counter}",
                    fringe_a_id=fa.fringe_id,
                    fringe_b_id=fb.fringe_id,
                    combined_amplitude=round(combined, 4),
                    is_constructive=is_constructive,
                    position=(mid_x, mid_y),
                )
                self._interference_nodes.append(node)
                nodes_formed += 1
                if nodes_formed >= 10:  # cap per cycle
                    break
            if nodes_formed >= 10:
                break

        if nodes_formed > 0:
            self._record_event(
                HolographicEvent.INTERFERENCE_FORMED,
                intensity=0.6,
                fringe_ids=[],
                description=f"{nodes_formed} interference nodes formed",
            )
        self._stats.total_interference_formed += nodes_formed
        self._stats.total_interference_nodes = len(self._interference_nodes)
        return {
            "nodes_formed": nodes_formed,
            "total_nodes": len(self._interference_nodes),
        }

    def _reconstruct_phase(self) -> Dict[str, Any]:
        """Phase 3: Strong fringes spontaneously trigger reconstructions."""
        reconstructions_made = 0
        # Pick a few strong fringes as spontaneous cues
        candidates = [
            f for f in self._fringes.values()
            if f.amplitude * f.coherence >= self.RECONSTRUCTION_THRESHOLD
        ]
        random.shuffle(candidates)
        for cue in candidates[:3]:  # limit spontaneous reconstructions per cycle
            result = self.trigger_reconstruction(cue.fringe_id)
            if "error" not in result:
                reconstructions_made += 1
        self._stats.total_reconstructions_made += reconstructions_made
        return {
            "reconstructions_made": reconstructions_made,
            "total_reconstructions": len(self._reconstructions),
        }

    def _diffract_phase(self) -> Dict[str, Any]:
        """Phase 4: Patterns diffract through open attention apertures."""
        diffractions = 0
        for aperture in self._apertures.values():
            if aperture.openness <= 0.01:
                continue
            for fringe in self._fringes.values():
                dx = fringe.position[0] - aperture.center[0]
                dy = fringe.position[1] - aperture.center[1]
                distance = math.sqrt(dx * dx + dy * dy)
                if distance > aperture.radius:
                    continue
                # Diffraction boosts amplitude within the aperture
                boost = aperture.openness * self.DIFFRACTION_SPREAD * (1.0 - distance / max(aperture.radius, 0.01))
                fringe.amplitude = min(self.MAX_AMPLITUDE, fringe.amplitude + boost * 0.1)
                diffractions += 1
        if diffractions > 0:
            self._record_event(
                HolographicEvent.DIFFRACTION,
                intensity=0.4,
                fringe_ids=[],
                description=f"{diffractions} patterns diffracted through apertures",
            )
        self._stats.total_diffractions += diffractions
        return {
            "diffractions": diffractions,
            "open_apertures": sum(1 for a in self._apertures.values() if a.openness > 0.01),
        }

    def _attenuate_phase(self) -> Dict[str, Any]:
        """Phase 5: Unused fringes fade and are flushed from the substrate."""
        attenuated = 0
        flushed = 0
        locked_count = 0
        to_remove: List[str] = []
        energy_recovered = 0.0
        for fringe in self._fringes.values():
            if fringe.locked:
                locked_count += 1
                continue
            fringe.amplitude = max(
                self.MIN_AMPLITUDE,
                fringe.amplitude - fringe.attenuation_rate * (1.0 - fringe.coherence * 0.5),
            )
            if fringe.amplitude > self.MIN_AMPLITUDE:
                attenuated += 1
            if fringe.amplitude <= self.ATTENUATION_FLUSH_THRESHOLD:
                to_remove.append(fringe.fringe_id)
                energy_recovered += fringe.amplitude * fringe.coherence
                flushed += 1

        for fid in to_remove:
            self.remove_fringe(fid)

        if flushed > 0:
            self._record_event(
                HolographicEvent.SUBSTRATE_FLUSH,
                intensity=0.2,
                fringe_ids=to_remove,
                description=f"{flushed} attenuated fringes flushed from substrate",
            )
        self._stats.total_attenuations += attenuated
        self._stats.total_substrate_flushes += flushed
        self._stats.total_coherence_locks += locked_count
        return {
            "attenuated": attenuated,
            "flushed": flushed,
            "locked": locked_count,
            "energy_recovered": round(energy_recovered, 4),
        }

    # -------------------------------------------------------------------------
    # Simulation & Status
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles and return the final status."""
        cycles = max(1, min(100, int(cycles)))
        last_cycle = None
        for _ in range(cycles):
            last_cycle = self.run_cycle()
        return {
            "cycles_run": cycles,
            "last_cycle": last_cycle,
            "status": self.get_status(),
        }

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the holographic cognition matrix."""
        with self._lock:
            self._stats.total_fringes = len(self._fringes)
            self._stats.total_interference_nodes = len(self._interference_nodes)
            self._stats.total_reconstructions = len(self._reconstructions)
            self._stats.total_apertures = len(self._apertures)
            self._stats.total_events = len(self._event_history)
            self._update_avg_metrics()
            return {
                "total_fringes": self._stats.total_fringes,
                "total_interference_nodes": self._stats.total_interference_nodes,
                "total_reconstructions": self._stats.total_reconstructions,
                "total_apertures": self._stats.total_apertures,
                "substrate_energy": round(self._substrate_energy, 4),
                "active": self._active,
                "cycle_count": self._cycle_count,
                "stats": {
                    "total_events": self._stats.total_events,
                    "total_fringe_encoded": self._stats.total_fringe_encoded,
                    "total_interference_formed": self._stats.total_interference_formed,
                    "total_reconstructions_made": self._stats.total_reconstructions_made,
                    "total_diffractions": self._stats.total_diffractions,
                    "total_attenuations": self._stats.total_attenuations,
                    "total_substrate_flushes": self._stats.total_substrate_flushes,
                    "total_coherence_locks": self._stats.total_coherence_locks,
                    "avg_amplitude": round(self._stats.avg_amplitude, 4),
                    "avg_coherence": round(self._stats.avg_coherence, 4),
                    "last_cycle_time_ms": self._stats.last_cycle_time_ms,
                },
            }

    def get_events(
        self, fringe_type: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent holographic events."""
        with self._lock:
            events = list(self._event_history)
            if fringe_type:
                events = [e for e in events if e.get("fringe_type") == fringe_type]
            return events[:limit]

    def reset(self) -> Dict[str, Any]:
        """Reset the holographic cognition matrix to its initial state."""
        with self._lock:
            self._fringes.clear()
            self._interference_nodes.clear()
            self._reconstructions.clear()
            self._apertures.clear()
            self._event_history.clear()
            self._fringe_counter = 0
            self._node_counter = 0
            self._reconstruction_counter = 0
            self._substrate_energy = 0.0
            self._stats = HolographicStats()
            self._cycle_count = 0
            self._active = False
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _record_event(
        self,
        event: HolographicEvent,
        intensity: float,
        fringe_ids: List[str],
        description: str,
    ) -> None:
        """Record a holographic event in the history."""
        self._event_history.append({
            "event_id": f"evt_{len(self._event_history) + 1}",
            "event_type": event.value,
            "intensity": round(intensity, 4),
            "fringe_ids": fringe_ids,
            "description": description,
            "timestamp": time.time(),
        })

    def _update_avg_metrics(self) -> None:
        """Update average metrics from current fringes."""
        if not self._fringes:
            self._stats.avg_amplitude = 0.0
            self._stats.avg_coherence = 0.0
            return
        n = len(self._fringes)
        self._stats.avg_amplitude = sum(f.amplitude for f in self._fringes.values()) / n
        self._stats.avg_coherence = sum(f.coherence for f in self._fringes.values()) / n

    def _fringe_to_dict(self, f: CognitiveFringe) -> Dict[str, Any]:
        """Convert a fringe to a dictionary representation."""
        return {
            "fringe_id": f.fringe_id,
            "label": f.label,
            "fringe_type": f.fringe_type.value,
            "amplitude": round(f.amplitude, 4),
            "phase": round(f.phase, 4),
            "wavelength": round(f.wavelength, 4),
            "coherence": round(f.coherence, 4),
            "attenuation_rate": round(f.attenuation_rate, 4),
            "position": [round(f.position[0], 4), round(f.position[1], 4)],
            "recall_count": f.recall_count,
            "locked": f.locked,
            "age_cycles": f.age_cycles,
            "timestamp": f.timestamp,
        }

    def _node_to_dict(self, n: InterferenceNode) -> Dict[str, Any]:
        """Convert an interference node to a dictionary representation."""
        return {
            "node_id": n.node_id,
            "fringe_a_id": n.fringe_a_id,
            "fringe_b_id": n.fringe_b_id,
            "combined_amplitude": n.combined_amplitude,
            "is_constructive": n.is_constructive,
            "position": [round(n.position[0], 4), round(n.position[1], 4)],
            "timestamp": n.timestamp,
        }

    def _reconstruction_to_dict(self, r: ReconstructionRecord) -> Dict[str, Any]:
        """Convert a reconstruction record to a dictionary representation."""
        return {
            "reconstruction_id": r.reconstruction_id,
            "cue_fringe_id": r.cue_fringe_id,
            "recovered_fringe_ids": r.recovered_fringe_ids,
            "recovered_count": len(r.recovered_fringe_ids),
            "fidelity": r.fidelity,
            "cue_strength": r.cue_strength,
            "timestamp": r.timestamp,
        }

    def _aperture_to_dict(self, a: ApertureWindow) -> Dict[str, Any]:
        """Convert an aperture to a dictionary representation."""
        return {
            "aperture_id": a.aperture_id,
            "label": a.label,
            "center": [round(a.center[0], 4), round(a.center[1], 4)],
            "radius": round(a.radius, 4),
            "openness": round(a.openness, 4),
            "timestamp": a.timestamp,
        }
