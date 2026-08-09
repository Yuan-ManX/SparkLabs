"""
SparkLabs Engine - Pyroclastic Flow Choreographer"""

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

class ChoreographyPhase(Enum):
    """Phases of the pyroclastic flow choreography cycle."""
    STAGE_ASH_COLUMN = "stage_ash_column"              # stage ash columns from mass flux and buoyancy; mark collapse candidates
    PLAN_LAVA_BOMB_ARCS = "plan_lava_bomb_arcs"        # plan ballistic lava-bomb arcs: launch angle, muzzle velocity, apex, range
    ROUTE_SURGE_CURRENTS = "route_surge_currents"      # route pyroclastic density currents downhill: runout, velocity, class
    RECONCILE_TRAJECTORIES = "reconcile_trajectories"  # reconcile intersecting trajectories; detect collisions and merging
    EMIT_CHOREOGRAPHY = "emit_choreography"            # emit the full choreography map with staged flows, arcs, routes, timing


class FlowKind(Enum):
    """The kind of pyroclastic fragment flow being choreographed."""
    ASH_COLUMN = "ash_column"        # buoyant vertical ash plume
    LAVA_BOMB = "lava_bomb"          # ballistic projectile
    SURGE_CURRENT = "surge_current"  # turbulent dilute density current
    BLOCK_CLAST = "block_clast"      # larger ballistic block


class TrajectoryState(Enum):
    """State of an individual fragment-flow trajectory through the cycle."""
    PENDING = "pending"        # registered but not yet processed
    STAGED = "staged"          # ash column staged (height computed)
    PLANNED = "planned"        # ballistic arc planned
    ROUTED = "routed"          # surge current routed downhill
    RECONCILED = "reconciled"  # intersections reconciled
    EMITTED = "emitted"        # emitted into the choreography


class SurgeClass(Enum):
    """Classification of a pyroclastic surge current by concentration and runout."""
    DILUTE = "dilute"              # turbulent, low particle concentration, long runout
    TRANSITIONAL = "transitional"  # between dilute and concentrated
    CONCENTRATED = "concentrated"  # dense, high particle concentration, short runout


