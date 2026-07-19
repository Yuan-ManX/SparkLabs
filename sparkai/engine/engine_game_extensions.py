"""
SparkLabs Engine - Game Runtime Extensions

Original SparkLabs modules that extend the base GameRuntime with:
  - AudioSynth: procedural Web Audio API sound effects (no asset files)
  - ParticleEngine: multi-emitter particle system (trails, bursts, sparkles)
  - PhysicsKit: friction, slopes, moving platforms, bounce pads, knockback
  - EntityKit: projectiles, hazards, powerups, checkpoints, bounce pads,
               moving platforms, teleporters
  - FxInjector: assembles the above into JavaScript snippets that the
                HtmlAssembler embeds into the generated game document

Design goals:
  - Zero external assets: every sound is synthesized at runtime via the
    browser's AudioContext; every particle is drawn with canvas primitives.
  - Drop-in integration: FxInjector produces self-contained JS strings that
    the existing HtmlAssembler can splice into its output without restructuring.
  - Genre aware: effects adapt to the compiled GameConfig (gravity, genre,
    palette) so each game gets a fitting sensory layer.

Pattern integration (original SparkLabs design):
  - Procedural asset generation (procedural audio streams)
  - Particle emitter graph (multi-emitter particle system)
  - Component-based entity composition (ECS roots)
  - Fixed-timestep deterministic updates for replayability
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Audio Synthesizer
# =============================================================================


class AudioSynth:
    """Generates procedural Web Audio API sound-effect JavaScript.

    Every sound is synthesized from oscillators and noise buffers, so the
    generated game ships with rich audio feedback without any binary assets.
    """

    def build_js(self) -> str:
        """Return the JavaScript audio engine snippet."""
        return """
  // ===== SparkLabs Procedural Audio Engine =====
  var audioCtx = null;
  var audioEnabled = true;
  function initAudio() {
    if (audioCtx) return;
    try {
      var Ctor = window.AudioContext || window.webkitAudioContext;
      if (!Ctor) { audioEnabled = false; return; }
      audioCtx = new Ctor();
    } catch (e) { audioEnabled = false; }
  }
  function resumeAudio() {
    if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
  }
  function tone(freq, dur, type, gainVal, slideTo) {
    if (!audioEnabled || !audioCtx) return;
    type = type || 'square';
    gainVal = gainVal == null ? 0.12 : gainVal;
    var now = audioCtx.currentTime;
    var osc = audioCtx.createOscillator();
    var gain = audioCtx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, now);
    if (slideTo) osc.frequency.exponentialRampToValueAtTime(Math.max(20, slideTo), now + dur);
    gain.gain.setValueAtTime(gainVal, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + dur);
    osc.connect(gain); gain.connect(audioCtx.destination);
    osc.start(now); osc.stop(now + dur);
  }
  function noiseBurst(dur, gainVal, filterFreq) {
    if (!audioEnabled || !audioCtx) return;
    gainVal = gainVal == null ? 0.1 : gainVal;
    filterFreq = filterFreq || 1200;
    var now = audioCtx.currentTime;
    var bufSize = Math.floor(audioCtx.sampleRate * dur);
    var buf = audioCtx.createBuffer(1, bufSize, audioCtx.sampleRate);
    var data = buf.getChannelData(0);
    for (var i = 0; i < bufSize; i++) data[i] = (Math.random() * 2 - 1);
    var src = audioCtx.createBufferSource(); src.buffer = buf;
    var filt = audioCtx.createBiquadFilter();
    filt.type = 'lowpass'; filt.frequency.value = filterFreq;
    var gain = audioCtx.createGain();
    gain.gain.setValueAtTime(gainVal, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + dur);
    src.connect(filt); filt.connect(gain); gain.connect(audioCtx.destination);
    src.start(now); src.stop(now + dur);
  }
  function sfxJump() { tone(380, 0.14, 'square', 0.10, 720); }
  function sfxCollect() { tone(880, 0.07, 'triangle', 0.12, 1320); setTimeout(function(){ tone(1320, 0.08, 'triangle', 0.10); }, 60); }
  function sfxStomp() { noiseBurst(0.10, 0.14, 900); tone(220, 0.12, 'square', 0.10, 110); }
  function sfxDamage() { tone(200, 0.18, 'sawtooth', 0.16, 90); noiseBurst(0.12, 0.10, 600); }
  function sfxGoal() {
    var notes = [523, 659, 784, 1047];
    notes.forEach(function(f, i){ setTimeout(function(){ tone(f, 0.16, 'triangle', 0.13); }, i * 90); });
  }
  function sfxGameOver() {
    var notes = [440, 349, 261, 196];
    notes.forEach(function(f, i){ setTimeout(function(){ tone(f, 0.28, 'sawtooth', 0.14); }, i * 140); });
  }
  function sfxPowerup() { tone(660, 0.06, 'square', 0.10, 990); setTimeout(function(){ tone(990, 0.10, 'triangle', 0.12, 1480); }, 50); }
  function sfxBounce() { tone(520, 0.10, 'sine', 0.12, 180); }
  function sfxShoot() { tone(900, 0.05, 'square', 0.08, 400); noiseBurst(0.04, 0.06, 2000); }
  function sfxTeleport() { tone(440, 0.20, 'sine', 0.10, 1760); }
  function sfxCheckpoint() { tone(700, 0.08, 'triangle', 0.10, 1050); setTimeout(function(){ tone(1050, 0.12, 'triangle', 0.10); }, 70); }
