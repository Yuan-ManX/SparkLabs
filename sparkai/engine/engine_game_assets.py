"""
SparkLabs Engine - Genre Asset Profiles

Provides per-genre overrides for audio, visual styling, and particle effects
so each generated game has a distinct sensory identity instead of sharing
one universal asset palette.

Each GenreAssetProfile produces three self-contained JavaScript/CSS snippets:
  1. build_css()              -> genre-specific CSS (canvas filters, overlays)
  2. build_audio_overrides()  -> JS that redefines sfx* functions per genre
  3. build_effect_overrides() -> JS that redefines particle spawn functions
  4. build_post_process_js()  -> JS canvas post-processing per frame

The overrides run AFTER the base FxInjector definitions, so redefining a
function name cleanly replaces the shared default. Games without a profile
fall back to the base AudioSynth/ParticleEngine behavior.

Genre identities (original SparkLabs design):
  - platformer : cartoon bouncy, bright saturated, dust puffs
  - shooter    : sci-fi vector, CRT scanlines, neon laser zaps
  - parkour    : motion speed, speed-lines, whooshes, afterimage
  - tank_battle: military pixelated, smoke debris, low cannon booms
  - puzzle     : neon crystal, chimes bells, bloom glow, ripple cascade
  - boss_battle: epic cinematic, dramatic stings, shockwave embers
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class GenreAssetProfile:
    """Per-genre audio, visual, and effect overrides for generated games."""

    def __init__(self, genre: str, config: Any) -> None:
        self.genre = genre
        self.config = config

    def build_css(self) -> str:
        """Return genre-specific CSS injected into the HTML <style> block."""
        handler = _CSS_PROFILES.get(self.genre)
        if handler is None:
            return ""
        return handler(self.config)

    def build_audio_overrides(self) -> str:
        """Return JS that redefines sfx* functions with genre-specific sounds."""
        handler = _AUDIO_PROFILES.get(self.genre)
        if handler is None:
            return ""
        return handler(self.config)

    def build_effect_overrides(self) -> str:
        """Return JS that redefines particle spawn functions per genre."""
        handler = _EFFECT_PROFILES.get(self.genre)
        if handler is None:
            return ""
        return handler(self.config)

    def build_post_process_js(self) -> str:
        """Return JS for canvas post-processing called after scene render."""
        handler = _POST_PROCESS_PROFILES.get(self.genre)
        if handler is None:
            return ""
        return handler(self.config)


# =============================================================================
# CSS Profiles - visual identity per genre
# =============================================================================


def _css_platformer(config: Any) -> str:
    # Cartoon: saturated, soft vignette, no scanlines
    return """
  #gameCanvas { image-rendering: auto; filter: saturate(1.35) contrast(1.08); }
  #overlay-title { text-shadow: 0 0 18px rgba(249,115,22,0.55), 2px 2px 0 #000; }
  .vignette-overlay {
    position: absolute; inset: 0; pointer-events: none; z-index: 6;
    background: radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.45) 100%);
  }"""


def _css_shooter(config: Any) -> str:
    # Sci-fi CRT: scanlines + chromatic glow
    return """
  #gameCanvas { image-rendering: pixelated; filter: contrast(1.15) saturate(1.2); }
  .crt-scanlines {
    position: absolute; inset: 0; pointer-events: none; z-index: 6;
    background: repeating-linear-gradient(0deg, rgba(0,0,0,0.18) 0px, rgba(0,0,0,0.18) 1px, transparent 2px, transparent 3px);
    mix-blend-mode: multiply;
  }
  .crt-vignette {
    position: absolute; inset: 0; pointer-events: none; z-index: 7;
    background: radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.55) 100%);
  }
  #overlay-title { text-shadow: 0 0 12px #00e5ff, 0 0 24px #00e5ff, 2px 2px 0 #000; }"""


def _css_parkour(config: Any) -> str:
    # Motion: high contrast cyan/magenta, speed lines overlay
    return """
  #gameCanvas { image-rendering: auto; filter: contrast(1.25) saturate(1.1) brightness(1.05); }
  .speed-overlay {
    position: absolute; inset: 0; pointer-events: none; z-index: 6;
    background:
      radial-gradient(circle at 50% 50%, transparent 30%, rgba(0,229,255,0.06) 70%, rgba(0,229,255,0.12) 100%);
  }
  #overlay-title { text-shadow: 0 0 14px #00e5ff, 0 0 28px #ff00ff, 2px 2px 0 #000; }
  .hud-block { border-color: rgba(0,229,255,0.35) !important; }"""


