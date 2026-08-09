"""
SparkLabs Engine - Temporal Flow Regulator"""

from __future__ import annotations

import logging
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

class TemporalRegionType(Enum):
    """Types of temporal regions."""
    NORMAL = "normal"          # standard time flow
    DILATED = "dilated"        # slow-motion
    COMPRESSED = "compressed"  # fast-forward
    STASIS = "stasis"          # frozen time
    EDDY = "eddy"             # time loop
    RAPID = "rapid"            # extreme fast-forward


class FlowPhase(Enum):
    """Phases of the temporal flow cycle."""
    FLOW = "flow"
    MEASURE = "measure"
    REGULATE = "regulate"
    DISTORT = "distort"
    STABILIZE = "stabilize"


class TemporalEvent(Enum):
    """Events that can occur in the temporal field."""
    FREEZE = "freeze"            # region enters stasis
    THAW = "thaw"                # region exits stasis
    SURGE = "surge"              # flow rate spikes
    RECEDE = "recede"            # flow rate drops
    BREACH = "breach"            # pressure cascade between regions
    VORTEX_FORM = "vortex_form"  # eddy forms
    VORTEX_COLLAPSE = "vortex_collapse"  # eddy dissipates
    SYNC = "sync"                # regions synchronize flow rates


# =============================================================================
# Temporal Constants
# =============================================================================

# Default flow rates for each region type
DEFAULT_FLOW_RATES: Dict[TemporalRegionType, float] = {
    TemporalRegionType.NORMAL: 1.0,
    TemporalRegionType.DILATED: 0.3,
    TemporalRegionType.COMPRESSED: 2.5,
    TemporalRegionType.STASIS: 0.0,
    TemporalRegionType.EDDY: 0.8,
    TemporalRegionType.RAPID: 5.0,
}

# Default viscosity for each region type
DEFAULT_VISCOSITY: Dict[TemporalRegionType, float] = {
    TemporalRegionType.NORMAL: 0.5,
    TemporalRegionType.DILATED: 0.7,
    TemporalRegionType.COMPRESSED: 0.4,
    TemporalRegionType.STASIS: 1.0,
    TemporalRegionType.EDDY: 0.3,
    TemporalRegionType.RAPID: 0.1,
}

# Default density for each region type
DEFAULT_DENSITY: Dict[TemporalRegionType, float] = {
    TemporalRegionType.NORMAL: 0.5,
    TemporalRegionType.DILATED: 0.8,
    TemporalRegionType.COMPRESSED: 0.2,
    TemporalRegionType.STASIS: 1.0,
    TemporalRegionType.EDDY: 0.6,
    TemporalRegionType.RAPID: 0.1,
}

# Pressure threshold for breach events
BREACH_THRESHOLD = 0.5


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class TemporalCurrent:
    """A directional flow of time between two regions."""
    current_id: str
    source_id: str
    target_id: str
    # Flow rate differential (how much time flows from source to target)
    flow_differential: float
    # Direction of flow (positive = source to target, negative = target to source)
    direction: float = 1.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class TemporalRegion:
    """A region of game space with its own time flow properties."""
    region_id: str
    label: str
    region_type: TemporalRegionType = TemporalRegionType.NORMAL
    # Current flow rate (0.0 = frozen, 1.0 = normal, >1.0 = fast)
    flow_rate: float = 1.0
    # Target flow rate (what the region is moving toward)
    target_flow_rate: float = 1.0
    # Viscosity (resistance to change, 0.0-1.0)
    viscosity: float = 0.5
    # Temporal density (affects simulation detail, 0.0-1.0)
    density: float = 0.5
    # Temporal pressure (builds up when flow rate differs from neighbors)
    pressure: float = 0.0
    # Whether this region is currently in an eddy (time loop)
    is_eddy_active: bool = False
    # Eddy rotation count (how many loops have occurred)
    eddy_rotations: int = 0
    # Connected regions via currents
    currents: List[TemporalCurrent] = field(default_factory=list)
    # Metadata
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    # Total time elapsed in this region (game time)
    elapsed_game_time: float = 0.0
    # Number of flow rate changes
    flow_changes: int = 0


