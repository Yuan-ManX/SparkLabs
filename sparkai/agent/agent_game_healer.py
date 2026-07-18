"""
SparkLabs Agent - Game Healer

An AI agent that automatically repairs game quality issues by analyzing
game HTML, detecting missing features, and injecting self-contained
JavaScript patches that add the missing capabilities.

This agent closes the AI-native feedback loop:
  Generate -> Critique -> Heal -> Re-critique

Each healing patch is a self-contained JavaScript block that hooks
into the existing game runtime (window.gameState, update(), etc.)
without requiring any changes to the original game code.

Architecture:
  GameHealer (singleton)
    |-- SignalExtractor   -> detects missing features from HTML
    |-- PatchGenerator    -> creates JS patches for each issue
    |-- PatchApplier      -> injects patches into HTML before </body>
    |-- HealingSession    -> tracks applied patches and results

Healing Patch Types:
  - audio:        Procedural Web Audio SFX (collect, hit, jump, gameover)
  - touch:        Touch-to-keyboard input mapping for mobile
  - settings:     Settings overlay with volume and pause controls
  - achievements: Achievement tracking with unlock notifications
  - save_load:    localStorage persistence for high scores and progress
  - tutorial:     Contextual hint system for first-time players
  - difficulty:   CONFIG tuning for enemy speed and lives
  - pause:        Pause/resume system with overlay
"""

from __future__ import annotations

import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class HealingPatch:
    """A single healing patch applied to game HTML."""
    patch_id: str
    patch_type: str  # audio, touch, settings, achievements, save_load, tutorial, difficulty, pause
    title: str
    description: str
    js_code: str = ""
    config_changes: Dict[str, Any] = field(default_factory=dict)
    applied: bool = False

    def to_dict(self, include_js: bool = False) -> Dict[str, Any]:
        result = {
            "patch_id": self.patch_id,
            "patch_type": self.patch_type,
            "title": self.title,
            "description": self.description,
            "config_changes": self.config_changes,
            "applied": self.applied,
        }
        if include_js:
            result["js_code"] = self.js_code
        return result


@dataclass
class HealingResult:
    """Result of a healing session."""
    session_id: str
    success: bool
    original_html: str
    healed_html: str
    patches: List[HealingPatch] = field(default_factory=list)
    fixes_applied: int = 0
    original_size: int = 0
    healed_size: int = 0
    duration_s: float = 0.0
    signals: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self, include_html: bool = False) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "session_id": self.session_id,
            "success": self.success,
            "patches": [p.to_dict() for p in self.patches],
            "fixes_applied": self.fixes_applied,
            "original_size": self.original_size,
            "healed_size": self.healed_size,
            "duration_s": round(self.duration_s, 3),
            "signals": self.signals,
            "error": self.error,
        }
        if include_html:
            result["original_html"] = self.original_html
            result["healed_html"] = self.healed_html
        return result


@dataclass
class HealingStats:
    """Aggregate statistics for the healer."""
    total_sessions: int = 0
    successful_sessions: int = 0
    total_patches_applied: int = 0
    patch_type_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_sessions": self.total_sessions,
            "successful_sessions": self.successful_sessions,
            "total_patches_applied": self.total_patches_applied,
            "patch_type_counts": dict(self.patch_type_counts),
        }


# ---------------------------------------------------------------------------
# Game Healer Singleton
# ---------------------------------------------------------------------------


