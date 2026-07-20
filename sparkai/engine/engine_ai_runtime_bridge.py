"""
SparkLabs - AI Runtime Bridge

Connects the cognitive layer (architect, conductor, brain) to the actual
game generation pipeline (GameRuntime). The bridge makes generated games
truly AI-native by:

  1. Pre-build reasoning - the architect reasons about the prompt to derive
     AI-driven parameters (difficulty target, pacing curve, narrative beats).
  2. Config adaptation - the AIConfigAdapter merges AI parameters into the
     GameConfig, adjusting gravity, enemy speed, collectible count, etc.
  3. Telemetry injection - the AITelemetryInjector embeds a JavaScript bridge
     that reports player events to the parent window for the conductor.
  4. Adaptive difficulty injection - the AdaptiveDifficultyInjector embeds
     a JavaScript controller that adjusts game parameters in real-time based
     on player performance signals (deaths, collectibles, time, progress).
  5. Build wrapping - the AIRuntimeBridge wraps GameRuntime.build_from_gdd
     with the full AI pipeline, producing an AIRuntimeResult.

The injected JavaScript is self-contained and runs entirely in the browser,
communicating with the AI layer via window.postMessage. This design keeps
the game executable offline while still reflecting AI-driven adaptation.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AI-Driven Configuration Adapter
# ---------------------------------------------------------------------------

class AIConfigAdapter:
    """
    Adapts a GameConfig with AI-driven parameters derived from the
    cognitive architect, conductor, and game brain.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._adaptation_count = 0
        self._last_overrides: Dict[str, Any] = {}

    def derive_overrides(
        self, prompt: str = "", genre: str = "",
        player_skill: float = 0.5, pacing_zone: str = "intro",
        difficulty_target: float = 0.5,
    ) -> Dict[str, Any]:
        """Derive AI-driven parameter overrides from cognitive state."""
        overrides: Dict[str, Any] = {}

        # Difficulty-driven parameter adjustments
        # difficulty_target: 0.0 (relaxed) .. 1.0 (intense)
        diff = max(0.0, min(1.0, difficulty_target))

        # Gravity: higher difficulty = slightly stronger gravity for tighter control
        overrides["gravity_scale"] = 0.9 + 0.3 * diff

        # Enemy speed: scales with difficulty
        overrides["enemy_speed_scale"] = 0.7 + 0.6 * diff

        # Enemy count: more enemies at higher difficulty
        overrides["enemy_count_delta"] = int(round((diff - 0.5) * 6))

        # Collectible count: fewer collectibles at higher difficulty
        overrides["collectible_count_delta"] = -int(round((diff - 0.5) * 4))

        # Move speed: slightly faster at higher difficulty for urgency
        overrides["move_speed_scale"] = 0.95 + 0.15 * diff

        # Jump strength: slightly weaker at higher difficulty for precision
        overrides["jump_strength_scale"] = 1.05 - 0.1 * diff

        # Lives: fewer at higher difficulty
        overrides["lives_delta"] = -int(round(max(0, diff - 0.5) * 3))

        # Pacing-driven adjustments
        if pacing_zone == "peak":
            overrides["vfx_intensity"] = 1.3
            overrides["particle_density"] = 1.2
        elif pacing_zone == "relief":
            overrides["vfx_intensity"] = 0.7
            overrides["particle_density"] = 0.8
        elif pacing_zone == "finale":
            overrides["vfx_intensity"] = 1.5
            overrides["particle_density"] = 1.4
        else:
            overrides["vfx_intensity"] = 1.0
            overrides["particle_density"] = 1.0

        # Player-skill-driven adjustments
        if player_skill > 0.75:
            overrides["enemy_count_delta"] = overrides.get("enemy_count_delta", 0) + 2
            overrides["challenge_level"] = "hard"
        elif player_skill < 0.3:
            overrides["enemy_count_delta"] = overrides.get("enemy_count_delta", 0) - 2
            overrides["challenge_level"] = "easy"
        else:
            overrides["challenge_level"] = "normal"

        with self._lock:
            self._adaptation_count += 1
            self._last_overrides = dict(overrides)

        return overrides

    def apply_to_config(self, config: Any, overrides: Dict[str, Any]) -> Any:
        """Apply AI-derived overrides to a GameConfig in-place."""
        if config is None:
            return config

        # Apply scalar scales
        if "gravity_scale" in overrides and hasattr(config, "gravity"):
            config.gravity = config.gravity * overrides["gravity_scale"]
        if "enemy_speed_scale" in overrides and hasattr(config, "enemy_speed"):
            config.enemy_speed = config.enemy_speed * overrides["enemy_speed_scale"]
        if "move_speed_scale" in overrides and hasattr(config, "move_speed"):
            config.move_speed = config.move_speed * overrides["move_speed_scale"]
        if "jump_strength_scale" in overrides and hasattr(config, "jump_strength"):
            config.jump_strength = config.jump_strength * overrides["jump_strength_scale"]

        # Apply count deltas
        if "enemy_count_delta" in overrides and hasattr(config, "enemy_count"):
            config.enemy_count = max(0, config.enemy_count + overrides["enemy_count_delta"])
        if "collectible_count_delta" in overrides and hasattr(config, "collectible_count"):
            config.collectible_count = max(0, config.collectible_count + overrides["collectible_count_delta"])
        if "lives_delta" in overrides and hasattr(config, "lives"):
            config.lives = max(1, config.lives + overrides["lives_delta"])

        return config

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "adaptation_count": self._adaptation_count,
                "last_overrides": dict(self._last_overrides),
            }


