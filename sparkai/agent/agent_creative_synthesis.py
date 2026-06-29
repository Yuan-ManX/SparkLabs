"""
SparkLabs Agent - Creative Synthesis Engine

A multi-domain creative synthesis engine that combines multiple creative
inputs into unified outputs. Supports narrative, visual, audio, gameplay,
character, level, mechanic, and theme domains, and provides idea
generation, style combination, and creativity evaluation.

Architecture:
  CreativeSynthesisEngine (Singleton)
    |-- CreativeDomain (typed creative domain)
    |-- CreativeInput (a single weighted contribution to a synthesis)
    |-- CreativeOutput (the unified result of a synthesis)
    |-- CreativeSynthesisSnapshot (point-in-time state capture)

The engine supports pluggable per-domain handlers so callers can override
idea generation for specific creative domains.
"""

from __future__ import annotations

import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


_time = _time_module


# =============================================================================
# Enums
# =============================================================================


class CreativeDomain(Enum):
    """Typed creative domain handled by the synthesis engine."""

    NARRATIVE = "narrative"
    VISUAL = "visual"
    AUDIO = "audio"
    GAMEPLAY = "gameplay"
    CHARACTER = "character"
    LEVEL = "level"
    MECHANIC = "mechanic"
    THEME = "theme"


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class CreativeInput:
    """A single weighted contribution to a creative synthesis.

    Attributes:
        input_id: Auto-generated unique identifier for the input.
        domain: The CreativeDomain this input belongs to.
        content: The creative content payload (text, config, etc.).
        weight: Importance weight in [0.0, 1.0] applied during blending.
        metadata: Optional auxiliary information about the input.
    """

    input_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: CreativeDomain = CreativeDomain.NARRATIVE
    content: Any = ""
    weight: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_id": self.input_id,
            "domain": self.domain.value,
            "content": self.content,
            "weight": self.weight,
            "metadata": dict(self.metadata),
        }


@dataclass
class CreativeOutput:
    """The unified result of a creative synthesis.

    Attributes:
        output_id: Auto-generated unique identifier for the output.
        domains: List of domain value strings contributing to the output.
        content: The synthesized creative content payload.
        quality_score: Estimated quality in [0.0, 1.0].
        novelty_score: Estimated novelty in [0.0, 1.0].
        coherence_score: Estimated coherence in [0.0, 1.0].
    """

    output_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domains: List[str] = field(default_factory=list)
    content: Any = ""
    quality_score: float = 0.0
    novelty_score: float = 0.0
    coherence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "output_id": self.output_id,
            "domains": list(self.domains),
            "content": self.content,
            "quality_score": self.quality_score,
            "novelty_score": self.novelty_score,
            "coherence_score": self.coherence_score,
        }


@dataclass
class CreativeSynthesisSnapshot:
    """Point-in-time capture of the creative synthesis engine state.

    Attributes:
        snapshot_id: Auto-generated unique identifier for the snapshot.
        captured_at: POSIX timestamp of capture.
        output_history: Serialized recent creative outputs.
        output_count: Number of outputs synthesized.
        system_status: Aggregate status dictionary at capture time.
    """

    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    captured_at: float = field(default_factory=_time.time)
    output_history: List[Dict[str, Any]] = field(default_factory=list)
    output_count: int = 0
    system_status: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at,
            "output_history": self.output_history,
            "output_count": self.output_count,
            "system_status": self.system_status,
        }


# =============================================================================
# CreativeSynthesisEngine (Singleton)
# =============================================================================


