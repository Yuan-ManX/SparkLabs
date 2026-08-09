"""
SparkLabs Engine - Silence Architecture Composer"""

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

class SilencePhase(Enum):
    """Phases of the silence architecture cycle."""
    HUSH = "hush"                # a silence enters the agent's acoustic space
    SUSPEND = "suspend"          # the silence suspends the current flow
    RESONATE = "resonate"        # the silence resonates with meaning
    DISSOLVE = "dissolve"        # the silence dissolves or persists
    ACCRUE = "accrue"            # accrued silence shapes voice architecture


class SilenceType(Enum):
    """Types of silence an agent can produce or encounter."""
    CAESURA = "caesura"          # a dramatic pause inside a phrase
    ELLIPSIS = "ellipsis"        # trailing off, the unsaid
    HESITATION = "hesitation"    # uncertainty, searching for words
    REVERENCE = "reverence"      # ceremonial, honorific silence
    DEFIANCE = "defiance"        # refusal to speak
    GRIEF = "grief"              # mourning, too heavy to utter
    ANTICIPATION = "anticipation"  # building tension before a beat
    ABSENCE = "absence"          # empty silence, void of intent


class SilenceFunction(Enum):
    """Functions a silence performs in the architecture of meaning."""
    STRUCTURAL = "structural"    # organizes the shape of discourse
    EMOTIONAL = "emotional"      # carries an emotional charge
    RHETORICAL = "rhetorical"    # persuasive, draws attention
    REGULATIVE = "regulative"    # governs turn-taking and pacing
    SYMBOLIC = "symbolic"        # represents absence itself


class SilenceState(Enum):
    """State of an individual silence moment."""
    PENDING = "pending"          # introduced, not yet suspended
    SUSPENDED = "suspended"      # the flow is paused
    RESONATING = "resonating"    # being interpreted for meaning
    DISSOLVED = "dissolved"      # released back into sound
    PERSISTED = "persisted"      # held as absence
    ACCRUED = "accrued"          # folded into voice architecture


class VoiceArchitecture(Enum):
    """The overall shape of an agent's silence practice."""
    SPARSE = "sparse"            # few pauses, dense speech
    MODERATE = "moderate"        # balanced cadence
    DENSE = "dense"              # frequent pauses, broken speech
    CATHEDRAL = "cathedral"      # long reverent silences
    STACCATO = "staccato"        # short sharp pauses
    UNFORMED = "unformed"        # insufficient accrued silence


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SilenceMoment:
    """A single moment of silence introduced into an agent's flow."""
    silence_id: str
    silence_type: SilenceType
    function: SilenceFunction
    duration_ms: int = 500                # how long the silence lasts
    intensity: float = 0.5                # 0.0-1.0, how weighty
    context: str = ""
    state: SilenceState = SilenceState.PENDING
    resonance: float = 0.0                # 0.0-1.0, interpreted weight
    interpretation: str = ""
    persisted: bool = False               # whether it remained as absence
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None


@dataclass
class SilenceReading:
    """An interpretation of a silence's function and meaning."""
    function: SilenceFunction
    resonance: float = 0.0                # how strongly this reading applies
    meaning: str = ""


@dataclass
class SilenceAccretion:
    """The accrued shape of silence in an agent's voice."""
    total_duration_ms: int = 0
    total_moments: int = 0
    function_weights: Dict[SilenceFunction, float] = field(default_factory=dict)
    type_weights: Dict[SilenceType, float] = field(default_factory=dict)
    signature_pattern: str = ""           # a phrase describing the cadence
    persistence_rate: float = 0.0         # 0.0-1.0, how often silence persists


@dataclass
class SilenceAgent:
    """Per-agent silence architecture state."""
    agent_id: str
    moments: Dict[str, SilenceMoment] = field(default_factory=dict)
    accretion: SilenceAccretion = field(default_factory=SilenceAccretion)
    architecture: VoiceArchitecture = VoiceArchitecture.UNFORMED
    default_function: SilenceFunction = SilenceFunction.STRUCTURAL
    silence_tolerance: float = 0.5        # 0.0-1.0, comfort with silence
    flow_pressure: float = 0.5            # 0.0-1.0, pressure to keep speaking
    total_introduced: int = 0
    total_dissolved: int = 0
    total_persisted: int = 0
    total_accrued: int = 0