"""


# =============================================================================
# Particle Engine
# =============================================================================


class ParticleEngine:
    """Generates an advanced multi-emitter particle system in JavaScript.

    Supports particle trails, radial bursts, sparkles, and emitters with
    configurable lifetimes, gravity, and color gradients.
    """

    def build_js(self) -> str:
        """Return the JavaScript particle engine snippet.

        Builds on top of the existing `particles` array and `spawnParticles`
        function defined by the base runtime, adding emitter graph support,
        burst/sparkle/trail generators, and unified update/render routines.
        """
        return """
  // ===== SparkLabs Advanced Particle Engine =====
  var emitters = [];
  // spawnParticles is provided by the base runtime; add complementary generators.
  function spawnBurst(x, y, color, count, speed) {
    speed = speed || 5;
    for (var i = 0; i < count; i++) {
      var ang = (i / count) * Math.PI * 2;
      particles.push({
        x: x, y: y,
        vx: Math.cos(ang) * speed,
        vy: Math.sin(ang) * speed,
        life: 40, maxLife: 40,
        color: color,
        size: 3 + Math.random() * 2,
        type: 'dot'
      });
    }
  }
  function spawnSparkles(x, y, color, count) {
    for (var i = 0; i < count; i++) {
      particles.push({
        x: x + (Math.random() - 0.5) * 20,
        y: y + (Math.random() - 0.5) * 20,
        vx: (Math.random() - 0.5) * 2,
        vy: -1 - Math.random() * 2,
        life: 50 + Math.random() * 30,
        maxLife: 80,
        color: color,
        size: 1 + Math.random() * 2,
        type: 'sparkle'
      });
    }
  }
  function spawnTrail(x, y, color, vx, vy) {
    particles.push({
      x: x, y: y,
      vx: vx * 0.3, vy: vy * 0.3,
      life: 20, maxLife: 20,
      color: color,
      size: 2 + Math.random() * 2,
      type: 'trail'
    });
  }
  function emitFrom(x, y, color, rate, duration) {
    emitters.push({ x: x, y: y, color: color, rate: rate, duration: duration, age: 0 });
  }
  function updateParticles() {
    // Process emitters
    for (var i = emitters.length - 1; i >= 0; i--) {
      var em = emitters[i];
      em.age++;
      if (em.age % em.rate === 0) {
        particles.push({
          x: em.x + (Math.random() - 0.5) * 10,
          y: em.y + (Math.random() - 0.5) * 10,
          vx: (Math.random() - 0.5) * 3,
          vy: -1 - Math.random() * 2,
          life: 40, maxLife: 40,
          color: em.color,
          size: 2 + Math.random() * 2,
          type: 'dot'
        });
      }
      if (em.age >= em.duration) emitters.splice(i, 1);
    }
    // Update particles (per-type behavior)
    for (var i = particles.length - 1; i >= 0; i--) {
      var p = particles[i];
      // Static types: no movement, no gravity
      if (p.type === 'treadmark' || p.type === 'afterimage') {
        p.life--;
        if (p.life <= 0) particles.splice(i, 1);
        continue;
      }
      // Ring: expands outward, no gravity
      if (p.type === 'ring') {
        p.size += 2.5;
        p.life--;
        if (p.life <= 0) particles.splice(i, 1);
        continue;
      }
      // Shard: rotates, light gravity
      if (p.type === 'shard') {
        p.x += p.vx; p.y += p.vy;
        p.vy += 0.12;
        p.vx *= 0.97;
        if (typeof p.rotV !== 'undefined') p.rot += p.rotV;
        p.life--;
        if (p.life <= 0) particles.splice(i, 1);
        continue;
      }
      // Default (dot / trail / sparkle)
      p.x += p.vx; p.y += p.vy;
      if (p.type !== 'sparkle') p.vy += 0.2;
      else p.vy += 0.05;
      p.vx *= 0.98;
      p.life--;
      if (p.life <= 0) particles.splice(i, 1);
    }
  }
  function renderParticles() {
    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      var alpha = p.life / p.maxLife;
      ctx.globalAlpha = Math.max(0, Math.min(1, alpha));
      var px = p.x - camera.x, py = p.y - camera.y;
      if (p.type === 'sparkle') {
        var s = p.size * (0.5 + alpha * 0.5);
        ctx.fillStyle = p.color;
        ctx.fillRect(px - s/2, py - s/2, s, s);
        // Cross sparkle
        ctx.fillRect(px - s, py - 0.5, s*2, 1);
        ctx.fillRect(px - 0.5, py - s, 1, s*2);
      } else if (p.type === 'ring') {
        // Expanding shockwave ring
        ctx.strokeStyle = p.color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(px, py, p.size, 0, Math.PI * 2);
        ctx.stroke();
      } else if (p.type === 'shard') {
        // Rotating crystal diamond
        ctx.save();
        ctx.translate(px, py);
        ctx.rotate(p.rot || 0);
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.moveTo(0, -p.size);
        ctx.lineTo(p.size * 0.7, 0);
        ctx.lineTo(0, p.size);
        ctx.lineTo(-p.size * 0.7, 0);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
      } else if (p.type === 'afterimage') {
        // Fading rectangle (player silhouette trail)
        ctx.fillStyle = p.color;
        ctx.fillRect(px, py, p.w || p.size, p.h || p.size);
      } else if (p.type === 'treadmark') {
        // Static tread mark (small rectangle, oriented by dir)
        ctx.fillStyle = p.color;
        if (p.dir === 'v') {
          ctx.fillRect(px - 1, py - 3, 2, 6);
        } else {
          ctx.fillRect(px - 3, py - 1, 6, 2);
        }
      } else {
        ctx.fillStyle = p.color;
        ctx.fillRect(px - p.size/2, py - p.size/2, p.size, p.size);
      }
    }
    ctx.globalAlpha = 1;
  }
