"""
SparkLabs - AI-Native Integration Layer

Synchronizes the cognitive architect, AI-native conductor, game brain, and
runtime bridge with the existing KernelEngineIntegrator. This layer closes
the feedback loop between high-level reasoning and live engine state:

  Engine tick -> KernelEngineIntegrator perceives state
              -> AINativeIntegration broadcasts to architect/conductor/brain
              -> CognitiveArchitect reasons and emits directives
              -> AINativeConductor adjusts physics/render/scene parameters
              -> GameBrain translates directives into player-facing decisions
              -> AIRuntimeBridge captures outcomes for the next build cycle

The integration runs on a single cadence so that cognitive, conductorial, and
directorial decisions stay coherent. Each participant exposes a uniform
``observe()`` / ``decide()`` / ``apply()`` surface so the integration layer
can drive them without knowing their internals.

Original SparkLabs design - unified AI-native synchronization substrate.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Integration Enums
# =============================================================================


class IntegrationTickPhase(Enum):
    """Phases of a single AI-native integration tick."""
    OBSERVE = "observe"       # Collect state from engine integrator
    BROADCAST = "broadcast"   # Distribute observations to participants
    REASON = "reason"         # Architect runs reasoning cycle
    CONDUCT = "conduct"       # Conductor adjusts engine subsystems
    DIRECT = "direct"         # Brain issues player-facing directives
    LEARN = "learn"           # Capture outcomes and update memory
    VERIFY = "verify"         # Sanity-check integration health


class DirectivePriority(Enum):
    """Priority levels for directives flowing through the integration."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class ObservationKind(Enum):
    """Categories of observations the integration layer routes."""
    ENGINE_STATE = "engine_state"
    PLAYER_SIGNAL = "player_signal"
    PERFORMANCE = "performance"
    NARRATIVE_BEAT = "narrative_beat"
    EMERGENCE = "emergence"
    ANOMALY = "anomaly"


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class IntegrationObservation:
    """A single observation routed through the integration layer."""
    observation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    kind: ObservationKind = ObservationKind.ENGINE_STATE
    source: str = "integration"
    payload: Dict[str, Any] = field(default_factory=dict)
    salience: float = 0.5
    timestamp: float = field(default_factory=time.time)


@dataclass
class IntegrationDirective:
    """A directive issued by a participant and routed to others."""
    directive_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    issuer: str = "architect"
    target: str = "conductor"
    kind: str = "adjust"
    priority: DirectivePriority = DirectivePriority.NORMAL
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    applied: bool = False


@dataclass
class IntegrationTickResult:
    """Outcome of a single integration tick."""
    tick: int = 0
    phase: IntegrationTickPhase = IntegrationTickPhase.OBSERVE
    observations_collected: int = 0
    directives_issued: int = 0
    directives_applied: int = 0
    architect_cycle: bool = False
    conductor_cycle: bool = False
    brain_cycle: bool = False
    duration_s: float = 0.0
    notes: List[str] = field(default_factory=list)


# =============================================================================
# Participant Adapter
# =============================================================================


class ParticipantAdapter:
    """
    Uniform adapter that lets the integration layer drive a participant
    (architect, conductor, brain, bridge) without knowing its internals.
    """

    def __init__(
        self,
        name: str,
        observe_fn: Optional[Callable[[Dict[str, Any]], None]] = None,
        decide_fn: Optional[Callable[[], Dict[str, Any]]] = None,
        apply_fn: Optional[Callable[[IntegrationDirective], bool]] = None,
    ) -> None:
        self.name = name
        self._observe_fn = observe_fn
        self._decide_fn = decide_fn
        self._apply_fn = apply_fn
        self.observations_received = 0
        self.decisions_made = 0
        self.directives_applied = 0
        self.directives_rejected = 0

    def observe(self, observation: Dict[str, Any]) -> None:
        """Push an observation to the participant."""
        if self._observe_fn is None:
            return
        try:
            self._observe_fn(observation)
            self.observations_received += 1
        except Exception as exc:
            logger.warning("Participant %s observe failed: %s", self.name, exc)

    def decide(self) -> Dict[str, Any]:
        """Ask the participant to make a decision."""
        if self._decide_fn is None:
            return {}
        try:
            result = self._decide_fn() or {}
            self.decisions_made += 1
            return result
        except Exception as exc:
            logger.warning("Participant %s decide failed: %s", self.name, exc)
            return {}

    def apply(self, directive: IntegrationDirective) -> bool:
        """Apply a directive to the participant."""
        if self._apply_fn is None:
            return False
        try:
            success = bool(self._apply_fn(directive))
            if success:
                self.directives_applied += 1
            else:
                self.directives_rejected += 1
            return success
        except Exception as exc:
            logger.warning("Participant %s apply failed: %s", self.name, exc)
            self.directives_rejected += 1
            return False

    def stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "observations_received": self.observations_received,
            "decisions_made": self.decisions_made,
            "directives_applied": self.directives_applied,
            "directives_rejected": self.directives_rejected,
        }


