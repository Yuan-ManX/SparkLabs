"""
SparkLabs Engine - Liquid Narrative Foundry"""

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

class LiquidNarrativePhase(Enum):
    """Phases of the liquid narrative foundry cycle."""
    INJECT_DROPLET = "inject_droplet"      # inject narrative droplets into channels at source points
    FLOW_CHANNELS = "flow_channels"        # flow droplets through channels according to gradient/viscosity
    SETTLE_POOLS = "settle_pools"          # settle accumulated droplets into pools; measure pool depth/tension
    COMPUTE_FLUX = "compute_flux"          # compute evaporation of stale threads and overflow of overfull pools
    EMIT_FLUID_MAP = "emit_fluid_map"      # emit the fluid narrative map with channels, pools, flux for the editor


class DropletKind(Enum):
    """The kind of narrative droplet flowing through a channel."""
    BEAT = "beat"                    # a single story beat
    REVEAL = "reveal"                # a reveal droplet
    CONFLICT = "conflict"           # a conflict droplet
    RESOLUTION = "resolution"       # a resolution droplet
    FORESHADOW = "foreshadow"       # a foreshadow droplet


class ChannelGradient(Enum):
    """The hydraulic gradient of a narrative channel (downhill = toward consequence)."""
    DOWNHILL = "downhill"            # strong flow toward consequence
    FLAT = "flat"                    # meandering flow
    UPHILL = "uphill"                # resisted flow, building tension
    CASCADING = "cascading"          # steep multi-step drop
    POOLING = "pooling"              # gathers into a basin


class PoolTension(Enum):
    """The tension state of a settled narrative pool."""
    DORMANT = "dormant"              # calm standing pool
    SIMMERING = "simmering"         # building tension
    ACTIVE = "active"                # active unresolved tension
    OVERFULL = "overfull"            # about to overflow


class FluxKind(Enum):
    """The kind of flux event computed against pools and droplets."""
    EVAPORATION = "evaporation"      # stale thread forgotten
    OVERFLOW = "overflow"            # overfull pool cascades into a new plot event
    SEEPAGE = "seepage"              # slow leak between basins
    CASCADE = "cascade"              # cascading plot event from overflow


class ChannelState(Enum):
    """State of an individual narrative channel through the cycle."""
    PENDING = "pending"              # registered but not yet processed
    REGISTERED = "registered"        # confirmed and classified
    FLOWING = "flowing"              # droplets flowing through the channel
    POOLED = "pooled"                # droplets settled into pools
    FLUXED = "fluxed"                # evaporation/overflow computed
    EMITTED = "emitted"              # emitted into the fluid narrative map


class Vitality(Enum):
    """Overall vitality of the liquid narrative ecosystem."""
    DRY = "dry"
    TRICKLING = "trickling"
    FLOWING = "flowing"
    TURBULENT = "turbulent"
    FLOODED = "flooded"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NarrativeChannel:
    """A narrative channel through which droplets flow."""
    channel_id: str
    channel_handle: str
    label: str
    gradient: ChannelGradient = ChannelGradient.DOWNHILL
    viscosity: float = 0.5                            # 0.0-1.0, how easily a thread changes course
    source_point: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    capacity: float = 10.0                            # how much narrative the channel can carry
    turbulence: float = 0.0                          # 0.0-1.0, narrative churn
    active: bool = True
    state: ChannelState = ChannelState.PENDING
    vitality: Vitality = Vitality.DRY
    created_at: float = field(default_factory=time.time)
    last_flowed_at: float = 0.0
    note: str = ""


@dataclass
class NarrativeDroplet:
    """A narrative droplet flowing through a channel."""
    droplet_id: str
    channel_id: str
    content: str
    kind: DropletKind = DropletKind.BEAT
    flow_distance: float = 0.0                        # how far the droplet has flowed
    flow_rate: float = 1.0                            # rate of flow per cycle
    weight: float = 1.0                               # narrative weight / consequence
    pooled: bool = False
    state: str = "injected"
    created_at: float = field(default_factory=time.time)


