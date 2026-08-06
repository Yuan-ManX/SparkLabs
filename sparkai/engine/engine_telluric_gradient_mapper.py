"""
SparkLabs Engine - Telluric Gradient Mapper

The TelluricGradientMapper charts the earth-current gradients that flow unseen
beneath the game world. Subterranean voltage differentials arise wherever
conductive strata, electrolytic pore water, and geomagnetic induction meet;
the mapper samples these differentials at probe stations, derives the local
gradient vector field, traces iso-voltage contours across the terrain, flags
anomalous surges that betray ore bodies, fault slip, or buried artifacts, and
finally emits a telluric map the editor can render as a flowing topographic
overlay of voltage shells and current streamlines.

This is original SparkLabs work. Telluric gradients are first-class entities:
their sample values, contour shapes, and anomaly signatures are recomputed
each cycle, and the editor previews them as a layered current-flow map so
designers can sculpt the hidden electrical geography of the world.

Architecture:
  SAMPLE_VOLTAGE    ->  COMPUTE_GRADIENT  ->  TRACE_CONTOURS  ->  DETECT_ANOMALIES  ->  EMIT_TELLURIC_MAP
  (sample voltage    (derive the local    (trace iso-voltage  (flag anomalous       (emit the full
   differentials     gradient vector      contours across     surges that betray    telluric map with
   at each probe     field from the       the terrain)        ore, fault, or        probe stations,
   station)          samples)                                  artifact)             gradients,
                                                                       contours, anomalies)

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
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class TelluricPhase(Enum):
    """Phases of the telluric gradient mapper cycle."""
    SAMPLE_VOLTAGE = "sample_voltage"        # sample voltage differentials at each probe station
    COMPUTE_GRADIENT = "compute_gradient"    # derive the local gradient vector field from the samples
    TRACE_CONTOURS = "trace_contours"        # trace iso-voltage contours across the terrain
    DETECT_ANOMALIES = "detect_anomalies"    # flag anomalous surges betraying ore, fault, or artifact
    EMIT_TELLURIC_MAP = "emit_telluric_map"  # emit the full telluric map with stations, gradients, contours, anomalies


class ProbeStationKind(Enum):
    """The kind of probe station sampling the telluric field."""
    SURFACE = "surface"          # surface probe driven into topsoil
    BOREHOLE = "borehole"        # deep borehole electrode
    SEABED = "seabed"            # seabed electrode for marine strata
    VAULT = "vault"              # shielded vault reference electrode


class GradientClass(Enum):
    """Classification of a telluric gradient by its magnitude and stability."""
    QUIESCENT = "quiescent"      # near-zero voltage differential, calm strata
    NOMINAL = "nominal"          # background terrestrial gradient
    CHARGED = "charged"          # elevated differential, conductive body nearby
    SURGING = "surging"          # rapidly fluctuating differential, active flow
    FAULTED = "faulted"          # extreme differential, likely fault slip or ore body


class CurrentDirection(Enum):
    """The dominant direction of telluric current flow along a gradient."""
    NORTHWARD = "northward"
    SOUTHWARD = "southward"
    EASTWARD = "eastward"
    WESTWARD = "westward"
    RADIAL_IN = "radial_in"      # current converging on a sink
    RADIAL_OUT = "radial_out"    # current diverging from a source


class FieldState(Enum):
    """State of an individual gradient entity through the cycle."""
    PENDING = "pending"          # registered but not yet sampled
    SAMPLED = "sampled"          # voltage differential sampled
    COMPUTED = "computed"        # gradient vector field computed
    CONTOURED = "contoured"      # iso-voltage contours traced
    ANALYZED = "analyzed"        # anomaly analysis complete
    EMITTED = "emitted"          # emitted into the telluric map


class FieldVitality(Enum):
    """Overall vitality of the telluric field ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    FLOWING = "flowing"
    DYNAMIC = "dynamic"
    CHAOTIC = "chaotic"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ProbeStation:
    """A probe station that measures the local telluric potential."""
    station_id: str
    station_handle: str
    label: str
    latitude: float                                # world-space latitude, -90.0 to 90.0
    longitude: float                               # world-space longitude, -180.0 to 180.0
    depth_m: float                                 # electrode depth in meters, >= 0.0
    kind: ProbeStationKind = ProbeStationKind.SURFACE
    contact_resistance_ohm: float = 100.0          # ground contact resistance
    potential_mv: float = 0.0                      # last sampled potential in millivolts
    active: bool = True
    vitality: FieldVitality = FieldVitality.DORMANT
    created_at: float = field(default_factory=time.time)
    last_sampled_at: float = 0.0
    note: str = ""


