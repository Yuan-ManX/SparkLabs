import React, { useState, useRef, useCallback, useEffect } from 'react';

interface GameRunnerProps {
  gameHtml?: string;
  sceneNodes?: { id: string; name: string; type: string }[];
}

// Generate a complete HTML5 game document from scene nodes.
// The generated game supports three modes (platformer, top-down, puzzle)
// auto-detected from entity names, with physics, enemies, particles,
// Web Audio sound effects and mobile touch controls.
// Exported so the AI service can pre-generate game HTML from prompts.
export const generateGameHtml = (nodes: { id: string; name: string; type: string }[]): string => {
  // Embed scene nodes as JSON for the iframe script to consume
  const safeNodes = JSON.stringify(nodes || []);

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />
<title>Game Runner</title>
<style>
  html, body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: #0a0a0a;
    color: #ccc;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    user-select: none;
    -webkit-user-select: none;
    -webkit-tap-highlight-color: transparent;
    touch-action: none;
  }
  #gameCanvas {
    display: block;
    width: 100vw;
    height: 100vh;
  }
  /* Heads-up display: score, mode and lives */
  #hud {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    padding: 8px 12px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    pointer-events: none;
    z-index: 5;
    box-sizing: border-box;
  }
  .hud-block {
    background: rgba(10,10,10,0.72);
    border: 1px solid #1a1a1a;
    border-radius: 6px;
    padding: 4px 9px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.6px;
    color: #999;
  }
  .hud-block .label { color: #555; margin-right: 5px; font-weight: 600; }
  #scoreVal { color: #f97316; }
  #modeVal { color: #999; font-size: 10px; }
  .hearts { color: #ef4444; letter-spacing: 2px; }
  .heart-empty { color: #2a2a2a; }

  /* End-game overlay */
  #overlay {
    position: absolute;
    inset: 0;
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(0,0,0,0.86);
    z-index: 20;
    pointer-events: none;
    text-align: center;
  }
  #overlay.show { display: flex; }
  #overlay-title {
    font-size: 44px;
    font-weight: 800;
    letter-spacing: 4px;
    color: #f97316;
    text-shadow: 0 0 18px rgba(249,115,22,0.55);
    margin: 0 0 8px 0;
  }
  #overlay-sub {
    color: #999;
    font-size: 12px;
    letter-spacing: 1px;
  }
  #overlay.lose #overlay-title {
    color: #ef4444;
    text-shadow: 0 0 18px rgba(239,68,68,0.55);
  }

  /* Touch controls: directional pad and action button */
  #touchPad {
    position: absolute;
    bottom: 22px;
    left: 22px;
    width: 132px;
    height: 132px;
    display: none;
    z-index: 10;
  }
  #touchPad.show { display: block; }
  .pad-btn {
    position: absolute;
    width: 44px;
    height: 44px;
    background: rgba(30,30,30,0.7);
    border: 1px solid #2a2a2a;
    border-radius: 9px;
    color: #ccc;
    font-size: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }
  .pad-btn:active {
    background: rgba(249,115,22,0.32);
    border-color: #f97316;
    color: #f97316;
  }
  #padUp    { top: 0;    left: 44px; }
  #padDown  { bottom: 0; left: 44px; }
  #padLeft  { top: 44px; left: 0;    }
  #padRight { top: 44px; right: 0;  }

  #touchAction {
    position: absolute;
    bottom: 34px;
    right: 26px;
    width: 72px;
    height: 72px;
    background: rgba(249,115,22,0.22);
    border: 2px solid #f97316;
    border-radius: 50%;
    color: #f97316;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1px;
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 10;
    cursor: pointer;
  }
  #touchAction.show { display: flex; }
  #touchAction:active { background: rgba(249,115,22,0.5); }

  /* Small hint text below the HUD */
  #hint {
    position: absolute;
    top: 42px;
    left: 0;
    right: 0;
    text-align: center;
    color: #555;
    font-size: 10px;
    letter-spacing: 0.6px;
    pointer-events: none;
    z-index: 4;
  }
</style>
</head>
<body>
<canvas id="gameCanvas"></canvas>
<div id="hud">
  <div class="hud-block"><span class="label">SCORE</span><span id="scoreVal">0</span></div>
  <div class="hud-block" id="modeVal">MODE</div>
  <div class="hud-block"><span class="label">LIVES</span><span id="livesVal" class="hearts"></span></div>
</div>
<div id="hint">Move with WASD / Arrows</div>
<div id="touchPad">
  <div class="pad-btn" id="padUp">&#9650;</div>
  <div class="pad-btn" id="padDown">&#9660;</div>
  <div class="pad-btn" id="padLeft">&#9664;</div>
  <div class="pad-btn" id="padRight">&#9654;</div>
