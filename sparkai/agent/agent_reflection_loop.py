"""
SparkLabs Agent - Reflection and Self-Correction Loop

A structured reflection mechanism that enables agents to analyze their own
actions, detect errors, and propose revisions. Each agent action is captured
as a reflection entry with before/after confidence scores. Sessions aggregate
reflection entries and track confidence trends over multiple iterations.
The system learns from completed sessions by extracting recurring error
patterns into a shared knowledge base for future pattern matching.

Architecture:
  ReflectionLoop
    |-- ReflectionEntry (single action-reflection pair)
    |-- ErrorPattern (recurring issue with severity and fix)
    |-- ReflectionSession (ordered sequence of entries per task)
    |-- ReflectionDomain (game development domain enumeration)
    |-- ConfidenceLevel (discrete confidence bands)
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ReflectionDomain(Enum):
    CODE_GENERATION = "code_generation"
    GAME_DESIGN = "game_design"
    ASSET_CREATION = "asset_creation"
    LEVEL_BUILDING = "level_building"
    NARRATIVE = "narrative"
    BALANCING = "balancing"
    PERFORMANCE = "performance"
    TESTING = "testing"


class ConfidenceLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


_SEED_ERROR_PATTERNS: List[Dict[str, Any]] = [
    {
        "pattern_name": "Missing Collision Detection",
        "description": "Game objects pass through each other without triggering collision events. "
                       "Commonly caused by missing collider components, disabled collision layers, "
                       "or improperly configured physics settings.",
        "domain": "game_design",
        "typical_fix": "Add appropriate collider components to all interactive objects and verify "
                       "collision layer masks are configured correctly.",
        "severity": ErrorSeverity.HIGH.value,
    },
    {
        "pattern_name": "Unbalanced Game Mechanics",
        "description": "Player abilities, enemy stats, resource generation rates, or progression "
                       "curves create an unfair or unfun experience. Indicators include win/loss "
                       "ratios far from 50% or player complaints about difficulty spikes.",
        "domain": "balancing",
        "typical_fix": "Review numerical tuning parameters and apply scaling curves. Run playtest "
                       "simulations to verify balance across different player skill levels.",
        "severity": ErrorSeverity.HIGH.value,
    },
    {
        "pattern_name": "Poor Asset Optimization",
        "description": "Textures, models, or audio files consume excessive memory or cause long "
                       "load times. May manifest as frame rate drops when assets enter the viewport "
                       "or stuttering during asset streaming.",
        "domain": "asset_creation",
        "typical_fix": "Compress textures to appropriate formats, reduce polygon counts with LOD "
                       "systems, and use asset bundling with async loading.",
        "severity": ErrorSeverity.MEDIUM.value,
    },
    {
        "pattern_name": "Incomplete Narrative Arcs",
        "description": "Storylines lack closure, character motivations are inconsistent, or quest "
                       "chains are disconnected. Players report confusion about objectives or "
                       "story continuity.",
        "domain": "narrative",
        "typical_fix": "Map out the complete narrative graph with entry, progression, and exit "
                       "conditions for every story node. Verify all branches have valid endings.",
        "severity": ErrorSeverity.MEDIUM.value,
    },
    {
        "pattern_name": "Performance Bottlenecks",
        "description": "Frame rate drops below target, high CPU or GPU utilization, or excessive "
                       "garbage collection pauses. Often caused by unbatched draw calls, expensive "
                       "per-frame computations, or memory allocation in hot paths.",
        "domain": "performance",
        "typical_fix": "Profile the application to identify hot paths. Use object pooling, draw "
                       "call batching, and spatial partitioning to reduce per-frame work.",
        "severity": ErrorSeverity.CRITICAL.value,
    },
    {
        "pattern_name": "UI Consistency Issues",
        "description": "User interface elements have inconsistent sizing, spacing, font usage, or "
                       "color schemes across different screens. Navigation flows differ between "
                       "similar menu types.",
        "domain": "game_design",
        "typical_fix": "Establish a UI style guide with standardized component sizes, spacing "
                       "tokens, and color palette. Apply the theme system consistently.",
        "severity": ErrorSeverity.LOW.value,
    },
    {
        "pattern_name": "Memory Leaks in Loops",
        "description": "Objects are created repeatedly inside update loops without being freed, "
                       "causing gradual memory growth. Common in game logic that spawns temporary "
                       "objects each frame without recycling.",
        "domain": "code_generation",
        "typical_fix": "Move allocations outside the hot loop or use object pools. Verify that "
                       "all dynamically created objects have corresponding deallocation paths.",
        "severity": ErrorSeverity.CRITICAL.value,
    },
    {
        "pattern_name": "State Management Bugs",
        "description": "Game state transitions are unreliable, causing entities to be in wrong "
                       "states, UI to display stale data, or save files to become corrupted. "
                       "Often stems from race conditions or missing state validation.",
        "domain": "code_generation",
        "typical_fix": "Implement a centralized state machine with explicit transition rules and "
                       "validation guards. Add state snapshots for debugging and rollback.",
        "severity": ErrorSeverity.HIGH.value,
    },
]


@dataclass
class ReflectionEntry:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    step_number: int = 0
    action: str = ""
    observation: str = ""
    critique: str = ""
    revision: str = ""
    confidence_before: float = 0.5
    confidence_after: float = 0.5
    domain: ReflectionDomain = ReflectionDomain.CODE_GENERATION
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        self.confidence_before = max(0.0, min(1.0, self.confidence_before))
        self.confidence_after = max(0.0, min(1.0, self.confidence_after))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "step_number": self.step_number,
            "action": self.action[:200],
            "observation": self.observation[:200],
            "critique": self.critique[:200],
            "revision": self.revision[:200],
            "confidence_before": self.confidence_before,
            "confidence_after": self.confidence_after,
            "domain": self.domain.value,
            "created_at": self.created_at,
        }


@dataclass
class ErrorPattern:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pattern_name: str = ""
    description: str = ""
    domain: str = ""
    occurrence_count: int = 0
    last_seen: float = field(default_factory=time.time)
    typical_fix: str = ""
    severity: str = ErrorSeverity.MEDIUM.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pattern_name": self.pattern_name,
            "description": self.description[:200],
            "domain": self.domain,
            "occurrence_count": self.occurrence_count,
            "last_seen": self.last_seen,
            "typical_fix": self.typical_fix[:200],
            "severity": self.severity,
        }


@dataclass
class ReflectionSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_description: str = ""
    domain: ReflectionDomain = ReflectionDomain.CODE_GENERATION
    entries: List[ReflectionEntry] = field(default_factory=list)
    current_step: int = 0
    max_iterations: int = 5
    confidence_trend: List[float] = field(default_factory=list)
    is_complete: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_description": self.task_description[:200],
            "domain": self.domain.value,
            "entry_count": len(self.entries),
            "current_step": self.current_step,
            "max_iterations": self.max_iterations,
            "confidence_trend": [round(v, 3) for v in self.confidence_trend[-10:]],
            "is_complete": self.is_complete,
        }


class ReflectionLoop:
    """
    Reflection and self-correction loop that captures agent actions, analyzes
    observations for issues, proposes revisions, and tracks confidence over
    multiple iterations. Completed sessions are mined for recurring error
    patterns that populate a shared pattern database for future matching.
    """

    _instance: Optional["ReflectionLoop"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_ENTRIES_PER_SESSION = 50
    CONFIDENCE_IMPROVEMENT_THRESHOLD = 0.02
    PATTERN_MATCH_SIMILARITY = 0.15

    def __init__(self):
        self._sessions: Dict[str, ReflectionSession] = {}
        self._error_patterns: Dict[str, ErrorPattern] = {}
        self._entry_count: int = 0
        self._session_count: int = 0
        self._pattern_count: int = 0
        self._seed_error_patterns()

    @classmethod
    def get_instance(cls) -> "ReflectionLoop":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed_error_patterns(self) -> None:
        for seed in _SEED_ERROR_PATTERNS:
            pattern = ErrorPattern(
                pattern_name=seed["pattern_name"],
                description=seed["description"],
                domain=seed["domain"],
                occurrence_count=0,
                typical_fix=seed["typical_fix"],
                severity=seed["severity"],
            )
            self._error_patterns[pattern.id] = pattern
        self._pattern_count = len(self._error_patterns)

    def start_session(
        self,
        task_description: str,
        domain: ReflectionDomain,
        max_iterations: int = 5,
    ) -> ReflectionSession:
        with self._lock:
            session = ReflectionSession(
                task_description=task_description,
                domain=domain,
                max_iterations=max(max_iterations, 1),
            )
            self._sessions[session.id] = session
            self._session_count += 1
            return session

    def reflect(
        self,
        session_id: str,
        action: str,
        observation: str,
        confidence_before: float,
    ) -> Optional[ReflectionEntry]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.is_complete:
                return None
            if len(session.entries) >= self.MAX_ENTRIES_PER_SESSION:
                session.is_complete = True
                return None

            criticism = self.generate_critique(observation)
            fix = self.propose_revision(session_id, criticism)
            new_confidence = self._compute_confidence_after(
                confidence_before, observation
            )

            entry = ReflectionEntry(
                session_id=session_id,
                step_number=session.current_step + 1,
                action=action,
                observation=observation,
                critique=criticism,
                revision=fix,
                confidence_before=confidence_before,
                confidence_after=new_confidence,
                domain=session.domain,
            )

            session.entries.append(entry)
            session.current_step += 1
            session.confidence_trend.append(new_confidence)
            self._entry_count += 1

            return entry

    def generate_critique(self, observation: str) -> str:
        observation_lower = observation.lower()
        detected_pattern = self.match_error_pattern(observation)

        if detected_pattern:
            return (
                f"Pattern matched: {detected_pattern.pattern_name}. "
                f"{detected_pattern.description} "
                f"Suggested fix: {detected_pattern.typical_fix}"
            )

        issues: List[str] = []

        if any(word in observation_lower for word in ["error", "fail", "crash", "exception"]):
            issues.append("Execution produced an error or failure condition.")

        if any(word in observation_lower for word in ["slow", "lag", "stutter", "low fps", "performance"]):
            issues.append("Performance degradation detected; frame budget may be exceeded.")

        if any(word in observation_lower for word in ["missing", "not found", "none", "empty"]):
            issues.append("Expected resource or data is missing or unavailable.")

        if any(word in observation_lower for word in ["incorrect", "wrong", "unexpected", "invalid"]):
            issues.append("Output does not match expected behavior or specification.")

        if any(word in observation_lower for word in ["incomplete", "partial", "unfinished"]):
            issues.append("Result is incomplete; additional work required.")

        if not issues:
            return "No significant issues detected. Action appears to have succeeded."

        return " | ".join(issues)

    def propose_revision(self, session_id: str, critique: str) -> str:
        session = self._sessions.get(session_id)
        if session is None:
            return "No active session found."

        if "No significant issues detected" in critique:
            return "Continue with current approach. No revision needed."

        parts: List[str] = ["Revision plan:"]

        if "error" in critique.lower() or "fail" in critique.lower():
            parts.append("Investigate error source and add error handling or validation guards.")

        if "performance" in critique.lower() or "slow" in critique.lower():
            parts.append("Profile the relevant code path and apply targeted optimizations.")

        if "missing" in critique.lower() or "not found" in critique.lower():
            parts.append("Verify resource references and ensure all dependencies are available.")

        if "incorrect" in critique.lower() or "wrong" in critique.lower():
            parts.append("Cross-check output against the specification and correct the logic.")

        if "incomplete" in critique.lower():
            parts.append("Identify remaining work items and schedule them for the next iteration.")

        if "pattern matched" in critique.lower():
            detected = self.match_error_pattern(
                session.entries[-1].observation if session.entries else ""
            )
            if detected:
                parts.append(f"Apply known fix for pattern '{detected.pattern_name}': {detected.typical_fix}")

        return " ".join(parts) if len(parts) > 1 else "Monitor and re-evaluate on next step."

    def should_continue(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        if session.is_complete:
            return False
        if session.current_step >= session.max_iterations:
            session.is_complete = True
            return False

        trend = session.confidence_trend
        if len(trend) >= 3:
            recent = trend[-3:]
            if recent[0] >= 0.95 and recent[-1] >= recent[0]:
                session.is_complete = True
                return False
            if len(trend) >= 4:
                last_four = trend[-4:]
                if all(
                    abs(last_four[i + 1] - last_four[i]) < self.CONFIDENCE_IMPROVEMENT_THRESHOLD
                    for i in range(len(last_four) - 1)
                ):
                    if last_four[-1] >= 0.7:
                        session.is_complete = True
                        return False
                    if last_four[-1] < 0.3:
                        session.is_complete = True
                        return False

        return True

    def learn_from_session(self, session_id: str) -> List[ErrorPattern]:
        session = self._sessions.get(session_id)
        if session is None or not session.is_complete:
            return []

        learned: List[ErrorPattern] = []

        for entry in session.entries:
            if entry.confidence_before > entry.confidence_after + 0.1:
                lowered = entry.observation.lower()
                if any(
                    w in lowered
                    for w in ["error", "fail", "bug", "crash", "broken", "incorrect"]
                ):
                    existing = self.match_error_pattern(entry.observation)
                    if existing:
                        existing.occurrence_count += 1
                        existing.last_seen = time.time()
                        learned.append(existing)
                    else:
                        name = self._derive_pattern_name(entry.observation)
                        pattern = ErrorPattern(
                            pattern_name=name,
                            description=entry.observation[:300],
                            domain=session.domain.value,
                            occurrence_count=1,
                            typical_fix=entry.revision[:300],
                            severity=ErrorSeverity.MEDIUM.value,
                        )
                        self._error_patterns[pattern.id] = pattern
                        self._pattern_count += 1
                        learned.append(pattern)

        return learned

    def match_error_pattern(self, observation: str) -> Optional[ErrorPattern]:
        if not observation:
            return None

        observation_lower = observation.lower()
        best_match: Optional[ErrorPattern] = None
        best_score: float = 0.0

        for pattern in self._error_patterns.values():
            score = self._similarity_score(observation_lower, pattern)
            if score > best_score:
                best_score = score
                best_match = pattern

        if best_match and best_score >= self.PATTERN_MATCH_SIMILARITY:
            return best_match
        return None

    def _similarity_score(self, text: str, pattern: ErrorPattern) -> float:
        tokenize = lambda s: set(re.findall(r"[a-zA-Z0-9]+", s.lower()))
        tokens = tokenize(text)
        pattern_text = f"{pattern.pattern_name} {pattern.description}"
        pattern_tokens = tokenize(pattern_text)

        if not pattern_tokens:
            return 0.0

        overlap = tokens & pattern_tokens
        return len(overlap) / len(pattern_tokens)

    def _derive_pattern_name(self, observation: str) -> str:
        lower = observation.lower()
        if "memory" in lower and ("leak" in lower or "grow" in lower):
            return "Memory Leak Detected"
        if "state" in lower and ("bug" in lower or "corrupt" in lower or "invalid" in lower):
            return "State Corruption Issue"
        if "performance" in lower or "slow" in lower or "fps" in lower:
            return "Performance Regression"
        if "collision" in lower and ("miss" in lower or "fail" in lower):
            return "Collision Failure"
        if "narrative" in lower or "story" in lower:
            return "Narrative Issue"
        if "balance" in lower or "difficulty" in lower:
            return "Balancing Issue"
        if "asset" in lower or "texture" in lower or "model" in lower:
            return "Asset Pipeline Issue"
        return "Unknown Error Pattern"

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            return {"error": "Session not found"}

        trend = session.confidence_trend
        start_confidence = trend[0] if trend else 0.0
        end_confidence = trend[-1] if trend else 0.0

        key_findings: List[str] = []
        for entry in session.entries:
            if abs(entry.confidence_after - entry.confidence_before) > 0.15:
                direction = "up" if entry.confidence_after > entry.confidence_before else "down"
                key_findings.append(
                    f"Step {entry.step_number}: confidence {direction} "
                    f"({entry.confidence_before:.2f} -> {entry.confidence_after:.2f})"
                )

        return {
            "session_id": session.id,
            "task": session.task_description[:200],
            "domain": session.domain.value,
            "start_confidence": round(start_confidence, 3),
            "end_confidence": round(end_confidence, 3),
            "iterations": session.current_step,
            "max_iterations": session.max_iterations,
            "is_complete": session.is_complete,
            "key_findings": key_findings[:5],
            "entry_count": len(session.entries),
        }

    def calibrate_confidence(self, session_id: str) -> float:
        session = self._sessions.get(session_id)
        if session is None:
            return 0.0

        trend = session.confidence_trend
        if not trend:
            return 0.5

        recent = trend[-3:]
        avg_recent = sum(recent) / len(recent)

        if len(trend) >= 3:
            slope = (trend[-1] - trend[0]) / max(len(trend) - 1, 1)
            if slope > 0.05:
                return min(1.0, avg_recent + 0.05)
            elif slope < -0.05:
                return max(0.0, avg_recent - 0.05)

        return round(avg_recent, 3)

    def reset_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.entries.clear()
        session.confidence_trend.clear()
        session.current_step = 0
        session.is_complete = False
        return True

    def get_stats(self) -> Dict[str, Any]:
        domain_breakdown: Dict[str, int] = {}
        for session in self._sessions.values():
            d = session.domain.value
            domain_breakdown[d] = domain_breakdown.get(d, 0) + 1

        return {
            "session_count": self._session_count,
            "entry_count": self._entry_count,
            "pattern_count": self._pattern_count,
            "domain_breakdown": domain_breakdown,
        }

    def _compute_confidence_after(
        self, confidence_before: float, observation: str
    ) -> float:
        observation_lower = observation.lower()
        adjustment = 0.0

        error_words = ["error", "fail", "crash", "exception", "broken"]
        success_words = ["success", "pass", "complete", "correct", "working", "good"]

        error_count = sum(1 for w in error_words if w in observation_lower)
        success_count = sum(1 for w in success_words if w in observation_lower)

        if error_count > 0:
            adjustment = -0.1 - (error_count - 1) * 0.05
        elif success_count > 0:
            adjustment = 0.05 + (success_count - 1) * 0.02
        else:
            adjustment = -0.03

        return max(0.0, min(1.0, confidence_before + adjustment))


def get_reflection_loop() -> ReflectionLoop:
    return ReflectionLoop.get_instance()