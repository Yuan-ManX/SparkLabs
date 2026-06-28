"""
SparkLabs Agent - Content Synthesis Engine

A unified content synthesis system that consolidates all game content
generation pipelines into a single cohesive framework. The engine
coordinates level design, character creation, dialogue authoring, music
composition, sound effects, textures, UI elements, story quests, and
advanced visual effects (animations, particles, shaders, cutscenes) with
quality control, style consistency enforcement, and batch generation.

Architecture:
  ContentSynthesisEngine (Singleton)
    |-- RequestRouter (dispatch by ContentType and SynthesisStrategy)
    |-- StyleRegistry (style consistency profiles and references)
    |-- ConsistencyValidator (cross-content style coherence checks)
    |-- QualityRanker (multi-dimension quality scoring and ranking)
    |-- ContentCache (deduplicated result storage for reuse)
    |-- HistoryLog (per-type synthesis audit trail)

Core Capabilities:
  - synthesize: Generate a single content item under constraints
  - synthesize_batch: Generate multiple items with shared context
  - create_style_profile: Build a reusable style consistency profile
  - apply_style: Apply a style profile to existing content
  - validate_consistency: Validate style coherence across a batch
  - rank_quality: Rank results by multi-dimension quality scoring
  - get_synthesis_history: Per-type audit trail retrieval
  - get_style_profiles: Access all registered style profiles
  - get_status: Real-time engine status snapshot

Usage:
    engine = get_content_synthesis_engine()
    request = SynthesisRequest(
        content_type=ContentType.CHARACTER,
        strategy=SynthesisStrategy.HYBRID,
        quality_tier=QualityTier.REFINED,
        prompt="Design a rogue alchemist NPC",
        constraints={"faction": "underground", "power_level": 7},
    )
    result = engine.synthesize(request)
    batch = engine.synthesize_batch([request, request2, request3])
    style = engine.create_style_profile("noir", references=[result])
"""

from __future__ import annotations

import random
import threading
import time as _time_module
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ContentType(Enum):
    """All content pipelines unified by the synthesis engine."""
    LEVEL = "level"
    CHARACTER = "character"
    DIALOGUE = "dialogue"
    MUSIC = "music"
    SFX = "sfx"
    TEXTURE = "texture"
    UI_ELEMENT = "ui_element"
    QUEST = "quest"
    ANIMATION = "animation"
    PARTICLE = "particle"
    SHADER = "shader"
    CUTSCENE = "cutscene"

    @classmethod
    def all_types(cls) -> List["ContentType"]:
        """Return all content types in canonical order."""
        return list(cls)


class SynthesisStrategy(Enum):
    """Strategies for generating content within a pipeline."""
    TEMPLATE_BASED = "template_based"
    PROCEDURAL = "procedural"
    NEURAL = "neural"
    HYBRID = "hybrid"
    REMIX = "remix"
    STYLE_TRANSFER = "style_transfer"

    def estimated_cost(self) -> float:
        """Relative cost multiplier for the strategy."""
        return {
            SynthesisStrategy.TEMPLATE_BASED: 0.3,
            SynthesisStrategy.PROCEDURAL: 0.5,
            SynthesisStrategy.NEURAL: 1.0,
            SynthesisStrategy.HYBRID: 0.8,
            SynthesisStrategy.REMIX: 0.6,
            SynthesisStrategy.STYLE_TRANSFER: 0.7,
        }[self]


class QualityTier(Enum):
    """Quality tiers that drive refinement depth and review passes."""
    DRAFT = "draft"
    STANDARD = "standard"
    REFINED = "refined"
    POLISHED = "polished"
    MASTERWORK = "masterwork"

    def min_score(self) -> float:
        """Minimum quality score required for this tier."""
        return {
            QualityTier.DRAFT: 0.30,
            QualityTier.STANDARD: 0.55,
            QualityTier.REFINED: 0.72,
            QualityTier.POLISHED: 0.85,
            QualityTier.MASTERWORK: 0.95,
        }[self]

    def refinement_passes(self) -> int:
        """Number of refinement passes implied by this tier."""
        return {
            QualityTier.DRAFT: 0,
            QualityTier.STANDARD: 1,
            QualityTier.REFINED: 2,
            QualityTier.POLISHED: 3,
            QualityTier.MASTERWORK: 4,
        }[self]


