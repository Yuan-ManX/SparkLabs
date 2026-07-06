"""
SparkLabs Agent - AI Netcode Director

A runtime fusion module that optimizes multiplayer netcode by fusing live
network telemetry with strategy selection, lag compensation tuning, and
region-aware recommendations. The director ingests latency and bandwidth
samples per session, classifies connection quality, detects anomalies such
as lag spikes and packet loss bursts, and issues strategy changes that
keep gameplay responsive across heterogeneous networks.

This module embodies the AI-native principle: netcode is not a fixed
transport layer but an intelligent agent that observes per-player
conditions, reasons about tradeoffs between client authority, server
authority, rollback, and prediction, and adapts sync mode, bandwidth
profile, and lag compensation in real time.

Architecture:
  NetcodeDirector (singleton)
    |-- LatencySample, BandwidthMeasurement, NetcodeSession,
        LagCompensationConfig, RegionProfile, NetcodeRecommendation,
        NetcodeAnomaly, NetcodeStats, NetcodeSnapshot, NetcodeEvent
    |-- NetcodeStrategy, LatencyTier, SyncMode, BandwidthProfile,
        LagCompensation, RegionCode, NetcodeEventKind

Core Capabilities:
  - create_session / get_session / list_sessions / update_session /
    close_session: session lifecycle management with strategy metadata.
  - record_latency / list_latency_samples: per-player RTT, jitter, and
    packet loss ingestion used to classify connection quality.
  - record_bandwidth / list_bandwidth_measurements: throughput and
    compression telemetry tracking across active sessions.
  - tune_lag_compensation / get_lag_compensation: backward reconciliation,
    forward prediction, and hybrid compensation configuration.
  - register_region / get_region / list_regions: region capacity and
    latency profiling for placement decisions.
  - analyze_session / list_recommendations: strategy recommendation
    engine that reasons over current telemetry and session profile.
  - detect_anomalies / list_anomalies: anomaly detection for lag spikes,
    packet loss bursts, and bandwidth compression regressions.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_SESSIONS: int = 10000
_MAX_LATENCY_SAMPLES: int = 50000
_MAX_BANDWIDTH_MEASUREMENTS: int = 50000
_MAX_RECOMMENDATIONS: int = 10000
_MAX_ANOMALIES: int = 10000
_MAX_EVENTS: int = 10000
_MAX_LAG_CONFIGS: int = 10000
_MAX_REGIONS: int = 1000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class NetcodeStrategy(str, Enum):
    """Authority and reconciliation model for a multiplayer session."""
    CLIENT_AUTHORITATIVE = "client_authoritative"
    SERVER_AUTHORITATIVE = "server_authoritative"
    DETERMINISTIC_LOCKSTEP = "deterministic_lockstep"
    ROLLBACK = "rollback"
    HYBRID = "hybrid"
    PREDICTION_RECONCILIATION = "prediction_reconciliation"


class LatencyTier(str, Enum):
    """Qualitative classification of a connection's latency profile."""
    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"
    CRITICAL = "critical"


class SyncMode(str, Enum):
    """State propagation strategy used by a session."""
    STATE_SYNC = "state_sync"
    SNAPSHOT_INTERPOLATION = "snapshot_interpolation"
    DELTA_COMPRESSION = "delta_compression"
    EVENT_RELAY = "event_relay"


class BandwidthProfile(str, Enum):
    """Bandwidth budgeting policy for outgoing replication traffic."""
    MINIMAL = "minimal"
    BALANCED = "balanced"
    PRIORITY_BASED = "priority_based"
    AGGRESSIVE = "aggressive"


class LagCompensation(str, Enum):
    """Lag compensation approach used for hit registration and rewind."""
    NONE = "none"
    BACKWARD_RECONCILIATION = "backward_reconciliation"
    FORWARD_PREDICTION = "forward_prediction"
    HYBRID_COMPENSATION = "hybrid_compensation"


class RegionCode(str, Enum):
    """Geographic region identifier for session placement."""
    NA_EAST = "na_east"
    NA_WEST = "na_west"
    EU_WEST = "eu_west"
    EU_CENTRAL = "eu_central"
    AP_EAST = "ap_east"
    AP_SOUTH = "ap_south"
    SA_EAST = "sa_east"
    OCEANIA = "oceania"


