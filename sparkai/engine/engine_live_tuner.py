"""
SparkLabs Engine - Live Tuner

The EngineLiveTuner is the autonomic optimization system of the AI-native
game engine. It continuously monitors engine performance metrics, player
experience data, and system health indicators, then autonomously tunes
engine parameters to maintain optimal performance and player experience.

Unlike manual tuning or static configuration, the Live Tuner:
  1. Monitors real-time metrics from every engine subsystem
  2. Detects performance degradation and player friction
  3. Identifies the optimal parameter adjustments
  4. Applies changes gradually with rollback safety
  5. Learns which adjustments work for each scenario

Tuning Domains:
  - PHYSICS: gravity, friction, restitution, substep count
  - RENDER: draw distance, shadow quality, texture LOD, post-processing
  - AUDIO: volume levels, doppler factor, reverb, 3D audio distance
  - GAMEPLAY: difficulty, spawn rate, health regen, XP curve
  - AI: pathfinding accuracy, behavior tree tick rate, perception range
  - MEMORY: cache size, pool allocation, GC frequency

The tuner runs a tuning cycle every 3 seconds:
  MONITOR -> ANALYZE -> DECIDE -> APPLY -> VERIFY

Each parameter has:
  - A current value
  - A min/max range
  - A target value (what the tuner thinks is optimal)
  - A confidence score (how sure the tuner is)
  - An adjustment rate (how fast to move toward target)
  - A rollback threshold (if metrics worsen beyond this, revert)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class TuningDomain(Enum):
    """Domains of engine parameters that can be tuned."""
    PHYSICS = "physics"
    RENDER = "render"
    AUDIO = "audio"
    GAMEPLAY = "gameplay"
    AI = "ai"
    MEMORY = "memory"
    NETWORK = "network"


class TuningAction(Enum):
    """Actions the tuner can take on a parameter."""
    INCREASE = "increase"
    DECREASE = "decrease"
    HOLD = "hold"
    ROLLBACK = "rollback"
    RESET = "reset"


class MetricType(Enum):
    """Types of metrics monitored by the tuner."""
    FPS = "fps"
    FRAME_TIME = "frame_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    GPU_USAGE = "gpu_usage"
    PLAYER_ENGAGEMENT = "player_engagement"
    PLAYER_FRUSTRATION = "player_frustration"
    DEATH_RATE = "death_rate"
    COMPLETION_RATE = "completion_rate"
    LATENCY = "latency"
    DRAW_CALLS = "draw_calls"
    PHYSICS_STEPS = "physics_steps"


class TunerPhase(Enum):
    """Phases of the tuning cycle."""
    MONITOR = "monitor"
    ANALYZE = "analyze"
    DECIDE = "decide"
    APPLY = "apply"
    VERIFY = "verify"


class AdjustStatus(Enum):
    """Status of a parameter adjustment."""
    PENDING = "pending"
    APPLIED = "applied"
    VERIFIED = "verified"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class TunableParameter:
    """A parameter that can be tuned by the live tuner."""
    param_id: str
    name: str
    domain: TuningDomain
    description: str
    current_value: float
    default_value: float
    min_value: float
    max_value: float
    target_value: float = 0.0
    confidence: float = 0.5  # 0.0 to 1.0
    adjustment_rate: float = 0.1  # How fast to move toward target
    unit: str = ""
    last_adjusted: float = 0.0
    adjustment_count: int = 0
    rollback_count: int = 0
    last_metric_before: Optional[float] = None
    last_metric_after: Optional[float] = None
    impact_score: float = 0.0  # How much this parameter affects metrics


@dataclass
class MetricSample:
    """A single metric sample."""
    metric_type: MetricType
    value: float
    timestamp: float
    context: str = ""  # Additional context (scene, level, etc.)


@dataclass
class AdjustmentRecord:
    """Record of a parameter adjustment."""
    record_id: str
    param_id: str
    action: TuningAction
    old_value: float
    new_value: float
    metric_before: Dict[str, float]
    metric_after: Dict[str, float]
    status: AdjustStatus
    timestamp: float
    verified: bool = False


@dataclass
class TunerStats:
    """Aggregate statistics for the live tuner."""
    total_parameters: int = 0
    total_adjustments: int = 0
    total_rollbacks: int = 0
    total_verified: int = 0
    total_cycles: int = 0
    avg_confidence: float = 0.0
    last_cycle_at: float = 0.0
    cycle_interval_s: float = 3.0
    improvements: int = 0
    regressions: int = 0
    adjustments_by_domain: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# Engine Live Tuner
# =============================================================================

class EngineLiveTuner:
    """
    Singleton continuous optimization system that autonomously tunes engine
    parameters based on real-time metrics and player experience data.

    The tuner:
      1. Maintains a registry of tunable parameters across all domains
      2. Collects metric samples from engine subsystems
      3. Analyzes metric trends to identify optimization opportunities
      4. Decides which parameters to adjust and by how much
      5. Applies changes gradually with automatic rollback safety
      6. Verifies improvements and learns from outcomes
    """

    _instance: Optional["EngineLiveTuner"] = None
    _instance_lock = threading.Lock()

    # Metric targets (ideal values)
    METRIC_TARGETS: Dict[MetricType, Tuple[float, float]] = {
        # (min_acceptable, ideal)
        MetricType.FPS: (30.0, 60.0),
        MetricType.FRAME_TIME: (16.6, 8.3),  # ms (lower is better)
        MetricType.MEMORY_USAGE: (0.8, 0.5),  # ratio (lower is better)
        MetricType.CPU_USAGE: (0.8, 0.6),
        MetricType.GPU_USAGE: (0.9, 0.7),
        MetricType.PLAYER_ENGAGEMENT: (0.4, 0.8),  # Higher is better
        MetricType.PLAYER_FRUSTRATION: (0.4, 0.1),  # Lower is better
        MetricType.DEATH_RATE: (0.3, 0.1),  # Lower is better
        MetricType.COMPLETION_RATE: (0.5, 0.8),  # Higher is better
        MetricType.LATENCY: (100.0, 30.0),  # ms (lower is better)
        MetricType.DRAW_CALLS: (2000.0, 500.0),  # Lower is better
        MetricType.PHYSICS_STEPS: (10.0, 4.0),  # Lower is better
    }

    # Whether higher or lower is better for each metric
    METRIC_DIRECTION: Dict[MetricType, str] = {
        MetricType.FPS: "higher",           # Higher FPS is better
        MetricType.FRAME_TIME: "lower",
        MetricType.MEMORY_USAGE: "lower",
        MetricType.CPU_USAGE: "lower",
        MetricType.GPU_USAGE: "lower",
        MetricType.PLAYER_ENGAGEMENT: "higher",
        MetricType.PLAYER_FRUSTRATION: "lower",
        MetricType.DEATH_RATE: "lower",
        MetricType.COMPLETION_RATE: "higher",
        MetricType.LATENCY: "lower",
        MetricType.DRAW_CALLS: "lower",
        MetricType.PHYSICS_STEPS: "lower",
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._parameters: Dict[str, TunableParameter] = {}
        self._metrics: Dict[MetricType, Deque[MetricSample]] = {
            mt: deque(maxlen=100) for mt in MetricType
        }
        self._adjustments: Deque[AdjustmentRecord] = deque(maxlen=200)
        self._stats = TunerStats()
        self._cycle_count: int = 0
        self._active: bool = False
        self._cycle_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._register_default_parameters()

    @classmethod
    def get_instance(cls) -> "EngineLiveTuner":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Parameter Registration
    # -------------------------------------------------------------------------

    def _register_default_parameters(self) -> None:
        """Register default tunable parameters."""
        defaults = [
            # PHYSICS
            ("physics_gravity", "Gravity", TuningDomain.PHYSICS,
             "Gravitational acceleration", -9.8, -20.0, -1.0, "m/s^2", 0.8),
            ("physics_friction", "Friction", TuningDomain.PHYSICS,
             "Surface friction coefficient", 0.5, 0.0, 2.0, "", 0.7),
            ("physics_restitution", "Restitution", TuningDomain.PHYSICS,
             "Bounce coefficient", 0.3, 0.0, 1.0, "", 0.6),
            ("physics_substeps", "Physics Substeps", TuningDomain.PHYSICS,
             "Number of physics substeps per frame", 4, 1, 16, "steps", 0.9),
            # RENDER
            ("render_draw_distance", "Draw Distance", TuningDomain.RENDER,
             "Maximum render distance", 1000.0, 100.0, 5000.0, "units", 0.8),
            ("render_shadow_quality", "Shadow Quality", TuningDomain.RENDER,
             "Shadow map resolution scale", 0.8, 0.0, 1.0, "", 0.7),
            ("render_texture_lod", "Texture LOD Bias", TuningDomain.RENDER,
             "Texture level of detail bias", 0.0, -2.0, 2.0, "", 0.6),
            ("render_post_processing", "Post Processing", TuningDomain.RENDER,
             "Post-processing intensity", 0.7, 0.0, 1.0, "", 0.5),
            # AUDIO
            ("audio_master_volume", "Master Volume", TuningDomain.AUDIO,
             "Master audio volume", 0.8, 0.0, 1.0, "", 0.9),
            ("audio_doppler_factor", "Doppler Factor", TuningDomain.AUDIO,
             "Doppler effect intensity", 1.0, 0.0, 3.0, "", 0.6),
            ("audio_3d_distance", "3D Audio Distance", TuningDomain.AUDIO,
             "3D audio falloff distance", 50.0, 10.0, 200.0, "units", 0.7),
            # GAMEPLAY
            ("gameplay_difficulty", "Difficulty", TuningDomain.GAMEPLAY,
             "Overall difficulty multiplier", 1.0, 0.1, 3.0, "x", 0.9),
            ("gameplay_spawn_rate", "Spawn Rate", TuningDomain.GAMEPLAY,
             "Enemy spawn rate multiplier", 1.0, 0.1, 5.0, "x", 0.8),
            ("gameplay_health_regen", "Health Regen", TuningDomain.GAMEPLAY,
             "Health regeneration rate", 1.0, 0.0, 10.0, "hp/s", 0.7),
            ("gameplay_xp_multiplier", "XP Multiplier", TuningDomain.GAMEPLAY,
             "Experience gain multiplier", 1.0, 0.1, 5.0, "x", 0.6),
            # AI
            ("ai_pathfinding_accuracy", "Pathfinding Accuracy", TuningDomain.AI,
             "Pathfinding grid resolution", 0.8, 0.1, 1.0, "", 0.8),
            ("ai_tick_rate", "AI Tick Rate", TuningDomain.AI,
             "Behavior tree update frequency", 10.0, 1.0, 60.0, "Hz", 0.7),
            ("ai_perception_range", "Perception Range", TuningDomain.AI,
             "NPC perception distance", 30.0, 5.0, 100.0, "units", 0.6),
            # MEMORY
            ("memory_cache_size", "Cache Size", TuningDomain.MEMORY,
             "Asset cache size in MB", 512.0, 64.0, 4096.0, "MB", 0.8),
            ("memory_pool_size", "Pool Size", TuningDomain.MEMORY,
             "Object pool allocation size", 100.0, 10.0, 1000.0, "objects", 0.7),
            # NETWORK
            ("network_tick_rate", "Network Tick Rate", TuningDomain.NETWORK,
             "Network update frequency", 30.0, 5.0, 120.0, "Hz", 0.9),
            ("network_interpolation", "Interpolation Delay", TuningDomain.NETWORK,
             "Client interpolation buffer", 100.0, 0.0, 500.0, "ms", 0.6),
        ]

        for pid, name, domain, desc, default, mn, mx, unit, impact in defaults:
            self._parameters[pid] = TunableParameter(
                param_id=pid,
                name=name,
                domain=domain,
                description=desc,
                current_value=default,
                default_value=default,
                min_value=mn,
                max_value=mx,
                target_value=default,
                unit=unit,
                impact_score=impact,
            )

        self._stats.total_parameters = len(self._parameters)

    def register_parameter(self, param_id: str, name: str, domain: TuningDomain,
                           description: str, default: float, min_val: float,
                           max_val: float, unit: str = "",
                           impact: float = 0.5) -> bool:
        """Register a new tunable parameter."""
        with self._lock:
            self._parameters[param_id] = TunableParameter(
                param_id=param_id,
                name=name,
                domain=domain,
                description=description,
                current_value=default,
                default_value=default,
                min_value=min_val,
                max_value=max_val,
                target_value=default,
                unit=unit,
                impact_score=impact,
            )
            self._stats.total_parameters = len(self._parameters)
            return True

    # -------------------------------------------------------------------------
    # Metric Collection
    # -------------------------------------------------------------------------

    def report_metric(self, metric_type: MetricType, value: float,
                      context: str = "") -> None:
        """Report a metric sample to the tuner."""
        sample = MetricSample(
            metric_type=metric_type,
            value=value,
            timestamp=time.time(),
            context=context,
        )
        with self._lock:
            self._metrics[metric_type].append(sample)

    def report_metric_by_name(self, metric_name: str, value: float,
                              context: str = "") -> bool:
        """Report a metric by its enum name string.

        Case-insensitive: accepts both the enum name (e.g. "FPS") and
        the enum value (e.g. "fps").
        """
        mt = self._resolve_metric_type(metric_name)
        if mt is None:
            return False
        self.report_metric(mt, value, context)
        return True

    @staticmethod
    def _resolve_domain(name: str) -> Optional[TuningDomain]:
        """Resolve a domain string case-insensitively (name or value)."""
        if not name:
            return None
        key = name.strip()
        # Match by value first (lowercase canonical form)
        for d in TuningDomain:
            if d.value == key.lower() or d.name == key.upper():
                return d
        return None

    @staticmethod
    def _resolve_metric_type(name: str) -> Optional[MetricType]:
        """Resolve a metric type string case-insensitively (name or value)."""
        if not name:
            return None
        key = name.strip()
        for mt in MetricType:
            if mt.value == key.lower() or mt.name == key.upper():
                return mt
        return None

    def get_metric_average(self, metric_type: MetricType,
                           window: int = 10) -> Optional[float]:
        """Get the average of recent metric samples."""
        with self._lock:
            samples = list(self._metrics[metric_type])[-window:]
            if not samples:
                return None
            return sum(s.value for s in samples) / len(samples)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metric averages."""
        with self._lock:
            result = {}
            for mt in MetricType:
                samples = list(self._metrics[mt])
                if samples:
                    avg = sum(s.value for s in samples) / len(samples)
                    latest = samples[-1].value
                    result[mt.value] = {
                        "average": round(avg, 2),
                        "latest": round(latest, 2),
                        "sample_count": len(samples),
                    }
            return result

    # -------------------------------------------------------------------------
    # Tuning Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """
        Run a single tuning cycle:
          MONITOR -> ANALYZE -> DECIDE -> APPLY -> VERIFY
        """
        cycle_start = time.time()
        result = {
            "phase": "",
            "monitored": 0,
            "analyzed": 0,
            "decided": 0,
            "applied": 0,
            "verified": 0,
            "rolled_back": 0,
        }

        with self._lock:
            # 1. MONITOR - Collect current metric averages
            result["phase"] = "monitor"
            metric_avgs: Dict[MetricType, float] = {}
            for mt in MetricType:
                avg = self.get_metric_average(mt, 10)
                if avg is not None:
                    metric_avgs[mt] = avg
                    result["monitored"] += 1

            # 2. ANALYZE - Identify which parameters need adjustment
            result["phase"] = "analyze"
            adjustments_needed: List[Tuple[str, TuningAction, float]] = []
            for param_id, param in self._parameters.items():
                action, new_target = self._analyze_parameter(param, metric_avgs)
                if action != TuningAction.HOLD:
                    adjustments_needed.append((param_id, action, new_target))
                    result["analyzed"] += 1

            # 3. DECIDE - Sort by impact and select top adjustments
            result["phase"] = "decide"
            adjustments_needed.sort(
                key=lambda x: self._parameters[x[0]].impact_score,
                reverse=True,
            )
            # Limit adjustments per cycle to avoid instability
            max_per_cycle = 5
            adjustments_needed = adjustments_needed[:max_per_cycle]
            result["decided"] = len(adjustments_needed)

            # 4. APPLY - Apply the adjustments
            result["phase"] = "apply"
            for param_id, action, new_target in adjustments_needed:
                applied = self._apply_adjustment(param_id, action, new_target, metric_avgs)
                if applied:
                    result["applied"] += 1

            # 5. VERIFY - Check if previous adjustments improved metrics
            result["phase"] = "verify"
            verified, rolled_back = self._verify_adjustments(metric_avgs)
            result["verified"] = verified
            result["rolled_back"] = rolled_back

            # Update stats
            self._cycle_count += 1
            self._stats.total_cycles = self._cycle_count
            self._stats.last_cycle_at = time.time()
            self._stats.total_adjustments = len(self._adjustments)
            self._stats.total_rollbacks = sum(
                1 for a in self._adjustments if a.status == AdjustStatus.ROLLED_BACK
            )
            self._stats.total_verified = sum(
                1 for a in self._adjustments if a.status == AdjustStatus.VERIFIED
            )
            avg_conf = sum(p.confidence for p in self._parameters.values()) / max(1, len(self._parameters))
            self._stats.avg_confidence = round(avg_conf, 3)

        result["cycle_ms"] = round((time.time() - cycle_start) * 1000, 2)
        return result

    def _analyze_parameter(self, param: TunableParameter,
                           metrics: Dict[MetricType, float]) -> Tuple[TuningAction, float]:
        """Analyze a parameter and decide what action to take."""
        # Map parameter domain to relevant metrics
        domain_metrics = {
            TuningDomain.PHYSICS: [MetricType.FRAME_TIME, MetricType.PHYSICS_STEPS],
            TuningDomain.RENDER: [MetricType.FPS, MetricType.FRAME_TIME, MetricType.DRAW_CALLS, MetricType.GPU_USAGE],
            TuningDomain.AUDIO: [MetricType.CPU_USAGE],
            TuningDomain.GAMEPLAY: [MetricType.PLAYER_ENGAGEMENT, MetricType.PLAYER_FRUSTRATION,
                                    MetricType.DEATH_RATE, MetricType.COMPLETION_RATE],
            TuningDomain.AI: [MetricType.CPU_USAGE, MetricType.FRAME_TIME],
            TuningDomain.MEMORY: [MetricType.MEMORY_USAGE, MetricType.CPU_USAGE],
            TuningDomain.NETWORK: [MetricType.LATENCY],
        }

        relevant_metrics = domain_metrics.get(param.domain, [])
        if not relevant_metrics:
            return TuningAction.HOLD, param.current_value

        # Check if any relevant metric is outside acceptable range
        needs_adjustment = False
        direction = 0  # -1 = decrease param, 1 = increase param

        for mt in relevant_metrics:
            if mt not in metrics:
                continue
            value = metrics[mt]
            min_accept, ideal = self.METRIC_TARGETS.get(mt, (0, 0))
            direction_str = self.METRIC_DIRECTION.get(mt, "higher")

            # Check if metric is in bad range
            if direction_str == "higher":
                if value < min_accept:
                    needs_adjustment = True
                    # Need to improve this metric
                    if param.domain == TuningDomain.RENDER:
                        direction -= 1  # Reduce render load
                    elif param.domain == TuningDomain.GAMEPLAY:
                        direction += 1  # Increase engagement
            else:  # lower is better
                if value > min_accept:
                    needs_adjustment = True
                    if param.domain == TuningDomain.RENDER:
                        direction -= 1  # Reduce quality
                    elif param.domain == TuningDomain.PHYSICS:
                        direction -= 1  # Reduce substeps
                    elif param.domain == TuningDomain.AI:
                        direction -= 1  # Reduce AI load

        if not needs_adjustment:
            return TuningAction.HOLD, param.current_value

        # Calculate new target
        if direction < 0:
            new_target = param.current_value * (1 - param.adjustment_rate)
            new_target = max(param.min_value, new_target)
            return TuningAction.DECREASE, new_target
        elif direction > 0:
            new_target = param.current_value * (1 + param.adjustment_rate)
            new_target = min(param.max_value, new_target)
            return TuningAction.INCREASE, new_target
        else:
            return TuningAction.HOLD, param.current_value

    def _apply_adjustment(self, param_id: str, action: TuningAction,
                          new_target: float,
                          metrics: Dict[MetricType, float]) -> bool:
        """Apply an adjustment to a parameter."""
        param = self._parameters.get(param_id)
        if not param:
            return False

        old_value = param.current_value
        if action == TuningAction.DECREASE:
            new_value = max(param.min_value,
                            old_value - (old_value - new_target) * param.adjustment_rate)
        elif action == TuningAction.INCREASE:
            new_value = min(param.max_value,
                            old_value + (new_target - old_value) * param.adjustment_rate)
        else:
            return False

        # Don't adjust if change is too small
        if abs(new_value - old_value) < 0.001:
            return False

        param.current_value = new_value
        param.target_value = new_target
        param.last_adjusted = time.time()
        param.adjustment_count += 1
        param.last_metric_before = metrics.get(MetricType.FPS)

        # Record adjustment
        record = AdjustmentRecord(
            record_id=uuid.uuid4().hex[:10],
            param_id=param_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            metric_before=dict(metrics),
            metric_after={},
            status=AdjustStatus.APPLIED,
            timestamp=time.time(),
        )
        self._adjustments.append(record)

        # Update domain stats
        domain_key = param.domain.value
        self._stats.adjustments_by_domain[domain_key] = \
            self._stats.adjustments_by_domain.get(domain_key, 0) + 1

        return True

    def _verify_adjustments(self, current_metrics: Dict[MetricType, float]) -> Tuple[int, int]:
        """Verify recent adjustments and rollback if needed."""
        verified = 0
        rolled_back = 0

        # Check the most recent unverified adjustments
        for record in reversed(self._adjustments):
            if record.status != AdjustStatus.APPLIED:
                continue
            if time.time() - record.timestamp < 2.0:
                continue  # Need more time to see effect

            # Compare metrics before and after
            before_fps = record.metric_before.get(MetricType.FPS, 60.0)
            after_fps = current_metrics.get(MetricType.FPS, before_fps)

            record.metric_after = dict(current_metrics)

            if after_fps >= before_fps * 0.95:  # Allow 5% tolerance
                record.status = AdjustStatus.VERIFIED
                record.verified = True
                verified += 1
                self._stats.improvements += 1
                # Increase confidence in this parameter
                param = self._parameters.get(record.param_id)
                if param:
                    param.confidence = min(1.0, param.confidence + 0.05)
            else:
                # Rollback
                record.status = AdjustStatus.ROLLED_BACK
                rolled_back += 1
                self._stats.regressions += 1
                param = self._parameters.get(record.param_id)
                if param:
                    param.current_value = record.old_value
                    param.rollback_count += 1
                    param.confidence = max(0.0, param.confidence - 0.1)

            if verified + rolled_back >= 3:  # Only check a few per cycle
                break

        return verified, rolled_back

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """Start the automatic tuning cycle."""
        if self._active:
            return
        self._active = True
        self._stop_event.clear()
        self._cycle_thread = threading.Thread(
            target=self._cycle_loop, daemon=True, name="engine-live-tuner"
        )
        self._cycle_thread.start()
        logger.info("Engine live tuner started")

    def stop(self) -> None:
        """Stop the automatic tuning cycle."""
        self._active = False
        self._stop_event.set()
        if self._cycle_thread:
            self._cycle_thread.join(timeout=2.0)

    def _cycle_loop(self) -> None:
        """Background loop."""
        while not self._stop_event.is_set():
            try:
                self.run_cycle()
            except Exception as e:
                logger.error("Live tuner cycle error: %s", e)
            self._stop_event.wait(self._stats.cycle_interval_s)

    # -------------------------------------------------------------------------
    # Query API
    # -------------------------------------------------------------------------

    def get_parameters(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all parameters, optionally filtered by domain.

        Domain matching is case-insensitive and accepts both the enum
        name (e.g. "PHYSICS") and value (e.g. "physics").
        """
        with self._lock:
            params = list(self._parameters.values())
            if domain:
                d = self._resolve_domain(domain)
                if d is None:
                    return []
                params = [p for p in params if p.domain == d]
            return [
                {
                    "param_id": p.param_id,
                    "name": p.name,
                    "domain": p.domain.value,
                    "description": p.description,
                    "current_value": round(p.current_value, 4),
                    "default_value": round(p.default_value, 4),
                    "min_value": p.min_value,
                    "max_value": p.max_value,
                    "target_value": round(p.target_value, 4),
                    "confidence": round(p.confidence, 3),
                    "adjustment_rate": p.adjustment_rate,
                    "unit": p.unit,
                    "impact_score": round(p.impact_score, 3),
                    "adjustment_count": p.adjustment_count,
                    "rollback_count": p.rollback_count,
                    "last_adjusted": p.last_adjusted,
                }
                for p in params
            ]

    def get_parameter(self, param_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific parameter."""
        with self._lock:
            p = self._parameters.get(param_id)
            if not p:
                return None
            return {
                "param_id": p.param_id,
                "name": p.name,
                "domain": p.domain.value,
                "description": p.description,
                "current_value": round(p.current_value, 4),
                "default_value": round(p.default_value, 4),
                "min_value": p.min_value,
                "max_value": p.max_value,
                "target_value": round(p.target_value, 4),
                "confidence": round(p.confidence, 3),
                "adjustment_rate": p.adjustment_rate,
                "unit": p.unit,
                "impact_score": round(p.impact_score, 3),
                "adjustment_count": p.adjustment_count,
                "rollback_count": p.rollback_count,
                "last_adjusted": p.last_adjusted,
            }

    def set_parameter_value(self, param_id: str, value: float) -> bool:
        """Manually set a parameter value."""
        with self._lock:
            param = self._parameters.get(param_id)
            if not param:
                return False
            param.current_value = max(param.min_value, min(param.max_value, value))
            param.target_value = param.current_value
            param.last_adjusted = time.time()
            param.adjustment_count += 1
            return True

    def reset_parameter(self, param_id: str) -> bool:
        """Reset a parameter to its default value."""
        with self._lock:
            param = self._parameters.get(param_id)
            if not param:
                return False
            param.current_value = param.default_value
            param.target_value = param.default_value
            param.adjustment_count += 1
            return True

    def reset_all_parameters(self) -> int:
        """Reset all parameters to defaults."""
        with self._lock:
            count = 0
            for param in self._parameters.values():
                param.current_value = param.default_value
                param.target_value = param.default_value
                param.confidence = 0.5
                count += 1
            return count

    def get_adjustments(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent adjustment records."""
        with self._lock:
            return [
                {
                    "record_id": r.record_id,
                    "param_id": r.param_id,
                    "action": r.action.value,
                    "old_value": round(r.old_value, 4),
                    "new_value": round(r.new_value, 4),
                    "status": r.status.value,
                    "verified": r.verified,
                    "timestamp": r.timestamp,
                }
                for r in list(self._adjustments)[-limit:]
            ]

    def get_status(self) -> Dict[str, Any]:
        """Get the tuner status."""
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "last_cycle_at": self._stats.last_cycle_at,
                "cycle_interval_s": self._stats.cycle_interval_s,
                "stats": {
                    "total_parameters": self._stats.total_parameters,
                    "total_adjustments": self._stats.total_adjustments,
                    "total_rollbacks": self._stats.total_rollbacks,
                    "total_verified": self._stats.total_verified,
                    "total_cycles": self._stats.total_cycles,
                    "avg_confidence": self._stats.avg_confidence,
                    "improvements": self._stats.improvements,
                    "regressions": self._stats.regressions,
                },
                "adjustments_by_domain": dict(self._stats.adjustments_by_domain),
                "current_metrics": self.get_metrics(),
            }

    # -------------------------------------------------------------------------
    # Simulation
    # -------------------------------------------------------------------------

    def simulate_metrics(self, count: int = 10) -> Dict[str, Any]:
        """Simulate metric samples for testing."""
        import random as rnd
        for _ in range(count):
            self.report_metric(MetricType.FPS, rnd.uniform(25, 65))
            self.report_metric(MetricType.FRAME_TIME, rnd.uniform(8, 40))
            self.report_metric(MetricType.MEMORY_USAGE, rnd.uniform(0.3, 0.9))
            self.report_metric(MetricType.CPU_USAGE, rnd.uniform(0.2, 0.95))
            self.report_metric(MetricType.GPU_USAGE, rnd.uniform(0.3, 0.95))
            self.report_metric(MetricType.PLAYER_ENGAGEMENT, rnd.uniform(0.2, 0.9))
            self.report_metric(MetricType.PLAYER_FRUSTRATION, rnd.uniform(0.0, 0.5))
            self.report_metric(MetricType.DEATH_RATE, rnd.uniform(0.0, 0.4))
            self.report_metric(MetricType.COMPLETION_RATE, rnd.uniform(0.3, 0.9))
            self.report_metric(MetricType.DRAW_CALLS, rnd.uniform(200, 2500))
            self.report_metric(MetricType.PHYSICS_STEPS, rnd.uniform(1, 12))

        # Run a cycle
        cycle = self.run_cycle()
        return {
            "metrics_simulated": count,
            "cycle_result": cycle,
        }

    def reset(self) -> None:
        """Reset the tuner state."""
        with self._lock:
            for param in self._parameters.values():
                param.current_value = param.default_value
                param.target_value = param.default_value
                param.confidence = 0.5
                param.adjustment_count = 0
                param.rollback_count = 0
            self._adjustments.clear()
            for mt in MetricType:
                self._metrics[mt].clear()
            self._stats = TunerStats()
            self._stats.total_parameters = len(self._parameters)
            self._cycle_count = 0


# =============================================================================
# Module-level accessor
# =============================================================================

def get_live_tuner() -> EngineLiveTuner:
    """Return the singleton live tuner instance."""
    return EngineLiveTuner.get_instance()