class ConsistencyMode(Enum):
    """Strictness of cross-content style consistency enforcement."""
    STRICT = "strict"
    MODERATE = "moderate"
    LOOSE = "loose"
    EXPERIMENTAL = "experimental"

    def tolerance(self) -> float:
        """Allowed deviation from the style profile (higher = looser)."""
        return {
            ConsistencyMode.STRICT: 0.05,
            ConsistencyMode.MODERATE: 0.15,
            ConsistencyMode.LOOSE: 0.35,
            ConsistencyMode.EXPERIMENTAL: 0.60,
        }[self]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SynthesisRequest:
    """A request to synthesize a single content item."""
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    content_type: ContentType = ContentType.CHARACTER
    strategy: SynthesisStrategy = SynthesisStrategy.HYBRID
    quality_tier: QualityTier = QualityTier.STANDARD
    prompt: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)
    style_profile_id: Optional[str] = None
    seed: Optional[str] = None
    references: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: float = 0.5
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "content_type": self.content_type.value,
            "strategy": self.strategy.value,
            "quality_tier": self.quality_tier.value,
            "prompt": self.prompt,
            "constraints": dict(self.constraints),
            "style_profile_id": self.style_profile_id,
            "seed": self.seed,
            "references": list(self.references),
            "metadata": dict(self.metadata),
            "priority": round(self.priority, 4),
            "created_at": self.created_at,
        }


@dataclass
class SynthesisResult:
    """Generated content result for a single synthesis request."""
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    request_id: str = ""
    content_type: ContentType = ContentType.CHARACTER
    strategy: SynthesisStrategy = SynthesisStrategy.HYBRID
    quality_tier: QualityTier = QualityTier.STANDARD
    content: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    consistency_score: float = 0.0
    novelty_score: float = 0.0
    coherence_score: float = 0.0
    fidelity_score: float = 0.0
    refinement_passes: int = 0
    applied_style_id: Optional[str] = None
    generation_time_ms: float = 0.0
    cost_estimate: float = 0.0
    success: bool = False
    error: Optional[str] = None
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "request_id": self.request_id,
            "content_type": self.content_type.value,
            "strategy": self.strategy.value,
            "quality_tier": self.quality_tier.value,
            "content": dict(self.content),
            "quality_score": round(self.quality_score, 4),
            "consistency_score": round(self.consistency_score, 4),
            "novelty_score": round(self.novelty_score, 4),
            "coherence_score": round(self.coherence_score, 4),
            "fidelity_score": round(self.fidelity_score, 4),
            "refinement_passes": self.refinement_passes,
            "applied_style_id": self.applied_style_id,
            "generation_time_ms": round(self.generation_time_ms, 2),
            "cost_estimate": round(self.cost_estimate, 4),
            "success": self.success,
            "error": self.error,
        }


@dataclass
class ContentBatch:
    """A batch of content items synthesized together with shared context."""
    batch_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    results: List[SynthesisResult] = field(default_factory=list)
    shared_style_id: Optional[str] = None
    consistency_mode: ConsistencyMode = ConsistencyMode.MODERATE
    overall_quality: float = 0.0
    consistency_rating: float = 0.0
    total_time_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "results": [r.to_dict() for r in self.results],
            "shared_style_id": self.shared_style_id,
            "consistency_mode": self.consistency_mode.value,
            "overall_quality": round(self.overall_quality, 4),
            "consistency_rating": round(self.consistency_rating, 4),
            "total_time_ms": round(self.total_time_ms, 2),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }


@dataclass
class StyleProfile:
    """A reusable style consistency profile for content generation."""
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    mood_tags: List[str] = field(default_factory=list)
    color_palette: List[str] = field(default_factory=list)
    tonal_reference: str = "neutral"
    complexity_target: float = 0.5
    coherence_baseline: float = 0.8
    reference_count: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "description": self.description,
            "attributes": dict(self.attributes),
            "mood_tags": list(self.mood_tags),
            "color_palette": list(self.color_palette),
            "tonal_reference": self.tonal_reference,
            "complexity_target": round(self.complexity_target, 4),
            "coherence_baseline": round(self.coherence_baseline, 4),
            "reference_count": self.reference_count,
        }


