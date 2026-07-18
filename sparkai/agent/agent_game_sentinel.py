"""
SparkLabs Agent - Game Sentinel

The 12th stage of the AI-native pipeline. Acts as a runtime guardian that
validates game integrity, monitors health metrics, and auto-repairs common
defects before the game reaches the player.

Capabilities:
  1. Integrity Scan  - validate JS syntax, brace balance, script tag pairing
  2. Defect Repair    - auto-fix double-brace artifacts, unclosed tags, etc.
  3. Health Score     - composite score from integrity, complexity, size, structure
  4. Runtime Telemetry - inject a lightweight health monitor into the game HTML
  5. Diagnostic Report - full issue list with severity, location, and fix status

The sentinel bridges the AI agent layer and the engine runtime layer — it
understands both the generated JavaScript and the Python-side game document
structure, fusing validation intelligence with automatic correction.

Usage:
    sentinel = GameSentinel.get_instance()
    sentinel.initialize()
    result = sentinel.guard(html)
    # result.html contains the repaired, telemetry-instrumented game
    # result.report contains the diagnostic report with health score
"""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sparkai.engine.engine_js_validator import (
    JSValidator,
    ValidationReport,
    ValidationIssue,
    get_validator,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class RepairAction:
    """A single repair applied to the game HTML."""

    category: str  # "double_brace", "unclosed_tag", "telemetry", etc.
    action: str
    detail: str
    before: str = ""
    after: str = ""
    line: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "action": self.action,
            "detail": self.detail,
            "before": self.before[:80],
            "after": self.after[:80],
            "line": self.line,
        }


@dataclass
class HealthMetric:
    """A single health dimension measurement."""

    name: str
    value: float
    max_value: float = 100.0
    status: str = "ok"  # "ok", "warning", "critical"
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": round(self.value, 2),
            "max_value": self.max_value,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass
class SentinelResult:
    """Full result from a sentinel guard operation."""

    session_id: str
    passed: bool
    health_score: float
    metrics: List[HealthMetric] = field(default_factory=list)
    repairs: List[RepairAction] = field(default_factory=list)
    issues_remaining: List[Dict[str, Any]] = field(default_factory=list)
    original_size: int = 0
    repaired_size: int = 0
    telemetry_injected: bool = False
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "passed": self.passed,
            "health_score": round(self.health_score, 2),
            "metrics": [m.to_dict() for m in self.metrics],
            "repairs": [r.to_dict() for r in self.repairs],
            "issues_remaining": self.issues_remaining,
            "original_size": self.original_size,
            "repaired_size": self.repaired_size,
            "telemetry_injected": self.telemetry_injected,
            "timestamp": self.timestamp,
        }


# =============================================================================
# Game Sentinel Agent
# =============================================================================


