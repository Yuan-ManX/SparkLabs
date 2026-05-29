"""
SparkLabs Agent - Accessibility Auditor

AI-driven game accessibility auditing system. Checks game configurations
for accessibility compliance, suggests improvements for colorblind modes,
text readability, control remapping, audio cues, and difficulty accommodations.

Architecture:
  AccessibilityAuditor (singleton)
    |-- AccessibilityCategory (accessibility domain classification)
    |-- ComplianceLevel (WCAG-style compliance grading)
    |-- AuditSeverity (issue severity ranking)
    |-- GuidelineSource (accessibility standard origin tracking)
    |-- AccessibilityCheck (single audit check result)
    |-- AuditReport (aggregated scene audit summary)
    |-- ImprovementPlan (prioritized remediation plan)

Accessibility Domains:
  - VISUAL: color contrast, colorblind support, UI scaling
  - AUDITORY: audio cues, captions, sound alternatives
  - MOTOR: control remapping, input sensitivity, hold-to-toggle
  - COGNITIVE: text readability, complexity reduction, memory aids
  - LANGUAGE: localization readiness, reading level, text alternatives
  - DEVICE: platform-specific requirements, input method compatibility
"""

from __future__ import annotations

import collections
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AccessibilityCategory(Enum):
    VISUAL = "visual"
    AUDITORY = "auditory"
    MOTOR = "motor"
    COGNITIVE = "cognitive"
    LANGUAGE = "language"
    DEVICE = "device"


class ComplianceLevel(Enum):
    FAILS = "fails"
    PARTIAL = "partial"
    MEETS = "meets"
    EXCEEDS = "exceeds"
    BEST_PRACTICE = "best_practice"

    @classmethod
    def from_score(cls, score: float) -> ComplianceLevel:
        if score >= 0.95:
            return cls.BEST_PRACTICE
        if score >= 0.85:
            return cls.EXCEEDS
        if score >= 0.70:
            return cls.MEETS
        if score >= 0.40:
            return cls.PARTIAL
        return cls.FAILS

    @property
    def numeric_lower_bound(self) -> float:
        _bounds = {
            ComplianceLevel.FAILS: 0.0,
            ComplianceLevel.PARTIAL: 0.40,
            ComplianceLevel.MEETS: 0.70,
            ComplianceLevel.EXCEEDS: 0.85,
            ComplianceLevel.BEST_PRACTICE: 0.95,
        }
        return _bounds[self]


class AuditSeverity(Enum):
    BLOCKER = "blocker"
    MAJOR = "major"
    MINOR = "minor"
    SUGGESTION = "suggestion"

    @property
    def weight(self) -> float:
        _weights = {
            AuditSeverity.BLOCKER: 1.0,
            AuditSeverity.MAJOR: 0.65,
            AuditSeverity.MINOR: 0.30,
            AuditSeverity.SUGGESTION: 0.10,
        }
        return _weights[self]


class GuidelineSource(Enum):
    WCAG = "wcag"
    GAME_ACCESSIBILITY_GUIDELINES = "game_accessibility_guidelines"
    PLATFORM_REQUIREMENT = "platform_requirement"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AccessibilityCheck:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    category: AccessibilityCategory = AccessibilityCategory.VISUAL
    check_name: str = ""
    description: str = ""
    current_state: str = ""
    compliance: ComplianceLevel = ComplianceLevel.FAILS
    severity: AuditSeverity = AuditSeverity.MAJOR
    guideline_source: GuidelineSource = GuidelineSource.CUSTOM
    score: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    remediation_hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "check_name": self.check_name,
            "description": self.description,
            "current_state": self.current_state,
            "compliance": self.compliance.value,
            "severity": self.severity.value,
            "guideline_source": self.guideline_source.value,
            "score": round(self.score, 2),
            "details": self.details,
            "remediation_hint": self.remediation_hint,
        }


@dataclass
class AuditReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    game_scene: str = ""
    checks: List[AccessibilityCheck] = field(default_factory=list)
    overall_score: float = 0.0
    overall_compliance: ComplianceLevel = ComplianceLevel.FAILS
    critical_failures: int = 0
    recommendations: List[str] = field(default_factory=list)
    audited_at: float = field(default_factory=_time_module.time)
    category_summaries: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    guideline_sources_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "game_scene": self.game_scene,
            "checks": [c.to_dict() for c in self.checks],
            "overall_score": round(self.overall_score, 2),
            "overall_compliance": self.overall_compliance.value,
            "critical_failures": self.critical_failures,
            "recommendations": self.recommendations,
            "audited_at": self.audited_at,
            "audited_iso": _time_module.strftime(
                "%Y-%m-%dT%H:%M:%S", _time_module.localtime(self.audited_at)
            ),
            "category_summaries": self.category_summaries,
            "guideline_sources_used": self.guideline_sources_used,
        }


@dataclass
class ImprovementPlan:
    report_id: str = ""
    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    prioritized_fixes: List[Dict[str, Any]] = field(default_factory=list)
    estimated_effort: str = "medium"
    impact_assessment: str = ""
    target_compliance: ComplianceLevel = ComplianceLevel.MEETS
    estimated_hours: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "plan_id": self.plan_id,
            "prioritized_fixes": self.prioritized_fixes,
            "estimated_effort": self.estimated_effort,
            "impact_assessment": self.impact_assessment,
            "target_compliance": self.target_compliance.value,
            "estimated_hours": round(self.estimated_hours, 1),
            "created_at": self.created_at,
            "created_iso": _time_module.strftime(
                "%Y-%m-%dT%H:%M:%S", _time_module.localtime(self.created_at)
            ),
        }


# ---------------------------------------------------------------------------
# Accessibility Check Templates
# ---------------------------------------------------------------------------