class CreativeSynthesisEngine:
    """Combines multiple creative inputs into unified outputs (singleton).

    Provides multi-domain synthesis, idea generation, style combination,
    and creativity evaluation. The engine is thread-safe and intended to
    be accessed through the module-level
    :func:`get_creative_synthesis_engine` factory.

    Per-domain handlers can be registered via
    :meth:`register_domain_handler` to override the default idea
    generation for a specific CreativeDomain.

    Usage:
        engine = get_creative_synthesis_engine()
        output = engine.synthesize([
            CreativeInput(domain=CreativeDomain.NARRATIVE, content="hero's journey", weight=0.8),
            CreativeInput(domain=CreativeDomain.THEME, content="redemption", weight=0.6),
        ])
        idea = engine.generate_idea(CreativeDomain.LEVEL, "a vertical cliff village")
        scores = engine.evaluate_creativity(output)
    """

    _instance: Optional["CreativeSynthesisEngine"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_HISTORY: int = 500

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._output_history: List[CreativeOutput] = []
        self._domain_handlers: Dict[CreativeDomain, Callable[[str], CreativeOutput]] = {}
        self._stats: Dict[str, Any] = {
            "total_syntheses": 0,
            "total_ideas_generated": 0,
            "total_style_combos": 0,
            "total_evaluations": 0,
            "domain_counts": {d.value: 0 for d in CreativeDomain},
        }
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "CreativeSynthesisEngine":
        """Return the singleton CreativeSynthesisEngine instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    def synthesize(self, inputs: List[CreativeInput]) -> CreativeOutput:
        """Combine multiple creative inputs into a unified output.

        Blends input content weighted by each input's weight, records the
        contributing domains, and scores the result for quality, novelty,
        and coherence using heuristic estimators.

        Args:
            inputs: The CreativeInput instances to synthesize.

        Returns:
            A CreativeOutput summarizing the synthesis.
        """
        with self._instance_lock:
            domains: List[str] = []
            domain_set = set()
            blended_parts: List[str] = []
            total_weight = 0.0
            for inp in inputs or []:
                if inp.domain.value not in domain_set:
                    domains.append(inp.domain.value)
                    domain_set.add(inp.domain.value)
                blended_parts.append(f"[{inp.domain.value}:{inp.weight:.2f}] {inp.content}")
                total_weight += inp.weight
                self._stats["domain_counts"][inp.domain.value] = (
                    self._stats["domain_counts"].get(inp.domain.value, 0) + 1
                )
            content = "\n".join(blended_parts) if blended_parts else ""
            output = CreativeOutput(
                domains=domains,
                content=content,
                quality_score=self._estimate_quality(inputs, total_weight),
                novelty_score=self._estimate_novelty(inputs),
                coherence_score=self._estimate_coherence(inputs),
            )
            self._output_history.append(output)
            if len(self._output_history) > self._MAX_HISTORY:
                self._output_history = self._output_history[-self._MAX_HISTORY:]
            self._stats["total_syntheses"] += 1
            return output

    def generate_idea(self, domain: CreativeDomain, prompt: str) -> CreativeOutput:
        """Generate a single-domain creative idea from a prompt.

        Dispatches to a registered per-domain handler when one exists;
        otherwise uses the default generator which elaborates the prompt
        with domain-specific framing.

        Args:
            domain: The CreativeDomain to generate in.
            prompt: The seed prompt for idea generation.

        Returns:
            A CreativeOutput containing the generated idea.
        """
        with self._instance_lock:
            handler = self._domain_handlers.get(domain)
            if handler is not None:
                output = handler(prompt)
            else:
                output = self._default_generate(domain, prompt)
            self._output_history.append(output)
            if len(self._output_history) > self._MAX_HISTORY:
                self._output_history = self._output_history[-self._MAX_HISTORY:]
            self._stats["total_ideas_generated"] += 1
            self._stats["domain_counts"][domain.value] = (
                self._stats["domain_counts"].get(domain.value, 0) + 1
            )
            return output

    # ------------------------------------------------------------------
    # Style Combination & Evaluation
    # ------------------------------------------------------------------

    def combine_styles(self, style_a: Dict[str, Any], style_b: Dict[str, Any]) -> Dict[str, Any]:
        """Combine two style dictionaries into a merged style profile.

        Keys present in both styles are blended 50/50 (numeric values are
        averaged; non-numeric values take style_a's). Keys present in only
        one style are inherited directly.

        Args:
            style_a: The first style dictionary.
            style_b: The second style dictionary.

        Returns:
            A merged style dictionary.
        """
        with self._instance_lock:
            merged: Dict[str, Any] = {}
            all_keys = set(style_a) | set(style_b)
            for key in all_keys:
                in_a = key in style_a
                in_b = key in style_b
                if in_a and in_b:
                    val_a = style_a[key]
                    val_b = style_b[key]
                    if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                        merged[key] = (val_a + val_b) / 2.0
                    else:
                        merged[key] = val_a
                elif in_a:
                    merged[key] = style_a[key]
                else:
                    merged[key] = style_b[key]
            self._stats["total_style_combos"] += 1
            return merged

    def evaluate_creativity(self, output: CreativeOutput) -> Dict[str, Any]:
        """Evaluate a CreativeOutput's creativity metrics.

        Returns the output's scores alongside composite metrics derived
        from the quality, novelty, and coherence scores.

        Args:
            output: The CreativeOutput to evaluate.

        Returns:
            A dictionary of evaluation metrics.
        """
        with self._instance_lock:
            quality = output.quality_score
            novelty = output.novelty_score
            coherence = output.coherence_score
            composite = (quality + novelty + coherence) / 3.0
            balance = 1.0 - (
                abs(quality - novelty) + abs(novelty - coherence) + abs(quality - coherence)
            ) / 3.0
            balance = max(0.0, min(1.0, balance))
            self._stats["total_evaluations"] += 1
            return {
                "output_id": output.output_id,
                "quality_score": quality,
                "novelty_score": novelty,
                "coherence_score": coherence,
                "composite_score": composite,
                "balance_score": balance,
                "domains": list(output.domains),
            }

    # ------------------------------------------------------------------
    # Handler Registration
    # ------------------------------------------------------------------

    def register_domain_handler(
        self,
        domain: CreativeDomain,
        handler: Callable[[str], CreativeOutput],
    ) -> None:
        """Register a custom idea-generation handler for a CreativeDomain.

        Args:
            domain: The CreativeDomain the handler applies to.
            handler: Callable invoked with a prompt string during idea
                generation; must return a CreativeOutput.
        """
        with self._instance_lock:
            self._domain_handlers[domain] = handler

    # ------------------------------------------------------------------
    # Status & Snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return aggregate status of the creative synthesis engine."""
        with self._instance_lock:
            return {
                "output_history_size": len(self._output_history),
                "registered_handlers": [d.value for d in self._domain_handlers],
                "stats": dict(self._stats),
            }

    def get_snapshot(self) -> CreativeSynthesisSnapshot:
        """Capture a point-in-time snapshot of the engine state."""
        with self._instance_lock:
            status = self.get_status()
            return CreativeSynthesisSnapshot(
                captured_at=_time.time(),
                output_history=[o.to_dict() for o in self._output_history],
                output_count=len(self._output_history),
                system_status=status,
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear output history, handlers, and statistics."""
        with self._instance_lock:
            self._output_history.clear()
            self._domain_handlers.clear()
            self._stats = {
                "total_syntheses": 0,
                "total_ideas_generated": 0,
                "total_style_combos": 0,
                "total_evaluations": 0,
                "domain_counts": {d.value: 0 for d in CreativeDomain},
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _estimate_quality(
        self, inputs: List[CreativeInput], total_weight: float
    ) -> float:
        """Estimate a quality score in [0.0, 1.0] from the inputs."""
        if not inputs or total_weight <= 0:
            return 0.0
        # Quality rises with the number of distinct domains and average weight.
        distinct_domains = len({inp.domain for inp in inputs})
        avg_weight = total_weight / len(inputs)
        return min(1.0, 0.4 * distinct_domains / 4.0 + 0.6 * avg_weight)

    def _estimate_novelty(self, inputs: List[CreativeInput]) -> float:
        """Estimate a novelty score in [0.0, 1.0] from the inputs."""
        if not inputs:
            return 0.0
        domains = len({inp.domain for inp in inputs})
        # More domains and more varied weights -> higher novelty.
        weight_spread = max((inp.weight for inp in inputs), default=0.0) - min(
            (inp.weight for inp in inputs), default=0.0
        )
        novelty = 0.5 * min(1.0, domains / 4.0) + 0.5 * weight_spread
        # Add a small random jitter to reflect creative variance.
        novelty += random.uniform(-0.05, 0.05)
        return max(0.0, min(1.0, novelty))

    def _estimate_coherence(self, inputs: List[CreativeInput]) -> float:
        """Estimate a coherence score in [0.0, 1.0] from the inputs."""
        if not inputs:
            return 0.0
        # Coherence is higher when fewer domains are blended and weights agree.
        domains = len({inp.domain for inp in inputs})
        weights = [inp.weight for inp in inputs]
        if not weights:
            return 0.0
        avg = sum(weights) / len(weights)
        variance = sum((w - avg) ** 2 for w in weights) / len(weights)
        coherence = 0.6 * (1.0 / max(1, domains)) + 0.4 * (1.0 - min(1.0, variance))
        return max(0.0, min(1.0, coherence))

    def _default_generate(
        self, domain: CreativeDomain, prompt: str
    ) -> CreativeOutput:
        """Default idea generator when no handler is registered."""
        framing = {
            CreativeDomain.NARRATIVE: f"Narrative concept: {prompt} with rising stakes and a turning point.",
            CreativeDomain.VISUAL: f"Visual concept: {prompt} with strong silhouette and mood lighting.",
            CreativeDomain.AUDIO: f"Audio concept: {prompt} layered with leitmotif and ambient texture.",
            CreativeDomain.GAMEPLAY: f"Gameplay concept: {prompt} with a risk/reward loop and clear feedback.",
            CreativeDomain.CHARACTER: f"Character concept: {prompt} with a defining flaw and a secret want.",
            CreativeDomain.LEVEL: f"Level concept: {prompt} with landmark navigation and pacing beats.",
            CreativeDomain.MECHANIC: f"Mechanic concept: {prompt} with emergent interactions and counterplay.",
            CreativeDomain.THEME: f"Theme concept: {prompt} expressed through conflict and resolution.",
        }
        content = framing.get(domain, f"{domain.value} concept: {prompt}")
        return CreativeOutput(
            domains=[domain.value],
            content=content,
            quality_score=round(random.uniform(0.6, 0.9), 3),
            novelty_score=round(random.uniform(0.5, 0.85), 3),
            coherence_score=round(random.uniform(0.7, 0.95), 3),
        )


# =============================================================================
# Module-level factory
# =============================================================================


def get_creative_synthesis_engine() -> CreativeSynthesisEngine:
    """Return the singleton CreativeSynthesisEngine instance."""
    return CreativeSynthesisEngine.get_instance()
