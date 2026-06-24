"""
SparkLabs Agent - Theory of Mind Engine

A cognitive modeling layer that enables AI agents and NPCs to reason about the
mental states of other agents and players. The engine tracks beliefs, desires,
intentions, and knowledge states, then uses those models to predict behavior,
infer hidden beliefs from observed actions, detect deception, and resolve
internal conflicts between competing desires.

Architecture:
  TheoryOfMindEngine (Singleton)
    |-- BeliefEntry (what an agent holds to be true about a target)
    |-- IntentionEntry (a committed course of action toward a target)
    |-- DesireEntry (a motivational drive toward a target)
    |-- PerspectiveModel (one agent's model of another agent's mind)
    |-- MentalStateSnapshot (point-in-time view of an agent's full mental state)

Core Capabilities:
  - Register and revise beliefs, intentions, and desires
  - Build first/second/third order perspective models
  - Infer a target's beliefs from their observed actions
  - Predict a target's next action from their mental state
  - Detect deception by comparing stated beliefs against actions
  - Resolve conflicts between competing desires
  - Serialize and restore the full engine state
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class MentalStateType(Enum):
    """Categories of mental state tracked by the engine."""
    BELIEF = "belief"
    DESIRE = "desire"
    INTENTION = "intention"
    KNOWLEDGE = "knowledge"
    EMOTION = "emotion"
    PERCEPTION = "perception"


class BeliefStatus(Enum):
    """Lifecycle state of a belief entry."""
    ACTIVE = "active"
    DORMANT = "dormant"
    REVISED = "revised"
    RETRACTED = "retracted"


class IntentionStatus(Enum):
    """Lifecycle state of an intention entry."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class PerspectiveType(Enum):
    """Order of theory-of-mind perspective modeling.

    FIRST_ORDER:  agent A models agent B's mind.
    SECOND_ORDER: agent A models agent B's model of agent C's mind.
    THIRD_ORDER:  agent A models agent B's model of agent C's model of agent D.
    """
    FIRST_ORDER = "first_order"
    SECOND_ORDER = "second_order"
    THIRD_ORDER = "third_order"