# =============================================================================
# Directive Router
# =============================================================================


class DirectiveRouter:
    """
    Routes directives from issuers to targets, respecting priority and
    deduplicating redundant adjustments.
    """

    def __init__(self, max_history: int = 256) -> None:
        self._lock = threading.RLock()
        self._queue: Deque[IntegrationDirective] = deque()
        self._history: Deque[IntegrationDirective] = deque(maxlen=max_history)
        self._dedupe_keys: Dict[str, float] = {}

    def submit(self, directive: IntegrationDirective) -> None:
        """Submit a directive to the routing queue."""
        with self._lock:
            # Deduplicate: skip if an identical directive was issued recently
            dedupe_key = f"{directive.issuer}:{directive.target}:{directive.kind}"
            now = time.time()
            last = self._dedupe_keys.get(dedupe_key, 0.0)
            if now - last < 0.5:
                return
            self._dedupe_keys[dedupe_key] = now
            self._queue.append(directive)

    def drain(self) -> List[IntegrationDirective]:
        """Drain the queue, returning directives sorted by priority (desc)."""
        with self._lock:
            items = list(self._queue)
            self._queue.clear()
            for d in items:
                self._history.append(d)
        # Sort by priority (highest first), then by timestamp (oldest first)
        items.sort(key=lambda d: (-d.priority.value, d.timestamp))
        return items

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "pending": len(self._queue),
                "history_size": len(self._history),
                "unique_routes": len(self._dedupe_keys),
            }


# =============================================================================
# AI-Native Integration (Singleton)
# =============================================================================