# ---------------------------------------------------------------------------
# AI Telemetry Injector
# ---------------------------------------------------------------------------

class AITelemetryInjector:
    """
    Injects a JavaScript telemetry bridge into the generated HTML that
    reports player events to the parent window via postMessage.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._injection_count = 0

    def build_header_js(self) -> str:
        """Build the JavaScript telemetry bridge for the HTML header."""
        return """
<!-- SparkLabs AI Telemetry Bridge -->
<script>
window.SparkLabsAI = window.SparkLabsAI || {};
(function() {
  var AI = window.SparkLabsAI;
  AI.sessionId = 'ai_' + Math.random().toString(36).substr(2, 9);
  AI.eventQueue = [];
  AI.tickCount = 0;
  AI.lastReport = 0;
  AI.playerState = {
    x: 0, y: 0, vx: 0, vy: 0,
    health: 100, lives: 3, score: 0,
    onGround: true, moving: false,
  };
  AI.performance = {
    deaths: 0, collectibles: 0, enemiesDefeated: 0,
    distanceTraveled: 0, timeAlive: 0, currentLevel: 0,
    deathTimes: [], collectibleTimes: [],
  };
  AI.adaptiveParams = {
    gravityScale: 1.0, enemySpeedScale: 1.0, moveSpeedScale: 1.0,
    jumpStrengthScale: 1.0, difficultyMultiplier: 1.0,
  };

  // Report an event to the parent window
  AI.report = function(eventType, payload) {
    var event = {
      sessionId: AI.sessionId,
      type: eventType,
      payload: payload || {},
      tick: AI.tickCount,
      time: Date.now(),
    };
    AI.eventQueue.push(event);
    // Send to parent if available
    if (window.parent && window.parent !== window) {
      try {
        window.parent.postMessage({
          source: 'sparklabs-ai-telemetry',
          event: event,
        }, '*');
      } catch(e) { /* cross-origin may block */ }
    }
    // Trim queue
    if (AI.eventQueue.length > 100) {
      AI.eventQueue = AI.eventQueue.slice(-50);
    }
  };

  // Update player state tracking
  AI.updatePlayerState = function(state) {
    var prev = AI.playerState;
    AI.playerState = Object.assign({}, prev, state);
    // Track distance
    var dx = (state.x || 0) - (prev.x || 0);
    var dy = (state.y || 0) - (prev.y || 0);
    AI.performance.distanceTraveled += Math.sqrt(dx*dx + dy*dy);
    // Track movement
    AI.playerState.moving = Math.abs(state.vx || 0) > 0.5;
  };

  // Record a death event
  AI.recordDeath = function() {
    AI.performance.deaths++;
    AI.performance.deathTimes.push(AI.tickCount);
    AI.report('player_death', {
      deaths: AI.performance.deaths,
      x: AI.playerState.x, y: AI.playerState.y,
      tick: AI.tickCount,
    });
  };

  // Record a collectible pickup
  AI.recordCollectible = function(value) {
    AI.performance.collectibles++;
    AI.performance.collectibleTimes.push(AI.tickCount);
    AI.report('collectible', {
      total: AI.performance.collectibles,
      value: value || 1,
      x: AI.playerState.x, y: AI.playerState.y,
    });
  };

  // Record an enemy defeat
  AI.recordEnemyDefeat = function() {
    AI.performance.enemiesDefeated++;
    AI.report('enemy_defeated', {
      total: AI.performance.enemiesDefeated,
    });
  };

  // Record a level change
  AI.recordLevelChange = function(level) {
    AI.performance.currentLevel = level;
    AI.report('level_change', { level: level });
  };

  // Get a performance summary
  AI.getPerformanceSummary = function() {
    return {
      deaths: AI.performance.deaths,
      collectibles: AI.performance.collectibles,
      enemiesDefeated: AI.performance.enemiesDefeated,
      distanceTraveled: Math.round(AI.performance.distanceTraveled),
      timeAlive: AI.performance.timeAlive,
      currentLevel: AI.performance.currentLevel,
      tickCount: AI.tickCount,
      deathRate: AI.performance.deaths / Math.max(1, AI.performance.timeAlive),
      collectibleRate: AI.performance.collectibles / Math.max(1, AI.performance.timeAlive),
    };
  };

  // Receive adaptive parameters from the parent
  window.addEventListener('message', function(msg) {
    if (msg.data && msg.data.source === 'sparklabs-ai-adapt') {
      AI.adaptiveParams = Object.assign(AI.adaptiveParams, msg.data.params || {});
    }
  });

  AI.report('session_start', { sessionId: AI.sessionId });
})();
</script>
<!-- End SparkLabs AI Telemetry Bridge -->
"""

    def build_loop_patch_js(self) -> str:
        """Build the JavaScript telemetry patch for the game loop."""
        return """