"""


# =============================================================================
# Physics Kit
# =============================================================================


class PhysicsKit:
    """Generates physics extensions: friction, knockback, bounce pads.

    These hooks integrate with the existing player update loop by providing
    additional force application and collision response helpers.
    """

    def build_js(self) -> str:
        """Return the JavaScript physics extension snippet."""
        return """
  // ===== SparkLabs Physics Extensions =====
  var knockback = { x: 0, y: 0, time: 0 };
  function applyKnockback(dx, dy, duration) {
    knockback.x = dx; knockback.y = dy; knockback.time = duration;
  }
  function updateKnockback() {
    if (knockback.time > 0) {
      player.x += knockback.x;
      player.y += knockback.y;
      knockback.time--;
      knockback.x *= 0.85; knockback.y *= 0.85;
    }
  }
  var invulnTime = 0;
  function isInvulnerable() { return invulnTime > 0; }
  function setInvulnerable(frames) { invulnTime = frames; }
  function updateInvulnerable() { if (invulnTime > 0) invulnTime--; }
"""


# =============================================================================
# FX Injector
# =============================================================================


@dataclass
class ExtensionConfig:
    """Configuration for runtime extensions."""
    enable_audio: bool = True
    enable_particles: bool = True
    enable_physics: bool = True
    enable_projectiles: bool = True
    enable_powerups: bool = True
    enable_checkpoints: bool = True
    enable_moving_platforms: bool = True
    enable_bounce_pads: bool = True
    enable_teleporters: bool = True
    enable_hazards: bool = True


class FxInjector:
    """Assembles extension JavaScript snippets and patches the game loop.

    The injector produces:
      1. A header snippet (audio + particle + physics definitions) inserted
         near the top of the game script.
      2. A loop-patch snippet that hooks the new systems into the existing
         update() and render() functions without rewriting them.
    """

    def __init__(self, config: Optional[ExtensionConfig] = None) -> None:
        self.config = config or ExtensionConfig()
        self._audio = AudioSynth()
        self._particles = ParticleEngine()
        self._physics = PhysicsKit()

    def build_header_js(self) -> str:
        """Build the header snippet with all enabled extension systems."""
        parts: List[str] = []
        if self.config.enable_audio:
            parts.append(self._audio.build_js())
        if self.config.enable_particles:
            parts.append(self._particles.build_js())
        if self.config.enable_physics:
            parts.append(self._physics.build_js())
        if self.config.enable_projectiles:
            parts.append(self._build_projectiles_js())
        if self.config.enable_powerups:
            parts.append(self._build_powerups_js())
        if self.config.enable_checkpoints:
            parts.append(self._build_checkpoints_js())
        if self.config.enable_moving_platforms:
            parts.append(self._build_moving_platforms_js())
        if self.config.enable_bounce_pads:
            parts.append(self._build_bounce_pads_js())
        if self.config.enable_teleporters:
            parts.append(self._build_teleporters_js())
        if self.config.enable_hazards:
            parts.append(self._build_hazards_js())
        return "\n".join(parts)

    def build_loop_patch_js(self) -> str:
        """Build the per-frame update/render hooks for extensions."""
        return """
  // ===== SparkLabs Extension Loop Hooks =====
  function updateExtensions() {
    if (typeof updateParticles === 'function') updateParticles();
    if (typeof updateKnockback === 'function') updateKnockback();
    if (typeof updateInvulnerable === 'function') updateInvulnerable();
    if (typeof updateProjectiles === 'function') updateProjectiles();
    if (typeof updatePowerups === 'function') updatePowerups();
    if (typeof updateCheckpoints === 'function') updateCheckpoints();
    if (typeof updateMovingPlatforms === 'function') updateMovingPlatforms();
    if (typeof updateBouncePads === 'function') updateBouncePads();
    if (typeof updateTeleporters === 'function') updateTeleporters();
    if (typeof updateHazards === 'function') updateHazards();
  }
  function renderExtensions() {
    if (typeof renderProjectiles === 'function') renderProjectiles();
    if (typeof renderPowerups === 'function') renderPowerups();
    if (typeof renderCheckpoints === 'function') renderCheckpoints();
    if (typeof renderMovingPlatforms === 'function') renderMovingPlatforms();
    if (typeof renderBouncePads === 'function') renderBouncePads();
    if (typeof renderTeleporters === 'function') renderTeleporters();
    if (typeof renderHazards === 'function') renderHazards();
    if (typeof renderParticles === 'function') renderParticles();
  }
