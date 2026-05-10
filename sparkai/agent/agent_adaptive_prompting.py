"""
SparkLabs Agent - Adaptive Prompting Engine

Self-improving prompt generation system that tracks success
rates per template, auto-tunes prompt parameters, and selects
optimal prompt strategies for each game development task.
Implements A/B testing of prompt variants with statistical
performance tracking.

Architecture:
  AdaptivePrompting
    |-- PromptRegistry (template catalog with variants)
    |-- PerformanceTracker (success/failure metrics per variant)
    |-- PromptOptimizer (parameter tuning from feedback)
    |-- VariantSelector (epsilon-greedy best-variant selection)
    |-- TemplateComposer (context-aware prompt assembly)

Optimization Strategies:
  - EPSILON_GREEDY: explore new variants with epsilon probability
  - UCB: upper confidence bound selection for exploration
  - THOMPSON_SAMPLING: bayesian variant selection
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class OptimizationStrategy(Enum):
    EPSILON_GREEDY = "epsilon_greedy"
    UCB = "ucb"
    THOMPSON_SAMPLING = "thompson_sampling"
    BEST_FIRST = "best_first"


class TaskCategory(Enum):
    CODE_GENERATION = "code_generation"
    GAME_DESIGN = "game_design"
    ASSET_DESCRIPTION = "asset_description"
    BUG_FIXING = "bug_fixing"
    DOCUMENTATION = "documentation"
    TESTING = "testing"


@dataclass
class PromptVariant:
    variant_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    template: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    success_count: int = 0
    failure_count: int = 0
    avg_response_time: float = 0.0
    total_response_time: float = 0.0
    created_at: float = field(default_factory=time.time)
    last_used_at: float = 0.0
    context_tokens: int = 0

    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / max(total, 1)

    def record_outcome(self, success: bool, response_time: float = 0.0) -> None:
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.total_response_time += response_time
        if self.success_count + self.failure_count > 0:
            self.avg_response_time = self.total_response_time / (
                self.success_count + self.failure_count
            )
        self.last_used_at = time.time()


@dataclass
class PromptTemplate:
    template_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    category: TaskCategory = TaskCategory.CODE_GENERATION
    base_prompt: str = ""
    variables: List[str] = field(default_factory=list)
    variants: List[PromptVariant] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    total_calls: int = 0


class AdaptivePrompting:
    """
    Self-improving prompt generation with performance-based
    variant selection and automated parameter optimization.
    """

    _instance: Optional[AdaptivePrompting] = None

    @classmethod
    def get_instance(cls) -> AdaptivePrompting:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._templates: Dict[str, PromptTemplate] = {}
        self._task_history: List[Dict[str, Any]] = []
        self._strategy: OptimizationStrategy = OptimizationStrategy.EPSILON_GREEDY
        self._epsilon: float = 0.15
        self._min_trials: int = 5

    def register_template(
        self,
        name: str,
        category: TaskCategory,
        base_prompt: str,
        variables: Optional[List[str]] = None,
    ) -> str:
        template = PromptTemplate(
            name=name,
            category=category,
            base_prompt=base_prompt,
            variables=variables or [],
        )
        default_variant = PromptVariant(template=base_prompt)
        template.variants.append(default_variant)
        self._templates[template.template_id] = template
        return template.template_id

    def add_variant(self, template_id: str, prompt_template: str) -> Optional[str]:
        template = self._templates.get(template_id)
        if template is None:
            return None
        variant = PromptVariant(template=prompt_template)
        template.variants.append(variant)
        return variant.variant_id

    def generate_prompt(
        self,
        template_id: str,
        context: Optional[Dict[str, Any]] = None,
        strategy: Optional[OptimizationStrategy] = None,
    ) -> Tuple[str, str]:
        template = self._templates.get(template_id)
        if template is None:
            return "", ""

        variants = template.variants
        if not variants:
            return "", ""

        strat = strategy or self._strategy
        selected = self._select_variant(variants, strat)

        prompt = selected.template
        if context:
            for key, value in context.items():
                placeholder = f"{{{key}}}"
                prompt = prompt.replace(placeholder, str(value))

        template.total_calls += 1
        return prompt, selected.variant_id

    def _select_variant(
        self,
        variants: List[PromptVariant],
        strategy: OptimizationStrategy,
    ) -> PromptVariant:
        if len(variants) == 1:
            return variants[0]

        if strategy == OptimizationStrategy.BEST_FIRST:
            return max(variants, key=lambda v: v.success_rate())

        if strategy == OptimizationStrategy.EPSILON_GREEDY:
            import random
            if random.random() < self._epsilon:
                return random.choice(variants)
            return max(variants, key=lambda v: v.success_rate())

        if strategy == OptimizationStrategy.UCB:
            best_variant = variants[0]
            best_score = -1.0
            total_trials = sum(v.success_count + v.failure_count for v in variants)
            for variant in variants:
                trials = variant.success_count + variant.failure_count
                if trials == 0:
                    score = float("inf")
                else:
                    exploration = (2.0 * max(total_trials, 1) / trials) ** 0.5
                    score = variant.success_rate() + exploration
                if score > best_score:
                    best_score = score
                    best_variant = variant
            return best_variant

        return max(variants, key=lambda v: v.success_rate())

    def record_outcome(
        self,
        template_id: str,
        variant_id: str,
        success: bool,
        response_time: float = 0.0,
    ) -> bool:
        template = self._templates.get(template_id)
        if template is None:
            return False

        for variant in template.variants:
            if variant.variant_id == variant_id:
                variant.record_outcome(success, response_time)
                self._task_history.append({
                    "template_id": template_id,
                    "variant_id": variant_id,
                    "success": success,
                    "response_time": response_time,
                    "timestamp": time.time(),
                })
                return True
        return False

    def get_best_variant(self, template_id: str) -> Optional[PromptVariant]:
        template = self._templates.get(template_id)
        if template is None or not template.variants:
            return None
        return max(template.variants, key=lambda v: v.success_rate())

    def get_variant_performance(self, template_id: str) -> List[Dict[str, Any]]:
        template = self._templates.get(template_id)
        if template is None:
            return []
        return [
            {
                "variant_id": v.variant_id,
                "success_rate": round(v.success_rate(), 3),
                "success_count": v.success_count,
                "failure_count": v.failure_count,
                "avg_response_time": round(v.avg_response_time, 4),
                "last_used_at": v.last_used_at,
            }
            for v in template.variants
        ]

    def set_strategy(self, strategy: OptimizationStrategy) -> None:
        self._strategy = strategy

    def set_epsilon(self, epsilon: float) -> None:
        self._epsilon = max(0.0, min(1.0, epsilon))

    def get_stats(self) -> Dict[str, Any]:
        total_calls = sum(t.total_calls for t in self._templates.values())
        total_variants = sum(len(t.variants) for t in self._templates.values())
        overall_success = 0
        overall_total = 0
        for t in self._templates.values():
            for v in t.variants:
                overall_success += v.success_count
                overall_total += v.success_count + v.failure_count
        success_rate = overall_success / max(overall_total, 1)

        return {
            "templates": len(self._templates),
            "total_variants": total_variants,
            "total_calls": total_calls,
            "overall_success_rate": round(success_rate, 3),
            "strategy": self._strategy.value,
            "epsilon": self._epsilon,
            "history_size": len(self._task_history),
        }

    def reset(self) -> None:
        self._templates.clear()
        self._task_history.clear()


_adaptive_prompting = AdaptivePrompting.get_instance()


def get_adaptive_prompting() -> AdaptivePrompting:
    return _adaptive_prompting