class AINativeIntegration:
    """
    Singleton integration layer that synchronizes all AI-native participants
    with the existing KernelEngineIntegrator. Each tick:

      1. Observes engine state via the integrator
      2. Broadcasts observations to architect, conductor, brain
      3. Runs architect reasoning cycle
      4. Runs conductor adjustment cycle
      5. Runs brain directive cycle
      6. Captures outcomes for learning
      7. Verifies integration health
    """

    _instance: Optional["AINativeIntegration"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tick: int = 0
        self._initialized: bool = False
        self._participants: Dict[str, ParticipantAdapter] = {}
        self._router = DirectiveRouter()
        self._observations: Deque[IntegrationObservation] = deque(maxlen=128)
        self._results_history: Deque[IntegrationTickResult] = deque(maxlen=64)
        self._last_result: Optional[IntegrationTickResult] = None
        # Outcome history for the LEARN phase (build outcomes from bridge)
        self._outcome_history: Deque[Dict[str, Any]] = deque(maxlen=32)
        self._lessons_synthesized: int = 0

        # Wiring to existing infrastructure (set during initialize)
        self._integrator: Any = None
        self._architect: Any = None
        self._conductor: Any = None
        self._brain: Any = None
        self._bridge: Any = None

    @classmethod
    def get_instance(cls) -> "AINativeIntegration":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -----------------------------------------------------------------
    # Initialization
    # -----------------------------------------------------------------

    def initialize(self) -> None:
        """Wire up all participants and connect to existing infrastructure."""
        with self._lock:
            if self._initialized:
                return

            # Connect to existing infrastructure (lazy imports to avoid cycles)
            try:
                from sparkai.engine.engine_kernel_integration import (
                    get_integrator,
                )
                self._integrator = get_integrator()
            except Exception as exc:
                logger.warning("Could not attach KernelEngineIntegrator: %s", exc)

            try:
                from sparkai.agent.agent_cognitive_architect import (
                    get_architect,
                )
                self._architect = get_architect()
            except Exception as exc:
                logger.warning("Could not attach CognitiveArchitect: %s", exc)

            try:
                from sparkai.engine.engine_ai_native_conductor import (
                    AINativeConductor,
                )
                self._conductor = AINativeConductor.get_instance()
            except Exception as exc:
                logger.warning("Could not attach AINativeConductor: %s", exc)

            try:
                from sparkai.agent.agent_game_brain import GameBrain
                self._brain = GameBrain.get_instance() if hasattr(GameBrain, "get_instance") else None
            except Exception as exc:
                logger.warning("Could not attach GameBrain: %s", exc)

            try:
                from sparkai.engine.engine_ai_runtime_bridge import (
                    AIRuntimeBridge,
                )
                self._bridge = AIRuntimeBridge.get_instance()
            except Exception as exc:
                logger.warning("Could not attach AIRuntimeBridge: %s", exc)

            # Register participants with uniform adapters
            self._participants["architect"] = ParticipantAdapter(
                name="architect",
                observe_fn=self._observe_architect,
                decide_fn=self._decide_architect,
                apply_fn=self._apply_architect,
            )
            self._participants["conductor"] = ParticipantAdapter(
                name="conductor",
                observe_fn=self._observe_conductor,
                decide_fn=self._decide_conductor,
                apply_fn=self._apply_conductor,
            )
            self._participants["brain"] = ParticipantAdapter(
                name="brain",
                observe_fn=self._observe_brain,
                decide_fn=self._decide_brain,
                apply_fn=self._apply_brain,
            )
            self._participants["bridge"] = ParticipantAdapter(
                name="bridge",
                observe_fn=self._observe_bridge,
                decide_fn=self._decide_bridge,
                apply_fn=self._apply_bridge,
            )

            self._initialized = True
            logger.info("AINativeIntegration initialized with %d participants",
                        len(self._participants))

    # -----------------------------------------------------------------
    # Participant observation adapters
    # -----------------------------------------------------------------

    def _observe_architect(self, observation: Dict[str, Any]) -> None:
        if self._architect is None:
            return
        # Feed observations as episodic entries for knowledge synthesis
        try:
            statement = observation.get("summary", str(observation)[:200])
            if not statement:
                return
            domain = observation.get("domain", "engine")
            tags = observation.get("tags", ["integration"])
            episode = {
                "id": uuid.uuid4().hex[:8],
                "summary": statement,
                "domain": domain,
                "tags": tags,
                "confidence": observation.get("confidence", 0.6),
                "content": statement,
            }
            # Architect exposes synthesize_knowledge() for episodic consolidation
            if hasattr(self._architect, "synthesize_knowledge"):
                self._architect.synthesize_knowledge([episode])
        except Exception as exc:
            logger.debug("Architect observe failed: %s", exc)

    def _observe_conductor(self, observation: Dict[str, Any]) -> None:
        if self._conductor is None:
            return
        # Feed engine state to conductor's analyzers
        try:
            if hasattr(self._conductor, "physics"):
                state = observation.get("physics", {})
                if state:
                    self._conductor.physics.observe(state)
            if hasattr(self._conductor, "render"):
                state = observation.get("render", {})
                if state:
                    self._conductor.render.observe(state)
            if hasattr(self._conductor, "scene"):
                state = observation.get("scene", {})
                if state:
                    self._conductor.scene.observe(state)
        except Exception as exc:
            logger.debug("Conductor observe failed: %s", exc)

    def _observe_brain(self, observation: Dict[str, Any]) -> None:
        if self._brain is None:
            return
        # Feed player signals to brain's modeler
        try:
            player_state = observation.get("player", {})
            if player_state and hasattr(self._brain, "player_modeler"):
                self._brain.player_modeler.observe(player_state)
        except Exception as exc:
            logger.debug("Brain observe failed: %s", exc)

    def _observe_bridge(self, observation: Dict[str, Any]) -> None:
        if self._bridge is None:
            return
        # Bridge is mostly passive during ticks; observations are logged
        pass

    # -----------------------------------------------------------------
    # Participant decision adapters
    # -----------------------------------------------------------------

    def _decide_architect(self) -> Dict[str, Any]:
        if self._architect is None:
            return {}
        try:
            decision = self._architect.cycle()
            # Convert architect decision into directives for conductor/brain
            if hasattr(decision, "directives"):
                for d in decision.directives:
                    directive = IntegrationDirective(
                        issuer="architect",
                        target=d.get("target", "conductor"),
                        kind=d.get("kind", "adjust"),
                        priority=DirectivePriority.NORMAL,
                        payload=d.get("payload", {}),
                    )
                    self._router.submit(directive)
            return {"phase": str(decision.phase), "cycle_id": decision.cycle_id}
        except Exception as exc:
            logger.warning("Architect decide failed: %s", exc)
            return {}

    def _decide_conductor(self) -> Dict[str, Any]:
        if self._conductor is None:
            return {}
        try:
            decision = self._conductor.cycle()
            # Convert conductor adjustments into directives for engine
            adjustments = []
            if hasattr(decision, "physics_adjustments"):
                adjustments.extend(decision.physics_adjustments)
            if hasattr(decision, "render_adjustments"):
                adjustments.extend(decision.render_adjustments)
            if hasattr(decision, "scene_adjustments"):
                adjustments.extend(decision.scene_adjustments)
            for adj in adjustments:
                directive = IntegrationDirective(
                    issuer="conductor",
                    target="engine",
                    kind=adj.get("kind", "adjust_parameter"),
                    priority=DirectivePriority.HIGH,
                    payload=adj,
                )
                self._router.submit(directive)
            return {"phase": str(decision.phase)}
        except Exception as exc:
            logger.warning("Conductor decide failed: %s", exc)
            return {}

    def _decide_brain(self) -> Dict[str, Any]:
        if self._brain is None:
            return {}
        try:
            # GameBrain exposes tick() rather than cycle()
            if hasattr(self._brain, "tick"):
                decision = self._brain.tick()
            elif hasattr(self._brain, "cycle"):
                decision = self._brain.cycle()
            else:
                return {}
            # Convert brain directives into conductor/engine directives
            if hasattr(decision, "directives"):
                for d in decision.directives:
                    if isinstance(d, dict):
                        directive = IntegrationDirective(
                            issuer="brain",
                            target=d.get("target", "conductor"),
                            kind=d.get("kind", "direct"),
                            priority=DirectivePriority.NORMAL,
                            payload=d.get("payload", {}),
                        )
                        self._router.submit(directive)
            return {"phase": str(decision.phase) if hasattr(decision, "phase") else "done"}
        except Exception as exc:
            logger.debug("Brain decide failed: %s", exc)
        return {}

    def _decide_bridge(self) -> Dict[str, Any]:
        # Bridge doesn't issue directives during ticks; it captures outcomes
        return {}

    # -----------------------------------------------------------------
    # Participant apply adapters
    # -----------------------------------------------------------------

    def _apply_architect(self, directive: IntegrationDirective) -> bool:
        if self._architect is None:
            return False
        try:
            # Architect exposes run_reasoning() for issuing reasoning tasks
            if hasattr(self._architect, "run_reasoning"):
                from sparkai.agent.agent_cognitive_architect import (
                    ReasoningRequest,
                )
                task = directive.payload.get("task", directive.kind)
                request = ReasoningRequest(
                    task=task,
                    context=directive.payload,
                )
                self._architect.run_reasoning(request)
                return True
        except Exception as exc:
            logger.debug("Architect apply failed: %s", exc)
        return False

    def _apply_conductor(self, directive: IntegrationDirective) -> bool:
        if self._conductor is None:
            return False
        try:
            kind = directive.kind
            if kind.startswith("physics") and hasattr(self._conductor, "physics"):
                self._conductor.physics.apply(directive.payload)
                return True
            if kind.startswith("render") and hasattr(self._conductor, "render"):
                self._conductor.render.apply(directive.payload)
                return True
            if kind.startswith("scene") and hasattr(self._conductor, "scene"):
                self._conductor.scene.apply(directive.payload)
                return True
        except Exception as exc:
            logger.debug("Conductor apply failed: %s", exc)
        return False

    def _apply_brain(self, directive: IntegrationDirective) -> bool:
        if self._brain is None:
            return False
        try:
            # Brain accepts adjustments via player_modeler.ingest() as events
            # that influence future cognitive ticks
            if hasattr(self._brain, "player_modeler"):
                event = {
                    "type": "directive",
                    "source": directive.issuer,
                    "kind": directive.kind,
                    "payload": directive.payload,
                    "timestamp": directive.timestamp,
                }
                self._brain.player_modeler.ingest(event)
                return True
        except Exception as exc:
            logger.debug("Brain apply failed: %s", exc)
        return False

    def _apply_bridge(self, directive: IntegrationDirective) -> bool:
        # Bridge doesn't accept directives during ticks
        return False

    # -----------------------------------------------------------------
    # Integration Tick
    # -----------------------------------------------------------------

    def tick(self) -> IntegrationTickResult:
        """Run a single integration tick through all phases."""
        if not self._initialized:
            self.initialize()
            if not self._initialized:
                return IntegrationTickResult()

        start = time.time()
        with self._lock:
            self._tick += 1
            tick_num = self._tick

        result = IntegrationTickResult(tick=tick_num)

        # Phase 1: OBSERVE - collect state from integrator
        result.phase = IntegrationTickPhase.OBSERVE
        observations = self._collect_observations()
        result.observations_collected = len(observations)
        for obs in observations:
            self._observations.append(obs)

        # Phase 2: BROADCAST - distribute observations to participants
        result.phase = IntegrationTickPhase.BROADCAST
        for obs in observations:
            payload = {
                "kind": obs.kind.value,
                "source": obs.source,
                "summary": obs.payload.get("summary", ""),
                "domain": obs.payload.get("domain", "engine"),
                "tags": obs.payload.get("tags", []),
                "confidence": obs.salience,
                "physics": obs.payload.get("physics", {}),
                "render": obs.payload.get("render", {}),
                "scene": obs.payload.get("scene", {}),
                "player": obs.payload.get("player", {}),
            }
            for participant in self._participants.values():
                participant.observe(payload)

        # Phase 3: REASON - architect cycle
        result.phase = IntegrationTickPhase.REASON
        arch_decision = self._participants["architect"].decide()
        result.architect_cycle = bool(arch_decision)

        # Phase 4: CONDUCT - conductor cycle
        result.phase = IntegrationTickPhase.CONDUCT
        cond_decision = self._participants["conductor"].decide()
        result.conductor_cycle = bool(cond_decision)

        # Phase 5: DIRECT - brain cycle
        result.phase = IntegrationTickPhase.DIRECT
        brain_decision = self._participants["brain"].decide()
        result.brain_cycle = bool(brain_decision)

        # Drain directive queue and apply to targets
        directives = self._router.drain()
        result.directives_issued = len(directives)
        for directive in directives:
            target = self._participants.get(directive.target)
            if target is None:
                continue
            success = target.apply(directive)
            if success:
                directive.applied = True
                result.directives_applied += 1

        # Phase 6: LEARN - capture outcomes from bridge and synthesize lessons
        result.phase = IntegrationTickPhase.LEARN
        lessons = self._capture_lessons()
        if lessons:
            result.notes.extend(lessons)
            self._lessons_synthesized += len(lessons)

        # Phase 7: VERIFY - sanity-check integration health
        result.phase = IntegrationTickPhase.VERIFY
        health = self._verify_health()
        if health.get("issues"):
            result.notes.extend(health["issues"])

        result.duration_s = time.time() - start
        with self._lock:
            self._last_result = result
            self._results_history.append(result)
        return result

    # -----------------------------------------------------------------
    # Learning (LEARN phase)
    # -----------------------------------------------------------------

    def _capture_lessons(self) -> List[str]:
        """
        Capture outcomes from the runtime bridge and synthesize lessons
        that feed back into the architect's knowledge base. This closes
        the feedback loop: build outcomes inform future reasoning.
        """
        lessons: List[str] = []
        if self._bridge is None:
            return lessons

        try:
            bridge_status = self._bridge.status()
            last_build = bridge_status.get("last_build")
            if not last_build:
                return lessons

            # Only learn from builds we haven't recorded yet
            build_signature = (
                last_build.get("ai_session_id"),
                last_build.get("duration_s"),
            )
            if self._outcome_history:
                last_recorded = self._outcome_history[-1]
                last_sig = (
                    last_recorded.get("ai_session_id"),
                    last_recorded.get("duration_s"),
                )
                if build_signature == last_sig:
                    return lessons  # Already captured this build

            outcome = {
                "ai_session_id": last_build.get("ai_session_id"),
                "success": bool(last_build.get("success")),
                "duration_s": last_build.get("duration_s", 0),
                "overrides_count": last_build.get("ai_overrides_count", 0),
                "captured_at": time.time(),
            }
            self._outcome_history.append(outcome)

            # Synthesize a lesson statement for the architect
            success_str = "succeeded" if outcome["success"] else "failed"
            lesson = (
                f"Build {success_str} with {outcome['overrides_count']} "
                f"AI overrides in {outcome['duration_s']:.2f}s"
            )
            lessons.append(lesson)

            # Feed the lesson back to the architect as an episode
            if self._architect is not None and hasattr(
                self._architect, "synthesize_knowledge"
            ):
                episode = {
                    "id": uuid.uuid4().hex[:8],
                    "summary": lesson,
                    "domain": "build_outcome",
                    "tags": ["learning", "bridge", success_str],
                    "confidence": 0.8 if outcome["success"] else 0.5,
                    "content": lesson,
                }
                self._architect.synthesize_knowledge([episode])

            # Compute trend note if we have enough history
            if len(self._outcome_history) >= 3:
                recent = list(self._outcome_history)[-5:]
                success_rate = sum(
                    1 for o in recent if o["success"]
                ) / len(recent)
                avg_duration = sum(o["duration_s"] for o in recent) / len(recent)
                trend = (
                    f"Recent trend: {success_rate*100:.0f}% success, "
                    f"avg {avg_duration:.2f}s"
                )
                lessons.append(trend)

        except Exception as exc:
            logger.debug("Lesson capture failed: %s", exc)

        return lessons

    def learning_stats(self) -> Dict[str, Any]:
        """Return learning metrics from the LEARN phase."""
        with self._lock:
            outcomes = list(self._outcome_history)
            if not outcomes:
                return {
                    "outcomes_recorded": 0,
                    "lessons_synthesized": self._lessons_synthesized,
                    "success_rate": 0.0,
                    "avg_duration_s": 0.0,
                }
            success_count = sum(1 for o in outcomes if o["success"])
            return {
                "outcomes_recorded": len(outcomes),
                "lessons_synthesized": self._lessons_synthesized,
                "success_rate": success_count / len(outcomes),
                "avg_duration_s": sum(
                    o["duration_s"] for o in outcomes
                ) / len(outcomes),
                "last_outcome": outcomes[-1] if outcomes else None,
            }

    # -----------------------------------------------------------------
    # Observation Collection
    # -----------------------------------------------------------------

    def _collect_observations(self) -> List[IntegrationObservation]:
        """Collect observations from the KernelEngineIntegrator."""
        observations: List[IntegrationObservation] = []
        if self._integrator is None:
            return observations
        try:
            status = self._integrator.status()
            snapshot = status.get("latest_snapshot")
            if snapshot:
                observations.append(IntegrationObservation(
                    kind=ObservationKind.ENGINE_STATE,
                    source="integrator",
                    payload={
                        "summary": f"tick={status.get('tick', 0)} "
                                   f"commands={status.get('dispatched_commands', 0)}",
                        "domain": "engine",
                        "tags": ["tick", "state"],
                        "physics": self._extract_physics(snapshot),
                        "render": self._extract_render(snapshot),
                        "scene": self._extract_scene(snapshot),
                        "player": self._extract_player(snapshot),
                    },
                    salience=0.6,
                ))
        except Exception as exc:
            logger.debug("Observation collection failed: %s", exc)
        return observations

    def _extract_physics(self, snapshot: Any) -> Dict[str, Any]:
        if isinstance(snapshot, dict):
            return {
                k: v for k, v in snapshot.items()
                if k in ("body_count", "collision_count", "penetration_count",
                         "stability_score", "gravity", "damping")
            }
        return {}

    def _extract_render(self, snapshot: Any) -> Dict[str, Any]:
        if isinstance(snapshot, dict):
            return {
                k: v for k, v in snapshot.items()
                if k in ("fps", "gpu_load", "draw_calls", "quality_level")
            }
        return {}

    def _extract_scene(self, snapshot: Any) -> Dict[str, Any]:
        if isinstance(snapshot, dict):
            return {
                k: v for k, v in snapshot.items()
                if k in ("entity_count", "max_entities", "active_scene",
                         "narrative_beat", "pacing_zone")
            }
        return {}

    def _extract_player(self, snapshot: Any) -> Dict[str, Any]:
        if isinstance(snapshot, dict):
            return {
                k: v for k, v in snapshot.items()
                if k in ("player_skill", "player_mood", "player_health",
                         "player_progress", "player_engagement")
            }
        return {}

    # -----------------------------------------------------------------
    # Health Verification
    # -----------------------------------------------------------------

    def _verify_health(self) -> Dict[str, Any]:
        issues: List[str] = []
        for name, p in self._participants.items():
            stats = p.stats()
            if stats["directives_rejected"] > 10:
                issues.append(
                    f"Participant {name} rejected "
                    f"{stats['directives_rejected']} directives"
                )
        return {"issues": issues, "healthy": len(issues) == 0}

    # -----------------------------------------------------------------
    # Status and Inspection
    # -----------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "tick": self._tick,
                "integrator_attached": self._integrator is not None,
                "architect_attached": self._architect is not None,
                "conductor_attached": self._conductor is not None,
                "brain_attached": self._brain is not None,
                "bridge_attached": self._bridge is not None,
                "participants": {
                    name: p.stats() for name, p in self._participants.items()
                },
                "router": self._router.stats(),
                "observations_buffered": len(self._observations),
                "learning": self.learning_stats(),
                "last_tick": {
                    "tick": self._last_result.tick if self._last_result else 0,
                    "phase": self._last_result.phase.value if self._last_result else None,
                    "observations": self._last_result.observations_collected if self._last_result else 0,
                    "directives_issued": self._last_result.directives_issued if self._last_result else 0,
                    "directives_applied": self._last_result.directives_applied if self._last_result else 0,
                    "architect_cycle": self._last_result.architect_cycle if self._last_result else False,
                    "conductor_cycle": self._last_result.conductor_cycle if self._last_result else False,
                    "brain_cycle": self._last_result.brain_cycle if self._last_result else False,
                    "duration_s": self._last_result.duration_s if self._last_result else 0,
                } if self._last_result else None,
            }

    def history(self, limit: int = 16) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._results_history)[-limit:]
        return [
            {
                "tick": r.tick,
                "phase": r.phase.value,
                "observations": r.observations_collected,
                "directives_issued": r.directives_issued,
                "directives_applied": r.directives_applied,
                "architect_cycle": r.architect_cycle,
                "conductor_cycle": r.conductor_cycle,
                "brain_cycle": r.brain_cycle,
                "duration_s": r.duration_s,
                "notes": r.notes,
            }
            for r in items
        ]

    def reset(self) -> None:
        """Reset integration state (preserves wiring)."""
        with self._lock:
            self._tick = 0
            self._observations.clear()
            self._results_history.clear()
            self._last_result = None
            self._outcome_history.clear()
            self._lessons_synthesized = 0
            for p in self._participants.values():
                p.observations_received = 0
                p.decisions_made = 0
                p.directives_applied = 0
                p.directives_rejected = 0


# =============================================================================
# Module-level Convenience
# =============================================================================


def get_integration() -> AINativeIntegration:
    """Return the singleton AINativeIntegration instance."""
    return AINativeIntegration.get_instance()


def quick_integration_status() -> Dict[str, Any]:
    """Return a quick status snapshot of the AI-native integration."""
    return get_integration().status()


def run_integration_tick() -> Dict[str, Any]:
    """Run a single integration tick and return the result as a dict."""
    result = get_integration().tick()
    return {
        "tick": result.tick,
        "phase": result.phase.value,
        "observations_collected": result.observations_collected,
        "directives_issued": result.directives_issued,
        "directives_applied": result.directives_applied,
        "architect_cycle": result.architect_cycle,
        "conductor_cycle": result.conductor_cycle,
        "brain_cycle": result.brain_cycle,
        "duration_s": result.duration_s,
        "notes": result.notes,
    }
