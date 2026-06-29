"""
SparkLabs Agent - Contextual Intelligence Engine

Contextual intelligence for scene understanding and situation awareness.
Analyzes raw scene data, classifies it into a typed game context, assesses
the situation (threat and opportunity levels), and predicts the likely
next context so downstream agents can plan proactively.

Architecture:
  ContextualIntelligenceEngine (Singleton)
    |-- ContextType (typed category of a scene)
    |-- ContextFeature (a single named signal extracted from a scene)
    |-- SceneContext (typed, feature-bundled representation of a scene)
    |-- SituationAssessment (actionable read of a SceneContext)
    |-- ContextualIntelligenceSnapshot (point-in-time state capture)

The engine supports pluggable per-type handlers so callers can override
classification or assessment behavior for specific context types.
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


_time = _time_module


# =============================================================================
# Enums
# =============================================================================


class ContextType(Enum):
    """Typed category of a game scene.

    Used to route scene analysis to type-specific handlers and to
    bucket historical contexts for trend analysis.
    """

    COMBAT = "combat"
    SOCIAL = "social"
    EXPLORATION = "exploration"
    PUZZLE = "puzzle"
    NARRATIVE = "narrative"
    ECONOMIC = "economic"
    STEALTH = "stealth"
    DIALOGUE = "dialogue"


# Keyword cues used by the default classifier to map scene signals to a
# ContextType. Keys are lowercased feature-name cues; values are the type.
_CONTEXT_KEYWORD_MAP: Dict[str, ContextType] = {
    "combat": ContextType.COMBAT,
    "enemy": ContextType.COMBAT,
    "attack": ContextType.COMBAT,
    "damage": ContextType.COMBAT,
    "fight": ContextType.COMBAT,
    "social": ContextType.SOCIAL,
    "npc": ContextType.SOCIAL,
    "friend": ContextType.SOCIAL,
    "party": ContextType.SOCIAL,
    "explore": ContextType.EXPLORATION,
    "discover": ContextType.EXPLORATION,
    "map": ContextType.EXPLORATION,
    "travel": ContextType.EXPLORATION,
    "puzzle": ContextType.PUZZLE,
    "riddle": ContextType.PUZZLE,
    "lock": ContextType.PUZZLE,
    "solve": ContextType.PUZZLE,
    "story": ContextType.NARRATIVE,
    "quest": ContextType.NARRATIVE,
    "lore": ContextType.NARRATIVE,
    "plot": ContextType.NARRATIVE,
    "trade": ContextType.ECONOMIC,
    "shop": ContextType.ECONOMIC,
    "gold": ContextType.ECONOMIC,
    "buy": ContextType.ECONOMIC,
    "stealth": ContextType.STEALTH,
    "hide": ContextType.STEALTH,
    "sneak": ContextType.STEALTH,
    "silent": ContextType.STEALTH,
    "dialogue": ContextType.DIALOGUE,
    "talk": ContextType.DIALOGUE,
    "conversation": ContextType.DIALOGUE,
    "speech": ContextType.DIALOGUE,
}


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class ContextFeature:
    """A single named signal extracted from a scene.

    Attributes:
        feature_id: Auto-generated unique identifier for the feature.
        name: Human-readable feature name (e.g. "enemy_count").
        value: The feature's value (numeric or string).
        weight: Importance weight in [0.0, 1.0] used during classification.
    """

    feature_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    value: Any = 0.0
    weight: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "name": self.name,
            "value": self.value,
            "weight": self.weight,
        }


@dataclass
class SceneContext:
    """A typed, feature-bundled representation of a scene.

    Attributes:
        context_id: Auto-generated unique identifier for the context.
        context_type: Classified ContextType of the scene.
        features: List of features extracted from the raw scene data.
        confidence: Classification confidence in [0.0, 1.0].
        timestamp: POSIX timestamp when the context was created.
    """

    context_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    context_type: ContextType = ContextType.EXPLORATION
    features: List[ContextFeature] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = field(default_factory=_time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "context_type": self.context_type.value,
            "features": [f.to_dict() for f in self.features],
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class SituationAssessment:
    """An actionable read of a SceneContext.

    Attributes:
        assessment_id: Auto-generated unique identifier for the assessment.
        scene_context: The SceneContext being assessed.
        threat_level: Estimated threat in [0.0, 1.0].
        opportunity_level: Estimated opportunity in [0.0, 1.0].
        recommended_action: Human-readable recommended next action.
        urgency: Urgency in [0.0, 1.0]; higher means act sooner.
    """

    assessment_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scene_context: Optional[SceneContext] = None
    threat_level: float = 0.0
    opportunity_level: float = 0.0
    recommended_action: str = ""
    urgency: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "scene_context": self.scene_context.to_dict() if self.scene_context else None,
            "threat_level": self.threat_level,
            "opportunity_level": self.opportunity_level,
            "recommended_action": self.recommended_action,
            "urgency": self.urgency,
        }


@dataclass
class ContextualIntelligenceSnapshot:
    """Point-in-time capture of the contextual intelligence engine state.

    Attributes:
        snapshot_id: Auto-generated unique identifier for the snapshot.
        captured_at: POSIX timestamp of capture.
        context_history: Serialized recent scene contexts.
        context_count: Number of contexts analyzed.
        system_status: Aggregate status dictionary at capture time.
    """

    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    captured_at: float = field(default_factory=_time.time)
    context_history: List[Dict[str, Any]] = field(default_factory=list)
    context_count: int = 0
    system_status: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at,
            "context_history": self.context_history,
            "context_count": self.context_count,
            "system_status": self.system_status,
        }


# =============================================================================
# ContextualIntelligenceEngine (Singleton)
# =============================================================================


class ContextualIntelligenceEngine:
    """Analyzes and classifies game contexts (singleton).

    Provides scene analysis, context classification, situation
    assessment, and next-context prediction. The engine is thread-safe
    and intended to be accessed through the module-level
    :func:`get_contextual_intelligence_engine` factory.

    Per-type handlers can be registered via
    :meth:`register_context_handler` to override the default assessment
    for a specific ContextType.

    Usage:
        engine = get_contextual_intelligence_engine()
        scene = engine.analyze_scene({"enemy_count": 3, "combat": True})
        assessment = engine.assess_situation(scene)
        next_type = engine.predict_next_context(scene)
    """

    _instance: Optional["ContextualIntelligenceEngine"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_HISTORY: int = 500

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._context_history: List[SceneContext] = []
        self._handlers: Dict[ContextType, Callable[[SceneContext], SituationAssessment]] = {}
        self._stats: Dict[str, Any] = {
            "total_scenes_analyzed": 0,
            "total_assessments": 0,
            "total_predictions": 0,
            "type_counts": {t.value: 0 for t in ContextType},
        }
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "ContextualIntelligenceEngine":
        """Return the singleton ContextualIntelligenceEngine instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Scene Analysis & Classification
    # ------------------------------------------------------------------

    def analyze_scene(self, scene_data: Dict[str, Any]) -> SceneContext:
        """Analyze raw scene data into a typed SceneContext.

        Extracts features from the scene_data keys, classifies the
        context type from the feature names, and assigns a confidence
        score based on the strength of the keyword matches.

        Args:
            scene_data: Raw scene signals as a flat dictionary.

        Returns:
            A SceneContext with extracted features and classification.
        """
        with self._instance_lock:
            features: List[ContextFeature] = []
            for name, value in (scene_data or {}).items():
                features.append(ContextFeature(
                    name=name,
                    value=value,
                    weight=1.0,
                ))
            context_type = self.classify_context(features)
            confidence = self._compute_confidence(features, context_type)
            context = SceneContext(
                context_type=context_type,
                features=features,
                confidence=confidence,
                timestamp=_time.time(),
            )
            self._context_history.append(context)
            if len(self._context_history) > self._MAX_HISTORY:
                self._context_history = self._context_history[-self._MAX_HISTORY:]
            self._stats["total_scenes_analyzed"] += 1
            self._stats["type_counts"][context_type.value] = (
                self._stats["type_counts"].get(context_type.value, 0) + 1
            )
            return context

    def classify_context(self, features: List[ContextFeature]) -> ContextType:
        """Classify a list of features into a ContextType.

        Uses weighted keyword matching against the feature names. The
        type with the highest cumulative weight wins; ties are broken by
        the default ContextType ordering (first declared wins).

        Args:
            features: The features to classify.

        Returns:
            The best-matching ContextType. Defaults to EXPLORATION when
            no cues are present.
        """
        if not features:
            return ContextType.EXPLORATION
        scores: Dict[ContextType, float] = {}
        for feature in features:
            cue = (feature.name or "").strip().lower()
            if cue in _CONTEXT_KEYWORD_MAP:
                ctx_type = _CONTEXT_KEYWORD_MAP[cue]
                scores[ctx_type] = scores.get(ctx_type, 0.0) + feature.weight
        if not scores:
            return ContextType.EXPLORATION
        return max(scores.items(), key=lambda kv: kv[1])[0]

    # ------------------------------------------------------------------
    # Situation Assessment
    # ------------------------------------------------------------------

    def assess_situation(self, scene_context: SceneContext) -> SituationAssessment:
        """Assess a SceneContext into an actionable SituationAssessment.

        Dispatches to a registered per-type handler when one exists;
        otherwise uses the default heuristic assessment based on the
        feature values and context type.

        Args:
            scene_context: The SceneContext to assess.

        Returns:
            A SituationAssessment with threat/opportunity/urgency and a
            recommended action.
        """
        with self._instance_lock:
            handler = self._handlers.get(scene_context.context_type)
            if handler is not None:
                assessment = handler(scene_context)
            else:
                assessment = self._default_assessment(scene_context)
            self._stats["total_assessments"] += 1
            return assessment

    def predict_next_context(
        self, scene_context: SceneContext
    ) -> Optional[ContextType]:
        """Predict the likely next ContextType after the given scene.

        Uses a simple transition heuristic based on the current context
        type and the recent history. When no history is available, falls
        back to a canonical successor map.

        Args:
            scene_context: The current SceneContext.

        Returns:
            The predicted next ContextType, or None if no prediction can
            be made.
        """
        with self._instance_lock:
            self._stats["total_predictions"] += 1
            current = scene_context.context_type
            # Default successor map for common transitions.
            successors: Dict[ContextType, ContextType] = {
                ContextType.EXPLORATION: ContextType.COMBAT,
                ContextType.COMBAT: ContextType.NARRATIVE,
                ContextType.NARRATIVE: ContextType.DIALOGUE,
                ContextType.DIALOGUE: ContextType.SOCIAL,
                ContextType.SOCIAL: ContextType.ECONOMIC,
                ContextType.ECONOMIC: ContextType.EXPLORATION,
                ContextType.PUZZLE: ContextType.NARRATIVE,
                ContextType.STEALTH: ContextType.COMBAT,
            }
            # If we have history, prefer the most common transition observed.
            if len(self._context_history) >= 2:
                transitions: Dict[ContextType, int] = {}
                for i in range(1, len(self._context_history)):
                    prev = self._context_history[i - 1].context_type
                    nxt = self._context_history[i].context_type
                    if prev == current:
                        transitions[nxt] = transitions.get(nxt, 0) + 1
                if transitions:
                    return max(transitions.items(), key=lambda kv: kv[1])[0]
            return successors.get(current)

    # ------------------------------------------------------------------
    # Handler Registration
    # ------------------------------------------------------------------

    def register_context_handler(
        self,
        context_type: ContextType,
        handler: Callable[[SceneContext], SituationAssessment],
    ) -> None:
        """Register a custom assessment handler for a ContextType.

        Args:
            context_type: The ContextType the handler applies to.
            handler: Callable invoked with a SceneContext during
                assessment; must return a SituationAssessment.
        """
        with self._instance_lock:
            self._handlers[context_type] = handler

    # ------------------------------------------------------------------
    # Status & Snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return aggregate status of the contextual intelligence engine."""
        with self._instance_lock:
            return {
                "context_history_size": len(self._context_history),
                "registered_handlers": [t.value for t in self._handlers],
                "stats": dict(self._stats),
            }

    def get_snapshot(self) -> ContextualIntelligenceSnapshot:
        """Capture a point-in-time snapshot of the engine state."""
        with self._instance_lock:
            status = self.get_status()
            return ContextualIntelligenceSnapshot(
                captured_at=_time.time(),
                context_history=[c.to_dict() for c in self._context_history],
                context_count=len(self._context_history),
                system_status=status,
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear context history, handlers, and statistics."""
        with self._instance_lock:
            self._context_history.clear()
            self._handlers.clear()
            self._stats = {
                "total_scenes_analyzed": 0,
                "total_assessments": 0,
                "total_predictions": 0,
                "type_counts": {t.value: 0 for t in ContextType},
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_confidence(
        self, features: List[ContextFeature], context_type: ContextType
    ) -> float:
        """Compute a confidence score in [0.0, 1.0] for a classification."""
        if not features:
            return 0.0
        matching_weight = 0.0
        total_weight = 0.0
        for feature in features:
            total_weight += feature.weight
            cue = (feature.name or "").strip().lower()
            if _CONTEXT_KEYWORD_MAP.get(cue) == context_type:
                matching_weight += feature.weight
        if total_weight <= 0:
            return 0.0
        return matching_weight / total_weight

    def _default_assessment(
        self, scene_context: SceneContext
    ) -> SituationAssessment:
        """Default heuristic assessment when no handler is registered."""
        context_type = scene_context.context_type
        threat = 0.3
        opportunity = 0.4
        action = "proceed_with_caution"
        urgency = 0.3
        if context_type == ContextType.COMBAT:
            threat = 0.8
            opportunity = 0.3
            action = "engage_or_retreat"
            urgency = 0.9
        elif context_type == ContextType.STEALTH:
            threat = 0.6
            opportunity = 0.5
            action = "remain_hidden"
            urgency = 0.7
        elif context_type == ContextType.ECONOMIC:
            threat = 0.1
            opportunity = 0.8
            action = "trade"
            urgency = 0.2
        elif context_type == ContextType.PUZZLE:
            threat = 0.2
            opportunity = 0.7
            action = "solve_puzzle"
            urgency = 0.4
        elif context_type == ContextType.DIALOGUE:
            threat = 0.1
            opportunity = 0.6
            action = "converse"
            urgency = 0.3
        elif context_type == ContextType.SOCIAL:
            threat = 0.1
            opportunity = 0.6
            action = "socialize"
            urgency = 0.3
        elif context_type == ContextType.NARRATIVE:
            threat = 0.2
            opportunity = 0.5
            action = "advance_story"
            urgency = 0.3
        return SituationAssessment(
            scene_context=scene_context,
            threat_level=threat,
            opportunity_level=opportunity,
            recommended_action=action,
            urgency=urgency,
        )


# =============================================================================
# Module-level factory
# =============================================================================


def get_contextual_intelligence_engine() -> ContextualIntelligenceEngine:
    """Return the singleton ContextualIntelligenceEngine instance."""
    return ContextualIntelligenceEngine.get_instance()