@dataclass
class SynthesisMetrics:
    """Aggregated metrics for synthesis operations."""
    total_syntheses: int = 0
    total_batches: int = 0
    total_errors: int = 0
    by_content_type: Dict[str, int] = field(default_factory=dict)
    by_strategy: Dict[str, int] = field(default_factory=dict)
    by_quality_tier: Dict[str, int] = field(default_factory=dict)
    avg_quality_score: float = 0.0
    avg_consistency_score: float = 0.0
    avg_generation_time_ms: float = 0.0
    total_cost: float = 0.0
    style_profiles_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_syntheses": self.total_syntheses,
            "total_batches": self.total_batches,
            "total_errors": self.total_errors,
            "by_content_type": dict(self.by_content_type),
            "by_strategy": dict(self.by_strategy),
            "by_quality_tier": dict(self.by_quality_tier),
            "avg_quality_score": round(self.avg_quality_score, 4),
            "avg_consistency_score": round(self.avg_consistency_score, 4),
            "avg_generation_time_ms": round(self.avg_generation_time_ms, 2),
            "total_cost": round(self.total_cost, 4),
            "style_profiles_count": self.style_profiles_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
        }


@dataclass
class ContentSynthesisSnapshot:
    """Complete system snapshot for diagnostics and persistence."""
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=_time_module.time)
    status: str = "idle"
    metrics: Optional[SynthesisMetrics] = None
    style_profiles: List[StyleProfile] = field(default_factory=list)
    recent_results: List[SynthesisResult] = field(default_factory=list)
    active_batches: int = 0
    cache_size: int = 0
    history_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "style_profiles": [p.to_dict() for p in self.style_profiles],
            "recent_results": [r.to_dict() for r in self.recent_results],
            "active_batches": self.active_batches,
            "cache_size": self.cache_size,
            "history_size": self.history_size,
        }


# ---------------------------------------------------------------------------
# ContentSynthesisEngine - Singleton
# ---------------------------------------------------------------------------

