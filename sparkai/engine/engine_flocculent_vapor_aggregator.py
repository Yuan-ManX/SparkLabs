"""
SparkLabs Engine - Flocculent Vapor Aggregator"""

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

class VaporPhase(Enum):
    """Phases of the flocculent vapor aggregator cycle."""
    REGISTER_VAPOR_CLUSTER = "register_vapor_cluster"          # register flocculent vapor clusters with their sensors and initial masses
    SAMPLE_VAPOR_MASS = "sample_vapor_mass"                    # sample each cluster's vapor mass for this cycle, update vapor regime
    AGGREGATE_FLOCCULENT_DENSITY = "aggregate_flocculent_density"  # aggregate clustered vapor density between neighboring clusters
    REGULATE_VAPOR_PRESSURE = "regulate_vapor_pressure"        # regulate vapor pressure to stay within the safe saturation envelope
    EMIT_CLUSTER_MAP = "emit_cluster_map"                      # emit the full cluster map with vapors, densities, and dispersion budgets


class VaporClusterKind(Enum):
    """The kind of flocculent vapor cluster being aggregated."""
    CIRRUS = "cirrus"          # wispy high-altitude flocculent vapor
    CUMULUS = "cumulus"        # heaped clustered vapor mass
    STRATUS = "stratus"        # layered sheet vapor
    NIMBUS = "nimbus"          # saturated precipitating vapor


class VaporPhaseState(Enum):
    """The thermodynamic phase state of a vapor cluster."""
    GASEOUS = "gaseous"        # fully gaseous vapor
    MIST = "mist"              # suspended droplet mist
    SATURATED = "saturated"    # at saturation threshold
    SUPERCOOLED = "supercooled"  # below dew point, unstable


class AggregationState(Enum):
    """The aggregation state of a vapor cluster's density."""
    PASSIVE = "passive"        # no active aggregation
    COLLECTING = "collecting"  # collecting neighboring vapor mass
    COMPACTING = "compacting"  # compacting into a denser cluster
    DENSIFIED = "densified"    # densified to maximum aggregation


class ClusterState(Enum):
    """State of an individual vapor cluster through the cycle."""
    PENDING = "pending"        # registered but not yet processed
    REGISTERED = "registered"  # confirmed and classified
    SAMPLED = "sampled"        # vapor mass sampled this cycle
    AGGREGATED = "aggregated"  # flocculent density aggregated
    REGULATED = "regulated"    # vapor pressure regulated
    EMITTED = "emitted"        # emitted into the cluster map