<!-- SparkLabs AI Loop Patch -->
<script>
(function() {
  // Patch the game loop to increment tick count and report periodically
  var origUpdate = window.update || function() {};
  window.update = function() {
    try {
      window.SparkLabsAI.tickCount++;
      window.SparkLabsAI.performance.timeAlive++;
      // Report every 120 ticks (~2 seconds at 60fps)
      if (window.SparkLabsAI.tickCount % 120 === 0) {
        window.SparkLabsAI.report('tick_summary', window.SparkLabsAI.getPerformanceSummary());
      }
    } catch(e) { /* telemetry must never break the game */ }
    return origUpdate.apply(this, arguments);
  };
})();
</script>
<!-- End SparkLabs AI Loop Patch -->
"""

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {"injection_count": self._injection_count}


# ---------------------------------------------------------------------------
# Adaptive Difficulty Injector
# ---------------------------------------------------------------------------

class AdaptiveDifficultyInjector:
    """
    Injects a JavaScript adaptive difficulty controller that adjusts
    game parameters in real-time based on player performance signals.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._injection_count = 0

    def build_header_js(self, initial_difficulty: float = 0.5) -> str:
        """Build the adaptive difficulty controller for the HTML header."""
        initial = max(0.1, min(1.0, initial_difficulty))
        return f"""
<!-- SparkLabs Adaptive Difficulty Controller -->
<script>
window.SparkLabsAI = window.SparkLabsAI || {{}};
(function() {{
  var AI = window.SparkLabsAI;
  AI.difficulty = {{
    current: {initial},
    target: {initial},
    min: 0.2,
    max: 1.0,
    adjustmentRate: 0.02,
    lastAdjustment: 0,
    adjustmentInterval: 180,  // 3 seconds at 60fps
    flowChannel: {{ lower: 0.3, upper: 0.7 }},
  }};

  AI.difficulty.adjust = function() {{
    var perf = AI.getPerformanceSummary();
    var tick = AI.tickCount;
    // Only adjust at intervals
    if (tick - AI.difficulty.lastAdjustment < AI.difficulty.adjustmentInterval) {{
      return;
    }}
    AI.difficulty.lastAdjustment = tick;

    // Compute player skill estimate from performance
    // Low death rate + high collectible rate = high skill
    var deathRate = perf.deathRate || 0;
    var collectibleRate = perf.collectibleRate || 0;
    var skillEstimate = Math.max(0, Math.min(1,
      0.5 - deathRate * 2 + collectibleRate * 0.5
    ));

    // Move target toward the flow channel (slightly above skill)
    AI.difficulty.target = Math.max(
      AI.difficulty.min,
      Math.min(AI.difficulty.max, skillEstimate + 0.15)
    );

    // Gradually move current toward target
    var delta = AI.difficulty.target - AI.difficulty.current;
    AI.difficulty.current += delta * AI.difficulty.adjustmentRate;

    // Compute adaptive parameter multipliers
    var d = AI.difficulty.current;
    AI.adaptiveParams.gravityScale = 0.9 + 0.3 * d;
    AI.adaptiveParams.enemySpeedScale = 0.7 + 0.6 * d;
    AI.adaptiveParams.moveSpeedScale = 0.95 + 0.15 * d;
    AI.adaptiveParams.jumpStrengthScale = 1.05 - 0.1 * d;
    AI.adaptiveParams.difficultyMultiplier = d;

    // Report the adjustment
    AI.report('difficulty_adjusted', {{
      current: d,
      target: AI.difficulty.target,
      skillEstimate: skillEstimate,
      deathRate: deathRate,
      collectibleRate: collectibleRate,
    }});
  }};

  AI.difficulty.getMultiplier = function(param) {{
    var map = {{
      gravity: AI.adaptiveParams.gravityScale,
      enemySpeed: AI.adaptiveParams.enemySpeedScale,
      moveSpeed: AI.adaptiveParams.moveSpeedScale,
      jumpStrength: AI.adaptiveParams.jumpStrengthScale,
      difficulty: AI.adaptiveParams.difficultyMultiplier,
    }};
    return map[param] || 1.0;
  }};
}})();
</script>
<!-- End SparkLabs Adaptive Difficulty Controller -->
"""

    def build_loop_patch_js(self) -> str:
        """Build the adaptive difficulty loop patch."""
        return """
<!-- SparkLabs Adaptive Difficulty Loop Patch -->
<script>
(function() {
  // Patch the game loop to run the difficulty adjuster
  var origUpdate = window.update || function() {};
  window.update = function() {
    try {
      if (window.SparkLabsAI && window.SparkLabsAI.difficulty) {
        window.SparkLabsAI.difficulty.adjust();
      }
    } catch(e) { /* difficulty controller must never break the game */ }
    return origUpdate.apply(this, arguments);
  };
})();
</script>
<!-- End SparkLabs Adaptive Difficulty Loop Patch -->
"""

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {"injection_count": self._injection_count}


