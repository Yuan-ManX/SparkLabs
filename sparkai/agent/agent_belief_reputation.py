"""
SparkLabs Agent - Belief & Reputation Engine

A social simulation system for AI-native game agents. Agents maintain
beliefs about the world, other agents, factions, and themselves. Social
events propagate through witness networks, updating reputation profiles
and trust relationships. The engine models belief decay, inference
chains, gossip propagation, and faction-based standing.

Architecture:
  BeliefReputationEngine (Singleton)
    |-- Belief (propositional knowledge with confidence and evidence)
    |-- ReputationProfile (aggregated social standing with trait scores)
    |-- SocialEvent (action record with witnesses and magnitude)
    |-- TrustNetwork (directed trust graph between agents)
    |-- FactionStanding (agent standing within a faction)

Core Capabilities:
  - Form, update, infer, and decay agent beliefs
  - Record social events and propagate reputation effects
  - Compute reputation profiles from event history
  - Build and query trust networks between agents
  - Track faction standing with reputation thresholds
  - Share beliefs through agent-to-agent communication
  - Generate gossip events among nearby agents
  - Classify standing levels on a hostility-to-alliance spectrum
"""

from __future__ import annotations

import heapq
import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BeliefSource(Enum):
    """How an agent acquired a belief."""
    DIRECT = "direct"
    OBSERVED = "observed"
    REPORTED = "reported"
    INFERRED = "inferred"


class ReputationTrait(Enum):
    """Personality traits that compose an agent's reputation profile."""
    HONOR = "honor"
    TRUSTWORTHINESS = "trustworthiness"
    HOSTILITY = "hostility"
    GENEROSITY = "generosity"
    COURAGE = "courage"
    WISDOM = "wisdom"
    DECEIT = "deceit"
    LOYALTY = "loyalty"


class StandingLevel(Enum):
    """Categorical standing derived from a [-1.0, 1.0] score."""
    HOSTILE = "hostile"
    UNFRIENDLY = "unfriendly"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    ALLIED = "allied"


# ---------------------------------------------------------------------------
# Trait-to-Event Mapping
# ---------------------------------------------------------------------------

_TRAIT_EVENT_WEIGHTS: Dict[ReputationTrait, Dict[str, float]] = {
    ReputationTrait.HONOR: {
        "helped": 0.08, "protected": 0.10, "betrayed": -0.15,
        "lied": -0.10, "kept_promise": 0.12, "broke_promise": -0.12,
        "stole": -0.10, "returned_item": 0.08, "confessed": 0.06,
    },
    ReputationTrait.TRUSTWORTHINESS: {
        "kept_promise": 0.12, "broke_promise": -0.15, "lied": -0.12,
        "confessed": 0.08, "shared_info": 0.06, "withheld_info": -0.08,
        "deceived": -0.14, "proved_reliable": 0.10,
    },
    ReputationTrait.HOSTILITY: {
        "attacked": 0.12, "threatened": 0.10, "insulted": 0.08,
        "provoked": 0.06, "helped": -0.06, "protected": -0.08,
        "spared": -0.10, "defused_conflict": -0.08,
    },
    ReputationTrait.GENEROSITY: {
        "shared_resource": 0.10, "gave_gift": 0.12, "donated": 0.10,
        "helped": 0.08, "stole": -0.10, "hoarded": -0.08,
        "charged_interest": -0.06, "refused_help": -0.08,
    },
    ReputationTrait.COURAGE: {
        "faced_danger": 0.10, "protected": 0.10, "fled": -0.10,
        "hid": -0.08, "stood_ground": 0.12, "attacked": 0.06,
        "rescued": 0.12, "defended": 0.10,
    },
    ReputationTrait.WISDOM: {
        "solved_problem": 0.10, "gave_advice": 0.08, "shared_info": 0.06,
        "made_mistake": -0.06, "misled": -0.10, "taught": 0.10,
        "discovered": 0.08, "predicted": 0.08,
    },
    ReputationTrait.DECEIT: {
        "lied": 0.12, "deceived": 0.14, "betrayed": 0.12,
        "withheld_info": 0.08, "confessed": -0.10, "kept_promise": -0.08,
        "proved_reliable": -0.10, "shared_info": -0.06,
    },
    ReputationTrait.LOYALTY: {
        "defended": 0.12, "betrayed": -0.15, "stood_ground": 0.08,
        "fled": -0.06, "helped": 0.06, "refused_help": -0.06,
        "kept_promise": 0.10, "broke_promise": -0.12,
    },
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Belief:
    """A propositional belief held by an agent about a target.

    Targets can be agent IDs, 'world' (environmental facts), 'self'
    (self-knowledge), or 'faction' (group-level beliefs). Confidence
    ranges from 0.0 (no belief) to 1.0 (absolute certainty). Beliefs
    decay over time proportionally to their decay_rate.
    """
    belief_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    holder_agent_id: str = ""
    target_agent_id: str = ""
    predicate: str = ""
    value: Any = None
    confidence: float = 0.5
    evidence: List[str] = field(default_factory=list)
    formed_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    source: BeliefSource = BeliefSource.DIRECT
    decay_rate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "belief_id": self.belief_id,
            "holder_agent_id": self.holder_agent_id,
            "target_agent_id": self.target_agent_id,
            "predicate": self.predicate,
            "value": self.value,
            "confidence": round(self.confidence, 4),
            "evidence_count": len(self.evidence),
            "evidence": self.evidence[-5:],
            "formed_at": self.formed_at,
            "last_updated": self.last_updated,
            "source": self.source.value,
            "decay_rate": self.decay_rate,
            "metadata": self.metadata,
        }

    def apply_decay(self, now: float) -> float:
        """Apply time-based decay and return the new confidence value."""
        if self.decay_rate <= 0.0 or self.confidence <= 0.0:
            return self.confidence
        elapsed = now - self.last_updated
        if elapsed <= 0.0:
            return self.confidence
        decay_factor = math.exp(-self.decay_rate * elapsed)
        self.confidence = max(0.0, self.confidence * decay_factor)
        self.last_updated = now
        return self.confidence