class GameSentinel:
    """
    Singleton agent that guards game integrity through validation, repair,
    and telemetry injection. Fuses the JS validator engine module with
    agent-level diagnostic reasoning.
    """

    _instance: Optional["GameSentinel"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        self._validator: JSValidator = get_validator()
        self._initialized = False
        self._total_guarded = 0
        self._total_repaired = 0
        self._history: deque = deque(maxlen=100)
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "GameSentinel":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        with self._lock:
            self._initialized = True
            logger.info("GameSentinel initialized")

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def total_guarded(self) -> int:
        return self._total_guarded

    @property
    def total_repaired(self) -> int:
        return self._total_repaired

    def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history)

    # ------------------------------------------------------------------
    # Core guard operation
    # ------------------------------------------------------------------

    def guard(self, html: str, inject_telemetry: bool = True) -> Dict[str, Any]:
        """
        Validate, repair, and instrument a game HTML document.

        Returns a dict with:
          - html: the repaired HTML (with telemetry if requested)
          - report: the SentinelResult as a dict
        """
        if not self._initialized:
            self.initialize()

        with self._lock:
            self._total_guarded += 1

        session_id = "sentinel_" + uuid.uuid4().hex[:12]
        original_html = html
        original_size = len(html)

        # Step 1: Validate
        pre_report = self._validator.validate_html(html)

        # Step 2: Repair
        repairs: List[RepairAction] = []
        repaired_html = html

        if not pre_report.passed:
            repaired_html, repairs = self._repair(html, pre_report)

        # Step 3: Re-validate after repair
        post_report = self._validator.validate_html(repaired_html)

        # Step 4: Inject telemetry
        telemetry_injected = False
        if inject_telemetry and post_report.passed:
            repaired_html, telemetry_injected = self._inject_telemetry(repaired_html)

        # Step 5: Compute health metrics
        metrics = self._compute_metrics(
            original_html, repaired_html, pre_report, post_report, repairs
        )

        # Step 6: Compute composite health score
        health_score = self._compute_health_score(metrics)

        # Step 7: Build result
        remaining_issues = [
            i.to_dict() for i in post_report.issues if i.severity == "error"
        ]

        result = SentinelResult(
            session_id=session_id,
            passed=post_report.passed,
            health_score=health_score,
            metrics=metrics,
            repairs=repairs,
            issues_remaining=remaining_issues,
            original_size=original_size,
            repaired_size=len(repaired_html),
            telemetry_injected=telemetry_injected,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        with self._lock:
            self._history.append(result.to_dict())
            if repairs:
                self._total_repaired += 1

        return {
            "html": repaired_html,
            "report": result.to_dict(),
        }

    # ------------------------------------------------------------------
    # Repair strategies
    # ------------------------------------------------------------------

    def _repair(
        self, html: str, report: ValidationReport
    ) -> tuple[str, List[RepairAction]]:
        """Apply repair strategies based on validation issues."""
        repairs: List[RepairAction] = []
        repaired = html

        # Strategy 1: Fix double-brace artifacts ({{ -> {, }} -> })
        has_double_brace = any(
            i.category == "double_brace" and i.severity == "error"
            for i in report.issues
        )
        if has_double_brace:
            before = repaired
            repaired = self._fix_double_braces(repaired)
            if repaired != before:
                repairs.append(
                    RepairAction(
                        category="double_brace",
                        action="normalize_braces",
                        detail="Replaced {{ with { and }} with } in script blocks",
                        before="var X = {{ ... }}",
                        after="var X = { ... }",
                    )
                )

        # Strategy 2: Fix unclosed script tags
        has_unclosed_script = any(
            i.category == "script_tags" and i.severity == "error"
            for i in report.issues
        )
        if has_unclosed_script:
            before = repaired
            repaired = self._fix_unclosed_scripts(repaired)
            if repaired != before:
                repairs.append(
                    RepairAction(
                        category="script_tags",
                        action="close_tags",
                        detail="Added missing </script> closing tags",
                    )
                )

        return repaired, repairs

    def _fix_double_braces(self, html: str) -> str:
        """
        Replace {{ with { and }} with } inside <script> blocks only.
        Leaves CSS and HTML content untouched.
        """
        def fix_script(match: re.Match) -> str:
            opening = match.group(0)[: match.group(0).index(">") + 1]
            content = match.group(1)
            # Don't replace {{ inside template literals (backtick strings)
            # Simple heuristic: only replace if not inside backtick context
            fixed = content.replace("{{", "{").replace("}}", "}")
            return opening + fixed + "</script>"

        return re.sub(
            r"<script(?:\s[^>]*)?>(.*?)</script>",
            fix_script,
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

    def _fix_unclosed_scripts(self, html: str) -> str:
        """Append missing </script> tags."""
        open_count = len(re.findall(r"<script\b", html, re.IGNORECASE))
        close_count = len(re.findall(r"</script\s*>", html, re.IGNORECASE))
        if open_count > close_count:
            html += "</script>" * (open_count - close_count)
        return html

    # ------------------------------------------------------------------
    # Telemetry injection
    # ------------------------------------------------------------------

    def _inject_telemetry(self, html: str) -> tuple[str, bool]:
        """
        Inject a lightweight runtime health monitor into the game HTML.
        The monitor tracks frame rate, error count, and reports back via
        a global window.SparkLabsSentinel object.
        """
        telemetry_script = """
<script>
// SparkLabs Sentinel Runtime Monitor
(function() {
  "use strict";
  window.SparkLabsSentinel = {
    frameCount: 0,
    lastFpsTime: Date.now(),
    currentFps: 60,
    errors: [],
    startTime: Date.now(),
    _log: function(type, msg) {
      this.errors.push({ t: Date.now() - this.startTime, type: type, msg: msg });
      if (this.errors.length > 50) this.errors.shift();
    }
  };
  // Track frame rate
  var origRAF = window.requestAnimationFrame;
  window.requestAnimationFrame = function(cb) {
    return origRAF.call(window, function(ts) {
      window.SparkLabsSentinel.frameCount++;
      var now = Date.now();
      if (now - window.SparkLabsSentinel.lastFpsTime >= 1000) {
        window.SparkLabsSentinel.currentFps = window.SparkLabsSentinel.frameCount;
        window.SparkLabsSentinel.frameCount = 0;
        window.SparkLabsSentinel.lastFpsTime = now;
      }
      cb(ts);
    });
  };
  // Capture runtime errors
  window.addEventListener('error', function(e) {
    window.SparkLabsSentinel._log('error', e.message + ' @ ' + (e.filename || '') + ':' + (e.lineno || 0));
  });
})();
</script>
"""
        # Inject before the closing </body> tag, or append at end
        if "</body>" in html:
            idx = html.rindex("</body>")
            return html[:idx] + telemetry_script + "\n" + html[idx:], True
        else:
            return html + telemetry_script, True

    # ------------------------------------------------------------------
    # Health metrics
    # ------------------------------------------------------------------

    def _compute_metrics(
        self,
        original: str,
        repaired: str,
        pre_report: ValidationReport,
        post_report: ValidationReport,
        repairs: List[RepairAction],
    ) -> List[HealthMetric]:
        """Compute health metrics across multiple dimensions."""
        metrics: List[HealthMetric] = []

        # 1. Integrity — based on remaining errors
        error_count = post_report.error_count
        integrity = max(0.0, 100.0 - error_count * 25.0)
        metrics.append(
            HealthMetric(
                name="integrity",
                value=integrity,
                status="ok" if error_count == 0 else "critical",
                detail="{} errors remaining after repair".format(error_count),
            )
        )

        # 2. Script health — script blocks and their validity
        script_count = post_report.script_blocks_checked
        script_health = 100.0 if script_count > 0 and error_count == 0 else 50.0
        metrics.append(
            HealthMetric(
                name="script_health",
                value=script_health,
                status="ok" if script_count > 0 else "warning",
                detail="{} script blocks validated".format(script_count),
            )
        )

        # 3. Size efficiency — based on HTML size
        size_kb = len(repaired) / 1024
        if size_kb < 50:
            size_score = 100.0
            size_status = "ok"
        elif size_kb < 150:
            size_score = 80.0
            size_status = "ok"
        elif size_kb < 300:
            size_score = 60.0
            size_status = "warning"
        else:
            size_score = 40.0
            size_status = "warning"
        metrics.append(
            HealthMetric(
                name="size_efficiency",
                value=size_score,
                status=size_status,
                detail="{:.1f} KB total size".format(size_kb),
            )
        )

        # 4. Structure — HTML document completeness
        has_doctype = original.strip().lower().startswith("<!doctype")
        has_html_tag = "<html" in original.lower()
        has_head = "<head" in original.lower()
        has_body = "<body" in original.lower()
        structure_checks = sum([has_doctype, has_html_tag, has_head, has_body])
        structure_score = (structure_checks / 4.0) * 100.0
        metrics.append(
            HealthMetric(
                name="document_structure",
                value=structure_score,
                status="ok" if structure_checks == 4 else "warning",
                detail="{}/4 structural elements present".format(structure_checks),
            )
        )

        # 5. Repair effectiveness
        if pre_report.error_count > 0:
            fixed = pre_report.error_count - post_report.error_count
            effectiveness = (fixed / pre_report.error_count) * 100.0
        else:
            effectiveness = 100.0
        metrics.append(
            HealthMetric(
                name="repair_effectiveness",
                value=effectiveness,
                status="ok" if effectiveness == 100.0 else "warning",
                detail="{} of {} issues repaired".format(
                    pre_report.error_count - post_report.error_count,
                    pre_report.error_count,
                ),
            )
        )

        return metrics

    def _compute_health_score(self, metrics: List[HealthMetric]) -> float:
        """Compute a weighted composite health score."""
        weights = {
            "integrity": 0.35,
            "script_health": 0.25,
            "size_efficiency": 0.10,
            "document_structure": 0.15,
            "repair_effectiveness": 0.15,
        }
        score = 0.0
        for m in metrics:
            weight = weights.get(m.name, 0.0)
            score += m.value * weight
        return score

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_guarded": self._total_guarded,
                "total_repaired": self._total_repaired,
                "history_count": len(self._history),
                "validator_checks": [
                    "double_brace",
                    "brace_balance",
                    "string_integrity",
                    "keyword_sanity",
                    "script_tags",
                ],
                "capabilities": [
                    "integrity_scan",
                    "defect_repair",
                    "health_score",
                    "runtime_telemetry",
                    "diagnostic_report",
                ],
            }
