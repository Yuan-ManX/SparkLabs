"""
SparkAI Agent - Game Vision

Visual analysis engine for game screenshots and rendering output.
Provides automated visual QA, layout analysis, UI detection, and
visual feedback generation for AI-native game development.

Key capabilities:
  - Screenshot analysis for automated visual testing
  - UI element detection and layout validation
  - Color palette and visual style assessment
  - Rendering artifact and glitch detection
  - Visual consistency checking across scenes
  - Composition and framing evaluation
"""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class VisionTaskType(Enum):
    SCREENSHOT_ANALYSIS = "screenshot_analysis"
    UI_DETECTION = "ui_detection"
    LAYOUT_VALIDATION = "layout_validation"
    COLOR_ANALYSIS = "color_analysis"
    ARTIFACT_DETECTION = "artifact_detection"
    CONSISTENCY_CHECK = "consistency_check"
    COMPOSITION_REVIEW = "composition_review"
    ACCESSIBILITY_AUDIT = "accessibility_audit"


class VisionSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class UIElementType(Enum):
    BUTTON = "button"
    TEXT = "text"
    IMAGE = "image"
    SLIDER = "slider"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    INPUT = "input"
    PANEL = "panel"
    ICON = "icon"
    PROGRESS_BAR = "progress_bar"


@dataclass
class VisionFinding:
    finding_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_type: VisionTaskType = VisionTaskType.SCREENSHOT_ANALYSIS
    severity: VisionSeverity = VisionSeverity.INFO
    title: str = ""
    description: str = ""
    location: Optional[Dict[str, float]] = None
    suggested_fix: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class UIElement:
    element_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    element_type: UIElementType = UIElementType.BUTTON
    label: str = ""
    bounding_box: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 0, "h": 0})
    text_content: str = ""
    is_visible: bool = True
    is_interactive: bool = True
    style_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisionAnalysisResult:
    analysis_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_type: VisionTaskType = VisionTaskType.SCREENSHOT_ANALYSIS
    findings: List[VisionFinding] = field(default_factory=list)
    ui_elements: List[UIElement] = field(default_factory=list)
    color_palette: List[str] = field(default_factory=list)
    composition_score: float = 0.0
    accessibility_score: float = 0.0
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


