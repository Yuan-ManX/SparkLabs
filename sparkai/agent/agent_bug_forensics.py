"""
SparkLabs Agent - Bug Forensics Engine

AI-driven crash log analysis and fix suggestion system for game engine
issues. Analyzes stack traces, classifies error patterns, reproduces
failure scenarios, and generates targeted fix recommendations.

Architecture:
  BugForensics (singleton)
    |-- Crash ingestion and classification
    |-- Pattern-based error categorization
    |-- Root cause analysis via stack trace decomposition
    |-- Reproduction step synthesis
    |-- Fix suggestion generation
    |-- Cross-report relationship mapping

Workflow:
  1. submit_crash() - ingest a crash report
  2. analyze_crash() - classify error, identify root cause
  3. suggest_fix() - generate fix recommendation
  4. find_related_issues() - discover related crash reports
"""

from __future__ import annotations

import re
import threading
import uuid

_time_module = __import__("time")

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------


class BugSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    COSMETIC = "cosmetic"


class ErrorCategory(Enum):
    NULL_POINTER = "null_pointer"
    MEMORY_LEAK = "memory_leak"
    RACE_CONDITION = "race_condition"
    INFINITE_LOOP = "infinite_loop"
    ASSERTION_FAILURE = "assertion_failure"
    RENDER_ERROR = "render_error"
    NETWORK_TIMEOUT = "network_timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    UNKNOWN = "unknown"


class FixConfidence(Enum):
    DEFINITE = "definite"
    HIGH = "high"
    MODERATE = "moderate"
    TENTATIVE = "tentative"
    SPECULATIVE = "speculative"


class ForensicsStatus(Enum):
    NEW = "new"
    ANALYZING = "analyzing"
    TRIAGED = "triaged"
    FIX_SUGGESTED = "fix_suggested"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class CrashReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    title: str = ""
    stack_trace: str = ""
    error_category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: BugSeverity = BugSeverity.MEDIUM
    game_state: Dict[str, Any] = field(default_factory=dict)
    player_actions: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=_time_module.time)
    status: ForensicsStatus = ForensicsStatus.NEW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "stack_trace": self.stack_trace[:500],
            "error_category": self.error_category.value,
            "severity": self.severity.value,
            "game_state": self.game_state,
            "player_actions": self.player_actions,
            "timestamp": self.timestamp,
            "status": self.status.value,
        }


@dataclass
class ForensicsAnalysis:
    report_id: str = ""
    root_cause: str = ""
    affected_components: List[str] = field(default_factory=list)
    reproduction_steps: List[str] = field(default_factory=list)
    related_issues: List[str] = field(default_factory=list)
    confidence: FixConfidence = FixConfidence.MODERATE
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "report_id": self.report_id,
            "root_cause": self.root_cause,
            "affected_components": self.affected_components,
            "reproduction_steps": self.reproduction_steps,
            "related_issues": self.related_issues,
            "confidence": self.confidence.value,
            "timestamp": self.timestamp,
        }


@dataclass
class FixSuggestion:
    analysis_id: str = ""
    description: str = ""
    code_snippet: str = ""
    file_path: str = ""
    line_number: int = 0
    risk_assessment: str = ""
    estimated_effort: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "description": self.description,
            "code_snippet": self.code_snippet,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "risk_assessment": self.risk_assessment,
            "estimated_effort": self.estimated_effort,
            "timestamp": self.timestamp,
        }


# ------------------------------------------------------------------
# Error Classification Patterns
# ------------------------------------------------------------------

_NULL_POINTER_PATTERNS: List[str] = [
    r"null\s*pointer",
    r"nullptr",
    r"NullReferenceException",
    r"NullPointerException",
    r"accessing\s+null",
    r"dereference\s+null",
    r"cannot\s+read\s+property.*of\s+null",
    r"cannot\s+read\s+property.*of\s+undefined",
    r"object\s+reference\s+not\s+set",
    r"NoneType.*has\s+no\s+attribute",
    r"AttributeError.*NoneType",
    r"SIGSEGV",
    r"segmentation\s+fault",
    r"access\s+violation",
    r"EXC_BAD_ACCESS",
]

_MEMORY_LEAK_PATTERNS: List[str] = [
    r"memory\s+leak",
    r"out\s+of\s+memory",
    r"OOM",
    r"allocation\s+failed",
    r"malloc.*failed",
    r"new.*failed",
    r"heap\s+exhausted",
    r"MemoryError",
    r"std::bad_alloc",
    r"failed\s+to\s+allocate",
    r"allocation\s+size.*exceeds",
]

_RACE_CONDITION_PATTERNS: List[str] = [
    r"race\s+condition",
    r"data\s+race",
    r"concurrent\s+modification",
    r"deadlock",
    r"mutex\s+deadlock",
    r"lock\s+timeout",
    r"thread\s+safety",
    r"ConcurrentModificationException",
    r"already\s+locked",
    r"not\s+thread.?safe",
]

