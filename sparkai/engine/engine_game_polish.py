"""
SparkLabs Engine - Game Polish Injector

Injects professional-grade polish features into the generated HTML5 game:
  - Combo / multiplier system with visual feedback
  - Particle burst effects on collect, defeat, and damage events
  - Floating score popups that rise and fade
  - Contextual tutorial hints for first-time players
  - Level transition screen with level name display
  - Settings overlay with audio toggle and restart

The injector mirrors the FeatureInjector pattern: it produces JavaScript
snippets inserted into the HtmlAssembler template. All systems use typeof
checks for graceful degradation when disabled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PolishConfig:
    """Configuration for polish feature injection."""
    enable_combo: bool = True
    enable_particles: bool = True
    enable_score_popups: bool = True
    enable_tutorial: bool = True
    enable_transitions: bool = True
    enable_settings: bool = True
    combo_decay_seconds: float = 3.0
    max_multiplier: int = 8
    popup_rise_speed: float = 1.5
    popup_lifetime: int = 50
    tutorial_display_frames: int = 240
    transition_frames: int = 45


class PolishInjector:
    """
    Produces JavaScript code snippets that add combo multipliers, particle
    bursts, score popups, tutorial hints, level transitions, and a settings
    overlay to the generated game.

    The generated JS integrates with existing runtime variables (score, lives,
    player, entities, ctx, W, H, etc.) without redeclaring them.
    """

    def __init__(self, config: Optional[PolishConfig] = None) -> None:
        self.config = config or PolishConfig()

    def build_header_js(self) -> str:
        """Generate JavaScript for all polish system definitions."""
        parts: list[str] = []
        if self.config.enable_combo:
            parts.append(self._combo_system_js())
        if self.config.enable_score_popups:
            parts.append(self._score_popups_js())
        if self.config.enable_particles:
            parts.append(self._particle_burst_js())
        if self.config.enable_tutorial:
            parts.append(self._tutorial_system_js())
        if self.config.enable_transitions:
            parts.append(self._transition_system_js())
        if self.config.enable_settings:
            parts.append(self._settings_system_js())
        return "\n".join(parts)

    def build_loop_patch_js(self) -> str:
        """Generate JavaScript for update/render hooks called each frame."""
        return self._loop_functions_js()

    def build_init_call_js(self) -> str:
        """Generate JavaScript to call during game initialization."""
        parts: list[str] = []
        if self.config.enable_tutorial:
            parts.append("initTutorial();")
        return "\n".join(parts)

    # =========================================================================
    # Combo / Multiplier System
    # =========================================================================

    def _combo_system_js(self) -> str:
        decay_frames = int(self.config.combo_decay_seconds * 60)
        return f"""
  // ---- Combo / Multiplier System ----
  var comboCount = 0;
  var comboMultiplier = 1;
  var comboTimer = 0;
  var COMBO_DECAY = {decay_frames};
  var MAX_MULTIPLIER = {self.config.max_multiplier};
  var comboDisplayTimer = 0;

  function addCombo() {{
    comboCount++;
    comboMultiplier = Math.min(MAX_MULTIPLIER, 1 + Math.floor(comboCount / 3));
    comboTimer = COMBO_DECAY;
    comboDisplayTimer = 120;
  }}

  function resetCombo() {{
    comboCount = 0;
    comboMultiplier = 1;
    comboTimer = 0;
  }}

  function updateCombo() {{
    if (comboTimer > 0) {{
      comboTimer--;
      if (comboTimer === 0) {{
        resetCombo();
      }}
    }}
    if (comboDisplayTimer > 0) comboDisplayTimer--;
  }}

  function applyScore(basePoints) {{
    var earned = basePoints * comboMultiplier;
    score += earned;
    return earned;
  }}

  function renderCombo() {{
    if (comboDisplayTimer <= 0 || comboMultiplier <= 1) return;
    var alpha = Math.min(1, comboDisplayTimer / 60);
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.font = 'bold 22px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillStyle = comboMultiplier >= 5 ? '#fbbf24' : '#f97316';
    ctx.strokeStyle = 'rgba(0,0,0,0.6)';
    ctx.lineWidth = 3;
    var text = 'x' + comboMultiplier + ' COMBO';
    ctx.strokeText(text, W / 2, 50);
    ctx.fillText(text, W / 2, 50);
    // Combo timer bar
    if (comboTimer > 0) {{
      var barW = 80;
      var barH = 4;
      var barX = W / 2 - barW / 2;
      var barY = 58;
      ctx.fillStyle = 'rgba(255,255,255,0.15)';
      ctx.fillRect(barX, barY, barW, barH);
      ctx.fillStyle = comboMultiplier >= 5 ? '#fbbf24' : '#f97316';
      ctx.fillRect(barX, barY, barW * (comboTimer / COMBO_DECAY), barH);
    }}
    ctx.restore();
  }}"""

    # =========================================================================
    # Score Popups
    # =========================================================================

    def _score_popups_js(self) -> str:
        return f"""
  // ---- Floating Score Popups ----
  var scorePopups = [];
  var POPUP_RISE = {self.config.popup_rise_speed};
  var POPUP_LIFE = {self.config.popup_lifetime};

  function spawnScorePopup(x, y, text, color) {{
    scorePopups.push({{
      x: x, y: y, text: text, color: color || '#fbbf24',
      life: POPUP_LIFE, vy: -POPUP_RISE
    }});
  }}

  function updateScorePopups() {{
    for (var i = scorePopups.length - 1; i >= 0; i--) {{
      var p = scorePopups[i];
      p.y += p.vy;
      p.life--;
      if (p.life <= 0) scorePopups.splice(i, 1);
    }}
  }}

  function renderScorePopups() {{
    ctx.save();
    ctx.font = 'bold 16px sans-serif';
    ctx.textAlign = 'center';
    for (var i = 0; i < scorePopups.length; i++) {{
      var p = scorePopups[i];
      var alpha = Math.min(1, p.life / 30);
      ctx.globalAlpha = alpha;
      ctx.strokeStyle = 'rgba(0,0,0,0.7)';
      ctx.lineWidth = 3;
      ctx.strokeText(p.text, p.x, p.y);
      ctx.fillStyle = p.color;
      ctx.fillText(p.text, p.x, p.y);
    }}
    ctx.restore();
  }}"""

    # =========================================================================
    # Particle Bursts
    # =========================================================================

    def _particle_burst_js(self) -> str:
        return """
  // ---- Particle Burst Effects ----
  var burstParticles = [];

  function spawnBurst(x, y, color, count) {
    count = count || 12;
    for (var i = 0; i < count; i++) {
      var angle = (i / count) * Math.PI * 2 + Math.random() * 0.4;
      var speed = 2 + Math.random() * 3;
      burstParticles.push({
        x: x, y: y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: 30 + Math.random() * 20,
        maxLife: 50,
        color: color || '#fbbf24',
        size: 3 + Math.random() * 3
      });
    }
  }

  function updateBurstParticles() {
    for (var i = burstParticles.length - 1; i >= 0; i--) {
      var p = burstParticles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.15;
      p.vx *= 0.96;
      p.life--;
      if (p.life <= 0) burstParticles.splice(i, 1);
    }
  }

  function renderBurstParticles() {
    ctx.save();
    for (var i = 0; i < burstParticles.length; i++) {
      var p = burstParticles[i];
      var alpha = p.life / p.maxLife;
      ctx.globalAlpha = alpha;
      ctx.fillStyle = p.color;
      ctx.fillRect(p.x - p.size / 2, p.y - p.size / 2, p.size, p.size);
    }
    ctx.restore();
  }"""

    # =========================================================================
    # Tutorial System
    # =========================================================================

    def _tutorial_system_js(self) -> str:
        display_frames = self.config.tutorial_display_frames
        return f"""
  // ---- Tutorial Hint System ----
  var tutorialHints = [];
  var tutorialActive = false;
  var TUTORIAL_DURATION = {display_frames};

  function initTutorial() {{
    tutorialHints = [];
    tutorialActive = true;
    // Detect game type from config and show relevant hints
    if (CONFIG.gravity > 0) {{
      tutorialHints.push({{ text: 'Arrow Keys / A,D to move', shown: false }});
      tutorialHints.push({{ text: 'Space / W / Up to jump', shown: false }});
    }} else {{
      tutorialHints.push({{ text: 'Arrow Keys / WASD to move', shown: false }});
    }}
    tutorialHints.push({{ text: 'Collect items for score', shown: false }});
    tutorialHints.push({{ text: 'Avoid enemies and hazards', shown: false }});
    tutorialHints.push({{ text: 'Press ESC to pause', shown: false }});
  }}

  var tutorialHintIndex = 0;
  var tutorialTimer = 0;

  function updateTutorial() {{
    if (!tutorialActive) return;
    if (tutorialTimer > 0) {{
      tutorialTimer--;
      if (tutorialTimer === 0 && tutorialHintIndex < tutorialHints.length - 1) {{
        tutorialHintIndex++;
        tutorialTimer = TUTORIAL_DURATION;
      }} else if (tutorialTimer === 0 && tutorialHintIndex >= tutorialHints.length - 1) {{
        tutorialActive = false;
      }}
    }} else {{
      tutorialTimer = TUTORIAL_DURATION;
    }}
  }}

  function renderTutorial() {{
    if (!tutorialActive || tutorialHintIndex >= tutorialHints.length) return;
    var hint = tutorialHints[tutorialHintIndex];
    var alpha = 1;
    if (tutorialTimer < 60) alpha = tutorialTimer / 60;
    else if (tutorialTimer > TUTORIAL_DURATION - 30) alpha = (TUTORIAL_DURATION - tutorialTimer) / 30;

    ctx.save();
    ctx.globalAlpha = alpha * 0.9;
    // Background bar
    var barH = 40;
    var barY = H - barH - 10;
    ctx.fillStyle = 'rgba(10,10,10,0.85)';
    ctx.fillRect(W / 2 - 200, barY, 400, barH);
    ctx.strokeStyle = 'rgba(249,115,22,0.5)';
    ctx.lineWidth = 1;
    ctx.strokeRect(W / 2 - 200, barY, 400, barH);
    // Text
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillStyle = '#f97316';
    ctx.fillText('TUTORIAL  ' + (tutorialHintIndex + 1) + '/' + tutorialHints.length, W / 2, barY + 15);
    ctx.fillStyle = '#ccc';
    ctx.fillText(hint.text, W / 2, barY + 32);
    ctx.restore();
  }}"""

    # =========================================================================
    # Level Transition System
    # =========================================================================

    def _transition_system_js(self) -> str:
        frames = self.config.transition_frames
        return f"""
  // ---- Level Transition Screen ----
  var transitionActive = false;
  var transitionTimer = 0;
  var transitionText = '';
  var TRANSITION_FRAMES = {frames};

  function showTransition(text) {{
    transitionActive = true;
    transitionTimer = TRANSITION_FRAMES;
    transitionText = text || '';
  }}

  function updateTransition() {{
    if (!transitionActive) return;
    transitionTimer--;
    if (transitionTimer <= 0) {{
      transitionActive = false;
    }}
  }}

  function renderTransition() {{
    if (!transitionActive) return;
    var progress = 1 - (transitionTimer / TRANSITION_FRAMES);
    var alpha;
    // Fade in, hold, fade out
    if (progress < 0.25) alpha = progress / 0.25;
    else if (progress > 0.75) alpha = (1 - progress) / 0.25;
    else alpha = 1;

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = 'rgba(0,0,0,0.7)';
    ctx.fillRect(0, 0, W, H);
    ctx.font = 'bold 36px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillStyle = '#f97316';
    ctx.strokeStyle = 'rgba(0,0,0,0.8)';
    ctx.lineWidth = 4;
    ctx.strokeText(transitionText, W / 2, H / 2);
    ctx.fillText(transitionText, W / 2, H / 2);
    // Loading dots
    var dots = Math.floor(progress * 4) % 4;
    var dotStr = '';
    for (var i = 0; i < dots; i++) dotStr += '.';
    ctx.font = '20px sans-serif';
    ctx.fillStyle = '#888';
    ctx.fillText(dotStr, W / 2, H / 2 + 40);
    ctx.restore();
  }}"""

    # =========================================================================
    # Settings Overlay
    # =========================================================================

    def _settings_system_js(self) -> str:
        return """
  // ---- Settings Overlay ----
  var settingsOpen = false;
  var audioEnabled = true;

  function toggleSettings() {
    settingsOpen = !settingsOpen;
  }

  function toggleAudio() {
    audioEnabled = !audioEnabled;
    if (typeof setAudioEnabled === 'function') setAudioEnabled(audioEnabled);
  }

  function restartGame() {
    settingsOpen = false;
    startGame();
  }

  function renderSettings() {
    if (!settingsOpen) return;
    ctx.save();
    // Dim background
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    ctx.fillRect(0, 0, W, H);
    // Panel
    var pw = 280, ph = 240;
    var px = W / 2 - pw / 2;
    var py = H / 2 - ph / 2;
    ctx.fillStyle = 'rgba(15,15,20,0.95)';
    ctx.fillRect(px, py, pw, ph);
    ctx.strokeStyle = '#f97316';
    ctx.lineWidth = 2;
    ctx.strokeRect(px, py, pw, ph);
    // Title
    ctx.font = 'bold 20px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillStyle = '#f97316';
    ctx.fillText('SETTINGS', W / 2, py + 35);
    // Audio toggle
    ctx.font = '15px sans-serif';
    ctx.fillStyle = '#ccc';
    ctx.textAlign = 'left';
    ctx.fillText('Audio', px + 30, py + 80);
    ctx.textAlign = 'right';
    ctx.fillStyle = audioEnabled ? '#4ade80' : '#ef4444';
    ctx.fillText(audioEnabled ? 'ON  [M]' : 'OFF [M]', px + pw - 30, py + 80);
    // Restart
    ctx.textAlign = 'left';
    ctx.fillStyle = '#ccc';
    ctx.fillText('Restart', px + 30, py + 120);
    ctx.textAlign = 'right';
    ctx.fillStyle = '#60a5fa';
    ctx.fillText('[R]', px + pw - 30, py + 120);
    // Resume
    ctx.textAlign = 'left';
    ctx.fillStyle = '#ccc';
    ctx.fillText('Resume', px + 30, py + 160);
    ctx.textAlign = 'right';
    ctx.fillStyle = '#60a5fa';
    ctx.fillText('[ESC]', px + pw - 30, py + 160);
    // Footer
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillStyle = '#555';
    ctx.fillText('SparkLabs AI-Native Engine', W / 2, py + ph - 20);
    ctx.restore();
  }"""

    # =========================================================================
    # Loop Integration
    # =========================================================================

    def _loop_functions_js(self) -> str:
        nl = "\n"
        update_parts: list[str] = []
        render_parts: list[str] = []

        if self.config.enable_combo:
            update_parts.append("updateCombo();")
            render_parts.append("renderCombo();")
        if self.config.enable_score_popups:
            update_parts.append("updateScorePopups();")
            render_parts.append("renderScorePopups();")
        if self.config.enable_particles:
            update_parts.append("updateBurstParticles();")
            render_parts.append("renderBurstParticles();")
        if self.config.enable_tutorial:
            update_parts.append("updateTutorial();")
            render_parts.append("renderTutorial();")
        if self.config.enable_transitions:
            update_parts.append("updateTransition();")
            render_parts.append("renderTransition();")

        update_body = nl.join("    " + p for p in update_parts) if update_parts else "    // no polish update hooks"
        render_body = nl.join("    " + p for p in render_parts) if render_parts else "    // no polish render hooks"

        return f"""
  // ---- Polish System Loop Integration ----
  function updatePolishSystems() {{
{update_body}
  }}
  function renderPolishSystems() {{
{render_body}
  }}
  function renderPolishOverlay() {{
    if (typeof renderSettings === 'function') renderSettings();
  }}"""
