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
  - Origin-aware (auto-detects bridge URL from window.location)
  - Resilient (retries session creation with exponential backoff)
  - Bi-directional (reports applied directives back to the server)

Flow:
  1. On game start, client POSTs to create a bridge session
  2. Every N frames, client collects telemetry and POSTs it
  3. Every M frames, client GETs pending directives from the server
  4. Client applies directives to the running game
  5. Client POSTs acknowledgment for applied directives
  6. On game end or page unload, client ends the session

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
  var ACK_INTERVAL = 120;        // frames between ack batches (~2s)
  var pendingDirectives = [];
  var appliedDirectives = [];    // directives awaiting acknowledgment
  var lastEvents = [];
  var initAttempts = 0;
  var MAX_INIT_ATTEMPTS = 5;
  var sessionState = 'disconnected';  // disconnected, connecting, active, paused, ended
  var performanceMetrics = {
    frameTimes: [],
    lastFrameTime: 0,
    inputLatency: 0,
  };

  // Derive bridge URL from window.location if not explicitly provided.
  // This avoids hardcoding network addresses and lets the same game
  // run in any deployment (local dev, staging, production).
  function deriveBridgeUrl(explicitUrl) {
    if (explicitUrl) return explicitUrl;
    if (typeof window === 'undefined' || !window.location) {
      return '/api/agent/game-bridge';
    }
    // Same-origin: use relative URL (works if frontend proxies to backend)
    var loc = window.location;
    // If frontend is served from a different port than the backend,
    // assume the backend is on the same hostname at port 8000.
    // This is the SparkLabs default deployment topology.
    if (loc.port === '3000' || loc.port === '5173' || loc.port === '4173') {
      return loc.protocol + '//' + loc.hostname + ':8000/api/agent/game-bridge';
    }
    // Same-origin fallback
    return loc.origin + '/api/agent/game-bridge';
  }

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
    // Track frame time for performance metrics
    var now = (typeof performance !== 'undefined') ? performance.now() : Date.now();
    if (performanceMetrics.lastFrameTime > 0) {
      var dt = now - performanceMetrics.lastFrameTime;
      performanceMetrics.frameTimes.push(dt);
      if (performanceMetrics.frameTimes.length > 60) {
        performanceMetrics.frameTimes.shift();
      }
    }
    performanceMetrics.lastFrameTime = now;

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
      perf: {
        fps: computeFps(),
        input_latency_ms: performanceMetrics.inputLatency,
      },
    };
  }

  function computeFps() {
    if (performanceMetrics.frameTimes.length < 5) return 60;
    var sum = 0;
    for (var i = 0; i < performanceMetrics.frameTimes.length; i++) {
      sum += performanceMetrics.frameTimes[i];
    }
    var avgMs = sum / performanceMetrics.frameTimes.length;
    return avgMs > 0 ? Math.round(1000 / avgMs) : 60;
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
          // Telemetry response may include inline directives
          if (data && data.data && data.data.directives) {
            pendingDirectives = pendingDirectives.concat(data.data.directives);
          }
        })
        .catch(function() { /* silent: game continues without bridge */ });
    } catch (e) { /* fetch not available or network error */ }
  }

  // Fetch pending directives from the bridge
  function fetchDirectives() {
    if (!BRIDGE_ENABLED || !SESSION_ID) return;
    try {
      fetch(BRIDGE_URL + '/sessions/' + SESSION_ID + '/directives?limit=8', {
        method: 'GET',
      }).then(function(res) { return res.json(); })
        .then(function(data) {
          if (data && data.data && Array.isArray(data.data)) {
            pendingDirectives = pendingDirectives.concat(data.data);
          }
        })
        .catch(function() { /* silent */ });
    } catch (e) { /* fetch error */ }
  }

  // Apply a single directive to the running game
  function applyDirective(d) {
    var p = d.params || {};
    var applied = false;
    switch (d.directive_type) {
      case 'tune_difficulty':
        if (p.enemy_speed_multiplier && typeof CONFIG !== 'undefined') {
          CONFIG.enemySpeed = (CONFIG.enemySpeed || 1.4) * p.enemy_speed_multiplier;
          applied = true;
        }
        if (p.duration_ticks && typeof window.gameState !== 'undefined') {
          window.gameState.difficultyBoostTicks = p.duration_ticks;
        }
        break;
      case 'tune_physics':
        if (typeof CONFIG !== 'undefined') {
          if (p.gravity_multiplier) {
            CONFIG.gravity = (CONFIG.gravity || 0.55) * p.gravity_multiplier;
            applied = true;
          }
          if (p.jump_strength_multiplier) {
            CONFIG.jumpStrength = (CONFIG.jumpStrength || 11.0) * p.jump_strength_multiplier;
            applied = true;
          }
          if (p.move_speed_multiplier && CONFIG.moveSpeed) {
            CONFIG.moveSpeed = CONFIG.moveSpeed * p.move_speed_multiplier;
            applied = true;
          }
          if (p.friction_multiplier && CONFIG.friction) {
            CONFIG.friction = Math.max(0.5, Math.min(0.99, CONFIG.friction * p.friction_multiplier));
            applied = true;
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
            w: p.width || 24, h: p.height || 24,
            vx: p.vx !== undefined ? p.vx : (p.entity_type === 'enemy' ? -1.0 : 0),
            vy: p.vy || 0,
            color: p.color || (p.entity_type === 'enemy' ? '#ef4444' : '#fbbf24'),
            alive: true,
            id: 'bridge_' + Math.random().toString(36).substr(2, 6),
          };
          entities.push(ent);
          applied = true;
        }
        break;
      case 'despawn_entity':
        if (typeof entities !== 'undefined' && p.entity_id) {
          for (var i = 0; i < entities.length; i++) {
            if (entities[i].id === p.entity_id) {
              entities.splice(i, 1);
              applied = true;
              break;
            }
          }
        }
        break;
      case 'trigger_event':
        if (p.event === 'pacing_nudge') {
          showHintMessage(p.message || 'Keep going forward!');
          applied = true;
        } else if (p.event === 'celebration') {
          showHintMessage(p.message || 'Great job!', '#10b981');
          applied = true;
        } else if (p.event === 'camera_shake' && typeof shakeCamera === 'function') {
          shakeCamera(p.intensity || 4, p.duration || 20);
          applied = true;
        }
        break;
      case 'adjust_pacing':
        // Pacing adjustment handled by spawn/tune directives
        if (typeof window.gameState !== 'undefined') {
          window.gameState.pacingMode = p.mode || 'normal';
          applied = true;
        }
        break;
      case 'morph_entity':
        // Morph entity type (e.g., enemy -> tougher enemy)
        if (typeof entities !== 'undefined' && p.entity_id && p.morph_to) {
          for (var j = 0; j < entities.length; j++) {
            if (entities[j].id === p.entity_id) {
              entities[j].type = p.morph_to;
              entities[j].color = p.color || entities[j].color;
              applied = true;
              break;
            }
          }
        }
        break;
      case 'broadcast_signal':
        if (typeof window.gameState !== 'undefined') {
          window.gameState.lastSignal = p.signal || 'unknown';
          window.gameState.signalPayload = p.payload || {};
          applied = true;
        }
        break;
      case 'no_op':
        // No operation - just sync flow state
        if (typeof window.gameState !== 'undefined') {
          window.gameState.flowState = p.flow_state || 'unknown';
          window.gameState.skillEstimate = p.skill_estimate || 0.5;
          window.gameState.targetDifficulty = p.target_difficulty || 0.5;
          applied = true;
        }
        break;
    }
    return applied;
  }

  // Apply all pending directives
  function applyDirectives() {
    var applied = [];
    while (pendingDirectives.length > 0) {
      var d = pendingDirectives.shift();
      try {
        var ok = applyDirective(d);
        if (ok) {
          applied.push({
            directive_id: d.directive_id,
            directive_type: d.directive_type,
            applied_at: Date.now() / 1000,
          });
        }
      } catch (e) { /* skip invalid directive */ }
    }
    // Queue for acknowledgment
    if (applied.length > 0) {
      appliedDirectives = appliedDirectives.concat(applied);
    }
  }

  // Send acknowledgment for applied directives
  function sendAcknowledgments() {
    if (!BRIDGE_ENABLED || !SESSION_ID || appliedDirectives.length === 0) return;
    var batch = appliedDirectives.slice();
    appliedDirectives = [];
    try {
      fetch(BRIDGE_URL + '/sessions/' + SESSION_ID + '/directives/ack', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ applied: batch }),
      }).catch(function() { /* silent */ });
    } catch (e) { /* silent */ }
  }

  // Show a transient hint message without blocking gameplay
  function showHintMessage(msg, color) {
    if (typeof document === 'undefined') return;
    var hint = document.createElement('div');
    hint.textContent = msg;
    var bg = color || '#f97316';
    hint.style.cssText = 'position:absolute;top:20%;left:50%;transform:translateX(-50%);' +
      'background:rgba(0,0,0,0.8);color:' + bg + ';padding:6px 16px;border-radius:6px;' +
      'font:600 12px monospace;z-index:50;pointer-events:none;transition:opacity 1s;';
    var container = document.getElementById('gameContainer') || document.body;
    container.appendChild(hint);
    setTimeout(function() { hint.style.opacity = '0'; }, 1500);
    setTimeout(function() { if (hint.parentNode) hint.parentNode.removeChild(hint); }, 2500);
  }

  // Start a bridge session with exponential backoff retry
  function startBridgeSession(gameTitle, genre) {
    if (!BRIDGE_URL || initAttempts >= MAX_INIT_ATTEMPTS) return;
    initAttempts++;
    sessionState = 'connecting';
    var backoffMs = Math.min(8000, 500 * Math.pow(2, initAttempts - 1));
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
            sessionState = 'active';
          } else {
            scheduleRetry(gameTitle, genre, backoffMs);
          }
        })
        .catch(function() {
          scheduleRetry(gameTitle, genre, backoffMs);
        });
    } catch (e) {
      scheduleRetry(gameTitle, genre, backoffMs);
    }
  }

  function scheduleRetry(gameTitle, genre, backoffMs) {
    if (initAttempts >= MAX_INIT_ATTEMPTS) {
      sessionState = 'disconnected';
      return;
    }
    setTimeout(function() { startBridgeSession(gameTitle, genre); }, backoffMs);
  }

  // End the bridge session
  function endBridgeSession() {
    if (!BRIDGE_ENABLED || !SESSION_ID) return;
    sessionState = 'ended';
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
    BRIDGE_URL = deriveBridgeUrl(bridgeUrl);
    startBridgeSession(gameTitle, genre);
  };

  window.bridgeTick = function() {
    BRIDGE_TICK++;
    if (!BRIDGE_ENABLED) return;
    if (BRIDGE_TICK % TELEMETRY_INTERVAL === 0) {
      sendTelemetry();
    }
    if (BRIDGE_TICK % DIRECTIVE_INTERVAL === 0) {
      fetchDirectives();
    }
    // Apply directives every frame (cheap operation)
    if (pendingDirectives.length > 0) {
      applyDirectives();
    }
    if (BRIDGE_TICK % ACK_INTERVAL === 0) {
      sendAcknowledgments();
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

  window.getBridgeState = function() {
    return {
      enabled: BRIDGE_ENABLED,
      session_id: SESSION_ID,
      state: sessionState,
      tick: BRIDGE_TICK,
      pending: pendingDirectives.length,
      applied_queue: appliedDirectives.length,
      fps: computeFps(),
    };
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

    # No hardcoded network address - client auto-derives from window.location.
    # The explicit URL passed to build_script() takes precedence.
    DEFAULT_BRIDGE_URL = ""

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

        If bridge_url is empty, the client auto-derives the URL from
        window.location at runtime, avoiding any hardcoded network address.
        """
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
        # If a specific URL is provided, inject it as the default
        if bridge_url:
            js = js.replace(
                "function deriveBridgeUrl(explicitUrl) {",
                f"function deriveBridgeUrl(explicitUrl) {{ return explicitUrl || '{bridge_url}';",
                1,
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
        url_escaped = bridge_url.replace("'", "\\'")
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
