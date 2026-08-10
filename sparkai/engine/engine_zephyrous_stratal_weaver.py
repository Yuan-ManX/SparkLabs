"""
SparkLabs Engine - Zephyrous Stratal Weaver"""

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

class WeaverPhase(Enum):
    """Phases of the zephyrous stratal weaver cycle."""
    GATHER_LAMINAE = "gather_laminae"              # gather wind-driven laminae with their wind speeds
    INTERLACE_STRATA = "interlace_strata"          # interlace drifting laminae into stratified formations, flag surges
    CONSOLIDATE_SEDIMENT = "consolidate_sediment"  # consolidate the interlaced sediment into compact strata
    MAP_BEDDING_PLANES = "map_bedding_planes"      # map the bedding planes between strata, flag folds
    EMIT_STRATAL_LAYER = "emit_stratal_layer"      # emit the full stratal layer with laminae, bedding planes, and porosity budgets


class WindKind(Enum):
    """The kind of zephyrous wind driving the laminae drift."""
    ZEPHYR = "zephyr"             # gentle west breeze
    BREEZE = "breeze"             # steady breeze
    GUST = "gust"                 # irregular gust
    GALE = "gale"                 # strong gale


class GrainKind(Enum):
    """The kind of wind-borne grain forming the laminae."""
    SAND = "sand"                 # coarse sand grain
    SILT = "silt"                 # fine silt grain
    CLAY = "clay"                 # clay grain
    LOESS = "loess"               # windblown loess
    DUST = "dust"                 # fine dust


class BeddingState(Enum):
    """The bedding plane state of a stratified formation."""
    CROSS_SET = "cross_set"       # cross-stratified bedding
    GRADED = "graded"             # graded bedding
    LAMINATED = "laminated"       # fine laminations
    EROSIONAL = "erosional"       # erosional boundary
    CONFORMABLE = "conformable"   # conformable contact


class StratumState(Enum):
    """State of an individual stratum through the weaver cycle."""
    PENDING = "pending"           # registered but not yet processed
    LAYERED = "layered"           # laminae gathered into a layer
    INTERLACED = "interlaced"     # laminae interlaced into stratified formations
    CONSOLIDATED = "consolidated" # sediment consolidated into compact strata
    MAPPED = "mapped"             # bedding planes mapped
    EMITTED = "emitted"           # emitted into the stratal layer


class Vitality(Enum):
    """Overall vitality of the zephyrous stratal weaver ecosystem."""
    DORMANT = "dormant"
    BREEZING = "breezing"
    DRIFTING = "drifting"
    LAMINATED = "laminated"
    STRATIFIED = "stratified"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Stratum:
    """A stratified sedimentary formation woven by the stratal weaver."""
    entity_id: str
    stratum_id: str
    stratum_label: str
    laminae_count: int                            # number of interlaced laminae
    bedding_plane_depth: float                    # m below surface
    wind_speed: float                             # m/s of the driving wind
    porosity: float                               # effective porosity ratio
    bedding_state: BeddingState = BeddingState.LAMINATED
    grain_kind: GrainKind = GrainKind.SILT
    wind_kind: WindKind = WindKind.ZEPHYR
    vitality: Vitality = Vitality.DORMANT
    thickness: float = 0.0                        # net layer thickness, m
    compaction: float = 0.0                       # net compaction ratio
    safe_porosity_floor: float = 0.05             # minimum safe porosity
    safe_porosity_ceiling: float = 0.95           # maximum safe porosity
    state: StratumState = StratumState.PENDING
    created_at: float = field(default_factory=time.time)
    last_mapped_at: float = 0.0
    note: str = ""


# =============================================================================
# Zephyrous Stratal Weaver
# =============================================================================