# ---------------------------------------------------------------------------
# AI Runtime Result
# ---------------------------------------------------------------------------

@dataclass
class AIRuntimeResult:
    """Result of an AI-driven game runtime build."""
    success: bool
    html: str
    config: Optional[Any]
    error: Optional[str]
    duration_s: float
    metadata: Dict[str, Any]
    ai_overrides: Dict[str, Any] = field(default_factory=dict)
    ai_session_id: str = ""
    ai_reasoning_conclusion: str = ""


# ---------------------------------------------------------------------------
# AI Runtime Bridge (Singleton)
# ---------------------------------------------------------------------------

class AIRuntimeBridge:
    """
    Singleton bridge that wraps GameRuntime with AI-driven pre-build
    reasoning, config adaptation, and post-build telemetry/adaptive
    difficulty injection.
    """

    _instance: Optional["AIRuntimeBridge"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized = False
        self._runtime: Optional[Any] = None
        self._architect: Optional[Any] = None
        self._conductor: Optional[Any] = None
        self._brain: Optional[Any] = None
        self._adapter = AIConfigAdapter()
        self._telemetry = AITelemetryInjector()
        self._adaptive = AdaptiveDifficultyInjector()
        self._build_count = 0
        self._last_result: Optional[AIRuntimeResult] = None

    @classmethod
    def get_instance(cls) -> "AIRuntimeBridge":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def initialize(self) -> None:
        """Initialize the bridge by acquiring the runtime and cognitive layer."""
        with self._lock:
            if self._initialized:
                return
            try:
                from sparkai.engine.engine_game_runtime import GameRuntime
                self._runtime = GameRuntime.get_instance()
            except Exception as exc:
                logger.warning("GameRuntime acquisition failed: %s", exc)
                self._runtime = None
            try:
                from sparkai.agent.agent_cognitive_architect import (
                    CognitiveArchitect,
                )
                self._architect = CognitiveArchitect.get_instance()
            except Exception as exc:
                logger.warning("CognitiveArchitect acquisition failed: %s", exc)
                self._architect = None
            try:
                from sparkai.engine.engine_ai_native_conductor import (
                    AINativeConductor,
                )
                self._conductor = AINativeConductor.get_instance()
            except Exception as exc:
                logger.warning("AINativeConductor acquisition failed: %s", exc)
                self._conductor = None
            try:
                from sparkai.agent.agent_game_brain import GameBrain
                self._brain = GameBrain.get_instance()
            except Exception as exc:
                logger.warning("GameBrain acquisition failed: %s", exc)
                self._brain = None
            self._initialized = True
            logger.info("AIRuntimeBridge initialized")

    # -----------------------------------------------------------------
    # Build Pipeline
    # -----------------------------------------------------------------

    def build_from_gdd(
        self, gdd: Any, prompt: str = "",
    ) -> AIRuntimeResult:
        """
        Build a game from a GDD with AI-driven adaptation.

        The pipeline:
          1. Pre-build: architect reasons about the prompt (if provided)
          2. Build: GameRuntime compiles and assembles the game
          3. Post-build: adapter applies AI overrides, injectors add AI scripts
        """
        if not self._initialized:
            self.initialize()
        start = time.time()
        ai_session_id = f"aibuild_{uuid.uuid4().hex[:10]}"

        try:
            with self._lock:
                self._build_count += 1

            # Phase 1: Pre-build reasoning
            reasoning_conclusion = ""
            difficulty_target = 0.5
            player_skill = 0.5
            pacing_zone = "intro"

            if self._architect is not None and prompt:
                try:
                    from sparkai.agent.agent_cognitive_architect import (
                        ReasoningRequest, ReasoningStrategy,
                    )
                    request = ReasoningRequest(
                        task=f"Optimize game parameters for: {prompt[:100]}",
                        strategy=ReasoningStrategy.ADAPTIVE_SWITCH,
                    )
                    result = self._architect.run_reasoning(request)
                    reasoning_conclusion = result.conclusion[:200]
                except Exception as exc:
                    logger.warning("Pre-build reasoning failed: %s", exc)

            # Pull brain state for player skill and pacing
            if self._brain is not None:
                try:
                    brain_status = self._brain.status()
                    player_state = brain_status.get("player", {})
                    pacing_state = brain_status.get("pacing", {})
                    player_skill = player_state.get("skill", 0.5)
                    pacing_zone = pacing_state.get("zone", "intro")
                    # Target difficulty hovers slightly above player skill
                    difficulty_target = min(1.0, player_skill + 0.15)
                except Exception as exc:
                    logger.warning("Brain state pull failed: %s", exc)

            # Phase 2: Derive AI overrides
            genre = ""
            if gdd is not None and hasattr(gdd, "concept"):
                concept = gdd.concept
                genre = getattr(concept, "genre", "")
                if hasattr(genre, "value"):
                    genre = genre.value

            overrides = self._adapter.derive_overrides(
                prompt=prompt, genre=genre,
                player_skill=player_skill, pacing_zone=pacing_zone,
                difficulty_target=difficulty_target,
            )

            # Phase 3: Build the game using the underlying runtime
            if self._runtime is None:
                return AIRuntimeResult(
                    success=False, html="", config=None,
                    error="GameRuntime not available",
                    duration_s=round(time.time() - start, 3),
                    metadata={}, ai_session_id=ai_session_id,
                )

            runtime_result = self._runtime.build_from_gdd(gdd)
            if not runtime_result.success:
                return AIRuntimeResult(
                    success=False, html="", config=None,
                    error=runtime_result.error or "Runtime build failed",
                    duration_s=round(time.time() - start, 3),
                    metadata=runtime_result.metadata,
                    ai_session_id=ai_session_id,
                )

            # Phase 4: Apply AI overrides to the config
            config = runtime_result.config
            config = self._adapter.apply_to_config(config, overrides)

            # Phase 5: Inject AI scripts into the HTML
            html = runtime_result.html
            telemetry_header = self._telemetry.build_header_js()
            telemetry_loop = self._telemetry.build_loop_patch_js()
            adaptive_header = self._adaptive.build_header_js(difficulty_target)
            adaptive_loop = self._adaptive.build_loop_patch_js()

            # Inject before </head>
            head_injection = (
                telemetry_header + "\n" + adaptive_header
            )
            if "</head>" in html:
                html = html.replace("</head>", head_injection + "\n</head>", 1)
            else:
                html = head_injection + "\n" + html

            # Inject before </body>
            body_injection = (
                telemetry_loop + "\n" + adaptive_loop
            )
            if "</body>" in html:
                html = html.replace("</body>", body_injection + "\n</body>", 1)
            else:
                html = html + "\n" + body_injection

            duration = time.time() - start
            result = AIRuntimeResult(
                success=True,
                html=html,
                config=config,
                error=None,
                duration_s=round(duration, 3),
                metadata={
                    **runtime_result.metadata,
                    "ai_session_id": ai_session_id,
                    "ai_overrides_applied": len(overrides),
                    "ai_difficulty_target": difficulty_target,
                    "ai_player_skill": player_skill,
                    "ai_pacing_zone": pacing_zone,
                    "ai_reasoning_conclusion": reasoning_conclusion,
                },
                ai_overrides=overrides,
                ai_session_id=ai_session_id,
                ai_reasoning_conclusion=reasoning_conclusion,
            )

            with self._lock:
                self._last_result = result

            return result

        except Exception as exc:
            logger.exception("AIRuntimeBridge build failed: %s", exc)
            return AIRuntimeResult(
                success=False, html="", config=None,
                error=str(exc),
                duration_s=round(time.time() - start, 3),
                metadata={}, ai_session_id=ai_session_id,
            )

    def build_from_prompt(
        self, prompt: str, genre_hint: Optional[str] = None,
    ) -> AIRuntimeResult:
        """Build a game from a prompt with AI-driven adaptation."""
        if not self._initialized:
            self.initialize()
        start = time.time()
        ai_session_id = f"aibuild_{uuid.uuid4().hex[:10]}"

        try:
            # Synthesize content from the prompt
            from sparkai.agent.agent_game_content_synthesizer import (
                get_content_synthesizer,
            )
            synthesizer = get_content_synthesizer()
            synth_result = synthesizer.synthesize(prompt, genre_hint=genre_hint)
            if not synth_result.success or synth_result.gdd is None:
                return AIRuntimeResult(
                    success=False, html="", config=None,
                    error=synth_result.error or "Content synthesis failed",
                    duration_s=round(time.time() - start, 3),
                    metadata={"synthesis_warnings": synth_result.warnings},
                    ai_session_id=ai_session_id,
                )

            # Build with AI adaptation
            return self.build_from_gdd(synth_result.gdd, prompt=prompt)

        except Exception as exc:
            logger.exception("AIRuntimeBridge build_from_prompt failed: %s", exc)
            return AIRuntimeResult(
                success=False, html="", config=None,
                error=str(exc),
                duration_s=round(time.time() - start, 3),
                metadata={}, ai_session_id=ai_session_id,
            )

    # -----------------------------------------------------------------
    # Status and Inspection
    # -----------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "build_count": self._build_count,
                "runtime_attached": self._runtime is not None,
                "architect_attached": self._architect is not None,
                "conductor_attached": self._conductor is not None,
                "brain_attached": self._brain is not None,
                "adapter": self._adapter.stats(),
                "telemetry": self._telemetry.stats(),
                "adaptive": self._adaptive.stats(),
                "last_build": {
                    "success": self._last_result.success if self._last_result else None,
                    "ai_session_id": self._last_result.ai_session_id if self._last_result else None,
                    "ai_overrides_count": len(self._last_result.ai_overrides) if self._last_result else 0,
                    "duration_s": self._last_result.duration_s if self._last_result else 0,
                } if self._last_result else None,
            }

    def get_last_overrides(self) -> Dict[str, Any]:
        with self._lock:
            if self._last_result:
                return dict(self._last_result.ai_overrides)
            return {}

    def reset(self) -> None:
        """Reset the bridge state (preserves wiring)."""
        with self._lock:
            self._build_count = 0
            self._last_result = None


# ---------------------------------------------------------------------------
# Module-level Convenience
# ---------------------------------------------------------------------------

def get_ai_bridge() -> AIRuntimeBridge:
    return AIRuntimeBridge.get_instance()


def quick_ai_bridge_status() -> Dict[str, Any]:
    return get_ai_bridge().status()
