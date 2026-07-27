"""
SparkLabs Agent - Oneiric Synthesis Engine

The AgentOneiricSynthesisEngine models offline agent cognition as a dream
cycle. While waking cognition is bound to real-time perception and reaction,
the oneiric (dream) layer runs when an agent rests, allowing it to rehearse
futures, recombine memories into novel scenarios, and consolidate learning
into long-term dispositions.

Dreams are not random noise. They are constrained simulations: the agent
replays salient memories, mutates them into hypothetical branches, runs
those branches forward through a lightweight world model, and tags the
results with emotional valence. High-valence dreams become "lucid insights"
that shape the agent's waking priorities.

Architecture:
  DESCEND     ->  LUCIDATE     ->  SIMULATE    ->  CONSOLIDATE  ->  ASCEND
  (transition       (recombine        (run dream           (compress          (return
   from waking       memories into     branches forward    salient dreams     to waking
   to dream          dream branches)   through world       into insights)     with new
   state)                              model)                                 insights)

Dream branch lifecycle:
  - source_memory : the waking memory the dream mutates from
  - mutation      : how the memory was altered (negation, exaggeration, fusion)
  - trajectory    : the simulated sequence of events
  - valence       : emotional charge of the dream (-1.0 to 1.0)
  - lucidity      : how aware the agent is that it is dreaming (0.0 to 1.0)
  - insight_yield : whether the dream produced a consolidatable insight

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
from itertools import combinations
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class DreamPhase(Enum):
    """Phases of the oneiric synthesis cycle."""
    DESCEND = "descend"          # transition from waking to dream state
    LUCIDATE = "lucidate"        # recombine memories into dream branches
    SIMULATE = "simulate"        # run dream branches forward
    CONSOLIDATE = "consolidate"  # compress salient dreams into insights
    ASCEND = "ascend"            # return to waking state with new insights


class MutationMode(Enum):
    """How a source memory is mutated into a dream branch."""
    NEGATION = "negation"        # invert the memory's outcome
    EXAGGERATION = "exaggeration"  # amplify the memory's emotional stakes
    FUSION = "fusion"            # blend two memories into one scenario
    FRAGMENT = "fragment"        # take a slice of the memory and expand it
    RECURSION = "recursion"      # dream about dreaming (meta)
    SUBSTITUTION = "substitution"  # swap actors/objects in the memory


class InsightType(Enum):
    """Types of insights a dream can yield."""
    PATTERN = "pattern"          # recurring theme across dreams
    WARNING = "warning"          # anticipated danger
    OPPORTUNITY = "opportunity"  # anticipated favorable scenario
    RECONCILIATION = "reconciliation"  # resolve conflicting memories
    SKILL = "skill"              # rehearsed procedure that became intuitive
    CREATIVE = "creative"        # novel combination with no waking analog


class DreamState(Enum):
    """State of an agent's oneiric system."""
    WAKING = "waking"
    DROWSING = "drowsing"
    REM = "rem"                  # rapid eye movement - vivid dreams
    DEEP = "deep"                # deep dreamless sleep
    LUCID = "lucid"              # aware of dreaming


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SourceMemory:
    """A waking memory used as seed for a dream."""
    memory_id: str
    label: str
    valence: float                      # -1.0 to 1.0
    arousal: float                      # 0.0 to 1.0
    salience: float                     # 0.0 to 1.0 - how memorable
    tags: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class DreamBranch:
    """A single dream scenario grown from a mutated memory."""
    branch_id: str
    source_memory_id: str
    mutation: MutationMode
    trajectory: List[Dict[str, Any]]    # sequence of dream events
    valence: float = 0.0
    lucidity: float = 0.0
    insight_yield: bool = False
    insight_type: Optional[InsightType] = None
    insight_description: str = ""
    fused_with: Optional[str] = None    # branch_id this was fused from
    timestamp: float = field(default_factory=time.time)