class ZephyrousStratalWeaver:
    """
    Thread-safe singleton that weaves zephyrous stratal layers.

    Strata are keyed internally by entity_id so each logical stratum owns
    exactly one entry. The stratum_id is a generated handle for external
    lookups; lookups by stratum_id fall back to a linear scan of the
    registered strata.

    Usage:
        weaver = ZephyrousStratalWeaver.get_instance()
        weaver.register_stratum(
            entity_id="strata::alpha",
            stratum_label="Alpha Dune Field",
            wind_speed=8.5,
        )
        weaver.cycle()
        stratum = weaver.get_stratum(stratum_id)
        plane_map = weaver.build_bedding_plane_map()
    """

    _instance: Optional["ZephyrousStratalWeaver"] = None
    _instance_lock = threading.Lock()

    # Capacity caps.
    _MAX_STRATA = 200
    _MAX_EVENTS = 200
    _MAX_LAMINAE_LOGS = 200
    _MAX_CONSOLIDATION_LOGS = 200
    _MAX_STRATAL_LAYERS = 120

    # Domain tuning constants.
    _WIND_FLUCTUATION = 0.4              # base wind fluctuation magnitude, m/s
    _COMPACTION_TOLERANCE = 0.03         # below this compaction drift is even
    _SAFE_POROSITY_FLOOR_DEFAULT = 0.05  # default minimum safe porosity
    _SAFE_POROSITY_CEILING_DEFAULT = 0.95  # default maximum safe porosity
    _CONSOLIDATION_THRESHOLD = 0.7       # porosity ratio above which sediment consolidates
    _SURGE_WIND = 1.0                    # wind speed above which laminae surge
    _DEPLETED_WIND = 0.1                 # wind speed below which laminae settle
    _THROTTLE_FACTOR = 0.7               # throttle factor for collecting laminae
    _CAP_FACTOR = 0.3                    # cap factor for surging laminae
    _MIN_WIND_SPEED = 1e-4
    _MAX_WIND_SPEED = 5.0

    def __init__(self) -> None:
        # Instance-level reentrant lock for thread-safe operation.
        self._global_lock = threading.RLock()
        # Internal dict keyed by entity_id (NOT stratum_id).
        self._strata: Dict[str, Stratum] = {}
        self._laminae_logs: Dict[str, Dict[str, Any]] = {}
        self._consolidation_logs: Dict[str, Dict[str, Any]] = {}
        self._stratal_layers: Dict[str, Dict[str, Any]] = {}
        self._bedding_planes: Dict[str, Dict[str, Any]] = {}
        self._phase: WeaverPhase = WeaverPhase.GATHER_LAMINAE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        if not self._strata:
            self._seed_synthetic_strata()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "ZephyrousStratalWeaver":
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
            "strata_registered": 0,
            "phase_runs": 0,
            "laminae_gathered": 0,
            "strata_interlaced": 0,
            "surge_strata": 0,
            "sediment_consolidated": 0,
            "laminae_capped": 0,
            "bedding_planes_mapped": 0,
            "stratal_layers_emitted": 0,
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
    def _parse_wind_kind(value: Any) -> WindKind:
        """Parse a WindKind from a string, enum, or None."""
        if value is None:
            return WindKind.ZEPHYR
        if isinstance(value, WindKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in WindKind:
                if kind.value == lowered:
                    return kind
        return WindKind.ZEPHYR

    @staticmethod
    def _parse_grain_kind(value: Any) -> GrainKind:
        """Parse a GrainKind from a string, enum, or None."""
        if value is None:
            return GrainKind.SILT
        if isinstance(value, GrainKind):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            for kind in GrainKind:
                if kind.value == lowered:
                    return kind
        return GrainKind.SILT

    # -------------------------------------------------------------------------
    # Classification Helpers
    # -------------------------------------------------------------------------

    def _classify_bedding_state(self, wind_speed: float, porosity_ratio: float) -> BeddingState:
        """Classify the bedding state from wind speed and porosity ratio."""
        if wind_speed >= self._SURGE_WIND and porosity_ratio >= self._CONSOLIDATION_THRESHOLD:
            return BeddingState.CROSS_SET
        if porosity_ratio >= self._CONSOLIDATION_THRESHOLD:
            return BeddingState.GRADED
        if wind_speed <= self._DEPLETED_WIND:
            return BeddingState.EROSIONAL
        if porosity_ratio >= self._CONSOLIDATION_THRESHOLD * 0.5:
            return BeddingState.CONFORMABLE
        return BeddingState.LAMINATED

    def _derive_vitality(self, stratum_id: str) -> Vitality:
        """Derive vitality for a stratum from its post-mapping state."""
        stratum = self._find_stratum_by_id(stratum_id)
        if stratum is None:
            return Vitality.DORMANT
        surging = abs(stratum.compaction) > self._COMPACTION_TOLERANCE * 5.0
        if stratum.bedding_state == BeddingState.CROSS_SET and surging:
            return Vitality.STRATIFIED
        if stratum.bedding_state == BeddingState.GRADED:
            return Vitality.LAMINATED
        if stratum.bedding_state == BeddingState.LAMINATED:
            return Vitality.DRIFTING
        if stratum.state in (StratumState.LAYERED, StratumState.INTERLACED):
            return Vitality.BREEZING
        return Vitality.DORMANT

    def _color_for_bedding(self, state: BeddingState) -> str:
        """Map a bedding state to a preview color for the editor stratal layer."""
        if state == BeddingState.CROSS_SET:
            return "#C2B280"  # sand - cross-set strata
        if state == BeddingState.GRADED:
            return "#CD853F"  # peru - graded bedding
        if state == BeddingState.LAMINATED:
            return "#D2B48C"  # tan - fine laminations
        if state == BeddingState.CONFORMABLE:
            return "#8B7355"  # muted brown - conformable contact
        return "#A0522D"      # sienna - erosional boundary

    # -------------------------------------------------------------------------
    # Stratum Management
    # -------------------------------------------------------------------------

    def register_stratum(
        self,
        entity_id: str,
        stratum_label: str,
        laminae_count: int = 8,
        bedding_plane_depth: float = 20.0,
        wind_speed: float = 8.0,
        porosity: float = 0.0,
        wind_kind: Optional[str] = None,
        grain_kind: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Register a new stratified formation with the weaver."""
        with self._global_lock:
            if entity_id in self._strata:
                return {"error": f"Stratum already registered: {entity_id}"}
            if len(self._strata) >= self._MAX_STRATA:
                return {"error": f"Stratum cap reached ({self._MAX_STRATA})"}

            stratum_id = (
                f"stratum_{entity_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )

            speed = max(
                self._MIN_WIND_SPEED,
                min(self._MAX_WIND_SPEED, float(wind_speed)),
            )
            parsed_wind = self._parse_wind_kind(wind_kind)
            parsed_grain = self._parse_grain_kind(grain_kind)
            porosity_ratio = max(0.0, min(1.0, float(porosity)))
            bedding = self._classify_bedding_state(speed, porosity_ratio)

            stratum = Stratum(
                entity_id=entity_id,
                stratum_id=stratum_id,
                stratum_label=stratum_label,
                laminae_count=int(laminae_count),
                bedding_plane_depth=float(bedding_plane_depth),
                wind_speed=speed,
                porosity=float(porosity),
                bedding_state=bedding,
                grain_kind=parsed_grain,
                wind_kind=parsed_wind,
                vitality=Vitality.DORMANT,
                thickness=0.0,
                compaction=0.0,
                safe_porosity_floor=self._SAFE_POROSITY_FLOOR_DEFAULT,
                safe_porosity_ceiling=self._SAFE_POROSITY_CEILING_DEFAULT,
                state=StratumState.PENDING,
                created_at=time.time(),
                last_mapped_at=0.0,
                note=note,
            )
            self._strata[entity_id] = stratum
            self._update_stats(strata_registered=1)
            self._record_event("stratum_registered", {
                "stratum_id": stratum_id,
                "entity_id": entity_id,
                "stratum_label": stratum_label,
                "wind_speed": stratum.wind_speed,
                "wind_kind": parsed_wind.value,
                "bedding_state": bedding.value,
            })

            return {
                "stratum_id": stratum_id,
                "entity_id": entity_id,
                "stratum_label": stratum_label,
                "wind_speed": stratum.wind_speed,
                "wind_kind": parsed_wind.value,
                "bedding_state": bedding.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single zephyrous stratal weaver cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic strata on the very first cycle if none exist.
            if not self._strata and self._cycle_count == 0:
                self._seed_synthetic_strata()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = WeaverPhase.GATHER_LAMINAE
            phase_outputs.append(self._phase_gather_laminae())
            self._phase = WeaverPhase.INTERLACE_STRATA
            phase_outputs.append(self._phase_interlace_strata())
            self._phase = WeaverPhase.CONSOLIDATE_SEDIMENT
            phase_outputs.append(self._phase_consolidate_sediment())
            self._phase = WeaverPhase.MAP_BEDDING_PLANES
            phase_outputs.append(self._phase_map_bedding_planes())
            self._phase = WeaverPhase.EMIT_STRATAL_LAYER
            phase_outputs.append(self._phase_emit_stratal_layer())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_gather_laminae(self) -> Dict[str, Any]:
        """Gather phase: confirm pending strata and their wind-driven laminae."""
        layered = 0
        laminae_sum = 0
        for stratum in self._strata.values():
            if stratum.state == StratumState.PENDING:
                stratum.state = StratumState.LAYERED
                layered += 1
            # Refresh bedding classification in case wind was set externally.
            porosity_ratio = max(0.0, min(1.0, stratum.porosity))
            stratum.bedding_state = self._classify_bedding_state(
                stratum.wind_speed, porosity_ratio,
            )
            laminae_sum += stratum.laminae_count
        avg_laminae = (laminae_sum / len(self._strata)) if self._strata else 0.0
        self._update_stats(phase_runs=1)
        self._record_event("phase_gather_laminae", {
            "layered": layered,
            "avg_laminae": avg_laminae,
        })
        return {
            "phase": "gather_laminae",
            "layered": layered,
            "avg_laminae": avg_laminae,
        }

    def _phase_interlace_strata(self) -> Dict[str, Any]:
        """Interlace phase: interlace drifting laminae into stratified formations."""
        interlaced = 0
        surging = 0
        strata = list(self._strata.values())
        for i, stratum in enumerate(strata):
            if stratum.state != StratumState.LAYERED:
                continue
            # Apply a small stochastic fluctuation to the wind speed.
            fluctuation = random.uniform(
                -self._WIND_FLUCTUATION, self._WIND_FLUCTUATION,
            )
            stratum.wind_speed = max(0.0, stratum.wind_speed + fluctuation)
            # Compare this stratum's laminae against the average of the others.
            if len(strata) <= 1:
                stratum.compaction = 0.0
            else:
                others = [s for j, s in enumerate(strata) if j != i]
                avg_other = sum(s.laminae_count for s in others) / len(others)
                # Compaction drift normalized by bedding plane span.
                plane_span = max(int(stratum.bedding_plane_depth) + 1, 1)
                stratum.compaction = (
                    stratum.laminae_count - avg_other
                ) / plane_span
            if abs(stratum.compaction) <= self._COMPACTION_TOLERANCE:
                interlaced += 1
            else:
                surging += 1
                # Record the laminae drift entry.
                log_id = (
                    f"laminae_{stratum.stratum_id}_{int(time.time() * 1000)}_"
                    f"{random.randint(100, 999)}"
                )
                log_entry = {
                    "laminae_log_id": log_id,
                    "stratum_id": stratum.stratum_id,
                    "entity_id": stratum.entity_id,
                    "compaction": stratum.compaction,
                    "laminae_count": stratum.laminae_count,
                    "kind": "surge",
                    "created_at": time.time(),
                }
                # Cap the laminae log collection.
                if len(self._laminae_logs) >= self._MAX_LAMINAE_LOGS:
                    oldest_key = next(iter(self._laminae_logs))
                    self._laminae_logs.pop(oldest_key, None)
                self._laminae_logs[log_id] = log_entry
            porosity_ratio = max(0.0, min(1.0, stratum.porosity))
            stratum.bedding_state = self._classify_bedding_state(
                stratum.wind_speed, porosity_ratio,
            )
            stratum.state = StratumState.INTERLACED
        self._update_stats(
            phase_runs=1,
            strata_interlaced=interlaced,
            surge_strata=surging,
        )
        self._record_event("phase_interlace_strata", {
            "interlaced": interlaced,
            "surging": surging,
        })
        return {
            "phase": "interlace_strata",
            "interlaced": interlaced,
            "surging": surging,
        }

    def _phase_consolidate_sediment(self) -> Dict[str, Any]:
        """Consolidate phase: consolidate the interlaced sediment into compact strata."""
        consolidated = 0
        capped = 0
        for stratum in self._strata.values():
            if stratum.state != StratumState.INTERLACED:
                continue
            poro = stratum.porosity
            # Clamp the porosity to the safe envelope.
            if poro > stratum.safe_porosity_ceiling:
                stratum.porosity = stratum.safe_porosity_ceiling
                poro = stratum.safe_porosity_ceiling
            elif poro < stratum.safe_porosity_floor:
                stratum.porosity = stratum.safe_porosity_floor
                poro = stratum.safe_porosity_floor
            # Re-classify after clamping.
            porosity_ratio = max(0.0, min(1.0, stratum.porosity))
            stratum.bedding_state = self._classify_bedding_state(
                stratum.wind_speed, porosity_ratio,
            )
            # Consolidate thickness based on the clamped porosity.
            if stratum.laminae_count > 0:
                if poro <= self._SAFE_POROSITY_FLOOR_DEFAULT * 10.0:
                    stratum.laminae_count = int(
                        stratum.laminae_count * self._CAP_FACTOR,
                    )
                    capped += 1
                elif porosity_ratio >= self._CONSOLIDATION_THRESHOLD * 0.5:
                    stratum.laminae_count = int(
                        stratum.laminae_count * self._THROTTLE_FACTOR,
                    )
            consolidated += 1
            stratum.thickness = stratum.bedding_plane_depth * 0.25
            # Record the consolidation log.
            log_id = (
                f"cons_{stratum.stratum_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            log_entry = {
                "consolidation_id": log_id,
                "stratum_id": stratum.stratum_id,
                "entity_id": stratum.entity_id,
                "porosity": poro,
                "laminae_count": stratum.laminae_count,
                "bedding_state": stratum.bedding_state.value,
                "created_at": time.time(),
            }
            # Cap the consolidation log collection.
            if len(self._consolidation_logs) >= self._MAX_CONSOLIDATION_LOGS:
                oldest_key = next(iter(self._consolidation_logs))
                self._consolidation_logs.pop(oldest_key, None)
            self._consolidation_logs[log_id] = log_entry
            stratum.state = StratumState.CONSOLIDATED
        self._update_stats(
            phase_runs=1,
            sediment_consolidated=consolidated,
            laminae_capped=capped,
        )
        self._record_event("phase_consolidate_sediment", {
            "consolidated": consolidated,
            "capped": capped,
        })
        return {
            "phase": "consolidate_sediment",
            "consolidated": consolidated,
            "capped": capped,
        }

    def _phase_map_bedding_planes(self) -> Dict[str, Any]:
        """Map phase: map the bedding planes between strata, flag folds."""
        mapped = 0
        folded = 0
        strata = list(self._strata.values())
        for i, stratum in enumerate(strata):
            if stratum.state != StratumState.CONSOLIDATED:
                continue
            # Compute a bedding plane depth offset from the consolidation result.
            offset = stratum.thickness
            plane_drift = stratum.wind_speed * 0.5
            plane_id = (
                f"plane_{stratum.stratum_id}_{int(time.time() * 1000)}_"
                f"{random.randint(100, 999)}"
            )
            plane_entry = {
                "bedding_plane_id": plane_id,
                "stratum_id": stratum.stratum_id,
                "entity_id": stratum.entity_id,
                "bedding_plane_depth": stratum.bedding_plane_depth,
                "offset": offset,
                "plane_drift": plane_drift,
                "bedding_state": stratum.bedding_state.value,
                "created_at": time.time(),
            }
            # Cap the bedding plane collection.
            if len(self._bedding_planes) >= self._MAX_STRATA * 2:
                oldest_key = next(iter(self._bedding_planes))
                self._bedding_planes.pop(oldest_key, None)
            self._bedding_planes[plane_id] = plane_entry
            stratum.last_mapped_at = time.time()
            stratum.state = StratumState.MAPPED
            mapped += 1
            if abs(stratum.compaction) > self._COMPACTION_TOLERANCE:
                folded += 1
        self._update_stats(
            phase_runs=1,
            bedding_planes_mapped=mapped,
        )
        self._record_event("phase_map_bedding_planes", {
            "mapped": mapped,
            "folded": folded,
        })
        return {
            "phase": "map_bedding_planes",
            "mapped": mapped,
            "folded": folded,
        }

    def _phase_emit_stratal_layer(self) -> Dict[str, Any]:
        """Emit phase: emit the full stratal layer with strata, planes, logs."""
        emitted = 0
        for stratum in self._strata.values():
            if stratum.state != StratumState.MAPPED:
                continue
            stratum.state = StratumState.EMITTED
            emitted += 1
        # Stamp vitality based on the post-mapping state.
        for stratum in self._strata.values():
            stratum.vitality = self._derive_vitality(stratum.stratum_id)
        # Build the consolidated stratal layer entry.
        layer_id = (
            f"layer_{int(time.time() * 1000)}_{random.randint(100, 999)}"
        )
        stratal_layer = {
            "layer_id": layer_id,
            "cycle_count": self._cycle_count,
            "stratum_count": len(self._strata),
            "laminae_log_count": len(self._laminae_logs),
            "consolidation_log_count": len(self._consolidation_logs),
            "bedding_plane_count": len(self._bedding_planes),
            "strata": [self._stratum_to_dict(s) for s in self._strata.values()],
            "laminae_logs": list(self._laminae_logs.values()),
            "consolidation_logs": list(self._consolidation_logs.values()),
            "bedding_planes": list(self._bedding_planes.values()),
            "created_at": time.time(),
        }
        # Cap the stratal layer collection.
        if len(self._stratal_layers) >= self._MAX_STRATAL_LAYERS:
            oldest_key = next(iter(self._stratal_layers))
            self._stratal_layers.pop(oldest_key, None)
        self._stratal_layers[layer_id] = stratal_layer
        self._update_stats(phase_runs=1, stratal_layers_emitted=1)
        self._record_event("phase_emit_stratal_layer", {
            "emitted": emitted,
            "layer_id": layer_id,
        })
        return {
            "phase": "emit_stratal_layer",
            "emitted": emitted,
            "layer_id": layer_id,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_stratum_by_id(self, stratum_id: str) -> Optional[Stratum]:
        """Find a stratum by its stratum_id (linear scan over entity_id keys)."""
        for stratum in self._strata.values():
            if stratum.stratum_id == stratum_id:
                return stratum
        return None

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_strata(self) -> None:
        """Seed a few synthetic stratified formations on the first cycle if empty."""
        seeds = [
            ("strata::alpha", "Alpha Dune Field", 8.0, 20.0, WindKind.ZEPHYR, GrainKind.SAND),
            ("strata::bravo", "Bravo Loess Ridge", 12.0, 45.0, WindKind.BREEZE, GrainKind.LOESS),
            ("strata::charlie", "Charlie Silt Basin", 6.0, 30.0, WindKind.GUST, GrainKind.SILT),
        ]
        for entity_id, label, laminae, depth, wind, grain in seeds:
            if entity_id in self._strata:
                continue
            if len(self._strata) >= self._MAX_STRATA:
                break
            self.register_stratum(
                entity_id=entity_id,
                stratum_label=label,
                laminae_count=laminae,
                bedding_plane_depth=depth,
                wind_speed=2.0,
                porosity=0.4,
                wind_kind=wind.value,
                grain_kind=grain.value,
            )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _stratum_to_dict(self, stratum: Stratum) -> Dict[str, Any]:
        return {
            "entity_id": stratum.entity_id,
            "stratum_id": stratum.stratum_id,
            "stratum_label": stratum.stratum_label,
            "laminae_count": stratum.laminae_count,
            "bedding_plane_depth": stratum.bedding_plane_depth,
            "wind_speed": stratum.wind_speed,
            "porosity": stratum.porosity,
            "thickness": stratum.thickness,
            "compaction": stratum.compaction,
            "bedding_state": stratum.bedding_state.value,
            "grain_kind": stratum.grain_kind.value,
            "wind_kind": stratum.wind_kind.value,
            "vitality": stratum.vitality.value,
            "safe_porosity_floor": stratum.safe_porosity_floor,
            "safe_porosity_ceiling": stratum.safe_porosity_ceiling,
            "state": stratum.state.value,
            "created_at": stratum.created_at,
            "last_mapped_at": stratum.last_mapped_at,
            "note": stratum.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "strata": len(self._strata),
                "laminae_logs": len(self._laminae_logs),
                "consolidation_logs": len(self._consolidation_logs),
                "bedding_planes": len(self._bedding_planes),
                "stratal_layers": len(self._stratal_layers),
                "stats": dict(self._stats),
            }

    def get_strata(self, limit: int = 10) -> Dict[str, Any]:
        with self._global_lock:
            strata = sorted(
                self._strata.values(),
                key=lambda s: s.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(strata),
                "strata": [
                    {
                        "stratum_id": s.stratum_id,
                        "entity_id": s.entity_id,
                        "stratum_label": s.stratum_label,
                        "laminae_count": s.laminae_count,
                        "wind_speed": s.wind_speed,
                        "wind_kind": s.wind_kind.value,
                        "bedding_state": s.bedding_state.value,
                        "vitality": s.vitality.value,
                    }
                    for s in strata
                ],
            }

    def get_stratum(self, stratum_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, NOT stratum_id, so we
        # MUST iterate over values and match on the stratum_id attribute.
        with self._global_lock:
            for stratum in self._strata.values():
                if stratum.stratum_id == stratum_id:
                    return self._stratum_to_dict(stratum)
            return {
                "error": "stratum not found",
                "stratum_id": stratum_id,
            }

    def get_events_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic strata if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._strata:
                self._seed_synthetic_strata()
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
            self._strata.clear()
            self._laminae_logs.clear()
            self._consolidation_logs.clear()
            self._stratal_layers.clear()
            self._bedding_planes.clear()
            self._phase = WeaverPhase.GATHER_LAMINAE
            self._cycle_count = 0
            self._init_stats()
            # Re-seed synthetic data so cycles produce meaningful output.
            if not self._strata:
                self._seed_synthetic_strata()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }

    # -------------------------------------------------------------------------
    # Domain-Specific Bedding Plane Mapping
    # -------------------------------------------------------------------------

    def build_bedding_plane_map(self) -> Dict[str, Any]:
        """Build a bedding plane map: run a mapping pass and return the map.

        Computes the current bedding state distribution, the compaction
        drift summary, and the porosity budget without advancing the cycle
        counter.
        """
        with self._global_lock:
            strata = list(self._strata.values())
            if not strata:
                return {
                    "mapped": 0,
                    "bedding_distribution": {},
                    "porosity_budget": 0.0,
                    "fold_count": 0,
                    "bedding_plane_map": "no strata registered",
                }
            bedding_counts: Dict[str, int] = {}
            total_porosity = 0.0
            folded = 0
            for stratum in strata:
                porosity_ratio = max(0.0, min(1.0, stratum.porosity))
                state = self._classify_bedding_state(
                    stratum.wind_speed, porosity_ratio,
                )
                bedding_counts[state.value] = (
                    bedding_counts.get(state.value, 0) + 1
                )
                total_porosity += stratum.porosity
                if abs(stratum.compaction) > self._COMPACTION_TOLERANCE:
                    folded += 1
            return {
                "mapped": len(strata),
                "bedding_distribution": bedding_counts,
                "porosity_budget": total_porosity,
                "fold_count": folded,
                "cycle_count": self._cycle_count,
                "bedding_plane_map": "mapping pass complete",
            }