"""
SparkLabs Agent - Multi-Modal Perception Fusion System

A perception fusion system that combines multiple sensory modalities
into a unified percept. Models how agents perceive their environment
through visual, auditory, spatial, social, and temporal channels,
with attention mechanisms to prioritize the most salient inputs.

Architecture:
  PerceptionFusionSystem (Singleton)
    |-- PerceptionSource (visual, auditory, spatial, social, temporal)
    |-- PerceptionFrame (snapshot at a moment in time)
    |-- SensorFusionEngine (multi-modal combination)
    |-- AttentionSystem (percept prioritization)
    |-- SaliencyMap (spatial attention distribution)
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class PerceptionSource(Enum):
    """Types of perceptual input channels."""
    VISUAL = "visual"
    AUDITORY = "auditory"
    SPATIAL = "spatial"
    SOCIAL = "social"
    TEMPORAL = "temporal"
    TACTILE = "tactile"
    PROPRIOCEPTIVE = "proprioceptive"


class AttentionLevel(Enum):
    """Level of attentional focus on a percept."""
    NONE = "none"
    PERIPHERAL = "peripheral"
    FOCAL = "focal"
    SUSTAINED = "sustained"
    HYPERFOCUS = "hyperfocus"


class FusionStrategy(Enum):
    """Strategy for combining multiple percepts."""
    WEIGHTED_AVERAGE = "weighted_average"
    BAYESIAN = "bayesian"
    MAX_CONFIDENCE = "max_confidence"
    DEMPSTER_SHAFER = "dempster_shafer"
    ATTENTION_WEIGHTED = "attention_weighted"


@dataclass
class Percept:
    """A single perceptual datum from a source channel."""
    percept_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source: PerceptionSource = PerceptionSource.VISUAL
    content: str = ""
    intensity: float = 0.5
    confidence: float = 0.5
    novelty: float = 0.5
    relevance: float = 0.5
    spatial_position: Optional[Tuple[float, float, float]] = None
    duration: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "percept_id": self.percept_id,
            "source": self.source.value,
            "content": self.content,
            "intensity": self.intensity,
            "confidence": self.confidence,
            "novelty": self.novelty,
            "relevance": self.relevance,
            "spatial_position": self.spatial_position,
            "duration": self.duration,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    def salience(self) -> float:
        """Compute the overall salience (attention-worthiness) of this percept."""
        return (
            self.intensity * 0.25
            + self.confidence * 0.15
            + self.novelty * 0.30
            + self.relevance * 0.30
        )


@dataclass
class PerceptionFrame:
    """A complete perceptual snapshot at a moment in time."""
    frame_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=_time_module.time)
    percepts: List[Percept] = field(default_factory=list)
    attention_map: Dict[str, AttentionLevel] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "percept_count": len(self.percepts),
            "percepts": [p.to_dict() for p in self.percepts],
            "attention_map": {k: v.value for k, v in self.attention_map.items()},
            "context": self.context,
        }

    def add_percept(self, percept: Percept) -> None:
        self.percepts.append(percept)

    def get_percepts_by_source(self, source: PerceptionSource) -> List[Percept]:
        return [p for p in self.percepts if p.source == source]

    def get_most_salient(self, limit: int = 5) -> List[Percept]:
        sorted_percepts = sorted(self.percepts, key=lambda p: p.salience(), reverse=True)
        return sorted_percepts[:limit]


class SensorFusionEngine:
    """
    Combines percepts from multiple sensory channels into a unified
    perception using configurable fusion strategies.
    """

    def __init__(self) -> None:
        self._strategy: FusionStrategy = FusionStrategy.WEIGHTED_AVERAGE
        self._source_weights: Dict[PerceptionSource, float] = {
            src: 1.0 for src in PerceptionSource
        }
        self._frame_history: List[PerceptionFrame] = []
        self._max_history: int = 100
        self._lock = threading.RLock()

    def set_strategy(self, strategy: FusionStrategy) -> None:
        with self._lock:
            self._strategy = strategy

    def set_source_weight(self, source: PerceptionSource, weight: float) -> None:
        with self._lock:
            self._source_weights[source] = max(0.0, weight)

    def fuse(self, frame: PerceptionFrame) -> PerceptionFrame:
        """
        Fuse percepts within a frame using the configured strategy.
        Returns the frame with fused percepts and attention annotations.
        """
        with self._lock:
            if self._strategy == FusionStrategy.WEIGHTED_AVERAGE:
                frame = self._fuse_weighted_average(frame)
            elif self._strategy == FusionStrategy.MAX_CONFIDENCE:
                frame = self._fuse_max_confidence(frame)
            elif self._strategy == FusionStrategy.ATTENTION_WEIGHTED:
                frame = self._fuse_attention_weighted(frame)
            else:
                frame = self._fuse_weighted_average(frame)

            self._frame_history.append(frame)
            if len(self._frame_history) > self._max_history:
                self._frame_history = self._frame_history[-self._max_history:]
            return frame

    def _fuse_weighted_average(self, frame: PerceptionFrame) -> PerceptionFrame:
        """Fuse percepts by weighted averaging within each source."""
        fused_percepts: List[Percept] = []
        for source in PerceptionSource:
            source_percepts = frame.get_percepts_by_source(source)
            if not source_percepts:
                continue
            weight = self._source_weights.get(source, 1.0)
            if len(source_percepts) == 1:
                p = source_percepts[0]
                p.relevance *= weight
                fused_percepts.append(p)
            else:
                avg_intensity = sum(p.intensity for p in source_percepts) / len(source_percepts)
                avg_confidence = sum(p.confidence for p in source_percepts) / len(source_percepts)
                avg_relevance = sum(p.relevance for p in source_percepts) / len(source_percepts) * weight
                fused = Percept(
                    source=source,
                    content=f"Fused {source.value}: {len(source_percepts)} percepts",
                    intensity=avg_intensity,
                    confidence=avg_confidence,
                    relevance=avg_relevance,
                    novelty=source_percepts[0].novelty,
                    tags=list(set(t for p in source_percepts for t in p.tags)),
                )
                fused_percepts.append(fused)
        frame.percepts = fused_percepts
        return frame

    def _fuse_max_confidence(self, frame: PerceptionFrame) -> PerceptionFrame:
        """Keep only the highest-confidence percept per source."""
        fused_percepts: List[Percept] = []
        for source in PerceptionSource:
            source_percepts = frame.get_percepts_by_source(source)
            if source_percepts:
                best = max(source_percepts, key=lambda p: p.confidence)
                fused_percepts.append(best)
        frame.percepts = fused_percepts
        return frame

    def _fuse_attention_weighted(self, frame: PerceptionFrame) -> PerceptionFrame:
        """Weight percepts by their attention level."""
        for p in frame.percepts:
            attn_level = frame.attention_map.get(p.percept_id, AttentionLevel.PERIPHERAL)
            attn_weights = {
                AttentionLevel.NONE: 0.0,
                AttentionLevel.PERIPHERAL: 0.3,
                AttentionLevel.FOCAL: 0.7,
                AttentionLevel.SUSTAINED: 0.9,
                AttentionLevel.HYPERFOCUS: 1.0,
            }
            p.relevance *= attn_weights.get(attn_level, 0.3)
        return frame

    def get_recent_frames(self, limit: int = 10) -> List[PerceptionFrame]:
        with self._lock:
            return self._frame_history[-limit:]

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "strategy": self._strategy.value,
                "source_weights": {s.value: w for s, w in self._source_weights.items()},
                "frame_count": len(self._frame_history),
            }


class SaliencyMap:
    """
    Spatial attention distribution map.
    Models how attention is distributed across spatial regions,
    driven by percept salience and novelty.
    """

    def __init__(self, width: int = 100, height: int = 100) -> None:
        self._width = width
        self._height = height
        self._grid: List[List[float]] = [[0.0] * width for _ in range(height)]
        self._lock = threading.RLock()

    def update(self, percepts: List[Percept]) -> None:
        """Update the saliency map with new percepts."""
        with self._lock:
            for p in percepts:
                if p.spatial_position:
                    x, y, z = p.spatial_position
                    gx = int(x * self._width) % self._width
                    gy = int(y * self._height) % self._height
                    salience = p.salience()
                    self._apply_gaussian_brush(gx, gy, salience, radius=3)

    def _apply_gaussian_brush(self, cx: int, cy: int, value: float, radius: int) -> None:
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self._width and 0 <= ny < self._height:
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist <= radius:
                        falloff = math.exp(-(dist ** 2) / (2.0 * (radius / 2.0) ** 2))
                        self._grid[ny][nx] = max(self._grid[ny][nx], value * falloff)

    def get_hotspot(self) -> Optional[Tuple[float, float]]:
        """Find the point of maximum salience."""
        with self._lock:
            max_val = 0.0
            max_pos = None
            for y in range(self._height):
                for x in range(self._width):
                    if self._grid[y][x] > max_val:
                        max_val = self._grid[y][x]
                        max_pos = (x / self._width, y / self._height)
            return max_pos

    def get_region_salience(self, x: float, y: float, radius: float = 0.1) -> float:
        """Get the average salience in a region."""
        with self._lock:
            cx = int(x * self._width)
            cy = int(y * self._height)
            r = int(radius * self._width)
            total = 0.0
            count = 0
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < self._width and 0 <= ny < self._height:
                        total += self._grid[ny][nx]
                        count += 1
            return total / count if count > 0 else 0.0

    def decay(self, rate: float = 0.05) -> None:
        """Apply temporal decay to the saliency map."""
        with self._lock:
            for y in range(self._height):
                for x in range(self._width):
                    self._grid[y][x] *= (1.0 - rate)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "width": self._width,
                "height": self._height,
                "max_salience": max(max(row) for row in self._grid),
                "hotspot": self.get_hotspot(),
            }


class AttentionSystem:
    """
    Prioritizes percepts based on salience, task relevance, and
    novelty. Models both bottom-up (stimulus-driven) and top-down
    (goal-driven) attention mechanisms.
    """

    def __init__(self) -> None:
        self._saliency_map = SaliencyMap()
        self._focus_target: Optional[str] = None
        self._focus_priority: float = 0.5
        self._attention_budget: float = 1.0
        self._lock = threading.RLock()

    def attend(self, frame: PerceptionFrame) -> PerceptionFrame:
        """
        Apply attention to a perception frame, assigning attention
        levels to each percept.
        """
        with self._lock:
            self._saliency_map.update(frame.percepts)
            self._saliency_map.decay(rate=0.02)

            sorted_percepts = sorted(frame.percepts, key=lambda p: p.salience(), reverse=True)
            running_budget = self._attention_budget

            for percept in sorted_percepts:
                if running_budget <= 0:
                    frame.attention_map[percept.percept_id] = AttentionLevel.NONE
                    continue

                salience = percept.salience()
                if salience >= 0.8:
                    level = AttentionLevel.HYPERFOCUS
                    cost = 0.4
                elif salience >= 0.6:
                    level = AttentionLevel.SUSTAINED
                    cost = 0.25
                elif salience >= 0.4:
                    level = AttentionLevel.FOCAL
                    cost = 0.15
                elif salience >= 0.2:
                    level = AttentionLevel.PERIPHERAL
                    cost = 0.05
                else:
                    level = AttentionLevel.NONE
                    cost = 0.0

                if running_budget >= cost:
                    frame.attention_map[percept.percept_id] = level
                    running_budget -= cost
                else:
                    frame.attention_map[percept.percept_id] = AttentionLevel.NONE

            return frame

    def set_focus(self, target_id: str, priority: float = 0.5) -> None:
        with self._lock:
            self._focus_target = target_id
            self._focus_priority = priority

    def clear_focus(self) -> None:
        with self._lock:
            self._focus_target = None

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "saliency_map": self._saliency_map.to_dict(),
                "focus_target": self._focus_target,
                "focus_priority": self._focus_priority,
                "attention_budget": self._attention_budget,
            }


class PerceptionFusionSystem:
    """
    Multi-modal perception fusion system for AI agents.

    Combines multiple sensory channels into a unified percept,
    with attention mechanisms and spatial saliency mapping.
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._fusion_engine = SensorFusionEngine()
        self._attention_system = AttentionSystem()
        self._last_frame: Optional[PerceptionFrame] = None

    @classmethod
    def get_instance(cls) -> "PerceptionFusionSystem":
        return cls()

    @property
    def fusion(self) -> SensorFusionEngine:
        return self._fusion_engine

    @property
    def attention(self) -> AttentionSystem:
        return self._attention_system

    def create_percept(
        self,
        source: str,
        content: str,
        intensity: float = 0.5,
        confidence: float = 0.5,
        novelty: float = 0.5,
        relevance: float = 0.5,
        spatial_position: Optional[Tuple[float, float, float]] = None,
        tags: Optional[List[str]] = None,
    ) -> Percept:
        """Create a new percept."""
        return Percept(
            source=PerceptionSource(source),
            content=content,
            intensity=intensity,
            confidence=confidence,
            novelty=novelty,
            relevance=relevance,
            spatial_position=spatial_position,
            tags=tags or [],
        )

    def create_frame(self, percepts: Optional[List[Percept]] = None,
                     context: Optional[Dict[str, Any]] = None) -> PerceptionFrame:
        """Create a new perception frame."""
        frame = PerceptionFrame(
            percepts=percepts or [],
            context=context or {},
        )
        return frame

    def perceive(self, frame: PerceptionFrame) -> PerceptionFrame:
        """
        Process a perception frame through the full pipeline:
        attention -> fusion -> store.
        """
        with self._lock:
            frame = self._attention_system.attend(frame)
            frame = self._fusion_engine.fuse(frame)
            self._last_frame = frame
            return frame

    def get_last_frame(self) -> Optional[PerceptionFrame]:
        return self._last_frame

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "fusion": self._fusion_engine.to_dict(),
                "attention": self._attention_system.to_dict(),
                "has_last_frame": self._last_frame is not None,
                "last_frame_percepts": len(self._last_frame.percepts) if self._last_frame else 0,
            }


_global_perception_fusion: Optional[PerceptionFusionSystem] = None


def get_perception_fusion() -> PerceptionFusionSystem:
    global _global_perception_fusion
    if _global_perception_fusion is None:
        _global_perception_fusion = PerceptionFusionSystem()
    return _global_perception_fusion