_INFINITE_LOOP_PATTERNS: List[str] = [
    r"infinite\s+loop",
    r"endless\s+loop",
    r"timeout\s+while\s+waiting",
    r"maximum\s+iteration",
    r"max\s+recursion\s+depth",
    r"stack\s+overflow",
    r"recursion\s+limit",
    r"watchdog\s+triggered",
    r"hang\s+detected",
    r"frame\s+timeout",
]

_ASSERTION_FAILURE_PATTERNS: List[str] = [
    r"assertion\s+failed",
    r"assert\s+failed",
    r"ASSERT",
    r"assert\(.*\)",
    r"debug\s+assert",
    r"check\s+failed",
    r"verification\s+failed",
    r"invariant\s+violated",
    r"contract\s+violation",
]

_RENDER_ERROR_PATTERNS: List[str] = [
    r"render\s+error",
    r"shader\s+compil",
    r"GPU\s+error",
    r"Vulkan\s+error",
    r"OpenGL\s+error",
    r"DirectX\s+error",
    r"Metal\s+error",
    r"framebuffer\s+error",
    r"texture\s+error",
    r"draw\s+call\s+failed",
    r"pipeline\s+error",
    r"swapchain\s+error",
    r"VK_ERROR",
    r"GL_INVALID",
]

_NETWORK_TIMEOUT_PATTERNS: List[str] = [
    r"network\s+timeout",
    r"connection\s+timeout",
    r"socket\s+timeout",
    r"request\s+timeout",
    r"HTTP.*timeout",
    r"RPC.*timeout",
    r"server\s+unreachable",
    r"connection\s+refused",
    r"connection\s+reset",
    r"DNS\s+resolution\s+failed",
    r"no\s+route\s+to\s+host",
]

_RESOURCE_EXHAUSTION_PATTERNS: List[str] = [
    r"resource\s+exhausted",
    r"file\s+descriptor.*exhausted",
    r"too\s+many\s+open\s+files",
    r"thread\s+pool\s+exhausted",
    r"connection\s+pool\s+exhausted",
    r"handle\s+limit\s+exceeded",
    r"quota\s+exceeded",
    r"buffer\s+overflow",
    r"index\s+out\s+of\s+bounds",
    r"array\s+index\s+out\s+of\s+range",
    r"vector.*out\s+of\s+range",
    r"list\s+index\s+out\s+of\s+range",
    r"IndexError",
    r"ArrayIndexOutOfBoundsException",
]


# ------------------------------------------------------------------
# Severity Classification Heuristics by Component
# ------------------------------------------------------------------

_CRITICAL_COMPONENT_PATTERNS: List[str] = [
    r"engine",
    r"core",
    r"memory",
    r"thread",
    r"render",
    r"physics",
    r"input",
    r"audio",
]

_HIGH_SEVERITY_PATTERNS: List[str] = [
    r"gameplay",
    r"network",
    r"AI",
    r"scripting",
    r"serialization",
    r"save",
    r"load",
]

_LOW_SEVERITY_PATTERNS: List[str] = [
    r"UI",
    r"menu",
    r"HUD",
    r"localization",
    r"accessibility",
]

_COSMETIC_COMPONENT_PATTERNS: List[str] = [
    r"animation",
    r"particle",
    r"effect",
    r"decal",
    r"cosmetic",
    r"visual",
    r"lighting",
    r"post.?process",
    r"bloom",
    r"ambient",
]


# ------------------------------------------------------------------
# Fix Templates by Error Category
# ------------------------------------------------------------------