class GameHealer:
    """AI agent that automatically heals game quality issues.

    Analyzes game HTML for missing features and injects self-contained
    JavaScript patches that add procedural audio, touch support, settings
    overlays, achievement systems, save/load persistence, tutorial hints,
    difficulty tuning, and pause functionality.
    """

    _instance: Optional["GameHealer"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "GameHealer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._initialized = False
                    cls._instance = obj
        return cls._instance

    @classmethod
    def get_instance(cls) -> "GameHealer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls()
        return cls._instance  # type: ignore[return-value]

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._inner_lock: threading.RLock = threading.RLock()
            self._history: List[HealingResult] = []
            self._stats = HealingStats()
            self._initialized = True

    # -- Public API --------------------------------------------------------

    def heal(self, html: str, signals: Optional[Dict[str, Any]] = None) -> HealingResult:
        """Analyze game HTML and apply healing patches.

        Args:
            html: The game HTML to heal.
            signals: Optional pre-extracted quality signals. If None,
                     signals will be extracted from the HTML.

        Returns:
            HealingResult with the healed HTML and applied patches.
        """
        import time
        start = time.time()
        session_id = _new_id("heal")

        try:
            # Extract signals if not provided
            if signals is None:
                signals = self._extract_signals(html)

            # Generate patches based on missing features
            patches = self._generate_patches(signals, html)

            # Apply patches to HTML
            healed_html = html
            applied_count = 0
            for patch in patches:
                healed_html = self._apply_patch(healed_html, patch)
                if patch.applied:
                    applied_count += 1

            result = HealingResult(
                session_id=session_id,
                success=True,
                original_html=html,
                healed_html=healed_html,
                patches=patches,
                fixes_applied=applied_count,
                original_size=len(html),
                healed_size=len(healed_html),
                duration_s=time.time() - start,
                signals=signals,
            )

            # Record in history
            with self._inner_lock:
                self._history.append(result)
                if len(self._history) > 100:
                    self._history.pop(0)
                self._stats.total_sessions += 1
                self._stats.successful_sessions += 1
                self._stats.total_patches_applied += applied_count
                for p in patches:
                    if p.applied:
                        cnt = self._stats.patch_type_counts.get(p.patch_type, 0)
                        self._stats.patch_type_counts[p.patch_type] = cnt + 1

            return result

        except Exception as e:
            return HealingResult(
                session_id=session_id,
                success=False,
                original_html=html,
                healed_html=html,
                duration_s=time.time() - start,
                error=str(e),
            )

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent healing sessions."""
        with self._inner_lock:
            return [r.to_dict() for r in self._history[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        with self._inner_lock:
            return self._stats.to_dict()

    def get_status(self) -> Dict[str, Any]:
        """Return status for health checks."""
        with self._inner_lock:
            return {
                "initialized": self._initialized,
                "total_sessions": len(self._history),
                "patch_types": [
                    "audio", "touch", "settings", "achievements",
                    "save_load", "tutorial", "difficulty", "pause",
                ],
            }

    # -- Signal Extraction -------------------------------------------------

    def _extract_signals(self, html: str) -> Dict[str, Any]:
        """Extract quality signals from game HTML."""
        html_lower = html.lower()
        signals: Dict[str, Any] = {
            "has_audio_api": "audiocontext" in html_lower,
            "has_touch": "touchstart" in html_lower,
            "has_settings": "settings" in html_lower and "overlay" in html_lower,
            "has_achievements": "achievement" in html_lower,
            "has_save_load": "localstorage" in html_lower,
            "has_tutorial": "tutorial" in html_lower or "hint" in html_lower,
            "has_pause": "pause" in html_lower and "function" in html_lower,
            "has_game_state": "window.gamestate" in html_lower,
        }

        # Extract CONFIG values for difficulty tuning
        config_patterns = {
            "enemy_speed": re.compile(r'"enemySpeed":\s*([0-9.]+)', re.I),
            "lives": re.compile(r'"lives":\s*(\d+)', re.I),
        }
        config_values: Dict[str, Any] = {}
        for key, pattern in config_patterns.items():
            match = pattern.search(html)
            if match:
                try:
                    config_values[key] = float(match.group(1)) if key == "enemy_speed" else int(match.group(1))
                except ValueError:
                    pass
        signals["config"] = config_values
        return signals

    # -- Patch Generation --------------------------------------------------

    def _generate_patches(self, signals: Dict[str, Any], html: str) -> List[HealingPatch]:
        """Generate healing patches based on detected missing features."""
        patches: List[HealingPatch] = []

        # Audio patch
        if not signals.get("has_audio_api"):
            patches.append(HealingPatch(
                patch_id=_new_id("ptch"),
                patch_type="audio",
                title="Procedural Audio System",
                description="Injects Web Audio API based SFX for collect, hit, jump, and game over events.",
                js_code=self._audio_patch_js(),
            ))

        # Touch patch
        if not signals.get("has_touch"):
            patches.append(HealingPatch(
                patch_id=_new_id("ptch"),
                patch_type="touch",
                title="Touch Input Support",
                description="Maps touch events to keyboard inputs for mobile playability.",
                js_code=self._touch_patch_js(),
            ))

        # Settings patch
        if not signals.get("has_settings"):
            patches.append(HealingPatch(
                patch_id=_new_id("ptch"),
                patch_type="settings",
                title="Settings Overlay",
                description="Adds a settings overlay with volume control and pause toggle.",
                js_code=self._settings_patch_js(),
            ))

        # Achievements patch
        if not signals.get("has_achievements"):
            patches.append(HealingPatch(
                patch_id=_new_id("ptch"),
                patch_type="achievements",
                title="Achievement System",
                description="Tracks score milestones and displays unlock notifications.",
                js_code=self._achievements_patch_js(),
            ))

        # Save/Load patch
        if not signals.get("has_save_load"):
            patches.append(HealingPatch(
                patch_id=_new_id("ptch"),
                patch_type="save_load",
                title="Save/Load Persistence",
                description="Persists high scores and progress using localStorage.",
                js_code=self._save_load_patch_js(),
            ))

        # Tutorial patch
        if not signals.get("has_tutorial"):
            patches.append(HealingPatch(
                patch_id=_new_id("ptch"),
                patch_type="tutorial",
                title="Tutorial Hints",
                description="Displays contextual hints during the first few seconds of gameplay.",
                js_code=self._tutorial_patch_js(),
            ))

        # Pause patch
        if not signals.get("has_pause"):
            patches.append(HealingPatch(
                patch_id=_new_id("ptch"),
                patch_type="pause",
                title="Pause System",
                description="Adds pause/resume functionality with ESC key and overlay.",
                js_code=self._pause_patch_js(),
            ))

        # Difficulty patch
        cfg = signals.get("config", {})
        enemy_speed = cfg.get("enemy_speed", 0.0)
        lives = cfg.get("lives", 0)
        config_changes: Dict[str, Any] = {}
        if enemy_speed > 2.5:
            config_changes["enemySpeed"] = 2.0
        if lives > 0 and lives < 3:
            config_changes["lives"] = 3
        if config_changes:
            patches.append(HealingPatch(
                patch_id=_new_id("ptch"),
                patch_type="difficulty",
                title="Difficulty Tuning",
                description=f"Adjusts CONFIG values for better balance: {config_changes}",
                js_code="",
                config_changes=config_changes,
            ))

        return patches

    # -- Patch Application -------------------------------------------------

    def _apply_patch(self, html: str, patch: HealingPatch) -> str:
        """Apply a single patch to the HTML."""
        try:
            # Apply CONFIG changes via regex replacement
            if patch.config_changes:
                for key, new_value in patch.config_changes.items():
                    # JSON format: "key": old_value
                    if isinstance(new_value, str):
                        pattern = re.compile(
                            rf'("{key}":\s*")[^"]+(")',
                            re.I,
                        )
                        html = pattern.sub(rf'\g<1>{new_value}\g<2>', html)
                    else:
                        pattern = re.compile(
                            rf'("{key}":\s*)[0-9.-]+',
                            re.I,
                        )
                        html = pattern.sub(rf'\g<1>{new_value}', html)

            # Inject JS code before </body>
            if patch.js_code:
                js_block = f"\n<!-- SparkLabs Heal: {patch.title} -->\n{patch.js_code}\n"
                if "</body>" in html:
                    html = html.replace("</body>", js_block + "</body>", 1)
                else:
                    html = html + js_block

            patch.applied = True
            return html
        except Exception:
            patch.applied = False
            return html

    # -- JavaScript Patch Templates ----------------------------------------

    @staticmethod
    def _audio_patch_js() -> str:
        """Generate procedural audio SFX patch."""
        return """<script>
(function() {
  var _slAudioCtx = null;
  function _slGetCtx() {
    if (!_slAudioCtx) {
      try { _slAudioCtx = new (window.AudioContext || window.webkitAudioContext)(); }
      catch(e) { return null; }
    }
    return _slAudioCtx;
  }
  function _slBeep(freq, duration, type, vol) {
    var ctx = _slGetCtx();
    if (!ctx) return;
    try {
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.type = type || 'sine';
      osc.frequency.value = freq || 440;
      gain.gain.value = vol || 0.15;
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + (duration || 0.15));
      osc.stop(ctx.currentTime + (duration || 0.15));
    } catch(e) {}
  }
  window.slPlaySFX = function(type) {
    switch(type) {
      case 'collect': _slBeep(880, 0.1, 'sine', 0.2); break;
      case 'jump': _slBeep(440, 0.08, 'square', 0.1); break;
      case 'hit': _slBeep(150, 0.2, 'sawtooth', 0.2); break;
      case 'gameover': _slBeep(100, 0.5, 'sawtooth', 0.25); break;
      case 'victory': _slBeep(660, 0.15, 'sine', 0.2); break;
      default: _slBeep(440, 0.1, 'sine', 0.1);
    }
  };
  // Hook into game state changes
  var _slLastScore = 0;
  var _slLastLives = -1;
  setInterval(function() {
    if (typeof window.gameState !== 'undefined') {
      if (window.gameState.score > _slLastScore) {
        window.slPlaySFX('collect');
      }
      _slLastScore = window.gameState.score;
      if (_slLastLives < 0) _slLastLives = window.gameState.lives;
      if (window.gameState.lives < _slLastLives) {
        window.slPlaySFX('hit');
        _slLastLives = window.gameState.lives;
      }
      if (window.gameState.state === 'gameover') {
        window.slPlaySFX('gameover');
      }
      if (window.gameState.state === 'victory') {
        window.slPlaySFX('victory');
      }
    }
  }, 200);
})();
</script>"""

    @staticmethod
    def _touch_patch_js() -> str:
        """Generate touch input mapping patch."""
        return """<script>
