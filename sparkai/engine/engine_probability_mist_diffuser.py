"""
Engine Probability Mist Diffuser
================================"""

from __future__ import annotations

import math
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# Enums
# =============================================================================

class MistType(Enum):
    """Types of probability mist, ordered by uncertainty intensity."""
    FOG = "fog"          # ambient low uncertainty
    HAZE = "haze"        # medium uncertainty
    VAPOR = "vapor"      # high uncertainty
    STEAM = "steam"      # action-triggered uncertainty
    ETHER = "ether"      # mystical quantum uncertainty


class MistPhase(Enum):
    """Phases of the probability mist cycle."""
    EVAPORATE = "evaporate"
    DIFFUSE = "diffuse"
    CONDENSE = "condense"
    PRECIPITATE = "precipitate"
    DISSIPATE = "dissipate"


class MistEvent(Enum):
    """Events that occur during the mist cycle."""
    MIST_SURGE = "mist_surge"                # sudden uncertainty influx
    CLARITY_BURST = "clarity_burst"          # rapid condensation
    DENSITY_INVERSION = "density_inversion"  # heavy mist rises
    FOG_BANK = "fog_bank"                    # large stable formation
    VAPOR_LOCK = "vapor_lock"               # mist trapped
    ETHER_STORM = "ether_storm"             # quantum chaos


# =============================================================================
# Default Parameters by Mist Type
# =============================================================================

# Default density (uncertainty level) for each mist type
DEFAULT_MIST_DENSITY: Dict[MistType, float] = {
    MistType.FOG: 0.2,
    MistType.HAZE: 0.4,
    MistType.VAPOR: 0.6,
    MistType.STEAM: 0.75,
    MistType.ETHER: 0.9,
}

# Default viscosity (resistance to flow) for each mist type
DEFAULT_MIST_VISCOSITY: Dict[MistType, float] = {
    MistType.FOG: 0.3,    # flows easily
    MistType.HAZE: 0.45,
    MistType.VAPOR: 0.55,
    MistType.STEAM: 0.4,  # forceful but flows
    MistType.ETHER: 0.8,  # resists normal flow
}