class ContentSynthesisEngine:
    """Unified content synthesis engine coordinating all generation pipelines.

    The ContentSynthesisEngine is the central hub that dispatches synthesis
    requests across content types (levels, characters, dialogue, music, SFX,
    textures, UI, quests, animations, particles, shaders, cutscenes), enforces
    style consistency, applies quality tiers, and supports batch generation
    with cross-item coherence validation.
    """

    _instance: Optional["ContentSynthesisEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_HISTORY_SIZE: int = 500
    MAX_CACHE_SIZE: int = 200

    # Content-type-specific generation baseline times (ms)
    _BASE_GEN_TIMES: Dict[ContentType, float] = {
        ContentType.LEVEL: 320.0,
        ContentType.CHARACTER: 280.0,
        ContentType.DIALOGUE: 120.0,
        ContentType.MUSIC: 450.0,
        ContentType.SFX: 180.0,
        ContentType.TEXTURE: 220.0,
        ContentType.UI_ELEMENT: 90.0,
        ContentType.QUEST: 260.0,
        ContentType.ANIMATION: 240.0,
        ContentType.PARTICLE: 140.0,
        ContentType.SHADER: 200.0,
        ContentType.CUTSCENE: 380.0,
    }

    def __new__(cls) -> "ContentSynthesisEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ContentSynthesisEngine":
        """Get or create the singleton ContentSynthesisEngine instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        with self._lock:
            if getattr(self, "_initialized", False):
                return
            self._initialized: bool = True
            self._style_profiles: Dict[str, StyleProfile] = {}
            self._content_cache: Dict[str, SynthesisResult] = {}
            self._history: deque = deque(maxlen=self.MAX_HISTORY_SIZE)
            self._history_by_type: Dict[str, deque] = defaultdict(
                lambda: deque(maxlen=100)
            )
            self._active_batches: int = 0
            self._status: str = "idle"
            self._metrics = SynthesisMetrics()
            self._quality_accumulator: List[float] = []
            self._consistency_accumulator: List[float] = []
            self._time_accumulator: List[float] = []
            self._seed_default_profiles()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the synthesis engine and seed default style profiles."""
        with self._lock:
            if not self._style_profiles:
                self._seed_default_profiles()
            self._status = "ready"

    def shutdown(self) -> None:
        """Graceful shutdown releasing caches and marking the engine idle."""
        with self._lock:
            self._content_cache.clear()
            self._status = "shutdown"

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Synthesize a single content item from a request.

        Args:
            request: A SynthesisRequest describing the desired content.

        Returns:
            A SynthesisResult with generated content and quality scores.
        """
        start = _time_module.time()
        result = SynthesisResult(
            request_id=request.request_id,
            content_type=request.content_type,
            strategy=request.strategy,
            quality_tier=request.quality_tier,
            applied_style_id=request.style_profile_id,
        )

        try:
            # Cache lookup
            cache_key = self._cache_key(request)
            if cache_key in self._content_cache:
                cached = self._content_cache[cache_key]
                result = SynthesisResult(
                    request_id=request.request_id,
                    content_type=cached.content_type,
                    strategy=cached.strategy,
                    quality_tier=cached.quality_tier,
                    content=dict(cached.content),
                    quality_score=cached.quality_score,
                    consistency_score=cached.consistency_score,
                    novelty_score=cached.novelty_score,
                    coherence_score=cached.coherence_score,
                    fidelity_score=cached.fidelity_score,
                    refinement_passes=cached.refinement_passes,
                    applied_style_id=request.style_profile_id,
                    generation_time_ms=1.0,
                    cost_estimate=0.0,
                    success=True,
                )
                with self._lock:
                    self._metrics.cache_hits += 1
                return result

            with self._lock:
                self._metrics.cache_misses += 1
                self._status = "synthesizing"

            # Generate raw content
            content = self._generate_content(request)
            result.content = content

            # Apply style if a profile is referenced
            if request.style_profile_id:
                profile = self._style_profiles.get(request.style_profile_id)
                if profile is not None:
                    result.content = self.apply_style(content, profile)
                    result.applied_style_id = profile.profile_id

            # Quality scoring
            scores = self._score_quality(result.content, request)
            result.quality_score = scores["quality"]
            result.novelty_score = scores["novelty"]
            result.coherence_score = scores["coherence"]
            result.fidelity_score = scores["fidelity"]

            # Refinement passes driven by tier
            passes = request.quality_tier.refinement_passes()
            target = request.quality_tier.min_score()
            for _ in range(passes):
                if result.quality_score >= target:
                    break
                result.content = self._refine_content(result.content, request)
                result.quality_score = min(
                    1.0, result.quality_score + random.uniform(0.04, 0.10)
                )
                result.refinement_passes += 1

            # Consistency score against style profile
            result.consistency_score = self._consistency_for(result, request)

            # Cost and timing
            result.generation_time_ms = (_time_module.time() - start) * 1000.0
            result.cost_estimate = (
                request.strategy.estimated_cost()
                * (1 + result.refinement_passes * 0.15)
            )
            result.success = result.quality_score >= target

            # Persist
            with self._lock:
                self._content_cache[cache_key] = result
                if len(self._content_cache) > self.MAX_CACHE_SIZE:
                    self._content_cache.pop(next(iter(self._content_cache)))
                self._history.append(result)
                self._history_by_type[request.content_type.value].append(result)
                self._record_metrics(request, result)
                self._status = "ready"

        except Exception as exc:  # noqa: BLE001 - preserve engine stability
            result.success = False
            result.error = str(exc)
            result.generation_time_ms = (_time_module.time() - start) * 1000.0
            with self._lock:
                self._metrics.total_errors += 1
                self._status = "ready"

        return result

    def synthesize_batch(
        self, requests: List[SynthesisRequest]
    ) -> ContentBatch:
        """Synthesize multiple items in a batch with shared context.

        Args:
            requests: A list of SynthesisRequest objects.

        Returns:
            A ContentBatch containing all results and consistency metrics.
        """
        batch = ContentBatch()
        batch_start = _time_module.time()

        with self._lock:
            self._active_batches += 1
            self._status = "batch_synthesizing"

        try:
            shared_style = None
            for req in requests:
                if req.style_profile_id:
                    shared_style = req.style_profile_id
                    batch.shared_style_id = shared_style
                    break

            results: List[SynthesisResult] = []
            for req in requests:
                results.append(self.synthesize(req))

            batch.results = results
            batch.success_count = sum(1 for r in results if r.success)
            batch.failure_count = len(results) - batch.success_count

            # Consistency across the batch
            mode = ConsistencyMode.MODERATE
            validation = self.validate_consistency(batch, mode)
            batch.consistency_rating = validation.get("consistency_rating", 0.0)

            if results:
                batch.overall_quality = (
                    sum(r.quality_score for r in results) / len(results)
                )

            batch.total_time_ms = (_time_module.time() - batch_start) * 1000.0

            with self._lock:
                self._metrics.total_batches += 1
                self._active_batches = max(0, self._active_batches - 1)
                self._status = "ready"

        except Exception:  # noqa: BLE001
            with self._lock:
                self._active_batches = max(0, self._active_batches - 1)
                self._status = "ready"

        return batch

    # ------------------------------------------------------------------
    # Style Management
    # ------------------------------------------------------------------

    def create_style_profile(
        self,
        name: str,
        references: Optional[List[Any]] = None,
        description: str = "",
    ) -> StyleProfile:
        """Create a reusable style consistency profile from references.

        Args:
            name: Human-readable profile name.
            references: A list of reference objects (SynthesisResult or dicts).
            description: Optional description of the intended style.

        Returns:
            A newly registered StyleProfile.
        """
        profile = StyleProfile(name=name, description=description)

        if references:
            palette: List[str] = []
            moods: List[str] = []
            complexities: List[float] = []
            for ref in references:
                ref_dict = ref.to_dict() if hasattr(ref, "to_dict") else ref
                if not isinstance(ref_dict, dict):
                    continue
                content = ref_dict.get("content", {}) or {}
                palette.extend(content.get("color_palette", []) or [])
                moods.extend(content.get("mood_tags", []) or [])
                if "complexity" in content:
                    complexities.append(float(content["complexity"]))
                profile.attributes.update(
                    {k: v for k, v in content.items() if k not in
                     ("color_palette", "mood_tags", "complexity")}
                )
            profile.reference_count = len(references)
            if palette:
                # Deduplicate preserving order
                seen: set = set()
                profile.color_palette = [
                    c for c in palette if not (c in seen or seen.add(c))
                ][:12]
            if moods:
                seen_m: set = set()
                profile.mood_tags = [
                    m for m in moods if not (m in seen_m or seen_m.add(m))
                ][:8]
            if complexities:
                profile.complexity_target = sum(complexities) / len(complexities)
            profile.coherence_baseline = min(
                1.0, 0.6 + 0.08 * profile.reference_count
            )

        with self._lock:
            self._style_profiles[profile.profile_id] = profile
            self._metrics.style_profiles_count = len(self._style_profiles)
        return profile

    def apply_style(
        self,
        content: Dict[str, Any],
        style_profile: StyleProfile,
    ) -> Dict[str, Any]:
        """Apply a style profile to existing content.

        Args:
            content: The raw content dict to restyle.
            style_profile: The StyleProfile to apply.

        Returns:
            A new content dict with style attributes merged in.
        """
        if not isinstance(content, dict):
            return content
        styled = dict(content)
        styled.setdefault("applied_style", style_profile.name)
        styled.setdefault("mood_tags", list(style_profile.mood_tags))
        if style_profile.color_palette and not styled.get("color_palette"):
            styled["color_palette"] = list(style_profile.color_palette)
        styled["tonal_reference"] = style_profile.tonal_reference
        styled["complexity"] = style_profile.complexity_target
        # Merge non-conflicting style attributes
        for key, value in style_profile.attributes.items():
            if key not in styled:
                styled[key] = value
        return styled

    def validate_consistency(
        self,
        content_batch: ContentBatch,
        mode: ConsistencyMode = ConsistencyMode.MODERATE,
    ) -> Dict[str, Any]:
        """Validate style consistency across a batch of content.

        Args:
            content_batch: A ContentBatch whose results to validate.
            mode: The ConsistencyMode governing tolerance.

        Returns:
            A dict with consistency rating, per-item deviations, and issues.
        """
        results = content_batch.results
        tolerance = mode.tolerance()
        issues: List[str] = []
        deviations: List[float] = []

        if not results:
            return {
                "consistency_rating": 1.0,
                "mode": mode.value,
                "deviations": [],
                "issues": [],
            }

        # Compute reference vectors
        quality_avg = sum(r.quality_score for r in results) / len(results)
        novelty_avg = sum(r.novelty_score for r in results) / len(results)
        coherence_avg = sum(r.coherence_score for r in results) / len(results)

        for idx, r in enumerate(results):
            dev = (
                abs(r.quality_score - quality_avg)
                + abs(r.novelty_score - novelty_avg)
                + abs(r.coherence_score - coherence_avg)
            ) / 3.0
            deviations.append(round(dev, 4))
            if dev > tolerance:
                issues.append(
                    f"Item {idx} ({r.content_type.value}) deviates by "
                    f"{dev:.3f} (tolerance {tolerance:.3f})"
                )

        consistency_rating = max(
            0.0, 1.0 - (sum(deviations) / len(deviations))
        )
        passed = consistency_rating >= (1.0 - tolerance)

        return {
            "consistency_rating": round(consistency_rating, 4),
            "mode": mode.value,
            "tolerance": tolerance,
            "passed": passed,
            "deviations": deviations,
            "issues": issues,
            "avg_quality": round(quality_avg, 4),
            "avg_novelty": round(novelty_avg, 4),
            "avg_coherence": round(coherence_avg, 4),
        }

    def rank_quality(
        self, results: List[SynthesisResult]
    ) -> List[SynthesisResult]:
        """Rank results by composite quality score.

        Args:
            results: A list of SynthesisResult objects.

        Returns:
            A new list sorted by descending quality score.
        """
        def composite(r: SynthesisResult) -> float:
            return (
                0.45 * r.quality_score
                + 0.20 * r.coherence_score
                + 0.20 * r.consistency_score
                + 0.15 * r.fidelity_score
            )
        return sorted(results, key=composite, reverse=True)

    # ------------------------------------------------------------------
    # Query APIs
    # ------------------------------------------------------------------

    def get_synthesis_history(
        self, content_type: Optional[ContentType] = None
    ) -> List[SynthesisResult]:
        """Get synthesis history, optionally filtered by content type.

        Args:
            content_type: If provided, filter to a specific content type.

        Returns:
            A list of SynthesisResult objects, newest first.
        """
        with self._lock:
            if content_type is None:
                return list(reversed(self._history))
            return list(reversed(self._history_by_type[content_type.value]))

    def get_style_profiles(self) -> List[StyleProfile]:
        """Get all registered style profiles.

        Returns:
            A list of StyleProfile objects.
        """
        with self._lock:
            return list(self._style_profiles.values())

    def get_status(self) -> Dict[str, Any]:
        """Get the current synthesis engine status snapshot.

        Returns:
            A dict with status, metrics, and counters.
        """
        with self._lock:
            avg_q = (
                sum(self._quality_accumulator) / len(self._quality_accumulator)
                if self._quality_accumulator else 0.0
            )
            avg_c = (
                sum(self._consistency_accumulator)
                / len(self._consistency_accumulator)
                if self._consistency_accumulator else 0.0
            )
            avg_t = (
                sum(self._time_accumulator) / len(self._time_accumulator)
                if self._time_accumulator else 0.0
            )
            self._metrics.avg_quality_score = avg_q
            self._metrics.avg_consistency_score = avg_c
            self._metrics.avg_generation_time_ms = avg_t
            return {
                "status": self._status,
                "metrics": self._metrics.to_dict(),
                "active_batches": self._active_batches,
                "style_profiles": len(self._style_profiles),
                "cache_size": len(self._content_cache),
                "history_size": len(self._history),
            }

    def snapshot(self) -> ContentSynthesisSnapshot:
        """Capture a complete system snapshot for diagnostics.

        Returns:
            A ContentSynthesisSnapshot with current state.
        """
        with self._lock:
            metrics_copy = SynthesisMetrics(**self._metrics.__dict__)
            return ContentSynthesisSnapshot(
                status=self._status,
                metrics=metrics_copy,
                style_profiles=list(self._style_profiles.values()),
                recent_results=list(self._history)[-20:],
                active_batches=self._active_batches,
                cache_size=len(self._content_cache),
                history_size=len(self._history),
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _seed_default_profiles(self) -> None:
        """Seed a small set of default style profiles."""
        defaults = [
            ("default_fantasy", "fantasy", ["epic", "magical", "heroic"],
             ["#4a1a6a", "#7a3aaa", "#dac0ff"]),
            ("default_noir", "noir", ["dark", "moody", "tense"],
             ["#1a1a1a", "#4a4a4a", "#8a8a8a"]),
            ("default_neon", "neon", ["vibrant", "energetic", "cyberpunk"],
             ["#ff00ff", "#00ffff", "#0a0a2e"]),
        ]
        for name, label, moods, palette in defaults:
            profile = StyleProfile(
                name=name,
                description=f"Auto-seeded {label} style profile",
                mood_tags=moods,
                color_palette=palette,
                tonal_reference=label,
                complexity_target=0.6 if label == "fantasy" else 0.5,
                coherence_baseline=0.85,
            )
            self._style_profiles[profile.profile_id] = profile

    def _generate_content(
        self, request: SynthesisRequest
    ) -> Dict[str, Any]:
        """Generate raw content dict for the request's content type."""
        base_time = self._BASE_GEN_TIMES.get(request.content_type, 200.0)
        seed = request.seed or uuid.uuid4().hex[:8]
        prompt_summary = (
            request.prompt[:120] + "..."
            if len(request.prompt) > 120 else request.prompt
        )
        ct = request.content_type
        c = request.constraints

        # Type-specific payloads
        type_payloads: Dict[ContentType, Dict[str, Any]] = {
            ContentType.LEVEL: {
                "layout_seed": seed, "rooms": random.randint(4, 12),
                "biome": c.get("biome", "temperate"), "difficulty_curve": "progressive",
            },
            ContentType.CHARACTER: {
                "archetype": c.get("archetype", "neutral"),
                "traits": ["courageous", "resourceful"][:random.randint(1, 2)],
                "backbone_seed": seed, "power_level": c.get("power_level", 5),
            },
            ContentType.DIALOGUE: {
                "lines": random.randint(3, 8),
                "tone": c.get("tone", "neutral"),
                "branching": c.get("branching", False),
            },
            ContentType.MUSIC: {
                "tempo_bpm": random.randint(70, 160),
                "key": random.choice(["C_major", "A_minor", "D_dorian"]),
                "duration_sec": random.randint(30, 180),
            },
            ContentType.SFX: {
                "effect_type": c.get("effect_type", "impact"),
                "duration_ms": random.randint(80, 1200), "layered": True,
            },
            ContentType.TEXTURE: {
                "resolution": c.get("resolution", "512x512"),
                "tiling": c.get("tiling", True),
                "channels": ["albedo", "normal", "roughness"],
            },
            ContentType.UI_ELEMENT: {
                "element": c.get("element", "button"),
                "responsive": True, "theme": c.get("theme", "default"),
            },
            ContentType.QUEST: {
                "objectives": random.randint(2, 5),
                "reward_tier": c.get("reward_tier", "standard"),
                "branches": random.randint(1, 3),
            },
            ContentType.ANIMATION: {
                "rig": c.get("rig", "humanoid"),
                "frames": random.randint(12, 60),
                "looping": c.get("looping", False),
            },
            ContentType.PARTICLE: {
                "emitter_shape": c.get("shape", "cone"),
                "max_particles": random.randint(100, 2000),
                "lifetime_ms": random.randint(300, 3000),
            },
            ContentType.SHADER: {
                "stage": c.get("stage", "fragment"),
                "inputs": ["uv", "normal", "time"],
                "technique": c.get("technique", "pbr"),
            },
            ContentType.CUTSCENE: {
                "shots": random.randint(3, 10),
                "duration_sec": random.randint(15, 90),
                "camera_work": "cinematic",
            },
        }

        complexity = min(1.0, 0.3 + len(c) * 0.08)
        content: Dict[str, Any] = {
            "content_type": ct.value, "prompt": request.prompt,
            "prompt_summary": prompt_summary, "seed": seed,
            "strategy": request.strategy.value, "complexity": complexity,
            "estimated_complexity": round(complexity, 4),
            "generation_hint_ms": round(base_time, 2),
        }
        content.update(type_payloads.get(ct, {}))

        # Merge remaining constraints as overrides
        for key, value in c.items():
            if key not in content:
                content[key] = value
        return content

    def _refine_content(
        self,
        content: Dict[str, Any],
        request: SynthesisRequest,
    ) -> Dict[str, Any]:
        """Apply a refinement pass to existing content."""
        refined = dict(content)
        refined["refinement_applied"] = refined.get("refinement_applied", 0) + 1
        refined["complexity"] = min(
            1.0, float(refined.get("complexity", 0.5)) + 0.05
        )
        return refined

    def _score_quality(
        self,
        content: Dict[str, Any],
        request: SynthesisRequest,
    ) -> Dict[str, float]:
        """Score content across quality dimensions."""
        prompt_len = len(request.prompt)
        constraint_count = len(request.constraints)

        quality = min(
            1.0,
            0.4
            + min(0.3, prompt_len / 400.0)
            + min(0.2, constraint_count * 0.04)
            + random.uniform(0.0, 0.1),
        )
        novelty = max(
            0.0,
            min(1.0, 0.3 + random.uniform(0.0, 0.6)
                if request.strategy in (
                    SynthesisStrategy.NEURAL,
                    SynthesisStrategy.REMIX,
                    SynthesisStrategy.STYLE_TRANSFER,
                )
                else random.uniform(0.2, 0.5)),
        )
        coherence = max(
            0.0,
            min(1.0, 0.6 + 0.05 * constraint_count + random.uniform(-0.1, 0.2)),
        )
        fidelity = max(
            0.0,
            min(1.0, 0.5 + min(0.4, prompt_len / 300.0) + random.uniform(-0.1, 0.1)),
        )

        return {
            "quality": round(quality, 4),
            "novelty": round(novelty, 4),
            "coherence": round(coherence, 4),
            "fidelity": round(fidelity, 4),
        }

    def _consistency_for(
        self,
        result: SynthesisResult,
        request: SynthesisRequest,
    ) -> float:
        """Compute a consistency score against the referenced style profile."""
        if not request.style_profile_id:
            return round(0.7 + random.uniform(-0.1, 0.15), 4)
        profile = self._style_profiles.get(request.style_profile_id)
        if profile is None:
            return round(0.6 + random.uniform(-0.1, 0.2), 4)
        baseline = profile.coherence_baseline
        deviation = abs(result.quality_score - baseline) * 0.5
        return round(max(0.0, min(1.0, baseline - deviation + random.uniform(-0.05, 0.05))), 4)

    def _cache_key(self, request: SynthesisRequest) -> str:
        """Build a deterministic cache key for a request."""
        constraints_hash = hash(
            tuple(sorted(request.constraints.items()))
        )
        return (
            f"{request.content_type.value}|{request.strategy.value}|"
            f"{request.quality_tier.value}|{request.prompt}|"
            f"{request.style_profile_id}|{constraints_hash}"
        )

    def _record_metrics(
        self,
        request: SynthesisRequest,
        result: SynthesisResult,
    ) -> None:
        """Update aggregate metrics after a synthesis."""
        m = self._metrics
        m.total_syntheses += 1
        m.by_content_type[request.content_type.value] = (
            m.by_content_type.get(request.content_type.value, 0) + 1
        )
        m.by_strategy[request.strategy.value] = (
            m.by_strategy.get(request.strategy.value, 0) + 1
        )
        m.by_quality_tier[request.quality_tier.value] = (
            m.by_quality_tier.get(request.quality_tier.value, 0) + 1
        )
        m.total_cost += result.cost_estimate
        self._quality_accumulator.append(result.quality_score)
        self._consistency_accumulator.append(result.consistency_score)
        self._time_accumulator.append(result.generation_time_ms)
        # Keep accumulators bounded
        if len(self._quality_accumulator) > 1000:
            self._quality_accumulator = self._quality_accumulator[-500:]
            self._consistency_accumulator = self._consistency_accumulator[-500:]
            self._time_accumulator = self._time_accumulator[-500:]


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_content_synthesis_engine() -> ContentSynthesisEngine:
    """Get the ContentSynthesisEngine singleton instance."""
    return ContentSynthesisEngine.get_instance()