@dataclass
class ReputationProfile:
    """Aggregated social standing of an agent.

    Overall standing ranges from -1.0 (universally despised) to 1.0
    (universally admired). Traits are scored on the same scale and
    aggregated from observed social events. Witness count tracks how
    many distinct agents have formed opinions about this agent.
    """
    agent_id: str = ""
    overall_standing: float = 0.0
    traits: Dict[str, float] = field(default_factory=dict)
    witness_count: int = 0
    last_evaluated: float = field(default_factory=time.time)
    reputation_history: List[Tuple[float, float]] = field(default_factory=list)
    factions: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "overall_standing": round(self.overall_standing, 4),
            "traits": {k: round(v, 4) for k, v in self.traits.items()},
            "witness_count": self.witness_count,
            "last_evaluated": self.last_evaluated,
            "history_entries": len(self.reputation_history),
            "factions": {
                fid: round(s, 4) for fid, s in self.factions.items()
            },
        }

    def get_standing_level(self) -> StandingLevel:
        return _standing_from_score(self.overall_standing)


@dataclass
class SocialEvent:
    """A recorded social action involving agents.

    Events have an actor (who performed the action), a target (who
    received it), a descriptive action string, an outcome, and a
    magnitude (0.0 to 1.0) indicating significance. Witnesses are
    agents who observed the event directly.
    """
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str = "witnessed"
    actor_id: str = ""
    target_id: str = ""
    action: str = ""
    outcome: str = ""
    magnitude: float = 0.5
    witnesses: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    location: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "target_id": self.target_id,
            "action": self.action,
            "outcome": self.outcome,
            "magnitude": round(self.magnitude, 4),
            "witness_count": len(self.witnesses),
            "witnesses": self.witnesses,
            "timestamp": self.timestamp,
            "location": self.location,
        }


@dataclass
class TrustNetwork:
    """A directed trust graph centered on one agent.

    Trust scores range from 0.0 (no trust) to 1.0 (complete trust).
    The network is built by traversing the agent's direct and indirect
    relationships up to a configurable depth.
    """
    agent_id: str = ""
    trust_relationships: Dict[str, float] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "trusted_agents": len(self.trust_relationships),
            "trust_relationships": {
                aid: round(s, 4)
                for aid, s in self.trust_relationships.items()
            },
            "last_updated": self.last_updated,
        }

    def get_trust(self, other_agent_id: str) -> float:
        return self.trust_relationships.get(other_agent_id, 0.0)


@dataclass
class FactionStanding:
    """An agent's standing within a specific faction.

    Standing ranges from -1.0 to 1.0. The reputation_threshold is the
    minimum standing required for the faction to consider the agent
    favorably. Metadata can store faction-specific tags.
    """
    faction_id: str = ""
    agent_id: str = ""
    standing: float = 0.0
    reputation_threshold: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "faction_id": self.faction_id,
            "agent_id": self.agent_id,
            "standing": round(self.standing, 4),
            "reputation_threshold": round(self.reputation_threshold, 4),
            "is_in_standing": self.standing >= self.reputation_threshold,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Standing Helpers
# ---------------------------------------------------------------------------

def _standing_from_score(score: float) -> StandingLevel:
    """Map a [-1.0, 1.0] standing score to a StandingLevel."""
    clamped = max(-1.0, min(1.0, score))
    if clamped <= -0.6:
        return StandingLevel.HOSTILE
    if clamped <= -0.2:
        return StandingLevel.UNFRIENDLY
    if clamped <= 0.2:
        return StandingLevel.NEUTRAL
    if clamped <= 0.6:
        return StandingLevel.FRIENDLY
    return StandingLevel.ALLIED


def _score_from_standing(level: StandingLevel) -> Tuple[float, float]:
    """Return the (min, max) score range for a StandingLevel."""
    ranges = {
        StandingLevel.HOSTILE: (-1.0, -0.6),
        StandingLevel.UNFRIENDLY: (-0.6, -0.2),
        StandingLevel.NEUTRAL: (-0.2, 0.2),
        StandingLevel.FRIENDLY: (0.2, 0.6),
        StandingLevel.ALLIED: (0.6, 1.0),
    }
    return ranges[level]


# ---------------------------------------------------------------------------
# BeliefReputationEngine
# ---------------------------------------------------------------------------