def _css_tank_battle(config: Any) -> str:
    # Military pixelated: grid overlay, desaturated
    return """
  #gameCanvas { image-rendering: pixelated; filter: saturate(0.85) contrast(1.1) brightness(0.95); }
  .grid-overlay {
    position: absolute; inset: 0; pointer-events: none; z-index: 6;
    background:
      linear-gradient(rgba(100,116,139,0.06) 1px, transparent 1px) 0 0/32px 32px,
      linear-gradient(90deg, rgba(100,116,139,0.06) 1px, transparent 1px) 0 0/32px 32px;
  }
  .crt-vignette {
    position: absolute; inset: 0; pointer-events: none; z-index: 7;
    background: radial-gradient(ellipse at center, transparent 60%, rgba(0,0,0,0.5) 100%);
  }
  #overlay-title { text-shadow: 2px 2px 0 #000, -1px -1px 0 #fbbf24; letter-spacing: 4px; }"""


def _css_puzzle(config: Any) -> str:
    # Neon crystal: dark gradient + bloom glow
    return """
  #gameCanvas { image-rendering: auto; filter: saturate(1.3) brightness(1.05); }
  body { background: radial-gradient(ellipse at 30% 20%, #1a0a2e 0%, #0a0a1a 60%, #000 100%); }
  .bloom-overlay {
    position: absolute; inset: 0; pointer-events: none; z-index: 6;
    background: radial-gradient(ellipse at 50% 50%, transparent 40%, rgba(168,85,247,0.08) 80%, rgba(168,85,247,0.15) 100%);
    mix-blend-mode: screen;
  }
  #overlay-title { text-shadow: 0 0 16px #a855f7, 0 0 32px #a855f7, 0 0 48px #a855f7; }
  .hud-block { border-color: rgba(168,85,247,0.4) !important; }"""


def _css_boss_battle(config: Any) -> str:
    # Epic cinematic: letterbox bars, dramatic vignette
    return """
  #gameCanvas { image-rendering: auto; filter: contrast(1.2) saturate(1.05); }
  .letterbox-top, .letterbox-bottom {
    position: absolute; left: 0; right: 0; height: 7vh; pointer-events: none; z-index: 8;
    background: #000;
  }
  .letterbox-top { top: 0; }
  .letterbox-bottom { bottom: 0; }
  .cinematic-vignette {
    position: absolute; inset: 0; pointer-events: none; z-index: 7;
    background: radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,0.6) 90%, rgba(0,0,0,0.85) 100%);
  }
  #overlay-title { text-shadow: 0 0 14px #ef4444, 0 0 28px #dc2626, 3px 3px 0 #000; letter-spacing: 5px; }
  #hud { top: 7vh; }"""


# =============================================================================
# Audio Profiles - distinct sound palettes per genre
# =============================================================================


def _audio_platformer(config: Any) -> str:
    # Cartoon bouncy: bright square waves, major chord collects, boing jumps
    return """
  // ===== Platformer Audio Profile (cartoon bouncy) =====
  sfxJump = function() { tone(420, 0.13, 'square', 0.10, 760); setTimeout(function(){ tone(760, 0.06, 'square', 0.08); }, 70); };
  sfxCollect = function() {
    var notes = [659, 784, 988, 1319];
    notes.forEach(function(f, i){ setTimeout(function(){ tone(f, 0.07, 'triangle', 0.12); }, i * 45); });
  };
  sfxStomp = function() { noiseBurst(0.08, 0.16, 1100); tone(180, 0.10, 'square', 0.10, 90); setTimeout(function(){ tone(660, 0.06, 'triangle', 0.10); }, 40); };
  sfxBounce = function() { tone(540, 0.10, 'sine', 0.14, 220); setTimeout(function(){ tone(880, 0.06, 'sine', 0.10); }, 50); };
  sfxPowerup = function() {
    var notes = [523, 659, 784, 1047, 1319];
    notes.forEach(function(f, i){ setTimeout(function(){ tone(f, 0.10, 'square', 0.11); }, i * 60); });
  };
  sfxGoal = function() {
    var notes = [523, 659, 784, 1047, 1319, 1568];
    notes.forEach(function(f, i){ setTimeout(function(){ tone(f, 0.16, 'triangle', 0.13); }, i * 90); });
  };"""