class NetcodeEventKind(str, Enum):
    """Event types emitted by the NetcodeDirector for observability."""
    STRATEGY_SELECTED = "strategy_selected"
    LATENCY_UPDATED = "latency_updated"
    BANDWIDTH_ADJUSTED = "bandwidth_adjusted"
    LAG_COMPENSATION_TUNED = "lag_compensation_tuned"
    REGION_OPTIMIZED = "region_optimized"
    SESSION_CREATED = "session_created"
    SESSION_UPDATED = "session_updated"
    SESSION_CLOSED = "session_closed"
    ANOMALY_DETECTED = "anomaly_detected"
    RECOMMENDATION_ISSUED = "recommendation_issued"
    METRIC_RECORDED = "metric_recorded"
    CONFIG_CHANGED = "config_changed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class LatencySample:
    """A single round-trip latency measurement for a player in a session."""
    sample_id: str
    session_id: str
    player_id: str
    region: RegionCode
    rtt_ms: float
    jitter_ms: float = 0.0
    packet_loss_pct: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BandwidthMeasurement:
    """A throughput snapshot for a session over a measurement window."""
    measurement_id: str
    session_id: str
    bytes_sent: int = 0
    bytes_received: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    compression_ratio: float = 1.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NetcodeSession:
    """A multiplayer session with its active netcode configuration."""
    session_id: str
    game_mode: str = ""
    player_count: int = 0
    region: RegionCode = RegionCode.NA_EAST
    strategy: NetcodeStrategy = NetcodeStrategy.SERVER_AUTHORITATIVE
    sync_mode: SyncMode = SyncMode.STATE_SYNC
    bandwidth_profile: BandwidthProfile = BandwidthProfile.BALANCED
    lag_compensation: LagCompensation = LagCompensation.NONE
    target_tick_rate: int = 30
    actual_tick_rate: float = 30.0
    interpolation_delay_ms: int = 100
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LagCompensationConfig:
    """Tunable parameters governing rewind and hit registration windows."""
    config_id: str
    session_id: str
    compensation_type: LagCompensation = LagCompensation.NONE
    history_size_ms: int = 200
    max_extrapolation_ms: int = 50
    hit_registration_window_ms: int = 100
    rewind_limit_ms: int = 250

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RegionProfile:
    """Capacity and latency profile for a geographic region."""
    region_code: RegionCode
    region_name: str = ""
    avg_latency_ms: float = 0.0
    player_density: int = 0
    server_capacity: int = 0
    load_factor: float = 0.0
    recommended_strategy: NetcodeStrategy = NetcodeStrategy.SERVER_AUTHORITATIVE

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NetcodeRecommendation:
    """A strategy change recommendation produced by the analysis engine."""
    recommendation_id: str
    session_id: str
    current_strategy: NetcodeStrategy
    recommended_strategy: NetcodeStrategy
    reason: str = ""
    confidence: float = 0.0
    expected_improvement: float = 0.0
    priority: str = "low"
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NetcodeAnomaly:
    """A detected network condition that degrades gameplay quality."""
    anomaly_id: str
    session_id: str
    anomaly_type: str
    severity: str = "medium"
    description: str = ""
    detected_at: str = field(default_factory=_now)
    metric_value: float = 0.0
    threshold_value: float = 0.0
    recommended_action: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NetcodeStats:
    """Aggregate statistics across all tracked netcode sessions."""
    total_sessions: int = 0
    active_sessions: int = 0
    total_samples: int = 0
    total_measurements: int = 0
    total_recommendations: int = 0
    total_anomalies: int = 0
    avg_rtt_ms: float = 0.0
    avg_packet_loss_pct: float = 0.0
    avg_bandwidth_kbps: float = 0.0
    strategy_distribution: Dict[str, int] = field(default_factory=dict)
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NetcodeSnapshot:
    """A point-in-time view of the director's state for diagnostics."""
    sessions: List[Dict[str, Any]] = field(default_factory=list)
    latency_samples: List[Dict[str, Any]] = field(default_factory=list)
    bandwidth_measurements: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NetcodeEvent:
    """An event emitted by the director for observability and audit."""
    event_id: str
    kind: NetcodeEventKind
    session_id: str
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Netcode Director Singleton
# ---------------------------------------------------------------------------


