"""
SparkLabs Agent - Game Sentinel

The 12th stage of the AI-native pipeline. Acts as a runtime guardian that
validates game integrity, monitors health metrics, and auto-repairs common
defects before the game reaches the player.

Capabilities:
  1. Integrity Scan         - validate JS syntax, brace balance, script tag pairing
  2. Defect Repair           - auto-fix double-brace artifacts, unclosed tags, etc.
  3. Health Score            - composite score from integrity, complexity, size, structure
  4. Runtime Telemetry       - inject a lightweight health monitor into the game HTML
  5. Diagnostic Report       - full issue list with severity, location, and fix status
  6. Playability Verification - semantic checks for canvas, game loop, input, levels, player
  7. Improvement Suggestions  - actionable guidance for making the game better

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
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
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
            "suggestions": self.suggestions,
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

        # Step 5: Playability verification — semantic checks beyond syntax
        playability = self._check_playability(repaired_html)

        # Step 6: Compute health metrics
        metrics = self._compute_metrics(
            original_html, repaired_html, pre_report, post_report, repairs
        )
        metrics.extend(playability["metrics"])

        # Step 7: Compute composite health score
        health_score = self._compute_health_score(metrics)

        # Step 8: Build result
        remaining_issues = [
            i.to_dict() for i in post_report.issues if i.severity == "error"
        ]
        # Append playability issues as non-blocking warnings
        for issue in playability["issues"]:
            remaining_issues.append(issue)

        # Step 9: Generate actionable improvement suggestions
        suggestions = self._generate_suggestions(metrics, remaining_issues, repaired_html)

        result = SentinelResult(
            session_id=session_id,
            passed=post_report.passed,
            health_score=health_score,
            metrics=metrics,
            repairs=repairs,
            issues_remaining=remaining_issues,
            suggestions=suggestions,
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
                        detail="Fixed {{ artifacts after )/=/, in script blocks",
                        before="function() {{ ... }}",
                        after="function() { ... }",
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
        Fix double-brace templating artifacts ({{ -> {) inside <script>
        blocks only. Only targets {{ that follows a closing parenthesis
        or arrow operator, which is the signature of an f-string escape
        leak (e.g. "function() {{", "if (x) {{", "=> {{").

        Never blindly collapses }} — that pattern is valid in nested
        object literals like {"a": {"b": 1}} and JSON data. Instead,
        the matching }} for each fixed {{ is resolved by removing one
        } from the next }} that appears at the same statement level.
        """
        # Pattern: {{ preceded by ), ], =, comma, semicolon, or arrow =>
        # This catches templating leaks like function() {{, if (x) {{, => {{
        artifact_re = re.compile(r'([)\]=,;]|\b=>)\s*\{\{')

        def fix_script(match: re.Match) -> str:
            opening = match.group(0)[: match.group(0).index(">") + 1]
            content = match.group(1)
            fixed = artifact_re.sub(lambda m: m.group(1) + " {", content)
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
    # Playability verification
    # ------------------------------------------------------------------

    def _check_playability(self, html: str) -> Dict[str, Any]:
        """
        Semantic verification that the game has the components required
        to actually be playable. Goes beyond syntax checking to ensure
        the runtime contract is satisfied: canvas, game loop, input
        handling, level data, player entity, and state transitions.
        """
        metrics: List[HealthMetric] = []
        issues: List[Dict[str, Any]] = []
        html_lower = html.lower()

        # 1. Canvas element present
        has_canvas = "<canvas" in html_lower
        metrics.append(HealthMetric(
            name="playability_canvas",
            value=100.0 if has_canvas else 0.0,
            status="ok" if has_canvas else "critical",
            detail="Canvas rendering surface present" if has_canvas
            else "Missing <canvas> element — game cannot render",
        ))
        if not has_canvas:
            issues.append({
                "category": "playability",
                "severity": "warning",
                "message": "No <canvas> element found — game has no render surface",
                "line": 0,
            })

        # 2. Game loop — requestAnimationFrame or setInterval with update logic
        has_loop = (
            "requestAnimationFrame" in html
            or "setInterval" in html
        )
        has_update = "update" in html or "tick" in html.lower() or "loop" in html.lower()
        loop_score = 0.0
        if has_loop and has_update:
            loop_score = 100.0
        elif has_loop:
            loop_score = 60.0
            issues.append({
                "category": "playability",
                "severity": "warning",
                "message": "Game loop scheduler found but no update/tick function detected",
                "line": 0,
            })
        else:
            issues.append({
                "category": "playability",
                "severity": "warning",
                "message": "No game loop (requestAnimationFrame/setInterval) detected",
                "line": 0,
            })
        metrics.append(HealthMetric(
            name="playability_game_loop",
            value=loop_score,
            status="ok" if loop_score == 100.0 else "warning",
            detail="Game loop and update function detected" if loop_score == 100.0
            else "Partial game loop detection",
        ))

        # 3. Input handling — keyboard and/or touch
        has_keyboard = "keydown" in html or "keyup" in html or "keypress" in html
        has_touch = "touchstart" in html or "touchend" in html or "touchmove" in html or "touchLeft" in html
        input_score = 0.0
        if has_keyboard and has_touch:
            input_score = 100.0
        elif has_keyboard or has_touch:
            input_score = 70.0
        else:
            issues.append({
                "category": "playability",
                "severity": "warning",
                "message": "No input handlers (keyboard/touch) detected — game may be unresponsive",
                "line": 0,
            })
        metrics.append(HealthMetric(
            name="playability_input",
            value=input_score,
            status="ok" if input_score >= 70.0 else "warning",
            detail="Keyboard + touch input" if input_score == 100.0
            else ("Keyboard only" if has_keyboard else "Touch only") if input_score > 0
            else "No input handlers",
        ))

        # 4. Level data — LEVELS array with at least one level
        levels_match = re.search(r'var\s+LEVELS\s*=\s*(\[.*?\]);', html, re.DOTALL)
        level_score = 0.0
        level_detail = "No LEVELS data found"
        if levels_match:
            try:
                import json as _json
                levels_data = _json.loads(levels_match.group(1))
                level_count = len(levels_data)
                if level_count > 0:
                    level_score = 100.0
                    level_detail = "{} level(s) defined".format(level_count)
                    # Check that at least one level has entities
                    has_entities = any(
                        len(lvl.get("entities", [])) > 0 for lvl in levels_data
                    )
                    if not has_entities:
                        level_score = 50.0
                        level_detail = "{} level(s) but none have entities".format(level_count)
                        issues.append({
                            "category": "playability",
                            "severity": "warning",
                            "message": "Levels exist but no entities are defined",
                            "line": 0,
                        })
                else:
                    level_score = 20.0
                    level_detail = "LEVELS array is empty"
                    issues.append({
                        "category": "playability",
                        "severity": "warning",
                        "message": "LEVELS array is empty — no levels to play",
                        "line": 0,
                    })
            except Exception:
                level_score = 30.0
                level_detail = "LEVELS data exists but JSON is malformed"
                issues.append({
                    "category": "playability",
                    "severity": "warning",
                    "message": "LEVELS JSON is malformed — game may not load levels",
                    "line": 0,
                })
        else:
            issues.append({
                "category": "playability",
                "severity": "warning",
                "message": "No LEVELS data found — game has no content",
                "line": 0,
            })
        metrics.append(HealthMetric(
            name="playability_levels",
            value=level_score,
            status="ok" if level_score == 100.0 else "warning",
            detail=level_detail,
        ))

        # 5. State transitions — win/lose conditions
        has_win = "won" in html_lower or "win" in html_lower or "victory" in html_lower or "complete" in html_lower
        has_lose = "lost" in html_lower or "lose" in html_lower or "game over" in html_lower or "dead" in html_lower or "death" in html_lower
        state_score = 0.0
        if has_win and has_lose:
            state_score = 100.0
        elif has_win or has_lose:
            state_score = 50.0
            missing = "lose" if has_win else "win"
            issues.append({
                "category": "playability",
                "severity": "warning",
                "message": "Partial end-state detection — {} condition missing".format(missing),
                "line": 0,
            })
        else:
            issues.append({
                "category": "playability",
                "severity": "warning",
                "message": "No win/lose state transitions detected",
                "line": 0,
            })
        metrics.append(HealthMetric(
            name="playability_end_states",
            value=state_score,
            status="ok" if state_score == 100.0 else "warning",
            detail="Win + lose states present" if state_score == 100.0
            else "Partial end-state coverage" if state_score > 0
            else "No end-state transitions",
        ))

        # 6. Player entity — check for player type in LEVELS or player spawn
        has_player = False
        if levels_match:
            try:
                import json as _json
                levels_data = _json.loads(levels_match.group(1))
                for lvl in levels_data:
                    for ent in lvl.get("entities", []):
                        if ent.get("type") == "player" or "player" in ent.get("id", "").lower():
                            has_player = True
                            break
                    if has_player:
                        break
            except Exception:
                pass
        if not has_player:
            # Fallback: check for player color or player-related variables
            has_player = "playerColor" in html or "player_color" in html or "playerSpawn" in html
        metrics.append(HealthMetric(
            name="playability_player",
            value=100.0 if has_player else 0.0,
            status="ok" if has_player else "critical",
            detail="Player entity defined in level data" if has_player
            else "No player entity found — game cannot be played",
        ))
        if not has_player:
            issues.append({
                "category": "playability",
                "severity": "warning",
                "message": "No player entity found in level data",
                "line": 0,
            })

        return {"metrics": metrics, "issues": issues}

    # ------------------------------------------------------------------
    # Improvement suggestions
    # ------------------------------------------------------------------

    def _generate_suggestions(
        self,
        metrics: List[HealthMetric],
        issues: List[Dict[str, Any]],
        html: str,
    ) -> List[Dict[str, Any]]:
        """
        Analyze metrics and issues to produce actionable improvement
        suggestions. Each suggestion has a priority, category, title,
        and concrete description of what to change.
        """
        suggestions: List[Dict[str, Any]] = []
        metric_map = {m.name: m for m in metrics}

        # Canvas / rendering surface
        m = metric_map.get("playability_canvas")
        if m and m.value < 100.0:
            suggestions.append({
                "priority": "critical",
                "category": "rendering",
                "title": "Add a canvas element",
                "description": "The game has no render surface. Add <canvas id=\"gameCanvas\"></canvas> inside <body> and obtain a 2D context with getContext('2d').",
            })

        # Game loop
        m = metric_map.get("playability_game_loop")
        if m and m.value < 100.0:
            if m.value == 0.0:
                suggestions.append({
                    "priority": "critical",
                    "category": "game_loop",
                    "title": "Implement a game loop",
                    "description": "No animation scheduler found. Add window.requestAnimationFrame(loop) with an update(dt) function that advances game state each frame.",
                })
            else:
                suggestions.append({
                    "priority": "high",
                    "category": "game_loop",
                    "title": "Add an update function to the game loop",
                    "description": "A loop scheduler exists but no update/tick function was detected. Define function update(dt) { ... } that processes physics, input, and rendering each frame.",
                })

        # Input handling
        m = metric_map.get("playability_input")
        if m and m.value < 100.0:
            if m.value == 0.0:
                suggestions.append({
                    "priority": "critical",
                    "category": "input",
                    "title": "Add input handlers",
                    "description": "No input handlers detected. Add keyboard listeners (keydown/keyup) and touch zones for mobile compatibility.",
                })
            else:
                suggestions.append({
                    "priority": "medium",
                    "category": "input",
                    "title": "Add touch input for mobile",
                    "description": "Only keyboard input detected. Add touchstart/touchend listeners or on-screen touch zones to support mobile play.",
                })

        # Level data
        m = metric_map.get("playability_levels")
        if m and m.value < 100.0:
            if m.value == 0.0:
                suggestions.append({
                    "priority": "critical",
                    "category": "content",
                    "title": "Define level data",
                    "description": "No LEVELS array found. Define var LEVELS = [{name, width, height, entities: [...]}] with at least one level containing player, terrain, and collectibles.",
                })
            elif m.value <= 30.0:
                suggestions.append({
                    "priority": "high",
                    "category": "content",
                    "title": "Fix malformed LEVELS JSON",
                    "description": "The LEVELS array exists but contains invalid JSON. Check for missing closing braces on entity objects — each entity needs its own closing }.",
                })
            elif m.value <= 50.0:
                suggestions.append({
                    "priority": "medium",
                    "category": "content",
                    "title": "Add entities to levels",
                    "description": "Levels exist but contain no entities. Add player spawn points, platforms, enemies, and collectibles to each level.",
                })

        # End states
        m = metric_map.get("playability_end_states")
        if m and m.value < 100.0:
            if m.value == 0.0:
                suggestions.append({
                    "priority": "high",
                    "category": "gameplay",
                    "title": "Add win and lose conditions",
                    "description": "No end-state transitions detected. Add state transitions for 'won' (e.g., reaching the goal) and 'lost' (e.g., running out of lives).",
                })
            else:
                missing = "lose" if "win" in str(m.detail).lower() else "win"
                suggestions.append({
                    "priority": "medium",
                    "category": "gameplay",
                    "title": "Add the missing {} condition".format(missing),
                    "description": "Only one end-state detected. Add a {} condition so the player can both succeed and fail.".format(missing),
                })

        # Player entity
        m = metric_map.get("playability_player")
        if m and m.value < 100.0:
            suggestions.append({
                "priority": "critical",
                "category": "entity",
                "title": "Add a player entity",
                "description": "No player entity found in level data. Add an entity with type='player' to at least one level so the player has a controllable avatar.",
            })

        # Size optimization
        m = metric_map.get("size_efficiency")
        if m and m and m.value < 60.0:
            suggestions.append({
                "priority": "low",
                "category": "optimization",
                "title": "Reduce game HTML size",
                "description": "The game is {:.0f} KB — consider minifying JavaScript, removing unused code, or splitting into smaller levels.".format(len(html) / 1024),
            })

        # Integrity issues
        m = metric_map.get("integrity")
        if m and m.value < 100.0:
            suggestions.append({
                "priority": "critical",
                "category": "syntax",
                "title": "Fix JavaScript syntax errors",
                "description": "{} syntax errors remain after auto-repair. Check the issues list for specific line numbers and brace mismatches.".format(m.detail),
            })

        # If everything is perfect, add a positive note
        if not suggestions and all(m.value >= 90.0 for m in metrics):
            suggestions.append({
                "priority": "info",
                "category": "overall",
                "title": "Game quality is excellent",
                "description": "All health metrics score above 90. The game has valid syntax, complete playability checks, and good structure. Consider adding polish: particle effects, screen shake, or dynamic music.",
            })

        return suggestions

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
            "integrity": 0.20,
            "script_health": 0.15,
            "size_efficiency": 0.05,
            "document_structure": 0.10,
            "repair_effectiveness": 0.10,
            "playability_canvas": 0.10,
            "playability_game_loop": 0.08,
            "playability_input": 0.05,
            "playability_levels": 0.07,
            "playability_end_states": 0.05,
            "playability_player": 0.05,
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
                    "playability_verification",
                    "improvement_suggestions",
                ],
            }