def _audio_shooter(config: Any) -> str:
    # Sci-fi: laser zaps (sawtooth sweep down), deep explosion booms, engine hum
    return """
  // ===== Shooter Audio Profile (sci-fi laser) =====
  sfxShoot = function() {
    tone(1400, 0.06, 'sawtooth', 0.10, 280);
    noiseBurst(0.03, 0.05, 3000);
  };
  sfxCollect = function() { tone(1320, 0.05, 'sine', 0.12, 1760); setTimeout(function(){ tone(1760, 0.04, 'sine', 0.10); }, 30); };
  sfxStomp = function() { sfxDamage(); };
  sfxDamage = function() {
    tone(120, 0.20, 'sawtooth', 0.16, 50);
    noiseBurst(0.15, 0.14, 500);
  };
  sfxPowerup = function() {
    tone(660, 0.08, 'square', 0.10, 990);
    setTimeout(function(){ tone(1320, 0.06, 'sawtooth', 0.10, 1760); }, 60);
    setTimeout(function(){ noiseBurst(0.04, 0.08, 4000); }, 100);
  };
  sfxBounce = function() { tone(800, 0.04, 'sine', 0.10, 1200); };
  sfxGoal = function() {
    [440, 554, 659, 880, 1108].forEach(function(f, i){ setTimeout(function(){ tone(f, 0.14, 'sawtooth', 0.12); }, i * 80); });
  };
  sfxGameOver = function() {
    tone(220, 0.4, 'sawtooth', 0.16, 60);
    setTimeout(function(){ noiseBurst(0.5, 0.18, 300); }, 100);
  };"""


def _audio_parkour(config: Any) -> str:
    # Motion: whooshes (filtered noise sweeps), heartbeat bass, wind ambient
    return """
  // ===== Parkour Audio Profile (motion whoosh) =====
  sfxJump = function() {
    noiseBurst(0.12, 0.10, 2000);
    tone(680, 0.10, 'sine', 0.08, 1200);
  };
  sfxCollect = function() { tone(1568, 0.05, 'sine', 0.12, 2093); setTimeout(function(){ tone(2093, 0.04, 'sine', 0.10); }, 25); };
  sfxStomp = function() { noiseBurst(0.06, 0.12, 2500); };
  sfxDamage = function() {
    tone(180, 0.18, 'sine', 0.14, 70);
    noiseBurst(0.10, 0.10, 800);
  };
  sfxPowerup = function() {
    [880, 1175, 1568, 2093].forEach(function(f, i){ setTimeout(function(){ tone(f, 0.06, 'sine', 0.10); }, i * 35); });
  };
  sfxBounce = function() { tone(440, 0.08, 'sine', 0.12, 880); noiseBurst(0.04, 0.06, 1800); };
  sfxCheckpoint = function() {
    tone(1047, 0.06, 'sine', 0.10, 1568);
    setTimeout(function(){ tone(1568, 0.10, 'sine', 0.10); }, 50);
  };
  sfxGoal = function() {
    [880, 1175, 1568, 2093, 2637].forEach(function(f, i){ setTimeout(function(){ tone(f, 0.10, 'sine', 0.12); }, i * 60); });
  };"""


def _audio_tank_battle(config: Any) -> str:
    # Military: low cannon booms (sine + noise), metal clanks, rumble engine
    return """
  // ===== Tank Battle Audio Profile (military cannon) =====
  sfxShoot = function() {
    tone(80, 0.18, 'sine', 0.20, 40);
    noiseBurst(0.12, 0.18, 400);
    setTimeout(function(){ tone(60, 0.10, 'sine', 0.12, 30); }, 30);
  };
  sfxCollect = function() { tone(440, 0.05, 'square', 0.10, 660); };
  sfxStomp = function() { sfxShoot(); };
  sfxDamage = function() {
    tone(90, 0.25, 'sawtooth', 0.18, 40);
    noiseBurst(0.20, 0.16, 300);
  };
  sfxBounce = function() { tone(140, 0.08, 'square', 0.12, 80); };
  sfxPowerup = function() {
    [330, 440, 550].forEach(function(f, i){ setTimeout(function(){ tone(f, 0.10, 'square', 0.10); }, i * 70); });
  };
  sfxCheckpoint = function() { tone(500, 0.08, 'square', 0.10, 700); setTimeout(function(){ tone(700, 0.10, 'square', 0.10); }, 60); };
  sfxGoal = function() {
    [262, 330, 392, 523].forEach(function(f, i){ setTimeout(function(){ tone(f, 0.20, 'square', 0.14); }, i * 130); });
  };
  sfxGameOver = function() {
    tone(110, 0.6, 'sawtooth', 0.18, 50);
    setTimeout(function(){ noiseBurst(0.4, 0.16, 250); }, 150);
  };"""


