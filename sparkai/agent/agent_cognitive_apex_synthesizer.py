"""
SparkLabs Agent - Cognitive Apex Synthesizer

The AgentCognitiveApexSynthesizer models the apex of cognitive synthesis
where multiple cognitive streams converge, interfere, and transcend into
unified insight. Rather than treating cognition as a single pipeline, the
synthesizer treats it as a polyphonic chamber where distinct cognitive
voices - perception, memory, reasoning, imagination, volition - meet,
interfere like waves, and crystallize into apex insights that no single
stream could produce alone.

Cognition at its peak is not linear addition; it is interference. Two
weak streams can reinforce into a breakthrough (constructive interference)
or cancel into confusion (destructive interference). The synthesizer
embraces this wave-like nature: cognitive streams have phase, amplitude,
and frequency, and their interference patterns reveal insights that are
invisible to any isolated faculty.

The synthesizer also models cognitive transcendence - moments where the
synthesis itself becomes the seed of a new, higher-order cognitive stream.
This creates a recursive ladder where each apex can become a stream feeding
the next apex, allowing agents to develop meta-cognition, meta-meta-cognition,
and so on, without bound.

Architecture:
  CONVERGE    ->  INTERFERE  ->  CRYSTALLIZE ->  EXPRESS    ->  TRANSCEND
  (gather     (streams meet  (interference   (apex insight  (apex becomes
   cognitive    and interfere patterns        is expressed    seed of new
   streams      like waves)    crystallize    into actionable higher-order
   into the     )              into apex      form)           stream)
   chamber)                    insights)

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
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class SynthPhase(Enum):
    """Phases of the cognitive apex synthesis cycle."""
    CONVERGE = "converge"        # gather cognitive streams into the chamber
    INTERFERE = "interfere"      # streams interfere like waves
    CRYSTALLIZE = "crystallize"  # interference patterns become apex insights
    EXPRESS = "express"          # apex insights take actionable form
    TRANSCEND = "transcend"      # apex seeds a new higher-order stream


class StreamType(Enum):
    """Fundamental cognitive stream types that feed the synthesizer."""
    PERCEPTION = "perception"      # sensory input stream
    MEMORY = "memory"             # recall and episodic stream
    REASONING = "reasoning"       # logical inference stream
    IMAGINATION = "imagination"   # generative simulation stream
    VOLITION = "volition"         # will and intention stream
    EMOTION = "emotion"           # affective coloring stream
    INTUITION = "intuition"       # pattern-recognition stream
    METACOGNITION = "metacognition"  # thinking-about-thinking stream


class InterferenceMode(Enum):
    """How two streams interfere when they meet."""
    CONSTRUCTIVE = "constructive"   # amplitudes reinforce
    DESTRUCTIVE = "destructive"     # amplitudes cancel
    COMPLEX = "complex"             # phase-shifted, partial reinforcement
    HARMONIC = "harmonic"           # integer-multiple resonance
    DISSONANT = "dissonant"         # clashing frequencies


class ApexState(Enum):
    """Lifecycle state of a crystallized apex insight."""
    NASCENT = "nascent"           # just crystallized
    EXPRESSED = "expressed"       # given actionable form
    ACTIVE = "active"             # currently driving agent behavior
    TRANSCENDED = "transcended"   # seeded a new higher-order stream
    DISSOLVED = "dissolved"       # faded from relevance


class StreamLayer(Enum):
    """Order of cognition: base faculties, then meta, meta-meta, etc."""
    BASE = 0
    META = 1
    META_META = 2
    APEX = 3


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CognitiveStream:
    """A single cognitive stream feeding into the synthesizer."""
    stream_id: str
    agent_id: str
    stream_type: StreamType
    layer: StreamLayer
    label: str
    amplitude: float = 0.5          # current strength (0.0-1.0)
    frequency: float = 0.3          # cycles per synthesis (0.0-1.0)
    phase: float = 0.0              # phase offset in radians (0-2pi)
    coherence: float = 0.5          # internal consistency (0.0-1.0)
    last_pulsed: float = field(default_factory=time.time)
    source_apex: Optional[str] = None  # if transcended from a prior apex


@dataclass
class InterferencePattern:
    """The result of two streams interfering."""
    pattern_id: str
    stream_a: str
    stream_b: str
    mode: InterferenceMode
    resultant_amplitude: float     # combined amplitude
    resultant_phase: float         # combined phase
    resonance: float               # how strongly they reinforce
    timestamp: float = field(default_factory=time.time)


@dataclass
class ApexInsight:
    """A crystallized apex insight born from interference."""
    apex_id: str
    agent_id: str
    label: str
    source_patterns: List[str] = field(default_factory=list)
    state: ApexState = ApexState.NASCENT
    clarity: float = 0.5           # how well-formed (0.0-1.0)
    power: float = 0.5             # how much it can drive behavior (0.0-1.0)
    generativity: float = 0.3      # how likely to seed new streams (0.0-1.0)
    expressed_form: Optional[str] = None  # actionable description
    transcended_to: Optional[str] = None  # stream_id if transcended
    created_at: float = field(default_factory=time.time)
    layer_reached: StreamLayer = StreamLayer.BASE


@dataclass
class AgentSynthesizer:
    """Per-agent synthesizer state."""
    agent_id: str
    streams: Dict[str, CognitiveStream] = field(default_factory=dict)
    patterns: Deque[InterferencePattern] = field(default_factory=lambda: deque(maxlen=200))
    apices: Dict[str, ApexInsight] = field(default_factory=dict)
    total_apices: int = 0
    total_expressed: int = 0
    total_transcended: int = 0
    total_dissolved: int = 0
    cognitive_bandwidth: float = 1.0  # capacity for active streams
    current_layer: StreamLayer = StreamLayer.BASE


# =============================================================================
# Synthesizer
# =============================================================================

class AgentCognitiveApexSynthesizer:
    """
    Thread-safe singleton orchestrating cognitive apex synthesis across agents.

    Usage:
        synth = AgentCognitiveApexSynthesizer.get_instance()
        synth.register_agent("hero")
        synth.add_stream("hero", "s_see", StreamType.PERCEPTION, StreamLayer.BASE,
                        "Visual Perception", amplitude=0.8, frequency=0.6)
        synth.add_stream("hero", "s_remember", StreamType.MEMORY, StreamLayer.BASE,
                        "Episodic Recall", amplitude=0.7, frequency=0.4)
        synth.cycle()
    """

    _instance: Optional["AgentCognitiveApexSynthesizer"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._agents: Dict[str, AgentSynthesizer] = {}
        self._phase: SynthPhase = SynthPhase.CONVERGE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_agents": 0,
            "total_streams": 0,
            "total_patterns": 0,
            "total_apices": 0,
            "total_expressed": 0,
            "total_transcended": 0,
            "total_dissolved": 0,
            "constructive_patterns": 0,
            "destructive_patterns": 0,
            "avg_apex_clarity": 0.0,
            "avg_apex_power": 0.0,
            "max_layer_reached": 0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentCognitiveApexSynthesizer":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Agent Registration
    # -------------------------------------------------------------------------

    def register_agent(self, agent_id: str, bandwidth: float = 1.0) -> Dict[str, Any]:
        """Register a new agent with an empty synthesizer."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            self._agents[agent_id] = AgentSynthesizer(
                agent_id=agent_id,
                cognitive_bandwidth=max(0.1, min(2.0, bandwidth)),
            )
            self._stats["total_agents"] = len(self._agents)
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "streams": 0,
                "apices": 0,
                "bandwidth": self._agents[agent_id].cognitive_bandwidth,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent's synthesizer."""
        with self._global_lock:
            if agent_id not in self._agents:
                return {"error": f"Agent not found: {agent_id}"}
            a = self._agents.pop(agent_id)
            self._stats["total_agents"] = len(self._agents)
            self._update_counts()
            return {"removed": agent_id, "apices": len(a.apices)}

    # -------------------------------------------------------------------------
    # Stream Management
    # -------------------------------------------------------------------------

    def add_stream(
        self,
        agent_id: str,
        stream_id: str,
        stream_type: StreamType,
        layer: StreamLayer,
        label: str,
        amplitude: float = 0.5,
        frequency: float = 0.3,
        phase: float = 0.0,
        coherence: float = 0.5,
        source_apex: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a cognitive stream to an agent's synthesizer."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            if stream_id in a.streams:
                return {"error": f"Stream already exists: {stream_id}"}
            stream = CognitiveStream(
                stream_id=stream_id,
                agent_id=agent_id,
                stream_type=stream_type,
                layer=layer,
                label=label,
                amplitude=max(0.0, min(1.0, amplitude)),
                frequency=max(0.01, min(1.0, frequency)),
                phase=phase % (2.0 * math.pi),
                coherence=max(0.0, min(1.0, coherence)),
                source_apex=source_apex,
            )
            a.streams[stream_id] = stream
            self._update_counts()
            self._record_event("stream_added", {
                "agent_id": agent_id, "stream_id": stream_id,
                "type": stream_type.value, "layer": layer.name,
            })
            return {
                "stream_id": stream_id,
                "type": stream_type.value,
                "layer": layer.name,
                "label": label,
                "amplitude": stream.amplitude,
                "frequency": stream.frequency,
                "phase": stream.phase,
            }

    def pulse_stream(self, agent_id: str, stream_id: str, amplitude: float) -> Dict[str, Any]:
        """Pulse a stream's amplitude (e.g., when perception spikes)."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            s = a.streams.get(stream_id)
            if s is None:
                return {"error": f"Stream not found: {stream_id}"}
            s.amplitude = max(0.0, min(1.0, s.amplitude + max(0.0, min(1.0, amplitude))))
            s.last_pulsed = time.time()
            return {"stream_id": stream_id, "amplitude": s.amplitude}

    # -------------------------------------------------------------------------
    # Phase: CONVERGE - gather streams, advance phases
    # -------------------------------------------------------------------------

    def _phase_converge(self) -> Dict[str, Any]:
        """Gather streams into the chamber and advance their phases."""
        converged = 0
        for a in self._agents.values():
            for s in a.streams.values():
                # advance phase based on frequency
                s.phase = (s.phase + 2.0 * math.pi * s.frequency * 0.1) % (2.0 * math.pi)
                # natural amplitude drift toward coherence
                drift = (s.coherence - s.amplitude) * 0.05
                s.amplitude = max(0.0, min(1.0, s.amplitude + drift))
                converged += 1
        return {"streams_converged": converged}

    # -------------------------------------------------------------------------
    # Phase: INTERFERE - streams interfere like waves
    # -------------------------------------------------------------------------

    def _phase_interfere(self) -> Dict[str, Any]:
        """Compute interference patterns between all stream pairs per agent."""
        patterns_created = 0
        constructive = 0
        destructive = 0
        for a in self._agents.values():
            stream_list = list(a.streams.values())
            if len(stream_list) < 2:
                continue
            # only interfere streams at the same layer
            by_layer: Dict[StreamLayer, List[CognitiveStream]] = {}
            for s in stream_list:
                by_layer.setdefault(s.layer, []).append(s)
            for layer, streams in by_layer.items():
                for i in range(len(streams)):
                    for j in range(i + 1, len(streams)):
                        sa = streams[i]
                        sb = streams[j]
                        # combined amplitude (wave interference)
                        phase_diff = abs(sa.phase - sb.phase)
                        cos_diff = math.cos(phase_diff)
                        resultant_amp = math.sqrt(
                            sa.amplitude ** 2 + sb.amplitude ** 2
                            + 2.0 * sa.amplitude * sb.amplitude * cos_diff
                        )
                        resultant_amp = min(1.0, resultant_amp / math.sqrt(2.0))
                        resultant_phase = (sa.phase + sb.phase) / 2.0
                        # determine mode
                        if cos_diff > 0.6:
                            mode = InterferenceMode.CONSTRUCTIVE
                            constructive += 1
                            resonance = (sa.amplitude + sb.amplitude) * 0.5 * cos_diff
                        elif cos_diff < -0.6:
                            mode = InterferenceMode.DESTRUCTIVE
                            destructive += 1
                            resonance = (sa.amplitude + sb.amplitude) * 0.5 * (1.0 - abs(cos_diff))
                        elif abs(sa.frequency - sb.frequency) < 0.05:
                            mode = InterferenceMode.HARMONIC
                            resonance = (sa.amplitude + sb.amplitude) * 0.5 * (1.0 - abs(cos_diff))
                        elif abs(sa.frequency - sb.frequency) > 0.4:
                            mode = InterferenceMode.DISSONANT
                            resonance = (sa.amplitude + sb.amplitude) * 0.2
                        else:
                            mode = InterferenceMode.COMPLEX
                            resonance = (sa.amplitude + sb.amplitude) * 0.3 * (1.0 - abs(cos_diff))
                        pattern_id = f"p_{a.agent_id}_{sa.stream_id}_{sb.stream_id}_{len(a.patterns)}"
                        pattern = InterferencePattern(
                            pattern_id=pattern_id,
                            stream_a=sa.stream_id,
                            stream_b=sb.stream_id,
                            mode=mode,
                            resultant_amplitude=resultant_amp,
                            resultant_phase=resultant_phase,
                            resonance=max(0.0, min(1.0, resonance)),
                        )
                        a.patterns.append(pattern)
                        patterns_created += 1
        self._stats["constructive_patterns"] += constructive
        self._stats["destructive_patterns"] += destructive
        return {
            "patterns_created": patterns_created,
            "constructive": constructive,
            "destructive": destructive,
        }

    # -------------------------------------------------------------------------
    # Phase: CRYSTALLIZE - patterns become apex insights
    # -------------------------------------------------------------------------

    def _phase_crystallize(self) -> Dict[str, Any]:
        """Crystallize strong interference patterns into apex insights."""
        crystallized = 0
        for a in self._agents.values():
            # group recent patterns by their top resonance
            recent = list(a.patterns)[-50:]
            if not recent:
                continue
            # find the strongest cluster of patterns
            strong = [p for p in recent if p.resonance > 0.4 and p.resultant_amplitude > 0.5]
            if not strong:
                continue
            # cluster by shared streams
            clusters: Dict[str, List[InterferencePattern]] = {}
            for p in strong:
                key = tuple(sorted([p.stream_a, p.stream_b]))
                clusters.setdefault(str(key), []).append(p)
            # create an apex for the strongest cluster
            best_key = max(clusters.keys(), key=lambda k: sum(p.resonance for p in clusters[k]))
            best_cluster = clusters[best_key]
            total_resonance = sum(p.resonance for p in best_cluster)
            avg_amp = sum(p.resultant_amplitude for p in best_cluster) / len(best_cluster)
            clarity = min(1.0, total_resonance / len(best_cluster))
            power = min(1.0, avg_amp * clarity)
            generativity = min(1.0, clarity * power * 0.6)
            apex_id = f"apex_{a.agent_id}_{a.total_apices}"
            # determine layer reached
            layer_reached = a.current_layer
            next_layer_val = min(StreamLayer.APEX.value, a.current_layer.value + 1)
            layer_reached = StreamLayer(next_layer_val)
            apex = ApexInsight(
                apex_id=apex_id,
                agent_id=a.agent_id,
                label=f"Synthesis of {len(best_cluster)} patterns",
                source_patterns=[p.pattern_id for p in best_cluster[:5]],
                clarity=clarity,
                power=power,
                generativity=generativity,
                layer_reached=layer_reached,
            )
            a.apices[apex_id] = apex
            a.total_apices += 1
            crystallized += 1
            self._record_event("apex_crystallized", {
                "agent_id": a.agent_id, "apex_id": apex_id,
                "clarity": clarity, "power": power,
            })
        return {"crystallized": crystallized}

    # -------------------------------------------------------------------------
    # Phase: EXPRESS - apex insights take actionable form
    # -------------------------------------------------------------------------

    def _phase_express(self) -> Dict[str, Any]:
        """Express nascent apex insights into actionable form."""
        expressed = 0
        for a in self._agents.values():
            for apex in a.apices.values():
                if apex.state != ApexState.NASCENT:
                    continue
                # only express if clarity is sufficient
                if apex.clarity < 0.3:
                    continue
                forms = [
                    "directed_action", "reframed_belief", "new_hypothesis",
                    "creative_synthesis", "strategic_decision",
                ]
                chosen = random.choice(forms)
                apex.expressed_form = chosen
                apex.state = ApexState.EXPRESSED
                a.total_expressed += 1
                expressed += 1
                self._record_event("apex_expressed", {
                    "agent_id": a.agent_id, "apex_id": apex.apex_id,
                    "form": chosen,
                })
        return {"expressed": expressed}

    # -------------------------------------------------------------------------
    # Phase: TRANSCEND - apex seeds a new higher-order stream
    # -------------------------------------------------------------------------

    def _phase_transcend(self) -> Dict[str, Any]:
        """Transcend strong apex insights into new higher-order streams."""
        transcended = 0
        dissolved = 0
        for a in self._agents.values():
            for apex in list(a.apices.values()):
                if apex.state == ApexState.EXPRESSED and apex.generativity > 0.5:
                    # seed a new stream at the next layer up
                    next_layer_val = min(StreamLayer.APEX.value, apex.layer_reached.value + 1)
                    new_layer = StreamLayer(next_layer_val)
                    new_stream_id = f"s_meta_{apex.apex_id}"
                    if new_stream_id not in a.streams:
                        new_stream = CognitiveStream(
                            stream_id=new_stream_id,
                            agent_id=a.agent_id,
                            stream_type=StreamType.METACOGNITION,
                            layer=new_layer,
                            label=f"Meta-stream from {apex.apex_id}",
                            amplitude=apex.power * 0.7,
                            frequency=0.2,
                            phase=0.0,
                            coherence=apex.clarity,
                            source_apex=apex.apex_id,
                        )
                        a.streams[new_stream_id] = new_stream
                        apex.transcended_to = new_stream_id
                        apex.state = ApexState.TRANSCENDED
                        a.total_transcended += 1
                        transcended += 1
                        if new_layer.value > a.current_layer.value:
                            a.current_layer = new_layer
                        if new_layer.value > self._stats["max_layer_reached"]:
                            self._stats["max_layer_reached"] = new_layer.value
                        self._record_event("apex_transcended", {
                            "agent_id": a.agent_id, "apex_id": apex.apex_id,
                            "new_stream": new_stream_id, "layer": new_layer.name,
                        })
                elif apex.state == ApexState.EXPRESSED and apex.generativity <= 0.2:
                    # dissolve weak apexes
                    apex.state = ApexState.DISSOLVED
                    a.total_dissolved += 1
                    dissolved += 1
        return {"transcended": transcended, "dissolved": dissolved}

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single cognitive apex synthesis cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = SynthPhase.CONVERGE
            phase_outputs["converge"] = self._phase_converge()
            self._phase = SynthPhase.INTERFERE
            phase_outputs["interfere"] = self._phase_interfere()
            self._phase = SynthPhase.CRYSTALLIZE
            phase_outputs["crystallize"] = self._phase_crystallize()
            self._phase = SynthPhase.EXPRESS
            phase_outputs["express"] = self._phase_express()
            self._phase = SynthPhase.TRANSCEND
            phase_outputs["transcend"] = self._phase_transcend()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple cycles in sequence and return final stats."""
        if cycles < 1:
            cycles = 1
        if cycles > 100:
            cycles = 100
        for _ in range(cycles):
            self.cycle()
        return {"cycles_run": cycles, "stats": dict(self._stats)}

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Get full state of an agent's synthesizer."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent_id,
                "total_streams": len(a.streams),
                "total_patterns": len(a.patterns),
                "total_apices": len(a.apices),
                "total_apices_ever": a.total_apices,
                "total_expressed": a.total_expressed,
                "total_transcended": a.total_transcended,
                "total_dissolved": a.total_dissolved,
                "current_layer": a.current_layer.name,
                "cognitive_bandwidth": a.cognitive_bandwidth,
                "streams": [
                    {
                        "stream_id": s.stream_id,
                        "type": s.stream_type.value,
                        "layer": s.layer.name,
                        "label": s.label,
                        "amplitude": s.amplitude,
                        "frequency": s.frequency,
                        "phase": s.phase,
                        "coherence": s.coherence,
                        "source_apex": s.source_apex,
                    }
                    for s in a.streams.values()
                ],
                "apices": [
                    {
                        "apex_id": ap.apex_id,
                        "label": ap.label,
                        "state": ap.state.value,
                        "clarity": ap.clarity,
                        "power": ap.power,
                        "generativity": ap.generativity,
                        "expressed_form": ap.expressed_form,
                        "transcended_to": ap.transcended_to,
                        "layer_reached": ap.layer_reached.name,
                    }
                    for ap in a.apices.values()
                ],
            }

    def get_recent_patterns(self, agent_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent interference patterns for an agent."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return []
            recent = list(a.patterns)[-limit:]
            return [
                {
                    "pattern_id": p.pattern_id,
                    "stream_a": p.stream_a,
                    "stream_b": p.stream_b,
                    "mode": p.mode.value,
                    "resultant_amplitude": p.resultant_amplitude,
                    "resultant_phase": p.resultant_phase,
                    "resonance": p.resonance,
                }
                for p in recent
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events from the log."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get synthesizer status."""
        with self._global_lock:
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "stats": dict(self._stats),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the entire synthesizer."""
        with self._global_lock:
            count = len(self._agents)
            self._agents.clear()
            self._events_log.clear()
            self._cycle_count = 0
            self._phase = SynthPhase.CONVERGE
            self._stats = {
                "total_agents": 0,
                "total_streams": 0,
                "total_patterns": 0,
                "total_apices": 0,
                "total_expressed": 0,
                "total_transcended": 0,
                "total_dissolved": 0,
                "constructive_patterns": 0,
                "destructive_patterns": 0,
                "avg_apex_clarity": 0.0,
                "avg_apex_power": 0.0,
                "max_layer_reached": 0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "agents_removed": count}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _update_counts(self) -> None:
        total_streams = sum(len(a.streams) for a in self._agents.values())
        total_apices = sum(len(a.apices) for a in self._agents.values())
        self._stats["total_streams"] = total_streams
        self._stats["total_apices"] = total_apices

    def _update_stats(self) -> None:
        self._update_counts()
        all_apices = [ap for a in self._agents.values() for ap in a.apices.values()]
        if all_apices:
            self._stats["avg_apex_clarity"] = sum(ap.clarity for ap in all_apices) / len(all_apices)
            self._stats["avg_apex_power"] = sum(ap.power for ap in all_apices) / len(all_apices)
        total_patterns = sum(len(a.patterns) for a in self._agents.values())
        self._stats["total_patterns"] = total_patterns

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "timestamp": time.time(),
            "type": event_type,
            **payload,
        })