@dataclass
class TemporalEventRecord:
    """A recorded temporal event."""
    event_id: str
    event_type: TemporalEvent
    region_id: str
    region_label: str
    old_flow_rate: float
    new_flow_rate: float
    description: str
    timestamp: float


@dataclass
class TemporalFieldStats:
    """Aggregate statistics for the temporal field."""
    total_regions: int = 0
    total_events: int = 0
    total_freezes: int = 0
    total_thaws: int = 0
    total_surges: int = 0
    total_recedes: int = 0
    total_breaches: int = 0
    total_vortices_formed: int = 0
    total_vortices_collapsed: int = 0
    total_syncs: int = 0
    avg_flow_rate: float = 1.0
    avg_viscosity: float = 0.5
    avg_pressure: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Engine Temporal Flow Regulator
# =============================================================================

class EngineTemporalFlowRegulator:
    """
    Singleton engine module that regulates temporal flow across game
    regions using fluid dynamics metaphors.

    The regulator runs a 5-phase cycle:
      1. FLOW      - Time flows through regions at their current rates
      2. MEASURE   - Flow rates and pressures are measured
      3. REGULATE  - Flow rates adjust toward their targets
      4. DISTORT   - Pressure differentials cause temporal distortions
      5. STABILIZE - Viscosity dampens extreme values

    The fluid metaphor ensures temporal dynamics feel natural: time
    doesn't snap between rates, it flows and pools like a viscous fluid
    responding to pressure differentials.
    """

    _instance: Optional["EngineTemporalFlowRegulator"] = None
    _instance_lock = threading.Lock()

    # Configuration
    MAX_REGIONS = 100
    MAX_EVENT_HISTORY = 200
    MAX_CURRENTS_PER_REGION = 8
    # How quickly flow rate moves toward target (lower = more viscous)
    FLOW_ADJUSTMENT_RATE = 0.1
    # Minimum flow rate
    MIN_FLOW_RATE = 0.0
    # Maximum flow rate
    MAX_FLOW_RATE = 10.0
    # Pressure buildup rate when neighbors differ
    PRESSURE_RATE = 0.05
    # Pressure decay rate
    PRESSURE_DECAY = 0.02
    # Breach threshold (pressure needed to trigger cascade)
    BREACH_THRESHOLD = 0.5
    # Breach propagation factor
    BREACH_PROPAGATION = 0.4
    # Eddy formation chance when flow is circular
    EDDY_FORM_CHANCE = 0.15
    # Eddy collapse chance per cycle
    EDDY_COLLAPSE_CHANCE = 0.05
    # Sync threshold (regions within this range synchronize)
    SYNC_THRESHOLD = 0.1

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._regions: Dict[str, TemporalRegion] = {}
        self._event_history: Deque[TemporalEventRecord] = deque(
            maxlen=self.MAX_EVENT_HISTORY
        )
        self._stats = TemporalFieldStats()
        self._cycle_count: int = 0
        self._active: bool = False

    @classmethod
    def get_instance(cls) -> "EngineTemporalFlowRegulator":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Region Management
    # -------------------------------------------------------------------------

    def register_region(self, region_id: str, label: str,
                        region_type: str = "normal",
                        flow_rate: Optional[float] = None,
                        viscosity: Optional[float] = None,
                        density: Optional[float] = None,
                        ) -> Dict[str, Any]:
        """Register a new temporal region."""
        with self._lock:
            if region_id in self._regions:
                return {"error": f"Region already exists: {region_id}"}
            if len(self._regions) >= self.MAX_REGIONS:
                return {"error": "Maximum regions reached"}

            try:
                rtype = TemporalRegionType(region_type)
            except ValueError:
                return {"error": f"Unknown region type: {region_type}"}

            # Use defaults from region type if not specified
            if flow_rate is None:
                flow_rate = DEFAULT_FLOW_RATES.get(rtype, 1.0)
            if viscosity is None:
                viscosity = DEFAULT_VISCOSITY.get(rtype, 0.5)
            if density is None:
                density = DEFAULT_DENSITY.get(rtype, 0.5)

            region = TemporalRegion(
                region_id=region_id,
                label=label,
                region_type=rtype,
                flow_rate=max(self.MIN_FLOW_RATE, min(self.MAX_FLOW_RATE, float(flow_rate))),
                target_flow_rate=max(self.MIN_FLOW_RATE, min(self.MAX_FLOW_RATE, float(flow_rate))),
                viscosity=max(0.0, min(1.0, float(viscosity))),
                density=max(0.0, min(1.0, float(density))),
            )
            self._regions[region_id] = region
            self._stats.total_regions = len(self._regions)
            return self._region_to_dict(region)

    def get_region(self, region_id: str) -> Dict[str, Any]:
        """Get the state of a temporal region."""
        with self._lock:
            region = self._regions.get(region_id)
            if region is None:
                return {"error": f"Region not found: {region_id}"}
            return self._region_to_dict(region)

    def list_regions(self) -> Dict[str, Any]:
        """List all temporal regions."""
        with self._lock:
            return {
                "regions": [self._region_to_dict(r) for r in self._regions.values()],
                "total": len(self._regions),
            }

    def remove_region(self, region_id: str) -> Dict[str, Any]:
        """Remove a temporal region."""
        with self._lock:
            if region_id not in self._regions:
                return {"error": f"Region not found: {region_id}"}
            # Remove currents pointing to this region
            for r in self._regions.values():
                r.currents = [c for c in r.currents if c.target_id != region_id]
            del self._regions[region_id]
            self._stats.total_regions = len(self._regions)
            return {"removed": region_id}

    def set_flow_rate(self, region_id: str, flow_rate: float,
                      description: str = "") -> Dict[str, Any]:
        """Set the target flow rate for a region."""
        with self._lock:
            region = self._regions.get(region_id)
            if region is None:
                return {"error": f"Region not found: {region_id}"}

            old_rate = region.flow_rate
            new_rate = max(self.MIN_FLOW_RATE, min(self.MAX_FLOW_RATE, float(flow_rate)))
            region.target_flow_rate = new_rate
            region.flow_changes += 1
            region.last_updated = time.time()

            # Record event
            event_type: TemporalEvent
            if new_rate == 0.0:
                event_type = TemporalEvent.FREEZE
                self._stats.total_freezes += 1
            elif old_rate == 0.0 and new_rate > 0.0:
                event_type = TemporalEvent.THAW
                self._stats.total_thaws += 1
            elif new_rate > old_rate:
                event_type = TemporalEvent.SURGE
                self._stats.total_surges += 1
            else:
                event_type = TemporalEvent.RECEDE
                self._stats.total_recedes += 1

            self._record_event(region, event_type, old_rate, new_rate, description)

            return self._region_to_dict(region)

    # -------------------------------------------------------------------------
    # Current Management (connections between regions)
    # -------------------------------------------------------------------------

    def link_regions(self, source_id: str, target_id: str,
                     flow_differential: float = 0.1) -> Dict[str, Any]:
        """Create a temporal current between two regions."""
        with self._lock:
            source = self._regions.get(source_id)
            if source is None:
                return {"error": f"Source region not found: {source_id}"}
            if target_id not in self._regions:
                return {"error": f"Target region not found: {target_id}"}
            if source_id == target_id:
                return {"error": "Cannot link region to itself"}
            if len(source.currents) >= self.MAX_CURRENTS_PER_REGION:
                return {"error": "Maximum currents reached for source region"}

            # Check if current already exists
            for c in source.currents:
                if c.target_id == target_id:
                    c.flow_differential = float(flow_differential)
                    return {"current": self._current_to_dict(c)}

            current = TemporalCurrent(
                current_id=f"current_{source_id}_{target_id}_{int(time.time()*1000)}",
                source_id=source_id,
                target_id=target_id,
                flow_differential=float(flow_differential),
            )
            source.currents.append(current)
            return {"current": self._current_to_dict(current)}

    def unlink_regions(self, source_id: str, target_id: str) -> Dict[str, Any]:
        """Remove a temporal current between regions."""
        with self._lock:
            source = self._regions.get(source_id)
            if source is None:
                return {"error": f"Source region not found: {source_id}"}
            original_len = len(source.currents)
            source.currents = [c for c in source.currents if c.target_id != target_id]
            removed = original_len - len(source.currents)
            return {"removed": removed, "source_id": source_id, "target_id": target_id}

    def get_currents(self, region_id: str) -> Dict[str, Any]:
        """Get all temporal currents for a region."""
        with self._lock:
            region = self._regions.get(region_id)
            if region is None:
                return {"error": f"Region not found: {region_id}"}
            return {
                "region_id": region_id,
                "currents": [self._current_to_dict(c) for c in region.currents],
                "total": len(region.currents),
            }

    # -------------------------------------------------------------------------
    # Temporal Flow Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single temporal flow cycle.

        Phases: FLOW -> MEASURE -> REGULATE -> DISTORT -> STABILIZE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: FLOW - Time flows through regions
            phase = FlowPhase.FLOW
            flow_info = self._flow_phase()

            # Phase 2: MEASURE - Measure pressures and differentials
            phase = FlowPhase.MEASURE
            measure_info = self._measure_phase()

            # Phase 3: REGULATE - Adjust flow rates toward targets
            phase = FlowPhase.REGULATE
            regulate_info = self._regulate_phase()

            # Phase 4: DISTORT - Pressure cascades cause distortions
            phase = FlowPhase.DISTORT
            distort_info = self._distort_phase()

            # Phase 5: STABILIZE - Viscosity dampens extremes
            phase = FlowPhase.STABILIZE
            stabilize_info = self._stabilize_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()

            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "flow": flow_info,
                "measure": measure_info,
                "regulate": regulate_info,
                "distort": distort_info,
                "stabilize": stabilize_info,
                "total_regions": len(self._regions),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _flow_phase(self) -> Dict[str, Any]:
        """Phase 1: Time flows through regions at their current rates."""
        total_flow = 0.0
        for region in self._regions.values():
            # Advance game time by flow rate
            region.elapsed_game_time += region.flow_rate
            total_flow += region.flow_rate

            # Handle eddy rotation
            if region.is_eddy_active:
                region.eddy_rotations += int(region.flow_rate * 0.5)
                # Chance to collapse
                if random.random() < self.EDDY_COLLAPSE_CHANCE:
                    region.is_eddy_active = False
                    self._record_event(
                        region, TemporalEvent.VORTEX_COLLAPSE,
                        region.flow_rate, region.flow_rate,
                        f"Eddy collapsed in {region.label}"
                    )
                    self._stats.total_vortices_collapsed += 1

        return {
            "total_flow": round(total_flow, 4),
            "avg_flow": round(total_flow / max(1, len(self._regions)), 4),
        }

    def _measure_phase(self) -> Dict[str, Any]:
        """Phase 2: Measure temporal pressure between connected regions."""
        pressures_measured = 0
        for region in self._regions.values():
            if not region.currents:
                continue
            for current in region.currents:
                target = self._regions.get(current.target_id)
                if target is None:
                    continue

                # Pressure builds from flow rate differential
                diff = abs(region.flow_rate - target.flow_rate)
                pressure_delta = diff * self.PRESSURE_RATE * current.flow_differential
                region.pressure += pressure_delta
                pressures_measured += 1

            # Clamp pressure
            region.pressure = max(0.0, min(2.0, region.pressure))

        return {"pressures_measured": pressures_measured}

    def _regulate_phase(self) -> Dict[str, Any]:
        """Phase 3: Flow rates adjust toward their targets."""
        adjustments = 0
        for region in self._regions.values():
            if abs(region.flow_rate - region.target_flow_rate) < 0.01:
                continue

            # Viscosity resists change
            adjustment = (region.target_flow_rate - region.flow_rate) * self.FLOW_ADJUSTMENT_RATE
            adjustment *= (1.0 - region.viscosity * 0.5)

            old_rate = region.flow_rate
            region.flow_rate = max(
                self.MIN_FLOW_RATE,
                min(self.MAX_FLOW_RATE, region.flow_rate + adjustment)
            )

            if abs(region.flow_rate - old_rate) > 0.001:
                adjustments += 1

        return {"flow_adjustments": adjustments}

    def _distort_phase(self) -> Dict[str, Any]:
        """Phase 4: Pressure differentials cause temporal distortions."""
        breaches = 0
        vortices_formed = 0
        syncs = 0

        for region in list(self._regions.values()):
            # Check for breach (pressure cascade)
            if region.pressure >= self.BREACH_THRESHOLD:
                for current in region.currents:
                    target = self._regions.get(current.target_id)
                    if target is None:
                        continue

                    # Propagate pressure to target
                    target.pressure += region.pressure * self.BREACH_PROPAGATION

                    # Shift target flow rate toward source
                    shift = (region.flow_rate - target.flow_rate) * self.BREACH_PROPAGATION
                    target.target_flow_rate = max(
                        self.MIN_FLOW_RATE,
                        min(self.MAX_FLOW_RATE, target.target_flow_rate + shift)
                    )

                # Record breach event
                self._record_event(
                    region, TemporalEvent.BREACH,
                    region.flow_rate, region.flow_rate,
                    f"Temporal breach in {region.label}, pressure {region.pressure:.2f}"
                )
                breaches += 1
                self._stats.total_breaches += 1

                # Reduce pressure after breach
                region.pressure *= 0.5

            # Check for eddy formation (circular flow)
            if not region.is_eddy_active and region.region_type == TemporalRegionType.EDDY:
                if random.random() < self.EDDY_FORM_CHANCE:
                    region.is_eddy_active = True
                    self._record_event(
                        region, TemporalEvent.VORTEX_FORM,
                        region.flow_rate, region.flow_rate,
                        f"Temporal eddy formed in {region.label}"
                    )
                    vortices_formed += 1
                    self._stats.total_vortices_formed += 1

            # Check for sync (regions with similar flow rates synchronize)
            for current in region.currents:
                target = self._regions.get(current.target_id)
                if target is None:
                    continue
                if abs(region.flow_rate - target.flow_rate) < self.SYNC_THRESHOLD:
                    # Both regions move toward their average
                    avg = (region.flow_rate + target.flow_rate) / 2.0
                    region.target_flow_rate = avg
                    target.target_flow_rate = avg
                    syncs += 1

        self._stats.total_syncs += syncs
        return {
            "breaches": breaches,
            "vortices_formed": vortices_formed,
            "syncs": syncs,
        }

    def _stabilize_phase(self) -> Dict[str, Any]:
        """Phase 5: Viscosity dampens extreme values and pressure decays."""
        for region in self._regions.values():
            # Pressure decays
            region.pressure = max(0.0, region.pressure - self.PRESSURE_DECAY)

            # High viscosity pulls flow rate toward 1.0 (normal)
            if region.viscosity > 0.7 and region.region_type == TemporalRegionType.NORMAL:
                pull = (1.0 - region.flow_rate) * 0.02 * region.viscosity
                region.flow_rate = max(
                    self.MIN_FLOW_RATE,
                    min(self.MAX_FLOW_RATE, region.flow_rate + pull)
                )

            region.last_updated = time.time()

        return {"regions_stabilized": len(self._regions)}

    # -------------------------------------------------------------------------
    # Simulation and Status
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles in sequence and seed sample data if empty."""
        with self._lock:
            # Seed sample regions if empty
            if not self._regions:
                self._seed_sample_data()

            last_cycle: Optional[Dict[str, Any]] = None
            for _ in range(cycles):
                # Randomly adjust flow rates during simulation
                if self._regions and random.random() < 0.3:
                    region_id = random.choice(list(self._regions.keys()))
                    new_rate = random.choice([0.0, 0.3, 1.0, 2.5, 5.0])
                    self.set_flow_rate(region_id, new_rate)
                last_cycle = self.run_cycle()

            return {
                "cycles_run": cycles,
                "last_cycle": last_cycle,
                "final_stats": self._stats_to_dict(),
                "status": self.get_status(),
            }

    def _seed_sample_data(self) -> None:
        """Seed the field with sample regions and currents."""
        sample_regions = [
            ("region_arena", "Boss Arena", "dilated", 0.3),
            ("region_town", "Town Hub", "normal", 1.0),
            ("region_wild", "Wilderness", "normal", 1.0),
            ("region_dungeon", "Dungeon", "compressed", 2.5),
            ("region_shrine", "Ancient Shrine", "stasis", 0.0),
            ("region_maze", "Time Maze", "eddy", 0.8),
        ]
        for rid, label, rtype, rate in sample_regions:
            self.register_region(rid, label, rtype, rate)

        # Link regions
        self.link_regions("region_town", "region_arena", 0.5)
        self.link_regions("region_town", "region_wild", 0.3)
        self.link_regions("region_wild", "region_dungeon", 0.4)
        self.link_regions("region_dungeon", "region_shrine", 0.6)
        self.link_regions("region_arena", "region_maze", 0.3)

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the temporal field."""
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "total_regions": len(self._regions),
                "stats": self._stats_to_dict(),
            }

    def get_events(self, region_id: Optional[str] = None,
                   limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent temporal events."""
        with self._lock:
            results = []
            for event in self._event_history:
                if region_id and event.region_id != region_id:
                    continue
                results.append(self._event_to_dict(event))
            return results[:limit]

    def reset(self) -> Dict[str, Any]:
        """Reset the temporal field to initial state."""
        with self._lock:
            self._regions.clear()
            self._event_history.clear()
            self._stats = TemporalFieldStats()
            self._cycle_count = 0
            self._active = False
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _record_event(self, region: TemporalRegion, event_type: TemporalEvent,
                      old_rate: float, new_rate: float,
                      description: str) -> None:
        event = TemporalEventRecord(
            event_id=f"evt_{int(time.time()*1000)}_{random.randint(0,9999)}",
            event_type=event_type,
            region_id=region.region_id,
            region_label=region.label,
            old_flow_rate=round(old_rate, 4),
            new_flow_rate=round(new_rate, 4),
            description=description,
            timestamp=time.time(),
        )
        self._event_history.append(event)
        self._stats.total_events += 1

    def _update_avg_metrics(self) -> None:
        if not self._regions:
            self._stats.avg_flow_rate = 1.0
            self._stats.avg_viscosity = 0.5
            self._stats.avg_pressure = 0.0
            return
        self._stats.avg_flow_rate = round(
            sum(r.flow_rate for r in self._regions.values()) / len(self._regions), 4
        )
        self._stats.avg_viscosity = round(
            sum(r.viscosity for r in self._regions.values()) / len(self._regions), 4
        )
        self._stats.avg_pressure = round(
            sum(r.pressure for r in self._regions.values()) / len(self._regions), 4
        )

    def _stats_to_dict(self) -> Dict[str, Any]:
        return {
            "total_regions": self._stats.total_regions,
            "total_events": self._stats.total_events,
            "total_freezes": self._stats.total_freezes,
            "total_thaws": self._stats.total_thaws,
            "total_surges": self._stats.total_surges,
            "total_recedes": self._stats.total_recedes,
            "total_breaches": self._stats.total_breaches,
            "total_vortices_formed": self._stats.total_vortices_formed,
            "total_vortices_collapsed": self._stats.total_vortices_collapsed,
            "total_syncs": self._stats.total_syncs,
            "avg_flow_rate": self._stats.avg_flow_rate,
            "avg_viscosity": self._stats.avg_viscosity,
            "avg_pressure": self._stats.avg_pressure,
            "last_cycle_time_ms": self._stats.last_cycle_time_ms,
            "active": self._stats.active,
        }

    def _region_to_dict(self, region: TemporalRegion) -> Dict[str, Any]:
        return {
            "region_id": region.region_id,
            "label": region.label,
            "region_type": region.region_type.value,
            "flow_rate": round(region.flow_rate, 4),
            "target_flow_rate": round(region.target_flow_rate, 4),
            "viscosity": round(region.viscosity, 4),
            "density": round(region.density, 4),
            "pressure": round(region.pressure, 4),
            "is_eddy_active": region.is_eddy_active,
            "eddy_rotations": region.eddy_rotations,
            "current_count": len(region.currents),
            "elapsed_game_time": round(region.elapsed_game_time, 2),
            "flow_changes": region.flow_changes,
            "created_at": region.created_at,
            "last_updated": region.last_updated,
        }

    def _current_to_dict(self, current: TemporalCurrent) -> Dict[str, Any]:
        return {
            "current_id": current.current_id,
            "source_id": current.source_id,
            "target_id": current.target_id,
            "flow_differential": round(current.flow_differential, 4),
            "direction": round(current.direction, 4),
            "timestamp": current.timestamp,
        }

    def _event_to_dict(self, event: TemporalEventRecord) -> Dict[str, Any]:
        return {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "region_id": event.region_id,
            "region_label": event.region_label,
            "old_flow_rate": event.old_flow_rate,
            "new_flow_rate": event.new_flow_rate,
            "description": event.description,
            "timestamp": event.timestamp,
        }