def _audio_puzzle(config: Any) -> str:
    # Neon crystal: chimes bells (sine + harmonics), soft pads, no explosions
    return """
  // ===== Puzzle Audio Profile (crystal chimes) =====
  sfxJump = function() { tone(880, 0.08, 'sine', 0.10, 1320); };
  sfxCollect = function() {
    tone(1047, 0.10, 'sine', 0.12);
    setTimeout(function(){ tone(1568, 0.10, 'sine', 0.10); }, 40);
    setTimeout(function(){ tone(2093, 0.12, 'sine', 0.08); }, 80);
  };
  sfxStomp = function() { tone(660, 0.06, 'sine', 0.10, 990); };
  sfxDamage = function() { tone(220, 0.15, 'sine', 0.10, 180); };
  sfxBounce = function() { tone(660, 0.08, 'sine', 0.10, 880); };
  sfxPowerup = function() {
    [784, 988, 1319, 1568].forEach(function(f, i){ setTimeout(function(){ tone(f, 0.12, 'sine', 0.11); }, i * 70); });
  };
  sfxCheckpoint = function() { tone(1175, 0.10, 'sine', 0.10, 1568); };
  sfxGoal = function() {
    [523, 659, 784, 1047, 1319, 1568, 2093].forEach(function(f, i){ setTimeout(function(){ tone(f, 0.14, 'sine', 0.12); }, i * 80); });
  };
  sfxGameOver = function() {
    [523, 440, 349, 262].forEach(function(f, i){ setTimeout(function(){ tone(f, 0.30, 'sine', 0.12); }, i * 180); });
  };"""


def _audio_boss_battle(config: Any) -> str:
    # Epic cinematic: orchestral stings (sawtooth chords), deep drum hits, dramatic
    return """
  // ===== Boss Battle Audio Profile (epic orchestral) =====
  sfxJump = function() { tone(330, 0.10, 'sawtooth', 0.10, 495); };
  sfxShoot = function() {
    tone(180, 0.10, 'sawtooth', 0.12, 90);
    noiseBurst(0.06, 0.08, 1200);
  };
  sfxCollect = function() { tone(784, 0.08, 'triangle', 0.12, 1047); setTimeout(function(){ tone(1047, 0.06, 'triangle', 0.10); }, 40); };
  sfxStomp = function() {
    tone(110, 0.15, 'sawtooth', 0.16, 55);
    noiseBurst(0.10, 0.12, 800);
  };
  sfxDamage = function() {
    tone(140, 0.25, 'sawtooth', 0.18, 60);
    noiseBurst(0.18, 0.16, 500);
  };
  sfxBounce = function() { tone(440, 0.10, 'triangle', 0.12, 660); };
  sfxPowerup = function() {
    [440, 554, 659, 880, 1108].forEach(function(f, i){ setTimeout(function(){ tone(f, 0.12, 'sawtooth', 0.12); }, i * 70); });
  };
  sfxCheckpoint = function() { tone(659, 0.10, 'triangle', 0.10, 880); setTimeout(function(){ tone(880, 0.12, 'triangle', 0.10); }, 60); };
  sfxGoal = function() {
    [392, 523, 659, 784, 1047, 1319].forEach(function(f, i){ setTimeout(function(){ tone(f, 0.18, 'sawtooth', 0.14); }, i * 110); });
  };
  sfxGameOver = function() {
    [330, 262, 196, 165, 131].forEach(function(f, i){ setTimeout(function(){ tone(f, 0.35, 'sawtooth', 0.16); }, i * 180); });
  };"""


# =============================================================================
# Effect Profiles - genre-specific particle behaviors
# =============================================================================


