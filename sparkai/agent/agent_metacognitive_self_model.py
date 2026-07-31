"""
SparkLabs Agent - Metacognitive Self-Model

The AgentMetacognitiveSelfModel captures how an agent observes its own
cognition and slowly forms a model of itself as a thinker. An agent that
never looks inward cannot tell when its reasoning is brittle; an agent
that watches itself decide, questions why it leaned that way, theorizes
a model of its own habits, tests that model against fresh decisions,
and revises the model when it mispredicts, gradually becomes its own
critic.

Each cycle is a single pass of self-observation: the agent records what
it noticed itself doing, formulates questions about why, drafts a
theoretical self-portrait, tests the portrait against a probe, and
revises the portrait where the test broke it.

Architecture:
  OBSERVE   ->  QUESTION  ->  THEORIZE  ->  TEST     ->  REVISE
  (capture    (ask why      (draft a       (probe the    (rewrite the
   cognitive   the agent     theoretical    portrait      portrait
   events as   leaned that   portrait of    against a     where the
   they        way)          its own        fresh probe)  probe broke
  happened)                  habits)                       it)

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

class MetacognitivePhase(Enum):
    """Phases of the metacognitive self-model cycle."""
    OBSERVE = "observe"        # capture cognitive events as they happened
    QUESTION = "question"      # ask why the agent leaned that way
    THEORIZE = "theorize"      # draft a theoretical self-portrait
    TEST = "test"              # probe the portrait against a fresh case
    REVISE = "revise"          # rewrite the portrait where the probe broke it


class CognitiveMode(Enum):
    """The cognitive mode an observed event was in."""
    DELIBERATE = "deliberate"    # slow, careful reasoning
    REACTIVE = "reactive"        # fast, reflexive response
    IMITATIVE = "imitative"      # echoing another agent
    CREATIVE = "creative"        # novel combination
    HABITUAL = "habitual"        # well-worn path


class SelfDimension(Enum):
    """A dimension along which the agent theorizes about itself."""
    PATIENCE = "patience"        # how long the agent holds a question
    BOLDNESS = "boldness"        # how willing to commit on thin evidence
    RIGIDITY = "rigidity"        # how stuck the agent gets on prior frames
    CURIOSITY = "curiosity"      # how readily the agent chases novelty
    DOUBT = "doubt"              # how often the agent second-guesses itself


class ProbeOutcome(Enum):
    """Outcome of probing a theoretical self-portrait."""
    CONFIRMED = "confirmed"      # the portrait predicted the probe
    REFUTED = "refuted"          # the portrait got it wrong
    PARTIAL = "partial"          # the portrait got part of it right
    NO_PREDICTION = "no_prediction"  # the portrait had nothing to say


class SelfModelMaturity(Enum):
    """How mature the agent's self-model has become."""
    UNFORMED = "unformed"        # not enough observation yet
    FRAGMENTARY = "fragmentary"  # a few isolated self-notions
    COHERENT = "coherent"        # a self-portrait hangs together
    SELF_AWARE = "self_aware"    # the portrait survives revision across probes


class EventState(Enum):
    """State of an individual cognitive event."""
    OBSERVED = "observed"        # captured but not yet questioned
    QUESTIONED = "questioned"    # a why-question has been attached
    THEORIZED = "theorized"      # folded into a self-portrait
    TESTED = "tested"            # used as probe or prediction
    REVISED = "revised"          # contribution to the portrait revised


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CognitiveEvent:
    """A single observed cognitive event."""
    event_id: str
    description: str
    mode: CognitiveMode
    confidence: float = 0.5                # 0.0-1.0, how confident the agent was
    context: str = ""
    why_question: str = ""                 # the why-question attached in QUESTION
    theorized_link: str = ""               # which self-dimension it was tied to
    prediction_match: Optional[ProbeOutcome] = None
    state: EventState = EventState.OBSERVED
    created_at: float = field(default_factory=time.time)
    revised_at: Optional[float] = None


