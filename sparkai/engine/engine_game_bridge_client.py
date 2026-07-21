"""
SparkLabs Engine - Game Bridge Client

Generates the JavaScript bridge client snippet that gets injected into
generated HTML5 games. This client connects the running browser game to
the server-side AI-Native Game Bridge, enabling real-time AI observation
and adaptation of the generated game.

The client is designed to be:
  - Self-contained (no external dependencies beyond fetch API)
  - Non-blocking (async HTTP, never stalls the game loop)
  - Gracefully degrading (bridge unavailable = game still works)
  - Safe (validates directives before applying them)

Flow:
  1. On game start, client POSTs to create a bridge session
  2. Every N frames, client collects telemetry and POSTs it
  3. The bridge responds with pending directives
  4. Client applies directives to the running game
  5. On game end or page unload, client ends the session

Integration points in the generated game:
  - window.initBridge(url, title, genre)  -> call once on game start
  - window.bridgeTick()                   -> call once per frame
  - window.trackBridgeEvent(name)         -> call on jump/death/collect/etc.
  - window.endBridge()                    -> call on game over
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Bridge Client JavaScript
# =============================================================================

BRIDGE_CLIENT_JS = r"""
// =============================================================================
// SparkLabs AI-Native Game Bridge Client
// Connects this game to the server-side cognitive engine for real-time
// AI observation and adaptation. Non-blocking: if the bridge is
// unavailable, the game continues to run normally.
// =============================================================================
(function() {
  var BRIDGE_ENABLED = false;
  var BRIDGE_URL = '';
  var SESSION_ID = null;
  var BRIDGE_TICK = 0;
  var TELEMETRY_INTERVAL = 30;   // frames between telemetry reports (~0.5s)
  var DIRECTIVE_INTERVAL = 60;   // frames between directive polls (~1s)
  var pendingDirectives = [];
  var lastEvents = [];
  var lastHealth = 100;
  var initAttempts = 0;

  // Collect telemetry from the running game state
  function collectTelemetry() {
    if (typeof player === 'undefined' || !player) return null;
    var events = lastEvents.slice();
    lastEvents = [];
    var enemyCount = 0;
    var collectibleCount = 0;
    if (typeof entities !== 'undefined' && entities) {
      for (var i = 0; i < entities.length; i++) {
        if (entities[i].type === 'enemy') enemyCount++;
        else if (entities[i].type === 'collectible') collectibleCount++;
      }
    }
    return {
      tick: BRIDGE_TICK,
      timestamp: Date.now() / 1000,
      player: {
        x: player.x || 0,
        y: player.y || 0,
        vx: player.vx || 0,
        vy: player.vy || 0,
        health: (typeof lives !== 'undefined') ? lives * 20 : 100,
        on_ground: player.onGround || false,
        wall_sliding: player.isWallSliding || false,
        jumps_remaining: player.jumpsRemaining || 0,
      },
      events: events,
      score: (typeof score !== 'undefined') ? score : 0,
      lives: (typeof lives !== 'undefined') ? lives : 3,
      level: (typeof levelIdx !== 'undefined') ? levelIdx + 1 : 1,
      enemy_count: enemyCount,
      collectible_count: collectibleCount,
    };
  }

  // Send telemetry frame to the bridge
  function sendTelemetry() {
    if (!BRIDGE_ENABLED || !SESSION_ID) return;
    var frame = collectTelemetry();
    if (!frame) return;
    try {
      fetch(BRIDGE_URL + '/sessions/' + SESSION_ID + '/telemetry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(frame),
      }).then(function(res) { return res.json(); })
        .then(function(data) {
          if (data && data.data && data.data.directives) {
            pendingDirectives = pendingDirectives.concat(data.data.directives);
          }
        })
        .catch(function() { /* silent: game continues without bridge */ });
    } catch (e) { /* fetch not available or network error */ }
  }

  // Apply a single directive to the running game
  function applyDirective(d) {
    var p = d.params || {};
    switch (d.directive_type) {
      case 'tune_difficulty':
        if (p.enemy_speed_multiplier && typeof CONFIG !== 'undefined') {
          CONFIG.enemySpeed = (CONFIG.enemySpeed || 1.4) * p.enemy_speed_multiplier;
        }
        break;
      case 'tune_physics':
        if (typeof CONFIG !== 'undefined') {
          if (p.gravity_multiplier) {
            CONFIG.gravity = (CONFIG.gravity || 0.55) * p.gravity_multiplier;
          }
          if (p.jump_strength_multiplier) {
            CONFIG.jumpStrength = (CONFIG.jumpStrength || 11.0) * p.jump_strength_multiplier;
          }
        }
        break;
      case 'spawn_entity':
        if (typeof entities !== 'undefined' && p.entity_type) {
          var spawnX = p.x !== undefined ? p.x : (player ? player.x + 200 : 400);
          var spawnY = p.y !== undefined ? p.y : 400;
          var ent = {
            type: p.entity_type,
            x: spawnX, y: spawnY,
            w: 24, h: 24,
            vx: p.entity_type === 'enemy' ? -1.0 : 0,
            vy: 0,
            color: p.entity_type === 'enemy' ? '#ef4444' : '#fbbf24',
            alive: true,
          };
          entities.push(ent);
        }
        break;
      case 'despawn_entity':
        if (typeof entities !== 'undefined' && p.entity_id) {
          for (var i = 0; i < entities.length; i++) {
            if (entities[i].id === p.entity_id) {
              entities.splice(i, 1);
              break;
            }
          }
        }
        break;
      case 'trigger_event':
        if (p.event === 'pacing_nudge' && typeof showOverlay === 'function') {
          // Brief hint overlay without blocking gameplay
          showHintMessage('Keep going forward!');
        }
        break;
      case 'adjust_pacing':
        // Pacing adjustment is handled by spawn/tune directives
        break;
      case 'morph_entity':
        // Entity morphing would require game-specific entity model
        break;
      case 'broadcast_signal':
        // Broadcast a signal that game logic can pick up
        if (typeof window.gameState !== 'undefined') {
          window.gameState.lastSignal = p.signal || 'unknown';
        }
        break;
      case 'no_op':
        // No operation - just sync flow state
        if (typeof window.gameState !== 'undefined') {
          window.gameState.flowState = p.flow_state || 'unknown';
          window.gameState.skillEstimate = p.skill_estimate || 0.5;
        }
        break;
    }
  }

  // Apply all pending directives
  function applyDirectives() {
    while (pendingDirectives.length > 0) {
      var d = pendingDirectives.shift();
      try { applyDirective(d); } catch (e) { /* skip invalid directive */ }
    }
  }

  // Show a transient hint message without blocking gameplay
  function showHintMessage(msg) {
    if (typeof document === 'undefined') return;
    var hint = document.createElement('div');
    hint.textContent = msg;
    hint.style.cssText = 'position:absolute;top:20%;left:50%;transform:translateX(-50%);' +
      'background:rgba(0,0,0,0.8);color:#f97316;padding:6px 16px;border-radius:6px;' +
      'font:600 12px monospace;z-index:50;pointer-events:none;transition:opacity 1s;';
    var container = document.getElementById('gameContainer') || document.body;
    container.appendChild(hint);
    setTimeout(function() { hint.style.opacity = '0'; }, 1500);
    setTimeout(function() { if (hint.parentNode) hint.parentNode.removeChild(hint); }, 2500);
  }

  // Start a bridge session
  function startBridgeSession(gameTitle, genre) {
    if (!BRIDGE_URL || initAttempts > 2) return;
    initAttempts++;
    try {
      fetch(BRIDGE_URL + '/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: 'generated_game',
          game_title: gameTitle || 'SparkLabs Game',
          genre: genre || 'platformer',
          player_id: 'player_' + Math.random().toString(36).substr(2, 8),
        }),
      }).then(function(res) { return res.json(); })
        .then(function(data) {
          if (data && data.data && data.data.session_id) {
            SESSION_ID = data.data.session_id;
            BRIDGE_ENABLED = true;
            initAttempts = 0;
          }
        })
        .catch(function() { /* bridge unavailable, game continues */ });
    } catch (e) { /* fetch error */ }
  }

  // End the bridge session
  function endBridgeSession() {
    if (!BRIDGE_ENABLED || !SESSION_ID) return;
    try {
      fetch(BRIDGE_URL + '/sessions/' + SESSION_ID + '/end', {
        method: 'POST',
      }).catch(function() { /* silent */ });
    } catch (e) { /* silent */ }
    BRIDGE_ENABLED = false;
    SESSION_ID = null;
  }

  // Public API
  window.initBridge = function(bridgeUrl, gameTitle, genre) {
    BRIDGE_URL = bridgeUrl || 'http://localhost:8000/api/agent/game-bridge';
    startBridgeSession(gameTitle, genre);
  };

  window.bridgeTick = function() {
    BRIDGE_TICK++;
    if (BRIDGE_TICK % TELEMETRY_INTERVAL === 0) {
      sendTelemetry();
    }
    if (BRIDGE_TICK % DIRECTIVE_INTERVAL === 0) {
      applyDirectives();
    }
  };

  window.trackBridgeEvent = function(eventName) {
    if (lastEvents.length < 10) {
      lastEvents.push(eventName);
    }
  };

  window.endBridge = function() {
    endBridgeSession();
  };

  // Cleanup on page unload
  if (typeof window !== 'undefined') {
    window.addEventListener('beforeunload', endBridgeSession);
  }
})();
"""


# =============================================================================
# Bridge Client Builder
# =============================================================================


class BridgeClientBuilder:
    """
    Builds the bridge client JavaScript snippet for injection into
    generated HTML5 games. The builder can customize the bridge URL
    and telemetry intervals based on the game configuration.
    """

    DEFAULT_BRIDGE_URL = "http://localhost:8000/api/agent/game-bridge"

    @classmethod
    def build_script(
        cls,
        bridge_url: str = "",
        telemetry_interval: int = 30,
        directive_interval: int = 60,
    ) -> str:
        """
        Build the bridge client JavaScript with the given configuration.
        Returns the full script as a string (without <script> tags).
        """
        url = bridge_url or cls.DEFAULT_BRIDGE_URL
        js = BRIDGE_CLIENT_JS
        # Override the default intervals if provided
        if telemetry_interval != 30:
            js = js.replace(
                "var TELEMETRY_INTERVAL = 30;",
                f"var TELEMETRY_INTERVAL = {int(telemetry_interval)};",
            )
        if directive_interval != 60:
            js = js.replace(
                "var DIRECTIVE_INTERVAL = 60;",
                f"var DIRECTIVE_INTERVAL = {int(directive_interval)};",
            )
        # Override the default bridge URL
        if url != cls.DEFAULT_BRIDGE_URL:
            js = js.replace(
                cls.DEFAULT_BRIDGE_URL,
                url,
            )
        return js

    @classmethod
    def build_init_call(
        cls,
        game_title: str = "",
        genre: str = "",
        bridge_url: str = "",
    ) -> str:
        """
        Build the JavaScript call to initialize the bridge when the
        game starts. This should be called after the game's main
        initialization code.
        """
        title_escaped = game_title.replace("'", "\\'").replace('"', '\\"')
        genre_escaped = genre.replace("'", "\\'").replace('"', '\\"')
        url = bridge_url or cls.DEFAULT_BRIDGE_URL
        url_escaped = url.replace("'", "\\'")
        return (
            f"if (typeof window.initBridge === 'function') {{ "
            f"window.initBridge('{url_escaped}', '{title_escaped}', '{genre_escaped}'); "
            f"}}"
        )

    @classmethod
    def build_tick_call(cls) -> str:
        """Build the JavaScript call to run the bridge tick each frame."""
        return "if (typeof window.bridgeTick === 'function') { window.bridgeTick(); }"

    @classmethod
    def build_event_track_call(cls, event_name: str) -> str:
        """Build the JavaScript call to track a game event."""
        escaped = event_name.replace("'", "\\'")
        return (
            f"if (typeof window.trackBridgeEvent === 'function') {{ "
            f"window.trackBridgeEvent('{escaped}'); "
            f"}}"
        )

    @classmethod
    def build_end_call(cls) -> str:
        """Build the JavaScript call to end the bridge session."""
        return "if (typeof window.endBridge === 'function') { window.endBridge(); }"

    @classmethod
    def build_full_script_tag(
        cls,
        game_title: str = "",
        genre: str = "",
        bridge_url: str = "",
        telemetry_interval: int = 30,
        directive_interval: int = 60,
    ) -> str:
        """
        Build the complete bridge client as a <script> tag ready for
        injection into the generated HTML.
        """
        script = cls.build_script(bridge_url, telemetry_interval, directive_interval)
        return f"<script>\n{script}\n</script>\n"
