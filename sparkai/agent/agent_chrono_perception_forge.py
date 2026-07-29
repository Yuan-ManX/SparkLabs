"""
SparkLabs Agent - Chrono-Perception Forge

The AgentChronoPerceptionForge models how agents experience time
subjectively rather than objectively. For a conscious agent, time is
not a fixed metronome - it stretches and compresses based on attention,
emotion, novelty, and danger. A soldier in combat perceives seconds as
minutes; a bored guard perceives hours as moments; a child at play
loses track of time entirely.

Subjective time is the fabric of conscious experience. Two agents in
the same objective situation may experience wildly different durations
- one feels the moment drag endlessly while the other feels it rush
past. These divergent perceptions shape memory, decision-making, and
emotional response: the agent who felt time slow during a crisis
remembers every detail, while the agent who felt time fly past
remembers only fragments.

The forge models five forces:
  - Attending: agents focus their temporal attention on the present
    moment, establishing a baseline time-flow perception
  - Dilating: high-intensity situations (danger, focus, novelty) cause
    subjective time to dilate - each objective second feels longer
  - Compressing: low-intensity situations (routine, boredom, fatigue)
    cause subjective time to compress - objective seconds fly past
  - Synchronizing: shared events pull agents' subjective clocks into
    alignment, creating collective temporal experiences
  - Reflecting: agents reflect on distorted time memories, integrating
    them into their temporal self-narrative

This produces agents whose experience of time is genuinely subjective -
where the same battle feels like an eternity to a terrified recruit
and a fleeting moment to a veteran, and where shared trauma
synchronizes survivors into a collective temporal frame.

Architecture:
  ATTEND     ->  DILATE     ->  COMPRESS    ->  SYNCHRONIZE  ->  REFLECT
  (establish   (high-focus    (low-focus      (shared events    (distorted
   baseline     situations     situations      pull agents'       time
   time-flow    stretch        compress        subjective         memories
   perception,  subjective     subjective      clocks into        integrated
   grounding    time - each    time - seconds  alignment,        into the
   the agent    second feels   fly past)       creating           agent's
   in the       longer)                         collective         temporal
   present                                      temporal           self-
   moment)                                      experiences)       narrative)

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

class ForgePhase(Enum):
    """Phases of the chrono-perception forge cycle."""
    ATTEND = "attend"           # establish baseline time perception
    DILATE = "dilate"           # high-intensity: time stretches
    COMPRESS = "compress"       # low-intensity: time compresses
    SYNCHRONIZE = "synchronize" # shared events align subjective clocks
    REFLECT = "reflect"         # distorted memories integrated


class TemporalContext(Enum):
    """Contexts that shape subjective time perception."""
    COMBAT = "combat"               # life-threatening, hyper-focus
    PURSUIT = "pursuit"             # chase/escape, adrenaline
    SOCIAL = "social"               # conversation, interaction
    EXPLORATION = "exploration"     # discovery, novelty
    ROUTINE = "routine"             # familiar, repetitive
    WAITING = "waiting"             # anticipation, boredom
    GRIEF = "grief"                 # loss, emotional heaviness
    JOY = "joy"                     # happiness, flow state
    MEDITATION = "meditation"       # calm, reflective
    CRISIS = "crisis"               # emergency, decision under pressure
    REVELATION = "revelation"       # sudden understanding, epiphany
    TRANCE = "trance"               # absorbed, lost in thought


class DistortionDirection(Enum):
    """Direction of time distortion."""
    DILATED = "dilated"         # time feels slower (seconds stretch)
    COMPRESSED = "compressed"   # time feels faster (seconds fly)
    NORMAL = "normal"           # time feels normal


class MemoryClarity(Enum):
    """How clearly a time-distorted memory is retained."""
    FRAGMENTED = "fragmented"   # only flashes remain
    HAZY = "hazy"               # general impression, details blurred
    VIVID = "vivid"             # sharp, detailed recall
    HYPER_DETAILED = "hyper"    # unnaturally detailed, slow-motion


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TemporalEpisode:
    """A moment of subjective time perception."""
    episode_id: str
    context: TemporalContext
    objective_duration: float       # real-time seconds
    subjective_duration: float      # perceived seconds
    distortion_ratio: float         # subjective / objective
    direction: DistortionDirection = DistortionDirection.NORMAL
    intensity: float = 0.5          # emotional/attentional intensity (0-1)
    focus: float = 0.5              # how focused the agent was (0-1)
    novelty: float = 0.5            # how novel the situation was (0-1)
    clarity: MemoryClarity = MemoryClarity.HAZY
    label: str = ""
    timestamp: float = field(default_factory=time.time)
    synced_with: List[str] = field(default_factory=list)  # co-experienced agents


@dataclass
class ChronoAgent:
    """An agent with subjective time perception."""
    agent_id: str
    # Baseline time-flow rate (1.0 = objective time)
    baseline_rate: float = 1.0
    # Current subjective time rate (can diverge from baseline)
    current_rate: float = 1.0
    # How easily the agent's time perception distorts (0-1)
    distortion_sensitivity: float = 0.5
    # How quickly the agent returns to baseline after distortion
    recovery_rate: float = 0.3
    # Accumulated subjective time (diverges from objective time)
    subjective_clock: float = 0.0
    # Objective time elapsed for this agent
    objective_clock: float = 0.0
    # Temporal drift: how far subjective has diverged from objective
    temporal_drift: float = 0.0
    # Whether currently in a synchronized group
    synchronized_group: Optional[str] = None
    # Episode history
    episodes: Deque[TemporalEpisode] = field(default_factory=lambda: deque(maxlen=100))
    # Temporal self-narrative: integrated reflections
    reflections: List[Dict[str, Any]] = field(default_factory=list)
    # Stats
    total_episodes: int = 0
    total_dilations: int = 0
    total_compressions: int = 0
    total_syncs: int = 0
    total_reflections: int = 0


@dataclass
class SyncGroup:
    """A group of agents whose subjective clocks are synchronized."""
    group_id: str
    member_ids: List[str] = field(default_factory=list)
    shared_rate: float = 1.0
    trigger_event: str = ""
    created_at: float = field(default_factory=time.time)


# =============================================================================
# Chrono-Perception Forge Engine
# =============================================================================

class AgentChronoPerceptionForge:
    """
    Thread-safe singleton orchestrating subjective time perception.

    Usage:
        forge = AgentChronoPerceptionForge.get_instance()
        forge.register_agent("soldier", distortion_sensitivity=0.8, recovery_rate=0.4)
        forge.register_agent("medic", distortion_sensitivity=0.6, recovery_rate=0.5)
        forge.experience_moment("soldier", "ep_ambush", TemporalContext.COMBAT,
                                objective_duration=5.0, intensity=0.95,
                                focus=0.9, novelty=0.8, label="Ambush at Dawn")
        forge.experience_moment("medic", "ep_ambush", TemporalContext.CRISIS,
                                objective_duration=5.0, intensity=0.85,
                                focus=0.85, novelty=0.7, label="Ambush at Dawn")
        forge.synchronize_group("sync_ambush", ["soldier", "medic"], "Ambush")
        forge.cycle()
    """

    _instance: Optional["AgentChronoPerceptionForge"] = None
    _lock = threading.RLock()

    # How much intensity contributes to dilation
    _INTENSITY_DILATION_FACTOR = 0.6
    # How much focus contributes to dilation
    _FOCUS_DILATION_FACTOR = 0.4
    # How much novelty contributes to dilation
    _NOVELTY_DILATION_FACTOR = 0.3
    # Minimum intensity for dilation to occur
    _DILATION_THRESHOLD = 0.55
    # Maximum compression ratio (time flies)
    _MAX_COMPRESSION = 0.3
    # Maximum dilation ratio (time slows)
    _MAX_DILATION = 3.5
    # How much dilation boosts memory clarity
    _DILATION_CLARITY_BOOST = 0.4
    # How much compression degrades memory clarity
    _COMPRESSION_CLARITY_PENALTY = 0.3
    # Sync convergence rate
    _SYNC_CONVERGENCE = 0.5

    def __init__(self) -> None:
        self._agents: Dict[str, ChronoAgent] = {}
        self._sync_groups: Dict[str, SyncGroup] = {}
        self._phase: ForgePhase = ForgePhase.ATTEND
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=300)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {
            "total_agents": 0,
            "total_episodes": 0,
            "total_dilations": 0,
            "total_compressions": 0,
            "total_syncs": 0,
            "total_reflections": 0,
            "active_sync_groups": 0,
            "avg_subjective_rate": 1.0,
            "avg_temporal_drift": 0.0,
            "max_dilation_ratio": 1.0,
            "max_compression_ratio": 1.0,
            "hyper_detailed_episodes": 0,
            "fragmented_episodes": 0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentChronoPerceptionForge":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Agent Management
    # -------------------------------------------------------------------------

    def register_agent(
        self, agent_id: str,
        distortion_sensitivity: float = 0.5,
        recovery_rate: float = 0.3,
        baseline_rate: float = 1.0,
    ) -> Dict[str, Any]:
        """Register a new agent with subjective time perception."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already exists: {agent_id}"}
            agent = ChronoAgent(
                agent_id=agent_id,
                distortion_sensitivity=max(0.0, min(1.0, distortion_sensitivity)),
                recovery_rate=max(0.0, min(1.0, recovery_rate)),
                baseline_rate=max(0.1, baseline_rate),
                current_rate=baseline_rate,
            )
            self._agents[agent_id] = agent
            self._stats["total_agents"] = len(self._agents)
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "distortion_sensitivity": agent.distortion_sensitivity,
                "recovery_rate": agent.recovery_rate,
                "baseline_rate": agent.baseline_rate,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent from the forge."""
        with self._global_lock:
            if agent_id not in self._agents:
                return {"error": f"Agent not found: {agent_id}"}
            # Remove from any sync groups
            for group in self._sync_groups.values():
                if agent_id in group.member_ids:
                    group.member_ids.remove(agent_id)
            a = self._agents.pop(agent_id)
            self._stats["total_agents"] = len(self._agents)
            return {"removed": agent_id, "episodes_removed": a.total_episodes}

    # -------------------------------------------------------------------------
    # Experience
    # -------------------------------------------------------------------------

    def experience_moment(
        self,
        agent_id: str,
        episode_id: str,
        context: TemporalContext,
        objective_duration: float = 1.0,
        intensity: float = 0.5,
        focus: float = 0.5,
        novelty: float = 0.5,
        label: str = "",
    ) -> Dict[str, Any]:
        """Record a moment of subjective time perception for an agent."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            if episode_id in [e.episode_id for e in a.episodes]:
                return {"error": f"Episode already exists: {episode_id}"}

            # Clamp inputs
            intensity = max(0.0, min(1.0, intensity))
            focus = max(0.0, min(1.0, focus))
            novelty = max(0.0, min(1.0, novelty))
            objective_duration = max(0.01, objective_duration)

            # Compute distortion ratio based on intensity, focus, novelty
            # High intensity + focus + novelty => dilation (time slows)
            # Low intensity + focus + novelty => compression (time flies)
            dilation_pressure = (
                intensity * self._INTENSITY_DILATION_FACTOR
                + focus * self._FOCUS_DILATION_FACTOR
                + novelty * self._NOVELTY_DILATION_FACTOR
            )
            sensitivity = a.distortion_sensitivity

            if dilation_pressure > self._DILATION_THRESHOLD:
                # Dilation: time slows down
                excess = dilation_pressure - self._DILATION_THRESHOLD
                ratio = 1.0 + excess * sensitivity * 2.0
                ratio = min(ratio, self._MAX_DILATION)
                direction = DistortionDirection.DILATED
                a.total_dilations += 1
            else:
                # Compression: time speeds up
                deficit = self._DILATION_THRESHOLD - dilation_pressure
                ratio = 1.0 - deficit * sensitivity * 0.8
                ratio = max(ratio, self._MAX_COMPRESSION)
                direction = DistortionDirection.COMPRESSED
                a.total_compressions += 1

            subjective_duration = objective_duration * ratio

            # Determine memory clarity based on distortion
            if direction == DistortionDirection.DILATED:
                clarity_score = 0.5 + (ratio - 1.0) * self._DILATION_CLARITY_BOOST
                clarity_score = min(1.0, clarity_score)
                if clarity_score > 0.85:
                    clarity = MemoryClarity.HYPER_DETAILED
                elif clarity_score > 0.6:
                    clarity = MemoryClarity.VIVID
                else:
                    clarity = MemoryClarity.HAZY
            else:
                clarity_score = 0.5 - (1.0 - ratio) * self._COMPRESSION_CLARITY_PENALTY
                clarity_score = max(0.0, clarity_score)
                if clarity_score < 0.25:
                    clarity = MemoryClarity.FRAGMENTED
                elif clarity_score < 0.5:
                    clarity = MemoryClarity.HAZY
                else:
                    clarity = MemoryClarity.VIVID

            # Update agent's subjective clock
            a.subjective_clock += subjective_duration
            a.objective_clock += objective_duration
            a.temporal_drift = a.subjective_clock - a.objective_clock
            a.current_rate = ratio

            # Create episode
            episode = TemporalEpisode(
                episode_id=episode_id,
                context=context,
                objective_duration=objective_duration,
                subjective_duration=subjective_duration,
                distortion_ratio=ratio,
                direction=direction,
                intensity=intensity,
                focus=focus,
                novelty=novelty,
                clarity=clarity,
                label=label,
            )
            a.episodes.append(episode)
            a.total_episodes += 1

            self._record_event("moment_experienced", {
                "agent_id": agent_id,
                "episode_id": episode_id,
                "context": context.value,
                "ratio": round(ratio, 4),
                "direction": direction.value,
                "clarity": clarity.value,
            })
            return {
                "episode_id": episode_id,
                "agent_id": agent_id,
                "context": context.value,
                "objective_duration": objective_duration,
                "subjective_duration": round(subjective_duration, 4),
                "distortion_ratio": round(ratio, 4),
                "direction": direction.value,
                "clarity": clarity.value,
                "subjective_clock": round(a.subjective_clock, 4),
                "temporal_drift": round(a.temporal_drift, 4),
            }

    def synchronize_group(
        self, group_id: str, member_ids: List[str], trigger_event: str = "",
    ) -> Dict[str, Any]:
        """Synchronize the subjective clocks of a group of agents."""
        with self._global_lock:
            valid_members = [mid for mid in member_ids if mid in self._agents]
            if len(valid_members) < 2:
                return {"error": "Need at least 2 valid agents to synchronize"}
            # Compute shared rate as average of members' current rates
            rates = [self._agents[mid].current_rate for mid in valid_members]
            shared_rate = sum(rates) / len(rates)
            # Converge each member's rate toward the shared rate
            for mid in valid_members:
                a = self._agents[mid]
                a.current_rate = (
                    a.current_rate * (1.0 - self._SYNC_CONVERGENCE)
                    + shared_rate * self._SYNC_CONVERGENCE
                )
                a.synchronized_group = group_id
                a.total_syncs += 1
                # Mark latest episode as synced
                if a.episodes:
                    a.episodes[-1].synced_with = [
                        other for other in valid_members if other != mid
                    ]
            group = SyncGroup(
                group_id=group_id,
                member_ids=list(valid_members),
                shared_rate=shared_rate,
                trigger_event=trigger_event,
            )
            self._sync_groups[group_id] = group
            self._record_event("group_synchronized", {
                "group_id": group_id,
                "members": valid_members,
                "shared_rate": round(shared_rate, 4),
                "trigger": trigger_event,
            })
            return {
                "group_id": group_id,
                "members": valid_members,
                "shared_rate": round(shared_rate, 4),
                "trigger_event": trigger_event,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single chrono-perception forge cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = ForgePhase.ATTEND
            phase_outputs["attend"] = self._phase_attend()
            self._phase = ForgePhase.DILATE
            phase_outputs["dilate"] = self._phase_dilate()
            self._phase = ForgePhase.COMPRESS
            phase_outputs["compress"] = self._phase_compress()
            self._phase = ForgePhase.SYNCHRONIZE
            phase_outputs["synchronize"] = self._phase_synchronize()
            self._phase = ForgePhase.REFLECT
            phase_outputs["reflect"] = self._phase_reflect()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_attend(self) -> Dict[str, Any]:
        """Attend phase: agents recover toward baseline time perception."""
        recovered = 0
        for a in self._agents.values():
            if a.synchronized_group:
                continue  # skip synchronized agents
            old_rate = a.current_rate
            # Recover toward baseline
            a.current_rate = (
                a.current_rate * (1.0 - a.recovery_rate)
                + a.baseline_rate * a.recovery_rate
            )
            if abs(old_rate - a.baseline_rate) > 0.01 and abs(a.current_rate - a.baseline_rate) < 0.05:
                recovered += 1
        return {
            "agents_checked": len(self._agents),
            "agents_recovered": recovered,
        }

    def _phase_dilate(self) -> Dict[str, Any]:
        """Dilate phase: identify agents in high-intensity states."""
        dilated = 0
        max_ratio = 1.0
        for a in self._agents.values():
            if a.episodes:
                last = a.episodes[-1]
                if last.direction == DistortionDirection.DILATED:
                    dilated += 1
                    if last.distortion_ratio > max_ratio:
                        max_ratio = last.distortion_ratio
        return {
            "dilated_agents": dilated,
            "max_dilation_ratio": round(max_ratio, 4),
        }

    def _phase_compress(self) -> Dict[str, Any]:
        """Compress phase: identify agents in compressed time states."""
        compressed = 0
        min_ratio = 1.0
        for a in self._agents.values():
            if a.episodes:
                last = a.episodes[-1]
                if last.direction == DistortionDirection.COMPRESSED:
                    compressed += 1
                    if last.distortion_ratio < min_ratio:
                        min_ratio = last.distortion_ratio
        return {
            "compressed_agents": compressed,
            "min_compression_ratio": round(min_ratio, 4),
        }

    def _phase_synchronize(self) -> Dict[str, Any]:
        """Synchronize phase: dissolve old sync groups and converge rates."""
        dissolved = 0
        to_remove = []
        for gid, group in self._sync_groups.items():
            # Sync groups dissolve after one cycle (agents drift apart)
            for mid in group.member_ids:
                a = self._agents.get(mid)
                if a:
                    a.synchronized_group = None
            dissolved += 1
            to_remove.append(gid)
        for gid in to_remove:
            self._sync_groups.pop(gid, None)
        return {
            "groups_dissolved": dissolved,
            "active_groups": len(self._sync_groups),
        }

    def _phase_reflect(self) -> Dict[str, Any]:
        """Reflect phase: agents integrate distorted time memories."""
        reflections_formed = 0
        for a in self._agents.values():
            if not a.episodes:
                continue
            # Find hyper-detailed or fragmented episodes for reflection
            significant = [
                e for e in a.episodes
                if e.clarity in (MemoryClarity.HYPER_DETAILED, MemoryClarity.FRAGMENTED)
            ]
            if not significant:
                continue
            # Form a reflection
            episode = significant[-1]
            reflection = {
                "reflection_id": f"refl_{int(time.time() * 1000)}_{random.randint(0, 9999)}",
                "agent_id": a.agent_id,
                "source_episode": episode.episode_id,
                "label": episode.label,
                "context": episode.context.value,
                "direction": episode.direction.value,
                "ratio": round(episode.distortion_ratio, 4),
                "clarity": episode.clarity.value,
                "insight": self._generate_reflection_insight(episode),
                "timestamp": time.time(),
            }
            a.reflections.append(reflection)
            a.total_reflections += 1
            reflections_formed += 1
        return {
            "reflections_formed": reflections_formed,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Get the full chrono-perception state for an agent."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent_id,
                "baseline_rate": a.baseline_rate,
                "current_rate": round(a.current_rate, 4),
                "distortion_sensitivity": a.distortion_sensitivity,
                "recovery_rate": a.recovery_rate,
                "subjective_clock": round(a.subjective_clock, 4),
                "objective_clock": round(a.objective_clock, 4),
                "temporal_drift": round(a.temporal_drift, 4),
                "synchronized_group": a.synchronized_group,
                "total_episodes": a.total_episodes,
                "total_dilations": a.total_dilations,
                "total_compressions": a.total_compressions,
                "total_syncs": a.total_syncs,
                "total_reflections": a.total_reflections,
                "recent_episodes": [
                    self._serialize_episode(e) for e in list(a.episodes)[-5:]
                ],
                "reflections": a.reflections[-5:],
            }

    def get_episode(self, agent_id: str, episode_id: str) -> Dict[str, Any]:
        """Get a specific temporal episode."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            for e in a.episodes:
                if e.episode_id == episode_id:
                    return self._serialize_episode(e)
            return {"error": f"Episode not found: {episode_id}"}

    def get_sync_groups(self) -> List[Dict[str, Any]]:
        """Get all active sync groups."""
        with self._global_lock:
            return [
                {
                    "group_id": g.group_id,
                    "members": list(g.member_ids),
                    "shared_rate": round(g.shared_rate, 4),
                    "trigger_event": g.trigger_event,
                    "created_at": g.created_at,
                }
                for g in self._sync_groups.values()
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events log."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the forge."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple cycles and return the final status."""
        with self._global_lock:
            for _ in range(max(1, cycles)):
                self.cycle()
            return self.get_status()

    def reset(self) -> Dict[str, Any]:
        """Reset the entire forge."""
        with self._global_lock:
            self._agents.clear()
            self._sync_groups.clear()
            self._phase = ForgePhase.ATTEND
            self._cycle_count = 0
            self._events_log.clear()
            self._init_stats()
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _generate_reflection_insight(self, episode: TemporalEpisode) -> str:
        """Generate a textual insight from a distorted time memory."""
        if episode.direction == DistortionDirection.DILATED:
            if episode.clarity == MemoryClarity.HYPER_DETAILED:
                return f"Time froze during '{episode.label}' - every detail etched forever"
            return f"Time stretched during '{episode.label}' - it felt much longer than it was"
        else:
            if episode.clarity == MemoryClarity.FRAGMENTED:
                return f"Time vanished during '{episode.label}' - only fragments remain"
            return f"Time flew during '{episode.label}' - it passed in a blur"

    def _serialize_episode(self, e: TemporalEpisode) -> Dict[str, Any]:
        return {
            "episode_id": e.episode_id,
            "context": e.context.value,
            "objective_duration": e.objective_duration,
            "subjective_duration": round(e.subjective_duration, 4),
            "distortion_ratio": round(e.distortion_ratio, 4),
            "direction": e.direction.value,
            "intensity": e.intensity,
            "focus": e.focus,
            "novelty": e.novelty,
            "clarity": e.clarity.value,
            "label": e.label,
            "timestamp": e.timestamp,
            "synced_with": list(e.synced_with),
        }

    def _update_stats(self) -> None:
        total_agents = len(self._agents)
        total_episodes = 0
        total_dilations = 0
        total_compressions = 0
        total_syncs = 0
        total_reflections = 0
        hyper_detailed = 0
        fragmented = 0
        rates = []
        drifts = []
        max_dilation = 1.0
        max_compression = 1.0
        for a in self._agents.values():
            total_episodes += a.total_episodes
            total_dilations += a.total_dilations
            total_compressions += a.total_compressions
            total_syncs += a.total_syncs
            total_reflections += a.total_reflections
            rates.append(a.current_rate)
            drifts.append(a.temporal_drift)
            for e in a.episodes:
                if e.clarity == MemoryClarity.HYPER_DETAILED:
                    hyper_detailed += 1
                elif e.clarity == MemoryClarity.FRAGMENTED:
                    fragmented += 1
                if e.distortion_ratio > max_dilation:
                    max_dilation = e.distortion_ratio
                if e.distortion_ratio < max_compression:
                    max_compression = e.distortion_ratio
        self._stats["total_agents"] = total_agents
        self._stats["total_episodes"] = total_episodes
        self._stats["total_dilations"] = total_dilations
        self._stats["total_compressions"] = total_compressions
        self._stats["total_syncs"] = total_syncs
        self._stats["total_reflections"] = total_reflections
        self._stats["active_sync_groups"] = len(self._sync_groups)
        self._stats["avg_subjective_rate"] = sum(rates) / len(rates) if rates else 1.0
        self._stats["avg_temporal_drift"] = sum(drifts) / len(drifts) if drifts else 0.0
        self._stats["max_dilation_ratio"] = max_dilation
        self._stats["max_compression_ratio"] = max_compression
        self._stats["hyper_detailed_episodes"] = hyper_detailed
        self._stats["fragmented_episodes"] = fragmented

    def _init_stats(self) -> None:
        self._stats = {
            "total_agents": 0,
            "total_episodes": 0,
            "total_dilations": 0,
            "total_compressions": 0,
            "total_syncs": 0,
            "total_reflections": 0,
            "active_sync_groups": 0,
            "avg_subjective_rate": 1.0,
            "avg_temporal_drift": 0.0,
            "max_dilation_ratio": 1.0,
            "max_compression_ratio": 1.0,
            "hyper_detailed_episodes": 0,
            "fragmented_episodes": 0,
            "last_cycle_time_ms": 0.0,
        }

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