# =============================================================================
# Composer
# =============================================================================

class EngineSilenceArchitectureComposer:
    """
    Thread-safe singleton orchestrating silence architecture composition.

    Usage:
        composer = EngineSilenceArchitectureComposer.get_instance()
        composer.register_agent("narrator")
        composer.introduce_silence(
            "narrator", "s1", SilenceType.CAESURA, SilenceFunction.STRUCTURAL,
            duration_ms=1200, intensity=0.7, context="before the verdict",
        )
        composer.cycle()
        state = composer.get_agent_state("narrator")
    """

    _instance: Optional["EngineSilenceArchitectureComposer"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _SUSPEND_FLOW_THRESHOLD = 0.3         # intensity needed to actually suspend
    _RESONATE_BASE_GAIN = 0.15            # base resonance per active moment
    _DISSOLVE_PERSISTENCE_BIAS = 0.4      # higher = more silences persist
    _ACCRUE_PATTERN_THRESHOLD = 4         # accrued moments needed for pattern
    _ACCRUE_ARCHITECTURE_THRESHOLD = 6    # accrued moments needed for shape
    _MAX_MOMENTS_PER_AGENT = 100
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._agents: Dict[str, SilenceAgent] = {}
        self._phase: SilencePhase = SilencePhase.HUSH
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineSilenceArchitectureComposer":
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
            "total_silences": 0,
            "total_suspended": 0,
            "total_resonated": 0,
            "total_dissolved": 0,
            "total_persisted": 0,
            "total_accrued": 0,
            "formed_architectures": 0,
            "avg_resonance": 0.0,
            "avg_persistence_rate": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._agents:
            return
        resonances: List[float] = []
        persistence_rates: List[float] = []
        for agent in self._agents.values():
            for moment in agent.moments.values():
                if moment.state in (SilenceState.DISSOLVED, SilenceState.PERSISTED, SilenceState.ACCRUED):
                    resonances.append(moment.resonance)
            persistence_rates.append(agent.accretion.persistence_rate)
        self._stats["total_agents"] = len(self._agents)
        self._stats["formed_architectures"] = sum(
            1 for a in self._agents.values() if a.architecture != VoiceArchitecture.UNFORMED
        )
        self._stats["avg_resonance"] = sum(resonances) / len(resonances) if resonances else 0.0
        self._stats["avg_persistence_rate"] = (
            sum(persistence_rates) / len(persistence_rates) if persistence_rates else 0.0
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
                       default_function: SilenceFunction = SilenceFunction.STRUCTURAL,
                       silence_tolerance: float = 0.5,
                       flow_pressure: float = 0.5) -> Dict[str, Any]:
        """Register a new agent for silence architecture composition."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            agent = SilenceAgent(
                agent_id=agent_id,
                default_function=default_function,
                silence_tolerance=max(0.0, min(1.0, silence_tolerance)),
                flow_pressure=max(0.0, min(1.0, flow_pressure)),
            )
            self._agents[agent_id] = agent
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "architecture": agent.architecture.value,
                "default_function": agent.default_function.value,
                "silence_tolerance": agent.silence_tolerance,
                "flow_pressure": agent.flow_pressure,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.pop(agent_id, None)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            self._record_event("agent_removed", {"agent_id": agent_id})
            return {
                "removed": agent_id,
                "cleared_moments": len(agent.moments),
                "accrued_moments": agent.accretion.total_moments,
            }

    # -------------------------------------------------------------------------
    # Silence Intake
    # -------------------------------------------------------------------------

    def introduce_silence(self, agent_id: str, silence_id: str,
                          silence_type: SilenceType, function: SilenceFunction,
                          duration_ms: int = 500, intensity: float = 0.5,
                          context: str = "") -> Dict[str, Any]:
        """Introduce a new moment of silence into an agent's flow."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            if silence_id in agent.moments:
                return {"error": f"Silence already exists: {silence_id}"}
            moment = SilenceMoment(
                silence_id=silence_id,
                silence_type=silence_type,
                function=function,
                duration_ms=max(0, int(duration_ms)),
                intensity=max(0.0, min(1.0, intensity)),
                context=context,
            )
            agent.moments[silence_id] = moment
            if len(agent.moments) > self._MAX_MOMENTS_PER_AGENT:
                oldest = min(agent.moments, key=lambda sid: agent.moments[sid].created_at)
                agent.moments.pop(oldest, None)
            agent.total_introduced += 1
            self._stats["total_silences"] += 1
            self._record_event("silence_introduced", {
                "agent_id": agent_id,
                "silence_id": silence_id,
                "type": silence_type.value,
                "function": function.value,
                "duration_ms": moment.duration_ms,
                "intensity": moment.intensity,
            })
            return {
                "agent_id": agent_id,
                "silence_id": silence_id,
                "type": silence_type.value,
                "function": function.value,
                "state": moment.state.value,
                "duration_ms": moment.duration_ms,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single silence architecture cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = SilencePhase.HUSH
            phase_outputs["hush"] = self._phase_hush()
            self._phase = SilencePhase.SUSPEND
            phase_outputs["suspend"] = self._phase_suspend()
            self._phase = SilencePhase.RESONATE
            phase_outputs["resonate"] = self._phase_resonate()
            self._phase = SilencePhase.DISSOLVE
            phase_outputs["dissolve"] = self._phase_dissolve()
            self._phase = SilencePhase.ACCRUE
            phase_outputs["accrue"] = self._phase_accrue()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_hush(self) -> Dict[str, Any]:
        """Hush phase: pending silences become suspended-ready."""
        activated = 0
        for agent in self._agents.values():
            for moment in agent.moments.values():
                if moment.state == SilenceState.PENDING:
                    # A silence only hushes if it overcomes the agent's flow pressure.
                    if moment.intensity >= self._SUSPEND_FLOW_THRESHOLD or \
                       moment.intensity >= agent.flow_pressure:
                        moment.state = SilenceState.SUSPENDED
                        activated += 1
                    else:
                        # Too weak to suspend - immediately dissolved as no-op.
                        moment.state = SilenceState.DISSOLVED
                        moment.interpretation = "too faint to suspend the flow"
                        moment.resolved_at = time.time()
        self._record_event("phase_hush", {"activated": activated})
        return {"activated": activated}

    def _phase_suspend(self) -> Dict[str, Any]:
        """Suspend phase: suspended silences hold the flow open."""
        suspended = 0
        for agent in self._agents.values():
            for moment in agent.moments.values():
                if moment.state != SilenceState.SUSPENDED:
                    continue
                # Longer and more intense silences suspend more strongly.
                # The agent's tolerance increases the effective suspension.
                effective = moment.intensity * (0.5 + agent.silence_tolerance * 0.5)
                moment.resonance = min(1.0, effective + (moment.duration_ms / 5000.0))
                moment.state = SilenceState.RESONATING
                suspended += 1
        self._stats["total_suspended"] += suspended
        self._record_event("phase_suspend", {"suspended": suspended})
        return {"suspended": suspended}

    def _phase_resonate(self) -> Dict[str, Any]:
        """Resonate phase: each silence is interpreted by its function."""
        resonated = 0
        for agent in self._agents.values():
            for moment in agent.moments.values():
                if moment.state != SilenceState.RESONATING:
                    continue
                reading = self._interpret_silence(moment, agent)
                # Resonance grows with how well the function matches the type.
                moment.resonance = min(1.0, moment.resonance + reading.resonance)
                moment.interpretation = reading.meaning
                resonated += 1
        self._stats["total_resonated"] += resonated
        self._record_event("phase_resonate", {"resonated": resonated})
        return {"resonated": resonated}

    def _phase_dissolve(self) -> Dict[str, Any]:
        """Dissolve phase: silences either dissolve or persist as absence."""
        dissolved = 0
        persisted = 0
        for agent in self._agents.values():
            for moment in agent.moments.values():
                if moment.state != SilenceState.RESONATING:
                    continue
                # Persistence bias: high resonance + low tolerance = persists.
                persistence_chance = (
                    self._DISSOLVE_PERSISTENCE_BIAS
                    + moment.resonance * 0.4
                    - agent.silence_tolerance * 0.2
                )
                if random.random() < max(0.0, min(1.0, persistence_chance)):
                    moment.persisted = True
                    moment.state = SilenceState.PERSISTED
                    persisted += 1
                else:
                    moment.state = SilenceState.DISSOLVED
                    dissolved += 1
                moment.resolved_at = time.time()
        self._stats["total_dissolved"] += dissolved
        self._stats["total_persisted"] += persisted
        self._record_event("phase_dissolve", {
            "dissolved": dissolved,
            "persisted": persisted,
        })
        return {"dissolved": dissolved, "persisted": persisted}

    def _phase_accrue(self) -> Dict[str, Any]:
        """Accrue phase: resolved silences fold into the agent's voice architecture."""
        accrued = 0
        for agent in self._agents.values():
            for moment in list(agent.moments.values()):
                if moment.state not in (SilenceState.DISSOLVED, SilenceState.PERSISTED):
                    continue
                # Fold this moment into the accretion.
                acc = agent.accretion
                acc.total_duration_ms += moment.duration_ms
                acc.total_moments += 1
                acc.function_weights[moment.function] = (
                    acc.function_weights.get(moment.function, 0.0) + moment.resonance
                )
                acc.type_weights[moment.silence_type] = (
                    acc.type_weights.get(moment.silence_type, 0.0) + 1.0
                )
                if moment.persisted:
                    acc.persistence_rate = (
                        (acc.persistence_rate * (acc.total_moments - 1) + 1.0)
                        / acc.total_moments
                    )
                else:
                    acc.persistence_rate = (
                        acc.persistence_rate * (acc.total_moments - 1)
                        / acc.total_moments
                    )
                moment.state = SilenceState.ACCRUED
                agent.total_accrued += 1
                if moment.persisted:
                    agent.total_persisted += 1
                else:
                    agent.total_dissolved += 1
                accrued += 1
            # Once enough moments accrue, derive the architecture and pattern.
            if agent.accretion.total_moments >= self._ACCRUE_PATTERN_THRESHOLD:
                agent.accretion.signature_pattern = self._derive_pattern(agent)
            if agent.accretion.total_moments >= self._ACCRUE_ARCHITECTURE_THRESHOLD:
                agent.architecture = self._derive_architecture(agent)
        self._stats["total_accrued"] += accrued
        self._record_event("phase_accrue", {"accrued": accrued})
        return {"accrued": accrued}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _interpret_silence(self, moment: SilenceMoment,
                           agent: SilenceAgent) -> SilenceReading:
        """Produce an interpretation of a silence based on its function."""
        function = moment.function
        # Base resonance from the alignment of type and function.
        resonance = self._RESONATE_BASE_GAIN + moment.intensity * 0.5
        # Type-function affinities boost resonance.
        affinity = {
            (SilenceType.CAESURA, SilenceFunction.STRUCTURAL): 0.25,
            (SilenceType.CAESURA, SilenceFunction.RHETORICAL): 0.20,
            (SilenceType.ELLIPSIS, SilenceFunction.EMOTIONAL): 0.25,
            (SilenceType.ELLIPSIS, SilenceFunction.SYMBOLIC): 0.20,
            (SilenceType.HESITATION, SilenceFunction.EMOTIONAL): 0.20,
            (SilenceType.HESITATION, SilenceFunction.REGULATIVE): 0.15,
            (SilenceType.REVERENCE, SilenceFunction.SYMBOLIC): 0.30,
            (SilenceType.REVERENCE, SilenceFunction.STRUCTURAL): 0.15,
            (SilenceType.DEFIANCE, SilenceFunction.RHETORICAL): 0.25,
            (SilenceType.DEFIANCE, SilenceFunction.SYMBOLIC): 0.20,
            (SilenceType.GRIEF, SilenceFunction.EMOTIONAL): 0.30,
            (SilenceType.GRIEF, SilenceFunction.SYMBOLIC): 0.20,
            (SilenceType.ANTICIPATION, SilenceFunction.RHETORICAL): 0.25,
            (SilenceType.ANTICIPATION, SilenceFunction.STRUCTURAL): 0.15,
            (SilenceType.ABSENCE, SilenceFunction.SYMBOLIC): 0.30,
            (SilenceType.ABSENCE, SilenceFunction.EMOTIONAL): 0.20,
        }
        resonance += affinity.get((moment.silence_type, function), 0.0)
        # Meaning template by function.
        meaning_templates = {
            SilenceFunction.STRUCTURAL:
                f"{moment.silence_type.value} pause shapes the flow: {moment.context}",
            SilenceFunction.EMOTIONAL:
                f"{moment.silence_type.value} pause carries feeling: {moment.context}",
            SilenceFunction.RHETORICAL:
                f"{moment.silence_type.value} pause draws the listener in: {moment.context}",
            SilenceFunction.REGULATIVE:
                f"{moment.silence_type.value} pause governs the turn: {moment.context}",
            SilenceFunction.SYMBOLIC:
                f"{moment.silence_type.value} pause marks an absence: {moment.context}",
        }
        meaning = meaning_templates.get(
            function,
            f"{moment.silence_type.value} pause: {moment.context}",
        )
        return SilenceReading(
            function=function,
            resonance=min(1.0, resonance),
            meaning=meaning,
        )

    def _derive_pattern(self, agent: SilenceAgent) -> str:
        """Derive a signature cadence pattern from accrued silence."""
        acc = agent.accretion
        if not acc.function_weights:
            return "no signature yet"
        top_function = max(acc.function_weights, key=lambda f: acc.function_weights[f])
        if not acc.type_weights:
            return f"{top_function.value}-shaped cadence"
        top_type = max(acc.type_weights, key=lambda t: acc.type_weights[t])
        return f"{top_type.value} {top_function.value} cadence"

    def _derive_architecture(self, agent: SilenceAgent) -> VoiceArchitecture:
        """Derive the agent's overall voice architecture from accreted silence."""
        acc = agent.accretion
        if acc.total_moments < self._ACCRUE_ARCHITECTURE_THRESHOLD:
            return VoiceArchitecture.UNFORMED
        avg_duration = acc.total_duration_ms / max(1, acc.total_moments)
        # Frequency of pauses relative to the moment count.
        moment_count = acc.total_moments
        # Long silences dominate -> cathedral.
        if avg_duration >= 1500 and acc.persistence_rate >= 0.4:
            return VoiceArchitecture.CATHEDRAL
        # Very short silences -> staccato.
        if avg_duration < 300:
            return VoiceArchitecture.STACCATO
        # High frequency and high persistence -> dense.
        if moment_count >= 12 and acc.persistence_rate >= 0.4:
            return VoiceArchitecture.DENSE
        # Low frequency -> sparse.
        if moment_count < 8:
            return VoiceArchitecture.SPARSE
        return VoiceArchitecture.MODERATE

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
                "architecture": agent.architecture.value,
                "default_function": agent.default_function.value,
                "silence_tolerance": agent.silence_tolerance,
                "flow_pressure": agent.flow_pressure,
                "total_introduced": agent.total_introduced,
                "total_dissolved": agent.total_dissolved,
                "total_persisted": agent.total_persisted,
                "total_accrued": agent.total_accrued,
                "accretion": {
                    "total_duration_ms": agent.accretion.total_duration_ms,
                    "total_moments": agent.accretion.total_moments,
                    "function_weights": {
                        f.value: w for f, w in agent.accretion.function_weights.items()
                    },
                    "type_weights": {
                        t.value: w for t, w in agent.accretion.type_weights.items()
                    },
                    "signature_pattern": agent.accretion.signature_pattern,
                    "persistence_rate": agent.accretion.persistence_rate,
                },
            }

    def get_silence(self, agent_id: str, silence_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            moment = agent.moments.get(silence_id)
            if moment is None:
                return {"error": f"Silence not found: {silence_id}"}
            return {
                "silence_id": moment.silence_id,
                "type": moment.silence_type.value,
                "function": moment.function.value,
                "duration_ms": moment.duration_ms,
                "intensity": moment.intensity,
                "context": moment.context,
                "state": moment.state.value,
                "resonance": moment.resonance,
                "interpretation": moment.interpretation,
                "persisted": moment.persisted,
                "created_at": moment.created_at,
                "resolved_at": moment.resolved_at,
            }

    def get_silences(self, agent_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            moments = sorted(
                agent.moments.values(),
                key=lambda m: m.created_at,
                reverse=True,
            )[:limit]
            return {
                "agent_id": agent_id,
                "silences": [
                    {
                        "silence_id": m.silence_id,
                        "type": m.silence_type.value,
                        "function": m.function.value,
                        "state": m.state.value,
                        "duration_ms": m.duration_ms,
                        "resonance": m.resonance,
                        "persisted": m.persisted,
                    }
                    for m in moments
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
        """Seed synthetic agents and silences, then run multiple cycles."""
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
        """Seed a small synthetic cast of agents with distinct silence practices."""
        seed_agents = [
            ("sim_narrator", SilenceFunction.STRUCTURAL, 0.6, 0.4),
            ("sim_mourner", SilenceFunction.EMOTIONAL, 0.8, 0.3),
            ("sim_orator", SilenceFunction.RHETORICAL, 0.4, 0.7),
        ]
        for agent_id, function, tolerance, flow in seed_agents:
            if agent_id in self._agents:
                continue
            self.register_agent(
                agent_id,
                default_function=function,
                silence_tolerance=tolerance,
                flow_pressure=flow,
            )
        # Seed varied silence moments for each agent.
        seed_silences = [
            ("sim_s1", SilenceType.CAESURA, SilenceFunction.STRUCTURAL, 1200, 0.7, "before the verdict"),
            ("sim_s2", SilenceType.ELLIPSIS, SilenceFunction.EMOTIONAL, 800, 0.6, "the unspoken name"),
            ("sim_s3", SilenceType.REVERENCE, SilenceFunction.SYMBOLIC, 2000, 0.8, "honoring the fallen"),
            ("sim_s4", SilenceType.HESITATION, SilenceFunction.REGULATIVE, 400, 0.3, "searching for words"),
            ("sim_s5", SilenceType.DEFIANCE, SilenceFunction.RHETORICAL, 1500, 0.7, "refusing to answer"),
            ("sim_s6", SilenceType.ANTICIPATION, SilenceFunction.RHETORICAL, 900, 0.6, "before the reveal"),
            ("sim_s7", SilenceType.GRIEF, SilenceFunction.EMOTIONAL, 2500, 0.9, "the letter unread"),
            ("sim_s8", SilenceType.ABSENCE, SilenceFunction.SYMBOLIC, 3000, 0.5, "the empty chair"),
        ]
        for agent_id, _, _, _ in seed_agents:
            agent = self._agents.get(agent_id)
            if agent is None:
                continue
            for sid, stype, sfunc, dur, inten, ctx in seed_silences:
                if sid not in agent.moments:
                    self.introduce_silence(
                        agent_id, sid, stype, sfunc,
                        duration_ms=dur, intensity=inten, context=ctx,
                    )

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._agents.clear()
            self._events_log.clear()
            self._phase = SilencePhase.HUSH
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