</div>
<div id="touchAction">JUMP</div>
<div id="overlay">
  <div id="overlay-title">YOU WIN</div>
  <div id="overlay-sub">All nodes collected</div>
</div>
<script>
(function () {
  'use strict';

  // Scene nodes injected from the host application
  var sceneNodes = ${safeNodes};

  // ===== DOM references =====
  var canvas = document.getElementById('gameCanvas');
  var ctx = canvas.getContext('2d');
  var scoreEl = document.getElementById('scoreVal');
  var livesEl = document.getElementById('livesVal');
  var modeEl = document.getElementById('modeVal');
  var hintEl = document.getElementById('hint');
  var overlayEl = document.getElementById('overlay');
  var overlayTitleEl = document.getElementById('overlay-title');
  var overlaySubEl = document.getElementById('overlay-sub');
  var touchPad = document.getElementById('touchPad');
  var touchAction = document.getElementById('touchAction');

  // ===== Viewport sizing with device pixel ratio for crisp rendering =====
  var viewW = 0, viewH = 0, dpr = 1;
  function resizeCanvas() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    viewW = window.innerWidth;
    viewH = window.innerHeight;
    canvas.width = Math.floor(viewW * dpr);
    canvas.height = Math.floor(viewH * dpr);
    canvas.style.width = viewW + 'px';
    canvas.style.height = viewH + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  // Guard against zero-size canvas during initial mount
  if (viewW < 10) viewW = 320;
  if (viewH < 10) viewH = 240;

  // ===== Color palette matching the editor theme =====
  var COLORS = {
    bg: '#0a0a0a',
    grid: '#111',
    accent: '#f97316',
    player: '#f97316',
    playerHi: '#fdba74',
    enemy: '#ef4444',
    enemyHi: '#fca5a5',
    platform: '#1f2937',
    platformEdge: '#374151',
    ground: '#0f0f0f',
    textBright: '#ccc',
    textMid: '#999',
    textDim: '#555'
  };
  var nodeColors = ['#3b82f6', '#10b981', '#a855f7', '#ec4899', '#eab308', '#06b6d4', '#ef4444', '#f97316'];

  // ===== Classify an entity by its name =====
  function classify(name) {
    var n = (name || '').toLowerCase();
    if (/(player|hero|character|protagonist|avatar)/.test(n)) return 'player';
    if (/(enemy|monster|boss|mob|foe|creature|skull|goblin)/.test(n)) return 'enemy';
    if (/(platform|ground|floor|terrain|world|structure|wall|brick|building)/.test(n)) return 'platform';
    if (/(puzzle|tile|switch|gem|crystal|rune)/.test(n)) return 'puzzle';
    return 'item';
  }

  // ===== Auto-detect game mode from scene node names =====
  function detectGameMode(list) {
    var counts = { player: 0, enemy: 0, platform: 0, puzzle: 0, item: 0 };
    for (var i = 0; i < list.length; i++) {
      var c = classify(list[i].name);
      if (counts[c] !== undefined) counts[c]++;
    }
    // Puzzle mode when puzzle-tagged nodes exist and no enemies
    if (counts.puzzle > 0 && counts.enemy === 0) return 'puzzle';
    // Platformer when there are terrain/platform nodes
    if (counts.platform >= 2) return 'platformer';
    if (counts.platform >= 1 && counts.enemy > 0) return 'platformer';
    // Fall back to top-down exploration
    return 'topdown';
  }

  var gameMode = detectGameMode(sceneNodes);
  modeEl.textContent = gameMode.toUpperCase();

  // ===== Web Audio API sound engine =====
  var audioCtx = null;
  function ensureAudio() {
    if (!audioCtx) {
      try {
        var AC = window.AudioContext || window.webkitAudioContext;
        if (AC) audioCtx = new AC();
      } catch (e) { audioCtx = null; }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
      try { audioCtx.resume(); } catch (e) {}
    }
  }
  function beep(freq, duration, type, vol) {
    if (!audioCtx) return;
    try {
      var t = audioCtx.currentTime;
      var osc = audioCtx.createOscillator();
      var gain = audioCtx.createGain();
      osc.type = type || 'square';
      osc.frequency.setValueAtTime(freq, t);
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.exponentialRampToValueAtTime(vol || 0.18, t + 0.005);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + (duration || 0.1));
      osc.connect(gain).connect(audioCtx.destination);
      osc.start(t);
      osc.stop(t + (duration || 0.1) + 0.03);
    } catch (e) {}
  }
  function sfxCollect() {
    beep(660, 0.07, 'square', 0.16);
    setTimeout(function () { beep(990, 0.09, 'square', 0.14); }, 55);
  }
  function sfxDamage() {
    beep(180, 0.16, 'sawtooth', 0.22);
    setTimeout(function () { beep(110, 0.2, 'sawtooth', 0.2); }, 80);
  }
  function sfxJump() { beep(420, 0.06, 'square', 0.1); }
  function sfxStep() { beep(220, 0.03, 'sine', 0.04); }
  function sfxWin() {
    var notes = [523, 659, 784, 1047];
    for (var i = 0; i < notes.length; i++) {
      (function (f, d) { setTimeout(function () { beep(f, 0.18, 'triangle', 0.2); }, d); })(notes[i], i * 110);
    }
  }
  function sfxLose() {
    var notes = [440, 330, 220, 110];
    for (var i = 0; i < notes.length; i++) {
      (function (f, d) { setTimeout(function () { beep(f, 0.22, 'sawtooth', 0.2); }, d); })(notes[i], i * 130);
    }
  }

  // ===== Game state =====
  var state = {
    score: 0,
    lives: 3,
    maxLives: 3,
    won: false,
    lost: false,
    invuln: 0
  };

  // ===== Input handling: keyboard + touch =====
  var keys = Object.create(null);
  var touchInput = { up: false, down: false, left: false, right: false, action: false };

  window.addEventListener('keydown', function (e) {
    var k = (e.key || '').toLowerCase();
    keys[k] = true;
    if (k === ' ' || k === 'arrowup' || k === 'arrowdown' || k === 'arrowleft' || k === 'arrowright') {
      e.preventDefault();
    }
    ensureAudio();
  });
  window.addEventListener('keyup', function (e) {
    var k = (e.key || '').toLowerCase();
    keys[k] = false;
  });

  function bindPad(id, prop) {
    var el = document.getElementById(id);
    if (!el) return;
    var setOn = function (e) { if (e && e.preventDefault) e.preventDefault(); touchInput[prop] = true; ensureAudio(); };
    var setOff = function (e) { if (e && e.preventDefault) e.preventDefault(); touchInput[prop] = false; };
    el.addEventListener('touchstart', setOn, { passive: false });
    el.addEventListener('touchend', setOff, { passive: false });
    el.addEventListener('touchcancel', setOff, { passive: false });
    el.addEventListener('mousedown', setOn);
    el.addEventListener('mouseup', setOff);
    el.addEventListener('mouseleave', setOff);
  }
  bindPad('padUp', 'up');
  bindPad('padDown', 'down');
  bindPad('padLeft', 'left');
  bindPad('padRight', 'right');
  bindPad('touchAction', 'action');

  function isTouchDevice() {
    return (('ontouchstart' in window) || (navigator.maxTouchPoints || 0) > 0);
  }
  if (isTouchDevice()) {
    touchPad.classList.add('show');
    if (gameMode === 'platformer') touchAction.classList.add('show');
  }

  function inputUp()     { return !!(keys['w'] || keys['arrowup']    || touchInput.up); }
  function inputDown()   { return !!(keys['s'] || keys['arrowdown']  || touchInput.down); }
  function inputLeft()   { return !!(keys['a'] || keys['arrowleft']  || touchInput.left); }
  function inputRight()  { return !!(keys['d'] || keys['arrowright'] || touchInput.right); }
  function inputAction() { return !!(keys[' '] || touchInput.action); }

  // ===== Particle system =====
  var particles = [];
  function spawnParticles(x, y, color, count) {
    var n = count || 12;
    for (var i = 0; i < n; i++) {
      var angle = (Math.PI * 2 * i / n) + Math.random() * 0.5;
      var speed = 1.4 + Math.random() * 2.6;
      particles.push({
        x: x, y: y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 1.0,
        life: 1.0,
        decay: 0.018 + Math.random() * 0.018,
        size: 2 + Math.random() * 3,
        color: color
      });
    }
  }
  function updateParticles() {
    for (var i = particles.length - 1; i >= 0; i--) {
      var p = particles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.14;
      p.vx *= 0.97;
      p.life -= p.decay;
      if (p.life <= 0) particles.splice(i, 1);
    }
  }
  function drawParticles() {
    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      ctx.globalAlpha = Math.max(0, p.life);
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  // ===== World containers =====
  var world = { platforms: [], items: [], enemies: [], playerSpawn: null };

  function makeItem(id, name, x, y, idx) {
    return {
      id: id, name: name,
      x: x, y: y, w: 24, h: 24,
      color: nodeColors[idx % nodeColors.length],
      collected: false,
      bob: Math.random() * Math.PI * 2
    };
  }

  function buildWorld() {
    world.platforms.length = 0;
    world.items.length = 0;
    world.enemies.length = 0;
    world.playerSpawn = null;

    var groundH = 40;
    if (gameMode === 'platformer') {
      world.platforms.push({ x: 0, y: viewH - groundH, w: viewW, h: groundH, kind: 'ground' });
    }

    var n = sceneNodes.length;
    if (n === 0) {
      // No scene data — spawn a small set of collectibles so the game is playable
      var count = 5;
      for (var i = 0; i < count; i++) {
        var ix = (i + 1) * (viewW / (count + 1));
        var iy;
        if (gameMode === 'platformer') {
          iy = viewH - groundH - 110 - (i % 2) * 80;
          world.platforms.push({ x: ix - 35, y: iy + 28, w: 70, h: 14, kind: 'platform' });
        } else {
          iy = 80 + (i * 71) % Math.max(60, viewH - 160);
        }
        world.items.push(makeItem('node_' + i, 'Node ' + (i + 1), ix - 12, iy, i));
      }
    } else {
      var usableW = Math.max(120, viewW - 160);
      var stepX = usableW / n;
      var layoutX = 80;
      for (var i = 0; i < n; i++) {
        var node = sceneNodes[i];
        var kind = classify(node.name);
        var x = layoutX + stepX * i + stepX / 2;

        if (kind === 'player') {
          world.playerSpawn = gameMode === 'platformer'
            ? { x: x - 13, y: viewH - groundH - 50 }
            : { x: x - 13, y: viewH / 2 - 16 };
          continue;
        }
        if (kind === 'platform') {
          if (gameMode === 'platformer') {
            var pw = 100;
            var ph = 16;
            var py = viewH - groundH - 90 - ((i * 67) % Math.max(80, viewH * 0.4));
            world.platforms.push({ x: x - pw / 2, y: py, w: pw, h: ph, kind: 'platform' });
          } else {
            // Top-down: treat as a solid obstacle block
            var bs = 48;
            var by = 80 + ((i * 53) % Math.max(60, viewH - 200));
            world.platforms.push({ x: x - bs / 2, y: by, w: bs, h: bs, kind: 'block' });
          }
          continue;
        }
        if (kind === 'enemy') {
          var ey;
          if (gameMode === 'platformer') {
            ey = viewH - groundH - 30;
          } else {
            ey = 80 + ((i * 91) % Math.max(80, viewH - 160));
          }
          world.enemies.push({
            x: x - 14, y: ey, w: 28, h: 28,
            baseX: x - 14, baseY: ey,
            patrolRange: 60 + ((i * 23) % 80),
            dir: 1,
            speed: 0.9 + ((i * 0.17) % 1.0),
            color: COLORS.enemy,
            alive: true,
            wobble: Math.random() * Math.PI * 2
          });
          continue;
        }
        // Default: collectible item
        var iy2;
        if (gameMode === 'platformer') {
          iy2 = viewH - groundH - 110 - ((i * 53) % Math.max(60, viewH * 0.35));
          // Provide a small platform under floating items so they are reachable
          world.platforms.push({ x: x - 35, y: iy2 + 28, w: 70, h: 14, kind: 'platform' });
        } else {
          iy2 = 70 + ((i * 71) % Math.max(60, viewH - 140));
        }
        world.items.push(makeItem(node.id, node.name, x - 12, iy2, i));
      }
    }

    if (!world.playerSpawn) {
      world.playerSpawn = gameMode === 'platformer'
        ? { x: 60, y: viewH - groundH - 50 }
        : { x: 60, y: viewH / 2 - 16 };
    }
  }

  // ===== Player entity and physics constants =====
  var player = {
    x: 0, y: 0, w: 26, h: 32,
    vx: 0, vy: 0,
    speed: 3.4,
    onGround: false,
    facing: 1
  };
  var GRAVITY = 0.55;
  var JUMP_VELOCITY = -11.5;
  var MAX_FALL = 14;

  function resetPlayer() {
    if (world.playerSpawn) {
      player.x = world.playerSpawn.x;
      player.y = world.playerSpawn.y;
    } else {
      player.x = 40;
      player.y = viewH - 100;
    }
    player.vx = 0;
    player.vy = 0;
    player.onGround = false;
  }

  // ===== Puzzle mode: grid-based layout =====
  var puzzle = { cell: 50, cols: 0, rows: 0, offsetX: 0, offsetY: 0 };

  function buildPuzzle() {
    puzzle.cell = 50;
    puzzle.cols = Math.max(8, Math.floor(viewW / 50) - 2);
    puzzle.rows = Math.max(6, Math.floor(viewH / 50) - 3);
    puzzle.offsetX = (viewW - puzzle.cols * puzzle.cell) / 2;
    puzzle.offsetY = (viewH - puzzle.rows * puzzle.cell) / 2 + 6;

    var pCol = 1, pRow = 1;
    player.w = puzzle.cell - 10;
    player.h = puzzle.cell - 10;
    player.x = puzzle.offsetX + pCol * puzzle.cell + 5;
    player.y = puzzle.offsetY + pRow * puzzle.cell + 5;
    player.gridCol = pCol;
    player.gridRow = pRow;
    player.moveTimer = 0;
    player.facing = 1;

    world.items.length = 0;
    var n = sceneNodes.length || 6;
    var placed = {};
    for (var i = 0; i < n; i++) {
      var col, row, tries = 0, key;
      do {
        col = 1 + Math.floor(Math.random() * (puzzle.cols - 2));
        row = 1 + Math.floor(Math.random() * (puzzle.rows - 2));
        key = col + ',' + row;
        tries++;
      } while ((placed[key] || (col === pCol && row === pRow)) && tries < 30);
      placed[key] = true;
      var node = sceneNodes[i] || { id: 'node_' + i, name: 'Node ' + (i + 1) };
      world.items.push({
        id: node.id, name: node.name,
        col: col, row: row,
        x: puzzle.offsetX + col * puzzle.cell + 8,
        y: puzzle.offsetY + row * puzzle.cell + 8,
        w: puzzle.cell - 16, h: puzzle.cell - 16,
        color: nodeColors[i % nodeColors.length],
        collected: false,
        bob: Math.random() * Math.PI * 2
      });
    }
  }

  // ===== Collision helpers =====
  function rectsOverlap(a, b) {
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }

  // Solid-body resolution against platforms (axis-separated)
  function moveAndCollide(ent, platforms) {
    ent.x += ent.vx;
    for (var i = 0; i < platforms.length; i++) {
      var p = platforms[i];
      if (rectsOverlap(ent, p)) {
        if (ent.vx > 0) ent.x = p.x - ent.w;
        else if (ent.vx < 0) ent.x = p.x + p.w;
        ent.vx = 0;
      }
    }
    ent.onGround = false;
    ent.y += ent.vy;
    for (var j = 0; j < platforms.length; j++) {
      var q = platforms[j];
      if (rectsOverlap(ent, q)) {
        if (ent.vy > 0) { ent.y = q.y - ent.h; ent.onGround = true; }
        else if (ent.vy < 0) { ent.y = q.y + q.h; }
        ent.vy = 0;
      }
    }
  }

  // ===== Update: platformer mode =====
  function updatePlatformer() {
    if (state.won || state.lost) return;

    var ax = 0;
    if (inputLeft()) ax -= 1;
    if (inputRight()) ax += 1;
    player.vx = ax * player.speed;
    if (ax !== 0) player.facing = ax;

    // Jump when on ground
    if ((inputAction() || inputUp()) && player.onGround) {
      player.vy = JUMP_VELOCITY;
      player.onGround = false;
      sfxJump();
    }

    player.vy += GRAVITY;
    if (player.vy > MAX_FALL) player.vy = MAX_FALL;

    moveAndCollide(player, world.platforms);

    // Clamp to view bounds horizontally
    if (player.x < 0) player.x = 0;
    if (player.x + player.w > viewW) player.x = viewW - player.w;

    // Fell out of the world
    if (player.y > viewH + 80) {
      damagePlayer(true);
    }

    updateEnemies();
    checkItemPickup();
    checkEnemyContact();
    if (state.invuln > 0) state.invuln--;
  }

  // ===== Update: top-down mode =====
  function updateTopDown() {
    if (state.won || state.lost) return;

    var dx = 0, dy = 0;
    if (inputUp()) dy -= 1;
    if (inputDown()) dy += 1;
    if (inputLeft()) dx -= 1;
    if (inputRight()) dx += 1;
    if (dx !== 0 && dy !== 0) { dx *= 0.7071; dy *= 0.7071; }
    player.vx = dx * player.speed;
    player.vy = dy * player.speed;
    if (dx !== 0) player.facing = dx;

    moveAndCollide(player, world.platforms);

    if (player.x < 0) player.x = 0;
    if (player.x + player.w > viewW) player.x = viewW - player.w;
    if (player.y < 0) player.y = 0;
    if (player.y + player.h > viewH) player.y = viewH - player.h;

    updateEnemies();
    checkItemPickup();
    checkEnemyContact();
    if (state.invuln > 0) state.invuln--;
  }

  // ===== Update: puzzle mode (grid-stepped movement) =====
  function updatePuzzle() {
    if (state.won || state.lost) return;
    if (player.moveTimer > 0) { player.moveTimer--; return; }

    var tCol = player.gridCol, tRow = player.gridRow;
    if (inputLeft()) { tCol--; player.facing = -1; }
    else if (inputRight()) { tCol++; player.facing = 1; }
    else if (inputUp()) tRow--;
    else if (inputDown()) tRow++;

    if (tCol !== player.gridCol || tRow !== player.gridRow) {
      if (tCol >= 0 && tCol < puzzle.cols && tRow >= 0 && tRow < puzzle.rows) {
        player.gridCol = tCol;
        player.gridRow = tRow;
        player.x = puzzle.offsetX + tCol * puzzle.cell + 5;
        player.y = puzzle.offsetY + tRow * puzzle.cell + 5;
        player.moveTimer = 5;
        sfxStep();
        ensureAudio();
      }
    }
    checkItemPickup();
  }

  // ===== Enemy patrol AI =====
  function updateEnemies() {
    for (var i = 0; i < world.enemies.length; i++) {
      var e = world.enemies[i];
      if (!e.alive) continue;
      e.wobble += 0.08;
      e.x += e.dir * e.speed;
      if (e.x > e.baseX + e.patrolRange) { e.x = e.baseX + e.patrolRange; e.dir = -1; }
      else if (e.x < e.baseX - e.patrolRange) { e.x = e.baseX - e.patrolRange; e.dir = 1; }
      if (e.x < 4) { e.x = 4; e.dir = 1; }
      if (e.x + e.w > viewW - 4) { e.x = viewW - e.w - 4; e.dir = -1; }
    }
  }

  function checkItemPickup() {
    for (var i = 0; i < world.items.length; i++) {
      var it = world.items[i];
      if (it.collected) continue;
      if (rectsOverlap(player, it)) {
        it.collected = true;
        state.score += 10;
        scoreEl.textContent = state.score;
        spawnParticles(it.x + it.w / 2, it.y + it.h / 2, it.color, 14);
        sfxCollect();
        if (countRemainingItems() === 0) winGame();
      }
    }
  }

  function checkEnemyContact() {
    if (state.invuln > 0) return;
    for (var i = 0; i < world.enemies.length; i++) {
      var e = world.enemies[i];
      if (!e.alive) continue;
      if (rectsOverlap(player, e)) {
        damagePlayer(false);
        break;
      }
    }
  }

  function countRemainingItems() {
    var c = 0;
    for (var i = 0; i < world.items.length; i++) if (!world.items[i].collected) c++;
    return c;
  }

  function damagePlayer(fellOff) {
    state.lives--;
    state.invuln = 90;
    sfxDamage();
    spawnParticles(player.x + player.w / 2, player.y + player.h / 2, COLORS.enemy, 16);
    updateLivesHud();
    if (state.lives <= 0) {
      loseGame();
    } else if (fellOff || gameMode === 'platformer') {
      resetPlayer();
    } else if (world.playerSpawn) {
      player.x = world.playerSpawn.x;
      player.y = world.playerSpawn.y;
      player.vx = 0; player.vy = 0;
    }
  }

  function updateLivesHud() {
    var s = '';
    for (var i = 0; i < state.maxLives; i++) {
      if (i < state.lives) s += '\\u2665';
      else s += '<span class="heart-empty">\\u2665</span>';
    }
    livesEl.innerHTML = s;
  }

  function winGame() {
    state.won = true;
    overlayEl.classList.remove('lose');
    overlayEl.classList.add('show');
    overlayTitleEl.textContent = 'YOU WIN';
    overlaySubEl.textContent = 'Score: ' + state.score + '  /  All nodes collected';
    sfxWin();
    spawnParticles(player.x + player.w / 2, player.y + player.h / 2, COLORS.accent, 32);
  }

  function loseGame() {
    state.lost = true;
    overlayEl.classList.add('lose', 'show');
    overlayTitleEl.textContent = 'GAME OVER';
    overlaySubEl.textContent = 'Score: ' + state.score + '  /  Press Restart to try again';
    sfxLose();
  }

  // ===== Rendering =====
  function drawBackground() {
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, viewW, viewH);
    // Faint grid for spatial reference
    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth = 1;
    ctx.beginPath();
    var g = 40;
    for (var x = 0; x <= viewW; x += g) { ctx.moveTo(x + 0.5, 0); ctx.lineTo(x + 0.5, viewH); }
    for (var y = 0; y <= viewH; y += g) { ctx.moveTo(0, y + 0.5); ctx.lineTo(viewW, y + 0.5); }
    ctx.stroke();
  }

  function drawPlatforms() {
    for (var i = 0; i < world.platforms.length; i++) {
      var p = world.platforms[i];
      ctx.fillStyle = p.kind === 'ground' ? COLORS.ground : COLORS.platform;
      ctx.fillRect(p.x, p.y, p.w, p.h);
      // Top edge highlight to read as a solid surface
      ctx.fillStyle = COLORS.platformEdge;
      ctx.fillRect(p.x, p.y, p.w, 2);
      ctx.strokeStyle = 'rgba(255,255,255,0.05)';
      ctx.lineWidth = 1;
      ctx.strokeRect(p.x + 0.5, p.y + 0.5, p.w - 1, p.h - 1);
    }
  }

  function drawItems() {
    for (var i = 0; i < world.items.length; i++) {
      var it = world.items[i];
      if (it.collected) continue;
      it.bob += 0.06;
      var bobY = Math.sin(it.bob) * 3;
      // Glow halo
      ctx.shadowColor = it.color;
      ctx.shadowBlur = 14;
      ctx.fillStyle = it.color;
      ctx.fillRect(it.x, it.y + bobY, it.w, it.h);
      ctx.shadowBlur = 0;
      // Top highlight strip
      ctx.fillStyle = 'rgba(255,255,255,0.35)';
      ctx.fillRect(it.x + 3, it.y + 3 + bobY, it.w - 6, 3);
      // Label
      ctx.fillStyle = '#fff';
      ctx.font = '8px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      var label = it.name || 'item';
      if (label.length > 8) label = label.substring(0, 7);
      ctx.fillText(label, it.x + it.w / 2, it.y + it.h / 2 + bobY);
    }
  }

  function drawEnemies() {
    for (var i = 0; i < world.enemies.length; i++) {
      var e = world.enemies[i];
      if (!e.alive) continue;
      var yOff = Math.sin(e.wobble) * 1.5;
      ctx.shadowColor = e.color;
      ctx.shadowBlur = 10;
      ctx.fillStyle = e.color;
      ctx.fillRect(e.x, e.y + yOff, e.w, e.h);
      ctx.shadowBlur = 0;
      // Eyes follow patrol direction
      var eyeShift = e.dir > 0 ? 2 : -2;
      ctx.fillStyle = '#fff';
      ctx.fillRect(e.x + e.w / 2 - 8 + eyeShift, e.y + 7 + yOff, 4, 5);
      ctx.fillRect(e.x + e.w / 2 + 4 + eyeShift, e.y + 7 + yOff, 4, 5);
      ctx.fillStyle = '#000';
      ctx.fillRect(e.x + e.w / 2 - 7 + eyeShift, e.y + 9 + yOff, 2, 2);
      ctx.fillRect(e.x + e.w / 2 + 5 + eyeShift, e.y + 9 + yOff, 2, 2);
      // Highlight
      ctx.fillStyle = COLORS.enemyHi;
      ctx.fillRect(e.x + 3, e.y + 3 + yOff, e.w - 6, 3);
    }
  }

  function drawPlayer() {
    // Flicker during invulnerability
    if (state.invuln > 0 && Math.floor(state.invuln / 4) % 2 === 0) return;
    var px = player.x, py = player.y, pw = player.w, ph = player.h;
    ctx.shadowColor = COLORS.player;
    ctx.shadowBlur = 16;
    ctx.fillStyle = COLORS.player;
    ctx.fillRect(px, py, pw, ph);
    ctx.shadowBlur = 0;
    // Top highlight
    ctx.fillStyle = COLORS.playerHi;
    ctx.fillRect(px + 3, py + 3, pw - 6, 4);
    // Directional eye
    ctx.fillStyle = '#fff';
    var eyeX = player.facing > 0 ? px + pw - 9 : px + 3;
    ctx.fillRect(eyeX, py + 9, 6, 6);
    ctx.fillStyle = '#000';
    ctx.fillRect(eyeX + 1, py + 10, 3, 4);
  }

  function drawPuzzle() {
    // Grid frame
    ctx.strokeStyle = '#1a1a1a';
    ctx.lineWidth = 2;
    ctx.strokeRect(puzzle.offsetX, puzzle.offsetY, puzzle.cols * puzzle.cell, puzzle.rows * puzzle.cell);
    // Inner grid lines
    ctx.strokeStyle = '#111';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (var c = 1; c < puzzle.cols; c++) {
      ctx.moveTo(puzzle.offsetX + c * puzzle.cell + 0.5, puzzle.offsetY);
      ctx.lineTo(puzzle.offsetX + c * puzzle.cell + 0.5, puzzle.offsetY + puzzle.rows * puzzle.cell);
    }
    for (var r = 1; r < puzzle.rows; r++) {
      ctx.moveTo(puzzle.offsetX, puzzle.offsetY + r * puzzle.cell + 0.5);
      ctx.lineTo(puzzle.offsetX + puzzle.cols * puzzle.cell, puzzle.offsetY + r * puzzle.cell + 0.5);
    }
    ctx.stroke();
    drawItems();
    drawPlayer();
  }

  // ===== Main loop =====
  function update() {
    if (gameMode === 'platformer') updatePlatformer();
    else if (gameMode === 'puzzle') updatePuzzle();
    else updateTopDown();
    updateParticles();
  }

  function draw() {
    drawBackground();
    if (gameMode === 'puzzle') {
      drawPuzzle();
    } else {
      drawPlatforms();
      drawItems();
      drawEnemies();
      drawPlayer();
    }
    drawParticles();
  }

  function loop() {
    update();
    draw();
    requestAnimationFrame(loop);
  }

  // ===== Initialize =====
  function init() {
    if (gameMode === 'puzzle') {
      buildPuzzle();
      hintEl.textContent = 'Move cell-by-cell with WASD / Arrows';
    } else if (gameMode === 'platformer') {
      buildWorld();
      resetPlayer();
      hintEl.textContent = 'Move with A/D, Jump with Space / W / Up';
    } else {
      buildWorld();
      resetPlayer();
      hintEl.textContent = 'Move with WASD / Arrows';
    }
    updateLivesHud();
    scoreEl.textContent = state.score;
    requestAnimationFrame(loop);
  }

  // Rebuild layout on viewport resize (debounced)
  var resizeTimer = null;
  window.addEventListener('resize', function () {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      if (viewW < 10) viewW = 320;
      if (viewH < 10) viewH = 240;
      if (gameMode === 'puzzle') buildPuzzle();
      else { buildWorld(); resetPlayer(); }
    }, 220);
  });

  // Unlock audio on first user interaction inside the iframe
  window.addEventListener('pointerdown', ensureAudio, { once: true });
  window.addEventListener('keydown', ensureAudio, { once: true });

  init();
})();
</script>
</body>
</html>`;
};

const GameRunner: React.FC<GameRunnerProps> = ({ gameHtml, sceneNodes = [] }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [currentHtml, setCurrentHtml] = useState('');
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const startGame = useCallback(() => {
    const html = gameHtml || generateGameHtml(sceneNodes);
    setCurrentHtml(html);
    setIsRunning(true);
  }, [gameHtml, sceneNodes]);

  // Auto-start when a pre-generated game HTML arrives from the AI pipeline
  useEffect(() => {
    if (gameHtml) {
      setCurrentHtml(gameHtml);
      setIsRunning(true);
    }
  }, [gameHtml]);

  const stopGame = useCallback(() => {
    setIsRunning(false);
    setCurrentHtml('');
  }, []);

  const restartGame = useCallback(() => {
    stopGame();
    setTimeout(startGame, 100);
  }, [startGame, stopGame]);

  return (
    <div className="sl-panel h-full">
      <div className="sl-panel-header">
        <i className="fa-solid fa-gamepad text-[10px] text-orange-500" />
        <span className="sl-panel-header-title">Game Runner</span>
        <div className="sl-panel-header-actions">
          {!isRunning ? (
            <button className="sl-panel-header-btn" onClick={startGame} title="Run Game">
              <i className="fa-solid fa-play" />
            </button>
          ) : (
            <>
              <button className="sl-panel-header-btn" onClick={restartGame} title="Restart">
                <i className="fa-solid fa-rotate-right" />
              </button>
              <button className="sl-panel-header-btn" onClick={stopGame} title="Stop">
                <i className="fa-solid fa-stop" />
              </button>
            </>
          )}
        </div>
      </div>
      <div className="flex-1 relative bg-[#0a0a0a]">
        {isRunning && currentHtml ? (
          <iframe
            ref={iframeRef}
            srcDoc={currentHtml}
            sandbox="allow-scripts"
            className="w-full h-full border-0"
            title="Game Runner"
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <i className="fa-solid fa-gamepad text-3xl text-[#222] mb-3 block" />
              <div className="text-[12px] text-[#555] mb-2">Game Runner Ready</div>
              <div className="text-[10px] text-[#333] mb-4">Click Play to run the generated game</div>
              <button onClick={startGame} className="flex items-center gap-1.5 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-[11px] font-semibold text-white transition-all">
                <i className="fa-solid fa-play text-[9px]" /> Run Game
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GameRunner;