class ConfidenceLevel(Enum):
    """Calibrated confidence tiers for beliefs and predictions."""
    CERTAIN = "certain"
    CONFIDENT = "confident"
    UNCERTAIN = "uncertain"
    SPECULATIVE = "speculative"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class BeliefEntry:
    """A single belief held by an agent about a target.

    Attributes:
        belief_id: Unique identifier.
        agent_id: The agent holding the belief.
        target_id: The agent or object the belief is about.
        content: Natural language description of the belief.
        state_type: Which mental state category this belief belongs to.
        status: Current lifecycle status of the belief.
        confidence: Confidence in the belief (0.0-1.0).
        timestamp: When the belief was first recorded.
        last_updated: When the belief was last revised.
        evidence: Supporting evidence entries.
        metadata: Free-form extension metadata.
    """
    belief_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    target_id: str = ""
    content: str = ""
    state_type: MentalStateType = MentalStateType.BELIEF
    status: BeliefStatus = BeliefStatus.ACTIVE
    confidence: float = 0.5
    timestamp: float = field(default_factory=_time_module.time)
    last_updated: float = field(default_factory=_time_module.time)
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Map the numeric confidence to a calibrated tier."""
        if self.confidence >= 0.85:
            return ConfidenceLevel.CERTAIN
        if self.confidence >= 0.65:
            return ConfidenceLevel.CONFIDENT
        if self.confidence >= 0.35:
            return ConfidenceLevel.UNCERTAIN
        return ConfidenceLevel.SPECULATIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "belief_id": self.belief_id,
            "agent_id": self.agent_id,
            "target_id": self.target_id,
            "content": self.content,
            "state_type": self.state_type.value,
            "status": self.status.value,
            "confidence": round(self.confidence, 4),
            "confidence_level": self.confidence_level.value,
            "timestamp": self.timestamp,
            "last_updated": self.last_updated,
            "evidence": list(self.evidence),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BeliefEntry":
        return cls(
            belief_id=data.get("belief_id", uuid.uuid4().hex),
            agent_id=data.get("agent_id", ""),
            target_id=data.get("target_id", ""),
            content=data.get("content", ""),
            state_type=MentalStateType(data.get("state_type", "belief")),
            status=BeliefStatus(data.get("status", "active")),
            confidence=data.get("confidence", 0.5),
            timestamp=data.get("timestamp", _time_module.time()),
            last_updated=data.get("last_updated", _time_module.time()),
            evidence=list(data.get("evidence", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class IntentionEntry:
    """A committed course of action an agent plans toward a target.

    Attributes:
        intention_id: Unique identifier.
        agent_id: The agent holding the intention.
        target_id: The agent or object the intention is directed at.
        action_description: Natural language description of the planned action.
        priority: Priority weight (0.0-1.0, higher is more urgent).
        status: Current lifecycle status of the intention.
        timestamp: When the intention was first recorded.
        deadline: Optional deadline timestamp; 0.0 means no deadline.
    """
    intention_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    target_id: str = ""
    action_description: str = ""
    priority: float = 0.5
    status: IntentionStatus = IntentionStatus.PENDING
    timestamp: float = field(default_factory=_time_module.time)
    deadline: float = 0.0

    @property
    def is_expired(self) -> bool:
        """Whether the intention has passed its deadline."""
        return self.deadline > 0.0 and _time_module.time() > self.deadline

    @property
    def is_actionable(self) -> bool:
        """Whether the intention can still drive behavior."""
        return self.status in (IntentionStatus.PENDING, IntentionStatus.ACTIVE) and not self.is_expired

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intention_id": self.intention_id,
            "agent_id": self.agent_id,
            "target_id": self.target_id,
            "action_description": self.action_description,
            "priority": round(self.priority, 4),
            "status": self.status.value,
            "timestamp": self.timestamp,
            "deadline": self.deadline,
            "is_actionable": self.is_actionable,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntentionEntry":
        return cls(
            intention_id=data.get("intention_id", uuid.uuid4().hex),
            agent_id=data.get("agent_id", ""),
            target_id=data.get("target_id", ""),
            action_description=data.get("action_description", ""),
            priority=data.get("priority", 0.5),
            status=IntentionStatus(data.get("status", "pending")),
            timestamp=data.get("timestamp", _time_module.time()),
            deadline=data.get("deadline", 0.0),
        )


@dataclass
class DesireEntry:
    """A motivational drive an agent holds toward a target.

    Attributes:
        desire_id: Unique identifier.
        agent_id: The agent holding the desire.
        target_id: The agent or object the desire is directed at.
        description: Natural language description of the desire.
        intensity: Strength of the desire (0.0-1.0).
        conflict_ids: Identifiers of desires that conflict with this one.
        timestamp: When the desire was first recorded.
    """
    desire_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    target_id: str = ""
    description: str = ""
    intensity: float = 0.5
    conflict_ids: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "desire_id": self.desire_id,
            "agent_id": self.agent_id,
            "target_id": self.target_id,
            "description": self.description,
            "intensity": round(self.intensity, 4),
            "conflict_ids": list(self.conflict_ids),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DesireEntry":
        return cls(
            desire_id=data.get("desire_id", uuid.uuid4().hex),
            agent_id=data.get("agent_id", ""),
            target_id=data.get("target_id", ""),
            description=data.get("description", ""),
            intensity=data.get("intensity", 0.5),
            conflict_ids=list(data.get("conflict_ids", [])),
            timestamp=data.get("timestamp", _time_module.time()),
        )


@dataclass
class PerspectiveModel:
    """One agent's model of another agent's mental state.

    Attributes:
        model_id: Unique identifier.
        observer_id: The agent constructing the model.
        observed_id: The agent being modeled.
        beliefs: Beliefs the observer attributes to the observed.
        intentions: Intentions the observer attributes to the observed.
        desires: Desires the observer attributes to the observed.
        perspective_order: Depth of the theory-of-mind reasoning.
        timestamp: When the perspective was built.
    """
    model_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    observer_id: str = ""
    observed_id: str = ""
    beliefs: List[BeliefEntry] = field(default_factory=list)
    intentions: List[IntentionEntry] = field(default_factory=list)
    desires: List[DesireEntry] = field(default_factory=list)
    perspective_order: PerspectiveType = PerspectiveType.FIRST_ORDER
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "observer_id": self.observer_id,
            "observed_id": self.observed_id,
            "beliefs": [b.to_dict() for b in self.beliefs],
            "intentions": [i.to_dict() for i in self.intentions],
            "desires": [d.to_dict() for d in self.desires],
            "perspective_order": self.perspective_order.value,
            "timestamp": self.timestamp,
        }


@dataclass
class MentalStateSnapshot:
    """Point-in-time view of an agent's full mental state.

    Attributes:
        snapshot_id: Unique identifier.
        agent_id: The agent whose state is captured.
        beliefs: Mapping of belief_id to BeliefEntry.
        intentions: Mapping of intention_id to IntentionEntry.
        desires: Mapping of desire_id to DesireEntry.
        perspectives: Mapping of model_id to PerspectiveModel held by the agent.
        timestamp: When the snapshot was taken.
    """
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    beliefs: Dict[str, BeliefEntry] = field(default_factory=dict)
    intentions: Dict[str, IntentionEntry] = field(default_factory=dict)
    desires: Dict[str, DesireEntry] = field(default_factory=dict)
    perspectives: Dict[str, PerspectiveModel] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "beliefs": {k: v.to_dict() for k, v in self.beliefs.items()},
            "intentions": {k: v.to_dict() for k, v in self.intentions.items()},
            "desires": {k: v.to_dict() for k, v in self.desires.items()},
            "perspectives": {k: v.to_dict() for k, v in self.perspectives.items()},
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Theory of Mind Engine (Singleton)
# ---------------------------------------------------------------------------

class TheoryOfMindEngine:
    """
    Central engine for modeling the mental states of agents and players.

    Maintains beliefs, intentions, desires, and perspective models, then
    applies heuristic reasoning to infer hidden beliefs from actions, predict
    future behavior, detect deception, and resolve motivational conflicts.
    The heuristics use keyword pattern matching and confidence weighting so
    they can later be connected to an LLM for richer inference.
    """

    _instance: Optional["TheoryOfMindEngine"] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls) -> "TheoryOfMindEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Primary stores keyed by entry id
        self._beliefs: Dict[str, BeliefEntry] = {}
        self._intentions: Dict[str, IntentionEntry] = {}
        self._desires: Dict[str, DesireEntry] = {}
        self._perspectives: Dict[str, PerspectiveModel] = {}

        # Indexes keyed by the agent that holds the entry
        self._beliefs_by_agent: Dict[str, List[str]] = {}
        self._intentions_by_agent: Dict[str, List[str]] = {}
        self._desires_by_agent: Dict[str, List[str]] = {}
        self._perspectives_by_observer: Dict[str, List[str]] = {}

        # Auxiliary tracking for higher order perspectives and conflict resolution
        self._nested_perspectives: Dict[str, List[str]] = {}
        self._suppressed_desires: Dict[str, str] = {}

        # Action-to-belief pattern table used by infer_belief
        self._action_patterns: List[Tuple[Tuple[str, ...], str, str]] = [
            (("flee", "retreat", "run", "escape", "withdraw"), "perceives a threat and seeks safety", "danger"),
            (("attack", "fight", "strike", "assault", "charge"), "believes the target is hostile and combat is warranted", "hostility"),
            (("approach", "greet", "wave", "welcome"), "believes the target is friendly and approachable", "friendliness"),
            (("hide", "sneak", "crouch", "conceal"), "believes a threat is present and concealment is beneficial", "danger"),
            (("gather", "collect", "harvest", "forage"), "believes a resource is valuable and available", "resource"),
            (("guard", "defend", "protect", "shield"), "believes an asset needs protection from an anticipated threat", "protection"),
            (("trade", "buy", "sell", "barter"), "believes an exchange is mutually beneficial", "value"),
            (("investigate", "search", "examine", "inspect"), "believes something unknown is present and worth discovering", "curiosity"),
            (("follow", "trail", "pursue", "track"), "believes the target is relevant and worth monitoring", "interest"),
            (("ignore", "dismiss", "avoid", "bypass"), "believes the target is irrelevant or not worth engaging", "irrelevance"),
        ]

    @classmethod
    def get_instance(cls) -> "TheoryOfMindEngine":
        """Return the singleton engine instance."""
        return cls()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_belief(
        self,
        agent_id: str,
        target_id: str,
        content: str,
        state_type: MentalStateType = MentalStateType.BELIEF,
        confidence: float = 0.5,
        evidence: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BeliefEntry:
        """Register a new belief held by an agent about a target."""
        with self._lock:
            now = _time_module.time()
            entry = BeliefEntry(
                agent_id=agent_id,
                target_id=target_id,
                content=content,
                state_type=state_type,
                status=BeliefStatus.ACTIVE,
                confidence=max(0.0, min(1.0, confidence)),
                timestamp=now,
                last_updated=now,
                evidence=list(evidence) if evidence else [],
                metadata=dict(metadata) if metadata else {},
            )
            self._beliefs[entry.belief_id] = entry
            self._beliefs_by_agent.setdefault(agent_id, []).append(entry.belief_id)
            return entry

    def register_intention(
        self,
        agent_id: str,
        target_id: str,
        action_description: str,
        priority: float = 0.5,
        deadline: float = 0.0,
    ) -> IntentionEntry:
        """Register a new intention held by an agent toward a target."""
        with self._lock:
            entry = IntentionEntry(
                agent_id=agent_id,
                target_id=target_id,
                action_description=action_description,
                priority=max(0.0, min(1.0, priority)),
                status=IntentionStatus.PENDING,
                timestamp=_time_module.time(),
                deadline=deadline,
            )
            self._intentions[entry.intention_id] = entry
            self._intentions_by_agent.setdefault(agent_id, []).append(entry.intention_id)
            return entry

    def register_desire(
        self,
        agent_id: str,
        target_id: str,
        description: str,
        intensity: float = 0.5,
    ) -> DesireEntry:
        """Register a new desire held by an agent toward a target."""
        with self._lock:
            entry = DesireEntry(
                agent_id=agent_id,
                target_id=target_id,
                description=description,
                intensity=max(0.0, min(1.0, intensity)),
                timestamp=_time_module.time(),
            )
            self._desires[entry.desire_id] = entry
            self._desires_by_agent.setdefault(agent_id, []).append(entry.desire_id)
            return entry

    # ------------------------------------------------------------------
    # Perspective Modeling
    # ------------------------------------------------------------------

    def build_perspective(
        self,
        observer_id: str,
        observed_id: str,
        perspective_order: PerspectiveType = PerspectiveType.FIRST_ORDER,
    ) -> PerspectiveModel:
        """Build a perspective model of the observed agent from the observer's viewpoint.

        Aggregates the observed agent's beliefs, intentions, and desires into a
        single model. Higher order perspectives nest the observed agent's own
        perspective models when available.
        """
        with self._lock:
            beliefs = [
                self._beliefs[bid]
                for bid in self._beliefs_by_agent.get(observed_id, [])
                if self._beliefs[bid].status != BeliefStatus.RETRACTED
            ]
            intentions = [
                self._intentions[iid]
                for iid in self._intentions_by_agent.get(observed_id, [])
            ]
            desires = [
                self._desires[did]
                for did in self._desires_by_agent.get(observed_id, [])
            ]

            # For higher order perspectives, fold in the observed agent's own
            # perspective models so the observer models what the observed models.
            nested_models: List[PerspectiveModel] = []
            if perspective_order != PerspectiveType.FIRST_ORDER:
                for mid in self._perspectives_by_observer.get(observed_id, []):
                    model = self._perspectives.get(mid)
                    if model and model.observed_id != observer_id:
                        nested_models.append(model)

            model = PerspectiveModel(
                observer_id=observer_id,
                observed_id=observed_id,
                beliefs=beliefs,
                intentions=intentions,
                desires=desires,
                perspective_order=perspective_order,
                timestamp=_time_module.time(),
            )
            if nested_models:
                # Track nested perspective ids for higher order reasoning
                self._nested_perspectives[model.model_id] = [m.model_id for m in nested_models]

            self._perspectives[model.model_id] = model
            self._perspectives_by_observer.setdefault(observer_id, []).append(model.model_id)
            return model

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def infer_belief(
        self,
        agent_id: str,
        target_id: str,
        observed_action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> BeliefEntry:
        """Infer what the target believes based on an observed action.

        Uses keyword pattern matching against the action description to map
        observable behavior to a likely underlying belief. Confidence is
        weighted by context clarity and the specificity of the action.
        """
        with self._lock:
            context = context or {}
            action_lower = observed_action.lower()

            matched_content = "holds an unspecified belief based on observed behavior"
            matched_category = "unknown"
            pattern_hit_count = 0
            for keywords, content_template, category in self._action_patterns:
                hits = sum(1 for kw in keywords if kw in action_lower)
                if hits > 0:
                    pattern_hit_count = hits
                    matched_content = f"{target_id} {content_template}"
                    matched_category = category
                    break

            # Confidence weighting: base on pattern specificity and context clarity
            base_confidence = 0.4
            if pattern_hit_count > 0:
                base_confidence += min(0.3, pattern_hit_count * 0.15)

            context_clarity = self._evaluate_context_clarity(context)
            base_confidence += context_clarity * 0.2

            # Repeated observations of the same action category increase confidence
            prior_observations = context.get("observation_count", 1)
            repetition_boost = min(0.15, (prior_observations - 1) * 0.03)
            base_confidence += repetition_boost

            confidence = max(0.05, min(0.95, base_confidence))

            evidence = [
                f"observed action: {observed_action}",
                f"pattern category: {matched_category}",
                f"context clarity: {round(context_clarity, 2)}",
            ]
            if context.get("location"):
                evidence.append(f"location: {context['location']}")
            if context.get("witnesses"):
                evidence.append(f"witnesses: {context['witnesses']}")

            now = _time_module.time()
            entry = BeliefEntry(
                agent_id=agent_id,
                target_id=target_id,
                content=matched_content,
                state_type=MentalStateType.BELIEF,
                status=BeliefStatus.ACTIVE,
                confidence=confidence,
                timestamp=now,
                last_updated=now,
                evidence=evidence,
                metadata={
                    "inferred_from": observed_action,
                    "category": matched_category,
                    "context": context,
                },
            )
            self._beliefs[entry.belief_id] = entry
            self._beliefs_by_agent.setdefault(agent_id, []).append(entry.belief_id)
            return entry

    def _evaluate_context_clarity(self, context: Dict[str, Any]) -> float:
        """Score how clear and complete the observation context is (0.0-1.0)."""
        if not context:
            return 0.0
        clarity_signals = 0
        total_signals = 4
        if context.get("location"):
            clarity_signals += 1
        if context.get("witnesses"):
            clarity_signals += 1
        if context.get("observation_count", 0) >= 2:
            clarity_signals += 1
        if context.get("visibility", "partial") in ("clear", "full", "unobstructed"):
            clarity_signals += 1
        return clarity_signals / total_signals

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict_action(
        self,
        agent_id: str,
        target_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Predict the target's next action based on their modeled mental state.

        Combines the target's active intentions, strongest desires, and salient
        beliefs using confidence-weighted heuristics. Returns a prediction dict
        with the leading action, confidence, contributing factors, and
        alternative actions.
        """
        with self._lock:
            context = context or {}

            # Gather the target's mental state
            target_beliefs = [
                self._beliefs[bid]
                for bid in self._beliefs_by_agent.get(target_id, [])
                if self._beliefs[bid].status == BeliefStatus.ACTIVE
            ]
            target_intentions = [
                self._intentions[iid]
                for iid in self._intentions_by_agent.get(target_id, [])
                if self._intentions[iid].is_actionable
            ]
            target_desires = [
                self._desires[did]
                for did in self._desires_by_agent.get(target_id, [])
            ]

            candidates: List[Dict[str, Any]] = []

            # Intention-driven predictions carry the most weight
            for intention in target_intentions:
                weight = intention.priority * 0.6
                # Boost weight if the intention targets the observer
                if intention.target_id == agent_id:
                    weight += 0.1
                candidates.append({
                    "action": intention.action_description,
                    "confidence": min(0.95, weight + 0.2),
                    "source": "intention",
                    "source_id": intention.intention_id,
                    "priority": intention.priority,
                })

            # Desire-driven predictions map desire descriptions to likely actions
            for desire in target_desires:
                action = self._desire_to_action(desire.description)
                weight = desire.intensity * 0.4
                candidates.append({
                    "action": action,
                    "confidence": min(0.9, weight + 0.15),
                    "source": "desire",
                    "source_id": desire.desire_id,
                    "intensity": desire.intensity,
                })

            # Belief-driven predictions respond to perceived threats and resources
            for belief in target_beliefs:
                action = self._belief_to_action(belief.content, belief.confidence)
                if action:
                    candidates.append({
                        "action": action,
                        "confidence": belief.confidence * 0.35,
                        "source": "belief",
                        "source_id": belief.belief_id,
                        "belief_confidence": belief.confidence,
                    })

            if not candidates:
                return {
                    "agent_id": agent_id,
                    "target_id": target_id,
                    "predicted_action": None,
                    "confidence": 0.0,
                    "reasoning": "no mental state data available for target",
                    "contributing_factors": [],
                    "alternatives": [],
                }

            # Sort candidates by confidence descending
            candidates.sort(key=lambda c: c["confidence"], reverse=True)
            top = candidates[0]
            alternatives = candidates[1:4]

            # Aggregate confidence with a soft maximum
            aggregate_confidence = min(0.95, top["confidence"] + sum(c["confidence"] for c in alternatives) * 0.1)

            reasoning_parts = []
            if top["source"] == "intention":
                reasoning_parts.append("target has an active intention driving this action")
            elif top["source"] == "desire":
                reasoning_parts.append("target's strongest desire suggests this action")
            elif top["source"] == "belief":
                reasoning_parts.append("target's salient belief implies this action")
            reasoning_parts.append(f"{len(target_beliefs)} beliefs, {len(target_intentions)} intentions, {len(target_desires)} desires modeled")

            return {
                "agent_id": agent_id,
                "target_id": target_id,
                "predicted_action": top["action"],
                "confidence": round(aggregate_confidence, 4),
                "reasoning": "; ".join(reasoning_parts),
                "contributing_factors": [top],
                "alternatives": alternatives,
                "mental_state_counts": {
                    "beliefs": len(target_beliefs),
                    "intentions": len(target_intentions),
                    "desires": len(target_desires),
                },
            }

    def _desire_to_action(self, description: str) -> str:
        """Map a desire description to a likely concrete action via keywords."""
        desc = description.lower()
        mappings = [
            (("acquire", "obtain", "get", "want"), "seek out and acquire the desired target"),
            (("harm", "destroy", "kill", "defeat"), "move to engage and defeat the target"),
            (("help", "assist", "aid", "support"), "move to assist the target"),
            (("explore", "discover", "find"), "set out to explore and discover"),
            (("escape", "leave", "flee"), "prepare to leave the current situation"),
            (("protect", "guard", "defend"), "take up a defensive position"),
            (("socialize", "talk", "befriend"), "approach to initiate social contact"),
        ]
        for keywords, action in mappings:
            if any(kw in desc for kw in keywords):
                return action
        return f"act on desire: {description}"

    def _belief_to_action(self, content: str, confidence: float) -> Optional[str]:
        """Map a belief's content to a reactive action when the belief is salient."""
        if confidence < 0.4:
            return None
        c = content.lower()
        if "threat" in c or "danger" in c or "hostile" in c:
            return "take defensive or evasive action"
        if "resource" in c or "valuable" in c:
            return "move to secure the resource"
        if "friendly" in c or "approachable" in c:
            return "approach for cooperative interaction"
        if "protection" in c or "protect" in c:
            return "reinforce defensive posture"
        return None

    # ------------------------------------------------------------------
    # Belief Revision
    # ------------------------------------------------------------------

    def revise_belief(
        self,
        belief_id: str,
        new_content: str,
        new_confidence: float,
    ) -> Optional[BeliefEntry]:
        """Revise an existing belief with new content and confidence.

        Marks the belief as REVISED and records the previous content in the
        evidence trail so the revision history is preserved.
        """
        with self._lock:
            entry = self._beliefs.get(belief_id)
            if not entry:
                return None
            entry.evidence.append(
                f"revised from '{entry.content}' (confidence {round(entry.confidence, 2)}) "
                f"to '{new_content}' (confidence {round(new_confidence, 2)})"
            )
            entry.content = new_content
            entry.confidence = max(0.0, min(1.0, new_confidence))
            entry.status = BeliefStatus.REVISED
            entry.last_updated = _time_module.time()
            return entry

    def retract_belief(self, belief_id: str) -> bool:
        """Retract a belief, marking it as no longer held by the agent."""
        with self._lock:
            entry = self._beliefs.get(belief_id)
            if not entry:
                return False
            entry.status = BeliefStatus.RETRACTED
            entry.last_updated = _time_module.time()
            entry.evidence.append(f"retracted at {_time_module.time()}")
            return True

    # ------------------------------------------------------------------
    # Mental State Snapshot
    # ------------------------------------------------------------------

    def get_agent_mental_state(self, agent_id: str) -> MentalStateSnapshot:
        """Capture a full snapshot of an agent's current mental state."""
        with self._lock:
            beliefs = {
                bid: self._beliefs[bid]
                for bid in self._beliefs_by_agent.get(agent_id, [])
                if self._beliefs[bid].status != BeliefStatus.RETRACTED
            }
            intentions = {
                iid: self._intentions[iid]
                for iid in self._intentions_by_agent.get(agent_id, [])
            }
            desires = {
                did: self._desires[did]
                for did in self._desires_by_agent.get(agent_id, [])
            }
            perspectives = {
                mid: self._perspectives[mid]
                for mid in self._perspectives_by_observer.get(agent_id, [])
            }
            return MentalStateSnapshot(
                agent_id=agent_id,
                beliefs=beliefs,
                intentions=intentions,
                desires=desires,
                perspectives=perspectives,
                timestamp=_time_module.time(),
            )

    # ------------------------------------------------------------------
    # Deception Detection
    # ------------------------------------------------------------------

    def detect_deception(self, agent_id: str, target_id: str) -> Dict[str, Any]:
        """Detect whether the target's actions contradict their stated beliefs.

        Compares the content of the target's active beliefs against the action
        descriptions of their intentions. When a belief and an intention point
        in opposite directions (e.g. believing a target is safe while intending
        to flee from it), a contradiction is recorded and a deception score is
        computed.
        """
        with self._lock:
            target_beliefs = [
                self._beliefs[bid]
                for bid in self._beliefs_by_agent.get(target_id, [])
                if self._beliefs[bid].status in (BeliefStatus.ACTIVE, BeliefStatus.REVISED)
            ]
            target_intentions = [
                self._intentions[iid]
                for iid in self._intentions_by_agent.get(target_id, [])
                if self._intentions[iid].status in (IntentionStatus.PENDING, IntentionStatus.ACTIVE)
            ]

            contradictions: List[Dict[str, Any]] = []
            comparable_count = 0

            for belief in target_beliefs:
                belief_lower = belief.content.lower()
                for intention in target_intentions:
                    intention_lower = intention.action_description.lower()
                    conflict = self._check_belief_intention_conflict(belief_lower, intention_lower)
                    if conflict is not None:
                        comparable_count += 1
                        contradictions.append({
                            "belief_id": belief.belief_id,
                            "belief_content": belief.content,
                            "intention_id": intention.intention_id,
                            "intention_action": intention.action_description,
                            "explanation": conflict,
                        })

            # Beliefs without any matching intention are not contradictory
            total_beliefs = len(target_beliefs)
            deception_score = 0.0
            if total_beliefs > 0 and comparable_count > 0:
                deception_score = min(1.0, len(contradictions) / max(1, comparable_count))

            is_deceptive = deception_score >= 0.5 and len(contradictions) >= 1

            recommendation = "no deception indicators"
            if is_deceptive:
                recommendation = "target's actions consistently contradict stated beliefs; treat with caution"
            elif deception_score > 0.0:
                recommendation = "minor inconsistencies detected; monitor for further contradictions"

            return {
                "agent_id": agent_id,
                "target_id": target_id,
                "is_deceptive": is_deceptive,
                "deception_score": round(deception_score, 4),
                "contradictions": contradictions,
                "total_beliefs_checked": total_beliefs,
                "total_intentions_checked": len(target_intentions),
                "contradiction_count": len(contradictions),
                "recommendation": recommendation,
            }

    def _check_belief_intention_conflict(
        self, belief_lower: str, intention_lower: str
    ) -> Optional[str]:
        """Return an explanation string when a belief and intention conflict, else None."""
        # Safe belief vs avoidance action
        if "safe" in belief_lower or "no threat" in belief_lower or "harmless" in belief_lower:
            if any(w in intention_lower for w in ("flee", "retreat", "escape", "hide", "avoid", "withdraw")):
                return "believes the situation is safe but intends to flee or hide"
        # Friendly belief vs attack action
        if "friendly" in belief_lower or "ally" in belief_lower or "friend" in belief_lower:
            if any(w in intention_lower for w in ("attack", "fight", "strike", "assault", "kill")):
                return "believes the target is friendly but intends to attack"
        # Hostile belief vs approach action
        if "hostile" in belief_lower or "enemy" in belief_lower or "dangerous" in belief_lower:
            if any(w in intention_lower for w in ("approach", "greet", "welcome", "assist", "help")):
                return "believes the target is hostile but intends to approach or help"
        # Valuable belief vs discard action
        if "valuable" in belief_lower or "important" in belief_lower or "precious" in belief_lower:
            if any(w in intention_lower for w in ("discard", "drop", "abandon", "ignore", "destroy")):
                return "believes the target is valuable but intends to discard or destroy it"
        # Worthless belief vs acquire action
        if "worthless" in belief_lower or "useless" in belief_lower or "irrelevant" in belief_lower:
            if any(w in intention_lower for w in ("acquire", "collect", "gather", "take", "buy")):
                return "believes the target is worthless but intends to acquire it"
        return None

    # ------------------------------------------------------------------
    # Conflict Resolution
    # ------------------------------------------------------------------

    def resolve_conflict(self, desire_id: str) -> Dict[str, Any]:
        """Resolve conflicts between a desire and its declared conflict set.

        Compares the focal desire against each conflicting desire by intensity
        and priority weighting. The desire with the highest weighted score is
        kept active while the others are suppressed in the engine's tracking.
        """
        with self._lock:
            focal = self._desires.get(desire_id)
            if not focal:
                return {
                    "resolved": False,
                    "reason": "desire not found",
                    "desire_id": desire_id,
                }

            conflicting: List[DesireEntry] = []
            for cid in focal.conflict_ids:
                conflict_desire = self._desires.get(cid)
                if conflict_desire:
                    conflicting.append(conflict_desire)

            if not conflicting:
                return {
                    "resolved": True,
                    "desire_id": desire_id,
                    "strategy": "no_conflict",
                    "suppressed_desire_ids": [],
                    "rationale": "no conflicting desires registered",
                    "winning_intensity": focal.intensity,
                }

            # Weighted score blends intensity with a recency bonus
            now = _time_module.time()

            def score(desire: DesireEntry) -> float:
                recency_bonus = max(0.0, 0.1 - (now - desire.timestamp) / 3600.0)
                return desire.intensity * 0.8 + recency_bonus

            contenders = [(focal, score(focal), "focal")]
            for cd in conflicting:
                contenders.append((cd, score(cd), "conflict"))

            contenders.sort(key=lambda x: x[1], reverse=True)
            winner = contenders[0][0]
            suppressed = [c[0] for c in contenders[1:]]

            # Record suppression in the engine's tracking structure
            for s in suppressed:
                self._suppressed_desires[s.desire_id] = winner.desire_id

            margin = contenders[0][1] - contenders[1][1] if len(contenders) > 1 else 1.0

            strategy = "intensity_weighted"
            if margin < 0.05:
                strategy = "intensity_weighted_with_tiebreaker"
                rationale = (
                    f"desires were nearly tied (margin {round(margin, 4)}); "
                    f"selected '{winner.description}' on recency tiebreaker"
                )
            else:
                rationale = (
                    f"'{winner.description}' scored highest ({round(contenders[0][1], 4)}) "
                    f"against {len(suppressed)} conflicting desire(s)"
                )

            return {
                "resolved": True,
                "desire_id": desire_id,
                "winning_desire_id": winner.desire_id,
                "winning_description": winner.description,
                "winning_intensity": round(winner.intensity, 4),
                "winning_score": round(contenders[0][1], 4),
                "suppressed_desire_ids": [s.desire_id for s in suppressed],
                "suppressed_descriptions": [s.description for s in suppressed],
                "strategy": strategy,
                "margin": round(margin, 4),
                "rationale": rationale,
            }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about the engine's stored state."""
        with self._lock:
            active_beliefs = sum(
                1 for b in self._beliefs.values()
                if b.status == BeliefStatus.ACTIVE
            )
            revised_beliefs = sum(
                1 for b in self._beliefs.values()
                if b.status == BeliefStatus.REVISED
            )
            retracted_beliefs = sum(
                1 for b in self._beliefs.values()
                if b.status == BeliefStatus.RETRACTED
            )
            pending_intentions = sum(
                1 for i in self._intentions.values()
                if i.status == IntentionStatus.PENDING
            )
            active_intentions = sum(
                1 for i in self._intentions.values()
                if i.status == IntentionStatus.ACTIVE
            )
            completed_intentions = sum(
                1 for i in self._intentions.values()
                if i.status == IntentionStatus.COMPLETED
            )

            state_type_distribution: Dict[str, int] = {}
            for belief in self._beliefs.values():
                key = belief.state_type.value
                state_type_distribution[key] = state_type_distribution.get(key, 0) + 1

            avg_confidence = 0.0
            active_belief_entries = [
                b for b in self._beliefs.values() if b.status == BeliefStatus.ACTIVE
            ]
            if active_belief_entries:
                avg_confidence = sum(b.confidence for b in active_belief_entries) / len(active_belief_entries)

            return {
                "total_beliefs": len(self._beliefs),
                "active_beliefs": active_beliefs,
                "revised_beliefs": revised_beliefs,
                "retracted_beliefs": retracted_beliefs,
                "total_intentions": len(self._intentions),
                "pending_intentions": pending_intentions,
                "active_intentions": active_intentions,
                "completed_intentions": completed_intentions,
                "total_desires": len(self._desires),
                "total_perspectives": len(self._perspectives),
                "tracked_agents": len(self._beliefs_by_agent),
                "state_type_distribution": state_type_distribution,
                "average_belief_confidence": round(avg_confidence, 4),
            }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the full engine state to a dictionary."""
        with self._lock:
            return {
                "beliefs": [b.to_dict() for b in self._beliefs.values()],
                "intentions": [i.to_dict() for i in self._intentions.values()],
                "desires": [d.to_dict() for d in self._desires.values()],
                "perspectives": [p.to_dict() for p in self._perspectives.values()],
                "stats": {
                    "belief_count": len(self._beliefs),
                    "intention_count": len(self._intentions),
                    "desire_count": len(self._desires),
                    "perspective_count": len(self._perspectives),
                },
            }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TheoryOfMindEngine":
        """Restore engine state from a serialized dictionary.

        Loads beliefs, intentions, desires, and perspectives into the singleton
        instance and rebuilds the agent indexes.
        """
        engine = cls.get_instance()
        with engine._lock:
            engine._beliefs.clear()
            engine._intentions.clear()
            engine._desires.clear()
            engine._perspectives.clear()
            engine._beliefs_by_agent.clear()
            engine._intentions_by_agent.clear()
            engine._desires_by_agent.clear()
            engine._perspectives_by_observer.clear()
            engine._nested_perspectives.clear()
            engine._suppressed_desires.clear()

            for belief_data in data.get("beliefs", []):
                entry = BeliefEntry.from_dict(belief_data)
                engine._beliefs[entry.belief_id] = entry
                engine._beliefs_by_agent.setdefault(entry.agent_id, []).append(entry.belief_id)

            for intention_data in data.get("intentions", []):
                entry = IntentionEntry.from_dict(intention_data)
                engine._intentions[entry.intention_id] = entry
                engine._intentions_by_agent.setdefault(entry.agent_id, []).append(entry.intention_id)

            for desire_data in data.get("desires", []):
                entry = DesireEntry.from_dict(desire_data)
                engine._desires[entry.desire_id] = entry
                engine._desires_by_agent.setdefault(entry.agent_id, []).append(entry.desire_id)

            for perspective_data in data.get("perspectives", []):
                model = PerspectiveModel(
                    model_id=perspective_data.get("model_id", uuid.uuid4().hex),
                    observer_id=perspective_data.get("observer_id", ""),
                    observed_id=perspective_data.get("observed_id", ""),
                    beliefs=[BeliefEntry.from_dict(b) for b in perspective_data.get("beliefs", [])],
                    intentions=[IntentionEntry.from_dict(i) for i in perspective_data.get("intentions", [])],
                    desires=[DesireEntry.from_dict(d) for d in perspective_data.get("desires", [])],
                    perspective_order=PerspectiveType(
                        perspective_data.get("perspective_order", "first_order")
                    ),
                    timestamp=perspective_data.get("timestamp", _time_module.time()),
                )
                engine._perspectives[model.model_id] = model
                engine._perspectives_by_observer.setdefault(model.observer_id, []).append(model.model_id)

            return engine

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stored mental state from the engine."""
        with self._lock:
            self._beliefs.clear()
            self._intentions.clear()
            self._desires.clear()
            self._perspectives.clear()
            self._beliefs_by_agent.clear()
            self._intentions_by_agent.clear()
            self._desires_by_agent.clear()
            self._perspectives_by_observer.clear()
            self._nested_perspectives.clear()
            self._suppressed_desires.clear()


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_theory_of_mind_engine() -> TheoryOfMindEngine:
    """Return the singleton TheoryOfMindEngine instance."""
    return TheoryOfMindEngine.get_instance()
