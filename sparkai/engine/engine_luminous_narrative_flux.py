"""
SparkLabs Engine - Luminous Narrative Flux"""

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

class FluxPhase(Enum):
    """Phases of the luminous narrative flux cycle."""
    EMIT = "emit"               # story beats emit luminous flux
    FLOW = "flow"               # flux flows through narrative medium
    REFRACT = "refract"         # flux bends around obstacles
    CONVERGE = "converge"       # multiple beats merge into patterns
    ILLUMINATE = "illuminate"   # peak luminosity creates story moments


class NarrativeChromaticity(Enum):
    """Emotional color of a story beat."""
    CRIMSON = "crimson"         # passion, danger, sacrifice
    GOLD = "gold"               # triumph, glory, revelation
    AZURE = "azure"             # calm, wisdom, depth
    VERDANT = "verdant"         # growth, hope, renewal
    VIOLET = "violet"           # mystery, transformation, magic
    ASHEN = "ashen"             # loss, grief, despair
    WHITE = "white"             # purity, clarity, transcendence
    BLACK = "black"             # shadow, unknown, hidden


class BeatPolarization(Enum):
    """Directional bias of a story beat."""
    ASCENDING = "ascending"     # rising action, building tension
    DESCENDING = "descending"   # falling action, resolution
    LATERAL = "lateral"         # complication, redirect
    VORTEX = "vortex"           # spiraling, chaotic
    STILL = "still"             # pause, contemplation


class IlluminationType(Enum):
    """Types of illuminated story moments."""
    EPIPHANY = "epiphany"               # sudden realization
    CLIMAX = "climax"                   # peak dramatic intensity
    REVELATION = "revelation"           # hidden truth unveiled
    CATHARSIS = "catharsis"             # emotional release
    CALL_TO_ACTION = "call_to_action"   # inciting incident
    THRESHOLD = "threshold"             # point of no return
    REFLECTION = "reflection"           # contemplative pause
    CONVERGENCE = "convergence"         # threads unite


class MediumType(Enum):
    """Types of narrative medium that flux flows through."""
    OPEN = "open"               # free-flowing, unconstrained
    DENSE = "dense"             # resistant, requires force
    PRISMATIC = "prismatic"     # splits flux into components
    REFLECTIVE = "reflective"   # bounces flux back
    ABSORBENT = "absorbent"     # consumes flux energy
    AMPLIFYING = "amplifying"   # boosts flux strength


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class StoryBeat:
    """A luminous story beat in the narrative flux."""
    beat_id: str
    label: str
    luminosity: float = 0.5          # brightness/importance (0.0-1.0)
    chromaticity: NarrativeChromaticity = NarrativeChromaticity.WHITE
    polarization: BeatPolarization = BeatPolarization.LATERAL
    wavelength: float = 0.5          # narrative "size" of the beat (0.0-1.0)
    source_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    emitted_at: float = field(default_factory=time.time)
    description: str = ""
    active: bool = True
    distance_traveled: float = 0.0


@dataclass
class NarrativeMedium:
    """A region of narrative space that flux flows through."""
    medium_id: str
    label: str
    medium_type: MediumType
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius: float = 1.0              # influence radius
    density: float = 0.5             # how much it affects flux (0.0-1.0)
    refraction_index: float = 1.0    # how much it bends flux (1.0 = none)
    absorption: float = 0.0          # how much flux energy it consumes


@dataclass
class FluxRay:
    """A ray of narrative flux traveling through the world."""
    ray_id: str
    source_beat: str
    direction: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    strength: float = 0.5
    chromaticity: NarrativeChromaticity = NarrativeChromaticity.WHITE
    polarization: BeatPolarization = BeatPolarization.LATERAL
    hops: int = 0
    absorbed: bool = False