class Vitality(Enum):
    """Overall vitality of the volcanic choreography ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    ERUPTING = "erupting"
    SURGING = "surging"
    CHAOTIC = "chaotic"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PyroclasticFlow:
    """A choreographed pyroclastic fragment flow from a volcanic vent."""
    entity_id: str                              # internal key (e.g. "flow::vesuvius_ash_1")
    flow_id: str                                # external generated id for lookups
    flow_label: str                             # human-readable label
    flow_kind: FlowKind
    vent_id: str                                # source vent identifier
    vent_elevation_m: float                     # vent elevation in meters
    mass_flux_kg_s: float = 0.0                 # mass eruption rate (kg/s)
    temperature_k: float = 1100.0               # flow temperature in Kelvin
    # Ash column attributes.
    column_height_m: float = 0.0                # computed ash column height
    column_stable: bool = True                  # True if plume is stable, False if collapse candidate
    # Lava bomb ballistic attributes.
    launch_angle_deg: float = 45.0              # launch angle in degrees
    muzzle_velocity_mps: float = 100.0          # initial ballistic velocity (m/s)
    arc_apex_m: float = 0.0                     # computed apex of ballistic arc
    arc_range_m: float = 0.0                    # computed horizontal range
    flight_time_s: float = 0.0                  # computed time of flight
    # Surge current attributes.
    terrain_gradient: float = 0.1               # downhill slope (fraction, 0.0-1.0)
    runout_distance_m: float = 0.0              # computed surge runout
    surge_velocity_mps: float = 0.0             # computed surge velocity
    surge_class: SurgeClass = SurgeClass.DILUTE
    # Choreography state.
    stage_time_s: float = 0.0                   # assigned staging time within the choreography
    state: TrajectoryState = TrajectoryState.PENDING
    vitality: Vitality = Vitality.DORMANT
    created_at: float = field(default_factory=time.time)
    last_choreographed_at: float = 0.0
    note: str = ""


# =============================================================================
# Choreographer
# =============================================================================

class PyroclasticFlowChoreographer:
    """
    Thread-safe singleton that choreographs volcanic fragment-flow trajectories.

    Flows are keyed internally by entity_id so that each logical eruption source
    owns exactly one entry. The flow_id is a generated handle for external
    lookups; lookups by flow_id fall back to a linear scan of the registered
    flows.

    Usage:
        choreographer = PyroclasticFlowChoreographer.get_instance()
        choreographer.register_flow(
            entity_id="flow::vesuvius_ash_1",
            flow_label="Vesuvius Ash Plume",
            flow_kind="ash_column",
            vent_id="vent_vesuvius",
        )
        choreographer.cycle()
        flow = choreographer.get_flow(flow_id)
        report = choreographer.choreograph_flows()
    """

    _instance: Optional["PyroclasticFlowChoreographer"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Capacity caps.
    _MAX_FLOWS = 100
    _MAX_EVENTS = 200
    _MAX_ARCS = 120
    _MAX_ROUTES = 120
    _MAX_RECONCILIATIONS = 80
    _MAX_CHOREOGRAPHY = 120

    # Domain tuning constants.
    _GRAVITY = 9.81                          # m/s^2
    _COLUMN_HEIGHT_COEFF = 2500.0            # scaling for column height from mass flux
    _COLUMN_COLLAPSE_HEIGHT_M = 25000.0      # columns above this are stable; below may collapse
    _MAX_MUZZLE_VELOCITY = 400.0             # m/s cap on ballistic launch speed
    _MAX_LAUNCH_ANGLE_DEG = 89.0             # cap on launch angle (avoid pure vertical)
    _MIN_TERRAIN_GRADIENT = 0.01             # floor on downhill slope
    _MAX_TERRAIN_GRADIENT = 0.9              # ceiling on downhill slope
    _SURGE_RUNOUT_COEFF = 1500.0             # scaling for surge runout
    _SURGE_VELOCITY_COEFF = 25.0             # scaling for surge velocity
    _COLLISION_RANGE_M = 500.0               # flows within this horizontal band are collision candidates

    def __init__(self) -> None:
        # Internal dict keyed by entity_id (NOT flow_id).
        self._flows: Dict[str, PyroclasticFlow] = {}
        self._arcs: Dict[str, Dict[str, Any]] = {}
        self._routes: Dict[str, Dict[str, Any]] = {}
        self._reconciliations: Dict[str, Dict[str, Any]] = {}
        self._choreography: Dict[str, Dict[str, Any]] = {}
        self._phase: ChoreographyPhase = ChoreographyPhase.STAGE_ASH_COLUMN
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._flows:
            self._seed_synthetic_flows()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "PyroclasticFlowChoreographer":
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
            "flows_registered": 0,
            "phase_runs": 0,
            "columns_staged": 0,
            "arcs_planned": 0,
            "surges_routed": 0,
            "collisions_detected": 0,
            "choreographies_emitted": 0,
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
    def _parse_flow_kind(value: Any) -> FlowKind:
        """Parse a FlowKind from a string, enum, or None."""
        if value is None:
            return FlowKind.ASH_COLUMN
        if isinstance(value, FlowKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in FlowKind:
                if kind.value == lowered:
                    return kind
        return FlowKind.ASH_COLUMN

    @staticmethod
    def _parse_surge_class(value: Any) -> SurgeClass:
        """Parse a SurgeClass from a string, enum, or None."""
        if value is None:
            return SurgeClass.DILUTE
        if isinstance(value, SurgeClass):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for cls in SurgeClass:
                if cls.value == lowered:
                    return cls
        return SurgeClass.DILUTE

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _compute_column_height(self, mass_flux_kg_s: float) -> float:
        """Compute the ash column height from the mass eruption rate.

        Uses an empirical quarter-power scaling: taller columns come from
        larger mass flux. The result is clamped to a sensible ceiling.
        """
        flux = max(mass_flux_kg_s, 1.0)
        height = self._COLUMN_HEIGHT_COEFF * math.pow(flux, 0.25)
        return min(height, 45000.0)

    def _compute_ballistic_arc(self, launch_angle_deg: float, muzzle_velocity_mps: float) -> Dict[str, float]:
        """Compute the ballistic arc of a lava bomb or block clast.

        Returns apex, horizontal range, and time of flight using standard
        projectile motion under gravity.
        """
        angle = max(1.0, min(self._MAX_LAUNCH_ANGLE_DEG, float(launch_angle_deg)))
        velocity = max(1.0, min(self._MAX_MUZZLE_VELOCITY, float(muzzle_velocity_mps)))
        theta = math.radians(angle)
        sin_theta = math.sin(theta)
        # Time of flight (launch and landing at the same elevation).
        flight_time = (2.0 * velocity * sin_theta) / self._GRAVITY
        # Horizontal range.
        arc_range = (velocity * velocity * math.sin(2.0 * theta)) / self._GRAVITY
        # Apex height.
        arc_apex = (velocity * velocity * sin_theta * sin_theta) / (2.0 * self._GRAVITY)
        return {
            "arc_apex_m": arc_apex,
            "arc_range_m": arc_range,
            "flight_time_s": max(flight_time, 0.0),
        }

    def _compute_surge_runout(self, vent_elevation_m: float, terrain_gradient: float) -> float:
        """Compute the surge current runout distance downhill.

        Runout scales with the square root of the elevation drop and inversely
        with how steep the terrain is: steeper slopes shed faster but shorter.
        """
        gradient = max(self._MIN_TERRAIN_GRADIENT, min(self._MAX_TERRAIN_GRADIENT, terrain_gradient))
        drop = max(vent_elevation_m, 1.0)
        runout = self._SURGE_RUNOUT_COEFF * math.sqrt(drop) * (1.0 / (1.0 + gradient * 2.0))
        return max(runout, 0.0)

    def _compute_surge_velocity(self, terrain_gradient: float, temperature_k: float) -> float:
        """Compute the surge current velocity from gradient and temperature."""
        gradient = max(self._MIN_TERRAIN_GRADIENT, min(self._MAX_TERRAIN_GRADIENT, terrain_gradient))
        # Hotter, steeper surges move faster.
        temp_factor = max(temperature_k, 300.0) / 1100.0
        velocity = self._SURGE_VELOCITY_COEFF * math.sqrt(gradient * 9.81) * temp_factor
        return max(velocity, 0.0)

    def _classify_surge_class(self, runout_distance_m: float, mass_flux_kg_s: float) -> SurgeClass:
        """Classify a surge current by its runout and mass flux."""
        if mass_flux_kg_s >= 5.0e6 and runout_distance_m < 5000.0:
            return SurgeClass.CONCENTRATED
        if runout_distance_m >= 10000.0:
            return SurgeClass.DILUTE
        return SurgeClass.TRANSITIONAL

    def _color_for_flow_kind(self, flow_kind: FlowKind) -> str:
        """Map a flow kind to a preview color for the editor choreography."""
        if flow_kind == FlowKind.ASH_COLUMN:
            return "#C0C0C0"  # silver-grey ash plume
        if flow_kind == FlowKind.LAVA_BOMB:
            return "#FF4500"  # orange-red ballistic bomb
        if flow_kind == FlowKind.SURGE_CURRENT:
            return "#8B0000"  # dark red density current
        return "#FFD700"      # gold block clast

    # -------------------------------------------------------------------------
    # Flow Management
    # -------------------------------------------------------------------------

    def register_flow(
        self,
        entity_id: str,
        flow_label: str,
        flow_kind: Optional[str] = None,
        vent_id: str = "vent_default",
        vent_elevation_m: float = 1500.0,
        mass_flux_kg_s: float = 1.0e6,
        temperature_k: float = 1100.0,
        launch_angle_deg: float = 45.0,
        muzzle_velocity_mps: float = 120.0,
        terrain_gradient: float = 0.15,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new pyroclastic fragment flow with the choreographer."""
        with self._global_lock:
            if entity_id in self._flows:
                return {"error": f"Flow already registered: {entity_id}"}
            if len(self._flows) >= self._MAX_FLOWS:
                return {"error": f"Flow cap reached ({self._MAX_FLOWS})"}

            flow_id = (
                f"flow_{entity_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )

            parsed_kind = self._parse_flow_kind(flow_kind)
            elevation = max(0.0, float(vent_elevation_m))
            flux = max(0.0, float(mass_flux_kg_s))
            temp = max(300.0, float(temperature_k))

            flow = PyroclasticFlow(
                entity_id=entity_id,
                flow_id=flow_id,
                flow_label=flow_label,
                flow_kind=parsed_kind,
                vent_id=vent_id,
                vent_elevation_m=elevation,
                mass_flux_kg_s=flux,
                temperature_k=temp,
                column_height_m=0.0,
                column_stable=True,
                launch_angle_deg=float(launch_angle_deg),
                muzzle_velocity_mps=float(muzzle_velocity_mps),
                arc_apex_m=0.0,
                arc_range_m=0.0,
                flight_time_s=0.0,
                terrain_gradient=max(
                    self._MIN_TERRAIN_GRADIENT,
                    min(self._MAX_TERRAIN_GRADIENT, float(terrain_gradient)),
                ),
                runout_distance_m=0.0,
                surge_velocity_mps=0.0,
                surge_class=SurgeClass.DILUTE,
                stage_time_s=0.0,
                state=TrajectoryState.PENDING,
                vitality=Vitality.DORMANT,
                created_at=time.time(),
                last_choreographed_at=0.0,
                note=note,
            )
            self._flows[entity_id] = flow
            self._update_stats(flows_registered=1)
            self._record_event("flow_registered", {
                "flow_id": flow_id,
                "entity_id": entity_id,
                "flow_label": flow_label,
                "flow_kind": parsed_kind.value,
                "vent_id": vent_id,
                "vent_elevation_m": elevation,
            })

            return {
                "flow_id": flow_id,
                "entity_id": entity_id,
                "flow_label": flow_label,
                "flow_kind": parsed_kind.value,
                "vent_id": vent_id,
                "vent_elevation_m": elevation,
                "mass_flux_kg_s": flux,
                "temperature_k": temp,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single pyroclastic flow choreography cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic flows on the very first cycle if none exist.
            if not self._flows and self._cycle_count == 0:
                self._seed_synthetic_flows()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = ChoreographyPhase.STAGE_ASH_COLUMN
            phase_outputs.append(self._phase_stage_ash_column())
            self._phase = ChoreographyPhase.PLAN_LAVA_BOMB_ARCS
            phase_outputs.append(self._phase_plan_lava_bomb_arcs())
            self._phase = ChoreographyPhase.ROUTE_SURGE_CURRENTS
            phase_outputs.append(self._phase_route_surge_currents())
            self._phase = ChoreographyPhase.RECONCILE_TRAJECTORIES
            phase_outputs.append(self._phase_reconcile_trajectories())
            self._phase = ChoreographyPhase.EMIT_CHOREOGRAPHY
            phase_outputs.append(self._phase_emit_choreography())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_stage_ash_column(self) -> Dict[str, Any]:
        """Stage phase: compute ash column heights from mass flux and mark collapse candidates."""
        columns_staged = 0
        total_height = 0.0
        collapse_candidates = 0
        for flow in self._flows.values():
            if flow.state != TrajectoryState.PENDING:
                continue
            if flow.flow_kind == FlowKind.ASH_COLUMN:
                height = self._compute_column_height(flow.mass_flux_kg_s)
                flow.column_height_m = height
                # Columns below the collapse threshold that carry enough mass
                # are marked as collapse candidates (they may feed a surge).
                flow.column_stable = height >= self._COLUMN_COLLAPSE_HEIGHT_M
                if not flow.column_stable:
                    collapse_candidates += 1
                total_height += height
                columns_staged += 1
            # Non-ash flows skip staging but advance to the next state.
            flow.state = TrajectoryState.STAGED
        avg_height = (total_height / columns_staged) if columns_staged > 0 else 0.0
        self._update_stats(phase_runs=1, columns_staged=columns_staged)
        self._record_event("phase_stage_ash_column", {
            "columns_staged": columns_staged,
            "collapse_candidates": collapse_candidates,
            "avg_column_height_m": avg_height,
        })
        return {
            "phase": "stage_ash_column",
            "columns_staged": columns_staged,
            "collapse_candidates": collapse_candidates,
            "avg_column_height_m": avg_height,
        }

    def _phase_plan_lava_bomb_arcs(self) -> Dict[str, Any]:
        """Plan phase: plan ballistic lava-bomb and block-clast arcs."""
        arcs_planned = 0
        total_range = 0.0
        for flow in self._flows.values():
            if flow.state != TrajectoryState.STAGED:
                continue
            if flow.flow_kind in (FlowKind.LAVA_BOMB, FlowKind.BLOCK_CLAST):
                arc = self._compute_ballistic_arc(
                    flow.launch_angle_deg, flow.muzzle_velocity_mps,
                )
                flow.arc_apex_m = arc["arc_apex_m"]
                flow.arc_range_m = arc["arc_range_m"]
                flow.flight_time_s = arc["flight_time_s"]
                total_range += flow.arc_range_m
                arcs_planned += 1
                # Record the arc entry for the editor.
                arc_id = (
                    f"arc_{flow.flow_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                arc_entry = {
                    "arc_id": arc_id,
                    "flow_id": flow.flow_id,
                    "entity_id": flow.entity_id,
                    "vent_id": flow.vent_id,
                    "launch_angle_deg": flow.launch_angle_deg,
                    "muzzle_velocity_mps": flow.muzzle_velocity_mps,
                    "arc_apex_m": flow.arc_apex_m,
                    "arc_range_m": flow.arc_range_m,
                    "flight_time_s": flow.flight_time_s,
                    "color": self._color_for_flow_kind(flow.flow_kind),
                    "created_at": time.time(),
                }
                if len(self._arcs) >= self._MAX_ARCS:
                    oldest_key = next(iter(self._arcs))
                    self._arcs.pop(oldest_key, None)
                self._arcs[arc_id] = arc_entry
            flow.state = TrajectoryState.PLANNED
        avg_range = (total_range / arcs_planned) if arcs_planned > 0 else 0.0
        self._update_stats(phase_runs=1, arcs_planned=arcs_planned)
        self._record_event("phase_plan_lava_bomb_arcs", {
            "arcs_planned": arcs_planned,
            "avg_arc_range_m": avg_range,
        })
        return {
            "phase": "plan_lava_bomb_arcs",
            "arcs_planned": arcs_planned,
            "avg_arc_range_m": avg_range,
        }

    def _phase_route_surge_currents(self) -> Dict[str, Any]:
        """Route phase: route pyroclastic density currents downhill."""
        surges_routed = 0
        total_runout = 0.0
        for flow in self._flows.values():
            if flow.state != TrajectoryState.PLANNED:
                continue
            if flow.flow_kind == FlowKind.SURGE_CURRENT:
                runout = self._compute_surge_runout(
                    flow.vent_elevation_m, flow.terrain_gradient,
                )
                velocity = self._compute_surge_velocity(
                    flow.terrain_gradient, flow.temperature_k,
                )
                flow.runout_distance_m = runout
                flow.surge_velocity_mps = velocity
                flow.surge_class = self._classify_surge_class(
                    runout, flow.mass_flux_kg_s,
                )
                total_runout += runout
                surges_routed += 1
                # Record the route entry for the editor.
                route_id = (
                    f"route_{flow.flow_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                route_entry = {
                    "route_id": route_id,
                    "flow_id": flow.flow_id,
                    "entity_id": flow.entity_id,
                    "vent_id": flow.vent_id,
                    "vent_elevation_m": flow.vent_elevation_m,
                    "terrain_gradient": flow.terrain_gradient,
                    "runout_distance_m": flow.runout_distance_m,
                    "surge_velocity_mps": flow.surge_velocity_mps,
                    "surge_class": flow.surge_class.value,
                    "color": self._color_for_flow_kind(flow.flow_kind),
                    "created_at": time.time(),
                }
                if len(self._routes) >= self._MAX_ROUTES:
                    oldest_key = next(iter(self._routes))
                    self._routes.pop(oldest_key, None)
                self._routes[route_id] = route_entry
            # Also fold collapse-candidate ash columns into surge routing:
            # an unstable column that collapses feeds a fresh surge route.
            elif flow.flow_kind == FlowKind.ASH_COLUMN and not flow.column_stable:
                runout = self._compute_surge_runout(
                    flow.vent_elevation_m, flow.terrain_gradient,
                )
                velocity = self._compute_surge_velocity(
                    flow.terrain_gradient, flow.temperature_k,
                )
                flow.runout_distance_m = runout
                flow.surge_velocity_mps = velocity
                flow.surge_class = self._classify_surge_class(
                    runout, flow.mass_flux_kg_s,
                )
                total_runout += runout
                surges_routed += 1
                route_id = (
                    f"route_{flow.flow_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                route_entry = {
                    "route_id": route_id,
                    "flow_id": flow.flow_id,
                    "entity_id": flow.entity_id,
                    "vent_id": flow.vent_id,
                    "vent_elevation_m": flow.vent_elevation_m,
                    "terrain_gradient": flow.terrain_gradient,
                    "runout_distance_m": flow.runout_distance_m,
                    "surge_velocity_mps": flow.surge_velocity_mps,
                    "surge_class": flow.surge_class.value,
                    "color": self._color_for_flow_kind(FlowKind.SURGE_CURRENT),
                    "origin": "column_collapse",
                    "created_at": time.time(),
                }
                if len(self._routes) >= self._MAX_ROUTES:
                    oldest_key = next(iter(self._routes))
                    self._routes.pop(oldest_key, None)
                self._routes[route_id] = route_entry
            flow.state = TrajectoryState.ROUTED
        avg_runout = (total_runout / surges_routed) if surges_routed > 0 else 0.0
        self._update_stats(phase_runs=1, surges_routed=surges_routed)
        self._record_event("phase_route_surge_currents", {
            "surges_routed": surges_routed,
            "avg_runout_distance_m": avg_runout,
        })
        return {
            "phase": "route_surge_currents",
            "surges_routed": surges_routed,
            "avg_runout_distance_m": avg_runout,
        }

    def _phase_reconcile_trajectories(self) -> Dict[str, Any]:
        """Reconcile phase: reconcile intersecting trajectories and detect collisions."""
        collisions_detected = 0
        reconciled = 0
        flows_list = list(self._flows.values())
        for flow in flows_list:
            if flow.state != TrajectoryState.ROUTED:
                continue
            reconciled += 1
            # Compare against every other routed flow to find collision bands.
            for other in flows_list:
                if other.entity_id == flow.entity_id:
                    continue
                if other.state != TrajectoryState.ROUTED:
                    continue
                # Use the horizontal reach (arc range or runout) to detect
                # trajectories that land in overlapping bands.
                reach_a = flow.arc_range_m or flow.runout_distance_m
                reach_b = other.arc_range_m or other.runout_distance_m
                if reach_a <= 0.0 or reach_b <= 0.0:
                    continue
                if abs(reach_a - reach_b) <= self._COLLISION_RANGE_M:
                    collisions_detected += 1
                    reconciliation_id = (
                        f"recon_{flow.flow_id}_{other.flow_id}_"
                        f"{int(time.time() * 1000)}_{random.randint(100, 999)}"
                    )
                    recon_entry = {
                        "reconciliation_id": reconciliation_id,
                        "flow_a_id": flow.flow_id,
                        "flow_b_id": other.flow_id,
                        "reach_a_m": reach_a,
                        "reach_b_m": reach_b,
                        "separation_m": abs(reach_a - reach_b),
                        "kind": "collision_candidate",
                        "created_at": time.time(),
                    }
                    if len(self._reconciliations) >= self._MAX_RECONCILIATIONS:
                        oldest_key = next(iter(self._reconciliations))
                        self._reconciliations.pop(oldest_key, None)
                    self._reconciliations[reconciliation_id] = recon_entry
            flow.state = TrajectoryState.RECONCILED
        self._update_stats(
            phase_runs=1,
            collisions_detected=collisions_detected,
        )
        self._record_event("phase_reconcile_trajectories", {
            "reconciled": reconciled,
            "collisions_detected": collisions_detected,
        })
        return {
            "phase": "reconcile_trajectories",
            "reconciled": reconciled,
            "collisions_detected": collisions_detected,
        }

    def _phase_emit_choreography(self) -> Dict[str, Any]:
        """Emit phase: emit the full choreography map with staged flows, arcs, routes, timing."""
        emitted = 0
        # Assign staging times so each flow gets a slot in the choreography.
        slot_index = 0
        for flow in self._flows.values():
            if flow.state != TrajectoryState.RECONCILED:
                continue
            flow.state = TrajectoryState.EMITTED
            flow.last_choreographed_at = time.time()
            flow.vitality = self._derive_vitality(flow)
            flow.stage_time_s = float(slot_index) * 5.0
            slot_index += 1
            emitted += 1
            # Emit a choreography entry per flow.
            choreography_id = (
                f"chor_{flow.flow_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            entry = {
                "choreography_id": choreography_id,
                "flow_id": flow.flow_id,
                "entity_id": flow.entity_id,
                "flow_label": flow.flow_label,
                "flow_kind": flow.flow_kind.value,
                "vent_id": flow.vent_id,
                "stage_time_s": flow.stage_time_s,
                "column_height_m": flow.column_height_m,
                "column_stable": flow.column_stable,
                "arc_apex_m": flow.arc_apex_m,
                "arc_range_m": flow.arc_range_m,
                "flight_time_s": flow.flight_time_s,
                "runout_distance_m": flow.runout_distance_m,
                "surge_velocity_mps": flow.surge_velocity_mps,
                "surge_class": flow.surge_class.value,
                "vitality": flow.vitality.value,
                "color": self._color_for_flow_kind(flow.flow_kind),
                "visible": True,
                "preview_url": f"/preview/pyroclastic/{choreography_id}.svg",
                "created_at": time.time(),
            }
            if len(self._choreography) >= self._MAX_CHOREOGRAPHY:
                oldest_key = next(iter(self._choreography))
                self._choreography.pop(oldest_key, None)
            self._choreography[choreography_id] = entry
        map_size = (
            len(self._flows) + len(self._arcs) + len(self._routes)
            + len(self._reconciliations) + len(self._choreography)
        )
        self._update_stats(phase_runs=1, choreographies_emitted=1)
        self._record_event("phase_emit_choreography", {
            "emitted": emitted,
            "map_size": map_size,
        })
        return {
            "phase": "emit_choreography",
            "emitted": emitted,
            "map_size": map_size,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _derive_vitality(self, flow: PyroclasticFlow) -> Vitality:
        """Derive the vitality of a flow from its computed trajectory."""
        if flow.flow_kind == FlowKind.ASH_COLUMN:
            if not flow.column_stable:
                return Vitality.CHAOTIC
            if flow.column_height_m >= 30000.0:
                return Vitality.ERUPTING
            if flow.column_height_m >= 10000.0:
                return Vitality.SURGING
            if flow.column_height_m > 0.0:
                return Vitality.STIRRING
            return Vitality.DORMANT
        if flow.flow_kind in (FlowKind.LAVA_BOMB, FlowKind.BLOCK_CLAST):
            if flow.arc_range_m >= 3000.0:
                return Vitality.CHAOTIC
            if flow.arc_range_m >= 1000.0:
                return Vitality.ERUPTING
            if flow.arc_range_m > 0.0:
                return Vitality.STIRRING
            return Vitality.DORMANT
        if flow.flow_kind == FlowKind.SURGE_CURRENT:
            if flow.surge_velocity_mps >= 50.0:
                return Vitality.CHAOTIC
            if flow.surge_velocity_mps >= 20.0:
                return Vitality.SURGING
            if flow.runout_distance_m > 0.0:
                return Vitality.ERUPTING
            return Vitality.DORMANT
        return Vitality.DORMANT

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_flows(self) -> None:
        """Seed a few synthetic pyroclastic flows if the choreographer is empty."""
        seeds = [
            (
                "flow::vesuvius_ash_plume",
                "Vesuvius Ash Plume",
                FlowKind.ASH_COLUMN,
                "vent_vesuvius",
                1280.0,
                1.5e7,
                1100.0,
                45.0,
                120.0,
                0.18,
            ),
            (
                "flow::vesuvius_lava_bomb_alpha",
                "Vesuvius Lava Bomb Alpha",
                FlowKind.LAVA_BOMB,
                "vent_vesuvius",
                1280.0,
                0.0,
                1300.0,
                55.0,
                180.0,
                0.18,
            ),
            (
                "flow::vesuvius_surge_beta",
                "Vesuvius Surge Beta",
                FlowKind.SURGE_CURRENT,
                "vent_vesuvius",
                1280.0,
                3.0e6,
                1050.0,
                45.0,
                100.0,
                0.22,
            ),
            (
                "flow::stromboli_block_gamma",
                "Stromboli Block Gamma",
                FlowKind.BLOCK_CLAST,
                "vent_stromboli",
                920.0,
                0.0,
                1250.0,
                65.0,
                220.0,
                0.30,
            ),
        ]
        for (
            entity_id,
            flow_label,
            flow_kind,
            vent_id,
            vent_elevation_m,
            mass_flux_kg_s,
            temperature_k,
            launch_angle_deg,
            muzzle_velocity_mps,
            terrain_gradient,
        ) in seeds:
            if entity_id in self._flows:
                continue
            if len(self._flows) >= self._MAX_FLOWS:
                break
            self.register_flow(
                entity_id=entity_id,
                flow_label=flow_label,
                flow_kind=flow_kind.value,
                vent_id=vent_id,
                vent_elevation_m=vent_elevation_m,
                mass_flux_kg_s=mass_flux_kg_s,
                temperature_k=temperature_k,
                launch_angle_deg=launch_angle_deg,
                muzzle_velocity_mps=muzzle_velocity_mps,
                terrain_gradient=terrain_gradient,
                note="seeded",
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _flow_to_dict(self, flow: PyroclasticFlow) -> Dict[str, Any]:
        return {
            "flow_id": flow.flow_id,
            "entity_id": flow.entity_id,
            "flow_label": flow.flow_label,
            "flow_kind": flow.flow_kind.value,
            "vent_id": flow.vent_id,
            "vent_elevation_m": flow.vent_elevation_m,
            "mass_flux_kg_s": flow.mass_flux_kg_s,
            "temperature_k": flow.temperature_k,
            "column_height_m": flow.column_height_m,
            "column_stable": flow.column_stable,
            "launch_angle_deg": flow.launch_angle_deg,
            "muzzle_velocity_mps": flow.muzzle_velocity_mps,
            "arc_apex_m": flow.arc_apex_m,
            "arc_range_m": flow.arc_range_m,
            "flight_time_s": flow.flight_time_s,
            "terrain_gradient": flow.terrain_gradient,
            "runout_distance_m": flow.runout_distance_m,
            "surge_velocity_mps": flow.surge_velocity_mps,
            "surge_class": flow.surge_class.value,
            "stage_time_s": flow.stage_time_s,
            "state": flow.state.value,
            "vitality": flow.vitality.value,
            "created_at": flow.created_at,
            "last_choreographed_at": flow.last_choreographed_at,
            "note": flow.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "flows": len(self._flows),
                "arcs": len(self._arcs),
                "routes": len(self._routes),
                "reconciliations": len(self._reconciliations),
                "choreography": len(self._choreography),
                "stats": dict(self._stats),
            }

    def get_flows(self, limit: int = 10) -> Dict[str, Any]:
        with self._global_lock:
            flows = sorted(
                self._flows.values(),
                key=lambda f: f.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(flows),
                "flows": [
                    {
                        "flow_id": f.flow_id,
                        "entity_id": f.entity_id,
                        "flow_label": f.flow_label,
                        "flow_kind": f.flow_kind.value,
                        "vent_id": f.vent_id,
                        "vent_elevation_m": f.vent_elevation_m,
                        "state": f.state.value,
                        "vitality": f.vitality.value,
                    }
                    for f in flows
                ],
            }

    def get_flow(self, flow_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT flow_id, so we
        # MUST iterate over values and match on the flow_id attribute.
        with self._global_lock:
            for flow in self._flows.values():
                if flow.flow_id == flow_id:
                    return self._flow_to_dict(flow)
            return {
                "error": "flow not found",
                "flow_id": flow_id,
            }

    def get_events_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic flows if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._flows:
                self._seed_synthetic_flows()
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
            self._flows.clear()
            self._arcs.clear()
            self._routes.clear()
            self._reconciliations.clear()
            self._choreography.clear()
            self._phase = ChoreographyPhase.STAGE_ASH_COLUMN
            self._cycle_count = 0
            self._init_stats()
            # Re-seed synthetic data so the choreographer is never empty.
            self._seed_synthetic_flows()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }

    # -------------------------------------------------------------------------
    # Domain Action
    # -------------------------------------------------------------------------

    def choreograph_flows(
        self,
        wind_speed_mps: float = 0.0,
        terrain_step_m: float = 50.0,
    ) -> Dict[str, Any]:
        """Produce a unified choreography report across all staged flows.

        Synthesizes the registered flows into a single staged eruption
        sequence with timing, collision warnings, dispersal footprint, and
        peak energy estimates.
        """
        with self._global_lock:
            flows = list(self._flows.values())
            staged_count = len(flows)
            total_mass = sum(f.mass_flux_kg_s for f in flows)
            total_runout = sum(f.runout_distance_m for f in flows)
            total_range = sum(f.arc_range_m for f in flows)
            peak_column = max((f.column_height_m for f in flows), default=0.0)
            peak_apex = max((f.arc_apex_m for f in flows), default=0.0)
            peak_velocity = max((f.surge_velocity_mps for f in flows), default=0.0)

            # Build collision warnings from the reconciliation log.
            warnings: List[Dict[str, Any]] = []
            for recon in self._reconciliations.values():
                if recon.get("kind") == "collision_candidate":
                    warnings.append({
                        "flow_a_id": recon.get("flow_a_id"),
                        "flow_b_id": recon.get("flow_b_id"),
                        "separation_m": recon.get("separation_m"),
                    })

            # Timing score: how evenly the staging slots are distributed.
            timing_score = 1.0
            if staged_count > 1:
                timing_score = max(0.0, 1.0 - (staged_count * 0.05))

            # Dispersal footprint: rough ellipse area from range and runout.
            major_axis = max(total_range, total_runout, 1.0)
            minor_axis = max(peak_apex, peak_column * 0.1, 1.0)
            dispersal_footprint_m2 = math.pi * major_axis * minor_axis

            # Peak kinetic energy estimate from the fastest surge.
            peak_energy_j = 0.5 * (total_mass / max(staged_count, 1)) * (peak_velocity ** 2)

            choreography_id = (
                f"choreography_report_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )

            self._record_event("choreograph_flows", {
                "choreography_id": choreography_id,
                "staged_flows": staged_count,
                "collision_warnings": len(warnings),
            })

            return {
                "choreography_id": choreography_id,
                "staged_flows": staged_count,
                "total_mass_flux_kg_s": total_mass,
                "peak_column_height_m": peak_column,
                "peak_arc_apex_m": peak_apex,
                "peak_surge_velocity_mps": peak_velocity,
                "total_runout_m": total_runout,
                "total_arc_range_m": total_range,
                "timing_score": timing_score,
                "dispersal_footprint_m2": dispersal_footprint_m2,
                "peak_energy_j": peak_energy_j,
                "wind_speed_mps": float(wind_speed_mps),
                "terrain_step_m": float(terrain_step_m),
                "collision_warnings": warnings,
                "cycle_count": self._cycle_count,
            }