(function() {
  var canvas = document.querySelector('canvas');
  if (!canvas) return;
  var _slTouchStart = null;
  function _slSimulateKey(type, key) {
    var evt = new KeyboardEvent(type, { key: key, bubbles: true });
    document.dispatchEvent(evt);
  }
  canvas.addEventListener('touchstart', function(e) {
    e.preventDefault();
    if (e.touches.length > 0) {
      _slTouchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY, time: Date.now() };
      // Tap = jump
      _slSimulateKey('keydown', 'ArrowUp');
      setTimeout(function() { _slSimulateKey('keyup', 'ArrowUp'); }, 100);
    }
    if (e.touches.length > 1) {
      // Two fingers = pause
      _slSimulateKey('keydown', 'Escape');
      setTimeout(function() { _slSimulateKey('keyup', 'Escape'); }, 100);
    }
  }, { passive: false });
  canvas.addEventListener('touchmove', function(e) {
    e.preventDefault();
    if (!_slTouchStart || e.touches.length === 0) return;
    var dx = e.touches[0].clientX - _slTouchStart.x;
    var dy = e.touches[0].clientY - _slTouchStart.y;
    if (Math.abs(dx) > 30) {
      if (dx > 0) { _slSimulateKey('keydown', 'ArrowRight'); }
      else { _slSimulateKey('keydown', 'ArrowLeft'); }
      _slTouchStart.x = e.touches[0].clientX;
    }
  }, { passive: false });
  canvas.addEventListener('touchend', function(e) {
    e.preventDefault();
    _slSimulateKey('keyup', 'ArrowLeft');
    _slSimulateKey('keyup', 'ArrowRight');
    _slTouchStart = null;
  }, { passive: false });
})();
</script>"""

    @staticmethod
    def _settings_patch_js() -> str:
        """Generate settings overlay patch."""
        return """<script>
