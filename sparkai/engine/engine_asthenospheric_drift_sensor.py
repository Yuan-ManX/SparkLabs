"""
SparkLabs Engine - Asthenospheric Drift Sensor"""

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

class AsthenosphericPhase(Enum):
    """Phases of the asthenospheric drift sensor cycle."""
    REGISTER_DRIFT = "register_drift"          # register ductile-mantle drift vectors with magnitude and azimuth
    INTEGRATE_STRAIN = "integrate_strain"      # integrate strain tensors from the registered drift vectors
    TRACK_CONVECTION = "track_convection"      # track convective-cell displacement across sensing cells
    ANALYZE_CREEP = "analyze_creep"            # analyze the creep regime per drift vector (quasi-static, steady, transient, accelerating, rupturing)
    EMIT_DRIFT_FIELD = "emit_drift_field"      # emit the full drift field with vectors, cells, and strain records for the editor


class DriftDirection(Enum):
    """Compass octant classification of a drift vector's azimuth."""
    NORTH = "north"
    NORTHEAST = "northeast"
    EAST = "east"
    SOUTHEAST = "southeast"
    SOUTH = "south"
    SOUTHWEST = "southwest"
    WEST = "west"
    NORTHWEST = "northwest"


class CreepRegime(Enum):
    """Creep regime classification for a ductile-mantle drift vector."""
    QUASI_STATIC = "quasi_static"      # slow, steady plastic flow below yield
    STEADY_CREEP = "steady_creep"      # constant-rate ductile creep
    TRANSIENT = "transient"            # time-dependent transient creep
    ACCELERATING = "accelerating"      # accelerating creep toward yield
    RUPTURING = "rupturing"            # creep has exceeded yield, rupture onset


class DriftState(Enum):
    """State of an individual drift vector through the cycle."""
    PENDING = "pending"                # registered but not yet processed
    REGISTERED = "registered"          # confirmed and classified
    INTEGRATED = "integrated"          # strain tensor integrated
    TRACKED = "tracked"                # convective-cell displacement tracked
    ANALYZED = "analyzed"              # creep regime analyzed
    EMITTED = "emitted"                # emitted into the drift field