@dataclass
class SelfPortrait:
    """A theoretical self-portrait along multiple dimensions."""
    dimensions: Dict[SelfDimension, float] = field(default_factory=dict)
    coherence: float = 0.0                 # 0.0-1.0, how internally consistent
    confidence: float = 0.0                # 0.0-1.0, how confident the portrait is
    prediction_accuracy: float = 0.5       # 0.0-1.0, how well it has predicted probes
    total_probes: int = 0
    correct_probes: int = 0
    signature: str = ""                    # a phrase describing the portrait


@dataclass
class ProbeCase:
    """A probe used to test the self-portrait."""
    probe_id: str
    dimension: SelfDimension
    expected: float                        # 0.0-1.0, what the portrait predicted
    actual: float                          # 0.0-1.0, what actually happened
    outcome: ProbeOutcome = ProbeOutcome.NO_PREDICTION
    note: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class MetacognitiveAgent:
    """Per-agent metacognitive self-model state."""
    agent_id: str
    events: Dict[str, CognitiveEvent] = field(default_factory=dict)
    portrait: SelfPortrait = field(default_factory=SelfPortrait)
    probes: List[ProbeCase] = field(default_factory=list)
    maturity: SelfModelMaturity = SelfModelMaturity.UNFORMED
    introspection_bias: float = 0.5        # 0.0-1.0, how hard the agent looks inward
    total_observed: int = 0
    total_questioned: int = 0
    total_theorized: int = 0
    total_tested: int = 0
    total_revised: int = 0


# =============================================================================
# Self-Model
# =============================================================================

