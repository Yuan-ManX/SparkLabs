"""
SparkLabs Agent - Bug Predictor

Predictive bug detection engine for AI-generated game code within
the SparkLabs AI-native game engine. Scans codebases for common
bug patterns, ranks hotspots by severity, and generates structured
mitigation plans to guide remediation efforts.

Architecture:
  BugPredictor
    |-- PatternMatcher (simulated pattern detection engine)
    |-- HotspotRanker (severity-weighted prioritization)
    |-- MitigationPlanner (step-by-step fix generation)
    |-- StatsCollector (prediction history and analytics)

Bug Categories:
  - LOGIC: control flow errors, incorrect branching
  - PERFORMANCE: frame rate bottlenecks, excessive allocation
  - SECURITY: injection vectors, unsafe operations
  - MEMORY: leaks, unbounded growth, dangling references
  - NULL_REFERENCE: unguarded access, missing null checks
  - CONCURRENCY: race conditions, deadlock potential
  - CONFIGURATION: misconfiguration, hardcoded paths
  - ASSET: corrupted resources, missing dependencies
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class BugCategory(Enum):
    LOGIC = "logic"
    PERFORMANCE = "performance"
    SECURITY = "security"
    MEMORY = "memory"
    NULL_REFERENCE = "null_reference"
    CONCURRENCY = "concurrency"
    CONFIGURATION = "configuration"
    ASSET = "asset"


class RiskLevel(Enum):
    NEGLIGIBLE = (0, "negligible")
    LOW = (1, "low")
    MEDIUM = (2, "medium")
    HIGH = (3, "high")
    CRITICAL = (4, "critical")

    def __new__(cls, score, label):
        obj = object.__new__(cls)
        obj._value_ = label
        obj.score = score
        return obj


class CodePattern(Enum):
    LOOP_NESTING = "loop_nesting"
    RECURSION = "recursion"
    STATE_MUTATION = "state_mutation"
    EVENT_HANDLING = "event_handling"
    RESOURCE_LOADING = "resource_loading"
    NETWORK_CALL = "network_call"
    FILE_IO = "file_io"


PATTERN_CATEGORY_MAP: Dict[CodePattern, BugCategory] = {
    CodePattern.LOOP_NESTING: BugCategory.PERFORMANCE,
    CodePattern.RECURSION: BugCategory.PERFORMANCE,
    CodePattern.STATE_MUTATION: BugCategory.LOGIC,
    CodePattern.EVENT_HANDLING: BugCategory.CONCURRENCY,
    CodePattern.RESOURCE_LOADING: BugCategory.ASSET,
    CodePattern.NETWORK_CALL: BugCategory.SECURITY,
    CodePattern.FILE_IO: BugCategory.CONFIGURATION,
}

CATEGORY_RISK_WEIGHTS: Dict[BugCategory, float] = {
    BugCategory.LOGIC: 1.0,
    BugCategory.PERFORMANCE: 0.8,
    BugCategory.SECURITY: 1.5,
    BugCategory.MEMORY: 1.2,
    BugCategory.NULL_REFERENCE: 1.3,
    BugCategory.CONCURRENCY: 1.4,
    BugCategory.CONFIGURATION: 0.6,
    BugCategory.ASSET: 0.5,
}

PATTERN_SIGNATURES: Dict[CodePattern, List[str]] = {
    CodePattern.LOOP_NESTING: [
        r"for\s+\w+\s+in\s+.+:\s*\n\s+for\s+\w+\s+in\s+",
        r"while\s+.+:\s*\n\s+for\s+\w+\s+in\s+",
        r"for\s+\w+\s+in\s+.+:\s*\n\s+while\s+",
    ],
    CodePattern.RECURSION: [
        r"def\s+(\w+)\(.*\)[\s\S]*?\1\(",
    ],
    CodePattern.STATE_MUTATION: [
        r"self\.\w+\s*=\s*.+\n\s*if\s+.+:\s*\n\s+self\.\w+\s*=",
        r"global\s+\w+",
        r"nonlocal\s+\w+",
    ],
    CodePattern.EVENT_HANDLING: [
        r"addEventListener|add_event_listener|on\w+\s*=\s*lambda",
        r"@event|@signal|@slot",
        r"connect\s*\(\s*self\.\w+",
    ],
    CodePattern.RESOURCE_LOADING: [
        r"load\s*\(\s*['\"]",
        r"import\s+.*\.asset|from\s+.*asset",
        r"Resources\.Load|Resources\.load|AssetDatabase",
    ],
    CodePattern.NETWORK_CALL: [
        r"urllib|requests\.(get|post|put|delete)",
        r"socket\.\w+\(",
        r"http\.\w+\(",
        r"fetch\s*\(\s*['\"]https?://",
    ],
    CodePattern.FILE_IO: [
        r"open\s*\(\s*['\"]",
        r"os\.path\.\w+",
        r"pathlib\.Path\(",
        r"file\s*=\s*open\(",
    ],
}

SECURITY_SIGNATURES: List[Tuple[str, str]] = [
    (r"\beval\s*\(", "Use of eval() permits arbitrary code execution"),
    (r"\bexec\s*\(", "Use of exec() permits arbitrary code execution"),
    (r"os\.system\s*\(", "System command execution may allow injection"),
    (r"subprocess\.\w+\(.*shell\s*=\s*True", "Shell=True in subprocess is an injection vector"),
    (r"pickle\.loads?\(", "Unpickling untrusted data is unsafe"),
    (r"__import__\s*\(.+\)", "Dynamic import may load unintended modules"),
]

MEMORY_SIGNATURES: List[Tuple[str, str]] = [
    (r"while\s+True\s*:", "Unbounded loop may cause memory exhaustion"),
    (r"\.append\(.*\)\s*$", "Unchecked list growth may leak memory"),
    (r"global\s+\w+\s*\n.*\+=", "Unbounded global accumulator detected"),
]

NULL_REFERENCE_SIGNATURES: List[Tuple[str, str]] = [
    (r"\.\w+\(\)\s*$", "Method call on potentially null reference"),
    (r"\[\s*['\"]\w+['\"]\s*\]", "Dictionary access without key existence check"),
    (r"return\s+\w+\.\w+", "Chained access without null guard"),
]


@dataclass
class CodeHotspot:
    hotspot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    file_path: str = ""
    line_range: str = ""
    risk_score: float = 0.0
    category: BugCategory = BugCategory.LOGIC
    pattern_matches: List[str] = field(default_factory=list)
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hotspot_id": self.hotspot_id,
            "file_path": self.file_path,
            "line_range": self.line_range,
            "risk_score": round(self.risk_score, 2),
            "category": self.category.value,
            "pattern_matches": self.pattern_matches[:5],
            "suggestion": self.suggestion,
        }


@dataclass
class BugPrediction:
    prediction_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    hotspot_id: str = ""
    confidence: float = 0.0
    estimated_impact: str = ""
    mitigation_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "hotspot_id": self.hotspot_id,
            "confidence": round(self.confidence, 2),
            "estimated_impact": self.estimated_impact,
            "mitigation_steps": self.mitigation_steps,
        }


@dataclass
class ScanResult:
    scan_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    total_files: int = 0
    hotspots_found: int = 0
    average_risk: float = 0.0
    scan_duration: float = 0.0
    hotspots: List[CodeHotspot] = field(default_factory=list)
    predictions: List[BugPrediction] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "total_files": self.total_files,
            "hotspots_found": self.hotspots_found,
            "average_risk": round(self.average_risk, 2),
            "scan_duration": round(self.scan_duration, 3),
            "top_hotspots": [h.to_dict() for h in self.hotspots[:10]],
            "predictions_count": len(self.predictions),
        }


class BugPredictor:
    """
    Predictive bug detection agent for game code.

    Performs simulated pattern matching across codebases to identify
    bug-prone regions, rank them by severity, and produce actionable
    mitigation plans.

    Usage:
        predictor = BugPredictor.get_instance()
        result = predictor.analyze_codebase(["game_loop.py", "player.py"])
        hotspots = predictor.predict_hotspots()
    """

    _instance: Optional[BugPredictor] = None

    def __init__(self):
        self._lock = threading.Lock()
        self._hotspots: Dict[str, CodeHotspot] = {}
        self._predictions: Dict[str, BugPrediction] = {}
        self._history: List[ScanResult] = []
        self._total_scans: int = 0
        self._total_files_scanned: int = 0

    @classmethod
    def get_instance(cls) -> BugPredictor:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def analyze_file(self, file_path: str, content: str) -> List[CodeHotspot]:
        """
        Scan a single file for bug patterns and return detected hotspots.
        """
        hotspots: List[CodeHotspot] = []
        lines = content.split("\n")

        for pattern in CodePattern:
            signatures = PATTERN_SIGNATURES.get(pattern, [])
            for sig in signatures:
                matches = list(re.finditer(sig, content, re.MULTILINE | re.DOTALL))
                for match in matches:
                    line_num = content[:match.start()].count("\n") + 1
                    category = PATTERN_CATEGORY_MAP.get(pattern, BugCategory.LOGIC)
                    weight = CATEGORY_RISK_WEIGHTS.get(category, 1.0)
                    risk_score = min(1.0, weight * 0.5 + len(matches) * 0.05)
                    suggestion = self._generate_suggestion(category, pattern)

                    hotspot = CodeHotspot(
                        file_path=file_path,
                        line_range=f"L{line_num}",
                        risk_score=round(risk_score, 2),
                        category=category,
                        pattern_matches=[match.group(0).strip()[:80]],
                        suggestion=suggestion,
                    )
                    hotspots.append(hotspot)

        hotspots.extend(self._scan_security(file_path, content))
        hotspots.extend(self._scan_memory(file_path, content))
        hotspots.extend(self._scan_null_reference(file_path, content))

        for hotspot in hotspots:
            self._hotspots[hotspot.hotspot_id] = hotspot

        return hotspots

    def analyze_codebase(self, file_paths: Dict[str, str]) -> ScanResult:
        """
        Bulk scan multiple files and produce a consolidated ScanResult.
        """
        start = time.time()
        all_hotspots: List[CodeHotspot] = []
        all_predictions: List[BugPrediction] = []

        with self._lock:
            for file_path, content in file_paths.items():
                file_hotspots = self.analyze_file(file_path, content)
                all_hotspots.extend(file_hotspots)
                for hotspot in file_hotspots:
                    prediction = self._build_prediction(hotspot)
                    all_predictions.append(prediction)
                    self._predictions[prediction.prediction_id] = prediction

            average_risk = (
                sum(h.risk_score for h in all_hotspots) / max(1, len(all_hotspots))
            )

            result = ScanResult(
                total_files=len(file_paths),
                hotspots_found=len(all_hotspots),
                average_risk=round(average_risk, 2),
                scan_duration=round(time.time() - start, 3),
                hotspots=all_hotspots,
                predictions=all_predictions,
            )

            self._history.append(result)
            self._total_scans += 1
            self._total_files_scanned += len(file_paths)

            if len(self._history) > 100:
                self._history = self._history[-100:]

            return result

    def predict_hotspots(self, min_score: float = 0.3) -> List[CodeHotspot]:
        """
        Return ranked list of high-risk areas exceeding the minimum score threshold.
        """
        with self._lock:
            filtered = [h for h in self._hotspots.values() if h.risk_score >= min_score]
            return sorted(filtered, key=lambda h: h.risk_score, reverse=True)

    def rank_risks(self) -> List[CodeHotspot]:
        """
        Sort all known hotspots by severity and confidence, highest first.
        """
        with self._lock:
            ranked = sorted(
                self._hotspots.values(),
                key=lambda h: (CATEGORY_RISK_WEIGHTS.get(h.category, 1.0) * h.risk_score),
                reverse=True,
            )
            return ranked

    def generate_mitigation_plan(self, hotspot_id: str) -> Optional[BugPrediction]:
        """
        Produce a step-by-step fix suggestion for a given hotspot.
        """
        with self._lock:
            if hotspot_id in self._predictions:
                return self._predictions[hotspot_id]

            hotspot = self._hotspots.get(hotspot_id)
            if hotspot is None:
                return None

            prediction = self._build_prediction(hotspot)
            self._predictions[prediction.prediction_id] = prediction
            return prediction

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Return past scan results as dictionaries.
        """
        with self._lock:
            return [r.to_dict() for r in self._history[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        """
        Return prediction statistics including scan counts and category breakdowns.
        """
        with self._lock:
            category_counts: Dict[str, int] = {}
            for hotspot in self._hotspots.values():
                cat = hotspot.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1

            avg_risk = (
                sum(h.risk_score for h in self._hotspots.values()) / max(1, len(self._hotspots))
            )

            return {
                "total_scans": self._total_scans,
                "total_files_scanned": self._total_files_scanned,
                "total_hotspots": len(self._hotspots),
                "total_predictions": len(self._predictions),
                "average_risk_score": round(avg_risk, 2),
                "category_breakdown": category_counts,
                "cached_results": len(self._history),
            }

    def _scan_security(self, file_path: str, content: str) -> List[CodeHotspot]:
        hotspots: List[CodeHotspot] = []
        for sig, description in SECURITY_SIGNATURES:
            for match in re.finditer(sig, content, re.MULTILINE):
                line_num = content[:match.start()].count("\n") + 1
                hotspots.append(CodeHotspot(
                    file_path=file_path,
                    line_range=f"L{line_num}",
                    risk_score=round(min(1.0, 1.5 * 0.5), 2),
                    category=BugCategory.SECURITY,
                    pattern_matches=[match.group(0).strip()[:80]],
                    suggestion=description,
                ))
        return hotspots

    def _scan_memory(self, file_path: str, content: str) -> List[CodeHotspot]:
        hotspots: List[CodeHotspot] = []
        for sig, description in MEMORY_SIGNATURES:
            for match in re.finditer(sig, content, re.MULTILINE):
                line_num = content[:match.start()].count("\n") + 1
                hotspots.append(CodeHotspot(
                    file_path=file_path,
                    line_range=f"L{line_num}",
                    risk_score=round(min(1.0, 1.2 * 0.5), 2),
                    category=BugCategory.MEMORY,
                    pattern_matches=[match.group(0).strip()[:80]],
                    suggestion=description,
                ))
        return hotspots

    def _scan_null_reference(self, file_path: str, content: str) -> List[CodeHotspot]:
        hotspots: List[CodeHotspot] = []
        for sig, description in NULL_REFERENCE_SIGNATURES:
            for match in re.finditer(sig, content, re.MULTILINE):
                line_num = content[:match.start()].count("\n") + 1
                hotspots.append(CodeHotspot(
                    file_path=file_path,
                    line_range=f"L{line_num}",
                    risk_score=round(min(1.0, 1.3 * 0.4), 2),
                    category=BugCategory.NULL_REFERENCE,
                    pattern_matches=[match.group(0).strip()[:80]],
                    suggestion=description,
                ))
        return hotspots

    def _generate_suggestion(self, category: BugCategory, pattern: CodePattern) -> str:
        suggestions = {
            (BugCategory.PERFORMANCE, CodePattern.LOOP_NESTING): (
                "Flatten nested loops or use early-exit conditions to reduce iteration complexity"
            ),
            (BugCategory.PERFORMANCE, CodePattern.RECURSION): (
                "Replace recursion with iterative approach or enforce a depth limit"
            ),
            (BugCategory.LOGIC, CodePattern.STATE_MUTATION): (
                "Encapsulate state transitions in dedicated methods to avoid scattered mutations"
            ),
            (BugCategory.CONCURRENCY, CodePattern.EVENT_HANDLING): (
                "Ensure event handlers are thread-safe and avoid blocking the main thread"
            ),
            (BugCategory.ASSET, CodePattern.RESOURCE_LOADING): (
                "Verify asset paths and implement async loading with fallback handling"
            ),
            (BugCategory.SECURITY, CodePattern.NETWORK_CALL): (
                "Validate all network inputs, use HTTPS, and implement request timeouts"
            ),
            (BugCategory.CONFIGURATION, CodePattern.FILE_IO): (
                "Use configuration management instead of hardcoded file paths"
            ),
        }
        return suggestions.get((category, pattern), f"Review {pattern.value} pattern in context of {category.value}")

    def _build_prediction(self, hotspot: CodeHotspot) -> BugPrediction:
        confidence = min(0.95, hotspot.risk_score * 0.8 + 0.1)

        impact_descriptions = {
            BugCategory.LOGIC: "May cause incorrect game state transitions",
            BugCategory.PERFORMANCE: "Likely to introduce frame rate drops under load",
            BugCategory.SECURITY: "Potential attack surface for code injection",
            BugCategory.MEMORY: "Risk of gradual memory exhaustion over extended play",
            BugCategory.NULL_REFERENCE: "May trigger crashes when references are unset",
            BugCategory.CONCURRENCY: "Could produce race conditions in multiplayer scenarios",
            BugCategory.CONFIGURATION: "May fail on different deployment environments",
            BugCategory.ASSET: "Can result in missing textures or silent load failures",
        }

        mitigation_steps = [
            f"Locate the affected code at {hotspot.file_path}:{hotspot.line_range}",
            f"Analyze the {hotspot.category.value} pattern: {', '.join(hotspot.pattern_matches[:2])}",
            f"Apply fix: {hotspot.suggestion}",
            "Add unit tests covering the patched code path",
            "Run regression tests to verify no side effects",
        ]

        return BugPrediction(
            hotspot_id=hotspot.hotspot_id,
            confidence=round(confidence, 2),
            estimated_impact=impact_descriptions.get(hotspot.category, "Unknown impact"),
            mitigation_steps=mitigation_steps,
        )


def get_bug_predictor() -> BugPredictor:
    return BugPredictor.get_instance()