(function() {
  var overlay = document.createElement('div');
  overlay.id = 'sl-settings-overlay';
  overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);display:none;z-index:9999;justify-content:center;align-items:center;font-family:monospace;';
  overlay.innerHTML = '<div style="background:#141414;border:1px solid #f97316;border-radius:12px;padding:24px;min-width:300px;">' +
    '<h2 style="color:#f97316;margin:0 0 16px;font-size:18px;">Settings</h2>' +
    '<div style="margin-bottom:12px;"><label style="color:#aaa;font-size:12px;display:block;margin-bottom:4px;">SFX Volume</label>' +
    '<input type="range" id="sl-vol" min="0" max="100" value="50" style="width:100%;"></div>' +
    '<div style="margin-bottom:16px;"><label style="color:#aaa;font-size:12px;display:block;margin-bottom:4px;">Music Volume</label>' +
    '<input type="range" id="sl-music" min="0" max="100" value="30" style="width:100%;"></div>' +
    '<button id="sl-resume" style="background:#f97316;color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px;width:100%;">Resume</button>' +
    '</div>';
  document.body.appendChild(overlay);
  var btn = document.createElement('button');
  btn.innerHTML = '&#9881;';
  btn.style.cssText = 'position:fixed;top:8px;right:8px;z-index:9998;background:rgba(20,20,20,0.8);color:#f97316;border:1px solid #333;border-radius:6px;width:32px;height:32px;font-size:16px;cursor:pointer;';
  btn.onclick = function() {
    overlay.style.display = 'flex';
    if (typeof window.slPause === 'function') window.slPause();
  };
  document.body.appendChild(btn);
  document.getElementById('sl-resume').onclick = function() {
    overlay.style.display = 'none';
    if (typeof window.slResume === 'function') window.slResume();
  };
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      if (overlay.style.display === 'flex') {
        overlay.style.display = 'none';
        if (typeof window.slResume === 'function') window.slResume();
      } else {
        overlay.style.display = 'flex';
        if (typeof window.slPause === 'function') window.slPause();
      }
    }
  });
})();
</script>"""

    @staticmethod
    def _achievements_patch_js() -> str:
        """Generate achievement system patch."""
        return """<script>