_CHECK_TEMPLATES: List[Dict[str, Any]] = [
    {
        "check_name": "color_contrast_ratio",
        "category": AccessibilityCategory.VISUAL,
        "description": "Verify foreground/background color pairs meet minimum contrast ratios (4.5:1 normal, 3:1 large text).",
        "guideline_source": GuidelineSource.WCAG,
        "severity": AuditSeverity.BLOCKER,
    },
    {
        "check_name": "colorblind_palette_support",
        "category": AccessibilityCategory.VISUAL,
        "description": "Ensure game provides at least one colorblind-friendly palette (deuteranopia, protanopia, tritanopia).",
        "guideline_source": GuidelineSource.GAME_ACCESSIBILITY_GUIDELINES,
        "severity": AuditSeverity.MAJOR,
    },
    {
        "check_name": "ui_scaling_support",
        "category": AccessibilityCategory.VISUAL,
        "description": "Check that UI elements support scaling up to at least 200% without layout breakage.",
        "guideline_source": GuidelineSource.WCAG,
        "severity": AuditSeverity.MAJOR,
    },
    {
        "check_name": "motion_reduction_option",
        "category": AccessibilityCategory.VISUAL,
        "description": "Verify users can disable or reduce screen shake, parallax, and rapid animations.",
        "guideline_source": GuidelineSource.GAME_ACCESSIBILITY_GUIDELINES,
        "severity": AuditSeverity.MAJOR,
    },
    {
        "check_name": "text_readability",
        "category": AccessibilityCategory.COGNITIVE,
        "description": "Check font size, line height, letter spacing, and reading level of in-game text.",
        "guideline_source": GuidelineSource.WCAG,
        "severity": AuditSeverity.BLOCKER,
    },
    {
        "check_name": "tutorial_clarity",
        "category": AccessibilityCategory.COGNITIVE,
        "description": "Evaluate whether tutorials are skippable, reviewable, and use plain language.",
        "guideline_source": GuidelineSource.GAME_ACCESSIBILITY_GUIDELINES,
        "severity": AuditSeverity.MAJOR,
    },
    {
        "check_name": "cognitive_load_warnings",
        "category": AccessibilityCategory.COGNITIVE,
        "description": "Assess on-screen information density and check for cognitive overload indicators.",
        "guideline_source": GuidelineSource.CUSTOM,
        "severity": AuditSeverity.MINOR,
    },
    {
        "check_name": "audio_cue_system",
        "category": AccessibilityCategory.AUDITORY,
        "description": "Verify critical gameplay events have both audio and visual/tactile indicators.",
        "guideline_source": GuidelineSource.GAME_ACCESSIBILITY_GUIDELINES,
        "severity": AuditSeverity.BLOCKER,
    },
    {
        "check_name": "subtitle_support",
        "category": AccessibilityCategory.AUDITORY,
        "description": "Check that subtitles/captions are available, configurable, and include speaker identification.",
        "guideline_source": GuidelineSource.WCAG,
        "severity": AuditSeverity.BLOCKER,
    },
    {
        "check_name": "audio_volume_controls",
        "category": AccessibilityCategory.AUDITORY,
        "description": "Ensure independent volume controls for music, SFX, dialogue, and ambient sounds.",
        "guideline_source": GuidelineSource.PLATFORM_REQUIREMENT,
        "severity": AuditSeverity.MAJOR,
    },
    {
        "check_name": "mono_audio_option",
        "category": AccessibilityCategory.AUDITORY,
        "description": "Check for mono audio output option for users with single-sided hearing.",
        "guideline_source": GuidelineSource.GAME_ACCESSIBILITY_GUIDELINES,
        "severity": AuditSeverity.MINOR,
    },
    {
        "check_name": "control_remapping",
        "category": AccessibilityCategory.MOTOR,
        "description": "Verify all inputs can be remapped, including keyboard, mouse, controller, and touch.",
        "guideline_source": GuidelineSource.PLATFORM_REQUIREMENT,
        "severity": AuditSeverity.BLOCKER,
    },
    {
        "check_name": "input_sensitivity",
        "category": AccessibilityCategory.MOTOR,
        "description": "Check that stick/mouse sensitivity, dead zones, and acceleration curves are adjustable.",
        "guideline_source": GuidelineSource.GAME_ACCESSIBILITY_GUIDELINES,
        "severity": AuditSeverity.MAJOR,
    },
    {
        "check_name": "hold_toggle_alternatives",
        "category": AccessibilityCategory.MOTOR,
        "description": "Verify hold-to-perform actions have toggle alternatives for reduced stamina demand.",
        "guideline_source": GuidelineSource.GAME_ACCESSIBILITY_GUIDELINES,
        "severity": AuditSeverity.MAJOR,
    },
    {
        "check_name": "assist_mode_availability",
        "category": AccessibilityCategory.MOTOR,
        "description": "Check for aim assist, auto-targeting, simplified inputs, and other motor assistance features.",
        "guideline_source": GuidelineSource.CUSTOM,
        "severity": AuditSeverity.MINOR,
    },
    {
        "check_name": "localization_readiness",
        "category": AccessibilityCategory.LANGUAGE,
        "description": "Evaluate whether UI layout accommodates text expansion for translated languages.",
        "guideline_source": GuidelineSource.WCAG,
        "severity": AuditSeverity.MAJOR,
    },
    {
        "check_name": "reading_level_assessment",
        "category": AccessibilityCategory.LANGUAGE,
        "description": "Analyze in-game text for appropriate reading level and jargon density.",
        "guideline_source": GuidelineSource.CUSTOM,
        "severity": AuditSeverity.MINOR,
    },
    {
        "check_name": "text_alternatives_for_visuals",
        "category": AccessibilityCategory.LANGUAGE,
        "description": "Check that critical visual information has text or audio description alternatives.",
        "guideline_source": GuidelineSource.WCAG,
        "severity": AuditSeverity.MAJOR,
    },
    {
        "check_name": "platform_input_compatibility",
        "category": AccessibilityCategory.DEVICE,
        "description": "Validate that the game supports platform-native accessibility APIs and input methods.",
        "guideline_source": GuidelineSource.PLATFORM_REQUIREMENT,
        "severity": AuditSeverity.BLOCKER,
    },
    {
        "check_name": "screen_reader_support",
        "category": AccessibilityCategory.DEVICE,
        "description": "Check for screen reader compatibility on menus, HUD elements, and interactive UI.",
        "guideline_source": GuidelineSource.WCAG,
        "severity": AuditSeverity.MAJOR,
    },
    {
        "check_name": "multi_device_consistency",
        "category": AccessibilityCategory.DEVICE,
        "description": "Verify that accessibility settings persist and behave consistently across target platforms.",
        "guideline_source": GuidelineSource.CUSTOM,
        "severity": AuditSeverity.MINOR,
    },
]


# ---------------------------------------------------------------------------
# AccessibilityAuditor Singleton
# ---------------------------------------------------------------------------


