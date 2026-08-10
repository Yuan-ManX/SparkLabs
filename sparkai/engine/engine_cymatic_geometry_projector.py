"""
SparkLabs Engine - Cymatic Geometry Projector"""

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

class CymaticPhase(Enum):
    """Phases of the cymatic geometry projection cycle."""
    REGISTER_SOURCE = "register_source"      # register sound sources with frequency, amplitude, position
    PROPAGATE_FIELD = "propagate_field"      # propagate vibrational fields from sources through the scene
    IMPRINT_GEOMETRY = "imprint_geometry"    # compute standing-wave imprints on nearby surfaces
    RENDER_OVERLAYS = "render_overlays"      # render editor-previewable cymatic overlays per surface
    EMIT_CYMATIC_MAP = "emit_cymatic_map"    # emit the full cymatic map with sources, fields, imprints, overlays


class SourceKind(Enum):
    """The kind of sound source emitting a vibrational field."""
    POINT = "point"                  # omnidirectional point source
    DIRECTIONAL = "directional"      # focused directional emission
    AMBIENT = "ambient"              # ambient room fill
    RESONANT = "resonant"            # resonant cavity driver


class WaveMode(Enum):
    """The vibrational mode a source produces."""
    RADIAL = "radial"                # radial standing wave
    CONCENTRIC = "concentric"        # concentric ring pattern
    LATTICE = "lattice"              # intricate lattice grid
    NODAL = "nodal"                  # nodal-line dominant


class ImprintPattern(Enum):
    """The standing-wave pattern imprinted on a surface."""
    NODES = "nodes"                        # stationary nodes
    ANTINODES = "antinodes"                # peak antinodes
    RADIAL_SYMMETRY = "radial_symmetry"    # rotational symmetry
    CHLADNI = "chladni"                    # Chladni-style figure


class SourceState(Enum):
    """State of an individual sound source through the cycle."""
    PENDING = "pending"              # registered but not yet processed
    REGISTERED = "registered"        # confirmed and classified
    PROPAGATED = "propagated"        # vibrational field propagated
    IMPRINTED = "imprinted"          # standing-wave imprint computed
    OVERLAID = "overlaid"            # editor overlay rendered
    EMITTED = "emitted"              # emitted into the cymatic map


class Vitality(Enum):
    """Overall vitality of the cymatic ecosystem."""
    SILENT = "silent"
    HUMMING = "humming"
    RESONATING = "resonating"
    VIBRANT = "vibrant"
    SATURATED = "saturated"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SoundSource:
    """A sound source that emits a vibrational field into the scene."""
    source_id: str
    source_handle: str
    label: str
    frequency: float                              # Hz
    amplitude: float                              # 0.0-1.0
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    kind: SourceKind = SourceKind.POINT
    wave_mode: WaveMode = WaveMode.RADIAL
    pattern: ImprintPattern = ImprintPattern.NODES
    field_reach: float = 1.0                      # how far the vibrational field reaches
    active: bool = True
    state: SourceState = SourceState.PENDING
    vitality: Vitality = Vitality.SILENT
    created_at: float = field(default_factory=time.time)
    last_propagated_at: float = 0.0
    note: str = ""


@dataclass
class SurfaceImprint:
    """A standing-wave imprint on a nearby surface from a source's field."""
    imprint_id: str
    source_id: str
    surface_label: str
    pattern: ImprintPattern = ImprintPattern.NODES
    symmetry_order: int = 2
    node_count: int = 1
    antinode_count: int = 2
    sharpness: float = 0.5                        # 0.0-1.0
    state: str = "imprinted"
    created_at: float = field(default_factory=time.time)


# =============================================================================
# Projector
# =============================================================================