def _effects_platformer(config: Any) -> str:
    # Cartoon: dust puffs on landing, sparkle burst on collect, star on stomp
    return """
  // ===== Platformer Effect Profile (cartoon dust) =====
  var _origSpawnBurst = (typeof spawnBurst === 'function') ? spawnBurst : null;
  spawnBurst = function(x, y, color, count, speed) {
    if (_origSpawnBurst) _origSpawnBurst(x, y, color, count, speed);
    // Add bouncing dust puffs
    for (var i = 0; i < Math.floor(count * 0.6); i++) {
      particles.push({
        x: x + (Math.random() - 0.5) * 12, y: y,
        vx: (Math.random() - 0.5) * 3, vy: -1 - Math.random() * 1.5,
        life: 30, maxLife: 30, color: '#d4d4d4', size: 3 + Math.random() * 2, type: 'dot'
      });
    }
  };
  function spawnStompStars(x, y) {
    for (var i = 0; i < 6; i++) {
      var ang = (i / 6) * Math.PI * 2;
      particles.push({
        x: x, y: y, vx: Math.cos(ang) * 4, vy: Math.sin(ang) * 4 - 1,
        life: 25, maxLife: 25, color: '#fbbf24', size: 4, type: 'sparkle'
      });
    }
  }"""


def _effects_shooter(config: Any) -> str:
    # Sci-fi: engine trails, muzzle flash, explosion debris, shield ripple
    return """
  // ===== Shooter Effect Profile (sci-fi engine) =====
  var _origSpawnBurst = (typeof spawnBurst === 'function') ? spawnBurst : null;
  spawnBurst = function(x, y, color, count, speed) {
    // Explosion: debris + smoke
    for (var i = 0; i < count; i++) {
      var ang = Math.random() * Math.PI * 2;
      var spd = (speed || 5) * (0.4 + Math.random() * 0.8);
      particles.push({
        x: x, y: y, vx: Math.cos(ang) * spd, vy: Math.sin(ang) * spd,
        life: 35 + Math.random() * 20, maxLife: 55,
        color: Math.random() < 0.4 ? '#ffaa00' : (Math.random() < 0.5 ? color : '#888'),
        size: 2 + Math.random() * 3, type: 'dot'
      });
    }
    // Shockwave ring
    particles.push({ x: x, y: y, vx: 0, vy: 0, life: 18, maxLife: 18, color: '#fff', size: 4, type: 'ring' });
  };
  function spawnEngineTrail(x, y, color) {
    particles.push({
      x: x + (Math.random() - 0.5) * 4, y: y,
      vx: (Math.random() - 0.5) * 0.5, vy: 2 + Math.random() * 2,
      life: 18, maxLife: 18, color: color || '#00e5ff', size: 2 + Math.random() * 2, type: 'trail'
    });
  }
  function spawnMuzzleFlash(x, y, ang) {
    for (var i = 0; i < 5; i++) {
      var a = ang + (Math.random() - 0.5) * 0.6;
      particles.push({
        x: x, y: y, vx: Math.cos(a) * 6, vy: Math.sin(a) * 6,
        life: 8, maxLife: 8, color: '#ffff80', size: 3, type: 'sparkle'
      });
    }
  }"""


def _effects_parkour(config: Any) -> str:
    # Motion: speed lines, afterimage trail, landing impact dust, boost sparkle
    return """
  // ===== Parkour Effect Profile (motion speed) =====
  var _origSpawnBurst = (typeof spawnBurst === 'function') ? spawnBurst : null;
  spawnBurst = function(x, y, color, count, speed) {
    if (_origSpawnBurst) _origSpawnBurst(x, y, color, count, speed);
    // Horizontal speed lines
    for (var i = 0; i < count; i++) {
      particles.push({
        x: x + (Math.random() - 0.5) * 20, y: y + (Math.random() - 0.5) * 20,
        vx: -8 - Math.random() * 4, vy: 0,
        life: 12, maxLife: 12, color: color, size: 1 + Math.random() * 2, type: 'trail'
      });
    }
  };
  function spawnAfterimage(x, y, w, h, color) {
    particles.push({
      x: x, y: y, vx: 0, vy: 0, life: 10, maxLife: 10,
      color: color, size: 0, type: 'afterimage', w: w, h: h
    });
  }
  function spawnBoostSparkle(x, y) {
    for (var i = 0; i < 8; i++) {
      particles.push({
        x: x, y: y, vx: (Math.random() - 0.5) * 6, vy: (Math.random() - 0.5) * 6,
        life: 20, maxLife: 20, color: Math.random() < 0.5 ? '#00e5ff' : '#ff00ff',
        size: 2 + Math.random() * 2, type: 'sparkle'
      });
    }
  }"""