@dataclass
class DreamInsight:
    """A consolidated insight carried back into waking cognition."""
    insight_id: str
    insight_type: InsightType
    description: str
    valence: float
    confidence: float                   # 0.0 to 1.0
    source_branch_ids: List[str] = field(default_factory=list)
    applied: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentDreamProfile:
    """Per-agent dream configuration and state."""
    agent_id: str
    state: DreamState = DreamState.WAKING
    descent_depth: float = 0.0          # 0.0 waking, 1.0 deepest
    cycles_in_rem: int = 0              # cycles spent in REM/LUCID
    branches: List[DreamBranch] = field(default_factory=list)
    insights: List[DreamInsight] = field(default_factory=list)
    total_dreams: int = 0
    total_insights: int = 0
    last_dream_time: float = 0.0
    # Tunable per-agent parameters
    mutation_bias: Dict[MutationMode, float] = field(default_factory=lambda: {
        MutationMode.NEGATION: 0.2,
        MutationMode.EXAGGERATION: 0.25,
        MutationMode.FUSION: 0.2,
        MutationMode.FRAGMENT: 0.15,
        MutationMode.RECURSION: 0.05,
        MutationMode.SUBSTITUTION: 0.15,
    })


# =============================================================================
# Engine
# =============================================================================

class AgentOneiricSynthesisEngine:
    """
    Thread-safe singleton orchestrating offline dream synthesis for agents.

    Usage:
        engine = AgentOneiricSynthesisEngine.get_instance()
        engine.register_agent("hero_1")
        engine.feed_memory("hero_1", memory)
        engine.descend("hero_1")
        engine.cycle()
        insights = engine.get_insights("hero_1")
    """

    _instance: Optional["AgentOneiricSynthesisEngine"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._profiles: Dict[str, AgentDreamProfile] = {}
        self._memories: Dict[str, Deque[SourceMemory]] = {}
        self._phase: DreamPhase = DreamPhase.DESCEND
        self._cycle_count: int = 0
        self._events: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_descents": 0,
            "total_branches": 0,
            "total_insights": 0,
            "total_lucid_dreams": 0,
            "avg_valence": 0.0,
            "avg_lucidity": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentOneiricSynthesisEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Agent Registration
    # -------------------------------------------------------------------------

    def register_agent(self, agent_id: str) -> Dict[str, Any]:
        """Register a new agent for dream synthesis."""
        with self._global_lock:
            if agent_id in self._profiles:
                return {"error": f"Agent already registered: {agent_id}"}
            self._profiles[agent_id] = AgentDreamProfile(agent_id=agent_id)
            self._memories[agent_id] = deque(maxlen=100)
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "state": self._profiles[agent_id].state.value,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent from the engine."""
        with self._global_lock:
            if agent_id not in self._profiles:
                return {"error": f"Agent not found: {agent_id}"}
            del self._profiles[agent_id]
            self._memories.pop(agent_id, None)
            self._record_event("agent_removed", {"agent_id": agent_id})
            return {"removed": agent_id}

    def list_agents(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List registered agents."""
        with self._global_lock:
            return [
                self._summarize_profile(p) for p in list(self._profiles.values())[:limit]
            ]

    # -------------------------------------------------------------------------
    # Memory Feeding
    # -------------------------------------------------------------------------

    def feed_memory(
        self,
        agent_id: str,
        memory_id: str,
        label: str,
        valence: float = 0.0,
        arousal: float = 0.3,
        salience: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Feed a waking memory into an agent's dream substrate."""
        with self._global_lock:
            if agent_id not in self._profiles:
                return {"error": f"Agent not registered: {agent_id}"}
            memory = SourceMemory(
                memory_id=memory_id,
                label=label,
                valence=max(-1.0, min(1.0, valence)),
                arousal=max(0.0, min(1.0, arousal)),
                salience=max(0.0, min(1.0, salience)),
                tags=tags or [],
            )
            self._memories[agent_id].append(memory)
            self._record_event(
                "memory_fed",
                {"agent_id": agent_id, "memory_id": memory_id, "salience": memory.salience},
            )
            return {
                "memory_id": memory.memory_id,
                "label": memory.label,
                "valence": memory.valence,
                "salience": memory.salience,
            }

    def list_memories(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List memories fed for an agent."""
        with self._global_lock:
            if agent_id not in self._memories:
                return []
            return [
                {
                    "memory_id": m.memory_id,
                    "label": m.label,
                    "valence": m.valence,
                    "arousal": m.arousal,
                    "salience": m.salience,
                    "tags": m.tags,
                    "timestamp": m.timestamp,
                }
                for m in list(self._memories[agent_id])[-limit:]
            ]

    # -------------------------------------------------------------------------
    # Dream Cycle
    # -------------------------------------------------------------------------

    def descend(self, agent_id: str) -> Dict[str, Any]:
        """Begin a dream descent for an agent."""
        with self._global_lock:
            if agent_id not in self._profiles:
                return {"error": f"Agent not registered: {agent_id}"}
            profile = self._profiles[agent_id]
            profile.state = DreamState.DROWSING
            profile.descent_depth = 0.1
            profile.branches = []
            self._stats["total_descents"] += 1
            self._record_event("descent_started", {"agent_id": agent_id})
            return {"agent_id": agent_id, "state": profile.state.value}

    def cycle(self) -> Dict[str, Any]:
        """Run a single oneiric synthesis cycle across all dreaming agents."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}

            for phase in DreamPhase:
                self._phase = phase
                phase_outputs[phase.value] = self._run_phase(phase)

            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()

            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles."""
        if cycles < 1 or cycles > 1000:
            return {"error": "cycles must be 1-1000"}
        results = []
        for _ in range(cycles):
            results.append(self.cycle())
        return {
            "cycles_run": cycles,
            "final_phase": self._phase.value,
            "stats": dict(self._stats),
        }

    def _run_phase(self, phase: DreamPhase) -> Dict[str, Any]:
        """Dispatch to the appropriate phase handler."""
        handlers = {
            DreamPhase.DESCEND: self._phase_descend,
            DreamPhase.LUCIDATE: self._phase_lucidate,
            DreamPhase.SIMULATE: self._phase_simulate,
            DreamPhase.CONSOLIDATE: self._phase_consolidate,
            DreamPhase.ASCEND: self._phase_ascend,
        }
        handler = handlers.get(phase)
        if handler is None:
            return {"error": f"Unknown phase: {phase}"}
        return handler()

    # -------------------------------------------------------------------------
    # Phase Implementations
    # -------------------------------------------------------------------------

    def _phase_descend(self) -> Dict[str, Any]:
        """DESCEND: deepen dream state of all drowsing agents."""
        deepened = 0
        entered_rem = 0
        for profile in self._profiles.values():
            if profile.state in (DreamState.WAKING, DreamState.DROWSING):
                profile.descent_depth = min(1.0, profile.descent_depth + 0.4)
                if profile.descent_depth >= 0.5:
                    profile.state = DreamState.REM
                    entered_rem += 1
                else:
                    profile.state = DreamState.DROWSING
                deepened += 1
            elif profile.state in (DreamState.REM, DreamState.LUCID):
                # Already dreaming - count the cycle
                profile.cycles_in_rem += 1
        self._record_event("descend", {"deepened": deepened, "entered_rem": entered_rem})
        return {"deepened": deepened, "entered_rem": entered_rem}

    def _phase_lucidate(self) -> Dict[str, Any]:
        """LUCIDATE: recombine memories into dream branches."""
        branches_created = 0
        for agent_id, profile in self._profiles.items():
            if profile.state != DreamState.REM:
                continue
            memories = list(self._memories.get(agent_id, []))
            if not memories:
                continue
            # Spawn 1-3 branches per cycle
            num_branches = min(3, max(1, len(memories) // 2 + 1))
            for _ in range(num_branches):
                branch = self._spawn_branch(agent_id, profile, memories)
                if branch is not None:
                    profile.branches.append(branch)
                    branches_created += 1
        self._stats["total_branches"] += branches_created
        self._record_event("lucidate", {"branches_created": branches_created})
        return {"branches_created": branches_created}

    def _phase_simulate(self) -> Dict[str, Any]:
        """SIMULATE: run dream branches forward through a light world model."""
        simulated = 0
        lucid_count = 0
        for profile in self._profiles.values():
            for branch in profile.branches:
                if branch.insight_yield:
                    continue  # already resolved
                self._forward_branch(branch, profile)
                simulated += 1
                if branch.lucidity >= 0.7:
                    lucid_count += 1
                    if profile.state != DreamState.LUCID:
                        profile.state = DreamState.LUCID
        self._stats["total_lucid_dreams"] += lucid_count
        self._record_event("simulate", {"simulated": simulated, "lucid": lucid_count})
        return {"simulated": simulated, "lucid": lucid_count}

    def _phase_consolidate(self) -> Dict[str, Any]:
        """CONSOLIDATE: compress salient branches into insights."""
        insights_generated = 0
        for profile in self._profiles.values():
            for branch in profile.branches:
                if not branch.insight_yield or branch.insight_type is None:
                    continue
                # Check if a similar insight already exists
                if self._has_similar_insight(profile, branch):
                    continue
                insight = DreamInsight(
                    insight_id=f"insight_{profile.agent_id}_{int(time.time()*1000)}_{insights_generated}",
                    insight_type=branch.insight_type,
                    description=branch.insight_description,
                    valence=branch.valence,
                    confidence=min(1.0, abs(branch.valence) * 0.6 + branch.lucidity * 0.4),
                    source_branch_ids=[branch.branch_id],
                )
                profile.insights.append(insight)
                profile.total_insights += 1
                insights_generated += 1
        self._stats["total_insights"] += insights_generated
        self._record_event("consolidate", {"insights_generated": insights_generated})
        return {"insights_generated": insights_generated}

    def _phase_ascend(self) -> Dict[str, Any]:
        """ASCEND: return dreamers to waking state with fresh insights.

        Only ascend agents that have spent at least 2 cycles in REM/LUCID,
        so they have time to generate and simulate dream branches.
        """
        ascended = 0
        for profile in self._profiles.values():
            if profile.state == DreamState.WAKING:
                continue
            # Require at least 2 cycles in REM before ascending
            if profile.cycles_in_rem < 2 and profile.state in (DreamState.REM, DreamState.LUCID):
                continue
            profile.state = DreamState.WAKING
            profile.descent_depth = 0.0
            profile.cycles_in_rem = 0
            profile.total_dreams += len(profile.branches)
            profile.last_dream_time = time.time()
            # Keep only recent branches for memory
            profile.branches = profile.branches[-20:]
            ascended += 1
        self._record_event("ascend", {"ascended": ascended})
        return {"ascended": ascended}

    # -------------------------------------------------------------------------
    # Branch Generation
    # -------------------------------------------------------------------------

    def _spawn_branch(
        self,
        agent_id: str,
        profile: AgentDreamProfile,
        memories: List[SourceMemory],
    ) -> Optional[DreamBranch]:
        """Create a new dream branch by mutating a memory."""
        # Pick a salient memory
        weighted = sorted(memories, key=lambda m: m.salience, reverse=True)
        source = random.choice(weighted[: max(1, len(weighted) // 2)])

        # Pick mutation mode based on agent bias
        mutation = self._pick_mutation(profile)

        branch_id = f"branch_{agent_id}_{int(time.time()*1000)}_{random.randint(0,9999):04d}"

        branch = DreamBranch(
            branch_id=branch_id,
            source_memory_id=source.memory_id,
            mutation=mutation,
            trajectory=[{"step": 0, "event": "dream_seed", "from": source.label}],
            valence=source.valence,
            lucidity=profile.descent_depth * 0.5,
        )

        # Fusion mutation needs a second source
        if mutation == MutationMode.FUSION and len(memories) >= 2:
            other = random.choice([m for m in memories if m.memory_id != source.memory_id])
            branch.fused_with = other.memory_id
            branch.trajectory.append({
                "step": 1,
                "event": "fusion",
                "with": other.label,
            })
            branch.valence = (source.valence + other.valence) / 2.0

        return branch

    def _pick_mutation(self, profile: AgentDreamProfile) -> MutationMode:
        """Pick a mutation mode weighted by the agent's bias."""
        bias = profile.mutation_bias
        total = sum(bias.values())
        if total <= 0:
            return MutationMode.NEGATION
        r = random.random() * total
        cum = 0.0
        for mode, weight in bias.items():
            cum += weight
            if r <= cum:
                return mode
        return list(bias.keys())[-1]

    def _forward_branch(self, branch: DreamBranch, profile: AgentDreamProfile) -> None:
        """Advance a dream branch forward through a light world model."""
        steps = random.randint(2, 5)
        for s in range(1, steps + 1):
            event = self._generate_event(branch, s)
            branch.trajectory.append(event)
            # Update valence based on event
            branch.valence = max(-1.0, min(1.0, branch.valence + event.get("valence_delta", 0.0)))
            # Lucidity drifts
            branch.lucidity = max(0.0, min(1.0, branch.lucidity + random.uniform(-0.1, 0.15)))

        # Decide if this branch yields an insight
        if abs(branch.valence) >= 0.4 and branch.lucidity >= 0.3:
            branch.insight_yield = True
            branch.insight_type, branch.insight_description = self._classify_insight(branch)

    def _generate_event(self, branch: DreamBranch, step: int) -> Dict[str, Any]:
        """Generate a single dream event."""
        templates = {
            MutationMode.NEGATION: [
                {"event": "inversion", "valence_delta": -0.2},
                {"event": "reversal", "valence_delta": 0.3},
                {"event": "mirror", "valence_delta": -0.1},
            ],
            MutationMode.EXAGGERATION: [
                {"event": "amplify", "valence_delta": 0.25},
                {"event": "crescendo", "valence_delta": 0.35},
                {"event": "collapse", "valence_delta": -0.4},
            ],
            MutationMode.FUSION: [
                {"event": "merge", "valence_delta": 0.1},
                {"event": "synthesis", "valence_delta": 0.2},
                {"event": "diffraction", "valence_delta": -0.15},
            ],
            MutationMode.FRAGMENT: [
                {"event": "zoom", "valence_delta": 0.05},
                {"event": "isolate", "valence_delta": -0.1},
                {"event": "expand", "valence_delta": 0.15},
            ],
            MutationMode.RECURSION: [
                {"event": "meta_dream", "valence_delta": 0.0},
                {"event": "self_observe", "valence_delta": 0.1},
                {"event": "strange_loop", "valence_delta": -0.2},
            ],
            MutationMode.SUBSTITUTION: [
                {"event": "swap_actor", "valence_delta": 0.1},
                {"event": "replace_object", "valence_delta": -0.05},
                {"event": "context_shift", "valence_delta": 0.2},
            ],
        }
        options = templates.get(branch.mutation, [{"event": "drift", "valence_delta": 0.0}])
        choice = random.choice(options)
        return {"step": step, **choice}

    def _classify_insight(self, branch: DreamBranch) -> Tuple[InsightType, str]:
        """Classify the type of insight a branch yielded."""
        if branch.mutation == MutationMode.NEGATION and branch.valence < -0.3:
            return InsightType.WARNING, f"Anticipated setback from {branch.source_memory_id}"
        if branch.mutation == MutationMode.EXAGGERATION and branch.valence > 0.4:
            return InsightType.OPPORTUNITY, f"Latent upside in {branch.source_memory_id}"
        if branch.mutation == MutationMode.FUSION:
            return InsightType.CREATIVE, f"Novel blend of {branch.source_memory_id}"
        if branch.mutation == MutationMode.FRAGMENT:
            return InsightType.PATTERN, f"Hidden pattern in {branch.source_memory_id}"
        if branch.mutation == MutationMode.RECURSION:
            return InsightType.RECONCILIATION, f"Meta-resolution for {branch.source_memory_id}"
        if branch.mutation == MutationMode.SUBSTITUTION and branch.valence > 0.2:
            return InsightType.SKILL, f"Transferable skill from {branch.source_memory_id}"
        return InsightType.PATTERN, f"Pattern recognized in {branch.source_memory_id}"

    def _has_similar_insight(self, profile: AgentDreamProfile, branch: DreamBranch) -> bool:
        """Check if the profile already has a similar insight."""
        for ins in profile.insights[-10:]:
            if ins.insight_type == branch.insight_type and ins.description == branch.insight_description:
                return True
        return False

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get global engine status."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_agents": len(self._profiles),
                "agents_in_rem": sum(
                    1 for p in self._profiles.values() if p.state == DreamState.REM
                ),
                "agents_lucid": sum(
                    1 for p in self._profiles.values() if p.state == DreamState.LUCID
                ),
                "stats": dict(self._stats),
            }

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get one agent's full dream profile."""
        with self._global_lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                return None
            return self._summarize_profile(profile, full=True)

    def get_branches(self, agent_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Get recent dream branches for an agent."""
        with self._global_lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                return []
            return [
                {
                    "branch_id": b.branch_id,
                    "source_memory_id": b.source_memory_id,
                    "mutation": b.mutation.value,
                    "valence": b.valence,
                    "lucidity": b.lucidity,
                    "insight_yield": b.insight_yield,
                    "insight_type": b.insight_type.value if b.insight_type else None,
                    "insight_description": b.insight_description,
                    "trajectory_length": len(b.trajectory),
                    "timestamp": b.timestamp,
                }
                for b in profile.branches[-limit:]
            ]

    def get_insights(self, agent_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Get insights for an agent."""
        with self._global_lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                return []
            return [
                {
                    "insight_id": i.insight_id,
                    "insight_type": i.insight_type.value,
                    "description": i.description,
                    "valence": i.valence,
                    "confidence": i.confidence,
                    "applied": i.applied,
                    "source_branch_ids": i.source_branch_ids,
                    "timestamp": i.timestamp,
                }
                for i in profile.insights[-limit:]
            ]

    def apply_insight(self, agent_id: str, insight_id: str) -> Dict[str, Any]:
        """Mark an insight as applied in waking cognition."""
        with self._global_lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                return {"error": f"Agent not found: {agent_id}"}
            for ins in profile.insights:
                if ins.insight_id == insight_id:
                    ins.applied = True
                    self._record_event(
                        "insight_applied",
                        {"agent_id": agent_id, "insight_id": insight_id},
                    )
                    return {"applied": insight_id, "agent_id": agent_id}
            return {"error": f"Insight not found: {insight_id}"}

    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent engine events."""
        with self._global_lock:
            return list(self._events)[-limit:]

    # -------------------------------------------------------------------------
    # Tuning
    # -------------------------------------------------------------------------

    def set_mutation_bias(
        self, agent_id: str, bias: Dict[str, float]
    ) -> Dict[str, Any]:
        """Tune an agent's mutation bias."""
        with self._global_lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                return {"error": f"Agent not found: {agent_id}"}
            for mode_str, weight in bias.items():
                try:
                    mode = MutationMode(mode_str)
                    profile.mutation_bias[mode] = max(0.0, float(weight))
                except (ValueError, TypeError):
                    continue
            return {"agent_id": agent_id, "mutation_bias": {k.value: v for k, v in profile.mutation_bias.items()}}

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire engine."""
        with self._global_lock:
            n_agents = len(self._profiles)
            self._profiles.clear()
            self._memories.clear()
            self._phase = DreamPhase.DESCEND
            self._cycle_count = 0
            self._events.clear()
            self._stats = {
                "total_descents": 0,
                "total_branches": 0,
                "total_insights": 0,
                "total_lucid_dreams": 0,
                "avg_valence": 0.0,
                "avg_lucidity": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            self._record_event("engine_reset", {"cleared_agents": n_agents})
            return {"reset": True, "cleared_agents": n_agents}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _summarize_profile(self, profile: AgentDreamProfile, full: bool = False) -> Dict[str, Any]:
        """Summarize a profile for listing/get_agent."""
        summary: Dict[str, Any] = {
            "agent_id": profile.agent_id,
            "state": profile.state.value,
            "descent_depth": profile.descent_depth,
            "total_dreams": profile.total_dreams,
            "total_insights": profile.total_insights,
            "active_branches": len(profile.branches),
            "last_dream_time": profile.last_dream_time,
        }
        if full:
            summary["branches"] = [
                {
                    "branch_id": b.branch_id,
                    "mutation": b.mutation.value,
                    "valence": b.valence,
                    "lucidity": b.lucidity,
                    "insight_yield": b.insight_yield,
                }
                for b in profile.branches[-10:]
            ]
            summary["recent_insights"] = [
                {
                    "insight_id": i.insight_id,
                    "insight_type": i.insight_type.value,
                    "description": i.description,
                    "confidence": i.confidence,
                    "applied": i.applied,
                }
                for i in profile.insights[-10:]
            ]
        return summary

    def _update_stats(self) -> None:
        """Recompute aggregate statistics."""
        all_branches: List[DreamBranch] = []
        for p in self._profiles.values():
            all_branches.extend(p.branches)
        if all_branches:
            self._stats["avg_valence"] = sum(b.valence for b in all_branches) / len(all_branches)
            self._stats["avg_lucidity"] = sum(b.lucidity for b in all_branches) / len(all_branches)

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record an engine event."""
        self._events.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