class CymaticGeometryProjector:
    """
    Thread-safe singleton that projects cymatic resonance patterns onto
    scene geometry.

    Sound sources are keyed internally by source_handle so that each logical
    source owns exactly one entry. The source_id is a generated handle for
    external lookups; lookups by source_id fall back to a linear scan of
    the registered sources.

    Usage:
        projector = CymaticGeometryProjector.get_instance()
        projector.register_source(
            source_handle="src::bass_drum",
            label="Bass Drum",
            frequency=80.0,
            amplitude=0.9,
            position={"x": 0.0, "y": 0.0, "z": 0.0},
        )
        projector.cycle()
        source = projector.get_source(source_id)
        cymatic_map = projector.get_cymatic_map()
    """

    _instance: Optional["CymaticGeometryProjector"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Capacity caps.
    _MAX_SOURCES = 60
    _MAX_EVENTS = 200
    _MAX_FIELDS = 60
    _MAX_IMPRINTS = 120
    _MAX_OVERLAYS = 120

    # Domain tuning constants.
    _SPEED_OF_SOUND = 343.0          # m/s, used for wavelength computation
    _FREQUENCY_MIN = 20.0            # Hz, lower bound of audible range
    _FREQUENCY_MAX = 20000.0         # Hz, upper bound of audible range
    _FIELD_REACH_BASE = 8.0          # base multiplier for field reach from amplitude
    _FIELD_REACH_FREQ_FACTOR = 200.0 # lower frequencies reach further
    _PROPAGATION_DECAY = 0.02        # intensity decay per unit distance
    _VITALITY_VIBRANT_FRACTION = 0.6
    _VITALITY_SATURATED_FRACTION = 0.9

    # Surface labels available for imprinting.
    _SURFACE_LABELS = (
        "floor", "ceiling", "wall_north", "wall_south", "wall_east", "wall_west",
    )

    def __init__(self) -> None:
        # Internal dict keyed by source_handle (NOT source_id).
        self._sources: Dict[str, SoundSource] = {}
        self._fields: Dict[str, Dict[str, Any]] = {}
        self._imprints: Dict[str, SurfaceImprint] = {}
        self._overlays: Dict[str, Dict[str, Any]] = {}
        self._phase: CymaticPhase = CymaticPhase.REGISTER_SOURCE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._sources:
            self._seed_synthetic_sources()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "CymaticGeometryProjector":
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
            "sources_registered": 0,
            "phase_runs": 0,
            "fields_propagated": 0,
            "imprints_computed": 0,
            "overlays_rendered": 0,
            "cymatic_maps_emitted": 0,
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
    def _parse_source_kind(value: Any) -> SourceKind:
        """Parse a SourceKind from a string, enum, or None."""
        if value is None:
            return SourceKind.POINT
        if isinstance(value, SourceKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in SourceKind:
                if kind.value == lowered:
                    return kind
        return SourceKind.POINT

    @staticmethod
    def _parse_wave_mode(value: Any) -> WaveMode:
        """Parse a WaveMode from a string, enum, or None."""
        if value is None:
            return WaveMode.RADIAL
        if isinstance(value, WaveMode):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for mode in WaveMode:
                if mode.value == lowered:
                    return mode
        return WaveMode.RADIAL

    @staticmethod
    def _parse_position(value: Any) -> Dict[str, float]:
        """Parse a position dict from input, defaulting to origin."""
        if value is None:
            return {"x": 0.0, "y": 0.0, "z": 0.0}
        if isinstance(value, dict):
            return {
                "x": float(value.get("x", 0.0)),
                "y": float(value.get("y", 0.0)),
                "z": float(value.get("z", 0.0)),
            }
        return {"x": 0.0, "y": 0.0, "z": 0.0}

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_wave_mode(self, frequency: float) -> WaveMode:
        """Classify the vibrational wave mode from frequency."""
        if frequency < 200.0:
            return WaveMode.RADIAL
        if frequency < 800.0:
            return WaveMode.CONCENTRIC
        if frequency < 2000.0:
            return WaveMode.NODAL
        return WaveMode.LATTICE

    def _classify_pattern(self, frequency: float, amplitude: float) -> ImprintPattern:
        """Classify the standing-wave imprint pattern from frequency and amplitude."""
        if frequency < 200.0 and amplitude >= 0.5:
            return ImprintPattern.NODES
        if frequency < 800.0:
            return ImprintPattern.RADIAL_SYMMETRY
        if frequency < 2000.0:
            return ImprintPattern.ANTINODES
        return ImprintPattern.CHLADNI

    def _compute_field_reach(self, frequency: float, amplitude: float) -> float:
        """Compute how far a source's vibrational field reaches."""
        freq_factor = self._FIELD_REACH_FREQ_FACTOR / max(frequency, self._FREQUENCY_MIN)
        return amplitude * self._FIELD_REACH_BASE * (1.0 + freq_factor)

    def _compute_wavelength(self, frequency: float) -> float:
        """Compute the wavelength from frequency."""
        return self._SPEED_OF_SOUND / max(frequency, self._FREQUENCY_MIN)

    def _compute_symmetry_order(self, frequency: float) -> int:
        """Compute the radial symmetry order from frequency."""
        order = int(2 + frequency / 200.0)
        return max(2, min(order, 12))

    def _compute_sharpness(self, frequency: float, amplitude: float) -> float:
        """Compute pattern sharpness (0.0-1.0) from frequency and amplitude."""
        freq_boost = 100.0 / max(frequency, self._FREQUENCY_MIN)
        return min(1.0, amplitude * (1.0 + freq_boost))

    def _color_for_frequency(self, frequency: float) -> str:
        """Map a frequency to a preview color for the overlay."""
        if frequency < 200.0:
            return "#8B0000"  # dark red - bold low rumble
        if frequency < 800.0:
            return "#FF4500"  # orange-red
        if frequency < 2000.0:
            return "#FFD700"  # gold
        if frequency < 4000.0:
            return "#00CED1"  # dark turquoise
        return "#9370DB"  # medium purple - intricate highs

    # -------------------------------------------------------------------------
    # Source Management
    # -------------------------------------------------------------------------

    def register_source(
        self,
        source_handle: str,
        label: str,
        frequency: float = 440.0,
        amplitude: float = 0.5,
        position: Optional[Dict[str, float]] = None,
        kind: Optional[str] = None,
        wave_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register a new sound source for cymatic projection."""
        with self._global_lock:
            if source_handle in self._sources:
                return {"error": f"Source already registered: {source_handle}"}
            if len(self._sources) >= self._MAX_SOURCES:
                return {"error": f"Source cap reached ({self._MAX_SOURCES})"}

            source_id = f"src_{source_handle}_{int(time.time() * 1000)}_{random.randint(100, 999)}"

            freq = max(self._FREQUENCY_MIN, min(self._FREQUENCY_MAX, float(frequency)))
            amp = max(0.0, min(1.0, float(amplitude)))
            pos = self._parse_position(position)
            parsed_kind = self._parse_source_kind(kind)
            # If the caller did not specify a wave_mode, classify it from frequency.
            if wave_mode is None:
                parsed_mode = self._classify_wave_mode(freq)
            else:
                parsed_mode = self._parse_wave_mode(wave_mode)
            pattern = self._classify_pattern(freq, amp)

            source = SoundSource(
                source_id=source_id,
                source_handle=source_handle,
                label=label,
                frequency=freq,
                amplitude=amp,
                position=pos,
                kind=parsed_kind,
                wave_mode=parsed_mode,
                pattern=pattern,
                field_reach=self._compute_field_reach(freq, amp),
                active=True,
                state=SourceState.PENDING,
                vitality=Vitality.SILENT,
                created_at=time.time(),
                last_propagated_at=0.0,
                note="",
            )
            self._sources[source_handle] = source
            self._update_stats(sources_registered=1)
            self._record_event("source_registered", {
                "source_id": source_id,
                "source_handle": source_handle,
                "label": label,
                "frequency": freq,
                "amplitude": amp,
                "kind": parsed_kind.value,
                "wave_mode": parsed_mode.value,
                "pattern": pattern.value,
            })
            return {
                "source_id": source_id,
                "source_handle": source_handle,
                "label": label,
                "frequency": freq,
                "amplitude": amp,
                "kind": parsed_kind.value,
                "wave_mode": parsed_mode.value,
                "pattern": pattern.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single cymatic geometry projection cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic sources on the very first cycle if none exist.
            if not self._sources and self._cycle_count == 0:
                self._seed_synthetic_sources()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = CymaticPhase.REGISTER_SOURCE
            phase_outputs.append(self._phase_register_source())
            self._phase = CymaticPhase.PROPAGATE_FIELD
            phase_outputs.append(self._phase_propagate_field())
            self._phase = CymaticPhase.IMPRINT_GEOMETRY
            phase_outputs.append(self._phase_imprint_geometry())
            self._phase = CymaticPhase.RENDER_OVERLAYS
            phase_outputs.append(self._phase_render_overlays())
            self._phase = CymaticPhase.EMIT_CYMATIC_MAP
            phase_outputs.append(self._phase_emit_cymatic_map())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_register_source(self) -> Dict[str, Any]:
        """Register phase: confirm pending sources and classify their vibrational profiles."""
        registered = 0
        frequency_sum = 0.0
        for source in self._sources.values():
            if source.state != SourceState.PENDING:
                continue
            # Recompute derived attributes in case frequency/amplitude were adjusted.
            source.wave_mode = self._classify_wave_mode(source.frequency)
            source.pattern = self._classify_pattern(source.frequency, source.amplitude)
            source.field_reach = self._compute_field_reach(source.frequency, source.amplitude)
            source.state = SourceState.REGISTERED
            registered += 1
            frequency_sum += source.frequency
        avg_frequency = (frequency_sum / registered) if registered > 0 else 0.0
        self._update_stats(phase_runs=1)
        self._record_event("phase_register_source", {
            "registered": registered,
            "avg_frequency": avg_frequency,
        })
        return {
            "phase": "register_source",
            "registered": registered,
            "avg_frequency": avg_frequency,
        }

    def _phase_propagate_field(self) -> Dict[str, Any]:
        """Propagate phase: emit vibrational fields from confirmed sources through the scene."""
        propagated = 0
        for source in self._sources.values():
            if source.state != SourceState.REGISTERED:
                continue
            wavelength = self._compute_wavelength(source.frequency)
            reach = source.field_reach
            # Intensity decays with distance from the source.
            intensity = source.amplitude * max(0.0, 1.0 - self._PROPAGATION_DECAY * reach)
            # Node and antinode counts come from the standing-wave structure.
            node_count = max(1, int(reach / max(wavelength * 0.5, 0.001)))
            antinode_count = node_count + 1

            field_id = f"vf_{source.source_id}_{int(time.time() * 1000)}_{random.randint(100, 999)}"
            vibrational_field = {
                "field_id": field_id,
                "source_id": source.source_id,
                "source_handle": source.source_handle,
                "frequency": source.frequency,
                "amplitude": source.amplitude,
                "reach": reach,
                "intensity": intensity,
                "wavelength": wavelength,
                "wave_mode": source.wave_mode.value,
                "node_count": node_count,
                "antinode_count": antinode_count,
                "state": "propagated",
                "created_at": time.time(),
            }
            # Cap the field collection.
            if len(self._fields) >= self._MAX_FIELDS:
                # Drop the oldest field to make room.
                oldest_key = next(iter(self._fields))
                self._fields.pop(oldest_key, None)
            self._fields[field_id] = vibrational_field
            source.state = SourceState.PROPAGATED
            source.last_propagated_at = time.time()
            propagated += 1
        self._update_stats(phase_runs=1, fields_propagated=propagated)
        self._record_event("phase_propagate_field", {"propagated": propagated})
        return {"phase": "propagate_field", "propagated": propagated}

    def _phase_imprint_geometry(self) -> Dict[str, Any]:
        """Imprint phase: compute standing-wave imprints on nearby surfaces."""
        imprinted_sources = 0
        imprints_created = 0
        for source in self._sources.values():
            if source.state != SourceState.PROPAGATED:
                continue
            # Determine how many nearby surfaces this field reaches.
            surface_count = 2 + (1 if source.amplitude >= 0.5 else 0)
            available = list(self._SURFACE_LABELS)
            chosen_surfaces = random.sample(available, min(surface_count, len(available)))
            for surface_label in chosen_surfaces:
                imprint_id = (
                    f"imp_{source.source_id}_{surface_label}_"
                    f"{int(time.time() * 1000)}_{random.randint(100, 999)}"
                )
                field_data = None
                for fd in self._fields.values():
                    if fd.get("source_id") == source.source_id:
                        field_data = fd
                        break
                node_count = field_data["node_count"] if field_data else 1
                antinode_count = field_data["antinode_count"] if field_data else 2
                imprint = SurfaceImprint(
                    imprint_id=imprint_id,
                    source_id=source.source_id,
                    surface_label=surface_label,
                    pattern=source.pattern,
                    symmetry_order=self._compute_symmetry_order(source.frequency),
                    node_count=node_count,
                    antinode_count=antinode_count,
                    sharpness=self._compute_sharpness(source.frequency, source.amplitude),
                    state="imprinted",
                    created_at=time.time(),
                )
                # Cap the imprint collection.
                if len(self._imprints) >= self._MAX_IMPRINTS:
                    oldest_key = next(iter(self._imprints))
                    self._imprints.pop(oldest_key, None)
                self._imprints[imprint_id] = imprint
                imprints_created += 1
            source.state = SourceState.IMPRINTED
            imprinted_sources += 1
        self._update_stats(phase_runs=1, imprints_computed=imprints_created)
        self._record_event("phase_imprint_geometry", {
            "imprinted_sources": imprinted_sources,
            "imprints_created": imprints_created,
        })
        return {
            "phase": "imprint_geometry",
            "imprinted_sources": imprinted_sources,
            "imprints_created": imprints_created,
        }

    def _phase_render_overlays(self) -> Dict[str, Any]:
        """Render phase: render editor-previewable cymatic overlays per surface."""
        overlaid_sources = 0
        overlays_created = 0
        for source in self._sources.values():
            if source.state != SourceState.IMPRINTED:
                continue
            for imprint in self._imprints.values():
                if imprint.source_id != source.source_id:
                    continue
                if imprint.state != "imprinted":
                    continue
                overlay_id = (
                    f"ovl_{imprint.imprint_id}_"
                    f"{int(time.time() * 1000)}_{random.randint(100, 999)}"
                )
                overlay = {
                    "overlay_id": overlay_id,
                    "source_id": source.source_id,
                    "imprint_id": imprint.imprint_id,
                    "surface_label": imprint.surface_label,
                    "pattern": imprint.pattern.value,
                    "visible": True,
                    "color": self._color_for_frequency(source.frequency),
                    "line_weight": source.amplitude * 3.0 + 0.5,
                    "preview_url": f"/preview/cymatic/{overlay_id}.svg",
                    "state": "rendered",
                    "created_at": time.time(),
                }
                # Cap the overlay collection.
                if len(self._overlays) >= self._MAX_OVERLAYS:
                    oldest_key = next(iter(self._overlays))
                    self._overlays.pop(oldest_key, None)
                self._overlays[overlay_id] = overlay
                imprint.state = "overlaid"
                overlays_created += 1
            source.state = SourceState.OVERLAID
            overlaid_sources += 1
        self._update_stats(phase_runs=1, overlays_rendered=overlays_created)
        self._record_event("phase_render_overlays", {
            "overlaid_sources": overlaid_sources,
            "overlays_created": overlays_created,
        })
        return {
            "phase": "render_overlays",
            "overlaid_sources": overlaid_sources,
            "overlays_created": overlays_created,
        }

    def _phase_emit_cymatic_map(self) -> Dict[str, Any]:
        """Emit phase: emit the full cymatic map with sources, fields, imprints, overlays."""
        emitted = 0
        for source in self._sources.values():
            if source.state != SourceState.OVERLAID:
                continue
            source.state = SourceState.EMITTED
            source.vitality = self._derive_vitality()
            emitted += 1
        # Mark imprints as emitted.
        for imprint in self._imprints.values():
            if imprint.state == "overlaid":
                imprint.state = "emitted"
        # Mark overlays as emitted.
        for overlay in self._overlays.values():
            if overlay.get("state") == "rendered":
                overlay["state"] = "emitted"
        map_size = (
            len(self._sources) + len(self._fields)
            + len(self._imprints) + len(self._overlays)
        )
        self._update_stats(phase_runs=1, cymatic_maps_emitted=1)
        self._record_event("phase_emit_cymatic_map", {
            "emitted": emitted,
            "map_size": map_size,
        })
        return {
            "phase": "emit_cymatic_map",
            "emitted": emitted,
            "map_size": map_size,
        }

    # -------------------------------------------------------------------------
    # Vitality
    # -------------------------------------------------------------------------

    def _derive_vitality(self) -> Vitality:
        """Derive overall ecosystem vitality from the source population."""
        count = len(self._sources)
        if count == 0:
            return Vitality.SILENT
        if count <= 2:
            return Vitality.HUMMING
        if count <= 5:
            return Vitality.RESONATING
        if count <= 10:
            return Vitality.VIBRANT
        return Vitality.SATURATED

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_sources(self) -> None:
        """Seed a few synthetic sound sources on the first cycle if empty."""
        seeds = [
            (
                "src::bass_rumble",
                "Bass Rumble",
                65.0,                       # low frequency - bold, simple patterns
                0.9,                        # high amplitude
                {"x": 0.0, "y": 0.0, "z": 0.0},
                SourceKind.RESONANT,
                WaveMode.RADIAL,
            ),
            (
                "src::mid_tone",
                "Mid Tone",
                440.0,                      # mid frequency - moderate complexity
                0.6,
                {"x": 3.0, "y": 1.0, "z": 0.0},
                SourceKind.POINT,
                WaveMode.CONCENTRIC,
            ),
            (
                "src::treble_chime",
                "Treble Chime",
                3200.0,                     # high frequency - intricate lattice
                0.4,
                {"x": -2.0, "y": 2.0, "z": 1.0},
                SourceKind.DIRECTIONAL,
                WaveMode.LATTICE,
            ),
        ]
        for source_handle, label, frequency, amplitude, position, kind, wave_mode in seeds:
            if source_handle in self._sources:
                continue
            if len(self._sources) >= self._MAX_SOURCES:
                break
            self.register_source(
                source_handle=source_handle,
                label=label,
                frequency=frequency,
                amplitude=amplitude,
                position=position,
                kind=kind.value,
                wave_mode=wave_mode.value,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _source_to_dict(self, source: SoundSource) -> Dict[str, Any]:
        return {
            "source_id": source.source_id,
            "source_handle": source.source_handle,
            "label": source.label,
            "frequency": source.frequency,
            "amplitude": source.amplitude,
            "position": dict(source.position),
            "kind": source.kind.value,
            "wave_mode": source.wave_mode.value,
            "pattern": source.pattern.value,
            "field_reach": source.field_reach,
            "active": source.active,
            "state": source.state.value,
            "vitality": source.vitality.value,
            "created_at": source.created_at,
            "last_propagated_at": source.last_propagated_at,
            "note": source.note,
        }

    def _imprint_to_dict(self, imprint: SurfaceImprint) -> Dict[str, Any]:
        return {
            "imprint_id": imprint.imprint_id,
            "source_id": imprint.source_id,
            "surface_label": imprint.surface_label,
            "pattern": imprint.pattern.value,
            "symmetry_order": imprint.symmetry_order,
            "node_count": imprint.node_count,
            "antinode_count": imprint.antinode_count,
            "sharpness": imprint.sharpness,
            "state": imprint.state,
            "created_at": imprint.created_at,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "sources": len(self._sources),
                "fields": len(self._fields),
                "imprints": len(self._imprints),
                "overlays": len(self._overlays),
                "stats": dict(self._stats),
            }

    def get_sources(self, limit: int = 50) -> Dict[str, Any]:
        with self._global_lock:
            sources = sorted(
                self._sources.values(),
                key=lambda s: s.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(sources),
                "sources": [
                    {
                        "source_id": s.source_id,
                        "source_handle": s.source_handle,
                        "label": s.label,
                        "frequency": s.frequency,
                        "amplitude": s.amplitude,
                        "kind": s.kind.value,
                        "wave_mode": s.wave_mode.value,
                        "pattern": s.pattern.value,
                        "field_reach": s.field_reach,
                        "state": s.state.value,
                        "vitality": s.vitality.value,
                        "active": s.active,
                    }
                    for s in sources
                ],
            }

    def get_source(self, source_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by source_handle, NOT source_id, so we MUST
        # iterate over values and match on the source_id attribute.
        with self._global_lock:
            for source in self._sources.values():
                if source.source_id == source_id:
                    return self._source_to_dict(source)
            return {"error": f"Source not found: {source_id}", "source_id": source_id}

    def get_cymatic_map(self) -> Dict[str, Any]:
        """Return the full cymatic map with sources, fields, imprints, and overlays."""
        with self._global_lock:
            return {
                "sources": [self._source_to_dict(s) for s in self._sources.values()],
                "fields": list(self._fields.values()),
                "imprints": [self._imprint_to_dict(i) for i in self._imprints.values()],
                "overlays": list(self._overlays.values()),
                "source_count": len(self._sources),
                "field_count": len(self._fields),
                "imprint_count": len(self._imprints),
                "overlay_count": len(self._overlays),
                "cycle_count": self._cycle_count,
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic sources if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._sources:
                self._seed_synthetic_sources()
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
            self._sources.clear()
            self._fields.clear()
            self._imprints.clear()
            self._overlays.clear()
            self._phase = CymaticPhase.REGISTER_SOURCE
            self._cycle_count = 0
            self._init_stats()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }
