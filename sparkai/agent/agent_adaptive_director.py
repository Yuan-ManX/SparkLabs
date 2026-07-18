"""
SparkLabs Agent - Adaptive Difficulty Director

Monitors player performance in real-time and dynamically adjusts
game parameters to maintain optimal challenge. Unlike static
difficulty settings, the Adaptive Director continuously observes
player behavior — deaths, completion speed, collectible ratio,
damage taken — and modulates enemy speed, spawn rates, collectible
placement, and damage values to keep the player in the flow zone.

This module generates adaptation rules as executable JavaScript
that hooks into the game runtime's update loop, reading from
window.gameState and writing adjustments back to CONFIG and
entity properties.

Architecture:
  AdaptiveDirector (singleton)
    |-- MetricTracker   -> defines which player metrics to monitor
    |-- SkillClassifier -> maps metric patterns to skill levels
    |-- RuleSynthesizer -> generates adaptation rules from game design
    |-- JsInjector      -> compiles rules to executable browser JS
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class PlayerMetric:
    """A player behavior metric to track."""
    name: str
    description: str
    initial_value: float
    window_seconds: float = 30.0


@dataclass
class AdaptationRule:
    """A single adaptation rule: condition -> action."""
    rule_id: str
    metric: str
    operator: str  # greater, less, equal
    threshold: float
    action: str  # increase_difficulty, decrease_difficulty, spawn_bonus, show_hint
    intensity: float  # 0.0 to 1.0
    description: str = ""


@dataclass
class AdaptiveProfile:
    """A complete adaptive difficulty profile for a game."""
    profile_id: str
    game_prompt: str
    skill_levels: List[str]  # beginner, intermediate, expert
    metrics: List[PlayerMetric]
    rules: List[AdaptationRule]
    flow_zone_min: float  # optimal challenge range
    flow_zone_max: float
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "game_prompt": self.game_prompt,
            "skill_levels": self.skill_levels,
            "metrics": [
                {"name": m.name, "description": m.description, "initial_value": m.initial_value}
                for m in self.metrics
            ],
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "metric": r.metric,
                    "operator": r.operator,
                    "threshold": r.threshold,
                    "action": r.action,
                    "intensity": r.intensity,
                    "description": r.description,
                }
                for r in self.rules
            ],
            "flow_zone_min": self.flow_zone_min,
            "flow_zone_max": self.flow_zone_max,
            "created_at": self.created_at,
        }


@dataclass
class AdaptiveResult:
    """Result of an adaptive direction run."""
    success: bool
    profile: Optional[AdaptiveProfile]
    js_code: str
    duration_s: float
    session_id: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "profile": self.profile.to_dict() if self.profile else None,
            "js_length": len(self.js_code),
            "duration_s": round(self.duration_s, 4),
            "session_id": self.session_id,
            "error": self.error,
        }


# =============================================================================
# Metric Tracker - Default metrics for any game
# =============================================================================


class MetricTracker:
    """Defines the standard set of player metrics to monitor."""

    @staticmethod
    def default_metrics() -> List[PlayerMetric]:
        return [
            PlayerMetric(
                name="death_rate",
                description="Deaths per minute — measures frustration level",
                initial_value=0.0,
                window_seconds=60.0,
            ),
            PlayerMetric(
                name="collect_ratio",
                description="Percentage of collectibles gathered — measures exploration",
                initial_value=0.0,
                window_seconds=0.0,
            ),
            PlayerMetric(
                name="damage_taken",
                description="Total damage taken in current level",
                initial_value=0.0,
                window_seconds=0.0,
            ),
            PlayerMetric(
                name="level_time",
                description="Seconds spent in current level — measures pacing",
                initial_value=0.0,
                window_seconds=0.0,
            ),
            PlayerMetric(
                name="score_velocity",
                description="Score gained per second — measures engagement",
                initial_value=0.0,
                window_seconds=10.0,
            ),
        ]


# =============================================================================
# Skill Classifier
# =============================================================================


class SkillClassifier:
    """Maps player metric patterns to skill levels."""

    LEVELS = ["beginner", "intermediate", "expert"]

    @staticmethod
    def classify(metrics: Dict[str, float]) -> str:
        """Classify player skill from current metric values."""
        death_rate = metrics.get("death_rate", 0)
        collect_ratio = metrics.get("collect_ratio", 0)
        score_velocity = metrics.get("score_velocity", 0)

        # High death rate and low collection = beginner
        if death_rate > 2.0 or collect_ratio < 0.3:
            return "beginner"
        # Low death rate and high collection = expert
        if death_rate < 0.5 and collect_ratio > 0.7 and score_velocity > 20:
            return "expert"
        return "intermediate"


# =============================================================================
# Rule Synthesizer
# =============================================================================


class RuleSynthesizer:
    """Generates adaptation rules based on game prompt and genre."""

    # Genre-specific rule templates
    GENRE_RULES: Dict[str, List[Dict[str, Any]]] = {
        "platformer": [
            {"metric": "death_rate", "operator": "greater", "threshold": 3.0,
             "action": "decrease_difficulty", "intensity": 0.3,
             "description": "Too many deaths — slow enemies and add platforms"},
            {"metric": "death_rate", "operator": "less", "threshold": 0.3,
             "action": "increase_difficulty", "intensity": 0.2,
             "description": "Player is breezing through — speed up enemies"},
            {"metric": "collect_ratio", "operator": "less", "threshold": 0.3,
             "action": "spawn_bonus", "intensity": 0.5,
             "description": "Low collection — spawn bonus collectibles near player"},
        ],
        "shooter": [
            {"metric": "death_rate", "operator": "greater", "threshold": 2.5,
             "action": "decrease_difficulty", "intensity": 0.35,
             "description": "High death rate — reduce enemy spawn rate"},
            {"metric": "score_velocity", "operator": "less", "threshold": 10.0,
             "action": "spawn_bonus", "intensity": 0.4,
             "description": "Low engagement — spawn bonus targets"},
            {"metric": "death_rate", "operator": "less", "threshold": 0.3,
             "action": "increase_difficulty", "intensity": 0.25,
             "description": "Player dominating — increase enemy speed and count"},
        ],
        "puzzle": [
            {"metric": "level_time", "operator": "greater", "threshold": 120.0,
             "action": "show_hint", "intensity": 0.6,
             "description": "Stuck too long — reveal a hint"},
            {"metric": "level_time", "operator": "less", "threshold": 15.0,
             "action": "increase_difficulty", "intensity": 0.2,
             "description": "Solving too fast — increase complexity"},
        ],
    }

    DEFAULT_RULES: List[Dict[str, Any]] = [
        {"metric": "death_rate", "operator": "greater", "threshold": 3.0,
         "action": "decrease_difficulty", "intensity": 0.3,
         "description": "High frustration — reduce enemy speed"},
        {"metric": "death_rate", "operator": "less", "threshold": 0.3,
         "action": "increase_difficulty", "intensity": 0.2,
         "description": "Low challenge — increase enemy speed"},
        {"metric": "collect_ratio", "operator": "less", "threshold": 0.3,
         "action": "spawn_bonus", "intensity": 0.5,
         "description": "Low exploration — spawn bonus items"},
        {"metric": "score_velocity", "operator": "less", "threshold": 5.0,
         "action": "show_hint", "intensity": 0.4,
         "description": "Low engagement — show directional hint"},
    ]

    def synthesize(self, prompt: str) -> List[AdaptationRule]:
        """Generate adaptation rules from the game prompt."""
        prompt_lower = prompt.lower()

        # Detect genre from prompt keywords
        genre = "default"
        if any(kw in prompt_lower for kw in ["platform", "jump", "side-scroll"]):
            genre = "platformer"
        elif any(kw in prompt_lower for kw in ["shoot", "gun", "bullet", "space"]):
            genre = "shooter"
        elif any(kw in prompt_lower for kw in ["puzzle", "match", "logic", "block"]):
            genre = "puzzle"

        templates = self.GENRE_RULES.get(genre, self.DEFAULT_RULES)
        rules: List[AdaptationRule] = []

        for tmpl in templates:
            rules.append(AdaptationRule(
                rule_id=f"rule_{uuid.uuid4().hex[:8]}",
                metric=tmpl["metric"],
                operator=tmpl["operator"],
                threshold=float(tmpl["threshold"]),
                action=tmpl["action"],
                intensity=float(tmpl["intensity"]),
                description=tmpl["description"],
            ))

        return rules


# =============================================================================
# JS Injector - Compile rules to executable browser JavaScript
# =============================================================================


class JsInjector:
    """Compiles adaptation rules into executable JavaScript for the browser."""

    @staticmethod
    def build_js(profile: AdaptiveProfile) -> str:
        """Generate the complete adaptive difficulty JavaScript.

        The JS hooks into the game loop, tracks player metrics,
        classifies skill level, and applies adaptation actions.
        """
        rules_json = _json_dumps_rules(profile.rules)
        flow_min = profile.flow_zone_min
        flow_max = profile.flow_zone_max

        # Use placeholder substitution to avoid f-string brace conflicts
        js = '''<script>
// SparkLabs Adaptive Difficulty Director - real-time player adaptation
(function() {
  var SL_ADAPT_RULES = __RULES_JSON__;
  var SL_FLOW_MIN = __FLOW_MIN__;
  var SL_FLOW_MAX = __FLOW_MAX__;
  var SL_ADAPT_STATE = {
    death_count: 0,
    level_start_time: Date.now(),
    last_score: 0,
    last_score_time: Date.now(),
    score_history: [],
    collectibles_total: 0,
    collectibles_gathered: 0,
    skill_level: 'intermediate',
    adapt_cooldown: 0,
    hint_shown: false,
  };

  function sl_adapt_trackDeath() {
    SL_ADAPT_STATE.death_count++;
  }

  function sl_adapt_trackCollect(gathered, total) {
    SL_ADAPT_STATE.collectibles_gathered = gathered;
    SL_ADAPT_STATE.collectibles_total = total;
  }

  function sl_adapt_computeMetrics() {
    var now = Date.now();
    var elapsed_s = (now - SL_ADAPT_STATE.level_start_time) / 1000;
    var gs = window.gameState || {};

    // Death rate: deaths per minute
    var death_rate = elapsed_s > 0 ? (SL_ADAPT_STATE.death_count / elapsed_s) * 60 : 0;

    // Collect ratio
    var collect_ratio = SL_ADAPT_STATE.collectibles_total > 0
      ? SL_ADAPT_STATE.collectibles_gathered / SL_ADAPT_STATE.collectibles_total : 0;

    // Score velocity: score gained per second over last 10s
    var score_now = gs.score || 0;
    var score_dt = (now - SL_ADAPT_STATE.last_score_time) / 1000;
    var score_delta = score_now - SL_ADAPT_STATE.last_score;
    var score_velocity = score_dt > 0 ? score_delta / score_dt : 0;
    SL_ADAPT_STATE.score_history.push({ t: now, s: score_now });
    if (SL_ADAPT_STATE.score_history.length > 60) SL_ADAPT_STATE.score_history.shift();
    SL_ADAPT_STATE.last_score = score_now;
    SL_ADAPT_STATE.last_score_time = now;

    // Level time
    var level_time = elapsed_s;

    // Damage taken (from gameState if available)
    var damage_taken = gs.damage_taken || 0;

    return {
      death_rate: death_rate,
      collect_ratio: collect_ratio,
      score_velocity: score_velocity,
      level_time: level_time,
      damage_taken: damage_taken,
    };
  }

  function sl_adapt_classifySkill(metrics) {
    if (metrics.death_rate > 2.0 || metrics.collect_ratio < 0.3) return 'beginner';
    if (metrics.death_rate < 0.5 && metrics.collect_ratio > 0.7 && metrics.score_velocity > 20) return 'expert';
    return 'intermediate';
  }

  function sl_adapt_checkRule(rule, metrics) {
    var val = metrics[rule.metric] || 0;
    if (rule.operator === 'greater') return val > rule.threshold;
    if (rule.operator === 'less') return val < rule.threshold;
    if (rule.operator === 'equal') return Math.abs(val - rule.threshold) < 0.1;
    return false;
  }

  function sl_adapt_applyAction(rule) {
    var intensity = rule.intensity || 0.3;
    var gs = window.gameState || {};

    if (rule.action === 'decrease_difficulty') {
      // Slow down enemies and reduce spawn rate
      if (typeof CONFIG !== 'undefined') {
        CONFIG.enemySpeed = Math.max(0.5, (CONFIG.enemySpeed || 1.5) * (1 - intensity * 0.3));
      }
      sl_adapt_log('Adaptive: decreasing difficulty (' + rule.description + ')');
    } else if (rule.action === 'increase_difficulty') {
      // Speed up enemies and increase challenge
      if (typeof CONFIG !== 'undefined') {
        CONFIG.enemySpeed = Math.min(6.0, (CONFIG.enemySpeed || 1.5) * (1 + intensity * 0.3));
      }
      sl_adapt_log('Adaptive: increasing difficulty (' + rule.description + ')');
    } else if (rule.action === 'spawn_bonus') {
      // Spawn a bonus collectible near the player
      if (typeof spawnEntity === 'function') {
        spawnEntity('collectible');
        spawnEntity('collectible');
      }
      sl_adapt_log('Adaptive: spawning bonus items (' + rule.description + ')');
    } else if (rule.action === 'show_hint') {
      // Show a brief on-screen hint
      if (!SL_ADAPT_STATE.hint_shown) {
        sl_adapt_showHint(rule.description);
        SL_ADAPT_STATE.hint_shown = true;
        setTimeout(function() { SL_ADAPT_STATE.hint_shown = false; }, 15000);
      }
    }
  }

  function sl_adapt_log(msg) {
    if (typeof console !== 'undefined' && console.debug) {
      console.debug('[SparkLabs Adaptive] ' + msg);
    }
  }

  function sl_adapt_showHint(text) {
    try {
      var ctx = document.getElementById('gameCanvas');
      if (!ctx) ctx = document.querySelector('canvas');
      if (!ctx) return;
      var div = document.createElement('div');
      div.style.cssText = 'position:fixed;top:15%;left:50%;transform:translateX(-50%);background:rgba(10,10,10,0.9);color:#f97316;padding:10px 20px;border-radius:8px;font:13px sans-serif;z-index:9999;border:1px solid rgba(249,115,22,0.4);transition:opacity 0.5s';
      div.textContent = text;
      document.body.appendChild(div);
      setTimeout(function() { div.style.opacity = '0'; }, 4000);
      setTimeout(function() { if (div.parentNode) div.parentNode.removeChild(div); }, 5000);
    } catch(e) {}
  }

  function sl_adapt_evaluate() {
    if (SL_ADAPT_COOLDOWN > 0) { SL_ADAPT_COOLDOWN--; return; }
    var metrics = sl_adapt_computeMetrics();
    var skill = sl_adapt_classifySkill(metrics);
    if (skill !== SL_ADAPT_STATE.skill_level) {
      SL_ADAPT_STATE.skill_level = skill;
      sl_adapt_log('Skill level changed to: ' + skill);
    }

    var any_fired = false;
    for (var i = 0; i < SL_ADAPT_RULES.length; i++) {
      if (sl_adapt_checkRule(SL_ADAPT_RULES[i], metrics)) {
        sl_adapt_applyAction(SL_ADAPT_RULES[i]);
        any_fired = true;
      }
    }

    // Cooldown after applying adaptations to prevent oscillation
    if (any_fired) SL_ADAPT_COOLDOWN = 90; // ~1.5s at 60fps
  }

  var SL_ADAPT_COOLDOWN = 0;

  // Hook into game loop
  var sl_origUpdate = typeof window.update === 'function' ? window.update : null;
  if (sl_origUpdate) {
    window.update = function(dt) {
      sl_origUpdate(dt);
      sl_adapt_evaluate();
    };
  } else {
    setInterval(sl_adapt_evaluate, 500);
  }

  // Reset metrics on level change
  var sl_origLoadLevel = typeof window.loadLevel === 'function' ? window.loadLevel : null;
  if (sl_origLoadLevel) {
    window.loadLevel = function(idx) {
      SL_ADAPT_STATE.death_count = 0;
      SL_ADAPT_STATE.level_start_time = Date.now();
      SL_ADAPT_STATE.hint_shown = false;
      sl_origLoadLevel(idx);
    };
  }

  // Track deaths by hooking into loseLife
  var sl_origLoseLife = typeof window.loseLife === 'function' ? window.loseLife : null;
  if (sl_origLoseLife) {
    window.loseLife = function() {
      sl_adapt_trackDeath();
      sl_origLoseLife();
    };
  }

  // Expose for debugging
  window.SparkLabsAdaptive = {
    state: SL_ADAPT_STATE,
    rules: SL_ADAPT_RULES,
    evaluate: sl_adapt_evaluate,
    getMetrics: sl_adapt_computeMetrics,
    getSkill: function() { return SL_ADAPT_STATE.skill_level; },
  };
})();
</script>'''

        js = js.replace("__RULES_JSON__", rules_json)
        js = js.replace("__FLOW_MIN__", str(flow_min))
        js = js.replace("__FLOW_MAX__", str(flow_max))
        return js


def _json_dumps_rules(rules: List[AdaptationRule]) -> str:
    """Serialize rules to JSON without external dependency issues."""
    import json
    return json.dumps([
        {
            "rule_id": r.rule_id,
            "metric": r.metric,
            "operator": r.operator,
            "threshold": r.threshold,
            "action": r.action,
            "intensity": r.intensity,
            "description": r.description,
        }
        for r in rules
    ])


# =============================================================================
# Adaptive Director (Singleton)
# =============================================================================


class AdaptiveDirector:
    """
    Top-level director that generates adaptive difficulty profiles
    and compiles them to executable JavaScript for game HTML injection.
    """

    _instance: Optional["AdaptiveDirector"] = None
    _lock = threading.RLock()

    def __init__(self):
        self._tracker = MetricTracker()
        self._classifier = SkillClassifier()
        self._synthesizer = RuleSynthesizer()
        self._injector = JsInjector()
        self._history: List[Dict[str, Any]] = []
        self._initialized: bool = False

    @classmethod
    def get_instance(cls) -> "AdaptiveDirector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        self._initialized = True
        logger.info("AdaptiveDirector initialized")

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "history_count": len(self._history),
            "default_metrics": len(self._tracker.default_metrics()),
        }

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)

    def generate(self, prompt: str) -> AdaptiveResult:
        """Generate an adaptive difficulty profile and JS code for a game.

        Args:
            prompt: The game description prompt (same as conductor prompt)

        Returns:
            AdaptiveResult with the profile and executable JS
        """
        start = time.time()
        session_id = f"adapt_{uuid.uuid4().hex[:12]}"

        if not self._initialized:
            self.initialize()

        if not prompt or not prompt.strip():
            return AdaptiveResult(
                success=False, profile=None, js_code="",
                duration_s=0.0, session_id=session_id,
                error="Prompt is required",
            )

        try:
            # Generate metrics
            metrics = self._tracker.default_metrics()

            # Synthesize rules
            rules = self._synthesizer.synthesize(prompt)

            # Create profile
            profile = AdaptiveProfile(
                profile_id=f"prof_{uuid.uuid4().hex[:12]}",
                game_prompt=prompt,
                skill_levels=self._classifier.LEVELS,
                metrics=metrics,
                rules=rules,
                flow_zone_min=0.4,
                flow_zone_max=0.7,
            )

            # Compile to JS
            js_code = self._injector.build_js(profile)

            duration = time.time() - start
            result = AdaptiveResult(
                success=True,
                profile=profile,
                js_code=js_code,
                duration_s=duration,
                session_id=session_id,
            )

            self._history.append(result.to_dict())
            if len(self._history) > 30:
                self._history = self._history[-30:]

            return result

        except Exception as e:
            logger.exception("Adaptive direction failed")
            return AdaptiveResult(
                success=False, profile=None, js_code="",
                duration_s=time.time() - start, session_id=session_id,
                error=str(e),
            )


# =============================================================================
# Module-level accessor
# =============================================================================


def get_adaptive_director() -> AdaptiveDirector:
    """Return the singleton AdaptiveDirector instance."""
    return AdaptiveDirector.get_instance()