def _effects_tank_battle(config: Any) -> str:
    # Military: smoke puffs, debris on wall destruction, muzzle flash, tread marks
    return """
  // ===== Tank Battle Effect Profile (military smoke) =====
  var _origSpawnBurst = (typeof spawnBurst === 'function') ? spawnBurst : null;
  spawnBurst = function(x, y, color, count, speed) {
    // Smoke puffs rising
    for (var i = 0; i < count; i++) {
      particles.push({
        x: x + (Math.random() - 0.5) * 16, y: y + (Math.random() - 0.5) * 8,
        vx: (Math.random() - 0.5) * 1.5, vy: -1 - Math.random() * 1.5,
        life: 40 + Math.random() * 20, maxLife: 60,
        color: Math.random() < 0.5 ? '#6b6b6b' : '#8b4513',
        size: 4 + Math.random() * 4, type: 'dot'
      });
    }
    // Debris flying
    for (var i = 0; i < Math.floor(count * 0.5); i++) {
      var ang = Math.random() * Math.PI * 2;
      var spd = 3 + Math.random() * 4;
      particles.push({
        x: x, y: y, vx: Math.cos(ang) * spd, vy: Math.sin(ang) * spd - 1,
        life: 30, maxLife: 30, color: '#8b4513', size: 2 + Math.random() * 2, type: 'dot'
      });
    }
  };
  function spawnTreadMark(x, y, dir) {
    particles.push({
      x: x, y: y, vx: 0, vy: 0, life: 120, maxLife: 120,
      color: 'rgba(60,40,20,0.4)', size: 3, type: 'treadmark', dir: dir || 'h'
    });
  }
  function spawnCannonSmoke(x, y, dir) {
    for (var i = 0; i < 6; i++) {
      var dx = dir === 'left' ? -1 : (dir === 'right' ? 1 : 0);
      var dy = dir === 'up' ? -1 : (dir === 'down' ? 1 : 0);
      particles.push({
        x: x, y: y, vx: dx * (2 + Math.random()) + (Math.random() - 0.5),
        vy: dy * (2 + Math.random()) + (Math.random() - 0.5),
        life: 25, maxLife: 25, color: '#d4d4d4', size: 4 + Math.random() * 3, type: 'dot'
      });
    }
  }"""


def _effects_puzzle(config: Any) -> str:
    # Neon crystal: crystal shards, ripple on placement, cascade sparkle float
    return """
  // ===== Puzzle Effect Profile (crystal cascade) =====
  var _origSpawnBurst = (typeof spawnBurst === 'function') ? spawnBurst : null;
  spawnBurst = function(x, y, color, count, speed) {
    // Crystal shards spinning outward
    for (var i = 0; i < count; i++) {
      var ang = (i / count) * Math.PI * 2 + Math.random() * 0.3;
      var spd = (speed || 4) * (0.5 + Math.random() * 0.7);
      particles.push({
        x: x, y: y, vx: Math.cos(ang) * spd, vy: Math.sin(ang) * spd,
        life: 50, maxLife: 50, color: Math.random() < 0.4 ? '#fff' : color,
        size: 2 + Math.random() * 3, type: 'shard', rot: Math.random() * Math.PI, rotV: (Math.random() - 0.5) * 0.3
      });
    }
    // Ripple ring
    particles.push({ x: x, y: y, vx: 0, vy: 0, life: 30, maxLife: 30, color: color, size: 4, type: 'ring' });
  };
  function spawnFloatSparkle(x, y, color) {
    particles.push({
      x: x + (Math.random() - 0.5) * 30, y: y,
      vx: (Math.random() - 0.5) * 0.5, vy: -0.5 - Math.random() * 1,
      life: 60 + Math.random() * 40, maxLife: 100,
      color: Math.random() < 0.5 ? color : '#a855f7',
      size: 1 + Math.random() * 2, type: 'sparkle'
    });
  }"""