class Vitality(Enum):
    """Overall vitality of the asthenospheric sensing ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    FLOWING = "flowing"
    DYNAMIC = "dynamic"
    CHAOTIC = "chaotic"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class DriftVector:
    """A ductile-mantle drift vector sensed at a node in the asthenosphere."""
    drift_id: str
    entity_id: str
    drift_label: str
    magnitude: float                              # cm/yr, ductile-mantle drift speed
    azimuth: float                                # radians, drift direction (0 = east, pi/2 = north)
    depth_km: float                               # sensing depth in km
    creep_rate: float = 0.0                       # per-cycle strain rate
    creep_regime: CreepRegime = CreepRegime.QUASI_STATIC
    direction: DriftDirection = DriftDirection.NORTH
    strain_xx: float = 0.0                        # normal strain component (east-east)
    strain_yy: float = 0.0                        # normal strain component (north-north)
    strain_xy: float = 0.0                        # shear strain component
    convective_cell_id: str = ""                  # sensing cell this vector belongs to
    cell_displacement: float = 0.0                # convective-cell displacement this cycle, km
    state: DriftState = DriftState.PENDING
    vitality: Vitality = Vitality.DORMANT
    created_at: float = field(default_factory=time.time)
    last_sensed_at: float = 0.0
    note: str = ""


# =============================================================================
# Sensor
# =============================================================================

class AsthenosphericDriftSensor:
    """
    Thread-safe singleton that senses ductile-mantle drift vectors within the
    asthenosphere.

    Drift vectors are keyed internally by entity_id so that each sensing node
    owns exactly one entry. The drift_id is a generated handle for external
    lookups; lookups by drift_id fall back to a linear scan of the registered
    drift vectors.

    Usage:
        sensor = AsthenosphericDriftSensor.get_instance()
        sensor.register_drift(
            entity_id="node::pacific_7",
            drift_label="Pacific Ductile Node 7",
            magnitude=6.4,
            azimuth=1.2,
            depth_km=180.0,
        )
        sensor.cycle()
        drift = sensor.get_drift(drift_id)
        report = sensor.sense_drifts()
    """

    _instance: Optional["AsthenosphericDriftSensor"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Capacity caps.
    _MAX_DRIFTS = 100
    _MAX_EVENTS = 200
    _MAX_STRAIN = 120
    _MAX_CELLS = 60
    _MAX_FIELD = 100

    # Domain tuning constants.
    _TWO_PI = 2.0 * math.pi
    _MIN_MAGNITUDE = 0.0
    _MAX_MAGNITUDE = 25.0                       # cm/yr, capped drift speed
    _MIN_DEPTH_KM = 50.0                        # top of the asthenosphere
    _MAX_DEPTH_KM = 410.0                       # bottom of the asthenosphere
    _STRAIN_SCALE = 0.02                        # base strain perturbation per cycle
    _CREEP_SCALE = 0.05                         # base creep rate perturbation per cycle
    _CONVECTION_SCALE = 0.1                     # base convective cell displacement, km
    _QUASI_STATIC_MAGNITUDE = 2.0               # below this is quasi-static creep
    _STEADY_CREEP_MAGNITUDE = 6.0               # below this is steady creep
    _TRANSIENT_MAGNITUDE = 12.0                 # below this is transient creep
    _ACCELERATING_MAGNITUDE = 18.0              # below this is accelerating creep
    _RUPTURE_STRAIN_THRESHOLD = 0.15            # shear strain above this triggers rupture

    def __init__(self) -> None:
        # Internal dict keyed by entity_id (NOT drift_id).
        self._drifts: Dict[str, DriftVector] = {}
        self._strain_records: Dict[str, Dict[str, Any]] = {}
        self._cells: Dict[str, Dict[str, Any]] = {}
        self._field: Dict[str, Dict[str, Any]] = {}
        self._phase: AsthenosphericPhase = AsthenosphericPhase.REGISTER_DRIFT
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._drifts:
            self._seed_synthetic_drifts()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AsthenosphericDriftSensor":
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
            "drifts_registered": 0,
            "phase_runs": 0,
            "strain_integrated": 0,
            "cells_tracked": 0,
            "creep_analyzed": 0,
            "fields_emitted": 0,
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
    def _parse_drift_direction(value: Any) -> DriftDirection:
        """Parse a DriftDirection from a string, enum, or None."""
        if value is None:
            return DriftDirection.NORTH
        if isinstance(value, DriftDirection):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for direction in DriftDirection:
                if direction.value == lowered:
                    return direction
        return DriftDirection.NORTH

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_drift_direction(self, azimuth: float) -> DriftDirection:
        """Classify the compass octant of a drift vector from its azimuth (radians)."""
        # Map azimuth to a compass octant. Wrap into [0, 2*pi).
        angle = azimuth % self._TWO_PI
        sector = int((angle / self._TWO_PI) * len(DriftDirection)) % len(DriftDirection)
        return list(DriftDirection)[sector]

    def _classify_creep_regime(self, magnitude: float, strain_xy: float) -> CreepRegime:
        """Classify the creep regime from drift magnitude and accumulated shear strain."""
        if strain_xy >= self._RUPTURE_STRAIN_THRESHOLD:
            return CreepRegime.RUPTURING
        if magnitude < self._QUASI_STATIC_MAGNITUDE:
            return CreepRegime.QUASI_STATIC
        if magnitude < self._STEADY_CREEP_MAGNITUDE:
            return CreepRegime.STEADY_CREEP
        if magnitude < self._TRANSIENT_MAGNITUDE:
            return CreepRegime.TRANSIENT
        if magnitude < self._ACCELERATING_MAGNITUDE:
            return CreepRegime.ACCELERATING
        return CreepRegime.RUPTURING

    def _color_for_creep_regime(self, regime: CreepRegime) -> str:
        """Map a creep regime to a preview color for the editor vector field."""
        if regime == CreepRegime.QUASI_STATIC:
            return "#4682B4"   # steel blue - slow, quasi-static creep
        if regime == CreepRegime.STEADY_CREEP:
            return "#32CD32"   # lime green - steady ductile creep
        if regime == CreepRegime.TRANSIENT:
            return "#FFD700"   # gold - transient time-dependent creep
        if regime == CreepRegime.ACCELERATING:
            return "#FF4500"   # orange-red - accelerating creep toward yield
        return "#8B0000"       # dark red - rupturing creep

    def _derive_vitality(self) -> Vitality:
        """Derive the overall vitality of the sensing ecosystem from the drift population."""
        drift_count = len(self._drifts)
        rupturing_count = sum(
            1 for d in self._drifts.values()
            if d.creep_regime == CreepRegime.RUPTURING
        )
        if drift_count == 0:
            return Vitality.DORMANT
        if rupturing_count >= 2:
            return Vitality.CHAOTIC
        if drift_count <= 1:
            return Vitality.STIRRING
        if drift_count <= 3:
            return Vitality.FLOWING
        return Vitality.DYNAMIC

    # -------------------------------------------------------------------------
    # Drift Management
    # -------------------------------------------------------------------------

    def register_drift(
        self,
        entity_id: str,
        drift_label: str,
        magnitude: float = 1.0,
        azimuth: float = 0.0,
        depth_km: float = 200.0,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new ductile-mantle drift vector at a sensing node."""
        with self._global_lock:
            if entity_id in self._drifts:
                return {"error": f"Drift already registered for entity: {entity_id}"}
            if len(self._drifts) >= self._MAX_DRIFTS:
                return {"error": f"Drift cap reached ({self._MAX_DRIFTS})"}

            drift_id = (
                f"drift_{entity_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )

            mag = max(
                self._MIN_MAGNITUDE,
                min(self._MAX_MAGNITUDE, float(magnitude)),
            )
            depth = max(
                self._MIN_DEPTH_KM,
                min(self._MAX_DEPTH_KM, float(depth_km)),
            )
            direction = self._classify_drift_direction(azimuth)
            regime = self._classify_creep_regime(mag, 0.0)

            drift = DriftVector(
                drift_id=drift_id,
                entity_id=entity_id,
                drift_label=drift_label,
                magnitude=mag,
                azimuth=azimuth,
                depth_km=depth,
                creep_rate=0.0,
                creep_regime=regime,
                direction=direction,
                strain_xx=0.0,
                strain_yy=0.0,
                strain_xy=0.0,
                convective_cell_id="",
                cell_displacement=0.0,
                state=DriftState.PENDING,
                vitality=Vitality.DORMANT,
                created_at=time.time(),
                last_sensed_at=0.0,
                note=note,
            )
            self._drifts[entity_id] = drift
            self._update_stats(drifts_registered=1)
            self._record_event("drift_registered", {
                "drift_id": drift_id,
                "entity_id": entity_id,
                "drift_label": drift_label,
                "magnitude": mag,
                "azimuth": azimuth,
                "depth_km": depth,
                "direction": direction.value,
                "creep_regime": regime.value,
            })

            return {
                "drift_id": drift_id,
                "entity_id": entity_id,
                "drift_label": drift_label,
                "magnitude": mag,
                "azimuth": azimuth,
                "depth_km": depth,
                "direction": direction.value,
                "creep_regime": regime.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single asthenospheric drift sensor cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic drifts on the very first cycle if none exist.
            if not self._drifts and self._cycle_count == 0:
                self._seed_synthetic_drifts()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = AsthenosphericPhase.REGISTER_DRIFT
            phase_outputs.append(self._phase_register_drift())
            self._phase = AsthenosphericPhase.INTEGRATE_STRAIN
            phase_outputs.append(self._phase_integrate_strain())
            self._phase = AsthenosphericPhase.TRACK_CONVECTION
            phase_outputs.append(self._phase_track_convection())
            self._phase = AsthenosphericPhase.ANALYZE_CREEP
            phase_outputs.append(self._phase_analyze_creep())
            self._phase = AsthenosphericPhase.EMIT_DRIFT_FIELD
            phase_outputs.append(self._phase_emit_drift_field())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_register_drift(self) -> Dict[str, Any]:
        """Register phase: confirm pending drift vectors and classify them."""
        registered_drifts = 0
        magnitude_sum = 0.0
        for drift in self._drifts.values():
            # Recompute direction and creep regime in case magnitude shifted.
            drift.direction = self._classify_drift_direction(drift.azimuth)
            drift.creep_regime = self._classify_creep_regime(
                drift.magnitude, drift.strain_xy,
            )
            magnitude_sum += drift.magnitude
            if drift.state == DriftState.PENDING:
                drift.state = DriftState.REGISTERED
                registered_drifts += 1
            else:
                registered_drifts += 1
        avg_magnitude = (
            magnitude_sum / registered_drifts if registered_drifts > 0 else 0.0
        )
        self._update_stats(phase_runs=1)
        self._record_event("phase_register_drift", {
            "registered_drifts": registered_drifts,
            "avg_magnitude": avg_magnitude,
        })
        return {
            "phase": "register_drift",
            "registered_drifts": registered_drifts,
            "avg_magnitude": avg_magnitude,
        }

    def _phase_integrate_strain(self) -> Dict[str, Any]:
        """Integrate phase: integrate strain tensors from the registered drift vectors."""
        strain_integrated = 0
        for drift in self._drifts.values():
            if drift.state != DriftState.REGISTERED:
                continue
            # Decompose the drift vector into east-west (x) and north-south (y).
            east_component = drift.magnitude * math.cos(drift.azimuth)
            north_component = drift.magnitude * math.sin(drift.azimuth)
            # Integrate strain as the gradient of the velocity field at depth.
            # Strain scales inversely with depth: shallower nodes deform more.
            depth_factor = self._MIN_DEPTH_KM / max(drift.depth_km, self._MIN_DEPTH_KM)
            strain_xx_delta = east_component * self._STRAIN_SCALE * depth_factor
            strain_yy_delta = north_component * self._STRAIN_SCALE * depth_factor
            strain_xy_delta = (
                0.5 * (east_component + north_component) * self._STRAIN_SCALE * depth_factor
            )
            drift.strain_xx += strain_xx_delta
            drift.strain_yy += strain_yy_delta
            drift.strain_xy += strain_xy_delta
            drift.state = DriftState.INTEGRATED

            # Record the strain entry.
            strain_id = (
                f"strain_{drift.drift_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            strain_entry = {
                "strain_id": strain_id,
                "drift_id": drift.drift_id,
                "entity_id": drift.entity_id,
                "strain_xx": drift.strain_xx,
                "strain_yy": drift.strain_yy,
                "strain_xy": drift.strain_xy,
                "strain_xx_delta": strain_xx_delta,
                "strain_yy_delta": strain_yy_delta,
                "strain_xy_delta": strain_xy_delta,
                "depth_factor": depth_factor,
                "created_at": time.time(),
            }
            # Cap the strain collection.
            if len(self._strain_records) >= self._MAX_STRAIN:
                oldest_key = next(iter(self._strain_records))
                self._strain_records.pop(oldest_key, None)
            self._strain_records[strain_id] = strain_entry
            strain_integrated += 1
        self._update_stats(phase_runs=1, strain_integrated=strain_integrated)
        self._record_event("phase_integrate_strain", {
            "strain_integrated": strain_integrated,
        })
        return {
            "phase": "integrate_strain",
            "strain_integrated": strain_integrated,
        }

    def _phase_track_convection(self) -> Dict[str, Any]:
        """Track phase: track convective-cell displacement across sensing cells."""
        cells_tracked = 0
        for drift in self._drifts.values():
            if drift.state != DriftState.INTEGRATED:
                continue
            # Assign the drift to a convective sensing cell if not yet assigned.
            if not drift.convective_cell_id:
                drift.convective_cell_id = (
                    f"cell_{drift.entity_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
            # Convective cell displacement scales with drift magnitude and
            # inversely with depth (shallower cells displace more per cycle).
            depth_factor = self._MIN_DEPTH_KM / max(drift.depth_km, self._MIN_DEPTH_KM)
            displacement = (
                drift.magnitude * self._CONVECTION_SCALE * depth_factor
            )
            drift.cell_displacement = displacement
            drift.state = DriftState.TRACKED

            # Record the convective cell entry.
            cell_entry = {
                "cell_id": drift.convective_cell_id,
                "drift_id": drift.drift_id,
                "entity_id": drift.entity_id,
                "displacement": displacement,
                "magnitude": drift.magnitude,
                "azimuth": drift.azimuth,
                "depth_km": drift.depth_km,
                "direction": drift.direction.value,
                "cycle": self._cycle_count,
                "created_at": time.time(),
            }
            # Cap the cell collection.
            if len(self._cells) >= self._MAX_CELLS:
                oldest_key = next(iter(self._cells))
                self._cells.pop(oldest_key, None)
            self._cells[drift.convective_cell_id] = cell_entry
            cells_tracked += 1
        self._update_stats(phase_runs=1, cells_tracked=cells_tracked)
        self._record_event("phase_track_convection", {
            "cells_tracked": cells_tracked,
        })
        return {
            "phase": "track_convection",
            "cells_tracked": cells_tracked,
        }

    def _phase_analyze_creep(self) -> Dict[str, Any]:
        """Analyze phase: analyze the creep regime per drift vector."""
        creep_analyzed = 0
        rupturing_count = 0
        for drift in self._drifts.values():
            if drift.state != DriftState.TRACKED:
                continue
            # Creep rate perturbs slightly each cycle.
            creep_delta = random.uniform(-self._CREEP_SCALE, self._CREEP_SCALE)
            drift.creep_rate = max(0.0, drift.creep_rate + creep_delta)
            # Reclassify the creep regime from magnitude and accumulated shear.
            drift.creep_regime = self._classify_creep_regime(
                drift.magnitude, abs(drift.strain_xy),
            )
            if drift.creep_regime == CreepRegime.RUPTURING:
                rupturing_count += 1
            drift.last_sensed_at = time.time()
            drift.state = DriftState.ANALYZED
            creep_analyzed += 1
        self._update_stats(phase_runs=1, creep_analyzed=creep_analyzed)
        self._record_event("phase_analyze_creep", {
            "creep_analyzed": creep_analyzed,
            "rupturing_count": rupturing_count,
        })
        return {
            "phase": "analyze_creep",
            "creep_analyzed": creep_analyzed,
            "rupturing_count": rupturing_count,
        }

    def _phase_emit_drift_field(self) -> Dict[str, Any]:
        """Emit phase: emit the full drift field with vectors, cells, and strain records."""
        emitted = 0
        for drift in self._drifts.values():
            if drift.state != DriftState.ANALYZED:
                continue
            drift.state = DriftState.EMITTED
            emitted += 1
        # Stamp the drift vectors with the derived vitality.
        vitality = self._derive_vitality()
        for drift in self._drifts.values():
            drift.vitality = vitality
        # Build editor field entries - one vector per drift.
        for drift in self._drifts.values():
            if drift.state != DriftState.EMITTED:
                continue
            field_id = (
                f"field_{drift.drift_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            field_entry = {
                "field_id": field_id,
                "drift_id": drift.drift_id,
                "entity_id": drift.entity_id,
                "drift_label": drift.drift_label,
                "magnitude": drift.magnitude,
                "azimuth": drift.azimuth,
                "depth_km": drift.depth_km,
                "direction": drift.direction.value,
                "creep_regime": drift.creep_regime.value,
                "creep_rate": drift.creep_rate,
                "strain_xx": drift.strain_xx,
                "strain_yy": drift.strain_yy,
                "strain_xy": drift.strain_xy,
                "convective_cell_id": drift.convective_cell_id,
                "cell_displacement": drift.cell_displacement,
                "vitality": drift.vitality.value,
                "color": self._color_for_creep_regime(drift.creep_regime),
                "vector_weight": 0.5 + (drift.magnitude / self._MAX_MAGNITUDE) * 2.0,
                "visible": True,
                "preview_url": f"/preview/asthenospheric/{field_id}.svg",
                "state": "emitted",
                "created_at": time.time(),
            }
            # Cap the field collection.
            if len(self._field) >= self._MAX_FIELD:
                oldest_key = next(iter(self._field))
                self._field.pop(oldest_key, None)
            self._field[field_id] = field_entry
        field_size = (
            len(self._drifts) + len(self._strain_records)
            + len(self._cells) + len(self._field)
        )
        self._update_stats(phase_runs=1, fields_emitted=1)
        self._record_event("phase_emit_drift_field", {
            "emitted": emitted,
            "field_size": field_size,
            "vitality": vitality.value,
        })
        return {
            "phase": "emit_drift_field",
            "emitted": emitted,
            "field_size": field_size,
            "vitality": vitality.value,
        }

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_drifts(self) -> None:
        """Seed a few synthetic ductile-mantle drift vectors on the first cycle if empty."""
        seeds = [
            (
                "node::pacific_7",
                "Pacific Ductile Node 7",
                6.4,
                1.2,
                180.0,
            ),
            (
                "node::atlantic_3",
                "Atlantic Ductile Node 3",
                2.1,
                0.4,
                240.0,
            ),
            (
                "node::african_5",
                "African Ductile Node 5",
                14.8,
                2.7,
                150.0,
            ),
            (
                "node::antarctic_2",
                "Antarctic Ductile Node 2",
                0.9,
                3.5,
                320.0,
            ),
        ]
        for entity_id, drift_label, magnitude, azimuth, depth_km in seeds:
            if entity_id in self._drifts:
                continue
            if len(self._drifts) >= self._MAX_DRIFTS:
                break
            self.register_drift(
                entity_id=entity_id,
                drift_label=drift_label,
                magnitude=magnitude,
                azimuth=azimuth,
                depth_km=depth_km,
                note="seeded",
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _drift_to_dict(self, drift: DriftVector) -> Dict[str, Any]:
        return {
            "drift_id": drift.drift_id,
            "entity_id": drift.entity_id,
            "drift_label": drift.drift_label,
            "magnitude": drift.magnitude,
            "azimuth": drift.azimuth,
            "depth_km": drift.depth_km,
            "creep_rate": drift.creep_rate,
            "creep_regime": drift.creep_regime.value,
            "direction": drift.direction.value,
            "strain_xx": drift.strain_xx,
            "strain_yy": drift.strain_yy,
            "strain_xy": drift.strain_xy,
            "convective_cell_id": drift.convective_cell_id,
            "cell_displacement": drift.cell_displacement,
            "state": drift.state.value,
            "vitality": drift.vitality.value,
            "created_at": drift.created_at,
            "last_sensed_at": drift.last_sensed_at,
            "note": drift.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "drifts": len(self._drifts),
                "strain_records": len(self._strain_records),
                "cells": len(self._cells),
                "field": len(self._field),
                "stats": dict(self._stats),
            }

    def get_drifts(self, limit: int = 10) -> Dict[str, Any]:
        """Return a count + list of drift vectors (newest first)."""
        with self._global_lock:
            drifts = sorted(
                self._drifts.values(),
                key=lambda d: d.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(self._drifts),
                "drifts": [self._drift_to_dict(d) for d in drifts],
            }

    def get_drift(self, drift_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT drift_id, so we MUST
        # iterate over values and match on the drift_id attribute.
        with self._global_lock:
            for drift in self._drifts.values():
                if drift.drift_id == drift_id:
                    return self._drift_to_dict(drift)
            return {
                "error": "drift not found",
                "drift_id": drift_id,
            }

    def get_events_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_drift_field(self) -> Dict[str, Any]:
        """Return the full drift field with drifts, strain records, cells, and field entries."""
        with self._global_lock:
            return {
                "drifts": [self._drift_to_dict(d) for d in self._drifts.values()],
                "strain_records": list(self._strain_records.values()),
                "cells": list(self._cells.values()),
                "field": list(self._field.values()),
                "drift_count": len(self._drifts),
                "strain_count": len(self._strain_records),
                "cell_count": len(self._cells),
                "field_count": len(self._field),
                "cycle_count": self._cycle_count,
            }

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic drifts if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._drifts:
                self._seed_synthetic_drifts()
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
            self._drifts.clear()
            self._strain_records.clear()
            self._cells.clear()
            self._field.clear()
            self._phase = AsthenosphericPhase.REGISTER_DRIFT
            self._cycle_count = 0
            self._init_stats()
            # Re-seed synthetic drifts so cycles produce meaningful output
            # immediately after a reset.
            if not self._drifts:
                self._seed_synthetic_drifts()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }

    # -------------------------------------------------------------------------
    # Domain-Specific Action
    # -------------------------------------------------------------------------

    def sense_drifts(self) -> Dict[str, Any]:
        """Run a sensing pass over the drift field and return a sensing report.

        The report summarizes the current drift population, the dominant
        creep regime, the average magnitude, the rupturing drift count, and
        the vitality of the sensing ecosystem. It does not advance the
        cycle; it only reads the current state.
        """
        with self._global_lock:
            drift_count = len(self._drifts)
            if drift_count == 0:
                return {
                    "sensed": False,
                    "reason": "no drifts registered",
                    "cycle_count": self._cycle_count,
                }
            magnitudes = [d.magnitude for d in self._drifts.values()]
            avg_magnitude = sum(magnitudes) / drift_count
            max_magnitude = max(magnitudes)
            min_magnitude = min(magnitudes)
            # Tally creep regimes across the drift population.
            regime_counts: Dict[str, int] = {}
            for drift in self._drifts.values():
                regime_counts[drift.creep_regime.value] = (
                    regime_counts.get(drift.creep_regime.value, 0) + 1
                )
            # Determine the dominant creep regime.
            dominant_regime = (
                max(regime_counts.items(), key=lambda item: item[1])[0]
                if regime_counts else "unknown"
            )
            rupturing_count = regime_counts.get(CreepRegime.RUPTURING.value, 0)
            vitality = self._derive_vitality()
            # Sum convective cell displacements across the field.
            total_displacement = sum(
                d.cell_displacement for d in self._drifts.values()
            )
            self._record_event("sense_drifts", {
                "drift_count": drift_count,
                "avg_magnitude": avg_magnitude,
                "dominant_regime": dominant_regime,
                "rupturing_count": rupturing_count,
                "vitality": vitality.value,
            })
            return {
                "sensed": True,
                "drift_count": drift_count,
                "avg_magnitude": avg_magnitude,
                "max_magnitude": max_magnitude,
                "min_magnitude": min_magnitude,
                "regime_counts": regime_counts,
                "dominant_regime": dominant_regime,
                "rupturing_count": rupturing_count,
                "total_cell_displacement": total_displacement,
                "vitality": vitality.value,
                "cycle_count": self._cycle_count,
            }
