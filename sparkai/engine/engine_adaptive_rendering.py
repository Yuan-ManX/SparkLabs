"""
SparkAI Adaptive Rendering Engine - Intelligent rendering optimization system.

Provides adaptive rendering capabilities that dynamically adjust quality
settings based on performance metrics, device capabilities, and scene
complexity to maintain optimal frame rates.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class QualityTier(Enum):
    """Rendering quality tiers for adaptive adjustment."""
    ULTRA = "ultra"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"
    PERFORMANCE = "performance"


class RenderFeature(Enum):
    """Individual render features that can be toggled."""
    SHADOWS = "shadows"
    AMBIENT_OCCLUSION = "ambient_occlusion"
    ANTI_ALIASING = "anti_aliasing"
    POST_PROCESSING = "post_processing"
    PARTICLE_EFFECTS = "particle_effects"
    DYNAMIC_LIGHTING = "dynamic_lighting"
    REFLECTIONS = "reflections"
    VOLUMETRIC_EFFECTS = "volumetric_effects"
    BLOOM = "bloom"
    MOTION_BLUR = "motion_blur"
    DEPTH_OF_FIELD = "depth_of_field"
    LOD_SYSTEM = "lod_system"
    TEXTURE_STREAMING = "texture_streaming"
    GPU_PARTICLES = "gpu_particles"
    SCREEN_SPACE_EFFECTS = "screen_space_effects"


class AdaptationStrategy(Enum):
    """Strategies for adapting rendering quality."""
    AGGRESSIVE = "aggressive"  # Quick quality reduction
    CONSERVATIVE = "conservative"  # Gradual quality adjustment
    BALANCED = "balanced"  # Balance between quality and performance
    ADAPTIVE_LEARNING = "adaptive_learning"  # Learn from historical patterns


@dataclass
class PerformanceMetrics:
    """Real-time performance metrics for adaptive decisions."""
    current_fps: float = 60.0
    target_fps: float = 60.0
    frame_time_ms: float = 16.67
    gpu_utilization: float = 0.5
    cpu_utilization: float = 0.3
    memory_usage_mb: float = 256.0
    draw_calls: int = 100
    triangle_count: int = 50000
    texture_memory_mb: float = 128.0
    shader_complexity: float = 0.5
    screen_fill_percentage: float = 0.7
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_fps": self.current_fps,
            "target_fps": self.target_fps,
            "frame_time_ms": self.frame_time_ms,
            "gpu_utilization": self.gpu_utilization,
            "cpu_utilization": self.cpu_utilization,
            "memory_usage_mb": self.memory_usage_mb,
            "draw_calls": self.draw_calls,
            "triangle_count": self.triangle_count,
            "texture_memory_mb": self.texture_memory_mb,
            "shader_complexity": self.shader_complexity,
            "screen_fill_percentage": self.screen_fill_percentage,
            "timestamp": self.timestamp,
        }


@dataclass
class QualityPreset:
    """Defines a quality preset with feature toggles."""
    tier: QualityTier
    features: Dict[RenderFeature, bool] = field(default_factory=dict)
    resolution_scale: float = 1.0
    shadow_resolution: int = 2048
    max_draw_distance: float = 1000.0
    lod_bias: float = 0.0
    max_particles: int = 1000
    texture_quality: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value,
            "features": {k.value: v for k, v in self.features.items()},
            "resolution_scale": self.resolution_scale,
            "shadow_resolution": self.shadow_resolution,
            "max_draw_distance": self.max_draw_distance,
            "lod_bias": self.lod_bias,
            "max_particles": self.max_particles,
            "texture_quality": self.texture_quality,
        }


@dataclass
class AdaptationEvent:
    """Records a quality adaptation event."""
    event_id: str
    from_tier: QualityTier
    to_tier: QualityTier
    reason: str
    metrics_before: PerformanceMetrics
    metrics_after: Optional[PerformanceMetrics] = None
    timestamp: float = field(default_factory=time.time)
    was_effective: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "from_tier": self.from_tier.value,
            "to_tier": self.to_tier.value,
            "reason": self.reason,
            "metrics_before": self.metrics_before.to_dict(),
            "metrics_after": self.metrics_after.to_dict() if self.metrics_after else None,
            "timestamp": self.timestamp,
            "was_effective": self.was_effective,
        }


class MetricsCollector:
    """Collects and analyzes performance metrics over time."""

    def __init__(self, history_size: int = 120) -> None:
        self._history: deque = deque(maxlen=history_size)
        self._lock = threading.RLock()

    def record(self, metrics: PerformanceMetrics) -> None:
        with self._lock:
            self._history.append(metrics)

    def get_average_fps(self, window: int = 30) -> float:
        with self._lock:
            recent = list(self._history)[-window:]
            if not recent:
                return 60.0
            return sum(m.current_fps for m in recent) / len(recent)

    def get_fps_trend(self) -> str:
        with self._lock:
            if len(self._history) < 10:
                return "stable"
            recent = list(self._history)[-10:]
            first_half = recent[:5]
            second_half = recent[5:]
            avg_first = sum(m.current_fps for m in first_half) / 5
            avg_second = sum(m.current_fps for m in second_half) / 5
            diff = avg_second - avg_first
            if diff > 2:
                return "improving"
            elif diff < -2:
                return "degrading"
            return "stable"

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "samples_collected": len(self._history),
                "average_fps": self.get_average_fps(),
                "fps_trend": self.get_fps_trend(),
            }


class QualityManager:
    """Manages quality presets and feature configurations."""

    def __init__(self) -> None:
        self._presets: Dict[QualityTier, QualityPreset] = {}
        self._current_tier: QualityTier = QualityTier.HIGH
        self._feature_overrides: Dict[RenderFeature, bool] = {}
        self._lock = threading.RLock()
        self._initialize_presets()

    def _initialize_presets(self) -> None:
        """Initialize default quality presets."""
        all_features_on = {f: True for f in RenderFeature}
        all_features_off = {f: False for f in RenderFeature}

        self._presets[QualityTier.ULTRA] = QualityPreset(
            tier=QualityTier.ULTRA,
            features=dict(all_features_on),
            resolution_scale=1.0,
            shadow_resolution=4096,
            max_draw_distance=2000.0,
            lod_bias=0.0,
            max_particles=5000,
            texture_quality=1.0,
        )

        self._presets[QualityTier.HIGH] = QualityPreset(
            tier=QualityTier.HIGH,
            features=dict(all_features_on),
            resolution_scale=1.0,
            shadow_resolution=2048,
            max_draw_distance=1500.0,
            lod_bias=0.0,
            max_particles=3000,
            texture_quality=1.0,
        )

        self._presets[QualityTier.MEDIUM] = QualityPreset(
            tier=QualityTier.MEDIUM,
            features={f: f not in [
                RenderFeature.VOLUMETRIC_EFFECTS,
                RenderFeature.MOTION_BLUR,
                RenderFeature.DEPTH_OF_FIELD,
            ] for f in RenderFeature},
            resolution_scale=0.85,
            shadow_resolution=1024,
            max_draw_distance=1000.0,
            lod_bias=0.5,
            max_particles=1500,
            texture_quality=0.75,
        )

        self._presets[QualityTier.LOW] = QualityPreset(
            tier=QualityTier.LOW,
            features={f: f in [
                RenderFeature.SHADOWS,
                RenderFeature.ANTI_ALIASING,
                RenderFeature.DYNAMIC_LIGHTING,
                RenderFeature.LOD_SYSTEM,
            ] for f in RenderFeature},
            resolution_scale=0.7,
            shadow_resolution=512,
            max_draw_distance=600.0,
            lod_bias=1.0,
            max_particles=500,
            texture_quality=0.5,
        )

        self._presets[QualityTier.MINIMAL] = QualityPreset(
            tier=QualityTier.MINIMAL,
            features={f: f in [
                RenderFeature.ANTI_ALIASING,
                RenderFeature.LOD_SYSTEM,
            ] for f in RenderFeature},
            resolution_scale=0.5,
            shadow_resolution=256,
            max_draw_distance=300.0,
            lod_bias=2.0,
            max_particles=100,
            texture_quality=0.25,
        )

        self._presets[QualityTier.PERFORMANCE] = QualityPreset(
            tier=QualityTier.PERFORMANCE,
            features=dict(all_features_off),
            resolution_scale=0.4,
            shadow_resolution=128,
            max_draw_distance=150.0,
            lod_bias=3.0,
            max_particles=0,
            texture_quality=0.1,
        )

    def get_current_preset(self) -> QualityPreset:
        with self._lock:
            preset = self._presets[self._current_tier]
            # Apply any feature overrides
            for feature, enabled in self._feature_overrides.items():
                preset.features[feature] = enabled
            return preset

    def set_tier(self, tier: QualityTier) -> None:
        with self._lock:
            self._current_tier = tier

    def get_tier(self) -> QualityTier:
        with self._lock:
            return self._current_tier

    def override_feature(self, feature: RenderFeature, enabled: bool) -> None:
        with self._lock:
            self._feature_overrides[feature] = enabled

    def clear_overrides(self) -> None:
        with self._lock:
            self._feature_overrides.clear()

    def get_all_presets(self) -> Dict[str, Any]:
        with self._lock:
            return {k.value: v.to_dict() for k, v in self._presets.items()}


class AdaptiveRenderingEngine:
    """Intelligent adaptive rendering engine for dynamic quality management.

    Continuously monitors performance metrics and automatically adjusts
    rendering quality to maintain target frame rates while maximizing
    visual fidelity.
    """

    _instance: Optional["AdaptiveRenderingEngine"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if self._instance is not None:
            raise RuntimeError("Use AdaptiveRenderingEngine.get_instance()")
        self._metrics_collector = MetricsCollector()
        self._quality_manager = QualityManager()
        self._adaptation_strategy: AdaptationStrategy = AdaptationStrategy.BALANCED
        self._target_fps: float = 60.0
        self._adaptation_history: List[AdaptationEvent] = []
        self._adaptation_cooldown: float = 2.0  # seconds between adaptations
        self._last_adaptation_time: float = 0.0
        self._initialized: bool = False
        self._enabled: bool = True
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "AdaptiveRenderingEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(
        self,
        target_fps: float = 60.0,
        strategy: AdaptationStrategy = AdaptationStrategy.BALANCED,
    ) -> None:
        """Initialize the adaptive rendering engine."""
        with self._lock:
            self._target_fps = target_fps
            self._adaptation_strategy = strategy
            self._initialized = True

    def update_metrics(self, metrics: PerformanceMetrics) -> None:
        """Update performance metrics and trigger adaptation if needed."""
        with self._lock:
            self._metrics_collector.record(metrics)

            if not self._initialized or not self._enabled:
                return

            current_time = time.time()
            if current_time - self._last_adaptation_time < self._adaptation_cooldown:
                return

            self._evaluate_adaptation(metrics)

    def _evaluate_adaptation(self, metrics: PerformanceMetrics) -> None:
        """Evaluate whether quality adaptation is needed."""
        current_tier = self._quality_manager.get_tier()
        fps_deficit = self._target_fps - metrics.current_fps
        fps_ratio = metrics.current_fps / max(self._target_fps, 1.0)

        tier_order = list(QualityTier)
        current_index = tier_order.index(current_tier)

        should_degrade = fps_ratio < 0.85  # Below 85% of target
        should_upgrade = fps_ratio > 0.95 and current_index > 0  # Above 95% and not at max

        if should_degrade and current_index < len(tier_order) - 1:
            new_tier = tier_order[min(current_index + 1, len(tier_order) - 1)]
            reason = f"FPS deficit: {fps_deficit:.1f} (ratio: {fps_ratio:.2f})"
            self._apply_adaptation(current_tier, new_tier, reason, metrics)

        elif should_upgrade:
            new_tier = tier_order[max(current_index - 1, 0)]
            reason = f"Performance headroom available (ratio: {fps_ratio:.2f})"
            self._apply_adaptation(current_tier, new_tier, reason, metrics)

    def _apply_adaptation(
        self,
        from_tier: QualityTier,
        to_tier: QualityTier,
        reason: str,
        metrics: PerformanceMetrics,
    ) -> None:
        """Apply a quality tier adaptation."""
        event = AdaptationEvent(
            event_id=f"adapt_{uuid.uuid4().hex[:8]}",
            from_tier=from_tier,
            to_tier=to_tier,
            reason=reason,
            metrics_before=metrics,
        )

        self._quality_manager.set_tier(to_tier)
        self._last_adaptation_time = time.time()
        self._adaptation_history.append(event)

    def get_current_config(self) -> Dict[str, Any]:
        """Get current rendering configuration."""
        with self._lock:
            preset = self._quality_manager.get_current_preset()
            return {
                "current_tier": self._quality_manager.get_tier().value,
                "preset": preset.to_dict(),
                "target_fps": self._target_fps,
                "strategy": self._adaptation_strategy.value,
                "enabled": self._enabled,
                "initialized": self._initialized,
            }

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._enabled = enabled

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "metrics": self._metrics_collector.get_statistics(),
                "current_tier": self._quality_manager.get_tier().value,
                "adaptation_count": len(self._adaptation_history),
                "last_adaptation": (
                    self._adaptation_history[-1].to_dict()
                    if self._adaptation_history else None
                ),
                "target_fps": self._target_fps,
                "strategy": self._adaptation_strategy.value,
                "enabled": self._enabled,
                "initialized": self._initialized,
            }

    def get_adaptation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [e.to_dict() for e in self._adaptation_history[-limit:]]

    def get_all_presets(self) -> Dict[str, Any]:
        return self._quality_manager.get_all_presets()


def get_adaptive_rendering() -> AdaptiveRenderingEngine:
    """Get the global AdaptiveRenderingEngine instance."""
    return AdaptiveRenderingEngine.get_instance()