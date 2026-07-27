"""
SparkLabs Engine - Predictive State Prefetcher

The EnginePredictiveStatePrefetcher uses AI prediction to drive engine
resource management. By analyzing player behavior patterns, narrative
trajectory, and agent decisions, it predicts what will happen in the next
5-30 seconds and pre-loads/pre-computes the necessary resources.

This eliminates loading screens and frame hitches in an AI-native way:
the engine anticipates needs before they arise.

Architecture:
  OBSERVE  ->  PREDICT  ->  PREFETCH  ->  VERIFY  ->  ADAPT
  (collect      (forecast    (pre-load      (check if      (learn from
   player and    future       assets,        predictions    prediction
   world state)  states)      warm shaders,  were accurate)  outcomes)
                            generate paths)

The prefetcher manages:
  - Player trajectory prediction (next positions, likely destinations)
  - Action prediction (combat, dialogue, exploration transitions)
  - Scene transition prediction (which areas will be entered)
  - Asset prefetching (textures, models, audio, scripts)
  - Shader pre-warming (compile shaders before they're needed)
  - Path pre-computation (NPC navigation paths)
  - Prediction accuracy tracking and adaptive learning

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class PrefetchPhase(Enum):
    """Phases of the predictive prefetcher cycle."""
    OBSERVE = "observe"
    PREDICT = "predict"
    PREFETCH = "prefetch"
    VERIFY = "verify"
    ADAPT = "adapt"


class PredictionType(Enum):
    """Types of predictions the prefetcher makes."""
    PLAYER_MOVEMENT = "player_movement"
    SCENE_TRANSITION = "scene_transition"
    COMBAT_ENCOUNTER = "combat_encounter"
    DIALOGUE_TRIGGER = "dialogue_trigger"
    ASSET_REQUEST = "asset_request"
    SHADER_COMPILE = "shader_compile"
    PATH_COMPUTE = "path_compute"
    AUDIO_LOAD = "audio_load"


class PrefetchStatus(Enum):
    """Status of a prefetch request."""
    PENDING = "pending"
    LOADING = "loading"
    READY = "ready"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PlayerActivity(Enum):
    """Current player activity classification."""
    IDLE = "idle"
    EXPLORING = "exploring"
    COMBAT = "combat"
    DIALOGUE = "dialogue"
    INVENTORY = "inventory"
    TRAVELING = "traveling"
    PUZZLE = "puzzle"
    CUTSCENE = "cutscene"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PlayerSnapshot:
    """A snapshot of player state at a point in time."""
    timestamp: float
    position: Tuple[float, float, float]
    velocity: Tuple[float, float, float]
    activity: PlayerActivity
    facing: float = 0.0  # yaw angle in radians
    health_pct: float = 1.0
    target_entity: Optional[str] = None


@dataclass
class Prediction:
    """A prediction about a future game state."""
    prediction_id: str
    prediction_type: PredictionType
    confidence: float
    predicted_time: float  # when this is expected to happen
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    verified: bool = False
    hit: Optional[bool] = None  # None = not yet verified, True = correct, False = wrong


@dataclass
class PrefetchRequest:
    """A request to prefetch a resource."""
    request_id: str
    resource_type: str  # asset, shader, path, audio, script
    resource_id: str
    priority: int  # 0 = highest
    status: PrefetchStatus = PrefetchStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    prediction_id: Optional[str] = None
    size_kb: float = 0.0


@dataclass
class PrefetcherStats:
    """Statistics for the predictive prefetcher."""
    total_observations: int = 0
    total_predictions: int = 0
    total_prefetches: int = 0
    total_hits: int = 0
    total_misses: int = 0
    total_expired: int = 0
    total_cancelled: int = 0
    total_data_prefetched_kb: float = 0.0
    avg_confidence: float = 0.0
    hit_rate: float = 0.0
    prediction_accuracy: float = 0.0
    prefetch_efficiency: float = 0.0
    activity_distribution: Dict[str, int] = field(default_factory=dict)
    prediction_type_distribution: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# EnginePredictiveStatePrefetcher
# =============================================================================

class EnginePredictiveStatePrefetcher:
    """AI-driven predictive state prefetcher for the game engine.

    Predicts future game states and pre-loads resources to eliminate
    loading screens and frame hitches.
    """

    _instance: Optional["EnginePredictiveStatePrefetcher"] = None
    _instance_lock = threading.Lock()

    # Number of player snapshots to keep for trajectory analysis
    HISTORY_SIZE = 60
    # Prediction horizon in seconds
    PREDICTION_HORIZON_S = 15.0
    # Prefetch expiry time
    PREFETCH_EXPIRY_S = 30.0
    # Minimum confidence to issue a prefetch
    MIN_CONFIDENCE = 0.3

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._player_history: Deque[PlayerSnapshot] = deque(maxlen=self.HISTORY_SIZE)
        self._predictions: Dict[str, Prediction] = {}
        self._prefetch_queue: Dict[str, PrefetchRequest] = {}
        self._completed_prefetches: Deque[PrefetchRequest] = deque(maxlen=100)
        self._cycle_count = 0
        self._stats = PrefetcherStats()
        self._active = False
        self._current_activity = PlayerActivity.IDLE
        self._velocity_model: List[Tuple[float, float, float]] = []  # recent velocities for trend
        logger.info("EnginePredictiveStatePrefetcher initialized")

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EnginePredictiveStatePrefetcher":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Observation
    # -------------------------------------------------------------------------

    def observe(
        self,
        position: Tuple[float, float, float],
        velocity: Tuple[float, float, float],
        activity: str,
        facing: float = 0.0,
        health_pct: float = 1.0,
        target_entity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a player state observation."""
        with self._lock:
            act = self._resolve_activity(activity)
            snapshot = PlayerSnapshot(
                timestamp=time.time(),
                position=position,
                velocity=velocity,
                activity=act,
                facing=facing,
                health_pct=max(0.0, min(1.0, health_pct)),
                target_entity=target_entity,
            )
            self._player_history.append(snapshot)
            self._current_activity = act
            self._velocity_model.append(velocity)
            if len(self._velocity_model) > 10:
                self._velocity_model.pop(0)
            self._stats.total_observations += 1
            self._update_activity_distribution(act)
            return {
                "observed": True,
                "activity": act.value,
                "observation_count": len(self._player_history),
            }

    # -------------------------------------------------------------------------
    # Prediction
    # -------------------------------------------------------------------------

    def predict(self) -> Dict[str, Any]:
        """Generate predictions about future game states."""
        with self._lock:
            predictions: List[Prediction] = []

            if len(self._player_history) < 3:
                return {
                    "predictions_made": 0,
                    "reason": "insufficient_observations",
                    "predictions": [],
                }

            # Predict player movement
            move_pred = self._predict_movement()
            if move_pred:
                predictions.append(move_pred)

            # Predict scene transition (if traveling toward a boundary)
            scene_pred = self._predict_scene_transition()
            if scene_pred:
                predictions.append(scene_pred)

            # Predict combat encounter (if health dropping or near enemies)
            combat_pred = self._predict_combat()
            if combat_pred:
                predictions.append(combat_pred)

            # Predict dialogue (if near NPC and slowing down)
            dialogue_pred = self._predict_dialogue()
            if dialogue_pred:
                predictions.append(dialogue_pred)

            # Predict asset request (based on movement direction)
            asset_pred = self._predict_asset_request()
            if asset_pred:
                predictions.append(asset_pred)

            # Predict shader compile (based on scene type)
            shader_pred = self._predict_shader_compile()
            if shader_pred:
                predictions.append(shader_pred)

            # Predict path computation (for NPCs)
            path_pred = self._predict_path_compute()
            if path_pred:
                predictions.append(path_pred)

            # Predict audio load
            audio_pred = self._predict_audio_load()
            if audio_pred:
                predictions.append(audio_pred)

            # Store predictions
            now = time.time()
            for pred in predictions:
                self._predictions[pred.prediction_id] = pred
                self._stats.total_predictions += 1
                self._update_prediction_type_distribution(pred.prediction_type)
                # Update average confidence
                n = self._stats.total_predictions
                self._stats.avg_confidence = round(
                    (self._stats.avg_confidence * (n - 1) + pred.confidence) / n, 3
                )

            return {
                "predictions_made": len(predictions),
                "predictions": [self._prediction_to_dict(p) for p in predictions],
                "avg_confidence": round(
                    sum(p.confidence for p in predictions) / max(1, len(predictions)), 3
                ),
            }

    # -------------------------------------------------------------------------
    # Prefetch
    # -------------------------------------------------------------------------

    def prefetch(self) -> Dict[str, Any]:
        """Execute prefetch requests for high-confidence predictions."""
        with self._lock:
            now = time.time()
            requests: List[PrefetchRequest] = []

            for pred in list(self._predictions.values()):
                # Skip low-confidence predictions
                if pred.confidence < self.MIN_CONFIDENCE:
                    continue
                # Skip already-verified predictions
                if pred.verified:
                    continue
                # Skip predictions that are too old
                if now - pred.created_at > self.PREFETCH_EXPIRY_S:
                    pred.hit = False
                    pred.verified = True
                    self._stats.total_expired += 1
                    continue

                # Generate prefetch requests based on prediction type
                req = self._create_prefetch_request(pred)
                if req:
                    self._prefetch_queue[req.request_id] = req
                    requests.append(req)
                    self._stats.total_prefetches += 1
                    self._stats.total_data_prefetched_kb += req.size_kb

            # Simulate loading (mark as ready)
            for req in requests:
                req.status = PrefetchStatus.LOADING
                # Simulate async load completion
                req.status = PrefetchStatus.READY
                req.completed_at = time.time()
                self._completed_prefetches.append(req)

            return {
                "prefetches_issued": len(requests),
                "total_active": len(self._prefetch_queue),
                "total_data_kb": round(self._stats.total_data_prefetched_kb, 1),
                "requests": [self._prefetch_to_dict(r) for r in requests],
            }

    def cancel_prefetch(self, request_id: str) -> bool:
        """Cancel a pending prefetch request."""
        with self._lock:
            if request_id in self._prefetch_queue:
                req = self._prefetch_queue[request_id]
                if req.status in (PrefetchStatus.PENDING, PrefetchStatus.LOADING):
                    req.status = PrefetchStatus.CANCELLED
                    self._stats.total_cancelled += 1
                    return True
            return False

    # -------------------------------------------------------------------------
    # Verification and Adaptation
    # -------------------------------------------------------------------------

    def verify(self) -> Dict[str, Any]:
        """Verify which predictions were accurate and update stats."""
        with self._lock:
            now = time.time()
            verified_count = 0
            hits = 0
            misses = 0

            for pred in list(self._predictions.values()):
                if pred.verified:
                    continue
                # Check if prediction time has passed
                if now >= pred.predicted_time:
                    pred.verified = True
                    verified_count += 1
                    # Simulate verification (in real engine, check actual state)
                    # For simulation: predictions with confidence > 0.5 are "hits"
                    if pred.confidence > 0.5:
                        pred.hit = True
                        hits += 1
                        self._stats.total_hits += 1
                    else:
                        pred.hit = False
                        misses += 1
                        self._stats.total_misses += 1

            # Update rates
            total_verified = self._stats.total_hits + self._stats.total_misses
            if total_verified > 0:
                self._stats.prediction_accuracy = round(
                    self._stats.total_hits / total_verified, 3
                )
            if self._stats.total_prefetches > 0:
                self._stats.hit_rate = round(
                    self._stats.total_hits / max(1, self._stats.total_prefetches), 3
                )
                self._stats.prefetch_efficiency = round(
                    self._stats.total_hits / max(1, self._stats.total_prefetches), 3
                )

            return {
                "verified": verified_count,
                "hits": hits,
                "misses": misses,
                "prediction_accuracy": self._stats.prediction_accuracy,
                "hit_rate": self._stats.hit_rate,
            }

    def adapt(self) -> Dict[str, Any]:
        """Adapt prediction models based on verification results."""
        with self._lock:
            # Adjust minimum confidence threshold based on accuracy
            accuracy = self._stats.prediction_accuracy
            if accuracy > 0.8:
                self.MIN_CONFIDENCE = max(0.2, self.MIN_CONFIDENCE - 0.02)
            elif accuracy < 0.4 and self.MIN_CONFIDENCE < 0.6:
                self.MIN_CONFIDENCE = min(0.6, self.MIN_CONFIDENCE + 0.02)

            # Clean up old predictions
            now = time.time()
            expired_ids = [
                pid for pid, pred in self._predictions.items()
                if pred.verified and now - pred.predicted_time > 60
            ]
            for pid in expired_ids:
                del self._predictions[pid]

            return {
                "min_confidence": self.MIN_CONFIDENCE,
                "cleaned_predictions": len(expired_ids),
                "active_predictions": len(self._predictions),
                "adaptation": "confidence_threshold_adjusted" if expired_ids else "no_change",
            }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single prefetcher cycle.

        Phases: OBSERVE -> PREDICT -> PREFETCH -> VERIFY -> ADAPT
        """
        start_time = time.time()
        with self._lock:
            self._active = True
            phase = PrefetchPhase.OBSERVE

            # Phase 1: OBSERVE - already collecting via observe()
            obs_count = len(self._player_history)

            # Phase 2: PREDICT
            phase = PrefetchPhase.PREDICT
            pred_result = self.predict()

            # Phase 3: PREFETCH
            phase = PrefetchPhase.PREFETCH
            pf_result = self.prefetch()

            # Phase 4: VERIFY
            phase = PrefetchPhase.VERIFY
            ver_result = self.verify()

            # Phase 5: ADAPT
            phase = PrefetchPhase.ADAPT
            adapt_result = self.adapt()

            elapsed_ms = (time.time() - start_time) * 1000
            self._cycle_count += 1
            self._stats.total_observations = obs_count

            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "observations": obs_count,
                "predictions_made": pred_result.get("predictions_made", 0),
                "prefetches_issued": pf_result.get("prefetches_issued", 0),
                "verified": ver_result.get("verified", 0),
                "prediction_accuracy": ver_result.get("prediction_accuracy", 0),
                "hit_rate": ver_result.get("hit_rate", 0),
                "min_confidence": adapt_result.get("min_confidence", self.MIN_CONFIDENCE),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles with simulated player behavior."""
        with self._lock:
            import random

            initial_predictions = self._stats.total_predictions
            initial_prefetches = self._stats.total_prefetches

            # Simulated player trajectory
            pos = [0.0, 0.0, 0.0]
            vel = [1.0, 0.0, 0.0]
            activities = list(PlayerActivity)

            for c in range(cycles):
                # Simulate player movement
                pos[0] += vel[0]
                pos[1] += vel[1]
                pos[2] += vel[2]

                # Occasionally change direction
                if random.random() < 0.3:
                    vel[0] = round(random.uniform(-2, 2), 1)
                    vel[1] = round(random.uniform(-2, 2), 1)
                    vel[2] = round(random.uniform(-1, 1), 1)

                # Observe
                self.observe(
                    position=(round(pos[0], 1), round(pos[1], 1), round(pos[2], 1)),
                    velocity=(vel[0], vel[1], vel[2]),
                    activity=random.choice(activities).value,
                    facing=random.uniform(0, 6.28),
                    health_pct=random.uniform(0.3, 1.0),
                    target_entity=f"npc_{random.randint(1, 5)}" if random.random() < 0.3 else None,
                )

                # Run cycle
                self.run_cycle()

            return {
                "cycles_run": cycles,
                "predictions_made": self._stats.total_predictions - initial_predictions,
                "prefetches_issued": self._stats.total_prefetches - initial_prefetches,
                "prediction_accuracy": self._stats.prediction_accuracy,
                "hit_rate": self._stats.hit_rate,
                "total_data_kb": round(self._stats.total_data_prefetched_kb, 1),
            }

    # -------------------------------------------------------------------------
    # Status and Accessors
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the predictive prefetcher."""
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "current_activity": self._current_activity.value,
                "observation_count": len(self._player_history),
                "active_predictions": len(self._predictions),
                "active_prefetches": sum(
                    1 for r in self._prefetch_queue.values()
                    if r.status in (PrefetchStatus.PENDING, PrefetchStatus.LOADING)
                ),
                "min_confidence": self.MIN_CONFIDENCE,
                "stats": {
                    "total_observations": self._stats.total_observations,
                    "total_predictions": self._stats.total_predictions,
                    "total_prefetches": self._stats.total_prefetches,
                    "total_hits": self._stats.total_hits,
                    "total_misses": self._stats.total_misses,
                    "total_expired": self._stats.total_expired,
                    "total_cancelled": self._stats.total_cancelled,
                    "total_data_prefetched_kb": round(self._stats.total_data_prefetched_kb, 1),
                    "avg_confidence": self._stats.avg_confidence,
                    "hit_rate": self._stats.hit_rate,
                    "prediction_accuracy": self._stats.prediction_accuracy,
                    "prefetch_efficiency": self._stats.prefetch_efficiency,
                    "activity_distribution": dict(self._stats.activity_distribution),
                    "prediction_type_distribution": dict(self._stats.prediction_type_distribution),
                },
            }

    def get_predictions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent predictions."""
        with self._lock:
            preds = sorted(
                self._predictions.values(),
                key=lambda p: p.created_at,
                reverse=True,
            )[:limit]
            return [self._prediction_to_dict(p) for p in preds]

    def get_prefetches(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent prefetch requests."""
        with self._lock:
            reqs = list(self._completed_prefetches)[-limit:]
            return [self._prefetch_to_dict(r) for r in reversed(reqs)]

    def get_player_trajectory(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Get recent player trajectory snapshots."""
        with self._lock:
            snaps = list(self._player_history)[-limit:]
            return [
                {
                    "timestamp": s.timestamp,
                    "position": list(s.position),
                    "velocity": list(s.velocity),
                    "activity": s.activity.value,
                    "facing": round(s.facing, 3),
                    "health_pct": round(s.health_pct, 2),
                    "target_entity": s.target_entity,
                }
                for s in snaps
            ]

    def reset(self) -> Dict[str, Any]:
        """Reset the prefetcher to initial state."""
        with self._lock:
            self._player_history.clear()
            self._predictions.clear()
            self._prefetch_queue.clear()
            self._completed_prefetches.clear()
            self._velocity_model.clear()
            self._cycle_count = 0
            self._stats = PrefetcherStats()
            self._active = False
            self._current_activity = PlayerActivity.IDLE
            self.MIN_CONFIDENCE = 0.3
            logger.info("EnginePredictiveStatePrefetcher reset")
            return {"reset": True, "message": "Predictive state prefetcher reset"}

    # -------------------------------------------------------------------------
    # Internal Prediction Helpers
    # -------------------------------------------------------------------------

    def _predict_movement(self) -> Optional[Prediction]:
        """Predict future player position based on velocity trend."""
        if len(self._velocity_model) < 2:
            return None
        latest = self._player_history[-1]
        # Average recent velocity
        avg_vx = sum(v[0] for v in self._velocity_model) / len(self._velocity_model)
        avg_vy = sum(v[1] for v in self._velocity_model) / len(self._velocity_model)
        avg_vz = sum(v[2] for v in self._velocity_model) / len(self._velocity_model)
        speed = math.sqrt(avg_vx ** 2 + avg_vy ** 2 + avg_vz ** 2)
        if speed < 0.1:
            return None
        # Predict position in 5 seconds
        future_pos = (
            round(latest.position[0] + avg_vx * 5, 1),
            round(latest.position[1] + avg_vy * 5, 1),
            round(latest.position[2] + avg_vz * 5, 1),
        )
        confidence = min(0.9, 0.4 + speed * 0.1)
        return Prediction(
            prediction_id=f"pred_move_{int(time.time() * 1000)}",
            prediction_type=PredictionType.PLAYER_MOVEMENT,
            confidence=round(confidence, 3),
            predicted_time=time.time() + 5.0,
            details={
                "predicted_position": list(future_pos),
                "velocity": [round(avg_vx, 2), round(avg_vy, 2), round(avg_vz, 2)],
                "speed": round(speed, 2),
            },
        )

    def _predict_scene_transition(self) -> Optional[Prediction]:
        """Predict scene transition based on movement toward boundaries."""
        if len(self._player_history) < 5:
            return None
        latest = self._player_history[-1]
        # If player is near a boundary (simulated: distance from origin > 40)
        dist = math.sqrt(sum(c ** 2 for c in latest.position))
        if dist > 40:
            return Prediction(
                prediction_id=f"pred_scene_{int(time.time() * 1000)}",
                prediction_type=PredictionType.SCENE_TRANSITION,
                confidence=round(min(0.85, 0.3 + (dist - 40) * 0.02), 3),
                predicted_time=time.time() + 8.0,
                details={
                    "current_distance": round(dist, 1),
                    "predicted_scene": f"scene_{int(latest.position[0] // 50)}_{int(latest.position[1] // 50)}",
                },
            )
        return None

    def _predict_combat(self) -> Optional[Prediction]:
        """Predict combat encounter based on health and target."""
        latest = self._player_history[-1]
        if latest.health_pct < 0.5 or latest.target_entity:
            confidence = 0.6 if latest.target_entity else 0.4
            return Prediction(
                prediction_id=f"pred_combat_{int(time.time() * 1000)}",
                prediction_type=PredictionType.COMBAT_ENCOUNTER,
                confidence=confidence,
                predicted_time=time.time() + 3.0,
                details={
                    "target": latest.target_entity or "unknown",
                    "health_pct": round(latest.health_pct, 2),
                },
            )
        return None

    def _predict_dialogue(self) -> Optional[Prediction]:
        """Predict dialogue trigger based on slowing near NPCs."""
        if len(self._velocity_model) < 3:
            return None
        latest = self._player_history[-1]
        avg_speed = sum(
            math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
            for v in self._velocity_model
        ) / len(self._velocity_model)
        if avg_speed < 1.0 and latest.target_entity:
            return Prediction(
                prediction_id=f"pred_dialogue_{int(time.time() * 1000)}",
                prediction_type=PredictionType.DIALOGUE_TRIGGER,
                confidence=0.55,
                predicted_time=time.time() + 4.0,
                details={
                    "target_npc": latest.target_entity,
                    "avg_speed": round(avg_speed, 2),
                },
            )
        return None

    def _predict_asset_request(self) -> Optional[Prediction]:
        """Predict asset requests based on movement direction."""
        if len(self._velocity_model) < 2:
            return None
        latest = self._player_history[-1]
        avg_vx = sum(v[0] for v in self._velocity_model) / len(self._velocity_model)
        avg_vy = sum(v[1] for v in self._velocity_model) / len(self._velocity_model)
        speed = math.sqrt(avg_vx ** 2 + avg_vy ** 2)
        if speed < 0.5:
            return None
        # Predict which chunk assets will be needed
        chunk_x = int((latest.position[0] + avg_vx * 10) // 20)
        chunk_y = int((latest.position[1] + avg_vy * 10) // 20)
        return Prediction(
            prediction_id=f"pred_asset_{int(time.time() * 1000)}",
            prediction_type=PredictionType.ASSET_REQUEST,
            confidence=round(min(0.8, 0.4 + speed * 0.08), 3),
            predicted_time=time.time() + 6.0,
            details={
                "chunk": f"chunk_{chunk_x}_{chunk_y}",
                "asset_type": "environment",
            },
        )

    def _predict_shader_compile(self) -> Optional[Prediction]:
        """Predict shader compilation needs based on scene type."""
        latest = self._player_history[-1]
        if latest.activity in (PlayerActivity.COMBAT, PlayerActivity.CUTSCENE):
            return Prediction(
                prediction_id=f"pred_shader_{int(time.time() * 1000)}",
                prediction_type=PredictionType.SHADER_COMPILE,
                confidence=0.5,
                predicted_time=time.time() + 2.0,
                details={
                    "shader_type": "post_fx" if latest.activity == PlayerActivity.CUTSCENE else "particle",
                    "trigger_activity": latest.activity.value,
                },
            )
        return None

    def _predict_path_compute(self) -> Optional[Prediction]:
        """Predict NPC path computation needs."""
        latest = self._player_history[-1]
        if latest.activity == PlayerActivity.COMBAT and latest.target_entity:
            return Prediction(
                prediction_id=f"pred_path_{int(time.time() * 1000)}",
                prediction_type=PredictionType.PATH_COMPUTE,
                confidence=0.65,
                predicted_time=time.time() + 1.5,
                details={
                    "npc_id": latest.target_entity,
                    "path_type": "flank",
                },
            )
        return None

    def _predict_audio_load(self) -> Optional[Prediction]:
        """Predict audio loading needs based on activity."""
        latest = self._player_history[-1]
        audio_map = {
            PlayerActivity.COMBAT: "combat_music",
            PlayerActivity.DIALOGUE: "dialogue_voices",
            PlayerActivity.CUTSCENE: "cutscene_score",
            PlayerActivity.PUZZLE: "ambient_puzzle",
        }
        audio = audio_map.get(latest.activity)
        if audio:
            return Prediction(
                prediction_id=f"pred_audio_{int(time.time() * 1000)}",
                prediction_type=PredictionType.AUDIO_LOAD,
                confidence=0.6,
                predicted_time=time.time() + 3.0,
                details={
                    "audio_id": audio,
                    "trigger_activity": latest.activity.value,
                },
            )
        return None

    def _create_prefetch_request(self, pred: Prediction) -> Optional[PrefetchRequest]:
        """Create a prefetch request from a prediction."""
        resource_map = {
            PredictionType.PLAYER_MOVEMENT: ("path", f"path_{pred.details.get('predicted_position', [0,0,0])}"),
            PredictionType.SCENE_TRANSITION: ("asset", pred.details.get("predicted_scene", "unknown")),
            PredictionType.COMBAT_ENCOUNTER: ("asset", f"combat_{pred.details.get('target', 'generic')}"),
            PredictionType.DIALOGUE_TRIGGER: ("script", f"dialogue_{pred.details.get('target_npc', 'npc')}"),
            PredictionType.ASSET_REQUEST: ("asset", pred.details.get("chunk", "chunk_0_0")),
            PredictionType.SHADER_COMPILE: ("shader", pred.details.get("shader_type", "generic")),
            PredictionType.PATH_COMPUTE: ("path", f"npc_path_{pred.details.get('npc_id', 'npc')}"),
            PredictionType.AUDIO_LOAD: ("audio", pred.details.get("audio_id", "ambient")),
        }
        rtype, rid = resource_map.get(pred.prediction_type, ("asset", "unknown"))
        size_map = {"asset": 512.0, "shader": 128.0, "path": 32.0, "audio": 256.0, "script": 64.0}
        return PrefetchRequest(
            request_id=f"pf_{int(time.time() * 1000)}_{pred.prediction_id[-4:]}",
            resource_type=rtype,
            resource_id=rid,
            priority=int((1.0 - pred.confidence) * 10),
            status=PrefetchStatus.PENDING,
            prediction_id=pred.prediction_id,
            size_kb=size_map.get(rtype, 100.0),
        )

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _resolve_activity(self, activity: str) -> PlayerActivity:
        """Resolve a string to a PlayerActivity (case-insensitive)."""
        for act in PlayerActivity:
            if act.value == activity.lower() or act.name.lower() == activity.lower():
                return act
        return PlayerActivity.IDLE

    def _update_activity_distribution(self, activity: PlayerActivity) -> None:
        """Update the activity distribution stats."""
        dist = self._stats.activity_distribution
        dist[activity.value] = dist.get(activity.value, 0) + 1

    def _update_prediction_type_distribution(self, ptype: PredictionType) -> None:
        """Update the prediction type distribution stats."""
        dist = self._stats.prediction_type_distribution
        dist[ptype.value] = dist.get(ptype.value, 0) + 1

    def _prediction_to_dict(self, pred: Prediction) -> Dict[str, Any]:
        """Convert a Prediction to a dictionary."""
        return {
            "prediction_id": pred.prediction_id,
            "prediction_type": pred.prediction_type.value,
            "confidence": round(pred.confidence, 3),
            "predicted_time": pred.predicted_time,
            "details": pred.details,
            "created_at": pred.created_at,
            "verified": pred.verified,
            "hit": pred.hit,
        }

    def _prefetch_to_dict(self, req: PrefetchRequest) -> Dict[str, Any]:
        """Convert a PrefetchRequest to a dictionary."""
        return {
            "request_id": req.request_id,
            "resource_type": req.resource_type,
            "resource_id": req.resource_id,
            "priority": req.priority,
            "status": req.status.value,
            "created_at": req.created_at,
            "completed_at": req.completed_at,
            "prediction_id": req.prediction_id,
            "size_kb": round(req.size_kb, 1),
        }
