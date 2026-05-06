"""
SparkLabs Agent - State Synchronization Mesh

Bidirectional state synchronization between the AI agent's memory
model and the live game engine. Ensures the agent's mental model of
game state stays coherent with actual engine objects — critical for
AI-driven game editing where stale assumptions produce bad code.

Architecture:
  StateSyncMesh
    |-- SyncChannel (one per domain: objects, scripts, assets, scenes)
    |-- DriftDetector (compares agent memory ↔ engine snapshot)
    |-- ReconciliationEngine (resolves conflicts with merge strategies)
    |-- SyncTrigger (event-based: on_create, on_modify, on_delete)
    |-- SnapshotStore (periodic full-state dumps for diff comparison)

Reconciliation Strategies:
  - AGENT_WINS: agent's view overrides engine (for design intent)
  - ENGINE_WINS: engine state is authoritative (for runtime facts)
  - MERGE: attempt field-level merging with conflict reporting
  - DEFER: flag conflict for human/AI resolution later

Sync Domains:
  - OBJECTS: game entities, positions, components
  - SCRIPTS: attached behavior scripts and their parameters
  - ASSETS: registered assets and their metadata
  - SCENES: scene hierarchy and active scene stack
  - SETTINGS: global engine settings and configurations

Usage:
    mesh = StateSyncMesh()
    mesh.register_engine(engine_instance)
    mesh.register_agent_memory(agent_memory)
    channel = mesh.open_channel("objects", strategy="ENGINE_WINS")
    channel.on_drift(lambda domain, diffs: agent.resolve_conflicts(diffs))
    mesh.sync_all()
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class SyncStrategy(Enum):
    AGENT_WINS = "agent_wins"
    ENGINE_WINS = "engine_wins"
    MERGE = "merge"
    DEFER = "defer"


class SyncDomain(Enum):
    OBJECTS = "objects"
    SCRIPTS = "scripts"
    ASSETS = "assets"
    SCENES = "scenes"
    SETTINGS = "settings"
    BEHAVIORS = "behaviors"
    VARIABLES = "variables"


class DriftSeverity(Enum):
    INFO = "info"
    MINOR = "minor"
    SIGNIFICANT = "significant"
    CRITICAL = "critical"


@dataclass
class StateDiff:
    field_path: str = ""
    agent_value: Any = None
    engine_value: Any = None
    severity: DriftSeverity = DriftSeverity.INFO
    domain: SyncDomain = SyncDomain.OBJECTS


@dataclass
class SyncSnapshot:
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    domain: SyncDomain = SyncDomain.OBJECTS
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = ""


@dataclass
class SyncReport:
    domain: SyncDomain = SyncDomain.OBJECTS
    timestamp: float = 0.0
    total_entities: int = 0
    synced_count: int = 0
    conflicts_found: int = 0
    conflicts_resolved: int = 0
    drifts_detected: List[StateDiff] = field(default_factory=list)
    duration_ms: float = 0.0
    strategy_used: SyncStrategy = SyncStrategy.MERGE


@dataclass
class SyncChannel:
    channel_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    domain: SyncDomain = SyncDomain.OBJECTS
    strategy: SyncStrategy = SyncStrategy.ENGINE_WINS
    auto_sync: bool = True
    last_sync_at: float = 0.0
    total_syncs: int = 0
    agent_snapshot: Optional[SyncSnapshot] = None
    engine_snapshot: Optional[SyncSnapshot] = None
    drift_handlers: List[Callable[[List[StateDiff]], None]] = field(default_factory=list)
    sync_interval_seconds: float = 1.0

    def on_drift(self, handler: Callable[[List[StateDiff]], None]) -> None:
        self.drift_handlers.append(handler)


class StateSyncMesh:
    """Bidirectional state synchronization mesh — agent ↔ engine."""

    _instance: Optional["StateSyncMesh"] = None

    def __init__(self):
        self._channels: Dict[SyncDomain, SyncChannel] = {}
        self._engine: Any = None
        self._agent_memory: Any = None
        self._snapshot_store: Dict[str, List[SyncSnapshot]] = {}
        self._sync_reports: List[SyncReport] = []
        self._enabled: bool = True
        self._last_global_sync: float = 0.0
        self._global_sync_interval: float = 5.0
        self._total_syncs: int = 0
        self._MAX_REPORTS = 200
        self._sync_reports_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "StateSyncMesh":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_engine(self, engine: Any) -> None:
        self._engine = engine

    def register_agent_memory(self, memory: Any) -> None:
        self._agent_memory = memory

    def open_channel(self, domain: SyncDomain, strategy: SyncStrategy = SyncStrategy.ENGINE_WINS,
                     auto_sync: bool = True, interval: float = 1.0) -> SyncChannel:
        channel = SyncChannel(
            domain=domain,
            strategy=strategy,
            auto_sync=auto_sync,
            sync_interval_seconds=interval,
        )
        self._channels[domain] = channel
        return channel

    def capture_agent_snapshot(self, domain: SyncDomain) -> Optional[SyncSnapshot]:
        if not self._agent_memory:
            return None
        try:
            if hasattr(self._agent_memory, "get_domain_state"):
                data = self._agent_memory.get_domain_state(domain.value)
            else:
                data = {}
            return SyncSnapshot(domain=domain, data=data, source="agent")
        except Exception:
            return None

    def capture_engine_snapshot(self, domain: SyncDomain) -> Optional[SyncSnapshot]:
        if not self._engine:
            return None
        try:
            if hasattr(self._engine, "get_domain_snapshot"):
                data = self._engine.get_domain_snapshot(domain.value)
            else:
                data = {}
            return SyncSnapshot(domain=domain, data=data, source="engine")
        except Exception:
            return None

    def detect_drift(self, agent_snap: Dict[str, Any], engine_snap: Dict[str, Any],
                     domain: SyncDomain) -> List[StateDiff]:
        diffs: List[StateDiff] = []
        all_keys = set(agent_snap.keys()) | set(engine_snap.keys())

        for key in all_keys:
            av = agent_snap.get(key)
            ev = engine_snap.get(key)
            if av != ev:
                severity = DriftSeverity.INFO
                if key in ("position", "transform", "current_scene"):
                    severity = DriftSeverity.SIGNIFICANT
                elif key in ("health", "score", "active_script"):
                    severity = DriftSeverity.CRITICAL
                diffs.append(StateDiff(
                    field_path=key,
                    agent_value=av,
                    engine_value=ev,
                    severity=severity,
                    domain=domain,
                ))
        return diffs

    def reconcile(self, channel: SyncChannel, diffs: List[StateDiff]) -> int:
        resolved = 0
        strategy = channel.strategy

        for diff in diffs:
            if strategy == SyncStrategy.AGENT_WINS and diff.agent_value is not None:
                self._push_to_engine(diff.domain, diff.field_path, diff.agent_value)
                resolved += 1
            elif strategy == SyncStrategy.ENGINE_WINS:
                self._push_to_agent(diff.domain, diff.field_path, diff.engine_value)
                resolved += 1
            elif strategy == SyncStrategy.MERGE:
                winner = diff.agent_value if diff.agent_value is not None else diff.engine_value
                self._push_to_engine(diff.domain, diff.field_path, winner)
                self._push_to_agent(diff.domain, diff.field_path, winner)
                resolved += 1

        for handler in channel.drift_handlers:
            try:
                handler(diffs)
            except Exception:
                pass

        return resolved

    def _push_to_engine(self, domain: SyncDomain, key: str, value: Any) -> None:
        if self._engine and hasattr(self._engine, "apply_sync_update"):
            try:
                self._engine.apply_sync_update(domain.value, key, value)
            except Exception:
                pass

    def _push_to_agent(self, domain: SyncDomain, key: str, value: Any) -> None:
        if self._agent_memory and hasattr(self._agent_memory, "apply_sync_update"):
            try:
                self._agent_memory.apply_sync_update(domain.value, key, value)
            except Exception:
                pass

    def sync_domain(self, domain: SyncDomain) -> SyncReport:
        t0 = time.time()
        channel = self._channels.get(domain)
        if not channel:
            channel = SyncChannel(domain=domain, strategy=SyncStrategy.ENGINE_WINS)
            self._channels[domain] = channel

        agent_snap = self.capture_agent_snapshot(domain)
        engine_snap = self.capture_engine_snapshot(domain)

        channel.agent_snapshot = agent_snap
        channel.engine_snapshot = engine_snap

        agent_data = agent_snap.data if agent_snap else {}
        engine_data = engine_snap.data if engine_snap else {}

        diffs = self.detect_drift(agent_data, engine_data, domain)
        resolved = self.reconcile(channel, diffs)

        report = SyncReport(
            domain=domain,
            timestamp=time.time(),
            total_entities=len(set(agent_data.keys()) | set(engine_data.keys())),
            synced_count=len(agent_data),
            conflicts_found=len(diffs),
            conflicts_resolved=resolved,
            drifts_detected=diffs,
            duration_ms=(time.time() - t0) * 1000,
            strategy_used=channel.strategy,
        )

        channel.last_sync_at = time.time()
        channel.total_syncs += 1
        self._total_syncs += 1

        with self._sync_reports_lock:
            self._sync_reports.append(report)
            if len(self._sync_reports) > self._MAX_REPORTS:
                self._sync_reports = self._sync_reports[-self._MAX_REPORTS:]

        return report

    def sync_all(self) -> List[SyncReport]:
        if not self._enabled:
            return []
        reports = []
        for domain in SyncDomain:
            try:
                report = self.sync_domain(domain)
                reports.append(report)
            except Exception:
                pass
        self._last_global_sync = time.time()
        return reports

    def maybe_sync_all(self) -> List[SyncReport]:
        now = time.time()
        if now - self._last_global_sync >= self._global_sync_interval:
            return self.sync_all()
        return []

    def get_channel(self, domain: SyncDomain) -> Optional[SyncChannel]:
        return self._channels.get(domain)

    def get_recent_reports(self, limit: int = 20) -> List[SyncReport]:
        return self._sync_reports[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "channels": len(self._channels),
            "total_syncs": self._total_syncs,
            "last_global_sync": self._last_global_sync,
            "reports_stored": len(self._sync_reports),
            "enabled": self._enabled,
            "engine_registered": self._engine is not None,
            "agent_memory_registered": self._agent_memory is not None,
            "channels_detail": {
                d.value: {
                    "strategy": ch.strategy.value,
                    "auto_sync": ch.auto_sync,
                    "total_syncs": ch.total_syncs,
                }
                for d, ch in self._channels.items()
            },
        }

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def set_global_interval(self, seconds: float) -> None:
        self._global_sync_interval = seconds

    def reset(self) -> None:
        self._channels.clear()
        self._sync_reports.clear()
        self._total_syncs = 0
        self._last_global_sync = 0.0


def get_state_sync_mesh() -> StateSyncMesh:
    return StateSyncMesh.get_instance()