@dataclass
class ConvergencePattern:
    """A pattern formed when multiple flux rays converge."""
    pattern_id: str
    ray_ids: Set[str] = field(default_factory=set)
    beat_ids: Set[str] = field(default_factory=set)
    combined_luminosity: float = 0.0
    dominant_chromaticity: NarrativeChromaticity = NarrativeChromaticity.WHITE
    dominant_polarization: BeatPolarization = BeatPolarization.STILL
    coherence: float = 0.5


@dataclass
class IlluminatedMoment:
    """A moment of peak narrative luminosity."""
    moment_id: str
    illumination_type: IlluminationType
    luminosity: float
    chromaticity: NarrativeChromaticity
    polarization: BeatPolarization
    source_beats: List[str]
    description: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class NarrativeShadow:
    """A dark region in the narrative - mystery or unexplored thread."""
    shadow_id: str
    label: str
    darkness: float = 0.5            # how obscured (0.0-1.0)
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    surrounding_beats: List[str] = field(default_factory=list)
    revealed: bool = False


# =============================================================================
# Engine
# =============================================================================

class EngineLuminousNarrativeFlux:
    """
    Thread-safe singleton for luminous narrative flux.

    Usage:
        flux = EngineLuminousNarrativeFlux.get_instance()
        flux.emit_beat("bt_1", "Hero Arrives", luminosity=0.7,
                       chromaticity=NarrativeChromaticity.GOLD,
                       polarization=BeatPolarization.ASCENDING)
        flux.register_medium("md_1", "Dungeon", MediumType.DENSE, density=0.7)
        flux.cycle()
    """

    _instance: Optional["EngineLuminousNarrativeFlux"] = None
    _lock = threading.RLock()

    # Chromaticity mixing rules for convergence
    _CHROMATIC_MIX = {
        (NarrativeChromaticity.CRIMSON, NarrativeChromaticity.GOLD): NarrativeChromaticity.CRIMSON,
        (NarrativeChromaticity.AZURE, NarrativeChromaticity.VERDANT): NarrativeChromaticity.AZURE,
        (NarrativeChromaticity.VIOLET, NarrativeChromaticity.BLACK): NarrativeChromaticity.VIOLET,
        (NarrativeChromaticity.WHITE, NarrativeChromaticity.WHITE): NarrativeChromaticity.WHITE,
    }

    def __init__(self) -> None:
        self._beats: Dict[str, StoryBeat] = {}
        self._media: Dict[str, NarrativeMedium] = {}
        self._rays: Dict[str, FluxRay] = {}
        self._patterns: Dict[str, ConvergencePattern] = {}
        self._moments: Deque[IlluminatedMoment] = deque(maxlen=50)
        self._shadows: Dict[str, NarrativeShadow] = {}
        self._phase: FluxPhase = FluxPhase.EMIT
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_beats": 0,
            "total_media": 0,
            "total_rays": 0,
            "total_patterns": 0,
            "total_illuminations": 0,
            "total_shadows": 0,
            "avg_luminosity": 0.0,
            "max_luminosity": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineLuminousNarrativeFlux":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Beat Management
    # -------------------------------------------------------------------------

    def emit_beat(
        self,
        beat_id: str,
        label: str,
        luminosity: float = 0.5,
        chromaticity: NarrativeChromaticity = NarrativeChromaticity.WHITE,
        polarization: BeatPolarization = BeatPolarization.LATERAL,
        wavelength: float = 0.5,
        source_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        description: str = "",
    ) -> Dict[str, Any]:
        """Emit a new story beat into the narrative flux."""
        with self._global_lock:
            if beat_id in self._beats:
                return {"error": f"Beat already exists: {beat_id}"}
            beat = StoryBeat(
                beat_id=beat_id,
                label=label,
                luminosity=max(0.0, min(1.0, luminosity)),
                chromaticity=chromaticity,
                polarization=polarization,
                wavelength=max(0.0, min(1.0, wavelength)),
                source_position=source_position,
                description=description,
            )
            self._beats[beat_id] = beat
            self._stats["total_beats"] = len(self._beats)
            # Create initial flux ray
            ray_id = f"ray_{beat_id}_0"
            ray = FluxRay(
                ray_id=ray_id,
                source_beat=beat_id,
                direction=(1.0, 0.0, 0.0),
                strength=beat.luminosity,
                chromaticity=beat.chromaticity,
                polarization=beat.polarization,
            )
            self._rays[ray_id] = ray
            self._stats["total_rays"] = len(self._rays)
            self._record_event("beat_emitted", {
                "beat_id": beat_id, "luminosity": beat.luminosity,
                "chromaticity": chromaticity.value,
            })
            return {
                "beat_id": beat_id,
                "label": label,
                "luminosity": beat.luminosity,
                "chromaticity": chromaticity.value,
                "polarization": polarization.value,
            }

    # -------------------------------------------------------------------------
    # Medium Management
    # -------------------------------------------------------------------------

    def register_medium(
        self,
        medium_id: str,
        label: str,
        medium_type: MediumType,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        radius: float = 1.0,
        density: float = 0.5,
        refraction_index: float = 1.0,
        absorption: float = 0.0,
    ) -> Dict[str, Any]:
        """Register a narrative medium in the flux field."""
        with self._global_lock:
            if medium_id in self._media:
                return {"error": f"Medium already exists: {medium_id}"}
            medium = NarrativeMedium(
                medium_id=medium_id,
                label=label,
                medium_type=medium_type,
                position=position,
                radius=max(0.0, radius),
                density=max(0.0, min(1.0, density)),
                refraction_index=max(0.1, refraction_index),
                absorption=max(0.0, min(1.0, absorption)),
            )
            self._media[medium_id] = medium
            self._stats["total_media"] = len(self._media)
            self._record_event("medium_registered", {
                "medium_id": medium_id, "type": medium_type.value,
            })
            return {
                "medium_id": medium_id,
                "label": label,
                "type": medium_type.value,
                "density": medium.density,
                "refraction_index": medium.refraction_index,
                "absorption": medium.absorption,
            }

    # -------------------------------------------------------------------------
    # Shadow Management
    # -------------------------------------------------------------------------

    def register_shadow(
        self,
        shadow_id: str,
        label: str,
        darkness: float = 0.5,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> Dict[str, Any]:
        """Register a narrative shadow (mystery or unexplored thread)."""
        with self._global_lock:
            if shadow_id in self._shadows:
                return {"error": f"Shadow already exists: {shadow_id}"}
            shadow = NarrativeShadow(
                shadow_id=shadow_id,
                label=label,
                darkness=max(0.0, min(1.0, darkness)),
                position=position,
            )
            self._shadows[shadow_id] = shadow
            self._stats["total_shadows"] = len(self._shadows)
            return {
                "shadow_id": shadow_id,
                "label": label,
                "darkness": shadow.darkness,
            }

    def reveal_shadow(self, shadow_id: str) -> Dict[str, Any]:
        """Reveal a narrative shadow (resolve the mystery)."""
        with self._global_lock:
            shadow = self._shadows.get(shadow_id)
            if shadow is None:
                return {"error": f"Shadow not found: {shadow_id}"}
            shadow.revealed = True
            shadow.darkness = 0.0
            return {"revealed": shadow_id, "label": shadow.label}

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single luminous flux cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            # EMIT: active beats emit new rays
            self._phase = FluxPhase.EMIT
            phase_outputs["emit"] = self._phase_emit()
            # FLOW: rays travel through the narrative space
            self._phase = FluxPhase.FLOW
            phase_outputs["flow"] = self._phase_flow()
            # REFRACT: rays bend through media
            self._phase = FluxPhase.REFRACT
            phase_outputs["refract"] = self._phase_refract()
            # CONVERGE: intersecting rays form patterns
            self._phase = FluxPhase.CONVERGE
            phase_outputs["converge"] = self._phase_converge()
            # ILLUMINATE: high-luminosity patterns create story moments
            self._phase = FluxPhase.ILLUMINATE
            phase_outputs["illuminate"] = self._phase_illuminate()
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

    def _phase_emit(self) -> Dict[str, Any]:
        """EMIT: active beats emit new flux rays."""
        emitted = 0
        for beat in self._beats.values():
            if not beat.active:
                continue
            # Each beat emits a new ray each cycle with diminishing strength
            ray_count = sum(1 for r in self._rays.values() if r.source_beat == beat.beat_id)
            if ray_count >= 5:  # Limit rays per beat
                continue
            ray_id = f"ray_{beat.beat_id}_{ray_count}"
            if ray_id in self._rays:
                continue
            decay = 0.8 ** ray_count
            ray = FluxRay(
                ray_id=ray_id,
                source_beat=beat.beat_id,
                direction=self._random_direction(),
                strength=beat.luminosity * decay,
                chromaticity=beat.chromaticity,
                polarization=beat.polarization,
                hops=0,
            )
            self._rays[ray_id] = ray
            emitted += 1
        self._stats["total_rays"] = len(self._rays)
        return {"emitted": emitted, "total_rays": len(self._rays)}

    def _phase_flow(self) -> Dict[str, Any]:
        """FLOW: rays travel and may be absorbed by media."""
        flowed = 0
        absorbed = 0
        to_remove: List[str] = []
        for ray in self._rays.values():
            if ray.absorbed:
                continue
            ray.hops += 1
            ray.strength *= 0.9  # Natural attenuation
            if ray.strength < 0.05:
                ray.absorbed = True
                absorbed += 1
                continue
            flowed += 1
            # Check if ray passes through any medium
            for medium in self._media.values():
                if medium.medium_type == MediumType.ABSORBENT:
                    ray.strength *= (1.0 - medium.absorption * 0.3)
                    if ray.strength < 0.05:
                        ray.absorbed = True
                        absorbed += 1
                        break
                elif medium.medium_type == MediumType.AMPLIFYING:
                    ray.strength = min(1.0, ray.strength * (1.0 + medium.density * 0.1))
        self._stats["total_rays"] = len(self._rays)
        return {"flowed": flowed, "absorbed": absorbed}

    def _phase_refract(self) -> Dict[str, Any]:
        """REFRACT: rays bend through prismatic and reflective media."""
        refracted = 0
        for ray in self._rays.values():
            if ray.absorbed:
                continue
            for medium in self._media.values():
                if medium.medium_type == MediumType.PRISMATIC:
                    # Split chromaticity into components (simplified: just boost strength)
                    ray.strength = min(1.0, ray.strength * (1.0 + medium.density * 0.05))
                    refracted += 1
                elif medium.medium_type == MediumType.REFLECTIVE:
                    # Bounce: reverse direction (simplified)
                    ray.direction = tuple(-d for d in ray.direction)
                    refracted += 1
        return {"refracted": refracted}

    def _phase_converge(self) -> Dict[str, Any]:
        """CONVERGE: intersecting rays form convergence patterns."""
        # Group active rays by approximate location (simplified: by chromaticity)
        chroma_groups: Dict[NarrativeChromaticity, List[FluxRay]] = {}
        for ray in self._rays.values():
            if ray.absorbed:
                continue
            chroma_groups.setdefault(ray.chromaticity, []).append(ray)
        new_patterns: Dict[str, ConvergencePattern] = {}
        for chroma, rays in chroma_groups.items():
            if len(rays) < 2:
                continue
            # Create a convergence pattern
            pattern_id = f"pattern_{chroma.value}_{self._cycle_count}_{len(new_patterns)}"
            beat_ids = set(r.source_beat for r in rays)
            ray_ids = set(r.ray_id for r in rays)
            combined_lum = sum(r.strength for r in rays) / len(rays)
            # Determine dominant polarization
            polar_counts: Dict[BeatPolarization, int] = {}
            for r in rays:
                polar_counts[r.polarization] = polar_counts.get(r.polarization, 0) + 1
            dominant_polar = max(polar_counts, key=polar_counts.get)
            # Coherence: how aligned the rays are
            coherence = min(1.0, combined_lum * 0.8 + len(rays) * 0.05)
            pattern = ConvergencePattern(
                pattern_id=pattern_id,
                ray_ids=ray_ids,
                beat_ids=beat_ids,
                combined_luminosity=combined_lum,
                dominant_chromaticity=chroma,
                dominant_polarization=dominant_polar,
                coherence=coherence,
            )
            new_patterns[pattern_id] = pattern
        old_count = len(self._patterns)
        self._patterns = new_patterns
        self._stats["total_patterns"] = len(self._patterns)
        return {
            "patterns_formed": len(new_patterns),
            "total_beats_in_patterns": sum(len(p.beat_ids) for p in new_patterns.values()),
        }

    def _phase_illuminate(self) -> Dict[str, Any]:
        """ILLUMINATE: high-luminosity patterns create illuminated story moments."""
        illuminated = 0
        for pattern in self._patterns.values():
            if pattern.combined_luminosity < 0.5:
                continue
            # Check if we already have a moment for this pattern
            has_existing = any(
                m.luminosity >= pattern.combined_luminosity - 0.1
                and m.chromaticity == pattern.dominant_chromaticity
                for m in self._moments
            )
            if has_existing:
                continue
            # Determine illumination type from chromaticity and polarization
            illum_type = self._determine_illumination(
                pattern.dominant_chromaticity, pattern.dominant_polarization
            )
            moment = IlluminatedMoment(
                moment_id=f"illum_{illum_type.value}_{int(time.time() * 1000) % 100000}",
                illumination_type=illum_type,
                luminosity=pattern.combined_luminosity,
                chromaticity=pattern.dominant_chromaticity,
                polarization=pattern.dominant_polarization,
                source_beats=list(pattern.beat_ids),
                description=f"{illum_type.value.replace('_', ' ').title()} - "
                           f"{pattern.dominant_chromaticity.value} luminosity at {pattern.combined_luminosity:.3f}",
            )
            self._moments.append(moment)
            illuminated += 1
            self._stats["total_illuminations"] = len(self._moments)
            self._record_event("illuminated", {
                "moment_id": moment.moment_id,
                "type": illum_type.value,
                "luminosity": round(moment.luminosity, 4),
            })
        return {"illuminated": illuminated, "total_moments": len(self._moments)}

    def _determine_illumination(
        self, chroma: NarrativeChromaticity, polar: BeatPolarization
    ) -> IlluminationType:
        """Determine illumination type from chromaticity and polarization."""
        if chroma == NarrativeChromaticity.GOLD and polar == BeatPolarization.ASCENDING:
            return IlluminationType.CLIMAX
        if chroma == NarrativeChromaticity.WHITE:
            return IlluminationType.EPIPHANY
        if chroma == NarrativeChromaticity.VIOLET:
            return IlluminationType.REVELATION
        if chroma == NarrativeChromaticity.ASHEN and polar == BeatPolarization.DESCENDING:
            return IlluminationType.CATHARSIS
        if chroma == NarrativeChromaticity.CRIMSON and polar == BeatPolarization.ASCENDING:
            return IlluminationType.CALL_TO_ACTION
        if chroma == NarrativeChromaticity.AZURE and polar == BeatPolarization.STILL:
            return IlluminationType.REFLECTION
        if polar == BeatPolarization.VORTEX:
            return IlluminationType.CONVERGENCE
        return IlluminationType.THRESHOLD

    def _random_direction(self) -> Tuple[float, float, float]:
        """Generate a random unit direction vector."""
        import random as _rng
        theta = _rng.uniform(0, 2 * math.pi)
        phi = _rng.uniform(0, math.pi)
        x = math.sin(phi) * math.cos(theta)
        y = math.sin(phi) * math.sin(theta)
        z = math.cos(phi)
        return (x, y, z)

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get global flux status."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_beats": len(self._beats),
                "total_media": len(self._media),
                "total_rays": len(self._rays),
                "total_patterns": len(self._patterns),
                "total_moments": len(self._moments),
                "total_shadows": len(self._shadows),
                "stats": dict(self._stats),
            }

    def list_beats(self) -> List[Dict[str, Any]]:
        """List all story beats."""
        with self._global_lock:
            return [
                {
                    "beat_id": b.beat_id,
                    "label": b.label,
                    "luminosity": round(b.luminosity, 4),
                    "chromaticity": b.chromaticity.value,
                    "polarization": b.polarization.value,
                    "wavelength": b.wavelength,
                    "active": b.active,
                    "distance_traveled": round(b.distance_traveled, 4),
                }
                for b in self._beats.values()
            ]

    def list_media(self) -> List[Dict[str, Any]]:
        """List all narrative media."""
        with self._global_lock:
            return [
                {
                    "medium_id": m.medium_id,
                    "label": m.label,
                    "type": m.medium_type.value,
                    "density": m.density,
                    "refraction_index": m.refraction_index,
                    "absorption": m.absorption,
                }
                for m in self._media.values()
            ]

    def get_patterns(self) -> List[Dict[str, Any]]:
        """Get convergence patterns."""
        with self._global_lock:
            return [
                {
                    "pattern_id": p.pattern_id,
                    "ray_count": len(p.ray_ids),
                    "beat_ids": list(p.beat_ids),
                    "combined_luminosity": round(p.combined_luminosity, 4),
                    "dominant_chromaticity": p.dominant_chromaticity.value,
                    "dominant_polarization": p.dominant_polarization.value,
                    "coherence": round(p.coherence, 4),
                }
                for p in self._patterns.values()
            ]

    def get_moments(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get illuminated story moments."""
        with self._global_lock:
            return [
                {
                    "moment_id": m.moment_id,
                    "type": m.illumination_type.value,
                    "luminosity": round(m.luminosity, 4),
                    "chromaticity": m.chromaticity.value,
                    "polarization": m.polarization.value,
                    "source_beats": m.source_beats,
                    "description": m.description,
                    "timestamp": m.timestamp,
                }
                for m in list(self._moments)[-limit:]
            ]

    def get_shadows(self) -> List[Dict[str, Any]]:
        """Get narrative shadows."""
        with self._global_lock:
            return [
                {
                    "shadow_id": s.shadow_id,
                    "label": s.label,
                    "darkness": s.darkness,
                    "revealed": s.revealed,
                    "surrounding_beats": s.surrounding_beats,
                }
                for s in self._shadows.values()
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent flux events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire flux."""
        with self._global_lock:
            n = len(self._beats)
            self._beats.clear()
            self._media.clear()
            self._rays.clear()
            self._patterns.clear()
            self._moments.clear()
            self._shadows.clear()
            self._phase = FluxPhase.EMIT
            self._cycle_count = 0
            self._events_log.clear()
            self._stats = {
                "total_beats": 0,
                "total_media": 0,
                "total_rays": 0,
                "total_patterns": 0,
                "total_illuminations": 0,
                "total_shadows": 0,
                "avg_luminosity": 0.0,
                "max_luminosity": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "cleared_beats": n}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _update_stats(self) -> None:
        """Update aggregate statistics."""
        if self._beats:
            luminosities = [b.luminosity for b in self._beats.values()]
            self._stats["avg_luminosity"] = sum(luminosities) / len(luminosities)
            self._stats["max_luminosity"] = max(luminosities)
        else:
            self._stats["avg_luminosity"] = 0.0
            self._stats["max_luminosity"] = 0.0

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record a flux event."""
        self._events_log.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