_FIX_TEMPLATES: Dict[ErrorCategory, Dict[str, str]] = {
    ErrorCategory.NULL_POINTER: {
        "description": "Add null guard before dereferencing the pointer or reference",
        "code_snippet": (
            "if (ptr != nullptr) {\n"
            "    // perform the operation\n"
            "    ptr->DoWork();\n"
            "} else {\n"
            "    // log warning and handle gracefully\n"
            "    LOG_WARNING(\"Unexpected null pointer in %s\", __FUNCTION__);\n"
            "    return DEFAULT_VALUE;\n"
            "}"
        ),
        "risk_assessment": "Low risk - standard defensive programming pattern",
        "estimated_effort": "15-30 minutes",
    },
    ErrorCategory.MEMORY_LEAK: {
        "description": "Ensure proper deallocation of resources in all code paths",
        "code_snippet": (
            "// Use RAII or smart pointers to manage lifecycle\n"
            "std::unique_ptr<Resource> resource = std::make_unique<Resource>();\n"
            "// Or ensure explicit cleanup in destructor\n"
            "void Cleanup() {\n"
            "    if (allocated_buffer) {\n"
            "        free(allocated_buffer);\n"
            "        allocated_buffer = nullptr;\n"
            "    }\n"
            "}"
        ),
        "risk_assessment": "Low risk for new allocations, moderate for refactoring existing pools",
        "estimated_effort": "1-3 hours",
    },
    ErrorCategory.RACE_CONDITION: {
        "description": "Add proper synchronization around shared mutable state",
        "code_snippet": (
            "std::lock_guard<std::mutex> lock(data_mutex);\n"
            "// Access shared data within the lock scope\n"
            "shared_data.Modify();\n"
            "// Lock is automatically released at scope exit"
        ),
        "risk_assessment": "Moderate risk - may introduce deadlocks if lock ordering is incorrect",
        "estimated_effort": "2-8 hours",
    },
    ErrorCategory.INFINITE_LOOP: {
        "description": "Add loop termination condition and iteration limit",
        "code_snippet": (
            "const int MAX_ITERATIONS = 10000;\n"
            "int iteration = 0;\n"
            "while (!IsConverged() && iteration < MAX_ITERATIONS) {\n"
            "    PerformIteration();\n"
            "    iteration++;\n"
            "}\n"
            "if (iteration >= MAX_ITERATIONS) {\n"
            "    LOG_ERROR(\"Loop exceeded max iterations\");\n"
            "}"
        ),
        "risk_assessment": "Low risk - standard safety pattern",
        "estimated_effort": "30 minutes - 1 hour",
    },
    ErrorCategory.ASSERTION_FAILURE: {
        "description": "Replace assert with proper error handling for the production case",
        "code_snippet": (
            "if (!IsValidState()) {\n"
            "    LOG_ERROR(\"Invalid state detected, attempting recovery\");\n"
            "    RecoverToDefaultState();\n"
            "    return;\n"
            "}"
        ),
        "risk_assessment": "Moderate risk - assertion may have been masking a deeper issue",
        "estimated_effort": "1-4 hours",
    },
    ErrorCategory.RENDER_ERROR: {
        "description": "Add resource validity checks and fallback rendering path",
        "code_snippet": (
            "if (!shader->IsCompiled()) {\n"
            "    shader = fallback_shader;\n"
            "}\n"
            "if (!texture->IsValid()) {\n"
            "    texture = default_texture;\n"
            "}\n"
            "RenderWithResources(shader, texture);"
        ),
        "risk_assessment": "Low risk - fallback paths prevent visual corruption",
        "estimated_effort": "1-2 hours",
    },
    ErrorCategory.NETWORK_TIMEOUT: {
        "description": "Add timeout configuration, retry logic with exponential backoff",
        "code_snippet": (
            "const int MAX_RETRIES = 3;\n"
            "float backoff = 1.0f;\n"
            "for (int i = 0; i < MAX_RETRIES; i++) {\n"
            "    if (SendRequest(timeout_seconds)) break;\n"
            "    _time_module.sleep(backoff);\n"
            "    backoff *= 2.0f;\n"
            "}"
        ),
        "risk_assessment": "Low risk - standard network resilience pattern",
        "estimated_effort": "30 minutes - 1 hour",
    },
    ErrorCategory.RESOURCE_EXHAUSTION: {
        "description": "Implement resource pooling, limits, and graceful degradation",
        "code_snippet": (
            "if (resource_pool.Available() == 0) {\n"
            "    LOG_WARNING(\"Resource pool exhausted, using degraded mode\");\n"
            "    EnableDegradedMode();\n"
            "    return;\n"
            "}\n"
            "auto resource = resource_pool.Acquire();"
        ),
        "risk_assessment": "Moderate risk - pooling changes may affect memory footprint",
        "estimated_effort": "3-8 hours",
    },
    ErrorCategory.UNKNOWN: {
        "description": "Add detailed logging and graceful error handling around the crash site",
        "code_snippet": (
            "try {\n"
            "    // Suspected crash site\n"
            "    PerformOperation();\n"
            "} catch (const std::exception& e) {\n"
            "    LOG_ERROR(\"Operation failed: %s\", e.what());\n"
            "    // Attempt recovery or safe shutdown\n"
            "    SafeRecovery();\n"
            "}"
        ),
        "risk_assessment": "Unknown risk - requires further investigation",
        "estimated_effort": "4-16 hours (requires deeper analysis)",
    },
}


# ------------------------------------------------------------------
# Component Extraction from Stack Traces
# ------------------------------------------------------------------

_COMPONENT_EXTRACTION_PATTERNS: List[str] = [
    r"(?P<component>[A-Z][a-zA-Z]+(?:System|Manager|Engine|Module|Handler|Component|Renderer|Simulator|Controller|Processor))",
    r"at\s+(?P<component>[A-Z][a-zA-Z_]+)\.",
    r"in\s+(?P<component>[a-zA-Z_]+\.(?:cpp|h|cs|py|java|js|ts))",
    r"from\s+(?P<component>[a-zA-Z_]+(?:/|\.)[a-zA-Z_]+)",
    r"::(?P<component>[A-Z][a-zA-Z]+)",
]


# ------------------------------------------------------------------
# BugForensics Singleton
# ------------------------------------------------------------------