class BeliefReputationEngine:
    """Thread-safe singleton engine for belief and reputation management.

    Maintains belief stores, reputation profiles, event history, trust
    networks, and faction standings. All mutating operations are guarded
    by a re-entrant lock for concurrent access from game threads.
    """

    _instance: Optional["BeliefReputationEngine"] = None
    _lock = threading.RLock()
    _initialized: bool = False

    _MAX_BELIEFS: int = 50000
    _MAX_BELIEFS_PER_HOLDER: int = 2000
    _MAX_EVENTS: int = 100000
    _MAX_EVENTS_PER_AGENT: int = 5000
    _MAX_HISTORY_LENGTH: int = 100
    _DEFAULT_DECAY_INTERVAL: float = 60.0
    _GOSSIP_RADIUS: float = 5.0
    _INFERENCE_CONFIDENCE_FLOOR: float = 0.3
    _TRUST_DECAY_RATE: float = 0.0001

    def __new__(cls) -> "BeliefReputationEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._beliefs: Dict[str, Belief] = {}
        self._beliefs_by_holder: Dict[str, Set[str]] = {}
        self._beliefs_by_target: Dict[str, Set[str]] = {}
        self._beliefs_by_predicate: Dict[str, Set[str]] = {}
        self._beliefs_by_holder_target: Dict[Tuple[str, str], Set[str]] = {}

        self._profiles: Dict[str, ReputationProfile] = {}
        self._events: Dict[str, SocialEvent] = {}
        self._events_by_actor: Dict[str, List[str]] = {}
        self._events_by_target: Dict[str, List[str]] = {}
        self._events_by_witness: Dict[str, List[str]] = {}

        self._trust_networks: Dict[str, TrustNetwork] = {}
        self._faction_standings: Dict[Tuple[str, str], FactionStanding] = {}

        self._total_beliefs_formed: int = 0
        self._total_beliefs_decayed: int = 0
        self._total_events_recorded: int = 0
        self._total_inferences: int = 0
        self._total_gossip_events: int = 0

    @classmethod
    def get_instance(cls) -> "BeliefReputationEngine":
        return cls()

    # ------------------------------------------------------------------
    # Belief Management
    # ------------------------------------------------------------------

    def form_belief(
        self,
        holder_id: str,
        target_id: str,
        predicate: str,
        value: Any = None,
        confidence: float = 0.5,
        source: BeliefSource = BeliefSource.DIRECT,
        evidence: Optional[List[str]] = None,
        decay_rate: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Belief:
        with self._lock:
            self._enforce_belief_limits(holder_id)

            clamped_confidence = max(0.0, min(1.0, confidence))
            now = time.time()

            belief = Belief(
                holder_agent_id=holder_id,
                target_agent_id=target_id,
                predicate=predicate,
                value=value,
                confidence=clamped_confidence,
                evidence=list(evidence) if evidence else [],
                formed_at=now,
                last_updated=now,
                source=source,
                decay_rate=decay_rate,
                metadata=metadata or {},
            )

            self._store_belief(belief)
            self._total_beliefs_formed += 1
            return belief

    def update_belief(
        self,
        belief_id: str,
        new_value: Optional[Any] = None,
        new_confidence: Optional[float] = None,
        new_evidence: Optional[List[str]] = None,
    ) -> Optional[Belief]:
        with self._lock:
            belief = self._beliefs.get(belief_id)
            if belief is None:
                return None
            if new_value is not None:
                belief.value = new_value
            if new_confidence is not None:
                belief.confidence = max(0.0, min(1.0, new_confidence))
            if new_evidence is not None:
                belief.evidence.extend(new_evidence)
            belief.last_updated = time.time()
            return belief

    def get_beliefs(
        self,
        holder_id: str,
        target_id: Optional[str] = None,
        predicate: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> List[Belief]:
        with self._lock:
            if target_id is not None:
                candidate_ids = self._beliefs_by_holder_target.get(
                    (holder_id, target_id), set()
                ).copy()
            else:
                candidate_ids = self._beliefs_by_holder.get(holder_id, set()).copy()

            if predicate is not None and predicate in self._beliefs_by_predicate:
                pred_ids = self._beliefs_by_predicate[predicate]
                candidate_ids = candidate_ids.intersection(pred_ids)

            results: List[Belief] = []
            for bid in candidate_ids:
                belief = self._beliefs.get(bid)
                if belief is None:
                    continue
                if belief.holder_agent_id != holder_id:
                    continue
                if belief.confidence < min_confidence:
                    continue
                results.append(belief)

            results.sort(key=lambda b: b.confidence, reverse=True)
            return results

    def infer_belief(
        self,
        holder_id: str,
        target_id: str,
        predicate: str,
    ) -> Optional[Belief]:
        with self._lock:
            related = self._find_related_beliefs(holder_id, target_id, predicate)
            if not related:
                return None

            inferred_confidence = self._compute_inference_confidence(related)
            if inferred_confidence < self._INFERENCE_CONFIDENCE_FLOOR:
                return None

            inferred_value = self._resolve_inferred_value(related, predicate)

            evidence_refs = [b.belief_id for b in related]

            now = time.time()
            belief = Belief(
                holder_agent_id=holder_id,
                target_agent_id=target_id,
                predicate=predicate,
                value=inferred_value,
                confidence=inferred_confidence,
                evidence=evidence_refs,
                formed_at=now,
                last_updated=now,
                source=BeliefSource.INFERRED,
                decay_rate=0.00005,
            )

            self._store_belief(belief)
            self._total_inferences += 1
            return belief

    def decay_beliefs(self) -> int:
        with self._lock:
            now = time.time()
            removed_count = 0
            to_remove: List[str] = []

            for bid, belief in self._beliefs.items():
                confidence = belief.apply_decay(now)
                if confidence <= 0.01:
                    to_remove.append(bid)

            for bid in to_remove:
                self._remove_belief_internal(bid)
                self._total_beliefs_decayed += 1
                removed_count += 1

            return removed_count

    def share_belief(
        self,
        from_agent_id: str,
        to_agent_id: str,
        belief_id: str,
        trust_modifier: float = 1.0,
    ) -> Optional[Belief]:
        with self._lock:
            original = self._beliefs.get(belief_id)
            if original is None:
                return None
            if original.holder_agent_id != from_agent_id:
                return None

            trust = self._compute_pair_trust(from_agent_id, to_agent_id)
            effective_trust = max(0.0, min(1.0, trust * trust_modifier))

            shared_confidence = original.confidence * effective_trust * 0.85
            if shared_confidence < 0.05:
                return None

            shared = Belief(
                holder_agent_id=to_agent_id,
                target_agent_id=original.target_agent_id,
                predicate=original.predicate,
                value=original.value,
                confidence=shared_confidence,
                evidence=[f"shared_from_{from_agent_id}", belief_id],
                source=BeliefSource.REPORTED,
                decay_rate=original.decay_rate * 1.2,
                metadata={"shared_by": from_agent_id, "original_belief_id": belief_id},
            )

            self._store_belief(shared)
            self._total_beliefs_formed += 1
            return shared

    # ------------------------------------------------------------------
    # Social Event Management
    # ------------------------------------------------------------------

    def record_social_event(self, event: SocialEvent) -> SocialEvent:
        with self._lock:
            self._enforce_event_limits()

            if not event.event_id:
                event.event_id = uuid.uuid4().hex
            if event.timestamp <= 0.0:
                event.timestamp = time.time()

            self._events[event.event_id] = event
            self._total_events_recorded += 1

            self._list_append(
                self._events_by_actor, event.actor_id, event.event_id
            )
            if event.target_id:
                self._list_append(
                    self._events_by_target, event.target_id, event.event_id
                )
            for witness_id in event.witnesses:
                self._list_append(
                    self._events_by_witness, witness_id, event.event_id
                )

            return event

    def process_social_event(self, event: SocialEvent) -> Dict[str, Any]:
        with self._lock:
            self.record_social_event(event)

            actor_profile = self._ensure_profile(event.actor_id)
            target_profile = (
                self._ensure_profile(event.target_id)
                if event.target_id else None
            )

            actor_delta = self._compute_reputation_delta(event, is_actor=True)
            self._apply_reputation_delta(actor_profile, actor_delta, event)

            target_delta = {}
            if target_profile is not None:
                target_delta = self._compute_reputation_delta(event, is_actor=False)
                self._apply_reputation_delta(target_profile, target_delta, event)

            for witness_id in event.witnesses:
                witness_profile = self._ensure_profile(witness_id)
                if witness_id != event.actor_id and witness_id != event.target_id:
                    witness_profile.witness_count += 1

            self._update_trust_from_event(event)

            return {
                "event_id": event.event_id,
                "actor_standing": actor_profile.overall_standing,
                "actor_traits": dict(actor_profile.traits),
                "target_standing": (
                    target_profile.overall_standing
                    if target_profile else None
                ),
                "target_traits": (
                    dict(target_profile.traits)
                    if target_profile else None
                ),
                "actor_delta": actor_delta,
                "target_delta": target_delta,
            }

    def get_events_for_agent(
        self,
        agent_id: str,
        role: str = "actor",
        limit: int = 50,
    ) -> List[SocialEvent]:
        with self._lock:
            if role == "actor":
                event_ids = self._events_by_actor.get(agent_id, [])
            elif role == "target":
                event_ids = self._events_by_target.get(agent_id, [])
            elif role == "witness":
                event_ids = self._events_by_witness.get(agent_id, [])
            else:
                return []

            results: List[SocialEvent] = []
            for eid in reversed(event_ids[-limit:]):
                evt = self._events.get(eid)
                if evt is not None:
                    results.append(evt)
            return results

    # ------------------------------------------------------------------
    # Reputation Management
    # ------------------------------------------------------------------

    def get_reputation(self, agent_id: str) -> Optional[ReputationProfile]:
        with self._lock:
            return self._profiles.get(agent_id)

    def evaluate_reputation(
        self,
        agent_id: str,
        events: Optional[List[SocialEvent]] = None,
    ) -> ReputationProfile:
        with self._lock:
            if events is None:
                event_ids = self._events_by_actor.get(agent_id, [])
                events = [
                    self._events[eid]
                    for eid in event_ids
                    if eid in self._events
                ]

            profile = self._ensure_profile(agent_id)

            trait_accum: Dict[str, float] = {}
            for trait in ReputationTrait:
                trait_accum[trait.value] = 0.0

            total_weight = 0.0
            for evt in events:
                if not evt.action:
                    continue
                weight = evt.magnitude
                total_weight += weight

                action_weights = _TRAIT_EVENT_WEIGHTS
                for trait, action_map in action_weights.items():
                    if evt.action in action_map:
                        trait_accum[trait.value] += (
                            action_map[evt.action] * weight
                        )

            if total_weight > 0.0:
                for trait_value in trait_accum:
                    trait_accum[trait_value] /= total_weight
                    trait_accum[trait_value] = max(
                        -1.0, min(1.0, trait_accum[trait_value])
                    )

            profile.traits = trait_accum
            profile.overall_standing = self._compute_overall_standing(trait_accum)
            profile.last_evaluated = time.time()

            history_entry = (profile.last_evaluated, profile.overall_standing)
            profile.reputation_history.append(history_entry)
            if len(profile.reputation_history) > self._MAX_HISTORY_LENGTH:
                profile.reputation_history = profile.reputation_history[
                    -self._MAX_HISTORY_LENGTH :
                ]

            return profile

    def get_standing_level(self, standing_score: float) -> StandingLevel:
        return _standing_from_score(standing_score)

    # ------------------------------------------------------------------
    # Trust Network
    # ------------------------------------------------------------------

    def build_trust_network(
        self, agent_id: str, max_depth: int = 2
    ) -> TrustNetwork:
        with self._lock:
            network = self._trust_networks.get(agent_id)
            if network is None:
                network = TrustNetwork(agent_id=agent_id)
                self._trust_networks[agent_id] = network

            visited: Set[str] = {agent_id}
            current_level: Set[str] = {agent_id}
            depth = 0

            while depth < max_depth and current_level:
                next_level: Set[str] = set()
                for current_id in current_level:
                    for other_id, trust in self._get_direct_trusts(current_id):
                        if other_id not in visited:
                            decayed = trust * (0.7 ** depth)
                            if decayed > 0.05:
                                network.trust_relationships[other_id] = max(
                                    network.trust_relationships.get(
                                        other_id, 0.0
                                    ),
                                    decayed,
                                )
                                next_level.add(other_id)
                        visited.add(other_id)
                current_level = next_level
                depth += 1

            network.last_updated = time.time()
            return network

    def get_trust_score(self, agent_a_id: str, agent_b_id: str) -> float:
        with self._lock:
            return self._compute_pair_trust(agent_a_id, agent_b_id)

    # ------------------------------------------------------------------
    # Faction Standing
    # ------------------------------------------------------------------

    def get_faction_standing(
        self, faction_id: str, agent_id: str
    ) -> Optional[FactionStanding]:
        with self._lock:
            return self._faction_standings.get((faction_id, agent_id))

    def update_faction_standing(
        self,
        faction_id: str,
        agent_id: str,
        standing_delta: float,
    ) -> FactionStanding:
        with self._lock:
            key = (faction_id, agent_id)
            existing = self._faction_standings.get(key)

            if existing is not None:
                existing.standing = max(
                    -1.0, min(1.0, existing.standing + standing_delta)
                )
                return existing

            standing = FactionStanding(
                faction_id=faction_id,
                agent_id=agent_id,
                standing=max(-1.0, min(1.0, standing_delta)),
            )
            self._faction_standings[key] = standing

            profile = self._ensure_profile(agent_id)
            profile.factions[faction_id] = standing.standing

            return standing

    # ------------------------------------------------------------------
    # Gossip and Social Network
    # ------------------------------------------------------------------

    def gossip(
        self, agent_id: str, range_radius: float = 5.0
    ) -> List[SocialEvent]:
        with self._lock:
            nearby_agents = self._find_nearby_agents(
                agent_id, range_radius
            )
            if not nearby_agents:
                return []

            recent_events = self.get_events_for_agent(
                agent_id, role="witness", limit=20
            )
            if not recent_events:
                return []

            gossip_events: List[SocialEvent] = []
            for evt in recent_events:
                if random.random() > 0.4:
                    continue
                for listener_id in nearby_agents:
                    if listener_id == agent_id:
                        continue
                    if random.random() > 0.3:
                        continue

                    trust = self._compute_pair_trust(agent_id, listener_id)
                    if trust < 0.15:
                        continue

                    gossip_magnitude = evt.magnitude * trust * 0.6
                    gossip_event = SocialEvent(
                        event_type="communicated",
                        actor_id=evt.actor_id,
                        target_id=evt.target_id,
                        action=evt.action,
                        outcome=evt.outcome,
                        magnitude=gossip_magnitude,
                        witnesses=[listener_id, agent_id],
                        location=evt.location,
                    )
                    gossip_events.append(gossip_event)
                    self.record_social_event(gossip_event)
                    self._total_gossip_events += 1

            return gossip_events

    def get_social_network(
        self, agent_id: str, depth: int = 1
    ) -> Dict[str, Any]:
        with self._lock:
            visited: Set[str] = {agent_id}
            current_level: Set[str] = {agent_id}
            nodes: List[Dict[str, Any]] = []
            edges: List[Dict[str, Any]] = []

            d = 0
            while d <= depth and current_level:
                next_level: Set[str] = set()
                for current_id in current_level:
                    if current_id not in visited or d == 0:
                        profile = self._profiles.get(current_id)
                        nodes.append({
                            "agent_id": current_id,
                            "standing": (
                                profile.overall_standing if profile else 0.0
                            ),
                            "depth": d,
                        })

                    for other_id, trust in self._get_direct_trusts(current_id):
                        edges.append({
                            "from": current_id,
                            "to": other_id,
                            "trust": round(trust, 4),
                            "depth": d,
                        })
                        if other_id not in visited:
                            next_level.add(other_id)
                        visited.add(other_id)

                current_level = next_level
                d += 1

            return {
                "center_agent": agent_id,
                "nodes": nodes,
                "edges": edges,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "max_depth": depth,
            }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            source_dist: Dict[str, int] = {}
            predicate_dist: Dict[str, int] = {}
            for belief in self._beliefs.values():
                src = belief.source.value
                source_dist[src] = source_dist.get(src, 0) + 1
                pred = belief.predicate
                predicate_dist[pred] = predicate_dist.get(pred, 0) + 1

            standing_dist: Dict[str, int] = {}
            for profile in self._profiles.values():
                level = _standing_from_score(profile.overall_standing).value
                standing_dist[level] = standing_dist.get(level, 0) + 1

            event_type_dist: Dict[str, int] = {}
            for evt in self._events.values():
                et = evt.event_type
                event_type_dist[et] = event_type_dist.get(et, 0) + 1

            avg_confidence = 0.0
            if self._beliefs:
                avg_confidence = sum(
                    b.confidence for b in self._beliefs.values()
                ) / len(self._beliefs)

            return {
                "total_beliefs": len(self._beliefs),
                "total_beliefs_formed": self._total_beliefs_formed,
                "total_beliefs_decayed": self._total_beliefs_decayed,
                "total_inferences": self._total_inferences,
                "total_events_recorded": self._total_events_recorded,
                "total_gossip_events": self._total_gossip_events,
                "total_profiles": len(self._profiles),
                "total_trust_networks": len(self._trust_networks),
                "total_faction_standings": len(self._faction_standings),
                "unique_belief_holders": len(self._beliefs_by_holder),
                "unique_belief_targets": len(self._beliefs_by_target),
                "unique_predicates": len(self._beliefs_by_predicate),
                "avg_confidence": round(avg_confidence, 4),
                "source_distribution": source_dist,
                "standing_distribution": standing_dist,
                "event_type_distribution": event_type_dist,
                "max_beliefs": self._MAX_BELIEFS,
                "max_events": self._MAX_EVENTS,
            }

    def reset(self) -> None:
        with self._lock:
            self._beliefs.clear()
            self._beliefs_by_holder.clear()
            self._beliefs_by_target.clear()
            self._beliefs_by_predicate.clear()
            self._beliefs_by_holder_target.clear()
            self._profiles.clear()
            self._events.clear()
            self._events_by_actor.clear()
            self._events_by_target.clear()
            self._events_by_witness.clear()
            self._trust_networks.clear()
            self._faction_standings.clear()
            self._total_beliefs_formed = 0
            self._total_beliefs_decayed = 0
            self._total_events_recorded = 0
            self._total_inferences = 0
            self._total_gossip_events = 0

    # ------------------------------------------------------------------
    # Internal: Belief Storage
    # ------------------------------------------------------------------

    def _store_belief(self, belief: Belief) -> None:
        bid = belief.belief_id
        self._beliefs[bid] = belief
        self._add_to_set(self._beliefs_by_holder, belief.holder_agent_id, bid)
        self._add_to_set(self._beliefs_by_target, belief.target_agent_id, bid)
        self._add_to_set(self._beliefs_by_predicate, belief.predicate, bid)
        key = (belief.holder_agent_id, belief.target_agent_id)
        self._add_to_set(self._beliefs_by_holder_target, key, bid)

    def _remove_belief_internal(self, belief_id: str) -> None:
        belief = self._beliefs.pop(belief_id, None)
        if belief is None:
            return
        self._remove_from_set(
            self._beliefs_by_holder, belief.holder_agent_id, belief_id
        )
        self._remove_from_set(
            self._beliefs_by_target, belief.target_agent_id, belief_id
        )
        self._remove_from_set(
            self._beliefs_by_predicate, belief.predicate, belief_id
        )
        key = (belief.holder_agent_id, belief.target_agent_id)
        self._remove_from_set(self._beliefs_by_holder_target, key, belief_id)

    def _enforce_belief_limits(self, holder_id: str) -> None:
        if len(self._beliefs) < self._MAX_BELIEFS:
            return
        sorted_beliefs = sorted(
            self._beliefs.items(),
            key=lambda item: item[1].confidence,
        )
        overflow = len(self._beliefs) - self._MAX_BELIEFS + 1
        for belief_id, _ in sorted_beliefs[:overflow]:
            self._remove_belief_internal(belief_id)

        holder_ids = self._beliefs_by_holder.get(holder_id, set())
        if len(holder_ids) < self._MAX_BELIEFS_PER_HOLDER:
            return
        holder_beliefs = [
            (bid, self._beliefs[bid])
            for bid in holder_ids
            if bid in self._beliefs
        ]
        holder_beliefs.sort(key=lambda item: item[1].confidence)
        overflow = len(holder_beliefs) - self._MAX_BELIEFS_PER_HOLDER + 1
        for belief_id, _ in holder_beliefs[:overflow]:
            self._remove_belief_internal(belief_id)

    # ------------------------------------------------------------------
    # Internal: Event Helpers
    # ------------------------------------------------------------------

    def _enforce_event_limits(self) -> None:
        if len(self._events) < self._MAX_EVENTS:
            return
        sorted_events = sorted(
            self._events.items(),
            key=lambda item: item[1].timestamp,
        )
        overflow = len(self._events) - self._MAX_EVENTS + 1
        for event_id, evt in sorted_events[:overflow]:
            self._remove_event_internal(event_id)

    def _remove_event_internal(self, event_id: str) -> None:
        evt = self._events.pop(event_id, None)
        if evt is None:
            return
        for lst in (
            self._events_by_actor.get(evt.actor_id),
            self._events_by_target.get(evt.target_id),
        ):
            if lst and event_id in lst:
                lst.remove(event_id)
        for witness_id in evt.witnesses:
            lst = self._events_by_witness.get(witness_id)
            if lst and event_id in lst:
                lst.remove(event_id)

    # ------------------------------------------------------------------
    # Internal: Reputation Computation
    # ------------------------------------------------------------------

    def _ensure_profile(self, agent_id: str) -> ReputationProfile:
        if agent_id not in self._profiles:
            profile = ReputationProfile(agent_id=agent_id)
            for trait in ReputationTrait:
                profile.traits[trait.value] = 0.0
            self._profiles[agent_id] = profile
        return self._profiles[agent_id]

    def _compute_reputation_delta(
        self, event: SocialEvent, is_actor: bool
    ) -> Dict[str, float]:
        deltas: Dict[str, float] = {}
        action = event.action
        if not action:
            return deltas

        action_weights = _TRAIT_EVENT_WEIGHTS
        for trait, action_map in action_weights.items():
            if action in action_map:
                weight = action_map[action] * event.magnitude
                if not is_actor:
                    weight *= -0.5
                deltas[trait.value] = weight

        return deltas

    def _apply_reputation_delta(
        self,
        profile: ReputationProfile,
        deltas: Dict[str, float],
        event: SocialEvent,
    ) -> None:
        for trait_value, delta in deltas.items():
            current = profile.traits.get(trait_value, 0.0)
            profile.traits[trait_value] = max(-1.0, min(1.0, current + delta))

        profile.overall_standing = self._compute_overall_standing(profile.traits)
        profile.last_evaluated = time.time()

        history_entry = (profile.last_evaluated, profile.overall_standing)
        profile.reputation_history.append(history_entry)
        if len(profile.reputation_history) > self._MAX_HISTORY_LENGTH:
            profile.reputation_history = profile.reputation_history[
                -self._MAX_HISTORY_LENGTH :
            ]

    def _compute_overall_standing(
        self, traits: Dict[str, float]
    ) -> float:
        if not traits:
            return 0.0

        positive_traits = {
            ReputationTrait.HONOR.value,
            ReputationTrait.TRUSTWORTHINESS.value,
            ReputationTrait.GENEROSITY.value,
            ReputationTrait.COURAGE.value,
            ReputationTrait.WISDOM.value,
            ReputationTrait.LOYALTY.value,
        }
        negative_traits = {
            ReputationTrait.HOSTILITY.value,
            ReputationTrait.DECEIT.value,
        }

        pos_sum = 0.0
        pos_count = 0
        for t in positive_traits:
            if t in traits:
                pos_sum += traits[t]
                pos_count += 1

        neg_sum = 0.0
        neg_count = 0
        for t in negative_traits:
            if t in traits:
                neg_sum += traits[t]
                neg_count += 1

        pos_avg = pos_sum / max(pos_count, 1)
        neg_avg = neg_sum / max(neg_count, 1)

        return max(-1.0, min(1.0, (pos_avg - neg_avg) * 0.5))

    # ------------------------------------------------------------------
    # Internal: Inference
    # ------------------------------------------------------------------

    def _find_related_beliefs(
        self, holder_id: str, target_id: str, predicate: str
    ) -> List[Belief]:
        related: List[Belief] = []

        holder_belief_ids = self._beliefs_by_holder.get(holder_id, set())
        for bid in holder_belief_ids:
            belief = self._beliefs.get(bid)
            if belief is None:
                continue
            if belief.target_agent_id == target_id and belief.predicate != predicate:
                if belief.confidence > 0.2:
                    related.append(belief)

        if target_id not in ("world", "self", "faction"):
            target_belief_ids = self._beliefs_by_holder.get(target_id, set())
            for bid in target_belief_ids:
                belief = self._beliefs.get(bid)
                if belief is None:
                    continue
                if belief.target_agent_id == holder_id and belief.confidence > 0.2:
                    related.append(belief)

        related.sort(key=lambda b: b.confidence, reverse=True)
        return related[:10]

    def _compute_inference_confidence(
        self, related: List[Belief]
    ) -> float:
        if not related:
            return 0.0

        total_conf = sum(b.confidence for b in related)
        avg_conf = total_conf / len(related)

        diversity = min(1.0, len(related) / 5.0)

        source_bonus = 0.0
        for b in related:
            if b.source == BeliefSource.DIRECT:
                source_bonus += 0.05
            elif b.source == BeliefSource.OBSERVED:
                source_bonus += 0.03

        return min(0.95, avg_conf * (0.5 + 0.5 * diversity) + source_bonus)

    def _resolve_inferred_value(
        self, related: List[Belief], predicate: str
    ) -> Any:
        if not related:
            return None

        if all(isinstance(b.value, (int, float)) for b in related):
            total = sum(b.value * b.confidence for b in related)
            total_weight = sum(b.confidence for b in related)
            if total_weight > 0:
                return total / total_weight

        if all(isinstance(b.value, bool) for b in related):
            true_weight = sum(
                b.confidence for b in related if b.value is True
            )
            false_weight = sum(
                b.confidence for b in related if b.value is False
            )
            return true_weight >= false_weight

        return related[0].value

    # ------------------------------------------------------------------
    # Internal: Trust Computation
    # ------------------------------------------------------------------

    def _compute_pair_trust(self, agent_a: str, agent_b: str) -> float:
        if agent_a == agent_b:
            return 1.0

        network = self._trust_networks.get(agent_a)
        if network is not None and agent_b in network.trust_relationships:
            val = network.trust_relationships[agent_b]
            elapsed = time.time() - network.last_updated
            decay = math.exp(-self._TRUST_DECAY_RATE * elapsed)
            return max(0.0, val * decay)

        profile_a = self._profiles.get(agent_a)
        profile_b = self._profiles.get(agent_b)

        base_trust = 0.3

        if profile_a is not None and profile_b is not None:
            trustworthiness_b = profile_b.traits.get(
                ReputationTrait.TRUSTWORTHINESS.value, 0.0
            )
            deceit_b = profile_b.traits.get(
                ReputationTrait.DECEIT.value, 0.0
            )
            base_trust = 0.3 + trustworthiness_b * 0.3 - deceit_b * 0.2
            base_trust = max(0.0, min(1.0, base_trust))

        return base_trust

    def _get_direct_trusts(
        self, agent_id: str
    ) -> List[Tuple[str, float]]:
        results: List[Tuple[str, float]] = []

        profile = self._profiles.get(agent_id)
        if profile is not None and profile.factions:
            for faction_id in profile.factions:
                for (fid, aid), fs in self._faction_standings.items():
                    if fid == faction_id and aid != agent_id:
                        results.append((aid, max(0.0, fs.standing)))

        actor_events = self._events_by_actor.get(agent_id, [])
        target_events = self._events_by_target.get(agent_id, [])

        interaction_counts: Dict[str, int] = {}
        for eid in actor_events:
            evt = self._events.get(eid)
            if evt is not None and evt.target_id:
                interaction_counts[evt.target_id] = (
                    interaction_counts.get(evt.target_id, 0) + 1
                )
        for eid in target_events:
            evt = self._events.get(eid)
            if evt is not None and evt.actor_id:
                interaction_counts[evt.actor_id] = (
                    interaction_counts.get(evt.actor_id, 0) + 1
                )

        for other_id, count in interaction_counts.items():
            trust = min(0.6, 0.1 + count * 0.05)
            results.append((other_id, trust))

        return results

    def _update_trust_from_event(self, event: SocialEvent) -> None:
        if not event.actor_id or not event.target_id:
            return

        network_a = self._trust_networks.get(event.actor_id)
        if network_a is None:
            network_a = TrustNetwork(agent_id=event.actor_id)
            self._trust_networks[event.actor_id] = network_a

        current = network_a.trust_relationships.get(event.target_id, 0.3)
        trust_delta = self._trust_delta_from_action(event.action)
        network_a.trust_relationships[event.target_id] = max(
            0.0, min(1.0, current + trust_delta * event.magnitude)
        )
        network_a.last_updated = time.time()

    def _trust_delta_from_action(self, action: str) -> float:
        positive_actions = {
            "helped", "protected", "kept_promise", "shared_resource",
            "gave_gift", "defended", "rescued", "proved_reliable",
            "confessed", "shared_info", "taught", "returned_item",
        }
        negative_actions = {
            "attacked", "betrayed", "lied", "stole", "broke_promise",
            "deceived", "fled", "threatened", "insulted", "withheld_info",
            "misled", "refused_help",
        }

        if action in positive_actions:
            return 0.08
        if action in negative_actions:
            return -0.10
        return 0.0

    # ------------------------------------------------------------------
    # Internal: Gossip Helpers
    # ------------------------------------------------------------------

    def _find_nearby_agents(
        self, agent_id: str, radius: float
    ) -> List[str]:
        nearby: List[str] = []

        agent_events = list(
            self._events_by_actor.get(agent_id, [])
        )
        agent_events.extend(
            self._events_by_target.get(agent_id, [])
        )
        agent_events.extend(
            self._events_by_witness.get(agent_id, [])
        )

        proximity: Dict[str, int] = {}
        for eid in agent_events:
            evt = self._events.get(eid)
            if evt is None:
                continue
            for candidate in [evt.actor_id, evt.target_id]:
                if candidate and candidate != agent_id:
                    proximity[candidate] = proximity.get(candidate, 0) + 1
            for witness_id in evt.witnesses:
                if witness_id and witness_id != agent_id:
                    proximity[witness_id] = proximity.get(witness_id, 0) + 1

        interaction_threshold = max(1, int(radius * 0.4))
        for other_id, count in proximity.items():
            if count >= interaction_threshold:
                nearby.append(other_id)

        return nearby

    # ------------------------------------------------------------------
    # Internal: Index Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _add_to_set(
        index: Dict[Any, Set[str]], key: Any, entry_id: str
    ) -> None:
        if key not in index:
            index[key] = set()
        index[key].add(entry_id)

    @staticmethod
    def _remove_from_set(
        index: Dict[Any, Set[str]], key: Any, entry_id: str
    ) -> None:
        if key in index:
            index[key].discard(entry_id)
            if not index[key]:
                del index[key]

    @staticmethod
    def _list_append(
        index: Dict[str, List[str]], key: str, entry_id: str
    ) -> None:
        if key not in index:
            index[key] = []
        if entry_id not in index[key]:
            index[key].append(entry_id)


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_belief_reputation() -> BeliefReputationEngine:
    """Return the singleton BeliefReputationEngine instance."""
    return BeliefReputationEngine.get_instance()