"""
SparkLabs Engine - Game Feature Injector

Injects tilemap rendering, save/load, achievements, screen shake, smooth camera,
and minimap into the generated HTML5 game runtime. Each feature is independently
toggleable and integrates with the existing HtmlAssembler output.

The injector produces JavaScript snippets that are inserted into the game template:
  - build_header_js(): Feature system definitions
  - build_loop_patch_js(): Update/render hooks called each frame
  - build_init_call_js(): Initialization calls for game start
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FeatureConfig:
    """Configuration for feature injection."""
    enable_tilemap: bool = True
    enable_save_system: bool = True
    enable_achievements: bool = True
    enable_screen_shake: bool = True
    enable_smooth_camera: bool = True
    enable_minimap: bool = True
    tile_size: int = 32
    minimap_size: int = 120
    shake_decay: float = 0.85
    camera_lerp: float = 0.12


class FeatureInjector:
    """
    Produces JavaScript code snippets that add tilemap rendering, save/load,
    achievements, screen shake, smooth camera, and minimap to the generated game.

    The generated JS integrates with the existing runtime variables (player,
    entities, camera, LEVELS, CONFIG, etc.) without redeclaring them.
    """

    def __init__(self, config: Optional[FeatureConfig] = None) -> None:
        self.config = config or FeatureConfig()

    def build_header_js(self) -> str:
        """Generate JavaScript for all feature system definitions."""
        parts: List[str] = []

        if self.config.enable_save_system:
            parts.append(self._save_system_js())

        if self.config.enable_achievements:
            parts.append(self._achievements_js())

        if self.config.enable_screen_shake:
            parts.append(self._screen_shake_js())

        if self.config.enable_smooth_camera:
            parts.append(self._smooth_camera_js())

        if self.config.enable_tilemap:
            parts.append(self._tilemap_js())

        if self.config.enable_minimap:
            parts.append(self._minimap_js())

        return "\n".join(parts)

    def build_loop_patch_js(self) -> str:
        """Generate JavaScript for update/render hooks called each frame."""
        return self._loop_functions_js()

    def build_init_call_js(self) -> str:
        """Generate JavaScript to call during game initialization."""
        parts: List[str] = []
        if self.config.enable_save_system:
            parts.append("loadSavedProgress();")
        if self.config.enable_achievements:
            parts.append("initAchievements();")
        if self.config.enable_tilemap:
            parts.append("generateTilemapForLevel(levelIdx);")
        return "\n".join(parts)

    # =========================================================================
    # Save / Load System
    # =========================================================================

    def _save_system_js(self) -> str:
        return """
  // ---- Save / Load System ----
  var SAVE_KEY = 'sparklabs_save_' + (CONFIG.title || 'game').replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
  var saveNotificationTimer = 0;

  function saveProgress() {{
    try {{
      var data = {{
        level: levelIdx,
        score: score,
        lives: lives,
        achievements: typeof ACHIEVEMENTS !== 'undefined' ? ACHIEVEMENTS : {{}}
      }};
      localStorage.setItem(SAVE_KEY, JSON.stringify(data));
      saveNotificationTimer = 180;
    }} catch(e) {{ /* localStorage may be unavailable */ }}
  }}

  function loadSavedProgress() {{
    try {{
      var raw = localStorage.getItem(SAVE_KEY);
      if (!raw) return;
      var data = JSON.parse(raw);
      if (data.score) score = data.score;
      if (data.lives) lives = data.lives;
      if (data.achievements && typeof ACHIEVEMENTS !== 'undefined') {{
        var keys = Object.keys(data.achievements);
        for (var i = 0; i < keys.length; i++) {{
          if (ACHIEVEMENTS[keys[i]]) {{
            ACHIEVEMENTS[keys[i]].unlocked = true;
          }}
        }}
      }}
    }} catch(e) {{ /* parse error */ }}
  }}"""

    # =========================================================================
    # Achievement System
    # =========================================================================

    def _achievements_js(self) -> str:
        return """
  // ---- Achievement System ----
  var ACHIEVEMENTS = {{
    first_steps:     {{ name: 'First Steps',      desc: 'Complete level 1',           unlocked: false, icon: 'flag' }},
    collector:       {{ name: 'Collector',        desc: 'Gather 50 collectibles',     unlocked: false, icon: 'gem' }},
    survivor:        {{ name: 'Survivor',         desc: 'Clear a level without dying', unlocked: false, icon: 'shield' }},
    speed_runner:    {{ name: 'Speed Runner',     desc: 'Complete a level under 30s',  unlocked: false, icon: 'bolt' }},
    explorer:        {{ name: 'Explorer',         desc: 'Visit all levels',           unlocked: false, icon: 'compass' }},
    champion:        {{ name: 'Champion',         desc: 'Complete all levels',        unlocked: false, icon: 'trophy' }},
    sharpshooter:    {{ name: 'Sharpshooter',     desc: 'Defeat 10 enemies',          unlocked: false, icon: 'crosshairs' }},
    untouchable:     {{ name: 'Untouchable',      desc: 'Finish without losing a life', unlocked: false, icon: 'star' }}
  }};
  var achievementBannerTimer = 0;
  var achievementBannerText = '';
  var levelStartTime = 0;
  var totalCollectiblesGathered = 0;
  var totalEnemiesDefeated = 0;
  var deathlessLevel = true;
  var deathlessRun = true;

  function initAchievements() {{
    levelStartTime = Date.now();
  }}

  function unlockAchievement(key) {{
    if (ACHIEVEMENTS[key] && !ACHIEVEMENTS[key].unlocked) {{
      ACHIEVEMENTS[key].unlocked = true;
      achievementBannerText = ACHIEVEMENTS[key].name;
      achievementBannerTimer = 240;
      if (typeof saveProgress === 'function') saveProgress();
    }}
  }}

  function checkAchievements() {{
    if (levelIdx >= 1 && !ACHIEVEMENTS.first_steps.unlocked) {{
      unlockAchievement('first_steps');
    }}
    if (totalCollectiblesGathered >= 50 && !ACHIEVEMENTS.collector.unlocked) {{
      unlockAchievement('collector');
    }}
    if (totalEnemiesDefeated >= 10 && !ACHIEVEMENTS.sharpshooter.unlocked) {{
      unlockAchievement('sharpshooter');
    }}
    if (LEVELS && levelIdx >= LEVELS.length - 1 && !ACHIEVEMENTS.explorer.unlocked) {{
      unlockAchievement('explorer');
    }}
  }}"""

    # =========================================================================
    # Screen Shake
    # =========================================================================

    def _screen_shake_js(self) -> str:
        return f"""
  // ---- Screen Shake ----
  var shakeIntensity = 0;
  var shakeX = 0, shakeY = 0;

  function triggerShake(intensity) {{
    shakeIntensity = Math.max(shakeIntensity, intensity);
  }}

  function updateShake() {{
    if (shakeIntensity > 0.1) {{
      shakeX = (Math.random() - 0.5) * shakeIntensity * 2;
      shakeY = (Math.random() - 0.5) * shakeIntensity * 2;
      shakeIntensity *= {self.config.shake_decay};
    }} else {{
      shakeIntensity = 0;
      shakeX = 0;
      shakeY = 0;
    }}
  }}"""

    # =========================================================================
    # Smooth Camera
    # =========================================================================

    def _smooth_camera_js(self) -> str:
        return f"""
  // ---- Smooth Camera Follow ----
  var cameraTargetX = 0, cameraTargetY = 0;
  var CAMERA_DEADZONE = 80;

  function updateSmoothCamera() {{
    if (!player) return;
    var targetX = player.x - W / 2 + player.w / 2;
    var targetY = player.y - H / 2 + player.h / 2;

    // Deadzone: only move camera if player is far enough from center
    var dx = targetX - cameraTargetX;
    var dy = targetY - cameraTargetY;
    if (Math.abs(dx) > CAMERA_DEADZONE) {{
      cameraTargetX += (dx > 0 ? dx - CAMERA_DEADZONE : dx + CAMERA_DEADZONE);
    }}
    if (Math.abs(dy) > CAMERA_DEADZONE) {{
      cameraTargetY += (dy > 0 ? dy - CAMERA_DEADZONE : dy + CAMERA_DEADZONE);
    }}

    // Lerp camera toward target
    camera.x += (cameraTargetX - camera.x) * {self.config.camera_lerp};
    camera.y += (cameraTargetY - camera.y) * {self.config.camera_lerp};

    // Apply screen shake offset
    camera.x += shakeX;
    camera.y += shakeY;
  }}"""

    # =========================================================================
    # Tilemap System
    # =========================================================================

    def _tilemap_js(self) -> str:
        return f"""
  // ---- Tilemap System ----
  var TILE_SIZE = {self.config.tile_size};
  var TILE_MAP = [];
  var TILE_COLORS = {{
    empty: 'transparent',
    ground: CONFIG.terrainColor || '#3a3a4a',
    platform: CONFIG.structureColor || '#5a5a7a',
    wall: '#2a2a3a',
    hazard: '#ff4444'
  }};

  function generateTilemapForLevel(idx) {{
    TILE_MAP = [];
    if (!LEVELS || idx >= LEVELS.length) return;
    var level = LEVELS[idx];
    if (!level) return;

    // Determine level bounds from entities
    var minX = 0, maxX = W * 2, minY = 0, maxY = H * 2;
    if (level.entities) {{
      for (var i = 0; i < level.entities.length; i++) {{
        var e = level.entities[i];
        if (e.x !== undefined) {{
          minX = Math.min(minX, e.x);
          maxX = Math.max(maxX, e.x + (e.w || TILE_SIZE));
          maxY = Math.max(maxY, e.y + (e.h || TILE_SIZE));
        }}
      }}
    }}

    var cols = Math.ceil((maxX - minX) / TILE_SIZE);
    var rows = Math.ceil((maxY - minY) / TILE_SIZE);
    cols = Math.min(cols, 80);
    rows = Math.min(rows, 60);

    for (var r = 0; r < rows; r++) {{
      var row = [];
      for (var c = 0; c < cols; c++) {{
        var tileType = 'empty';
        // Ground tiles along the bottom
        if (r >= rows - 2) tileType = 'ground';
        // Random platform tiles
        if (r < rows - 3 && r > rows * 0.3 && Math.random() < 0.08) {{
          tileType = 'platform';
        }}
        // Wall tiles on edges
        if (c === 0 || c === cols - 1) tileType = 'wall';
        row.push(tileType);
      }}
      TILE_MAP.push(row);
    }}

    // Solidify tiles under existing platform entities
    if (level.entities) {{
      for (var i = 0; i < level.entities.length; i++) {{
        var e = level.entities[i];
        if (e.type === 'structure' || e.type === 'terrain') {{
          var startCol = Math.floor(e.x / TILE_SIZE);
          var endCol = Math.ceil((e.x + (e.w || TILE_SIZE)) / TILE_SIZE);
          var startRow = Math.floor(e.y / TILE_SIZE);
          var endRow = Math.ceil((e.y + (e.h || TILE_SIZE)) / TILE_SIZE);
          for (var r = startRow; r <= endRow && r < TILE_MAP.length; r++) {{
            for (var c = startCol; c <= endCol && c < TILE_MAP[r].length; c++) {{
              if (r >= 0 && c >= 0) TILE_MAP[r][c] = 'platform';
            }}
          }}
        }}
      }}
    }}
  }}

  function renderTilemap() {{
    if (!TILE_MAP || TILE_MAP.length === 0) return;
    for (var r = 0; r < TILE_MAP.length; r++) {{
      for (var c = 0; c < TILE_MAP[r].length; c++) {{
        var type = TILE_MAP[r][c];
        if (type === 'empty') continue;
        var color = TILE_COLORS[type] || TILE_COLORS.platform;
        if (color === 'transparent') continue;
        ctx.fillStyle = color;
        var tx = c * TILE_SIZE;
        var ty = r * TILE_SIZE;
        ctx.fillRect(tx, ty, TILE_SIZE, TILE_SIZE);
        // Add tile border for visual definition
        ctx.strokeStyle = 'rgba(0,0,0,0.2)';
        ctx.lineWidth = 1;
        ctx.strokeRect(tx, ty, TILE_SIZE, TILE_SIZE);
      }}
    }}
  }}"""

    # =========================================================================
    # Minimap
    # =========================================================================

    def _minimap_js(self) -> str:
        return f"""
  // ---- Minimap ----
  var MINIMAP_SIZE = {self.config.minimap_size};
  var minimapPadding = 10;

  function renderMinimap() {{
    if (!currentLevel) return;
    // Determine world bounds
    var worldW = W * 2, worldH = H * 2;
    if (currentLevel.width) worldW = currentLevel.width;
    if (currentLevel.height) worldH = currentLevel.height;
    var maxDim = Math.max(worldW, worldH);
    var scale = MINIMAP_SIZE / maxDim;

    var mmX = W - MINIMAP_SIZE - minimapPadding;
    var mmY = minimapPadding;

    // Background
    ctx.save();
    ctx.fillStyle = 'rgba(10, 10, 20, 0.75)';
    ctx.fillRect(mmX - 4, mmY - 4, MINIMAP_SIZE + 8, MINIMAP_SIZE + 8);
    ctx.strokeStyle = 'rgba(249, 115, 22, 0.6)';
    ctx.lineWidth = 1;
    ctx.strokeRect(mmX - 4, mmY - 4, MINIMAP_SIZE + 8, MINIMAP_SIZE + 8);
    ctx.restore();

    // Draw entities as dots (screen space - no camera offset)
    ctx.save();
    if (entities) {{
      for (var i = 0; i < entities.length; i++) {{
        var e = entities[i];
        if (!e.x && e.x !== 0) continue;
        var ex = mmX + e.x * scale;
        var ey = mmY + e.y * scale;
        if (e.type === 'enemy') {{
          ctx.fillStyle = '#ef4444';
          ctx.fillRect(ex - 1, ey - 1, 3, 3);
        }} else if (e.type === 'collectible') {{
          ctx.fillStyle = '#fbbf24';
          ctx.fillRect(ex - 1, ey - 1, 2, 2);
        }} else if (e.type === 'goal') {{
          ctx.fillStyle = '#22c55e';
          ctx.fillRect(ex - 2, ey - 2, 5, 5);
        }} else if (e.type === 'structure' || e.type === 'terrain') {{
          ctx.fillStyle = 'rgba(100, 100, 120, 0.5)';
          var ew = (e.w || 32) * scale;
          var eh = (e.h || 32) * scale;
          ctx.fillRect(ex, ey, Math.max(2, ew), Math.max(2, eh));
        }}
      }}
    }}

    // Player dot (bright)
    if (player) {{
      var px = mmX + player.x * scale;
      var py = mmY + player.y * scale;
      ctx.fillStyle = '#f97316';
      ctx.beginPath();
      ctx.arc(px, py, 3, 0, Math.PI * 2);
      ctx.fill();
    }}
    ctx.restore();
  }}"""

    # =========================================================================
    # Loop Integration Functions
    # =========================================================================

    def _loop_functions_js(self) -> str:
        update_parts: List[str] = []
        render_parts: List[str] = []

        if self.config.enable_screen_shake:
            update_parts.append("updateShake();")

        if self.config.enable_smooth_camera:
            update_parts.append("updateSmoothCamera();")
        else:
            update_parts.append("camera.x += shakeX || 0; camera.y += shakeY || 0;")

        if self.config.enable_achievements:
            update_parts.append("checkAchievements();")

        # Save notification timer
        update_parts.append("if (saveNotificationTimer > 0) saveNotificationTimer--;")
        update_parts.append("if (achievementBannerTimer > 0) achievementBannerTimer--;")

        if self.config.enable_tilemap:
            render_parts.append("renderTilemap();")

        # Render in screen space (after ctx.restore())
        if self.config.enable_minimap:
            render_parts.append("renderMinimap();")

        if self.config.enable_save_system or self.config.enable_achievements:
            render_parts.append("renderOverlays();")

        nl = "\n"
        update_body = nl.join("    " + p for p in update_parts)
        render_body = nl.join("    " + p for p in render_parts)

        return f"""
  // ---- Feature System Loop Integration ----
  function updateFeatureSystems() {{
{update_body}
  }}

  function renderFeatureSystems() {{
{render_body}
  }}

  function renderOverlays() {{
    // Save notification
    if (saveNotificationTimer > 0) {{
      var alpha = Math.min(1, saveNotificationTimer / 60);
      ctx.save();
      ctx.fillStyle = 'rgba(34, 197, 94, ' + (alpha * 0.9) + ')';
      ctx.fillRect(W / 2 - 100, H - 50, 200, 32);
      ctx.fillStyle = 'rgba(255, 255, 255, ' + alpha + ')';
      ctx.font = '14px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Progress Saved', W / 2, H - 30);
      ctx.restore();
    }}

    // Achievement banner
    if (achievementBannerTimer > 0) {{
      var bannerAlpha = Math.min(1, achievementBannerTimer / 60);
      var slideX = achievementBannerTimer > 180 ? (240 - achievementBannerTimer) * 3 : 0;
      ctx.save();
      ctx.fillStyle = 'rgba(249, 115, 22, ' + (bannerAlpha * 0.95) + ')';
      ctx.fillRect(W - 280 + slideX, 50, 260, 48);
      ctx.fillStyle = 'rgba(255, 255, 255, ' + bannerAlpha + ')';
      ctx.font = 'bold 16px sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText('Achievement Unlocked!', W - 270 + slideX, 70);
      ctx.font = '14px sans-serif';
      ctx.fillText(achievementBannerText, W - 270 + slideX, 88);
      ctx.restore();
    }}
  }}"""