@dataclass
class NarrativePool:
    """A basin where accumulated droplets settle as unresolved tension."""
    pool_id: str
    channel_id: str
    depth: float = 0.0                                # accumulated droplet weight
    tension: PoolTension = PoolTension.DORMANT
    droplet_count: int = 0
    capacity: float = 10.0
    state: str = "settled"
    created_at: float = field(default_factory=time.time)


# =============================================================================
# Foundry
# =============================================================================

class LiquidNarrativeFoundry:
    """
    Thread-safe singleton that casts narrative as a fluid flowing through
    channels, pools, and basins of the world.

    Narrative channels are keyed internally by channel_handle so that each
    logical channel owns exactly one entry. The channel_id is a generated
    handle for external lookups; lookups by channel_id fall back to a linear
    scan of the registered channels.

    Usage:
        foundry = LiquidNarrativeFoundry.get_instance()
        foundry.register_channel(
            channel_handle="ch::main_arc",
            label="Main Arc",
            gradient="downhill",
            viscosity=0.4,
            source_point={"x": 0.0, "y": 0.0, "z": 0.0},
        )
        foundry.cycle()
        channel = foundry.get_channel(channel_id)
        fluid_map = foundry.get_fluid_map()
    """

    _instance: Optional["LiquidNarrativeFoundry"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Capacity caps.
    _MAX_CHANNELS = 60
    _MAX_EVENTS = 200
    _MAX_DROPLETS = 240
    _MAX_POOLS = 120
    _MAX_FLUX_EVENTS = 200

    # Domain tuning constants.
    _VISCOSITY_MIN = 0.0
    _VISCOSITY_MAX = 1.0
    _FLOW_RATE_BASE = 1.0          # base flow rate per cycle
    _FLOW_GRADIENT_FACTOR = 2.0    # gradient multiplier on flow rate
    _EVAPORATION_AGE_CYCLES = 3   # droplets older than this evaporate if pooled and stale
    _POOL_OVERFULL_FRACTION = 0.9  # pool depth above this fraction of capacity is overfull
    _TURBULENCE_PER_DROPLET = 0.05
    _VITALITY_FLOWING_FRACTION = 0.4
    _VITALITY_TURBULENT_FRACTION = 0.7

    # Source-point labels available for synthetic seeding.
    _SOURCE_LABELS = (
        "origin", "inciting_incident", "rising_action", "midpoint", "climax_foothills",
    )

    def __init__(self) -> None:
        # Internal dict keyed by channel_handle (NOT channel_id).
        self._channels: Dict[str, NarrativeChannel] = {}
        self._droplets: Dict[str, NarrativeDroplet] = {}
        self._pools: Dict[str, NarrativePool] = {}
        self._flux_events: Dict[str, Dict[str, Any]] = {}
        self._phase: LiquidNarrativePhase = LiquidNarrativePhase.INJECT_DROPLET
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._channels:
            self._seed_synthetic_channels()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "LiquidNarrativeFoundry":
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
            "channels_registered": 0,
            "phase_runs": 0,
            "droplets_injected": 0,
            "pools_settled": 0,
            "flux_events_computed": 0,
            "fluid_maps_emitted": 0,
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
    def _parse_gradient(value: Any) -> ChannelGradient:
        """Parse a ChannelGradient from a string, enum, or None."""
        if value is None:
            return ChannelGradient.DOWNHILL
        if isinstance(value, ChannelGradient):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for gradient in ChannelGradient:
                if gradient.value == lowered:
                    return gradient
        return ChannelGradient.DOWNHILL

    @staticmethod
    def _parse_droplet_kind(value: Any) -> DropletKind:
        """Parse a DropletKind from a string, enum, or None."""
        if value is None:
            return DropletKind.BEAT
        if isinstance(value, DropletKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in DropletKind:
                if kind.value == lowered:
                    return kind
        return DropletKind.BEAT

    @staticmethod
    def _parse_source_point(value: Any) -> Dict[str, float]:
        """Parse a source_point dict from input, defaulting to origin."""
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

    def _classify_turbulence(self, droplet_count: int) -> float:
        """Classify channel turbulence from droplet population."""
        return min(1.0, droplet_count * self._TURBULENCE_PER_DROPLET)

    def _compute_flow_rate(self, gradient: ChannelGradient, viscosity: float) -> float:
        """Compute the flow rate of a droplet given channel gradient and viscosity."""
        gradient_factor = {
            ChannelGradient.DOWNHILL: 1.0,
            ChannelGradient.FLAT: 0.5,
            ChannelGradient.UPHILL: 0.2,
            ChannelGradient.CASCADING: 1.5,
            ChannelGradient.POOLING: 0.1,
        }.get(gradient, 0.5)
        visc = max(self._VISCOSITY_MIN, min(self._VISCOSITY_MAX, viscosity))
        # Higher viscosity resists flow.
        return self._FLOW_RATE_BASE * gradient_factor * self._FLOW_GRADIENT_FACTOR * (1.0 - visc * 0.5)

    def _classify_pool_tension(self, depth: float, capacity: float) -> PoolTension:
        """Classify pool tension from depth and capacity."""
        ratio = depth / max(capacity, 0.001)
        if ratio >= self._POOL_OVERFULL_FRACTION:
            return PoolTension.OVERFULL
        if ratio >= 0.5:
            return PoolTension.ACTIVE
        if ratio >= 0.2:
            return PoolTension.SIMMERING
        return PoolTension.DORMANT

    def _color_for_gradient(self, gradient: ChannelGradient) -> str:
        """Map a channel gradient to a preview color for the editor overlay."""
        if gradient == ChannelGradient.DOWNHILL:
            return "#1E90FF"  # dodger blue - strong flow
        if gradient == ChannelGradient.FLAT:
            return "#20B2AA"  # light sea green - meandering
        if gradient == ChannelGradient.UPHILL:
            return "#FF8C00"  # dark orange - resisted flow
        if gradient == ChannelGradient.CASCADING:
            return "#8A2BE2"  # blue violet - cascading drop
        return "#4682B4"  # steel blue - pooling basin

    def _color_for_tension(self, tension: PoolTension) -> str:
        """Map a pool tension to a preview color for the editor overlay."""
        if tension == PoolTension.DORMANT:
            return "#2F4F4F"  # dark slate gray - calm
        if tension == PoolTension.SIMMERING:
            return "#CD853F"  # peru - building
        if tension == PoolTension.ACTIVE:
            return "#FF4500"  # orange red - active tension
        return "#8B0000"  # dark red - overfull, about to overflow

    # -------------------------------------------------------------------------
    # Channel Management
    # -------------------------------------------------------------------------

    def register_channel(
        self,
        channel_handle: str,
        label: str,
        gradient: Optional[str] = None,
        viscosity: float = 0.5,
        source_point: Optional[Dict[str, float]] = None,
        capacity: float = 10.0,
    ) -> Dict[str, Any]:
        """Register a new narrative channel for fluid narrative projection."""
        with self._global_lock:
            if channel_handle in self._channels:
                return {"error": f"Channel already registered: {channel_handle}"}
            if len(self._channels) >= self._MAX_CHANNELS:
                return {"error": f"Channel cap reached ({self._MAX_CHANNELS})"}

            channel_id = f"ch_{channel_handle}_{int(time.time() * 1000)}_{random.randint(100, 999)}"

            visc = max(self._VISCOSITY_MIN, min(self._VISCOSITY_MAX, float(viscosity)))
            cap = max(1.0, float(capacity))
            parsed_gradient = self._parse_gradient(gradient)
            sp = self._parse_source_point(source_point)

            channel = NarrativeChannel(
                channel_id=channel_id,
                channel_handle=channel_handle,
                label=label,
                gradient=parsed_gradient,
                viscosity=visc,
                source_point=sp,
                capacity=cap,
                turbulence=0.0,
                active=True,
                state=ChannelState.PENDING,
                vitality=Vitality.DRY,
                created_at=time.time(),
                last_flowed_at=0.0,
                note="",
            )
            self._channels[channel_handle] = channel
            self._update_stats(channels_registered=1)
            self._record_event("channel_registered", {
                "channel_id": channel_id,
                "channel_handle": channel_handle,
                "label": label,
                "gradient": parsed_gradient.value,
                "viscosity": visc,
                "capacity": cap,
            })
            return {
                "channel_id": channel_id,
                "channel_handle": channel_handle,
                "label": label,
                "gradient": parsed_gradient.value,
                "viscosity": visc,
                "capacity": cap,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single liquid narrative foundry cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic channels on the very first cycle if none exist.
            if not self._channels and self._cycle_count == 0:
                self._seed_synthetic_channels()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = LiquidNarrativePhase.INJECT_DROPLET
            phase_outputs.append(self._phase_inject_droplet())
            self._phase = LiquidNarrativePhase.FLOW_CHANNELS
            phase_outputs.append(self._phase_flow_channels())
            self._phase = LiquidNarrativePhase.SETTLE_POOLS
            phase_outputs.append(self._phase_settle_pools())
            self._phase = LiquidNarrativePhase.COMPUTE_FLUX
            phase_outputs.append(self._phase_compute_flux())
            self._phase = LiquidNarrativePhase.EMIT_FLUID_MAP
            phase_outputs.append(self._phase_emit_fluid_map())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_inject_droplet(self) -> Dict[str, Any]:
        """Inject phase: inject narrative droplets into channels at source points."""
        injected = 0
        droplet_kinds_pool = list(DropletKind)
        for channel in self._channels.values():
            if channel.state != ChannelState.PENDING:
                continue
            # Each pending channel gets a small burst of droplets at its source point.
            burst = random.randint(1, 3)
            for _ in range(burst):
                droplet_id = (
                    f"drp_{channel.channel_id}_"
                    f"{int(time.time() * 1000)}_{random.randint(100, 999)}"
                )
                kind = random.choice(droplet_kinds_pool)
                weight = round(random.uniform(0.5, 1.5), 3)
                droplet = NarrativeDroplet(
                    droplet_id=droplet_id,
                    channel_id=channel.channel_id,
                    content=f"{kind.value} beat for {channel.label}",
                    kind=kind,
                    flow_distance=0.0,
                    flow_rate=self._compute_flow_rate(channel.gradient, channel.viscosity),
                    weight=weight,
                    pooled=False,
                    state="injected",
                    created_at=time.time(),
                )
                # Cap the droplet collection.
                if len(self._droplets) >= self._MAX_DROPLETS:
                    oldest_key = next(iter(self._droplets))
                    self._droplets.pop(oldest_key, None)
                self._droplets[droplet_id] = droplet
                injected += 1
            channel.state = ChannelState.REGISTERED
        self._update_stats(phase_runs=1, droplets_injected=injected)
        self._record_event("phase_inject_droplet", {"injected": injected})
        return {"phase": "inject_droplet", "injected": injected}

    def _phase_flow_channels(self) -> Dict[str, Any]:
        """Flow phase: flow droplets through channels according to gradient/viscosity."""
        flowed = 0
        # Group droplets by channel for turbulence computation.
        channel_droplet_counts: Dict[str, int] = {}
        for droplet in self._droplets.values():
            if droplet.state != "injected":
                continue
            channel_droplet_counts[droplet.channel_id] = (
                channel_droplet_counts.get(droplet.channel_id, 0) + 1
            )

        for channel in self._channels.values():
            if channel.state != ChannelState.REGISTERED:
                continue
            count = channel_droplet_counts.get(channel.channel_id, 0)
            channel.turbulence = self._classify_turbulence(count)
            for droplet in self._droplets.values():
                if droplet.channel_id != channel.channel_id:
                    continue
                if droplet.state != "injected":
                    continue
                droplet.flow_distance += droplet.flow_rate
                droplet.state = "flowing"
                flowed += 1
            channel.state = ChannelState.FLOWING
            channel.last_flowed_at = time.time()
        self._update_stats(phase_runs=1)
        self._record_event("phase_flow_channels", {"flowed": flowed})
        return {"phase": "flow_channels", "flowed": flowed}

    def _phase_settle_pools(self) -> Dict[str, Any]:
        """Settle phase: settle accumulated droplets into pools; measure pool depth/tension."""
        pools_settled = 0
        # Group flowing droplets by channel and gather into pools.
        for channel in self._channels.values():
            if channel.state != ChannelState.FLOWING:
                continue
            channel_droplets = [
                d for d in self._droplets.values()
                if d.channel_id == channel.channel_id and d.state == "flowing"
            ]
            if not channel_droplets:
                channel.state = ChannelState.POOLED
                continue
            pool_id = (
                f"pool_{channel.channel_id}_"
                f"{int(time.time() * 1000)}_{random.randint(100, 999)}"
            )
            depth = sum(d.weight for d in channel_droplets)
            tension = self._classify_pool_tension(depth, channel.capacity)
            for d in channel_droplets:
                d.pooled = True
                d.state = "pooled"
            pool = NarrativePool(
                pool_id=pool_id,
                channel_id=channel.channel_id,
                depth=round(depth, 3),
                tension=tension,
                droplet_count=len(channel_droplets),
                capacity=channel.capacity,
                state="settled",
                created_at=time.time(),
            )
            # Cap the pool collection.
            if len(self._pools) >= self._MAX_POOLS:
                oldest_key = next(iter(self._pools))
                self._pools.pop(oldest_key, None)
            self._pools[pool_id] = pool
            pools_settled += 1
            channel.state = ChannelState.POOLED
        self._update_stats(phase_runs=1, pools_settled=pools_settled)
        self._record_event("phase_settle_pools", {"pools_settled": pools_settled})
        return {"phase": "settle_pools", "pools_settled": pools_settled}

    def _phase_compute_flux(self) -> Dict[str, Any]:
        """Flux phase: compute evaporation of stale threads and overflow of overfull pools."""
        flux_events_created = 0
        for pool in self._pools.values():
            if pool.state != "settled":
                continue
            # Evaporation: pools that have sat dormant for too long evaporate a droplet.
            age = time.time() - pool.created_at
            if pool.tension == PoolTension.DORMANT and age > self._EVAPORATION_AGE_CYCLES:
                flux_id = (
                    f"fx_{pool.pool_id}_evap_"
                    f"{int(time.time() * 1000)}_{random.randint(100, 999)}"
                )
                flux_event = {
                    "flux_id": flux_id,
                    "pool_id": pool.pool_id,
                    "channel_id": pool.channel_id,
                    "kind": FluxKind.EVAPORATION.value,
                    "magnitude": round(min(pool.depth, 1.0), 3),
                    "detail": "stale thread evaporated",
                    "state": "computed",
                    "created_at": time.time(),
                }
                if len(self._flux_events) >= self._MAX_FLUX_EVENTS:
                    oldest_key = next(iter(self._flux_events))
                    self._flux_events.pop(oldest_key, None)
                self._flux_events[flux_id] = flux_event
                pool.depth = max(0.0, pool.depth - 1.0)
                pool.droplet_count = max(0, pool.droplet_count - 1)
                pool.tension = self._classify_pool_tension(pool.depth, pool.capacity)
                flux_events_created += 1
            # Overflow: overfull pools cascade into a new plot event.
            elif pool.tension == PoolTension.OVERFULL:
                flux_id = (
                    f"fx_{pool.pool_id}_ovr_"
                    f"{int(time.time() * 1000)}_{random.randint(100, 999)}"
                )
                overflow_amount = round(pool.depth - pool.capacity * 0.5, 3)
                flux_event = {
                    "flux_id": flux_id,
                    "pool_id": pool.pool_id,
                    "channel_id": pool.channel_id,
                    "kind": FluxKind.OVERFLOW.value,
                    "magnitude": max(0.0, overflow_amount),
                    "detail": "overfull pool cascaded into a new plot event",
                    "state": "computed",
                    "created_at": time.time(),
                }
                if len(self._flux_events) >= self._MAX_FLUX_EVENTS:
                    oldest_key = next(iter(self._flux_events))
                    self._flux_events.pop(oldest_key, None)
                self._flux_events[flux_id] = flux_event
                pool.depth = round(pool.capacity * 0.5, 3)
                pool.tension = self._classify_pool_tension(pool.depth, pool.capacity)
                flux_events_created += 1
            # Seepage: simmering pools leak slowly to neighbors.
            elif pool.tension == PoolTension.SIMMERING:
                flux_id = (
                    f"fx_{pool.pool_id}_sep_"
                    f"{int(time.time() * 1000)}_{random.randint(100, 999)}"
                )
                flux_event = {
                    "flux_id": flux_id,
                    "pool_id": pool.pool_id,
                    "channel_id": pool.channel_id,
                    "kind": FluxKind.SEEPAGE.value,
                    "magnitude": 0.1,
                    "detail": "slow leak between basins",
                    "state": "computed",
                    "created_at": time.time(),
                }
                if len(self._flux_events) >= self._MAX_FLUX_EVENTS:
                    oldest_key = next(iter(self._flux_events))
                    self._flux_events.pop(oldest_key, None)
                self._flux_events[flux_id] = flux_event
                pool.depth = max(0.0, round(pool.depth - 0.1, 3))
                pool.tension = self._classify_pool_tension(pool.depth, pool.capacity)
                flux_events_created += 1
            pool.state = "fluxed"
        # Mark channels as fluxed.
        for channel in self._channels.values():
            if channel.state == ChannelState.POOLED:
                channel.state = ChannelState.FLUXED
        self._update_stats(phase_runs=1, flux_events_computed=flux_events_created)
        self._record_event("phase_compute_flux", {"flux_events_created": flux_events_created})
        return {"phase": "compute_flux", "flux_events_created": flux_events_created}

    def _phase_emit_fluid_map(self) -> Dict[str, Any]:
        """Emit phase: emit the fluid narrative map with channels, pools, flux for the editor."""
        emitted = 0
        for channel in self._channels.values():
            if channel.state != ChannelState.FLUXED:
                continue
            channel.state = ChannelState.EMITTED
            channel.vitality = self._derive_vitality()
            emitted += 1
        # Mark droplets as emitted.
        for droplet in self._droplets.values():
            if droplet.state == "pooled":
                droplet.state = "emitted"
        # Mark pools as emitted.
        for pool in self._pools.values():
            if pool.state == "fluxed":
                pool.state = "emitted"
        # Mark flux events as emitted.
        for flux_event in self._flux_events.values():
            if flux_event.get("state") == "computed":
                flux_event["state"] = "emitted"
        map_size = (
            len(self._channels) + len(self._droplets)
            + len(self._pools) + len(self._flux_events)
        )
        self._update_stats(phase_runs=1, fluid_maps_emitted=1)
        self._record_event("phase_emit_fluid_map", {
            "emitted": emitted,
            "map_size": map_size,
        })
        return {
            "phase": "emit_fluid_map",
            "emitted": emitted,
            "map_size": map_size,
        }

    # -------------------------------------------------------------------------
    # Vitality
    # -------------------------------------------------------------------------

    def _derive_vitality(self) -> Vitality:
        """Derive overall ecosystem vitality from the droplet population."""
        total_droplets = len(self._droplets)
        capacity_total = sum(c.capacity for c in self._channels.values()) or 1.0
        saturation = total_droplets / max(capacity_total, 1.0)
        if total_droplets == 0:
            return Vitality.DRY
        if saturation < self._VITALITY_FLOWING_FRACTION:
            return Vitality.TRICKLING
        if saturation < self._VITALITY_TURBULENT_FRACTION:
            return Vitality.FLOWING
        if saturation < 1.0:
            return Vitality.TURBULENT
        return Vitality.FLOODED

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_channels(self) -> None:
        """Seed a few synthetic narrative channels on the first cycle if empty."""
        seeds = [
            (
                "ch::main_arc",
                "Main Arc",
                ChannelGradient.DOWNHILL,    # strong flow toward consequence
                0.3,                          # low viscosity - changes course easily
                {"x": 0.0, "y": 0.0, "z": 0.0},
                12.0,
            ),
            (
                "ch::subplot_braid",
                "Subplot Braid",
                ChannelGradient.FLAT,         # meandering flow
                0.6,
                {"x": 2.0, "y": 1.0, "z": 0.0},
                8.0,
            ),
            (
                "ch::backstory_pool",
                "Backstory Pool",
                ChannelGradient.POOLING,     # gathers into a basin
                0.8,                          # high viscosity - resists change
                {"x": -1.0, "y": 2.0, "z": 1.0},
                10.0,
            ),
        ]
        for channel_handle, label, gradient, viscosity, source_point, capacity in seeds:
            if channel_handle in self._channels:
                continue
            if len(self._channels) >= self._MAX_CHANNELS:
                break
            self.register_channel(
                channel_handle=channel_handle,
                label=label,
                gradient=gradient.value,
                viscosity=viscosity,
                source_point=source_point,
                capacity=capacity,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _channel_to_dict(self, channel: NarrativeChannel) -> Dict[str, Any]:
        return {
            "channel_id": channel.channel_id,
            "channel_handle": channel.channel_handle,
            "label": channel.label,
            "gradient": channel.gradient.value,
            "viscosity": channel.viscosity,
            "source_point": dict(channel.source_point),
            "capacity": channel.capacity,
            "turbulence": channel.turbulence,
            "active": channel.active,
            "state": channel.state.value,
            "vitality": channel.vitality.value,
            "created_at": channel.created_at,
            "last_flowed_at": channel.last_flowed_at,
            "note": channel.note,
        }

    def _droplet_to_dict(self, droplet: NarrativeDroplet) -> Dict[str, Any]:
        return {
            "droplet_id": droplet.droplet_id,
            "channel_id": droplet.channel_id,
            "content": droplet.content,
            "kind": droplet.kind.value,
            "flow_distance": droplet.flow_distance,
            "flow_rate": droplet.flow_rate,
            "weight": droplet.weight,
            "pooled": droplet.pooled,
            "state": droplet.state,
            "created_at": droplet.created_at,
        }

    def _pool_to_dict(self, pool: NarrativePool) -> Dict[str, Any]:
        return {
            "pool_id": pool.pool_id,
            "channel_id": pool.channel_id,
            "depth": pool.depth,
            "tension": pool.tension.value,
            "droplet_count": pool.droplet_count,
            "capacity": pool.capacity,
            "state": pool.state,
            "created_at": pool.created_at,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "channels": len(self._channels),
                "droplets": len(self._droplets),
                "pools": len(self._pools),
                "flux_events": len(self._flux_events),
                "stats": dict(self._stats),
            }

    def get_channels(self, limit: int = 50) -> Dict[str, Any]:
        with self._global_lock:
            channels = sorted(
                self._channels.values(),
                key=lambda c: c.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(channels),
                "channels": [
                    {
                        "channel_id": c.channel_id,
                        "channel_handle": c.channel_handle,
                        "label": c.label,
                        "gradient": c.gradient.value,
                        "viscosity": c.viscosity,
                        "capacity": c.capacity,
                        "turbulence": c.turbulence,
                        "state": c.state.value,
                        "vitality": c.vitality.value,
                        "active": c.active,
                    }
                    for c in channels
                ],
            }

    def get_channel(self, channel_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by channel_handle, NOT channel_id, so we
        # MUST iterate over values and match on the channel_id attribute.
        with self._global_lock:
            for channel in self._channels.values():
                if channel.channel_id == channel_id:
                    return self._channel_to_dict(channel)
            return {"error": f"Channel not found: {channel_id}", "channel_id": channel_id}

    def get_fluid_map(self) -> Dict[str, Any]:
        """Return the full fluid narrative map with channels, droplets, pools, and flux events."""
        with self._global_lock:
            return {
                "channels": [self._channel_to_dict(c) for c in self._channels.values()],
                "droplets": [self._droplet_to_dict(d) for d in self._droplets.values()],
                "pools": [self._pool_to_dict(p) for p in self._pools.values()],
                "flux_events": list(self._flux_events.values()),
                "channel_count": len(self._channels),
                "droplet_count": len(self._droplets),
                "pool_count": len(self._pools),
                "flux_event_count": len(self._flux_events),
                "cycle_count": self._cycle_count,
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic channels if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._channels:
                self._seed_synthetic_channels()
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
            self._channels.clear()
            self._droplets.clear()
            self._pools.clear()
            self._flux_events.clear()
            self._phase = LiquidNarrativePhase.INJECT_DROPLET
            self._cycle_count = 0
            self._init_stats()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }
