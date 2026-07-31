"""
SparkLabs Agent - Temporal Self Projection

The AgentTemporalSelfProjection lets an agent project itself into its own
past and future selves. The agent takes its present self-model, projects it
backward (how did I arrive here?) and forward (who will I become?),
embodies each projected self with a stance, a confidence, and a tension,
then encounters the divergences between each projected self and the
recorded or observed self. The lessons of those divergences are folded
back into the present self-model, and the projections are released so the
agent does not over-anchor on a single remembered past or a single
imagined future.

A self that only models itself in the present tends to drift without a
story; a self that projects across time, meets the gaps between
projection and reality, and folds those gaps back in tends to grow
coherent - the agent can feel who it was, who it is, and who it is
becoming as one continuous thread.

Architecture:
  PROJECT    ->  EMBODY     ->  ENCOUNTER   ->  INTEGRATE  ->  RELEASE
  (the agent    (each         (the projected   (the lessons    (the
   projects a   projected     self meets the    of the          projections
   past self    self is       observed self    divergence      fade so the
   and a        given a       and the gaps     are folded      present
   future self  stance, a     become           back into the   self-model
   from the     confidence    encounters)      present         does not
   present      and a                          self-model)     over-anchor)
   self-model)  tension)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class TemporalProjectionPhase(Enum):
    """Phases of the temporal self-projection cycle."""
    PROJECT = "project"        # project the present self-model into past and future selves
    EMBODY = "embody"          # give each projected self a stance, confidence, and tension
    ENCOUNTER = "encounter"    # meet the divergences between projection and observation
    INTEGRATE = "integrate"    # fold the lessons of the divergences into the present self
    RELEASE = "release"        # release the projections so the self does not over-anchor


class ProjectionDirection(Enum):
    """Whether a projection travels into the past or into the future."""
    PAST = "past"              # who the agent thinks it was
    FUTURE = "future"          # who the agent thinks it will become


class ProjectionStance(Enum):
    """The affective stance a projected self is embodied with."""
    ASPIRATIONAL = "aspirational"  # the projected self is who the agent hopes to be
    FEARED = "feared"              # the projected self is who the agent dreads becoming
    NOSTALGIC = "nostalgic"        # the projected self is who the agent fondly remembers
    PRAGMATIC = "pragmatic"        # the projected self is who the agent realistically expects


class EncounterOutcome(Enum):
    """How a projected self relates to the observed self at the encounter."""
    CONFIRMED = "confirmed"    # the projection matched the observation
    DIVERGENT = "divergent"    # the projection drifted from the observation
    CONFLICTED = "conflicted"  # the projection and observation partially agreed
    BLANK = "blank"            # there was no observation to encounter against


class SelfCoherence(Enum):
    """The overall coherence of an agent's temporal self-model."""
    FRAGMENTED = "fragmented"  # projections and observations rarely agree
    SETTLED = "settled"        # some agreement, still loosely held
    COHERENT = "coherent"      # projections and observations mostly align
    CRYSTALLIZED = "crystallized"  # the self-model is tightly coherent across time


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ProjectedSelf:
    """A self projected backward or forward from the present self-model."""
    projection_id: str
    direction: ProjectionDirection
    target_horizon_cycles: int = 3        # how many cycles away the projection sits
    stance: ProjectionStance = ProjectionStance.PRAGMATIC
    projected_traits: Dict[str, float] = field(default_factory=dict)  # trait -> 0.0-1.0
    confidence: float = 0.4               # 0.0-1.0, how strongly the projection is held
    coherence: float = 0.0                # 0.0-1.0, how well-formed the projected self is
    created_at: float = field(default_factory=time.time)


@dataclass
class EncounterRecord:
    """A record of a projected self meeting the observed self."""
    encounter_id: str
    projection_id: str
    observed_traits: Dict[str, float] = field(default_factory=dict)  # trait -> 0.0-1.0
    outcome: EncounterOutcome = EncounterOutcome.BLANK
    divergence_score: float = 0.0         # 0.0-1.0, how far projection was from observation
    created_at: float = field(default_factory=time.time)