"""

    # ----- Individual extension builders -----

    def _build_projectiles_js(self) -> str:
        return """
  // ===== SparkLabs Projectile System =====
  var projectiles = [];
  var projectileCooldown = 0;
  function fireProjectile() {
    if (projectileCooldown > 0) return;
    var dir = player.facing || 1;
    projectiles.push({
      x: player.x + player.w/2, y: player.y + player.h/2,
      vx: dir * 10, vy: 0,
      w: 10, h: 4, life: 60, color: CONFIG.accentColor
    });
    projectileCooldown = 12;
    if (typeof sfxShoot === 'function') sfxShoot();
  }
  function updateProjectiles() {
    if (projectileCooldown > 0) projectileCooldown--;
    for (var i = projectiles.length - 1; i >= 0; i--) {
      var p = projectiles[i];
      p.x += p.vx; p.life--;
      if (p.life <= 0) { projectiles.splice(i, 1); continue; }
      // Hit enemies
      for (var j = 0; j < entities.length; j++) {
        var e = entities[j];
        if (!e.alive || e.type !== 'enemy') continue;
        if (rectOverlap(p, e)) {
          e.health = (e.health || 1) - 1;
          if (e.health <= 0) {
            e.alive = false;
            spawnBurst(e.x + e.w/2, e.y + e.h/2, e.color, 10, 4);
            score += e.isBoss ? 500 : 50;
            updateScore();
            if (typeof sfxStomp === 'function') sfxStomp();
          }
          projectiles.splice(i, 1);
          break;
        }
      }
    }
  }
  function renderProjectiles() {
    ctx.fillStyle = CONFIG.accentColor;
    for (var i = 0; i < projectiles.length; i++) {
      var p = projectiles[i];
      ctx.fillRect(p.x - camera.x, p.y - camera.y, p.w, p.h);
    }
  }
