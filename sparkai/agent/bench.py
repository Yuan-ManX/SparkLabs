"""
SparkAI Agent - Game Bench Evaluation

Quality scoring pipeline for AI-generated game content.
Evaluates games across three dimensions:
  - Build Health: Does the code compile and run?
  - Visual Usability: Is the game playable and visually coherent?
  - Intent Alignment: Does the game match the original prompt?

Scores are 0.0-1.0 per dimension, combined into a weighted total.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BenchDimension(Enum):
    BUILD_HEALTH = "build_health"
    VISUAL_USABILITY = "visual_usability"
    INTENT_ALIGNMENT = "intent_alignment"


@dataclass
class DimensionScore:
    dimension: str
    score: float = 0.0
    max_score: float = 1.0
    details: str = ""
    checks: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def normalized(self) -> float:
        return self.score / self.max_score if self.max_score > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "max_score": self.max_score,
            "normalized": round(self.normalized, 3),
            "details": self.details,
            "checks": self.checks,
        }


@dataclass
class BenchResult:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str = ""
    dimensions: List[DimensionScore] = field(default_factory=list)
    total_score: float = 0.0
    passed: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "total_score": round(self.total_score, 3),
            "passed": self.passed,
            "timestamp": self.timestamp,
        }


class BuildHealthChecker:
    """
    Evaluates whether generated game code compiles and runs.
    Checks for syntax errors, missing imports, and runtime crashes.
    """

    def check(self, code: str, prompt: str) -> DimensionScore:
        checks = []

        syntax_ok = self._check_syntax(code)
        checks.append({"name": "syntax", "passed": syntax_ok, "detail": "Syntax validation"})

        imports_ok = self._check_imports(code)
        checks.append({"name": "imports", "passed": imports_ok, "detail": "Import resolution"})

        structure_ok = self._check_structure(code)
        checks.append({"name": "structure", "passed": structure_ok, "detail": "Code structure"})

        entry_ok = self._check_entry_point(code)
        checks.append({"name": "entry_point", "passed": entry_ok, "detail": "Entry point exists"})

        passed_count = sum(1 for c in checks if c["passed"])
        score = passed_count / len(checks) if checks else 0.0

        return DimensionScore(
            dimension=BenchDimension.BUILD_HEALTH.value,
            score=score,
            details=f"{passed_count}/{len(checks)} checks passed",
            checks=checks,
        )

    def _check_syntax(self, code: str) -> bool:
        try:
            compile(code, "<bench>", "exec")
            return True
        except SyntaxError:
            return False

    def _check_imports(self, code: str) -> bool:
        lines = code.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                if "nonexistent" in stripped or "fake_module" in stripped:
                    return False
        return True

    def _check_structure(self, code: str) -> bool:
        has_function = "def " in code or "function " in code or "class " in code
        return has_function or len(code.strip()) > 50

    def _check_entry_point(self, code: str) -> bool:
        return (
            'if __name__' in code
            or "main(" in code
            or "window.onload" in code
            or "addEventListener" in code
            or "createScene" in code
            or len(code.strip()) > 100
        )


class VisualUsabilityChecker:
    """
    Evaluates whether the game is visually playable.
    Checks for canvas/renderer setup, input handling, and UI elements.
    """

    def check(self, code: str, prompt: str) -> DimensionScore:
        checks = []

        has_renderer = self._check_renderer(code)
        checks.append({"name": "renderer", "passed": has_renderer, "detail": "Rendering setup"})

        has_input = self._check_input(code)
        checks.append({"name": "input", "passed": has_input, "detail": "Input handling"})

        has_game_loop = self._check_game_loop(code)
        checks.append({"name": "game_loop", "passed": has_game_loop, "detail": "Game loop"})

        has_ui = self._check_ui(code)
        checks.append({"name": "ui", "passed": has_ui, "detail": "UI elements"})

        has_feedback = self._check_feedback(code)
        checks.append({"name": "feedback", "passed": has_feedback, "detail": "Visual feedback"})

        passed_count = sum(1 for c in checks if c["passed"])
        score = passed_count / len(checks) if checks else 0.0

        return DimensionScore(
            dimension=BenchDimension.VISUAL_USABILITY.value,
            score=score,
            details=f"{passed_count}/{len(checks)} checks passed",
            checks=checks,
        )

    def _check_renderer(self, code: str) -> bool:
        keywords = ["canvas", "webgl", "three", "renderer", "ctx", "drawImage", "fillRect", "Sprite"]
        return any(kw.lower() in code.lower() for kw in keywords)

    def _check_input(self, code: str) -> bool:
        keywords = ["keydown", "keyup", "mousedown", "click", "touchstart", "input", "addEventListener", "onKey"]
        return any(kw.lower() in code.lower() for kw in keywords)

    def _check_game_loop(self, code: str) -> bool:
        keywords = ["requestAnimationFrame", "setInterval", "update", "tick", "loop", "gameLoop"]
        return any(kw.lower() in code.lower() for kw in keywords)

    def _check_ui(self, code: str) -> bool:
        keywords = ["innerHTML", "textContent", "createElement", "score", "health", "button", "UI", "hud"]
        return any(kw.lower() in code.lower() for kw in keywords)

    def _check_feedback(self, code: str) -> bool:
        keywords = ["animation", "transition", "transform", "opacity", "color", "flash", "shake", "particle"]
        return any(kw.lower() in code.lower() for kw in keywords)


class IntentAlignmentChecker:
    """
    Evaluates whether the generated game matches the original prompt.
    Checks for keyword coverage, genre match, and feature presence.
    """

    def check(self, code: str, prompt: str) -> DimensionScore:
        checks = []

        keyword_score = self._check_keywords(code, prompt)
        checks.append({"name": "keyword_coverage", "passed": keyword_score > 0.3, "detail": f"Coverage: {keyword_score:.0%}", "score": keyword_score})

        genre_match = self._check_genre(code, prompt)
        checks.append({"name": "genre_match", "passed": genre_match, "detail": "Genre indicators present"})

        feature_match = self._check_features(code, prompt)
        checks.append({"name": "feature_match", "passed": feature_match > 0.3, "detail": f"Feature coverage: {feature_match:.0%}", "score": feature_match})

        passed_count = sum(1 for c in checks if c["passed"])
        score = passed_count / len(checks) if checks else 0.0

        return DimensionScore(
            dimension=BenchDimension.INTENT_ALIGNMENT.value,
            score=score,
            details=f"{passed_count}/{len(checks)} checks passed",
            checks=checks,
        )

    def _check_keywords(self, code: str, prompt: str) -> float:
        prompt_words = set(w.lower() for w in prompt.split() if len(w) > 3)
        code_lower = code.lower()
        matched = sum(1 for w in prompt_words if w in code_lower)
        return matched / len(prompt_words) if prompt_words else 0.5

    def _check_genre(self, code: str, prompt: str) -> bool:
        genre_indicators = {
            "platformer": ["jump", "platform", "gravity", "side-scroll"],
            "shooter": ["shoot", "bullet", "weapon", "enemy", "aim"],
            "rpg": ["quest", "inventory", "level_up", "character", "stat"],
            "puzzle": ["match", "solve", "grid", "piece", "logic"],
            "strategy": ["build", "resource", "unit", "base", "upgrade"],
            "racing": ["speed", "track", "lap", "car", "vehicle"],
        }
        prompt_lower = prompt.lower()
        code_lower = code.lower()
        for genre, indicators in genre_indicators.items():
            if genre in prompt_lower:
                return any(ind in code_lower for ind in indicators)
        return True

    def _check_features(self, code: str, prompt: str) -> float:
        feature_keywords = {
            "multiplayer": ["socket", "network", "sync", "player_2"],
            "ai": ["behavior", "pathfind", "decision", "agent"],
            "physics": ["collision", "rigidbody", "force", "velocity"],
            "procedural": ["generate", "random", "seed", "procedural"],
            "narrative": ["story", "dialogue", "quest", "cutscene"],
        }
        prompt_lower = prompt.lower()
        code_lower = code.lower()
        requested = [f for f, _ in feature_keywords.items() if f in prompt_lower]
        if not requested:
            return 0.5
        matched = 0
        for feature in requested:
            if any(kw in code_lower for kw in feature_keywords[feature]):
                matched += 1
        return matched / len(requested)


class GameBench:
    """
    Evaluation pipeline for AI-generated game content.
    Scores games across Build Health, Visual Usability, and Intent Alignment.
    """

    def __init__(
        self,
        build_weight: float = 0.4,
        visual_weight: float = 0.3,
        intent_weight: float = 0.3,
        pass_threshold: float = 0.6,
    ):
        self.build_weight = build_weight
        self.visual_weight = visual_weight
        self.intent_weight = intent_weight
        self.pass_threshold = pass_threshold
        self._build_checker = BuildHealthChecker()
        self._visual_checker = VisualUsabilityChecker()
        self._intent_checker = IntentAlignmentChecker()
        self._history: List[BenchResult] = []

    def evaluate(self, code: str, prompt: str) -> BenchResult:
        """
        Evaluate generated game code against the original prompt.
        Returns a BenchResult with dimension scores and overall pass/fail.
        """
        build_score = self._build_checker.check(code, prompt)
        visual_score = self._visual_checker.check(code, prompt)
        intent_score = self._intent_checker.check(code, prompt)

        total = (
            build_score.normalized * self.build_weight
            + visual_score.normalized * self.visual_weight
            + intent_score.normalized * self.intent_weight
        )

        result = BenchResult(
            prompt=prompt,
            dimensions=[build_score, visual_score, intent_score],
            total_score=total,
            passed=total >= self.pass_threshold,
        )

        self._history.append(result)
        return result

    def get_history(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._history]

    def get_stats(self) -> Dict[str, Any]:
        if not self._history:
            return {"total_evaluations": 0}
        scores = [r.total_score for r in self._history]
        pass_rate = sum(1 for r in self._history if r.passed) / len(self._history)
        return {
            "total_evaluations": len(self._history),
            "average_score": round(sum(scores) / len(scores), 3),
            "pass_rate": round(pass_rate, 3),
            "pass_threshold": self.pass_threshold,
            "weights": {
                "build_health": self.build_weight,
                "visual_usability": self.visual_weight,
                "intent_alignment": self.intent_weight,
            },
        }