@dataclass
class TelluricGradient:
    """A telluric gradient measured between two probe stations."""
    gradient_id: str
    entity_id: str                                 # internal key, distinct from gradient_id
    source_station_id: str
    sink_station_id: str
    label: str
    voltage_mv: float                              # potential differential in millivolts
    distance_m: float                              # electrode spacing in meters
    gradient_class: GradientClass = GradientClass.NOMINAL
    current_direction: CurrentDirection = CurrentDirection.NORTHWARD
    current_density_ma_per_m2: float = 0.0         # estimated current density
    azimuth_deg: float = 0.0                       # flow azimuth in degrees, 0-360
    stability: float = 0.5                         # 0.0 (wild) to 1.0 (rock-steady)
    anomaly_signal: float = 0.0                    # 0.0-1.0, fraction of anomaly threshold reached
    contour_id: Optional[str] = None               # linked iso-voltage contour, if any
    state: FieldState = FieldState.PENDING
    created_at: float = field(default_factory=time.time)
    last_sampled_at: float = 0.0
    note: str = ""


# =============================================================================
# Mapper
# =============================================================================

class TelluricGradientMapper:
    """
    Thread-safe singleton that maps earth-current gradients across the game
    world.

    Probe stations are keyed internally by station_handle so that each logical
    probe owns exactly one entry. Gradients are keyed internally by entity_id
    (NOT gradient_id); lookups by gradient_id fall back to a linear scan of
    the registered gradients.

    Usage:
        mapper = TelluricGradientMapper.get_instance()
        mapper.register_gradient(
            source_handle="probe::alpha",
            sink_handle="probe::beta",
            label="Alpha-Beta Spacing",
            voltage_mv=42.0,
            distance_m=120.0,
        )
        mapper.cycle()
        gradient = mapper.get_gradient(gradient_id)
        report = mapper.map_gradients()
    """

    _instance: Optional["TelluricGradientMapper"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Capacity caps.
    _MAX_GRADIENTS = 100
    _MAX_EVENTS = 200
    _MAX_STATIONS = 80
    _MAX_CONTOURS = 120
    _MAX_ANOMALIES = 60
    _MAX_SAMPLES = 200

    # Domain tuning constants.
    _DEG_TO_RAD = math.pi / 180.0
    _EARTH_RADIUS_M = 6_371_000.0
    _QUIESCENT_VOLTAGE_MAX = 5.0           # below this differential, strata are calm
    _NOMINAL_VOLTAGE_MAX = 25.0            # below this, background terrestrial gradient
    _CHARGED_VOLTAGE_MAX = 80.0            # below this, conductive body nearby
    _SURGING_VOLTAGE_MAX = 200.0           # below this, active flow
    _ANOMALY_VOLTAGE_THRESHOLD = 150.0     # above this, anomaly signature ramps up
    _MAX_STABILITY = 1.0
    _MIN_CONTACT_RESISTANCE = 1.0
    _CONDUCTIVITY_BASE = 0.01              # base formation conductivity, S/m
    _CONTOUR_STEP_MV = 10.0                # iso-voltage contour step in millivolts

    def __init__(self) -> None:
        # Internal dicts: stations keyed by station_handle, gradients keyed by entity_id.
        self._stations: Dict[str, ProbeStation] = {}
        self._gradients: Dict[str, TelluricGradient] = {}
        self._contours: Dict[str, Dict[str, Any]] = {}
        self._anomalies: Dict[str, Dict[str, Any]] = {}
        self._samples: Dict[str, Dict[str, Any]] = {}
        self._phase: TelluricPhase = TelluricPhase.SAMPLE_VOLTAGE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._gradients:
            self._seed_synthetic_gradients()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "TelluricGradientMapper":
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
            "gradients_registered": 0,
            "phase_runs": 0,
            "samples_taken": 0,
            "contours_traced": 0,
            "anomalies_detected": 0,
            "maps_emitted": 0,
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
    def _parse_probe_kind(value: Any) -> ProbeStationKind:
        """Parse a ProbeStationKind from a string, enum, or None."""
        if value is None:
            return ProbeStationKind.SURFACE
        if isinstance(value, ProbeStationKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in ProbeStationKind:
                if kind.value == lowered:
                    return kind
        return ProbeStationKind.SURFACE

    @staticmethod
    def _parse_current_direction(value: Any) -> CurrentDirection:
        """Parse a CurrentDirection from a string, enum, or None."""
        if value is None:
            return CurrentDirection.NORTHWARD
        if isinstance(value, CurrentDirection):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for direction in CurrentDirection:
                if direction.value == lowered:
                    return direction
        return CurrentDirection.NORTHWARD

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_gradient_class(self, voltage_mv: float, stability: float) -> GradientClass:
        """Classify a gradient by its voltage differential and stability."""
        if voltage_mv <= self._QUIESCENT_VOLTAGE_MAX and stability > 0.7:
            return GradientClass.QUIESCENT
        if voltage_mv <= self._NOMINAL_VOLTAGE_MAX:
            return GradientClass.NOMINAL
        if voltage_mv <= self._CHARGED_VOLTAGE_MAX:
            return GradientClass.CHARGED
        if voltage_mv <= self._SURGING_VOLTAGE_MAX:
            return GradientClass.SURGING
        return GradientClass.FAULTED

    def _classify_current_direction(self, azimuth_deg: float) -> CurrentDirection:
        """Classify the dominant current direction from the flow azimuth."""
        # Wrap into [0, 360) and bin into eight sectors.
        az = azimuth_deg % 360.0
        # Cardinal sectors first, then radial fallbacks encoded as boundary bands.
        if 315.0 <= az or az < 45.0:
            return CurrentDirection.NORTHWARD
        if 45.0 <= az < 135.0:
            return CurrentDirection.EASTWARD
        if 135.0 <= az < 225.0:
            return CurrentDirection.SOUTHWARD
        return CurrentDirection.WESTWARD

    def _azimuth_between(self, src_lat: float, src_lon: float, dst_lat: float, dst_lon: float) -> float:
        """Compute the initial azimuth (degrees, 0-360) from src to dst."""
        lat1 = src_lat * self._DEG_TO_RAD
        lat2 = dst_lat * self._DEG_TO_RAD
        dlon = (dst_lon - src_lon) * self._DEG_TO_RAD
        x = math.sin(dlon) * math.cos(lat2)
        y = (
            math.cos(lat1) * math.sin(lat2)
            - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        )
        bearing = math.atan2(x, y)
        return (bearing * 180.0 / math.pi) % 360.0

    def _haversine_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Great-circle distance in meters between two lat/lon points."""
        phi1 = lat1 * self._DEG_TO_RAD
        phi2 = lat2 * self._DEG_TO_RAD
        dphi = (lat2 - lat1) * self._DEG_TO_RAD
        dlmb = (lon2 - lon1) * self._DEG_TO_RAD
        a = (
            math.sin(dphi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2.0) ** 2
        )
        return 2.0 * self._EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    def _compute_current_density(self, voltage_mv: float, distance_m: float) -> float:
        """Estimate current density (mA/m^2) from voltage and spacing."""
        # Ohm's law in a resistive half-space; conductivity shapes the result.
        voltage_v = voltage_mv / 1000.0
        distance_safe = max(distance_m, 1.0)
        # E-field approximation; convert to current density via conductivity.
        e_field = voltage_v / distance_safe
        return abs(e_field * self._CONDUCTIVITY_BASE) * 1000.0

    def _color_for_gradient_class(self, gradient_class: GradientClass) -> str:
        """Map a gradient class to a preview color for the editor contour."""
        if gradient_class == GradientClass.QUIESCENT:
            return "#2E8B57"   # sea green - calm strata
        if gradient_class == GradientClass.NOMINAL:
            return "#4682B4"   # steel blue - background terrestrial flow
        if gradient_class == GradientClass.CHARGED:
            return "#FFD700"   # gold - conductive body nearby
        if gradient_class == GradientClass.SURGING:
            return "#FF4500"   # orange-red - active surge
        return "#8B0000"       # dark red - faulted extreme differential

    # -------------------------------------------------------------------------
    # Gradient Registration
    # -------------------------------------------------------------------------

    def register_gradient(
        self,
        source_handle: str,
        sink_handle: str,
        label: str,
        voltage_mv: float = 0.0,
        distance_m: float = 100.0,
        current_direction: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new telluric gradient between two probe stations."""
        with self._global_lock:
            if source_handle not in self._stations:
                return {"error": f"Unknown source station: {source_handle}"}
            if sink_handle not in self._stations:
                return {"error": f"Unknown sink station: {sink_handle}"}
            if source_handle == sink_handle:
                return {"error": "Source and sink stations must differ"}
            if len(self._gradients) >= self._MAX_GRADIENTS:
                return {"error": f"Gradient cap reached ({self._MAX_GRADIENTS})"}

            source = self._stations[source_handle]
            sink = self._stations[sink_handle]
            entity_id = (
                f"ent_{source_handle}_{sink_handle}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            gradient_id = (
                f"grad_{entity_id}_{random.randint(100, 999)}"
            )

            spacing = max(1.0, float(distance_m))
            voltage = float(voltage_mv)
            direction = self._parse_current_direction(current_direction)
            stability = 0.5
            gradient_class = self._classify_gradient_class(voltage, stability)
            current_density = self._compute_current_density(voltage, spacing)

            gradient = TelluricGradient(
                gradient_id=gradient_id,
                entity_id=entity_id,
                source_station_id=source.station_id,
                sink_station_id=sink.station_id,
                label=label,
                voltage_mv=voltage,
                distance_m=spacing,
                gradient_class=gradient_class,
                current_direction=direction,
                current_density_ma_per_m2=current_density,
                azimuth_deg=0.0,
                stability=stability,
                anomaly_signal=0.0,
                contour_id=None,
                state=FieldState.PENDING,
                created_at=time.time(),
                last_sampled_at=0.0,
                note=note,
            )
            self._gradients[entity_id] = gradient
            self._update_stats(gradients_registered=1)
            self._record_event("gradient_registered", {
                "gradient_id": gradient_id,
                "entity_id": entity_id,
                "source_station_id": source.station_id,
                "sink_station_id": sink.station_id,
                "label": label,
                "voltage_mv": voltage,
                "distance_m": spacing,
                "gradient_class": gradient_class.value,
            })

            return {
                "gradient_id": gradient_id,
                "entity_id": entity_id,
                "source_station_id": source.station_id,
                "sink_station_id": sink.station_id,
                "label": label,
                "voltage_mv": voltage,
                "distance_m": spacing,
                "gradient_class": gradient_class.value,
                "current_direction": direction.value,
                "current_density_ma_per_m2": current_density,
            }

    def _seed_stations_for_pair(self, source_handle: str, sink_handle: str) -> None:
        """Seed a minimal pair of probe stations if they are missing."""
        for handle, lat, lon, depth, kind in [
            (source_handle, 12.34, 45.67, 1.5, ProbeStationKind.SURFACE),
            (sink_handle, 12.40, 45.80, 25.0, ProbeStationKind.BOREHOLE),
        ]:
            if handle in self._stations:
                continue
            if len(self._stations) >= self._MAX_STATIONS:
                break
            station_id = (
                f"sta_{handle}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            station = ProbeStation(
                station_id=station_id,
                station_handle=handle,
                label=handle.replace("probe::", "").replace("_", " ").title(),
                latitude=lat,
                longitude=lon,
                depth_m=depth,
                kind=kind,
                contact_resistance_ohm=100.0,
                potential_mv=0.0,
                active=True,
                vitality=FieldVitality.DORMANT,
                created_at=time.time(),
                last_sampled_at=0.0,
                note="seeded",
            )
            self._stations[handle] = station

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single telluric gradient mapper cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic gradients on the very first cycle if none exist.
            if not self._gradients and self._cycle_count == 0:
                self._seed_synthetic_gradients()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = TelluricPhase.SAMPLE_VOLTAGE
            phase_outputs.append(self._phase_sample_voltage())
            self._phase = TelluricPhase.COMPUTE_GRADIENT
            phase_outputs.append(self._phase_compute_gradient())
            self._phase = TelluricPhase.TRACE_CONTOURS
            phase_outputs.append(self._phase_trace_contours())
            self._phase = TelluricPhase.DETECT_ANOMALIES
            phase_outputs.append(self._phase_detect_anomalies())
            self._phase = TelluricPhase.EMIT_TELLURIC_MAP
            phase_outputs.append(self._phase_emit_telluric_map())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_sample_voltage(self) -> Dict[str, Any]:
        """Sample phase: sample voltage differentials at each probe station."""
        samples_taken = 0
        potential_sum = 0.0
        for station in self._stations.values():
            if not station.active:
                continue
            # Each station picks up a small telluric potential modulated by its
            # contact resistance and depth; deeper probes see stronger signals.
            depth_factor = 1.0 + min(station.depth_m, 1000.0) / 100.0
            resistance_factor = self._MIN_CONTACT_RESISTANCE / max(
                station.contact_resistance_ohm, self._MIN_CONTACT_RESISTANCE,
            )
            base_potential = random.uniform(-50.0, 50.0) * depth_factor * resistance_factor
            station.potential_mv = base_potential
            station.last_sampled_at = time.time()
            potential_sum += abs(base_potential)
            samples_taken += 1
            sample_id = (
                f"smp_{station.station_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            sample_entry = {
                "sample_id": sample_id,
                "station_id": station.station_id,
                "potential_mv": base_potential,
                "depth_m": station.depth_m,
                "contact_resistance_ohm": station.contact_resistance_ohm,
                "created_at": station.last_sampled_at,
            }
            if len(self._samples) >= self._MAX_SAMPLES:
                oldest_key = next(iter(self._samples))
                self._samples.pop(oldest_key, None)
            self._samples[sample_id] = sample_entry
            # Mark gradients attached to this station as ready to compute.
            for gradient in self._gradients.values():
                if gradient.state == FieldState.PENDING and (
                    gradient.source_station_id == station.station_id
                    or gradient.sink_station_id == station.station_id
                ):
                    gradient.state = FieldState.SAMPLED
                    gradient.last_sampled_at = station.last_sampled_at
        avg_potential = (potential_sum / samples_taken) if samples_taken > 0 else 0.0
        self._update_stats(phase_runs=1, samples_taken=samples_taken)
        self._record_event("phase_sample_voltage", {
            "samples_taken": samples_taken,
            "avg_potential_mv": avg_potential,
        })
        return {
            "phase": "sample_voltage",
            "samples_taken": samples_taken,
            "avg_potential_mv": avg_potential,
        }

    def _phase_compute_gradient(self) -> Dict[str, Any]:
        """Compute phase: derive the local gradient vector field from samples."""
        computed = 0
        for gradient in self._gradients.values():
            if gradient.state != FieldState.SAMPLED:
                continue
            source = self._find_station_by_id(gradient.source_station_id)
            sink = self._find_station_by_id(gradient.sink_station_id)
            if source is None or sink is None:
                continue
            # Real measured differential between the two sampled potentials,
            # plus the registered baseline differential for this gradient.
            measured = abs(source.potential_mv - sink.potential_mv)
            blended = 0.5 * measured + 0.5 * gradient.voltage_mv
            gradient.voltage_mv = blended
            gradient.distance_m = self._haversine_m(
                source.latitude, source.longitude,
                sink.latitude, sink.longitude,
            )
            gradient.azimuth_deg = self._azimuth_between(
                source.latitude, source.longitude,
                sink.latitude, sink.longitude,
            )
            gradient.current_direction = self._classify_current_direction(gradient.azimuth_deg)
            gradient.current_density_ma_per_m2 = self._compute_current_density(
                blended, gradient.distance_m,
            )
            # Stability tightens as the sample window grows; we approximate it
            # from how close the measured value sits to the registered baseline.
            denom = max(abs(blended), 1.0)
            gradient.stability = max(
                0.0, min(self._MAX_STABILITY, 1.0 - abs(measured - gradient.voltage_mv) / denom),
            )
            gradient.gradient_class = self._classify_gradient_class(
                blended, gradient.stability,
            )
            gradient.state = FieldState.COMPUTED
            computed += 1
        self._update_stats(phase_runs=1)
        self._record_event("phase_compute_gradient", {"computed": computed})
        return {"phase": "compute_gradient", "computed": computed}

    def _phase_trace_contours(self) -> Dict[str, Any]:
        """Trace phase: trace iso-voltage contours across the terrain."""
        traced = 0
        # Group gradients into voltage shells by snapping to the contour step.
        shells: Dict[int, List[TelluricGradient]] = {}
        for gradient in self._gradients.values():
            if gradient.state != FieldState.COMPUTED:
                continue
            shell_index = int(gradient.voltage_mv / self._CONTOUR_STEP_MV)
            shells.setdefault(shell_index, []).append(gradient)
        for shell_index, members in shells.items():
            contour_id = (
                f"ctr_shell{shell_index}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            member_ids = [g.gradient_id for g in members]
            anchor = members[0]
            contour = {
                "contour_id": contour_id,
                "shell_index": shell_index,
                "voltage_band_mv": (
                    shell_index * self._CONTOUR_STEP_MV,
                    (shell_index + 1) * self._CONTOUR_STEP_MV,
                ),
                "member_count": len(members),
                "member_gradient_ids": member_ids,
                "anchor_gradient_id": anchor.gradient_id,
                "gradient_class": anchor.gradient_class.value,
                "color": self._color_for_gradient_class(anchor.gradient_class),
                "line_weight": 0.5 + anchor.stability * 2.0,
                "visible": True,
                "preview_url": f"/preview/telluric/{contour_id}.svg",
                "created_at": time.time(),
            }
            if len(self._contours) >= self._MAX_CONTOURS:
                oldest_key = next(iter(self._contours))
                self._contours.pop(oldest_key, None)
            self._contours[contour_id] = contour
            for gradient in members:
                gradient.contour_id = contour_id
                gradient.state = FieldState.CONTOURED
            traced += len(members)
        self._update_stats(phase_runs=1, contours_traced=len(shells))
        self._record_event("phase_trace_contours", {
            "traced": traced,
            "contours": len(shells),
        })
        return {
            "phase": "trace_contours",
            "traced": traced,
            "contours": len(shells),
        }

    def _phase_detect_anomalies(self) -> Dict[str, Any]:
        """Detect phase: flag anomalous surges betraying ore, fault, or artifact."""
        anomalies_detected = 0
        for gradient in self._gradients.values():
            if gradient.state != FieldState.CONTOURED:
                continue
            # Anomaly signal ramps up once the differential crosses the threshold.
            over_threshold = max(
                0.0, gradient.voltage_mv - self._ANOMALY_VOLTAGE_THRESHOLD,
            )
            gradient.anomaly_signal = min(
                1.0, over_threshold / self._ANOMALY_VOLTAGE_THRESHOLD,
            )
            if gradient.anomaly_signal >= 0.5 or gradient.gradient_class == GradientClass.FAULTED:
                anomaly_id = (
                    f"anm_{gradient.gradient_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                cause = self._infer_anomaly_cause(gradient)
                anomaly_entry = {
                    "anomaly_id": anomaly_id,
                    "gradient_id": gradient.gradient_id,
                    "entity_id": gradient.entity_id,
                    "voltage_mv": gradient.voltage_mv,
                    "anomaly_signal": gradient.anomaly_signal,
                    "stability": gradient.stability,
                    "gradient_class": gradient.gradient_class.value,
                    "current_direction": gradient.current_direction.value,
                    "cause": cause,
                    "created_at": time.time(),
                }
                if len(self._anomalies) >= self._MAX_ANOMALIES:
                    oldest_key = next(iter(self._anomalies))
                    self._anomalies.pop(oldest_key, None)
                self._anomalies[anomaly_id] = anomaly_entry
                anomalies_detected += 1
            gradient.state = FieldState.ANALYZED
        self._update_stats(phase_runs=1, anomalies_detected=anomalies_detected)
        self._record_event("phase_detect_anomalies", {
            "anomalies_detected": anomalies_detected,
        })
        return {
            "phase": "detect_anomalies",
            "anomalies_detected": anomalies_detected,
        }

    def _phase_emit_telluric_map(self) -> Dict[str, Any]:
        """Emit phase: emit the full telluric map with stations, gradients, contours."""
        emitted = 0
        for gradient in self._gradients.values():
            if gradient.state != FieldState.ANALYZED:
                continue
            gradient.state = FieldState.EMITTED
            emitted += 1
        # Stamp probe stations with vitality based on the gradient population.
        for station in self._stations.values():
            station.vitality = self._derive_vitality(station.station_id)
        map_size = (
            len(self._stations) + len(self._gradients)
            + len(self._contours) + len(self._anomalies)
        )
        self._update_stats(phase_runs=1, maps_emitted=1)
        self._record_event("phase_emit_telluric_map", {
            "emitted": emitted,
            "map_size": map_size,
        })
        return {
            "phase": "emit_telluric_map",
            "emitted": emitted,
            "map_size": map_size,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_station_by_id(self, station_id: str) -> Optional[ProbeStation]:
        """Find a probe station by its station_id (linear scan over handles)."""
        for station in self._stations.values():
            if station.station_id == station_id:
                return station
        return None

    def _infer_anomaly_cause(self, gradient: TelluricGradient) -> str:
        """Infer a plausible cause for an anomalous telluric gradient."""
        if gradient.gradient_class == GradientClass.FAULTED:
            return "fault_slip"
        if gradient.stability < 0.3:
            return "active_flow"
        if gradient.current_direction in (CurrentDirection.RADIAL_IN, CurrentDirection.RADIAL_OUT):
            return "buried_artifact"
        return "conductive_ore_body"

    def _derive_vitality(self, station_id: str) -> FieldVitality:
        """Derive vitality for a probe station from its gradient population."""
        gradient_count = sum(
            1 for g in self._gradients.values()
            if g.source_station_id == station_id or g.sink_station_id == station_id
        )
        faulted_count = sum(
            1 for g in self._gradients.values()
            if (g.source_station_id == station_id or g.sink_station_id == station_id)
            and g.gradient_class == GradientClass.FAULTED
        )
        if gradient_count == 0:
            return FieldVitality.DORMANT
        if faulted_count >= 2:
            return FieldVitality.CHAOTIC
        if gradient_count <= 1:
            return FieldVitality.STIRRING
        if gradient_count <= 3:
            return FieldVitality.FLOWING
        return FieldVitality.DYNAMIC

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_gradients(self) -> None:
        """Seed a few synthetic probe stations and gradients on the first cycle if empty."""
        seeds = [
            (
                "probe::aurora", "probe::basalt",
                "Aurora-Basalt Spacing", 18.0, 850.0, ProbeStationKind.SURFACE, 1.2,
                (35.6762, 139.6503), (35.6812, 139.6603),
            ),
            (
                "probe::cinder", "probe::driftwood",
                "Cinder-Driftwood Spacing", 62.0, 420.0, ProbeStationKind.BOREHOLE, 28.0,
                (40.7128, -74.0060), (40.7188, -74.0160),
            ),
            (
                "probe::ember", "probe::frost",
                "Ember-Frost Spacing", 175.0, 1500.0, ProbeStationKind.VAULT, 80.0,
                (51.5074, -0.1278), (51.5174, -0.1378),
            ),
        ]
        for source_handle, sink_handle, label, voltage_mv, distance_m, kind, depth, src_coord, sink_coord in seeds:
            self._seed_station_if_missing(source_handle, src_coord[0], src_coord[1], depth, kind)
            self._seed_station_if_missing(
                sink_handle, sink_coord[0], sink_coord[1], max(1.0, depth / 2.0), kind,
            )
            # Skip if a gradient between this pair is already registered.
            already = any(
                g.source_station_id == self._stations[source_handle].station_id
                and g.sink_station_id == self._stations[sink_handle].station_id
                for g in self._gradients.values()
            )
            if already:
                continue
            if len(self._gradients) >= self._MAX_GRADIENTS:
                break
            self.register_gradient(
                source_handle=source_handle,
                sink_handle=sink_handle,
                label=label,
                voltage_mv=voltage_mv,
                distance_m=distance_m,
                note="seeded",
            )

    def _seed_station_if_missing(
        self,
        station_handle: str,
        latitude: float,
        longitude: float,
        depth_m: float,
        kind: ProbeStationKind,
    ) -> None:
        """Seed a single probe station if it is missing."""
        if station_handle in self._stations:
            return
        if len(self._stations) >= self._MAX_STATIONS:
            return
        station_id = (
            f"sta_{station_handle}_{int(time.time() * 1000)}_"
            f"{random.randint(100, 999)}"
        )
        station = ProbeStation(
            station_id=station_id,
            station_handle=station_handle,
            label=station_handle.replace("probe::", "").replace("_", " ").title(),
            latitude=latitude,
            longitude=longitude,
            depth_m=depth_m,
            kind=kind,
            contact_resistance_ohm=100.0,
            potential_mv=0.0,
            active=True,
            vitality=FieldVitality.DORMANT,
            created_at=time.time(),
            last_sampled_at=0.0,
            note="seeded",
        )
        self._stations[station_handle] = station

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _station_to_dict(self, station: ProbeStation) -> Dict[str, Any]:
        return {
            "station_id": station.station_id,
            "station_handle": station.station_handle,
            "label": station.label,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "depth_m": station.depth_m,
            "kind": station.kind.value,
            "contact_resistance_ohm": station.contact_resistance_ohm,
            "potential_mv": station.potential_mv,
            "active": station.active,
            "vitality": station.vitality.value,
            "created_at": station.created_at,
            "last_sampled_at": station.last_sampled_at,
            "note": station.note,
        }

    def _gradient_to_dict(self, gradient: TelluricGradient) -> Dict[str, Any]:
        return {
            "gradient_id": gradient.gradient_id,
            "entity_id": gradient.entity_id,
            "source_station_id": gradient.source_station_id,
            "sink_station_id": gradient.sink_station_id,
            "label": gradient.label,
            "voltage_mv": gradient.voltage_mv,
            "distance_m": gradient.distance_m,
            "gradient_class": gradient.gradient_class.value,
            "current_direction": gradient.current_direction.value,
            "current_density_ma_per_m2": gradient.current_density_ma_per_m2,
            "azimuth_deg": gradient.azimuth_deg,
            "stability": gradient.stability,
            "anomaly_signal": gradient.anomaly_signal,
            "contour_id": gradient.contour_id,
            "state": gradient.state.value,
            "created_at": gradient.created_at,
            "last_sampled_at": gradient.last_sampled_at,
            "note": gradient.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "stations": len(self._stations),
                "gradients": len(self._gradients),
                "contours": len(self._contours),
                "anomalies": len(self._anomalies),
                "samples": len(self._samples),
                "stats": dict(self._stats),
            }

    def get_gradients(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._global_lock:
            gradients = sorted(
                self._gradients.values(),
                key=lambda g: g.created_at,
                reverse=True,
            )[:limit]
            return [self._gradient_to_dict(g) for g in gradients]

    def get_gradient(self, gradient_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT gradient_id, so we
        # MUST iterate over values and match on the gradient_id attribute.
        with self._global_lock:
            for gradient in self._gradients.values():
                if gradient.gradient_id == gradient_id:
                    return self._gradient_to_dict(gradient)
            return {
                "error": "gradient not found",
                "gradient_id": gradient_id,
            }

    def get_events_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic gradients if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._gradients:
                self._seed_synthetic_gradients()
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
            self._stations.clear()
            self._gradients.clear()
            self._contours.clear()
            self._anomalies.clear()
            self._samples.clear()
            self._phase = TelluricPhase.SAMPLE_VOLTAGE
            self._cycle_count = 0
            self._init_stats()
            # Re-seed synthetic data so the mapper never starts empty.
            self._seed_synthetic_gradients()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }

    # -------------------------------------------------------------------------
    # Domain-Specific Action
    # -------------------------------------------------------------------------

    def map_gradients(self) -> Dict[str, Any]:
        """Build and return a telluric gradient mapping report.

        The report folds the live gradient field, traced contours, and
        detected anomalies into a single payload the editor can render as
        a layered current-flow map.
        """
        with self._global_lock:
            gradients = [self._gradient_to_dict(g) for g in self._gradients.values()]
            contours = list(self._contours.values())
            anomalies = list(self._anomalies.values())
            stations = [self._station_to_dict(s) for s in self._stations.values()]
            # Voltage histogram across 8 shells for a quick visual sense.
            histogram: Dict[str, int] = {}
            for gradient in gradients:
                bucket = int(gradient["voltage_mv"] / self._CONTOUR_STEP_MV)
                histogram[str(bucket)] = histogram.get(str(bucket), 0) + 1
            # Tally gradient classes for the report header.
            class_tally: Dict[str, int] = {}
            for gradient in gradients:
                key = gradient["gradient_class"]
                class_tally[key] = class_tally.get(key, 0) + 1
            return {
                "report_id": (
                    f"map_{int(time.time() * 1000)}_{random.randint(100, 999)}"
                ),
                "cycle_count": self._cycle_count,
                "station_count": len(stations),
                "gradient_count": len(gradients),
                "contour_count": len(contours),
                "anomaly_count": len(anomalies),
                "voltage_histogram": histogram,
                "class_tally": class_tally,
                "stations": stations,
                "gradients": gradients,
                "contours": contours,
                "anomalies": anomalies,
                "generated_at": time.time(),
            }