def _effects_boss_battle(config: Any) -> str:
    # Epic: shockwave on boss hit, ember particles, screen flash on phase change
    return """
  // ===== Boss Battle Effect Profile (epic shockwave) =====
  var _origSpawnBurst = (typeof spawnBurst === 'function') ? spawnBurst : null;
  spawnBurst = function(x, y, color, count, speed) {
    if (_origSpawnBurst) _origSpawnBurst(x, y, color, count, speed);
    // Embers floating up
    for (var i = 0; i < Math.floor(count * 0.7); i++) {
      particles.push({
        x: x + (Math.random() - 0.5) * 16, y: y,
        vx: (Math.random() - 0.5) * 2, vy: -2 - Math.random() * 2,
        life: 40 + Math.random() * 30, maxLife: 70,
        color: Math.random() < 0.5 ? '#ff6600' : '#ffaa00',
        size: 2 + Math.random() * 2, type: 'sparkle'
      });
    }
    // Shockwave ring
    particles.push({ x: x, y: y, vx: 0, vy: 0, life: 22, maxLife: 22, color: '#fff', size: 6, type: 'ring' });
  };
  function spawnShockwave(x, y, color) {
    particles.push({ x: x, y: y, vx: 0, vy: 0, life: 28, maxLife: 28, color: color || '#fff', size: 8, type: 'ring' });
    particles.push({ x: x, y: y, vx: 0, vy: 0, life: 18, maxLife: 18, color: '#fff', size: 4, type: 'ring' });
  }
  function spawnPhaseChange(x, y) {
    for (var i = 0; i < 20; i++) {
      var ang = (i / 20) * Math.PI * 2;
      particles.push({
        x: x, y: y, vx: Math.cos(ang) * 7, vy: Math.sin(ang) * 7,
        life: 50, maxLife: 50, color: '#dc2626', size: 4, type: 'sparkle'
      });
    }
    spawnShockwave(x, y, '#dc2626');
  }"""


# =============================================================================
# Post-Process Profiles - canvas post-processing per frame
# =============================================================================


def _post_process_platformer(config: Any) -> str:
    # Cartoon: subtle vignette only (CSS handles saturation)
    return """
  function applyPostProcess() {
    // Soft cartoon vignette
    var grad = ctx.createRadialGradient(W/2, H/2, Math.min(W,H)*0.4, W/2, H/2, Math.max(W,H)*0.7);
    grad.addColorStop(0, 'rgba(0,0,0,0)');
    grad.addColorStop(1, 'rgba(0,0,0,0.35)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);
  }"""


def _post_process_shooter(config: Any) -> str:
    # Sci-fi: chromatic aberration glow on bright pixels (simplified: cyan/magenta overlay)
    return """
  function applyPostProcess() {
    // CRT scanline drift (subtle)
    ctx.globalAlpha = 0.04;
    ctx.fillStyle = '#00e5ff';
    for (var y = 0; y < H; y += 3) { ctx.fillRect(0, y, W, 1); }
    ctx.globalAlpha = 1;
    // Edge glow
    var grad = ctx.createRadialGradient(W/2, H/2, Math.min(W,H)*0.3, W/2, H/2, Math.max(W,H)*0.7);
    grad.addColorStop(0, 'rgba(0,0,0,0)');
    grad.addColorStop(1, 'rgba(0,30,60,0.5)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);
  }"""


def _post_process_parkour(config: Any) -> str:
    # Motion: speed lines when moving fast (driven by player velocity)
    return """
  function applyPostProcess() {
    if (typeof player !== 'undefined' && player) {
      var spd = Math.abs(player.vx || 0);
      if (spd > 5) {
        var intensity = Math.min(0.4, (spd - 5) * 0.08);
        ctx.globalAlpha = intensity;
        ctx.strokeStyle = '#00e5ff';
        ctx.lineWidth = 1;
        for (var i = 0; i < 12; i++) {
          var y = Math.random() * H;
          var len = 40 + Math.random() * 80;
          ctx.beginPath();
          ctx.moveTo(W - len, y);
          ctx.lineTo(W, y);
          ctx.stroke();
        }
        ctx.globalAlpha = 1;
      }
    }
    // Cyan vignette
    var grad = ctx.createRadialGradient(W/2, H/2, Math.min(W,H)*0.35, W/2, H/2, Math.max(W,H)*0.75);
    grad.addColorStop(0, 'rgba(0,0,0,0)');
    grad.addColorStop(1, 'rgba(0,40,60,0.4)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);
  }"""