@dataclass
class TemporalSelfState:
    """Per-agent temporal self-projection state."""
    agent_id: str
    present_self_model: Dict[str, float] = field(default_factory=dict)  # trait -> 0.0-1.0
    last_observations: Deque[Dict[str, float]] = field(default_factory=deque)
    projections: List[ProjectedSelf] = field(default_factory=list)
    encounters: List[EncounterRecord] = field(default_factory=list)
    coherence: SelfCoherence = SelfCoherence.FRAGMENTED
    total_projected: int = 0
    total_embodied: int = 0
    total_encountered: int = 0
    total_integrated: int = 0
    total_released: int = 0


# =============================================================================
# Agent Temporal Self Projection
# =============================================================================

class AgentTemporalSelfProjection:
    """
    Thread-safe singleton orchestrating temporal self-projection per agent.

    Usage:
        projector = AgentTemporalSelfProjection.get_instance()
        projector.register_agent("a1", {"curiosity": 0.6, "caution": 0.4})
        projector.record_observation("a1", {"curiosity": 0.55, "caution": 0.45})
        projector.cycle()
        state = projector.get_agent_state("a1")
    """

    _instance: Optional["AgentTemporalSelfProjection"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _PROJECT_DEFAULT_HORIZON = 3            # cycles away a synthesized projection sits
    _EMBODY_CONFIDENCE_BASE = 0.4           # base confidence assigned during embody
    _DIVERGENCE_THRESHOLD = 0.3             # divergence above this counts as DIVERGENT
    _INTEGRATION_GAIN = 0.12                # how strongly a lesson nudges the present self
    _RELEASE_DECAY = 0.2                    # how much confidence fades per release pass
    _MAX_PROJECTIONS_PER_AGENT = 30
    _MAX_ENCOUNTERS_PER_AGENT = 50
    _MAX_AGENTS = 30
    _MAX_EVENTS = 200
    _MAX_OBSERVATIONS_PER_AGENT = 8

    def __init__(self) -> None:
        self._agents: Dict[str, TemporalSelfState] = {}
        self._phase: TemporalProjectionPhase = TemporalProjectionPhase.PROJECT
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentTemporalSelfProjection":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    def _init_stats(self) -> None:
        self._stats = {
            "total_agents": 0,
            "total_projected": 0,
            "total_embodied": 0,
            "total_encountered": 0,
            "total_integrated": 0,
            "total_released": 0,
            "open_projections": 0,
            "avg_confidence": 0.0,
            "avg_divergence": 0.0,
            "coherence": SelfCoherence.FRAGMENTED.value,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._agents:
            return
        confidences: List[float] = []
        divergences: List[float] = []
        open_projections = 0
        for state in self._agents.values():
            for proj in state.projections:
                if proj.confidence > 0.05:
                    open_projections += 1
                    confidences.append(proj.confidence)
            for enc in state.encounters:
                divergences.append(enc.divergence_score)
        self._stats["total_agents"] = len(self._agents)
        self._stats["open_projections"] = open_projections
        self._stats["avg_confidence"] = (
            sum(confidences) / len(confidences) if confidences else 0.0
        )
        self._stats["avg_divergence"] = (
            sum(divergences) / len(divergences) if divergences else 0.0
        )
        # Derive overall coherence from agent coherence distribution.
        self._stats["coherence"] = self._derive_coherence().value

    def _derive_coherence(self) -> SelfCoherence:
        if not self._agents:
            return SelfCoherence.FRAGMENTED
        order = [
            SelfCoherence.FRAGMENTED,
            SelfCoherence.SETTLED,
            SelfCoherence.COHERENT,
            SelfCoherence.CRYSTALLIZED,
        ]
        ranks = [order.index(s.coherence) for s in self._agents.values()]
        avg_rank = sum(ranks) / len(ranks)
        if avg_rank >= 2.5:
            return SelfCoherence.CRYSTALLIZED
        if avg_rank >= 1.5:
            return SelfCoherence.COHERENT
        if avg_rank >= 0.5:
            return SelfCoherence.SETTLED
        return SelfCoherence.FRAGMENTED

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Agent Management
    # -------------------------------------------------------------------------

    def register_agent(self, agent_id: str,
                       initial_traits: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Register a new agent for temporal self-projection."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            if len(self._agents) >= self._MAX_AGENTS:
                return {"error": f"Agent capacity reached ({self._MAX_AGENTS})"}
            traits = {k: self._clip(v) for k, v in (initial_traits or {}).items()}
            state = TemporalSelfState(agent_id=agent_id, present_self_model=dict(traits))
            self._agents[agent_id] = state
            self._record_event("agent_registered", {
                "agent_id": agent_id,
                "initial_traits": dict(traits),
            })
            return {
                "agent_id": agent_id,
                "present_self_model": dict(traits),
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        with self._global_lock:
            state = self._agents.pop(agent_id, None)
            if state is None:
                return {"error": f"Agent not found: {agent_id}"}
            self._record_event("agent_removed", {"agent_id": agent_id})
            return {
                "removed": agent_id,
                "cleared_projections": len(state.projections),
                "cleared_encounters": len(state.encounters),
            }

    # -------------------------------------------------------------------------
    # Observation Intake
    # -------------------------------------------------------------------------

    def record_observation(self, agent_id: str,
                           observed_traits: Dict[str, float]) -> Dict[str, Any]:
        """Record the agent's actual observed traits for this cycle."""
        with self._global_lock:
            state = self._agents.get(agent_id)
            if state is None:
                return {"error": f"Agent not found: {agent_id}"}
            traits = {k: self._clip(v) for k, v in observed_traits.items()}
            state.last_observations.append(dict(traits))
            if len(state.last_observations) > self._MAX_OBSERVATIONS_PER_AGENT:
                state.last_observations.popleft()
            self._record_event("observation_recorded", {
                "agent_id": agent_id,
                "observed_traits": dict(traits),
            })
            return {
                "agent_id": agent_id,
                "observed_traits": dict(traits),
                "observation_count": len(state.last_observations),
            }

    # -------------------------------------------------------------------------
    # Explicit Projection
    # -------------------------------------------------------------------------

    def project_self(self, agent_id: str, projection_id: str,
                     direction: ProjectionDirection, horizon_cycles: int = 3,
                     stance: ProjectionStance = ProjectionStance.PRAGMATIC) -> Dict[str, Any]:
        """Explicitly project a single self for an agent."""
        with self._global_lock:
            state = self._agents.get(agent_id)
            if state is None:
                return {"error": f"Agent not found: {agent_id}"}
            if any(p.projection_id == projection_id for p in state.projections):
                return {"error": f"Projection already exists: {projection_id}"}
            projected = self._synthesize_projection(
                state, projection_id, direction, horizon_cycles, stance,
            )
            state.projections.append(projected)
            if len(state.projections) > self._MAX_PROJECTIONS_PER_AGENT:
                # Drop the projection with the lowest confidence.
                drop_id = min(state.projections, key=lambda p: p.confidence).projection_id
                state.projections = [
                    p for p in state.projections if p.projection_id != drop_id
                ]
            state.total_projected += 1
            self._record_event("projection_created", {
                "agent_id": agent_id,
                "projection_id": projection_id,
                "direction": direction.value,
                "horizon_cycles": horizon_cycles,
                "stance": stance.value,
            })
            return {
                "agent_id": agent_id,
                "projection_id": projection_id,
                "direction": direction.value,
                "target_horizon_cycles": projected.target_horizon_cycles,
                "stance": projected.stance.value,
                "projected_traits": dict(projected.projected_traits),
                "confidence": projected.confidence,
                "coherence": projected.coherence,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single temporal self-projection cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = TemporalProjectionPhase.PROJECT
            phase_outputs["project"] = self._phase_project()
            self._phase = TemporalProjectionPhase.EMBODY
            phase_outputs["embody"] = self._phase_embody()
            self._phase = TemporalProjectionPhase.ENCOUNTER
            phase_outputs["encounter"] = self._phase_encounter()
            self._phase = TemporalProjectionPhase.INTEGRATE
            phase_outputs["integrate"] = self._phase_integrate()
            self._phase = TemporalProjectionPhase.RELEASE
            phase_outputs["release"] = self._phase_release()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_project(self) -> Dict[str, Any]:
        """Project phase: synthesize projections for agents that have none."""
        projected = 0
        for state in self._agents.values():
            # If the agent already has live projections, do not pile on more.
            live = [p for p in state.projections if p.confidence > 0.05]
            if live:
                continue
            if not state.present_self_model:
                continue
            # Synthesize one past self and one future self from the present model.
            past_id = f"proj_{state.agent_id}_past_{self._cycle_count}"
            future_id = f"proj_{state.agent_id}_future_{self._cycle_count}"
            past = self._synthesize_projection(
                state, past_id, ProjectionDirection.PAST,
                self._PROJECT_DEFAULT_HORIZON, ProjectionStance.NOSTALGIC,
            )
            future = self._synthesize_projection(
                state, future_id, ProjectionDirection.FUTURE,
                self._PROJECT_DEFAULT_HORIZON, ProjectionStance.ASPIRATIONAL,
            )
            state.projections.append(past)
            state.projections.append(future)
            if len(state.projections) > self._MAX_PROJECTIONS_PER_AGENT:
                state.projections = state.projections[-self._MAX_PROJECTIONS_PER_AGENT:]
            state.total_projected += 2
            projected += 2
        self._stats["total_projected"] += projected
        self._record_event("phase_project", {"projected": projected})
        return {"projected": projected}

    def _phase_embody(self) -> Dict[str, Any]:
        """Embody phase: give each projection a confidence and a coherence."""
        embodied = 0
        for state in self._agents.values():
            for proj in state.projections:
                if proj.confidence <= 0.05:
                    continue
                # Confidence rises from the base by how much the present self
                # supports the projected traits, modulated by stance.
                stance_boost = {
                    ProjectionStance.ASPIRATIONAL: 0.15,
                    ProjectionStance.FEARED: 0.10,
                    ProjectionStance.NOSTALGIC: 0.05,
                    ProjectionStance.PRAGMATIC: 0.08,
                }.get(proj.stance, 0.0)
                support = sum(proj.projected_traits.values()) / max(
                    1, len(proj.projected_traits)
                )
                proj.confidence = max(0.0, min(1.0,
                    self._EMBODY_CONFIDENCE_BASE + stance_boost + support * 0.2))
                # Coherence is how tightly the projected traits agree among themselves.
                if proj.projected_traits:
                    vals = list(proj.projected_traits.values())
                    spread = max(vals) - min(vals)
                    proj.coherence = max(0.0, min(1.0, 1.0 - spread))
                else:
                    proj.coherence = 0.0
                embodied += 1
            state.total_embodied += sum(
                1 for p in state.projections if p.confidence > 0.05
            )
        self._stats["total_embodied"] += embodied
        self._record_event("phase_embody", {"embodied": embodied})
        return {"embodied": embodied}

    def _phase_encounter(self) -> Dict[str, Any]:
        """Encounter phase: meet each projection against the latest observation."""
        encountered = 0
        for state in self._agents.values():
            if not state.last_observations:
                continue
            observed = state.last_observations[-1]
            for proj in state.projections:
                if proj.confidence <= 0.05:
                    continue
                divergence = self._compute_divergence(proj.projected_traits, observed)
                outcome = self._classify_outcome(divergence, observed)
                encounter = EncounterRecord(
                    encounter_id=f"enc_{proj.projection_id}_{self._cycle_count}",
                    projection_id=proj.projection_id,
                    observed_traits=dict(observed),
                    outcome=outcome,
                    divergence_score=divergence,
                )
                state.encounters.append(encounter)
                if len(state.encounters) > self._MAX_ENCOUNTERS_PER_AGENT:
                    state.encounters = state.encounters[-self._MAX_ENCOUNTERS_PER_AGENT:]
                encountered += 1
            state.total_encountered += sum(
                1 for p in state.projections if p.confidence > 0.05
            )
        self._stats["total_encountered"] += encountered
        self._record_event("phase_encounter", {"encountered": encountered})
        return {"encountered": encountered}

    def _phase_integrate(self) -> Dict[str, Any]:
        """Integrate phase: fold the lessons of recent encounters into the present self."""
        integrated = 0
        for state in self._agents.values():
            if not state.present_self_model:
                continue
            # Use the most recent encounter per projection.
            seen_projections: set = set()
            for enc in reversed(state.encounters):
                if enc.projection_id in seen_projections:
                    continue
                seen_projections.add(enc.projection_id)
                if enc.outcome == EncounterOutcome.CONFIRMED:
                    # A confirmed projection reinforces the present self slightly.
                    for trait, value in enc.observed_traits.items():
                        if trait in state.present_self_model:
                            state.present_self_model[trait] = self._clip(
                                state.present_self_model[trait] * (1 - self._INTEGRATION_GAIN * 0.5)
                                + value * (self._INTEGRATION_GAIN * 0.5)
                            )
                        else:
                            state.present_self_model[trait] = self._clip(value)
                    integrated += 1
                elif enc.outcome in (EncounterOutcome.DIVERGENT, EncounterOutcome.CONFLICTED):
                    # A divergent projection nudges the present self toward the observed.
                    for trait, value in enc.observed_traits.items():
                        current = state.present_self_model.get(trait, 0.5)
                        state.present_self_model[trait] = self._clip(
                            current + (value - current) * self._INTEGRATION_GAIN
                        )
                    integrated += 1
                # BLANK encounters carry no lesson.
            state.total_integrated += integrated
            # Re-derive agent coherence from the most recent encounters.
            state.coherence = self._agent_coherence(state)
        self._stats["total_integrated"] += integrated
        self._record_event("phase_integrate", {"integrated": integrated})
        return {"integrated": integrated}

    def _phase_release(self) -> Dict[str, Any]:
        """Release phase: decay projection confidence so old projections fade."""
        released = 0
        for state in self._agents.values():
            for proj in state.projections:
                if proj.confidence <= 0.05:
                    continue
                proj.confidence = max(0.0, proj.confidence - self._RELEASE_DECAY)
                if proj.confidence <= 0.05:
                    released += 1
            state.total_released += released
            # Drop fully faded projections to keep the list compact.
            state.projections = [
                p for p in state.projections if p.confidence > 0.05
            ]
            # Keep at least one slot open by trimming oldest if at capacity.
            if len(state.projections) > self._MAX_PROJECTIONS_PER_AGENT:
                state.projections.sort(key=lambda p: p.created_at)
                state.projections = state.projections[-self._MAX_PROJECTIONS_PER_AGENT:]
        self._stats["total_released"] += released
        self._record_event("phase_release", {"released": released})
        return {"released": released}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _clip(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _synthesize_projection(self, state: TemporalSelfState, projection_id: str,
                               direction: ProjectionDirection, horizon_cycles: int,
                               stance: ProjectionStance) -> ProjectedSelf:
        """Synthesize a projected self from the present self-model."""
        projected_traits: Dict[str, float] = {}
        for trait, value in state.present_self_model.items():
            # Past selves drift slightly backward; future selves drift forward.
            drift = random.uniform(-0.15, 0.15)
            directional = -0.05 if direction == ProjectionDirection.PAST else 0.05
            stance_pull = {
                ProjectionStance.ASPIRATIONAL: 0.10,
                ProjectionStance.FEARED: -0.10,
                ProjectionStance.NOSTALGIC: 0.03,
                ProjectionStance.PRAGMATIC: 0.0,
            }.get(stance, 0.0)
            projected = value + drift + directional + stance_pull
            # Farther horizons amplify the drift.
            projected += (horizon_cycles - self._PROJECT_DEFAULT_HORIZON) * 0.02
            projected_traits[trait] = self._clip(projected)
        coherence = 0.4 if projected_traits else 0.0
        return ProjectedSelf(
            projection_id=projection_id,
            direction=direction,
            target_horizon_cycles=max(1, horizon_cycles),
            stance=stance,
            projected_traits=projected_traits,
            confidence=self._EMBODY_CONFIDENCE_BASE,
            coherence=coherence,
        )

    def _compute_divergence(self, projected: Dict[str, float],
                            observed: Dict[str, float]) -> float:
        """Compute the divergence between projected and observed trait sets."""
        if not projected and not observed:
            return 0.0
        all_traits = set(projected) | set(observed)
        total = 0.0
        for trait in all_traits:
            p = projected.get(trait, 0.5)
            o = observed.get(trait, 0.5)
            total += abs(p - o)
        return self._clip(total / max(1, len(all_traits)))

    def _classify_outcome(self, divergence: float,
                          observed: Dict[str, float]) -> EncounterOutcome:
        """Classify how a projection relates to the observation."""
        if not observed:
            return EncounterOutcome.BLANK
        if divergence < self._DIVERGENCE_THRESHOLD * 0.5:
            return EncounterOutcome.CONFIRMED
        if divergence < self._DIVERGENCE_THRESHOLD:
            return EncounterOutcome.CONFLICTED
        return EncounterOutcome.DIVERGENT

    def _agent_coherence(self, state: TemporalSelfState) -> SelfCoherence:
        """Derive an agent's coherence from its recent encounters."""
        if not state.encounters:
            return SelfCoherence.FRAGMENTED
        recent = state.encounters[-5:]
        confirmed = sum(1 for e in recent if e.outcome == EncounterOutcome.CONFIRMED)
        divergent = sum(1 for e in recent if e.outcome == EncounterOutcome.DIVERGENT)
        ratio = confirmed / max(1, len(recent))
        if ratio >= 0.7 and divergent == 0:
            return SelfCoherence.CRYSTALLIZED
        if ratio >= 0.5:
            return SelfCoherence.COHERENT
        if divergent < len(recent):
            return SelfCoherence.SETTLED
        return SelfCoherence.FRAGMENTED

    def _integrate_lesson(self, state: TemporalSelfState,
                          encounter: EncounterRecord) -> None:
        """Fold a single encounter's lesson into the present self-model."""
        if encounter.outcome == EncounterOutcome.BLANK:
            return
        for trait, value in encounter.observed_traits.items():
            current = state.present_self_model.get(trait, 0.5)
            state.present_self_model[trait] = self._clip(
                current + (value - current) * self._INTEGRATION_GAIN
            )

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "agents": len(self._agents),
                "stats": dict(self._stats),
            }

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        with self._global_lock:
            state = self._agents.get(agent_id)
            if state is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent_id,
                "present_self_model": dict(state.present_self_model),
                "coherence": state.coherence.value,
                "projections_count": len(state.projections),
                "encounters_count": len(state.encounters),
                "observations_count": len(state.last_observations),
                "total_projected": state.total_projected,
                "total_embodied": state.total_embodied,
                "total_encountered": state.total_encountered,
                "total_integrated": state.total_integrated,
                "total_released": state.total_released,
            }

    def get_projections(self, agent_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            state = self._agents.get(agent_id)
            if state is None:
                return {"error": f"Agent not found: {agent_id}"}
            projections = sorted(
                state.projections,
                key=lambda p: p.created_at,
                reverse=True,
            )[:limit]
            return {
                "agent_id": agent_id,
                "projections": [
                    {
                        "projection_id": p.projection_id,
                        "direction": p.direction.value,
                        "target_horizon_cycles": p.target_horizon_cycles,
                        "stance": p.stance.value,
                        "projected_traits": dict(p.projected_traits),
                        "confidence": p.confidence,
                        "coherence": p.coherence,
                        "created_at": p.created_at,
                    }
                    for p in projections
                ],
            }

    def get_encounters(self, agent_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            state = self._agents.get(agent_id)
            if state is None:
                return {"error": f"Agent not found: {agent_id}"}
            encounters = sorted(
                state.encounters,
                key=lambda e: e.created_at,
                reverse=True,
            )[:limit]
            return {
                "agent_id": agent_id,
                "encounters": [
                    {
                        "encounter_id": e.encounter_id,
                        "projection_id": e.projection_id,
                        "observed_traits": dict(e.observed_traits),
                        "outcome": e.outcome.value,
                        "divergence_score": e.divergence_score,
                        "created_at": e.created_at,
                    }
                    for e in encounters
                ],
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Simulation
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic agents and observations, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_agents()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_agents(self) -> None:
        """Seed a small set of synthetic agents with present selves and observations."""
        seed_agents = [
            ("sim_scout", {"curiosity": 0.7, "caution": 0.3, "loyalty": 0.5}),
            ("sim_builder", {"patience": 0.8, "ambition": 0.4, "caution": 0.6}),
            ("sim_diplomat", {"empathy": 0.7, "patience": 0.7, "ambition": 0.3}),
        ]
        for agent_id, traits in seed_agents:
            if agent_id not in self._agents:
                self.register_agent(agent_id, traits)
            state = self._agents.get(agent_id)
            if state is None:
                continue
            # Seed a couple of recorded observations that drift from the
            # initial model so encounters have something to bite on.
            if not state.last_observations:
                drift = {k: self._clip(v + random.uniform(-0.1, 0.1))
                         for k, v in traits.items()}
                state.last_observations.append(drift)
                drift2 = {k: self._clip(v + random.uniform(-0.15, 0.15))
                          for k, v in traits.items()}
                state.last_observations.append(drift2)

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._agents.clear()
            self._events_log.clear()
            self._phase = TemporalProjectionPhase.PROJECT
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