class GameVisionEngine:
    """Visual analysis engine for game screenshots and UI."""

    _instance: Optional["GameVisionEngine"] = None

    @classmethod
    def get_instance(cls) -> "GameVisionEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._results: Dict[str, VisionAnalysisResult] = {}
        self._findings_history: List[VisionFinding] = []
        self._task_count: int = 0
        self._ui_templates: Dict[str, List[UIElement]] = {}
        self._color_profiles: Dict[str, List[str]] = {}

    def analyze_screenshot(
        self,
        image_description: str,
        task_types: Optional[List[VisionTaskType]] = None,
    ) -> VisionAnalysisResult:
        """Analyze a game screenshot for visual quality and issues."""
        if task_types is None:
            task_types = list(VisionTaskType)

        self._task_count += 1
        start_time = time.time()

        result = VisionAnalysisResult(
            task_type=task_types[0] if task_types else VisionTaskType.SCREENSHOT_ANALYSIS,
        )

        for ttype in task_types:
            findings = self._run_analysis_task(ttype, image_description)
            result.findings.extend(findings)

            if ttype == VisionTaskType.UI_DETECTION:
                result.ui_elements = self._detect_ui_elements(image_description)

            if ttype == VisionTaskType.COLOR_ANALYSIS:
                result.color_palette = self._extract_color_palette(image_description)

        result.composition_score = self._evaluate_composition(image_description)
        result.accessibility_score = self._evaluate_accessibility(image_description)
        result.duration_ms = (time.time() - start_time) * 1000

        self._results[result.analysis_id] = result
        self._findings_history.extend(result.findings)

        return result

    def _run_analysis_task(
        self, task_type: VisionTaskType, image_description: str
    ) -> List[VisionFinding]:
        """Execute a specific vision analysis task."""
        findings: List[VisionFinding] = []

        if task_type == VisionTaskType.ARTIFACT_DETECTION:
            findings = self._check_artifacts(image_description)
        elif task_type == VisionTaskType.LAYOUT_VALIDATION:
            findings = self._validate_layout(image_description)
        elif task_type == VisionTaskType.CONSISTENCY_CHECK:
            findings = self._check_consistency(image_description)
        elif task_type == VisionTaskType.ACCESSIBILITY_AUDIT:
            findings = self._audit_accessibility(image_description)

        return findings

    def _check_artifacts(self, image_description: str) -> List[VisionFinding]:
        """Detect rendering artifacts and visual glitches."""
        findings: List[VisionFinding] = []

        artifact_patterns = [
            ("z-fighting", "overlapping surfaces detected", VisionSeverity.ERROR),
            ("clipping", "geometry clipping through camera plane", VisionSeverity.WARNING),
            ("stretching", "texture stretching or distortion", VisionSeverity.WARNING),
            ("aliasing", "jagged edges from insufficient anti-aliasing", VisionSeverity.INFO),
        ]

        for pattern, description, severity in artifact_patterns:
            if pattern in image_description.lower():
                findings.append(VisionFinding(
                    task_type=VisionTaskType.ARTIFACT_DETECTION,
                    severity=severity,
                    title=f"Artifact: {pattern}",
                    description=description,
                    suggested_fix=f"Review rendering settings for {pattern}",
                ))

        return findings

    def _validate_layout(self, image_description: str) -> List[VisionFinding]:
        """Validate UI layout and composition."""
        findings: List[VisionFinding] = []

        layout_issues = [
            ("overlap", "UI elements overlapping", VisionSeverity.ERROR),
            ("misaligned", "elements not aligned to grid", VisionSeverity.WARNING),
            ("overflow", "content overflowing container bounds", VisionSeverity.ERROR),
            ("spacing", "inconsistent spacing between elements", VisionSeverity.WARNING),
        ]

        for issue, description, severity in layout_issues:
            if issue in image_description.lower():
                findings.append(VisionFinding(
                    task_type=VisionTaskType.LAYOUT_VALIDATION,
                    severity=severity,
                    title=f"Layout: {issue}",
                    description=description,
                    suggested_fix=f"Adjust layout to resolve {issue}",
                ))

        return findings

    def _check_consistency(self, image_description: str) -> List[VisionFinding]:
        """Check visual consistency across scenes."""
        findings: List[VisionFinding] = []

        consistency_checks = [
            ("font", "inconsistent font usage", VisionSeverity.WARNING),
            ("color", "color scheme deviation", VisionSeverity.WARNING),
            ("spacing", "spacing guideline violation", VisionSeverity.INFO),
            ("style", "visual style inconsistency", VisionSeverity.WARNING),
        ]

        for check, description, severity in consistency_checks:
            if check in image_description.lower():
                findings.append(VisionFinding(
                    task_type=VisionTaskType.CONSISTENCY_CHECK,
                    severity=severity,
                    title=f"Consistency: {check}",
                    description=description,
                    suggested_fix=f"Standardize {check} usage across scenes",
                ))

        return findings

    def _audit_accessibility(self, image_description: str) -> List[VisionFinding]:
        """Audit visual accessibility."""
        findings: List[VisionFinding] = []

        accessibility_checks = [
            ("contrast", "low color contrast ratio", VisionSeverity.ERROR),
            ("text_size", "text too small for readability", VisionSeverity.WARNING),
            ("color_blind", "color-only information without alternatives", VisionSeverity.WARNING),
            ("focus", "missing focus indicators for interactive elements", VisionSeverity.ERROR),
        ]

        for check, description, severity in accessibility_checks:
            if check in image_description.lower():
                findings.append(VisionFinding(
                    task_type=VisionTaskType.ACCESSIBILITY_AUDIT,
                    severity=severity,
                    title=f"Accessibility: {check}",
                    description=description,
                    suggested_fix=f"Improve {check} for better accessibility",
                ))

        return findings

    def _detect_ui_elements(self, image_description: str) -> List[UIElement]:
        """Detect UI elements in a screenshot."""
        elements: List[UIElement] = []

        ui_patterns = {
            "button": UIElementType.BUTTON,
            "text_label": UIElementType.TEXT,
            "image_display": UIElementType.IMAGE,
            "slider": UIElementType.SLIDER,
            "dropdown": UIElementType.DROPDOWN,
            "checkbox": UIElementType.CHECKBOX,
            "input_field": UIElementType.INPUT,
            "panel": UIElementType.PANEL,
            "icon": UIElementType.ICON,
            "progress": UIElementType.PROGRESS_BAR,
        }

        for pattern, elem_type in ui_patterns.items():
            if pattern in image_description.lower():
                elements.append(UIElement(element_type=elem_type, label=pattern))

        return elements

    def _extract_color_palette(self, image_description: str) -> List[str]:
        """Extract dominant color palette."""
        preset_palettes = {
            "dark": ["#1a1a2e", "#16213e", "#0f3460", "#e94560"],
            "light": ["#f8f9fa", "#e9ecef", "#dee2e6", "#495057"],
            "vibrant": ["#ff6b6b", "#feca57", "#48dbfb", "#ff9ff3"],
            "nature": ["#2d6a4f", "#52b788", "#95d5b2", "#d8f3dc"],
            "scifi": ["#0b090a", "#161a1d", "#660708", "#a4161a"],
        }

        for name, palette in preset_palettes.items():
            if name in image_description.lower():
                return palette

        return preset_palettes["dark"]

    def _evaluate_composition(self, image_description: str) -> float:
        """Evaluate visual composition quality (0-100)."""
        base_score = 75.0

        positive_indicators = ["balanced", "centered", "rule_of_thirds", "framing"]
        negative_indicators = ["cluttered", "empty", "imbalanced", "chaotic"]

        for indicator in positive_indicators:
            if indicator in image_description.lower():
                base_score += 5.0

        for indicator in negative_indicators:
            if indicator in image_description.lower():
                base_score -= 10.0

        return max(0.0, min(100.0, base_score))

    def _evaluate_accessibility(self, image_description: str) -> float:
        """Evaluate accessibility score (0-100)."""
        base_score = 70.0

        accessible = ["high_contrast", "large_text", "focus_visible"]
        inaccessible = ["low_contrast", "tiny_text", "no_focus"]

        for indicator in accessible:
            if indicator in image_description.lower():
                base_score += 8.0

        for indicator in inaccessible:
            if indicator in image_description.lower():
                base_score -= 12.0

        return max(0.0, min(100.0, base_score))

    def register_ui_template(self, template_name: str, elements: List[UIElement]) -> None:
        """Register a reusable UI template for comparison."""
        self._ui_templates[template_name] = elements

    def compare_against_template(
        self, template_name: str, image_description: str
    ) -> VisionAnalysisResult:
        """Compare a screenshot against a registered template."""
        result = VisionAnalysisResult(task_type=VisionTaskType.LAYOUT_VALIDATION)

        if template_name not in self._ui_templates:
            result.findings.append(VisionFinding(
                task_type=VisionTaskType.LAYOUT_VALIDATION,
                severity=VisionSeverity.ERROR,
                title="Template Not Found",
                description=f"UI template '{template_name}' is not registered",
            ))
            return result

        template_elements = self._ui_templates[template_name]
        detected_elements = self._detect_ui_elements(image_description)

        missing = []
        for te in template_elements:
            found = any(
                de.element_type == te.element_type and de.label == te.label
                for de in detected_elements
            )
            if not found:
                missing.append(te.label)

        if missing:
            result.findings.append(VisionFinding(
                task_type=VisionTaskType.CONSISTENCY_CHECK,
                severity=VisionSeverity.ERROR,
                title="Missing UI Elements",
                description=f"Expected elements not found: {', '.join(missing)}",
                suggested_fix="Add missing UI elements to match template",
            ))

        self._results[result.analysis_id] = result
        return result

    def get_result(self, analysis_id: str) -> Optional[VisionAnalysisResult]:
        """Retrieve a previous analysis result."""
        return self._results.get(analysis_id)

    def get_findings(
        self,
        severity: Optional[VisionSeverity] = None,
        limit: int = 50,
    ) -> List[VisionFinding]:
        """Retrieve analysis findings with optional severity filter."""
        if severity is None:
            return self._findings_history[-limit:]
        return [f for f in self._findings_history if f.severity == severity][-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        severity_counts = {}
        for f in self._findings_history:
            severity_counts[f.severity.value] = severity_counts.get(f.severity.value, 0) + 1

        return {
            "total_tasks": self._task_count,
            "total_findings": len(self._findings_history),
            "cached_results": len(self._results),
            "ui_templates": len(self._ui_templates),
            "color_profiles": len(self._color_profiles),
            "severity_distribution": severity_counts,
            "average_composition_score": sum(
                r.composition_score for r in self._results.values()
            ) / max(len(self._results), 1),
        }


def get_game_vision() -> GameVisionEngine:
    return GameVisionEngine.get_instance()