def _post_process_tank_battle(config: Any) -> str:
    # Military: scanline grid + slight green tint
    return """
  function applyPostProcess() {
    // Subtle scanlines
    ctx.globalAlpha = 0.05;
    ctx.fillStyle = '#000';
    for (var y = 0; y < H; y += 2) { ctx.fillRect(0, y, W, 1); }
    ctx.globalAlpha = 1;
    // Brown/green military tint
    var grad = ctx.createRadialGradient(W/2, H/2, Math.min(W,H)*0.4, W/2, H/2, Math.max(W,H)*0.75);
    grad.addColorStop(0, 'rgba(0,0,0,0)');
    grad.addColorStop(1, 'rgba(20,15,5,0.5)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);
  }"""


def _post_process_puzzle(config: Any) -> str:
    # Neon: bloom-like glow on purple/white + soft float
    return """
  function applyPostProcess() {
    // Purple bloom
    ctx.globalCompositeOperation = 'screen';
    var grad = ctx.createRadialGradient(W/2, H/2, Math.min(W,H)*0.2, W/2, H/2, Math.max(W,H)*0.7);
    grad.addColorStop(0, 'rgba(40,10,60,0.15)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'source-over';
    // Deep vignette
    var grad2 = ctx.createRadialGradient(W/2, H/2, Math.min(W,H)*0.3, W/2, H/2, Math.max(W,H)*0.75);
    grad2.addColorStop(0, 'rgba(0,0,0,0)');
    grad2.addColorStop(1, 'rgba(10,0,20,0.6)');
    ctx.fillStyle = grad2;
    ctx.fillRect(0, 0, W, H);
  }"""


def _post_process_boss_battle(config: Any) -> str:
    # Epic: dramatic vignette + red flash on low HP
    return """
  function applyPostProcess() {
    // Dramatic vignette
    var grad = ctx.createRadialGradient(W/2, H/2, Math.min(W,H)*0.25, W/2, H/2, Math.max(W,H)*0.75);
    grad.addColorStop(0, 'rgba(0,0,0,0)');
    grad.addColorStop(1, 'rgba(0,0,0,0.6)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);
    // Red tint when player low HP
    if (typeof lives !== 'undefined' && lives <= 1) {
      ctx.fillStyle = 'rgba(120,0,0,0.15)';
      ctx.fillRect(0, 0, W, H);
    }
  }"""


# =============================================================================
# Profile Registries
# =============================================================================


_CSS_PROFILES = {
    "platformer": _css_platformer,
    "shooter": _css_shooter,
    "parkour": _css_parkour,
    "tank_battle": _css_tank_battle,
    "puzzle": _css_puzzle,
    "boss_battle": _css_boss_battle,
}

_AUDIO_PROFILES = {
    "platformer": _audio_platformer,
    "shooter": _audio_shooter,
    "parkour": _audio_parkour,
    "tank_battle": _audio_tank_battle,
    "puzzle": _audio_puzzle,
    "boss_battle": _audio_boss_battle,
}

_EFFECT_PROFILES = {
    "platformer": _effects_platformer,
    "shooter": _effects_shooter,
    "parkour": _effects_parkour,
    "tank_battle": _effects_tank_battle,
    "puzzle": _effects_puzzle,
    "boss_battle": _effects_boss_battle,
}

_POST_PROCESS_PROFILES = {
    "platformer": _post_process_platformer,
    "shooter": _post_process_shooter,
    "parkour": _post_process_parkour,
    "tank_battle": _post_process_tank_battle,
    "puzzle": _post_process_puzzle,
    "boss_battle": _post_process_boss_battle,
}


# DOM overlay elements injected once at game start
_DOM_OVERLAY_HTML = {
    "platformer": '<div class="vignette-overlay"></div>',
    "shooter": '<div class="crt-scanlines"></div><div class="crt-vignette"></div>',
    "parkour": '<div class="speed-overlay"></div>',
    "tank_battle": '<div class="grid-overlay"></div><div class="crt-vignette"></div>',
    "puzzle": '<div class="bloom-overlay"></div>',
    "boss_battle": '<div class="letterbox-top"></div><div class="letterbox-bottom"></div><div class="cinematic-vignette"></div>',
}


def get_dom_overlay_html(genre: str) -> str:
    """Return DOM overlay elements (scanlines, vignettes, etc.) for the genre."""
    return _DOM_OVERLAY_HTML.get(genre, "")


def has_profile(genre: str) -> bool:
    """Return True if a genre has a dedicated asset profile."""
    return genre in _CSS_PROFILES