(function() {
  var _slAchievements = [
    { id: 'first_score', name: 'First Steps', desc: 'Score your first point', threshold: 1, unlocked: false },
    { id: 'score_50', name: 'Getting Started', desc: 'Reach 50 points', threshold: 50, unlocked: false },
    { id: 'score_100', name: 'Century', desc: 'Reach 100 points', threshold: 100, unlocked: false },
    { id: 'score_500', name: 'High Scorer', desc: 'Reach 500 points', threshold: 500, unlocked: false },
    { id: 'score_1000', name: 'Master', desc: 'Reach 1000 points', threshold: 1000, unlocked: false },
  ];
  function _slShowAchievement(ach) {
    var toast = document.createElement('div');
    toast.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#141414;border:2px solid #fbbf24;border-radius:8px;padding:12px 24px;z-index:99999;font-family:monospace;animation:slfadein 0.3s;';
    toast.innerHTML = '<div style="color:#fbbf24;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Achievement Unlocked</div>' +
      '<div style="color:#fff;font-size:14px;font-weight:bold;margin-top:4px;">' + ach.name + '</div>' +
      '<div style="color:#888;font-size:11px;margin-top:2px;">' + ach.desc + '</div>';
    document.body.appendChild(toast);
    setTimeout(function() { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.5s'; }, 2500);
    setTimeout(function() { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 3000);
  }
  setInterval(function() {
    if (typeof window.gameState === 'undefined') return;
    var score = window.gameState.score || 0;
    for (var i = 0; i < _slAchievements.length; i++) {
      var ach = _slAchievements[i];
      if (!ach.unlocked && score >= ach.threshold) {
        ach.unlocked = true;
        _slShowAchievement(ach);
      }
    }
  }, 500);
  window.slGetAchievements = function() { return _slAchievements; };
})();
</script>"""

    @staticmethod
    def _save_load_patch_js() -> str:
        """Generate save/load persistence patch."""
        return """<script>
(function() {
  var _slSaveKey = 'sparklabs_game_save';
  function _slSave() {
    try {
      var data = {
        highScore: window.gameState ? (window.gameState.score || 0) : 0,
        timestamp: Date.now(),
      };
      var existing = {};
      try { existing = JSON.parse(localStorage.getItem(_slSaveKey) || '{}'); } catch(e) {}
      if (data.highScore > (existing.highScore || 0)) {
        localStorage.setItem(_slSaveKey, JSON.stringify(data));
      }
    } catch(e) {}
  }
  function _slLoad() {
    try {
      var raw = localStorage.getItem(_slSaveKey);
      if (raw) return JSON.parse(raw);
    } catch(e) {}
    return null;
  }
  window.slSaveGame = _slSave;
  window.slLoadGame = _slLoad;
  window.slGetHighScore = function() {
    var data = _slLoad();
    return data ? (data.highScore || 0) : 0;
  };
  // Auto-save on state changes
  setInterval(function() {
    if (typeof window.gameState !== 'undefined') {
      if (window.gameState.state === 'gameover' || window.gameState.state === 'victory') {
        _slSave();
      }
    }
  }, 1000);
  // Display high score on load
  var hs = _slLoad();
  if (hs && hs.highScore > 0) {
    setTimeout(function() {
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed;bottom:8px;right:8px;color:#666;font-size:10px;font-family:monospace;z-index:9990;';
      el.textContent = 'High Score: ' + hs.highScore;
      document.body.appendChild(el);
    }, 1000);
  }
})();
</script>"""

    @staticmethod
    def _tutorial_patch_js() -> str:
        """Generate tutorial hints patch."""
        return """<script>
(function() {
  var _slHints = [
    { text: 'Use Arrow Keys or WASD to move', delay: 1000, duration: 4000 },
    { text: 'Press Up or Space to jump', delay: 5000, duration: 4000 },
    { text: 'Collect items for points', delay: 10000, duration: 4000 },
    { text: 'Avoid enemies to survive', delay: 15000, duration: 4000 },
  ];
  var _slHintShown = false;
  function _slShowHint(text, duration) {
    var el = document.createElement('div');
    el.style.cssText = 'position:fixed;bottom:40px;left:50%;transform:translateX(-50%);background:rgba(20,20,20,0.9);color:#f97316;border:1px solid #f97316;border-radius:8px;padding:10px 20px;font-family:monospace;font-size:13px;z-index:99991;animation:slfadein 0.3s;';
    el.textContent = text;
    document.body.appendChild(el);
    setTimeout(function() {
      el.style.opacity = '0';
      el.style.transition = 'opacity 0.5s';
      setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, 500);
    }, duration);
  }
  // Only show hints if game is in intro/playing state
  setTimeout(function() {
    _slHintShown = true;
    _slHints.forEach(function(hint) {
      setTimeout(function() { _slShowHint(hint.text, hint.duration); }, hint.delay);
    });
  }, 500);
})();
</script>"""

    @staticmethod
    def _pause_patch_js() -> str:
        """Generate pause system patch."""
        return """<script>
(function() {
  var _slPaused = false;
  var _slOverlay = document.createElement('div');
  _slOverlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);display:none;justify-content:center;align-items:center;z-index:9998;font-family:monospace;';
  _slOverlay.innerHTML = '<div style="color:#f97316;font-size:32px;font-weight:bold;">PAUSED</div>';
  document.body.appendChild(_slOverlay);
  window.slPause = function() {
    _slPaused = true;
    _slOverlay.style.display = 'flex';
  };
  window.slResume = function() {
    _slPaused = false;
    _slOverlay.style.display = 'none';
  };
  window.slIsPaused = function() { return _slPaused; };
  document.addEventListener('keydown', function(e) {
    if (e.key === 'p' || e.key === 'P') {
      if (_slPaused) window.slResume();
      else window.slPause();
    }
  });
  // Hook into game loop - check if update function exists
  var _slOrigUpdate = null;
  setTimeout(function() {
    if (typeof window.update === 'function' && !_slOrigUpdate) {
      _slOrigUpdate = window.update;
      window.update = function() {
        if (!_slPaused) return _slOrigUpdate.apply(this, arguments);
      };
    }
  }, 500);
})();
</script>"""


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

def get_game_healer() -> GameHealer:
    """Return the singleton GameHealer instance."""
    return GameHealer.get_instance()