class BugForensics:
    """
    Singleton system for AI-driven crash log analysis and fix suggestion.

    Ingests crash reports, classifies errors via pattern matching on stack
    traces, performs root cause analysis, synthesizes reproduction steps,
    and generates targeted fix recommendations with risk assessment.

    The system maintains a cross-report index for discovering related
    issues and tracking fix effectiveness over time.
    """

    _instance: Optional[BugForensics] = None
    _lock = threading.RLock()

    def __new__(cls) -> BugForensics:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> BugForensics:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.__init__()
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        with self._lock:
            if hasattr(self, "_initialized") and self._initialized:
                return
            self._crash_reports: Dict[str, CrashReport] = {}
            self._analyses: Dict[str, ForensicsAnalysis] = {}
            self._fix_suggestions: Dict[str, FixSuggestion] = {}
            self._component_index: Dict[str, List[str]] = {}
            self._category_index: Dict[ErrorCategory, List[str]] = {}
            self._stats: Dict[str, Any] = {
                "total_crashes": 0,
                "total_analyses": 0,
                "total_fixes": 0,
                "resolved_count": 0,
                "by_category": {},
                "by_severity": {},
            }
            self._initialized = True

    # ------------------------------------------------------------------
    # Crash Submission
    # ------------------------------------------------------------------

    def submit_crash(
        self,
        title: str,
        stack_trace: str,
        game_state: Optional[Dict[str, Any]] = None,
        player_actions: Optional[List[str]] = None,
    ) -> CrashReport:
        """
        Ingest a crash report and perform initial classification.

        The stack trace is analyzed to determine the error category and
        severity. The report is indexed for later cross-referencing.
        """
        category = self.classify_error(stack_trace)
        severity = self._assess_severity(stack_trace, category)

        report = CrashReport(
            title=title,
            stack_trace=stack_trace,
            error_category=category,
            severity=severity,
            game_state=game_state or {},
            player_actions=player_actions or [],
        )

        self._crash_reports[report.id] = report

        self._category_index.setdefault(category, []).append(report.id)

        components = self._extract_components(stack_trace)
        for component in components:
            self._component_index.setdefault(component, []).append(report.id)

        self._stats["total_crashes"] += 1
        cat_key = category.value
        self._stats["by_category"][cat_key] = (
            self._stats["by_category"].get(cat_key, 0) + 1
        )
        sev_key = severity.value
        self._stats["by_severity"][sev_key] = (
            self._stats["by_severity"].get(sev_key, 0) + 1
        )

        return report

    # ------------------------------------------------------------------
    # Error Classification
    # ------------------------------------------------------------------

    def classify_error(self, stack_trace: str) -> ErrorCategory:
        """
        Classify the error category from a stack trace using pattern matching.

        Patterns are checked in priority order: null pointer, memory,
        race conditions, infinite loops, assertions, render errors,
        network timeouts, and resource exhaustion. Falls back to UNKNOWN.
        """
        trace_lower = stack_trace.lower()

        classification_rules: List[tuple[List[str], ErrorCategory]] = [
            (_NULL_POINTER_PATTERNS, ErrorCategory.NULL_POINTER),
            (_MEMORY_LEAK_PATTERNS, ErrorCategory.MEMORY_LEAK),
            (_RACE_CONDITION_PATTERNS, ErrorCategory.RACE_CONDITION),
            (_INFINITE_LOOP_PATTERNS, ErrorCategory.INFINITE_LOOP),
            (_ASSERTION_FAILURE_PATTERNS, ErrorCategory.ASSERTION_FAILURE),
            (_RENDER_ERROR_PATTERNS, ErrorCategory.RENDER_ERROR),
            (_NETWORK_TIMEOUT_PATTERNS, ErrorCategory.NETWORK_TIMEOUT),
            (_RESOURCE_EXHAUSTION_PATTERNS, ErrorCategory.RESOURCE_EXHAUSTION),
        ]

        best_category = ErrorCategory.UNKNOWN
        best_score = 0

        for patterns, category in classification_rules:
            score = sum(1 for p in patterns if re.search(p, trace_lower, re.IGNORECASE))
            if score > best_score:
                best_score = score
                best_category = category

        return best_category

    # ------------------------------------------------------------------
    # Severity Assessment
    # ------------------------------------------------------------------

    def _assess_severity(
        self,
        stack_trace: str,
        category: ErrorCategory,
    ) -> BugSeverity:
        """
        Determine crash severity based on the affected component and error category.

        Engine/core/memory/thread/input/audio components map to CRITICAL.
        Gameplay/network/AI/serialization map to HIGH.
        UI/menu/HUD map to LOW.
        Animation/visual/effect components map to COSMETIC.
        Category overrides: MEMORY_LEAK and RACE_CONDITION force HIGH or above.
        """
        trace_lower = stack_trace.lower()

        has_critical_component = any(
            re.search(p, trace_lower, re.IGNORECASE)
            for p in _CRITICAL_COMPONENT_PATTERNS
        )
        has_high_component = any(
            re.search(p, trace_lower, re.IGNORECASE)
            for p in _HIGH_SEVERITY_PATTERNS
        )
        has_low_component = any(
            re.search(p, trace_lower, re.IGNORECASE)
            for p in _LOW_SEVERITY_PATTERNS
        )
        has_cosmetic_component = any(
            re.search(p, trace_lower, re.IGNORECASE)
            for p in _COSMETIC_COMPONENT_PATTERNS
        )

        if category == ErrorCategory.MEMORY_LEAK:
            return BugSeverity.HIGH
        if category == ErrorCategory.RACE_CONDITION:
            return BugSeverity.HIGH
        if category == ErrorCategory.RESOURCE_EXHAUSTION:
            return BugSeverity.HIGH
        if category == ErrorCategory.ASSERTION_FAILURE:
            return BugSeverity.HIGH

        if has_critical_component:
            return BugSeverity.CRITICAL
        if has_high_component:
            return BugSeverity.HIGH
        if has_low_component:
            return BugSeverity.LOW
        if has_cosmetic_component:
            return BugSeverity.COSMETIC

        return BugSeverity.MEDIUM

    # ------------------------------------------------------------------
    # Crash Analysis
    # ------------------------------------------------------------------

    def analyze_crash(self, report_id: str) -> Optional[ForensicsAnalysis]:
        """
        Perform root cause analysis on a crash report.

        Steps:
        1. Retrieve the crash report
        2. Confirm error classification
        3. Extract affected components from the stack trace
        4. Synthesize reproduction steps from game state and player actions
        5. Find related crash reports sharing components or categories
        6. Determine confidence based on pattern match strength
        """
        report = self._crash_reports.get(report_id)
        if report is None:
            return None

        report.status = ForensicsStatus.ANALYZING

        category = self.classify_error(report.stack_trace)
        report.error_category = category

        affected_components = self._extract_components(report.stack_trace)

        root_cause = self._identify_root_cause(report.stack_trace, category)

        reproduction_steps = self.generate_reproduction_steps(report_id)

        related_reports = self.find_related_issues(report_id)
        related_ids = [r.id for r in related_reports]

        confidence = self._assess_confidence(report.stack_trace, category)

        analysis = ForensicsAnalysis(
            report_id=report_id,
            root_cause=root_cause,
            affected_components=affected_components,
            reproduction_steps=reproduction_steps,
            related_issues=related_ids,
            confidence=confidence,
        )

        self._analyses[analysis.id] = analysis
        report.status = ForensicsStatus.TRIAGED

        self._stats["total_analyses"] += 1

        return analysis

    # ------------------------------------------------------------------
    # Root Cause Identification
    # ------------------------------------------------------------------

    def _identify_root_cause(
        self,
        stack_trace: str,
        category: ErrorCategory,
    ) -> str:
        """
        Extract the most likely root cause from the stack trace.

        Uses the innermost crashing frame as the primary signal, then
        incorporates category-specific heuristics for a descriptive
        root cause summary.
        """
        frames = self._parse_stack_frames(stack_trace)
        crash_frame = frames[0] if frames else "unknown location"

        category_explanations: Dict[ErrorCategory, str] = {
            ErrorCategory.NULL_POINTER: (
                f"Null pointer dereference at {crash_frame}. "
                "An object was accessed without being properly initialized "
                "or was prematurely freed."
            ),
            ErrorCategory.MEMORY_LEAK: (
                f"Memory leak originating near {crash_frame}. "
                "Allocated memory was not freed in all code paths, "
                "leading to gradual heap exhaustion."
            ),
            ErrorCategory.RACE_CONDITION: (
                f"Race condition detected at {crash_frame}. "
                "Multiple threads accessed shared state without proper "
                "synchronization, causing data corruption."
            ),
            ErrorCategory.INFINITE_LOOP: (
                f"Infinite loop or excessive recursion at {crash_frame}. "
                "A loop termination condition was never met or recursion "
                "depth exceeded safe limits."
            ),
            ErrorCategory.ASSERTION_FAILURE: (
                f"Assertion failure at {crash_frame}. "
                "A runtime invariant was violated, indicating unexpected "
                "program state during execution."
            ),
            ErrorCategory.RENDER_ERROR: (
                f"Rendering pipeline failure at {crash_frame}. "
                "A GPU resource (shader, texture, buffer) was invalid "
                "or the pipeline state was misconfigured."
            ),
            ErrorCategory.NETWORK_TIMEOUT: (
                f"Network operation timed out at {crash_frame}. "
                "A remote endpoint did not respond within the expected "
                "window, possibly due to connectivity issues."
            ),
            ErrorCategory.RESOURCE_EXHAUSTION: (
                f"Resource limit exceeded at {crash_frame}. "
                "A system resource (file handles, threads, memory pools) "
                "was exhausted beyond available capacity."
            ),
            ErrorCategory.UNKNOWN: (
                f"Unclassified crash at {crash_frame}. "
                "The error pattern did not match any known category. "
                "Manual investigation is required."
            ),
        }

        return category_explanations.get(category, category_explanations[ErrorCategory.UNKNOWN])

    # ------------------------------------------------------------------
    # Stack Frame Parsing
    # ------------------------------------------------------------------

    def _parse_stack_frames(self, stack_trace: str) -> List[str]:
        """
        Parse a stack trace into individual frames.

        Handles common formats: C++ (function at file:line), C# (at Class.Method),
        Python (File \"path\", line N), and generic backtrace formats.
        """
        frames: List[str] = []

        cpp_pattern = re.compile(
            r"(\S+)\s+at\s+(\S+)\s+\[0x[0-9a-f]+\]",
            re.IGNORECASE,
        )
        cs_pattern = re.compile(
            r"at\s+([A-Za-z_][\w.]*\([^)]*\))\s+in\s+(\S+):line\s+(\d+)",
            re.IGNORECASE,
        )
        py_pattern = re.compile(
            r'File\s+"([^"]+)",\s+line\s+(\d+),\s+in\s+(\S+)',
        )
        generic_pattern = re.compile(
            r"#\d+\s+(?:0x[0-9a-f]+\s+)?(\S+)(?:\s+\([^)]*\))?(?:\s+\[[^\]]+\])?",
        )

        for line in stack_trace.split("\n"):
            line = line.strip()
            if not line:
                continue

            cs_match = cs_pattern.search(line)
            if cs_match:
                frames.append(f"{cs_match.group(1)} in {cs_match.group(2)}:{cs_match.group(3)}")
                continue

            cpp_match = cpp_pattern.search(line)
            if cpp_match:
                frames.append(f"{cpp_match.group(1)} at {cpp_match.group(2)}")
                continue

            py_match = py_pattern.search(line)
            if py_match:
                frames.append(f"{py_match.group(3)} at {py_match.group(1)}:{py_match.group(2)}")
                continue

            generic_match = generic_pattern.search(line)
            if generic_match:
                frames.append(generic_match.group(1))
                continue

            if len(frames) < 20:
                frames.append(line[:120])

        return frames if frames else [stack_trace[:200]]

    # ------------------------------------------------------------------
    # Component Extraction
    # ------------------------------------------------------------------

    def _extract_components(self, stack_trace: str) -> List[str]:
        """
        Extract affected component names from the stack trace.

        Uses regex patterns to identify engine subsystems, manager
        classes, and file paths referenced in the crash.
        """
        components: List[str] = []
        seen: set = set()

        for pattern in _COMPONENT_EXTRACTION_PATTERNS:
            for match in re.finditer(pattern, stack_trace):
                name = match.group("component") if "component" in match.groupdict() else match.group(0)
                if name and name not in seen:
                    seen.add(name)
                    components.append(name)

        if not components:
            components.append("unknown")

        return components[:10]

    # ------------------------------------------------------------------
    # Confidence Assessment
    # ------------------------------------------------------------------

    def _assess_confidence(
        self,
        stack_trace: str,
        category: ErrorCategory,
    ) -> FixConfidence:
        """
        Assess confidence in the error classification.

        Multiple strong pattern matches within a single category
        produce DEFINITE confidence. A single clear match yields HIGH.
        Weak or ambiguous matches yield MODERATE or TENTATIVE.
        UNKNOWN category always yields SPECULATIVE.
        """
        if category == ErrorCategory.UNKNOWN:
            return FixConfidence.SPECULATIVE

        trace_lower = stack_trace.lower()

        pattern_map: Dict[ErrorCategory, List[str]] = {
            ErrorCategory.NULL_POINTER: _NULL_POINTER_PATTERNS,
            ErrorCategory.MEMORY_LEAK: _MEMORY_LEAK_PATTERNS,
            ErrorCategory.RACE_CONDITION: _RACE_CONDITION_PATTERNS,
            ErrorCategory.INFINITE_LOOP: _INFINITE_LOOP_PATTERNS,
            ErrorCategory.ASSERTION_FAILURE: _ASSERTION_FAILURE_PATTERNS,
            ErrorCategory.RENDER_ERROR: _RENDER_ERROR_PATTERNS,
            ErrorCategory.NETWORK_TIMEOUT: _NETWORK_TIMEOUT_PATTERNS,
            ErrorCategory.RESOURCE_EXHAUSTION: _RESOURCE_EXHAUSTION_PATTERNS,
        }

        patterns = pattern_map.get(category, [])
        match_count = sum(
            1 for p in patterns if re.search(p, trace_lower, re.IGNORECASE)
        )

        if match_count >= 3:
            return FixConfidence.DEFINITE
        if match_count == 2:
            return FixConfidence.HIGH
        if match_count == 1:
            return FixConfidence.MODERATE
        return FixConfidence.TENTATIVE

    # ------------------------------------------------------------------
    # Reproduction Steps
    # ------------------------------------------------------------------

    def generate_reproduction_steps(self, report_id: str) -> List[str]:
        """
        Generate reproduction steps from game state and player actions.

        Combines contextual data from the crash report to synthesize
        a step-by-step sequence that attempts to reproduce the failure.
        """
        report = self._crash_reports.get(report_id)
        if report is None:
            return ["Unable to retrieve crash report."]

        steps: List[str] = []

        steps.append("1. Launch the game in the same configuration as the crash report.")

        game_state = report.game_state
        if game_state:
            level = game_state.get("level") or game_state.get("scene") or game_state.get("map")
            if level:
                steps.append(f"2. Load the '{level}' level/scene.")
            else:
                steps.append("2. Load the level where the crash occurred.")

            mode = game_state.get("mode") or game_state.get("game_mode")
            if mode:
                steps.append(f"3. Set game mode to '{mode}'.")

            platform = game_state.get("platform") or game_state.get("target")
            if platform:
                steps.append(f"4. Configure platform target as '{platform}'.")
        else:
            steps.append("2. Load the affected game level or scene.")
            steps.append("3. Use default game configuration.")

        player_actions = report.player_actions
        if player_actions:
            action_index = 5 if len(steps) >= 4 else len(steps) + 1
            for i, action in enumerate(player_actions[:10]):
                steps.append(f"{action_index + i}. {action}")
        else:
            steps.append("5. Perform normal gameplay actions in the crash area.")

        steps.append(f"{len(steps) + 1}. Observe the crash at the reported location.")

        category = report.error_category
        category_hints: Dict[ErrorCategory, str] = {
            ErrorCategory.RACE_CONDITION: f"{len(steps) + 2}. Run multiple instances or stress-test threading to trigger race condition.",
            ErrorCategory.MEMORY_LEAK: f"{len(steps) + 2}. Repeat the sequence multiple times to observe memory growth.",
            ErrorCategory.NETWORK_TIMEOUT: f"{len(steps) + 2}. Simulate poor network conditions or high latency.",
            ErrorCategory.RENDER_ERROR: f"{len(steps) + 2}. Verify GPU driver version and graphics settings match the crash environment.",
            ErrorCategory.RESOURCE_EXHAUSTION: f"{len(steps) + 2}. Monitor system resource usage during reproduction.",
            ErrorCategory.INFINITE_LOOP: f"{len(steps) + 2}. Attach a debugger to catch the hung thread.",
        }
        hint = category_hints.get(category)
        if hint:
            steps.append(hint)

        return steps

    # ------------------------------------------------------------------
    # Fix Suggestion
    # ------------------------------------------------------------------

    def suggest_fix(self, analysis_id: str) -> Optional[FixSuggestion]:
        """
        Generate a fix suggestion from a completed analysis.

        Uses category-specific fix templates enriched with extracted
        file paths and line numbers from the stack trace.
        """
        analysis = self._analyses.get(analysis_id)
        if analysis is None:
            return None

        report = self._crash_reports.get(analysis.report_id)
        if report is None:
            return None

        template = _FIX_TEMPLATES.get(
            report.error_category,
            _FIX_TEMPLATES[ErrorCategory.UNKNOWN],
        )

        file_path, line_number = self._extract_file_location(report.stack_trace)

        suggestion = FixSuggestion(
            analysis_id=analysis_id,
            description=template["description"],
            code_snippet=template["code_snippet"],
            file_path=file_path,
            line_number=line_number,
            risk_assessment=template["risk_assessment"],
            estimated_effort=template["estimated_effort"],
        )

        self._fix_suggestions[suggestion.id] = suggestion
        report.status = ForensicsStatus.FIX_SUGGESTED

        self._stats["total_fixes"] += 1

        return suggestion

    # ------------------------------------------------------------------
    # File Location Extraction
    # ------------------------------------------------------------------

    def _extract_file_location(self, stack_trace: str) -> tuple[str, int]:
        """
        Extract the most likely source file path and line number from
        the stack trace. Returns empty string and 0 if not found.
        """
        file_line_patterns = [
            re.compile(r"at\s+\S+\s+in\s+(?P<file>[^:\s]+):line\s+(?P<line>\d+)", re.IGNORECASE),
            re.compile(r'File\s+"(?P<file>[^"]+)",\s+line\s+(?P<line>\d+)'),
            re.compile(r"(?P<file>[a-zA-Z0-9_/\\-]+\.(?:cpp|h|cs|py|java|js|ts|rs|go))[:\(](?P<line>\d+)\)?"),
            re.compile(r"(?P<file>[^\s]+)\((?P<line>\d+)\)"),
        ]

        for line in stack_trace.split("\n"):
            for pattern in file_line_patterns:
                match = pattern.search(line)
                if match:
                    return match.group("file"), int(match.group("line"))

        return "", 0

    # ------------------------------------------------------------------
    # Related Issues
    # ------------------------------------------------------------------

    def find_related_issues(self, report_id: str) -> List[CrashReport]:
        """
        Find crash reports related to the given report.

        Related reports share the same error category or have
        overlapping affected components. Results are deduplicated.
        """
        report = self._crash_reports.get(report_id)
        if report is None:
            return []

        related_ids: set = set()

        category_ids = self._category_index.get(report.error_category, [])
        for cid in category_ids:
            if cid != report_id:
                related_ids.add(cid)

        components = self._extract_components(report.stack_trace)
        for component in components:
            component_ids = self._component_index.get(component, [])
            for cid in component_ids:
                if cid != report_id:
                    related_ids.add(cid)

        related = []
        for rid in related_ids:
            related_report = self._crash_reports.get(rid)
            if related_report:
                related.append(related_report)

        related.sort(
            key=lambda r: (
                0 if r.error_category == report.error_category else 1,
                -r.timestamp,
            )
        )

        return related[:20]

    # ------------------------------------------------------------------
    # Status Management
    # ------------------------------------------------------------------

    def mark_resolved(self, report_id: str) -> bool:
        """
        Mark a crash report as resolved. Returns True if the report
        exists and was updated, False otherwise.
        """
        report = self._crash_reports.get(report_id)
        if report is None:
            return False

        report.status = ForensicsStatus.RESOLVED
        self._stats["resolved_count"] += 1
        return True

    def mark_wont_fix(self, report_id: str) -> bool:
        """
        Mark a crash report as won't fix. Returns True if the report
        exists and was updated, False otherwise.
        """
        report = self._crash_reports.get(report_id)
        if report is None:
            return False

        report.status = ForensicsStatus.WONT_FIX
        return True

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_report(self, report_id: str) -> Optional[CrashReport]:
        """Retrieve a crash report by ID."""
        return self._crash_reports.get(report_id)

    def get_analysis(self, analysis_id: str) -> Optional[ForensicsAnalysis]:
        """Retrieve a forensics analysis by ID."""
        return self._analyses.get(analysis_id)

    def get_fix_suggestion(self, suggestion_id: str) -> Optional[FixSuggestion]:
        """Retrieve a fix suggestion by ID."""
        return self._fix_suggestions.get(suggestion_id)

    def list_reports(
        self,
        category: Optional[ErrorCategory] = None,
        severity: Optional[BugSeverity] = None,
        status: Optional[ForensicsStatus] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        List crash reports with optional filtering by category,
        severity, and status.
        """
        results = list(self._crash_reports.values())

        if category is not None:
            results = [r for r in results if r.error_category == category]
        if severity is not None:
            results = [r for r in results if r.severity == severity]
        if status is not None:
            results = [r for r in results if r.status == status]

        results.sort(key=lambda r: r.timestamp, reverse=True)
        return [r.to_dict() for r in results[:limit]]

    def list_analyses(self, report_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List forensics analyses, optionally filtered by report ID."""
        results = list(self._analyses.values())
        if report_id is not None:
            results = [a for a in results if a.report_id == report_id]
        results.sort(key=lambda a: a.timestamp, reverse=True)
        return [a.to_dict() for a in results]

    def list_fix_suggestions(
        self,
        analysis_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List fix suggestions, optionally filtered by analysis ID."""
        results = list(self._fix_suggestions.values())
        if analysis_id is not None:
            results = [s for s in results if s.analysis_id == analysis_id]
        results.sort(key=lambda s: s.timestamp, reverse=True)
        return [s.to_dict() for s in results]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for the forensics system."""
        total = max(self._stats["total_crashes"], 1)
        return {
            "total_crashes": self._stats["total_crashes"],
            "total_analyses": self._stats["total_analyses"],
            "total_fixes": self._stats["total_fixes"],
            "resolved_count": self._stats["resolved_count"],
            "resolution_rate": round(self._stats["resolved_count"] / total, 3),
            "by_category": dict(self._stats["by_category"]),
            "by_severity": dict(self._stats["by_severity"]),
            "pending_count": sum(
                1
                for r in self._crash_reports.values()
                if r.status in (ForensicsStatus.NEW, ForensicsStatus.ANALYZING)
            ),
            "triaged_count": sum(
                1
                for r in self._crash_reports.values()
                if r.status == ForensicsStatus.TRIAGED
            ),
            "wont_fix_count": sum(
                1
                for r in self._crash_reports.values()
                if r.status == ForensicsStatus.WONT_FIX
            ),
            "indexed_components": len(self._component_index),
        }

    # ------------------------------------------------------------------
    # Full Pipeline
    # ------------------------------------------------------------------

    def run_pipeline(
        self,
        title: str,
        stack_trace: str,
        game_state: Optional[Dict[str, Any]] = None,
        player_actions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the complete forensics pipeline: submit, analyze, and
        suggest a fix. Returns a dictionary with report, analysis, and
        fix suggestion.
        """
        report = self.submit_crash(
            title=title,
            stack_trace=stack_trace,
            game_state=game_state,
            player_actions=player_actions,
        )

        analysis = self.analyze_crash(report.id)

        suggestion = None
        if analysis is not None:
            suggestion = self.suggest_fix(analysis.id)

        return {
            "report": report.to_dict(),
            "analysis": analysis.to_dict() if analysis else None,
            "fix_suggestion": suggestion.to_dict() if suggestion else None,
        }


# ------------------------------------------------------------------
# Module-level Accessor
# ------------------------------------------------------------------


def get_bug_forensics() -> BugForensics:
    """Return the singleton BugForensics instance."""
    return BugForensics.get_instance()