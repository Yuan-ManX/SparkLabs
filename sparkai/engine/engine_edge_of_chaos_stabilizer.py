"""
SparkLabs Engine - Edge-of-Chaos Stabilizer

The EngineEdgeOfChaosStabilizer models how a living system holds itself
at the boundary between rigid order and formless noise. Complexity
flourishes neither in frozen stasis nor in dissolving chaos, but on the
narrow edge between them - the edge of chaos, where information is rich
enough to compute and flexible enough to evolve.

Each observed system (an agent's behavior, a narrative arc, a combat
exchange, a world simulation) has an entropy signature. The stabilizer
senses that entropy, classifies it against the order-chaos spectrum,
damps it when it grows too volatile, amplifies it when it grows too
rigid, and recenters it on the edge where emergence is most likely.

Architecture:
  SENSE     ->  ENTROPY    ->  DAMP      ->  AMPLIFY   ->  RECENTER
  (raw       (the entropy   (chaotic       (ordered      (the system is
   signals   is classified  deviations     deviations    pulled back
   are       on the order-  are damped     are amplified toward the
   gathered) chaos          toward         toward        edge where
             spectrum)      stability)     variation)    emergence
                                            lives)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import math
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

class ChaosPhase(Enum):
    """Phases of the edge-of-chaos stabilization cycle."""
    SENSE = "sense"            # raw entropy signals are gathered
    ENTROPY = "entropy"        # entropy is classified on the spectrum
    DAMP = "damp"              # chaotic deviations are damped
    AMPLIFY = "amplify"        # ordered deviations are amplified
    RECENTER = "recenter"      # the system is pulled back toward the edge


class SystemDomain(Enum):
    """Domains of a system whose entropy can be stabilized."""
    NARRATIVE = "narrative"    # story coherence vs chaos
    BEHAVIOR = "behavior"      # agent behavior predictability vs novelty
    DIALOGUE = "dialogue"      # conversation focus vs divergence
    EMOTION = "emotion"        # emotional range vs flatness
    WORLD = "world"            # world simulation order vs noise
    COMBAT = "combat"          # combat determinism vs chaos
    PUZZLE = "puzzle"          # puzzle structure vs openness
    AGENT = "agent"            # whole-agent integration


class EntropyState(Enum):
    """Classification of a system's current entropy."""
    FROZEN = "frozen"          # too ordered, no variation
    ORDERED = "ordered"        # mostly stable, slight variation
    EDGE = "edge"              # balanced, edge of chaos
    CHAOTIC = "chaotic"        # mostly volatile
    DISSOLVING = "dissolving"  # too chaotic, structure dissolving


class StabilizerMode(Enum):
    """How aggressively the stabilizer intervenes."""
    PASSIVE = "passive"        # only sense, do not intervene
    ACTIVE = "active"          # damp and amplify as needed
    AGGRESSIVE = "aggressive"  # strong recentering force


class SampleState(Enum):
    """State of an individual entropy sample."""
    PENDING = "pending"        # introduced, not yet sensed
    SENSED = "sensed"          # gathered into the rolling window
    CLASSIFIED = "classified"  # entropy state assigned
    DAMPED = "damped"          # damping intervention applied
    AMPLIFIED = "amplified"    # amplification intervention applied
    RECENTERED = "recentered"  # recentering intervention applied


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class EntropySample:
    """A single observation of a system's entropy."""
    sample_id: str
    observed_entropy: float              # 0.0 (frozen) - 1.0 (dissolving)
    volatility: float = 0.3              # 0.0-1.0, how much entropy is swinging
    domain: SystemDomain = SystemDomain.AGENT
    context: str = ""
    state: SampleState = SampleState.PENDING
    classified_as: EntropyState = EntropyState.EDGE
    intervention: float = 0.0            # -1.0 (damp) to +1.0 (amplify)
    edge_drift: float = 0.0              # distance from the target edge
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None


@dataclass
class EntropyWindow:
    """Rolling window of recent entropy observations."""
    samples: Deque[EntropySample] = field(default_factory=lambda: deque(maxlen=20))
    mean_entropy: float = 0.5
    mean_volatility: float = 0.3
    trend: float = 0.0                    # -1.0 (cooling) to +1.0 (heating)