class AgentMetacognitiveSelfModel:
    """
    Thread-safe singleton orchestrating metacognitive self-modeling.

    Usage:
        model = AgentMetacognitiveSelfModel.get_instance()
        model.register_agent("strategist")
        model.observe_event("strategist", "e1",
                            "chose the cautious move under time pressure",
                            CognitiveMode.REACTIVE, confidence=0.6)
        model.cycle()
        state = model.get_agent_state("strategist")
    """

    _instance: Optional["AgentMetacognitiveSelfModel"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _QUESTION_DEPTH = 2                    # why-questions asked per event
    _THEORIZE_LINK_THRESHOLD = 0.3         # confidence needed to link a dimension
    _TEST_PROBE_COUNT = 3                  # probes per cycle
    _REVISE_ACCURACY_GAIN = 0.15           # confidence gained per correct probe
    _REVISE_ACCURACY_LOSS = 0.20           # confidence lost per wrong probe
    _MATURITY_THRESHOLD = 5                # tested events needed for SELF_AWARE
    _MAX_EVENTS_PER_AGENT = 80
    _MAX_PROBES_PER_AGENT = 120
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._agents: Dict[str, MetacognitiveAgent] = {}
        self._phase: MetacognitivePhase = MetacognitivePhase.OBSERVE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentMetacognitiveSelfModel":
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
            "total_events": 0,
            "total_observed": 0,
            "total_questioned": 0,
            "total_theorized": 0,
            "total_tested": 0,
            "total_revised": 0,
            "mature_models": 0,
            "avg_portrait_coherence": 0.0,
            "avg_prediction_accuracy": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._agents:
            return
        coherences: List[float] = []
        accuracies: List[float] = []
        for agent in self._agents.values():
            if agent.portrait.total_probes > 0:
                coherences.append(agent.portrait.coherence)
                accuracies.append(agent.portrait.prediction_accuracy)
        n = len(self._agents)
        self._stats["total_agents"] = n
        self._stats["mature_models"] = sum(
            1 for a in self._agents.values()
            if a.maturity in (SelfModelMaturity.COHERENT, SelfModelMaturity.SELF_AWARE)
        )
        self._stats["avg_portrait_coherence"] = (
            sum(coherences) / len(coherences) if coherences else 0.0
        )
        self._stats["avg_prediction_accuracy"] = (
            sum(accuracies) / len(accuracies) if accuracies else 0.0
        )

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
                       introspection_bias: float = 0.5) -> Dict[str, Any]:
        """Register a new agent for metacognitive self-modeling."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            agent = MetacognitiveAgent(
                agent_id=agent_id,
                introspection_bias=max(0.0, min(1.0, introspection_bias)),
            )
            self._agents[agent_id] = agent
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "maturity": agent.maturity.value,
                "introspection_bias": agent.introspection_bias,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.pop(agent_id, None)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            self._record_event("agent_removed", {"agent_id": agent_id})
            return {
                "removed": agent_id,
                "cleared_events": len(agent.events),
                "cleared_probes": len(agent.probes),
            }

    # -------------------------------------------------------------------------
    # Event Intake
    # -------------------------------------------------------------------------

    def observe_event(self, agent_id: str, event_id: str, description: str,
                      mode: CognitiveMode, confidence: float = 0.5,
                      context: str = "") -> Dict[str, Any]:
        """Record a cognitive event the agent observed in itself."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            if event_id in agent.events:
                return {"error": f"Event already exists: {event_id}"}
            event = CognitiveEvent(
                event_id=event_id,
                description=description,
                mode=mode,
                confidence=max(0.0, min(1.0, confidence)),
                context=context,
            )
            agent.events[event_id] = event
            if len(agent.events) > self._MAX_EVENTS_PER_AGENT:
                oldest = min(agent.events, key=lambda eid: agent.events[eid].created_at)
                agent.events.pop(oldest, None)
            self._stats["total_events"] += 1
            self._record_event("event_observed", {
                "agent_id": agent_id,
                "event_id": event_id,
                "mode": mode.value,
                "confidence": event.confidence,
            })
            return {
                "agent_id": agent_id,
                "event_id": event_id,
                "mode": mode.value,
                "state": event.state.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single metacognitive self-model cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = MetacognitivePhase.OBSERVE
            phase_outputs["observe"] = self._phase_observe()
            self._phase = MetacognitivePhase.QUESTION
            phase_outputs["question"] = self._phase_question()
            self._phase = MetacognitivePhase.THEORIZE
            phase_outputs["theorize"] = self._phase_theorize()
            self._phase = MetacognitivePhase.TEST
            phase_outputs["test"] = self._phase_test()
            self._phase = MetacognitivePhase.REVISE
            phase_outputs["revise"] = self._phase_revise()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_observe(self) -> Dict[str, Any]:
        """Observe phase: freshly captured events are confirmed as observed."""
        observed = 0
        for agent in self._agents.values():
            for event in agent.events.values():
                if event.state != EventState.OBSERVED:
                    continue
                # Observation stamps the event with a default context if missing.
                if not event.context:
                    event.context = "the agent's own stream of thought"
                # Introspection bias sharpens or softens the recorded confidence.
                sharpening = (agent.introspection_bias - 0.5) * 0.2
                event.confidence = max(0.0, min(1.0, event.confidence + sharpening))
                agent.total_observed += 1
                observed += 1
        self._stats["total_observed"] += observed
        self._record_event("phase_observe", {"observed": observed})
        return {"observed": observed}

    def _phase_question(self) -> Dict[str, Any]:
        """Question phase: attach why-questions to observed events."""
        questioned = 0
        for agent in self._agents.values():
            for event in agent.events.values():
                if event.state != EventState.OBSERVED:
                    continue
                # Ask a why-question shaped by the cognitive mode.
                event.why_question = self._compose_why(event)
                event.state = EventState.QUESTIONED
                agent.total_questioned += 1
                questioned += 1
        self._stats["total_questioned"] += questioned
        self._record_event("phase_question", {"questioned": questioned})
        return {"questioned": questioned}

    def _phase_theorize(self) -> Dict[str, Any]:
        """Theorize phase: draft or update a self-portrait from questioned events."""
        theorized = 0
        for agent in self._agents.values():
            portrait = agent.portrait
            for event in agent.events.values():
                if event.state != EventState.QUESTIONED:
                    continue
                # Link the event to a self-dimension it speaks to.
                dimension = self._link_dimension(event)
                event.theorized_link = dimension.value
                # Update the portrait along that dimension.
                current = portrait.dimensions.get(dimension, 0.5)
                # Deliberate/creative events push toward the high end of a dimension;
                # reactive/habitual events push toward the low end.
                push = self._dimensional_push(dimension, event)
                new_value = max(0.0, min(1.0, current * 0.7 + push * 0.3))
                portrait.dimensions[dimension] = new_value
                event.state = EventState.THEORIZED
                agent.total_theorized += 1
                theorized += 1
            # Recompute portrait coherence from dimension spread.
            portrait.coherence = self._compute_coherence(portrait)
            portrait.signature = self._derive_signature(agent)
        self._stats["total_theorized"] += theorized
        self._record_event("phase_theorize", {"theorized": theorized})
        return {"theorized": theorized}

    def _phase_test(self) -> Dict[str, Any]:
        """Test phase: probe the portrait against fresh cases."""
        tested = 0
        probes_added = 0
        for agent in self._agents.values():
            portrait = agent.portrait
            if not portrait.dimensions:
                continue
            # Synthesize a few probes against the strongest dimensions.
            sorted_dims = sorted(
                portrait.dimensions.items(),
                key=lambda kv: abs(kv[1] - 0.5),
                reverse=True,
            )
            for i in range(min(self._TEST_PROBE_COUNT, len(sorted_dims))):
                dimension, expected = sorted_dims[i]
                # The actual value is the expected value perturbed by introspection noise.
                noise = (random.random() - 0.5) * (1.0 - agent.introspection_bias) * 0.6
                actual = max(0.0, min(1.0, expected + noise))
                outcome = self._classify_outcome(expected, actual)
                probe = ProbeCase(
                    probe_id=f"probe_{dimension.value}_{self._cycle_count}_{i}",
                    dimension=dimension,
                    expected=expected,
                    actual=actual,
                    outcome=outcome,
                    note=self._probe_note(dimension, outcome),
                )
                agent.probes.append(probe)
                probes_added += 1
                portrait.total_probes += 1
                if outcome in (ProbeOutcome.CONFIRMED, ProbeOutcome.PARTIAL):
                    portrait.correct_probes += 1
                # Mark a theorized event as tested to feed the revise phase.
                for event in agent.events.values():
                    if event.state == EventState.THEORIZED and \
                       event.theorized_link == dimension.value:
                        event.prediction_match = outcome
                        event.state = EventState.TESTED
                        agent.total_tested += 1
                        tested += 1
                        break
            # Trim probes to the cap, dropping the oldest.
            if len(agent.probes) > self._MAX_PROBES_PER_AGENT:
                agent.probes = agent.probes[-self._MAX_PROBES_PER_AGENT:]
            # Update prediction accuracy.
            if portrait.total_probes > 0:
                portrait.prediction_accuracy = (
                    portrait.correct_probes / portrait.total_probes
                )
        self._stats["total_tested"] += tested
        self._record_event("phase_test", {
            "tested": tested,
            "probes_added": probes_added,
        })
        return {"tested": tested, "probes_added": probes_added}

    def _phase_revise(self) -> Dict[str, Any]:
        """Revise phase: rewrite the portrait where the probe broke it."""
        revised = 0
        for agent in self._agents.values():
            portrait = agent.portrait
            for event in list(agent.events.values()):
                if event.state != EventState.TESTED:
                    continue
                outcome = event.prediction_match or ProbeOutcome.NO_PREDICTION
                dimension = SelfDimension(event.theorized_link) \
                    if event.theorized_link else None
                if dimension is None:
                    continue
                current = portrait.dimensions.get(dimension, 0.5)
                if outcome == ProbeOutcome.REFUTED:
                    # Pull the dimension back toward neutral and lose confidence.
                    portrait.dimensions[dimension] = current * 0.6 + 0.5 * 0.4
                    portrait.confidence = max(0.0, portrait.confidence - self._REVISE_ACCURACY_LOSS)
                elif outcome == ProbeOutcome.CONFIRMED:
                    portrait.confidence = min(1.0, portrait.confidence + self._REVISE_ACCURACY_GAIN)
                elif outcome == ProbeOutcome.PARTIAL:
                    portrait.dimensions[dimension] = current * 0.85 + 0.5 * 0.15
                event.state = EventState.REVISED
                event.revised_at = time.time()
                agent.total_revised += 1
                revised += 1
            # Recompute coherence and signature after revision.
            portrait.coherence = self._compute_coherence(portrait)
            portrait.signature = self._derive_signature(agent)
            # Advance maturity based on cumulative tested events.
            if agent.total_tested >= self._MATURITY_THRESHOLD:
                agent.maturity = SelfModelMaturity.SELF_AWARE
            elif agent.total_tested >= 2:
                agent.maturity = SelfModelMaturity.COHERENT
            elif agent.total_theorized >= 1:
                agent.maturity = SelfModelMaturity.FRAGMENTARY
        self._stats["total_revised"] += revised
        self._record_event("phase_revise", {"revised": revised})
        return {"revised": revised}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _compose_why(self, event: CognitiveEvent) -> str:
        """Compose a why-question shaped by the cognitive mode."""
        templates = {
            CognitiveMode.DELIBERATE: f"why did I choose {event.description} so deliberately?",
            CognitiveMode.REACTIVE: f"why did {event.description} slip out before I weighed it?",
            CognitiveMode.IMITATIVE: f"why did I echo {event.description} instead of answering myself?",
            CognitiveMode.CREATIVE: f"why did {event.description} feel worth combining?",
            CognitiveMode.HABITUAL: f"why did I fall back on {event.description} without checking?",
        }
        return templates.get(event.mode, f"why did I do {event.description}?")

    def _link_dimension(self, event: CognitiveEvent) -> SelfDimension:
        """Link an event to the self-dimension it speaks to most."""
        # Mode -> dimension mapping, perturbed by event confidence.
        mapping = {
            CognitiveMode.DELIBERATE: SelfDimension.PATIENCE,
            CognitiveMode.REACTIVE: SelfDimension.BOLDNESS,
            CognitiveMode.IMITATIVE: SelfDimension.RIGIDITY,
            CognitiveMode.CREATIVE: SelfDimension.CURIOSITY,
            CognitiveMode.HABITUAL: SelfDimension.RIGIDITY,
        }
        dimension = mapping.get(event.mode, SelfDimension.DOUBT)
        # Low-confidence events speak more to doubt than the default mapping.
        if event.confidence < 0.3:
            dimension = SelfDimension.DOUBT
        return dimension

    def _dimensional_push(self, dimension: SelfDimension,
                          event: CognitiveEvent) -> float:
        """Compute the value a dimension should be pushed toward by an event."""
        # High confidence deliberate/creative events push the dimension up.
        # Low confidence reactive/habitual events push it down.
        base = event.confidence
        if event.mode in (CognitiveMode.DELIBERATE, CognitiveMode.CREATIVE):
            return 0.4 + base * 0.5
        if event.mode in (CognitiveMode.REACTIVE, CognitiveMode.HABITUAL):
            return 0.2 + base * 0.4
        if event.mode == CognitiveMode.IMITATIVE:
            return 0.3 + base * 0.3
        return 0.5

    def _compute_coherence(self, portrait: SelfPortrait) -> float:
        """Compute how internally consistent the portrait is."""
        if not portrait.dimensions:
            return 0.0
        values = list(portrait.dimensions.values())
        if len(values) == 1:
            return 0.5
        # Coherence rises when dimensions cluster rather than scatter.
        spread = max(values) - min(values)
        return max(0.0, min(1.0, 1.0 - spread))

    def _classify_outcome(self, expected: float, actual: float) -> ProbeOutcome:
        """Classify how a probe outcome compares to the portrait's prediction."""
        diff = abs(expected - actual)
        if diff < 0.1:
            return ProbeOutcome.CONFIRMED
        if diff < 0.25:
            return ProbeOutcome.PARTIAL
        return ProbeOutcome.REFUTED

    def _probe_note(self, dimension: SelfDimension,
                    outcome: ProbeOutcome) -> str:
        """Compose a short note for a probe case."""
        return f"probe on {dimension.value} came back {outcome.value}"

    def _derive_signature(self, agent: MetacognitiveAgent) -> str:
        """Derive a signature phrase for the agent's self-portrait."""
        portrait = agent.portrait
        if not portrait.dimensions:
            return "no portrait yet"
        # Find the dimension furthest from neutral.
        top_dim = max(
            portrait.dimensions,
            key=lambda d: abs(portrait.dimensions[d] - 0.5),
        )
        value = portrait.dimensions[top_dim]
        if value > 0.65:
            direction = "high"
        elif value < 0.35:
            direction = "low"
        else:
            direction = "mid"
        return f"{direction} {top_dim.value} self"

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent_id,
                "maturity": agent.maturity.value,
                "introspection_bias": agent.introspection_bias,
                "total_observed": agent.total_observed,
                "total_questioned": agent.total_questioned,
                "total_theorized": agent.total_theorized,
                "total_tested": agent.total_tested,
                "total_revised": agent.total_revised,
                "portrait": {
                    "dimensions": {
                        d.value: v for d, v in agent.portrait.dimensions.items()
                    },
                    "coherence": agent.portrait.coherence,
                    "confidence": agent.portrait.confidence,
                    "prediction_accuracy": agent.portrait.prediction_accuracy,
                    "total_probes": agent.portrait.total_probes,
                    "correct_probes": agent.portrait.correct_probes,
                    "signature": agent.portrait.signature,
                },
                "probes_count": len(agent.probes),
            }

    def get_event(self, agent_id: str, event_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            event = agent.events.get(event_id)
            if event is None:
                return {"error": f"Event not found: {event_id}"}
            return {
                "event_id": event.event_id,
                "description": event.description,
                "mode": event.mode.value,
                "confidence": event.confidence,
                "context": event.context,
                "why_question": event.why_question,
                "theorized_link": event.theorized_link,
                "prediction_match": event.prediction_match.value
                    if event.prediction_match else None,
                "state": event.state.value,
                "created_at": event.created_at,
                "revised_at": event.revised_at,
            }

    def get_events(self, agent_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            events = sorted(
                agent.events.values(),
                key=lambda e: e.created_at,
                reverse=True,
            )[:limit]
            return {
                "agent_id": agent_id,
                "events": [
                    {
                        "event_id": e.event_id,
                        "description": e.description,
                        "mode": e.mode.value,
                        "state": e.state.value,
                        "confidence": e.confidence,
                        "theorized_link": e.theorized_link,
                    }
                    for e in events
                ],
            }

    def get_probes(self, agent_id: str, limit: int = 30) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            probes = agent.probes[-limit:]
            return {
                "agent_id": agent_id,
                "probes": [
                    {
                        "probe_id": p.probe_id,
                        "dimension": p.dimension.value,
                        "expected": p.expected,
                        "actual": p.actual,
                        "outcome": p.outcome.value,
                        "note": p.note,
                    }
                    for p in probes
                ],
            }

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "agents": len(self._agents),
                "stats": dict(self._stats),
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic agents and events, then run multiple cycles."""
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
        """Seed a small synthetic cast of agents with distinct introspection styles."""
        seed_agents = [
            ("sim_deliberator", 0.7),
            ("im_reactor", 0.3),
            ("sim_imagineer", 0.8),
        ]
        for agent_id, bias in seed_agents:
            if agent_id in self._agents:
                continue
            self.register_agent(agent_id, introspection_bias=bias)
        # Seed shared cognitive events for each agent.
        seed_events = [
            ("sim_e1", "weighed three options before answering", CognitiveMode.DELIBERATE, 0.7, "a hard call"),
            ("sim_e2", "snapped a refusal before thinking", CognitiveMode.REACTIVE, 0.3, "a tense moment"),
            ("sim_e3", "echoed the older agent's plan", CognitiveMode.IMITATIVE, 0.5, "an uncertain turn"),
            ("sim_e4", "proposed a strange new move", CognitiveMode.CREATIVE, 0.6, "an open field"),
            ("sim_e5", "fell back on the usual opening", CognitiveMode.HABITUAL, 0.4, "a familiar board"),
            ("sim_e6", "re-checked the math a third time", CognitiveMode.DELIBERATE, 0.55, "a tricky sum"),
        ]
        for agent_id, _ in seed_agents:
            agent = self._agents.get(agent_id)
            if agent is None:
                continue
            for eid, desc, mode, conf, ctx in seed_events:
                if eid not in agent.events:
                    self.observe_event(agent_id, eid, desc, mode, confidence=conf, context=ctx)

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._agents.clear()
            self._events_log.clear()
            self._phase = MetacognitivePhase.OBSERVE
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