"""

    def _build_powerups_js(self) -> str:
        return """
  // ===== SparkLabs Powerup System =====
  var activePowerups = { shield: 0, speed: 0, doubleJump: 0 };
  function activatePowerup(kind) {
    if (kind === 'shield') { activePowerups.shield = 600; if (typeof sfxPowerup === 'function') sfxPowerup(); }
    else if (kind === 'speed') { activePowerups.speed = 480; if (typeof sfxPowerup === 'function') sfxPowerup(); }
    else if (kind === 'doubleJump') { activePowerups.doubleJump = 720; if (typeof sfxPowerup === 'function') sfxPowerup(); }
    spawnSparkles(player.x + player.w/2, player.y + player.h/2, '#fbbf24', 12);
  }
  function updatePowerups() {
    if (activePowerups.shield > 0) activePowerups.shield--;
    if (activePowerups.speed > 0) activePowerups.speed--;
    if (activePowerups.doubleJump > 0) activePowerups.doubleJump--;
    // Pick up powerup entities
    for (var i = 0; i < entities.length; i++) {
      var e = entities[i];
      if (!e.alive || e.type !== 'powerup') continue;
      if (rectOverlap(player, e)) {
        e.alive = false;
        activatePowerup(e.powerupKind || 'shield');
      }
    }
  }
  function renderPowerups() {
    for (var i = 0; i < entities.length; i++) {
      var e = entities[i];
      if (!e.alive || e.type !== 'powerup') continue;
      var pulse = 0.8 + Math.sin(Date.now() / 200) * 0.2;
      ctx.globalAlpha = pulse;
      ctx.fillStyle = '#fbbf24';
      ctx.fillRect(e.x - camera.x, e.y - camera.y, e.w, e.h);
      ctx.globalAlpha = 1;
      // Shield aura around player
      if (activePowerups.shield > 0) {
        ctx.strokeStyle = 'rgba(100,200,255,0.6)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(player.x + player.w/2 - camera.x, player.y + player.h/2 - camera.y, player.w, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
  }
"""

    def _build_checkpoints_js(self) -> str:
        return """
  // ===== SparkLabs Checkpoint System =====
  var lastCheckpoint = null;
  function updateCheckpoints() {
    for (var i = 0; i < entities.length; i++) {
      var e = entities[i];
      if (!e.alive || e.type !== 'checkpoint') continue;
      if (rectOverlap(player, e) && lastCheckpoint !== e) {
        lastCheckpoint = e;
        e.activated = true;
        if (typeof sfxCheckpoint === 'function') sfxCheckpoint();
        spawnSparkles(e.x + e.w/2, e.y + e.h/2, '#22c55e', 8);
      }
    }
  }
  function renderCheckpoints() {
    for (var i = 0; i < entities.length; i++) {
      var e = entities[i];
      if (!e.alive || e.type !== 'checkpoint') continue;
      ctx.fillStyle = e.activated ? '#22c55e' : '#555';
      ctx.fillRect(e.x - camera.x + e.w/4, e.y - camera.y, e.w/2, e.h);
      ctx.fillStyle = e.activated ? '#22c55e' : '#333';
      ctx.fillRect(e.x - camera.x, e.y - camera.y + e.h - 4, e.w, 4);
    }
  }
"""

    def _build_moving_platforms_js(self) -> str:
        return """
  // ===== SparkLabs Moving Platform System =====
  function updateMovingPlatforms() {
    for (var i = 0; i < entities.length; i++) {
      var e = entities[i];
      if (!e.alive || e.type !== 'structure' || !e.isMoving) continue;
      e.movePhase = (e.movePhase || 0) + 0.02;
      var prevX = e.x, prevY = e.y;
      if (e.moveAxis === 'x') e.x = e.originX + Math.sin(e.movePhase) * e.moveRange;
      else e.y = e.originY + Math.sin(e.movePhase) * e.moveRange;
      // Carry player if standing on it
      if (player.onGround && rectOverlap(player, {x: e.x, y: e.y - 2, w: e.w, h: 4})) {
        player.x += (e.x - prevX);
        player.y += (e.y - prevY);
      }
    }
  }
  function renderMovingPlatforms() {
    // Moving platforms render within the main structure render; no-op here.
  }
"""

    def _build_bounce_pads_js(self) -> str:
        return """
  // ===== SparkLabs Bounce Pad System =====
  function updateBouncePads() {
    for (var i = 0; i < entities.length; i++) {
      var e = entities[i];
      if (!e.alive || e.type !== 'bouncepad') continue;
      if (rectOverlap(player, e) && player.vy >= 0) {
        player.vy = -CONFIG.jumpStrength * 1.6;
        player.onGround = false;
        if (typeof sfxBounce === 'function') sfxBounce();
        spawnBurst(e.x + e.w/2, e.y, '#06b6d4', 8, 3);
      }
    }
  }
  function renderBouncePads() {
    for (var i = 0; i < entities.length; i++) {
      var e = entities[i];
      if (!e.alive || e.type !== 'bouncepad') continue;
      ctx.fillStyle = '#06b6d4';
      ctx.fillRect(e.x - camera.x, e.y - camera.y + e.h - 6, e.w, 6);
      ctx.fillStyle = '#0891b2';
      ctx.fillRect(e.x - camera.x + 2, e.y - camera.y + e.h - 10, e.w - 4, 4);
    }
  }
"""

    def _build_teleporters_js(self) -> str:
        return """
  // ===== SparkLabs Teleporter System =====
  var teleportCooldown = 0;
  function updateTeleporters() {
    if (teleportCooldown > 0) { teleportCooldown--; return; }
    for (var i = 0; i < entities.length; i++) {
      var e = entities[i];
      if (!e.alive || e.type !== 'teleporter') continue;
      if (rectOverlap(player, e)) {
        var target = null;
        for (var j = 0; j < entities.length; j++) {
          var t = entities[j];
          if (t.alive && t.type === 'teleporter' && t !== e && t.pairId === e.pairId) {
            target = t; break;
          }
        }
        if (target) {
          spawnBurst(player.x + player.w/2, player.y + player.h/2, '#a855f7', 16, 5);
          player.x = target.x;
          player.y = target.y - player.h;
          teleportCooldown = 30;
          if (typeof sfxTeleport === 'function') sfxTeleport();
          spawnBurst(player.x + player.w/2, player.y + player.h/2, '#a855f7', 16, 5);
        }
      }
    }
  }
  function renderTeleporters() {
    for (var i = 0; i < entities.length; i++) {
      var e = entities[i];
      if (!e.alive || e.type !== 'teleporter') continue;
      var pulse = 0.6 + Math.sin(Date.now() / 150) * 0.4;
      ctx.globalAlpha = pulse;
      ctx.fillStyle = '#a855f7';
      ctx.beginPath();
      ctx.arc(e.x + e.w/2 - camera.x, e.y + e.h/2 - camera.y, e.w/2, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    }
  }
"""

    def _build_hazards_js(self) -> str:
        return """
  // ===== SparkLabs Hazard System =====
  function updateHazards() {
    for (var i = 0; i < entities.length; i++) {
      var e = entities[i];
      if (!e.alive || e.type !== 'hazard') continue;
      if (rectOverlap(player, e) && !isInvulnerable()) {
        if (activePowerups.shield > 0) {
          activePowerups.shield = 0;
          setInvulnerable(60);
          applyKnockback(player.x < e.x ? -4 : 4, -4, 12);
          if (typeof sfxDamage === 'function') sfxDamage();
        } else {
          loseLife();
          return;
        }
      }
    }
  }
  function renderHazards() {
    for (var i = 0; i < entities.length; i++) {
      var e = entities[i];
      if (!e.alive || e.type !== 'hazard') continue;
      var flicker = 0.7 + Math.sin(Date.now() / 80) * 0.3;
      ctx.globalAlpha = flicker;
      ctx.fillStyle = '#ef4444';
      // Spike pattern
      var spikes = Math.floor(e.w / 8);
      for (var s = 0; s < spikes; s++) {
        ctx.beginPath();
        ctx.moveTo(e.x - camera.x + s * 8, e.y - camera.y + e.h);
        ctx.lineTo(e.x - camera.x + s * 8 + 4, e.y - camera.y);
        ctx.lineTo(e.x - camera.x + s * 8 + 8, e.y - camera.y + e.h);
        ctx.closePath();
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }
  }
"""


# =============================================================================
# Entity Kit (spec helpers)
# =============================================================================


class EntityKit:
    """Factory for additional entity specifications.

    These specs are consumed by the ConceptCompiler to populate levels with
    the new entity types supported by the runtime extensions.
    """

    @staticmethod
    def powerup(entity_id: str, name: str, x: float, y: float, kind: str = "shield") -> Dict[str, Any]:
        return {
            "entity_id": entity_id, "name": name, "entity_type": "powerup",
            "x": x, "y": y, "width": 24, "height": 24, "color": "#fbbf24",
            "properties": {"powerupKind": kind},
        }

    @staticmethod
    def checkpoint(entity_id: str, name: str, x: float, y: float) -> Dict[str, Any]:
        return {
            "entity_id": entity_id, "name": name, "entity_type": "checkpoint",
            "x": x, "y": y, "width": 24, "height": 48, "color": "#555555",
            "properties": {"activated": False},
        }

    @staticmethod
    def bouncepad(entity_id: str, name: str, x: float, y: float, width: float = 48) -> Dict[str, Any]:
        return {
            "entity_id": entity_id, "name": name, "entity_type": "bouncepad",
            "x": x, "y": y, "width": width, "height": 12, "color": "#06b6d4",
            "properties": {},
        }

    @staticmethod
    def teleporter(entity_id: str, name: str, x: float, y: float, pair_id: str) -> Dict[str, Any]:
        return {
            "entity_id": entity_id, "name": name, "entity_type": "teleporter",
            "x": x, "y": y, "width": 32, "height": 32, "color": "#a855f7",
            "properties": {"pairId": pair_id},
        }

    @staticmethod
    def hazard(entity_id: str, name: str, x: float, y: float, width: float = 48, height: float = 16) -> Dict[str, Any]:
        return {
            "entity_id": entity_id, "name": name, "entity_type": "hazard",
            "x": x, "y": y, "width": width, "height": height, "color": "#ef4444",
            "properties": {},
        }

    @staticmethod
    def moving_platform(entity_id: str, name: str, x: float, y: float, width: float = 96,
                        move_axis: str = "x", move_range: float = 120) -> Dict[str, Any]:
        return {
            "entity_id": entity_id, "name": name, "entity_type": "structure",
            "x": x, "y": y, "width": width, "height": 16, "color": "#94a3b8",
            "properties": {
                "isMoving": True, "moveAxis": move_axis, "moveRange": move_range,
                "originX": x, "originY": y, "movePhase": 0,
            },
        }


def get_fx_injector(config: Optional[ExtensionConfig] = None) -> FxInjector:
    """Convenience accessor for an FxInjector instance."""
    return FxInjector(config)