@dataclass
class StabilizerAgent:
    """Per-agent (or per-system) stabilization state."""
    agent_id: str
    domain: SystemDomain
    target_entropy: float = 0.5           # the edge this agent targets
    mode: StabilizerMode = StabilizerMode.ACTIVE
    window: EntropyWindow = field(default_factory=EntropyWindow)
    samples: Dict[str, EntropySample] = field(default_factory=dict)
    current_state: EntropyState = EntropyState.EDGE
    total_sensed: int = 0
    total_damped: int = 0
    total_amplified: int = 0
    total_recentered: int = 0
    stability_score: float = 0.5          # 0.0-1.0, how settled on the edge
    last_intervention: float = 0.0


# =============================================================================
# Stabilizer
# =============================================================================

class EngineEdgeOfChaosStabilizer:
    """
    Thread-safe singleton orchestrating edge-of-chaos stabilization.

    Usage:
        stabilizer = EngineEdgeOfChaosStabilizer.get_instance()
        stabilizer.register_agent("narrator", SystemDomain.NARRATIVE,
                                  target_entropy=0.5, mode=StabilizerMode.ACTIVE)
        stabilizer.sense("narrator", "s1", observed_entropy=0.85,
                         volatility=0.4, context="mid-act twist")
        stabilizer.cycle()
        state = stabilizer.get_agent_state("narrator")
    """

    _instance: Optional["EngineEdgeOfChaosStabilizer"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _EDGE_TARGET = 0.5                    # the canonical edge of chaos
    _EDGE_TOLERANCE = 0.1                 # within this distance, still EDGE
    _FROZEN_THRESHOLD = 0.2               # below this, FROZEN
    _ORDERED_THRESHOLD = 0.4              # below this, ORDERED
    _CHAOTIC_THRESHOLD = 0.7              # above this, CHAOTIC
    _DISSOLVING_THRESHOLD = 0.85          # above this, DISSOLVING
    _DAMP_STRENGTH = 0.15                 # how strongly damping pulls down
    _AMPLIFY_STRENGTH = 0.15              # how strongly amplification pushes up
    _RECENTER_STRENGTH = 0.2              # how strongly recentering pulls to edge
    _MAX_SAMPLES_PER_AGENT = 100
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._agents: Dict[str, StabilizerAgent] = {}
        self._phase: ChaosPhase = ChaosPhase.SENSE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineEdgeOfChaosStabilizer":
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
            "total_samples": 0,
            "total_sensed": 0,
            "total_damped": 0,
            "total_amplified": 0,
            "total_recentered": 0,
            "agents_on_edge": 0,
            "avg_stability_score": 0.0,
            "avg_edge_drift": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._agents:
            return
        n = len(self._agents)
        self._stats["total_agents"] = n
        self._stats["agents_on_edge"] = sum(
            1 for a in self._agents.values() if a.current_state == EntropyState.EDGE
        )
        self._stats["avg_stability_score"] = sum(a.stability_score for a in self._agents.values()) / n
        # Average drift from the edge across the most recent resolved samples.
        drifts: List[float] = []
        for agent in self._agents.values():
            for sample in agent.samples.values():
                if sample.state == SampleState.RECENTERED:
                    drifts.append(abs(sample.edge_drift))
        self._stats["avg_edge_drift"] = sum(drifts) / len(drifts) if drifts else 0.0

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

    def register_agent(self, agent_id: str, domain: SystemDomain,
                       target_entropy: float = 0.5,
                       mode: StabilizerMode = StabilizerMode.ACTIVE) -> Dict[str, Any]:
        """Register a new agent for edge-of-chaos stabilization."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            agent = StabilizerAgent(
                agent_id=agent_id,
                domain=domain,
                target_entropy=max(0.0, min(1.0, target_entropy)),
                mode=mode,
            )
            self._agents[agent_id] = agent
            self._record_event("agent_registered", {
                "agent_id": agent_id,
                "domain": domain.value,
                "target_entropy": agent.target_entropy,
                "mode": mode.value,
            })
            return {
                "agent_id": agent_id,
                "domain": domain.value,
                "target_entropy": agent.target_entropy,
                "mode": mode.value,
                "current_state": agent.current_state.value,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.pop(agent_id, None)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            self._record_event("agent_removed", {"agent_id": agent_id})
            return {
                "removed": agent_id,
                "cleared_samples": len(agent.samples),
            }

    # -------------------------------------------------------------------------
    # Sample Intake
    # -------------------------------------------------------------------------

    def sense(self, agent_id: str, sample_id: str, observed_entropy: float,
              volatility: float = 0.3,
              domain: Optional[SystemDomain] = None,
              context: str = "") -> Dict[str, Any]:
        """Introduce a new entropy observation for an agent."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            if sample_id in agent.samples:
                return {"error": f"Sample already exists: {sample_id}"}
            sample = EntropySample(
                sample_id=sample_id,
                observed_entropy=max(0.0, min(1.0, observed_entropy)),
                volatility=max(0.0, min(1.0, volatility)),
                domain=domain or agent.domain,
                context=context,
            )
            agent.samples[sample_id] = sample
            if len(agent.samples) > self._MAX_SAMPLES_PER_AGENT:
                oldest = min(agent.samples, key=lambda sid: agent.samples[sid].created_at)
                agent.samples.pop(oldest, None)
            self._stats["total_samples"] += 1
            self._record_event("sample_sensed", {
                "agent_id": agent_id,
                "sample_id": sample_id,
                "observed_entropy": sample.observed_entropy,
                "volatility": sample.volatility,
            })
            return {
                "agent_id": agent_id,
                "sample_id": sample_id,
                "observed_entropy": sample.observed_entropy,
                "state": sample.state.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single edge-of-chaos stabilization cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = ChaosPhase.SENSE
            phase_outputs["sense"] = self._phase_sense()
            self._phase = ChaosPhase.ENTROPY
            phase_outputs["entropy"] = self._phase_entropy()
            self._phase = ChaosPhase.DAMP
            phase_outputs["damp"] = self._phase_damp()
            self._phase = ChaosPhase.AMPLIFY
            phase_outputs["amplify"] = self._phase_amplify()
            self._phase = ChaosPhase.RECENTER
            phase_outputs["recenter"] = self._phase_recenter()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_sense(self) -> Dict[str, Any]:
        """Sense phase: pending samples enter the rolling window."""
        sensed = 0
        for agent in self._agents.values():
            for sample in agent.samples.values():
                if sample.state != SampleState.PENDING:
                    continue
                agent.window.samples.append(sample)
                agent.total_sensed += 1
                sample.state = SampleState.SENSED
                sensed += 1
            # Recompute window aggregates whenever new samples arrive.
            if agent.window.samples:
                entropies = [s.observed_entropy for s in agent.window.samples]
                volatilities = [s.volatility for s in agent.window.samples]
                prev_mean = agent.window.mean_entropy
                agent.window.mean_entropy = sum(entropies) / len(entropies)
                agent.window.mean_volatility = sum(volatilities) / len(volatilities)
                # Trend: how the mean moved relative to the previous mean.
                if len(entropies) >= 2:
                    agent.window.trend = max(-1.0, min(1.0, agent.window.mean_entropy - prev_mean))
        self._stats["total_sensed"] += sensed
        self._record_event("phase_sense", {"sensed": sensed})
        return {"sensed": sensed}

    def _phase_entropy(self) -> Dict[str, Any]:
        """Entropy phase: classify each sensed sample on the order-chaos spectrum."""
        classified = 0
        for agent in self._agents.values():
            for sample in agent.samples.values():
                if sample.state != SampleState.SENSED:
                    continue
                sample.classified_as = self._classify_entropy(
                    sample.observed_entropy, agent.target_entropy,
                )
                # Edge drift: distance from the agent's target edge.
                sample.edge_drift = sample.observed_entropy - agent.target_entropy
                sample.state = SampleState.CLASSIFIED
                classified += 1
            # Update the agent's current state from the rolling mean.
            if agent.window.samples:
                agent.current_state = self._classify_entropy(
                    agent.window.mean_entropy, agent.target_entropy,
                )
        self._record_event("phase_entropy", {"classified": classified})
        return {"classified": classified}

    def _phase_damp(self) -> Dict[str, Any]:
        """Damp phase: chaotic deviations are pulled back toward stability."""
        damped = 0
        for agent in self._agents.values():
            if agent.mode == StabilizerMode.PASSIVE:
                continue
            for sample in agent.samples.values():
                if sample.state != SampleState.CLASSIFIED:
                    continue
                if sample.classified_as not in (EntropyState.CHAOTIC, EntropyState.DISSOLVING):
                    continue
                # Strength scales with how far past the chaotic threshold.
                overflow = max(0.0, sample.observed_entropy - self._CHAOTIC_THRESHOLD)
                strength = self._DAMP_STRENGTH * (0.5 + overflow * 2.0)
                if agent.mode == StabilizerMode.AGGRESSIVE:
                    strength *= 1.5
                sample.intervention = -min(1.0, strength)
                sample.observed_entropy = max(
                    0.0, sample.observed_entropy + sample.intervention,
                )
                sample.state = SampleState.DAMPED
                agent.total_damped += 1
                agent.last_intervention = sample.intervention
                damped += 1
        self._stats["total_damped"] += damped
        self._record_event("phase_damp", {"damped": damped})
        return {"damped": damped}

    def _phase_amplify(self) -> Dict[str, Any]:
        """Amplify phase: ordered deviations are pushed toward variation."""
        amplified = 0
        for agent in self._agents.values():
            if agent.mode == StabilizerMode.PASSIVE:
                continue
            for sample in agent.samples.values():
                if sample.state != SampleState.CLASSIFIED:
                    continue
                if sample.classified_as not in (EntropyState.FROZEN, EntropyState.ORDERED):
                    continue
                # Strength scales with how far below the ordered threshold.
                underflow = max(0.0, self._ORDERED_THRESHOLD - sample.observed_entropy)
                strength = self._AMPLIFY_STRENGTH * (0.5 + underflow * 2.0)
                if agent.mode == StabilizerMode.AGGRESSIVE:
                    strength *= 1.5
                sample.intervention = min(1.0, strength)
                sample.observed_entropy = min(
                    1.0, sample.observed_entropy + sample.intervention,
                )
                sample.state = SampleState.AMPLIFIED
                agent.total_amplified += 1
                agent.last_intervention = sample.intervention
                amplified += 1
        self._stats["total_amplified"] += amplified
        self._record_event("phase_amplify", {"amplified": amplified})
        return {"amplified": amplified}

    def _phase_recenter(self) -> Dict[str, Any]:
        """Recenter phase: pull every damped/amplified sample back toward the edge."""
        recentered = 0
        for agent in self._agents.values():
            if agent.mode == StabilizerMode.PASSIVE:
                # Even passive agents mark samples as recentered without intervention.
                for sample in agent.samples.values():
                    if sample.state in (SampleState.DAMPED, SampleState.AMPLIFIED, SampleState.CLASSIFIED):
                        sample.state = SampleState.RECENTERED
                        sample.resolved_at = time.time()
                        recentered += 1
                continue
            for sample in agent.samples.values():
                if sample.state not in (SampleState.DAMPED, SampleState.AMPLIFIED, SampleState.CLASSIFIED):
                    continue
                # Recenter force: proportional to remaining drift from target.
                drift = agent.target_entropy - sample.observed_entropy
                force = max(-1.0, min(1.0, drift * self._RECENTER_STRENGTH * 2.0))
                if agent.mode == StabilizerMode.AGGRESSIVE:
                    force *= 1.3
                sample.intervention = max(-1.0, min(1.0, sample.intervention + force))
                sample.observed_entropy = max(
                    0.0, min(1.0, sample.observed_entropy + force),
                )
                # Edge drift after recentering.
                sample.edge_drift = sample.observed_entropy - agent.target_entropy
                sample.state = SampleState.RECENTERED
                sample.resolved_at = time.time()
                agent.total_recentered += 1
                recentered += 1
            # Update stability score: how close the rolling mean is to the target.
            if agent.window.samples:
                drift = abs(agent.window.mean_entropy - agent.target_entropy)
                agent.stability_score = max(0.0, min(1.0, 1.0 - drift * 2.0))
            # Reclassify current state after recentering.
            if agent.window.samples:
                agent.current_state = self._classify_entropy(
                    agent.window.mean_entropy, agent.target_entropy,
                )
        self._stats["total_recentered"] += recentered
        self._record_event("phase_recenter", {"recentered": recentered})
        return {"recentered": recentered}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _classify_entropy(self, observed: float, target: float) -> EntropyState:
        """Classify an entropy reading on the order-chaos spectrum.

        Classification is relative to the agent's target edge so that an
        agent whose target is shifted (say toward more order for a puzzle
        domain) still gets meaningful state labels.
        """
        drift = observed - target
        # Absolute spectrum bands first.
        if observed < self._FROZEN_THRESHOLD:
            return EntropyState.FROZEN
        if observed < self._ORDERED_THRESHOLD:
            return EntropyState.ORDERED
        if observed > self._DISSOLVING_THRESHOLD:
            return EntropyState.DISSOLVING
        if observed > self._CHAOTIC_THRESHOLD:
            return EntropyState.CHAOTIC
        # Within the broad middle band, classify relative to the target edge.
        if abs(drift) <= self._EDGE_TOLERANCE:
            return EntropyState.EDGE
        if drift < 0:
            return EntropyState.ORDERED
        return EntropyState.CHAOTIC

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
                "domain": agent.domain.value,
                "target_entropy": agent.target_entropy,
                "mode": agent.mode.value,
                "current_state": agent.current_state.value,
                "stability_score": agent.stability_score,
                "last_intervention": agent.last_intervention,
                "window": {
                    "sample_count": len(agent.window.samples),
                    "mean_entropy": agent.window.mean_entropy,
                    "mean_volatility": agent.window.mean_volatility,
                    "trend": agent.window.trend,
                },
                "total_sensed": agent.total_sensed,
                "total_damped": agent.total_damped,
                "total_amplified": agent.total_amplified,
                "total_recentered": agent.total_recentered,
            }

    def get_sample(self, agent_id: str, sample_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            sample = agent.samples.get(sample_id)
            if sample is None:
                return {"error": f"Sample not found: {sample_id}"}
            return {
                "sample_id": sample.sample_id,
                "observed_entropy": sample.observed_entropy,
                "volatility": sample.volatility,
                "domain": sample.domain.value,
                "context": sample.context,
                "state": sample.state.value,
                "classified_as": sample.classified_as.value,
                "intervention": sample.intervention,
                "edge_drift": sample.edge_drift,
                "created_at": sample.created_at,
                "resolved_at": sample.resolved_at,
            }

    def get_samples(self, agent_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            samples = sorted(
                agent.samples.values(),
                key=lambda s: s.created_at,
                reverse=True,
            )[:limit]
            return {
                "agent_id": agent_id,
                "samples": [
                    {
                        "sample_id": s.sample_id,
                        "observed_entropy": s.observed_entropy,
                        "volatility": s.volatility,
                        "state": s.state.value,
                        "classified_as": s.classified_as.value,
                        "intervention": s.intervention,
                        "edge_drift": s.edge_drift,
                    }
                    for s in samples
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
        """Seed synthetic agents and entropy samples, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_agents()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                # Each simulated cycle, push a fresh wave of samples in.
                self._seed_wave()
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_agents(self) -> None:
        """Seed a small synthetic cast of agents across diverse domains."""
        seed_agents = [
            ("sim_narrator", SystemDomain.NARRATIVE, 0.5, StabilizerMode.ACTIVE),
            ("sim_combat", SystemDomain.COMBAT, 0.6, StabilizerMode.AGGRESSIVE),
            ("sim_puzzle", SystemDomain.PUZZLE, 0.35, StabilizerMode.ACTIVE),
        ]
        for agent_id, domain, target, mode in seed_agents:
            if agent_id in self._agents:
                continue
            self.register_agent(agent_id, domain, target_entropy=target, mode=mode)

    def _seed_wave(self) -> None:
        """Push a fresh wave of entropy samples into each agent."""
        for agent_id, agent in self._agents.items():
            # Bias samples toward the agent's typical operating band,
            # with occasional excursions to keep the stabilizer busy.
            base = agent.target_entropy
            for i in range(3):
                excursion = random.gauss(0.0, 0.18)
                observed = max(0.0, min(1.0, base + excursion))
                volatility = max(0.0, min(1.0, abs(excursion) * 1.5))
                sid = f"{agent_id}_wave_{self._cycle_count}_{i}_{random.randint(0,9999)}"
                if sid not in agent.samples:
                    self.sense(
                        agent_id, sid, observed_entropy=observed,
                        volatility=volatility,
                        context=f"simulated wave cycle {self._cycle_count}",
                    )

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._agents.clear()
            self._events_log.clear()
            self._phase = ChaosPhase.SENSE
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