class NetcodeDirector:
    """AI-native fusion module optimizing multiplayer netcode at runtime."""

    _instance: Optional["NetcodeDirector"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "NetcodeDirector":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "NetcodeDirector":
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._sessions: Dict[str, NetcodeSession] = {}
            self._latency: Dict[str, List[LatencySample]] = {}
            self._bandwidth: Dict[str, List[BandwidthMeasurement]] = {}
            self._lag_configs: Dict[str, LagCompensationConfig] = {}
            self._regions: Dict[str, RegionProfile] = {}
            self._recommendations: Dict[str, NetcodeRecommendation] = {}
            self._anomalies: Dict[str, NetcodeAnomaly] = {}
            self._events: List[NetcodeEvent] = []
            self._seed_data()
            self._initialized = True

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(self, kind: NetcodeEventKind, session_id: str,
              payload: Dict[str, Any]) -> None:
        event = NetcodeEvent(
            event_id=_new_id("evt"),
            kind=kind,
            session_id=session_id,
            timestamp=_now(),
            payload=payload,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    @staticmethod
    def _coerce_strategy(value: Any) -> Optional[NetcodeStrategy]:
        if isinstance(value, NetcodeStrategy):
            return value
        if isinstance(value, str):
            try:
                return NetcodeStrategy(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _coerce_sync_mode(value: Any) -> Optional[SyncMode]:
        if isinstance(value, SyncMode):
            return value
        if isinstance(value, str):
            try:
                return SyncMode(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _coerce_bandwidth_profile(value: Any) -> Optional[BandwidthProfile]:
        if isinstance(value, BandwidthProfile):
            return value
        if isinstance(value, str):
            try:
                return BandwidthProfile(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _coerce_lag_compensation(value: Any) -> Optional[LagCompensation]:
        if isinstance(value, LagCompensation):
            return value
        if isinstance(value, str):
            try:
                return LagCompensation(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _coerce_region(value: Any) -> Optional[RegionCode]:
        if isinstance(value, RegionCode):
            return value
        if isinstance(value, str):
            try:
                return RegionCode(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _classify_latency(rtt_ms: float, jitter_ms: float,
                          packet_loss_pct: float) -> LatencyTier:
        if rtt_ms >= 250 or packet_loss_pct >= 10.0 or jitter_ms >= 100.0:
            return LatencyTier.CRITICAL
        if rtt_ms >= 150 or packet_loss_pct >= 5.0 or jitter_ms >= 60.0:
            return LatencyTier.POOR
        if rtt_ms >= 80 or packet_loss_pct >= 2.0 or jitter_ms >= 30.0:
            return LatencyTier.MODERATE
        if rtt_ms >= 40:
            return LatencyTier.GOOD
        return LatencyTier.EXCELLENT

    def _avg_latency(self, session_id: str) -> Tuple[float, float, float, int]:
        samples = self._latency.get(session_id, [])
        if not samples:
            return (0.0, 0.0, 0.0, 0)
        avg_rtt = sum(s.rtt_ms for s in samples) / len(samples)
        avg_jitter = sum(s.jitter_ms for s in samples) / len(samples)
        avg_loss = sum(s.packet_loss_pct for s in samples) / len(samples)
        return (avg_rtt, avg_jitter, avg_loss, len(samples))

    # ------------------------------------------------------------------
    # Session Lifecycle
    # ------------------------------------------------------------------

    def create_session(self, game_mode: str, player_count: Any = 0,
                       region: Any = "", strategy: Any = "", sync_mode: Any = "",
                       bandwidth_profile: Any = "", lag_compensation: Any = "",
                       target_tick_rate: Any = 30,
                       session_id: str = "", player_id: str = "") -> NetcodeSession:
        with self._lock:
            region_enum = self._coerce_region(region) or RegionCode.NA_EAST
            strategy_enum = self._coerce_strategy(strategy) or \
                NetcodeStrategy.SERVER_AUTHORITATIVE
            sync_enum = self._coerce_sync_mode(sync_mode) or SyncMode.STATE_SYNC
            bandwidth_enum = self._coerce_bandwidth_profile(bandwidth_profile) or \
                BandwidthProfile.BALANCED
            lag_enum = self._coerce_lag_compensation(lag_compensation) or \
                LagCompensation.NONE
            try:
                tick = int(target_tick_rate) if target_tick_rate else 30
            except (TypeError, ValueError):
                tick = 30
            try:
                pcount = int(player_count) if player_count else 0
            except (TypeError, ValueError):
                pcount = 0
            sid = session_id if session_id else _new_id("sess")
            session = NetcodeSession(
                session_id=sid,
                game_mode=game_mode,
                player_count=max(0, pcount),
                region=region_enum,
                strategy=strategy_enum,
                sync_mode=sync_enum,
                bandwidth_profile=bandwidth_enum,
                lag_compensation=lag_enum,
                target_tick_rate=max(1, tick),
                actual_tick_rate=float(tick),
            )
            self._sessions[session.session_id] = session
            _evict_fifo_dict(self._sessions, _MAX_SESSIONS)
            default_cfg = LagCompensationConfig(
                config_id=_new_id("lc"),
                session_id=session.session_id,
                compensation_type=lag_enum,
            )
            self._lag_configs[session.session_id] = default_cfg
            self._emit(NetcodeEventKind.SESSION_CREATED, session.session_id, {
                "game_mode": game_mode,
                "player_count": session.player_count,
                "region": region_enum.value,
            })
            self._emit(NetcodeEventKind.STRATEGY_SELECTED, session.session_id, {
                "strategy": strategy_enum.value,
                "sync_mode": sync_enum.value,
            })
            return session

    def get_session(self, session_id: str) -> Optional[NetcodeSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self, strategy: Any = None, region: Any = None,
                      status: str = None, limit: int = 100) -> List[NetcodeSession]:
        with self._lock:
            items = list(self._sessions.values())
            if strategy is not None:
                strategy_enum = self._coerce_strategy(strategy)
                if strategy_enum is not None:
                    items = [s for s in items if s.strategy == strategy_enum]
            if region is not None:
                region_enum = self._coerce_region(region)
                if region_enum is not None:
                    items = [s for s in items if s.region == region_enum]
            if status is not None:
                items = [s for s in items if s.status == status]
            return items[-limit:]

    def update_session(self, session_id: str, **kwargs: Any) -> Optional[NetcodeSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            immutable = {"session_id", "created_at"}
            for key, value in kwargs.items():
                if key in immutable:
                    continue
                if key == "strategy":
                    coerced = self._coerce_strategy(value)
                    if coerced is not None:
                        session.strategy = coerced
                elif key == "sync_mode":
                    coerced = self._coerce_sync_mode(value)
                    if coerced is not None:
                        session.sync_mode = coerced
                elif key == "bandwidth_profile":
                    coerced = self._coerce_bandwidth_profile(value)
                    if coerced is not None:
                        session.bandwidth_profile = coerced
                elif key == "lag_compensation":
                    coerced = self._coerce_lag_compensation(value)
                    if coerced is not None:
                        session.lag_compensation = coerced
                elif key == "region":
                    coerced = self._coerce_region(value)
                    if coerced is not None:
                        session.region = coerced
                elif hasattr(session, key):
                    setattr(session, key, value)
            session.updated_at = _now()
            self._emit(NetcodeEventKind.SESSION_UPDATED, session_id, {
                "fields": list(kwargs.keys()),
            })
            return session

    def close_session(self, session_id: str) -> Optional[NetcodeSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.status = "closed"
            session.updated_at = _now()
            self._emit(NetcodeEventKind.SESSION_CLOSED, session_id, {
                "strategy": session.strategy.value,
            })
            return session

    # ------------------------------------------------------------------
    # Latency Telemetry
    # ------------------------------------------------------------------

    def record_latency(self, session_id: str, player_id: str, region: Any,
                       rtt_ms: Any = 0.0, jitter_ms: float = 0.0,
                       packet_loss_pct: float = 0.0,
                       latency_ms: Any = None) -> Optional[LatencySample]:
        with self._lock:
            if session_id not in self._sessions:
                return None
            region_enum = self._coerce_region(region) or RegionCode.NA_EAST
            actual_rtt = latency_ms if latency_ms is not None else rtt_ms
            try:
                actual_rtt = float(actual_rtt) if actual_rtt else 0.0
            except (TypeError, ValueError):
                actual_rtt = 0.0
            sample = LatencySample(
                sample_id=_new_id("lat"),
                session_id=session_id,
                player_id=player_id,
                region=region_enum,
                rtt_ms=actual_rtt,
                jitter_ms=float(jitter_ms),
                packet_loss_pct=float(packet_loss_pct),
            )
            self._latency.setdefault(session_id, []).append(sample)
            _evict_fifo_list(self._latency[session_id], _MAX_LATENCY_SAMPLES)
            tier = self._classify_latency(rtt_ms, jitter_ms, packet_loss_pct)
            self._emit(NetcodeEventKind.LATENCY_UPDATED, session_id, {
                "player_id": player_id,
                "rtt_ms": sample.rtt_ms,
                "tier": tier.value,
            })
            self._emit(NetcodeEventKind.METRIC_RECORDED, session_id, {
                "metric": "latency",
                "sample_id": sample.sample_id,
            })
            return sample

    def list_latency_samples(self, session_id: str, limit: int = 100) -> List[LatencySample]:
        with self._lock:
            samples = self._latency.get(session_id, [])
            return list(samples[-limit:])

    # ------------------------------------------------------------------
    # Bandwidth Telemetry
    # ------------------------------------------------------------------

    def record_bandwidth(self, session_id: str, bytes_sent: Any = 0,
                         bytes_received: Any = 0, messages_sent: Any = 0,
                         messages_received: Any = 0,
                         compression_ratio: float = 1.0,
                         bytes_per_second: Any = None) -> Optional[BandwidthMeasurement]:
        with self._lock:
            if session_id not in self._sessions:
                return None
            if bytes_per_second is not None:
                try:
                    bps = int(bytes_per_second)
                except (TypeError, ValueError):
                    bps = 0
                bsent = bps
                brecv = 0
            else:
                try:
                    bsent = int(bytes_sent) if bytes_sent else 0
                except (TypeError, ValueError):
                    bsent = 0
                try:
                    brecv = int(bytes_received) if bytes_received else 0
                except (TypeError, ValueError):
                    brecv = 0
            try:
                msent = int(messages_sent) if messages_sent else 0
            except (TypeError, ValueError):
                msent = 0
            try:
                mrecv = int(messages_received) if messages_received else 0
            except (TypeError, ValueError):
                mrecv = 0
            measurement = BandwidthMeasurement(
                measurement_id=_new_id("bw"),
                session_id=session_id,
                bytes_sent=bsent,
                bytes_received=brecv,
                messages_sent=msent,
                messages_received=mrecv,
                compression_ratio=float(compression_ratio),
            )
            self._bandwidth.setdefault(session_id, []).append(measurement)
            _evict_fifo_list(self._bandwidth[session_id], _MAX_BANDWIDTH_MEASUREMENTS)
            self._emit(NetcodeEventKind.BANDWIDTH_ADJUSTED, session_id, {
                "bytes_sent": measurement.bytes_sent,
                "bytes_received": measurement.bytes_received,
                "compression_ratio": measurement.compression_ratio,
            })
            self._emit(NetcodeEventKind.METRIC_RECORDED, session_id, {
                "metric": "bandwidth",
                "measurement_id": measurement.measurement_id,
            })
            return measurement

    def list_bandwidth_measurements(self, session_id: str,
                                    limit: int = 100) -> List[BandwidthMeasurement]:
        with self._lock:
            measurements = self._bandwidth.get(session_id, [])
            return list(measurements[-limit:])

    # ------------------------------------------------------------------
    # Lag Compensation
    # ------------------------------------------------------------------

    def tune_lag_compensation(self, session_id: str, compensation_type: Any = "",
                              history_size_ms: Any = 200,
                              max_extrapolation_ms: Any = 50,
                              hit_registration_window_ms: Any = 100,
                              rewind_limit_ms: Any = 250,
                              lag_compensation_ms: Any = None,
                              mode: Any = None) -> Optional[LagCompensationConfig]:
        with self._lock:
            if session_id not in self._sessions:
                return None
            effective_type = mode if mode else compensation_type
            if lag_compensation_ms is not None and not effective_type:
                effective_type = "rewind"
            lag_enum = self._coerce_lag_compensation(effective_type) or \
                LagCompensation.NONE
            try:
                hs = int(history_size_ms) if history_size_ms else 200
            except (TypeError, ValueError):
                hs = 200
            try:
                me = int(max_extrapolation_ms) if max_extrapolation_ms else 50
            except (TypeError, ValueError):
                me = 50
            try:
                hr = int(hit_registration_window_ms) if hit_registration_window_ms else 100
            except (TypeError, ValueError):
                hr = 100
            try:
                rl = int(rewind_limit_ms) if rewind_limit_ms else 250
            except (TypeError, ValueError):
                rl = 250
            config = LagCompensationConfig(
                config_id=_new_id("lag"),
                session_id=session_id,
                compensation_type=lag_enum,
                history_size_ms=max(0, hs),
                max_extrapolation_ms=max(0, me),
                hit_registration_window_ms=max(0, hr),
                rewind_limit_ms=max(0, rl),
            )
            self._lag_configs[session_id] = config
            _evict_fifo_dict(self._lag_configs, _MAX_LAG_CONFIGS)
            session = self._sessions.get(session_id)
            if session is not None:
                session.lag_compensation = lag_enum
                session.updated_at = _now()
            self._emit(NetcodeEventKind.LAG_COMPENSATION_TUNED, session_id, {
                "compensation_type": lag_enum.value,
                "history_size_ms": config.history_size_ms,
                "rewind_limit_ms": config.rewind_limit_ms,
            })
            self._emit(NetcodeEventKind.CONFIG_CHANGED, session_id, {
                "scope": "lag_compensation",
            })
            return config

    def get_lag_compensation(self, session_id: str) -> Optional[LagCompensationConfig]:
        with self._lock:
            return self._lag_configs.get(session_id)

    # ------------------------------------------------------------------
    # Region Management
    # ------------------------------------------------------------------

    def register_region(self, region_code: Any, region_name: str = "",
                        avg_latency_ms: Any = 0.0, player_density: Any = 0,
                        server_capacity: Any = 0, load_factor: Any = 0.0,
                        recommended_strategy: Any = "",
                        name: str = "",
                        latency_baseline_ms: Any = None) -> Optional[RegionProfile]:
        with self._lock:
            region_enum = self._coerce_region(region_code)
            if region_enum is None:
                return None
            effective_name = name if name else region_name
            effective_latency = latency_baseline_ms if latency_baseline_ms is not None else avg_latency_ms
            try:
                lat = float(effective_latency) if effective_latency else 0.0
            except (TypeError, ValueError):
                lat = 0.0
            strategy_enum = self._coerce_strategy(recommended_strategy) or \
                NetcodeStrategy.SERVER_AUTHORITATIVE
            profile = RegionProfile(
                region_code=region_enum,
                region_name=effective_name,
                avg_latency_ms=lat,
                player_density=max(0, int(player_density) if player_density else 0),
                server_capacity=max(0, int(server_capacity) if server_capacity else 0),
                load_factor=float(load_factor) if load_factor else 0.0,
                recommended_strategy=strategy_enum,
            )
            self._regions[region_enum.value] = profile
            _evict_fifo_dict(self._regions, _MAX_REGIONS)
            self._emit(NetcodeEventKind.REGION_OPTIMIZED, "", {
                "region": region_enum.value,
                "avg_latency_ms": profile.avg_latency_ms,
                "recommended_strategy": strategy_enum.value,
            })
            return profile

    def get_region(self, region_code: Any) -> Optional[RegionProfile]:
        with self._lock:
            region_enum = self._coerce_region(region_code)
            if region_enum is None:
                return None
            return self._regions.get(region_enum.value)

    def list_regions(self) -> List[RegionProfile]:
        with self._lock:
            return list(self._regions.values())

    # ------------------------------------------------------------------
    # Strategy Analysis
    # ------------------------------------------------------------------

    def analyze_session(self, session_id: str) -> Optional[NetcodeRecommendation]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            avg_rtt, avg_jitter, avg_loss, sample_count = self._avg_latency(session_id)
            current = session.strategy
            recommended = current
            reason = (
                "Current strategy remains appropriate for observed network conditions."
            )
            confidence = 0.5
            expected_improvement = 0.0
            priority = "low"

            if sample_count == 0:
                reason = "Insufficient latency data; retaining current strategy."
                confidence = 0.3
            elif avg_rtt >= 150 or avg_loss >= 5.0:
                recommended = NetcodeStrategy.ROLLBACK
                reason = (
                    "Elevated RTT and packet loss favor rollback to mask remote "
                    "input delay and keep local play responsive."
                )
                confidence = 0.85
                expected_improvement = 0.4
                priority = "high"
            elif avg_rtt < 50 and avg_loss < 1.0:
                if session.player_count <= 4:
                    recommended = NetcodeStrategy.PREDICTION_RECONCILIATION
                    reason = (
                        "Low latency enables tight prediction and reconciliation "
                        "for responsive competitive play."
                    )
                    confidence = 0.8
                    expected_improvement = 0.2
                    priority = "medium"
                else:
                    recommended = NetcodeStrategy.SERVER_AUTHORITATIVE
                    reason = (
                        "Low latency with a larger player count favors server "
                        "authority for consistency."
                    )
                    confidence = 0.75
                    expected_improvement = 0.15
                    priority = "medium"
            elif avg_jitter >= 40:
                recommended = NetcodeStrategy.HYBRID
                reason = (
                    "Elevated jitter benefits from a hybrid approach mixing "
                    "prediction with reconciliation."
                )
                confidence = 0.7
                expected_improvement = 0.25
                priority = "medium"
            elif session.player_count >= 32 and current != NetcodeStrategy.SERVER_AUTHORITATIVE:
                recommended = NetcodeStrategy.SERVER_AUTHORITATIVE
                reason = (
                    "Large player counts benefit from server authority to limit "
                    "desync and bandwidth blowup."
                )
                confidence = 0.65
                expected_improvement = 0.2
                priority = "medium"

            recommendation = NetcodeRecommendation(
                recommendation_id=_new_id("rec"),
                session_id=session_id,
                current_strategy=current,
                recommended_strategy=recommended,
                reason=reason,
                confidence=confidence,
                expected_improvement=expected_improvement,
                priority=priority,
            )
            self._recommendations[recommendation.recommendation_id] = recommendation
            _evict_fifo_dict(self._recommendations, _MAX_RECOMMENDATIONS)
            self._emit(NetcodeEventKind.RECOMMENDATION_ISSUED, session_id, {
                "recommendation_id": recommendation.recommendation_id,
                "current_strategy": current.value,
                "recommended_strategy": recommended.value,
                "confidence": confidence,
                "priority": priority,
            })
            return recommendation

    def list_recommendations(self, session_id: str, limit: int = 50) -> List[NetcodeRecommendation]:
        with self._lock:
            items = [r for r in self._recommendations.values()
                     if r.session_id == session_id]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Anomaly Detection
    # ------------------------------------------------------------------

    def detect_anomalies(self, session_id: str) -> List[NetcodeAnomaly]:
        with self._lock:
            if session_id not in self._sessions:
                return []
            anomalies: List[NetcodeAnomaly] = []
            samples = self._latency.get(session_id, [])
            if samples:
                recent = samples[-20:]
                avg_rtt = sum(s.rtt_ms for s in recent) / len(recent)
                max_rtt = max(s.rtt_ms for s in recent)
                avg_loss = sum(s.packet_loss_pct for s in recent) / len(recent)
                max_loss = max(s.packet_loss_pct for s in recent)
                max_jitter = max(s.jitter_ms for s in recent)

                if max_rtt >= 300.0:
                    anomaly = NetcodeAnomaly(
                        anomaly_id=_new_id("anm"),
                        session_id=session_id,
                        anomaly_type="lag_spike",
                        severity="high",
                        description=(
                            f"Detected lag spike with max RTT {max_rtt:.1f} ms "
                            f"exceeding 300 ms threshold."
                        ),
                        metric_value=max_rtt,
                        threshold_value=300.0,
                        recommended_action="Switch to rollback strategy and raise interpolation delay.",
                    )
                    self._anomalies[anomaly.anomaly_id] = anomaly
                    _evict_fifo_dict(self._anomalies, _MAX_ANOMALIES)
                    anomalies.append(anomaly)
                    self._emit(NetcodeEventKind.ANOMALY_DETECTED, session_id, {
                        "anomaly_id": anomaly.anomaly_id,
                        "anomaly_type": anomaly.anomaly_type,
                        "severity": anomaly.severity,
                    })

                if avg_loss >= 5.0:
                    anomaly = NetcodeAnomaly(
                        anomaly_id=_new_id("anm"),
                        session_id=session_id,
                        anomaly_type="packet_loss_burst",
                        severity="high" if avg_loss >= 10.0 else "medium",
                        description=(
                            f"Average packet loss {avg_loss:.2f}% indicates a "
                            f"sustained loss burst affecting delivery."
                        ),
                        metric_value=avg_loss,
                        threshold_value=5.0,
                        recommended_action="Enable delta compression and raise resend budget.",
                    )
                    self._anomalies[anomaly.anomaly_id] = anomaly
                    _evict_fifo_dict(self._anomalies, _MAX_ANOMALIES)
                    anomalies.append(anomaly)
                    self._emit(NetcodeEventKind.ANOMALY_DETECTED, session_id, {
                        "anomaly_id": anomaly.anomaly_id,
                        "anomaly_type": anomaly.anomaly_type,
                        "severity": anomaly.severity,
                    })

                if max_jitter >= 100.0:
                    anomaly = NetcodeAnomaly(
                        anomaly_id=_new_id("anm"),
                        session_id=session_id,
                        anomaly_type="jitter_burst",
                        severity="medium",
                        description=(
                            f"Jitter spike of {max_jitter:.1f} ms exceeds 100 ms "
                            f"threshold and may cause stutter."
                        ),
                        metric_value=max_jitter,
                        threshold_value=100.0,
                        recommended_action="Increase snapshot interpolation delay and smooth inputs.",
                    )
                    self._anomalies[anomaly.anomaly_id] = anomaly
                    _evict_fifo_dict(self._anomalies, _MAX_ANOMALIES)
                    anomalies.append(anomaly)
                    self._emit(NetcodeEventKind.ANOMALY_DETECTED, session_id, {
                        "anomaly_id": anomaly.anomaly_id,
                        "anomaly_type": anomaly.anomaly_type,
                        "severity": anomaly.severity,
                    })

                if max_loss >= 20.0:
                    anomaly = NetcodeAnomaly(
                        anomaly_id=_new_id("anm"),
                        session_id=session_id,
                        anomaly_type="severe_packet_loss",
                        severity="critical",
                        description=(
                            f"Severe packet loss of {max_loss:.2f}% will cause "
                            f"meaningful gameplay degradation."
                        ),
                        metric_value=max_loss,
                        threshold_value=20.0,
                        recommended_action="Migrate session to a healthier region or pause ranked play.",
                    )
                    self._anomalies[anomaly.anomaly_id] = anomaly
                    _evict_fifo_dict(self._anomalies, _MAX_ANOMALIES)
                    anomalies.append(anomaly)
                    self._emit(NetcodeEventKind.ANOMALY_DETECTED, session_id, {
                        "anomaly_id": anomaly.anomaly_id,
                        "anomaly_type": anomaly.anomaly_type,
                        "severity": anomaly.severity,
                    })

            measurements = self._bandwidth.get(session_id, [])
            if measurements:
                recent_bw = measurements[-10:]
                avg_compression = sum(m.compression_ratio for m in recent_bw) / len(recent_bw)
                if avg_compression < 0.5:
                    anomaly = NetcodeAnomaly(
                        anomaly_id=_new_id("anm"),
                        session_id=session_id,
                        anomaly_type="compression_regression",
                        severity="medium",
                        description=(
                            f"Average compression ratio {avg_compression:.2f} dropped "
                            f"below 0.5, indicating inefficient payload encoding."
                        ),
                        metric_value=avg_compression,
                        threshold_value=0.5,
                        recommended_action="Tighten delta compression and prioritize critical state.",
                    )
                    self._anomalies[anomaly.anomaly_id] = anomaly
                    _evict_fifo_dict(self._anomalies, _MAX_ANOMALIES)
                    anomalies.append(anomaly)
                    self._emit(NetcodeEventKind.ANOMALY_DETECTED, session_id, {
                        "anomaly_id": anomaly.anomaly_id,
                        "anomaly_type": anomaly.anomaly_type,
                        "severity": anomaly.severity,
                    })

            return anomalies

    def list_anomalies(self, session_id: str, limit: int = 50) -> List[NetcodeAnomaly]:
        with self._lock:
            items = [a for a in self._anomalies.values()
                     if a.session_id == session_id]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100,
                    kind: Any = None) -> List[NetcodeEvent]:
        with self._lock:
            items = list(self._events)
            if kind is not None:
                if isinstance(kind, NetcodeEventKind):
                    items = [e for e in items if e.kind == kind]
                elif isinstance(kind, str):
                    try:
                        kind_enum = NetcodeEventKind(kind)
                        items = [e for e in items if e.kind == kind_enum]
                    except ValueError:
                        items = []
            return items[-limit:]

    def get_stats(self) -> NetcodeStats:
        with self._lock:
            total_samples = sum(len(s) for s in self._latency.values())
            total_measurements = sum(len(m) for m in self._bandwidth.values())
            active_sessions = sum(1 for s in self._sessions.values()
                                  if s.status == "active")
            all_samples: List[LatencySample] = []
            for sample_list in self._latency.values():
                all_samples.extend(sample_list)
            avg_rtt = (sum(s.rtt_ms for s in all_samples) / len(all_samples)
                       if all_samples else 0.0)
            avg_loss = (sum(s.packet_loss_pct for s in all_samples) / len(all_samples)
                        if all_samples else 0.0)
            total_bytes = sum(
                m.bytes_sent + m.bytes_received
                for measurements in self._bandwidth.values()
                for m in measurements
            )
            avg_bandwidth_kbps = 0.0
            if total_measurements > 0:
                avg_bandwidth_kbps = (total_bytes / total_measurements) / 1024.0
            strategy_distribution: Dict[str, int] = {}
            for session in self._sessions.values():
                key = session.strategy.value
                strategy_distribution[key] = strategy_distribution.get(key, 0) + 1
            return NetcodeStats(
                total_sessions=len(self._sessions),
                active_sessions=active_sessions,
                total_samples=total_samples,
                total_measurements=total_measurements,
                total_recommendations=len(self._recommendations),
                total_anomalies=len(self._anomalies),
                avg_rtt_ms=avg_rtt,
                avg_packet_loss_pct=avg_loss,
                avg_bandwidth_kbps=avg_bandwidth_kbps,
                strategy_distribution=strategy_distribution,
                last_updated=_now(),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "sessions": len(self._sessions),
                "latency_samples": sum(len(s) for s in self._latency.values()),
                "bandwidth_measurements": sum(len(m) for m in self._bandwidth.values()),
                "lag_configs": len(self._lag_configs),
                "regions": len(self._regions),
                "recommendations": len(self._recommendations),
                "anomalies": len(self._anomalies),
                "events": len(self._events),
            }

    def get_snapshot(self) -> NetcodeSnapshot:
        with self._lock:
            sessions = [s.to_dict() for s in list(self._sessions.values())[:20]]
            latency_samples: List[Dict[str, Any]] = []
            for sample_list in self._latency.values():
                latency_samples.extend(s.to_dict() for s in sample_list)
            latency_samples = latency_samples[-20:]
            bandwidth_measurements: List[Dict[str, Any]] = []
            for measurement_list in self._bandwidth.values():
                bandwidth_measurements.extend(m.to_dict() for m in measurement_list)
            bandwidth_measurements = bandwidth_measurements[-20:]
            recommendations = [r.to_dict() for r in list(self._recommendations.values())[-20:]]
            anomalies = [a.to_dict() for a in list(self._anomalies.values())[-20:]]
            return NetcodeSnapshot(
                sessions=sessions,
                latency_samples=latency_samples,
                bandwidth_measurements=bandwidth_measurements,
                recommendations=recommendations,
                anomalies=anomalies,
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._latency.clear()
            self._bandwidth.clear()
            self._lag_configs.clear()
            self._regions.clear()
            self._recommendations.clear()
            self._anomalies.clear()
            self._events.clear()
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        # Regions
        na_east = RegionProfile(
            region_code=RegionCode.NA_EAST,
            region_name="North America East",
            avg_latency_ms=35.0,
            player_density=4200,
            server_capacity=8000,
            load_factor=0.52,
            recommended_strategy=NetcodeStrategy.SERVER_AUTHORITATIVE,
        )
        self._regions[na_east.region_code.value] = na_east

        eu_west = RegionProfile(
            region_code=RegionCode.EU_WEST,
            region_name="Europe West",
            avg_latency_ms=42.0,
            player_density=5100,
            server_capacity=9000,
            load_factor=0.57,
            recommended_strategy=NetcodeStrategy.PREDICTION_RECONCILIATION,
        )
        self._regions[eu_west.region_code.value] = eu_west

        ap_east = RegionProfile(
            region_code=RegionCode.AP_EAST,
            region_name="Asia Pacific East",
            avg_latency_ms=58.0,
            player_density=6300,
            server_capacity=10000,
            load_factor=0.63,
            recommended_strategy=NetcodeStrategy.HYBRID,
        )
        self._regions[ap_east.region_code.value] = ap_east

        # Sessions
        session1 = NetcodeSession(
            session_id="sess_seed_1",
            game_mode="team_deathmatch",
            player_count=8,
            region=RegionCode.NA_EAST,
            strategy=NetcodeStrategy.SERVER_AUTHORITATIVE,
            sync_mode=SyncMode.STATE_SYNC,
            bandwidth_profile=BandwidthProfile.BALANCED,
            lag_compensation=LagCompensation.BACKWARD_RECONCILIATION,
            target_tick_rate=30,
            actual_tick_rate=29.8,
            interpolation_delay_ms=100,
            created_at="2025-09-01T12:00:00Z",
            updated_at="2025-09-01T12:05:00Z",
            status="active",
        )
        self._sessions[session1.session_id] = session1

        session2 = NetcodeSession(
            session_id="sess_seed_2",
            game_mode="battle_royale",
            player_count=60,
            region=RegionCode.EU_WEST,
            strategy=NetcodeStrategy.HYBRID,
            sync_mode=SyncMode.SNAPSHOT_INTERPOLATION,
            bandwidth_profile=BandwidthProfile.PRIORITY_BASED,
            lag_compensation=LagCompensation.HYBRID_COMPENSATION,
            target_tick_rate=20,
            actual_tick_rate=19.5,
            interpolation_delay_ms=150,
            created_at="2025-09-01T13:00:00Z",
            updated_at="2025-09-01T13:10:00Z",
            status="active",
        )
        self._sessions[session2.session_id] = session2

        # Latency samples for session 1
        self._latency["sess_seed_1"] = [
            LatencySample(
                sample_id="lat_seed_1",
                session_id="sess_seed_1",
                player_id="player_alpha",
                region=RegionCode.NA_EAST,
                rtt_ms=32.0,
                jitter_ms=4.0,
                packet_loss_pct=0.2,
                timestamp="2025-09-01T12:01:00Z",
            ),
            LatencySample(
                sample_id="lat_seed_2",
                session_id="sess_seed_1",
                player_id="player_beta",
                region=RegionCode.NA_EAST,
                rtt_ms=48.0,
                jitter_ms=6.5,
                packet_loss_pct=0.4,
                timestamp="2025-09-01T12:02:00Z",
            ),
            LatencySample(
                sample_id="lat_seed_3",
                session_id="sess_seed_1",
                player_id="player_gamma",
                region=RegionCode.NA_EAST,
                rtt_ms=320.0,
                jitter_ms=110.0,
                packet_loss_pct=22.0,
                timestamp="2025-09-01T12:03:00Z",
            ),
        ]

        # Latency samples for session 2
        self._latency["sess_seed_2"] = [
            LatencySample(
                sample_id="lat_seed_4",
                session_id="sess_seed_2",
                player_id="player_delta",
                region=RegionCode.EU_WEST,
                rtt_ms=55.0,
                jitter_ms=9.0,
                packet_loss_pct=0.6,
                timestamp="2025-09-01T13:01:00Z",
            ),
            LatencySample(
                sample_id="lat_seed_5",
                session_id="sess_seed_2",
                player_id="player_epsilon",
                region=RegionCode.EU_WEST,
                rtt_ms=72.0,
                jitter_ms=12.0,
                packet_loss_pct=1.1,
                timestamp="2025-09-01T13:02:00Z",
            ),
        ]

        # Bandwidth measurements for session 1
        self._bandwidth["sess_seed_1"] = [
            BandwidthMeasurement(
                measurement_id="bw_seed_1",
                session_id="sess_seed_1",
                bytes_sent=128000,
                bytes_received=96400,
                messages_sent=320,
                messages_received=410,
                compression_ratio=0.62,
                timestamp="2025-09-01T12:01:30Z",
            ),
            BandwidthMeasurement(
                measurement_id="bw_seed_2",
                session_id="sess_seed_1",
                bytes_sent=145200,
                bytes_received=101800,
                messages_sent=355,
                messages_received=438,
                compression_ratio=0.58,
                timestamp="2025-09-01T12:02:30Z",
            ),
            BandwidthMeasurement(
                measurement_id="bw_seed_3",
                session_id="sess_seed_1",
                bytes_sent=161000,
                bytes_received=112500,
                messages_sent=388,
                messages_received=472,
                compression_ratio=0.55,
                timestamp="2025-09-01T12:03:30Z",
            ),
        ]

        # Lag compensation config for session 1
        lag_config = LagCompensationConfig(
            config_id="lag_seed_1",
            session_id="sess_seed_1",
            compensation_type=LagCompensation.BACKWARD_RECONCILIATION,
            history_size_ms=220,
            max_extrapolation_ms=60,
            hit_registration_window_ms=120,
            rewind_limit_ms=260,
        )
        self._lag_configs[lag_config.session_id] = lag_config

        # Recommendation for session 1
        recommendation = NetcodeRecommendation(
            recommendation_id="rec_seed_1",
            session_id="sess_seed_1",
            current_strategy=NetcodeStrategy.SERVER_AUTHORITATIVE,
            recommended_strategy=NetcodeStrategy.ROLLBACK,
            reason=(
                "One player shows RTT above 200 ms with elevated packet loss; "
                "rollback will mask input delay and keep local play responsive."
            ),
            confidence=0.82,
            expected_improvement=0.35,
            priority="high",
            created_at="2025-09-01T12:04:00Z",
        )
        self._recommendations[recommendation.recommendation_id] = recommendation


def get_netcode_director() -> NetcodeDirector:
    """Factory function returning the singleton NetcodeDirector instance."""
    return NetcodeDirector.get_instance()