# Default volatility (how quickly density changes) for each mist type
DEFAULT_MIST_VOLATILITY: Dict[MistType, float] = {
    MistType.FOG: 0.1,
    MistType.HAZE: 0.2,
    MistType.VAPOR: 0.35,
    MistType.STEAM: 0.5,
    MistType.ETHER: 0.7,
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class MistRegion:
    """A region of the game world containing probability mist."""
    region_id: str
    label: str
    # Type of mist in this region
    mist_type: MistType
    # Current mist density (uncertainty level, 0.0-1.0)
    density: float
    # Target density the region is moving toward
    target_density: float
    # Viscosity (resistance to diffusion)
    viscosity: float
    # Volatility (rate of density change)
    volatility: float
    # Saturation point where condensation begins
    saturation_point: float
    # Accumulated certainty droplets ready to precipitate
    certainty_droplets: float
    # Whether this region is an active uncertainty source
    is_source: bool
    last_updated: float = field(default_factory=time.time)


@dataclass
class MistChannel:
    """A diffusion channel connecting two mist regions."""
    channel_id: str
    source_id: str
    target_id: str
    # Flow rate of mist through this channel (0.0-1.0)
    flow_rate: float
    # Pressure differential driving the flow
    pressure: float
    # Whether flow is currently blocked
    blocked: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class PrecipitationOutcome:
    """A concrete outcome precipitated from condensed certainty."""
    outcome_id: str
    region_id: str
    # Type of outcome (decision, loot, event, etc.)
    outcome_type: str
    # Certainty/confidence level of the outcome (0.0-1.0)
    certainty: float
    # Description of the precipitated outcome
    description: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class MistEventRecord:
    """A recorded mist event."""
    event_id: str
    event_type: MistEvent
    intensity: float
    region_ids: List[str]
    density_delta: float
    description: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class MistStats:
    """Aggregate statistics for the mist diffuser."""
    total_regions: int = 0
    total_channels: int = 0
    total_outcomes: int = 0
    total_events: int = 0
    total_mist_surges: int = 0
    total_clarity_bursts: int = 0
    total_density_inversions: int = 0
    total_fog_banks: int = 0
    total_vapor_locks: int = 0
    total_ether_storms: int = 0
    avg_density: float = 0.0
    avg_viscosity: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Main Class
# =============================================================================

class EngineProbabilityMistDiffuser:
    """Diffuses probability mist through the game world.

    Models uncertainty as a flowing mist that evaporates from sources,
    diffuses through channels, condenses into certainty, and precipitates
    as concrete outcomes.
    """

    _instance: Optional["EngineProbabilityMistDiffuser"] = None
    _instance_lock = threading.Lock()

    # Configuration constants
    MAX_REGIONS = 100
    MAX_CHANNELS = 200
    MAX_OUTCOMES = 150
    MAX_EVENT_HISTORY = 200
    MIN_DENSITY = 0.0
    MAX_DENSITY = 1.0
    MIN_VISCOSITY = 0.0
    MAX_VISCOSITY = 1.0
    DIFFUSION_RATE = 0.12
    NATURAL_DENSITY_DECAY = 0.04
    EVAPORATION_RATE = 0.15
    CONDENSATION_THRESHOLD = 0.8
    PRECIPITATION_THRESHOLD = 0.5
    CLARITY_BURST_THRESHOLD = 0.9
    FOG_BANK_THRESHOLD = 0.6
    VAPOR_LOCK_THRESHOLD = 0.85
    ETHER_STORM_THRESHOLD = 0.95
    DENSITY_INVERSION_DIFF = 0.3
    MAX_CHANNELS_PER_REGION = 8

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._regions: Dict[str, MistRegion] = {}
        self._channels: Dict[str, MistChannel] = {}
        # Adjacency: region_id -> list of connected region_ids
        self._adjacency: Dict[str, List[str]] = {}
        self._outcomes: List[PrecipitationOutcome] = []
        self._event_history: List[MistEventRecord] = []
        self._stats = MistStats()
        self._cycle_count: int = 0
        self._active: bool = False

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineProbabilityMistDiffuser":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Region Management
    # -------------------------------------------------------------------------

    def register_region(
        self,
        region_id: str,
        label: str,
        mist_type: str = "fog",
        density: Optional[float] = None,
        viscosity: Optional[float] = None,
        volatility: Optional[float] = None,
        is_source: bool = False,
    ) -> Dict[str, Any]:
        """Register a new mist region in the probability field."""
        with self._lock:
            if region_id in self._regions:
                return {"error": f"Region already registered: {region_id}"}
            if len(self._regions) >= self.MAX_REGIONS:
                return {"error": "Maximum regions reached"}

            try:
                mtype = MistType(mist_type)
            except ValueError:
                return {"error": f"Unknown mist type: {mist_type}"}

            if density is None:
                density = DEFAULT_MIST_DENSITY.get(mtype, 0.3)
            density = max(self.MIN_DENSITY, min(self.MAX_DENSITY, float(density)))

            if viscosity is None:
                viscosity = DEFAULT_MIST_VISCOSITY.get(mtype, 0.5)
            viscosity = max(
                self.MIN_VISCOSITY, min(self.MAX_VISCOSITY, float(viscosity))
            )

            if volatility is None:
                volatility = DEFAULT_MIST_VOLATILITY.get(mtype, 0.2)
            volatility = max(0.0, min(1.0, float(volatility)))

            region = MistRegion(
                region_id=region_id,
                label=label,
                mist_type=mtype,
                density=density,
                target_density=density,
                viscosity=viscosity,
                volatility=volatility,
                saturation_point=self.CONDENSATION_THRESHOLD,
                certainty_droplets=0.0,
                is_source=is_source,
            )
            self._regions[region_id] = region
            self._adjacency[region_id] = []
            self._stats.total_regions = len(self._regions)
            return self._region_to_dict(region)

    def get_region(self, region_id: str) -> Dict[str, Any]:
        """Get the state of a mist region."""
        with self._lock:
            region = self._regions.get(region_id)
            if region is None:
                return {"error": f"Region not found: {region_id}"}
            return self._region_to_dict(region)

    def list_regions(self) -> List[Dict[str, Any]]:
        """List all mist regions."""
        with self._lock:
            return [self._region_to_dict(r) for r in self._regions.values()]

    def remove_region(self, region_id: str) -> Dict[str, Any]:
        """Remove a mist region and its channels."""
        with self._lock:
            if region_id not in self._regions:
                return {"removed": False}
            del self._regions[region_id]
            # Remove channels referencing this region
            for cid in list(self._channels.keys()):
                channel = self._channels[cid]
                if channel.source_id == region_id or channel.target_id == region_id:
                    del self._channels[cid]
            # Clean adjacency
            self._adjacency.pop(region_id, None)
            for rid in self._adjacency:
                if region_id in self._adjacency[rid]:
                    self._adjacency[rid] = [
                        r for r in self._adjacency[rid] if r != region_id
                    ]
            self._stats.total_regions = len(self._regions)
            self._stats.total_channels = len(self._channels)
            return {"removed": True, "region_id": region_id}

    def set_region_density(
        self, region_id: str, density: float, description: str = ""
    ) -> Dict[str, Any]:
        """Set the target density (uncertainty level) of a region."""
        with self._lock:
            region = self._regions.get(region_id)
            if region is None:
                return {"error": f"Region not found: {region_id}"}
            old_density = region.target_density
            new_density = max(
                self.MIN_DENSITY, min(self.MAX_DENSITY, float(density))
            )
            region.target_density = new_density
            region.last_updated = time.time()

            # Record events based on density change
            event_type: Optional[MistEvent] = None
            if new_density >= self.ETHER_STORM_THRESHOLD and old_density < self.ETHER_STORM_THRESHOLD:
                event_type = MistEvent.ETHER_STORM
                self._stats.total_ether_storms += 1
            elif new_density >= self.CLARITY_BURST_THRESHOLD and old_density < self.CLARITY_BURST_THRESHOLD:
                # High density can trigger clarity burst (saturation)
                event_type = MistEvent.CLARITY_BURST
                self._stats.total_clarity_bursts += 1
            elif new_density - old_density >= 0.3:
                event_type = MistEvent.MIST_SURGE
                self._stats.total_mist_surges += 1

            if event_type is not None:
                self._record_event(
                    event_type,
                    abs(new_density - old_density),
                    [region_id],
                    new_density - old_density,
                    description,
                )

            return self._region_to_dict(region)

    # -------------------------------------------------------------------------
    # Channel Management
    # -------------------------------------------------------------------------

    def link_regions(
        self, source_id: str, target_id: str, flow_rate: float = 0.5
    ) -> Dict[str, Any]:
        """Create a diffusion channel between two regions."""
        with self._lock:
            if source_id not in self._regions:
                return {"error": f"Source region not found: {source_id}"}
            if target_id not in self._regions:
                return {"error": f"Target region not found: {target_id}"}
            if source_id == target_id:
                return {"error": "Cannot link region to itself"}

            # Check for existing channel
            for channel in self._channels.values():
                if channel.source_id == source_id and channel.target_id == target_id:
                    channel.flow_rate = max(0.0, min(1.0, flow_rate))
                    return {"channel": self._channel_to_dict(channel)}

            channel_id = f"ch_{source_id}_{target_id}_{int(time.time() * 1000)}"
            channel = MistChannel(
                channel_id=channel_id,
                source_id=source_id,
                target_id=target_id,
                flow_rate=max(0.0, min(1.0, float(flow_rate))),
                pressure=0.0,
                blocked=False,
            )
            self._channels[channel_id] = channel
            if target_id not in self._adjacency[source_id]:
                self._adjacency[source_id].append(target_id)
            self._stats.total_channels = len(self._channels)
            return {"channel": self._channel_to_dict(channel)}

    def unlink_regions(self, source_id: str, target_id: str) -> Dict[str, Any]:
        """Remove a diffusion channel between two regions."""
        with self._lock:
            removed = 0
            for cid in list(self._channels.keys()):
                channel = self._channels[cid]
                if channel.source_id == source_id and channel.target_id == target_id:
                    del self._channels[cid]
                    removed += 1
            if target_id in self._adjacency.get(source_id, []):
                self._adjacency[source_id].remove(target_id)
            self._stats.total_channels = len(self._channels)
            return {
                "removed": removed,
                "source_id": source_id,
                "target_id": target_id,
            }

    def get_channels(self, region_id: str) -> Dict[str, Any]:
        """Get all diffusion channels for a region."""
        with self._lock:
            if region_id not in self._regions:
                return {"error": f"Region not found: {region_id}"}
            outgoing = []
            incoming = []
            for channel in self._channels.values():
                if channel.source_id == region_id:
                    outgoing.append(self._channel_to_dict(channel))
                if channel.target_id == region_id:
                    incoming.append(self._channel_to_dict(channel))
            return {
                "region_id": region_id,
                "outgoing": outgoing,
                "incoming": incoming,
                "total": len(outgoing) + len(incoming),
            }

    # -------------------------------------------------------------------------
    # Mist Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single probability mist cycle.

        Phases: EVAPORATE -> DIFFUSE -> CONDENSE -> PRECIPITATE -> DISSIPATE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: EVAPORATE - uncertainty rises from sources
            evaporate_info = self._evaporate_phase()

            # Phase 2: DIFFUSE - mist spreads through channels
            diffuse_info = self._diffuse_phase()

            # Phase 3: CONDENSE - mist forms certainty droplets
            condense_info = self._condense_phase()

            # Phase 4: PRECIPITATE - certainty falls as outcomes
            precipitate_info = self._precipitate_phase()

            # Phase 5: DISSIPATE - residual uncertainty fades
            dissipate_info = self._dissipate_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()

            phase = MistPhase.DISSIPATE
            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "evaporate": evaporate_info,
                "diffuse": diffuse_info,
                "condense": condense_info,
                "precipitate": precipitate_info,
                "dissipate": dissipate_info,
                "total_regions": len(self._regions),
                "total_channels": len(self._channels),
                "total_outcomes": len(self._outcomes),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _evaporate_phase(self) -> Dict[str, Any]:
        """Phase 1: Uncertainty evaporates from sources into regions."""
        sources_active = 0
        total_added = 0.0
        for region in self._regions.values():
            if region.is_source:
                # Sources generate mist
                added = self.EVAPORATION_RATE * (1.0 - region.viscosity * 0.3)
                region.density = min(self.MAX_DENSITY, region.density + added)
                total_added += added
                sources_active += 1
            # Move density toward target
            diff = region.target_density - region.density
            region.density += diff * region.volatility * 0.3
            region.density = max(
                self.MIN_DENSITY, min(self.MAX_DENSITY, region.density)
            )
        return {
            "sources_active": sources_active,
            "total_density_added": round(total_added, 4),
        }

    def _diffuse_phase(self) -> Dict[str, Any]:
        """Phase 2: Mist diffuses through channels based on pressure."""
        diffused = 0
        total_flow = 0.0
        inversions = 0
        vapor_locks = 0

        for channel in self._channels.values():
            if channel.blocked:
                continue
            source = self._regions.get(channel.source_id)
            target = self._regions.get(channel.target_id)
            if source is None or target is None:
                continue

            # Pressure = density differential
            pressure = source.density - target.density
            channel.pressure = pressure

            # Check for density inversion (heavy mist below light mist)
            if (
                pressure < -self.DENSITY_INVERSION_DIFF
                and source.mist_type.value > target.mist_type.value
            ):
                self._record_event(
                    MistEvent.DENSITY_INVERSION,
                    abs(pressure),
                    [channel.source_id, channel.target_id],
                    pressure,
                    f"Density inversion: {source.label} -> {target.label}",
                )
                inversions += 1
                # Inversion causes reverse flow
                pressure = abs(pressure) * 0.5

            # Flow amount depends on pressure, flow rate, and viscosities
            avg_viscosity = (source.viscosity + target.viscosity) / 2.0
            flow = (
                pressure
                * channel.flow_rate
                * self.DIFFUSION_RATE
                * (1.0 - avg_viscosity * 0.4)
            )

            if flow > 0:
                source.density -= flow
                target.density += flow
                total_flow += flow
                diffused += 1

            # Vapor lock: high density region with no outflow
            if (
                source.density >= self.VAPOR_LOCK_THRESHOLD
                and source.viscosity >= 0.7
                and not any(
                    self._regions.get(c.target_id)
                    and self._regions[c.target_id].density < source.density
                    for c in self._channels.values()
                    if c.source_id == channel.source_id and not c.blocked
                )
            ):
                self._record_event(
                    MistEvent.VAPOR_LOCK,
                    source.density,
                    [channel.source_id],
                    0.0,
                    f"Vapor lock in {source.label}",
                )
                vapor_locks += 1

        # Fog bank: stable high-density region
        for region in self._regions.values():
            if (
                region.density >= self.FOG_BANK_THRESHOLD
                and region.viscosity >= 0.5
                and random.random() < 0.05
            ):
                self._record_event(
                    MistEvent.FOG_BANK,
                    region.density,
                    [region.region_id],
                    0.0,
                    f"Fog bank formed in {region.label}",
                )

        return {
            "channels_active": diffused,
            "total_flow": round(total_flow, 4),
            "density_inversions": inversions,
            "vapor_locks": vapor_locks,
        }

    def _condense_phase(self) -> Dict[str, Any]:
        """Phase 3: Mist condenses into certainty droplets at saturation."""
        condensed = 0
        total_droplets = 0.0
        for region in self._regions.values():
            if region.density >= region.saturation_point:
                # Condensation rate depends on how far above saturation
                excess = region.density - region.saturation_point
                droplets = excess * (1.0 - region.viscosity * 0.3)
                region.certainty_droplets += droplets
                region.density -= droplets * 0.5  # Partial density reduction
                region.density = max(
                    self.MIN_DENSITY, min(self.MAX_DENSITY, region.density)
                )
                total_droplets += droplets
                condensed += 1

                # Clarity burst: rapid condensation
                if droplets > self.CLARITY_BURST_THRESHOLD * 0.3:
                    self._record_event(
                        MistEvent.CLARITY_BURST,
                        droplets,
                        [region.region_id],
                        -droplets,
                        f"Clarity burst in {region.label}",
                    )
        return {
            "regions_condensed": condensed,
            "total_droplets": round(total_droplets, 4),
        }

    def _precipitate_phase(self) -> Dict[str, Any]:
        """Phase 4: Certainty droplets precipitate as concrete outcomes."""
        precipitated = 0
        for region in list(self._regions.values()):
            if region.certainty_droplets >= self.PRECIPITATION_THRESHOLD:
                # Determine outcome type based on mist type
                outcome_types = {
                    MistType.FOG: "ambient_event",
                    MistType.HAZE: "minor_decision",
                    MistType.VAPOR: "major_decision",
                    MistType.STEAM: "action_trigger",
                    MistType.ETHER: "quantum_event",
                }
                outcome_type = outcome_types.get(region.mist_type, "generic")
                certainty = min(1.0, region.certainty_droplets)
                outcome = PrecipitationOutcome(
                    outcome_id=(
                        f"outcome_{region.region_id}_{int(time.time() * 1000)}"
                        f"_{random.randint(0, 999)}"
                    ),
                    region_id=region.region_id,
                    outcome_type=outcome_type,
                    certainty=certainty,
                    description=f"{outcome_type} precipitated in {region.label}",
                )
                self._outcomes.append(outcome)
                if len(self._outcomes) > self.MAX_OUTCOMES:
                    self._outcomes.pop(0)
                region.certainty_droplets = 0.0
                precipitated += 1
                self._stats.total_outcomes = len(self._outcomes)
        return {
            "outcomes_precipitated": precipitated,
            "total_outcomes": len(self._outcomes),
        }

    def _dissipate_phase(self) -> Dict[str, Any]:
        """Phase 5: Residual uncertainty fades away."""
        total_decayed = 0.0
        for region in self._regions.values():
            if not region.is_source:
                decay = self.NATURAL_DENSITY_DECAY * (1.0 - region.viscosity * 0.5)
                old_density = region.density
                region.density = max(self.MIN_DENSITY, region.density - decay)
                total_decayed += old_density - region.density
            region.last_updated = time.time()
        return {
            "total_density_decayed": round(total_decayed, 4),
        }

    # -------------------------------------------------------------------------
    # Event Recording
    # -------------------------------------------------------------------------

    def _record_event(
        self,
        event_type: MistEvent,
        intensity: float,
        region_ids: List[str],
        density_delta: float,
        description: str = "",
    ) -> Dict[str, Any]:
        """Record a mist event."""
        event = MistEventRecord(
            event_id=f"evt_{int(time.time() * 1000)}_{random.randint(0, 9999)}",
            event_type=event_type,
            intensity=max(0.0, min(1.0, float(intensity))),
            region_ids=region_ids,
            density_delta=float(density_delta),
            description=description,
        )
        self._event_history.append(event)
        if len(self._event_history) > self.MAX_EVENT_HISTORY:
            self._event_history.pop(0)

        self._stats.total_events += 1
        if event_type == MistEvent.MIST_SURGE:
            self._stats.total_mist_surges += 1
        elif event_type == MistEvent.CLARITY_BURST:
            self._stats.total_clarity_bursts += 1
        elif event_type == MistEvent.DENSITY_INVERSION:
            self._stats.total_density_inversions += 1
        elif event_type == MistEvent.FOG_BANK:
            self._stats.total_fog_banks += 1
        elif event_type == MistEvent.VAPOR_LOCK:
            self._stats.total_vapor_locks += 1
        elif event_type == MistEvent.ETHER_STORM:
            self._stats.total_ether_storms += 1
        return self._event_to_dict(event)

    def get_events(
        self, region_id: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent mist events, optionally filtered by region."""
        with self._lock:
            results = []
            for event in reversed(self._event_history):
                if region_id is not None and region_id not in event.region_ids:
                    continue
                results.append(self._event_to_dict(event))
                if len(results) >= limit:
                    break
            return results

    def get_outcomes(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get precipitated outcomes."""
        with self._lock:
            results = [self._outcome_to_dict(o) for o in self._outcomes]
            results.sort(key=lambda d: d.get("timestamp", 0), reverse=True)
            return results[:limit]

    # -------------------------------------------------------------------------
    # Simulation & Status
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles and return a summary."""
        cycles = max(1, min(100, int(cycles)))
        results: List[Dict[str, Any]] = []
        with self._lock:
            for _ in range(cycles):
                results.append(self.run_cycle())
        last = results[-1] if results else {}
        return {
            "cycles_run": len(results),
            "last_cycle": last,
            "status": self.get_status(),
        }

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the mist diffuser."""
        with self._lock:
            return {
                "total_regions": len(self._regions),
                "total_channels": len(self._channels),
                "total_outcomes": len(self._outcomes),
                "active": self._stats.active,
                "cycle_count": self._cycle_count,
                "stats": {
                    "total_events": self._stats.total_events,
                    "total_mist_surges": self._stats.total_mist_surges,
                    "total_clarity_bursts": self._stats.total_clarity_bursts,
                    "total_density_inversions": self._stats.total_density_inversions,
                    "total_fog_banks": self._stats.total_fog_banks,
                    "total_vapor_locks": self._stats.total_vapor_locks,
                    "total_ether_storms": self._stats.total_ether_storms,
                    "avg_density": round(self._stats.avg_density, 4),
                    "avg_viscosity": round(self._stats.avg_viscosity, 4),
                    "last_cycle_time_ms": self._stats.last_cycle_time_ms,
                },
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the mist diffuser to its initial state."""
        with self._lock:
            self._regions.clear()
            self._channels.clear()
            self._adjacency.clear()
            self._outcomes.clear()
            self._event_history.clear()
            self._stats = MistStats()
            self._cycle_count = 0
            self._active = False
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Serialization Helpers
    # -------------------------------------------------------------------------

    def _update_avg_metrics(self) -> None:
        """Update running average metrics."""
        if self._regions:
            total_density = sum(r.density for r in self._regions.values())
            total_viscosity = sum(r.viscosity for r in self._regions.values())
            self._stats.avg_density = total_density / len(self._regions)
            self._stats.avg_viscosity = total_viscosity / len(self._regions)

    def _region_to_dict(self, region: MistRegion) -> Dict[str, Any]:
        return {
            "region_id": region.region_id,
            "label": region.label,
            "mist_type": region.mist_type.value,
            "density": round(region.density, 4),
            "target_density": round(region.target_density, 4),
            "viscosity": round(region.viscosity, 4),
            "volatility": round(region.volatility, 4),
            "saturation_point": round(region.saturation_point, 4),
            "certainty_droplets": round(region.certainty_droplets, 4),
            "is_source": region.is_source,
            "last_updated": region.last_updated,
        }

    def _channel_to_dict(self, channel: MistChannel) -> Dict[str, Any]:
        return {
            "channel_id": channel.channel_id,
            "source_id": channel.source_id,
            "target_id": channel.target_id,
            "flow_rate": round(channel.flow_rate, 4),
            "pressure": round(channel.pressure, 4),
            "blocked": channel.blocked,
            "timestamp": channel.timestamp,
        }

    def _outcome_to_dict(self, outcome: PrecipitationOutcome) -> Dict[str, Any]:
        return {
            "outcome_id": outcome.outcome_id,
            "region_id": outcome.region_id,
            "outcome_type": outcome.outcome_type,
            "certainty": round(outcome.certainty, 4),
            "description": outcome.description,
            "timestamp": outcome.timestamp,
        }

    def _event_to_dict(self, event: MistEventRecord) -> Dict[str, Any]:
        return {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "intensity": round(event.intensity, 4),
            "region_ids": event.region_ids,
            "density_delta": round(event.density_delta, 4),
            "description": event.description,
            "timestamp": event.timestamp,
        }