class AccessibilityAuditor:
    """AI-driven game accessibility auditing system with compliance grading."""

    _instance: Optional["AccessibilityAuditor"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "AccessibilityAuditor":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized: bool = True
        self._audit_reports: Dict[str, AuditReport] = {}
        self._check_templates: Dict[str, Dict[str, Any]] = {}
        self._improvement_plans: Dict[str, ImprovementPlan] = {}
        self._stats: Dict[str, Any] = {
            "total_audits": 0,
            "total_checks_performed": 0,
            "blockers_found": 0,
            "majors_found": 0,
            "minors_found": 0,
            "suggestions_found": 0,
            "fails_count": 0,
            "partials_count": 0,
            "meets_count": 0,
            "exceeds_count": 0,
            "best_practice_count": 0,
            "average_score": 0.0,
            "reports_generated": 0,
            "improvement_plans_generated": 0,
            "scenes_audited": collections.defaultdict(int),
        }
        self._load_check_templates()

    @classmethod
    def get_instance(cls) -> "AccessibilityAuditor":
        return cls()

    # ------------------------------------------------------------------
    # Template loading
    # ------------------------------------------------------------------

    def _load_check_templates(self):
        """Populate internal check template registry from predefined configurations."""
        for tmpl in _CHECK_TEMPLATES:
            self._check_templates[tmpl["check_name"]] = tmpl

    # ------------------------------------------------------------------
    # Core audit execution
    # ------------------------------------------------------------------

    def run_audit(self, scene_id: str, game_config: Dict[str, Any]) -> AuditReport:
        """Execute a full accessibility audit against a game scene configuration.

        Args:
            scene_id: Unique identifier for the game scene being audited.
            game_config: Dictionary containing visual, audio, input, UI,
                         font, and accessibility settings for the scene.

        Returns:
            AuditReport with all check results, compliance scores, and recommendations.
        """
        report = AuditReport(game_scene=scene_id)
        checks: List[AccessibilityCheck] = []

        visual_config = game_config.get("visual", {})
        audio_config = game_config.get("audio", {})
        input_config = game_config.get("input", {})
        ui_config = game_config.get("ui", {})
        font_config = game_config.get("font", {})
        localization_config = game_config.get("localization", {})
        device_config = game_config.get("device", {})
        accessibility_config = game_config.get("accessibility", {})
        tutorial_config = game_config.get("tutorial", {})

        # -- VISUAL checks --
        checks.append(
            self._run_color_contrast_check(game_config)
        )
        checks.append(
            self._run_colorblind_palette_check(accessibility_config)
        )
        checks.append(
            self._run_ui_scaling_check(ui_config)
        )
        checks.append(
            self._run_motion_reduction_check(accessibility_config)
        )

        # -- COGNITIVE checks --
        checks.append(
            self._run_text_readability_check(font_config)
        )
        checks.append(
            self._run_tutorial_clarity_check(tutorial_config)
        )
        checks.append(
            self._run_cognitive_load_check(game_config)
        )

        # -- AUDITORY checks --
        checks.append(
            self._run_audio_cue_check(audio_config)
        )
        checks.append(
            self._run_subtitle_support_check(audio_config, accessibility_config)
        )
        checks.append(
            self._run_volume_controls_check(audio_config)
        )
        checks.append(
            self._run_mono_audio_check(audio_config)
        )

        # -- MOTOR checks --
        checks.append(
            self._run_control_remapping_check(input_config)
        )
        checks.append(
            self._run_input_sensitivity_check(input_config)
        )
        checks.append(
            self._run_hold_toggle_check(input_config)
        )
        checks.append(
            self._run_assist_mode_check(accessibility_config)
        )

        # -- LANGUAGE checks --
        checks.append(
            self._run_localization_check(localization_config)
        )
        checks.append(
            self._run_reading_level_check(ui_config)
        )
        checks.append(
            self._run_text_alternatives_check(accessibility_config)
        )

        # -- DEVICE checks --
        checks.append(
            self._run_platform_input_check(device_config)
        )
        checks.append(
            self._run_screen_reader_check(ui_config, accessibility_config)
        )
        checks.append(
            self._run_multi_device_consistency_check(device_config)
        )

        report.checks = checks
        report = self._compute_report_scores(report)
        report = self._generate_recommendations(report)
        report = self._compute_category_summaries(report)
        report.guideline_sources_used = sorted(
            list({chk.guideline_source.value for chk in checks})
        )

        self._audit_reports[report.id] = report
        self._update_stats(report)

        return report

    # ------------------------------------------------------------------
    # Individual check runners
    # ------------------------------------------------------------------

    def _run_color_contrast_check(
        self, game_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["color_contrast_ratio"]
        visual = game_config.get("visual", {})
        foreground = visual.get("foreground_color", "#FFFFFF")
        background = visual.get("background_color", "#000000")
        compliance = self.check_color_contrast(foreground, background)
        score = self._compliance_to_score(compliance)
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=f"Foreground: {foreground}, Background: {background}",
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=score,
            details={"foreground": foreground, "background": background},
            remediation_hint=(
                "Increase contrast ratio to at least 4.5:1 for normal text "
                "and 3:1 for large text. Consider darker backgrounds with "
                "lighter text."
            ),
        )

    def _run_colorblind_palette_check(
        self, accessibility_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["colorblind_palette_support"]
        palettes = accessibility_config.get("colorblind_palettes", [])
        mode_count = len(palettes) if isinstance(palettes, list) else 0
        if mode_count >= 3:
            compliance = ComplianceLevel.BEST_PRACTICE
        elif mode_count >= 2:
            compliance = ComplianceLevel.EXCEEDS
        elif mode_count >= 1:
            compliance = ComplianceLevel.MEETS
        else:
            compliance = ComplianceLevel.FAILS
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=f"{mode_count} colorblind palette(s) configured",
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={"palettes": palettes},
            remediation_hint=(
                "Add at least one colorblind-friendly palette supporting "
                "deuteranopia, protanopia, and tritanopia."
            ),
        )

    def _run_ui_scaling_check(
        self, ui_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["ui_scaling_support"]
        max_scale = ui_config.get("max_scale_percent", 100)
        if isinstance(max_scale, (int, float)):
            if max_scale >= 200:
                compliance = ComplianceLevel.EXCEEDS
            elif max_scale >= 150:
                compliance = ComplianceLevel.MEETS
            elif max_scale >= 110:
                compliance = ComplianceLevel.PARTIAL
            else:
                compliance = ComplianceLevel.FAILS
        else:
            compliance = ComplianceLevel.FAILS
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=f"Max UI scale: {max_scale}%",
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={"max_scale_percent": max_scale},
            remediation_hint=(
                "Support UI scaling up to at least 200% with anchor-based "
                "layout to prevent element overlap and clipping."
            ),
        )

    def _run_motion_reduction_check(
        self, accessibility_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["motion_reduction_option"]
        motion_option = accessibility_config.get("reduce_motion", False)
        if isinstance(motion_option, bool) and motion_option:
            compliance = ComplianceLevel.MEETS
        elif accessibility_config.get("motion_reduction_toggle", False):
            compliance = ComplianceLevel.MEETS
        else:
            compliance = ComplianceLevel.FAILS
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=(
                "Motion reduction available"
                if compliance in (ComplianceLevel.MEETS, ComplianceLevel.EXCEEDS)
                else "No motion reduction option found"
            ),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={"reduce_motion": motion_option},
            remediation_hint=(
                "Add a toggle to disable screen shake, parallax effects, "
                "and rapid animations."
            ),
        )

    def _run_text_readability_check(
        self, font_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["text_readability"]
        compliance = self.check_text_readability(font_config)
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=self._describe_font_config(font_config),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details=dict(font_config),
            remediation_hint=(
                "Use minimum 14px body text, 1.5x line height, and avoid "
                "decorative fonts for critical information."
            ),
        )

    def _run_tutorial_clarity_check(
        self, tutorial_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["tutorial_clarity"]
        skippable = tutorial_config.get("skippable", False)
        reviewable = tutorial_config.get("reviewable", False)
        plain_language = tutorial_config.get("plain_language", False)
        score_count = sum([skippable, reviewable, plain_language])
        if score_count >= 3:
            compliance = ComplianceLevel.BEST_PRACTICE
        elif score_count >= 2:
            compliance = ComplianceLevel.MEETS
        elif score_count >= 1:
            compliance = ComplianceLevel.PARTIAL
        else:
            compliance = ComplianceLevel.FAILS
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=(
                f"Skippable: {skippable}, Reviewable: {reviewable}, "
                f"Plain Language: {plain_language}"
            ),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={
                "skippable": skippable,
                "reviewable": reviewable,
                "plain_language": plain_language,
            },
            remediation_hint=(
                "Make all tutorials skippable, add a tutorial review menu, "
                "and write instructions in plain language."
            ),
        )

    def _run_cognitive_load_check(
        self, game_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["cognitive_load_warnings"]
        ui_config = game_config.get("ui", {})
        hud_elements = ui_config.get("hud_element_count", 10)
        if isinstance(hud_elements, (int, float)):
            if hud_elements <= 5:
                compliance = ComplianceLevel.BEST_PRACTICE
            elif hud_elements <= 8:
                compliance = ComplianceLevel.EXCEEDS
            elif hud_elements <= 12:
                compliance = ComplianceLevel.MEETS
            elif hud_elements <= 18:
                compliance = ComplianceLevel.PARTIAL
            else:
                compliance = ComplianceLevel.FAILS
        else:
            compliance = ComplianceLevel.PARTIAL
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=f"HUD elements: {hud_elements}",
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={"hud_element_count": hud_elements},
            remediation_hint=(
                "Reduce on-screen information density by grouping related "
                "elements and allowing players to customize HUD visibility."
            ),
        )

    def _run_audio_cue_check(
        self, audio_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["audio_cue_system"]
        compliance = self.check_audio_cues(audio_config)
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=self._describe_audio_config(audio_config),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details=dict(audio_config),
            remediation_hint=(
                "Ensure all critical audio events have synchronized visual "
                "or haptic indicators."
            ),
        )

    def _run_subtitle_support_check(
        self,
        audio_config: Dict[str, Any],
        accessibility_config: Dict[str, Any],
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["subtitle_support"]
        subtitles_enabled = audio_config.get("subtitles_enabled", False)
        speaker_labels = audio_config.get("speaker_labels", False)
        configurable = audio_config.get("subtitle_configurable", False)
        score_count = sum([subtitles_enabled, speaker_labels, configurable])
        if score_count >= 3:
            compliance = ComplianceLevel.BEST_PRACTICE
        elif score_count >= 2:
            compliance = ComplianceLevel.MEETS
        elif score_count >= 1:
            compliance = ComplianceLevel.PARTIAL
        else:
            compliance = ComplianceLevel.FAILS
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=(
                f"Enabled: {subtitles_enabled}, Labels: {speaker_labels}, "
                f"Configurable: {configurable}"
            ),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={
                "subtitles_enabled": subtitles_enabled,
                "speaker_labels": speaker_labels,
                "configurable": configurable,
            },
            remediation_hint=(
                "Add configurable subtitles with speaker identification, "
                "adjustable size, and background opacity options."
            ),
        )

    def _run_volume_controls_check(
        self, audio_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["audio_volume_controls"]
        master = audio_config.get("master_volume", 0)
        music = audio_config.get("music_volume", 0)
        sfx = audio_config.get("sfx_volume", 0)
        dialogue = audio_config.get("dialogue_volume", 0)
        has_controls = all(
            isinstance(v, (int, float))
            for v in [master, music, sfx, dialogue]
        )
        if audio_config.get("independent_channels", False) and has_controls:
            compliance = ComplianceLevel.BEST_PRACTICE
        elif has_controls:
            compliance = ComplianceLevel.MEETS
        elif any(isinstance(v, (int, float)) for v in [master, music, sfx]):
            compliance = ComplianceLevel.PARTIAL
        else:
            compliance = ComplianceLevel.FAILS
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=(
                f"Master: {master}, Music: {music}, SFX: {sfx}, "
                f"Dialogue: {dialogue}"
            ),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={
                "master_volume": master,
                "music_volume": music,
                "sfx_volume": sfx,
                "dialogue_volume": dialogue,
            },
            remediation_hint=(
                "Provide independent volume sliders for master, music, SFX, "
                "dialogue, and ambient channels."
            ),
        )

    def _run_mono_audio_check(
        self, audio_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["mono_audio_option"]
        mono_available = audio_config.get("mono_output", False)
        compliance = ComplianceLevel.MEETS if mono_available else ComplianceLevel.FAILS
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=(
                "Mono output available"
                if mono_available
                else "No mono output option"
            ),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={"mono_output": mono_available},
            remediation_hint=(
                "Add a mono audio output toggle for players with "
                "single-sided hearing."
            ),
        )

    def _run_control_remapping_check(
        self, input_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["control_remapping"]
        compliance = self.check_control_remapping(input_config)
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=self._describe_input_config(input_config),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details=dict(input_config),
            remediation_hint=(
                "Allow full remapping of all inputs across keyboard, mouse, "
                "controller, and touch surfaces."
            ),
        )

    def _run_input_sensitivity_check(
        self, input_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["input_sensitivity"]
        adjustable_sensitivity = input_config.get("adjustable_sensitivity", False)
        adjustable_deadzone = input_config.get("adjustable_deadzone", False)
        if adjustable_sensitivity and adjustable_deadzone:
            compliance = ComplianceLevel.BEST_PRACTICE
        elif adjustable_sensitivity or adjustable_deadzone:
            compliance = ComplianceLevel.MEETS
        else:
            compliance = ComplianceLevel.FAILS
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=(
                f"Sensitivity adjustable: {adjustable_sensitivity}, "
                f"Deadzone adjustable: {adjustable_deadzone}"
            ),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={
                "adjustable_sensitivity": adjustable_sensitivity,
                "adjustable_deadzone": adjustable_deadzone,
            },
            remediation_hint=(
                "Expose stick/mouse sensitivity, dead zone, and acceleration "
                "curve settings to players."
            ),
        )

    def _run_hold_toggle_check(
        self, input_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["hold_toggle_alternatives"]
        toggle_supported = input_config.get("hold_to_toggle", False)
        compliance = (
            ComplianceLevel.MEETS if toggle_supported else ComplianceLevel.FAILS
        )
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=(
                "Toggle available"
                if toggle_supported
                else "Hold-only, no toggle alternative"
            ),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={"hold_to_toggle": toggle_supported},
            remediation_hint=(
                "Provide toggle mode as an alternative for all "
                "hold-to-perform actions."
            ),
        )

    def _run_assist_mode_check(
        self, accessibility_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["assist_mode_availability"]
        aim_assist = accessibility_config.get("aim_assist", False)
        auto_target = accessibility_config.get("auto_targeting", False)
        simplified_inputs = accessibility_config.get("simplified_inputs", False)
        score_count = sum([aim_assist, auto_target, simplified_inputs])
        if score_count >= 3:
            compliance = ComplianceLevel.BEST_PRACTICE
        elif score_count >= 2:
            compliance = ComplianceLevel.EXCEEDS
        elif score_count >= 1:
            compliance = ComplianceLevel.MEETS
        else:
            compliance = ComplianceLevel.FAILS
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=(
                f"Aim Assist: {aim_assist}, Auto-Target: {auto_target}, "
                f"Simplified: {simplified_inputs}"
            ),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={
                "aim_assist": aim_assist,
                "auto_targeting": auto_target,
                "simplified_inputs": simplified_inputs,
            },
            remediation_hint=(
                "Offer aim assist, auto-targeting, and simplified control "
                "schemes for motor accessibility."
            ),
        )

    def _run_localization_check(
        self, localization_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["localization_readiness"]
        text_expansion_support = localization_config.get(
            "text_expansion_support", False
        )
        locale_count = localization_config.get("supported_locales", 0)
        if isinstance(locale_count, list):
            locale_count = len(locale_count)
        if text_expansion_support and locale_count >= 3:
            compliance = ComplianceLevel.BEST_PRACTICE
        elif text_expansion_support or locale_count >= 2:
            compliance = ComplianceLevel.MEETS
        elif locale_count >= 1:
            compliance = ComplianceLevel.PARTIAL
        else:
            compliance = ComplianceLevel.FAILS
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=(
                f"Text expansion support: {text_expansion_support}, "
                f"Locales: {locale_count}"
            ),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={
                "text_expansion_support": text_expansion_support,
                "supported_locales": locale_count,
            },
            remediation_hint=(
                "Design UI layouts with 30-40% text expansion headroom for "
                "common translations."
            ),
        )

    def _run_reading_level_check(
        self, ui_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["reading_level_assessment"]
        reading_level = ui_config.get("target_reading_level", "college")
        levels_map = {
            "elementary": ComplianceLevel.BEST_PRACTICE,
            "middle_school": ComplianceLevel.EXCEEDS,
            "high_school": ComplianceLevel.MEETS,
            "college": ComplianceLevel.PARTIAL,
        }
        compliance = levels_map.get(reading_level, ComplianceLevel.FAILS)
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=f"Target reading level: {reading_level}",
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={"target_reading_level": reading_level},
            remediation_hint=(
                "Aim for a reading level of high school or below. Reduce "
                "jargon and use common vocabulary."
            ),
        )

    def _run_text_alternatives_check(
        self, accessibility_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["text_alternatives_for_visuals"]
        text_descriptions = accessibility_config.get("text_descriptions", False)
        audio_descriptions = accessibility_config.get("audio_descriptions", False)
        if text_descriptions and audio_descriptions:
            compliance = ComplianceLevel.BEST_PRACTICE
        elif text_descriptions or audio_descriptions:
            compliance = ComplianceLevel.MEETS
        else:
            compliance = ComplianceLevel.FAILS
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=(
                f"Text descriptions: {text_descriptions}, "
                f"Audio descriptions: {audio_descriptions}"
            ),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={
                "text_descriptions": text_descriptions,
                "audio_descriptions": audio_descriptions,
            },
            remediation_hint=(
                "Provide text and/or audio description alternatives for "
                "critical visual game information."
            ),
        )

    def _run_platform_input_check(
        self, device_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["platform_input_compatibility"]
        platform_api = device_config.get("platform_accessibility_api", False)
        native_input = device_config.get("native_input_support", False)
        if platform_api and native_input:
            compliance = ComplianceLevel.BEST_PRACTICE
        elif platform_api:
            compliance = ComplianceLevel.MEETS
        elif native_input:
            compliance = ComplianceLevel.PARTIAL
        else:
            compliance = ComplianceLevel.FAILS
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=(
                f"Platform API: {platform_api}, "
                f"Native Input: {native_input}"
            ),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={
                "platform_accessibility_api": platform_api,
                "native_input_support": native_input,
            },
            remediation_hint=(
                "Integrate with platform-native accessibility APIs and "
                "support switch/adaptive controller inputs."
            ),
        )

    def _run_screen_reader_check(
        self,
        ui_config: Dict[str, Any],
        accessibility_config: Dict[str, Any],
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["screen_reader_support"]
        sr_support = accessibility_config.get("screen_reader_support", False)
        semantic_ui = ui_config.get("semantic_ui_labels", False)
        if sr_support and semantic_ui:
            compliance = ComplianceLevel.BEST_PRACTICE
        elif sr_support:
            compliance = ComplianceLevel.MEETS
        elif semantic_ui:
            compliance = ComplianceLevel.PARTIAL
        else:
            compliance = ComplianceLevel.FAILS
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=(
                f"Screen reader: {sr_support}, "
                f"Semantic labels: {semantic_ui}"
            ),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={
                "screen_reader_support": sr_support,
                "semantic_ui_labels": semantic_ui,
            },
            remediation_hint=(
                "Add semantic labeling to all UI elements and ensure "
                "screen reader navigation order is logical."
            ),
        )

    def _run_multi_device_consistency_check(
        self, device_config: Dict[str, Any]
    ) -> AccessibilityCheck:
        tmpl = self._check_templates["multi_device_consistency"]
        targets = device_config.get("target_platforms", [])
        if isinstance(targets, list):
            platform_count = len(targets)
        else:
            platform_count = 0
        settings_sync = device_config.get("settings_sync", False)
        if settings_sync and platform_count >= 2:
            compliance = ComplianceLevel.BEST_PRACTICE
        elif platform_count >= 2:
            compliance = ComplianceLevel.MEETS
        elif platform_count == 1:
            compliance = ComplianceLevel.PARTIAL
        else:
            compliance = ComplianceLevel.PARTIAL
        return AccessibilityCheck(
            category=tmpl["category"],
            check_name=tmpl["check_name"],
            description=tmpl["description"],
            current_state=(
                f"Platforms: {platform_count}, Settings sync: {settings_sync}"
            ),
            compliance=compliance,
            severity=tmpl["severity"],
            guideline_source=tmpl["guideline_source"],
            score=self._compliance_to_score(compliance),
            details={
                "target_platforms": platform_count,
                "settings_sync": settings_sync,
            },
            remediation_hint=(
                "Ensure accessibility settings persist and behave consistently "
                "across all target platforms."
            ),
        )

    # ------------------------------------------------------------------
    # Domain-specific compliance checkers
    # ------------------------------------------------------------------

    def check_color_contrast(
        self, foreground: str, background: str
    ) -> ComplianceLevel:
        """Evaluate color contrast compliance between a foreground and
        background color pair.

        Colors are expected as hex strings (e.g. '#FFFFFF'). The method
        computes an approximate relative luminance and contrast ratio based
        on WCAG 2.1 formulas.

        Args:
            foreground: Hex color string for the foreground element.
            background: Hex color string for the background element.

        Returns:
            ComplianceLevel based on computed contrast ratio.
        """
        fg_luminance = self._hex_to_luminance(foreground)
        bg_luminance = self._hex_to_luminance(background)
        if bg_luminance <= 0.0:
            return ComplianceLevel.FAILS

        lighter = max(fg_luminance, bg_luminance)
        darker = min(fg_luminance, bg_luminance)
        contrast_ratio = (lighter + 0.05) / (darker + 0.05)

        if contrast_ratio >= 7.0:
            return ComplianceLevel.BEST_PRACTICE
        if contrast_ratio >= 4.5:
            return ComplianceLevel.MEETS
        if contrast_ratio >= 3.0:
            return ComplianceLevel.PARTIAL
        return ComplianceLevel.FAILS

    @staticmethod
    def _hex_to_luminance(hex_color: str) -> float:
        """Convert a hex color string to relative luminance per WCAG 2.1.

        Accepts 3-character or 6-character hex strings with optional '#' prefix.
        Returns 0.0 for invalid inputs.
        """
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        if len(hex_color) != 6:
            return 0.0

        try:
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
        except (ValueError, IndexError):
            return 0.0

        def _linearize(channel: float) -> float:
            if channel <= 0.03928:
                return channel / 12.92
            return ((channel + 0.055) / 1.055) ** 2.4

        return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)

    def check_text_readability(
        self, font_config: Dict[str, Any]
    ) -> ComplianceLevel:
        """Evaluate text readability based on font size, line height,
        letter spacing, and contrast configuration.

        Args:
            font_config: Dictionary with keys like 'size_px', 'line_height',
                         'letter_spacing', 'font_family', and 'contrast_ratio'.

        Returns:
            ComplianceLevel based on readability heuristics.
        """
        size = font_config.get("size_px", 12)
        line_height = font_config.get("line_height", 1.2)
        letter_spacing = font_config.get("letter_spacing", 0.0)
        contrast_ratio = font_config.get("contrast_ratio", 1.0)

        score = 0.0
        if isinstance(size, (int, float)) and size >= 16:
            score += 0.30
        elif isinstance(size, (int, float)) and size >= 14:
            score += 0.20
        elif isinstance(size, (int, float)) and size >= 12:
            score += 0.10

        if isinstance(line_height, (int, float)) and line_height >= 1.5:
            score += 0.30
        elif isinstance(line_height, (int, float)) and line_height >= 1.3:
            score += 0.15

        if isinstance(letter_spacing, (int, float)) and letter_spacing >= 0.05:
            score += 0.15

        if isinstance(contrast_ratio, (int, float)) and contrast_ratio >= 4.5:
            score += 0.25
        elif isinstance(contrast_ratio, (int, float)) and contrast_ratio >= 3.0:
            score += 0.15

        return ComplianceLevel.from_score(score)

    def check_audio_cues(
        self, audio_config: Dict[str, Any]
    ) -> ComplianceLevel:
        """Evaluate whether critical audio events have corresponding visual
        or haptic alternatives for deaf/hard-of-hearing players.

        Args:
            audio_config: Dictionary with keys like 'visual_cues',
                         'haptic_feedback', 'closed_captions',
                         'audio_descriptions'.

        Returns:
            ComplianceLevel based on audio cue accessibility.
        """
        visual_cues = audio_config.get("visual_cues", False)
        haptic_feedback = audio_config.get("haptic_feedback", False)
        closed_captions = audio_config.get("closed_captions", False)

        score = 0.0
        if visual_cues:
            score += 0.40
        if haptic_feedback:
            score += 0.30
        if closed_captions:
            score += 0.30

        return ComplianceLevel.from_score(score)

    def check_control_remapping(
        self, input_config: Dict[str, Any]
    ) -> ComplianceLevel:
        """Evaluate whether game controls support full remapping including
        keyboard, mouse, controller, and touch inputs.

        Args:
            input_config: Dictionary with keys like 'remappable',
                         'controller_support', 'keyboard_support',
                         'mouse_support', 'touch_support',
                         'preset_profiles'.

        Returns:
            ComplianceLevel based on remapping coverage.
        """
        remappable = input_config.get("remappable", False)
        if not remappable:
            return ComplianceLevel.FAILS

        keyboard = input_config.get("keyboard_support", False)
        mouse = input_config.get("mouse_support", False)
        controller = input_config.get("controller_support", False)
        touch = input_config.get("touch_support", False)
        presets = input_config.get("preset_profiles", False)

        device_count = sum([keyboard, mouse, controller, touch])
        score = 0.0

        if device_count >= 4:
            score += 0.60
        elif device_count >= 3:
            score += 0.50
        elif device_count >= 2:
            score += 0.35
        else:
            score += 0.20

        if presets:
            score += 0.25

        if input_config.get("conflict_warnings", False):
            score += 0.15

        return ComplianceLevel.from_score(score)

    # ------------------------------------------------------------------
    # Improvement plan generation
    # ------------------------------------------------------------------

    def generate_improvement_plan(self, report_id: str) -> ImprovementPlan:
        """Generate a prioritized improvement plan from an audit report.

        Args:
            report_id: The UUID of a previously generated AuditReport.

        Returns:
            ImprovementPlan with ranked fixes, effort estimates, and impact
            assessment.

        Raises:
            ValueError: If the report_id is not found.
        """
        report = self._audit_reports.get(report_id)
        if report is None:
            raise ValueError(f"Audit report not found: {report_id}")

        prioritized: List[Dict[str, Any]] = []
        failed_checks = [
            chk for chk in report.checks
            if chk.compliance in (ComplianceLevel.FAILS, ComplianceLevel.PARTIAL)
        ]
        failed_checks.sort(
            key=lambda c: (
                c.severity.weight,
                c.score,
            ),
            reverse=True,
        )

        total_hours = 0.0
        for idx, chk in enumerate(failed_checks):
            effort_hours = self._estimate_fix_effort(chk)
            total_hours += effort_hours
            prioritized.append({
                "rank": idx + 1,
                "check_id": chk.id,
                "check_name": chk.check_name,
                "category": chk.category.value,
                "current_compliance": chk.compliance.value,
                "severity": chk.severity.value,
                "remediation_hint": chk.remediation_hint,
                "estimated_effort_hours": round(effort_hours, 1),
                "effort_level": self._effort_hours_to_level(effort_hours),
            })

        total_blockers = sum(
            1 for p in prioritized if p["severity"] == AuditSeverity.BLOCKER.value
        )
        estimated_effort = self._compute_overall_effort(total_hours)
        target = (
            ComplianceLevel.EXCEEDS
            if report.overall_score >= 0.70
            else ComplianceLevel.MEETS
        )

        impact = (
            f"Addressing {len(prioritized)} issues will improve the overall "
            f"compliance score from {report.overall_score:.2f} to an estimated "
            f"{min(report.overall_score + 0.25, 1.0):.2f}. "
            f"{total_blockers} blocker-level issue(s) must be resolved first."
        )

        plan = ImprovementPlan(
            report_id=report_id,
            prioritized_fixes=prioritized,
            estimated_effort=estimated_effort,
            impact_assessment=impact,
            target_compliance=target,
            estimated_hours=round(total_hours, 1),
        )

        self._improvement_plans[plan.plan_id] = plan
        self._stats["improvement_plans_generated"] += 1

        return plan

    @staticmethod
    def _estimate_fix_effort(check: AccessibilityCheck) -> float:
        """Estimate remediation effort in hours based on severity and category.

        Args:
            check: The AccessibilityCheck to estimate effort for.

        Returns:
            Estimated hours to fix the issue.
        """
        base_effort = {
            AccessibilityCategory.VISUAL: 4.0,
            AccessibilityCategory.AUDITORY: 3.0,
            AccessibilityCategory.MOTOR: 5.0,
            AccessibilityCategory.COGNITIVE: 2.0,
            AccessibilityCategory.LANGUAGE: 3.0,
            AccessibilityCategory.DEVICE: 6.0,
        }.get(check.category, 3.0)

        severity_multiplier = {
            AuditSeverity.BLOCKER: 1.5,
            AuditSeverity.MAJOR: 1.2,
            AuditSeverity.MINOR: 1.0,
            AuditSeverity.SUGGESTION: 0.6,
        }.get(check.severity, 1.0)

        compliance_penalty = 1.0
        if check.compliance == ComplianceLevel.FAILS:
            compliance_penalty = 1.4
        elif check.compliance == ComplianceLevel.PARTIAL:
            compliance_penalty = 1.0

        return round(base_effort * severity_multiplier * compliance_penalty, 1)

    @staticmethod
    def _effort_hours_to_level(hours: float) -> str:
        if hours <= 2.0:
            return "trivial"
        if hours <= 6.0:
            return "moderate"
        if hours <= 12.0:
            return "significant"
        return "major"

    @staticmethod
    def _compute_overall_effort(total_hours: float) -> str:
        if total_hours <= 10.0:
            return "low"
        if total_hours <= 30.0:
            return "medium"
        if total_hours <= 80.0:
            return "high"
        return "critical"

    # ------------------------------------------------------------------
    # Report scoring and summarization
    # ------------------------------------------------------------------

    def _compute_report_scores(self, report: AuditReport) -> AuditReport:
        """Compute overall score, compliance level, and failure counts for a
        report based on its checks."""
        if not report.checks:
            report.overall_score = 0.0
            report.overall_compliance = ComplianceLevel.FAILS
            report.critical_failures = 0
            return report

        total_weight = 0.0
        weighted_sum = 0.0
        critical_count = 0

        for chk in report.checks:
            weight = chk.severity.weight
            total_weight += weight
            weighted_sum += chk.score * weight
            if chk.compliance in (ComplianceLevel.FAILS,) and chk.severity in (
                AuditSeverity.BLOCKER,
                AuditSeverity.MAJOR,
            ):
                critical_count += 1

        report.overall_score = (
            weighted_sum / total_weight if total_weight > 0 else 0.0
        )
        report.overall_compliance = ComplianceLevel.from_score(report.overall_score)
        report.critical_failures = critical_count
        return report

    def _generate_recommendations(self, report: AuditReport) -> AuditReport:
        """Generate human-readable recommendations sorted by priority."""
        recommendations: List[str] = []
        failed_checks = sorted(
            report.checks,
            key=lambda c: (c.severity.weight, c.score),
            reverse=True,
        )
        for chk in failed_checks:
            if chk.compliance in (ComplianceLevel.FAILS, ComplianceLevel.PARTIAL):
                recommendations.append(
                    f"[{chk.severity.value.upper()}] {chk.check_name}: "
                    f"{chk.remediation_hint}"
                )
        report.recommendations = recommendations
        return report

    def _compute_category_summaries(self, report: AuditReport) -> AuditReport:
        """Compute per-category compliance summaries for the report."""
        summaries: Dict[str, Dict[str, Any]] = {}
        for cat in AccessibilityCategory:
            cat_checks = [c for c in report.checks if c.category == cat]
            if not cat_checks:
                continue
            avg_score = sum(c.score for c in cat_checks) / len(cat_checks)
            blockers = sum(
                1 for c in cat_checks
                if c.severity == AuditSeverity.BLOCKER
                and c.compliance == ComplianceLevel.FAILS
            )
            summaries[cat.value] = {
                "check_count": len(cat_checks),
                "average_score": round(avg_score, 2),
                "compliance": ComplianceLevel.from_score(avg_score).value,
                "blockers": blockers,
                "fail_count": sum(
                    1 for c in cat_checks if c.compliance == ComplianceLevel.FAILS
                ),
            }
        report.category_summaries = summaries
        return report

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compliance_to_score(compliance: ComplianceLevel) -> float:
        """Map a ComplianceLevel to a representative numeric score."""
        _score_map = {
            ComplianceLevel.FAILS: 0.15,
            ComplianceLevel.PARTIAL: 0.55,
            ComplianceLevel.MEETS: 0.78,
            ComplianceLevel.EXCEEDS: 0.90,
            ComplianceLevel.BEST_PRACTICE: 0.98,
        }
        return _score_map.get(compliance, 0.0)

    @staticmethod
    def _describe_font_config(font_config: Dict[str, Any]) -> str:
        size = font_config.get("size_px", "N/A")
        line_height = font_config.get("line_height", "N/A")
        family = font_config.get("font_family", "default")
        return f"Size: {size}px, Line Height: {line_height}, Family: {family}"

    @staticmethod
    def _describe_audio_config(audio_config: Dict[str, Any]) -> str:
        visual = audio_config.get("visual_cues", False)
        haptic = audio_config.get("haptic_feedback", False)
        captions = audio_config.get("closed_captions", False)
        return (
            f"Visual cues: {visual}, Haptic: {haptic}, Captions: {captions}"
        )

    @staticmethod
    def _describe_input_config(input_config: Dict[str, Any]) -> str:
        remappable = input_config.get("remappable", False)
        keyboard = input_config.get("keyboard_support", False)
        controller = input_config.get("controller_support", False)
        return (
            f"Remappable: {remappable}, Keyboard: {keyboard}, "
            f"Controller: {controller}"
        )

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def _update_stats(self, report: AuditReport):
        """Update internal statistics counters from a completed audit report."""
        self._stats["total_audits"] += 1
        self._stats["total_checks_performed"] += len(report.checks)
        self._stats["reports_generated"] += 1

        for chk in report.checks:
            stat_key = f"{chk.severity.value}s_found"
            if stat_key in self._stats:
                self._stats[stat_key] += 1
            compliance_key = f"{chk.compliance.value}s_count"
            if compliance_key in self._stats:
                self._stats[compliance_key] += 1

        total_scores = self._stats["average_score"] * (self._stats["total_audits"] - 1)
        total_scores += report.overall_score
        self._stats["average_score"] = round(
            total_scores / self._stats["total_audits"], 2
        )

        scenes = self._stats["scenes_audited"]
        if isinstance(scenes, collections.defaultdict):
            scenes[str(report.game_scene)] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Return a snapshot of auditor statistics.

        Returns:
            Dictionary with audit counts, severity distributions,
            compliance breakdowns, and average scores.
        """
        scenes = self._stats.get("scenes_audited", {})
        if isinstance(scenes, collections.defaultdict):
            scenes_dict = dict(scenes)
        else:
            scenes_dict = scenes

        return {
            "total_audits": self._stats["total_audits"],
            "total_checks_performed": self._stats["total_checks_performed"],
            "reports_generated": self._stats["reports_generated"],
            "improvement_plans_generated": self._stats[
                "improvement_plans_generated"
            ],
            "average_score": self._stats["average_score"],
            "severity_distribution": {
                "blockers": self._stats["blockers_found"],
                "majors": self._stats["majors_found"],
                "minors": self._stats["minors_found"],
                "suggestions": self._stats["suggestions_found"],
            },
            "compliance_distribution": {
                "fails": self._stats["fails_count"],
                "partials": self._stats["partials_count"],
                "meets": self._stats["meets_count"],
                "exceeds": self._stats["exceeds_count"],
                "best_practice": self._stats["best_practice_count"],
            },
            "scenes_audited": sorted(scenes_dict.keys()),
        }

    def get_report(self, report_id: str) -> Optional[AuditReport]:
        """Retrieve a previously generated audit report by ID.

        Args:
            report_id: The UUID of the audit report.

        Returns:
            The AuditReport if found, or None.
        """
        return self._audit_reports.get(report_id)

    def get_improvement_plan(
        self, plan_id: str
    ) -> Optional[ImprovementPlan]:
        """Retrieve a previously generated improvement plan by ID.

        Args:
            plan_id: The UUID of the improvement plan.

        Returns:
            The ImprovementPlan if found, or None.
        """
        return self._improvement_plans.get(plan_id)

    def list_reports(self) -> List[Dict[str, Any]]:
        """List all audit report summaries.

        Returns:
            List of dictionaries with report id, scene, score, and timestamp.
        """
        return [
            {
                "id": r.id,
                "game_scene": r.game_scene,
                "overall_score": round(r.overall_score, 2),
                "compliance": r.overall_compliance.value,
                "checks_count": len(r.checks),
                "critical_failures": r.critical_failures,
                "audited_at": r.audited_at,
            }
            for r in self._audit_reports.values()
        ]


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_accessibility_auditor() -> AccessibilityAuditor:
    """Return the singleton AccessibilityAuditor instance."""
    return AccessibilityAuditor.get_instance()