class Vitality(Enum):
    """Overall vitality of the flocculent vapor ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    FLOWING = "flowing"
    DYNAMIC = "dynamic"
    CHAOTIC = "chaotic"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Vapor:
    """A flocculent vapor cluster aggregated by the vapor aggregator."""
    entity_id: str
    vapor_id: str
    vapor_label: str
    vapor_mass: float                              # kg of vapor in the cluster
    cluster_density: float                         # kg/m^3
    saturation_ratio: float                        # 0.0 to 1.0
    cluster_altitude: float                        # meters above datum
    vapor_pressure: float                          # Pa above baseline
    dispersion_rate: float                         # m/s
    vapor_cluster_kind: VaporClusterKind = VaporClusterKind.CUMULUS
    vapor_phase: VaporPhaseState = VaporPhaseState.GASEOUS
    aggregation_state: AggregationState = AggregationState.PASSIVE
    vitality: Vitality = Vitality.DORMANT
    density_balance: float = 0.0                   # net density imbalance, kg/m^3
    safe_density_floor: float = 0.05               # minimum safe density, kg/m^3
    safe_density_ceiling: float = 1.20             # maximum safe density, kg/m^3
    state: ClusterState = ClusterState.PENDING
    created_at: float = field(default_factory=time.time)
    last_sampled_at: float = 0.0
    note: str = ""


# =============================================================================
# Aggregator
# =============================================================================

class FlocculentVaporAggregator:
    """
    Thread-safe singleton that aggregates flocculent vapor cloud clusters.

    Vapor clusters are keyed internally by entity_id so each logical cluster
    owns exactly one entry. The vapor_id is a generated handle for external
    lookups; lookups by vapor_id fall back to a linear scan of the
    registered vapors.

    Usage:
        aggregator = FlocculentVaporAggregator.get_instance()
        aggregator.register_vapor(
            entity_id="vapor::alpha",
            vapor_label="Alpha Cumulus Cluster",
            vapor_mass=12.5,
        )
        aggregator.cycle()
        vapor = aggregator.get_vapor(vapor_id)
        cluster_map = aggregator.build_vapor_cluster_map()
    """

    _instance: Optional["FlocculentVaporAggregator"] = None
    _instance_lock = threading.Lock()

    # Capacity caps.
    _MAX_VAPORS = 200
    _MAX_EVENTS = 200
    _MAX_DENSITY_LOGS = 200
    _MAX_REGULATION_LOGS = 200
    _MAX_MAPS = 120

    # Domain tuning constants.
    _MASS_FLUCTUATION = 0.4              # base vapor mass fluctuation magnitude, kg
    _DENSITY_TOLERANCE = 0.03            # below this density imbalance is balanced
    _SAFE_DENSITY_FLOOR_DEFAULT = 0.05   # default minimum safe density, kg/m^3
    _SAFE_DENSITY_CEILING_DEFAULT = 1.20  # default maximum safe density, kg/m^3
    _SATURATION_THRESHOLD = 0.7          # saturation ratio above which vapor is saturated
    _OVERDENSE_DENSITY = 1.0             # density above which cluster is overdense
    _DEPLETED_DENSITY = 0.1              # density below which cluster is depleted
    _DISPERSION_THROTTLE_FACTOR = 0.7    # throttle factor for collecting dispersion
    _DISPERSION_CAP_FACTOR = 0.3         # cap factor for overdense dispersion
    _MIN_CLUSTER_DENSITY = 1e-4
    _MAX_CLUSTER_DENSITY = 5.0

    def __init__(self) -> None:
        # Instance-level reentrant lock for thread-safe operation.
        self._global_lock = threading.RLock()
        # Internal dict keyed by entity_id (NOT vapor_id).
        self._vapors: Dict[str, Vapor] = {}
        self._density_logs: Dict[str, Dict[str, Any]] = {}
        self._regulation_logs: Dict[str, Dict[str, Any]] = {}
        self._cluster_maps: Dict[str, Dict[str, Any]] = {}
        self._phase: VaporPhase = VaporPhase.REGISTER_VAPOR_CLUSTER
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._vapors:
            self._seed_synthetic_vapors()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "FlocculentVaporAggregator":
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
            "vapors_registered": 0,
            "phase_runs": 0,
            "masses_sampled": 0,
            "densities_aggregated": 0,
            "overdense_cells": 0,
            "pressures_regulated": 0,
            "pressures_capped": 0,
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
    def _parse_vapor_cluster_kind(value: Any) -> VaporClusterKind:
        """Parse a VaporClusterKind from a string, enum, or None."""
        if value is None:
            return VaporClusterKind.CUMULUS
        if isinstance(value, VaporClusterKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in VaporClusterKind:
                if kind.value == lowered:
                    return kind
        return VaporClusterKind.CUMULUS

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_vapor_phase(self, density: float, saturation: float) -> VaporPhaseState:
        """Classify the thermodynamic vapor phase from density and saturation ratio."""
        if density >= self._OVERDENSE_DENSITY and saturation >= self._SATURATION_THRESHOLD:
            return VaporPhaseState.SUPERCOOLED
        if saturation >= self._SATURATION_THRESHOLD:
            return VaporPhaseState.SATURATED
        if density <= self._DEPLETED_DENSITY:
            return VaporPhaseState.GASEOUS
        return VaporPhaseState.MIST

    def _classify_aggregation_state(self, density: float, dispersion_rate: float) -> AggregationState:
        """Classify the aggregation state from density and current dispersion rate."""
        if dispersion_rate <= 0.0:
            return AggregationState.PASSIVE
        if density >= self._OVERDENSE_DENSITY:
            return AggregationState.DENSIFIED
        if density >= self._SATURATION_THRESHOLD * 0.5:
            return AggregationState.COMPACTING
        return AggregationState.COLLECTING

    def _derive_vitality(self, vapor_id: str) -> Vitality:
        """Derive vitality for a vapor cluster from its post-regulation state."""
        vapor = self._find_vapor_by_id(vapor_id)
        if vapor is None:
            return Vitality.DORMANT
        overdense = abs(vapor.density_balance) > self._DENSITY_TOLERANCE * 5.0
        if vapor.vapor_phase == VaporPhaseState.SUPERCOOLED and overdense:
            return Vitality.CHAOTIC
        if vapor.aggregation_state == AggregationState.COLLECTING:
            return Vitality.FLOWING
        if vapor.vapor_phase == VaporPhaseState.SATURATED:
            return Vitality.DYNAMIC
        if vapor.state in (ClusterState.REGISTERED, ClusterState.SAMPLED):
            return Vitality.STIRRING
        return Vitality.DORMANT

    def _color_for_phase(self, phase: VaporPhaseState) -> str:
        """Map a vapor phase to a preview color for the editor cluster map."""
        if phase == VaporPhaseState.GASEOUS:
            return "#87CEEB"  # sky blue - calm gaseous vapor
        if phase == VaporPhaseState.MIST:
            return "#B0C4DE"  # light steel blue - drifting mist
        if phase == VaporPhaseState.SATURATED:
            return "#4682B4"  # steel blue - saturated vapor
        return "#2F4F4F"      # dark slate gray - supercooled vapor

    # -------------------------------------------------------------------------
    # Vapor Management
    # -------------------------------------------------------------------------

    def register_vapor(
        self,
        entity_id: str,
        vapor_label: str,
        vapor_mass: float = 8.0,
        cluster_density: float = 0.4,
        saturation_ratio: float = 0.4,
        cluster_altitude: float = 1000.0,
        vapor_pressure: float = 0.0,
        dispersion_rate: float = 0.0,
        vapor_cluster_kind: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new flocculent vapor cluster with the aggregator."""
        with self._global_lock:
            if entity_id in self._vapors:
                return {"error": f"Vapor already registered: {entity_id}"}
            if len(self._vapors) >= self._MAX_VAPORS:
                return {"error": f"Vapor cap reached ({self._MAX_VAPORS})"}

            vapor_id = (
                f"vapor_{entity_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )

            density = max(
                self._MIN_CLUSTER_DENSITY,
                min(self._MAX_CLUSTER_DENSITY, float(cluster_density)),
            )
            parsed_kind = self._parse_vapor_cluster_kind(vapor_cluster_kind)
            saturation = max(0.0, min(1.0, float(saturation_ratio)))
            phase = self._classify_vapor_phase(density, saturation)
            dispersion = max(0.0, float(dispersion_rate))
            agg_state = self._classify_aggregation_state(density, dispersion)

            vapor = Vapor(
                entity_id=entity_id,
                vapor_id=vapor_id,
                vapor_label=vapor_label,
                vapor_mass=float(vapor_mass),
                cluster_density=density,
                saturation_ratio=saturation,
                cluster_altitude=float(cluster_altitude),
                vapor_pressure=float(vapor_pressure),
                dispersion_rate=dispersion,
                vapor_cluster_kind=parsed_kind,
                vapor_phase=phase,
                aggregation_state=agg_state,
                vitality=Vitality.DORMANT,
                density_balance=0.0,
                safe_density_floor=self._SAFE_DENSITY_FLOOR_DEFAULT,
                safe_density_ceiling=self._SAFE_DENSITY_CEILING_DEFAULT,
                state=ClusterState.PENDING,
                created_at=time.time(),
                last_sampled_at=0.0,
                note=note,
            )
            self._vapors[entity_id] = vapor
            self._update_stats(vapors_registered=1)
            self._record_event("vapor_registered", {
                "vapor_id": vapor_id,
                "entity_id": entity_id,
                "vapor_label": vapor_label,
                "vapor_mass": vapor.vapor_mass,
                "vapor_cluster_kind": parsed_kind.value,
                "vapor_phase": phase.value,
            })

            return {
                "vapor_id": vapor_id,
                "entity_id": entity_id,
                "vapor_label": vapor_label,
                "vapor_mass": vapor.vapor_mass,
                "vapor_cluster_kind": parsed_kind.value,
                "vapor_phase": phase.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single flocculent vapor aggregator cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic vapors on the very first cycle if none exist.
            if not self._vapors and self._cycle_count == 0:
                self._seed_synthetic_vapors()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = VaporPhase.REGISTER_VAPOR_CLUSTER
            phase_outputs.append(self._phase_register_vapor_cluster())
            self._phase = VaporPhase.SAMPLE_VAPOR_MASS
            phase_outputs.append(self._phase_sample_vapor_mass())
            self._phase = VaporPhase.AGGREGATE_FLOCCULENT_DENSITY
            phase_outputs.append(self._phase_aggregate_flocculent_density())
            self._phase = VaporPhase.REGULATE_VAPOR_PRESSURE
            phase_outputs.append(self._phase_regulate_vapor_pressure())
            self._phase = VaporPhase.EMIT_CLUSTER_MAP
            phase_outputs.append(self._phase_emit_cluster_map())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_register_vapor_cluster(self) -> Dict[str, Any]:
        """Register phase: confirm pending vapor clusters and their sensors."""
        registered = 0
        mass_sum = 0.0
        for vapor in self._vapors.values():
            if vapor.state == ClusterState.PENDING:
                vapor.state = ClusterState.REGISTERED
                registered += 1
            # Refresh vapor phase classification in case density was set externally.
            vapor.vapor_phase = self._classify_vapor_phase(
                vapor.cluster_density, vapor.saturation_ratio,
            )
            mass_sum += vapor.vapor_mass
        avg_mass = (mass_sum / len(self._vapors)) if self._vapors else 0.0
        self._update_stats(phase_runs=1)
        self._record_event("phase_register_vapor_cluster", {
            "registered": registered,
            "avg_mass": avg_mass,
        })
        return {
            "phase": "register_vapor_cluster",
            "registered": registered,
            "avg_mass": avg_mass,
        }

    def _phase_sample_vapor_mass(self) -> Dict[str, Any]:
        """Sample phase: sample each cluster's vapor mass for this cycle."""
        sampled = 0
        for vapor in self._vapors.values():
            if vapor.state != ClusterState.REGISTERED:
                continue
            # Apply a small stochastic fluctuation to the vapor mass.
            fluctuation = random.uniform(
                -self._MASS_FLUCTUATION, self._MASS_FLUCTUATION,
            )
            vapor.vapor_mass = max(0.0, vapor.vapor_mass + fluctuation)
            # Density drifts slightly with mass, clamped to physical bounds.
            drift = fluctuation * 0.01
            vapor.cluster_density = max(
                self._MIN_CLUSTER_DENSITY,
                min(self._MAX_CLUSTER_DENSITY, vapor.cluster_density + drift),
            )
            vapor.vapor_phase = self._classify_vapor_phase(
                vapor.cluster_density, vapor.saturation_ratio,
            )
            vapor.last_sampled_at = time.time()
            vapor.state = ClusterState.SAMPLED
            sampled += 1
        self._update_stats(phase_runs=1, masses_sampled=sampled)
        self._record_event("phase_sample_vapor_mass", {"sampled": sampled})
        return {"phase": "sample_vapor_mass", "sampled": sampled}

    def _phase_aggregate_flocculent_density(self) -> Dict[str, Any]:
        """Aggregate phase: aggregate clustered vapor density between clusters."""
        aggregated = 0
        overdense = 0
        vapors = list(self._vapors.values())
        for i, vapor in enumerate(vapors):
            if vapor.state != ClusterState.SAMPLED:
                continue
            # Compare this cluster's density against the average of the others.
            if len(vapors) <= 1:
                vapor.density_balance = 0.0
            else:
                others = [v for j, v in enumerate(vapors) if j != i]
                avg_other = sum(v.cluster_density for v in others) / len(others)
                # Density imbalance normalized by an assumed inter-cluster distance.
                distance = max(vapor.cluster_altitude, 1.0) / 1000.0
                vapor.density_balance = (
                    vapor.cluster_density - avg_other
                ) / max(distance, 0.001)
            if abs(vapor.density_balance) <= self._DENSITY_TOLERANCE:
                aggregated += 1
            else:
                overdense += 1
                # Record the density imbalance entry.
                log_id = (
                    f"density_{vapor.vapor_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "density_log_id": log_id,
                    "vapor_id": vapor.vapor_id,
                    "entity_id": vapor.entity_id,
                    "density_balance": vapor.density_balance,
                    "cluster_density": vapor.cluster_density,
                    "kind": "overdense",
                    "created_at": time.time(),
                }
                # Cap the density log collection.
                if len(self._density_logs) >= self._MAX_DENSITY_LOGS:
                    oldest_key = next(iter(self._density_logs))
                    self._density_logs.pop(oldest_key, None)
                self._density_logs[log_id] = log_entry
            vapor.state = ClusterState.AGGREGATED
        self._update_stats(
            phase_runs=1,
            densities_aggregated=aggregated,
            overdense_cells=overdense,
        )
        self._record_event("phase_aggregate_flocculent_density", {
            "aggregated": aggregated,
            "overdense": overdense,
        })
        return {
            "phase": "aggregate_flocculent_density",
            "aggregated": aggregated,
            "overdense": overdense,
        }

    def _phase_regulate_vapor_pressure(self) -> Dict[str, Any]:
        """Regulate phase: regulate vapor pressure within the safe envelope."""
        regulated = 0
        capped = 0
        for vapor in self._vapors.values():
            if vapor.state != ClusterState.AGGREGATED:
                continue
            density = vapor.cluster_density
            # Clamp the density to the safe envelope.
            if density > vapor.safe_density_ceiling:
                vapor.cluster_density = vapor.safe_density_ceiling
                density = vapor.safe_density_ceiling
            elif density < vapor.safe_density_floor:
                vapor.cluster_density = vapor.safe_density_floor
                density = vapor.safe_density_floor
            # Re-classify after clamping.
            vapor.vapor_phase = self._classify_vapor_phase(
                density, vapor.saturation_ratio,
            )
            # Regulate dispersion based on the clamped density.
            if vapor.dispersion_rate > 0.0:
                if density >= self._OVERDENSE_DENSITY:
                    vapor.dispersion_rate *= self._DISPERSION_CAP_FACTOR
                    vapor.aggregation_state = AggregationState.DENSIFIED
                    capped += 1
                elif density >= self._SATURATION_THRESHOLD * 0.5:
                    vapor.dispersion_rate *= self._DISPERSION_THROTTLE_FACTOR
                    vapor.aggregation_state = AggregationState.COMPACTING
                else:
                    vapor.aggregation_state = AggregationState.COLLECTING
                regulated += 1
                # Record the regulation log.
                log_id = (
                    f"reg_{vapor.vapor_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "regulation_id": log_id,
                    "vapor_id": vapor.vapor_id,
                    "entity_id": vapor.entity_id,
                    "cluster_density": density,
                    "dispersion_rate": vapor.dispersion_rate,
                    "aggregation_state": vapor.aggregation_state.value,
                    "created_at": time.time(),
                }
                # Cap the regulation log collection.
                if len(self._regulation_logs) >= self._MAX_REGULATION_LOGS:
                    oldest_key = next(iter(self._regulation_logs))
                    self._regulation_logs.pop(oldest_key, None)
                self._regulation_logs[log_id] = log_entry
            else:
                vapor.aggregation_state = AggregationState.PASSIVE
            # Vapor pressure tracks density within the envelope.
            vapor.vapor_pressure = density * 1000.0
            vapor.state = ClusterState.REGULATED
        self._update_stats(
            phase_runs=1,
            pressures_regulated=regulated,
            pressures_capped=capped,
        )
        self._record_event("phase_regulate_vapor_pressure", {
            "regulated": regulated,
            "capped": capped,
        })
        return {
            "phase": "regulate_vapor_pressure",
            "regulated": regulated,
            "capped": capped,
        }

    def _phase_emit_cluster_map(self) -> Dict[str, Any]:
        """Emit phase: emit the full cluster map with vapors, densities, logs."""
        emitted = 0
        for vapor in self._vapors.values():
            if vapor.state != ClusterState.REGULATED:
                continue
            vapor.state = ClusterState.EMITTED
            emitted += 1
        # Stamp vitality based on the post-regulation state.
        for vapor in self._vapors.values():
            vapor.vitality = self._derive_vitality(vapor.vapor_id)
        # Build the consolidated cluster map entry.
        map_id = (
            f"map_{int(time.time() * 1000)}_{random.randint(100, 999)}"
        )
        cluster_map = {
            "map_id": map_id,
            "cycle_count": self._cycle_count,
            "vapor_count": len(self._vapors),
            "density_log_count": len(self._density_logs),
            "regulation_log_count": len(self._regulation_logs),
            "vapors": [self._vapor_to_dict(v) for v in self._vapors.values()],
            "density_logs": list(self._density_logs.values()),
            "regulation_logs": list(self._regulation_logs.values()),
            "created_at": time.time(),
        }
        # Cap the cluster map collection.
        if len(self._cluster_maps) >= self._MAX_MAPS:
            oldest_key = next(iter(self._cluster_maps))
            self._cluster_maps.pop(oldest_key, None)
        self._cluster_maps[map_id] = cluster_map
        self._update_stats(phase_runs=1, maps_emitted=1)
        self._record_event("phase_emit_cluster_map", {
            "emitted": emitted,
            "map_id": map_id,
        })
        return {
            "phase": "emit_cluster_map",
            "emitted": emitted,
            "map_id": map_id,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_vapor_by_id(self, vapor_id: str) -> Optional[Vapor]:
        """Find a vapor by its vapor_id (linear scan over entity_id keys)."""
        for vapor in self._vapors.values():
            if vapor.vapor_id == vapor_id:
                return vapor
        return None

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_vapors(self) -> None:
        """Seed a few synthetic flocculent vapor clusters on the first cycle if empty."""
        seeds = [
            ("vapor::alpha", "Alpha Cumulus Cluster", 12.5, 0.45, VaporClusterKind.CUMULUS, 0.04),
            ("vapor::bravo", "Bravo Nimbus Cluster", 18.0, 0.85, VaporClusterKind.NIMBUS, 0.06),
            ("vapor::charlie", "Charlie Cirrus Cluster", 6.0, 0.18, VaporClusterKind.CIRRUS, 0.0),
        ]
        for entity_id, label, mass, density, kind, dispersion in seeds:
            if entity_id in self._vapors:
                continue
            if len(self._vapors) >= self._MAX_VAPORS:
                break
            self.register_vapor(
                entity_id=entity_id,
                vapor_label=label,
                vapor_mass=mass,
                cluster_density=density,
                saturation_ratio=0.4,
                cluster_altitude=1200.0,
                vapor_pressure=0.0,
                dispersion_rate=dispersion,
                vapor_cluster_kind=kind.value,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _vapor_to_dict(self, vapor: Vapor) -> Dict[str, Any]:
        return {
            "entity_id": vapor.entity_id,
            "vapor_id": vapor.vapor_id,
            "vapor_label": vapor.vapor_label,
            "vapor_mass": vapor.vapor_mass,
            "cluster_density": vapor.cluster_density,
            "saturation_ratio": vapor.saturation_ratio,
            "cluster_altitude": vapor.cluster_altitude,
            "vapor_pressure": vapor.vapor_pressure,
            "dispersion_rate": vapor.dispersion_rate,
            "vapor_cluster_kind": vapor.vapor_cluster_kind.value,
            "vapor_phase": vapor.vapor_phase.value,
            "aggregation_state": vapor.aggregation_state.value,
            "vitality": vapor.vitality.value,
            "density_balance": vapor.density_balance,
            "safe_density_floor": vapor.safe_density_floor,
            "safe_density_ceiling": vapor.safe_density_ceiling,
            "state": vapor.state.value,
            "created_at": vapor.created_at,
            "last_sampled_at": vapor.last_sampled_at,
            "note": vapor.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "vapors": len(self._vapors),
                "density_logs": len(self._density_logs),
                "regulation_logs": len(self._regulation_logs),
                "cluster_maps": len(self._cluster_maps),
                "stats": dict(self._stats),
            }

    def get_vapors(self, limit: int = 10) -> Dict[str, Any]:
        with self._global_lock:
            vapors = sorted(
                self._vapors.values(),
                key=lambda v: v.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(vapors),
                "vapors": [
                    {
                        "vapor_id": v.vapor_id,
                        "entity_id": v.entity_id,
                        "vapor_label": v.vapor_label,
                        "vapor_mass": v.vapor_mass,
                        "vapor_cluster_kind": v.vapor_cluster_kind.value,
                        "vapor_phase": v.vapor_phase.value,
                        "aggregation_state": v.aggregation_state.value,
                        "vitality": v.vitality.value,
                    }
                    for v in vapors
                ],
            }

    def get_vapor(self, vapor_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT vapor_id, so we
        # MUST iterate over values and match on the vapor_id attribute.
        with self._global_lock:
            for vapor in self._vapors.values():
                if vapor.vapor_id == vapor_id:
                    return self._vapor_to_dict(vapor)
            return {
                "error": "vapor not found",
                "vapor_id": vapor_id,
            }

    def get_events_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic vapors if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._vapors:
                self._seed_synthetic_vapors()
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
            self._vapors.clear()
            self._density_logs.clear()
            self._regulation_logs.clear()
            self._cluster_maps.clear()
            self._phase = VaporPhase.REGISTER_VAPOR_CLUSTER
            self._cycle_count = 0
            self._init_stats()
            # Re-seed synthetic data so cycles produce meaningful output.
            if not self._vapors:
                self._seed_synthetic_vapors()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }

    # -------------------------------------------------------------------------
    # Domain-Specific Aggregation
    # -------------------------------------------------------------------------

    def build_vapor_cluster_map(self) -> Dict[str, Any]:
        """Build a vapor cluster map: run an aggregation pass and return the map.

        Computes the current vapor phase distribution, the density imbalance
        summary, and the dispersion budget without advancing the cycle
        counter.
        """
        with self._global_lock:
            vapors = list(self._vapors.values())
            if not vapors:
                return {
                    "aggregated": 0,
                    "phase_distribution": {},
                    "dispersion_budget": 0.0,
                    "overdense_count": 0,
                    "cluster_map": "no vapors registered",
                }
            phase_counts: Dict[str, int] = {}
            total_dispersion = 0.0
            overdense = 0
            for vapor in vapors:
                phase = self._classify_vapor_phase(
                    vapor.cluster_density, vapor.saturation_ratio,
                )
                phase_counts[phase.value] = phase_counts.get(phase.value, 0) + 1
                total_dispersion += vapor.dispersion_rate
                if abs(vapor.density_balance) > self._DENSITY_TOLERANCE:
                    overdense += 1
            return {
                "aggregated": len(vapors),
                "phase_distribution": phase_counts,
                "dispersion_budget": total_dispersion,
                "overdense_count": overdense,
                "cycle_count": self._cycle_count,
                "cluster_map": "aggregation pass complete",
            }
