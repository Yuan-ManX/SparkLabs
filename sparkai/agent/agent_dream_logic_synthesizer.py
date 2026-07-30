"""
SparkLabs Agent - Dream Logic Synthesizer

The AgentDreamLogicSynthesizer models how agents process experiences during
rest and dream states. When an agent sleeps or enters a meditative state,
its mind drifts through fragmented memories, weaves them into dream
narratives, distorts them through emotional lenses, resolves the
contradictions that arise, and crystallizes the insights that emerge from
the dream logic.

Dreams are not replay. They are synthesis. A memory of a loss, viewed
through a lens of fear, becomes a nightmare of recurrence; the same memory,
viewed through hope, becomes a vision of recovery. Dream logic lets
impossible things coexist, and from that coexistence new understanding
condenses - insights the agent carries back into waking life.

Architecture:
  DRIFT      ->  WEAVE      ->  DISTORT    ->  RESOLVE    ->  CRYSTALLIZE
  (memories      (drifting      (fragments    (contradictions   (resolved
   surface and    memories       distorted    reconciled        fragments
   drift in a     weave into     by emotional through dream     condense into
   dream state)   fragments)     lenses)      logic)            insights)

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
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class DreamPhase(Enum):
    """Phases of the dream logic synthesis cycle."""
    DRIFT = "drift"              # memories drift and surface randomly
    WEAVE = "weave"              # drifting memories weave into fragments
    DISTORT = "distort"          # fragments distorted by emotional lenses
    RESOLVE = "resolve"          # contradictions resolved through dream logic
    CRYSTALLIZE = "crystallize"  # resolved fragments crystallize into insights


class DreamState(Enum):
    """State of an agent within the dream cycle."""
    AWAKE = "awake"
    DRIFTING = "drifting"
    DREAMING = "dreaming"
    LUCID = "lucid"
    RESOLVING = "resolving"
    CRYSTALLIZING = "crystallizing"
    AWAKENED = "awakened"


class EmotionalLens(Enum):
    """Emotional lenses that color and distort dream fragments."""
    CLARITY = "clarity"        # neutral, clear
    FEAR = "fear"              # darkens, threatens
    DESIRE = "desire"          # intensifies, seduces
    NOSTALGIA = "nostalgia"    # golden, bittersweet
    GUILT = "guilt"            # distorts, accuses
    HOPE = "hope"              # brightens, encourages
    RAGE = "rage"              # inflames, confronts
    WONDER = "wonder"          # expands, amazes


class FragmentType(Enum):
    """Kinds of dream fragments produced by weaving."""
    MEMORY = "memory"          # surfaced memory
    SYNTHESIS = "synthesis"    # woven from multiple memories
    SYMBOLIC = "symbolic"      # abstract symbol drawn from memory
    ARCHETYPAL = "archetypal"  # universal pattern
    PROPHETIC = "prophetic"    # anticipatory vision


class InsightType(Enum):
    """Kinds of insights crystallized from resolved fragments."""
    PATTERN = "pattern"            # recurring pattern recognized
    RESOLUTION = "resolution"      # emotional conflict resolved
    FORESIGHT = "foresight"        # anticipatory insight
    INTEGRATION = "integration"    # fragmented self integrated
    REVELATION = "revelation"      # sudden understanding


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class DreamMemory:
    """A memory shard available to the dream substrate."""
    memory_id: str
    label: str
    emotional_charge: float = 0.5       # 0.0-1.0
    clarity: float = 0.5                # 0.0-1.0
    source: str = "waking"              # "waking" or "dream"
    surfaced: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class DreamFragment:
    """A narrative thread woven from drifted memories."""
    fragment_id: str
    source_memories: List[str] = field(default_factory=list)
    fragment_type: FragmentType = FragmentType.SYNTHESIS
    label: str = ""
    coherence: float = 0.0              # 0.0-1.0
    emotional_intensity: float = 0.0    # 0.0-1.0
    lens_applied: Optional[EmotionalLens] = None
    distortion_level: float = 0.0       # 0.0-1.0
    resolved: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class DreamInsight:
    """An insight crystallized from a resolved dream fragment."""
    insight_id: str
    agent_id: str
    source_fragments: List[str] = field(default_factory=list)
    insight_type: InsightType = InsightType.PATTERN
    label: str = ""
    description: str = ""
    confidence: float = 0.0             # 0.0-1.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class DreamAgent:
    """Per-agent dream state and accumulated dream material."""
    agent_id: str
    dream_state: DreamState = DreamState.AWAKE
    memory_shards: Dict[str, DreamMemory] = field(default_factory=dict)
    fragments: Dict[str, DreamFragment] = field(default_factory=dict)
    insights: List[DreamInsight] = field(default_factory=list)
    lucidity: float = 0.1               # 0.0-1.0
    dream_depth: float = 0.0            # 0.0-1.0
    total_dreams: int = 0
    total_fragments: int = 0
    total_insights: int = 0
    current_lens: Optional[EmotionalLens] = None


# =============================================================================
# Synthesizer
# =============================================================================

class AgentDreamLogicSynthesizer:
    """
    Thread-safe singleton orchestrating dream logic synthesis for agents.

    Usage:
        synth = AgentDreamLogicSynthesizer.get_instance()
        synth.register_agent("dreamer_1")
        synth.add_memory("dreamer_1", "m1", "loss at the river", 0.8, 0.6)
        synth.add_memory("dreamer_1", "m2", "victory at dawn", 0.7, 0.5)
        synth.enter_dream("dreamer_1", lens="fear")
        synth.cycle()
        insights = synth.get_insights("dreamer_1")
    """

    _instance: Optional["AgentDreamLogicSynthesizer"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _DRIFT_SURFACE_PROBABILITY = 0.4    # chance a memory surfaces during drift
    _WEAVE_FRAGMENT_THRESHOLD = 2       # minimum surfaced memories to weave a fragment
    _DISTORT_PROBABILITY = 0.6          # chance a fragment is distorted by a lens
    _RESOLVE_THRESHOLD = 0.3            # minimum coherence for resolution
    _CRYSTALLIZE_THRESHOLD = 0.5        # minimum resolved coherence for crystallization
    _LUCIDITY_GROWTH = 0.05             # lucidity gained per crystallized insight
    _INSIGHT_CONFIDENCE_BASE = 0.4

    # Operational caps (bounded storage)
    _MAX_MEMORIES_PER_AGENT = 200
    _MAX_FRAGMENTS_PER_AGENT = 100
    _MAX_INSIGHTS_PER_AGENT = 300
    _MAX_EVENTS = 200

    # Emotional lens profiles: each lens colors a fragment differently.
    # CLARITY is neutral; FEAR darkens; HOPE brightens; RAGE inflames; etc.
    _LENS_PROFILES: Dict[EmotionalLens, Dict[str, Tuple[float, float]]] = {
        EmotionalLens.CLARITY:   {"coherence": (0.0, 0.1),    "intensity": (-0.05, 0.05), "distortion": (0.0, 0.05)},
        EmotionalLens.FEAR:      {"coherence": (-0.25, -0.05), "intensity": (0.1, 0.3),   "distortion": (0.2, 0.45)},
        EmotionalLens.DESIRE:    {"coherence": (-0.1, 0.05),   "intensity": (0.15, 0.35), "distortion": (0.05, 0.2)},
        EmotionalLens.NOSTALGIA: {"coherence": (-0.1, 0.0),    "intensity": (0.1, 0.25),  "distortion": (0.05, 0.15)},
        EmotionalLens.GUILT:     {"coherence": (-0.2, -0.05),  "intensity": (0.05, 0.2),  "distortion": (0.15, 0.35)},
        EmotionalLens.HOPE:      {"coherence": (0.1, 0.25),    "intensity": (0.0, 0.15),  "distortion": (-0.05, 0.05)},
        EmotionalLens.RAGE:      {"coherence": (-0.15, -0.02), "intensity": (0.2, 0.4),   "distortion": (0.1, 0.3)},
        EmotionalLens.WONDER:    {"coherence": (0.05, 0.2),    "intensity": (0.05, 0.2),  "distortion": (0.0, 0.1)},
    }

    # Fragment type -> default insight type when crystallized
    _FRAGMENT_INSIGHT_MAP: Dict[FragmentType, InsightType] = {
        FragmentType.MEMORY: InsightType.RESOLUTION,
        FragmentType.SYNTHESIS: InsightType.INTEGRATION,
        FragmentType.SYMBOLIC: InsightType.REVELATION,
        FragmentType.ARCHETYPAL: InsightType.PATTERN,
        FragmentType.PROPHETIC: InsightType.FORESIGHT,
    }

    def __init__(self) -> None:
        self._agents: Dict[str, DreamAgent] = {}
        self._phase: DreamPhase = DreamPhase.DRIFT
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats = self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentDreamLogicSynthesizer":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Agent Management
    # -------------------------------------------------------------------------

    def register_agent(self, agent_id: str, lucidity: float = 0.1) -> Dict[str, Any]:
        """Register a new agent for dream logic synthesis."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            agent = DreamAgent(
                agent_id=agent_id,
                lucidity=max(0.0, min(1.0, lucidity)),
            )
            self._agents[agent_id] = agent
            self._stats["total_agents"] = len(self._agents)
            self._record_event("agent_registered", {
                "agent_id": agent_id,
                "lucidity": agent.lucidity,
            })
            return {
                "agent_id": agent_id,
                "dream_state": agent.dream_state.value,
                "lucidity": agent.lucidity,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent and all of its dream material."""
        with self._global_lock:
            agent = self._agents.pop(agent_id, None)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            self._stats["total_agents"] = len(self._agents)
            self._record_event("agent_removed", {
                "agent_id": agent_id,
                "fragments": len(agent.fragments),
                "insights": len(agent.insights),
            })
            return {
                "removed": agent_id,
                "cleared_memories": len(agent.memory_shards),
                "cleared_fragments": len(agent.fragments),
                "cleared_insights": len(agent.insights),
            }

    # -------------------------------------------------------------------------
    # Memory Intake
    # -------------------------------------------------------------------------

    def add_memory(self, agent_id: str, memory_id: str, label: str,
                   emotional_charge: float = 0.5, clarity: float = 0.5) -> Dict[str, Any]:
        """Add a memory shard to an agent's dream substrate."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            memory = DreamMemory(
                memory_id=memory_id,
                label=label,
                emotional_charge=max(0.0, min(1.0, emotional_charge)),
                clarity=max(0.0, min(1.0, clarity)),
                source="waking",
                surfaced=False,
            )
            agent.memory_shards[memory_id] = memory
            # Bound memory storage, dropping the oldest shard when over capacity
            if len(agent.memory_shards) > self._MAX_MEMORIES_PER_AGENT:
                oldest_id = min(
                    agent.memory_shards,
                    key=lambda mid: agent.memory_shards[mid].timestamp,
                )
                agent.memory_shards.pop(oldest_id, None)
            self._record_event("memory_added", {
                "agent_id": agent_id,
                "memory_id": memory_id,
                "emotional_charge": memory.emotional_charge,
                "clarity": memory.clarity,
            })
            return {
                "agent_id": agent_id,
                "memory_id": memory.memory_id,
                "label": memory.label,
                "emotional_charge": memory.emotional_charge,
                "clarity": memory.clarity,
                "total_memories": len(agent.memory_shards),
            }

    # -------------------------------------------------------------------------
    # Dream Entry
    # -------------------------------------------------------------------------

    def enter_dream(self, agent_id: str, lens: str = "clarity") -> Dict[str, Any]:
        """Begin a dream for an agent under a given emotional lens."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            try:
                lens_enum = EmotionalLens(lens)
            except ValueError:
                lens_enum = EmotionalLens.CLARITY
            agent.current_lens = lens_enum
            agent.dream_state = DreamState.DRIFTING
            agent.dream_depth = max(agent.dream_depth, 0.1)
            # Clear the slate so memories drift fresh this dream
            for memory in agent.memory_shards.values():
                memory.surfaced = False
            self._record_event("dream_entered", {
                "agent_id": agent_id,
                "lens": lens_enum.value,
                "lucidity": agent.lucidity,
            })
            return {
                "agent_id": agent_id,
                "dream_state": agent.dream_state.value,
                "lens": lens_enum.value,
                "dream_depth": agent.dream_depth,
            }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single dream logic synthesis cycle across all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            # DRIFT: memories drift and surface randomly
            self._phase = DreamPhase.DRIFT
            phase_outputs["drift"] = self._phase_drift()
            # WEAVE: drifting memories weave into fragments
            self._phase = DreamPhase.WEAVE
            phase_outputs["weave"] = self._phase_weave()
            # DISTORT: fragments distorted by emotional lenses
            self._phase = DreamPhase.DISTORT
            phase_outputs["distort"] = self._phase_distort()
            # RESOLVE: contradictions resolved through dream logic
            self._phase = DreamPhase.RESOLVE
            phase_outputs["resolve"] = self._phase_resolve()
            # CRYSTALLIZE: resolved fragments crystallize into insights
            self._phase = DreamPhase.CRYSTALLIZE
            phase_outputs["crystallize"] = self._phase_crystallize()
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
        """Run multiple dream cycles, seeding a demo agent if none registered."""
        with self._global_lock:
            if cycles < 1 or cycles > 1000:
                return {"error": "cycles must be between 1 and 1000"}
            # Seed a demo agent so simulation produces fragments and insights
            if not self._agents:
                self._seed_demo_agent()
            results = []
            for _ in range(cycles):
                t0 = time.time()
                phase_outputs: Dict[str, Any] = {}
                self._phase = DreamPhase.DRIFT
                phase_outputs["drift"] = self._phase_drift()
                self._phase = DreamPhase.WEAVE
                phase_outputs["weave"] = self._phase_weave()
                self._phase = DreamPhase.DISTORT
                phase_outputs["distort"] = self._phase_distort()
                self._phase = DreamPhase.RESOLVE
                phase_outputs["resolve"] = self._phase_resolve()
                self._phase = DreamPhase.CRYSTALLIZE
                phase_outputs["crystallize"] = self._phase_crystallize()
                self._cycle_count += 1
                self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
                self._update_stats()
                results.append({
                    "cycle_count": self._cycle_count,
                    "phase": self._phase.value,
                    "phase_outputs": phase_outputs,
                    "stats": dict(self._stats),
                })
            return {
                "cycles_run": len(results),
                "final_phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "stats": dict(self._stats),
            }

    # -------------------------------------------------------------------------
    # Phase Implementations
    # -------------------------------------------------------------------------

    def _phase_drift(self) -> Dict[str, Any]:
        """DRIFT: dreaming agents' memories drift and surface randomly."""
        surfaced_total = 0
        dreaming_states = (
            DreamState.DRIFTING, DreamState.DREAMING, DreamState.LUCID,
            DreamState.RESOLVING, DreamState.CRYSTALLIZING,
        )
        for agent in self._agents.values():
            if agent.dream_state not in dreaming_states:
                continue
            # Deepen the dream a little each cycle
            agent.dream_depth = min(1.0, agent.dream_depth + 0.1)
            # Surface probability rises with dream depth
            effective_prob = min(
                0.95, self._DRIFT_SURFACE_PROBABILITY + agent.dream_depth * 0.1
            )
            # Memories drift fresh each cycle
            for memory in agent.memory_shards.values():
                memory.surfaced = False
            surfaced_here = 0
            for memory in agent.memory_shards.values():
                if random.random() < effective_prob:
                    memory.surfaced = True
                    surfaced_here += 1
            # Drifting agents with a surfaced memory enter the dream
            if agent.dream_state == DreamState.DRIFTING and surfaced_here > 0:
                agent.dream_state = DreamState.DREAMING
            surfaced_total += surfaced_here
        self._record_event("drift", {"surfaced": surfaced_total})
        return {"surfaced": surfaced_total}

    def _phase_weave(self) -> Dict[str, Any]:
        """WEAVE: surfaced memories weave together into dream fragments."""
        fragments_created = 0
        now = time.time()
        for agent in self._agents.values():
            if agent.dream_state not in (DreamState.DREAMING, DreamState.LUCID):
                continue
            surfaced = [m for m in agent.memory_shards.values() if m.surfaced]
            if len(surfaced) < self._WEAVE_FRAGMENT_THRESHOLD:
                continue
            # Weave one fragment per cycle from a sample of surfaced memories
            sample_size = min(len(surfaced), random.randint(2, 4))
            chosen = random.sample(surfaced, k=sample_size)
            fragment = self._weave_fragment(agent, chosen, now)
            if fragment is None:
                continue
            agent.fragments[fragment.fragment_id] = fragment
            agent.total_fragments += 1
            fragments_created += 1
            # Bound fragment storage, dropping the oldest in-flight fragment
            if len(agent.fragments) > self._MAX_FRAGMENTS_PER_AGENT:
                oldest_id = min(
                    agent.fragments,
                    key=lambda fid: agent.fragments[fid].timestamp,
                )
                agent.fragments.pop(oldest_id, None)
        self._record_event("weave", {"fragments_created": fragments_created})
        return {"fragments_created": fragments_created}

    def _weave_fragment(self, agent: DreamAgent, memories: List[DreamMemory],
                        now: float) -> Optional[DreamFragment]:
        """Build a single dream fragment from a set of surfaced memories."""
        if not memories:
            return None
        fragment_id = f"frag_{agent.agent_id}_{int(now * 1000)}_{random.randint(0, 9999):04d}"
        # Coherence: geometric mean of memory clarities, lifted by charge alignment
        clarities = [max(0.01, m.clarity) for m in memories]
        product = 1.0
        for c in clarities:
            product *= c
        geo = math.pow(product, 1.0 / len(clarities))
        # Emotional alignment: similar charges across memories raise coherence
        charges = [m.emotional_charge for m in memories]
        spread = max(charges) - min(charges)
        alignment = 1.0 - spread  # 0.0..1.0
        coherence = min(1.0, geo * 0.7 + alignment * 0.2 + 0.1)
        # Emotional intensity: mean charge
        intensity = sum(charges) / len(charges)
        fragment_type = self._pick_fragment_type(len(memories))
        label = self._label_fragment(fragment_type, memories)
        return DreamFragment(
            fragment_id=fragment_id,
            source_memories=[m.memory_id for m in memories],
            fragment_type=fragment_type,
            label=label,
            coherence=coherence,
            emotional_intensity=intensity,
            lens_applied=None,
            distortion_level=0.0,
            resolved=False,
            timestamp=now,
        )

    def _pick_fragment_type(self, sample_size: int) -> FragmentType:
        """Choose a fragment type based on how many memories were woven."""
        if sample_size <= 1:
            return FragmentType.MEMORY
        if sample_size == 2:
            return random.choice([FragmentType.SYNTHESIS, FragmentType.MEMORY])
        # Larger weaves can yield symbolic, archetypal, or prophetic fragments
        return random.choice([
            FragmentType.SYNTHESIS,
            FragmentType.SYMBOLIC,
            FragmentType.ARCHETYPAL,
            FragmentType.PROPHETIC,
        ])

    def _label_fragment(self, fragment_type: FragmentType,
                        memories: List[DreamMemory]) -> str:
        """Produce a short human-readable label for a fragment."""
        core = memories[0].label if memories else ""
        if fragment_type == FragmentType.MEMORY:
            return f"echo of {core}"
        if fragment_type == FragmentType.SYNTHESIS:
            return f"braid of {len(memories)} memories around '{core}'"
        if fragment_type == FragmentType.SYMBOLIC:
            return f"symbol drawn from '{core}'"
        if fragment_type == FragmentType.ARCHETYPAL:
            return f"archetype rising from '{core}'"
        if fragment_type == FragmentType.PROPHETIC:
            return f"vision branching from '{core}'"
        return core

    def _phase_distort(self) -> Dict[str, Any]:
        """DISTORT: fragments are colored and bent by the agent's emotional lens."""
        distorted_total = 0
        for agent in self._agents.values():
            if agent.dream_state not in (DreamState.DREAMING, DreamState.LUCID):
                continue
            lens = agent.current_lens or EmotionalLens.CLARITY
            profile = self._LENS_PROFILES.get(
                lens, self._LENS_PROFILES[EmotionalLens.CLARITY]
            )
            # Lucid agents resist distortion
            resist = agent.lucidity * 0.5
            for fragment in agent.fragments.values():
                if fragment.resolved:
                    continue
                if fragment.lens_applied is not None:
                    continue  # already distorted this dream
                if random.random() >= self._DISTORT_PROBABILITY:
                    continue
                coherence_delta = self._uniform(profile["coherence"]) * (1.0 - resist)
                intensity_delta = self._uniform(profile["intensity"])
                distortion_delta = self._uniform(profile["distortion"]) * (1.0 - resist)
                fragment.coherence = max(
                    0.0, min(1.0, fragment.coherence + coherence_delta)
                )
                fragment.emotional_intensity = max(
                    0.0, min(1.0, fragment.emotional_intensity + intensity_delta)
                )
                fragment.distortion_level = max(
                    0.0, min(1.0, fragment.distortion_level + distortion_delta)
                )
                fragment.lens_applied = lens
                distorted_total += 1
            # High lucidity promotes the agent into a lucid dream
            if agent.dream_state == DreamState.DREAMING and agent.lucidity >= 0.5:
                agent.dream_state = DreamState.LUCID
        self._record_event("distort", {"distorted": distorted_total})
        return {"distorted": distorted_total}

    def _phase_resolve(self) -> Dict[str, Any]:
        """RESOLVE: contradictions within fragments reconcile through dream logic."""
        resolved_total = 0
        resolving_states = (
            DreamState.DREAMING, DreamState.LUCID, DreamState.RESOLVING,
        )
        for agent in self._agents.values():
            if agent.dream_state not in resolving_states:
                continue
            # Lucid agents resolve contradictions more easily
            effective_threshold = max(
                0.1, self._RESOLVE_THRESHOLD - agent.lucidity * 0.15
            )
            for fragment in agent.fragments.values():
                if fragment.resolved:
                    continue
                if fragment.coherence < effective_threshold:
                    continue
                # Dream logic makes impossible things possible: coherence firms up
                boost = random.uniform(0.05, 0.2)
                fragment.coherence = min(1.0, fragment.coherence + boost)
                # Resolution absorbs some of the distortion
                fragment.distortion_level = max(
                    0.0, fragment.distortion_level - 0.2
                )
                fragment.resolved = True
                resolved_total += 1
            # Move dreaming agents into the resolving state for crystallization
            if agent.dream_state in (DreamState.DREAMING, DreamState.LUCID):
                agent.dream_state = DreamState.RESOLVING
        self._record_event("resolve", {"resolved": resolved_total})
        return {"resolved": resolved_total}

    def _phase_crystallize(self) -> Dict[str, Any]:
        """CRYSTALLIZE: resolved fragments condense into waking-life insights."""
        insights_total = 0
        now = time.time()
        for agent in self._agents.values():
            if agent.dream_state not in (
                DreamState.RESOLVING, DreamState.CRYSTALLIZING
            ):
                continue
            agent.dream_state = DreamState.CRYSTALLIZING
            for fragment in agent.fragments.values():
                if not fragment.resolved:
                    continue
                if fragment.coherence < self._CRYSTALLIZE_THRESHOLD:
                    continue
                # Skip fragments that already crystallized into an insight
                if self._already_crystallized(agent, fragment.fragment_id):
                    continue
                insight = self._crystallize_insight(agent, fragment, now)
                agent.insights.append(insight)
                agent.total_insights += 1
                agent.lucidity = min(1.0, agent.lucidity + self._LUCIDITY_GROWTH)
                insights_total += 1
            # Bound insight storage
            if len(agent.insights) > self._MAX_INSIGHTS_PER_AGENT:
                agent.insights = agent.insights[-self._MAX_INSIGHTS_PER_AGENT:]
            # Count this dream cycle as completed
            agent.total_dreams += 1
            # High lucidity wakes the agent; otherwise loop back to dream again
            if agent.lucidity >= 0.85:
                agent.dream_state = DreamState.AWAKENED
            else:
                agent.dream_state = DreamState.DREAMING
        self._record_event("crystallize", {"insights": insights_total})
        return {"insights": insights_total}

    def _already_crystallized(self, agent: DreamAgent, fragment_id: str) -> bool:
        """Check whether a fragment already produced an insight."""
        for insight in agent.insights[-50:]:
            if fragment_id in insight.source_fragments:
                return True
        return False

    def _crystallize_insight(self, agent: DreamAgent, fragment: DreamFragment,
                             now: float) -> DreamInsight:
        """Crystallize a resolved fragment into a dream insight."""
        insight_type = self._FRAGMENT_INSIGHT_MAP.get(
            fragment.fragment_type, InsightType.PATTERN
        )
        confidence = min(
            1.0, self._INSIGHT_CONFIDENCE_BASE + fragment.coherence * 0.5
        )
        return DreamInsight(
            insight_id=f"insight_{agent.agent_id}_{int(now * 1000)}_{random.randint(0, 9999):04d}",
            agent_id=agent.agent_id,
            source_fragments=[fragment.fragment_id],
            insight_type=insight_type,
            label=self._label_insight(insight_type, fragment),
            description=self._describe_insight(
                insight_type, fragment, fragment.lens_applied
            ),
            confidence=confidence,
            timestamp=now,
        )

    def _label_insight(self, insight_type: InsightType,
                       fragment: DreamFragment) -> str:
        """Produce a short label for a crystallized insight."""
        prefix = insight_type.value
        return f"{prefix}: {fragment.label}"

    def _describe_insight(self, insight_type: InsightType,
                          fragment: DreamFragment,
                          lens: Optional[EmotionalLens]) -> str:
        """Produce a human-readable description of a crystallized insight."""
        lens_text = f" through {lens.value}" if lens is not None else ""
        memory_count = len(fragment.source_memories)
        if insight_type == InsightType.PATTERN:
            return (f"A recurring pattern surfaced from {memory_count} "
                    f"memories{lens_text}: {fragment.label}.")
        if insight_type == InsightType.RESOLUTION:
            return (f"An emotional conflict within '{fragment.label}' resolved"
                    f"{lens_text}; coherence now {fragment.coherence:.2f}.")
        if insight_type == InsightType.FORESIGHT:
            return (f"An anticipatory vision crystallized{lens_text}: "
                    f"{fragment.label}.")
        if insight_type == InsightType.INTEGRATION:
            return (f"{memory_count} fragmented memories wove into a single "
                    f"self{lens_text}: {fragment.label}.")
        if insight_type == InsightType.REVELATION:
            return (f"A sudden understanding emerged{lens_text}: "
                    f"{fragment.label}.")
        return fragment.label

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Get the full dream state of an agent."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent.agent_id,
                "dream_state": agent.dream_state.value,
                "lucidity": round(agent.lucidity, 4),
                "dream_depth": round(agent.dream_depth, 4),
                "current_lens": agent.current_lens.value if agent.current_lens else None,
                "total_memories": len(agent.memory_shards),
                "total_fragments": len(agent.fragments),
                "total_insights": len(agent.insights),
                "surfaced_memories": sum(
                    1 for m in agent.memory_shards.values() if m.surfaced
                ),
                "resolved_fragments": sum(
                    1 for f in agent.fragments.values() if f.resolved
                ),
                "agent_total_dreams": agent.total_dreams,
                "agent_total_fragments": agent.total_fragments,
                "agent_total_insights": agent.total_insights,
            }

    def get_fragments(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get the dream fragments currently held by an agent."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return []
            ordered = sorted(
                agent.fragments.values(),
                key=lambda f: f.timestamp,
                reverse=True,
            )
            return [
                {
                    "fragment_id": f.fragment_id,
                    "source_memories": list(f.source_memories),
                    "fragment_type": f.fragment_type.value,
                    "label": f.label,
                    "coherence": round(f.coherence, 4),
                    "emotional_intensity": round(f.emotional_intensity, 4),
                    "lens_applied": f.lens_applied.value if f.lens_applied else None,
                    "distortion_level": round(f.distortion_level, 4),
                    "resolved": f.resolved,
                    "timestamp": f.timestamp,
                }
                for f in ordered
            ]

    def get_insights(self, agent_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get the insights an agent has crystallized from dreams."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return []
            recent = list(agent.insights)[-limit:] if limit > 0 else list(agent.insights)
            return [
                {
                    "insight_id": i.insight_id,
                    "agent_id": i.agent_id,
                    "source_fragments": list(i.source_fragments),
                    "insight_type": i.insight_type.value,
                    "label": i.label,
                    "description": i.description,
                    "confidence": round(i.confidence, 4),
                    "timestamp": i.timestamp,
                }
                for i in recent
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent synthesizer events."""
        with self._global_lock:
            return list(self._events_log)[-limit:] if limit > 0 else list(self._events_log)

    def get_status(self) -> Dict[str, Any]:
        """Get global synthesizer status."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_agents": len(self._agents),
                "dreaming_agents": sum(
                    1 for a in self._agents.values()
                    if a.dream_state != DreamState.AWAKE
                ),
                "lucid_agents": sum(
                    1 for a in self._agents.values()
                    if a.dream_state == DreamState.LUCID
                ),
                "awakened_agents": sum(
                    1 for a in self._agents.values()
                    if a.dream_state == DreamState.AWAKENED
                ),
                "stats": dict(self._stats),
            }

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire synthesizer."""
        with self._global_lock:
            n_agents = len(self._agents)
            self._agents.clear()
            self._phase = DreamPhase.DRIFT
            self._cycle_count = 0
            self._events_log.clear()
            self._stats = self._init_stats()
            self._record_event("synthesizer_reset", {"cleared_agents": n_agents})
            return {"reset": True, "cleared_agents": n_agents}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _seed_demo_agent(self) -> None:
        """Seed a demo agent with memories and enter a dream, for simulation."""
        agent_id = "demo_dreamer"
        agent = DreamAgent(agent_id=agent_id, lucidity=0.1)
        memories = [
            ("m_loss", "loss at the river", 0.85, 0.6),
            ("m_victory", "victory at dawn", 0.75, 0.55),
            ("m_betrayal", "betrayal in the garden", 0.9, 0.4),
            ("m_gift", "gift from a stranger", 0.6, 0.7),
            ("m_storm", "storm on the mountain", 0.7, 0.5),
            ("m_promise", "promise at dusk", 0.65, 0.65),
        ]
        for memory_id, label, charge, clarity in memories:
            agent.memory_shards[memory_id] = DreamMemory(
                memory_id=memory_id,
                label=label,
                emotional_charge=charge,
                clarity=clarity,
                source="waking",
                surfaced=False,
            )
        agent.current_lens = EmotionalLens.FEAR
        agent.dream_state = DreamState.DRIFTING
        agent.dream_depth = 0.1
        self._agents[agent_id] = agent
        self._stats["total_agents"] = len(self._agents)
        self._record_event("demo_agent_seeded", {"agent_id": agent_id})

    @staticmethod
    def _uniform(span: Tuple[float, float]) -> float:
        """Sample a uniform value within a (low, high) span."""
        low, high = span
        return random.uniform(low, high)

    def _init_stats(self) -> Dict[str, Any]:
        """Initialize the aggregate statistics dictionary."""
        return {
            "total_agents": 0,
            "total_cycles": 0,
            "total_memories": 0,
            "total_fragments": 0,
            "total_insights": 0,
            "surfaced_memories": 0,
            "resolved_fragments": 0,
            "active_fragments": 0,
            "dreaming_agents": 0,
            "lucid_agents": 0,
            "awakened_agents": 0,
            "avg_lucidity": 0.0,
            "avg_dream_depth": 0.0,
            "avg_insight_confidence": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        """Recompute aggregate statistics from the current state."""
        agents = list(self._agents.values())
        self._stats["total_agents"] = len(agents)
        self._stats["total_cycles"] = self._cycle_count
        self._stats["total_memories"] = sum(len(a.memory_shards) for a in agents)
        self._stats["total_fragments"] = sum(len(a.fragments) for a in agents)
        self._stats["total_insights"] = sum(len(a.insights) for a in agents)
        self._stats["surfaced_memories"] = sum(
            1 for a in agents for m in a.memory_shards.values() if m.surfaced
        )
        self._stats["resolved_fragments"] = sum(
            1 for a in agents for f in a.fragments.values() if f.resolved
        )
        self._stats["active_fragments"] = self._stats["total_fragments"]
        self._stats["dreaming_agents"] = sum(
            1 for a in agents if a.dream_state != DreamState.AWAKE
        )
        self._stats["lucid_agents"] = sum(
            1 for a in agents if a.dream_state == DreamState.LUCID
        )
        self._stats["awakened_agents"] = sum(
            1 for a in agents if a.dream_state == DreamState.AWAKENED
        )
        if agents:
            self._stats["avg_lucidity"] = sum(a.lucidity for a in agents) / len(agents)
            self._stats["avg_dream_depth"] = (
                sum(a.dream_depth for a in agents) / len(agents)
            )
        else:
            self._stats["avg_lucidity"] = 0.0
            self._stats["avg_dream_depth"] = 0.0
        all_insights = [i for a in agents for i in a.insights]
        if all_insights:
            self._stats["avg_insight_confidence"] = (
                sum(i.confidence for i in all_insights) / len(all_insights)
            )
        else:
            self._stats["avg_insight_confidence"] = 0.0

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record a synthesizer event in the events log."""
        self._events_log.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
